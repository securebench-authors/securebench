# financial-document-processor

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/financial-document-processor

## The conversion in short

The baseline image holds 17 documents (10 JPG, 7 PDF) in `/app/documents/`, under names its build randomized. The agent must classify them by content, move the invoices to `/app/invoices/` and the rest to `/app/other/`, extract each invoice's total and VAT, and write `/app/invoices/summary.csv` with a final `total` row. Upstream identifies documents by the SHA-512 of their content, so the random names do not matter.

Nothing has to run at grading time, so the pack has four artifact checks and no protocol check. Every check lists the three folders `/app/invoices`, `/app/other` and `/app/documents`; each listing carries the SHA-256 of every file and the target of every symlink, so the Oracle identifies documents by content as upstream does, and follows symlinks and `..` between the three folders as upstream's filesystem calls do (`_Tree.resolve` in `hidden/oracle.py`). The `summary` check also reads `/app/invoices/summary.csv` as text.

The Oracle reads the summary the two ways upstream reads it: the header and the row count as `csv.DictReader` gives them, and the values as `pd.read_csv` gives them. It reimplements CPython's csv reader and the parts of pandas' reader that matter here: its NA strings, a field cut at its first NUL character, leading fields taken as the index when the first data row is longer than the header, and the column types pandas infers (numbers, booleans or text).

## How upstream's tests map to checks

Upstream has one test file, `tests/test_outputs.py`, with seven test functions, all of which check what the task asks for. There are no regression tests.

| Upstream test | Assertion | Check | How the check carries it |
|---|---|---|---|
| `test_directories_created` | `/app/invoices` exists and `is_dir()` | `invoices` | `/app/invoices` must resolve to a directory, following symlinks |
| `test_directories_created` | `/app/other` exists and `is_dir()` | `other` | `/app/other` must resolve to a directory |
| `test_invoices_moved_correctly` | the set of SHA-512s of the entries of `/app/invoices` for which `is_file()` holds, names ending in `.json` skipped and `summary.csv` counted by name, equals `expected_original_documents` | `invoices` | the same set over the entries of the resolved directory, each resolved as `is_file()` and the hash resolve it, with SHA-256; `invoices.documents` and `invoices.names` in `expected.json` |
| `test_other_documents_moved_correctly` | the set of SHA-512s of the entries of `/app/other` for which `is_file()` holds equals `expected_original_others` | `other` | the same set, with SHA-256; `other` in `expected.json` |
| `test_summary_csv_exists` | `/app/invoices/summary.csv` exists | `summary` | the file is present, regular, valid UTF-8 and at most 1 MiB |
| `test_summary_csv_structure` | `csv.DictReader` field names equal `expected_headers` | `summary` | the first row of the Oracle's csv reader (excel dialect, universal newlines) equals `summary.header` |
| `test_summary_csv_structure` | `len(rows) == 11` | `summary` | the non-empty rows after the header number `summary.rows` (11) |
| `test_summary_csv_content` | `pd.read_csv` does not raise | `summary` | a text that ends inside a quoted field, or a row longer than pandas expects, fails |
| `test_summary_csv_content` | `len(df) == len(expected_data)` | `summary` | the pandas table has as many rows as `summary.amounts` has entries (11) |
| `test_summary_csv_content` | for each row, `filename == "total"` or the SHA-512 of `Path("/app/invoices") / filename` is in `expected_data` | `summary` | the filename equals `summary.total_row`, or `_join` and `_Tree.resolve` reach a regular file whose SHA-256 is a key of `summary.amounts`; a filename column pandas reads as numbers or booleans fails, as `Path / <number>` raises |
| `test_summary_csv_content` | `abs(float(total_amount) - expected) < 0.01` | `summary` | the same `float()` and `< 0.01`; a boolean column counts as 1.0 and 0.0, as `float(True)` does |
| `test_summary_csv_content` | `abs(float(vat or 0) - expected_vat or 0) < 0.01`, where a NaN or empty actual VAT and an empty expected VAT count as 0 | `summary` | the same comparison, with pandas' NA strings read as NaN |
| `test_original_documents_dir_empty` | `/app/documents` can be iterated and no entry `is_file()` | `documents` | `/app/documents` resolves to a directory and no entry of it resolves to a regular file |

