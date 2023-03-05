import json
from typing import Any

import marshmallow as ma
from starlette.websockets import WebSocket, WebSocketState

from starmallow.serializers import JSONEncoder
from starmallow.utils import is_marshmallow_dataclass


class APIWebSocket(WebSocket):

    async def receive_json(
        self,
        mode: str = "text",
        model: ma.Schema = None,
    ) -> Any:
        if mode not in {"text", "binary"}:
            raise RuntimeError('The "mode" argument should be "text" or "binary".')
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.',
            )
        message = await self.receive()
        self._raise_on_disconnect(message)

        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")

        if model:
            if isinstance(model, ma.Schema):
                schema = model
            elif isinstance(model, type) and issubclass(model, ma.Schema):
                schema = model()
            else:
                raise TypeError(f"model was of unexpected type {type(model)}")
            return schema.loads(text)

        return json.loads(text)

    async def send_json(
        self,
        data: Any,
        mode: str = "text",
        model: ma.Schema = None,
    ) -> None:
        if mode not in {"text", "binary"}:
            raise RuntimeError('The "mode" argument should be "text" or "binary".')

        if model:
            if isinstance(model, ma.Schema):
                schema = model
            elif isinstance(model, type) and issubclass(model, ma.Schema):
                schema = model()
            else:
                raise TypeError(f"model was of unexpected type {type(model)}")
            text = schema.dumps(data)
        elif is_marshmallow_dataclass(data):
            text = data.Schema().dumps(data)
        else:
            text = json.dumps(data, cls=JSONEncoder)

        if mode == "text":
            await self.send({"type": "websocket.send", "text": text})
        else:
            await self.send({"type": "websocket.send", "bytes": text.encode("utf-8")})
