from typing import Any, Dict, List, Union

from starlette.exceptions import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


class RequestValidationError(HTTPException):
    def __init__(
        self,
        errors: Dict[str, Union[Any, List, Dict]],
    ) -> None:
        super().__init__(status_code=HTTP_422_UNPROCESSABLE_ENTITY)
        self.errors = errors


class WebSocketRequestValidationError(HTTPException):
    def __init__(
        self,
        errors: Dict[str, Union[Any, List, Dict]],
    ) -> None:
        super().__init__(status_code=HTTP_422_UNPROCESSABLE_ENTITY)
        self.errors = errors
