import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

logger = logging.getLogger(__name__)

def json_default(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif is_dataclass(obj):
        return asdict(obj)
    elif isinstance(obj, Enum):
        return obj.name


class JSONEncoder(json.JSONEncoder):
    '''
        Simple JSONEncoder that handles additional types
    '''
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.hex()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, Enum):
            return obj.name
        # If a class and not any of the default types, automatically try to parse the object's attributes
        elif not isinstance(obj, (str, int, float, type(None), list, dict)):
            try:
                data = vars(obj)
            except Exception:
                logger.exception(f'Failed to encode {obj}')
                return None
            else:
                return data
        return json.JSONEncoder.default(self, obj)

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> from json.encoder import JSONEncoder
        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, str):
            if self.ensure_ascii:
                return json.encoder.encode_basestring_ascii(o)
            else:
                return json.encoder.encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        # StarMallow: We attempt default behaviour, which will use the c_make_encoder for performance
        # Only if it fails with the keys error will we force our own make_encoder.
        # this will preserve the C performance for ~95% of the usecases.
        # The remainder would be a little slower, but acceptably so.
        try:
            chunks = self.iterencode(o, _one_shot=True)
            if not isinstance(chunks, (list, tuple)):
                chunks = list(chunks)
        except TypeError as e:
            if e.args[0].startswith('keys must be '):
                chunks = self.iterencode(o, _one_shot=True, use_python_iterencode=True)
                if not isinstance(chunks, (list, tuple)):
                    chunks = list(chunks)
            else:
                raise

        return ''.join(chunks)

    def iterencode(self, o, _one_shot=False, use_python_iterencode=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = json.encoder.encode_basestring_ascii
        else:
            _encoder = json.encoder.encode_basestring

        def floatstr(
            o,
            allow_nan=self.allow_nan,
            _repr=float.__repr__,
            _inf=json.encoder.INFINITY,
            _neginf=-json.encoder.INFINITY,
        ):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(f"Out of range float values are not JSON compliant: {repr(o)}")

            return text

        if (
            _one_shot
            and json.encoder.c_make_encoder is not None
            and self.indent is None
            and not use_python_iterencode
        ):
            _iterencode = json.encoder.c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan,
            )
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot,
            )
        return _iterencode(o, 0)


def _make_iterencode(
    markers,
    _default,
    _encoder,
    _indent,
    _floatstr,
    _key_separator,
    _item_separator,
    _sort_keys,
    _skipkeys,
    _one_shot,
    ## HACK: hand-optimized bytecode; turn globals into locals
    ValueError=ValueError,
    dict=dict,
    float=float,
    id=id,
    int=int,
    isinstance=isinstance,
    list=list,
    str=str,
    tuple=tuple,
    _intstr=int.__repr__,
):

    if _indent is not None and not isinstance(_indent, str):
        _indent = ' ' * _indent

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + _indent * _current_indent_level
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, str):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, int):
                # Subclasses of int/float may override __repr__, but we still
                # want to encode them as integers/floats in JSON. One example
                # within the standard library is IntEnum.
                yield buf + _intstr(value)
            elif isinstance(value, float):
                # see comment above for int
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + _indent * _current_indent_level
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + _indent * _current_indent_level
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = sorted(dct.items())
        else:
            items = dct.items()
        for key, value in items:
            if isinstance(key, str):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                # see comment for int/float in _make_iterencode
                key = _floatstr(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif isinstance(key, int):
                # see comment for int/float in _make_iterencode
                key = _intstr(key)
            # Custom key handling
            elif isinstance(key, UUID):
                key = str(key)
            elif isinstance(key, Enum):
                key = key.name
            elif isinstance(key, (datetime, date)):
                key = key.isoformat()
            elif _skipkeys:
                continue
            else:
                raise TypeError(
                    f'keys must be str, int, float, bool, UUID, Enum, date, datetime, or None, '
                    f'not {key.__class__.__name__}',
                )
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, str):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, int):
                # see comment for int/float in _make_iterencode
                yield _intstr(value)
            elif isinstance(value, float):
                # see comment for int/float in _make_iterencode
                yield _floatstr(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + _indent * _current_indent_level
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, str):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, int):
            # see comment for int/float in _make_iterencode
            yield _intstr(o)
        elif isinstance(o, float):
            # see comment for int/float in _make_iterencode
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            yield from _iterencode_list(o, _current_indent_level)
        elif isinstance(o, dict):
            yield from _iterencode_dict(o, _current_indent_level)
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            yield from _iterencode(o, _current_indent_level)
            if markers is not None:
                del markers[markerid]
    return _iterencode
