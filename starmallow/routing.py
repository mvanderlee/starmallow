import asyncio
import datetime as dt
import inspect
import logging
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.error_store import ErrorStore
from marshmallow.utils import missing as missing_
from starlette import routing
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import FormData, Headers, QueryParams
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import request_response

from starmallow.constants import STATUS_CODES_WITH_NO_BODY
from starmallow.exceptions import RequestValidationError
from starmallow.params import Body, Cookie, Form, Header, Param, ParamType, Path, Query
from starmallow.types import DecoratedCallable
from starmallow.utils import (
    generate_unique_id,
    get_args,
    is_marshmallow_dataclass,
    is_marshmallow_field,
    is_marshmallow_schema,
    is_optional,
)

logger = logging.getLogger(__name__)

PY_TO_MF_MAPPING = {
    int: mf.Integer,
    float: mf.Float,
    bool: mf.Boolean,
    str: mf.String,
    Decimal: mf.Decimal,
    dt.date: mf.Date,
    dt.datetime: mf.DateTime,
    dt.time: mf.Time,
    dt.timedelta: mf.TimeDelta,
    uuid.UUID: mf.UUID,
}


class SchemaModel(ma.Schema):
    def __init__(
        self,
        schema: ma.Schema,
        load_default: Any = missing_,
        required: bool = True,
    ) -> None:
        self.schema = schema
        self.load_default = load_default
        self.required = required

    def to_nested(self):
        return mf.Nested(
            self.schema,
            required=self.required,
            load_default=self.load_default,
        )

    def load(
        self,
        data: Union[
            Mapping[str, Any],
            Iterable[Mapping[str, Any]],
        ],
        *,
        many: Optional[bool] = None,
        partial: Optional[bool] = None,
        unknown: Optional[str] = None,
    ) -> Any:
        if not data and self.load_default:
            return self.load_default

        return self.schema.load(data, many=many, partial=partial, unknown=unknown)


@dataclass
class EndpointModel:
    path_params: Optional[Dict[str, Path]] = field(default_factory=list)
    query_params: Optional[Dict[str, Query]] = field(default_factory=list)
    header_params: Optional[Dict[str, Header]] = field(default_factory=list)
    cookie_params: Optional[Dict[str, Cookie]] = field(default_factory=list)
    body_params: Optional[Dict[str, Body]] = field(default_factory=list)
    form_params: Optional[Dict[str, Form]] = field(default_factory=list)
    name: Optional[str] = None
    path: Optional[str] = None
    methods: Optional[List[str]] = None
    call: Optional[Callable[..., Any]] = None
    response_model: Optional[ma.Schema] = None
    response_class: Type[Response] = JSONResponse
    status_code: Optional[int] = None


async def get_body(
    request: Request,
    endpoint_model: "EndpointModel",
) -> Union[FormData, bytes, Dict[str, Any]]:
    is_body_form = bool(endpoint_model.form_params)
    should_process_body = is_body_form or endpoint_model.body_params
    try:
        body: Any = None
        if should_process_body:
            if is_body_form:
                body = await request.form()
            else:
                body_bytes = await request.body()
                if body_bytes:
                    json_body: Any = missing_
                    content_type_value: str = request.headers.get("content-type")
                    if not content_type_value:
                        json_body = await request.json()
                    else:
                        main_type, sub_type = content_type_value.split('/')
                        if main_type == "application":
                            if sub_type == "json" or sub_type.endswith("+json"):
                                json_body = await request.json()
                    if json_body != missing_:
                        body = json_body
                    else:
                        body = body_bytes

        return body
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="There was an error parsing the body",
        ) from e


def request_params_to_args(
    received_params: Union[Mapping[str, Any], QueryParams, Headers],
    endpoint_params: Dict[str, Param],
    ignore_namespace: bool = True,
) -> Tuple[Dict[str, Any], ErrorStore]:
    values = {}
    error_store = ErrorStore()
    for field_name, param in endpoint_params.items():
        if isinstance(param.model, mf.Field):
            try:
                # Load model from specific param
                values[field_name] = param.model.deserialize(
                    received_params.get(field_name, ma.missing),
                    field_name,
                    received_params,
                )
            except ma.ValidationError as error:
                error_store.store_error(error.messages, field_name)
        elif isinstance(param.model, ma.Schema):
            try:
                if ignore_namespace:
                    # Load model from entire params
                    values[field_name] = param.model.load(received_params, unknown=ma.EXCLUDE)
                else:
                    values[field_name] = param.model.load(received_params.get(field_name, ma.missing), unknown=ma.EXCLUDE)
            except ma.ValidationError as error:
                error_store.store_error(error.messages)
        else:
            raise Exception(f'Invalid model type {type(param.model)}, expected marshmallow Schema or Field')

    return values, error_store


