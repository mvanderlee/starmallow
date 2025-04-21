import collections.abc
import datetime as dt
import inspect
import logging
import re
import uuid
import warnings
from collections.abc import Callable, Mapping, Sequence
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from dataclasses import is_dataclass
from decimal import Decimal
from enum import Enum
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    ForwardRef,
    NotRequired,
    Protocol,
    TypeGuard,
    TypeVar,
    Union,
    _eval_type,  # type: ignore
    get_args,
    get_origin,
)

import dpath
import marshmallow as ma
import marshmallow.fields as mf
import marshmallow_dataclass2.collection_field as collection_field
import typing_inspect
from marshmallow.validate import Equal, OneOf
from marshmallow_dataclass2 import class_schema, is_generic_alias_of_dataclass
from marshmallow_dataclass2.union_field import Union as UnionField
from starlette.responses import Response
from typing_inspect import is_final_type, is_generic_type, is_literal_type

from starmallow.concurrency import contextmanager_in_threadpool
from starmallow.datastructures import DefaultPlaceholder, DefaultType

if TYPE_CHECKING:  # pragma: nocover
    from starmallow.routing import APIRoute

logger = logging.getLogger(__name__)

status_code_ranges: dict[str, str] = {
    "1XX": "Information",
    "2XX": "Success",
    "3XX": "Redirection",
    "4XX": "Client Error",
    "5XX": "Server Error",
    "DEFAULT": "Default Response",
}

MARSHMALLOW_ITERABLES: tuple[type[mf.Field], ...] = (
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
    Any: mf.Raw,
}

PY_ITERABLES = [
    list,
    list,
    collections.abc.Sequence,
    Sequence,
    tuple,
    tuple,
    set,
    set,
    frozenset,
    frozenset,
    dict,
    dict,
    collections.abc.Mapping,
    Mapping,
]

T = TypeVar("T")


def get_model_field(model: Any, **kwargs) -> mf.Field | None:
    if model == inspect._empty:
        return None

    if is_marshmallow_dataclass(model):
        model = model.Schema

    if is_generic_alias_of_dataclass(model):
        model = class_schema(model)

    if is_marshmallow_schema(model):
        return mf.Nested(model if isinstance(model, ma.Schema) else model())

    if is_marshmallow_field_or_generic(model):
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
        subtyp = arguments[0] if arguments else Any
        return get_model_field(subtyp, **kwargs)

    # enumerations
    if not is_generic_type(model) and lenient_issubclass(model, Enum):
        return mf.Enum(model, **kwargs)

    # Union
    if typing_inspect.is_union_type(model):
        if typing_inspect.is_optional_type(model):
            kwargs["allow_none"] = kwargs.get("allow_none", True)
            kwargs["dump_default"] = kwargs.get("dump_default")
            if not kwargs.get("required"):
                kwargs["load_default"] = kwargs.get("load_default")
            kwargs.setdefault("required", False)

        arguments = get_args(model)
        subtypes = [t for t in arguments if t is not NoneType]  # type: ignore
        if len(subtypes) == 1:
            return get_model_field(model, **kwargs)

        union_types = []
        for subtyp in subtypes:
            field = get_model_field(subtyp, required=True)
            if field is not None:
                union_types.append((subtyp, field))

        return UnionField(union_types, **kwargs)

    origin = get_origin(model)
    if origin not in PY_ITERABLES:
        raise Exception(f'Unknown model type, model is {model}')

    arguments = get_args(model)
    if origin in (list, list):
        child_type = get_model_field(arguments[0])
        return mf.List(child_type, **kwargs) # type: ignore

    if origin in (collections.abc.Sequence, Sequence) or (
        origin in (tuple, tuple)
        and len(arguments) == 2
        and arguments[1] is Ellipsis
    ):
        child_type = get_model_field(arguments[0])
        return collection_field.Sequence(child_type, **kwargs) # type: ignore

    if origin in (set, set):
        child_type = get_model_field(arguments[0])
        return collection_field.Set(child_type, frozen=False, **kwargs) # type: ignore

    if origin in (frozenset, frozenset):
        child_type = get_model_field(arguments[0])
        return collection_field.Set(child_type, frozen=True, **kwargs) # type: ignore

    if origin in (tuple, tuple):
        child_types = tuple(
            get_model_field(arg)
            for arg in arguments
        )
        return mf.Tuple(child_types, **kwargs) # type: ignore

    if origin in (dict, dict, collections.abc.Mapping, Mapping):
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
    return get_origin(field) in (Union, UnionType) and type(None) in get_args(field)


def get_path_param_names(path: str) -> set[str]:
    return set(re.findall("{(.*?)}", path))


def generate_unique_id(route: "APIRoute") -> str:
    operation_id = route.name + route.path_format
    operation_id = re.sub("[^0-9a-zA-Z_]", "_", operation_id)
    assert route.methods
    # Sort to ensure that 'GET' always comes before 'HEAD'
    operation_id = operation_id + "_" + sorted(route.methods)[0].lower()
    return operation_id


class MaDataclassProtocol(Protocol):
    Schema: NotRequired[type[ma.Schema]]


