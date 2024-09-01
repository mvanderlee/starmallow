from typing import Any

from starlette.requests import Request

try:
    import ujson
except ImportError:  # pragma: nocover
    ujson = None  # type: ignore


try:
    import orjson
except ImportError:  # pragma: nocover
    orjson = None  # type: ignore


class UJSONRequest(Request):

    async def json(self) -> Any:
        assert ujson is not None, "ujson must be installed to use UJSONRequest"

        if not hasattr(self, "_json"):
            body = await self.body()
            self._json = ujson.loads(body)
        return self._json


class ORJSONRequest(Request):

    async def json(self) -> Any:
        assert orjson is not None, "orjson must be installed to use ORJSONRequest"

        if not hasattr(self, "_json"):
            body = await self.body()
            self._json = orjson.loads(body)
        return self._json
