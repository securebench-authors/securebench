"""Oracle for cancel-async-tasks.

The cases and the values upstream's assertions expect are in cases.json. Each
judgment repeats one upstream test's assertions, in upstream's order, on what the
adapter observed of the driver process.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

ARTIFACT_CHECK = "run-py-exists"
RUN_CHECK = "run-to-completion"
CANCEL_CHECK = "cancel-on-interrupt"


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise ValueError("cases.json must be an object")
    cases: dict[str, tuple[Case, ...]] = {}
    for check_id in (RUN_CHECK, CANCEL_CHECK):
        entries = data[check_id]
        if not isinstance(entries, list):
            raise ValueError(f"cases.json: {check_id} must be a list")
        built = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"cases.json: {check_id} entries must be objects")
            built.append(
                Case(
                    challenge=entry["challenge"],
                    context={"upstream_test": entry["upstream_test"], "expected": entry["expected"]},
                )
            )
        cases[check_id] = tuple(built)
    return Plan(artifact_contexts={ARTIFACT_CHECK: None}, cases=cases)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == ARTIFACT_CHECK and isinstance(evidence, ArtifactEvidence):
        return judge_exists(evidence)
    if check_id in (RUN_CHECK, CANCEL_CHECK) and isinstance(evidence, CaseEvidence):
        if not isinstance(context, dict):
            return fail("bad context")
        test = context.get("upstream_test")
        expected = context.get("expected")
        if not isinstance(expected, dict):
            return fail("bad context")
        if not isinstance(evidence.outcome, Observed):
            return fail("no observation", test=test)
        observation = evidence.outcome.value
        if not isinstance(observation, dict):
            return fail("observation is not an object", test=test)
        if check_id == RUN_CHECK:
            return judge_run(test, expected, observation)
        return judge_cancel(test, expected, observation)
    return fail("unexpected check or evidence", check=check_id)


def judge_exists(evidence: ArtifactEvidence) -> Judgment:
    # Path("/app/run.py").exists() is true for anything at that path, so only
    # absence fails. The protocol checks import the file, so a run.py that is
    # not a working module fails there.
    if len(evidence.files) != 1:
        return fail("expected exactly one file in the evidence")
    found = evidence.files[0]
    if found.status is FileStatus.ABSENT:
        return fail("File /app/run.py does not exist")
    return Judgment(True, None)


def judge_run(test: JsonValue, expected: dict, observation: dict) -> Judgment:
    # subprocess.run(..., timeout=..., check=True) raises on a timeout or a non-zero exit.
    timed_out = observation.get("timed_out")
    if timed_out is not False:
        return fail("driver did not exit within the timeout" if timed_out is True else "timed_out missing", test=test)
    returncode = observation.get("returncode")
    if not is_int(returncode) or not is_int(expected.get("returncode")):
        return fail("returncode missing", test=test)
    if returncode != expected["returncode"]:
        return fail("driver exited with a non-zero status", test=test, returncode=returncode)
    counted = check_counts(expected, observation)
    if counted is not None:
        return fail(counted, test=test)
    minimum = expected.get("min_elapsed_seconds")
    if minimum is not None:
        elapsed = observation.get("elapsed_seconds")
        if not is_number(elapsed) or not is_number(minimum):
            return fail("elapsed_seconds missing", test=test)
        if not elapsed >= minimum:
            return fail(f"Expected runtime >= {minimum}s", test=test, elapsed_seconds=elapsed)
    return Judgment(True, {"test": test})


def judge_cancel(test: JsonValue, expected: dict, observation: dict) -> Judgment:
    # proc.communicate(timeout=...) raises if the driver has not exited in time.
    timed_out = observation.get("timed_out")
    if timed_out is not False:
        return fail("driver did not exit within the timeout" if timed_out is True else "timed_out missing", test=test)
    counted = check_counts(expected, observation)
    if counted is not None:
        return fail(counted, test=test)
    return Judgment(True, {"test": test})


def check_counts(expected: dict, observation: dict) -> str | None:
    """Return why the counts are wrong, or None when every count matches.

    Upstream asserts stdout.count(<line>) == n on the decoded stdout; the
    adapter splits it at "\\n", so joining with "\\n" restores it exactly.
    """
    stdout = observation.get("stdout")
    if not isinstance(stdout, list) or not all(isinstance(line, str) for line in stdout):
        return "stdout missing or not valid UTF-8"
    text = "\n".join(stdout)
    # A list of [line, count] pairs, in the order upstream asserts them.
    counts = expected.get("counts")
    if not isinstance(counts, list) or not counts:
        return "bad context"
    for pair in counts:
        if not isinstance(pair, list) or len(pair) != 2:
            return "bad context"
        needle, wanted = pair
        if not isinstance(needle, str) or not needle or not is_int(wanted):
            return "bad context"
        found = text.count(needle)
        if found != wanted:
            return f"stdout contains {needle!r} {found} times, expected {wanted}"
    return None


def is_int(value: JsonValue) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fail(reason: str, **details: JsonValue) -> Judgment:
    diagnostic: dict[str, JsonValue] = {"reason": reason}
    diagnostic.update(details)
    return Judgment(False, diagnostic)
