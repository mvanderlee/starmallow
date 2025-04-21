from typing import Any

from starlette.exceptions import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR


class RequestValidationError(HTTPException):
    def __init__(
        self,
        errors: dict[str, Any | list | dict],
    ) -> None:
        super().__init__(status_code=HTTP_422_UNPROCESSABLE_ENTITY)
        self.errors = errors


class WebSocketRequestValidationError(HTTPException):
    def __init__(
        self,
        errors: dict[str, Any | list | dict],
    ) -> None:
        super().__init__(status_code=HTTP_422_UNPROCESSABLE_ENTITY)
        self.errors = errors


class SchemaGenerationError(HTTPException):
    def __init__(
        self,
    ) -> None:
        super().__init__(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate schema")
