import http.client
import inspect
import itertools
import re
import warnings
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Type

import marshmallow as ma
import marshmallow.fields as mf
from apispec import APISpec
from apispec.ext.marshmallow import OpenAPIConverter, SchemaResolver
# from apispec.ext.marshmallow.openapi import OpenAPIConverter
from starlette.responses import Response
from starlette.routing import BaseRoute, Mount, compile_path
from starlette.schemas import BaseSchemaGenerator

from starmallow.datastructures import DefaultPlaceholder
from starmallow.endpoint import EndpointModel, SchemaModel
from starmallow.ext.marshmallow import MarshmallowPlugin
from starmallow.responses import HTTPValidationError
from starmallow.routing import APIRoute
from starmallow.utils import (
    deep_dict_update,
    dict_safe_add,
    is_marshmallow_field,
    status_code_ranges,
)


class SchemaRegistry(dict):
    '''
        Dict that holds all the schemas for each class and lazily resolves them.
    '''
    def __init__(
        self,
        spec: APISpec,
        converter: OpenAPIConverter,
        resolver: SchemaResolver,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.spec = spec
        self.converter = converter
        self.resolver = resolver

    def __getitem__(self, item):
        if is_marshmallow_field(item):
            # If marshmallow field, just resolve it here without caching
            prop = self.converter.field2property(item)
            return prop

        if isinstance(item, SchemaModel):
            item = item.schema

        is_class = inspect.isclass(item)
        schema_class = item if is_class else item.__class__

        try:
            schema = super().__getitem__(schema_class)
        except KeyError:
            try:
                schema = self.spec.components.schemas.__getitem__(schema_class.__name__)
            except KeyError:
                self.spec.components.schema(component_id=schema_class.__name__, schema=item)

            schema = self.resolver.resolve_schema_dict(item)
            super().__setitem__(schema_class, schema)

        if not is_class:
            schema = self.resolver.resolve_schema_dict(item)

        return schema


class SchemaGenerator(BaseSchemaGenerator):
    '''OpenApi Schema generator'''

    def __init__(
        self,
        title: str,
        version: str,
        description: str,
        openapi_version: str = '3.0.0',
    ) -> None:
        super().__init__()

        marshmallow_plugin = MarshmallowPlugin()
        self.spec = APISpec(
            title=title,
            version=version,
            openapi_version=openapi_version,
            info={'description': description} if description else {},
            plugins=[marshmallow_plugin],
        )

        self.converter = marshmallow_plugin.converter
        self.resolver = marshmallow_plugin.resolver

        # Builtin definitions
        self.schemas = SchemaRegistry(self.spec, self.converter, self.resolver)

        self.operation_ids: Set[str] = set()

    def get_endpoints(
        self,
        routes: List[BaseRoute],
        base_path: str = "",
    ) -> Dict[str, Sequence[EndpointModel]]:
        """
            Given the routes, yields the following information:

            - path
                eg: /users/
            - http_method
                one of 'get', 'post', 'put', 'patch', 'delete', 'options'
            - func
                method ready to extract the docstring

            Returns a Dict where the keys are the paths, and the values are sequences of endpoint infos.
            This allows each path to have multiple responses.
        """

        endpoints_info: Dict[str, Sequence[APIRoute]] = defaultdict(list)

        for route in routes:
            # path is not defined in BaseRoute, but all implementations have it.
            _, path, _ = compile_path(base_path + route.path)

            if isinstance(route, APIRoute) and route.include_in_schema:
                if inspect.isfunction(route.endpoint) or inspect.ismethod(route.endpoint):
                    for method in (route.methods or ['GET']):
                        if method == 'HEAD':
                            continue

                        endpoints_info[path].append(route.endpoint_model)

            elif isinstance(route, Mount):
                endpoints_info.update(self.get_endpoints(route.routes, base_path=path))

        return endpoints_info

    def _add_endpoint_parameters(
        self,
        endpoint: EndpointModel,
        schema: Dict,
    ):
        schema["parameters"] = [
            self.converter._field2parameter(
                field.model.to_nested() if isinstance(field.model, SchemaModel) else field.model,
                name=name,
                location=field.in_.name,
            )
            for name, field in itertools.chain(
                endpoint.query_params.items(),
                endpoint.path_params.items(),
                endpoint.header_params.items(),
                endpoint.cookie_params.items(),
            )
            if field.include_in_schema
        ]

    def _add_endpoint_body(
        self,
        endpoint: EndpointModel,
        schema: Dict,
    ):
        # If only 1 schema is defined. Use it as the entire schema.
        if len(endpoint.body_params) == 1 and isinstance(list(endpoint.body_params.values())[0].model, ma.Schema):
            body_param = list(endpoint.body_params.values())[0]
            if body_param.include_in_schema:
                endpoint_schema = self.schemas[body_param.model]

        # Otherwise, loop over all body params and build a new schema from the key value pairs.
        # This mimic's FastApi's behaviour: https://fastapi.tiangolo.com/tutorial/body-multiple-params/#multiple-body-parameters
        else:
            required_properties = []
            endpoint_properties = {}
            endpoint_schema = {
                "type": "object",
                "properties": endpoint_properties,
                "required": required_properties,
            }
            for name, value in endpoint.body_params.items():
                if value.include_in_schema:
                    if isinstance(value.model, ma.Schema):
                        endpoint_properties[name] = self.schemas[value.model]
                        if isinstance(value.model, SchemaModel) and value.model.required:
                            required_properties.append(name)

                    elif isinstance(value.model, mf.Field):
                        endpoint_properties[name] = self.converter.field2property(value.model)
                        if value.model.required:
                            required_properties.append(name)

        if endpoint_schema:
            schema['requestBody'] = {
                'content': {
                    endpoint.response_class.media_type: {'schema': endpoint_schema}
                },
                'required': True,
            }

    def _add_endpoint_response(
        self,
        endpoint: EndpointModel,
        schema: Dict,
    ):
        operation_responses = schema.setdefault("responses", {})
        response_codes = list(operation_responses.keys())
        main_response = str(endpoint.status_code or (response_codes[0] if response_codes else 200))

        operation_responses[main_response] = {
            'content': {
                endpoint.response_class.media_type: {
                    'schema': self.schemas[endpoint.response_model] if endpoint.response_model else {}
                }
            },
        }
        if endpoint.route.response_description:
            operation_responses[main_response]['description'] = endpoint.route.response_description

        # Process additional responses
        route = endpoint.route
        if isinstance(route.response_class, DefaultPlaceholder):
            current_response_class: Type[Response] = route.response_class.value
        else:
            current_response_class = route.response_class
        assert current_response_class, "A response class is needed to generate OpenAPI"
        route_response_media_type: Optional[str] = current_response_class.media_type

        if route.responses:
            for (
                additional_status_code,
                additional_response,
            ) in route.responses.items():
                process_response = additional_response.copy()
                process_response.pop("model", None)
                status_code_key = str(additional_status_code).upper()
                if status_code_key == "DEFAULT":
                    status_code_key = "default"
                openapi_response = operation_responses.setdefault(
                    status_code_key, {}
                )
                assert isinstance(
                    process_response, dict
                ), "An additional response must be a dict"
                field = route.response_fields.get(additional_status_code)
                additional_field_schema: Optional[Dict[str, Any]] = None
                if field:
                    additional_field_schema = self.schemas[field] if field else {}
                    media_type = route_response_media_type or "application/json"
                    additional_schema = (
                        process_response.setdefault("content", {})
                        .setdefault(media_type, {})
                        .setdefault("schema", {})
                    )
                    deep_dict_update(additional_schema, additional_field_schema)
                status_text: Optional[str] = status_code_ranges.get(
                    str(additional_status_code).upper()
                ) or http.client.responses.get(int(additional_status_code))
                description = (
                    process_response.get("description")
                    or openapi_response.get("description")
                    or status_text
                    or "Additional Response"
                )
                deep_dict_update(openapi_response, process_response)
                openapi_response["description"] = description

    def _add_default_error_response(self, schema: Dict):
        dict_safe_add(
            schema,
            'responses.422.description',
            'Validation Error',
        )
        dict_safe_add(
            schema,
            'responses.422.content.application/json.schema',
            self.schemas[HTTPValidationError],
        )

    def _generate_openapi_summary(self, route: APIRoute) -> str:
        if route.summary:
            return route.summary
        return re.sub(r"(\w)([A-Z])", r"\1 \2", route.name).replace(".", " ").replace("_", " ").title()

    def _get_route_openapi_metadata(self, route: APIRoute) -> Dict[str, Any]:
        schema = {}
        if route.tags:
            schema["tags"] = route.tags
        schema["summary"] = self._generate_openapi_summary(route=route)
        if route.description:
            schema["description"] = route.description
        operation_id = route.operation_id or route.unique_id
        if operation_id in self.operation_ids:
            message = (
                f"Duplicate Operation ID {operation_id} for function "
                + f"{route.endpoint.__name__}"
            )
            file_name = getattr(route.endpoint, "__globals__", {}).get("__file__")
            if file_name:
                message += f" at {file_name}"
            warnings.warn(message)
        self.operation_ids.add(operation_id)
        schema["operationId"] = operation_id
        if route.deprecated:
            schema["deprecated"] = route.deprecated

        return schema

    def get_endpoint_schema(
        self,
        endpoint: EndpointModel,
    ) -> Dict[str, Any]:
        '''
            Generates the endpoint schema
        '''
        schema = self._get_route_openapi_metadata(endpoint.route)

        schema.update(self.parse_docstring(endpoint.call))

        # Query, Path, and Header parameters
        any_params = (
            endpoint.query_params
            or endpoint.path_params
            or endpoint.header_params
            or endpoint.cookie_params
        )
        if any_params:
            self._add_endpoint_parameters(endpoint, schema)

        # Body
        if endpoint.body_params:
            self._add_endpoint_body(endpoint, schema)

        # Response
        self._add_endpoint_response(endpoint, schema)

        # Add default error response
        if (any_params or endpoint.body_params) and not any(
            [
                status in schema['responses']
                for status in ["422", "4XX", "default"]
            ]
        ):
            self._add_default_error_response(schema)

        # Callbacks
        if endpoint.route.callbacks:
            callbacks = {}
            for callback in endpoint.route.callbacks:
                if isinstance(callback, APIRoute):
                    callbacks[callback.name] = {
                        path: self.get_operations(endpoints)
                        for path, endpoints in self.get_endpoints([callback]).items()
                    }

            schema['callbacks'] = callbacks

        return schema

    def get_operations(self, endpoints: List[EndpointModel]):
        return {
            method.lower(): self.get_endpoint_schema(e)
            for e in endpoints
            for method in e.methods
            if method != 'HEAD'
        }

    def get_schema(
        self,
        routes: List[APIRoute],
    ) -> Dict[str, Any]:
        '''
            Generates the schemas for the specified routes..
        '''
        endpoints_info = self.get_endpoints(routes)

        for path, endpoints in endpoints_info.items():
            self.spec.path(
                path=path,
                operations=self.get_operations(endpoints),
            )

        return self.spec.to_dict()
