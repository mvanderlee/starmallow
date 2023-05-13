import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Dict, Final, List, Literal, Set
from uuid import UUID

import marshmallow.fields as mf
import pytest
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import StarMallow
from starmallow.responses import UJSONResponse

from .utils import assert_json

app = StarMallow()


############################################################
# Models  -  classes and schemas
############################################################
# region
class MyEnum(Enum):
    optionA = 'optionA'
    optionB = 'optionB'


@ma_dataclass
class Item:
    item_id: dt.date
# endregion


############################################################
# Test API
############################################################
# region
@app.get("/path/str", response_class=UJSONResponse)
def get_path_str() -> str:
    return 5


@app.get("/path/int", response_class=UJSONResponse)
def get_path_int() -> int:
    return "5"


@app.get("/path/bool", response_class=UJSONResponse)
def get_path_bool() -> bool:
    return True


@app.get("/path/date", response_class=UJSONResponse)
def get_path_date() -> dt.date:
    return dt.date(2023, 2, 27)


@app.get("/path/datetime", response_class=UJSONResponse)
def get_path_datetime() -> dt.datetime:
    return dt.datetime(2023, 2, 27, 11, 37, 43)


@app.get("/path/time", response_class=UJSONResponse)
def get_path_time() -> dt.time:
    return dt.time(11, 37, 43)


@app.get("/path/timedelta", response_class=UJSONResponse)
def get_path_timedelta() -> dt.timedelta:
    return dt.timedelta(days=1, hours=6, seconds=321)


@app.get("/path/uuid", response_class=UJSONResponse)
def get_path_uuid() -> UUID:
    return UUID(hex='2c55d0f62629450a8eee71f791cd8eb9')


@app.get("/path/decimal", response_class=UJSONResponse)
def get_path_decimal() -> Decimal:
    return Decimal(123456789)


@app.get("/path/enum", response_class=UJSONResponse)
def get_path_enum() -> MyEnum:
    return MyEnum.optionA


@app.get("/path/literal", response_class=UJSONResponse)
def get_path_literal() -> Literal['alpha', 'beta']:
    return 'alpha'


# Final can only be used inside a class, not as a function argument
@ma_dataclass
class FinalItem:
    item_id: Final[int] = 10


@app.get("/path/final", response_class=UJSONResponse)
def get_path_final() -> FinalItem:
    return FinalItem()


@app.get("/path/date_field", response_class=UJSONResponse)
def get_path_date_field() -> mf.Date:
    return dt.date(2023, 2, 27)


@app.get("/path/date_model", response_model=mf.Date(), response_class=UJSONResponse)
def get_path_date_model():
    return dt.date(2023, 2, 27)


@app.get("/path/dataclass", response_class=UJSONResponse)
def get_path_dataclass() -> Item:
    return {'item_id': dt.date(2023, 2, 27)}


@app.get("/path/schema", response_class=UJSONResponse)
def get_path_schema() -> Item.Schema:
    return {'item_id': dt.date(2023, 2, 27)}


@app.get("/path/dataclass_model", response_model=Item, response_class=UJSONResponse)
def get_path_dataclass_model():
    return {'item_id': dt.date(2023, 2, 27)}


@app.get("/path/schema_model", response_model=Item.Schema, response_class=UJSONResponse)
def get_path_schema_model():
    return {'item_id': dt.date(2023, 2, 27)}


@app.get("/path/list_date", response_class=UJSONResponse)
def get_path_list_date() -> List[dt.date]:
    return [dt.date(2023, 2, 27)]


@app.get("/path/set_date", response_class=UJSONResponse)
def get_path_set_date() -> Set[dt.date]:
    return {dt.date(2023, 2, 27)}


@app.get("/path/dict_date_date", response_class=UJSONResponse)
def get_path_dict_date_date() -> Dict[dt.date, dt.date]:
    return {dt.date(2023, 2, 27): dt.date(2023, 2, 27)}


