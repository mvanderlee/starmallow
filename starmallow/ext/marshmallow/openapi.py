import warnings
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
from apispec.utils import OpenAPIVersion

from starmallow.utils import MARSHMALLOW_ITERABLES


class OpenAPIConverter(ApiSpecOpenAPIConverter):

    def __init__(
        self,
        openapi_version: OpenAPIVersion | str,
        schema_name_resolver,
        spec: APISpec,
    ) -> None:
        super().__init__(
            openapi_version=openapi_version,
            schema_name_resolver=schema_name_resolver,
            spec=spec,
        )
        self.add_attribute_function(self.field2title)

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
                if any(not getattr(validator, 'min_inclusive') for validator in validators)
                else 'minimum'
            )
        )
        max_attr = (
            'x-maximum'
            if x_prefix
            else (
                'exclusiveMaximum'
                if any(not getattr(validator, 'max_inclusive') for validator in validators)
                else 'maximum'
            )
        )
        return make_min_max_attributes(validators, min_attr, max_attr)

    # Overriding to add uniqueItems support
    def field2type_and_format(
        self: FieldConverterMixin, field: mf.Field, **kwargs: Any
    ) -> dict:
        """Return the dictionary of OpenAPI type and format based on the field type.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        ret = {}

        # If this type isn't directly in the field mapping then check the
        # hierarchy until we find something that does.
        for field_class in type(field).__mro__:
            # FastAPI compatibility. This is part of the JSON Schema spec
            if field_class == collection_field.Set:
                ret['uniqueItems'] = True

            if field_class in self.field_mapping:
                type_, fmt = self.field_mapping[field_class]
                break
        else:
            warnings.warn(
                "Field of type {} does not inherit from marshmallow.Field.".format(
                    type(field)
                ),
                UserWarning,
            )
            type_, fmt = "string", None

        if type_:
            ret["type"] = type_
        if fmt:
            ret["format"] = fmt

        return ret

    def field2title(self: FieldConverterMixin, field: mf.Field, **kwargs: Any) -> dict:
        ret = {}

        if 'title' in field.metadata:
            ret['title'] = field.metadata['title']
        elif field.name and not isinstance(field.parent, MARSHMALLOW_ITERABLES):
            ret['title'] = field.name.title().replace('_', ' ')

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
