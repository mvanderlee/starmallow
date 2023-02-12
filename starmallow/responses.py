import marshmallow as ma
import marshmallow.fields as mf


class HTTPValidationError(ma.Schema):
    status_code = mf.Integer(required=True, description="HTTP status code")
    detail = mf.Raw(required=True, description="Error detail")
    errors = mf.Raw(description="Exception or error type")
