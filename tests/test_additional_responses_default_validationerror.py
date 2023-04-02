from starlette.testclient import TestClient

from starmallow import StarMallow

from .utils import assert_json

app = StarMallow()


@app.get("/a/{id}")
async def a(id):
    pass  # pragma: no cover


openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/a/{id}": {
            "get": {
                "responses": {
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
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "A",
                "operationId": "a_a__id__get",
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Id"},
                        "name": "id",
                        "in": "path",
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
        },
    },
}


client = TestClient(app)


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)
