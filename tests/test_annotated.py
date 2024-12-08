'''Test Resolved Params'''
import datetime as dt
from typing import Annotated, Literal, Optional, Union

import marshmallow as ma
import marshmallow.fields as mf
import pytest
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import Body, Header, Path, Query, ResolvedParam, StarMallow

from .utils import assert_json

app = StarMallow()


############################################################
# Models  -  classes and schemas
############################################################
# region  -  VS Code folding marker - https://code.visualstudio.com/docs/editor/codebasics#_folding
def paging_parameters(
    offset: Annotated[int, Query(0)],
    limit: Annotated[int, Query()] = 1000,
):
    return {"offset": offset, "limit": limit}


def search_parameters(q: Annotated[str, Path()]):
    return {"q": q}


# To test nested resolved params
def searchable_page_parameters(
    paging_params: Annotated[dict[str, int], ResolvedParam(paging_parameters)],
    search_params: Annotated[dict[str, str], ResolvedParam(search_parameters)],
):
    return {
        "offset": paging_params["offset"],
        "limit": paging_params["limit"],
        "q": search_params["q"],
    }


@ma_dataclass
class PathParams:
    item_id: int


# For testing with native marshmallow schemas
class PathParamsSchema(ma.Schema):
    item_id = mf.Integer()


@ma_dataclass
class MultiPathParams:
    item_id: int
    sub_item_id: int


@ma_dataclass
class MultiQueryParams:
    name: str


@ma_dataclass
class MultiBodyParams:
    weight: float


@ma_dataclass
class MultiHeaderParams:
    color: str = 'blue'
# endregion
# endregion


############################################################
# Test API
############################################################
# region
@app.get("/paging")
def get_paging(paging_params: Annotated[dict[str, int], ResolvedParam(paging_parameters)]):
    return paging_params


@app.get("/filtered_paging_1/{q}")
def get_filtered_paging_1(search_params: Annotated[dict[str, str], ResolvedParam(search_parameters)]):
    return search_params


@app.get("/filtered_paging_2/{q}")
def get_filtered_paging_2(filtered_paging_params: Annotated[dict[str, int | str], ResolvedParam(searchable_page_parameters)]):
    return filtered_paging_params


@app.post("/optional_with_default")
def post_optional_with_default(
    optional_body: Annotated[dt.datetime | None, Body()] = dt.datetime.max,
):
    return {'optional_body': optional_body}


@app.post('/multi_combo_optional/{item_id}/{sub_item_id}')
def post_multi_combo_optional(
    item_id: int,
    path_params: Annotated[MultiPathParams, Path()],
    query_params: Annotated[MultiQueryParams | None, Query()],
    body_params: Annotated[MultiBodyParams | None, Body()],
    weight_unit: Annotated[Optional[Literal['lbs', 'kg']], Query(title='Weight')],
    color: Annotated[Union[str, None], Header('blue')],
    # Tests convert_underscores
    user_agent: Annotated[Optional[str], Header(None)],
    # Tests aliasing
    aliased_header: Annotated[Optional[str], Header(None, alias="myalias")],
):
    return {
        'item_id': item_id,
        'param_item_id': path_params.item_id,
        'sub_item': path_params.sub_item_id,
        # Special None response to signify that the entire object is None
        'name': query_params.name if query_params is not None else '__NONE__',
        'weight': body_params.weight if body_params is not None else '__NONE__',
        'weight_unit': weight_unit,
        'color': color,
        'user_agent': user_agent,
        'aliased_header': aliased_header,
    }
# endregion


############################################################
# Tests
############################################################
# region
client = TestClient(app)

openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/paging": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                    },
                },
                "summary": "Get Paging",
                "operationId": "get_paging_paging_get",
                "parameters": [
                    {
                        "required": False,
                        "schema": {
                            "default": 0,
                            "type": "integer",
                            "title": "Offset",
                        },
                        "name": "offset",
                        "in": "query",
                    },
                    {
                        "required": False,
                        "schema": {
                            "default": 1000,
                            "type": "integer",
                            "title": "Limit",
                        },
                        "name": "limit",
                        "in": "query",
                    },
                ],
            },
        },
        "/filtered_paging_1/{q}": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                    },
                },
                "summary": "Get Filtered Paging 1",
                "operationId": "get_filtered_paging_1_filtered_paging_1__q__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {
                            "type": "string",
                            "title": "Q",
                        },
                        "name": "q",
                        "in": "path",
                    },
                ],
            },
        },
        "/filtered_paging_2/{q}": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                    },
                },
                "summary": "Get Filtered Paging 2",
                "operationId": "get_filtered_paging_2_filtered_paging_2__q__get",
                "parameters": [
                    {
                        "required": False,
                        "schema": {
                            "default": 0,
                            "type": "integer",
                            "title": "Offset",
                        },
                        "name": "offset",
                        "in": "query",
                    },
                    {
                        "required": False,
                        "schema": {
                            "default": 1000,
                            "type": "integer",
                            "title": "Limit",
                        },
                        "name": "limit",
                        "in": "query",
                    },
                    {
                        "required": True,
                        "schema": {
                            "type": "string",
                            "title": "Q",
                        },
                        "name": "q",
                        "in": "path",
                    },
                ],
            },
        },
        "/optional_with_default": {
            "post": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                    },
                },
                "summary": "Post Optional With Default",
                "operationId": "post_optional_with_default_optional_with_default_post",
                "requestBody": {
                    "content": {
                        "application/json": {
                           "schema": {
                               "$ref": "#/components/schemas/Body_post_optional_with_default_optional_with_default_post",
                           },
                        },
                    },
                    "required": True,
                },
            },
        },
        "/multi_combo_optional/{item_id}/{sub_item_id}": {
            "post": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                    },
                },
                "summary": "Post Multi Combo Optional",
                "operationId": "post_multi_combo_optional_multi_combo_optional__item_id___sub_item_id__post",
                "parameters": [
                    {
                        'in': 'query',
                        'name': 'name',
                        'required': True,
                        'schema': {
                            'title': 'Name',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'weight_unit',
                        'required': False,
                        'schema': {
                            "default": None,
                            'enum': ['lbs', 'kg'],
                            "nullable": True,
                            'title': 'Weight',
                        },
                    },
                    {
                        'in': 'path',
                        'name': 'item_id',
                        'required': True,
                        'schema': {
                            'title': 'Item Id',
                            'type': 'integer',
                        },
                    },
                    {
                        'in': 'path',
                        'name': 'sub_item_id',
                        'required': True,
                        'schema': {
                            'title': 'Sub Item Id',
                            'type': 'integer',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'color',
                        'required': False,
                        'schema': {
                            'default': 'blue',
                            "nullable": True,
                            'title': 'Color',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'user_agent',
                        'required': False,
                        'schema': {
                            "default": None,
                            "nullable": True,
                            'title': 'User Agent',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'aliased_header',
                        'required': False,
                        'schema': {
                            "default": None,
                            "nullable": True,
                            'title': 'Myalias',
                            'type': 'string',
                        },
                    },
                ],
                'requestBody': {
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/MultiBodyParams'},
                        },
                    },
                    'required': False,
                },
            },
        },
    },
    "components": {
        "schemas": {
            "Body_post_optional_with_default_optional_with_default_post": {
                "properties": {
                    "optional_body": {
                        "default": "9999-12-31T23:59:59.999999",
                        "format": "date-time",
                        "nullable": True,
                        "title": "Optional Body",
                        "type": "string",
                    },
                },
                "required": [],
                "title": "Body_post_optional_with_default_optional_with_default_post",
                "type": "object",
            },
            "HTTPValidationError": {
                'properties': {
                    'detail': {
                        'description': 'Error detail',
                        'title': 'Detail',
                    },
                    'errors': {
                        'description': 'Exception or error type',
                        'title': 'Errors',
                    },
                    'status_code': {
                        'description': 'HTTP status code',
                        'title': 'Status Code',
                        'type': 'integer',
                    },
                },
                'required': ['detail', 'status_code'],
                'title': 'HTTPValidationError',
                'type': 'object',
            },
            "MultiBodyParams": {
                "type": "object",
                "properties": {
                    "weight": {
                        "type": "number",
                        "title": "Weight",
                    },
                },
                "required": [
                    "weight",
                ],
                "title": "Body Params",
            },
        },
    },
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/paging?limit=50", 200, {"offset": 0, "limit": 50}),
        ("/filtered_paging_1/name=foobar", 200, {"q": "name=foobar"}),
        (
            "/filtered_paging_2/name=foobar?limit=50", 200,
            {"offset": 0, "limit": 50, "q": "name=foobar"},
        ),
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)


@pytest.mark.parametrize(
    "path,headers,body,expected_status,expected_response",
    [
        (
            "/optional_with_default",
            {},
            {},
            200,
            {
                'optional_body': '9999-12-31T23:59:59.999999',
            },
        ),
        (
            "/optional_with_default",
            {},
            {
                'optional_body': None,
            },
            200,
            {
                'optional_body': None,
            },
        ),
        (
            "/multi_combo_optional/5/3",
            {},
            None,
            200,
            {
                'item_id': 5,
                'param_item_id': 5,
                'sub_item': 3,
                'name': '__NONE__',
                'weight': '__NONE__',
                'weight_unit': None,
                'color': 'blue',
                "user_agent": "testclient",
                "aliased_header": None,
            },
        ),
    ],
)
def test_post_path(path, headers, body, expected_status, expected_response):
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)

# endregion
