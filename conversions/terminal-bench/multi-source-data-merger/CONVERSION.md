# multi-source-data-merger

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/multi-source-data-merger

## How the pack grades

The baseline holds three small user tables in `/data`: `source_a/users.json` (users 101 and 102), `source_b/users.csv` (101 and 103) and `source_c/users.parquet` (101 and 104), each with its own column names. The agent must merge them by user id with priority `source_a > source_b > source_c`, write the result to `/app/merged_users.parquet`, and write a conflict report to `/app/conflicts.json`.

Upstream's verifier (`tests/test.sh`) installs Python 3.13, pandas 2.3.3, pyarrow 22.0.0 and pytest from the network and runs the three test functions of `tests/test_outputs.py` once on the agent's two files. Evaluation environments have no network, and the deliverables are a Parquet file and a JSON file, which no registry parser reads. So the pack has two protocol checks, one case each, with the empty challenge `{}`:

- **`merged`** runs `evaluation/adapter.py merged`, which reads `/app/merged_users.parquet` with `pandas.read_parquet`, as upstream's test does, and reports the column names, the row count and, for each of the first 64 rows, the values in the columns `user_id`, `name`, `email` and `created_date`. pandas reads a Parquet list column as one numpy array per cell; for `name`, `email` and `created_date` the adapter reports the value inside up to 16 nested one-element arrays, with the number of such arrays (`wrapping`), and an array of any other size, or nested deeper, as an array.
- **`conflicts`** runs `evaluation/adapter.py conflicts`, which reads `/app/conflicts.json` as UTF-8 text with Python's `json` module, as upstream's test does, and reports whether the report is an object, its `total_conflicts`, whether `conflicts` is a list and its length, and for each of the first 128 entries whether it is an object, its `user_id`, `field` and `selected`, whether `values` is an object, and `values.source_a`.

The adapter runs on the baseline's own Python 3.11, pandas 2.2.3 and pyarrow 17.0.0 in `/usr/local`, outside the scope. Every value is reported as a cell: its kind after decoding (`absent` for a missing key, `null`, `bool`, `int`, `float`, `decimal`, `str`, `object`, `list`, `other`), its text (`str()` for an integer or decimal, `repr()` for a float, at most 256 bytes) and whether that text is exactly the value. The adapter holds no expected value. A missing or undecodable deliverable is reported as `unable`, which fails the case.

The Oracle (`hidden/oracle.py`) holds only judging logic. Every expected value is a literal of `tests/test_outputs.py`, kept in `hidden/cases.json` with its case's challenge. The Oracle compares cells with the semantics of upstream's Python `==`: a string equals only an equal string, and a number equals an integer when it is that `int`, a `float` or `Decimal` of the same value, or (for 0 and 1) a `bool`. A string inside nested one-element arrays equals an equal string, as numpy's elementwise `==` and `assert` on a one-element array make it upstream; an empty or longer array never does, because `assert` on it raises `ValueError`. The adapter unwraps at most 16 levels (see "Bounds" under "Fidelity changes").

## How upstream's tests map to checks

Upstream has no regression tests; all three test functions check what the task asks for.

| Upstream (`tests/test_outputs.py`) | Check | SecureBench |
|---|---|---|
| line 13: `os.path.exists("/app/merged_users.parquet")` | `merged`, case 0 | the adapter reports `unable` (`missing`) when it does not exist |
| line 14: `os.path.exists("/app/conflicts.json")` | `conflicts`, case 0 | the adapter reports `unable` (`missing`) |
| line 19: `pd.read_parquet` succeeds | `merged`, case 0 | the adapter's own `pd.read_parquet`; an exception gives `unable` (`unreadable`) |
| line 22: `len(df) == 4` | `merged`, case 0 | `row_count` equals `row_count` in `hidden/cases.json` (4) |
| line 23: `set(df["user_id"]) == {101, 102, 103, 104}` | `merged`, case 0 | column `user_id` appears exactly once (a missing column raises `KeyError`, a repeated one makes `df["user_id"]` a frame whose set is its labels); every `user_id` cell equals one of `user_ids` in `hidden/cases.json` by Python `==`, and each of them is matched |
| line 26: `df[df["user_id"] == 101].iloc[0]` | `merged`, case 0 | the row whose `user_id` equals 101 (exactly one, given line 23) |
| lines 27 to 29: user 101's `name == "John Doe"`, `email == "john@a.com"`, `created_date == "2024-01-15"` | `merged`, case 0 | each column appears exactly once (a repeated column makes `assert series == text` raise) and the cell is the equal string, from `hidden/cases.json`, also inside up to 16 nested one-element arrays (a Parquet list cell), whose nesting is not judged |
| line 32: `df[df["user_id"] == 104].iloc[0]` | `merged`, case 0 | the row whose `user_id` equals 104 |
| lines 33 to 35: user 104's `name == "Alice Brown"`, `email == "alice@c.com"`, `created_date == "2024-04-01"` | `merged`, case 0 | equal strings, from `hidden/cases.json` |
| lines 40 and 41: `json.load` succeeds | `conflicts`, case 0 | the adapter's `json.loads` of the file decoded as UTF-8; failure gives `unable` (`unreadable`) |
| line 44: `report["total_conflicts"] >= 1` | `conflicts`, case 0 | the report is an object with `total_conflicts`; together with line 45, the number of entries is at least `min_total_conflicts` in `hidden/cases.json` (1) |
| line 45: `len(report["conflicts"]) == report["total_conflicts"]` | `conflicts`, case 0 | `conflicts` is a list and `total_conflicts` equals its length by Python `==` (so `3.0`, and `true` for one entry, pass as upstream) |
| line 48: `c["user_id"] == 101` for every entry | `conflicts`, case 0 | every entry is an object with a `user_id` key (a non-object entry raises `TypeError`, a missing key `KeyError`) |
| line 49: at least one entry for user 101 | `conflicts`, case 0 | at least one entry whose `user_id` equals `user_id` in `hidden/cases.json` (101) by Python `==` |
| line 52: `c["field"] == "email"` for every user-101 entry | `conflicts`, case 0 | every user-101 entry has a `field` key; the entries whose `field` is the string `field` in `hidden/cases.json` (`email`) are selected |
| lines 53 to 56: if there is one, the first such entry has `values["source_a"] == "john@a.com"` and `selected == "john@a.com"` | `conflicts`, case 0 | only if there is one: the first has `values` as an object, and `source_a` and `selected` the equal strings from `hidden/cases.json` |

## Expected values

`hidden/cases.json` holds one case per check. Each value in it is a literal of `tests/test_outputs.py`: the row count 4 (line 22), the ids 101 to 104 (line 23), users 101 and 104's name, email and created_date (lines 26 to 35), the minimum count 1 (line 44), user 101 (line 48), the field `email` (line 52), and `john@a.com` for `source_a` and `selected` (lines 55 and 56). Nothing is derived. The upstream reference's outputs satisfy every one (the reference passes both graders).

## Differential test of the checks against upstream's tests

The adapter reads with pandas 2.2.3 and pyarrow 17.0.0 on Python 3.11, where upstream reads with pandas 2.3.3 and pyarrow 22.0.0 on Python 3.13, and the Oracle reimplements upstream's comparisons. `hidden/differential.py` compares the two on 89 pairs of deliverables, each the reference's output with one change, written with the baseline's pyarrow (the only Parquet writer a candidate has here; allowed domains are empty). The native side runs upstream's three test functions on upstream's verifier stack, in a container of the baseline that ran the install half of `tests/test.sh`. The SecureBench side runs `evaluation/adapter.py` in the baseline from `/app`, then `hidden/oracle.py`. Its docstring gives the three commands. We reran it on the remediated pack on 2026-10-25, after the review finding on list cells: the two sides agree on all 89.

| Change to the reference's output | Upstream | SecureBench |
|---|---|---|
| none; `user_id` as int32, int8, uint64, nullable Int64, float64, decimal(5,0) or decimal(7,2); `created_date` as large_string; `name` categorical; strings as pandas `string` dtype; columns reordered with an extra `_source` column; no status column; rows shuffled; a stored non-range index; a directory dataset partitioned by status; no compression, gzip, zstd or brotli; Parquet 1.0 with data page v2; user 102's name `Jane`; user 103's email null; user 103's created_date `2024/03/01`; `name`, `email` or `created_date` as `list<string>` with one element per cell, all three at once, or `name` as `list<list<string>>`; user 102's name a two-element list | pass | pass |
| report indented; `total_conflicts` 3.0; `total_conflicts` `true` with only the email conflict; entries' `user_id` 101.0; only the email conflict; no email conflict; the email conflict listed twice; a second, wrong email conflict after the first; extra conflicts for user 102, on status (also with `NaN`), on `_source`, or a status conflict twice; an extra entry `{"user_id": 102}` without `field`; the email conflict without `source_c`; created_date values with ` 00:00:00`; the name conflict's `selected` wrong; field names capitalized; a repeated `selected` key whose last value is right; extra keys in each entry; extra top-level keys claiming a pass | pass | pass |
| 3 rows; 5 rows (101 twice, or an extra user 105); `user_id` as strings, as the index, or float64 with a NaN; a repeated `name` column; `created_date` as date32 or timestamp; user 101's created_date `2024-1-15`; user 101's name with a trailing space; user 104's email uppercase; user 101's name in a `list<string>` column as an empty list, a two-element list, a one-element list of a wrong name, or a one-element list of a two-element list; an empty Parquet file | fail | fail |
| `total_conflicts` 4 with 3 listed, `"3"`, `Infinity`, or 0 with an empty list; `{}`; a top-level list; `conflicts` as an object or a string; an entry without `field`; an entry without `user_id`; an entry that is a string; no entry for user 101 (all 102, or entries' `user_id` `"101"`); a wrong email conflict listed first; the email conflict's `selected` or `source_a` wrong; its `selected` missing; its `values` a string; a byte-order mark; Latin-1 bytes | fail | fail |

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** Upstream runs its tests once on the agent's two files; the pack has one case per file with the empty challenge `{}`.
- **Reader versions (equivalent on the differential above).** Upstream reads with pandas 2.3.3, pyarrow 22.0.0 and Python 3.13, installed at grading time. Here the adapter reads with the baseline's pandas 2.2.3, pyarrow 17.0.0 and Python 3.11, outside the scope. In SecureBench a candidate can write Parquet only with the baseline's pyarrow 17 (or by hand), and every file that pyarrow 17 wrote in the differential gets the same verdict on both stacks.
- **Comparisons (equivalent).** The Oracle reproduces upstream's Python `==` on decoded values: `user_id` may be any integer type, a float or a decimal of the same value; `total_conflicts` may be 3.0 (or `true` for one entry); an entry's `user_id` may be 101.0; and a value equal as a string passes whatever its Parquet string type (`string`, `large_string`, dictionary, pandas `string`), also inside nested one-element lists, which pandas reads as numpy arrays and upstream's `assert array == text` accepts. We confirmed that rule on upstream's stack (numpy 2.5.4): a one-element array of an equal string and a one-element array of such an array pass, an empty or two-element array raises `ValueError`. The adapter decodes the report as UTF-8 and parses it with Python's `json`, as `open(...)` with the image's `LANG=C.UTF-8` and `json.load` do, so `NaN`, `Infinity` and repeated keys behave as upstream.
- **Bounds (stricter, negligible).** The adapter reports at most 256 column names, 64 rows and 128 conflict entries, each value at most 256 bytes of text, and unwraps at most 16 nested one-element arrays around `name`, `email` and `created_date`; the Oracle fails anything longer, larger or deeper, which no correct deliverable comes near (5 columns, 4 rows, 3 conflicts, values under 20 bytes, plain strings). Upstream passes a correct string nested 17 or more lists deep (the review of this remediation confirmed depth 17 on upstream's stack); here it fails. `conflicts.json` is read only up to 16 MiB. Upstream has no bounds. These keep the Oracle's work bounded.
- **Python startup (equivalent for correct candidates, stricter for one attack).** The image sets `PYTHONPATH=/app`, so upstream's pytest imports any module a candidate leaves in `/app`, such as `/app/pandas.py`, before the real one. The adapter runs with `-I`, which ignores `PYTHONPATH` and the working directory, so nothing in `/app` runs during evaluation. `attack-shadow-pandas` passes upstream this way and fails here.
- **Adapter exit (equivalent).** pyarrow 17 sometimes aborts at interpreter shutdown with "terminate called without an active exception" (exit status 134) after the response has been written. We saw it in 1 of 30 local runs at 0.3 CPU and in the first SecureBench run of the reference. The adapter flushes its response and ends with `os._exit(0)`, after which 60 local runs and every SecureBench run were clean. The response is complete before the call, so this changes no observation.
- **Allowed domains (stricter).** None, which is all the reference needs: pandas and pyarrow are in the image. Upstream allows the whole Internet, so an agent there can install other libraries (polars, duckdb) to do the merge. Here it has the image's Python, pandas 2.2.3 and pyarrow 17.0.0.
- **Scope (stricter, only for entries no correct solution needs).** One root, `/app`, which holds both deliverables. The baseline's `/app` is empty. Nothing is excluded, so a deliverable written as a directory of Parquet part files (which `pd.read_parquet` reads, upstream and here) is captured whole. The bounds are the format's maxima (100,000 entries, 2 GiB), and internal symlinks are allowed. Capture still fails, where upstream passes, a candidate that leaves in `/app` a symlink leaving `/app` (a virtual environment's `bin/python`, for example), a special file, or more than the bounds; nothing in this task needs any of these. Upstream keeps its tests in `/tests`, outside the scope and absent from the image, so no test file can be rewritten, and files outside `/app`, such as `/conftest.py`, never reach the Evaluation.

## Divergences from native

From `qualification.json` (`problems: []`, pack `sha256:b36034e2...07200fde3f`, every SecureBench run admitted, clean and rejudged). The reference, `mutant-float-ids` and `mutant-listed-fields` pass both graders. The null candidate and the mutants `mutant-datetime-dates`, `mutant-string-ids` and `mutant-total-users` fail both. No mutant diverges. The two attacks get native 1.0 and SecureBench `failed`:

- **`attack-shadow-pandas`: native 1.0, SecureBench `failed` (`case_error`).** Its Parquet file is empty. Upstream's pytest inherits the image's `PYTHONPATH=/app`, imports the candidate's `/app/pandas.py`, and its fake `read_parquet` returns a correct table. The adapter runs with `-I`, reads the file with the real pandas, and pyarrow reports a 0-byte file. SecureBench is right: `/app/merged_users.parquet` is not a Parquet file.
- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** Its deliverables are an empty Parquet file and `{}`, which fail upstream's tests; the native 1.0 comes only from the planted `/pytest.ini` and `/conftest.py` rewriting every outcome to passed. SecureBench captures only `/app`, and the Oracle reads the deliverables' values itself. SecureBench is right.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with its `#!/bin/bash` first line replaced by `#!/bin/sh`, a comment and `cd /app`. The script uses nothing specific to bash (one quoted heredoc). No drift repair was needed.
- `null.sh`: changes nothing.
- Mutants. Each rebuilds the reference from `reference.sh` with one `sed` change and exits 1 without running anything unless exactly the intended line changed, so a mutant can never silently become the reference. Each aims at a place where the check is least like upstream's assertion: a value the adapter decodes and the Oracle compares with its own reimplementation of Python `==`.
  - `mutant-float-ids.sh` (`user_id` compared by Python `==`): `user_id` stored as float64. Upstream's `set(...) == {101, ...}` accepts 101.0, so both graders should pass it.
  - `mutant-string-ids.sh` (the same comparison, failing side): every source's `user_id` cast to `str` before combining, so the dataset stores ids as strings.
  - `mutant-datetime-dates.sh` (`created_date` decoded by the adapter): `created_date` converted with `pd.to_datetime` before saving, so it is a timestamp, not a string.
  - `mutant-total-users.sh` (`total_conflicts` compared with the list's length): counts users with conflicts instead of conflicts.
  - `mutant-listed-fields.sh` (`name`, `email` and `created_date` unwrapped from one-element arrays by the adapter): `groupby('user_id').agg(lambda s: s.head(1).tolist())` in place of `.first()`, so every merged field except `user_id` is stored as `list<string>` with one element per cell. Upstream's `assert array == text` accepts these, so both graders should pass it.
- Attacks.
  - `attack-shadow-pandas.sh`, aimed at this task: leaves an empty `/app/merged_users.parquet` and a fake `/app/pandas.py` whose `read_parquet` returns a correct table whatever the file; the conflict report is the reference's. It targets the image's `PYTHONPATH=/app`, through which upstream's pytest imports the fake module.
  - `attack-conftest.sh`: writes an empty Parquet file and `{}` as the report, and plants `/pytest.ini` and `/conftest.py`, whose report hook rewrites every test outcome to passed.

## Remediation

The conversion was made under an earlier converter brief that asked for checks beyond upstream's assertions. This pass makes the pack check exactly what `tests/test_outputs.py` checks.

Removed from `hidden/oracle.py` (each could fail a candidate that upstream passes because of what it computes):

- the merged values of users 102 and 103 (upstream checks only 101 and 104);
- the rule that every `user_id` cell is an integer (upstream's `set(...) == {...}` accepts floats and decimals of the same value);
- the rules that every conflict entry is about user 101, that its `field` is one of `name`, `email`, `created_date` or `status`, and that no field is listed twice;
- the required `name`, `email` and `created_date` conflicts with all three source values and the selected value (upstream checks only `source_a` and `selected` of the first email conflict, and only if there is one).

Removed from the pack with them: `hidden/expected.json` and `hidden/derive.py`, which derived the values of users 102 and 103 and of the three conflicts from the reference; the adapter's `values.source_b` and `values.source_c`, and their schema entries, which only the removed conflict checks read.

Restored: no upstream assertion had been dropped. Three of upstream's semantics that the earlier checks missed are now reproduced: a `user_id` stored as a Parquet decimal compares by value (the adapter now reports the kind `decimal`, and the schemas allow it), entries for other users need no `field`; and, after the review of this remediation, a `name`, `email` or `created_date` stored as a Parquet list with one element per cell compares as upstream's numpy `==` does (the adapter now reports `wrapping`, and `merged.schema.json` has it).

Moved: every expected value is now in `hidden/cases.json`, each a literal of upstream's test, with its case's challenge; `oracle.py` holds only judging logic. The row count, the id set, the user-101 and user-104 values, the minimum conflict count, the user, field and values of the email conflict were in `hidden/expected.json` or in `oracle.py` before.

`hidden/differential.py` is kept and rerun on the remediated pack. It gained 12 cases for the restored semantics, and 10 more for list cells after the review (decimal ids with a scale, float ids with a NaN, `total_conflicts` `true`, entries without `field` or `user_id`, a non-object entry, no entry for user 101, the first or second of two email conflicts wrong, the email conflict's `values` a string or its `selected` missing, `conflicts` a string). Two report cases were renamed (`conflicts-user_id-float`, `conflicts-user_id-string`): the old `user_id-string` report case had the same name as a Parquet case and overwrote it, so the Parquet string-id case had not run before.

Candidates deleted:

- `attack-upstream-values.sh`: it wrote upstream's literals without reading `/data`. That is a public-answer cheat, not tampering with grading, and outside SecureBench's scope; it now passes both graders.
- `mutant-unmapped-email-address.sh`, `mutant-missing-as-conflict.sh` and `mutant-bookkeeping-conflicts.sh`: each existed to show a removed addition (users 102 and 103, conflicts only for user 101, the allowed field names). All three passed natively; with the additions removed they now pass SecureBench too (table below).
- `mutant-reversed-priority.sh` and `mutant-drop-duplicated-users.sh`: to keep at most five mutants. They tested plain string and row-count comparisons, which are closest to upstream's assertions; the kept mutants cover the same requirements at the decoded-value comparisons.
- `mutant-selected-lowest.sh`, after the review of this remediation: replaced by `mutant-listed-fields.sh` to stay at five mutants. It tested a plain JSON string comparison, the check closest to upstream's assertion.

Candidates added: `mutant-float-ids.sh`, aimed at the restored Python `==` on `user_id`, where the Oracle's comparison is least like upstream's (a reimplemented `set` equality over decoded cells); and, after the review, `mutant-listed-fields.sh`, aimed at the adapter's unwrapping of list cells.

Mutants that SecureBench failed only because of an addition, run once against the remediated pack with `securebench run`:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-bookkeeping-conflicts` | 1.0 | `failed` (`oracle`) | `passed` (run `sha256:b58504b1...`) |
| `mutant-missing-as-conflict` | 1.0 | `failed` (`oracle`) | `passed` (run `sha256:19e7fb6e...`) |
| `mutant-unmapped-email-address` | 1.0 | `failed` (`oracle`) | `passed` (run `sha256:073cd8fb...`) |

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated: checks exactly upstream's assertions (users 101 and 104, the id set, the first email conflict if any); the additions for users 102 and 103, integer user_id and the full conflict report are removed, and the literals are in hidden/cases.json. attack-shadow-pandas (PYTHONPATH=/app) and attack-conftest pass natively by hijacking upstream's test run."

## Review before remediation

Reviewer: a71b336f11fcd6793, 2026-10-13 (round 2)

Pack digest at review: `sha256:45fca62271e67719ad4a4727c25b6531afabffc4c26d918acde828eb3cf3a632` (`uv run securebench validate`, unchanged from the start of round 2 to the verdict). All 14 SecureBench runs in `qualification.json` record this digest, all are admitted, clean (`dirty: false`) and rejudged, and `problems` is empty.

Round 1 findings:
- Extra conflict entries for user 101 under any field name passed: fixed. `hidden/oracle.py` now rejects any entry whose `field` is not the string `name`, `email`, `created_date` or `status`, and any field listed twice. `mutant-bookkeeping-conflicts.sh` (the guarded `sed` mutant from round 1) is added and gets SecureBench `failed` (`oracle`) with native 1.0. I re-ran my own tests through `adapter.py` in the pinned baseline and the new Oracle. The bookkeeping mutant and a junk extra entry now fail. Three independently written correct solutions still pass: one with a status conflict carrying the raw `"active"`/`true`/`true` values, one without a status conflict, and one with `int32` ids. The differential, the docstring and the "Conflict report" bullet describe the new rule.
- The "Scope." bullet had no label: fixed ("stricter, only for entries no correct solution needs").

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference. `reference.sh` differs from upstream `solution/solve.sh` only in the shebang, a comment and `cd /app`. Correct.
2. Scope. One root, `/app`, empty in the baseline, holding both deliverables, nothing excluded, internal symlinks allowed, maximum bounds. Upstream's tests are in `/tests`, outside the scope and absent from the image (C49). The adapter runs the baseline's `/usr/local/bin/python3 -I`, so nothing in `/app` is imported. No baseline symlink under `/app` (A16). Independently written correct solutions pass. Correct.
3. Leaked expected values. Expected values are only in `hidden/expected.json`. In the pinned image, `/app` is empty, there is no `/tests` or `/solution`, and no file outside the `/data` inputs holds the expected strings. The answer is derivable from public inputs (C58), which is recorded. Correct.
4. Challenges. Both checks send `{}`. Correct.
5. Hidden cases. None can help: the deliverables are output files fixed by three public inputs and a public solution (C58), as "Answer already public upstream" records, with the passing probe. Correct.
6. Oracle (C52 to C54). Schemas have no optional properties, so every indexed field exists. Rows are deduplicated by `user_id` and conflicts by field. Work is bounded by the schemas and the 16 MiB read, and `column_count` and `conflict_count` catch truncation. Comparisons reproduce Python `==`. Every required field is checked. Correct.
7. Mutants and attacks. Nine guarded mutants built from the reference with `sed`, each aimed at one requirement and running real code, and three task-specific attacks (upstream values, a shadow `pandas.py` through `PYTHONPATH=/app`, `conftest.py`). Every one gets SecureBench `failed`, never `invalid`. Correct.
8. Divergences from native. Six candidates get native 1.0 and SecureBench `failed`: `attack-upstream-values`, `attack-shadow-pandas`, `attack-conftest`, `mutant-unmapped-email-address`, `mutant-missing-as-conflict` and `mutant-bookkeeping-conflicts`. I checked each explanation against `tests/test_outputs.py` and the candidate. Upstream checks only users 101 and 104 and the conditional email conflict. It imports `/app/pandas.py` through `PYTHONPATH`, and it trusts a pytest report a planted `/conftest.py` rewrites. `mutant-missing-as-conflict` does list 12 conflicts (3 for each of 101 to 104). Each explanation holds, and in each case SecureBench is right by the instructions. The reference passes both graders. The null candidate and the other six mutants fail both. Correct.
9. Inventory. No row yet; the coordinator adds it. The task is 31st in `campaign.py order terminal-bench`, the last of the campaign's extension. The row should be `converted`. Correct.

Upstream assertions. Every assertion of `tests/test_outputs.py` (lines 13, 14, 19, 22, 23, 26 to 29, 32 to 35, 40, 41, 44, 45, 48, 49, 52 to 56) maps to a check in the table under "The conversion in short", confirmed against `adapter.py` and `oracle.py`. Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (session bdda55d6), 2026-10-26 (round 3)

Pack digest at review: `sha256:b36034e282e0249fa90880e4fac2208225c9723dffbfef8aa3adab07200fde3f` (`uv run securebench validate`). All nine SecureBench runs in `qualification.json` record this digest, are admitted, clean (`dirty: false`) and rejudged, and `problems` is empty.

Earlier findings:
- Round 1 (a Parquet list cell in `name`, `email` or `created_date` passed upstream and failed here, unrecorded): fixed in round 2. The adapter unwraps nested one-element 1-D arrays, and the Oracle compares the innermost value. On 15 variants I wrote, run through upstream's own stack (Python 3.13, pandas 2.3.3, pyarrow 22.0.0, numpy 2.5.4) and through the adapter plus Oracle, the two agree on every variant up to depth 16 (finding 1 of round 2 covered depth 17).
- Round 2, finding 1 (the 16-level unwrapping bound was unrecorded): fixed. The "Bounds (stricter, negligible)" bullet now lists it, with depth 17 passing upstream and failing here. The `adapter.py` comment, the Oracle's docstring and comment, and the mapping table now say "up to 16". Line 11 no longer claims "any nesting".
- Round 2, finding 2 (no mutant reached the unwrapping): fixed. `mutant-listed-fields.sh` replaces `.first()` with `.agg(lambda s: s.head(1).tolist())`, a guarded one-line `sed` change. I ran it in the pinned baseline. It stores `name`, `email` and `created_date` as `list<string>`, and the adapter reports each with `wrapping: 1`, so it really goes through the unwrapping. It passes both graders (native 1.0, run fresh, not cached). `mutant-selected-lowest.sh` was dropped to stay at five, and "Remediation" records why.

1. Instructions. Unchanged; `cmp` against upstream `instruction.md`: identical. Correct.
2. Scope. `task.toml` unchanged: one root, `/app`, empty in the pinned image with no symlinks, nothing excluded. There is no `/tests` or `/solution` in the image. The adapter runs `/usr/local/bin/python3 -I -B`, so neither `PYTHONPATH=/app` nor the working directory reaches it. Correct.
3. Expected values. Only in `hidden/cases.json`, unchanged. `evaluation/` and the image hold none, apart from the public `/data` inputs. Allowed domains are empty. Correct.
4. Challenges. Both checks send `{}`. Correct.
5. Cases. One case per deliverable for upstream's single run; none added; seed unused. Correct.
6. Oracle. Judging logic only. The changes since round 2 are comments and the docstring. `wrapping` is bounded (0 to 16) and required in `merged.schema.json`. Every assertion of `tests/test_outputs.py` (lines 13, 14, 19, 22, 23, 26 to 29, 32 to 35, 40, 41, 44, 45, 48, 49, 52 to 56) maps to a check as the table says, and every fidelity change carries a label and a reason. Correct.
7. Candidates. The reference is upstream's solution plus the shebang, a comment and `cd /app`. Five guarded `sed` mutants run real code, each aimed at a decoded or converted value: `user_id` as float and as string, `created_date` as timestamp, `total_conflicts`, and list cells. `mutant-float-ids` and `mutant-listed-fields` pass both graders. `mutant-datetime-dates`, `mutant-string-ids` and `mutant-total-users` fail both. Both attacks get SecureBench `failed`. Correct.
8. Divergences. Only the two attacks diverge (native 1.0, SecureBench `failed`). The explanations hold. `attack-shadow-pandas` passes natively only through `PYTHONPATH=/app` importing its `/app/pandas.py`; here the real pandas rejects the 0-byte file (`case_error`). `attack-conftest` passes natively only through the planted `/pytest.ini` and `/conftest.py`, which lie outside the scope; here the Oracle fails its empty deliverables (`oracle`). SecureBench is right in both. Correct.
9. Inventory. `converted` is right, and no exclusion reason applies. The note in `conversions/inventory.tsv` still describes the pre-remediation additions; the coordinator should replace it with the proposed note under "Inventory note".

Findings:
- None.

Verdict: approved
