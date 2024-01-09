from typing import Any

import marshmallow as ma
import marshmallow.fields as mf
import marshmallow_dataclass.collection_field as collection_field
from apispec import APISpec
from apispec.ext.marshmallow.common import get_fields
from apispec.ext.marshmallow.field_converter import (
    FieldConverterMixin,
    make_min_max_attributes,
    make_type_list,
)
from apispec.ext.marshmallow.openapi import OpenAPIConverter as ApiSpecOpenAPIConverter
from marshmallow.utils import is_collection
from packaging.version import Version

from starmallow.utils import MARSHMALLOW_ITERABLES

# marshmallow field => (JSON Schema type, format)
DEFAULT_FIELD_MAPPING = {
    mf.Integer: ("integer", None),
    mf.Number: ("number", None),
    mf.Float: ("number", None),
    mf.Decimal: ("string", "decimal"),
    mf.String: ("string", None),
    mf.Boolean: ("boolean", None),
    mf.UUID: ("string", "uuid"),
    mf.DateTime: ("string", "date-time"),
    mf.Date: ("string", "date"),
    mf.Time: ("string", None),
    mf.TimeDelta: ("integer", None),
    mf.Email: ("string", "email"),
    mf.URL: ("string", "url"),
    mf.Dict: ("object", None),
    mf.Field: (None, None),
    mf.Raw: (None, None),
    mf.List: ("array", None),
}

# Properties that may be defined in a field's metadata that will be added to the output
# of field2property
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject
_VALID_PROPERTIES = {
    "format",
    "title",
    "description",
    "default",
    "multipleOf",
    "maximum",
    "exclusiveMaximum",
    "minimum",
    "exclusiveMinimum",
    "maxLength",
    "minLength",
    "pattern",
    "maxItems",
    "minItems",
    "uniqueItems",
    "maxProperties",
    "minProperties",
    "required",
    "enum",
    "type",
    "items",
    "allOf",
    "oneOf",
    "anyOf",
    "not",
    "properties",
    "additionalProperties",
    "readOnly",
    "writeOnly",
    "xml",
    "externalDocs",
    "example",
    "nullable",
}


_VALID_PREFIX = "x-"


