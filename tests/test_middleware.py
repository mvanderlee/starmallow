import pytest
from starlette.datastructures import MutableHeaders
from starlette.middleware import Middleware
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from starmallow import APIRouter, StarMallow


class TestMiddleware:
    def __init__(self, app: ASGIApp, **kwargs) -> None:
        self.app = app
        self.headers = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # noqa
        self.send = send
        await self.app(scope, receive, self.send_with_headers)

    async def send_with_headers(self, message: Message) -> None:
        """Apply compression using brotli."""
        if message["type"] == "http.response.start":
            headers = MutableHeaders(raw=message["headers"])
            headers.update(self.headers)

        await self.send(message)


############################################################
# Test API
############################################################
# region
app = StarMallow(
    middleware=[Middleware(TestMiddleware, test_app_header='app_value')],
)

router = APIRouter(
    prefix='/router',
    middleware=[Middleware(TestMiddleware, test_router_header='router_value')],
)


@router.get('')
def router_get():
    return {}


@router.get(
    '/route',
    middleware=[Middleware(TestMiddleware, test_router_route_header='router_route_value')],
)
def router_route_get():
    return {}


@app.get('/')
def app_get():
    return {}


@app.get(
    "/route",
    middleware=[Middleware(TestMiddleware, test_app_route_header='app_route_value')],
)
def route_get():
    return {}


app.include_router(router)
# endregion


############################################################
# Tests
############################################################
# region
client = TestClient(app)


@pytest.mark.parametrize(
    "path,expected_status,expected_headers",
    [
        ("/", 200, {'test_app_header': 'app_value'}),
        ("/route", 200, {'test_app_header': 'app_value', 'test_app_route_header': 'app_route_value'}),
        ("/router", 200, {'test_app_header': 'app_value', 'test_router_header': 'router_value'}),
        (
            "/router/route",
            200,
            {
                'test_app_header': 'app_value',
                'test_router_header': 'router_value',
                'test_router_route_header': 'router_route_value',
            },
        ),
    ],
)
def test_get_path(path, expected_status, expected_headers):
    response = client.get(path)
    assert response.status_code == expected_status
    assert {
        k: v
        for k,v in response.headers.items()
        if k.startswith('test_')
    } == expected_headers

# endregion
