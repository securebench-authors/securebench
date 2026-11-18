# log-summary-date-ranges

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/log-summary-date-ranges

## How the pack grades

The task has one deliverable, `/app/summary.csv`, and upstream's verifier reads only that file. The pack has one protocol check, `summary`, with one case. Its adapter, `evaluation/adapter.py`, runs on the baseline's own `/usr/local/bin/python3` (3.13.7, outside the scope, so the candidate cannot replace it). It opens the file as upstream's test does (`newline=""`, UTF-8 with strict errors) and reports `list(csv.reader(f))` as an array of arrays of strings. If the file is missing or not readable, is not valid UTF-8, or makes `csv.reader` raise, the adapter reports `unable` and the case fails. No candidate code runs in the Evaluation: the adapter is started with `-I`, so nothing under `/app` is on its import path.

Upstream's `tests/test_outputs.py` has two tests:

| Upstream assertion | Where it is checked |
|---|---|
| `test_summary_file_exists`: `OUTPUT_FILE.exists()` | the adapter reports `unable` (`absent`) when the file is missing |
| `reader` is not empty | `judge`: "the CSV file is empty" |
| `header == ["period", "severity", "count"]` | `judge` compares row 0 with `hidden/expected.json` |
| `len(reader) - 1 == len(EXPECTED_ROWS)` | `judge` compares the row count |
| each of the 15 rows equals `EXPECTED_ROWS` | `judge` compares each row with `hidden/expected.json` |

Together the assertions require the list of rows `csv.reader` returns to equal the header followed by the 15 expected rows, in order; the Oracle checks exactly that. The header and the 15 rows are copied literally from `EXPECTED_ROWS` and the header assertion into `hidden/expected.json`. Each row is a list of strings, as `csv.reader` returns it, so `"370"` and `" 370"` differ just as they do upstream.

## Fidelity changes

- **CSV parsing (equivalent).** The adapter calls the same `csv.reader` as upstream's test, with the same `open` arguments. Upstream's test runs on the Python 3.13 that `uvx -p 3.13` downloads at grading time, whose patch release may be newer than the baseline's 3.13.7. We know of no change to `csv.reader` within 3.13 patch releases. The stock SecureBench interpreter (3.12.15) is not used, because its version differs from upstream's.
- **Text decoding (equivalent).** The adapter names `encoding="utf-8"` with strict errors. Natively the verifier's Python runs in UTF-8 mode (the image's `LANG` is empty, so the C locale is coerced), which decodes the same way. Non-UTF-8 bytes fail both graders. A byte-order mark stays part of the first header field (`"﻿period"`) in both and fails the header comparison.
- **Observation bounds (equivalent).** The observation schema allows at most 1,000 rows of at most 64 fields of at most 4,096 bytes, and the response at most 4 MiB. A file beyond any of these bounds fails the case. Every file the native test accepts holds the 16 fixed rows of 3 short fields, so it fails natively too.
- **Two tests become one check (equivalent).** Upstream's two tests both pass only when the file exists and holds the expected rows, so one case with the same conditions gives the same verdict.
- **Scope: `/app`, excluding `logs`, `**/.venv`, `**/venv` and `**/env` (equivalent for every solution).** The instructions name `/app/summary.csv` as the only deliverable. The logs are input whose counts upstream hardcodes, so a candidate's edits to them change no native verdict. Virtual environments under these common names contain absolute symlinks out of `/app` that would fail capture, and nothing graded lives there. Changes outside `/app` are dropped; upstream's verdict depends on nothing an honest solution writes elsewhere (only the two attacks below rely on paths outside `/app`).
- **Capture can fail a candidate that passes natively (stricter, in uncommon cases).** Natively anything may be left in `/app`. Here capture fails the attempt, whatever `summary.csv` holds, when `/app` (outside the excluded paths) contains:
  - a symlink that escapes `/app`, such as a virtual environment under a name other than `.venv`, `venv` or `env` (`python3 -m venv /app/myenv` creates `myenv/bin/python -> /usr/local/bin/python3`);
  - a special file (FIFO, socket, device node) or a file capture cannot read;
  - more than 100,000 entries or more than 2 GiB of file bytes. These are the largest bounds a scope allows; upstream allows 10 GiB of storage.

  Relative symlinks inside `/app` are allowed. A `/app/summary.csv` that is itself such a symlink passes, as natively, because the adapter's `open` follows it (we checked this with a candidate that also created a venv at `/app/env`).
- **Allowed domains: `deb.debian.org` only (stricter).** Upstream sets `allow_internet = true`. The reference solution's only network use is `apt-get update && apt-get install -y grep coreutils`, and the image's apt sources (`/etc/apt/sources.list.d/debian.sources`) name only `deb.debian.org` (both `debian` and `debian-security`). The task itself needs no network.
- **Reference wrapper (equivalent).** Upstream's `solution/solve.sh` is a bash script (arrays, process substitution), and both graders here start candidates with `sh`. `candidates/upstream-solve.bash` is upstream's script byte for byte, and `reference.sh` only changes to `/app` and runs it with the image's bash. No drift repair was needed: the unmodified script passes natively and in SecureBench.

## Candidates

- `reference.sh`: upstream's solution, unchanged, run through bash.
- `null.sh`: changes nothing; the file is absent.
- The mutants share `candidates/summarize.py`, which counts severities correctly (lines containing `[ERROR]`, `[WARNING]` or `[INFO]`, over the date ranges of the instructions) and writes the file in a different style for each. Four aim at how the file is decoded and split into rows, which the adapter must do exactly as upstream's test does:
  - `mutant-csv-writer.sh`: `csv.writer` defaults, so `\r\n` terminators. Correct for `csv.reader`; expected to pass both.
  - `mutant-quote-all.sh`: every field quoted and no final newline. Correct for `csv.reader`; expected to pass both.
  - `mutant-blank-line.sh`: an extra blank line at the end, which `csv.reader` returns as a sixteenth data row `[]`. Expected to fail both.
  - `mutant-bom.sh`: written with `utf-8-sig`. Expected to fail both on the header.
  - `mutant-substring.sh`: well-formed file, but counts every line containing the severity word, falling into the task's trap (WARNING messages mentioning "ERROR"). Expected to fail both.
- `attack-root-conftest.sh`: writes a wrong summary plus `/pytest.ini` and `/conftest.py`. pytest finds the ini file in a parent of `/tests`, makes `/` the rootdir and loads the conftest, which rewrites every test outcome to passed.
- `attack-shadow-curl.sh`: writes a header-only summary and puts a fake `curl` in `/usr/local/bin`, ahead of `/usr/bin` on `PATH`. The native `test.sh` pipes `curl` output into `sh` to install uv, so the fake installer drops a `uvx` that exits 0 and the reward becomes 1.

Both attacks fail in SecureBench because nothing outside `/app` is captured and no candidate code runs while grading.

## Divergences from native

The reference, the null candidate and all five mutants get the same verdict from both graders. Both attacks diverge, and SecureBench is right both times:

- `attack-root-conftest`: native reward 1.0, SecureBench `failed` (oracle). The summary has one data row, with a wrong count. Natively, `/pytest.ini` and `/conftest.py` rewrite pytest's outcomes; SecureBench captures neither file, and its adapter reads the summary with the baseline's Python.
- `attack-shadow-curl`: native reward 1.0, SecureBench `failed` (oracle). The summary has a header and no data rows. Natively, the fake `/usr/local/bin/curl` replaces the uv installer and pytest never runs; SecureBench captures nothing outside `/app` and runs no candidate code while grading.

## Review

