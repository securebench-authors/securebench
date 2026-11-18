# large-scale-text-editing

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/large-scale-text-editing

## How the pack grades

The agent writes `/app/apply_macros.vim`, a Vim script that must turn the public
`/app/input.csv` (one million rows) into the public `/app/expected.csv`, using only
three `setreg` lines, `:%normal! @a/@b/@c` and `:wq` or `:x`, with fewer than 200
keystrokes in the three macros. Upstream's `tests/test.sh` deletes `/app/*.csv`,
regenerates a clean `input.csv`, and runs the five tests of `tests/test_outputs.py`.
They map to two checks:

| Upstream test | Check | How |
|---|---|---|
| `test_apply_macros_exists` | `script` (artifact) | the captured file must be present and a regular file |
| `test_apply_macros_well_formed` | `script` (artifact) | the Oracle runs upstream's line checks on the captured file: every `:%normal!` token is `@a/@b/@c`; `:wq` or `:x` present; `setreg` for a, b and c present; `:%normal! @a/@b/@c` present; every non-comment line valid, with the macro text free of the forbidden patterns |
| `test_apply_macros_runs` | `run` (protocol, one case) | the adapter repeats `rm *.csv` and `gen_large_csv.py input`, then runs `vim -Nu NONE -n -Es /app/input.csv -S /app/apply_macros.vim` in `/app` with upstream's 600-second timeout and reports the exit status; the Oracle requires 0 |
| `test_input_equiv_expected` | `run` | the adapter reports the SHA-256 of `/app/input.csv` after the Vim run; the Oracle compares it with the digest of upstream's expected file, kept in `hidden/expected.json` |
| `test_macros_nonempty_and_efficient` | `run` | the adapter writes upstream's `_defs_only.vim` (its code is copied unchanged), runs Vim on it with the 300-second timeout, and returns the two dump files as upstream reads them; the Oracle parses the `KEYSTROKES` line and requires a, b and c above 0, their sum equal to `total`, `total` below 200, and the first three stripped register lines pairwise distinct |

The three running tests stay in one case and in upstream's order, because they share
state: upstream's second Vim run reads the script after the first Vim run, which can
change it.

`hidden/expected.json` holds the SHA-256 of the `expected.csv` that upstream's generator
writes in `expected` mode. `hidden/derive_expected.py` recomputes it; it equals the
SHA-256 of `/app/expected.csv` in the baseline image
(`833cb9527dad306efe9f8f870497f6f519e3978e9c27f093bc56eb2935f41f97`). The generator is in
`evaluation/gen_large_csv.py`, a byte-for-byte copy of upstream's `tests/gen_large_csv.py`
(identical to `environment/gen_large_csv.py`); its expected output is public anyway,
because the baseline ships `/app/expected.csv`.

## Fidelity changes

- **Instructions**: unchanged, equivalent.
- **Allowed domains**: none. The reference only writes a file. Equivalent.
- **Scope** (stricter): only `/app` is captured, without symlinks. The instructions ask
  for one file there, and `vim -Nu NONE` reads no configuration from elsewhere. A
  solution that changes anything outside `/app`, or makes `apply_macros.vim` a symlink,
  passes natively and fails here; no solution the instructions allow needs either.
- **Scope bounds** (stricter): capture walks at most 100,000 entries and 2 GiB under
  `/app`, the largest bounds the framework allows; upstream has no bound but the
  container's 10 GiB disk. The baseline's `/app` has 2 files and 89 MB. An agent that
  leaves more than 100,000 files in `/app` (for example the million-row file split into
  small chunks for testing) or more than 2 GiB there fails capture here and can pass
  natively.
- **Reading the script** (stricter): the artifact check parses the file as strict
  UTF-8 of at most 1 MiB. Upstream reads it with `errors="ignore"` and no size bound,
  so a script with invalid UTF-8 bytes (for example in a comment) or above 1 MiB can
  pass natively and fails here. The bound keeps the Oracle's scan within its time
  limit; real scripts are a few hundred bytes. A byte-order mark fails both (upstream's
  first line then starts with U+FEFF, which matches no allowed command). The Oracle
  translates `\r\n` and `\r` to `\n` as `Path.read_text` does.
