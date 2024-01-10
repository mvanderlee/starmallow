import asyncio
import functools
import inspect
import logging
from contextlib import AsyncExitStack
from enum import Enum, IntEnum
from typing import Any, Callable, Coroutine, Dict, List, Mapping, Optional, Set, Tuple, Type, Union

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.error_store import ErrorStore
from marshmallow.utils import missing as missing_
from starlette import routing
from starlette.background import BackgroundTasks
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import FormData, Headers, QueryParams
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match, compile_path, request_response
from starlette.status import WS_1008_POLICY_VIOLATION
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from starmallow.constants import STATUS_CODES_WITH_NO_BODY
from starmallow.datastructures import Default, DefaultPlaceholder
from starmallow.decorators import EndpointOptions
from starmallow.endpoint import EndpointMixin, EndpointModel
from starmallow.endpoints import APIHTTPEndpoint
from starmallow.exceptions import RequestValidationError, WebSocketRequestValidationError
from starmallow.params import Param, ParamType
from starmallow.responses import JSONResponse
from starmallow.types import DecoratedCallable
from starmallow.utils import (
    create_response_model,
    generate_unique_id,
    get_name,
    get_value_or_default,
    is_async_gen_callable,
    is_body_allowed_for_status_code,
    is_gen_callable,
    is_marshmallow_field,
    is_marshmallow_schema,
    lenient_issubclass,
    solve_generator,
)
from starmallow.websockets import APIWebSocket

logger = logging.getLogger(__name__)


async def get_body(
    request: Request,
    endpoint_model: "EndpointModel",
) -> Union[FormData, bytes, Dict[str, Any]]:
    is_body_form = bool(endpoint_model.flat_params[ParamType.form])
    should_process_body = is_body_form or endpoint_model.flat_params[ParamType.body]
    try:
        body: Any = None
        if should_process_body:
            if is_body_form:
                body = await request.form()
                stack = request.scope.get("starmallow_astack")
                assert isinstance(stack, AsyncExitStack)
                stack.push_async_callback(body.close)
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
                    values[field_name] = param.model.load(
                        received_params.get(field_name, ma.missing),
                        unknown=ma.EXCLUDE,
                    )
            except ma.ValidationError as error:
                error_store.store_error(error.messages)
        else:
            raise Exception(f'Invalid model type {type(param.model)}, expected marshmallow Schema or Field')

    return values, error_store


