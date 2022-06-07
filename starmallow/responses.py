import marshmallow as ma
import marshmallow.fields as mf


class APIError(ma.Schema):
    status_code = mf.Integer(description="HTTP status code", required=True)
    detail = mf.Raw(description="Error detail", required=True)
    errors = mf.Raw(description="Exception or error type")