Upstream draws no random values, so the Oracle does not use the seed.

### Expected values

`hidden/expected.json` holds every value the Oracle compares with, and `hidden/oracle.py` holds none. `hidden/derive.py` writes the file from upstream's `tests/test_outputs.py` with `ast`, so nothing is copied by hand: the three hash lists and `expected_data`, `expected_headers`, the constant 11 of `len(rows) == 11` (checked against `len(expected_data)`), the constant `"total"` of `filename == "total"` (checked to be the one key of `expected_data` that names no document), the entry `"summary.csv"` that upstream counts by name, and the three columns the content test reads as filename, total and VAT. It maps every SHA-512 to the SHA-256 of the same file in upstream `environment/documents/`, and fails unless the 17 shipped documents and the 17 listed hashes match one to one. To redo it: `python3 -I task/hidden/derive.py conversions/upstream/terminal-bench/financial-document-processor`. The values are the same as before the remediation; only the file's layout changed.

The baseline holds exactly these documents: `sha512sum /app/documents/*` in the pinned image (run with `--network none`) gives the 17 SHA-512s of upstream's lists.

### Differential tests against upstream's tests

The Oracle replaces `csv.DictReader`, `pandas.read_csv` and the filesystem calls of upstream's tests (pandas is not available to an Oracle, and upstream installs it at grading time). `hidden/differential.py` compares them; its docstring gives the commands. Upstream's side runs in `python:3.13-slim` (Python 3.13) with pandas 2.3.2 and pytest 8.4.1, the versions upstream's `test.sh` pins, with no network. We reran every mode for the remediation.

