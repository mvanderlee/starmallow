import inspect
import re
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Any, Dict, Generic, Union

import dpath.util
import marshmallow as ma
import marshmallow.fields as mf

if TYPE_CHECKING:  # pragma: nocover
    from starmallow.routing import APIRoute

# Python >= 3.8  - Source: https://stackoverflow.com/a/58841311/3776765
try:
    from typing import get_args, get_origin
# Compatibility
except ImportError:
    get_args = lambda t: getattr(t, '__args__', ()) if t is not Generic else Generic
    get_origin = lambda t: getattr(t, '__origin__', None)


def is_optional(field):
    return get_origin(field) is Union and type(None) in get_args(field)


def generate_unique_id(route: "APIRoute") -> str:
    operation_id = route.name + route.path_format
    operation_id = re.sub("[^0-9a-zA-Z_]", "_", operation_id)
    assert route.methods
    operation_id = operation_id + "_" + list(route.methods)[0].lower()
    return operation_id


def is_marshmallow_schema(obj):
    return (inspect.isclass(obj) and issubclass(obj, ma.Schema)) or isinstance(obj, ma.Schema)


def is_marshmallow_field(obj):
    return (inspect.isclass(obj) and issubclass(obj, mf.Field)) or isinstance(obj, mf.Field)


def is_marshmallow_dataclass(obj):
    return is_dataclass(obj) and hasattr(obj, 'Schema') and is_marshmallow_schema(obj.Schema)


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
    dpath.util.new(d, path, value, separator='.', creator=__dict_creator__)
