'''
    Tests various permutations of accepting input. i.e.: Path, Query, Body, etc
'''

from typing import Any, Dict, Literal

import marshmallow as ma
import marshmallow.fields as mf
import pytest
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.background import BackgroundTasks
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from starlette.testclient import TestClient

from starmallow import Body, Header, NoParam, Path, Query, StarMallow

from .utils import assert_json

app = StarMallow()


############################################################
# Models  -  classes and schemas
############################################################
# region  -  VS Code folding marker - https://code.visualstudio.com/docs/editor/codebasics#_folding
# For testing with marshmallow dataclass
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


############################################################
# Test API
############################################################
# region
# Test no annotations - autodetect string type
@app.get("/path/{item_id}")
def get_path_id(item_id):
    return item_id


# Test with request parameter
@app.get("/path_with_request/{item_id}")
def get_path_with_request(item_id, request: Request):
    return isinstance(request, Request)


# Test with httpconnection parameter
@app.get("/path_with_http_connection/{item_id}")
def get_path_with_http_connection(item_id, httpconn: HTTPConnection):
    return isinstance(httpconn, HTTPConnection)


# Test with response parameter
@app.get("/path_with_response/{item_id}")
def get_path_with_response(item_id, response: Response):
    return isinstance(response, Response)


# Test with background tasks parameter
@app.get("/path_with_background_tasks/{item_id}")
def get_path_with_background_tasks(item_id, tasks: BackgroundTasks):
    return isinstance(tasks, BackgroundTasks)


# Test with no field parameter
@app.get("/path_with_noparam/{item_id}")
def get_path_with_noparam(item_id, empty: str = NoParam()):
    # Expected this to be provided by a 3rd party decorator.
    # Since it isn't, it will be NoParams()
    return isinstance(empty, NoParam)


# Test that type annotation is honored
@app.get("/path/int/{item_id}")
def get_path_int_id(item_id: int):
    return item_id


# Test with explicit location option
@app.get("/path/param/{item_id}")
def get_path_param_id(item_id: int = Path()):
    return item_id


# Test with marshmallow dataclass
@app.get("/path/ma_dataclass/{item_id}")
def get_path_ma_dataclass_id(path_params: PathParams = Path()):
    return path_params.item_id


# Test with marshmallow dataclass schema
@app.get("/path/ma_schema/{item_id}")
def get_path_ma_schema_id(path_params: PathParams.Schema = Path()):
    return path_params.item_id


# Test with marshmallow schema as model instead of annotation
@app.get("/path/model_schema/{item_id}")
def get_path_model_ma_schema_id(path_params=Path(model=PathParamsSchema)):
    return path_params['item_id']


# Test with marshmallow schema as model to override the annotation
@app.get("/path/model_override/{item_id}")
def get_path_override_ma_schema_id(path_params: Dict[Any, Any] = Path(model=PathParamsSchema)):
    return path_params['item_id']


# Test with flat arguments - no schemas
@app.post('/multi_flat/{item_id}/{sub_item_id}')
def post_multi_flat(
    item_id: int,
    sub_item_id,
    name: str,  # Query
    weight: float = Body(),
    color: str = Header('blue'),
):
    return {
        'item_id': item_id,
        'sub_item': sub_item_id,
        'name': name,
        'weight': weight,
        'color': color,
    }


# Test with only schemas
@app.post('/multi_schema/{item_id}/{sub_item_id}')
def post_multi_schema(
    path_params: MultiPathParams = Path(),
    query_params: MultiQueryParams = Query(),
    body_params: MultiBodyParams = Body(),
    header_params: MultiHeaderParams = Header(),
):
    return {
        'item_id': path_params.item_id,
        'sub_item': path_params.sub_item_id,
        'name': query_params.name,
        'weight': body_params.weight,
        'color': header_params.color,
    }


