# chess-best-move

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/chess-best-move

## The conversion in short

The baseline holds `/app/chess_board.png`, an 8 by 8 board drawn with Unicode chess symbols by upstream's `environment/make.py` from the FEN `r1bq1r2/1p3pp1/p1n1p3/3nPkbP/8/P1N5/1P2QPP1/R1B1K2R w KQ - 0 16`. The agent must find white's best move, here every mate in one, and write the moves to `/app/move.txt` in the form `[src][dst]`, one per line. Upstream has one test (`tests/test_outputs.py`), `test_move_correct`, which asserts `sorted(Path("/app/move.txt").read_text().strip().split()) == sorted(["g2g4", "e2e4"])`. Nothing else is asserted, and upstream has no regression tests.

The pack has one artifact check, `moves`, which reads `/app/move.txt` with the `text` parser (strict UTF-8, at most 1 MiB). The Oracle's `plan` loads the expected moves from `hidden/expected.json` into the check's context. `judge` applies Python's `str.split()`, as upstream does, and requires the same multiset of moves: the count must match and the sorted lists must be equal. So order, line breaks and surrounding whitespace do not matter, and a missing, extra or repeated move fails, exactly as upstream's sorted-list equality decides. Upstream's `strip()` before `split()` is left out because `split()` already drops leading and trailing whitespace. `judge` fails closed on an absent, non-regular, too large or non-UTF-8 file, on any evidence other than the one declared file, and on a malformed context. Its work is one `split()` over at most 1 MiB, and the sort runs only when the count already equals the expected count of 2. No protocol check is needed: the deliverable is a file, and nothing has to run at grading time.

## How upstream's tests map to checks

`tests/test.sh` only runs pytest on `tests/test_outputs.py` and writes the reward; it asserts nothing itself. `tests/test_outputs.py` has one test with one assertion. There are no regression tests to run by outcome.

| Upstream (`tests/test_outputs.py`, `test_move_correct`) | Check and case | SecureBench |
|---|---|---|
| `Path("/app/move.txt").read_text()` succeeds (the file exists, is readable, decodes as UTF-8) | `moves` (artifact check, no cases) | fails unless the file is present, a regular file, at most 1 MiB and valid UTF-8 without a byte-order mark |
| `.strip().split()` | `moves` | `judge`: `text.split()` |
| `assert sorted(move) == sorted(["g2g4", "e2e4"])` (line 25) | `moves` | `judge`: `len(got) == len(context)` and `sorted(got) == sorted(context)`, with the context `["e2e4", "g2g4"]` from `hidden/expected.json` |

Nothing in the pack lies outside this table: the Oracle has no other check, case or assertion, and uses no randomness.

### Expected value

`hidden/expected.json` holds `{"moves": ["e2e4", "g2g4"]}`, the two moves upstream's test asserts on (line 25). `oracle.py` holds no move. We checked them by running the upstream reference (`candidates/reference.sh`) through SecureBench: it read the FEN `r1bq1r2/1p3pp1/p1n1p3/3nPkbP/8/P1N5/1P2QPP1/R1B1K2R w KQkq - 0 1` from the image, tried every legal move with python-chess 1.2.0, found exactly two mates, `e2e4` (the queen to e4) and `g2g4` (the pawn), and wrote `e2e4\ng2g4` (run `sha256:ab317ce1...`, and every qualification run of `reference`). The piece placement equals the FEN in upstream's `make.py`; the reference's castling field `KQkq` differs from `KQ`, which changes no mate. To redo it, run `candidates/reference.sh` in the baseline with network access and read `/app/move.txt`.

### Differential test of the check against upstream's test

