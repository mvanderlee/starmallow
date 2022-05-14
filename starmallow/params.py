from enum import Enum
from typing import Any, Optional, Union

import marshmallow as ma
import marshmallow.fields as mf


class ParamType(Enum):
    path = 'path'
    query = 'query'
    header = 'header'
    cookie = 'cookie'
    body = 'body'
    form = 'form'


class Param:

    def __init__(
        self,
        default: Any,
        *,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        model: Union[ma.Schema, mf.Field] = None,
    ) -> None:
        self.default = default
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.model = model


class Path(Param):
    in_ = ParamType.path


class Query(Param):
    in_ = ParamType.query


class Header(Param):
    in_ = ParamType.header


class Cookie(Param):
    in_ = ParamType.cookie


class Body(Param):
    in_ = ParamType.body


class Form(Body):
    in_ = ParamType.form