# Test with flat arguments and schemas, and even some overlap, duplicated fields in flat and schema
@app.post('/multi_combo/{item_id}/{sub_item_id}')
def post_multi_combo(
    item_id: int,
    path_params: MultiPathParams = Path(),
    query_params: MultiQueryParams = Query(),
    body_params: MultiBodyParams = Body(),
    weight_unit: Literal['lbs', 'kg'] = Query(),
    color: str = Header('blue'),
):
    return {
        'item_id': item_id,
        'param_item_id': path_params.item_id,
        'sub_item': path_params.sub_item_id,
        'name': query_params.name,
        'weight': body_params.weight,
        'weight_unit': weight_unit,
        'color': color,
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
        "/path/{item_id}": {
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
                "summary": "Get Path Id",
                "operationId": "get_path_id_path__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path_with_request/{item_id}": {
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
                "summary": "Get Path With Request",
                "operationId": "get_path_with_request_path_with_request__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path_with_http_connection/{item_id}": {
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
                "summary": "Get Path With Http Connection",
                "operationId": "get_path_with_http_connection_path_with_http_connection__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path_with_response/{item_id}": {
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
                "summary": "Get Path With Response",
                "operationId": "get_path_with_response_path_with_response__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path_with_background_tasks/{item_id}": {
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
                "summary": "Get Path With Background Tasks",
                "operationId": "get_path_with_background_tasks_path_with_background_tasks__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path_with_noparam/{item_id}": {
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
                "summary": "Get Path With Noparam",
                "operationId": "get_path_with_noparam_path_with_noparam__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path/int/{item_id}": {
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
                "summary": "Get Path Int Id",
                "operationId": "get_path_int_id_path_int__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id", "type": "integer"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path/param/{item_id}": {
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
                "summary": "Get Path Param Id",
                "operationId": "get_path_param_id_path_param__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id", "type": "integer"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/path/ma_dataclass/{item_id}": {
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
                "summary": "Get Path Ma Dataclass Id",
                "operationId": "get_path_ma_dataclass_id_path_ma_dataclass__item_id__get",
                "parameters": [
                    {
                        "in": "path",
                        "name": "path_params",
                        "required": True,
                        "schema": {
                            "title": "Path Params",
                            "allOf": [
                                {
                                    "$ref": "#/components/schemas/PathParams",
                                },
                            ],
                        },
                    },
                ],
            },
        },
        "/path/ma_schema/{item_id}": {
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
                "summary": "Get Path Ma Schema Id",
                "operationId": "get_path_ma_schema_id_path_ma_schema__item_id__get",
                "parameters": [
                    {
                        "in": "path",
                        "name": "path_params",
                        "required": True,
                        "schema": {
                            "title": "Path Params",
                            "allOf": [
                                {
                                    "$ref": "#/components/schemas/PathParams",
                                },
                            ],
                        },
                    },
                ],
            },
        },
        "/path/model_schema/{item_id}": {
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
                "summary": "Get Path Model Ma Schema Id",
                "operationId": "get_path_model_ma_schema_id_path_model_schema__item_id__get",
                "parameters": [
                    {
                        "in": "path",
                        "name": "path_params",
                        "required": True,
                        "schema": {
                            "title": "Path Params",
                            "allOf": [
                                {
                                    "$ref": "#/components/schemas/PathParams1",
                                },
                            ],
                        },
                    },
                ],
            },
        },
        "/path/model_override/{item_id}": {
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
                "summary": "Get Path Override Ma Schema Id",
                "operationId": "get_path_override_ma_schema_id_path_model_override__item_id__get",
                "parameters": [
                    {
                        "in": "path",
                        "name": "path_params",
                        "required": True,
                        "schema": {
                            "title": "Path Params",
                            "allOf": [
                                {
                                    "$ref": "#/components/schemas/PathParams1",
                                },
                            ],
                        },
                    },
                ],
            },
        },
        "/multi_flat/{item_id}/{sub_item_id}": {
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
                "summary": "Post Multi Flat",
                "operationId": "post_multi_flat_multi_flat__item_id___sub_item_id__post",
                "parameters": [
                    {
                        "in": "query",
                        "name": "name",
                        "required": True,
                        "schema": {
                            "type": "string",
                            "title": "Name",
                        },
                    },
                    {
                        "in": "path",
                        "name": "item_id",
                        "required": True,
                        "schema": {
                            "type": "integer",
                            "title": "Item Id",
                        },
                    },
                    {
                        "in": "path",
                        "name": "sub_item_id",
                        "required": True,
                        "schema": {
                            "title": "Sub Item Id",
                        },
                    },
                    {
                        "in": "header",
                        "name": "color",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "default": "blue",
                            "title": "Color",
                        },
                    },
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_post_multi_flat_multi_flat__item_id___sub_item_id__post",
                            },
                        },
                    },
                    "required": True,
                },
            },
        },
        "/multi_schema/{item_id}/{sub_item_id}": {
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
                "summary": "Post Multi Schema",
                "operationId": "post_multi_schema_multi_schema__item_id___sub_item_id__post",
                "parameters": [
                    {
                        'in': 'query',
                        'name': 'query_params',
                        'required': True,
                        'schema': {
                            'allOf': [{'$ref': '#/components/schemas/MultiQueryParams'}],
                            'title': 'Query Params',
                        },
                    },
                    {
                        'in': 'path',
                        'name': 'path_params',
                        'required': True,
                        'schema': {
                            'allOf': [{'$ref': '#/components/schemas/MultiPathParams'}],
                            'title': 'Path Params',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'header_params',
                        'required': True,
                        'schema': {
                            'allOf': [{'$ref': '#/components/schemas/MultiHeaderParams'}],
                            'title': 'Header Params',
                        },
                    },
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                '$ref': '#/components/schemas/MultiBodyParams',
                            },
                        },
                    },
                    "required": True,
                },
            },
        },
        "/multi_combo/{item_id}/{sub_item_id}": {
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
                "summary": "Post Multi Combo",
                "operationId": "post_multi_combo_multi_combo__item_id___sub_item_id__post",
                "parameters": [
                    {
                        'in': 'query',
                        'name': 'query_params',
                        'required': True,
                        'schema': {
                            'allOf': [{'$ref': '#/components/schemas/MultiQueryParams'}],
                            'title': 'Query Params',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'weight_unit',
                        'required': True,
                        'schema': {
                            'enum': ['lbs', 'kg'],
                            'title': 'Weight Unit',
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
                        'name': 'path_params',
                        'required': True,
                        'schema': {
                            'allOf': [{'$ref': '#/components/schemas/MultiPathParams'}],
                            'title': 'Path Params',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'color',
                        'required': False,
                        'schema': {
                            'default': 'blue',
                            'title': 'Color',
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
                    'required': True,
                },
            },
        },
    },
    "components": {
        "schemas": {
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
            "Body_post_multi_flat_multi_flat__item_id___sub_item_id__post": {
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
                "title": "Body_post_multi_flat_multi_flat__item_id___sub_item_id__post",
            },
            "PathParams": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "title": "Item Id",
                    },
                },
                "required": [
                    "item_id",
                ],
                "title": "Path Params",
            },
            "PathParams1": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "title": "Item Id",
                    },
                },
                "title": "Path Params",
            },
            "MultiPathParams": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "title": "Item Id",
                    },
                    "sub_item_id": {
                        "type": "integer",
                        "title": "Sub Item Id",
                    },
                },
                "required": [
                    "item_id",
                    "sub_item_id",
                ],
                "title": "Path Params",
            },
            "MultiQueryParams": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "title": "Name",
                    },
                },
                "required": [
                    "name",
                ],
                "title": "Query Params",
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
            "MultiHeaderParams": {
                "type": "object",
                "properties": {
                    "color": {
                        "type": "string",
                        "default": "blue",
                        "title": "Color",
                    },
                },
                "title": "Header Params",
            },
        },
    },
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/path/5", 200, '5'),
        ("/path_with_request/5", 200, True),
        ("/path_with_http_connection/5", 200, True),
        ("/path_with_response/5", 200, True),
        ("/path_with_background_tasks/5", 200, True),
        ("/path_with_noparam/5", 200, True),
        ("/path/int/5", 200, 5),
        ("/path/param/5", 200, 5),
        ("/path/ma_dataclass/5", 200, 5),
        ("/path/ma_schema/5", 200, 5),
        ("/path/model_schema/5", 200, 5),
        ("/path/model_override/5", 200, 5),
        ("/nonexistent", 404, {"detail": "Not Found"}),
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
            "/multi_flat/5/3?name=foobar",
            {'color': 'red'},
            {'weight': 95.2},
            200,
            {
                'item_id': 5,
                'sub_item': '3',
                'name': 'foobar',
                'weight': 95.2,
                'color': 'red',
            },
        ),
        (
            "/multi_schema/5/3?name=foobar",
            {'color': 'red'},
            {'weight': 95.2},
            200,
            {
                'item_id': 5,
                'sub_item': 3,
                'name': 'foobar',
                'weight': 95.2,
                'color': 'red',
            },
        ),
        (
            "/multi_combo/5/3?name=foobar&weight_unit=lbs",
            {'color': 'red'},
            {'weight': 95.2},
            200,
            {
                'item_id': 5,
                'param_item_id': 5,
                'sub_item': 3,
                'name': 'foobar',
                'weight': 95.2,
                'weight_unit': 'lbs',
                'color': 'red',
            },
        ),
    ],
)
def test_post_path(path, headers, body, expected_status, expected_response):
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)


