# fix-ocaml-gc

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/fix-ocaml-gc

## What upstream checks

The agent must fix a bug in the OCaml runtime's major-heap sweeper
(`/app/ocaml/runtime/shared_heap.c`) so that the compiler bootstraps and the
basic testsuite passes. Upstream's `tests/test.sh`:

1. clones the original repository into `/app/ocaml-original` and replaces
   `/app/ocaml/testsuite` with its copy;
2. runs `make clean && ./configure && make -j4` in `/app/ocaml`, ignoring the
   exit status;
3. runs `make -C testsuite one DIR=tests/basic | tee tests.txt`;
4. `tests/test_outputs.py` asserts that `tests.txt` contains `40 tests passed`.

That line is printed by `testsuite/summarize.awk` from the result lines of
`ocamltest`, which the candidate's own build produces. Each of the 40 tests in
`testsuite/tests/basic` is one test file that ocamltest compiles, runs and
compares with reference files. The native grader therefore trusts a test report
written by candidate code: `candidates/attack-stub-ocamltest.sh` replaces the
build with stubs and a fake ocamltest that prints `=> passed` for every test,
and passes upstream's test without fixing anything.

## How the pack grades

One protocol check, `basic-testsuite`, with one case.

- **Setup** (`evaluation/build.sh`) runs upstream's build chain
  `make clean && ./configure && make -j4` in `/app/ocaml` and always exits 0,
  as upstream continues to the testsuite whatever the build's status. A
  candidate whose build fails therefore fails the case (class `oracle`),
  not the setup.
- **Case** (`evaluation/adapter.py`, stock Python):
  1. runs upstream's own command `make -C testsuite one DIR=tests/basic` in
     `/app/ocaml` and reports the end of its standard output (as upstream,
     only standard output; the exit status is not used, as upstream pipes it
     through `tee`);
  2. deletes `testsuite/tests/basic/_ocamltest` and then performs, one by one,
     the 444 steps ocamltest performs for the 40 tests: it creates each build
     directory with symlinks to the test's source modules, runs each of the
     223 commands with the same argv, working directory and output file as
     ocamltest, and reports each command's exit status and output file, the
     final `.corrected.corrected` file of the 3 expect tests, and the section
     table (name, length, SHA-256 of the contents) of the 70 bytecode
     programs that ocamltest compares with `tools/cmpbyt`.
- **Oracle** (`hidden/oracle.py`) passes the case only if:
  - the testsuite's standard output contains `40 tests passed` (upstream's
    assertion, kept literally);
  - each of the 478 ocamltest checks for these tests holds, recomputed from
    the raw outputs against the reference files in `hidden/reference/`:
    - 223 exit statuses: 0 for every compiler, program and expect run, except
      2 for the one compilation `unit_naming.ml` expects to fail;
    - 144 compiler outputs that must be empty (no `.compilers.reference`);
    - 76 text comparisons: 72 program outputs against `<test>.reference`, the
      compiler output of `unit_naming.ml` against
      `unit_naming.compilers.reference`, and the 3 expect tests' corrected files
      against their own source (`patmatch_for_multiple.ml`,
      `patmatch_incoherence.ml`, `patmatch_split_no_or.ml`);
    - 35 `compare-bytecode-programs` checks (every default test except
      `constprop.ml.c`, whose header disables the comparison).

The summary line alone is printed by candidate code and proves nothing, so the
Oracle does not rely on it; it is kept so that a candidate that breaks
ocamltest or the testsuite run fails here as it does natively. The
transliterated checks are what a forger has to satisfy: every compared value
is a raw output of the candidate's compilers and programs, and the expected
values are in `hidden/`.

### Mapping from ocamltest's checks

