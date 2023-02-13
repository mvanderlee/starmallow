from apispec.ext.marshmallow import MarshmallowPlugin as ApiSpecMarshmallowPlugin

from .openapi import OpenAPIConverter


class MarshmallowPlugin(ApiSpecMarshmallowPlugin):

    Converter = OpenAPIConverter
