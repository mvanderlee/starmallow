import inspect
import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    NewType,
    cast,
    get_args,
    get_origin,
)

import marshmallow as ma
import marshmallow.fields as mf
import typing_inspect
from marshmallow.types import StrSequenceOrSet
from marshmallow.utils import missing as missing_
from marshmallow_dataclass2 import class_schema, is_generic_alias_of_dataclass
from starlette.background import BackgroundTasks
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from starlette.websockets import WebSocket

from starmallow.params import (
    Body,
    Cookie,
    Form,
    Header,
    NoParam,
    Param,
    ParamType,
    Path,
    Query,
    ResolvedParam,
    Security,
)
from starmallow.responses import JSONResponse
from starmallow.security.base import SecurityBaseResolver
from starmallow.utils import (
    MaDataclassProtocol,
    create_response_model,
    get_model_field,
    get_path_param_names,
    get_typed_return_annotation,
    get_typed_signature,
    is_marshmallow_dataclass,
    is_marshmallow_field_or_generic,
    is_marshmallow_schema,
    is_optional,
    lenient_issubclass,
)

if TYPE_CHECKING:
    from starmallow.routing import APIRoute, APIWebSocketRoute

logger = logging.getLogger(__name__)

STARMALLOW_PARAM_TYPES = (
    Param,
    NoParam,
    ResolvedParam,
    mf.Field,
)


@dataclass
class EndpointModel:
    path: str
    call: Callable[..., Any]
    route: 'APIRoute | APIWebSocketRoute'
    params: dict[ParamType, dict[str, Param]] = field(default_factory=dict)
    flat_params: dict[ParamType, dict[str, Param]] = field(default_factory=dict)
    name: str | None = None
    methods: Sequence[str] | None = None
    response_model: ma.Schema | type[ma.Schema | MaDataclassProtocol] | mf.Field | None = None
    response_class: type[Response] = JSONResponse
    status_code: int | None = None

    @property
    def path_params(self) -> dict[str, Path] | None:
        return cast(dict[str, Path], self.flat_params.get(ParamType.path))

    @property
    def query_params(self) -> dict[str, Query] | None:
        return cast(dict[str, Query], self.flat_params.get(ParamType.query))

    @property
    def header_params(self) -> dict[str, Header] | None:
        return cast(dict[str, Header], self.flat_params.get(ParamType.header))

    @property
    def cookie_params(self) -> dict[str, Cookie] | None:
        return cast(dict[str, Cookie], self.flat_params.get(ParamType.cookie))

    @property
    def body_params(self) -> dict[str, Body] | None:
        return cast(dict[str, Body], self.flat_params.get(ParamType.body))

    @property
    def form_params(self) -> dict[str, Form] | None:
        return cast(dict[str, Form], self.flat_params.get(ParamType.form))

    @property
    def non_field_params(self) -> dict[str, NoParam] | None:
        return cast(dict[str, NoParam], self.flat_params.get(ParamType.noparam))

    @property
    def resolved_params(self) -> dict[str, ResolvedParam] | None:
        return cast(dict[str, ResolvedParam], self.flat_params.get(ParamType.resolved))

    @property
    def security_params(self) -> dict[str, Security] | None:
        return cast(dict[str, Security], self.flat_params.get(ParamType.security))


class SchemaMeta:
    def __init__(self, title):
        self.title = title