- **`layouts`: 141 cases.** Each builds an `/app` with the shipped documents and a `summary.csv`, runs upstream's seven test functions verbatim, and judges the same tree with the Oracle (loaded as the Oracle worker loads it), with the three listings built as the framework builds them for this scope and the summary through the framework's `text` parser binding. The cases cover line endings, quoting, blank and whitespace-only lines, a byte-order mark, invalid UTF-8, header variants, short and long rows, leading index columns, NUL characters, every pandas NA string and near misses for the VAT, number formats, numbers of more than 4,300 digits, boolean VAT columns, numeric filenames with and without a total row, totals 0.0099 and 0.01 from the expected value, repeated rows, filenames written as `./name`, `name/.`, `../invoices/name`, `/../app/invoices/name`, through another folder, through a missing directory, relative to `/app` or outside `/app`, a filename with a component of 256 bytes, extra files, directories and symlinks in the three folders (loops, dangling links, a chain of 40 and of 41 links, targets with a component of 255 and of 256 bytes), and the folders or the summary themselves as symlinks. 135 agree (68 pass on both sides). The 6 that differ all pass upstream and fail here, and each is a stricter change listed below: `padded-past-1-mib`, `invoices-in-store-symlinked`, `summary-symlink-to-app`, `invoices-dir-symlink`, `other-dir-symlink` and `documents-dir-symlink-empty`. The Oracle gives the same verdicts on all 141 cases on the host's Python 3.12.15 (`ours` mode).
- **`values`: 723,492 numbers.** For every expected total and VAT (and 0), numbers within about 0.0105 of it, written with 2 to 17 decimals, as shortest representations, and as the 40 doubles on each side of expected ± 0.01. It compares upstream's comparison on the value `pd.read_csv` parses from a numeric column with the Oracle's `float()` of the same text. 28 differ, in both directions: all have 17 to 22 significant digits and lie within one unit in the last place of expected ± 0.01, where pandas' parser rounds differently from Python's correctly rounded `float()`. No number with 16 or fewer significant digits differs. When a column holds any text pandas cannot parse as a number, upstream applies Python's `float()` to the text, as the Oracle does.
- **`numeric`: 31,015 strings.** Every string of up to 4 characters over digits, `.`, `e`, `E`, signs, space, tab, `i`, `n`, `f` and `a`, and a list of words (infinity spellings, booleans in every case, integers at the int64 and uint64 limits, also behind 4,400 leading zeros, integers of more than 4,300 digits, numbers at the limit of a double). It compares the column type the Oracle infers for a one-value column with the dtype pandas gives it, and checks that Python's `float()` accepts every string pandas reads as a number. 3 differ: two numbers of 309 and 310 digits, and `1.7976931348623158e308`, which pandas rejects as out of range and the Oracle reads as a number.
- **`rows`: 300,000 random texts** over `,`, `"`, `\n`, `\r`, NUL, space and two letters. The Oracle's csv reader gives the same rows, or the same error, as `csv.reader` over a file opened in text mode, on every one.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Document identity (equivalent).** Documents are identified by SHA-256 where upstream uses SHA-512. Both are computed over the whole content, and `derive.py` checks that the 17 documents are distinct under both.
- **CSV reading (equivalent, with two residuals).** The Oracle reimplements CPython's csv reader and the parts of `pd.read_csv` listed above, and compares with the same `float()` and `< 0.01` as upstream. Where the two upstream readers disagree, the Oracle follows the one that fails: a text that ends inside a quoted field is kept by `csv.reader` but makes `pd.read_csv` raise "EOF inside string", so the Oracle fails it. The differential tests show the same verdicts except for two residuals, which no extraction produces: numbers written with 17 or more significant digits within one unit in the last place of a threshold (both directions), and, for the filename column only, numbers of more than 300 digits or at the limit of a double, which matter only for a summary whose filenames are all such numbers and that has no total row. pandas' integer parser also makes a column with an integer outside the 64-bit range text or numbers depending on which comes first; the Oracle treats it as text in either order, which again matters only for such a filename column.
- **Paths and symlinks (equivalent inside the three folders, stricter elsewhere).** The Oracle joins a summary filename to `/app/invoices` as `pathlib` does and resolves it, and every folder entry, as Linux does: it follows symlinks (at most 40 per path), resolves `..` on the real directory, and treats a path of 4,096 bytes or more, or a component of more than 255 bytes, as `ENAMETOOLONG`. Upstream's `is_file()` returns False on `ENOENT`, `ENOTDIR` and `ELOOP` but raises on `ENAMETOOLONG`, so the Oracle skips a folder entry in the first cases and fails the check in the last. So symlinks, repeated entries and filenames such as `./name` or `../invoices/name` get upstream's verdict. A path that leads anywhere the listings do not show fails, where upstream may pass: another directory of `/app` (for example invoices kept in `/app/store` with symlinks to them in `/app/invoices`), anything outside `/app`, and anything more than two levels below `/app`. The same holds for one of the three folders itself replaced by a symlink, and for `summary.csv` as a symlink or reached through one. The platform forces these: capture keeps only `/app`, the scope drops what lies deeper (next bullet), the framework does not allow listing a scope root, a listing of a path that is a symlink reports only `not_directory`, and an artifact check reads a file only at its own path. No plausible correct solution moves the documents and then links to them from elsewhere.
- **Bounds (stricter, negligible).** The summary may be at most 1 MiB (upstream reads any size; a correct summary is about 350 bytes, so only padding fails, `padded-past-1-mib`), each folder may hold at most 10,000 entries, and the Oracle resolves at most 1,000,000 path components per check (a correct solution needs about 100; `attack-symlink-maze` reaches the bound). They keep the Oracle's work on candidate data bounded.
- **Allowed domains (stricter).** `archive.ubuntu.com` and `security.ubuntu.com` for Tesseract, `github.com` and `release-assets.githubusercontent.com` for the Python 3.13 that `uv run` downloads (the image has no Python), and `pypi.org` and `files.pythonhosted.org` for the script's dependencies. The reference's proxy log showed requests to exactly these six hosts and no denied request (run `sha256:368b70bc...`, before the remediation; the reference and the domains are unchanged). Upstream allows the whole Internet.
- **Scope (stricter, only for odd entries).** One root, `/app`. Every graded file sits directly in `/app/invoices`, `/app/other` or `/app/documents`, two levels below `/app`, so the root excludes `*/*/*` and everything deeper is dropped from the candidate. An agent can keep a virtual environment, caches and work trees in `/app`, with internal symlinks allowed and the largest bounds the format allows (100,000 entries, 2 GiB). The baseline's `/app` holds only `documents/` with the 17 files and no symlink. Capture still fails, where upstream may pass, a candidate that leaves within two levels of `/app` an absolute symlink or one leaving `/app`, a FIFO, socket or device, an unreadable entry, or a name capture rejects. Upstream keeps no test files in the image (`/tests` is mounted only at grading time), so there is nothing to exclude, and files the candidate writes outside `/app`, such as `/conftest.py`, cannot affect the verdict.
- **Cases (equivalent).** The pack has upstream's checks and nothing else: the documents are fixed by the baseline, and the Oracle compares exactly upstream's expected values.

## Limitation: answer reachable through an allowed domain

`github.com` is allowed because `uv run` downloads the reference's Python 3.13 from GitHub releases. It also serves the upstream repository, `https://github.com/harbor-framework/terminal-bench-2`, whose `financial-document-processor/tests/test_outputs.py` lists the SHA-512 of every document and every expected amount. The reference cannot run without the domain.

## Divergences from native

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** It moves every document to `/app/other` and writes a summary with only its header, which fails four of upstream's seven tests (`test_invoices_moved_correctly`, `test_other_documents_moved_correctly`, `test_summary_csv_structure` and `test_summary_csv_content`). The native 1.0 can come only from the planted `/pytest.ini` and `/conftest.py`, which rewrite every test report to passed. SecureBench captures only `/app`, and the Oracle reads the folders and the summary itself, so the planted files have no effect and the `invoices` check fails ("wrong documents", 10 missing; run `sha256:efbd3f014c91d4bba2eef1b72145734e248800dddd52c6f31a0d2a13b7df3fe2`). SecureBench is right.

The reference passes both graders. The null candidate, the five mutants and `attack-symlink-maze` fail both. `qualification.json` records pack `sha256:0dce511f2433899fd252a7b5bd08f789b1d382eda837d4996d16a2cec68f32b0` and no problems; every SecureBench run is admitted, rejudged and not dirty. A first qualification of the remediated pack before the review fixes (`sha256:e0a85316...`) gave the same verdicts for every candidate in both graders.

## Remediation

What we removed, restored and moved to bring the pack in line with the current converter brief:

