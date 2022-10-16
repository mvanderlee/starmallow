import inspect
import itertools
from collections import defaultdict
from typing import Any, Dict, List, Sequence

import marshmallow as ma
import marshmallow.fields as mf
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin, SchemaResolver
from starlette.routing import BaseRoute, Mount, compile_path
from starlette.schemas import BaseSchemaGenerator

from starmallow.responses import APIError
from starmallow.routing import APIRoute, EndpointModel, SchemaModel
from starmallow.utils import dict_safe_add


class SchemaRegistry(dict):
    '''
        Dict that holds all the schemas for each class and lazily resolves them.
    '''
    def __init__(self, spec: APISpec, resolver: SchemaResolver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spec = spec
        self.resolver = resolver

    def __getitem__(self, item):
        if isinstance(item, SchemaModel):
            item = item.schema

        is_class = inspect.isclass(item)
        schema_class = item if is_class else item.__class__

        try:
            schema = super().__getitem__(schema_class)
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
            info={'description': description},
            plugins=[marshmallow_plugin],
        )

        self.converter = marshmallow_plugin.converter
        self.resolver = marshmallow_plugin.resolver

        # Builtin definitions
        self.schemas = SchemaRegistry(self.spec, self.resolver)

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

        endpoints_info: Dict[str, Sequence[EndpointModel]] = defaultdict(list)

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
            dict_safe_add(
                schema,
                'requestBody.content.application/json.schema',
                endpoint_schema,
            )

    def _add_endpoint_response(
        self,
        endpoint: EndpointModel,
        schema: Dict,
    ):
        response_codes = list(schema.get("responses", {}).keys())
        main_response = endpoint.status_code or (response_codes[0] if response_codes else 200)

        dict_safe_add(
            schema,
            f'responses.{main_response}.content.application/json.schema',
            self.schemas[endpoint.response_model],
        )

    def _add_endpoint_validation_error_response(self, schema: Dict):
        dict_safe_add(
            schema,
            'responses.422.content.application/json.schema',
            self.schemas[APIError],
        )

    def get_endpoint_schema(
        self,
        endpoint: EndpointModel,
    ) -> Dict[str, Any]:
        '''
            Generates the endpoint schema
        '''
        schema = self.parse_docstring(endpoint.call)

        # Query, Path, and Header parameters
        if (
            endpoint.query_params
            or endpoint.path_params
            or endpoint.header_params
            or endpoint.cookie_params
        ):
            self._add_endpoint_parameters(endpoint, schema)

        # Body
        if endpoint.body_params:
            self._add_endpoint_body(endpoint, schema)

        # Response
        if endpoint.response_model:
            self._add_endpoint_response(endpoint, schema)

        # Default error response
        self._add_endpoint_validation_error_response(schema)

        return schema

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
                operations={
                    method.lower(): self.get_endpoint_schema(e)
                    for e in endpoints
                    for method in e.methods
                    if method != 'HEAD'
                },
            )

        return self.spec.to_dict()
