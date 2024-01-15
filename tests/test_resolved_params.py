'''Test Resolved Params'''

from typing import Annotated, Tuple
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from starmallow import Path, Query, ResolvedParam, Security, StarMallow
from starmallow.security.api_key import APIKeyHeader

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

# Goal is to mimic a db connection that is used by both the API and the Security param
# Ensure that we can resolve nexted resolved params that have shared dependencies
# And ensure a single db session is used. (we'll mimic the db session)


async def get_session():
    yield uuid4()
DBSession = Annotated[str, ResolvedParam(get_session)]
Token = Annotated[str, Security(APIKeyHeader(name='Authorization'))]


def get_item_from_token(session: DBSession, token: Token):
    return (session, token)
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


@app.get("/nested")
def get_nested(
    session: DBSession,
    item: Tuple[str, str] = ResolvedParam(get_item_from_token),
):
    assert session == item[0]
    return {
        'token': item[1],
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
        "/nested": {
            "get": {
                "operationId": "get_nested_nested_get",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {},
                            },
                        },
                        "description": "Successful Response",
                    },
                },
                "security": [
                    {
                        "APIKeyHeader": [],
                    },
                ],
                "summary": "Get Nested",
            },
        },
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
        "securitySchemes": {
            "APIKeyHeader": {
                "in": "header",
                "name": "Authorization",
                "type": "apiKey",
            },
        },
    },
}


@pytest.mark.parametrize(
    "path,headers,expected_status,expected_response",
    [
        ("/paging?limit=50", {}, 200, {"offset": 0, "limit": 50}),
        ("/filtered_paging_1/name=foobar", {}, 200, {"q": "name=foobar"}),
        (
            "/filtered_paging_2/name=foobar?limit=50", {}, 200,
            {"offset": 0, "limit": 50, "q": "name=foobar"},
        ),
        ("/nested", {'Authorization': 'ABCDEF'}, 200, {'token': 'ABCDEF'}),
        ("/openapi.json", {}, 200, openapi_schema),
    ],
)
def test_get_path(path, headers, expected_status, expected_response):
    response = client.get(path, headers=headers)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
# endregion
