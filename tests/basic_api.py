import datetime as dt
import http
from decimal import Decimal
from enum import Enum
from typing import Final, FrozenSet, Literal, Optional
from uuid import UUID

from marshmallow.validate import Length, Range, Regexp
from marshmallow_dataclass import dataclass as ma_dataclass

from starmallow import Path, Query, StarMallow

app = StarMallow()


class MyEnum(Enum):
    optionA = 'optionA'
    optionB = 'optionB'


@app.api_route("/api_route")
def non_operation():
    return {"message": "Hello World"}


def non_decorated_route():
    return {"message": "Hello World"}


app.add_api_route("/non_decorated_route", non_decorated_route)


# Tests no input, and no annotated response
@app.get("/text")
def get_text():
    return "Hello World"


# Test input that matches path param with no annotated response
@app.get("/path/{item_id}")
def get_id(item_id):
    return item_id


#########################################################
# Test all supported types
#########################################################
@app.get("/path/str/{item_id}")
def get_str_id(item_id: str):
    return item_id


@app.get("/path/int/{item_id}")
def get_int_id(item_id: int):
    return item_id


@app.get("/path/float/{item_id}")
def get_float_id(item_id: float):
    return item_id


@app.get("/path/bool/{item_id}")
def get_bool_id(item_id: bool):
    return item_id


@app.get("/path/date/{item_id}")
def get_date_id(item_id: dt.date):
    return item_id


@app.get("/path/datetime/{item_id}")
def get_datetime_id(item_id: dt.datetime):
    return item_id


@app.get("/path/time/{item_id}")
def get_time_id(item_id: dt.time):
    return item_id


@app.get("/path/timedelta/{item_id}")
def get_timedelta_id(item_id: dt.timedelta):
    return item_id


@app.get("/path/uuid/{item_id}")
def get_uuid_id(item_id: UUID):
    return item_id


@app.get("/path/decimal/{item_id}")
def get_decimal_id(item_id: Decimal):
    return item_id


@app.get("/path/enum/{item_id}")
def get_enum_id(item_id: MyEnum):
    return item_id


@app.get("/path/literal/{item_id}")
def get_literal_id(item_id: Literal['alpha', 'beta']):
    return item_id


# Final can only be used inside a class, not as a function argument
@ma_dataclass
class FinalItem:
    item_id: Final[int] = 10


@app.get("/path/final/{item_id}")
def get_final_id(item_id: FinalItem = Path()):
    return item_id


#########################################################
# Test Path parameters
#########################################################
@app.get("/path/param/{item_id}")
def get_path_param_id(item_id: str = Path()):
    return item_id


@app.get("/path/param-required/{item_id}")
def get_path_param_required_id(item_id: str = Path()):
    return item_id


@app.get("/path/param-deprecated/{item_id}")
def get_path_param_deprecated_id(item_id: str = Path(deprecated=True)):
    return item_id


@app.get("/path/param-exclude/{item_id}")
def get_path_param_exclude_id(item_id: str = Path(include_in_schema=False)):
    return item_id


@app.get("/path/param-title/{item_id}")
def get_path_param_title_id(item_id: str = Path(title='Custom Item Title')):
    return item_id


#########################################################
# Test Convience validators
#########################################################
@app.get("/path/param-minlength/{item_id}")
def get_path_param_min_length(item_id: str = Path(min_length=3)):
    return item_id


@app.get("/path/param-maxlength/{item_id}")
def get_path_param_max_length(item_id: str = Path(max_length=3)):
    return item_id


@app.get("/path/param-min_maxlength/{item_id}")
def get_path_param_min_max_length(item_id: str = Path(max_length=3, min_length=2)):
    return item_id


@app.get("/path/param-regex/{item_id}")
def get_path_param_regex(item_id: str = Path(regex='colou?r')):
    return item_id


@app.get("/path/param-gt/{item_id}")
def get_path_param_gt(item_id: float = Path(gt=3)):
    return item_id


@app.get("/path/param-gt0/{item_id}")
def get_path_param_gt0(item_id: float = Path(gt=0)):
    return item_id


@app.get("/path/param-ge/{item_id}")
def get_path_param_ge(item_id: float = Path(ge=3)):
    return item_id


@app.get("/path/param-lt/{item_id}")
def get_path_param_lt(item_id: float = Path(lt=3)):
    return item_id


@app.get("/path/param-lt0/{item_id}")
def get_path_param_lt0(item_id: float = Path(lt=0)):
    return item_id


@app.get("/path/param-le/{item_id}")
def get_path_param_le(item_id: float = Path(le=3)):
    return item_id


@app.get("/path/param-lt-gt/{item_id}")
def get_path_param_lt_gt(item_id: float = Path(lt=3, gt=1)):
    return item_id


@app.get("/path/param-le-ge/{item_id}")
def get_path_param_le_ge(item_id: float = Path(le=3, ge=1)):
    return item_id


@app.get("/path/param-lt-int/{item_id}")
def get_path_param_lt_int(item_id: int = Path(lt=3)):
    return item_id


@app.get("/path/param-gt-int/{item_id}")
def get_path_param_gt_int(item_id: int = Path(gt=3)):
    return item_id


@app.get("/path/param-le-int/{item_id}")
def get_path_param_le_int(item_id: int = Path(le=3)):
    return item_id


