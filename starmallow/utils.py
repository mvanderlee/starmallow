import inspect
import re
import warnings
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Generic, Union

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


class Undefined:
    '''Allows us to check if something is undefined vs None'''
    pass


def is_optional(field):
    return get_origin(field) is Union and type(None) in get_args(field)


def generate_operation_id_for_path(
    *, name: str, path: str, method: str
) -> str:  # pragma: nocover
    warnings.warn(
        "fastapi.utils.generate_operation_id_for_path() was deprecated, "
        "it is not used internally, and will be removed soon",
        DeprecationWarning,
        stacklevel=2,
    )
    operation_id = name + path
    operation_id = re.sub("[^0-9a-zA-Z_]", "_", operation_id)
    operation_id = operation_id + "_" + method.lower()
    return operation_id


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