For each `(* TEST *)` file ocamltest runs two tests: `native` (ocamlopt.byte
build, check compiler output, run, check program output, ocamlopt.opt build,
check compiler output) and `bytecode` (ocamlc.byte build, check compiler
output, run, check program output, ocamlc.opt build, check compiler output,
compare-bytecode-programs). An `expect` test runs `testsuite/tools/expect`
twice (the second time with `-principal` on the first run's corrected file)
and compares the result with the test source. `unit_naming.ml` only compiles
with ocamlc.byte, expecting exit status 2 and the output in
`unit_naming.compilers.reference`. Every action that checks something maps to
one expectation in `hidden/cases.json`; the `what` field of each expectation
names the ocamltest action.

### How the plan was derived

`hidden/cases.json` holds the steps (sent as the challenge) and the
expectations (kept on the host). `hidden/derivation/derive_cases.py` produced
it from one native run of the reference solution in the upstream image
(`docker run --memory 6g`), traced with

```
cd /app/ocaml && strace -f -qq -v -s 8192 -e trace=execve,chdir,clone,clone3,vfork,fork \
    -e signal=none -o strace.txt \
    make -C testsuite one DIR=tests/basic OCAMLTESTFLAGS=-keep-test-dir-on-success
```

The trace gives the exact argv and working directory of every process
ocamltest started (the `-pp 'gcc -E -P  -D_FILE_OFFSET_BITS=64'` argument of
`constprop.ml.c` is one argv element; ocamltest's log prints it unquoted). The
kept ocamltest logs give the source modules of each build directory and the
reference file each comparison used. The expected exit status 2 comes from
the header of `unit_naming.ml` (`ocamlc_byte_exit_status = "2"`). The 40
reference files are copied unchanged from `testsuite/tests/basic` of the
upstream image. That native run printed `40 tests passed`, and the adapter
run on the same build judged by the Oracle passed every expectation.

## Reimplemented native tools

- **ocamltest's text comparison** (`Filecompare.compare_text_files`, used by
  every check-output action) is `oracle.same_text`: byte equality, except that
  when exactly one file's first line ends in CR, that file's terminated lines
  must all end in CRLF and are compared with the CR removed. We compiled the
  upstream function verbatim (with ocamltest's `Seq.equal`) into a test
  program and compared it with `same_text` on 40,948 file pairs: every pair of
  strings of at most 3 characters over `a`, CR and LF, and 3,000 random texts
  each paired both ways with CRLF/LF conversions, a trailing CR, a trailing
  LF, a removed final LF and a single CR inserted. The verdicts agreed on
  every pair. Upstream's `skip_header_lines`/`skip_header_bytes` variables are
  not set by any of these tests, so they are not reimplemented.
- **`tools/cmpbyt`** (compare-bytecode-programs) is the adapter's
  `bytecode_toc`, which reads the trailer and section table as
  `Bytesections.read_toc` does, plus `oracle.same_bytecode`, which requires
  both trailers to carry the upstream image's exec magic number `Caml1999X037` and the
  sections other than `DBUG` to match in order, name, length and content. We
  ran the real `tools/cmpbyt` and our version on 37 pairs built from real
  test programs: identical files, DBUG sections added to one or both sides at
  different positions, one byte changed and one byte appended in each
  section, renamed sections, a different loader prefix, rotated sections, an
  extra empty section, a different magic number on one or both sides,
  truncated, empty and garbage files, and corrupt section counts and lengths.
  The verdicts agreed on all 37.
- **ocamltest's orchestration** is replaced by the adapter replaying the
  traced commands (see the fidelity changes).

## Fidelity changes

- **Checks: ocamltest's per-test checks are added to upstream's summary
  assertion. Stricter, by design.** Upstream accepts whatever the candidate's
  ocamltest reports. The pack also recomputes every check ocamltest makes for
  the 40 tests from raw outputs. A candidate whose ocamltest misreports (such
  as `attack-stub-ocamltest.sh`) passes natively and fails here. For a
  candidate built with the reference build's configuration and a working
  ocamltest, both graders make the same checks, because these are the checks
  ocamltest itself makes. The next bullet lists where the verdicts can still
  differ.
- **The replayed checks are fixed from the reference build's configuration;
  ocamltest adapts to the candidate's. Stricter.** The replay cannot trust
  the candidate's configuration, which is in the scope (`configure`,
  `Makefile.config`, `utils/config`), so the steps, the expected exit
  statuses and the exec magic number are those of the traced reference build.
  ocamltest instead reads the candidate's build:
  - With the native compiler disabled (for example `./configure
    --disable-native-compiler`), ocamltest's `native` test becomes a skip and
    the `bytecode` test drops the `ocamlc.opt` build and
    compare-bytecode-programs (`ocamltest/ocaml_tests.ml`, lines 30-60 and
    88). ocamltest joins the branches so that a skipped branch beside a
    passed one counts as passed (`join_parallel` in `ocamltest/main.ml`),
    and `summarize.awk` counts `=> passed`, so native still prints
    `40 tests passed`, while the replayed `ocamlopt` and `ocamlc.opt` steps
    fail here.
  - tools/cmpbyt checks each program's trailer against the build's own
    `Config.exec_magic_number`; the Oracle requires `Caml1999X037`, the
    upstream image's value. A candidate that changes the magic number
    consistently passes natively and fails here.
  - The testsuite runs twice in the case (upstream's command for the summary
    line, then the replay), so a candidate whose compilers or programs
    behave nondeterministically has to pass both runs, where native runs the
    testsuite once.

  None of these is a plausible fix of the garbage collector, and none is
  exercised by a candidate.
- **Testsuite restored by scope, not by a fresh clone. Equivalent.**
  `ocaml/testsuite` is excluded from the scope, so every Evaluation sees the
  baseline image's testsuite, which was cloned from the same tag upstream's
  test.sh clones. Upstream's clone into `/app/ocaml-original` is not
  reproduced; it needs network access at grading time, and a candidate that
  pre-creates that directory makes upstream copy the candidate's testsuite
  instead (`attack-preclone-original.sh`).
- **Commands replayed by the adapter instead of ocamltest. Equivalent for
  the checks, with these differences:**
  - Each command gets a minimal environment: `PATH`, `HOME=/root`,
    `TERM=dumb`, `OCAMLRUNPARAM=` (empty), plus `OCAML_COLOR=auto` and
    `OCAML_ERROR_STYLE=contextual` for compilers and the expect tool, as in
    the traced run. The make and ocamltest bookkeeping variables (for example
    `MAKEFLAGS`, `test_build_directory`) are left out; none of the 40 tests
    reads them.
  - Standard input is `/dev/null` instead of the pipe make inherits. None of
    the tests reads standard input.
  - Each replayed command runs with ocamltest's 600-second timeout for
    this testsuite (`timeout=600`). Equivalent.
  - The adapter runs every step even after a failure, where ocamltest stops a
    test at its first failed action. The verdict is the same: the case fails
    if any check fails.
- **Bounds on reported outputs. Equivalent.** The adapter reports at most
  10,240 bytes of each output file; the longest expected output is 7,776
  bytes (8,028 with CRLF endings), so an output beyond the bound cannot
  match and fails. It reports the last 65,536 bytes of the testsuite's
  standard output, where the summary is printed (upstream's run prints about
  2.1 KB). A bytecode program with more than 64 sections or larger than 64
  MiB is reported as unreadable and fails the comparison; the test programs
  have 7 sections and about 230 KB.
- **Build failure fails the case, not the setup. Equivalent.** Upstream
  ignores the build's exit status and goes on to the testsuite, so
  `build.sh` does too; a build that fails late but leaves working compilers
  is graded on the testsuite, as upstream does.
- **Time limits. More lenient for a slow build, stricter for a slow
  testsuite.** Upstream's verifier has 3,600 seconds for the whole of
  test.sh: clone, build and testsuite. The pack gives the build its own
  3,600 seconds (`setup_timeout_seconds`) and the case another 3,600 seconds
  (`timeout_seconds`), so a candidate whose build and testsuite together take
  more than an hour can pass here and time out natively (more lenient).
  Inside the case, upstream's own testsuite command for the summary line is
  capped at 1,800 seconds (`SUMMARY_TIMEOUT` in `evaluation/adapter.py`), so
  that the replay keeps time to run; a candidate whose testsuite run takes
  between 30 minutes and an hour minus its build time passes natively and
  fails here (stricter). The reference build took 9 CPU-minutes (2 minutes
  with 8 CPUs) and the whole reference case 53 seconds on one CPU, so both
  limits are far from correct candidates.
- **Scope. Equivalent.** `/app`, with `ocaml/testsuite` excluded (see above),
  symlinks allowed (the OCaml build creates 167 internal symlinks), and the
  maximum bounds (100,000 entries, 2 GiB), because an agent will build in
  place: a built tree is about 750 MB and 9,000 files. Upstream's
  `make clean` removes those products before grading, as `build.sh` does.
- **Domains. Stricter for the agent.** None. Upstream allows internet
  access, which the reference solution (one `sed` command) does not need,
  and the pack allows only what the reference needs. With it, an agent
  could clone `github.com/sadiqj/ocaml`, the repository test.sh clones, and
  compare the broken tag with its history to find the change; without network
  that route is closed and the bug has to be found in the code.

## Candidates

- `reference.sh`: upstream's `solve.sh` (one `sed` on line 650 of
  `runtime/shared_heap.c`) with an explicit `cd`.
