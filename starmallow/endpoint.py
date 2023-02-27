
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
from starlette.responses import Response

from starmallow.params import Body, Cookie, Form, Header, Param, ParamType, Path, Query
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
)

if TYPE_CHECKING:
    from starmallow.routing import APIRoute

logger = logging.getLogger(__name__)


@dataclass
class EndpointModel:
    path_params: Optional[Dict[str, Path]] = field(default_factory=list)
    query_params: Optional[Dict[str, Query]] = field(default_factory=list)
    header_params: Optional[Dict[str, Header]] = field(default_factory=list)
    cookie_params: Optional[Dict[str, Cookie]] = field(default_factory=list)
    body_params: Optional[Dict[str, Body]] = field(default_factory=list)
    form_params: Optional[Dict[str, Form]] = field(default_factory=list)
    name: Optional[str] = None
    path: Optional[str] = None
    methods: Optional[List[str]] = None
    call: Optional[Callable[..., Any]] = None
    response_model: Optional[ma.Schema | mf.Field] = None
    response_class: Type[Response] = JSONResponse
    status_code: Optional[int] = None
    route: 'APIRoute' = None


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

    def _get_params_from_endpoint(
        self,
        endpoint: Callable[..., Any],
        path: str,
    ) -> Dict[ParamType, List[Dict[str, Param]]]:
        path_param_names = get_path_param_names(path)
        params = {param_type: {} for param_type in ParamType}
        for name, parameter in inspect.signature(endpoint).parameters.items():
            if name == 'self' and '.' in endpoint.__qualname__:
                # Skip 'self' in APIHTTPEndpoint functions
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
        params = self._get_params_from_endpoint(endpoint, path)

        response_model = create_response_model(response_model or inspect.signature(endpoint).return_annotation)

        return EndpointModel(
            path=path,
            name=name,
            methods=methods,
            call=endpoint,
            path_params=params[ParamType.path],
            query_params=params[ParamType.query],
            header_params=params[ParamType.header],
            cookie_params=params[ParamType.cookie],
            body_params=params[ParamType.body],
            form_params=params[ParamType.form],
            response_model=response_model,
            response_class=response_class,
            status_code=status_code,
            route=route,
        )
