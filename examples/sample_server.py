from dataclasses import asdict
from typing import Annotated, Optional

import aiofiles.tempfile
import marshmallow.fields as mf
import orjson
from marshmallow.validate import Range
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette_context import middleware, plugins

from starmallow.applications import StarMallow
from starmallow.params import Body, Cookie, Header, Path, Query, Security
from starmallow.security.http import HTTPAuthorizationCredentials, HTTPBearer
from starmallow.security.oauth2 import OAuth2PasswordBearer

app = StarMallow(
    title="My API",
    version="1.0.0",
    middleware=[
        # Order matters!
        Middleware(GZipMiddleware, minimum_size=500),
        Middleware(
            middleware.ContextMiddleware,
            plugins=(
                plugins.RequestIdPlugin(),
                plugins.CorrelationIdPlugin(),
            ),
        ),
    ],
)


jwt_scheme = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")


@ma_dataclass
class CreateRequest:
    my_string: str
    my_int: int = 5


@ma_dataclass
class CreateResponse:
    my_string: str


@app.get('/oauth_test')
def oauth_test(
    token: str = Security(oauth2_scheme),
):
    print(token)


@app.get('/auth_test')
def auth_test(
    token: Annotated[HTTPAuthorizationCredentials, Security(jwt_scheme)],
):
    print(token)


@app.post('/test')
async def test(
    create_request: CreateRequest,
    limit: Annotated[int, Query()],
    offset: int = 0,
    offset2: int = Query(0, model=mf.Integer(validate=[Range(min=0, max=50)])),
    my_string: str = Body('foobar'),
    email: str = Body(..., model=mf.Email()),
    foobar: str = Header(...),
    preference: Optional[str] = Cookie(...),
) -> CreateResponse:
    print(create_request)
    print(limit)
    print(offset)
    print(offset2)
    print(foobar)
    print(my_string)
    print(email)
    print(preference)

    return create_request


# Test path parameters
@app.get('/test/{id}')
def test_id(
    id: int = Path(...),
) -> CreateResponse:
    print(id)

    return None


# Test basic JSON request body and JSON response body
@app.put('/test2')
def test2(create_request: CreateRequest) -> CreateResponse:
    print(create_request)

    return asdict(create_request)


# Test basic JSON request body and JSON response body with request defaults
@app.patch('/test3')
def test3(
    create_request: CreateRequest = CreateRequest(my_string='foobar', my_int=10),
) -> CreateResponse:
    print(create_request)

    return asdict(create_request)


# Test request query from schema where the entire schema is required
@app.get('/test4')
def test4(
    create_request: CreateRequest = Query(...),
) -> CreateResponse:
    print(create_request)

    return asdict(create_request)


# Test request query from schema where the entire schema has a default
@app.get('/test5')
def test5(
    create_request: CreateRequest = Query(CreateRequest(my_string='default_string', my_int=101)),
) -> CreateResponse:
    print(create_request)

    return asdict(create_request)


# Test basic JSON request body and JSON response body
@app.put('/tmp_file')
async def put_tmp_file(create_request: CreateRequest) -> CreateResponse:
    async with aiofiles.tempfile.TemporaryFile('wb') as f:
        await f.write(orjson.dumps(create_request))

    return asdict(create_request)
