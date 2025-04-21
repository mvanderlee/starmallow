import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypeVar

import marshmallow.fields as mf
from starlette.websockets import WebSocket

import starmallow.fields as sf
from starmallow.delimited_field import DelimitedList
from starmallow.endpoints import APIHTTPEndpoint

EndpointCallable = Callable[..., Awaitable[Any] | Any]
WebSocketEndpointCallable = Callable[[WebSocket], Awaitable[None]]
DecoratedCallable = TypeVar("DecoratedCallable", bound=EndpointCallable | type[APIHTTPEndpoint])

UUID = Annotated[uuid.UUID, mf.UUID]
DelimitedListUUID = Annotated[list[uuid.UUID], DelimitedList[mf.UUID]]
DelimitedListStr = Annotated[list[str], DelimitedList[mf.String]]
DelimitedListInt = Annotated[list[int], DelimitedList[mf.Integer]]

HttpUrl = Annotated[str, sf.HttpUrl]

# Aliases
UUIDType = UUID
