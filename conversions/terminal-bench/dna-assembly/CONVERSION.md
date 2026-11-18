# dna-assembly

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/dna-assembly

## How the pack grades

The agent must write `/app/primers.fasta`: eight primers that make the four
templates in `/app/sequences.fasta` ready for a one-pot BsaI Golden Gate
assembly of the target plasmid. Upstream's single test, `test_primers` in
`tests/test_outputs.py`, reads that file and checks it in Python, calling
primer3's `oligotm` for melting temperatures.

The pack has one artifact check, `primers`, which reads `/app/primers.fasta`
as UTF-8 text (at most 16 MiB). No candidate code runs during grading, so
there is no protocol check and no adapter. `hidden/oracle.py` repeats
`test_primers` on the file's text, function by function (`parse_bsai_primer`,
`make_fragment`, `test_primers`), with every `assert` turned into a failed
judgment that carries the assertion's own message:

| Upstream assertion | In the Oracle |
| --- | --- |
| `primers_path.exists()` | file status must be `present` |
| `len(lines) == 16` | same, on lines split as Python's text mode splits them (below) |
| header starts with `>`; `re.fullmatch(r"[atcg]+", primer)` after `.lower()` | same; the regular expression is a hand-written check of the same character set |
| all eight `input/egfp/flag/snap` `_fwd/_rev` keys present | same, with the same dict (a repeated header overwrites, as upstream) |
| `parse_bsai_primer`: BsaI site present, clamp of at least 1 nt, room for padding, overhang and binding | same |
| `make_fragment`: forward and reverse annealing sites found on the template (doubled for the circular vector) | same |
| annealing tracts (with overhang overlap) 15 to 45 nt | same |
| `oligotm` Tm of each tract in [58, 72], pair at most 5 apart | same comparisons, on Tm from `_oligotm` (below) |
| the four overhang matches, closure, unique junction overhangs | same |
| assembled sequence in `output + output` | same |

The template, insert and target sequences are upstream's test literals
(`vector`, `egfp`, `flag`, `snap`, `output`), stored in
`hidden/templates.json` with `vector` under the key `input`. They are
identical to the records of `environment/sequences.fasta`, which ships in the
image (sha256 `ebdc361b…f130736f` in both). The Oracle never reads the
candidate's copy of that file; `attack-rewrite-sequences` checks this.

## Fidelity changes

- **`oligotm` reimplemented in the Oracle (equivalent).** Upstream's verifier
  installs primer3 with apt at grading time and runs `oligotm -tp 1 -sc 1
  -mv 50 -dv 2 -n 0.8 -d 500` on each annealing tract. The Evaluation has no
  network, the baseline has no primer3, and a Tm computed inside the
  Evaluation would be candidate-controlled, so `_oligotm` in the Oracle
  reimplements the one code path these flags reach in primer3 2.6.1
  (`src/oligotm.c`, the version Ubuntu 24.04 ships as `primer3 2.6.1-4`):
  SantaLucia 1998 nearest-neighbour parameters, terminal and symmetry
  corrections, divalent-to-monovalent conversion and SantaLucia salt
  correction, operation by operation so the doubles agree, then rounded as
  `printf("%f")` prints and the test's `float()` reads it. Left out: the
  Breslauer table, the other salt corrections, DMSO and formamide (zero with
  these flags), `N` and other characters, and lengths outside 15 to 45. None
  is reachable: the test calls `oligotm` only on a substring of a template
  after checking its length is 15 to 45.
  Because that input domain is finite, we compared the reimplementation with
  the native binary on all of it: every substring of 15 to 45 nt of the
  doubled vector, egfp, flag and snap, 123,876 sequences, 14,373 of them
  within 1 °C of 58 or 72. All 123,876 printed values agree exactly
  (`hidden/check_oligotm.py` regenerates the domain and redoes the
  comparison; its docstring has the commands). The mutants
  `mutant-tm-gap-over-5` (pair 5.02 °C apart), `mutant-tm-above-72`
  (72.02 °C) and `mutant-tm-near-limits` (58.14 °C, 71.69 °C, pairs 4.95 °C
  apart, passes) put the thresholds through both graders.
- **primer3 version fixed (equivalent today).** Natively, `oligotm` is
  whatever version apt serves when the verifier runs; it was 2.6.1-4 when we
  converted. The Oracle keeps 2.6.1's values even if Ubuntu ships another
  version later.
- **Line splitting reimplemented (equivalent).** Upstream iterates over
  `open(path, "r")`, whose universal newlines end a line at `\n`, `\r\n` or a
  lone `\r`, and strips trailing whitespace from each line. SecureBench's
  text parser splits on `\n` only and keeps `\r`, so the Oracle splits the
  raw text itself: it translates `\r\n` and `\r` to `\n`, splits, drops the
  empty piece after a final newline, and applies `str.rstrip()`.
  `mutant-cr-line-endings` (upper case, lone-CR line endings, passes) and
  `mutant-crcrlf-last-line` (a final `\r\r\n`, which upstream reads as an
  extra empty line, fails) check both directions. A file that is not UTF-8
  or starts with a byte-order mark is `unparsable` here; upstream's UTF-8
  decoding fails on the first and leaves `﻿` before the first `>` on
  the second, so both fail there too. `str.lower` and `str.rstrip` run on
  the host's Python 3.12 instead of upstream's 3.13; their tables differ
  only for code points no valid file contains.
