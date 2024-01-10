import pytest
from httpx import Response
from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.decorators import route
from starmallow.endpoints import APIHTTPEndpoint
from starmallow.routing import APIRouter

from .utils import assert_json

app = StarMallow()

client = TestClient(app)


@app.api_route("/api_route")
class NonOperation(APIHTTPEndpoint):
    def get(self):
        return {"message": "Get World"}

    def post(self):
        return {"message": "Post World"}

    def put(self):
        return {"message": "Put World"}

    def delete(self):
        return {"message": "Delete World"}

    def patch(self):
        return {"message": "Patch World"}

    def options(self):
        return {"message": "Options World"}

    def head(self):
        return {"message": "Head World"}


@app.api_route("/path/str/{item_id}")
class StringId(APIHTTPEndpoint):
    def get(self, item_id: str) -> str:
        return item_id


router = APIRouter(prefix='/overrides', tags=['Overrides'])


@router.api_route("")
class Overrides(APIHTTPEndpoint):
    @route(name='OverriddenGet')
    def get(self):
        return {"message": "Get World"}

    @route(deprecated=True)
    def post(self):
        return {"message": "Post World"}

    @route(operation_id='CustomOperation')
    def put(self):
        return {"message": "Put World"}

    @route(status_code=204)
    def delete(self):
        return {"message": "Delete World"}

    @route(tags=['alpha', 'beta'])
    def patch(self):
        return {"message": "Patch World"}

    @route(include_in_schema=False)
    def options(self):
        return {"message": "Options World"}


app.include_router(router)


openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/api_route": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Non Operation Get",
                "operationId": "NonOperation_get_api_route_get",
            },
            "post": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Non Operation Post",
                "operationId": "NonOperation_post_api_route_post",
            },
            "put": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Non Operation Put",
                "operationId": "NonOperation_put_api_route_put",
            },
            "patch": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Non Operation Patch",
                "operationId": "NonOperation_patch_api_route_patch",
            },
            "delete": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Non Operation Delete",
                "operationId": "NonOperation_delete_api_route_delete",
            },
            "options": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Non Operation Options",
                "operationId": "NonOperation_options_api_route_options",
            },
        },
        "/path/str/{item_id}": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string"}}},
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
                "summary": "String Id Get",
                "operationId": "StringId_get_path_str__item_id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Item Id", "type": "string"},
                        "name": "item_id",
                        "in": "path",
                    },
                ],
            },
        },
        "/overrides": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "tags": [
                    "Overrides",
                ],
                "summary": "Overridden Get",
                "operationId": "OverriddenGet_overrides_get",
            },
            "post": {
                "deprecated": True,
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "tags": [
                    "Overrides",
                ],
                "summary": "Overrides Post",
                "operationId": "Overrides_post_overrides_post",
            },
            "put": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "tags": [
                    "Overrides",
                ],
                "summary": "Overrides Put",
                "operationId": "CustomOperation",
            },
            "patch": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Overrides Patch",
                "operationId": "Overrides_patch_overrides_patch",
                "tags": ["Overrides", "alpha", "beta"],
            },
            "delete": {
                "responses": {
                    "204": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "tags": [
                    "Overrides",
                ],
                "summary": "Overrides Delete",
                "operationId": "Overrides_delete_overrides_delete",
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
        },
    },
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/api_route", 200, {"message": "Get World"}),
        ("/path/str/foobar", 200, 'foobar'),
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)


@pytest.mark.parametrize(
    "fn,expected_response",
    [
        (client.get, {"message": "Get World"}),
        (client.post, {"message": "Post World"}),
        (client.put, {"message": "Put World"}),
        (client.delete, {"message": "Delete World"}),
        (client.patch, {"message": "Patch World"}),
        (client.options, {"message": "Options World"}),
        (client.head, b''),
    ],
)
def test_non_operation_methods(fn, expected_response):
    response: Response = fn("/api_route")
    assert response.status_code == 200
    if isinstance(expected_response, dict):
        assert_json(response.json(), expected_response)
    else:
        assert response.content == expected_response
