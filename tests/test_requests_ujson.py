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
from starmallow.requests import UJSONRequest

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
@app.put("/ujson/str", request_class=UJSONRequest)
def put_ujson_str(input_: str = Body()) -> str:
    assert type(input_) == str
    return input_


@app.put("/ujson/int", request_class=UJSONRequest)
def put_ujson_int(input_: int = Body()) -> int:
    assert type(input_) == int
    return input_


@app.put("/ujson/bool", request_class=UJSONRequest)
def put_ujson_bool(input_: bool = Body()) -> bool:
    assert type(input_) == bool
    return input_


@app.put("/ujson/date", request_class=UJSONRequest)
def put_ujson_date(input_: dt.date = Body()) -> dt.date:
    assert type(input_) == dt.date
    return input_


@app.put("/ujson/datetime", request_class=UJSONRequest)
def put_ujson_datetime(input_: dt.datetime = Body()) -> dt.datetime:
    assert type(input_) == dt.datetime
    return input_


@app.put("/ujson/time", request_class=UJSONRequest)
def put_ujson_time(input_: dt.time = Body()) -> dt.time:
    assert type(input_) == dt.time
    return input_


@app.put("/ujson/timedelta", request_class=UJSONRequest)
def put_ujson_timedelta(input_: dt.timedelta = Body()) -> dt.timedelta:
    assert type(input_) == dt.timedelta
    return input_


@app.put("/ujson/uuid", request_class=UJSONRequest)
def put_ujson_uuid(input_: UUID = Body()) -> UUID:
    assert type(input_) == UUID
    return input_


@app.put("/ujson/decimal", request_class=UJSONRequest)
def put_ujson_decimal(input_: Decimal = Body()) -> Decimal:
    assert type(input_) == Decimal
    return input_


@app.put("/ujson/enum", request_class=UJSONRequest)
def put_ujson_enum(input_: MyEnum = Body()) -> MyEnum:
    assert type(input_) == MyEnum
    return input_


@app.put("/ujson/literal", request_class=UJSONRequest)
def put_ujson_literal(input_: Literal['alpha', 'beta'] = Body()) -> Literal['alpha', 'beta']:
    assert input_ in ['alpha', 'beta']
    return input_


# Final can only be used inside a class, not as a function argument
@ma_dataclass
class FinalItem:
    item_id: Final[int] = 10


@app.put("/ujson/final", request_class=UJSONRequest)
def put_ujson_final(input_: FinalItem = Body()) -> FinalItem:
    assert type(input_) == FinalItem
    return input_


@app.put("/ujson/date_field", request_class=UJSONRequest)
def put_ujson_date_field(input_: mf.Date = Body()) -> mf.Date:
    assert type(input_) == dt.date
    return input_


@app.put("/ujson/dataclass", request_class=UJSONRequest)
def put_ujson_dataclass(input_: Item = Body()) -> Item:
    assert type(input_) == Item
    return input_


@app.put("/ujson/schema", request_class=UJSONRequest)
def put_ujson_schema(input_: Item.Schema = Body()) -> Item.Schema:
    assert type(input_) == Item
    return input_


@app.put("/ujson/list_date", request_class=UJSONRequest)
def put_ujson_list_date(input_: List[dt.date] = Body()) -> List[dt.date]:
    assert type(input_) == list
    assert len(input_) > 0
    assert type(input_[0]) == dt.date
    return input_


@app.put("/ujson/set_date", request_class=UJSONRequest)
def put_ujson_set_date(input_: Set[dt.date] = Body()) -> Set[dt.date]:
    assert type(input_) == set
    assert len(input_) > 0
    assert type(list(input_)[0]) == dt.date
    return input_


@app.put("/ujson/dict_date_date", request_class=UJSONRequest)
def put_ujson_dict_date_date(input_: Dict[dt.date, dt.date] = Body()) -> Dict[dt.date, dt.date]:
    assert type(input_) == dict
    assert len(input_) > 0
    assert type(list(input_.keys())[0]) == dt.date
    assert type(list(input_.values())[0]) == dt.date
    return input_


