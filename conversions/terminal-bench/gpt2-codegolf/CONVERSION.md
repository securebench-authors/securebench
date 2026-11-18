# gpt2-codegolf

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/gpt2-codegolf

## How the pack grades

Upstream has one test, `test_gpt2_implementation` in `tests/test_outputs.py`. It asserts, in order:

1. `/app/gpt2.c` exists and `stat().st_size < 5000`;
2. `gcc -O3 /app/gpt2.c -lm`, run in `/app`, exits 0;
3. `/app/a.out gpt2-124M.ckpt vocab.bpe 'THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT'`, run in `/app` with a 90-second timeout, exits 0;
4. its stdout contains `WARRANTY OF ANY KIND, EXPRESS OR IMPLIED`.

Both commands run through `subprocess.run(..., capture_output=True, text=True)`, so the test also fails when any captured stream (compiler or program, stdout or stderr) is not valid UTF-8, and the `in` test sees stdout after universal-newline translation.

The pack maps this to two checks:

- **`source`** (artifact check) reads `/app/gpt2.c` from the captured candidate. The Oracle requires it to be a regular file smaller than 5000 bytes (assertion 1). A file that is not valid UTF-8 is still judged by its size, since gcc accepts it.
- **`generate`** (protocol check, one case) replays the candidate on the baseline, and `evaluation/adapter.py` (stock Python) runs the compile command, then, only if it exits 0, the program with the 90-second timeout. Both commands, the program's arguments and the timeout come from the challenge, built from `hidden/cases.json`. The adapter reports the exit statuses, whether the program timed out, whether each stream decodes as strict UTF-8, and the program's stdout. The Oracle requires compile exit 0, UTF-8 compiler output, no timeout, program exit 0, UTF-8 program output, and the expected text in stdout after the same newline translation (assertions 2 to 4).

The size limit and the expected text are in `hidden/cases.json`; `hidden/oracle.py` holds only the comparisons. There are no pass-to-pass tests.

## Fidelity changes

- **Scope excludes the checkpoint and vocabulary (stricter).** The scope is `/app`, so the program may read any helper file the agent leaves there, as upstream allows, but `/app/gpt2-124M.ckpt` and `/app/vocab.bpe` are excluded. Upstream's test runs the program on these two files, which are the user's inputs ("I have downloaded the gpt-2 weights ... It should read the .ckpt and the .bpe file"); natively an agent could rewrite them and be graded on its own inputs. A candidate that modifies them in place is graded on the originals. `attack-rewrite-inputs.sh` shows the route.
- **Only `/app` survives (stricter).** Changes outside `/app` (for example a compiler wrapper in `/usr/local/bin`, or headers under `/usr/include`) are not captured, while natively they persist into grading. The instructions ask for a dependency-free file at `/app/gpt2.c`, compiled with the system `gcc`. `attack-gcc-wrapper.sh` shows the route.
- **`/app/gpt2.c` must be a regular file (stricter).** Upstream's `stat()` and `gcc` follow a symlink; the artifact check reports a symlink as `not_regular`, which fails. The scope still permits internal symlinks elsewhere in `/app`, so this affects only a candidate whose `gpt2.c` itself is a link.
- **Size read from the captured file (equivalent).** The artifact check's `size` is the byte length of the captured regular file, which is what `stat().st_size` reports for it. Tested on both sides of the boundary by `mutant-size-4999.sh` and `mutant-size-5000.sh`.
- **UTF-8 decoding and newline translation reimplemented (equivalent).** The adapter decodes each stream with Python's strict incremental UTF-8 decoder, and the Oracle applies `\r\n`/`\r` to `\n` translation before the substring test, as `text=True` does. This assumes the native verifier's Python decodes as UTF-8: it is Python 3.13 under a C or UTF-8 locale, where Python uses UTF-8. `mutant-stdout-raw-byte.sh` and `mutant-stderr-raw-byte.sh` compare both graders on correct output plus one invalid byte.
- **Bounded stdout (stricter).** The adapter keeps the first 512 KiB of the program's stdout (the observation is bounded at 4 MiB) while still checking the UTF-8 validity of the whole stream. If the expected text is not in that prefix and stdout was longer, the case fails, while upstream would search the whole output. The correct continuation is about 150 bytes. `mutant-verbose.sh` prints about 200 KB of debug output before a correct continuation and passes both graders.
- **Standard input (equivalent).** The adapter runs both commands with standard input from `/dev/null`; upstream's test inherits the verifier's standard input. The task's program takes its input from arguments.
- **Timeouts (equivalent).** Upstream gives the compiler no timeout of its own (only the 900-second verifier timeout) and the program 90 seconds. The adapter does the same, with the case timeout set to the verifier's 900 seconds. Like `subprocess.run`, the 90 seconds cover both the program's exit and the end of its output.
- **No allowed domains (stricter for the agent).** Upstream allows internet access. The reference solution needs none, so the agent environment has no network.

## Divergences from native

The reference, null and all five mutants get the same verdict from both graders. Both mutants with one invalid UTF-8 byte (`mutant-stdout-raw-byte.sh`, `mutant-stderr-raw-byte.sh`) fail natively, which confirms that the native verifier decodes both streams as strict UTF-8.

