import inspect

from typing_inspect import is_generic_type


def get_orig_class(obj):
    """
    Allows you got get the runtime origin class inside __init__

    Near duplicate of https://github.com/Stewori/pytypes/blob/master/pytypes/type_util.py#L182
    """
    try:
        return object.__getattribute__(obj, "__orig_class__")
    except AttributeError:
        cls = object.__getattribute__(obj, "__class__")
        if is_generic_type(cls):
            # Searching from index 1 is sufficient: At 0 is get_orig_class, at 1 is the caller.
            frame = inspect.currentframe()
            if frame is None:
                raise ValueError('Frame does not have a caller') from None

            frame = frame.f_back
            try:
                while frame:
                    try:
                        res = frame.f_locals["self"]
                        if res.__origin__ is cls:
                            return res
                    except (KeyError, AttributeError):
                        frame = frame.f_back
            finally:
                del frame

        raise
