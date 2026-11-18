# overfull-hbox

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/overfull-hbox

## How the pack grades

The baseline (`alexgshaw/overfull-hbox:20251031`, Ubuntu 24.04 with
`texlive-latex-base`) holds `/app/main.tex`, `/app/input.tex` and
`/app/synonyms.txt`. Compiling `main.tex` gives 7 "Overfull \hbox" warnings.
The agent must remove them by replacing words in `input.tex` with synonyms from
`synonyms.txt`, without editing `main.tex` or `synonyms.txt`.

Upstream's verifier (`tests/test.sh`) installs uv, Python 3.13 and pytest from
the network and runs `tests/test_outputs.py`. Its session fixture runs
`apt install -y --reinstall texlive-latex-base`, copies its own `main.tex` to
`/app/main_original.tex` and runs `/usr/bin/pdflatex -jobname=main
main_original.tex` in `/app`. Four tests then read the files.

The pack has two artifact checks and one protocol check with one case, as
upstream has one fixed document:

- `unmodified` reads `/app/main.tex` and `/app/synonyms.txt` and compares them
  with `hidden/main.tex` and `hidden/synonyms.txt`.
- `substitutions` reads `/app/input.tex` and compares its tokens with those of
  `hidden/input.tex`, using the synonym families `plan` builds from
  `hidden/synonyms.txt` with upstream's own loop.