- **Regular expressions rewritten as scans** (equivalent, except one more lenient case
  below): the Oracle may not apply
  regular expressions to evidence, so each of upstream's expressions in
  `test_apply_macros_well_formed`, `_is_valid_line`, `_is_valid_keystroke_sequence` and
  the `KEYSTROKES` parse is a hand-written scan in `hidden/oracle.py`, named after the
  expression it replaces. `re.IGNORECASE` is reproduced with the two letters whose
  case-insensitive match includes non-ASCII characters (`i`: U+0130, U+0131; `s`:
  U+017F, measured with Python 3.13 over every code point), and `\s`, `\w`, `\d` with
  `str.isspace`, `str.isalnum` or `_`, and `str.isdecimal`, which are the predicates
  Python's `re` uses for `str` patterns. `hidden/differential.py` compares the scans
  with upstream's own functions and expressions, run on upstream's interpreter (Python
  3.13 in the baseline image) on random inputs dense in the characters and words the
  expressions treat specially (colons, range characters, case variants, Unicode digits
  and spaces, quotes, CR and CRLF line ends, byte-order marks). 500,000 rounds, each
  comparing one macro string, one `setreg` extraction, two whole scripts, two
  `:%normal!` token lists and one `KEYSTROKES` line: 0 mismatches, with 305,524 macro
  strings and 61,098 complete scripts accepted by upstream, so both sides of every
  check were reached. One difference cannot be tested there: SecureBench runs the
  Oracle on the host's Python 3.12 (Unicode 15.0), while upstream uses Python 3.13
  (Unicode 15.1). Only the characters added in Unicode 15.1 (CJK Extension I and a few
  others) are classified differently, and only as `\w` after a forbidden command name,
  which no Vim macro has a reason to contain.
- **Catastrophic backtracking in upstream's file-command pattern** (more lenient):
  upstream's `:(\d*|[\$%\+\-\.]|(\d+,\d*)|(\d*,\$))*{cmd}\b` can split a run of digits
  in exponentially many ways, and Python's `re` tries them all when no command follows
  the run. Measured in the baseline image with one CPU, upstream's
  `_is_valid_keystroke_sequence` on `:s/x/y/\<CR>:` + n zeros + `1\<CR>j` takes 0.38 s
  for n = 16, 1.52 s for 18, 6.12 s for 20 and 23.84 s for 22, about four times longer
  for every two more digits (the reviewer measured 115 s for 24). From about 26 digits
  after a `:`, the check plus the Vim run exceed the native verifier's 1,200 seconds,
  and from about 28 the check alone does, so the script fails natively. The Oracle's
  scan gives the same answer (accepted) in under a millisecond, so such a script can
  pass here. We do not reproduce a running time in the Oracle. The case needs a
  macro with a 26-digit count or line number after a colon, which no transformation of
  this file needs. The differential's fragments are too short to reach it.
- **Expected file** (stricter): upstream regenerates `/app/expected.csv` with
  `/tests/gen_large_csv.py` after the agent's Vim script has run, inside the container
  that script controls, and asserts the generation succeeded. Here the expected digest
  is computed beforehand by the same generator and stays on the host, so the assertion
  about the generation has nothing to check. A script that rewrites the generator
  during its Vim run passes natively and fails here (`attack-tamper-generator`). The
  adapter does not write `/app/expected.csv` after the first Vim run, so upstream's
  second Vim run can see that file and this one cannot; only a script that reads it
  from a `setreg` line could notice.
