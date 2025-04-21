from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute

from starmallow.datastructures import Default
from starmallow.responses import JSONResponse
from starmallow.types import DecoratedCallable
from starmallow.utils import generate_unique_id

if TYPE_CHECKING:  # pragma: nocover
    from starmallow.routing import APIRoute


@dataclass
class EndpointOptions:
    name: str | None = None
    include_in_schema: bool = True
    status_code: int | None = None
    middleware: Sequence[Middleware] | None = None
    deprecated: bool | None = None
    request_class: type[Request] = Request
    response_model: type[Any] | None = None
    response_class: type[Response] = JSONResponse
    # OpenAPI summary
    summary: str | None = None
    description: str | None = None
    response_description: str = "Successful Response"
    responses: dict[int | str, dict[str, Any]] | None = None
    callbacks: list[BaseRoute] | None = None
    # Sets the OpenAPI operationId to be used in your path operation
    operation_id: str | None = None
    # If operation_id is None, this function will be used to create one.
    generate_unique_id_function: Callable[["APIRoute"], str] = field(
        default_factory=lambda: Default(generate_unique_id),
    )
    # OpenAPI tags
    tags: list[str | Enum] | None = None
    # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
    openapi_extra: dict[str, Any] | None = None
    route_class: type["APIRoute"] | None = None


def route(
    *,
    name: str | None = None,
    include_in_schema: bool = True,
    status_code: int | None = None,
    middleware: Sequence[Middleware] | None = None,
    deprecated: bool | None = None,
    request_class: type[Request] = Default(Request),
    response_model: type[Any] | None = None,
    response_class: type[Response] = JSONResponse,
    # OpenAPI summary
    summary: str | None = None,
    description: str | None = None,
    response_description: str = "Successful Response",
    responses: dict[int | str, dict[str, Any]] | None = None,
    callbacks: list[BaseRoute] | None = None,
    # Sets the OpenAPI operationId to be used in your path operation
    operation_id: str | None = None,
    # If operation_id is None, this function will be used to create one.
    generate_unique_id_function: Callable[["APIRoute"], str] = Default(generate_unique_id),
    # OpenAPI tags
    tags: list[str | Enum] | None = None,
    # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
    openapi_extra: dict[str, Any] | None = None,
    route_class: type["APIRoute"] | None = None,
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    '''
        Intended to be used with APIHTTPEndpoint to override options on a per method basis
    '''
    def decorator(func: DecoratedCallable) -> DecoratedCallable:
        # Attach options to the function so we can call upon them when we process the class
        func.endpoint_options = EndpointOptions( # type: ignore
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
