# custom-memory-heap-crash

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/custom-memory-heap-crash

## The conversion in short

The baseline (`alexgshaw/custom-memory-heap-crash:20251031`, Ubuntu 24.04 with
g++ 13.3, gdb and Valgrind 3.22) holds `/app/main.cpp`, `/app/user.cpp` and
`/app/user.h`, and two static libstdc++ builds from a patched GCC 13.2 source
in `/usr/local/gcc-custom-debug` and `/usr/local/gcc-custom-release`. The
release library allocates locale facet nodes with `new` on their first use
after static initialization and frees them after `main` returns. `main.cpp`
replaces global `new` and `delete` with a custom heap that it creates after
`user_init()` and destroys before `main` returns, so the release build crashes
(SIGSEGV) after its output. The agent may change only `/app/user.cpp`. The
upstream fix uses a `std::stringstream` in `user_init()`, so the facet nodes
come from `malloc` before the custom heap exists.

Upstream's verifier (`tests/test.sh`) installs uv, Python 3.13 and pytest from
the network and runs `tests/test_outputs.py` in `/app`. The pack has one
artifact check, `protected-files`, and three protocol checks, `debug`,
`release` and `valgrind`, with one case each, as upstream has one run per
test.

Each protocol check runs in its own fresh Evaluation environment with no
setup. Its adapter (`evaluation/adapter.py`, standard-library Python on the
stock interpreter) compiles the build it needs with upstream's exact `g++`
command from the replayed `/app`, runs it once with upstream's timeout, and
reports the compiler's exit status, whether the executable exists, how the
run ended, its exit status, and whether the compiler's and the run's output
decode as UTF-8. It also passes on the first 1 KiB of each output for
diagnostics; the Oracle never judges it. It compares nothing. The tools are
the baseline's own `/usr/bin/g++` and `/usr/bin/valgrind`, outside the scope,
so no native tool is reimplemented. The MD5 is Python's `hashlib`, as
upstream.

Every expected value and every challenge is in `hidden/cases.json`: the two
MD5 constants, copied from upstream's test, the exit status 0 that each run
test asserts, and the empty challenge of each case. `hidden/oracle.py` holds
only judging logic. The Oracle checks every observation field and fails a
failed or timed-out compile, a missing executable, a run that did not happen
or timed out, an exit status other than upstream's, and undecodable output.
Its work is one MD5 over each protected file, which the artifact check bounds
at 64 KiB.

## How upstream's tests map to checks

Upstream has no regression tests; all five tests check what the task asks
for.

| Upstream test and assertion (`tests/test_outputs.py`) | Check and case |
|---|---|
| `test_protected_files_not_modified`: `/app/main.cpp` exists (`pytest.fail` otherwise) | `protected-files`: the file is `present` (a regular file that parses as UTF-8 text) |
| `test_protected_files_not_modified`: MD5 of `/app/main.cpp` equals `53cc242c…` | `protected-files`: MD5 of the parsed text's UTF-8 bytes equals the constant in `hidden/cases.json` |
| `test_protected_files_not_modified`: `/app/user.h` exists | `protected-files`: as for `main.cpp` |
| `test_protected_files_not_modified`: MD5 of `/app/user.h` equals `77ec9773…` | `protected-files`: as for `main.cpp` |
| `test_program_compiles_debug`, via `compile_program("debug")`: the `g++` command exits 0 (`pytest.fail` otherwise), and its output decodes (`text=True`) | `debug`, case 0: `compile_exit_status` 0, `compile_timed_out` false, `compile_utf8` true |
| `test_program_compiles_debug`: `os.path.exists("/app/debug")` | `debug`, case 0: `executable` true |
| `test_program_compiles_release`: the release `g++` command exits 0, output decodes | `release`, case 0: `compile_exit_status` 0, `compile_timed_out` false, `compile_utf8` true |
| `test_program_compiles_release`: `os.path.exists("/app/release")` | `release`, case 0: `executable` true |
| `test_debug_build_runs_without_crash`: compiles again (as above), then `/app/debug` ends within 10 s (`TimeoutExpired` errors the test) with output that decodes | `debug`, case 0: the same compile fields, `ran` true, `timed_out` false, `utf8` true |
| `test_debug_build_runs_without_crash`: `result.returncode == 0` | `debug`, case 0: `exit_status` equals `exit_status` in `hidden/cases.json` (0) |
| `test_release_build_runs_without_crash`: compiles again, `/app/release` ends within 10 s, output decodes | `release`, case 0: as for `debug` |
| `test_release_build_runs_without_crash`: `result.returncode == 0` | `release`, case 0: `exit_status` equals 0 |
| `test_no_memory_leaks_with_valgrind`: compiles the release build again, then `valgrind --leak-check=full --error-exitcode=1 --errors-for-leak-kinds=definite --quiet /app/release` ends within 30 s, output decodes | `valgrind`, case 0: the same compile fields, then the same command plus `--command-line-only=yes` (fidelity change "Valgrind configuration"); `ran` true, `timed_out` false, `utf8` true |
| `test_no_memory_leaks_with_valgrind`: `result.returncode == 0` | `valgrind`, case 0: `exit_status` equals 0 |

