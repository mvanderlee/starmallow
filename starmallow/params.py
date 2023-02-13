import logging
from enum import Enum
from typing import Any, Callable, Iterable

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.utils import is_iterable_but_not_string
from marshmallow.validate import Length, Range, Regexp

logger = logging.getLogger(__name__)


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
        default: Any = Ellipsis,
        *,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        model: ma.Schema | mf.Field = None,
        validators: None
        | (
            Callable[[Any], Any]
            | Iterable[Callable[[Any], Any]]
        ) = None,
        # Convience validators
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        regex: str | None = None,
        title: str = None,
    ) -> None:
        self.default = default
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.model = model
        self.title = title

        # Convience validators - fastapi compatibility
        self.validators = []
        if gt is not None:
            self.validators.append(Range(min=float(gt), min_inclusive=False))
        if ge is not None:
            self.validators.append(Range(min=float(ge), min_inclusive=True))
        if lt is not None:
            self.validators.append(Range(max=float(lt), max_inclusive=False))
        if le is not None:
            self.validators.append(Range(max=float(le), max_inclusive=True))
        if min_length is not None:
            self.validators.append(Length(min=min_length))
        if max_length is not None:
            self.validators.append(Length(max=max_length))
        if regex is not None:
            self.validators.append(Regexp(regex))

        if validators and is_iterable_but_not_string(validators):
            self.validators += validators

        if self.model and getattr(self.model, 'validators', None) and self.validators:
            logger.warning('Provided validators will override model validators')


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
