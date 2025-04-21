'''Test Resolved Params'''
from dataclasses import field
from typing import Annotated, Generic, TypeVar

import pytest
from marshmallow_dataclass2 import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import Query, StarMallow

from .utils import assert_json

app = StarMallow()

T = TypeVar("T")

############################################################
# Models  -  classes and schemas
############################################################
# region  -  VS Code folding marker - https://code.visualstudio.com/docs/editor/codebasics#_folding


@ma_dataclass
class QueryParameters(Generic[T]):
    id: T = None


@ma_dataclass
class PageableResponse(Generic[T]):
    items: list[T] = field(default_factory=list)
# endregion


############################################################
# Test API
############################################################
# region
@app.get("/data")
def get_data(
    params: Annotated[QueryParameters[int], Query()],
) -> PageableResponse[str]:
    return {'items': ['foo', 'bar']}
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
        "/data": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PageableResponse",
                                },
                            },
                        },
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
                "summary": "Get Data",
                "operationId": "get_data_data_get",
                "parameters": [
                    {
                        "required": False,
                        "schema": {
                            "default": None,
                            "nullable": True,
                            "type": "integer",
                            "title": "Id",
                        },
                        "name": "id",
                        "in": "query",
                    },
                ],
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
            "PageableResponse": {
                "properties": {
                    "items": {
                        "items": {
                            "type": "string",
                        },
                        "title": "Items",
                        "type": "array",
                    },
                },
                "title": "PageableResponse",
                "type": "object",
            },
        },
    },
}


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_response"),
    [
        ("/data?id=50", 200, {"items": ["foo", "bar"]}),
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
# endregion
