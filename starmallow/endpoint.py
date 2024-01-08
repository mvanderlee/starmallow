import inspect
import logging
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    NewType,
    Optional,
    Type,
    Union,
    get_origin,
)

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.utils import missing as missing_
from starlette.background import BackgroundTasks
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from typing_extensions import Annotated

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
    create_response_model,
    get_args,
    get_model_field,
    get_path_param_names,
    is_marshmallow_dataclass,
    is_marshmallow_field,
    is_marshmallow_schema,
    is_optional,
    lenient_issubclass,
)

if TYPE_CHECKING:
    from starmallow.routing import APIRoute

logger = logging.getLogger(__name__)

STARMALLOW_PARAM_TYPES = (
    Param,
    NoParam,
    ResolvedParam,
    mf.Field,
)


@dataclass
class EndpointModel:
    params: Optional[Dict[ParamType, Dict[str, Param]]] = field(default_factory=dict)
    flat_params: Optional[Dict[ParamType, Dict[str, Param]]] = field(default_factory=dict)
    name: Optional[str] = None
    path: Optional[str] = None
    methods: Optional[List[str]] = None
    call: Optional[Callable[..., Any]] = None
    response_model: Optional[ma.Schema | mf.Field] = None
    response_class: Type[Response] = JSONResponse
    status_code: Optional[int] = None
    route: 'APIRoute' = None

    @property
    def path_params(self) -> Dict[str, Path] | None:
        return self.flat_params.get(ParamType.path)

    @property
    def query_params(self) -> Dict[str, Query] | None:
        return self.flat_params.get(ParamType.query)

    @property
    def header_params(self) -> Dict[str, Header] | None:
        return self.flat_params.get(ParamType.header)

    @property
    def cookie_params(self) -> Dict[str, Cookie] | None:
        return self.flat_params.get(ParamType.cookie)

    @property
    def body_params(self) -> Dict[str, Body] | None:
        return self.flat_params.get(ParamType.body)

    @property
    def form_params(self) -> Dict[str, Form] | None:
        return self.flat_params.get(ParamType.form)

    @property
    def non_field_params(self) -> Dict[str, NoParam] | None:
        return self.flat_params.get(ParamType.noparam)

    @property
    def resolved_params(self) -> Dict[str, ResolvedParam] | None:
        return self.flat_params.get(ParamType.resolved)

    @property
    def security_params(self) -> Dict[str, Security] | None:
        return self.flat_params.get(ParamType.security)


class SchemaMeta:
    def __init__(self, title):
        self.title = title


