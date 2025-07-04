# Copied from webargs, but allows for None values.

"""Field classes.

Includes all fields from `marshmallow.fields` in addition to a custom
`Nested` field and `DelimitedList`.

All fields can optionally take a special `location` keyword argument, which
tells webargs where to parse the request argument from.

.. code-block:: python

    args = {
        "active": fields.Bool(location="query"),
        "content_type": fields.Str(data_key="Content-Type", location="headers"),
    }
"""
from typing import Any, ClassVar, Generic, Protocol, TypeVar, TypeVarTuple

import marshmallow as ma

from .generics import get_orig_class

T = TypeVar('T', bound=ma.fields.Field | type[ma.fields.Field])
Ts = TypeVarTuple('Ts')  # Bound is not supported, bound=ma.fields.Field | type[ma.fields.Field]


class _SupportListOrTupleField(Protocol):
    delimiter: str

    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs) -> list | tuple: ...
    def _deserialize(self, value, attr: str | None, data, **kwargs): ...
    def make_error(self, key: str, **kwargs) -> ma.ValidationError: ...


class DelimitedFieldMixin:
    """
    This is a mixin class for subclasses of ma.fields.List and ma.fields.Tuple
    which split on a pre-specified delimiter. By default, the delimiter will be ","

    Because we want the MRO to reach this class before the List or Tuple class,
    it must be listed first in the superclasses

    For example, a DelimitedList-like type can be defined like so:

    >>> class MyDelimitedList(DelimitedFieldMixin, ma.fields.List):
    >>>     pass
    """

    delimiter: str = ","
    # delimited fields set is_multiple=False for webargs.core.is_multiple
    is_multiple: bool = False

    def _serialize(self: _SupportListOrTupleField, value: Any, attr: str | None, obj: Any, **kwargs):
        # serializing will start with parent-class serialization, so that we correctly
        # output lists of non-primitive types, e.g. DelimitedList(DateTime)
        if value is not None:
            return self.delimiter.join(
                format(each) if each is not None else ''
                for each in super()._serialize(value, attr, obj, **kwargs)
            )

    def _deserialize(self: _SupportListOrTupleField, value, attr: str | None, data, **kwargs):
        if value is not None:
            # attempting to deserialize from a non-string source is an error
            if not isinstance(value, str):
                raise self.make_error("invalid")

            values = value.split(self.delimiter)  # if value else []
            return super()._deserialize(values, attr, data, **kwargs)


class DelimitedList(DelimitedFieldMixin, ma.fields.List, Generic[T]):  # type: ignore
    """A field which is similar to a List, but takes its input as a delimited
    string (e.g. "foo,bar,baz").

    Like List, it can be given a nested field type which it will use to
    de/serialize each element of the list.

    :param Field cls_or_instance: A field class or instance.
    :param str delimiter: Delimiter between values.
    """

    default_error_messages: ClassVar[dict[str, str]] = {"invalid": "Not a valid delimited list."}

    def __init__(
        self,
        *,
        delimiter: str | None = None,
        **kwargs,
    ):
        cls_or_instance = get_orig_class(self).__args__[0]
        self.delimiter = delimiter or self.delimiter
        super().__init__(cls_or_instance, **kwargs)


class DelimitedTuple(DelimitedFieldMixin, ma.fields.Tuple, Generic[*Ts]):  # type: ignore
    """A field which is similar to a Tuple, but takes its input as a delimited
    string (e.g. "foo,bar,baz").

    Like Tuple, it can be given a tuple of nested field types which it will use to
    de/serialize each element of the tuple.

    :param Iterable[Field] tuple_fields: An iterable of field classes or instances.
    :param str delimiter: Delimiter between values.
    """

    default_error_messages: ClassVar[dict[str, str]] = {"invalid": "Not a valid delimited tuple."}

    def __init__(
        self,
        *,
        delimiter: str | None = None,
        **kwargs,
    ):
        cls_or_instances = get_orig_class(self).__args__
        self.delimiter = delimiter or self.delimiter
        super().__init__(cls_or_instances, **kwargs)