- **Size bound of 16 MiB on `primers.fasta` (stricter).** Upstream reads any
  size. The reference's file is 379 bytes; a file above 16 MiB could pass
  upstream only with clamps of megabytes before the BsaI site.
- **`primers.fasta` must be a regular file (stricter).** Upstream follows a
  symlink; the artifact check reports one as `not_regular`, which fails.
- **Scope (stricter only in edge cases).** The scope is all of `/app`, which
  holds the deliverable and nothing upstream's test loads. Its limits are
  the largest SecureBench accepts (100,000 entries, 2 GiB) so that scratch
  work left in `/app` does not fail capture. Capture rejects absolute
  symlinks and symlinks that leave `/app`, so an agent that leaves, say, a
  virtual environment in `/app` fails capture where upstream would ignore
  it; relative symlinks inside `/app` are allowed.
- **Allowed domains (stricter).** Upstream allows the whole internet. The
  pack allows `archive.ubuntu.com` and `security.ubuntu.com`, the image's
  apt sources, which is what the reference needs to install EMBOSS and
  primer3. An agent cannot reach PyPI or NEB's website, which the
  instructions suggest consulting for BsaI-HF v2's requirements; the
  requirements the test checks (site `ggtctc`, one spacer base, four-base
  overhang, a 5' clamp) are standard knowledge.
- **Instructions, cases and baseline (unchanged).** `instructions.md` is
  upstream's `instruction.md` byte for byte; upstream has a single test and
  the pack a single check; the baseline is upstream's image
  `alexgshaw/dna-assembly:20251031`, pinned by digest.

## Candidates

`reference.sh` runs upstream's `solve.sh`, kept byte for byte as
`candidates/upstream-solve.bash` (the name keeps both graders from treating
it as a candidate). The mutants and attacks share `candidates/design-primers`,
a POSIX `sh` port of `solve.sh`'s primer construction that takes the
annealing ranges as arguments; with `solve.sh`'s ranges it writes a file
byte-identical to the reference's.

- `mutant-tm-gap-over-5`, `mutant-tm-above-72`, `mutant-tm-near-limits`:
  annealing lengths chosen, by measuring each design with the test's own
  tract logic, to fall just past or just inside the Tm limits.
- `mutant-cr-line-endings`, `mutant-crcrlf-last-line`: line-ending variants
  of the reference file (above).
- `attack-fake-oligotm`: primers whose real Tm is far below 58 °C, plus a
  fake `oligotm` in `/usr/local/bin` that prints 65 °C. Upstream's test runs
  whatever `oligotm` comes first on PATH, so this targets the native grader;
  SecureBench computes Tm on the host and must fail it.
- `attack-rewrite-sequences`: a wrong design (egfp keeps its stop codon) plus
  a rewritten `/app/sequences.fasta` whose `output` record is exactly what
  the primers assemble. With that record as the target the Oracle's logic
  passes these primers, so it fails only because the target comes from
  `hidden/`.
- `attack-oracle-dos`: a 15.2 MB file of eight 1.9 MB primers, to make the
  Oracle crash or time out; it must end `failed`. The Oracle's work is linear
  in the file size, and every Tm call is on at most 45 bases.

## Divergences from native

- `attack-fake-oligotm`: native 1.0, SecureBench `failed` (class `oracle`,
  "Forward primer must have a Tm between 58 and 72 degrees C."). SecureBench
  is right. The input pair's annealing tracts have Tm 51.69 °C and 42.52 °C
  by primer3's own `oligotm`, so the primers break the task's rules. The
  native grader passes them because its test runs `oligotm` from PATH, and
  the fake in `/usr/local/bin` that the attack leaves comes before the
  `/usr/bin/oligotm` the verifier installs. SecureBench computes Tm on the
  host and never runs a candidate-controlled tool.

Every other candidate gets the same verdict from both graders.

## Review

Reviewer: acce5d9fb2b8735ad, 2026-10-27

Pack digest from `securebench validate`: `sha256:c03be1edad523395c39cee34d4ec741561c9140a322a0818583754bba5a2823b`. I noted it before reviewing and it was unchanged at the end. All eleven SecureBench runs in `qualification.json` record it.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md` finds no difference.
2. Scope. The scope is one root, `/app`, with no excludes. I inspected the pinned baseline (`alexgshaw/dna-assembly@sha256:d1adf683…`): `/app` holds only `sequences.fasta` (sha256 `ebdc361b…f130736f`), and it has no symlinks and no `/.securebench`. Upstream's test lives in `/tests`, outside the image, and nothing in `/app` is loaded by convention, so a candidate cannot rewrite the specification. The deliverable `/app/primers.fasta` is in scope, and the 2 GiB and 100,000-entry limits cover any solution the instructions allow. The two stricter edge cases are recorded: a symlinked deliverable, and symlinks that leave `/app`, such as a virtual environment.
3. No expected value leaks. There is no `public/` or `evaluation/`. The Oracle's only data is `hidden/templates.json`. I compared it, by parsing the upstream test with `ast`, with the test's literals `vector`, `egfp`, `flag`, `snap` and `output`, and all five match exactly. They also match the baseline's `sequences.fasta`, which the instructions describe as the task's input, so these values are public by design and are not the answer. The answer is the primers, and no copy of them exists anywhere. The Oracle never reads the candidate's copy of `sequences.fasta`. The allowed domains are the image's two apt sources. They hold no answer and offer no channel between runs.
4. Challenges. There are no protocol checks and no challenges.
5. Cases. Upstream has one test, `test_primers`, and the pack has one artifact check. `plan` ignores the seed, which is correct because upstream draws nothing at random.
6. Oracle. `oracle.py` holds only judging logic, and the sequences come from `hidden/`. `_test_primers`, `_make_fragment` and `_parse_bsai_primer` follow upstream line for line, and every upstream `assert` has a matching `_require`. `primers.fasta` exists. There are 16 lines, split the way universal newlines split them, then `rstrip`. Headers start with `>`. Each primer matches `[atcg]+` after `lower()`. All eight keys are present, and a repeated header overwrites as in upstream's dict. The BsaI site, clamp and spacer are present. Both annealing sites are found. Each tract is 15 to 45 nt. Each Tm is between 58 and 72 °C, and each pair is at most 5 °C apart. The four overhang matches hold, closure included. The junction overhangs are unique. The assembly is in `output + output`.
   - Tm reimplementation. I checked `_oligotm` independently. I regenerated the input domain (123,876 sequences) and ran native `oligotm` from primer3 2.6.1-4 in the baseline on every one of them. `check_oligotm.py compare` reports 0 missing and 0 different. The domain is complete, because the Oracle calls `_oligotm` only after the 15 to 45 nt length check, and only on substrings of a template or of the doubled vector.
   - Differential against upstream's own test. I ran upstream's own `test_primers` (python3, real primer3, inside the baseline) and the Oracle (fed through SecureBench's text parser) on 25 files. These covered LF, CR, CRLF, LF CR and CR CR LF endings; a missing final newline; a trailing blank line, a trailing space and a trailing lone CR; trailing whitespace on headers and primers (tab, NBSP, FF, NEL, U+2028); a VT used as a separator; NUL in headers; a BOM; upper-case headers; a header with a leading space; an empty file; a 4,000-nt clamp; reversed record order; and the primers of every mutant and attack. All 25 verdicts agree. The only difference is the BOM file's failure message: the text parser reports it `unparsable`, while upstream's test fails on the header check.
   - Robustness. The Oracle ignores claims, fails closed on unexpected evidence or context, and its work is linear in a file bounded at 16 MiB. An exception or timeout in `judge` becomes a failed judgment in `securebench/oracle/process.py`.
   - Regression tests. None are run by outcome.
7. Candidates. `upstream-solve.bash` is byte-identical to upstream's `solve.sh`, and `reference.sh` only changes to `/app` and runs it with bash.
   - Mutants. Three are aimed at the reimplemented `oligotm`: 5.02 °C apart, 72.02 °C, and a design that sits at every limit and passes. Two are aimed at the reimplemented line splitting. All run real code (the shared `design-primers`), and I confirmed their Tm with the native binary. Each gets the same verdict from both graders in qualification.
   - Attacks. All three end `failed`. `attack-rewrite-sequences` targets this task's agent-writable copy of the target plasmid. `attack-fake-oligotm` targets the native grader's PATH lookup. `attack-oracle-dos` sends a file just under the size bound.
8. Divergences. The only divergence is `attack-fake-oligotm`: native 1.0, SecureBench `failed`. The explanation holds. Its input forward tract `taatgaggatcccgg` has Tm 51.688886 °C and its reverse tract has 42.518680 °C. Native primer3 prints exactly these values, and both are below 58 °C, so the primers break the task's rules. The native test passes them only because it runs the fake `oligotm` the attack puts first on PATH. SecureBench is right.
   - Qualification. `qualification.json` reports `problems: []`. Every run is admitted and rejudged, every one has `dirty: false`, and none reused a cached native result. The runs record three framework commits (`dd3182b`, `6622854`, `115da84`), but `git diff` shows no change to `securebench/`, `pyproject.toml` or `uv.lock` between them.
9. Inventory. There is no row yet; the coordinator adds it on commit. The row should read `converted`, with reason `-`. No exclusion reason applies, because the conversion exists and qualifies.

Every fidelity change is labelled stricter or equivalent, with its reason, and every upstream assertion is checked. One point for the record, not a finding: the reference writes `primers.fasta` with `sed`, `cut`, `tr` and `rev`, and `solve.sh` has no `set -e`, so its result would not change without network. The apt domains are still what its `apt-get install` and its `needle`/`oligotm` diagnostics use, and an agent needs primer3 to meet the Tm rules the instructions state, so keeping them is right.

Findings:
- None.

Verdict: approved
