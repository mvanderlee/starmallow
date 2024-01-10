from starlette.testclient import TestClient

from starmallow import StarMallow

app = StarMallow()


@app.get("/a", responses={"hello": {"description": "Not a valid additional response"}})
async def a():
    pass  # pragma: no cover


openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/a": {
            "get": {
                "responses": {
                    # this is how one would imagine the openapi schema to be
                    # but since the key is not valid, openapi.utils.get_openapi will raise ValueError
                    "hello": {"description": "Not a valid additional response"},
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                },
                "summary": "A",
                "operationId": "a_a_get",
            },
        },
    },
}

client = TestClient(app)


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to generate schema",
    }