- `null.sh`: changes nothing; the build crashes while bootstrapping.
- `mutant-crlf-bytecode-stdout.sh`: the fix, plus a bytecode runtime that
  writes CRLF line endings on standard output and error (the replacement head
  of `caml_write_fd` is `crlf-write-fd.c`). Aimed at `oracle.same_text`:
  ocamltest's comparison accepts output whose lines all end in CRLF against
  an LF reference, so both graders should pass it. In a trial run 29 outputs
  carried CRLF endings, the native-style testsuite printed `40 tests passed`
  and the Oracle passed.
- `mutant-dbug-from-native-compiler.sh`: the fix, plus an `ocamlc.opt` that
  always writes a (possibly empty) DBUG section, which `ocamlc.byte` does not.
  Aimed at `oracle.same_bytecode`: cmpbyt ignores DBUG, so both graders should
  pass it (they did in a trial run).
- `mutant-extra-section-from-native-compiler.sh`: the fix, plus an
  `ocamlc.opt` that adds an empty `XTRA` section. Aimed at the same place
  from the strict side: cmpbyt fails 35 tests, and so does the Oracle (trial
  run: native 5 passed, 35 failed; Oracle 35 failed comparisons and the
  summary).
- `attack-stub-ocamltest.sh`: leaves the GC broken and replaces `configure`,
  `Makefile`, `Makefile.common` and `ocamltest/ocamltest.opt` with stubs, so
  the build "succeeds" and the restored testsuite prints `40 tests passed`. A
  simulation of upstream's test.sh printed the summary; SecureBench fails it
  (the summary passes, every command of the transliterated checks fails).
