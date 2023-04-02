from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from starmallow import APIRouter, StarMallow
from starmallow.types import HttpUrl

from .utils import assert_json


@ma_dataclass
class CustomModel:
    a: int


app = StarMallow()

callback_router = APIRouter(default_response_class=JSONResponse)


@callback_router.get(
    "{$callback_url}/callback/", responses={400: {"model": CustomModel}},
)
def callback_route():
    pass  # pragma: no cover


@app.post("/", callbacks=callback_router.routes)
def main_route(callback_url: HttpUrl):
    pass  # pragma: no cover


openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/": {
            "post": {
                "summary": "Main Route",
                "operationId": "main_route__post",
                "parameters": [
                    {
                        "required": True,
                        "schema": {
                            "title": "Callback Url",
                            "type": "string",
                            "format": "url",
                        },
                        "name": "callback_url",
                        "in": "query",
                    },
                ],
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
                "callbacks": {
                    "callback_route": {
                        "{$callback_url}/callback/": {
                            "get": {
                                "summary": "Callback Route",
                                "operationId": "callback_route__callback_url__callback__get",
                                "responses": {
                                    "400": {
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "$ref": "#/components/schemas/CustomModel",
                                                },
                                            },
                                        },
                                        "description": "Bad Request",
                                    },
                                    "200": {
                                        "description": "Successful Response",
                                        "content": {"application/json": {"schema": {}}},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
    "components": {
        "schemas": {
            "CustomModel": {
                "title": "CustomModel",
                "required": ["a"],
                "type": "object",
                "properties": {"a": {"title": "A", "type": "integer"}},
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

client = TestClient(app)


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)
