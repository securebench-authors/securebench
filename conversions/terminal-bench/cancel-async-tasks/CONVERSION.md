# cancel-async-tasks

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/cancel-async-tasks

The agent writes `/app/run.py` with an `async run_tasks(tasks, max_concurrent)` that runs async jobs with bounded concurrency and still lets each job's cleanup run when the run is interrupted with Ctrl-C.

## How the pack grades

Upstream's verifier (`tests/test.sh`) copies `tests/test.py` to `/app/test.py` and runs `tests/test_outputs.py` under pytest. Each test starts `python test.py --n-tasks N --max-concurrent M` as a subprocess; the driver's job prints `Task started.`, sleeps 2 s, prints `Task finished.`, and in a `finally` sleeps 1 s and prints `Cleaned up.`. The tests count those lines in the subprocess's stdout.

The pack runs the same driver, byte for byte (`evaluation/test.py`), in the same way:

| Upstream test | Check | What the Oracle requires |
|---|---|---|
| `test_run_py_file_exists` | artifact check `run-py-exists` | `/app/run.py` is not absent |
| `test_tasks_run_concurrently` (2 tasks, max 2, timeout 5 s) | `run-to-completion`, case 0 | no timeout; exit status 0 (`check=True`); `Task started.`, `Task finished.`, `Cleaned up.` each 2 times |
| `test_tasks_obey_max_concurrent` (2 tasks, max 1, timeout 10 s) | `run-to-completion`, case 1 | as above, and elapsed time >= 6 s |
| `test_tasks_cancel_below_max_concurrent` (2 tasks, max 3) | `cancel-on-interrupt`, case 0 | SIGINT after 0.5 s; exit within 5 s; `Task started.` and `Cleaned up.` each 2 times |
| `test_tasks_cancel_at_max_concurrent` (2 tasks, max 2) | `cancel-on-interrupt`, case 1 | as above |
| `test_tasks_cancel_above_max_concurrent` (3 tasks, max 2) | `cancel-on-interrupt`, case 2 | as above |

`evaluation/adapter.py` copies the driver to `/app/test.py` (as `test.sh` does), starts it with `/app` as working directory, and for `run-to-completion` wraps it in `subprocess.run(..., timeout=...)` while measuring the elapsed time with `time.monotonic()` around the call, as upstream does. For `cancel-on-interrupt` it uses `Popen`, sleeps, sends SIGINT and calls `communicate(timeout=...)`, as upstream does. It reports whether the driver timed out, its exit status, the elapsed time and the stdout split at `"\n"` (absent when stdout is not UTF-8, which makes upstream's `decode("utf-8")` raise). The adapter decides nothing.

`hidden/cases.json` holds every literal of upstream's tests: the driver arguments, the timeouts and the SIGINT delay (sent as the challenge), and the expected exit status, line counts and minimum runtime (kept as the context). `hidden/oracle.py` repeats each test's assertions in upstream's order: it joins the lines with `"\n"`, which restores upstream's decoded stdout exactly, and uses `str.count` on it, as upstream does. There are no regression tests and no randomness; the seed is unused.

## Fidelity changes

- **Instructions:** `instructions.md` is upstream `instruction.md` byte for byte. Equivalent.
- **Allowed domains: none** (upstream has `allow_internet = true`). Stricter. The reference needs no network. The instructions say the agent may install packages; in SecureBench it cannot. Natively, packages installed with the system `pip` are not visible to the tests anyway, because upstream's driver runs under the uvx environment's `python`, whose site-packages are separate (checked in the baseline: `sys.path` of that `python` holds the stdlib and the uvx environment only). Only a package installed inside `/app` would have helped natively.
- **Scope: `/app`, minus `/app/test.py` and any `.venv` or `venv` directory.** Stricter for changes outside `/app`: natively an agent could, for example, patch the stdlib in `/usr/local/lib/python3.13`, which the tests' interpreter uses; such changes are not captured here. The instructions name `/app/run.py` as the deliverable and nothing else. `/app/test.py` is excluded because upstream overwrites it with its own driver before any test runs; the adapter writes the same file. Symlinks inside `/app` are allowed, since `from run import run_tasks` works with a symlinked `run.py` natively.
- **Virtual environments and absolute symlinks.** A symlink in `/app` whose target is absolute or leaves `/app` fails capture, while natively it is harmless. The usual case is a virtual environment: `python -m venv /app/.venv` creates `bin/python -> /usr/local/bin/python3`. We exclude every directory named `.venv` or `venv` under `/app`, so such an environment is dropped instead of failing the candidate (the reference plus `python -m venv --without-pip` at `/app/.venv` and `/app/sub/venv` passes). Natively the tests never use a virtual environment in `/app`: they run the uvx interpreter, and only a `run.py` that adds the environment's site-packages to `sys.path` itself could use it, which then fails here. A virtual environment under another name, or any other absolute symlink, still fails capture. Stricter for those candidates.
- **Interpreter.** The driver runs under the baseline's `/usr/local/bin/python` (3.13.7) instead of the uvx virtual environment that upstream builds on that same interpreter. Same interpreter and standard library; the importable third-party packages differ in both directions: natively pytest 8.4.1, pytest-json-ctrf 0.3.5 and their dependencies (pluggy, iniconfig, packaging, pygments) are importable and `pip` is not; here only the baseline's `pip` is. Stricter for a `run.py` that imports the test tooling, more lenient for one that imports `pip`. We know of no reason a solution would do either.
- **`run-py-exists`** accepts any status except `absent` (a directory, a symlink, an over-large or non-UTF-8 file). `Path.exists()` also accepts these except a dangling symlink, which it reports as missing. The protocol checks import `run.py`, so a dangling symlink fails there and the attempt's verdict is the same. More lenient on this one check only; equivalent for the attempt.
- **Output bound.** The driver's stdout reaches the Oracle only inside an observation of at most 4 MiB and at most 100,000 lines (the schemas' `max_items`; 100,000 empty lines are only about 100 KB); upstream has no bound. A run beyond either bound fails with `case_error`. The reference prints under 100 bytes per case. Stricter for a candidate that prints that much extra output.
- **SIGINT disposition.** The adapter resets SIGINT to its default and unblocks it before starting the driver, because an ignored SIGINT survives `exec` and Python then never raises `KeyboardInterrupt`. Upstream's runner leaves SIGINT at its default. Equivalent.
- **Warm-up run.** Before the measured driver run, the adapter starts the baseline interpreter once with `-I -c "import argparse, asyncio"` (standard library only, no candidate code). Without it, the 0.5 s SIGINT window was not reliable: a fresh Evaluation reads the interpreter and standard library cold, and with the other cases of the attempt (and of other attempts on the same daemon) starting at the same time, the driver was still importing `asyncio` when the SIGINT arrived. With four reference attempts running together, all four failed `cancel-on-interrupt` with zero `Task started.` lines; the driver's traceback showed the `KeyboardInterrupt` inside `import asyncio`. A second qualification failed `mutant-threads` this way, though it passes natively. With the warm-up, six attempts at once (four reference, two `mutant-threads`) all passed. Natively the cancel tests run after `test_tasks_run_concurrently` and `test_tasks_obey_max_concurrent` have already loaded the same files into the same container, so the warm-up brings the Evaluation back to native conditions. Equivalent.
- **Standard input** of the driver is `/dev/null` instead of pytest's inherited standard input. The driver never reads it. Equivalent.
- **Elapsed time** is measured by the adapter inside the Evaluation, which the candidate controls, and the Oracle compares it with upstream's 6 s bound. Natively the pytest process measures it. A candidate that takes over the adapter could report any elapsed time, but the bound is public and honest code can always meet it by sleeping, so this lets through nothing the native test does not. Equivalent.