- **Regenerating the input** (equivalent): the adapter runs the copied generator with
  the stock Python instead of the baseline's `python3`; the generator is deterministic
  and its output was compared byte for byte (the reference's transformed file matches
  the expected digest, and the regenerated input is the baseline's `input.csv`).
- **Vim's standard input** (equivalent): the adapter gives both Vim runs `/dev/null` as
  standard input. Upstream's runs inherit the verifier's non-interactive standard input;
  Vim in `-Es` mode reads it only if the script does not exit.
- **Dump files** (stricter, unreachable by honest output): the adapter returns at most
  65,536 characters of each dump file and the Oracle fails a truncated one. Vim's
  `keytrans` writes each keystroke as at most a few characters, so a dump of macros
  below 200 keystrokes is far smaller.
- **Timeouts** (equivalent): the Vim runs keep upstream's 600 and 300 seconds; the case
  has upstream's verifier timeout of 1,200 seconds. The reference takes about 100
  seconds per case with one CPU.

## Limitation: keystroke count measured by the candidate's Vim session

Upstream checks only the text of a `setreg` line up to its first quote, and loads the
whole line in the Vim session that counts the keystrokes. A script can therefore run
any Vim command from the rest of a `setreg` line, for example to write its own
`vim_keystrokes.out` and `vim_regs.out` and quit, and so pass the 200-keystroke bound
with longer macros. This conversion keeps upstream's check and its counting, so the
same script passes here: the adapter's Vim session runs candidate code. The values
such a script writes are upstream's public bound, not hidden values, so the forgery is
of the hardcoding kind that SecureBench does not claim to stop. The same holds for the
digest of the transformed file: a script can copy the public `/app/expected.csv`
(shipped in the baseline) over the input from a `setreg` line, natively and here.

## Mutants and where they aim

- `mutant-let-search`: a correct transformation whose macro a starts with
  `:let @/=''`. It reaches the rejecting side of the Oracle's rewrite of the forbidden
  patterns (`let\s+`).
- `mutant-trailing-comment`: upstream's macros with a trailing comment on each `setreg`
  line, written with CRLF line ends. It reaches the Oracle's newline translation and the
  line-shape check (`setreg` lines must end with a quote and `)`). We did not give CRLF
  line ends to `mutant-199-keystrokes`: Vim exits 1 on a CRLF script, natively too, so
  that mutant would no longer pass, and it is the only one on the passing side of the
  keystroke bound.
- `mutant-200-keystrokes` and `mutant-199-keystrokes`: correct macros of exactly 200
  and 199 keystrokes, counting `<CR>` and `<Esc>` as one each. They test upstream's
  `< 200` threshold through the Oracle's parse of the `KEYSTROKES` line. The 199 one
  also uses the other accepted forms: `:call`, double-quoted register names, indented
  and comment lines, and `:x`.
- `mutant-same-macros`: macros a and b identical. It tests the Oracle's splitting and
  stripping of the register dump.

## Divergences from native
- `attack-tamper-generator`: native passes (1.0), SecureBench fails (`oracle`, the
  transformed file does not match the expected digest). SecureBench is right: the macros
  only trim whitespace, so the file is not transformed. Natively, a `system()` call in the
  tail of a `setreg` line overwrites `/tests/gen_large_csv.py` during the grader's Vim run,
  so the "expected" file is a copy of the wrong output. Here the generator is read-only,
  and the expected digest is computed beforehand and kept on the host.
- `attack-background-reward`: native passes (1.0), SecureBench fails (`oracle`, the
  script does not define the macros). SecureBench is right: the candidate hands in only
  `:wq`. Natively, the background process it leaves keeps writing 1 to
  `/logs/verifier/reward.txt` while the verifier runs in the same container. SecureBench
  grades only what was captured under `/app`, in a fresh environment.

Every mutant gets the same verdict from both graders: `mutant-199-keystrokes` passes
both, and `mutant-200-keystrokes`, `mutant-let-search`, `mutant-same-macros` and
`mutant-trailing-comment` fail both. The null candidate fails both and the reference
passes both.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-03 (second review). Pack digest
reviewed: `sha256:901c78694ed2994208372048f4bccd28e0b8dcb1dc52176fbe303b5e2b53a219`.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` finds no
   difference.
2. Scope: one root, `/app`, `symlinks = false`. The bounds are now 100,000 entries and
   2 GiB, the framework's maxima, and the new "Scope bounds (stricter)" bullet records
   them. The baseline's `/app` holds only `input.csv` and `expected.csv`, with no
   symlinks. `/tests` is not in the baseline, and the generator is mounted read-only
   under `/.securebench/evaluation`. Vim runs with `-u NONE`, so it loads no
   configuration. The adapter and the generator run with `python3 -I`, and `vim` is
   found on a `PATH` outside the scope. The candidate cannot rewrite any part of the
   specification.
3. Leaks: `hidden/expected.json` equals the SHA-256 of the baseline's public
   `/app/expected.csv` (`833cb952...`, checked in the image). So no value in this task is
   hidden: the answer is public by design, as upstream. Nothing else in `evaluation/` or
   the scope carries an expected value.
4. Challenges: the only challenge is `{}`.
5. Cases: one case holds upstream's three running tests, in upstream's order, because
   they share state. No case was added, and the seed is unused.
6. Oracle: `oracle.py` and the adapter are unchanged since the first review.
   - Expected values: the expected digest comes from `hidden/expected.json`, and the only
     constant in `oracle.py` is upstream's threshold of 200.
   - Assertions: I traced every upstream assertion, and each is checked or explained.
     The checks cover `exists` and `well_formed`, both Vim exit statuses, the digest,
     both dump files, the `KEYSTROKES` parse, the counts, the sum, `< 200`, the line
     count and distinctness. The generator's return code and `EXPECTED.exists` are
     explained under "Expected file".
   - Regex scans: these match upstream on everything I read through, except the
     catastrophic backtracking, which is now recorded as more lenient.
   - Running time: worst-case 1 MiB scripts take at most 14 s in the baseline image on 1
     CPU, under the 60 s judge limit, and a judge timeout fails the attempt anyway.
7. Candidates:
   - The reference is upstream `solve.sh` plus `cd /app`.
   - `mutant-let-search` replaces `mutant-ex-commands` and reaches the rejecting side of
     the forbidden-pattern scan. I checked this in the baseline image: upstream's
     `test_apply_macros_well_formed` and the Oracle both reject its line 1.
     (Upstream's extraction stops at the first `'`, so the checked text is `:let @/=`,
     which `let\s+` matches.)
   - `mutant-trailing-comment` now has CRLF line ends, which upstream and the Oracle
     both reject on line 1. CRLF is not a strong test of the newline translation,
     because `str.strip()` removes the `\r` anyway, and the translation matters only for
     a bare `\r`. But a script with bare `\r` line ends cannot pass natively either:
     Vim sees one line. So no stronger mutant exists, and this one is acceptable.
   - The two attacks are aimed at this task.