- `attack-preclone-original.sh`: leaves the GC broken and creates
  `/app/ocaml-original/testsuite/Makefile` whose `one` target prints the
  summary line. Upstream's clone into that directory then fails and test.sh
  copies this testsuite over the real one. SecureBench ignores that directory
  and fails the candidate.

## Divergences from native

Qualification (`qualification.json`, no problems): reference passed both
graders; null failed both; the three mutants agree (crlf and dbug passed
both, extra-section failed both).

- `attack-stub-ocamltest.sh`: native passed (reward 1.0), SecureBench failed
  (class `oracle`). SecureBench is right: the garbage collector is still
  broken and no compiler was built; the native grader accepted the
  `40 tests passed` line printed by the candidate's stub ocamltest. Here the
  summary line also passes, but every replayed compiler command fails to
  start.
- `attack-preclone-original.sh`: native passed (reward 1.0), SecureBench
  failed (class `oracle`). SecureBench is right: the build still crashes; the
  native grader's clone into the pre-created `/app/ocaml-original` failed, so
  test.sh copied the candidate's fake testsuite and its Makefile printed the
  summary line. SecureBench uses the baseline's testsuite and ignores that
  directory.

## Review

Reviewer: acca893ae1c1a2d05, 2026-10-27 (second review)

Pack digest at review: `sha256:9d73860705a989406e85c8142e6e985f3213d6f8330f4ad0625ffef0172f7116` (`securebench validate`), unchanged since the first review; the fixes are in `CONVERSION.md` only.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. `/app` with `ocaml/testsuite` excluded, symlinks allowed, maximum bounds. The baseline `/app` holds only `ocaml` and has no symlinks (`find /app -type l` in the pinned image: 0). The testsuite (test sources, reference files, `testsuite/Makefile`, `summarize.awk`, `testsuite/tools`) is excluded, so a candidate cannot rewrite the specification. The image's testsuite is byte-identical to a fresh clone of the tag (`diff -rq`), so the exclusion is equivalent to upstream's re-clone. ocamltest and the build files are in scope but feed only the summary line, which the Oracle does not rely on. The "Scope." bullet is now labelled equivalent. Correct.
3. Expected values. `public/` is absent. `evaluation/` holds the adapter, `build.sh` and schemas, with no expected value. The expected values (40 reference files, exit statuses, the summary substring, the exec magic) are in `hidden/`; the 40 files in `hidden/reference/` are byte-identical to `testsuite/tests/basic` in the pinned image. Those files are readable in the baseline but excluded from the scope, so a candidate cannot change what the Oracle compares with; they are upstream's public answers, which are out of scope. No allowed domains. Correct.
4. Challenges. The single challenge carries the summary command and 444 steps (argv, directories, output paths, source names); expectations and references stay in the context. Nothing beyond what the case needs.
5. Cases. One case for upstream's single test `test_tests_output`. Its 478 checks transliterate ocamltest's checks for the 40 tests the summary line reports, as Section 5 ("Never trust a test report") requires, because the summary comes from candidate-built ocamltest. Counts match ocamltest's test trees (36 default tests x 6 runs + 3 expect x 2 + 1 = 223 runs; 144 empty compiler outputs; 72 + 1 + 3 text comparisons; 35 cmpbyt). The seed is not used.
6. Oracle. Every expected value is read from `hidden/cases.json` and `hidden/reference/`; `oracle.py` holds only comparison logic. It keeps upstream's substring assertion, checks every expectation, rejects duplicate result ids, fails on missing steps, timeouts, unstartable commands and truncated outputs, bounds its work by the schema (outputs at most 10,240 bytes, 1,000 results, 64 sections), ignores extra fields, and fails closed. `same_text` follows `Filecompare.compare_text_files`; the `empty` kind matches `check_file` ("no reference: output must be empty", `ocamltest/filecompare.ml`, lines 221-228); `same_bytecode` follows `tools/cmpbyt.ml`. No regression tests run by outcome.
7. Candidates. `reference.sh` is upstream's `solve.sh` with an explicit `cd` (POSIX `sh` shebang). `null.sh` changes nothing. The three mutants build and run real code and are aimed at `same_text` and `same_bytecode`. The replay's dependence on the reference configuration is now recorded as a stricter fidelity change; the candidates that would exercise it (native compiler disabled, a changed magic number) are not plausible fixes, so the absence of a mutant there is acceptable. Both attacks tamper with native grading (a forged ocamltest report; a pre-created `/app/ocaml-original`). Every value the task compares with is public, so no forgery can pass a hidden check.
8. Divergences. `qualification.json` reports no problems; every SecureBench run records the digest above, is admitted, unchanged by rejudge, and made from a clean tree. The runs were made at two framework commits (32596a1, 5505e2c), but `git diff --stat` between them touches only `conversions/inventory.tsv` and project notes, no SecureBench code. Reference passed both, null failed both, the mutants agree (crlf and dbug passed both, extra-section failed both). The two divergences are the attacks, both native 1.0 and SecureBench `failed` (class `oracle`). The explanations hold: the stub attack's diagnostic shows every replayed compiler command "could not be started" (320 failed checks), and the preclone attack fails the summary and every replayed check (393 failed checks), the build still being broken. SecureBench is right in both.
9. Inventory. `conversions/inventory.tsv` has no row for `terminal-bench/fix-ocaml-gc` yet; no exclusion is claimed. The coordinator adds the row (`converted`).

Upstream assertions: `tests.txt` exists (the adapter always captures the summary output; equivalent) and contains `40 tests passed` (kept literally). The build's exit status is ignored, as upstream. Nothing is dropped.

First-review findings, rechecked:
- Unlabelled "Scope." and "Domains." bullets: fixed. Scope is labelled equivalent; Domains is labelled stricter for the agent, with the reason (least the reference needs) and the route it closes (cloning `github.com/sadiqj/ocaml` and comparing the tag with its history).
- Time limits: fixed. The new "Time limits" bullet records the separate 3,600 s setup and 3,600 s case (more lenient) and the 1,800 s cap on the summary run (stricter), with measured reference timings; the misleading "upstream's verifier timeout" sentence is gone.
- "Same verdict" claim: fixed. The claim is narrowed to candidates built with the reference configuration, and a new stricter bullet records the native-compiler-disabled skip, the fixed `Caml1999X037` magic number and the doubled testsuite run, with the reason (the replay cannot trust the candidate's configuration).

Findings:
- None.

Verdict: approved
