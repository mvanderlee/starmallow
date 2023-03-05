import difflib
import json


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

    if left != right:
        diff = difflib.unified_diff(
            left.splitlines(True),
            right.splitlines(True),
            fromfile="left",
            tofile="right",
        )
        assert 0, "\n" + "".join(diff)
