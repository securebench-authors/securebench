# vulnerable-secret

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/vulnerable-secret

## How the pack grades

The agent works in `/app` of the upstream image, which holds the stripped binary
`/app/vulnerable`. Its only deliverable is `/app/results.txt`. The pack has one
artifact check, `results`, which reads that file from the candidate as UTF-8 text
(at most 16 MiB). There are no protocol checks, so nothing of the candidate runs
during grading.

`hidden/oracle.py` reproduces what upstream's tests do with the file: Python's
text-mode read (universal newlines turn `\r\n` and a lone `\r` into `\n`), then
`str.strip()`, then the comparisons. The flag and the format rules come from
`hidden/expected.json`, which holds the literals of `tests/test_outputs.py`.

| Upstream test (`tests/test_outputs.py`)    | Where it is checked                                                                                      |
|---|---|
| `test_results_file_exists`                 | the file's evidence status must be `present`                                                             |
| `test_results_file_contains_secret_flag`   | stripped content equals `flag` in `hidden/expected.json`                                                |
| `test_results_file_format`                 | stripped content starts with `prefix`, ends with `suffix` and is longer than `longer_than` characters   |

The third test is implied by the second; it is kept so every assertion has a
counterpart.

## Fidelity changes

- **Domains: stricter.** Upstream allows the internet; `allowed_domains` is empty.
  The reference needs only `python3` and the binary, both in the image. The native
  verifier downloads `curl`, `uv` and pytest at grading time; the pack's grading
  needs none of them.
- **Decoding and stripping: equivalent.** Upstream reads with `open(path, "r")`.
  The image sets no `LANG`, so Python 3.13 runs in UTF-8 mode (PEP 540; checked in
  the image: `sys.flags.utf8_mode == 1`, preferred encoding `utf-8`). The text
  parser decodes strict UTF-8 like that read, and the Oracle applies the same
  newline translation and the same `str.strip()`, which also removes Unicode
  whitespace such as U+00A0. Invalid UTF-8 fails both (upstream raises
  `UnicodeDecodeError`). A UTF-8 byte-order mark fails both for different reasons:
  upstream keeps U+FEFF, which `strip()` does not remove, so equality fails; the
  text parser reports the file `unparsable`. `mutant-nbsp`, `mutant-crlf` and
  `mutant-bom` probe these paths on both graders.
- **Results file size: stricter.** The artifact check reads at most 16 MiB, the
  largest bound allowed. Upstream reads any size, so a file holding the flag plus
  more than 16 MiB of whitespace passes natively and fails here (`too_large`).
- **Results file as a symlink: stricter.** Upstream's `Path.exists()` and `open()`
  follow symlinks, so `/app/results.txt` linking to another file that holds the
  flag passes natively. Capture never follows symlinks: an internal relative link
  is captured as a link and the artifact check reports it `not_regular`, and a link
  with an absolute target, or one that escapes `/app`, fails capture. The root
  allows internal symlinks (`symlinks = true`) so that unrelated links an agent
  leaves in `/app` do not fail the attempt.
- **Other agent files in `/app`: stricter.** The scope is all of `/app`, because
  the instructions fix only the results path and agents keep exploit scripts and
  payloads beside it. Anything capture rejects there (a named pipe or socket, a
  symlink with an absolute target, such as the links of a Python virtual
  environment created in `/app`, or more than 100,000 entries or 2 GiB) fails the
  attempt with class `capture`, where upstream ignores it. Nothing else in `/app`
  is graded.
- **Instructions, cases and baseline: unchanged.** `instructions.md` is upstream
  `instruction.md` byte for byte, and the baseline is the upstream image
  `alexgshaw/vulnerable-secret:20251031` pinned by digest.

## Candidates

- `reference.sh` runs upstream `solution/solve.sh`, kept byte for byte as
  `candidates/upstream-solve.bash`, with `bash` in `/app`. No drift repair.
- `null.sh` changes nothing.
- `mutant-nbsp.sh` (expected pass on both): the exploited flag followed by U+00A0.
- `mutant-crlf.sh` (expected pass on both): the flag indented by a tab and space
  and followed by `\r\n\r\n`.
- `mutant-bom.sh` (expected fail on both): the flag written with the `utf-8-sig`
  codec.
- `mutant-whole-line.sh` (expected fail on both): the whole
  `Access granted! Secret: ...` line instead of the flag.
- `mutant-static-decode.sh` (expected fail on both): XOR-decodes the key from the
  binary without the exploit, including the terminator, so a NUL follows the flag.
- `attack-symlink-escape.sh`: `results.txt` as an absolute symlink to
  `/.securebench/instructions.md`; SecureBench fails it at capture.
- `attack-invalid-utf8.sh`: a flag-shaped file with invalid UTF-8 and a NUL;
  `unparsable`, failed by the Oracle.
- `attack-oversize.sh`: a 17 MiB flag-shaped file; `too_large`, failed by the
  Oracle.

`candidates/exploit-secret` is the exploit three mutants share. The helper files
have no `.sh` suffix because qualify treats every `*.sh` file as a candidate.

## Divergences from native
None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-crlf` and `mutant-nbsp` pass both; the null
candidate, `mutant-bom`, `mutant-whole-line`, `mutant-static-decode` and the three
attacks fail both (native reward 0). The SecureBench runs were made at two
framework commits, 918e23e2 and 6d06d959, because a coordinator commit landed
during qualify; it changed only `conversions/agents.tsv`, so the SecureBench code
is the same and qualify reported no problem.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-03

Pack digest checked: `sha256:bb79055f0d851d7778d432f38f934824f820fd23c4992d7c4e4f5b1660c16173` (`securebench validate`, at the start and again at the end).

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. `candidates/upstream-solve.bash` is also identical to upstream `solution/solve.sh`.
2. Scope. One root, `/app`, no excludes, `symlinks = true`. The deliverable path is fixed by the instructions, and `/app` covers it and anything an agent leaves beside it. There are no test files or convention-loaded files to protect: upstream's tests live in `/tests`, which the image does not contain, and the pack has no protocol check, so nothing in `/app` is ever loaded by a grader. I listed the baseline image (`docker run --network none`): `/app` holds only the stripped `vulnerable` binary and no symlinks; `/.securebench` is absent. The cost of scoping all of `/app` (a venv, FIFO or absolute symlink there fails capture) cannot be avoided, since exclude patterns cannot express "everything except `results.txt`". It is recorded as stricter. I confirmed in `securebench/candidate/state.py` that capture rejects absolute and escaping symlink targets even with `symlinks = true`, as the record says.
3. No expected value leaks. `public/` and `evaluation/` do not exist. The flag lives only in `hidden/expected.json`. The Oracle reads nothing from the candidate except `/app/results.txt` as evidence. The flag is XOR-encoded inside `/app/vulnerable` in the baseline, which is the task itself: the same binary, unchanged, is what upstream gives the agent. Grading never reads it, so a candidate gains nothing by changing it. `grep -r b4ff3r` over the image's filesystem finds the plaintext flag nowhere, and there is no `/tests`. `allowed_domains` is empty, so the public upstream test file is not reachable, and no "answer reachable" limitation is needed.
4. Challenges. There are no protocol checks and so no challenges.
5. Cases. There are no protocol cases. The one artifact check covers upstream's three tests, and none was added. The seed is unused, which is correct because upstream draws no random values.
6. Oracle. The flag, prefix, suffix and length bound all come from `hidden/expected.json`, and those values match the literals in `tests/test_outputs.py`. `oracle.py` holds only comparisons. It checks the status (present), the type (`Text`), equality after universal-newline translation and `str.strip()`, then prefix, suffix and length, and it fails closed on a malformed context or unexpected evidence. Its work is bounded by the 16 MiB file limit. I compared it with upstream's `open(path, "r").read().strip()` under the image's Python 3.13. The image sets no `LANG`, and I confirmed `sys.flags.utf8_mode == 1` with preferred encoding `utf-8`. So upstream decodes strict UTF-8, like the text parser (`securebench/evidence/parsers.py`). The parser's only extra rejection is a leading BOM, and upstream fails that too, because U+FEFF is not whitespace. A NUL passes the parser and fails equality, as it does natively. The replace order `\r\n` then `\r` matches Python's universal newlines. No regression tests run by outcome.
7. Candidates. The reference is upstream's solve script run with `bash` in `/app`, with no drift repair; it passes both graders. Null fails both. The five mutants all run the real exploit or decode the real binary. They are aimed at the reimplemented read: decoding (`bom`), stripping of Unicode whitespace (`nbsp`), newline translation and leading whitespace (`crlf`), a NUL (`static-decode`) and wrong extraction (`whole-line`). Each gets the same verdict from both graders. The three attacks (an escaping symlink, invalid UTF-8 with a NUL, and an oversize file) cover the only routes this task offers, which are capture and parsing of the single deliverable, since no candidate code runs during grading. All three end `failed` (classes `capture`, `oracle`, `oracle`), never `invalid`.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run records the pack digest above, is admitted, is rejudged and is not dirty. No verdict differs from native, and the section says so. The two framework commits (918e23e2 and 6d06d959) differ only in `conversions/agents.tsv` (`git diff --stat`), as the record states.
9. Inventory. `conversions/inventory.tsv` has no row for this task: it was removed when the task went on standby (54aced3d), and the converter may not edit the file. The coordinator should add `terminal-bench	vulnerable-secret	converted	-`. No exclusion reason applies: the task needs only an artifact check on one text file.

Upstream assertions: `test_results_file_exists` maps to the present status; `test_results_file_contains_secret_flag` to the equality check; and `test_results_file_format` (starts with `FLAG{`, ends with `}`, longer than 10) to the three format checks. None is dropped. Every fidelity change has a label and a reason: domains, decoding, file size, symlink and other files in `/app`.

Findings:
- None.

Verdict: approved