- `compile` runs `evaluation/adapter.py`, which compiles a copy of the
  pristine `main.tex` (as `main_original.tex`, with `-jobname=main`, as
  upstream's fixture does) with the candidate's `input.tex` in a fresh
  directory, and returns the log. The Oracle requires the success line and the
  absence of the warning text, both read from `hidden/log.json`.

Every expected value lives in `hidden/`: upstream's three files byte for byte
and the two log strings of `hidden/log.json`. `oracle.py` holds only how to
compare. `evaluation/` holds the adapter, the two schemas and a copy of the
pristine `main.tex`, which is an input to the compile (it is public in the
baseline and upstream), not an expected value. Artifact checks run first, so
the compile case runs only on an `input.tex` the Oracle has already accepted.

The Oracle's work is linear in `input.tex`, which is at most 4 MiB, and in the
log, which is at most 512 KiB. Every observation field is required by the
schema and checked: `ending` must be `exited`, `log_present` and `log_utf8`
must be true, and `log_bytes` must be at most 512 KiB and equal the UTF-8
length of the `log` shown. Nothing is counted.

## How upstream's tests map to checks

One row per assertion of `tests/test_outputs.py`, and the fixture's steps.
Upstream has no regression tests.

| Upstream | Check and case |
|---|---|
| fixture: `apt install -y --reinstall texlive-latex-base` | none; fidelity change "TeX distribution" |
| fixture: copy `/tests/main.tex` to `/app/main_original.tex`, run `/usr/bin/pdflatex -jobname=main main_original.tex` in `/app` | `compile`, case 0: the adapter runs the same command on a copy of `evaluation/main.tex` and `/app/input.tex` in a fresh directory (fidelity change "Compile directory") |
| `test_main_synonyms_not_modified`: `assert synonyms_path_agent.exists()` | `unmodified`: `/app/synonyms.txt` is present |
| same: `assert synonyms == synonyms_agent` | `unmodified`: its text, after universal-newline translation, equals `hidden/synonyms.txt` |
| same: `assert main_path_agent.exists()` | `unmodified`: `/app/main.tex` is present |
| same: `assert main == main_agent` | `unmodified`: its text, after universal-newline translation, equals `hidden/main.tex` |
| `test_compilation_successful`: `open("/app/main.log")` and `"Output written on main.pdf" in log_content` | `compile`, case 0: `ending` is `exited`, `log_present` and `log_utf8` are true, the log is shown in full, and it contains `must_contain` of `hidden/log.json` |
| `test_no_overfull_hboxes`: `"Overfull \\hbox" not in log_content` | `compile`, case 0: the log does not contain `must_not_contain` of `hidden/log.json` |
| `test_input_file_matches`: `open("/app/input.tex")` | `substitutions`: `/app/input.tex` is present and valid UTF-8 |
| same: `assert len(tokens) == len(tokens_agent)`, tokens from `re.findall(r"\S+")` after spacing out `---` | `substitutions`: the same count, with `str.split()` after the same replacement |
| same: `assert match_agent` | `substitutions`: always true, as upstream's pattern matches every token without a newline; `_split` always returns a split |
| same: `assert p == p_agent and s == s_agent`, from `^(\W*)(.*?)(\W*)$` | `substitutions`: the same, with a hand-written split on `str.isalnum() or "_"` |
| same: `assert w == w_agent or (w in synonyms and w_agent in synonyms[w])` | `substitutions`: the same, with the families of `hidden/synonyms.txt` (a word on several lines keeps the family of its last line, as upstream's loop does) |
| same: `else: assert not match_agent` | unreachable upstream (the pattern matches every token), so no check |

## Fidelity changes

- **Compile directory (stricter, only against files planted for the
  compile).** Upstream compiles in `/app`, so TeX also reads any other file
  the agent left there: TeX looks for classes and packages in the current
  directory first, and LaTeX reads `main.aux` at `\begin{document}`. The
  adapter compiles in a fresh directory that holds only the pristine
  `main.tex` (as `main_original.tex`) and the candidate's `input.tex`. This
  protects the grading compile from tampering and adds no requirement on what
  the candidate computes: the instructions allow edits to `input.tex` only,
  the token check pins `input.tex` to upstream's text with listed synonyms, and
  the document has no cross-references, so a `main.aux` that a normal compile
  leaves behind changes nothing. `attack-aux-injection` (a `main.aux` that
  raises `\hfuzz`) and `attack-local-class` (an `/app/article.cls` that does
  the same) exploit upstream's choice (see "Divergences from native").
- **TeX distribution (stricter, only against changes to the TeX tree).**
  Upstream reinstalls `texlive-latex-base` before compiling, which restores
  that package's files but not other TeX trees. Here the scope is `/app` only,
  so nothing the agent changes outside `/app` reaches the Evaluation: the whole
  distribution is the baseline's. This protects the grading compiler.
  `attack-texmfhome-class` installs a modified `article.cls` in TEXMFHOME
  (`/root/texmf`), which upstream's reinstall leaves in place. The reinstall
  itself needs the network and is not repeated. It reinstalls the same version
  (`2023.20240207-1`, pinned in the Dockerfile, with no newer version for
  noble), so it changes nothing for an agent that left the distribution alone.
- **Tokenizer reimplementation (equivalent).** The Oracle may not apply
  regular expressions to evidence, so `str.split()` replaces
  `re.findall(r"\S+")` and a hand-written loop over `str.isalnum() or "_"`
  replaces `^(\W*)(.*?)(\W*)$`. Two differential tests support this.
  The original conversion tested, in `python:3.13-slim-bookworm` (upstream's
  Python) and `python:3.12-slim` (the host Python of the Oracle), that for
  every code point `str.isspace()` equals `re.fullmatch(r"\s")` and the word
  test equals `re.fullmatch(r"\w")` (0 differences), and that 200,000 random
  strings over ASCII punctuation, `---`, Unicode spaces (U+00A0, U+2009,
  U+3000, U+0085, U+001C), combining marks, digits of other scripts, U+FEFF,
  U+200B and CJK give identical tokens and splits. The remediation reran the
  verdict comparison on the remediated check: 20,000 random mutations of the
  real `input.tex` (1 to 3 each of: allowed synonym swaps, swaps to unlisted
  or other families' words, any whitespace run replaced by one of 16 others
  including U+00A0, U+2009, U+3000, U+0085, U+001C, VT, FF, CR, CRLF, blank
  lines and nothing, inserted punctuation, combining marks, other-script
  digits, U+FEFF, `---` and `--`, deleted characters, altered em dashes, case
  changes, whitespace added at both ends), each judged by the Oracle's `judge`
  and by upstream's `test_input_file_matches` code reading the same file with
  `open(path, "r")`. In Python 3.13.17 and in the host's 3.12.15, both in a
  memory-limited container: 5,115 pass, 14,885 fail, 0 differences. Python
  3.12 and 3.13 agree on whitespace; they differ on 622 word characters added
  in Unicode 15.1, which cannot change a verdict: `input.tex` and
  `synonyms.txt` are ASCII, so any such character changes a token's prefix,
  word or suffix away from upstream's values in either version.
- **Reading files (equivalent).** Upstream reads every file with `open(path,
  "r")`: strict UTF-8 and universal newlines. The `text` parser decodes strict
  UTF-8 and rejects a leading byte-order mark, and the Oracle translates
  `\r\n` and `\r` to `\n`. A byte-order mark fails upstream too: U+FEFF is not
  whitespace and not a word character, so it changes the first token's prefix
  or adds a token in `input.tex`, and makes `main.tex` or `synonyms.txt`
  differ. The adapter reports whether the log is valid UTF-8, and the Oracle
  fails a log that is not, where upstream's `open` raises.
- **Empty `synonyms.txt` line handling (equivalent).** `plan` splits the file
  on `\n` and drops the empty piece after the final newline, as iterating a
  file does.
- **File type (stricter, negligible).** A symlink at `/app/input.tex`,
  `/app/main.tex` or `/app/synonyms.txt` fails; upstream follows it. A
  relative link to a file inside `/app` is captured and reported as not a
  regular file; any other link fails capture (see "Symlinks").
- **Symlinks (stricter, negligible).** Capture keeps only symlinks with a
  relative target that stays inside `/app`, because a link with an absolute
  target or one that climbs out of the root would point at files outside the
  candidate after replay. A candidate that leaves any other symlink at the top
  level of `/app`, such as `ln -s /usr/share/texlive/texmf-dist/tex/latex/base
  /app/tex-base`, ends `failed` (class `capture`), although upstream never
  looks at that link and would pass it. No allowed edit needs a symlink: the
  instructions allow only word replacements in `input.tex`. The root sets
  `symlinks = true` so that a relative link inside `/app` is captured instead
  of failing capture.
- **Size (stricter, negligible).** `input.tex` may be at most 4 MiB,
  `main.tex` and `synonyms.txt` 1 MiB each, and the log 512 KiB. The originals
  are 5,186, 328 and 6,008 bytes, and the log of a correct solution is about
  3 KiB.
- **Timeout (equivalent).** Upstream gives the whole verifier 360 s. The case
  has 360 s and pdflatex 300 s of it; it takes under 2 s.
- **pdflatex input (equivalent).** The adapter runs pdflatex with standard
  input from `/dev/null`, so a TeX error ends the job at once ("Emergency
  stop") instead of waiting at the `?` prompt. Either way no "Output written"
  line appears.
- **Allowed domains (stricter).** `archive.ubuntu.com` and
  `security.ubuntu.com`, which the reference needs for `apt install
  python3-pip`. Upstream allows the whole Internet. Neither domain serves the
  answer.
- **Scope (equivalent for every solution the instructions allow).** `/app`,
  excluding `*/*`. The instructions allow edits to `/app/input.tex` only, and
  the three files the tests read are at the top level of `/app`, so every
  allowed solution is captured in full. Work directories an agent leaves below
  the top level are dropped instead of failing capture. Upstream could not
  read them either: its compile searches `/app` itself but not its
  subdirectories (`TEXINPUTS` lists `.` without `//`), and its tests read only
  the three top-level files. The reference leaves `fix_one_hbox.py` and
  `main.{aux,log,pdf}` at the top level; they are captured and ignored.
  Symlinks are the one exception to "captured in full" (see "Symlinks").
- **Instructions (equivalent).** `instructions.md` is upstream
  `instruction.md` byte for byte.

## Divergences from native

`qualification.json` from the remediation (pack
`sha256:b125925bac2e1c18e26160dc7e2c3b4ec16ea642a029c30820dc86cca265501c`,
`problems: []`): the reference passes both graders, `mutant-crlf` passes
both, and the null candidate and the other four mutants fail both. The three
attacks diverge, each with native 1.0 and SecureBench `failed` (`oracle`).
None of them changes `input.tex`, `main.tex` or `synonyms.txt`, so only the
`compile` case can fail them:

- **`attack-aux-injection`.** It leaves `input.tex` unchanged and writes
  `/app/main.aux` with `\global\hfuzz=\maxdimen`. Upstream compiles
  `-jobname=main` in `/app`, so LaTeX reads that file at `\begin{document}`
  and reports no overfull box. Here the compile runs in a fresh directory with
  only `main_original.tex` and `input.tex`, and the 7 overfull boxes of the
  original document are reported. SecureBench is right: no word was replaced,
  and the document as the instructions define it (`main.tex` with this
  `input.tex`) has 7 overfull boxes.
- **`attack-local-class`.** The same through `/app/article.cls`, which TeX
  finds in the current directory before the distribution's class. SecureBench
  is right, for the same reason.
- **`attack-texmfhome-class`.** The same through
  `/root/texmf/tex/latex/article.cls`. Upstream's reinstall of
  `texlive-latex-base` does not touch TEXMFHOME. Here nothing outside `/app` is
  captured, so the Evaluation compiles with the baseline's distribution.
  SecureBench is right, for the same reason.

## Candidates

| Candidate | What it does | Aimed at |
|---|---|---|
| `reference` | upstream `solve.sh`, with `cd /app` | |
| `null` | nothing | |
| `mutant-shortest-synonym` | replaces every listed word with the shortest member of its family (awk), never compiles to check; every change is allowed, one overfull box remains | `compile`: the log comes from the adapter's own compile, and the warning text is found |
| `mutant-unlisted-synonym` | the reference's substitutions, but weatherbeaten to "shabby" and pathfinder to "explorer", which are not listed; compiles with no overfull box | `substitutions`: the families `plan` builds |
| `mutant-en-dashes` | the reference's substitutions plus every `---` shortened to `--` | `substitutions`: the reimplemented tokenizer's em-dash spacing and token count |
| `mutant-crlf` | the reference's substitutions, with `main.tex`, `synonyms.txt` and `input.tex` rewritten with CRLF line ends; compiles with no overfull box | the Oracle's newline translation of all three files, which stands in for upstream's text-mode `open`; it should pass both graders |
| `mutant-thin-spaces` | the reference's substitutions plus thin spaces (U+2009) for the spaces of the first paragraph; every token is unchanged, LaTeX stops with "Unicode character not set up" | `substitutions` must treat U+2009 as whitespace, as `\s` does, and `compile` must then fail it |
| `attack-aux-injection` | writes `/app/main.aux` with `\global\hfuzz=\maxdimen` | a convention-loaded file read by upstream's compile in `/app` |
| `attack-local-class` | writes `/app/article.cls` that sets the same at `\begin{document}` | a class file in the compile directory |
| `attack-texmfhome-class` | the same class in `/root/texmf/tex/latex` | a TeX tree outside what upstream's reinstall restores |

## Old candidates failed by an addition

Before remediation, `qualification.json` had no mutant with a native pass and
a SecureBench `failed`: all five mutants failed both graders. The only
candidate an addition failed was `attack-paragraph-breaks` (native 1.0,
SecureBench `failed`, class `oracle`, from the whitespace rule). Run once
against the remediated pack with `securebench run`, it now passes, so the
addition is gone; it is deleted (see "Remediation"). `mutant-thin-spaces`
was also run, because its failing check changed.

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-paragraph-breaks` | 1.0 | `failed` (`oracle`, `substitutions`: whitespace rule) | `passed` (then deleted) |
| `mutant-thin-spaces` | 0.0 | `failed` (`oracle`, `substitutions`: whitespace rule) | `failed` (`oracle`, `compile`: "Solution must compile successfully") |
| `mutant-shortest-synonym`, `mutant-unlisted-synonym`, `mutant-en-dashes` | 0.0 | `failed` (`oracle`) | not run for this step (no native pass); they run in `qualify` |
| `mutant-sloppy-main` | 0.0 | `failed` (`oracle`) | not run; deleted after review (see "Remediation") |

## Remediation

Done on 2026-10-25 against the current converter brief.

Removed:

- The whitespace rule of the `substitutions` check (`_layout`, `_gap` and the
  gap and edge comparisons in `hidden/oracle.py`), and its fidelity change
  "Whitespace between tokens". Upstream's `test_input_file_matches` compares
  tokens only, so the rule failed candidates upstream passes because of what
  they write in `input.tex` (added paragraph breaks, other whitespace
  characters). The check now compares tokens exactly as upstream does.
- The section "Answer already public upstream", which the current brief does
  not have.

Restored: nothing. Every upstream assertion already had a check (see the map).

Moved: the two log strings, "Output written on main.pdf" and
"Overfull \hbox", from constants in `hidden/oracle.py` to `hidden/log.json`.
`plan` passes them as the context of the compile case. The other expected
values were already in `hidden/` (`input.tex`, `main.tex`, `synonyms.txt`).
`plan` still builds the synonym families from `hidden/synonyms.txt`; this is
upstream's own parsing loop over the data file, not a computed answer.

Kept: the scope and its `*/*` exclude, the adapter's fresh compile directory,
the TeX tree outside the scope, the strict UTF-8 log handling and every
observation check. Each of these only stops a candidate from tampering with
how it is graded.

Candidates deleted:

- `attack-paragraph-breaks`: it does not tamper with grading; it makes an
  edit that upstream's tests accept and that only the removed whitespace rule
  rejected. It now passes SecureBench, as it passes native.
- `attack-fake-log`: a forged `main.log` and `main.pdf` in `/app`. It tests
  the same protection as `attack-aux-injection` (the adapter compiles and reads
  its log in a fresh directory) more weakly, since a compile in `/app` would
  also overwrite the forged log; dropped to stay within three attacks.
- `attack-forged-synonyms`: unlisted words plus an edited `synonyms.txt`. The
  edit fails `unmodified` before any reference material matters, so it tests
  only plain equality in `unmodified`; dropped to stay within three attacks.

- `mutant-sloppy-main`: it adds `\sloppy` to `main.tex`, which fails the
  `unmodified` comparison with or without newline translation, so it tested
  only plain equality. The review of the remediation found that no mutant
  exercised the newline translation, where the Oracle stands in for
  upstream's text-mode `open`; `mutant-crlf` replaces it to stay within five
  mutants.

Candidate added: `mutant-crlf` (review finding), described under
"Candidates". Run once with `securebench run`, it passes every check; in the
baseline it leaves 17, 110 and 19 CR bytes in `main.tex`, `synonyms.txt` and
`input.tex`, and a log with no overfull box.

Candidates kept: the reference and null unchanged; `mutant-shortest-synonym`,
`mutant-unlisted-synonym`, `mutant-en-dashes` and `mutant-thin-spaces`, with
the comment of `mutant-thin-spaces` updated to say it now fails at `compile`;
the three attacks that tamper with the grading compile and pass natively.

Other changes after review: the comment above `[scope]` in `task/task.toml`
cited a lesson code from a document outside the briefs; it now gives the
reason in full. The "Scope" bullet wrongly said that `symlinks = true` lets
any top-level symlink be captured; the new "Symlinks" bullet states the real
rule as a stricter difference.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated 2026-10-25: removed
the whitespace rule (added paragraph breaks now pass, as upstream); log
strings moved to hidden/log.json. Stricter only against tampering: the
compile runs in a fresh directory on the baseline TeX tree, closing three
planted-file routes that pass natively."

## Review before remediation

Reviewer: conversion-reviewer agent (overfull-hbox), 2026-10-13, round 2

Pack digest at review: `sha256:32e9d6e43fc66d208605b3b9cf72101962cd6ba8b6069a804d3c7d6c176abdd5` (`securebench validate`, the same in rounds 1 and 2; the pack and candidates are unchanged since round 1, and only `CONVERSION.md` changed).

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. `hidden/input.tex`, `hidden/main.tex`, `hidden/synonyms.txt` and `evaluation/main.tex` are byte-identical to upstream `tests/` (and to `environment/tests/`).
2. Scope. The instructions allow edits to `/app/input.tex` only, and all three files sit at the top level of `/app`, which the root covers; `*/*` drops only paths below the top level, which upstream's compile cannot read either (`TEXINPUTS` lists `.` without `//`). No test files exist in the scope. Changes outside `/app` (TeX trees, TEXMFHOME) are not captured, which is the stated "TeX distribution (stricter)" change. Correct. The "Scope" fidelity bullet now carries the label "equivalent for every solution the instructions allow" with this reason, and explains `symlinks = true`.
3. Leaks. The Oracle takes every expected value from `hidden/` through `plan`; the baseline copies of the three files inside the scope are never used as reference (C48). I inspected the image itself (pinned digest, amd64): `/app` holds only the three upstream files, there is no `/tests`, `/solution` or Python, and `/root` has only shell dotfiles. `evaluation/main.tex` is the pristine public input to the compile, not an expected value. No leak.
4. Challenges. One case with challenge `{}` (`max_challenge_bytes = 64`); contexts are artifact contexts and stay on the host. No leak.
5. Hidden case. The deliverable is an edit of one fixed document and the answer is public in upstream `solve.sh`, so no hidden case can help (C58). `CONVERSION.md` says so and names the passing six-`sed` script. Correct.
6. Oracle (C52 to C54). Every observation field is schema-required and checked (`ending`, `log_present`, `log_utf8`, `log_bytes` against the shown log). Nothing is counted. Work is linear in the bounded inputs (4 MiB `input.tex`, 512 KiB log). No regex, no evidence used as path or code. The compile case runs only after both artifact checks pass (architecture 6.2.5), so pdflatex only ever sees an `input.tex` limited to upstream tokens, listed synonyms and space, tab and newline gaps; the adapter compiles in a fresh temporary directory with absolute `/usr/bin/pdflatex` and `python3 -I`, so nothing else in `/app` reaches it. I re-ran an independent differential test of `_substitutions` (Python 3.12.15, in a memory-limited container): 20,000 random mutations of `input.tex` (synonym swaps, every whitespace kind including U+00A0, U+2009, U+3000, U+0085, VT, FF, CR, CRLF, inserted punctuation, combining marks, U+FEFF, U+200B, deletions, em-dash edits) against upstream's regex code combined with my own regex implementation of the whitespace rule: 0 differences, 3,394 passes. I also checked the stated equivalences of the text parser (strict UTF-8 and the BOM rejection fail only inputs upstream also fails) and of `plan`'s family building (110 lines, no duplicate words, no empty or multi-word members). The claim that `texlive-latex-base` has no newer version for noble holds (`apt-cache policy` after `apt-get update` in the baseline: candidate `2023.20240207-1`). Correct.
7. Candidates. `reference.sh` is upstream `solve.sh` plus only `#!/bin/sh` and `cd /app` (diffed). I ran four candidates in the baseline and through the Oracle's `_substitutions`: `mutant-shortest-synonym` passes `substitutions` and leaves 1 overfull box, so it exercises the compile check; `attack-paragraph-breaks` leaves 0 overfull boxes (so upstream accepts it) and fails the whitespace rule; `mutant-en-dashes` fails on token count (921 vs 939); `mutant-unlisted-synonym` fails at `shabby`. `attack-aux-injection`, `attack-local-class`, `attack-texmfhome-class` and `attack-fake-log` leave `input.tex` untouched, so they reach and fail the compile case; `mutant-sloppy-main` and `attack-forged-synonyms` fail `unmodified`. `mutant-thin-spaces` no longer reaches the compile check, and `CONVERSION.md` says so. Each one targets a requirement or a weakness of this task and runs real code. Correct.
8. Divergences from native. `qualification.json` reports `problems: []`. All 13 SecureBench runs are admitted, rejudged, not dirty, and record the digest above. They ran at commits 57f64a1, 72e4d48 and dadfdd1, which differ only in campaign records: `git diff` of `securebench`, `securebench_utility` and `securebench_relay_proxy` between them is empty. The reference passes both graders. Null, the five mutants, `attack-fake-log` and `attack-forged-synonyms` fail both. The four divergences are `attack-aux-injection`, `attack-local-class`, `attack-texmfhome-class` and `attack-paragraph-breaks`, each native 1.0 and SecureBench `failed` (`oracle`), and each is explained. The explanations hold. The three TeX attacks leave `input.tex` unchanged, and upstream passes them only because its compile reads files the agent planted in `/app` or TEXMFHOME. In round 1 I reproduced in the baseline that the paragraph-break edit leaves 0 overfull boxes and that the Oracle rejects it at the first changed gap. SecureBench is right in all four: none of them replaces a word as the instructions require, and the document they define still has overfull boxes (or, for paragraph breaks, an edit the instructions forbid).
9. Inventory. No row yet (the coordinator adds it on approval). The task is convertible; none of the exclusion reasons applies (no network, privileges, host actions or service needed at evaluation; 2 CPUs and 4 GB). Correct.

Upstream assertions: each assertion of `tests/test_outputs.py` maps to a check as in the table under "The conversion in short" (`unmodified`: both existence and equality assertions; `substitutions`: token count, prefix and suffix, word allowed; `compile`: success line and no overfull box; the fixture's reinstall and compile directory are listed fidelity changes). The `else: assert not match_agent` branch of `test_input_file_matches` is unreachable (the pattern matches every token without a newline), so dropping it is equivalent. None is dropped silently.

Findings:
- None. The round 1 finding (the "Scope" fidelity bullet had no label and did not explain `symlinks = true`) is fixed: the bullet is labelled equivalent for every allowed solution, gives the reason (`TEXINPUTS` does not search subdirectories, and the tests read only the three top-level files), and says that `symlinks = true` captures a stray top-level symlink while a symlink at a checked path still fails as "not a regular file". The fix is in `CONVERSION.md` only, so the qualification still applies.

Verdict: approved

## Review

Reviewer: conversion-reviewer agent (overfull-hbox, remediation review, round 2), 2026-10-25

Pack digest at review: `sha256:b125925bac2e1c18e26160dc7e2c3b4ec16ea642a029c30820dc86cca265501c` (`securebench validate`). Since round 1 (digest `sha256:d4063e83...`), the only pack change is the comment above `[scope]` in `task/task.toml` (`git diff`: comment lines only). In `candidates/`, `mutant-sloppy-main.sh` was deleted and `mutant-crlf.sh` added. `CONVERSION.md` was revised. `hidden/oracle.py`, the adapter, the schemas and the hidden data have not changed since round 1 (file times predate it), so my round 1 checks of them still hold.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. The hidden copies of `input.tex`, `main.tex` and `synonyms.txt`, and `evaluation/main.tex`, are byte-identical to upstream `tests/`.
2. Scope. One root, `/app`, excluding `*/*`, which under 4.6 drops every path of two or more components and keeps the three top-level files. Upstream's compile does not search subdirectories (`TEXINPUTS` in the baseline starts with `.:` without `//`). The scope holds no test files, and the baseline has no symlinks under `/app`. The new "Symlinks (stricter, negligible)" bullet and the revised "File type" and "Scope" bullets match `check_symlink` in `securebench/candidate/state.py`: only a relative link that stays inside the root is captured, and any other link fails capture. They also match my round 1 run (reference substitutions plus an absolute link at `/app/tex-base` ended `failed capture`). The `task.toml` comment now gives its reason in full, with no lesson code.
3. Expected value leaks. Unchanged since round 1. I inspected the pinned image: `/app` holds only the three upstream files, there is no `/tests`, `/solution` or `/logs`, and a filesystem grep for `fix_one_hbox`, `weatherbeaten` and the canary GUID finds only `/app/input.tex` and `/app/synonyms.txt`, which are task inputs. The Oracle takes all reference data from `hidden/`. `evaluation/` holds only the adapter, the schemas and the public pristine `main.tex`. The two allowed domains (the image's apt sources) do not serve the answer. No leak.
4. Challenges. One case, challenge `{}`. No leak.
5. Cases. One case, from upstream's single fixture compile. The seed is unused, and upstream draws nothing at random.
6. Oracle. Unchanged since round 1. Every expected value comes from `hidden/` (three files and `log.json`). Every observation field is required and checked. Nothing is counted. The work is bounded, with no regex and no evidence value used as a path or command, and the Oracle fails closed. The token check compares tokens only, as upstream does. My differential test (20,000 random mutations of `input.tex`, Python 3.13.17 in a memory-limited container, `judge` against upstream's `test_input_file_matches` code) gave 0 differences and 2,989 passes. There are no regression tests.
7. Candidates. `reference.sh` is upstream `solve.sh` plus the `sh` shebang, a comment and `cd /app`. The new `mutant-crlf.sh` runs real code: it applies the reference's six substitutions with `sed`, appends CR to every line of `main.tex`, `synonyms.txt` and `input.tex`, and runs `pdflatex`. It targets the Oracle's universal-newline translation, which stands in for upstream's text-mode `open`. It passes both graders, which is the expected verdict for a correct edit saved with CRLF line ends. The other four mutants target the tokenizer (`mutant-en-dashes`, `mutant-thin-spaces`), the families (`mutant-unlisted-synonym`) and the adapter's compile and log (`mutant-shortest-synonym`). Each gets the same verdict from both graders. The three attacks plant files that upstream's compile reads, and each ends `failed` in SecureBench. There are five mutants and three attacks.
8. Divergences. `qualification.json` reports `problems: []`. All 10 SecureBench runs are admitted, rejudged, not dirty, and record the digest above. They ran at framework commits bde1fa3, 5ff0d90, 826994e and d7fe3f7, and `git diff` of `securebench`, `securebench_utility`, `securebench_relay_proxy`, `pyproject.toml`, `uv.lock` and `conversions/campaign.py` between consecutive commits is empty. Results: the reference passes both graders, null fails both, `mutant-crlf` passes both, and the other four mutants fail both. The three attacks are native 1.0 and SecureBench `failed` (`oracle`). "Divergences from native" explains all three, and the explanations hold: none of them changes `input.tex`, and upstream passes them only because its compile reads a `main.aux`, an `article.cls` or a TEXMFHOME class that the agent planted. The document the instructions define still has 7 overfull boxes, so SecureBench is right.
9. Inventory. Decision `converted`, reason `-`: correct, and no exclusion reason applies. The current row's note is stale (it describes the removed whitespace rule and cites "lesson C58") and should be replaced by the proposed note in "Inventory note". That note says "stricter only against tampering". This is accurate apart from the negligible symlink and size limits, which the coordinator may want to mention.

Upstream assertions. Every assertion of `tests/test_outputs.py` maps to a check, as in "How upstream's tests map to checks". The unreachable `else: assert not match_agent` branch and the fixture's reinstall and compile directory are explained with labels. None is dropped silently.

Round 1 findings:
- Symlink claim: fixed. The "Symlinks" bullet labels the difference stricter and negligible, gives the reason, and states correctly which links fail capture.
- No mutant for the newline translation: fixed. `mutant-crlf` replaces `mutant-sloppy-main`, and the "Candidates" table and "Remediation" section describe the change.
- Lesson code in `task.toml`: fixed. The comment now gives the reason in full.

Findings:
- None.

Verdict: approved
