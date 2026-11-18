"""Oracle for headless-terminal.

One case runs upstream's seven tests in order in one process, as pytest does.
`plan` sends each test's source, from hidden/tests/, in the challenge. For
each test the driver records the values upstream's assertions compare, or
the exception the test raised. A test passes when it raised nothing and
every recorded value matches the expectation in hidden/cases.json, compared
the way upstream's assertion compares it; the case passes when all seven do.
"""

from securebench.core.evidence import CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

SHOWN_CHARACTERS = 200


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    cases = tuple(Case(_challenge(resources, case["challenge"]), case["expected"]) for case in data["cases"])
    return Plan(artifact_contexts={}, cases={"tests": cases})


def _challenge(resources, listed):
    # The driver holds no test bodies: each test travels in the challenge as
    # its source from hidden/tests/, in the order cases.json lists the tests.
    tests = [
        {"name": name, "source": resources.read("tests/" + name + ".py").decode("utf-8")}
        for name in listed["tests"]
    ]
    return {"tests": tests}


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if check_id != "tests" or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observed = evidence.outcome.value
    if not isinstance(observed, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    failures = {}
    for name, expected in context.items():
        reason = _judge_test(expected, observed.get(name))
        if reason is not None:
            failures[name] = reason
    if failures:
        return Judgment(False, {"failed_tests": failures})
    return Judgment(True, None)


def _judge_test(expected, record):
    if not isinstance(record, dict):
        return "no record"
    if "error" in record:
        return "raised " + _shown(record["error"])
    if "exists" in expected:
        # assert path.exists() / assert not path.exists()
        exists = record.get("exists")
        if not isinstance(exists, bool):
            return "path.exists() not recorded"
        if exists is not expected["exists"]:
            return f"path.exists() is {exists}"
        if not exists:
            return None
    if "status_code" in expected:
        # assert response.status_code == 200
        status = record.get("status_code")
        if isinstance(status, bool) or not isinstance(status, int):
            return "status code not recorded"
        if status != expected["status_code"]:
            return f"status code {status}"
    if "text" in expected:
        # assert <text>.strip() == <the expected text>
        text = record.get("text")
        if not isinstance(text, str):
            return "text not recorded"
        if text.strip() != expected["text"]:
            return "stripped text differs: " + _shown(text)
    return None


def _shown(value):
    if not isinstance(value, str):
        return "(not a string)"
    return repr(value[:SHOWN_CHARACTERS])
