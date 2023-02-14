import marshmallow as ma
import marshmallow.fields as mf


class HTTPValidationError(ma.Schema):
    status_code = mf.Integer(required=True, metadata={'description': "HTTP status code"})
    detail = mf.Raw(required=True, metadata={'description': "Error detail"})
    errors = mf.Raw(metadata={'description': "Exception or error type"})
