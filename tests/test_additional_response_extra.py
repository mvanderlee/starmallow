from starlette.testclient import TestClient

from starmallow import APIRouter, StarMallow

from .utils import assert_json

router = APIRouter()

sub_router = APIRouter()

app = StarMallow()


@sub_router.get("/")
def read_item():
    return {"id": "foo"}


router.include_router(sub_router, prefix="/items")

app.include_router(router)


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
                "summary": "Read Item",
                "operationId": "read_item_items__get",
            },
        },
    },
}

client = TestClient(app)


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert_json(response.json(), openapi_schema)


def test_path_operation():
    response = client.get("/items/")
    assert response.status_code == 200, response.text
    assert response.json() == {"id": "foo"}
