# sqlite-db-truncate

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/sqlite-db-truncate

## The conversion in short

Upstream has one test, `test_json_data`. It loads `/app/recover.json` with `json.load`, builds the set of `(item["word"], item["value"])` tuples over every item of the loaded value, intersects it with the set of its 8 expected pairs (a literal `soln` in the test), and asserts that the intersection has more than 6 pairs. Upstream has no regression tests.

The pack has one artifact check, `recover`, which reads `/app/recover.json` with the `json` parser (at most 1 MiB). The Oracle's `plan` loads the 8 expected pairs and the threshold 7 from `hidden/expected.json` into the check's context. `judge` runs upstream's test on the parsed value: it builds the same Python set of `(word, value)` tuples and counts its intersection with the expected set. It fails closed on an absent, non-regular, too large or unparsable file, on any evidence other than the one declared file, and on a malformed context. Its work is one pass over the items of a file of at most 1 MiB, with set operations on scalars. No protocol check is needed: the deliverable is a file, and nothing has to run at grading time.

## How upstream's tests map to checks

| Upstream (`tests/test_outputs.py`, `test_json_data`) | Check and case |
|---|---|
| `json.load(open("/app/recover.json"))` succeeds | `recover` fails unless the file is present, regular, at most 1 MiB and strict JSON (`securebench.core.jsondata`); see the fidelity changes for the differences |
| `for item in data` | `recover`: the value must be a JSON array. Upstream raises on any other non-empty value (iterating a string or an object's keys gives strings, and `"a"["word"]` raises) and finds no match in an empty one |
| `item["word"]`, `item["value"]` for every item, and the tuple is hashable | `recover`: every item must be an object with both keys, and neither value may be an array or object; otherwise it fails and the diagnostic names the item's index |
| `soln_tuples & data_tuples`, `score = len(matches)` | `recover`: the same Python set intersection, so each expected pair counts once however often it is repeated, and values compare with Python's `==` (`10` equals `10.0`, `"10.0"` does not) |
| `assert score > 6` | `recover`: `score >= 7` (`threshold` in `expected.json`) |
| `soln`, the 8 expected pairs | `hidden/expected.json`, `pairs`, in upstream's order |

There is one case: the one artifact check on the one file, as upstream has one test on one file.

### Expected values

`hidden/expected.json` holds upstream's `soln` in its order, and the threshold 7. `hidden/derive.py` checks it. It decodes every cell of `trunc.db` by the SQLite file format (cell pointer array, varints, record serial types), prints the 10 rows, and fails unless the 8 pairs of upstream's `soln` are among them and `expected.json` equals `soln` with threshold 7. To redo it:

```sh
python3 -I -B task/hidden/derive.py <upstream>/environment/trunc.db \
  <upstream>/tests/test_outputs.py task/hidden/expected.json
```

The baseline's `/app/trunc.db` has the same SHA-256 as the upstream copy (`a7f00ee2...332a5b`). The page holds 10 rows: `testword00` = 1 (serial type 9, the constant 1), `testword01` = 2, then the 8 rows upstream tests, `testword02` = 10 to `testword07` = 99 as one-byte integers and `testword08` = 99.99 and `testword09` = 0.5 as big-endian doubles. Upstream tests only the 8 that its reference recovers, and so does the Oracle: listing the other two or not changes nothing.

### Differential test of the Oracle against the upstream test

The Oracle reimplements upstream's test, and the framework's strict JSON parser decodes the file differently from `json.load`, so we compared the two on 43 files (40 written files, plus an absent file, a directory and a symlink) built around the acceptance boundary and the format rules. `hidden/differential.py` writes the corpus and runs both sides; its docstring has the commands. The native side ran upstream's `test_json_data` verbatim with the baseline's Python 3.13.7 on each file as `/app/recover.json`, in the baseline image with no network and 512 MiB of memory. The SecureBench side ran the framework's `file_evidence` binding with this pack's file spec, then `plan` and `judge`. We re-ran both sides on the remediated Oracle on 2026-10-25.

| File | Upstream | SecureBench |
|---|---|---|
| the reference's 8 pairs | pass | pass |
| integer values written as `10`, `25`, ... | pass | pass |
| all 10 rows, `testword00` and `testword01` included | pass | pass |
| 7 of the 8 pairs | pass | pass |
| 7 pairs and a wrong eighth (`99.98`) | pass | pass |
| 7 pairs and unrelated rows (`{"word": null, "value": 3}`, ...) | pass | pass |
| values in exponent form (`1.000000e+01`, `9.999000e+01`, ...) | pass | pass |
| `99.990000000000000001`, which rounds to the same double as `99.99` | pass | pass |
| 8 pairs and an extra item claiming `PASSED` | pass | pass |
| a word written with `02` escapes | pass | pass |
| pretty-printed with CRLF line endings | pass | pass |
| 8 pairs and `testword02` again as the integer `10` | pass | pass |
| 8 pairs and `testword02` again with `11` | pass | pass |
| 8 pairs and `testword02` again with `null` | pass | pass |
| 8 pairs and `testword02` again with `11`, `testword03` again with `26` | pass | pass |
| every word with 384 guessed values (integers 0 to 255 and halves up to 127.5) | pass | pass |
| padded with spaces to exactly 1 MiB | pass | pass |
| 6 of the 8 pairs | fail | fail |
| 6 pairs and the next doubles above `99.99` and `0.5` | fail | fail |
| 6 distinct pairs, one repeated to 8 items | fail | fail |
| words with a trailing space | fail | fail |
| values as strings (`"10.0"`) | fail | fail |
| values `true` | fail | fail |
| one object mapping words to values | fail | fail |
| the 8 pairs wrapped in `{"rows": [...]}` | fail | fail |
| empty array; `null` | fail | fail |
| 8 pairs and an item without `value` | fail | fail |
| 8 pairs and an item that is an array | fail | fail |
| 8 pairs and an item whose value is an array, or whose word is an object | fail | fail |
| a UTF-8 byte-order mark before the answer | fail | fail |
| invalid UTF-8 in an extra word | fail | fail |
| trailing text after the array | fail | fail |
| absent; a directory | fail | fail |
| every object with a repeated `"word"` key, the last one right | pass | **fail** |
| 8 pairs and an extra row with `NaN` | pass | **fail** |
| 8 pairs and an extra row with a 21-digit integer | pass | **fail** |
| 8 pairs and an extra word with a lone surrogate `\ud800` | pass | **fail** |
| 8 pairs and an extra key nested 70 levels deep | pass | **fail** |
| padded to 1 MiB + 1 byte | pass | **fail** |
| a symlink to a correct answer | pass | **fail** |

Every remaining difference comes from how the framework reads the file (strict JSON, the size bound, no symlinks), listed below. None comes from the Oracle's counting.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte (`cmp` reports no difference).
- **Cases (equivalent).** Exactly upstream's 8 pairs and its threshold, none added and none removed. The deliverable is the recovery of one fixed file baked into the baseline.
- **Strict JSON (stricter, forced by the platform, negligible).** Artifact checks parse JSON only with the framework's strict parser; there are no task-specific parsers. It rejects what `json.load` accepts and the instructions' format does not need: repeated keys in one object (`json.load` keeps the last), `NaN` and `Infinity`, number literals that overflow a double (`1e400`, `-1e400`, which `json.load` reads as infinity), integer literals longer than 20 characters, lone surrogates, and nesting deeper than 64. A file with any of these fails here, even in a row upstream ignores. A byte-order mark and invalid UTF-8 fail both graders. No correct answer needs any of these (table above), and `json.dump` of the reference's values, including the garbage double `mutant-no-range-filter` keeps, produces none of them.
- **Answer file bound (stricter, negligible).** The artifact check reads at most 1 MiB, and upstream reads any size. The reference's answer is 426 bytes, and the 10 rows with any formatting stay under a few KiB. The bound keeps the Oracle's work on the host bounded.
- **Regular file (stricter, forced by the platform, negligible).** `/app/recover.json` must be a regular file. Upstream's `open()` follows a symlink. The artifact check reads by lookup without following links, so a symlink to a correct answer fails here. The instructions ask to "create a JSON file in /app/recover.json".
- **Pair comparison (equivalent).** The Oracle builds the same Python set of tuples as upstream from the parsed values, so the comparison is Python's `==` and hash, exactly as upstream: words must be equal strings, and numbers compare by value, so `9.999e1`, `99.990` and `99.99` are one double, while `99.99000000000001` is another (table above). The strict parser returns the same Python types as `json.load` for the values it accepts.
- **Allowed domains (stricter).** None, which is all the reference needs: it parses the file with the baseline's Python 3.13. Upstream allows the Internet, so an agent there could install SQLite recovery tools or Python packages. Here it has the image's Python 3.13 with its `sqlite3` module (SQLite 3.40.1), and no `sqlite3` command-line tool.
- **Scope (stricter, only for odd entries at the top level of `/app` and odd names one level down).** One root, `/app`, which holds the deliverable and `trunc.db`. The root excludes `*/*`, so everything below the top level of `/app` is dropped from the candidate, and an agent can keep a virtual environment, caches or links in subdirectories without failing capture. The check reads only `/app/recover.json`, so nothing a correct candidate needs is dropped. Internal symlinks are allowed, and the bounds are the largest the format allows (100,000 entries, 2 GiB). Capture still fails, where upstream passes, a correct candidate that leaves directly in `/app` an absolute symlink or one leaving `/app`, a FIFO, socket or device, an unreadable entry, more than 2 GiB of top-level files, or a name capture rejects. Capture also lists each top-level directory and checks the name of every entry in it before it applies the exclude (`securebench_utility/utility.py`, the scan loop calling `check_name`), so a correct candidate also fails if it leaves, one level down, a name capture rejects (for example `/app/work/a\b`, a name that is not valid UTF-8, or one that is too long). Those entries are excluded before they are counted, so only top-level entries count against the bounds; the scan of the level below is limited only by the walk's deadline. Upstream keeps no test files in the image (they are mounted at `/tests` only at grading time), so there is nothing to exclude. Files written outside `/app`, such as `/conftest.py`, are not captured and cannot affect the verdict.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` unchanged, after a `#!/bin/sh` line, a comment and `cd /app`. It scans `trunc.db` for `testword`, reads the byte after each word as a one-byte integer when the next byte is `0x0f`, and otherwise as a big-endian double kept only between 0.1 and 1000. It writes the 8 tested pairs.
- `null.sh`: changes nothing.
- `mutant-integers-only.sh` (threshold): the reference without its double branch. Recovers the 6 integer rows, one short of `score > 6`, so it shows the boundary: 6 fails.
- `mutant-no-range-filter.sh` (parsing of odd numbers): the reference without its range filter on doubles. It also lists `testword01` with the garbage double `8.960515547256254e-299`. The 8 tested pairs are unchanged, so it passes upstream; it shows that the strict parser reads such a number and that an extra row does not change the count.
- `mutant-string-values.sh` (pair comparison): writes values as JSON strings (`"10.0"`); 0 of 8, since a string never equals a float.
- `mutant-object-format.sh` (top-level type): writes one object mapping words to values instead of an array of objects. Upstream raises `TypeError` on `"testword02"["word"]`.
- `mutant-wrong-key.sh` (item keys): writes the word under `"name"`. Upstream raises `KeyError`.
- `attack-conftest.sh` (aimed at this task's native runner): writes an empty array to `recover.json`, and `/pytest.ini` and `/conftest.py`, whose report hook rewrites every test outcome to passed. Upstream's `pytest /tests/test_outputs.py` takes `/` as its rootdir from `/pytest.ini` and loads `/conftest.py`.
- `attack-duplicate-rows.sh` (aimed at this task's count): the integers-only mutant, then its first row repeated until the file has 8 items, to reach the threshold with 6 distinct pairs. The Oracle counts distinct pairs, as upstream's set does.
- `attack-claim-pass.sh` (claims of a verdict): the README's example pair, plus items that claim `test_json_data` `PASSED` with 8 of 8; 1 of 8.

The mutants rebuild the reference from `reference.sh` with `sed`, and exit 1 without running anything if the line they change is not there, so a mutant can never silently become the reference.

## Remediation

This pass, on 2026-10-25, brought the conversion in line with the current converter brief.

Removed:
- The "one value per word" rule in `hidden/oracle.py`: an expected word listed with more than one distinct value counted as not recovered. Upstream's test has no such rule, and it failed candidates that upstream passes because of what they write (for example the 384-guess spray, and a file listing two words with a second value each). The Oracle now counts the intersection of Python tuple sets, as upstream does.
- The key function `_key` in `hidden/oracle.py`, which kept booleans apart from numbers. Python's tuple equality makes `True == 1`; with the raw tuples the Oracle now follows Python exactly. No expected value is 0 or 1, so no verdict changes.
- The constant `PAIRS = 8` in `hidden/oracle.py`: the number of pairs now comes only from `hidden/expected.json`.
- The fidelity change "One value per word", the hidden-cases discussion and the section "Answer already public upstream". Under the current brief a public or guessable answer is outside SecureBench's scope.

Restored: nothing. Every assertion of `test_json_data` already had a check, and upstream has no regression tests.

Moved: nothing. The expected pairs and the threshold were already in `hidden/expected.json`; `oracle.py` holds only the check id, the answer path and judging logic.

Candidates:
- Deleted `attack-spray.sh`. It decodes no value and guesses 384 values per word. It does not tamper with grading, so it is out of scope, and with the rule above removed it passes SecureBench as it passes native.
- Deleted `mutant-little-endian-double.sh`. Its output is the same file as `mutant-integers-only.sh` (both doubles decode to tiny numbers that the range filter drops), so it tested nothing the other does not; the brief allows at most five mutants.
- Deleted `mutant-serial-type-byte.sh`. It reads every integer row as 15 and fails at 2 of 8, the same failing count path as `mutant-integers-only.sh` but far from the threshold, so it tested less; it made room for the mutant below within the limit of five.
- Added `mutant-no-range-filter.sh`, aimed at the strict parser on an unusual number, where the conversion reads the file differently from `json.load`.
- Kept the other four mutants and the three attacks unchanged except for comments.

Candidates that an addition failed, run once against the remediated pack with `securebench run` (1 CPU, 2048 MiB, 10240 MiB disk). No mutant passed native and failed SecureBench in the earlier `qualification.json`; the one candidate that did is `attack-spray`, now deleted:

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-spray` | 1.0 | `failed` (`oracle`) | `passed` (run `sha256:c7c44044...`) |

## Divergences from native

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** Its `recover.json` is an empty array, which fails upstream's assertion. It also writes `/pytest.ini` and `/conftest.py`. Upstream runs `pytest /tests/test_outputs.py`; pytest looks for an ini file from `/tests` upwards, finds `/pytest.ini`, takes `/` as its rootdir, and loads `/conftest.py`, whose report hook rewrites the failed `test_json_data` to passed. SecureBench captures only `/app`, and the Oracle reads the answer file itself, so the planted files have no effect and the empty array fails the check (0 of 7 required). SecureBench is right: nothing was recovered.

Every other candidate gets the same verdict from both graders: the reference and `mutant-no-range-filter` pass both; the null candidate, the four other mutants, `attack-duplicate-rows` and `attack-claim-pass` fail both. `qualification.json` (one round, 2026-10-25) has `problems: []`, and every SecureBench run is admitted, rejudged, not dirty and at pack digest `sha256:d85e9d99714526273c825a1fb6097d268f5c921e1e0a6c6399337b3e81f7babc`.

## Inventory note

Proposed note: "Remediated 2026-10-25: counts pairs as upstream's set intersection; the one-value-per-word rule and attack-spray are removed. Stricter only where the platform reads the file (strict JSON, 1 MiB, regular file)."

## Review before remediation

Reviewer: a4e3d3b19ef5d664f, 2026-10-13 (round 3)

Pack digest at review: `sha256:69c2f7c3da34c9eb778afed332d2aca59d33caf5e2e92f713e32669a71fc1a03` (`uv run securebench validate`: valid), the same in all three rounds. The pack, the candidates and `qualification.json` are unchanged since round 2 (file times 02:47 to 02:58); only `CONVERSION.md` changed.

Earlier findings:
- Round 1, Scope, names one level down: fixed in round 2 and still correct.
- Round 1, Strict JSON, overflowing literals (`1e400`, `-1e400`): fixed in round 2 and still listed.
- Round 2, false counting claim in the Scope bullet: fixed. Line 90 now says entries one level down "are excluded before they are counted, so only top-level entries count against the bounds; the scan of the level below is limited only by the walk's deadline". That matches `securebench_utility/utility.py`: `check_name`, then `excluded()` and `continue` before both entry counters, with `budget.tick()` as the deadline check. In round 2 I confirmed that `excluded(..., "sub/x")` is `True` under `*/*`.

1. Instructions. `cmp` against upstream `instruction.md`: identical.
2. Scope. The root `/app` with `*/*` excluded covers the only deliverable, `/app/recover.json`. The image holds no tests, and files planted outside `/app` are not captured. The Scope bullet now describes capture correctly.
3. Leaks. The baseline image adds only `trunc.db` to `/app`, with the same SHA-256 as upstream. Expected values are only in `hidden/`. The answer is public upstream, and lesson C58 is recorded with the hardcoding run that passes.
4. Challenges. There are no protocol checks, so there is nothing to leak.
5. Hidden case. None is possible, because the deliverable is fixed by the baseline (lesson C58). Recorded.
6. Oracle. Unchanged. Every field is checked, pairs are deduplicated, and work is bounded. The "one value per word" rule cannot be bypassed. My differential re-run in round 1 matched all 43 verdicts in the table.
7. Mutants and attacks. Unchanged. They run real code against real requirements.
8. Divergences from native. Unchanged since round 2. `qualification.json` has `problems: []`, 2 rounds, and every SecureBench run admitted, rejudged, not dirty, and at the digest above. The two framework commits recorded (`1316d96`, `b16fb37`) have identical SecureBench code trees. There are two divergences, and both explanations hold:
   - `attack-spray` passes native and fails here, under the stated stricter rule.
   - `attack-conftest` passes native only through the planted `/conftest.py`, which SecureBench never captures.
   SecureBench is right in both cases.
9. Inventory. No row yet; the coordinator adds it. The task is convertible, and no exclusion reason applies.

Upstream assertions: each step of `test_json_data` maps to a row of the table in "The conversion in short", and none is dropped. Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-25

Pack digest at review: `sha256:d85e9d99714526273c825a1fb6097d268f5c921e1e0a6c6399337b3e81f7babc` (`uv run securebench validate`: valid). It did not change between the start of the review and the final qualification.

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. One root, `/app`, with `*/*` excluded and symlinks allowed. It covers the only deliverable, `/app/recover.json`. In the baseline image `/app` holds only `trunc.db`, with no symlinks, and the image has no `/tests` and no `/.securebench`. Upstream mounts its tests at `/tests` only at grading time, and SecureBench runs no test runner, so there are no test files or convention-loaded files to exclude. The Scope bullet describes capture accurately.
3. Leaks. There is no `public/` and no `evaluation/`. The expected pairs are only in `hidden/` (`expected.json`, plus `differential.py`, which only documents the differential test). The baseline's `/app/trunc.db` is the task input and has the same SHA-256 as upstream (`a7f00ee2...332a5b`). There are no allowed domains, so no limitation section is needed.
4. Challenges. There are no protocol checks, so there is nothing to leak.
5. Cases. There is one artifact check on the one file, with upstream's 8 pairs and its threshold (`> 6`, written as `>= 7`). Nothing was added, and the seed is not used. I re-ran `hidden/derive.py` on the upstream `trunc.db` and test file. It decodes 10 rows and confirms that `expected.json` equals upstream's `soln` with threshold 7.
6. Oracle. `oracle.py` holds only the check id, the answer path and judging logic, and the expected values come from `expected.json`. It reproduces `test_json_data`:
   - The file must be an array.
   - Every item must be an object with `word` and `value`, and neither may be a list or object (upstream raises TypeError or KeyError there).
   - Matching is the intersection of Python tuple sets, so repeated items count once, `10 == 10.0`, and extra keys are ignored.
   - The work is bounded by the 1 MiB artifact bound.

   The framework's strict parser is `json.loads`, with Python's `float()` and `int()` plus extra rejections, so the values it accepts compare as they do in upstream's test. I re-ran `hidden/differential.py` on both sides: native in the baseline image with no network and 512 MiB, and SecureBench through `uv run`. All 43 verdicts match the table. The only 7 differences (repeated key, NaN, 21-digit integer, lone surrogate, nesting deeper than 64, more than 1 MiB, symlink) are all listed as stricter fidelity changes. Upstream has no regression tests.
7. Candidates. `reference.sh` without its first 3 lines is byte-identical to upstream `solution/solve.sh`. I ran every candidate in the baseline container and checked its `recover.json`:
   - integers-only gives 6 of 8.
   - no-range-filter gives the 8 pairs plus `testword01` with `8.960515547256254e-299`, a finite double that the strict parser accepts.
   - string-values, object-format and wrong-key produce the outputs described.
   - duplicate-rows has 6 distinct pairs in 8 items.
   - claim-pass has 1 pair plus claim items.

   Every mutant runs the real reference with one `sed` change, and the `grep` guard stops it from silently becoming the reference. The mutants are aimed at the threshold, the strict parser on an unusual number, value types, the top-level type and the item keys. There are 5 mutants and 3 attacks. The attacks target the native pytest rootdir and conftest, distinct counting, and verdict claims.
8. Divergences. In `qualification.json`, `problems` is `[]`. All 10 candidates were run, and every SecureBench run is admitted, rejudged, not dirty and at the digest above. The runs come from four framework commits (`ba54c26`, `8066b81`, `f8227e8`, `ef0a0d3`), and all four have the same `securebench/` and `securebench_utility/` trees. The one divergence is `attack-conftest`: native 1.0 through the planted `/pytest.ini` and `/conftest.py`, SecureBench `failed` on the empty array. The explanation holds, and SecureBench is right. Every other verdict agrees with native.
9. Inventory. `conversions/inventory.tsv` line 29 still describes the removed one-value-per-word rule, `attack-spray` and lesson C58. The proposed note in "Inventory note" is accurate, and the coordinator should apply it. The task is convertible, and no exclusion reason applies.

Upstream assertions: `json.load` of the file, iterating the items, `item["word"]` and `item["value"]` with hashable tuples, the set intersection, and `assert score > 6` each map to a row of the table in "How upstream's tests map to checks". None is dropped, and every fidelity change has a label and a reason.

Findings:
- `task/task.toml`, the scope comment: it cites "lesson A14" and names other conversions (gcode-to-text, vulnerable-secret). Neither can be resolved by a reader of this pack. It is a comment only and does not affect grading, so it does not block. Fix it in the next pack change.
- `conversions/inventory.tsv` line 29: the note is stale, as described in point 9. The coordinator updates it, using the proposed note.

Verdict: approved