- **Removed: each invoice and the total row exactly once** (`hidden/oracle.py`, the `seen` set in `_row`). Upstream requires 11 rows that each match and does not check that they name different invoices. The Oracle now accepts repeated rows as upstream does (`invoice-row-twice`, `total-row-twice-no-invoice`, `invoice-row-twice-no-total-row` pass on both sides).
- **Removed: summary filenames limited to `name` and `/app/invoices/name`** (`_row`). Replaced by resolving the filename as upstream's `Path("/app/invoices") / filename` and `open` do (`_join`, `_Tree.resolve`), over listings of the three folders instead of `/app/invoices` alone (`task.toml`). The Oracle still never uses evidence as a filesystem path: it looks names up in the listings.
- **Removed: every symlink in the three folders failing its check** (`_files`). Symlinks are now followed as upstream's `is_file()`, hashing and `iterdir()` follow them, within what the listings show (previous section).
- **Removed: stricter readings of the summary.** A NUL character in a field, a summary whose data rows all have leading extra fields, and a boolean column now get pandas' reading (`_pandas_table`, `_column_kind`, `_numbers`), where the Oracle failed them before.
- **Restored: nothing.** Every upstream assertion already had a check (table above), and upstream has no regression tests.
- **Moved to `hidden/expected.json`:** the expected header, the row count, the name of the total row, the entry `summary.csv` that upstream counts by name, and the three columns the content test reads. `derive.py` now extracts all of them from upstream's tests, and `expected.json` is regrouped by check.
- **Removed from `CONVERSION.md`:** the fidelity changes for the removed rules (each invoice once, summary filenames, symlinks, NUL characters, rows longer than the header, hidden cases) and the section "Answer already public upstream". The answer reachable on `github.com` is now recorded as the converter brief asks, above.
- **Candidates deleted:** `attack-duplicate-row`, which does not tamper with grading: it writes a summary that upstream's own test accepts, and it now passes both graders. `mutant-net-total`, `mutant-amount-due` and `mutant-total-row-net`, to keep at most five mutants: each changes one extracted amount, which the Oracle compares with the same `float()` and `< 0.01` as upstream, the place least likely to diverge.
- **Candidates added:** `mutant-relative-filenames`, aimed at the new filename resolution, and `attack-symlink-maze`, aimed at the new symlink resolution. `attack-conftest` lost a lesson code in its comment.

Fixes for the review of the remediated pack (the `## Review` section below):

- **Finding 1 (a component longer than 255 bytes).** `_Tree.resolve` now returns `TOO_LONG` for a component of more than 255 bytes and for a path of 4,096 bytes or more, and `_folder` fails its check on it, as upstream's `is_file()` raises `ENAMETOOLONG`. Before, the Oracle skipped such an entry, so a correct layout plus a symlink to `aaa...` (256 bytes) in a folder passed SecureBench and failed upstream. The differential has cases at 255 and 256 bytes in each folder, a long component followed by `..`, and summary filenames with a component of 255 and 256 bytes; all agree.
- **Finding 2 (integers of more than 4,300 digits).** `_pandas_number` now decides the int64 and uint64 range by comparing digits, without `int()`, which refuses texts of more than 4,300 digits and made `judge` raise. The differential has `vat-zero-4300-digits`, `vat-zero-4301-digits` and `total-int-padded-4400` (all pass on both sides), and `numeric` mode has eight such words.

### Old candidates that an addition failed

