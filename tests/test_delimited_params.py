import pytest
from starlette.testclient import TestClient

from starmallow import Body, Header, StarMallow
from starmallow.types import DelimitedListInt

from .utils import assert_json

app = StarMallow()


############################################################
# Test API
############################################################
# region
@app.get("/path/{item_ids}")
def get_path_ids(item_ids: DelimitedListInt):
    return item_ids


@app.get("/query")
def get_query_ids(item_ids: DelimitedListInt):
    return item_ids


@app.get("/header")
def get_header_ids(item_ids: DelimitedListInt = Header()):
    return item_ids


@app.post("/json")
def post_json_ids(item_ids: DelimitedListInt = Body()):
    return item_ids
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
        "/path/{item_ids}": {
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
                "summary": "Get Path Ids",
                "operationId": "get_path_ids_path__item_ids__get",
                "parameters": [
                    {
                        'explode': True,
                        "in": "path",
                        "name": "item_ids",
                        "schema": {
                            "items": {
                                "type": "integer",
                            },
                            "title": "Item Ids",
                            "type": "array",
                        },
                        "required": True,
                        "style": "form",
                    },
                ],
            },
        },
        "/query": {
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
                "summary": "Get Query Ids",
                "operationId": "get_query_ids_query_get",
                "parameters": [
                    {
                        'explode': True,
                        "in": "query",
                        "name": "item_ids",
                        "schema": {
                            "items": {
                                "type": "integer",
                            },
                            "title": "Item Ids",
                            "type": "array",
                        },
                        "required": True,
                        "style": "form",
                    },
                ],
            },
        },
        "/header": {
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
                "summary": "Get Header Ids",
                "operationId": "get_header_ids_header_get",
                "parameters": [
                    {
                        'explode': True,
                        "in": "header",
                        "name": "item_ids",
                        "schema": {
                            "items": {
                                "type": "integer",
                            },
                            "title": "Item Ids",
                            "type": "array",
                        },
                        "required": True,
                        "style": "form",
                    },
                ],
            },
        },
        "/json": {
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
                "summary": "Post Json Ids",
                "operationId": "post_json_ids_json_post",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_post_json_ids_json_post",
                            },
                        },
                    },
                    "required": True,
                },
            },
        },
    },
    "components": {
        "schemas": {
            "Body_post_json_ids_json_post": {
                "properties": {
                    "item_ids": {
                        "items": {"type": "integer"},
                        "title": "Item Ids",
                        "type": "array",
                    },
                },
                "required": ["item_ids"],
                "title": "Body_post_json_ids_json_post",
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
        },
    },
}


@pytest.mark.parametrize(
    "path,headers,expected_status,expected_response",
    [
        ("/path/1,2,3,4", {}, 200, [1, 2, 3, 4]),
        ("/query?item_ids=5,4,3,2", {}, 200, [5, 4, 3, 2]),
        ("/header", {'item_ids': '6,8,7'}, 200, [6, 8, 7]),
        ("/openapi.json", {}, 200, openapi_schema),
    ],
)
def test_get_path(path, headers, expected_status, expected_response):
    response = client.get(path, headers=headers)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)


@pytest.mark.parametrize(
    "path,headers,body,expected_status,expected_response",
    [
        ("/json", {}, {'item_ids': '1,3,5'}, 200, [1, 3, 5]),
    ],
)
def test_post_path(path, headers, body, expected_status, expected_response):
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
# endregion
