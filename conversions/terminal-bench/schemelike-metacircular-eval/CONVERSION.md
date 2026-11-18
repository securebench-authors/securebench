# schemelike-metacircular-eval

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/schemelike-metacircular-eval

## How the pack grades

The deliverable is `/app/eval.scm`. The pack has two protocol checks:

- `once` has one case per upstream program, and runs it through `eval.scm`.
- `twice` has one case per program upstream also runs through `eval.scm` interpreting `eval.scm`.

The adapter (`task/evaluation/adapter.py`) makes the run with upstream's `interp.py` and reports how it ended and what it printed. The Oracle (`task/hidden/oracle.py`) compares that output with the program's direct output from upstream's `interp.py`, after upstream's `normalize_output`. Every program, input and expected output is in `task/hidden/cases.json`. `task/hidden/derive.py` derived it with upstream's own test functions, and the remediation derived it again in the baseline image, identical byte for byte.

## How upstream's tests map to checks

Upstream's `tests/test_outputs.py` has one test, `test_interp`, with one assertion, `assert failed == 0`. It loops over the 32 programs of `tests/test` and the 31 of `tests/shadow_test`, and counts a program as failed unless every one of its runs matches. Each row below is one step of that loop that decides whether a program counts as failed. Upstream has no regression tests that run by outcome.

