import os
from enum import Enum
from logging import getLogger
from string import Template
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
)

from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import BaseRoute
from starlette.types import ASGIApp, Receive, Scope, Send

from starmallow.datastructures import Default
from starmallow.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from starmallow.endpoints import APIHTTPEndpoint
from starmallow.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from starmallow.exceptions import RequestValidationError, SchemaGenerationError
from starmallow.middleware import AsyncExitStackMiddleware
from starmallow.responses import JSONResponse
from starmallow.routing import APIRoute, APIRouter
from starmallow.schema_generator import SchemaGenerator
from starmallow.types import DecoratedCallable
from starmallow.utils import generate_unique_id

logger = getLogger(__name__)

class StarMallow(Starlette):

    def __init__(
        self,
        *args,
        debug: bool = False,
        routes: Optional[List[BaseRoute]] = None,
        middleware: Sequence[Middleware] = None,
        exception_handlers: Mapping[
            Any,
            Callable[
                [Request, Exception], Union[Response, Awaitable[Response]],
            ],
        ] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        lifespan: Callable[[Starlette], AsyncContextManager] = None,

        title: str = "StarMallow",
        description: str = "",
        version: str = "0.1.0",
        root_path: str = "",
        openapi_url: Optional[str] = "/openapi.json",
        openapi_tags: Optional[List[Dict[str, Any]]] = None,
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
        swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
        swagger_ui_parameters: Optional[Dict[str, Any]] = None,

        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,

        **kwargs,
    ) -> None:
        # The lifespan context function is a newer style that replaces
        # on_startup / on_shutdown handlers. Use one or the other, not both.
        assert lifespan is None or (
            on_startup is None and on_shutdown is None
        ), "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."

        self.debug = debug
        self.title = title
        self.description = description
        self.version = version
        self.root_path = root_path
        self.openapi_url = openapi_url
        self.openapi_tags = openapi_tags
        self.openapi_version = "3.0.2"
        self.openapi_schema: Optional[Dict[str, Any]] = None
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.swagger_ui_oauth2_redirect_url = swagger_ui_oauth2_redirect_url
        self.swagger_ui_init_oauth = swagger_ui_init_oauth
        self.swagger_ui_parameters = swagger_ui_parameters

        if self.openapi_url:
            assert self.title, "A title must be provided for OpenAPI, e.g.: 'My API'"
            assert self.version, "A version must be provided for OpenAPI, e.g.: '2.1.0'"

        self.state = State()
        self.router: APIRouter = APIRouter(
            routes=routes,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
        )
        self.exception_handlers = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.exception_handlers.setdefault(HTTPException, http_exception_handler)
        self.exception_handlers.setdefault(
            RequestValidationError, request_validation_exception_handler,
        )

        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: Union[ASGIApp, None] = None
        self.init_openapi()

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        error_handler = None
        exception_handlers: Dict[
            Any, Callable[[Request, Exception], Response],
        ] = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value

        middleware = (
            [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
            + self.user_middleware
            + [
                Middleware(
                    ExceptionMiddleware, handlers=exception_handlers, debug=debug,
                ),
                # Teardown all ResolvedParam contextmanagers
                Middleware(AsyncExitStackMiddleware),
            ]
        )

        app = self.router
        for cls, options in reversed(middleware):
            app = cls(app=app, **options)
        return app

    def openapi(self) -> Dict[str, Any]:
        if not self.openapi_schema:
            self.openapi_schema = SchemaGenerator(
                self.title,
                self.version,
                self.description,
                self.openapi_version,
            ).get_schema(self.routes)
        return self.openapi_schema

    def init_openapi(self):
        if self.openapi_url:
            async def openapi(req: Request) -> JSONResponse:
                try:
                    return JSONResponse(self.openapi())
                except Exception as e:
                    logger.exception('Failed to generate OpenAPI schema')
                    raise SchemaGenerationError() from e

            self.add_route(self.openapi_url, openapi, include_in_schema=False)

        if self.openapi_url and self.docs_url:
            async def swagger_ui_html(req: Request) -> HTMLResponse:
                root_path = req.scope.get("root_path", "").rstrip("/")
                openapi_url = root_path + self.openapi_url
                oauth2_redirect_url = self.swagger_ui_oauth2_redirect_url
                if oauth2_redirect_url:
                    oauth2_redirect_url = root_path + oauth2_redirect_url
                return get_swagger_ui_html(
                    openapi_url=openapi_url,
                    title=self.title + " - Swagger UI",
                    oauth2_redirect_url=oauth2_redirect_url,
                    init_oauth=self.swagger_ui_init_oauth,
                    swagger_ui_parameters=self.swagger_ui_parameters,
                )

            self.add_route(self.docs_url, swagger_ui_html, include_in_schema=False)

            if self.swagger_ui_oauth2_redirect_url:

                async def swagger_ui_redirect(req: Request) -> HTMLResponse:
                    return get_swagger_ui_oauth2_redirect_html()

                self.add_route(
                    self.swagger_ui_oauth2_redirect_url,
                    swagger_ui_redirect,
                    include_in_schema=False,
                )

        if self.openapi_url and self.redoc_url:
            async def redoc_html(req: Request) -> HTMLResponse:
                root_path = req.scope.get("root_path", "").rstrip("/")
                openapi_url = root_path + self.openapi_url
                return get_redoc_html(
                    openapi_url=openapi_url, title=self.title + " - ReDoc",
                )

            self.add_route(self.redoc_url, redoc_html, include_in_schema=False)

    def add_docs_route(self):
        def swagger_ui() -> HTMLResponse:
            with open(os.path.join(os.path.dirname(__file__), "templates/swagger_ui.html")) as f:
                content = Template(f.read()).substitute(title=self.title, schema_url=self.schema_url)

            return HTMLResponse(content)

        self.add_route(path=self.docs_url, route=swagger_ui, methods=["GET"], include_in_schema=False)

    def add_redoc_route(self):
        def redoc() -> HTMLResponse:
            with open(os.path.join(os.path.dirname(__file__), "templates/redoc.html")) as f:
                content = Template(f.read()).substitute(title=self.title, schema_url=self.schema_url)

            return HTMLResponse(content)

        self.add_route(path=self.redoc_url, route=redoc, methods=["GET"], include_in_schema=False)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.root_path:
            scope["root_path"] = self.root_path
        await super().__call__(scope, receive, send)

    def add_api_route(
        self,
        path: str,
        endpoint: Union[Callable[..., Any], APIHTTPEndpoint],
        *,
        methods: Optional[Union[Set[str], List[str]]] = None,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
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
        return self.router.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.api_route(
            path=path,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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

    def add_api_websocket_route(
        self, path: str, endpoint: Callable[..., Any], name: Optional[str] = None,
    ) -> None:
        self.router.add_api_websocket_route(path, endpoint, name=name)

    def websocket(
        self, path: str, name: Optional[str] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_api_websocket_route(path, func, name=name)
            return func

        return decorator

    def include_router(
        self,
        router: APIRouter,
        *,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        default_response_class: Type[Response] = Default(JSONResponse),
        generate_unique_id_function: Callable[[APIRoute], str] = Default(
            generate_unique_id,
        ),
    ) -> None:
        self.router.include_router(
            router,
            prefix=prefix,
            tags=tags,
            responses=responses,
            callbacks=callbacks,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            default_response_class=default_response_class,
            generate_unique_id_function=generate_unique_id_function,
        )

    def get(
        self,
        path: str,
        *,
        name: str = None,
        include_in_schema: bool = True,
        status_code: Optional[int] = None,
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
        return self.router.get(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.put(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.post(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.delete(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.options(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.head(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.patch(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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
        return self.router.trace(
            path,
            name=name,
            include_in_schema=include_in_schema,
            status_code=status_code,
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

    def websocket_route(
        self, path: str, name: Union[str, None] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.router.add_api_websocket_route(path, func, name=name)
            return func

        return decorator

    def on_event(
        self, event_type: str,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.router.on_event(event_type)

    def middleware(
        self, middleware_type: str,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_middleware(BaseHTTPMiddleware, dispatch=func)
            return func

        return decorator

    def exception_handler(
        self, exc_class_or_status_code: Union[int, Type[Exception]],
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_exception_handler(exc_class_or_status_code, func)
            return func

        return decorator
