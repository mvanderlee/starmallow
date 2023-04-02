from enum import Enum
from typing import Any, ClassVar, Dict, Optional

import marshmallow as ma
from marshmallow_dataclass import dataclass as ma_dataclass


# Provided by: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#security-scheme-object
class SecurityTypes(Enum):
    apiKey = "apiKey"
    http = "http"
    mutualTLS = "mutualTLS"
    oauth2 = "oauth2"
    openIdConnect = "openIdConnect"


@ma_dataclass
class SecurityBase:
    type: ClassVar[SecurityTypes]
    description: Optional[str] = None

    @ma.post_dump()
    def post_dump(self, data: Dict[str, Any], **kwargs):
        # Remove None values
        return {
            key: value
            for key, value in data.items()
            if value is not None
        }


class SecurityBaseResolver:
    # I've thought about making this a dataclass, but then we'd have to use __post_init__ etc and it gets
    # more complicated to understand than just basic __init__

    def __init__(
        self,
        model: SecurityBase,
        scheme_name: str,
    ) -> None:
        self.model = model
        self.schema_name = scheme_name