class SchemaModel(ma.Schema):
    def __init__(
        self,
        schema: ma.Schema,
        load_default: Any = missing_,
        required: bool = True,
        metadata: Dict[str, Any] = None,
        **kwargs,
    ) -> None:
        self.schema = schema
        self.load_default = load_default
        self.required = required
        self.title = metadata.get('title')
        self.metadata = metadata
        self.kwargs = kwargs

        if not getattr(schema.Meta, "title", None):
            if schema.Meta is ma.Schema.Meta:
                # Don't override global Meta object's title
                schema.Meta = SchemaMeta(self.title)
            else:
                schema.Meta.title = self.title

    def to_nested(self):
        metadata = self.kwargs.get('metadata') or {}
        metadata['title'] = self.title

        return mf.Nested(
            self.schema,
            required=self.required,
            load_default=self.load_default,
            **self.kwargs,
            metadata=metadata,
        )

    def load(
        self,
        data: Union[
            Mapping[str, Any],
            Iterable[Mapping[str, Any]],
        ],
        *,
        many: Optional[bool] = None,
        partial: Optional[bool] = None,
        unknown: Optional[str] = None,
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
    ) -> Union[ma.Schema, mf.Field]:
        model = type_annotation

        kwargs = {
            'required': True,
            'metadata': {
                'title': (
                    parameter.title
                    if (isinstance(parameter, Param) and parameter.title)
                    else parameter_name.title().replace('_', ' ')
                ),
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

        if isinstance(model, NewType) and getattr(model, '_marshmallow_field', None):
            return model._marshmallow_field(**kwargs)
        elif is_marshmallow_schema(model):
            return SchemaModel(model(), **kwargs)
        elif is_marshmallow_field(model):
            if model.load_default is not None and model.load_default != kwargs.get('load_default', ma.missing):
                logger.warning(
                    f"'{parameter_name}' model and annotation have different 'load_default' values."
                    + f" {model.load_default} <> {kwargs.get('load_default', ma.missing)}",
                )

            model.required = kwargs['required']
            model.load_default = kwargs.get('load_default', ma.missing)
            model.metadata.update(kwargs['metadata'])

            return model
        else:
            try:
                return get_model_field(model, **kwargs)
            except Exception as e:
                raise Exception(f'Unknown model type for parameter {parameter_name}, model is {model}') from e

    def get_resolved_param(self, resolved_param: ResolvedParam, annotation: Any, path: str) -> ResolvedParam:
        # Supports `field = ResolvedParam(resolver_callable)
        # and field: resolver_callable = ResolvedParam()
        if resolved_param.resolver is None:
            resolved_param.resolver = annotation

        resolved_param.resolver_params = self._get_params(resolved_param.resolver, path=path)

        return resolved_param

    def _get_params(
        self,
        func: Callable[..., Any],
        path: str,
    ) -> Dict[ParamType, Dict[str, Param]]:
        path_param_names = get_path_param_names(path)
        params = {param_type: {} for param_type in ParamType}
        for name, parameter in inspect.signature(func).parameters.items():
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
                        "Cannot specify `Param` in `Annotated` and default value"
                    f" together for {name!r}"
                    )

                    starmallow_param = starmallow_annotations[-1]
                    if (
                        isinstance(starmallow_param, Param)
                        and starmallow_param.default is not inspect.Signature.empty
                        and default_value is inspect.Signature.empty
                    ):
                        default_value = starmallow_param.default

            if (
                # Skip 'self' in APIHTTPEndpoint functions
                (name == 'self' and '.' in func.__qualname__)
                or isinstance(starmallow_param, NoParam)
            ):
                continue
            elif isinstance(starmallow_param, ResolvedParam):
                resolved_param: ResolvedParam = self.get_resolved_param(starmallow_param, type_annotation, path=path)
                params[ParamType.resolved][name] = resolved_param

                if isinstance(starmallow_param, Security):
                    params[ParamType.security][name] = resolved_param
                # Allow `ResolvedParam(HTTPBearer())`
                elif isinstance(resolved_param.resolver, SecurityBaseResolver):
                    params[ParamType.security][name] = resolved_param

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
            model.name = name

            if isinstance(starmallow_param, Param):
                # Create new field_info with processed model
                field_info = starmallow_param.__class__(
                    starmallow_param.default,
                    deprecated=starmallow_param.deprecated,
                    include_in_schema=starmallow_param.include_in_schema,
                    model=model,
                )
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
        endpoint: Callable[..., Any],
        route: 'APIRoute',
        name: Optional[str] = None,
        methods: Optional[List[str]] = None,

        status_code: Optional[int] = None,
        response_model: Optional[ma.Schema] = None,
        response_class: Type[Response] = JSONResponse,
    ) -> EndpointModel:
        params = self._get_params(endpoint, path)

        response_model = create_response_model(response_model or inspect.signature(endpoint).return_annotation)

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
    left: Dict[str, Param],
    right: Dict[str, Param],
) -> Dict[str, Param]:
    res = left.copy()
    for name, param in right.items():
        if name not in left:
            res[name] = param
        elif param != left[name]:
            raise AssertionError(f"Parameter {name} has conflicting definitions. {left[name]} != {param}")

    return res


def safe_merge_all_params(
    left: Dict[ParamType, Dict[str, Param]],
    right: Dict[ParamType, Dict[str, Param]],
) -> Dict[ParamType, Dict[str, Param]]:
    res = {
        param_type: safe_merge_params(left[param_type], right[param_type])
        for param_type in ParamType
    }

    return res


def flatten_parameters(
    params: Dict[ParamType, Dict[str, Param]],
) -> Dict[ParamType, Dict[str, Param]]:
    # flat_params = {param_type: {} for param_type in ParamType}
    flat_params = params.copy()
    for param in params[ParamType.resolved].values():
        if not param.resolver_params:
            continue

        flat_params = safe_merge_all_params(flat_params, param.resolver_params)

        if param.resolver_params[ParamType.resolved]:
            flat_nested_params = flatten_parameters(param.resolver_params)

            flat_params = safe_merge_all_params(flat_params, flat_nested_params)

    return flat_params
