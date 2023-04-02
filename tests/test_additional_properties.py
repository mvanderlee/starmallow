from typing import Dict

from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import StarMallow

from .utils import assert_json

app = StarMallow()


@ma_dataclass
class Items:
    items: Dict[str, int]


@app.post("/foo")
def foo(items: Items):
    return items.items


client = TestClient(app)


openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/foo": {
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
                "summary": "Foo",
                "operationId": "foo_foo_post",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Items"},
                        },
                    },
                    "required": True,
                },
            },
        },
    },
    "components": {
        "schemas": {
            "Items": {
                "title": "Items",
                "required": ["items"],
                "type": "object",
                "properties": {
                    "items": {
                        "title": "Items",
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                },
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


def test_additional_properties_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_additional_properties_post():
    response = client.post("/foo", json={"items": {"foo": 1, "bar": 2}})
    assert response.status_code == 200, response.text
    assert response.json() == {"foo": 1, "bar": 2}
