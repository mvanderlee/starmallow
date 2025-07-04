from marshmallow_dataclass2 import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.params import ResolvedParam, Security
from starmallow.security.api_key import APIKeyHeader

from ...utils import assert_json

app = StarMallow()

api_key = APIKeyHeader(name="key", auto_error=False)


@ma_dataclass
class User:
    username: str


def get_current_user(oauth_header: str | None = Security(api_key)):
    if oauth_header is None:
        return None
    user = User(username=oauth_header)
    return user


@app.get("/users/me")
def read_current_user(current_user: User | None = ResolvedParam(get_current_user)):
    if current_user is None:
        return {"msg": "Create an account first"}
    return current_user


client = TestClient(app)

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
                "security": [{"APIKeyHeader": []}],
            },
        },
    },
    "components": {
        "securitySchemes": {
            "APIKeyHeader": {"type": "apiKey", "name": "key", "in": "header"},
        },
    },
}


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_security_api_key():
    response = client.get("/users/me", headers={"key": "secret"})
    assert response.status_code == 200, response.text
    assert response.json() == {"username": "secret"}


def test_security_api_key_no_key():
    response = client.get("/users/me")
    assert response.status_code == 200, response.text
    assert response.json() == {"msg": "Create an account first"}