@pytest.mark.parametrize(
    "path,headers,body,expected_status,expected_response",
    [
        (
            "/multi_flat/alpha/beta?name=foobar",
            {'color': 'red'},
            {'weight': 'twenty'},
            422,
            {
                "detail": {
                    "json": {
                        "weight": ["Not a valid number."],
                    },
                    "path": {
                        "item_id": ["Not a valid integer."],
                    },
                },
                "error": "ValidationError",
                "status_code": 422,
            },
        ),
        (
            "/multi_schema/alpha/beta?name=foobar",
            {'color': 'red'},
            {'weight': 'twenty'},
            422,
            {
                "detail": {
                    "json": {
                        "weight": ["Not a valid number."],
                    },
                    "path": {
                        "item_id": ["Not a valid integer."],
                        "sub_item_id": ["Not a valid integer."],
                    },
                },
                "error": "ValidationError",
                "status_code": 422,
            },
        ),
        (
            "/multi_combo/alpha/beta?name=foobar&weight_unit=notkilos",
            {'color': 'red'},
            {'weight': 'twenty'},
            422,
            {
                "detail": {
                    "json": {
                        "weight": ["Not a valid number."],
                    },
                    "path": {
                        "item_id": ["Not a valid integer.", "Not a valid integer."],
                        "sub_item_id": ["Not a valid integer."],
                    },
                    "query": {
                        "weight_unit": ["Must be one of: lbs, kg."],
                    },
                },
                "error": "ValidationError",
                "status_code": 422,
            },
        ),
    ],
)
def test_post_path_validation(path, headers, body, expected_status, expected_response):
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
# endregion
