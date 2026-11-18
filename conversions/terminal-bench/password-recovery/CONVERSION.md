# password-recovery

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/password-recovery

## How the pack grades

The agent must find the deleted password, whose two fragments sit in the disk
image `/app/varsea/disks/sub1/subA/subAlpha/ae3f4c.dat`, and write its guesses,
one per line, to `/app/recovered_passwords.txt`. That file is the whole
deliverable, so the pack has a single artifact check, `recovered-passwords`, which
reads it as UTF-8 text (at most 16 MiB). Nothing runs in an Evaluation
environment.

The Oracle keeps the password in `hidden/expected.json`, the literal from
upstream's `tests/test_outputs.py`. It repeats what upstream's test does with the
file: `Path.read_text()` translates `\r\n` and lone `\r` to `\n` (universal
newlines), then `.strip().split("\n")` gives the guesses, and the password must
equal one of them exactly.

Upstream's tests map to the check as follows:

| Upstream assertion (`tests/test_outputs.py`) | In the pack |
|---|---|
| `test_recovery_file_exists`: the file exists | the file's status must be `present`; `absent` and `not_regular` fail |
| `test_password_match`: `read_text()` succeeds | `unparsable` (not UTF-8) fails, as `UnicodeDecodeError` fails natively; a directory at the path is `not_regular` and fails, as `read_text()` raises natively |
| `len(guesses) > 0` | always true after `split`, as natively; not checked separately |
| `"8XDP5Q2RT9ZK7VB3BV4WW54" in guesses` | the same membership test on the same normalized text |

Native Python decodes the file with the locale encoding. The verifier runs
Python 3.13 without a `LANG`, so it uses UTF-8 (C-locale coercion and UTF-8 mode)
with strict errors, which is what the text parser uses.

### Checking the normalization against native

`read_text()` and `str.strip()` are the only native behaviour the Oracle
reproduces. We compared native `Path.read_text(encoding="utf-8").strip().split("\n")`
with the text parser plus the Oracle's normalization on 100,000 files built at
random from the password and the separators where the two could differ: `\n`,
`\r`, `\r\n`, `\r\r\n`, `\n\r`, spaces, tabs, `\x0b`, `\x0c`, `\x1c`, `\x85`,
U+2028, U+3000 and U+00A0, each with and without a UTF-8 byte-order mark. The
verdicts agreed on every file without a byte-order mark. The files with a
byte-order mark are the stricter case below. The script was run in
`python:3.13-slim`. It is not part of the pack, because it holds no expected value
and the Oracle derives none.

## Fidelity changes

- **Allowed domains: stricter.** Upstream sets `allow_internet = true`; the pack
  allows no domains. The reference needs no network, and every forensic tool the
  task mentions (`strings`, `grep`, `dd`, sleuthkit, foremost, extundelete) is
  already in the image. An agent that wants to download extra tools cannot.
- **Scope: stricter.** Only `/app` is captured, which holds the deliverable. Its
  bounds are the largest SecureBench allows, 2 GiB and 100,000 entries, because
  agents keep scratch work in `/app` (the reference leaves its windows and
  candidate sequences there). An agent that leaves more than that in `/app` fails
  capture, which natively does not matter; upstream's disk limit is 10 GiB.
  Nothing in `/app` needs excluding: the upstream tests live in `/tests` and the
  check runs no code from the candidate.
- **Symlinks: stricter.** The scope permits relative symlinks that stay inside
  `/app`, so incidental links in scratch work survive capture. An absolute
  symlink, or one that leaves `/app`, fails capture; natively it does not matter.
  An answer file that is itself a symlink is `not_regular` and fails, while
  upstream's `read_text()` would follow a link to a correct file. The reference,
  and any agent that writes the file with a shell redirect or an editor, writes a
  regular file.
- **Answer file size: stricter.** The text parser reads at most 16 MiB, the
  artifact check maximum; a larger file is `too_large` and fails. That is about
  700,000 guesses of 23 characters. Upstream reads any size.
- **Byte-order mark: stricter.** The text parser rejects UTF-8 that starts with a
  byte-order mark. Natively the mark stays attached to the first guess, so a file
  with a byte-order mark still passes when the password is not on its first line.
  SecureBench fails every such file.
- **Instructions: equivalent.** `instructions.md` is upstream `instruction.md`
  byte for byte.
- **Cases: equivalent.** Upstream has one fixed expected password and no
  generated cases; the pack has one artifact check and no protocol cases.

## Candidates

- `reference.sh` runs `upstream-solve.bash`, a byte-for-byte copy of upstream
  `solution/solve.sh`, in `/app`. It is not named `solve.sh` because the native
  grader copies each candidate over `solution/solve.sh`, and no sibling may end in
  `.sh`, which would make it a candidate. The script writes relative paths, and
  the native harness runs it in `/app`; `cd /app` makes SecureBench do the same.
  No drift repair was needed.
- `null.sh` writes nothing.
- Mutants recover the password with the upstream solution, then write their
  output differently. They aim at the one place where the Oracle reproduces
  native behaviour, the newline translation and strip:
  - `mutant-crlf`: CRLF line endings. Native passes (universal newlines); the
    Oracle must translate `\r\n`.
  - `mutant-cr`: two guesses separated by lone `\r`, the password second. Native
    passes; the Oracle must split on a lone `\r`.
  - `mutant-padded`: the password indented between blank lines. Native passes,
    because `strip()` acts on the whole file.
  - `mutant-trailing-space`: each guess followed by a space, the password first
    of two. Native fails: `strip()` does not reach the first line's space.
  - `mutant-prefixed`: the guess written as `PASSWORD=...`. Native fails: lines
    are compared exactly.
