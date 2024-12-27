import asyncio
import inspect
import logging
from contextlib import AsyncExitStack
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

import marshmallow as ma
import marshmallow.fields as mf
from marshmallow.error_store import ErrorStore
from marshmallow.utils import missing as missing_
from starlette.background import BackgroundTasks as StarletteBackgroundTasks
from starlette.datastructures import FormData, Headers, QueryParams
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from starlette.websockets import WebSocket

from starmallow.background import BackgroundTasks
from starmallow.params import Param, ParamType, ResolvedParam
from starmallow.utils import (
    is_async_gen_callable,
    is_gen_callable,
    lenient_issubclass,
    solve_generator,
)

logger = logging.getLogger(__name__)


async def get_body(
    request: Request,
    form_params: Dict[str, Param],
    body_params: Dict[str, Param],
) -> Union[FormData, bytes, Dict[str, Any]]:
    is_body_form = bool(form_params)
    should_process_body = is_body_form or body_params
    try:
        body: Any = None
        if should_process_body:
            if is_body_form:
                body = await request.form()
                stack = request.scope.get("starmallow_astack")
                assert isinstance(stack, AsyncExitStack)
                stack.push_async_callback(body.close)
            else:
                body_bytes = await request.body()
                if body_bytes:
                    json_body: Any = missing_
                    content_type_value: str = request.headers.get("content-type")
                    if not content_type_value:
                        json_body = await request.json()
                    else:
                        main_type, sub_type = content_type_value.split(';')[0].split('/')
                        if main_type == "application":
                            if sub_type == "json" or sub_type.endswith("+json"):
                                json_body = await request.json()
                    if json_body != missing_:
                        body = json_body
                    else:
                        body = body_bytes

        return body
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="There was an error parsing the body",
        ) from e


def request_params_to_args(
    received_params: Union[Mapping[str, Any], QueryParams, Headers],
    endpoint_params: Dict[str, Param],
    ignore_namespace: bool = True,
) -> Tuple[Dict[str, Any], ErrorStore]:
    values = {}
    error_store = ErrorStore()
    for field_name, param in endpoint_params.items():
        if not param.alias and getattr(param, "convert_underscores", None):
            alias = field_name.replace("_", "-")
        else:
            alias = param.alias or field_name

        if isinstance(param.model, mf.Field):
            try:
                # Load model from specific param
                values[field_name] = param.model.deserialize(
                    received_params.get(alias, ma.missing),
                    field_name,
                    received_params,
                )
            except ma.ValidationError as error:
                error_store.store_error(error.messages, field_name)
        elif isinstance(param.model, ma.Schema):
            try:
                load_params = received_params if ignore_namespace else received_params.get(alias, {})

                # Entire model is optional and no data was passed in.
                if getattr(param.model, 'required', None) is False and not load_params:
                    values[field_name] = None
                else:
                    values[field_name] = param.model.load(load_params, unknown=ma.EXCLUDE)

            except ma.ValidationError as error:
                # Entire model is optional, so ignore errors
                if getattr(param.model, 'required', None) is False:
                    values[field_name] = None
                else:
                    error_store.store_error(error.messages)
        else:
            raise Exception(f'Invalid model type {type(param.model)}, expected marshmallow Schema or Field')

    return values, error_store


async def resolve_basic_args(
    request: Request | WebSocket,
    response: Response,
    background_tasks: StarletteBackgroundTasks,
    params: Dict[ParamType, Dict[str, Param]],
):
    path_values, path_errors = request_params_to_args(
        request.path_params,
        params.get(ParamType.path),
    )
    query_values, query_errors = request_params_to_args(
        request.query_params,
        params.get(ParamType.query),
    )
    header_values, header_errors = request_params_to_args(
        request.headers,
        params.get(ParamType.header),
    )
    cookie_values, cookie_errors = request_params_to_args(
        request.cookies,
        params.get(ParamType.cookie),
    )

    form_params = params.get(ParamType.form)
    body_params = params.get(ParamType.body)
    body = await get_body(request, form_params, body_params)
    form_values, form_errors = {}, None
    json_values, json_errors = {}, None
    if form_params:
        form_values, form_errors = request_params_to_args(
            body if body is not None and isinstance(body, FormData) else {},
            form_params,
            # If there is only one parameter defined, then don't namespace by the parameter name
            # Otherwise we honor the namespace: https://fastapi.tiangolo.com/tutorial/body-multiple-params/
            ignore_namespace=len(form_params) == 1,
        )
    if body_params:
        json_values, json_errors = request_params_to_args(
            body if body is not None and isinstance(body, Mapping) else {},
            body_params,
            # If there is only one parameter defined, then don't namespace by the parameter name
            # Otherwise we honor the namespace: https://fastapi.tiangolo.com/tutorial/body-multiple-params/
            ignore_namespace=len(body_params) == 1,
        )

    values = {
        **path_values,
        **query_values,
        **header_values,
        **cookie_values,
        **form_values,
        **json_values,
    }
    errors = {}
    if path_errors.errors:
        errors['path'] = path_errors.errors
    if query_errors.errors:
        errors['query'] = query_errors.errors
    if header_errors.errors:
        errors['header'] = header_errors.errors
    if cookie_errors.errors:
        errors['cookie'] = cookie_errors.errors
    if form_errors and form_errors.errors:
        errors['form'] = form_errors.errors
    if json_errors and json_errors.errors:
        errors['json'] = json_errors.errors

    # Handle non-field params
    for param_name, param_type in params.get(ParamType.noparam).items():
        if lenient_issubclass(param_type, (HTTPConnection, Request, WebSocket)):
            values[param_name] = request
        elif lenient_issubclass(param_type, Response):
            values[param_name] = response
        elif lenient_issubclass(param_type, StarletteBackgroundTasks):
            values[param_name] = background_tasks

    return values, errors


