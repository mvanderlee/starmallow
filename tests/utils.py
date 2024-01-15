import difflib
import json


class SortedDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, *args, object_hook=self.object_hook, **kwargs)

    def object_hook(self, obj):
        new_obj = {}
        for k, v in obj.items():
            if isinstance(v, list) and len(v) != 0:
                if isinstance(v[0], dict):
                    # Python3's sorted function doesn't handle dicts,
                    # so here we take the list of dicts, and sort them by their json string.
                    # This allows us to ignore the order when comparing list of dicts
                    tmp_dict = {json.dumps(d): d for d in v}
                    sorted_keys = sorted(tmp_dict.keys())
                    new_obj[k] = [tmp_dict[k] for k in sorted_keys]
                else:
                    new_obj[k] = sorted(v)
            else:
                new_obj[k] = v
        return new_obj


def assert_json(
    actual,
    expected,
):
    '''
        Prints a nicer diff when the assertion fails.

        Source: https://github.com/pytest-dev/pytest/issues/1531#issuecomment-723590313
    '''
    left = json.dumps(actual, indent=2, sort_keys=True)
    right = json.dumps(expected, indent=2, sort_keys=True)

    # Compare sorted values - Otherwise arrays can sometimes pass, sometimes fail
    if json.loads(left, cls=SortedDecoder) != json.loads(right, cls=SortedDecoder):
        diff = difflib.unified_diff(
            left.splitlines(True),
            right.splitlines(True),
            fromfile="left",
            tofile="right",
        )
        assert 0, "\n" + "".join(diff)