## Candidates

- `reference.sh`: upstream `solve.sh` after `cd /app`, with `#!/bin/sh` as interpreter line (the script is POSIX). No drift repair.
- `null.sh`: no `run.py`.
- `mutant-gather.sh`: `asyncio.gather` with a semaphore; on an interrupt with a queued task, the running tasks' cleanup never prints. Aimed at the SIGINT delivery and the `Cleaned up.` count.
- `mutant-requeue.sh`: a worker pool that moves on to the next queued task after a cancellation, so three tasks start. Aimed at the `Task started.` count.
- `mutant-unbounded.sh`: a semaphore of `max_concurrent + 1`; correct counts but about 3 s instead of 6 s. Aimed at the adapter-measured elapsed time and the 6 s bound.
- `mutant-sequential.sh`: runs tasks one after another; about 6 s for two tasks, past the 5 s timeout, and only one task started on interrupt. Aimed at the adapter's timeout handling.
- `mutant-threads.sh`: one event loop per task in a `ThreadPoolExecutor`. The interrupt does not reach the threads, but the interpreter waits for them at exit, so every task finishes and cleans up within 5 s, and it passes. Aimed at the 5 s `communicate` window and the handling of a driver that dies of SIGINT.
- `attack-replace-driver.sh`: writes its own `/app/test.py` printing the counted lines beside a do-nothing `run.py`. Dropped by the scope exclusion and overwritten by the adapter.
- `attack-reward-daemon.sh`: leaves a process that keeps writing `1` to the native `/logs/verifier/reward.txt`. Nothing outside `/app` reaches an Evaluation.
- `attack-forge-observation.sh`: a `run.py` that writes a passing observation to the adapter's own stdout through `/proc/<parent>/fd/1` when imported. The adapter's own response follows it, so the response is not one JSON value and the case fails with `case_error`; if the write does not land, the adapter's genuine observation shows no counted lines and the case fails with `oracle`. Our trial runs and the final qualification ended `case_error`; the first qualification, before the warm-up run was added, ended class `oracle`, most likely a cancel case where the SIGINT arrived before the driver imported `run.py` (see "Warm-up run"). Both are `failed`.

