from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

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
    name: str = None
    include_in_schema: bool = True
    status_code: Optional[int] = None
    deprecated: Optional[bool] = None
    response_model: Optional[Type[Any]] = None
    response_class: Type[Response] = JSONResponse
    # OpenAPI summary
    summary: Optional[str] = None
    description: Optional[str] = None
    response_description: str = "Successful Response"
    responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None
    callbacks: Optional[List[BaseRoute]] = None
    # Sets the OpenAPI operationId to be used in your path operation
    operation_id: Optional[str] = None
    # If operation_id is None, this function will be used to create one.
    generate_unique_id_function: Callable[["APIRoute"], str] = field(
        default_factory=lambda: Default(generate_unique_id),
    )
    # OpenAPI tags
    tags: Optional[List[Union[str, Enum]]] = None
    # Will be deeply merged with the automatically generated OpenAPI schema for the path operation.
    openapi_extra: Optional[Dict[str, Any]] = None


def route(
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
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    '''
        Intended to be used with APIHTTPEndpoint to override options on a per method basis
    '''
    def decorator(func: DecoratedCallable) -> DecoratedCallable:
        # Attach options to the function so we can call upon them when we process the class
        func.endpoint_options = EndpointOptions(
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
