
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
)

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.utils import missing as missing_
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
)
from starmallow.responses import JSONResponse
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
        return mf.Nested(
            self.schema,
            required=self.required,
            load_default=self.load_default,
            title=self.title,
            **self.kwargs,
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

    def _get_param_model(self, parameter: inspect.Parameter) -> Union[ma.Schema, mf.Field]:
        model = parameter.annotation

        kwargs = {
            'required': True,
            'metadata': {
                'title': (
                    parameter.default.title
                    if (isinstance(parameter.default, Param) and parameter.default.title)
                    else parameter.name.title().replace('_', ' ')
                )
            }
        }
        # Ensure we pass parameter fields into the marshmallow field
        if isinstance(parameter.default, Param):
            if parameter.default.validators:
                kwargs['validate'] = parameter.default.validators
            if parameter.default.deprecated:
                kwargs['metadata']['deprecated'] = parameter.default.deprecated

        if is_optional(model):
            kwargs.update({
                'load_default': None,
                'required': False,
            })
            # This does not support Union[A,B,C,None]. Only Union[A,None] and Optional[A]
            model = next((a for a in get_args(parameter.annotation) if a is not None), None)

        if isinstance(parameter.default, Param):
            # If default is not Ellipsis, then it's optional regardless of the typehint.
            # Although it's best practice to also mark the typehint as Optional
            if parameter.default.default != Ellipsis:
                kwargs.update({
                    'load_default': parameter.default.default,
                    'required': False,
                })

            # Ignore type hint. Use provided model instead.
            if parameter.default.model is not None:
                model = parameter.default.model
        elif parameter.default != inspect._empty:
            # If default is not a Param but is defined, then it's optional regardless of the typehint.
            # Although it's best practice to also mark the typehint as Optional
            kwargs.update({
                'load_default': parameter.default,
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
                logger.warning(f"'{parameter.name}' model and annotation have different 'load_default' values. {model.load_default} <> {kwargs.get('load_default', ma.missing)}")

            model.required = kwargs['required']
            model.load_default = kwargs.get('load_default', ma.missing)
            model.metadata.update(kwargs['metadata'])

            return model
        else:
            try:
                return get_model_field(model, **kwargs)
            except Exception:
                raise Exception(f'Unknown model type for parameter {parameter.name}, model is {model}')

    def _get_params(
        self,
        func: Callable[..., Any],
        path: str,
    ) -> Dict[ParamType, Dict[str, Param]]:
        path_param_names = get_path_param_names(path)
        params = {param_type: {} for param_type in ParamType}
        for name, parameter in inspect.signature(func).parameters.items():
            if (
                # Skip 'self' in APIHTTPEndpoint functions
                (name == 'self' and '.' in func.__qualname__)
                or isinstance(parameter.default, NoParam)
            ):
                continue
            elif isinstance(parameter.default, ResolvedParam):
                resolved_param: ResolvedParam = parameter.default
                resolved_param.resolver_params = self._get_params(resolved_param.resolver, path=path)
                params[ParamType.resolved][name] = resolved_param
                continue
            elif lenient_issubclass(
                parameter.annotation,
                (
                    Request,
                    WebSocket,
                    HTTPConnection,
                    Response,
                    BackgroundTasks,
                )
            ):
                params[ParamType.noparam][name] = parameter.annotation
                continue

            model = self._get_param_model(parameter)
            model.name = name

            if isinstance(parameter.default, Param):
                # Create new field_info with processed model
                field_info = parameter.default.__class__(
                    parameter.default.default,
                    deprecated=parameter.default.deprecated,
                    include_in_schema=parameter.default.include_in_schema,
                    model=model,
                )
            elif isinstance(model, mf.Field):
                # If marshmallow field with no Param defined

                # Check if it is a PathParameter
                if name in path_param_names:
                    field_info = Path(
                        # If a default was provided, honor it.
                        ... if parameter.default == inspect._empty else parameter.default,
                        deprecated=False,
                        include_in_schema=True,
                        model=model,
                    )
                else:
                    # Default it to QueryParameter
                    field_info = Query(
                        # If a default was provided, honor it.
                        ... if parameter.default == inspect._empty else parameter.default,
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
            flat_params=flatten_resolved_parameters(params),
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


def flatten_resolved_parameters(
    resolved_params: Dict[ParamType, Dict[str, Param]]
) -> Dict[ParamType, Dict[str, Param]]:
    # flat_params = {param_type: {} for param_type in ParamType}
    flat_params = resolved_params.copy()
    for param in resolved_params[ParamType.resolved].values():
        if not param.resolver_params:
            continue

        flat_params = safe_merge_all_params(flat_params, param.resolver_params)

        if param.resolver_params[ParamType.resolved]:
            flat_nested_params = flatten_resolved_parameters(param.resolver_params)

            flat_params = safe_merge_all_params(flat_params, flat_nested_params)

    return flat_params
