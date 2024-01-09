import collections.abc
import datetime as dt
import inspect
import logging
import re
import uuid
import warnings
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from dataclasses import is_dataclass
from decimal import Decimal
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    _GenericAlias,
    get_args,
    get_origin,
)

import dpath.util
import marshmallow as ma
import marshmallow.fields as mf
import marshmallow_dataclass.collection_field as collection_field
from marshmallow.validate import Equal, OneOf
from starlette.responses import Response
from typing_inspect import is_final_type, is_generic_type, is_literal_type

from starmallow.concurrency import contextmanager_in_threadpool
from starmallow.datastructures import DefaultPlaceholder, DefaultType

if TYPE_CHECKING:  # pragma: nocover
    from starmallow.routing import APIRoute

logger = logging.getLogger(__name__)

status_code_ranges: Dict[str, str] = {
    "1XX": "Information",
    "2XX": "Success",
    "3XX": "Redirection",
    "4XX": "Client Error",
    "5XX": "Server Error",
    "DEFAULT": "Default Response",
}

MARSHMALLOW_ITERABLES: Tuple[mf.Field] = (
    mf.Dict,
    mf.List,
    mf.Mapping,
    mf.Tuple,
    collection_field.Sequence,
    collection_field.Set,
)

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

PY_ITERABLES = [
    list,
    List,
    collections.abc.Sequence,
    Sequence,
    tuple,
    Tuple,
    set,
    Set,
    frozenset,
    FrozenSet,
    dict,
    Dict,
    collections.abc.Mapping,
    Mapping,
]


def get_model_field(model: Any, **kwargs) -> mf.Field:
    if model == inspect._empty:
        return None

    if is_marshmallow_dataclass(model):
        model = model.Schema

    if is_marshmallow_schema(model):
        return mf.Nested(model if isinstance(model, ma.Schema) else model())

    if is_marshmallow_field(model):
        return model if isinstance(model, mf.Field) else model()

    # Native Python handling
    if model in PY_TO_MF_MAPPING:
        return PY_TO_MF_MAPPING[model](**kwargs)

    if is_literal_type(model):
        arguments = get_args(model)
        return mf.Raw(
            validate=(
                Equal(arguments[0])
                if len(arguments) == 1
                else OneOf(arguments)
            ),
            **kwargs,
        )

    if is_final_type(model):
        arguments = get_args(model)
        if arguments:
            subtyp = arguments[0]
        else:
            subtyp = Any
        return get_model_field(subtyp, **kwargs)

    # enumerations
    if not is_generic_type(model) and lenient_issubclass(model, Enum):
        return mf.Enum(model, **kwargs)

    origin = get_origin(model)
    if origin not in PY_ITERABLES:
        raise Exception(f'Unknown model type, model is {model}')

    arguments = get_args(model)
    if origin in (list, List):
        child_type = get_model_field(arguments[0])
        return mf.List(child_type, **kwargs)

    if origin in (collections.abc.Sequence, Sequence) or (
        origin in (tuple, Tuple)
        and len(arguments) == 2
        and arguments[1] is Ellipsis
    ):
        child_type = get_model_field(arguments[0])
        return collection_field.Sequence(child_type, **kwargs)

    if origin in (set, Set):
        child_type = get_model_field(arguments[0])
        return collection_field.Set(child_type, frozen=False, **kwargs)

    if origin in (frozenset, FrozenSet):
        child_type = get_model_field(arguments[0])
        return collection_field.Set(child_type, frozen=True, **kwargs)

    if origin in (tuple, Tuple):
        child_types = (
            get_model_field(arg)
            for arg in arguments
        )
        return mf.Tuple(child_types, **kwargs)

    if origin in (dict, Dict, collections.abc.Mapping, Mapping):
        key_type = get_model_field(arguments[0])
        value_type = get_model_field(arguments[1])
        return mf.Dict(keys=key_type, values=value_type, **kwargs)


def is_body_allowed_for_status_code(status_code: int | str | None) -> bool:
    if status_code is None:
        return True
    # Ref: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#patterned-fields-1
    if status_code in {
        "default",
        "1XX",
        "2XX",
        "3XX",
        "4XX",
        "5XX",
    }:
        return True
    current_status_code = int(status_code)
    return not (current_status_code < 200 or current_status_code in {204, 304})


def is_optional(field):
    return get_origin(field) is Union and type(None) in get_args(field)


def get_path_param_names(path: str) -> Set[str]:
    return set(re.findall("{(.*?)}", path))