class OpenAPIConverter(ApiSpecOpenAPIConverter):

    field_mapping = DEFAULT_FIELD_MAPPING

    def __init__(
        self,
        openapi_version: Version | str,
        schema_name_resolver,
        spec: APISpec,
    ) -> None:
        super().__init__(
            openapi_version=openapi_version,
            schema_name_resolver=schema_name_resolver,
            spec=spec,
        )
        self.add_attribute_function(self.field2title)
        self.add_attribute_function(self.field2uniqueItems)
        self.add_attribute_function(self.field2enum)

    # Overriding to add exclusiveMinimum and exclusiveMaximum support
    def field2range(self: FieldConverterMixin, field: mf.Field, ret) -> dict:
        """Return the dictionary of OpenAPI field attributes for a set of
        :class:`Range <marshmallow.validators.Range>` validators.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        validators = [
            validator
            for validator in field.validators
            if (
                hasattr(validator, "min")
                and hasattr(validator, "max")
                and not hasattr(validator, "equal")
            )
        ]

        x_prefix = not set(make_type_list(ret.get("type"))) & {"number", "integer"}

        min_attr = (
            'x-minimum'
            if x_prefix
            else (
                'exclusiveMinimum'
                if any(not getattr(validator, 'min_inclusive') for validator in validators)  # noqa: B009
                else 'minimum'
            )
        )
        max_attr = (
            'x-maximum'
            if x_prefix
            else (
                'exclusiveMaximum'
                if any(not getattr(validator, 'max_inclusive') for validator in validators)  # noqa: B009
                else 'maximum'
            )
        )
        return make_min_max_attributes(validators, min_attr, max_attr)

    # Override to remove 'deprecated' from valid properties.
    # The spec has is at the parameter level, not schema level
    def metadata2properties(
        self, field: mf.Field, **kwargs: Any,
    ) -> dict:
        """Return a dictionary of properties extracted from field metadata.

        Will include field metadata that are valid properties of `OpenAPI schema
        objects
        <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject>`_
        (e.g. "description", "enum", "example").

        In addition, `specification extensions
        <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#specification-extensions>`_
        are supported.  Prefix `x_` to the desired extension when passing the
        keyword argument to the field constructor. apispec will convert `x_` to
        `x-` to comply with OpenAPI.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        # Dasherize metadata that starts with x_
        metadata = {
            key.replace("_", "-") if key.startswith("x_") else key: value
            for key, value in field.metadata.items()
            if isinstance(key, str)
        }

        # Avoid validation error with "Additional properties not allowed"
        ret = {
            key: value
            for key, value in metadata.items()
            if key in _VALID_PROPERTIES or key.startswith(_VALID_PREFIX)
        }
        return ret

    def field2title(self: FieldConverterMixin, field: mf.Field, **kwargs: Any) -> dict:
        ret = {}

        if 'title' in field.metadata:
            ret['title'] = field.metadata['title']
        elif field.name and not isinstance(field.parent, MARSHMALLOW_ITERABLES):
            ret['title'] = field.name.title().replace('_', ' ')

        return ret

    def field2uniqueItems(self: FieldConverterMixin, field: mf.Field, **kwargs: Any) -> dict:
        ret = {}

        # If this type isn't directly in the field mapping then check the
        # hierarchy until we find something that does.
        for field_class in type(field).__mro__:
            # FastAPI compatibility. This is part of the JSON Schema spec
            if field_class == collection_field.Set:
                ret['uniqueItems'] = True

        return ret

    def field2enum(self: FieldConverterMixin, field: mf.Field, **kwargs: Any) -> dict:
        ret = {}

        if isinstance(field, mf.Enum):
            if field.by_value:
                choices = [x.value for x in field.enum]
            else:
                choices = list(field.enum.__members__)

            if choices:
                ret['enum'] = choices

        return ret

    # Overrice to add 'deprecated' support
    def _field2parameter(
        self, field: mf.Field, *, name: str, location: str,
    ):
        """Return an OpenAPI parameter as a `dict`, given a marshmallow
        :class:`Field <marshmallow.Field>`.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject
        """
        ret: dict = {"in": location, "name": name}

        partial = getattr(field.parent, "partial", False)
        ret["required"] = field.required and (
            not partial
            or (is_collection(partial) and field.name not in partial)  # type:ignore
        )

        prop = self.field2property(field)
        multiple = isinstance(field, mf.List)

        if self.openapi_version.major < 3:
            if multiple:
                ret["collectionFormat"] = "multi"
            ret.update(prop)
        else:
            if multiple:
                ret["explode"] = True
                ret["style"] = "form"
            if prop.get("description", None):
                ret["description"] = prop.pop("description", None)
            ret["schema"] = prop

            if 'deprecated' in field.metadata:
                ret['deprecated'] = field.metadata['deprecated']
        return ret

    def schema2jsonschema(self, schema):
        """Return the JSON Schema Object for a given marshmallow
        :class:`Schema <marshmallow.Schema>` instance. Schema may optionally
        provide the ``title`` and ``description`` class Meta options.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject

        :param Schema schema: A marshmallow Schema instance
        :rtype: dict, a JSON Schema Object
        """
        fields = get_fields(schema)
        Meta = getattr(schema, "Meta", None)
        partial = getattr(schema, "partial", None)

        jsonschema = self.fields2jsonschema(fields, partial=partial)

        if hasattr(Meta, "title"):
            jsonschema["title"] = Meta.title
        else:
            jsonschema['title'] = schema.__class__.__name__

        if hasattr(Meta, "description"):
            jsonschema["description"] = Meta.description
        if hasattr(Meta, "unknown") and Meta.unknown != ma.EXCLUDE:
            jsonschema["additionalProperties"] = Meta.unknown == ma.INCLUDE

        return jsonschema
