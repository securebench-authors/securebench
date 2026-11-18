# feal-linear-cryptanalysis

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/feal-linear-cryptanalysis

## The conversion in short

Upstream has one test, `test_attack`. It reads `/app/plaintexts.txt` as text and asserts, for each of 100 decimal plaintexts written as a literal (`soln`) in the test, that the value occurs in the file as a substring. Nothing else is asserted: order, separators and any extra text are free.

The pack has one artifact check, `plaintexts`, which reads `/app/plaintexts.txt` with the `text` parser (at most 1 MiB). The Oracle's `plan` loads the expected plaintexts from `hidden/expected.json` into the check's context, and `judge` asserts that each one occurs in the text as a substring, with Python's `in` on `str`, the same operation upstream uses. It fails closed on an absent, non-regular, too large or non-UTF-8 file, on any evidence other than the one declared file, and on a context that is not a non-empty list of distinct ASCII digit strings. Its work is one substring search over at most 1 MiB per expected value. No protocol check is needed, because the deliverable is a file and nothing has to run at grading time.

## How upstream's tests map to checks

Upstream's only test file is `tests/test_outputs.py`, with one test, `test_attack`. `tests/test.sh` installs its tools, checks that the image sets a working directory (a property of the image, `WORKDIR /app`, not of the candidate) and runs pytest; it asserts nothing about the candidate. Upstream has no regression tests.

| Upstream assertion (`tests/test_outputs.py::test_attack`) | Check and case | How it is checked |
|---|---|---|
| `open("/app/plaintexts.txt").read()` succeeds | artifact check `plaintexts`, file `/app/plaintexts.txt` | `judge` fails unless the file is `present` (regular, at most 1 MiB, valid UTF-8 without a byte-order mark) |
| `assert c in data` for each `c` in `soln.split()` (100 values) | artifact check `plaintexts` | `judge` checks `value in text` for each of the 100 values of `hidden/expected.json`, which are `soln.split()` in the same order; the diagnostic lists the indices of the missing ones |

There is nothing in the pack that no upstream assertion accounts for.

### Expected values

`hidden/expected.json` holds the 100 values of `soln.split()`, in that order, which is also the order of `/app/ciphertexts.txt`. `hidden/derive.py` regenerates it. It recomputes the plaintexts the way upstream `environment/task-deps/gen.py` does at image build time (SHA-256 of the key string, then SHA-256 with a counter), and fails unless all of these hold:

- a Python port of `feal.c` encrypts each of the 32 known plaintexts of `/app/pairs.txt` to its known ciphertext, so the port matches the image's cipher;
- the port encrypts plaintext i to line i of `/app/ciphertexts.txt` and decrypts line i back to plaintext i;
- the derived set equals the 100 values upstream's test asserts on.

To redo it, copy `/app/pairs.txt` and `/app/ciphertexts.txt` out of the pinned baseline and run `python3 -I task/hidden/derive.py pairs.txt ciphertexts.txt <upstream>/tests/test_outputs.py`. Independently, the image's own `/app/decrypt` run on `/app/ciphertexts.txt` with the upstream keys `0x68e63 0x62571 0x1f61c 0xb74a5` prints exactly the 100 values of `expected.json`, in the same order.

### Differential test of the text parser against upstream's `open().read()`

