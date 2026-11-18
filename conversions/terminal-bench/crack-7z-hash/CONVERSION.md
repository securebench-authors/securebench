# crack-7z-hash

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/crack-7z-hash

## How the pack grades

The agent must write the word stored in `secret_file.txt`, inside the
password-protected `/app/secrets.7z`, to `/app/solution.txt`.

Upstream's `tests/test_outputs.py` has two tests:

- `test_solution_file`: `os.path.exists("/app/solution.txt")`.
- `test_solution_content`: `open("/app/solution.txt", "r").read().strip() == "honeybear"`.

The pack has one protocol check, `solution`, with one case. Its adapter
(`evaluation/adapter.py`, standard-library Python on the stock interpreter)
opens the path named in the challenge with `open(path, "rb")`, which follows
symlinks as the native `open()` does, and returns the raw bytes as base64. If
the file cannot be opened (absent, a directory, a dangling symlink) it reports
`unable`, and the case fails. The Oracle decodes the bytes the way the native
test does (strict UTF-8, universal newlines), applies `str.strip()` and
compares the result with the expected word in `hidden/cases.json`.

Both upstream tests map to this one case: a file that can be read and holds the
word also exists, and a missing file fails both upstream tests and the case.

A protocol check is used instead of an artifact check so that a
`solution.txt` that is a relative symlink to the extracted
`secrets/secret_file.txt` passes, as it does natively. An artifact check would
see such a symlink as `not_regular`. The adapter runs on the stock interpreter
with `-I`, so nothing the candidate writes in `/app` is loaded into it; the
candidate controls only the bytes of the file it reads.

## Fidelity changes

- **Scope: all of `/app`, symlinks allowed** (equivalent). The native test
  reads only `/app/solution.txt`. The whole of `/app`, John the Ripper's tree
  included, is captured so that a `solution.txt` that is a relative symlink to
  any file the agent wrote under `/app` resolves after replay as it does
  natively. That covers symlinks to `secrets/secret_file.txt`
  (`mutant-symlink`) and to files extracted under `/app/john` (checked with a
  scratch candidate that ran `7z x` in `/app/john/run` and linked
  `solution.txt` to `john/run/secrets/secret_file.txt`: passed). Only
  `/app/john/.git` is excluded, implicitly, as in every root. Nothing hidden
  is exposed by capturing `john`: after the reference runs, `john.pot` holds
  only the archive's hash and the password `1998`.
- **Absolute symlinks and symlinks leaving `/app`** (stricter). Capture accepts
  only relative symlinks that stay inside their scope root. A `solution.txt`
  made with `ln -s /app/secrets/secret_file.txt` passes natively and fails
  SecureBench with class `capture`. This is a framework rule we cannot relax
  in the pack; the relative form passes (`mutant-symlink`).
- **Capture bounds** (stricter). `/app` may hold at most 100,000 entries and
  2 GiB (the largest bound SecureBench allows); the native harness has no
  such bound. The baseline `/app` is 259 MiB and about 2,700 entries outside
  `.git`, so a full rebuild of John fits.
- **Files larger than 3,000,000 bytes** (stricter). The adapter reports
  `unable` for them, because their base64 would not fit in the 4 MiB
  observation limit. Natively, a `solution.txt` of several megabytes of
  whitespace around the word would pass.
- **Reimplemented text reading** (equivalent). The Oracle replaces the native
  `open(path, "r").read().strip()` with strict UTF-8 decoding, universal
  newline translation and `str.strip()`. The native verifier runs Python 3.13
  in the image's C locale, which Python coerces to UTF-8, so the native
  decoding is strict UTF-8 too. We compared the Oracle's verdict with the
  native expression on 5,808 byte strings concentrated at the acceptance
  boundary (the word and five near-misses, padded on both sides with ASCII
  whitespace, CR/LF combinations, U+0085, U+00A0, U+2028, U+3000, U+200B,
  U+FEFF, NUL, a lone surrogate, Latin-1 `0xA0` and `0xFF`), under both
  `LANG=C.UTF-8` and an unset `LANG` in `python:3.13-slim`: 0 differences.
  `mutant-nbsp`, `mutant-latin1`, `mutant-bom` and `mutant-crlf` check the
  same boundary against the real native harness.
- **Allowed domains: `archive.ubuntu.com` and `security.ubuntu.com`**
  (stricter). Upstream gives the agent unrestricted internet
  (`allow_internet = true`). The reference needs only the image's own apt
  sources, to install `libcompress-raw-lzma-perl` and `7zip`. An agent that
  wants to download other tools (for example hashcat releases from GitHub)
  cannot.

## Reference runtime

The reference cracks the 7z key derivation (524,288 SHA-256 iterations) with
John the Ripper's default modes. With the upstream limit of one CPU, John
still starts 12 OpenMP threads (the worker has 12 cores), and on our worker it
ran at 4 to 5 candidates per second: single mode took 39 minutes and the
wordlist pass, which finds `1998` at line 3,320 of `password.lst`, about
4 more. That SecureBench attempt took 2,619 seconds, while a second container
of ours competed for the same cores. In the qualification, the native agent
phase took 1,588 seconds, within upstream's 1,800-second agent timeout but
close to it. The pack has no agent time limit of its own, so on a slower or
busier worker the native reference could time out while the SecureBench one
still passes.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with `cd /app` added, because
  the upstream script lists relative paths from the working directory.
- `null.sh`: changes nothing.
- `mutant-symlink.sh`: extracts the archive and makes `solution.txt` a
  relative symlink to `secrets/secret_file.txt`. Aimed at the adapter's
  symlink following. Expected to pass both.
- `mutant-nbsp.sh`: writes the word followed by a UTF-8 no-break space, which
  `str.strip()` removes after UTF-8 decoding. Aimed at the reimplemented
  decoding and strip. Expected to pass both.
