# Add starmallow package without installing it
import os.path
import sys
from typing import Optional

sys.path.insert(1, os.path.abspath('../'))


from dataclasses import asdict

import marshmallow.fields as mf
from marshmallow.validate import Range
from marshmallow_dataclass import dataclass as ma_dataclass

from starmallow.applications import StarMallow
from starmallow.params import Body, Cookie, Header, Path, Query

app = StarMallow()


@ma_dataclass
class CreateRequest:
    my_string: str
    my_int: int = 5


@ma_dataclass
class CreateResponse:
    my_string: str


@app.post('/test')
async def test(
    create_request: CreateRequest,
    limit: int,
    offset: int = 0,
    offset2: int = Query(0, model=mf.Integer(validate=[Range(min=0, max=50)])),
    my_string: str = Body(...),
    email: str = Body(..., model=mf.Email()),
    authorization: str = Header(...),
    preference: Optional[str] = Cookie(...),
) -> CreateResponse:
    print(create_request)
    print(limit)
    print(authorization)
    print(my_string)

    return create_request


@app.get('/test/{id}')
def test_id(
    id: int = Path(...),
) -> CreateResponse:
    print(id)

    return None


@app.get('/test2')
def test2(create_request: CreateRequest) -> CreateResponse:
    print(create_request)

    return asdict(create_request)


@app.get('/test3')
def test3(
    create_request: CreateRequest = CreateRequest(my_string='foobar', my_int=10),
) -> CreateResponse:
    print(create_request)

    return asdict(create_request)


@app.get('/test4')
def test4(
    create_request: CreateRequest = Query(...),
) -> CreateResponse:
    print(create_request)

    return asdict(create_request)
