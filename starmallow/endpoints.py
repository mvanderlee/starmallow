from typing import Any, ClassVar, Collection, Optional

HTTP_METHOD_FUNCS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")


class APIHTTPEndpoint:

    #: The methods this view is registered for. Uses the same default
    #: (``["GET", "HEAD", "OPTIONS"]``) as ``route`` and
    #: ``add_url_rule`` by default.
    methods: ClassVar[Optional[Collection[str]]] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:

        if "methods" not in cls.__dict__:
            methods = set()

            for base in cls.__bases__:
                if getattr(base, "methods", None):
                    methods.update(base.methods)  # type: ignore[attr-defined]

            for key in HTTP_METHOD_FUNCS:
                if hasattr(cls, key.lower()):
                    methods.add(key)

            if methods:
                cls.methods = methods

    @classmethod
    def get_routes(
        cls,
    ):
        pass
