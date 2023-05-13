import json
from typing import Any, Dict, Optional

import marshmallow as ma
import marshmallow.fields as mf
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse as StarJSONResponse

from .serializers import JSONEncoder, json_default

try:
    import ujson
except ImportError:  # pragma: nocover
    ujson = None  # type: ignore


try:
    import orjson
except ImportError:  # pragma: nocover
    orjson = None  # type: ignore


class JSONResponse(StarJSONResponse):

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            cls=JSONEncoder,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


class UJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        assert ujson is not None, "ujson must be installed to use UJSONResponse"
        return ujson.dumps(content, default=json_default, ensure_ascii=False).encode("utf-8")


class ORJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        assert orjson is not None, "orjson must be installed to use ORJSONResponse"
        return orjson.dumps(
            content,
            default=json_default,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
        )


class HTTPValidationError(ma.Schema):
    status_code = mf.Integer(required=True, metadata={'description': "HTTP status code"})
    detail = mf.Raw(required=True, metadata={'description': "Error detail"})
    errors = mf.Raw(metadata={'description': "Exception or error type"})
