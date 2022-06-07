'''
    Test API defintions using native python data types
'''

import datetime as dt
from decimal import Decimal
from uuid import UUID

import marshmallow.fields as mf
from marshmallow.validate import Range
from starlette.testclient import TestClient

from starmallow.applications import StarMallow
from starmallow.params import Body, Cookie, Header, Path, Query

app = StarMallow()


@app.post('/items')
def post_item(
    name: str,
    age: int,
    weight: float,
    bool: bool,
    decimal: Decimal,
    date: dt.date,
    datetime: dt.datetime,
    time: dt.time,
    timedelta: dt.timedelta,
    uuid: UUID,
):
    return None


@app.put('/items/{id}')
def put_item2(
    id: UUID = Path(...),
    name: str = 'foobar',
    age: int = Query(0, model=mf.Integer(validate=[Range(min=0, max=50)])),
    weight: float = Query(..., include_in_schema=False),
    bool: bool = Body(...),
    decimal: Decimal = Body(...),
    date: dt.date = Body(...),
    datetime: dt.datetime = Body(...),
    time: dt.time = Body(..., deprecated=True),
    timedelta: dt.timedelta = Header(...),
    uuid: UUID = Cookie(...),
):
    return None


client = TestClient(app)

openapi_schema = {
    'info': {'description': '', 'title': 'FastAPI', 'version': '0.1.0'},
    'openapi': '3.0.2',
    'components': {
        'schemas': {
            'APIError': {
                'properties': {
                    'detail': {
                        'description': 'Error '
                        'detail',
                    },
                    'errors': {
                        'description': 'Exception or error type',
                    },
                    'status_code': {
                        'description': 'HTTP status code',
                        'type': 'integer',
                    },
                },
                'required': ['detail', 'status_code'],
                'type': 'object',
            },
        },
    },
    'paths': {
        '/items': {
            'post': {
                'parameters': [
                    {
                        'in': 'query',
                        'name': 'name',
                        'required': True,
                        'schema': {'type': 'string'},
                    },
                    {
                        'in': 'query',
                        'name': 'age',
                        'required': True,
                        'schema': {'type': 'integer'},
                    },
                    {
                        'in': 'query',
                        'name': 'weight',
                        'required': True,
                        'schema': {'type': 'number'},
                    },
                    {
                        'in': 'query',
                        'name': 'bool',
                        'required': True,
                        'schema': {'type': 'boolean'},
                    },
                    {
                        'in': 'query',
                        'name': 'decimal',
                        'required': True,
                        'schema': {'type': 'number'},
                    },
                    {
                        'in': 'query',
                        'name': 'date',
                        'required': True,
                        'schema': {
                            'format': 'date',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'datetime',
                        'required': True,
                        'schema': {
                            'format': 'date-time',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'time',
                        'required': True,
                        'schema': {'type': 'string'},
                    },
                    {
                        'in': 'query',
                        'name': 'timedelta',
                        'required': True,
                        'schema': {
                            'type': 'integer',
                            'x-unit': 'seconds',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'uuid',
                        'required': True,
                        'schema': {
                            'format': 'uuid',
                            'type': 'string',
                        },
                    },
                ],
                'responses': {
                    '422': {
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/APIError'},
                            },
                        },
                    },
                },
            },
        },
        '/items/{id}': {
            'put': {
                'parameters': [
                    {
                        'in': 'query',
                        'name': 'name',
                        'required': True,
                        'schema': {'type': 'string'},
                    },
                    {
                        'in': 'query',
                        'name': 'age',
                        'required': False,
                        'schema': {
                            'default': 0,
                            'maximum': 50,
                            'minimum': 0,
                            'type': 'integer',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'weight',
                        'required': True,
                        'schema': {'type': 'number'},
                    },
                    {
                        'in': 'path',
                        'name': 'id',
                        'required': True,
                        'schema': {
                            'format': 'uuid',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'timedelta',
                        'required': True,
                        'schema': {
                            'type': 'integer',
                            'x-unit': 'seconds',
                        },
                    },
                    {
                        'in': 'cookie',
                        'name': 'uuid',
                        'required': True,
                        'schema': {
                            'format': 'uuid',
                            'type': 'string',
                        },
                    },
                ],
                'requestBody': {
                    'content': {
                        'application/json': {
                            'schema': {
                                'bool': {
                                    'in': 'body',
                                    'name': 'bool',
                                    'required': True,
                                    'schema': {'type': 'boolean'},
                                },
                                'date': {
                                    'in': 'body',
                                    'name': 'date',
                                    'required': True,
                                    'schema': {
                                        'format': 'date',
                                        'type': 'string',
                                    },
                                },
                                'datetime': {
                                    'in': 'body',
                                    'name': 'datetime',
                                    'required': True,
                                    'schema': {
                                        'format': 'date-time',
                                        'type': 'string',
                                    },
                                },
                                'decimal': {
                                    'in': 'body',
                                    'name': 'decimal',
                                    'required': True,
                                    'schema': {'type': 'number'},
                                },
                                'time': {
                                    'in': 'body',
                                    'name': 'time',
                                    'required': True,
                                    'schema': {'type': 'string'},
                                },
                            },
                        },
                    },
                },
                'responses': {
                    '422': {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/APIError'}}}},
                },
            },
        },
    },
}


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert response.json() == openapi_schema


def test_get_api_route():
    response = client.post(
        "/items",
        params={
            'name': 'Tony',
            'age': 30,
            'weight': 190.34,
            'bool': True,
            'decimal': 1234,
            'date': '2022-01-01',
            'datetime': '2022-01-01T02:35:13',
            'time': '23:32:23',
            'timedelta': 86400,
            'uuid': '9f160d7f-c759-4be7-9a20-7f45fa9958c8',
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() is None


def test_get_api_route_invalid():
    response = client.post(
        "/items",
        params={
            'name': 'Tony',
            'age': 'foobar',
            'weight': '3da',
            'bool': 'nope',
            'decimal': 'dd1234',
            'date': 'nodate',
            'datetime': '2022-01-01Tddde',
            'time': '23asdfd3',
            'timedelta': 'asdf',
            'uuid': '9f160d7f-c759-#@$@#-9a20-7f45fa9958c8',
        },
    )
    assert response.status_code == 422, response.text
    assert response.json() == {
        "detail": {
            "query": {
                "age": ["Not a valid integer."],
                "weight": ["Not a valid number."],
                "bool": ["Not a valid boolean."],
                "decimal": ["Not a valid number."],
                "date": ["Not a valid date."],
                "datetime": ["Not a valid datetime."],
                "time": ["Not a valid time."],
                "timedelta": ["Not a valid period of time."],
                "uuid": ["Not a valid UUID."],
            },
        },
        "error": "ValidationError",
        "status_code": 422,
    }