def is_marshmallow_schema(obj: Any) -> TypeGuard[ma.Schema | type[ma.Schema]]:
    try:
        return (inspect.isclass(obj) and issubclass(obj, ma.Schema)) or isinstance(obj, ma.Schema)
    except TypeError:
        # This is a workaround for the case where obj is a generic type
        # and issubclass raises a TypeError.
        return False


def is_marshmallow_field(obj: Any) -> TypeGuard[mf.Field | type[mf.Field]]:
    try:
        return (inspect.isclass(obj) and issubclass(obj, mf.Field)) or isinstance(obj, mf.Field)
    except TypeError:
        # This is a workaround for the case where obj is a generic type
        # and issubclass raises a TypeError.
        return False


def is_marshmallow_field_or_generic(obj: Any) -> TypeGuard[mf.Field | type[mf.Field]]:
    try:
        return (
            (inspect.isclass(obj) and issubclass(obj, mf.Field))
            or isinstance(obj, mf.Field)
            or (
                isinstance(obj, typing_inspect.typingGenericAlias)
                and lenient_issubclass(get_origin(obj), mf.Field)
            )
        )
    except TypeError:
        # This is a workaround for the case where obj is a generic type
        # and issubclass raises a TypeError.
        return False

def is_marshmallow_dataclass(obj: MaDataclassProtocol | Any) -> TypeGuard[MaDataclassProtocol]:
    schema = getattr(obj, 'Schema', None)

    return is_dataclass(obj) and schema is not None and is_marshmallow_schema(schema)


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
    gen_kwargs: dict[str, Any],
) -> Any:
    if is_gen_callable(call):
        cm = contextmanager_in_threadpool(contextmanager(call)(**gen_kwargs))
    elif is_async_gen_callable(call):
        cm = asynccontextmanager(call)(**gen_kwargs)
    else:
        raise ValueError(f"Cannot solve generator for {call}")
    return await stack.enter_async_context(cm)


def lenient_issubclass(cls: Any, class_or_tuple: type[Any] | tuple[type[Any | UnionType], ...] | UnionType) -> bool:
    try:
        return isinstance(cls, type) and issubclass(cls, class_or_tuple)
    except TypeError:
        return False


def eq_marshmallow_fields(left: mf.Field | Any, right: mf.Field | Any) -> bool:
    '''
        Marshmallow Fields don't have an __eq__ functions.
        This compares them instead.
    '''
    if not (isinstance(left, mf.Field) and isinstance(right, mf.Field)):
        return False

    left_dict = left.__dict__.copy()
    left_dict.pop('_creation_index', None)
    right_dict = right.__dict__.copy()
    right_dict.pop('_creation_index', None)

    return left_dict == right_dict


def _dict_creator(current, segments, i, hints: Sequence | None = None):
    '''
        Create missing path components. Always create a dictionary.

        set(obj, segments, value) -> obj
    '''
    segment = segments[i]

    # Infer the type from the hints provided.
    if hints and i < len(hints):
        current[segment] = hints[i][1]()
    else:
        current[segment] = {}


def dict_safe_add(d: dict, path: str, value: Any):
    dpath.new(d, path, value, separator='.', creator=_dict_creator)


def deep_dict_update(main_dict: dict[Any, Any], update_dict: dict[Any, Any]) -> None:
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


def create_response_model(type_: type[Any] | Any | ma.Schema | mf.Field) -> mf.Field | None:
    if type_ in [inspect._empty, None] or (inspect.isclass(type_) and issubclass(type_, Response)):
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
) -> Any:
    """
    Pass items or `DefaultPlaceholder`s by descending priority.

    The first one to _not_ be a `DefaultPlaceholder` will be returned.

    Otherwise, the first item (a `DefaultPlaceholder`) will be returned.
    """
    items = (first_item, *extra_items)
    for item in items:
        if not isinstance(item, DefaultPlaceholder):
            return item

    if isinstance(first_item, DefaultPlaceholder):
        return first_item.value
    else:
        return first_item

def get_name(endpoint: Callable) -> str:
    if inspect.isroutine(endpoint) or inspect.isclass(endpoint):
        return endpoint.__qualname__
    return endpoint.__class__.__name__


# Functions that help resolve forward references like
# def foo(a: 'str') -> 'UnresolvedClass': pass
# inspect.signature returns the literal string instead of the actual type.
def get_typed_signature(call: Callable[..., Any]) -> inspect.Signature:
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param.annotation, globalns),
        )
        for param in signature.parameters.values()
    ]
    typed_signature = inspect.Signature(typed_params)
    return typed_signature


def get_typed_annotation(annotation: Any, globalns: dict[str, Any]) -> Any:
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_typed_return_annotation(call: Callable[..., T]) -> T | None:
    signature = inspect.signature(call)
    annotation = signature.return_annotation

    if annotation is inspect.Signature.empty:
        return None

    globalns = getattr(call, "__globals__", {})
    return get_typed_annotation(annotation, globalns)



def evaluate_forwardref(value: Any, globalns: dict[str, Any] | None, localns: dict[str, Any] | None) -> Any:
    """Behaves like typing._eval_type, except it won't raise an error if a forward reference can't be resolved."""
    if value is None:
        value = NoneType
    elif isinstance(value, str):
        value = ForwardRef(value, is_argument=False, is_class=True)

    try:
        return _eval_type(value, globalns, localns)  # type: ignore
    except NameError:
        # the point of this function is to be tolerant to this case
        return value