async def get_request_args(
    request: Request,
    endpoint_model: EndpointModel,
) -> Tuple[Dict[str, Any], Dict[str, Union[Any, List, Dict]]]:
    path_values, path_errors = request_params_to_args(
        request.path_params,
        endpoint_model.path_params,
    )
    query_values, query_errors = request_params_to_args(
        request.query_params,
        endpoint_model.query_params,
    )
    header_values, header_errors = request_params_to_args(
        request.headers,
        endpoint_model.header_params,
    )
    cookie_values, cookie_errors = request_params_to_args(
        request.cookies,
        endpoint_model.cookie_params,
    )

    body = await get_body(request, endpoint_model)
    form_values, form_errors = {}, None
    json_values, json_errors = {}, None
    if endpoint_model.form_params:
        form_values, form_errors = request_params_to_args(
            body if body is not None and isinstance(body, FormData) else {},
            endpoint_model.form_params,
            # If there is only one parameter defined, then don't namespace by the parameter name
            # Otherwise we honor the namespace: https://fastapi.tiangolo.com/tutorial/body-multiple-params/
            ignore_namespace=len(endpoint_model.form_params) == 1,
        )
    if endpoint_model.body_params:
        json_values, json_errors = request_params_to_args(
            body if body is not None and isinstance(body, Mapping) else {},
            endpoint_model.body_params,
            # If there is only one parameter defined, then don't namespace by the parameter name
            # Otherwise we honor the namespace: https://fastapi.tiangolo.com/tutorial/body-multiple-params/
            ignore_namespace=len(endpoint_model.body_params) == 1,
        )

    values = {
        **path_values,
        **query_values,
        **header_values,
        **cookie_values,
        **form_values,
        **json_values,
    }
    errors = {}
    if path_errors.errors:
        errors['path'] = path_errors.errors
    if query_errors.errors:
        errors['query'] = query_errors.errors
    if header_errors.errors:
        errors['header'] = header_errors.errors
    if cookie_errors.errors:
        errors['cookie'] = cookie_errors.errors
    if form_errors and form_errors.errors:
        errors['form'] = form_errors.errors
    if json_errors and json_errors.errors:
        errors['json'] = json_errors.errors

    return values, errors


async def run_endpoint_function(
    endpoint_model: EndpointModel,
    values: Dict[str, Any],
) -> Any:
    assert endpoint_model.call is not None, "endpoint_model.call must be a function"

    if asyncio.iscoroutinefunction(endpoint_model.call):
        return await endpoint_model.call(**values)
    else:
        return await run_in_threadpool(endpoint_model.call, **values)


def get_request_handler(
    endpoint_model: EndpointModel,
) -> Callable[[Request], Coroutine[Any, Any, Response]]:
    assert endpoint_model.call is not None, "dependant.call must be a function"

    async def app(request: Request) -> Response:
        values, errors = await get_request_args(request, endpoint_model)

        if errors:
            raise RequestValidationError(errors)

        raw_response = await run_endpoint_function(
            endpoint_model,
            values,
        )
        if isinstance(raw_response, Response):
            return raw_response

        response_data = None
        if endpoint_model.response_model is not None:
            response_data = endpoint_model.response_model.dump(raw_response)
        response_args = {}
        if endpoint_model.status_code is not None:
            response_args["status_code"] = endpoint_model.status_code

        response = endpoint_model.response_class(response_data, **response_args)

        return response

    return app


