import uuid
from typing import Any, Callable, List, TypeVar

import marshmallow.fields as mf
from marshmallow_dataclass import NewType

from .delimited_field import DelimitedList

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])

UUID = NewType('UUID', uuid.UUID, field=mf.UUID)
DelimitedListUUID = NewType('DelimitedListUUID', List[uuid.UUID], field=lambda *args, **kwargs: DelimitedList(mf.UUID(), *args, **kwargs))
DelimitedListStr = NewType('DelimitedListStr', List[str], field=lambda *args, **kwargs: DelimitedList(mf.String(), *args, **kwargs))
DelimitedListInt = NewType('DelimitedListInt', List[int], field=lambda *args, **kwargs: DelimitedList(mf.Integer(), *args, **kwargs))

# Aliases
UUIDType = UUID
