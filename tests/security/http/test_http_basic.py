from base64 import b64encode

from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.params import Security
from starmallow.security.http import HTTPBasic, HTTPBasicCredentials

from ...utils import assert_json

app = StarMallow()

security = HTTPBasic(auto_error=False)


@app.get("/users/me")
def read_current_user(credentials: HTTPBasicCredentials | None = Security(security)):
    if credentials is None:
        return {"msg": "Create an account first"}
    return {"username": credentials.username, "password": credentials.password}


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
                "security": [{"HTTPBasic": []}],
            },
        },
    },
    "components": {
        "securitySchemes": {"HTTPBasic": {"type": "http", "scheme": "basic"}},
    },
}


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_security_http_basic():
    response = client.get("/users/me", auth=("john", "secret"))
    assert response.status_code == 200, response.text
    assert response.json() == {"username": "john", "password": "secret"}


def test_security_http_basic_no_credentials():
    response = client.get("/users/me")
    assert response.status_code == 200, response.text
    assert response.json() == {"msg": "Create an account first"}


def test_security_http_basic_invalid_credentials():
    response = client.get(
        "/users/me", headers={"Authorization": "Basic notabase64token"},
    )
    assert response.status_code == 401, response.text
    assert response.headers["WWW-Authenticate"] == "Basic"
    assert response.json() == {"detail": "Invalid authentication credentials"}


def test_security_http_basic_non_basic_credentials():
    payload = b64encode(b"johnsecret").decode("ascii")
    auth_header = f"Basic {payload}"
    response = client.get("/users/me", headers={"Authorization": auth_header})
    assert response.status_code == 401, response.text
    assert response.headers["WWW-Authenticate"] == "Basic"
    assert response.json() == {"detail": "Invalid authentication credentials"}
