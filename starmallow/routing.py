import asyncio
import functools
import inspect
import logging
from enum import Enum, IntEnum
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

import marshmallow as ma
from starlette import routing
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import (
    BaseRoute,
    Match,
    compile_path,
    is_async_callable,
    wrap_app_handling_exceptions,
)
from starlette.status import WS_1008_POLICY_VIOLATION
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from starmallow.constants import STATUS_CODES_WITH_NO_BODY
from starmallow.datastructures import Default, DefaultPlaceholder
from starmallow.decorators import EndpointOptions
from starmallow.endpoint import EndpointMixin, EndpointModel
from starmallow.endpoints import APIHTTPEndpoint
from starmallow.exceptions import RequestValidationError, WebSocketRequestValidationError
from starmallow.request_resolver import resolve_params
from starmallow.responses import JSONResponse
from starmallow.types import DecoratedCallable
from starmallow.utils import (
    create_response_model,
    generate_unique_id,
    get_name,
    get_typed_signature,
    get_value_or_default,
    is_body_allowed_for_status_code,
    is_marshmallow_field,
    is_marshmallow_schema,
)
from starmallow.websockets import APIWebSocket

logger = logging.getLogger(__name__)


async def run_endpoint_function(
    endpoint_model: EndpointModel,
    values: Dict[str, Any],
) -> Any:
    assert endpoint_model.call is not None, "endpoint_model.call must be a function"

    kwargs = {
        name: values[name]
        for name in get_typed_signature(endpoint_model.call).parameters
        if name in values
    }

    if asyncio.iscoroutinefunction(endpoint_model.call):
        return await endpoint_model.call(**kwargs)
    else:
        return await run_in_threadpool(endpoint_model.call, **kwargs)


