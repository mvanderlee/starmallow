from marshmallow_dataclass2 import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.params import ResolvedParam, Security
from starmallow.security.api_key import APIKeyCookie

from ...utils import assert_json

app = StarMallow()

api_key = APIKeyCookie(name="key", description="An API Cookie Key")


@ma_dataclass
class User:
    username: str


def get_current_user(oauth_header: str = Security(api_key)):
    user = User(username=oauth_header)
    return user


@app.get("/users/me")
def read_current_user(current_user: User = ResolvedParam(get_current_user)):
    return current_user


openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
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
                "security": [{"APIKeyCookie": []}],
            },
        },
    },
    "components": {
        "securitySchemes": {
            "APIKeyCookie": {
                "type": "apiKey",
                "name": "key",
                "in": "cookie",
                "description": "An API Cookie Key",
            },
        },
    },
}


def test_openapi_schema():
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_security_api_key():
    client = TestClient(app, cookies={"key": "secret"})
    response = client.get("/users/me")
    assert response.status_code == 200, response.text
    assert response.json() == {"username": "secret"}


def test_security_api_key_no_key():
    client = TestClient(app)
    response = client.get("/users/me")
    assert response.status_code == 403, response.text
    assert response.json() == {"detail": "Not authenticated"}
