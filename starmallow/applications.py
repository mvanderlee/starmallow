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
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute

from starmallow.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from starmallow.exceptions import RequestValidationError
from starmallow.routing import APIRoute, APIRouter
from starmallow.schema_generator import SchemaGenerator
from starmallow.types import DecoratedCallable
from starmallow.utils import generate_unique_id


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
                [Request, Exception], Union[Response, Awaitable[Response]]
            ],
        ] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        lifespan: Callable[[Starlette], AsyncContextManager] = None,

        title: str = "FastAPI",
        description: str = "",
        version: str = "0.1.0",
        openapi_url: Optional[str] = "/openapi.json",
        openapi_tags: Optional[List[Dict[str, Any]]] = None,
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",

        **kwargs,
    ) -> None:
        # The lifespan context function is a newer style that replaces
        # on_startup / on_shutdown handlers. Use one or the other, not both.
        assert lifespan is None or (
            on_startup is None and on_shutdown is None
        ), "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."

        self._debug = debug
        self.title = title
        self.description = description
        self.version = version
        self.openapi_url = openapi_url
        self.openapi_tags = openapi_tags
        self.openapi_version = "3.0.2"
        self.openapi_schema: Optional[Dict[str, Any]] = None
        self.docs_url = docs_url
        self.redoc_url = redoc_url

        if self.openapi_url:
            assert self.title, "A title must be provided for OpenAPI, e.g.: 'My API'"
            assert self.version, "A version must be provided for OpenAPI, e.g.: '2.1.0'"

        self.state = State()
        self.router: APIRouter = APIRouter(
            routes=routes,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
        )
        self.exception_handlers = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.exception_handlers.setdefault(HTTPException, http_exception_handler)
        self.exception_handlers.setdefault(
            RequestValidationError, request_validation_exception_handler
        )

        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack = self.build_middleware_stack()
        self.init_openapi()

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
                return JSONResponse(self.openapi())

            self.add_route(self.openapi_url, openapi, include_in_schema=False)

        if self.openapi_url and self.docs_url:
            pass

        if self.openapi_url and self.redoc_url:
            pass

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
        return self.router.add_api_route(
            path=path,
            endpoint=endpoint,
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
        return self.router.api_route(
            path=path,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
        generate_unique_id_function: Callable[[APIRoute], str] = generate_unique_id,
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
            operation_id=operation_id,
            generate_unique_id_function=generate_unique_id_function,
            openapi_extra=openapi_extra,
        )
