# dna-insert

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/dna-insert

## How the pack grades

Upstream has one test, `test_primers` in `tests/test_outputs.py`. It reads
`/app/primers.fasta`, checks its shape and the primers' sequences against three
constants (`vector1`, `vector2`, `insert`), and runs primer3's `oligotm` on the
two annealed parts to check their melting temperatures.

The pack has one artifact check, `primers`, which reads `/app/primers.fasta` as
UTF-8 text (at most 16 MiB). There are no protocol checks: nothing in the task
needs the candidate's code to run, so no Evaluation environment is started.
`hidden/oracle.py` repeats the test step by step on the file's text, in the
same order:

| Upstream assertion | Oracle |
|---|---|
| `primers_path.exists()` | file status must be `present` |
| `len(lines) == 4`, lines read with universal newlines and `rstrip()` | same split (`\r\n` and `\r` end lines, a final terminator adds no line), same `rstrip()` |
| `re.fullmatch(r"[atcg]+", ...)` on lines 2 and 4, lower-cased | non-empty and every character in `atcg`, after `lower()` |
| `insert` found in `rc(rev) + fwd` | same `find`, same slicing into the two annealed parts |
| annealed lengths in 15..45 | same |
| reverse part is a suffix of `vector1`, forward part a prefix of `vector2` | same |
| `oligotm` Tm of each part in 58..72, and at most 5 apart | the same comparisons, on temperatures from `hidden/oligotm.json` |

The constants and bounds live in `hidden/expected.json`. Upstream's test
constants are copied unchanged; they match `sequences.fasta` (the output
plasmid is the input with `insert` placed after position 213, between
`vector1` and `vector2`).

## Melting temperatures

The Oracle runs on the host and cannot run `oligotm`, and the brief forbids
vendoring primer3. It does not reimplement it either. Once the overlap checks
pass, the forward annealed part is `vector2[:n]` and the reverse one is
`vector1[-n:]`, with `n` in 15..45, so the test can only ever pass `oligotm`
62 sequences: `vector2[:n]` and `rc(vector1[-n:])`. `hidden/derive_oligotm.py`
runs the real `oligotm`, with upstream's flags in upstream's order, on all 62
and writes `hidden/oligotm.json` (each sequence, the exact standard output, and
`float(stdout.strip())` as the test computes it). The Oracle looks up the
temperature by strand and length. Within this domain the lookup is exactly the
native tool; a length outside the table fails closed.

The table was derived with Ubuntu 24.04's `primer3` package, version 2.6.1-4,
which is what the native verifier's `apt-get install primer3` installs in the
baseline image today. The command is in the script's docstring.

`hidden/differential.py` runs upstream's own `test_primers` (with `oligotm`
replaced by the same table) and the Oracle on 1,112 crafted files: every pair
of annealed lengths 13..45, which covers every temperature threshold (the
closest are a reverse part of 30 nucleotides at 58.08 C, forward 24 at
72.39 C, and pairs 4.99 and 5.40 C apart), and 23 files that probe line
handling (CR, CRLF, no final newline, blank and whitespace-only lines, Unicode
whitespace, upper case, wrong order, invalid UTF-8, a BOM). They agree on all
but the BOM file (see below).

## Fidelity changes

- **Melting temperatures from a table of real `oligotm` output** (equivalent).
  See above. If the Ubuntu archive later ships a primer3 whose `oligotm`
  prints other values, the native verdict would follow it and ours would not;
  the table records the version it came from.
- **A byte-order mark at the start of the file** (stricter). SecureBench's text
  parser rejects a leading BOM, so such a file is `unparsable` and fails.
  Natively the BOM stays in the first line, which is a header the test never
  reads, so the file can pass.
- **Files above 16 MiB** (stricter). The artifact check reads at most 16 MiB,
  the largest SecureBench allows. A correct file is a few hundred bytes; only
  headers padded past 16 MiB, which the test ignores, could pass natively and
  fail here.
- **`/app/primers.fasta` as a symlink** (stricter). The artifact check accepts
  only a regular file, while the test follows symlinks. A symlink that leaves
  `/app` also fails capture.
- **Scope** (equivalent). The scope is `/app`, the only place the test reads.
  Its subdirectories' contents are excluded (`*/*`): the test never reads them,
  and an agent's scratch there (a virtualenv's absolute symlinks, a large
  download) would otherwise fail capture or the size bounds. Internal symlinks
  are allowed for the same reason. Top-level files of `/app` are captured.
- **Allowed domains** (equivalent). Upstream allows all internet access; the
  pack allows `archive.ubuntu.com` and `security.ubuntu.com`, which the
  reference needs for `apt-get install emboss primer3`. The answer is not
  published there.
- **Instructions, cases** (equivalent). `instructions.md` is upstream's
  `instruction.md` byte for byte; the one upstream test is the one artifact
  check.

## Candidates

- `reference.sh`: upstream's `solve.sh` with `cd /app` added. Annealed parts of
  15 and 41 nucleotides (59.54 and 62.23 C).
- `null.sh`: does nothing.
- `mutant-gc-formula.sh`: picks the shortest annealed parts that the basic
  GC-content Tm formula puts at 58 C or more (21 and 44); their `oligotm`
  temperatures are 5.54 C apart. Fails both graders, on the 5 C rule.
- `mutant-wallace.sh`: the same with the Wallace rule (18 and 23); the reverse
  part is at 52.19 C. Fails both, on the 58 C minimum.
- `mutant-no-dntp.sh`: runs `oligotm` without `-n 0.8`; it lands on 15 and 30,
  the reverse part at 58.08 C, just above the minimum. Passes both.