class EndpointMixin:

    def _get_param_model(self, parameter: inspect.Parameter) -> Union[ma.Schema, mf.Field]:
        model = parameter.annotation

        kwargs = {
            'required': True,
        }
        if is_optional(parameter.annotation):
            kwargs = {
                'load_default': None,
                'required': False,
            }
            # This does not support Union[A,B,C,None]. Only Union[A,None] and Optional[A]
            model = next((a for a in get_args(parameter.annotation) if a is not None), None)

        if isinstance(parameter.default, Param):
            # If default is not Ellipsis, then it's optional regardless of the typehint.
            # Although it's best practice to also mark the typehint as Optional
            if parameter.default.default != Ellipsis:
                kwargs = {
                    'load_default': parameter.default.default,
                    'required': False,
                }

            # Ignore type hint. Use provided model instead.
            if parameter.default.model is not None:
                model = parameter.default.model
        elif parameter.default != inspect._empty:
            # If default is not a Param but is defined, then it's optional regardless of the typehint.
            # Although it's best practice to also mark the typehint as Optional
            kwargs = kwargs = {
                'load_default': parameter.default,
                'required': False,
            }

        if is_marshmallow_dataclass(model):
            model = model.Schema

        if is_marshmallow_schema(model):
            return SchemaModel(model(), **kwargs)
        elif is_marshmallow_field(model):
            if model.load_default is not None and model.load_default != kwargs.get('load_default', ma.missing):
                logger.warning(f"'{parameter.name}' model and annotation have different 'load_default' values. {model.load_default} <> {kwargs.get('load_default', ma.missing)}")

            model.required = kwargs['required']
            model.load_default = kwargs.get('load_default', ma.missing)

            return model
        elif model in PY_TO_MF_MAPPING:
            return PY_TO_MF_MAPPING[model](**kwargs)
        else:
            raise Exception(f'Unknown model type for parameter {parameter.name}, model is {model}')

    def _get_params_from_endpoint(
        self,
        endpoint: Callable[..., Any],
    ) -> Dict[ParamType, List[Dict[str, Param]]]:
        params = {param_type: {} for param_type in ParamType}
        for name, parameter in inspect.signature(endpoint).parameters.items():
            model = self._get_param_model(parameter)

            if isinstance(parameter.default, Param):
                # Create new field_info with processed model
                field_info = parameter.default.__class__(
                    parameter.default.default,
                    deprecated=parameter.default.deprecated,
                    include_in_schema=parameter.default.include_in_schema,
                    model=model,
                )
            elif isinstance(model, mf.Field):
                # If marshmallow field with no Param defined, default it to QueryParameter
                field_info = Query(
                    # If a default was provided, honor it.
                    ... if parameter.default == inspect._empty else parameter.default,
                    deprecated=False,
                    include_in_schema=True,
                    model=model,
                )
            else:
                # Default all others to body params
                field_info = Body(..., deprecated=False, include_in_schema=True, model=model)

            params[field_info.in_][name] = field_info

        return params

    def get_endpoint_model(
        self,
        path: str,
        endpoint: Callable[..., Any],
        name: Optional[str] = None,
        methods: Optional[List[str]] = None,

        status_code: Optional[int] = None,
        response_model: Optional[ma.Schema] = None,
        response_class: Type[Response] = JSONResponse,
    ) -> EndpointModel:
        params = self._get_params_from_endpoint(endpoint)

        response_model = response_model or inspect.signature(endpoint).return_annotation
        if is_marshmallow_dataclass(response_model):
            response_model = response_model.Schema
        if is_marshmallow_schema(response_model):
            response_model = response_model()
        else:
            response_model = None

        return EndpointModel(
            path=path,
            name=name,
            methods=methods,
            call=endpoint,
            path_params=params[ParamType.path],
            query_params=params[ParamType.query],
            header_params=params[ParamType.header],
            cookie_params=params[ParamType.cookie],
            body_params=params[ParamType.body],
            form_params=params[ParamType.form],
            response_model=response_model,
            response_class=response_class,
            status_code=status_code,
        )


class APIRoute(routing.Route, EndpointMixin):

    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        name: Optional[str] = None,
        methods: Optional[Union[Set[str], List[str]]] = None,
        include_in_schema: bool = True,

        description: Optional[str] = None,

        status_code: Optional[int] = None,
        response_model: Optional[ma.Schema] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            path,
            endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )
        assert callable(endpoint), "An endpoint must be a callable"

        self.status_code = status_code
        self.response_model = response_model
        self.response_class = response_class
        self.operation_id = operation_id
        self.generate_unique_id_function = generate_unique_id_function
        self.openapi_extra = openapi_extra

        self.unique_id = self.operation_id or generate_unique_id_function(self)

        # normalize enums e.g. http.HTTPStatus
        if isinstance(status_code, IntEnum):
            status_code = int(status_code)
        self.status_code = status_code

        self.description = description or inspect.cleandoc(self.endpoint.__doc__ or "")
        # if a "form feed" character (page break) is found in the description text,
        # truncate description text to the content preceding the first "form feed"
        self.description = self.description.split("\f")[0]

        if self.response_model:
            assert (
                status_code not in STATUS_CODES_WITH_NO_BODY
            ), f"Status code {status_code} must not have a response body"

        self.endpoint_model = self.get_endpoint_model(
            path,
            endpoint,
            name=name,
            methods=self.methods,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
        )

        self.app = request_response(get_request_handler(self.endpoint_model))


class APIRouter(routing.Router):

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Optional[Union[Set[str], List[str]]] = None,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        route = APIRoute(
            path,
            endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

        self.routes.append(route)

    def api_route(
        self,
        path: str,
        *,
        methods: Optional[Union[Set[str], List[str]]] = None,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_api_route(
                path,
                func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
                status_code=status_code,
                response_model=response_model,
                response_class=response_class,
                operation_id=operation_id,
                generate_unique_id_function=generate_unique_id_function,
                openapi_extra=openapi_extra,
            )
            return func
        return decorator

    def get(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['GET'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def put(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['PUT'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def post(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['POST'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def delete(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['DELETE'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def options(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['OPTIONS'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def head(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['HEAD'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def patch(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['PATCH'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )

    def trace(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = generate_unique_id,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['TRACE'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )
