# db-wal-recovery

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/db-wal-recovery

## How the pack grades

The agent must write `/app/recovered.json`. Upstream's verifier (`tests/test_outputs.py`) reads only that file, so the pack has one artifact check, `recovered-json`. It reads the file with the strict JSON parser, and the Oracle never runs anything in an Evaluation environment.

`hidden/oracle.py` transliterates the seven upstream tests one function each, in upstream order. Upstream rewards the task only when all seven pass, so the first failing test decides the verdict:

| Upstream test | Oracle |
|---|---|
| `test_recovered_json_exists` | file status must be `present` (absent, not regular, too large or unparsable all fail; upstream's `json.load` in every later test fails the same way) |
| `test_recovered_json_is_valid` | `_json_is_valid`: a list, non-empty |
| `test_recovered_data_structure` | `_data_structure`: every item a dict holding `id`, `name`, `value`; `isinstance` int, str, int |
| `test_recovered_data_sorted` | `_data_sorted`: `ids == sorted(ids)` |
| `test_recovered_data_completeness` | `_data_completeness`: 11 records, ids `[1..11]`, values of ids 1 and 2, names of ids 3 to 11 |
| `test_no_duplicate_ids` | `_no_duplicate_ids` |
| `test_wal_was_decrypted` | `_wal_was_decrypted`: more than 5 records; the value of id 1 and the name of id 6, each checked only when that id is present |

The Oracle uses Python's own semantics, as upstream's tests do: a JSON `true` passes `isinstance(..., int)` and equals `1`, and extra fields in a record are allowed. Every literal the tests compare with (11, the id list, 150 and 250, the nine names, the threshold 5) is in `hidden/expected.json`, copied from `tests/test_outputs.py`. Upstream checks only those fields: the names of ids 1 and 2 and the values of ids 3 to 11 are never asserted, so the pack does not check them either.

The expected data was confirmed by running the upstream `solution/solve.sh` in the baseline image without network. It writes exactly those values (apple 150, banana 250, cherry 300, ... mango 1100).

### Differential against the native tests

We ran the upstream test functions inside the baseline image and the Oracle on 39 hand-made `recovered.json` files. On the pack side, each file went through the framework's own evidence parser (`securebench.evidence.parsers.parse`) before `judge`. These included the correct output; boolean ids and values; floats in `id` and `value`; string ids; extra and claim fields; unsorted, duplicated, missing and null records; old WAL values; wrong names on checked and unchecked ids; empty, non-list, non-JSON and byte-order-marked files; and deep nesting, including a correct file with an extra field nested to exactly 57 and to 58 levels. All verdicts agree except the seven inputs listed under "Fidelity changes" as strict-parser rejections (duplicate key, NaN, an overflowing number `1e400`, two 21+ character integers, lone surrogate, nesting of 58 levels). SecureBench is stricter on each of them.

## Fidelity changes

- **Instructions:** none. `instructions.md` is upstream `instruction.md` byte for byte (equivalent).
- **Strict JSON parsing (stricter).** Upstream uses Python's `json.load`. The artifact check's parser additionally rejects duplicate object keys, `NaN`/`Infinity`, number literals that overflow a float (such as `1e400`, which `json.load` turns into `inf`), integer literals longer than 20 characters, lone surrogates in strings, nesting deeper than 57 levels and files over 16 MiB. The depth limit is 57 (since commit b1086f3), which leaves room for the framework to wrap the parsed value in the judge request and the attempt record. A file that upstream accepts only through one of these features (for example a correct file with an extra `"x": NaN` or `"x": 1e400` field, an extra field nested 58 levels deep, or a 21-digit `value` on an unchecked id) fails here. Python's own parser accepts nesting up to its recursion limit, roughly 1,000 levels. No real implementation of this task produces such output, and the framework offers no lenient JSON parser.
- **Symlinked `recovered.json` (stricter).** Upstream's `open()` follows a symlink. Here a symlink that escapes `/app` fails capture, and one that stays inside `/app` is captured as a symlink, which the artifact check reports as `not_regular`. Writing the answer as a regular file is the plain reading of the instructions.
- **Scope `/app`, bounds 100,000 entries and 2 GiB (stricter only beyond those bounds).** Upstream never inspects `/app` beyond `recovered.json`, so the bounds are set as high as SecureBench allows to cover scratch files an agent might leave. Changes outside `/app` are not captured, which does not matter because upstream reads nothing outside it. Internal symlinks are allowed.
- **Special and unreadable files in `/app` (stricter).** Capture fails the attempt (class `capture`) when the agent leaves a FIFO, socket or device file, an unreadable file, or a symlink that escapes `/app` anywhere in `/app`. The native verifier reads only `recovered.json` and would still pass such a run. SecureBench must read the whole scope to capture the candidate, and it cannot capture such entries faithfully. Solving the task never needs them: the reference leaves only regular files.
- **Allowed domains: none (equivalent for grading).** Upstream allows internet access. The reference solution uses only tools already in the image (`python3`, `sqlite3`, `xxd`).
- **Cases:** one artifact check covering all seven upstream tests (equivalent).

## Candidates

- `reference.sh`: runs `upstream-solve.bash`, a verbatim copy of upstream `solution/solve.sh`, under bash after `cd /app`. No drift repair was needed.
- `null.sh`: changes nothing.
- `mutant-checkpoint-first.sh`: opens the database read-write before decrypting. SQLite then discards the invalid WAL (we saw `main.db-wal` drop to 0 bytes in the baseline after a read-write open), so only 5 records survive. Expected: both graders fail.
- `mutant-float-values.sh`: right records with values written as floats (`150.0`). This is aimed at the parser's int/float distinction and at the `isinstance(value, int)` transliteration. Expected: both graders fail.
- `mutant-csv-strings.sh`: right records exported through `sqlite3 -csv` with ids and values left as strings. Expected: both graders fail.
- `mutant-sqlite-json-rowid.sh`: decrypts with `xxd` and writes the image's `sqlite3 -json` output with an extra `rowid` field. It checks that the strict parser and the Oracle accept sqlite3's own JSON formatting and extra fields. Expected: both graders pass.
- `attack-symlink-escape.sh`: `recovered.json` as a symlink out of `/app`, plus an absolute symlink to `/.securebench`. SecureBench: `failed`, class `capture`.
- `attack-verdict-claim.sh`: base data padded with guessed rows, verdict fields in every record, and forged `reward.txt` and `verdict.json` files. SecureBench: `failed`, class `oracle`.
- `attack-oracle-crash.sh`: base data plus records with unhashable and mixed-type ids, 20-character integers and a value nested 57 levels deep, the deepest the parser accepts. It is aimed at a judge that raises instead of failing, and at the framework's own request and record encoding. SecureBench: `failed`, class `oracle` ("item 5: id should be an integer").

## Note: the evidence depth fix

An earlier version of `attack-oracle-crash.sh` wrote a file nested 63 levels deep. The parser accepted it (its limit was 64), but wrapping the value in the judge request went over the encoder's limit, and `securebench run` crashed without writing a record. Commit b1086f3 fixed this in the framework: evidence deeper than 57 levels is now `unparsable`, and a judge request that cannot be encoded fails the check. The attack was then set to the new maximum of 57 so that it still reaches the Oracle.

## Divergences from native

None. In `qualification.json`, every mutant gets the same verdict from both graders: `checkpoint-first`, `float-values` and `csv-strings` fail both; `sqlite-json-rowid` passes both. The reference passes both, the null candidate fails both, and the three attacks end `failed` in SecureBench (`symlink-escape` with class `capture`, the other two with class `oracle`). The native harness also fails all three attacks.

## Review

Reviewer: ac732195d308d70d8, 2026-10-27 (second pass, after the converter addressed the first review's findings)

Pack digest at review: `sha256:a35b76b46942afbea1d33877feee5c43a54356586eac12c941bb74a567690795` (`securebench validate`: valid). The fixes touched only `CONVERSION.md`; the digest is unchanged since the first pass, and no file in `task/` or `candidates/` changed after it.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. No fidelity change needed.
2. Scope. One root, `/app`, the only directory the instructions name. I listed `/app` in the pinned baseline (`docker run --network none`): it holds `main.db` and `main.db-wal` only, with no symlinks, so nothing leads out of the root. No test or convention-loaded files apply: the upstream tests live in `/tests` natively, are not in the image, and the pack runs no code in an Evaluation (artifact check only). No exclude patterns are declared. `symlinks = true` is harmless because the check reads one file and a symlink there is reported `not_regular` (recorded as stricter). Capture failures on special, unreadable or escaping entries anywhere in `/app` are now recorded as stricter ("Special and unreadable files in `/app`").
3. Expected value leaks. No `public/` or `evaluation/`. In the baseline image, `/tests`, `/solution`, `/oracle` and `/logs` are absent. A grep of the whole image for `mango` and `honeydew` finds only pip's vendored `rich` colour tables. The WAL-only names (fig to mango) and the values 150 and 250 exist in the image only inside the XOR-encrypted WAL (`b"mango"` is absent from the raw bytes and present after XOR with 0x42), which is the puzzle itself. The base records 3 to 5 are readable from `main.db`, as upstream intends. `allowed_domains` is empty, so the published upstream tests are not reachable, and no limitation section is needed.
4. Challenges. None: the pack has no protocol check.
5. Cases. One artifact check covering upstream's seven tests over one file; nothing added, no seed used (upstream draws nothing at random).
6. Oracle. Every literal (11, the id list, 150, 250, the nine names, the threshold 5) is in `hidden/expected.json` and matches `tests/test_outputs.py`; `oracle.py` holds only comparison logic. Each function matches its upstream test line by line with the same Python semantics (`isinstance` with bools, `True == 1`, later-wins dict for `id_to_item`, presence-guarded checks in `test_wal_was_decrypted`). Stopping at the first failure is sound because upstream's reward needs all seven tests to pass. Work is bounded by the 16 MiB parser limit and is at most n log n; every test is wrapped so a raise becomes a failed judgment. Extra fields are ignored, as upstream ignores them. My own differential (upstream test functions under host Python `json.load` against the framework parser plus `judge`, 12 inputs including `true` as id 1, wrong unchecked names and values, CRLF whitespace, a 20-digit unchecked value, a dict top level and an empty file) agreed everywhere except an extra `"x": 1e400` field. That case is now listed among the strict-parser rejections, and the converter's differential (39 inputs, seven stricter rejections) includes it.
7. Candidates. `upstream-solve.bash` is byte-identical to upstream `solution/solve.sh`; `reference.sh` only adds `cd /app` and runs it under bash. `null.sh` changes nothing. The four mutants run real code (sqlite3, Python, xxd). Three aim at the one place the check differs from upstream, the strict JSON parser and the `isinstance` transliteration (float values, CSV strings, sqlite3's own `-json` output with an extra field); the fourth is the realistic mistake of opening the database read-write before decrypting, which discards the WAL. The three attacks target capture (escaping symlinks), verdict claims and forged reward files, and judge crashes. `attack-oracle-crash`'s payload has `jsondata.depth` 57, the deepest the parser accepts, so it reaches the Oracle; qualification shows it failing with class `oracle`. No candidate can pass without the hidden names, which only decryption yields.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run is admitted, rejudged, not dirty and records the digest above. The runs name two framework commits, e574fb4 and 47cc04f; `git diff e574fb4 47cc04f -- securebench pyproject.toml uv.lock` is empty (the only commit between them converts regex-chess), so the SecureBench code is the same. Verdicts: the reference passes both graders, null fails both, `checkpoint-first`, `float-values` and `csv-strings` fail both, `sqlite-json-rowid` passes both, and all three attacks end `failed` in SecureBench (`symlink-escape` class `capture`, the other two class `oracle`) and fail natively. There is no divergence, and "Divergences from native" says so correctly.
9. Inventory. `conversions/inventory.tsv` has no row for `db-wal-recovery` yet; the coordinator adds it at commit. No exclusion reason applies: the task is a pure file artifact with no service, network or privilege need.

Upstream assertions: every assertion of the seven tests maps to an Oracle function (table in "How the pack grades"); none is dropped.

First-review findings, rechecked:
- Overflowing number literals (`1e400`): now listed in the "Strict JSON parsing" bullet with an example, and the differential paragraph counts it among the stricter rejections. Fixed.
- Special and unreadable files in `/app`: now a separate fidelity change, labelled stricter, with the reason. Fixed.
- Stale "open framework issue" placeholder: replaced by the divergence summary from qualification. Fixed.

Findings:
- None.

Verdict: approved
