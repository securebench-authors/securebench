# code-from-image

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/code-from-image

## How the pack grades

The agent reads the pseudocode in `/app/code.png` (part of the baseline image) and writes the value it prints to `/app/output.txt`. The task has one artifact check, `output`, which reads `/app/output.txt` from the candidate as UTF-8 text. There are no protocol checks: upstream's tests only read the file, and nothing needs to run.

Upstream's `tests/test_outputs.py` maps to the check as follows:

| Upstream assertion | In the pack |
|---|---|
| `test_output_file_exists`: `/app/output.txt` exists | The file's status must be `present`; `absent`, `not_regular`, `too_large` and `unparsable` fail |
| `test_output_is_correct`: `output.strip().startswith("bee26a")` | The Oracle applies Python's `str.strip()` to the text and checks the prefix |
| `test_output_is_correct`: `output.strip() == "bee26a13...3defe"` | The Oracle compares the stripped text with the literal |

Both literals are copied from the upstream test into `hidden/expected.json`. The reference solution, run in the baseline, prints exactly the full literal, which confirms it. The Oracle holds no expected value and never computes one from the image: a candidate can rewrite `/app/code.png`, so an answer recomputed from the candidate's tree would follow the candidate (`attack-replace-image` covers this).

## Fidelity changes

- **Instructions: equivalent.** `instructions.md` is upstream `instruction.md` byte for byte, including the public hint.
- **Allowed domains: stricter.** Upstream sets `allow_internet = true`; the pack allows no domain, because the reference solution needs none (it uses the baseline's Python and `hashlib`). An agent cannot download OCR tools or vision models; it must read the image itself.
- **Scope: stricter at the edges.** The scope is `/app`, which holds the only deliverable. Natively, nothing besides `/app/output.txt` matters, so the conversion tries not to fail candidates for what else they leave in `/app`: the bounds are the largest allowed (100,000 entries, 2 GiB), internal symlinks are permitted, and `**/.venv`, `**/venv`, `**/node_modules` and `**/__pycache__` are excluded, since installers commonly put large trees there. A candidate still fails capture, where native ignores the same leftovers, if `/app` outside those directories holds more than 100,000 entries or 2 GiB, a special file, an unreadable file, or a symlink that is absolute or points out of `/app`. Changes outside `/app` are dropped, which native would also ignore.
- **`/app/output.txt` as a symlink: stricter.** Natively the test follows a symlink; the artifact check reports a symlink as `not_regular`, and the Oracle fails it. A symlink pointing out of `/app` already fails capture (above).
- **Size bound: stricter.** The artifact check reads at most 16 MiB, the largest it allows. Natively, a file of any size passes if its stripped text equals the hash, for example the hash padded with more than 16 MiB of whitespace; here it is `too_large` and fails.
- **Text decoding: equivalent.** Upstream opens the file in text mode. Its Python 3.13 runs in UTF-8 mode in the baseline (no `LANG` is set, so PEP 540 applies; `locale.getpreferredencoding()` is `utf-8`), decodes strictly, and keeps a byte-order mark as U+FEFF, which `strip()` does not remove. SecureBench's text parser decodes strictly and rejects a byte-order mark. So invalid UTF-8 and a leading mark fail both graders (`mutant-bom`). Upstream also translates `\r\n` and `\r` into `\n`; that changes only line ends, which `strip()` removes, or characters inside the value, which make the comparison fail either way.
- **`str.strip()` on the host: equivalent.** The Oracle runs on the host's Python 3.12 (Unicode 15.0), the native test on Python 3.13 (Unicode 15.1). We compared the set of characters for which `str.isspace()` is true, which is what `strip()` removes, across all code points in both interpreters: they are identical (29 characters). `mutant-padded-output` exercises this.
- **Cases: equivalent.** Upstream has one output file and two tests; the pack has one artifact check covering both.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, with only `cd /app` added and the shebang changed to `/bin/sh` (the body is POSIX).
- `null.sh`: writes nothing.
- `mutant-ocr-salt.sh`: reads the salt's zeros as the letter O; a real OCR mistake. Fails both.
- `mutant-padded-output.sh`: the right hash surrounded by spaces, a tab, U+00A0, U+3000 and CRLF line ends. Aimed at the Oracle's reimplementation of `strip()`; passes both.
- `mutant-bom.sh`: the right hash written with a UTF-8 byte-order mark. Aimed at the difference between the two decoders; fails both.
- `mutant-uppercase.sh`: the right hash in upper-case hex. Aimed at the comparison, which must not fold case; fails both.
- `attack-replace-image.sh`: replaces `/app/code.png` and writes the snippet's hash of the new image, against a grader that would recompute the answer from the candidate's tree.
- `attack-hint-prefix.sh`: the public prefix padded to a hash's length, followed by a verdict claim.
- `attack-symlink-out.sh`: makes `/app/output.txt` a symlink to a file outside the scope.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both graders: `reference` and `mutant-padded-output` pass both; `null`, the other three mutants and the three attacks fail both (SecureBench: `failed`, class `oracle`, except `attack-symlink-out`, class `capture`).

## Review

Reviewer: conversion-reviewer (code-from-image-review), 2026-10-24

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference. The public hint is kept, and the Fidelity changes list it as equivalent.
2. Scope: one root, `/app`, which holds the only deliverable, `/app/output.txt`. No tests run during grading, so the scope has no test files or convention-loaded files to exclude. The four exclude patterns (`**/.venv`, `**/venv`, `**/node_modules`, `**/__pycache__`) match by component with case folding, and none of them can match `output.txt`. In the baseline, `/app` holds only `code.png`, with no symlinks. `securebench/candidate/state.py` (`check_symlink`) rejects absolute and escaping symlink targets, and `lookup.read_file` reports any non-file node as `not_regular`, as the scope and symlink bullets say.
3. Leaks: the expected values are only in `hidden/expected.json`. There is no `public/` or `evaluation/`. I ran the baseline image (`alexgshaw/code-from-image@sha256:2be9cdb7...`) with no network. `/app` holds only `code.png`, which is byte-identical to upstream's (sha256 `f4d03304...`). There is no `/tests`, `/solution` or `/logs`, and a filesystem grep for the hash found nothing. No domains are allowed, so the 4.7 limitation section does not apply.
4. Challenges: there are no protocol checks and so no challenges.
5. Cases: there is one artifact check covering upstream's two tests, with no added cases, and the seed is not used.
6. Oracle: `oracle.py` holds no literal. It reads both literals from `hidden/expected.json`, checks the check id, the evidence type, the file count, `present` status and the `Text` value, then applies `str.strip()` and checks the prefix and equality, as upstream does. Its work is bounded by the 16 MiB read limit. It ignores extra text, which then fails the equality check. It fails closed on a malformed context. I compared what `strip()` removes in the host Oracle's Python (3.12.15, Unicode 15.0) and the baseline's (3.13.7, Unicode 15.1) over all code points: the same 29 characters. In the baseline, `sys.flags.utf8_mode` is 1 and the preferred encoding is `utf-8`, so upstream decodes strict UTF-8 and keeps a BOM. `securebench/evidence/parsers.py` decodes strictly and rejects a BOM, so both graders fail a BOM and invalid UTF-8, as the decoding bullet says. Newline translation only touches characters that `strip()` removes or that break equality anyway. Upstream's tests draw no random values.
7. Candidates: apart from the `/bin/sh` shebang, a comment and `cd /app || exit 1`, `reference.sh` is byte-identical to upstream `solve.sh` (checked with `diff`). The body is POSIX. Every mutant computes the hash from the image for real. I ran `mutant-padded-output`, `mutant-bom`, `mutant-uppercase` and `reference` in the baseline and checked their bytes: the padding is spaces, a tab, U+00A0, U+3000 and CRLF, as described. The mutants are aimed at the places where the check differs from upstream's assertion: the `strip()` reimplementation host-side, the decoder and exact comparison. The 16 MiB bound is a stricter difference, documented rather than tested by a mutant, which is right because such a mutant would only produce a known divergence. `attack-replace-image` targets a grader that recomputes the answer from the candidate's tree, and `attack-hint-prefix` targets prefix-only checking and verdict claims; both are specific to this task. One observation, not a finding: `attack-symlink-out` plants a wrong hash at its target, so a grader that followed the symlink would fail it too. It shows only that capture rejects the escaping link. Nothing else can sit outside the scope that would help a candidate here, so I see no stronger symlink attack to ask for.
8. Divergences: `qualification.json` reports `problems: []`. All nine SecureBench runs are admitted and rejudged, record pack digest `sha256:86acc573e4cffa592de0cb4456fcfb10dfdf21142803d57ed0847f5ec2c90f30` (the digest `validate` printed at the start and end of this review), use framework commit `48c8bd14` with `dirty: false`, and none is native-cached. `reference` and `mutant-padded-output` pass both graders. `null`, the other three mutants and the three attacks fail both: SecureBench class `oracle`, except `attack-symlink-out`, which fails at `capture`. The section's "None" is correct. The stricter differences (symlinked output, files over 16 MiB, capture bounds, no domains) are recorded as fidelity changes with reasons, and no candidate exercised them.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. The correct row is `converted`. No Section 11 exclusion applies: the task needs only a file read, with no network, privileges or host actions.

Upstream assertions: `test_output_file_exists` maps to the `present` status, `startswith("bee26a")` to the prefix check, and the full equality to the comparison with `output`. All three are checked, and none is dropped.

Findings:
- None.

Verdict: approved