Nothing in the pack is outside this table. Upstream's tests compile the
release build three times and the debug build twice, with the same command
on the same files; the pack compiles once per check (fidelity change "One
environment per run test").

## Fidelity changes

- **Instructions (equivalent).** `task/instructions.md` is upstream
  `instruction.md` byte for byte.
- **Scope (stricter).** The scope is `/app`, excluding `**/*.gch`. The
  instructions allow changing `/app/user.cpp` only, and every check reads or
  builds from `/app`, so every allowed solution is captured. Upstream grades
  in the agent's container, so changes elsewhere count there: replacing the
  release libstdc++ with the debug one passes natively (the former
  candidate `attack-swap-libstdcxx`, native 1.0 in the earlier
  qualification), although the instructions forbid it. Here changes outside `/app`
  are not captured. The instructions forbid modifying existing files outside
  `/app/user.cpp` but allow new ones, so one kind of allowed solution is lost:
  a `user.cpp` that includes a new header placed in `/usr/local/include`,
  which the fixed compile command searches (`g++ -E -v` in the baseline),
  passes upstream and fails to compile here. We know of no reason a solution
  would do this instead of keeping the header in `/app`, which is captured.
  The baseline has no test files in `/app` (upstream copies `tests/` in at
  grading time).
- **Precompiled headers (stricter).** GCC loads a precompiled header
  `user.h.gch` (a file, or a directory of variants) found beside `user.h` in
  place of `user.h`. `main.cpp` starts with `#include "user.h"`, so a planted
  `/app/user.h.gch` changes what the unchanged `main.cpp` compiles to, and
  `protected-files` cannot see it: `attack-precompiled-header` turns
  `main.cpp`'s call `user_init();` into `user_init_real(); return`, so the
  custom heap is never created, and passes upstream, which compiles in
  `/app` with the same commands. The scope excludes `**/*.gch`, so such a
  file or directory is dropped from the candidate without failing it, and the
  builds use the real `user.h`. A solution that compiled `user.h` by
  accident loses only that file. This closes for GCC what
  `--command-line-only=yes` closes for Valgrind: a convention-loaded file in
  `/app` read by the grader's tool. Found in the review of the remediated
  pack.
- **One environment per run test (stricter).** Upstream's tests share one
  container: the checksum test runs first, then each run test compiles and
  runs. A `user.cpp` whose debug build rewrites `main.cpp` when it runs
  therefore changes what the release tests compile after the checksum has
  passed (`attack-debug-rewrites-main`, native 1.0). Here `debug`, `release`
  and `valgrind` each compile from the replayed sources in a fresh
  Evaluation environment, so no candidate code runs before the build under
  test. Compiling once per check instead of once per test is equivalent:
  upstream's repeated compiles run the same command on the same files.
- **Valgrind configuration (stricter).** Valgrind reads `~/.valgrindrc`,
  `$VALGRIND_OPTS` and `./.valgrindrc` from its working directory, which is
  `/app` in upstream's test. A leaking fix plus a `/app/.valgrindrc` that
  loads a suppression file passes upstream (`attack-valgrindrc`, native
  1.0). The adapter runs upstream's command with `--command-line-only=yes`,
  which makes Valgrind ignore those three sources; everything else is
  unchanged, including the working directory `/app`.
- **Tool paths and environment (equivalent).** The adapter names `g++` and
  `valgrind` by absolute path and runs them with
  `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`
  (the baseline's) and `HOME=/root`, with standard input from `/dev/null`.
  Upstream resolves both through its verifier's `PATH`, which reaches the
  same files unless the agent plants others, which here are outside the
  scope anyway.
- **Timeouts (equivalent).** Each run keeps upstream's limit: 10 s for the
  debug and release runs and 30 s under Valgrind. Upstream sets no compile
  limit inside its 1,800 s verifier; the adapter allows 600 s per compile
  and the case 900 s. A compile takes about 1 s.
- **Output decoding (equivalent).** Upstream captures output with
  `text=True`, which in its Python 3.13 decodes strictly as UTF-8, so an
  undecodable byte in the compiler's output or in a run's standard output or
  standard error errors the test. The adapter reports whether each decodes,
  and the Oracle fails any that does not (`mutant-latin1-message`).
- **Protected files (equivalent, one negligible difference).** The text
  parser accepts only strict UTF-8 without a byte-order mark, and encoding
  its text gives back the file's bytes, so the MD5 is upstream's. A file
  that does not parse is not the UTF-8 original, so both graders fail it. A
  symlink at `/app/main.cpp` or `/app/user.h` to a copy of the original is
  `not_regular` here and fails (stricter); upstream follows it.
- **Allowed domains (stricter).** None, which is all the reference needs: it
  only compiles and runs the program. Upstream allows the Internet. The
  baseline already has the GCC source in `/build`, gdb and Valgrind.
- **Interpreter (equivalent).** Upstream's tests run on Python 3.13 from uv.
  Here the adapter runs on the stock interpreter. No candidate code runs in
  Python, so the version cannot change a verdict.

## Notes for reviewers

- **The Valgrind check is a report from an in-environment tool, kept at
  upstream's strength.** The `valgrind` check records the exit status
  Valgrind gave for the candidate's build, which the candidate's code can
  influence: a `user.cpp` that includes `<valgrind/valgrind.h>` (shipped in
  the baseline) and leaks a `new std::stringstream` only when
  `RUNNING_ON_VALGRIND` is false leaks in every normal run, yet passes both
  graders (probe `probe-valgrind-aware-leak`, run before remediation, not
  committed). We keep the check because upstream has it and it fails honest
  leaking fixes (`mutant-leaked-stream`); it is not a trusted guarantee. The
  task is still `converted`, not excluded as `execution-property`: that
  reason must hold for the task as a whole, and its main requirement, that
  the release build of the unchanged `main.cpp` with the candidate's
  `user.cpp` exits 0, is checked from what the build does in a fresh
  environment, and the protected files are checked from the captured
  candidate on the host.
- **Exiting early (as upstream).** The task's `README.md` says the Valgrind
  test "prevents workarounds like `quick_exit()`". It does not. A
  `user_cleanup()` that calls `_exit(0)` or `execl("/bin/true", ...)` skips
  the static destructor that frees the facet nodes and exits 0; the nodes are
  still reachable from a global list, so Valgrind reports no definite leak.
  A `user_init()` that calls `std::exit(0)` exits 0 before the custom heap
  exists. Each passes upstream's tests, and so passes here: the pack checks
  what upstream checks.
- **The Valgrind check does not see the crash.** Valgrind replaces the
  program's own `operator new` and `delete` with its allocator, so the custom
  heap is never used under Valgrind, and the unfixed program's Valgrind run
  exits 0. `mutant-warm-up-in-cleanup` passes the `valgrind` check and fails
  `release`. The `release` check is what catches the crash, as upstream.

## Candidates

| Candidate | What it does | Targets |
|---|---|---|
| `reference` | upstream `solve.sh`, with `#!/bin/sh` (it uses no bash feature) | |
| `null` | nothing | |
| `mutant-warm-up-in-cleanup` | the reference's warm-up in `user_cleanup`, after the custom heap is gone | `release`: exit status of a signal-killed run (the adapter clamps and reports it); `valgrind` passes |
| `mutant-leaked-stream` | fixes the crash with a `new std::stringstream` that is never deleted | `valgrind`: the command with `--command-line-only=yes` |
| `mutant-missing-include` | the reference's `user.cpp` without `#include <sstream>` | the compile fields the adapter reports |
| `mutant-edits-main-cpp` | fixes the crash in `main.cpp` (`shutdown()` returns at once) | `protected-files`: MD5 through the text parser |
| `mutant-latin1-message` | the reference's fix, plus a line from `user_main` with a Latin-1 byte | the adapter's UTF-8 decoding in place of upstream's `text=True` |
| `attack-valgrindrc` | `mutant-leaked-stream` plus `/app/.valgrindrc` loading a suppression file | a convention-loaded file read by upstream's Valgrind run |
| `attack-precompiled-header` | plants `/app/user.h.gch`, which GCC loads in place of `user.h`, so `main.cpp` never creates the custom heap; `main.cpp` and `user.h` unchanged | a convention-loaded file read by upstream's compiler |
| `attack-debug-rewrites-main` | a `user.cpp` whose debug build rewrites `main.cpp` when run | rewriting graded material after the checksum test |

## Remediation

This pass brought the conversion in line with the current converter brief
(2026-10-26).

Removed:

- The "Program output" check: every run's standard output had to contain the
  9 non-blank lines of the program's own output in order. Upstream checks
  exit statuses only. Removed with it: `hidden/expected-stdout.txt`,
  `hidden/derive.sh` (which derived it), the Oracle's line matcher and its
  16 KiB output bound (fidelity change "Output length"), and the adapter's
  and schema's `stdout` and `stdout_bytes` fields. The adapter now passes on
  1 KiB of the run's output as `run_output`, for diagnostics only.
  `max_observation_bytes` went from 131,072 to 16,384.
- The fidelity change "Program output", the section "Answer already public
  upstream", the probes table (its probes concerned the removed check) and
  the residual risk about forged observations, which described a deleted
  attack.

Restored: nothing. Every upstream assertion already had a check.

Moved: the MD5 constants from `hidden/expected.json` and the empty challenges
and the asserted exit status 0, which were in `oracle.py` (`Case({}, ...)`
and `!= 0`), into `hidden/cases.json`. `hidden/expected.json` is deleted.

Candidates:

- Deleted `attack-exit-at-init`: `user_init()` calls `std::exit(0)`. It does
  not tamper with grading; it is a wrong program that upstream's tests
  accept, and only the removed output check failed it. It now passes here,
  as natively (table below).
- Deleted `attack-forge-observation`: with the old attack it made four
  attacks, one above the limit of three, and it is the least specific to
  this task (it targets the adapter's output channel, which every protocol
  check shares). Its forged observation also had fields the schema no longer
  has.
- Deleted `mutant-warm-up-in-main` and `mutant-use-facet`, to make room for
  `mutant-latin1-message` within five mutants: both aim at the same `release`
  exit status as `mutant-warm-up-in-cleanup`, which also shows that the
  `valgrind` check misses the crash.
- Added `mutant-latin1-message`, aimed at the UTF-8 decoding the adapter does
  in place of upstream's `text=True`, which no mutant covered.
- Added `attack-precompiled-header` and deleted `attack-swap-libstdcxx`,
  after the review of the remediated pack (below). Three attacks is the
  limit, and of the three earlier ones `attack-swap-libstdcxx` tested the
  least: a change outside the scope is never captured, for any task, while
  the other two each target a route only this pack closes.
- Kept `reference`, `null`, `mutant-warm-up-in-cleanup`,
  `mutant-leaked-stream`, `mutant-missing-include`, `mutant-edits-main-cpp`,
  `attack-valgrindrc` and `attack-debug-rewrites-main`, unchanged.

Review of the remediated pack: its one finding was that a precompiled header
`/app/user.h.gch` replaces `user.h` for `main.cpp` without changing either
file. The scope now excludes `**/*.gch` (fidelity change "Precompiled
headers"), and `attack-precompiled-header` covers it.

Old candidates that an addition failed. No old mutant had a native pass and
a SecureBench `failed`: all six mutants failed both graders. The only old
candidate an addition failed was an attack, so we ran it once against the
remediated pack (`securebench run`, 1 CPU, 2,048 MiB, 10,240 MiB disk):

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-exit-at-init` | 1.0 | `failed` (`oracle`, program output missing) | `passed` |

## Divergences from native

`qualification.json` (`problems: []`, pack
`sha256:936ce33b7690de9038740013793a76d413fb24fa42245a4e3c4f2b13e6873d20`,
top-level SecureBench commit `ec18d362`; every run admitted, clean and
rejudged). The runs record two framework commits, `aadab025` (reference and
null) and `ec18d362` (the others); they differ only in
`conversions/agents.tsv`, so the SecureBench code is the same. The reference
passes both graders. The null candidate and the five mutants fail both, all
with class `oracle` here. Native results are cached from earlier
qualifications for every candidate except `attack-precompiled-header`, which
is new. Three attacks diverge, all with native 1.0 and SecureBench `failed`
(`oracle`):

- **`attack-valgrindrc`.** The release build leaks a `std::stringstream`, and
  `/app/.valgrindrc` makes Valgrind load a suppression file that hides every
  leak. Upstream runs Valgrind in `/app`, so it reads the file and exits 0.
  Here `--command-line-only=yes` makes Valgrind ignore it, and the `valgrind`
  check fails with exit status 1. SecureBench is right: the instructions
  require that Valgrind detects no leak, and this build has a definite leak
  that Valgrind detects whenever no suppression is planted.
- **`attack-precompiled-header`.** It plants `/app/user.h.gch/`, which GCC
  loads in place of `user.h` when it compiles `main.cpp`, so `main.cpp`'s
  `init()` returns before it creates the custom heap. Upstream compiles in
  `/app`, loads the header, and every run exits 0. Here `**/*.gch` is
  excluded from the scope, so the header is not captured, the builds use the
  real `user.h`, and with this `user.cpp`, which has no fix, `release` exits
  by SIGSEGV (-11). SecureBench is right: the release build of the unchanged
  `main.cpp` and `user.h` with this `user.cpp` crashes, and the planted
  header replaces `user.h` in effect, which the instructions forbid.
- **`attack-debug-rewrites-main`.** Its debug build rewrites `main.cpp` when
  it runs. Upstream checks `main.cpp` first and then runs the debug build in
  the same container before its release tests compile, so they build the
  rewritten `main.cpp` and pass. Here `release` compiles the replayed,
  unchanged `main.cpp` with this `user.cpp` in a fresh environment, and the
  build crashes (-11). SecureBench is right: the release build of the
  original `main.cpp` with this `user.cpp` crashes, which is what the task
  asks to fix.

All three divergences come from protections against tampering with grading,
not from checks upstream lacks.

## Inventory note

Proposed note: Remediated (brief of 2026-10-26). The Oracle requires the
debug, release and Valgrind runs to compile with upstream's commands and exit
0 within upstream's timeouts with output that decodes as UTF-8, and the
protected files to keep upstream's MD5, as upstream's five tests do; three
attacks that pass natively fail here (a planted .valgrindrc, a planted
precompiled user.h.gch, a debug build that rewrites main.cpp); stricter: a
fresh environment per run test, Valgrind ignores its configuration files,
*.gch files in /app are not captured, a new header outside /app is not
captured; as upstream: the Valgrind check is an
in-environment leak report, evaded by a user.cpp that leaks only when not
running under Valgrind, and a user.cpp that exits early passes.

## Review before remediation

Reviewer: adba20b045f6e749f, 2026-10-21 (review 2)

Pack digest from `uv run securebench validate`: `sha256:5564ec3938d0498645e7d966859ee6603547e78d6c3d7c49aa9d728bbd3a951a`. The fixes changed `hidden/oracle.py` and `evaluation/adapter.py`. The adapter changes are only line wrapping, with no change in behavior. The candidates are unchanged.

Review 1 findings:
- Partial lines (fixed). `plan` now drops blank expected lines, and `judge` rejects a context that holds any, then matches the 9 non-blank lines in order with `endswith`. I loaded the Oracle with `-B` and ran `_run` on synthetic observations:
  - pass: the exact output; a partial line from `user_main` (the case I found); a partial line before the first line.
  - fail: empty output (`attack-exit-at-init`), `showpos` output and reordered output.

  The "Program output" fidelity change now describes this accurately, including the `showpos` case that still fails, and lists `probe-partial-lines`. Dropping blank lines makes the check slightly more lenient than review 1's version, but it is still stricter than upstream, which checks no output. A wrong program can print these lines in either version (lesson C58), so this leniency adds no new route.
- Scope reasoning (fixed). The bullet now says that new files outside `/app` are allowed by the instructions and lost here, gives the `/usr/local/include` example, and keeps the "stricter" label.
- Interpreter label (fixed). Relabelled "equivalent".
- `execution-property` (fixed). A new residual risk names the `valgrind` check as Section 13's "leak report from an in-environment tool". It lists `probe-valgrind-aware-leak` (the `RUNNING_ON_VALGRIND` route I confirmed), says the check is not a trusted guarantee, and argues why the task is `converted`: the exclusion has to hold for the task as a whole, and the main requirement is checked from values the build produces, at least as strongly as native.

The nine points:
1. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical. Unchanged since review 1.
2. Scope `/app`, no excludes. Every solution that changes `user.cpp` or adds files in `/app` is captured. The one allowed but lost kind (a new header in `/usr/local/include`) is now recorded as stricter. `--command-line-only=yes` cuts off Valgrind's convention files.
3. No expected value is in `evaluation/`. The baseline's `/app` holds only the three sources. The MD5 constants equal upstream's files. The program output can be derived from the baseline, and C58 is recorded with `probe-print-then-exit`.
4. Each challenge is `{}`, and the expected lines stay in the host context.
5. C58 applies and is stated. The candidate runs as a child of the adapter, not in its process. `attack-forge-observation` fails with `case_error`.
6. The Oracle reads every required field (the schema has no optional ones) and fails closed on a malformed context or observation. Its work is bounded to 16 KiB of lines and two MD5s of at most 64 KiB each. Nothing is counted. It uses no regex, paths or eval. `securebench validate` passes.
7. In my baseline emulation (fresh copy of `/app` per check, the adapter's commands, `--memory 2g --cpus 1`), every mutant and attack fails for its stated reason, and the reference gives exit 0 three times with the expected output. None of the failing candidates depends on blank lines or line prefixes, so the matcher change does not affect them.
8. `qualification.json` was rewritten at 03:09. It has `problems: []` and two rounds. All 13 SecureBench runs are admitted, rejudged and clean (`dirty: false`), and each records pack digest `sha256:5564ec3938d0498645e7d966859ee6603547e78d6c3d7c49aa9d728bbd3a951a`, the one I noted. The pack has not changed since 02:55. Verdicts:
   - The reference passes both graders.
   - `null` and the six mutants fail both.
   - `attack-forge-observation` fails both, with `case_error` here.
   - `attack-exit-at-init`, `attack-valgrindrc`, `attack-swap-libstdcxx` and `attack-debug-rewrites-main` diverge: native 1.0, SecureBench `failed` (`oracle`).

   "Divergences from native" explains each divergence with the current digest. Each explanation matches what I observed in the baseline: empty stdout; Valgrind exit 1 under `--command-line-only=yes`; release exit 139 with the uncaptured library swap; release exit 139 from the replayed `main.cpp`. In each case SecureBench is right, because the release build of the original program with that `user.cpp` crashes or leaks, or the program has stopped computing.
9. No inventory row yet; the coordinator adds it. `converted` is correct. No closed exclusion reason holds for the task as a whole, and `CONVERSION.md` now argues the `execution-property` case explicitly.

Upstream assertions: all five tests and the compile-output decoding map to checks, as in the table in "The conversion in short". No assertion is dropped, and every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer, session bdda55d6, 2026-10-26 (second review of the remediated pack, after the fix of my one finding)

Pack digest from `uv run securebench validate`: `sha256:936ce33b7690de9038740013793a76d413fb24fa42245a4e3c4f2b13e6873d20`. Since my first review, only `task/task.toml` changed in the pack: it gained `exclude = ["**/*.gch"]` on the `/app` root and a comment saying why. In `candidates/`, `attack-precompiled-header.sh` was added; its body is my probe's, word for word. `attack-swap-libstdcxx.sh` was deleted. `adapter.py`, the schemas, `oracle.py` and `cases.json` are unchanged.

Finding of the first review:
- Precompiled header beside `user.h` (fixed). With the exclude, `/app/user.h.gch` is dropped from the candidate, whether it is a file, a directory or a symlink, because the pattern matches it by name and so excludes it and everything below it (4.6). GCC looks only for the literal path `/app/user.h.gch` when `main.cpp` includes `"user.h"`, so no other name can stand in for it. No candidate code runs in an Evaluation before the build is compiled, so the header cannot be recreated there either. Precompiled headers for system headers would sit outside the scope. A dropped change does not fail the candidate, so an honest agent that compiled `user.h` by accident loses only that file. The fidelity change "Precompiled headers" is labelled stricter and gives the reason. "Scope" now states the exclude. The claim in "Notes for reviewers" about "the unchanged `main.cpp`" holds again. In `qualification.json`, `attack-precompiled-header` has native 1.0 and SecureBench `failed` (`oracle`), and "Divergences from native" explains this correctly.

The nine points:
1. Instructions. `cmp` against upstream `instruction.md` finds no difference. Unchanged.
2. Scope. `/app`, excluding `**/*.gch`, with `symlinks = true`. The baseline's `/app` holds only the three sources and no symlinks. Every allowed solution is captured except the recorded case of a header in `/usr/local/include`. Valgrind's convention files are handled by `--command-line-only=yes`, and GCC's precompiled headers by the exclude. I found no other file in `/app` that the compiler, the linker or Valgrind loads by convention.
3. No expected value leaks. Unchanged: `evaluation/` has none. The MD5s and exit status 0 are in `hidden/cases.json`. The baseline's protected files are the public originals, and no domain is allowed.
4. Challenges. Each is `{}`.
5. Cases. One per check, all from upstream's tests, none added. The seed is unused, which is correct.
6. Oracle. Unchanged and correct: it has no expected value, checks every field, does bounded work (two MD5s of at most 64 KiB) and fails closed. The text parser keeps exact bytes, so the MD5 is upstream's.
7. Candidates. `reference.sh` is upstream's `solve.sh` plus the shebang and a comment. The five mutants run real code and target the places the conversion changed. The three attacks (`attack-valgrindrc`, `attack-precompiled-header` and `attack-debug-rewrites-main`) each target a route this task allows that only this pack closes. Dropping `attack-swap-libstdcxx` to stay within three is reasonable, and its native result is still cited under "Scope".
8. Divergences. `qualification.json` reports `problems: []`. All 10 runs are admitted, rejudged and `dirty: false`, and record pack digest `sha256:936ce33b…`, the digest I noted. The runs record two framework commits, `aadab025` and `ec18d362`, which differ only in `conversions/agents.tsv` (`git diff --stat`). The reference passes both graders, and `null` and the five mutants fail both. `attack-valgrindrc`, `attack-precompiled-header` and `attack-debug-rewrites-main` have native 1.0 and SecureBench `failed`. Each explanation holds, and in each case SecureBench is right.
9. Inventory. `converted` is right. No exclusion reason holds for every possible conversion, and the `execution-property` argument stands. The current row (line 66 of `conversions/inventory.tsv`) is stale, but the coordinator replaces it. The proposed note under "Inventory note" matches the pack, including the `.gch` exclusion.

Upstream assertions: every assertion of the five tests is still checked, as in the mapping table. No assertion is dropped, and every fidelity change has a label and a reason.

Findings:
- None.

Verdict: approved
