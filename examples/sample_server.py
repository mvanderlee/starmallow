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