8. Divergences: `qualification.json` reports no problems. Every SecureBench run records
   the digest above and SecureBench commit `57c0ac07`, with a clean tree, and every run
   was rejudged. All five mutants get the same verdict from both graders. The native
   results for unchanged candidates are cached, which is correct because those scripts
   did not change. The two divergences are the two attacks (native 1.0, SecureBench
   `failed`), and their explanations hold.
9. Inventory: there is no row yet in `conversions/inventory.tsv`. The coordinator adds
   it, and there is no exclusion reason to check.

Earlier findings:
- Backtracking difference: fixed. "Catastrophic backtracking in upstream's
  file-command pattern (more lenient)" records it with measurements, and the scan bullet
  says it is equivalent except for this case.
- Missing mutants: fixed (see point 7).
- Scope bounds: fixed (raised to the maxima and recorded).

Findings:
- None that block approval. One correction for the backtracking bullet: "from about 26
  digits after a `:`, the check plus the Vim run exceed the native verifier's 1,200
  seconds" overstates the effect. The bullet's own figures (23.84 s at 22 digits, about
  4 times per 2 digits) give about 380 s at 26 digits. Adding the roughly 100 s Vim run
  gives about 480 s, well under 1,200 s. The native failure starts at about 27 to 28
  digits, as the bullet's "from about 28 the check alone does" says. The conclusion is
  unaffected.

Verdict: approved