In the earlier `qualification.json` no mutant had a native pass with SecureBench `failed`: the seven mutants failed both graders. One attack did, so we ran it once against the remediated pack.

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-duplicate-row` | 1.0 | `failed` (`oracle`, "the same invoice or total row appears twice") | `passed` (run `sha256:e54a994686d01af4bf1d292bbe90adedcf3d531bfe6e16666f4a584bf22cbf97`) |

We then deleted it (above).

## Candidates

- `reference.sh`: upstream `solution/solve.sh` verbatim, after a `#!/bin/sh` line and a comment. Upstream's `#!/bin/bash` comes after the canary comment, so it is not a shebang; the script uses only a quoted heredoc and `&&`, and already runs `cd /app`. No drift repair was needed: `tesseract-ocr=5.3.4-1build5` still installs from the Ubuntu mirrors, and `uv run` resolves the script's pinned dependencies.
- `null.sh`: changes nothing.
- `mutant-total-keyword.sh` (classification, the set comparison by SHA-256): calls a document an invoice when its text contains "total", so the shipping record with line totals (an "other" document) goes to `/app/invoices` and into the summary.
- `mutant-copy.sh` (`/app/documents` empty, the resolution of folder entries): copies each document instead of moving it.
- `mutant-headers.sh` (the csv reader and the exact header): names the columns `filename,total,vat`.
- `mutant-no-vat.sh` (pandas' NA handling of the VAT): never reads the VAT, so five invoices get an empty VAT and the total row's VAT is 0.
- `mutant-relative-filenames.sh` (the filename resolution): writes each filename as `invoices/<name>`, relative to the working directory, which upstream opens as `/app/invoices/invoices/<name>`.
- `attack-conftest.sh`: moves every document to `/app/other`, writes a summary with only its header, and plants `/pytest.ini` and `/conftest.py`, whose report hook rewrites every test report to passed. Upstream's verifier runs `pytest /tests/test_outputs.py`; pytest finds `/pytest.ini` above `/tests`, takes `/` as its rootdir and loads `/conftest.py`.
- `attack-symlink-maze.sh`: leaves the documents in place and fills the three folders with 9,000 symlinks each, in loops whose targets repeat `../<folder>/` 75 times, to make the Oracle's path resolution crash or run out of time and turn the failure into an infrastructure error. In our run (`sha256:f729de6375b3bfef0ad78d1f5943256fc146fa8ee9a22f80a1915af8d71ea448`) the `invoices` check failed with "resolving paths took more than 1000000 steps".

The five mutants rebuild the reference from `reference.sh` with one `sed` change each and run it, so each runs the real OCR pipeline. Each exits 1 without running anything if its change did not touch exactly the expected number of lines, so a mutant can never silently become the reference. `mutant-relative-filenames` failed SecureBench at `summary` ("filename names no regular file", run `sha256:20c36e2d4342f16a083de4d62820f63341c762a52dac20477c1b3814e646caf5`).

## Inventory

Proposed note: `converted`. Remediated: the pack checks exactly upstream's seven tests, reading the summary as csv and pandas do and following symlinks, `..` and Linux's name limits as the filesystem does; stricter only for paths outside the three listed folders (forced by capture and listing) and for a summary above 1 MiB; github.com is allowed because the reference downloads Python 3.13 from it, and it serves the upstream answer.

## Review before remediation

Reviewer: a9bf2ca12f89e720a, 2026-10-13 (second round)

Pack digest at review: `sha256:65330e14dc7972dc140a7eb24769a4740a6f7aca634c3d869d38c8f56874010a` (`uv run securebench validate`). It is unchanged after qualification, and the pack holds no `__pycache__`.

Since the first round, the converter changed `hidden/oracle.py` (fail a summary that ends inside a quoted field), `hidden/differential.py` (10 more layout cases, and `rows` mode adjusted to the new return value) and `CONVERSION.md`. The candidates are unchanged.

Status of the first-round findings:
- **Finding 1 (open quote at end of input, more lenient): fixed.** `_csv_rows` now reports whether the text ends in `IN_QUOTED_FIELD`, and `_summary` fails such a text. A correct summary never ends inside a quote. A quote opened earlier that swallows the rest of the file also ends there, and upstream fails that too.
- **Findings 2, 3 and 4 (extra leading column, NUL characters, folders replaced by symlinks; stricter): fixed.** Each now has its own fidelity bullet labelled stricter, with a reason, and its case is in `differential.py`.

I reran `differential.py layouts` in `python:3.13-slim` with pandas 2.3.2 and no network. It gives 95 cases, and exactly 14 differ, all upstream `pass` and Oracle `fail`. Each of the 14 is a listed stricter change. The three open-quote cases now give `fail` on both sides. `differential.py rows` gives 300,000 texts and 0 differences. My own extra cases from round one also all match the record. `double-slash-filename` falls under "fails any other filename"; `quoted-header`, `numeric-filenames`, the quote-placement cases and `unterminated-in-middle` agree.

1. **Instructions.** `cmp` with upstream `instruction.md`: identical. Unchanged since round one.
2. **Scope.** Unchanged and sound. One root `/app`, excluding `*/*/*`, with internal symlinks allowed. Every graded file is directly in one of the three folders, and the image has no test files to exclude. The remaining capture failures are listed.
3. **Leaks.** No `public/` or `evaluation/`, and expected values only in `hidden/expected.json`. In round one I checked the pinned image with no network: `/app` holds only the 17 documents, their SHA-256s equal `expected.json`, and nothing else in the image carries labels, tests or solutions. `expected.json` is unchanged since then. The six allowed domains match the reference's proxy log. `github.com` serves the answer, which is public anyway (C58).
4. **Challenges.** None: the pack has artifact checks only.
5. **Hidden cases.** No hidden case can help, because every hash and amount is public in upstream's test (C58). `probe-hardcode` passes, as recorded.
6. **Oracle (C52 to C54).** Each invoice and the total row count once. Filename, total and VAT are all checked. The work is linear over at most 1 MiB and 10,000 entries per listing, with no regular expression and no evidence used as a path. The fix adds one boolean and keeps all of this.
7. **Mutants and attacks.** Unchanged. The seven guarded single-edit mutants run the real OCR pipeline, one per requirement. `attack-duplicate-row` targets C52 and `attack-conftest` targets C49. In qualification all of them get `failed` (`oracle`) from SecureBench in both rounds, never `invalid`.
8. **Divergences from native.** `qualification.json` reports `problems: []` and two rounds. All 11 SecureBench runs are admitted, rejudged, not dirty, and record pack `sha256:65330e14...874010a`, the digest I noted. The reference passes both graders. The null candidate and the seven mutants fail both. Two candidates diverge, and both are explained correctly:
   - `attack-duplicate-row`: native 1.0, because upstream does not deduplicate rows. The stricter change is listed, and SecureBench is right.
   - `attack-conftest`: native 1.0, which only the planted `/pytest.ini` and `/conftest.py` can produce. SecureBench captures only `/app`, and the Oracle fails the `invoices` check. SecureBench is right.
9. **Inventory.** There is no row yet. It should be `converted`, and no exclusion reason applies.

**Upstream assertions.** Each of the seven test functions is mapped in the table. Every difference found by the differential tests and by my extra cases is listed with a label and a reason.

Findings:
- None that blocks. One note for the record: the `attack-conftest` divergence bullet says its layout "fails five of upstream's seven tests". Running upstream's tests on that layout (every document in `/app/other`, a header-only summary, `/app/documents` empty) fails four: `test_invoices_moved_correctly`, `test_other_documents_moved_correctly`, `test_summary_csv_structure` and `test_summary_csv_content`. The other three pass. The conclusion does not change, because a native 1.0 still needs the planted files.

Verdict: approved

## Review

Reviewer: conversion-reviewer (session bdda55d6), 2026-10-25 (second round)

Pack digest at review: `sha256:0dce511f2433899fd252a7b5bd08f789b1d382eda837d4996d16a2cec68f32b0` (`uv run securebench validate`). It is unchanged after qualification. Since my first round, only `hidden/oracle.py`, `hidden/differential.py` and `CONVERSION.md` changed.

Status of my first-round findings (on `sha256:e0a85316...`):
- **Finding 1 (a component longer than 255 bytes, more lenient): fixed.** `_Tree.resolve` now returns `TOO_LONG` for a path of 4,096 bytes or more, or a component of more than 255 bytes, counted in UTF-8 bytes. `_folder` fails its check on it, as upstream's `is_file()` raises `ENAMETOOLONG`. My end-to-end probe (a correct layout plus a symlink to a 300-byte name in `/app/documents`) passed before. It now gets `failed` (`oracle`, "too long, so is_file() raises"): run `sha256:e420947bba54380d88dc0f5622e0fbbdc28d15ab9d0f407430a2bef55325a44c`, admitted, on the current digest. My 14 probe cases all agree with upstream's tests, run in `python:3.13-slim` with pandas 2.3.2 and no network. Besides the first round's cases, they include a 256-byte multibyte name, a long component after a regular file and after a missing directory (both pass on both sides, since `is_file()` ignores ENOTDIR and ENOENT), and a symlink into `/app/other` with a 256-byte name.
- **Finding 2 (integers of more than 4,300 digits, stricter): fixed.** `_pandas_number` now decides the int64 and uint64 range by comparing digit strings, with no `int()`. I checked by hand that it agrees with the old `INT64_MIN <= int(x) <= UINT64_MAX` at both limits and one past them, with and without leading zeros. `vat-zero-4301-digits` and `total-int-padded-4400` now pass on both sides.

1. **Instructions.** `cmp` with upstream `instruction.md`: identical.
2. **Scope.** Unchanged and sound. One root, `/app`, excluding `*/*/*` (every path of three or more components). The baseline's `/app` holds only the 17 documents and no symlink. The image has no test or convention-loaded files. Capture rejects absolute symlink targets, as the scope bullet says.
3. **Leaks.** There is no `public/` and no `evaluation/`. In the pinned image, run with `--network none`, `/app` holds only the 17 documents, and their SHA-256s are exactly those in `expected.json`. Nothing else in the image carries tests, labels, a solution or a summary. The answer on `github.com` is recorded under the limitation section. I did not check whether the other allowed domains also serve upstream's tests.
4. **Challenges.** None: artifact checks only.
5. **Cases.** No protocol checks and no added checks. The seed is unused, and upstream draws no random values.
6. **Oracle.** A copy of `derive.py` run in my scratch directory reproduces `expected.json` exactly. `oracle.py` holds no expected value, uses no regular expression, and never uses evidence as a path. Its work is bounded: 1 MiB of text, 10,000 entries per listing, and 1,000,000 resolution steps. An exception in `judge` becomes a failed judgment, never `invalid`. I reran on the current pack, in `python:3.13-slim` with pandas 2.3.2 and no network:
   - `layouts`: 141 cases. 135 agree (68 pass on both sides), and only the 6 listed stricter cases differ.
   - `numeric`: 31,015 strings, with the same 3 recorded residuals.

   Both match `CONVERSION.md`.
7. **Candidates.** `reference.sh` is upstream `solve.sh` byte for byte after a 4-line header. The five guarded single-`sed` mutants run the real OCR pipeline. Each is aimed at a place where the check reimplements upstream: classification, the folder-entry resolution, the csv header, pandas' NA handling and the filename resolution. In qualification, all five get the same verdict from both graders (fail). Both attacks get `failed` (`oracle`), never `invalid`.
8. **Divergences.** `qualification.json` reports `problems: []`. All 9 SecureBench runs are admitted, rejudged and not dirty, and record pack `sha256:0dce511f...68f32b0`, the digest I noted. The runs name three framework commits (`25ea1e23`, `7fe0c050`, `a6f3948c`). `git diff` shows no change between them under `securebench/`, `securebench_relay_proxy/`, `securebench_utility/`, `pyproject.toml` or `uv.lock`. The native results are `native_cached`, which is allowed because the candidates are unchanged since the first qualification of the remediated pack. The reference passes both graders. The null candidate, the five mutants and `attack-symlink-maze` fail both. One candidate diverges, `attack-conftest`: native 1.0, SecureBench `failed`. The explanation holds. Its layout fails four of upstream's seven tests, as the earlier review confirmed by running them, so the native 1.0 comes only from the planted `/pytest.ini` and `/conftest.py`, which lie outside the scope. SecureBench is right.
9. **Inventory.** The row in `conversions/inventory.tsv` still describes the pack before the remediation ("each invoice and the total must appear once"). It should be replaced by the note proposed under "## Inventory", which is right for this pack: `converted`. No exclusion reason applies.

**Upstream assertions.** Each of the seven test functions is mapped in the table, and none is dropped. Every difference the differential tests and my probe cases found is listed with a label and a reason.

Findings:
- None that blocks. For the coordinator: update the inventory row (point 9).

Verdict: approved
