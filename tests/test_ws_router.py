from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

from starmallow import APIRouter, APIWebSocket, StarMallow

router = APIRouter()
prefix_router = APIRouter()
native_prefix_route = APIRouter(prefix="/native")
app = StarMallow()


@ma_dataclass
class Name:
    name: str


@app.websocket_route("/")
async def index(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, world!")
    await websocket.close()


@router.websocket_route("/router")
async def routerindex(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, router!")
    await websocket.close()


@prefix_router.websocket_route("/")
async def routerprefixindex(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, router with prefix!")
    await websocket.close()


@router.websocket("/router2")
async def routerindex2(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, router!")
    await websocket.close()


@router.websocket("/router/{pathparam:path}")
async def routerindexparams(websocket: WebSocket, pathparam: str, queryparam: str):
    await websocket.accept()
    await websocket.send_text(pathparam)
    await websocket.send_text(queryparam)
    await websocket.close()


@native_prefix_route.websocket("/")
async def router_native_prefix_ws(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, router with native prefix!")
    await websocket.close()


@router.websocket("/router_json")
async def router_json(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    await websocket.send_json(data)
    await websocket.close()


@router.websocket("/router_json_dataclass")
async def router_json_dataclass(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    await websocket.send_json(Name(name=data['name']))
    await websocket.close()


@router.websocket("/router_json_model")
async def router_json_model(websocket: APIWebSocket):
    await websocket.accept()
    data = await websocket.receive_json(model=Name.Schema)
    await websocket.send_json(data, model=Name.Schema)
    await websocket.close()


app.include_router(router)
app.include_router(prefix_router, prefix="/prefix")
app.include_router(native_prefix_route)


def test_app():
    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, world!"


def test_router():
    client = TestClient(app)
    with client.websocket_connect("/router") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, router!"


def test_prefix_router():
    client = TestClient(app)
    with client.websocket_connect("/prefix/") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, router with prefix!"


def test_native_prefix_router():
    client = TestClient(app)
    with client.websocket_connect("/native/") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, router with native prefix!"


def test_router2():
    client = TestClient(app)
    with client.websocket_connect("/router2") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, router!"


def test_router_with_params():
    client = TestClient(app)
    with client.websocket_connect(
        "/router/path/to/file?queryparam=a_query_param",
    ) as websocket:
        data = websocket.receive_text()
        assert data == "path/to/file"
        data = websocket.receive_text()
        assert data == "a_query_param"


def test_router_json():
    client = TestClient(app)
    with client.websocket_connect("/router_json") as websocket:
        websocket.send_text('{"name": "foobar"}')
        data = websocket.receive_text()
        assert data == '{"name": "foobar"}'


def test_router_json_dataclass():
    client = TestClient(app)
    with client.websocket_connect("/router_json_dataclass") as websocket:
        websocket.send_text('{"name": "foobar"}')
        data = websocket.receive_text()
        assert data == '{"name": "foobar"}'


def test_router_json_model():
    client = TestClient(app)
    with client.websocket_connect("/router_json_model") as websocket:
        websocket.send_text('{"name": "foobar"}')
        data = websocket.receive_text()
        assert data == '{"name": "foobar"}'
