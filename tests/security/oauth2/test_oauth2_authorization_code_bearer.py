from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.params import Security
from starmallow.security.oauth2 import OAuth2AuthorizationCodeBearer

from ...utils import assert_json

app = StarMallow()

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="authorize", tokenUrl="token", auto_error=True,
)


@app.get("/items/")
async def read_items(token: str | None = Security(oauth2_scheme)):
    return {"token": token}


client = TestClient(app)

openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/items/": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "Read Items",
                "operationId": "read_items_items__get",
                "security": [{"OAuth2AuthorizationCodeBearer": []}],
            },
        },
    },
    "components": {
        "securitySchemes": {
            "OAuth2AuthorizationCodeBearer": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "authorize",
                        "tokenUrl": "token",
                        "scopes": {},
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


def test_no_token():
    response = client.get("/items")
    assert response.status_code == 401, response.text
    assert response.json() == {"detail": "Not authenticated"}


def test_incorrect_token():
    response = client.get("/items", headers={"Authorization": "Non-existent testtoken"})
    assert response.status_code == 401, response.text
    assert response.json() == {"detail": "Not authenticated"}


def test_token():
    response = client.get("/items", headers={"Authorization": "Bearer testtoken"})
    assert response.status_code == 200, response.text
    assert response.json() == {"token": "testtoken"}
