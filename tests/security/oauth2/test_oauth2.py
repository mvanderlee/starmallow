import pytest
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.params import ResolvedParam, Security
from starmallow.security.oauth2 import OAuth2, OAuth2PasswordRequestFormStrict

from ...utils import assert_json

app = StarMallow()

reusable_oauth2 = OAuth2(
    flows={
        "password": {
            "tokenUrl": "token",
            "scopes": {"read:users": "Read the users", "write:users": "Create users"},
        },
    },
)


@ma_dataclass
class User:
    username: str


# Here we use string annotations to test them
def get_current_user(oauth_header: "str" = Security(reusable_oauth2)):
    user = User(username=oauth_header)
    return user


@app.post("/login")
# Here we use string annotations to test them
def login(form_data: OAuth2PasswordRequestFormStrict = ResolvedParam()):
    return form_data


@app.get("/users/me")
# Here we use string annotations to test them
def read_current_user(current_user: "User" = ResolvedParam(get_current_user)):
    return current_user


client = TestClient(app)

openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/login": {
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
                "summary": "Login",
                "operationId": "login_login_post",
                "requestBody": {
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_login_login_post",
                            },
                        },
                    },
                    "required": True,
                },
            },
        },
        "/users/me": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Read Current User",
                "operationId": "read_current_user_users_me_get",
                "security": [{"OAuth2": []}],
            },
        },
    },
    "components": {
        "schemas": {
            "Body_login_login_post": {
                "title": "Body_login_login_post",
                "required": ["grant_type", "username", "password"],
                "type": "object",
                "properties": {
                    "grant_type": {
                        "title": "Grant Type",
                        "pattern": "password",
                        "type": "string",
                    },
                    "username": {"title": "Username", "type": "string"},
                    "password": {"title": "Password", "type": "string"},
                    "scope": {"title": "Scope", "type": "string", "default": ""},
                    "client_id": {"default": None, "nullable": True, "title": "Client Id", "type": "string"},
                    "client_secret": {"default": None, "nullable": True, "title": "Client Secret", "type": "string"},
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
        "securitySchemes": {
            "OAuth2": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "scopes": {
                            "read:users": "Read the users",
                            "write:users": "Create users",
                        },
                        "tokenUrl": "token",
                    },
                },
            },
        },
    },
}


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_security_oauth2():
    response = client.get("/users/me", headers={"Authorization": "Bearer footokenbar"})
    assert response.status_code == 200, response.text
    assert response.json() == {"username": "Bearer footokenbar"}


def test_security_oauth2_password_other_header():
    response = client.get("/users/me", headers={"Authorization": "Other footokenbar"})
    assert response.status_code == 200, response.text
    assert response.json() == {"username": "Other footokenbar"}


def test_security_oauth2_password_bearer_no_header():
    response = client.get("/users/me")
    assert response.status_code == 403, response.text
    assert response.json() == {"detail": "Not authenticated"}


required_params = {
    'detail': {
        'form': {
            'grant_type': ['Missing data for required field.'],
            'password': ['Missing data for required field.'],
            'username': ['Missing data for required field.'],
        },
    },
    'error': 'ValidationError',
    'status_code': 422,
}

grant_type_required = {
    'detail': {
        'form': {
            'grant_type': ['Missing data for required field.'],
        },
    },
    'error': 'ValidationError',
    'status_code': 422,
}

grant_type_incorrect = {
    'detail': {
        'form': {
            'grant_type': ['String does not match expected pattern.'],
        },
    },
    'error': 'ValidationError',
    'status_code': 422,
}


@pytest.mark.parametrize(
    "data,expected_status,expected_response",
    [
        (None, 422, required_params),
        ({"username": "johndoe", "password": "secret"}, 422, grant_type_required),
        (
            {"username": "johndoe", "password": "secret", "grant_type": "incorrect"},
            422,
            grant_type_incorrect,
        ),
        (
            {"username": "johndoe", "password": "secret", "grant_type": "password"},
            200,
            {
                "grant_type": "password",
                "username": "johndoe",
                "password": "secret",
                "scopes": [],
                "client_id": None,
                "client_secret": None,
            },
        ),
    ],
)
def test_strict_login(data, expected_status, expected_response):
    response = client.post("/login", data=data)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
