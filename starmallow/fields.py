'''
    Defines custom Marshmallow fields mostly for integrating with marshmallow_dataclass NewType
    This allows us to document them properly in OpenAPI
'''

import marshmallow.fields as mf

from .delimited_field import DelimitedFieldMixin


class DelimitedListUUID(DelimitedFieldMixin, mf.List):
    def __init__(self, *, delimiter: str | None = None, **kwargs):
        super().__init__(mf.UUID(), delimiter=delimiter, **kwargs)


class DelimitedListStr(DelimitedFieldMixin, mf.List):
    def __init__(self, *, delimiter: str | None = None, **kwargs):
        super().__init__(mf.String(), delimiter=delimiter, **kwargs)


class DelimitedListInt(DelimitedFieldMixin, mf.List):
    def __init__(self, *, delimiter: str | None = None, **kwargs):
        super().__init__(mf.Integer(), delimiter=delimiter, **kwargs)


class HttpUrl(mf.Url):
    def __init__(
        self,
        *,
        relative: bool = False,
        require_tld: bool = True,
        **kwargs,
    ):
        super().__init__(
            schemes={'http', 'https'},
            relative=relative,
            require_tld=require_tld,
            **kwargs
        )
