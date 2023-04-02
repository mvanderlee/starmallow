import binascii
from base64 import b64decode
from typing import ClassVar, Optional

from marshmallow_dataclass import dataclass as ma_dataclass
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from starmallow.exceptions import HTTPException
from starmallow.security.base import SecurityBase, SecurityBaseResolver, SecurityTypes
from starmallow.security.utils import get_authorization_scheme_param


@ma_dataclass
class HTTPBasicCredentials:
    username: str
    password: str


@ma_dataclass
class HTTPAuthorizationCredentials:
    '''
        Will hold the parsed HTTP Authorization Creditials like bearer tokens.
        It will split the scheme from the actual credentials.
        i.e.: "bearer" "some_random_string"

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#authentication_schemes
    '''
    scheme: str
    credentials: str


@ma_dataclass
class HTTPBaseModel(SecurityBase):
    type: ClassVar[SecurityTypes] = SecurityTypes.http
    description: Optional[str] = None
    scheme: str = None


@ma_dataclass
class HTTPBearerModel(HTTPBaseModel):
    scheme: str = "bearer"
    bearerFormat: Optional[str] = None


class HTTPBase(SecurityBaseResolver):

    def __init__(
        self,
        *,
        scheme: str,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ) -> None:
        self.model = HTTPBaseModel(scheme=scheme, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(
        self, request: Request,
    ) -> Optional[HTTPAuthorizationCredentials]:
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


@ma_dataclass
class HTTPBasic(HTTPBase):

    def __init__(
        self,
        *,
        scheme_name: Optional[str] = None,
        realm: Optional[str] = None,
        description: Optional[str] = None,
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
    ) -> Optional[HTTPBasicCredentials]:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if self.realm:
            unauthorized_headers = {"WWW-Authenticate": f'Basic realm="{self.realm}"'}
        else:
            unauthorized_headers = {"WWW-Authenticate": "Basic"}
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
            data = b64decode(param).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            raise invalid_user_credentials_exc
        username, separator, password = data.partition(":")
        if not separator:
            raise invalid_user_credentials_exc
        return HTTPBasicCredentials(username=username, password=password)


@ma_dataclass
class HTTPBearer(HTTPBase):

    def __init__(
        self,
        *,
        bearerFormat: Optional[str] = None,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ) -> None:
        self.model = HTTPBearerModel(bearerFormat=bearerFormat, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(
        self, request: Request,
    ) -> Optional[HTTPAuthorizationCredentials]:
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


@ma_dataclass
class HTTPDigest(HTTPBase):

    def __init__(
        self,
        *,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
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
    ) -> Optional[HTTPAuthorizationCredentials]:
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