The Oracle reimplements no native tool, but the text parser decodes the file differently from upstream's `open().read()`, so we compared the two on 17 files built around the acceptance boundary. The native side ran upstream's `test_attack` with the baseline's Python 3.13.7 on each file as `/app/plaintexts.txt`; the SecureBench side ran the framework's own `file_evidence` binding (the code that makes the Oracle's evidence) and then `judge`.

| File | Upstream | SecureBench |
|---|---|---|
| the 100 values, one per line | pass | pass |
| same, CRLF line endings | pass | pass |
| same, CR line endings | pass | pass |
| same, reversed order | pass | pass |
| same, NUL bytes as separators | pass | pass |
| same, each with a leading `0` | pass | pass |
| all 100 concatenated with no separator | pass | pass |
| the values among extra text and a `PASSED` claim | pass | pass |
| padded with spaces to exactly 1 MiB | pass | pass |
| 99 values | fail | fail |
| 99 values and the last one missing its final digit | fail | fail |
| 99 values and the last one split by a newline | fail | fail |
| the values in hexadecimal | fail | fail |
| valid answer followed by a byte `0xff` (invalid UTF-8) | fail | fail |
| empty | fail | fail |
| valid answer preceded by a UTF-8 byte-order mark | pass | **fail** |
| valid answer padded to 1 MiB + 1 byte and more | pass | **fail** |

The two differences are the fidelity changes listed below as stricter. Two mutants, `mutant-crlf-output` and `mutant-unseparated-output`, repeat the CRLF and no-separator rows with the real attack in both graders.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** One artifact check over exactly upstream's 100 values, none added and none removed.
- **Answer file bound (stricter).** The artifact check reads at most 1 MiB, so a file larger than that fails even if it holds every plaintext. Upstream reads any size. An answer is about 2 KiB (the reference's, with its debug lines, is under 10 KiB); the bound keeps the Oracle's work over candidate data bounded, since the Oracle runs on the host.
- **Byte-order mark (stricter).** The `text` parser rejects a file that starts with a UTF-8 byte-order mark, so such a file fails. Upstream decodes it as a `U+FEFF` character and still finds the values. Any other valid or invalid UTF-8 is treated the same by both (table above).
- **Line endings (equivalent).** Upstream's text mode turns CR and CRLF into LF; the `text` parser keeps them. The values are digit strings, so this changes no substring match (table above, and `mutant-crlf-output`).
- **Allowed domains (stricter).** None, which is all the reference needs: it compiles with the baseline's gcc and runs the baseline's `/app/decrypt`. Upstream allows the Internet, so an agent there could install packages or tools; here it has only what the image ships (gcc, Python 3.13).
- **Scope (equivalent).** One root, `/app`, which holds the only deliverable. Internal symlinks are allowed, because a correct agent may create them in its own work files. Upstream keeps no test files in the image (they are mounted at `/tests` only at grading time), so there is nothing to exclude. Files the candidate writes outside `/app`, such as `/conftest.py`, are not captured and cannot affect the verdict.
- **Symlinked answer file (stricter).** `/app/plaintexts.txt` must be a regular file. If it is a symlink to a correct answer (for example to `/app/out.txt`), the artifact check reads it by lookup without following the link and reports it `not_regular`, so the check fails. Upstream's `open()` follows the link and passes. This difference is our choice. Replay keeps internal symlinks (`symlinks = true`), so a protocol check whose adapter opens `/app/plaintexts.txt` in the Evaluation would follow the link and pass such a candidate. Only a link that leaves the scope would fail under any conversion, because capture rejects it. We chose the artifact check for two reasons. It starts no environment and runs nothing from the candidate. And the instructions ask for the answer to be saved "in the file /app/plaintexts.txt", so a regular file is the natural reading.
- **Scope bounds (stricter).** A candidate with more than 10,000 entries or 256 MiB under `/app` fails capture. Upstream bounds the candidate only by its 10 GiB disk. Capture walks and stores the candidate's tree, so it needs some bound. These bounds are far above what the task needs: the baseline `/app` holds 6 files (44 KB), and after the reference it holds 9 files (79 KB). A correct agent fails only if it leaves very large work files inside `/app` instead of `/tmp`.
- **Unreadable files under `/app` (stricter).** Capture fails, with class `capture`, on any file under `/app` it cannot read, so a candidate with the correct answer and one mode-000 file in `/app` (or a mode-000 `plaintexts.txt`) fails SecureBench. Natively the verifier runs as root, reads any mode and looks only at `plaintexts.txt`, so it passes. Capture reads the candidate's tree without overriding file permissions, because Evaluation environments and capture keep no capability to do so, and replay keeps no permission bits other than the executable bit anyway. A correct agent fails only if it removes read permission from a file it leaves in `/app`.

## Divergences from native

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** It recovers nothing and writes only the 32 known plaintexts of `pairs.txt` to `/app/plaintexts.txt`. It also writes `/pytest.ini` and `/conftest.py`. Upstream runs `pytest /tests/test_outputs.py`; pytest looks for an ini file from `/tests` upwards, finds `/pytest.ini`, takes `/` as its rootdir and conftest boundary, and loads `/conftest.py`, whose report hook rewrites the failed `test_attack` to passed. The native verifier log of the qualification run before remediation shows `rootdir: /`, `configfile: pytest.ini` and `1 passed`. SecureBench captures only `/app`, and the Oracle reads the answer file itself, so the planted files have no effect and the missing plaintexts fail the check. SecureBench is right: no ciphertext was decrypted.

No other candidate diverges. The reference passes and the null candidate fails both graders. `mutant-crlf-output` and `mutant-unseparated-output` pass both (native 1.0, SecureBench `passed`). The other three mutants and `attack-claim-pass` fail both. The native results of the seven unchanged candidates are reused from the qualification before remediation (`native_cached`); the two new mutants ran natively.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with `cd /app` added, a `#!/bin/sh` first line and a comment naming the source, and without upstream's second line `#! /bin/bash`. That line follows the canary comment, so it was never a shebang, only an inert comment; both graders run the candidate as a POSIX `sh` script, which the new first line states. The script body is unchanged. Its linear attack recovers round keys 0 to 2, brute-forces round key 3, and runs `/app/decrypt`.
- `null.sh`: changes nothing.
- `mutant-no-last-round-key.sh` (key recovery): the reference without the search for the last round key, so key 3 stays 0. Finds 0 of 100.
- `mutant-reversed-keys.sh` (decryption): the reference passing the recovered keys to `./decrypt` in reverse order. Finds 0 of 100.
- `mutant-skip-last-ciphertext.sh` (every value is checked): the reference decrypting only the first 99 ciphertexts. Finds 99 of 100.
- `mutant-crlf-output.sh` (the text parser keeps CR where upstream's text mode drops it): the reference writing its output with CRLF line endings. Upstream accepts it, so SecureBench must too.
- `mutant-unseparated-output.sh` (the Oracle's substring search): the reference with every newline dropped, so the debug lines and the values run together. Upstream's substring test accepts it, so the Oracle must not split the file into lines or numbers.
- `attack-conftest.sh`: aimed at this task's native grader; above.
- `attack-claim-pass.sh`: an answer file that names the keys, claims `test_attack PASSED`, and lists the 32 known plaintexts and the 100 ciphertexts, without decrypting anything. It checks that the Oracle ignores claims of success.

The mutants rebuild the reference from `reference.sh` with one `sed` substitution each, and exit 1 without running anything if the line they change is not there, so a mutant can never silently become the reference.

## Remediation

This conversion was remediated on 2026-10-24 against the current converter brief. It already tested exactly upstream's 100 values with upstream's substring operation, so there were no added cases, inputs, randomness or stricter assertions to remove, and no dropped assertion to restore.

- **Removed.** From `hidden/oracle.py`, the constant `COUNT = 100`, which `_expected` used to require exactly 100 context values. The number of values is a property of the expected data, which now lives only in `hidden/expected.json`; the Oracle requires a non-empty list of distinct ASCII digit strings. From this record, the section "Answer already public upstream" and the "Hidden cases" fidelity bullet, which discussed cases the current brief does not ask for.
- **Restored.** Nothing: the map above accounts for every upstream assertion, and upstream has no regression tests.
- **Moved.** Nothing else: the expected values were already in `hidden/expected.json`, and the task has no challenges.
- **Candidates.** None deleted. `attack-conftest` tampers with the native grader's pytest run and is aimed at this task; `attack-claim-pass` tries to win by claiming a verdict and decrypts nothing, so both tamper with grading rather than hardcoding an answer. The three old mutants aim at the task's real work. Added `mutant-crlf-output` and `mutant-unseparated-output`, the places where the check is least like upstream's assertion (the text parser's line endings and the Oracle's substring search), which the brief asks a mutant for and the old set did not cover.

Old mutants that caught an addition (native pass, SecureBench `failed`) in the qualification before remediation:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| none | | | |

All three old mutants had native 0.0 and SecureBench `failed` (`oracle`), so none was failed by an addition, and none was run for this step. They run again in the new qualification.

## Inventory note

Proposed row: `terminal-bench	feal-linear-cryptanalysis	converted	-	Remediated 2026-10-24: one artifact check over exactly upstream's 100 values; the answer is a literal in the public upstream test, which is outside SecureBench's scope.`

## Review before remediation

Reviewer: a89e32c86fc642304 (conversion-reviewer, Claude Opus 5.5), 2026-10-06

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope. The instructions name one deliverable, `/app/plaintexts.txt`, and the root `/app` covers it. The baseline `/app` holds only `feal.c`, `decrypt.c`, `feal`, `decrypt`, `pairs.txt` and `ciphertexts.txt`, with no symlinks (lesson A16) and no test files: upstream mounts its tests at `/tests` only at grading time (C49). No exclusions, so A14 and A15 do not apply. One case where a correct solution fails is not labelled stricter (first finding).
3. Expected values. They are only in `hidden/expected.json`, and no pack file outside `hidden/` holds any. I pulled the pinned digest (it equals what the `20251031` tag resolves to today) and searched its whole final filesystem for the first and last expected values: no match. The Oracle never reads `/app/ciphertexts.txt` or any other file the delta can change (C48). I re-ran `hidden/derive.py` on `pairs.txt` and `ciphertexts.txt` copied from the image myself, and its output is byte-identical to `expected.json`. The image's own `/app/decrypt` with the upstream keys prints the same 100 values in the same order, and they also equal upstream's `soln` in that order. Earlier layers of the public image still hold `app/gen.py` (with the keys) and `app/orig_plaintexts.txt`. I confirmed this with `docker image save`, and the files are hidden by whiteouts in later layers. A candidate cannot reach them from inside its environment, but they are one more public place where the answer appears (third finding).
4. Challenges. The task has no protocol check and so no challenge. The context, the 100 expected values, stays on the host.
5. Hidden cases. The 32 pairs in `pairs.txt` are known-plaintext input and do not show the deliverable. The answer is a literal in the public upstream test, and the 100 ciphertexts are fixed in the baseline. The instructions name no program the Evaluation could rerun on fresh pairs. So I agree that C58 applies and that no hidden case could stop a candidate that hardcodes the published answer. `CONVERSION.md` says so and records that the hardcoding script passes SecureBench.
6. Oracle (C52 to C54). The only required field is the file, and `judge` requires exactly that one declared path, with status `present` and a `Text` value. It fails closed on absent, not regular, too large, unparsable, a wrong check or malformed context. The context must be 100 distinct ASCII digit strings, so one repeated correct value cannot stand in for several (C52). The work is bounded: 100 substring searches over at most 1 MiB. No regular expression, no evidence used as a path, no side effects. `securebench validate` reports the pack valid. The diagnostic lists only indices, not values. The text parser (`securebench/evidence/parsers.py`) is strict UTF-8 without a byte-order mark and keeps `\r`. Its only difference from upstream's `open().read()` that can change a verdict is the byte-order mark, which is listed as stricter.
7. Mutants and attacks. Each mutant rebuilds and runs the real attack with one guarded `sed` change, so they run real code (C73). `no-last-round-key` targets key recovery, `reversed-keys` targets decryption and `skip-last-ciphertext` targets "all the ciphertexts". The last one finds 99 of 100, which shows that every value is checked. `attack-conftest` hits this task's real weakness on native, a pytest rootdir taken over through `/pytest.ini`, and it passes natively. `attack-claim-pass` covers C56. All get `failed` with class `oracle`, never `invalid` (C72). The qualification pack digest equals the digest of the current pack (I recomputed it with `taskspec.load.pack_digest`), and `problems` is empty.
8. Divergences. There is one: `attack-conftest` gets native 1.0 and SecureBench `failed`. The explanation holds. pytest looks for an ini file from `/tests` upward and finds `/pytest.ini`, so `/` becomes the rootdir and conftest boundary and `/conftest.py` is loaded. SecureBench captures only `/app` and reads the answer file itself. SecureBench is right.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet, and none for any other task either. The converting brief forbids the converter to edit it, so this is for the coordinator: the row should be `terminal-bench	feal-linear-cryptanalysis	converted`. The task is fifth in `campaign.py order terminal-bench`, within the selection order.

Upstream assertions: `test_outputs.py::test_attack` opens `/app/plaintexts.txt`, which maps to the artifact check's file status. Its `assert c in data` for each value of `soln` maps to `judge`'s `value in text` over the same 100 values. `test.sh` checks only that a working directory is set, which is a property of the image (`WORKDIR /app`), and installs its tools. It makes no assertion about the candidate. Nothing is dropped.

Findings:
- `CONVERSION.md`, "Fidelity changes", Scope bullet: two stricter differences sit inside a bullet labelled "equivalent". (a) An `/app/plaintexts.txt` that is a symlink to a correct answer fails SecureBench, while upstream's `open()` follows it and passes. I confirmed this with a probe run: the answer is decrypted to `/app/out.txt` and `plaintexts.txt` is a symlink to it, and SecureBench reports `failed`, `oracle`, "/app/plaintexts.txt is not_regular". (b) A candidate over 10,000 entries or 256 MiB in `/app` fails, where upstream has no such bound. Both make some correct candidates fail, so each needs its own bullet labelled stricter, with its reason, as `train-fasttext` does for its symlinked deliverable.
- `CONVERSION.md`, "Fidelity changes", Hidden cases bullet: it carries no stricter, more lenient or equivalent label. Keeping exactly upstream's cases is equivalent, so the bullet should say so, or the point should move to "Answer already public upstream".
- `CONVERSION.md`, "Answer already public upstream": the section should also name the published baseline image. Its earlier layers contain `app/gen.py` with the keys and `app/orig_plaintexts.txt` with the answer (added by Dockerfile lines 8 and 11, and hidden only by the `rm` layers of lines 13 and 14). This does not change the verdict, because the files are not reachable inside the environment and the answer is already public in the test.

Verdict: changes needed

## Review 2 before remediation

Reviewer: a89e32c86fc642304 (conversion-reviewer, Claude Opus 5.5), 2026-10-06

Only `CONVERSION.md` changed since review 1. The pack still validates, and its digest is still `sha256:8744c11a…096d896a`, the digest every run in `qualification.json` records. So the qualification and the results of review 1 for the pack and the candidates still apply.

1. Instructions. Unchanged and identical to upstream (`cmp`).
2. Scope. The Scope bullet is now limited to what is equivalent. The symlinked answer file and the scope bounds each have their own bullet labelled stricter, with a reason. The figures in the bounds bullet are plausible: the baseline `/app` holds 6 files, and the reference adds `attack.c`, `attack` and `plaintexts.txt`, for 9. The reason given in the symlink bullet is partly wrong (finding below).
3. Expected values. Unchanged from review 1.
4. Challenges. There are none.
5. Hidden cases. The bullet is now labelled equivalent, and the C58 section shows the hardcoding script.
6. Oracle. Unchanged from review 1.
7. Mutants and attacks. Unchanged from review 1.
8. Divergences. Unchanged, and the explanation still holds.
9. Inventory. The row is for the coordinator, as before.

All three findings of review 1 are addressed. The image layers are now named in "Answer already public upstream", with the right Dockerfile lines.

Findings:
- `CONVERSION.md`, "Fidelity changes", Symlinked answer file bullet: the sentence "The framework never follows a candidate's symlink when it reads evidence, so no conversion of this answer-file task can avoid this" is not true. Replay keeps internal symlinks (architecture Section 5.2), and the scope sets `symlinks = true`. So a protocol check whose adapter opens `/app/plaintexts.txt` in the Evaluation would follow a link to `/app/out.txt` and pass such a candidate, as upstream does. Only a link that leaves the scope fails under every conversion, because capture rejects it (Section 5.3). The difference comes from choosing an artifact check, which reads by lookup, over a protocol check. The bullet should say that this is a choice and give the reason for it. For example: the artifact check starts no environment and runs nothing from the candidate, and the instructions ask for "the file /app/plaintexts.txt". It should not present the difference as unavoidable. The label, stricter, is correct. This is a wording fix to the record, with no change to the pack.

Verdict: changes needed

## Review 3 before remediation

Reviewer: a89e32c86fc642304 (conversion-reviewer, Claude Opus 5.5), 2026-10-06

Since review 2, only the "Symlinked answer file" bullet changed. The pack still validates, and its digest is still `sha256:8744c11a…096d896a`, the one `qualification.json` records. Points 1 to 9 are as in review 2.

The bullet now says that the difference is a choice. It says that a protocol check would follow an internal link, and that only a link leaving the scope fails under every conversion. It gives two reasons for choosing the artifact check: it runs nothing from the candidate, and the instructions name "the file /app/plaintexts.txt". This agrees with architecture Sections 5.2 and 5.3, and the label, stricter, is correct. This resolves the finding of review 2.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-24 (second pass, after the converter addressed the first pass's two findings)

Pack digest under review: `sha256:b816e3805590d29369fc8dcdf3e7c83dc2d1d6d4d773b8c2856287b3ede76ad6`. It is the same digest as in the first pass and the one every SecureBench run in `qualification.json` records. Since the first pass only `CONVERSION.md` changed; `task/` and `candidates/` did not (the `reference.sh` diff against upstream is the same as before).

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope. One root, `/app`, which holds the only deliverable. The pinned baseline's `/app` holds `ciphertexts.txt`, `decrypt`, `decrypt.c`, `feal`, `feal.c` and `pairs.txt`. It has no symlinks and no test files. Upstream mounts its tests at `/tests` only at grading time, and the Oracle runs nothing from the candidate, so no convention-loaded file can affect the verdict. There are no exclude patterns. Four bullets cover the scope's stricter differences, each labelled stricter with a reason: the symlinked answer file, the scope bounds, and now unreadable files under `/app` (line 69). The new bullet matches what I probed: a correct answer plus a mode-000 work file, or a mode-000 `plaintexts.txt`, fails capture. Its reason holds: containers start with `--cap-drop ALL` (`securebench/isolation/docker.py`), and replay keeps only the executable bit.
3. Expected values. They are only in `hidden/expected.json`, and the pack has no `public/` or `evaluation/`. A search of the whole baseline filesystem for the first, fifteenth and last expected values found nothing. `expected.json` equals `soln.split()` of upstream's test, in order: 100 distinct values. The answer is a literal in the public upstream test, which is out of scope. No domain is allowed.
4. Challenges. None. The task has only an artifact check, and the context stays on the host.
5. Cases. One artifact check over exactly upstream's 100 values, none added and none removed. The seed is unused, as upstream's tests draw nothing at run time.
6. Oracle. Every expected value comes from `hidden/expected.json`, and `oracle.py` holds no value or count. `judge` requires:
   - the one declared file, with status `present` and a `Text` value;
   - `value in text` for every value, which is upstream's `c in data`.
   It fails closed on a wrong check, malformed context or any other status, and the context check rejects duplicates. Its work is 100 substring searches over at most 1 MiB. It uses no regular expression, never uses evidence as a path, and has no side effects. The `text` parser (`securebench/evidence/parsers.py`) decodes strict UTF-8, rejects a byte-order mark, keeps `\r` and normalizes nothing, as the record's table says. Upstream has no regression tests.
7. Candidates. I regenerated each mutant's script from its `sed` and diffed it against `reference.sh`: each changes exactly the intended line. In the baseline, dash with GNU `sed "s/$/\r/"` writes CRLF, and `tr -d "\n"` removes newlines.
   - `mutant-crlf-output` aims at the parser's line endings and `mutant-unseparated-output` at the substring search, the two places where the check is least like upstream's.
   - The other three mutants run the real attack with one step broken.
   - All five got the same verdict from both graders.
   - `attack-conftest` tampers with the native pytest run through `/pytest.ini` and `/conftest.py`, and `attack-claim-pass` claims a verdict. Both end `failed` (`oracle`).
   - `reference.sh` is upstream plus `cd /app`, a `#!/bin/sh` first line and a source comment, without the inert second line `#! /bin/bash`. The "Candidates" bullet (line 79) now says exactly this and why.
8. Divergences. `qualification.json` reports no problems. Every SecureBench run is admitted, rejudged and not dirty, and records the digest above. The runs name two framework commits (`0d1e267` and `e60a414`), but `git diff` shows no change between them to `securebench/`, `pyproject.toml` or `uv.lock`. The only divergence is `attack-conftest` (native 1.0, SecureBench `failed`), and its explanation is correct: SecureBench captures only `/app` and reads the answer itself, so SecureBench is right. Seven native results are cached. The cache key covers the script, the scripts it calls and the files in `candidates/` that are not scripts, so the reuse is sound.
9. Inventory. The proposed row (`converted`, `-`) is correct, and no exclusion applies. The current row in `conversions/inventory.tsv` still has the note from before remediation, which uses a lesson code; the coordinator should replace it with the proposed row.

Upstream assertions: `open("/app/plaintexts.txt").read()` maps to the file status `present`, and `assert c in data` for each of the 100 values maps to `judge`'s `value in text`. `test.sh` asserts nothing about the candidate. Nothing is dropped.

First-pass findings:
- Unreadable files under `/app`: fixed by the new stricter bullet at line 69. Its description and reason are accurate.
- Description of `reference.sh`: fixed at line 79. It matches the diff against upstream.

Findings:
- None.

Verdict: approved