- **`attack-gcc-wrapper.sh`: native passed, SecureBench failed. SecureBench is right.** Natively, the `gcc` the candidate placed in `/usr/local/bin` survives into grading and compiles a 9 KB program kept in `/app/full.c`, so a program above the 5000-byte limit passes because the grader's compiler was replaced. SecureBench captures only `/app`, so the real `gcc` compiles the 22-byte stub, which prints nothing.
- **`attack-rewrite-inputs.sh`: native passed, SecureBench failed. SecureBench is right.** Natively, the test runs the program on the checkpoint the candidate overwrote with the expected text, and a program that prints its first argument's file passes. SecureBench excludes the checkpoint and vocabulary from the scope, so the program prints the real 498 MB checkpoint, which is not UTF-8 and does not contain the expected text. The attack hardcodes a guessable answer; it is kept because it shows that the test inputs cannot be rewritten.

## Review

Reviewer: a029d0a9879639e98, 2026-10-26

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. No fidelity change needed.
2. Scope. One root, `/app`, the deliverable's directory and the cwd of upstream's test, so any helper file a solution leaves there is graded as natively. The baseline `/app` holds only `gpt2-124M.ckpt` and `vocab.bpe` (checked in the pinned image) and no symlinks. The excludes `gpt2-124M.ckpt` and `vocab.bpe` are single-component patterns matched against paths relative to `/app`, so they cover exactly the two test inputs (and anything below or replacing them). There are no test files or convention-loaded files in a C task. Both stricter changes (excluded inputs, only `/app` survives) are listed with reasons. The exclusion of the inputs is defensible as protecting the test's inputs, although a candidate can still put converted weights under another name in `/app`, as natively; the instructions ask the program to read the user's `.ckpt` and `.bpe`.
3. No expected value leaks. The expected text and the size limit are only in `hidden/cases.json`. `evaluation/` holds the adapter and two schemas, with no expected value. The challenge carries the commands, the prompt and the timeout, not the expected text. In the baseline image, `/app` holds only the two input files, there are no `/tests`, `/solution` or `/.securebench`, and no file outside `/usr`, `/proc` and `/sys` contains the expected text. The expected text is a well-known license phrase that follows the prompt, so it is guessable; per the brief, a hardcoder is outside scope. No allowed domains, so no 4.7 limitation applies.
4. Challenges. The single challenge holds `compile_argv`, `run_argv` (with upstream's prompt, which the case needs) and `run_timeout_seconds`. Nothing else hidden.
5. Cases. One case, from upstream's single test, with upstream's literal prompt and expected substring. No seed is used, and none is needed.
6. Oracle. Expected values come from `hidden/cases.json`; `oracle.py` only compares. It checks every field it relies on with `is True`/`is False` and exact integer equality (schema integers exclude booleans), in upstream's order: present or unparsable regular file with size < 5000; compile exit 0 and UTF-8 compiler streams; no timeout, exit 0, UTF-8 program streams; substring after the universal-newline translation of `text=True` (which cannot change a match for a substring without `\r` or `\n`, but is harmless). Work over evidence is linear in at most 2 MiB of stdout. Extra fields are ignored and fail closed. I confirmed that the framework sets `size` for `unparsable` text evidence (`securebench/evidence/binding.py:42`). No regression tests exist. The adapter's reimplementation of `subprocess.run(..., timeout=90)` (the timeout covers both exit and end of output) has no mutant among the five. I ran one in `gpt2-codegolf-review` (`mutant-linger.sh`: upstream program plus a forked child that keeps stdout open for 150 s). SecureBench failed it with `program timed out` at 92 s, as `subprocess.run` natively raises `TimeoutExpired`. The reference runs in about 8 s, far from the threshold.
7. Candidates. `reference.sh` runs upstream's `solve.sh` unchanged (`upstream-solve.bash` is byte-identical to upstream). `null.sh` changes nothing. All five mutants compile and run upstream's program with real changes, aimed at the size boundary (4999/5000), the strict UTF-8 decoding of stdout and stderr, and the bounded stdout (the verbose mutant stays under the 512 KiB prefix, so it checks chunked collection rather than the recorded stricter bound). `attack-gcc-wrapper.sh` replaces the grader's compiler to escape the size limit, a route specific to this task. `attack-rewrite-inputs.sh` rewrites the test inputs but carries the guessable expected text, so it shows only that the inputs cannot be rewritten, not a route a hardcoder lacks; `CONVERSION.md` says so. Both attacks fail in SecureBench.
8. Divergences. `qualification.json` reports no problems. Every SecureBench run is admitted, rejudged, not dirty, and records pack digest `sha256:39c39039c29148d7969764b7217e42e4cb49f375ee459a941b24e0175c84a5f9`, the digest `validate` printed at the start and end of this review. The runs record three framework commits (e48b4fa, 00a6c4f, 820481c), but `git diff` shows no change to `securebench/`, `pyproject.toml` or `uv.lock` between them. Reference passes both graders, null fails both, and all five mutants agree. The two divergences are both attacks (native passed, SecureBench failed). The explanations hold: the `/usr/local/bin/gcc` wrapper is outside the scope, and the excluded checkpoint is restored, so the program prints its non-UTF-8 bytes.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet, so there is nothing to check. No exclusion reason applies: the 90-second limit is absolute rather than relative to a reference, and the task fits in 1 CPU and 8 GiB.

Upstream assertions: `exists()` and `st_size < 5000` map to the `source` artifact check (a symlinked `gpt2.c` fails; listed as stricter). The compile `returncode == 0` and the implicit UTF-8 decoding of compiler output map to the `compile` record. The 90-second `timeout`, `returncode == 0`, the implicit decoding of both program streams and the `in` test on stdout map to the `run` record. None is dropped. Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved
