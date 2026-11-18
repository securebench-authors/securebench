# polyglot-rust-c

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/polyglot-rust-c

## How the pack grades

Upstream has one test, `test_fibonacci_polyglot` in `tests/test_outputs.py`. It
makes three kinds of assertion, and each becomes part of a check:

| Upstream | SecureBench |
|---|---|
| `os.listdir("/app/polyglot") == ["main.rs"]` | Artifact check `polyglot-listing`: a listing of `/app/polyglot`. The listing is recursive, so the Oracle keeps only the top-level names and requires them to equal `["main.rs"]` (from `hidden/cases.json`). |
| `rustc /app/polyglot/main.rs -o /app/polyglot/main` and `g++ -x c++ /app/polyglot/main.rs -o /app/polyglot/cmain`, results ignored (`os.popen`) | Two protocol checks, `fibonacci-rust` and `fibonacci-cpp`. The `setup_command` of each runs `evaluation/setup.sh` with its language, which runs only that language's compile command, unchanged, in `/app`. It ignores the exit status, as upstream does, and always succeeds; a failed build shows as a missing binary in every case of that check. |
| For each of the five `test_cases` `(0,"1"), (1,"1"), (2,"2"), (10,"89"), (42,"433494437")`: run both binaries with `check=True, text=True` and assert `stdout.strip() == expected` | Each of the two checks has one case per entry, ten cases in all. The challenge is `{"n": n}`; the expected string is the case's context, from `hidden/cases.json`. `evaluation/adapter.py` runs the check's own binary (`/app/polyglot/main n` or `/app/polyglot/cmain n`) and reports a launch error, or the exit status, the stdout size and the stdout decoded as strict UTF-8 and stripped with `str.strip()`. The Oracle requires no launch error, exit status 0, a stripped stdout present, and equal to the expected string. An upstream test case passes exactly when its case passes in both checks. |

The expected values are the literals of upstream's `test_cases`; nothing is
derived.

## Fidelity changes

- **Scope: `/app`** (equivalent). The deliverable is
  `/app/polyglot/main.rs`, which does not exist in the baseline (`/app` is
  empty), so the root is `/app`. Covering all of `/app` keeps solutions that
  read another file under `/app`, such as an absolute `#include "/app/..."`,
  which upstream's test does not forbid (`mutant-include-outside`).
- **Internal symlinks allowed, except as `/app/polyglot` itself** (stricter,
  only for a candidate that makes `/app/polyglot` a symlink). Internal
  symlinks are allowed so that, for example, a `main.rs` that links to a
  file elsewhere under `/app` builds as it does upstream. The listing does
  not follow a symlink at the listed path: when `/app/polyglot` is a link to
  a directory under `/app` that holds only `main.rs`, the listing reports
  `not_directory` and the attempt fails, while `os.listdir`, `rustc` and
  `g++` follow the link upstream and pass. Following it would need the
  Oracle to resolve links over a listing of all of `/app`; we keep the
  simpler check, since the instructions ask for a file written in
  `/app/polyglot`, not for a linked directory.
- **`polyglot/.git` captured** (equivalent for `.git`). `polyglot/.git` is
  listed in `git_directories`, so a `.git` directory left in `/app/polyglot`
  is captured and the listing sees it, as `os.listdir` does upstream
  (`mutant-git-dir`). Without it, the implicit `**/.git` exclusion would drop
  it and the listing check would pass.
- **Case variants of `.git` are dropped** (more lenient, only for a candidate
  that leaves a directory named `.GIT`, `.Git` or similar in
  `/app/polyglot`). The implicit `.git` exclusion folds case, but the
  `git_directories` exemption matches the exact name `.git`, and no other
  name may be listed there. Such a directory is therefore not captured, and
  the listing sees only `main.rs`, where upstream's `os.listdir` on a
  case-sensitive filesystem sees both and fails. No pack setting can capture
  it.
- **Each language is built and run in its own Evaluation** (stricter, only
  for a program whose build or run in one language depends on the other
  language's build or run). Upstream builds both binaries in one container
  and runs the Rust binary before the C++ one for each input, so a Rust-only
  `main.rs` whose binary copies itself to `/app/polyglot/cmain` passes
  natively although `g++` builds nothing (`attack-self-copy`). Here
  `fibonacci-cpp` never builds or runs the Rust program, so the C++ result
  comes only from what `g++` built.
- **Files outside `/app` are not captured** (stricter, only for solutions the
  instructions do not allow). Natively, anything the agent changes in the
  container survives into grading: a replaced `g++` or `rustc`, or a header
  under `/usr/include`. The instructions ask for a single file and name the
  installed compilers, so a solution that depends on changes outside `/app`
  is not one they allow. `attack-fake-gxx` is the tampering version of this.
- **Scope bounds** (stricter, only for pathological candidates). Capture of
  `/app` is bounded at 100,000 entries and 2 GiB, the largest bounds allowed.
  Upstream has no such bound beyond the 10 GiB disk.
- **The adapter strips stdout** (equivalent). Upstream compares
  `stdout.strip()`; the adapter applies the same `str.strip()` to the stdout
  decoded as strict UTF-8 (Python 3.13 under the C locale uses UTF-8 mode for
  `text=True`), so a stdout that is not UTF-8 fails both graders
  (`mutant-invalid-utf8`) and any whitespace around the number, Unicode
  whitespace included, is accepted by both (`mutant-whitespace`). Stripping
  in the adapter rather than the Oracle lets any amount of surrounding
  whitespace fit the observation. `text=True` also turns `\r\n` and `\r` into
  `\n`; the adapter does not, which changes nothing: line breaks at the ends
  are stripped either way, and a line break inside the number never equals
  an expected value.
- **Stripped stdout over 64 KiB is reported unreadable** (equivalent). The
  longest expected value is 9 bytes, so such an output fails upstream's
  comparison too.
- **Separate cases instead of one loop** (equivalent). Upstream runs the five
  inputs in sequence in one container and stops at the first failure; here
  each input is a case in its own Evaluation, started from the snapshot taken
  after the build. A program whose result depends on files written by its
  own earlier runs could behave differently; the task's output depends only
  on `n`.
- **Timeouts** (more lenient). The native verifier has 900 seconds for
  everything, including installing `curl`, `uv` and Python. Here each build
  has 900 seconds and each case another 900. A solution that is correct but
  takes minutes per run could pass here and time out natively. The reference
  takes under a second per case.
- **Standard input and error** (equivalent). The binary gets `/dev/null` as
  standard input and its standard error is discarded; upstream captures
  standard error and never reads it.

No instructions, domains (none are needed; the native verifier downloads its
tools, which Evaluation does not need) or cases change.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` byte for byte, after a
  `cd /app` (upstream relies on the working directory being `/app`).
- `null.sh`: changes nothing.
- `mutant-whitespace.sh`: the reference printing the number between ASCII
  and Unicode whitespace (tab, NBSP, CR). Aimed at the adapter's decoding
  and stripping; passes both.
- `mutant-invalid-utf8.sh`: the reference whose C++ build prints `0xff`
  after the number. Aimed at the adapter's decoding; fails both.
- `mutant-git-dir.sh`: the reference plus `/app/polyglot/.git`. Aimed at the
  listing and the implicit `.git` exclusion; fails both.
- `mutant-exit-status.sh`: the reference whose C++ build exits 3 after
  printing the right number. Aimed at the adapter's report of `check=True`;
  fails both.
- `mutant-include-outside.sh`: the reference whose C++ side includes a
  header from `/app/include`. Aimed at the scope; passes both.
- `attack-self-copy.sh`: a Rust-only `main.rs` whose binary copies itself
  to `/app/polyglot/cmain` when run, so a grader that runs the Rust binary
  first in the same filesystem runs the Rust program as the C++ one. Here
  the C++ check never contains the Rust binary, `g++` builds nothing, and
  every `fibonacci-cpp` case fails.
- `attack-fake-gxx.sh`: a Rust-only `main.rs` and a `g++` wrapper outside
  `/app` that builds a separate C++ file whenever asked to compile `main.rs`.
  Natively the wrapper is in place at grading time; here it is not captured,
  the real `g++` rejects the Rust code, and every `fibonacci-cpp` case fails.
- `attack-adapter-takeover.sh`: a Rust-only `main.rs` whose binary writes a
  forged observation into the adapter's standard output through
  `/proc/<ppid>/fd/1` and then kills the adapter. The killed adapter exits
  non-zero, so the `fibonacci-rust` cases fail as `case_error`; the
  `fibonacci-cpp` cases fail because `g++` builds nothing.

## Divergences from native

- `attack-fake-gxx`: native reward 1.0, SecureBench `failed` (oracle; the
  C++ binary is never built). SecureBench is right. The candidate's
  `main.rs` is plain Rust and not a polyglot: `g++ -x c++` on it fails. It
  passes natively only because the replaced `/usr/bin/g++` is still in the
  container when the verifier runs, so the native grader tests the agent's
  wrapper rather than the installed g++ 13 the instructions name.
- `attack-self-copy`: native reward 1.0, SecureBench `failed` (oracle; no
  C++ binary in any `fibonacci-cpp` case). SecureBench is right. `main.rs`
  is plain Rust, which `g++` rejects. Natively the Rust binary runs first
  and copies itself over the missing `cmain`, so the verifier's "C++" runs
  are the Rust program.

Every other candidate gets the same verdict from both graders: the reference,
`mutant-whitespace` and `mutant-include-outside` pass both; the null
candidate, `mutant-invalid-utf8`, `mutant-git-dir`, `mutant-exit-status` and
`attack-adapter-takeover` fail both.

## Review

Reviewer: conversion-reviewer (scratch `polyglot-rust-c-review`), 2026-10-26 (second review, after the converter addressed review 1)

Pack digest reviewed: `sha256:77be7f7b8cc8ed636984b6417cc23f4133ce38161c396cb7c23af2f66577a557` (`securebench validate`, unchanged at the end of the review).

Review 1 findings and what became of them:

- **Rust binary replacing `cmain` (fixed).** There are now two protocol checks, `fibonacci-rust` and `fibonacci-cpp` (`task.toml` lines 34-69). `setup.sh` takes the language and runs only that compile command, and `adapter.py` runs only that check's binary. So no `fibonacci-cpp` Evaluation contains a Rust build, and no `fibonacci-rust` Evaluation contains a C++ build. Prebuilt binaries cannot be shipped: the listing check allows only `main.rs` in `/app/polyglot`, and artifact checks run first. `attack-self-copy.sh` is my attack script unchanged below the comment (`diff`). It now gets `failed` (oracle) from SecureBench and 1.0 natively.
- **Case variants of `.git` (recorded).** They are recorded as more lenient. The reason is correct: `_git_directory` in `securebench/taskspec/load.py` accepts only the exact name `.git`. The `polyglot/.git` bullet no longer claims it matches `os.listdir` in general.
- **Symlinked `/app/polyglot` (recorded).** It is recorded as stricter. The reason given, that the instructions ask for a file written in `/app/polyglot` and not a linked directory, holds.

1. Instructions. `cmp` against upstream `instruction.md`: identical (the file is unchanged since review 1).
2. Scope. Unchanged root `/app`, `git_directories = ["polyglot/.git"]`, `symlinks = true`, no exclude patterns. The baseline `/app` is empty, with no symlinks into or out of it and no `/.securebench` (checked in review 1 in the pinned image). It holds no test files and loads no files by convention. `setup.sh` still fixes `PATH` to system directories outside the scope, and the adapter runs under `python3 -I`. The two listing edge cases are now recorded (above).
3. Expected values. Only in `hidden/cases.json`, unchanged. Nothing in `evaluation/`, the baseline or the scope holds them, and they are public Fibonacci numbers in any case. There are no allowed domains.
4. Challenges. Still `{"n": n}` only, the same for both checks.
5. Cases. `plan` gives both checks the same five upstream `test_cases`. Each upstream entry runs two binaries, and each becomes one case, so nothing is added beyond that split. The split is recorded as stricter, with its reason. The seed is unused, and upstream draws no random values.
6. Oracle. It judges one flat observation per case: no `launch_error`, `exit_status` 0, `stdout_stripped` present and equal to the expected value from the context. It accepts only the three check ids. The observation schema is the old per-language object, and it still rejects extra fields. `max_observation_bytes` of 131072 can make an escaped stripped output near 64 KiB fail as `case_error`. Any such output is wrong anyway, since the longest expected value is 9 bytes, so the verdict is the same. Diagnostics are truncated, and anything unexpected fails. No regression tests run by outcome.
7. Candidates. The reference, null and mutants are unchanged since review 1 and still get the same verdict from both graders. There are three attacks: `attack-self-copy` (the route of finding 1), `attack-fake-gxx`, and `attack-adapter-takeover`, which now forges only a single-language observation. All three get `failed` from SecureBench. The forged Rust observation carries only a public value, and the forging adapter is killed, so the case fails as `case_error`.
8. Divergences. `attack-fake-gxx` (native 1.0, SecureBench `failed`) and `attack-self-copy` (native 1.0, SecureBench `failed`) are both explained, and SecureBench is right in both: each `main.rs` is plain Rust that `g++` rejects. `qualification.json` reports `problems: []`. Every SecureBench run records the digest above, framework commit `268badb` (not dirty), is admitted, and is reproduced by `rejudge`. Native results reused as `native_cached` are for candidate scripts that did not change. The two changed attacks ran natively again.
9. Inventory. `conversions/inventory.tsv` still has no row for `polyglot-rust-c`. This is a conversion, not an exclusion, and no Section 11 reason applies.

Upstream assertions:
- `os.listdir(...) == ["main.rs"]` is checked by `polyglot-listing`, with the two recorded edge cases.
- The two `os.popen` builds become `setup.sh rust` and `setup.sh cpp`.
- `check=True` becomes `exit_status == 0`.
- `text=True` becomes the strict UTF-8 decode.
- `strip() == expected` is judged per binary.

An upstream entry passes exactly when its case passes in both checks. No assertion is dropped, and every fidelity change has a label and a reason.

Findings:
- None that block approval. Note: the docstring of `task/hidden/oracle.py` (lines 3-6) still describes one `fibonacci` check "where both binaries must exit 0". It should name the two per-language checks. This is documentation only and does not change any verdict.

Verdict: approved