- `mutant-crlf-upper.sh`: the reference's primers in upper case with CRLF
  endings and trailing spaces. Passes both; it tests the Oracle's line
  handling.
- `mutant-trailing-blank.sh`: the reference's primers plus an empty fifth line.
  Fails both, on the line count.
- `write-primers` is a helper the mutants and `attack-fake-oligotm.sh` share;
  it writes primers in the reference's layout for given annealed lengths.
- `attack-fake-oligotm.sh`: puts a fake `oligotm` in `/usr/local/bin`, which
  comes before the `/usr/bin/oligotm` the native verifier installs on `PATH`,
  and writes primers whose real temperatures (72.39 and 57.03 C) break both
  bounds. It passes natively (Pier, reward 1.0); SecureBench fails it because the fake is outside the scope and the Oracle uses its own
  table.
- `attack-root-conftest.sh`: writes `/pytest.ini` and a `/conftest.py` that
  rewrites every test report to passed, and a primers file with no primers. It
  passes natively (Pier, reward 1.0); SecureBench fails it because nothing outside `/app` is captured and no test runner takes part.

## Divergences from native

- `attack-fake-oligotm`: native 1.0, SecureBench `failed` (oracle: forward Tm
  72.39 C). SecureBench is right: the primers' real `oligotm` temperatures
  (72.39 and 57.03 C) break both bounds, and the native verdict comes from the
  fake `oligotm` the candidate put first on `PATH`.
- `attack-root-conftest`: native 1.0, SecureBench `failed` (oracle: the primer
  lines are `PASSED`, not nucleotides). SecureBench is right: the file holds no
  primers, and the native verdict comes from the candidate's `/conftest.py`
  rewriting pytest's reports.

Every other candidate gets the same verdict from both graders.

## Review

Reviewer: conversion-reviewer (dna-insert-review), 2026-10-26

Pack digest checked: `sha256:27d8dc2a9be2d87b8df37acca406b4af12400dda9f055293ba5823fb63855b9d` (`securebench validate`, before and after qualification; every SecureBench run in `qualification.json` records it).

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. No fidelity change needed.
2. Scope. One root `/app` with `exclude = ["*/*"]`; per 4.6, `*` matches one whole component, so this drops everything below a subdirectory of `/app` and keeps every top-level file, including `/app/primers.fasta`, the only path upstream's test reads. The baseline's `/app` holds only `sequences.fasta` (identical to upstream's) and no symlinks. Tests live at `/tests`, outside the scope, and nothing convention-loaded is involved because no test runner is used. `symlinks = true` gives no route: the artifact check accepts only a regular file, and that is recorded as stricter.
3. No expected value leaks. There is no `public/` or `evaluation/`, and no Evaluation environment is started. `hidden/expected.json` holds upstream's test constants (`vector1`, `vector2`, `insert`) and bounds. These constants can be derived from the public `sequences.fasta`, so they are outside SecureBench's scope. The baseline image contains nothing else. The allowed domains are Ubuntu's apt archives, which do not publish the answer.
4. Challenges. There are none (artifact check only).
5. Cases. Upstream's one test maps to the one artifact check. Nothing was added, and the seed is unused.
6. Oracle. Every upstream assertion maps in order to a check in `judge` (exists, 4 lines after universal-newline split and `rstrip`, `[atcg]+` after `lower`, insert `find`, both length bounds, both overlaps, both Tm bounds and the 5 C difference). None is dropped. Expected values and bounds come from `hidden/`; the only constant in `oracle.py` is the nucleotide set the regex encodes. The Tm table replaces running `oligotm`. I checked the claim that the test can only pass `oligotm` `vector2[:n]` and `rc(vector1[-n:])` for n in 15..45, and it holds because the overlap and length checks come first. I re-derived all 62 temperatures independently with my own script in the baseline image (primer3 2.6.1-4 from apt, upstream's flags): 0 differences from `hidden/oligotm.json`. No value is integral, so the `isinstance(..., float)` guard never fails closed on a valid row. I ran `hidden/differential.py`: 1,112 files, 1 mismatch, the BOM file, recorded as stricter. Work over candidate text is linear and bounded at 16 MiB. The Oracle reads no claims and reports no status fields.
7. Candidates. `reference.sh` is upstream `solve.sh` with only `cd /app` added (checked with `diff`). The five mutants run real code and target the two places where the conversion departs from upstream. The Tm table and thresholds are covered by gc-formula (difference 5.54 C), wallace (52.19 C) and no-dntp (58.08 C, just above the minimum). Line handling is covered by crlf-upper and trailing-blank. Both graders agree on all five. `attack-fake-oligotm` targets this task's tool lookup on `PATH`, and `attack-root-conftest` targets the native test runner. Both fail in SecureBench (class `oracle`) and pass natively.
8. Divergences. Qualification reports no problems. All runs are admitted, rejudged and clean. The three framework commits recorded (ae46211, 2b6f70d, 22ddcca) differ only in ledger commits, with no change under `securebench/`. The only divergences are the two attacks (native 1.0, SecureBench `failed`), and CONVERSION.md explains both correctly: the real temperatures 72.39 and 57.03 C break the bounds, and the conftest file holds no primers.
9. Inventory. `conversions/inventory.tsv` has no row for dna-insert yet; the coordinator adds it. No exclusion is claimed, and none applies: the conversion is faithful.

Findings:
- `CONVERSION.md`, "Allowed domains" bullet (minor, does not block): narrowing upstream's open internet to the two Ubuntu archives is labelled "equivalent". It does not change any verdict for a given candidate, but it removes routes an agent could take natively (for example PyPI's primer3-py or building primer3 from GitHub). "stricter" with the existing reason would be more accurate.

Verdict: approved