@app.get("/path/list_dataclass", response_class=UJSONResponse)
def get_path_list_dataclass() -> List[Item]:
    return [{'item_id': dt.date(2023, 2, 27)}]


@app.get("/path/custom_description", response_description='Custom Description', response_class=UJSONResponse)
def get_path_custom_description() -> str:
    return 5


@app.get(
    "/path/multi_response",
    responses={
        200: {
            "description": "Custom 200",
            "model": mf.String(),
        },
        201: {
            "description": "Item Created",
            "model": Item,
        },
        204: {
            "description": "Item Deleted",
        },
        404: {
            "content": {
                "text/plain": {},
            },
            "description": "Item Not Found",
        },
    },
    response_class=UJSONResponse,
)
def get_path_multi_response() -> str:
    return 5
# endregion


############################################################
# Tests
############################################################
# region
client = TestClient(app)

openapi_schema = {
    "openapi": "3.0.2",
    "info": {"title": "StarMallow", "version": "0.1.0"},
    "paths": {
        "/path/str": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                },
                "summary": "Get Path Str",
                "operationId": "get_path_str_path_str_get",
            },
        },
        "/path/int": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "integer"}}},
                    },
                },
                "summary": "Get Path Int",
                "operationId": "get_path_int_path_int_get",
            },
        },
        "/path/bool": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "boolean"}}},
                    },
                },
                "summary": "Get Path Bool",
                "operationId": "get_path_bool_path_bool_get",
            },
        },
        "/path/date": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date"}}},
                    },
                },
                "summary": "Get Path Date",
                "operationId": "get_path_date_path_date_get",
            },
        },
        "/path/datetime": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date-time"}}},
                    },
                },
                "summary": "Get Path Datetime",
                "operationId": "get_path_datetime_path_datetime_get",
            },
        },
        "/path/time": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                },
                "summary": "Get Path Time",
                "operationId": "get_path_time_path_time_get",
            },
        },
        "/path/timedelta": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "integer", "x-unit": "seconds"}}},
                    },
                },
                "summary": "Get Path Timedelta",
                "operationId": "get_path_timedelta_path_timedelta_get",
            },
        },
        "/path/uuid": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "uuid"}}},
                    },
                },
                "summary": "Get Path Uuid",
                "operationId": "get_path_uuid_path_uuid_get",
            },
        },
        "/path/decimal": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "decimal"}}},
                    },
                },
                "summary": "Get Path Decimal",
                "operationId": "get_path_decimal_path_decimal_get",
            },
        },
        "/path/enum": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"enum": ["optionA", "optionB"], "type": "string"}}},
                    },
                },
                "summary": "Get Path Enum",
                "operationId": "get_path_enum_path_enum_get",
            },
        },
        "/path/literal": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"enum": ["alpha", "beta"]}}},
                    },
                },
                "summary": "Get Path Literal",
                "operationId": "get_path_literal_path_literal_get",
            },
        },
        "/path/final": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FinalItem"}}},
                    },
                },
                "summary": "Get Path Final",
                "operationId": "get_path_final_path_final_get",
            },
        },
        "/path/date_field": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date"}}},
                    },
                },
                "summary": "Get Path Date Field",
                "operationId": "get_path_date_field_path_date_field_get",
            },
        },
        "/path/date_model": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date"}}},
                    },
                },
                "summary": "Get Path Date Model",
                "operationId": "get_path_date_model_path_date_model_get",
            },
        },
        "/path/dataclass": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                },
                "summary": "Get Path Dataclass",
                "operationId": "get_path_dataclass_path_dataclass_get",
            },
        },
        "/path/schema": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                },
                "summary": "Get Path Schema",
                "operationId": "get_path_schema_path_schema_get",
            },
        },
        "/path/dataclass_model": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                },
                "summary": "Get Path Dataclass Model",
                "operationId": "get_path_dataclass_model_path_dataclass_model_get",
            },
        },
        "/path/schema_model": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                },
                "summary": "Get Path Schema Model",
                "operationId": "get_path_schema_model_path_schema_model_get",
            },
        },
        "/path/list_date": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "items": {
                                        "format": "date",
                                        "type": "string",
                                    },
                                    "type": "array",
                                },
                            },
                        },
                    },
                },
                "summary": "Get Path List Date",
                "operationId": "get_path_list_date_path_list_date_get",
            },
        },
        "/path/set_date": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "items": {
                                        "format": "date",
                                        "type": "string",
                                    },
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                            },
                        },
                    },
                },
                "summary": "Get Path Set Date",
                "operationId": "get_path_set_date_path_set_date_get",
            },
        },
        "/path/dict_date_date": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "additionalProperties": {
                                        "format": "date",
                                        "type": "string",
                                    },
                                    "type": "object",
                                },
                            },
                        },
                    },
                },
                "summary": "Get Path Dict Date Date",
                "operationId": "get_path_dict_date_date_path_dict_date_date_get",
            },
        },
        "/path/list_dataclass": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "items": {
                                        "$ref": "#/components/schemas/Item",
                                    },
                                    "type": "array",
                                },
                            },
                        },
                    },
                },
                "summary": "Get Path List Dataclass",
                "operationId": "get_path_list_dataclass_path_list_dataclass_get",
            },
        },
        "/path/custom_description": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Custom Description",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                },
                "summary": "Get Path Custom Description",
                "operationId": "get_path_custom_description_path_custom_description_get",
            },
        },
        "/path/multi_response": {
            "get": {
                "responses": {
                    "200": {
                        "description": "Custom 200",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                    "201": {
                        "description": "Item Created",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                    "204": {
                        "description": "Item Deleted",
                    },
                    "404": {
                        "description": "Item Not Found",
                        "content": {"text/plain": {}},
                    },
                },
                "summary": "Get Path Multi Response",
                "operationId": "get_path_multi_response_path_multi_response_get",
            },
        },

    },
    "components": {
        "schemas": {
            'FinalItem': {
                'properties': {
                    'item_id': {
                        'default': 10,
                        'title': 'Item Id',
                        'type': 'integer',
                    },
                },
                'title': 'FinalItem',
                'type': 'object',
            },
            "Item": {
                "properties": {
                    "item_id": {
                        "format": "date",
                        "title": "Item Id",
                        "type": "string",
                    },
                },
                "required": [
                    "item_id",
                ],
                "title": "Item",
                "type": "object",
            },
        },
    },
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ('/path/str', 200, "5"),
        ('/path/int', 200, 5),
        ('/path/bool', 200, True),
        ('/path/date', 200, "2023-02-27"),
        ('/path/datetime', 200, "2023-02-27T11:37:43"),
        ('/path/time', 200, "11:37:43"),
        ('/path/timedelta', 200, 108321),
        ('/path/uuid', 200, '2c55d0f6-2629-450a-8eee-71f791cd8eb9'),
        ('/path/decimal', 200, 123456789.0),
        ('/path/enum', 200, "optionA"),
        ('/path/literal', 200, "alpha"),
        ('/path/final', 200, {'item_id': 10}),
        ('/path/date_field', 200, "2023-02-27"),
        ('/path/date_model', 200, "2023-02-27"),
        ('/path/dataclass', 200, {'item_id': "2023-02-27"}),
        ('/path/schema', 200, {'item_id': "2023-02-27"}),
        ('/path/dataclass_model', 200, {'item_id': "2023-02-27"}),
        ('/path/schema_model', 200, {'item_id': "2023-02-27"}),
        ('/path/list_date', 200, ["2023-02-27"]),
        ('/path/set_date', 200, ["2023-02-27"]),
        ('/path/dict_date_date', 200, {"2023-02-27": "2023-02-27"}),
        ('/path/list_dataclass', 200, [{'item_id': "2023-02-27"}]),
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)
# endregion
