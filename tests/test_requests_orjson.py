import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Dict, Final, List, Literal, Set
from uuid import UUID

import marshmallow.fields as mf
import pytest
from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.testclient import TestClient

from starmallow import Body, StarMallow
from starmallow.requests import ORJSONRequest

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
@app.put("/orjson/str", request_class=ORJSONRequest)
def put_orjson_str(input_: str = Body()) -> str:
    assert type(input_) == str
    return input_


@app.put("/orjson/int", request_class=ORJSONRequest)
def put_orjson_int(input_: int = Body()) -> int:
    assert type(input_) == int
    return input_


@app.put("/orjson/bool", request_class=ORJSONRequest)
def put_orjson_bool(input_: bool = Body()) -> bool:
    assert type(input_) == bool
    return input_


@app.put("/orjson/date", request_class=ORJSONRequest)
def put_orjson_date(input_: dt.date = Body()) -> dt.date:
    assert type(input_) == dt.date
    return input_


@app.put("/orjson/datetime", request_class=ORJSONRequest)
def put_orjson_datetime(input_: dt.datetime = Body()) -> dt.datetime:
    assert type(input_) == dt.datetime
    return input_


@app.put("/orjson/time", request_class=ORJSONRequest)
def put_orjson_time(input_: dt.time = Body()) -> dt.time:
    assert type(input_) == dt.time
    return input_


@app.put("/orjson/timedelta", request_class=ORJSONRequest)
def put_orjson_timedelta(input_: dt.timedelta = Body()) -> dt.timedelta:
    assert type(input_) == dt.timedelta
    return input_


@app.put("/orjson/uuid", request_class=ORJSONRequest)
def put_orjson_uuid(input_: UUID = Body()) -> UUID:
    assert type(input_) == UUID
    return input_


@app.put("/orjson/decimal", request_class=ORJSONRequest)
def put_orjson_decimal(input_: Decimal = Body()) -> Decimal:
    assert type(input_) == Decimal
    return input_


@app.put("/orjson/enum", request_class=ORJSONRequest)
def put_orjson_enum(input_: MyEnum = Body()) -> MyEnum:
    assert type(input_) == MyEnum
    return input_


@app.put("/orjson/literal", request_class=ORJSONRequest)
def put_orjson_literal(input_: Literal['alpha', 'beta'] = Body()) -> Literal['alpha', 'beta']:
    assert input_ in ['alpha', 'beta']
    return input_


# Final can only be used inside a class, not as a function argument
@ma_dataclass
class FinalItem:
    item_id: Final[int] = 10


@app.put("/orjson/final", request_class=ORJSONRequest)
def put_orjson_final(input_: FinalItem = Body()) -> FinalItem:
    assert type(input_) == FinalItem
    return input_


@app.put("/orjson/date_field", request_class=ORJSONRequest)
def put_orjson_date_field(input_: mf.Date = Body()) -> mf.Date:
    assert type(input_) == dt.date
    return input_


@app.put("/orjson/dataclass", request_class=ORJSONRequest)
def put_orjson_dataclass(input_: Item = Body()) -> Item:
    assert type(input_) == Item
    return input_


@app.put("/orjson/schema", request_class=ORJSONRequest)
def put_orjson_schema(input_: Item.Schema = Body()) -> Item.Schema:
    assert type(input_) == Item
    return input_


@app.put("/orjson/list_date", request_class=ORJSONRequest)
def put_orjson_list_date(input_: List[dt.date] = Body()) -> List[dt.date]:
    assert type(input_) == list
    assert len(input_) > 0
    assert type(input_[0]) == dt.date
    return input_


@app.put("/orjson/set_date", request_class=ORJSONRequest)
def put_orjson_set_date(input_: Set[dt.date] = Body()) -> Set[dt.date]:
    assert type(input_) == set
    assert len(input_) > 0
    assert type(list(input_)[0]) == dt.date
    return input_


@app.put("/orjson/dict_date_date", request_class=ORJSONRequest)
def put_orjson_dict_date_date(input_: Dict[dt.date, dt.date] = Body()) -> Dict[dt.date, dt.date]:
    assert type(input_) == dict
    assert len(input_) > 0
    assert type(list(input_.keys())[0]) == dt.date
    assert type(list(input_.values())[0]) == dt.date
    return input_