async def call_resolver(
    request: Request | WebSocket,
    param_name: str,
    resolved_param: ResolvedParam,
    resolver_kwargs: Dict[str, Any],
):
    # Resolver can be a class with __call__ function
    resolver = resolved_param.resolver
    if not inspect.isfunction(resolver) and callable(resolver):
        resolver = resolver.__call__
    elif not inspect.isfunction(resolver):
        raise TypeError(f'{param_name} = {resolved_param} resolver is not a function or callable')

    if is_gen_callable(resolver) or is_async_gen_callable(resolver):
        stack = request.scope.get("starmallow_astack")
        assert isinstance(stack, AsyncExitStack)
        return await solve_generator(
            call=resolver, stack=stack, gen_kwargs=resolver_kwargs,
        )
    elif asyncio.iscoroutinefunction(resolver):
        return await resolver(**resolver_kwargs)
    else:
        return resolver(**resolver_kwargs)


async def resolve_subparams(
    request: Request | WebSocket,
    response: Response,
    background_tasks: StarletteBackgroundTasks,
    params: Dict[str, ResolvedParam],
    dependency_cache: Optional[Dict[Tuple[Callable[..., Any], Tuple[str]], Any]],
) -> Dict[str, Any]:
    values = {}
    for param_name, resolved_param in params.items():
        if resolved_param.use_cache and resolved_param.cache_key in dependency_cache:
            values[param_name] = dependency_cache[resolved_param.cache_key]
            continue

        resolver_kwargs, resolver_errors, _, _ = await resolve_params(
            request=request,
            background_tasks=background_tasks,
            response=response,
            params=resolved_param.resolver_params,
            dependency_cache=dependency_cache,
        )

        # Exit early since other resolvers may rely on this one, which could raise argument exceptions
        if resolver_errors:
            return None, resolver_errors

        resolved_value = await call_resolver(request, param_name, resolved_param, resolver_kwargs)
        values[param_name] = resolved_value
        if resolved_param.use_cache:
            dependency_cache[resolved_param.cache_key] = resolved_value

    return values, {}


async def resolve_params(
    request: Request | WebSocket,
    params: Dict[ParamType, Dict[str, Param]],
    background_tasks: Optional[StarletteBackgroundTasks] = None,
    response: Optional[Response] = None,
    dependency_cache: Optional[Dict[Tuple[Callable[..., Any], Tuple[str]], Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Union[Any, List, Dict]], StarletteBackgroundTasks, Response]:
    dependency_cache = dependency_cache or {}

    if response is None:
        response = Response()
        del response.headers["content-length"]
        response.status_code = None  # type: ignore

    if background_tasks is None:
        background_tasks = BackgroundTasks()

    # Process security params first so we can raise permission issues
    security_values, errors = await resolve_subparams(
        request,
        response,
        background_tasks,
        params.get(ParamType.security),
        dependency_cache=dependency_cache,
    )
    if errors:
        return None, errors, background_tasks, response

    arg_values, errors = await resolve_basic_args(
        request,
        response,
        background_tasks,
        params,
    )
    if errors:
        return None, errors, background_tasks, response

    resolved_values, errors = await resolve_subparams(
        request,
        response,
        background_tasks,
        params.get(ParamType.resolved),
        dependency_cache=dependency_cache,
    )
    if errors:
        return None, errors, background_tasks, response

    return {
        **security_values,
        **arg_values,
        **resolved_values,
    }, {}, background_tasks, response