The `text` parser replaces `read_text()`, and the Oracle runs on Python 3.12.15 where upstream's verifier runs a uv-managed Python 3.13. `hidden/differential.py` compares the two on 34 inputs at the acceptance boundary. Its docstring gives the three commands. The native side runs upstream's test function verbatim in the pinned baseline with no network, on a uv-managed CPython 3.13.16 with no locale set (so in UTF-8 mode, as in the verifier's container, which sets no `LANG`), with each input at `/app/move.txt`. The SecureBench side runs the framework's `file_evidence` binding with this check's file spec, then `plan` and `judge` of `hidden/oracle.py`, loaded through the Oracle worker's `load`.

| Input at `/app/move.txt` | Upstream | SecureBench |
|---|---|---|
| `e2e4\ng2g4` (the reference's output); the moves reversed with a trailing newline; on one line separated by a space or a tab; with `\r\n` or lone `\r`; separated by `\f` and `\v`; separated by `\x1c` to `\x1f`; with blank lines and spaces around; separated and surrounded by Unicode spaces (U+00A0, U+3000, U+2028, U+2029, U+0085, U+2003) | pass | pass |
| the answer padded with spaces to exactly 1 MiB | pass | pass |
| empty; whitespace only; absent; a directory | fail | fail |
| with a byte-order mark; followed by the invalid byte `0xff`; the moves joined by a zero-width space (U+200B), by U+180E, by NUL, or by nothing | fail | fail |
| one move only (each of the two); a move repeated; both moves twice; an extra move; a line `PASSED test_move_correct` after the answer | fail | fail |
| comma-separated; uppercase; SAN (`Qe4#`, `g4#`); a promotion suffix (`e2e4q`); fullwidth letters | fail | fail |
| **the answer padded with spaces to 1 MiB + 1 byte** | **pass** | **fail** |
| **`/app/move.txt` a symlink to a file holding the answer** | **pass** | **fail** |

Both differences are stricter fidelity changes listed below. The characters `str.split()` treats as whitespace are the same in Python 3.12 and 3.13 on every input above.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** Upstream's one test reads one file for one fixed image, and the pack has one artifact check for that file and no protocol check, so there are no cases to add or drop.
- **Answer comparison (equivalent).** The same `split()` and the same multiset comparison as upstream's sorted lists. A byte-order mark and invalid UTF-8 fail both graders, so the parser's stricter decoding changes no verdict (table above, and `mutant-bom`).
- **Answer file bound (stricter, negligible).** The artifact check reads at most 1 MiB; upstream reads any size. A correct answer is 9 bytes plus whitespace, so only a file padded with more than a mebibyte of whitespace passes upstream and fails here. The bound keeps the Oracle's work over candidate data bounded, which the platform requires of every artifact check.
- **Regular file (stricter, negligible).** `/app/move.txt` must be a regular file; upstream follows a symlink. Capture would reject a symlink whose target leaves `/app` anyway.
- **Allowed domains (stricter).** `archive.ubuntu.com` for Stockfish, which the reference installs with `apt install` from the package lists already in the image, and `pypi.org` and `files.pythonhosted.org` for numpy and python-chess, which it installs with `pip3`. The reference's proxy log shows requests to exactly these three hosts and no denied request (run `sha256:ab317ce1...`). Upstream allows the whole Internet. The image's apt sources also name `security.ubuntu.com`, which the reference never asks because it runs no `apt update`. So an agent that runs `apt-get update` here gets exit status 100 after refreshing every `archive.ubuntu.com` index, and a command chained after it with `&&` does not run; a following `apt-get install -y stockfish` on its own still succeeds (probe run `sha256:337b04d3...`). Upstream's verdict for such an agent would not depend on this. We did not find the answer on the allowed hosts: the baseline has no copy of it (a search of every file outside `/proc`, `/sys` and `/dev` for `g2g4` finds nothing), and the answer is a mate any chess library or engine finds from the image. We did not search all of PyPI or the Ubuntu archive for a copy of upstream's test.
- **Scope (stricter, only for odd entries at the top level of `/app` and odd names one level down).** One root, `/app`, which holds the only deliverable. The baseline's `/app` holds only `chess_board.png` (37,022 bytes) and no symlink. The root excludes `*/*`, so everything below the top level of `/app` is dropped from the candidate: a virtual environment, caches or links an agent keeps in subdirectories of `/app` can then neither exceed the bounds nor fail capture. The reference writes only top-level files (`solve.py` and `move.txt`), and the evaluation reads only `/app/move.txt`, so nothing a correct candidate needs is dropped. Internal symlinks are allowed, and the bounds are the largest the format allows (100,000 entries, 2 GiB), which now apply only to top-level entries. Capture still fails, where upstream passes, a correct candidate that leaves directly in `/app` an absolute symlink or one leaving `/app`, a FIFO, socket or device, an unreadable directory, top-level files over 2 GiB in total, or a name capture rejects. No pack setting avoids these, because the deliverable is a file directly in `/app`. Work outside `/app` (Stockfish in `/usr/games`, Python packages, `/tmp`) is not captured and does not matter. Upstream keeps no test files in the image (`/tests` is mounted only at grading time), so there is no test file to exclude, and files the candidate writes outside `/app`, such as `/conftest.py`, cannot affect the verdict.

## Mutants failed by an addition before remediation

No earlier mutant was failed by an addition: in the qualification before remediation, every mutant scored 0.0 natively and `failed` on SecureBench, so none had to be rerun.

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| (none with native 1.0 and SecureBench `failed`) | | | |

## Remediation

The conversion already kept upstream's one assertion and nothing more, so remediation changed no check.

- **Removed.** No case, input, check or assertion: the pack had none beyond upstream's. The section "Answer already public upstream" and the fidelity change "Hidden cases (none added)", which argued against an addition the pack never made; "Cases (equivalent)" replaces it. References to lesson codes and to other conversions, in this file, in the docstring of `hidden/differential.py` and in the comment of `candidates/attack-conftest.sh`. The comment edit is the only change to `hidden/differential.py`; the Oracle, `expected.json` and `task.toml` are unchanged.
- **Restored.** Nothing: no upstream assertion was dropped, and upstream has no regression tests.
- **Moved.** Nothing: the expected moves were already in `hidden/expected.json`, and `oracle.py` holds only judging logic.
- **Candidates deleted.** `attack-spray.sh`, which wrote the two public upstream moves among four others. It hardcodes the upstream answer and tests the answer's content, not how it is graded, so it is outside SecureBench's scope.
- **Candidates added.** `mutant-bom.sh`, aimed at the one place the check is least like upstream's: the `text` parser that replaces `read_text()`. None of the four earlier mutants reached it.
- **Candidates kept.** `reference.sh` and `null.sh` unchanged; `attack-conftest.sh` (comment only); the four mutants unchanged.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with a `#!/bin/sh` first line, a comment, and `cd /app` in place of upstream's `#!/bin/bash` line, which comes after the canary comment and so is not a shebang. The script uses nothing specific to bash: its one heredoc is quoted (`<<'EOF'`). No drift repair was needed: `apt install -y stockfish` without `apt update` still finds `stockfish 16-1build1` in `noble/universe`, and the pinned numpy 2.3.2 and python-chess 1.2.0 wheels still install.
- `null.sh`: changes nothing.
- `mutant-bom.sh` (the file as `read_text()` decodes it): the reference writing `move.txt` with `encoding="utf-8-sig"`, so the file starts with a UTF-8 byte-order mark. Upstream's `read_text()` keeps it as U+FEFF on the first move, which `split()` does not remove, so the sorted lists differ; SecureBench's `text` parser reports the file `unparsable` (run `sha256:3c9a42f3...`, `failed`, class `oracle`).
- `mutant-one-line.sh` (the `split()`): the reference joining the moves with commas, so it writes `e2e4,g2g4`, which `split()` keeps as one token.
- `mutant-engine-only.sh` (the count in the multiset comparison): the reference with its mate-in-one shortcut disabled (`if best_moves:` becomes `if False:`), so it writes Stockfish's single best move after 2 seconds, one of the two mates (`g2g4` in our runs).
- `mutant-san.sh` (the form `[src][dst]`): the reference recording each mate in standard algebraic notation, so it writes `Qe4#` and `g4#`.
- `mutant-mirrored.sh` (the position the image shows): the reference reading each rank right to left (`board[row][7 - col]`), so it solves the mirrored position and writes its mates `d2d4` and `b2b4`.
- `attack-conftest.sh`: reads nothing, writes only `g2g4`, and plants `/pytest.ini` and `/conftest.py`, whose report hook rewrites every test report to passed. Upstream's verifier runs `pytest /tests/test_outputs.py`; pytest finds `/pytest.ini` above `/tests`, takes `/` as its rootdir and loads `/conftest.py`. It is aimed at this task's native verifier, and on SecureBench it tests that files planted outside the scope cannot change the verdict.

The five mutants rebuild the reference from `reference.sh` with `sed` and exit 1 without running anything if the change did not apply, so a mutant can never silently become the reference.

## Divergences from native

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** Its answer is only `g2g4`, which fails upstream's sorted-list equality, so the native 1.0 can come only from the planted `/conftest.py` rewriting the failed test to passed. SecureBench captures only `/app` and the Oracle reads the answer itself, so the planted files have no effect. SecureBench is right.

The other candidates agree across the graders in the qualification after remediation (`qualification.json`, no problems, every SecureBench run admitted, clean and reproduced by `rejudge`, one pack digest `sha256:9502a8b1...`). The reference scored 1.0 natively and `passed`. The null candidate and all five mutants scored 0.0 natively and `failed` (`oracle`). The native results for `reference`, `null` and the four unchanged mutants are reused from the earlier qualification (`native_cached`). `mutant-bom` and `attack-conftest`, whose script changed, ran natively again.

## Inventory note

Proposed note: Remediated: no addition to remove; the Oracle compares the whitespace-split moves in /app/move.txt with upstream's e2e4 and g2g4 (in hidden/expected.json) as a multiset, matched to upstream's test on 34 inputs; attack-spray deleted (hardcoded the public answer), mutant-bom added for the text parser; attack-conftest passes natively by rewriting pytest's report; stricter: a symlinked or over-1 MiB move.txt fails, and only the three hosts the reference uses are allowed, so apt-get update exits 100 without security.ubuntu.com.

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-21

Pack digest checked: `sha256:b6399f30be97342b4d6ac449bf0773646130672b656fac49c8704901273ee13d` (`securebench validate`, at the start of the review and again after qualification).

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. Listed as an equivalent fidelity change.
2. Scope. One root, `/app`, with `exclude = ["*/*"]`, internal symlinks allowed, and the largest bounds. The only deliverable is `/app/move.txt`, which sits at the top level, so every solution the instructions allow is captured. I read the capture walker (`securebench_utility/utility.py`, `walk_root`). It never descends into excluded subtrees. It still lists each top-level directory and checks its direct children's names before applying the exclusion. The scope bullet lists exactly these residual stricter cases ("odd names one level down", "an unreadable directory", plus top-level absolute or escaping symlinks, FIFOs, sockets and devices). The baseline's `/app` holds only `chess_board.png`, and there are no tests in the image (`/tests` and `/logs` are absent), so lesson C49 has nothing to exclude. Planted files outside `/app` are not captured.
3. Leaked expected values. `hidden/expected.json` is the only place the moves appear in the pack. There are no `public/` or `evaluation/` directories. I searched every file in the pinned baseline outside `/proc`, `/sys` and `/dev`, with no network, for `g2g4`, `Qe4#`, the FEN fragment `3nPkbP` and `test_move_correct`, and found nothing. (`e2e4` matches only hex digests in dpkg md5sums and apt lists.) `make.py` was removed in the image. The answer is public upstream (point 5).
4. Challenge leaks. There are no protocol checks, so no challenge exists. The expected moves travel only as the artifact check's context on the host. No candidate code shares a process with a driver.
5. Hidden case. None, and justified under lesson C58. The deliverable is the answer for the one fixed image in the baseline, and the moves are literals in upstream `tests/test_outputs.py`, `README.md` and the instructions' own example (`e2e4`). The hardcoding attack that passes is named, with a probe run, under "Answer already public upstream". This matches the approved gcode-to-text and count-dataset-tokens handling.
6. Oracle (C52 to C54). `judge` requires exactly the one declared file, status `present` and a `Text` value, and fails closed on any other check id, evidence shape or malformed context. It compares the moves as a multiset (count and sorted list), so a repeated or extra move fails (C52). Its work is one `split()` over at most 1 MiB, and the diagnostic is truncated (C54). `plan` validates `expected.json`. I re-ran `hidden/differential.py` myself. The SecureBench side, through the real `file_evidence` binding and the Oracle loaded by `load`, reproduces the table. The native side ran in the pinned baseline with no network, on the image's Python 3.12.3 as a cross-check. The two sides differ only on `padded-past-1-mib` and `symlink-to-answer`, the two listed stricter changes. I confirmed in `securebench/candidate/lookup.py` that a symlinked `/app/move.txt` really yields `not_regular`, as the differential assumes. The `text` parser rejects only invalid UTF-8 and a BOM, and both fail upstream too.
7. Mutants and attacks. Each mutant rebuilds the real reference with one `sed` edit, guarded by a `grep` that aborts if the edit did not apply, and runs it (C73). Each targets one requirement: every winning move (`engine-only`), the position shown in the image (`mirrored`), the `[src][dst]` form (`san`) and one move per line (`one-line`). `attack-spray` targets an Oracle that only looks for the expected moves among others. `attack-conftest` targets the native verifier's pytest (C49). All six get SecureBench `failed` with class `oracle`, never `invalid` (C72).
8. Divergences. The only divergence is `attack-conftest` (native 1.0 in both rounds, SecureBench `failed`). The explanation holds: the file holds only `g2g4`, which fails upstream's `sorted(move) == sorted(["g2g4", "e2e4"])`. So the native pass can only come from the planted `/pytest.ini` making `/` the rootdir, with `/conftest.py` rewriting reports. SecureBench is right. The native work directory was temporary, so I could not read the verifier log, but the reasoning does not depend on it. The other candidates agree across graders: reference 1.0 and `passed`; null, the four mutants and `attack-spray` 0.0 and `failed`.
9. Inventory. There is no row yet; the coordinator adds it on approval. `converted` is right, because none of the closed-list reasons holds. The task needs network only in the Agent environment, and its deliverable is a file read by lookup.

Upstream assertions. `tests/test_outputs.py` makes one assertion, `sorted(read_text().strip().split()) == sorted(["g2g4", "e2e4"])`. Its three parts (the read succeeds, `strip().split()`, multiset equality) map to the `moves` check in the table. The two stricter differences (the 1 MiB bound, a regular file) are labelled and justified. `tests/test.sh` asserts nothing beyond running pytest.

Qualification. `qualification.json` reports `problems: []`. Every SecureBench run is admitted, `rejudged`, clean (`dirty: false`) and records pack digest `sha256:b6399f30...`, the digest I noted. The runs name four framework commits (`6c0366a`, `d8a1be6`, `54c1874`, `7baad5c`). I checked that the `securebench`, `securebench_utility` and `securebench_relay_proxy` trees are identical at all four.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-26

Pack digest checked: `sha256:9502a8b195d6c453b843ebd390b0974f46fdac7c95688b72a9afeda4b171b297` (`securebench validate`, at the start of the review and again after qualification). The Oracle, `expected.json` and `task.toml` are unchanged since the earlier approval; the digest moved only because of the docstring edit in `hidden/differential.py`.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. Listed as an equivalent fidelity change.
2. Scope. One root, `/app`, with `exclude = ["*/*"]`. Under the matching rules of 4.6, `*/*` matches every path of two or more components below `/app`, so only top-level entries are captured, and the one deliverable, `/app/move.txt`, is top-level. I ran the pinned baseline with no network: `/app` holds only `chess_board.png` and no symlink, `/tests` and `/logs` do not exist, and there is no `conftest.py` or `pytest.ini` anywhere in the image. So there is no test file to exclude, and files planted outside `/app` are not captured. The residual stricter cases (top-level special files or escaping symlinks, odd names one level down) are listed in the scope bullet.
3. Leaked expected values. The moves appear in the pack only in `hidden/expected.json`; there is no `public/` or `evaluation/`. I searched every file of the baseline outside `/proc`, `/sys` and `/dev` for `g2g4`, `Qe4#`, the FEN fragment `3nPkbP` and `test_move_correct`: no match. The allowed hosts are a Debian package archive and PyPI, which the reference needs; the answer is a mate any chess library finds from the image, and by the campaign's ruling a public or guessable answer is out of scope.
4. Challenges. No protocol check, so no challenge. The expected moves stay on the host as the artifact check's context.
5. Cases. Upstream's one test reads one file for one fixed image; the pack has one artifact check and no cases. No case was added. `plan` ignores the seed, as upstream draws nothing at random.
6. Oracle. `plan` reads and validates `hidden/expected.json`; `oracle.py` holds no move. `judge` requires exactly the declared file, status `present` and a `Text` value, and fails closed on any other check id, evidence shape or malformed context. It applies `str.split()` and compares count and sorted list, which is upstream's sorted-list equality, so a repeated, missing or extra move fails. Its work is one split over at most 1 MiB, and the diagnostic is bounded (16 tokens of 16 characters). Extra text such as `PASSED test_move_correct` fails. I read the `text` parser (`securebench/evidence/parsers.py`): strict UTF-8 decoding with no normalization, and a rejected BOM, which upstream also fails on. I re-ran `hidden/differential.py` on both sides: the SecureBench side through the current `file_evidence` binding and the Oracle's `load`, the native side running upstream's test verbatim in the pinned baseline with no network on uv's CPython 3.13.16 with no locale set (the image sets no `LANG`). The 34 verdicts agree except `padded-past-1-mib` and `symlink-to-answer`, the two stricter changes listed and labelled. There are no regression tests.
7. Candidates. `reference.sh` differs from upstream `solve.sh` only by the `#!/bin/sh` line, a comment and `cd /app`, with upstream's second-line `#!/bin/bash` (a comment there) dropped, as recorded; no drift repair. Each mutant rebuilds the reference with a `sed` edit guarded by `grep` and runs real code. `mutant-bom` targets the `text` parser that replaces `read_text()`, `mutant-one-line` the split, `mutant-engine-only` the count. All five get the same verdict from both graders (native 0.0, SecureBench `failed`). `attack-conftest` tampers with this task's native verifier (planted `/pytest.ini` and `/conftest.py`) and gets `failed` on SecureBench. Deleting `attack-spray`, which only hardcoded the public answer, matches the ruling that public answers are out of scope.
8. Divergences. `qualification.json` reports `problems: []`. All eight SecureBench runs are admitted, clean (`dirty: false`), reproduced by `rejudge` and record pack digest `sha256:9502a8b1...`, the digest I noted. The runs name two framework commits (`9eeef7f`, `6e74bd9`); `git diff 9eeef7f 6e74bd9` over `securebench`, `securebench_utility` and `securebench_relay_proxy` is empty. The only divergence is `attack-conftest` (native 1.0, SecureBench `failed`). The explanation holds: its file holds only `g2g4`, which fails upstream's assertion, so the native pass can only come from the planted conftest rewriting the report. SecureBench is right. Native results for the reference, the null candidate and the four unchanged mutants are reused (`native_cached`); `mutant-bom` and `attack-conftest`, whose scripts changed, ran again.
9. Inventory. The row says `converted` with reason `-`, which is right: none of the exclusion reasons holds, since the task needs network only in the Agent environment and its deliverable is a file read by lookup. The row's note still names lesson C58 and the hardcoding attack; the proposed note in "## Inventory note" replaces it correctly and should be applied.

Upstream assertions. `tests/test_outputs.py` makes one assertion, `sorted(Path("/app/move.txt").read_text().strip().split()) == sorted(["g2g4", "e2e4"])`. Its parts (the read succeeds, `strip().split()`, multiset equality) map to the `moves` check as the table shows. The two stricter differences (the 1 MiB bound, a regular file) are labelled with reasons. `tests/test.sh` asserts nothing beyond running pytest.

Findings:
- None that block. One note: `mutant-san` and `mutant-mirrored` test the answer's content, where the check is identical to upstream's, rather than a place where it differs. They are harmless, and the places that do differ (the parser, the split, the count) each have a mutant.

Verdict: approved