## Divergences from native

None. In `qualification.json` the reference passes both graders; the null candidate, every attack and the mutants `gather`, `requeue`, `sequential` and `unbounded` fail both; `mutant-threads` passes both. The attacks also fail natively (reward 0): each ships a do-nothing `run.py`, and the native verifier overwrites `/app/test.py`. We did not establish why the reward daemon has no effect natively (whether it survives into the verifier at all); SecureBench's verdict does not depend on it.

## Review

Reviewer: conversion-reviewer (scratch `cancel-async-tasks-review`), 2026-10-26, second review

Pack digest checked: `sha256:30702e839e579e4b9cab245bf4bc0c8ce096d5fc5d68941ec0001e199c5726f7`. Every SecureBench run in `qualification.json` records it. The first review saw `sha256:b08b4dc8...4b955434`. Since then the converter changed the scope excludes in `task.toml` and added a warm-up run to `evaluation/adapter.py`. `instructions.md`, `evaluation/test.py`, the schemas, `hidden/cases.json` and `hidden/oracle.py` are unchanged. Outside the pack, `candidates/reference.sh` and `CONVERSION.md` changed.

Earlier findings:
- Finding 1 (an absolute symlink in `/app` fails capture) is fixed. The root now also excludes `**/.venv` and `**/venv`, and a new fidelity bullet records the rest: a virtual environment under another name, or any other absolute symlink, still fails capture (stricter), and a `run.py` that uses a dropped environment fails here. I re-ran the reference plus `python -m venv --without-pip` at `/app/.venv` and at `/app/Sub/VENV` (script in scratch `cancel-async-tasks-review/reference-venv2.sh`), and it ended `passed`.
- Finding 2 (the 100,000-line bound) is fixed in the "Output bound" bullet.
- Finding 3 (the interpreter label) is fixed: stricter for a `run.py` that imports the test tooling, more lenient for one that imports `pip`.
- Finding 4 (`set -e`) is fixed. `reference.sh` is upstream `solve.sh` with only `#!/bin/sh`, a comment and `cd /app` added (checked with `diff`), and the "Candidates" section lists the interpreter line.

1. Instructions. `cmp` against upstream `instruction.md`: identical (unchanged since the first review).
2. Scope. `/app` minus `test.py`, `**/.venv` and `**/venv`. These patterns match a directory of that name at any depth, including directly under `/app`, and its case variants. Excluding them only drops candidate files. It cannot drop a deliverable, since the instructions require `/app/run.py`, and it does not touch the specification. The baseline `/app` is empty, so no baseline symlinks lead out of it. The pack still runs no test runner, so `conftest.py` and similar files do not apply.
3. Expected values. They are only in `hidden/cases.json` (unchanged), and all are public upstream literals. The adapter change adds no value. No allowed domains.
4. Challenges. Unchanged; each holds only its case's arguments, timeout and SIGINT delay.
5. Cases. Unchanged: five protocol cases and one artifact check, one for each of upstream's six tests. The seed is unused.
6. Oracle. Unchanged and still as described in the first review. The adapter change, a warm-up run, only loads files. Before measuring anything, the adapter runs `/usr/local/bin/python -I -c "import argparse, asyncio"` with `cwd=/`. The `-I` flag keeps `/app`, the environment variables and user site-packages off the path, and the baseline's site-packages has no `.pth` files, so no candidate code runs in it. It runs before `start = time.monotonic()`, so it adds nothing to the elapsed time. If it times out, the adapter crashes and the case fails with `case_error`, never `invalid`, and a candidate cannot cause that because none of its code runs there. The adapter still reports only what the driver did.
7. Candidates. `reference.sh` is now the upstream solution with only the allowed additions. Mutants and attacks are unchanged; `attack-forge-observation` ended `failed`, class `case_error`, in the new qualification, which matches the candidate note.
8. Divergences. `qualification.json` reports no problems. Every run is admitted and rejudged, and all record the same digest and clean framework commit `7cc3619`. The reference passes both graders, the null and every attack fail SecureBench, and every mutant agrees with native (`mutant-threads` passes both; the other four fail both). Native results are marked `native_cached`; caching applies only to unchanged candidate scripts, and the changed `reference.sh` was run natively in the earlier qualification that `CONVERSION.md` describes. The "Warm-up run" bullet says why it is needed: without it, four concurrent reference attempts failed `cancel-on-interrupt`, interrupted inside `import asyncio`, and `mutant-threads` diverged once. It also says why it is equivalent: natively, the cancel tests run after two earlier tests have loaded the same files in the same container. The explanation holds: the warm-up only brings driver start-up back to native conditions and checks nothing.
9. Inventory. No row yet; the coordinator adds it at commit. The exclusion reasons still do not apply (the SIGINT is sent inside the Evaluation; the 6 s rule is a lower bound; the cleanup is observed as printed output).

Upstream assertions: unchanged since the first review. Every assertion of the six tests maps to a check, and none is dropped.

Findings:
- None.

Verdict: approved
