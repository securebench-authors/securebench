# gcode-to-text

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/gcode-to-text

## The conversion in short

The baseline holds `/app/text.gcode`, a Prusa MK4S print that embosses text on top of a box. The agent must work out what text the print shows and write it to `/app/out.txt`. Upstream has two tests in `tests/test_outputs.py`, and nothing else is asserted.

The pack has one artifact check, `answer`, which reads `/app/out.txt` with the `text` parser (strict UTF-8, at most 1 MiB). The Oracle's `plan` loads the expected text from `hidden/expected.json` into the check's context. `judge` applies Python's `str.strip()`, as upstream does, and requires equality with the expected text. It fails closed on an absent, non-regular, too large or non-UTF-8 file, on any evidence other than the one declared file, and on a malformed context. Its work is one `strip()` over at most 1 MiB. No protocol check is needed: the deliverable is a file, and nothing has to run at grading time.

## How upstream's tests map to checks

Both upstream tests check what the task asks for; upstream has no regression tests.

| Upstream test and assertion (`tests/test_outputs.py`) | Check and case | How |
|---|---|---|
| `test_hello_file_exists`: `assert hello_path.exists()` for `/app/out.txt` | `answer` (artifact check, no cases) | `judge` fails unless the file's status is `present`, which also requires a regular file (stricter, below) |
| `test_hello_file_content`: `hello_path.read_text()` succeeds | `answer` | the `text` parser decodes the file as strict UTF-8, at most 1 MiB; anything else is `unparsable` or `too_large` and fails (below) |
| `test_hello_file_content`: `assert hello_path.read_text().strip() == "flag{gc0d3_iz_ch4LLenGiNg}"` | `answer` | `judge`: `text.strip() == context`, with the context from `hidden/expected.json` |

The pack has no other check, case or assertion.

### Expected value

`hidden/expected.json` holds `{"text": "flag{gc0d3_iz_ch4LLenGiNg}"}`, the literal upstream's test asserts on (line 17). `oracle.py` holds no expected value. We checked the literal by running the upstream reference (`candidates/reference.sh`) through SecureBench with the allowed domains below: Tesseract read `flag{gc0d3_iz_ch4LLenGiNg}` and the reference wrote it followed by a newline, 27 bytes. Every qualification run of `reference` repeats this.

### Differential test of the check against upstream's tests

The `text` parser replaces `read_text()`, and the Oracle runs on the host's Python 3.12 where upstream's verifier runs Python 3.13. `hidden/differential.py` compares the two on 32 inputs at the acceptance boundary. Its docstring gives the three commands. The native side runs upstream's two test functions verbatim in the pinned baseline with no network, on its Python 3.13.7 with no locale set (UTF-8 mode, as in the verifier's container, whose image sets no `LANG`), with each input at `/app/out.txt`. The SecureBench side runs the framework's `file_evidence` binding with this check's file spec, then `plan` and `judge` of `hidden/oracle.py`, loaded through the Oracle worker's `load`. We reran both sides during the remediation, on the current framework, and got the same 32 verdicts as before.