def generate_unique_id(route: "APIRoute") -> str:
    operation_id = route.name + route.path_format
    operation_id = re.sub("[^0-9a-zA-Z_]", "_", operation_id)
    assert route.methods
    # Sort to ensure that 'GET' always comes before 'HEAD'
    operation_id = operation_id + "_" + sorted(route.methods)[0].lower()
    return operation_id


def is_marshmallow_schema(obj):
    return (inspect.isclass(obj) and issubclass(obj, ma.Schema)) or isinstance(obj, ma.Schema)


def is_marshmallow_field(obj):
    return (inspect.isclass(obj) and issubclass(obj, mf.Field)) or isinstance(obj, mf.Field)


def is_marshmallow_dataclass(obj):
    return is_dataclass(obj) and hasattr(obj, 'Schema') and is_marshmallow_schema(obj.Schema)


def is_async_gen_callable(call: Callable[..., Any]) -> bool:
    if inspect.isasyncgenfunction(call):
        return True
    dunder_call = getattr(call, "__call__", None)  # noqa: B004
    return inspect.isasyncgenfunction(dunder_call)


def is_gen_callable(call: Callable[..., Any]) -> bool:
    if inspect.isgeneratorfunction(call):
        return True
    dunder_call = getattr(call, "__call__", None)  # noqa: B004
    return inspect.isgeneratorfunction(dunder_call)


async def solve_generator(
    *,
    call: Callable[..., Any],
    stack: AsyncExitStack,
    gen_kwargs: Dict[str, Any],
) -> Any:
    if is_gen_callable(call):
        cm = contextmanager_in_threadpool(contextmanager(call)(**gen_kwargs))
    elif is_async_gen_callable(call):
        cm = asynccontextmanager(call)(**gen_kwargs)
    return await stack.enter_async_context(cm)


def lenient_issubclass(cls: Any, class_or_tuple: Union[Type[Any], Tuple[Type[Any], ...], None]) -> bool:
    try:
        return isinstance(cls, type) and issubclass(cls, class_or_tuple)  # type: ignore[arg-type]
    except TypeError:
        if isinstance(cls, _GenericAlias):
            return False
        raise  # pragma: no cover


def eq_marshmallow_fields(left: mf.Field, right: mf.Field) -> bool:
    '''
        Marshmallow Fields don't have an __eq__ functions.
        This compares them instead.
    '''
    left_dict = left.__dict__.copy()
    left_dict.pop('_creation_index', None)
    right_dict = right.__dict__.copy()
    right_dict.pop('_creation_index', None)

    return left_dict == right_dict


def __dict_creator__(current, segments, i, hints=()):
    '''
        Create missing path components. Always create a dictionary.

        set(obj, segments, value) -> obj
    '''
    segment = segments[i]

    # Infer the type from the hints provided.
    if i < len(hints):
        current[segment] = hints[i][1]()
    else:
        current[segment] = {}


def dict_safe_add(d: Dict, path: str, value: Any):
    dpath.new(d, path, value, separator='.', creator=__dict_creator__)


def deep_dict_update(main_dict: Dict[Any, Any], update_dict: Dict[Any, Any]) -> None:
    for key, value in update_dict.items():
        if (
            key in main_dict
            and isinstance(main_dict[key], dict)
            and isinstance(value, dict)
        ):
            deep_dict_update(main_dict[key], value)
        elif (
            key in main_dict
            and isinstance(main_dict[key], list)
            and isinstance(update_dict[key], list)
        ):
            main_dict[key] = main_dict[key] + update_dict[key]
        else:
            main_dict[key] = value


def create_response_model(type_: Type[Any]) -> ma.Schema | mf.Field | None:
    if type_ in [inspect._empty, None] or issubclass(type_, Response):
        return None

    field = get_model_field(type_)
    if field is not None:
        return field
    else:
        warnings.warn(f"Can't create response model for {type_}")

        return None


def get_value_or_default(
    first_item: DefaultPlaceholder | DefaultType,
    *extra_items: DefaultPlaceholder | DefaultType,
) -> DefaultPlaceholder | DefaultType:
    """
    Pass items or `DefaultPlaceholder`s by descending priority.

    The first one to _not_ be a `DefaultPlaceholder` will be returned.

    Otherwise, the first item (a `DefaultPlaceholder`) will be returned.
    """
    items = (first_item,) + extra_items
    for item in items:
        if not isinstance(item, DefaultPlaceholder):
            return item
    return first_item


def get_name(endpoint: Callable) -> str:
    if inspect.isroutine(endpoint) or inspect.isclass(endpoint):
        return endpoint.__qualname__
    return endpoint.__class__.__name__