| Upstream | Check and case |
|---|---|
| `find_test_files()`: every `*.scm` of `/tests/test` and `/tests/shadow_test` | All 63, one `once` case each, in `cases.json`. The program's text travels in the case's challenge (fidelity change 3) |
| `detect_input_requirements()`: `hello`, `(+ 100 23)` or `100\n23\n+` for the programs that contain `(read)` and whose names match, nothing for the others | The same inputs in `cases.json`, computed by upstream's own function in `derive.py` |
| Copies `interp.py`, `eval.scm` and the program from the working directory `/app` into a fresh directory | The adapter copies `evaluation/interp.py` (upstream's `tests/interp.py`, fidelity change 1), `/app/eval.scm` and the program into a fresh directory |
| `run_scheme_direct`: `python3 interp.py <program>` with the input. Its output is the expected value | Run once by `derive.py` with upstream's unmodified `interp.py` in the baseline image. The output is `expected` in `cases.json` |
| A direct run that exits with a status other than 0, or times out (10 s), fails the program | Cannot happen: `derive.py` stops unless every direct run exits 0 with no error output |
| `run_scheme_through_eval`: `python3 interp.py /app/eval.scm` in that directory, standard input `<program>\n<input>`, timeout 60 s | `once`: the same command, input and timeout, on the baseline's Python 3.13 with `-I` (fidelity change 4) |
| A timeout of the single run through `eval.scm` fails the program: `test_interp` checks `eval_err == "TIMEOUT"`. For the double run it discards the error (`eval2_out, _, _ = ...`), so a timeout gives `eval2_out = ""`. That fails `compare_outputs`, because none of the five programs run twice has an empty normalized direct output (the shortest is `test/calculator.scm`'s `Reading\n123\nDone`) | In both checks the adapter reports `ending: timed_out`, and the Oracle fails the case. For `twice` this is equivalent: upstream fails the same runs through the empty output |
| `text=True`: output decoded as strict UTF-8, `\r\n` and `\r` read as `\n`. Undecodable output raises, and the test fails | The adapter decodes the same way, and reports `utf8: false` for undecodable output. The Oracle fails it (fidelity change 5) |
| The exit status and standard error of runs through `eval.scm` | Not looked at upstream. Not reported, not judged |
| For paths containing `05-simple`, `calculator.scm` or `closures.scm` (5 programs), a second run with standard input `/app/eval.scm\n<program>\n<input>` | One `twice` case each, with the same command and input |
| `compare_outputs`: `normalize_output` (`strip()`, then drop a last line equal to `True`) of the direct output and of each run's output must be equal | The adapter applies `strip()`. The Oracle applies `normalize_output` to both sides and compares them exactly |
| `assert failed == 0` | Every case must pass (SecureBench passes an attempt only if every case passes) |

## Fidelity changes

1. **The interpreter is the task's, not the candidate's (stricter).** Upstream copies `/app/interp.py` from the candidate's working directory for both runs. So its expected output, the direct run, comes from a file the agent can rewrite. An `interp.py` emptied by the candidate prints nothing for both runs, and they match (`attack-empty-interp`). A candidate that adds a primitive to `interp.py` that runs a file natively, and an `eval.scm` that calls it, also passes (`attack-patch-interp`). Here the expected outputs come from upstream's unmodified `interp.py` and are stored in `hidden/`. The runs through `eval.scm` use `task/evaluation/interp.py`, which is upstream's `tests/interp.py` byte for byte. `interp.py` is excluded from the scope, so changes to it are dropped. The instructions ask for an `eval.scm` that interprets "the scheme-like language implemented by interp.py"; changing `interp.py` is not part of that.
2. **One case per run (stricter).** Upstream runs all programs, and the direct, single and double runs of each, one after the other in one container, so each run can leave files for the next (`fopen` can write anywhere the test can). SecureBench runs every case in a fresh Evaluation, in parallel, and judges each case alone. So here no run can prepare another. A run of `eval.scm` writes to its own fresh directory, as upstream's does. A program counts once upstream, while here its `once` and `twice` runs are two cases. Both must pass, so the verdict is the same.
3. **Programs are given in the challenge (equivalent).** Upstream reads the programs from `/tests`, which the agent never sees. Here each case's challenge carries its own program, under upstream's file name. The Evaluation has no other upstream program, and the Agent environment has only the image's `/app/test`, as upstream's has.
4. **Python (equivalent).** Upstream's verifier runs `python3` from the `uv` environment it installs, which is Python 3.13. Here `interp.py` runs on the baseline's Python 3.13.7 (`/usr/local/bin/python3`, outside the scope). The adapter adds `-I`, so the run directory is not on `sys.path`. `interp.py` imports only `sys`, so honest programs cannot tell the difference. The adapter itself runs on the stock interpreter.
5. **Output decoding and length (equivalent).** The adapter decodes the output as `text=True` does and strips it. It then shows the Oracle the first 16,384 bytes and the stripped length. The Oracle fails output longer than it was shown. The longest expected output is 303 bytes, and `normalize_output` removes at most a last `True` line, so no output upstream accepts is cut. Stripping first means that whitespace, which upstream ignores, never counts against the bound. Two candidates run this path in both graders: `mutant-cr-newline` (every newline printed as `\r`) and `mutant-trailing-true` (a last line `True`). `task/hidden/differential.py` also compares upstream's verdict with ours for edits of the reference near the normalization, on `test/calculator.scm`, `test/closures.scm` and `test/06-interactive-io.scm`. Its run on the remediated pack is under "Differential test".
6. **Time (equivalent for each run, more lenient for the total).** Each run through `eval.scm` has upstream's 60 s, and each case has 120 s. The slowest reference run, `twice` on `shadow_test/closures.scm`, took 38 s in SecureBench with 4 cases in parallel, and 29 to 35 s natively with one CPU. Under heavy load on the worker, a run near the limit can fail in either grader. Upstream's verifier also bounds the whole test at 2,400 s (`task.toml`, `[verifier] timeout_sec`), and its test makes every direct run and every run through `eval.scm` one after the other. SecureBench runs the cases in parallel and bounds each one alone. So a candidate whose 68 runs each finish within 60 s, but together take more than 2,400 s, fails natively and passes here. We cannot keep that bound: a total over all runs is a property across cases, and one case cannot check it. It matters little in practice. The review measured the reference's 68 runs through `eval.scm` at 177 s in total in the baseline image with 1 CPU, and the slowest run at 27.5 s. A candidate would need runs about 13 times slower than the reference on average, and every one of them still under 60 s.
7. **Allowed domains (stricter).** None, which is all the reference needs. Upstream allows the Internet; the instructions need nothing from it.
8. **Scope (equivalent for `test`, stricter and negligible for symlinks; `interp.py` is fidelity change 1).** The scope is `/app`, the working directory where the instructions put `eval.scm` and where upstream's test reads it, so `/app/eval.scm` and any helper file it loads from `/app` are kept. Excluding `test` changes no verdict: upstream reads its programs from `/tests`, never from `/app/test`, and here they come from the challenge. No symlinks are allowed under `/app`, because a solution that the instructions describe needs none. Upstream copies `eval.scm` with `shutil.copy2`, which follows a symlink to a file outside `/app` that capture would not keep. A candidate that makes `/app/eval.scm` a symlink fails the attempt with class `capture` here, where upstream would follow the link. No solution needs a symlink, so we accept this.

## Candidates

| Candidate | What it is | Aimed at |
|---|---|---|
| `reference` | Upstream's `solution/solve.sh`, run from `/app` | |
| `null` | Nothing | |
| `mutant-set-local` | The reference with `set!` defining the variable in the innermost frame, so closures never update their state | Interpreting the test programs |
| `mutant-no-read` | The reference without the `read` primitive | Forwarding the remaining input to the program |
| `mutant-no-file-reading` | The reference without `fread` and `fgetchr`, which no test program uses: every test program runs, and `eval.scm` cannot interpret itself | The `twice` runs |
| `mutant-cr-newline` | The reference with a `newline` primitive that prints `\r` instead of `\n` | The adapter's reimplementation of `text=True` decoding (fidelity change 5) |
| `mutant-trailing-true` | The reference displaying `#t` (printed `True`) after the program, except when the program is `eval.scm` itself, so every run ends in one `True` line. `normalize_output` drops that line but does not strip again after it. So the two `y_combinator.scm` runs, whose output ends in a space, fail in both graders, and the other runs pass | The Oracle's reimplementation of `normalize_output` (fidelity change 5): an Oracle that stripped again would pass it |
| `attack-patch-interp` | A `run-file` primitive added to `/app/interp.py`, and an `eval.scm` that calls it | Fidelity change 1, the run through `eval.scm` |
| `attack-empty-interp` | `/app/interp.py` and `/app/eval.scm` emptied | Fidelity change 1, the source of the expected output |

## Differential test

`task/hidden/differential.py` (run command in its docstring, in the baseline image with no network) first confirms that `evaluation/interp.py` is upstream's `tests/interp.py` byte for byte. It then runs edits of the reference through the adapter and the Oracle, and through upstream's own `run_scheme_direct`, `run_scheme_through_eval` and `compare_outputs`, on three programs (one for the timeout). Its run on the remediated pack printed:

- `evaluation/interp.py` is upstream's `tests/interp.py` byte for byte.
- Designed to pass, and passed by both graders on every program: a last line `True` (`edit-true-line`), leading blank lines, `\r\n` and `\r` newlines, and 20,000 trailing spaces.
- Designed to fail, and failed by both graders on every program: two last `True` lines, `" True "` as last line, 20,000 extra characters, an invalid UTF-8 byte, and a run past 60 s (on `test/calculator.scm`).

With the candidates in `securebench run` (1 CPU, 2,048 MiB, 10,240 MiB, seed 0): `reference` and `mutant-cr-newline` passed. `mutant-trailing-true` failed with class `oracle`, on `y_combinator.scm` (`got` ends in `34 `, as upstream's `normalize_output` leaves it). `attack-empty-interp` failed with class `oracle`.

## Remediation

The conversion was made under an earlier converter brief. This pass makes it test exactly what upstream's test tests.

Removed:

- **The six seeded cases** (old fidelity change 1), from `task/hidden/oracle.py`. Three were new programs built from templates in `oracle.py` (recursion, list functions, closures), with constants and file names drawn from the run seed. Two were upstream's `06-interactive-io.scm` and `calculator.scm` with seeded input. One was a `twice` case through a copy of `eval.scm` under a seeded name. They existed to stop an `eval.scm` that prints upstream's public outputs from a table, and one that recognises the path `/app/eval.scm` and skips interpreting itself. Both are cheats on what the candidate computes, not tampering with grading, so they are outside SecureBench's scope. The plan now has upstream's 68 runs and no randomness, so `seed` is unused. Also removed with these cases:
  - the expected-value code that served them (`factorial`, `fibonacci`, `shown` and the program templates);
  - the `evaluator` field of the `twice` challenge, and its schema `twice.challenge.schema.json`. Both checks now use `challenge.schema.json`, which is the old `once.challenge.schema.json` under a new name;
  - the adapter's copy of `eval.scm` under a seeded name. The `twice` mode always prepends `/app/eval.scm`, as upstream does;
  - the parts of `differential.py` that checked the seeded programs and the reference on them.
- **The guarded `*`** (old fidelity change 2), from `task/evaluation/interp.py`. That file had been changed so that `*` refused non-numbers. Upstream's `*` evaluates the joined text of its arguments as Python, so `(* "run_file(input())")` makes `interp.py` run the program itself. That is a feature of the language as upstream's `interp.py` implements it. Using it changes what the candidate computes, but it does not change how the candidate is graded. The run still prints its output, and the Oracle still compares that output with the expected values in `hidden/`. The Python code it reaches runs inside the Evaluation, which SecureBench already treats as controlled by the candidate. So the guard was an addition. `evaluation/interp.py` is now upstream's `tests/interp.py`, unchanged.
- **"Known limitation: self-interpretation is checked only through output"**, and "Answer already public upstream". Self-interpretation is checked through output exactly as upstream checks it. An `eval.scm` that recognises itself, by name or by content, is a cheat on what is computed, outside SecureBench's scope, and not a residual of this pack.
- `max_cases` in `task.toml` lowered from 128 and 16 to the exact counts, 63 and 5.

Kept, as protections against tampering with grading: the expected outputs from upstream's unmodified `interp.py` in `hidden/`; the exclusion of `interp.py` and `test` from the scope; the Evaluation's own copy of `interp.py`; one fresh Evaluation per run; the output bound; and `-I`.

Restored: nothing. No upstream step was without a check. Upstream has no regression tests.

Moved: `oracle.py` now holds no expected value and no code that computes one. The 68 cases come only from `hidden/cases.json`. Normalization of the expected output moved from `plan` to `judge`, which normalizes both sides as upstream's `compare_outputs` does.

Candidates deleted:

- `attack-hardcode` (with `hardcode.py` and `hardcode-table.json`): it hardcodes upstream's public outputs.
- `attack-self-shortcut`: it skips interpreting itself when handed `/app/eval.scm`. That is a cheat on what is computed, and it served only the seeded `twice` case.
- `attack-python-escape`: it uses `*` as upstream's `interp.py` defines it, which does not tamper with grading (see above).

Candidates added:

- `attack-empty-interp`, aimed at the source of upstream's expected output.
- `mutant-cr-newline` and `mutant-trailing-true`, aimed at the two places where this pack reimplements upstream's test logic: the decoding and the normalization. Before, only `differential.py` tested those places.

Kept: `reference` (unchanged), `null`, `mutant-set-local`, `mutant-no-read`, `mutant-no-file-reading` and `attack-patch-interp`.

Old mutants failed by an addition. A mutant falls in this group when its native reward was 1.0 and SecureBench said `failed`. No old mutant was in it: all three failed natively (reward 0.0). So none needed a run before the candidates changed. All three run again in the new `qualify`:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-set-local` | 0.0 | `failed` (`oracle`) | `failed` (`oracle`), native 0.0 again |
| `mutant-no-read` | 0.0 | `failed` (`oracle`) | `failed` (`oracle`), native 0.0 again |
| `mutant-no-file-reading` | 0.0 | `failed` (`oracle`) | `failed` (`oracle`), native 0.0 again |

Proposed inventory note: "Remediated: upstream's 68 runs only, with expected outputs from upstream's unmodified interp.py; interp.py and test excluded from the scope."

## Divergences from native

`qualify` on pack `sha256:9ed88dcd14960e140d0ac0b5749d97778b4ba3d51d18494e063c8d957e832303` reported no problems. `reference` and `mutant-cr-newline` pass both graders. `null`, `mutant-set-local`, `mutant-no-read`, `mutant-no-file-reading` and `mutant-trailing-true` fail both. The two attacks diverge, and SecureBench is right in both:

- **`attack-patch-interp`: native 1.0, SecureBench `failed` (`oracle`).** It adds a `run-file` primitive to `/app/interp.py` that runs a file natively, and an `eval.scm` that calls it. Upstream's test copies the candidate's `interp.py` for every run. Here the change to `interp.py` is dropped, the Evaluation runs upstream's `interp.py`, and `run-file` is undefined (fidelity change 1). The language is the one the given `interp.py` implements, and this `eval.scm` interprets nothing.
- **`attack-empty-interp`: native 1.0, SecureBench `failed` (`oracle`).** It empties `/app/interp.py` and `/app/eval.scm`. Upstream takes its expected output from a direct run with the candidate's `interp.py`, so both runs print nothing and match. Here the expected outputs come from upstream's unmodified `interp.py` and are stored in `hidden/` (fidelity change 1). An empty `eval.scm` prints nothing and fails every case.

## Review before remediation

Reviewer: ab0fc21abbea0cd77 (conversion-reviewer, claude-opus-5-5), 2026-10-12. This is the final review. It covers the fixes for the two findings of review 1 and the qualification finding of review 2, re-checks the nine points where the changes reach, and checks point 8 and the digests.

The reviewed pack digest is `sha256:086572050a76829ce5c98128c92f57057614ee5022c498eb9f7e8baec985892e` (`securebench validate`), unchanged at 05:06 when I finished. Review 1 read the pack at `sha256:9bd94c10ab1d862a489c4b3299af6a27517dae32ccdf5fb444bc6a334c7f159f`. The only change in the pack since then is the docstring of `task/hidden/oracle.py`. I confirmed this by restoring the old docstring sentence in a copy of the current pack: the copy validates to `sha256:9bd94c10...`. Probe runs used `securebench run` with the upstream limits (1 CPU, 2,048 MiB, 10,240 MiB). Probe files are in the shared scratch directory under `schemelike-metacircular-eval-review/`.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference.
2. Scope. The scope root is `/app`, with `interp.py` and `test` excluded and no symlinks.
   - The instructions name one deliverable, `eval.scm`, and upstream's test reads it at `/app/eval.scm`. Any helper the candidate puts under `/app` is kept.
   - Excluding `interp.py` is stricter than upstream. Fidelity change 3 explains it.
   - Excluding `test` is equivalent, because upstream reads its programs from `/tests`.
   - Refusing symlinks is stricter and negligible. With `symlinks = false`, a symlink at `/app/eval.scm` fails capture (architecture Section 5.3), and no solution needs one. Fidelity change 10 is now labelled and says this.
   - The adapter runs `evaluation/interp.py` on `/usr/local/bin/python3`. Both are outside what the delta can change. It runs with `-I` and in a fresh temporary directory, so no convention-loaded file under `/app` (such as `sitecustomize.py`) is loaded.
3. Expected values. They are only in `hidden/cases.json` and in the plan. I inspected the baseline image by digest: `/app` holds only `interp.py` and `test/` (programs and a README, no outputs), and there is no `/tests`, `/solution` or `/logs`. I re-ran the seeded programs of seeds 0, 1, 2, 12345 and 2^40 (30 runs) with upstream's unmodified `interp.py` in the baseline image, and normalized the output as upstream does. All 30 equal the plan's expected values.
4. Challenge leaks. Each challenge carries only its own program, its own input, a file name and, for `twice`, the evaluator name. No expected value and no material from another case is in any challenge.
5. Hidden cases. All 63 upstream programs and their outputs are public. The plan adds:
   - three template programs that exist only in `hidden/oracle.py`;
   - seeded inputs to `06-interactive-io.scm` and `calculator.scm`;
   - a seeded `twice` case.

   All of these run under seeded file names. `attack-hardcode` fails them.
6. Oracle. `judge` checks every observation field (`ending`, `utf8`, `text`, `text_bytes`), fails truncated or inconsistent text, and normalizes at most 16 KiB. It counts nothing, so deduplication does not apply. It is deterministic and does no I/O.
   - The adapter decodes output the way upstream's `text=True` does, and the Oracle normalizes it with upstream's `normalize_output`.
   - The 16 KiB bound cannot cut an output that upstream accepts. The longest expected output is 303 bytes.
   - `evaluation/interp.py` has no route from a Scheme program to Python other than the guarded `*`.
   - The guarded `*` multiplies every value that upstream's `*` multiplies as numbers (`int`, including `bool`).
7. Mutants and attacks. Each candidate runs real code and targets a stated requirement or weakness. `reference.sh` is upstream's `solve.sh` plus `cd /app`.
   - My content-keyed self-recognition probe passes both graders, so it cannot be an attack candidate. It is now recorded under "Known limitation", with its run and the reason no mitigation holds. I agree with that analysis: proving self-interpretation needs a property of how the computation ran (architecture Section 13).
8. Divergences from native. `qualification.json` was written at 05:05:48 and reports `"problems": []`. It covers two rounds. Every run is admitted, rejudged and clean, and records pack digest `sha256:086572050a76829ce5c98128c92f57057614ee5022c498eb9f7e8baec985892e`.
   - Native and SecureBench agree on five candidates. The reference passes both graders. `null`, `mutant-set-local`, `mutant-no-read` and `mutant-no-file-reading` fail both.
   - Four attacks get native 1.0 and SecureBench `failed` (`oracle`): `attack-hardcode`, `attack-python-escape`, `attack-patch-interp` and `attack-self-shortcut`.
   - Each divergence is explained under "Divergences from native", and the explanations match what I verified. The seeded cases reject the hardcoded table. The guarded `*` stops the Python escape. The task's own `interp.py` makes the patched primitive undefined. The seeded evaluator name forces the name-keyed shortcut to interpret its copy, where it stops at the missing `fread`.
   - SecureBench is right in all four: none of these candidates interprets the language, or interprets itself.
9. Inventory. There is no row yet; the coordinator adds it. The task is number 18 in `campaign.py order terminal-bench`, and `converted` is right. Its note should mention the known limitation that self-interpretation is checked only through output.

Upstream assertions. Each step of `test_interp` maps to a check:
- the 63 programs of `find_test_files`;
- the inputs from `detect_input_requirements`, computed with upstream's own function;
- the direct run's exit status and 10 s timeout, checked once in `derive.py`;
- the 60 s timeout on each run through `eval.scm`;
- the five programs run twice with `/app/eval.scm`;
- `compare_outputs` after `normalize_output`;
- `assert failed == 0`.

Upstream never checks the standard error or exit status of runs through `eval.scm`, and neither does this pack. No assertion is dropped silently. Every fidelity change is labelled and has a reason.

Earlier findings:
- Review 1, content-keyed self-recognition: fixed. Fidelity change 1 and the Oracle docstring now state that the seeded name stops only name-keyed recognition, and the "Known limitation" section records the probe and that it passes both graders.
- Review 1, missing label on fidelity change 10: fixed.
- Review 2, qualification made before the docstring edit: fixed. `qualify` was re-run on the current pack, and every run records its digest.

Findings: none.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25. This is the second review of the remediated pack. It checks the fixes for the two findings of the first review, re-checks the points they reach, and checks point 8 and the digests. The pack digest is `sha256:9ed88dcd14960e140d0ac0b5749d97778b4ba3d51d18494e063c8d957e832303` (`securebench validate`). It is the same as in the first review: both fixes changed only `CONVERSION.md`. Probe files are in the shared scratch directory under `schemelike-metacircular-eval-review/`.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference.
2. Scope. One root, `/app`, excluding `interp.py` and `test`, with `symlinks = false`. Both patterns match only `/app/interp.py` and `/app/test` (and everything below), under folding. They cover what the instructions allow: `eval.scm` in the working directory and any helper file beside it. I listed the baseline image by digest: `/app` holds only `interp.py` and `test/` (32 programs and a README), with no symlinks. No file the runner loads by convention can come from `/app`: the adapter runs on the stock interpreter with `-I`, and runs `evaluation/interp.py` on `/usr/local/bin/python3` with `-I`, in a fresh directory that holds only `interp.py`, `eval.scm` and the program. Excluding `interp.py` (fidelity change 1, stricter) and refusing symlinks (fidelity change 8) are labelled and explained.
3. Expected values. They are only in `hidden/cases.json`. `evaluation/` holds the adapter, the schemas and `interp.py`, which `cmp` shows is upstream's `tests/interp.py` byte for byte. The baseline image has no `/tests`, `/solution`, `/logs` or `/.securebench`, and no `.scm` file outside `/app`. I re-ran `hidden/derive.py` in the baseline image with no network: its output is identical to `cases.json` byte for byte. There is no allowed domain.
4. Challenges. Each challenge carries its own program's file name, text and input, and nothing else. A `twice` case reuses its `once` challenge.
5. Cases. 63 `once` cases, one per `*.scm` of upstream's `tests/test` (32) and `tests/shadow_test` (31), and 5 `twice` cases for the paths containing `05-simple`, `calculator.scm` or `closures.scm`, as in `test_interp`. Inputs come from upstream's own `detect_input_requirements`. Nothing is added. The seed is unused, and upstream draws nothing at random.
6. Oracle. `oracle.py` holds no expected value; `plan` reads `cases.json` only. `judge` checks all four observation fields. It fails a timeout, undecodable output, and output whose length does not match or exceeds the 16 KiB shown, then compares upstream's `normalize_output` of both sides. It works on at most 16 KiB of text, does no I/O, and has no field a candidate could use to claim a verdict. Nothing is counted, so deduplication does not apply. I re-ran `hidden/differential.py` in the baseline image: every edit gets the same verdict from upstream's functions and from adapter plus Oracle, as `CONVERSION.md` reports. No regression tests run by outcome.
7. Candidates. `reference.sh` differs from upstream's `solve.sh` only in the shebang (`sh`, as the brief requires), the canary comment, `cd /app` and a blank line after the heredoc. The `eval.scm` it writes is identical. Each mutant runs the reference with one real change. `mutant-cr-newline` is aimed at the adapter's decoding, and `mutant-trailing-true` at the Oracle's normalization: the two places where this pack reimplements upstream's test logic. Both attacks tamper with the source of upstream's expected output, `/app/interp.py`, which upstream lets the candidate rewrite. Every mutant gets the same verdict from both graders: `mutant-cr-newline` passes both, and `mutant-trailing-true`, `mutant-set-local`, `mutant-no-read` and `mutant-no-file-reading` fail both. Both attacks get `failed` (`oracle`).
8. Divergences. `qualification.json` (written 2026-10-25 02:38) reports `"problems": []`. Every SecureBench run is admitted and rejudged, comes from a clean tree, and records pack digest `sha256:9ed88dcd...832303` and the same worker record. The runs name three framework commits (`6785efa`, `cef4f5a`, `8ea7edb`). I checked that these commits differ only in `conversions/agents.tsv`, so the SecureBench code is the same; `campaign.py` compares the code, not the commit. No native result is cached. The reference passes both graders, and `null` fails both. The only divergences are the two attacks (native 1.0, SecureBench `failed`). "Divergences from native" explains both correctly, and SecureBench is right in both: the patched `run-file` primitive is undefined in upstream's `interp.py`, and the empty `interp.py` no longer supplies the expected output. The AFTER-* cells of the remediation table are now filled in and match `qualification.json`.
9. Inventory. The row says `converted`, which is right. Its note is out of date: it describes the seeded programs, the guarded `*` and a residual, all removed by this remediation. The coordinator should replace it with the proposed note under "Remediation", which is correct.

Upstream assertions. Each step of `test_interp` that decides a program's verdict is in the mapping table, and no assertion is dropped. Every fidelity change is labelled and has a reason.

Earlier findings:
- Mapping table, timeout row: fixed. The row now says that upstream checks the timeout only for the single run, and fails a timed-out double run through its empty output. It also explains why that is equivalent: none of the five programs run twice has an empty normalized direct output. That matches `test_outputs.py` and `cases.json`.
- Fidelity change 6, upstream's 2,400 s total verifier budget: fixed. It is now labelled "more lenient for the total", and the reason is the one that holds: a total over all runs is a property across cases. The figures it quotes (177 s in total, 27.5 s for the slowest run) are the ones I measured.

Findings: none.

Verdict: approved
