import logging
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from typing import Any, ClassVar

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.validate import Length, Range, Regexp

from starmallow.security.base import SecurityBaseResolver
from starmallow.utils import eq_marshmallow_fields

logger = logging.getLogger(__name__)


class ParamType(Enum):
    path = 'path'
    query = 'query'
    header = 'header'
    cookie = 'cookie'
    body = 'body'
    form = 'form'

    noparam = 'noparam'
    resolved = 'resolved'
    security = 'security'


class Param:
    in_: ClassVar[ParamType]

    def __init__(
        self,
        default: Any = Ellipsis,
        *,
        # alias to look the param up by.
        alias: str | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        model: ma.Schema | mf.Field | None = None,
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
        # OpenAPI title
        title: str | None = None,
    ) -> None:
        self.default = default
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.model = model
        self.alias = alias
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

        if validators:
            if isinstance(validators, Iterable) and not isinstance(validators, str):
                self.validators += validators
            elif callable(validators):
                self.validators.append(validators)
            else:
                raise ValueError('Validators must be a callable or list of callables')

        if self.model and getattr(self.model, 'validators', None) and self.validators:
            logger.warning('Provided validators will override model validators')

    def __eq__(self, other: "object | Param") -> bool:
        return (
            isinstance(other, Param)
            and self.__class__ == other.__class__
            and self.in_ == other.in_
            and self.default == other.default
            and self.deprecated == other.deprecated
            and self.include_in_schema == other.include_in_schema
            and self.title == other.title
            and eq_marshmallow_fields(self.model, other.model)
            # Marshmallow Validators don't have an __eq__ function, but the repr should work.
            and [repr(v) for v in self.validators] == [repr(v) for v in other.validators]
        )


class Path(Param):
    in_ = ParamType.path


class Query(Param):
    in_ = ParamType.query


class Header(Param):
    in_ = ParamType.header

    def __init__(
        self,
        default: Any = Ellipsis,
        *,
        # alias to look the param up by.
        alias: str | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        model: ma.Schema | mf.Field | None = None,
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
        # OpenAPI title
        title: str | None = None,
        convert_underscores: bool = True,
    ) -> None:
        self.convert_underscores = convert_underscores
        super().__init__(
            default=default,
            alias=alias,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            model=model,
            validators=validators,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            regex=regex,
            title=title,
        )


class Cookie(Param):
    in_ = ParamType.cookie


class Body(Param):
    in_ = ParamType.body

    def __init__(
        self,
        default: Any = Ellipsis,
        *,
        media_type: str = "application/json",
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        model: ma.Schema | mf.Field | None = None,
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
        title: str | None = None,
    ) -> None:
        super().__init__(
            default=default,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            model=model,
            validators=validators,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            regex=regex,
            title=title,
        )
        self.media_type = media_type


class Form(Body):
    in_ = ParamType.form

    def __init__(
        self,
        default: Any = Ellipsis,
        *,
        media_type: str = "application/x-www-form-urlencoded",
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        model: ma.Schema | mf.Field | None = None,
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
        title: str | None = None,
    ) -> None:
        super().__init__(
            default=default,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            model=model,
            validators=validators,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            regex=regex,
            title=title,
            media_type=media_type,
        )


class NoParam:
    '''
        Used to tell StarMallow to ignore these arguments as they will be provided by a 3rd party.
        Typical usecase is if there is a 3rd party decorator that adds these.

        Arguments will not be added to Swagger docs or be validated in any way.
    '''


class ResolvedParam:
    def __init__(self, resolver: Callable[[Any], Any] | None = None, use_cache: bool = True):
        self.resolver = resolver
        # Set when we resolve the routes in the EnpointMixin
        self.resolver_params: dict[ParamType, dict[str, Param]] = {}
        self.use_cache = use_cache
        self.cache_key = (self.resolver, None)


class Security(ResolvedParam):

    def __init__(
        self,
        resolver: SecurityBaseResolver | None = None,
        scopes: Sequence[str] | None = None,
        use_cache: bool = True,
    ):
        # Not calling super so that the resolver typehinting actually works in VSCode
        self.resolver = resolver
        # Set when we resolve the routes in the EnpointMixin
        self.resolver_params: dict[ParamType, dict[str, Param]] = {}
        self.scopes = scopes or []
        self.use_cache = use_cache
        self.cache_key = (self.resolver, tuple(sorted(set(self.scopes or []))))
