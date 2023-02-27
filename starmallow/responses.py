import json
from typing import Any, Dict, Optional

import marshmallow as ma
import marshmallow.fields as mf
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse as StarJSONResponse

from .serializers import JSONEncoder


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


class HTTPValidationError(ma.Schema):
    status_code = mf.Integer(required=True, metadata={'description': "HTTP status code"})
    detail = mf.Raw(required=True, metadata={'description': "Error detail"})
    errors = mf.Raw(metadata={'description': "Exception or error type"})
