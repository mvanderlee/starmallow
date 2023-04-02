from enum import Enum
from typing import ClassVar, Optional

from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN

from starmallow.dataclasses import required_field
from starmallow.exceptions import HTTPException
from starmallow.security.base import SecurityBase, SecurityBaseResolver, SecurityTypes


class APIKeyIn(Enum):
    query = "query"
    header = "header"
    cookie = "cookie"


@ma_dataclass
class APIKeyModel(SecurityBase):
    type: ClassVar[SecurityTypes] = SecurityTypes.apiKey
    in_: APIKeyIn = required_field(data_key='in')
    name: str = required_field()


class APIKeyQuery(SecurityBaseResolver):
    def __init__(
        self,
        *,
        name: str,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model: APIKeyModel = APIKeyModel(in_=APIKeyIn.query, name=name, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> Optional[str]:
        api_key = request.query_params.get(self.model.name)
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        return api_key


class APIKeyHeader(SecurityBaseResolver):
    def __init__(
        self,
        *,
        name: str,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model: APIKeyModel = APIKeyModel(in_=APIKeyIn.header, name=name, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> Optional[str]:
        api_key = request.headers.get(self.model.name)
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        return api_key


class APIKeyCookie(SecurityBaseResolver):
    def __init__(
        self,
        *,
        name: str,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model: APIKeyModel = APIKeyModel(in_=APIKeyIn.cookie, name=name, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> Optional[str]:
        api_key = request.cookies.get(self.model.name)
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        return api_key
