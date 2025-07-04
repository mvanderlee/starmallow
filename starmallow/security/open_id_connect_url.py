from typing import ClassVar

from marshmallow_dataclass2 import dataclass as ma_dataclass
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN

from starmallow.dataclasses import required_field
from starmallow.security.base import SecurityBase, SecurityBaseResolver, SecurityTypes


@ma_dataclass(frozen=True)
class OpenIdConnectModel(SecurityBase):
    type: ClassVar[SecurityTypes] = SecurityTypes.openIdConnect
    openIdConnectUrl: str = required_field()


class OpenIdConnect(SecurityBaseResolver):
    def __init__(
        self,
        *,
        openIdConnectUrl: str,  # noqa: N803
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ):
        self.model = OpenIdConnectModel(
            openIdConnectUrl=openIdConnectUrl, description=description,
        )
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> str | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        return authorization