class SchemaModel(ma.Schema):
    def __init__(
        self,
        schema: ma.Schema,
        load_default: Any = missing_,
        required: bool = True,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> None:
        self.schema = schema
        self.load_default = load_default
        self.required = required
        self.title = metadata.get('title') if metadata else None
        self.metadata = metadata
        self.kwargs = kwargs

        if not getattr(schema.Meta, "title", None):
            if schema.Meta is ma.Schema.Meta:
                # Don't override global Meta object's title
                schema.Meta = SchemaMeta(self.title) # type: ignore
            else:
                schema.Meta.title = self.title

    def to_nested(self):
        metadata = self.kwargs.get('metadata') or {}
        metadata['title'] = self.title

        return mf.Nested(
            self.schema,
            required=self.required,
            load_default=self.load_default,
            unknown=ma.EXCLUDE,
            **self.kwargs,
            metadata=metadata,

        )

    def load(
        self,
        data: Mapping[str, Any] | Iterable[Mapping[str, Any]],
        *,
        many: bool | None = None,
        partial: bool | StrSequenceOrSet | None = None,
        unknown: str | None = None,
    ) -> Any:
        if not data and self.load_default:
            return self.load_default

        return self.schema.load(data, many=many, partial=partial, unknown=unknown)


class EndpointMixin:

    def _get_param_model(
        self,
        type_annotation: Any,
        parameter: Param,
        parameter_name: str,
        default_value: Any,
    ) -> ma.Schema | mf.Field | None:
        model = getattr(parameter, 'model', None) or type_annotation
        if isinstance(model, SchemaModel):
            return model

        if isinstance(parameter, Param):
            title = parameter.title or (parameter.alias or parameter_name).title().replace('_', ' ')
        else:
            title = parameter_name.title().replace('_', ' ')

        kwargs = {
            'required': True,
            'metadata': {
                'title': title,
            },
        }
        # Ensure we pass parameter fields into the marshmallow field
        if isinstance(parameter, Param):
            if parameter.validators:
                kwargs['validate'] = parameter.validators
            if parameter.deprecated:
                kwargs['metadata']['deprecated'] = parameter.deprecated

        if is_optional(model):
            kwargs.update({
                'load_default': None,
                'required': False,
                'allow_none': True,  # Even if a default is provided, we should also allow None
            })
            # This does not support Union[A,B,C,None]. Only Union[A,None] and Optional[A]
            model = next((a for a in get_args(type_annotation) if a is not None), None)

        if isinstance(parameter, Param):
            # If default is not Ellipsis, then it's optional regardless of the typehint.
            # Although it's best practice to also mark the typehint as Optional
            if default_value != Ellipsis:
                kwargs.update({
                    'load_default': default_value,
                    'required': False,
                })

            # Ignore type hint. Use provided model instead.
            if parameter.model is not None:
                model = parameter.model
        elif default_value != inspect._empty:
            # If default is not a Param but is defined, then it's optional regardless of the typehint.
            # Although it's best practice to also mark the typehint as Optional
            kwargs.update({
                'load_default': default_value,
                'required': False,
            })

        # If no type was specified, read the raw value
        if model == inspect._empty:
            return mf.Raw(**kwargs)

        if is_marshmallow_dataclass(model):
            model = model.Schema

        if is_generic_alias_of_dataclass(model): # type: ignore
            model = class_schema(model) # type: ignore

        mmf = getattr(model, '_marshmallow_field', None)
        if isinstance(model, NewType) and mmf and lenient_issubclass(mmf, mf.Field):
            return mmf(**kwargs)
        elif is_marshmallow_schema(model):
            return SchemaModel(model() if inspect.isclass(model) else model, **kwargs)
        elif is_marshmallow_field_or_generic(model):
            if not isinstance(model, mf.Field): # inspect.isclass(model):
                model = model()

            if model.load_default is not None and model.load_default != kwargs.get('load_default', ma.missing):
                logger.warning(
                    f"'{parameter_name}' model and annotation have different 'load_default' values."
                    f" {model.load_default} <> {kwargs.get('load_default', ma.missing)}",
                )

            model.required = kwargs['required']
            model.load_default = kwargs.get('load_default', ma.missing)
            model.metadata = {
                **model.metadata,
                **kwargs['metadata'],
            }

            return model

        # elif is_marshmallow_field_or_generic(model):
        #     if isinstance(model, mf.Field):
        #         model if isinstance(model, mf.Field) else model()

        else:
            try:
                return get_model_field(model, **kwargs)
            except Exception as e:
                raise Exception(f'Unknown model type for parameter {parameter_name}, model is {model}, {type(model)}') from e

    def get_resolved_param(self, resolved_param: ResolvedParam, annotation: Any, path: str) -> ResolvedParam:
        # Supports `field = ResolvedParam(resolver_callable)
        # and field: resolver_callable = ResolvedParam()
        if resolved_param.resolver is None:
            resolved_param.resolver = annotation

        resolved_param.resolver_params = self._get_params(resolved_param.resolver, path=path)

        return resolved_param

    def get_security_param(self, resolved_param: Security, annotation: Any, path: str) -> Security:
        if resolved_param.resolver is None:
            resolved_param.resolver = annotation

        resolved_param.resolver_params = self._get_params(resolved_param.resolver, path=path)

        return resolved_param

    def _get_params(
        self,
        func: Callable[..., Any],
        path: str,
    ) -> dict[ParamType, dict[str, Param]]:
        path_param_names = get_path_param_names(path)
        params = {param_type: {} for param_type in ParamType}
        for name, parameter in get_typed_signature(func).parameters.items():
            default_value = parameter.default

            # The type annotation. i.e.: 'str' in these `value: str`. Or `value: [str, Query(gt=3)]`
            type_annotation: Any = inspect._empty
            # The param to use when looking for Param details.
            # i.e.: 'Query(gt=3)' in these `value: Query(gt=3)`. Or `value: [str, Query(gt=3)]`
            starmallow_param: Any = inspect._empty
            if parameter.annotation is not inspect.Signature.empty:
                type_annotation = parameter.annotation
            if isinstance(parameter.default, STARMALLOW_PARAM_TYPES):
                starmallow_param = parameter.default
                default_value = getattr(starmallow_param, 'default', None)

            if get_origin(parameter.annotation) is Annotated:
                annotated_args = get_args(parameter.annotation)
                type_annotation = annotated_args[0]
                starmallow_annotations = [
                    arg
                    for arg in annotated_args[1:]
                    if isinstance(arg, STARMALLOW_PARAM_TYPES)
                ]
                if starmallow_annotations:
                    assert starmallow_param is inspect._empty, (
                        f"Cannot specify `Param` in `Annotated` and default value together for {name!r}"
                    )

                    starmallow_param = starmallow_annotations[-1]
                    if (
                        isinstance(starmallow_param, Param)
                        and starmallow_param.default is not inspect.Signature.empty
                        and default_value is inspect.Signature.empty
                    ):
                        default_value = starmallow_param.default

                field_annotations = [
                    arg
                    for arg in annotated_args
                    if (
                        isinstance(arg, mf.Field)
                        or lenient_issubclass(arg, mf.Field)
                        or (
                            isinstance(arg, typing_inspect.typingGenericAlias)
                            and lenient_issubclass(get_origin(arg), mf.Field)
                        )
                    )
                ]
                if field_annotations:
                    type_annotation = field_annotations[-1]
            if (
                # Skip 'self' in APIHTTPEndpoint functions
                (name == 'self' and '.' in func.__qualname__)
                or isinstance(starmallow_param, NoParam)
            ):
                continue
            elif isinstance(starmallow_param, Security):
                security_param = self.get_security_param(starmallow_param, type_annotation, path=path)
                params[ParamType.security][name] = security_param
                continue
            elif isinstance(starmallow_param, ResolvedParam):
                resolved_param = self.get_resolved_param(starmallow_param, type_annotation, path=path)

                # Allow `ResolvedParam(HTTPBearer())` - treat as securty param
                if isinstance(resolved_param.resolver, SecurityBaseResolver):
                    params[ParamType.security][name] = resolved_param
                else:
                    params[ParamType.resolved][name] = resolved_param

                continue
            elif lenient_issubclass(
                type_annotation,
                (
                    Request,
                    WebSocket,
                    HTTPConnection,
                    Response,
                    BackgroundTasks,
                ),
            ):
                params[ParamType.noparam][name] = type_annotation
                continue

            model = self._get_param_model(type_annotation, starmallow_param, name, default_value)
            model.name = name # type: ignore

            if isinstance(starmallow_param, Param):
                # Create new field_info with processed model
                starmallow_param.model = model
                field_info = starmallow_param
            elif isinstance(model, mf.Field):
                # If marshmallow field with no Param defined

                # Check if it is a PathParameter
                if name in path_param_names:
                    field_info = Path(
                        # If a default was provided, honor it.
                        ... if default_value == inspect._empty else default_value,
                        deprecated=False,
                        include_in_schema=True,
                        model=model,
                    )
                else:
                    # Default it to QueryParameter
                    field_info = Query(
                        # If a default was provided, honor it.
                        ... if default_value == inspect._empty else default_value,
                        deprecated=False,
                        include_in_schema=True,
                        model=model,
                    )
            else:
                # Default all others to body params
                field_info = Body(..., deprecated=False, include_in_schema=True, model=model)

            params[field_info.in_][name] = field_info

        return params

    def get_endpoint_model(
        self,
        path: str,
        endpoint: Callable[..., ma.Schema | mf.Field | Response | None],
        route: 'APIRoute | APIWebSocketRoute',
        name: str | None = None,
        methods: Sequence[str] | None = None,

        status_code: int | None = None,
        response_model: ma.Schema | type[ma.Schema | MaDataclassProtocol] | None = None,
        response_class: type[Response] = JSONResponse,
    ) -> EndpointModel:
        params = self._get_params(endpoint, path)

        response_model = create_response_model(response_model or get_typed_return_annotation(endpoint))  # type: ignore

        return EndpointModel(
            path=path,
            name=name,
            methods=methods,
            call=endpoint,
            params=params,
            flat_params=flatten_parameters(params),
            response_model=response_model,
            response_class=response_class,
            status_code=status_code,
            route=route,
        )


def safe_merge_params(
    left: dict[str, Param],
    right: dict[str, Param],
) -> dict[str, Param]:
    res = left.copy()
    for name, param in right.items():
        if name not in left:
            res[name] = param
        elif param != left[name]:
            raise AssertionError(f"Parameter {name} has conflicting definitions. {left[name]} != {param}")

    return res


def safe_merge_all_params(
    left: dict[ParamType, dict[str, Param]],
    right: dict[ParamType, dict[str, Param]],
) -> dict[ParamType, dict[str, Param]]:
    res = {
        param_type: safe_merge_params(left[param_type], right[param_type])
        for param_type in ParamType
    }

    return res


def flatten_parameters(
    params: dict[ParamType, dict[str, Param]],
) -> dict[ParamType, dict[str, Param]]:
    # flat_params = {param_type: {} for param_type in ParamType}
    flat_params = params.copy()

    for param in params[ParamType.resolved].values():
        if not (isinstance(param, ResolvedParam) and param.resolver_params):
            continue

        flat_params = safe_merge_all_params(flat_params, param.resolver_params)

        if param.resolver_params[ParamType.resolved]:
            flat_nested_params = flatten_parameters(param.resolver_params)

            flat_params = safe_merge_all_params(flat_params, flat_nested_params)

    return flat_params
