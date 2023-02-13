'''
    Test API defintions using native python data types
'''

import datetime as dt
from decimal import Decimal
from uuid import UUID

import marshmallow.fields as mf
from marshmallow.validate import Range
from starlette.testclient import TestClient

from starmallow import StarMallow
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
    'info': {'title': 'StarMallow', 'version': '0.1.0'},
    'openapi': '3.0.2',
    'components': {
        'schemas': {
            'HTTPValidationError': {
                'properties': {
                    'detail': {
                        'description': 'Error detail',
                        'title': 'Detail',
                    },
                    'errors': {
                        'description': 'Exception or error type',
                        'title': 'Errors',
                    },
                    'status_code': {
                        'description': 'HTTP status code',
                        'title': 'Status Code',
                        'type': 'integer',
                    },
                },
                'required': ['detail', 'status_code'],
                'title': 'HTTPValidationError',
                'type': 'object',
            },
        },
    },
    'paths': {
        '/items': {
            'post': {
                'summary': 'Post Item',
                'operationId': 'post_item_items_post',
                'parameters': [
                    {
                        'in': 'query',
                        'name': 'name',
                        'required': True,
                        'schema': {'title': 'Name', 'type': 'string'},
                    },
                    {
                        'in': 'query',
                        'name': 'age',
                        'required': True,
                        'schema': {'title': 'Age', 'type': 'integer'},
                    },
                    {
                        'in': 'query',
                        'name': 'weight',
                        'required': True,
                        'schema': {'title': 'Weight', 'type': 'number'},
                    },
                    {
                        'in': 'query',
                        'name': 'bool',
                        'required': True,
                        'schema': {'title': 'Bool', 'type': 'boolean'},
                    },
                    {
                        'in': 'query',
                        'name': 'decimal',
                        'required': True,
                        'schema': {'title': 'Decimal', 'type': 'number'},
                    },
                    {
                        'in': 'query',
                        'name': 'date',
                        'required': True,
                        'schema': {
                            'format': 'date',
                            'title': 'Date',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'datetime',
                        'required': True,
                        'schema': {
                            'format': 'date-time',
                            'title': 'Datetime',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'time',
                        'required': True,
                        'schema': {'title': 'Time', 'type': 'string'},
                    },
                    {
                        'in': 'query',
                        'name': 'timedelta',
                        'required': True,
                        'schema': {
                            'title': 'Timedelta',
                            'type': 'integer',
                            'x-unit': 'seconds',
                        },
                    },
                    {
                        'in': 'query',
                        'name': 'uuid',
                        'required': True,
                        'schema': {
                            'title': 'Uuid',
                            'format': 'uuid',
                            'type': 'string',
                        },
                    },
                ],
                'responses': {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError"
                                }
                            }
                        },
                    },
                },
            },
        },
        '/items/{id}': {
            'put': {
                'summary': 'Put Item2',
                'operationId': 'put_item2_items__id__put',
                'parameters': [
                    {
                        'in': 'query',
                        'name': 'name',
                        'required': False,
                        'schema': {'title': 'Name', 'type': 'string', 'default': 'foobar'},
                    },
                    {
                        'in': 'query',
                        'name': 'age',
                        'required': False,
                        'schema': {
                            'default': 0,
                            'maximum': 50,
                            'minimum': 0,
                            'title': 'Age',
                            'type': 'integer',
                        },
                    },
                    {
                        'in': 'path',
                        'name': 'id',
                        'required': True,
                        'schema': {
                            'format': 'uuid',
                            'title': 'Id',
                            'type': 'string',
                        },
                    },
                    {
                        'in': 'header',
                        'name': 'timedelta',
                        'required': True,
                        'schema': {
                            'title': 'Timedelta',
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
                            'title': 'Uuid',
                            'type': 'string',
                        },
                    },
                ],
                'requestBody': {
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'bool': {
                                        'title': 'Bool',
                                        'type': 'boolean'
                                    },
                                    'date': {
                                        'format': 'date',
                                        'title': 'Date',
                                        'type': 'string',
                                    },
                                    'datetime': {
                                        'format': 'date-time',
                                        'title': 'Datetime',
                                        'type': 'string',
                                    },
                                    'decimal': {
                                        'title': 'Decimal',
                                        'type': 'number',
                                    },
                                    'time': {
                                        'title': 'Time',
                                        'type': 'string',
                                    },
                                },
                                'required': ['bool', 'decimal', 'date', 'datetime', 'time'],
                            },
                        },
                    },
                    'required': True,
                },
                'responses': {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError"
                                }
                            }
                        },
                    },
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