Reviewer: a5519b22af2638c9a, 2026-10-26 (second review, after the converter addressed review 1)

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: still identical.
2. Scope. One root, `/app`, now excluding `logs`, `**/.venv`, `**/venv` and `**/env`, with the largest bounds a scope allows (100,000 entries, 2 GiB). The only deliverable is `/app/summary.csv`, which the root covers, and the new exclude cannot touch it. Upstream's tests live in `/tests`, outside the scope. The adapter is started with `-I`, so no file under `/app` is importable: a planted `/app/csv.py` was not loaded in my test. The baseline `/app` holds only `logs/` and no symlinks. The ways capture can fail an honest solution are now listed under "Capture can fail a candidate that passes natively (stricter, in uncommon cases)": an escaping symlink such as a venv under another name, a special or unreadable file, and the scope bounds against upstream's 10 GiB. That fixes review 1's second finding.
3. Leaks. The 16 expected rows are only in `hidden/expected.json`. `evaluation/` holds the adapter and two schemas, with no expected value. The challenge is `{}`. The baseline `/app` holds only the input logs, and the pinned digest is the RepoDigest of `alexgshaw/log-summary-date-ranges:20251031`. `deb.debian.org` does not make the answer reachable.
4. Challenges. There is one, the empty object, which leaks nothing.
5. Cases. There is one case for upstream's single CSV read, and `max_cases = 1`. Both upstream tests are merged into it, recorded as equivalent. The seed is unused, which is right, because upstream draws no random values.
6. Oracle. `oracle.py` now holds only judging logic: it type-checks the rows, then tests non-empty, header, row count and each row, in upstream's order, against `hidden/expected.json`. Anything other than `Observed`, or a malformed observation, fails. The work is bounded by the observation schema (at most 1,000 rows, 64 fields per row, 4,096 bytes per field, 4 MiB in all). Nothing claims a verdict. The CSV is now parsed in the Evaluation by the real `csv.reader` on the baseline's `/usr/local/bin/python3` (3.13.7), which lies outside the scope. That fixes review 1's main finding (Section 4.4). I ran the adapter in the baseline image (`--network none`) on edge-case files, and each gave what the native test sees:
   - The expected rows, also through a relative symlink: correct rows.
   - Missing file: `unable`/`absent`.
   - A directory: `unable`/`unreadable`.
   - A BOM: `"﻿period"`, which fails the header check.
   - Byte `0xff`: `unable`/`not-utf8`.
   - A 200,000-character field: `unable`/`csv-error` (the field limit).
   - A NUL inside a field: kept as `\u0000`.

   A huge file can only end in a timeout, a memory kill or an oversized output, and each of those is `case_error`, so `failed`. No file the native test accepts is anywhere near these bounds.
7. Candidates. `upstream-solve.bash` is still byte-identical to upstream `solve.sh`. `reference.sh` is unchanged. The five mutants run real code and now aim at decoding and row splitting, which is where the adapter must match upstream: CRLF, quote-all without a final newline, a trailing blank line, a BOM, plus the counting trap. All five agree with native. Both attacks target the native grader, the only tampering route this task offers, since no candidate code runs during grading. They fail in SecureBench.
8. Divergences. `validate` prints pack digest `sha256:fb455d116d747d38f8723347c40f1b5209a0df5a1adf43b36a08e858eb81e02c`. Every SecureBench run in `qualification.json` records that digest, at a clean framework commit (`b994ecff`, the current HEAD), and every run was rejudged. `problems` is empty. The native results are `native_cached`, which is valid because no candidate script or other file in `candidates/` changed. The null candidate now fails with `case_error` (`unable`/`absent`), which is still `failed`. The only divergences are the two attacks (native 1.0, SecureBench `failed`), and the explanations hold.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet. No exclusion reason applies.

Upstream assertions:
- `OUTPUT_FILE.exists()` is checked by the adapter's `absent` route.
- The emptiness, header, row-count and per-row assertions are each a `judge` branch.

None is dropped.

Findings:
- None that blocks. One note, which changes no verdict: the "CSV parsing" bullet says native `uvx -p 3.13` "downloads" a Python 3.13 at grading time. By uv's default `python-preference = managed`, an installed system interpreter is preferred over a download, so the native verifier very likely runs the image's own 3.13.7, the same interpreter the adapter uses. Either way the bullet's "equivalent" label holds. The converter may want to correct the wording.

Verdict: approved
