import uuid
from typing import Any, Callable, List, TypeVar

import marshmallow.fields as mf
from marshmallow_dataclass import NewType

import starmallow.fields as sf

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])

UUID = NewType('UUID', uuid.UUID, field=mf.UUID)
DelimitedListUUID = NewType('DelimitedListUUID', List[uuid.UUID], field=sf.DelimitedListUUID)
DelimitedListStr = NewType('DelimitedListStr', List[str], field=sf.DelimitedListStr)
DelimitedListInt = NewType('DelimitedListInt', List[int], field=sf.DelimitedListInt)

HttpUrl = NewType("HttpUrl", str, field=sf.HttpUrl)

# Aliases
UUIDType = UUID