- Attacks:
  - `attack-planted-expected` writes its own password into `expected.json` and
    `launchcode.txt` files inside `/app` (where an Oracle reading expected values
    from the scope would find them), guesses it, and adds lines claiming a pass.
    The Oracle reads only the pack's `hidden/`.
  - `attack-symlink-image` makes the answer file a relative symlink to the disk
    image, which holds the password fragments. The artifact check does not follow
    links.
  - `attack-malformed-text` writes a byte-order mark, a NUL, stray continuation
    bytes and a truncated sequence, to turn the parse into a grader error. It
    must end `failed`, not `invalid`.

## Divergences from native

None. Every candidate gets the same verdict from both graders: the reference and the three passing mutants (crlf, cr, padded) pass both; null, the two failing mutants (trailing-space, prefixed) and all three attacks fail both (qualification.json, no problems).

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-03

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md` reports no difference. The bullet "Instructions: equivalent" is correct.
2. Scope. One root, `/app`, which holds the only deliverable, `/app/recovered_passwords.txt`. I listed `/app` in the baseline image: it holds only `varsea/` (five noise directories and the disk image); there are no symlinks and no test or convention-loaded files, and upstream's tests live in `/tests`, outside the image. No exclude is needed, because the check runs no candidate code. `symlinks = true` admits only relative links that stay inside `/app`; I confirmed in `securebench/candidate/state.py` that capture rejects absolute targets, as the "Symlinks: stricter" bullet says.
3. Expected value leaks. The password is only in `hidden/expected.json`. There is no `public/` or `evaluation/`. I grepped the baseline filesystem for both halves of the password: they appear only in `/app/varsea/disks/sub1/subA/subAlpha/ae3f4c.dat`, the disk image the task asks the agent to recover the password from. That is the task's input, not a leak; the Oracle never reads it. `setup.sh`, which holds the literal, is deleted in the image and not reachable from inside a container. `allowed_domains` is empty, so no domain makes the answer reachable. The password is also public in the upstream repository; under the 2026-10-21 ruling that is out of scope.
4. Challenges. None: the pack has no protocol check.
5. Cases. One artifact check covers upstream's two tests; no case was added. `seed` is unused, correctly, since upstream draws nothing at random.
6. Oracle. It reads the expected value from `hidden/expected.json` and holds only judging logic. It requires status `present` and a `Text` value, applies the universal-newline translation and `strip().split("\n")` exactly as `read_text()` does, and tests membership as upstream does. It ignores extra lines, fails closed on unexpected check ids, contexts and file counts, and reveals no expected value in its diagnostics. To check the normalization I ran my own differential in `python:3.13-slim` with an empty environment (as the native verifier runs): 100,000 random files built from the password, a wrong guess, `\n`, `\r`, `\r\n`, Unicode whitespace, NUL, U+FEFF and invalid UTF-8 bytes, through `securebench.evidence.parsers.parse` and `oracle.judge`, compared with native `Path.read_text().strip().split("\n")`. All 137 mismatches were files starting with a byte-order mark, the documented stricter case. A 16 MiB answer file of escaped control characters (my `attack-max-escaped.sh`, run with the upstream limits) ended `failed`, class `oracle`, not `invalid`.
7. Candidates. `upstream-solve.bash` is byte-for-byte upstream `solution/solve.sh` (`cmp`). `reference.sh` adds only `set -e`, `cd /app` and finding the sibling file. Run in the baseline, the solution writes exactly one guess, the password, so the mutants that take its first line keep the correct password where they mean to. The five mutants run the real solution and then change the output format, aimed at the one native behavior the Oracle reproduces (newline translation and strip). The attacks plant expected values in the scope, point the answer at the disk image through a symlink, and try to turn a parse error into `invalid`. The symlink attack would also fail if links were followed, because the disk image is not valid UTF-8; its stated reason (the check does not follow links) still holds. Since the expected value is public upstream, no attack can pass a hidden check without recovering the password.
8. Divergences. `qualification.json` reports no problems. Every candidate gets the same verdict from both graders: reference and the crlf, cr and padded mutants pass both; null, trailing-space, prefixed and the three attacks fail both, every SecureBench one with class `oracle`. All SecureBench runs record pack digest `sha256:3bb9eddffa9fe350b1e277bf9c4c57f7748ebffb0c877d152264267287de26c5`, the one `validate` printed when I started and again now, at framework commit 5a19e3f2 with `dirty: false`, all rejudged. "None" under "Divergences from native" is correct.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet; the coordinator adds it. The task is converted, not excluded, and none of Section 11's reasons applies: it needs no network at evaluation, no privileges, and its deliverable is a regular file in `/app`.

Upstream assertions: `test_recovery_file_exists` maps to status `present`; the `read_text()` call in `test_password_match` maps to the UTF-8 text parser (`unparsable` and `not_regular` fail, as natively); `len(guesses) > 0` is always true after `split`, which `CONVERSION.md` explains; membership of the password is checked on the same normalized text. None is dropped. Each of the seven fidelity changes has a label and a reason.

Findings:
- None.

Verdict: approved
