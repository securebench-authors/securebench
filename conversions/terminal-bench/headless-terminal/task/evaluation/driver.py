"""Upstream's tests/test_outputs.py, run the way its test.sh runs it.

pytest runs the seven tests in file order, in one process, under the system
Python, with standard input on /dev/null and standard output and error
captured in temporary files. The adapter starts this driver in the same
conditions, and the driver runs the tests in the order the challenge lists
them.

The test functions are not here: each arrives in the challenge as source
text, from hidden/tests/ (the keystrokes, paths and files a test uses decide
what it should find). Each test body is upstream's, line for line, except
that every `assert` is replaced by a record of the values it compares; the
Oracle compares them. The driver defines every test before it runs the
first, as pytest collects the module before it runs any test. A test that
raises is recorded with its exception, which pytest would report as a
failure.

Usage: python3 -I driver.py <JSON list of {"name", "source"}> <result path>
"""

import io
import json
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# pytest's console script runs with its own directory first on sys.path, and
# the test module appends /app (upstream line 8). -I left out the first.
sys.path.insert(0, "/usr/local/bin")
sys.path.append("/app")

ERROR_CHARACTERS = 2000


class _NoInput:
    """What pytest puts in sys.stdin while it captures output."""

    encoding = None

    def _refuse(self, *args):
        raise OSError("pytest: reading from stdin while output is captured!  Consider using `-s`.")

    read = readline = readlines = __next__ = _refuse

    def __iter__(self):
        return self

    def fileno(self):
        raise io.UnsupportedOperation("redirected stdin is pseudofile, has no fileno()")

    def isatty(self):
        return False

    def close(self):
        pass

    @property
    def buffer(self):
        return self


class _Response:
    """The part of requests.Response the upstream test reads."""

    def __init__(self, status_code, content_type, content):
        self.status_code = status_code
        self.text = _text(content_type, content)


def _parse_content_type_header(header):
    # requests 2.32.5, utils._parse_content_type_header, unchanged.
    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    items_to_strip = "\"' "
    for param in params:
        param = param.strip()
        if param:
            key, value = param, True
            index_of_equals = param.find("=")
            if index_of_equals != -1:
                key = param[:index_of_equals].strip(items_to_strip)
                value = param[index_of_equals + 1 :].strip(items_to_strip)
            params_dict[key.lower()] = value
    return content_type, params_dict


def _encoding_from_header(content_type):
    # requests 2.32.5, utils.get_encoding_from_headers, unchanged.
    if not content_type:
        return None
    content_type, params = _parse_content_type_header(content_type)
    if "charset" in params:
        return params["charset"].strip("'\"")
    if "text" in content_type:
        return "ISO-8859-1"
    if "application/json" in content_type:
        # Assume UTF-8 based on RFC 4627: https://www.ietf.org/rfc/rfc4627.txt since the charset was unset
        return "utf-8"


def _text(content_type, content):
    # requests 2.32.5, Response.text. Without a Content-Type requests guesses
    # the encoding with charset_normalizer; that guess is not reimplemented,
    # and str() falls back to UTF-8 as requests does when the guess fails.
    if not content:
        return ""
    encoding = _encoding_from_header(content_type)
    try:
        return str(content, encoding, errors="replace")
    except (LookupError, TypeError):
        return str(content, errors="replace")


def _get(url):
    """requests.get(url), the one call upstream makes, on the standard library."""
    try:
        with urllib.request.urlopen(url) as response:
            return _Response(response.status, response.headers.get("Content-Type"), response.read())
    except urllib.error.HTTPError as error:
        # requests returns 4xx and 5xx responses instead of raising.
        return _Response(error.code, error.headers.get("Content-Type"), error.read())


def _record_file(record, path):
    # Upstream's file tests assert path.exists() and then compare the stripped
    # text; this records both values.
    record["exists"] = path.exists()
    if record["exists"]:
        record["text"] = path.read_text()


# The module-level names the tests use: upstream's imports, the recorder for
# its file assertions and the stand-in for requests.get.
TEST_GLOBALS = {
    "Path": Path,
    "shlex": shlex,
    "subprocess": subprocess,
    "_get": _get,
    "_record_file": _record_file,
}


def _describe(error):
    try:
        text = f"{type(error).__name__}: {error}"
    except BaseException:
        text = type(error).__name__
    return text[:ERROR_CHARACTERS]


def main():
    tests = json.loads(sys.argv[1])
    result_path = sys.argv[2]
    namespace = dict(TEST_GLOBALS)
    for test in tests:
        exec(compile(test["source"], f"<{test['name']}>", "exec"), namespace)
    sys.stdin = _NoInput()
    results = {}
    for test in tests:
        name = test["name"]
        record = {}
        try:
            namespace[name](record)
        except BaseException as error:  # pytest reports any exception from a test as its failure
            record["error"] = _describe(error)
        results[name] = record
    with open(result_path, "w", encoding="utf-8") as stream:
        json.dump(results, stream)


if __name__ == "__main__":
    main()
