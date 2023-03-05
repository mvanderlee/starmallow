'''
    Tests various permutations of accepting input. i.e.: Path, Query, Body, etc
'''
from typing import List

import pytest
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import Body, StarMallow
from starmallow.dataclasses import dump_only_field, optional_field, required_field

from .utils import assert_json

app = StarMallow()


############################################################
# Models  -  classes and schemas
############################################################
# region  -  VS Code folding marker - https://code.visualstudio.com/docs/editor/codebasics#_folding
# For testing with marshmallow dataclass
@ma_dataclass
class FieldBody:
    alpha: str = required_field(description="this field is required")
    beta: int = optional_field()
    charlie: bool = dump_only_field(default=True)
    delta: List[str] = optional_field(default_factory=lambda: ['foobar'])
# endregion


############################################################
# Test API
############################################################
# region
# Test with only schemas
@app.post('/dataclass_fields')
def post_dataclass_fields(
    field_body: FieldBody = Body(),
) -> FieldBody:
    return field_body
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

        "/dataclass_fields": {
            "post": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FieldBody"}}},
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
                "summary": "Post Dataclass Fields",
                "operationId": "post_dataclass_fields_dataclass_fields_post",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/FieldBody",
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
            "FieldBody": {
                "type": "object",
                "properties": {
                    "alpha": {
                        "description": "this field is required",
                        "type": "string",
                        "title": "Alpha",
                    },
                    "beta": {
                        "default": None,
                        "nullable": True,
                        "type": "integer",
                        "title": "Beta",
                    },
                    "charlie": {
                        "default": True,
                        "readOnly": True,
                        "type": "boolean",
                        "title": "Charlie",
                    },
                    "delta": {
                        "items": {
                            "type": "string",
                        },
                        "title": "Delta",
                        "type": "array",
                    },
                },
                "required": [
                    "alpha",
                ],
                "title": "Field Body",
            },
        },
    },
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)


@pytest.mark.parametrize(
    "path,body,expected_status,expected_response",
    [
        (
            "/dataclass_fields",
            {
                "alpha": "foobar",
                "beta": 10,
            },
            200,
            {
                'alpha': "foobar",
                'beta': 10,
                'charlie': True,
                'delta': ['foobar'],
            },
        ),
        # Validate that charlie is ignored as input
        (
            "/dataclass_fields",
            {
                "alpha": "foobar",
                "beta": 10,
                'charlie': False,
                'delta': ['barfoo'],
            },
            200,
            {
                'alpha': "foobar",
                'beta': 10,
                'charlie': True,
                'delta': ['barfoo'],
            },
        ),
    ],
)
def test_post_path(path, body, expected_status, expected_response):
    response = client.post(path, json=body)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
# endregion