| Input at `/app/out.txt` | Upstream | SecureBench |
|---|---|---|
| the flag; with `\n`, `\n\f` (Tesseract's page break), `\r\n`, lone `\r` on both sides; with spaces, tabs and blank lines around; with `\v` and `\x1c` to `\x1f` around; with Unicode spaces around (U+00A0, U+3000, U+2028, U+2029, U+0085, U+2003) | pass | pass |
| the flag padded with spaces to exactly 1 MiB | pass | pass |
| empty; whitespace only; absent; a directory | fail | fail |
| the flag with a byte-order mark; with a trailing zero-width space; between NUL bytes; followed by the invalid byte `0xff` | fail | fail |
| the flag twice; the flag and a line `PASSED test_hello_file_content`; quoted; after `The text shows: `; with a space or a `\r` inside it | fail | fail |
| lowercase, uppercase, `O` for `0`, fullwidth, a Cyrillic `а`, without `flag{}`; two readings on two lines | fail | fail |
| **the flag padded with spaces to 1 MiB + 1 byte** | **pass** | **fail** |
| **`/app/out.txt` a symlink to a file holding the flag** | **pass** | **fail** |

Both differences are stricter fidelity changes listed below. The Unicode whitespace that `str.strip()` removes is the same in Python 3.12 and 3.13 on every input above.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** One answer, upstream's fixed literal, as in upstream's test.
- **Answer comparison (equivalent).** The same `strip()` and the same equality as upstream. A byte-order mark and invalid UTF-8 fail both graders, so the parser's stricter decoding changes no verdict (table above; `mutant-utf8-bom` checks the byte-order mark through both real graders).
- **Answer file bound (stricter, negligible).** The artifact check reads at most 1 MiB; upstream reads any size. A correct answer is 26 bytes plus whitespace, so only a file padded with more than a mebibyte of whitespace passes upstream and fails here. The bound keeps the Oracle's work bounded, because the Oracle runs on the host without a sandbox.
- **Regular file (stricter, negligible).** `/app/out.txt` must be a regular file; upstream follows a symlink. Capture would reject a symlink whose target leaves `/app` anyway.
- **Allowed domains (stricter).** `deb.debian.org` for `python3-opencv` and `tesseract-ocr`, which the reference installs with `apt-get` (the baseline's sources are `deb.debian.org/debian` and `deb.debian.org/debian-security`), and `pypi.org` and `files.pythonhosted.org` for the Python packages it installs with `pip`. The reference's proxy log shows requests to exactly these three hosts and no denied request. Upstream allows the whole Internet. We did not find the answer on these hosts: the baseline has no copy of it (a search of every file outside `/proc`, `/sys` and `/dev` for `gc0d3` finds nothing), and the `terminal-bench` 0.2.18 wheel on PyPI holds no task files. We did not search all of PyPI.
- **Scope (stricter, only for odd entries at the top level of `/app` and odd names one level down).** One root, `/app`, which holds the only deliverable. The baseline's `/app` holds only `text.gcode` (1,661,422 bytes) and no symlink. The root excludes `*/*`, so everything below the top level of `/app` is dropped from the candidate: the evaluation reads only `/app/out.txt`, and the contents of an agent's work directories (a virtual environment, caches, links out of `/app`) then count against no capture bound and are neither walked nor captured. The reference writes only top-level files (`makeseg.py`, `render.py`, `ocr.py`, two PNG images and `out.txt`; its segment pickle goes to `/tmp`), so nothing a correct candidate needs is dropped. Internal symlinks are allowed, and the bounds are the largest the format allows (100,000 entries, 2 GiB), which apply only to top-level entries. Capture still fails, where upstream passes, a correct candidate that leaves directly in `/app` an absolute symlink or one leaving `/app`, a FIFO, socket or device, an unreadable directory, top-level files over 2 GiB in total, or a name capture rejects. Capture also lists every top-level directory and checks the name of each entry directly inside it before it applies the exclude patterns (`securebench_utility/utility.py`, `walk_root`), so a name one level down that is not UTF-8, contains a backslash or is too long fails capture too, and a very large top-level directory counts against the capture time limit while it is listed. The reviewer confirmed the first case with a probe that writes the right flag and creates `/app/work/a\b`: SecureBench reports `failed`, class `capture`, where upstream passes. No pack setting avoids these, because the deliverable is a file directly in `/app`. Work outside `/app` (packages, `/tmp`) is not captured and does not matter. Upstream keeps no test files in the image (`/tests` is mounted only at grading time), so there is no test file to exclude, and files the candidate writes outside `/app`, such as `/conftest.py`, cannot affect the verdict.

## Old mutants failed by an addition

The remediation brief asks us to rerun every old mutant that native passed (reward 1.0) while SecureBench said `failed`. There is none: in the qualification before remediation, all four mutants got native 0.0 and SecureBench `failed`, and the pack had no addition to remove.

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| (none) | | | |

## Remediation

- **Removed from the pack:** nothing. The pack had no case, input, check or assertion beyond upstream's two tests, and no randomness. `task/` changes in two comments only: the first line of `hidden/differential.py`'s docstring, which named an internal lesson code, and the scope comment in `task.toml`, which claimed that names below the top level of `/app` cannot fail capture (corrected after the review; see the Scope bullet). The pack digest therefore changes.
- **Restored:** nothing; every upstream assertion already had its check (map above).
- **Moved:** nothing; the expected value was already in `hidden/expected.json`, and `oracle.py` holds only judging logic.
- **Candidates deleted:** `attack-spray.sh`. It wrote four hardcoded readings of the upstream flag, the right one among them, without tampering with grading; a candidate that uses the public answer is outside SecureBench's scope.
- **Candidates added:** `mutant-utf8-bom.sh`, aimed at the one place where the check is not upstream's own code: the `text` parser that replaces `read_text()`. The differential test above already compares them offline; this mutant compares them through both real graders.
- **Candidates changed:** `attack-conftest.sh`, only its comment (an internal lesson code removed).
- **`CONVERSION.md`:** the section "Answer already public upstream" and the bullet "Hidden cases (none added)" removed; the map, the table of old mutants and this section added; references to internal lesson codes, to another conversion and to the architecture document replaced by the reasons themselves.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with a `#!/bin/sh` first line, a comment, and `cd /app` in place of upstream's `#! /bin/bash` line, which comes after the canary comment and so is not a shebang. The script uses nothing specific to bash: its heredocs are unquoted, and the three Python scripts it writes contain no `$`, backquote or escaped character that a shell would expand. No drift repair was needed: it passes SecureBench with tesseract-ocr 5.3.0-2 from bookworm and the pinned pip packages.
- `null.sh`: changes nothing.
- `mutant-no-z-filter.sh` (the text, not the object it is printed on): the reference with the `z1 >= 5.0` filter replaced by `True`, so the box's 10,315 extrusion segments are rendered with the text's 37,004. Tesseract reads nothing, and `/app/out.txt` is blank.
- `mutant-mirrored.sh` (the text as it reads on the print): the reference rendering a plain top-down view (`render.py 0 0 0`) in place of its 201 degree turn about Y, so the text reaches OCR mirrored. Tesseract reads `“`, `a` and `VP`.
- `mutant-lowercase.sh` (the exact text, against the equality after `strip()`): the reference, then lowercasing `/app/out.txt` as a "normalization". Writes `flag{gc0d3_iz_ch4llenging}`.
- `mutant-wrong-dir.sh` (the answer's location, against the existence test): the reference run from `/tmp`, so its relative `out.txt` lands in `/tmp/out.txt` with the right text, and `/app/out.txt` does not exist.
- `mutant-utf8-bom.sh` (the `text` parser in place of `read_text()`): the reference, then rewriting `/app/out.txt` with Python's `utf-8-sig` codec, so the right text follows a byte-order mark. Upstream's `read_text()` keeps U+FEFF and `strip()` does not remove it; the `text` parser rejects the file as unparsable. Both fail.
- `attack-conftest.sh` (aimed at this task's native verifier): reads nothing, writes `flag{}`, and plants `/pytest.ini` and `/conftest.py`, whose report hook rewrites every test report to passed. Upstream's verifier runs `pytest /tests/test_outputs.py`; pytest finds `/pytest.ini` above `/tests`, takes `/` as its rootdir and loads `/conftest.py`. On SecureBench these files lie outside the scope and are not captured, and the Oracle reads the answer itself.

The mutants that change the reference rebuild it from `reference.sh` with one `sed` change each, and exit 1 without running anything if the change did not apply; `mutant-utf8-bom` exits 1 if the byte-order mark is not in place. So no mutant can silently become the reference.

## Divergences from native

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** Its answer is `flag{}`, which fails upstream's equality, so the native 1.0 can come only from the planted `/pytest.ini` and `/conftest.py` rewriting the failed test report to passed. SecureBench captures only `/app`, so the planted files are not in the candidate, and the Oracle reads the answer itself. SecureBench is right.

Every other candidate gets the same verdict from both graders: the reference passes both, and the null candidate and all five mutants fail both (`mutant-utf8-bom`: native 0.0, SecureBench `failed`, `oracle`, "/app/out.txt is unparsable").

## Inventory note

Proposed: `converted`. One artifact check reads `/app/out.txt` and carries upstream's two assertions exactly; remediated with nothing removed from the pack.

## Review before remediation

Reviewer: af35ffe31f3ebe31b, 2026-10-11

`uv run securebench validate` reports the pack valid, digest `sha256:8d3ac062e8676f43bbd62b6a89cf517ab208809d2ab39052e88cc2b024a72475`, at the start of the review and again after qualification. The pack and candidates did not change in between: only `CONVERSION.md` and `qualification.json` were written after the first read.

1. **Instructions.** `cmp` of upstream `instruction.md` with `task/instructions.md` finds them identical.
2. **Scope.** The only deliverable the instructions name is `/app/out.txt`, directly in the one root `/app`. `exclude = ["*/*"]` matches only paths of two or more components, so it never drops `/app/out.txt`, and it lets an agent keep work files in subdirectories. The cases where capture fails a correct candidate (top-level absolute or escaping symlinks, FIFOs, unreadable directories, rejected names) are listed as stricter, and no pack setting avoids them. Upstream ships no test files in the image (`/tests` is mounted at grading), and the Oracle reads the answer by lookup, so no convention-loaded file (lesson C49) can matter.
3. **Expected values.** The flag is only in `hidden/expected.json` (and in `hidden/differential.py`, which is hidden and not loaded by the Oracle). I inspected the baseline image itself: its history adds only `text.gcode.gz` to `python:3.13-slim-bookworm` and decompresses it; `/app` holds only `text.gcode`, whose SHA-256 equals the decompressed upstream `text.gcode.gz`; a `grep` of every file outside `/proc`, `/sys` and `/dev` (run with `--network none`) finds no `gc0d3`, `ch4LL` or `flag{`. The G-code's only text label is the object name `Embossed text`. On the allowed domains, the latest `harbor` (0.24.0) and `terminal-bench` (0.2.18) wheels on PyPI hold no `gc0d3` and no gcode file; I did not search all of PyPI, as `CONVERSION.md` also says. The answer is public upstream anyway (point 5).
4. **Challenge leaks.** The pack has no protocol check, so there is no challenge and no Evaluation environment. The context (the flag) stays on the host.
5. **Hidden case.** None is possible, and `CONVERSION.md` says why: the deliverable is the text one fixed, public G-code file prints, and the flag is a literal in upstream `tests/test_outputs.py` and `README.md` (lesson C58). The hardcoding attack is described with its passing run; I confirmed that run (`run-probe-hardcode`, manifest `sha256:3dad0f73...`, status `passed`). It cannot be a committed candidate because a committed attack must fail.
6. **Oracle.** `judge` checks the check id, the context's type and form, that the evidence is exactly one file at `/app/out.txt` with no listings, its status `present` and a `Text` value; it then compares `text.strip()` with the context, as upstream does. Nothing is counted, so deduplication does not arise. The work is one `strip()` over at most 1 MiB. No regular expression, no file access, no evidence used as a path. I reran the converter's differential test (`hidden/differential.py`: corpus, native side in the pinned baseline with `--network none`, our side through `file_evidence` and the Oracle loader): all 32 inputs agree except the two listed stricter differences (flag padded past 1 MiB, and `/app/out.txt` as a symlink). The Unicode whitespace inputs contain the code points `CONVERSION.md` names.
7. **Mutants and attacks.** Each mutant runs the real reference with one change and targets a requirement: the Z filter separating text from object (`no-z-filter`, OCR reads nothing), the view the text reads in (`mirrored`, OCR reads `“ a VP`), the exact text (`lowercase`), and the location (`wrong-dir`, OCR runs and writes `/tmp/out.txt`). The converter's attempt transcripts show the OCR step ran in every mutant, so none fails for a script error (lesson C73). The `sed`-built mutants exit 1 if their edit did not apply. `attack-spray` targets a substring-matching Oracle and `attack-conftest` the native pytest report (lesson C49). All get `failed` with class `oracle`, never `invalid` (lesson C72).
8. **Divergences from native.** One: `attack-conftest`, native 1.0 and SecureBench `failed`. Its answer `flag{}` fails upstream's equality, so the native pass can only come from the planted `/pytest.ini` and `/conftest.py` (pytest takes `/` as rootdir because `/pytest.ini` is an ancestor of `/tests/test_outputs.py`, and loads `/conftest.py`). SecureBench captures only `/app` and the Oracle compares the answer itself, so SecureBench is right. Every other candidate agrees: the reference passes both graders, and null, the four mutants and `attack-spray` fail both. The earlier `invalid` runs (docker commit timeout) are explained and are not in the recorded qualification.
9. **Inventory.** There is no row yet; the coordinator adds it. `gcode-to-text` is the fourth task of the campaign's extension, in the order `campaign.py order terminal-bench` prints. The row should be `converted`: the answer is a file read by lookup, nothing needs network, host actions or capabilities at evaluation, and the limits are 1 CPU and 2 GiB, so no exclusion reason applies. The note should say that no hidden case is possible (lesson C58), since the flag is a literal in the upstream test.

Upstream assertions. `test_hello_file_exists` (`/app/out.txt` exists) and `test_hello_file_content` (`read_text()` succeeds and `.strip()` equals the flag) are both checked by `answer`, as the table in "The conversion in short" maps them. The differences are the 1 MiB bound and the regular-file requirement, both labelled stricter with a reason. The "Hidden cases (none added)" bullet carries no stricter, more lenient or equivalent label, but it describes no difference from upstream (upstream also has the one case), so nothing is unexplained.

Qualification. `qualification.json` reports no problems. Every SecureBench run is admitted, rejudged, records the pack digest above and the worker record `sha256:d9013d84...`, and was made from a clean tree. The runs name three commits (`7122482`, `0464855`, `c8bee7c`), but `securebench`, `securebench_utility` and `securebench_relay_proxy` have identical trees at all three, as `campaign.py` requires.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer, session bdda55d6-3805-4704-aca7-50b6d04d93e5, 2026-10-25 (second review, after the converter's fixes)

`uv run securebench validate` reports the pack valid, digest `sha256:35b04e2fd4feae513c4c70be200bba699b31c7a04edd0b8690e1b8f4cc1ca6af`. Since the first review, `task/` has changed only in the scope comment in `task.toml` (`git diff`). In `candidates/`, the remediation changes (the `attack-conftest` comment, the deletion of `attack-spray`, the new `mutant-utf8-bom`) are as I first reviewed them.

1. **Instructions.** `cmp` of upstream `instruction.md` with `task/instructions.md` finds them identical.
2. **Scope.** One root, `/app`, which holds the only deliverable, `/app/out.txt`. `exclude = ["*/*"]` matches only relative paths of two or more components, so it never drops `/app/out.txt`. In the baseline image itself, `/app` holds only `text.gcode` and no symlink. The image has no test files (`/tests` is mounted only at grading time), and no test runner runs at evaluation, so no convention-loaded file can matter. The first review's finding is fixed. The Scope bullet now says that capture checks the names directly inside each top-level directory before it applies the excludes (`securebench_utility/utility.py`, `walk_root`). So a name there that is not UTF-8, contains a backslash or is too long fails capture, and a very large top-level directory counts against the capture time limit. The bullet labels this stricter and gives the probe as evidence. The `task.toml` comment no longer claims that such names cannot fail capture. Both statements now match the capture code I read.
3. **Expected value leaks.** The flag is only in `hidden/expected.json` and `hidden/differential.py`, which the Oracle does not load. There is no `public/` or `evaluation/`. I inspected the pinned baseline: its history adds only `text.gcode.gz` to `python:3.13-slim-bookworm` and decompresses it, there is no `/.securebench`, and a `grep` for `gc0d3`, `ch4LL` and `flag{` over every file outside `/proc`, `/sys` and `/dev` (run with `--network none`) finds nothing. On the allowed domains, I also downloaded every `terminal-bench` distribution on PyPI larger than 1 MB (14 sdists, 0.1.0 to 0.2.12, several of which bundle Terminal-Bench 1 tasks): none contains this task or `gc0d3`. Like the converter, I did not search all of PyPI. No limitation section is needed.
4. **Challenges.** The pack has no protocol check, so there is no challenge and no Evaluation environment. The context stays on the host.
5. **Cases.** One artifact context, upstream's literal (`tests/test_outputs.py` line 17). No case was added, and the seed is not used, as upstream draws nothing at random.
6. **Oracle.** `oracle.py` holds no expected value. `judge` checks the check id, the context's form, that the evidence is exactly the one declared file with no listings, its status `present` and a `Text` value, then compares `text.strip()` with the context, as upstream does. Its work is one `strip()` over at most 1 MiB. It uses no regular expression and no evidence value as a path, and it ignores claims: the `flag-pass-claim` input fails. Nothing is counted. I reran `hidden/differential.py` on both sides: the native side on upstream's tests in the pinned baseline with `--network none`, and our side through `file_evidence` and the Oracle loader. All 32 inputs agree except the two listed stricter differences (the flag padded past 1 MiB, and `/app/out.txt` as a symlink), as the table says. There are no regression tests.
7. **Candidates.** `reference.sh` is upstream `solve.sh` with `#!/bin/sh` in place of the non-shebang `#! /bin/bash`, a comment and `cd /app`. The heredocs contain no `$` or backquote, and their backslashes (`\n`, `\d`, `\.`) come before characters that neither dash nor bash expands in an unquoted heredoc, so running under `sh` writes the same scripts. The `sed`-built mutants exit 1 if their edit did not apply, and `mutant-utf8-bom` exits 1 if the byte-order mark is missing. `mutant-utf8-bom` is aimed at the one reimplemented tool, the `text` parser in place of `read_text()`. The other four are aimed at the requirements (Z filter, view, exact text, location), and all run the real reference. `attack-conftest` plants `/pytest.ini` and `/conftest.py`, which this task's native verifier loads. In the new qualification, every mutant gets the same verdict from both graders (native 0.0, SecureBench `failed`, class `oracle`), and the attack gets `failed`.
8. **Divergences.** `qualification.json` reports no problems. Every one of its eight SecureBench runs is admitted and rejudged, records the digest above and the worker record `sha256:d9013d84...`, and comes from a clean tree. The runs name four commits (`84120d2`, `1d37fc4`, `1f41de4`, `a2b9ecc`), but `securebench`, `securebench_utility` and `securebench_relay_proxy` have identical trees at all four (`git diff`). The native results are `native_cached`, which the candidate scripts allow because they have not changed. The one divergence is `attack-conftest`: native 1.0, SecureBench `failed`. The explanation holds. `flag{}` fails upstream's equality, so the native pass can come only from the planted `/conftest.py`, which rewrites the report. SecureBench captures only `/app` and reads the answer itself, so SecureBench is right. The reference passes both graders, and null fails both.
9. **Inventory.** The decision `converted` is right: the deliverable is a file read by an artifact check, and no exclusion reason applies. The current note in `conversions/inventory.tsv` cites "lesson C58" and the old "no hidden case" framing. The coordinator may want to replace it with the note proposed under "Inventory note".

Upstream assertions. `test_hello_file_exists` (`exists()`) and `test_hello_file_content` (`read_text()` succeeds and `.strip()` equals the flag) are both checked by `answer`, as the map says. Every fidelity change has a label and a reason.

Findings:
- None. Both findings of the first review are fixed: the scope claim is corrected in `CONVERSION.md` and `task.toml`, and qualification has been rerun on the current pack.

Verdict: approved
