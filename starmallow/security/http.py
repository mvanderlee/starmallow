import asyncio
import binascii
from base64 import b64decode
from typing import ClassVar

from marshmallow_dataclass2 import dataclass as ma_dataclass
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from starmallow.exceptions import HTTPException
from starmallow.security.base import SecurityBase, SecurityBaseResolver, SecurityTypes
from starmallow.security.utils import get_authorization_scheme_param


@ma_dataclass(frozen=True)
class HTTPBasicCredentials:
    username: str
    password: str


@ma_dataclass(frozen=True)
class HTTPAuthorizationCredentials:
    '''
        Will hold the parsed HTTP Authorization Creditials like bearer tokens.
        It will split the scheme from the actual credentials.
        i.e.: "bearer" "some_random_string"

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#authentication_schemes
    '''
    scheme: str
    credentials: str


@ma_dataclass(frozen=True)
class HTTPBaseModel(SecurityBase):
    type: ClassVar[SecurityTypes] = SecurityTypes.http
    description: str | None = None
    scheme: str | None = None


@ma_dataclass(frozen=True)
class HTTPBearerModel(HTTPBaseModel):
    scheme: str = "bearer"
    bearerFormat: str | None = None


class HTTPBase(SecurityBaseResolver):

    def __init__(
        self,
        *,
        scheme: str,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        self.model = HTTPBaseModel(scheme=scheme, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(
        self, request: Request,
    ) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


class HTTPBasic(HTTPBase):

    def __init__(
        self,
        *,
        scheme_name: str | None = None,
        realm: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        super().__init__(
            scheme='basic',
            description=description,
            scheme_name=scheme_name,
            auto_error=auto_error,
        )

        self.realm = realm

    async def __call__(  # type: ignore
        self, request: Request,
    ) -> HTTPBasicCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        unauthorized_headers = (
            {"WWW-Authenticate": f'Basic realm="{self.realm}"'}
            if self.realm
            else {"WWW-Authenticate": "Basic"}
        )
        invalid_user_credentials_exc = HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers=unauthorized_headers,
        )
        if not authorization or scheme.lower() != "basic":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers=unauthorized_headers,
                )
            else:
                return None
        try:
            def decode(param: str) -> str:
                return b64decode(param).decode("ascii")

            data = await asyncio.to_thread(decode, param)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            raise invalid_user_credentials_exc from None
        username, separator, password = data.partition(":")
        if not separator:
            raise invalid_user_credentials_exc
        return HTTPBasicCredentials(username=username, password=password)


class HTTPBearer(HTTPBase):

    def __init__(
        self,
        *,
        bearerFormat: str | None = None,  # noqa: N803
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        self.model = HTTPBearerModel(bearerFormat=bearerFormat, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(
        self, request: Request,
    ) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail="Invalid authentication credentials",
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


class HTTPDigest(HTTPBase):

    def __init__(
        self,
        *,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        super().__init__(
            scheme='digest',
            description=description,
            scheme_name=scheme_name,
            auto_error=auto_error,
        )

    async def __call__(
        self, request: Request,
    ) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        if scheme.lower() != "digest":
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid authentication credentials",
            )
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
