from typing import Any, Dict, List, Optional, Union

import marshmallow as ma
from marshmallow_dataclass2 import dataclass as ma_dataclass
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from starmallow.dataclasses import optional_field, required_field
from starmallow.exceptions import HTTPException
from starmallow.params import Form
from starmallow.security.base import SecurityBase, SecurityBaseResolver, SecurityTypes
from starmallow.security.utils import get_authorization_scheme_param


# region - Models
@ma_dataclass(frozen=True)
class OAuthFlow:
    refreshUrl: Optional[str] = optional_field()
    scopes: Dict[str, str] = optional_field(default_factory=dict)

    class Meta:
        unknown = ma.INCLUDE

    @ma.post_dump()
    def post_dump(self, data: Dict[str, Any], **kwargs):
        # Remove None values
        return {
            key: value
            for key, value in data.items()
            if value is not None
        }


@ma_dataclass(frozen=True)
class OAuthFlowImplicit(OAuthFlow):
    authorizationUrl: str = required_field()


@ma_dataclass(frozen=True)
class OAuthFlowPassword(OAuthFlow):
    tokenUrl: str = required_field()


@ma_dataclass(frozen=True)
class OAuthFlowClientCredentials(OAuthFlow):
    tokenUrl: str = required_field()


@ma_dataclass(frozen=True)
class OAuthFlowAuthorizationCode(OAuthFlow):
    authorizationUrl: str = required_field()
    tokenUrl: str = required_field()


@ma_dataclass(frozen=True)
class OAuthFlowsModel:
    implicit: Optional[OAuthFlowImplicit] = optional_field()
    password: Optional[OAuthFlowPassword] = optional_field()
    clientCredentials: Optional[OAuthFlowClientCredentials] = optional_field()
    authorizationCode: Optional[OAuthFlowAuthorizationCode] = optional_field()

    class Meta:
        unknown = ma.INCLUDE

    @ma.post_dump()
    def post_dump(self, data: Dict[str, Any], **kwargs):
        # Remove None values
        return {
            key: value
            for key, value in data.items()
            if value is not None
        }


@ma_dataclass(frozen=True)
class OAuth2Model(SecurityBase):
    type: SecurityTypes = SecurityTypes.oauth2
    flows: OAuthFlowsModel = required_field()
# endregion


class OAuth2PasswordRequestForm:
    """
    This is a dependency class, use it like:

        @app.post("/login")
        def login(form_data: OAuth2PasswordRequestForm = ResolvedParam()):
            data = form_data.parse()
            print(data.username)
            print(data.password)
            for scope in data.scopes:
                print(scope)
            if data.client_id:
                print(data.client_id)
            if data.client_secret:
                print(data.client_secret)
            return data


    It creates the following Form request parameters in your endpoint:

    grant_type: the OAuth2 spec says it is required and MUST be the fixed string "password".
        Nevertheless, this dependency class is permissive and allows not passing it. If you want to enforce it,
        use instead the OAuth2PasswordRequestFormStrict dependency.
    username: username string. The OAuth2 spec requires the exact field name "username".
    password: password string. The OAuth2 spec requires the exact field name "password".
    scope: Optional string. Several scopes (each one a string) separated by spaces. E.g.
        "items:read items:write users:read profile openid"
    client_id: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
    client_secret: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
    """

    def __init__(
        self,
        grant_type: str = Form(default=None, regex="password"),
        username: str = Form(),
        password: str = Form(),
        scope: str = Form(default=""),
        client_id: Optional[str] = Form(default=None),
        client_secret: Optional[str] = Form(default=None),
    ):
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


class OAuth2PasswordRequestFormStrict(OAuth2PasswordRequestForm):
    """
    This is a dependency class, use it like:

        @app.post("/login")
        def login(form_data: OAuth2PasswordRequestFormStrict = ResolvedParam()):
            data = form_data.parse()
            print(data.username)
            print(data.password)
            for scope in data.scopes:
                print(scope)
            if data.client_id:
                print(data.client_id)
            if data.client_secret:
                print(data.client_secret)
            return data


    It creates the following Form request parameters in your endpoint:

    grant_type: the OAuth2 spec says it is required and MUST be the fixed string "password".
        This dependency is strict about it. If you want to be permissive, use instead the
        OAuth2PasswordRequestForm dependency class.
    username: username string. The OAuth2 spec requires the exact field name "username".
    password: password string. The OAuth2 spec requires the exact field name "password".
    scope: Optional string. Several scopes (each one a string) separated by spaces. E.g.
        "items:read items:write users:read profile openid"
    client_id: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
    client_secret: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
    """

    def __init__(
        self,
        grant_type: str = Form(regex="password"),
        username: str = Form(),
        password: str = Form(),
        scope: str = Form(default=""),
        client_id: Optional[str] = Form(default=None),
        client_secret: Optional[str] = Form(default=None),
    ):
        super().__init__(
            grant_type=grant_type,
            username=username,
            password=password,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
        )


class OAuth2(SecurityBaseResolver):
    def __init__(
        self,
        *,
        flows: Union[OAuthFlowsModel, Dict[str, Dict[str, Any]]] = OAuthFlowsModel(),
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model = OAuth2Model(flows=flows, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated",
                )
            else:
                return None
        return authorization


class OAuth2PasswordBearer(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


class OAuth2AuthorizationCodeBearer(OAuth2):
    def __init__(
        self,
        authorizationUrl: str,
        tokenUrl: str,
        refreshUrl: Optional[str] = None,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            authorizationCode={
                "authorizationUrl": authorizationUrl,
                "tokenUrl": tokenUrl,
                "refreshUrl": refreshUrl,
                "scopes": scopes,
            },
        )
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None  # pragma: nocover
        return param


class SecurityScopes:
    def __init__(self, scopes: Optional[List[str]] = None):
        self.scopes = scopes or []
        self.scope_str = " ".join(self.scopes)
