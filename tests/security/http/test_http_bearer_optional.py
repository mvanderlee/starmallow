from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.params import Security
from starmallow.security.http import HTTPAuthorizationCredentials, HTTPBearer

from ...utils import assert_json

app = StarMallow()

security = HTTPBearer(auto_error=False)


@app.get("/users/me")
def read_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
):
    if credentials is None:
        return {"msg": "Create an account first"}
    return {"scheme": credentials.scheme, "credentials": credentials.credentials}


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
                "security": [{"HTTPBearer": []}],
            },
        },
    },
    "components": {
        "securitySchemes": {"HTTPBearer": {"type": "http", "scheme": "bearer"}},
    },
}


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_security_http_bearer():
    response = client.get("/users/me", headers={"Authorization": "Bearer foobar"})
    assert response.status_code == 200, response.text
    assert response.json() == {"scheme": "Bearer", "credentials": "foobar"}


def test_security_http_bearer_no_credentials():
    response = client.get("/users/me")
    assert response.status_code == 200, response.text
    assert response.json() == {"msg": "Create an account first"}


def test_security_http_bearer_incorrect_scheme_credentials():
    response = client.get("/users/me", headers={"Authorization": "Basic notreally"})
    assert response.status_code == 200, response.text
    assert response.json() == {"msg": "Create an account first"}