@app.get("/path/param-ge-int/{item_id}")
def get_path_param_ge_int(item_id: int = Path(ge=3)):
    return item_id


@app.get("/path/param-lt-gt-int/{item_id}")
def get_path_param_lt_gt_int(item_id: int = Path(lt=3, gt=1)):
    return item_id


@app.get("/path/param-le-ge-int/{item_id}")
def get_path_param_le_ge_int(item_id: int = Path(le=3, ge=1)):
    return item_id


#########################################################
# Test Marshmallow validators
#########################################################
@app.get("/path/ma-param-minlength/{item_id}")
def get_path_ma_param_min_length(item_id: str = Path(validators=Length(min=3))):
    return item_id


@app.get("/path/ma-param-maxlength/{item_id}")
def get_path_ma_param_max_length(item_id: str = Path(validators=Length(max=3))):
    return item_id


@app.get("/path/ma-param-regex/{item_id}")
def get_path_ma_param_regex(item_id: str = Path(validators=Regexp('colou?r'))):
    return item_id


@app.get("/path/ma-param-min_maxlength/{item_id}")
def get_path_ma_param_min_max_length(item_id: str = Path(validators=Length(min=2, max=3))):
    return item_id


@app.get("/path/ma-param-gt/{item_id}")
def get_path_ma_param_gt(item_id: float = Path(validators=Range(min=3.0, min_inclusive=False))):
    return item_id


@app.get("/path/ma-param-gt0/{item_id}")
def get_path_ma_param_gt0(item_id: float = Path(validators=Range(min=0.0, min_inclusive=False))):
    return item_id


@app.get("/path/ma-param-ge/{item_id}")
def get_path_ma_param_ge(item_id: float = Path(validators=Range(min=3.0))):
    return item_id


@app.get("/path/ma-param-lt/{item_id}")
def get_path_ma_param_lt(item_id: float = Path(validators=Range(max=3.0, max_inclusive=False))):
    return item_id


@app.get("/path/ma-param-lt0/{item_id}")
def get_path_ma_param_lt0(item_id: float = Path(validators=Range(max=0.0, max_inclusive=False))):
    return item_id


@app.get("/path/ma-param-le/{item_id}")
def get_path_ma_param_le(item_id: float = Path(validators=Range(max=3.0))):
    return item_id


@app.get("/path/ma-param-lt-gt/{item_id}")
def get_path_ma_param_lt_gt(item_id: float = Path(validators=Range(min=1.0, max=3.0, min_inclusive=False, max_inclusive=False))):
    return item_id


@app.get("/path/ma-param-le-ge/{item_id}")
def get_path_ma_param_le_ge(item_id: float = Path(validators=Range(min=1.0, max=3.0))):
    return item_id


@app.get("/path/ma-param-lt-int/{item_id}")
def get_path_ma_param_lt_int(item_id: int = Path(validators=Range(max=3, max_inclusive=False))):
    return item_id


@app.get("/path/ma-param-gt-int/{item_id}")
def get_path_ma_param_gt_int(item_id: int = Path(validators=Range(min=3, min_inclusive=False))):
    return item_id


@app.get("/path/ma-param-le-int/{item_id}")
def get_path_ma_param_le_int(item_id: int = Path(validators=Range(max=3))):
    return item_id


@app.get("/path/ma-param-ge-int/{item_id}")
def get_path_ma_param_ge_int(item_id: int = Path(validators=Range(min=3))):
    return item_id


@app.get("/path/ma-param-lt-gt-int/{item_id}")
def get_path_ma_param_lt_gt_int(
    item_id: int = Path(
        validators=Range(
            min=1,
            max=3,
            min_inclusive=False,
            max_inclusive=False,
        ),
    ),
):
    return item_id


@app.get("/path/ma-param-le-ge-int/{item_id}")
def get_path_ma_param_le_ge_int(item_id: int = Path(validators=Range(min=1, max=3))):
    return item_id


#########################################################
#
#########################################################
@app.get("/query")
def get_query(query):
    return f"foo bar {query}"


@app.get("/query/optional")
def get_query_optional(query=None):
    if query is None:
        return "foo bar"
    return f"foo bar {query}"


@app.get("/query/int")
def get_query_type(query: int):
    return f"foo bar {query}"


@app.get("/query/int/optional")
def get_query_type_optional(query: Optional[int] = None):
    if query is None:
        return "foo bar"
    return f"foo bar {query}"


@app.get("/query/int/default")
def get_query_type_int_default(query: int = 10):
    return f"foo bar {query}"


@app.get("/query/param")
def get_query_param(query=Query(default=None)):
    if query is None:
        return "foo bar"
    return f"foo bar {query}"


@app.get("/query/param-required")
def get_query_param_required(query=Query()):
    return f"foo bar {query}"


@app.get("/query/param-required/int")
def get_query_param_required_type(query: int = Query()):
    return f"foo bar {query}"


@app.get("/enum-status-code", status_code=http.HTTPStatus.CREATED)
def get_enum_status_code():
    return "foo bar"


@app.get("/query/frozenset")
def get_query_type_frozenset(query: FrozenSet[int] = Query(...)):
    return ",".join(map(str, sorted(query)))