- `mutant-latin1.sh`: writes the word followed by a Latin-1 no-break space,
  which is not valid UTF-8. Expected to fail both.
- `mutant-bom.sh`: writes the word behind a UTF-8 byte-order mark, which UTF-8
  decoding keeps and `strip()` does not remove. Expected to fail both.
- `mutant-crlf.sh`: writes the word with CRLF line endings, a tab and blank
  lines around it. Aimed at universal newline translation. Expected to pass
  both.
- `extract.sh.inc`: shared by the mutants; installs 7-Zip and extracts the
  archive as the reference does. It is not a candidate.
- `attack-wordlist.sh`: writes the first 20,000 entries of John the Ripper's
  bundled `password.lst`, which include the secret word, without cracking
  anything; it fails if the grader searches the file instead of comparing its
  whole stripped content.
- `attack-claim.sh`: writes a wrong word with forged verdicts (an adapter
  envelope, a judgment, `PASSED`) and a native reward file.
- `attack-symlink-escape.sh`: makes `solution.txt` a relative symlink that
  leaves `/app` to `/proc/self/fd/0`, so a grader that followed it would read
  its own input (in SecureBench, the challenge) as the answer. Capture rejects
  it.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-crlf`, `mutant-nbsp` and `mutant-symlink`
pass both; null, `mutant-bom`, `mutant-latin1` and the three attacks fail both.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-03 (second review, after the converter's fix). Pack digest at review: `sha256:4ebb1d54058fd3435603d152ae26bdb82556fa55241a30c8396e91cb7a91dde8`.

The first review had one finding. The first "Fidelity changes" bullet called the `john` exclusion equivalent, although a `solution.txt` that is a relative symlink into `/app/john` passed natively and failed SecureBench, and its capture-bounds reason did not hold. The converter took the second remedy: it removed `exclude = ["john"]`, so all of `/app` is captured, and raised both scope bounds to 2 GiB. The scope bullet now describes that, and the bounds bullet gives the real numbers. With `john` captured, the symlink case resolves after replay, so "equivalent" is now the right label for the scope bullet. Finding fixed. Only `task.toml` and `CONVERSION.md` changed. `instructions.md`, `hidden/`, `evaluation/` and `candidates/` are as in the first review.

1. Instructions. `cmp` with upstream `instruction.md`: identical (unchanged).
2. Scope. One root, `/app`, symlinks allowed, no explicit excludes. Only the implicit `**/.git` exclusion applies, which drops `/app/john/.git`. I re-checked the larger root in the baseline image:
   - There are 11 symlinks outside `.git`, all relative and internal: `doc/LICENSE -> ../LICENSE`, `doc/README -> ../README.md`, `src/arch.h -> x86-64.h`, and eight tools in `run/` linked to `john`. None leaves `/app`.
   - There are no FIFOs, sockets or device files, which would fail every capture.
   - There is no `conftest.py` or `.pth` file, and no other convention-loaded file. Nothing in `/app` is loaded at grading time anyway: the adapter runs the stock interpreter with `-I`, and the native test reads only `solution.txt`.
   - The bounds are 100,000 entries and 2 GiB, the framework's maximum. The baseline is 259 MiB and 2,717 entries outside `.git`, so the recorded stricter bounds change is accurate.
3. Leaks. Capturing `john` exposes nothing hidden. A grep of `/app` finds `honeybear` only in `john/run/password.lst`, which was already in the baseline the agent can read. It is one entry of 1,795,708 and does not single out the answer. `john.pot` would hold only the archive hash and `1998`. The expected value is still only in `hidden/cases.json`, and no allowed domain publishes it.
4. Challenges. Unchanged: `{"path": "/app/solution.txt"}`. It holds nothing hidden.
5. Cases. Unchanged: one case for both upstream tests. No case was added, and there is no seed use.
6. Oracle. Unchanged. My earlier differential still applies: 2,420 near-boundary byte strings, Oracle against native `open(p, 'r').read().strip()` under CPython 3.13.16 in the C locale, 0 differences. The Oracle's judging logic and bounds are as described in the first review. Regression tests: none.
7. Candidates. Unchanged and still well aimed (see the first review). In `qualification.json`:
   - SecureBench: `reference`, `mutant-crlf`, `mutant-nbsp` and `mutant-symlink` passed. `null` failed (`case_error`). `mutant-bom`, `mutant-latin1`, `attack-claim` and `attack-wordlist` failed (`oracle`). `attack-symlink-escape` failed (`capture`). No run ended `invalid`.
   - Native: the same verdicts for every candidate.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run is admitted and rejudged, and every one records the digest above. "Divergences from native: None" matches the verdicts. All native results are `native_cached`. That is allowed: the candidate scripts are unchanged, and the native harness does not read the pack. The null run records framework commit `700d1ad7`, the others `b5b5b183`. `git diff 700d1ad7 b5b5b183 -- securebench` is empty, so they ran the same SecureBench code, as qualify confirmed, and neither run is dirty. The "Reference runtime" section now gives the native agent phase as 1,588 s against upstream's 1,800-second timeout. It records the risk that a slower worker could time the native reference out. That is a property of upstream's limit, not of the conversion.
9. Inventory. `conversions/inventory.tsv` still has no `crack-7z-hash` row. The coordinator adds it as `converted`, with no exclusion reason: no Section 11 reason applies.

Upstream assertions:
- `test_solution_file`: covered by the case. A missing file or a dangling symlink makes the adapter report `unable`, and a directory or an unreadable file fails the content check, as it does natively.
- `test_solution_content`: covered by the Oracle's strict UTF-8 decoding, newline translation, `strip()` and equality.

Findings:
- None.

Verdict: approved