async def get_request_args(
    request: Request | WebSocket,
    endpoint_model: EndpointModel,
    background_tasks: Optional[BackgroundTasks] = None,
    response: Optional[Response] = None,
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
    form_params = endpoint_model.form_params
    if form_params:
        form_values, form_errors = request_params_to_args(
            body if body is not None and isinstance(body, FormData) else {},
            form_params,
            # If there is only one parameter defined, then don't namespace by the parameter name
            # Otherwise we honor the namespace: https://fastapi.tiangolo.com/tutorial/body-multiple-params/
            ignore_namespace=len(form_params) == 1,
        )
    body_params = endpoint_model.body_params
    if body_params:
        json_values, json_errors = request_params_to_args(
            body if body is not None and isinstance(body, Mapping) else {},
            body_params,
            # If there is only one parameter defined, then don't namespace by the parameter name
            # Otherwise we honor the namespace: https://fastapi.tiangolo.com/tutorial/body-multiple-params/
            ignore_namespace=len(body_params) == 1,
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

    if response is None:
        response = Response()
        del response.headers["content-length"]
        response.status_code = None  # type: ignore

    # Handle non-field params
    for param_name, param_type in endpoint_model.non_field_params.items():
        if lenient_issubclass(param_type, (HTTPConnection, Request, WebSocket)):
            values[param_name] = request
        elif lenient_issubclass(param_type, Response):
            values[param_name] = response
        elif lenient_issubclass(param_type, BackgroundTasks):
            if background_tasks is None:
                background_tasks = BackgroundTasks()
            values[param_name] = background_tasks

    # Handle resolved params - reverse resolved params so we process the most nested ones first
    for param_name, resolved_param in reversed(endpoint_model.resolved_params.items()):
        # Get all known arguments for the resolver.
        resolver_kwargs = {}
        for name, parameter in inspect.signature(resolved_param.resolver).parameters.items():
            if lenient_issubclass(parameter.annotation, (HTTPConnection, Request, WebSocket)):
                resolver_kwargs[name] = request
            elif lenient_issubclass(parameter.annotation, Response):
                resolver_kwargs[name] = response
            elif lenient_issubclass(parameter.annotation, BackgroundTasks):
                if background_tasks is None:
                    background_tasks = BackgroundTasks()
                resolver_kwargs[name] = background_tasks
            elif name in values:
                resolver_kwargs[name] = values[name]

        # Resolver can be a class with __call__ function
        resolver = resolved_param.resolver
        if not inspect.isfunction(resolver) and callable(resolver):
            resolver = resolver.__call__
        elif not inspect.isfunction(resolver):
            raise TypeError(f'{param_name} = {resolved_param} resolver is not a function or callable')

        if is_gen_callable(resolver) or is_async_gen_callable(resolver):
            stack = request.scope.get("starmallow_astack")
            assert isinstance(stack, AsyncExitStack)
            values[param_name] = await solve_generator(
                call=resolver, stack=stack, gen_kwargs=resolver_kwargs,
            )
        elif asyncio.iscoroutinefunction(resolver):
            values[param_name] = await resolver(**resolver_kwargs)
        else:
            values[param_name] = resolver(**resolver_kwargs)

    return values, errors


async def run_endpoint_function(
    endpoint_model: EndpointModel,
    values: Dict[str, Any],
) -> Any:
    assert endpoint_model.call is not None, "endpoint_model.call must be a function"

    kwargs = {
        name: values[name]
        for name in inspect.signature(endpoint_model.call).parameters
        if name in values
    }

    if asyncio.iscoroutinefunction(endpoint_model.call):
        return await endpoint_model.call(**kwargs)
    else:
        return await run_in_threadpool(endpoint_model.call, **kwargs)


def websocket_session(func: Callable) -> ASGIApp:
    """
    Takes a coroutine `func(session)`, and returns an ASGI application.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        session = APIWebSocket(scope, receive=receive, send=send)
        await func(session)

    return app


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

        response_data = raw_response
        if is_marshmallow_schema(endpoint_model.response_model):
            response_data = endpoint_model.response_model.dump(raw_response)
        elif is_marshmallow_field(endpoint_model.response_model):
            response_data = endpoint_model.response_model._serialize(raw_response, attr='response', obj=raw_response)

        response_args = {}
        if endpoint_model.status_code is not None:
            response_args["status_code"] = endpoint_model.status_code

        response = endpoint_model.response_class(response_data, **response_args)

        return response

    return app


def get_websocker_hander(
    endpoint_model: EndpointModel,
) -> Callable[[Request], Coroutine[Any, Any, Response]]:
    assert endpoint_model.call is not None, "dependant.call must be a function"

    async def app(websocket: WebSocket) -> None:
        values, errors = await get_request_args(websocket, endpoint_model)

        if errors:
            await websocket.close(code=WS_1008_POLICY_VIOLATION)
            raise WebSocketRequestValidationError(errors)

        await run_endpoint_function(
            endpoint_model,
            values,
        )

    return app


class APIWebSocketRoute(routing.WebSocketRoute, EndpointMixin):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        name: Optional[str] = None,
    ) -> None:
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)
        self.app = websocket_session(
            get_websocker_hander(
                self.get_endpoint_model(
                    self.path_format,
                    endpoint,
                    name=name,
                    route=self,
                ),
            ),
        )

    def matches(self, scope: Scope) -> Tuple[Match, Scope]:
        match, child_scope = super().matches(scope)
        if match != Match.NONE:
            child_scope["route"] = self
        return match, child_scope


class APIRoute(routing.Route, EndpointMixin):

    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        name: Optional[str] = None,
        methods: Optional[Union[Set[str], List[str]]] = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[ma.Schema] = None,
        response_class: Union[Type[Response], DefaultPlaceholder] = Default(
            JSONResponse,
        ),
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Union[
            Callable[["APIRoute"], str], DefaultPlaceholder,
        ] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Copied from starlette, without the path assertion
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.include_in_schema = include_in_schema

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            # Endpoint is function or method. Treat it as `func(request) -> response`.
            self.app = request_response(endpoint)
            if methods is None:
                methods = ["GET"]
        else:
            # Endpoint is a class. Treat it as ASGI.
            self.app = endpoint

        if methods is None:
            self.methods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)
        # End starlette copy
        assert callable(endpoint), "An endpoint must be a callable"

        self.status_code = status_code
        self.deprecated = deprecated
        self.response_model = response_model
        self.response_class = response_class
        self.summary = summary
        self.operation_id = operation_id
        self.callbacks = callbacks
        self.tags = tags or []
        self.responses = responses or {}
        self.openapi_extra = openapi_extra

        self.generate_unique_id_function = generate_unique_id_function
        if isinstance(generate_unique_id_function, DefaultPlaceholder):
            current_generate_unique_id: Callable[
                ["APIRoute"], str,
            ] = generate_unique_id_function.value
        else:
            current_generate_unique_id = generate_unique_id_function
        self.unique_id = self.operation_id or current_generate_unique_id(self)

        # normalize enums e.g. http.HTTPStatus
        if isinstance(status_code, IntEnum):
            status_code = int(status_code)
        self.status_code = status_code

        self.description = description or inspect.cleandoc(self.endpoint.__doc__ or "")
        # if a "form feed" character (page break) is found in the description text,
        # truncate description text to the content preceding the first "form feed"
        self.description = self.description.split("\f")[0]
        self.response_description = response_description

        if self.response_model:
            assert (
                status_code not in STATUS_CODES_WITH_NO_BODY
            ), f"Status code {status_code} must not have a response body"

        response_fields = {}
        for additional_status_code, response in self.responses.items():
            assert isinstance(response, dict), "An additional response must be a dict"
            model = response.get("model")
            if model:
                assert is_body_allowed_for_status_code(
                    additional_status_code,
                ), f"Status code {additional_status_code} must not have a response body"
                # TODO: do we want this?
                # response_name = f"Response_{additional_status_code}_{self.unique_id}"
                # response_field = create_response_model(name=response_name, type_=model)
                response_field = create_response_model(type_=model)
                response_fields[additional_status_code] = response_field
        if response_fields:
            self.response_fields: Dict[Union[int, str], ma.Schema] = response_fields
        else:
            self.response_fields = {}

        self.endpoint_model = self.get_endpoint_model(
            self.path_format,
            endpoint,
            name=name,
            methods=self.methods,
            status_code=status_code,
            response_model=response_model,
            response_class=response_class,
            route=self,
        )

        self.app = request_response(get_request_handler(self.endpoint_model))


class APIRouter(routing.Router):

    def __init__(
        self,
        *args,
        tags: Optional[List[Union[str, Enum]]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(
            generate_unique_id,
        ),
        prefix: str = "",
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.tags: List[Union[str, Enum]] = tags or []
        self.default_response_class = default_response_class
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.responses = responses or {}
        self.callbacks = callbacks or []
        self.generate_unique_id_function = generate_unique_id_function
        self.prefix = prefix

    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_route(
                path,
                func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
            )
            return func

        return decorator

    def add_api_route(
        self,
        path: str,
        endpoint: Union[Callable[..., Any], APIHTTPEndpoint],
        *,
        methods: Optional[Union[Set[str], List[str]]] = None,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:

        current_tags = self.tags.copy()
        if tags:
            current_tags.extend(tags)

        if isinstance(endpoint, type(APIHTTPEndpoint)):
            # Ensure the functions are bound to a class instance
            # Currently all routes will share the same instance
            endpoint = endpoint()

            for method in endpoint.methods:
                endpoint_function = getattr(endpoint, method.lower())
                if hasattr(endpoint_function, 'endpoint_options'):
                    endpoint_options = endpoint_function.endpoint_options
                else:
                    endpoint_options = EndpointOptions()

                method_tags = current_tags.copy()
                if endpoint_options.tags:
                    method_tags.extend(endpoint_options.tags)

                route = APIRoute(
                    self.prefix + path,
                    endpoint_function,
                    methods=[method],
                    name=endpoint_options.name or name,
                    include_in_schema=endpoint_options.include_in_schema and include_in_schema and self.include_in_schema,
                    status_code=endpoint_options.status_code or status_code,
                    deprecated=endpoint_options.deprecated or deprecated or self.deprecated,
                    response_model=endpoint_options.response_model or response_model,
                    response_class=endpoint_options.response_class or response_class,
                    summary=endpoint_options.summary or summary,
                    description=endpoint_options.description or description,
                    response_description=endpoint_options.response_description or response_description,
                    responses=endpoint_options.responses or responses,
                    callbacks=endpoint_options.callbacks or callbacks,
                    operation_id=endpoint_options.operation_id or operation_id,
                    generate_unique_id_function=endpoint_options.generate_unique_id_function or generate_unique_id_function,
                    openapi_extra=endpoint_options.openapi_extra or openapi_extra,
                    tags=method_tags,
                )

                self.routes.append(route)

        else:
            route = APIRoute(
                self.prefix + path,
                endpoint,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema and self.include_in_schema,
                status_code=status_code,
                deprecated=deprecated or self.deprecated,
                response_model=response_model,
                response_class=response_class,
                summary=summary,
                description=description,
                response_description=response_description,
                responses=responses,
                callbacks=callbacks,
                operation_id=operation_id,
                generate_unique_id_function=generate_unique_id_function,
                openapi_extra=openapi_extra,
                tags=current_tags,
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
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
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
                deprecated=deprecated,
                response_model=response_model,
                response_class=response_class,
                summary=summary,
                description=description,
                response_description=response_description,
                responses=responses,
                callbacks=callbacks,
                operation_id=operation_id,
                generate_unique_id_function=generate_unique_id_function,
                openapi_extra=openapi_extra,
                tags=tags,
            )
            return func
        return decorator

    def add_api_websocket_route(
        self, path: str, endpoint: Callable[..., Any], name: Optional[str] = None,
    ) -> None:
        route = APIWebSocketRoute(
            self.prefix + path,
            endpoint=endpoint,
            name=name,
        )
        self.routes.append(route)

    def websocket(
        self, path: str, name: Optional[str] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_api_websocket_route(path, func, name=name)
            return func

        return decorator

    def websocket_route(
        self, path: str, name: Union[str, None] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_websocket_route(path, func, name=name)
            return func

        return decorator

    def include_router(
        self,
        router: "APIRouter",
        *,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
    ) -> None:
        if prefix:
            assert prefix.startswith("/"), "A path prefix must start with '/'"
            assert not prefix.endswith(
                "/",
            ), "A path prefix must not end with '/', as the routes will start with '/'"
        else:
            for r in router.routes:
                path = getattr(r, "path")  # noqa: B009
                name = getattr(r, "name", "unknown")
                if path is not None and not path:
                    raise Exception(
                        f"Prefix and path cannot be both empty (path operation: {name})",
                    )

        if responses is None:
            responses = {}
        for route in router.routes:
            if isinstance(route, APIRoute):
                combined_responses = {**responses, **route.responses}
                use_response_class = get_value_or_default(
                    route.response_class,
                    router.default_response_class,
                    default_response_class,
                    self.default_response_class,
                )
                current_tags = []
                if tags:
                    current_tags.extend(tags)
                if route.tags:
                    current_tags.extend(route.tags)
                current_callbacks = []
                if callbacks:
                    current_callbacks.extend(callbacks)
                if route.callbacks:
                    current_callbacks.extend(route.callbacks)
                current_generate_unique_id = get_value_or_default(
                    route.generate_unique_id_function,
                    router.generate_unique_id_function,
                    generate_unique_id_function,
                    self.generate_unique_id_function,
                )
                self.add_api_route(
                    prefix + route.path,
                    route.endpoint,
                    response_model=route.response_model,
                    status_code=route.status_code,
                    tags=current_tags,
                    summary=route.summary,
                    description=route.description,
                    response_description=route.response_description,
                    responses=combined_responses,
                    callbacks=current_callbacks,
                    deprecated=route.deprecated or deprecated or self.deprecated,
                    methods=route.methods,
                    operation_id=route.operation_id,
                    include_in_schema=(
                        route.include_in_schema
                        and self.include_in_schema
                        and include_in_schema
                    ),
                    response_class=use_response_class,
                    name=route.name,
                    openapi_extra=route.openapi_extra,
                    generate_unique_id_function=current_generate_unique_id,
                )
            elif isinstance(route, routing.Route):
                methods = list(route.methods or [])
                self.add_route(
                    prefix + route.path,
                    route.endpoint,
                    methods=methods,
                    include_in_schema=route.include_in_schema,
                    name=route.name,
                )
            elif isinstance(route, APIWebSocketRoute):
                self.add_api_websocket_route(
                    prefix + route.path, route.endpoint, name=route.name,
                )
            elif isinstance(route, routing.WebSocketRoute):
                self.add_websocket_route(
                    prefix + route.path, route.endpoint, name=route.name,
                )

        for handler in router.on_startup:
            self.add_event_handler("startup", handler)
        for handler in router.on_shutdown:
            self.add_event_handler("shutdown", handler)

    def get(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['GET'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def put(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['PUT'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def post(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['POST'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def delete(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['DELETE'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def options(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['OPTIONS'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def head(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['HEAD'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def patch(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['PATCH'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )

    def trace(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        response_model: Optional[Type[Any]] = None,
        response_class: Type[Response] = JSONResponse,
        # OpenAPI summary
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        # Sets the OpenAPI operationId to be used in your path operation
        operation_id: Optional[str] = None,
        # If operation_id is None, this function will be used to create one.
        generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
        # OpenAPI tags
        tags: Optional[List[Union[str, Enum]]] = None,
        # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        return self.api_route(
            path,
            methods=['TRACE'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            deprecated=deprecated,
            response_model=response_model,
            response_class=response_class,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            callbacks=callbacks,
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
            tags=tags,
        )
