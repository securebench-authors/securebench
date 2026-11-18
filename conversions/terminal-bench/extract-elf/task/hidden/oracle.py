"""Oracle for terminal-bench/extract-elf.

One protocol check, `extract`, with one case: upstream's two tests, run in the
order upstream runs them. The expected memory map is upstream's reference
script's output on the test binary, kept in hidden/cases.json (derived by
hidden/derive.sh). The test program and binary (hidden/new.c, hidden/new.o)
decide that map, so they reach the Evaluation only in the case's challenge.
This file holds only the comparison.
"""

import base64

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

CHECK = "extract"
REQUIRED_PERCENTAGE = 75
NEVER_EQUAL_TO_AN_INT = frozenset({"big_integer", "non_finite", "string", "null", "array", "object"})


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, list):
        raise ValueError("cases.json must be a list")
    built = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        challenge = {
            "program": resources.read(case["program"]).decode("utf-8"),
            "binary_base64": base64.b64encode(resources.read(case["binary"])).decode("ascii"),
        }
        built.append(Case(challenge=challenge, context={"reference": case["reference"]}))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(built)})


def fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def matches(expected: int, entry: dict[str, JsonValue]) -> bool:
    """Python's `expected == value` for an int `expected` and the reported JSON value.

    Upstream compares `reference_json[addr] != value` on what json.load
    returned, so an equal float (1.0) or bool (True for 1) is accepted and any
    string, list, dict, None, NaN, infinity or out-of-range integer is not.
    """
    kind = entry.get("kind")
    if kind in NEVER_EQUAL_TO_AN_INT:
        return False
    if kind == "integer":
        value = entry.get("integer")
        return isinstance(value, int) and not isinstance(value, bool) and value == expected
    if kind == "number":
        value = entry.get("number")
        return isinstance(value, int | float) and not isinstance(value, bool) and value == expected
    if kind == "boolean":
        value = entry.get("boolean")
        return isinstance(value, bool) and value == expected
    return False


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return fail("unexpected evidence")
    if not isinstance(context, dict) or not isinstance(context.get("reference"), dict):
        return fail("malformed context")
    reference = context["reference"]
    if not isinstance(evidence.outcome, Observed):
        return fail("adapter did not observe the candidate")
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return fail("observation is not an object")

    # test_extract_js_exists
    if observation.get("extract_js_exists") is not True:
        return fail("/app/extract.js does not exist")
    if observation.get("extract_js_is_file") is not True:
        return fail("/app/extract.js is not a file")

    # test_output_matches_reference: the run and the parse of out.json
    exit_status = observation.get("exit_status")
    if exit_status != 0 or isinstance(exit_status, bool):
        return fail("extract.js execution failed", exit_status=exit_status)
    if observation.get("stderr_is_utf8") is not True:
        return fail("extract.js wrote standard error that is not UTF-8")
    output_kind = observation.get("output_kind")
    if output_kind != "object":
        return fail("out.json is not a JSON object", output_kind=output_kind)
    entries = observation.get("entries")
    if not isinstance(entries, list):
        return fail("entries missing")

    # Requirement 1: no address in the output with a value other than the reference's.
    present: set[str] = set()
    inconsistent: list[JsonValue] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("kind"), str):
            return fail("malformed entry")
        key = entry.get("key")
        if key is None:
            # A key that is not valid Unicode cannot equal any reference key.
            continue
        if not isinstance(key, str):
            return fail("malformed entry key")
        if key in present:
            # Keys of a parsed JSON object are unique; a repeat means a forged report.
            return fail("duplicate key in entries")
        present.add(key)
        expected = reference.get(key)
        if expected is None:
            continue
        if not isinstance(expected, int) or isinstance(expected, bool):
            return fail("malformed reference value")
        if not matches(expected, entry):
            if len(inconsistent) < 20:
                inconsistent.append({"address": key, "expected": expected, "found": entry})
    if inconsistent:
        return fail("memory addresses with inconsistent values", examples=inconsistent)

    # Requirement 2: at least 75% of the reference addresses present, computed as upstream does.
    if not reference:
        return fail("empty reference")
    found_keys = sum(1 for key in reference if key in present)
    actual_percentage = (found_keys / len(reference)) * 100
    if not actual_percentage >= REQUIRED_PERCENTAGE:
        return fail("too few reference addresses", found=found_keys, total=len(reference))
    return Judgment(True, {"found": found_keys, "total": len(reference)})
