"""Oracle for terminal-bench/video-processing.

Each case maps to one upstream test in tests/test_outputs.py; the frame ranges,
the allowed third-party modules and Python 3.13's standard library module names
live in hidden/cases.json and hidden/stdlib_module_names.json.
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

NUMERIC_KINDS = ("integer", "float", "boolean")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    stdlib = resources.read_json("stdlib_module_names.json")
    exists = tuple(Case(item["challenge"], {"test": item["test"]}) for item in cases["video-exists"])
    analyzer = tuple(
        Case(
            item["challenge"],
            {"test": item["test"], "takeoff_range": item["takeoff_range"], "landing_range": item["landing_range"]},
        )
        for item in cases["jump-analyzer"]
    )
    imports = tuple(
        Case(
            item["challenge"],
            {"test": item["test"], "allowed_third_party": item["allowed_third_party"], "stdlib": stdlib},
        )
        for item in cases["imports"]
    )
    return Plan(artifact_contexts={}, cases={"video-exists": exists, "jump-analyzer": analyzer, "imports": imports})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return _fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed) or not isinstance(evidence.outcome.value, dict):
        return _fail("the adapter returned no observation")
    observation = evidence.outcome.value
    if check_id == "video-exists":
        return _judge_exists(observation)
    if check_id == "jump-analyzer":
        return _judge_analyzer(context, observation)
    if check_id == "imports":
        return _judge_imports(context, observation)
    return _fail("unknown check")


def _fail(reason: str) -> Judgment:
    return Judgment(False, {"reason": reason})


def _judge_exists(observation: dict) -> Judgment:
    if observation.get("exists") is not True:
        return _fail("video file does not exist")
    return Judgment(True, None)


def _judge_analyzer(context: dict, observation: dict) -> Judgment:
    # The order follows the assertions in upstream's _test_jump_analyzer_video.
    if observation.get("video_exists") is not True:
        return _fail("video file does not exist")
    run = observation.get("run")
    if not isinstance(run, dict):
        return _fail("jump_analyzer.py was not run")
    if run.get("output_decodes") is not True:
        return _fail("jump_analyzer.py printed output that does not decode as UTF-8")
    returncode = run.get("returncode")
    if not isinstance(returncode, int) or isinstance(returncode, bool) or returncode != 0:
        return _fail(f"jump_analyzer.py exited with {returncode}")
    status = run.get("output_toml")
    if status == "absent":
        return _fail("output.toml was not created")
    if status != "parsed":
        return _fail("failed to parse output.toml")
    found = {}
    for key, name in (("takeoff", "jump_takeoff_frame_number"), ("landing", "jump_land_frame_number")):
        field = run.get(key)
        if not isinstance(field, dict) or field.get("kind") == "absent":
            return _fail(f"missing required field: {name}")
        found[key] = field
    for key, label in (("takeoff", "Takeoff"), ("landing", "Landing")):
        verdict = _in_range(found[key], context[key + "_range"])
        if verdict is not None:
            return _fail(f"{label} frame {verdict}")
    return Judgment(True, {"takeoff": found["takeoff"].get("value"), "landing": found["landing"].get("value")})


def _in_range(field: dict, bounds: list) -> str | None:
    kind = field.get("kind")
    value = field.get("value")
    if kind not in NUMERIC_KINDS:
        return f"is not a number (kind {kind})"
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "has no numeric value"
    low, high = bounds
    if not low <= value <= high:
        return f"{value} not within inclusive range"
    return None


def _judge_imports(context: dict, observation: dict) -> Judgment:
    status = observation.get("file")
    if status == "absent":
        return _fail("jump_analyzer.py does not exist")
    if status != "parsed":
        return _fail("jump_analyzer.py could not be read or parsed")
    names = observation.get("imports")
    count = observation.get("count")
    if not isinstance(names, list) or not isinstance(count, int) or isinstance(count, bool):
        return _fail("import list missing")
    if not all(isinstance(name, str) for name in names):
        return _fail("import list malformed")
    if count != len(names):
        return _fail("more distinct imports than the standard library and the allowlist hold")
    allowed = set(context["allowed_third_party"])
    stdlib = set(context["stdlib"])
    forbidden = sorted(name for name in names if name not in stdlib and name not in allowed)
    if forbidden:
        return _fail(f"forbidden third-party imports found: {forbidden[:20]}")
    return Judgment(True, None)
