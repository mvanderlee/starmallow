import inspect
import re
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Any, Dict, Generic, Set, Tuple, Type, Union

import dpath.util
import marshmallow as ma
import marshmallow.fields as mf
import marshmallow_dataclass.collection_field as collection_field

from starmallow.datastructures import DefaultPlaceholder, DefaultType

if TYPE_CHECKING:  # pragma: nocover
    from starmallow.routing import APIRoute

# Python >= 3.8  - Source: https://stackoverflow.com/a/58841311/3776765
try:
    from typing import get_args, get_origin
# Compatibility
except ImportError:
    get_args = lambda t: getattr(t, '__args__', ()) if t is not Generic else Generic
    get_origin = lambda t: getattr(t, '__origin__', None)


MARSHMALLOW_ITERABLES: Tuple[mf.Field] = (
    mf.Dict,
    mf.List,
    mf.Mapping,
    mf.Tuple,
    collection_field.Sequence,
    collection_field.Set,
)


status_code_ranges: Dict[str, str] = {
    "1XX": "Information",
    "2XX": "Success",
    "3XX": "Redirection",
    "4XX": "Client Error",
    "5XX": "Server Error",
    "DEFAULT": "Default Response",
}


def is_body_allowed_for_status_code(status_code: Union[int, str, None]) -> bool:
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


def create_response_model(type_: Type[Any]) -> ma.Schema | None:
    if is_marshmallow_dataclass(type_):
        type_ = type_.Schema

    return type_() if is_marshmallow_schema(type_) else None


def get_value_or_default(
    first_item: Union[DefaultPlaceholder, DefaultType],
    *extra_items: Union[DefaultPlaceholder, DefaultType],
) -> Union[DefaultPlaceholder, DefaultType]:
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