@app.put("/ujson/list_dataclass", request_class=UJSONRequest)
def put_ujson_list_dataclass(input_: List[Item] = Body()) -> List[Item]:
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
        "/ujson/str": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_str_ujson_str_put",
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
                "summary": "Put Ujson Str",
                "operationId": "put_ujson_str_ujson_str_put",
            },
        },
        "/ujson/int": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_int_ujson_int_put",
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
                "summary": "Put Ujson Int",
                "operationId": "put_ujson_int_ujson_int_put",
            },
        },
        "/ujson/bool": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_bool_ujson_bool_put",
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
                "summary": "Put Ujson Bool",
                "operationId": "put_ujson_bool_ujson_bool_put",
            },
        },
        "/ujson/date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_date_ujson_date_put",
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
                "summary": "Put Ujson Date",
                "operationId": "put_ujson_date_ujson_date_put",
            },
        },
        "/ujson/datetime": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_datetime_ujson_datetime_put",
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
                "summary": "Put Ujson Datetime",
                "operationId": "put_ujson_datetime_ujson_datetime_put",
            },
        },
        "/ujson/time": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_time_ujson_time_put",
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
                "summary": "Put Ujson Time",
                "operationId": "put_ujson_time_ujson_time_put",
            },
        },
        "/ujson/timedelta": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_timedelta_ujson_timedelta_put",
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
                "summary": "Put Ujson Timedelta",
                "operationId": "put_ujson_timedelta_ujson_timedelta_put",
            },
        },
        "/ujson/uuid": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_uuid_ujson_uuid_put",
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
                "summary": "Put Ujson Uuid",
                "operationId": "put_ujson_uuid_ujson_uuid_put",
            },
        },
        "/ujson/decimal": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_decimal_ujson_decimal_put",
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
                "summary": "Put Ujson Decimal",
                "operationId": "put_ujson_decimal_ujson_decimal_put",
            },
        },
        "/ujson/enum": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_enum_ujson_enum_put",
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
                "summary": "Put Ujson Enum",
                "operationId": "put_ujson_enum_ujson_enum_put",
            },
        },
        "/ujson/literal": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_literal_ujson_literal_put",
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
                "summary": "Put Ujson Literal",
                "operationId": "put_ujson_literal_ujson_literal_put",
            },
        },
        "/ujson/final": {
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
                "summary": "Put Ujson Final",
                "operationId": "put_ujson_final_ujson_final_put",
            },
        },
        "/ujson/date_field": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_date_field_ujson_date_field_put",
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
                "summary": "Put Ujson Date Field",
                "operationId": "put_ujson_date_field_ujson_date_field_put",
            },
        },
        "/ujson/dataclass": {
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
                "summary": "Put Ujson Dataclass",
                "operationId": "put_ujson_dataclass_ujson_dataclass_put",
            },
        },
        "/ujson/schema": {
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
                "summary": "Put Ujson Schema",
                "operationId": "put_ujson_schema_ujson_schema_put",
            },
        },
        "/ujson/list_date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_list_date_ujson_list_date_put",
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
                "summary": "Put Ujson List Date",
                "operationId": "put_ujson_list_date_ujson_list_date_put",
            },
        },
        "/ujson/set_date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_set_date_ujson_set_date_put",
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
                "summary": "Put Ujson Set Date",
                "operationId": "put_ujson_set_date_ujson_set_date_put",
            },
        },
        "/ujson/dict_date_date": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_dict_date_date_ujson_dict_date_date_put",
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
                "summary": "Put Ujson Dict Date Date",
                "operationId": "put_ujson_dict_date_date_ujson_dict_date_date_put",
            },
        },
        "/ujson/list_dataclass": {
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_put_ujson_list_dataclass_ujson_list_dataclass_put",
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
                "summary": "Put Ujson List Dataclass",
                "operationId": "put_ujson_list_dataclass_ujson_list_dataclass_put",
            },
        },
    },
    "components": {
        "schemas": {
            "Body_put_ujson_bool_ujson_bool_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "boolean",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_ujson_bool_ujson_bool_put",
                "type": "object",
            },
            "Body_put_ujson_date_field_ujson_date_field_put": {
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
                "title": "Body_put_ujson_date_field_ujson_date_field_put",
                "type": "object",
            },
            "Body_put_ujson_date_ujson_date_put": {
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
                "title": "Body_put_ujson_date_ujson_date_put",
                "type": "object",
            },
            "Body_put_ujson_datetime_ujson_datetime_put": {
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
                "title": "Body_put_ujson_datetime_ujson_datetime_put",
                "type": "object",
            },
            "Body_put_ujson_decimal_ujson_decimal_put": {
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
                "title": "Body_put_ujson_decimal_ujson_decimal_put",
                "type": "object",
            },
            "Body_put_ujson_dict_date_date_ujson_dict_date_date_put": {
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
                "title": "Body_put_ujson_dict_date_date_ujson_dict_date_date_put",
                "type": "object",
            },
            "Body_put_ujson_enum_ujson_enum_put": {
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
                "title": "Body_put_ujson_enum_ujson_enum_put",
                "type": "object",
            },
            "Body_put_ujson_int_ujson_int_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "integer",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_ujson_int_ujson_int_put",
                "type": "object",
            },
            "Body_put_ujson_list_dataclass_ujson_list_dataclass_put": {
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
                "title": "Body_put_ujson_list_dataclass_ujson_list_dataclass_put",
                "type": "object",
            },
            "Body_put_ujson_list_date_ujson_list_date_put": {
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
                "title": "Body_put_ujson_list_date_ujson_list_date_put",
                "type": "object",
            },
            "Body_put_ujson_literal_ujson_literal_put": {
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
                "title": "Body_put_ujson_literal_ujson_literal_put",
                "type": "object",
            },
            "Body_put_ujson_set_date_ujson_set_date_put": {
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
                "title": "Body_put_ujson_set_date_ujson_set_date_put",
                "type": "object",
            },
            "Body_put_ujson_str_ujson_str_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_ujson_str_ujson_str_put",
                "type": "object",
            },
            "Body_put_ujson_time_ujson_time_put": {
                "properties": {
                    "input_": {
                        "title": "Input ",
                        "type": "string",
                    },
                },
                "required": [
                    "input_",
                ],
                "title": "Body_put_ujson_time_ujson_time_put",
                "type": "object",
            },
            "Body_put_ujson_timedelta_ujson_timedelta_put": {
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
                "title": "Body_put_ujson_timedelta_ujson_timedelta_put",
                "type": "object",
            },
            "Body_put_ujson_uuid_ujson_uuid_put": {
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
                "title": "Body_put_ujson_uuid_ujson_uuid_put",
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
        ('/ujson/str', 200, "5", True),
        ('/ujson/int', 200, 5, True),
        ('/ujson/bool', 200, True, True),
        ('/ujson/date', 200, "2023-02-27", True),
        ('/ujson/datetime', 200, "2023-02-27T11:37:43", True),
        ('/ujson/time', 200, "11:37:43", True),
        ('/ujson/timedelta', 200, 108321, True),
        ('/ujson/uuid', 200, '2c55d0f6-2629-450a-8eee-71f791cd8eb9', True),
        ('/ujson/decimal', 200, "123456789", True),
        ('/ujson/enum', 200, "optionA", True),
        ('/ujson/literal', 200, "alpha", True),
        ('/ujson/final', 200, {'item_id': 10}, False),
        ('/ujson/date_field', 200, "2023-02-27", True),
        ('/ujson/dataclass', 200, {'item_id': "2023-02-27"}, False),
        ('/ujson/schema', 200, {'item_id': "2023-02-27"}, False),
        ('/ujson/list_date', 200, ["2023-02-27"], True),
        ('/ujson/set_date', 200, ["2023-02-27"], True),
        ('/ujson/dict_date_date', 200, {"2023-02-27": "2023-02-27"}, True),
        ('/ujson/list_dataclass', 200, [{'item_id': "2023-02-27"}], True),
    ],
)
def test_put_ujson(path, expected_status, input_, wrap):
    response = client.put(path, json={"input_": input_} if wrap else input_)
    assert response.status_code == expected_status
    assert_json(response.json(), input_)
# endregion