def request_response(
    func: Callable[[Request], Union[Awaitable[Response], Response]],
    request_class: Type[Request],
) -> ASGIApp:
    """
    Takes a function or coroutine `func(request) -> response`,
    and returns an ASGI application.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        request = request_class(scope, receive, send)

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            if is_async_callable(func):
                response = await func(request)
            else:
                response = await run_in_threadpool(func, request)
            await response(scope, receive, send)

        try:
            await wrap_app_handling_exceptions(app, request)(scope, receive, send)
        except RuntimeError as e:
            # This likely means that the exception was thrown by a background task
            # after the response has been successfully send to the client
            logger.exception(f'Runtime error occurred: {e}')

    return app


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
        values, errors, background_tasks, sub_response = await resolve_params(request, endpoint_model.params)

        if errors:
            raise RequestValidationError(errors)

        raw_response = await run_endpoint_function(
            endpoint_model,
            values,
        )
        if isinstance(raw_response, Response):
            if raw_response.background is None:
                raw_response.background = background_tasks
            return raw_response

        response_data = raw_response
        if is_marshmallow_schema(endpoint_model.response_model):
            response_data = endpoint_model.response_model.dump(raw_response)
        elif is_marshmallow_field(endpoint_model.response_model):
            response_data = endpoint_model.response_model._serialize(raw_response, attr='response', obj=raw_response)

        response_args: Dict[str, Any] = {"background": background_tasks}
        if endpoint_model.status_code is not None:
            response_args["status_code"] = endpoint_model.status_code
        if sub_response.status_code:
            response_args["status_code"] = sub_response.status_code

        response = endpoint_model.response_class(response_data, **response_args)
        if not is_body_allowed_for_status_code(response.status_code):
            response.body = b""
        response.headers.raw.extend(sub_response.headers.raw)

        return response

    return app


def get_websocker_hander(
    endpoint_model: EndpointModel,
) -> Callable[[Request], Coroutine[Any, Any, Response]]:
    assert endpoint_model.call is not None, "dependant.call must be a function"

    async def app(websocket: WebSocket) -> None:
        values, errors, _, _ = await resolve_params(websocket, endpoint_model.params)

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
        middleware: Sequence[Middleware] | None = None,
        status_code: Optional[int] = None,
        deprecated: Optional[bool] = None,
        request_class: Union[Type[Request], DefaultPlaceholder] = Default(
            Request,
        ),
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
            self.app = request_response(endpoint, request_class)
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
        self.summary = summary
        self.operation_id = operation_id
        self.callbacks = callbacks
        self.tags = tags or []
        self.responses = responses or {}
        self.openapi_extra = openapi_extra

        if isinstance(request_class, DefaultPlaceholder):
            self.request_class: Request = request_class.value
        else:
            self.request_class = request_class

        if isinstance(response_class, DefaultPlaceholder):
            self.response_class: Response = response_class.value
        else:
            self.response_class = response_class

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
            self.endpoint,
            name=self.name,
            methods=self.methods,
            status_code=self.status_code,
            response_model=self.response_model,
            response_class=self.response_class,
            route=self,
        )

        self.middleware = middleware  # Store for include_router
        self.app = request_response(self.get_route_handler(), self.request_class)
        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(app=self.app, *args, **kwargs)  # noqa: B026

    def get_route_handler(self):
        return get_request_handler(self.endpoint_model)


class APIRouter(routing.Router):

    def __init__(
        self,
        *args,
        tags: Optional[List[Union[str, Enum]]] = None,
        default_request_class: Type[Request] = Default(Request),
        default_response_class: Type[Response] = Default(JSONResponse),
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(
            generate_unique_id,
        ),
        prefix: str = "",
        route_class: Optional[Type[APIRoute]] = APIRoute,
        middleware: Sequence[Middleware] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, middleware=middleware, **kwargs)

        self.tags: List[Union[str, Enum]] = tags or []
        self.default_request_class = default_request_class
        self.default_response_class = default_response_class
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.responses = responses or {}
        self.callbacks = callbacks or []
        self.generate_unique_id_function = generate_unique_id_function
        self.prefix = prefix
        self.route_class = route_class
        self.middleware = middleware

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
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ) -> None:
        route_class = route_class or self.route_class

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

                endpoint_route_class = endpoint_options.route_class or route_class
                route = endpoint_route_class(
                    self.prefix + path,
                    endpoint_function,
                    methods=[method],
                    name=endpoint_options.name or name,
                    include_in_schema=endpoint_options.include_in_schema and include_in_schema and self.include_in_schema,
                    status_code=endpoint_options.status_code or status_code,
                    middleware=endpoint_options.middleware or middleware,
                    deprecated=endpoint_options.deprecated or deprecated or self.deprecated,
                    request_class=endpoint_options.request_class or request_class,
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
            route = route_class(
                self.prefix + path,
                endpoint,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema and self.include_in_schema,
                status_code=status_code,
                middleware=middleware,
                deprecated=deprecated or self.deprecated,
                request_class=request_class,
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
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_api_route(
                path,
                func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
                status_code=status_code,
                middleware=middleware,
                deprecated=deprecated,
                request_class=request_class,
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
                route_class=route_class,
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
        default_request_class: Type[Request] = Default(Request),
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
                use_request_class = get_value_or_default(
                    route.request_class,
                    router.default_request_class,
                    default_request_class,
                    self.default_request_class,
                )
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

                middleware = []
                if router.middleware:
                    middleware.extend(router.middleware)
                if route.middleware:
                    middleware.extend(route.middleware)

                self.add_api_route(
                    prefix + route.path,
                    route.endpoint,
                    response_model=route.response_model,
                    status_code=route.status_code,
                    middleware=middleware,
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
                    request_class=use_request_class,
                    response_class=use_response_class,
                    name=route.name,
                    openapi_extra=route.openapi_extra,
                    generate_unique_id_function=current_generate_unique_id,
                    route_class=route.__class__,
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
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['GET'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def put(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['PUT'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def post(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['POST'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def delete(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['DELETE'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def options(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['OPTIONS'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def head(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['HEAD'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def patch(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['PATCH'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )

    def trace(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
        middleware: Sequence[Middleware] | None = None,
        deprecated: Optional[bool] = None,
        request_class: Type[Request] = Default(Request),
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
        route_class: Optional[Type[APIRoute]] = None,
    ):
        return self.api_route(
            path,
            methods=['TRACE'],
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
            middleware=middleware,
            deprecated=deprecated,
            request_class=request_class,
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
            route_class=route_class,
        )
