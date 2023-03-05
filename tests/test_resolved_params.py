'''Test Resolved Params'''

import pytest
from starlette.testclient import TestClient

from starmallow import Path, Query, ResolvedParam, StarMallow

from .utils import assert_json

app = StarMallow()


############################################################
# Models  -  classes and schemas
############################################################
# region  -  VS Code folding marker - https://code.visualstudio.com/docs/editor/codebasics#_folding
def paging_parameters(
    offset: int = Query(0),
    limit: int = 1000,
):
    return {"offset": offset, "limit": limit}


def search_parameters(q: str = Path()):
    return {"q": q}


# To test nested resolved params
def searchable_page_parameters(
    paging_params=ResolvedParam(paging_parameters),
    search_params=ResolvedParam(search_parameters),
):
    return {
        "offset": paging_params["offset"],
        "limit": paging_params["limit"],
        "q": search_params["q"],
    }
# endregion


############################################################
# Test API
############################################################
# region
@app.get("/paging")
def get_paging(paging_params=ResolvedParam(paging_parameters)):
    return paging_params


@app.get("/filtered_paging_1/{q}")
def get_filtered_paging_1(search_params=ResolvedParam(search_parameters)):
    return search_params


@app.get("/filtered_paging_2/{q}")
def get_filtered_paging_2(filtered_paging_params=ResolvedParam(searchable_page_parameters)):
    return filtered_paging_params
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
        ("/paging?limit=50", 200, {"offset": 0, "limit": 50}),
        ("/filtered_paging_1/name=foobar", 200, {"q": "name=foobar"}),
        ("/filtered_paging_2/name=foobar?limit=50", 200, {"offset": 0, "limit": 50, "q": "name=foobar"}),
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)

# endregion