@app.put("/orjson/list_dataclass", request_class=ORJSONRequest)
def put_orjson_list_dataclass(input_: List[Item] = Body()) -> List[Item]:
    assert type(input_) == list
    assert len(input_) > 0
    assert type(input_[0]) == Item
    return input_
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
        "/orjson/str": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_str_orjson_str_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Str",
                "operationId": "put_orjson_str_orjson_str_put",
            },
        },
        "/orjson/int": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_int_orjson_int_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "integer"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Int",
                "operationId": "put_orjson_int_orjson_int_put",
            },
        },
        "/orjson/bool": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_bool_orjson_bool_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "boolean"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Bool",
                "operationId": "put_orjson_bool_orjson_bool_put",
            },
        },
        "/orjson/date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_date_orjson_date_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Date",
                "operationId": "put_orjson_date_orjson_date_put",
            },
        },
        "/orjson/datetime": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_datetime_orjson_datetime_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date-time"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Datetime",
                "operationId": "put_orjson_datetime_orjson_datetime_put",
            },
        },
        "/orjson/time": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_time_orjson_time_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Time",
                "operationId": "put_orjson_time_orjson_time_put",
            },
        },
        "/orjson/timedelta": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_timedelta_orjson_timedelta_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "integer", "x-unit": "seconds"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Timedelta",
                "operationId": "put_orjson_timedelta_orjson_timedelta_put",
            },
        },
        "/orjson/uuid": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_uuid_orjson_uuid_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "uuid"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Uuid",
                "operationId": "put_orjson_uuid_orjson_uuid_put",
            },
        },
        "/orjson/decimal": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_decimal_orjson_decimal_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "decimal"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Decimal",
                "operationId": "put_orjson_decimal_orjson_decimal_put",
            },
        },
        "/orjson/enum": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_enum_orjson_enum_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"enum": ["optionA", "optionB"], "type": "string"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Enum",
                "operationId": "put_orjson_enum_orjson_enum_put",
            },
        },
        "/orjson/literal": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_literal_orjson_literal_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"enum": ["alpha", "beta"]}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Literal",
                "operationId": "put_orjson_literal_orjson_literal_put",
            },
        },
        "/orjson/final": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/FinalItem",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FinalItem"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Final",
                "operationId": "put_orjson_final_orjson_final_put",
            },
        },
        "/orjson/date_field": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_date_field_orjson_date_field_put",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"type": "string", "format": "date"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Date Field",
                "operationId": "put_orjson_date_field_orjson_date_field_put",
            },
        },
        "/orjson/dataclass": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Item",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Dataclass",
                "operationId": "put_orjson_dataclass_orjson_dataclass_put",
            },
        },
        "/orjson/schema": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Item",
                            },
                        },
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Schema",
                "operationId": "put_orjson_schema_orjson_schema_put",
            },
        },
        "/orjson/list_date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_list_date_orjson_list_date_put",
                            },
                        },
                    },
                    "required": True,
                },
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
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson List Date",
                "operationId": "put_orjson_list_date_orjson_list_date_put",
            },
        },
        "/orjson/set_date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_set_date_orjson_set_date_put",
                            },
                        },
                    },
                    "required": True,
                },
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
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Set Date",
                "operationId": "put_orjson_set_date_orjson_set_date_put",
            },
        },
        "/orjson/dict_date_date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_dict_date_date_orjson_dict_date_date_put",
                            },
                        },
                    },
                    "required": True,
                },
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
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson Dict Date Date",
                "operationId": "put_orjson_dict_date_date_orjson_dict_date_date_put",
            },
        },
        "/orjson/list_dataclass": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_orjson_list_dataclass_orjson_list_dataclass_put",
                            },
                        },
                    },
                    "required": True,
                },
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
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError",
                                },
                            },
                        },
                        "description": "Validation Error",
                    },
                },
                "summary": "Put Orjson List Dataclass",
                "operationId": "put_orjson_list_dataclass_orjson_list_dataclass_put",
            },
        },
    },
    "components": {
        "schemas": {
            "Body_put_orjson_bool_orjson_bool_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "boolean",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_bool_orjson_bool_put",
                "type": "object",
            },
            "Body_put_orjson_date_field_orjson_date_field_put": {
                "properties": {
                    "input_": {
                        "format": "date",
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_date_field_orjson_date_field_put",
                "type": "object",
            },
            "Body_put_orjson_date_orjson_date_put": {
                "properties": {
                    "input_": {
                        "format": "date",
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_date_orjson_date_put",
                "type": "object",
            },
            "Body_put_orjson_datetime_orjson_datetime_put": {
                "properties": {
                    "input_": {
                        "format": "date-time",
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_datetime_orjson_datetime_put",
                "type": "object",
            },
            "Body_put_orjson_decimal_orjson_decimal_put": {
                "properties": {
                    "input_": {
                        "format": "decimal",
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_decimal_orjson_decimal_put",
                "type": "object",
            },
            "Body_put_orjson_dict_date_date_orjson_dict_date_date_put": {
                "properties": {
                    "input_": {
                        "additionalProperties": {
                            "format": "date",
                            "type": "string",
                        },
                        "title": "Input ",
                        "type": "object",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_dict_date_date_orjson_dict_date_date_put",
                "type": "object",
            },
            "Body_put_orjson_enum_orjson_enum_put": {
                "properties": {
                    "input_": {
                        "enum": [
                            "optionA",
                            "optionB",
                        ],
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_enum_orjson_enum_put",
                "type": "object",
            },
            "Body_put_orjson_int_orjson_int_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "integer",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_int_orjson_int_put",
                "type": "object",
            },
            "Body_put_orjson_list_dataclass_orjson_list_dataclass_put": {
                "properties": {
                    "input_": {
                        "items": {
                            "$ref": "#/components/schemas/Item",
                        },
                        "title": "Input ",
                        "type": "array",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_list_dataclass_orjson_list_dataclass_put",
                "type": "object",
            },
            "Body_put_orjson_list_date_orjson_list_date_put": {
                "properties": {
                    "input_": {
                        "items": {
                            "format": "date",
                            "type": "string",
                        },
                        "title": "Input ",
                        "type": "array",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_list_date_orjson_list_date_put",
                "type": "object",
            },
            "Body_put_orjson_literal_orjson_literal_put": {
                "properties": {
                    "input_": {
                        "enum": [
                            "alpha",
                            "beta",
                        ],
                        "title": "Input ",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_literal_orjson_literal_put",
                "type": "object",
            },
            "Body_put_orjson_set_date_orjson_set_date_put": {
                "properties": {
                    "input_": {
                        "items": {
                            "format": "date",
                            "type": "string",
                        },
                        "title": "Input ",
                        "type": "array",
                        "uniqueItems": True,
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_set_date_orjson_set_date_put",
                "type": "object",
            },
            "Body_put_orjson_str_orjson_str_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_str_orjson_str_put",
                "type": "object",
            },
            "Body_put_orjson_time_orjson_time_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_time_orjson_time_put",
                "type": "object",
            },
            "Body_put_orjson_timedelta_orjson_timedelta_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "integer",
                        "x-unit": "seconds",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_timedelta_orjson_timedelta_put",
                "type": "object",
            },
            "Body_put_orjson_uuid_orjson_uuid_put": {
                "properties": {
                    "input_": {
                        "format": "uuid",
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_orjson_uuid_orjson_uuid_put",
                "type": "object",
            },
            'FinalItem': {
                'properties': {
                    'item_id': {
                        'default': 10,
                        'title': 'Item Id',
                        'type': 'integer',
                    },
                },
                'title': 'Input ',
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
                "title": "Input ",
                "type": "object",
            },
            "HTTPValidationError": {
                "properties": {
                    "detail": {
                        "description": "Error detail",
                        "title": "Detail",
                    },
                    "errors": {
                        "description": "Exception or error type",
                        "title": "Errors",
                    },
                    "status_code": {
                        "description": "HTTP status code",
                        "title": "Status Code",
                        "type": "integer",
                    },
                },
                "required": [
                    "detail",
                    "status_code",
                ],
                "title": "HTTPValidationError",
                "type": "object",
            },
        },
    },
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/openapi.json", 200, openapi_schema),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert_json(response.json(), expected_response)


@pytest.mark.parametrize(
    "path,expected_status,input_,wrap",
    [
        ('/orjson/str', 200, "5", True),
        ('/orjson/int', 200, 5, True),
        ('/orjson/bool', 200, True, True),
        ('/orjson/date', 200, "2023-02-27", True),
        ('/orjson/datetime', 200, "2023-02-27T11:37:43", True),
        ('/orjson/time', 200, "11:37:43", True),
        ('/orjson/timedelta', 200, 108321, True),
        ('/orjson/uuid', 200, '2c55d0f6-2629-450a-8eee-71f791cd8eb9', True),
        ('/orjson/decimal', 200, "123456789", True),
        ('/orjson/enum', 200, "optionA", True),
        ('/orjson/literal', 200, "alpha", True),
        ('/orjson/final', 200, {'item_id': 10}, False),
        ('/orjson/date_field', 200, "2023-02-27", True),
        ('/orjson/dataclass', 200, {'item_id': "2023-02-27"}, False),
        ('/orjson/schema', 200, {'item_id': "2023-02-27"}, False),
        ('/orjson/list_date', 200, ["2023-02-27"], True),
        ('/orjson/set_date', 200, ["2023-02-27"], True),
        ('/orjson/dict_date_date', 200, {"2023-02-27": "2023-02-27"}, True),
        ('/orjson/list_dataclass', 200, [{'item_id': "2023-02-27"}], True),
    ],
)
def test_put_orjson(path, expected_status, input_, wrap):
    response = client.put(path, json={"input_": input_} if wrap else input_)
    assert response.status_code == expected_status
    assert_json(response.json(), input_)
# endregion
