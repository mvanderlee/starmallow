# Add starmallow package without installing it
import os.path
import sys

sys.path.insert(1, os.path.abspath('../'))


from dataclasses import asdict

from marshmallow_dataclass import dataclass as ma_dataclass

from starmallow.applications import StarMallow
from starmallow.params import Body, Header

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
    my_string: str = Body(...),
    authorization: str = Header(...),
) -> CreateResponse:
    print(create_request)
    print(limit)
    print(authorization)
    print(my_string)

    return create_request


@app.get('/test2')
def test(create_request: CreateRequest) -> CreateResponse:
    print(create_request)

    return asdict(create_request)
